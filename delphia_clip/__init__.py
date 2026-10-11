# SPDX-License-Identifier: GPL-3.0-or-later
# This add-on is distributed without warranty; see COPYING.txt and LICENSE.txt.
bl_info = {
    "name": "Delphia Clipboard", "author": "Delphia",
    "version": (1, 1, 2), "blender": (3, 3, 0),
    "location": "3D View > Sidebar > Delphia", "category": "Import-Export",
    "description": "Send selected meshes to Delphia through a versioned clipboard reference",
}

import bpy
import uuid
from .transfer import publish
from .textures import apply_textures

_errors = {
    'Copy textures from Delphia first': ('먼저 Delphia에서 텍스처를 보내세요', '先にDelphiaからテクスチャを送信してください'),
    'Unsupported texture clipboard version': ('지원하지 않는 텍스처 전송 버전입니다', '未対応のテクスチャ転送バージョンです'),
    'Invalid texture transfer directory': ('올바르지 않은 텍스처 전송 폴더입니다', 'テクスチャ転送フォルダーが無効です'),
    'Invalid material list': ('올바르지 않은 머티리얼 목록입니다', 'マテリアル一覧が無効です'),
    'Unsupported channel': ('지원하지 않는 채널입니다', '未対応のチャンネルです'),
    'Invalid image filename': ('올바르지 않은 이미지 파일명입니다', '画像ファイル名が無効です'),
    'Invalid image path or size': ('올바르지 않은 이미지 경로 또는 크기입니다', '画像パスまたはサイズが無効です'),
    'Texture transfer is missing or changed; send again': ('텍스처 전송 데이터가 변경되었거나 손상되었습니다. 다시 보내세요', '転送データが変更または破損しています。再送信してください'),
    'Texture transfer exceeds the memory safety limit': ('텍스처 전송이 메모리 안전 한도를 초과합니다', '転送がメモリ安全制限を超えています'),
    'Could not decode texture': ('텍스처 이미지를 읽을 수 없습니다', 'テクスチャを読み込めません'),
    'Texture manifest is too large': ('텍스처 전송 목록 파일이 너무 큽니다', 'テクスチャ転送リストが大きすぎます'),
}

_translations = {
    'ko_KR': {
        ('*', 'Update Textures from Delphia'): 'Delphia 텍스처 업데이트',
        ('*', 'Updated %d channels; skipped %d materials'): '채널 %d개 업데이트, 머티리얼 %d개 건너뜀',
        ('*', 'Import Texture Manifest'): '텍스처 전송 파일 선택',
        ('*', 'Copy to Delphia'): 'Delphia로 복사',
        ('*', 'Copied selected meshes to Delphia'): '선택한 메시를 Delphia로 복사했습니다',
        ('*', 'Send selected meshes to Delphia through a versioned clipboard reference'): '선택한 메시를 클립보드 참조로 Delphia에 전달합니다',
        ('*', 'Export selected mesh objects for File > Open by BlenderClip in Delphia'): 'Delphia의 파일 > BlenderClip으로 열기에서 사용할 선택 메시를 내보냅니다',
    },
    'ja_JP': {
        ('*', 'Update Textures from Delphia'): 'Delphiaテクスチャを更新',
        ('*', 'Updated %d channels; skipped %d materials'): 'チャンネル%d個を更新、マテリアル%d個をスキップ',
        ('*', 'Import Texture Manifest'): 'テクスチャ転送ファイルを選択',
        ('*', 'Copy to Delphia'): 'Delphiaへコピー',
        ('*', 'Copied selected meshes to Delphia'): '選択メッシュをDelphiaへコピーしました',
        ('*', 'Send selected meshes to Delphia through a versioned clipboard reference'): '選択メッシュをクリップボード参照でDelphiaへ送信します',
        ('*', 'Export selected mesh objects for File > Open by BlenderClip in Delphia'): 'Delphiaのファイル > BlenderClipから開く用に選択メッシュを書き出します',
    },
}

_errors.update({
    'Model transfer exceeds the safety limit': ('모델 또는 머티리얼 목록이 전송 제한을 초과합니다. 선택을 나누어 보내주세요.', 'モデルまたはマテリアル一覧が転送上限を超えています。選択を分けて送信してください。'),
    'Replaced Textures': ('교체된 텍스처', '置き換えたテクスチャ'),
    'Select unused images to remove; source files are kept.': ('제거할 미사용 이미지를 선택하세요. 원본 파일은 유지됩니다.', '削除する未使用画像を選択してください。元ファイルは保持されます。'),
    'Unused': ('미사용', '未使用'),
    'In use / protected': ('사용 중 / 보호됨', '使用中 / 保護されています'),
    'Removed': ('제거됨', '削除済み'),
})

for _key, _values in _errors.items():
    for _locale, _value in zip(('ko_KR', 'ja_JP'), _values):
        _translations[_locale][('*', _key)] = _value


class DELPHIA_OT_copy(bpy.types.Operator):
    bl_idname = "delphia.copy_models"
    bl_label = "Copy to Delphia"
    bl_description = "Export selected mesh objects for File > Open by BlenderClip in Delphia"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        try:
            try:
                properties = bpy.ops.export_scene.fbx.get_rna_type().properties
            except (AttributeError, RuntimeError):
                import addon_utils
                addon_utils.enable("io_scene_fbx", default_set=False)
                properties = bpy.ops.export_scene.fbx.get_rna_type().properties
            required = {'filepath', 'use_selection', 'object_types', 'path_mode', 'embed_textures'}
            if not required.issubset(set(properties.keys())):
                raise RuntimeError("This FBX exporter does not support the required options")

            def export(path):
                options = dict(filepath=str(path), check_existing=False, use_selection=True,
                               object_types={'MESH'}, use_mesh_modifiers=True, bake_anim=False,
                               add_leaf_bones=False, path_mode='COPY', embed_textures=True,
                               axis_forward='-Z', axis_up='Y', batch_mode='OFF',
                               use_active_collection=False, use_visible=False)
                options = {key: value for key, value in options.items() if key in properties}
                if 'FINISHED' not in bpy.ops.export_scene.fbx(**options):
                    raise RuntimeError("FBX export was cancelled")

            materials = {}
            for ob in context.selected_objects:
                if ob.type != 'MESH':
                    continue
                for slot in ob.material_slots:
                    mat = slot.material
                    if mat is None or mat.library:
                        continue
                    identity = mat.get('delphia_id')
                    if not identity:
                        identity = str(uuid.uuid4())
                        mat['delphia_id'] = identity
                    materials[mat.name] = identity
            publish(export, lambda text: setattr(context.window_manager, 'clipboard', text), materials=materials)
        except Exception as exc:
            self.report({'ERROR'}, bpy.app.translations.pgettext_iface(str(exc)))
            return {'CANCELLED'}
        self.report({'INFO'}, bpy.app.translations.pgettext_iface("Copied selected meshes to Delphia"))
        return {'FINISHED'}


class DELPHIA_PG_replaced(bpy.types.PropertyGroup):
    image_name: bpy.props.StringProperty()
    identity: bpy.props.StringProperty()
    details: bpy.props.StringProperty()
    selected: bpy.props.BoolProperty(default=False)


def replacement_image(item):
    image = bpy.data.images.get(item.image_name)
    return image if image and str(image.as_pointer()) == item.identity else None


def removable_image(image):
    return image is not None and image.users == 0 and not image.use_fake_user and not image.library


class DELPHIA_UL_replaced(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        image = replacement_image(item)
        row = layout.row()
        row.enabled = removable_image(image)
        row.prop(item, 'selected', text='')
        row.label(text=item.image_name, icon='IMAGE_DATA')
        layout.label(text=item.details)
        layout.label(text='Unused' if removable_image(image) else 'In use / protected' if image else 'Removed')


class DELPHIA_OT_replaced(bpy.types.Operator):
    bl_idname = 'delphia.review_replaced'
    bl_label = 'Replaced Textures'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=720)

    def draw(self, context):
        wm = context.window_manager
        self.layout.label(text='Select unused images to remove; source files are kept.')
        self.layout.template_list('DELPHIA_UL_replaced', '', wm, 'delphia_replaced', wm,
                                  'delphia_replaced_index', rows=8)

    def execute(self, context):
        for item in context.window_manager.delphia_replaced:
            image = replacement_image(item)
            if item.selected and removable_image(image):
                bpy.data.images.remove(image)
        return {'FINISHED'}


def show_replaced(context, records):
    items = context.window_manager.delphia_replaced
    previous = [(i.image_name, i.identity, i.details, '') for i in items if replacement_image(i)]
    items.clear()
    seen = set()
    for name, identity, material, channel in previous + records:
        if identity in seen:
            continue
        seen.add(identity)
        item = items.add()
        item.image_name, item.identity = name, identity
        item.details = material + (' / ' + channel if channel else '')
    if records and not bpy.app.background:
        bpy.ops.delphia.review_replaced('INVOKE_DEFAULT')


class DELPHIA_OT_textures(bpy.types.Operator):
    bl_idname = 'delphia.import_textures'
    bl_label = 'Update Textures from Delphia'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            records = []
            applied, skipped = apply_textures(context.window_manager.clipboard, records)
        except Exception as exc:
            self.report({'ERROR'}, bpy.app.translations.pgettext_iface(str(exc)))
            return {'CANCELLED'}
        self.report({'WARNING'} if skipped else {'INFO'},
                    bpy.app.translations.pgettext_iface('Updated %d channels; skipped %d materials') % (applied, skipped))
        show_replaced(context, records)
        return {'FINISHED'}


class DELPHIA_PT_bridge(bpy.types.Panel):
    bl_label = 'Delphia'
    bl_idname = 'DELPHIA_PT_bridge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Delphia'

    def draw(self, context):
        self.layout.operator(DELPHIA_OT_copy.bl_idname, icon='EXPORT')
        self.layout.operator(DELPHIA_OT_textures.bl_idname, icon='IMPORT')
        self.layout.operator(DELPHIA_OT_texture_file.bl_idname, icon='FILE_FOLDER')
        self.layout.operator(DELPHIA_OT_replaced.bl_idname, icon='IMAGE_DATA')


class DELPHIA_OT_texture_file(bpy.types.Operator):
    bl_idname = 'delphia.import_texture_file'
    bl_label = 'Import Texture Manifest'
    bl_options = {'REGISTER', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default='*.json', options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from pathlib import Path
        from .textures import PREFIX
        try:
            path = Path(self.filepath)
            if path.stat().st_size > 4*1024*1024:
                raise ValueError('Texture manifest is too large')
            records = []
            applied, skipped = apply_textures(PREFIX + path.read_text(encoding='utf-8'), records)
        except Exception as exc:
            self.report({'ERROR'}, bpy.app.translations.pgettext_iface(str(exc)))
            return {'CANCELLED'}
        self.report({'WARNING'} if skipped else {'INFO'},
                    bpy.app.translations.pgettext_iface('Updated %d channels; skipped %d materials') % (applied, skipped))
        show_replaced(context, records)
        return {'FINISHED'}


def menu(self, context):
    self.layout.operator(DELPHIA_OT_copy.bl_idname, icon='COPYDOWN')


def register():
    bpy.app.translations.register(__name__, _translations)
    bpy.utils.register_class(DELPHIA_PG_replaced)
    bpy.types.WindowManager.delphia_replaced = bpy.props.CollectionProperty(type=DELPHIA_PG_replaced)
    bpy.types.WindowManager.delphia_replaced_index = bpy.props.IntProperty()
    bpy.utils.register_class(DELPHIA_UL_replaced)
    bpy.utils.register_class(DELPHIA_OT_replaced)
    bpy.utils.register_class(DELPHIA_OT_copy)
    bpy.utils.register_class(DELPHIA_OT_textures)
    bpy.utils.register_class(DELPHIA_OT_texture_file)
    bpy.utils.register_class(DELPHIA_PT_bridge)
    bpy.types.VIEW3D_MT_object.append(menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu)
    bpy.utils.unregister_class(DELPHIA_PT_bridge)
    bpy.utils.unregister_class(DELPHIA_OT_texture_file)
    bpy.utils.unregister_class(DELPHIA_OT_textures)
    bpy.utils.unregister_class(DELPHIA_OT_copy)
    bpy.utils.unregister_class(DELPHIA_OT_replaced)
    bpy.utils.unregister_class(DELPHIA_UL_replaced)
    del bpy.types.WindowManager.delphia_replaced_index
    del bpy.types.WindowManager.delphia_replaced
    bpy.utils.unregister_class(DELPHIA_PG_replaced)
    bpy.app.translations.unregister(__name__)

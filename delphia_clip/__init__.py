# SPDX-License-Identifier: GPL-3.0-or-later
# This add-on is distributed without warranty; see COPYING.txt and LICENSE.txt.
bl_info = {
    "name": "Delphia Clipboard", "author": "Delphia",
    "version": (1, 0, 2), "blender": (3, 3, 0),
    "location": "3D View > Sidebar > Delphia", "category": "Import-Export",
    "description": "Send selected meshes to Delphia through a versioned clipboard reference",
}

import bpy
from .transfer import publish
from .textures import apply_textures
from . import dialogs
from . import copy_texture
from .help_ui import DELPHIA_OT_help

_POSE_WARNING = 'This file contains an armature. Meshes will be exported in their current pose.'
_POSE_RECOMMENDATION = 'Recommended: cancel, switch the armature to Rest Position, then export again.'
_POSE_UNCHANGED = 'Continuing does not change the original pose. Bones and animation are not exported.'
_POSE_TRANSLATIONS = {
    'ko_KR': {('*', _POSE_WARNING): '아마추어가 포함된 파일입니다. 메시가 현재 포즈 그대로 내보내집니다.',
              ('*', _POSE_RECOMMENDATION): '취소 후 아마추어를 Rest Position으로 변경하고 다시 내보내는 것을 권장합니다.',
              ('*', _POSE_UNCHANGED): '계속해도 원본 포즈는 변경하지 않습니다. 본과 애니메이션은 전송하지 않습니다.'},
    'ja_JP': {('*', _POSE_WARNING): 'アーマチュアが含まれています。現在のポーズでメッシュを出力します。',
              ('*', _POSE_RECOMMENDATION): 'キャンセルしてレストポジションに切り替え、再度出力することを推奨します。',
              ('*', _POSE_UNCHANGED): '続行しても元のポーズは変更しません。ボーンとアニメーションは出力しません。'},
}

def has_armature():
    return any(obj.type == 'ARMATURE' for obj in bpy.data.objects)

class DELPHIA_OT_copy(bpy.types.Operator):
    bl_idname = "delphia.copy_models"
    bl_label = "Copy to Delphia"
    bl_description = "Export selected mesh objects for File > Open by BlenderClip in Delphia"
    pose_warning_accepted: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' for o in context.selected_objects)

    def invoke(self, context, event):
        self.pose_warning_accepted = False
        if has_armature():
            # execute is called only after OK; cancellation never starts export.
            self.pose_warning_accepted = True
            return context.window_manager.invoke_props_dialog(self, width=700)
        return self.execute(context)

    def draw(self, context):
        self.layout.label(text=_POSE_WARNING, icon='ERROR')
        self.layout.label(text=_POSE_RECOMMENDATION)
        self.layout.label(text=_POSE_UNCHANGED)

    def execute(self, context):
        accepted = self.pose_warning_accepted
        self.pose_warning_accepted = False
        if has_armature() and not accepted:
            self.report({'WARNING'}, bpy.app.translations.pgettext_iface(_POSE_WARNING) + ' ' +
                        bpy.app.translations.pgettext_iface(_POSE_RECOMMENDATION))
            return {'CANCELLED'}
        try:
            try:
                properties = bpy.ops.export_scene.fbx.get_rna_type().properties
            except (AttributeError, RuntimeError):
                import addon_utils
                addon_utils.enable("io_scene_fbx", default_set=False)
                properties = bpy.ops.export_scene.fbx.get_rna_type().properties
            # Color export is mandatory, never an optional exporter capability.
            # Refuse older exporters instead of silently dropping color attributes.
            required = {'filepath', 'use_selection', 'object_types', 'path_mode', 'embed_textures',
                        'colors_type'}
            if not required.issubset(set(properties.keys())):
                raise RuntimeError("This FBX exporter does not support the required options")

            def export(path):
                options = dict(filepath=str(path), check_existing=False, use_selection=True,
                               object_types={'MESH'}, use_mesh_modifiers=True, bake_anim=False,
                               add_leaf_bones=False, path_mode='STRIP',
                               embed_textures=False,
                               prioritize_active_color=False,
                               axis_forward='-Z', axis_up='Y', batch_mode='OFF',
                               use_active_collection=False, use_visible=False)
                options = {key: value for key, value in options.items() if key in properties}
                # Override defaults/presets on every invocation and export all
                # existing color attributes, not just the active attribute.
                options['colors_type'] = 'SRGB'
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
                    # Export never writes custom properties to user materials.
                    # Existing bridge IDs remain usable; otherwise match by name.
                    if isinstance(identity, str) and identity:
                        materials[mat.name] = identity
            publish(export, lambda text: setattr(context.window_manager, 'clipboard', text), materials=materials,
                    addon_version='.'.join(str(part) for part in bl_info['version']),
                    include_textures=False)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, "Copied selected meshes to Delphia")
        return {'FINISHED'}


class DELPHIA_OT_textures(bpy.types.Operator):
    bl_idname = 'delphia.import_textures'
    bl_label = 'Update Textures from Delphia'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.delphia.texture_mapping('INVOKE_DEFAULT', payload=context.window_manager.clipboard)


class DELPHIA_PT_bridge(bpy.types.Panel):
    bl_label = 'Delphia'
    bl_idname = 'DELPHIA_PT_bridge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Delphia'

    def draw(self, context):
        self.layout.operator(DELPHIA_OT_help.bl_idname, text='Help · EN / JP / KR', icon='HELP')
        self.layout.operator(DELPHIA_OT_copy.bl_idname, icon='EXPORT')
        self.layout.operator('delphia.copy_texture', icon='IMAGE_DATA')
        self.layout.operator(DELPHIA_OT_textures.bl_idname, icon='IMPORT')
        notice = self.layout.box().column(align=True)
        notice.label(text='Imported textures are', icon='INFO', translate=False)
        notice.label(text='packed automatically.', translate=False)
        notice.label(text='Save your .blend file', translate=False)
        notice.label(text='to keep them.', translate=False)
        images = [image for image in bpy.data.images if image.type not in ('RENDER_RESULT', 'COMPOSITING')]
        unused_count = sum(dialogs.unused(image) for image in images)
        if unused_count:
            warning = self.layout.box().column(align=True)
            warning.alert = True
            warning.label(text='%d unused images found.' % unused_count, icon='ERROR', translate=False)
            warning.label(text='Review before deleting.', translate=False)
        self.layout.operator('delphia.unused_images',
                             text='Unused Images · %d' % unused_count, icon='IMAGE_DATA')


def menu(self, context):
    self.layout.operator(DELPHIA_OT_copy.bl_idname, icon='COPYDOWN')


def register():
    bpy.app.translations.register(__name__, _POSE_TRANSLATIONS)
    bpy.utils.register_class(DELPHIA_OT_help)
    dialogs.register()
    copy_texture.register()
    for cls in (DELPHIA_OT_copy, DELPHIA_OT_textures, DELPHIA_PT_bridge):
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu)


def unregister():
    bpy.app.translations.unregister(__name__)
    bpy.utils.unregister_class(DELPHIA_OT_help)
    bpy.types.VIEW3D_MT_object.remove(menu)
    for cls in (DELPHIA_PT_bridge, DELPHIA_OT_textures, DELPHIA_OT_copy):
        bpy.utils.unregister_class(cls)
    dialogs.unregister()
    copy_texture.unregister()

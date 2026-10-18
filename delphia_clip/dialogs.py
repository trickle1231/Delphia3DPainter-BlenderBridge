# SPDX-License-Identifier: GPL-3.0-or-later
"""Material mapping and project-wide unused image review."""
import json
import bpy
from .textures import PREFIX, apply_textures
from .material_nodes import node_tree


class ClipboardTypeMismatch(ValueError):
    pass


def unsupported_reason(material, channel):
    if not material:
        return 'Missing Material'
    if material.library:
        return 'Linked Library (Read Only)'
    tree = node_tree(material)
    if tree is None:
        return ''
    outputs = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs) != 1:
        return 'No Unique Active Output'
    if len(outputs[0].inputs['Surface'].links) != 1:
        return 'Surface Not Connected'
    shader = outputs[0].inputs['Surface'].links[0].from_node
    if shader.type != 'BSDF_PRINCIPLED':
        return 'Surface Is Not Principled'
    socket = shader.inputs.get('Base Color' if channel == 'albedo' else 'Emission Color')
    if socket is None and channel == 'emission':
        socket = shader.inputs.get('Emission')
    if socket is None:
        return 'Missing Channel Socket'
    if socket.is_linked and socket.links[0].from_node.type != 'TEX_IMAGE':
        return 'Channel Uses Non-Image Nodes'
    return ''


def supported(material, channel):
    return not unsupported_reason(material, channel)


class SavedMapping(bpy.types.PropertyGroup):
    key: bpy.props.StringProperty()
    target: bpy.props.PointerProperty(type=bpy.types.Material)
    unassigned: bpy.props.BoolProperty()


def mapping_key(entry, channel):
    return json.dumps([entry.get('id') or '', entry['name'], channel])


def remember_mapping(rows, sources, scene):
    for row in rows:
        # Store explicit choices, not automatic ID/name suggestions.
        current = str(row.material.as_pointer()) if row.material else ''
        if current == row.initial:
            continue
        key = mapping_key(sources[row.source_index], row.channel)
        for i in reversed(range(len(scene.delphia_saved_mappings))):
            if scene.delphia_saved_mappings[i].key == key:
                scene.delphia_saved_mappings.remove(i)
        saved = scene.delphia_saved_mappings.add()
        saved.key, saved.target = key, row.material
        saved.unassigned = row.material is None


_material_items = {}
_material_numbers = {}


def material_choices(self, context):
    names = tuple(sorted({m.name for m in bpy.data.materials if not m.library}))
    # Keep enum strings alive: Blender retains references to callback items.
    if names not in _material_items:
        for name in names:
            if name not in _material_numbers:
                _material_numbers[name] = len(_material_numbers) + 1
        _material_items[names] = [('__UNASSIGNED__', 'Unassigned', 'Skip this texture', 0)] + [
            (name, name, name, _material_numbers[name]) for name in names]
    return _material_items[names]


class MappingRow(bpy.types.PropertyGroup):
    texture: bpy.props.StringProperty()
    channel: bpy.props.StringProperty()
    source_index: bpy.props.IntProperty()
    material_name: bpy.props.EnumProperty(items=material_choices)
    initial: bpy.props.StringProperty()
    match: bpy.props.StringProperty()

    @property
    def material(self):
        return bpy.data.materials.get(self.material_name)

    @material.setter
    def material(self, value):
        self.material_name = value.name if value else '__UNASSIGNED__'


def status(row, rows):
    mat = row.material
    if mat is None:
        return row.match if row.initial == '' and row.match.startswith('Saved Target') else 'Skipped'
    if sum(r.material == mat and r.channel == row.channel for r in rows) > 1:
        return 'Conflict: Same Material / Channel'
    if not supported(mat, row.channel):
        return unsupported_reason(mat, row.channel)
    return row.match if str(mat.as_pointer()) == row.initial else 'Manual Match'


class DELPHIA_UL_mapping(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.36)
        split.label(text=item.texture, translate=False)
        right = split.split(factor=0.62)
        right.prop(item, 'material_name', text='')
        right.label(text=status(item, data.rows), translate=False)


class DELPHIA_OT_mapping(bpy.types.Operator):
    bl_idname = 'delphia.texture_mapping'
    bl_label = 'Texture Mapping'
    bl_options = {'UNDO'}
    payload: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    rows: bpy.props.CollectionProperty(type=MappingRow)
    index: bpy.props.IntProperty()
    remove_replaced: bpy.props.BoolProperty(
        name='Remove Replaced Images (Packed Only)', default=False,
        description='After successful replacement, remove unused packed images only. Fake User and linked images are protected. Never deletes source files')

    def prepare(self):
        if not self.payload.startswith(PREFIX):
            raise ClipboardTypeMismatch('Clipboard does not contain Delphia textures. Use Send Textures to Blender in Delphia first.')
        if len(self.payload) > 4*1024*1024:
            raise ValueError('Texture manifest is too large')
        manifest = json.loads(self.payload[len(PREFIX):])
        if manifest.get('version') != 1 or len(manifest['materials']) > 4096:
            raise ValueError('Invalid texture manifest')
        self.rows.clear()
        for index, entry in enumerate(manifest['materials']):
            identity = entry.get('id')
            matches = [m for m in bpy.data.materials if identity and m.get('delphia_id') == identity and not m.library]
            mat = matches[0] if len(matches) == 1 else bpy.data.materials.get(entry['name'])
            if mat and mat.library:
                mat = None
            match = 'ID Match' if len(matches) == 1 else 'Name Match · Review'
            for channel in entry['channels']:
                if channel not in ('albedo', 'emission'):
                    raise ValueError('Unsupported channel')
                row = self.rows.add()
                row.texture = entry['name'] + '_' + channel.capitalize()
                row.channel, row.source_index = channel, index
                row.material = mat
                row.initial = str(mat.as_pointer()) if mat else ''
                row.match = match
                saved = [s for s in bpy.context.scene.delphia_saved_mappings if s.key == mapping_key(entry, channel)]
                if saved:
                    record = saved[0]
                    target = record.target if len(saved) == 1 else None
                    row.material = target if target and not target.library else None
                    row.initial = str(row.material.as_pointer()) if row.material else ''
                    row.match = ('Saved Match' if row.material else 'Skipped' if record.unassigned
                                 else 'Saved Target Missing · Review')

    def invoke(self, context, event):
        try:
            self.prepare()
        except ClipboardTypeMismatch as exc:
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=850)

    def draw(self, context):
        source = json.loads(self.payload[len(PREFIX):]).get('source', {})
        if not isinstance(source, dict):
            source = {}
        origin = self.layout.box()
        origin.label(text='Source: Delphia / ' + str(source.get('project', 'Unknown project'))[:200], translate=False)
        origin.label(text='Sent: ' + str(source.get('sentAt', 'Unknown'))[:80], translate=False)
        head = self.layout.split(factor=0.36)
        head.label(text='Texture', translate=False)
        right = head.split(factor=0.62)
        right.label(text='Material', translate=False)
        right.label(text='Status', translate=False)
        self.layout.template_list('DELPHIA_UL_mapping', '', self, 'rows', self, 'index', rows=10)
        if self.rows and 0 <= self.index < len(self.rows):
            self.layout.label(text=status(self.rows[self.index], self.rows), translate=False)
        self.layout.label(text='Choose Unassigned to skip a texture.', translate=False)
        self.layout.label(text='Manual choices are remembered. Save your .blend to keep them.', translate=False)
        self.layout.prop(self, 'remove_replaced')

    def execute(self, context):
        try:
            if not self.rows:
                self.prepare()
            problems = [r.texture + ': ' + status(r, self.rows) for r in self.rows if r.material and (
                unsupported_reason(r.material, r.channel) or sum(other.material == r.material and other.channel == r.channel for other in self.rows) > 1)]
            if problems:
                raise ValueError('; '.join(problems))
            manifest = json.loads(self.payload[len(PREFIX):])
            sources = manifest['materials']
            manifest['materials'] = [dict(name=r.material.name, id='', channels={r.channel: sources[r.source_index]['channels'][r.channel]})
                                     for r in self.rows if r.material]
            replaced = []
            context.window_manager.progress_begin(0, 100)
            try:
                applied, skipped = apply_textures(PREFIX + json.dumps(manifest), replaced,
                                                 context.window_manager.progress_update)
            finally:
                context.window_manager.progress_end()
            remember_mapping(self.rows, sources, context.scene)
            removed = remove_replaced_packed(replaced) if self.remove_replaced else 0
            self.report({'INFO'}, 'Updated %d channels; %d unassigned' % (applied, sum(not r.material for r in self.rows)))
            if removed:
                self.report({'INFO'}, 'Removed %d unused packed images. Source files were not deleted.' % removed)
        except ClipboardTypeMismatch as exc:
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


def unused(image):
    return (image.users == 0 and not image.use_fake_user and not image.library
            and image.type not in ('RENDER_RESULT', 'COMPOSITING'))


def remove_replaced_packed(records):
    count = 0
    for name, identity, _, _ in records:
        image = bpy.data.images.get(name)
        if (image and str(image.as_pointer()) == identity and unused(image)
                and (image.packed_file or len(image.packed_files))):
            bpy.data.images.remove(image)
            count += 1
    return count


class UnusedRow(bpy.types.PropertyGroup):
    image_name: bpy.props.StringProperty()
    identity: bpy.props.StringProperty()
    selected: bpy.props.BoolProperty()


def resolve_image(row):
    image = bpy.data.images.get(row.image_name)
    return image if image and str(image.as_pointer()) == row.identity else None


def refresh_unused(wm):
    wm.delphia_unused.clear()
    for image in sorted(bpy.data.images, key=lambda i: i.name.casefold()):
        if unused(image):
            row = wm.delphia_unused.add()
            row.image_name, row.identity = image.name, str(image.as_pointer())
    wm.delphia_unused_index = min(wm.delphia_unused_index, max(0, len(wm.delphia_unused)-1))


class DELPHIA_UL_unused(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        image = resolve_image(item)
        row = layout.row()
        row.enabled = bool(image and unused(image) and not image.library and not image.use_fake_user)
        row.prop(item, 'selected', text='')
        row.label(text=item.image_name, translate=False, icon='IMAGE_DATA')
        if image and (image.library or image.use_fake_user):
            layout.label(text='Protected', translate=False)


class DELPHIA_OT_select_unused(bpy.types.Operator):
    bl_idname = 'delphia.select_unused_images'
    bl_label = 'Select All'
    select: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for row in context.window_manager.delphia_unused:
            image = resolve_image(row)
            row.selected = bool(self.select and image and unused(image))
        return {'FINISHED'}


class DELPHIA_OT_delete_unused(bpy.types.Operator):
    bl_idname = 'delphia.delete_unused_images'
    bl_label = 'Delete Selected'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        count = 0
        for row in context.window_manager.delphia_unused:
            image = resolve_image(row)
            if row.selected and image and unused(image) and not image.library and not image.use_fake_user:
                bpy.data.images.remove(image)
                count += 1
        refresh_unused(context.window_manager)
        self.report({'INFO'}, 'Removed %d images. Source files were not deleted.' % count)
        return {'FINISHED'}


class DELPHIA_OT_unused(bpy.types.Operator):
    bl_idname = 'delphia.unused_images'
    bl_label = 'Unused Textures'

    def invoke(self, context, event):
        refresh_unused(context.window_manager)
        return context.window_manager.invoke_props_dialog(self, width=850)

    def draw(self, context):
        wm = context.window_manager
        images = [image for image in bpy.data.images if image.type not in ('RENDER_RESULT', 'COMPOSITING')]
        self.layout.label(text='Unused Images: %d / %d total' % (sum(unused(image) for image in images), len(images)), translate=False)
        split = self.layout.split(factor=0.5)
        left = split.column()
        left.template_list('DELPHIA_UL_unused', '', wm, 'delphia_unused', wm, 'delphia_unused_index', rows=12)
        selection = left.row(align=True)
        selection.operator('delphia.select_unused_images', text='Select All').select = True
        selection.operator('delphia.select_unused_images', text='Deselect All').select = False
        left.operator('delphia.delete_unused_images', icon='TRASH')
        right = split.column()
        if wm.delphia_unused and wm.delphia_unused_index < len(wm.delphia_unused):
            image = resolve_image(wm.delphia_unused[wm.delphia_unused_index])
            if image:
                image.preview_ensure()
                if image.preview and image.preview.icon_id:
                    right.template_icon(icon_value=image.preview.icon_id, scale=16)
                else:
                    right.label(text='Preview unavailable', translate=False)
                right.label(text=image.name, translate=False)
                right.label(text='%d × %d' % tuple(image.size), translate=False)
        self.layout.label(text='Only deletable unused images. Fake User / linked images excluded. Source files are kept.', translate=False)

    def execute(self, context):
        return {'FINISHED'}


classes = (SavedMapping, MappingRow, UnusedRow, DELPHIA_UL_mapping, DELPHIA_OT_mapping,
           DELPHIA_UL_unused, DELPHIA_OT_select_unused, DELPHIA_OT_delete_unused, DELPHIA_OT_unused)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.delphia_unused = bpy.props.CollectionProperty(type=UnusedRow)
    bpy.types.WindowManager.delphia_unused_index = bpy.props.IntProperty(min=0)
    bpy.types.Scene.delphia_saved_mappings = bpy.props.CollectionProperty(type=SavedMapping)


def unregister():
    del bpy.types.Scene.delphia_saved_mappings
    del bpy.types.WindowManager.delphia_unused_index
    del bpy.types.WindowManager.delphia_unused
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

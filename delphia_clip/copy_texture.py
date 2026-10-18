# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy individual material images using Blender's native image clipboard."""
import bpy
import bpy.utils.previews

_previews = None


def clear_preview():
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None


def update_preview(wm, context):
    global _previews
    clear_preview()
    index = wm.delphia_copy_image_index
    if not 0 <= index < len(wm.delphia_copy_images):
        return
    image = wm.delphia_copy_images[index].image
    if image is None:
        return
    temporary = None
    try:
        width, height = image.size
        if width <= 0 or height <= 0 or width * height > 67108864:
            return
        # Generate pixels on a disposable copy, never on the user's image.
        temporary = image.copy()
        ratio = min(1.0, 256 / max(width, height))
        width, height = max(1, int(width * ratio)), max(1, int(height * ratio))
        temporary.scale(width, height)
        _previews = bpy.utils.previews.new()
        preview = _previews.new('selected')
        preview.image_size = (width, height)
        preview.image_pixels_float = temporary.pixels[:]
    except (RuntimeError, ValueError, ReferenceError):
        clear_preview()
    finally:
        if temporary is not None:
            bpy.data.images.remove(temporary)


def material_images(context):
    images = {}
    visited = set()

    def visit(tree):
        if tree is None or tree.as_pointer() in visited:
            return
        visited.add(tree.as_pointer())
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image and node.image.source in {'FILE', 'GENERATED'}:
                images[node.image.as_pointer()] = node.image
            elif node.type == 'GROUP':
                visit(node.node_tree)

    for obj in context.selected_objects:
        for slot in getattr(obj, 'material_slots', ()):
            if slot.material:
                visit(slot.material.node_tree)
    return sorted(images.values(), key=lambda image: (image.name, image.library.filepath if image.library else ''))


class DELPHIA_OT_copy_image(bpy.types.Operator):
    bl_idname = 'delphia.copy_texture_image'
    bl_label = 'Copy'
    bl_description = 'Copy this image to the system clipboard'
    image_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        entries = context.window_manager.delphia_copy_images
        image = entries[self.image_index].image if 0 <= self.image_index < len(entries) else None
        if image is None:
            self.report({'ERROR'}, 'Image is no longer available')
            return {'CANCELLED'}
        try:
            # No editor switching, material edits, rendering or baking.
            with context.temp_override(edit_image=image):
                result = bpy.ops.image.clipboard_copy()
            if 'FINISHED' not in result:
                raise RuntimeError('Image clipboard is unavailable on this platform')
        except (RuntimeError, AttributeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Image copied to clipboard')
        return {'FINISHED'}


class DELPHIA_PG_copy_image(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(type=bpy.types.Image)


class DELPHIA_UL_copy_images(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        image = item.image
        if image:
            label = image.name + (' — ' + image.library.filepath if image.library else '')
            layout.label(text=label, icon='IMAGE_DATA', translate=False)
            layout.operator('delphia.copy_texture_image', text='Copy', icon='COPYDOWN').image_index = index


class DELPHIA_OT_copy_texture(bpy.types.Operator):
    bl_idname = 'delphia.copy_texture'
    bl_label = 'Copy Texture'
    bl_description = 'Preview and copy one image from the selected objects\' materials'

    def invoke(self, context, event):
        entries = context.window_manager.delphia_copy_images
        entries.clear()
        for image in material_images(context):
            entries.add().image = image
        context.window_manager.delphia_copy_image_index = 0
        update_preview(context.window_manager, context)
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        if not wm.delphia_copy_images:
            layout.label(text='No material images on selected objects', icon='INFO')
            return
        layout.template_list('DELPHIA_UL_copy_images', '', wm, 'delphia_copy_images',
                             wm, 'delphia_copy_image_index', rows=6)
        index = wm.delphia_copy_image_index
        image = wm.delphia_copy_images[index].image if 0 <= index < len(wm.delphia_copy_images) else None
        if image:
            if _previews and 'selected' in _previews:
                layout.template_icon(icon_value=_previews['selected'].icon_id, scale=10)
            else:
                layout.label(text='Preview unavailable', icon='INFO')
            layout.label(text='%d x %d' % tuple(image.size), translate=False)

    def execute(self, context):
        clear_preview()
        context.window_manager.delphia_copy_images.clear()
        return {'FINISHED'}

    def cancel(self, context):
        clear_preview()
        context.window_manager.delphia_copy_images.clear()


def register():
    for cls in (DELPHIA_OT_copy_image, DELPHIA_PG_copy_image, DELPHIA_UL_copy_images, DELPHIA_OT_copy_texture):
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.delphia_copy_images = bpy.props.CollectionProperty(type=DELPHIA_PG_copy_image, options={'SKIP_SAVE'})
    bpy.types.WindowManager.delphia_copy_image_index = bpy.props.IntProperty(options={'SKIP_SAVE'}, update=update_preview)


def unregister():
    clear_preview()
    del bpy.types.WindowManager.delphia_copy_image_index
    del bpy.types.WindowManager.delphia_copy_images
    for cls in (DELPHIA_OT_copy_texture, DELPHIA_UL_copy_images, DELPHIA_PG_copy_image, DELPHIA_OT_copy_image):
        bpy.utils.unregister_class(cls)

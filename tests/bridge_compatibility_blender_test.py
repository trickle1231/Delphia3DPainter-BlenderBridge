"""Run in Blender background mode; only creates disposable test materials."""
import sys
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
from delphia_clip.material_nodes import node_tree, node_usage_state, restore_pre_node_material
from delphia_clip.dialogs import mapping_key

assert mapping_key({'id': 'duplicate', 'name': 'A'}, 'albedo') != mapping_key(
    {'id': 'duplicate', 'name': 'B'}, 'albedo')
material = bpy.data.materials.new('Bridge Compatibility Test')
tree = node_tree(material, create=True)
image_node = tree.nodes.new('ShaderNodeTexImage')
image = bpy.data.images.new('Bridge Compatibility Image', width=2, height=2)
image_node.image = image
shader = next(n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED')
tree.links.new(image_node.outputs['Color'], shader.inputs['Base Color'])
if bpy.app.version < (5, 0, 0):
    material.use_nodes = False
    previous = node_usage_state(material)
    assert node_tree(material, create=True) == tree and material.use_nodes
    restore_pre_node_material(material, True, previous)
    assert not material.use_nodes
    material.use_nodes = True
mesh = bpy.data.meshes.new('Bridge Compatibility Mesh')
obj = bpy.data.objects.new('Bridge Compatibility Object', mesh)
mesh.materials.append(material)
original_link = obj.material_slots[0].link
import tempfile
bpy.context.collection.objects.link(obj)
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
before_nodes = tuple(tree.nodes)
before_links = [(link.from_socket, link.to_socket) for link in tree.links]
before_properties = dict(material.items())
with tempfile.TemporaryDirectory() as folder:
    for include in (False, True):
        bpy.ops.export_scene.fbx(filepath=str(Path(folder) / 'test.fbx'),
            use_selection=True, object_types={'MESH'},
            path_mode='COPY' if include else 'STRIP', embed_textures=include)
        assert tuple(tree.nodes) == before_nodes
        assert [(link.from_socket, link.to_socket) for link in tree.links] == before_links
        assert dict(material.items()) == before_properties
        assert image_node.image == image
assert obj.material_slots[0].material == material
assert obj.material_slots[0].link == original_link
bpy.data.objects.remove(obj, do_unlink=True)
bpy.data.meshes.remove(mesh)
bpy.data.materials.remove(material)
bpy.data.images.remove(image)
print('Bridge compatibility cases PASS')

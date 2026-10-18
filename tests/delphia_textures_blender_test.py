import sys
import json
import hashlib
import tempfile
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
import delphia_clip
from delphia_clip.textures import apply_textures, PREFIX
from delphia_clip.material_nodes import node_tree

delphia_clip.register()
material = bpy.data.materials.new('Bridge Test')
assert node_tree(material, create=True) is not None
material['delphia_id'] = 'test-identity'
shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
with tempfile.TemporaryDirectory(prefix='DelphiaTextures-') as folder:
    image = bpy.data.images.new('test image', width=4, height=4)
    image.generated_color = (0.3, 0.5, 0.8, 1)
    image.filepath_raw = str(Path(folder) / '0.png')
    image.file_format = 'PNG'
    image.save()
    info = dict(file='0.png', sha256=hashlib.sha256(Path(image.filepath_raw).read_bytes()).hexdigest())
    entry = dict(name='renamed original', id='test-identity', channels=dict(albedo=info, emission=info))
    manifest = dict(version=1, directory=folder, materials=[entry])
    text = PREFIX + json.dumps(manifest)
    progress_values = []
    assert apply_textures(text, progress=progress_values.append) == (2, 0)
    assert progress_values and progress_values[-1] == 100
    assert progress_values == sorted(progress_values)
    count = len(bpy.data.images)
    assert apply_textures(text) == (2, 0)
    assert len(bpy.data.images) == count
    node = shader.inputs['Base Color'].links[0].from_node
    assert node.image.packed_file
    emission = shader.inputs.get('Emission Color') or shader.inputs.get('Emission')
    assert emission.is_linked
    assert emission.links[0].from_node.image.packed_file
    albedo_node = shader.inputs['Base Color'].links[0].from_node
    emission_node = emission.links[0].from_node
    assert albedo_node.location.x < shader.location.x
    assert emission_node.location.x < shader.location.x
    assert albedo_node.location != emission_node.location
    # ID-free local imports use exact names; duplicate IDs are never guessed.
    entry['id'] = ''
    entry['name'] = material.name
    assert apply_textures(PREFIX + json.dumps(manifest)) == (2, 0)
    entry['id'] = 'test-identity'
    duplicate = bpy.data.materials.new('Duplicate ID')
    duplicate['delphia_id'] = 'test-identity'
    assert apply_textures(PREFIX + json.dumps(manifest)) == (2, 0)
    bpy.data.materials.remove(duplicate)
    # Review preserves old images until explicit selection; deletion rechecks users.
    records = []
    assert apply_textures(text, records) == (2, 0)
    assert len(records) == 2
    # Shared image node must not have its image replaced for other consumers.
    other = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    material.node_tree.links.new(node.outputs['Color'], other.inputs['Base Color'])
    old_image = node.image
    assert apply_textures(text) == (2, 0)
    assert node.image == old_image
    # Existing alpha follows the new albedo, without changing shared consumers.
    current = shader.inputs['Base Color'].links[0].from_node
    material.node_tree.links.new(current.outputs['Alpha'], shader.inputs['Alpha'])
    records = []
    assert apply_textures(text, records) == (2, 0)
    assert shader.inputs['Alpha'].links[0].from_node.image == shader.inputs['Base Color'].links[0].from_node.image
    # Inject failure after mutations, verifying links, images and image count.
    import delphia_clip.textures as textures
    original_apply = textures._apply_textures
    before_images = {i.as_pointer() for i in bpy.data.images}
    before_nodes = [(n, n.image) for n in material.node_tree.nodes if n.type == 'TEX_IMAGE']
    before_links = {(l.from_socket.as_pointer(), l.to_socket.as_pointer()) for l in material.node_tree.links}
    def fail_after_apply(text, records):
        original_apply(text, records)
        raise RuntimeError('injected failure')
    textures._apply_textures = fail_after_apply
    try:
        apply_textures(text, [])
        raise AssertionError('failure not raised')
    except RuntimeError:
        pass
    finally:
        textures._apply_textures = original_apply
    assert before_images == {i.as_pointer() for i in bpy.data.images}
    assert all(n.image == image for n, image in before_nodes)
    assert before_links == {(l.from_socket.as_pointer(), l.to_socket.as_pointer()) for l in material.node_tree.links}
    # A complex input graph is skipped, not destructively disconnected.
    noise = material.node_tree.nodes.new('ShaderNodeTexNoise')
    material.node_tree.links.new(noise.outputs['Color'], shader.inputs['Base Color'])
    assert apply_textures(text) == (0, 1)
    assert shader.inputs['Base Color'].links[0].from_node == noise
    entry['channels']['albedo']['sha256'] = '0'*64
    try:
        apply_textures(PREFIX + json.dumps(manifest))
        raise AssertionError('bad digest accepted')
    except ValueError:
        pass
    # Reject huge decoded dimensions before Blender attempts allocation.
    import struct
    png_path = Path(folder) / '0.png'
    data = bytearray(png_path.read_bytes())
    data[16:24] = struct.pack('>II', 32768, 32768)
    png_path.write_bytes(data)
    entry['channels']['albedo']['sha256'] = hashlib.sha256(data).hexdigest()
    try:
        apply_textures(PREFIX + json.dumps(manifest))
        raise AssertionError('oversized image accepted')
    except ValueError as exc:
        assert 'safety limit' in str(exc)
delphia_clip.unregister()
print('DELPHIA_TEXTURES_PASS', bpy.app.version_string)

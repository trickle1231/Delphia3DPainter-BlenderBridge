import sys
import json
from pathlib import Path
from types import SimpleNamespace
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
import delphia_clip
from delphia_clip import dialogs
from delphia_clip.material_nodes import node_tree
delphia_clip.register()
wm = bpy.context.window_manager
bpy.types.WindowManager.test_mapping = bpy.props.CollectionProperty(type=dialogs.MappingRow)
a = bpy.data.materials.new('Original')
assert node_tree(a, create=True) is not None
a['delphia_id'] = 'known'
b = bpy.data.materials.new('Manual')
assert node_tree(b, create=True) is not None
payload = dialogs.PREFIX + json.dumps(dict(version=1, materials=[dict(name='Renamed', id='known', channels={'albedo': {}})]))
fake = SimpleNamespace(payload=payload, rows=wm.test_mapping)
dialogs.DELPHIA_OT_mapping.prepare(fake)
row = fake.rows[0]
assert row.material == a and dialogs.status(row, fake.rows) == 'ID Match'
row.material = b
assert dialogs.status(row, fake.rows) == 'Manual Match'
row.material = None
assert dialogs.status(row, fake.rows) == 'Skipped'
row.material = b
other = fake.rows.add()
other.material, other.channel = b, 'albedo'
assert dialogs.status(row, fake.rows) == 'Conflict: Same Material / Channel'
fake.rows.remove(1)
fake.payload = dialogs.PREFIX + json.dumps(dict(version=1, materials=[dict(name='Manual', id='lost', channels={'emission': {}})]))
dialogs.DELPHIA_OT_mapping.prepare(fake)
assert dialogs.status(fake.rows[0], fake.rows) == 'Name Match · Review'
fake.rows[0].material = a
dialogs.remember_mapping(fake.rows, json.loads(fake.payload[len(dialogs.PREFIX):])['materials'], bpy.context.scene)
dialogs.DELPHIA_OT_mapping.prepare(fake)
assert fake.rows[0].material == a and dialogs.status(fake.rows[0], fake.rows) == 'Saved Match'
shader = next(n for n in a.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
noise = a.node_tree.nodes.new('ShaderNodeTexNoise')
a.node_tree.links.new(noise.outputs['Color'], shader.inputs['Base Color'])
assert dialogs.unsupported_reason(a, 'albedo') == 'Channel Uses Non-Image Nodes'
a.node_tree.nodes.remove(noise)
image = bpy.data.images.new('Unrelated unused', width=32, height=32)
image.preview_ensure()
protected = bpy.data.images.new('Protected unused', width=4, height=4)
protected.use_fake_user = True
used = bpy.data.images.new('Used', width=4, height=4)
node = b.node_tree.nodes.new('ShaderNodeTexImage')
node.image = used
dialogs.refresh_unused(wm)
names = {r.image_name for r in wm.delphia_unused}
assert image.name in names and protected.name not in names and used.name not in names
assert bpy.ops.delphia.select_unused_images(select=True) == {'FINISHED'}
assert all(r.selected for r in wm.delphia_unused)
assert bpy.ops.delphia.select_unused_images(select=False) == {'FINISHED'}
assert not any(r.selected for r in wm.delphia_unused)
assert bpy.ops.delphia.select_unused_images(select=True) == {'FINISHED'}
assert bpy.ops.delphia.delete_unused_images() == {'FINISHED'}
assert bpy.data.images.get('Unrelated unused') is None
assert bpy.data.images.get('Protected unused') is not None
assert bpy.data.images.get('Used') is not None
del bpy.types.WindowManager.test_mapping
packed = bpy.data.images.new('Replaced packed', width=4, height=4)
import tempfile
with tempfile.TemporaryDirectory() as folder:
    path = str(Path(folder) / 'packed.png')
    packed.filepath_raw = path
    packed.file_format = 'PNG'
    packed.save()
    bpy.data.images.remove(packed)
    packed = bpy.data.images.load(path)
    packed.name = 'Replaced packed'
    packed.pack()
external = bpy.data.images.new('Replaced unpacked', width=4, height=4)
protected.pack()
used.pack()
records = [(i.name, str(i.as_pointer()), 'Test', 'albedo') for i in (packed, external, protected, used)]
assert dialogs.remove_replaced_packed(records) == 1
assert bpy.data.images.get('Replaced packed') is None
assert bpy.data.images.get('Replaced unpacked') is not None
assert bpy.data.images.get('Protected unused') is not None
assert bpy.data.images.get('Used') is not None
with tempfile.TemporaryDirectory() as folder:
    saved_path = str(Path(folder) / 'mapping.blend')
    bpy.ops.wm.save_as_mainfile(filepath=saved_path)
    bpy.ops.wm.open_mainfile(filepath=saved_path)
    remembered = bpy.context.scene.delphia_saved_mappings
    assert len(remembered) == 1 and remembered[0].target.name == 'Original'
    target = remembered[0].target
    target.name = 'Renamed target'
    assert remembered[0].target.name == 'Renamed target'
    bpy.data.materials.remove(target)
    assert remembered[0].target is None and not remembered[0].unassigned
delphia_clip.unregister()
print('DIALOGS_PASS', bpy.app.version_string)

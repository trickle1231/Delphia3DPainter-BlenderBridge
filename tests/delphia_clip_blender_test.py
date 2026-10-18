"""blender --background --factory-startup --python this_file"""
import sys
import json
import tempfile
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
import delphia_clip
from delphia_clip import transfer

# Redirect both the temporary bridge and clipboard: never overwrite user data.
with tempfile.TemporaryDirectory() as folder:
    captured = []
    original_publish = transfer.publish
    delphia_clip.publish = lambda export, setter, **kwargs: original_publish(export, captured.append, Path(folder) / 'bridge', **kwargs)
    delphia_clip.register()
    bpy.ops.object.select_all(action='DESELECT')
    cube = bpy.data.objects['Cube']
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube
    bpy.ops.object.duplicate()
    other = bpy.context.object
    other.location.x = 3
    cube.select_set(True)
    assert bpy.ops.delphia.copy_models() == {'FINISHED'}
    path = Path(folder) / 'bridge' / 'latest.fbx'
    assert path.read_bytes().startswith(b'Kaydara FBX Binary')
    assert captured and captured[-1].startswith(transfer.PREFIX)
    assert json.loads(captured[-1][len(transfer.PREFIX):])['include_textures'] is False
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 2, len(meshes)
    assert all(len(o.data.uv_layers) for o in meshes)
    assert abs(abs(meshes[0].location.x - meshes[1].location.x) - 3) < 0.001
    delphia_clip.unregister()
print('DELPHIA_CLIP_PASS', bpy.app.version_string)

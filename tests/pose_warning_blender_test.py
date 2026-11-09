"""Background regression: warning gate, current-pose FBX, original preservation."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from types import SimpleNamespace
import tempfile
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
import delphia_clip

delphia_clip.register()
assert not hasattr(bpy.types.Scene, 'delphia_export_rest_pose')
assert not delphia_clip.has_armature()
bpy.ops.object.armature_add()
rig = bpy.context.object
bone = rig.pose.bones[0]
bone.location.x = 2
cube = bpy.data.objects['Cube']
group = cube.vertex_groups.new(name=bone.name)
group.add(list(range(len(cube.data.vertices))), 1, 'REPLACE')
modifier = cube.modifiers.new('Rig', 'ARMATURE')
modifier.object = rig
bpy.ops.object.select_all(action='DESELECT')
cube.select_set(True)
bpy.context.view_layer.objects.active = cube
bpy.context.view_layer.update()
assert delphia_clip.has_armature()  # rig need not be selected
calls = []
delphia_clip.publish = lambda *args, **kwargs: calls.append(True)
assert bpy.ops.delphia.copy_models() == {'CANCELLED'}
assert not calls
# Invoke routes to confirmation, not export; cancellation cannot call publish.
operator = SimpleNamespace(pose_warning_accepted=False)
context = SimpleNamespace(window_manager=SimpleNamespace(
    invoke_props_dialog=lambda op, width: {'RUNNING_MODAL'}))
assert delphia_clip.DELPHIA_OT_copy.invoke(operator, context, None) == {'RUNNING_MODAL'}
assert operator.pose_warning_accepted and not calls
before = tuple(len(c) for c in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.scenes))
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'pose.fbx'
    def publish(export, setter, **kwargs):
        export(path)
    delphia_clip.publish = publish
    assert bpy.ops.delphia.copy_models(pose_warning_accepted=True) == {'FINISHED'}
    assert rig.data.pose_position == 'POSE' and abs(bone.location.x-2) < 1e-6
    assert modifier.object == rig and bpy.context.selected_objects == [cube]
    assert tuple(len(c) for c in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.scenes)) == before
    scene = bpy.data.scenes.new('Verify')
    with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
        bpy.ops.import_scene.fbx(filepath=str(path))
        assert len(scene.objects) == 1
        obj = scene.objects[0]
        center = sum((obj.matrix_world @ v.co).x for v in obj.data.vertices)/len(obj.data.vertices)
        assert abs(center-2) < .001, center
delphia_clip.unregister()
print('POSE_WARNING_PASS', bpy.app.version_string)

import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).parents[1]))
import delphia_clip
import io_scene_fbx.export_fbx_bin as exporter

delphia_clip.register()
source = bpy.data.objects['Cube']
source.location.x = 10
bpy.ops.mesh.primitive_plane_add()
emitter = bpy.context.object
bpy.ops.object.particle_system_add()
settings = emitter.particle_systems[0].settings
settings.type = 'HAIR'
settings.count = 8
settings.render_type = 'OBJECT'
settings.instance_object = source
bpy.context.view_layer.update()
assert sum(i.particle_system is not None for i in bpy.context.evaluated_depsgraph_get().object_instances) > 0
method = exporter.ObjectWrapper.dupli_list_gen
counts = tuple(len(c) for c in (bpy.data.objects, bpy.data.meshes, bpy.data.particles))
with tempfile.TemporaryDirectory() as folder:
    baseline = str(Path(folder)/'baseline.fbx')
    bpy.ops.export_scene.fbx(filepath=baseline, use_selection=True, object_types={'MESH'}, bake_anim=False)
    output = Path(folder)/'filtered.fbx'
    delphia_clip.publish = lambda export, setter, **kwargs: export(output)
    assert bpy.ops.delphia.copy_models() == {'FINISHED'}
    assert exporter.ObjectWrapper.dupli_list_gen is method
    assert emitter.particle_systems[0].settings == settings and settings.count == 8
    assert bpy.context.selected_objects == [emitter]
    assert tuple(len(c) for c in (bpy.data.objects, bpy.data.meshes, bpy.data.particles)) == counts
    sizes = []
    for path in (baseline, str(output)):
        scene = bpy.data.scenes.new('Verify')
        with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
            bpy.ops.import_scene.fbx(filepath=path)
            sizes.append(sum(o.type == 'MESH' for o in scene.objects))
    assert sizes[0] > 1 and sizes[1] == sizes[0], sizes
print('PARTICLE_EXPORT_POLICY_PASS', bpy.app.version_string)

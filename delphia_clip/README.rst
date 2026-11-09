Delphia Clipboard 1.0.2
====================

Installation
------------
Install the versioned ``DelphiaClipboard-<version>.zip`` file as a legacy add-on from Blender Preferences
(Add-ons / Install from Disk; exact wording varies by Blender version).
Enable Delphia Clipboard. In Object Mode select meshes, then use
Object > Copy to Delphia, or search for Copy to Delphia with F3.
In Delphia use File > Open by BlenderClip.
The same model-send button is available in the 3D Viewport N sidebar's
Delphia tab. This integration remains a free feature; no Pro gate is added.

Files containing an armature show a confirmation before export: meshes are
sent in their current pose. Cancel and switch to Rest Position before exporting
if a neutral pose is desired. The bridge never changes pose or creates rest-pose
copies. Only static meshes are transferred, not bones, cameras, lights or animation.
Particles and modifier evaluation follow Blender's FBX exporter behavior under
the bridge's mesh-only, apply-modifiers export options. The bridge does not filter
particle instances or patch the exporter. Particle-generated meshes may be included.

Return textures
---------------
In Delphia use Copy to Blender for the current canvas, or Copy Selected to
Blender in the image export dialog for multiple canvases. Before closing Delphia,
press Update Textures from Delphia in Blender's Delphia sidebar.
If the clipboard has changed, send textures from Delphia again.
This transfers bound Albedo and Emission canvases.
Each successful send replaces this Delphia instance's previous transfer;
normal application shutdown removes it. Crashes can leave temporary files.

Sending meshes does not modify materials, nodes, slots or custom properties.
Existing delphia_id custom properties are read if present.
The name-to-ID map travels with the model and is retained in DPP projects.
Existing IDs are not regenerated on export. Texture Mapping offers ID or name
matches for review and allows explicit material selection or Unassigned.
Missing materials are not created automatically.
Keep the original Blender scene for material matching.

The active Material Output must connect directly to a Principled shader.
Base Color and Emission / Emission Color are detected by socket name for
different Blender versions. Existing direct image nodes are reused; shared
nodes are separated before assigning a new image. Other shader graphs are
skipped, not deleted. Existing image source files are never overwritten.
Imported images are sRGB and packed in the .blend (save the .blend to persist).
Albedo-image Alpha is connected when the shader Alpha input is unlinked or
already uses that image node's Alpha; unrelated Alpha connections are preserved.
Material transparency/render settings are not changed automatically.
No shader baking or emission-strength synchronization
is performed; an unlinked zero emission strength is raised to one.
UV transforms already present on a reused node are preserved. Delphia-only
UV offset/scale changes are not transferred by this first protocol version.
Save the Blender project before applying updates to keep a recovery copy.
To replace the current project's model, use File > Replace Current Project
Model > BlenderClip. The local-file replacement remains available separately.

Website distribution
--------------------
This ZIP is a source distribution under GPL-3.0-or-later. Keep LICENSE.txt,
COPYING.txt, the Python source files and this README together when publishing.
Do not describe the add-on as proprietary or forbid its modification or
redistribution. A download price does not remove recipients' GPL rights.
The independent Delphia application's commercial terms are separate.
No Blender Extensions upload or extension manifest is needed for this legacy
add-on package. Blender 4.2+ users should choose Install from Disk.
This integration is not endorsed by the Blender Foundation.

Compatibility
-------------
Targets Blender 3.3 and later with the bundled FBX exporter. Optional export
properties are detected through RNA; required properties are checked before
exporting. Runtime tests currently pass on Blender 3.6.23, 4.2.8 LTS, 4.5.0
and 5.0.0 (model transfer, texture import, mapping and cleanup). The bridge
does not read Material.use_nodes, which Blender plans to remove in 6.0; its
pre-5.0 fallback uses the property only when a material has no node tree.
Blender 6.x still requires runtime testing before it is declared supported.
This is a legacy add-on ZIP, not an Extensions repository package.

Selected mesh objects are exported with modifiers, UVs, material assignments,
and transforms, including all vertex color sets. Animation and rigs are not exported.
Image textures are never packed or copied with the model. The standard FBX
exporter can retain texture path references, but Delphia does not load them
automatically. Materials and node connections are not modified.
Use Copy Texture in the sidebar to preview material images from selected objects.
Each row has a Copy button which copies one image to the system clipboard;
paste it using Delphia's existing layer-panel image paste command.
This uses Blender's native image clipboard operator and requires a Blender/platform
combination that supports it. There is no shader baking or multi-image copy.
For standalone FBX/OBJ files, use Import Model Texture in Delphia's bottom
layer-panel dropdown. Select one image to add a canvas-sized top-level layer.
Original model textures are not cached in Delphia or stored separately in DPP;
only the imported layer is saved. Use the model file again for another import.
No clipboard paste shortcut is overridden. Delphia opens a new model using
its existing save-confirmation/import workflow, not an append operation.

Transport and cleanup
---------------------
The OS temporary folder's DelphiaBlenderClip-v1 directory retains latest.fbx
and one tiny writer.lock file. Export uses a private pending directory;
failure preserves the last successful export. Clipboard publication failure
restores the previous model. OS locking serializes Blender writers. Previous
and pending crash leftovers are reconciled on the next export. A stale
clipboard reference is rejected by size and SHA-256 checks.

Delphia copies the verified FBX into an owned QTemporaryDir before importing.
The latest successful BlenderClip import is retained for the application
session, so another Blender export cannot overwrite the project's source.
Normal shutdown removes that workspace. An abnormal Delphia termination can
leave its import workspace behind; it is intentionally not swept while other
Delphia instances may be using it. Save a DPP for permanent storage.

Tests
-----
python -B tests/delphia_clip_test.py
blender --background --factory-startup --python-exit-code 1 --python tests/delphia_clip_blender_test.py

Tests use isolated temporary directories and do not overwrite the real bridge
clipboard or user preferences. Delphia's blender_clip CTest must be built and
run separately; source inspection alone is not an end-to-end integration test.
Material mapping and unused images
---------------------------------

Texture Mapping opens with Texture / Material / Status columns so users can
review ID matches, name suggestions, and remembered manual assignments.
Choose any local material manually, or Unassigned to skip. Conflicting assignments
to the same material/channel and unsupported node graphs block application.
Cancelling the mapping dialog leaves the materials unchanged. Transfer files must
remain available until application finishes.

Manual assignments are remembered in the scene; save the .blend to retain them.
Remove Replaced Images (Packed Only) is off by default and optionally removes
unused replaced packed images. Fake User and linked-library images are protected.

The sidebar's Unused Images button opens the cleanup popup.
It lists unused images from the entire Blender project, with a large preview of
the active entry. Select checkboxes and Delete Selected to remove image datablocks
after confirmation. Source files are never deleted. Usage is checked again at
deletion time. Fake User and linked-library images are shown but protected.
Closing the popup does not undo an already confirmed deletion; use Blender Undo.
The add-on UI is English.

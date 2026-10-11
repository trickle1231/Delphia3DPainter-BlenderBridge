Delphia Clipboard 1.1
====================

Installation
------------
Install DelphiaClipboard.zip as a legacy add-on from Blender Preferences
(Add-ons / Install from Disk; exact wording varies by Blender version).
Enable Delphia Clipboard. In Object Mode select meshes, then use
Object > Copy to Delphia, or search for Copy to Delphia with F3.
In Delphia use File > Open by BlenderClip.
The same model-send button is available in the 3D Viewport N sidebar's
Delphia tab. This integration remains a free feature; no Pro gate is added.

Return textures
---------------
In Delphia choose File > Send Textures to Blender. Before closing Delphia,
press Update Textures from Delphia in Blender's Delphia sidebar. Alternatively
use Import Texture Manifest and select manifest.json in the temporary
DelphiaTextures-* directory. This transfers bound Albedo and Emission canvases.
Each successful send replaces this Delphia instance's previous transfer;
normal application shutdown removes it. Crashes can leave temporary files.

Sending meshes assigns local editable materials a delphia_id custom property.
The name-to-ID map travels with the model and is retained in DPP projects.
When an ID is duplicated, an exact material name must disambiguate it; existing
IDs are not regenerated on export. Only transfers without IDs
fall back to an exact material name. Missing materials are skipped, not created.
Keep the original Blender scene, or save it to preserve these material IDs.

The active Material Output must connect directly to a Principled shader.
Base Color and Emission / Emission Color are detected by socket name for
different Blender versions. Existing direct image nodes are reused; shared
nodes are separated before assigning a new image. Other shader graphs are
skipped, not deleted. Existing image source files are never overwritten.
Imported images are sRGB and packed in the .blend (save the .blend to persist).
An existing direct Albedo-image Alpha connection to the same shader is updated
alongside color; unrelated Alpha connections are preserved. No shader baking or emission-strength synchronization
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
exporting. Only Blender 4.2.8 LTS has been runtime-tested in this workspace.
No claim of testing every 3.x/4.x/5.x version. This is a legacy add-on ZIP,
not an Extensions repository package.

Selected mesh objects are exported with modifiers, UVs, material assignments,
and transforms. Animation and rigs are not exported. FBX-supported image
textures are embedded. Procedural shader graphs are not baked or reproduced.
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
Replacement review
------------------

After texture assignment, Replaced Textures opens a scrollable list of the old
images. Select unused images and confirm to remove their Blender datablocks;
source files on disk are never deleted. Images still used elsewhere, linked
library images and Fake User images are protected. Nothing is selected by
default. Cancel keeps all images. The Delphia sidebar can reopen the accumulated
replacement list. This review list is temporary and is not saved in the blend.


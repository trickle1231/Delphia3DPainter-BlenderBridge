# Delphia Blender Bridge

Send selected Blender meshes to **Delphia 3D Painter**, paint your textures, and bring them back into your Blender materials.

The add-on appears in Blender as **Delphia Clipboard**. The bridge is available with both Lite and Pro.

[Official website](https://delphia3dpainter.com/) · [Downloads](https://delphia3dpainter.com/downloads) · [Painter documentation](https://trickle1231.github.io/Delphia3DPainter-releases/)

## Install

1. Download the packaged **`DelphiaClipboard-<version>.zip`**. Use the add-on ZIP, not GitHub's **Source code** ZIP.
2. In Blender, open **Edit → Preferences → Add-ons**.
3. Choose **Install from Disk** (or **Install**, depending on your Blender version), then select the ZIP without extracting it.
4. Enable **Delphia Clipboard**.
5. In the 3D Viewport, press **N** and open the **Delphia** tab.

This is a legacy add-on ZIP, not a Blender Extensions repository package. The add-on targets Blender **3.3+** with its bundled FBX exporter; this does not imply every later Blender release has been tested. See [compatibility and technical notes](delphia_clip/README.rst) for recorded test versions.

## Quick start

1. **Blender:** In Object Mode, select the mesh objects to paint and click **Copy to Delphia**.
2. **Delphia:** Choose **File → Open → Open by BlenderClip** and complete the model import.
3. Paint your textures in Delphia.
4. **Delphia:** Click **Copy to Blender** for the current canvas. For multiple canvases, use **Copy Selected to Blender** in the image export dialog.
5. **Blender:** Click **Update Textures from Delphia**, review the **Texture Mapping** dialog, and confirm.
6. **Save your `.blend` file.** Imported textures are packed automatically, but saving is required to keep them on disk.

> Keep Delphia open until Blender has finished importing the textures. The clipboard contains a reference to temporary transfer files, not a permanent project backup.

## Send a model to Delphia

**Copy to Delphia** is available in the Delphia sidebar, the **Object** menu, and **F3** search. It requires **Object Mode** and at least one selected mesh.

| Included | Not transferred |
| --- | --- |
| Selected meshes, evaluated modifiers, UVs, transforms, material assignments, and vertex color sets | Bones, animation, cameras, lights, and complete shader graphs |

- The export does not modify your original materials, nodes, material slots, or custom properties.
- Models are transferred as static geometry. If the file contains an armature, a confirmation warns that meshes will be exported in their **current pose**. Cancel and switch the armature to **Rest Position** first if you want a neutral pose. The bridge does not change the pose for you.
- Particle-generated geometry follows Blender's FBX exporter behavior; it is not separately filtered by the bridge.
- Image textures are **not bundled with the model** or automatically loaded into Delphia. Use **Copy Texture** below to bring in an existing image separately.
- Opening a BlenderClip uses Delphia's normal new-model workflow; it does not append the model to the current scene. Save your current project when prompted.
- To replace an existing project's model instead, use **File → Replace Current Project Model → BlenderClip** in Delphia. Save a backup before replacing geometry or changing UVs.

Keep the original Blender scene for the return trip. Save a **DPP** project in Delphia for permanent storage; the bridge clipboard is not a substitute for saving.

## Copy an existing Blender texture to Delphia

1. Select the objects whose material images you want to inspect.
2. Click **Copy Texture** in the Delphia sidebar.
3. Preview the images and click the desired image's **Copy** button.
4. In Delphia, use the layer panel's image paste command.

This copies **one image at a time**, not the evaluated appearance of a material. Procedural shaders are not baked. It uses Blender's native image clipboard support, which must be available in your Blender/platform combination.

## Bring painted textures back to Blender

The bridge updates **Albedo / Base Color** and **Emission** textures. It does not transfer Delphia's editable layer stack or automatically synchronize changes continuously: send and import again whenever you want an update.

### Review material mapping

**Update Textures from Delphia** opens **Texture Mapping** with the source project, send time, and a row for each texture/channel.

- Check each row's **Material** and **Status** before confirming.
- Existing bridge IDs can identify materials. Names can provide suggested matches, but review them—especially after renaming or duplicating materials.
- Choose a different local material manually if needed, or **Unassigned** to skip a texture.
- Manual choices are remembered in the Blender scene. Save the `.blend` to retain them.
- Two textures cannot target the same material/channel in one update. Resolve conflicting assignments and unsupported materials before applying.
- Cancelling the dialog leaves your materials unchanged. Missing materials are not created automatically.

### Supported material setup

Use a **Principled BSDF connected directly to the active Material Output**. The target Base Color or Emission input must be unlinked or connected directly to an Image Texture node. More complex graphs are not automatically baked or replaced; the mapping dialog reports unsupported targets.

- A compatible image node is reused, or a new one is created when needed. Shared connections are handled without replacing unrelated image users.
- Imported images use **sRGB** and are **packed into the `.blend`**. Original texture files on disk are not overwritten.
- For Albedo, the Image Texture's **Alpha** output is connected to the Principled shader's **Alpha** input if that input is unlinked or already uses this texture's alpha. A custom Alpha connection is preserved.
- The bridge does not automatically change Blender's material transparency/render settings. If transparent pixels do not display as expected, check those settings for your Blender version and render engine.
- Emission strength is not synchronized from Delphia. An unlinked strength of zero is raised to one so the imported emission can contribute.
- Existing vector/UV connections on reused image nodes are preserved. Delphia-only UV offset/scale adjustments are not transferred.

Save the Blender project before updating if you want a recovery copy, and save again after checking the result.

## Clean up unused images

Repeated texture updates can leave old images in the Blender project.

- **Remove Replaced Images (Packed Only)** in Texture Mapping is optional and off by default. It removes replaced packed images only when they are unused and eligible for deletion.
- **Unused Images · count** in the sidebar opens a project-wide list—not just images imported by Delphia. Preview entries, select the ones you no longer need, and choose **Delete Selected** to confirm.
- Usage is checked again before deletion. **Fake User** and linked-library images are protected.
- These operations remove Blender image datablocks, **not source files on disk**.
- Closing the cleanup dialog does not reverse confirmed deletions. Use Blender Undo if needed.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Copy to Delphia is unavailable | Switch to Object Mode and select at least one mesh. |
| The Delphia tab is missing | Enable Delphia Clipboard in Preferences, then press N in the 3D Viewport. |
| Clipboard does not contain a valid transfer | Repeat the appropriate send action, then import immediately. Copying text, images, or another model can replace the clipboard reference. |
| A texture transfer is missing or expired | Keep Delphia open and send again. A new send replaces that Delphia instance's previous texture transfer; normal shutdown removes it. |
| Textures target the wrong material | Review Texture Mapping and select the intended local material manually. |
| A material is unsupported | Check the direct Principled BSDF → Material Output connection and the target image input. Complex shader graphs are not baked. |
| The model arrived without its existing textures | This is expected. Model transfer does not include image files; use Copy Texture separately. |
| Imported textures disappear after reopening Blender | Confirm that you saved the `.blend` after import. |

The sidebar's **Help · EN / JP / KR** button provides a short guide in English, Japanese, and Korean. Most add-on controls are in English.

## License

The add-on is distributed under **GPL-3.0-or-later**. See [LICENSE.txt](delphia_clip/LICENSE.txt) and [COPYING.txt](delphia_clip/COPYING.txt). Delphia 3D Painter's application license is separate. This integration is not endorsed by the Blender Foundation.

For implementation details and test commands, see the [technical README](delphia_clip/README.rst).

# SPDX-License-Identifier: GPL-3.0-or-later
"""Import packed images without deleting user shader graphs or source files."""
import hashlib
import json
import struct
from pathlib import Path
import tempfile
import bpy

PREFIX = 'DELPHIA_TEXTURE_CLIP_V1\n'


def apply_textures(text, replaced=None):
    # Keep originals alive until the entire operation commits. Restore existing
    # node objects (rather than swapping node trees) so external references survive.
    states = []
    for mat in bpy.data.materials:
        if mat.library:
            continue
        tree = mat.node_tree
        nodes = list(tree.nodes) if tree else []
        states.append((mat, mat.use_nodes, nodes,
                       [(n, n.image, n.label) for n in nodes if n.type == 'TEX_IMAGE'],
                       [(l.from_socket, l.to_socket) for l in tree.links] if tree else [],
                       [(s, s.default_value) for n in nodes if n.type == 'BSDF_PRINCIPLED'
                        for s in n.inputs if s.name == 'Emission Strength']))
    images = {i.as_pointer() for i in bpy.data.images}
    records = []
    try:
        result = _apply_textures(text, records)
    except Exception:
        for mat, enabled, nodes, old_images, links, strengths in states:
            tree = mat.node_tree
            if tree:
                tree.links.clear()
                for node in list(tree.nodes):
                    if node not in nodes:
                        tree.nodes.remove(node)
                for node, image, label in old_images:
                    node.image, node.label = image, label
                for source, target in links:
                    tree.links.new(source, target)
                for socket, value in strengths:
                    socket.default_value = value
            mat.use_nodes = enabled
        for image in list(bpy.data.images):
            if image.as_pointer() not in images and image.users == 0:
                bpy.data.images.remove(image)
        raise
    if replaced is not None:
        replaced.extend(records)
    else:
        for name, identity, _, _ in records:
            image = bpy.data.images.get(name)
            if image and str(image.as_pointer()) == identity and image.get('delphia_owned') and image.users == 0:
                bpy.data.images.remove(image)
    return result


def _apply_textures(text, replaced):
    if len(text) > 4 * 1024 * 1024 or not text.startswith(PREFIX):
        raise ValueError('Copy textures from Delphia first')
    manifest = json.loads(text[len(PREFIX):])
    if manifest.get('version') != 1:
        raise ValueError('Unsupported texture clipboard version')
    root = Path(manifest['directory'])
    if (root.parent.resolve() != Path(tempfile.gettempdir()).resolve()
            or not root.name.startswith('DelphiaTextures-') or root.is_symlink()):
        raise ValueError('Invalid texture transfer directory')
    entries = manifest['materials']
    if not isinstance(entries, list) or len(entries) > 4096:
        raise ValueError('Invalid material list')
    # Validate every file before touching the user's scene. Retain bytes while
    # loading, so a concurrently replaced transfer cannot change packed data.
    files = {}
    total_bytes = 0
    decoded_bytes = 0
    for entry in entries:
        for channel, info in entry['channels'].items():
            if channel not in ('albedo', 'emission'):
                raise ValueError('Unsupported channel')
            name = info['file']
            if Path(name).name != name or not name.endswith('.png'):
                raise ValueError('Invalid image filename')
            path = root / name
            if path.is_symlink() or path.resolve().parent != root.resolve() or path.stat().st_size > 512*1024*1024:
                raise ValueError('Invalid image path or size')
            data = path.read_bytes()
            total_bytes += len(data)
            if total_bytes > 1024*1024*1024:
                raise ValueError('Texture transfer exceeds the memory safety limit')
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(data).hexdigest() != info['sha256']:
                raise ValueError('Texture transfer is missing or changed; send again')
            if len(data) < 33 or data[12:16] != b'IHDR':
                raise ValueError('Could not decode texture')
            width, height = struct.unpack('>II', data[16:24])
            decoded_bytes += width * height * 16
            if not width or not height or max(width, height) > 16384 or decoded_bytes > 1024*1024*1024:
                raise ValueError('Texture transfer exceeds the memory safety limit')
            files[name] = data
    # Decode all inputs before changing material links.
    with tempfile.TemporaryDirectory(prefix='DelphiaTextureRead-') as folder:
        for name, data in files.items():
            path = Path(folder) / name
            path.write_bytes(data)
            probe = bpy.data.images.load(str(path), check_existing=False)
            try:
                if probe.size[0] <= 0 or probe.size[1] <= 0:
                    raise ValueError('Could not decode texture')
            finally:
                bpy.data.images.remove(probe)
    applied = skipped = 0
    for entry in entries:
        identity = entry.get('id', '')
        matches = [m for m in bpy.data.materials if m.get('delphia_id') == identity] if identity else []
        if len(matches) > 1:
            matches = [m for m in matches if m.name == entry['name']]
        if not identity:
            matches = [m for m in bpy.data.materials if m.name == entry['name']]
        if len(matches) != 1 or matches[0].library:
            skipped += 1
            continue
        material = matches[0]
        if not material.use_nodes:
            material.use_nodes = True
        tree = material.node_tree
        outputs = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output]
        if len(outputs) != 1 or len(outputs[0].inputs['Surface'].links) != 1:
            skipped += 1
            continue
        shader = outputs[0].inputs['Surface'].links[0].from_node
        if shader.type != 'BSDF_PRINCIPLED':
            skipped += 1
            continue
        targets = {}
        for channel in entry['channels']:
            socket = shader.inputs.get('Base Color' if channel == 'albedo' else 'Emission Color')
            if socket is None and channel == 'emission':
                socket = shader.inputs.get('Emission')
            if socket is None or (socket.is_linked and socket.links[0].from_node.type != 'TEX_IMAGE'):
                targets = {}
                break
            targets[channel] = socket
        if not targets:
            skipped += 1
            continue
        for channel, socket in targets.items():
            info = entry['channels'][channel]
            # Reuse the connected image node but never overwrite its old image
            # datablock: it may also be used by an unrelated material.
            node = socket.links[0].from_node if socket.is_linked else tree.nodes.new('ShaderNodeTexImage')
            previous = node.image
            alpha = shader.inputs.get('Alpha')
            update_alpha = (channel == 'albedo' and alpha is not None and alpha.is_linked
                            and alpha.links[0].from_socket == node.outputs['Alpha'])
            shared_alpha = any(not update_alpha or link.to_socket != alpha for link in node.outputs['Alpha'].links)
            if len(node.outputs['Color'].links) > 1 or shared_alpha:
                original = node
                node = tree.nodes.new('ShaderNodeTexImage')
                node.interpolation = original.interpolation
                node.extension = original.extension
                node.projection = original.projection
                node.projection_blend = original.projection_blend
                if original.inputs['Vector'].is_linked:
                    tree.links.new(original.inputs['Vector'].links[0].from_socket, node.inputs['Vector'])
            old = node.image
            # Load from an isolated file to avoid race-with-export; pack before
            # the temporary file is removed. No source texture is overwritten.
            with tempfile.TemporaryDirectory(prefix='DelphiaTextureRead-') as folder:
                path = Path(folder) / 'image.png'
                path.write_bytes(files[info['file']])
                image = bpy.data.images.load(str(path), check_existing=False)
                image.name = 'Delphia ' + material.name + ' ' + channel
                image.colorspace_settings.name = 'sRGB'
                image.pack()
            image['delphia_owned'] = True
            node.image = image
            node.label = 'Delphia ' + channel
            tree.links.new(node.outputs['Color'], socket)
            if update_alpha:
                tree.links.new(node.outputs['Alpha'], alpha)
            if channel == 'emission':
                strength = shader.inputs.get('Emission Strength')
                if strength is not None and not strength.is_linked and strength.default_value == 0:
                    strength.default_value = 1
            if replaced is not None and previous:
                replaced.append((previous.name, str(previous.as_pointer()), material.name, channel))
            elif old and old.get('delphia_owned') and old.users == 0:
                bpy.data.images.remove(old)
            applied += 1
    return applied, skipped

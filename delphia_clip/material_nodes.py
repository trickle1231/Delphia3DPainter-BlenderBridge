# SPDX-License-Identifier: GPL-3.0-or-later
"""Bridge Blender's pre-5.0 optional and post-5.0 mandatory material nodes."""
import bpy


def node_usage_state(material):
    return material.use_nodes if bpy.app.version < (5, 0, 0) else None


def node_tree(material, create=False):
    """Return a material node tree without reading deprecated ``use_nodes``."""
    if create and bpy.app.version < (5, 0, 0):
        material.use_nodes = True
    tree = material.node_tree
    if tree is not None or not create:
        return tree
    # Blender 3.x/4.x creates the default node tree through this legacy switch.
    # Blender 5+ creates it with the material, so this branch is not reached;
    # Blender 6 can remove the property without affecting the bridge.
    try:
        material.use_nodes = True
    except (AttributeError, TypeError):
        return None
    return material.node_tree


def restore_pre_node_material(material, had_node_tree, use_nodes=None):
    """Undo a failed pre-5.0 node-tree creation when Blender permits it."""
    if use_nodes is not None:
        material.use_nodes = use_nodes
        return
    if had_node_tree or material.node_tree is None:
        return
    try:
        material.use_nodes = False
    except (AttributeError, TypeError):
        pass

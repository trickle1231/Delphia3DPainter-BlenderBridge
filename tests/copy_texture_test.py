"""Pure discovery regression tests; no Blender or clipboard writes."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

source = Path(__file__).parents[1] / 'delphia_clip' / 'copy_texture.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
namespace = {}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
    and n.name == 'material_images'], type_ignores=[]), str(source), 'exec'), namespace)


class Data:
    def __init__(self, **values):
        self.__dict__.update(values)

    def as_pointer(self):
        return id(self)


class DiscoveryTest(unittest.TestCase):
    def test_same_names_and_cyclic_groups(self):
        first = Data(name='Color', source='FILE', library=NS(filepath='a.blend'))
        second = Data(name='Color', source='FILE', library=NS(filepath='b.blend'))
        graph = Data(nodes=[])
        graph.nodes = [NS(type='TEX_IMAGE', image=first), NS(type='TEX_IMAGE', image=second),
                       NS(type='TEX_IMAGE', image=first), NS(type='GROUP', node_tree=graph)]
        context = NS(selected_objects=[NS(material_slots=[NS(material=NS(node_tree=graph))])])
        self.assertEqual(namespace['material_images'](context), [first, second])

    def test_no_materials(self):
        self.assertEqual(namespace['material_images'](NS(selected_objects=[NS()])), [])


if __name__ == '__main__':
    unittest.main()

"""Run with Python; transport does not require Blender."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('transfer', Path(__file__).parents[1] / 'delphia_clip' / 'transfer.py')
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)


class TransferTest(unittest.TestCase):
    def test_size_limit_preserves_previous_transfer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            transfer.publish(lambda p: p.write_bytes(b'old'), lambda _: None, root)
            limit = transfer.MAX_MODEL_BYTES
            try:
                transfer.MAX_MODEL_BYTES = 4
                with self.assertRaisesRegex(RuntimeError, '512 MiB'):
                    transfer.publish(lambda p: p.write_bytes(b'large'), lambda _: None, root)
                self.assertEqual((root / 'latest.fbx').read_bytes(), b'old')
            finally:
                transfer.MAX_MODEL_BYTES = limit

    def test_replace_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'bridge'
            clipboard = []
            transfer.publish(lambda p: p.write_bytes(b'first'), clipboard.append, root)
            self.assertTrue(json.loads(clipboard[-1][len(transfer.PREFIX):])['include_textures'])
            transfer.publish(lambda p: p.write_bytes(b'second'), clipboard.append, root, addon_version='1.0.1', include_textures=False)
            self.assertEqual((root / 'latest.fbx').read_bytes(), b'second')
            payload = json.loads(clipboard[-1][len(transfer.PREFIX):])
            self.assertEqual(payload['size'], 6)
            self.assertEqual(payload['version'], 1)
            self.assertEqual(payload['addon_version'], '1.0.1')
            self.assertFalse(payload['include_textures'])
            def fail(_):
                raise RuntimeError('test failure')
            with self.assertRaises(RuntimeError):
                transfer.publish(fail, clipboard.append, root)
            self.assertEqual((root / 'latest.fbx').read_bytes(), b'second')
            with self.assertRaises(RuntimeError):
                transfer.publish(lambda p: p.write_bytes(b'third'), fail, root)
            self.assertEqual((root / 'latest.fbx').read_bytes(), b'second')
            self.assertEqual(set(p.name for p in root.iterdir()), {'latest.fbx', 'writer.lock'})

    def test_crash_leftovers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'previous.fbx').write_bytes(b'previous')
            (root / 'pending').mkdir()
            (root / 'pending' / 'incomplete').write_bytes(b'x')
            def fail(_):
                raise RuntimeError('test failure')
            with self.assertRaises(RuntimeError):
                transfer.publish(fail, lambda _: None, root)
            self.assertEqual((root / 'latest.fbx').read_bytes(), b'previous')
            self.assertFalse((root / 'pending').exists())


if __name__ == '__main__':
    unittest.main()

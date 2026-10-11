# SPDX-License-Identifier: GPL-3.0-or-later
# This add-on is distributed without warranty; see COPYING.txt and LICENSE.txt.
"""Private, bounded clipboard transport; no Blender dependency."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from contextlib import contextmanager

PREFIX = 'DELPHIA_BLENDER_CLIP_V1\n'


@contextmanager
def writer_lock(root):
    # OS releases the lock even on a crash. Multiple Blender instances cannot
    # replace each other's pending export or restore the wrong previous file.
    with (root / 'writer.lock').open('a+b') as lock:
        if lock.seek(0, 2) == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def publish(export, set_clipboard, root=None, materials=None):
    root = Path(root) if root is not None else Path(tempfile.gettempdir()) / 'DelphiaBlenderClip-v1'
    if root.is_symlink() or root.resolve() != root.absolute():
        raise RuntimeError('Clipboard directory must not be a symbolic link')
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    with writer_lock(root):
        pending = root / 'pending'
        latest = root / 'latest.fbx'
        backup = root / 'previous.fbx'
        # Exact private targets only; never follow a directory link for cleanup.
        if any(p.is_symlink() or p.resolve() != p for p in (pending, latest, backup)):
            raise RuntimeError('Unexpected symbolic link in clipboard directory')
        if backup.exists():
            if not latest.exists():
                os.replace(backup, latest)
            else:
                backup.unlink()
        if pending.exists():
            shutil.rmtree(pending)
        pending.mkdir()
        try:
            model = pending / 'model.fbx'
            export(model)
            if not model.is_file() or model.stat().st_size == 0:
                raise RuntimeError('Exporter did not create a model')
            with model.open('rb') as stream:
                sha = hashlib.sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    sha.update(block)
            payload = PREFIX + json.dumps(dict(version=1, format='fbx', path=str(latest),
                                               sha256=sha.hexdigest(), size=model.stat().st_size,
                                               materials=materials or {}))
            if len(payload) > 16384 or model.stat().st_size > 2*1024*1024*1024:
                raise RuntimeError('Model transfer exceeds the safety limit')
            if latest.exists():
                os.replace(latest, backup)
            try:
                os.replace(model, latest)
                set_clipboard(payload)
            except Exception:
                if latest.exists():
                    latest.unlink()
                if backup.exists():
                    os.replace(backup, latest)
                raise
            if backup.exists():
                backup.unlink()
            return payload
        finally:
            if pending.exists():
                shutil.rmtree(pending)

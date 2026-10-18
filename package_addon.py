"""Build the installable Blender add-on ZIP using the add-on's declared version."""

from __future__ import annotations

import ast
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ADDON_DIR = ROOT / "delphia_clip"
INIT_FILE = ADDON_DIR / "__init__.py"


def addon_version() -> str:
    tree = ast.parse(INIT_FILE.read_text(encoding="utf-8"), filename=str(INIT_FILE))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets):
            continue
        info = ast.literal_eval(node.value)
        version = info.get("version")
        if isinstance(version, tuple) and all(isinstance(part, int) for part in version):
            return ".".join(map(str, version))
    raise RuntimeError("Could not read bl_info['version'] from delphia_clip/__init__.py")


def main() -> None:
    version = addon_version()
    archive = ROOT / f"DelphiaClipboard-{version}.zip"
    pending = archive.with_suffix('.zip.pending')
    sources = [source for source in sorted(ADDON_DIR.rglob('*'))
               if source.is_file() and '__pycache__' not in source.parts]
    with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for source in sources:
            output.write(source, source.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(pending) as check:
        if check.testzip() is not None:
            raise RuntimeError('Invalid add-on archive')
        for source in sources:
            if check.read(source.relative_to(ROOT).as_posix()) != source.read_bytes():
                raise RuntimeError('Archive does not match source: ' + str(source))
    pending.replace(archive)
    print(archive)


if __name__ == "__main__":
    main()

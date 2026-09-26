#!/usr/bin/env python3
"""Create a Chrome Web Store ZIP with the extension files at archive root."""

from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile


source = Path(sys.argv[1]).resolve()
archive = Path(sys.argv[2]).resolve()
files = [source / "manifest.json", source / "background.js"]
files.extend(sorted((source / "icons").glob("*.png")))

with ZipFile(archive, "w", compression=ZIP_DEFLATED) as package:
    for path in files:
        package.write(path, path.relative_to(source))

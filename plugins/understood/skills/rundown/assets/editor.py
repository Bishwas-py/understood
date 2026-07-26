#!/usr/bin/env python3
"""Print the URL scheme prefix for the editor installed on this machine.

    $ ./editor.py
    cursor://file

Cursor first, VS Code as fallback, because a machine with both is almost always
someone who moved to Cursor and kept VS Code around. Add ":line" to a file's
absolute path to build a link:

    cursor://file/Users/me/project/app/main.go:135

Exits 1 and prints nothing to stdout when neither is found, so a caller can tell
the difference between "use vscode" and "do not write links at all".
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# (name, scheme prefix, macOS app bundle, CLI names, Windows dir fragments)
EDITORS = [
    ("Cursor", "cursor://file", "Cursor.app", ("cursor",), ("Cursor",)),
    ("VS Code", "vscode://file", "Visual Studio Code.app", ("code", "code-insiders"), ("Microsoft VS Code",)),
]


def installed(app: str, clis: tuple[str, ...], win_dirs: tuple[str, ...]) -> bool:
    if any(shutil.which(c) for c in clis):
        return True
    if sys.platform == "darwin":
        for base in ("/Applications", Path.home() / "Applications"):
            if (Path(base) / app).exists():
                return True
    elif sys.platform.startswith("win"):
        for var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            root = os.environ.get(var)
            if root and any((Path(root) / "Programs" / d).exists() or (Path(root) / d).exists() for d in win_dirs):
                return True
    else:
        # Linux: desktop entries, flatpak, and the usual snap/bin locations are
        # all covered by `which` above for the CLI, this catches GUI-only installs.
        for d in ("/usr/share/applications", Path.home() / ".local/share/applications"):
            p = Path(d)
            if p.is_dir() and any(app.split(".")[0].lower() in f.name.lower() for f in p.iterdir()):
                return True
    return False


def main() -> int:
    for name, scheme, app, clis, win_dirs in EDITORS:
        if installed(app, clis, win_dirs):
            print(scheme)
            print(f"{name} found", file=sys.stderr)
            return 0
    print("no supported editor found: links would be inert", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

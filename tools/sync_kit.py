#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Copy the kit into an app, byte for byte, with a MANIFEST of hashes.

    python3 tools/sync_kit.py ~/Projects/SbAe9-SBC ~/Projects/SbAe9-AudioMon

Replaces <app>/sbae9kit/ with this repo's sbae9kit/ and writes
<app>/sbae9kit/MANIFEST (kit version, this repo's commit, a sha256 per
file). The app's tests check the copy against it (sbae9kit.vendor.verify),
so the kit is only ever changed here.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sbae9kit import KIT_VERSION, vendor  # noqa: E402

SRC = os.path.join(ROOT, "sbae9kit")


def commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "describe", "--always", "--dirty"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def sync(app):
    dest = os.path.join(app, "sbae9kit")
    tmp = dest + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for name in vendor.files(SRC):
        shutil.copy2(os.path.join(SRC, name), tmp)
    with open(os.path.join(tmp, "MANIFEST"), "w") as f:
        f.write("# sbae9kit, vendored from SbAe9-Kit by tools/sync_kit.py. Don't edit here.\n")
        f.write(f"kit {KIT_VERSION}\ncommit {commit()}\n")
        for name in vendor.files(tmp):
            f.write(f"{name} {vendor.digest(os.path.join(tmp, name))}\n")
    shutil.rmtree(dest, ignore_errors=True)
    os.rename(tmp, dest)
    problems = vendor.verify(dest)
    print(f"{dest}: kit {KIT_VERSION} ({commit()})" + (f", PROBLEMS: {problems}" if problems else ""))
    return not problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(0 if all(sync(os.path.abspath(a)) for a in sys.argv[1:]) else 1)

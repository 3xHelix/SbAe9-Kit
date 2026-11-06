# SPDX-License-Identifier: GPL-2.0-only
"""Is this vendored copy of the kit exactly what SbAe9-Kit shipped?

tools/sync_kit.py writes MANIFEST (kit version, source commit, a sha256 per
file). An app's test calls verify(): any edit made in the app's copy, rather
than in SbAe9-Kit, shows up as a mismatch.
"""

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {"MANIFEST", "__pycache__"}


def files(folder=HERE):
    return sorted(n for n in os.listdir(folder)
                  if n not in SKIP and n.endswith(".py") and os.path.isfile(os.path.join(folder, n)))


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_manifest(folder=HERE):
    out = {}
    with open(os.path.join(folder, "MANIFEST")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition(" ")
                out[key] = value.strip()
    return out


def verify(folder=HERE):
    """[] if the copy matches its MANIFEST, else what's wrong."""
    try:
        man = read_manifest(folder)
    except OSError:
        return ["no MANIFEST: copy the kit with SbAe9-Kit's tools/sync_kit.py"]
    problems = []
    listed = {k for k in man if k.endswith(".py")}
    for name in files(folder):
        if name not in listed:
            problems.append(f"{name}: not part of the kit (added in the app?)")
        elif digest(os.path.join(folder, name)) != man[name]:
            problems.append(f"{name}: changed in the app; change it in SbAe9-Kit and sync")
    for name in sorted(listed - set(files(folder))):
        problems.append(f"{name}: missing")
    return problems

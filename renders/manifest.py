#!/usr/bin/env python3
"""Write generated/renders/v0.5.0/MANIFEST.json: every rendered PNG with its
sha256, plus the tool versions and the pinned keycap source — the renders'
reproduction contract."""
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "generated", "renders", "v0.5.0")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = {}
    for root, _dirs, names in os.walk(OUT):
        for n in sorted(names):
            if n.lower().endswith(".png"):
                p = os.path.join(root, n)
                files[os.path.relpath(p, OUT)] = sha256(p)
    prov_path = os.path.join(REPO, "generated", "renders", "assets",
                             "PROVENANCE.json")
    prov = json.load(open(prov_path)) if os.path.exists(prov_path) else {}
    try:
        bl = subprocess.run(["/opt/homebrew/bin/blender", "--version"],
                            capture_output=True, text=True).stdout.split("\n")[0]
    except Exception:
        bl = "unknown"
    manifest = {
        "release": "generated/release/v0.5.0 (boards @8eef566357b8)",
        "renderer": bl,
        "keycaps": prov.get("keycaps", {}),
        "cad_tools": prov.get("tools", {}),
        "renders": files,
        "note": "regenerate: renders/README.md; assets tree is derived "
                "(gitignored), final PNGs are committed",
    }
    with open(os.path.join(OUT, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"manifest: {len(files)} renders hashed")


if __name__ == "__main__":
    main()

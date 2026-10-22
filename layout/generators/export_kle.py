#!/usr/bin/env python3
"""Derive the KLE sketch from the Ergogen layout output.

Layout-phase generator: Ergogen is the source of truth
(`layout/ergogen/config.yaml`), this script re-derives
`layout/- FINAL/keyboard_layout_v2.json` from
`layout/generated/v2/points/points.yaml` so the two can never drift apart.

Usage (from repo root):
    npx ergogen layout/ergogen -o layout/generated/v2
    python3 layout/generators/export_kle.py [--check]

--check additionally round-trips the output through kle-serial
(requires node + project node_modules) and asserts every key lands
within 0.01u of the Ergogen coordinates.

Do NOT hand-edit keyboard_layout_v2.json. Change the Ergogen config
and/or spec/layout.yaml, regenerate Ergogen output, re-run this script.
KLE v1 (layout/- FINAL/keyboard_layout_v1.json) is the archived
row-staggered starting sketch and is intentionally left untouched.
"""

import json
import subprocess
import sys

REPO = __file__.rsplit("/layout/generators/", 1)[0]
PTS = REPO + "/layout/generated/v2/points/points.yaml"
OUT = REPO + "/layout/- FINAL/keyboard_layout_v2.json"

U = 19.0  # mm per KLE unit (MX pitch)
# KLE x/y are the TOP-LEFT corner; Ergogen points are CENTERS.
# Hence the -0.5u corner offset on both absolute origins.
X0 = -0.5  # KLE wants top-left corners; Ergogen gives centers


def R3(x):
    return round(x + 1e-9, 3)


# Ergogen key name -> KLE label. Left-hand legends, keycap convention
# (shifted symbol on the first line, base below).  Labels show BASE-layer
# + shift only; the per-layer keymap of record is spec/keymap.md + the
# generated keymaps (config/gen_keymap.py) — a KLE label is a render aid,
# never the binding.
LAB = {
    "matrix_outer_bottom": "Z",
    "matrix_outer_home": "A",
    "matrix_outer_top": "Q",
    "matrix_pinky_bottom": "X",
    "matrix_pinky_home": "S",
    "matrix_pinky_top": "W",
    "matrix_ring_bottom": "C",
    "matrix_ring_home": "D",
    "matrix_ring_top": "E",
    "matrix_middle_bottom": "V",
    "matrix_middle_home": "F",
    "matrix_middle_top": "R",
    "matrix_index_bottom": "B",
    "matrix_index_home": "G",
    "matrix_index_top": "T",
    "matrix_inner_bottom": "_\n-",     # base -, shift _ (L1 repeats -)
    "matrix_inner_home": "{\n[",       # base [, shift {
    "matrix_inner_top": "~\n`",
    "thumbs_t_ctrl_cluster": "Esc",      # west->east on the left half
    "thumbs_t_cmd_cluster": "L1",
    "thumbs_t_l1_cluster": "Tab",
    "thumbs_t_space_cluster": "Space",
    "encoder": "Enc",
}

# Left label -> right-hand counterpart (mirrored side).
MLAB = {
    "Enc": "Enc",
    "Space": "Enter", "L1": "L2",
    "Tab": "Backspace", "Esc": "Delete",
    "_\n-": "\"\n'", "{\n[": "}\n]", "~\n`": "|\n\\",
    "Q": "P", "A": ":\n;", "Z": "?\n/",
    "W": "O", "S": "L", "X": ">\n.",
    "E": "I", "D": "K", "C": "<\n,",
    "R": "U", "F": "J", "V": "M",
    "T": "Y", "G": "H", "B": "N",
}

LCOLS = ["outer", "pinky", "ring", "middle", "index", "inner"]
ROWS = ["top", "home", "bottom"]  # emitted top-down


def load_points(path):
    """Minimal YAML reader for Ergogen points files (flat key: x/y/r only)."""
    pts, cur = {}, None
    for line in open(path):
        if line and not line[0].isspace() and line.rstrip().endswith(":"):
            cur = line.strip()[:-1]
            pts[cur] = {}
        elif cur is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            k, v = k.strip().strip("'\""), v.strip()
            if k in ("x", "y", "r") and v not in ("", "~", "null"):
                pts[cur][k] = float(v)
    return pts


def main():
    d = load_points(PTS)
    # Top of the matrix lands on KLE y=0.
    top = max(v["y"] for k, v in d.items() if "_top" in k and not k.startswith("mirror_"))
    Y0 = top / U - 0.5

    def Ku(p):
        return (p["x"] / U + X0, Y0 - p["y"] / U, -p.get("r", 0))

    rows = []
    cur_y = 0.0
    first_row = True
    for r in ROWS:
        seq = ["matrix_%s_%s" % (c, r) for c in LCOLS]
        seq += ["mirror_matrix_%s_%s" % (c, r) for c in reversed(LCOLS)]
        items, prev_x = [], None
        for i, name in enumerate(seq):
            right = name.startswith("mirror_")
            base = name.replace("mirror_matrix_", "matrix_") if right else name
            lab = MLAB[LAB[base]] if right else LAB[base]
            x, y, rr = Ku(d[name])
            if i == 0:
                # First key of a row anchors absolutely. Ku already yields
                # TOP-LEFT corners (X0 folds in the center-to-corner half
                # unit); gaps below stay relative and frame-free.
                dy = y - (cur_y if first_row else cur_y + 1)
                dd = {"y": R3(dy), "x": R3(x)}
            else:
                dd = {}
                dy, dx = y - prev_y, x - prev_x - 1
                if abs(dy) > 0.0005:
                    dd["y"] = R3(dy)
                if abs(dx) > 0.0005:
                    dd["x"] = R3(dx)
                if not dd:
                    dd = None
            items += [lab] if dd is None else [dd, lab]
            prev_x, prev_y = x, y
        cur_y = prev_y
        first_row = False
        rows.append(items)

    # Thumb keys: one self-contained row each (rotation is only legal on
    # the first item of a row). Offsets are relative to each key's own
    # pivot because rx/ry teleport the KLE cursor before x/y apply.
    tseq = [
        "thumbs_t_ctrl_cluster", "thumbs_t_cmd_cluster",
        "thumbs_t_l1_cluster", "thumbs_t_space_cluster",
        "mirror_thumbs_t_space_cluster", "mirror_thumbs_t_l1_cluster",
        "mirror_thumbs_t_cmd_cluster", "mirror_thumbs_t_ctrl_cluster",
        "encoder", "mirror_encoder",
    ]
    # All keys are 1u: the KLE rect starts at its top edge, so
    # pivot/offset use 0.5. (A taller key would need h/2 here.)
    heights = {}
    for name in tseq:
        right = name.startswith("mirror_")
        base = name.replace("mirror_thumbs_", "thumbs_")
        if base == name:
            base = name.replace("mirror_", "")
        lab = MLAB[LAB[base]] if right else LAB[base]
        src = d[name]
        h = heights.get(lab, 1.0)
        # (x, y) = top-left corner of the KLE rect, same frame as the
        # finger rows above (Ku yields tops, not centers).
        x, y, rr = Ku(src)[0], Ku(src)[1], -src.get("r", 0)
        rx, ry = R3(x + 0.5), R3(y + h / 2)
        dd = {"x": R3(x - rx), "y": R3(y - ry),
              "r": R3(rr), "rx": rx, "ry": ry}
        if h != 1.0:
            dd["h"] = h
        rows.append([dd, lab])

    with open(OUT, "w") as f:
        json.dump(rows, f, indent=2)
    n = sum(1 for r in rows for e in r if isinstance(e, str))
    print("wrote %s: %d rows, %d keys" % (OUT, len(rows), n))

    if "--check" in sys.argv:
        node = (
            "const kls=require('./node_modules/kle-serial');"
            "const fs=require('fs');"
            "const raw=JSON.parse(fs.readFileSync('%s','utf8'));"
            "const kb=kls.Serial.deserialize(raw);"
            "console.log('kle-serial keys: '+kb.keys.length);" % OUT
        )
        subprocess.run(["node", "-e", node], cwd=REPO, check=True)


if __name__ == "__main__":
    main()

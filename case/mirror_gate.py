#!/usr/bin/env python3
"""H-7 left/right mirror gate for the generated case solids.

The board and plate are gated in `pcb/generators/check_board.py`.  The
case tub/cover are CadQuery solids, so their pointwise check lives here
(run with the pinned case venv):

    case/.venv/bin/python case/mirror_gate.py

Both halves are generated from independently parsed artifacts, so a
0.07mm sample-phase drift can hide in the plate tabs or a port bore even
when the source outline is symmetric.  This gate mirrors the Left solid
about the shared x=145.75 axis, then takes a two-sided max vertex
distance to the Right solid.  A 0.5mm translation of the Right solid is
the negative control; the tolerance is 0.05mm (H-7).
"""
import math
import os
import sys

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt

import params as P

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "case", "out")
TOL = 0.05


def load(kind, half):
    path = os.path.join(OUT, f"Hojicha44-{half}-{kind}.step")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}; run gen_case.py and gen_cover.py")
    return cq.importers.importStep(path).val()


def mirror(shape):
    return shape.mirror("YZ", basePointVector=(P.MIRROR_AX, 0, 0))


def points(shape):
    return [(v.Center().x, v.Center().y, v.Center().z)
            for v in shape.Vertices()]


def distance(pt, shape):
    v = BRepBuilderAPI_MakeVertex(gp_Pnt(*pt)).Vertex()
    d = BRepExtrema_DistShapeShape(v, shape.wrapped)
    d.Perform()
    return d.Value()


def max_distance(pts, shape):
    return max(distance(p, shape) for p in pts)


def check(kind):
    left, right = load(kind, "Left"), load(kind, "Right")
    lm = mirror(left)
    pl, pr = points(lm), points(right)
    if not pl or not pr:
        return [f"{kind}: no vertices (empty STEP?)"]
    d1 = max_distance(pl, right)
    d2 = max_distance(pr, lm)
    d = max(d1, d2)
    print(f"  {kind}: {len(pl)}/{len(pr)} vertices, "
          f"L->R {d1:.4f}mm, R->L {d2:.4f}mm, max {d:.4f}mm "
          f"(floor {TOL:.2f})", flush=True)
    bad = []
    if d > TOL:
        bad.append(f"{kind}: mirror residual {d:.4f}mm > {TOL:.2f}mm")
    # Negative control: a 0.5mm shift must be rejected.  A subset is
    # enough (every point moves ~0.5mm) and keeps the gate under a
    # minute after the two full passes.
    ctl = max_distance(pl[:80], right.translate((0.5, 0, 0)))
    print(f"  {kind}: 0.5mm control {ctl:.4f}mm", flush=True)
    if ctl <= TOL:
        bad.append(f"{kind}: 0.5mm control did NOT fail "
                   f"(residual {ctl:.4f}mm)")
    return bad


def main():
    bad = []
    for kind in ("tub", "cover"):
        bad += check(kind)
    for b in bad:
        print(f"  !! {b}")
    print("case mirror gate: CLEAN" if not bad else
          "case mirror gate: FAILING")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

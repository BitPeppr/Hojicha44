#!/usr/bin/env python3
"""Offline bore shape audit for v3.4/v3.5 (not part of CI).

Run alongside `gen_case.py` (it rebuilds the halves): probes the FINISHED
solids at bore-specific positions the generic probe battery doesn't
cover — USB below-bore wall, flank, fillet envelope, full-width under
the lip; TRRS axis/edges/extreme-z chords; slab sills. Handy before a
real print.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

import gen_case as G
import params

fails = []


def probe(tag, name, solid, o, u, v, b, t, z, want):
    x, y = o[0] + u[0] * t + v[0] * b, o[1] + u[1] * t + v[1] * b
    clf = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z), 1e-6)
    got = clf.State() == TopAbs_IN
    if got != want:
        fails.append(f"{tag} {name} t={t} b={b} z={z}: "
                     f"{'solid' if got else 'void'} != "
                     f"{'solid' if want else 'void'}")
    else:
        print(f"  ok {tag} {name} t={t} b={b:+.2f} z={z:+.2f} "
              f"{'solid' if want else 'void'}")


for tag in ("Left", "Right"):
    print(f"{tag}:")
    solid, info = G.build_half(tag)
    for name in ("usb", "trrs", "pwrsw"):
        pr = info["ports"][name]
        o, u, v = pr["o"], pr["u"], pr["v"]
        if name == "usb":
            # below the bore (z0=2.0) the wall must be solid again
            probe(tag, name + "/below", solid, o, u, v, 0.0, 3.5, 1.5, True)
            # inside w/2 at mouth depth -> void (straight flank zone)
            probe(tag, name + "/flank", solid, o, u, v, 6.3, 3.5, 4.5, False)
            # bottom fillet: inside the fillet envelope at z0+0.4
            r, w = pr["r"], pr["w"]
            z = params.USB_MOUTH_Z0 + 0.4
            hw = (w / 2 - r) + math.sqrt(max(
                r ** 2 - (params.USB_MOUTH_Z0 + r - z) ** 2, 0.0))
            probe(tag, name + "/fillet-in", solid, o, u, v,
                  hw - 0.05, 3.5, z, False)
            # flat top: full width void right under the lip plane
            probe(tag, name + "/top", solid, o, u, v, 6.9, 3.5, 5.95, False)
        elif name == "trrs":
            r = pr["r"]
            zc = pr["zc"]
            # across the axis -> void; just past the radius -> solid
            probe(tag, name + "/axis", solid, o, u, v, 0.0, 3.5, zc, False)
            probe(tag, name + "/edge-in", solid, o, u, v,
                  r - 0.15, 3.5, zc, False)
            probe(tag, name + "/edge-out", solid, o, u, v,
                  r + 0.15, 3.5, zc, True)
            # chord at a far z plane: in-out at the exact circle
            for dz in (-4.2, 3.4):
                hw = math.sqrt(max(r ** 2 - dz ** 2, 0.0))
                if hw < 0.3:
                    continue
                zb = zc + dz
                if not (params.FLOOR_Z < zb < params.TOP_LIP_Z):
                    continue
                probe(tag, name + f"/chord{dz:+.1f}-in", solid, o, u, v,
                      hw - 0.05, 3.5, zb, False)
                probe(tag, name + f"/chord{dz:+.1f}-out", solid, o, u, v,
                      hw + 0.05, 3.5, zb, True)
            # drop-in: the PJ-320A's plastic mouth face sits RECESSED
            # 0.99mm behind the board edge (review-measured), so on the
            # straight drop-in nothing of the jack crosses the wall
            # band; the face-slide probes stand as conservative bounds. Dims
            # measured off the vendored model
            # pcb/kicad/Hojicha44.3dshapes/PJ-320A.step: face 6.1 wide
            # (±3.05 about the plug axis), top flat at z 5.0, axis
            # vertex z=2.5 (= TRRS_MOUTH_ZC). The face section must
            # slide through the bore at every z it occupies; the wall
            # must resume just past the circle.
            face_hw, face_top = 3.05, 5.0
            for zz in (0.15, zc, face_top - 0.15):
                hwz = math.sqrt(max(r ** 2 - (zz - zc) ** 2, 0.0))
                if hwz < face_hw:
                    fails.append(f"{tag} TRRS bore r={r} cannot host face "
                                 f"corner hw {face_hw} at z={zz:.2f} "
                                 f"(has {hwz:.3f})")
                    continue
                for t in (0.7, 3.5):
                    for sgn in (-1.0, 1.0):
                        probe(tag, name + f"/face-in z{zz:.2f}", solid,
                              o, u, v, sgn * (face_hw - 0.15), t, zz, False)
                        if hwz > face_hw + 0.25:
                            probe(tag, name + f"/face-spare z{zz:.2f}",
                                  solid, o, u, v, sgn * (face_hw + 0.25),
                                  t, zz, False)
                        probe(tag, name + f"/wall-resumed z{zz:.2f}", solid,
                              o, u, v, sgn * (hwz + 0.2), t, zz, True)
        elif name == "pwrsw":
            # v3.5 actuator window: the slot's sill below must be
            # solid, the fillet envelope must admit the nail, the wall
            # must resume past the 5.0-width (ring stays one piece),
            # and the lip plane stays open
            r_, w_ = pr["r"], pr["w"]
            z0_ = pr["z0"]
            probe(tag, name + "/below", solid, o, u, v, 0.0, 3.5,
                  z0_ - 0.6, True)
            probe(tag, name + "/flank", solid, o, u, v,
                  w_ / 2 - 0.15, 3.5, (z0_ + pr["z1"]) / 2, False)
            z = z0_ + 0.4
            hw = (w_ / 2 - r_) + math.sqrt(max(
                r_ ** 2 - (z0_ + r_ - z) ** 2, 0.0))
            probe(tag, name + "/fillet-in", solid, o, u, v,
                  hw - 0.05, 3.5, z, False)
            probe(tag, name + "/wall-resumed", solid, o, u, v,
                  w_ / 2 + 0.55, 3.5, (z0_ + pr["z1"]) / 2, True)
            probe(tag, name + "/top", solid, o, u, v, 0.0, 3.5,
                  params.TOP_LIP_Z - 0.1, False)
        # slab under every bore stays solid at two depths
        probe(tag, name + "/slab1", solid, o, u, v, 0.0, 3.5,
              params.FLOOR_Z - 1.0, True)
        probe(tag, name + "/slab2", solid, o, u, v, 0.0, 3.5,
              params.FLOOR_Z - 0.2, True)
print()
if fails:
    print(f"FAIL ({len(fails)}):")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("all shape probes pass")

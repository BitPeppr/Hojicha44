#!/usr/bin/env python3
"""Offline bore shape audit for v4.x (not part of CI).

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
            # plug passage (thin-top revision): the bore is a Ø6.0
            # round SIDE hole closed by a 0.7 roof — it passes the
            # straight 3.5mm plug barrel (the jack is soldered inside
            # the cavity and its 6.1-wide mouth face NEVER crosses the
            # wall; the old face-slide probes belonged to the Ø9.5
            # top-open notch and are gone). The barrel tops at 4.25 —
            # in the COVER band (tub ends at the 3.20 lip); the cover's
            # upper hole + roof are verified by the x=143 wall section.
            # Here: worst tub-band slice just under the lip.
            barrel_r, jack_axis = 2.0, 2.5
            zt = params.TOP_LIP_Z - 0.1  # 3.1
            hwb = math.sqrt(max(r ** 2 - (zt - zc) ** 2, 0.0))
            hp = math.sqrt(max(barrel_r ** 2 - (zt - jack_axis) ** 2, 0.0))
            if hwb <= hp + 0.1:
                fails.append(f"{tag} TRRS bore r={r} too tight for a "
                             f"Ø{2 * barrel_r} barrel at z={zt:.2f} "
                             f"(bore hw {hwb:.3f} vs plug {hp:.3f})")
            else:
                for t in (0.7, 3.5):
                    probe(tag, name + "/plug-in", solid, o, u, v,
                          hp - 0.05, t, zt, False)
                    probe(tag, name + "/wall-resumed", solid, o, u, v,
                          hwb + 0.2, t, zt, True)
        elif name == "pwrsw":
            if pr.get("skipped") or pr.get("kind") == "none":
                # thin-cover lip: the pwrsw port lives entirely ABOVE
                # the tub (body top 5.0 > lip 3.20) — no tub bore; the
                # COVER carries PWRSW_WIN + the nail slot (gen_cover
                # gates probe that solid/void pattern).
                print(f"  skipped {tag} pwrsw (above-tub port; the cover "
                      f"carries PWRSW_WIN)")
            else:
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

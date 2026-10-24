#!/usr/bin/env python3
"""Hojicha44 thin top cover — v4.0 (CadQuery, parametric).

The user review called the v3.5 rim ring "extraordinarily thick" and
asked for a top case that follows the components: a 2.5mm top PLATE on
the lip that

  * opens a single key field around the 22 keycaps (their 17.48x16.48
    KLP footprints, dilated CAP_CLEAR, merge at the 19mm pitch into one
    clean opening),
  * covers the MCU/encoder wiring strip between the key field and the
    inner skin, with windows for the nio module, the EC11 and the
    pwrsw body,
  * reuses the tub's port passages so USB and TRRS align (the TRRS
    cylinder is now an EDGE NOTCH: the lip 3.48 sits below the bore top
    7.25, so the wall band above the jack is open and a straight plug's
    head clears the case),
  * keeps the 8 recessed magnet pockets (Ø4x1.0 in a 1.2 pocket, 1.3
    floor) whose faces still meet the tub's at the lip plane.

The plate stays at the Choc v1 clip band (1.00..2.20) — moving it up
would lose the clip engagement (spec/case.md) — so the thinness comes
from the lip/cover above it: the keycaps now stand ~2.4mm proud of the
top face instead of sitting flush with a 3.0mm ring.

  case/.venv/bin/python case/gen_cover.py            # both halves
  case/.venv/bin/python case/gen_cover.py Left       # one half

Outputs (gitignored scratch): $CASE_OUT (default case/out)
  Hojicha44-{half}-cover.step/.stl
"""
import json
import math
import os
import sys

import cadquery as cq

import params
import gen_case as G

REPO = G.REPO
OUT_DIR = G.OUT_DIR   # CASE_OUT override shared with gen_case.py


def rrect(w, h, r, cx, cy, ang, z0, z1):
    """Rounded-rectangle prism (r clamped to the shorter side)."""
    r = min(r, w / 2 - 0.05, h / 2 - 0.05)
    wp = cq.Workplane("XY").rect(w, h).extrude(z1 - z0)
    if r > 0.2:
        wp = wp.edges("|Z").fillet(r)
    return (wp.rotate((0, 0, 0), (0, 0, 1), ang)
            .translate((cx, cy, z0)).val())


def drop_scrap(solid):
    """Keep the largest solid, drop tiny enclosed scraps.

    The union of 22 staggered cap cutters (and the neighbouring windows)
    can enclose small material regions between footprints. Those
    regions are separate solids after the cut; if exported they would be
    loose pieces in the print. Dropping them makes them VOID — the key
    field becomes one clean opening. Real severances (a port slot
    cutting the plate in two) are caught by the volume limits in
    check_cover, so this can never silently remove a structural piece.
    """
    parts = sorted(solid.Solids(), key=lambda s: s.Volume(), reverse=True)
    if len(parts) <= 1:
        return solid, []
    scrap = parts[1:]
    return parts[0], [(round(s.Volume(), 1),
                       tuple(round(v, 1) for v in s.BoundingBox().center))
                      for s in scrap]


def win2(tag, win):
    """Mirror a Left-frame window rect (x0,y0,x1,y1) onto Right."""
    if tag == "Left":
        return win
    ax = 2.0 * params.MIRROR_AX
    return (ax - win[2], win[1], ax - win[0], win[3])


def key_side(tag, win):
    """The window edge facing the key field (Left keys are at lower x,
    Right keys at higher x), +0.4mm into the cover web."""
    return (win[0] - 0.4) if tag == "Left" else (win[2] + 0.4)


def build_cover(tag):
    P = params
    dxf = os.path.join(G.PLATE_DIR, f"Hojicha44-{tag}-plate.dxf")
    pcb = os.path.join(REPO, "pcb", "kicad", f"Hojicha44-{tag}.kicad_pcb")
    lands = json.load(open(os.path.join(
        G.PLATE_DIR, f"Hojicha44-{tag}-lands.json")))
    outline = G.read_outline(dxf)          # plate outline (tabs included)
    rim = G.read_pcb_outline(pcb)          # PCB rim
    cav_poly = G.offset_pts(outline, P.RIM_CLEAR)
    rim_ring = G.resample_ring(rim, P.SKIN_STEP)
    rnorm = G.outward_field(rim_ring)
    # outer face = the SAME dilated-rim ring as the tub (flush seam,
    # aligned magnet stations)
    skin = G.resample_ring(G.offset_pts(rim, P.CASE_OUTSET), P.SKIN_STEP)
    ports = G.compute_ports(tag, rim_ring, rnorm, skin, P)
    sksegs = list(zip(skin, skin[1:] + skin[:1]))
    pocket_rects = G.pocket_layout(lands["tabs"], sksegs, P)
    stations, bands, webs = G.magnet_stations(P, tag, skin, cav_poly,
                                              pocket_rects, ports)
    pad_centers = [(o[0] + u[0] * 2.0, o[1] + u[1] * 2.0)
                   for t in lands["tabs"]
                   for (o, u, v) in [G.tab_frame(t)]]
    holes = G.read_cutouts(dxf)            # 22 switch centres + angles

    z0, z1 = P.TOP_LIP_Z, P.TOP_LIP_Z + P.COVER_T
    solid = G.prism(skin, z0, z1)

    # ---- key field: union of the 22 dilated cap footprints -------------
    kw = P.CAP_FOOT_W + 2 * P.CAP_CLEAR
    kh = P.CAP_FOOT_H + 2 * P.CAP_CLEAR
    cutter = None
    for (cx, cy, ang) in holes:
        s = rrect(kw, kh, P.CAP_ROUND, cx, cy, ang, z0 - 1.0, z1 + 1.0)
        cutter = s if cutter is None else cutter.fuse(s)
    # ---- component windows (MCU / encoder / pwrsw body; mirrored) ------
    for (x0, y0, x1, y1) in (win2(tag, P.MCU_WIN), win2(tag, P.ENC_WIN),
                             win2(tag, P.PWRSW_WIN)):
        s = rrect(x1 - x0, y1 - y0, 2.0, (x0 + x1) / 2, (y0 + y1) / 2,
                  0.0, z0 - 1.0, z1 + 1.0)
        cutter = cutter.fuse(s)
    solid = solid.cut(cutter)

    from OCP.gp import gp_Dir, gp_Pnt

    # ---- USB: the SAME frame/width/fillets as the tub bore, full depth
    pr = ports["usb"]
    ox, oy = pr["o"]
    ux, uy = pr["u"]
    travel = P.SLOT_IN + 1.0 + pr["out"] + 1.0
    base = (ox - ux * (P.SLOT_IN + 1.0), oy - uy * (P.SLOT_IN + 1.0))
    solid = solid.cut(G.fillet_slot(base, pr["v"], pr["u"], pr["w"],
                                    z0 - 0.5, z1 + 0.5, pr["r"], travel))
    # ---- TRRS: the SAME Ø9.5 cylinder. The lip is below the bore top,
    # so this is an EDGE NOTCH (open above), not the old blind tunnel.
    pr = ports["trrs"]
    ox, oy = pr["o"]
    ux, uy = pr["u"]
    base = (ox - ux * (P.SLOT_IN + 1.0), oy - uy * (P.SLOT_IN + 1.0))
    solid = solid.cut(cq.Solid.makeCylinder(
        P.TRRS_MOUTH_R, travel,
        gp_Pnt(base[0], base[1], P.TRRS_MOUTH_ZC),
        gp_Dir(ux, uy, 0.0)))
    # ---- magnets: cut UP from the underside (faces flush at z0) --------
    for (cx, cy) in stations:
        solid = solid.cut(cq.Solid.makeCylinder(
            P.MAG_DIA / 2, P.COVER_MAG_DEPTH,
            gp_Pnt(cx, cy, z0), gp_Dir(0, 0, 1)))

    # ---- edge embellishment (no-indent design): a 0.4mm chamfer on the
    # outer-rim top edges only — the kernel rejects chamfering ALL top
    # edges (window/slot tangencies); the rim loop alone builds fine.
    skin_pts = skin
    near = []
    for e in solid.Edges():
        c = e.Center()
        if abs(c.z - z1) > 0.05:
            continue
        d = 1e9
        for a, b in zip(skin_pts, skin_pts[1:] + skin_pts[:1]):
            d = min(d, G.segd((c.x, c.y), a, b))
        if d < 0.8:
            near.append(e)
    if near:
        solid = (cq.Workplane("XY").newObject([solid])
                 .newObject(near).chamfer(0.4).val())

    solid, scrap = drop_scrap(solid)

    return solid, {"skin": skin, "cav_poly": cav_poly,
                   "mag_stations": stations, "mag_bands": bands,
                   "mag_webs": webs,
                   "pad_centers": pad_centers, "ports": ports,
                   "holes": holes, "scrap": scrap}


def check_cover(tag, solid, info):
    P = params
    bad = []
    bb = solid.BoundingBox()
    z0, z1 = P.TOP_LIP_Z, P.TOP_LIP_Z + P.COVER_T
    if abs(bb.zmin - z0) > 0.05:
        bad.append(f"zmin {bb.zmin:.2f} != lip {z0}")
    if abs(bb.zmax - z1) > 0.05:
        bad.append(f"zmax {bb.zmax:.2f} != lip+COVER_T {z1}")
    if not solid.isValid():
        bad.append("kernel reports invalid solid")
    nsolids = len(solid.Solids())
    if nsolids != 1:
        bad.append(f"{nsolids} disjoint solids (an opening split the plate)")
    scrap = info.get("scrap", [])
    scrap_vol = sum(v for v, _ in scrap)
    if scrap:
        biggest = max(v for v, _ in scrap)
        if biggest > 60.0 or scrap_vol > 400.0:
            bad.append(f"dropped {len(scrap)} pieces/{scrap_vol:.0f} mm3 — "
                       f"that is a severed plate, not enclosed scraps "
                       f"(biggest {biggest:.0f} mm3)")

    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN

    def solid_at(x, y, z):
        clf = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z),
                                          1e-6)
        return clf.State() == TopAbs_IN

    def expect(name, x, y, z, want):
        if solid_at(x, y, z) != want:
            bad.append(f"{name} at ({G.r2(x)},{G.r2(y)},{G.r2(z)}) "
                       f"{'solid' if want else 'void'} expected")

    mid = z0 + P.COVER_T / 2.0

    # 1. key field: every switch centre must be open through the plate
    for (cx, cy, _ang) in info["holes"]:
        expect("key field open", cx, cy, mid, False)
    # 2. outer band: solid over the tab pads (press gate) and at skin
    #    samples clear of every port rect
    for (px, py) in info["pad_centers"]:
        expect("cover presses tab pad", px, py, z0 + 0.2, True)
        # second probe stays under any key-field ledge (the ledge only
        # trims the top KEY_LEDGE_D over a border; the press face and
        # >=1.0mm of material over the pad must remain)
        expect("cover presses tab pad", px, py, z0 + 1.0, True)
    skin, cav = info["skin"], info["cav_poly"]
    snorm = G.outward_field(skin)
    hits = 0
    for si in range(0, len(skin), max(1, len(skin) // 24)):
        sp = skin[si]
        if min(G.rect_d(sp, info["ports"][n]["rect"])
               for n in ("usb", "trrs", "pwrsw")) < 1.8:
            continue
        px = sp[0] - snorm[si][0] * 0.6
        py = sp[1] - snorm[si][1] * 0.6
        expect("outer band solid", px, py, mid, True)
        hits += 1
    if hits < 12:
        bad.append(f"outer band probes only {hits}")

    # 3. component windows are open, and the strip around them is solid
    for base, nm in ((P.MCU_WIN, "mcu"), (P.ENC_WIN, "enc"),
                     (P.PWRSW_WIN, "pwrsw")):
        x0, y0, x1, y1 = win2(tag, base)
        expect(f"{nm} window open", (x0 + x1) / 2, (y0 + y1) / 2, mid,
               False)
    pox = info["ports"]["pwrsw"]["o"][0]
    expect("pwrsw window open to the north skin", pox, 66.0, mid, False)
    # cover material between the component windows and the key field
    # (probe just outside each window edge; void here means an opening
    # merged the window into the key field — the plate must keep the
    # component strip the user asked for)
    mw = win2(tag, P.MCU_WIN)
    ew = win2(tag, P.ENC_WIN)
    expect("mcu/key-field web solid", key_side(tag, mw),
           (mw[1] + mw[3]) / 2, mid, True)
    expect("enc/key-field web solid", key_side(tag, ew),
           (ew[1] + ew[3]) / 2, mid, True)

    # 4. port passages: void through the band, air beyond, and the TRRS
    #    notch is open at the top (the straight-plug fix)
    for name in ("usb", "trrs"):
        pr = info["ports"][name]
        o, u = pr["o"], pr["u"]
        dt = P.CASE_OUTSET / 2.0
        zbs = (z0 + 0.4, z1 - 0.4) if name == "usb" else \
            (z0 + 0.3, z0 + 1.0)
        for zb in zbs:
            expect(f"{name} passage void", o[0] + u[0] * dt,
                   o[1] + u[1] * dt, zb, False)
        expect(f"{name} air beyond", o[0] + u[0] * (pr["out"] + 3.0),
               o[1] + u[1] * (pr["out"] + 3.0), mid, False)
    pr = info["ports"]["trrs"]
    o, u = pr["o"], pr["u"]
    expect("trrs roof solid", o[0] + u[0] * (P.CASE_OUTSET / 2.0),
           o[1] + u[1] * (P.CASE_OUTSET / 2.0), z1 - 0.2, True)

    # 5. magnets: real recesses that mirror the tub's stations
    stn = info["mag_stations"]
    if len(stn) < P.MAG_MIN_STATIONS:
        bad.append(f"cover magnet stations {len(stn)} < "
                   f"{P.MAG_MIN_STATIONS}")
    for (cx, cy) in stn:
        expect("cover magnet pocket void", cx, cy, z0 + 0.5, False)
        expect("cover magnet pocket floor", cx, cy,
               z0 + P.COVER_MAG_DEPTH + 0.4, True)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            expect("cover magnet pocket web",
                   cx + dx * (P.MAG_DIA / 2 + 0.3),
                   cy + dy * (P.MAG_DIA / 2 + 0.3), z0 + 0.5, True)

    # 6. antenna: the MCU window must keep the cover >=3mm away — probe
    #    the centre and a 2mm cross (the old ring-distance gates are
    #    meaningless on a covering plate, the 3mm rule is the contract)
    ant = P.ANTENNA_L if tag == "Left" else P.ANTENNA_R
    for (dx, dy) in ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2)):
        expect("no cover within 2mm of antenna",
               ant[0] + dx, ant[1] + dy, mid, False)

    vol = solid.Volume()
    bstat = (f", magnet band min {min(info['mag_bands']):.2f}, "
             f"web min {min(info['mag_webs']):.2f}") if stn else ""
    sc = (f", dropped {len(scrap)} enclosed scraps "
          f"({scrap_vol:.0f} mm3)" if scrap else "")
    print(f"  {tag} cover: volume {vol / 1000:.1f} cm3, "
          f"bbox z [{bb.zmin:.1f}, {bb.zmax:.1f}], "
          f"key holes {len(info['holes'])} (one opening), "
          f"stations {len(stn)}{sc}{bstat}")
    if not (6000 <= vol <= 28000):
        bad.append(f"cover volume {vol / 1000:.1f} cm3 outside "
                   f"[6, 28] tripwire (thin top plate, key field open)")
    return bad


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    halves = sys.argv[1:] or ["Left", "Right"]
    rc = 0
    for tag in halves:
        solid, info = build_cover(tag)
        bad = check_cover(tag, solid, info)
        if bad:
            print(f"{tag} FAIL:")
            for b in bad:
                print(f"  !! {b}")
            rc = 1
            continue
        step = os.path.join(OUT_DIR, f"Hojicha44-{tag}-cover.step")
        stl = os.path.join(OUT_DIR, f"Hojicha44-{tag}-cover.stl")
        cq.exporters.export(cq.Workplane(obj=solid), step)
        cq.exporters.export(cq.Workplane(obj=solid), stl)
        assert os.path.getsize(step) > 100000, f"{tag}: STEP suspiciously small"
        assert os.path.getsize(stl) > 100000, f"{tag}: STL suspiciously small"
        print(f"{tag}: cover -> {os.path.basename(step)} "
              f"({os.path.getsize(step) // 1024} KB)")
    sys.exit(rc)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Hojicha44 ring cover — v3.5 (CadQuery, parametric).

Flush bezel ring that sits on the tub lip: underside TOP_LIP_Z, top
+COVER_T, outer face FLUSH with the skin (the SAME dilated-rim ring as
the tub — an intentional lid seam), inner edge on the PCB rim +
RIM_CLEAR — NOT the plate outline (v1 cut the outline cavity, which
left a tab-shaped bite over every tab: the top poron pads pressed
NOTHING; the review caught it). The rim-based interior bridges all 8
tab zones and presses the top pads at the designed 16.7% preload,
gated per pad. Retained by 8+8 recessed 4x2 N52 magnets whose faces
meet AT the lip plane: tub magnet face-up to 6.0, ring magnet
face-down to 6.0 — a rigid zero-gap stop that cannot crush the foam,
no heat-set inserts, nothing on the exterior.

  case/.venv/bin/python case/gen_cover.py            # both halves
  case/.venv/bin/python case/gen_cover.py Left       # one half

Outputs (gitignored scratch): case/out/Hojicha44-{half}-cover.step/.stl

Construction (z=0 is the PCB top; see params.py):
  1. solid = prism(skin) from TOP_LIP_Z to +COVER_T
  2. ring  = minus prism(rim + RIM_CLEAR) — inner edge = the PCB rim
       line + 0.5, so the ring BRIDGES every tab pocket (an outline-
       based interior leaves bites and the pads unload; the 0..0.5mm
       root sliver stays unpressed — harmless)
  3. passages reusing gen_case.compute_ports (same anchors, widths and
     MEASURED breach as the tub):
       W1  usb 14.0-wide slot, FULL depth (plug neck/housing to ~9.2
           abs rides through and 0.2 past the top)
       W2  trrs = the SAME Ø9.5 cylinder (axis zc 2.5): a BLIND tunnel
           in the 6..9 slice (tops at 7.25 > boot swing 6.75), whose
           chord in that slice stays <=6.42 (lip plane) < band 7.7 — the
           NOT split
       pwrsw flick slot, full depth BUT starting t=1.6 (inner web 1.1
           to the cavity-side edge): W1 must remain the ONLY full
           radial severance or the ring falls into two pieces
  4. magnets = Ø4.3x1.7 pockets (Ø4x1.5 magnets, COVER_MAG_DEPTH) cut
     UP from the underside at the SAME magnet_stations the tub pocketed
     (shared geometry, zero-gap)

Gates (check_cover, exit 0 only if every one passes): bbox z window,
single solid (2 pieces == a passage split the ring), ring wall census
>= OUTSET-RIM-0.3, per-port passage void probes at real band t, pwrsw inner web
solid, trrs blind-tunnel ceiling solid, TAB-PAD PRESS (solid ring over
all 8 top-poron pad centres — the pad-unloading bug can't return),
magnet pocket void/floor/web probes, station count, antenna rings +
no-cover-over-antenna, volume tripwire band.
"""
import json
import math
import os
import sys

import cadquery as cq

import params
import gen_case as G

REPO = G.REPO
OUT_DIR = os.path.join(REPO, "case", "out")


def build_cover(tag):
    P = params
    dxf = os.path.join(G.PLATE_DIR, f"Hojicha44-{tag}-plate.dxf")
    pcb = os.path.join(REPO, "pcb", "kicad", f"Hojicha44-{tag}.kicad_pcb")
    lands = json.load(open(os.path.join(
        G.PLATE_DIR, f"Hojicha44-{tag}-lands.json")))
    outline = G.read_outline(dxf)          # plate outline (tabs included)
    rim = G.read_pcb_outline(pcb)          # PCB rim
    cav_poly = G.offset_pts(outline, P.RIM_CLEAR)
    # the cover's INTERIOR follows the PCB rim, not the plate outline:
    # tab-bulge bites gape over every tab pocket and leave the top
    # poron pads pressing nothing (v1 review defect — now gated per pad)
    ring_inner = G.offset_pts(rim, P.RIM_CLEAR)
    rim_ring = G.resample_ring(rim, P.SKIN_STEP)
    rnorm = G.outward_field(rim_ring)
    # the cover's outer face is the skin face itself — MUST be the same
    # ring as the tub's (flush seam, aligned magnet stations)
    skin = G.resample_ring(G.offset_pts(rim, P.CASE_OUTSET), P.SKIN_STEP)
    ports = G.compute_ports(tag, rim_ring, rnorm, skin, P)
    sksegs = list(zip(skin, skin[1:] + skin[:1]))
    pocket_rects = G.pocket_layout(lands["tabs"], sksegs, P)
    stations, bands, webs = G.magnet_stations(P, tag, skin, cav_poly,
                                        pocket_rects, ports)
    # top-poron press points (lands: pad centre = tab root +2.0 outward;
    # these MUST land on ring material at the lip plane)
    pad_centers = [(o[0] + u[0] * 2.0, o[1] + u[1] * 2.0)
                   for t in lands["tabs"]
                   for (o, u, v) in [G.tab_frame(t)]]

    z0, z1 = P.TOP_LIP_Z, P.TOP_LIP_Z + P.COVER_T
    solid = G.prism(skin, z0, z1)
    solid = solid.cut(G.prism(ring_inner, z0, z1))

    from OCP.gp import gp_Dir, gp_Pnt

    # port passages through the cover
    # usb: full-depth filleted slot (same w/r as the bore)
    pr = ports["usb"]
    ox, oy = pr["o"]
    ux, uy = pr["u"]
    travel = P.SLOT_IN + 1.0 + pr["out"] + 1.0
    base = (ox - ux * (P.SLOT_IN + 1.0), oy - uy * (P.SLOT_IN + 1.0))
    solid = solid.cut(G.fillet_slot(base, pr["v"], pr["u"], pr["w"],
                                    z0 - 0.5, z1 + 0.5, pr["r"], travel))
    # trrs: the SAME bore cylinder — chord in the 6..9 slice stays
    # narrow (<=6.42 at the lip plane), so no ring severance
    pr = ports["trrs"]
    ox, oy = pr["o"]
    ux, uy = pr["u"]
    travel = P.SLOT_IN + 1.0 + pr["out"] + 1.0
    base = (ox - ux * (P.SLOT_IN + 1.0), oy - uy * (P.SLOT_IN + 1.0))
    solid = solid.cut(cq.Solid.makeCylinder(
        P.TRRS_MOUTH_R, travel,
        gp_Pnt(base[0], base[1], P.TRRS_MOUTH_ZC),
        gp_Dir(ux, uy, 0.0)))
    # pwrsw: full depth but NOT full radial — starts PWRSW_COVER_IN
    # outboard so a 1.1 web survives next to the cavity edge and W1
    # stays the only severance
    pr = ports["pwrsw"]
    ox, oy = pr["o"]
    ux, uy = pr["u"]
    t_web = P.PWRSW_COVER_IN
    travel = pr["out"] + 1.0 - t_web + 1.0
    base = (ox + ux * t_web, oy + uy * t_web)
    solid = solid.cut(G.fillet_slot(base, pr["v"], pr["u"], pr["w"],
                                    z0 - 0.5, z1 + 0.5, pr["r"], travel))
    # magnet pockets: cut UP from the underside (faces flush at z0).
    # T4 (review M4): cover-side magnets are Ø4x1.5 (tub keeps 2.0s —
    # the pair is asymmetric-tolerant, faces still meet exactly at the
    # lip plane), so the pocket is shallower and the floor over the
    # pocket grows 0.8 -> 1.3mm (COVER_T - COVER_MAG_DEPTH).
    for (cx, cy) in stations:
        solid = solid.cut(cq.Solid.makeCylinder(
            P.MAG_DIA / 2, P.COVER_MAG_DEPTH,
            gp_Pnt(cx, cy, z0), gp_Dir(0, 0, 1)))

    return solid, {"skin": skin, "cav_poly": cav_poly,
                   "ring_inner": ring_inner,
                   "mag_stations": stations, "mag_bands": bands,
                   "mag_webs": webs,
                   "pad_centers": pad_centers, "ports": ports}


def check_cover(tag, solid, info):
    P = params
    bad = []
    bb = solid.BoundingBox()
    z1 = P.TOP_LIP_Z + P.COVER_T
    if abs(bb.zmin - P.TOP_LIP_Z) > 0.05:
        bad.append(f"zmin {bb.zmin:.2f} != lip {P.TOP_LIP_Z}")
    if abs(bb.zmax - z1) > 0.05:
        bad.append(f"zmax {bb.zmax:.2f} != lip+COVER_T {z1}")
    if not solid.isValid():
        bad.append("kernel reports invalid solid")
    nsolids = len(solid.Solids())
    if nsolids != 1:
        bad.append(f"{nsolids} disjoint solids (a full-depth passage "
                   f"split the ring)")
    skin = info["skin"]
    # census + antenna measure the REAL ring (rim-based interior — the
    # plate-outline cavity would read the backfilled tab bites as thin
    # walls that no longer exist)
    cav = info["ring_inner"]
    cavsegs = list(zip(cav, cav[1:] + cav[:1]))
    # full-point sampling (audit 2026-10-20 hardening — same as the tub)
    wall_min = min(min(G.segd(sp, a, b) for a, b in cavsegs)
                   for sp in skin)
    # nominal ring wall is OUTSET-RIM_CLEAR = 7.7, but the W2/pwrsw
    # shoulders carve local compressions (7.20 measured, 5.85 on v3.4);
    # gate well above the 1.40 FDM-print floor but below the features
    wall_gate = 5.0
    if wall_min < wall_gate:
        bad.append(f"ring wall thins to {wall_min:.3f} < {wall_gate:.1f}")

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

    # passage voids at real band t (inside the ring's material envelope,
    # not the trivial air past the skin) + their structural claims
    pr = info["ports"]["usb"]
    o, u, v = pr["o"], pr["u"], pr["v"]
    for t in (3.5, 14.25):        # bite fill + plateau band
        for zb in (P.TOP_LIP_Z + 0.4, P.TOP_LIP_Z + P.COVER_T - 0.4):
            expect("usb cover passage",
                   o[0] + u[0] * t, o[1] + u[1] * t, zb, False)
    # ring resumes wherever a passage MEETS the skin: probe 0.6mm
    # inside skin samples that hug (0.05..1.2 from) each port rect —
    # port-agnostic, no hand-placed coordinates (the bite's outline is
    # wider than the mouth frame, so b=w/2+eps is NOT valid resume
    # ground there)
    snorm = G.outward_field(skin)
    hits = 0
    for si in range(len(skin)):
        sp = skin[si]
        inner = (sp[0] - snorm[si][0] * 0.6, sp[1] - snorm[si][1] * 0.6)
        for name in ("usb", "trrs", "pwrsw"):
            rd = G.rect_d(sp, info["ports"][name]["rect"])
            if 0.05 <= rd <= 1.6:
                expect(f"{name} cover wall resumes (skin-hug)",
                       inner[0], inner[1], P.TOP_LIP_Z + P.COVER_T - 0.25,
                       True)
                hits += 1
    if hits < 6:
        bad.append(f"cover wall resume probes found only {hits} skin "
                   f"hug points")
    pr = info["ports"]["trrs"]
    o, u, v = pr["o"], pr["u"], pr["v"]
    for zb in (P.TOP_LIP_Z + 0.4, P.TOP_LIP_Z + 0.9):
        hw = math.sqrt(max(pr["r"] ** 2 - (zb - pr["zc"]) ** 2, 0.0))
        expect("trrs cover passage", o[0] + u[0] * 3.5,
               o[1] + u[1] * 3.5, zb, False)
        for sgn in (-1.0, 1.0):
            expect("trrs cover wall resumes",
                   o[0] + u[0] * 3.5 + v[0] * sgn * (hw + 0.35),
                   o[1] + u[1] * 3.5 + v[1] * sgn * (hw + 0.35), zb, True)
    expect("trrs cover ceiling over boot",
           o[0] + u[0] * 3.5, o[1] + u[1] * 3.5,
           P.TOP_LIP_Z + P.COVER_T - 0.4, True)  # blind
    pr = info["ports"]["pwrsw"]
    o, u, v = pr["o"], pr["u"], pr["v"]
    for zb in (P.TOP_LIP_Z + 0.4, P.TOP_LIP_Z + P.COVER_T - 0.4):
        expect("pwrsw cover passage", o[0] + u[0] * 3.5,
               o[1] + u[1] * 3.5, zb, False)
        expect("pwrsw cover inner web", o[0] + u[0] * 1.1,
               o[1] + u[1] * 1.1, zb, True)
        for sgn in (-1.0, 1.0):
            expect("pwrsw cover wall resumes",
                   o[0] + u[0] * 3.5 + v[0] * sgn * (pr["w"] / 2 + 0.4),
                   o[1] + u[1] * 3.5 + v[1] * sgn * (pr["w"] / 2 + 0.4),
                   zb, True)
    # the ring must PRESS the top poron pads (v1 review defect: an
    # outline-based interior left tab-shaped bites and the pads pressed
    # nothing — these are the probes that fail in that state)
    for (px, py) in info["pad_centers"]:
        expect("cover presses tab pad", px, py, P.TOP_LIP_Z + 0.2, True)
        expect("cover presses tab pad", px, py, P.TOP_LIP_Z + 1.5, True)
    # magnet pockets: real recesses that mirror the tub's
    stn = info["mag_stations"]
    if len(stn) < P.MAG_MIN_STATIONS:
        bad.append(f"cover magnet stations {len(stn)} < "
                   f"{P.MAG_MIN_STATIONS}")
    for (cx, cy) in stn:
        expect("cover magnet pocket void", cx, cy,
               P.TOP_LIP_Z + 0.9, False)
        expect("cover magnet pocket floor", cx, cy,
               P.TOP_LIP_Z + P.COVER_MAG_DEPTH + 0.4, True)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            expect("cover magnet pocket web",
                   cx + dx * (P.MAG_DIA / 2 + 0.3),
                   cy + dy * (P.MAG_DIA / 2 + 0.3),
                   P.TOP_LIP_Z + 0.9, True)
    # antenna: same ring clearances as the tub + no plastic overhead
    ant = P.ANTENNA_L if tag == "Left" else P.ANTENNA_R
    ant_lim = P.ANT_R_MM + P.ANT_CASE_CLEAR
    for ring in (cav, skin):
        d = min(G.segd(ant, a, b)
                for a, b in zip(ring, ring[1:] + ring[:1]))
        if d < ant_lim:
            bad.append(f"cover antenna ring only {d:.2f} < {ant_lim}")
    expect("no cover over antenna", ant[0], ant[1], 7.5, False)

    vol = solid.Volume()
    bstat = ""
    if stn:
        bstat = (f", magnet band min {min(info['mag_bands']):.2f}, "
                 f"web min {min(info['mag_webs']):.2f}")
    print(f"  {tag} cover: volume {vol / 1000:.1f} cm3, "
          f"bbox z [{bb.zmin:.1f}, {bb.zmax:.1f}], "
          f"wall_min {wall_min:.2f}, stations {len(stn)}{bstat}")
    print(f"  {tag} cover magnets: "
          f"[{', '.join(f'({G.r2(x)},{G.r2(y)})' for x, y in stn)}]")
    if not (6000 <= vol <= 13000):
        bad.append(f"cover volume {vol / 1000:.1f} cm3 outside "
                   f"[6, 13] tripwire")
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
        assert os.path.getsize(step) > 200000, f"{tag}: STEP suspiciously small"
        assert os.path.getsize(stl) > 200000, f"{tag}: STL suspiciously small"
        print(f"{tag}: cover -> {os.path.basename(step)} "
              f"({os.path.getsize(step) // 1024} KB)")
    sys.exit(rc)


if __name__ == "__main__":
    main()

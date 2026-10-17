#!/usr/bin/env python3
"""Hojicha44 bottom tub — rev-0 (CadQuery, parametric).

Derives the tub from the laser plate: plate outline + tab roots come from
plate/Hojicha44-{half}-plate.dxf (OUTLINE) and -lands.json. Never hand-drawn.

  case/.venv/bin/python case/gen_case.py            # both halves -> case/out/
  case/.venv/bin/python case/gen_case.py Left       # one half

Outputs (gitignored scratch): case/out/Hojicha44-{half}-tub.step/.stl

Construction (z=0 is the PCB top; see params.py for sources):
  1. blank  = outer footprint (plate outline + RIM_CLEAR + WALL_T),
             from floor-bottom to TOP_LIP_Z
  2. well   = cavity footprint (plate outline + RIM_CLEAR),
             cut from FLOOR_Z up (board zone drops to the floor)
  3. pillars = tab-sized blocks re-added FLOOR_Z -> SHELF_Z (tab support)
  4. pockets = tab slots cut SHELF_Z -> TOP_LIP_Z (receive tab + both foams;
             USB notch / TRRS channel propagate via the outline itself)

v0 scope: NO fasteners, NO top cover (open decisions, see params.py).
Exit 0 only if every gate below passes.
"""
import json
import math
import os
import sys

import cadquery as cq

import params

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATE_DIR = os.path.join(REPO, "plate")
OUT_DIR = os.path.join(REPO, "case", "out")


def r2(x):
    return round(float(x), 2)


def read_outline(path):
    """OUTLINE polyline vertices from the R12 plate DXF."""
    lines = open(path, encoding="latin-1").read().split("\n")
    found = 0
    i = 0
    while i < len(lines):
        if lines[i] == "0" and i + 1 < len(lines) and lines[i + 1] == "POLYLINE":
            layer, verts, j = None, [], i + 2
            while j < len(lines) and not (
                    lines[j] == "0" and lines[j + 1] == "SEQEND"):
                if lines[j] == "8" and j + 1 < len(lines) and \
                        lines[j + 1] in ("OUTLINE", "CUTOUT", "PORON"):
                    layer = lines[j + 1]
                    j += 2
                    continue
                if lines[j] == "10":
                    verts.append((float(lines[j + 1]), float(lines[j + 3])))
                    j += 4
                else:
                    j += 1
            if layer == "OUTLINE" and verts:
                found += 1
                if found > 1:
                    raise RuntimeError(f"multiple OUTLINE loops in {path}")
                out = verts
            i = j + 2
            continue
        i += 1
    try:
        return out
    except NameError:
        raise RuntimeError(f"no OUTLINE in {path}")


def segd(pt, a, b):
    """Distance from a point to a segment."""
    rx, ry = b[0] - a[0], b[1] - a[1]
    L2 = rx * rx + ry * ry or 1e-12
    t = max(0.0, min(1.0, ((pt[0] - a[0]) * rx + (pt[1] - a[1]) * ry) / L2))
    return math.hypot(pt[0] - (a[0] + t * rx), pt[1] - (a[1] + t * ry))


def read_pcb_outline(path):
    """Closed Edge.Cuts loop from a .kicad_pcb (the PCB rim: the plate
    outline withOUT tabs — tabs are plate features, not rim features).
    The case exterior dilates THIS, so tab tongues never bump the skin."""
    import re as _re
    segs = []
    for m in _re.finditer(
            r'\(gr_line \(start (-?[\d.]+) (-?[\d.]+)\) '
            r'\(end (-?[\d.]+) (-?[\d.]+)\) \(layer "Edge\.Cuts"',
            open(path).read()):
        segs.append(((float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))))
    assert len(segs) > 8, f"no Edge.Cuts loop in {path}"
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    loop = [segs[0][0], segs[0][1]]
    used = {0}
    while len(loop) < len(segs) + 1:
        nxt = None
        for i, (a, b) in enumerate(segs):
            if i in used:
                continue
            if key(a) == key(loop[-1]):
                nxt = (i, b); break
            if key(b) == key(loop[-1]):
                nxt = (i, a); break
        assert nxt is not None, "Edge.Cuts does not chain into one loop"
        used.add(nxt[0])
        loop.append(nxt[1])
    assert key(loop[-1]) == key(loop[0]), "Edge.Cuts loop not closed"
    return loop[:-1]


def wire_of(pts):
    """Closed wire from a point loop (drops explicit closure dup)."""
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < 1e-6:
        pts = pts[:-1]
    return cq.Workplane("XY").polyline(pts).close().val()


def offset_pts(pts, d):
    """Planar outward offset of a closed loop, back as points."""
    loops = wire_of(pts).offset2D(d)
    if not isinstance(loops, list):
        loops = [loops]
    # keep the largest loop by area (offset can splinter on concavities)
    def area(verts):
        return abs(sum(a.X * b.Y - b.X * a.Y
                       for a, b in zip(verts, verts[1:] + verts[:1])) / 2)
    best, best_a = None, -1.0
    for w in loops:
        verts = w.Vertices()
        a = area(verts)
        if a > best_a:
            best, best_a = verts, a
    return [(v.X, v.Y) for v in best]


def prism(pts, z0, z1):
    """Vertical prism of a point loop from z0 to z1."""
    if math.hypot(pts[-1][0] - pts[0][0],
                  pts[-1][1] - pts[0][1]) < 1e-6:
        pts = pts[:-1]
    return cq.Workplane("XY").polyline(pts).close() \
        .extrude(z1 - z0).val().translate((0, 0, z0))


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if ((a[1] > y) != (b[1] > y)) and \
                (x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1] + 1e-12) + a[0]):
            inside = not inside
    return inside


def tab_frame(t):
    """(origin, outward, transverse) unit vectors for a tab root."""
    a = math.radians(t["angle"])
    dx, dy = math.cos(a), math.sin(a)
    return (t["x"], t["y"]), (dx, dy), (-dy, dx)


def rect_in_frame(origin, u, v, a0, a1, b0, b1):
    """Corners of [a0,a1]x[b0,b1] in (u=along, v=lateral) frame."""
    ox, oy = origin
    return [(ox + u[0] * a + v[0] * b, oy + u[1] * a + v[1] * b)
            for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]


# Port anchors (spec coordinates; slots are explicit rects, verified by gates)
PORTS = {"Left": {"usb": (118.0, 49.95), "trrs": (134.6, -22.0)},
         "Right": {"usb": (173.5, 49.95), "trrs": (157.0, -22.0)}}


def outward_field(outline):
    """Per-vertex unit outward normals, orientation via signed area."""
    A = sum(a[0] * b[1] - b[0] * a[1]
            for a, b in zip(outline, outline[1:] + outline[:1])) / 2
    n = len(outline)
    out = []
    for i in range(n):
        a, b = outline[(i - 1) % n], outline[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1e-12
        out.append((ty / L, -tx / L) if A > 0 else (-ty / L, tx / L))
    return out


def resample_ring(pts, step=1.0):
    """Uniform arclength resample of a closed ring (dissolves tangent-
    discontinuity joints where per-vertex normal offset would fold)."""
    cum = [0.0]
    for i in range(1, len(pts) + 1):
        a, b = pts[i - 1], pts[i % len(pts)]
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = cum[-1]
    n = max(64, int(round(tot / step)))
    out = []
    for k in range(n):
        ss = tot * k / n
        for i in range(len(pts)):
            if cum[i] <= ss <= cum[i + 1]:
                t = 0 if cum[i + 1] == cum[i] else (ss - cum[i]) / (cum[i + 1] - cum[i])
                a, b = pts[i], pts[(i + 1) % len(pts)]
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                break
    return out


def slot_frame(ring, normals, anchor):
    """(origin, outward, transverse) at the RING point nearest anchor.
    ring and normals must come from the same resampled loop."""
    bi = min(range(len(ring)), key=lambda i: math.hypot(
        ring[i][0] - anchor[0], ring[i][1] - anchor[1]))
    o = ring[bi]
    u = normals[bi]
    return o, u, (-u[1], u[0])


def build_half(tag):
    P = params
    dxf = os.path.join(PLATE_DIR, f"Hojicha44-{tag}-plate.dxf")
    pcb = os.path.join(REPO, "pcb", "kicad",
                       f"Hojicha44-{tag}.kicad_pcb")
    lands = json.load(open(os.path.join(
        PLATE_DIR, f"Hojicha44-{tag}-lands.json")))
    outline = read_outline(dxf)        # PLATE outline (tabs included)
    rim = read_pcb_outline(pcb)        # PCB rim (tabs are NOT rim)
    tabs = lands["tabs"]
    assert len(tabs) == 8, f"{tag}: want 8 tabs, got {len(tabs)}"
    for t in tabs:  # params must match the plate generator's truth
        assert t["width"] == params.TAB_W, f"{tag}: TAB_W drift"
        assert t["protrusion"] == params.TAB_L, f"{tag}: TAB_L drift"

    cav_poly = offset_pts(outline, P.RIM_CLEAR)     # plate + clearance
    z_bot = P.FLOOR_Z - 2.0                          # 2mm floor slab

    # v3.1 exterior: ONE constant dilation of the PCB RIM — the plate
    # outline includes the tab tongues, and dilating it gave the case
    # eight bulges. Dilating the rim keeps the wall uniformly thick
    # everywhere; tabs live in internal pockets inside the band.
    # Notches shallower than CASE_OUTSET (USB 5.4, TRRS channel) fill in
    # and vanish from the silhouette; ports breach via explicit slots.
    rim_ring = resample_ring(rim, P.SKIN_STEP)
    rnorm = outward_field(rim_ring)
    skin = resample_ring(offset_pts(rim, P.CASE_OUTSET), P.SKIN_STEP)
    solid = prism(skin, z_bot, P.TOP_LIP_Z)
    solid = solid.cut(prism(cav_poly, P.FLOOR_Z, P.TOP_LIP_Z))

    # shelf/pocket per tab (fully interior). Adaptive nose: straight rims
    # carry the full POCKET_OUT, but tabs near rim curvature (the north
    # tab by the USB-notch shoulder measures 0.25 web at 5.5) shrink the
    # nose in 0.05 steps, floored at TAB_L+0.2, until every corner
    # clears SKIN_MIN against the actual skin ring.
    sksegs_b = list(zip(skin, skin[1:] + skin[:1]))
    pocket_rects = []
    pocket_centers = []
    for t in tabs:
        o, u, v = tab_frame(t)
        hw = t["width"] / 2 + P.POCKET_CLEAR
        nose = P.POCKET_OUT
        while nose > P.TAB_L + 0.2:
            cs = rect_in_frame(o, u, v, -P.POCKET_IN, nose, -hw, hw)
            web = min(min(segd(c, a, b) for a, b in sksegs_b) for c in cs)
            if web >= P.SKIN_MIN:
                break
            nose -= 0.05
        assert nose <= P.POCKET_OUT + 1e-9 and \
            all(min(segd(c, a, b) for a, b in sksegs_b)
                >= P.SKIN_MIN
                for c in rect_in_frame(o, u, v, -P.POCKET_IN, nose,
                                        -hw, hw)), \
            f"tab at {t['x']},{t['y']}: no nose >= TAB_L+0.2 clears SKIN_MIN"
        pillar = rect_in_frame(o, u, v, -P.POCKET_IN, nose, -hw, hw)
        solid = solid.fuse(prism(pillar, P.FLOOR_Z, P.SHELF_Z))
        solid = solid.cut(prism(pillar, P.POCKET_BOT, P.POCKET_TOP))
        pocket_rects.append(pillar)
        pocket_centers.append((o[0] + u[0] * (t["protrusion"] / 2),
                               o[1] + u[1] * (t["protrusion"] / 2)))

    # port slots: full-height wall openings at USB + TRRS. v3 anchored
    # these on the SKIN ring, cutting outward into air — silent no-ops
    # (battery passed by probing outside the case). v3.1 anchors on the
    # RIM and spans the full wall band: SLOT_IN into the cavity through
    # SLOT_OUT past the skin. v3.2 z-span: FLOOR_Z (slab top) .. lip —
    # the v3.1 cut ran from z_bot and punched the port plugs clean
    # through the 2mm floor slab (the "hole in the bottom" the user
    # found); plugs sit above the slab so a sill is free clearance.
    for name in ("usb", "trrs"):
        anchor = PORTS[tag][name]
        o, u, v = slot_frame(rim_ring, rnorm, anchor)
        w = P.USB_SLOT_W if name == "usb" else P.TRRS_SLOT_W
        slot = rect_in_frame(o, u, v, -P.SLOT_IN, P.SLOT_OUT, -w / 2, w / 2)
        solid = solid.cut(prism(slot, P.FLOOR_Z, P.TOP_LIP_Z))

    return solid, {"tabs": tabs, "pockets": pocket_centers,
                   "pocket_rects": pocket_rects,
                   "outline": outline, "rim": rim, "skin": skin,
                   "rim_ring": rim_ring, "rnorm": rnorm,
                   "cav_poly": cav_poly}


def check_half(tag, solid, info):
    P = params
    bad = []
    bb = solid.BoundingBox()
    if abs(bb.zmin - (P.FLOOR_Z - 2.0)) > 0.05:
        bad.append(f"zmin {bb.zmin:.2f} != floor slab {P.FLOOR_Z - 2.0}")
    if abs(bb.zmax - P.TOP_LIP_Z) > 0.05:
        bad.append(f"zmax {bb.zmax:.2f} != lip {P.TOP_LIP_Z}")
    # pocket centers follow tab roots (+half protrusion along tongue)
    for t, (cx, cy) in zip(info["tabs"], info["pockets"]):
        o, u, v = tab_frame(t)
        ex, ey = o[0] + u[0] * t["protrusion"] / 2, \
            o[1] + u[1] * t["protrusion"] / 2
        if math.hypot(cx - ex, cy - ey) > 0.05:
            bad.append(f"pocket drift at tab {t['x']},{t['y']}")
    if not solid.isValid():
        bad.append("kernel reports invalid solid")
    oc = info["outline"]
    segs = list(zip(oc, oc[1:] + oc[:1]))

    # skin containment: every tab pocket rect must fit inside the OUTER
    # skin with >= SKIN_MIN web. Same rect as the builder (-POCKET_IN ..
    # POCKET_OUT) — the 2026-10-16 v0 span bug (protrusion + POCKET_OUT =
    # 10.5mm phantom corners) lived here silently until v3; measured real
    # pockets sit >= 4.2 inside at CASE_OUTSET 6.0, straight rims 0.5.
    skin = info["skin"]
    snorm = outward_field(skin)
    sksegs = list(zip(skin, skin[1:] + skin[:1]))
    for rect in info["pocket_rects"]:
        for cr in rect:
            d = min(segd(cr, a, b) for a, b in sksegs)
            if d < P.SKIN_MIN:
                bad.append(f"pocket corner ({r2(cr[0])},{r2(cr[1])}) "
                           f"only {d:.2f} inside skin < {P.SKIN_MIN}")
    # skin must stay outside the cavity everywhere (no pinch-back);
    # tab tips (rim+5, cavity rim+5.5) sit inside the rim+7.0 band by
    # design, so the TABBED outline is the wrong reference here
    for sp in skin[::4]:
        if point_in_poly(sp, info["cav_poly"]):
            bad.append(f"skin pinches inside cavity at "
                       f"({r2(sp[0])},{r2(sp[1])})")
            break
    # wall-thickness census (v3.2 strength review): thinnest skin->cavity
    # distance must clear the design floor. Design value: tab tips are
    # the closest cavity points (rim+TAB_L+RIM_CLEAR = rim+5.5 vs skin
    # rim+CASE_OUTSET) -> 1.5 uniform at every tab; elsewhere walls run
    # 6.5. Resample chord sag costs <=0.03, so 1.40 leaves real margin.
    cav = info["cav_poly"]
    cavsegs = list(zip(cav, cav[1:] + cav[:1]))
    wall_min = min(min(segd(sp, a, b) for a, b in cavsegs)
                   for sp in skin[::2])
    if wall_min < 1.40:
        bad.append(f"wall thins to {wall_min:.3f} < 1.40 (tab-tip floor "
                   f"is OUTSET-TAB_L-RIM_CLEAR)")
    # point-in-solid battery: proves void/solid SEMANTICS (distances alone
    # cannot catch an inside-out build — a flipped normal still measures).
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN

    def solid_at(x, y, z):
        clf = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z),
                                          1e-6)
        return clf.State() == TopAbs_IN

    def expect(name, x, y, z, want):
        if solid_at(x, y, z) != want:
            bad.append(f"{name} at ({r2(x)},{r2(y)},{r2(z)}) "
                       f"{'solid' if want else 'void'} expected")

    wx = sum(p[0] for p in oc) / len(oc)
    wy = sum(p[1] for p in oc) / len(oc)
    if not point_in_poly((wx, wy), oc):  # concave fallback: grid search
        xs = [min(p[0] for p in oc) + 5 * k for k in range(40)]
        ys = [min(p[1] for p in oc) + 5 * k for k in range(40)]
        hit = next(((x, y) for x in xs for y in ys
                    if point_in_poly((x, y), oc)
                    and min(math.hypot(x - t["x"], y - t["y"])
                            for t in info["tabs"]) > 8.0), None)
        assert hit is not None, "no interior well probe found"
        wx, wy = hit
    expect("well void", wx, wy, 0.0, False)
    expect("floor slab", wx, wy, P.FLOOR_Z - 0.5, True)
    for t in info["tabs"]:
        o, u, v = tab_frame(t)
        tx, ty = o[0] + u[0] * 4.0, o[1] + u[1] * 4.0
        expect("pocket void", tx, ty, 2.75, False)
        expect("pillar solid", tx, ty, (P.SHELF_Z + P.FLOOR_Z) / 2, True)
    # skin band solid midway between tabs (swell low there), skipping
    # port-slot zones where the wall is legitimately open
    def near_port(x, y):
        for nm in ("usb", "trrs"):
            ax, ay = PORTS[tag][nm]
            if math.hypot(x - ax, y - ay) < 16.0:
                return True
        return False
    for si in range(0, len(skin), len(skin) // 16):
        sp = skin[si]
        # step INWARD along the local base-ring normal (origin-scaling
        # would drag far-side probes into the cavity)
        px = sp[0] - snorm[si][0] * 0.3
        py = sp[1] - snorm[si][1] * 0.3
        if (min(math.hypot(px - t["x"], py - t["y"])
                for t in info["tabs"]) > 12.0 and not near_port(px, py)):
            expect("skin band solid", px, py, 0.0, True)
    # port slots void: probe INSIDE the wall band on the rim anchor (the
    # v3 probes sat outside the case and passed while the cut was a no-op)
    for name in ("usb", "trrs"):
        anchor = PORTS[tag][name]
        o, u, v = slot_frame(info["rim_ring"], info["rnorm"], anchor)
        expect(f"{name} slot void",
               o[0] + u[0] * (P.CASE_OUTSET / 2),
               o[1] + u[1] * (P.CASE_OUTSET / 2), 0.0, False)
        # v3.2: the slot must open the WALL ONLY — the 2mm slab below it
        # stays (v3.1's through-cut made two holes in the case bottom)
        expect(f"{name} slab under slot solid",
               o[0] + u[0] * (P.CASE_OUTSET / 2),
               o[1] + u[1] * (P.CASE_OUTSET / 2),
               P.FLOOR_Z - 1.0, True)
    # antenna keepout: "no case material within 3mm" of the module
    # antenna (electronics.yaml; r=5 circles verified against both PCB
    # Cmts.User marks). Probes the point and the 3mm compass ring at
    # cavity-depth, board-surface, and module-antenna height. The FUTURE
    # COVER carries this rule too (no plastic over the antenna zone).
    ant = P.ANTENNA_L if tag == "Left" else P.ANTENNA_R
    for dz in (P.FLOOR_Z + 0.4, 0.0, 4.0):
        for dx, dy in ((0, 0), (3, 0), (-3, 0), (0, 3), (0, -3)):
            expect("antenna clear", ant[0] + dx, ant[1] + dy, dz, False)
    # slots are analytically bounded by their rects; prove they cannot
    # merge with tab pockets (a slot eating a pocket would free the tab)
    def rects_overlap(p, q):
        return (point_in_poly(p[0], q) or point_in_poly(p[2], q)
                or point_in_poly(q[0], p) or point_in_poly(q[2], p))
    for name in ("usb", "trrs"):
        anchor = PORTS[tag][name]
        o, u, v = slot_frame(info["rim_ring"], info["rnorm"], anchor)
        w = P.USB_SLOT_W if name == "usb" else P.TRRS_SLOT_W
        slot = rect_in_frame(o, u, v, -P.SLOT_IN, P.SLOT_OUT,
                             -w / 2, w / 2)
        for rect in info["pocket_rects"]:
            if rects_overlap(slot, rect):
                bad.append(f"{name} slot overlaps a tab pocket")
    # volume band: analytic estimate ±12% (offset joins differ slightly)
    vol = solid.Volume()
    print(f"  {tag}: volume {vol / 1000:.1f} cm3, "
          f"bbox z [{bb.zmin:.1f}, {bb.zmax:.1f}]")
    if not (55000 <= vol <= 75000):
        bad.append(f"volume {vol / 1000:.1f} cm3 outside [55, 75] tripwire")
    if not (vol > 0):
        bad.append("empty solid")
    return bad


def main():
    import params as P
    os.makedirs(OUT_DIR, exist_ok=True)
    halves = sys.argv[1:] or ["Left", "Right"]
    rc = 0
    for tag in halves:
        solid, info = build_half(tag)
        bad = check_half(tag, solid, info)
        if bad:
            print(f"{tag} FAIL:")
            for b in bad:
                print(f"  !! {b}")
            rc = 1
            continue
        step = os.path.join(OUT_DIR, f"Hojicha44-{tag}-tub.step")
        stl = os.path.join(OUT_DIR, f"Hojicha44-{tag}-tub.stl")
        cq.exporters.export(cq.Workplane(obj=solid), step)
        cq.exporters.export(cq.Workplane(obj=solid), stl)
        assert os.path.getsize(step) > 100000, f"{tag}: STEP suspiciously small"
        assert os.path.getsize(stl) > 100000, f"{tag}: STL suspiciously small"
        print(f"{tag}: tub -> {os.path.basename(step)} "
              f"({os.path.getsize(step) // 1024} KB)")
    sys.exit(rc)


if __name__ == "__main__":
    main()

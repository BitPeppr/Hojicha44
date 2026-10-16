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


def hex_prism(cx, cy, r_circ, z0, z1):
    pts = [(cx + r_circ * math.cos(math.pi / 6 + k * math.pi / 3),
            cy + r_circ * math.sin(math.pi / 6 + k * math.pi / 3))
           for k in range(6)]
    return prism(pts, z0, z1)


def cyl_prism(cx, cy, r, z0, z1, n=24):
    pts = [(cx + r * math.cos(2 * math.pi * k / n),
            cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return prism(pts, z0, z1)


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


# Exclusion zones for fastener bosses (approximate, documented):
# USB plug swing + TRRS mouth recess. Bosses must never sit in a notch void.
EXCL = {"Left": {"usb": (118.0, 49.95), "trrs": (128.0, -30.0, 143.0, -14.0)},
        "Right": {"usb": (173.5, 49.95), "trrs": (148.0, -30.0, 163.0, -14.0)}}
EXCL_R = 14.0  # radius around the USB anchor; TRRS box as given


def outward_normal(outline, idx):
    """Unit outward normal at outline[idx] (centroid-side test)."""
    n = len(outline)
    a, b = outline[(idx - 2) % n], outline[(idx + 2) % n]
    tx, ty = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, ty) or 1e-12
    for cand in ((ty / L, -tx / L), (-ty / L, tx / L)):
        p = outline[idx]
        probe = (p[0] + cand[0] * 2.0, p[1] + cand[1] * 2.0)
        if not point_in_poly(probe, outline):
            return cand
    return (ty / L, -tx / L)


def boss_sites(outline, tabs, tag, P):
    """N_BOSS rim indices midway between tab roots, exclusions applied."""
    n = len(outline)
    # nearest outline index per tab root
    root_idx = []
    for t in tabs:
        bi = min(range(n), key=lambda i: math.hypot(
            outline[i][0] - t["x"], outline[i][1] - t["y"]))
        root_idx.append(bi)
    root_idx.sort()
    sites = []
    E = EXCL[tag]
    for k in range(len(root_idx)):
        a, b = root_idx[k], root_idx[(k + 1) % len(root_idx)]
        mid = (a + ((b - a) % n) // 2) % n
        p = outline[mid]
        # exclusions: USB radius, TRRS box, tab proximity (12mm)
        if math.hypot(p[0] - E["usb"][0], p[1] - E["usb"][1]) < EXCL_R:
            continue
        x0, y0, x1, y1 = E["trrs"]
        if x0 - 4 < p[0] < x1 + 4 and y0 - 4 < p[1] < y1 + 4:
            continue
        if min(math.hypot(p[0] - t["x"], p[1] - t["y"]) for t in tabs) < 12.0:
            continue
        # local straightness over +-6mm (tangent swing < 12 deg)
        angs = []
        for d in range(-6, 7, 2):
            q, r = outline[(mid + d - 1) % n], outline[(mid + d + 1) % n]
            angs.append(math.atan2(r[1] - q[1], r[0] - q[0]))
        if max(angs) - min(angs) > math.radians(12):
            continue
        sites.append(mid)
    # even out: greedily keep N_BOSS farthest-apart by arclength
    def dist(a, b):
        d = abs(a - b) % n
        return min(d, n - d)
    keep = []
    pool = sites[:]
    while pool and len(keep) < P.N_BOSS:
        nxt = max(pool, key=lambda s: min([dist(s, k) for k in keep] + [1e9]))
        keep.append(nxt)
        pool.remove(nxt)
    return sorted(keep)


def build_half(tag):
    P = params
    dxf = os.path.join(PLATE_DIR, f"Hojicha44-{tag}-plate.dxf")
    lands = json.load(open(os.path.join(
        PLATE_DIR, f"Hojicha44-{tag}-lands.json")))
    outline = read_outline(dxf)
    tabs = lands["tabs"]
    assert len(tabs) == 8, f"{tag}: want 8 tabs, got {len(tabs)}"
    for t in tabs:  # params must match the plate generator's truth
        assert t["width"] == params.TAB_W, f"{tag}: TAB_W drift"
        assert t["protrusion"] == params.TAB_L, f"{tag}: TAB_L drift"

    cav_poly = offset_pts(outline, P.RIM_CLEAR)          # plate + clearance
    outer_poly = offset_pts(outline, P.RIM_CLEAR + P.WALL_T)

    z_bot = P.FLOOR_Z - 2.0  # 2mm floor slab

    def dedupe(pts, tol=0.05):
        out = [pts[0]]
        for p in pts[1:]:
            if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= tol:
                out.append(p)
        return out
    outer_poly, cav_poly = dedupe(outer_poly), dedupe(cav_poly)

    # stepped outer wall (stacked-layer look; kernel tapered extrude and
    # ordered loft both choke on this outline, so the draft is explicit):
    # +3.5 base, +3.0 middle, +2.5 top.
    z1, z2 = -3.0, 1.6
    solid = prism(offset_pts(outline, P.RIM_CLEAR + P.WALL_T + P.WALL_FLARE),
                  z_bot, z1)
    solid = solid.fuse(prism(offset_pts(outline, P.RIM_CLEAR + P.WALL_T + P.WALL_FLARE / 2), z1, z2))
    solid = solid.fuse(prism(outer_poly, z2, P.TOP_LIP_Z))
    solid = solid.cut(prism(cav_poly, P.FLOOR_Z, P.TOP_LIP_Z))

    # captive-nut bosses (M3 nylon, no inserts, no metal)
    sites = boss_sites(outline, tabs, tag, P)
    assert len(sites) == P.N_BOSS, \
        f"{tag}: {len(sites)} boss sites, want {P.N_BOSS}"
    bosses = []
    for idx in sites:
        nrm = outward_normal(outline, idx)
        cx = outline[idx][0] + nrm[0] * P.FAST_C
        cy = outline[idx][1] + nrm[1] * P.FAST_C
        solid = solid.fuse(cyl_prism(cx, cy, P.FAST_R, z_bot,
                                     P.TOP_LIP_Z, n=32))
        solid = solid.cut(hex_prism(cx, cy, P.NUT_AF / math.sqrt(3),
                                    z_bot, z_bot + P.NUT_DEPTH))
        # flared mouth: eases nut entry, absorbs first-layer elephant foot
        solid = solid.cut(hex_prism(cx, cy, P.NUT_AF / math.sqrt(3) + P.NUT_FLARE_R,
                                    z_bot, z_bot + P.NUT_FLARE_H))
        solid = solid.cut(cyl_prism(cx, cy, P.SCREW_R, z_bot,
                                    P.TOP_LIP_Z, n=16))
        bosses.append((cx, cy))

    pocket_centers = []
    for t in tabs:
        o, u, v = tab_frame(t)
        hw = t["width"] / 2 + P.POCKET_CLEAR
        # shelf pillar: tab footprint + clearance, floor -> shelf
        pillar = rect_in_frame(o, u, v, -P.POCKET_IN,
                               t["protrusion"] + P.POCKET_OUT - 0.0, -hw, hw)
        solid = solid.fuse(prism(pillar, P.FLOOR_Z, P.SHELF_Z))
        # pocket slot: same footprint, shelf -> lip (receives tab + foams)
        pocket = rect_in_frame(o, u, v, -P.POCKET_IN,
                               t["protrusion"] + P.POCKET_OUT, -hw, hw)
        solid = solid.cut(prism(pocket, P.POCKET_BOT, P.POCKET_TOP))
        cx = o[0] + u[0] * (t["protrusion"] / 2)
        cy = o[1] + u[1] * (t["protrusion"] / 2)
        pocket_centers.append((cx, cy))

    return solid, {"tabs": tabs, "pockets": pocket_centers,
                   "outline": outline, "bosses": bosses}


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
    # bosses: standoff from the plate outline, clear of tab pockets
    oc = info["outline"]
    segs = list(zip(oc, oc[1:] + oc[:1]))

    def segd(pt, a, b):
        rx, ry = b[0] - a[0], b[1] - a[1]
        L2 = rx * rx + ry * ry or 1e-12
        t = max(0.0, min(1.0, ((pt[0] - a[0]) * rx + (pt[1] - a[1]) * ry) / L2))
        return math.hypot(pt[0] - (a[0] + t * rx), pt[1] - (a[1] + t * ry))

    for cx, cy in info.get("bosses", []):
        dd = min(segd((cx, cy), a, b) for a, b in segs)
        # boss EDGE must clear the cavity (+0.5) with 0.3 margin:
        # center distance >= FAST_R + RIM_CLEAR + 0.3 = 5.3
        if dd < P.FAST_R + P.RIM_CLEAR + 0.3:
            bad.append(f"boss at {r2(cx)},{r2(cy)} intrudes "
                       f"(edge clear {dd - P.FAST_R:.2f} < 0.8)")
        # boss disc must clear every tab pocket rect (boss r + 0.5)
        for t in info["tabs"]:
            o, u, v = tab_frame(t)
            lx = (cx - o[0]) * u[0] + (cy - o[1]) * u[1]
            ly = (cx - o[0]) * v[0] + (cy - o[1]) * v[1]
            dx = max(-P.POCKET_IN - lx, 0.0,
                     lx - (t["protrusion"] + P.POCKET_OUT))
            dy = max(-(t["width"] / 2 + P.POCKET_CLEAR) - ly, 0.0,
                     ly - (t["width"] / 2 + P.POCKET_CLEAR))
            if math.hypot(dx, dy) < P.FAST_R + 0.5:
                bad.append(f"boss at {r2(cx)},{r2(cy)} crowds "
                           f"tab pocket ({math.hypot(dx, dy):.2f} < 5.0)")
    # nut pocket + flare inside boss material (analytic): hex R 3.29,
    # flared R 3.79, vs boss r 4.5
    if P.NUT_AF / math.sqrt(3) + P.NUT_FLARE_R > P.FAST_R - 0.5:
        bad.append("nut pocket breaks boss wall")
    if len(info.get("bosses", [])) != params.N_BOSS:
        bad.append("boss count drift")
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
    # board well: void above the floor, slab below
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
    for cx, cy in info.get("bosses", []):
        expect("boss meat", cx + 3.0, cy, 0.0, True)
        expect("pilot void", cx, cy, 0.0, False)
        expect("nut void", cx, cy, P.FLOOR_Z - 2.0 + 1.0, False)
    bs = info.get("bosses", [])
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            if math.hypot(bs[i][0] - bs[j][0], bs[i][1] - bs[j][1]) < 15.0:
                bad.append("boss pair too close")
    # volume band: analytic estimate ±12% (offset joins differ slightly)
    vol = solid.Volume()
    print(f"  {tag}: volume {vol / 1000:.1f} cm3, "
          f"bbox z [{bb.zmin:.1f}, {bb.zmax:.1f}]")
    if not (45000 <= vol <= 60000):
        bad.append(f"volume {vol / 1000:.1f} cm3 outside [45, 60] tripwire")
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

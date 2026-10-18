#!/usr/bin/env python3
"""Hojicha44 bottom tub — v3.5 (CadQuery, parametric).

Derives the tub from the plate + PCB: plate outline and tab roots from
plate/Hojicha44-{half}-plate.dxf (OUTLINE) and -lands.json, the PCB rim
(rim = plate outline MINUS tabs) from pcb/kicad/Hojicha44-{half}.kicad_pcb.
Never hand-drawn; one generic build_half() routine, both halves.

  case/.venv/bin/python case/gen_case.py            # both halves -> case/out/
  case/.venv/bin/python case/gen_case.py Left       # one half

Outputs (gitignored scratch): case/out/Hojicha44-{half}-tub.step/.stl

Construction (z=0 is the PCB top; see params.py for sources):
  1. solid   = prism(skin) from the floor bottom (-7.6) to TOP_LIP_Z,
               skin = ONE CASE_OUTSET dilation of the PCB rim (v3: no
               tab bulges, no bosses)
  2. well    = prism(plate outline + RIM_CLEAR) cut FLOOR_Z..lip
               (the board zone drops to the floor step)
  3. pillars = tab-sized blocks re-added FLOOR_Z..SHELF_Z (tab support)
  4. pockets = tab slots cut SHELF_Z..lip (receive tab + both foams)
  5. port mouths = USB/TRRS/pwrsw shaped bores (bottom-filleted slots,
                round TRRS bore) whose outer extent is measured to
                actually breach the skin (v3.3) and whose z bands are
                sized to the real plugs/actuator (v3.4, params.py)
  6. magnets = Ø4.2x2.2 recessed pockets in the wall-band top face at
                measured-wide stations (v3.5 zero-gap retention stack;
                the ring cover glues its magnets face-down opposite —
                adjacent faces meet at TOP_LIP_Z, a rigid stop)

Gates (check_half, exit 0 only if every one passes): bbox, pocket
drift, single-solid topology, pocket-corner webs >= SKIN_MIN, no skin
pinch into the cavity, wall census >= 1.40, the void/solid classifier
battery (well, slab, pockets, pillars, skin band unmasked, bore
mouths at two z planes, air beyond the mouths, slab under mouths,
antenna envelope rings), bore-vs-pocket separation >= 3mm (SAT),
magnet pocket void/floor/web probes + station-count floor, per-port
tolerance census print, volume tripwire.
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


# Port anchors (slot frame anchors, KiCad frame):
# usb   = points.yaml helper usb / mirror_usb (mcu + [0,17.95])
# trrs  = jack MOUTH centres derived from the layout trrs anchor
#         (130.5/-22) via the PCB placement chain: anchor ± 8.05
#         (gen_pcb.py TRRS rot-90 dX) + footprint mouth y 12.1
#         -> 134.55 (L) / 156.95 (R), rounded.
# pwrsw = the ACTUATOR MOUTH centre on the north rim plateau, NOT the
#         switch footprint (SW_LPWR1/SW_RPWR1 sit at 102/189.5, 51
#         after the M2 review shift — the footprint moved 2mm WEST so
#         the actuator blade band sits under this fixed window; the
#         mouth itself cannot move: SAT-constrained, pocket >=3.2 /
#         USB ~1.8 margins). The plateau is the raw Edge.Cuts line
#         y=58.0 across x 97.5..110.5 (mirror 181..194), so the frame
#         is axis-aligned EXACT (no resample-phase wobble): a wobbly
#         +/-.5 anchor x swings the slot into tab-4's pocket (east edge
#         x=100.59; SAT floor 3 wants west edge >= 103.6) or onto the
#         notch shoulder (110.5). The mouth centre 106.3 clears both;
#         blade/throw stays exposed (body now spans x 97..107).
# Slots are explicit rects whose outer extent is measured to actually
# breach the skin.
PORTS = {"Left": {"usb": (118.0, 49.95), "trrs": (134.6, -22.0),
                  "pwrsw": (106.3, 58.0)},
         "Right": {"usb": (173.5, 49.95), "trrs": (157.0, -22.0),
                   "pwrsw": (185.2, 58.0)}}


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


def fillet_slot(base, v, u, w, z0, z1, r, travel):
    """Bottom-filleted slot swept along u (profile plane xDir = v, flat
    top past z1). Shared by the tub ports and the cover passages."""
    pl = cq.Plane(origin=(base[0], base[1], 0.0),
                  xDir=(v[0], v[1], 0.0),
                  normal=(u[0], u[1], 0.0))
    s45 = r * math.sqrt(0.5)
    return (cq.Workplane(pl)
            .moveTo(-w / 2, z0 + r)
            .lineTo(-w / 2, z1).lineTo(w / 2, z1)
            .lineTo(w / 2, z0 + r)
            .threePointArc((w / 2 - r + s45, z0 + r - s45),
                           (w / 2 - r, z0))
            .lineTo(-w / 2 + r, z0)
            .threePointArc((-w / 2 + r - s45, z0 + r - s45),
                           (-w / 2, z0 + r))
            .close()
            .extrude(travel)
            .val())


def pocket_layout(tabs, sksegs, P):
    """Tab pocket rects with the adaptive-nose rule. Shared by
    build_half (pillar fuse + pocket cut) and gen_cover.py, which needs
    the same tab footprint for magnet-station separation. Straight rims
    carry the full POCKET_OUT, but tabs near rim curvature (the north
    tab by the USB-notch shoulder measures 0.25 web at 5.5) shrink the
    nose in 0.05 steps, floored at TAB_L+0.2, until every corner clears
    SKIN_MIN against the actual skin ring."""
    rects = []
    for t in tabs:
        o, u, v = tab_frame(t)
        hw = t["width"] / 2 + P.POCKET_CLEAR
        nose = P.POCKET_OUT
        while nose > P.TAB_L + 0.2:
            cs = rect_in_frame(o, u, v, -P.POCKET_IN, nose, -hw, hw)
            web = min(min(segd(c, a, b) for a, b in sksegs) for c in cs)
            if web >= P.SKIN_MIN:
                break
            nose -= 0.05
        rect = rect_in_frame(o, u, v, -P.POCKET_IN, nose, -hw, hw)
        assert nose <= P.POCKET_OUT + 1e-9 and \
            all(min(segd(c, a, b) for a, b in sksegs) >= P.SKIN_MIN
                for c in rect), \
            f"tab at {t['x']},{t['y']}: no nose >= TAB_L+0.2 clears SKIN_MIN"
        rects.append(rect)
    return rects


def compute_ports(tag, rim_ring, rnorm, skin, P):
    """Measured-breach port set for one half: usb, trrs, pwrsw.

    BOTH build_half (tub cuts) and gen_cover.py (passages) MUST come
    through here so the two parts share anchors, widths and the
    measured outer extent — a port the cover doesn't know about is a
    port the cover will bridge over.

    History: v3 anchored these on the SKIN ring, cutting outward into
    air — silent no-ops (the battery passed by probing outside the
    case). v3.1 anchored on the RIM with a FIXED outer extent; v3.2
    moved the z-span down to FLOOR_Z (slab top) .. lip, which made
    each port a full-height 11.6mm rectangle (the user rightly called
    the result "gaping"); v3.3 kept that z band and MEASURED the outer
    extent instead — the v3.1 fixed SLOT_OUT=8.5 shipped the USB port
    sealed shut on BOTH halves, because inside the USB notch the
    7.0-dilated skin bridges ~17mm north of the rim (arc envelope of
    the notch-mouth corners). v3.4 keeps the measured breach and
    shapes each bore to the plug; v3.5 adds the pwrsw actuator window.
    check_half re-proves the breach on the finished solid (mouth
    probes at two z planes, air beyond, slab solid under each bore).
    """
    ports = {}
    for name in ("usb", "trrs", "pwrsw"):
        anchor = PORTS[tag][name]
        if name == "pwrsw":
            # exact axis-aligned plateau frame (see PORTS comment) —
            # the raw rim line is y=58.0 there, so no resample phase
            o = anchor
            u = (0.0, 1.0)
        else:
            o, u, v = slot_frame(rim_ring, rnorm, anchor)
        v = (-u[1], u[0])
        if name == "usb":
            w = P.USB_MOUTH_W
        elif name == "pwrsw":
            w = P.PWRSW_MOUTH_W
        else:
            w = 2 * P.TRRS_MOUTH_R

        def face_pts(a):
            return [(o[0] + u[0] * a + v[0] * b,
                     o[1] + u[1] * a + v[1] * b)
                    for b in (-w / 2 + w * k / 8 for k in range(9))]

        # march the bore face outward (0.5mm steps) until every point
        # across the FULL width clears the skin ring, plus
        # SLOT_BREACH_MARGIN — the fixed-extent v3.1 lesson.
        out = P.SLOT_OUT
        while any(point_in_poly(p, skin) for p in face_pts(out)):
            out += 0.5
            if out >= 40.0:
                raise RuntimeError(
                    f"{tag} {name}: no skin breach within 40mm")
        out += P.SLOT_BREACH_MARGIN
        travel = P.SLOT_IN + 1.0 + out + 1.0
        base = (o[0] - u[0] * (P.SLOT_IN + 1.0),
                o[1] - u[1] * (P.SLOT_IN + 1.0))
        if name == "trrs":
            from OCP.gp import gp_Dir, gp_Pnt
            cut = cq.Solid.makeCylinder(
                P.TRRS_MOUTH_R, travel,
                gp_Pnt(base[0], base[1], P.TRRS_MOUTH_ZC),
                gp_Dir(u[0], u[1], 0.0))
            d = {"kind": "circle", "zc": P.TRRS_MOUTH_ZC,
                 "r": P.TRRS_MOUTH_R}
        else:
            # bottom-filleted slot with a flat top PAST the case top
            # plane (the mouth's top face becomes the solid's own top
            # face, no coincident-face seam), rounded under.
            z0 = P.USB_MOUTH_Z0 if name == "usb" else P.PWRSW_MOUTH_Z0
            r = P.USB_MOUTH_R if name == "usb" else P.PWRSW_MOUTH_R
            z1 = P.TOP_LIP_Z + P.SLOT_PAST_TOP
            cut = fillet_slot(base, v, u, w, z0, z1, r, travel)
            d = {"kind": "fillet", "z0": z0, "z1": z1, "r": r}
        d.update(o=o, u=u, v=v, w=w, out=out, cut=cut)
        d["rect"] = rect_in_frame(o, u, v, -P.SLOT_IN, out, -w / 2, w / 2)
        ports[name] = d
    return ports


def rect_d(pt, rect):
    """True point-to-rect distance: 0 when the point is INSIDE the rect
    (edge-distance alone reads a deep-inside point as 'far' — it
    reported 6.7 for a point centred in the USB bore's rect)."""
    if point_in_poly(pt, rect):
        return 0.0
    return min(segd(pt, a, b)
               for a, b in zip(rect, rect[1:] + rect[:1]))


def magnet_stations(P, tag, skin, cav, pocket_rects, ports):
    """Recessed-magnet stations on the wall-band top face (v3.5).

    Candidates walk the CAVITY boundary outward into the band. A station
    centers a ØMAG_DIA pocket with:
      - >= (MAG_STATION_BAND - MAG_DIA) / 2 web to BOTH boundaries,
      - >= 3mm beyond the magnet radius from every port rect and every
        tab pocket rect (a recess must never merge with a void),
      - >= ANT_R_MM + ANT_CASE_CLEAR beyond the magnet radius from the
        antenna centre,
      - MAG_MIN_SEP arc separation between chosen stations.
    Candidate rings rotate to start at the USB anchor so mirrored
    halves pick mirrored stations from identical geometry; slots are
    snapped at tot/MAG_MAX_STATIONS spacing. Returns ([(cx, cy), ...],
    [local band width at each station, ...]).
    """
    cav_ring = resample_ring(cav, P.SKIN_STEP)
    n = len(cav_ring)
    ua = PORTS[tag]["usb"]
    bi = min(range(n), key=lambda i: math.hypot(
        cav_ring[i][0] - ua[0], cav_ring[i][1] - ua[1]))
    cav_ring = cav_ring[bi:] + cav_ring[:bi]
    cn = outward_field(cav_ring)
    arcs = [0.0] * (n + 1)
    tot = 0.0
    for i in range(1, n + 1):
        a, b = cav_ring[i - 1], cav_ring[i % n]
        tot += math.hypot(b[0] - a[0], b[1] - a[1])
        arcs[i] = tot
    sksegs = list(zip(skin, skin[1:] + skin[:1]))
    cavsegs = list(zip(cav, cav[1:] + cav[:1]))
    obstructions = list(pocket_rects) + [
        ports[k]["rect"] for k in ("usb", "trrs", "pwrsw")]
    ant = P.ANTENNA_L if tag == "Left" else P.ANTENNA_R
    ant_lim = P.ANT_R_MM + P.ANT_CASE_CLEAR + P.MAG_DIA / 2
    web = (P.MAG_STATION_BAND - P.MAG_DIA) / 2
    cands = []
    for i in range(n):
        c = cav_ring[i]
        d = min(segd(c, a, b) for a, b in sksegs)
        if d < P.MAG_STATION_BAND:
            continue
        pt = (c[0] + cn[i][0] * d / 2, c[1] + cn[i][1] * d / 2)
        # the station must sit ON the solid band: outside the cavity
        # region and inside the skin (rejections for notch/channel fjord
        # walls whose outward normal points INTO the bite's air).
        if point_in_poly(pt, cav) or not point_in_poly(pt, skin):
            continue
        # the mid-band premise (center at d/2) must hold against the
        # true boundaries, or the pocket webs disappear at obliques
        if min(segd(pt, a, b) for a, b in sksegs) < web:
            continue
        if min(segd(pt, a, b) for a, b in cavsegs) < web:
            continue
        if any(rect_d(pt, r) < P.MAG_DIA / 2 + 3.0 for r in obstructions):
            continue
        if math.hypot(pt[0] - ant[0], pt[1] - ant[1]) < ant_lim:
            continue
        cands.append((arcs[i], pt, d))
    taken = []
    step = tot / P.MAG_MAX_STATIONS
    for k in range(P.MAG_MAX_STATIONS):
        want = step * k
        best = None
        for s, cpt, d in cands:
            off = abs(s - want)
            off = min(off, tot - off)
            if off > step / 2:
                continue
            clash = False
            for s2, _, _ in taken:
                dd = abs(s - s2)
                if min(dd, tot - dd) < P.MAG_MIN_SEP:
                    clash = True
                    break
            if clash:
                continue
            if best is None or off < best[0]:
                best = (off, s, cpt, d)
        if best is not None:
            taken.append((best[1], best[2], best[3]))
    return ([p for _, p, _ in taken], [d for _, _, d in taken])


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
    # Notches shallower than CASE_OUTSET (USB ~5.45 deep, TRRS channel)
    # fill in and vanish from the silhouette; ports breach via explicit
    # slots (outer extent measured, see below).
    rim_ring = resample_ring(rim, P.SKIN_STEP)
    rnorm = outward_field(rim_ring)
    skin = resample_ring(offset_pts(rim, P.CASE_OUTSET), P.SKIN_STEP)
    solid = prism(skin, z_bot, P.TOP_LIP_Z)
    solid = solid.cut(prism(cav_poly, P.FLOOR_Z, P.TOP_LIP_Z))

    # shelf/pocket per tab (fully interior). Adaptive nose rule lives in
    # pocket_layout (shared with gen_cover.py): straight rims carry the
    # full POCKET_OUT, curved-rim tabs shrink the nose until every
    # corner clears SKIN_MIN against the actual skin ring.
    sksegs_b = list(zip(skin, skin[1:] + skin[:1]))
    pocket_rects = pocket_layout(tabs, sksegs_b, P)
    pocket_centers = []
    for t, rect in zip(tabs, pocket_rects):
        o, u, v = tab_frame(t)
        # B1 (multi-model review, blocker): the pillar shelf IS needed
        # under the tab tongue (the tab lobes are cavity in v3.1's
        # no-bulge dilation — the wall over a tab tip is only 1.5 wide),
        # but the fused rect reached 1.0mm INBOARD of the rim, putting
        # solid case material inside the PCB footprint (z -1.6..-0.55)
        # at every station: the board would rest ~1.05mm high on 8
        # pillar strips and unload the bottom pads. The shelf now starts
        # 0.3 outboard of the rim (PCB-edge fab tolerance; the foam pad
        # spans rim..rim+4, so the 0.3 sliver just bridges), and the
        # pocket VOID keeps its full -1.0 inboard clearance for the
        # tab-root fillets. Gates: "pcb footprint clear" (air at
        # root-0.5, z -1.0/-0.7) + "pillar solid" (root+4.0).
        nose = max((p[0] - o[0]) * u[0] + (p[1] - o[1]) * u[1]
                   for p in rect)
        hw = t["width"] / 2 + P.POCKET_CLEAR
        pillar = rect_in_frame(o, u, v, 0.3, nose, -hw, hw)
        solid = solid.fuse(prism(pillar, P.FLOOR_Z, P.SHELF_Z))
        solid = solid.cut(prism(rect, P.POCKET_BOT, P.POCKET_TOP))
        o, u, v = tab_frame(t)
        pocket_centers.append((o[0] + u[0] * (t["protrusion"] / 2),
                               o[1] + u[1] * (t["protrusion"] / 2)))

    # port mouths: shaped bores at USB + TRRS + pwrsw via compute_ports
    # (anchors, plug-shaped z bands and the MEASURED breach march live
    # there; the ring cover reuses the exact same dicts so both parts
    # agree on every opening). check_half re-proves the breach on the
    # finished solid (mouth probes at two z planes, air beyond, slab
    # solid under each bore).
    ports = compute_ports(tag, rim_ring, rnorm, skin, P)
    for name in ("usb", "trrs", "pwrsw"):
        solid = solid.cut(ports[name].pop("cut"))

    # v3.5 retention: recessed Ø4.2x2.2 magnet pockets in the band top
    # face. Stations are measured by magnet_stations against the SAME
    # skin ring + pocket/port rects just committed to the solid; faces
    # sit flush at TOP_LIP_Z (zero-gap against the cover's opposite
    # pair — params.py carries the preload reasoning).
    stations, bands = magnet_stations(P, tag, skin, cav_poly,
                                      pocket_rects, ports)
    from OCP.gp import gp_Dir, gp_Pnt
    for (cx, cy) in stations:
        solid = solid.cut(cq.Solid.makeCylinder(
            P.MAG_DIA / 2, P.MAG_DEPTH,
            gp_Pnt(cx, cy, P.TOP_LIP_Z - P.MAG_DEPTH), gp_Dir(0, 0, 1)))

    return solid, {"tabs": tabs, "pockets": pocket_centers,
                   "pocket_rects": pocket_rects,
                   "mag_stations": stations, "mag_bands": bands,
                   "outline": outline, "rim": rim, "skin": skin,
                   "rim_ring": rim_ring, "rnorm": rnorm,
                   "cav_poly": cav_poly, "ports": ports}


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
    nsolids = len(solid.Solids())
    if nsolids != 1:
        bad.append(f"{nsolids} disjoint solids (pillar/floor not fused)")
    oc = info["outline"]
    segs = list(zip(oc, oc[1:] + oc[:1]))

    # skin containment: every tab pocket rect must fit inside the OUTER
    # skin with >= SKIN_MIN web. Same rects as the builder — this gate
    # measured corner webs 1.15-1.55 at OUTSET 7.0 (the historical v0
    # span bug — 10.5mm phantom corners — lived here silently until v3).
    skin = info["skin"]
    snorm = outward_field(skin)
    sksegs = list(zip(skin, skin[1:] + skin[:1]))
    min_web = 9e9
    for rect in info["pocket_rects"]:
        for cr in rect:
            d = min(segd(cr, a, b) for a, b in sksegs)
            min_web = min(min_web, d)
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
        # B1 regression: nothing solid may exist INSIDE the PCB footprint
        # below z=0 (the deleted pillar fuse lived exactly at root-0.5,
        # mid-PCB-band). Probed at two depths per tab...
        for dz in (-1.0, -0.7):
            expect("pcb footprint clear",
                   o[0] - u[0] * 0.5, o[1] - u[1] * 0.5, dz, False)
    # ...plus a coarse plan-wide sweep of the PCB FOOTPRINT at z=-1.0 so
    # the same bug class cannot return through another path. Footprint =
    # the PCB rim (NOT the plate outline — the tab-tongue lobes hold the
    # legitimate pillar shelf); points within 0.3mm of the rim edge are
    # excluded as boundary tolerance. (Port bores and pocket voids are
    # air here too, so only rogue solids can fail the sweep.)
    rim = info["rim"]
    rimsegs = list(zip(rim, rim[1:] + rim[:1]))
    _xs = [p[0] for p in rim]
    _ys = [p[1] for p in rim]
    _gx = min(_xs) + 2.0
    while _gx <= max(_xs) - 2.0:
        _gy = min(_ys) + 2.0
        while _gy <= max(_ys) - 2.0:
            if point_in_poly((_gx, _gy), rim) and \
                    min(segd((_gx, _gy), a, b) for a, b in rimsegs) > 0.3:
                expect("cavity sweep z-1", _gx, _gy, -1.0, False)
            _gy += 3.0
        _gx += 3.0
    # bore cross-section half-width at height z (ground truth for the
    # probe battery below — must mirror exactly what build_half cut:
    # "circle" = round TRRS bore, "fillet" = bottom-filleted USB slot
    # with a flat top at z1, full width above the bottom fillet)
    def bore_hw(name, z):
        pr = info["ports"][name]
        if pr["kind"] == "circle":
            return math.sqrt(max(pr["r"] ** 2 - (z - pr["zc"]) ** 2, 0.0))
        if z < pr["z0"] or z >= pr["z1"]:
            return 0.0
        if z < pr["z0"] + pr["r"]:
            return (pr["w"] / 2 - pr["r"]) + math.sqrt(
                max(pr["r"] ** 2 - (pr["z0"] + pr["r"] - z) ** 2, 0.0))
        return pr["w"] / 2

    # skin band solid midway between tabs. v3.3: port zones are no
    # longer MASKED (the old 16mm anchor radius hid the USB slot's open
    # face — the exact blind spot that let the sealed-USB v3.2 through
    # with all gates green). v3.4: probes landing INSIDE a port bore's
    # cross-section at z=0 must be void (material is cut there); a bore
    # that doesn't reach z=0 (USB starts at z0=2.0) leaves the band
    # solid — the classifier tracks the bore, not the old full-height
    # rect. Everything else stays solid.
    for si in range(0, len(skin), len(skin) // 16):
        sp = skin[si]
        # step INWARD along the local base-ring normal (origin-scaling
        # would drag far-side probes into the cavity)
        px = sp[0] - snorm[si][0] * 0.3
        py = sp[1] - snorm[si][1] * 0.3
        if min(math.hypot(px - t["x"], py - t["y"])
               for t in info["tabs"]) > 12.0:
            in_bore = False
            for name in ("usb", "trrs", "pwrsw"):
                pr = info["ports"][name]
                rx, ry = px - pr["o"][0], py - pr["o"][1]
                t_along = rx * pr["u"][0] + ry * pr["u"][1]
                b_later = rx * pr["v"][0] + ry * pr["v"][1]
                if (not (-P.SLOT_IN < t_along < pr["out"])
                        or abs(b_later) >= bore_hw(name, 0.0)):
                    continue
                in_bore = True
                break
            expect("skin band over bore open" if in_bore
                   else "skin band solid", px, py, 0.0, not in_bore)
    # port mouths (v3.4 breach gates): the wall band on the rim anchor
    # must be cut, the bore MOUTH must be void across its cross-section
    # at two z planes inside the bore (the sealed-USB v3.2 shipped with
    # these positions inside solid wall and no gate watching them),
    # air just beyond the face must stay air, and the slab under each
    # bore stays solid (v3.1's through-cut made two holes in the case
    # bottom).
    for name in ("usb", "trrs", "pwrsw"):
        pr = info["ports"][name]
        o, u, v, aout = pr["o"], pr["u"], pr["v"], pr["out"]
        # wall band mid-depth probe at the bore's own mid z (circle
        # ports center zc; fillet ports span z0..z1)
        pz = pr["zc"] if pr["kind"] == "circle" else \
            (pr["z0"] + pr["z1"]) / 2
        expect(f"{name} bore void",
               o[0] + u[0] * (P.CASE_OUTSET / 2),
               o[1] + u[1] * (P.CASE_OUTSET / 2), pz, False)
        if pr["kind"] == "circle":
            zlo = pr["zc"] - pr["r"] * 0.55
            zhi = pr["zc"] + pr["r"] * 0.55
        else:
            span = pr["z1"] - pr["z0"]
            zlo = pr["z0"] + 0.25 * span
            zhi = pr["z0"] + 0.75 * span
        for zb in (zlo, zhi):
            hw = bore_hw(name, zb) * 0.9
            for k in range(9):
                b = -hw + 2 * hw * k / 8
                expect(f"{name} mouth",
                       o[0] + u[0] * (aout - 0.5) + v[0] * b,
                       o[1] + u[1] * (aout - 0.5) + v[1] * b, zb, False)
            hwa = bore_hw(name, zb) * 0.8
            for k in (0, 4, 8):
                b = -hwa + hwa * 2 * k / 8
                expect(f"{name} air beyond mouth",
                       o[0] + u[0] * (aout + 3.0) + v[0] * b,
                       o[1] + u[1] * (aout + 3.0) + v[1] * b, zb, False)
        # v3.2: the bore must open the WALL ONLY — the 2mm slab below it
        # stays (v3.1's through-cut made two holes in the case bottom)
        expect(f"{name} slab under bore solid",
               o[0] + u[0] * (P.CASE_OUTSET / 2),
               o[1] + u[1] * (P.CASE_OUTSET / 2),
               P.FLOOR_Z - 1.0, True)
    # antenna keepout: "no case material within ANT_CASE_CLEAR of the
    # r=ANT_R module circle" (electronics.yaml; circles verified against
    # both PCB Cmts.User marks). Gate the envelope, not stray compass
    # points: the whole 3mm band around the circle must be open air at
    # four z planes (rings at 2.5/5.0/7.5mm from the centre, 24
    # azimuths), the centre must sit inside the cavity air, and the
    # distance to both ring boundaries must clear ANT_R+ANT_CASE_CLEAR
    # (any case material lies between the cavity edge and the skin, so
    # bounding BOTH distances bounds every material point). The FUTURE
    # COVER carries this rule too (no plastic over the antenna zone).
    ant = P.ANTENNA_L if tag == "Left" else P.ANTENNA_R
    if not point_in_poly(ant, info["cav_poly"]):
        bad.append("antenna centre is not inside cavity air")
    ant_lim = P.ANT_R_MM + P.ANT_CASE_CLEAR
    ant_d = 9e9
    for ring, segs in ((info["cav_poly"], None), (skin, None)):
        d = min(segd(ant, a, b) for a, b in zip(ring, ring[1:] + ring[:1]))
        ant_d = min(ant_d, d)
        if d < ant_lim:
            bad.append(f"antenna ring only {d:.2f} from a skin boundary "
                       f"(< {ant_lim:.1f} clearance)")
    for ring_r in (P.ANT_R_MM - P.ANT_CASE_CLEAR + 0.5, P.ANT_R_MM,
                   P.ANT_R_MM + P.ANT_CASE_CLEAR - 0.5):
        for k in range(24):
            aa = 2 * math.pi * k / 24
            px = ant[0] + ring_r * math.cos(aa)
            py = ant[1] + ring_r * math.sin(aa)
            for zb in (-2.0, 0.0, 2.0, 4.0):
                expect("antenna envelope open", px, py, zb, False)
    # bores are analytically bounded by their rects; prove they cannot
    # merge with tab pockets (a bore eating a pocket would free the
    # tab). Corner-containment overlap tests are UNSOUND (a crossing
    # with no corner inside either rect hides); use SAT over all
    # separating axes of both rects — a projection gap is a LOWER
    # bound on true separation, so max-gap >= 3 proves distance >= 3
    # and max-gap <= 0 proves penetration. The rects BOUND the bores
    # (the fillet/circle regions are subsets), so this stays sound.
    def rect_sep_gap(p, q):
        gaps = []
        for r in (p, q):
            ux, uy = r[1][0] - r[0][0], r[1][1] - r[0][1]
            L = math.hypot(ux, uy) or 1e-12
            for ax, ay in ((ux / L, uy / L), (-uy / L, ux / L)):
                pa = [a[0] * ax + a[1] * ay for a in p]
                pb = [b[0] * ax + b[1] * ay for b in q]
                gaps.append(max(min(pb) - max(pa), min(pa) - max(pb)))
        return max(gaps)

    for name in ("usb", "trrs", "pwrsw"):
        bore = info["ports"][name]["rect"]
        for rect in info["pocket_rects"]:
            sep = rect_sep_gap(bore, rect)
            if sep <= 0:
                bad.append(f"{name} bore overlaps a tab pocket")
            elif sep < 3.0:
                bad.append(f"{name} bore only {sep:.2f} from a pocket "
                           f"(< 3)")
    # v3.5 magnet pockets: each recess must be a real hole in the band
    # top (void at half depth), properly floored (solid just below the
    # pocket bottom), and walled (the station gates promise ~1.1 webs;
    # the classifier proves them on the finished solid).
    stn = info["mag_stations"]
    if len(stn) < P.MAG_MIN_STATIONS:
        bad.append(f"magnet stations {len(stn)} < {P.MAG_MIN_STATIONS}")
    for (cx, cy) in stn:
        expect("magnet pocket void", cx, cy, P.TOP_LIP_Z - 0.5, False)
        expect("magnet pocket floor", cx, cy,
               P.TOP_LIP_Z - P.MAG_DEPTH - 0.4, True)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            expect("magnet pocket web",
                   cx + dx * (P.MAG_DIA / 2 + 0.3),
                   cy + dy * (P.MAG_DIA / 2 + 0.3), P.TOP_LIP_Z - 0.5,
                   True)
    # volume band: analytic estimate ±12% (offset joins differ slightly)
    vol = solid.Volume()
    outs = ", ".join(f"{n} out={info['ports'][n]['out']:.2f}"
                     for n in ("usb", "trrs", "pwrsw"))
    print(f"  {tag}: volume {vol / 1000:.1f} cm3, "
          f"bbox z [{bb.zmin:.1f}, {bb.zmax:.1f}], "
          f"wall_min {wall_min:.2f}, pocket_web_min {min_web:.2f} "
          f"({outs})")
    # per-port tolerance census (the "perfect, not too big, not too
    # tight" port contract as numbers, printed every build).
    for name in ("usb", "trrs", "pwrsw"):
        sep = min(rect_sep_gap(info["ports"][name]["rect"], rect)
                  for rect in info["pocket_rects"])
        if name == "usb":
            shape = (f"slot {P.USB_MOUTH_W:.1f}w z{P.USB_MOUTH_Z0:+.1f}"
                     f"..lip vs housing {P.USB_HOUSING_W} "
                     f"({(P.USB_MOUTH_W - P.USB_HOUSING_W) / 2:.2f}/side),"
                     f" plug bottom 2.8 ({2.8 - P.USB_MOUTH_Z0:+.1f} "
                     f"to z0)")
        elif name == "trrs":
            rneed = math.hypot(P.TRRS_FACE_HW,
                               P.TRRS_FACE_TOP - P.TRRS_MOUTH_ZC)
            shape = (f"bore Ø{2 * P.TRRS_MOUTH_R:.1f} zc"
                     f"{P.TRRS_MOUTH_ZC} vs boot Ø{P.TRRS_BOOT_DIA} "
                     f"({(2 * P.TRRS_MOUTH_R - P.TRRS_BOOT_DIA) / 2:.2f}"
                     f"/side), drop-in face r {rneed:.2f} -> "
                     f"{P.TRRS_MOUTH_R - rneed:.2f} clear")
        else:
            shape = (f"slot {P.PWRSW_MOUTH_W:.1f}w z"
                     f"{P.PWRSW_MOUTH_Z0:+.1f}..lip vs lever sweep "
                     f"{P.PWRSW_LEVER_SWEEP} "
                     f"({(P.PWRSW_MOUTH_W - P.PWRSW_LEVER_SWEEP) / 2:.2f}"
                     f"/side), nail entry {5.0 - P.PWRSW_MOUTH_Z0:.1f} "
                     f"below body top z5.0")
        print(f"  {tag} census {name}: {shape}; breached out "
              f"{info['ports'][name]['out']:.2f}, pocket SAT {sep:.2f}")
    if stn:
        print(f"  {tag} census magnets: {len(stn)} stations "
              f"[{', '.join(f'({r2(x)},{r2(y)})' for x, y in stn)}], "
              f"band min {min(info['mag_bands']):.2f}, web min "
              f"{(min(info['mag_bands']) - P.MAG_DIA) / 2:.2f}, "
              f"ant margin {ant_d:.2f} (r{P.ANT_R_MM:.0f}"
              f"+{P.ANT_CASE_CLEAR:.0f}+{P.MAG_DIA / 2:.1f})")
    else:
        print(f"  {tag} census magnets: none eligible")
    if not (55000 <= vol <= 75000):
        bad.append(f"volume {vol / 1000:.1f} cm3 outside [55, 75] tripwire")
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

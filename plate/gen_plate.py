#!/usr/bin/env python3
"""Hojicha44 plate + gasket generator — rev-1.

Derives the laser-cut switch plate from the placed PCB (generator-owned
geometry, never hand-drawn):

  outline  = PCB Edge.Cuts loop, identical (USB notch included, so the
             plug housing passes the plate edge exactly as it passes the PCB)
  cutouts  = 22x 15x15mm Choc PG1350 squares at switch instances/rotations
  encoder  = 16.2x12.4mm window (instance rot 0, body axis-aligned):
             clears the encoder's 14.95x11.70 terminal-block envelope
             (measured off the vendored STEP, which the rev-2 plate band
             z 1.00..2.20 now intersects) AND clears the neighbour key
             cutout where a 17mm round hole would merge into it; the 13mm
             knob rides high on the 20mm shaft (bore never enters the hole)
  W1       = switch strip + MCU/cell/USB + JST windows (slide switch 6.4,
             module/cell stack, JST ~5.75 — all taller than the plate top
             at GAP+PLATE_THICK = 3.5mm)
  W2       = TRRS window + channel opening to the split-gap edge (jack
             mouth must exit; the plug overlaps plate-top height)
  tabs     = TAB_N gasket tongues spliced into the outline (tab-and-jacket
             suspension): TAB_W wide, TAB_L proud, TAB_FILLET root fillets,
             chamfered tips; silicone jackets in the case swallow them so
             the assembly floats. Every switch + the encoder must sit near
             a tab root (MAX_TAB_DIST, set from evidence).

Stack contract (spec/case.md): 1.5mm PC plate, 2.0mm PCB-to-plate gap
(top-side diodes are 1.35mm, module underside 4.5mm).

Usage:
  python3 plate/gen_plate.py          # writes plate/
  python3 plate/gen_plate.py --check  # verify only

Outputs (gitignored scratch, like out/fit):
  plate/Hojicha44-{Left,Right}-plate.dxf   (R12, mm, layers
      OUTLINE/CUTOUT/PORON[reference-only])
  plate/Hojicha44-{Left,Right}-plate.svg   (preview, lands hatched)
  plate/Hojicha44-{Left,Right}-lands.json  (gasket map for case design)

Exit 0 only if every gate below passes.
"""
import json
import math
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "pcb", "generators"))
import frame
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
OUT_DIR = os.path.join(REPO, "plate")

# the case's port anchors (case/params.py) — stdlib-only module, loaded
# by path so the plate generator keeps its no-casualty-dependency rule
# (the plate must build without the CadQuery venv).
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "case_params", os.path.join(REPO, "case", "params.py"))
case_params = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(case_params)
# Stock-footprint search: vendored copies ship in-repo (CI-portable, see
# plate/vendor_footprints/README.md); fall back to the local KiCad install.
VENDOR_FP = os.path.join(REPO, "plate", "vendor_footprints")
STOCK_FP = os.environ.get(
    "KICAD_STOCK_FP",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

# ---- rev-2 decisions (change here, everything downstream follows) ----
# SUPPORT STRATEGY (b) — "true Choc hang": the switch must be RETAINED
# by the plate, not merely cleared by it.
# CUTOUT 15.0 -> 14.0.  Sources:
#   * the PG1350 lower body (the part that passes the plate) is 13.8
#     square (Kailh's plate-footprint datum) and the 15.0 figure is the
#     CLIP WING span -- a 15.0 hole leaves the switch unsupported in
#     the plate: it rocks, lifts out, and nothing holds it.
#   * plate thickness 1.2mm (Keebio: a Choc plate must be 1.2mm for
#     the clip to engage; at 1.5/1.6mm the "lower catch doesn't
#     engage" and the switch is held by friction alone).
#   * a 14.0 hole keeps 0.10mm/side on the 13.8 body (a 13.8 hole is
#     line-to-line and risks a switch that will not insert) while the
#     15.0 clip wing still overlaps the plate by 0.50mm/side, which is
#     what the clip arm hooks under.
#   * First-article coupon (spec/first-article.md): cut 13.8 / 14.0 /
#     14.2 / 15.0 squares in 1.2mm PC and measure retention before
#     the plate order.
CUTOUT = 14.0          # Choc PG1350 plate cutout (13.8 body + 0.1/side)
# ENCODER WINDOW.  rev-1 used a 12.7mm SQUARE hole, sized off the
# vendored ROT_EC11E STEP for the OLD plate band (z 2.0..3.5), where
# the encoder's body is 12.30 wide.  The rev-2 plate moved the band to
# z 1.00..2.20 (1.00 gap + 1.20 plate) and THAT BREAKS THE OLD HOLE:
# measured off the same vendored STEP, the encoder's cross-section is
#   z 0.0..1.5 : 14.95 wide x 11.70 deep  (the A/B/C and S1/S2
#                terminal blocks stand proud of the 12.30 body)
#   z 1.6..2.3 : 12.30 wide x 11.70 deep  (the waist)
# so in the new band the encoder needs 14.95 of width and the 12.7
# hole FOULS IT by up to 1.41mm/side — the encoder would not go
# through the plate at all.  The window is therefore sized to the
# measured ENVELOPE (not the waist): 16.2 x 12.4 gives ~0.34/side
# over the 14.95 x 11.70 envelope, and stays SYMMETRIC about the
# shaft so the two halves' windows remain exact mirrors (the encoder
# is a translated, NOT mirrored, part, so an offset window would
# break the plate's mirror gate).
# The encoder is located by its PCB pins, not by the plate (the old
# hole had 0.20/side, i.e. clearance only), so nothing is lost.
# The knob rides high on the 20mm shaft either way.
# FIRST ARTICLE: caliper the REAL encoder's terminals at z 1.0..1.5.
# If they do NOT protrude above ~1.5mm (i.e. the STEP overstates
# them), the window may be reduced to 12.7 square; the shipped plate
# must clear the model as it stands.
ENC_W = 16.2            # encoder window, x (shaft-centred)
ENC_H = 12.4            # encoder window, y (shaft-centred)
# Hard guard: the window must never shrink below the measured
# clearance envelope + 0.2/side.  These floors are the reason the
# rev-2 window is 16.2 and not 12.7.
ENC_ENV_X = 14.95       # measured: terminal-block span (vendored STEP)
ENC_ENV_Y = 11.70       # measured: body depth (vendored STEP)
assert ENC_W >= ENC_ENV_X + 0.2, f"encoder window {ENC_W} < envelope {ENC_ENV_X} + 0.2"
assert ENC_H >= ENC_ENV_Y + 0.2, f"encoder window {ENC_H} < envelope {ENC_ENV_Y} + 0.2"
PLATE_THICK = 1.2      # mm PC -- Choc v1 clip engagement (Keebio: 1.2mm)
# PCB top -> plate underside.  MEASURED from the Kailh Choc v1 outline
# drawing and a community STEP model (spec/research-open-items-2026-10-21.md
# §PG1350; the memo's S1/S3): the stack above the PCB is
#   0.0-0.9   skirt
#   0.9-1.3   the flexible clip arms, whose retaining lip engages the
#             plate's UNDERSIDE
#   2.2-3.0   the 14.8-15.0 "ears" (the flange) that bear on the
#             plate's TOP surface
# so the plate must lie between the lip (<=1.3) and the ears (2.2):
# a 1.2mm plate on a 1.00mm gap occupies 1.00..2.20 — the lip grabs
# the underside and the ears seat exactly on the top.  A 1.05 gap
# would lift the ears 0.05 into the plate, and a 1.3 gap would put the
# plate top at 2.5, straight through the ears: no grab at all.
GAP = 1.00             # PCB top -> plate underside
# DIODE RELIEF.  The 22 matrix diodes (1N4148W SOD-123) stand on the
# PCB's TOP side and are the only thing under the plate in the matrix
# field.  MEASURED from KiCad's own D_SOD-123.step (the vendored
# model): body 2.566 x 1.416mm, TOP AT 1.260mm above the seating
# plane (the repo's old "1.35" comment was 0.09 pessimistic).  With
# GAP 1.00 the plate underside would foul the diode by 0.26mm, so the
# plate carries a 0.40mm RELIEF POCKET under every diode: the pocket
# floor sits at GAP+0.40 = 1.40, i.e. 0.14mm above the diode top,
# and 0.80mm of plate is left under it.
# Alternatives rejected: (a) diodes on B.Cu — the Choc hotswap socket
# is a bottom-side part whose solder tabs and plastic body are
# asymmetric, and the switch fixes the socket's orientation, so the
# two halves' bottom copper CANNOT be mirror-symmetric and a back-side
# diode would break the project's left/right mirror discipline for no
# functional gain; (b) no relief at all — needs GAP >= 1.4, outside
# the switch's clip band.
DIODE_RELIEF_D = 0.40  # relief pocket depth in the plate underside
DIODE_BODY_L = 2.566   # measured diode body length (its local x)
DIODE_BODY_W = 1.416   # measured diode body width (its local y)
DIODE_RELIEF_CLR = 0.15  # pocket margin around the body, per side
DIODE_TOP_Z = 1.26     # measured diode top above the PCB top surface
TAB_W = 10.0             # tab width along the rim
TAB_L = 5.0              # tab protrusion past the outline
TAB_FILLET = 2.0         # root fillets (crack control, esp. carbon/acrylic)
TAB_N = 8                # tab count per half: 2 pinned corners + 6 greedy;
                             # fewer, softer mounts = more suspension
TAB_TIP_CH = 1.5         # tip chamfer (no sharp points in the case)
PORON_PAD_L = 7.0        # poron pad per tab, cut from 90x4mm strip stock.
                         # (6-review audit 2026-10-20: 8.0 pads left only
                         # 0.35mm to the kerf diamond at tight tabs — 7.0
                         # restores >=0.85/side; spec §246 carve remark is
                         # now adopted in-file)
PORON_PAD_W = 4.0
PORON_EDGE_MIN = 0.6       # ABSOLUTE floor on the pad-corner -> plate-edge
                          # margin (the kerf + part-tolerance budget).
                          # Unenforced before the 2026-10-21 audit round:
                          # reverting PORON_PAD_L to 8.0 passed every gate
                          # while silently restoring the 0.35mm
                          # kerf-fragile margin.
PORON_SPEC = 'PORON 4701-30 Very Soft 240kg/m3, 3mm adhesive (-40 strips / -50 fallback, drop-in)'
# Left tab roots, held for the Right half's exact-mirror splice. The
# greedy tab walk samples the 1mm rim grid; run independently on the
# mirrored right rim it can land on a neighbouring sample (0.07mm off)
# and make the plate/case rim asymmetric. Build Left first, then derive
# the Right roots from these coordinates and re-project them onto the
# right rim.
_LAST_LEFT_TABS = None
MAX_TAB_DIST = 55.0         # every switch + encoder must sit this near a tab
                         # root (measured worst 48.14mm at 2.5 pitches).
                         # Consistency comes from mount UNIFORMITY here, not
                         # proximity: 8 identical poron-padded tabs at even
                         # spacing share load equally, which is exactly what
                         # sparse tab suspension (cf. Satisfaction75) relies
                         # on. Encoder push stays soft by design.
MATERIAL = 'PC'          # rev-1 pick; any of PC/POM/FR4/ALU/CARBON re-gates
WEB_MIN = {            # min solid web (mm) per plate material, 1.5mm stock.
    'PC': 1.0,         # laser-cut PC is virtually unbreakable
    'POM': 1.0,        # mills beautifully, tough
    'FR4': 1.5,        # routed; glass dust, standard 1.5 holds
    'ALU': 1.5,        # laser/waterjet/CNC
    'CARBON': 2.0,     # milled only (never laser: toxic dust + delam);
                       # conductive: plate touches switch plastic + gaskets
                       # only by construction — verify at assembly
}[MATERIAL]
DIODE_CLEAR = 0.3      # min diode-to-cutout-edge (diodes stay under solid plate)
WIN_TRRS_WEST_MARGIN = 1.0  # mirror-exact with the right half's outboard
                            # tpad: 0.5 made the left window 17.55 wide vs
                            # 18.05 for a cosmetic-but-real asymmetry
WIN_FILLET = 0.5            # inside-corner relief on the big windows and
                            # the encoder hole (crack initiators); kerf
                            # rounds the cut, the FILE must not stay square

CHOC_RE = re.compile(r'SW_[LR]\d+$')
DIODE_RE = re.compile(r'D_[LR]\d+$')


def r2(x):
    return round(float(x), 2)


def rot_cw(x, y, deg):
    """KiCad rotation: clockwise-positive in the y-up frame."""
    t = math.radians(deg)
    return (x * math.cos(t) + y * math.sin(t),
            -x * math.sin(t) + y * math.cos(t))


# ---- footprint sources ----
def fp_source(lib, name):
    if lib == "Hojicha44":
        p = os.path.join(PCB_DIR, "Hojicha44.pretty", name + ".kicad_mod")
    else:
        p = os.path.join(VENDOR_FP, lib + ".pretty", name + ".kicad_mod")
        if os.path.exists(p):
            return open(p).read()
        p = os.path.join(STOCK_FP, lib + ".pretty", name + ".kicad_mod")
    return open(p).read()


def layer_bbox(src, layer):
    xs, ys = [], []
    for b in re.split(r'(?=\(fp_)', src):
        if f'(layer "{layer}")' in b:
            for n in re.findall(r'\((?:start|end|center|mid) '
                                r'(-?[\d.]+) (-?[\d.]+)\)', b):
                xs.append(float(n[0]))
                ys.append(float(n[1]))
    assert xs, f'no {layer} graphics found'
    return (min(xs), min(ys), max(xs), max(ys))


def xform_rect(x0, y0, x1, y1, cx, cy, rot):
    """Local rect -> board-axis-aligned bbox (rots here are all k*90)."""
    pts = [rot_cw(x, y, rot) for x, y in
           ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    xs = [p[0] + cx for p in pts]
    ys = [p[1] + cy for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def chamfer(poly, r):
    """Cut every vertex back by r along both adjacent edges (relief).

    Big window/encoder corners are the plate's crack initiators: a 0.5mm
    back-cut kills them in the CUT FILE itself. Vertices hanging on
    short edges (<= 2r+0.2) stay sharp — backing off would produce
    negative cuts and slivers, which the laser reads worse than the
    crack risk. (Verified: even a 0.17-corner-radius body clears this.)
    """
    out = []
    n = len(poly)
    for i, p in enumerate(poly):
        q = poly[i - 1]
        s = poly[(i + 1) % n]
        d1 = math.hypot(p[0] - q[0], p[1] - q[1])
        d2 = math.hypot(s[0] - p[0], s[1] - p[1])
        if d1 <= 2 * r + 0.2 or d2 <= 2 * r + 0.2:
            out.append(p)
            continue
        f1, f2 = r / d1, r / d2
        out.append((p[0] + (q[0] - p[0]) * f1, p[1] + (q[1] - p[1]) * f1))
        out.append((p[0] + (s[0] - p[0]) * f2, p[1] + (s[1] - p[1]) * f2))
    return out


# ---- board parsing ----
def parse_instances(path):
    # The committed board is stored y-negated so KiCad's y-up export lands
    # in the plate design frame (frame.py).  The plate is authored entirely
    # in the design frame, so convert before reading.
    lines = frame.read_design(path).splitlines()
    out = {}
    fp = at = None
    for i, ln in enumerate(lines):
        m = re.match(r'\s*\(footprint "([^"]+)"', ln)
        if m:
            fp, at = m.group(1), None
            for k in range(i, min(i + 10, len(lines))):
                a = re.match(r'\s*\(at (-?[\d.]+) (-?[\d.]+)( -?[\d.]+)?',
                             lines[k])
                if a:
                    at = (float(a.group(1)), float(a.group(2)),
                          float(a.group(3) or 0))
                    break
        r = re.search(r'\(property "Reference" "([^"]+)"', ln)
        if r and fp and at:
            out[r.group(1)] = (fp,) + at
    return out


def parse_outline(path):
    s = frame.read_design(path)
    segs = []
    for m in re.finditer(
            r'\(gr_line \(start (-?[\d.]+) (-?[\d.]+)\) '
            r'\(end (-?[\d.]+) (-?[\d.]+)\) \(layer "Edge\.Cuts"', s):
        segs.append(('line', (float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))))
    for m in re.finditer(
            r'\(gr_arc \(start (-?[\d.]+) (-?[\d.]+)\) '
            r'\(mid (-?[\d.]+) (-?[\d.]+)\) '
            r'\(end (-?[\d.]+) (-?[\d.]+)\) \(layer "Edge\.Cuts"', s):
        segs.append(('arc', (float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4))),
                     (float(m.group(5)), float(m.group(6)))))
    return segs


def arc_center(p0, pm, p1):
    (x0, y0), (x1, y1), (x2, y2) = p0, pm, p1
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    assert abs(d) > 1e-9, f'collinear arc {p0} {pm} {p1}'
    ux = ((x0 * x0 + y0 * y0) * (y1 - y2) + (x1 * x1 + y1 * y1) * (y2 - y0) +
          (x2 * x2 + y2 * y2) * (y0 - y1)) / d
    uy = ((x0 * x0 + y0 * y0) * (x2 - x1) + (x1 * x1 + y1 * y1) * (x0 - x2) +
          (x2 * x2 + y2 * y2) * (x1 - x0)) / d
    return (ux, uy)


def subdivide(seq, step=1.0):
    # seq entries are (seg, flip) from chain_loop: walk every segment in
    # CHAIN direction, or backward-stored segments spike out-and-back
    # (parallel double tracks + jumps in the resample).
    pts = []
    for s, flip in seq:
        if s[0] == 'line':
            _, a, b = s
            if flip:
                a, b = b, a
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
            for k in range(n):
                t = k / n
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        else:
            _, a, m, b = s
            if flip:
                a, b = b, a
            c = arc_center(a, m, b)
            r = math.hypot(a[0] - c[0], a[1] - c[1])
            a0 = math.atan2(a[1] - c[1], a[0] - c[0])
            am = math.atan2(m[1] - c[1], m[0] - c[0])
            a1 = math.atan2(b[1] - c[1], b[0] - c[0])

            def norm(t):
                while t <= -math.pi:
                    t += 2 * math.pi
                while t > math.pi:
                    t -= 2 * math.pi
                return t
            d1, d2 = norm(am - a0), norm(a1 - am)
            total = d1 + d2 if (d1 > 0) == (d2 > 0) else d1 - d2
            n = max(2, int(abs(r * total) / step))
            for k in range(n):
                t = a0 + total * k / n
                pts.append((c[0] + r * math.cos(t), c[1] + r * math.sin(t)))
    return pts


def chain_loop(segs):
    """Order raw segments into one closed loop."""
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    unused = list(range(len(segs)))
    seq = [(segs[0], False)]
    unused.remove(0)
    cur_end = key(segs[0][-1])
    while unused:
        nxt = flip = None
        for i in unused:
            s = segs[i]
            if key(s[1]) == cur_end:
                nxt, flip = i, False
                break
            if key(s[-1]) == cur_end:
                nxt, flip = i, True
                break
        assert nxt is not None, 'outline does not chain into one loop'
        unused.remove(nxt)
        s = segs[nxt]
        seq.append((s, flip))
        cur_end = key(s[1] if flip else s[-1])
    assert cur_end == key(seq[0][0][1]), \
        f'outline not closed (end {cur_end} vs start {key(seq[0][0][1])})'
    return seq


# ---- geometry helpers ----
def poly_area(pts):
    return abs(sum(p[0] * q[1] - q[0] * p[1]
                   for p, q in zip(pts, pts[1:] + pts[:1])) / 2)


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if ((a[1] > y) != (b[1] > y)) and \
                (x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1] + 1e-12) + a[0]):
            inside = not inside
    return inside


def seg_dist(pt, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-12
    t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / L2))
    return math.hypot(pt[0] - (a[0] + t * dx), pt[1] - (a[1] + t * dy))


def poly_dist(pt, poly):
    return min(seg_dist(pt, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def rect_poly(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def cut_poly(cx, cy, w, h, rot):
    hw, hh = w / 2, h / 2
    return [(cx + dx, cy + dy)
            for dx, dy in (rot_cw(-hw, -hh, rot), rot_cw(hw, -hh, rot),
                           rot_cw(hw, hh, rot), rot_cw(-hw, hh, rot))]


def polys_intersect(p, q):
    if any(point_in_poly(v, q) for v in p) or \
            any(point_in_poly(v, p) for v in q):
        return True
    for a, b in zip(p, p[1:] + p[:1]):
        for c, d in zip(q, q[1:] + q[:1]):
            rx, ry = b[0] - a[0], b[1] - a[1]
            sx, sy = d[0] - c[0], d[1] - c[1]
            den = rx * sy - ry * sx
            if abs(den) < 1e-12:
                continue
            t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / den
            u = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                return True
    return False


def expand_poly(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for p in poly:
        vx, vy = p[0] - cx, p[1] - cy
        L = math.hypot(vx, vy) or 1e-12
        out.append((p[0] + vx / L * d, p[1] + vy / L * d))
    return out


def rect_pt_dist(px, py, rect):
    """Min distance from point to axis-aligned rect (x0,y0,x1,y1)."""
    x0, y0, x1, y1 = rect
    dx = max(x0 - px, 0.0, px - x1)
    dy = max(y0 - py, 0.0, py - y1)
    return math.hypot(dx, dy)


def seg_hit(a, b, c, d):
    """Segment intersection params (t, u) in [0,1], or None."""
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / den
    u = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / den
    return (t, u) if 0 <= t <= 1 and 0 <= u <= 1 else None


def union_rects(p, q):
    """Boundary loops of the union of two axis-aligned rects (each given
    as 4 corners). Overlapping-with-area pairs merge into one loop;
    disjoint/touching pairs come back as two."""
    x0 = max(min(p[0][0], p[2][0]), min(q[0][0], q[2][0]))
    x1 = min(max(p[0][0], p[2][0]), max(q[0][0], q[2][0]))
    y0 = max(min(p[0][1], p[2][1]), min(q[0][1], q[2][1]))
    y1 = min(max(p[0][1], p[2][1]), max(q[0][1], q[2][1]))
    if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9:
        return [p, q]  # disjoint or merely touching: keep both loops

    def edges(poly, rid):
        pts = poly + poly[:1]
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:]))
        seq = pts if area > 0 else pts[::-1]
        return [(a, b, rid) for a, b in zip(seq, seq[1:])]

    E = edges(p, 0) + edges(q, 1)
    cut = [set() for _ in E]
    for i in range(len(E)):
        for j in range(i + 1, len(E)):
            (a, b, ri), (c, d, rj) = E[i], E[j]
            if ri == rj:
                continue
            h = seg_hit(a, b, c, d)
            if h:
                cut[i].add(round(h[0], 9))
                cut[j].add(round(h[1], 9))
    segs = []
    for k, (a, b, rid) in enumerate(E):
        ts = sorted(cut[k] | {0.0, 1.0})
        for t0, t1 in zip(ts, ts[1:]):
            if t1 - t0 < 1e-9:
                continue
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            segs.append((p0, p1))
    # kept = union boundary: subsegments with union-interior on exactly
    # one side (tested either side of the line, so boundary-coincident
    # samples cannot confuse the ray cast)
    kept = []
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1e-12
        nx, ny = -dy / L * 1e-4, dx / L * 1e-4
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        li = point_in_poly((mx + nx, my + ny), p) or \
            point_in_poly((mx + nx, my + ny), q)
        ri = point_in_poly((mx - nx, my - ny), p) or \
            point_in_poly((mx - nx, my - ny), q)
        if li + ri == 1:
            kept.append((a, b))
    loops, pool = [], kept[:]
    while pool:
        a, b = pool.pop()
        loop = [a, b]
        while True:
            nxt = next((i for i, (c, d) in enumerate(pool)
                        if math.hypot(c[0] - loop[-1][0],
                                      c[1] - loop[-1][1]) < 1e-6), None)
            if nxt is None:
                break
            c, d = pool.pop(nxt)
            loop.append(d)
        loops.append(loop)
    return loops


# ---- per-half build ----
def usb_anchor(tag):
    """(x, y) mouth anchor for the notch, parsed from points.yaml.

    The same anchor check_board uses to referee notch openness; parsing
    mirrors gen_pcb.load_points to stay yaml-dependency-free.
    """
    t = open(os.path.join(
        REPO, "layout", "generated", "v2", "points", "points.yaml")).read()
    name = "usb" if tag == "Left" else "mirror_usb"
    m = re.search(rf"^{name}:\n  x: ([-\d.]+)\n  'y': ([-\d.]+)", t, re.M)
    assert m, f"points.yaml: no {name} entry"
    return float(m.group(1)), float(m.group(2))


def build_half(tag):
    global _LAST_LEFT_TABS
    pcb = os.path.join(PCB_DIR, f'Hojicha44-{tag}.kicad_pcb')
    inst = parse_instances(pcb)
    seq = chain_loop(parse_outline(pcb))
    loop = subdivide(seq)

    sw = sorted((r, v[1], v[2], v[3]) for r, v in inst.items()
                if CHOC_RE.match(r))
    assert len(sw) == 22, f'{tag}: want 22 switches, got {len(sw)}'
    enc = [(r, v[1], v[2], v[3]) for r, v in inst.items()
           if re.match(r'ENC_[LR]1$', r)]
    assert len(enc) == 1, f'{tag}: want 1 encoder, got {enc}'
    enc = enc[0]
    di = [(r, v[1], v[2]) for r, v in inst.items() if DIODE_RE.match(r)]
    assert len(di) == 22, f'{tag}: want 22 diodes, got {len(di)}'
    tool = [(v[1], v[2]) for r, v in inst.items()
            if v[0].startswith('MountingHole:')]
    assert len(tool) == 2, f'{tag}: want 2 tooling holes, got {tool}'

    def one(pat):
        hits = [(r,) + v for r, v in inst.items() if re.match(pat, r)]
        assert len(hits) == 1, f'{tag}: want 1 {pat}, got {hits}'
        return hits[0]

    swp = one(r'SW_[LR]PWR1$')
    mcu = one(r'U_[LR]1$')
    jst = one(r'J_[LR]2$')
    trrs = one(r'J_[LR]1$')

    cuts = [cut_poly(x, y, CUTOUT, CUTOUT, rot) for _, x, y, rot in sw]

    # Diode relief pockets (support b): a 0.35mm-deep pocket in the
    # plate underside under every matrix diode, so the plate can come
    # down to GAP 1.05 without fouling the 1.26mm-tall SOD-123s.
    # The pocket follows the MEASURED body (2.566 x 1.416) + 0.15/side
    # and is rotated with the placed diode.
    diodes = [(r, v[1], v[2], v[3]) for r, v in inst.items()
              if DIODE_RE.match(r)]
    assert len(diodes) == 22, f'{tag}: want 22 diodes, got {len(diodes)}'
    relief = []
    for r, dx, dy, drot in diodes:
        hl = (DIODE_BODY_L / 2 + DIODE_RELIEF_CLR)
        hw = (DIODE_BODY_W / 2 + DIODE_RELIEF_CLR)
        a = math.radians(drot)
        ca, sa = math.cos(a), math.sin(a)
        poly = []
        for ux, uy in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)):
            # KiCad clockwise-positive rotation
            poly.append((dx + ux * ca + uy * sa, dy - ux * sa + uy * ca))
        relief.append(poly)

    # component windows, derived per half from placed part bodies
    _, swp_fp, _, _, srot = swp
    sb = layer_bbox(fp_source(*swp_fp.split(':')), 'F.CrtYd')
    sw_rect = xform_rect(sb[0] - 1.0, sb[1] - 1.0, sb[2] + 1.0, sb[3] + 1.0,
                         swp[2], swp[3], srot)
    # MCU envelope: 18.3 x 34.1 about local (-7.62, 13.97)
    mx, my, mrot = mcu[2], mcu[3], mcu[4]
    mcu_rect = xform_rect(-7.62 - 9.15 - 1.5, 13.97 - 17.05 - 1.5,
                          -7.62 + 9.15 + 1.5, 13.97 + 17.05 + 1.5,
                          mx, my, mrot)
    jb = layer_bbox(fp_source(*jst[1].split(':')), 'F.Fab')
    jst_rect = xform_rect(jb[0] - 1.5, jb[1] - 1.5, jb[2] + 1.5, jb[3] + 1.5,
                          jst[2], jst[3], jst[4])
    # W1: switch strip + MCU/cell + JST as separate loops (may overlap;
    # laser cuts the union; webs between them are not structural).
    # Core edges facing the key field pull in until the cutout web is
    # comfortable (target 2.5+) while keeping 1.0 part margin — this is
    # what keeps the plate millable in FR4/alu/carbon, not just PC.
    w_sw = rect_poly(*sw_rect)
    cx0 = min(mcu_rect[0], jst_rect[0])
    cy0 = min(mcu_rect[1], jst_rect[1])
    cx1 = max(mcu_rect[2], jst_rect[2])
    cy1 = max(mcu_rect[3], jst_rect[3])
    # unexpanded part extents (coverage floor = these minus 1.0)
    px0 = min(mcu_rect[0] + 1.5, jst_rect[0] + 1.5)
    py0 = min(mcu_rect[1] + 1.5, jst_rect[1] + 1.5)
    px1 = max(mcu_rect[2] - 1.5, jst_rect[2] - 1.5)
    py1 = max(mcu_rect[3] - 1.5, jst_rect[3] - 1.5)

    def edge_web(x0, y0, x1, y1):
        d = 1e9
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.5))
        for k in range(n + 1):
            t = k / n
            p = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            d = min(d, min(poly_dist(p, c) for c in cuts))
        return d

    while edge_web(cx0, cy0, cx0, cy1) < 2.5 and cx0 < px0 - 1.0:
        cx0 += 0.25
    while edge_web(cx1, cy0, cx1, cy1) < 2.5 and cx1 > px1 + 1.0:
        cx1 -= 0.25
    while edge_web(cx0, cy0, cx1, cy0) < 2.5 and cy0 < py0 - 1.0:
        cy0 += 0.25
    while edge_web(cx0, cy1, cx1, cy1) < 2.5 and cy1 > py1 + 1.0:
        cy1 -= 0.25
    w_core = rect_poly(cx0, cy0, cx1, cy1)
    # TRRS body in footprint frame: x +-3, y -2..12.1 (STEP bbox + mouth)
    tx, ty, trot = trrs[2], trrs[3], trrs[4]
    tb = xform_rect(-3.0, -2.0, 3.0, 12.1, 0, 0, trot)
    # channel opens to the split-gap edge: east (+x) on Left, west on Right
    xs = [p[0] for p in loop]
    edge_x = max(xs) + 1.0 if tag == 'Left' else min(xs) - 1.0
    tpad = 1.0
    if tag == 'Left':
        w_trrs = rect_poly(tx + tb[0] - WIN_TRRS_WEST_MARGIN, ty + tb[1] - tpad,
                           edge_x, ty + tb[3] + tpad)
    else:
        w_trrs = rect_poly(edge_x, ty + tb[1] - tpad,
                           tx + tb[2] + tpad, ty + tb[3] + tpad)
    # USB-plug bay (post-audit H1): the plug is 12.35 wide over an 11.0
    # notch, so its shoulders cut residual plate strips beside the notch
    # walls at z 2.0..3.5 that neither the switch strip (stops at its own
    # courtyard) nor the pulled-in core edges cover. The mouth anchor is
    # the config usb point (notch referee in check_board); the notch floor
    # is the highest outline point strictly inside the mouth window that
    # sits below the anchor (an open bite dips under it). The floor flat
    # spans mouth wall to wall, so subdivide()'s internodes keep its run
    # contiguous and its x extent IS the notch span. (A fixed-depth
    # band-min scan grabs the west/east outline edges instead — dead end.)
    # The bay runs 1.4 past each wall and north of the outline (its top
    # corners land outside the loop — benign in the window-web gate; the
    # case-side USB bore is 14.0 wide over the same span by construction).
    ux, uy = usb_anchor(tag)
    ymax = max(p[1] for p in loop)
    win = 5.5  # the config notch subtract is 11.0 wide
    inwin = [p for p in loop
             if ux - win + 0.5 < p[0] < ux + win - 0.5 and p[1] < uy - 0.5]
    yfloor = max(p[1] for p in inwin)
    fpts = sorted((p for p in loop
                   if abs(p[1] - yfloor) <= 0.3
                   and ux - win - 0.5 <= p[0] <= ux + win + 0.5),
                  key=lambda q: q[0])
    runs, cur = [], [fpts[0]]
    for p in fpts[1:]:
        if p[0] - cur[-1][0] <= 2.2:
            cur.append(p)
        else:
            runs.append(cur)
            cur = [p]
    runs.append(cur)
    cluster = max(runs, key=lambda rr: rr[-1][0] - rr[0][0])
    fx0, fx1 = cluster[0][0], cluster[-1][0]
    assert 9.0 <= fx1 - fx0 <= 13.0, \
        f'{tag}: notch floor span {fx0}..{fx1} unrecognised'
    bay = rect_poly(fx0 - 1.4, yfloor, fx1 + 1.4, ymax + 2.0)
    # switch strip + core overlap by design (shared tall-part zone): emit
    # ONE union loop instead of two overlapping rects, so the CAD shows a
    # single L opening and no phantom double-cut line. (Laser cuts the
    # union either way; this is clarity, not geometry change.)
    merged = union_rects(w_sw, w_core)
    if len(merged) == 1 and len(merged[0]) >= 6:
        mloop = merged[0]
        if math.hypot(mloop[-1][0] - mloop[0][0],
                      mloop[-1][1] - mloop[0][1]) < 1e-6:
            mloop = mloop[:-1]
        mb = union_rects(mloop, bay)
        assert len(mb) == 1 and len(mb[0]) >= 6, \
            f'{tag}: usb bay did not merge into the W1 opening ' \
            f'({len(mb)} loops)'
        mloop = mb[0]
        if math.hypot(mloop[-1][0] - mloop[0][0],
                      mloop[-1][1] - mloop[0][1]) < 1e-6:
            mloop = mloop[:-1]
        # crack audit: the big openings carry no square inside corners
        mloop = chamfer(mloop, WIN_FILLET)
        wins = [mloop, chamfer(w_trrs, WIN_FILLET)]
    else:
        wins = [w_sw, w_core, w_trrs, bay]
    win_rects = [w_sw, w_core, w_trrs, bay]  # conservative keepouts
    assert enc[3] == 0, f'{tag}: encoder rotated {enc[3]}, hole assumes 0'
    # stock footprint origin is pad A; the shaft (which must pass through
    # the plate hole) sits at local +(7.5, 2.5) — gen_pcb.py places the
    # instance at ergogen_point minus that offset, so add it back here.
    # A hole at the raw instance origin would sit 7.9mm off-shaft.
    _osx, _osy = rot_cw(7.5, 2.5, enc[3])
    enc_poly = cut_poly(enc[1] + _osx, enc[2] + _osy, ENC_W, ENC_H, 0)
    # same crack argument as the windows; verified vs the vendored EC11:
    # a body corner radius >= 0.17 keeps the body clear of a 0.5 back-cut
    enc_hole = chamfer(enc_poly, WIN_FILLET)

    bad = []

    def fail(msg):
        bad.append(f'{tag}: {msg}')

    if poly_area(loop) < 10000:
        fail(f'suspicious loop area {poly_area(loop):.0f}')

    def web(p, q):
        d = min(poly_dist(v, q) for v in p)
        return min(d, min(poly_dist(v, p) for v in q))

    for i in range(len(cuts)):
        for j in range(i + 1, len(cuts)):
            if web(cuts[i], cuts[j]) < max(2.0, WEB_MIN):
                fail(f'cutout-cutout web {web(cuts[i], cuts[j]):.2f} < {max(2.0, WEB_MIN)}')
        if min(poly_dist(v, loop) for v in cuts[i]) < WEB_MIN:
            fail(f'{sw[i][0]} cutout within {WEB_MIN} of outline')
        for wpoly in wins:
            if polys_intersect(expand_poly(cuts[i], 0.01), wpoly):
                fail(f'{sw[i][0]} cutout intersects component window')

    ex, ey = enc[1] + _osx, enc[2] + _osy  # shaft center (see above)
    if web(enc_hole, loop) < WEB_MIN:
        fail(f'encoder hole within {WEB_MIN} of outline')
    for c in cuts:
        if web(enc_hole, c) < WEB_MIN:
            fail(f'encoder hole within {WEB_MIN} of a cutout')
    for wpoly in wins:
        # overlap (dd<0) is a deliberate union; slivers (0<=dd<1) are not
        dd = web(enc_hole, wpoly)
        if 0 <= dd < WEB_MIN:
            fail(f'encoder-to-window sliver {dd:.2f} < {WEB_MIN}')

    for wpoly in wins:
        for v in wpoly:
            # window corners past the outline (USB notch void) are benign;
            # assert webs only where plate material exists
            if point_in_poly(v, loop) and poly_dist(v, loop) < WEB_MIN:
                fail(f'window corner {r2(v[0])},{r2(v[1])} web '
                     f'{poly_dist(v, loop):.2f} < {WEB_MIN}')

    for ref, dx, dy in di:
        if any(point_in_poly((dx, dy), c) for c in cuts):
            fail(f'{ref} sits inside a switch cutout')
        d = min(poly_dist((dx, dy), c) for c in cuts)
        if d < DIODE_CLEAR:
            fail(f'{ref} {d:.2f} from cutout edge < {DIODE_CLEAR}')

    # NOTE (2026-10-15): a pads-vs-cutout containment check lived here
    # and was reverted — socket solder pads sit on the FAR side of the PCB
    # and legitimately extend past the 15mm plate cutout, which clears the
    # SWITCH BODY. Plate and PCB provably share one frame instead: both
    # derive cutouts/placements from the same parsed instance (x, y, rot)
    # through the same clockwise-positive convention, whose correctness
    # on real geometry was already measured end-to-end (TRRS mouth
    # 22.40mm in spec matches placed boards to 0.01). Encoder to nearest
    # switch is 18.2mm center-to-center in both files (4.45 plate
    # edge-to-edge vs ~4.9 body-to-body on copper) — same spacing,
    # different ink. (PCB renders are y-flipped vs this north-up plate,
    # which makes identical layouts read as shifted side by side.)

    # -- gasket TABS (tab-and-jacket suspension).
    # The plate grows discrete tongues that slot into silicone jackets in
    # the case: fewer, softer mounts than rim strips, so the assembly
    # floats instead of coupling the full rim to the case. Bottom gaskets
    # go away with the strips — the PCB hangs from the plate on the
    # switches; bottom-case foam is acoustic only (spec/case.md).
    # Each tab: TAB_W wide, TAB_L proud of the outline, TAB_FILLET root
    # fillets (crack initiation control, esp. carbon/acrylic), 1.5 chamfer
    # on the tip for jacket entry. Tabs sit on straight solid rim only.
    per, cum = [loop[0]], [0.0]
    for p in loop[1:]:
        cum.append(cum[-1] + math.hypot(p[0] - per[-1][0], p[1] - per[-1][1]))
        per.append(p)
    P = cum[-1] + math.hypot(loop[0][0] - per[-1][0], loop[0][1] - per[-1][1])

    def at(s):
        s = s % P
        for k in range(len(cum)):
            c0 = cum[k]
            c1 = cum[k + 1] if k + 1 < len(cum) else P
            if c0 <= s <= c1:
                a, b = per[k], per[(k + 1) % len(per)]
                t = 0 if c1 == c0 else (s - c0) / (c1 - c0)
                tang = (b[0] - a[0], b[1] - a[1])
                L = math.hypot(*tang) or 1e-12
                return ((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t),
                        (tang[0] / L, tang[1] / L))
        return per[0], (1.0, 0.0)

    def inward(pt, tang):
        n = (-tang[1], tang[0])
        probe = (pt[0] + n[0] * 2.0, pt[1] + n[1] * 2.0)
        return n if point_in_poly(probe, loop) else (-n[0], -n[1])

    def tang_at(s):
        return at(s)[1]

    def param_of(pt):
        """Nearest closed-loop parameter + distance for a world point."""
        best = (1e9, 0.0)
        for k in range(len(loop)):
            a, b = loop[k], loop[(k + 1) % len(loop)]
            vx, vy = b[0] - a[0], b[1] - a[1]
            L2 = vx * vx + vy * vy or 1e-12
            t = max(0.0, min(1.0,
                       ((pt[0] - a[0]) * vx +
                        (pt[1] - a[1]) * vy) / L2))
            d = math.hypot(pt[0] - (a[0] + vx * t),
                           pt[1] - (a[1] + vy * t))
            if d < best[0]:
                best = (d, cum[k] + math.sqrt(L2) * t)
        return best

    def straight(s, half_span, tol_deg=6.0):
        # tabs are not precision datums; 6deg over the root span still
        # fillets cleanly (fillets are computed from local tangents) and
        # the simplicity assert backstops any residual chord error
        a0 = math.atan2(*tang_at(s - half_span)[::-1])
        a1 = math.atan2(*tang_at(s + half_span)[::-1])
        return abs((a1 - a0 + math.pi) % (2 * math.pi) - math.pi) < \
            math.radians(tol_deg)

    openings = [expand_poly(c, 0.0) for c in cuts]
    openings.append(expand_poly(enc_hole, 0.0))
    openings += [expand_poly(wpoly, 0.0) for wpoly in win_rects]
    # port mouths the cables exit through (measured from the outline)
    # + the pwrsw actuator slot (v3.5; M8 review: was missing, a future
    # tab retune could park a pocket on the flick channel — today's
    # placement clears it by the case-side SAT margin only).
    # Mirror-exact (6-review audit 2026-10-20): the right half derives
    # from the LEFT literals over the shared axis x -> 291.5 - x (pwrsw
    # was already hand-mirrored; usb/trrs carried a +0.5 drafting drift
    # that skewed only the right keep-zones). The case PORTS anchors
    # (case/params.py PORTS — the single source of truth for both
    # files: usb L (118, 49.95), trrs (134.55, -22.0), pwrsw mouth
    # centre (106.3, 58.0), mirrored per half) must stay inside these
    # keep-zones; the assert below enforces it, so re-derive the
    # literals if an anchor moves.
    L_rects = ((111.0, 45.0, 125.0, 60.0),      # usb
               (129.0, -27.0, 138.0, -17.0),    # trrs
               (103.8, 52.0, 108.8, 64.0))      # pwrsw
    if tag == 'Left':
        port_rects = [rect_poly(*r) for r in L_rects]
    else:
        port_rects = [rect_poly(291.5 - x2, y1, 291.5 - x1, y2)
                      for (x1, y1, x2, y2) in L_rects]
    # Cross-module drift guard: the keep-rects above must contain the
    # case's port anchors (case/params.py PORTS is the single source of
    # truth for both files). If a port moves in the case, the plate
    # gate fails here until the keep-rects follow \u2014 the two files
    # cannot drift apart silently.
    for (name, (ax, ay)), rect in zip(case_params.PORTS[tag].items(),
                                      port_rects):
        xs = [p[0] for p in rect]
        ys = [p[1] for p in rect]
        if not (min(xs) <= ax <= max(xs) and min(ys) <= ay <= max(ys)):
            fail(f'case port anchor {name} ({ax:.2f},{ay:.2f}) '
                 f'outside the plate keep-rect {min(xs):.1f}..{max(xs):.1f} '
                 f'x {min(ys):.1f}..{max(ys):.1f}')
    openings += port_rects

    def fillet_arc(corner, u_away, o_out, r, n=6):
        # 90° concave fillet joining the rim (direction u_away from the
        # corner) to the tab side (direction o_out). Sweeps from the rim
        # tangent point to the side tangent point THROUGH the corner side;
        # the long way around would draw a near-full loop in the plate.
        T1 = (corner[0] + u_away[0] * r, corner[1] + u_away[1] * r)
        T2 = (corner[0] + o_out[0] * r, corner[1] + o_out[1] * r)
        O = (T1[0] + o_out[0] * r, T1[1] + o_out[1] * r)
        a0 = math.atan2(T1[1] - O[1], T1[0] - O[0])
        a1 = math.atan2(T2[1] - O[1], T2[0] - O[0])
        amid = math.atan2(corner[1] - O[1], corner[0] - O[0])
        ccw = (a1 - a0) % (2 * math.pi)
        if (amid - a0) % (2 * math.pi) <= ccw:
            angs = [a0 + ccw * k / n for k in range(n + 1)]
        else:
            cw = (a0 - a1) % (2 * math.pi)
            angs = [a0 - cw * k / n for k in range(n + 1)]
        return [(O[0] + r * math.cos(t), O[1] + r * math.sin(t))
                for t in angs]

    def tab_frame(px, py, tx, ty):
        # the REAL tab outline (fillets + sides + chamfered tip) rigidly
        # attached to its rim frame: eligibility is tested against this,
        # not an inflated root box, so narrow-but-sufficient fingers
        # (like the MCU-window east finger) stay eligible
        n = inward((px, py), (tx, ty))
        o = (-n[0], -n[1])
        hw = TAB_W / 2
        A = (px - tx * hw, py - ty * hw)
        B = (px + tx * hw, py + ty * hw)
        F, TL, CH = TAB_FILLET, TAB_L, 1.5
        path = []
        path += fillet_arc(A, (-tx, -ty), o, F)
        S1 = (A[0] + o[0] * (TL - CH), A[1] + o[1] * (TL - CH))
        path.append(S1)
        E1 = (px - tx * (hw - CH) + o[0] * TL,
              py - ty * (hw - CH) + o[1] * TL)
        E2 = (px + tx * (hw - CH) + o[0] * TL,
              py + ty * (hw - CH) + o[1] * TL)
        path.append(E1)
        path.append(E2)
        S2 = (B[0] + o[0] * (TL - CH), B[1] + o[1] * (TL - CH))
        path.append(S2)
        path += fillet_arc(B, (tx, ty), o, F)[::-1]
        return path

    def web_poly(p, q):
        d = min(poly_dist(v, q) for v in p)
        return min(d, min(poly_dist(v, p) for v in q))

    def eligible(s):
        span = TAB_W / 2 + TAB_FILLET + 2.0
        if not straight(s, span):
            return False
        (px, py), (tx, ty) = at(s)
        tp = tab_frame(px, py, tx, ty)
        for o in openings:
            if polys_intersect(tp, o):
                return False
            if web_poly(tp, o) < WEB_MIN:
                return False
        return True

    NS = 720
    elig = [s for k in range(NS) if eligible(P * k / NS)
            for s in [P * k / NS]]
    # Tab roots: Left is the design authority. Right mirrors the LEFT
    # roots and re-projects them onto the right rim; the greedy walk is
    # NOT run independently on the right (its 1mm sample phase can land
    # one grid point over, e.g. x 170.64 -> 170.57, which is enough to
    # make the plate/case rim fail the 0.05mm mirror gate). The right
    # projection must find the mirrored rim point within 0.05mm — that
    # is the plate-side mirror gate.
    centers = []
    if tag == 'Right':
        if _LAST_LEFT_TABS is None:
            fail('Right tab layout needs the Left build first (same '
                 'process, Left before Right)')
        else:
            for lx, ly in _LAST_LEFT_TABS:
                target = (2 * case_params.MIRROR_AX - lx, ly)
                d, s = param_of(target)
                if d > 0.05:
                    fail(f'mirrored left tab ({lx:.3f},{ly:.3f}) -> '
                         f'({target[0]:.3f},{target[1]:.3f}) is '
                         f'{d:.3f}mm off the right rim (floor 0.05)')
                    continue
                if not eligible(s):
                    fail(f'mirrored left tab ({lx:.3f},{ly:.3f}) -> '
                         f'({target[0]:.3f},{target[1]:.3f}) is not '
                         f'eligible on the right rim')
                    continue
                centers.append(s)
            centers.sort()
            if len(centers) != TAB_N:
                fail(f'only {len(centers)} mirrored tab spots, want '
                     f'{TAB_N}')
    else:
        # pinned corners: user-directed support where even spacing will
        # not go on its own (top edge above the outer key column,
        # bottom-inner corner under the MCU). Snapped to the nearest
        # eligible sample; loud failure if it cannot host a tab at all.
        PINNED = [(95.0, 56.0), (120.0, -52.5)]
        for wx, wy in PINNED:
            s0 = min((P * k / NS for k in range(NS)),
                     key=lambda s: math.hypot(at(s)[0][0] - wx,
                                              at(s)[0][1] - wy))
            snap = None
            for off in [d / 2 for k in range(25) for d in (k, -k)]:
                if eligible((s0 + off) % P):
                    snap = (s0 + off) % P
                    break
            if snap is None:
                fail(f'pinned corner ({wx},{wy}) has no eligible tab '
                     f'spot within 12mm')
            else:
                centers.append(snap)
        if centers:
            while len(centers) < TAB_N and len(centers) < len(elig):
                cand, candd = elig[0], -1.0
                for s in elig:
                    d = min(min(abs(s - c), P - abs(s - c)) for c in centers)
                    if d > candd:
                        candd, cand = d, s
                centers.append(cand)
        centers.sort()
        if len(centers) == TAB_N:
            _LAST_LEFT_TABS = [at(c)[0] for c in centers]
    if len(centers) < TAB_N:
        fail(f'only {len(centers)} tab spots eligible, want {TAB_N}')
        centers = []
    # min spacing between tab roots (no shared fillet zones)
    for a, b in zip(centers, centers[1:] + centers[:1] if centers else []):
        if centers and (b - a) % P < TAB_W + 2 * TAB_FILLET + 6.0:
            fail('tab roots overlap/clash')

    # splice tabs into a dense outline (0.5mm; chordal error negligible)
    dense, dcum = [loop[0]], [0.0]
    for p in loop[1:]:
        prev = dense[-1]
        L = math.hypot(p[0] - prev[0], p[1] - prev[1])
        n = max(1, int(L / 0.5))
        for k in range(1, n + 1):
            t = k / n
            dense.append((prev[0] + (p[0] - prev[0]) * t,
                          prev[1] + (p[1] - prev[1]) * t))
            dcum.append(dcum[-1] + L / n)
    Pdense = dcum[-1] + math.hypot(loop[0][0] - dense[-1][0],
                                   loop[0][1] - dense[-1][1])

    def tab_path(c):
        # single source of truth for tab geometry: the splice emits
        # exactly what eligibility approved, so a passing gate means the
        # outline contains the approved shape (and vice versa)
        (px, py), (tx, ty) = at(c)
        return tab_frame(px, py, tx, ty)

    intervals = []
    for c in centers:
        intervals.append((c - (TAB_W / 2 + TAB_FILLET + 1.0),
                          c + (TAB_W / 2 + TAB_FILLET + 1.0)))
    # rebuild outline skipping tabbed spans, inserting tab paths
    marks = []
    for c in centers:
        marks.append((c - (TAB_W / 2 + TAB_FILLET + 1.0), 'start', c))
        marks.append((c + (TAB_W / 2 + TAB_FILLET + 1.0), 'end', c))
    marks.sort()
    # walk dense outline; at each tab interval emit rim point, tab path
    tab_paths = {c: tab_path(c) for c in centers}
    inside = [False] * len(dense)
    for i, s in enumerate(dcum):
        for a, b in intervals:
            ss = s % P
            aa, bb = a % P, b % P
            hit = (aa <= ss <= bb) if aa <= bb else (ss >= aa or ss <= bb)
            if hit:
                inside[i] = True
                break
    inject = {}
    for (a, b), c in zip(intervals, centers):
        # splice position = first dense index at/after the interval start
        # (NOT the nearest: nearest can fall just BEFORE the start, which
        # emits the whole tab path before its rim anchor and spikes
        # out-and-back across the interval width).
        target = a % P
        bi = next(i for i, s in enumerate(dcum) if (s % P) >= target)
        inject.setdefault(bi, []).append(c)
    final = []
    for i, pt in enumerate(dense):
        if i in inject:
            for c in inject[i]:
                final.extend(tab_paths[c])
        if not inside[i]:
            final.append(pt)
    # dedupe consecutive near-coincident points (segment-joint doubles
    # laser as zero-length moves and read as spikes)
    new_loop = [final[0]]
    for pt in final[1:]:
        if math.hypot(pt[0] - new_loop[-1][0], pt[1] - new_loop[-1][1]) >= 0.01:
            new_loop.append(pt)
    # drop an explicit closure duplicate (closed POLYLINE/SVG-polygon
    # auto-close; keeping it lasers a zero-length spike). A genuine small
    # closing segment (<=0.6) stays.
    if math.hypot(new_loop[-1][0] - new_loop[0][0],
                  new_loop[-1][1] - new_loop[0][1]) < 0.05:
        new_loop.pop()
    # self-checks: outline simplicity (no loops/spikes), per-tab area
    n = len(new_loop)
    for i in range(n):
        a, b = new_loop[i], new_loop[(i + 1) % n]
        for j in range(i + 2, n):
            if j == n - 1 and i == 0:
                continue
            c, d = new_loop[j], new_loop[(j + 1) % n]
            rx, ry = b[0] - a[0], b[1] - a[1]
            sx, sy = d[0] - c[0], d[1] - c[1]
            den = rx * sy - ry * sx
            if abs(den) < 1e-12:
                continue
            t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / den
            u = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / den
            if 0 < t < 1 and 0 < u < 1:
                fail(f'outline self-intersects near '
                     f'{r2(a[0])},{r2(a[1])}')
                break
        else:
            continue
        break
    for c in centers:
        tp = tab_paths[c]
        area = abs(sum(p[0] * q[1] - q[0] * p[1]
                       for p, q in zip(tp, tp[1:] + tp[:1])) / 2)
        if not (30.0 <= area <= 90.0):
            fail(f'tab at {r2(c)} area {area:.0f} outside 30-90')
    # closure + area sanity (tabs add ~55mm^2 each)
    if math.hypot(new_loop[0][0] - new_loop[-1][0],
                  new_loop[0][1] - new_loop[-1][1]) > 0.6:
        fail('tabbed outline does not close')
    gain = poly_area(new_loop) - poly_area(loop)
    if not (TAB_N * 25.0 <= gain <= TAB_N * 90.0):
        fail(f'suspicious tab area gain {gain:.0f}')
    # every switch + the encoder must sit near a tab root (suspension
    # still has to reach the keys; bar set from evidence below)
    worst, worst_pt = 0.0, None
    for qx, qy in [(x, y) for _, x, y, _ in sw] + [(ex, ey)]:
        d = 1e9
        for c in centers:
            (px, py), _ = at(c)
            d = min(d, math.hypot(qx - px, qy - py))
        if d > worst:
            worst, worst_pt = d, (qx, qy)
    if worst > MAX_TAB_DIST:
        fail(f'worst key-to-tab {worst:.0f}mm at '
             f'{r2(worst_pt[0])},{r2(worst_pt[1])} > {MAX_TAB_DIST}')
    tabs = []
    poron = []
    poron_edge = 1e9          # tightest pad-corner -> plate-edge margin
    poron_edge_at = None
    for c in centers:
        (px, py), (tx, ty) = at(c)
        n = inward((px, py), (tx, ty))
        ang = math.degrees(math.atan2(-n[1], -n[0]))
        tabs.append({'x': r2(px), 'y': r2(py), 'angle': r2(ang),
                     'width': TAB_W, 'protrusion': TAB_L})
        # poron pad fully ON the tongue: center pushed 2.0 outward from
        # the root, so the 8x4 pad spans rim-line to +4.0 inside the
        # 5-long tongue (same pad top + bottom = a pair)
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        tx2, ty2 = -dy, dx
        cx, cy = px + dx * 2.0, py + dy * 2.0
        hl, hw = PORON_PAD_L / 2, PORON_PAD_W / 2
        pad = [(cx + tx2 * a + dx * b, cy + ty2 * a + dy * b)
               for a, b in ((-hl, -hw), (hl, -hw),
                            (hl, hw), (-hl, hw))]
        for vx, vy in pad:
            if not point_in_poly((vx, vy), new_loop) and \
                    poly_dist((vx, vy), new_loop) > 0.1:
                fail(f'poron pad corner ({r2(vx)},{r2(vy)}) off-plate')
            # kerf margin: the pad corner's distance to the plate edge
            # (3-review audit 2026-10-21: reverting PORON_PAD_L to 8.0
            # passed every gate while silently restoring the 0.35mm
            # kerf-fragile margin — the documented value was policed by
            # nothing, so it is policed here)
            m = poly_dist((vx, vy), new_loop)
            if point_in_poly((vx, vy), new_loop) and m < poron_edge:
                poron_edge = m
                poron_edge_at = (r2(vx), r2(vy))
        poron.append(pad)
    lands = [('tab', 0, None) for _ in tabs]
    # absolute kerf-margin floor on the poron pads (see PORON_EDGE_MIN)
    if poron_edge < PORON_EDGE_MIN:
        fail(f'poron pad corner-edge margin {poron_edge:.3f}mm at '
             f'{poron_edge_at} < {PORON_EDGE_MIN}mm — the 7mm pad keeps '
             f'>=0.6mm to the plate edge (kerf + tolerance)')
    poron_edge_mm = poron_edge

    # --- diode relief gates (support b) --------------------------------
    # (a) the stack must actually clear the measured diode: the relief
    #     floor (GAP + DIODE_RELIEF_D) must stand above the diode top
    #     (DIODE_TOP_Z) with the stated margin.
    clear = GAP + DIODE_RELIEF_D - DIODE_TOP_Z
    if clear < 0.10:
        fail(f'diode relief leaves only {clear:.3f}mm over the diode top '
             f'(floor 0.10) — raise GAP or DIODE_RELIEF_D')
    # (b) the relief must not eat the plate: the material left under a
    #     pocket is PLATE_THICK - DIODE_RELIEF_D.
    if PLATE_THICK - DIODE_RELIEF_D < 0.6:
        fail(f'diode relief leaves {PLATE_THICK - DIODE_RELIEF_D:.2f}mm of '
             f'plate under the pocket (floor 0.6)')
    # (c) every pocket must sit in solid material: inside the outline,
    #     clear of the switch cutouts, and clear of the other pockets.
    for i, pk in enumerate(relief):
        for v in pk:
            if not point_in_poly(v, new_loop):
                fail(f'diode relief pocket {i} corner ({r2(v[0])},'
                     f'{r2(v[1])}) is off the plate')
        for c in cuts:
            if web_poly(pk, c) < 0.3:
                fail(f'diode relief pocket {i} is within 0.3mm of a switch '
                     f'cutout (the clip must bear on solid material)')
        for j, pk2 in enumerate(relief[:i]):
            if web_poly(pk, pk2) < 0.3:
                fail(f'diode relief pockets {i} and {j} are too close')

    # Output-side mirror gate: every right tab root must land on the
    # mirror of a left tab root, not merely be derived from one.
    if tag == 'Right' and _LAST_LEFT_TABS is not None:
        mirrored = [(2 * case_params.MIRROR_AX - x, y)
                    for x, y in _LAST_LEFT_TABS]
        for t in tabs:
            d = min(math.hypot(t['x'] - mx, t['y'] - my)
                    for mx, my in mirrored)
            if d > 0.05:
                fail(f'tab root ({t["x"]:.3f},{t["y"]:.3f}) is {d:.3f}mm '
                     f'from the nearest mirrored left tab (floor 0.05)')

    # M-review: definitive encoder-neighborhood webs (the spec's "~3.55"
    # and a reviewer's "1.75" measured different pairs — print every
    # pair that matters, from the real geometry)
    enc_open = expand_poly(enc_hole, 0.0)
    enc_web = {
        'cutouts': min(web_poly(enc_open, c) for c in cuts),
        'windows': min((web_poly(enc_open, w) for w in win_rects),
                       default=float('inf')),
        'ports': min(web_poly(enc_open, r) for r in port_rects),
    }

    return {'half': tag, 'loop': loop, 'outline': new_loop, 'cuts': cuts,
            'sw': sw, 'enc': enc_hole, 'wins': wins, 'tool': tool,
            'tabs': tabs, 'poron': poron, 'enc_web': enc_web,
            'poron_edge': poron_edge_mm, 'relief': relief}, bad


# ---- DXF R12 writer ----
def dxf_write(path, res):
    L = []
    A = L.append
    A('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n'
      '9\n$INSUNITS\n70\n4\n0\nENDSEC\n')
    A('0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3\n')
    for name, color in (('OUTLINE', 3), ('CUTOUT', 7), ('PORON', 2),
                         ('RELIEF', 1)):
        A(f'0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\nCONTINUOUS\n')
    A('0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n')

    def closed_poly(pts, layer):
        A(f'0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n1\n')
        for x, y in pts:
            A(f'0\nVERTEX\n8\n{layer}\n10\n{r2(x)}\n20\n{r2(y)}\n30\n0.0\n')
        A('0\nSEQEND\n')

    closed_poly(res['outline'] + res['outline'][:1], 'OUTLINE')
    for poly in res['cuts'] + res['wins']:
        closed_poly(poly + poly[:1], 'CUTOUT')
    closed_poly(res['enc'] + res['enc'][:1], 'CUTOUT')
    for pad in res['poron']:
        closed_poly(pad + pad[:1], 'PORON')
    for pocket in res['relief']:
        closed_poly(pocket + pocket[:1], 'RELIEF')
    # H3: the PORON layer is a knife/punch 1:1 template, not laser
    # content — say so on the file itself (it travels to vendors without
    # the repo README). North of the outline: tabs tip out ~2.8 there.
    oy = max(p[1] for p in res['outline'])
    ox = min(p[0] for p in res['outline'])
    A('0\nTEXT\n8\nPORON\n10\n' + str(r2(ox)) + '\n20\n' + str(r2(oy + 6.0))
      + '\n30\n0.0\n40\n3.0\n1\n'
      'DO NOT CUT PORON - KNIFE/PUNCH TEMPLATE ONLY, REFERENCE\n')
    # RELIEF: a PARTIAL-DEPTH pocket in the plate underside (0.35mm),
    # not a through-cut.  Cutting it through would leave the switch
    # with no plate support; skipping it fouls the diodes.
    A('0\nTEXT\n8\nRELIEF\n10\n' + str(r2(ox)) + '\n20\n'
      + str(r2(oy + 3.0)) + '\n30\n0.0\n40\n3.0\n1\n'
      'RELIEF POCKETS - MACHINE 0.40mm DEEP INTO THE UNDERSIDE - '
      'DO NOT CUT THROUGH\n')
    A('0\nENDSEC\n0\nEOF\n')
    open(path, 'w').write(''.join(L))


# ---- SVG preview (y-down) ----
def svg_write(path, res):
    loop, cuts, wins = res['outline'], res['cuts'], res['wins']
    enc_poly = res['enc']
    xs = [p[0] for p in loop] + [v[0] for c in cuts for v in c]
    ys = [p[1] for p in loop] + [v[1] for c in cuts for v in c]
    x0, x1, y0, y1 = min(xs) - 9, max(xs) + 9, min(ys) - 9, max(ys) + 9
    S = 4.0
    W, H = (x1 - x0) * S, (y1 - y0) * S

    def P(p):
        return f'{r2((p[0] - x0) * S)},{r2((y1 - p[1]) * S)}'

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{r2(W)}" '
         f'height="{r2(H)}" viewBox="0 0 {r2(W)} {r2(H)}">',
         f'<rect width="{r2(W)}" height="{r2(H)}" fill="#111"/>']
    o.append(f'<polygon points="{" ".join(P(p) for p in loop)}" '
             f'fill="#1d3a24" stroke="#4caf50" stroke-width="1.5"/>')
    for c in cuts:
        o.append(f'<polygon points="{" ".join(P(p) for p in c)}" '
                 f'fill="#000" stroke="#fff" stroke-width="1"/>')
    for wpoly in wins:
        o.append(f'<polygon points="{" ".join(P(p) for p in wpoly)}" '
                 f'fill="#000" stroke="#ff9800" stroke-width="1.5" '
                 f'stroke-dasharray="5,3"/>')
    o.append(f'<polygon points="{" ".join(P(p) for p in enc_poly)}" '
             f'fill="#000" stroke="#ff9800" stroke-width="1.5"/>')
    for pk in res.get('relief', []):
        o.append(f'<polygon points="{" ".join(P(p) for p in pk)}" '
                 f'fill="none" stroke="#00bcd4" stroke-width="1" '
                 f'stroke-dasharray="3,2"/>')
    for k, (t, pad) in enumerate(zip(res['tabs'], res['poron']), 1):
        o.append(f'<polygon points="{" ".join(P(p) for p in pad)}" '
                 f'fill="rgba(255,235,59,0.30)" stroke="#ff0" '
                 f'stroke-width="1" stroke-dasharray="2,2"/>')
        ang = math.radians(t['angle'])
        lx = t['x'] + math.cos(ang) * (t['protrusion'] + 4.0)
        ly = t['y'] + math.sin(ang) * (t['protrusion'] + 4.0)
        o.append(f'<text x="{r2((lx - x0) * S)}" y="{r2((y1 - ly) * S)}" '
                 f'fill="#f0f" font-size="9" font-weight="bold" '
                 f'text-anchor="middle">T{k}</text>')
    o.append(f'<text x="8" y="14" fill="#f0f" font-size="10">'
             f'T = gasket tab (poron pads top+bottom, yellow)'
             f'</text>')
    o.append(f'<text x="8" y="26" fill="#fff" font-size="10">'
             f'white square = Choc cutout 15x15'
             f'</text>')
    o.append(f'<text x="8" y="38" fill="#ff9800" font-size="10">'
             f'solid orange = encoder window {ENC_W:g}x{ENC_H:g} / dashed orange = '
             f'component window (tall parts)'
             f'</text>')
    for tx, ty in res['tool']:
        o.append(f'<circle cx="{r2((tx - x0) * S)}" cy="{r2((y1 - ty) * S)}" '
                 f'r="{r2(1.6 * S)}" fill="none" stroke="#03a9f4" '
                 f'stroke-width="1"/>')
    for ref, x, y, _ in res['sw']:
        o.append(f'<text x="{r2((x - x0) * S)}" y="{r2((y1 - y) * S)}" '
                 f'fill="#888" font-size="7" text-anchor="middle">{ref}</text>')
    o.append(
        f'<text x="8" y="'
        f'{r2((y1 - (max(p[1] for p in loop) + 6.0)) * S)}" '
        f'fill="#ffeb3b" font-size="12" font-weight="bold">'
        f'DO NOT CUT PORON - KNIFE/PUNCH TEMPLATE ONLY (reference)</text>')
    o.append('</svg>')
    open(path, 'w').write('\n'.join(o))


def main():
    check_only = '--check' in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)
    failed = False
    for tag in ('Left', 'Right'):
        res, bad = build_half(tag)
        if bad:
            print(f'{tag} FAIL:')
            for b in bad:
                print(f'  !! {b}')
            failed = True
            continue
        if not check_only:
            dxf_write(os.path.join(OUT_DIR, f'Hojicha44-{tag}-plate.dxf'),
                      res)
            svg_write(os.path.join(OUT_DIR, f'Hojicha44-{tag}-plate.svg'), res)
            json.dump({
                'half': tag, 'units': 'mm (KiCad board frame)',
                'plate': f'{PLATE_THICK}mm {MATERIAL}', 'gap': GAP,
                'poron': {'spec': PORON_SPEC, 'pad': [PORON_PAD_L,
                          PORON_PAD_W], 'faces': ['top', 'bottom'],
                          'center': 'tab root center + 2.0 outward '
                                    '(fully on tongue)'},
                'tabs': res['tabs'],
                'diode_relief': {
                    'depth': DIODE_RELIEF_D,
                    'pockets': len(res['relief']),
                    'floor_z': round(GAP + DIODE_RELIEF_D, 3),
                    'diode_top_z': DIODE_TOP_Z,
                    'clearance': round(GAP + DIODE_RELIEF_D - DIODE_TOP_Z, 3),
                    'note': 'partial-depth pocket in the plate UNDERSIDE; '
                            'machine 0.40mm, do not cut through',
                },
            }, open(os.path.join(OUT_DIR, f'Hojicha44-{tag}-lands.json'),
                    'w'), indent=1)
        print(f'{tag}: 22 cutouts + enc {ENC_W}x{ENC_H} + {len(res["wins"])} '
              f'windows + {len(res["tabs"])} gasket tabs — CLEAN')
        ew = res['enc_web']
        print(f'{tag}: encoder web — cutouts {ew["cutouts"]:.2f}, '
              f'windows {ew["windows"]:.2f}, ports {ew["ports"]:.2f}')
        print(f'{tag}: poron pad {PORON_PAD_L}x{PORON_PAD_W} — corner-edge '
              f'margin {res["poron_edge"]:.3f}mm (floor {PORON_EDGE_MIN})')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

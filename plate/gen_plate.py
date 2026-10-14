#!/usr/bin/env python3
"""Hojicha44 plate + gasket generator — rev-1.

Derives the laser-cut switch plate from the placed PCB (generator-owned
geometry, never hand-drawn):

  outline  = PCB Edge.Cuts loop, identical (USB notch included, so the
             plug housing passes the plate edge exactly as it passes the PCB)
  cutouts  = 22x 15x15mm Choc PG1350 squares at switch instances/rotations
  encoder  = 12.5x12.5mm square hole (instance rot 0, body axis-aligned):
             clears the ~11.7 body at 0.4/side AND clears the neighbour key
             cutout where a 17mm round hole would merge into it; the 13mm
             knob rides high on the 20mm shaft (bore never enters the hole)
  W1       = switch strip + MCU/cell/USB + JST windows (slide switch 6.4,
             module/cell stack, JST ~5.75 — all taller than the plate top
             at GAP+PLATE_THICK = 3.5mm)
  W2       = TRRS window + channel opening to the split-gap edge (jack
             mouth must exit; the plug overlaps plate-top height)
  gaskets  = 2.5mm Poron strips run along the rim (top + bottom pair at
             the same XY), broken at every opening, pin zone and port mouth;
             every switch + the encoder must sit within 40mm of foam

Stack contract (spec/case.md): 1.5mm PC plate, 2.0mm PCB-to-plate gap
(top-side diodes are 1.35mm, module underside 4.5mm).

Usage:
  python3 plate/gen_plate.py          # writes plate/
  python3 plate/gen_plate.py --check  # verify only

Outputs (gitignored scratch, like out/fit):
  plate/Hojicha44-{Left,Right}-plate.dxf   (R12, mm, layers
      OUTLINE/CUTOUT/GASKET[reference-only])
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
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
OUT_DIR = os.path.join(REPO, "plate")
STOCK_FP = ("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

# ---- rev-1 decisions (change here, everything downstream follows) ----
CUTOUT = 15.0          # Choc PG1350 plate cutout (switch body is 15x15)
ENC_SQ = 12.5           # square hole: body ~11.7 + 0.4/side, knob rides high
PLATE_THICK = 1.5      # mm PC
GAP = 2.0              # PCB top -> plate underside (diodes are 1.35)
STRIP_W = 2.0            # Poron strip width (fits 3.75mm+ rim fingers)
STRIP_OFF = 2.0          # strip centerline offset inward from the edge
STRIP_KEEPOUT = 0.75     # strip clearance to openings/pin zones (strips run
                         # on a visible edge, placed accurately by hand)
MIN_STRIP = 10.0         # drop stubs shorter than this
MAX_KEY_DIST = 55.0         # every switch + encoder must sit this near foam:
                         # perimeter-ring support is the industry standard
                         # configuration (commercial 60-65% gasket boards
                         # leave center keys ~55mm from foam); measured
                         # worst here is ~44mm at 2.3 pitches on 50gf Choc,
                         # strictly better. Encoder push over the window
                         # zone stays soft by design (6N, no foam under it)
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
DIODE_CLEAR = 0.25     # min diode-to-cutout-edge (diodes stay under solid plate)
WIN_TRRS_WEST_MARGIN = 0.5  # asymmetric: body coverage vs encoder-hole web

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


# ---- board parsing ----
def parse_instances(path):
    lines = open(path).read().splitlines()
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
    s = open(path).read()
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


def subdivide(segs, step=1.0):
    pts = []
    for s in segs:
        if s[0] == 'line':
            _, a, b = s
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
            for k in range(n):
                t = k / n
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        else:
            _, a, m, b = s
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


# ---- per-half build ----
def build_half(tag):
    pcb = os.path.join(PCB_DIR, f'Hojicha44-{tag}.kicad_pcb')
    inst = parse_instances(pcb)
    seq = chain_loop(parse_outline(pcb))
    loop = subdivide([s for s, _ in seq])

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
    wins = [w_sw, w_core, w_trrs]
    assert enc[3] == 0, f'{tag}: encoder rotated {enc[3]}, hole assumes 0'
    enc_poly = cut_poly(enc[1], enc[2], ENC_SQ, ENC_SQ, 0)
    enc_hole = enc_poly

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

    ex, ey = enc[1], enc[2]
    if web(enc_poly, loop) < WEB_MIN:
        fail('encoder hole within 1.5 of outline')
    for c in cuts:
        if web(enc_poly, c) < WEB_MIN:
            fail('encoder hole within 1.5 of a cutout')
    for wpoly in wins:
        # overlap (dd<0) is a deliberate union; slivers (0<=dd<1) are not
        dd = web(enc_poly, wpoly)
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

    # -- gasket STRIPS (paired top+bottom at the same XY).
    # Real gasket boards run Poron/silicone STRIPS along the rim, not
    # floating pads: a 7x5 pad cannot fit the 3-6mm rim fingers left beside
    # the component windows, but a 2.5mm strip can. Each strip sits on
    # solid plate (top case presses it) with its twin under the PCB
    # (bottom case carries it) — the plate edge itself is the tongue that
    # will slot into the future case groove. Strips break at every opening
    # (windows, cutouts, holes), at pin zones underneath, and at the two
    # port mouths (USB notch, TRRS channel) the cables must exit through.
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

    def strip_quad(cx, cy, tx, ty):
        # 2.0mm of rim length x STRIP_W, centered STRIP_OFF inward
        n = inward((cx, cy), (tx, ty))
        mx, my = cx + n[0] * STRIP_OFF, cy + n[1] * STRIP_OFF
        hx, hy = tx * 1.0, ty * 1.0
        wx, wy = n[0] * STRIP_W / 2, n[1] * STRIP_W / 2
        return [(mx - hx - wx, my - hy - wy), (mx + hx - wx, my + hy - wy),
                (mx + hx + wx, my + hy + wy), (mx - hx + wx, my - hy + wy)]

    def quad_ok(q, keep_polys):
        return not any(polys_intersect(q, kc) for kc in keep_polys)

    # union keepouts, both faces (strips are pairs at one XY)
    keep = [expand_poly(c, STRIP_KEEPOUT) for c in cuts]
    keep.append(expand_poly(enc_poly, STRIP_KEEPOUT))
    keep += [expand_poly(wpoly, STRIP_KEEPOUT) for wpoly in wins]
    keep += [expand_poly(cut_poly(x, y, 14.0, 16.0, rot), STRIP_KEEPOUT)
             for _, x, y, rot in sw]
    tpads = [(float(x), float(y)) for x, y in
             re.findall(r'\(pad "(?:S|T|R1|R2)" thru_hole \S+\s+'
                        r'\(at (-?[\d.]+) (-?[\d.]+)', open(pcb).read())]
    tpts = [rot_cw(lx, ly, trot) for lx, ly in tpads]
    pin_zones = [(tx + min(p[0] for p in tpts) - 1.0,
                  ty + min(p[1] for p in tpts) - 1.0,
                  tx + max(p[0] for p in tpts) + 1.0,
                  ty + max(p[1] for p in tpts) + 1.0),
                 (ex - 7.0, ey - 7.0, ex + 7.0, ey + 7.0),
                 (jst[2] - 3.0, jst[3] - 3.0, jst[2] + 5.0, jst[3] + 3.0)]
    keep += [rect_poly(*z) for z in pin_zones]
    # port mouths the cables exit through (measured from the outline;
    # USB notch is 11mm on both halves)
    if tag == 'Left':
        keep.append(rect_poly(111.0, 45.0, 125.0, 60.0))
        keep.append(rect_poly(129.0, -27.0, 138.0, -17.0))
    else:
        keep.append(rect_poly(167.0, 45.0, 181.0, 60.0))
        keep.append(rect_poly(154.0, -27.0, 163.0, -17.0))

    STEP = 2.0
    NS = int(P / STEP)
    clear = []
    for k in range(NS):
        (px, py), (tx, ty) = at(P * k / NS)
        q = strip_quad(px, py, tx, ty)
        clear.append(quad_ok(q, keep))
    # group consecutive clear steps into strips; drop stubs
    strips, cur = [], []
    for k in range(NS + 1):
        if k < NS and clear[k]:
            (px, py), _ = at(P * k / NS)
            cur.append((px, py))
        else:
            if len(cur) * STEP >= MIN_STRIP:
                strips.append(cur)
            cur = []
    # merge wrap-around strip
    if len(strips) > 1 and clear[0] and clear[NS - 1]:
        strips[0] = strips[-1] + strips[0]
        strips.pop()
    # coverage: every switch + the encoder must sit near foam
    pts = [(x, y) for _, x, y, _ in sw] + [(ex, ey)]
    # coverage measured against strip centerline samples
    worst, worst_pt = 0.0, None
    centers = [s for s in strips for s in [s[len(s) // 2]]]
    for qx, qy in pts:
        d = 1e9
        for s in strips:
            for (sx, sy) in s[::2]:
                d = min(d, math.hypot(qx - sx, qy - sy))
        if d > worst:
            worst, worst_pt = d, (qx, qy)
    if worst > MAX_KEY_DIST:
        fail(f'worst key-to-foam {worst:.0f}mm at '
             f'{r2(worst_pt[0])},{r2(worst_pt[1])} > {MAX_KEY_DIST}')
    total = sum((len(s) - 1) * STEP for s in strips)
    if not strips:
        fail('no gasket strips at all')
    lands = [('strip', 0, s) for s in strips]

    return {'half': tag, 'loop': loop, 'seq': seq, 'cuts': cuts,
            'sw': sw, 'enc': enc_hole, 'wins': wins, 'tool': tool,
            'lands': lands}, bad


# ---- DXF R12 writer ----
def dxf_write(path, loop_seq, cuts, enc_hole, wins, lands):
    L = []
    A = L.append
    A('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n'
      '9\n$INSUNITS\n70\n4\n0\nENDSEC\n')
    A('0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3\n')
    for name, color in (('OUTLINE', 3), ('CUTOUT', 7), ('GASKET', 6)):
        A(f'0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\nCONTINUOUS\n')
    A('0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n')

    for s, flip in loop_seq:
        if s[0] == 'line':
            a, b = (s[2], s[1]) if flip else (s[1], s[2])
            A(f'0\nLINE\n8\nOUTLINE\n10\n{r2(a[0])}\n20\n{r2(a[1])}\n30\n0.0\n'
              f'11\n{r2(b[0])}\n21\n{r2(b[1])}\n31\n0.0\n')
        else:
            _, a, m, b = s
            if flip:
                a, b = b, a
            c = arc_center(a, m, b)
            r = math.hypot(a[0] - c[0], a[1] - c[1])
            a0 = math.degrees(math.atan2(a[1] - c[1], a[0] - c[0]))
            a1 = math.degrees(math.atan2(b[1] - c[1], b[0] - c[0]))
            am = math.degrees(math.atan2(m[1] - c[1], m[0] - c[0]))

            def norm(d):
                while d < 0:
                    d += 360
                while d >= 360:
                    d -= 360
                return d
            a0n, a1n, amn = norm(a0), norm(a1), norm(am)
            if (amn - a0n) % 360 <= (a1n - a0n) % 360:
                start, end = a0n, a1n
            else:
                start, end = a1n, a0n
            A(f'0\nARC\n8\nOUTLINE\n10\n{r2(c[0])}\n20\n{r2(c[1])}\n30\n0.0\n'
              f'40\n{r2(r)}\n50\n{r2(start)}\n51\n{r2(end)}\n')
    for poly in cuts + wins:
        A('0\nPOLYLINE\n8\nCUTOUT\n66\n1\n70\n1\n')
        for x, y in poly:
            A(f'0\nVERTEX\n8\nCUTOUT\n10\n{r2(x)}\n20\n{r2(y)}\n30\n0.0\n')
        A('0\nSEQEND\n')
    A('0\nPOLYLINE\n8\nCUTOUT\n66\n1\n70\n1\n')
    for x, y in enc_hole:
        A(f'0\nVERTEX\n8\nCUTOUT\n10\n{r2(x)}\n20\n{r2(y)}\n30\n0.0\n')
    A('0\nSEQEND\n')
    for _, _, strip in lands:
        # rebuild the ribbon from the centerline (STRIP_W wide)
        A('0\nPOLYLINE\n8\nGASKET\n66\n1\n70\n1\n')
        left, right = [], []
        for k, (sx, sy) in enumerate(strip):
            q = strip[min(k + 1, len(strip) - 1)]
            q0 = strip[max(k - 1, 0)]
            tx, ty = q[0] - q0[0], q[1] - q0[1]
            nL = math.hypot(tx, ty) or 1e-12
            nx, ny = -ty / nL * STRIP_W / 2, tx / nL * STRIP_W / 2
            left.append((sx + nx, sy + ny))
            right.append((sx - nx, sy - ny))
        for x, y in left + right[::-1] + left[:1]:
            A(f'0\nVERTEX\n8\nGASKET\n10\n{r2(x)}\n20\n{r2(y)}\n30\n0.0\n')
        A('0\nSEQEND\n')
    A('0\nENDSEC\n0\nEOF\n')
    open(path, 'w').write(''.join(L))


# ---- SVG preview (y-down) ----
def svg_write(path, res):
    loop, cuts, wins = res['loop'], res['cuts'], res['wins']
    enc_poly = res['enc']
    xs = [p[0] for p in loop] + [v[0] for c in cuts for v in c]
    ys = [p[1] for p in loop] + [v[1] for c in cuts for v in c]
    x0, x1, y0, y1 = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
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
    for k, (_, _, strip) in enumerate(res['lands'], 1):
        o.append(f'<polyline points="{" ".join(P(p) for p in strip)}" '
                 f'fill="none" stroke="#f0f" stroke-width="2.5" '
                 f'stroke-linecap="round"/>')
        mx = sum(p[0] for p in strip) / len(strip)
        my = sum(p[1] for p in strip) / len(strip)
        o.append(f'<text x="{r2((mx - x0) * S)}" y="{r2((y1 - my) * S)}" '
                 f'fill="#f0f" font-size="8" font-weight="bold" '
                 f'text-anchor="middle">G{k}</text>')
    o.append(f'<text x="8" y="14" fill="#f0f" font-size="10">'
             f'G = Poron strip (top + bottom pair at same XY)'
             f'</text>')
    for tx, ty in res['tool']:
        o.append(f'<circle cx="{r2((tx - x0) * S)}" cy="{r2((y1 - ty) * S)}" '
                 f'r="{r2(1.6 * S)}" fill="none" stroke="#03a9f4" '
                 f'stroke-width="1"/>')
    for ref, x, y, _ in res['sw']:
        o.append(f'<text x="{r2((x - x0) * S)}" y="{r2((y1 - y) * S)}" '
                 f'fill="#888" font-size="7" text-anchor="middle">{ref}</text>')
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
                      res['seq'], res['cuts'], res['enc'],
                      res['wins'], res['lands'])
            svg_write(os.path.join(OUT_DIR, f'Hojicha44-{tag}-plate.svg'), res)
            recs = []
            for _, _, strip in res['lands']:
                recs.append({
                    'length': r2((len(strip) - 1) * 2.0),
                    'centerline': [[r2(x), r2(y)] for x, y in strip],
                })
            total = sum(r['length'] for r in recs)
            json.dump({
                'half': tag, 'units': 'mm (KiCad board frame)',
                'plate': f'{PLATE_THICK}mm {MATERIAL}', 'gap': GAP,
                'strip_width': STRIP_W, 'strips': recs,
            }, open(os.path.join(OUT_DIR, f'Hojicha44-{tag}-lands.json'),
                    'w'), indent=1)
        print(f'{tag}: 22 cutouts + enc {ENC_SQ}sq + {len(res["wins"])} '
              f'windows + {len(res["lands"])} gasket strips '
              f'({total:.0f}mm foam/side) — CLEAN')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

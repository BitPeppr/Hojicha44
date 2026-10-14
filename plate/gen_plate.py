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
TAB_W = 10.0             # tab width along the rim (jacket pocket ~12)
TAB_L = 5.0              # tab protrusion past the outline
TAB_FILLET = 2.0         # root fillets (crack control, esp. carbon/acrylic)
TAB_N = 6                # tab count per half: fewer, softer mounts =
                             # more suspension; even spacing keeps it uniform
TAB_TIP_CH = 1.5         # tip chamfer for jacket entry
MAX_TAB_DIST = 55.0         # every switch + encoder must sit this near a tab
                         # root (measured worst 46-47mm at 2.5 pitches).
                         # Consistency comes from mount UNIFORMITY here, not
                         # proximity: 8 identical silicone jackets at even
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


# ---- per-half build ----
def build_half(tag):
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

    def straight(s, half_span):
        a0 = math.atan2(*tang_at(s - half_span)[::-1])
        a1 = math.atan2(*tang_at(s + half_span)[::-1])
        return abs((a1 - a0 + math.pi) % (2 * math.pi) - math.pi) <             math.radians(2.0)

    openings = [expand_poly(c, 0.0) for c in cuts]
    openings.append(expand_poly(enc_poly, 0.0))
    openings += [expand_poly(wpoly, 0.0) for wpoly in wins]
    # port mouths the cables exit through (measured from the outline)
    if tag == 'Left':
        openings.append(rect_poly(111.0, 45.0, 125.0, 60.0))
        openings.append(rect_poly(129.0, -27.0, 138.0, -17.0))
    else:
        openings.append(rect_poly(167.0, 45.0, 181.0, 60.0))
        openings.append(rect_poly(154.0, -27.0, 163.0, -17.0))

    def root_poly(cx, cy, tx, ty):
        # tab footprint: full width incl. fillets, 6mm buried root,
        # protrusion + tip chamfer zone
        n = inward((cx, cy), (tx, ty))
        hw = TAB_W / 2 + TAB_FILLET + 1.0
        pts = []
        for dx, dy in ((-hw, -6.0), (hw, -6.0),
                       (hw, TAB_L + 1.0), (-hw, TAB_L + 1.0)):
            pts.append((cx + tx * dx - n[0] * dy,
                        cy + ty * dx - n[1] * dy))
        return pts

    def eligible(s):
        span = TAB_W / 2 + TAB_FILLET + 2.0
        if not straight(s, span):
            return False
        (px, py), (tx, ty) = at(s)
        rp = root_poly(px, py, tx, ty)
        return not any(polys_intersect(rp, o) for o in openings)

    NS = 720
    elig = [s for k in range(NS) if eligible(P * k / NS)
            for s in [P * k / NS]]
    centers = []
    if elig:
        centers = [elig[0]]
        while len(centers) < TAB_N and len(centers) < len(elig):
            cand, candd = elig[0], -1.0
            for s in elig:
                d = min(min(abs(s - c), P - abs(s - c)) for c in centers)
                if d > candd:
                    candd, cand = d, s
            centers.append(cand)
    centers.sort()
    if len(centers) < TAB_N:
        fail(f'only {len(centers)} tab spots eligible, want {TAB_N}')
        centers = []
    # min spacing between tab roots (no shared fillet zones)
    for a, b in zip(centers, centers[1:] + centers[:1] if centers else []):
        if centers and (b - a) % P < TAB_W + 2 * TAB_FILLET + 6.0:
            fail('tab roots overlap/clash')

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
        (px, py), (tx, ty) = at(c)
        n = inward((px, py), (tx, ty))
        o = (-n[0], -n[1])
        hw = TAB_W / 2
        A = (px - tx * hw, py - ty * hw)
        B = (px + tx * hw, py + ty * hw)
        F, TL, CH = TAB_FILLET, TAB_L, 1.5
        path = []
        # incoming fillet (rim -> left side)
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
        # outgoing fillet (right side -> rim): traverse T2->T1, i.e. the
        # reverse of the rim->side order used on the incoming side, or the
        # path doubles back on itself into a spike
        path += fillet_arc(B, (tx, ty), o, F)[::-1]
        return path

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
    for c in centers:
        (px, py), (tx, ty) = at(c)
        n = inward((px, py), (tx, ty))
        ang = math.degrees(math.atan2(-n[1], -n[0]))
        tabs.append({'x': r2(px), 'y': r2(py), 'angle': r2(ang),
                     'width': TAB_W, 'protrusion': TAB_L})
    lands = [('tab', 0, None) for _ in tabs]

    return {'half': tag, 'loop': loop, 'outline': new_loop, 'cuts': cuts,
            'sw': sw, 'enc': enc_hole, 'wins': wins, 'tool': tool,
            'tabs': tabs}, bad


# ---- DXF R12 writer ----
def dxf_write(path, res):
    L = []
    A = L.append
    A('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n'
      '9\n$INSUNITS\n70\n4\n0\nENDSEC\n')
    A('0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3\n')
    for name, color in (('OUTLINE', 3), ('CUTOUT', 7), ('TABS', 6)):
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
    for t in res['tabs']:
        # reference envelope for jacket makers: root rect at the tab
        ang = math.radians(t['angle'])
        dx, dy = math.cos(ang), math.sin(ang)
        tx, ty = -dy, dx
        cx, cy, hw = t['x'], t['y'], t['width'] / 2
        ref = [(cx + tx * a + dx * b, cy + ty * a + dy * b)
               for a, b in ((-hw, -4.0), (hw, -4.0),
                            (hw, t['protrusion'] + 1.0),
                            (-hw, t['protrusion'] + 1.0))]
        closed_poly(ref + ref[:1], 'TABS')
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
    for k, t in enumerate(res['tabs'], 1):
        ang = math.radians(t['angle'])
        lx = t['x'] + math.cos(ang) * (t['protrusion'] + 4.0)
        ly = t['y'] + math.sin(ang) * (t['protrusion'] + 4.0)
        o.append(f'<text x="{r2((lx - x0) * S)}" y="{r2((y1 - ly) * S)}" '
                 f'fill="#f0f" font-size="9" font-weight="bold" '
                 f'text-anchor="middle">T{k}</text>')
    o.append(f'<text x="8" y="14" fill="#f0f" font-size="10">'
             f'T = gasket tab (silicone jacket in case)'
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
                      res)
            svg_write(os.path.join(OUT_DIR, f'Hojicha44-{tag}-plate.svg'), res)
            json.dump({
                'half': tag, 'units': 'mm (KiCad board frame)',
                'plate': f'{PLATE_THICK}mm {MATERIAL}', 'gap': GAP,
                'tabs': res['tabs'],
            }, open(os.path.join(OUT_DIR, f'Hojicha44-{tag}-lands.json'),
                    'w'), indent=1)
        print(f'{tag}: 22 cutouts + enc {ENC_SQ}sq + {len(res["wins"])} '
              f'windows + {len(res["tabs"])} gasket tabs — CLEAN')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

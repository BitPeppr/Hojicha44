#!/usr/bin/env python3
"""Committed output-artifact gates (were /tmp/pcbcheck.py + /tmp/fid.py).

Usage: python3 pcb/generators/check_board.py  (exit 1 on findings)

Per half, verified against the BUILT .kicad_pcb — independent of the
builders that produced it (fix.md §5.1 items 3-5):

 1. outline topology: exactly 1 Edge.Cuts loop (gr_line + gr_arc
    endpoints), with 0 dangling endpoints. A separate interior notch loop
    fails the count; an open contour fails the dangling check.
 2. fiducials: every FID_* footprint inside the outline with >=3.0mm edge
    clearance (fix.md P0-2 acceptance).
 3. notch openness: the loop's max-y over the usb x-window (the config USB
    subtract is 11 wide, so ±5.5) sits below the usb anchor — an enclosed
    hole would leave the outer edge above it — and no pad copper comes
    within 0.5mm of that bite floor inside the window (fix.md §2.1).
 4. pad + via containment: every pad centre and every via centre inside
    the outline — footprint-library drift that walks a TRRS THT pin past
    the board edge must fail the committed gate, not just the builders.
 5. antenna keepout: committed pad copper keeps ANT_R_MM clearance
    (edge-measured), via centres meet the r=5.0 build rule, and every
    committed TRACK keeps its edge outside the keepout — a preserved
    board passing GUI DRC (the keepout is not a stock KiCad constraint)
    must still fail here.
 6. TRRS crossover pin-map: identical UART pinctrl on both halves means
    the right half's copper must carry the crossing (D1->RING1, D0->TIP,
    electronics.yaml split_link_nets) — asserted on the committed board's
    own pad nets, and again on the netlist it was built from.
 7. W1 content: each waived ref's committed pads (number, size, drill,
    type, layers, LOCAL position) must equal the vendored stock source.
    The exact-28 waiver gate proves WHICH refs mismatch, never WHAT — a
    pad-level hand edit inside an already-waived ref stays 28 and passes
    silently (audit round 2026-10-20: probes found 0 drift on all 28+28,
    so the gate starts honest).
 8. artifact-vs-model drift: every committed copper pad must equal the
    generator's own model (position, size, drill, net). The model is
    derived from the vendored library + the placements, so this proves
    the committed board is what the generator produces — ANY hand edit
    of a pad (position, size, net) on any footprint is caught here, not
    just the 28 waived refs.
 9. diode cathode tick: every D_* footprint carries exactly one F.SilkS
    tick bar at the local (-2.45) cathode mark and none of the stock
    SOD-123 cathode graphics — the tick is the ONLY polarity mark on 44
    diodes, and CI never runs the builder that creates it.
10. silk-to-edge: no F.SilkS graphics nearer the board edge than the
    floor below (measured floor 0.24 = the TRRS jack outline silk, whose
    aperture IS the edge there; label silks 0.49/0.78).

Also runs inside gen_pcb.main, so the committed pipeline enforces it.
"""
import csv
import math
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame
import gen_pcb as G

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
PROJECT = {"L": "Hojicha44-Left", "R": "Hojicha44-Right"}

NOTCH_HALF_W = 5.5  # config USB subtract size [11, 10.8]
NOTCH_INNER = 4.5  # strictly inside the bite, clear of the border walls
FID_EDGE_MM = 3.0
PAD_NOTCH_MM = 0.5
SILK_EDGE_MM = 0.20  # measured floor 2026-10-20: TRRS jack outline silk
                     # runs 0.24 from the Edge.Cuts (the jack aperture is
                     # the edge there); label silk floors: 0.49 (TRRS
                     # label) / 0.78 (MCU) — 0.20 catches real undercutting
                     # (a moved reference/label, drifted notch silk).
UART_L = ("/TRRS_T", "/TRRS_R1")   # U_L1 pin1 (TX) / pin2 (RX)
UART_R = ("/TRRS_R1", "/TRRS_T")   # U_R1 pin1 / pin2 — the CROSSED half
DRIFT_POS_MM = 0.01   # committed-vs-model position tolerance (KiCad
                       # writes 3 decimals; the model rounds to 4)
DRIFT_SIZE_MM = 0.002  # size / drill tolerance
MIRROR_TOL = 0.05     # H-7 left/right gate: board, plate, tub, cover
TICK_LOCAL_X = -2.45   # the SOD-123 cathode tick bar (gen_pcb embed)
TICK_HALF_LEN = 0.5


def edge_segments(txt):
    """Edge.Cuts segments from the board file (lines + arc endpoint chords)."""
    segs = []
    for m in re.finditer(
            r'\(gr_line \(start ([-\d.]+) ([-\d.]+)\) '
            r'\(end ([-\d.]+) ([-\d.]+)\) \(layer "Edge.Cuts"\)', txt):
        segs.append(((float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))))
    for m in re.finditer(
            r'\(gr_arc \(start ([-\d.]+) ([-\d.]+)\) \(mid [^)]*\) '
            r'\(end ([-\d.]+) ([-\d.]+)\)', txt):
        blk = txt[m.start():m.start() + 400]
        if '(layer "Edge.Cuts"' not in blk:
            continue
        segs.append(((float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))))
    return segs


def order_loop(segs):
    """Order a closed component's segments into a point cycle."""
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append(b)
        adj.setdefault(key(b), []).append(a)
    start = key(segs[0][0])
    pts, prev, cur = [segs[0][0]], start, key(segs[0][1])
    pts.append(segs[0][1])
    while cur != start:
        nxt = [key(q) for q in adj[cur] if key(q) != prev]
        if not nxt:
            raise RuntimeError(f"open contour at {cur}")
        prev, cur = cur, nxt[0]
        pts.append(next(q for q in adj[prev] if key(q) == cur))
    return pts


def closed_segs(points):
    """Point cycle -> segment list (strips an explicit closure vertex)."""
    if (len(points) > 1 and
            math.hypot(points[0][0] - points[-1][0],
                       points[0][1] - points[-1][1]) < 1e-6):
        points = points[:-1]
    return list(zip(points, points[1:] + points[:1]))


def mirror_residual(left, right, axis=G.MIRROR_AXIS):
    """Max one-sided distance from each mirrored-Left vertex to Right
    (and back), i.e. a cheap symmetric Hausdorff bound for point loops.
    The right half is RIGHT = 2*axis - LEFT. Both directions catch a
    missing/extra lobe, not just a shifted matching one."""
    lm = [(2 * axis - x, y) for x, y in left]
    ls, rs = closed_segs(lm), closed_segs(right)
    d_lr = max(min(seg_dist(x, y, a, b) for a, b in rs)
               for x, y in lm)
    d_rl = max(min(seg_dist(x, y, a, b) for a, b in ls)
               for x, y in right)
    return max(d_lr, d_rl)


def mirror_layer_residual(left_loops, right_loops, axis=G.MIRROR_AXIS):
    """Symmetric Hausdorff bound across a whole plate layer (many loops)."""
    lm = [[(2 * axis - x, y) for x, y in loop] for loop in left_loops]
    ls = [s for loop in lm for s in closed_segs(loop)]
    rs = [s for loop in right_loops for s in closed_segs(loop)]
    d_lr = max(min(seg_dist(x, y, a, b) for a, b in rs)
               for loop in lm for x, y in loop)
    d_rl = max(min(seg_dist(x, y, a, b) for a, b in ls)
               for loop in right_loops for x, y in loop)
    return max(d_lr, d_rl)


def mirror_artifacts():
    """Design-frame board and plate loops for the left/right gate."""
    out = {}
    for tag, half in (("L", "Left"), ("R", "Right")):
        txt = frame.read_design(
            os.path.join(PCB_DIR, f"Hojicha44-{half}.kicad_pcb"))
        pts = order_loop(edge_segments(txt))
        if (math.hypot(pts[0][0] - pts[-1][0],
                       pts[0][1] - pts[-1][1]) < 1e-6):
            pts = pts[:-1]
        out[f"board-{tag}"] = pts
        polys = dxf_polylines(
            os.path.join(PLATE_DIR, f"Hojicha44-{half}-plate.dxf"))
        by_layer = {}
        for layer, poly in polys:
            if (math.hypot(poly[0][0] - poly[-1][0],
                           poly[0][1] - poly[-1][1]) < 1e-6):
                poly = poly[:-1]
            by_layer.setdefault(layer, []).append(poly)
        for layer in ("OUTLINE", "CUTOUT", "PORON"):
            loops = by_layer.get(layer, [])
            if not loops:
                raise RuntimeError(f"no plate {layer} for {half}")
            out[f"plate-{layer.lower()}-{tag}"] = loops
    return out


def check_mirror():
    """H-7: board and every plate layer must mirror to 0.05mm."""
    bad = []
    art = mirror_artifacts()
    d = mirror_residual(art["board-L"], art["board-R"])
    print(f"  mirror board: max {d:.4f}mm (floor {MIRROR_TOL:.2f})")
    if d > MIRROR_TOL:
        bad.append(f"board left/right mirror residual {d:.4f}mm > "
                   f"{MIRROR_TOL:.2f}mm")
    for layer in ("outline", "cutout", "poron"):
        d = mirror_layer_residual(art[f"plate-{layer}-L"],
                                  art[f"plate-{layer}-R"])
        print(f"  mirror plate {layer}: max {d:.4f}mm "
              f"(floor {MIRROR_TOL:.2f})")
        if d > MIRROR_TOL:
            bad.append(f"plate {layer} left/right mirror residual "
                       f"{d:.4f}mm > {MIRROR_TOL:.2f}mm")
    return bad


def mirror_selftest():
    """Prove the mirror comparator rejects a 0.5mm half-shift and that
    the actual board/plate pass."""
    bad = []
    art = mirror_artifacts()
    for key in ("board", "plate-outline", "plate-cutout", "plate-poron"):
        left, right = art[f"{key}-L"], art[f"{key}-R"]
        if key == "board":
            left, right = [left], [right]
            measure = mirror_layer_residual
        else:
            measure = mirror_layer_residual
        d = measure(left, right)
        if d > MIRROR_TOL:
            bad.append(f"self-test {key}: actual residual {d:.4f}mm")
        shifted = [[(x + 0.5, y) for x, y in loop] for loop in right]
        ctl = measure(left, shifted)
        if ctl <= MIRROR_TOL:
            bad.append(f"self-test {key}: 0.5mm half-shift did NOT fail "
                       f"(residual {ctl:.4f}mm)")
        near = [[(x + 0.02, y) for x, y in loop] for loop in right]
        if measure(left, near) > MIRROR_TOL:
            bad.append(f"self-test {key}: 0.02mm shift exceeded the "
                       f"0.05mm floor")
    return bad


def components(segs):
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append(key(b))
        adj.setdefault(key(b), []).append(key(a))
    seen, comps = set(), []
    for v in adj:
        if v in seen:
            continue
        stack, comp = [v], []
        seen.add(v)
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comp_segs = [(a, b) for a, b in segs
                     if key(a) in set(comp) and key(b) in set(comp)]
        dangling = [u for u in comp if len(adj[u]) % 2 == 1]
        comps.append((comp_segs, dangling))
    return comps


def fiducials(path):
    """{ref: (x, y)} for FID_* footprints in the board file."""
    import audit_silk as A
    return {ref: (x, y) for ref, x, y, _, _ in A.footprints(path)
            if ref.startswith("FID_")}


def seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg_dist(a1, a2, b1, b2):
    """Exact minimum distance between two 2D segments (0.0 if they cross
    or touch). Vertex sampling is NOT enough here: a silk line running
    parallel to the board edge is closest along its INTERIOR, and a
    silk line that crosses the edge has true distance 0 while its
    endpoints sit far away — both cases would read as clear under a
    vertex-only scan."""
    d1x, d1y = a2[0] - a1[0], a2[1] - a1[1]
    d2x, d2y = b2[0] - b1[0], b2[1] - b1[1]
    den = d1x * d2y - d1y * d2x
    if abs(den) > 1e-12:
        t = ((b1[0] - a1[0]) * d2y - (b1[1] - a1[1]) * d2x) / den
        u = ((b1[0] - a1[0]) * d1y - (b1[1] - a1[1]) * d1x) / den
        if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            return 0.0
    return min(seg_dist(a1[0], a1[1], b1, b2),
               seg_dist(a2[0], a2[1], b1, b2),
               seg_dist(b1[0], b1[1], a1, a2),
               seg_dist(b2[0], b2[1], a1, a2))


def silk_items(proj):
    """F.SilkS graphics as polylines, placement-transformed for
    footprint-local items. Returns [(owner, [(x, y), ...]), ...].
    Unflipped footprints only: a flipped instance renders its silk on
    B.SilkS (the fp block's local layer token changes with it), so any
    F.SilkS fp_* item is an unflipped one and the same at/rot transform
    the builder uses for pads applies. Global arc/rect matches are
    layer-confirmed inside a bounded tail window (like edge_segments)."""
    import audit_silk as A
    txt = proj["txt"]
    items = []
    for m in re.finditer(
            r'\(gr_line \(start ([-\d.]+) ([-\d.]+)\) '
            r'\(end ([-\d.]+) ([-\d.]+)\) \(layer "F\.SilkS"\)', txt):
        items.append(("gr_line", [(float(m.group(1)), float(m.group(2))),
                                  (float(m.group(3)), float(m.group(4)))]))
    for m in re.finditer(
            r'\(gr_arc \(start ([-\d.]+) ([-\d.]+)\) \(mid ([-\d.]+) '
            r'([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)', txt):
        if '(layer "F.SilkS"' not in txt[m.start():m.start() + 400]:
            continue
        items.append(("gr_arc", [(float(m.group(i + 1)), float(m.group(i + 2)))
                                 for i in range(0, 6, 2)]))
    for m in re.finditer(
            r'\(gr_rect \(start ([-\d.]+) ([-\d.]+)\) '
            r'\(end ([-\d.]+) ([-\d.]+)\)', txt):
        if '(layer "F.SilkS"' not in txt[m.start():m.start() + 300]:
            continue
        x1, y1, x2, y2 = (float(m.group(i)) for i in range(1, 5))
        items.append(("gr_rect", [(x1, y1), (x2, y2)]))
    for ref, x, y, rot, blk in A.footprints(proj["path"]):

        def _rel(sub, t):
            mm = re.search(r'\(' + t + r' ([-\d.]+) ([-\d.]+)\)', sub)
            return (float(mm.group(1)), float(mm.group(2))) if mm else None

        for kw, sub in A.split_top(blk):
            if kw not in ("fp_line", "fp_arc", "fp_rect", "fp_circle"):
                continue
            lay = re.search(r'\(layer "([^"]+)"', sub)
            if not lay or lay.group(1) != "F.SilkS":
                continue
            if kw == "fp_circle":
                c, e = _rel(sub, "center"), _rel(sub, "end")
                if not c or not e:
                    continue
                rr = math.hypot(e[0] - c[0], e[1] - c[1])
                loc = [(rr * math.cos(2 * math.pi * k / 12),
                        rr * math.sin(2 * math.pi * k / 12)) for k in range(12)]
            else:
                sp, mid = _rel(sub, "start"), _rel(sub, "mid")
                en = _rel(sub, "end")
                if not sp or not en:
                    continue
                loc = [sp] + ([mid] if mid else []) + [en]
            items.append((f"{ref}.{kw}",
                          [(x + gx, y + gy)
                           for gx, gy in (G.cw_rotate(lx, ly, rot)
                                          for lx, ly in loc)]))
    return items


def _pad_blocks(blk):
    """[(num, type, shape, block)] for every pad in a footprint block."""
    out = []
    for m in re.finditer(r'\(pad "([^"]*)"\s+(\S+)\s+(\S+)', blk):
        d = 0
        k = m.start()
        while True:
            c = blk[k]
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            k += 1
        out.append((m.group(1), m.group(2), m.group(3), blk[m.start():k + 1]))
    return out


def committed_pads(path):
    """Copper pads parsed from the COMMITTED board file.

    Returns [(ref, num, x, y, hw, hh, drill, net, layers, lx, ly)] with
    GLOBAL x/y and the pad's LOCAL (at) kept for the content comparison.
    KiCad stores each pad in the footprint's local frame, so the global
    position is fp_at + cw_rotate(pad_local, fp_rot) — the same
    convention the generator's own model uses (verified pad-for-pad
    against R.Board: the project frame is y-up while KiCad's is y-down,
    and the shared cw_rotate accounts for the rotation sense).
    """
    import audit_silk as A
    out = []
    for ref, fx, fy, frot, blk in A.footprints(path):
        for num, typ, shape, pb in _pad_blocks(blk):
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', pb)
            sz = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', pb)
            if not at or not sz:
                continue
            lx, ly = float(at.group(1)), float(at.group(2))
            gx, gy = G.cw_rotate(lx, ly, frot)
            dr = re.search(r'\(drill ([^\)]*)\)', pb)
            drill = 0.0
            if dr:
                vals = [float(v) for v in dr.group(1).split()
                        if re.fullmatch(r"[-\d.]+", v)]
                drill = max(vals) / 2.0 if vals else 0.0
            ly_ = re.search(r'\(layers ([^\)]*)\)', pb)
            net = re.search(r'\(net \d+ "([^"]*)"\)', pb)
            out.append((ref, num, fx + gx, fy + gy,
                        float(sz.group(1)) / 2, float(sz.group(2)) / 2,
                        drill, net.group(1) if net else None,
                        ly_.group(1) if ly_ else "", lx, ly, typ))
    return out


def committed_tracks(txt):
    """Committed copper tracks: [(x1, y1, x2, y2, width, layer)]."""
    out = []
    for m in re.finditer(
            r'\(segment \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) '
            r'([-\d.]+)\) \(width ([-\d.]+)\) \(layer "([FB])\.Cu"\)', txt):
        out.append((float(m.group(1)), float(m.group(2)),
                    float(m.group(3)), float(m.group(4)),
                    float(m.group(5)), m.group(6)))
    return out


def committed_vias(txt):
    """Committed vias: [(x, y, pad_diameter)]."""
    out = []
    for m in re.finditer(
            r'\(via \(at ([-\d.]+) ([-\d.]+)\) \(size ([-\d.]+)\)', txt):
        out.append((float(m.group(1)), float(m.group(2)),
                    float(m.group(3))))
    return out


def pad_rect(p):
    """The 4 corners of a (possibly rotated) pad, in global coords."""
    x, y, hw, hh, ang = p[2], p[3], p[4], p[5], 0.0
    corners = []
    for lx, ly in ((hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)):
        gx, gy = G.cw_rotate(lx, ly, ang)
        corners.append((x + gx, y + gy))
    return corners


def rect_dist_to_point(corners, px, py):
    """Distance from a point to a convex quad (0 if inside)."""
    if G.inside_outline([corners], px, py):
        return 0.0
    return min(seg_dist(px, py, a, b)
               for a, b in zip(corners, corners[1:] + corners[:1]))


def w1_pad_texts(src):
    """{pad_number: (type, size, drill, layers-normalized, local at)} — the
    placement-independent pad invariants plus the LOCAL position (a moved
    pad inside an already-waived ref must not pass)."""
    out = {}
    for num, typ, shape, pb in _pad_blocks(src):
        sz = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', pb)
        dr = re.search(r'\(drill ([^)]*)\)', pb)
        ly = re.search(r'\(layers ([^)]*)\)', pb)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', pb)
        inv = (
            typ,
            (round(float(sz.group(1)), 4), round(float(sz.group(2)), 4))
            if sz else None,
            tuple(sorted(round(float(v), 4) for v in (dr.group(1).split()
                          if dr else [])
                         if re.fullmatch(r"[-\d.]+", v))),
            tuple(sorted(("*" + l[1:] if l[:2] in ("F.", "B.") else l)
                         for l in (ly.group(1).split() if ly else []))),
            (round(float(at.group(1)), 4), round(float(at.group(2)), 4))
            if at else None,
        )
        out[num] = inv
    return out


def check(tag, pts):
    """Run the board gates on a design-frame view of the committed board.

    The committed .kicad_pcb is stored y-negated so KiCad's y-up Gerber
    export matches the plate/case design frame (frame.py).  Every gate in
    _check_design was written against design-frame coordinates, so convert
    once here and hand the audit helpers a temporary design-frame copy.
    The conversion is pure coordinate reflection: topology, distances and
    local footprint content are preserved.
    """
    path = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")
    txt = frame.to_design(open(path).read())
    fd, design_path = tempfile.mkstemp(
        prefix=f"hojicha-{tag}-design-", suffix=".kicad_pcb")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(txt)
        return _check_design(tag, pts, design_path, txt)
    finally:
        os.unlink(design_path)


def _check_design(tag, pts, path, txt):
    """0 if clean, 1 otherwise. Prints findings (design-frame input)."""
    proj = {"txt": txt, "path": path}
    bad = []

    # 1. outline topology on the artifact
    segs = edge_segments(txt)
    comps = components(segs)
    ndang = sum(len(d) for _, d in comps)
    print(f"  topology {tag}: {len(segs)} edge segs, "
          f"{len(comps)} loop(s), {ndang} dangling ends")
    if len(comps) != 1:
        bad.append(f"want exactly 1 Edge.Cuts loop, got {len(comps)}")
    if ndang:
        bad.append(f"{ndang} dangling outline endpoints")
    try:
        loop = order_loop(comps[0][0]) if comps else []
    except RuntimeError as e:
        # open contour: topology findings above already fail the gate;
        # skip the dependent checks instead of crashing the build.
        bad.append(f"outline not orderable: {e}")
        loop = []

    # 2. fiducials inside + edge clearance
    fids = fiducials(path)
    for ref, (x, y) in sorted(fids.items()):
        inside = G.inside_outline([loop], x, y) if loop else False
        edge = min([seg_dist(x, y, a, b) for a, b in segs] or [1e18])
        print(f"  fiducial {ref}: ({x:.2f},{y:.2f}) "
              f"{'inside' if inside else 'OUTSIDE'}, edge {edge:.2f}")
        if not inside:
            bad.append(f"{ref} outside the outline")
        if edge < FID_EDGE_MM:
            bad.append(f"{ref} {edge:.2f}mm from edge, want >={FID_EDGE_MM}")

    # 3. notch openness: bite floor dips below the usb anchor in-window,
    #    and pad copper keeps 0.5mm off that floor
    ux, uy, _ = pts["usb" if tag == "L" else "mirror_usb"]
    # Bite floor = highest segment midpoint strictly inside the bite. (Max
    # over vertices fails: it catches the outer edge at the window border.)
    # Open bite -> the flat floor (~47.25); flat top with no bite -> ~60;
    # enclosed hole is already excluded by the single-loop count above.
    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in segs]
    win = [y for x, y in mids if abs(x - ux) <= NOTCH_INNER] if comps else []
    floor = max(win) if win else None
    print(f"  notch {tag}: usb ({ux:.2f},{uy:.2f}), "
          f"bite floor {floor if floor is None else f'{floor:.2f}'}")
    if floor is None:
        bad.append("no outline points in the notch window")
    else:
        if not (floor < uy and floor > uy - 10):
            bad.append(f"bite floor {floor:.2f} not an open bite below "
                       f"usb {uy:.2f}")
    import gen_route as R
    nets, pin_net = G.load_nets(tag)
    placements = G.build_placements(tag, pts, pin_net)
    board = R.Board(tag, pts, placements, nets, pin_net)
    # the COMMITTED artifact's pads — the gates below read these, not the
    # generator's model (audit round 2026-10-21: gates that re-derive
    # geometry from the library cannot see a hand edit of the board)
    cpads = committed_pads(path)
    if floor is not None:
        worst = None
        for p in cpads:
            if p[7] is None:
                continue
            xs = [c[0] for c in pad_rect(p)]
            if max(xs) < ux - NOTCH_HALF_W or min(xs) > ux + NOTCH_HALF_W:
                continue
            top = max(c[1] for c in pad_rect(p))
            gap = floor - top
            if worst is None or gap < worst[0]:
                worst = (gap, p[0], p[1])
            if gap < PAD_NOTCH_MM:
                bad.append(f"{p[0]}.{p[1]} pad copper {gap:.2f}mm above "
                           f"bite floor, want >={PAD_NOTCH_MM}")
        if worst is not None:
            print(f"  notch copper {tag}: nearest pad {worst[1]}.{worst[2]} "
                  f"gap {worst[0]:.2f}")

    # 4. pad + via containment (COMMITTED artifact)
    if loop:
        nv = 0
        for p in cpads:
            if not G.inside_outline([loop], p[2], p[3]):
                bad.append(f"pad centre {p[0]}.{p[1] or '?'} "
                           f"({p[2]:.2f},{p[3]:.2f}) outside the outline")
        for vx, vy, _vd in committed_vias(txt):
            nv += 1
            if not G.inside_outline([loop], vx, vy):
                bad.append(f"via ({vx:.2f},{vy:.2f}) outside the outline")
        print(f"  containment {tag}: {len(cpads)} committed pads, "
              f"{nv} vias")

    # 5. antenna keepout at commit level: pad copper edge-measured and
    #    via centres >= ANT_R_MM from the antenna centre, and every
    #    committed TRACK's edge outside the keepout (the router's own
    #    rule is edge-based: KEEP_R + w/2 + MARGIN).
    ax, ay, _ = pts["antenna" if tag == "L" else "mirror_antenna"]
    npad = 0
    for p in cpads:
        if p[7] is None and p[8].strip() == "":
            continue
        d = rect_dist_to_point(pad_rect(p), ax, ay)
        npad += 1
        if d < G.ANT_R_MM:
            bad.append(f"{p[0]}.{p[1]} pad copper {d:.2f}mm from the "
                       f"antenna centre, want >= {G.ANT_R_MM}")
    for vx, vy, vd in committed_vias(txt):
        d = math.hypot(vx - ax, vy - ay) - vd / 2
        if d < G.ANT_R_MM:
            bad.append(f"via ({vx:.2f},{vy:.2f}) {d:.2f}mm from the "
                       f"antenna centre, want >= {G.ANT_R_MM}")
    ntrk = 0
    for x1, y1, x2, y2, w, _lay in committed_tracks(txt):
        ntrk += 1
        d = seg_dist(ax, ay, (x1, y1), (x2, y2)) - w / 2
        if d < G.ANT_R_MM:
            bad.append(f"track ({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f}) "
                       f"{d:.2f}mm from the antenna centre, want >= "
                       f"{G.ANT_R_MM}")
    print(f"  antenna {tag}: keepout centre ({ax:.2f},{ay:.2f}) — "
          f"{npad} pads / {ntrk} tracks / {len(committed_vias(txt))} vias "
          f"must clear r={G.ANT_R_MM}")

    # 6. TRRS crossover pin-map — on the COMMITTED board's own pad nets
    #    (the netlist alone cannot see a hand edit of the board).
    jref = f"J_{tag}1"
    uref = f"U_{tag}1"
    jmap = {}
    umap = {}
    for p in cpads:
        if p[0] == jref:
            jmap[p[1]] = p[7]
        if p[0] == uref:
            umap[p[1]] = p[7]
    if jmap.get("T") != "/TRRS_T" or jmap.get("R1") != "/TRRS_R1" \
            or jmap.get("S") != "GND":
        bad.append(f"{jref} jack pads not on the split-link nets (board): "
                   f"{jmap}")
    want = UART_L if tag == "L" else UART_R
    if (umap.get("1"), umap.get("2")) != want:
        bad.append(f"{uref} pins 1/2 = {(umap.get('1'), umap.get('2'))} "
                   f"want {want} (split-link crossover, committed board)")
    # and again on the netlist the board was built from
    jn = {p: n for (r, p), (c, n) in pin_net.items() if r == jref}
    un = [pin_net.get((uref, "1"), (None, None))[1],
          pin_net.get((uref, "2"), (None, None))[1]]
    if jn.get("T") != "/TRRS_T" or jn.get("R1") != "/TRRS_R1" \
            or jn.get("S") != "GND" or tuple(un) != want:
        bad.append(f"split-link netlist mismatch: jack {jn}, uart {un}, "
                   f"want {want}")
    print(f"  uart {tag}: board U pin1 {umap.get('1')}, pin2 {umap.get('2')}"
          f"; jack T/R1 {jmap.get('T')}/{jmap.get('R1')}")

    # 7. W1 content: waived refs' committed pads must equal vendored stock
    #    (position included — a moved pad inside a waived ref is drift)
    import audit_silk as A
    committed = {r: blk for r, x, y, rot, blk in A.footprints(path)}
    libof = {r: (lib, name)
             for kind, lib, name, r, *rest in placements}
    ndiffs = 0
    for fpname, ref in sorted(G.w1_want(tag)):
        if ref not in committed or ref not in libof:
            bad.append(f"W1 content: {ref} missing from board/placements")
            continue
        lp = w1_pad_texts(G.fp_source(*libof[ref]))
        bp = w1_pad_texts(committed[ref])
        if lp != bp:
            ndiffs += 1
            onlyl = [k for k in lp if k not in bp][:3]
            onlyb = [k for k in bp if k not in lp][:3]
            mag = [k for k in lp if k in bp and lp[k] != bp[k]][:4]
            bad.append(f"W1 content {ref} ({fpname}): pads differ — "
                       f"extra-in-lib {onlyl}, extra-on-board {onlyb}, "
                       f"val-diff {mag}")
    print(f"  w1 content {tag}: {len(G.w1_want(tag))} waived refs, "
          f"{ndiffs} pad-diff refs")

    # 8. artifact-vs-model drift: every committed copper pad must equal
    #    the generator's model (position/size/drill/NET). The model comes
    #    from the vendored library + the placements, so this proves the
    #    committed board IS what the generator produces — a hand edit on
    #    ANY footprint is caught, not only the 28 waived refs. (The net
    #    matters as much as the geometry: a swapped pad net rewires the
    #    matrix while every length check still passes.)
    def net_eq(a, b):
        if a is None or b is None:
            return a is None and b is None
        if a.startswith("unconnected") or b.startswith("unconnected"):
            return a.startswith("unconnected") and b.startswith("unconnected")
        return a == b

    model_pads = [(ref, num, x, y, hw, hh, drill, n)
                  for (x, y, hw, hh, ang, drill, n, ref, layers, num)
                  in board.pads]
    used = [False] * len(model_pads)
    unmatched = []
    for p in cpads:
        # copper pads only: the pad TYPE is the discriminator (KiCad
        # writes "*.Cu" for through-hole pads AND for NPTH holes alike,
        # so the layer list cannot tell them apart)
        if p[11] not in ("thru_hole", "smd"):
            continue
        hit = None
        for i, m in enumerate(model_pads):
            if used[i] or m[0] != p[0] or m[1] != p[1]:
                continue
            if (abs(m[2] - p[2]) <= DRIFT_POS_MM
                    and abs(m[3] - p[3]) <= DRIFT_POS_MM
                    and abs(m[4] - p[4]) <= DRIFT_SIZE_MM
                    and abs(m[5] - p[5]) <= DRIFT_SIZE_MM
                    and abs(m[6] - p[6]) <= DRIFT_SIZE_MM
                    and net_eq(m[7], p[7])):
                hit = i
                break
        if hit is None:
            unmatched.append(p)
        else:
            used[hit] = True
    for p in unmatched[:8]:
        bad.append(f"artifact drift: committed pad {p[0]}.{p[1] or '?'} at "
                   f"({p[2]:.2f},{p[3]:.2f}) size {p[4] * 2:.3f}x{p[5] * 2:.3f} "
                   f"drill {p[6] * 2:.2f} net {p[7]} does not match the "
                   f"generator's model — the board was hand-edited")
    if len(unmatched) > 8:
        bad.append(f"artifact drift: {len(unmatched) - 8} more pads differ")
    missing = [m for i, m in enumerate(model_pads)
               if not used[i] and m[7] is not None]
    for m in missing[:4]:
        bad.append(f"artifact drift: model pad {m[0]}.{m[1] or '?'} "
                   f"({m[2]:.2f},{m[3]:.2f}) net {m[7]} is NOT on the "
                   f"committed board")
    print(f"  artifact drift {tag}: {len(cpads)} committed pads, "
          f"{len(unmatched)} unmatched vs model")

    # 9. diode cathode tick: the ONLY polarity mark on 44 diodes. Each
    #    D_* footprint must carry exactly one F.SilkS tick bar at the
    #    local cathode mark, and no stock cathode graphics (the SOD-123
    #    silk is stripped so the tick can take its place).
    import audit_silk as A2
    nticks = 0
    for ref, x, y, rot, blk in A2.footprints(path):
        if not re.match(r"^D_[LR]\d\d$", ref):
            continue
        lines = []
        for kw, sub in A2.split_top(blk):
            if kw != "fp_line":
                continue
            lay = re.search(r'\(layer "([^"]+)"', sub)
            if not lay or lay.group(1) != "F.SilkS":
                continue
            st = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', sub)
            en = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', sub)
            if st and en:
                lines.append(((float(st.group(1)), float(st.group(2))),
                              (float(en.group(1)), float(en.group(2)))))
        tick = cathode_ticks(lines)
        if len(tick) != 1:
            bad.append(f"{ref}: {len(tick)} cathode ticks (want exactly 1) "
                       f"— the diode's polarity mark is the tick; the stock "
                       f"cathode bar is stripped")
        elif len(lines) != 1:
            bad.append(f"{ref}: {len(lines)} F.SilkS lines (want only the "
                       f"tick) — the stock SOD-123 cathode graphics are "
                       f"stripped")
        else:
            nticks += 1
    print(f"  cathode ticks {tag}: {nticks} diodes with exactly one tick")

    # 10. silk-to-edge clearance: a future silk edit must not silently
    #     undercut the measured 0.49/0.78 walls.
    #     Segment-to-segment (exact, crossing = 0) — not vertex sampling.
    items = silk_items(proj)
    worst, where = 9e9, None
    for owner, ptsi in items:
        ssegs = list(zip(ptsi, ptsi[1:])) or \
            (list(zip(ptsi, ptsi[1:] + ptsi[:1])) if len(ptsi) > 2 else [])
        for s1, s2 in ssegs:
            for a, b in segs:
                d = seg_seg_dist(s1, s2, a, b)
                if d < worst:
                    worst, where = d, (owner, s1)
    if worst is not None and worst < SILK_EDGE_MM:
        bad.append(f"F.SilkS {where[0]} at ({where[1][0]:.2f},"
                   f"{where[1][1]:.2f}) only {worst:.2f}mm from edge, "
                   f"want >= {SILK_EDGE_MM}")
    print(f"  silk-edge {tag}: {len(items)} items, min edge distance "
          f"{worst:.2f} ({where[0] if where else '-'})")

    for b in bad:
        print(f"  !! {b}")
    return 1 if bad else 0


# ---------------------------------------------------------------- frame gate
# Cross-artifact frame proof: the release drill/Gerber must be the same
# physical frame as the plate DXF/case anchors.  This is deliberately
# independent of the board generator's own coordinates: it matches the
# released T12/T10 holes against the plate cutout geometry and the released
# Edge.Cuts profile against the plate outline.  A Y-mirrored release (the
# pre-v0.4.0 bug) fails even when every T12 is a perfect centre hole.
FRAME_TOL = 0.05
PLATE_DIR = os.path.join(REPO, "plate")
SPEC = os.path.join(REPO, "spec", "electronics.yaml")


def release_version():
    s = open(SPEC).read()
    m = re.search(r"^version:\s*(\d+\.\d+\.\d+)", s, re.M)
    assert m, "spec/electronics.yaml has no version MAJOR.MINOR.PATCH"
    return m.group(1)


def release_dir():
    return os.path.join(REPO, "generated", "release",
                        f"v{release_version()}")


def dxf_polylines(path):
    """[(layer, [(x, y), ...])] from the R12 plate DXF (stdlib only)."""
    lines = open(path, encoding="latin-1").read().split("\n")
    out = []
    i = 0
    while i < len(lines) - 1:
        code, val = lines[i].strip(), lines[i + 1].strip()
        if code == "0" and val == "POLYLINE":
            layer, pts = None, []
            j = i + 2
            while j < len(lines) - 1:
                c, v = lines[j].strip(), lines[j + 1].strip()
                if c == "8":
                    layer = v
                elif c == "0" and v == "VERTEX":
                    x = y = None
                    k = j + 2
                    while k < len(lines) - 1 and lines[k].strip() != "0":
                        if lines[k].strip() == "10":
                            x = float(lines[k + 1])
                        if lines[k].strip() == "20":
                            y = float(lines[k + 1])
                        k += 2
                    if x is not None and y is not None:
                        pts.append((x, y))
                elif c == "0" and v == "SEQEND":
                    i = j
                    break
                j += 2
            out.append((layer, pts))
        i += 2
    return out


def parse_drill(path):
    """{tool_diameter: [(x, y), ...]} from a KiCad Excellon file."""
    tools, hits, cur = {}, {}, None
    for line in open(path):
        line = line.strip()
        m = re.match(r"T(\d+)C([\d.]+)$", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"T(\d+)$", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"X([-\d.]+)Y([-\d.]+)", line)
        if m and cur is not None:
            hits.setdefault(tools[cur], []).append(
                (float(m.group(1)), float(m.group(2))))
    return hits


def parse_gerber_segments(path):
    """[(a, b)] line segments from a KiCad Edge.Cuts Gerber (4.6 mm)."""
    s = open(path).read()
    scale = 1e6  # %FSLAX46Y46*%
    assert "%FSLAX46Y46*%" in s, f"{path}: expected 4.6 mm coordinates"
    segs, cur = [], None
    for line in s.splitlines():
        m = re.match(r"X(-?\d+)Y(-?\d+)D0([12])\*$", line)
        if not m:
            continue
        p = (int(m.group(1)) / scale, int(m.group(2)) / scale)
        if m.group(3) == "2":
            cur = p
        elif cur is not None:
            segs.append((cur, p))
            cur = p
    return segs


def poly_area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                   - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly))) / 2.0)


def point_in_poly(p, poly):
    x, y = p
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > y) != (b[1] > y):
            xx = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < xx:
                inside = not inside
    return inside


def cutout_poly(points):
    """Drop the DXF's explicit closure duplicate."""
    if len(points) > 1 and math.hypot(points[0][0] - points[-1][0],
                                      points[0][1] - points[-1][1]) < 1e-9:
        return points[:-1]
    return points


def poly_center(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def poly_side_angle(poly):
    """Angle of the longest edge (radians).  The cutout is a square; the
    edge lattice gives the four candidate switch rotations."""
    edges = list(zip(poly, poly[1:] + poly[:1]))
    a, b = max(edges, key=lambda e: math.hypot(e[1][0] - e[0][0],
                                               e[1][1] - e[0][1]))
    return math.atan2(b[1] - a[1], b[0] - a[0])


def rot_cw(x, y, deg):
    t = math.radians(deg)
    return (x * math.cos(t) + y * math.sin(t),
            -x * math.sin(t) + y * math.cos(t))


def frame_residuals(t12, t10, cutouts):
    """Match released drill holes to plate cutouts in the design frame.

    Returns (findings, max_t12_residual, max_post_residual).  t12/t10 are
    release drill coordinates; cutouts are plate DXF CUTOUT polygons.
    """
    findings = []
    if len(t12) != 22:
        findings.append(f"release has {len(t12)} T12 holes, want 22")
    if len(t10) != 44:
        findings.append(f"release has {len(t10)} T10 holes, want 44")
    candidates = [cutout_poly(p) for layer, p in cutouts
                  if layer == "CUTOUT" and len(p) >= 4]
    candidates = [p for p in candidates
                  if 120.0 <= poly_area(p) <= 400.0 and len(p) <= 8]
    matched = {}
    t12_res = []
    for i, hole in enumerate(t12):
        inside = [p for p in candidates if point_in_poly(hole, p)]
        if not inside:
            near = min(candidates, key=lambda p: math.hypot(
                hole[0] - poly_center(p)[0], hole[1] - poly_center(p)[1]))
            d = math.hypot(hole[0] - poly_center(near)[0],
                           hole[1] - poly_center(near)[1])
            findings.append(
                f"T12 {i} ({hole[0]:.3f},{hole[1]:.3f}) is not inside any "
                f"switch cutout (nearest centre {d:.3f}mm away) — release "
                f"is not in the plate frame")
            t12_res.append(d)
            continue
        cut = min(inside, key=poly_area)  # smallest containing cutout
        c = poly_center(cut)
        d = math.hypot(hole[0] - c[0], hole[1] - c[1])
        t12_res.append(d)
        if d > FRAME_TOL:
            findings.append(f"T12 {i} is {d:.3f}mm from its cutout centre "
                            f"(want <= {FRAME_TOL})")
        key = id(cut)
        if key in matched:
            findings.append(f"T12 {i} and {matched[key]} share one cutout")
        matched[key] = i
    max_t12 = max(t12_res) if t12_res else 0.0

    # The standard Choc post pair is (0,-5.9) and (5,-3.8) in footprint-local
    # coordinates.  A mirror maps it to (0,+5.9)/(5,+3.8), which is NOT a
    # rotation of the original pair — so this test catches handedness
    # independently of the board file.  The plate square gives the 90-degree
    # lattice; try all four rotations and require one to fit both posts.
    max_post = 0.0
    for cut in [p for p in candidates if id(p) in matched]:
        c = poly_center(cut)
        near = sorted(t10, key=lambda p: math.hypot(p[0] - c[0],
                                                    p[1] - c[1]))[:2]
        actual = [(p[0] - c[0], p[1] - c[1]) for p in near]
        best = None
        theta = math.degrees(poly_side_angle(cut))
        for k in range(4):
            rot = -theta + k * 90.0
            want = [rot_cw(px, py, rot) for px, py in ((0.0, -5.9),
                                                       (5.0, -3.8))]
            res = max(min(math.hypot(w[0] - a[0], w[1] - a[1])
                          for a in actual) for w in want)
            if best is None or res < best[0]:
                best = (res, rot)
        max_post = max(max_post, best[0])
        if best[0] > FRAME_TOL:
            findings.append(
                f"switch cutout at ({c[0]:.2f},{c[1]:.2f}): T10 posts are "
                f"{best[0]:.3f}mm from the standard Choc pattern (best "
                f"rotation {best[1]:.1f} deg) — mirrored/reversed posts")
    return findings, max_t12, max_post


def usb_floor(segments, ux, uy):
    """Highest y at x=ux below the USB anchor, over outline segments."""
    vals = []
    for a, b in segments:
        if abs(b[0] - a[0]) < 1e-12:
            continue
        t = (ux - a[0]) / (b[0] - a[0])
        if -1e-9 <= t <= 1 + 1e-9:
            y = a[1] + t * (b[1] - a[1])
            if y < uy - 1.0:
                vals.append(y)
    return max(vals) if vals else None


def board_instances(txt):
    """{ref: (x, y, rot)} from a design-frame board text."""
    lines = txt.splitlines()
    out = {}
    for i, ln in enumerate(lines):
        if not re.match(r'\s*\(footprint "', ln):
            continue
        at = ref = None
        for k in range(i, min(i + 12, len(lines))):
            if at is None:
                m = re.match(r'\s*\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?',
                             lines[k])
                if m:
                    at = (float(m.group(1)), float(m.group(2)),
                          float(m.group(3) or 0))
            m = re.search(r'\(property "Reference" "([^"]+)"', lines[k])
            if m:
                ref = m.group(1)
                break
        if ref and at:
            out[ref] = at
    return out


def parse_pos(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def pos_findings(rows, inst, tol=FRAME_TOL):
    """Release pos.csv must be the design-frame placement list.

    The committed board is stored Y-NEGATED, so its stored placement
    (x, y) and stored rotation are the mirrored ones; the pos writer
    emits the DESIGN frame (x, -y) and the design rotation, which is
    the negative of the stored one (verified on the v0.4.0 cut:
    SW_L20 -> (100, -27.7, -27.5) for stored board (100, -27.7,
    +27.5)).  The RULE asserted below is "pos y == -board y and pos rot
    == -board rot", which is what makes the rule right even though the
    stored frame is the mirror of the design frame.  A component placed
    from a Y-mirrored pos file would sit on the wrong side of the board
    even though the gerbers are correct.
    """
    bad = []
    if len(rows) < 40:
        bad.append(f"pos.csv has only {len(rows)} placements")
    for r in rows:
        ref = r["Ref"].strip('"')
        if ref not in inst:
            bad.append(f"pos.csv ref {ref} not on the board")
            continue
        bx, by, brot = inst[ref]
        x, y, rot = (float(r["PosX"]), float(r["PosY"]), float(r["Rot"]))
        d = math.hypot(x - bx, y - by)
        if d > tol:
            bad.append(f"pos {ref} ({x:.3f},{y:.3f}) != design "
                       f"({bx:.3f},{by:.3f}) — {d:.3f}mm")
        want_rot = (-brot) % 360.0
        drot = abs((rot - want_rot + 180.0) % 360.0 - 180.0)
        if drot > tol:
            bad.append(f"pos {ref} rot {rot:.3f} != design {-brot:.3f} "
                       f"(delta {drot:.3f} deg)")
    return bad


def case_ports():
    import importlib.util as ilu
    spec = ilu.spec_from_file_location(
        "case_params_frame", os.path.join(REPO, "case", "params.py"))
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PORTS


def check_frame(tag, pts):
    """Cross-artifact frame/ports gate for one half.  Returns findings."""
    half = "Left" if tag == "L" else "Right"
    bad = []
    reldir = release_dir()
    drill = os.path.join(reldir, half, f"Hojicha44-{half}.drl")
    gerber = os.path.join(reldir, half,
                          f"Hojicha44-{half}-Edge_Cuts.gm1")
    plate = os.path.join(PLATE_DIR, f"Hojicha44-{half}-plate.dxf")
    for p in (drill, gerber, plate):
        if not os.path.exists(p):
            return [f"missing frame-gate input {os.path.relpath(p, REPO)}"]
    hits = parse_drill(drill)
    t12 = hits.get(3.45, [])
    t10 = hits.get(3.05, [])
    cutouts = dxf_polylines(plate)
    finds, max_t12, max_post = frame_residuals(t12, t10, cutouts)
    bad += finds
    print(f"  frame {tag}: {len(t12)} T12 / {len(t10)} T10 vs "
          f"{len([1 for l, _ in cutouts if l == 'CUTOUT'])} plate cutouts; "
          f"max T12 residual {max_t12:.4f}mm, max post residual "
          f"{max_post:.4f}mm")

    # released Edge.Cuts profile vs plate outline: the USB notch floor is a
    # common feature (tabs are not on the PCB rim), so a y-mirrored export
    # shows up as a ~94mm floor error even if every drill hit is centred.
    gsegs = parse_gerber_segments(gerber)
    ux, uy, _ = pts["usb" if tag == "L" else "mirror_usb"]
    plate_outline = next((p for l, p in cutouts if l == "OUTLINE"), [])
    psegs = list(zip(plate_outline, plate_outline[1:] + plate_outline[:1]))
    gf = usb_floor(gsegs, ux, uy)
    pf = usb_floor(psegs, ux, uy)
    print(f"  frame outline {tag}: USB notch floor release "
          f"{'none' if gf is None else f'{gf:.3f}'} / plate "
          f"{'none' if pf is None else f'{pf:.3f}'}")
    if gf is None or pf is None:
        bad.append("USB notch floor not found on release/plate outline")
    elif abs(gf - pf) > FRAME_TOL:
        bad.append(f"release USB notch floor {gf:.3f} != plate {pf:.3f} "
                   f"— release outline is not in the design frame")

    # port anchors: PORTS is the single source shared by plate + case.  Read
    # the committed board in DESIGN frame (the storage is y-negated) and
    # derive the same anchors the generators use.
    inst = board_instances(frame.read_design(
        os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")))
    pos = os.path.join(reldir, half, "pos.csv")
    if not os.path.exists(pos):
        bad.append("release pos.csv missing")
    else:
        rows = parse_pos(pos)
        bad += pos_findings(rows, inst)
        print(f"  frame pos {tag}: {len(rows)} placements checked")
    ports = case_ports()[half]
    usb_want = (pts["usb" if tag == "L" else "mirror_usb"][0],
                pts["usb" if tag == "L" else "mirror_usb"][1])
    trrs = inst.get(f"J_{tag}1")
    pwr = inst.get(f"SW_{tag}PWR1")
    got = {"usb": usb_want}
    if trrs:
        got["trrs"] = (trrs[0] + (12.1 if tag == "L" else -12.1), trrs[1])
    if pwr:
        got["pwrsw"] = (pwr[0], pwr[1] + 7.0)
    for name in ("usb", "trrs", "pwrsw"):
        if name not in got:
            bad.append(f"port {name}: source footprint missing")
            continue
        d = math.hypot(ports[name][0] - got[name][0],
                       ports[name][1] - got[name][1])
        if d > FRAME_TOL:
            bad.append(f"PORTS[{half}][{name}] {ports[name]} != design "
                       f"anchor {got[name]} ({d:.3f}mm)")
        else:
            print(f"  port {tag}.{name}: ({got[name][0]:.2f},"
                  f"{got[name][1]:.2f}) matches PORTS")
    return bad


def cathode_ticks(lines):
    """The cathode-end tick lines of one diode footprint.

    The tick must sit at the CATHODE end: pad 1 (cathode) is at local
    x=-1.65, so the mark is at local x=-2.45.  The old test compared
    |x| against |TICK_LOCAL_X|, so a tick drawn at +2.45 (the ANODE
    side) passed -- and the tick is the ONLY polarity mark on 44
    hand-soldered diodes.  The sign is required.  (The y ENDPOINTS may
    be in either order: the frame convention mirrors the footprint's
    local y, which reverses them.)
    """
    return [ln for ln in lines
            if abs(ln[0][0] - TICK_LOCAL_X) < 0.01
            and abs(abs(ln[0][1]) - TICK_HALF_LEN) < 0.01
            and abs(abs(ln[1][1]) - TICK_HALF_LEN) < 0.01]


def tick_selftest():
    """Negative control for the cathode-tick matcher.

    The tick is the only polarity mark on 44 hand-soldered diodes, so
    the matcher must reject a tick drawn on the ANODE side (+2.45) and
    must still accept the real one.
    """
    bad = []
    import audit_silk as A3
    for half in ("Left", "Right"):
        path = os.path.join(PCB_DIR, f"Hojicha44-{half}.kicad_pcb")
        got = None
        for ref, x, y, rot, blk in A3.footprints(path):
            if not re.match(r"^D_[LR]\d\d$", ref):
                continue
            lines = []
            for kw, sub in A3.split_top(blk):
                if kw != "fp_line":
                    continue
                lay = re.search(r'\(layer "([^"]+)"', sub)
                if not lay or lay.group(1) != "F.SilkS":
                    continue
                st = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', sub)
                en = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', sub)
                if st and en:
                    lines.append(((float(st.group(1)), float(st.group(2))),
                                  (float(en.group(1)), float(en.group(2)))))
            got = lines
            break
        if not got:
            bad.append(f"self-test {half}: no diode footprint found for "
                       f"the tick control")
            continue
        if len(cathode_ticks(got)) != 1:
            bad.append(f"self-test {half}: the real tick was not matched")
        flipped = [(((2.45 if abs(a[0]) < 2.5 else a[0]), a[1]), b)
                   for a, b in got]
        if cathode_ticks(flipped):
            bad.append(f"self-test {half}: an ANODE-side tick (+2.45) was "
                       f"accepted — the polarity mark is not policed")
    return bad


def frame_selftest():
    """Negative controls for the frame gate (no KiCad, current tree only).

    Proves the gate is not a tautology: the released T12/T10 set must pass
    in the plate frame, fail when Y-negated, and the port check must fail
    on a 0.5mm perturbation.  Returns findings.
    """
    bad = []
    pts = G.load_points()
    for tag in ("L", "R"):
        half = "Left" if tag == "L" else "Right"
        hits = parse_drill(os.path.join(
            release_dir(), half, f"Hojicha44-{half}.drl"))
        cutouts = dxf_polylines(os.path.join(
            PLATE_DIR, f"Hojicha44-{half}-plate.dxf"))
        t12, t10 = hits.get(3.45, []), hits.get(3.05, [])
        good, _, _ = frame_residuals(t12, t10, cutouts)
        if good:
            bad.append(f"self-test {tag}: current release fails frame gate: "
                       + "; ".join(good[:2]))
        mirrored = frame_residuals(
            [(x, -y) for x, y in t12], [(x, -y) for x, y in t10], cutouts)[0]
        if not mirrored:
            bad.append(f"self-test {tag}: Y-negated drill did NOT fail")
        if len(mirrored) < 10:
            bad.append(f"self-test {tag}: Y-negated drill only produced "
                       f"{len(mirrored)} findings; expected the centre test "
                       f"to reject most/all 22 switches")
        # outline negative control: the USB notch floor must pass on the
        # release and fail when the Gerber segments are Y-negated.
        ux, uy, _ = pts["usb" if tag == "L" else "mirror_usb"]
        gerber = os.path.join(release_dir(), half,
                              f"Hojicha44-{half}-Edge_Cuts.gm1")
        gsegs = parse_gerber_segments(gerber)
        plate_outline = next((p for l, p in cutouts if l == "OUTLINE"), [])
        psegs = list(zip(plate_outline,
                         plate_outline[1:] + plate_outline[:1]))
        gf, pf = usb_floor(gsegs, ux, uy), usb_floor(psegs, ux, uy)
        if gf is None or pf is None or abs(gf - pf) > FRAME_TOL:
            bad.append(f"self-test {tag}: released USB notch floor does not "
                       f"match the plate")
        gmir = [((a[0], -a[1]), (b[0], -b[1])) for a, b in gsegs]
        gfm = usb_floor(gmir, ux, uy)
        if gfm is not None and abs(gfm - pf) <= FRAME_TOL:
            bad.append(f"self-test {tag}: Y-negated outline did NOT fail")
        # pos.csv frame + negative controls: both a 0.5mm position nudge
        # and a 1-degree rotation nudge must be rejected.
        inst = board_instances(frame.read_design(
            os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")))
        rows = parse_pos(os.path.join(release_dir(), half, "pos.csv"))
        if pos_findings(rows, inst):
            bad.append(f"self-test {tag}: current pos.csv fails the "
                       f"design-frame check")
        nudge_xy = [dict(r) for r in rows]
        nudge_xy[0]["PosX"] = str(float(nudge_xy[0]["PosX"]) + 0.5)
        if not pos_findings(nudge_xy, inst):
            bad.append(f"self-test {tag}: 0.5mm pos nudge did NOT fail")
        nudge_rot = [dict(r) for r in rows]
        nudge_rot[0]["Rot"] = str(float(nudge_rot[0]["Rot"]) + 1.0)
        if not pos_findings(nudge_rot, inst):
            bad.append(f"self-test {tag}: 1deg pos rotation nudge DID NOT "
                       f"fail")
        # port perturbation: the real anchors pass, a 0.5mm nudge must not.
        ports = case_ports()[half]
        trrs = inst[f"J_{tag}1"]
        pwr = inst[f"SW_{tag}PWR1"]
        anchors = {"usb": (ux, uy),
                   "trrs": (trrs[0] + (12.1 if tag == "L" else -12.1),
                            trrs[1]),
                   "pwrsw": (pwr[0], pwr[1] + 7.0)}
        for name, a in anchors.items():
            if math.hypot(ports[name][0] - a[0],
                          ports[name][1] - a[1]) > FRAME_TOL:
                bad.append(f"self-test {tag}.{name}: real anchor does not "
                           f"match PORTS")
            nudged = (a[0] + 0.5, a[1])
            if math.hypot(ports[name][0] - nudged[0],
                          ports[name][1] - nudged[1]) <= FRAME_TOL:
                bad.append(f"self-test {tag}.{name}: 0.5mm nudge did not "
                           f"fail the port check")
    return bad


def main():
    pts = G.load_points()
    rc = 0
    for tag in ("L", "R"):
        rc |= check(tag, pts)
        for b in check_frame(tag, pts):
            print(f"  !! {b}")
            rc = 1
    for b in check_mirror():
        print(f"  !! {b}")
        rc = 1
    if "--self-test" in sys.argv:
        for b in frame_selftest():
            print(f"  !! {b}")
            rc = 1
        for b in mirror_selftest():
            print(f"  !! {b}")
            rc = 1
        for b in tick_selftest():
            print(f"  !! {b}")
            rc = 1
        print("frame/mirror self-test: CLEAN" if rc == 0 else
              "frame/mirror self-test: FAILING")
    print("check_board: CLEAN" if rc == 0 else "check_board: FAILING")
    sys.exit(rc)


if __name__ == "__main__":
    main()

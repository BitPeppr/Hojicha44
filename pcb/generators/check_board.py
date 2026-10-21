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
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    """0 if clean, 1 otherwise. Prints findings."""
    path = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")
    txt = open(path).read()
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
        tick = [ln for ln in lines
                if abs(abs(ln[0][0]) - abs(TICK_LOCAL_X)) < 0.01
                and abs(abs(ln[0][1]) - TICK_HALF_LEN) < 0.01
                and abs(abs(ln[1][1]) - TICK_HALF_LEN) < 0.01]
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


def main():
    pts = G.load_points()
    rc = 0
    for tag in ("L", "R"):
        rc |= check(tag, pts)
    print("check_board: CLEAN" if rc == 0 else "check_board: FAILING")
    sys.exit(rc)


if __name__ == "__main__":
    main()

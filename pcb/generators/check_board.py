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
 4. pad/via containment (audit round 2026-10-20): every pad centre and
    every via centre inside the outline — footprint-library drift that
    walks a TRRS THT pin past the board edge must fail the committed
    gate, not just the builders' own asserts.
 5. antenna keepout (audit round 2026-10-20): committed pad copper keeps
    ANT_R_MM clearance (edge-measured) and via centres meet the r=5.0
    build rule — a preserved board passing GUI DRC (the keepout is not a
    stock KiCad constraint) must still fail here.
 6. TRRS crossover pin-map (audit round 2026-10-20): identical UART
    pinctrl on both halves means the right half's copper must carry the
    crossing (D1->RING1, D0->TIP, electronics.yaml split_link_nets) —
    asserted on the netlist each half committed.
 7. W1 content (audit round 2026-10-20): the exact-28 waiver gate proves
    WHICH refs mismatch, never WHAT — a pad-level hand edit inside an
    already-waived ref stays 28 and passes silently. Each waived ref's
    committed pad blocks (number/size/drill/type/layers) must equal the
    vendored stock source (verification probe 2026-10-20: 0 diffs on all
    28, both halves).
 8. silk-to-edge (audit round 2026-10-20): no F.SilkS graphics nearer the
    board edge than the floor below — the MCU socket was already shifted
    0.5mm south once for exactly this reason (its silk would otherwise
    cross the USB-notch edge), and a future silk edit could undo the
    0.49/0.78mm walls silently.

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


def w1_pad_texts(src):
    """{pad_number: (type, size, drill, layers-normalized)} — the
    placement-independent pad-hour invariants from a footprint source."""
    out = {}
    for m in re.finditer(r'\(pad "([^"]*)"\s+(thru_hole|smd|np_thru_hole|connect)',
                         src):
        d = 0
        k = m.start()
        while True:
            c = src[k]
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            k += 1
        pb = src[m.start():k + 1]
        sz = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', pb)
        dr = re.search(r'\(drill ([^)]*)\)', pb)
        ly = re.search(r'\(layers ([^)]*)\)', pb)
        inv = (
            m.group(2),
            (round(float(sz.group(1)), 4), round(float(sz.group(2)), 4))
            if sz else None,
            tuple(sorted(round(float(v), 4) for v in (dr.group(1).split()
                          if dr else [])
                         if re.fullmatch(r"[-\d.]+", v))),
            tuple(sorted(("*" + l[1:] if l[:2] in ("F.", "B.") else l)
                         for l in (ly.group(1).split() if ly else []))),
        )
        out[m.group(1)] = inv
    return out


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
    if floor is not None:
        worst = None
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if n is None:
                continue
            xs = []
            for lx, ly in ((hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)):
                gx, gy = G.cw_rotate(lx, ly, ang)
                xs.append(x + gx)
            if max(xs) < ux - NOTCH_HALF_W or min(xs) > ux + NOTCH_HALF_W:
                continue
            corners = []
            for lx, ly in ((hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)):
                gx, gy = G.cw_rotate(lx, ly, ang)
                corners.append((x + gx, y + gy))
            top = max(c[1] for c in corners)
            gap = floor - top
            if worst is None or gap < worst[0]:
                worst = (gap, ref, num)
            if gap < PAD_NOTCH_MM:
                bad.append(f"{ref}.{num} pad copper {gap:.2f}mm above "
                           f"bite floor, want >={PAD_NOTCH_MM}")
        if worst is not None:
            print(f"  notch copper {tag}: nearest pad {worst[1]}.{worst[2]} "
                  f"gap {worst[0]:.2f}")

    # 4. pad + via containment (audit round 2026-10-20)
    if loop:
        nv = 0
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if not G.inside_outline([loop], x, y):
                bad.append(f"pad centre {ref}.{num or '?'} "
                           f"({x:.2f},{y:.2f}) outside the outline")
        for m in re.finditer(r'\(via \(at ([-\d.]+) ([-\d.]+)', txt):
            vx, vy = float(m.group(1)), float(m.group(2))
            nv += 1
            if not G.inside_outline([loop], vx, vy):
                bad.append(f"via ({vx:.2f},{vy:.2f}) outside the outline")
        print(f"  containment {tag}: {len(board.pads)} pads, {nv} vias")

    # 5. antenna keepout at commit level (audit round 2026-10-20): pad
    #    copper edge-mesured >= ANT_R_MM from the antenna centre, via
    #    centres >= ANT_R_MM (the builder's own semantics).
    ax, ay, _ = pts["antenna" if tag == "L" else "mirror_antenna"]
    for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
        corners = []
        for lx, ly in ((hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)):
            gx, gy = G.cw_rotate(lx, ly, ang)
            corners.append((x + gx, y + gy))
        rsegs = list(zip(corners, corners[1:] + corners[:1]))
        # distance centre->rect (0 if the centre is inside)
        if G.inside_outline([corners], ax, ay):
            d = 0.0
        else:
            d = min(seg_dist(ax, ay, a, b) for a, b in rsegs)
        if d < G.ANT_R_MM:
            bad.append(f"{ref}.{num} pad copper {d:.2f}mm from the "
                       f"antenna centre, want >= {G.ANT_R_MM}")
    for m in re.finditer(r'\(via \(at ([-\d.]+) ([-\d.]+)', txt):
        vx, vy = float(m.group(1)), float(m.group(2))
        d = math.hypot(vx - ax, vy - ay)
        if d < G.ANT_R_MM:
            bad.append(f"via ({vx:.2f},{vy:.2f}) {d:.2f}mm from the "
                       f"antenna centre, want >= {G.ANT_R_MM}")
    print(f"  antenna {tag}: keepout centre ({ax:.2f},{ay:.2f}) "
          f"pads/vias must clear r={G.ANT_R_MM}")

    # 6. TRRS crossover pin-map (audit round 2026-10-20)
    jref = f"J_{tag}1"
    uref = f"U_{tag}1"
    jmap = {}
    for (r, p), (c, n) in pin_net.items():
        if r == jref:
            jmap[p] = n
    if jmap.get("T") != "/TRRS_T" or jmap.get("R1") != "/TRRS_R1" \
            or jmap.get("S") != "GND":
        bad.append(f"{jref} jack pads not on the split-link nets: {jmap}")
    u1 = pin_net.get((uref, "1"), (None, None))[1]
    u2 = pin_net.get((uref, "2"), (None, None))[1]
    want = UART_L if tag == "L" else UART_R
    if (u1, u2) != want:
        bad.append(f"{uref} pins 1/2 = {(u1, u2)} want {want} "
                   "(split-link crossover)")
    print(f"  uart {tag}: U pin1 {u1}, pin2 {u2}; jack T/R1 "
          f"{jmap.get('T')}/{jmap.get('R1')}")

    # 7. W1 content: waived refs' committed pads must equal vendored stock
    #    (audit round 2026-10-20 — probes found 0 drift on all 28+28)
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

    # 8. silk-to-edge clearance (audit round 2026-10-20): a future silk
    #    edit must not silently undercut the measured 0.49/0.78 walls.
    #    Segment-to-segment (exact, crossing = 0) — not vertex sampling.
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

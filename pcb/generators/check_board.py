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


def check(tag, pts):
    """0 if clean, 1 otherwise. Prints findings."""
    path = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")
    txt = open(path).read()
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
        edge = min([G.seg_dist(x, y, a, b) for a, b in segs] or [1e18])
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
    if floor is not None:
        import gen_route as R
        nets, pin_net = G.load_nets(tag)
        placements = G.build_placements(tag, pts, pin_net)
        board = R.Board(tag, pts, placements, nets, pin_net)
        worst = None
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if n is None:
                continue
            corners = []
            for lx, ly in ((hw, hh), (hw, -hh), (-hw, hh), (-hw, -hh)):
                gx, gy = G.cw_rotate(lx, ly, ang)
                corners.append((x + gx, y + gy))
            xs = [c[0] for c in corners]
            if max(xs) < ux - NOTCH_HALF_W or min(xs) > ux + NOTCH_HALF_W:
                continue
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

#!/usr/bin/env python3
"""Hojicha44 deterministic router — tracks/vias for both halves.

Strategy (2-layer, no pours, dual-layer A* throughout, vias wherever
routable — POWER width 0.5 for battery nets, 0.25 signal, exact per-class
clearance + quantization margin):
  * Anode links first (22/half, short local SW.2 -> via -> D.2).
  * COL rails: matrix SW.1 pads chained in y order; thumb + MCU pins tap
    into the finished rail (interleaving the MCU pin forced 100mm+ jumps).
  * ROW rails: same in x order over D.1 pads.
  * Stubs (ENC x3, TRRS x2, VBAT x2), then GND nearest-neighbour chain.
Rails claim corridors before stubs; single pass, no rip-up (it oscillated).
Emit dedupes vias/segments and trims buried trailing micro-steps.

Deterministic: same inputs -> same copper. Rerun-safe via gen_pcb's
extract/dedupe (fresh routes normalized and compared; GUI copper survives).

Usage: python3 pcb/generators/gen_route.py  (dry plan, prints counts only)
"""
import heapq
import math
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pcb as G

GRID = 0.25
MARGIN = 0.15  # quantization slop: segments between free cell centres still
# graze pad corners (r5 at 0.10 left 0.025mm grazes: ROW2/COL4 on F vs diode
# pad2). Carve uses the same margin so THT pin escape stays open.
ROUTER_VERSION = 13  # bump when routing behavior changes: stale generator
# copper from older revisions is dropped (it would dangle/short); GUI-added
# copper is preserved only within the same revision.
W = {"s": 0.25, "p": 0.5}
CLR = {"s": 0.2, "p": 0.25}
VIA = {"s": (0.6, 0.3), "p": (1.0, 0.5)}
EDGE_CLR = 0.15
HOLE_CLR = 0.25
KEEP_R = 5.0
LAYERS = ("F.Cu", "B.Cu")


def pclass(net):
    return "p" if ("/VBAT_SW" in net or net.startswith("Net-(J_")) else "s"


def U():
    return str(uuid.uuid4())


def r2(v):
    return round(v, 3)


# ---------------------------------------------------------------- model

class Board:
    """Pads, holes, outline and nets for one half, in global mm."""

    def __init__(self, tag, pts, placements, nets, pin_net):
        self.tag = tag
        self.nets = {c: n for c, n in nets}
        # pads: [(x, y, hw, hh, ang_cw, drill_r, net, ref)]
        self.pads = []
        # holes (NPTH/mechanical + THT drills share drill blocking)
        self.holes = []  # (x, y, r)
        for kind, lib, name, ref, value, x, y, rot, *_ in placements:
            if kind == "TOOL":
                self.holes.append((x, y, 1.6))  # 3.2mm NPTH mounting hole
                continue
            if kind == "FID":
                continue
            src = G.fp_source(lib, name)
            pn = dict()
            for (r, p), (c, n) in pin_net.items():
                if r == ref:
                    pn[p] = (c, n)
            for m in re.finditer(r'\(pad "([^"]*)" (\S+) (\S+)', src):
                num = m.group(1)
                # pad block extent
                d = 0
                k = m.start()
                s = src
                while True:
                    if s[k] == "(":
                        d += 1
                    elif s[k] == ")":
                        d -= 1
                        if d == 0:
                            break
                    k += 1
                blk = s[m.start():k + 1]
                at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk)
                sz = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", blk)
                if not at or not sz:
                    continue
                px, py = float(at.group(1)), float(at.group(2))
                gx, gy = G.cw_rotate(px, py, rot)
                net = pn.get(num)
                if num and net is None and num != "MP":
                    raise RuntimeError(f"{ref}.{num}: schematic net missing")
                # MP mounting holes are intentionally netless (mechanical).
                w, h = float(sz.group(1)), float(sz.group(2))
                dr = re.search(r"\(drill ([^\)]+)\)", blk)
                drill = 0.0
                if dr:
                    vals = [float(v) for v in dr.group(1).split()
                            if re.fullmatch(r"[-\d.]+", v)]
                    drill = max(vals) / 2.0 if vals else 0.0
                ly = re.search(r"\(layers ([^\)]+)\)", blk)
                layers = ly.group(1) if ly else ""
                self.pads.append((x + gx, y + gy, w / 2, h / 2, rot,
                                  drill, net[1] if net else None, ref,
                                  layers, num))
                if drill > 0:
                    self.holes.append((x + gx, y + gy, drill))
        # fiducials: copper obstacles without nets
        for kind, lib, name, ref, value, x, y, rot, *_ in placements:
            if kind != "FID":
                continue
            self.pads.append((x, y, 0.5, 0.5, 0, 0.0, None, ref,
                              '"F.Cu" "F.Mask"', ""))
        # antenna keepout centre
        ax, ay, _ = pts["antenna" if tag == "L" else "mirror_antenna"]
        self.keep = (ax, ay)
        # outline loops for inside tests
        self.loops = G.outline_loops(tag)
        xs = [p[0] for l in self.loops for p in l]
        ys = [p[1] for l in self.loops for p in l]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        # USB-notch bite floor for the power-class keepout below: highest
        # outline midpoint strictly inside the 11mm bite (border walls at
        # +-5.5 excluded via +-4.5, same math as check_board).
        ux, _, _ = pts["usb" if tag == "L" else "mirror_usb"]
        mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                for loop in self.loops
                for a, b in zip(loop, loop[1:] + loop[:1])]
        win = [y for x, y in mids if abs(x - ux) <= 4.5]
        assert win, f"{tag}: no outline inside the notch window"
        self.notch = (ux, max(win))

    def inside(self, x, y):
        return G.inside_outline(self.loops, x, y)

    def pad_at(self, ref, num):
        for (x, y, hw, hh, ang, drill, n, r, layers, nm) in self.pads:
            if r == ref and nm == str(num):
                return (x, y, hw, hh, ang, n, layers)
        raise RuntimeError(f"pad {ref}.{num} missing")


# ---------------------------------------------------------------- grids

class Grid:
    def __init__(self, board, layer, cls):
        w = W[cls]
        x0, y0, x1, y1 = board.bbox
        self.gx0 = math.floor(x0 / GRID) * GRID
        self.gy0 = math.floor(y0 / GRID) * GRID
        self.nx = int(math.ceil((x1 - self.gx0) / GRID)) + 1
        self.ny = int(math.ceil((y1 - self.gy0) / GRID)) + 1
        n = self.nx * self.ny
        self.blocked = bytearray(n)
        self.w = w
        # outside outline
        for j in range(self.ny):
            y = self.gy0 + j * GRID
            for i in range(self.nx):
                x = self.gx0 + i * GRID
                if not board.inside(x, y):
                    self.blocked[j * self.nx + i] = 1
        # edge band (rule 0.075 + margin; TRRS mouth pads live ~0.5 off-edge)
        band = 0.075 + w / 2 + MARGIN
        for loop in board.loops:
            for a, b in zip(loop, loop[1:] + loop[:1]):
                self._band(a, b, band)
        # keepout (spec: no copper within 5.0 — exact + margin)
        kx, ky = board.keep
        kr = KEEP_R + w / 2 + MARGIN
        self._disc(kx, ky, kr)
        # USB-notch power keepout: the 0.5mm battery rail may not hug the
        # notch floor where the USB plug bumps it — copper edge must stay
        # >=0.5mm off the bite (the DRC edge rule is only 0.2). Block the
        # floor band [floor-0.5, floor+2.0] on power grids; with 0.25mm
        # cells the last free centre is floor-0.75, i.e. copper edge exactly
        # floor-0.5. The band stops at floor+2 so the rail can still swing
        # north around the bite (a full-height wall forced it south through
        # the MCU pin field and grazed a GND exit on L). Own pads carve
        # later per net, so the RAW endpoint stays reachable.
        if cls == "p":
            ux, floor = board.notch
            self._rect(ux - 7, floor - 0.5, ux + 7, floor + 2.0)
        # pads: exact per-class clearance (signal 0.2 / power 0.25)
        cl = CLR[cls]
        for (x, y, hw, hh, ang, drill, net, ref, layers, num) in board.pads:
            if layer not in layers and "*.Cu" not in layers:
                continue
            self._rot_rect(x, y, hw + cl + w / 2 + MARGIN,
                           hh + cl + w / 2 + MARGIN, ang)
        # holes (NPTH + all drills)
        for (x, y, r) in board.holes:
            self._disc(x, y, r + HOLE_CLR + w / 2 + MARGIN)

    def _on_layer(self, board, x, y, layer):
        return True  # pads pre-filtered by caller into per-layer lists

    def _idx(self, x, y):
        return (int(round((y - self.gy0) / GRID)) * self.nx
                + int(round((x - self.gx0) / GRID)))

    def _band(self, a, b, d):
        x0 = min(a[0], b[0]) - d
        x1 = max(a[0], b[0]) + d
        y0 = min(a[1], b[1]) - d
        y1 = max(a[1], b[1]) + d
        i0 = max(0, int((x0 - self.gx0) / GRID))
        i1 = min(self.nx - 1, int((x1 - self.gx0) / GRID))
        j0 = max(0, int((y0 - self.gy0) / GRID))
        j1 = min(self.ny - 1, int((y1 - self.gy0) / GRID))
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                x = self.gx0 + i * GRID
                y = self.gy0 + j * GRID
                if G.seg_dist(x, y, a, b) < d:
                    self.blocked[j * self.nx + i] = 1

    def _disc(self, cx, cy, r):
        i0 = max(0, int((cx - r - self.gx0) / GRID))
        i1 = min(self.nx - 1, int((cx + r - self.gx0) / GRID))
        j0 = max(0, int((cy - r - self.gy0) / GRID))
        j1 = min(self.ny - 1, int((cy + r - self.gy0) / GRID))
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                if math.hypot(self.gx0 + i * GRID - cx,
                               self.gy0 + j * GRID - cy) < r:
                    self.blocked[j * self.nx + i] = 1

    def _rect(self, x0, y0, x1, y1):
        # Block cell centres inside [x0, x1] x [y0, y1] (inclusive bounds —
        # the notch-floor math depends on the exact y0 cell flipping).
        i0 = max(0, int(math.ceil((x0 - self.gx0) / GRID)))
        i1 = min(self.nx - 1, int(math.floor((x1 - self.gx0) / GRID)))
        j0 = max(0, int(math.ceil((y0 - self.gy0) / GRID)))
        j1 = min(self.ny - 1, int(math.floor((y1 - self.gy0) / GRID)))
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                self.blocked[j * self.nx + i] = 1

    def _rot_rect(self, cx, cy, hw, hh, ang):
        # ang is CW-positive like KiCad; test corners via inverse transform
        a = math.radians(ang)
        ext = math.hypot(hw, hh)
        i0 = max(0, int((cx - ext - self.gx0) / GRID))
        i1 = min(self.nx - 1, int((cx + ext - self.gx0) / GRID))
        j0 = max(0, int((cy - ext - self.gy0) / GRID))
        j1 = min(self.ny - 1, int((cy + ext - self.gy0) / GRID))
        ca, sa = math.cos(a), math.sin(a)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                dx = self.gx0 + i * GRID - cx
                dy = self.gy0 + j * GRID - cy
                # inverse (CW) rotation = CCW by a
                lx = dx * ca - dy * sa
                ly = dx * sa + dy * ca
                if abs(lx) < hw and abs(ly) < hh:
                    self.blocked[j * self.nx + i] = 1

    def copy(self):
        g = Grid.__new__(Grid)
        g.__dict__.update(self.__dict__)
        g.blocked = bytearray(self.blocked)
        return g

    def free_rect(self, x, y, hw, hh, ang):
        a = math.radians(ang)
        ext = math.hypot(hw, hh)
        i0 = max(0, int((x - ext - self.gx0) / GRID))
        i1 = min(self.nx - 1, int((x + ext - self.gx0) / GRID))
        j0 = max(0, int((y - ext - self.gy0) / GRID))
        j1 = min(self.ny - 1, int((y + ext - self.gy0) / GRID))
        ca, sa = math.cos(a), math.sin(a)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                dx = self.gx0 + i * GRID - x
                dy = self.gy0 + j * GRID - y
                if abs(dx * ca - dy * sa) < hw and abs(dx * sa + dy * ca) < hh:
                    self.blocked[j * self.nx + i] = 0

    def cell(self, x, y):
        i = int(round((x - self.gx0) / GRID))
        j = int(round((y - self.gy0) / GRID))
        if 0 <= i < self.nx and 0 <= j < self.ny:
            return (i, j)
        return None

# ---------------------------------------------------------------- A*

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.41421356), (1, -1, 1.41421356),
        (-1, 1, 1.41421356), (-1, -1, 1.41421356)]
BEND = 0.35
POP_CAP = 300000


def astar2(gF, gB, s_xy, s_layers, t_xy, t_layers, ownF, ownB,
           otherF, otherB, keep, via_r, via_cost=4.0, holes=()):
    """Dual-layer A*. Layers: 0=F.Cu, 1=B.Cu. Via transitions cost extra.

    ownF/ownB: [(x,y,hw,hh,ang)] carved free. otherF/otherB: other-net pads
    re-blocked AFTER the carve — carving full own clearance otherwise frees
    the overlap sliver with a neighbour's clearance zone and A* happily
    routes through it (r12: GND exit through COL2's zone, 0.065 graze).
    Start/goal cells are still forced free, so pins stay escapable; only
    the shared slivers become walls, steering exits to truly free sides.
    keep=(kx,ky): no via within 5mm+via_r of it. holes=[(x,y,r)]: no via
    within r+via_drill/2+0.25. Returns runs+vias.
    """
    import heapq
    import math as _m
    F, B = gF.copy(), gB.copy()
    for (x, y, hw, hh, ang) in ownF:
        F.free_rect(x, y, hw, hh, ang)
    for (x, y, hw, hh, ang) in ownB:
        B.free_rect(x, y, hw, hh, ang)
    for (x, y, hw, hh, ang) in otherF:
        F._rot_rect(x, y, hw, hh, ang)
    for (x, y, hw, hh, ang) in otherB:
        B._rot_rect(x, y, hw, hh, ang)
    G = (F, B)
    s = (F.cell(*s_xy), B.cell(*s_xy))
    t = (F.cell(*t_xy), B.cell(*t_xy))
    if None in s or None in t:
        raise RuntimeError(f"route endpoint off-grid: {s_xy} -> {t_xy}")
    starts = [L for L in (0, 1) if (L == 0 and "F" in s_layers)
              or (L == 1 and "B" in s_layers)]
    goals = [L for L in (0, 1) if (L == 0 and "F" in t_layers)
             or (L == 1 and "B" in t_layers)]
    for L, c in ((0, s), (1, s), (0, t), (1, t)):
        g = G[L]
        g.blocked[c[L][1] * g.nx + c[L][0]] = 0

    def h(i, j):
        dx = min(abs(i - t[0][0]), abs(i - t[1][0]))
        dy = min(abs(j - t[0][1]), abs(j - t[1][1]))
        return max(dx, dy) + 0.41421356 * min(dx, dy)

    def via_ok(i, j):
        # centre must be free on both layers (covers pads/tracks/holes via
        # the blocked grids); annular ring checked at 4 neighbours so a via
        # never grazes adjacent copper. Keepout + drill rules are exact.
        for L in (0, 1):
            g = G[L]
            if g.blocked[j * g.nx + i]:
                return False
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if not (0 <= ni < g.nx and 0 <= nj < g.ny):
                    return False
                if g.blocked[nj * g.nx + ni]:
                    return False
        x = F.gx0 + i * GRID
        y = F.gy0 + j * GRID
        if _m.hypot(x - keep[0], y - keep[1]) < KEEP_R + via_r - 1e-9:
            return False
        for hx, hy, hr in holes:
            if _m.hypot(x - hx, y - hy) < hr + via_r + 0.25 - 1e-9:
                return False
        return True

    openq = []
    best, prev = {}, {}
    for L in starts:
        i, j = s[L]
        openq.append((h(i, j), 0.0, i, j, L, -1))
        best[(i, j, L)] = 0.0
    pops = 0
    found = None
    tcell = t[0]  # F/B grids share geometry
    while openq:
        f, cost, i, j, L, d = heapq.heappop(openq)
        if (i, j) == tcell and L in goals:
            found = (i, j, L)
            break
        if best.get((i, j, L), 1e18) < cost - 1e-9:
            continue
        pops += 1
        if pops > POP_CAP:
            raise RuntimeError(f"A* cap ({POP_CAP}) {s_xy} -> {t_xy}")
        g = G[L]
        for nd, (di, dj, step) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < g.nx and 0 <= nj < g.ny):
                continue
            if g.blocked[nj * g.nx + ni]:
                continue
            if di and dj and (g.blocked[j * g.nx + ni]
                              or g.blocked[nj * g.nx + i]):
                continue  # no corner-cutting: grazes cost clearance
            nc = cost + step + (BEND if d != -1 and nd != d else 0.0)
            if nc < best.get((ni, nj, L), 1e18) - 1e-9:
                best[(ni, nj, L)] = nc
                prev[(ni, nj, L)] = (i, j, L)
                heapq.heappush(openq, (nc + h(ni, nj), nc, ni, nj, L, nd))
        # via to other layer
        oL = 1 - L
        if via_ok(i, j):
            nc = cost + via_cost
            if nc < best.get((i, j, oL), 1e18) - 1e-9:
                best[(i, j, oL)] = nc
                prev[(i, j, oL)] = (i, j, L)
                heapq.heappush(openq, (nc + h(i, j), nc, i, j, oL, -2))
    if found is None:
        raise RuntimeError(f"A* no path {s_xy} -> {t_xy}")
    # reconstruct (x, y, layer) path
    path = []
    cur = found
    while True:
        i, j, L = cur
        path.append((G[L].gx0 + i * GRID, G[L].gy0 + j * GRID, L))
        p = prev.get(cur)
        if p is None:
            break
        cur = p
    path.reverse()
    path[0] = (s_xy[0], s_xy[1], path[0][2])
    path[-1] = (t_xy[0], t_xy[1], path[-1][2])
    # split into per-layer runs; vias at transitions
    runs, cvia = [], []
    curL, cur = path[0][2], [(path[0][0], path[0][1])]
    for x, y, L in path[1:]:
        if L != curL:
            runs.append((curL, cur))
            cvia.append((x, y))
            curL, cur = L, [(x, y)]
        else:
            cur.append((x, y))
    runs.append((curL, cur))

    def direction(a, b):
        dx = round((b[0] - a[0]) / GRID)
        dy = round((b[1] - a[1]) / GRID)
        return (dx // max(1, abs(dx)) if dx else 0,
                dy // max(1, abs(dy)) if dy else 0)

    out = []
    for L, pts in runs:
        comp = [pts[0]]
        for p in pts[1:]:
            if len(comp) == 1:
                comp.append(p)
                continue
            if direction(comp[-2], comp[-1]) == direction(comp[-1], p):
                comp[-1] = p
            else:
                comp.append(p)
        if len(comp) > 1:
            out.append((L, comp))
    return out, cvia


# ---------------------------------------------------------------- plan

def net_pads(board, net):
    """{ref: [(x,y,hw,hh,ang,layers)]} pads on net (numbered only)."""
    out = {}
    for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
        if n == net:
            out.setdefault(ref, []).append((x, y, hw, hh, ang, layers))
    return out


def on_layer(layers, layer):
    return layer in layers or "*.Cu" in layers


def normalize(blk):
    """Canonical form for route dedupe: no uuids, net by name, rounded."""
    blk = blk.strip()  # extracted blocks lack emit's leading tab
    blk = re.sub(r'\(uuid "[^"]*"\)', "", blk)
    blk = re.sub(r" -0(\.0+)?(?=[\s)])", " 0", blk)
    def rnd(m):
        return f"{round(float(m.group(0)), 3)}"
    blk = re.sub(r"(?<![\w.])-?\d+\.\d+", rnd, blk)
    return blk


def plan(tag, pts, placements, nets, pin_net):
    """Route one half. Returns (board, tracks, vias).

    tracks: [(net, layer, width, [(x,y),...])]; vias: [(net, x, y)].
    """
    board = Board(tag, pts, placements, nets, pin_net)
    board.nets_inv = {n: c for c, n in nets}
    tracks, vias = [], []
    grids = {}

    def grid(layer, cls):
        key = (layer, cls)
        if key not in grids:
            grids[key] = Grid(board, layer, cls)
        return grids[key]

    routed = {"F.Cu": [], "B.Cu": []}  # (polyline, width, cls) per layer

    def block_routed(layer, cls, net):
        """Fresh copy of base grid with already-routed other-net copper."""
        g = grid(layer, cls).copy()
        for (qn, pl, w0, c0) in routed[layer]:
            if qn == net:
                continue  # own copper is connectable, not obstacle
            clr = 0.25 if (c0 == "p" or cls == "p") else 0.20
            for a, b in zip(pl, pl[1:]):
                length = math.hypot(b[0] - a[0], b[1] - a[1])
                steps = max(1, int(length / (GRID / 2)))
                for k in range(steps + 1):
                    x = a[0] + (b[0] - a[0]) * k / steps
                    y = a[1] + (b[1] - a[1]) * k / steps
                    g._disc(x, y, w0 / 2 + clr + W[cls] / 2 + MARGIN)
        for (vn, vx, vy, size, drill) in vias:
            if vn == net:
                continue
            clr = 0.25 if cls == "p" else 0.20
            g._disc(vx, vy, size / 2 + clr + W[cls] / 2 + MARGIN)
        return g

    def own_pads(net, layer, inflate=False):
        out = []
        cls = pclass(net)
        # carve the full blocked rect (copper + clearance + half-width +
        # margin): anything less seals THT pins inside their own clearance
        # ring (proven: 1-cell sliver at x=109.2 sealed U_L1.11). Overlap
        # with neighbour zones is harmless — A* still avoids them by cost.
        grow = (CLR[cls] + W[cls] / 2 + MARGIN) if inflate else 0.0
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if n == net and (layer in layers or "*.Cu" in layers):
                out.append((x, y, hw + grow, hh + grow, ang))
        return out

    def other_pads(net, layer):
        # Other-net pads, same inflation the base grid used: re-blocked
        # after the own carve so shared clearance slivers become walls.
        out = []
        cls = pclass(net)
        grow = CLR[cls] + W[cls] / 2 + MARGIN
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if n is not None and n != net and (layer in layers or "*.Cu" in layers):
                out.append((x, y, hw + grow, hh + grow, ang))
        return out

    def elayers(ref, num):
        for (x, y, hw, hh, ang, drill, n, r, layers, nm) in board.pads:
            if r == ref and nm == str(num):
                if "B.Cu" in layers and "F.Cu" in layers:
                    return {"F", "B"}
                if "B.Cu" in layers:
                    return {"B"}
                return {"F"}
        raise RuntimeError(f"pad {ref}.{num} missing")

    def at(ref, num):
        p = board.pad_at(ref, num)
        return (p[0], p[1])

    def connect(net, pa, pb):
        """Dual-layer connection, single pass (no rip-up).

        Rails claim corridors first (plan order below); stubs route around
        them. Failures raise with endpoints so the plan order can be fixed
        instead of oscillating (rip-up ping-pong proved non-convergent).
        """
        cls = pclass(net)
        w = W[cls]
        gF = block_routed("F.Cu", cls, net)
        gB = block_routed("B.Cu", cls, net)
        try:
            runs, found_vias = astar2(
                gF, gB, (pa[0], pa[1]), pa[2], (pb[0], pb[1]), pb[2],
                own_pads(net, "F.Cu", inflate=True),
                own_pads(net, "B.Cu", inflate=True),
                other_pads(net, "F.Cu"),
                other_pads(net, "B.Cu"),
                board.keep, VIA[cls][0] / 2, 4.0,
                holes=[(x, y, r) for (x, y, r) in board.holes])
        except RuntimeError as e:
            raise RuntimeError(f"{net} ({pa[0]:.2f},{pa[1]:.2f}) -> "
                               f"({pb[0]:.2f},{pb[1]:.2f}): {e}")
        for L, path in runs:
            layer = "F.Cu" if L == 0 else "B.Cu"
            routed[layer].append((net, path, w, cls))
            tracks.append((net, layer, w, path))
        for vx, vy in found_vias:
            size, drill = VIA[cls]
            vias.append((net, vx, vy, size, drill))
        return runs

    def chain(net, points):
        """points: [(x, y, layerset)]; consecutive pairs + taps."""
        for a, b in zip(points, points[1:]):
            connect(net, a, b)

    def tap(net, t):
        """Stub from point t=(x, y, layerset) to nearest same-net copper."""
        best, bestd = None, 1e18
        for layer in ("F.Cu", "B.Cu"):
            for (qn, pl, w0, c0) in routed[layer]:
                if qn != net:
                    continue
                for a, b in zip(pl, pl[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    L2 = dx * dx + dy * dy
                    tt = 0.0 if L2 == 0 else max(0.0, min(1.0, ((t[0] - a[0]) * dx + (t[1] - a[1]) * dy) / L2))
                    q = (a[0] + tt * dx, a[1] + tt * dy)
                    d = math.hypot(t[0] - q[0], t[1] - q[1])
                    if d < bestd:
                        best, bestd = ((q, {"F"} if layer == "F.Cu" else {"B"}), d)
        assert best is not None, f"{net}: no copper to tap"
        (qx, qy), qlay = best
        if bestd > 0.6:
            connect(net, t, (qx, qy, qlay))
        # else: pad already touches copper — a micro-stub would dangle

    def P(ref, num):
        """Endpoint (x, y, layerset): SMD fixed layer, THT both layers."""
        for (x, y, hw, hh, ang, drill, n, r, layers, nm) in board.pads:
            if r == ref and nm == str(num):
                if "*.Cu" in layers:
                    return (x, y, {"F", "B"})
                if "B.Cu" in layers:
                    return (x, y, {"B"})
                return (x, y, {"F"})
        raise RuntimeError(f"pad {ref}.{num} missing")


    # ---- anode links: SW.2 -> D.2 (different layers: vias auto-placed)
    for idx in range(22):
        sref, dref = f"SW_{tag}{idx:02d}", f"D_{tag}{idx:02d}"
        spa, apa = P(sref, "2"), P(dref, "2")
        snet = [p[6] for p in board.pads if p[7] == sref and p[9] == "2"][0]
        anet = [p[6] for p in board.pads if p[7] == dref and p[9] == "2"][0]
        assert snet == anet, f"{sref}.2 vs {dref}.2 net mismatch"
        connect(snet, spa, apa)



    # ---- COL rails: matrix SW.1 pads in y order; thumb + MCU pads tap in.
    # (rails first: long runs get clean corridors; taps route around them)
    for c in range(6):
        net = f"/COL{c}_{tag}"
        main, taps = [], []
        for idx in range(22):
            r, cc = divmod(idx, 6)
            if r == 3 and cc >= 4:
                continue
            if cc != c:
                continue
            p = P(f"SW_{tag}{idx:02d}", "1")
            (main if r < 3 else taps).append(p)
        mcu = [p for p in board.pads if p[7].startswith("U_") and p[6] == net]
        assert len(mcu) == 1, f"{net}: want 1 MCU pin, got {len(mcu)}"
        # matrix rail first (short adjacent hops); MCU + thumbs tap into it.
        # Interleaving the MCU pin in y-order forced 100mm+ jumps across the
        # dense east zone (A* cap) — taps stay short instead.
        main.sort(key=lambda q: q[1])
        chain(net, main)
        taps.append((mcu[0][0], mcu[0][1], {"F", "B"}))
        for t in taps:
            tap(net, t)


    # ---- ROW rails: finger-row D.1 pads in x order; thumb row chained.
    for r in range(4):
        net = f"/ROW{r}_{tag}"
        main, taps = [], []
        for idx in range(22):
            rr, cc = divmod(idx, 6)
            if rr == 3 and cc >= 4:
                continue
            if rr != r:
                continue
            p = P(f"D_{tag}{idx:02d}", "1")
            (main if r < 3 else taps).append(p)
        if r < 3:
            main.sort(key=lambda q: q[0])
        else:
            main = sorted(taps, key=lambda q: q[0])
            taps = []
        mcu = [p for p in board.pads if p[7].startswith("U_") and p[6] == net]
        assert len(mcu) == 1, f"{net}: want 1 MCU pin, got {len(mcu)}"
        # same as COLs: rail the matrix, tap the MCU pin in afterwards.
        main.sort(key=lambda q: q[0])
        chain(net, main)
        taps.append((mcu[0][0], mcu[0][1], {"F", "B"}))
        for t in taps:
            tap(net, t)

    # ---- short stubs: encoder, TRRS, power (nearest far endpoint each)
    jobs = []
    for eref, epin in [(f"ENC_{tag}1", "A"), (f"ENC_{tag}1", "B"),
                       (f"ENC_{tag}1", "S1")]:
        ep = P(eref, epin)
        net = [p[6] for p in board.pads if p[7] == eref and p[9] == epin][0]
        up = [p for p in board.pads if p[7].startswith("U_") and p[6] == net]
        assert len(up) == 1, f"{net}: want 1 MCU pin, got {len(up)}"
        jobs.append((net, ep, (up[0][0], up[0][1], {"F", "B"})))
    for ref, pin in [(f"J_{tag}1", "T"), (f"J_{tag}1", "R1"),
                     (f"J_{tag}2", "1"), (f"SW_{tag}PWR1", "2")]:
        ep = P(ref, pin)
        net = [p[6] for p in board.pads if p[7] == ref and p[9] == str(pin)][0]
        if net.startswith("unconnected"):
            continue
        others = [(x, y, {"F", "B"}) for (x, y, hw, hh, ang, drill, n, r, layers, num)
                  in board.pads
                  if n == net and not (r == ref and num == str(pin))]
        assert others, f"{net}: no far endpoint"
        fx, fy, fl = min(others, key=lambda q: math.hypot(q[0] - ep[0], q[1] - ep[1]))
        jobs.append((net, ep, (fx, fy, fl)))
    for net, a, b in jobs:
        connect(net, a, b)



    # ---- GND chain (nearest-neighbour over GND pads, any layer each)
    gnds = []
    for (x, y, hw, hh, ang, drill, n, r, layers, num) in board.pads:
        if n == "GND":
            if "*.Cu" in layers:
                ls = {"F", "B"}
            else:
                ls = {"B"} if "B.Cu" in layers else {"F"}
            gnds.append((x, y, ls))
    assert gnds, "no GND pads"
    order = [gnds[0]]
    rest = gnds[1:]
    while rest:
        nxt = min(rest, key=lambda q: math.hypot(q[0] - order[-1][0], q[1] - order[-1][1]))
        order.append(nxt)
        rest.remove(nxt)
    chain("GND", order)


    return board, tracks, vias


# ---------------------------------------------------------------- emit

def emit(board, tracks, vias):
    segs, vv = [], []
    seen_via = set()
    deduped = []
    for (net, x, y, size, drill) in vias:
        key = (net, round(x, 3), round(y, 3))
        if key in seen_via:
            continue  # double layer-transition at one cell (same net, one drill)
        seen_via.add(key)
        deduped.append((net, x, y, size, drill))
    vias = deduped
    tracks = _drop_nubs(board, tracks, vias)
    for net, layer, w, path in tracks:
        code = board.nets_inv[net]
        for a, b in zip(path, path[1:]):
            if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                continue
            segs.append(
                f'\t(segment (start {r2(a[0])} {r2(a[1])}) (end {r2(b[0])} {r2(b[1])})'
                f' (width {w}) (layer "{layer}") (net {code}) (uuid "{U()}"))')
    for net, x, y, size, drill in vias:
        code = board.nets_inv[net]
        vv.append(
            f'\t(via (at {r2(x)} {r2(y)}) (size {size}) (drill {drill})'
            f' (layers "F.Cu" "B.Cu") (net {code}) (uuid "{U()}"))')
    return segs, vv


def _drop_nubs(board, tracks, vias, maxlen=0.5):
    """Drop dangling compression nubs (r6: 0.13mm ROW1_L stub).

    A* appends the exact off-grid endpoint after the last cell centre; when a
    tap goal is a projection already ON copper, direction compression leaves
    the last cell centre as a lone micro-step (in-memory run [MCU..A,B] with
    B the goal, A 0.13 away, both buried in rail copper). KiCad still flags
    the tip as dangling, so buried trailing micro-steps are trimmed and fully
    buried short runs are dropped. Pad endpoints are NEVER trimmed: a
    pad-to-rail micro-bridge is load-bearing (both-ends-touch + mid-air
    midpoint is kept). Iterate to fixpoint.
    """
    import math as _m

    def segdist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return _m.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def in_pad(net, px, py):
        for (x, y, hw, hh, ang, drill, n, ref, layers, num) in board.pads:
            if n != net:
                continue
            a = _m.radians(ang)
            dx, dy = px - x, py - y
            if abs(dx * _m.cos(a) - dy * _m.sin(a)) < hw + 0.03 \
                    and abs(dx * _m.sin(a) + dy * _m.cos(a)) < hh + 0.03:
                return True
        return False

    def on_track(net, lay, px, py, skip=None):
        for (qn, qlay, qw, path) in tracks:
            if qn != net or qlay != lay:
                continue
            for a, b in zip(path, path[1:]):
                if skip is not None and ((a, b) == skip or (a, b) == (skip[1], skip[0])):
                    continue
                if segdist(px, py, a[0], a[1], b[0], b[1]) < 0.05:
                    return True
        return False

    def on_via(net, px, py):
        for (vn, vx, vy, size, drill) in vias:
            if vn == net and _m.hypot(px - vx, py - vy) < 0.05:
                return True
        return False

    def buried_in_cu(net, lay, px, py, skip=None):
        # point lies inside same-net copper body (track half-width / via
        # barrel): it is a valid connected endpoint even when off-centreline
        # (r8: trim prev-point A sat 0.059 off the rail centreline, inside
        # the 0.125 body — a legal junction, but snap 0.05 rejected it).
        for (qn, qlay, qw, path) in tracks:
            if qn != net or qlay != lay:
                continue
            for a, b in zip(path, path[1:]):
                if skip is not None and ((a, b) == skip or (a, b) == (skip[1], skip[0])):
                    continue
                if segdist(px, py, a[0], a[1], b[0], b[1]) < qw / 2 + 0.01:
                    return True
        for (vn, vx, vy, size, drill) in vias:
            if vn == net and _m.hypot(px - vx, py - vy) < size / 2 + 0.01:
                return True
        return False

    tracks = [(n, l, w, [tuple(p) for p in path]) for (n, l, w, path) in tracks]
    for _ in range(10):
        # identical-run dedupe (orientation-independent for 2-point runs)
        seen, uniq = set(), []
        for (n, l, w, path) in tracks:
            e = tuple((round(x, 3), round(y, 3)) for p in path for x, y in [p])
            key = (n, l, w, min(e[0], e[-1]), max(e[0], e[-1])) if len(path) == 2 \
                else (n, l, w) + e
            if key in seen:
                continue
            seen.add(key)
            uniq.append((n, l, w, path))
        tracks = uniq
        changed = False
        kept = []
        for (n, l, w, path) in tracks:
            # (a) trim buried trailing micro-step: last point on copper AND
            # prev point on copper AND last point not in a pad (pad ends are
            # valuable even when adjacent copper buries them).
            while len(path) > 2:
                (ax, ay), (bx, by) = path[-2], path[-1]
                if _m.hypot(bx - ax, by - ay) >= 0.3:
                    break
                # drop the tip whenever the new endpoint stays buried in
                # copper and the tip is not a pad: covers both the buried
                # overshoot (goal already on copper) and the mid-air tip
                # (prev stays connected, tip touched nothing).
                sk = ((ax, ay), (bx, by))
                if buried_in_cu(n, l, ax, ay, skip=sk) and not in_pad(n, bx, by):
                    path = path[:-1]
                    changed = True
                else:
                    break
            if len(path) < 2:
                changed = True
                continue
            if len(path) == 2:
                (ax, ay), (bx, by) = path
                if _m.hypot(bx - ax, by - ay) < maxlen \
                        and not in_pad(n, ax, ay) and not in_pad(n, bx, by):
                    sk = ((ax, ay), (bx, by))
                    ta = on_track(n, l, ax, ay, skip=sk) or on_via(n, ax, ay)
                    tb = on_track(n, l, bx, by, skip=sk) or on_via(n, bx, by)
                    mx, my = (ax + bx) / 2, (ay + by) / 2
                    buried = on_track(n, l, mx, my, skip=sk)
                    if (ta != tb) or (ta and tb and buried):
                        changed = True  # nub or fully-buried redundant stub
                        continue
            kept.append((n, l, w, path))
        tracks = kept
        if not changed:
            break
    return tracks

def main():
    import gen_pcb as P
    pts = P.load_points()
    total_v = []
    for tag in ("L", "R"):
        nets, pin_net = P.load_nets(tag)
        placements = P.build_placements(tag, pts, pin_net)
        board, tracks, vias = plan(tag, pts, placements, nets, pin_net)
        nseg = sum(len(p) - 1 for _, _, _, p in tracks)
        print(f"route {tag}: {len(tracks)} nets, {nseg} segments, {len(vias)} vias")
        total_v += vias
    print("OK (dry plan)")


if __name__ == "__main__":
    main()

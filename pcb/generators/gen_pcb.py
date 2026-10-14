#!/usr/bin/env python3
"""Hojicha44 PCB generator — source of truth for placed+routed .kicad_pcb.

Reads ergogen points + board outline DXF + the per-half schematic netlists,
embeds footprints at their placed positions, and writes both board files.

  python3 pcb/generators/gen_pcb.py        # place + route + DRC

Routed: tracks/vias come from the deterministic router
(pcb/generators/gen_route.py); GUI-added copper is preserved by normalized
dedupe. DRC must show zero unconnected (clean modulo waivers W1/W2); what
this pass must satisfy is outline validity,
footprint embedding, net assignment parity with the schematic, and courtyard
sanity.

Right-half rule: the mirror_* points are already mirrored coordinates. Use
them directly with the SAME layers and the given rotations — no footprint
mirroring/flipping. (Flipping would swap F.Cu/B.Cu and put sockets on top.)
"""
import math
import os
import re
import shutil
import subprocess
import sys
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
POINTS = os.path.join(REPO, "layout", "generated", "v2", "points", "points.yaml")
BOARD_DXF = os.path.join(REPO, "layout", "generated", "v2", "outlines", "board.dxf")
PROJECT = {"L": "Hojicha44-Left", "R": "Hojicha44-Right"}
HALVES = ("L", "R")
MIRROR_AXIS = 145.75  # (x_left + x_mirror)/2 for every ergogen pair

KICAD_CLI = (
    shutil.which("kicad-cli")
    or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
)
STOCK_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

FP_SRC = {
    "SW": ("Hojicha44", "SW_Hotswap_Kailh_Choc_V1_1.00u"),
    "DIODE": ("Diode_SMD", "D_SOD-123"),
    "MCU": ("Hojicha44", "Socket_Strips_2x12_P2.54mm_NiceNano"),
    "ENC": ("Rotary_Encoder",
            "RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm_CircularMountingHoles"),
    "TRRS": ("Hojicha44", "TRRS-PJ-320A"),
    "JST": ("Connector_JST", "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"),
    "PWR": ("Button_Switch_THT", "SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm"),
    "FID": ("Fiducial", "Fiducial_1mm_Mask3mm"),
    "TOOL": ("MountingHole", "MountingHole_3.2mm_M3"),
}

COLS = ["outer", "pinky", "ring", "middle", "index", "inner"]
ROW_OF_R = {0: "top", 1: "home", 2: "bottom"}
THUMBS = ["t_ctrl", "t_cmd", "t_l1", "t_space"]


def U():
    return str(uuid.uuid4())


def r2(v):
    return round(v, 3)


# ---------------------------------------------------------------- points

def load_points():
    """{name: (x, y, r)} parsed with regex (no yaml dependency)."""
    t = open(POINTS).read()
    out = {}
    for m in re.finditer(
            r"^([A-Za-z0-9_]+):\n  x: ([-\d.]+)\n  'y': ([-\d.]+)\n  r: ([-\d.]+)",
            t, re.M):
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))
    assert len(out) >= 60, f"points: {len(out)} entries, want >= 60"
    return out


def key_points(pts, tag):
    """22 (idx, point_name, x, y, rot) in schematic idx order.

    Schematic idx: r0c0..r0c5 (0-5, top row), r1 (6-11, home), r2 (12-17,
    bottom), thumbs R3C0-3 (18-21, west->east). Right half uses the already-
    mirrored mirror_* coordinates with their given rotations.
    """
    pre = "" if tag == "L" else "mirror_"
    out = []
    for r in range(3):
        for c in range(6):
            idx = r * 6 + c
            name = f"{pre}matrix_{COLS[c]}_{ROW_OF_R[r]}"
            x, y, rot = pts[name]
            out.append((idx, name, x, y, rot))
    for i, th in enumerate(THUMBS):
        idx = 18 + i
        name = f"{pre}thumbs_{th}_cluster"
        x, y, rot = pts[name]
        out.append((idx, name, x, y, rot))
    assert len(out) == 22
    return out


# ---------------------------------------------------------------- netlist

def load_nets(tag):
    """Run kicad-cli netlist export; return (nets, pin_net).

    nets: [(code, name)]; pin_net: {(ref, pin): (code, name)}.
    """
    sch = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_sch")
    tmp = f"/tmp/hojicha-nets-{tag}.net"
    r = subprocess.run(
        [KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr",
         "-o", tmp, sch], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"netlist export failed for {tag}:\n{r.stderr}")
    s = open(tmp).read()
    nets = [(0, "")]
    pin_net = {}
    for m in re.finditer(
            r"\(net\s*\(code \"(\d+)\"\)\s*\(name \"([^\"]*)\"\)"
            r"\s*\(class \"[^\"]*\"\)(.*?)\n\t\t\)", s, re.S):
        code, name, body = int(m.group(1)), m.group(2), m.group(3)
        nets.append((code, name))
        for n in re.finditer(
                r"\(node\s*\(ref \"([^\"]+)\"\)\s*\(pin \"([^\"]+)\"\)",
                body):
            pin_net[(n.group(1), n.group(2))] = (code, name)
    if len(nets) <= 1:
        raise RuntimeError(f"netlist parse found no nets for {tag}")
    return nets, pin_net


# ---------------------------------------------------------------- outline

def load_dxf_entities():
    """Parse ENTITIES section: [('line', x1,y1,x2,y2), ('arc', cx,cy,r,a1,a2)]."""
    lines = open(BOARD_DXF).read().splitlines()
    try:
        i = lines.index("ENTITIES")
    except ValueError:
        raise RuntimeError("board.dxf has no ENTITIES section")
    ents = []
    j = i + 1
    while j < len(lines):
        t = lines[j].strip()
        if t == "ENDSEC":
            break
        if t == "LINE":
            d = {}
            j += 1
            while j + 1 < len(lines) and lines[j].strip() != "0":
                d[lines[j].strip()] = lines[j + 1].strip()
                j += 2
            ents.append(("line", float(d["10"]), float(d["20"]),
                         float(d["11"]), float(d["21"])))
            continue
        if t == "ARC":
            d = {}
            j += 1
            while j + 1 < len(lines) and lines[j].strip() != "0":
                d[lines[j].strip()] = lines[j + 1].strip()
                j += 2
            ents.append(("arc", float(d["10"]), float(d["20"]),
                         float(d["40"]), float(d["50"]), float(d["51"])))
            continue
        j += 1
    return ents


def arc_segments(cx, cy, r, a1, a2, max_step=6.0):
    """DXF arc (deg, CCW) -> list of ((x1,y1),(x2,y2)) chords.

    Ergogen emits zero-span fillet dots (span ~1e-7 deg) at tangent joints;
    those are not geometry — skip them, and drop sub-micron chords, so the
    loop-closure check sees real joints only.
    """
    while a2 < a1:
        a2 += 360.0
    span = a2 - a1
    if span < 1e-3:
        return []
    n = max(2, int(math.ceil(span / max_step)))
    pts = []
    for k in range(n + 1):
        a = math.radians(a1 + span * k / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    segs = list(zip(pts, pts[1:]))
    return [(p1, p2) for p1, p2 in segs
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 1e-3]


def outline_graphics(side):
    """Edge.Cuts gr_line items for one side, arcs segmented."""
    ents = load_dxf_entities()
    out = []
    n_arc = 0
    for e in ents:
        if e[0] == "line":
            _, x1, y1, x2, y2 = e
            if side == "L" and max(x1, x2) >= MIRROR_AXIS:
                continue
            if side == "R" and min(x1, x2) < MIRROR_AXIS:
                continue
            out.append(
                f'\t(gr_line (start {r2(x1)} {r2(y1)}) (end {r2(x2)} {r2(y2)})'
                f' (layer "Edge.Cuts") (stroke (width 0.1) (type solid))'
                f' (uuid "{U()}"))')
        else:
            _, cx, cy, r, a1, a2 = e
            if side == "L" and cx >= MIRROR_AXIS:
                continue
            if side == "R" and cx < MIRROR_AXIS:
                continue
            n_arc += 1
            for (p1, p2) in arc_segments(cx, cy, r, a1, a2):
                out.append(
                    f'\t(gr_line (start {r2(p1[0])} {r2(p1[1])})'
                    f' (end {r2(p2[0])} {r2(p2[1])})'
                    f' (layer "Edge.Cuts") (stroke (width 0.1) (type solid))'
                    f' (uuid "{U()}"))')
    # closed-loop sanity: every segment endpoint meets another segment
    ends = {}
    for g in out:
        m = re.search(r"\(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)", g)
        a = (round(float(m.group(1)), 2), round(float(m.group(2)), 2))
        b = (round(float(m.group(3)), 2), round(float(m.group(4)), 2))
        ends[a] = ends.get(a, 0) + 1
        ends[b] = ends.get(b, 0) + 1
    dangle = [p for p, n in ends.items() if n != 2]
    print(f"  outline {side}: {len(out)} segments ({n_arc} arcs), "
          f"{len(dangle)} open endpoints")
    assert not dangle, f"outline {side} not closed: {dangle[:6]}"
    return out


# ---------------------------------------------------------------- footprints

def fp_source(lib, name):
    if lib == "Hojicha44":
        p = os.path.join(PCB_DIR, "Hojicha44.pretty", name + ".kicad_mod")
    else:
        p = os.path.join(STOCK_FP, lib + ".pretty", name + ".kicad_mod")
    return open(p).read()


# KiCad footprint rotation is CLOCKWISE-positive (verified: stock TRRS at
# rot=270 maps local (-2.3,11.3) to global offset (-11.3,-2.3), i.e. CW270).
# Ergogen r is CCW-positive (makerjs). Same visual orientation therefore
# needs KiCad rot = -ergogen_r. Gets this wrong and every rotated footprint
# tilts the mirror image (plus a lib_footprint_mismatch warning per part).
def krot(erg_r):
    return r2(-erg_r)


def embed(src, libref, ref, value, x, y, rot, pin_nets, hide_ref=False,
          ref_on_fab=False, strip_silk=False, cathode_tick=False):
    """Embed a .kicad_mod as a board instance.

    Keeps all local geometry; sets the instance position, reference/value,
    per-pad nets, and fresh uuids (instances must not share uuids).
    hide_ref hides the silk reference designator; ref_on_fab moves it to
    Fab instead (dense matrix: silk refs sit on neighbour silk/pads);
    strip_silk drops F.SilkS graphics (SOD-123: the cathode bar sits 0.2mm
    from the pad and trips angle-dependent DRC noise; Fab keeps polarity).
    cathode_tick re-adds a minimal cathode tick for stripped SOD-123s:
    1.0mm bar just outside pad 1 (cathode) at 0.29mm local clearance, so
    on-board polarity stays readable after placement (independent review
    F1). Local geometry rotates with the footprint, so the clearance is
    rotation-proof; DRC re-verifies every placed rotation.
    """
    s = re.sub(r'\(footprint "[^"]*"', f'(footprint "{libref}"', src, count=1)
    s = re.sub(r'(\(layer "F\.Cu"\)\n)',
               rf'\1\t(uuid "{U()}")\n\t(at {r2(x)} {r2(y)} {r2(rot)})\n',
               s, count=1)
    s = re.sub(r'\(property "Reference" "[^"]*"',
               f'(property "Reference" "{ref}"', s, count=1)
    if hide_ref:
        s = re.sub(r'(\(property "Reference" "[^"]*"\n\t\t\(at [^)]*\)\n'
                   r'\t\t\(layer "[^"]*"\))',
                   r'\1\n\t\t(hide yes)', s, count=1)
    if ref_on_fab:
        s = re.sub(r'(\(property "Reference" "[^"]*"\n\t\t\(at [^)]*\)\n'
                   r'\t\t\(layer ")F\.SilkS(")',
                   r'\1F.Fab\2', s, count=1)
    if strip_silk:
        s = strip_layer_graphics(s, "F.SilkS")
    s = re.sub(r'\(property "Value" "[^"]*"',
               f'(property "Value" "{value}"', s, count=1)

    def padsub(blk, num):
        if num and num in pin_nets and "(net " not in blk:
            code, name = pin_nets[num]
            if "(uuid " in blk:
                blk = blk.replace("(uuid ", f'(net {code} "{name}") (uuid ',
                                  1)
            else:
                blk = blk[:-1].rstrip() + f' (net {code} "{name}")\n\t)'
        return blk

    out = []
    i = 0
    while i < len(s):
        m = re.search(r'\(pad "([^"]*)"', s[i:])
        if not m:
            out.append(s[i:])
            break
        j = i + m.start()
        out.append(s[i:j])
        depth, k = 0, j
        while True:
            if s[k] == "(":
                depth += 1
            elif s[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append(padsub(s[j:k + 1], m.group(1)))
        i = k + 1
    s = "".join(out)
    s = re.sub(r'uuid "[^"]*"', lambda m: f'uuid "{U()}"', s)
    if cathode_tick:
        s = (s.rstrip()[:-1].rstrip() +
             f'\n\t(fp_line (start -2.45 -0.5) (end -2.45 0.5)'
             f' (stroke (width 0.12) (type solid)) (layer "F.SilkS")'
             f' (uuid "{U()}"))\n)')
    return s


def ref_nets(pin_net, ref):
    """{pin: (code, name)} for one refdes."""
    return {p: v for (r, p), v in pin_net.items() if r == ref}


def cw_rotate(x, y, deg):
    """KiCad clockwise-positive rotation of a local point."""
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a),
            -x * math.sin(a) + y * math.cos(a))


def outline_loops(side):
    """Closed Edge.Cuts loops for one side, largest first."""
    ents = load_dxf_entities()
    segs = []
    for e in ents:
        if e[0] == "line":
            _, x1, y1, x2, y2 = e
            if side == "L" and max(x1, x2) >= MIRROR_AXIS:
                continue
            if side == "R" and min(x1, x2) < MIRROR_AXIS:
                continue
            segs.append(((x1, y1), (x2, y2)))
        else:
            _, cx, cy, r, a1, a2 = e
            if side == "L" and cx >= MIRROR_AXIS:
                continue
            if side == "R" and cx < MIRROR_AXIS:
                continue
            segs.extend(arc_segments(cx, cy, r, a1, a2))
    # chain into loops (segments usable in either direction)
    def key(p):
        return (round(p[0], 2), round(p[1], 2))
    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append((a, b))
        adj.setdefault(key(b), []).append((a, b))
    used = set()
    loops = []
    for idx, (a0, b0) in enumerate(segs):
        if idx in used:
            continue
        loop, cur, prev = [key(a0)], key(b0), key(a0)
        # mark first segment used
        for j, (a, b) in enumerate(segs):
            if j not in used and ((key(a) == prev and key(b) == cur)
                                  or (key(b) == prev and key(a) == cur)):
                used.add(j)
                break
        while cur != loop[0]:
            nxt = None
            for j, (a, b) in enumerate(segs):
                if j in used:
                    continue
                if key(a) == cur and key(b) != prev:
                    nxt = (j, key(b))
                    break
                if key(b) == cur and key(a) != prev:
                    nxt = (j, key(a))
                    break
            if nxt is None:
                # dead end: try any unused segment touching cur (T-junction)
                for j, (a, b) in enumerate(segs):
                    if j in used:
                        continue
                    if key(a) == cur:
                        nxt = (j, key(b))
                        break
                    if key(b) == cur:
                        nxt = (j, key(a))
                        break
            if nxt is None:
                raise RuntimeError(f"outline {side}: open loop at {cur}")
            used.add(nxt[0])
            prev, cur = cur, nxt[1]
            loop.append(cur)
            assert len(loop) < len(segs) + 2, f"outline {side}: loop runaway"
        loops.append(loop)
    def area(loop):
        return sum(loop[i][0] * loop[(i + 1) % len(loop)][1]
                   - loop[(i + 1) % len(loop)][0] * loop[i][1]
                   for i in range(len(loop))) / 2
    loops.sort(key=lambda l: -abs(area(l)))
    return loops


def inside_outline(loops, x, y):
    """In largest loop and not inside any smaller (notch/hole) loop."""
    def inside(loop):
        c = False
        n = len(loop)
        for i in range(n):
            x1, y1 = loop[i]
            x2, y2 = loop[(i + 1) % n]
            if ((y1 > y) != (y2 > y)):
                xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < xin:
                    c = not c
        return c
    if not loops or not inside(loops[0]):
        return False
    return not any(inside(l) for l in loops[1:])


def footprint_pads(src, numbered=True):
    """[(number, x, y)] for pads in a .kicad_mod.

    numbered=True (default): only net-assignable pads. numbered=False also
    returns NPTH/mechanical "" pads — needed for clearance searches (a
    tooling hole drilled 1.5mm from a switch mounting hole proved it).
    """
    return [(m.group(1), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r'\(pad "([^"]*)"\s+\S+\s+\S+\s*\(at ([-\d.]+) ([-\d.]+)',
                                 src) if (m.group(1) or not numbered)]


def courtyard_segments(src, circle_steps=16):
    """F.CrtYd outline as segments (circles approximated), footprint-local."""
    segs = []
    s = src

    def blocks():
        i = 0
        while True:
            m = re.search(
                r"\n\t\((fp_line|fp_rect|fp_circle|fp_arc|fp_poly)[\s]", s[i:])
            if not m:
                return
            j = i + m.start()
            depth, k = 0, j + 1
            while True:
                if s[k] == "(":
                    depth += 1
                elif s[k] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            yield s[j:k + 1]
            i = k + 1

    for blk in blocks():
        if '(layer "F.CrtYd")' not in blk:
            continue
        if blk.startswith("\n\t(fp_line"):
            a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            segs.append(((float(a.group(1)), float(a.group(2))),
                         (float(b.group(1)), float(b.group(2)))))
        elif blk.startswith("\n\t(fp_rect"):
            a = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", blk)
            b = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            x1, y1, x2, y2 = (float(a.group(1)), float(a.group(2)),
                              float(b.group(1)), float(b.group(2)))
            c = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            segs += list(zip(c, c[1:] + c[:1]))
        elif blk.startswith("\n\t(fp_circle"):
            c = re.search(r"\(center ([-\d.]+) ([-\d.]+)\)", blk)
            e = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", blk)
            cx, cy = float(c.group(1)), float(c.group(2))
            r = math.hypot(float(e.group(1)) - cx, float(e.group(2)) - cy)
            pts = [(cx + r * math.cos(2 * math.pi * k / circle_steps),
                    cy + r * math.sin(2 * math.pi * k / circle_steps))
                   for k in range(circle_steps)]
            segs += list(zip(pts, pts[1:] + pts[:1]))
    return segs


def check_containment(tag, placements):
    """Every numbered pad must sit inside its half's outline.

    Would have caught the original TRRS error (mouth-end pads off-board)
    which DRC does not check.
    """
    loops = outline_loops(tag)
    bad = []
    for kind, lib, name, ref, value, x, y, rot, *_ in placements:
        if kind in ("FID", "TOOL"):
            if not inside_outline(loops, x, y):
                bad.append(f"{ref} at ({r2(x)}, {r2(y)})")
            continue
        src = fp_source(lib, name)
        for num, px, py in footprint_pads(src):
            gx, gy = cw_rotate(px, py, rot)
            if not inside_outline(loops, x + gx, y + gy):
                bad.append(f"{ref}.{num} at ({r2(x + gx)}, {r2(y + gy)})")
    print(f"  containment {tag}: {len(placements)} "
          f"footprints checked" + ("" if not bad else f" — {len(bad)} OFF-BOARD"))
    for b in bad[:10]:
        print(f"  !! off-board pad {b}")
    assert not bad, f"{len(bad)} pads outside the {tag} outline"


def strip_layer_graphics(s, layer):
    """Drop top-level fp_* graphics blocks on one layer (keep pads/text)."""
    out = []
    i = 0
    while i < len(s):
        m = re.search(r"\n\t\((fp_line|fp_rect|fp_circle|fp_arc|fp_poly|fp_curve|fp_text)[\s]",
                      s[i:])
        if not m:
            out.append(s[i:])
            break
        j = i + m.start()
        out.append(s[i:j])
        depth, k = 0, j + 1
        while True:
            if s[k] == "(":
                depth += 1
            elif s[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blk = s[j:k + 1]
        if f'(layer "{layer}")' not in blk:
            out.append(blk)
        i = k + 1
    return "".join(out)


def seg_dist(px, py, a, b):
    """Distance from a point to a segment."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# ---------------------------------------------------------------- fiducials

FID_EDGE_MM = 3.0  # min distance from any Edge.Cuts segment (fix.md P0-2)
FID_PAD_MM = 3.0   # min distance from any placed pad centre (mask clearance)


def pick_fiducials(tag, placements, n=3):
    """n fiducial centres on real board area, clear of the edge and pads.

    Targets are the old intent (outer top-left, outer top-right, bottom
    centre) but each one snaps to the nearest valid 1 mm grid point. The old
    bbox-corner rule put all six fiducials outside the irregular outline.
    """
    loops = outline_loops(tag)
    edges = [(a, b) for loop in loops
             for a, b in zip(loop, loop[1:] + loop[:1])]
    pads = []
    for kind, lib, name, ref, value, x, y, rot, *_ in placements:
        if kind == "FID":
            continue
        for num, px, py in footprint_pads(fp_source(lib, name),
                                          numbered=False):
            gx, gy = cw_rotate(px, py, rot)
            pads.append((x + gx, y + gy))

    xs = [p[0] for loop in loops for p in loop]
    ys = [p[1] for loop in loops for p in loop]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cands = []
    for gx in range(math.floor(x0), math.ceil(x1) + 1):
        for gy in range(math.floor(y0), math.ceil(y1) + 1):
            if not inside_outline(loops, gx, gy):
                continue
            if min(seg_dist(gx, gy, a, b) for a, b in edges) < FID_EDGE_MM:
                continue
            if any(math.hypot(gx - px, gy - py) < FID_PAD_MM for px, py in pads):
                continue
            cands.append((float(gx), float(gy)))
    assert cands, f"{tag}: no valid fiducial spot inside the outline"

    targets = [(x0 + 6, y1 - 6), (x1 - 6, y1 - 6), ((x0 + x1) / 2, y0 + 6)]
    chosen = []
    for tx, ty in targets[:n]:
        free = [c for c in cands
                if all(math.hypot(c[0] - q[0], c[1] - q[1]) >= 20 for q in chosen)]
        best = min(free or cands,
                   key=lambda c: math.hypot(c[0] - tx, c[1] - ty))
        chosen.append(best)
    print(f"  fiducials {tag}: " + ", ".join(f"({x:.0f},{y:.0f})" for x, y in chosen))
    return chosen


def pick_tooling(tag, placements, fiducials, n=2):
    """n 3.2mm NPTH tooling holes: inside, far from edge/pads/fiducials.

    Gasket mounting uses no PCB holes, but SMD assembly wants fab tooling.
    Stricter clearances than fiducials (drill breaks out near copper), and
    courtyard-aware: pad centres alone miss courtyard corners (MT_L1 vs
    SW_L12 proved it — 11.4mm centre distance still overlapped).
    """
    loops = outline_loops(tag)
    edges = [(a, b) for loop in loops
             for a, b in zip(loop, loop[1:] + loop[:1])]
    pads = []
    crt = []
    boxes = []
    for kind, lib, name, ref, value, x, y, rot, *_ in placements:
        if kind in ("FID", "TOOL"):
            continue
        src = fp_source(lib, name)
        for num, px, py in footprint_pads(src, numbered=False):
            gx, gy = cw_rotate(px, py, rot)
            pads.append((x + gx, y + gy))
        pts = []
        for (ax, ay), (bx, by) in courtyard_segments(src):
            gax, gay = cw_rotate(ax, ay, rot)
            gbx, gby = cw_rotate(bx, by, rot)
            crt.append(((x + gax, y + gay), (x + gbx, y + gby)))
            pts += [(x + gax, y + gay), (x + gbx, y + gby)]
        if pts:
            # grown by the tooling courtyard radius: a candidate INSIDE a
            # courtyard still has segment distance > 0, so the segment test
            # alone passes holes right through courtyards.
            xs2 = [p[0] for p in pts]
            ys2 = [p[1] for p in pts]
            boxes.append((min(xs2) - 3.7, min(ys2) - 3.7,
                          max(xs2) + 3.7, max(ys2) + 3.7))
    xs = [p[0] for loop in loops for p in loop]
    ys = [p[1] for loop in loops for p in loop]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cands = []
    for gx in range(math.floor(x0), math.ceil(x1) + 1):
        for gy in range(math.floor(y0), math.ceil(y1) + 1):
            if not inside_outline(loops, gx, gy):
                continue
            if min(seg_dist(gx, gy, a, b) for a, b in edges) < 4.0:
                continue
            if any(math.hypot(gx - px, gy - py) < 5.0 for px, py in pads):
                continue
            if any(bx0 <= gx <= bx1 and by0 <= gy <= by1
                   for bx0, by0, bx1, by1 in boxes):
                continue
            if any(seg_dist(gx, gy, a, b) < 3.7 for a, b in crt):
                continue
            cands.append((float(gx), float(gy)))
    assert cands, f"{tag}: no valid tooling-hole spot inside the outline"
    targets = [(x0 + 8, (y0 + y1) / 2), (x1 - 8, (y0 + y1) / 2)]
    chosen = []
    for tx, ty in targets[:n]:
        taken = fiducials + chosen
        free = [c for c in cands
                if all(math.hypot(c[0] - q[0], c[1] - q[1]) >= 20 for q in taken)]
        best = min(free or cands,
                   key=lambda c: math.hypot(c[0] - tx, c[1] - ty))
        chosen.append(best)
    print(f"  tooling {tag}: " + ", ".join(f"({x:.0f},{y:.0f})" for x, y in chosen))
    return chosen


# ---------------------------------------------------------------- copper
#
# Ownership split: the generator owns the outline, footprints, nets and
# placement; a human (or a router) owns copper. gen_pcb.py rebuilds the whole
# board body from scratch, so routed tracks would otherwise be thrown away by
# the next run — a fake segment injected into a sandbox copy did not survive
# build_board(). Preserved copper is remapped by net NAME (net codes are
# assigned per netlist export and are not stable) and then checked: every
# preserved track must still terminate on real copper, and none may enter the
# antenna keepout. A footprint that moves without re-routing therefore fails
# the build instead of producing a silently broken board.

ANT_R_MM = 5.0   # antenna copper keepout radius (config: antenna_keepout)
COPPER_KINDS = ("segment", "via", "zone")


def top_level_items(s):
    """[(start, end, keyword)] for the board items inside (kicad_pcb ...).

    Depth 1 is a board item: the whole file is one s-expression, so the
    items to walk are the children of the root, not the root itself.
    """
    items, depth, start, keyword = [], 0, None, None
    in_str = esc = False
    for i, c in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            if depth == 1:
                start = i
                m = re.match(r"\(([A-Za-z_][\w.-]*)", s[i:])
                keyword = m.group(1) if m else None
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 1 and start is not None:
                items.append((start, i + 1, keyword))
                start = None
    assert depth == 0, "unbalanced parentheses in board file"
    return items


def extract_copper(path, name_code):
    """[(kind, raw_block)] of existing copper, net codes remapped by name.

    A net the new netlist does not know is a hard error: silently renumbering
    would weld a track onto the wrong net, which DRC only notices as an
    unconnected item somewhere else.
    """
    if not os.path.exists(path):
        return []
    s = open(path).read()
    code_name = {int(m.group(1)): m.group(2)
                 for m in re.finditer(r"\n\t\(net (\d+) \"([^\"]*)\"\)", s)}
    out = []
    for a, b, kw in top_level_items(s):
        if kw not in COPPER_KINDS:
            continue
        blk = s[a:b]
        m = re.search(r"\(net (\d+)\)", blk)
        if m:
            old = int(m.group(1))
            nm = re.search(r'\(net_name "([^"]*)"\)', blk)
            name = nm.group(1) if nm and nm.group(1) in name_code \
                else code_name.get(old)
            if name is None:
                raise RuntimeError(f"{os.path.basename(path)}: copper on net "
                                   f"code {old} with no name")
            if name not in name_code:
                raise RuntimeError(
                    f"{os.path.basename(path)}: preserved copper is on net "
                    f"'{name}', which the schematic no longer has — delete or "
                    f"re-route it")
            blk = blk.replace(f"(net {old})", f"(net {name_code[name]})", 1)
        out.append((kw, blk))
    return out


def copper_pieces(copper, code_name):
    """(segments, vias) as {net name: [(...)]} for the dangling check."""
    segs, vias = {}, {}
    for kind, blk in copper:
        m = re.search(r"\(net (\d+)\)", blk)
        if not m:
            continue
        name = code_name[int(m.group(1))]
        if kind == "segment":
            g = re.search(r"\(start ([\d.-]+) ([\d.-]+)\)\s*"
                          r"\(end ([\d.-]+) ([\d.-]+)\)", blk)
            segs.setdefault(name, []).append(tuple(float(g.group(i))
                                                   for i in (1, 2, 3, 4)))
        elif kind == "via":
            g = re.search(r"\(at ([\d.-]+) ([\d.-]+)\)", blk)
            vias.setdefault(name, []).append((float(g.group(1)), float(g.group(2))))
    return segs, vias


def check_copper(tag, copper, placements, code_name, pts):
    """Preserved copper must attach to copper and avoid the antenna keepout.

    Catches the invisible break: move a footprint, regenerate, and the old
    track now ends in the middle of nowhere. KiCad reports that only as an
    unconnected item — indistinguishable from the pre-routing state, so the
    DRC waiver would hide it.
    """
    segs, vias = copper_pieces(copper, code_name)
    pads = {}
    for p in placements:
        kind, lib, name, ref, value, x, y, rot = p[:8]
        pn = p[11]
        for num, px, py in footprint_pads(fp_source(lib, name)):
            if num not in pn:
                continue
            gx, gy = cw_rotate(px, py, rot)
            pads.setdefault(pn[num][1], []).append((x + gx, y + gy))

    def same(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) < 0.01

    bad = []
    for name, ss in segs.items():
        plist, vlist = pads.get(name, []), vias.get(name, [])
        for i, seg in enumerate(ss):
            for pt in (seg[:2], seg[2:]):
                touch = (sum(same(pt, q) for q in plist)
                         + sum(same(pt, q) for q in vlist)
                         + sum(1 for k, o in enumerate(ss)
                               if k != i and (same(pt, o[:2]) or same(pt, o[2:]))))
                if touch == 0:
                    bad.append(f"{name}: dangling track end at "
                               f"({r2(pt[0])}, {r2(pt[1])})")

    ax, ay, _ = pts["antenna" if tag == "L" else "mirror_antenna"]
    for name, ss in segs.items():
        for x1, y1, x2, y2 in ss:
            d = seg_dist(ax, ay, (x1, y1), (x2, y2))
            if d < ANT_R_MM - 1e-9:
                bad.append(f"{name}: track passes {r2(d)}mm from the antenna "
                           f"centre (keepout r={ANT_R_MM})")
    for name, vs in vias.items():
        for vx, vy in vs:
            d = math.hypot(vx - ax, vy - ay)
            if d < ANT_R_MM - 1e-9:
                bad.append(f"{name}: via {r2(d)}mm from the antenna centre "
                           f"(keepout r={ANT_R_MM})")

    n = sum(1 for k, _ in copper if k == "segment")
    nv = sum(1 for k, _ in copper if k == "via")
    nz = sum(1 for k, _ in copper if k == "zone")
    print(f"  copper {tag}: {n} segments, {nv} vias, {nz} zones preserved"
          + ("" if not bad else f" — {len(bad)} PROBLEM"))
    for b in bad[:10]:
        print(f"  !! {b}")
    assert not bad, f"{len(bad)} copper problems on {tag}"


# ---------------------------------------------------------------- build

def build_placements(tag, pts, pin_net):
    """49 schematic placements + fiducials + tooling (no file I/O)."""
    placements = []

    keys = key_points(pts, tag)
    for idx, pname, x, y, rot in keys:
        placements.append(("SW", *FP_SRC["SW"], f"SW_{tag}{idx:02d}",
                           f"K{idx:02d}", x, y, krot(rot), False, True, False,
                           ref_nets(pin_net, f"SW_{tag}{idx:02d}")))
        # Diode in the inter-key gap beside its switch. The RIGHT half is a
        # true mirror: offset direction negates (east on L, west on R) while
        # the body rotation stays krot+90 — mod 180 that IS the mirrored axis
        # (-(k+90) == -k+90), and N/S polarity is preserved across the mirror
        # (nets follow pad numbers either way). Same-side offsets would pile
        # the outer-column diode against the board edge instead of the gap.
        sgn = 1 if tag == "L" else -1
        dx = sgn * 9.5 * math.cos(math.radians(rot))
        dy = sgn * 9.5 * math.sin(math.radians(rot))
        placements.append(("DIODE", *FP_SRC["DIODE"], f"D_{tag}{idx:02d}",
                           "1N4148W", x + dx, y + dy, krot(rot) + 90,
                           False, True, True,
                           ref_nets(pin_net, f"D_{tag}{idx:02d}")))

    mx, my, _ = pts["mcu" if tag == "L" else "mirror_mcu"]
    # socket USB end (local y=0) faces north: rot 180, pad-centre on mcu,
    # shifted 0.5mm south so the silk top clears the USB-notch cutout.
    placements.append(("MCU", *FP_SRC["MCU"], f"U_{tag}1", "nice!nano v2",
                       mx - 7.62, my + 13.97 - 0.5, 180, False, False, False,
                       ref_nets(pin_net, f"U_{tag}1")))

    ex, ey, _ = pts["encoder" if tag == "L" else "mirror_encoder"]
    # stock origin is pad A; shaft centre is +(7.5, 2.5).
    placements.append(("ENC", *FP_SRC["ENC"], f"ENC_{tag}1", "EC11E-Switch",
                       ex - 7.5, ey - 2.5, 0, False, False, False,
                       ref_nets(pin_net, f"ENC_{tag}1")))

    tx, ty, _ = pts["trrs" if tag == "L" else "mirror_trrs"]
    # stock mouth at local +Y (sleeve text y=11.4, silk top 12.6); face the
    # split gap with the body 2mm inboard of the anchor so the mouth-end
    # pads stay on copper AND the mouth silk clears the slanted inner edge
    # (the edge leans 2.77mm over the jack height — mouth-at-anchor+8.5
    # would hang T/S pads off the board).
    if tag == "L":
        placements.append(("TRRS", *FP_SRC["TRRS"], f"J_{tag}1",
                           "PJ-320A TRRS", tx - 8.05, ty, 90,
                           False, False, False,
                           ref_nets(pin_net, f"J_{tag}1")))
    else:
        placements.append(("TRRS", *FP_SRC["TRRS"], f"J_{tag}1",
                           "PJ-320A TRRS", tx + 8.05, ty, 270,
                           False, False, False,
                           ref_nets(pin_net, f"J_{tag}1")))

    jx, jy, _ = pts["jst" if tag == "L" else "mirror_jst"]
    placements.append(("JST", *FP_SRC["JST"], f"J_{tag}2", "BATT_LIPO",
                       jx, jy, 0, False, False, False,
                       ref_nets(pin_net, f"J_{tag}2")))

    px, py, _ = pts["pwrsw" if tag == "L" else "mirror_pwrsw"]
    placements.append(("PWR", *FP_SRC["PWR"], f"SW_{tag}PWR1", "PWR_SW",
                       px, py, 0, False, False, False,
                       ref_nets(pin_net, f"SW_{tag}PWR1")))

    # every schematic footprint must be placed exactly once (no extras, none
    # missing) — otherwise net parity is a lie.
    sch_refs = {r for (r, _) in pin_net} | \
        {f"SW_{tag}{i:02d}" for i in range(22)} | \
        {f"D_{tag}{i:02d}" for i in range(22)}
    placed_refs = {p[3] for p in placements}
    # pin_net only holds refs that own nets; power symbols own none. The
    # schematic-placement cross-check lives in gen_schematic; here assert the
    # 49 expected schematic footprints are present.
    want = {f"SW_{tag}{i:02d}" for i in range(22)} | \
        {f"D_{tag}{i:02d}" for i in range(22)} | \
        {f"U_{tag}1", f"ENC_{tag}1", f"J_{tag}1", f"J_{tag}2", f"SW_{tag}PWR1"}
    assert placed_refs == want, \
        f"placement refs drift: {sorted(placed_refs ^ want)}"

    # fiducials: three targets on real board area (see pick_fiducials —
    # edge-and-pad-clear, inside the outline; the old bbox-corner rule put
    # all six off the board).
    for i, (fx, fy) in enumerate(pick_fiducials(tag, placements), start=1):
        placements.append(("FID", *FP_SRC["FID"], f"FID_{tag}{i}",
                           "FIDUCIAL", fx, fy, 0, True, True, False, {}))
    # tooling holes: 2x 3.2mm NPTH for SMD assembly (gasket mounting itself
    # uses no PCB holes — these are fab tooling, in confirmed-open areas).
    fid_pts = [(p[5], p[6]) for p in placements if p[0] == "FID"]
    for i, (hx, hy) in enumerate(pick_tooling(tag, placements, fid_pts), start=1):
        placements.append(("TOOL", *FP_SRC["TOOL"], f"MT_{tag}{i}",
                           "TOOLING", hx, hy, 0, True, True, False, {}))
    return placements


def build_board(tag, pts):
    nets, pin_net = load_nets(tag)
    codes = {c for c, _ in nets}
    assert 0 in codes, "net 0 missing"
    placements = build_placements(tag, pts, pin_net)
    gfx = outline_graphics(tag)

    # --- emit ---
    path = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")
    blank = open(path).read()
    name_code = {n: c for c, n in nets}
    copper = extract_copper(path, name_code)
    import gen_route as router
    tag_now = f"placed+routed r{router.ROUTER_VERSION}"
    mtag = re.search(r'\(comment 2 "([^"]*)"\)', blank)
    if mtag is None or mtag.group(1) != tag_now:
        if copper:
            print(f"  copper {tag}: dropping {len(copper)} items from "
                  f"older revision ({mtag.group(1) if mtag else 'none'}); "
                  f"GUI copper must be re-added after router revs")
        copper = []
    head = blank.split('(net 0 "")')[0] + '(net 0 "")\n'
    head = re.sub(r'\(comment 2 "[^"]*"\)', f'(comment 2 "{tag_now}")', head)
    for code, name in sorted(nets):
        if code == 0:
            continue
        head += f'\t(net {code} "{name}")\n'

    body = []
    for kind, lib, name, ref, value, x, y, rot, hide, fab, strip, pn in placements:
        src = fp_source(lib, name)
        body.append(embed(src, f"{lib}:{name}", ref, value, x, y, rot, pn,
                          hide_ref=hide, ref_on_fab=fab, strip_silk=strip,
                          cathode_tick=(kind == "DIODE")))

    # antenna keepout marking + JST pin-1 "+" (placement review aids; the
    # copper-pour keepout is enforced at routing — no pours exist yet).
    ax, ay, _ = pts["antenna" if tag == "L" else "mirror_antenna"]
    jx, jy, _ = pts["jst" if tag == "L" else "mirror_jst"]
    body.append(
        f'\t(gr_circle (center {r2(ax)} {r2(ay)}) (end {r2(ax + 5)} {r2(ay)})'
        f' (layer "Cmts.User") (stroke (width 0.15) (type solid))'
        f' (fill none) (uuid "{U()}"))')
    body.append(
        f'\t(gr_text "ANT KEEPOUT" (at {r2(ax)} {r2(ay - 7)} 0)'
        f' (layer "Cmts.User") (uuid "{U()}")'
        f' (effects (font (size 1 1) (thickness 0.15))))')
    body.append(
        f'\t(gr_text "+" (at {r2(jx - 3.5)} {r2(jy)} 0)'
        f' (layer "F.SilkS") (uuid "{U()}")'
        f' (effects (font (size 1 1) (thickness 0.15))))')

    # --- route (deterministic; generator-owned copper) ---
    import gen_route as router
    _board, _tracks, _vias = router.plan(tag, pts, placements, nets, pin_net)
    _segs, _vv = router.emit(_board, _tracks, _vias)
    route_blocks = _segs + _vv
    fresh = {router.normalize(b) for b in route_blocks}
    kept = [(k, b) for k, b in copper if router.normalize(b) not in fresh]
    if len(kept) != len(copper):
        print(f"  copper {tag}: {len(copper) - len(kept)} regenerated "
              f"(dedupe), {len(kept)} GUI items kept")

    with open(path, "w") as f:
        f.write(head)
        f.write("\n".join(gfx) + "\n")
        f.write("\n".join(body + route_blocks + [b for _, b in kept]) + "\n)\n")
    print(f"{PROJECT[tag]}: {len(placements)} footprints, "
          f"{len(nets)} nets, {len(gfx)} edge segments, "
          f"{len(route_blocks)} routed + {len(kept)} preserved copper items")
    check_containment(tag, placements)
    check_copper(tag, kept, placements, {c: n for c, n in nets}, pts)
    return path


def drc(tag):
    """Run DRC and enforce the placement gate.

    Passes with: documented waivers W1/W2 only. unconnected_items is NOT
    waived (routing landed — DRC is the connectivity backstop).
    Anything else fails the build.
    """
    out = os.path.join(PCB_DIR, PROJECT[tag] + "-drc.rpt")
    r = subprocess.run(
        [KICAD_CLI, "pcb", "drc", "--severity-all", "--format", "report",
         "-o", out, os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")],
        capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"  {tail[-1] if tail else 'drc done'}")
    return check_drc_report(out, tag)


def check_drc_report(path, tag=None):
    """0 if clean (modulo waivers), 1 otherwise. Prints non-waived items."""
    import collections
    if tag is None:
        tag = "R" if "-Right-" in path or "Right" in path else "L"
    # Waiver W1: exact expected lib_footprint_mismatch set per half.
    # 28 = 22x D_SOD-123 (stripped silk + cathode tick) + 4x thumb Choc
    # (rotated) + MCU socket (reversed column) + TRRS (renamed pads).
    # A 29th mismatch (or a missing one) fails the build instead of passing
    # silently under the old blanket skip.
    w1_want = (
        {("D_SOD-123", f"D_{tag}{i:02d}") for i in range(22)}
        | {("SW_Hotswap_Kailh_Choc_V1_1.00u", f"SW_{tag}{i:02d}")
           for i in (18, 19, 20, 21)}
        | {("Socket_Strips_2x12_P2.54mm_NiceNano", f"U_{tag}1"),
           ("TRRS-PJ-320A", f"J_{tag}1")}
    )
    s = open(path).read()
    pats = re.findall(r"\[(.*?)\]: (.*?)\n((?:    .*\n)+)", s)
    counts = collections.Counter()
    bad = []
    w1_got = set()
    for typ, desc, body in pats:
        counts[typ] += 1
        # unconnected_items: NOT waived — routing landed (r10), DRC is the
        # backstop and must stay armed. Any unconnected item fails the build.
        if typ == "lib_footprint_mismatch":
            txt = f"{desc}\n{body}"
            for m in re.finditer(
                    r"Footprint '([^']+)' does not match.*?Footprint (\S+)",
                    txt, re.S):
                w1_got.add((m.group(1), m.group(2)))
            continue  # set asserted after the loop, not blanket-skipped
        if typ == "silk_over_copper":
            refs = set(re.findall(r"of (SW_[LR]\d+|SW_[LR]PWR1) on [BM]\.Cu", body))
            segs = set(re.findall(r"Segment of (SW_[LR]\d+|SW_[LR]PWR1) on [BM]\.Silk(?:screen|S)", body))
            pads = re.findall(r"Pad (\d+) \[.*?\] of (SW_[LR]\d+|SW_[LR]PWR1) on ([BM])\.Cu", body)
            # waiver W2: Choc B.SilkS socket outline vs its OWN pad 2 —
            # vendor marginality, proven angle-dependent rasterization noise
            # (lone footprint: rot +13.5 clean, -13.5 flagged; rigid geometry
            # is rotation-invariant, so the flag cannot be real). Silk sits
            # under the socket frame, covered by the solder fillet.
            if (refs == segs and len(refs) == 1
                    and all(p[0] == "2" and p[1] in refs and p[2] == "B"
                            for p in pads) and pads):
                continue
        bad.append((typ, desc, body))
    if w1_got != w1_want:
        print(f"  drc W1 mismatch {tag}: want {len(w1_want)}, got {len(w1_got)}")
        for m in sorted(w1_want - w1_got)[:10]:
            print(f"  !! W1 missing {m}")
        for m in sorted(w1_got - w1_want)[:10]:
            print(f"  !! W1 extra {m}")
        bad.append(("lib_footprint_mismatch", "W1 set drift",
                    f"want {sorted(w1_want)}\ngot {sorted(w1_got)}\n"))
    print(f"  drc: {dict(counts)}" +
          ("" if not bad else f" — {len(bad)} NON-WAIVED"))
    for typ, desc, body in bad[:10]:
        print(f"  !! [{typ}] {desc}\n{body}")
    return 1 if bad else 0


def main():
    pts = load_points()
    for tag in HALVES:
        build_board(tag, pts)
    # Artifact gates (committed check_board.py — were /tmp scripts):
    # outline topology, fiducials, notch openness, per built board file.
    import check_board
    rc = 0
    for tag in HALVES:
        rc |= check_board.check(tag, pts)
    # DRC gate: placement must be clean modulo documented waivers
    # (W1/W2 only — unconnected is NOT waived). Exit non-zero otherwise.
    for tag in HALVES:
        rc |= drc(tag)
    sys.exit(rc)


if __name__ == "__main__":
    main()

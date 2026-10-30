"""Gerber-style PCB artwork, generated from the real placement file.

Round 24c (review: "actual traces, as you would find on pcb gerber").

The old PCB was a procedural band field: evenly spaced gold stripes.
That is not what a board looks like. A real board is ROUTED -- traces
leave a pad, run at 0/45/90 degrees, jog around obstacles, and end on
another pad or a via; the copper sits under a soldermask except where
the mask is opened for pads; silkscreen prints outlines and references
on top.

This module draws that artwork with PIL, in BOARD MILLIMETRE space
(the same units as generated/renders/assets/placements.json), and
writes two maps:

  pcb_albedo.png   mask green, copper, exposed pad plating, silk
  pcb_metal.png    white where copper is exposed (drives metallic +
                   roughness + bump in the material)

The board mesh's local axes are x = placement x, z = placement y
(verified against D_L00 at 9.5/30.0), and its bounding box is passed
in so the caller can map the image to the mesh exactly.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- inks
MASK_GREEN = (18, 74, 40)
MASK_GREEN_D = (12, 54, 30)
# copper UNDER MASK is not gold -- the resin tints it. It reads as a
# lighter, more saturated green on a real board, which is exactly why a
# finished PCB shows its traces as a tonal web rather than as metal.
COPPER = (96, 176, 104)
COPPER_HOT = (74, 146, 84)       # bus/pour edges, a touch lighter
COPPER_EXPOSED = (206, 170, 92)  # ENIG pads: bright champagne gold
SILK = (196, 198, 190)

PX_PER_MM = 16.0

FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
)


def _font(px):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, px)
            except Exception:
                pass
    return ImageFont.load_default()


# ------------------------------------------------------------ routing
def route_path(p0, p1, rng, jog=0.5):
    """A 0/45/90 degree route from p0 to p1.

    Real routers leave a pad, run 45 degrees for a while, then finish
    straight. `jog` chooses where the diagonal happens, and a small
    random nudge keeps a bundle of parallel traces from collapsing
    into one line.
    """
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return [p0, p1]
    k = jog + rng.uniform(-0.12, 0.12)
    k = min(max(k, 0.2), 0.8)
    if abs(dx) > abs(dy):
        # diagonal until y is satisfied, then straight in x
        s = math.copysign(1.0, dx)
        t = math.copysign(1.0, dy) if dy else 0.0
        xm = x0 + s * abs(dy) * k
        return [(x0, y0), (xm, y0 + (xm - x0) * t), (x1, y1)]
    s = math.copysign(1.0, dy)
    t = math.copysign(1.0, dx) if dx else 0.0
    ym = y0 + s * abs(dx) * k
    return [(x0, y0), (x0 + (ym - y0) * t, ym), (x1, y1)]


def _draw_route(d, pts, mm, rng, w_mm=0.25):
    """Line with the 45-degree corner rounded by the joint setting."""
    px = [(x * mm, y * mm) for x, y in pts]
    d.line(px, fill=None, width=max(1, int(round(w_mm * mm))), joint="curve")


def _line(d, pts, mm, w_mm, col, org=(0.0, 0.0)):
    px = [((x - org[0]) * mm, (y - org[1]) * mm) for x, y in pts]
    d.line(px, fill=col, width=max(1, int(round(w_mm * mm))), joint="curve")


def _pad(d, x, y, w, h, mm, col, org=(0.0, 0.0), round_=False):
    x, y = x - org[0], y - org[1]
    x0, y0 = (x - w / 2) * mm, (y - h / 2) * mm
    x1, y1 = (x + w / 2) * mm, (y + h / 2) * mm
    if round_:
        d.ellipse([x0, y0, x1, y1], fill=col)
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius=max(1, int(0.15 * mm)),
                            fill=col)


def _via(d, x, y, mm, col, ring=(20, 40, 26), org=(0.0, 0.0)):
    """Annular ring: copper circle with the drill punched through."""
    r = 0.35 * mm
    cx, cy = (x - org[0]) * mm, (y - org[1]) * mm
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    ri = 0.16 * mm
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=ring)


# ------------------------------------------------------------ artwork
def build_art(placements, bbox, outdir, seed=44, silk_text=True,
              prefix="pcb"):
    """Draw one half's artwork. Returns (albedo_path, metal_path).

    placements: list of dicts with ref/x/y/rot from placements.json
    bbox: (x0, y0, x1, y1) of the board mesh in board millimetres
    """
    x0, y0, x1, y1 = bbox
    mm = PX_PER_MM
    W = int(round((x1 - x0) * mm))
    H = int(round((y1 - y0) * mm))
    origin = (x0, y0)

    def T(x, y):
        return ((x - origin[0]) * mm, (y - origin[1]) * mm)

    rng = random.Random(seed)

    albedo = Image.new("RGB", (W, H), MASK_GREEN)
    metal = Image.new("L", (W, H), 0)
    silk = Image.new("L", (W, H), 0)
    da = ImageDraw.Draw(albedo)
    dm = ImageDraw.Draw(metal)
    ds = ImageDraw.Draw(silk)

    # ---- soldermask: not a flat card. Two octaves of mottle plus a
    # slight vertical flow, so the mask reads as flowed liquid resin.
    noise = Image.new("L", (max(2, W // 8), max(2, H // 8)))
    nr = noise.load()
    for j in range(noise.height):
        for i in range(noise.width):
            nr[i, j] = 128 + rng.randint(-26, 26)
    noise = noise.resize((W, H), Image.BICUBIC).filter(
        ImageFilter.GaussianBlur(3))
    fine = Image.new("L", (W, H))
    fr = fine.load()
    for j in range(H):
        for i in range(W):
            fr[i, j] = 128 + rng.randint(-40, 40)
    fine = fine.filter(ImageFilter.GaussianBlur(0.6))
    albedo = Image.composite(
        Image.new("RGB", (W, H), MASK_GREEN_D), albedo,
        noise.point(lambda v: max(0, min(255, int((v - 128) * 1.4 + 128)))))
    albedo = Image.blend(albedo, Image.composite(
        Image.new("RGB", (W, H), (30, 96, 56)), albedo, fine), 0.22)
    da = ImageDraw.Draw(albedo)

    # ---- ground pour: every real board has one, and it is what makes
    # the mask read as a LAYER rather than paint. Inset from the edge,
    # drawn a touch lighter than the bare mask, with a hatched fill so
    # the copper shows through the resin.
    px0, py0 = T(x0 + 2.0, y0 + 2.0)
    px1, py1 = T(x1 - 2.0, y1 - 2.0)
    da.rounded_rectangle([px0, py0, px1, py1], radius=int(1.6 * mm),
                         fill=(20, 72, 40))
    hatch = Image.new("L", (W, H), 0)
    dh = ImageDraw.Draw(hatch)
    step = int(1.2 * mm)
    for k in range(-H, W, step * 2):
        dh.line([(k, 0), (k + H, H)], fill=70, width=1)
    pour_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(pour_mask).rounded_rectangle(
        [px0, py0, px1, py1], radius=int(1.6 * mm), fill=255)
    albedo = Image.composite(
        Image.new("RGB", (W, H), (26, 88, 48)), albedo,
        Image.composite(hatch, Image.new("L", (W, H), 0), pour_mask))
    da = ImageDraw.Draw(albedo)

    # ---- collect pads by family
    sws, diodes, others = [], [], []
    for p in placements:
        ref = p["ref"]
        if ref.startswith(("SW_L", "SW_R")) and ref[4:5].isdigit():
            sws.append(p)
        elif ref.startswith(("D_L", "D_R")) and ref[2:3].isdigit():
            diodes.append(p)
        else:
            others.append(p)

    def sw_pads(p):
        """Kailh choc hotswap: two plated slots, 5.5 mm apart across the
        switch centre, plus the two 1.7 mm post holes."""
        x, y = p["x"], p["y"]
        a = math.radians(p.get("rot", 0.0))
        ca, sa = math.cos(a), math.sin(a)
        out = []
        for dx, dy in ((-2.75, 0.0), (2.75, 0.0)):
            out.append((x + dx * ca - dy * sa, y + dx * sa + dy * ca))
        return out

    # ---- copper: switch -> diode, then diode buses down each column
    # to the controller, plus per-row runs. All in board mm.
    traces = []          # (pts, width_mm)

    def nearest_diode(p):
        best, bd = None, 1e9
        for q in diodes:
            d = (q["x"] - p["x"]) ** 2 + (q["y"] - p["y"]) ** 2
            if d < bd:
                best, bd = q, d
        return best

    # ---- buses first: one horizontal row run per key row, one vertical
    # column run per key column. These are the long haul; the short
    # stubs below join the pads to them.
    rows = {}
    for p in sws:
        rows.setdefault(round(p["y"]), []).append(p)
    for ry, group in rows.items():
        group = sorted(group, key=lambda p: p["x"])
        lane = ry + 6.4 + rng.uniform(-0.4, 0.4)
        for p in group:
            q = nearest_diode(p)
            if q is None:
                continue
            traces.append((route_path((q["x"] + 1.2, q["y"]), (q["x"] + 1.2, lane),
                                      rng, 0.45), 0.34))
            traces.append(([(group[0]["x"] - 2.0, lane),
                        (group[-1]["x"] + 4.0, lane)], 0.34))

    cols = {}
    for p in sws:
        cols.setdefault(round(p["x"] / 19.0), []).append(p)
    for ck, group in cols.items():
        lane_x = min(p["x"] for p in group) - 3.4 + rng.uniform(-0.3, 0.3)
        ys = [p["y"] for p in group]
        traces.append(([(lane_x, min(ys) - 3.0), (lane_x, max(ys) + 3.0)], 0.34))
        for p in group:
            q = nearest_diode(p)
            if q is None:
                continue
            traces.append((route_path((q["x"], q["y"] - 0.9), (lane_x, q["y"] - 0.9),
                                      rng, 0.5), 0.30))

    # ---- switch -> diode stub and pad-to-pad matrix runs
    for p in sws:
        pads = sw_pads(p)
        q = nearest_diode(p)
        if q is None:
            continue
        traces.append((route_path(pads[0], (q["x"] - 0.8, q["y"]), rng, 0.55),
                       0.30))
        traces.append((route_path(pads[1], (pads[1][0], p["y"] + 6.0), rng, 0.5),
                       0.28))

    # controller fan-out: a real fan of traces from the MCU pads into
    # the column buses, on both sides of the module
    mcu = next((p for p in others if p["ref"].startswith("U_")), None)
    if mcu is not None:
        for i in range(24):
            sgn = -1 if i % 2 else 1
            px_ = mcu["x"] + sgn * 6.35
            py_ = mcu["y"] - 13.97 + (i // 2) * 2.54
            end = (px_ + sgn * (6.0 + (i % 7) * 3.2),
                   py_ - 4.0 - (i % 5) * 2.6)
            traces.append((route_path((px_, py_), end, rng, 0.55), 0.30))

    # jack / encoder runs
    enc = next((p for p in others if p["ref"].startswith("ENC_")), None)
    jacks = [p for p in others if p["ref"].startswith("J_")]
    if mcu is not None:
        for j in jacks:
            traces.append((route_path((mcu["x"], mcu["y"]),
                                      (j["x"], j["y"]), rng, 0.5), 0.22))
        if enc is not None:
            traces.append((route_path((mcu["x"], mcu["y"]),
                                      (enc["x"], enc["y"]), rng, 0.5), 0.22))
            traces.append((route_path((enc["x"] - 4, enc["y"] + 4),
                                      (enc["x"] - 12, 40.0), rng, 0.5), 0.20))

    # draw copper UNDER the mask: traces are mask-covered copper, so
    # they are drawn on the metal map but get the dull copper ink on
    # the albedo
    for pts, w in traces:
        _line(dm, pts, mm, w, 255, origin)
        _line(da, pts, mm, w, COPPER, origin)
    dm = ImageDraw.Draw(metal)
    da = ImageDraw.Draw(albedo)

    # ---- pads (exposed): drawn last, with a mask-opening ring
    for p in sws:
        for (px_, py_) in sw_pads(p):
            _pad(da, px_, py_, 2.6, 1.7, mm, COPPER_EXPOSED, origin)
            _pad(dm, px_, py_, 2.6, 1.7, mm, 255, origin)
        # post holes punched through everything
        for dy in (-5.5, 5.5):
            hx, hy = p["x"] - origin[0], p["y"] - origin[1] + dy
            da.ellipse([(hx - 0.95) * mm, (hy - 0.95) * mm,
                        (hx + 0.95) * mm, (hy + 0.95) * mm],
                       fill=(230, 230, 228))

    for q in diodes:
        for dx in (-1.35, 1.35):
            _pad(da, q["x"] + dx, q["y"], 1.5, 1.5, mm, COPPER_EXPOSED, origin)
            _pad(dm, q["x"] + dx, q["y"], 1.5, 1.5, mm, 255, origin)

    if mcu is not None:
        for sgn in (-1, 1):
            for i in range(12):
                px_ = mcu["x"] + sgn * 6.35
                py_ = mcu["y"] - 13.97 + i * 2.54
                _pad(da, px_, py_, 1.9, 1.5, mm, COPPER_EXPOSED, origin)
                _pad(dm, px_, py_, 1.9, 1.5, mm, 255, origin)

    for j in jacks:
        for i in range(4):
            _pad(da, j["x"] + 2.5, j["y"] - 3.0 + i * 2.0, 1.6, 1.2, mm,
                 COPPER_EXPOSED, origin)
            _pad(dm, j["x"] + 2.5, j["y"] - 3.0 + i * 2.0, 1.6, 1.2, mm, 255,
                 origin)

    if enc is not None:
        for i in range(3):
            _pad(da, enc["x"] - 4.3, enc["y"] - 2.5 + i * 2.5, 1.6, 1.4, mm,
                 COPPER_EXPOSED, origin)
            _pad(dm, enc["x"] - 4.3, enc["y"] - 2.5 + i * 2.5, 1.6, 1.4, mm,
                 255, origin)
        _pad(da, enc["x"], enc["y"], 2.0, 2.0, mm, COPPER_EXPOSED, origin)
        _pad(dm, enc["x"], enc["y"], 2.0, 2.0, mm, 255, origin)

    # mounting holes + fiducials
    for p in others:
        if p["ref"].startswith("MT_"):
            r = 1.6
            hx, hy = p["x"] - origin[0], p["y"] - origin[1]
            da.ellipse([(hx - r) * mm, (hy - r) * mm,
                        (hx + r) * mm, (hy + r) * mm], fill=(228, 228, 226))
            da.ellipse([(hx - r + 0.18) * mm, (hy - r + 0.18) * mm,
                        (hx + r - 0.18) * mm, (hy + r - 0.18) * mm],
                       fill=MASK_GREEN_D)
        if p["ref"].startswith("FID_"):
            _pad(da, p["x"], p["y"], 1.0, 1.0, mm, COPPER_EXPOSED, origin,
                 round_=True)
            _pad(dm, p["x"], p["y"], 1.0, 1.0, mm, 255, origin, round_=True)

    # ---- vias, scattered along the routes
    for i in range(70):
        t, w = traces[rng.randrange(len(traces))]
        seg = rng.randrange(len(t) - 1)
        f = rng.random()
        x = t[seg][0] + (t[seg + 1][0] - t[seg][0]) * f
        y = t[seg][1] + (t[seg + 1][1] - t[seg][1]) * f
        if x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1:
            vmask = Image.new("L", (W, H), 0)
            _via(ImageDraw.Draw(vmask), x, y, mm, 255, ring=0, org=origin)
            albedo.paste(COPPER_EXPOSED, (0, 0), vmask)
            metal.paste(255, (0, 0), vmask)
        if i % 9 == 0:
            _via(ImageDraw.Draw(metal), x, y, mm, 90, ring=40, org=origin)

    # ---- silkscreen: switch outlines, diode bars, refs, logo
    f_small = _font(max(9, int(1.05 * mm)))
    f_tiny = _font(max(8, int(0.85 * mm)))
    f_logo = _font(max(14, int(2.4 * mm)))
    for p in sws:
        x, y = T(p["x"], p["y"])
        s = 5.0 * mm
        ds.rounded_rectangle([x - s / 2, y - s / 2, x + s / 2, y + s / 2],
                             radius=int(0.6 * mm), outline=220, width=max(1, int(0.16 * mm)))
        ds.text((x - s / 2 + 2, y + s / 2 - 1.5 * mm), p["ref"],
                font=f_tiny, fill=190)
    for q in diodes:
        x, y = T(q["x"], q["y"])
        ds.rectangle([x - 1.6 * mm, y - 0.9 * mm, x + 1.6 * mm, y + 0.9 * mm],
                     outline=200, width=max(1, int(0.14 * mm)))
        ds.line([x - 1.6 * mm, y - 0.9 * mm, x + 1.6 * mm, y + 0.9 * mm],
                fill=200, width=1)
    if mcu is not None:
        x, y = T(mcu["x"], mcu["y"])
        ds.rectangle([x - 7.2 * mm, y - 15.5 * mm, x + 7.2 * mm, y + 15.5 * mm],
                     outline=230, width=max(1, int(0.18 * mm)))
        ds.text((x - 6.5 * mm, y + 16.4 * mm), "nice!nano v2",
                font=f_small, fill=235)
        ds.text((x - 6.5 * mm, y - 17.8 * mm), "U1", font=f_small, fill=235)
    if enc is not None:
        x, y = T(enc["x"], enc["y"])
        r = 4.2 * mm
        ds.ellipse([x - r, y - r, x + r, y + r], outline=225,
                   width=max(1, int(0.18 * mm)))
        ds.text((x - 3.4 * mm, y + r + 2), "ENC1", font=f_tiny, fill=225)
    for j in jacks:
        x, y = T(j["x"], j["y"])
        ds.rectangle([x - 2.4 * mm, y - 4.6 * mm, x + 2.4 * mm, y + 4.6 * mm],
                     outline=225, width=max(1, int(0.16 * mm)))
    if silk_text:
        x, y = T(x0 + (x1 - x0) * 0.30, y0 + 3.2)
        ds.text((x, y), "HOJICHA44", font=f_logo, fill=235)
        ds.text((x + 2, y + 3.2 * mm), "REV A  ML-04",
                font=f_small, fill=200)

    # composite silk onto the albedo (silk is printed OVER the mask)
    albedo.paste((228, 229, 222), (0, 0), silk)

    os.makedirs(outdir, exist_ok=True)
    a_path = os.path.join(outdir, f"{prefix}_albedo.png")
    m_path = os.path.join(outdir, f"{prefix}_metal.png")
    albedo.save(a_path)
    metal.save(m_path)
    return a_path, m_path


def build_art_for_side(side, placements_all, bbox, outdir, **kw):
    pl = placements_all[side]
    return build_art(pl, bbox, outdir,
                     seed=44 if side == "Left" else 71,
                     prefix="pcb" if side == "Left" else "pcbr", **kw)


def main(argv):
    """CLI: pcb_tex.py <bbox.json> <outdir>

    Blender's bundled Python has no PIL, so the artwork is generated by
    the system interpreter before/while the scene builds. bbox.json is
    {"Left": [[x0,z0],[x1,z1]], ...} written by the render scene.
    """
    import json
    import sys
    bbox_path, outdir = argv[0], argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    pl = json.load(open(os.path.join(root, "generated", "renders", "assets",
                                     "placements.json")))
    boxes = json.load(open(bbox_path))
    made = []
    for side in ("Left", "Right"):
        bb = boxes.get(side) or boxes.get("Left")
        flat = (bb[0][0], bb[0][1], bb[1][0], bb[1][1])
        made.append(build_art_for_side(side, pl, flat, outdir))
    return made


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

"""Hojicha44 render scene — Blender 5.2 headless.

Run:
  blender --background --python renders/scene.py -- \
      --samples 64 --res 1600x1000 --setups dark,bright \
      --shots hero,exploded,macro,orbit

Assembly (all in the committed storage frame, scaled to Blender meters):
  board GLBs at z −1.60 (substrate top lands on the case datum z=0)
  plates at z +1.00 (underside = the GAP plane)
  keycaps dropped onto each switch (skirt = plate top + CAP_LIFT)
  knobs on the encoder shafts (6mm engagement)
  tubs under, covers above (cover lifted for the exploded shot)

Materials are assigned by node-name rules from the converted PCB GLBs and
the part names. Everything is derived from committed artifacts only.
"""
import bpy
import sys
import math
import json
import os
import argparse

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(REPO, "generated", "renders", "assets")
OUTROOT = os.path.join(REPO, "generated", "renders", "v0.5.0")

SCALE = 0.001          # storage-frame mm -> Blender meters
PCB_TOP_IN_STEP = 1.60  # substrate top inside the kicad-cli STEP (measured)
PLATE_Z = 1.00          # plate underside above the PCB top (GAP)
CAP_STEM_Z = 1.5        # cap stem-bottom inside the switch body (above the
                        # PCB top); KLP skirt then wraps the housing and the
                        # cap top lands flush under the cover plane (7.67 vs
                        # cover 7.70)
KNOB_ENGAGE = 6.0       # knob body engages the shaft this deep
SPLIT_GAP = 8.0         # tub-to-tub gap in the assembled shot
EXPLODE = {"cover": 26.0, "plate": 12.0, "caps": 30.0, "knob": 16.0}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--res", default="1600x1000")
    p.add_argument("--setups", default="dark,bright")
    p.add_argument("--shots", default="hero,exploded,macro,orbit")
    p.add_argument("--out", default=OUTROOT)
    p.add_argument("--device", default="metal", choices=["metal", "cpu"])
    p.add_argument("--palette", action="store_true",
                   help="garish debug colors to verify assignments")
    p.add_argument("--hide-cover", action="store_true")
    p.add_argument("--hide-case", action="store_true")
    p.add_argument("--hide-plate", action="store_true")
    return p.parse_args(argv)


def import_glb(path, prefix):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in objs if o.parent is None or o.parent not in objs]
    grp = bpy.data.collections.new(prefix)
    bpy.context.scene.collection.children.link(grp)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        grp.objects.link(o)
        o.scale = (SCALE, SCALE, SCALE)
    # Blender's glTF importer converts Y-up -> Z-up by rotating +90 deg
    # about X (measured: our storage (x, y, z) landed at (x, -z, y)).
    # Counter-rotate the roots by -90 deg about X so the world returns to
    # the storage frame. NOTE: imported objects use rotation_mode
    # QUATERNION, where rotation_euler writes are silently ignored —
    # switch the mode first or the fix does nothing.
    for r in roots:
        r.rotation_mode = "XYZ"
        r.rotation_euler.x -= math.pi / 2
    return grp, roots, objs


def import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    grp = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(grp)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        grp.objects.link(o)
        o.name = name
        o.data.name = name
        o.scale = (SCALE, SCALE, SCALE)
    return grp, objs


def bbox_mm(objs):
    import mathutils
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            pts.append(o.matrix_world @ mathutils.Vector(corner))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def pbr(name, color, rough=0.5, metal=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    return mat


def assign(objs, mat):
    for o in objs:
        if o.type != "MESH":
            continue
        o.data.materials.clear()
        o.data.materials.append(mat)


def materialize_pcb(objs):
    """name/z-based rules over the converted board nodes."""
    m_sub = pbr("pcb_substrate", (0.016, 0.020, 0.017), rough=0.42)
    m_cu = pbr("pcb_copper", (0.72, 0.58, 0.20), rough=0.28, metal=1.0)
    m_silk = pbr("pcb_silk", (0.87, 0.87, 0.84), rough=0.5)
    m_comp = pbr("pcb_component", (0.05, 0.05, 0.055), rough=0.35)
    m_diode = pbr("pcb_diode", (0.08, 0.08, 0.09), rough=0.2)
    for o in objs:
        if o.type != "MESH":
            continue
        (x0, y0, z0), (x1, y1, z1) = bbox_mm([o])
        span = z1 - z0
        name = o.name
        if name.startswith("D_"):
            assign([o], m_diode)
        elif name.startswith(("ENC_", "J_", "SW_")):
            assign([o], m_comp)
        elif span > 0.9 and len(o.data.polygons) > 15000:
            # the two big copper layer meshes
            assign([o], m_cu)
        elif span > 0.9:
            assign([o], m_sub)
        elif z0 > 0.5:
            assign([o], m_silk)
        else:
            assign([o], m_sub)


def setup_world_and_lights(setup):
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    for o in list(bpy.data.objects):
        if o.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(o, do_unlink=True)
    if setup == "dark":
        bg.inputs[0].default_value = (0.004, 0.004, 0.005, 1)
        key = bpy.data.lights.new("key", "AREA")
        key.energy = 140; key.size = 0.35
        ko = bpy.data.objects.new("key", key)
        ko.location = (-0.18, -0.22, 0.28)
        ko.rotation_euler = (math.radians(38), 0, math.radians(-35))
        fill = bpy.data.lights.new("fill", "AREA")
        fill.energy = 40; fill.size = 0.6; fill.color = (0.7, 0.8, 1.0)
        fo = bpy.data.objects.new("fill", fill)
        fo.location = (0.30, -0.10, 0.12)
        rim = bpy.data.lights.new("rim", "AREA")
        rim.energy = 80; rim.size = 0.25
        ro = bpy.data.objects.new("rim", rim)
        ro.location = (0.05, 0.30, 0.22)
        for o in (ko, fo, ro):
            bpy.context.collection.objects.link(o)
    else:
        bg.inputs[0].default_value = (0.85, 0.87, 0.90, 1)
        key = bpy.data.lights.new("key", "AREA")
        key.energy = 250; key.size = 0.8
        ko = bpy.data.objects.new("key", key)
        ko.location = (0.0, -0.35, 0.45)
        ko.rotation_euler = (math.radians(25), 0, 0)
        bpy.context.collection.objects.link(ko)


def add_cam(name, loc, look_at, lens=50):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    co = bpy.data.objects.new(name, cam)
    co.location = loc
    import mathutils
    direction = mathutils.Vector(look_at) - mathutils.Vector(loc)
    co.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(co)
    return co


def render_to(cam, path, res, samples, device="metal"):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    if device == "metal":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
        except Exception as e:
            print("  (GPU setup unavailable, CPU render):", e)
    else:
        sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    print(f"  rendering {os.path.basename(path)} ...", flush=True)
    bpy.ops.render.render(write_still=True)
    print("  wrote", path, flush=True)


def main():
    args = parse_args()
    res = tuple(int(v) for v in args.res.split("x"))
    os.makedirs(args.out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    print("[scene] empty scene ready", flush=True)
    sc = bpy.context.scene

    parts = {}
    for half in ("Left", "Right"):
        h = half[0]
        parts[h] = {}
        _, roots, objs = import_glb(os.path.join(ASSETS, "board",
                                                 f"Hojicha44-{half}.glb"),
                                    f"board_{h}")
        for o in roots:
            o.location.z -= PCB_TOP_IN_STEP * SCALE
        parts[h]["board"] = objs
        print(f"[scene] {half}: board imported ({len(objs)} objs)", flush=True)
        _, roots, objs = import_glb(os.path.join(ASSETS, "plate",
                                                 f"Hojicha44-{half}.glb"),
                                    f"plate_{h}")
        for o in roots:
            o.location.z += PLATE_Z * SCALE
        parts[h]["plate"] = objs
        for part in ("tub", "cover"):
            _, roots, objs = import_glb(os.path.join(
                ASSETS, "case", f"Hojicha44-{half}-{part}.glb"), f"{part}_{h}")
            parts[h][part] = objs

        materialize_pcb(parts[h]["board"])
        print(f"[scene] {half}: pcb materials assigned", flush=True)
        if args.palette:
            assign(parts[h]["plate"], pbr(f"dbg_plate_{h}", (0.1, 0.7, 0.2),
                                          rough=0.4))
            assign(parts[h]["tub"], pbr(f"dbg_tub_{h}", (0.2, 0.3, 0.9),
                                        rough=0.5))
            assign(parts[h]["cover"], pbr(f"dbg_cover_{h}", (0.9, 0.7, 0.1),
                                          rough=0.5))
        else:
            assign(parts[h]["plate"], pbr("plate_pc", (0.05, 0.05, 0.06),
                                          rough=0.35))
            assign(parts[h]["tub"], pbr("case_pa12", (0.045, 0.047, 0.05),
                                        rough=0.62))
            assign(parts[h]["cover"], pbr("case_pa12", (0.045, 0.047, 0.05),
                                          rough=0.62))

        # keycaps + knobs from the placements file
        pl = json.load(open(os.path.join(ASSETS, "placements.json")))[half]
        switches = [p for p in pl if p["ref"].startswith("SW_")]
        ys = sorted(set(p["y"] for p in switches))
        # classify: 3 finger rows (most common y bands) + thumb row
        from collections import Counter
        band = Counter(p["y"] for p in switches)
        finger_ys = [y for y, n in band.items() if n >= 5]
        thumb = [p for p in switches if p["y"] not in finger_ys]
        finger = [p for p in switches if p["y"] in finger_ys]
        finger.sort(key=lambda p: p["y"])
        rows = None  # v1: uniform variant mapping below; homing later
        row_ids = {}
        for i, y in enumerate(sorted(finger_ys)):
            row_ids[y] = i  # 0 = storage-frame lowest y
        m_caps = pbr("cap_pbt", (0.030, 0.030, 0.032), rough=0.45)
        m_cap_home = pbr("cap_pbt_home", (0.10, 0.10, 0.11), rough=0.45)
        if args.palette:
            m_caps = pbr(f"dbg_cap_{h}", (0.9, 0.1, 0.1), rough=0.45)
            m_cap_home = m_caps
        for p in finger + thumb:
            variant = "thumb" if p in thumb else (
                "saddle" if row_ids[p["y"]] == 1 else "saddle_tilted")
            _, roots_c, objs = import_glb(os.path.join(
                ASSETS, "parts", f"klp_{variant}.glb"), f"cap_{p['ref']}")
            assign(objs, m_caps)
            parts[h].setdefault("caps", []).extend(objs)
            for o in roots_c:
                o.location.x += p["x"] * SCALE
                o.location.y += p["y"] * SCALE
                o.rotation_euler.z += math.radians(p["rot"])
            # the KLP origin is not the cap's geometric centre — place by
            # bbox centre so every cap registers with its switch cutout
            (cx0, cy0, _), (cx1, cy1, _) = bbox_mm(objs)
            for o in roots_c:
                o.location.x += p["x"] * SCALE - (cx0 + cx1) / 2
                o.location.y += p["y"] * SCALE - (cy0 + cy1) / 2
        # drop caps so the stem bottom sits inside the switch body
        for o in parts[h]["caps"]:
            (x0, y0, z0), _ = bbox_mm([o])
            o.location.z += CAP_STEM_Z * SCALE - z0

        # knob(s) — encoder top measured from the imported board geometry
        enc_objs = [o for o in parts[h]["board"] if "ENC" in o.name]
        encs = [p for p in pl if "ENC" in p["ref"] or "EC11" in p["ref"]]
        enc_top = None
        if enc_objs:
            (_, _, _), (_, _, ez1) = bbox_mm(enc_objs)
            enc_top = ez1  # meters, already offset by the board z correction
        for p in encs:
            _, roots_k, objs = import_glb(os.path.join(ASSETS, "parts",
                                                       "knob.glb"),
                                          f"knob_{p['ref']}")
            assign(objs, pbr("knob_alu", (0.55, 0.56, 0.58), rough=0.35,
                             metal=1.0))
            parts[h].setdefault("knobs", []).extend(objs)
            knob_base = ((enc_top if enc_top is not None
                          else (24.54 * SCALE)) - KNOB_ENGAGE * SCALE)
            for o in roots_k:
                o.location.x += p["x"] * SCALE
                o.location.y += p["y"] * SCALE
                o.rotation_euler.z += math.radians(p["rot"])
                o.location.z += knob_base

    # position the right half next to the left with the split gap
    (lx0, _, _), (lx1, _, _) = bbox_mm(parts["L"]["tub"])
    (rx0, _, _), (_, _, _) = bbox_mm(parts["R"]["tub"])
    dx = (lx1 + SPLIT_GAP * SCALE) - rx0
    for o in parts["R"]["board"] + parts["R"]["plate"] + \
            parts["R"]["tub"] + parts["R"]["cover"] + \
            parts["R"].get("caps", []) + parts["R"].get("knobs", []):
        o.location.x += dx

    all_objs = [o for h in parts for lst in parts[h].values()
                for o in (lst if isinstance(lst, list) else [])]
    # ---- diagnostics: where did every group actually land?
    for h in parts:
        for grp in ("board", "plate", "tub", "cover", "caps", "knobs"):
            objs = parts[h].get(grp, [])
            if not objs:
                print(f"[diag] {h}/{grp}: EMPTY", flush=True)
                continue
            (x0, y0, z0), (x1, y1, z1) = bbox_mm(objs)
            hidden = sum(1 for o in objs if o.hide_render)
            print(f"[diag] {h}/{grp}: x {x0*1000:.1f}..{x1*1000:.1f} "
                  f"y {y0*1000:.1f}..{y1*1000:.1f} z {z0*1000:.2f}..{z1*1000:.2f} "
                  f"n={len(objs)} hidden={hidden}", flush=True)
    if args.hide_cover:
        for h in parts:
            for o in parts[h]["cover"]:
                o.hide_render = True
    if args.hide_case:
        for h in parts:
            for o in parts[h]["tub"] + parts[h]["cover"]:
                o.hide_render = True

    # render queue
    (bx0, by0, bz0), (bx1, by1, bz1) = bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    setups = args.setups.split(",")
    shots = args.shots.split(",")
    for setup in setups:
        setup_world_and_lights(setup)
        sdir = os.path.join(args.out, setup)
        os.makedirs(sdir, exist_ok=True)
        if "hero" in shots:
            cam = add_cam("hero", (cx - 0.22, cy - 0.30, 0.26), (cx, cy, 0.0),
                          lens=50)
            render_to(cam, os.path.join(sdir, "hero.png"), res, args.samples,
                      args.device)
        if "exploded" in shots:
            for grp, dz in (("cover", EXPLODE["cover"]),
                            ("plate", EXPLODE["plate"]),
                            ("caps", EXPLODE["caps"]),
                            ("knobs", EXPLODE["knob"])):
                for h in parts:
                    for o in parts[h].get(grp, []):
                        o.location.z += dz * SCALE
            cam = add_cam("exploded", (cx - 0.12, cy - 0.46, 0.36),
                          (cx, cy, 0.05), lens=50)
            render_to(cam, os.path.join(sdir, "exploded.png"), res,
                      args.samples, args.device)
            for grp, dz in (("cover", EXPLODE["cover"]),
                            ("plate", EXPLODE["plate"]),
                            ("caps", EXPLODE["caps"]),
                            ("knobs", EXPLODE["knob"])):
                for h in parts:
                    for o in parts[h].get(grp, []):
                        o.location.z -= dz * SCALE
        if "macro" in shots:
            # encoder + knob closeup (left half)
            enc = [p for p in json.load(open(os.path.join(
                ASSETS, "placements.json")))["Left"]
                if "ENC" in p["ref"] or "EC11" in p["ref"]]
            if enc:
                ex, ey = enc[0]["x"] * SCALE, enc[0]["y"] * SCALE
                cam = add_cam("macro_enc", (ex - 0.05, ey - 0.05, 0.10),
                              (ex, ey, 0.02), lens=85)
                render_to(cam, os.path.join(sdir, "macro_encoder.png"), res,
                          args.samples, args.device)
            cam = add_cam("macro_keys", (cx - 0.05, cy - 0.09, 0.055),
                          (cx - 0.01, cy - 0.02, 0.004), lens=85)
            render_to(cam, os.path.join(sdir, "macro_keys.png"), res,
                      args.samples, args.device)
        if "orbit" in shots:
            for i in range(12):
                a = 2 * math.pi * i / 12
                cam = add_cam(f"orbit{i}", (cx + 0.20 * math.cos(a),
                                            cy - 0.20 * math.sin(a), 0.16),
                              (cx, cy, 0.0), lens=50)
                render_to(cam, os.path.join(sdir, f"orbit_{i:02d}.png"), res,
                          args.samples, args.device)
        if "top" in shots:
            cam = add_cam("top", (cx, cy - 0.001, 0.45), (cx, cy, 0.0),
                          lens=60)
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = 0.36
            render_to(cam, os.path.join(sdir, "top.png"), res, args.samples,
                      args.device)
    print("SCENE-DONE")


main()

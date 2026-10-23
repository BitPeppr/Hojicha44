"""Hojicha44 render scene — Blender 5.2 headless.

Run:
  blender --background --python renders/scene.py -- \
      --samples 96 --res 1600x1000 --setups bright --shots hero,exploded

FRAME — everything is assembled in the **design frame** (x right, y up),
the frame of the committed plate DXF, the case STLs and the board STEP
export. KiCad stores the .kicad_pcb y-down; kicad-cli's STEP export
negates y (measured: Edge.Cuts y -60.00..54.63 -> glb y -54.63..60.00),
so board GLBs and the plate/case already share the design frame.
placements.json is converted (y -> -y); cutouts.json is a raw
transcription of the plate DXF.

REGISTRATION MASTER — the plate CUTOUT holes. The scene matches every
switch footprint to a plate hole and ABORTS if any is off by > 0.05 mm.
The caps, switch bodies and thumb rotations all come from the matched
hole (center + polygon angle), never from a separately-computed origin.

STACK (z=0 is the PCB top):
  PCB substrate           -1.60..0        (STEP top 1.60 shifted down)
  plate                    1.00..2.20
  switch body              0.30..3.30, cap stem tip 1.50
  flat KLP Saddle top      7.58           (cover bezel plane 7.70)
  cover ring               4.70..7.70
  knob (10 mm) seats on the bushing, top just above the 24.54 shaft

The assembled halves are used at their committed positions — the case
files already place them in one shared layout; no artificial split gap.
"""
import bpy
import sys
import math
import json
import os
import re
import argparse

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(REPO, "generated", "renders", "assets")
OUTROOT = os.path.join(REPO, "generated", "renders", "v0.5.0")

SCALE = 0.001            # design-frame mm -> Blender meters
PCB_TOP_IN_STEP = 1.60   # substrate top inside the kicad-cli STEP
PLATE_Z = 1.00           # plate underside above the PCB top (GAP)
CAP_STEM_Z = 1.5         # cap stem tip above the PCB top (inside switch)
KNOB_TOP_CLEAR = 0.1     # knob top sits 0.1 mm above the shaft top, so the
                         # 10 mm knob seats on the encoder bushing (top 14.5)
# exploded view: keep the tub/PCB/switch stack, lift the top layers apart
EXPLODE = {"cover": 46.0, "caps": 26.0, "plate": 14.0, "knobs": 12.0}
# nice!nano courtyard in the FOOTPRINT's local (file) frame, from the
# embedded Socket_Strips_2x12_P2.54mm_NiceNano footprint (KiCad 10)
NANO_COURT = (-17.07, -29.94, 2.85, 2.60)   # x0, y0, x1, y1


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
    # about X (measured: our design (x, y, z) lands at (x, -z, y)).
    # Counter-rotate the roots by -90 deg about X so the world returns to
    # the design frame. NOTE: imported objects use rotation_mode
    # QUATERNION, where rotation_euler writes are silently ignored.
    for r in roots:
        r.rotation_mode = "XYZ"
        r.rotation_euler.x -= math.pi / 2
    # setting scale/rotation does not refresh matrix_world; every bbox
    # measurement below depends on an evaluated transform
    bpy.context.view_layer.update()
    return grp, roots, objs


def bbox_mm(objs):
    import mathutils
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            pts.append(o.matrix_world @ mathutils.Vector(corner))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def pbr(name, color, rough=0.5, metal=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat


def assign(objs, mat):
    for o in objs:
        if o.type != "MESH":
            continue
        o.data.materials.clear()
        o.data.materials.append(mat)


def mesh_area_span(o):
    """Surface area (mm^2) and world-z thickness (mm) of one board layer
    solid. The glTF stores design millimetres as raw vertex units (object
    scale 0.001 turns them into metres), so the area is directly
    comparable to the STEP. NOTE: the mesh data stays Y-up (the importer
    rotates the object), so design thickness = world z span, not local z."""
    import mathutils
    area = sum(p.area for p in o.data.polygons)
    zs = [(o.matrix_world @ mathutils.Vector(c)).z for c in o.bound_box]
    return area, (max(zs) - min(zs)) * 1000.0


def materialize_pcb(objs):
    """Assign PCB materials by measured layer geometry, not by guesswork.

    kicad-cli emits the board as anonymous layer solids. Measured on the
    committed board: substrate 27.8k mm^2; top/bottom copper pours
    12.6k/12.4k on planes; silkscreen 206/63 mm^2 on planes; pad/via
    copper 1.5k/1.5k/211 mm^2 through the board thickness. The pours are
    rendered as black soldermask (their real appearance), the pad copper
    as ENIG gold, the sparse planes as white silk.
    """
    m_sub = pbr("pcb_substrate", (0.016, 0.026, 0.021), rough=0.45)
    m_mask = pbr("pcb_soldermask", (0.010, 0.010, 0.012), rough=0.32)
    m_cu = pbr("pcb_copper", (0.76, 0.60, 0.22), rough=0.26, metal=1.0)
    m_silk = pbr("pcb_silk", (0.86, 0.86, 0.83), rough=0.55)
    m_comp = pbr("pcb_component", (0.045, 0.045, 0.050), rough=0.35)
    m_diode = pbr("pcb_diode", (0.020, 0.020, 0.022), rough=0.25)
    census = {}
    for o in objs:
        if o.type != "MESH":
            continue
        name = o.name
        if name.startswith("D_"):
            mat = m_diode
        elif name.startswith(("ENC_", "J_", "SW_")):
            mat = m_comp
        else:
            area, span = mesh_area_span(o)
            if area > 20000:
                mat = m_sub
            elif span < 0.2:
                # plane: the large pours are the soldermask, the sparse
                # ~50-200 mm^2 planes are silkscreen
                mat = m_mask if area > 5000 else m_silk
            else:
                mat = m_cu
            print(f"  [pcb] {name}: area {area:.1f} mm2, thickness "
                  f"{span:.3f} mm -> {mat.name}", flush=True)
        assign([o], mat)
        census[mat.name] = census.get(mat.name, 0) + 1
    print("  [pcb] material census:", census, flush=True)


def fp_to_design(ax, ay, rot_deg, lx, ly):
    """Footprint-local (KiCad file frame) -> design frame."""
    r = math.radians(rot_deg)
    c, s = math.cos(r), math.sin(r)
    return (ax + c * lx - s * ly, -(ay + s * lx + c * ly))


def smooth(objs, angle_deg=35.0):
    """Smooth shading for curved parts. Imported custom split normals are
    cleared first: the glTF exporter writes per-face normals from OCCT's
    split vertices, and those would override any smoothing we ask for."""
    meshes = [o for o in objs if o.type == "MESH"]
    if not meshes:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    for o in meshes:
        if o.data.has_custom_normals:
            bpy.context.view_layer.objects.active = o
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.shade_smooth()
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg),
                                             keep_sharp_edges=True)
    except (AttributeError, TypeError):
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle_deg))


def move_z(objs, dz):
    """Lift a group once (roots only, in case the importer nested nodes)."""
    for o in objs:
        if o.parent is None:
            o.location.z += dz


def add_cube(name, loc, size, mat, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] * SCALE, size[1] * SCALE, size[2] * SCALE)
    o.rotation_euler.z = math.radians(rot_z)
    assign([o], mat)
    return o


def setup_world_and_lights(setup, cx, cy):
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    if setup == "bright":
        bg_cam.inputs[0].default_value = (0.86, 0.88, 0.91, 1.0)
        bg_cam.inputs[1].default_value = 1.0
        # reflections/ambient: a bright studio wall the metal knob can see
        bg_amb.inputs[0].default_value = (0.80, 0.84, 0.90, 1.0)
        bg_amb.inputs[1].default_value = 0.40
    else:
        bg_cam.inputs[0].default_value = (0.004, 0.004, 0.005, 1.0)
        bg_cam.inputs[1].default_value = 1.0
        bg_amb.inputs[0].default_value = (0.05, 0.07, 0.12, 1.0)
        bg_amb.inputs[1].default_value = 0.05
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_amb.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])

    for o in list(bpy.data.objects):
        if o.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(o, do_unlink=True)
    import mathutils

    def area(name, energy, size, loc, target, color=(1, 1, 1)):
        li = bpy.data.lights.new(name, "AREA")
        li.energy = energy
        li.size = size
        li.color = color
        o = bpy.data.objects.new(name, li)
        o.location = loc
        d = mathutils.Vector(target) - mathutils.Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(o)

    if setup == "bright":
        area("key", 3, 1.0, (cx - 0.16, cy - 0.26, 0.40), (cx, cy, 0.0))
        area("fill", 0.8, 1.0, (cx + 0.34, cy - 0.16, 0.18),
             (cx, cy, 0.0), (0.82, 0.90, 1.0))
        area("rim", 2, 0.5, (cx + 0.02, cy + 0.34, 0.30), (cx, cy, 0.0))
        area("rim2", 0.6, 0.5, (cx - 0.36, cy + 0.18, 0.24), (cx, cy, 0.0))
    else:
        area("key", 55, 0.4, (cx - 0.18, cy - 0.24, 0.30), (cx, cy, 0.0))
        area("fill", 15, 0.6, (cx + 0.30, cy - 0.10, 0.12),
             (cx, cy, 0.0), (0.70, 0.80, 1.0))
        area("rim", 26, 0.25, (cx + 0.05, cy + 0.30, 0.22), (cx, cy, 0.0))


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
    sc.render.film_transparent = False
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
    # AgX + strong lights lifts near-black albedos toward white — use a
    # Standard transform so assigned colors render as authored
    sc = bpy.context.scene
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0

    placements = json.load(open(os.path.join(ASSETS, "placements.json")))
    cutouts = json.load(open(os.path.join(ASSETS, "cutouts.json")))

    m_cap = pbr("cap_pbt", (0.032, 0.031, 0.034), rough=0.44)
    m_sw = pbr("switch_body", (0.026, 0.026, 0.030), rough=0.38)
    m_knob = pbr("knob_alu", (0.58, 0.59, 0.61), rough=0.30, metal=1.0)
    m_nano = pbr("nano_pcb", (0.012, 0.055, 0.032), rough=0.42)
    m_chip = pbr("nano_chip", (0.020, 0.020, 0.023), rough=0.30)
    m_usb = pbr("usb_shell", (0.62, 0.63, 0.65), rough=0.28, metal=1.0)
    m_sock = pbr("nano_socket", (0.028, 0.028, 0.030), rough=0.45)

    parts = {}
    for half in ("Left", "Right"):
        h = half[0]
        parts[h] = {}
        _, roots, objs = import_glb(os.path.join(
            ASSETS, "board", f"Hojicha44-{half}.glb"), f"board_{h}")
        for o in roots:
            o.location.z -= PCB_TOP_IN_STEP * SCALE
        bpy.context.view_layer.update()
        parts[h]["board"] = objs
        print(f"[scene] {half}: board imported ({len(objs)} objs)", flush=True)
        _, roots, objs = import_glb(os.path.join(
            ASSETS, "plate", f"Hojicha44-{half}.glb"), f"plate_{h}")
        for o in roots:
            o.location.z += PLATE_Z * SCALE
        bpy.context.view_layer.update()
        parts[h]["plate"] = objs
        for part in ("tub", "cover"):
            _, roots, objs = import_glb(os.path.join(
                ASSETS, "case", f"Hojicha44-{half}-{part}.glb"),
                f"{part}_{h}")
            parts[h][part] = objs

        materialize_pcb(parts[h]["board"])
        if args.palette:
            assign(parts[h]["plate"], pbr(f"dbg_plate_{h}",
                                          (0.1, 0.7, 0.2), rough=0.4))
            assign(parts[h]["tub"], pbr(f"dbg_tub_{h}",
                                        (0.2, 0.3, 0.9), rough=0.5))
            assign(parts[h]["cover"], pbr(f"dbg_cover_{h}",
                                          (0.9, 0.7, 0.1), rough=0.5))
        else:
            assign(parts[h]["plate"], pbr("plate_pc", (0.050, 0.050, 0.055),
                                          rough=0.36))
            assign(parts[h]["tub"], pbr("case_pa12", (0.042, 0.044, 0.048),
                                        rough=0.60))
            assign(parts[h]["cover"], pbr("case_pa12",
                                          (0.042, 0.044, 0.048), rough=0.60))

        # ---- registration: plate holes are the physical master
        pl = placements[half]
        cuts = cutouts[half]
        sw = [p for p in pl if re.fullmatch(r"SW_[LR]\d\d", p["ref"])]
        holes = {}
        worst = 0.0
        for p in sw:
            c = min(cuts, key=lambda c: (c["x"] - p["x"]) ** 2
                    + (c["y"] - p["y"]) ** 2)
            d = math.hypot(c["x"] - p["x"], c["y"] - p["y"])
            worst = max(worst, d)
            holes[p["ref"]] = c
        if len(sw) != 22 or worst > 0.05:
            sys.exit(f"[scene] ABORT {half}: registration {worst:.3f} mm "
                     f"over {len(sw)} switches")
        # every switch hole must also be hit exactly once (no shared holes)
        used = {(c["x"], c["y"]) for c in holes.values()}
        if len(used) != 22:
            sys.exit(f"[scene] ABORT {half}: {len(used)} distinct holes "
                     "for 22 switch footprints")
        print(f"[scene] {half}: REGISTRATION 22/22 switch footprints on "
              f"plate holes, worst {worst:.4f} mm", flush=True)

        # ---- cap variant map: thumbs by position, homing on the index
        # home key. The index column is the tallest stagger column (F/J:
        # left home row A S D F G [ — the 4th key from the outer edge).
        cols = {}
        for p in sw:
            if p["y"] < -10.0:
                continue
            cols.setdefault(round(p["x"], 1), []).append(p)
        if len(cols) != 6:
            sys.exit(f"[scene] ABORT {half}: {len(cols)} finger columns")
        index_x = max(cols, key=lambda x: max(q["y"] for q in cols[x]))
        home = sorted(cols[index_x], key=lambda q: q["y"])[1]
        print(f"[scene] {half}: index column x={index_x:.1f}, "
              f"homing key ({home['x']:.1f},{home['y']:.1f})", flush=True)

        # ---- caps (KLP Lamé; flat Saddle profile stays under the bezel)
        for p in sw:
            c = holes[p["ref"]]
            if p["y"] < -10.0:
                variant = "thumb"
            elif (abs(p["x"] - home["x"]) < 1e-6
                  and abs(p["y"] - home["y"]) < 1e-6):
                variant = "saddle_homing"
            else:
                variant = "saddle"
            _, roots_c, objs = import_glb(os.path.join(
                ASSETS, "parts", f"klp_{variant}.glb"),
                f"cap_{h}_{p['ref']}")
            assign(objs, m_cap)
            parts[h].setdefault("caps", []).extend(objs)
            for o in roots_c:
                o.rotation_euler.z += math.radians(c["angle"])
            bpy.context.view_layer.update()
            # the KLP origin is not the cap's geometric centre — place by
            # bbox centre so every cap registers with its plate hole
            (cx0, cy0, z0), (cx1, cy1, _) = bbox_mm(objs)
            for o in roots_c:
                o.location.x += c["x"] * SCALE - (cx0 + cx1) / 2
                o.location.y += c["y"] * SCALE - (cy0 + cy1) / 2
                o.location.z += CAP_STEM_Z * SCALE - z0
            bpy.context.view_layer.update()

        # ---- switch housings visible between plate and cap skirt
        for p in sw:
            c = holes[p["ref"]]
            o = add_cube(f"swbody_{h}_{p['ref']}",
                         (c["x"] * SCALE, c["y"] * SCALE, 1.80 * SCALE),
                         (13.6, 13.6, 3.0), m_sw, c["angle"])
            parts[h].setdefault("swbodies", []).append(o)

        # ---- nice!nano v2 stand-in (the VRML model kicad-cli skips),
        # dimensioned from the committed footprint courtyard
        nanos = [p for p in pl if p["ref"].startswith("U_")]
        big = [c for c in cuts if c["w"] > 27 and c["h"] > 55]
        for p in nanos:
            x0, y0, x1, y1 = NANO_COURT
            corners = [fp_to_design(p["x_file"], p["y_file"], p["rot"], lx, ly)
                       for lx in (x0, x1) for ly in (y0, y1)]
            nx0 = min(q[0] for q in corners)
            nx1 = max(q[0] for q in corners)
            ny0 = min(q[1] for q in corners)
            ny1 = max(q[1] for q in corners)
            ncx, ncy = (nx0 + nx1) / 2, (ny0 + ny1) / 2
            if big:
                w = big[0]
                if not (w["x"] - w["w"] / 2 <= nx0 and nx1 <= w["x"] + w["w"] / 2
                        and w["y"] - w["h"] / 2 <= ny0
                        and ny1 <= w["y"] + w["h"] / 2):
                    sys.exit(f"[scene] ABORT {half}: nano courtyard "
                             f"({nx0:.2f}..{nx1:.2f},{ny0:.2f}..{ny1:.2f}) "
                             f"outside MCU window ({w['x']},{w['y']})")
                print(f"[scene] {half}: nano bbox x {nx0:.2f}..{nx1:.2f} "
                      f"y {ny0:.2f}..{ny1:.2f} inside MCU window", flush=True)
            body_y = 33.0            # nice!nano v2 body (module PCB)
            body_x = 17.8
            z_pcb0 = 3.0             # socket stack under the module PCB
            z_pcb1 = z_pcb0 + 1.6
            g = parts[h].setdefault("nano", [])
            g.append(add_cube(f"nano_pcb_{h}",
                              (ncx * SCALE, ncy * SCALE,
                               ((z_pcb0 + z_pcb1) / 2) * SCALE),
                              (body_x, body_y, 1.6), m_nano))
            # USB-C receptacle at the north (+y) end, on the module top
            g.append(add_cube(f"nano_usb_{h}",
                              (ncx * SCALE, (ncy + body_y / 2 - 3.7) * SCALE,
                               (z_pcb1 + 1.5) * SCALE),
                              (9.0, 7.4, 3.0), m_usb))
            # nRF52840 + antenna keepout sit on top of the module
            g.append(add_cube(f"nano_mcu_{h}",
                              (ncx * SCALE, (ncy + 2.0) * SCALE,
                               (z_pcb1 + 0.45) * SCALE),
                              (5.5, 5.5, 0.9), m_chip))
            g.append(add_cube(f"nano_ant_{h}",
                              (ncx * SCALE, (ncy - 14.0) * SCALE,
                               (z_pcb1 + 0.25) * SCALE),
                              (3.0, 2.0, 0.5), m_chip))
            # two low-profile socket strips under the module
            for sgn in (-1, 1):
                g.append(add_cube(f"nano_sock_{h}_{sgn}",
                                  ((ncx + sgn * 7.62) * SCALE, ncy * SCALE,
                                   1.5 * SCALE),
                                  (2.6, 29.0, 3.0), m_sock))

        # ---- knob on the encoder shaft (measured encoder top)
        enc_objs = [o for o in parts[h]["board"]
                    if o.name.startswith("ENC")]
        enc_top = None
        bpy.context.view_layer.update()
        if enc_objs:
            enc_top = bbox_mm(enc_objs)[1][2]
        wins = [c for c in cuts if 15.5 <= c["w"] <= 16.9
                and 11.5 <= c["h"] <= 13.3]
        for win in wins:
            _, roots_k, objs = import_glb(os.path.join(
                ASSETS, "parts", "knob.glb"),
                f"knob_{h}_{win['x']}")
            assign(objs, m_knob)
            parts[h].setdefault("knobs", []).extend(objs)
            (_, _, kz0), (_, _, kz1) = bbox_mm(objs)
            knob_h = kz1 - kz0
            base = ((enc_top - knob_h + KNOB_TOP_CLEAR * SCALE)
                    if enc_top is not None
                    else (14.54 + KNOB_TOP_CLEAR) * SCALE)
            for o in roots_k:
                o.location.x += win["x"] * SCALE
                o.location.y += win["y"] * SCALE
                o.location.z += base - kz0
            print(f"[scene] {half}: knob at ({win['x']:.2f},{win['y']:.2f}) "
                  f"base {base*1000:.2f} mm, knob {knob_h*1000:.2f} mm, "
                  f"encoder top {enc_top*1000:.2f}", flush=True)

    # ---- smooth curved parts (welded glbs make this effective)
    for h in parts:
        smooth(parts[h].get("caps", []), 35.0)
        smooth(parts[h].get("knobs", []), 35.0)

    all_objs = [o for h in parts for lst in parts[h].values()
                for o in (lst if isinstance(lst, list) else [])]
    # ---- diagnostics: where every group actually landed
    bpy.context.view_layer.update()
    for h in parts:
        for grp in ("board", "plate", "tub", "cover", "caps", "knobs",
                    "swbodies", "nano"):
            objs = parts[h].get(grp, [])
            if not objs:
                print(f"[diag] {h}/{grp}: EMPTY", flush=True)
                continue
            (x0, y0, z0), (x1, y1, z1) = bbox_mm(objs)
            hidden = sum(1 for o in objs if o.hide_render)
            print(f"[diag] {h}/{grp}: x {x0*1000:.1f}..{x1*1000:.1f} "
                  f"y {y0*1000:.1f}..{y1*1000:.1f} "
                  f"z {z0*1000:.2f}..{z1*1000:.2f} n={len(objs)} "
                  f"hidden={hidden}", flush=True)
    # the committed case places the halves in one layout: report the true
    # tub seam instead of inventing a split gap
    (_, _, _), (lx1, _, _) = bbox_mm(parts["L"]["tub"])
    (rx0, _, _), (_, _, _) = bbox_mm(parts["R"]["tub"])
    print(f"[diag] tub seam (design): {(rx0-lx1)*1000:.2f} mm", flush=True)
    if args.hide_cover:
        for h in parts:
            for o in parts[h]["cover"]:
                o.hide_render = True
    if args.hide_case:
        for h in parts:
            for o in parts[h]["tub"] + parts[h]["cover"]:
                o.hide_render = True
    if args.hide_plate:
        for h in parts:
            for o in parts[h]["plate"]:
                o.hide_render = True

    # ---- render queue
    (bx0, by0, bz0), (bx1, by1, bz1) = bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    print(f"[scene] assembly centre ({cx*1000:.1f},{cy*1000:.1f}) mm",
          flush=True)
    setups = args.setups.split(",")
    shots = args.shots.split(",")
    for setup in setups:
        setup_world_and_lights(setup, cx, cy)
        sdir = os.path.join(args.out, setup)
        os.makedirs(sdir, exist_ok=True)
        if "hero" in shots:
            cam = add_cam("hero", (cx - 0.24, cy - 0.44, 0.30),
                          (cx, cy, 0.004), lens=50)
            render_to(cam, os.path.join(sdir, "hero.png"), res,
                      args.samples, args.device)
        if "exploded" in shots:
            for grp, dz in EXPLODE.items():
                for h in parts:
                    move_z(parts[h].get(grp, []), dz * SCALE)
            cam = add_cam("exploded", (cx - 0.10, cy - 0.52, 0.47),
                          (cx, cy, 0.055), lens=50)
            render_to(cam, os.path.join(sdir, "exploded.png"), res,
                      args.samples, args.device)
            for grp, dz in EXPLODE.items():
                for h in parts:
                    move_z(parts[h].get(grp, []), -dz * SCALE)
        if "macro" in shots:
            enc = [p for p in placements["Left"] if p["ref"].startswith("ENC")]
            if enc:
                ex, ey = enc[0]["x"] * SCALE, enc[0]["y"] * SCALE
                cam = add_cam("macro_enc", (ex - 0.05, ey - 0.06, 0.12),
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
            cam = add_cam("top", (cx, cy - 0.0001, 0.50), (cx, cy, 0.0),
                          lens=60)
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = 0.40
            render_to(cam, os.path.join(sdir, "top.png"), res, args.samples,
                      args.device)
    print("SCENE-DONE")


main()

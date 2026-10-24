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

STACK (z=0 is the PCB top; thin-top round):
  PCB substrate           -1.60..0        (STEP top 1.60 shifted down)
  bottom gaskets          -1.55..1.00     (3.0 poron compressed to 2.55)
  plate                    1.00..2.20
  switch body              0.30..3.30, cap stem tip 1.50
  top gaskets              2.20..3.20     (1.5 poron compressed to 1.00)
  KLP Normal_Tilted top    11.14          (~5.9 mm proud of the cover;
                                           thumbs wear the same family)
  top cover plate          3.20..5.20     (flat, no-indent; 0.4 chamfer
                                           on the outer-rim top edges)
  encoder = short-shaft EC11-class (tip 13.5, two-tone) under a low
  fluted alu knob (OD 16.8, H 9.2, crown ~15.3, skirt rim+0.9 so the
  0.8mm max push travel can never hit the cover)

COLOURWAY (round 4: "make it less bland"): warm-bone satin PBT caps,
mid-grey matte PLA case, near-black waxy POM plate, machined-metal knob
and encoder, gold traces on the nice!nano.

POSE (round 4): for the product shots the halves are parented to an
empty on each outer bottom edge, then pushed 7 mm apart, splayed 4 deg
in plan and tented 5 deg — the classic Sofle/Corne wing presentation.
Pure render transform; the case files build the assembled layout.
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
# exploded view: keep the tub/PCB/switch stack, lift the top layers apart
EXPLODE = {"cover": 40.0, "caps": 26.0, "plate": 14.0, "gaskets": 14.0}
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
    p.add_argument("--no-floor", action="store_true",
                   help="omit the studio floor (debug/compare)")
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


def micro_texture(mat, scale, bump, dist, rough_lo=None, rough_hi=None,
                  detail=3.5):
    """Procedural surface texture in generated (per-object 0..1) space.

    One noise drives a bump normal plus an optional roughness range. The
    rendered board is ~3 px/mm, so the scale is chosen for features that
    read at that size (0.5-3 mm), not for powder-grain detail. Idempotent:
    materials are shared between halves, so repeated calls are no-ops.
    """
    if mat.get("micro_texture"):
        return mat
    mat["micro_texture"] = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(tc.outputs["Generated"], noise.inputs["Vector"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    bmp.inputs["Distance"].default_value = dist
    nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    if rough_lo is not None and rough_hi is not None:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 1.0
        mr.inputs["To Min"].default_value = rough_lo
        mr.inputs["To Max"].default_value = rough_hi
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
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
    # fine soldermask / substrate / silk grain; metal pads get only a
    # slight roughness break-up so the ENIG stays specular
    micro_texture(m_sub, 120, 0.25, 0.00006, 0.42, 0.50)
    micro_texture(m_mask, 180, 0.20, 0.00004, 0.28, 0.38)
    micro_texture(m_cu, 300, 0.10, 0.00002, 0.22, 0.30)
    micro_texture(m_silk, 300, 0.20, 0.00003, 0.50, 0.60)
    micro_texture(m_comp, 100, 0.15, 0.00004, 0.32, 0.40)
    micro_texture(m_diode, 200, 0.10, 0.00002, 0.22, 0.28)
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
        # reflections/ambient: a bright studio wall the metal parts can see
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
    lands = {h: json.load(open(os.path.join(
        REPO, "plate", f"Hojicha44-{h}-lands.json")))
        for h in ("Left", "Right")}

    m_cap = pbr("cap_pbt", (0.55, 0.525, 0.475), rough=0.42)  # warm bone
    m_sw = pbr("switch_body", (0.026, 0.026, 0.030), rough=0.38)
    m_nano = pbr("nano_pcb", (0.010, 0.010, 0.012), rough=0.42)   # black mask
    m_chip = pbr("nano_chip", (0.020, 0.020, 0.023), rough=0.30)
    m_usb = pbr("usb_shell", (0.62, 0.63, 0.65), rough=0.28, metal=1.0)
    m_sock = pbr("nano_socket", (0.028, 0.028, 0.030), rough=0.45)
    m_gold = pbr("nano_castel", (0.83, 0.68, 0.28), rough=0.30, metal=1.0)
    m_silk = pbr("nano_silk", (0.80, 0.80, 0.77), rough=0.55)
    m_poron = pbr("poron_pad", (0.40, 0.38, 0.36), rough=0.93)
    micro_texture(m_poron, 90, 0.5, 0.001, 0.88, 0.97, detail=3.0)
    # colourway hierarchy (user review 2026-10-24: keycap lighter than
    # case, case lighter than plate, plate glossier than the matte PLA
    # case — a POM/PP plate against a printed PLA shell):
    #   caps   = warm bone, satin fine grain     (lightest)
    #   case   = mid grey, coarse sintered grain  (middle)
    #   plate  = near-black waxy POM gloss        (darkest, smoothest)
    m_case = pbr("case_pla", (0.30, 0.30, 0.315), rough=0.62)
    m_plate = pbr("plate_pom", (0.035, 0.036, 0.042), rough=0.14)
    m_knob = pbr("knob_alu", (0.72, 0.73, 0.75), rough=0.26, metal=1.0)
    m_enc_body = pbr("enc_gunmetal", (0.16, 0.16, 0.175),
                     rough=0.30, metal=0.9)
    m_enc_shaft = pbr("enc_steel", (0.66, 0.67, 0.70), rough=0.20, metal=1.0)
    # texture pass: PBT caps a FINE satin grain, the PLA case a clearly
    # coarser grain, the POM plate almost none (waxy gloss), the knob and
    # encoder read as machined metal
    micro_texture(m_cap, 42, 0.28, 0.00022, 0.36, 0.48, detail=5.0)
    micro_texture(m_sw, 40, 0.20, 0.00004, 0.34, 0.42)
    micro_texture(m_nano, 60, 0.15, 0.00003, 0.38, 0.48)
    micro_texture(m_chip, 120, 0.10, 0.00002, 0.28, 0.34)
    micro_texture(m_usb, 200, 0.10, 0.00002, 0.24, 0.32)
    micro_texture(m_sock, 50, 0.15, 0.00003, 0.42, 0.50)
    micro_texture(m_case, 85, 0.40, 0.00055, 0.52, 0.68, detail=5.0)
    micro_texture(m_plate, 240, 0.10, 0.00002, 0.11, 0.17)
    micro_texture(m_knob, 300, 0.06, 0.000015, 0.22, 0.30)
    micro_texture(m_enc_body, 140, 0.18, 0.00004, 0.24, 0.34)
    micro_texture(m_enc_shaft, 260, 0.08, 0.00002, 0.16, 0.24)

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
            assign(parts[h]["plate"], m_plate)
            assign(parts[h]["tub"], m_case)
            assign(parts[h]["cover"], m_case)

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

        # ---- cap variant map: thumbs by position, homing on the INNER
        # index home key (G/H), one column inboard of the F/J stagger peak.
        cols = {}
        for p in sw:
            if p["y"] < -10.0:
                continue
            cols.setdefault(round(p["x"], 1), []).append(p)
        if len(cols) != 6:
            sys.exit(f"[scene] ABORT {half}: {len(cols)} finger columns")
        peak_x = max(cols, key=lambda x: max(q["y"] for q in cols[x]))
        inboard = [x for x in cols
                   if (x > peak_x if half == "Left" else x < peak_x)]
        index_x = max(inboard, key=lambda x: max(q["y"] for q in cols[x]))
        home = sorted(cols[index_x], key=lambda q: q["y"])[1]
        print(f"[scene] {half}: inner index column x={index_x:.1f}, "
              f"homing key ({home['x']:.1f},{home['y']:.1f})", flush=True)

        # ---- caps (KLP Lamé; user review: the flat Saddle field read
        # as "basically inline with case" — switch to the TALL Tilted
        # family, cap tops ~11.1mm abs, ~5.9mm proud of the cover.
        # Round 4 review: the four THUMBS wore the low KLP "Thumb"
        # profile and read as sunken below the rim ("case seems taller
        # than the keys, hard to press inside the case holes") — the
        # KLP families share the foot, so thumbs now wear the same tall
        # Normal_Tilted as the fingers (Sofle/Lily/Corne thumb clusters
        # sit at full cap height too). The tilted family has no homing
        # variant; homing keys wear the same cap.
        for p in sw:
            c = holes[p["ref"]]
            variant = "normal_tilted"
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

        # ---- poron gaskets on every tab, compressed to the real
        # assembly heights (bottom 3.0 -> 2.55, top 1.5 -> 1.28). They
        # stick to the plate tabs, so the explode lifts them with the
        # plate; the pad centre is the tab root + 2.0mm outward (the
        # same rule plate/gen_plate.py uses for the PORON DXF layer).
        for t in lands[half]["tabs"]:
            a = math.radians(t["angle"])
            px = t["x"] + math.cos(a) * 2.0
            py = t["y"] + math.sin(a) * 2.0
            o = add_cube(f"gsk_b_{h}_{t['x']:.0f}_{t['y']:.0f}",
                         (px * SCALE, py * SCALE, -0.275 * SCALE),
                         (4.0, 7.0, 2.55), m_poron, t["angle"])
            parts[h].setdefault("gaskets", []).append(o)
            o = add_cube(f"gsk_t_{h}_{t['x']:.0f}_{t['y']:.0f}",
                         (px * SCALE, py * SCALE, 2.70 * SCALE),
                         (4.0, 7.0, 1.00), m_poron, t["angle"])
            parts[h].setdefault("gaskets", []).append(o)
        print(f"[scene] {half}: {len(lands[half]['tabs'])} tabs, top+bottom "
              f"gaskets at the compressed heights", flush=True)

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
            z_pcb0 = 4.5             # Mill-Max 315+3320 stack (spec BOM)
            z_pcb1 = z_pcb0 + 1.6
            g = parts[h].setdefault("nano", [])
            g.append(add_cube(f"nano_pcb_{h}",
                              (ncx * SCALE, ncy * SCALE,
                               ((z_pcb0 + z_pcb1) / 2) * SCALE),
                              (body_x, body_y, 1.6), m_nano))
            # gold castellated pads: 12 per long edge at 2.54mm pitch
            # (the 2x12 socket pin field), not one continuous strip
            for sgn in (-1, 1):
                for i in range(12):
                    g.append(add_cube(
                        f"nano_pad_{h}_{sgn}_{i}",
                        ((ncx + sgn * (body_x / 2 - 0.45)) * SCALE,
                         (ncy + (i - 5.5) * 2.54) * SCALE,
                         ((z_pcb0 + z_pcb1) / 2) * SCALE),
                        (0.9, 1.7, 1.75), m_gold))
            # copper runs: from each pad inward with a deterministic
            # length + jog, plus scattered vias — the board reads as
            # wired, not printed
            tr = 0.25
            for sgn in (-1, 1):
                for i in range(12):
                    y_off = (i - 5.5) * 2.54
                    L = 2.0 + ((i * 37 + (sgn > 0) * 13) % 53) / 10.0
                    g.append(add_cube(
                        f"nano_tr_{h}_{sgn}_{i}",
                        ((ncx + sgn * (body_x / 2 - 0.9 - L / 2)) * SCALE,
                         (ncy + y_off) * SCALE, (z_pcb1 + 0.02) * SCALE),
                        (L, tr, 0.04), m_gold))
                    if i % 3 == 1:
                        jl = 1.5 + (i % 4) * 0.9
                        g.append(add_cube(
                            f"nano_tj_{h}_{sgn}_{i}",
                            ((ncx + sgn * (body_x / 2 - 0.9 - L)) * SCALE,
                             (ncy + y_off + sgn * jl / 2) * SCALE,
                             (z_pcb1 + 0.02) * SCALE),
                            (tr, jl, 0.04), m_gold))
            for k in range(10):
                vx = ((k * 71) % 130) / 10.0 - 6.5
                vy = ((k * 53) % 240) / 10.0 - 12.0
                g.append(add_cube(
                    f"nano_via_{h}_{k}",
                    ((ncx + vx) * SCALE, (ncy + vy) * SCALE,
                     (z_pcb1 + 0.015) * SCALE),
                    (0.4, 0.4, 0.03), m_gold))
            # silkscreen text (Blender font, lies flat on the mask)
            for tname, tbody, ty, tsize in (
                    ("nice!nano v2", "nice!nano v2", -10.6, 2.2),
                    ("hojicha44", "hojicha44", -5.4, 1.5)):
                crv = bpy.data.curves.new(f"nano_txt_{h}_{tname}",
                                          type="FONT")
                crv.body = tbody
                crv.size = tsize * SCALE
                crv.extrude = 0.02 * SCALE
                crv.align_x = "CENTER"
                tob = bpy.data.objects.new(f"nano_txt_{h}_{ty}", crv)
                tob.location = (ncx * SCALE, (ncy + ty) * SCALE,
                                (z_pcb1 + 0.05) * SCALE)
                tob.rotation_euler = (0, 0, 0)
                bpy.context.collection.objects.link(tob)
                assign([tob], m_silk)
                g.append(tob)
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
            # crystal (silver) + a passives field around the QFN
            g.append(add_cube(f"nano_xtal_{h}",
                              ((ncx - 4.8) * SCALE, (ncy + 7.5) * SCALE,
                               (z_pcb1 + 0.45) * SCALE),
                              (3.2, 2.5, 0.9), m_usb))
            for k in range(8):
                px = ((k * 47) % 90) / 10.0 - 4.5
                py = 2.0 + ((k * 31) % 60) / 10.0 - 1.5
                g.append(add_cube(
                    f"nano_pas_{h}_{k}",
                    ((ncx + px) * SCALE, (ncy + py) * SCALE,
                     (z_pcb1 + 0.11) * SCALE),
                    (0.6, 0.3, 0.22), m_chip))
            # reset pushbutton (top-east corner) + status LED (top-west)
            g.append(add_cube(f"nano_rst_{h}",
                              ((ncx + 6.5) * SCALE, (ncy + 13.4) * SCALE,
                               (z_pcb1 + 0.7) * SCALE),
                              (2.4, 2.6, 1.4), m_sock))
            g.append(add_cube(f"nano_led_{h}",
                              ((ncx - 5.6) * SCALE, (ncy + 13.4) * SCALE,
                               (z_pcb1 + 0.25) * SCALE),
                              (1.6, 1.0, 0.5), m_gold))
            # two low-profile socket strips under the module (the 315
            # bodies; the 3320 pins rise into the module)
            for sgn in (-1, 1):
                g.append(add_cube(f"nano_sock_{h}_{sgn}",
                                  ((ncx + sgn * 7.62) * SCALE, ncy * SCALE,
                                   1.3 * SCALE),
                                  (2.6, 29.0, 2.6), m_sock))

        # ---- EC11: short-shaft EC11-class variant (BOM primary) under a
        # low fluted knob. The board GLB carries the vendored 20mm-class
        # ALPS STEP as one mesh: (a) truncate the shaft at 13.5mm above
        # the board — the low-profile class the Sofle Choc build guide
        # documents ("prefer short shaft... 10mm D-shaped shaft") and the
        # KLOTZ/MKUltra knob aesthetic (a 2-3mm stem above the bush);
        # (b) split body/bush from shaft at the 11.3 step plane for a
        # two-tone finish (gunmetal body, bright steel shaft). The knob
        # then covers everything above the rim — no bare shaft shows.
        enc_objs = [o for o in parts[h]["board"]
                    if o.type == "MESH" and o.name.startswith("ENC_")]
        if enc_objs:
            import bmesh
            ENC_SPLIT_Z, ENC_SHAFT_TOP_Z = 11.35, 13.5
            for o in enc_objs:
                # round-4 debug: the board glb keeps its -90 deg X
                # counter-rotation (and the 0.001 scale) ON THE OBJECT,
                # so raw mesh-local z is NOT design z (it is design y!)
                # -- the first truncation silently matched nothing and
                # the full 24.5mm shaft kept rendering. All selection is
                # therefore done in world design metres via matrix_world;
                # the mesh itself stays untouched in its local frame.
                mw = o.matrix_world.copy()
                bm = bmesh.new()
                me_body = o.data.copy()
                bm.from_mesh(me_body)
                dz = {v: (mw @ v.co).z for v in bm.verts}
                top = ENC_SHAFT_TOP_Z * SCALE
                drop = [v for v in bm.verts if dz[v] > top]
                n_trunc = len(drop)
                if drop:
                    bmesh.ops.delete(bm, geom=drop, context="VERTS")
                    bmesh.ops.holes_fill(
                        bm, edges=[e for e in bm.edges
                                   if len(e.link_faces) == 1], sides=0)
                split = ENC_SPLIT_Z * SCALE
                bm_body, bm_shaft = bmesh.new(), bmesh.new()
                vmap_body, vmap_shaft = {}, {}
                for f in bm.faces:
                    fz = [dz[v] for v in f.verts]
                    if min(fz) >= split - 1e-9:
                        tgt, vmap = bm_shaft, vmap_shaft
                    else:
                        tgt, vmap = bm_body, vmap_body
                    vs = []
                    for v in f.verts:
                        nv = vmap.get(v)
                        if nv is None:
                            nv = vmap[v] = tgt.verts.new(v.co)
                        vs.append(nv)
                    try:
                        tgt.faces.new(vs)
                    except ValueError:
                        pass
                bm.free()
                bm_body.to_mesh(me_body)
                bm_body.free()
                me_body.update()
                o.data = me_body
                assign([o], m_enc_body)
                if len(vmap_shaft):
                    me_shaft = bpy.data.meshes.new(o.name + "_shaft")
                    bm_shaft.to_mesh(me_shaft)
                    bm_shaft.free()
                    so = bpy.data.objects.new(o.name + "_shaft", me_shaft)
                    # inherit the body's full local transform + parent so
                    # the local-frame shaft mesh lands exactly on it
                    so.parent = o.parent
                    so.matrix_basis = o.matrix_basis.copy()
                    so.rotation_mode = o.rotation_mode
                    bpy.context.collection.objects.link(so)
                    bpy.context.view_layer.update()
                    assign([so], m_enc_shaft)
                    parts[h]["board"].append(so)
                print(f"  [enc] {o.name}: truncated {n_trunc} verts "
                      f"(top {ENC_SHAFT_TOP_Z}mm), shaft faces "
                      f"{len(vmap_shaft)}", flush=True)
            # ---- low fluted knob on the short shaft (user review round 4:
            # "add a knob to it, not too tall, not too thin, not toooo
            # fat"). parts/knob.glb: OD 16.8, H 9.2, 18 grip ridges, a
            # lighter machined-aluminium finish. The skirt bottom lands
            # rim+0.9 = 6.1 abs (push-travel clearance), the crown
            # reaches ~15.3 — just above the 11.14 cap tops. Placed on
            # each truncated shaft's axis.
            bpy.context.view_layer.update()
            for o in list(parts[h]["board"]):
                if o.type == "MESH" and o.name.endswith("_shaft"):
                    (kx0, ky0, _), (kx1, ky1, _) = bbox_mm([o])
                    _, knob_roots, knob_objs = import_glb(
                        os.path.join(ASSETS, "parts", "knob.glb"),
                        f"knob_{h}")
                    for ko in knob_roots:
                        # skirt bottom = rim 5.2 + push travel 0.8 (EC11
                        # push is 0.5 +/- 0.3) + 0.1: the skirt must
                        # NEVER hit the cover when the knob is pressed
                        ko.location = ((kx0 + kx1) / 2,
                                       (ky0 + ky1) / 2,
                                       6.1 * SCALE)
                    assign(knob_objs, m_knob)
                    parts[h].setdefault("knob", []).extend(knob_objs)
            print(f"[scene] {half}: encoder truncated to {ENC_SHAFT_TOP_Z}mm "
                  f"+ two-tone metal split + low fluted knob "
                  f"(short-shaft EC11-class BOM variant)", flush=True)

    # ---- smooth curved parts (welded glbs make this effective)
    for h in parts:
        smooth(parts[h].get("caps", []), 35.0)

    all_objs = [o for h in parts for lst in parts[h].values()
                for o in (lst if isinstance(lst, list) else [])]
    # ---- diagnostics: where every group actually landed
    bpy.context.view_layer.update()
    for h in parts:
        for grp in ("board", "plate", "tub", "cover", "caps",
                    "swbodies", "nano", "gaskets", "knob"):
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

    # ---- presentation pose (user review round 4: "two halves slightly
    # further apart, maybe even slightly angled away from each other"):
    # every object of a half is parented to an empty sitting on its
    # OUTER BOTTOM long edge, then the empty is splayed 4° in plan,
    # tented 5° about that edge (the hinge edge stays on the desk, so
    # nothing sinks below the floor) and pushed 7mm further out — the
    # classic Sofle/Corne product-shot wing. Pure render transform: the
    # committed case files still build the assembled 2.8mm-seam layout.
    # round-5 review: 7mm + 4 deg pushed the halves out of frame
    # ("can't see most of the left board") — halve the horizontal
    # spread, keep the tent (that is the "angled away" that reads)
    SPLAY_DEG, TENT_DEG, SPLIT_MM = 2.5, 5.0, 2.5
    for h, sgn in (("L", -1.0), ("R", 1.0)):
        half_objs = [o for lst in parts[h].values()
                     for o in (lst if isinstance(lst, list) else [])]
        (hx0, hy0, hz0), (hx1, hy1, _) = bbox_mm(parts[h]["tub"])
        pe = bpy.data.objects.new(f"pose_{h}", None)
        pe.empty_display_size = 0.02
        bpy.context.collection.objects.link(pe)
        pe.location = ((hx0 if sgn < 0 else hx1), (hy0 + hy1) / 2, hz0)
        bpy.context.view_layer.update()
        # python parenting does NOT keep world transforms (no auto
        # parent-inverse like the UI operator) — without this every
        # child jumps by the pivot and the assembly lands ~2x out
        pe_inv = pe.matrix_world.inverted()
        for o in half_objs:
            o.parent = pe
            o.matrix_parent_inverse = pe_inv.copy()
        bpy.context.view_layer.update()
        # tent: +x edge lifts for the left half, -x edge for the right;
        # splay: far end swings outward (CCW left, CW right)
        pe.rotation_euler = (
            0.0,
            math.radians(TENT_DEG if sgn > 0 else -TENT_DEG),
            math.radians(SPLAY_DEG if sgn < 0 else -SPLAY_DEG))
        pe.location.x += sgn * SPLIT_MM * SCALE
        bpy.context.view_layer.update()
        print(f"[scene] pose {h}: splayed {SPLAY_DEG} deg, tented "
              f"{TENT_DEG} deg on the outer edge, split +{SPLIT_MM} mm",
              flush=True)

    # ---- render queue
    (bx0, by0, bz0), (bx1, by1, bz1) = bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    print(f"[scene] assembly centre ({cx*1000:.1f},{cy*1000:.1f}) mm",
          flush=True)

    # ---- studio floor: grounds the product and gives the soft key lights
    # a surface to draw a contact shadow on. Placed 0.2 mm under the tub
    # bottom; the 4 m plane fills the camera frame (no horizon visible).
    if not args.no_floor:
        bpy.ops.mesh.primitive_plane_add(
            size=4.0, location=(cx, cy, bz0 - 0.0002))
        floor = bpy.context.active_object
        floor.name = "studio_floor"
        m_floor = pbr("studio_floor", (0.40, 0.385, 0.365), rough=0.85)
        micro_texture(m_floor, 800, 0.60, 0.0008, 0.72, 0.90, detail=3.0)
        assign([floor], m_floor)
        print(f"[scene] floor at z {bz0*1000 - 0.2:.2f} mm", flush=True)

    setups = args.setups.split(",")
    shots = args.shots.split(",")
    for setup in setups:
        setup_world_and_lights(setup, cx, cy)
        sdir = os.path.join(args.out, setup)
        os.makedirs(sdir, exist_ok=True)
        if "hero" in shots:
            # review: slightly higher, looking down more (30.6 -> 34.5 deg)
            cam = add_cam("hero", (cx - 0.30, cy - 0.52, 0.40),
                          (cx, cy, 0.010), lens=50)
            render_to(cam, os.path.join(sdir, "hero.png"), res,
                      args.samples, args.device)
        if "exploded" in shots:
            for grp, dz in EXPLODE.items():
                for h in parts:
                    move_z(parts[h].get(grp, []), dz * SCALE)
            # review: slightly lower + flatter (38 -> 32 deg, 60mm lens)
            cam = add_cam("exploded", (cx - 0.12, cy - 0.624, 0.45),
                          (cx, cy, 0.055), lens=60)
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

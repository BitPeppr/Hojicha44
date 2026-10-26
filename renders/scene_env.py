"""Hojicha44 desk-environment shots — Blender 5.2 headless (rounds 7-8).

Two cameras over the SAME posed keyboard build_keyboard() assembles:

  desk  wide room view, WIRELESS story (round 8: no cables at all —
        the keyboard shows off its BLE nature): keyboard on its
        fabric desk mat, monitor behind, Mac mini, mouse, pen cup
        with pens, notebook + pen, ceramic mug with coffee, desk
        lamp (a real light in a real shade), walnut desk, plastered
        wall + baseboard
  mat   low closeup across the mat: the TRRS cable dressed between
        the halves (chunky plugs with strain boots, stiff wide U —
        round-7 review: "limp, almost like a thread, too thin"),
        the USB-C running back to the aluminium dock, shallow depth
        of field on the cable loop

The environment pose widens the split by an extra 200 mm so the cable
loop has room to read as a real cable (product shots keep the tight
pose); the halves sit ON the 3 mm mat, lifted by its thickness.

Round 8 texture pass: the mat is FABRIC now (crossed-thread weave
bump + fuzz noise + wash variation), the wall is mottled plaster
(two-scale noise colour + tooth), the walnut gained distortion and
deeper pores, and the props gained detail (monitor power LED, mini
front ports + debossed logo disc, mouse seam + scroll nub, cup rim,
dock right-angle connector).

Run:
  blender --background --python renders/scene_env.py -- \
      --samples 128 --res 2400x1500 --shots desk,mat
  ... add --framecheck for the NDC pre-flight (same maths as scene.py)

Reuses scene.py: init_scene, build_keyboard, pbr, micro_texture,
assign, bbox_mm, add_cam, render_to, frame_report. scene.py's
parse_args supplies the flags; the studio-only ones (setups/palette/
hide_*/stack-colors/no_floor) are ignored here.
"""
import bpy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S     # noqa: E402
import env_props as EP     # noqa: E402
import env_materials as EM   # noqa: E402

import mathutils

PROPS = []            # every visible env object
CABLES = []           # wires + their plugs: hidden for the desk shot


# ---------------------------------------------------------- env materials

def emit_mat(name, color, strength):
    """Principled with emission (socket renamed across Blender 4/5)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    for key in ("Emission", "Emission Color"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = (*color, 1.0)
            break
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def _noise(nt, scale, detail, name="n"):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.label = name
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    return nz


def proc_wood(name):
    """Oiled walnut: stretched wave bands + heavy distortion drive a
    colour ramp (grain along the desk's long axis), two-scale noise
    drives the pore bump and the roughness range (round 8: distortion
    7 -> 13, pores deeper, plus a broad tone-wash noise)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.35, 9.0, 1.0)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Distortion"].default_value = 13.0
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 1.4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.38, (0.092, 0.056, 0.031, 1.0)
    e[1].position, e[1].color = 0.64, (0.212, 0.133, 0.075, 1.0)
    nz = _noise(nt, 1100.0, 6.0, "pores")       # fine pores
    nz2 = _noise(nt, 5.0, 2.0, "wash")           # broad tone wash
    wash = nt.nodes.new("ShaderNodeValToRGB")
    we = wash.color_ramp.elements
    we[0].position, we[0].color = 0.35, (0.88, 0.86, 0.84, 1.0)
    we[1].position, we[1].color = 0.75, (1.06, 1.04, 1.00, 1.0)
    mix_col = nt.nodes.new("ShaderNodeMixRGB")
    # MULTIPLY, not blend: a 50/50 mix with grey doubled the desk's
    # brightness (round-8 calibration: mean 0.40 -> 0.53, 4.5% blown)
    mix_col.blend_type = "MULTIPLY"
    mix_col.inputs["Fac"].default_value = 1.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.20
    L = nt.links.new
    L(tc.outputs["Generated"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], wave.inputs["Vector"])
    L(wave.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], mix_col.inputs["Color1"])
    L(wash.outputs["Color"], mix_col.inputs["Color2"])
    L(nz2.outputs["Fac"], wash.inputs["Fac"])
    L(mix_col.outputs["Color"], bsdf.inputs["Base Color"])
    L(mp.outputs["Vector"], nz.inputs["Vector"])
    L(nz.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L(nz.outputs["Fac"], bsdf.inputs["Roughness"])   # placeholder, next:
    # map pore noise 0..1 -> roughness 0.30..0.46
    math1 = nt.nodes.new("ShaderNodeMath")
    math1.operation = "MULTIPLY"
    L(nz.outputs["Fac"], math1.inputs[0])
    math1.inputs[1].default_value = 0.16
    math2 = nt.nodes.new("ShaderNodeMath")
    math2.operation = "ADD"
    L(math1.outputs["Value"], math2.inputs[0])
    math2.inputs[1].default_value = 0.30
    L(math2.outputs["Value"], bsdf.inputs["Roughness"])
    return mat


def proc_weave(name, base=(0.045, 0.047, 0.054)):
    """Fabric desk mat (round 8 review: "desk mat should have fabric
    texture"): two crossed thread-scale wave bands form the weave bump,
    a fuzz noise softens it, a broad wash noise varies the colour, and
    the roughness rides the weave so the mat never reads flat."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp1 = nt.nodes.new("ShaderNodeMapping")
    mp1.inputs["Scale"].default_value = (460.0, 24.0, 1.0)
    mp2 = nt.nodes.new("ShaderNodeMapping")
    mp2.inputs["Scale"].default_value = (24.0, 460.0, 1.0)
    w1 = nt.nodes.new("ShaderNodeTexWave")
    w1.wave_type, w1.bands_direction = "BANDS", "X"
    w1.inputs["Scale"].default_value = 1.0
    w2 = nt.nodes.new("ShaderNodeTexWave")
    w2.wave_type, w2.bands_direction = "BANDS", "X"
    w2.inputs["Scale"].default_value = 1.0
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    fuzz = _noise(nt, 1600.0, 5.0, "fuzz")
    addf = nt.nodes.new("ShaderNodeMath")
    addf.operation = "ADD"
    addf.use_clamp = True
    wash = _noise(nt, 3.5, 2.0, "wash")
    washr = nt.nodes.new("ShaderNodeValToRGB")
    wse = washr.color_ramp.elements
    wse[0].position, wse[0].color = 0.30, (0.038, 0.040, 0.047, 1.0)
    wse[1].position, wse[1].color = 0.72, (0.058, 0.062, 0.072, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.65   # round 17
    rramp = nt.nodes.new("ShaderNodeValToRGB")
    re = rramp.color_ramp.elements
    re[0].position, re[0].color = 0.0, (0.70, 0.70, 0.70, 1.0)
    re[1].position, re[1].color = 1.0, (0.96, 0.96, 0.96, 1.0)
    L = nt.links.new
    L(tc.outputs["Generated"], mp1.inputs["Vector"])
    L(tc.outputs["Generated"], mp2.inputs["Vector"])
    L(mp1.outputs["Vector"], w1.inputs["Vector"])
    L(mp2.outputs["Vector"], w2.inputs["Vector"])
    L(w1.outputs["Fac"], mult.inputs[0])
    L(w2.outputs["Fac"], mult.inputs[1])
    L(mult.outputs["Value"], addf.inputs[0])
    L(fuzz.outputs["Fac"], addf.inputs[1])
    L(addf.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L(wash.outputs["Fac"], washr.inputs["Fac"])
    L(washr.outputs["Color"], bsdf.inputs["Base Color"])
    L(addf.outputs["Value"], rramp.inputs["Fac"])
    L(rramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


def proc_plaster(name):
    """Painted plaster wall (round 8 review: "walls should have more
    texture"): two-scale mottling drives a subtle colour ramp, a
    medium noise gives the tooth bump, a fine noise the roughness."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    blotch = _noise(nt, 3.0, 1.5, "blotch")     # ~1 m clouds
    tooth = _noise(nt, 42.0, 4.0, "tooth")       # ~8 cm tooth
    fine = _noise(nt, 900.0, 5.0, "fine")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.35, (0.470, 0.450, 0.420, 1.0)
    e[1].position, e[1].color = 0.70, (0.560, 0.540, 0.505, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.55   # round 16: stronger
    rramp = nt.nodes.new("ShaderNodeValToRGB")
    re = rramp.color_ramp.elements
    re[0].position, re[0].color = 0.0, (0.78, 0.78, 0.78, 1.0)
    re[1].position, re[1].color = 1.0, (0.97, 0.97, 0.97, 1.0)
    L = nt.links.new
    L(blotch.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L(tooth.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L(fine.outputs["Fac"], rramp.inputs["Fac"])
    L(rramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


def screen_mat(name):
    """Dark desktop: vertical gradient + a soft off-axis glow, slight
    emission so it reads on, gloss for the window reflection."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "LINEAR"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.05, (0.010, 0.013, 0.022, 1.0)
    e[1].position, e[1].color = 0.95, (0.055, 0.078, 0.110, 1.0)
    L = nt.links.new
    L(tc.outputs["Generated"], grad.inputs["Vector"])
    L(grad.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    for key in ("Emission", "Emission Color"):
        if key in bsdf.inputs:
            L(ramp.outputs["Color"], bsdf.inputs[key])
            break
    bsdf.inputs["Emission Strength"].default_value = 0.55
    bsdf.inputs["Roughness"].default_value = 0.08
    return mat


# ---------------------------------------------------------- env primitives

def box(name, loc, size, mat, rot=(0.0, 0.0, 0.0), bevel=None,
        smooth=False, cable=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    if rot != (0.0, 0.0, 0.0):
        o.rotation_euler = rot
    if bevel:
        bm = o.modifiers.new("bev", "BEVEL")
        bm.width, bm.segments = bevel, 4
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
    if cable:
        CABLES.append(o)
    return o


def cyl(name, loc, r, depth, mat, rot=(0.0, 0.0, 0.0), smooth=True,
        track_to=None, scale=None, cable=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        location=loc)
    o = bpy.context.active_object
    o.name = name
    if track_to is not None:
        d = mathutils.Vector(track_to) - mathutils.Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    elif rot != (0.0, 0.0, 0.0):
        o.rotation_euler = rot
    if scale is not None:
        o.scale = scale
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
    if cable:
        CABLES.append(o)
    return o


def sphere(name, loc, scale, mat, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
    return o


def torus(name, loc, R, r, mat, rot=(0.0, 0.0, 0.0), scale=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    if scale is not None:
        o.scale = scale
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
    return o


def cone(name, loc, r1, r2, depth, mat, track_to):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth,
                                    location=loc)
    o = bpy.context.active_object
    o.name = name
    d = mathutils.Vector(track_to) - mathutils.Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
    return o


def cable(name, pts, r, mat, keyboard=False):
    """Rubber-sheathed cable: bezier spline, auto handles, round bevel.
    Round 18: `keyboard=True` marks the KEYBOARD's own cables (TRRS +
    its USB-C lead) — those hide in every env shot except the mat
    closeup ("wireless" means the KEYBOARD is wireless, not a
    powerless monitor/dock/computer). Infrastructure cables default
    to always-visible."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.fill_mode = "FULL"
    cu.bevel_depth = r
    cu.bevel_resolution = 6
    spl = cu.splines.new("BEZIER")
    spl.bezier_points.add(len(pts) - 1)
    for p, co in zip(spl.bezier_points, pts):
        p.co = co
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    S.assign([ob], mat)
    PROPS.append(ob)
    if keyboard:
        CABLES.append(ob)
    return ob


def light(name, kind, energy, loc, target, color=(1.0, 1.0, 1.0),
          size=1.0, spot=math.radians(50)):
    li = bpy.data.lights.new(name, kind)
    li.energy = energy
    li.color = color
    if kind == "AREA":
        li.size = size
    if kind == "SPOT":
        li.spot_size = spot
        li.spot_blend = 0.35
    o = bpy.data.objects.new(name, li)
    o.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(o)
    return o


def env_world():
    world = bpy.data.worlds.new("env_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs[0].default_value = (0.048, 0.052, 0.062, 1.0)
    bg_cam.inputs[1].default_value = 1.0
    bg_amb.inputs[0].default_value = (0.095, 0.092, 0.098, 1.0)
    bg_amb.inputs[1].default_value = 0.30
    L = nt.links.new
    L(bg_cam.outputs["Background"], mix.inputs[1])
    L(bg_amb.outputs["Background"], mix.inputs[2])
    L(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    L(mix.outputs["Shader"], out.inputs["Surface"])


# ------------------------------------------------------- my prop builders
# Round 17: the agent's mug (no visible liquid, odd handle), mouse
# (still wrong after two passes) and lying-fanned pens are replaced
# with these — simple, honest forms with strong value contrast that
# read correctly at 50 px in the desk shot.


def add_mug(loc, mats):
    """Ceramic mug, Ø82 x 96: outer wall, open glossy cavity, dark
    coffee 34mm down with a lighter crema ring, proper oval-section
    handle."""
    mx, my, mz = loc
    out = []
    o = cyl("env_mug_wall", (mx, my, mz + 0.048), 0.041, 0.096,
            mats["mug_outer"])
    out.append(o)
    o = cyl("env_mug_inner", (mx, my, mz + 0.0465), 0.0365, 0.089,
            mats["mug_glaze"])
    out.append(o)
    o = torus("env_mug_rim", (mx, my, mz + 0.0955), 0.0378, 0.0026,
              mats["mug_outer"])
    out.append(o)
    o = cyl("env_mug_coffee", (mx, my, mz + 0.062), 0.0360, 0.0015,
            mats["mug_coffee"])
    out.append(o)
    o = torus("env_mug_crema", (mx, my, mz + 0.0623), 0.0345, 0.0009,
              mats["mug_crema"])
    out.append(o)
    o = torus("env_mug_handle", (mx + 0.046, my, mz + 0.048),
              0.024, 0.0055, mats["mug_outer"],
              rot=(math.radians(90), 0.0, 0.0), scale=(1.0, 1.0, 1.35))
    out.append(o)
    return out


def add_mouse(loc, mats, rot_z=0.25):
    """Two-button shell mouse: egg body + rear hump, two button
    shells with a dark seam, exposed scroll wheel, thumb buttons."""
    out = []
    bx, by, bz = loc
    o = sphere("env_ms_body", (bx, by, bz + 0.009),
               (0.029, 0.057, 0.017), mats["ms_body"])
    o.rotation_euler.z = rot_z
    out.append(o)
    o = sphere("env_ms_hump", (bx - 0.008, by - 0.018, bz + 0.013),
               (0.024, 0.036, 0.017), mats["ms_body"])
    o.rotation_euler.z = rot_z
    out.append(o)
    for tag, dx in (("l", -0.0135), ("r", 0.0135)):
        o = box(f"env_ms_btn_{tag}",
                (bx + dx, by + 0.020, bz + 0.0145),
                (0.0145, 0.018, 0.0035), mats["ms_body"],
                rot=(0.0, 0.0, rot_z), bevel=0.002)
        out.append(o)
    o = box("env_ms_seam", (bx, by + 0.020, bz + 0.0148),
            (0.0011, 0.019, 0.0038), mats["ms_seam"],
            rot=(0.0, 0.0, rot_z))
    out.append(o)
    o = cyl("env_ms_wheel", (bx, by + 0.0125, bz + 0.0225),
            0.0065, 0.0045, mats["ms_wheel"],
            rot=(math.radians(90), 0.0, rot_z))
    out.append(o)
    for i, dy in enumerate((-0.003, 0.009)):
        o = box(f"env_ms_thumb_{i}",
                (bx - 0.0245, by + dy, bz + 0.011),
                (0.003, 0.010, 0.0035), mats["ms_seam"],
                rot=(0.0, 0.0, rot_z), bevel=0.0008)
        out.append(o)
    return out


def add_standing_pens(loc, mats, n=3):
    """Pens standing tip-down in the cup: barrel + cap + clip, three
    finishes, slight staggered leans (round-17: the agent's fanned
    pens clipped through the holder)."""
    out = []
    px, py, pz = loc
    finishes = ("pen_dark", "pen_white", "pen_copper")
    offs = ((0.007, 0.003, -6), (-0.008, -0.005, 5), (0.001, 0.010, 10))
    for i in range(n):
        dx, dy, lean = offs[i % 3]
        rot = (math.radians(lean), 0.0, math.radians(lean * 1.2))
        o = cyl(f"env_pen_bar_{i}", (px + dx, py + dy, pz + 0.052),
                0.0055, 0.128, mats[finishes[i % 3]], rot=rot)
        out.append(o)
        o = cyl(f"env_pen_cap_{i}", (px + dx, py + dy, pz + 0.124),
                0.0060, 0.026, mats["pen_cap"], rot=rot)
        out.append(o)
        o = box(f"env_pen_clip_{i}", (px + dx - 0.0072, py + dy,
                                     pz + 0.110),
                (0.0012, 0.0030, 0.024), mats["pen_clip_metal"],
                rot=(0.0, 0.0, math.radians(lean * 1.2)), bevel=0.0004)
        out.append(o)
    return out


# ------------------------------------------------------------- the scene

def main():
    args = S.parse_args()
    res = tuple(int(v) for v in args.res.split("x"))
    shots = [s for s in args.shots.split(",")
             if s in ("desk", "mat", "gaming", "dev")] or ["desk", "mat"]
    os.makedirs(os.path.join(args.out, "env"), exist_ok=True)
    S.init_scene()
    parts, all_objs = S.build_keyboard(args)

    # ---- environment pose: rounds 9-15 — 200 read limp, 120 read
    # "still too far apart": 84 mm total. Halves rest ON the mat.
    (bx0, by0, bz0), (bx1, by1, bz1) = S.bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    MAT_T = 0.003
    EXTRA_SPLIT = 0.042
    for h, sgn in (("L", -1.0), ("R", 1.0)):
        pe = bpy.data.objects.get(f"pose_{h}")
        pe.location.x += sgn * EXTRA_SPLIT
        pe.location.z += MAT_T
    bpy.context.view_layer.update()
    (bx0, by0, _), (bx1, by1, _) = S.bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    desk_z = bz0                  # desk surface == original tub bottom
    mat_top = bz0 + MAT_T
    print(f"[env] assembly centre ({cx*1000:.0f},{cy*1000:.0f}) mm, "
          f"desk z {desk_z*1000:.2f}", flush=True)

    # ---- materials
    m_wood = EM.proc_walnut2("env_walnut")   # round 12: flagship wood
    m_fabric = proc_weave("env_fabric")          # the desk mat surface
    m_stitch = S.pbr("env_stitch", (0.42, 0.38, 0.31), rough=0.70)
    S.micro_texture(m_stitch, 700, 0.35, 0.0002, 0.62, 0.78, detail=4.0)
    m_wall = proc_plaster("env_wall")
    m_base = S.pbr("env_baseboard", (0.75, 0.73, 0.69), rough=0.55)
    m_carpet = S.pbr("env_carpet", (0.115, 0.105, 0.095), rough=0.98)
    S.micro_texture(m_carpet, 900, 0.45, 0.0009, 0.95, 1.0, detail=4.0)
    m_alu = S.pbr("env_alu", (0.55, 0.56, 0.585), rough=0.30, metal=1.0)
    S.micro_texture(m_alu, 300, 0.06, 0.00001, 0.24, 0.34)
    m_alu_dark = S.pbr("env_alu_dark", (0.30, 0.31, 0.33), rough=0.38,
                       metal=1.0)
    m_bezel = S.pbr("env_bezel", (0.028, 0.029, 0.032), rough=0.32)
    m_screen = screen_mat("env_screen")
    m_plastic = S.pbr("env_plastic", (0.83, 0.83, 0.85), rough=0.15)
    S.micro_texture(m_plastic, 220, 0.10, 0.00002, 0.12, 0.20)
    m_rubber = S.pbr("env_rubber", (0.021, 0.022, 0.024), rough=0.55)
    S.micro_texture(m_rubber, 260, 0.16, 0.00004, 0.48, 0.62)
    # cable jacket: darker rubber with a tight surface tooth so the
    # thick cable reads as a jacketed lead, not a rendered tube
    m_cable = EM.proc_cable_braid("env_cable")   # round 12: braided
    m_connector = S.pbr("env_connector", (0.09, 0.09, 0.10), rough=0.30,
                        metal=0.7)
    m_gold = S.pbr("env_gold", (0.75, 0.58, 0.24), rough=0.28, metal=1.0)
    m_ceramic = S.pbr("env_ceramic", (0.72, 0.46, 0.33), rough=0.38)
    S.micro_texture(m_ceramic, 140, 0.14, 0.00003, 0.30, 0.44)
    m_coffee = S.pbr("env_coffee", (0.050, 0.030, 0.018), rough=0.08)
    m_cup_dark = S.pbr("env_cup_dark", (0.105, 0.105, 0.115), rough=0.58)
    S.micro_texture(m_cup_dark, 90, 0.20, 0.00005, 0.50, 0.65)
    m_cover_nb = S.pbr("env_notebook", (0.145, 0.185, 0.155), rough=0.58)
    S.micro_texture(m_cover_nb, 120, 0.14, 0.00004, 0.50, 0.64)
    m_pages = EM.proc_page_edges("env_pages")   # true sheet lines
    m_pen_dark = S.pbr("env_pen_dark", (0.085, 0.087, 0.095), rough=0.30)
    m_pen_white = S.pbr("env_pen_white", (0.85, 0.85, 0.84), rough=0.22)
    m_pen_copper = S.pbr("env_pen_copper", (0.52, 0.33, 0.20), rough=0.32,
                         metal=0.9)
    m_lamp = S.pbr("env_lamp_black", (0.020, 0.021, 0.023), rough=0.42)
    m_led = emit_mat("env_led", (0.10, 0.90, 0.35), 5.0)
    m_bulb = emit_mat("env_bulb", (1.0, 0.76, 0.47), 3.5)
    m_mon_led = emit_mat("env_mon_led", (0.15, 0.85, 1.0), 1.5)

    # ---- desk, wall, floor
    box("env_desk", (cx, cy + 0.06, desk_z - 0.020),
        (2.40, 1.06, 0.040), m_wood, bevel=0.003)
    box("env_wall", (cx, cy + 0.635, 0.42), (3.60, 0.045, 2.60), m_wall)
    box("env_baseboard", (cx, cy + 0.615, -0.735), (3.60, 0.055, 0.075),
        m_base)
    box("env_floor", (cx, cy - 0.40, -0.775), (3.60, 2.40, 0.012), m_carpet)

    # ---- fabric desk mat + stitched border
    mat = box("env_mat", (cx, cy - 0.010, mat_top - MAT_T / 2),
              (0.900, 0.400, MAT_T), m_fabric, bevel=0.0012)
    mat_x, mat_y = cx, cy - 0.010
    inset, step = 0.012, 0.0075
    for sy in (-1, 1):
        y = mat_y + sy * (0.200 - inset)
        n = int((0.900 - 2 * inset) / step)
        for i in range(n + 1):
            x = mat_x - 0.450 + inset + i * step
            box(f"env_stitch_{sy}_{i}", (x, y, mat_top + 0.00030),
                (0.0042, 0.0012, 0.0009), m_stitch)
    for sx in (-1, 1):
        x = mat_x + sx * (0.450 - inset)
        n = int((0.400 - 2 * inset) / step)
        for i in range(n + 1):
            y = mat_y - 0.200 + inset + i * step
            box(f"env_stitchV_{sx}_{i}", (x, y, mat_top + 0.00030),
                (0.0012, 0.0042, 0.0009), m_stitch)

    # ---- round 12: the sculpted props replace the primitives
    # (env_props.py — the agent-built high-detail module)
    ep_mats = {"nb_pages": m_pages}
    # materials for my own builders (round 17)
    my_mats = {
        "mug_outer": S.pbr("my_mug", (0.72, 0.46, 0.33), rough=0.38),
        "mug_glaze": S.pbr("my_glaze", (0.16, 0.10, 0.07), rough=0.08),
        "mug_coffee": S.pbr("my_coffee", (0.045, 0.027, 0.016), rough=0.06),
        "mug_crema": S.pbr("my_crema", (0.30, 0.19, 0.11), rough=0.35),
        "ms_body": S.pbr("my_ms", (0.83, 0.83, 0.85), rough=0.16),
        "ms_seam": S.pbr("my_ms_seam", (0.05, 0.05, 0.055), rough=0.35),
        "ms_wheel": S.pbr("my_ms_wheel", (0.28, 0.28, 0.30), rough=0.45),
        "pen_cap": S.pbr("my_pen_cap", (0.085, 0.087, 0.095), rough=0.30),
        "pen_clip_metal": S.pbr("my_pen_clip", (0.72, 0.73, 0.75),
                                rough=0.25, metal=1.0),
        "pen_dark": m_pen_dark, "pen_white": m_pen_white,
        "pen_copper": m_pen_copper,
    }
    S.micro_texture(my_mats["mug_outer"], 140, 0.14, 0.00003,
                    0.30, 0.44)
    # monitor: dual-strut neck, hinge, quick-release plate, screen, LED
    mx, my = cx, cy + 0.31   # round 18: centred (was +0.06 right)
    mon_objs = EP.build_monitor((mx, my, desk_z), ep_mats)
    PROPS.extend(mon_objs)
    # generic mini PC: vent grilles both flanks, full back I/O, front
    # USB-C x2 + headphone, debossed top circle
    mini_x, mini_y = cx + 0.42, cy + 0.36
    PROPS.extend(EP.build_minipc((mini_x, mini_y, desk_z), ep_mats))
    # sculpted ergonomic RH mouse: two buttons, thumb buttons, notched
    # wheel, seam groove
    PROPS.extend(add_mouse((cx + 0.40, cy - 0.105, desk_z),
                           my_mats, rot_z=0.30))
    # pen cup stays ours (the builder pens fan into it)
    cupx, cupy = cx - 0.62, cy + 0.20
    # round 18: a HOLLOW cup — the old inner disc was a lid the pens
    # clipped through; an inner wall makes a real cavity they stand in
    cyl("env_cup", (cupx, cupy, desk_z + 0.048), 0.038, 0.096, m_cup_dark)
    cyl("env_cup_inner", (cupx, cupy, desk_z + 0.047), 0.0335, 0.086,
        m_rubber)
    torus("env_cup_rim", (cupx, cupy, desk_z + 0.0955),
          0.0375, 0.0022, m_cup_dark)
    PROPS.extend(add_standing_pens((cupx, cupy, desk_z), my_mats, n=3))
    # notebook: overhanging covers, page block with true sheet lines
    # (proc_page_edges), spine ridge, strap, ribbon, title block
    nbx, nby = cx - 0.44, cy + 0.33
    PROPS.extend(EP.build_notebook((nbx, nby, desk_z),
                                   ep_mats, rot_z=math.radians(-14)))
    # mug (round 17): mine — visible coffee + crema, honest handle
    PROPS.extend(add_mug((cx + 0.70, cy + 0.30, desk_z), my_mats))
    # architect lamp: rocker switch, knuckle joints, real bulb
    lampx, lampy = cx - 0.80, cy + 0.44
    shade_pt = (lampx + 0.150, lampy - 0.110, desk_z + 0.345)
    PROPS.extend(EP.build_lamp((lampx, lampy, desk_z), shade_pt, ep_mats))
    # ---- aluminium dock (round 13: "way more detail... on dock"):
    # rubber under-body with 4 feet, alu chassis, a separate machined
    # brushed LID plate (reads as a screwed-on top), 4 individual
    # front ports (2 USB-C pills, USB-A, SD slot), a side power
    # button, status LED
    # round 17: the dock moved left-forward — at +0.34/+0.28 it
    # intersected the mini (mini spans x 0.322..0.518)
    dock_x, dock_y, dock_z = cx + 0.20, cy + 0.16, desk_z
    box("env_dock_rubber", (dock_x, dock_y, dock_z + 0.002),
        (0.086, 0.038, 0.004), m_rubber, bevel=0.001)
    for fy in (-1, 1):
        for fz in (-1, 1):
            cyl(f"env_dock_foot_{fy}_{fz}",
                (dock_x + fz * 0.034, dock_y + fy * 0.014,
                 dock_z + 0.0012), 0.0035, 0.0024, m_rubber)
    box("env_dock", (dock_x, dock_y, dock_z + 0.004 + 0.0075),
        (0.092, 0.044, 0.015), m_alu, bevel=0.004)
    box("env_dock_lid", (dock_x, dock_y, dock_z + 0.0205),
        (0.084, 0.036, 0.0018), m_alu, bevel=0.0012)
    for i, (px, pw, ph) in enumerate(((-0.024, 0.009, 0.0034),
                                      (-0.008, 0.009, 0.0034),
                                      (0.010, 0.0135, 0.0040),
                                      (0.029, 0.0026, 0.0030))):
        box(f"env_dock_p{i}", (dock_x + px, dock_y - 0.0225,
                               dock_z + 0.0085),
            (pw, 0.004, ph), m_rubber)
    cyl("env_dock_btn", (dock_x + 0.045, dock_y, dock_z + 0.0085),
        0.0022, 0.0015, m_rubber, rot=(0.0, 0.0, math.radians(90)))
    cyl("env_dock_led", (dock_x + 0.036, dock_y - 0.0222, dock_z + 0.010),
        0.0012, 0.001, m_led)

    # ---- cables (mat shot only; hidden for the wireless desk story)
    # TRRS: chunky plugs dress the jack holes — collar, barrel, boot —
    # then a thick jacket spans the halves in one stiff wide U.
    # the jack's DESIGN y comes from placements.json — the posed bbox
    # y cannot be un-posed by dividing by SCALE (round-11 catch #2:
    # splay mixes x into y, so the derived hole still landed ~6 mm
    # toward the MCU)
    _pl = json.load(open(os.path.join(S.ASSETS, "placements.json")))
    _jy = {p["ref"]: p["y"] for half in ("Left", "Right")
           for p in _pl[half] if p["ref"].startswith("J_")}
    jl = [o for o in parts["L"]["board"] if o.name.startswith("J_L1")]
    jr = [o for o in parts["R"]["board"] if o.name.startswith("J_R1")]
    usb = [o for o in parts["L"].get("nano", [])
           if o.name.startswith("nano_usb")]
    (lb0, lb1) = S.bbox_mm(parts["L"]["tub"])
    (rb0, rb1) = S.bbox_mm(parts["R"]["tub"])
    (j0, j1) = S.bbox_mm(jl)
    (k0, k1) = S.bbox_mm(jr)
    (u0, u1) = S.bbox_mm(usb)
    # round-10 review: "audio jacks still aren't correctly placed...
    # the cable is kinda floating outside the port". Estimates from the
    # jack bbox were never going to nail it. The EXACT posed hole
    # comes from the tub's own matrix_world: design frame -> glb local
    # is (x, -z, y) (import_glb's Y-up note) and the tub mesh data is
    # in glb units = design mm, so the hole = inner wall face at the
    # jack's y, zc 1.5: local (x_wall, -1.5, y_jack). The plug is then
    # built ALONG the posed wall direction, starting 2 mm INSIDE the
    # wall so the collar visibly enters the hole instead of hovering.
    def posed_hole(tub_objs, jack_y, sgn):
        tub = next(o for o in tub_objs if o.type == "MESH")
        # inner wall face: the L half's wall is its +x face, the R
        # half's its -x face (the first cut at * sgn was a mirror bug
        # that flung the right plug 0.6 m into space)
        lx = (max(c[0] for c in tub.bound_box) if sgn > 0
              else min(c[0] for c in tub.bound_box))
        v = mathutils.Vector((lx, -1.5, jack_y))
        return tub.matrix_world @ v

    def wall_dir(tub_objs, sgn):
        tub = next(o for o in tub_objs if o.type == "MESH")
        d = tub.matrix_world.to_3x3() @ mathutils.Vector((sgn, 0.0, 0.0))
        return d.normalized()

    hole_l = posed_hole(parts["L"]["tub"], _jy["J_L1"], 1.0)
    hole_r = posed_hole(parts["R"]["tub"], _jy["J_R1"], -1.0)
    dir_l = wall_dir(parts["L"]["tub"], 1.0)
    dir_r = wall_dir(parts["R"]["tub"], -1.0)
    PLUG_TIP = 0.018   # round 16: jacket starts inside the boot
    for tag, hole, d in (("l", hole_l, dir_l), ("r", hole_r, dir_r)):
        for name, r, t0, t1, m in (
                ("collar", 0.0019, -0.0020, 0.0035, m_gold),
                ("barrel", 0.0024, 0.0035, 0.0125, m_connector)):
            tc = (t0 + t1) / 2
            cyl(f"env_trrs_{name}_{tag}",
                tuple(hole + d * tc), r, t1 - t0, m,
                track_to=tuple(hole + d * (tc + 1.0)), cable=True)
        # round 16: the boot's cable-side mouth is WIDER than the
        # jacket so it swallows the cable — the old 2.1 mouth was
        # narrower than the 2.4 jacket and left a visible gap/step
        boot = cone(f"env_trrs_boot_{tag}",
                    tuple(hole + d * 0.0165), 0.0027, 0.0027, 0.008,
                    m_rubber, track_to=tuple(hole + d * 10.0))
        CABLES.append(boot)
    tip_l = tuple(hole_l + dir_l * PLUG_TIP)
    tip_r = tuple(hole_r + dir_r * PLUG_TIP)
    mid_y = (tip_l[1] + tip_r[1]) / 2
    mid_x = (tip_l[0] + tip_r[0]) / 2
    sag_z = mat_top + 0.0035
    sag = (mid_x, mid_y, sag_z)
    cable("env_trrs_cable", [tip_l, sag, tip_r], 0.0024, m_cable,
          keyboard=True)

    # USB-C: nano (left half, back rim) -> dock, right-angle at the dock
    usb_exit_y = lb1[1] + 0.004
    usb_exit = (u0[0] + (u1[0] - u0[0]) * 0.5, usb_exit_y,
                min((u0[2] + u1[2]) / 2, mat_top + 0.0135))
    box("env_usbc_plug", (usb_exit[0], lb1[1] + 0.0028, usb_exit[2]),
        (0.012, 0.011, 0.0062), m_connector, bevel=0.0015, cable=True)
    cyl("env_usbc_boot", (usb_exit[0], lb1[1] + 0.0085, usb_exit[2]),
        0.0021, 0.006, m_rubber, rot=(math.radians(90), 0.0, 0.0),
        cable=True)
    # round 13: the cable arcs RIGHT of the monitor foot (the old
    # diagonal path phase-checked straight through it)
    dock_port = (dock_x - 0.006, dock_y - 0.026, dock_z + 0.010)
    box("env_usbc_dock_plug", (dock_x - 0.006, dock_y - 0.027, dock_z + 0.010),
        (0.013, 0.010, 0.0060), m_connector, bevel=0.0015, cable=True)
    cable("env_usbc_cable", [
        usb_exit,
        (usb_exit[0] + 0.040, usb_exit_y + 0.020, mat_top + 0.005),
        (dock_x - 0.045, dock_y - 0.030, desk_z + 0.004),
        dock_port,
    ], 0.0020, m_cable, keyboard=True)
    # round 17: the full visible power/data chain — the desk shot
    # answers "where is power coming from?": a wall outlet behind the
    # desk, the mini's adapter cable arcing up to it, a short mini->
    # dock link on the desk, and the dock->monitor line rising over
    # the stand foot to the panel back.
    # round 18: "socket too unrealistic, just have a cable going
    # from computer to under the desk" — the power lead arcs off the
    # mini's back, over the desk's rear edge and down out of sight
    cable("env_mini_power", [
        (mini_x, mini_y + 0.098, desk_z + 0.012),
        (mini_x + 0.015, mini_y + 0.200, desk_z + 0.010),
        (mini_x + 0.005, cy + 0.585, desk_z - 0.260),
    ], 0.0026, m_cable)
    cable("env_mini_dock", [
        (mini_x - 0.060, mini_y - 0.098, desk_z + 0.010),
        (mini_x - 0.120, mini_y - 0.130, desk_z + 0.004),
        (dock_x + 0.008, dock_y + 0.024, desk_z + 0.008),
    ], 0.0018, m_cable)
    cable("env_dock_monitor", [
        (dock_x, dock_y + 0.023, dock_z + 0.011),
        (dock_x + 0.010, dock_y + 0.110, desk_z + 0.075),
        (mx + 0.010, my + 0.045, desk_z + 0.170),
        (mx + 0.004, my + 0.006, desk_z + 0.250),
    ], 0.0020, m_cable)

    # ---- round 12: the PC's power + the monitor data cable (review:
    # "power cable (where is power coming from?), data cable (to
    # monitor)") — they run down BEHIND the desk, out of frame; the
    # KEYBOARD stays wireless in the desk shot
    back_edge_y = cy + 0.59
    mini_io = (mini_x, mini_y + 0.098, desk_z + 0.012)
    mini_io = (mini_x, mini_y + 0.098, desk_z + 0.012)   # kept for
    # reference; the round-17 outlet chain replaces the blind drape
    # round 14: "cables going through stuff, especially through the
    # base of monitor stand" — the old path ended INSIDE the foot's
    # footprint (y 0.225..0.395). The data cable now sweeps BEHIND the
    # foot's right corner and climbs to the panel's back I/O, 250 mm
    # up — above the foot, into the panel, touching nothing.
    cable("env_pc_data", [
        (mini_x - 0.006, mini_y + 0.098, desk_z + 0.008),
        (mini_x - 0.100, mini_y + 0.150, desk_z + 0.006),
        (cx + 0.160, cy + 0.430, desk_z + 0.055),
        (mx + 0.004, my + 0.006, desk_z + 0.255),
    ], 0.0022, m_cable)

    # ---- gaming-scene props (round 12): the RGB tower behind the
    # board + a second mug for the dev top-down (between the halves).
    # Both hidden by default; visibility is toggled per shot below.
    # round 13: the tower moves right of the mug — at the left it
    # phase-checked through the notebook footprint; glass (+x face)
    # rotated to catch the front-centre camera
    tower_objs = EP.build_tower((cx + 0.88, cy + 0.44, desk_z), ep_mats)
    PROPS.extend(tower_objs)
    tower_root = tower_objs[0] if tower_objs else None
    dev_mug = []   # round 18: removed (clipped the keyboards in the
    # mat closeup; the side mug stays for desk/dev)
    side_mug_names = set()   # round 18: no per-shot mug toggling
    # rotate the tower so its glass face catches the gaming camera
    for o in tower_objs:
        if o.parent is None:
            o.rotation_euler.z = math.radians(-115)

    # ---- environment lighting (calibrated round 7; unchanged)
    env_world()
    li_window = light("env_window", "AREA", 22, (cx - 1.05, cy - 0.28, 0.66),
                      (cx, cy + 0.05, 0.04), color=(0.93, 0.95, 1.02),
                      size=1.15)
    li_fill = light("env_fill", "AREA", 4, (cx + 0.85, cy - 0.20, 0.30),
                    (cx, cy + 0.05, 0.02), color=(1.0, 0.92, 0.80),
                    size=0.70)
    # round 17: a LOW GRAZING sweep from the front-right skims the
    # desk surface — every bump on the walnut, weave and plaster
    # catches a raking shadow (the flatness fix: one big soft
    # overhead-ish source leaves nothing to see)
    li_graze = light("env_graze", "AREA", 4.5,
                     (cx + 0.80, cy - 0.52, 0.09),
                     (cx - 0.15, cy + 0.10, 0.005),
                     color=(1.0, 0.97, 0.92), size=0.55)
    # RGB accents behind the board for the gaming mood (dark until the
    # gaming shot enables them)
    rgb_pos = ((cx - 0.66, cy + 0.34, 0.16), (cx - 0.72, cy + 0.46, 0.20),
               (cx - 0.80, cy + 0.30, 0.10))
    rgb_cols = ((0.90, 0.12, 0.40), (0.12, 0.45, 1.00), (0.15, 0.95, 0.55))
    rgb_lights = [light(f"env_rgb_{i}", "AREA", 0.0, pos,
                        (cx, cy - 0.02, 0.02), color=col, size=0.16)
                  for i, (pos, col) in enumerate(zip(rgb_pos, rgb_cols))]

    # ---- cameras (calibrated round 7; unchanged)
    desk_cam = S.add_cam("env_desk", (cx + 0.10, cy - 1.45, 0.74),
                         (cx + 0.02, cy + 0.12, 0.05), lens=28)
    # round 16: dead-centre and pulled back — round 15 still clipped
    # the left half and pushed the right half to centre. The camera
    # sits on the assembly's centreline so both halves are symmetric,
    # far enough that the full board fits with margin.
    # round 17: slightly higher still — show more of the keyboard
    look = (cx, cy + 0.005, 0.010)
    mat_cam = S.add_cam("env_mat", (cx, cy - 0.70, 0.50),
                        look, lens=45)
    mat_cam.data.dof.use_dof = True
    mat_cam.data.dof.focus_distance = (
        mathutils.Vector(mat_cam.location) -
        mathutils.Vector(sag)).length
    mat_cam.data.dof.aperture_fstop = 8.0   # round 10: "still excessive"

    # gaming: low 3/4 in a dark room, the tower's RGB fans glowing
    # behind the halves (wireless gaming story)
    gaming_cam = S.add_cam("env_gaming", (cx + 0.06, cy - 1.32, 0.60),
                           (cx - 0.02, cy + 0.10, 0.06), lens=32)
    # dev: high top-down over the seam, the mug between the halves,
    # notebook + monitor glow — the software-dev setup
    dev_cam = S.add_cam("env_dev", (cx + 0.06, cy - 0.34, 0.86),
                        (cx, cy - 0.02, 0.005), lens=30)

    # ---- framecheck subjects: what must stay IN frame. The desk,
    # wall, baseboard and floor are backdrop and intentionally overflow
    # the frame edges; so do the far ends of the halves in the closeup.
    # desk (round 8): WIRELESS — the cables are hidden, so they are not
    # subjects either. mat: cables + dock + the caps around the seam.
    backdrop = {"env_desk", "env_wall", "env_baseboard", "env_floor"}
    desk_subjects = ([o for o in all_objs]
                      + [o for o in PROPS
                         if o.name not in backdrop and o not in CABLES]
                      + [mat])
    # seam-adjacent columns only: the third column still RENDERS, it
    # just isn't a framing constraint (a closeup lets the outer edge
    # of the board run past the frame by design)
    near_caps = [o for h in parts for o in parts[h]["caps"]
                 if abs(o.matrix_world[0][3] - cx) < 0.130]
    mat_subjects = (CABLES + near_caps
                    + [o for o in PROPS
                       if o.name.startswith("env_dock")])
    def set_visible(objs, visible):
        for o in objs:
            o.hide_render = not visible

    tower_names = {o.name for o in tower_objs}
    dev_mug_names = {o.name for o in dev_mug}
    # the tower + dev mug are hidden in desk/mat, so they are not
    # framing constraints there either
    for _sl in (desk_subjects, mat_subjects):
        _sl[:] = [o for o in _sl if o.name not in tower_names
                  and o.name not in dev_mug_names]
    # the tower (465 mm) and the monitor (567 mm on its stand) are
    # BACKGROUND elements in the gaming mood — dark room, monitor off,
    # the tower's RGB fans glowing; both loom cropped behind the
    # keyboard, so neither is a framing constraint
    mon_names = {o.name for o in mon_objs}
    gaming_subjects = ([o for o in all_objs]
                       + [o for o in PROPS
                          if o.name not in backdrop
                          and o.name not in tower_names
                          and o.name not in mon_names]
                       + [mat])
    # the dev top-down frames the SETUP: keyboard on the mat
    dev_subjects = ([o for o in all_objs] + [mat])
    cams = {"desk": (desk_cam, desk_subjects),
            "mat": (mat_cam, mat_subjects),
            "gaming": (gaming_cam, gaming_subjects),
            "dev": (dev_cam, dev_subjects)}
    if args.framecheck:
        for name, (cam, subj) in cams.items():
            if name in shots:
                S.frame_report(cam, subj, f"env_{name}", res)
        print("ENV-FRAMECHECK-DONE")
        return
    for name, (cam, subj) in cams.items():
        if name not in shots:
            continue
        # per-shot visibility: the keyboard is WIRELESS in every env
        # shot except the mat closeup (its story IS the cables); the
        # tower + RGB glow live only in gaming; the between-halves
        # mug only in the dev top-down (hiding the side mug there)
        for o in CABLES:
            o.hide_render = (name != "mat")
        set_visible(tower_objs, name == "gaming")
        gaming = (name == "gaming")
        li_window.data.energy = 4.0 if gaming else 22.0
        li_fill.data.energy = 1.5 if gaming else 4.0
        li_graze.data.energy = 1.0 if gaming else 4.5
        for i, li in enumerate(rgb_lights):
            li.data.energy = (0.55, 0.35, 0.45)[i] if gaming else 0.0
        S.render_to(cam, os.path.join(args.out, "env", f"{name}.png"),
                    res, args.samples, args.device)
    print("ENV-DONE")


main()

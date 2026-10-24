"""Hojicha44 desk-environment shots — Blender 5.2 headless (round 7).

Two cameras over the SAME posed keyboard build_keyboard() assembles:

  desk  wide room view: the keyboard on its desk mat mid-desk, monitor
        behind, Mac mini, mouse, pen cup with pens, notebook + pen,
        ceramic mug, desk lamp (a real light in a real shade), wood
        desk, wall + baseboard
  mat   low closeup across the mat: the TRRS cable sagging between the
        halves, USB-C running back to the aluminium dock, shallow depth
        of field on the cable loop

The environment pose widens the split by an extra 44 mm so the TRRS
loop has room to read (the product shots keep the tight 2.5 mm pose);
the halves sit ON the 3 mm mat, lifted by its thickness.

Run:
  blender --background --python renders/scene_env.py -- \
      --samples 128 --res 2400x1500 --shots desk,mat
  ... add --framecheck for the NDC pre-flight (same maths as scene.py)

Reuses scene.py: init_scene, build_keyboard, pbr, micro_texture,
assign, bbox_mm, add_cam, render_to, frame_report. scene.py's parse_args
supplies the flags; the studio-only ones (setups/palette/hide_*/stack
-colors/no_floor) are ignored here.
"""
import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S     # noqa: E402

import mathutils

PROPS = []            # framecheck subjects (everything that must stay in)


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


def proc_wood(name):
    """Oiled walnut: stretched wave bands + noise distortion drive a
    colour ramp (grain runs along the desk's long axis), a fine noise
    drives the pore bump and the roughness range."""
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
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 3.0
    wave.inputs["Detail Scale"].default_value = 1.6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.40, (0.098, 0.060, 0.034, 1.0)
    e[1].position, e[1].color = 0.62, (0.205, 0.128, 0.073, 1.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")      # pores
    nz.inputs["Scale"].default_value = 1100.0
    nz.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    rramp = nt.nodes.new("ShaderNodeValToRGB")   # roughness variation
    re = rramp.color_ramp.elements
    re[0].position, re[0].color = 0.0, (1.0, 1.0, 1.0, 1.0)
    re[1].position, re[1].color = 1.0, (1.0, 1.0, 1.0, 1.0)
    L = nt.links.new
    L(tc.outputs["Generated"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], wave.inputs["Vector"])
    L(wave.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L(mp.outputs["Vector"], nz.inputs["Vector"])
    L(nz.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    # map pore noise 0..1 -> roughness 0.30..0.44
    L(nz.outputs["Fac"], rramp.inputs["Fac"])
    math1 = nt.nodes.new("ShaderNodeMath")
    math1.operation = "MULTIPLY"
    L(rramp.outputs["Color"], math1.inputs[0])
    math1.inputs[1].default_value = 0.14
    math2 = nt.nodes.new("ShaderNodeMath")
    math2.operation = "ADD"
    L(math1.outputs["Value"], math2.inputs[0])
    math2.inputs[1].default_value = 0.30
    L(math2.outputs["Value"], bsdf.inputs["Roughness"])
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
        smooth=False, track=False):
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
    return o


def cyl(name, loc, r, depth, mat, rot=(0.0, 0.0, 0.0), smooth=True,
        track_to=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        location=loc)
    o = bpy.context.active_object
    o.name = name
    if track_to is not None:
        d = mathutils.Vector(track_to) - mathutils.Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    elif rot != (0.0, 0.0, 0.0):
        o.rotation_euler = rot
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    PROPS.append(o)
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


def torus(name, loc, R, r, mat, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
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


def cable(name, pts, r, mat):
    """Smooth rubber cable: a bezier spline with auto handles and a
    round bevel. pts must have >= 2 points; interior points shape sag."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.fill_mode = "FULL"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    spl = cu.splines.new("BEZIER")
    spl.bezier_points.add(len(pts) - 1)
    for p, co in zip(spl.bezier_points, pts):
        p.co = co
        p.handle_left_type = p.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    S.assign([ob], mat)
    PROPS.append(ob)
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


# ------------------------------------------------------------- the scene

def main():
    args = S.parse_args()
    res = tuple(int(v) for v in args.res.split("x"))
    shots = [s for s in args.shots.split(",")
             if s in ("desk", "mat")] or ["desk", "mat"]
    os.makedirs(os.path.join(args.out, "env"), exist_ok=True)
    S.init_scene()
    parts, all_objs = S.build_keyboard(args)

    # ---- environment pose: widen the split so the TRRS loop reads,
    # then sit the halves ON the 3mm mat (lift by its thickness)
    (bx0, by0, bz0), (bx1, by1, bz1) = S.bbox_mm(all_objs)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    MAT_T = 0.003
    EXTRA_SPLIT = 0.022
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
    m_wood = proc_wood("env_walnut")
    # near-black felt: at the window's ~12 W/m2 the old 0.085 albedo
    # rendered mid-grey (0.345 luma) — the mat must read DARK so the
    # bone caps and steel knob pop against it
    m_leather = S.pbr("env_leather", (0.034, 0.035, 0.040), rough=0.66)
    S.micro_texture(m_leather, 360, 0.28, 0.00025, 0.58, 0.72, detail=5.0)
    m_stitch = S.pbr("env_stitch", (0.60, 0.53, 0.42), rough=0.60)
    m_wall = S.pbr("env_wall", (0.545, 0.525, 0.495), rough=0.92)
    S.micro_texture(m_wall, 60, 0.10, 0.0004, 0.88, 0.96, detail=3.0)
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
    m_cable = S.pbr("env_cable", (0.030, 0.031, 0.034), rough=0.42)
    S.micro_texture(m_cable, 500, 0.12, 0.00003, 0.36, 0.50)
    m_connector = S.pbr("env_connector", (0.055, 0.056, 0.060), rough=0.30,
                        metal=0.6)
    m_ceramic = S.pbr("env_ceramic", (0.72, 0.46, 0.33), rough=0.38)
    S.micro_texture(m_ceramic, 140, 0.14, 0.00003, 0.30, 0.44)
    m_coffee = S.pbr("env_coffee", (0.050, 0.030, 0.018), rough=0.08)
    m_cup_dark = S.pbr("env_cup_dark", (0.105, 0.105, 0.115), rough=0.58)
    S.micro_texture(m_cup_dark, 90, 0.20, 0.00005, 0.50, 0.65)
    m_cover_nb = S.pbr("env_notebook", (0.145, 0.185, 0.155), rough=0.58)
    S.micro_texture(m_cover_nb, 120, 0.14, 0.00004, 0.50, 0.64)
    m_pages = S.pbr("env_pages", (0.88, 0.86, 0.80), rough=0.78)
    m_pen_dark = S.pbr("env_pen_dark", (0.085, 0.087, 0.095), rough=0.30)
    m_pen_white = S.pbr("env_pen_white", (0.85, 0.85, 0.84), rough=0.22)
    m_pen_copper = S.pbr("env_pen_copper", (0.52, 0.33, 0.20), rough=0.32,
                         metal=0.9)
    m_lamp = S.pbr("env_lamp_black", (0.020, 0.021, 0.023), rough=0.42)
    m_led = emit_mat("env_led", (0.10, 0.90, 0.35), 5.0)
    m_bulb = emit_mat("env_bulb", (1.0, 0.76, 0.47), 3.5)

    # ---- desk, wall, floor
    box("env_desk", (cx, cy + 0.06, desk_z - 0.020),
        (2.40, 1.06, 0.040), m_wood, bevel=0.003)
    box("env_wall", (cx, cy + 0.635, 0.42), (3.60, 0.045, 2.60), m_wall)
    box("env_baseboard", (cx, cy + 0.615, -0.735), (3.60, 0.055, 0.075),
        m_base)
    box("env_floor", (cx, cy - 0.40, -0.775), (3.60, 2.40, 0.012), m_carpet)

    # ---- desk mat (the mat closeup's hero surface) + stitching
    mat = box("env_mat", (cx, cy - 0.010, mat_top - MAT_T / 2),
              (0.900, 0.400, MAT_T), m_leather, bevel=0.0012)
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

    # ---- monitor (behind, facing the camera)
    mx, my = cx + 0.06, cy + 0.31
    box("env_mon_foot", (mx, my, desk_z + 0.010),
        (0.250, 0.170, 0.020), m_alu, bevel=0.004)
    box("env_mon_neck", (mx, my + 0.012, desk_z + 0.165),
        (0.045, 0.030, 0.310), m_alu)
    box("env_mon_panel", (mx, my + 0.020, desk_z + 0.425),
        (0.615, 0.014, 0.365), m_bezel, bevel=0.003)
    box("env_mon_screen", (mx, my + 0.020 - 0.0077, desk_z + 0.425),
        (0.598, 0.0005, 0.348), m_screen)

    # ---- Mac mini (aluminium squircle, M4-style)
    mini_x, mini_y = cx + 0.42, cy + 0.36
    box("env_mini", (mini_x, mini_y, desk_z + 0.019),
        (0.196, 0.196, 0.038), m_alu, bevel=0.009)
    box("env_mini_ports", (mini_x, mini_y - 0.0965, desk_z + 0.010),
        (0.105, 0.004, 0.008), m_rubber)

    # ---- mouse
    sphere("env_mouse", (cx + 0.40, cy - 0.105, desk_z + 0.007),
           (0.028, 0.056, 0.016), m_plastic)

    # ---- pen cup + pens
    cupx, cupy = cx - 0.62, cy + 0.20
    cyl("env_cup", (cupx, cupy, desk_z + 0.048), 0.038, 0.096, m_cup_dark)
    cyl("env_cup_inner", (cupx, cupy, desk_z + 0.090), 0.034, 0.004,
        m_rubber)
    for i, (dx, dy, rx, rz, pm) in enumerate((
            (0.008, 0.002, math.radians(12), math.radians(15), m_pen_dark),
            (-0.010, -0.005, math.radians(-10), math.radians(-22),
             m_pen_white),
            (0.001, 0.012, math.radians(16), math.radians(40),
             m_pen_copper))):
        cyl(f"env_pen_{i}", (cupx + dx, cupy + dy, desk_z + 0.105),
            0.0055, 0.140, pm, rot=(rx, 0.0, rz))
        # clip: a thin bright strip near the top of each pen
        cyl(f"env_penclip_{i}", (cupx + dx, cupy + dy, desk_z + 0.115),
            0.0057, 0.022, m_alu, rot=(rx, 0.0, rz))

    # ---- notebook + pen lying on it
    nbx, nby = cx - 0.44, cy + 0.33
    rot_nb = math.radians(-14)
    box("env_notebook", (nbx, nby, desk_z + 0.008),
        (0.148, 0.210, 0.014), m_cover_nb, rot=(0.0, 0.0, rot_nb),
        bevel=0.0025)
    box("env_nb_pages", (nbx, nby, desk_z + 0.008),
        (0.139, 0.205, 0.011), m_pages, rot=(0.0, 0.0, rot_nb))
    box("env_nb_strap", (nbx - 0.030, nby, desk_z + 0.0155),
        (0.012, 0.214, 0.004), m_rubber, rot=(0.0, 0.0, rot_nb))
    cyl("env_nb_pen", (nbx + 0.008, nby - 0.012, desk_z + 0.021),
        0.0055, 0.135, m_pen_dark,
        rot=(math.radians(90), 0.0, rot_nb + math.radians(24)))

    # ---- ceramic mug + coffee
    mugx, mugy = cx + 0.70, cy + 0.30
    cyl("env_mug", (mugx, mugy, desk_z + 0.048), 0.041, 0.096, m_ceramic)
    cyl("env_mug_in", (mugx, mugy, desk_z + 0.078), 0.036, 0.004, m_ceramic)
    cyl("env_coffee", (mugx, mugy, desk_z + 0.073), 0.036, 0.0015, m_coffee)
    torus("env_mug_handle", (mugx + 0.046, mugy, desk_z + 0.050),
          0.026, 0.007, m_ceramic, rot=(math.radians(90), 0.0, 0.0))

    # ---- desk lamp: base, struts, shade, real spot + warm bulb
    lampx, lampy = cx - 0.80, cy + 0.44
    cyl("env_lamp_base", (lampx, lampy, desk_z + 0.007), 0.055, 0.014,
        m_lamp)
    joint = (lampx + 0.030, lampy - 0.010, desk_z + 0.315)
    cyl("env_lamp_arm1", ((lampx + joint[0]) / 2,
                          (lampy + joint[1]) / 2,
                          (desk_z + joint[2]) / 2), 0.0065, 0.320, m_lamp,
        track_to=joint)
    sph = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.013,
                                               location=joint)
    joint_o = bpy.context.active_object
    joint_o.name = "env_lamp_joint"
    bpy.ops.object.shade_smooth()
    S.assign([joint_o], m_lamp)
    PROPS.append(joint_o)
    shade_pt = (lampx + 0.150, lampy - 0.110, desk_z + 0.345)
    cyl("env_lamp_arm2", ((joint[0] + shade_pt[0]) / 2,
                          (joint[1] + shade_pt[1]) / 2,
                          (joint[2] + shade_pt[2]) / 2), 0.0065, 0.180,
        m_lamp, track_to=shade_pt)
    aim = (cx - 0.10, cy - 0.05, mat_top)
    cone("env_lamp_shade", shade_pt, 0.046, 0.026, 0.075, m_lamp,
         track_to=aim)
    cyl("env_lamp_bulb", (shade_pt[0], shade_pt[1], shade_pt[2] - 0.024),
        0.016, 0.002, m_bulb, track_to=aim)
    # gentle warm pool over the keyboard, NOT a hot spot on the mat
    # surface the closeup frames (round-7 calibration: 16W aimed at
    # the mat rendered the charcoal leather at ~0.35 luma, washed out)
    # the spot sits just BELOW the shade rim: inside the solid cone it
    # contributed nothing (round-7 calibration found the image
    # byte-identical with the lamp on and off)
    lamp_dir = (mathutils.Vector((cx + 0.02, cy + 0.03, 0.03))
                - mathutils.Vector(shade_pt)).normalized()
    light("env_lamp_spot", "SPOT", 9,
          tuple(mathutils.Vector(shade_pt) + lamp_dir * 0.020),
          (cx + 0.02, cy + 0.03, 0.03),
          color=(1.0, 0.72, 0.42), spot=math.radians(58))

    # ---- aluminium dock (the USB-C cable's destination)
    dock_x, dock_y, dock_z = cx + 0.30, cy + 0.27, desk_z
    box("env_dock_rubber", (dock_x, dock_y, dock_z + 0.002),
        (0.086, 0.038, 0.004), m_rubber, bevel=0.001)
    box("env_dock", (dock_x, dock_y, dock_z + 0.005 + 0.0075),
        (0.092, 0.044, 0.015), m_alu, bevel=0.004)
    box("env_dock_ports", (dock_x, dock_y - 0.0225, dock_z + 0.010),
        (0.058, 0.003, 0.006), m_rubber)
    box("env_dock_p1", (dock_x - 0.014, dock_y - 0.0235, dock_z + 0.010),
        (0.009, 0.004, 0.0032), m_rubber)
    box("env_dock_p2", (dock_x + 0.014, dock_y - 0.0235, dock_z + 0.010),
        (0.009, 0.004, 0.0032), m_rubber)
    cyl("env_dock_led", (dock_x + 0.036, dock_y - 0.0222, dock_z + 0.010),
        0.0012, 0.001, m_led)

    # ---- cables: TRRS between the halves, USB-C back to the dock
    jl = [o for o in parts["L"]["board"] if o.name.startswith("J_L1")]
    jr = [o for o in parts["R"]["board"] if o.name.startswith("J_R1")]
    usb = [o for o in parts["L"].get("nano", [])
           if o.name.startswith("nano_usb")]
    (lb0, lb1) = S.bbox_mm(parts["L"]["tub"])
    (rb0, rb1) = S.bbox_mm(parts["R"]["tub"])
    (j0, j1) = S.bbox_mm(jl)
    (k0, k1) = S.bbox_mm(jr)
    (u0, u1) = S.bbox_mm(usb)
    trrs_l = (lb1[0] + 0.0006, (j0[1] + j1[1]) / 2, (j0[2] + j1[2]) / 2)
    trrs_r = (rb0[0] - 0.0006, (k0[1] + k1[1]) / 2, (k0[2] + k1[2]) / 2)
    # plug barrels + collars at the case walls
    for sgn, pt in ((-1, trrs_l), (1, trrs_r)):
        cyl(f"env_trrs_plug_{'l' if sgn < 0 else 'r'}",
            (pt[0] + sgn * 0.0075, pt[1], pt[2]),
            0.0018, 0.015, m_connector,
            rot=(0.0, math.radians(90), 0.0))
        cyl(f"env_trrs_collar_{'l' if sgn < 0 else 'r'}",
            (pt[0] + sgn * 0.0135, pt[1], pt[2]),
            0.0026, 0.005, m_connector,
            rot=(0.0, math.radians(90), 0.0))
    mid_y = (trrs_l[1] + trrs_r[1]) / 2
    sag = ((trrs_l[0] + trrs_r[0]) / 2, mid_y, mat_top + 0.0010)
    cable("env_trrs_cable", [
        trrs_l,
        (trrs_l[0] + 0.010, mid_y - 0.006, mat_top + 0.0018),
        sag,
        (trrs_r[0] - 0.010, mid_y + 0.006, mat_top + 0.0018),
        trrs_r,
    ], 0.0014, m_cable)

    # USB-C: nano (left half, back rim) -> dock front port
    usb_exit_y = lb1[1] + 0.004
    usb_exit = (u0[0] + (u1[0] - u0[0]) * 0.5, usb_exit_y,
                min((u0[2] + u1[2]) / 2, mat_top + 0.0135))
    dock_port = (dock_x - 0.006, dock_y - 0.026, dock_z + 0.010)
    box("env_usbc_plug", (usb_exit[0], lb1[1] + 0.0025, usb_exit[2]),
        (0.010, 0.0075, 0.0042), m_connector, bevel=0.0012)
    cable("env_usbc_cable", [
        usb_exit,
        (usb_exit[0] + 0.030, usb_exit_y + 0.020, mat_top + 0.006),
        (dock_x - 0.070, dock_y + 0.010, desk_z + 0.004),
        dock_port,
    ], 0.0018, m_cable)
    # dock -> mini (short feed cable sagging on the desk)
    cable("env_dock_feed", [
        (dock_x + 0.010, dock_y + 0.024, dock_z + 0.010),
        (dock_x + 0.060, dock_y + 0.060, desk_z + 0.0025),
        (mini_x + 0.010, mini_y + 0.110, desk_z + 0.010),
    ], 0.0018, m_cable)

    # ---- environment lighting
    env_world()
    light("env_window", "AREA", 22, (cx - 1.05, cy - 0.28, 0.66),
          (cx, cy + 0.05, 0.04), color=(0.93, 0.95, 1.02), size=1.15)
    light("env_fill", "AREA", 7, (cx + 0.85, cy - 0.20, 0.30),
          (cx, cy + 0.05, 0.02), color=(1.0, 0.92, 0.80), size=0.70)

    # ---- cameras
    desk_cam = S.add_cam("env_desk", (cx + 0.10, cy - 1.45, 0.74),
                         (cx + 0.02, cy + 0.12, 0.05), lens=28)
    look = (cx + 0.02, cy - 0.035, 0.012)
    mat_cam = S.add_cam("env_mat", (cx - 0.33, cy - 0.42, 0.155),
                        look, lens=45)
    mat_cam.data.dof.use_dof = True
    mat_cam.data.dof.focus_distance = (
        mathutils.Vector(mat_cam.location) -
        mathutils.Vector(sag)).length
    mat_cam.data.dof.aperture_fstop = 2.6

    # ---- framecheck subjects: what must stay IN frame. The desk,
    # wall, baseboard and floor are backdrop and intentionally overflow
    # the frame edges; so do the far ends of the halves in the closeup.
    # desk: the whole keyboard + every prop (monitor, mini, mouse, cup,
    # pens, notebook, mug, lamp, dock, cables) + the mat itself
    backdrop = {"env_desk", "env_wall", "env_baseboard", "env_floor"}
    desk_subjects = (all_objs
                      + [o for o in PROPS if o.name not in backdrop]
                      + [mat])
    # mat closeup: the cables + their plugs/collars + the dock + the
    # caps around the seam
    near_caps = [o for h in parts for o in parts[h]["caps"]
                 if abs(o.matrix_world[0][3] - cx) < 0.100]
    mat_subjects = ([o for o in PROPS if o.name.startswith(
        ("env_trrs", "env_usbc", "env_dock"))] + near_caps)
    cams = {"desk": (desk_cam, desk_subjects),
            "mat": (mat_cam, mat_subjects)}
    if args.framecheck:
        for name, (cam, subj) in cams.items():
            if name in shots:
                S.frame_report(cam, subj, f"env_{name}", res)
        print("ENV-FRAMECHECK-DONE")
        return
    for name, (cam, subj) in cams.items():
        if name not in shots:
            continue
        S.render_to(cam, os.path.join(args.out, "env", f"{name}.png"),
                    res, args.samples, args.device)
    print("ENV-DONE")


main()

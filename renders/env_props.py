"""Hojicha44 environment props — Blender 5.2 headless (round 11).

HIGH-DETAIL desk props for the scene_env desk shots, replacing the
round-8 box/cyl/sphere stand-ins one file up. Every builder here is
pure geometry + procedural materials (no disk textures) and returns
its objects as a LIST — the caller (scene_env.py) collects them into
its PROPS registry; nothing is appended to module globals.

USAGE (from scene_env.py):
    import env_props as EP
    props += EP.build_mouse((x, y, desk_z), mats, rot_z=0.4)
    props += EP.build_lamp((lx, ly, desk_z), (ax, ay, desk_z), mats)

CONVENTIONS
  * `loc` is the prop's ground anchor — the desk contact point; parts
    are authored as (dx, dy, dz) offsets in the prop's local frame
    (+x right, +y toward the wall/monitor, +z up, front = -y) and the
    anchor helper yaws offsets + eulers so rot_z spins the whole prop
    about its anchor (R = Rz(rot_z) composed AFTER each part's local
    tilt, so local tilts stay local).
  * Sizes are real-world metres (~3 px/mm at 2400 px over the 1.5 m
    desk): a detail is only built when it survives that resolution —
    sub-0.3 mm features are left to noise bumps, everything else is
    real geometry (seams, slots, clips, knurling ridges).
  * `mats` is the caller's shared material dict; every key is probed
    and a sensible default (S.pbr, or a small procedural graph for
    speckle/brushed/mesh/page-edge/screen/glass) is built and cached
    back into the dict when missing — so the caller can pre-tune any
    look by just passing the key.

PROPS
  mouse     sculpted right-handed shell: vertex-level blend of an
            arch dome + left-flank thumb flare (the silhouette reads
            ergonomic even at desk-cam distance), separate button
            shells with a dark seam groove, notched rubber wheel
            yawed 10 deg, two thumb buttons, rear ridge
  mug       tapered stoneware, OPEN glaze cavity (bmesh cap removal)
            with coffee inside, oval-section torus handle, rim torus,
            a stamped ring motif of 26 clay ticks near the base
  notebook A5 hardcover: page block visible on the three open sides
            with a true ~0.3 mm sheet-line material, raised spine
            ridge, elastic strap, ribbon, embossed title block
  lamp      architect two-arm lamp aimed at a world point: rocker
            switch on the base rim, knuckle spheres, cone shade with
            inner rim ring, glossy emissive bulb, cable stub to +y
  minipc    generic brushed-alu squircle with vent grilles on both
            flanks, a back I/O row (USB-A x2, jack, USB-C pill, HDMI
            trapezoid, power inlet), front ports, debossed top circle
  monitor   27 in brand-free panel on an elaborate stand: wide foot,
            riser, dual-strut neck + hinge, quick-release plate hint,
            recessed screen, power LED, cable notch in the foot
  pens      three distinct pens (hex+wire clip, tapered+stamped clip,
            knurled grip+stepped cap), separate cap/clip geometry
  tower     mid-tower for a future scene: open-window body (the +x
            face is deleted so the glass shows a real cavity), three
            RGB fan rings + hubs + blades inside, mesh front
"""
import bpy
import bmesh
import math

import mathutils

import scene as S     # import-safe (guarded main)


# ---------------------------------------------------------- shared helpers

def _yaw(off, rz):
    """Rotate a prop-local offset about the anchor's vertical axis."""
    c, s = math.cos(rz), math.sin(rz)
    return (off[0] * c - off[1] * s, off[0] * s + off[1] * c, off[2])


def _M(mats, key, build):
    """mats[key], or build() the default and cache it back in."""
    m = mats.get(key)
    if m is None:
        m = mats[key] = build()
    return m


def _land(loc, rz, off):
    """World location of a prop-local offset."""
    p = _yaw(off, rz)
    return (loc[0] + p[0], loc[1] + p[1], loc[2] + p[2])


def _box(name, loc, rz, off, size, mat, rot=(0.0, 0.0, 0.0), bevel=None):
    """Cube scaled to `size` (metres) at a yawed offset. With `bevel`
    the non-uniform scale is baked into the mesh first — the bevel
    width is LOCAL-space, so without baking it a 9 mm chamfer on a
    196 mm box would silently render at 1.8 mm (the round-8 trap)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(size)
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
        bm = o.modifiers.new("bev", "BEVEL")
        bm.width, bm.segments = bevel, 4
    S.assign([o], mat)
    return o


def _cyl(name, loc, rz, off, r, depth, mat, rot=(0.0, 0.0, 0.0), verts=32,
         smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r,
                                        depth=depth,
                                        location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _cone(name, loc, rz, off, r1, r2, depth, mat, rot=(0.0, 0.0, 0.0),
          verts=32, smooth=True):
    """Truncated cone; r1 sits on the -z end, r2 on +z (before rot)."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth,
                                    location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _sph(name, loc, rz, off, scale, mat, rot=(0.0, 0.0, 0.0), segs=48,
         rings=24):
    """UV sphere as an ellipsoid via object scale (bmesh edits run in
    the unit-sphere local frame and are scaled for free)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings,
                                          radius=1,
                                          location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(scale)
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _tor(name, loc, rz, off, R, r, mat, rot=(0.0, 0.0, 0.0), scale=None,
         minor=12):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                      minor_segments=minor,
                                      location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    if scale is not None:
        o.scale = tuple(scale)
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _tube(name, a, b, r, mat, verts=24):
    """World-space strut between two points (lamp arms)."""
    va, vb = mathutils.Vector(a), mathutils.Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r,
                                        depth=(vb - va).length,
                                        location=((va + vb) / 2)[:])
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (vb - va).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _cable(name, pts, r, mat):
    """Rubber cable stub: bezier + round bevel (scene_env's pattern).
    NOTE S.assign skips non-MESH objects, so the material goes onto
    the curve data directly — scene_env's cables render grey because
    of exactly that skip."""
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
    ob.data.materials.append(mat)
    return ob


def _bmesh_edit(o, fn):
    """Run fn(bm) on the object's mesh (vertex-level sculpting)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    fn(bm)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def _open_top_cone(name, center, r1, r2, depth, mat, verts=48):
    """Truncated cone with the +z cap DELETED — a real cavity whose
    inner wall is visible, not a layered fake."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=center)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()

    def cut(bm):
        caps = [f for f in bm.faces if f.normal.z > 0.5]
        bmesh.ops.delete(bm, geom=caps, context="FACES")
    _bmesh_edit(o, cut)
    S.assign([o], mat)
    return o


# -------------------------------------------------- procedural materials

def _emit(name, color, strength, rough=0.25):
    """Principled emission (socket renamed across Blender 4/5)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    for key in ("Emission", "Emission Color"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = (*color, 1.0)
            break
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _probe_set(bsdf, key, value):
    """Set a Principled input when this build has it (Coat sockets
    and Alpha are probed, never assumed)."""
    try:
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
            return True
    except Exception:
        pass
    return False


def _coat(mat, weight, rough):
    _probe_set(mat.node_tree.nodes["Principled BSDF"], "Coat Weight", weight)
    _probe_set(mat.node_tree.nodes["Principled BSDF"], "Coat Roughness",
               rough)
    return mat


def _speckle_mat(name, base, speck, rough=0.58, scale=110.0):
    """Speckled stoneware: one thresholded noise drives sparse dark
    flecks in colour AND bump (the ~1 mm glaze specks a real mug
    shows at 3 px/mm)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.70, (*base, 1.0)
    e[1].position, e[1].color = 0.80, (*speck, 1.0)
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.12
    bmp.inputs["Distance"].default_value = 0.000015
    L = nt.links.new
    L(tc.outputs["Generated"], nz.inputs["Vector"])
    L(nz.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L(nz.outputs["Fac"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _brushed_mat(name, color, rough, metal=1.0):
    """Brushed alu: one noise stretched ~60:1 along the depth axis
    (streaks ~0.6 mm wide across x/z on the 196 mm body) drives a
    whisper of bump and the roughness break-up that makes extruded
    cases read machined."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (300.0, 5.0, 5.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 2.0
    nz.inputs["Roughness"].default_value = 0.45
    rr = nt.nodes.new("ShaderNodeValToRGB")
    e = rr.color_ramp.elements
    e[0].position, e[0].color = 0.0, (rough - 0.05,) * 3 + (1.0,)
    e[1].position, e[1].color = 1.0, (rough + 0.04,) * 3 + (1.0,)
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.08
    bmp.inputs["Distance"].default_value = 0.000006
    L = nt.links.new
    L(tc.outputs["Generated"], mp.inputs["Vector"])
    L(mp.outputs["Vector"], nz.inputs["Vector"])
    L(nz.outputs["Fac"], rr.inputs["Fac"])
    L(rr.outputs["Color"], bsdf.inputs["Roughness"])
    L(nz.outputs["Fac"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    return mat


def _mesh_grille_mat(name, base=(0.032, 0.034, 0.038)):
    """Fine mesh front: two crossed wave systems multiplied into a
    diamond grid (~3 mm cells on the 442 mm plate — resolves at
    3 px/mm as perforated steel, not stripes)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wx = nt.nodes.new("ShaderNodeTexWave")
    wx.wave_type, wx.bands_direction = "BANDS", "X"
    wx.inputs["Scale"].default_value = 150.0
    wx.inputs["Distortion"].default_value = 0.15
    wy = nt.nodes.new("ShaderNodeTexWave")
    wy.wave_type, wy.bands_direction = "BANDS", "Y"
    wy.inputs["Scale"].default_value = 150.0
    wy.inputs["Distortion"].default_value = 0.15
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.50
    bmp.inputs["Distance"].default_value = 0.0003
    L = nt.links.new
    L(tc.outputs["Generated"], wx.inputs["Vector"])
    L(tc.outputs["Generated"], wy.inputs["Vector"])
    L(wx.outputs["Fac"], mult.inputs[0])
    L(wy.outputs["Fac"], mult.inputs[1])
    L(mult.outputs["Value"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.48
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _page_edge_mat(name):
    """Notebook page block: wave bands along the stack axis at ~34
    periods over the 10.4 mm block = true ~0.3 mm sheets, noise-
    distorted so the lines waver like a hand-stack, a per-sheet
    brightness jitter, warm paper white. One material covers all
    three open sides (generated space, the scene_env convention)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type, wave.bands_direction = "BANDS", "Z"
    wave.inputs["Scale"].default_value = 34.0
    wave.inputs["Distortion"].default_value = 0.35
    wave.inputs["Detail"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "B_SPLINE"
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0.800, 0.775, 0.720, 1.0)
    e[1].position, e[1].color = 1.0, (0.885, 0.865, 0.815, 1.0)
    mp_lo = nt.nodes.new("ShaderNodeMapping")
    mp_lo.inputs["Scale"].default_value = (3.0, 3.0, 0.05)
    jit = nt.nodes.new("ShaderNodeTexNoise")
    jit.inputs["Scale"].default_value = 2.0
    jr = nt.nodes.new("ShaderNodeValToRGB")
    jr.color_ramp.interpolation = "B_SPLINE"
    je = jr.color_ramp.elements
    je[0].position, je[0].color = 0.28, (0.93, 0.93, 0.93, 1.0)
    je[1].position, je[1].color = 0.75, (1.05, 1.05, 1.04, 1.0)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.10
    bmp.inputs["Distance"].default_value = 0.00006
    fib = nt.nodes.new("ShaderNodeTexNoise")
    fib.inputs["Scale"].default_value = 1600.0
    fib.inputs["Detail"].default_value = 4.0
    fr = nt.nodes.new("ShaderNodeValToRGB")
    fe = fr.color_ramp.elements
    fe[0].position, fe[0].color = 0.0, (0.78, 0.78, 0.78, 1.0)
    fe[1].position, fe[1].color = 1.0, (0.90, 0.90, 0.90, 1.0)
    L = nt.links.new
    L(gen, wave.inputs["Vector"])
    L(wave.outputs["Fac"], ramp.inputs["Fac"])
    L(gen, mp_lo.inputs["Vector"])
    L(mp_lo.outputs["Vector"], jit.inputs["Vector"])
    L(jit.outputs["Fac"], jr.inputs["Fac"])
    L(ramp.outputs["Color"], mix.inputs["Color1"])
    L(jr.outputs["Color"], mix.inputs["Color2"])
    L(mix.outputs["Color"], bsdf.inputs["Base Color"])
    L(wave.outputs["Fac"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    L(gen, fib.inputs["Vector"])
    L(fib.outputs["Fac"], fr.inputs["Fac"])
    L(fr.outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _screen_mat(name):
    """Dark desktop: vertical gradient + soft emission so it reads
    on, gloss for the window reflection (scene_env's look, built
    locally so the default needs nothing from other modules)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "LINEAR"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.05, (0.006, 0.007, 0.010, 1.0)
    e[1].position, e[1].color = 0.95, (0.016, 0.021, 0.030, 1.0)
    L = nt.links.new
    L(tc.outputs["Generated"], grad.inputs["Vector"])
    L(grad.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    for key in ("Emission", "Emission Color"):
        if key in bsdf.inputs:
            L(ramp.outputs["Color"], bsdf.inputs[key])
            break
    bsdf.inputs["Emission Strength"].default_value = 0.10
    bsdf.inputs["Roughness"].default_value = 0.045
    bsdf.inputs["Metallic"].default_value = 0.0
    for _k, _v in (("Coat Weight", 0.65), ("Coat Roughness", 0.04),
                   ("Specular IOR Level", 0.55)):
        if _k in bsdf.inputs:
            bsdf.inputs[_k].default_value = _v
    return mat


def _glass_mat(name, base, alpha, coat_w=0.9, coat_r=0.04):
    """Tempered-glass panel: near-black, high low-roughness coat for
    the room reflection, sub-1 Alpha so the RGB fans behind it glow
    through — an opaque panel would hide exactly what it exists to
    show."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.05
    bsdf.inputs["Metallic"].default_value = 0.0
    _probe_set(bsdf, "Alpha", alpha)
    _probe_set(bsdf, "Coat Weight", coat_w)
    _probe_set(bsdf, "Coat Roughness", coat_r)
    return mat


# ------------------------------------------------------------- the props

def build_mouse(loc, mats, rot_z=0.0):
    """Sculpted ergonomic RIGHT-HANDED mouse (~113 x 62 x 38 mm).

    The shell is a 48x24 sphere sculpted in bmesh — a gaussian blend
    of three forms: a rear-right arch dome (where a right palm sits),
    a left-flank thumb-flare bulge, and a front pinch the buttons
    land on, plus a rear ridge and a flattened base. Two separate
    button ellipsoids with a 2 mm dark seam groove, a yawed rubber
    wheel with 7 notch rings, two thumb buttons on the flare. At
    desk-cam distance the ASYMMETRIC silhouette is what reads
    "ergonomic mouse", not "squashed sphere"."""
    rz = rot_z
    m_body = _M(mats, "mouse_body", lambda: S.micro_texture(
        S.pbr("mouse_body", (0.155, 0.150, 0.148), rough=0.52),
        240, 0.18, 0.00002, 0.46, 0.58))
    m_seam = _M(mats, "mouse_seam", lambda: S.micro_texture(
        S.pbr("mouse_seam", (0.095, 0.095, 0.100), rough=0.65),
        200, 0.22, 0.00003, 0.58, 0.72))
    m_wheel = _M(mats, "mouse_wheel", lambda: S.micro_texture(
        S.pbr("mouse_wheel", (0.028, 0.028, 0.030), rough=0.72),
        500, 0.30, 0.00004, 0.65, 0.82, detail=4.0))
    objs = []

    # --- palm shell (unit sphere; scale at the bottom turns the unit
    # coords into the 61 x 107 x 38 mm silhouette). All z edits stay
    # on the TOP half and the base is clamped at -0.75, so the pad
    # sits exactly on the desk (a global z scale would push it under)
    shell = _sph("mp_shell", loc, rz, (0.0, 0.0, 0.0144),
                 (0.0300, 0.0535, 0.0192), m_body)

    def sculpt(bm):
        for v in bm.verts:
            x, y, z = v.co.x, v.co.y, v.co.z
            # thumb flare: left flank bulges outward and dips — the
            # shelf a right thumb rides on (<= +13% = ~4 mm)
            if x < -0.2:
                t = min(1.0, (-x - 0.2) / 0.8)
                fy = math.exp(-(((y - 0.02) / 0.52) ** 2))
                push = 0.13 * t * fy
                x *= (1.0 + push)
                z *= (1.0 - 0.55 * push)
            if z > 0.0:
                # right-hand arch: dome centred rear-right of centre
                a = math.exp(-(((x - 0.28) / 0.42) ** 2
                               + ((y - 0.08) / 0.50) ** 2))
                z *= (1.0 + 0.16 * a)
                # front pinch: nose drops toward the buttons
                if y < -0.35:
                    z *= (1.0 - 0.24 * min(1.0, (-y - 0.35) / 0.65))
                # rear ridge: subtle raised spine at the back centre
                r = math.exp(-((x / 0.16) ** 2)) * max(0.0, y - 0.62) / 0.38
                z += 0.06 * r
            # flat base pad (bottom never seen, but the contact
            # shadow stays tight instead of the sphere's point)
            if z < -0.75:
                z = -0.75 + (z + 0.75) * 0.25
                if z < -0.75:
                    z = -0.75
            v.co = (x, y, z)
    _bmesh_edit(shell, sculpt)
    objs.append(shell)

    # --- two separate button shells on the pinched front slope,
    # tilted rot_x so the front edge dips (the finger rest)
    for sgn, tag in ((-1.0, "L"), (1.0, "R")):
        objs.append(_sph(f"mp_btn_{tag}", loc, rz,
                         (sgn * 0.0135, -0.0345, 0.0245),
                         (0.0125, 0.0205, 0.0072), m_body,
                         rot=(0.10, 0.0, 0.0)))
    # center seam groove: dark floor in the 2 mm gap between the
    # buttons — the read as "two buttons" is this shadow line
    objs.append(_box("mp_seam", loc, rz, (0.0, -0.0345, 0.0240),
                     (0.0022, 0.0400, 0.0040), m_seam, rot=(0.10, 0.0, 0.0)))

    # --- rubber scroll wheel: yawed 10 deg in plan (the ergonomic
    # rake), poking through a dark slot floor
    wa = math.radians(10.0)
    objs.append(_box("mp_wheelwell", loc, rz, (0.0, -0.0205, 0.0284),
                     (0.0085, 0.0190, 0.0012), m_seam,
                     rot=(0.10, 0.0, wa)))
    objs.append(_cyl("mp_wheel", loc, rz, (0.0, -0.0205, 0.0250),
                    0.0093, 0.0070, m_wheel, rot=(0.0, math.pi / 2, wa),
                    verts=40))
    # fine notch rings: 7 tread tori spaced 1.1 mm along the axle —
    # at 3 px/mm they read as the grippy rubber tread
    for k in range(-3, 4):
        objs.append(_tor(f"mp_wrng_{k + 3}", loc, rz,
                         (math.cos(wa) * k * 0.0011,
                          -0.0205 + math.sin(wa) * k * 0.0011, 0.0250),
                         0.00945, 0.00045, m_wheel,
                         rot=(0.0, math.pi / 2, wa), minor=8))

    # --- two thumb buttons on the flare, tilted onto the flank
    for i, ty in enumerate((-0.004, 0.011)):
        objs.append(_box(f"mp_thumb{i}", loc, rz, (-0.0335, ty, 0.0155),
                         (0.0022, 0.0160, 0.0070), m_body,
                         rot=(0.0, -0.10, -0.14), bevel=0.0008))
    return objs


def build_mug(loc, mats):
    """Unique ceramic mug (~O82 x 96 mm): tapered stoneware body with
    a real open glaze cavity (coffee sits 12 mm down inside it), an
    oval-section torus handle arc, a rim torus, and a stamped ring
    motif of 26 clay ticks near the base — the motif is what makes
    it read handmade rather than shop-bought."""
    m_out = _M(mats, "mug_outer", lambda: _speckle_mat(
        "mug_outer", (0.72, 0.66, 0.56), (0.15, 0.13, 0.11),
        rough=0.58, scale=110.0))
    m_in = _M(mats, "mug_glaze", lambda: _coat(
        S.pbr("mug_glaze", (0.075, 0.16, 0.155), rough=0.14), 0.55, 0.09))
    m_cof = _M(mats, "mug_coffee", lambda: S.pbr(
        "mug_coffee", (0.045, 0.026, 0.014), rough=0.06))
    m_mot = _M(mats, "mug_motif", lambda: S.pbr(
        "mug_motif", (0.42, 0.36, 0.28), rough=0.62))
    objs = []

    # tapered body: 73 mm base -> 82 mm rim
    objs.append(_cone("mug_body", loc, 0.0, (0.0, 0.0, 0.048),
                      0.0365, 0.041, 0.096, m_out, verts=64))
    # inner glaze cavity: open-topped cone, glossy teal glaze; its
    # visible wall + the coffee depth is what sells "mug" at any
    # angle rather than a disc glued on a cylinder
    objs.append(_open_top_cone("mug_cavity",
                               (loc[0], loc[1], loc[2] + 0.047),
                               0.0305, 0.0360, 0.086, m_in, verts=64))
    objs.append(_tor("mug_rim", loc, 0.0, (0.0, 0.0, 0.0952),
                     0.0395, 0.0022, m_out, minor=16))
    objs.append(_cyl("mug_coffee", loc, 0.0, (0.0, 0.0, 0.082),
                     0.0345, 0.0016, m_cof))

    # handle: torus rotated upright, tube stretched 1.45x along the
    # local axis (= world front-back) -> oval strap cross-section
    # 8.4 x 12.2 mm; the near arc clears the cavity wall
    objs.append(_tor("mug_handle", loc, 0.0, (0.055, 0.0, 0.0585),
                     0.0165, 0.0042, m_out, rot=(math.pi / 2, 0.0, 0.0),
                     scale=(1.0, 1.0, 1.45), minor=16))

    # stamped geometric ring motif: 26 raised clay ticks 17 mm up
    # the wall, each rotated to lie tangentially — reads as a maker's
    # stamp band, cheap (26 boxes) and very legible
    rh = 0.0365 + (0.041 - 0.0365) * (0.017 / 0.096) + 0.0004
    for i in range(26):
        a = 2 * math.pi * i / 26
        objs.append(_box(f"mug_mot{i}", loc, 0.0,
                         (math.cos(a) * rh, math.sin(a) * rh, 0.017),
                         (0.0012, 0.0056, 0.0034), m_mot, rot=(0.0, 0.0, a),
                         bevel=0.0004))
    return objs


def build_notebook(loc, mats, rot_z=0.0):
    """A5 hardcover (~148 x 210 x 14 mm) lying closed.

    Layered like the real object: two 1.8 mm cover boards overhang a
    10.4 mm page block, so the PAGES are genuinely visible on the
    three open sides (fore-edge + both ends), wearing a sheet-line
    material with a true ~0.3 mm pitch. The spine is a raised rounded
    ridge (the case wrap), the elastic strap wraps the whole book,
    the ribbon lies over the top board, and a darker title block
    stands 0.7 mm proud — no text, just the debossed rectangle."""
    rz = rot_z
    m_cover = _M(mats, "nb_cover", lambda: S.micro_texture(
        S.pbr("nb_cover", (0.130, 0.115, 0.100), rough=0.60),
        130, 0.20, 0.00004, 0.52, 0.66))
    m_spine = _M(mats, "nb_spine", lambda: S.micro_texture(
        S.pbr("nb_spine", (0.105, 0.093, 0.082), rough=0.55),
        130, 0.20, 0.00004, 0.48, 0.62))
    m_pages = _M(mats, "nb_pages", lambda: _page_edge_mat("nb_pages"))
    m_strap = _M(mats, "nb_strap", lambda: S.micro_texture(
        S.pbr("nb_strap", (0.035, 0.036, 0.040), rough=0.80),
        400, 0.25, 0.00004, 0.72, 0.88, detail=4.0))
    m_ribbon = _M(mats, "nb_ribbon", lambda: S.micro_texture(
        S.pbr("nb_ribbon", (0.42, 0.08, 0.10), rough=0.70),
        300, 0.30, 0.00005, 0.62, 0.80, detail=4.0))
    m_title = _M(mats, "nb_title", lambda: S.pbr(
        "nb_title", (0.085, 0.075, 0.068), rough=0.45))
    objs = []

    # cover boards (rounded corners) overhang the page block by
    # 3.5 mm on the three open sides — the visible page recess
    objs.append(_box("nb_board_b", loc, rz, (0.0, 0.0, 0.0009),
                     (0.148, 0.210, 0.0018), m_cover, bevel=0.0025))
    objs.append(_box("nb_pages", loc, rz, (0.0, 0.0, 0.0070),
                     (0.141, 0.204, 0.0104), m_pages, bevel=0.0008))
    objs.append(_box("nb_board_t", loc, rz, (0.0, 0.0, 0.0131),
                     (0.148, 0.210, 0.0018), m_cover, bevel=0.0025))
    # spine ridge: proud of the boards on the closed long edge (-x),
    # slightly wrapped past the ends
    objs.append(_box("nb_spine", loc, rz, (-0.0703, 0.0, 0.0076),
                     (0.0075, 0.2115, 0.0152), m_spine, bevel=0.0025))
    # elastic closure strap: runs the full height (proud 0.7 mm on
    # top) and wraps both ends, 22 mm in from the fore-edge
    objs.append(_box("nb_strap", loc, rz, (0.052, 0.0, 0.00735),
                     (0.011, 0.2155, 0.0147), m_strap))
    # ribbon bookmark tail over the top board, angled off the spine
    objs.append(_box("nb_ribbon", loc, rz, (-0.052, 0.062, 0.0144),
                     (0.009, 0.048, 0.0008), m_ribbon,
                     rot=(0.0, 0.0, 0.35)))
    # embossed title block (no text): a 0.7 mm proud darker rectangle
    # centred on the top board
    objs.append(_box("nb_title", loc, rz, (0.008, -0.010, 0.01435),
                     (0.058, 0.082, 0.0007), m_title, bevel=0.0006))
    return objs


def build_lamp(loc, aim, mats):
    """Architect desk lamp aimed at a world point.

    `loc` = base centre on the desk, `aim` = the point the head
    lights. The head is placed up and slightly back along the
    base->aim line, the elbow rises off the chord — the classic two-
    knuckle scissor arc, computed for any aim. The base carries a
    rocker switch (beveled plate + tilted nub), the shade is a cone
    with an inner rim ring and a real glossy emissive bulb inside,
    and a rubber cable stub leaves the base toward +y (the wall)."""
    m_body = _M(mats, "lamp_body", lambda: S.micro_texture(
        S.pbr("lamp_body", (0.020, 0.021, 0.023), rough=0.42),
        180, 0.16, 0.00003, 0.36, 0.48))
    m_nub = _M(mats, "lamp_nub", lambda: S.pbr(
        "lamp_nub", (0.11, 0.11, 0.115), rough=0.35))
    m_bulb = _M(mats, "lamp_bulb", lambda: _emit(
        "lamp_bulb", (1.0, 0.76, 0.47), 5.0, rough=0.12))
    m_cable = _M(mats, "lamp_cable", lambda: S.micro_texture(
        S.pbr("lamp_cable", (0.026, 0.027, 0.030), rough=0.46),
        900, 0.30, 0.00006, 0.38, 0.55, detail=5.0))
    objs = []
    lx, ly, lz = loc

    # base disc + rocker switch on the front rim (rocked position =
    # nub tipped toward one end)
    objs.append(_cyl("lamp_base", loc, 0.0, (0.0, 0.0, 0.0075),
                     0.052, 0.015, m_body, verts=48))
    objs.append(_box("lamp_rocker", loc, 0.0, (0.024, -0.044, 0.0172),
                     (0.018, 0.0095, 0.0045), m_body, bevel=0.0012))
    objs.append(_box("lamp_nub", loc, 0.0, (0.027, -0.044, 0.0208),
                     (0.0055, 0.004, 0.0026), m_nub, rot=(-0.20, 0.0, 0.0)))

    # ---- the arm chain, solved in world space for the given aim
    back = mathutils.Vector((lx - aim[0], ly - aim[1], 0.0))
    if back.length < 1e-6:
        back = mathutils.Vector((0.0, 1.0, 0.0))
    back.normalize()
    BJ = mathutils.Vector((lx, ly, lz + 0.0235))
    H = (mathutils.Vector(aim) + back * 0.115
         + mathutils.Vector((0.0, 0.0, 0.13)))       # head centre
    E = (BJ + H) / 2 + mathutils.Vector((0.0, 0.02, 0.05))   # elbow
    shade_dir = (mathutils.Vector(aim) - H).normalized()
    SN = H - shade_dir * 0.030                # shade back / neck joint

    objs.append(_sph("lamp_joint_b", (BJ.x, BJ.y, BJ.z), 0.0,
                     (0.0, 0.0, 0.0), (0.011, 0.011, 0.011), m_body))
    objs.append(_sph("lamp_joint_e", (E.x, E.y, E.z), 0.0,
                     (0.0, 0.0, 0.0), (0.0095, 0.0095, 0.0095), m_body))
    objs.append(_sph("lamp_joint_n", (SN.x, SN.y, SN.z), 0.0,
                     (0.0, 0.0, 0.0), (0.008, 0.008, 0.008), m_body))
    objs.append(_tube("lamp_arm1", BJ, E, 0.0052, m_body))
    objs.append(_tube("lamp_arm2", E, SN, 0.0052, m_body))

    # shade: -z end (the wide radius1 opening) tracks the aim
    C = H + shade_dir * 0.042
    track = (mathutils.Vector(aim) - C).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.054,
                                    radius2=0.021, depth=0.088,
                                    location=C)
    shade = bpy.context.active_object
    shade.name = "lamp_shade"
    shade.rotation_euler = track
    bpy.ops.object.shade_smooth()
    S.assign([shade], m_body)
    objs.append(shade)
    # inner rim ring at the opening (the rolled edge real shades have)
    objs.append(_tor("lamp_rim", (H.x + shade_dir.x * 0.003,
                                  H.y + shade_dir.y * 0.003,
                                  H.z + shade_dir.z * 0.003), 0.0,
                     (0.0, 0.0, 0.0), 0.0535, 0.0021, m_body,
                     rot=(track.x, track.y, track.z), minor=16))
    # the bulb: small glossy emissive warm sphere inside the shade
    objs.append(_sph("lamp_bulb", (H.x + shade_dir.x * 0.014,
                                   H.y + shade_dir.y * 0.014,
                                   H.z + shade_dir.z * 0.014), 0.0,
                     (0.0, 0.0, 0.0), (0.0115, 0.0115, 0.0115), m_bulb))

    # power cable stub: exits the base rim toward +y (the wall) and
    # sags to the desk before running off
    objs.append(_cable("lamp_cable", [
        (lx + 0.020, ly + 0.050, lz + 0.006),
        (lx + 0.008, ly + 0.092, lz + 0.002),
        (lx + 0.010, ly + 0.150, lz + 0.0015),
    ], 0.0021, m_cable))
    return objs


def build_minipc(loc, mats):
    """Generic mini desktop PC, 196 x 196 x 38 mm (no brand, no
    logo): brushed-alu squircle (11 mm bevel reads as the rounded
    case at any distance), 12-slot vent grilles on BOTH flanks, a
    back I/O row (2x USB-A, round jack, USB-C pill, HDMI trapezoid,
    power inlet) as shallow dark insets, front USB-C x2 + headphone,
    and a debossed circle on the top (dark disc + light rim)."""
    m_body = _M(mats, "pc_body", lambda: _brushed_mat(
        "pc_body", (0.55, 0.56, 0.585), 0.30, metal=1.0))
    m_inset = _M(mats, "pc_inset", lambda: S.micro_texture(
        S.pbr("pc_inset", (0.030, 0.031, 0.034), rough=0.40),
        140, 0.12, 0.00003, 0.35, 0.45))
    objs = []

    body = _box("pc_body", loc, 0.0, (0.0, 0.0, 0.019),
                (0.196, 0.196, 0.038), m_body, bevel=0.011)
    objs.append(body)

    # side vent grilles: 2 columns x 6 rows of thin dark slots per
    # flank, flush-mounted — reads as a stamped grille, not stickers
    for sx in (-1.0, 1.0):
        for ci, cy in enumerate((-0.048, 0.048)):
            for ri in range(6):
                objs.append(_box(
                    f"pc_vent_{int(sx>0)}{ci}{ri}", loc, 0.0,
                    (sx * 0.0975, cy, 0.0092 + ri * 0.0042),
                    (0.0013, 0.052, 0.0021), m_inset))

    # ---- back I/O (+y face): shallow dark insets
    z = 0.019
    for i, px in enumerate((-0.062, -0.042)):        # 2x USB-A
        objs.append(_box(f"pc_usba_{i}", loc, 0.0, (px, 0.0975, z),
                         (0.0125, 0.0009, 0.0056), m_inset))
    objs.append(_cyl("pc_jack", loc, 0.0, (-0.018, 0.0972, z),
                     0.0034, 0.0012, m_inset, rot=(math.pi / 2, 0.0, 0.0)))
    objs.append(_box("pc_usbc_b", loc, 0.0, (0.004, 0.0975, z),
                     (0.0092, 0.0009, 0.0032), m_inset, bevel=0.0013))
    # HDMI: a real trapezoid — the top edge pulled in 24% by a bmesh
    # taper (runs under the bevel, so the slanted faces stay crisp)
    hdmi = _box("pc_hdmi", loc, 0.0, (0.026, 0.0975, z),
                (0.0152, 0.0009, 0.0075), m_inset, bevel=0.0006)

    def taper(bm):
        zs = [v.co.z for v in bm.verts]
        z0, z1 = min(zs), max(zs)
        for v in bm.verts:
            v.co.x *= 1.0 - 0.24 * (v.co.z - z0) / (z1 - z0)
    _bmesh_edit(hdmi, taper)
    objs.append(hdmi)
    objs.append(_box("pc_power", loc, 0.0, (0.049, 0.0975, z),
                     (0.0105, 0.0009, 0.0048), m_inset, bevel=0.0012))
    objs.append(_cyl("pc_power_pin", loc, 0.0, (0.049, 0.0968, z),
                     0.0014, 0.0008, m_inset, rot=(math.pi / 2, 0.0, 0.0)))

    # ---- front (-y): 2 USB-C pills + headphone circle
    for i, px in enumerate((-0.009, 0.009)):
        objs.append(_box(f"pc_usbc_f_{i}", loc, 0.0, (px, -0.0975, z),
                         (0.0092, 0.0009, 0.0032), m_inset, bevel=0.0013))
    objs.append(_cyl("pc_hp", loc, 0.0, (0.033, -0.0972, z),
                     0.0023, 0.0012, m_inset, rot=(math.pi / 2, 0.0, 0.0)))

    # ---- debossed circle on the top: dark disc + a raised body-
    # material rim ring that catches light like the deboss edge
    objs.append(_cyl("pc_topdisc", loc, 0.0, (0.0, 0.0, 0.03825),
                     0.0335, 0.0005, m_inset, rot=(0.0, 0.0, 0.0)))
    objs.append(_tor("pc_toprim", loc, 0.0, (0.0, 0.0, 0.03835),
                     0.0342, 0.0007, m_body))

    S.smooth([body], 40.0)      # bevel arcs rounded, faces stay flat
    return objs


def build_monitor(loc, mats):
    """27 in brand-free monitor (~615 x 365 x 14 mm panel) on an
    ELABORATE stand: wide flat foot + riser block, dual-link neck
    (two slender struts either side of a hinge cylinder), a quick-
    release plate hint on the panel back, recessed dark screen with
    a thin bezel, power LED bottom-right, and a cable-management
    notch strip in the foot. Faces -y (the user)."""
    m_body = _M(mats, "mon_body", lambda: S.micro_texture(
        S.pbr("mon_body", (0.32, 0.33, 0.35), rough=0.40, metal=0.9),
        260, 0.08, 0.00001, 0.34, 0.44))
    m_bezel = _M(mats, "mon_bezel", lambda: S.micro_texture(
        S.pbr("mon_bezel", (0.028, 0.029, 0.032), rough=0.32),
        220, 0.10, 0.00002, 0.28, 0.38))
    m_scr = _M(mats, "mon_screen", lambda: _screen_mat("mon_screen"))
    m_led = _M(mats, "mon_led", lambda: _emit(
        "mon_led", (0.70, 0.85, 1.0), 1.5))
    m_dark = _M(mats, "mon_dark", lambda: S.pbr(
        "mon_dark", (0.02, 0.02, 0.022), rough=0.45))
    objs = []
    rz = 0.0

    # ---- stand: foot plate, cable notch, riser, dual struts, hinge
    foot = _box("mon_foot", loc, rz, (0.0, 0.0, 0.0085),
                (0.280, 0.175, 0.017), m_body, bevel=0.006)
    objs.append(foot)
    objs.append(_box("mon_notch", loc, rz, (0.0, 0.058, 0.0178),
                     (0.036, 0.007, 0.0016), m_dark))
    riser = _box("mon_riser", loc, rz, (0.0, 0.030, 0.030),
                 (0.088, 0.052, 0.026), m_body, bevel=0.004)
    objs.append(riser)
    # two slender struts leaning back 4 deg, split by the hinge —
    # the dual-link neck reads engineered, not a slab
    for sx in (-1.0, 1.0):
        objs.append(_box(f"mon_strut_{int(sx > 0)}", loc, rz,
                         (sx * 0.020, 0.024, 0.118),
                         (0.0075, 0.026, 0.150), m_body,
                         rot=(-0.07, 0.0, 0.0)))
    objs.append(_cyl("mon_hinge", loc, rz, (0.0, 0.034, 0.196),
                     0.0155, 0.058, m_body, rot=(0.0, math.pi / 2, 0.0)))

    # ---- panel: thin-bezel slab, screen proud 0.2 mm, LED
    panel = _box("mon_panel", loc, rz, (0.0, 0.004, 0.3845),
                 (0.615, 0.0135, 0.365), m_bezel, bevel=0.003)
    objs.append(panel)
    objs.append(_box("mon_screen", loc, rz, (0.0, -0.00265, 0.3845),
                     (0.598, 0.0006, 0.347), m_scr))
    objs.append(_cyl("mon_led", loc, rz, (0.278, -0.0028, 0.2065),
                     0.0016, 0.0012, m_led, rot=(math.pi / 2, 0.0, 0.0)))
    # quick-release plate on the panel back + its release tab
    plate = _box("mon_qrplate", loc, rz, (0.0, 0.0152, 0.3745),
                (0.072, 0.009, 0.096), m_body, bevel=0.003)
    objs.append(plate)
    objs.append(_box("mon_qrtab", loc, rz, (0.0, 0.0227, 0.330),
                     (0.016, 0.006, 0.008), m_dark))

    S.smooth([foot, riser, panel, plate], 40.0)
    return objs


def build_pens(loc, mats, n=3):
    """Up to n pens (cycling 3 distinct designs, ~O11 x 140 mm),
    fanned side by side with slightly different yaws AND a small
    nose-up/down tilt each (the tilt rotates about the pen's own
    axis line, so no barrel dips below the desk).

      (a) hexagonal barrel, flat cap, thin wire clip + ball
      (b) tapered barrel, conical cap, wide stamped clip
      (c) round barrel, 12-ridge knurled grip band, stepped cap,
          angled clip

    Caps and clips are separate geometry, not painted on."""
    m_dark = _M(mats, "pen_dark", lambda: S.micro_texture(
        S.pbr("pen_dark", (0.085, 0.087, 0.095), rough=0.30),
        300, 0.08, 0.00002, 0.26, 0.34))
    m_white = _M(mats, "pen_white", lambda: S.micro_texture(
        S.pbr("pen_white", (0.85, 0.85, 0.84), rough=0.22),
        300, 0.08, 0.00002, 0.18, 0.26))
    m_copper = _M(mats, "pen_copper", lambda: S.micro_texture(
        S.pbr("pen_copper", (0.52, 0.33, 0.20), rough=0.32, metal=0.9),
        260, 0.08, 0.00002, 0.26, 0.36))
    m_metal = _M(mats, "pen_metal", lambda: S.micro_texture(
        S.pbr("pen_metal", (0.72, 0.73, 0.75), rough=0.24, metal=1.0),
        300, 0.06, 0.000015, 0.20, 0.28))
    m_grip = _M(mats, "pen_grip", lambda: S.micro_texture(
        S.pbr("pen_grip", (0.030, 0.031, 0.034), rough=0.75),
        700, 0.35, 0.00005, 0.68, 0.85, detail=4.0))
    objs = []
    Z = 0.0057          # barrel axis height (rebound per design below)
    HALFP = math.pi / 2
    # rest height = each design's fattest section, so the pen kisses
    # the desk instead of sinking; the rake always lifts the FAT
    # (cap) end, so the thin tip can never dig below the desk
    ZP = (0.0061, 0.0067, 0.0069)
    RAKE = (0.0, 0.01, 0.01)

    def _tip(anchor, rz, t, tf, r, mat, tag):
        """Shared writing end: shoulder cone + tiny ball point."""
        o1 = _cone(f"pen_tip_{tag}", anchor, rz, tf((0.0, -0.064, Z)),
                   r, 0.0010, 0.010, mat, rot=(HALFP + t, 0.0, 0.0))
        o2 = _sph(f"pen_point_{tag}", anchor, rz, tf((0.0, -0.069, Z)),
                  (0.0010, 0.0010, 0.0010), mat)
        return [o1, o2]

    for i in range(n):
        design = i % 3
        anchor = (loc[0] + (i - (n - 1) / 2.0) * 0.024, loc[1], loc[2])
        rz = math.radians((-10.0, 3.0, 14.0)[design] + 2.0 * i)
        Z = ZP[design]
        t = RAKE[design]
        st, ct = math.sin(t), math.cos(t)

        def tf(off, _st=st, _ct=ct):
            """Tilt the offset about the pen's axis line (through
            z = Z): the whole-pen rake, applied per part."""
            x, y, z = off
            z -= Z
            return (x, y * _ct - z * _st, y * _st + z * _ct + Z)

        if design == 0:
            # (a) hex barrel + flat cap + wire clip
            objs.append(_cyl(f"pen{i}_barrel", anchor, rz, tf((0, 0, Z)),
                             0.0056, 0.118, m_dark, rot=(HALFP + t, 0, 0),
                             verts=6))
            objs += _tip(anchor, rz, t, tf, 0.0056, m_dark, f"a{i}")
            objs.append(_cyl(f"pen{i}_cap", anchor, rz, tf((0, 0.0675, Z)),
                             0.0061, 0.017, m_dark, rot=(HALFP + t, 0, 0)))
            objs.append(_tor(f"pen{i}_capring", anchor, rz,
                             tf((0, 0.059, Z)), 0.0061, 0.0004, m_metal,
                             rot=(HALFP + t, 0, 0), minor=10))
            objs.append(_box(f"pen{i}_clip", anchor, rz,
                             tf((0, 0.061, 0.0125)),
                             (0.0012, 0.034, 0.0024), m_metal,
                             rot=(t, 0, 0)))
            objs.append(_sph(f"pen{i}_clipball", anchor, rz,
                             tf((0, 0.0775, 0.0125)),
                             (0.0013, 0.0013, 0.0013), m_metal))
        elif design == 1:
            # (b) tapered barrel + conical cap + stamped clip
            objs.append(_cone(f"pen{i}_barrel", anchor, rz, tf((0, 0, Z)),
                              0.0062, 0.0049, 0.118, m_white,
                              rot=(HALFP + t, 0, 0)))
            objs += _tip(anchor, rz, t, tf, 0.0049, m_white, f"b{i}")
            objs.append(_cone(f"pen{i}_cap", anchor, rz,
                             tf((0, 0.071, Z)), 0.0067, 0.0060, 0.024,
                             m_copper, rot=(HALFP + t, 0, 0)))
            objs.append(_box(f"pen{i}_clip", anchor, rz,
                            tf((0, 0.066, 0.0124)),
                            (0.0042, 0.036, 0.0011), m_copper,
                            rot=(t, 0, 0), bevel=0.0004))
            objs.append(_box(f"pen{i}_clipend", anchor, rz,
                            tf((0, 0.047, 0.0118)),
                            (0.0042, 0.006, 0.0011), m_copper,
                            rot=(0.35 + t, 0, 0)))
        else:
            # (c) round barrel + knurled grip + stepped cap + angled
            # clip; the 12 ridges are real 1 mm geometry — knurling
            # you can see, not a dark band
            objs.append(_cyl(f"pen{i}_barrel", anchor, rz, tf((0, 0, Z)),
                             0.0055, 0.118, m_copper, rot=(HALFP + t, 0, 0)))
            objs += _tip(anchor, rz, t, tf, 0.0055, m_copper, f"c{i}")
            objs.append(_cyl(f"pen{i}_grip", anchor, rz, tf((0, -0.047, Z)),
                             0.00575, 0.024, m_grip,
                             rot=(HALFP + t, 0, 0)))
            for k in range(12):
                a = math.pi * 2 * k / 12
                objs.append(_box(
                    f"pen{i}_knurl{k}", anchor, rz,
                    tf((math.cos(a) * 0.0062, -0.047,
                        Z + math.sin(a) * 0.0062)),
                    (0.0009, 0.024, 0.0011), m_grip, rot=(t, -a, 0.0)))
            for tag, ry in (("r0", -0.0585), ("r1", -0.0335)):
                objs.append(_tor(f"pen{i}_{tag}", anchor, rz,
                                 tf((0, ry, Z)), 0.0059, 0.00045, m_metal,
                                 rot=(HALFP + t, 0, 0), minor=10))
            objs.append(_cyl(f"pen{i}_cap", anchor, rz,
                             tf((0, 0.0635, Z)), 0.0062, 0.009, m_dark,
                             rot=(HALFP + t, 0, 0)))
            objs.append(_cyl(f"pen{i}_capstep", anchor, rz,
                             tf((0, 0.074, Z)), 0.0052, 0.012, m_dark,
                             rot=(HALFP + t, 0, 0)))
            objs.append(_box(f"pen{i}_clip", anchor, rz,
                            tf((0, 0.066, 0.0138)),
                            (0.0016, 0.030, 0.0026), m_metal,
                            rot=(0.16 + t, 0, 0)))
            objs.append(_sph(f"pen{i}_clipball", anchor, rz,
                             tf((0, 0.079, 0.0148)),
                             (0.0013, 0.0013, 0.0013), m_metal))
    return objs


def build_tower(loc, mats):
    """Mid-tower gaming PC (~210 x 455 x 465 mm) for a future scene.

    The body is a beveled box whose +x face is DELETED after the
    bevel is applied — a real open window, not a decal — so the
    tempered glass panel (near-black, high coat, Alpha 0.22) shows
    an actual cavity: dark interior plate, three RGB fans (glow
    ring + hub + 5 blades each) mounted 200 mm deep, just like the
    product renders. Mesh-textured front, top I/O dots, four feet.
    Brand-free."""
    m_case = _M(mats, "tower_case", lambda: S.micro_texture(
        S.pbr("tower_case", (0.045, 0.046, 0.050), rough=0.50),
        120, 0.15, 0.00003, 0.44, 0.56))
    m_int = _M(mats, "tower_interior", lambda: S.pbr(
        "tower_interior", (0.018, 0.018, 0.020), rough=0.70))
    m_glass = _M(mats, "tower_glass", lambda: _glass_mat(
        "tower_glass", (0.015, 0.024, 0.020), 0.22))
    m_mesh = _M(mats, "tower_mesh", lambda: _mesh_grille_mat("tower_mesh"))
    m_dark = _M(mats, "tower_dark", lambda: S.pbr(
        "tower_dark", (0.020, 0.020, 0.022), rough=0.50))
    m_led = _M(mats, "tower_pwrled", lambda: _emit(
        "tower_pwrled", (1.0, 0.85, 0.60), 2.0))
    # RGB rings: caller-provided "rgb1".."rgb3" or stock hues
    m_rgb = []
    for key, col in (("rgb1", (1.0, 0.08, 0.45)),
                     ("rgb2", (0.10, 0.85, 1.0)),
                     ("rgb3", (0.45, 0.15, 1.0))):
        m_rgb.append(_M(mats, key,
                        lambda c=col, k=key: _emit("tower_" + k, c, 3.0)))
    objs = []
    rz = 0.0

    # four rubber feet
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            objs.append(_box(f"tw_foot_{int(sx > 0)}{int(sy > 0)}", loc, rz,
                             (sx * 0.078, sy * 0.192, 0.006),
                             (0.016, 0.038, 0.012), m_dark))
    # body: bevel baked, then the +x face deleted -> the open glass
    # window (the wall's inner backfaces shade dark for free, which
    # is exactly what a case cavity looks like)
    body = _box("tw_body", loc, rz, (0.0, 0.0, 0.243),
                (0.208, 0.452, 0.462), m_case, bevel=0.007)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier="bev")

    def open_window(bm):
        win = [f for f in bm.faces
               if f.normal.x > 0.9 and f.calc_center_median().x > 0.10]
        bmesh.ops.delete(bm, geom=win, context="FACES")
    _bmesh_edit(body, open_window)
    objs.append(body)

    # interior plate the fans mount on — visible dark depth behind
    # the glow rings instead of a flat wall
    objs.append(_box("tw_intplate", loc, rz, (-0.0975, 0.0, 0.243),
                     (0.001, 0.430, 0.430), m_int))
    # three RGB fans near the front interior, rings facing the glass
    for j, fy in enumerate((-0.152, -0.034, 0.084)):
        objs.append(_tor(f"tw_rgb{j}", loc, rz, (-0.0925, fy, 0.243),
                         0.057, 0.0045, m_rgb[j],
                         rot=(0.0, math.pi / 2, 0.0), minor=16))
        objs.append(_cyl(f"tw_hub{j}", loc, rz, (-0.0935, fy, 0.243),
                         0.021, 0.006, m_dark, rot=(0.0, math.pi / 2, 0.0)))
        for k in range(5):
            a = math.pi * 2 * k / 5
            objs.append(_box(
                f"tw_blade{j}_{k}", loc, rz,
                (-0.0935, fy + math.cos(a) * 0.030,
                 0.243 + math.sin(a) * 0.030),
                (0.0012, 0.045, 0.014), m_dark, rot=(a, 0.0, 0.3)))
    # tempered glass in the window plane (Alpha lets the rings glow
    # through; the coat carries the room reflection)
    objs.append(_box("tw_glass", loc, rz, (0.104, 0.0, 0.243),
                     (0.0022, 0.424, 0.432), m_glass))
    # fine mesh front panel
    objs.append(_box("tw_front", loc, rz, (0.0, -0.2265, 0.243),
                     (0.196, 0.0012, 0.442), m_mesh))
    # top I/O near the front edge: power ring + glowing dot + 2 dots
    objs.append(_tor("tw_pwr_ring", loc, rz, (-0.060, -0.180, 0.4745),
                     0.0045, 0.0009, m_dark, minor=10))
    objs.append(_cyl("tw_pwr_dot", loc, rz, (-0.060, -0.180, 0.4750),
                     0.0018, 0.0008, m_led))
    for j, px in enumerate((-0.048, -0.036)):
        objs.append(_cyl(f"tw_io{j}", loc, rz, (px, -0.180, 0.4750),
                         0.0022, 0.0008, m_dark))

    S.smooth([body], 40.0)
    return objs

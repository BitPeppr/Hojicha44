"""Hojicha44 desk props — DETAIL PASS 2 (round 20), Blender 5.2 headless.

WHY THIS FILE EXISTS
    The round-19 desk render failed review on the small props: the mouse
    read as "a squashed sphere with a painted-on seam", the mug as "an
    amorphous bulbous blob" with no readable cavity, the pen holder was
    not hollow, and every prop looked untextured and 2-D. This module is
    the second, deeper pass: each prop is rebuilt from REAL forms (a
    sculpted shell with an authored silhouette profile, a wall you can
    see into, a rim with thickness, a page block with true sheet lines)
    so the shapes survive at 50 px, not just at 2400 px.

    Drop-in for the round-19 local builders in scene_env.py (add_mouse /
    add_mug / add_standing_pens) and env_props.py's build_notebook —
    nothing here edits those files; the main session swaps the calls.

CONVENTIONS (identical to env_props.py, so callers can swap them)
  * Every builder returns an OBJECT LIST; no module-level registry, so
    the caller stays in charge of what is collected and what is hidden.
  * `loc` is the prop's ground anchor (the desk contact point) and parts
    are authored as (dx, dy, dz) offsets in the prop's local frame
    (+x right, +y toward the wall/monitor, +z up, front = -y); the
    primitive helpers yaw the offset + the euler by `rot_z`, so rot_z
    spins the whole prop about its anchor and LOCAL tilts stay local
    (R = Rz(rot_z) composed AFTER each part's own rotation).
  * Sizes are real metres. The desk camera is ~3 px/mm, so a detail is
    only built when it survives that: sub-0.3 mm features are left to
    noise bumps, everything else is real geometry.
  * `mats` is the caller's shared dict. Each key is probed and a default
    (S.pbr / S.micro_texture / a small procedural graph) is built and
    cached back into the dict when absent — so a caller that wants to
    pre-tune the look just passes the key (the key names match the ones
    scene_env.py and env_props.py already use, e.g. "ms_body",
    "mug_glaze", "nb_pages", so their materials are picked up as-is).
  * Zero disk textures: every surface is procedural nodes.

WHAT IS NEW PER PROP
  mouse v4   sculpted ellipsoid shell: a python loop scales every vertex
             radially by (a) a silhouette profile with a real WAIST
             behind the buttons, a full rump and a tapered nose, and
             (b) a top-surface height curve that peaks rear-of-centre
             and falls to a low nose; the nose cap is FLATTENED so the
             buttons overhang a broad pad instead of a point. On top of
             that: a sunken split CHANNEL (not a painted strip), two
             separate raised button shells, a wheel in a rectangular
             well with tyre + hub + tread rings, a thumb/pinky ledge on
             the left flank carrying two side buttons, a dark underside
             pad with four PTFE skates, a DPI pill and the rear parting
             seam. 24 parts.
  mug v3     tapered stoneware with a genuine double wall: an open-topped
             outer cone and a nested inner tube leave a visible 8 mm
             wall section at the rim, the cavity's interior is DARK (a
             separate material), coffee sits 34 mm down with a MENISCUS
             ring where it meets the wall, and the handle is a real C
             (half-torus with a flattened inner side) whose struts bury
             themselves in the wall. Glaze = speckled stoneware with
             vertical drip streaks.
  pen holder hollow tapered cup: outer wall + inner wall + a thickened
             rim torus over the top annulus + an unglazed foot ring, with
             three pens standing IN the cavity (one with a matte-steel
             body + ring band).
  notebook   A5 hardcover lying closed: overhanging boards, a page block
             whose THREE cut sides wear a ~0.3 mm sheet-line material
             with yellowed outer edges, a raised spine ridge with
             stitched signature dashes, a vertical elastic band that
             disappears under the back cover at both ends, and a ribbon
             bookmark that folds over the fore-edge and lies out on the
             desk.

Run (module is import-safe; scene.py's main is guarded):
    import props_detail_v2 as P2
    props += P2.build_mouse_v4((x, y, desk_z), mats, rot_z=0.30)
"""
import bpy
import bmesh
import math

import mathutils

import scene as S     # noqa: E402  (import-safe: scene.py guards main)


_TAG = "props_detail_v2"      # idempotency marker on materials


# =========================================================== frame helpers

def _yaw(off, rz):
    """Rotate a prop-local offset about the anchor's vertical axis."""
    c, s = math.cos(rz), math.sin(rz)
    return (off[0] * c - off[1] * s, off[0] * s + off[1] * c, off[2])


def _land(loc, rz, off):
    """World location of a prop-local offset."""
    p = _yaw(off, rz)
    return (loc[0] + p[0], loc[1] + p[1], loc[2] + p[2])


def _ss(a, b, x):
    """0..1 smoothstep on [a, b] — the blend used for every profile edge
    so no sculpted surface gets a hard crease by accident."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    t = (x - a) / (b - a)
    return t * t * (3.0 - 2.0 * t)


def _curve(tab, x):
    """Piecewise-linear lookup through ((x0, y0), (x1, y1), ...)."""
    if x <= tab[0][0]:
        return tab[0][1]
    if x >= tab[-1][0]:
        return tab[-1][1]
    for i in range(len(tab) - 1):
        (a, va), (b, vb) = tab[i], tab[i + 1]
        if a <= x <= b:
            f = (x - a) / (b - a)
            return va + (vb - va) * f
    return tab[-1][1]


def _M(mats, key, build):
    """mats[key], or build() the default and cache it back in (env_props'
    pattern, so a caller pre-tunes by key)."""
    m = mats.get(key)
    if m is None:
        m = mats[key] = build()
    return m


def _bmesh_edit(o, fn):
    """Run fn(bm) on an object's mesh (vertex-level sculpting)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    fn(bm)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


# ========================================================= mesh primitives

def _box(name, loc, rz, off, size, mat, rot=(0.0, 0.0, 0.0), bevel=None):
    """Cube scaled to `size` at a yawed offset. With `bevel` the scale is
    baked into the mesh FIRST — the bevel width is LOCAL space, so on a
    210 mm board a 2.5 mm request would silently render 0.012 mm (the
    round-8 trap env_props documents)."""
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
          verts=48, smooth=True, open_top=False, open_bot=False):
    """Truncated cone; r1 sits on the -z end, r2 on +z. `open_top` /
    `open_bot` DELETE that cap after the fact — the cup/mug walls are
    built this way so the cavity is a real hole with an inner wall you
    can see into, not a lid the pens clip through (round-18's bug)."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth,
                                    location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if open_top or open_bot:
        def cut(bm):
            dead = []
            for f in bm.faces:
                if open_top and f.normal.z > 0.5:
                    dead.append(f)
                if open_bot and f.normal.z < -0.5:
                    dead.append(f)
            if dead:
                bmesh.ops.delete(bm, geom=dead, context="FACES")
        _bmesh_edit(o, cut)
    if smooth:
        bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


def _sph(name, loc, rz, off, scale, mat, rot=(0.0, 0.0, 0.0), segs=48,
         rings=24):
    """UV sphere as an ellipsoid via object scale — bmesh edits then run
    in the unit-sphere local frame and are scaled for free (Blender's UV
    sphere has its poles along LOCAL Z, so the shell's length axis is the
    y semi-axis and the shell keeps smooth, rounded nose/rump extremes)."""
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
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if scale is not None:
        o.scale = tuple(scale)
    bpy.ops.object.shade_smooth()
    S.assign([o], mat)
    return o


# ======================================================= material helpers

def _fresh(name):
    """Get-or-build guard (env_materials' pattern): returns (mat, nt);
    nt is None when the material was already built, so callers return
    early and stay idempotent — materials are shared between props."""
    mat = bpy.data.materials.get(name)
    if mat is not None and mat.get(_TAG):
        return mat, None
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat[_TAG] = True
    return mat, mat.node_tree


def _bsdf(nt):
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:                       # defensive: stripped tree
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output")
        if out is not None:
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _set(bsdf, key, value):
    """Probe-and-set a Principled input (Emission was renamed across
    Blender 4/5; Coat sockets may be absent) — never crash, just skip."""
    try:
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
            return True
    except Exception:
        pass
    return False


def _nz(nt, scale, detail=3.5, name="noise"):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.label = name
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = 0.55
    return nz


def _mp(nt, scale=(1.0, 1.0, 1.0), name="map"):
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.label = name
    mp.inputs["Scale"].default_value = tuple(scale)
    return mp


def _wave(nt, scale, distortion=0.0, detail=2.0, detail_scale=2.0,
          bands="Z", name="wave"):
    w = nt.nodes.new("ShaderNodeTexWave")
    w.label = name
    w.wave_type = "BANDS"
    w.bands_direction = bands
    w.inputs["Scale"].default_value = scale
    w.inputs["Distortion"].default_value = distortion
    w.inputs["Detail"].default_value = detail
    w.inputs["Detail Scale"].default_value = detail_scale
    return w


def _ramp(nt, stops, name="ramp", interp="LINEAR"):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.label = name
    cr = r.color_ramp
    try:
        cr.interpolation = interp
    except Exception:
        pass
    e = cr.elements
    e[0].position, e[0].color = stops[0][0], (*stops[0][1], 1.0)
    e[1].position, e[1].color = stops[1][0], (*stops[1][1], 1.0)
    for pos, col in stops[2:]:
        ne = e.new(pos)
        ne.color = (*col, 1.0)
    return r


def _bump(nt, strength, dist, name="bump"):
    b = nt.nodes.new("ShaderNodeBump")
    b.label = name
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    return b


def _mr(nt, to_min, to_max, name="range"):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.label = name
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = to_min
    mr.inputs["To Max"].default_value = to_max
    return mr


# -------------------------------------------------------- the materials

def _mtx(name, color, rough=0.5, metal=0.0, scale=240.0, bump=0.10,
         dist=0.00002, rlo=None, rhi=None, detail=3.5):
    """Principled + scene.py's micro_texture (the repo's own bar-setting
    helper: one noise -> bump + optional roughness range, generated
    space, idempotent). Idempotent via S.micro_texture's own guard."""
    m = S.pbr(name, color, rough=rough, metal=metal)
    S.micro_texture(m, scale, bump, dist, rlo, rhi, detail=detail)
    return m


def _glass(name, color, rough=0.10, coat=0.6, coat_r=0.08):
    """Glossy glaze: low roughness + a clear-coat weight, so the mug's
    cavity wall catches a moving highlight instead of reading flat."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Coat Roughness", coat_r)
    return mat


def _steel(name, color=(0.62, 0.63, 0.66), rough=0.34):
    """Brushed/matte steel: one noise stretched ~60:1 along one axis
    drives the roughness break-up + a whisper of bump — the streaks read
    as machined metal at 3 px/mm, which a flat metalness does not."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = _mp(nt, (300.0, 5.0, 5.0), "brush_space")
    L(tc.outputs["Generated"], mp.inputs["Vector"])
    nz = _nz(nt, 1.0, 2.0, "brush")
    L(mp.outputs["Vector"], nz.inputs["Vector"])
    rr = _ramp(nt, [(0.0, (rough - 0.06,) * 3),
                    (1.0, (rough + 0.05,) * 3)], "brush_rough")
    L(nz.outputs["Fac"], rr.inputs["Fac"])
    bmp = _bump(nt, 0.08, 0.000006, "brush_bump")
    L(nz.outputs["Fac"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    L(rr.outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    return mat


def _stoneware(name, base=(0.62, 0.60, 0.54), speck=(0.20, 0.17, 0.14),
               rough=0.62, scale=110.0):
    """Speckled stoneware with vertical GLAZE DRIPS. One thresholded
    noise gives the sparse ~1 mm clay/glaze flecks in colour AND bump
    (the specks are why a mug reads as ceramic, not plastic), and a
    second noise stretched ~40:1 along the object's height drags faint
    darker streaks down the wall — the drip pattern a real dipped glaze
    leaves. Both in generated space, so one material covers the whole
    tapered wall."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # ---- flecks
    nz = _nz(nt, scale, 2.0, "speckle")
    L(tc.outputs["Generated"], nz.inputs["Vector"])
    fr = _ramp(nt, [(0.62, base), (0.80, speck)], "speck_ramp")
    L(nz.outputs["Fac"], fr.inputs["Fac"])
    # ---- vertical drip streaks (stretched along the wall's height)
    mp = _mp(nt, (26.0, 26.0, 620.0), "drip_space")
    L(tc.outputs["Generated"], mp.inputs["Vector"])
    dn = _nz(nt, 2.2, 3.0, "drip")
    L(mp.outputs["Vector"], dn.inputs["Vector"])
    dr = _ramp(nt, [(0.30, (0.86, 0.84, 0.80)),
                    (0.62, (1.00, 0.98, 0.94)),
                    (0.78, (0.80, 0.76, 0.71))], "drip_ramp")
    L(dn.outputs["Fac"], dr.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.55
    L(fr.outputs["Color"], mix.inputs["Color1"])
    L(dr.outputs["Color"], mix.inputs["Color2"])
    L(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bmp = _bump(nt, 0.30, 0.00004, "clay_bump")
    L(nz.outputs["Fac"], bmp.inputs["Height"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bmp2 = _bump(nt, 0.06, 0.00002, "drip_bump")
    L(dn.outputs["Fac"], bmp2.inputs["Height"])
    L(bmp2.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _sheet_mat(name):
    """The notebook's page block: all THREE cut sides, one material.

    The sheets stack along the block's local Z (10.4 mm of paper), so
    the sheet lines are wave bands along Z in GENERATED space at ~35
    periods = a true ~0.3 mm pitch on the fore-edge and both ends — it
    resolves as stacked sheets at 3 px/mm instead of "smooth grey". A
    domain warp makes the sheets waver like a hand-stack, a second
    low-frequency noise varies each sheet's brightness individually, and
    the colour warms/yellows toward the outer sheets (the block's top
    and bottom in generated Z) the way the cut edges of a real book go.
    """
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]

    sheet = _wave(nt, 35.0, 0.30, 2.0, 2.0, bands="Z", name="sheets")
    L(gen, sheet.inputs["Vector"])
    sr = _ramp(nt, [(0.0, (0.780, 0.752, 0.695)),
                    (1.0, (0.895, 0.872, 0.818))], "sheet_ramp",
               interp="B_SPLINE")
    L(sheet.outputs["Fac"], sr.inputs["Fac"])

    # ---- per-sheet brightness jitter (constant within a sheet)
    mp_lo = _mp(nt, (3.0, 3.0, 0.05), "sheet_lo")
    L(gen, mp_lo.inputs["Vector"])
    jit = _nz(nt, 2.0, 2.0, "line_jitter")
    L(mp_lo.outputs["Vector"], jit.inputs["Vector"])
    jr = _ramp(nt, [(0.28, (0.82, 0.80, 0.77)),
                    (0.75, (1.06, 1.04, 1.01))], "jitter_ramp",
               interp="B_SPLINE")
    L(jit.outputs["Fac"], jr.inputs["Fac"])
    mj = nt.nodes.new("ShaderNodeMixRGB")
    mj.blend_type = "MULTIPLY"
    L(sr.outputs["Color"], mj.inputs["Color1"])
    L(jr.outputs["Color"], mj.inputs["Color2"])
    L(mj.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- yellowed outer edges: generated Z 0/1 = the block's two outer
    # sheets. max(z, 1-z) is 1 at the outer faces, 0 mid-stack.
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.label = "gen_z"
    L(gen, sep.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.label = "z_flip"
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L(sep.outputs["Z"], inv.inputs[1])
    mx = nt.nodes.new("ShaderNodeMath")
    mx.label = "edge_dist"
    mx.operation = "MAXIMUM"
    L(sep.outputs["Z"], mx.inputs[0])
    L(inv.outputs["Value"], mx.inputs[1])
    er = _ramp(nt, [(0.72, (1.00, 1.00, 1.00)),
                    (0.97, (0.86, 0.80, 0.68))], "yellow_ramp",
               interp="B_SPLINE")
    L(mx.outputs["Value"], er.inputs["Fac"])
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    L(mj.outputs["Color"], mul.inputs["Color1"])
    L(er.outputs["Color"], mul.inputs["Color2"])
    L(mul.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- sheet lines + paper fibre in bump
    bmp = _bump(nt, 0.14, 0.00005, "sheet_bump")
    L(sheet.outputs["Fac"], bmp.inputs["Height"])
    fib = _nz(nt, 1500.0, 4.0, "fibre")
    L(gen, fib.inputs["Vector"])
    bmp2 = _bump(nt, 0.06, 0.00002, "fibre_bump")
    L(fib.outputs["Fac"], bmp2.inputs["Height"])
    L(bmp2.outputs["Normal"], bsdf.inputs["Normal"])
    L(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    # paper is very matte, and rougher sheet-to-sheet
    bsdf.inputs["Roughness"].default_value = 0.86
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


# ============================================================ MOUSE   v4
#
# Local frame: NOSE = +y (away from the user, toward the monitor), RUMP =
# -y, the thumb/pinky LEDGE = -x, the palm arch = +x. The anchor is the
# underside contact point, so loc.z is the desk.
#
# The shell is one squashed ellipsoid (Blender's UV sphere has its poles
# along local Z, so the y semi-axis is the length and BOTH length
# extremes stay rounded) that a bmesh loop then sculpts in the unit
# frame. The loop does four things, in this order:
#   1. square the section (a mouse is a rounded BOX, not an egg),
#   2. scale x by the SILHOUETTE profile (rump swell / WAIST behind the
#      buttons / broad button pad) — after the power, so the waist
#      contrast it authors is not re-flattened,
#   3. scale z by the TOP-CURVE factor (peaks rear-of-centre, low nose),
#   4. clamp the base to a flat pad and flatten the nose cap.

_M_L = 0.118                      # nose tip -> rump tip
_M_SX, _M_SY, _M_SZ = 0.032, 0.059, 0.024
_M_CZ = 0.78 * _M_SZ              # sphere centre height: the flat base
                                  # pad lands exactly on the anchor plane
_M_TOP = ((0.00, 0.0305), (0.10, 0.0338), (0.22, 0.0380),
          (0.35, 0.0375), (0.50, 0.0360), (0.65, 0.0330),
          (0.80, 0.0290), (0.93, 0.0250), (1.00, 0.0210))
_M_BX, _M_BZ = 0.62, 0.70         # section superellipse exponents
_M_NOSE_T, _M_NOSE_P = 0.80, 2.0  # nose-cap flatten: t > 0.80 gets
                                  # compressed toward the front face
# The two recesses MILLED into the shell's top (metres, local frame). A
# box dropped inside a solid shell is invisible — that is exactly the
# round-19 mistake, and it is why the old seams and wheel did not render
# — so the channel and the well are carved hollow by the sculpt loop and
# then lined with a dark insert that sits in the carve.
_M_CH_HW, _M_CH_EDGE = 0.0009, 0.0009   # channel floor half-width / wall
_M_CH_D = 0.0014                        # channel depth
_M_CH_SEGS = ((0.011, 0.049), (-0.0285, -0.0125))   # seam + parting line
_M_SEG_EDGE = 0.0015                    # recess end blend
_M_WW_HW, _M_WW_EDGE = 0.0050, 0.0010   # wheel well floor half-width
_M_WW_D = 0.0065                        # wheel well depth
_M_WW_Y = (-0.0115, 0.0105)             # wheel well y span


def _m_t(y):
    """0 (rump) .. 1 (nose) for a local y."""
    return (y + _M_L / 2.0) / _M_L


def _m_top(y):
    """The shell's TOP surface height (m above the anchor) at local y —
    everything that sits on the shell is placed from this, so no part
    floats and nothing sinks through."""
    return _curve(_M_TOP, _m_t(y))


def _m_wprof(t):
    """Silhouette width multiplier along the length.

    ONE bulge, not two: a palm swell (+11% at t=0.22) and a WAIST pinch
    (-13% at t=0.50, immediately behind the button face — the pinched
    waist is the single cue that separates "ergonomic mouse" from
    "blob"). The front is left to the ellipsoid's own taper: an earlier
    version added a "front fill" to keep the buttons on a broad pad and
    produced a SECOND bulge at t=0.75, which read as a peanut from above.
    Values are relative: 1.0 == the ellipsoid's own radius."""
    return (1.00
            + 0.11 * math.exp(-(((t - 0.22) / 0.24) ** 2))
            - 0.14 * math.exp(-(((t - 0.50) / 0.15) ** 2)))


def _m_hprof(t):
    """Top-surface multiplier that puts the sculpted shell ON _M_TOP.

    The ellipsoid's own dome peaks at the length centre while a mouse's
    top peaks REAR of centre, so the factor dips over the middle and
    lifts at both ends. It is normalised against the vertex's own
    cross-section radius, which makes it exact for the top of each ring
    and harmless for the flanks below it — and it stays finite at the
    tips, where the cross-section radius (not the height) goes to zero."""
    r = max(0.06, math.sqrt(max(0.0, 1.0 - (2.0 * t - 1.0) ** 2)))
    return (_curve(_M_TOP, t) - _M_CZ) / (_M_SZ * (r ** _M_BZ))


def _mask_span(v, lo, hi, edge):
    """1 inside [lo, hi], smooth-blended to 0 over `edge` at each end —
    the footprint mask of a milled recess, so its walls SLOPE instead of
    stepping (a hard edge would read as a slot cut with a bandsaw)."""
    if lo <= v <= hi:
        return 1.0
    if lo - edge < v < lo:
        return _ss(lo - edge, lo, v)
    if hi < v < hi + edge:
        return _ss(hi + edge, hi, v)
    return 0.0


def _mask_half(v, hw, edge):
    """1 for |v| <= hw (v >= 0), blended to 0 at hw + edge."""
    if v <= hw:
        return 1.0
    if v < hw + edge:
        return 1.0 - _ss(hw, hw + edge, v)
    return 0.0


def _m_surf(tt):
    """The sculpted shell's top surface at length parameter tt, expressed
    in the unit-z frame the sculpt loop works in."""
    return (_curve(_M_TOP, tt) - _M_CZ) / _M_SZ


def _shell_sculpt(bm):
    """The sculpt loop. Vertices arrive as a unit sphere; they leave as
    the mouse's side profile with the split channel and the wheel well
    already milled into its top."""
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        t = (y + 1.0) * 0.5                     # 0 rump .. 1 nose
        # 1. square the section: exponent < 1 pulls the flanks and the
        #    top flat (a mouse cross-section is a rounded box with a
        #    wide base, tapering to a domed ridge)
        if abs(x) > 1e-9:
            x = math.copysign(abs(x) ** _M_BX, x)
        if abs(z) > 1e-9:
            z = math.copysign(abs(z) ** _M_BZ, z)
        # 2. the silhouette profile (WAIST first, so it survives)
        x *= _m_wprof(t)
        if x < 0.0:
            # the -x (thumb) flank narrows toward the nose sooner than
            # the +x (palm) flank: the right-hand wedge that reads as
            # "shaped for a hand", not "rotated blobs"
            x *= 1.0 - 0.10 * _ss(0.40, 0.95, t)
        # 3. the top curve, then 4. the milled recesses
        if z > 0.0:
            z *= _m_hprof(t)
            yw = y * _M_SY                       # metres along the length
            ax = abs(x) * _M_SX                 # |x| in metres
            dep = 0.0
            for lo, hi in _M_CH_SEGS:
                dep = max(dep, _M_CH_D
                          * _mask_span(yw, lo, hi, _M_SEG_EDGE)
                          * _mask_half(ax, _M_CH_HW, _M_CH_EDGE))
            dep = max(dep, _M_WW_D
                      * _mask_span(yw, _M_WW_Y[0], _M_WW_Y[1], _M_SEG_EDGE)
                      * _mask_half(ax, _M_WW_HW, _M_WW_EDGE))
            if dep > 0.0:
                floor = _m_surf(_m_t(yw)) - dep / _M_SZ
                if z > floor:
                    z = floor                   # flat-floored recess
        # 5. flat base pad (the contact patch, so the shadow stays a
        #    tight ellipse instead of the ellipsoid's point)
        if z < -0.78:
            z = -0.78
        # 6. blunt the nose: the outer 20% of the length is compressed
        #    toward the front, turning the ellipsoid's point into a
        #    ~45 x 25 mm pad the buttons overhang
        if y > _M_NOSE_T:
            s = (y - _M_NOSE_T) / (1.0 - _M_NOSE_T)
            y = _M_NOSE_T + (1.0 - _M_NOSE_T) * (0.06 + 0.94 * s ** _M_NOSE_P)
        v.co = (x, y, z)


def build_mouse_v4(loc, mats, rot_z=0.30):
    """RIGHT-HANDED ergonomic mouse, ~63 x 118 x 38 mm, 27 parts.

    The silhouette is authored, not implied: one squashed ellipsoid is
    sculpted in bmesh by a profile function that gives the shell a WAIST
    just behind the buttons, a full rump and a low nose, with a top curve
    peaking rear-of-centre where the palm sits. THE RECESSES ARE MILLED
    INTO THAT SHELL by the same loop — the split channel and the wheel
    well are carved hollow (with sloped walls) and then lined with dark
    inserts, rather than boxes floating inside a solid body, which is
    what made the round-19 seams and wheel invisible:

      shell (carved) + flat dark base pad + 4 PTFE skates + sensor lens
      two separate raised button shells (glossier than the shell),
      overlapping the channel's front segment
      the dark CHANNEL inserts: the front seam between the buttons and
      the rear parting line; together they run from the nose back over
      65% of the length, interrupted by the wheel well as on a real mouse
      the wheel well's dark floor + a scroll wheel: rubber tyre, lighter
      hub proud at both ends, 6 tread rings
      a DPI pill, the rear top-shell seam, a thumb/pinky LEDGE on the -x
      flank with two side buttons

    Each is a separate object with its own material, so at 50 px the
    shell reads as an assembly of parts (buttons, wheel, flank pad) and
    not one grey lump."""
    rz = rot_z
    m_body = _M(mats, "ms_body", lambda: _mtx(
        "pd2_ms_body", (0.115, 0.115, 0.120), rough=0.62, scale=300.0,
        bump=0.09, dist=0.00002, rlo=0.52, rhi=0.66))
    # the button shells get their own material: the same graphite but a
    # touch GLOSSIER than the shell, which is what makes them read as
    # separate parts under a grazing light instead of one continuous dome
    m_btn = _M(mats, "ms_button", lambda: _mtx(
        "pd2_ms_button", (0.125, 0.125, 0.130), rough=0.48, scale=300.0,
        bump=0.09, dist=0.00002, rlo=0.40, rhi=0.54))
    m_seam = _M(mats, "ms_seam", lambda: _mtx(
        "pd2_ms_seam", (0.030, 0.031, 0.034), rough=0.74, scale=420.0,
        bump=0.14, dist=0.00004, rlo=0.68, rhi=0.82))
    m_base = _M(mats, "ms_base", lambda: _mtx(
        "pd2_ms_base", (0.018, 0.018, 0.020), rough=0.80, scale=260.0,
        bump=0.10, dist=0.00003, rlo=0.72, rhi=0.88))
    m_sensor = _M(mats, "ms_sensor", lambda: S.pbr(
        "pd2_ms_sensor", (0.030, 0.036, 0.052), rough=0.10, metal=0.4))
    m_skate = _M(mats, "ms_skate", lambda: S.pbr(
        "pd2_ms_skate", (0.60, 0.60, 0.63), rough=0.22))
    m_tyre = _M(mats, "ms_tyre", lambda: _mtx(
        "pd2_ms_tyre", (0.050, 0.050, 0.056), rough=0.78, scale=520.0,
        bump=0.16, dist=0.00005, rlo=0.70, rhi=0.86, detail=4.0))
    m_hub = _M(mats, "ms_hub", lambda: S.pbr(
        "pd2_ms_hub", (0.52, 0.52, 0.55), rough=0.30, metal=0.6))
    m_tread = _M(mats, "ms_tread", lambda: _mtx(
        "pd2_ms_tread", (0.100, 0.100, 0.106), rough=0.85, scale=700.0,
        bump=0.12, dist=0.00002))
    m_side = _M(mats, "ms_side", lambda: _mtx(
        "pd2_ms_side", (0.042, 0.043, 0.048), rough=0.80, scale=600.0,
        bump=0.10, dist=0.00003, rlo=0.72, rhi=0.88))
    m_ledge = _M(mats, "ms_ledge", lambda: _mtx(
        "pd2_ms_ledge", (0.150, 0.148, 0.150), rough=0.90, scale=900.0,
        bump=0.10, dist=0.00002, rlo=0.82, rhi=0.96, detail=4.0))
    out = []

    # ---- the shell: the squashed ellipsoid, sculpted in the unit frame
    shell = _sph("p2_ms_shell", loc, rz, (0.0, 0.0, _M_CZ),
                 (_M_SX, _M_SY, _M_SZ), m_body, segs=56, rings=28)
    _bmesh_edit(shell, _shell_sculpt)
    out.append(shell)

    # ---- underside: the shadow gap + the feet the mouse glides on
    out.append(_box("p2_ms_basepad", loc, rz, (0.0, -0.002, -0.00035),
                    (0.050, 0.082, 0.0007), m_base))
    out.append(_cyl("p2_ms_sensor", loc, rz, (0.0, -0.024, -0.0012),
                    0.0052, 0.0009, m_sensor))
    for i, (sx, sy) in enumerate(((-1.0, -1.0), (1.0, -1.0),
                                  (-1.0, 1.0), (1.0, 1.0))):
        out.append(_box(f"p2_ms_skate_{i}", loc, rz,
                        (sx * 0.019, sy * 0.030, -0.0016),
                        (0.011, 0.016, 0.0018), m_skate))

    # ---- the two button shells: separate raised pieces sitting on the
    # shell's front slope (tilted down onto it), each overlapping the
    # channel's front segment and overhanging its carved inner edge —
    # exactly how a real two-button shell seats over its seam.
    for tag, sx in (("l", -1.0), ("r", 1.0)):
        out.append(_sph(f"p2_ms_btn_{tag}", loc, rz,
                        (sx * 0.0115, 0.031, _m_top(0.031) + 0.0007),
                        (0.0105, 0.0195, 0.0018), m_btn,
                        rot=(-0.20, 0.0, 0.0), segs=32, rings=16))

    # ---- the dark inserts that line the carved channel. Each is a
    # chamfered box whose top face rides ~0.5 mm under the surface chord,
    # so the milled walls of the carve stay visible around it and the
    # seam reads as an inset groove rather than a strip painted on. The
    # rear segment is the top-shell parting line that continues behind
    # the wheel well: together the channel runs from the nose back over
    # 65% of the length, interrupted by the well as on a real mouse.
    out.append(_box("p2_ms_chan_front", loc, rz, (0.0, 0.030, 0.02758),
                    (0.0018, 0.0390, 0.0035), m_seam,
                    rot=(-0.227, 0.0, 0.0), bevel=0.0004))
    out.append(_box("p2_ms_chan_rear", loc, rz, (0.0, -0.0205, 0.03523),
                    (0.0018, 0.0170, 0.0035), m_seam,
                    rot=(-0.049, 0.0, 0.0), bevel=0.0004))

    # ---- the wheel well's dark floor, 0.15 mm under the milled floor of
    # the carve (tilted to follow the top slope at the well)
    out.append(_box("p2_ms_wellfloor", loc, rz, (0.0, -0.001, 0.02735),
                    (0.0090, 0.0195, 0.0040), m_seam,
                    rot=(-0.169, 0.0, 0.0)))
    wa = math.radians(10.0)          # the ergonomic rake, in plan
    out.append(_cyl("p2_ms_wheel_tyre", loc, rz, (0.0, -0.001, 0.0325),
                    0.0052, 0.0080, m_tyre,
                    rot=(0.0, math.pi / 2, wa), verts=40))
    out.append(_cyl("p2_ms_wheel_hub", loc, rz, (0.0, -0.001, 0.0325),
                    0.0030, 0.0088, m_hub,
                    rot=(0.0, math.pi / 2, wa), verts=32))
    # 6 tread rings spaced 1.3 mm along the axle: at 3 px/mm they read
    # as the grippy rubber tread instead of a smooth tyre
    for k in range(6):
        out.append(_tor(f"p2_ms_wring_{k}", loc, rz,
                        (math.cos(wa) * (k - 2.5) * 0.0013,
                         -0.001 + math.sin(wa) * (k - 2.5) * 0.0013,
                         0.0325),
                        0.00535, 0.00045, m_tread,
                        rot=(0.0, math.pi / 2, wa), minor=8))

    # ---- DPI pill on the top centre just behind the parting line, and
    # the rear top-shell seam across the rump (where the top curve is
    # still rising toward the nose, hence the +0.27 rad tilt)
    out.append(_sph("p2_ms_dpi", loc, rz,
                    (0.0, -0.031, _m_top(-0.031) + 0.0008),
                    (0.0026, 0.0062, 0.0017), m_btn,
                    segs=24, rings=12))
    out.append(_box("p2_ms_rearseam", loc, rz,
                    (0.0, -0.045, _m_top(-0.045) - 0.0005),
                    (0.048, 0.0016, 0.0011), m_seam,
                    rot=(0.27, 0.0, 0.0), bevel=0.0004))

    # ---- the thumb/pinky LEDGE on the -x flank: a lens-shaped pad that
    # hugs the flank's curvature (a flat box would show a gap on a curved
    # wall) and stands ~2 mm proud, carrying two side buttons.
    out.append(_sph("p2_ms_ledge", loc, rz, (-0.0286, 0.006, 0.0125),
                    (0.0016, 0.0240, 0.0078), m_ledge,
                    rot=(-0.05, 0.0, 0.0), segs=32, rings=16))
    for i, (sy, dz) in enumerate(((-0.004, 0.0003), (0.012, 0.0003))):
        out.append(_sph(f"p2_ms_side_{i}", loc, rz,
                        (-0.0306, sy, 0.0128 + dz),
                        (0.0014, 0.0095, 0.0048), m_side,
                        rot=(0.0, 0.0, 0.12 if i else -0.12),
                        segs=24, rings=12))

    S.smooth([shell], 40.0)      # bevel/crease stays crisp, dome smooths
    return out


# ============================================================= MUG   v3
#
# Local frame: the mug stands on the anchor, its axis vertical, the
# handle on the -y side (toward the user / the desk camera). A REAL mug
# is a thick-walled vessel: the outer cone is open-topped and a nested
# inner tube (a pure tapered tube, both caps deleted) forms the cavity,
# so the top annulus between them is genuine 6-8 mm of stoneware. The
# cavity gets its own DARK material — looking into a mug at 35 deg+ has
# to show a dark interior, and one material on a single cone cannot be
# light outside and dark inside.

def build_mug_v3(loc, mats):
    """Ceramic mug, O82 x 96 mm, 9 parts.

    Tapered stoneware wall (O66 base -> O82 rim) with a thickened rim
    torus, a genuine cavity (inner tube + floor) whose interior reads
    dark from any angle above 35 deg, coffee 34 mm down with a MENISCUS
    ring where the surface meets the wall, a crema ring, a tea-stain
    line on the inner wall, an unglazed foot ring, and a handle that is
    a real C: a torus in the y-z plane whose two struts bury themselves
    in the wall, with the inner side flattened in bmesh for finger
    clearance. Glaze = speckled stoneware + vertical drip streaks."""
    m_out = _M(mats, "mug_outer", lambda: _stoneware(
        "pd2_mug_outer", (0.660, 0.605, 0.520), (0.190, 0.160, 0.130),
        rough=0.60, scale=110.0))
    m_in = _M(mats, "mug_glaze", lambda: _glass(
        "pd2_mug_glaze", (0.055, 0.085, 0.082), rough=0.12, coat=0.6,
        coat_r=0.08))
    m_cof = _M(mats, "mug_coffee", lambda: _mtx(
        "pd2_mug_coffee", (0.046, 0.027, 0.015), rough=0.07, scale=700.0,
        bump=0.03, dist=0.000004, rlo=0.04, rhi=0.10))
    m_crema = _M(mats, "mug_crema", lambda: S.pbr(
        "pd2_mug_crema", (0.300, 0.190, 0.105), rough=0.34))
    m_men = _M(mats, "mug_meniscus", lambda: S.pbr(
        "pd2_mug_meniscus", (0.020, 0.011, 0.006), rough=0.16))
    m_stain = _M(mats, "mug_stain", lambda: S.pbr(
        "pd2_mug_stain", (0.145, 0.082, 0.040), rough=0.40))
    m_foot = _M(mats, "mug_foot", lambda: _mtx(
        "pd2_mug_foot", (0.560, 0.520, 0.465), rough=0.86, scale=520.0,
        bump=0.22, dist=0.00005, rlo=0.80, rhi=0.96, detail=4.0))
    out = []
    R_BASE, R_RIM, H = 0.033, 0.041, 0.096

    # outer wall: open-topped tapered cone, floor kept at the anchor
    out.append(_cone("p2_mug_wall", loc, 0.0, (0.0, 0.0, H / 2.0),
                     R_BASE, R_RIM, H, m_out, verts=64, open_top=True))
    # inner tube: BOTH caps deleted — a pure wall whose inner surface is
    # the cavity. 8 mm section at the rim, 6 mm at the base.
    out.append(_cone("p2_mug_cavity", loc, 0.0, (0.0, 0.0, 0.047),
                     0.0245, 0.0325, 0.094, m_in, verts=64,
                     open_top=True, open_bot=True))
    # thickened rim: the tube straddles the top annulus and stands ~2 mm
    # proud, so the wall's cut edge reads as a rolled lip
    out.append(_tor("p2_mug_rim", loc, 0.0, (0.0, 0.0, 0.0948),
                    0.0368, 0.0033, m_out, minor=16))
    # unglazed foot ring (bare ceramic where it rested on the kiln shelf)
    out.append(_tor("p2_mug_foot", loc, 0.0, (0.0, 0.0, 0.0014),
                    0.0300, 0.0024, m_foot, minor=16))

    # ---- coffee 34 mm down. The cavity's wall radius there is 0.0296.
    CZ = 0.062
    out.append(_cyl("p2_mug_coffee", loc, 0.0, (0.0, 0.0, CZ),
                    0.0288, 0.0013, m_cof, verts=48))
    # MENISCUS: a small dark torus sitting exactly at the wall radius,
    # half in the coffee — the wet line where the surface creeps up the
    # ceramic (surface tension), which is what makes the liquid read as
    # a liquid rather than a grey disc
    out.append(_tor("p2_mug_meniscus", loc, 0.0, (0.0, 0.0, CZ + 0.0002),
                    0.0294, 0.0013, m_men, minor=16))
    # crema ring floating at the surface (a ring, not a full disc, so
    # the dark coffee still reads between the bubbles)
    out.append(_tor("p2_mug_crema", loc, 0.0, (0.0, 0.0, CZ + 0.0007),
                    0.0225, 0.0035, m_crema, minor=16))
    # the tea/coffee stain line a used mug gets on the inner wall
    out.append(_tor("p2_mug_stain", loc, 0.0, (0.0, 0.0, 0.0805),
                    0.0305, 0.0011, m_stain, minor=16))

    # ---- handle: a genuine C. Torus in the y-z plane (rot y 90 deg) so
    # its axis runs across the mug; major radius 24 mm puts the struts'
    # centreline on the wall at mid height, so the two ends bury ~7 mm
    # inside the stoneware and the outer crossbar stands clear.
    HW = R_BASE + (R_RIM - R_BASE) * (0.050 / H)      # wall radius at
                                                      # the handle height
    hnd = _tor("p2_mug_handle", loc, 0.0,
               (0.0, -(HW + 0.024), 0.050),
               0.024, 0.0055, m_out, rot=(0.0, math.pi / 2, 0.0),
               minor=20)

    def flatten(bm):
        """Flatten the handle's INNER side: push the arc that would sit
        inside the cavity back toward a plane, which opens the finger
        clearance ~3 mm the way a thrown handle is."""
        for v in bm.verts:
            if v.co.y > -0.045:
                v.co.y += 0.60 * (-0.042 - max(v.co.y, -0.045))
    _bmesh_edit(hnd, flatten)
    out.append(hnd)
    return out


# ======================================================= PEN HOLDER   v3
#
# The round-19 holder was not hollow: the old inner disc acted as a lid
# the pens clipped through. This one is two nested tapered walls, so the
# wall's thickness is visible as an annulus at the rim, and the pens
# stand visibly INSIDE a cavity with a dark interior.

def build_pen_holder_v3(loc, mats):
    """Hollow ceramic pen holder, ~O76 base / O80 rim x 96 mm, with 3
    pens standing inside it (17 parts).

    Outer wall (open top, floor kept) + inner tapered tube (both caps
    deleted) leave a 6-7 mm stoneware section; a rim torus thickens the
    top annulus and stands ~2 mm proud; an unglazed foot ring closes the
    base. The cavity interior is a separate dark material, so the holder
    reads HOLLOW from any angle above the rim. Pens: dark matte, white
    matte, and a matte-steel body with a ring band near the top — each
    with a tapered tip, barrel, cap and clip, slightly leaned."""
    m_out = _M(mats, "holder_outer", lambda: _stoneware(
        "pd2_holder_outer", (0.075, 0.075, 0.082), (0.030, 0.030, 0.034),
        rough=0.55, scale=150.0))
    m_in = _M(mats, "holder_inner", lambda: _mtx(
        "pd2_holder_inner", (0.020, 0.020, 0.024), rough=0.72,
        scale=380.0, bump=0.10, dist=0.00003, rlo=0.66, rhi=0.82))
    m_rim = _M(mats, "holder_rim", lambda: _glass(
        "pd2_holder_rim", (0.085, 0.085, 0.092), rough=0.22, coat=0.4,
        coat_r=0.12))
    m_foot = _M(mats, "holder_foot", lambda: _mtx(
        "pd2_holder_foot", (0.105, 0.102, 0.098), rough=0.88,
        scale=520.0, bump=0.22, dist=0.00005, rlo=0.82, rhi=0.96,
        detail=4.0))
    m_dark = _M(mats, "pen_dark", lambda: _mtx(
        "pd2_pen_dark", (0.085, 0.087, 0.095), rough=0.30, scale=300.0,
        bump=0.08, dist=0.00002, rlo=0.26, rhi=0.34))
    m_white = _M(mats, "pen_white", lambda: _mtx(
        "pd2_pen_white", (0.850, 0.845, 0.835), rough=0.22, scale=300.0,
        bump=0.08, dist=0.00002, rlo=0.18, rhi=0.26))
    m_copper = _M(mats, "pen_copper", lambda: _mtx(
        "pd2_pen_copper", (0.520, 0.330, 0.200), rough=0.32, metal=0.9,
        scale=260.0, bump=0.08, dist=0.00002, rlo=0.26, rhi=0.36))
    m_steel = _M(mats, "pen_steel", lambda: _steel(
        "pd2_pen_steel", (0.560, 0.570, 0.600), rough=0.38))
    m_clip = _M(mats, "pen_clip_metal", lambda: _steel(
        "pd2_pen_clip", (0.720, 0.730, 0.750), rough=0.24))
    out = []
    H, R_BASE, R_RIM = 0.096, 0.031, 0.040

    # outer wall: open top, floor kept
    out.append(_cone("p2_hold_wall", loc, 0.0, (0.0, 0.0, H / 2.0),
                     R_BASE, R_RIM, H, m_out, verts=64, open_top=True))
    # inner tube: BOTH caps deleted -> a hollow cavity whose floor is
    # the outer wall's bottom cap
    out.append(_cone("p2_hold_cavity", loc, 0.0, (0.0, 0.0, 0.047),
                     0.0245, 0.0335, 0.094, m_in, verts=64,
                     open_top=True, open_bot=True))
    # thickened rim over the annulus, ~2 mm proud of the wall top
    out.append(_tor("p2_hold_rim", loc, 0.0, (0.0, 0.0, 0.0948),
                    0.0368, 0.0033, m_rim, minor=16))
    # unglazed foot ring
    out.append(_tor("p2_hold_foot", loc, 0.0, (0.0, 0.0, 0.0014),
                    0.0290, 0.0024, m_foot, minor=16))

    # ---- three pens standing IN the cavity (tips on the cavity floor at
    # z = 0.002, caps clear of the rim). Each: tapered tip, barrel, cap,
    # clip; the third is the matte-steel body with a ring band.
    pens = (
        # (dx, dy, lean_x, lean_y, body mat, key)
        (0.0115, 0.0040, 0.030, -0.020, m_dark, "dark"),
        (-0.0110, 0.0010, -0.025, 0.018, m_white, "white"),
        (-0.0005, -0.0140, 0.015, 0.026, m_steel, "steel"),
    )
    for i, (dx, dy, lx, ly, bmat, tag) in enumerate(pens):
        a = (loc[0], loc[1], loc[2] + 0.002)
        rx, ry = math.radians(lx), math.radians(ly)
        out.append(_cyl(f"p2_pen{i}_barrel", a, 0.0, (0.0, 0.0, 0.058),
                        0.0055, 0.090, bmat,
                        rot=(rx, ry, 0.0), verts=32))
        # tapered writing tip (r1 at the top so the cone narrows down)
        out.append(_cone(f"p2_pen{i}_tip", a, 0.0, (0.0, 0.0, 0.008),
                         0.0055, 0.0012, 0.012, bmat, rot=(rx, ry, 0.0),
                         verts=32))
        out.append(_cyl(f"p2_pen{i}_cap", a, 0.0, (0.0, 0.0, 0.117),
                        0.0062, 0.030, m_dark, rot=(rx, ry, 0.0),
                        verts=32))
        out.append(_box(f"p2_pen{i}_clip", a, 0.0, (-0.0069, 0.0, 0.124),
                        (0.0016, 0.0030, 0.030), m_clip,
                        rot=(0.0, 0.0, 0.0), bevel=0.0005))
        if tag == "steel":
            # matte-steel body: a machined ring band near the top
            out.append(_tor(f"p2_pen{i}_band", a, 0.0, (0.0, 0.0, 0.098),
                            0.0062, 0.0006, m_copper,
                            rot=(rx, ry, 0.0), minor=16))
    return out


# ======================================================== NOTEBOOK   v2
#
# Local frame: the book lies closed, the spine at -x, the fore-edge at
# +x, the long axis along y (210 mm), the anchor is the underside of the
# bottom cover (so loc.z is the desk). The sheets stack along LOCAL Z, so
# the three cut sides are +x (fore-edge) and +-y (the ends) — and the
# sheet-line material's bands run along that Z.

_NB_T = 0.0020          # cover board thickness
_NB_PG = 0.0104         # page block thickness
_NB_W, _NB_H = 0.148, 0.210
_NB_PW, _NB_PH = 0.141, 0.204


def build_notebook_v2(loc, mats, rot_z=0.0):
    """A5 hardcover lying closed, ~148 x 210 x 14 mm, 20 parts.

    Layered like the real object: two 2 mm cover boards overhang a
    10.4 mm page block by 3.5 mm on the three open sides, so the PAGES
    are genuinely visible there wearing a true ~0.3 mm sheet-line
    material with yellowed outer edges. A raised spine ridge carries 9
    stitched signature dashes. The elastic band wraps VERTICALLY (across
    the book's height, 24 mm in from the fore-edge), stands proud 1.4 mm
    on the top board and turns over the top and bottom edges, ending
    under the back cover at both. The ribbon bookmark runs from the
    spine to the fore-edge, folds over it and lies out on the desk. A
    debossed title block (no text) sits centre-top."""
    rz = rot_z
    m_cover = _M(mats, "nb_cover", lambda: _mtx(
        "pd2_nb_cover", (0.140, 0.160, 0.150), rough=0.58, scale=130.0,
        bump=0.14, dist=0.00004, rlo=0.50, rhi=0.64))
    m_spine = _M(mats, "nb_spine", lambda: _mtx(
        "pd2_nb_spine", (0.100, 0.115, 0.106), rough=0.55, scale=130.0,
        bump=0.14, dist=0.00004, rlo=0.48, rhi=0.62))
    m_pages = _M(mats, "nb_pages", lambda: _sheet_mat("pd2_nb_pages"))
    m_strap = _M(mats, "nb_strap", lambda: _mtx(
        "pd2_nb_strap", (0.030, 0.031, 0.036), rough=0.82, scale=400.0,
        bump=0.25, dist=0.00004, rlo=0.74, rhi=0.90, detail=4.0))
    m_ribbon = _M(mats, "nb_ribbon", lambda: _mtx(
        "pd2_nb_ribbon", (0.420, 0.075, 0.095), rough=0.70, scale=300.0,
        bump=0.30, dist=0.00005, rlo=0.62, rhi=0.80, detail=4.0))
    m_title = _M(mats, "nb_title", lambda: S.pbr(
        "pd2_nb_title", (0.085, 0.095, 0.088), rough=0.45))
    m_thread = _M(mats, "nb_stitch", lambda: _mtx(
        "pd2_nb_stitch", (0.780, 0.730, 0.620), rough=0.72, scale=900.0,
        bump=0.10, dist=0.00002, rlo=0.66, rhi=0.80))
    out = []
    Z_BOT = 0.0                       # underside of the bottom cover
    Z_PG = Z_BOT + _NB_T              # page block bottom
    Z_TOP = Z_PG + _NB_PG             # top cover bottom

    # ---- the sandwich: bottom cover, page block, top cover
    out.append(_box("p2_nb_board_b", loc, rz, (0.0, 0.0, Z_BOT + 0.001),
                    (_NB_W, _NB_H, _NB_T), m_cover, bevel=0.0012))
    out.append(_box("p2_nb_pages", loc, rz,
                    (0.0, 0.0, Z_PG + _NB_PG / 2.0),
                    (_NB_PW, _NB_PH, _NB_PG), m_pages, bevel=0.0008))
    out.append(_box("p2_nb_board_t", loc, rz,
                    (0.0, 0.0, Z_TOP + 0.001),
                    (_NB_W, _NB_H, _NB_T), m_cover, bevel=0.0012))

    # ---- spine ridge: proud of both boards on the closed long edge and
    # wrapped past the ends, with the raised top standing ~0.6 mm over
    # the top cover
    out.append(_box("p2_nb_spine", loc, rz,
                    (-0.0737, 0.0, Z_PG + _NB_PG / 2.0 - 0.0005),
                    (0.0075, _NB_H + 0.0015, 0.0155), m_spine,
                    bevel=0.0025))

    # ---- stitched signature binding: 9 short thread dashes on the
    # spine face, alternating height like a hand-sewn gathering
    for i in range(9):
        y = -0.075 + i * 0.01875
        out.append(_box(f"p2_nb_stitch_{i}", loc, rz,
                        (-0.0778, y, Z_PG + _NB_PG / 2.0
                         + (-0.0007 if i % 2 else 0.0007)),
                        (0.0006, 0.0018, 0.0010), m_thread))

    # ---- the elastic band, wrapping vertically
    bx = 0.050                        # 24 mm in from the fore-edge
    out.append(_box("p2_nb_band", loc, rz, (bx, 0.0, Z_TOP + 0.0015),
                    (0.011, _NB_H + 0.002, 0.0014), m_strap,
                    bevel=0.0004))
    for tag, sy in (("t", 1.0), ("b", -1.0)):
        # turns over the cover's top/bottom edge and runs the full stack
        # thickness, so the band clearly disappears under the back cover
        out.append(_box(f"p2_nb_bandedge_{tag}", loc, rz,
                        (bx, sy * ((_NB_H / 2.0) + 0.0007),
                         Z_PG + _NB_PG / 2.0 - 0.0005),
                        (0.011, 0.0014, 0.0155), m_strap))
    # the band's hidden return under the back cover (keeps the loop
    # closed geometrically; the desk hides it)
    out.append(_box("p2_nb_band_back", loc, rz, (bx, 0.0, 0.0011),
                    (0.011, _NB_H + 0.002, 0.0014), m_strap,
                    bevel=0.0004))

    # ---- the ribbon bookmark: on-cover strip, fold over the fore-edge,
    # then a tail lying out on the desk
    ry_ = 0.038
    out.append(_box("p2_nb_ribbon", loc, rz, (0.002, ry_, Z_TOP + 0.00145),
                    (0.1480, 0.0100, 0.0009), m_ribbon, bevel=0.0003))
    out.append(_box("p2_nb_ribbonfold", loc, rz,
                    (0.0745, ry_, Z_PG + _NB_PG / 2.0 - 0.0005),
                    (0.0010, 0.0100, 0.0155), m_ribbon))
    out.append(_box("p2_nb_ribbontail", loc, rz,
                    (0.0945, ry_, 0.00045),
                    (0.0400, 0.0100, 0.0009), m_ribbon, bevel=0.0003))

    # ---- debossed title block (a rectangle, no text): 0.7 mm proud
    out.append(_box("p2_nb_title", loc, rz, (0.005, -0.012, Z_TOP + 0.00135),
                    (0.058, 0.082, 0.0007), m_title, bevel=0.0006))
    return out

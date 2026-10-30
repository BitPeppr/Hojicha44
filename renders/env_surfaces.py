"""Hojicha44 desk-environment SURFACES — Blender 5.2 headless.

Real 3D-form replacements for the round-19 primitive backdrop in
scene_env.py. The standing review is "not enough 3D detail, looks
rather basic, unrealistic": five plain boxes for a plank desk, one box
for the wall, one box for the floor, one bevelled box for the mat.
This module rebuilds all four as objects with joins, fillets, welted
borders, casters and seams — the geometry that catches a raking light
and reads as a real room at 3 px/mm.

USAGE (from scene_env.py — the caller collects the lists itself):

    import env_surfaces as ES
    PROPS += ES.build_plank_desk((cx, cy, desk_z), mats, planks=(5,))
    PROPS += ES.build_desk_mat((cx, mat_y, mat_top - MAT_T), mats)
    PROPS += ES.build_room((cx, cy + 0.6125, floor_z), mats)
    PROPS += ES.build_chair((cx, cy, floor_z), mats)      # dev scene

CONVENTIONS (env_props.py's rules, so the two files compose)
  * every builder takes an explicit world `loc` + a shared `mats`
    dict and RETURNS A LIST of objects. Nothing is appended to a
    module-level registry: the caller extends its own PROPS.
  * all sizes are metres; parts are authored as (dx, dy, dz) offsets
    in the builder's local frame (+x along the desk, +y toward the
    wall/monitor, +z up, front = -y) and yawed by the optional
    `rot_z`, which the caller can use to re-aim a whole surface.
  * `loc` is the ANCHOR, documented per builder:
      build_plank_desk  top-surface centre of the plank run
      build_desk_mat    the mat's underside centre (what it lies on)
      build_room        the wall's inner face at floor level
      build_chair       the floor point under the chair's column
  * materials: every key is probed with _M() and a default built with
    scene.pbr / scene.micro_texture when absent, then cached back
    into the dict — so a caller can pre-tune any surface by simply
    passing the key (scene_env's EM.proc_walnut2 for "wood" works).
  * Blender 5.2 facts honoured here: BEVEL is bm.width /
    bm.segments = w, n (no limit_method needed), to_track_quat only
    takes "Z"/"-Z"/"Y" style axes, and the emission socket is probed
    with `if key in bsdf.inputs` before use.
  * A subtle form is only built if it survives the desk shot's
    ~3 px/mm: a 1.5 mm seam, a 1.65 mm welt, a 2.5 mm cup in a plank
    — all real geometry, no fake bump maps standing in for joins.

PRIMITIVES: _box/_cyl/_tor/_cone mirror scene_env's helpers (same
argument order, same bevel pattern) but RETURN the object instead of
registering it. _panel (a two-point slab) and _rrect_prism (a filleted
rounded-rect slab) are the two new forms the brief needs: the mat's
folded corner and its welted border cannot be expressed as a rotated
box alone.
"""
import bpy
import bmesh
import math
import random as _rnd

import mathutils

import scene as S     # import-safe (guarded main)


# ---------------------------------------------------------- shared helpers

def _yaw(off, rz):
    """Rotate a local offset about the anchor's vertical axis."""
    c, s = math.cos(rz), math.sin(rz)
    return (off[0] * c - off[1] * s, off[0] * s + off[1] * c, off[2])


def _M(mats, key, build):
    """mats[key], or build() the default and cache it back in."""
    m = mats.get(key)
    if m is None:
        m = mats[key] = build()
    return m


def _land(loc, rz, off):
    """World location of a local offset."""
    p = _yaw(off, rz)
    return (loc[0] + p[0], loc[1] + p[1], loc[2] + p[2])


def _box(name, loc, rz, off, size, mat, rot=(0.0, 0.0, 0.0), bevel=None,
         smooth=False):
    """Cube scaled to `size` (metres) at a yawed offset.

    The non-uniform scale is ALWAYS baked into the mesh first: the
    BEVEL modifier's width is local-space, so an unbaked 9 mm chamfer
    on a 196 mm box renders at 1.8 mm (env_props' round-8 trap). The
    bake also puts every vertex in metres, which is what the vertex-
    level sculpting helpers (_bow_plank) need.
    """
    bpy.ops.mesh.primitive_cube_add(size=1, location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.scale = tuple(size)
    bpy.ops.object.transform_apply(location=False, rotation=False,
                                   scale=True)
    o.rotation_euler = (rot[0], rot[1], rot[2] + rz)
    if bevel:
        bm = o.modifiers.new("bev", "BEVEL")
        bm.width, bm.segments = bevel, 4
    if smooth:
        bpy.ops.object.shade_smooth()
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


def _panel(name, a, b, width, thick, mat, bevel=None):
    """Thin slab spanning two WORLD points: local +Y runs a->b (so the
    length is exact), local X is the lateral width, local Z is the
    thickness (the face normal). Aligning the two points with
    to_track_quat("Y","Z") beats a hand-built Euler triple — the fold
    facets are only readable when their normals land where the fold
    says (a 45°-rising facet whose normal came out horizontal would
    read as a stripe painted on the mat). Degenerate vertical
    directions keep the identity roll instead of a NaN quaternion."""
    va, vb = mathutils.Vector(a), mathutils.Vector(b)
    d = vb - va
    bpy.ops.mesh.primitive_cube_add(size=1, location=((va + vb) / 2)[:])
    o = bpy.context.active_object
    o.name = name
    o.scale = (width, d.length, thick)
    bpy.ops.object.transform_apply(location=False, rotation=False,
                                   scale=True)
    if abs(d.normalized().z) < 0.999:
        o.rotation_euler = d.to_track_quat("Y", "Z").to_euler()
    if bevel:
        bm = o.modifiers.new("bev", "BEVEL")
        bm.width, bm.segments = bevel, 3
    S.assign([o], mat)
    return o


def _bmesh_edit(o, fn):
    """Run fn(bm) on the object's mesh (vertex-level sculpting)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    fn(bm)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def _rrect_prism(name, loc, rz, off, w, d, t, r, mat, top=0.0,
                 corner_seg=3, rim_seg=2):
    """Rounded-rectangle slab: a box whose four VERTICAL edges are
    filleted in plan (radius r) and whose top/bottom rims are rolled
    by `top`.

    A BEVEL modifier cannot make this on a 3 mm sheet — it clamps at
    half the thickness and collapses the mat into an octagon — so the
    fillet is cut with bmesh.ops.bevel instead. That is what lets the
    mat's stitched welt follow the mat's TRUE outline rather than a
    guessed rectangle (and the rug's pile get a real soft corner).
    `rz` yaws the finished slab about the anchor's vertical axis; the
    bmesh work is done un-yawed, so local metres stay meaningful.
    """
    bpy.ops.mesh.primitive_cube_add(size=1, location=_land(loc, rz, off))
    o = bpy.context.active_object
    o.name = name
    o.scale = (w, d, t)
    bpy.ops.object.transform_apply(location=False, rotation=False,
                                   scale=True)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    ve = [e for e in bm.edges
          if abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-6
          and abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-6]
    if ve and r > 0.0:
        bmesh.ops.bevel(bm, geom=ve, offset=r, segments=corner_seg,
                        affect="EDGES")
    if top > 0.0:
        he = [e for e in bm.edges
              if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
        if he:
            bmesh.ops.bevel(bm, geom=he, offset=top, segments=rim_seg,
                            affect="EDGES")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o.rotation_euler.z = rz
    S.assign([o], mat)
    return o


def _rrect_outline(hw, hd, r, pitch):
    """Sample a rounded-rectangle outline (centred on the local origin,
    half-extents hw/hd, corner radius r) into (x, y, tangent_angle)
    samples roughly `pitch` metres apart.

    Each straight edge and each corner arc is sampled on its OWN so a
    short corner arc never gets skipped (walking one global arc-length
    counter would cut the corner with a chord and the welt would stop
    following the mat's outline). Angles are in the local frame, ready
    to be yawed with the mat by _box's rot[2] + rz.
    """
    r = max(r, 1.0e-4)
    r = min(r, hw - 1e-5, hd - 1e-5)
    parts = []
    # four FULL straight runs + four quarter arcs, CCW from the +x edge.
    # Each run is one whole edge, not two: splitting the bottom edge in
    # two halves leaves each half shorter than the welt pitch, which
    # silently drops the border's whole south side.
    parts.append((("line", hw, -(hd - r), hw, (hd - r)), 0.0))
    for cxy, a0, a1 in (((hw - r, hd - r), 0.0, math.pi / 2),
                        ((-(hw - r), hd - r), math.pi / 2, math.pi),
                        ((-(hw - r), -(hd - r)), math.pi, 3 * math.pi / 2),
                        ((hw - r, -(hd - r)), 3 * math.pi / 2,
                         2 * math.pi)):
        parts.append((("arc", cxy, a0, a1), r))
    parts.append((("line", hw, hd, -hw, hd), 0.0))
    parts.append((("line", -hw, hd - r, -hw, -(hd - r)), 0.0))
    parts.append((("line", -hw, -hd, hw, -hd), 0.0))

    out = []
    for spec, span in parts:
        if spec[0] == "line":
            _, x0, y0, x1, y1 = spec
            length = math.hypot(x1 - x0, y1 - y0)
            if length < 1e-9:
                continue
            ang = math.atan2(y1 - y0, x1 - x0)
            n = max(1, int(round(length / pitch)))
            step = length / n
            # centre the samples on the run: a box straddling an edge
            # boundary would open a gap in the welt
            ux, uy = (x1 - x0) / length, (y1 - y0) / length
            for i in range(n):
                t = step * (i + 0.5)
                out.append((x0 + ux * t, y0 + uy * t, ang))
        else:
            _, (cx, cy), a0, a1 = spec
            length = abs(a1 - a0) * span
            n = max(2, int(round(length / pitch)))
            da = (a1 - a0) / n
            for i in range(n):
                a = a0 + da * (i + 0.5)
                out.append((cx + span * math.cos(a), cy + span * math.sin(a),
                            a + (math.pi / 2 if a1 > a0 else -math.pi / 2)))
    return out


def _bow_plank(o, amp=0.0025, cuts=20):
    """Cup one plank along its length: a sine arch on the (subdivided)
    mesh whose value is ZERO AT BOTH ENDS, which is what a cupped board
    actually does — its ends land on the same plane as its neighbours
    and the middle rises. The mean is deliberately NOT removed: taking
    it out drops both ends 1.6 mm below the run and notches every seam
    beside the bowed board. A Blender cube has 8 corner vertices, so
    the x edges are subdivided first — without that the arch samples
    nothing but the two ends and renders flat. The BEVEL modifier
    stays on the stack and follows the deformed geometry, which is the
    right order for a chamfer. Local space is metres (_box baked it).
    """
    def _sub(bm):
        xe = [e for e in bm.edges
              if abs(e.verts[0].co.x - e.verts[1].co.x) > 1e-6]
        if xe:
            bmesh.ops.subdivide_edges(bm, edges=xe, cuts=cuts,
                                      use_grid_fill=True)

    _bmesh_edit(o, _sub)

    def _arch(bm):
        xs = [v.co.x for v in bm.verts]
        x0, x1 = min(xs), max(xs)
        if x1 - x0 < 1e-6:
            return
        for v in bm.verts:
            v.co.z += amp * math.sin(math.pi * ((v.co.x - x0) / (x1 - x0)))

    _bmesh_edit(o, _arch)


def _empty(name, loc, off, rot=(0.0, 0.0, 0.0)):
    """Pivot empty (the chair's backrest tilt) — not a mesh, so it is
    never returned to the caller's PROPS list."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.02
    e.location = _land(loc, 0.0, off)
    e.rotation_euler = rot
    bpy.context.collection.objects.link(e)
    return e


def _parent(children, pivot):
    """Parent a group to a pivot, keeping every world transform (python
    parenting does not maintain a parent-inverse by itself — without
    this each child jumps by the pivot and the chair's backrest flies
    across the room)."""
    bpy.context.view_layer.update()
    inv = pivot.matrix_world.inverted()
    for o in children:
        o.parent = pivot
        o.matrix_parent_inverse = inv.copy()


# ------------------------------------------------------ plank desk (1)

DESK_L = 2.40            # the run of boards (scene_env used 2.40 m)
DESK_T = 0.038           # nominal slab thickness (38 mm walnut)
DESK_SEC_GAP = 0.004     # butt-joint gap between two butted sections
SEAM_GAP = 0.0015        # dark shadow gap between adjacent boards
END_W = 0.008            # depth of the end-grain strip cut at each end
END_PROUD = 0.00015      # ... and it stands 0.15 mm clear of the board's
                         # own end face, so its grain face is never
                         # coplanar with the plank's (that pair z-fights)
T_VAR = 0.0004           # +/- sawmill thickness variance (0.4 mm)
Y_JIT = 0.0006           # +/- y jitter (0.6 mm): no perfect plane
SEAM_PROUD = 0.0003      # the dark gap reads as a 0.3 mm shadow line
SEAM_H = 0.040           # gap filler height: clears the plank bottoms
BOW_AMP = 0.0025         # cup height of the bowed board mid-length


def _plank_wood(base, i):
    """Per-board clone of the desk wood: the mapping offset is
    randomised (one material over the whole run reads as printed
    stripes — scene_env's round-19 lesson) and, when the albedo is a
    flat default, the tone is jittered for sawmill variance. A
    procedural Base Color graph (EM.proc_walnut2) is left alone: the
    clone would otherwise silently drop the caller's grain."""
    pm = base.copy()
    pm.name = f"{base.name}_plank{i}"
    rnd = _rnd.Random(9173 + i * 131)
    for nd in pm.node_tree.nodes:
        if nd.type == "MAPPING":
            nd.inputs["Location"].default_value = (
                rnd.random() * 6.0, rnd.random() * 4.0, 0.0)
    bsdf = pm.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None and not bsdf.inputs["Base Color"].is_linked:
        c = bsdf.inputs["Base Color"].default_value
        k = 0.88 + 0.24 * rnd.random()
        bsdf.inputs["Base Color"].default_value = (c[0] * k, c[1] * k,
                                                  c[2] * k, 1.0)
    elif bsdf is not None:
        # round 24: the procedural walnut leaves Base Color LINKED, so
        # the old branch never jittered it and all five boards rendered
        # the same tone ("looks like one printed sheet"). Insert a
        # per-plank multiply after the grain graph.
        src = bsdf.inputs["Base Color"].links[0].from_socket
        nt = pm.node_tree
        mul = nt.nodes.new("ShaderNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        mul.inputs["Fac"].default_value = 1.0
        k = 0.86 + 0.28 * rnd.random()
        mul.inputs["Color2"].default_value = (k, k, k, 1.0)
        nt.links.new(src, mul.inputs["Color1"])
        nt.links.new(mul.outputs["Color"], bsdf.inputs["Base Color"])
    return pm


def build_plank_desk(loc, mats, planks=(5,), plank_w=0.211, rot_z=0.0):
    """The plank desk: real boards, not five boxes.

    Per board: a chamfered top edge, an END-GRAIN strip cut at
    each end of the run (the short face of a plank shows grain, not
    the face's long ragwork — that strip is why a real plank desk
    reads as timber and not as painted MDF), a dark shadow-gap filler
    between boards, a +/-0.4 mm sawmill thickness variance and a
    +/-0.6 mm y jitter so the surface never lies in one plane, and one
    board cupped 2.5 mm over its length with its ENDS left on the plane
    (a 2.4 m board is never dead flat — the cup is what gives a
    hardwood top its long raking highlight, and a taller arch would
    show as a gap under the desk mat).

    `loc` = the TOP-surface centre of the plank run (the keyboard and
    the mat rest on it); the boards are hung from that top reference so
    their undersides share one plane while their TOPS ripple with the
    sawmill variance. `planks` may be an int or a tuple of ints: a
    tuple builds that many BUTTED SECTIONS along x (each section keeps
    its own plank count and both of its ends show end grain), so
    planks=(5,) is one 2.40 m run and planks=(3,2) reads as two slabs
    joined with a 4 mm shadow gap.
    """
    rz = rot_z
    counts = [int(p) for p in
              ((planks,) if isinstance(planks, int) else tuple(planks))]
    n = sum(counts)
    depth = n * plank_w

    m_wood = _M(mats, "wood", lambda: S.micro_texture(
        S.pbr("dsk_walnut", (0.145, 0.082, 0.045), rough=0.42),
        620, 0.16, 0.00028, 0.34, 0.50, detail=5.0))
    m_end = _M(mats, "end_grain", lambda: S.micro_texture(
        S.pbr("dsk_endgrain", (0.30, 0.205, 0.125), rough=0.56),
        1400, 0.30, 0.00010, 0.46, 0.66, detail=4.0))
    m_seam = _M(mats, "seam", lambda: S.pbr(
        "dsk_seam", (0.016, 0.011, 0.008), rough=0.95))

    objs = []
    n_sec = len(counts)
    usable = DESK_L - DESK_SEC_GAP * (n_sec - 1)
    x0 = -DESK_L / 2.0
    g = 0                                   # global plank index
    for si, cnt in enumerate(counts):
        L = usable * cnt / n
        xc = x0 + L / 2.0
        for i in range(cnt):
            g += 1
            rnd = _rnd.Random(8111 + g * 977)
            t = DESK_T + rnd.uniform(-T_VAR, T_VAR)
            dy = rnd.uniform(-Y_JIT, Y_JIT)
            yc = (g - 0.5) * plank_w - depth / 2.0 + dy
            # hung from the TOP reference: the underside shares one
            # plane, so the +/-0.4 mm variance lands on the surface the
            # keyboard and the mat actually sit on
            zc = -DESK_T + t / 2.0
            o = _box(f"dsk_plank_{si}_{i}", loc, rz, (xc, yc, zc),
                     (L, plank_w - SEAM_GAP, t),
                     _plank_wood(m_wood, g - 1), bevel=0.0015)
            objs.append(o)
            if g == n // 2:                 # the bowed board: mid-run
                _bow_plank(o, BOW_AMP)
            # end-grain strips: both short faces of the run of boards,
            # standing 0.15 mm proud of the board's own end face
            for sgn, tag in ((-1.0, "L"), (1.0, "R")):
                objs.append(_box(
                    f"dsk_end_{tag}_{si}_{i}", loc, rz,
                    (xc + sgn * (L / 2.0 - END_W / 2.0 + END_PROUD), yc,
                     zc),
                    (END_W, plank_w - SEAM_GAP, t), m_end,
                    bevel=0.0006))
        # dark shadow-gap filler between this section's boards: tall
        # enough to clear the plank undersides, only 0.3 mm proud so it
        # reads as a shadow line and not as a ridge
        szo = SEAM_PROUD - SEAM_H / 2.0
        for k in range(1, cnt):
            yb = (g - cnt + k) * plank_w - depth / 2.0
            objs.append(_box(f"dsk_seam_{si}_{k}", loc, rz,
                             (xc, yb, szo),
                             (L, SEAM_GAP + 0.0003, SEAM_H), m_seam))
        # and the butt joint between this section and the next
        if si < n_sec - 1:
            objs.append(_box(f"dsk_secseam_{si}", loc, rz,
                             (xc + L / 2.0 + DESK_SEC_GAP / 2.0, 0.0, szo),
                             (DESK_SEC_GAP + 0.0004, depth + 0.0010,
                              SEAM_H), m_seam))
        x0 += L + DESK_SEC_GAP
    return objs


# --------------------------------------------------------- desk mat (2)

MAT_W, MAT_D, MAT_T = 0.900, 0.400, 0.003    # the classic 900x400 mat
MAT_R = 0.010          # fillet radius of the mat's outline (plan)
MAT_EDGE = 0.0012      # roll on the top rim (~1.2 mm edge banding)
WELT_INSET = 0.010     # the stitched border sits 10 mm in
WELT_PITCH = 0.0075    # welt pitch (the round-19 stitch pitch)
WELT_SEG = 0.0055      # one welt piece, along the outline
WELT_W = 0.0022        # one welt piece, across the outline
WELT_H = 0.0018        # piece height: 1.65 mm proud of the mat
FOLD_F = 0.016         # dog-ear legs: a 16 mm "small 20 mm" fold
FOLD_ROOT = 0.0008     # the facets' roots are buried this deep
# ridge height that puts the two facets at EXACTLY 60 deg: with the
# legs at right angles in plan, cos(theta) = (dz^2 - f^2/2)/(dz^2 +
# f^2/2) = 0.5  ->  dz = sqrt(1.5) * f. dz is measured from the buried
# root, so the ridge sits sqrt(1.5)*FOLD_F - FOLD_ROOT above the sheet.
FOLD_H = math.sqrt(1.5) * FOLD_F - FOLD_ROOT     # ~18.8 mm


def build_desk_mat(loc, mats, rot_z=0.0):
    """The fabric desk mat: a real sheet with a folded corner.

    Form, in render order:
      * body — a 3 mm rounded-rect slab whose plan corners are filleted
        10 mm and whose top rim is rolled 1.2 mm (the edge banding of
        a real bound mat). The fillet is cut in bmesh, not a BEVEL
        modifier: a modifier clamps at half the sheet thickness and
        would octagon the mat (see _rrect_prism).
      * ONE folded corner at the front-left: two 16 mm panels that
        leave the mat's own surface (their roots are buried 0.8 mm
        into the sheet, so they emerge from it rather than float) and
        meet 58 deg apart on a raised ridge — the dog-ear you get when
        a mat has been kicked. A dark crease strip lies along the fold
        line so the join reads in shadow, not just in highlight.
      * the stitched border — a CONTINUOUS raised welt: a loop of small
        boxes standing 1.65 mm proud along the mat's true outline at a
        7.5 mm pitch, each oriented by the outline's own tangent. It is
        not decoration: it catches the grazing key light as a dotted
        ridge and marks the mat's edge against the walnut.
    `loc` = the mat's UNDERSIDE centre (what it lies on).
    """
    rz = rot_z
    m_fabric = _M(mats, "fabric", lambda: S.micro_texture(
        S.pbr("mat_fabric", (0.055, 0.058, 0.066), rough=0.85),
        700, 0.35, 0.00008, 0.78, 0.95, detail=5.0))
    # round 24: cream welt read as a string of pearls. A tonal
    # stitch (dark taupe, same family as the fabric) reads as an edge.
    m_welt = _M(mats, "welt", lambda: S.micro_texture(
        S.pbr("mat_welt", (0.165, 0.148, 0.122), rough=0.72),
        900, 0.20, 0.00006, 0.60, 0.78, detail=4.0))
    m_fold = _M(mats, "fold", lambda: S.micro_texture(
        S.pbr("mat_fold", (0.040, 0.042, 0.050), rough=0.88),
        700, 0.30, 0.00008, 0.80, 0.96, detail=4.0))
    m_crease = _M(mats, "crease", lambda: S.pbr(
        "mat_crease", (0.012, 0.013, 0.016), rough=0.92))

    objs = []
    # ---- the sheet. loc is the UNDERSIDE, so the slab is lifted by
    # half its thickness: the top surface lands on loc.z + MAT_T.
    objs.append(_rrect_prism("mat_body", loc, rz, (0.0, 0.0, MAT_T / 2.0),
                             MAT_W, MAT_D, MAT_T, MAT_R, m_fabric,
                             top=MAT_EDGE))

    # ---- the folded corner (front-left = -x, -y in the local frame)
    x0, y0 = -MAT_W / 2.0, -MAT_D / 2.0
    top = MAT_T
    # roots sink 0.8 mm into the sheet so the facets grow out of it
    root = top - 0.0008
    A = (x0 + FOLD_F, y0, root)            # on the front edge
    B = (x0, y0 + FOLD_F, root)            # on the left edge
    R = (x0 + FOLD_F / 2.0, y0 + FOLD_F / 2.0, top + FOLD_H)   # the ridge
    wA, wB, wR = (_land(loc, rz, p) for p in (A, B, R))
    objs.append(_panel("mat_fold_a", wA, wR, 0.014, 0.0015, m_fold,
                       bevel=0.0004))
    objs.append(_panel("mat_fold_b", wB, wR, 0.014, 0.0015, m_fold,
                       bevel=0.0004))
    # the crease the flap lifts along: a dark seam on the sheet
    objs.append(_panel("mat_fold_crease", wA, wB, 0.0016, 0.0008, m_crease))

    # ---- the stitched border (round 24c) -------------------------
    # A real bound mat shows TWO things: a raised edge band (the folded
    # and glued rim) and the stitch run that binds it. The old welt was
    # a single loop of raised boxes -- a dotted ridge, read as "a
    # string of pearls". Now: a continuous rounded rim band, plus a
    # denser stitch run on top of it, each stitch TWISTED +/-20 deg off
    # the tangent so the run reads as thread, and sunk 0.35 mm into the
    # band so it looks sewn into it rather than glued on.
    hw = MAT_W / 2.0 - WELT_INSET
    hd = MAT_D / 2.0 - WELT_INSET
    wr = max(0.0015, MAT_R - WELT_INSET)
    for i, (px, py, ang) in enumerate(_rrect_outline(hw, hd, wr, 0.018)):
        objs.append(_box(f"mat_rim_{i:03d}", loc, rz,
                         (px, py, top + 0.00055),
                         (0.0195, 0.0072, 0.0016), m_fabric,
                         rot=(0.0, 0.0, ang)))
    for i, (px, py, ang) in enumerate(_rrect_outline(hw, hd, wr, 0.0042)):
        tw = 20.0 if (i % 2 == 0) else -20.0
        objs.append(_box(f"mat_stitch_{i:03d}", loc, rz,
                         (px, py, top + 0.00115),
                         (0.0034, 0.0011, 0.00065), m_welt,
                         rot=(0.0, 0.0, ang + tw)))
    # a woven maker's label, sewn at the back-right corner: small, dark,
    # with its own finer weave -- the detail that says "product"
    lx = hw - 0.030
    ly = hd - 0.016
    objs.append(_box("mat_label", loc, rz, (lx, ly, top + 0.00035),
                     (0.030, 0.014, 0.0007), m_welt, rot=(0.0, 0.0, 90.0)))
    return objs


# -------------------------------------------------------------- room (3)

WALL_W, WALL_T, WALL_H = 3.60, 0.045, 2.60
FLOOR_D, FLOOR_T = 2.60, 0.012
BB_LO_H, BB_HI_H = 0.014, 0.032   # the two stepped skirting boards
BB_LO_D, BB_HI_D = 0.024, 0.016    # ... and their different y-depth
BB_CAP_H, BB_CAP_D = 0.006, 0.020
RAIL_H, RAIL_Z = 0.034, 1.00       # chair-rail height + section height
RAIL_D = 0.014
RAIL_SPLIT_X = 0.60                # trims are two stock lengths
SPLIT_GAP = 0.002
# every trim stands this far in FRONT of the plaster: a face coplanar
# with the wall's would z-fight, and the 1.5 mm shadow gap behind the
# moulding is what the shadow-line boxes read against
TRIM_PROUD = 0.0015
# the painted shadow lines are projected 1.5 mm proud too (0.3 mm shy
# of the trims), so they read as dark lines on the plaster
LINE_PROUD = 0.0012
LINE_D = 0.005
RUG_W, RUG_D, RUG_T = 1.90, 1.20, 0.004     # 4 mm pile
RUG_FIELD_INSET = 0.16


def _trim_run(name, loc, rz, x0, x1, y_off, depth, height, mat, seam_mat,
              bevel=None, z=0.0, step=0.0015):
    """One trim moulding run, built as TWO stock lengths with a real
    gap between them. A single full-length box reads as an extruded CGI
    rail; the black gap filler plus the `step` y offset on the far
    length is what makes the moulding read as site-fitted boards that
    were scribed to a wall that is not straight. Returns
    [board_0, board_1, seam]."""
    objs = []
    for side, (a, b) in enumerate(((x0, RAIL_SPLIT_X),
                                   (RAIL_SPLIT_X + SPLIT_GAP, x1))):
        dy = y_off + (step if side else 0.0)
        objs.append(_box(f"{name}_{side}", loc, rz,
                         ((a + b) / 2.0, dy, z),
                         (b - a, depth, height), mat, bevel=bevel))
    objs.append(_box(f"{name}_seam", loc, rz,
                     (RAIL_SPLIT_X + SPLIT_GAP / 2.0,
                      y_off + step / 2.0, z),
                     (SPLIT_GAP + 0.0006, depth * 2.0, height + 0.0012),
                     seam_mat))
    return objs


def build_room(loc, mats, rot_z=0.0):
    """The room: plaster wall, skirting, chair rail, floor and the rug.

    The wall stays deliberately FLAT (the brief's call — a bent wall
    reads as a modelling error, not as plaster), so the room's 3D work
    lives in the trims:
      * a shadow-line groove cut into the plaster just above the
        skirting, so the trim casts a real line onto the flat wall
        instead of reading as a sticker;
      * a two-piece baseboard — a lower board 24 mm deep and an upper
        board 16 mm deep, stepped, with a dark filler in their joint —
        the profile you actually get from a site-fitted skirting, and
        a chamfered cap strip on top;
      * the same moulding language repeated higher up as a chair rail,
        split into two lengths on the RAIL_SPLIT_X line with a 1.5 mm
        y step, so the two runs of trim agree;
      * a floor plane and, under the desk area, a dark rug: a
        rounded-rect pile 4 mm high with a rolled edge and a raised
        woven field inset 160 mm (the two tones + the 1.5 mm step are
        the border) — a bare floor is what made the desk look like it
        was floating in a studio.
    `loc` = the wall's inner face at FLOOR level: floor top is
    loc.z, the plaster runs back from loc.y toward +y.
    """
    rz = rot_z
    m_wall = _M(mats, "wall", lambda: S.micro_texture(
        S.pbr("room_wall", (0.415, 0.395, 0.370), rough=0.88),
        260, 0.30, 0.00012, 0.80, 0.96, detail=5.0))
    m_trim = _M(mats, "trim", lambda: S.micro_texture(
        S.pbr("room_trim", (0.78, 0.76, 0.72), rough=0.52),
        420, 0.12, 0.00005, 0.42, 0.60, detail=4.0))
    m_shadow = _M(mats, "shadow", lambda: S.pbr(
        "room_shadow", (0.020, 0.019, 0.018), rough=0.95))
    m_floor = _M(mats, "floor", lambda: S.micro_texture(
        S.pbr("room_floor", (0.050, 0.045, 0.040), rough=0.80),
        700, 0.28, 0.00010, 0.70, 0.90, detail=4.0))
    m_rug = _M(mats, "rug", lambda: S.micro_texture(
        S.pbr("room_rug", (0.043, 0.048, 0.052), rough=0.95),
        850, 0.45, 0.00035, 0.86, 0.99, detail=4.0))
    m_rug_field = _M(mats, "rug_field", lambda: S.micro_texture(
        S.pbr("room_rug_field", (0.062, 0.068, 0.074), rough=0.94),
        640, 0.40, 0.00030, 0.84, 0.98, detail=4.0))

    objs = []
    hw = WALL_W / 2.0

    # ---- the wall: flat plaster, and a shadow-line on its face just
    # above the skirting (proud of the plaster, so it READS as a line
    # rather than hiding inside the wall's own volume). The slab runs
    # BACKWARD from loc.y (+y): the inner face IS loc.y, so every trim
    # at a negative y stands proud of it instead of being buried 45 mm
    # inside the plaster (that sign error hid the whole skirting).
    objs.append(_box("room_wall", loc, rz, (0.0, WALL_T / 2.0,
                                            WALL_H / 2.0),
                     (WALL_W, WALL_T, WALL_H), m_wall))
    groove_z = BB_HI_H + BB_CAP_H + 0.002
    objs.append(_box("room_wall_shadowline", loc, rz,
                     (0.0, -(LINE_PROUD + LINE_D / 2.0),
                      groove_z + 0.002),
                     (WALL_W, LINE_D, 0.004), m_shadow))

    # ---- the two-piece baseboard: a deep lower board, a shallower
    # upper board, a chamfered cap, and a dark filler in their joint
    objs += _trim_run("room_base_lo", loc, rz, -hw, hw,
                      -(BB_LO_D / 2.0) - TRIM_PROUD,
                      BB_LO_D, BB_LO_H, m_trim, m_shadow,
                      z=BB_LO_H / 2.0)
    objs += _trim_run("room_base_hi", loc, rz, -hw, hw,
                      -(BB_HI_D / 2.0) - TRIM_PROUD - 0.001, BB_HI_D,
                      BB_HI_H - BB_LO_H, m_trim, m_shadow,
                      z=(BB_LO_H + BB_HI_H) / 2.0)
    objs += _trim_run("room_base_cap", loc, rz, -hw, hw,
                      -(BB_CAP_D / 2.0) - TRIM_PROUD,
                      BB_CAP_D, BB_CAP_H, m_trim, m_shadow, bevel=0.0015,
                      z=BB_HI_H + BB_CAP_H / 2.0)
    objs.append(_box("room_base_joint", loc, rz,
                     (0.0, -(BB_LO_D / 2.0) - TRIM_PROUD, BB_LO_H),
                     (WALL_W, BB_LO_D + 0.006, 0.0012), m_shadow))

    # ---- the chair rail (the same two-length language, 1.00 m up)
    objs += _trim_run("room_rail", loc, rz, -hw, hw,
                      -(RAIL_D / 2.0) - TRIM_PROUD,
                      RAIL_D, RAIL_H, m_trim, m_shadow, bevel=0.004,
                      z=RAIL_Z)
    objs.append(_box("room_rail_shadow", loc, rz,
                     (0.0, -(LINE_PROUD + LINE_D / 2.0),
                      RAIL_Z - RAIL_H / 2.0 - 0.0015),
                     (WALL_W, LINE_D, 0.003), m_shadow))

    # ---- the floor plane, tucked under the wall
    objs.append(_box("room_floor", loc, rz,
                     (0.0, -(FLOOR_D / 2.0 - 0.02), -FLOOR_T / 2.0),
                     (WALL_W, FLOOR_D, FLOOR_T), m_floor))
    # ---- the dark rug under the desk area: 4 mm pile standing ON the
    # floor, rounded rect, rolled edge, plus a raised woven field inset
    # 160 mm (the two tones and the 1.5 mm step are the border — a
    # second loop of boxes would cost 90 objects for the same read and
    # would fight the floor's own shadow)
    ry = -0.62
    objs.append(_rrect_prism("room_rug", loc, rz,
                             (0.0, ry, RUG_T / 2.0),
                             RUG_W, RUG_D, RUG_T, 0.030, m_rug,
                             top=0.0018))
    objs.append(_rrect_prism("room_rug_field", loc, rz,
                             (0.0, ry, RUG_T / 2.0 + 0.00075),
                             RUG_W - 2 * RUG_FIELD_INSET,
                             RUG_D - 2 * RUG_FIELD_INSET, RUG_T + 0.0015,
                             0.018, m_rug_field, top=0.0018))
    return objs


# ------------------------------------------------------------- chair (4)

CHAIR_LEG_R = 0.335      # star-base leg reach
CHAIR_COL_H = 0.30       # gas-lift column height
CHAIR_SEAT_W, CHAIR_SEAT_D = 0.50, 0.48
CHAIR_SEAT_T = 0.058
CHAIR_TILT = math.radians(7.0)
# caster wheel: a flat torus, so its outer radius is R + r and its
# centre must sit at exactly that height to touch the floor (the first
# pass centred it on the minor radius and sank every wheel 24 mm
# through the floor). The tube's top tucks up into the leg's foot pad.
WHEEL_R, WHEEL_r = 0.016, 0.008
WHEEL_Z = WHEEL_R + WHEEL_r            # 24 mm -> the wheel touches z=0


def build_chair(loc, mats, rot_z=0.0):
    """A simple office-chair silhouette for the dev scene: ~40 real
    primitives, matte nylon + a dark mesh, standing on five slanted
    legs with caster wheels.

    Form choices that have to survive a wide shot: the star legs are
    CHAMFERED slabs (a bare cylinder reads as a stool stand), each with
    its own caster built as a stem + a flat torus wheel that actually
    touches the floor; the gas column is split into a chrome tube, a
    dark dust sleeve and a collar so it reads as a lift, not a pole;
    the seat is a rounded pad over a thin pan with a waterfall front
    lip; the backrest is a frame + a dark mesh panel + a lumbar pillow
    and a headrest hint, all parented to a pivot empty and tilted 7 deg
    back about the seat's rear edge. Built facing +y (the brief): the
    seat's waterfall edge is at +y, the backrest behind it at -y.
    `loc` = the floor point under the chair's column.
    """
    rz = rot_z
    m_frame = _M(mats, "frame", lambda: S.micro_texture(
        S.pbr("chair_frame", (0.055, 0.056, 0.060), rough=0.62),
        300, 0.18, 0.00006, 0.52, 0.70, detail=4.0))
    m_plastic = _M(mats, "plastic", lambda: S.micro_texture(
        S.pbr("chair_plastic", (0.085, 0.086, 0.092), rough=0.55),
        360, 0.16, 0.00005, 0.46, 0.64, detail=4.0))
    m_mesh = _M(mats, "mesh", lambda: S.micro_texture(
        S.pbr("chair_mesh", (0.030, 0.031, 0.034), rough=0.85),
        620, 0.45, 0.00012, 0.76, 0.95, detail=5.0))
    m_chrome = _M(mats, "chrome", lambda: S.micro_texture(
        S.pbr("chair_chrome", (0.62, 0.63, 0.66), rough=0.24, metal=1.0),
        420, 0.05, 0.00001, 0.18, 0.30))
    m_caster = _M(mats, "caster", lambda: S.micro_texture(
        S.pbr("chair_caster", (0.028, 0.028, 0.031), rough=0.70),
        380, 0.22, 0.00005, 0.60, 0.78, detail=4.0))
    m_seat = _M(mats, "pad", lambda: S.micro_texture(
        S.pbr("chair_pad", (0.070, 0.070, 0.076), rough=0.80),
        500, 0.30, 0.00010, 0.72, 0.90, detail=4.0))

    objs = []
    o = _cyl("chair_hub", loc, rz, (0.0, 0.0, 0.066), 0.048, 0.024, m_frame)
    objs.append(o)
    objs.append(_cyl("chair_hub_disc", loc, rz, (0.0, 0.0, 0.052), 0.044,
                     0.010, m_plastic))

    # ---- 5-star base: slanted chamfered legs, foot pads, caster stems
    # and wheels that touch the floor at z = 0
    for k in range(5):
        a = k * 2.0 * math.pi / 5.0
        sx, sy = math.sin(a), math.cos(a)
        A = (0.0, 0.0, 0.058)
        B = (CHAIR_LEG_R * sx, CHAIR_LEG_R * sy, 0.030)
        objs.append(_panel(f"chair_leg_{k}", _land(loc, rz, A),
                           _land(loc, rz, B), 0.050, 0.020, m_frame,
                           bevel=0.004))
        objs.append(_box(f"chair_legpad_{k}", loc, rz,
                         (B[0], B[1], B[2] + 0.002),
                         (0.062, 0.040, 0.016), m_frame,
                         rot=(0.0, 0.0, a), bevel=0.003))
        objs.append(_cyl(f"chair_caster_stem_{k}", loc, rz,
                         (B[0], B[1], (0.024 + 0.050) / 2.0), 0.0065,
                         0.026, m_plastic, verts=20))
        objs.append(_tor(f"chair_caster_{k}", loc, rz,
                         (B[0], B[1], WHEEL_Z), WHEEL_R, WHEEL_r,
                         m_caster, rot=(math.pi / 2.0, 0.0, 0.0)))

    # ---- gas column: chrome tube, dark sleeve, collar, mech housing
    z0 = 0.075
    objs.append(_cyl("chair_column", loc, rz, (0.0, 0.0,
                                               z0 + CHAIR_COL_H / 2.0),
                     0.024, CHAIR_COL_H, m_chrome))
    objs.append(_cyl("chair_sleeve", loc, rz, (0.0, 0.0, z0 + 0.045),
                     0.030, 0.090, m_plastic))
    objs.append(_cyl("chair_collar", loc, rz, (0.0, 0.0,
                                               z0 + CHAIR_COL_H + 0.011),
                     0.028, 0.022, m_plastic))
    objs.append(_box("chair_mech", loc, rz, (0.0, 0.010, 0.418),
                     (0.130, 0.120, 0.055), m_plastic, bevel=0.008))

    # ---- seat: pan, rounded pad, waterfall front lip (+y edge)
    objs.append(_box("chair_pan", loc, rz, (0.0, 0.0, 0.447),
                     (0.440, 0.420, 0.014), m_plastic))
    objs.append(_box("chair_pad", loc, rz, (0.0, 0.0, 0.483),
                     (CHAIR_SEAT_W, CHAIR_SEAT_D, CHAIR_SEAT_T), m_seat,
                     bevel=0.014))
    objs.append(_box("chair_waterfall", loc, rz, (0.0, 0.245, 0.462),
                     (CHAIR_SEAT_W, 0.090, 0.030), m_seat,
                     rot=(math.radians(-8.0), 0.0, 0.0), bevel=0.004))

    # ---- backrest, parented to a tilt pivot at the seat's rear edge
    piv = _empty("chair_back_pivot", loc, (0.0, -0.20, 0.50),
                 rot=(CHAIR_TILT, 0.0, rz))
    back = []
    back.append(_box("chair_back_post_l", loc, 0.0, (-0.215, 0.0, 0.25),
                     (0.030, 0.032, 0.50), m_frame, bevel=0.005))
    back.append(_box("chair_back_post_r", loc, 0.0, (0.215, 0.0, 0.25),
                     (0.030, 0.032, 0.50), m_frame, bevel=0.005))
    back.append(_box("chair_back_top", loc, 0.0, (0.0, 0.0, 0.50),
                     (0.460, 0.034, 0.030), m_frame, bevel=0.006))
    back.append(_box("chair_back_bot", loc, 0.0, (0.0, 0.0, 0.02),
                     (0.460, 0.034, 0.026), m_frame, bevel=0.005))
    # the mesh: a dark panel on the sitter's side of the frame, proud
    back.append(_box("chair_back_mesh", loc, 0.0, (0.0, 0.013, 0.2625),
                     (0.395, 0.014, 0.445), m_mesh))
    back.append(_box("chair_lumbar", loc, 0.0, (0.0, 0.030, 0.100),
                     (0.300, 0.040, 0.110), m_mesh, bevel=0.010))
    # headrest hint: a small pad on two short posts above the frame
    back.append(_box("chair_head_post_l", loc, 0.0, (-0.090, 0.0, 0.462),
                     (0.024, 0.024, 0.030), m_frame))
    back.append(_box("chair_head_post_r", loc, 0.0, (0.090, 0.0, 0.462),
                     (0.024, 0.024, 0.030), m_frame))
    back.append(_box("chair_headrest", loc, 0.0, (0.0, 0.004, 0.505),
                     (0.260, 0.046, 0.075), m_seat, bevel=0.014))
    # support posts from the seat pan into the frame's lower corners
    back.append(_box("chair_back_sup_l", loc, 0.0, (-0.185, -0.175, 0.450),
                     (0.026, 0.026, 0.130), m_frame))
    back.append(_box("chair_back_sup_r", loc, 0.0, (0.185, -0.175, 0.450),
                     (0.026, 0.026, 0.130), m_frame))
    _parent(back, piv)
    objs += back
    return objs

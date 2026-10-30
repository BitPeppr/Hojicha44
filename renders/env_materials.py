"""Hojicha44 environment materials, round 9 -- HIGH-QUALITY procedurals.

Replaces the texture side of scene_env's round-8 pass, whose walnut
the user rejected as "far too low-quality". Every material below is
built around ONE idea the round-8 set lacked: DOMAIN WARPING. A wave
or noise sampled on straight coordinates can only ever read as
stripes or static; real materials are the same patterns pushed
through a slowly-varying vector field, so the bands MEANDER. The
_warp() helper chains mapping -> noise -> VectorMath(SUBTRACT/SCALE/
ADD) and is used at two scales everywhere below -- a broad wander
(what your eye reads as organic) plus a fine wiggle (what your eye
reads as physical).

DESIGN FRAME / COORDINATE RULES
  * Texture space is GENERATED (per-object bbox 0..1), the scene_env
    convention. That makes every scale here HOST-RELATIVE: a value
    is a feature count across the host's bbox, not an absolute
    millimetre pitch. Numbers are chosen for the real hosts and
    quoted in the comments (desk 2.4x1.06 m, page block 11 mm
    stack, PCB bbox ~120x45 mm, 1 m smoke-test cards).
  * Where a TRUE physical pitch must survive on differently-sized
    faces of one object (the notebook's sheet stack), the comment
    says so and the graph is built accordingly.
  * Warp noise is sampled on its own gently-anisotropic mapping,
    never on the heavily stretched pattern vector: sampling it there
    would make the wander as anisotropic as the pattern itself and
    shred the rings into noise (the exact failure that made the
    round-8 walnut read as blotches rather than wood).

Usage (from scene_env.py):
    import env_materials as EM
    m_desk = EM.proc_walnut2("env_walnut")
    m_floor = EM.proc_marble("env_floor")
    ...

Every function returns a ready material; calls are idempotent within
a session (marker property, the same guard scene.py's micro_texture
uses) so shared materials can be rebuilt harmlessly.
"""
import math

import bpy

_TAG = "env_materials_r9"   # idempotency marker on the material


# ---------------------------------------------------------------- helpers

def _fresh(name):
    """Get-or-build guard. Returns (mat, node_tree); the tree is None
    when the material was already built this session, so callers can
    return early and stay idempotent (materials are shared between
    halves/props, like scene.py's micro_texture)."""
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
    if bsdf is None:                      # defensive: stripped tree
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output")
        if out is not None:
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _set(bsdf, key, value):
    """Probe-and-set a Principled input (Emission was renamed across
    Blender 4/5, Coat inputs may be absent in trimmed builds) -- never
    crash, just skip when the socket is missing."""
    try:
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
            return True
    except Exception:
        pass
    return False


def _noise(nt, scale, detail, rough=0.55, name="noise"):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.label = name
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rough
    return nz


def _mapping(nt, scale=(1.0, 1.0, 1.0), location=(0.0, 0.0, 0.0),
             rotation=(0.0, 0.0, 0.0), name="mapping"):
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.label = name
    mp.inputs["Scale"].default_value = tuple(scale)
    mp.inputs["Location"].default_value = tuple(location)
    mp.inputs["Rotation"].default_value = tuple(rotation)
    return mp


def _wave(nt, scale, distortion, detail, detail_scale,
          bands="X", name="wave"):
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
    """ValToRGB with arbitrary sorted stops [(pos, (r, g, b)), ...].
    B_SPLINE for organic fades (wood, marble, paper), LINEAR where a
    stop is a MASK edge that must stay crisp (trace spikes)."""
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


def _warp(nt, vec, nvec, scale, detail, strength, rough=0.55,
          name="warp"):
    """The distortion chain that makes these materials read as real:
        vec + (noise(nvec) - 0.5) * strength
    `vec` is the pattern's (possibly anisotropic) coordinate; `nvec`
    is where the warp FIELD is sampled -- pass a gently-scaled mapping
    so the wander stays broad on the stretched axis. The noise Color
    output is a per-axis field, so the pattern bends differently in x
    and y. `strength` is in the same units as `vec`, so it must be
    small whenever `vec` is heavily scaled (a shift of one band
    period = 1/wave_scale in those units)."""
    L = nt.links.new
    nz = _noise(nt, scale, detail, rough, name)
    L(nvec, nz.inputs["Vector"])
    half = nt.nodes.new("ShaderNodeCombineXYZ")
    half.label = f"{name}_half"
    half.inputs["X"].default_value = 0.5
    half.inputs["Y"].default_value = 0.5
    half.inputs["Z"].default_value = 0.5
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.label = f"{name}_center"; sub.operation = "SUBTRACT"
    L(nz.outputs["Color"], sub.inputs[0])
    L(half.outputs["Vector"], sub.inputs[1])
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.label = f"{name}_strength"; sc.operation = "SCALE"
    try:
        sc.inputs["Scale"].default_value = strength
    except Exception:
        sc.inputs[1].default_value = strength
    L(sub.outputs["Vector"], sc.inputs[0])
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.label = f"{name}_add"; add.operation = "ADD"
    L(vec, add.inputs[0])
    L(sc.outputs["Vector"], add.inputs[1])
    return add.outputs["Vector"]


def _mix(nt, blend, name="mix"):
    m = nt.nodes.new("ShaderNodeMixRGB")
    m.label = name
    m.blend_type = blend
    m.inputs["Fac"].default_value = 1.0
    return m


def _math(nt, op, name="math", a=None, b=None, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.label = name
    m.operation = op
    m.use_clamp = clamp
    if a is not None:
        m.inputs[0].default_value = a
    if b is not None:
        m.inputs[1].default_value = b
    return m


def _bump(nt, strength, distance, name="bump"):
    b = nt.nodes.new("ShaderNodeBump")
    b.label = name
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    return b


def _maprange(nt, to_min, to_max, name="range"):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.label = name
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = to_min
    mr.inputs["To Max"].default_value = to_max
    return mr


# ------------------------------------------------------------- materials

def proc_walnut2(name):
    """Flagship desk wood: oiled walnut that survives a 0.2 mm/px closeup.

    Growth rings: bands across the face at ~62 periods per bbox-width
    (~17 mm on the 1.06 m desk depth), warped twice (broad +-4 mm
    drift over ~13 cm, fine +-1.3 mm edge-curl over ~1.5 cm) plus the
    wave's own distortion for ragged latewood edges. A 5-stop ramp
    runs umber heartwood -> honey; the ramp's natural discontinuity at
    the period wrap IS the sharp latewood line, B_SPLINE keeps the
    earlywood fade soft. A SECOND broad noise wash MULTIPLIES the ramp
    (never a grey mix -- that flattens contrast, the round-8 lesson in
    scene_env.proc_wood) for warm/cool figure zones. Pores ride a
    second anisotropic ~5:1 coordinate with the same warp trick, so
    the pore flow follows the ring wander: fine ~2 mm flecks plus
    occasional 30 cm grain channels thresholded out of a high-
    contrast noise. Roughness rides the pores (0.30 intact, 0.46 in
    the pores) and a 0.12 coat supplies the oiled sheen."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")

    # ---- ring space (round 24 rebuild) -------------------------------
    # The old graph was a Wave BANDS field on a 1:62 mapping: perfect
    # parallel stripes ~3 mm apart. Warping the VECTOR can only bend
    # those stripes; it can never produce cathedral FIGURE, because the
    # band spacing stays constant along the board. Real flat-sawn
    # walnut reads because the growth rings drift in and out of the
    # cut plane: the lines bunch, fan and pinch along the grain.
    #
    # So the ring coordinate is now
    #     c = y * RINGS + phase(x, y)
    # where `phase` is a broad noise field. The gradient of the phase
    # adds to (or cancels) the ring frequency, which is exactly how
    # bands spread apart and squeeze together. The phase also drifts
    # along X at 15-30 cm wavelength, so the figure runs down the
    # board instead of lying in dead-straight rails.
    #
    # RINGS = 5.0 on a 211 mm plank = ~42 mm between latewood lines:
    # at the desk camera (0.43 px/mm) that is ~18 px -- figure, not
    # pinstripes. The thin dark stop at the period wrap is the
    # latewood line (0.6 mm, sub-pixel: it reads as grain, not a rule).
    mp_phys = _mapping(nt, (0.088, 1.0, 1.0), name="phys_space")
    L(tc.outputs["Generated"], mp_phys.inputs["Vector"])
    phase_nz = _noise(nt, 1.6, 3.0, 0.55, name="figure_drift")
    L(mp_phys.outputs["Vector"], phase_nz.inputs["Vector"])
    phase_c = nt.nodes.new("ShaderNodeVectorMath")
    phase_c.label = "phase_centred"; phase_c.operation = "SUBTRACT"
    L(phase_nz.outputs["Color"], phase_c.inputs[0])
    phase_half = nt.nodes.new("ShaderNodeCombineXYZ")
    phase_half.inputs["X"].default_value = 0.5
    phase_half.inputs["Y"].default_value = 0.5
    phase_half.inputs["Z"].default_value = 0.5
    L(phase_half.outputs["Vector"], phase_c.inputs[1])
    phase_amp = nt.nodes.new("ShaderNodeVectorMath")
    phase_amp.label = "phase_amp"; phase_amp.operation = "SCALE"
    try:
        phase_amp.inputs["Scale"].default_value = 3.40
    except Exception:
        phase_amp.inputs[1].default_value = 2.60
    L(phase_c.outputs["Vector"], phase_amp.inputs[0])

    # base coordinate: y across the plank, ~5 rings over the width
    mp_rings = _mapping(nt, (1.0, 1.0, 1.0), name="ring_space")
    L(tc.outputs["Generated"], mp_rings.inputs["Vector"])
    ring_scaled = nt.nodes.new("ShaderNodeVectorMath")
    ring_scaled.label = "ring_y_scaled"; ring_scaled.operation = "MULTIPLY"
    L(mp_rings.outputs["Vector"], ring_scaled.inputs[0])
    ring_k = nt.nodes.new("ShaderNodeCombineXYZ")
    ring_k.inputs["X"].default_value = 0.0
    ring_k.inputs["Y"].default_value = 5.0
    ring_k.inputs["Z"].default_value = 0.0
    L(ring_k.outputs["Vector"], ring_scaled.inputs[1])

    ring_sum = nt.nodes.new("ShaderNodeVectorMath")
    ring_sum.label = "ring_sum"; ring_sum.operation = "ADD"
    L(ring_scaled.outputs["Vector"], ring_sum.inputs[0])
    L(phase_amp.outputs["Vector"], ring_sum.inputs[1])

    # take Y of the sum, add a fine ragged term, wrap to 0..1
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L(ring_sum.outputs["Vector"], sep.inputs[0])
    fine_nz = _noise(nt, 9.0, 3.0, 0.58, name="latewood_ragged")
    L(mp_phys.outputs["Vector"], fine_nz.inputs["Vector"])
    fine_c = nt.nodes.new("ShaderNodeMath")
    fine_c.operation = "SUBTRACT"; fine_c.inputs[1].default_value = 0.5
    L(fine_nz.outputs["Fac"], fine_c.inputs[0])
    fine_a = nt.nodes.new("ShaderNodeMath")
    fine_a.operation = "MULTIPLY"; fine_a.inputs[1].default_value = 0.75
    L(fine_c.outputs["Value"], fine_a.inputs[0])
    coord = nt.nodes.new("ShaderNodeMath")
    coord.operation = "ADD"
    L(sep.outputs["Y"], coord.inputs[0])
    L(fine_a.outputs["Value"], coord.inputs[1])
    wrap = nt.nodes.new("ShaderNodeMath")
    wrap.label = "ring_wrap"; wrap.operation = "FRACT"
    L(coord.outputs["Value"], wrap.inputs[0])

    # 5-stop ramp; the wrap discontinuity is the crisp latewood line
    ramp = _ramp(nt, [
        (0.000, (0.118, 0.074, 0.040)),
        (0.250, (0.112, 0.070, 0.038)),
        (0.600, (0.104, 0.064, 0.035)),
        (0.900, (0.092, 0.056, 0.030)),
        (0.975, (0.074, 0.046, 0.026)),
        (1.000, (0.076, 0.047, 0.027)),
    ], name="ring_ramp", interp="B_SPLINE")
    L(wrap.outputs["Value"], ramp.inputs["Fac"])

    # SECOND broad tone wash: +-12% warm/cool figure zones, MULTIPLIED
    wash_nz = _noise(nt, 2.2, 2.0, 0.50, name="wash")
    L(tc.outputs["Generated"], wash_nz.inputs["Vector"])
    wash = _ramp(nt, [(0.30, (0.82, 0.805, 0.79)),
                      (0.72, (1.12, 1.095, 1.04))],
                 name="wash_ramp", interp="B_SPLINE")
    L(wash_nz.outputs["Fac"], wash.inputs["Fac"])
    # a mid-scale cloud field (3-8 cm) breaks the arcs into patches
    cloud_nz = _noise(nt, 7.0, 3.0, 0.55, name="figure_clouds")
    L(mp_phys.outputs["Vector"], cloud_nz.inputs["Vector"])
    cloud = _ramp(nt, [(0.34, (0.84, 0.83, 0.82)),
                       (0.70, (1.10, 1.09, 1.06))],
                  name="cloud_ramp", interp="B_SPLINE")
    L(cloud_nz.outputs["Fac"], cloud.inputs["Fac"])
    mix_wash = _mix(nt, "MULTIPLY", "wash_x_ring")
    L(ramp.outputs["Color"], mix_wash.inputs["Color1"])
    L(wash.outputs["Color"], mix_wash.inputs["Color2"])
    mix_cloud = _mix(nt, "MULTIPLY", "cloud_x_ring")
    L(mix_wash.outputs["Color"], mix_cloud.inputs["Color1"])
    L(cloud.outputs["Color"], mix_cloud.inputs["Color2"])

    # ---- GRAIN STREAKS (round 24c) ------------------------------
    # The ring figure is a 40 mm signal and the pores are sub-pixel;
    # between them there was nothing, which is why the desk still read
    # flat at review size. Real walnut carries fine dark streaks along
    # the grain at 2-6 mm. phys_space compresses X by 0.088, so a noise
    # sampled there is stretched ~11:1 along the grain -- exactly the
    # shape of a grain streak.
    streak_nz = _noise(nt, 9.0, 4.0, 0.58, name="grain_streaks")
    L(mp_phys.outputs["Vector"], streak_nz.inputs["Vector"])
    streak = _ramp(nt, [(0.38, (0.905, 0.900, 0.895)),
                        (0.66, (1.085, 1.080, 1.070))],
                   name="streak_ramp", interp="B_SPLINE")
    L(streak_nz.outputs["Fac"], streak.inputs["Fac"])

    # ---- pore space: ~5:1 stretched along the grain, warped so the
    # pores flow with the rings
    mp_grain = _mapping(nt, (0.55, 3.2, 1.0), name="pore_space")
    L(tc.outputs["Generated"], mp_grain.inputs["Vector"])
    mp_pw = _mapping(nt, (2.0, 2.0, 1.0), name="pore_warp_src")
    L(tc.outputs["Generated"], mp_pw.inputs["Vector"])
    gvec = _warp(nt, mp_grain.outputs["Vector"], mp_pw.outputs["Vector"],
                 2.4, 2.0, 0.12, name="pore_warp")

    pores = _noise(nt, 620.0, 6.0, 0.62, name="pores")
    L(gvec, pores.inputs["Vector"])
    # vessels are ring-porous: they crowd into the latewood. Build a
    # mask from the ring ramp's own luminance (dark band = dense pores)
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    L(ramp.outputs["Color"], bw.inputs[0])
    late = _maprange(nt, 1.0, 0.0, name="latewood_mask")
    late.inputs["From Min"].default_value = 0.058
    late.inputs["From Max"].default_value = 0.105
    L(bw.outputs["Val"], late.inputs["Value"])

    # deep grain channels: coarser noise in the SAME stretched space
    # (a 0.10 x-mapping stretches it ~10:1 -> 30 cm x 3 mm streaks),
    # thresholded hard so they appear only occasionally
    mp_ch = _mapping(nt, (0.10, 1.0, 1.0), name="channel_stretch")
    L(gvec, mp_ch.inputs["Vector"])
    ch_nz = _noise(nt, 120.0, 2.0, 0.50, name="channels")
    L(mp_ch.outputs["Vector"], ch_nz.inputs["Vector"])
    ch_mask = _ramp(nt, [(0.58, (0.0, 0.0, 0.0)), (0.72, (1.0, 1.0, 1.0))],
                    name="channel_mask")
    L(ch_nz.outputs["Fac"], ch_mask.inputs["Fac"])
    ch_depth = _math(nt, "MULTIPLY", "channel_depth", b=1.8)
    L(ch_mask.outputs["Color"], ch_depth.inputs[0])

    pore_w = _math(nt, "MULTIPLY", "pore_in_latewood")
    L(pores.outputs["Fac"], pore_w.inputs[0])
    pore_w2 = _math(nt, "MULTIPLY", "pore_density", b=0.55)
    L(pore_w.outputs["Value"], pore_w2.inputs[0])
    L(late.outputs["Result"], pore_w2.inputs[1])
    height = _math(nt, "ADD", "pore_height")
    L(pore_w2.outputs["Value"], height.inputs[0])
    L(ch_depth.outputs["Value"], height.inputs[1])

    bump = _bump(nt, 0.58, 0.00034, name="pore_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # roughness rides the pores: oiled grain is glossier where intact,
    # dull inside the pores -- that sheen break-up is what reads as
    # wood rather than printed plastic at closeup scale
    rr = _maprange(nt, 0.44, 0.62, name="rough_riding_pores")
    L(height.outputs["Value"], rr.inputs["Value"])
    # round 24: a broad sheen field — 10-20 cm patches of fresher /
    # duller oil — so a big softbox draws PATCHES, not one even sheet
    sheen_nz = _noise(nt, 4.5, 2.0, 0.52, name="sheen_field")
    L(tc.outputs["Generated"], sheen_nz.inputs["Vector"])
    sheen = _maprange(nt, 0.26, 0.56, name="sheen_range")
    L(sheen_nz.outputs["Fac"], sheen.inputs["Value"])
    mix_rough = _math(nt, "MULTIPLY", "rough_x_sheen", b=0.55)
    L(rr.outputs["Result"], mix_rough.inputs[0])
    add_rough = _math(nt, "ADD", "rough_plus_sheen")
    L(mix_rough.outputs["Value"], add_rough.inputs[0])
    L(sheen.outputs["Result"], add_rough.inputs[1])
    L(add_rough.outputs["Value"], bsdf.inputs["Roughness"])

    # pores also darken the colour (x0.80 at the deepest): a bump-only
    # pore disappears under the oiled coat
    pr = _maprange(nt, 1.06, 0.58, name="pore_darkening")
    L(height.outputs["Value"], pr.inputs["Value"])
    mix_pore = _mix(nt, "MULTIPLY", "pore_x_colour")
    mix_streak = _mix(nt, "MULTIPLY", "streak_x_colour")
    L(mix_cloud.outputs["Color"], mix_streak.inputs["Color1"])
    L(streak.outputs["Color"], mix_streak.inputs["Color2"])
    L(mix_streak.outputs["Color"], mix_pore.inputs["Color1"])
    L(pr.outputs["Result"], mix_pore.inputs["Color2"])
    L(mix_pore.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _set(bsdf, "Coat Weight", 0.14)       # oiled sheen
    _set(bsdf, "Coat Roughness", 0.16)
    _set(bsdf, "Coat Roughness", 0.28)
    # the pore/channel bump above IS this material's height map; the
    # env detail sweep overwrites Normal links on untagged materials,
    # which is why earlier rounds lost the grain and read waxy
    mat["micro_texture"] = True
    return mat


def proc_marble(name):
    """Glossy white marble for the product-shot floor.

    Near-white base (0.78 warm .. 0.84 cool) mottled at ~0.5 m. The
    veins are wave bands pushed through TWO chained warps of different
    scales -- they MEANDER, pinch and swell like real veins instead of
    striping; a second decorrelated wave at 2.3x the frequency and a
    thinner spike lays faint gold-grey hairlines over the mid-grey
    veins. Roughness is 0.115 with the veins rougher (0.18 at the
    core), and a strong low-roughness coat supplies the polished-
    stone reflection."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]

    # base warm/cool mottle at decimetre scale
    blotch = _noise(nt, 1.8, 2.0, 0.50, name="blotch")
    L(gen, blotch.inputs["Vector"])
    base = _ramp(nt, [(0.30, (0.78, 0.762, 0.74)),
                      (0.72, (0.84, 0.84, 0.85))],
                 name="base_ramp", interp="B_SPLINE")
    L(blotch.outputs["Fac"], base.inputs["Fac"])

    # ---- primary veins: warp chain twice so the bands wander over
    # ~40 cm and micro-fishtail over ~4 cm (features must be far above
    # the vein period, or the bands just smear into noise)
    mp_v = _mapping(nt, name="vein_space")
    L(gen, mp_v.inputs["Vector"])
    mp_wb = _mapping(nt, (1.6, 1.6, 1.0), name="vein_warp_broad_src")
    L(gen, mp_wb.inputs["Vector"])
    vvec = _warp(nt, mp_v.outputs["Vector"], mp_wb.outputs["Vector"],
                 1.5, 2.0, 0.15, name="vein_warp_broad")
    mp_wf = _mapping(nt, (5.0, 5.0, 1.0), name="vein_warp_fine_src")
    L(gen, mp_wf.inputs["Vector"])
    vvec = _warp(nt, vvec, mp_wf.outputs["Vector"], 5.0, 3.0, 0.05,
                 name="vein_warp_fine")
    # Distortion 0.5, not 5: the wave's internal distortion noise is
    # sampled on the input vector, so a large amount tears the bands
    # into period-scale static instead of wandering them. Wandering is
    # the warp chain's job; the small residue is in-vein turbulence.
    veins = _wave(nt, 6.0, 0.5, 5.0, 2.0, bands="X", name="veins")
    L(vvec, veins.inputs["Vector"])
    mask = _ramp(nt, [(0.46, (0.0, 0.0, 0.0)), (0.50, (1.0, 1.0, 1.0)),
                      (0.54, (0.0, 0.0, 0.0))], name="vein_mask")
    L(veins.outputs["Fac"], mask.inputs["Fac"])

    grey = _mix(nt, "MIX", "grey_veins")
    grey.inputs["Color2"].default_value = (0.52, 0.51, 0.49, 1.0)
    L(base.outputs["Color"], grey.inputs["Color1"])
    L(mask.outputs["Color"], grey.inputs["Fac"])

    # ---- secondary gold-grey hairlines: same broad warp (both vein
    # systems belong to one slab, so they share the drift), higher
    # frequency, thinner spike, phase-shifted by a large mapping
    # location offset so the two webs never look related
    mp_v2 = _mapping(nt, location=(31.7, -11.3, 0.0), name="vein2_space")
    L(gen, mp_v2.inputs["Vector"])
    vvec2 = _warp(nt, mp_v2.outputs["Vector"], mp_wb.outputs["Vector"],
                  2.3, 2.0, 0.06, name="vein2_warp")
    veins2 = _wave(nt, 14.0, 0.3, 4.0, 2.0, bands="X", name="veins_gold")
    L(vvec2, veins2.inputs["Vector"])
    mask2 = _ramp(nt, [(0.465, (0.0, 0.0, 0.0)), (0.50, (1.0, 1.0, 1.0)),
                       (0.535, (0.0, 0.0, 0.0))], name="vein2_mask")
    L(veins2.outputs["Fac"], mask2.inputs["Fac"])

    gold = _mix(nt, "MIX", "gold_veins")
    gold.inputs["Color2"].default_value = (0.60, 0.51, 0.36, 1.0)
    L(grey.outputs["Color"], gold.inputs["Color1"])
    L(mask2.outputs["Color"], gold.inputs["Fac"])
    L(gold.outputs["Color"], bsdf.inputs["Base Color"])

    # roughness 0.10..0.18: polished stone, veins slightly rougher
    rv = _math(nt, "MULTIPLY", "vein_rough", b=0.05)
    L(mask.outputs["Color"], rv.inputs[0])
    rg = _math(nt, "MULTIPLY", "gold_rough", b=0.015)
    L(mask2.outputs["Color"], rg.inputs[0])
    rsum = _math(nt, "ADD", "vein_rough_sum")
    L(rv.outputs["Value"], rsum.inputs[0])
    L(rg.outputs["Value"], rsum.inputs[1])
    rbase = _math(nt, "ADD", "marble_rough", b=0.115)
    L(rsum.outputs["Value"], rbase.inputs[0])
    L(rbase.outputs["Value"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _set(bsdf, "Coat Weight", 0.62)       # strong polished coat
    _set(bsdf, "Coat Roughness", 0.06)
    return mat


def proc_pcb(name):
    """Dark-green PCB that reads as WIRED at exploded-diagram distance.

    Not accurate -- convincing. Two crossed wave systems at ~60
    periods per board axis (2 mm pitch, +-8 deg rotated so the grid
    feels routed, not graphed), each domain-warped so the runs bend
    like drawn tracks, both ramped to a NARROW gold spike (12% of the
    period = ~0.25 mm traces at the ~120 mm board bbox). A fine noise
    thresholded high scatters sparse via dots into the web's flow, a
    coarse thresholded noise lays pale silkscreen islands over the
    mask, and the trace/via mask drives Metallic so the gold reads as
    metal over matte soldermask. A 35 um-scale bump raises the web."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]

    # soldermask base + sub-millimetre mottle (the glass-fibre weave
    # shimmer real mask shows under raking light)
    mottle = _noise(nt, 240.0, 3.0, 0.55, name="mottle")
    L(gen, mottle.inputs["Vector"])
    mottle_f = _math(nt, "MULTIPLY", "mottle_amt", b=0.35)
    L(mottle.outputs["Fac"], mottle_f.inputs[0])
    mm = _mix(nt, "MIX", "soldermask_mottle")
    mm.inputs["Fac"].default_value = 0.0     # driven by the mottle
    L(mottle_f.outputs["Value"], mm.inputs["Fac"])
    mm.inputs["Color1"].default_value = (0.015, 0.105, 0.050, 1.0)
    mm.inputs["Color2"].default_value = (0.010, 0.082, 0.040, 1.0)

    # ---- trace web: two crossed, warped band systems
    mp_a = _mapping(nt, rotation=(0.0, 0.0, math.radians(8.0)),
                    name="trace_a_space")
    L(gen, mp_a.inputs["Vector"])
    mp_b = _mapping(nt, rotation=(0.0, 0.0, math.radians(-8.0)),
                    location=(13.0, -7.5, 0.0), name="trace_b_space")
    L(gen, mp_b.inputs["Vector"])
    mp_w = _mapping(nt, (5.0, 5.0, 1.0), name="trace_warp_src")
    L(gen, mp_w.inputs["Vector"])
    va = _warp(nt, mp_a.outputs["Vector"], mp_w.outputs["Vector"],
               3.5, 2.5, 0.010, name="trace_a_warp")
    vb = _warp(nt, mp_b.outputs["Vector"], mp_w.outputs["Vector"],
               4.2, 2.5, 0.012, name="trace_b_warp")

    spike = [(0.00, (0.0, 0.0, 0.0)), (0.42, (0.0, 0.0, 0.0)),
             (0.48, (1.0, 1.0, 1.0)), (0.54, (0.0, 0.0, 0.0)),
             (1.00, (0.0, 0.0, 0.0))]     # LINEAR interp + narrow spike:
    wa = _wave(nt, 60.0, 0.2, 3.0, 2.0, bands="X", name="traces_a")
    L(va, wa.inputs["Vector"])           # the trace edge must stay a
    sa = _ramp(nt, spike, name="trace_a_spike")   # hard mask edge, or
    L(wa.outputs["Fac"], sa.inputs["Fac"])        # the web blurs
    wb = _wave(nt, 60.0, 0.2, 3.0, 2.0, bands="Y", name="traces_b")
    L(vb, wb.inputs["Vector"])
    sb = _ramp(nt, spike, name="trace_b_spike")
    L(wb.outputs["Fac"], sb.inputs["Fac"])
    web = _math(nt, "MAXIMUM", "trace_web")
    L(sa.outputs["Color"], web.inputs[0])
    L(sb.outputs["Color"], web.inputs[1])

    # ---- vias: fine noise, high threshold -> sparse bright dots
    # (~0.9 mm on the board bbox), sampled on the warped trace space
    # so they sit in the web's flow
    via_nz = _noise(nt, 140.0, 1.5, 0.45, name="vias")
    L(va, via_nz.inputs["Vector"])
    via_r = _ramp(nt, [(0.60, (0.0, 0.0, 0.0)), (0.68, (1.0, 1.0, 1.0))],
                  name="via_mask")
    L(via_nz.outputs["Fac"], via_r.inputs["Fac"])
    metal = _math(nt, "MAXIMUM", "metal_mask")
    L(web.outputs["Value"], metal.inputs[0])
    L(via_r.outputs["Color"], metal.inputs[1])

    # ---- silkscreen: sparse pale islands from a coarse noise
    silk_nz = _noise(nt, 8.0, 2.0, 0.50, name="silk")
    L(gen, silk_nz.inputs["Vector"])
    silk_r = _ramp(nt, [(0.00, (0.0, 0.0, 0.0)), (0.58, (0.0, 0.0, 0.0)),
                        (0.65, (0.9, 0.9, 0.9)), (0.74, (0.0, 0.0, 0.0)),
                        (1.00, (0.0, 0.0, 0.0))], name="silk_mask")
    L(silk_nz.outputs["Fac"], silk_r.inputs["Fac"])
    silk_f = _math(nt, "MULTIPLY", "silk_amt", b=0.8)
    L(silk_r.outputs["Color"], silk_f.inputs[0])

    sm = _mix(nt, "MIX", "silk_hint")
    sm.inputs["Color2"].default_value = (0.72, 0.72, 0.68, 1.0)
    L(mm.outputs["Color"], sm.inputs["Color1"])
    L(silk_f.outputs["Value"], sm.inputs["Fac"])
    gm = _mix(nt, "MIX", "gold_web")
    gm.inputs["Color2"].default_value = (0.85, 0.66, 0.25, 1.0)
    L(sm.outputs["Color"], gm.inputs["Color1"])
    L(metal.outputs["Value"], gm.inputs["Fac"])
    L(gm.outputs["Color"], bsdf.inputs["Base Color"])
    L(metal.outputs["Value"], bsdf.inputs["Metallic"])   # gold = metal

    # roughness: matte mask 0.38, glossier metal web 0.26, duller silk
    rm = _math(nt, "MULTIPLY", "web_rough", b=0.12)
    L(metal.outputs["Value"], rm.inputs[0])
    rinv = _math(nt, "SUBTRACT", "mask_rough", a=0.38)
    L(rm.outputs["Value"], rinv.inputs[1])
    rs = _math(nt, "MULTIPLY", "silk_rough", b=0.10)
    L(silk_f.outputs["Value"], rs.inputs[0])
    rf = _math(nt, "ADD", "pcb_rough")
    L(rinv.outputs["Value"], rf.inputs[0])
    L(rs.outputs["Value"], rf.inputs[1])
    L(rf.outputs["Value"], bsdf.inputs["Roughness"])

    # bump: the web/vias raised like 35 um copper over a fine tooth
    tooth = _noise(nt, 1200.0, 4.0, 0.55, name="mask_tooth")
    L(gen, tooth.inputs["Vector"])
    tt = _math(nt, "MULTIPLY", "tooth_amt", b=0.18)
    L(tooth.outputs["Fac"], tt.inputs[0])
    h = _math(nt, "ADD", "trace_height")
    L(metal.outputs["Value"], h.inputs[0])
    L(tt.outputs["Value"], h.inputs[1])
    bump = _bump(nt, 0.50, 0.00004, name="trace_bump")
    L(h.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def proc_page_edges(name):
    """The page block of the notebook: all three visible sides, one
    material.

    The sheet lines must keep a TRUE ~0.3 mm pitch on every side, so
    they run along the block's Z (stack) axis in GENERATED space (one
    gen unit == the ~11 mm stack of the env_nb_pages block -> wave
    scale 37 == 0.3 mm sheets; on any proportionally-matched host the
    same 37 periods read at that host's true scale). The lines are
    domain-warped so the sheets waver like a real hand-stack, and a
    stretched noise (tiny Z scale -> constant within a line) varies
    each sheet's brightness individually. Corner darkening is PER
    FACE: generated coords span 0..1 on every box face's in-plane
    axes, and the geometric normal weights the normal's own axis out,
    so each visible side darkens toward its own corners independent
    of absolute size. Roughness ~0.85 with a faint fibre noise."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]

    # ---- sheet lines: bands along Z, warped by a field that is near-
    # constant down the stack (tiny Z scale) and varies along the
    # lines, so sheets drift sideways a few tenths of a period
    mp_s = _mapping(nt, name="sheet_space")
    L(gen, mp_s.inputs["Vector"])
    mp_lo = _mapping(nt, (4.0, 4.0, 0.02), name="lowfreq_src")
    L(gen, mp_lo.inputs["Vector"])
    svec = _warp(nt, mp_s.outputs["Vector"], mp_lo.outputs["Vector"],
                 2.4, 2.0, 0.016, name="sheet_warp")
    sheets = _wave(nt, 37.0, 0.25, 2.0, 2.0, bands="Z", name="sheets")
    L(svec, sheets.inputs["Vector"])
    sheet_r = _ramp(nt, [(0.0, (0.79, 0.762, 0.71)),
                         (1.0, (0.885, 0.862, 0.812))],
                    name="sheet_ramp", interp="B_SPLINE")
    L(sheets.outputs["Fac"], sheet_r.inputs["Fac"])

    # ---- per-sheet brightness: a second noise on the same lowfreq
    # mapping (different scale -> decorrelated) multiplies the sheet
    # colour, constant within one sheet, varying along its length
    jit_nz = _noise(nt, 2.0, 2.0, 0.50, name="line_jitter")
    L(mp_lo.outputs["Vector"], jit_nz.inputs["Vector"])
    jit = _ramp(nt, [(0.28, (0.80, 0.79, 0.775)),
                     (0.75, (1.06, 1.05, 1.02))],
                name="jitter_ramp", interp="B_SPLINE")
    L(jit_nz.outputs["Fac"], jit.inputs["Fac"])
    mix_jit = _mix(nt, "MULTIPLY", "line_jitter_x")
    L(sheet_r.outputs["Color"], mix_jit.inputs["Color1"])
    L(jit.outputs["Color"], mix_jit.inputs["Color2"])

    # ---- per-face corner darkening (see docstring): (1-|n_i|) zeroes
    # the normal's axis; max over the remaining two gen axes is 1 at
    # the corner; ~14% darkening there
    sep_n = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_n.label = "face_normal"
    L(tc.outputs["Normal"], sep_n.inputs["Vector"])
    sep_g = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_g.label = "gen_xyz"
    L(gen, sep_g.inputs["Vector"])
    corner = None
    for ax in ("X", "Y", "Z"):
        na = _math(nt, "ABSOLUTE", f"nabs_{ax}")
        L(sep_n.outputs[ax], na.inputs[0])
        inv = _math(nt, "SUBTRACT", f"ninv_{ax}", a=1.0)
        L(na.outputs["Value"], inv.inputs[1])
        gm = _math(nt, "SUBTRACT", f"gmid_{ax}", a=0.5)
        L(sep_g.outputs[ax], gm.inputs[1])
        ga = _math(nt, "ABSOLUTE", f"gabs_{ax}")
        L(gm.outputs["Value"], ga.inputs[0])
        w = _math(nt, "MULTIPLY", f"corner_w_{ax}")
        L(inv.outputs["Value"], w.inputs[0])
        L(ga.outputs["Value"], w.inputs[1])
        if corner is None:
            corner = w
        else:
            mx = _math(nt, "MAXIMUM", f"corner_max_{ax}")
            L(corner.outputs["Value"], mx.inputs[0])
            L(w.outputs["Value"], mx.inputs[1])
            corner = mx
    dark = _math(nt, "MULTIPLY", "corner_dark", b=0.14)
    L(corner.outputs["Value"], dark.inputs[0])
    vig = _math(nt, "SUBTRACT", "vignette", a=1.0)
    L(dark.outputs["Value"], vig.inputs[1])
    mix_vig = _mix(nt, "MULTIPLY", "corner_vignette")
    L(mix_jit.outputs["Color"], mix_vig.inputs["Color1"])
    L(vig.outputs["Value"], mix_vig.inputs["Color2"])
    L(mix_vig.outputs["Color"], bsdf.inputs["Base Color"])

    # paper tooth on the roughness, ~0.85 mean
    fib = _noise(nt, 1800.0, 4.0, 0.55, name="fibre")
    L(gen, fib.inputs["Vector"])
    fr = _maprange(nt, 0.80, 0.92, name="paper_rough")
    L(fib.outputs["Fac"], fr.inputs["Value"])
    L(fr.outputs["Result"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def proc_cable_braid(name):
    """Braided cable jacket: dark charcoal with a visible twist.

    Two wave systems rotated +-24 deg (pitch ~1.6 mm on a 1 m host)
    multiplied into a diamond lattice -- the braid's crossing strands;
    each system is domain-warped so the weave drifts instead of
    ruler-stripping. A fine noise adds fibre fuzz over the lattice
    for the bump, and the roughness rides that fuzz (0.35..0.55) so
    the jacket keeps a soft sheen with a whisper of coat."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # round 24e: OBJECT space, not Generated. A cable is a CURVE, and
    # Generated is its bounding box -- on a 300 x 5 mm run the braid
    # bands (620/unit) collapsed to a smear across the jacket, which is
    # why the sheath read as a plain grey tube in review. Object
    # coordinates are metres, which is what the scales below were
    # always written for ("pitch ~1.6 mm on a 1 m host").
    gen = tc.outputs["Object"]

    # broad jacket tone wash (worn vs fresh braid zones)
    tone_nz = _noise(nt, 15.0, 2.0, 0.50, name="jacket_tone")
    L(gen, tone_nz.inputs["Vector"])
    tone = _ramp(nt, [(0.30, (0.040, 0.041, 0.045)),
                      (0.72, (0.064, 0.065, 0.071))],
                 name="tone_ramp", interp="B_SPLINE")
    L(tone_nz.outputs["Fac"], tone.inputs["Fac"])

    # ---- the twist: two diagonal band systems, each warped (warp
    # field at ~4 cm, far above the 1.6 mm band pitch, so the strands
    # wander without shredding)
    mp_a = _mapping(nt, rotation=(0.0, 0.0, math.radians(24.0)),
                    name="braid_a_space")
    L(gen, mp_a.inputs["Vector"])
    mp_b = _mapping(nt, rotation=(0.0, 0.0, math.radians(-24.0)),
                    location=(11.3, -7.9, 0.0), name="braid_b_space")
    L(gen, mp_b.inputs["Vector"])
    mp_w = _mapping(nt, (3.0, 3.0, 1.0), name="braid_warp_src")
    L(gen, mp_w.inputs["Vector"])
    va = _warp(nt, mp_a.outputs["Vector"], mp_w.outputs["Vector"],
               8.0, 2.5, 0.0013, name="braid_a_warp")
    vb = _warp(nt, mp_b.outputs["Vector"], mp_w.outputs["Vector"],
               9.5, 2.5, 0.0015, name="braid_b_warp")
    # round 24e: 620/unit = 1.6 mm strands, which at the mat camera
    # (0.9 px/mm) is a one-pixel blur -- the jacket read as a plain
    # tube. 220/unit = 4.5 mm strands, and the bump carries them.
    wa = _wave(nt, 220.0, 0.1, 3.0, 2.0, bands="X", name="braid_a")
    L(va, wa.inputs["Vector"])
    wb = _wave(nt, 220.0, 0.1, 3.0, 2.0, bands="X", name="braid_b")
    L(vb, wb.inputs["Vector"])
    dia = _math(nt, "MULTIPLY", "diamond_braid")
    L(wa.outputs["Fac"], dia.inputs[0])
    L(wb.outputs["Fac"], dia.inputs[1])
    braid = _ramp(nt, [(0.0, (0.62, 0.62, 0.62)),
                       (0.52, (1.02, 1.02, 1.02)),
                       (1.0, (1.22, 1.22, 1.22))],
                  name="braid_shading", interp="B_SPLINE")
    L(dia.outputs["Value"], braid.inputs["Fac"])

    mt = _mix(nt, "MULTIPLY", "braid_x_tone")
    L(tone.outputs["Color"], mt.inputs["Color1"])
    L(braid.outputs["Color"], mt.inputs["Color2"])
    L(mt.outputs["Color"], bsdf.inputs["Base Color"])

    # fibre fuzz over the lattice: bump + sheen
    fuzz = _noise(nt, 2600.0, 5.0, 0.60, name="fuzz")
    L(gen, fuzz.inputs["Vector"])
    fz = _math(nt, "MULTIPLY", "fuzz_amt", b=0.25)
    L(fuzz.outputs["Fac"], fz.inputs[0])
    h = _math(nt, "ADD", "braid_height")
    L(dia.outputs["Value"], h.inputs[0])
    L(fz.outputs["Value"], h.inputs[1])
    bump = _bump(nt, 0.55, 0.00060, name="braid_bump")
    L(h.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    rr = _maprange(nt, 0.26, 0.40, name="fuzz_rough")
    L(fuzz.outputs["Fac"], rr.inputs["Value"])
    L(rr.outputs["Result"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _set(bsdf, "Coat Weight", 0.35)       # satin jacket: the highlight
    _set(bsdf, "Coat Roughness", 0.18)    # is what reads at 3-4 px
    return mat


def proc_glass_smoke(name):
    """Dark smoked glass for the PC side panel: simple but glossy.

    Near-black with a green cast (~0.02), metallic 0, roughness
    modulated 0.05..0.09 by a smudge-scale noise (hand oils and dust
    on a real panel), a high low-roughness coat for the glass
    reflection, and the green pushed into the reflection via Coat
    Tint / Specular Tint when those sockets exist (probed -- skipped
    cleanly on builds without them). No transmission: a smoked panel
    reads near-opaque at product distance and stays a grounded dark
    surface instead of a window into whatever is behind it."""
    mat, nt = _fresh(name)
    if nt is None:
        return mat
    bsdf = _bsdf(nt)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")

    bsdf.inputs["Base Color"].default_value = (0.015, 0.024, 0.019, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0

    # smudge-scale roughness variation, 0.05..0.09
    smudge = _noise(nt, 140.0, 2.0, 0.50, name="smudge")
    L(tc.outputs["Generated"], smudge.inputs["Vector"])
    rr = _maprange(nt, 0.05, 0.09, name="smudge_rough")
    L(smudge.outputs["Fac"], rr.inputs["Value"])
    L(rr.outputs["Result"], bsdf.inputs["Roughness"])

    # high coat, low coat roughness, green pushed into the reflection.
    # NOTE: in 5.2 Specular Tint is a COLOUR socket -- a pale green
    # tints the dielectric highlight, Coat Tint the coat layer; both
    # are probed and skipped if a build lacks them.
    _set(bsdf, "Coat Weight", 0.9)
    _set(bsdf, "Coat Roughness", 0.04)
    _set(bsdf, "Coat Tint", (0.72, 0.93, 0.78, 1.0))
    _set(bsdf, "Specular Tint", (0.78, 0.98, 0.85, 1.0))
    return mat

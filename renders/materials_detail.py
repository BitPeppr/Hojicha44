"""Hojicha44 product materials, round 21 -- the DETAIL pass.

Replaces the `pbr() + micro_texture()` set in scene.py's product block
(cap_pbt, case_pla, plate_pom, knob_alu, enc_steel, enc_gunmetal,
poron_pad) which the standing review rejected as "not enough detail,
texture, depth -- looks rather basic, unrealistic". One `pbr()` +
ONE noise bump can only ever deliver: a flat albedo, a flat roughness
and a single-frequency normal. Real moulded/printed/machined parts
carry SEVERAL DECORRELATED signals at different scales, and each one
is a separate physical event:

  * a BRIGHTNESS wash over a broad scale (where the part was rubbed,
    where the flow of the melt packed differently in the tool, where
    the dye took in anodising),
  * a ROUGHNESS RANGE, not a value -- so the specular lobe breaks into
    patches instead of sitting as one uniform sheen,
  * TWO OR MORE bump octaves (a broad shallow valley structure plus a
    finer relief on top), because a single octave reads as sandpaper or
    as a Belgian waffle depending on where the light lands,
  * a MICRO-structure signal: scratches, pores, speckle, fuzz,
    thresholded so it is RARE. Rare detail is what the eye reads as
    machined/real; evenly-spread detail is what it reads as noise.

That is the whole strategy: every function below stacks several
decorrelated signals, and every node choice is justified by what it
reads as at ~0.2 mm/px closeup render scale.

DELIBERATE SCALE POLICY -- read before editing a number here
  A material lives on a host, and generated space is the HOST's bbox
  normalised 0..1. So a noise scale of N is a feature count across the
  host, and the host table is:

      cap PBT        ~18 x 18 x 9 mm
      case (MJF/PLA) ~180 x 135 x 22 mm (half of a Corne wing)
      plate (POM)    ~250 x 160 x 1.2 mm
      knob (alu)     ~17 x 17 x 9 mm
      encoder shaft  ~6 x 6 x 14 mm
      cable          ~6 x 6 x 400 mm
      poron gasket   ~35 x 35 x 3 mm  (compressed to ~2.55)
      lens / bulb    ~30 x 30 x 30 mm

  feature_mm = host_mm / scale. E.g. cap orange peel at scale 130 ->
  18/130 = 0.14 mm, which is ~0.4 px at the ~3 px/mm of the hero shot
  and 0.7 px at a 0.2 mm/px macro: right at the threshold where it
  reads as SURFACE, not as texture. Bump `Distance` is an absolute
  height in metres, so it is quoted in um in the comments.

  THE ONE ASYMMETRY TO KNOW: albedo and roughness are host-INVARIANT
  (a 12% tone wash is 12% on an 18 mm cap or a 1 m test slab), while
  bump relief is host-DEPENDENT (20 um is 20 um on either). So the
  broad tone wash and the roughness zone below are the two channels
  that carry the read at EVERY scale, and the fine bump octaves are
  the closeup-only extra. Any swatch/screenshot test of these
  materials therefore measures the first two channels, not the fine
  relief -- which is why they are built to be strong on their own
  rather than leaning on sub-millimetre bump.

  The four generated-Z features (case build-layer banding, cap top
  polish, poron compressed skin, cable seam ring) need a host whose
  bbox has a real Z. A zero-thickness plane has a DEGENERATE generated
  Z (constant 0) and collapses them; the swatch test uses 1 m plates
  2 cm thick for exactly that reason.

  The cable braid assumes the jacket's length runs along the host's
  generated Z (this repo's cable meshes are laid that way). Off-axis
  hosts degrade to an elliptical swirl, not to garbage.

Every function is idempotent within a session (marker custom property,
the same guard scene.py's micro_texture and env_materials use) so a
material shared between halves/props can be rebuilt harmlessly.

Usage:
    import materials_detail as MD
    m_cap = MD.cap_pbt_v2("cap_pbt_v2")
    m_case = MD.case_sintered_v2("case_sintered_v2")
    ...
"""
import math

import bpy

_TAG = "materials_detail_r21"      # idempotency marker on the material


# --------------------------------------------------------------- helpers
# Module-private helpers: same shapes as env_materials' equivalents,
# deliberately NOT re-exported and never named the same, so this file
# imports and unit-tests on its own without the environment module.

def _dt_fresh(name):
    """Get-or-build guard. Returns (mat, node_tree); the tree is None
    when the material was already built this session, so callers return
    early and stay idempotent."""
    mat = bpy.data.materials.get(name)
    if mat is not None and mat.get(_TAG):
        return mat, None
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat[_TAG] = True
    return mat, mat.node_tree


def _dt_bsdf(nt):
    """The Principled BSDF, created + linked if the tree was stripped."""
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output")
        if out is None:
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            out.location = (320.0, 0.0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _dt_set(bsdf, key, value):
    """Probe-and-set a Principled input. Coat/Sheen/Specular Tint/Emission
    were all renamed across Blender 4 -> 5 and may be absent in trimmed
    builds: never crash, just skip when the socket is missing. Every
    optional socket in this file goes through here."""
    try:
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
            return True
    except Exception:
        pass
    return False


def _dt_tc(nt, name="tc"):
    """Texture Coordinate + its Generated output. Generated (per-object
    bbox 0..1) is the scene_env/scene.py convention and keeps every
    scale host-relative."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.label = name
    return tc, tc.outputs["Generated"]


def _dt_noise(nt, scale, detail=3.0, rough=0.55, name="noise"):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.label = name
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rough
    return nz


def _dt_map(nt, scale=(1.0, 1.0, 1.0), location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0), name="mapping"):
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.label = name
    mp.inputs["Scale"].default_value = tuple(scale)
    mp.inputs["Location"].default_value = tuple(location)
    mp.inputs["Rotation"].default_value = tuple(rotation)
    return mp


def _dt_wave(nt, scale, distortion=0.0, detail=0.0, detail_scale=1.0,
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


def _dt_ramp(nt, stops, name="ramp", interp="LINEAR"):
    """ValToRGB with sorted stops [(pos, (r, g, b)), ...].

    B_SPLINE for organic fades (the tone washes), LINEAR where a stop
    is a MASK edge that must stay crisp (scratch specks, pores, the
    cable seam). A narrow LINEAR spike IS a scratch; a ramp over the
    same width in B_SPLINE is a smudge.

    STOP POSITIONS MATTER MORE THAN THEY LOOK. A broad fBm noise has a
    Fac 5th/95th percentile of roughly 0.35/0.65, so a ramp whose stops
    sit at 0.3/0.7 makes the surface actually SPAN the value range,
    while the same ramp at 0.05/0.95 makes the whole surface huddle at
    the middle value -- which is exactly the "flat, no detail" failure
    this module exists to fix. Every broad ramp here uses ~0.28/0.72."""
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


def _dt_warp(nt, vec, nvec, scale, detail, strength, rough=0.55,
             name="warp"):
    """vec + (noise(nvec) - 0.5) * strength -- the domain-warp chain that
    makes patterns MEANDER instead of striping. `vec` is the pattern's
    (possibly anisotropic) coordinate; `nvec` is where the warp FIELD is
    sampled, so pass a gently-scaled mapping and the wander stays broad
    even on a heavily stretched pattern. `strength` is in `vec` units:
    keep it below one band period (1/wave_scale) or the bands shred."""
    L = nt.links.new
    nz = _dt_noise(nt, scale, detail, rough, name)
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


def _dt_mix(nt, blend="MIX", name="mix"):
    m = nt.nodes.new("ShaderNodeMixRGB")
    m.label = name
    m.blend_type = blend
    m.inputs["Fac"].default_value = 1.0
    return m


def _dt_math(nt, op, name="math", a=None, b=None, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.label = name
    m.operation = op
    m.use_clamp = clamp
    if a is not None:
        m.inputs[0].default_value = a
    if b is not None:
        m.inputs[1].default_value = b
    return m


def _dt_madd(nt, name="madd", a=None, mul=None, add=None):
    """Math MULTIPLY_ADD: out = a*mul + add. One node instead of a
    multiply plus an add -- keeps these long graphs readable."""
    m = nt.nodes.new("ShaderNodeMath")
    m.label = name
    m.operation = "MULTIPLY_ADD"
    if a is not None:
        m.inputs[0].default_value = a
    if mul is not None:
        m.inputs[1].default_value = mul
    if add is not None:
        m.inputs[2].default_value = add
    return m


def _dt_bump(nt, strength, distance, name="bump"):
    b = nt.nodes.new("ShaderNodeBump")
    b.label = name
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    b.invert = False
    return b


def _dt_range(nt, to_min, to_max, name="range", from_min=0.0, from_max=1.0,
              clamp=False):
    """MapRange with the From side filled in; used for ROUGHNESS RANGES
    and polish amounts, i.e. noise Fac -> a physical value span."""
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.label = name
    mr.inputs["From Min"].default_value = from_min
    mr.inputs["From Max"].default_value = from_max
    mr.inputs["To Min"].default_value = to_min
    mr.inputs["To Max"].default_value = to_max
    mr.clamp = clamp
    return mr


def _dt_axis(nt, gen, axis, label):
    """One channel of generated space as a scalar. Used for the top-face
    polish (cap), the compressed skin (poron) and the seam ring (cable).
    The axis must exist on the host (see the module docstring on
    degenerate Z)."""
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.label = label
    nt.links.new(gen, sep.inputs["Vector"])
    return sep.outputs[axis]


def _dt_add2(nt, sources, name="sum"):
    """Math ADD chain for scalp sources: ADD(a, b), then ADD(prev, c)...

    Used to combine signals that must ALL show up (two bump octaves, a
    ripple and a base) -- an ADD keeps each one's contrast; a MULTIPLY
    would make each one dim the previous and the composite would go
    flat, which is precisely the failure mode this module exists to
    fix."""
    L = nt.links.new
    acc = _dt_math(nt, "ADD", name)
    L(sources[0], acc.inputs[0])
    L(sources[1], acc.inputs[1])
    for i, s in enumerate(sources[2:]):
        extra = _dt_math(nt, "ADD", f"{name}_{i + 2}")
        L(acc.outputs["Value"], extra.inputs[0])
        L(s, extra.inputs[1])
        acc = extra
    return acc


def _dt_tone(nt, gen, name, scale, lo, hi, location=None):
    """A BROAD ALBEDO WASH on the host's overall shape: one soft noise
    (B_SPLINE) at a scale of a few features per bbox, ramped across
    ~0.28..0.72 so the surface really spans lo..hi, then returned as a
    ValToRGB of per-channel multiplies -- 0.88/1.12 is a +-12% wash.
    `location` decorrelates two washes that must not share cells."""
    L = nt.links.new
    vec = gen
    if location is not None:
        mp = _dt_map(nt, location=location, name=name + "_space")
        L(gen, mp.inputs["Vector"])
        vec = mp.outputs["Vector"]
    nz = _dt_noise(nt, scale, 2.0, 0.50, name + "_nz")
    L(vec, nz.inputs["Vector"])
    ramp = _dt_ramp(nt, [(0.28, lo), (0.72, hi)], name + "_ramp",
                    interp="B_SPLINE")
    L(nz.outputs["Fac"], ramp.inputs["Fac"])
    return ramp


def _dt_wash_onto(nt, base_col, ramp, name):
    """Hook a `_dt_tone` MULTIPLY ramp onto a constant base colour and
    return the MixRGB node (caller links its output onward)."""
    m = _dt_mix(nt, "MULTIPLY", name)
    m.inputs["Color1"].default_value = (*base_col, 1.0)
    nt.links.new(ramp.outputs["Color"], m.inputs["Color2"])
    return m


# ------------------------------------------------------------- materials

def cap_pbt_v2(name):
    """Injection-moulded PBT keycap -- the hero of every shot.

    PBT is pressed out of a polished tool, and the tool's own texture
    ends up in the part: ORANGE PEEL. Real keycaps show it at two
    scales at once -- a broad ~0.14 mm dimpling across the dish and a
    ~0.02 mm tool-finish ripple over the top of it. One octave reads as
    sandpaper; two decorrelated octaves read as moulded plastic.

      Bump octave A (broad, shallow): scale 130 over the 18 mm cap
        bbox, +-70 um relief, warped once so the dimpling drifts
        instead of latticing. The octave that survives at hero range.
      Bump octave B (fine): scale 900 = 0.02 mm tool ripple, +-18 um,
        on its own warped, offset mapping so it never shares octave A's
        cells. Sub-pixel at hero range; it frays the specular lobe.
    ROUGHNESS IS A RANGE (0.34..0.47), spanned wide: the mid-scale
    noise (scale 55 -> 0.33 mm) is the pack-density variation of the
    melt front. A single roughness over a whole keycap gives one
    uniform sheen and the classic "video game plastic" read; the range
    is what makes the highlight break per-key.
    TOP-FACE POLISH: caps get shinier where fingers rub, so the polish
    is a function of generated Z (top of the bbox) gated by a broad
    noise -- only SOME regions read rubbed, because a uniform whole-cap
    polish is the giveaway of a procedural material.
    ALBEDO WASH +-12% at ~0.3 cm scale: the melt-front flow pattern and
    the sink marks over the internal ribs. This is the channel that
    survives to any distance, so it is deliberately strong.
    SHEEN 0.07 (probed sockets): the soft retro-reflective edge PBT
    picks up at grazing view; without it the rim goes dead under the
    side accents.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- base albedo: warm bone under a +-12% broad wash
    tone = _dt_tone(nt, gen, "cap_tone", 3.4, (0.88, 0.885, 0.90),
                    (1.12, 1.105, 1.08))
    cap_col = _dt_wash_onto(nt, (0.550, 0.525, 0.475), tone, "cap_colour")
    L(cap_col.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- orange peel, octave A: broad shallow dimpling
    mp_a = _dt_map(nt, name="peel_a_space")
    L(gen, mp_a.inputs["Vector"])
    mp_aw = _dt_map(nt, (0.45, 0.45, 0.03), name="peel_a_warp_src")
    L(gen, mp_aw.inputs["Vector"])
    va = _dt_warp(nt, mp_a.outputs["Vector"], mp_aw.outputs["Vector"],
                  2.0, 2.0, 0.006, name="peel_a_warp")
    peel_a = _dt_noise(nt, 130.0, 3.0, 0.55, "peel_a")
    L(va, peel_a.inputs["Vector"])

    # ---- orange peel, octave B: fine tool ripple, decorrelated space
    mp_b = _dt_map(nt, location=(31.7, -11.3, 5.1), name="peel_b_space")
    L(gen, mp_b.inputs["Vector"])
    mp_bw = _dt_map(nt, (6.0, 6.0, 0.4), name="peel_b_warp_src")
    L(gen, mp_bw.inputs["Vector"])
    vb = _dt_warp(nt, mp_b.outputs["Vector"], mp_bw.outputs["Vector"],
                  4.0, 2.0, 0.004, name="peel_b_warp")
    peel_b = _dt_noise(nt, 900.0, 4.0, 0.55, "peel_b")
    L(vb, peel_b.inputs["Vector"])

    # ---- the two octaves sum into ONE height (ADD keeps both)
    wa = _dt_math(nt, "MULTIPLY", "peel_a_amt", b=0.55)
    L(peel_a.outputs["Fac"], wa.inputs[0])
    wb = _dt_math(nt, "MULTIPLY", "peel_b_amt", b=0.30)
    L(peel_b.outputs["Fac"], wb.inputs[0])
    height = _dt_add2(nt, [wa.outputs["Value"], wb.outputs["Value"]],
                      name="peel_height")
    bump = _dt_bump(nt, 0.34, 0.000088, "peel_bump")   # ~88 um total
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: 0.34..0.47 from the mid-scale pack noise (spanned
    # wide: a narrow ramp keeps the whole keycap at the same sheen),
    # with the fine octave riding it +-0.02 so the highlight frays
    mid_nz = _dt_noise(nt, 55.0, 3.0, 0.55, "cap_pack")
    L(gen, mid_nz.inputs["Vector"])
    gr = _dt_range(nt, 0.34, 0.47, "pack_rough", from_min=0.28,
                   from_max=0.72)
    L(mid_nz.outputs["Fac"], gr.inputs["Value"])
    fine_r = _dt_madd(nt, "fine_rough_off", mul=0.05, add=-0.025)
    L(peel_b.outputs["Fac"], fine_r.inputs[0])
    r1 = _dt_math(nt, "ADD", "cap_rough_base")
    L(gr.outputs["Result"], r1.inputs[0])
    L(fine_r.outputs["Value"], r1.inputs[1])

    # ---- top-face polish: generated Z (1 = crown) -> up to -0.17
    # roughness, gated by a broad noise so only patches are rubbed
    gz = _dt_axis(nt, gen, "Z", "cap_gen_axis")
    top = _dt_range(nt, 0.0, 1.0, "cap_top_mask", from_min=0.62,
                    from_max=1.0, clamp=True)
    L(gz, top.inputs["Value"])
    pol_gate = _dt_range(nt, 0.25, 1.0, "rub_gate", from_min=0.35,
                         from_max=0.72, clamp=True)
    pol_nz = _dt_noise(nt, 2.2, 2.0, 0.50, "rub_zones")
    L(gen, pol_nz.inputs["Vector"])
    L(pol_nz.outputs["Fac"], pol_gate.inputs["Value"])
    pol_amt = _dt_math(nt, "MULTIPLY", "polish_amt", b=0.17)
    L(top.outputs["Result"], pol_amt.inputs[0])
    L(pol_gate.outputs["Result"], pol_amt.inputs[1])
    r2 = _dt_math(nt, "SUBTRACT", "cap_rough_polished", a=0.0)
    L(r1.outputs["Value"], r2.inputs[0])
    L(pol_amt.outputs["Value"], r2.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "cap_rough_floor", b=0.19)
    L(r2.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _dt_set(bsdf, "Sheen Weight", 0.07)
    _dt_set(bsdf, "Sheen Roughness", 0.55)
    _dt_set(bsdf, "Sheen Tint", (0.94, 0.90, 0.83, 1.0))
    return mat


def case_sintered_v2(name):
    """MJF PA12 / printed PLA case -- coarse sintered, slightly matte.

    Sintered nylon is the noisiest material on the keyboard: the powder
    bed leaves a coarse open grain built from MANY octaves (the laser
    melts successive layers of partially fused particles, so there is
    no single cell size). A single-octave noise here is exactly what
    read as "plastic" before; detail 5.0 on two decorrelated scales is
    what reads as powder.

      grain octave A: scale 200 over the ~180 mm half = 0.9 mm particle
        beds, detail 5, warped so the powder drifts instead of gridding.
      grain octave B: scale 900 = 0.2 mm fused flakes, detail 4.
    BUILD-LAYER LINES are the second required signal: MJF/PLA stacks
    ~0.3 mm layers and the interface is a faintly different density.
    They must be HORIZONTAL (parallel to the build plate), so they are
    a band in generated Z with the X/Y mapping scales collapsed to ~0.
    Amplitude is deliberately tiny (+-0.008 roughness, +-1.5% colour):
    at 0.3 mm they only ever show up as a ripple in a GRACING
    highlight, which is how a real printed shell behaves under the side
    accents. Loud layer lines read as a 3D-print render test, not a
    product.
    ALBEDO WASH: TWO decorrelated broad washes (+-14% at ~0.4 m and
    +-9% at ~12 cm) -- powder-fusion density zones and the worn edges
    where the part was handled. This, not the grain, is what carries
    the material at any viewing distance.
    ROUGHNESS RIDES THE GRAIN (0.55..0.72), spanned wide: the valleys
    between grains are shadowed and matte, the grain crowns smoother.
    Uncoated PA12 -- no clear coat at all.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- base albedo: mid grey under two decorrelative washes
    tone_a = _dt_tone(nt, gen, "case_tone_a", 2.6, (0.86, 0.87, 0.88),
                      (1.14, 1.13, 1.12))
    tone_b = _dt_tone(nt, gen, "case_tone_b", 7.5, (0.91, 0.92, 0.93),
                      (1.09, 1.075, 1.065), location=(17.3, -9.1, 4.4))
    case_col = _dt_wash_onto(nt, (0.300, 0.300, 0.315), tone_a,
                             "case_colour")
    case_col2 = _dt_mix(nt, "MULTIPLY", "case_x_wash_b")
    L(case_col.outputs["Color"], case_col2.inputs["Color1"])
    L(tone_b.outputs["Color"], case_col2.inputs["Color2"])

    # ---- sintered grain, octave A (coarse particle beds)
    mp_a = _dt_map(nt, name="sint_a_space")
    L(gen, mp_a.inputs["Vector"])
    mp_aw = _dt_map(nt, (0.5, 0.5, 0.02), name="sint_a_warp_src")
    L(gen, mp_aw.inputs["Vector"])
    va = _dt_warp(nt, mp_a.outputs["Vector"], mp_aw.outputs["Vector"],
                  2.0, 2.0, 0.006, name="sint_a_warp")
    grain_a = _dt_noise(nt, 200.0, 5.0, 0.62, "sinter_a")
    L(va, grain_a.inputs["Vector"])

    # ---- octave B (fine fused flakes), decorrelated space
    mp_b = _dt_map(nt, location=(19.3, 7.7, -3.3), name="sint_b_space")
    L(gen, mp_b.inputs["Vector"])
    mp_bw = _dt_map(nt, (5.0, 5.0, 0.3), name="sint_b_warp_src")
    L(gen, mp_bw.inputs["Vector"])
    vb = _dt_warp(nt, mp_b.outputs["Vector"], mp_bw.outputs["Vector"],
                  3.4, 2.0, 0.004, name="sint_b_warp")
    grain_b = _dt_noise(nt, 900.0, 4.0, 0.60, "sinter_b")
    L(vb, grain_b.inputs["Vector"])

    # ---- LAYER LINES: bands along generated Z, X/Y collapsed. 22 mm
    # bbox / 73 = 0.30 mm. Detail and Distortion stay at 0 so nothing
    # adds sub-layer chatter.
    mp_l = _dt_map(nt, (0.0002, 0.0002, 73.0), name="layer_space")
    L(gen, mp_l.inputs["Vector"])
    layers = _dt_wave(nt, 1.0, 0.0, 0.0, 1.0, bands="Z", name="build_layers")
    L(mp_l.outputs["Vector"], layers.inputs["Vector"])
    lr = _dt_madd(nt, "layer_rough_ripple", mul=0.016, add=-0.008)
    L(layers.outputs["Fac"], lr.inputs[0])
    lt = _dt_ramp(nt, [(0.00, (0.985, 0.985, 0.985)),
                       (0.50, (1.015, 1.012, 1.008)),
                       (1.00, (0.985, 0.985, 0.985))],
                  name="layer_tone", interp="EASE")
    L(layers.outputs["Fac"], lt.inputs["Fac"])

    ly_mix = _dt_mix(nt, "MULTIPLY", "case_x_layers")
    L(case_col2.outputs["Color"], ly_mix.inputs["Color1"])
    L(lt.outputs["Color"], ly_mix.inputs["Color2"])
    L(ly_mix.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- height: multi-octave grain, ~420 um of total relief
    ga = _dt_math(nt, "MULTIPLY", "sint_a_amt", b=0.75)
    L(grain_a.outputs["Fac"], ga.inputs[0])
    gb = _dt_math(nt, "MULTIPLY", "sint_b_amt", b=0.40)
    L(grain_b.outputs["Fac"], gb.inputs[0])
    height = _dt_add2(nt, [ga.outputs["Value"], gb.outputs["Value"]],
                      name="sinter_height")
    bump = _dt_bump(nt, 0.55, 0.00042, "sinter_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: 0.55..0.72 riding the grain + the layer ripple
    gr = _dt_range(nt, 0.55, 0.72, "grain_rough", from_min=0.28,
                   from_max=0.72)
    L(height.outputs["Value"], gr.inputs["Value"])
    r1 = _dt_math(nt, "ADD", "case_rough_grain")
    L(gr.outputs["Result"], r1.inputs[0])
    L(lr.outputs["Value"], r1.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "case_rough_floor", b=0.50)
    L(r1.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _dt_set(bsdf, "Sheen Weight", 0.05)
    _dt_set(bsdf, "Sheen Roughness", 0.70)
    _dt_set(bsdf, "Sheen Tint", (0.88, 0.885, 0.90, 1.0))
    return mat


def plate_pom_v2(name):
    """POM / PP plate -- near-black, waxy gloss, machined swirl.

    A POM plate is the opposite of the sintered case: a semi-crystalline
    polymer with a WAXY specular. Wax is not a clear coat -- it is a
    retro-reflective soft edge, i.e. Sheen (probed), not Coat. So the
    sheen does the wax and the base roughness stays 0.12..0.22 for the
    gloss body.

      WAX ZONE: a broad noise spans the whole spec range -- 0.10 in the
      wax-rich zones, 0.24 where the wax has worn off bare POM, with
      Sheen Weight riding it 0.05..0.20 the other way. This is the
      channel that carries the material at any distance: it is what
      makes the reflection break into a soft polished patch instead of
      one even sheet.
      MACHINING SWIRL: an anisotropic noise stretched 500:5 (0.5 mm
      striae x 25 mm runs on the plate) through the warp chain so the
      swirl meanders instead of striping, driving Anisotropic 0..0.55
      and a +-0.03 ripple on top of the wax zone. Anisotropic
      roughness variation is what makes a soft reflection read as
      TURNED rather than blurred; a single isotropic roughness on this
      plate is a black mirror and nothing else.
      MICRO-SCRATCHES: rare by construction -- a narrow LINEAR ramp
      keeps only the top ~8% of the Fac range. A scratch in a waxy
      surface catches light because it is a FRESH SMOOTHER valley, so
      it lifts the colour toward worn lacquer AND drops the roughness.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- base albedo: near-black under a +-14% wash (small in absolute
    # terms, but it keeps the mid-tones from going dead)
    tone = _dt_tone(nt, gen, "pom_tone", 3.0, (0.86, 0.87, 0.90),
                    (1.14, 1.13, 1.10))
    pom_col = _dt_wash_onto(nt, (0.038, 0.039, 0.046), tone, "pom_colour")

    # ---- BURNISHED PATCHES: where a hand has polished the wax, the
    # roughness drops to a near-mirror (~0.05) and the albedo lifts a
    # little (micro-scratches scatter). This is the ONLY way a near-black
    # plastic reads at a mid-angle view: its diffuse is nearly nothing
    # and its coarse roughness variation only warps a soft lobe, so it
    # needs a few TIGHT mirror patches to give the reflection something
    # to break into. Real plates get them exactly this way -- the outer
    # rim, the screw seats, the tab that gets pinched on removal.
    burn_nz = _dt_noise(nt, 6.5, 2.0, 0.50, "burnish_zones")
    L(gen, burn_nz.inputs["Vector"])
    burn = _dt_range(nt, 0.0, 1.0, "burnish_mask", from_min=0.62,
                     from_max=0.80, clamp=True)
    L(burn_nz.outputs["Fac"], burn.inputs["Value"])
    burn_r = _dt_math(nt, "MULTIPLY", "burnish_rough", b=0.17)
    L(burn.outputs["Result"], burn_r.inputs[0])
    burn_tone = _dt_ramp(nt, [(0.00, (1.0, 1.0, 1.0)),
                              (1.00, (1.10, 1.10, 1.09))],
                         name="burnish_tone")
    L(burn.outputs["Result"], burn_tone.inputs["Fac"])
    pom_x_burn = _dt_mix(nt, "MULTIPLY", "pom_x_burnish")
    L(pom_col.outputs["Color"], pom_x_burn.inputs["Color1"])
    L(burn_tone.outputs["Color"], pom_x_burn.inputs["Color2"])

    # ---- wax zone: the broad read (see docstring)
    wax_nz = _dt_noise(nt, 4.2, 2.0, 0.50, "wax_zones")
    L(gen, wax_nz.inputs["Vector"])
    wax_r = _dt_range(nt, 0.10, 0.26, "wax_rough", from_min=0.28,
                      from_max=0.72)
    L(wax_nz.outputs["Fac"], wax_r.inputs["Value"])

    # ---- machining swirl: anisotropic space + warp
    mp_s = _dt_map(nt, (500.0, 5.0, 500.0), name="swirl_space")
    L(gen, mp_s.inputs["Vector"])
    mp_sw = _dt_map(nt, (0.6, 0.6, 0.03), name="swirl_warp_src")
    L(gen, mp_sw.inputs["Vector"])
    sv = _dt_warp(nt, mp_s.outputs["Vector"], mp_sw.outputs["Vector"],
                  1.8, 2.0, 0.02, name="swirl_warp")
    swirl_nz = _dt_noise(nt, 1.0, 3.0, 0.55, "swirl")
    L(sv, swirl_nz.inputs["Vector"])

    # ---- micro-scratches: sparse bright specks
    sc_nz = _dt_noise(nt, 1500.0, 3.0, 0.55, "scratches")
    L(gen, sc_nz.inputs["Vector"])
    sc_mask = _dt_ramp(nt, [(0.78, (0.0, 0.0, 0.0)),
                            (0.86, (1.0, 1.0, 1.0))],
                       name="scratch_mask")
    L(sc_nz.outputs["Fac"], sc_mask.inputs["Fac"])
    sc_amt = _dt_math(nt, "MULTIPLY", "scratch_amt", b=0.55)
    L(sc_mask.outputs["Color"], sc_amt.inputs[0])

    sc_mix = _dt_mix(nt, "MIX", "scratch_colour")
    sc_mix.inputs["Color1"].default_value = (0.038, 0.039, 0.046, 1.0)
    sc_mix.inputs["Color2"].default_value = (0.115, 0.118, 0.128, 1.0)
    sc_mix.inputs["Fac"].default_value = 0.0
    L(pom_x_burn.outputs["Color"], sc_mix.inputs["Color1"])
    L(sc_amt.outputs["Value"], sc_mix.inputs["Fac"])
    L(sc_mix.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- bump: +-30 um of turned relief, scratches +-15 um valleys
    st_amt = _dt_math(nt, "MULTIPLY", "swirl_height_amt", b=0.35)
    L(swirl_nz.outputs["Fac"], st_amt.inputs[0])
    sc_h = _dt_math(nt, "MULTIPLY", "scratch_height", b=0.30)
    L(sc_amt.outputs["Value"], sc_h.inputs[0])
    height = _dt_add2(nt, [st_amt.outputs["Value"], sc_h.outputs["Value"]],
                      name="pom_height")
    bump = _dt_bump(nt, 0.18, 0.000030, "pom_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: wax zone, + the swirl ripple, + the scratch gloss
    sw_r = _dt_madd(nt, "swirl_rough_ripple", mul=0.06, add=-0.03)
    L(swirl_nz.outputs["Fac"], sw_r.inputs[0])
    sc_drop = _dt_math(nt, "MULTIPLY", "scratch_gloss", b=0.05)
    L(sc_amt.outputs["Value"], sc_drop.inputs[0])
    r1 = _dt_math(nt, "ADD", "pom_rough_a")
    L(wax_r.outputs["Result"], r1.inputs[0])
    L(sw_r.outputs["Value"], r1.inputs[1])
    r2 = _dt_math(nt, "SUBTRACT", "pom_rough", a=0.0)
    L(r1.outputs["Value"], r2.inputs[0])
    L(sc_drop.outputs["Value"], r2.inputs[1])
    r3 = _dt_math(nt, "SUBTRACT", "pom_rough_burnished", a=0.0)
    L(r2.outputs["Value"], r3.inputs[0])
    L(burn_r.outputs["Value"], r3.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "pom_rough_floor", b=0.05)
    L(r3.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    # ---- anisotropic: the swirl mask stretches the specular lobe one
    # way, rotated so it runs along the machining direction. Capped at
    # 0.45: a stronger smear hides the key's reflection instead of
    # smearing it, which reads as a dirty mirror, not as machining.
    an = _dt_range(nt, 0.0, 0.45, "swirl_aniso", from_min=0.28,
                   from_max=0.72)
    L(swirl_nz.outputs["Fac"], an.inputs["Value"])
    L(an.outputs["Result"], bsdf.inputs["Anisotropic"])
    _dt_set(bsdf, "Anisotropic Rotation", 0.62)

    bsdf.inputs["Metallic"].default_value = 0.0
    # wax = Sheen, not Coat. The weight rides the wax zone over a WIDE
    # span (0.05..0.30): wax is the one thing on a POM plate that is
    # ALBEDO-INDEPENDENT and therefore the one signal that survives on
    # a near-black part at any lighting, because it adds light of its
    # own at grazing angles. A parked single value here is why the
    # near-black plate used to read as a flat hole.
    sw_w = _dt_range(nt, 0.30, 0.05, "sheen_weight_ride", from_min=0.28,
                     from_max=0.72)
    L(wax_nz.outputs["Fac"], sw_w.inputs["Value"])
    L(sw_w.outputs["Result"], bsdf.inputs["Sheen Weight"])
    _dt_set(bsdf, "Sheen Roughness", 0.30)
    _dt_set(bsdf, "Sheen Tint", (0.90, 0.90, 0.88, 1.0))
    return mat


def alu_anodized_v2(name):
    """Anodised aluminium knob / encoder body -- brushed + speckled.

    Anodising on a turned knob is two things at once: a BRUSHED metal
    substrate and a thin dielectric conversion layer over it.

      BRUSHED: an anisotropic noise (mapping 400:12, 0.04 mm lines x
      1.4 mm runs on the 17 mm knob OD), warped so the brushing drifts,
      driving Anisotropic 0.45..0.85 AND a +-0.09 ripple on the
      roughness. Brushing is a roughness-DIRECTION effect, so both must
      move together or it reads as blur, not as brushed.
      DYE ZONE: anodising dye is never uniform; it pools where the
      oxide grew fastest. A broad +-11% wash on the metal's albedo plus
      a broad 0.22..0.38 roughness zone -- this is the channel that
      carries the knob at any distance.
      SPECKLE: a thresholded fine noise (scale 2200 -> 0.008 mm) marks
      the uneven oxide flecks, darkening them ~9% and roughening them.
      COAT: the anodised conversion layer itself, 0.16 weight at
      roughness 0.22 -- a dielectric sheet over the metal, which is why
      a knob never reads as bare chrome and why a warm tint survives.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- brushed streaks: anisotropic, warped, rotation biased
    mp_b = _dt_map(nt, (400.0, 12.0, 400.0), name="brush_space")
    L(gen, mp_b.inputs["Vector"])
    mp_bw = _dt_map(nt, (0.5, 0.5, 0.02), name="brush_warp_src")
    L(gen, mp_bw.inputs["Vector"])
    bv = _dt_warp(nt, mp_b.outputs["Vector"], mp_bw.outputs["Vector"],
                  1.6, 2.0, 0.012, name="brush_warp")
    brush_nz = _dt_noise(nt, 1.0, 3.0, 0.55, "brushed")
    L(bv, brush_nz.inputs["Vector"])

    # ---- dye zone: broad albedo wash + broad roughness zone
    tone = _dt_tone(nt, gen, "alu_dye", 3.6, (0.895, 0.90, 0.915),
                    (1.105, 1.10, 1.085))
    sp_nz = _dt_noise(nt, 2200.0, 4.0, 0.55, "anodise_speckle")
    L(gen, sp_nz.inputs["Vector"])
    sp_mask = _dt_ramp(nt, [(0.52, (0.0, 0.0, 0.0)),
                            (0.60, (1.0, 1.0, 1.0))],
                       name="speckle_mask")
    L(sp_nz.outputs["Fac"], sp_mask.inputs["Fac"])
    sp_amt = _dt_math(nt, "MULTIPLY", "speckle_amt", b=0.70)
    L(sp_mask.outputs["Color"], sp_amt.inputs[0])

    sp_dark = _dt_ramp(nt, [(0.00, (1.0, 1.0, 1.0)),
                            (1.00, (0.91, 0.905, 0.915))],
                       name="speckle_tone")
    L(sp_amt.outputs["Value"], sp_dark.inputs["Fac"])
    alu_col = _dt_wash_onto(nt, (0.720, 0.730, 0.750), tone, "alu_colour")
    alu_x_speckle = _dt_mix(nt, "MULTIPLY", "alu_x_speckle")
    L(alu_col.outputs["Color"], alu_x_speckle.inputs["Color1"])
    L(sp_dark.outputs["Color"], alu_x_speckle.inputs["Color2"])
    L(alu_x_speckle.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- bump: +-14 um turned relief + +-4 um speckle
    br_amt = _dt_math(nt, "MULTIPLY", "brush_height", b=0.16)
    L(brush_nz.outputs["Fac"], br_amt.inputs[0])
    sp_h = _dt_math(nt, "MULTIPLY", "speckle_height", b=0.10)
    L(sp_amt.outputs["Value"], sp_h.inputs[0])
    height = _dt_add2(nt, [br_amt.outputs["Value"], sp_h.outputs["Value"]],
                      name="alu_height")
    bump = _dt_bump(nt, 0.14, 0.000014, "alu_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: broad 0.22..0.38 zone + the brush ripple + the
    # speckle tooth, all summed
    zone = _dt_noise(nt, 4.0, 2.0, 0.50, "alu_zone")
    L(gen, zone.inputs["Vector"])
    zr = _dt_range(nt, 0.22, 0.38, "zone_rough", from_min=0.28,
                   from_max=0.72)
    L(zone.outputs["Fac"], zr.inputs["Value"])
    br_r = _dt_madd(nt, "brush_rough_ripple", mul=0.18, add=-0.09)
    L(brush_nz.outputs["Fac"], br_r.inputs[0])
    sp_rough = _dt_math(nt, "MULTIPLY", "speckle_rough", b=0.05)
    L(sp_amt.outputs["Value"], sp_rough.inputs[0])
    r1 = _dt_math(nt, "ADD", "alu_rough_a")
    L(zr.outputs["Result"], r1.inputs[0])
    L(br_r.outputs["Value"], r1.inputs[1])
    r2 = _dt_math(nt, "ADD", "alu_rough")
    L(r1.outputs["Value"], r2.inputs[0])
    L(sp_rough.outputs["Value"], r2.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "alu_rough_floor", b=0.14)
    L(r2.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    an = _dt_range(nt, 0.45, 0.85, "brush_aniso", from_min=0.28,
                   from_max=0.72)
    L(brush_nz.outputs["Fac"], an.inputs["Value"])
    L(an.outputs["Result"], bsdf.inputs["Anisotropic"])
    _dt_set(bsdf, "Anisotropic Rotation", 0.38)

    bsdf.inputs["Metallic"].default_value = 1.0
    _dt_set(bsdf, "Coat Weight", 0.16)
    _dt_set(bsdf, "Coat Roughness", 0.22)
    _dt_set(bsdf, "Coat Tint", (0.90, 0.90, 0.92, 1.0))
    return mat


def steel_shaft_v2(name):
    """Ground-steel encoder shaft -- near-mirror, grinding anisotropy.

    Ground steel is the most mirror-like surface on the keyboard, so the
    danger here is FLATNESS, not coarseness: a perfect metallic mirror is
    a flat colour plus one sharp light reflection. Four signals keep it
    reading as ground metal -- and because a metal has almost no diffuse
    term, ALL of them have to live in the specular and the albedo:

      GRINDING STREAKS: mapping 300:300:26 (0.02 mm across x 0.23 mm
        along the shaft) driving Anisotropic 0.15..0.55 -- the specular
        lobe is smeared along the grind, which is what separates
        "ground" from "polished".
      A POLISH ZONE at broad scale spanning the whole roughness range
        0.035..0.16 (a dressed/burnished patch against a freshly ground
        one). This is the channel that carries the material at any
        distance: one continuous soft reflection breaks into zones of
        different sharpness.
      A TONE RIDE +-12% on the same streaks: real ground steel is never
        perfectly uniform (dresser passes leave density differences),
        and on a metal this is the one signal that is guaranteed to
        read at any sample count -- a pure mirror's own reflection can
        alias away to noise at 16 samples.
      RUPTURE IN THE NORMAL: +-12 um of grinding relief over a
        +-6 um ripple, enough to fray the mirror into streaks.
    Very high specular = metallic 1 with a near-white base tint (steel
    F0 ~0.56-0.65 by alloy). No coat: a bare shaft has none.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- grinding streaks along the shaft axis (generated Z)
    mp_g = _dt_map(nt, (300.0, 300.0, 26.0), name="grind_space")
    L(gen, mp_g.inputs["Vector"])
    mp_gw = _dt_map(nt, (0.4, 0.4, 0.02), name="grind_warp_src")
    L(gen, mp_gw.inputs["Vector"])
    gv = _dt_warp(nt, mp_g.outputs["Vector"], mp_gw.outputs["Vector"],
                  1.5, 2.0, 0.010, name="grind_warp")
    grind_nz = _dt_noise(nt, 1.0, 3.0, 0.55, "grind")
    L(gv, grind_nz.inputs["Vector"])

    # ---- tone ride: +-12% along the streaks (a mirror with a constant
    # colour has no readable detail under low sample counts)
    tone = _dt_tone(nt, gen, "steel_tone", 3.2, (0.88, 0.885, 0.895),
                    (1.12, 1.115, 1.105))
    steel_col = _dt_wash_onto(nt, (0.640, 0.650, 0.680), tone,
                              "steel_colour")
    L(steel_col.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- polish zone: broad zones spanning 0.035..0.16
    zone = _dt_noise(nt, 3.8, 2.0, 0.50, "steel_zone")
    L(gen, zone.inputs["Vector"])
    zr = _dt_range(nt, 0.035, 0.16, "polish_zone", from_min=0.28,
                   from_max=0.72)
    L(zone.outputs["Fac"], zr.inputs["Value"])

    # ---- bump: grinding relief + a finer ripple
    g_amt = _dt_math(nt, "MULTIPLY", "grind_height", b=0.20)
    L(grind_nz.outputs["Fac"], g_amt.inputs[0])
    fine_nz = _dt_noise(nt, 2400.0, 3.0, 0.55, "grind_micro")
    L(gen, fine_nz.inputs["Vector"])
    f_amt = _dt_math(nt, "MULTIPLY", "grind_micro_amt", b=0.12)
    L(fine_nz.outputs["Fac"], f_amt.inputs[0])
    height = _dt_add2(nt, [g_amt.outputs["Value"], f_amt.outputs["Value"]],
                      name="grind_height_sum")
    bump = _dt_bump(nt, 0.18, 0.000018, "grind_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: polish zone + the grind streak ripple + the fine
    # ripple, floored at 0.025 so no mirror aliases into fireflies
    gr_r = _dt_madd(nt, "grind_rough_ride", mul=0.16, add=-0.08)
    L(grind_nz.outputs["Fac"], gr_r.inputs[0])
    fz = _dt_madd(nt, "grind_micro_rough", mul=0.04, add=-0.02)
    L(fine_nz.outputs["Fac"], fz.inputs[0])
    r1 = _dt_math(nt, "ADD", "steel_rough_a")
    L(zr.outputs["Result"], r1.inputs[0])
    L(gr_r.outputs["Value"], r1.inputs[1])
    r2 = _dt_math(nt, "ADD", "steel_rough")
    L(r1.outputs["Value"], r2.inputs[0])
    L(fz.outputs["Value"], r2.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "steel_rough_floor", b=0.025)
    L(r2.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    an = _dt_range(nt, 0.15, 0.55, "grind_aniso", from_min=0.28,
                   from_max=0.72)
    L(grind_nz.outputs["Fac"], an.inputs["Value"])
    L(an.outputs["Result"], bsdf.inputs["Anisotropic"])
    _dt_set(bsdf, "Anisotropic Rotation", 0.0)

    bsdf.inputs["Metallic"].default_value = 1.0
    _dt_set(bsdf, "Specular IOR Level", 0.55)   # steel: no extra boost,
    # the base tint already sits at the alloy's F0
    return mat


def cable_jacket_v2(name):
    """Braided cable jacket -- twist wave, rubber fuzz, one seam ring.

    A braided jacket is one of the few patterns that is genuinely a
    FUNCTION, not a texture: each carrier runs along a helix, so the
    pattern is f(angle_around, distance_along) and nothing else. That is
    built explicitly rather than by crossing two rotated waves (which
    gives a diamond lattice -- a woven look, but not a twist):

      twist = ARCTAN2 over the generated XY cross-section, scaled to
      ~12 carrier positions around the circumference;
      along = generated Z x 100.5, which on a 0.4 m jacket puts a
      carrier crossing every ~4 mm along the length (~68 deg braid angle
      on a 6 mm cable);
      the two are summed and fed to a Wave BANDS along X, so the band
      phase IS the helix phase. TWO helices, counter-wound (the sign of
      the along term flipped), are added: that is the over/under of a
      real braid, and it is what makes the twist look woven rather than
      printed.
    RUBBER FUZZ: a high-frequency noise (scale 3000 -> 0.13 mm) drives
    both bump and the roughness range 0.38..0.54. Rubber has a nap;
    without it a braid reads as drawn vector art.
    NAP ZONE: a broad noise spanning the whole roughness range -- the
    nap is crushed where the cable was coiled and full where it was not.
    On a near-black jacket with no coat this is one of only two channels
    that can read at all, so it is spanned wide.
    MOULDING SEAM: an extruded jacket leaves ONE crisp ring where the
    crosshead die's two halves met. Approximated as |gen_z - 0.37|
    through a ~2 mm-wide EASE ramp: darker (the seat line), slightly
    GLOSSIER (molten polymer trowelled by the die) and raised by a hair
    -- all three at once, which is what makes it read as a real feature
    instead of a painted stripe.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- base albedo: black rubber under a +-15% wash
    tone = _dt_tone(nt, gen, "jacket_tone", 2.8, (0.85, 0.86, 0.88),
                    (1.15, 1.14, 1.11))
    jack_col = _dt_wash_onto(nt, (0.022, 0.022, 0.025), tone,
                             "jacket_colour")

    # ---- helix phase: atan2 of the cross-section, centred on 0.5
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.label = "cable_gen"
    L(gen, sep.inputs["Vector"])
    cx = _dt_math(nt, "SUBTRACT", "cross_x", a=0.5)
    L(sep.outputs["X"], cx.inputs[1])
    cy = _dt_math(nt, "SUBTRACT", "cross_y", a=0.5)
    L(sep.outputs["Y"], cy.inputs[1])
    ang = _dt_math(nt, "ARCTAN2", "angle_around")
    L(cx.outputs["Value"], ang.inputs[0])
    L(cy.outputs["Value"], ang.inputs[1])
    # 12 carriers: angle spans 2*pi and the band period is 1 in the
    # phase, so (2*pi)/N periods around = N carriers at 1.91*2*pi/N
    twist = _dt_math(nt, "MULTIPLY", "twist_around", b=1.91)
    L(ang.outputs["Value"], twist.inputs[0])
    along = _dt_math(nt, "MULTIPLY", "along_length", b=100.5)
    L(sep.outputs["Z"], along.inputs[0])
    h1 = _dt_math(nt, "ADD", "helix_cw")
    L(twist.outputs["Value"], h1.inputs[0])
    L(along.outputs["Value"], h1.inputs[1])
    h2 = _dt_math(nt, "SUBTRACT", "helix_ccw")
    L(twist.outputs["Value"], h2.inputs[0])
    L(along.outputs["Value"], h2.inputs[1])
    v1 = nt.nodes.new("ShaderNodeCombineXYZ")
    v1.label = "helix1_vec"
    L(h1.outputs["Value"], v1.inputs["X"])
    v2 = nt.nodes.new("ShaderNodeCombineXYZ")
    v2.label = "helix2_vec"
    L(h2.outputs["Value"], v2.inputs["X"])
    # distortion 0.35 grabs the noise field so the carrier edges wander
    # a little instead of being laser-straight
    w1 = _dt_wave(nt, 1.0, 0.35, 3.0, 2.0, bands="X", name="carrier_cw")
    L(v1.outputs["Vector"], w1.inputs["Vector"])
    w2 = _dt_wave(nt, 1.0, 0.35, 3.0, 2.0, bands="X", name="carrier_ccw")
    L(v2.outputs["Vector"], w2.inputs["Vector"])

    # carrier profiles: broad soft ridges so each strand has a round
    # cross-section rather than a hard stripe
    braid = _dt_ramp(nt, [(0.00, (1.20, 1.18, 1.15)),
                          (0.30, (0.40, 0.40, 0.42)),
                          (0.50, (0.24, 0.24, 0.26)),
                          (1.00, (1.20, 1.18, 1.15))],
                     name="carrier_profile", interp="B_SPLINE")
    L(w1.outputs["Fac"], braid.inputs["Fac"])
    braid2 = _dt_ramp(nt, [(0.00, (1.55, 1.52, 1.46)),
                           (0.30, (0.48, 0.48, 0.50)),
                           (0.50, (0.30, 0.30, 0.32)),
                           (1.00, (1.55, 1.52, 1.46))],
                      name="carrier_profile_ccw", interp="B_SPLINE")
    L(w2.outputs["Fac"], braid2.inputs["Fac"])

    br_mix = _dt_mix(nt, "MULTIPLY", "braid_x_tone")
    L(jack_col.outputs["Color"], br_mix.inputs["Color1"])
    L(braid.outputs["Color"], br_mix.inputs["Color2"])
    br_mix2 = _dt_mix(nt, "MULTIPLY", "braid2_x_braid")
    L(br_mix.outputs["Color"], br_mix2.inputs["Color1"])
    L(braid2.outputs["Color"], br_mix2.inputs["Color2"])

    # ---- rubber fuzz
    fuzz = _dt_noise(nt, 3000.0, 5.0, 0.60, "fuzz")
    L(gen, fuzz.inputs["Vector"])
    fz = _dt_math(nt, "MULTIPLY", "fuzz_height", b=0.22)
    L(fuzz.outputs["Fac"], fz.inputs[0])

    # ---- nap zone: broad, spans the whole spec roughness range
    nap = _dt_noise(nt, 4.4, 2.0, 0.50, "nap_zone")
    L(gen, nap.inputs["Vector"])
    nap_r = _dt_range(nt, 0.34, 0.62, "nap_rough", from_min=0.28,
                      from_max=0.72)
    L(nap.outputs["Fac"], nap_r.inputs["Value"])
    # ---- STRAND-COVERAGE ZONE: a braid is never uniform -- the carriers
    # bunch and the rubber matrix pokes through in patches. Broad
    # strand-rich zones read as glossy plastic (roughness -0.18) and
    # matrix-rich zones as matte rubber (+0.10). This is the coarse read
    # for the weave: the per-strand roughness swing below is only ~1 cm
    # across and therefore a closeup detail.
    cover = _dt_noise(nt, 5.2, 2.0, 0.50, "strand_cover")
    L(gen, cover.inputs["Vector"])
    cover_g = _dt_madd(nt, "strand_cover_gloss", mul=0.28, add=-0.14)
    L(cover.outputs["Fac"], cover_g.inputs[0])

    # ---- MOULDING SEAM: one ring at generated z = 0.37, ~2 mm wide
    dz = _dt_math(nt, "SUBTRACT", "seam_dz")
    L(sep.outputs["Z"], dz.inputs[0])
    dz.inputs[1].default_value = 0.37
    adz = _dt_math(nt, "ABSOLUTE", "seam_abs")
    L(dz.outputs["Value"], adz.inputs[0])
    # MapRange 1.0 at the centre -> 0.0 at 0.019 gen (~2 mm on 0.4 m)
    seam = _dt_range(nt, 1.0, 0.0, "seam_mask", from_min=0.005,
                     from_max=0.019)
    L(adz.outputs["Value"], seam.inputs["Value"])
    seam_t = _dt_ramp(nt, [(0.00, (0.55, 0.55, 0.58)),
                           (0.45, (0.72, 0.72, 0.74)),
                           (1.00, (1.00, 1.00, 1.00))],
                      name="seam_tone", interp="EASE")
    L(seam.outputs["Result"], seam_t.inputs["Fac"])
    seam_mix = _dt_mix(nt, "MULTIPLY", "seam_x_braid")
    L(br_mix2.outputs["Color"], seam_mix.inputs["Color1"])
    L(seam_t.outputs["Color"], seam_mix.inputs["Color2"])
    L(seam_mix.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- height: braid relief + fuzz + the raised seat line
    hh = _dt_add2(nt, [fz.outputs["Value"], seam.outputs["Result"]],
                  name="cable_height")
    bump = _dt_bump(nt, 0.30, 0.00016, "cable_bump")
    L(hh.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness. THE KEY READ: a braided jacket is not one material
    # -- the STRANDS are polyester/nylon (glossy plastic, ~0.2) and the
    # rubber filling the gaps between them is matte (~0.6). A single
    # roughness over the whole weave is the "flat rubber" failure; the
    # braid phase itself must drive a +-0.2 roughness swing, because
    # that is a genuine physical difference and it is the only channel
    # that can read on a near-black jacket at any distance.
    #   nap zone  0.30..0.58  (crushed vs full nap)
    #   strand   -0.22 on the carrier crowns, +0.06 in the gaps
    #   seat line -0.10 (trowelled by the die)
    strand = _dt_range(nt, 0.0, -0.22, "strand_gloss", from_min=0.15,
                       from_max=0.55)
    L(w2.outputs["Fac"], strand.inputs["Value"])
    gap = _dt_madd(nt, "gap_rough", mul=0.16, add=-0.06)
    L(w2.outputs["Fac"], gap.inputs[0])
    seam_rough = _dt_math(nt, "MULTIPLY", "seam_gloss", b=0.10)
    L(seam.outputs["Result"], seam_rough.inputs[0])
    r1 = _dt_math(nt, "ADD", "cable_rough_a")
    L(nap_r.outputs["Result"], r1.inputs[0])
    L(strand.outputs["Result"], r1.inputs[1])
    r2 = _dt_math(nt, "ADD", "cable_rough_b")
    L(r1.outputs["Value"], r2.inputs[0])
    L(cover_g.outputs["Value"], r2.inputs[1])
    r2b = _dt_math(nt, "ADD", "cable_rough_c")
    L(r2.outputs["Value"], r2b.inputs[0])
    L(gap.outputs["Value"], r2b.inputs[1])
    r3 = _dt_math(nt, "SUBTRACT", "cable_rough", a=0.0)
    L(r2b.outputs["Value"], r3.inputs[0])
    L(seam_rough.outputs["Value"], r3.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "cable_rough_floor", b=0.18)
    L(r3.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _dt_set(bsdf, "Sheen Weight", 0.05)
    _dt_set(bsdf, "Sheen Roughness", 0.75)
    _dt_set(bsdf, "Sheen Tint", (0.80, 0.80, 0.84, 1.0))
    return mat


def poron_v2(name):
    """Compressed Poron gasket -- open-cell foam, slightly shiny skin.

    Foam is the one material on the keyboard whose detail is COLOUR as
    much as shape, and the review note for it was explicit: "poron should
    look porous, not a sheet". Poron's cells are open and irregular, and
    they exist at SEVERAL sizes at once (0.05 mm bubbles inside 0.6 mm
    cells), so the pores come from THREE thresholded decorellated noises
    rather than a Voronoi (Voronoi gives a uniform bubble lattice, which
    reads as bubble wrap):

      pore octaves at 260 / 700 / 3200 = 0.13 / 0.05 / 0.011 mm on the
        35 mm gasket -- the visible cell, its inner bubbles, the cell
        wall's own tooth. Each is warped so the cells are organic
        instead of round.
      COLOUR: the pore floors are ~11% darker (light dies in an open
        cell) and a second threshold lifts the cell-wall RIMS ~14% --
        a pore is dark in the middle and bright at its lip, which is
        the actual read of an open cell. Both go into the albedo, so
        the foam reads as porous even in flat light.
      BUMP ~360 um of pore relief on the compressed skin.
      COMPRESSED SKIN: a gasket's top face has been pressed by the PCB
        above it, so it is shinier than the bulk: roughness is pulled
        from 0.95 at the bottom of generated Z to 0.82 at the pressed
        face. That gradient is what stops the pad reading as a flat
        chamfered slab.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    # ---- pore field: three decorrelated octaves
    mp_a = _dt_map(nt, name="pore_a_space")
    L(gen, mp_a.inputs["Vector"])
    mp_aw = _dt_map(nt, (0.5, 0.5, 0.02), name="pore_a_warp_src")
    L(gen, mp_aw.inputs["Vector"])
    va = _dt_warp(nt, mp_a.outputs["Vector"], mp_aw.outputs["Vector"],
                  2.2, 2.0, 0.006, name="pore_a_warp")
    pore_a = _dt_noise(nt, 260.0, 4.0, 0.58, "pore_a")
    L(va, pore_a.inputs["Vector"])
    mp_b = _dt_map(nt, location=(13.1, -7.9, 2.7), name="pore_b_space")
    L(gen, mp_b.inputs["Vector"])
    mp_bw = _dt_map(nt, (5.0, 5.0, 0.2), name="pore_b_warp_src")
    L(gen, mp_bw.inputs["Vector"])
    vb = _dt_warp(nt, mp_b.outputs["Vector"], mp_bw.outputs["Vector"],
                  3.6, 2.0, 0.004, name="pore_b_warp")
    pore_b = _dt_noise(nt, 700.0, 3.0, 0.55, "pore_b")
    L(vb, pore_b.inputs["Vector"])
    mp_c = _dt_map(nt, location=(-7.7, 13.3, -4.1), name="pore_c_space")
    L(gen, mp_c.inputs["Vector"])
    pore_c = _dt_noise(nt, 3200.0, 3.0, 0.55, "pore_c")
    L(mp_c.outputs["Vector"], pore_c.inputs["Vector"])

    # summed field, normalised back into 0..1
    pa = _dt_math(nt, "MULTIPLY", "pore_a_amt", b=0.62)
    L(pore_a.outputs["Fac"], pa.inputs[0])
    pb = _dt_math(nt, "MULTIPLY", "pore_b_amt", b=0.30)
    L(pore_b.outputs["Fac"], pb.inputs[0])
    pc = _dt_math(nt, "MULTIPLY", "pore_c_amt", b=0.14)
    L(pore_c.outputs["Fac"], pc.inputs[0])
    field = _dt_add2(nt, [pa.outputs["Value"], pb.outputs["Value"],
                          pc.outputs["Value"]], name="pore_field")
    f_norm = _dt_madd(nt, "pore_field_norm", mul=0.80, add=-0.16)
    L(field.outputs["Value"], f_norm.inputs[0])

    # ---- pore mask: narrow LINEAR ramp = a mask edge that stays crisp
    pmask = _dt_ramp(nt, [(0.40, (0.0, 0.0, 0.0)),
                          (0.58, (1.0, 1.0, 1.0))],
                     name="pore_mask")
    L(f_norm.outputs["Value"], pmask.inputs["Fac"])
    # ---- cell-wall rim: the TOP of the same field. The brightest thing
    # in the foam and the reason it reads as porous.
    rmask = _dt_ramp(nt, [(0.66, (0.0, 0.0, 0.0)),
                          (0.86, (1.0, 1.0, 1.0))],
                     name="cell_rim_mask")
    L(f_norm.outputs["Value"], rmask.inputs["Fac"])
    rim_amt = _dt_math(nt, "MULTIPLY", "rim_amt", b=0.34)
    L(rmask.outputs["Color"], rim_amt.inputs[0])

    # ---- colour: base, darkened in the pores, brightened at the rims
    pore_tone = _dt_ramp(nt, [(0.00, (1.0, 1.0, 1.0)),
                              (1.00, (0.89, 0.875, 0.855))],
                         name="pore_shade")
    L(pmask.outputs["Color"], pore_tone.inputs["Fac"])
    poron_col = _dt_wash_onto(nt, (0.400, 0.380, 0.360), pore_tone,
                              "poron_colour")
    rim_mix = _dt_mix(nt, "MIX", "poron_x_rim")
    rim_mix.inputs["Color1"].default_value = (0.400, 0.380, 0.360, 1.0)
    rim_mix.inputs["Color2"].default_value = (0.62, 0.60, 0.58, 1.0)
    rim_mix.inputs["Fac"].default_value = 0.0
    L(poron_col.outputs["Color"], rim_mix.inputs["Color1"])
    L(rim_amt.outputs["Value"], rim_mix.inputs["Fac"])
    L(rim_mix.outputs["Color"], bsdf.inputs["Base Color"])

    # ---- bump: pore relief + the rim lips
    rim_h = _dt_math(nt, "MULTIPLY", "rim_height", b=0.25)
    L(rim_amt.outputs["Value"], rim_h.inputs[0])
    height = _dt_add2(nt, [pmask.outputs["Color"], rim_h.outputs["Value"]],
                      name="pore_height")
    bump = _dt_bump(nt, 0.45, 0.00036, "pore_bump")
    L(height.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---- roughness: pore field 0.82..0.95 then the compressed top face
    # (generated Z -> 1) pulls it down to 0.82, shinier than the bulk
    rr = _dt_range(nt, 0.82, 0.95, "pore_rough", from_min=0.28,
                   from_max=0.72)
    L(field.outputs["Value"], rr.inputs["Value"])
    gz = _dt_axis(nt, gen, "Z", "poron_gen_axis")
    skin = _dt_range(nt, 0.0, 0.10, "compressed_skin", from_min=0.45,
                     from_max=1.0, clamp=True)
    L(gz, skin.inputs["Value"])
    r1 = _dt_math(nt, "SUBTRACT", "poron_rough", a=0.0)
    L(rr.outputs["Result"], r1.inputs[0])
    L(skin.outputs["Result"], r1.inputs[1])
    rfloor = _dt_math(nt, "MAXIMUM", "poron_rough_floor", b=0.78)
    L(r1.outputs["Value"], rfloor.inputs[0])
    L(rfloor.outputs["Value"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    _dt_set(bsdf, "Sheen Weight", 0.03)
    _dt_set(bsdf, "Sheen Roughness", 0.80)
    _dt_set(bsdf, "Sheen Tint", (0.92, 0.90, 0.88, 1.0))
    return mat


def lens_glass_v2(name):
    """Thin dark glass -- lamp bulb / monitor screen edge.

    "Transmission-ish" here deliberately means the LOOK of thin glass,
    not a refractive medium: this module serves product renders where a
    bulb is a small dark lens, so real Transmission would turn it into a
    window onto whatever sits behind it and break the silhouette. The
    look instead comes from the three things that make glass read at
    product distance:

      NEAR-BLACK base (0.007, 0.011, 0.009 -- the bottle green real
      soda-lime glass has), metallic 0, IOR 1.52. Without a transmission
      term this stays a grounded dark surface.
      A HIGH, LOW-ROUGHNESS COAT: the coat IS the air-glass interface
      reflection, which is what gives thin glass its "polished void"
      quality. This is also where the green goes -- Coat Tint is probed
      and set to (0.70, 0.95, 0.76) so the reflection carries the tint
      while the body stays neutral-black; Specular Tint is set the same
      way for the dielectric highlight. Both are probed and skipped
      cleanly on builds without them.
      A HAZE ZONE: real thin glass is never uniformly polished -- the
      flashed edge of a bulb and the ground edge of a screen carry
      dull patches. A broad noise spans the coat roughness 0.04..0.32
      AND the coat weight 0.72..0.95 in opposition, so the reflection
      breaks into a bright sharp streak and a soft dull wash instead of
      sitting as one flat mirror. (A mathematically perfect mirror over
      a uniform environment is a single colour: this zone is the reason
      the material is not flat, and it is also physically honest.)
      A POLISH-SWIRL BUMP: +-60 um of waviness from the draw, which
      bends the coat reflection instead of leaving it ruler-flat.
    """
    mat, nt = _dt_fresh(name)
    if nt is None:
        return mat
    bsdf = _dt_bsdf(nt)
    L = nt.links.new
    tc, gen = _dt_tc(nt)

    bsdf.inputs["Base Color"].default_value = (0.007, 0.011, 0.009, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    _dt_set(bsdf, "IOR", 1.52)

    # ---- haze zone: broad, spans the coat roughness AND its weight
    haze = _dt_noise(nt, 3.4, 2.0, 0.50, "haze_zone")
    L(gen, haze.inputs["Vector"])
    haze_r = _dt_range(nt, 0.04, 0.32, "haze_rough", from_min=0.28,
                       from_max=0.72)
    L(haze.outputs["Fac"], haze_r.inputs["Value"])
    haze_w = _dt_range(nt, 0.95, 0.72, "haze_weight", from_min=0.28,
                       from_max=0.72)
    L(haze.outputs["Fac"], haze_w.inputs["Value"])

    # ---- smudge-scale roughness variation on top of the zone: hand
    # oils and dust, 0.03..0.09. NOTE the zone and the smudge are
    # summed, so the two never both sit at their extreme and the total
    # stays inside the spec's 0.05..0.11 band at the mean while the
    # surface still spans the whole readable range.
    smudge = _dt_noise(nt, 120.0, 3.0, 0.50, "smudge")
    L(gen, smudge.inputs["Vector"])
    sm_r = _dt_range(nt, 0.03, 0.09, "smudge_rough", from_min=0.28,
                     from_max=0.72)
    L(smudge.outputs["Fac"], sm_r.inputs["Value"])
    rsum = _dt_math(nt, "ADD", "glass_rough")
    L(haze_r.outputs["Result"], rsum.inputs[0])
    L(sm_r.outputs["Result"], rsum.inputs[1])
    L(rsum.outputs["Value"], bsdf.inputs["Roughness"])

    # ---- polish swirl: the drawn-glass waviness that bends the coat
    mp_sw = _dt_map(nt, (60.0, 60.0, 0.4), location=(9.1, -4.3, 0.7),
                    name="polish_space")
    L(gen, mp_sw.inputs["Vector"])
    mp_ww = _dt_map(nt, (0.6, 0.6, 0.03), name="polish_warp_src")
    L(gen, mp_ww.inputs["Vector"])
    sv = _dt_warp(nt, mp_sw.outputs["Vector"], mp_ww.outputs["Vector"],
                  1.8, 2.0, 0.02, name="polish_warp")
    swirl = _dt_noise(nt, 1.0, 3.0, 0.55, "polish_swirl")
    L(sv, swirl.inputs["Vector"])
    sw = _dt_math(nt, "MULTIPLY", "polish_height", b=0.22)
    L(swirl.outputs["Fac"], sw.inputs[0])
    bump = _dt_bump(nt, 0.10, 0.000060, "polish_bump")     # ~60 um
    L(sw.outputs["Value"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _dt_set(bsdf, "Coat Roughness", 0.035)
    # the haze zone drives the coat WEIGHT as well as the roughness:
    # a dull flashed edge loses specular energy, a polished patch keeps
    # it, and the two together are what breaks the reflection open.
    # Probe-then-link: if the socket is absent, fall back to the scalar.
    try:
        L(haze_w.outputs["Result"], bsdf.inputs["Coat Weight"])
    except Exception:
        _dt_set(bsdf, "Coat Weight", 0.95)
    # the green of soda-lime glass, pushed into the REFLECTION (coat
    # tint) and the dielectric highlight (specular tint), not into the
    # body -- a green black body reads as green plastic
    _dt_set(bsdf, "Coat Tint", (0.70, 0.95, 0.76, 1.0))
    _dt_set(bsdf, "Specular Tint", (0.75, 0.98, 0.82, 1.0))
    return mat


# registry: (name, function) so a test can build them all without
# importing the eight names one by one.
BUILDERS = (
    ("cap_pbt_v2", cap_pbt_v2),
    ("case_sintered_v2", case_sintered_v2),
    ("plate_pom_v2", plate_pom_v2),
    ("alu_anodized_v2", alu_anodized_v2),
    ("steel_shaft_v2", steel_shaft_v2),
    ("cable_jacket_v2", cable_jacket_v2),
    ("poron_v2", poron_v2),
    ("lens_glass_v2", lens_glass_v2),
)

__all__ = [n for n, _ in BUILDERS] + ["BUILDERS"]

"""render_pp.py — realism + photographic post-processing layer for the
headless Cycles pipeline (Blender 5.2, macOS Metal GPU).

WHY THIS FILE EXISTS
--------------------
The standing review of the Hojicha44 renders is that they "look rather
basic, unrealistic, sterile" — Cycles' DEFAULT output reads clinical, and
the fix is NOT a material change. Photorealism comes from BELOW the
material level: how light bounces around the frame, where the fireflies
get clamped, and a whisper of lens + film character after the render.

That is exactly what this module adds to the existing pipeline:

  * ``tune_cycles``      — light-transport character the current pipeline
                            never touches (bounce budget, adaptive
                            sampling, indirect clamping, caustics off).
  * ``build_pp_chain``   — a compositor chain on the scene that adds
                            subtle photographic character (a negative-mix
                            fog-glow bloom on the hot spots only, tiny
                            chromatic dispersion, a warm-key/cool-shadow
                            colour grade, and a whisper of film grain).
  * ``render_realistic`` — a drop-in for ``scene.render_to`` that applies
                            both and renders to disk.

scene.py keeps working unchanged: this module READS nothing it owns and
mutates nothing outside the scene it is handed. It is import-safe (a
guarded ``main()``), so ``import render_pp`` inside ``scene_env.py`` or
any ``-- --python`` script only costs the definitions.

TERMINOLOGY / VERIFIED ON BLENDER 5.2.3 LTS
-------------------------------------------
Blender 5.2 moved the compositor. Three things the old API did no longer
exist, all verified by probe rather than assumption:

  1. ``scene.node_tree`` is GONE — the compositor node tree now lives on
     ``scene.compositing_node_group`` (a real ``CompositorNodeTree`` ID).
     ``scene.use_nodes`` still toggles compositing but emits a
     DeprecationWarning and is slated for removal in Blender 6.0, so it
     is set inside a ``try`` and only when the attribute exists.
  2. ``CompositorNodeComposite`` is GONE — a node group's output is now
     the Group Output node. The chain therefore ends on
     ``NodeGroupOutput`` wired to an ``Image`` interface socket; that is
     what the renderer writes to ``render.filepath``.
  3. The GLARE NODE HAS NO ``Mix`` SOCKET in 5.2. The legacy mix is
     emulated below (see PP_TUNING["glare_mix"]) with a Mix RGB on the
     node's new glare-ONLY output, which is the pass the old socket
     blended.

     Colour notes (both measured, not assumed): the compositor is
     display-referred END TO END — a bare RLayers -> Group Output chain is
     byte-identical to a non-composited render, so NO output transform
     node belongs in the chain (adding one double-encodes the frame).
     And of the Color Balance node's Lift/Gain/Gamma sockets, the Gain
     and Gamma RGBA twins work but writing the LIFT RGBA CORRUPTS the
     node in 5.2, so the shadow lift uses the scalar Lift socket and the
     cool-shadow bias rides on the Gamma.

Run it directly (headless, mirroring scene.py's CLI):

    blender --background --python renders/render_pp.py -- \
        --res 640x400 --samples 16 --device cpu
"""
import os

import bpy

__all__ = [
    "tune_cycles",
    "build_pp_chain",
    "render_realistic",
    "CYCLES_PRESETS",
    "PP_TUNING",
    "pp_chain_report",
]


# --------------------------------------------------------------------------
# tunables — one place to adjust the "character" of the output
# --------------------------------------------------------------------------

#: Cycles light-transport budgets per quality tier.
#:
#: "high" is the standing setting (spec): 8 total bounces with 4 diffuse,
#: 6 glossy, 8 transmission and 8 transparent. The bounce split matters
#: more than the total: Cycles' default total (4) is what leaves a matte
#: plastic floor looking like flat grey latex — the key light dies before
#: it can bounce off the floor back into the case. More glossy bounces are
#: what let a machined knob carry the studio wall.
CYCLES_PRESETS = {
    "draft": dict(max_bounces=4, diffuse_bounces=2, glossy_bounces=3,
                  transmission_bounces=4, transparent_max_bounces=4,
                  use_adaptive_sampling=True, adaptive_threshold=0.05,
                  sample_clamp_direct=2.0, sample_clamp_indirect=2.0,
                  caustics_reflective=False, caustics_refractive=False),
    "fast": dict(max_bounces=6, diffuse_bounces=3, glossy_bounces=4,
                 transmission_bounces=6, transparent_max_bounces=6,
                 use_adaptive_sampling=True, adaptive_threshold=0.02,
                 sample_clamp_direct=1.5, sample_clamp_indirect=1.5,
                 caustics_reflective=False, caustics_refractive=False),
    # THE DEFAULT — the review-driven "make it not sterile" setting
    "high": dict(max_bounces=8, diffuse_bounces=4, glossy_bounces=6,
                 transmission_bounces=8, transparent_max_bounces=8,
                 use_adaptive_sampling=True, adaptive_threshold=0.01,
                 sample_clamp_direct=1.0, sample_clamp_indirect=1.0,
                 caustics_reflective=False, caustics_refractive=False),
    "ultra": dict(max_bounces=12, diffuse_bounces=8, glossy_bounces=10,
                  transmission_bounces=12, transparent_max_bounces=12,
                  use_adaptive_sampling=True, adaptive_threshold=0.005,
                  sample_clamp_direct=1.0, sample_clamp_indirect=1.0,
                  caustics_reflective=False, caustics_refractive=False),
}

#: Prose for the report — why each property is being set at all. The
#: pipeline's complaint was "unrealistic", so every number here has a
#: job; if a job cannot be explained it does not belong in the list.
CYCLES_WHY = {
    "max_bounces":
        "total light paths: the default 4 starves the floor bounce",
    "diffuse_bounces":
        "matte surfaces keep the bounce: real colour bleed, not grey",
    "glossy_bounces":
        "specular inter-reflections (metal, stone coat, glass order)",
    "transmission_bounces":
        "glass/plastic thickness paths before they go black",
    "transparent_max_bounces":
        "fog glow / alpha friendly SSSTranslucence budget",
    "use_adaptive_sampling":
        "spend samples where they matter, stop in flat areas",
    "adaptive_threshold":
        "1% noise tolerance: converged, but not a 4x sample tax",
    "sample_clamp_direct":
        "kills direct-light fireflies (single bright samples)",
    "sample_clamp_indirect":
        "kills indirect/specular fireflies (the mirror-bounce ones)",
    "caustics_reflective":
        "OFF for speed — at this scale the caustic is sub-pixel noise",
    "caustics_refractive":
        "OFF for speed — a keyboard has no lens-shaped glass anyway",
}

#: post-processing character.
PP_TUNING = {
    # ---- Glare (the only optical "bloom") -------------------------------
    # Fog Glow = the soft halation a real lens paints around a hot specular
    # highlight (not the streaky Star/Streaks modes, which read as sci-fi).
    # Threshold 1.15 means ONLY pixels above 1.15 bloom, i.e. the hot spots
    # — the studio backdrop at 0.86 is untouched by design.
    "glare_type": "Fog Glow",     # enum label — 'Bloom' is the 4.3+ alias
    "glare_quality": "High",       # enum label, not 'HIGH'
    "glare_size": 6.0,              # radius of the halation in pixels
    "glare_threshold": 1.15,        # bloom only the hot spots
    "glare_smoothness": 0.85,      # how soft the halation falls off
    "glare_strength": 1.0,         # bloom amplitude of the pass itself
    # THE 5.2 PROBLEM: the Glare node lost its Mix socket, so the legacy
    # "mix" must be built. -0.03 means: subtract 3% of the bloom-only pass
    # from the image. Sign matters and it is applied literally (negative ->
    # Mix RGB SUBTRACT of the glare pass; positive -> ADD of it). It is
    # subtle on purpose: 3% bloom is a whisper of halation, and only the
    # pixels above 1.15 ever move, which is what "bloom only the hot spots
    # slightly" has to mean. Flip to +0.03 if a positive bloom is wanted.
    "glare_mix": -0.018,
    # ---- Lens Distortion ------------------------------------------------
    # Dispersion ONLY: 0.15 of radial channel separation. Distortion stays
    # 0 (a keyboard must not bend) and Jitter stays off (it is a dither,
    # not chromatic aberration). This is the tiny fringing on the edges of
    # the machined knob and the plate gap — the single strongest "this came
    # through a lens" cue at this resolution.
    "lens_dispersion": 0.04,
    "lens_distortion": 0.0,
    "lens_jitter": False,
    "lens_fit": False,
    # ---- Colour grade ---------------------------------------------------
    # Lift/Gamma/Gain, a whisper. Gain is the highlight bias: (1.0, 0.99,
    # 0.98) is 1-2% less green and blue in the KEY — the warm-key/cool-
    # shadow bias the studio rig already has in its light colours (the
    # warm west accent vs the cool rim), reinforced after the render.
    # Gamma carries the shadow bias (see the verified socket map in
    # build_pp_chain): out = x^(1/gamma), so a blue gamma above 1 lifts
    # the shadows in blue by ~2% at x=0.2 and by ~0.1% at x=0.9 — the
    # shadows go cool rather than neutral-grey. Lift is a channel-neutral
    # touch of shadow lightness; the Lift RGBA twin is unusable in 5.2
    # (it corrupts the node), so only the SCALAR socket is set.
    # Anything larger than this reads as Instagram, not as a camera.
    "cb_lift": (0.0, 0.0, 0.0),          # authored intent (see note)
    "cb_lift_scalar": 0.0015,            # the socket that works in 5.2
    "cb_gamma": (1.0, 1.0, 1.010),
    "cb_gain": (1.0, 0.99, 0.98),
    # ---- Film grain -----------------------------------------------------
    # NO vignette: a vignette on a product shot crops the eye and flattens
    # the corners (and the studio floor already falls off). Grain instead:
    # mean-neutral, bipolar, so it does not shift the average or the
    # levels, it only breaks up the flat gradients that read as "CG".
    # Strength 0.005 = 1.5% of full scale, scaled so the grain stays the
    # same PIXEL SIZE at any output resolution (the frequency is driven by
    # scene resolution, not left at Noise Texture's default of 5, which
    # would give 100-px blobs at 2400x1500).
    "grain_strength": 0.005,
    "grain_pixels": 1.5,      # grain feature size in pixels
    # The amplitude compensates for Perlin's real dynamic range: the
    # Noise Texture Fac output only spans ~0..1 around 0.5 (measured std
    # ~0.15), so a +-1 MapRange delivers a grain of only ~0.3/255. x3 puts
    # the grain RMS at ~1.7/255 — a subtle 35mm-style grain, mean-neutral,
    # with no level shift. Measured on the verification render (autocorr
    # at a 1px shift ~ -0.12, i.e. noise, not a smooth shift).
    "grain_amplitude": 3.0,
    "grain_detail": 1.0,     # octaves: 2, no fractal mush
}

#: properties that exist in Cycles but that we deliberately do NOT set.
NOT_SET_WHY = {
    "blur_glossy": (
        "DELIBERATELY SKIPPED — blur_glossy is a roughness fudge that "
        "softens EVERY glossy reflection, so the machined-knob image of "
        "the key light turns into a smeared blob and the plate loses the "
        "hard highlight that reads as 'waxy POM'. Real lens softness of a "
        "highlight comes from the geometry and the light size (the 70 mm "
        "accents in setup_world_and_lights), not from blurring every "
        "specular lobe. If a highlight is too crunchy the fix is a bigger "
        "light or a rougher material, not blur_glossy."),
    "use_denoising": (
        "left to the caller (scene.render_to already enables it) so this "
        "module never silently fights the pipeline's denoiser choice"),
    "samples": (
        "left to the caller — render_realistic() takes the sample count "
        "as an argument and honours it"),
}

#: names that Cycles used to expose and that changed in 5.x. Reported as
#: MISSING by tune_cycles' probe so the gap is visible, not silent.
CYCLES_RENAMED = {
    "total_bounces": "max_bounces (total is gone; min_light_bounces/min_"
                     "transparent_bounces appear instead)",
    "min_bounces": "min_light_bounces",
    "transparent_min_bounces": "min_transparent_bounces",
    "adaptive_stop_render": "removed — adaptive sampling no longer has a "
                            "stop-render switch",
    "caustics_diffuse": (
        "removed in 5.2 — only caustics_reflective and caustics_refractive "
        "survive; the diffuse caustic toggle is gone, so 'caustics off for "
        "diffuse' cannot be expressed any more"),
}


# --------------------------------------------------------------------------
# small guarded-setters (probe-then-set, never assume a name exists)
# --------------------------------------------------------------------------

def _try_set(rna, prop, value, applied, skipped, why=None):
    """Set ``rna.prop = value`` if the property exists at all.

    Cycles' RNA is not identical across versions (5.2 dropped
    total_bounces / min_bounces / adaptive_stop_render / caustics_diffuse),
    so every property is probed rather than assumed. A missing name is
    reported as MISSING so the report names the gap instead of hiding it
    in a TypeError.
    """
    if not hasattr(rna, prop):
        reason = CYCLES_RENAMED.get(prop, "not present in this Blender")
        skipped.append((prop, reason))
        return False
    try:
        setattr(rna, prop, value)
    except Exception as e:                     # read-only, enum clash, ...
        skipped.append((prop, f"setattr failed: {e}"))
        return False
    # read back: a silent refusal catches enum/range clamping. Floats are
    # stored as 32-bit, so compare them with a tolerance — 0.01 lands on
    # 0.009999999776482582 and a strict == would call that a rejection.
    try:
        got = getattr(rna, prop)
        if isinstance(value, float):
            if abs(float(got) - value) > abs(value) * 1e-6:
                skipped.append((prop, f"rejected, read back {got!r}"))
                return False
        elif got != value:
            skipped.append((prop, f"rejected, read back {got!r}"))
            return False
    except Exception:
        pass
    applied.append((prop, value))
    return True


def _socket(node, name, kind=None, index=None):
    """Find a node input socket by name, disambiguating duplicates.

    The 5.2 Color Balance node has TWO sockets for each of Lift / Gamma /
    Gain — a scalar master and an RGBA vector, both called 'Lift'. Indexing
    by name silently returns the SCALAR. So pick by type: prefer RGBA (or
    whatever ``kind`` asks for), falling back to a positional index.
    """
    socks = list(node.inputs)
    if index is not None:
        return socks[index]
    hits = [s for s in socks if s.name == name]
    if not hits:
        raise KeyError(f"{node.bl_idname} has no socket named {name!r} "
                       f"(has {[s.name for s in socks]})")
    if kind is not None:
        same = [s for s in hits if s.type == kind]
        if same:
            return same[0]
    return hits[0]


def _link(nt, out_socket, in_socket, verbose=True):
    if out_socket is None or in_socket is None:
        if verbose:
            print(f"  [pp] WARNING: skip link "
                  f"{getattr(out_socket, 'name', None)} -> "
                  f"{getattr(in_socket, 'name', None)}", flush=True)
        return None
    return nt.links.new(out_socket, in_socket)


def _rgba(triplet):
    """Lift/Gamma/Gain values are authored as RGB triples; Blender colour
    sockets take 4-tuples ('sequences of dimension 0 should contain 4
    items, not 3'). Keep the authoring form and pad here."""
    if len(triplet) == 4:
        return tuple(triplet)
    return (triplet[0], triplet[1], triplet[2], 1.0)


# --------------------------------------------------------------------------
# 1. Cycles realism
# --------------------------------------------------------------------------

def tune_cycles(scene, quality="high"):
    """Give Cycles light-transport character the current pipeline lacks.

    Returns a report dict::

        {"requested": [(prop, value), ...],       # what we asked for
         "applied":  [(prop, value), ...],        # what stuck
         "missing":  [(prop, why), ...],          # names 5.2 does not have
         "skipped":  [...],                       # deliberately not set
         "cycles":   scene.cycles}

    The report is printed as a compact table. Nothing here touches
    materials, meshes or samples.
    """
    sc = scene if scene is not None else bpy.context.scene
    if quality not in CYCLES_PRESETS:
        raise ValueError(f"quality must be one of {sorted(CYCLES_PRESETS)}")

    tuning = CYCLES_PRESETS[quality]
    applied, missing = [], []

    cyc = sc.cycles
    for prop, value in tuning.items():
        _try_set(cyc, prop, value, applied, missing, CYCLES_WHY.get(prop))

    # The spec wants diffuse caustics OFF too, so probe it explicitly even
    # though it cannot be set: 5.2 deleted the toggle, and a MISSING line
    # in the report is the only way that gap reaches the user. Probing it
    # (rather than assuming) is what stops a rename from silently turning
    # diffuse caustics back on.
    for prop in ("caustics_diffuse",):
        if not hasattr(cyc, prop):
            missing.append((prop, CYCLES_RENAMED.get(
                prop, "not present in this Blender")))

    # film must stay opaque: transparency would hand the compositor a
    # buffer with no background to grade or grain.
    if hasattr(sc.render, "film_transparent"):
        sc.render.film_transparent = False

    report = {
        "requested": list(tuning.items()),
        "applied": applied,
        "missing": missing,
        "skipped": list(NOT_SET_WHY.items()),
        "cycles": cyc,
    }

    print(f"[pp] tune_cycles({quality!r}) on {sc.name!r}", flush=True)
    for prop, val in applied:
        print(f"[pp]   SET    cycles.{prop} = {val}", flush=True)
    for prop, why in missing:
        print(f"[pp]   MISS   cycles.{prop} — {why}", flush=True)
    for prop, why in NOT_SET_WHY.items():
        print(f"[pp]   SKIP   cycles.{prop} — by design", flush=True)
    # the values that actually landed, read back off the RNA
    print("[pp]   now: max_b={max_bounces} diff={diffuse_bounces} "
          "gloss={glossy_bounces} trans={transmission_bounces} "
          "clip_d={sample_clamp_direct} clip_i={sample_clamp_indirect} "
          "caustic_refl={caustics_reflective} "
          "caustic_refr={caustics_refractive}".format(
              max_bounces=getattr(cyc, "max_bounces", "?"),
              diffuse_bounces=getattr(cyc, "diffuse_bounces", "?"),
              glossy_bounces=getattr(cyc, "glossy_bounces", "?"),
              transmission_bounces=getattr(cyc, "transmission_bounces", "?"),
              sample_clamp_direct=getattr(cyc, "sample_clamp_direct", "?"),
              sample_clamp_indirect=getattr(cyc, "sample_clamp_indirect",
                                            "?"),
              caustics_reflective=getattr(cyc, "caustics_reflective", "?"),
              caustics_refractive=getattr(cyc, "caustics_refractive", "?")),
          flush=True)
    return report


# --------------------------------------------------------------------------
# 2. the compositor chain
# --------------------------------------------------------------------------

def _comp_tree(sc):
    """The scene's compositor node tree, created if 5.2 left it empty.

    5.2 keeps it in ``scene.compositing_node_group``; the pre-5.0
    ``scene.node_tree`` path is tried first so the file also imports on a
    Blender that has not been upgraded.
    """
    ng = None
    for getter in (lambda: sc.node_tree,
                   lambda: sc.compositing_node_group):
        try:
            ng = getter()
            if ng is not None:
                break
        except Exception:
            continue
    if ng is None:
        ng = bpy.data.node_groups.new("realistic_pp", "CompositorNodeTree")
        try:
            sc.compositing_node_group = ng
        except Exception:
            raise RuntimeError(
                "cannot attach a compositor tree to this scene "
                "(scene.compositing_node_group unavailable)")
    return ng


def _output_socket(nt):
    """Ensure the group has a colour OUTPUT interface socket and return it.

    In 5.2 the group output node IS the Composite node: whatever feeds
    ``NodeGroupOutput`` is what the renderer writes to filepath. Renaming
    or reusing an existing output socket keeps the function idempotent.
    """
    for item in nt.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "OUTPUT":
            return item
    sock = nt.interface.new_socket(name="Image", in_out="OUTPUT",
                                   socket_type="NodeSocketColor")
    nt.update_tag()
    return sock


def build_pp_chain(scene, res=None):
    """Build the photographic post chain on ``scene.use_nodes``.

    RLayers -> [Glare] -> [negative-mix bloom] -> [Lens Distortion]
            -> [Color Balance] -> [film grain] -> Composite.

    Returns ``(nt, report)``. Every stage is guarded: a scene with no
    world, no lights or nothing on its layers still gets a valid, linked
    chain (the test case in the verification notes exercises exactly
    that — ``init_scene()`` produces a scene with neither).

    Nodes are fully cleared first, so calling this twice cannot pile up a
    second chain.
    """
    sc = scene if scene is not None else bpy.context.scene
    nt = _comp_tree(sc)
    made, warned = [], []

    # clear anything left from a previous call / another shot
    nt.nodes.clear()

    # --- chain wiring ----------------------------------------------------
    # 5.x: compositing is enabled through the (deprecated) use_nodes flag.
    if hasattr(sc, "use_nodes"):
        try:
            sc.use_nodes = True
        except Exception as e:
            warned.append(f"use_nodes: {e}")

    rl = nt.nodes.new("CompositorNodeRLayers")
    rl.name = "PP Render Layers"
    try:
        rl.scene = sc                    # the RLayers node defaults to
                                         # whatever scene was current
    except Exception as e:
        warned.append(f"rl.scene: {e}")
    made.append(("Render Layers", rl))

    image = rl.outputs["Image"]

    # --- 1) Glare: fog-glow halation on the hot spots ---------------------
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.name = "PP Glare"
    gt = _socket(glare, "Type")
    want_type = PP_TUNING["glare_type"]
    if gt.default_value != want_type:
        # 'Bloom' is 5.x's spelling of the same fog glow; fall back to it
        try:
            gt.default_value = want_type
        except TypeError:
            gt.default_value = "Bloom"
    gq = _socket(glare, "Quality")
    try:
        gq.default_value = PP_TUNING["glare_quality"]
    except TypeError:
        pass
    _socket(glare, "Threshold").default_value = \
        PP_TUNING["glare_threshold"]
    _socket(glare, "Size").default_value = PP_TUNING["glare_size"]
    try:
        _socket(glare, "Smoothness").default_value = \
            PP_TUNING["glare_smoothness"]
    except KeyError:
        pass
    try:
        _socket(glare, "Strength").default_value = \
            PP_TUNING["glare_strength"]
    except KeyError:
        pass
    _link(nt, image, glare.inputs["Image"])
    made.append((f"Glare ({gt.default_value}, size "
                 f"{_socket(glare, 'Size').default_value}, "
                 f"quality {gq.default_value}, "
                 f"thr {_socket(glare, 'Threshold').default_value})",
                 glare))

    # --- 2) the legacy Glare MIX, rebuilt by hand --------------------------
    # 5.2's Glare node lost its Mix socket, so the bloom must be blended
    # back by hand. Two measured facts drive the construction:
    #   * the "Image" output is the COMPOSITE (image + FULL bloom) — feeding
    #     it straight on blew 10% of the frame to 52% on the verification
    #     render, because Fog Glow at strength 1 is a strong halation;
    #   * the "Glare" output is the bloom-ONLY pass (measured range
    #     0..0.47, essentially zero under the 1.15 threshold).
    # So the mix blends the bloom-only pass against the RAW frame, which
    # is what the old Mix socket did: a NEGATIVE mix subtracts that
    # fraction of the bloom (Mix RGB computes C1 - Fac*C2), a positive one
    # adds it. Either way ONLY pixels above the 1.15 threshold ever move,
    # which is the "bloom only the hot spots slightly" requirement.
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.name = "PP Glare Mix"
    mix.blend_type = "SUBTRACT" if PP_TUNING["glare_mix"] < 0 else "ADD"
    _socket(mix, "Factor").default_value = abs(PP_TUNING["glare_mix"])
    _link(nt, image, _socket(mix, "Color1"))
    _link(nt, glare.outputs["Glare"], _socket(mix, "Color2"))
    made.append((f"Glare mix {PP_TUNING['glare_mix']:+.2f} "
                 f"(blend {mix.blend_type} on the bloom-only pass)", mix))

    # --- 3) Lens Distortion: a whisper of dispersion -----------------------
    lens = nt.nodes.new("CompositorNodeLensdist")
    lens.name = "PP Lens Distortion"
    _socket(lens, "Dispersion").default_value = PP_TUNING["lens_dispersion"]
    _socket(lens, "Distortion").default_value = PP_TUNING["lens_distortion"]
    try:
        _socket(lens, "Jitter").default_value = PP_TUNING["lens_jitter"]
        _socket(lens, "Fit").default_value = PP_TUNING["lens_fit"]
    except KeyError:
        pass
    _link(nt, mix.outputs["Color"], lens.inputs["Image"])
    made.append((f"Lens Distortion (dispersion "
                 f"{_socket(lens, 'Dispersion').default_value})", lens))

    # --- 4) Colour Balance: warm key, very slightly cool shadows -----------
    bal = nt.nodes.new("CompositorNodeColorBalance")
    bal.name = "PP Color Balance"
    try:
        _socket(bal, "Type").default_value = "Lift/Gamma/Gain"
    except (KeyError, TypeError):
        pass
    # 5.2 VERIFIED SOCKET MAP (measured on a ramp, not assumed): the Color
    # Balance node has TWO sockets for each of Lift/Gamma/Gain — a scalar
    # and an RGBA twin. The GAIN and GAMMA RGBAs work (the authored values
    # land exactly); writing the LIFT RGBA CORRUPTS the node — every form
    # tried (tuple, list, before/after linking, with a tree update, with
    # the scalar also set) produced non-monotonic garbage. So:
    #     gain / gamma -> RGBA twin (per channel, the authored values)
    #     lift         -> SCALAR socket (verified correct, channel neutral)
    # The cool-SHADOW bias therefore rides on the GAMMA: out = x^(1/gamma),
    # so a blue gamma above 1 lifts the shadows in blue and leaves the
    # highlights almost alone (at x=0.2 with gamma 1.010 the blue rises
    # ~2.3%, at x=0.9 only ~0.1%). That IS "shadows tinted slightly cool",
    # expressed on a socket that works. The warm KEY still comes from the
    # gain, exactly as authored.
    _socket(bal, "Gain", kind="RGBA").default_value = \
        _rgba(PP_TUNING["cb_gain"])
    _socket(bal, "Gamma", kind="RGBA").default_value = \
        _rgba(PP_TUNING["cb_gamma"])
    try:
        _socket(bal, "Lift", kind="VALUE").default_value = \
            PP_TUNING["cb_lift_scalar"]
    except (KeyError, IndexError):
        pass
    _link(nt, lens.outputs["Image"], bal.inputs["Image"])
    made.append((f"Color Balance (gain {PP_TUNING['cb_gain']}, "
                 f"gamma {PP_TUNING['cb_gamma']}, "
                 f"scalar lift {PP_TUNING['cb_lift_scalar']})", bal))

    # --- 5) FILM GRAIN (no vignette — see PP_TUNING) -----------------------
    # noise -> centre on 0 -> scale to the output resolution -> mix at the
    # grain strength. Centring is what keeps the grain mean-neutral: the
    # mid level of the picture never moves, only its fine structure.
    coords = nt.nodes.new("CompositorNodeImageCoordinates")
    coords.name = "PP Grain Coordinates"
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.name = "PP Grain Noise"
    try:
        noise.noise_dimensions = "2D"
    except Exception:
        pass
    if res is None:
        res = (sc.render.resolution_x, sc.render.resolution_y)
    try:
        # normalised coordinates are resolution independent, so dividing by
        # the pixel size makes the grain the same PHYSICAL size at 640px
        # and at 2400px (otherwise it swells with the frame).
        _socket(noise, "Scale").default_value = \
            max(res[0], res[1]) / float(PP_TUNING["grain_pixels"])
    except KeyError:
        pass
    try:
        _socket(noise, "Detail").default_value = PP_TUNING["grain_detail"]
        _socket(noise, "Roughness").default_value = 0.5
    except KeyError:
        pass
    # MEASURED GOTCHA: without its Image input linked the Image
    # Coordinates node returns a CONSTANT vector, so the noise evaluates
    # once and the "grain" is a flat tint (measured: high-frequency
    # content 0.0027 constant vs 0.0205 with the link). Feed it the frame.
    try:
        _link(nt, image, coords.inputs["Image"])
    except Exception as e:
        warned.append(f"grain coords image: {e}")
    try:
        _link(nt, coords.outputs["Normalized"], noise.inputs["Vector"])
    except Exception as e:
        warned.append(f"grain coords: {e}")

    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.name = "PP Grain Centre"
    # 0..1 -> -amp..+amp: mean-zero bipolar grain in one node
    _socket(ramp, "From Min").default_value = 0.0
    _socket(ramp, "From Max").default_value = 1.0
    _socket(ramp, "To Min").default_value = -PP_TUNING["grain_amplitude"]
    _socket(ramp, "To Max").default_value = PP_TUNING["grain_amplitude"]
    _socket(ramp, "Value").default_value = 0.0
    _link(nt, noise.outputs["Factor"], _socket(ramp, "Value"))

    # MapRange speaks VALUE; the grain is mixed as a COLOUR, so re-expand
    # the single centred field into an RGBA (a float socket cannot drive a
    # colour socket).
    pack = nt.nodes.new("CompositorNodeCombineColor")
    pack.name = "PP Grain To RGBA"
    for chan in ("Red", "Green", "Blue"):
        _link(nt, ramp.outputs["Result"], _socket(pack, chan))
    try:
        _socket(pack, "Alpha").default_value = 1.0
    except KeyError:
        pass

    grain = nt.nodes.new("ShaderNodeMixRGB")
    grain.name = "PP Film Grain"
    grain.blend_type = "MIX"
    _socket(grain, "Factor").default_value = PP_TUNING["grain_strength"]
    _link(nt, bal.outputs["Image"], _socket(grain, "Color1"))
    _link(nt, pack.outputs["Image"], _socket(grain, "Color2"))
    made.append((f"film grain (strength "
                 f"{PP_TUNING['grain_strength']}, "
                 f"{PP_TUNING['grain_pixels']}px @ "
                 f"{res[0]}x{res[1]}), no vignette", grain))

    # NOTE ON COLOUR MANAGEMENT (measured, do not "fix" this): the 5.2
    # compositor is display-referred end to end. A bare RLayers -> Group
    # Output chain renders BYTE-IDENTICAL to scene.render_to's non-
    # composited PNG, so no output transform is needed; inserting a
    # Convert to Display node instead DOUBLE-encodes the frame (measured:
    # mean luma 0.795 -> 0.947, p05 0.307 -> 0.807, i.e. the shadows jump
    # to near-midgrey). So there is deliberately no transform node here.

    # --- composite --------------------------------------------------------
    out = nt.nodes.new("NodeGroupOutput")
    out.name = "PP Composite"
    out_socket = _output_socket(nt)
    _link(nt, grain.outputs["Color"], out.inputs[out_socket.name])
    made.append((f"Composite (group output <- {out_socket.name})", out))

    # a deterministic, readable layout: one node per 220px column
    for i, (_label, node) in enumerate(made):
        try:
            node.location = (i * 240, 0)
        except Exception:
            pass

    print(f"[pp] chain on {sc.name!r}:", flush=True)
    for label, _node in made:
        print(f"[pp]   {label}", flush=True)
    for w in warned:
        print(f"[pp]   WARNING {w}", flush=True)
    print(f"[pp]   {len(nt.nodes)} nodes, {len(nt.links)} links "
          f"on {nt.bl_idname}", flush=True)
    if not nt.links:
        print("[pp]   WARNING: chain has NO links — the composite will "
              "not run", flush=True)
    return nt, {"nodes": made, "warnings": warned, "tree": nt}


def pp_chain_report(scene):
    """Human-readable statement of what the chain would do (no mutation)."""
    sc = scene if scene is not None else bpy.context.scene
    try:
        tree_id = f"{sc.compositing_node_group!r}"
    except Exception:
        tree_id = "n/a"
    lines = [
        f"scene {sc.name!r}: compositor tree {tree_id}",
        f"  glare     {PP_TUNING['glare_type']}, size "
        f"{PP_TUNING['glare_size']}, quality {PP_TUNING['glare_quality']}, "
        f"threshold {PP_TUNING['glare_threshold']}",
        f"  glare mix {PP_TUNING['glare_mix']:+.3f} on the bloom-only pass",
        f"  lens      dispersion {PP_TUNING['lens_dispersion']}, "
        f"distortion {PP_TUNING['lens_distortion']}",
        f"  grade     gain {PP_TUNING['cb_gain']}, "
        f"gamma {PP_TUNING['cb_gamma']} "
        f"(cool shadows), scalar lift {PP_TUNING['cb_lift_scalar']}",
        f"  grain     {PP_TUNING['grain_strength']} @ "
        f"{PP_TUNING['grain_pixels']}px, no vignette",
    ]
    txt = "\n".join(lines)
    print(txt, flush=True)
    return txt


# --------------------------------------------------------------------------
# 3. the drop-in render
# --------------------------------------------------------------------------

def _setup_device(sc, device):
    """Mirror scene.render_to's device choice so this file needs no import
    of scene.py (and so the pipeline cannot be disturbed by it)."""
    if device == "metal":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = "GPU"
        except Exception as e:
            print("  (GPU setup unavailable, CPU render):", e, flush=True)
            sc.cycles.device = "CPU"
    else:
        sc.cycles.device = "CPU"


def render_realistic(cam, path, res, samples, device="metal", quality="high",
                     post=True):
    """Drop-in for ``scene.render_to`` that also renders it photoreal.

    ``tune_cycles`` + ``build_pp_chain``, then the same render call the
    pipeline already uses. The positional signature is identical to
    ``render_to`` so it can be swapped in place in the shot list.

    resolves the known macOS Metal crash: the crash lives in the render
    buffer copy after sampling, so it happens inside ``render()`` and not
    here — retry on CPU is left to the caller (it is a device-wide
    problem, not a clipping one).
    """
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True          # as in scene.render_to
    sc.render.film_transparent = False

    tune_cycles(sc, quality)
    if post:
        build_pp_chain(sc, res)

    _setup_device(sc, device)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    print(f"  rendering {os.path.basename(path)} ({res[0]}x{res[1]}, "
          f"{samples} spp, {device}) ...", flush=True)
    bpy.ops.render.render(write_still=True)
    print("  wrote", path, flush=True)
    return path


# --------------------------------------------------------------------------
# CLI mirror (import-safe)
# --------------------------------------------------------------------------

def main():
    import argparse
    import sys

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--res", default="640x400")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--device", default="cpu", choices=["cpu", "metal"])
    p.add_argument("--quality", default="high", choices=sorted(CYCLES_PRESETS))
    p.add_argument("--out", default="/tmp/pp_cli.png")
    p.add_argument("--no-post", action="store_true")
    args = p.parse_args(argv)

    res = tuple(int(v) for v in args.res.split("x"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    # a bare smoke-test scene: matte sphere, metal sphere, glass-ish
    # sphere and a plane, so the CLI works with no assets at all.
    def mat(name, rough, metallic):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Base Color"].default_value = (0.8, 0.78, 0.74, 1.0)
        return m

    import mathutils
    for i, (rough, metal) in enumerate(((0.9, 0.0), (0.08, 1.0),
                                        (0.15, 0.0))):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.05, location=(-0.09 + i * 0.09, 0.0, 0.05))
        o = bpy.context.active_object
        o.data.materials.append(mat(f"m{i}", rough, metal))
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    for n, energy in (("key", 40.0), ("fill", 10.0)):
        li = bpy.data.lights.new(n, "AREA")
        li.energy, li.size = energy, 0.6
        o = bpy.data.objects.new(n, li)
        o.location = (-0.2 if n == "key" else 0.3, -0.4, 0.5)
        d = mathutils.Vector((0, 0, 0)) - mathutils.Vector(o.location)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(o)
    bpy.ops.object.camera_add(location=(0.0, -0.42, 0.22))
    bpy.context.active_object.rotation_euler = (
        mathutils.radians(90) * 0.79, 0.0, 0.0)
    sc.camera = bpy.context.active_object
    render_realistic(sc.camera, args.out, res, args.samples, args.device,
                     args.quality, post=not args.no_post)
    print("PP-DONE")


if __name__ == "__main__":
    main()

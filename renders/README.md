# Hojicha44 renders (Phase 10)

Product renders built from the **committed engineering artifacts only** —
no hand-modeled stand-ins for anything that exists in the repo. What you
see is what the release contains.

## Pipeline

```
renders/fetch_keycaps.sh        # download the pinned keycap sources (network)
renders/build_assets.py         # case/.venv — kicad-cli STEP export, plate
                                # extrusion from the tracked DXF, knob/screw
                                # procedural solids, named glTF conversion,
                                # placements.json from the committed boards
renders/scene.py                # Blender 5.2 headless — design-frame assembly,
                                # plate-hole registration gate, PBR materials,
                                # procedural textures, studio floor, render queue
```

Reproduce the deliverable (bright hero + exploded):

```
brew install --cask blender                 # once
./case/.venv/bin/pip install trimesh        # once
bash renders/fetch_keycaps.sh               # once (network)
# thin-top revision: build the case into a dev dir so the placed
# v0.5.0 order record in case/out stays hash-valid
CASE_OUT="$PWD/case/out-dev" ./case/.venv/bin/python case/gen_case.py
CASE_OUT="$PWD/case/out-dev" ./case/.venv/bin/python case/gen_cover.py
CASE_OUT="$PWD/case/out-dev" ./case/.venv/bin/python renders/build_assets.py
blender --background --python renders/scene.py -- \
    --samples 96 --res 1600x1000 --setups bright --shots hero,exploded
```

The same script accepts `--setups dark,bright` and the full shot set
`--shots hero,exploded,top,macro,orbit` (plus `macro_encoder` /
`macro_keys` under `macro`): hero + exploded are the product views, top
is the orthographic layout proof, the macros frame the posed knob and
the cap cluster beside the seam, and orbit is a 12-frame turntable at
0.55 m (the single-half 0.20 m radius was a pre-pose holdover — the
split assembly needs the distance).

**Pre-flight framing check** (`--framecheck`, round-5): before any long
render run, project every object's world bbox through each camera into
NDC and report the covered extent — a board that would run out of
frame fails as a NUMBER before hours of sampling:

    blender --background --python renders/scene.py -- \
        --framecheck --res 2400x1500 --setups bright \
        --shots hero,exploded,macro,orbit,top

Blender 5.x dropped `scene.world_to_camera_info`, so the check does the
lens/sensor maths by hand (`frame_report` in scene.py). Two catches it
already made: the encoder macro targeted the PRE-pose placements.json
coordinate (the tented halves moved it — the camera stared at an empty
spot), and the 0.10 m macro distance clipped the knob's far corner in
the 27×40 mm frame.

**Exploded diagram palette** (`--stack-colors`, round-6): the exploded
shot is rendered as its OWN invocation with one matte colour per layer
(slate tub / emerald board / amber gaskets / teal plate / graphite
switches / violet cover / cream caps / charcoal nano / brass knob) so
the stack reads like a technical diagram — and because it is a separate
process the product shots keep their real materials:

    blender --background --python renders/scene.py -- \
        --samples 96 --res 2400x1500 --setups bright \
        --shots exploded --stack-colors

Outputs land in `generated/renders/v0.5.0/<setup>/<shot>.png`, with
`MANIFEST.json` hashing each final PNG plus the tool versions. The
intermediate mesh tree (`generated/renders/assets/`) is regenerable and
gitignored; the scripts, this README, and the final PNGs are committed.
The delivery set is 2400×1500 ("1.5k").

## Keycaps

[KLP Lamé](https://github.com/braindefender/KLP-Lame-Keycaps) by
braindefender (Nikita Shirokov) — **CC-BY-SA 4.0**, Choc stem + Choc size,
pinned to commit `8e4b89b484cafe3bcaced6b459a4e29660991a40` (see
`generated/renders/assets/PROVENANCE.json`). Variants used: flat Saddle on
all finger rows, Saddle Homing on the inner index home keys (G/H), Thumb
on the four thumb keys. Per the license, attribution to the author is
required alongside any use of these shapes.

## Frame and registration (the fiddly part, measured)

- KiCad stores the board y-down; kicad-cli's STEP export negates y. The
  committed plate DXF and case STLs are y-up. Measured on the release
  board: Edge.Cuts y −60.00..54.63 → glb y −54.63..60.00. Everything is
  assembled in this ONE design frame: `placements.json` converts the
  board (x, −y); `cutouts.json` transcribes the plate DXF as-is.
- The plate CUTOUT holes are the registration master. The scene matches
  every switch footprint to a hole and aborts if any is more than
  0.05 mm away. Measured at v0.5.0: 22/22 switches per half, worst
  0.0000 mm. Cap centres, switch bodies and thumb rotations use the
  matched hole centre and polygon angle.
- There is no 1.4 mm "socket offset". The plate POLYLINEs are closed with
  a duplicated first vertex, so a vertex mean is biased by (w/10, h/10);
  bbox centres are exact. The cutout JSON uses bbox centres.
- The halves keep their committed positions (no synthetic split gap).
  The tub seam measures 2.11 mm; the plate and cover stop at the case
  spine, which is why the visible inner recess is wider than the seam.
- Stack (z = 0 at the PCB top, thin-top revision): substrate −1.60..0;
  bottom gaskets −1.55..1.00 (3.0 poron → 2.55); plate 1.00..2.20;
  switch body 0.30..3.30; cap stem tip 1.50; top gaskets 2.20..3.20
  (1.5 poron → 1.00, 33%); KLP Normal_Tilted cap top ~11.14, i.e. ~5.9 mm
  proud of the flat 5.20 cover (no-indent design: a 0.4 mm chamfer on
  the outer rim is the only embellishment). Openings CAP_CLEAR
  1.5/side: rows and columns both merge, no row-webs. **Thumbs wear
  the same tall Normal_Tilted family** (review round 4: the low KLP
  Thumb profile read as sunken below the rim; the families share the
  foot, so the plan allows either — the build buys tall).
  The plate stays at the Choc v1 clip band
  (1.00..2.20) — moving it up would lose the clip engagement — so the
  thin top comes from the lip/plate above it. The top plate carries the
  key-field opening and the MCU/encoder/pwrsw windows, so the wiring
  strip is covered. **Encoder = the short-shaft EC11-class BOM
  variant** (vendored 20mm STEP truncated at 13.5 mm, two-tone
  gunmetal/steel split — note the truncation selects by world-frame
  z, the board glb keeps its rotation on the root) under the **low
  fluted knob**: procedural `assets/parts/knob.glb`, Ø16.8 × 9.2,
  18 ridges, machined-aluminium finish; skirt bottom 6.1 abs (cover
  5.2 + 0.9 push-travel clearance), crown 15.3 — just above the caps.
  The knob covers the 12.0×11.7 cover window entirely and clears the
  nearest cap (SW_L17) by 3.6 mm at every angle.
- **Colourway hierarchy** (round 4): warm-bone satin PBT caps >
  mid-grey matte PLA case > near-black waxy POM plate (light-to-dark),
  silver knob, gunmetal encoder, gold castellations/traces on the
  nice!nano.
- **Presentation pose** (rounds 4–5): the halves are parented to an
  empty on each outer bottom edge and posed 2.5 mm further apart,
  2.5° splayed in plan, 5° tented (hinge edge stays on the desk) —
  pure render transform; the case files build the assembled 2.11 mm
  seam layout.

## Surface textures and studio floor

All surface detail is procedural, so the render has no external image
maps to lose: generated-coordinate noise drives a bump normal and a
roughness range on the PLA tub/cover (coarse grain), the bone PBT caps
(finer satin), the waxy POM plate, the PCB soldermask/silk and the
metal pads/knob. Feature sizes are chosen for the 1600 px delivery (~3 px/mm),
not for powder-scale detail that would disappear.

The poron gasket pads are rendered at their compressed heights (bottom
2.55, top 1.00) on the tab roots +2.0 mm outward, so the exploded view
shows the real stack instead of empty space above the gaskets.

The studio floor is a 4 m plane 0.2 mm under the tub bottom, with the
same procedural treatment. It is created after the assembly bbox is
measured, so it never affects camera framing, registration, or the
explode distances; the soft key lights draw the contact shadow.

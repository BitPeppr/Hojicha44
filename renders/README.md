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

The same script accepts `--setups dark,bright` and
`--shots hero,exploded,top,macro,orbit` for extra diagnostic views; only
the two bright images are kept in the release.

Outputs land in `generated/renders/v0.5.0/<setup>/<shot>.png`, with
`MANIFEST.json` hashing each final PNG plus the tool versions. The
intermediate mesh tree (`generated/renders/assets/`) is regenerable and
gitignored; the scripts, this README, and the final PNGs are committed.

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
  (1.5 poron → 1.00, 33%); flat cap top 7.58, i.e. 2.4 mm proud of the
  3.20..5.20 top plate. The plate stays at the Choc v1 clip band
  (1.00..2.20) — moving it up would lose the clip engagement — so the
  thin top comes from the lip/plate above it. The top plate carries the
  key-field opening and the MCU/encoder/pwrsw windows, so the wiring
  strip is covered. The encoder top is 24.54; the encoder is left bare
  (no knob in the product views), and its rectangular terminal base is
  hidden by the cover window (12.0x11.7 body + 0.5/side).

## Surface textures and studio floor

All surface detail is procedural, so the render has no external image
maps to lose: generated-coordinate noise drives a bump normal and a
roughness range on the PA12 tub/cover (sintered grain), the PBT caps
(finer orange-peel), the PC plate, the PCB soldermask/silk and the
metal pads. Feature sizes are chosen for the 1600 px delivery (~3 px/mm),
not for powder-scale detail that would disappear.

The poron gasket pads are rendered at their compressed heights (bottom
2.55, top 1.00) on the tab roots +2.0 mm outward, so the exploded view
shows the real stack instead of empty space above the gaskets.

The studio floor is a 4 m plane 0.2 mm under the tub bottom, with the
same procedural treatment. It is created after the assembly bbox is
measured, so it never affects camera framing, registration, or the
explode distances; the soft key lights draw the contact shadow.

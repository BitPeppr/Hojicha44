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
                                # lighting setups, render queue
```

Reproduce the deliverable (bright hero + exploded):

```
brew install --cask blender                 # once
./case/.venv/bin/pip install trimesh        # once
bash renders/fetch_keycaps.sh               # once (network)
./case/.venv/bin/python renders/build_assets.py
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
all finger rows, Saddle Homing on the index-column home keys (F/J), Thumb
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
- Stack (z = 0 at the PCB top): substrate −1.60..0; plate 1.00..2.20;
  switch body 0.30..3.30; cap stem tip 1.50; flat cap top 7.58; cover
  4.70..7.70. The encoder top is 24.54; the 10 mm knob seats on the
  bushing (top 14.50) with its top 0.1 mm past the shaft (base 14.64).

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
renders/scene.py                # Blender 5.2 headless — assembly, PBR
                                # materials, lighting setups, render queue
```

Reproduce everything:

```
brew install --cask blender                 # once
./case/.venv/bin/pip install trimesh        # once
bash renders/fetch_keycaps.sh               # once (network)
./case/.venv/bin/python renders/build_assets.py
blender --background --python renders/scene.py -- \
    --samples 96 --res 1600x1000 --setups dark,bright \
    --shots hero,exploded,macro,orbit
```

Outputs land in `generated/renders/v0.5.0/<setup>/<shot>.png` with a
manifest of the input hashes. The intermediate mesh tree
(`generated/renders/assets/`) is regenerable and gitignored; the scripts,
this README, and the final PNGs are committed.

## Keycaps

[KLP Lamé](https://github.com/braindefender/KLP-Lame-Keycaps) by
braindefender (Nikita Shirokov) — **CC-BY-SA 4.0**, Choc stem + Choc size,
pinned to commit `8e4b89b484cafe3bcaced6b459a4e29660991a40` (see
`generated/renders/assets/PROVENANCE.json`). Variants used: Saddle Tilted
(top/bottom rows), Saddle (home row), Thumb (thumb cluster). Per the
license, attribution to the author is required alongside any use of these
shapes.

## Frame conventions (the fiddly part, recorded once)

- The committed boards, the plate DXFs and the case solids all share ONE
  storage frame (y-down, per-half origin) — verified by bbox overlap during
  the asset build. The scene assembles in that frame directly.
- kicad-cli's STEP export puts the substrate top at z = 1.60 (measured);
  the scene offsets the board by −1.60 so the PCB top lands on the case
  datum z = 0 (case lip plane measured at z = 4.70 in the same frame —
  matching the stack spec exactly).
- The hand-copper manifest is the ONE artifact in the design frame (y-up);
  that is a generator-internal convention and does not concern renders.

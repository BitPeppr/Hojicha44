# Hojicha44 — case interface (plate + gasket contract, rev-1)

Source of truth for plate geometry: `layout/generators/gen_plate.py`
(derives from the placed PCB; never hand-edit CAD).
Preview: `out/plate/Hojicha44-{Left,Right}-plate.svg`
Laser file: `out/plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm)
Gasket map: `out/plate/Hojicha44-{Left,Right}-lands.json` (board frame)

## Stack (top to bottom, per half)

| Layer | Spec |
|---|---|
| Top case | future design; cavity = plate outline + ≥0.5 clearance |
| Top gaskets | Poron strips/pads per lands JSON (`top`), 7×5mm contact |
| Plate | 1.5mm PC, outline = PCB outline (USB notch included) |
| Plate↔PCB gap | 2.0mm nominal (top-side diodes are 1.35mm) |
| PCB | 1.6mm, rev-1 release |
| Bottom gaskets | Poron per lands JSON (`bottom`), thick enough to clear socket bodies (~2.5–3mm) |
| Bottom case | future design |

## Plate openings (both halves)

- 22× 15×15mm Choc cutouts at switch centers/rotations (friction fit).
- 12.5×12.5mm square encoder hole (instance rot 0, body axis-aligned).
  The 13mm knob rides HIGH on the 20mm shaft — its bore never enters
  the hole. A 17mm round hole was rejected: it merges into the neighbour
  key cutout (18.2mm pitch vs 15 + 17).
- W1 windows: slide-switch strip + MCU/cell/USB core (tall top-side parts).
- W2 window + channel to the split-gap edge: TRRS mouth must exit; the
  plug overlaps plate-top height, so no solid edge allowed there.
- NO plate screws, NO tooling holes in the plate (pure gasket float;
  assembly aligns on the switches themselves).

## Gasket rules (enforced by the generator)

- Lands 7×5mm, ≥2.0mm clear of every cutout/hole/window/tooling.
- Max unsupported span 60mm on the bottom map always; any top span over
  60mm must be bridged by a bottom land in its middle half (tall parts
  block long rim runs up top — that is what the bottom map is for).
- Current maps: Left 10 top / 16 bottom, Right 16 top / 16 bottom.
- Case screws must NEVER touch the plate: clamp the case halves around
  it or pass through oversized plate reliefs (none in rev-1 — clamp).
- USB/TRRS port openings in the case walls per the notch/mouth positions
  in `spec/electronics.yaml`; antenna end keeps the 3mm plastic-only rule.

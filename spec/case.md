# Hojicha44 — case interface (plate + gasket contract, rev-1)

Source of truth for plate geometry: `plate/gen_plate.py`
(derives from the placed PCB; never hand-edit CAD).
Preview: `plate/Hojicha44-{Left,Right}-plate.svg`
Laser file: `plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm)
Tab map: `plate/Hojicha44-{Left,Right}-lands.json` (root centers for
jacket pockets)

## Mounting: tab-and-jacket suspension

The plate grows 6 discrete tongues per half (10mm wide, 5mm proud,
2mm root fillets, chamfered tips) that slot into silicone jackets held
captive in the case walls — no rim strips, no plate screws, no hard
contact anywhere. The assembly floats on 8 soft mounts per half, so
support uniformity comes from identical jackets at even spacing, not
from foam proximity (measured worst key-to-tab 51mm at the bottom-row
middle keys, 2.7 pitches; encoder sits 42mm out). The inner
(microcontroller) edge carries no tab: MCU/TRRS/encoder windows occupy
it fully and the remaining rim finger is narrower than a tab root, so
that zone floats between its flanking tabs by design — encoder push
stays soft there.
Encoder push over the window zone stays soft by design.

## Stack (top to bottom, per half)

| Layer | Spec |
|---|---|
| Top case | future design; cavity = plate outline (tabs included) + ≥0.5 clearance; wall pockets locate the 8 jackets per half |
| Plate | 1.5mm (material below), outline = PCB outline + tabs (USB notch included) |
| Plate↔PCB gap | 2.0mm nominal (top-side diodes are 1.35mm) |
| PCB | 1.6mm, rev-1 release (hangs from the plate on the switches) |
| Bottom case | future design; acoustic foam optional, non-structural |

## Jacket contract (case-side part)

- Pocket per tab: 10mm wide tongue, 1.5mm thick → jacket inner slot
  ~10.5 × 2mm, wall ~1.5mm silicone; pocket depth swallows the 5mm
  protrusion + 1mm.
- Jackets wrap top AND bottom of each tab (full isolation, no hard path).
- Tabs are solid (no holes): pins through tabs would hard-mount the
  plate and defeat the suspension.
- USB/TRRS port openings in the case walls per the notch/mouth positions
  in `spec/electronics.yaml`; antenna end keeps the 3mm plastic-only rule.

## Plate materials (pick one, re-run the generator to re-gate)

| Material | Fab | Notes |
|---|---|---|
| PC 1.5mm (default) | laser | softest feel, virtually unbreakable, cheapest prototype |
| POM 1.5mm | mill/laser | machines beautifully, slightly firmer than PC |
| FR4 1.6mm | route | stiff, cheap; glass dust when routing |
| ALU 1.5mm | laser/waterjet/CNC | balanced feel, best sound; isolate from copper |
| CARBON 1.5mm | mill ONLY (never laser: toxic dust + delamination) | stiffest; **conductive** — plate touches switch plastic + jackets only by construction, verify at assembly |

`MATERIAL` in the generator re-gates every web minimum
(PC/POM 1.0, FR4/ALU 1.5, CARBON 2.0); tab roots carry 2mm fillets
against crack initiation in every material.

## Plate openings (both halves)

- 22× 15×15mm Choc cutouts at switch centers/rotations (friction fit).
- 12.5×12.5mm square encoder hole (instance rot 0, body axis-aligned).
  The 13mm knob rides HIGH on the 20mm shaft — its bore never enters
  the hole. A 17mm round hole was rejected: it merges into the neighbour
  key cutout (18.2mm pitch vs 15 + 17).
- W1 windows: slide-switch strip + MCU/cell/USB core (tall top-side parts).
- W2 window + channel to the split-gap edge: TRRS mouth must exit; the
  plug overlaps plate-top height, so no solid edge allowed there.

# Hojicha44 — case interface (plate + gasket contract, rev-1)

Source of truth for plate geometry: `plate/gen_plate.py`
(derives from the placed PCB; never hand-edit CAD).
Preview: `plate/Hojicha44-{Left,Right}-plate.svg`
Laser file: `plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm)
Gasket map: `plate/Hojicha44-{Left,Right}-lands.json` (strip centerlines)

## Plate materials (pick one, re-run the generator to re-gate)

| Material | Fab | Notes |
|---|---|---|
| PC 1.5mm (default) | laser | softest feel, virtually unbreakable, cheapest prototype |
| POM 1.5mm | mill/laser | machines beautifully, slightly firmer than PC |
| FR4 1.6mm | route | stiff, cheap; glass dust when routing |
| ALU 1.5mm | laser/waterjet/CNC | balanced feel, best sound; isolate from copper |
| CARBON 1.5mm | mill ONLY (never laser: toxic dust + delamination) | stiffest; **conductive** — plate touches switch plastic + gaskets only by construction, verify at assembly |

`MATERIAL` in the generator re-gates every web minimum
(PC/POM 1.0, FR4/ALU 1.5, CARBON 2.0). Current maps: Left 3 strips
(382mm foam/side), Right 4 strips (402mm/side).

## Stack (top to bottom, per half)

| Layer | Spec |
|---|---|
| Top case | future design; cavity = plate outline + ≥0.5 clearance |
| Top gaskets | Poron strips per lands JSON, 2.5mm wide |
| Plate | 1.5mm (material above), outline = PCB outline (USB notch included) |
| Plate↔PCB gap | 2.0mm nominal (top-side diodes are 1.35mm) |
| PCB | 1.6mm, rev-1 release |
| Bottom gaskets | Poron strips, same XY as top (pairs), thick enough to clear socket bodies (~2.5–3mm) |
| Bottom case | future design |

## Gasket rules (enforced by the generator)

- Strips run the rim, 2.5mm wide centered 2.0mm in from the edge, top +
  bottom pair at the same XY — never staggered, never floating pads.
- Strips break at every opening (cutouts, encoder, windows), every pin
  zone underneath, and both port mouths (USB notch, TRRS channel) so
  cables exit clean.
- Every switch + the encoder sits within 55mm of foam (measured worst
  ~44mm at 2.3 pitches on 50gf Choc — better than the ~55mm typical of
  commercial perimeter-ring gasket boards). Encoder push over the window
  zone stays soft by design (6N, no foam under it).
- The plate edge IS the mounting tongue: it slots into the future case
  groove with the strips. No tabs, no plate screws, no tooling holes in
  the plate (pure gasket float; assembly aligns on the switches).
- Case screws must NEVER touch the plate: clamp the case halves around
  it. USB/TRRS port openings in the case walls per the notch/mouth
  positions in `spec/electronics.yaml`; antenna end keeps the 3mm
  plastic-only rule.

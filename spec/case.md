# Hojicha44 — case interface (plate + gasket contract, rev-1)

Source of truth for plate geometry: `plate/gen_plate.py`
(derives from the placed PCB; never hand-edit CAD).
Preview: `plate/Hojicha44-{Left,Right}-plate.svg`
Laser file: `plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm)
Tab map: `plate/Hojicha44-{Left,Right}-lands.json` (root centers for
jacket pockets)

## Mounting: tab-and-jacket suspension

The plate grows 8 discrete tongues per half (10mm wide, 5mm proud,
2mm root fillets, chamfered tips), each carrying a poron pad top and
bottom — no rim strips, no plate screws, no hard contact anywhere. Two
tabs are pinned (top edge above the outer key column, bottom-inner
corner under the MCU); the rest spread even. Support uniformity comes
from identical poron-padded tabs at even spacing, not from foam
proximity. The inner
(microcontroller) edge carries no tab: MCU/TRRS/encoder windows occupy
it fully and the remaining rim finger is narrower than a tab root, so
that zone floats between its flanking tabs by design — encoder push
stays soft there.
Encoder push over the window zone stays soft by design.

## Stack (top to bottom, per half)

| Layer | Spec |
|---|---|
| Top case | future design; cavity = plate outline (tabs included) + ≥0.5 clearance |
| Top gaskets | Poron pads 8×4mm on each tab (PORON layer in the DXF), 3mm thick |
| Plate | 1.5mm (material below), outline = PCB outline + tabs (USB notch included) |
| Plate↔PCB gap | 2.0mm nominal (top-side diodes are 1.35mm) |
| PCB | 1.6mm, rev-1 release (hangs from the plate on the switches) |
| Bottom gaskets | Same 8×4 pads under each tab (pairs at one XY); tub floor steps to −5.6 under the PCB zone (sockets + clearance) — foam sets tab height, floor depth is separate (see `case/params.py`) |
| Bottom case | future design; acoustic foam optional, non-structural |

- **Bottom-case floor (case design):** floor under the PCB zone must sit
  ≥7.6mm below the plate underside (≈5mm step below the tab-support floor
  at −2.55) — PCB bottom hangs 3.6mm below plate underside (2.0 gap + 1.6
  PCB) and sockets reach ~6.6mm, so a flat floor at sandwich depth
  collides; allow ~1.0mm clearance.

## Sources (suppliers, verified)

- **Rogers PORON** small sheets (4701-30-15, 3.18–6.35 mm):
  McMaster-Carr (search "Rogers 4701-30"), silicone-foams.com
  resogoo.com, h-oproducts. Min order is usually a 300×300 mm sheet
  — ≫ what 16×8×4 mm pads need.
- **Drop-in keyboard strips** (4701-40 stiffer fallback, 3×90×4 mm
  self-adhesive, ≈$8–12): Keebox (AliExpress), ThockKing universal pad,
  eBay 20-packs, Amazon BTNCL/GMMK. No Rogers part number on listings,
  CFD unstated — treat as ≈41 kPa / 134 g per pad worst case, splice 2
  strips per half.
- **Adhesive**: supported grade has PET film; keep strip adhesive
  surface toward the tab. Store sheets below 40 °C / 80 % RH or the
  adhesive bonds permanently to PET release liner.
- **Shear / punch**: 8×4 pads cut cleanly with a sharp craft knife or
  a 4/8 mm punch on a mat (no hot knife — poron tears). 1:1 paper print
  = cut template.
- Spec: PORON **4701-30 Very Soft, 240 kg/m³ (15 pcf)** — the least-dense
  -30 sub-grade — 3mm thick, single-sided adhesive-backed. CFD ~24 kPa
  (~3.5 psi) @ 25% → **~78 gf per 8×4mm pad at 25% compression**.
- Static load ~25 g/pad (≈200 g half-assembly / 8 bottom gaskets) →
  ≈8–10% self-compression (≈0.2–0.3 mm on 3 mm), leaving ≈2.5–3× of
  force headroom before 25% compression.
  Softest stock grade ⇒ lowest mount resonance (deepest sound, most
  high-frequency isolation) and most travel per unit force (bounciest of
  the options). Every higher rung (-40 ≈ 41 kPa / 134 g/pad; denser
  -20/-30 suffixes) moves brighter and firmer — the wrong way for thock.
- Swap ladder (all drop-in, no CAD change): **-30-15** (default, thock-max;
  cut from sheet/strip stock) → **-40 stiffer-fallback off-the-shelf strips**
  (e.g. Keebox 32-pack, ~41 kPa / ~134 g/pad, static ≈ 5%) → **-50** only
  if the build feels mushy.
- Assembly preload: design the case cavity for 15–20% foam compression —
  never near 0% (rattle, pads can't damp unloaded) and never past ~50%
  (cell densification = accidental hard mount, harsh sound). Per half:
  cavity = 1.5 + 6×(1−c), c ∈ [0.15, 0.20] → **6.3–6.6 mm** sandwich
  (1.5 plate + 2× 3mm pads).
- Plate note: foam spec is plate-agnostic; recommended **PC 1.5 mm**
  (softest, most flex, deepest sound) or **POM 1.5 mm** (balanced,
  good feel, stable). Bounce comes from plate span between tabs; foam
  sets mount resonance and damping. (FR4/ALU/CARBON change downstream
  only via `MATERIAL` — web minimums re-gate.)
- Cut 8×4 mm pads from 90×4 mm stock (≈11 pads per 90 mm strip; 16 pads/half
  ⇒ 2 strips/half). Single-supported (PET adhesive) preferred; unsupported
  stock needs spray/transfer adhesive and holds less well.<|end|>
- Pads stick to the TABs (plate), top and bottom — never to the case,
  so the assembly keeps its gaskets on disassembly. Pad centers = tab
  root centers + 2.0mm outward (`lands.json`); placement map on the PORON DXF layer.
- USB/TRRS port openings in the case walls per the notch/mouth positions
  in `spec/electronics.yaml`; antenna end keeps the 3mm plastic-only rule.

## Poron pad-to-tab margin (rev-1, verified 2026-10-16)

Pad orientation from the generator (`hl` scales the transverse vector,
`hw` the outward one): the **8 mm axis runs LATERAL** across the 10 mm
tongue, the **4 mm axis runs ALONG** the 5 mm tongue (pad spans rim-line
to +4.0 → 1 mm tip spare, no tip overhang). All 16 pad corners test
on-plate (point-in-poly within 0.1 mm), but the lateral squeeze is tight:
**tightest corner-edge ≈ 0.35 mm on every tab, both halves** (uniform by
construction). The 1.5 mm tip chamfers narrow the tongue exactly where
the pad's outer corners sit. A laser kerf of ≈0.1–0.2 mm on top of ≈0.1 mm
part tolerance could nibble that margin in the real world. Rev-2:
slightly narrower pad (6–7 mm wide) or a longer tab. Current geometry is
plate-safe in CAD.
- No tip overhang — projection proof over all 8 tabs × both halves: every
  pad spans +0.0→+4.0 along the tongue against the +5.0 tip (1.0 mm spare),
  lateral half-width 4.0 against 5.0 nominal. Support is structural, not
  marginal: tongues splice outward of solid rim, tab eligibility bars any
  opening within web minimum of the tab frame, so solid material sits
  under every pad — the 0.35 mm is purely a manufacturing-tolerance
  margin, not a support question.
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

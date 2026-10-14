# Hojicha44 — first-article checklist (hands + parts required)

Do these in order, both halves where marked ×2. Nothing here can be proven
in software — this is the release gate for the physical items. Prints:
`out/fit/Hojicha44-{Left,Right}-fit.pdf` (Edge.Cuts + silk + fab + F.Cu
pads, 1:1 — print at 100% / actual size, then calibrate: column-adjacent
key centres must measure **19.00mm**; if not, the print scaled and nothing
below counts). The fit sheet shows the PCB only; the 16mm encoder
knock-through lives in the plate DXF (`layout/generated/v2/outlines/plate.dxf`),
which is the cutout source — not the PCB print.

## 1. Paper fit test (before ordering anything)

- [ ] Module footprint: place a real nice!nano on the print, pin-1/USB end
  to the notch edge. All 24 pads must sit on printed copper.
- [ ] Socket rows on print measure **15.24mm** apart, 2.54mm pitch.
- [ ] USB notch measures **11mm wide**; dry-fit the actual USB cable — with
  4.5mm sockets the plug sits above the PCB so 11mm is normally enough. If
  the housing hits the shoulders beside the notch, widen it to ~14mm.
- [ ] Encoder shaft hole over the anchor; 13mm knob clears the 16mm plate
  cutout on paper (spin circle).
- [ ] 301230 cell outline (12×30mm) fits between the socket rows on print.
- [ ] TRRS gap on print/caliper: board-edge to board-edge **20.42mm** at
  the jack height; plastic mouth-to-mouth **22.40mm** with each mouth
  **0.99mm recessed** behind its edge (silk tops at 21.40mm, 0.49mm
  recessed — NOT protruding). 90-degree plugs fit easily in this gap.
- [ ] Fab limits confirmed with the chosen fab BEFORE ordering: 2-layer
  1.6mm, 0.25mm track / 0.2mm clearance / 0.8-0.4mm via accepted; rev-2
  flex slots (typically >=1mm) quoted separately.

## 2. Bare-board DMM (before soldering modules)

- [ ] ×2 JST pigtail red → JST pin 1 (`+` mark), black → pin 2. Meter it —
  reverse polarity kills board and cell.
- [ ] ×2Pack+ to RAW with switch ON (<1Ω); switch OFF open. Record which
  slider end is ON (either is fine, just label it).
- [ ] On a real nice!nano (not yet soldered): RAW↔B+ short, GND↔B− short,
  RAW↔VCC open (OL). Power must enter via RAW; B+/B− holes stay open.

## 3. Assembly order (both halves)

- [ ] Diodes → sockets → TRRS → JST → switch → encoder. Modules last.
- [ ] TRRS cable mated with **both halves OFF *and* USB unplugged from
  both** (switch OFF alone is insufficient — USB still powers the
  controller), then switch on. Sleeve-GND mates at an angle; live mating
  glitches TX/RX and can brown-out the charger MOSFETs. Reverse on
  teardown: switches OFF, cable out, then USB.
- [ ] Antenna end: 5mm copper-free respected, no case material within 3mm.

## 4. Power-on

- [ ] ×2 Charge with switch ON: orange LED lights; OFF does nothing
  (switch is upstream of RAW — expected, label the case).
- [ ] ×2 TRRS continuity jack-to-jack over a straight cable: left
  TIP→right TIP, left RING1→right RING1, sleeve→sleeve (<1Ω each);
  RING2 open both ends (must never join batteries).
- [ ] ×2 Encoder: spin both directions + push click register; knob clears
  the plate through full rotation.
- [ ] Stack height: 4.5–5.0mm rows swallow the 3mm cell + PCM with
  clearance; JST sits beside the cell, not under the stack.
- [ ] BLE range with battery and case: with cells fitted and halves in
  the gasket case, each half links and types at the intended desk distance
  (no dropouts); note the measured range. If range disappoints, try the
  301228 fallback before re-spinning.

Pass all → Gerbers. Fail anything → file an issue with the measured value.

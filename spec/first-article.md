# Hojicha44 — first-article checklist (hands + parts required)

Do these in order, both halves where marked ×2. Nothing here can be proven
in software — this is the release gate for the physical items. Prints:
`out/fit/Hojicha44-{Left,Right}-fit.pdf` (Edge.Cuts + silk + fab, 1:1 —
print at 100% / actual size, then calibrate: adjacent key centres must
measure **19.05mm**; if not, the print scaled and nothing below counts).

## 1. Paper fit test (before ordering anything)

- [ ] Module footprint: place a real nice!nano on the print, pin-1/USB end
  to the notch edge. All 24 pads must sit on printed copper.
- [ ] Socket rows on print measure **15.24mm** apart, 2.54mm pitch.
- [ ] USB notch measures **11mm wide**; plug seats with the shell clearing.
- [ ] Encoder shaft hole over the anchor; 13mm knob clears the 16mm plate
  cutout on paper (spin circle).
- [ ] 301230 cell outline (12×30mm) fits between the socket rows on print.

## 2. Bare-board DMM (before soldering modules)

- [ ] ×2 JST pigtail red → JST pin 1 (`+` mark), black → pin 2. Meter it —
  reverse polarity kills board and cell.
- [ ] ×2Pack+ to RAW with switch ON (<1Ω); switch OFF open. Record which
  slider end is ON (either is fine, just label it).
- [ ] On a real nice!nano (not yet soldered): RAW↔B+ short, GND↔B− short,
  RAW↔VCC open (OL). Power must enter via RAW; B+/B− holes stay open.

## 3. Assembly order (both halves)

- [ ] Diodes → sockets → TRRS → JST → switch → encoder. Modules last.
- [ ] TRRS cable mated with **both halves OFF**, then switch on
  (sleeve-GND mates at an angle; live mating glitches TX/RX).
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

Pass all → Gerbers. Fail anything → file an issue with the measured value.

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
- [ ] Encoder shaft hole over the anchor; 12.5mm square plate hole clears
  the EC11E body (11mm class) at 0.4/side — the 13mm knob RIDES HIGH on
  the 20mm shaft, its bore never enters the hole (verify ≥6mm shaft
  engagement + spin clearance above the plate, not through it).
- [ ] 301230 cell outline (12×30mm) fits between the socket rows on print.
- [ ] TRRS gap on print/caliper: board-edge to board-edge **20.42mm** at
  the jack height; plastic mouth-to-mouth **22.40mm** with each mouth
  **0.99mm recessed** behind its edge (silk tops at 21.40mm, 0.49mm
  recessed — NOT protruding). 90-degree plugs fit easily in this gap.
  Measure the boot diameter of the chosen 90° cable; straight plugs are
  prohibited (two noses would meet head-on across the 22.40mm mouth gap).
- [ ] Fab limits confirmed with the chosen fab BEFORE ordering: 2-layer
  1.6mm, 0.25mm track / 0.2mm clearance / 0.8-0.4mm via accepted; rev-2
  flex slots (typically >=1mm) quoted separately.
- [ ] ORDER GATE — do not place the fab order until every box in §1 passes
  on paper AND the fab has accepted the limits above. §2–§5 need physical
  boards; nothing below can substitute for a failed box here.

## 2. Bare-board DMM (before soldering modules)

- [ ] ×2 JST pigtail red → JST pin 1 (`+` mark), black → pin 2. Meter on
  continuity beep AND record the readings — this board has NO
  reverse-polarity protection. Any doubt: STOP, do not plug the cell in.
  Reverse polarity kills board and cell.
- [ ] ×2Pack+ to RAW with switch ON (<1Ω); switch OFF open. Record which
  slider end is ON (either is fine, just label it).
- [ ] Solder the slide switch FIRST, before any other part, and re-verify:
  JST-1 → RAW <1Ω with switch ON, open with OFF. The switch is the only
  charge/safety disconnect — a dry joint here defeats it silently.
- [ ] On a real nice!nano (not yet soldered), meter on continuity beep:
  RAW↔B+ short (<1Ω), GND↔B− short (<1Ω), RAW↔VCC open (OL, no beep).
  Power must enter via RAW; B+/B− holes stay open.

## 3. Assembly order (both halves)

- [ ] Diodes → switch (already done in §2) → sockets → TRRS → JST →
  encoder. Modules last. Cell sandwich goes in AFTER all soldering: Kapton
  (polyimide) tape over the pouch face AND over the nano underside
  components, then cell between socket rows with the 4.5–5.0mm stack. No
  Kapton, no cell. Dress JST leads beside the cell, never under the stack.
- [ ] TRRS cable mated with **both halves OFF *and* USB unplugged from
  both** (switch OFF alone is insufficient — USB still powers the
  controller), then switch on. Sleeve-GND mates at an angle; live mating
  glitches TX/RX and can brown-out the charger MOSFETs. Reverse on
  teardown: switches OFF, cable out, then USB.
- [ ] Antenna end: 5mm copper-free respected, no case material within 3mm.
  Case shell near the antenna end must be plastic/wood — no metal, no
  carbon fibre (both detune/kill 2.4GHz).
- [ ] Plate clearance: top-side diodes stand ~1.35mm in the inter-key gaps.
  Any plate above the PCB needs relief pockets over the diodes or ≥1.5mm
  standoffs — a flat plate will rest on diodes. Validate on the build.
- [ ] Plate fit (rev-1 plate in `plate/`): 1:1 print over the real PCB —
  every 15×15 cutout frames its switch footprint, the 12.5² hole frames
  the encoder body, W1/W2 windows clear switch/module/JST/TRRS bodies,
  outline matches edge-for-edge including the USB notch. Seat one real
  Choc switch per region (corner/edge/thumb): clips engage, no rock.
- [ ] Poron pads (rev-1 plate): 8×4mm 4701-40 pads stuck top+bottom on all
  8 tabs per half per the PORON DXF layer — full tab coverage, none
  overhanging into cutouts/windows; peel-test one: adhesive holds the
  tab, not the case.

## 4. Power-on

- [ ] ×2 Charge with switch ON: orange LED lights; OFF does nothing
  (switch is upstream of RAW — expected, label the case).
- [ ] ×2 TRRS continuity jack-to-jack over a straight cable: left
  TIP→right TIP, left RING1→right RING1, sleeve→sleeve (<1Ω each);
  RING2 open both ends (must never join batteries).
- [ ] USB notch solder inspection: the socket pads sit 0.78mm from the
  notch edge — tight for fab and solder tolerance. Loupe-check for mask
  registration and solder bridging at the notch shoulders; record a photo.
- [ ] ×2 Encoder: spin both directions + push click register; knob clears
  the plate through full rotation.
- [ ] Stack height: 4.5–5.0mm rows swallow the 3mm cell + PCM with
  clearance; JST sits beside the cell, not under the stack.
- [ ] BLE range with battery and case: with cells fitted and halves in
  the gasket case, each half links and types at the intended desk distance
  (no dropouts); note the measured range. If range disappoints, try the
  301228 fallback before re-spinning.

- [ ] CPL: `pos.csv`/`pos-smt.csv` use KiCad convention (negated Y, board
  origin) — JLCPCB/PCBWay ingest KiCad CPL natively, do not flip axes.

## 5. Firmware bring-up (first flash)

- [ ] First flash per half MUST use full chip erase (`--erase`): P0.09/P0.10
  (spare D10 + encoder push) are NFC pins and stay locked to the NFC
  peripheral until UICR `nfct-pins-as-gpios` is written, which needs the
  erase. A non-erased first flash boots fine but leaves encoder push and
  the spare dead with no error.
- [ ] After flashing both halves: BLE-pair halves, confirm keys from each
  side, then verify encoder push-click registers AND the spare input
  toggles. If either is dead, re-flash that half with `--erase` before
  suspecting hardware. Keymap content is still DRAFT — this step proves
  the inputs, not the layout.

## 6. Case labels (apply before daily use)

- [ ] Each half, at the switch: `CHARGE ONLY WHEN ON`.
- [ ] Each half, at the TRRS jack: `TRRS: POWER OFF + USB OUT BOTH SIDES`.
- [ ] Inside the battery bay: `+ RED PIN1 — METER BEFORE PLUG-IN`.

## 7. Accepted prototype deviations + rev-2 backlog

These ship as-is in rev-1; recorded so nobody re-litigates them, and so
rev-2 has a list.

- Left VBAT runs a 184.82mm loop around the matrix (0.78mm notch-to-pad
  gap blocks the direct route). Functional: ~18.5mV drop @100mA. Rev-2:
  revisit with B.Cu pour.
- Ground is a 0.25mm daisy-chain, no pour. OK for prototype; rev-2 gets a
  B.Cu pour for EMC/robustness.
- USB notch-to-socket-pad 0.78mm (see §4 inspection). Rev-2: buy clearance
  if the outline allows.
- Diode height vs plate (§3) and antenna-enclosure rule (§3–§4 range test)
  validate on the first article; failures go to the case design, not a
  PCB re-spin, unless the range test indicts the layout.

Pass all → Gerbers. Fail anything → file an issue with the measured value.

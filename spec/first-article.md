# Hojicha44 — first-article checklist (hands + parts required)

Do these in order, both halves where marked ×2. Nothing here can be proven
in software — this is the release gate for the physical items. Prints:
`out/fit/Hojicha44-{Left,Right}-fit.pdf` (Edge.Cuts + silk + fab + F.Cu
pads, 1:1 — print at 100% / actual size, then calibrate: column-adjacent
key centres must measure **19.00mm**; if not, the print scaled and nothing
below counts). The fit sheet shows the PCB only; the 12.7mm square encoder
hole lives in the laser plate (`plate/Hojicha44-{Left,Right}-plate.dxf`),
which is the cutout source — not the PCB print. (`layout/generated/v2/outlines/plate.dxf`
is legacy ergogen output, superseded by `plate/`.)

Print notes (for the case tub/cover orders): PETG or ASA recommended
(PC also works); print both parts AS ORIENTED — tub open-face-up,
cover underside-up — every feature is then self-supporting except the
USB/TRRS mouth arc bridges (~7mm spans), which typically bridge
support-free on any decent bridge profile; add supports only for a
poor bridger.

## 0. Pilot batch

- [ ] **Build 5 half-pairs (10 halves)** for the first article: enough
  to test switch retention, plate fit, case fit and battery life with
  a spare in every failure-prone class, small enough that a design
  mistake is not expensive. Order quantities (spec/research-open-items-2026-10-21.md):
  20 PCBs (10 halves + 10 spares), 20 plates, 12–15
  cases (3–4 printed spares per design), 490 switches (14 packs of
  35), 450–500 hotswap sockets, 500 diodes, 12–14 cells, 150 magnets
  (16/half + spares), 12 modules, 20 polyfuses.
- [ ] Indicative unit cost **~USD 35–70 per half** (PCB ~USD 2/5 pcs
  + ENIG adder, PCBA ~USD 8 setup + per-joint, PA12 ~USD 2–4 per
  half, PG1350 ~USD 1.1 ea, LiPo USD 1.5–6, N52 USD 0.01–0.08).

## 1. Paper fit test (before ordering anything)

- [ ] **Regenerate the fit PDFs first** — `out/fit` renders predate the
  16 Oct boards (and the case v3.3-v3.5 port changes); rebuild prints
  from the current tracked artifacts before any caliper check here.
- [ ] **Choc cutout test coupon (PRE-ORDER, new in rev 2) — the support
  strategy hinges on this.**
  *What it is:* a **test piece** — one small offcut of the REAL plate
  material and thickness (1.2mm PC), cut by the same vendor with the
  same process, carrying every candidate feature. Not a full plate.
  *What to ask for:* a **100 x 100mm sheet of 1.2mm PC** with four
  **20 x 20mm squares**, one hole each of **13.8 / 14.0 / 14.2 /
  15.0mm**, all holes concentric in their square, PLUS one extra
  20x20mm square with a 14.0mm hole **and a 0.40mm-deep pocket in its
  underside** (the diode relief, 2.87 x 1.72mm, offset 9.5mm from the
  hole centre — the fabricator needs the DXF, and it is the RELIEF
  layer of the plate file). Cost: a few dollars; turnaround: a day.
  *What to do with it:* for each square (a) drop a PG1350 in — does
  the body pass the hole? (b) press the switch down onto the coupon
  and LIFT it — does the clip arm catch the plate's underside?
  Expected: at 14.0 the lip (0.9–1.3mm above the PCB) grabs the
  1.00mm underside and the 14.8mm ears seat on the 2.20mm top face;
  13.8 may be line-to-line (a switch that will not insert); 15.0
  reproduces the old rev-1 failure (the ears fall into the hole, no
  retention, the switch rocks out). On the relief square: the pocket
  must be 0.40mm deep, NOT through (0.80mm of material must remain),
  and the plate must still sit flat on the switch housings.
  *Why it is worth a day:* the decisions are 0.1–0.2mm of hole size
  and 0.05mm of ear seating — smaller than the datasheet tolerance
  and smaller than any drawing can promise. If 14.0 does not catch,
  drop to 13.9 and re-cut the coupon, rather than discovering it
  after ordering 2 plates and 44 switches.
- [ ] **Plate relief pocket (PRE-ORDER, new in rev 2)** — the plate
  carries a 0.40mm-deep pocket in its UNDERSIDE under each of the 22
  diodes (RELIEF layer in the plate DXF: machine 0.40mm, do NOT cut
  through; a through-cut leaves the switch without plate support).
  Test on the coupon: with the pocket floor 1.40mm above the PCB top
  and the diode top measured at 1.26mm, there must be no contact and
  the plate must still sit flat on the switch housings. Verify the
  pocket is 0.40mm, NOT through: the remaining material under it is
  0.80mm.
  The stack to check on the same coupon: the plate underside 1.00mm
  above the PCB top, the plate top 2.20mm — the switch's clip lip
  (0.9–1.3mm above the PCB) must grab the underside and the 14.8mm
  ears (starting at 2.2mm) must seat on the plate's top face with no
  interference.
- [ ] **Encoder window (PRE-ORDER, new in rev 2)** — the plate's encoder
  window is now **16.2 x 12.4** (rev 1 had a 12.7 square, which fouled
  the encoder's terminal blocks once the plate moved down to the 1.00mm
  gap). On the coupon (or a scrap of the same 1.2mm PC): the encoder
  must pass the window freely, and the two terminal blocks must clear
  it with room to spare. **Caliper the real encoder**: the width
  across the A/B/C and S1/S2 terminal blocks at 1.0mm and 1.5mm above
  the PCB. If the blocks do NOT protrude above ~1.5mm (the vendored
  STEP may overstate them), the window can go back to 12.7 square and
  the plate batch saves material — but only with that measurement in
  hand, not with the STEP alone.
- [ ] Module footprint: place a real nice!nano on the print, pin-1/USB end
  to the notch edge. All 24 pads must sit on printed copper.
- [ ] Socket rows on print measure **15.24mm** apart, 2.54mm pitch.
- [ ] USB notch measures **11mm wide**; dry-fit the actual USB cable — with
  4.5mm sockets the plug sits above the PCB so 11mm is normally enough. If
  the housing hits the shoulders beside the notch, widen it to ~14mm. Plug
  axis rides high on 4.5mm sockets with a ~9mm-inboard shell, so verify the
  housing clears the plate top in the solid-board overlap zone (seating depth), not just the notch width.
- [ ] Case port bores (case v3.3 **measured breach** + v3.4 shaped
  bores + v3.5 pwrsw aperture — no fixed depths): **USB = 14.0-wide
  bottom-filleted slot (z 2.0..top, plug axis rides at the lip plane) /
  TRRS = Ø9.5 round bore (axis z 2.5, measured off the vendored STEP)**;
  all three reach past the skin (printed `out=20.20` USB / `10.70` TRRS /
  `10.70` pwrsw at OUTSET 8.2 — re-read the live census line).
  Caliper the actual cables at the bore
  plane (with the bores open in a printed 1:1 slice — pre-v3.4 slices
  are the "gaping rectangle" and must not be printed): USB-C housing
  must clear **14.0 with margin** and the USB plug must SLIDE FULLY to
  the receptacle in the printed slice; the 90° TRRS boot must measure
  **≤ 8.5** across (it then swings freely inside the Ø9.5 bore).
  Measure the Z bands too: an overmold bottom below z 2.0 above the PCB
  means lowering `USB_MOUTH_Z0`; a jack axis far off the z 2.5 estimate
  (mouth-face centre vertex of the vendored PJ-320A STEP) means
  shifting `TRRS_MOUTH_ZC` (the bore then recentres on
  the jack); if the slicing shows a clipped-looking bore mouth, check
  the axis first. A boot wider than 8.5 means increasing `TRRS_MOUTH_R`
  in `case/params.py` and re-running `gen_case.py` BEFORE the real case
  order. Bores stop at the floor slab top (sill under each opening
  stays solid) — print slices must show **no through-hole in the case
  bottom**.
- [ ] PWR aperture (v3.5): 5.0-wide slot at the north rim plateau
  (mouth centre x 106.3/185.2, slot SILL 0.7 below the switch body top
  z 5.0). Flick test in the printed slice: a fingernail entering from
  above must reach and slide the red lever across its travel; caliper
  the lever blade across the 10mm body (design assumed ~2.0 blade +
  ±0.8 travel = ~3.6 sweep, 0.7/side margin in `params.py` — if the
  real sweep is wider, widen `PWRSW_MOUTH_W` and re-run
  `case/gen_case.py` BEFORE the case order). The window is centred on
  the switch origin (M3: the neutral lever band = origin ±1.8 sits
  centred in the 5.0 mouth at 0.7/side; the M2-era "window east of the
  switch centre" premise was a datasheet misread of the drawn nub — it
  is one travel extreme, the neutral lever is centred on the COM
  pin/footprint origin). SAT stands: mouth ≥3 to tab-4's pocket, ~1.8
  web to the USB mouth.
- [ ] Magnets — 16× Ø4×2×2mm N52 (TUB pockets) + 16× Ø4×1.5mm N52
  (COVER pockets, T4 review fix: shallower cover pocket -> 1.3mm floor
  over the magnet; the Ø4×2/Ø4×1.5 pair is asymmetric-tolerant, faces
  magnets still meet exactly at the lip plane): the tub has 8 × Ø4.3×2.2
  recesses in the band top, faces flush at the lip plane; the ring
  cover mirrors them face-down with 8 × Ø4.3×1.7 recesses. Glue: tub
  magnets FACE-UP flush, cover magnets FACE-DOWN flush (the 0.2mm glue
  seat decides the zero-gap stop). Station coordinates print in
  the gen_case/gen_cover census lines each run (PCB frame; LEFT tub at
  writing time: (130.17,57.76), (136.55,12.92), (133.44,-55.70),
  (67.30,-43.06), (19.46,-28.91), (-18.35,8.02), (6.74,52.44),
  (68.42,64.16) — the LEFT set is the SOURCE and Right is its exact
  mirror x->291.5-x). Cross-check one per half in
  the slicer against the STEP. Tests: dry-fit the cover with NO
  magnets and NO plate — it sits level at the 6.0 lip plane; then drop
  the plate in (pads live on its tabs) and reseat the cover: the ring
  underside must now PRESS each tab pad — a visible cushion gap at any
  tab zone is a reject (the foam compression mark check), and the
  stack rides ~0.5mm lower than the no-plate seat (uncompressed top
  pads 6.5 vs the 6.0 ring underside = the designed 16.7% preload);
  then with magnets it must snap-seat without rocking; poron must not
  stick to either case part. **Pull test (M4 gate): with the plate
  installed, a straight lift must hold ≥1.5 kg before the ring lifts**
  (8 mixed pairs ≈ 2–2.8 kg predicted; the glue lap is the weak link,
  not the 1.3mm pocket floor — the floor's rim shear is ~10mm² of
  perimeter at FDM in-plane strength, orders above the pull).
- [ ] Ring cover dry-fit: outer face FLUSH with the tub skin (lid seam
  visible but flush — fingernail probe), inner edge = PCB rim + 0.5
  (key field clear; the ring BRIDGES the tabs and presses the top
  pads), the plug's overmold rides through
  the cover slot and pokes ~0.2 above the top face (the module tops at
  7.7, below the ring), the jack boot
  clears the blind W2 tunnel (solid ceiling above the boot at 7.25),
  and the tub/ring pwrsw slots are ALIGNED into a single 5.0 flick
  channel (the ring's slot keeps a 1.1 inner web — confirm it prints
  intact).
- [ ] Encoder shaft hole over the anchor — **FIRST pre-order bench check,
  order (1) hole sample, (2) Choc clip fit + kerf on the 0.71mm pad
  margin (needs a laser-cut sample), (3) the plug slices below**. The
  12.7mm square plate hole clears the vendored EC11 STEP body, which
  measures **12.30 wide in the plate band (z 2.0..3.5)** — nominal
  0.20/side (the old 12.5 was spec'd 0.4/side off the "11mm class";
  the real part is wider) — drop the real (or spec-identical) encoder
  through a laser-cut hole sample before ordering the plate batch:
  ±0.2 fab tolerance can still rub; a further widen to 13.0 costs a
  ~3.35mm web — but to the W2 TRRS window (3.65 -> 3.35), NOT to
  SW_L17, whose web stays ~9.15mm (the mislabeled pairing a reviewer
  caught, fixed 2026-10-20). The 13mm knob RIDES HIGH on
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
  1.6mm, 0.25mm track / 0.2mm clearance / 0.30mm-drill-in-0.65mm-pad
  signal vias (0.50-in-1.00 power) accepted — the old "0.8-0.4mm" line
  quoted the KiCad template, not the boards; rev-2
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

- [ ] Diode placement map: diodes carry NO silk references (the 4mm
  inter-cutout gap fits no text) — the naming is deterministic:
  **D_Lxx / D_Rxx sits +x of its same-numbered switch (D_Lxx ↔
  SW_Lxx), 9.5mm in the local +x of the switch centre** (thumb-arc
  exceptions ride the switch rotation: local deltas (9.50,0.08),
  (9.24,−2.22), (8.43,−4.39), (7.12,−6.29) — i.e. still the switch's
  +x side). Solder direction/polarity comes from the cathode tick and
  the released net list (underline each D's col/row from its switch
  before soldering). No free-floating "nearest diode" guesses.
- [ ] Socket stack height caliper: BEFORE the cell goes under, measure
  the MATED height of the ordered machine-pin socket + pin set
  (ground pin tip to mating face) — accept 4.5–5.0mm only; reject any
  set that reads <3.5 (2.11mm-class) or >5.0 (slides under the module
  body). The stack budget assumes this number — record it in the notes.
- [ ] **Solder order (one list, no ambiguity — "sockets" means two
  different parts, so they are named):**
  1. slide switch (done in §2, FIRST — it is the charge disconnect)
  2. diodes (D_Lxx/D_Rxx, cathode tick to the row)
  3. **Choc hotswap sockets** (B.Cu, under each switch)
  4. **nice!nano machine-pin sockets** (the 2×12 headers — NOT the Choc
     sockets in step 3)
  5. TRRS jack, JST, slide-switch wiring, EC11 encoder
  6. modules last (nice!nano into its headers)
  7. **cell sandwich** (Kapton over the pouch face AND the nano
     underside, then the cell between the socket rows at the measured
     4.5–5.0mm stack; no Kapton, no cell; JST leads beside the cell,
     never under the stack)
  8. **plate onto the switches** (the plate's switch holes take the
     switch bodies, the gasket tabs hang over the rim)
  9. **PCB into the tub** (feet/rim seats, no screws)
  10. **poron pads** (bottom pads on the tabs, then the top pads)
  11. **magnets** (tub face-UP, cover face-DOWN — faces meet at the lip
      plane)
  12. **cover on** (the ring presses the top poron pads at 16.7%)
- [ ] TRRS cable mated with **both halves OFF *and* USB unplugged from
  both** (switch OFF alone is insufficient — USB still powers the
  controller), then switch on. Sleeve-GND mates at an angle; live mating
  glitches TX/RX and can brown-out the charger MOSFETs. Reverse on
  teardown: switches OFF, cable out, then USB.
- [ ] Antenna end: 5mm copper-free respected, no case material within 3mm.
  Case shell near the antenna end must be plastic/wood — no metal, no
  carbon fibre (both detune/kill 2.4GHz).
- [ ] Plate clearance: top-side diodes stand ~1.35mm in the inter-key gaps
  under solid plate (gated ≥0.25mm from every cutout edge) with a 2.0mm
  nominal plate gap → **0.65mm nominal vertical clearance**. Slide a
  0.5mm feeler under the plate over each diode row on the real build; any
  contact/scrape means relief pockets over the diodes or a gap increase
  (case-side fix). Validate on the build.
- [ ] Plate fit (rev-2 plate in `plate/`): 1:1 print over the real PCB —
  every 14×14 cutout frames its switch footprint, the 16.2×12.4 window frames
  the encoder body, W1/W2 windows clear switch/module/JST/TRRS bodies,
  outline matches edge-for-edge including the USB notch. Seat one real
  Choc switch per region (corner/edge/thumb): clips engage, no rock.
  (Laser kerf enlarges cutouts ~0.1–0.2mm, so expect a slip fit, not
  interference — rock is the reject criterion. If loose in every region,
  rev-2 cutout tightens 15.0 → 14.9.)
- [ ] Poron pads (rev-1 plate): 7×4mm 4701-30-15 pads stuck top+bottom on all
  8 tabs per half per the PORON DXF layer — full tab coverage, none
  overhanging into cutouts/windows; peel-test one: adhesive holds the
  tab, not the case.
- [ ] Gasket preload: dry-stack plate + pads (no PCB) and measure sandwich
  vs the 6.3–6.6mm cavity target (15–20% foam compression per
  `spec/case.md`). Under 6.3 crushes past 20% (bright/harsh); over 6.6
  leaves the stack loose (rattle).

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
  side, then verify the encoder push-click registers. If it is dead,
  re-flash that half with `--erase` before suspecting hardware. Keymap
  content is still DRAFT — this step proves the inputs, not the layout.
- [ ] The SPARE input (D10) has no keymap binding and no test pad, so
  it cannot be "verified by toggling" — check it with a DMM: the spare
  pin is MCU **D10 = P0.09** (module header pin 13, the pin labelled
  D10 on the silkscreen). With the half unpowered, continuity from the
  header pin to the D10 net pad; with it powered, the pin idles high
  and a scope/DMM shows the level. A "toggling spare" test would need a
  binding (or a test pad) that does not exist — do not read a pass here
  as a dead pin (audit 2026-10-21).

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

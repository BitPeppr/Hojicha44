# Hojicha44 — case CAD (CadQuery, parametric)

Bottom tub + (later) top cover, derived from the laser plate — never
hand-drawn. Roadmap Phase 5: CadQuery generates, FreeCAD inspects,
Blender visualises.

## Layout

- `params.py` — every dimension with its spec source. Change here.
- `gen_case.py` — tub generator + self-checks. Outputs to `case/out/`
  (STEP tracked since 2026-10-24; STL gitignored/regenerable; use
  `CASE_OUT=case/out-dev` for scratch builds).
- `gen_cover.py` — the top plate (thin-top v4; the old ring cover is
  history). It imports the
  tub's `compute_ports` / `pocket_layout` / `magnet_stations`, so the
  two parts interlock from shared anchors; same output convention.
- `probe_bores.py` — offline bore shape audit on the finished solids
  (not part of CI; run before a real print).
- `requirements.txt` — pinned CadQuery (`case/.venv`, Python 3.12).

## Conventions (match the rest of the repo)

- Units mm. Frame = KiCad board frame (same as `lands.json` / plate DXF).
- z = 0 is the PCB top surface. Plate underside +1.00, plate top +2.20
  (1.2mm plate, 1.00mm gap). Current generator census (2026-10-24,
  v4.1): tub **57.5 cm³**, cover **15.2 cm³** per half — older figures
  in the changelog are historical (pre thin-top / floor / ledge revs).

## Regenerating the order-time geometry (print-manifest recipe)

The shops are sent exactly what `generated/print/v0.5.0/MANIFEST.txt`
hashes. If ANY generator constant changes, in the SAME commit:

    case/.venv/bin/python case/gen_case.py            # gates exit-0
    case/.venv/bin/python case/gen_cover.py           # gates exit-0
    shasum -a 256 case/out/* > /tmp/h.txt             # paste over the old hashes
    npm test                                          # print-manifest gate re-verifies

The STEP files are tracked and CI verifies their hashes; the STLs are
regenerable and gitignored. Never order from a stale hash.
- Single source of truth: `plate/Hojicha44-{half}-plate.dxf` (OUTLINE +
  tab geometry via `lands.json`). Spec numbers: `spec/case.md`.
- Generators own geometry; `case/out/` is scratch like `out/fit`.

## Status

(Entries are newest-first. Each older entry keeps the measured
values of ITS build — those are historical, not current; the v3.6
entry below is the current truth for every number it quotes.)

- v4.2 (2026-10-24, review-triage + strength round): **PETG at 100%
  infill is a supported self-print material** (user decision): strength
  audit in spec/case.md — thinnest structural features 1.2–2.6mm, PETG
  stiffer than the MJF PA12 reference on every load path, risks are
  warp/dimensional not strength; tests/spec_checks now pins FLOOR_T
  >= 1.5 and ledge web >= 1.0. **The 4 case/out STEP files are COMMITTED**
  and print-manifest-verified in CI (review §5.3: "CI green on a machine
  that never built the case"); STLs stay gitignored; the print manifest
  was re-recorded under the v4.1 geometry (same-commit rule honored).
  Review-driven gates elsewhere: plate/gen_plate --check gained the
  **z-stack gate** (every top-side part crossing the plate band
  1.00..2.20 must clear it via a window/relief — encoder terminals,
  diode relief, MCU+socket stack, TRRS, pwrsw, one table, one place);
  CI pins the ZMK reusable workflow + west.yml to the v0.3 COMMIT and
  gains build-variants.yml (all four keymap variants compiled, review
  P1.6). First-article fixes: the diode-relief feeler test replaced by
  direct pocket measurement (it was logically invalid against the
  intentional 1.00mm gap), order policy split (coupons vs batch),
  magnet polarity stack-test, PRE-MJF family-bound caliper, service
  story (module/cell swap = full teardown), stale dry-fit numbers
  (3.20 lip / 33% preload).

- v4.1 (2026-10-24, user "make the whole keyboard lower" round):
  the assembled case was 12.80mm tall and the bottom tub (10.80mm)
  carried almost all of it — 4.0mm of air under the PCB plus a 2.0mm
  slab. No-trim limits: FLOOR_CLEAR 1.0mm under the deepest untrimmed
  part (encoder legs −3.65) drops FLOOR_Z −5.6 → **−4.65**, and the
  floor slab got its own constant (FLOOR_T 2.0 → **1.7**; MJF-safe,
  braced by the 8 tab pockets). Tub bottom −7.60 → **−6.35**: assembled
  case **12.80 → 11.55mm**, desk→cap-top 15.18 → **13.93mm**. Tub volume
  67.3 → 57.5 cm³ (tripwire [55,82] intact), wall_min 2.62 unchanged;
  gates exit-0 both halves. (A further ~0.8mm is available only by
  clipping the THT leads after soldering — deepest untrimmable feature
  is the socket bump −2.85 — not enabled: user prefers no trimming.)

- v4.0 (2026-10-24, user "thin top / component-following" round):
  **the top case is a 2.0mm TOP PLATE at 3.20..5.20**, not a rim ring.
  User review: the ring read as an extraordinarily thick top and the
  caps barely poked out. The plate CANNOT move up (Choc v1 clip band
  1.00..2.20, spec/case.md), so the top came down instead: TOP_LIP_Z
  4.70 -> 3.20 (the 1.5mm TOP_FOAM_T at 33% compression; new
  TOP_PRELOAD) and COVER_T 3.0 -> 2.0. A 0.8mm-deep, 3mm-wide
  LEDGE (KEY_LEDGE_W/D) is relieved around the key field, so the
  caps stand ~3.2mm proud of the surface they sit in while the
  outer band/magnets keep the full 2.0mm plate height.
  The cover spans the key field with ONE merged opening around the 22
  KLP cap footprints (17.48x16.48 + CAP_CLEAR 1.0; enclosed material
  islands are dropped as void and gated by a scrap-volume limit) and
  covers the MCU/encoder strip with windows: MCU_WIN, ENC_WIN (shrunk
  from 17.2x13.2 to 13.0x12.7 = the measured 12.0x11.7 EC11 body at
  the cover band +0.5/side, so the rectangular terminal base is now
  hidden), PWRSW_WIN + nail notch, the shared USB slot, and the TRRS as
  a **Ø6.0 round SIDE hole** (zc 1.5, 0.7mm closed roof under the 5.2
  top; clears a 3.5mm barrel 1.25/side) instead of the Ø9.5 top-open notch. Cover magnets Ø4x0.5 (pocket
  0.7, floor 1.3). New CASE_OUT env var builds to case/out-dev so the
  placed v0.5.0 order record in case/out stays hash-valid. Gates: both
  tubs and both covers exit 0; cover 16.7 cm3, 8 enclosed scraps
  175 mm3 dropped, 8/8 magnets, band 7.68; stack-ties updated.

- v3.7 (2026-10-21, H-7 mirror closure): the right board outline's
  `mirror_matrix_inner_top` plateau order was the mirror of the left
  order, so the right rim carried a 0.41mm north-plateau bump. Fixed the
  config (plateau points now mirror exactly: 194→181 like left 97.5→
  110.5), regenerated layout/board/plate. The right plate tab walk was
  still landing one 1mm sample over at the bottom-inner tab (x 170.57 vs
  mirrored 170.64, 0.07mm); `gen_plate.py` now derives the RIGHT tab
  roots from the LEFT roots and re-projects them onto the right rim
  (output-side mirror check included), so the plate tabs are exact
  mirrors. New gates: `check_board.py --self-test` mirrors board+plate
  (0.0000 / 0.0100mm); `case/mirror_gate.py` mirrors the STEP tub/cover
  (0.0094 / 0.0000mm), floor 0.05mm, with 0.5mm negative controls.
  Volumes unchanged: tub 75.7/75.7 cm³, cover 10.7/10.7 cm³.

- v3.6 (2026-10-20, six-review design audit round): **magnet stations are
  now SYMMETRIC-BY-CONSTRUCTION** — `magnet_stations()` computes the LEFT
  set once and mirrors it (`x -> 291.5 - x`) for Right, re-validating
  every mirrored station against the right boundaries/obstructions/
  antenna (asymmetric rejection aborts the build). Root cause of the
  6/7 drift was the per-half slot walk, not real geometry. **Geometry
  margins raised to the reviewer floors**: CASE_OUTSET 7.1 -> 8.2
  (wall 1.595 -> 2.62/2.70 — clears the MJF-2.0 pass and the 1.6 design
  floor), MAG_STATION_BAND 6.6 -> 7.5 (webs 1.15 -> 1.69), MAG_MIN_STATIONS
  6 -> 8 (the doc chain's 8/half is now BUILT truth — Left had been ON
  the 1.5 kg pull-test floor at 6/7). Census: tub 75.7/75.7 cm³ (within
  the widened [55,82] tripwire), stations 8/8 exact mirrors (the
  STATION SET is exactly mirrored; the tub outlines are not — the polygon
  offsetting leaves wall_min 2.62 L vs 2.70 R, inside every floor), band min
  7.68, web 1.69, ant margin 14.15 in-plane + 5.60 floor standoff
  (both now printed as a `census antenna` line), ports out
  20.20/10.70/10.70. Cover: 10.7/10.7 cm³ ([6,13] tripwire), ring
  wall census gate raised 1.40 -> 5.0 (7.20 measured; full-point
  sampling now, both tub and cover — the old every-2nd-point walk
  carried a claimed ≤0.03 sag that no longer has to be trusted).
  Plate: PORON_PAD_L 8.0 -> 7.0 (corner-edge 0.35 -> 0.71 measured,
  kerf-fragility closed), port keep-rects mirror-derived from the Left
  literals (usb/trrs carried a +0.5 drafting drift; webs now 5.62 both
  halves), encoder-hole corner maths documented (0.145 mm relief).
  PCB gates grown in check_board.py: pad+via containment, antenna
  keepout at commit level, TRRS crossover pin-map, W1 pad-content
  equality vs vendored stock, silk-to-edge clearance — all CLEAN on
  both halves.


- v3.5 (user "implement" round: pwrsw + magnets + ring cover): **PWR
  actuator aperture** — the WS-SLTV sits wholly inside the cavity, so
  the wall question was really a mouth: a 5.0-wide slot, z 4.3..top
  with 0.8mm fillets, through the north rim plateau. The plateau is the
  raw Edge.Cuts line y=58.0 (x 97.5..110.5, mirror 181..194), so the
  port frame is EXACT axis-aligned — no resample-phase wobble (a
  wobbling anchor x put the slot 0.87 from tab-4's pocket; the SAT gate
  caught it, and mouth centre 106.3/185.2 clears the pocket ≥3.2 and
  the USB mouth ~1.8). **Retention: recessed magnets** —
  `magnet_stations()` picks 8 per half on the band top face: local band
  ≥6.4 (≥1.1 webs both sides, re-checked against the true boundaries),
  ≥5.1 from every port/pocket rect via a rect-aware distance
  (`rect_d` — edge-distance alone read a deep-inside point as "far"
  and parked a phantom station inside the USB notch void; the pocket
  web probes caught it), antenna ≥10.1, spacing ≥14, slots snapped at
  perimeter/8 with both rings rotated to the USB anchor for mirror
  symmetry. Ø4.2×2.2 pockets, faces flush at the lip plane. **Ring
  cover v1** (`gen_cover.py`): flush ring z 4.70..7.70 reusing the tub's
  helpers verbatim — W1 full-depth (the plug's overmold pokes ~0.2 past the top; the module
  tops 7.7, below the ring),
  TRRS = the same Ø9.5 cylinder as a BLIND tunnel in the 4.70..7.70 slice
  (tops 7.25 > boot swing 6.75; chord ≤4.82, ring NOT split), pwrsw
  full-depth but keeping a 1.1 inner web (W1 stays the only radial
  severance → single solid; hard-won: hand-placed ring-resume
  coordinates were wrong for the wider bite outline, replaced by a
  port-agnostic skin-hug battery). New per-port census print every
  build (housing/boot/lever margins, breach, SAT) + magnet band/ant
  line. Measured: tub 68.0/68.0 cm³ (magnets+pwrsw −0.3), cover
  7.7/7.7 cm³, wall_min 1.49/1.50, webs 1.25/1.15, magnet band min
  6.48/6.49, stations mirrored 1.29mm (measured). [HISTORICAL — the
  v3.5 review round 2 below re-measured: tub 67.4 (B1 pillar fix),
  cover 9.0 (T4 pockets), census wall 5.85.] `probe_bores.py` gained a
  7-probe pwrsw group per half (below/flank/fillet/wall-resumed/top/
  sills).

- v3.5 round 3 (post-PCB-audit P0 batch, first-contact fail): **magnet
  policy matches the physical band** — the P0 policy (pocket Ø4.3,
  ≥1.15 webs, band 6.6) ran against a **6.5 physical band**
  (CASE_OUTSET 7.0 − RIM_CLEAR 0.5): the `d ≥ MAG_STATION_BAND` filter
  zeroed every ring candidate except the notch pocket, which the USB
  slot rect kills — "none eligible", both tubs AND the cover (it
  reuses `G.magnet_stations`). `opencode/probe_mags.py` (per-filter
  rejection census; dmax 13.2 at the notch) split the two failure
  layers and closed the 0.1 gap with the minimal raise: **CASE_OUTSET
  7.0 → 7.1**, band = 6.6 exactly. Census: wall_min 1.60 (tab tips
  were 1.49-1.50), web min 1.15, band min 6.60, stations 6 (L) / 7 (R)
  mirrored, volume 68.1/68.2; cover wall_min 5.94, web 1.15, stations
  6/7. Plate-side in the same batch: the USB-plug bay's notch-floor
  scan was rewritten onto the config usb anchor (band-min picked the
  west-edge outline points, x∈[-0.64,0.35] instead of the mouth); all
  plate gates CLEAN after.

- v3.5 review round (user solo review, findings A–F): **the ring now
  bridges the tabs** — v1 cut its interior from the plate outline,
  which left a tab-shaped bite over every tab pocket so the top poron
  pads pressed NOTHING (reviewer probed pad centres void at z 6.2/7.5).
  The interior is the PCB rim + 0.5 now: the ring presses all 8 top
  pads at the designed 16.7% (new tab-pad press gate fails in the
  bite state; the 0..0.5mm pad-root sliver stays unpressed). Encoder
  hole 12.5 → 12.7 (the vendored EC11 body measures 12.30 wide in the
  plate band → 0.20/side; plates re-gated CLEAN). Wording batch:
  TRRS mouths documented RECESSED 0.99 (drop-in is even easier than
  claimed — the jack never crosses the band), USB socket stack 4.5 /
  module 4.5..7.7, notch depth 6.3–10.3 local, slot sill vs module
  poke wording, `PWRSW_COVER_IN = 1.6` replaces the derived t_web,
  magnet mirror documented 1.29, print-orientation note. Measured
  after: cover 8.9/8.9 cm³, census wall_min 5.85, stations unchanged.

- v3.5 review round 2 (multi-model sweep, 2026-10-18): **B1 blocker
  fixed** — the tab pillar fuse reached 1.0mm inboard of the rim,
  putting solid case material under the PCB at all 8 stations (board
  would rest ~1.05mm high, bottom pads unloaded); the pillar now starts
  0.3 outboard of the rim (the shelf under the tab tongue survives —
  my first attempt deleted the fuse entirely and the gates caught it:
  the tab lobes are cavity, the fuse IS the shelf). New footprint-
  clear gates (per-tab + plan-wide rim sweep). **T4**: cover magnets
  Ø4×1.5 (16 pcs), pocket depth 1.7, floor 0.8 → 1.3mm; pull test
  ≥1.5 kg added to first-article. **M2**: pwrsw footprint shifted 2mm
  west (ergogen) so the blade band sits under the fixed mouth window;
  Left stub endpoints moved, Right's 31 stale hand-routed pwrsw items
  deleted (router re-routes fresh); the router now seeds its obstacle
  model with preserved GUI copper at exact clearance and the copper
  checker sees the merged board (both DRC-clean, W1-only). **M1**:
  floor derivation rewritten to the measured below-PCB ruler (encoder
  legs −3.65 from the vendored STEP — deepest — FLOOR_Z −5.6 keeps
  ~1.95mm; sockets are top-side, they never provisioned the floor).
  **M6/M7/M8**: gen_cover in CI, stack-ties check, pwrsw in plate tab
  eligibility (DXFs byte-identical), encoder web print (cutouts 9.15 /
  windows 3.65 / ports 4.92–5.35). Choc 15.0 kept with honest
  clip-never-engage wording; LOW doc cluster done. Measured after:
  tub 67.4/67.4 cm³, cover 9.0/9.0 cm³, wall_min 1.49/1.50 (tub) /
  5.85 (cover census), stations unchanged.

- v3.4 (user review round): **ports became shaped bores** — the
  v3.2-3.3 wall slots cut the FULL wall band (14×11.6 USB / 9.5×11.6
  TRRS rectangles the user rightly called "big gaping"). v3.4 sizes
  each mouth to the plug's z band instead (params.py carries the stack
  reasoning): **USB = 14.0-wide slot with 1.2mm bottom fillets spanning
  z 2.0..top** (plug axis rides at the lip plane — overmold bottom
  ~2.8; the neck above the lip exits through the open top, which is
  the cover's duty), **TRRS = Ø9.5 round bore on the jack-axis estimate
  z 2.4** (the v3.4 estimate; the vendored STEP later measured the
  mouth-face centre vertex at z **2.5** — the v3.5 bores use 2.5;
  the ≤8.5 ball swings freely inside, margins hold for ±0.5mm
  axis drift, clipped flat by the lip only where it passes the top).
  Measured breach unchanged (the march is z-independent): usb out=19.00,
  trrs out=9.50. Material returns: volumes 66.7/66.8 → **68.3 cm³**
  both halves; wall_min 1.49/1.50 and pocket webs 1.25/1.15 unchanged.
  `check_half` gates re-dereded to bore geometry (bore-aware skin-band
  classification, mouth probes at 0.9 half-width across two in-bore
  z planes, air beyond per plane, SAT bounding-rect proof); new
  `case/probe_bores.py` throws an offline shape audit (fillet envelope,
  full-width top, circle edges, extreme-z chords, sill). **Antenna
  window: none, by measurement** — 14.15mm of air to the nearest
  material beats the 3mm rule with margin; a window would only matter
  if a future cover passed closer than 3mm, which the contract
  forbids.
- v3.3 (comprehensive-review fix round): **port slots measured-breach** —
  the v3.2 fixed `SLOT_OUT = 8.5` capped the USB opening under the
  skin the dilated rim BRIDGES across the notch (the skin envelope
  rides ~17mm north of the rim there, so both halves shipped with the
  USB sealed shut). The slot face now marches outward until every point
  across its width clears the skin ring (+1.0mm travel; printed
  `out=19.00` USB / `9.50` TRRS), and the gate battery re-proves the
  breach on the finished solid: mouth probes across the whole face at
  two z planes, air beyond the face, slab under each slot solid. The
  16mm port mask on the wall census is gone (band probes now flip to
  expect-void inside a slot rect — the mask hid the open face). New
  gates: single-solid topology, SAT slot-vs-pocket separation ≥ 3mm
  (corner-containment was unsound), antenna envelope rings (24
  azimuths × 3 radii × 4 z) replacing stray compass points, and
  printed wall web metrics (`wall_min`, `pocket_web_min`).
- v3.2 (strength + ports + antenna, user review round): **CASE_OUTSET
  6.0 → 7.0** — the wall over every tab tip measured exactly 0.5 (skin
  vs tab tip + RIM_CLEAR), 1-2 FDM extrusion lines at 8 stations, the
  "concerningly thin" sections the user flagged. Census now: wall min
  1.49-1.50 at all tab stations (gate ≥ 1.40), 6.50 typical, printed
  every run. **Port slots re-z'd** — v3.1's cut ran from the case
  bottom and punched two through-holes in the floor slab at the anchors
  (the "hole in the bottom" the user found); slots now open the wall
  from FLOOR_Z (slab top) to the lip, sill intact. **TRRS slot 12 → 9.5**
  (molds the 90° boot, bore-side ≤ 8.5, not the jack body) — first
  article measures the real boot. **Antenna**: "no case material within
  3mm" (electronics.yaml) bounded by ring distance gates at the module
  points (118/173.5, 15.55); the wall runs ≥14.15mm away (nearest
  material = the cavity edge at rim+0.5), so no antenna opening exists
  or is required in the tub — the duty moves to the future top cover.
- v3.1 (bulges fixed): the exterior dilates the PCB RIM, not the plate
  outline — the tabs are spliced INTO the plate outline, so dilating it
  gave the case eight 5mm bulges. Rim dilation keeps the wall uniform
  (measured: skin-to-rim max exactly 6.0, ~1.0 cover over every tab
  tip). Port slots re-anchored on the rim and span the full wall band
  (v3's were silent no-ops — battery passed by probing outside the
  case). Pocket noses adaptive per tab (5.5 nominal, floor TAB_L+0.2)
  where rim curvature eats the corner web.
- v3: uniform 6.0mm dilation of the plate outline — superseded by v3.1
  (dilating the tabbed outline bulged at every tab).
- v2: per-tab smooth swells — superseded (walls varied in thickness;
  uniform dilation is the reference-case answer). v1: stepped walls +
  bosses — superseded (jutting pockets, layer lines).
- Verify: `case/.venv/bin/python case/gen_case.py`, then `gen_cover.py`
  and `probe_bores.py` the same way (exit 0 = all gates; probe_bores
  rebuilds the halves offline).
  Inspect in FreeCAD when available; Blender for renders (not installed).

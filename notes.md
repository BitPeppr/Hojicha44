# Hojicha44 — review notes

PCB-readiness review of the schematic + layout, and the state of the fixes.
Written 2026-10-12 (UTC date 2026-10-13). Regenerate sources, not outputs:
`python3 pcb/generators/gen_schematic.py`.

## Verdict

The electrical design is sound. The schematic went to two PCB files after
three fixes, two of which would have produced dead boards on first spin.
Remaining work is layout, not schematic.

## Verified correct

Checked against an exported netlist, pin by pin, not just ERC.

| Item | Result |
|---|---|
| Matrix topology | `COL → SW.1 → SW.2 → D.A → D.K → ROW` — genuine COL2ROW (`Diode:1N4001` pin 1 = K) |
| Net counts | ROW0‑2 = 7 pins, ROW3 = 5, COL0‑3 = 5, COL4/5 = 4 — as designed |
| Battery path | JST.1 → SPDT common (2) → throw (1) → VBAT_SW → MCU RAW; correct nice!nano input |
| Split cable | Straight-cable crossover intact on both boards: left `D1→TRRS_T`, right `D1→TRRS_R1` |
| Ring 2 | Genuinely unconnected — avoids joining both LiPos into the charger MOSFETs |
| Half interconnects | GND shared; **VCC3V3 and RAW never joined between halves** |
| Encoder | A/B → A0/A1, push → D16 dedicated GPIO, C+S2 → GND |
| ERC | 0 errors / 5 warnings per half; all warnings are the intentional single-pin spares (RST, VCC3V3, A3, A2, D10) |
| nRF mapping | Matches the official nice!nano v2 pinout diagram |
| Silkscreen names | `RAW,GND,RST,VCC,P0.31…P0.09` and `P0.06,P0.08,GND,GND,P0.17…P1.06` match the module exactly, including all 3 GND positions |
| Footprints | All referenced footprints exist in stock KiCad 10.0.6 |

## Fixes applied

### B1 — nice!nano pin numbering (blocker)

**Bug.** The footprint numbered pads 1 and 13 at the same end. The Pro Micro
/ nice!nano convention pairs **1 (D1) and 24 (RAW)** at the USB end, and
**12 (D9) / 13 (D10)** at the antenna end.

Consequence had it shipped: pin 2 (GND) would land on the module's D1 pad,
and pin 13 (D1) on the RAW edge's 7th pad (P0.29/A2). Half the MCU scrambled;
dead board at first power-up. ERC and DRC cannot catch this — netlists
connect by pin *number*, so everything looks correct.

**Evidence** (three independent sources, all agreeing):

- `keebio/fourier` `ProMicro-promicro` symbol: pin 1 = `TX0/PD3`, pin 24 = `RAW`
- `keebio/Keebio-Parts.pretty` `ArduinoProMicro.kicad_mod`: pad 1 at
  `(-13.97, 7.62)`, pad 24 at `(-13.97, -7.62)` — same end
- `raeedcho/temper` `nice_nano` symbol: pin 1 = `D1/P0.06`, pin 24 = `BATTERY+/RAW`

**Fix.** Reversed the second column of
`Hojicha44.pretty/Socket_Strips_2x12_P2.54mm_NiceNano` and re-keyed the
symbol in `gen_schematic.py`:

```
pads 1-12   TX/D1 edge : D1, D0, GND, GND, D2..D9
pads 13-24  RAW edge   : D10, D16, D14, D15, A0, A1, A2, A3, VCC, RST, GND, RAW
```

`check_mcu_footprint()` now asserts the pad map *and* the pin→function list on
every build, so a re-numbered symbol cannot drift silently.

Also: the stock `Connector_PinSocket_2.54mm:PinSocket_2x12_P2.54mm_Vertical` is
row-major (serpentine 1,2 / 3,4 …). Never substitute it — this is the whole
reason the project-local socket exists.

### B2 — encoder knock-through (blocker)

**Bug.** `outlines.board` subtracted a 16mm circle at each encoder point,
putting a hole in the *PCB*. The EC11E footprint's shaft centre sits at
(7.5, 2.5) and **all seven of its pads fall within 5.6–7.9mm of that centre** —
inside an 8mm radius. A 16mm hole deletes every pad's copper: A/B/C
(quadrature), S1/S2 (push) and both MP mounting lugs. The encoder would drop
into the hole with nothing to solder to.

**Options considered:**

| Option | Result |
|---|---|
| **Hole in plate/case only** ✅ chosen | EC11E body rests on the PCB, all 7 pads on copper; knob passes through the plate |
| Shrink the PCB cutout | Knob clears, but the body has no support — the case must hold it |
| Keep the hole, redesign pads | Needs a new footprint/pad ring; more work, same outcome |

**Fix.** `board.dxf` now has **0** circles; a new `plate.dxf` carries both
16mm cutouts. `spec/layout.yaml` corrected to say the cutout lives in `plate`.

### B3 — two PCB files

**Decision:** one KiCad project per half. A split keyboard is two boards, and
a single flat sheet produces one netlist — "Update PCB from schematic" would
have dropped both halves into one board file.

Now: `Hojicha44-Left.*` and `Hojicha44-Right.*`, each with its own
`.kicad_sch`, `.kicad_pro`, `.kicad_pcb` and ERC report, sharing the vendored
symbol/footprint libraries. The half-to-half link (the TRRS crossover) lives
in the spec, not in either netlist. A guard rejects foreign refs, so one
half's sheet can never carry the other's components.

(SUPERSEDED — crossover is copper, both overlays share TX/RX) The halves differ **only** in the TX/RX swap, which is the cost of a straight
cable — the right half's ZMK overlay must swap `tx-pin`/`rx-pin`.

### Also fixed

- **`SW_LPWR` refdes.** KiCad treats a reference not ending in a digit as
  un-annotated, so every netlist/PCB export warned "schematic has annotation
  errors" despite clean ERC. Renamed to `SW_LPWR1`; `place()` now asserts
  every refdes ends in a digit.
- **`POWER` netclass** (0.5mm tracks) auto-assigned to `VBAT_SW_*` by pattern.
- 1.6mm 2-layer stackup; track/via presets corrected (the KiCad template ships
  0-width/0-drill values that silently break DRC).
- Regenerated schematic PDFs/SVGs per half in `pcb/kicad/export/`.

## Open before routing

1. **Module orientation** — the one check that cannot be automated: place the
   socket so the **pin-1/USB end faces the module's USB end** (open board
   edge). Verified only against datasheet images so far; confirm against a
   physical module or a second community footprint.
2. **Antenna keepout** — 5mm copper-free zone at the module's south (antenna)
   end, no case material within 3mm. The `antenna` point and `antenna_keepout`
   outline mark it in the layout.
3. ~~**USB notch** — 11×5.4mm at each `usb` point; the module's USB shell must
   overhang that edge.~~ [CLOSED — contradicted by fixed specs: shell sits ~9mm inboard, notch alone seats the plug.]
4. ~~**Diode placement.** The Choc hotswap courtyard is ±7.75mm but **pad 2 sits
   at x=8.5**, outside it. A SOD-123 centred 7.62mm to the right (where the
   schematic draws it) trips courtyard overlap. All 44 diodes go in the 3.55mm
   inter-key gaps, rotated 90°.~~ [CLOSED — answered: DIODE_CLEAR gate.]
5. ~~**Cell choice.** The layout config moved to a 301230 (3×12×30) — note the
   spec still describes a 302030 (20mm wide, wider than the 18mm module).
   Reconcile the two before ordering cells.~~ [CLOSED — answered: 302030 rejected, 301230 locked.]
6. ~~**`decisions/` and `experiments/proposed/` are empty** — the roadmap's
   Phase 0/1 artefacts were never written down.~~ [CLOSED — dirs don't exist in repo.]

## Fabrication gates

From `spec/electronics.yaml` (`pcb_gates`), all must hold before Gerber export:

- JST-PH gets a `+` silkscreen mark at pin 1 (reverse polarity kills board and cell)
- diode polarity readable after placement (SOD-123 cathode band)
- 3× fiducials + tooling holes for SMD diode assembly
- Choc socket (bottom) vs SOD-123 keepout checked — no courtyard overlap
- TRRS T/R1/S continuity against the PJ-320A datasheet terminals 2‑5
- hotswap socket footprint pads sit on B.Cu as vendored: place the footprint
  **flipped** so the socket body faces the board's top side
- WS-SLTV: confirm pad 2 (centre) is the SPST common against the Würth
  drawing; the symbol assumes 2 = common, 1 = rail
- each half's board outline is the `board` outline, **not** `plate`

## Useful commands

```sh
python3 pcb/generators/gen_schematic.py   # spec check + both sheets + guards + audit + ERC
node layout/generators/dump_points.cjs    # ergogen point/YAML sidecars
```

`kicad-cli` is not on `PATH`; the generator finds it inside the KiCad bundle
(`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, v10.0.6).

Current output: 53 symbols / 101 wires / 22 nets / 82 pins per half, ERC
0 errors, DRC clean apart from the expected `invalid_outline` on the blank
boards.

## Placement pass (2026-10-13): review blockers closed

An external review raised four blockers. All four verified independently
before fixing — including one where the earlier review was wrong.

### 1. Socket row spacing — CONFIRMED, real blocker, fixed

The custom socket had its two pad columns 2.54mm apart. A Pro Micro module
needs **15.24mm**. The earlier guard even enforced the wrong value
(`column pitch != 2.54mm`), locking the bug in — along-row pitch (2.54) had
been conflated with row separation (15.24).

Geometry now rests on three legs: the official nice!nano v2 pinout image
(pad pitch 18.5px ⇒ 2.54mm/pitch, board bbox 18.3 × 34.9mm ⇒ column gap
15.65mm ≈ 15.24), keebio's `ArduinoProMicro.kicad_mod` (15.24), and the
12mm 301230 cell fitting *between* 15.24mm rows. `raeedcho/temper` agrees
on pin *numbering* but its 9.4mm spacing is a custom solder-jumper mod —
NOT a mechanical reference.

Fix: second column `x=-2.54` → `-15.24`, silk/Fab/courtyard redrawn to the
true envelope, reference designators re-centred (`-7.62`). Guard rewritten
to four independent assertions: along-row pitch 2.54, row separation 15.24,
24 pads in two columns with 1/24 sharing the USB end, envelope containment.
`_mcu` rect enlarged 18×33 → 18.3×34.9 with the USB/antenna points
re-derived (USB +0.5 past the north edge, antenna 1mm inside the south).

### 2. Placed PCBs — done via `pcb/generators/gen_pcb.py`

Both boards now carry 52 footprints / 48 nets each (22 switches + 22 diodes
+ MCU + encoder + TRRS + JST + PWR + 3 fiducials), outline from
`board.dxf` (arcs segmented, loop-closure asserted), nets straight from the
per-half netlist export. Unrouted — tracks/vias are the next phase.

Right half uses the already-mirrored `mirror_*` coordinates with the SAME
layers and mirrored rotations — no footprint flipping (flipping would swap
F.Cu/B.Cu and put sockets on top). Per the build: components stay on their
sides, only positions/rotations mirror.

New guards that DRC cannot provide:
- **Pad containment**: every numbered pad inside its outline (would have
  caught the TRRS mouth-end pads going off-board — DRC is silent there).
- **DRC gate with documented waivers**: W1 `lib_footprint_mismatch` on
  rotated parts (KiCad-version quirk: proven — identical footprint clean at
  rot 0, flagged at 90/180; the stock template board flags it too), W2
  Choc B.SilkS-vs-own-pad-2 vendor marginality (proven angle-dependent:
  lone footprint clean at +13.5, flagged at −13.5 with rigid geometry).
  Everything else fails the build. `gen_schematic.py` never clobbers a
  placed board.

### 3. Switch side — resolved, documentation fix

Sockets solder beneath, switches on top — the as-vendored orientation
(B.Cu pads + B.Fab/B.SilkS body) is correct; the "place FLIPPED" gate
instruction was self-contradictory and is gone. Diodes SMD on the front,
clear of the bottom-side socket courtyard (DRC courtyard clean).

### 4. Remaining gates — status

- Power-switch MPN locked: Wuerth WS-SLTV 450301014042 (matches footprint);
  still confirm pad 2 = common against the Würth drawing.
- Encoder stays provisional (H20mm bushing tall for a Choc case — confirm
  knob height) with correct placement (shaft on the anchor, all 7 pads on
  copper).
- Battery: 12mm 301230 fits between the 15.24mm rows with 1.6mm/side;
  socket stack height still TBD before routing.
- TRRS: repositioned 2mm inboard — mouth-end T/S pads back on copper with
  0.5mm edge margin; mouths ~22.4mm apart, 90° plugs fit easily.
- JST `+` silk added at pin 1; antenna keepout marked (no pours yet, so
  trivially satisfied); USB notch clears the socket silk by 0.45mm.
- Firmware: pin map still candidate — needs the ZMK overlay draft
  (`uart0` tx/rx crossover for the straight cable, `nfct-pins-as-gpios`
  for D10/D16, `diode-direction=col2row`). Nothing left to verify without it.

## PCB-design start (2026-10-13): fab blockers closed, copper ownership fixed

Both blockers from the review + `fix.md` (untracked, not in repo) are applied, regenerated and
re-measured on the regenerated files, not on the analysis copies.

| Fix | Evidence it now holds |
|---|---|
| **USB notch (P0-1)** | `board.dxf` is **1** closed loop per half (was 2: outer ring + enclosed notch). At `x = usb` the board tops out at **y 47.25** while the board's max y is 60.00 — a 12.75mm deep, 11mm wide open notch. Config: `size [11, 10.8]`, `shift [0, 2.7]`; floor stays 0.93mm above the top socket pad copper. |
| **Fiducials (P0-2)** | 3 per half, all `inside=True`, edge distances 3.03–3.48mm. `pick_fiducials()` searches 1mm grid points inside the loop, ≥3mm from any edge segment and ≥3mm from any placed pad, snapped to three targets (outer top-left, outer top-right, bottom centre). The old bbox-corner rule put all 6 off the board. |
| **`+` silk mark (P1-1)** | '+' glyph box is 0.86mm clear of the nearest JST silk segment; DRC reports no `silk_overlap`/`silk_over_copper` on `J_L2`/`J_R2` (the only silk items are the 2 W2 switch ones). |
| **Regeneration** | `npx ergogen` → `dump_points.cjs` → `export_kle.py --check` → `gen_schematic.py` (53 symbols, 22 nets, ERC clean) → `gen_pcb.py` (52 footprints, 48 nets, containment 49/49) all exit 0. DRC: 79 unconnected (pre-routing), 28 W1, 2 W2 — no non-waived item. |

### Copper ownership — gen_pcb.py was deleting routed tracks

Proven before it could bite: a fake `(segment ...)` injected into a sandbox copy
did **not** survive `build_board()`. `gen_pcb.py` rebuilt the entire board body
from `head + gfx + body`, so the normal pre-routing workflow (regenerate to
change placement) would silently erase any copper routed in the GUI.

Fixed — ownership is now explicit: the generator owns outline, footprints, nets
and placement; a **human or router owns copper**.

- `extract_copper()` pulls `(segment …)`, `(via …)` and `(zone …)` out of the
existing board verbatim and appends them back after the regenerated body.
- Net codes are **remapped by name**, because codes are assigned per netlist
export and are not stable. A preserved net the schematic no longer has is a hard
error rather than a silent renumber onto the wrong copper.
- `check_copper()` fails the build when preserved copper no longer attaches: a
track end must land on a pad, a via, or another track end of the same net, and
no track or via may enter the **r=5mm antenna keepout**. This matters because a
footprint move that strands old tracks is otherwise invisible — KiCad reports it
only as one more `unconnected_items`, which is exactly what the pre-routing DRC
waiver already covers.

Sandbox tests (project files untouched): dangling track → rejected; track
crossing the antenna keepout → rejected; via in the keepout → rejected; genuine
GND pad-to-pad track → build OK and preserved.

### Still open before copper

- The routing decisions in `fix.md` (untracked, not in repo) §8 (layers, TRRS vs 4-pin JST).
- `notes.md` "Open before routing" items 1, 4 and 5 (module orientation against
a physical module, cell 301230 vs the spec's 302030, socket stack height).

### Toolchain findings this pass

- KiCad footprint rotation is CLOCKWISE-positive (proven: TRRS at rot 270
  maps local (−2.3,11.3) to global offset (−11.3,−2.3) = CW270). Ergogen r
  is CCW-positive (makerjs). Same visual needs KiCad rot = −ergogen r —
  every rotated footprint was mirroring until this was caught via DRC
  coordinates. `krot()` in `gen_pcb.py` encodes the rule.
- Ergogen emits zero-span fillet dots (span ~1e-7°) at tangent joints —
  skip them or loop-closure counting breaks.
- Some stock/vendored silk sits 0.05–0.3mm over pads (TRRS verticals,
  SOD-123 cathode bar at odd angles): shave or strip, don't ignore — the
  classes also catch real errors.
- `notes.md` is tracked-able (not ignored) ✓

## Toolchain gotchas hit during this review

- `kicad-cli fp export svg` needs its **output directory to exist** first, and
  fails with a bare "Unable to load library" on a malformed footprint — no
  line number. Useful as a parser check, but the error message is useless.
- Ergogen 4.2.1 writes only DXF (plus SVG with `--svg`); the `points.yaml` /
  `source/canonical.yaml` sidecars older versions emitted are gone.
  `dump_points.cjs` restores them.
- Ergogen hoists `expand`/`fillet` to **every** item in an outline group, so
  the two mirrored halves come out identical even though only the second
  declares them. Verified by removing the keys and diffing the DXF.
- `layout/generated/` is gitignored, so `--clean` destroys outputs with no
  history. Regenerate rather than hand-edit.
## Close-out pass (2026-10-13): option D

### Switch common — was WIRED WRONG, now fixed and guarded

Research (Würth 450301014042 datasheet: front view 2-1-3, schematic marks 1
as COM) proves **pin 1 (middle) = COMMON**, pins 2/3 = throws. The schematic
had battery→pin 2→footprint-pad-2 (an outer throw): the rail would float in
one slider position. Fix: battery→pin 1, rail→pin 2, pin 3 NC — verified in
the netlist (`J_L2.1+SW_LPWR1.1` anon, `VBAT_SW = SW_LPWR1.2 + MCU RAW`). New
`check_pwr_footprint()` asserts pad 1 is the middle pad against library
drift; status promoted to fixed. First-article check left: which slider end
is ON (either works as on/off, just swapped).

### Encoder — locked, not shrunk

Shortest stock EC11E vertical-switch part is 20mm shaft (tip 24.5mm);
no shorter EC11E-switch exists and KiCad stocks only H20mm. Locked
**EC11E15244G1** (30/15, 0.5mm travel), footprint unchanged, knob ~10mm
proud documented as normal-with-fallback (trim shaft). Bourns 15mm
alternative recorded with its tab-span caveat, not taken.

### Socket stack — recorded, not measured

4.5mm round machine-pin (or 5.0mm PBS) recommended, 8.5mm Sullins fallback,
Mill-Max 2.11mm banned for the 301230 (3.5mm min, 4.5–5 comfortable with
PCM/wires). JST fits neither under the stack — sits beside the cell, as
placed. B+/B- holes stay open (power via RAW). Physical dry-fit still
wanted before ordering headers.

### Firmware — draft written, compile pending

`zmk/`: shared `.dtsi` (kscan col2row, transform, encoder, gpio-keys push,
vbatt, uicr), per-half overlays, minimal keymap, conf, and a
machine-generated `gpio-map.md` (all 24 pins both halves vs netlist).
Research corrected three stale assumptions: no `&a0`/`resolution` (use
`steps`), no `chosen zmk,split-uart` (use `wired_split` + pinctrl
`NRF_PSEL`), no `CONFIG_NFCT_PINS_AS_GPIOS` (use `&uicr`,
needs full chip erase on first flash). (2026-10-16: wired-split since
removed — BLE-only split, TRRS debug-only; the `wired_split` research above
is superseded, UART pinctrl kept for debug.) Bigger correction: **no TX/RX
firmware swap exists** — the copper crossover already routes correctly, so
both halves share identical UART pinctrl; the old "must swap" claim is
struck from README/spec. `pin_map` promoted to fixed. `west build`
verification + keymap content (layers, Backspace/Delete, combos) remain —
that needs a toolchain and product decisions, not more review.

### Tooling holes

Fiducials (3/half) placed; tooling holes belong in panel rails at fab, not
in the gasket-clamped board — documented, nothing to draw.

Nothing verifiable-without-parts-or-toolchain remains open.

## fig.md cross-check (2026-10-13, later review)

A second review (`fix.md`, untracked/not in repo) was verified item by item against the
current files. Where it disagrees with these notes, the files decide:

- P0-1 USB notch "enclosed hole": NOT PRESENT. Loop-traced the outline —
  single closed loop per half, contour runs top edge → down the west wall
  (112.50,57.53)→(112.50,47.25) → across the notch bottom → up the east
  wall → back to the edge. Open bite, correct.
- P0-5 battery citation: fixed properly. Official Getting Started blesses
  RAW/GND as B+/B- equivalents AND forbids socketing B+/B- — our 2x12
  socket + RAW feed matches the official procedure exactly (also corroborated
  by bstiQ build docs and direct-connection measurements). Spec cites it now.
- P1-4 mismatch: kept as documented waiver W1 (proven environmental), not
  "fixed" — pre-rotating geometry would guarantee mismatch instead.
- P1-5 tooling: implemented (2x 3.2mm NPTH, clearance-searched) rather than
  panel-rails — the pickers verify edge/pad/courtyard clearance every build.
  Two real bugs caught during implementation: NPTH pads were invisible to
  clearance (drilled 1.5mm from a switch hole), and courtyard interiors pass
  segment-distance checks (hole placed inside a courtyard). Both fixed.
- P1-6 ERC warnings: kept as warnings, deliberately. The 5 single-pin spares
  stay labeled (future use + UICR); no-connects would hide intent.
- P2-4 reset button: declined by decision — initial flash via factory UF2
  over USB, later via ZMK bootloader behavior; no button keeps the gasket
  seal and the pin count. RST is on socket pin 22 if a pogo is ever needed.
- Open decisions carried forward, not closed here: keymap content,
  TRRS-as-daily-link (documented fallback only), ergonomics (frozen layout
  stands). Routing closed below (was "tracks still to draw").

## Routing pass (2026-10-13): deterministic 2-layer router, DRC-clean

`pcb/generators/gen_route.py` (dual-layer A*, 0.25mm grid, exact per-class
clearance + 0.15 quantization margin, POWER 0.5/signal 0.25) routes both
halves; `gen_pcb.py` emits the copper revision-tagged (`placed+routed r10`)
and preserves GUI copper by normalized dedupe. Order: anode links (22/half,
short local) → COL rails (matrix chained, thumb+MCU tapped) → ROW rails →
stubs (ENC/TRRS/VBAT) → GND chain. Single pass, no rip-up (bounded retry
oscillated: stubs↔rails ripped each other).

Final: Left 54 fp / 48 nets / 111 edge segs / 455 copper items (the
"446" originally written here predated the last copper pass — it no
longer reproduced. Re-measured 2026-10-23 on the committed board:
384 `(segment` + 71 `(via` = 455; the identical metric reproduces
Right's 590 = 490+100), Right
54 / 48 / 117 / 590 (router r13). `unconnected_items` = 0 both halves.
DRC shows ONLY the documented waiver W1 (28× `lib_footprint_mismatch`) —
0 non-waived (W2 retired by the Choc silk trim: 0 silk items either half),
`gen_pcb.py` exits 0, rerun-stable (dedupe keeps 0/0).
`gen_schematic.py` (ERC 0 errors) and `audit_silk.py` (symmetric OK) green.

Bugs found by routing and fixed (all proven on the failing coordinates):
- TOOL holes missing from the obstacle model (`Board` skipped TOOL
  placements) — GND poured through MT_L2 (4× hole_clearance). Fix: 3.2mm
  NPTH discs in `board.holes`.
- Own-pad carve smaller than own-pad block left a 1-cell clearance sliver
  sealing every THT MCU pin (flood from U_L1.11 reached 144 cells). Fix:
  carve the full blocked rect; overlap with neighbour zones is harmless.
- Via ring scan (121 cells/expansion) made search 80s+ and sealed dense
  zones; centre+4-neighbour check is 5× faster with DRC-identical results.
- MCU pin interleaved in rail sort forced 100mm+ jumps (A* cap). Fix:
  rail the matrix, tap the MCU pin to nearest copper.
- `normalize()` never stripped emit's leading tab, so dedupe matched 0/408
  and the first same-rev rerun doubled the copper (816 items, checker
  rejected the ghosts). Fix: `strip()`; verified stable on rerun.
- A* goal projections on copper leave buried 0.13mm trailing overshoots
  (ROW1_L `track_dangling`). Fix: trim buried trailing micro-steps +
  drop fully-buried short runs; pad endpoints never trimmed.

Remaining (need parts/toolchain, not review): physical module checks
(header dry-fit, ON-position, plug seating, RAW↔B+ DMM), `west build`,
keymap content.

## Release-review responses (2026-10-13, second agent's six items)

1. **SW_R19 silk (Right) — removed, waiver retired.** The two
   `silk_over_copper` errors were Choc B.SilkS corners grazing own pad 2
   (marginal local gaps 0.07–0.19mm, flagging only at some rotations).
   Fix: pulled all five sub-0.3mm B.SilkS corners to ≥0.49mm local
   clearance in the vendored footprint (rotation preserves local distance,
   so no rotation can re-flag them). DRC now shows 0 `silk_over_copper`
   on both halves; the W2 waiver predicate stays in the gate as defense
   in depth but no longer triggers.
2. **Spec YAML — valid.** `spec/electronics.yaml` failed in ordinary YAML
   parsers (bare `: ` inside plain multiline scalars at `pin_map.note`,
   `firmware_note`, `pcb_gate`, `pcb.files`, plus `- Foo: bar` sequence
   entries parsed as mappings). Fixed with folded `>-` scalars and two
   reworded gates; validated with js-yaml (top-level keys load). The
   schematic generator only regexes version/rows/cols, so it is
   unaffected (ERC still clean).
3. **TRRS prose — corrected.** `split_link_nets` claimed tip-meets-ring1;
   the netlist has left TIP=TX / right TIP=RX and left RING1=RX / right
   RING1=TX (right-half copper crossover D1→RING1, D0→TIP), so a straight
   cable joins tip-to-tip and ring1-to-ring1. Prose now says exactly that.
4. **Physical checks — procedure written, execution needs parts.**
   `spec/first-article.md` is the executable gate (1:1 prints at
   `out/fit/`, calibrated to the 19.00mm column pitch; DMM/continuity/caliper
   steps with expected values; TRRS power-off + USB-unplug assembly order). Still
   genuinely open until run against real hardware.
5. **Battery — locked to orderable stock.** Primary: kriscables 301230
   110mAh + JST PH 2.0mm (€18.90, SKU `Li-Po Battery 110mah-1` — order 2;
   listing verifies 3×12×30, 3.7V, PH 2.0mm and documents 100mA→full in
   ~1.1h = 0.9C, suitable). Alternates KEEBD / Typeractive 301230 (same
   class; both sold out at check). PCM required, unprotected pouches
   rejected on arrival; pigtail polarity metered pre-plug-in.
6. **BOM — sourced + knob locked.** `MPN` on all symbols, populated
   `kicad-cli` export, `spec/bom.md` per-half list with SMT-vs-hand split.
   Knob: kriscables anodized aluminium EC11 (13×13mm, 6mm bore, €4.90) —
   clears the 16mm cutout, set-screw takes the 20mm shaft; spin/push
   clearance is a first-article item.
7. **Firmware correctness (encoder steps + push path) — fixed in-tree,
    first-article tests open.** `boards/shields/hojicha44/hojicha44.dtsi`: `left_encoder`
    `steps` 30 → **15** (EC11E15244G1 = 30 detents / 15 pulses; ZMK
    `steps` counts pulses per revolution per
    `zmk.dev/docs/hardware-integration/encoders`); `triggers-per-rotation`
    stays 30 untouched. `enc_sw` rebuilt: the old parent-level `sw-gpios`
    with `ACTIVE_HIGH` matched neither binding — Zephyr `gpio-keys` takes
    one child node per button with `gpios`, and the switch closes to GND
    so it is now `GPIO_ACTIVE_LOW | GPIO_PULL_UP` with
    `zephyr,code = <INPUT_KEY_MUTE>`. ZMK keymaps consume kscan events,
    so the push reaches the keymap via a new `zmk,kscan-gpio-direct` node
    (`input-keys = <&enc_sw_btn>`) plus a `zmk,kscan-sideband-behaviors`
    node in `config/hojicha44.keymap` binding press → `&kp C_MUTE`
    (assumed, joins the C_VOL_UP/DN cluster; matrix transform, the 24
    bindings cells, and both overlays untouched). `zmk/gpio-map.md`
    checked: pin-continuity tables only, no push binding described — no
    change. `west build` still needs a toolchain. Remaining first-article
    tests: CW/CCW revolution event counts (feel + counts vs `steps = 15`
    / `triggers-per-rotation = 30`), and push-to-Mute press on EACH half.

## Release hardening (2026-10-14)

- **DRC rules tightened to fab-real values** (`Hojicha44-{Left,Right}.kicad_pro`,
  `board.design_settings.rules`): `min_copper_edge_clearance` 0.075→0.2,
  `min_via_annular_width` 0.05→0.15, `min_clearance` 0.0→0.2. Netclasses
  already enforced 0.2/0.25, so nothing routed changed — but the gate now
  protects instead of waving through. Fresh DRC both halves: still only W1,
  0 unconnected. (Generator only owns track/via presets + netclasses, so
  direct pro-file edits survive regen. `min_track_width` was already 0.2.)
- **Release Gerbers use explicit layers.** Default export dumps 21 layers
  (Courtyard/Fab/Adhesive/Margin/Eco/User_* junk); `out/release/<Half>/`
  now holds exactly F.Cu,B.Cu,F/B.Mask,F/B.Silkscreen,F/B.Paste,Edge.Cuts
  + job + drill + pos + bom + MANIFEST (verified file list, all non-empty).
  fix.md (untracked, not in repo) §5.3 now carries the exact verified commands (explicit `-l` layer
  list, `--format csv --units mm` pos, MPN-field BOM, `out/release/` paths).
  Outputs stay gitignored.
- **ZMK `left_encoder` is shared-node naming, not a bug.** Defined once in
  the dtsi, enabled per overlay, consumed by `sensors` — renaming per half
  would break the reference. Comment added at the definition.

## Doc reconciliation vs measured geometry (2026-10-14)

Read-only on generators/boards/schematics; touched only spec/README/notes/fix.

- **Key pitch 19.00mm.** 12 column-adjacent pairs in
  `Hojicha44-Left.kicad_pcb` measure 19.00mm exactly (SW_L00-L06-L12,
  L01-L07-L13, L02-L08-L14, L03-L09-L15, L04-L10-L16, L05-L11-L17).
  `spec/electronics.yaml` pitch + pitch_note and
  `spec/first-article.md` calibration changed 19.05 → 19.00; the nominal
  MX 19.05 comment reworded honestly (boards use 19.00 as-measured).
- **TRRS mouths recessed, 22.40mm.** Footprint
  `TRRS-PJ-320A.kicad_mod` mouth side is +Y (sleeve text y=11.4, silk top
  12.6); plastic face at local y=12.1 (rear -2 + 14.1 body). With J_L1 at
  (122.45,-22) rot 90 and J_R1 at (169.05,-22) rot 270 (CW-positive):
  plastic mouths L 134.55 / R 156.95 = 22.40mm mouth-to-mouth; edges at
  y=-22 L 135.54 / R 155.96 = 20.42mm edge-to-edge; each mouth 0.99mm
  recessed (silk tops 21.40mm, 0.49mm recessed). `spec/layout.yaml`
  13.50mm-proud claim replaced; `spec/electronics.yaml`, `spec/first-article.md`,
  and `README.md` now agree on 22.40/20.42/recessed. Safety rule corrected
  in README + first-article: unplug USB from BOTH halves before any TRRS
  insert/remove (switch OFF alone insufficient).
- **Flex cuts deferred-to-rev-2.** Both outlines are a verified single
  Edge.Cuts loop with no slots; gasket build works without. Spec stanza
  marked deferred, no geometry change.
- **Docs-only parts.** `spec/bom.md`: diode example MPN Diodes Inc
  1N4148W-7-F SOD-123 (DigiKey/Mouser listings + diodes.com page) or
  equivalent; PG1350 = family, builder picks feel (kit); charge-ON case
  label; fab-limits pre-order confirm. `spec/first-article.md`: BLE
  range-with-battery-and-case test; fit sheet reworded to Edge.Cuts + silk
  + fab + F.Cu pads with plate DXF as the 16mm cutout source.

## VBAT notch clearance + mask/rating corrections (2026-10-14)

- **Battery rail off the notch.** VBAT_SW_L hugged the USB-notch floor
  (copper edge 0.25mm off it, via at (111.75,47.5)) where the plug bumps.
  Fix: power-class notch keepout in the router (bite band floor-0.5 to
  floor+2, own pads carve so RAW stays reachable) plus re-blocking
  other-net clearance after the own carve (shared THT slivers become
  walls instead of graze paths — this also fixed a GND-vs-COL2 graze the
  reroute exposed). Router r13: segment-to-segment measurement over the
  whole outline gives min VBAT copper-edge 2.518mm (at the RAW pad itself,
  DRC-clean); the notch zone is empty of power copper for 40mm around
  (L runs wide west-south, 185mm total, 20mV drop at 100mA — negligible;
  R runs 19mm direct), no power vias within 4mm of the old spot, DRC
  still clean.
- **Mask expansion 0.05mm** (`solder_mask_to_copper_clearance`, was 0) so
  normal mask shift can't leave mask on SOD-123 pads. No reroute (mask
  only); DRC re-verified.
- **WS-SLTV rating corrected to 300mA switching** (was 500mA/12VDC in
  spec/bom) — fine at the 100mA default; 500mA charge-boost jumper stays
  OPEN. Mill-Max 2.11mm sockets confirmed too short for the 301230.
- Halves are ~150x115mm: over 100x100 value pricing, noted in bom.md.

## Independent PCB review response (2026-10-14)

- **13.50mm mouth-to-mouth rebuttal — 22.40mm stands.** Footprint math from
  the current files gives plastic faces L x=134.55 / R x=156.95 = 22.40mm
  (J_L1 (122.45,-22) rot 90, J_R1 (169.05,-22) rot 270, CW-positive, mouth
  local +Y face 12.1; board edges 135.539/155.961 = 20.42 edge-to-edge,
  mouths recessed 0.99). No footprint feature (holes/pads/silk/centers)
  yields 13.5. The review likely carried the old stale layout note; the
  22.40 set stands, no action.
- **Review staleness, already handled — no action.** The review's component
  table repeats the old 500mA switch rating (spec now 300mA switching) and
  scopes itself to router r10 boards (current tree routes r13 with the VBAT
  notch keepout) — both already handled, no action.
- **Disposition:** F2 documented (no-pour decision in spec/electronics.yaml),
  F3 convention documented (KiCad CPL, do-not-flip in spec/first-article.md),
  F6 checklist complete (all eight items already present, no additions), F8
  wording fixed (zmk/gpio-map.md right-half functions swapped to match nets),
  F4 flex already deferred (no change), F7 west/keymap still excluded scope.

## Independent review F1 — diode cathode tick (2026-10-14)

On-board polarity gate now met in copper-adjacent silk, not just Fab: every
SOD-123 gets a 1.0mm F.SilkS tick just outside pad 1 (cathode) at 0.29mm
local clearance (generator-owned, rotates with the footprint, so all five
per-half rotations inherit it). DRC shows 0 new silk violations at every
rotation; silk audit still symmetric. 22 ticks per half, verified in-file.

## Adversarial re-audit (2026-10-14, post-r13)

Two independent re-measurements plus a clean rebuild, all green:
- Antenna keepout: min copper-edge 5.25 (L) / 5.175 (R), no intrusions.
- Notch power: L window clear (nearest 8.5+), R window min 14.26 at a JST
  pad; no power vias within 4mm of the old via spots.
- Diode ticks 22/half; same-side clearance min 0.50. One XY-overlap noted
  (D_R02 tick over SW_R03.2 B.Cu pad) is opposite-side F.SilkS-vs-B.Cu
  across 1.6mm FR4 — DRC-silent, not a fab short.
- Global track-to-edge min 0.29 (L) / 0.33 (R); pad landings 12/12;
  single outline loops; docs-vs-reality sweep clean except the r10
  counts and P1-8 marker fixed above.

## ZMK CI (2026-10-14)

Firmware now builds in CI instead of never: `.github/workflows/build.yml`
calls ZMK's reusable `build-user-config.yml`, matrixed over both halves in
`build.yaml` (`nice_nano_v2` + `hojicha44_left/right`; workflow and tree
both pinned to v0.3 as a matched pair, so the classic board name stands
with no variant suffix and no compat marker needed). Layout mirrors the
unified template + in-tree Corne exactly — `config/` (west.yml pinned v0.3,
keymap, conf), `boards/shields/hojicha44/` (shared dtsi, per-half overlays,
Kconfig pair, metadata), root `zephyr/module.yml`. Roles: left central via
`Kconfig.defconfig` default (overridable); right overlay carries the
`col-offset = <6>` so one 6-column transform + one 24-cell keymap serves
both halves (no 12-column transform needed). Keymap content itself is still
DRAFT (legends/layers open); CI proves compilation. Push to origin to run.

## ZMK CI green (2026-10-14)

First green run after four red ones, each a real find: `RC(00)` ->
comma form (C preprocessor), `&kp MO(1)` -> `&mo 1` (undefined token),
`nice_nano//zmk` rejected on the pinned v0.3 tree (variant syntax is
main-only) -> classic `nice_nano_v2`, and the @main workflow pinned to
v0.3 to match (its compat diagnostic predates the tree). One blind alley
corrected along the way: `CONFIG_ZMK_BOARD_COMPAT=y` does not exist in
v0.3 (fatal Kconfig warning) — the pin, not the marker, was the fix.
Artifacts: `hojicha44-firmwares` (2x UF2, ~300KB). Run with `--erase`
on first flash (UICR NFC). Keymap content still DRAFT by decision.

## Firmware in hand (2026-10-14)

Both UF2s downloaded from the green CI run into `out/firmware/`
(`hojicha44_left` 435KB central, `hojicha44_right` 359KB peripheral —
size split consistent with roles; UF2 magic verified). First flash with
`--erase` (UICR NFC), then BLE-pair halves before expecting keys.
Keymap remains DRAFT content on a compiling base.

## 3D models linked (2026-10-14)

Footprint audit vs independents, all correct: Choc socket pads byte-identical
to kiswitch `SW_Hotswap_Kailh_Choc_V1`; TRRS pads identical to Keebio
`TRRS-PJ-320A` (ours renames 1-4 to S/T/R1/R2, documented waiver);
MCU = standard Pro Micro geometry + canonical Arduino->nRF map
(D1=P0.06 … A3=P0.31, RAW=24); SOD-123/JST/switch/encoder are stock.
Vendored into `pcb/kicad/Hojicha44.3dshapes/` (kiswitch WRL MIT+CC-BY-SA,
Keebio STEP MIT, hand-drawn nano envelope WRL) and linked from the three
local `.pretty` footprints, so regen carries them. nice!nano has no public
STEP — envelope box only. Renders now show sockets/TRRS/nano; bare-bottom
iso explained by previously missing links, not missing copper.

## Plate + gaskets rev-1 (2026-10-14)

`plate/gen_plate.py` derives the plate from placed PCB data:
outline = Edge.Cuts loop, 22x 15x15 cutouts, 12.5sq encoder hole (a 17mm
round would merge into the neighbour key cutout at 18.2mm pitch; knob
rides high), W1 (switch+MCU+JST) + W2 (TRRS+channel) windows, 7x5 Poron
lands top+bottom (Left 10/16, Right 16/16) with 60mm span rule bridged
from below across window zones. Two real finds: (1) Kailh footprint
rotation is CW-positive need for cutout rots; (2) FPS seeding must start
on landable samples (a 109mm blocked inner-edge run poisons blind seeds).
Stack contract + screw rules in `spec/case.md`. All gates green.

## Plate rev-2: strips + material gate (2026-10-14)

Two corrections from review, both structural. (1) Gaskets are STRIPS,
not pads: discrete 7x5 pads cannot fit the 3-6mm rim fingers beside the
windows, but 2.5mm rim strips can — and strips are what real gasket
boards use. Top+bottom pairs at the same XY (never staggered); plate
edge is the case-groove tongue, no tabs needed. (2) Plate is
material-agnostic: MATERIAL constant (PC/POM/FR4/ALU/CARBON) re-gates
every web minimum; W1 core edges pull in for 2.5+ cutout webs. Coverage
rule is now every-key-within-55mm-of-foam (measured worst 44mm, better
than commercial perimeter-ring practice). Debugging scars: FPS seeding
must start on landable samples; VRML-style y-fears do not apply to DXF.

## Plate rev-3: tab-and-jacket suspension (2026-10-15)

Review correctly called rim strips the wrong philosophy: strips couple
the full rim to the case, while tabs on silicone jackets (Satisfaction75
style) suspend the assembly on 8 soft mounts per half. Plate grows
10x5mm tongues (2mm root fillets, chamfered tips) spliced into the
outline as one dense polyline; jackets are case-side (10.5x2mm slot).
Uniformity now comes from identical mounts at even spacing (measured
worst key-to-tab 46-47mm), not foam proximity. Outline differs from PCB
by the tabs only; ports, windows, and gates unchanged, all green.

## Plate rev-4: geometry debugged, 6 tabs (2026-10-15)

Review found real defects, all fixed and now self-checked. (1) Splice
bug: tab paths injected at nearest-dense-index could precede their rim
anchor, spiking 15mm out-and-back — inject at lower-bound instead.
(2) B-side fillet arcs swept the long way (270° loops) — traverse
T2->T1. (3) Closure duplicates dropped. Generator now asserts outline
simplicity (0 crossings, verified), per-tab area, min segment, closure.
8 -> 6 tabs; inner edge stays tab-free by physics (windows occupy it,
rim finger < tab root) and floats between flanks — documented in
spec/case.md with measured worst key-to-tab 51mm.

## Plate rev-5: pinned corners + cross-file proof (2026-10-15)

Two review items closed. (1) Corners: 2 pinned tabs per half (top edge
above the outer key column, bottom-inner corner under the MCU) snap to
the nearest eligible rim (±12mm, loud fail otherwise); 4 greedy fill the
rest — 6 total, even + corner-supported. (2) Plate-vs-PCB doubt answered
by numbers, not eyeballs: encoder-to-nearest-switch is 18.2mm c-c in
both files (4.45 plate edge-to-edge vs ~4.9 body-to-body on copper);
both derive from identical instance data through one convention, and the
PCB renders the user compared against are y-flipped while the plate is
north-up, which reads as a shift side by side. (A pads-vs-cutout check
was tried and reverted on the spot: socket pads live on the far side
and legitimately overhang the switch-body cutout.)

## Plate rev-6: encoder hole on shaft center (2026-10-15)

By-eye review caught a real 7.9mm error: the encoder hole was centered
on the footprint instance origin (pad A), but the EC11 shaft sits at
local +(7.5, 2.5) — gen_pcb.py places the instance at ergogen_point
minus that offset, so the plate must add it back. Hole now at shaft
(118,-8)/(173.5,-8), mirror-exact about 145.75 like everything else.
(Side note verified along the way: the PCB was never asymmetric — MCU
pad-span centers (118/173.5) and shaft centers both mirror at 145.75;
only footprint origins differ, which carry no physical meaning.)

## Plate rev-7: poron pads on tabs (2026-10-15)

Back to 8 tabs (2 pinned corners + 6 greedy) carrying 8x4mm 4701-40
poron pads top+bottom, cut from 90x4x3 strip stock (Keebox 32-pack
covers the build). Pads-on-tabs keeps the tab-suspension philosophy
with a buyable, dimensioned, keyboard-specific gasket; grade swaps
(-30/-50) tune feel without CAD changes. PORON DXF layer + SVG pads +
JSON spec carry placement.

## Plate rev-8: review round (2026-10-15)

Three review catches closed. (1) Poron pads now sit fully ON the
tongues (center +2.0 outward, asserted per-corner against the outline)
instead of straddling the root. (2) The switch-strip + MCU windows were
two overlapping rects reading as a phantom "tiny rectangle" — merged
into one L loop via an even-odd rect-union tracer (exact-area verified).
(3) Legend now names every mark (cutouts/encoder/windows/pads/tabs).
On foam amount: 8x4 pads x8 tabs is isolation by design, not support —
more foam couples more case; for a softer build swap grade (-30), not
area. All gates green on both halves.

## Populated renders (2026-10-15)

`pcb/render_populated.py` (deleted, see render.py note below) builds throwaway /tmp board copies with one
dummy top-side footprint per socket, each linking koktoh/keyswitch_model
Choc V1 Red (master/choc/v1/KiCad/red.wrl, StepUp pipeline; measured
15.0x15.0x11.0mm = the published PG1350 15*15*11 profile exactly). Red
is the representative render variant — BOM leaves feel to the builder.
Repo tree untouched (22 dummies live only in /tmp); outputs in
`pcb/kicad/export/*-populated*.png`. Sockets confirmed B.Cu SMD with
switches on top at matching (x, y, rot), thumbs splayed correctly.

## Missing 3D models linked (2026-10-15)

Two stock footprints referenced STEP files that exist NOWHERE (not in
any KiCad bundle, not in any upstream repo — footprints added without
their models): EC11 encoder + WS-SLTV slide switch, so renders silently
omitted both bodies. EC11 solved with marbastlib ROT_EC11E.step,
remapped offset (-2.5,-7.5)+rot-90 to (15,0)+rot180 via the verified
7-pad rigid correspondence (no mirror); STEP-landmark check then proved
the shaft lands at (118,-8) within 0.03mm (pixel forensics on shaded
metal lies — trust geometry, not highlights). Switch solved with a
hand-drawn 10x2.5x6.4 envelope (courtyard-centered origin verified).
gen_pcb MODEL_OVERRIDES keeps stock geometry (W1 waiver set provably
unaffected: model lines don't count). All gates green, release re-cut.

## Encoder transform fix (2026-10-16)

User callout was right: the EC11 body sat with legs visibly off the pads
(3-pin column exposed west of the body, columns swapped). Root cause: the
old offset (15,0)+rot180 was derived by composing marbastlib's pairing
with a footprint-frame correspondence — and "verified" by shaft position
only. The shaft sits at the pin pattern's symmetry centre, so it lands
within 0.03mm under EITHER rotation while the pin columns swap sides;
shaft-centering proves nothing. Fix came from measuring the STEP directly:
pin rows at model x=0 (y=-5.01/-2.48/+0.02) and x=14.5 (y=-5.03/-0.02),
lugs y=-8.38/+3.39 — pure shift (0,5,0)+rot0 lands every contact within
0.03mm of the stock pads (lugs 0.3mm, inside the 2.6mm MP drills) with the
shaft at (7.47,2.49). Side finding: marbastlib's own offset+rotation does
not land its model's pins on its own pads either — provenance is not
verification. W1 waiver set unchanged at 28 (model lines don't count);
all gates green.

## Render set simplified (2026-10-16)

Was 5 PNGs per half (bare top/bottom/top-iso/bottom-iso + populated +
populated-iso). Now 3, via one script `pcb/render.py` (supersedes
`render_populated.py`, deleted): bare top + bare bottom orthos straight
off the repo board, and populated-iso with everything (22 switch dummies
+ all board models). Fixed a real bug on the way: the old script rendered
the /tmp throwaway copy without the 3dshapes dir, so ${KIPRJMOD} models
(encoder, sockets, TRRS, envelopes) silently went missing from every
populated iso — render.py mirrors Hojicha44.3dshapes next to the temp
board first. Stale variants deleted from export/ (gitignored).

## Iso viewpoint flipped to thumb side (2026-10-16)

Populated iso now looks from the thumb-cluster (south) side instead of the
number-row side: `--rotate '-50,0,205'` with no sips post-rotation (the Z+180
absorbs the old `-r 180`). `pcb/render.py` takes `[all|iso|bare] [half]` so
one side can be re-rendered without redoing everything.


## Engineering audit of plate/gasket stack (2026-10-16)

Verified in detail:

- PORON 4701-30-15: density 240 kg/m3 (15 pcf), 3.18-12.70 mm,
  CFD ≈ 24 kPa @25% ⇒ ≈78 gf/8x4 pad. Static ≈25 g/pad ⇒ 8-10%
  rest compression, ≈2.5-3x headroom to 25%, far below the 50%
  densification wall. Correct for thock + bounce.
- Eight tabs share ≈200 g per half with equal loaded forces; assembly
  must stay under 0% (never ship loose at ~0% or rattle/-unloaded).
- 8x4 pad geometry sits on-plate following point-in-poly within 0.1 mm,
  with uniform 0.35 mm minimum edge clearance on every tab (pad width 8
  vs tab width 10). Acceptable in CAD, rev-2 to-do (extend tab length or
  shrink pad by 2-3 mm).
- Preload target c=15-20% ⇒ cavity 6.3-6.6 mm (1.5 plate + 2x compressed).
  Matches a 1.5 mm PC/POM plate; FR4/ALU/CARBON variants yield
  6.5-6.9 mm with the same formula.
- Geometry check passes for both halves: no cutout-cutout slivers >=2.0,
  cutout-outline >=1.0, diode clearance >=0.25, encoder cutout>=1.5
  and stroke-not-a-sliver against windows, outline self-intersection
  none, closure <0.6, tab area gain in 30-90 x 8, no tab overlap, worst
  key-to-tab <=55 (worst 46-47 measured). MAX_TAB_DIST 55 allowance
  covers uniformity.

Left as future-case decisions, not in code: cavity thickness tolerance
+/=0.2 mm, TRRS/antenna cutouts per notch and mouth positions.

## First-article checklist (rev-1) (already in spec/first-article.md)
## Case v3.2 strength + ports + antenna round (2026-10-17)

User-reported: thin walls, a hole in the case bottom, oversized TRRS, antenna
opening question. All four found/measured/fixed:

- **Thin walls were real**: the wall over every tab tip measured exactly
  0.5 (skin at rim+OUTSET vs cavity at tab tip+RIM_CLEAR) — 1-2 FDM lines
  at 8 stations. Whole-case dilation raised OUTSET 6.0→7.0 (user-sanctioned
  thickening): wall census min 1.49-1.50 at tab stations (new gate ≥1.40),
  6.50 typical (p50), nowhere thin. Pocket-corner webs 1.15-1.55
  (SKIN_MIN 0.4→1.0), no adaptive nose shrink triggers left.
- **The hole in the bottom** was the port slots: v3.1 cut them from z_bot
  (−7.6) — full-height of the CASE, not the wall — slicing the 2mm floor
  slab at the USB and TRRS anchors. Fixed: slots run FLOOR_Z (−5.6, slab
  top) → lip; slab intact, battery-gated now ("slab under slot solid").
  Plugs ride above the PCB top (z 0), so the sill is free clearance.
- **TRRS slot 12 → 9.5** (user: mold to the required size): sized to the
  90° boot (≤8.5 target + 0.5/side), not the jack body. Boot caliper at
  first article verifies; over 9.5 ⇒ widen TRRS_SLOT_W and re-cut.
- **Antenna**: keepout points verified against BOTH boards' Cmts.User
  circles (118/173.5, 15.55, r=5) — matches points.yaml `antenna` and the
  nice!nano usage (USB 118,49.95 ↔ antenna 118,15.55 = 34.4mm module
  span). "No case material within 3mm" passes by construction (>19mm to
  the nearest wall) and is battery-gated at 3 z bands; NO antenna opening
  exists or is required in the tub — duty moves to the top cover.
- Volumes 67.7 cm³ both halves (was 60.3 at OUTSET 6), z unchanged
  [−7.6, +6.0], all gates green both halves, npm test green.

## Comprehensive review fix round (2026-10-17)

14 read-only review agents (7 free models) audited the whole repo; fixes
landed (case re-ran green first try, `npm test` green, release re-cut):

- **B1 keymap binding order (blocker)**: `config/hojicha44.keymap` shipped
  LEFT-HALF-then-RIGHT-HALF while the transform is row-major interleaved —
  every binding from position 6 hit the wrong key on both layers. Reordered
  to per-row interleave (positions 0-5 = left row0, 6-11 = right row0, …);
  `zmk-structure` gate now asserts the FULL token sequence per layer (2
  layers pinned) so reordering can never silently ship again.
- **B2 USB port sealed shut (blocker)**: the 7.0 rim dilation BRIDGES the
  11×5.45 USB notch (skin envelope ~17mm north of the rim), so the v3.2
  fixed `SLOT_OUT = 8.5` capped the slot under 3-6mm of wall on BOTH
  halves. Fix: per-port measured breach (face marches outward till every
  point clears the skin ring, +1.0mm margin; printed `usb out=19.00`,
  `trrs out=9.50`) + breach gates on the finished solid (mouth void
  probes across the full face ×2 z planes, air beyond the face, slab
  under slots, in-slot band probes unmasked). STEP/STL re-exported
  (volumes 66.7/66.8 cm³, wall_min 1.49/1.50, webs 1.25/1.15).
- **Firmware hardening**: removed the duplicated `vbatt` node + chosen
  line (the nice_nano_v2 board file provides both, verified against
  zmkfirmware/zmk v0.3.0); dropped the duplicated UART pinctrl defs in
  both overlays (board pinctrl is identical AND carries the RX pull-up
  ours lacked) — left keeps `&uart0` enabled for TRRS debug, right is
  now truly BLE-only (no uart, no USB). Split roles were verified
  correct in `Kconfig.defconfig` (left central / right peripheral,
  upstream corne convention — NOT a conf problem); `CONFIG_ZMK_SPLIT=y`
  dropped as redundant, `CONFIG_ZMK_USB=y` moved to the new
  `config/hojicha44_left.conf` (per-half confs ARE collected from the
  user config dir; the empty confs in the shield dir are dead — deleted),
  central gains battery-level FETCHING+PROXY (peripheral levels can now
  reach the host). L1 encoder scrolls: `C_AC_SCROLL_UP/DOWN` (the
  v0.3 tree has no bare `C_SCROLL_*`; verified in keys.h). NFC comment
  rewritten (tree is Zephyr 3.5.0+zmk-fixes). Dead conf files in the
  shield dir deleted (ZMK v0.3 reads confs from the user config dir
  only — verified in the keymap-module CMake).
- **Release integrity**: `make_release.py --check` now re-hashes every
  artifact against MANIFEST.txt, rejects extra top-level files, and
  gates the manifest commit against the BOARD-AFFECTING head
  (`git log -1 -- pcb …`), replacing the self-referential HEAD pointer
  (that's why v0.3.1's manifest claimed 3016153 while its content was
  cut at eb6678f — verified: hashes all matched, only the pointer was
  stale). Release re-cut CLEAN at eb6678f6640f (`usb` boards unchanged;
  gerber re-exports differ only in date headers). Clean rmtree rebuild
  prevents half-updated trees.
- **CI**: `checks.yml` gains case (cadquery venv-free pip) + plate
  (`--check` writes nothing) gate jobs + `permissions: contents: read`;
  `build.yml` drops `secrets: inherit` (the ZMK v0.3 reusable workflow
  references no secrets; artifact upload uses the implicit github.token —
  watch the next firmware run, restore inherit if artifacts vanish).
- **Plate CI portability**: the two stock footprints gen_plate reads
  (W1 windows) vendored into `plate/vendor_footprints/` (KiCad 10.0.6,
  CC-BY-SA 4.0 note included); `STOCK_FP` now env-overridable, vendored
  dir takes precedence. `python3 plate/gen_plate.py --check` passes
  KiCad-less.
- **Docs sweep**: case.md got the port-breach contract + cover z
  contract (module top ~7.7 > lip 6.0: cover MUST carry the opening),
  she VALUES frame-labelled (FLOOR_Z/SHELF_Z from the PCB-top frame),
  the stray `<|end|>` removed, 17mm-hole rationale set straight
  (18.18mm encoder-to-SW_L17 measured — the original 18.2 claim was
  TRUE, the review verdict on it was wrong), stack table updated
  (bottom tub BUILT). electronics.yaml: antenna rule phrased
  inboard (not "open board edge", the antenna circle sits ≥13.6mm
  inside), "11x5.4" → "11mm wide × ~5.45 deep", mounting comment
  no longer claims the case clamps the PCB. case/README: wall
  numbers 1.49-1.50, antenna 14.15, v3.3 section. first-article.md:
  regenerate-fit-PDFs-first note + measured-breach dry-fit checklist.
  render.py: EXPORT_DIR makedirs.
- NOT changed on purpose: PCB geometry (keepout gate clears min copper
  edge 5.175/5.375 ≥ 5.0 empirically), plate geometry (poron margin
  stays measure-first rev-2 trigger), `SKIN_MIN 1.0` (webs 1.15-1.55
  stand; raising it mid-rev shrinks noses for no hardware evidence),
  cover design (contract documented, build deferred).

## Case v3.4 port bores (2026-10-17)

User looked at the v3.3 output and called the ports what they were:
"no need for a drastic big gaping rectangular hole" — and asked where
the antenna window and the smaller molded audio port were. Both fair:

- **Bores shaped to the plugs (the actual fix)**: v3.2-3.3 cut each
  port as a FULL-WALL rectangle (14×11.6 / 9.5×11.6 at z −5.6..6.0 —
  11.6mm tall!). Plug stack arithmetic (sockets ~4.5 — the old ~3.0
  figure was wrong, corrected in review; module 4.5..7.7, receptacle
  mid ~6.1 per the cover-contract
  numbers) puts the USB plug axis AT the lip plane: only ~2.8..lip of
  the plug crosses the wall; the neck above the lip rides through the
  open top (future cover's duty). So: **USB = 14.0-wide slot, 1.2mm
  bottom fillets, z 2.0..top; TRRS = round Ø9.5 bore centered z 2.4**
  (jack-axis estimate; the ≤8.5 right-angle plug boot swings about it,
  margins hold ±0.5mm drift; bore clipped flat by the lip where it
  passes the top). TRRS is the "molded audio port" shape the user
  asked about — a round bore, not a rectangle.
- **Antenna window: none.** The 3mm rule is met by 14.15mm
  (nearest-material measurement); plastic >3mm from the antenna is not
  a radio problem, so no window existed or is needed in the tub — the
  question was answered and documented rather than cutting a cosmetic
  hole.
- **Mechanics kept**: measured breach unchanged (the z-independent
  march still prints usb out=19.00 / trrs out=9.50), walls 1.49/1.50,
  webs 1.25/1.15, sill solid (no bottom holes), SAT ≥3mm to pockets.
  Material returned partly: volumes 66.7/66.8 → 68.3 cm³.
- **Gates re-derived to bores**: bore half-width function (circle vs
  bottom-filleted rect) as ground truth for the probe battery; skin
  band classification is bore-aware at z=0 (USB band SOLID below
  z0=2.0); mouth probes at two in-bore z planes ±0.9 half-width; air
  beyond per plane; SAT wording now bore-vs-pocket (bounding rect stays
  sound). Both halves green on first re-run; plus a throwaway shape
  audit (`case/probe_bores.py`, kept) probing fillet/edge/chord/sill
  positions on the finished solids — 15/15 per half.
  (First probe draft hit two points that turned out to be pre-existing
  cavity/bridge voids, not bore regressions — mapping the material
  around the anchors confirmed it; HEAD at the time is v3.2 so there is
  no v3.3 baseline on disk, only the working tree.)
- Docs: spec/case.md port contract rewritten (breach + shaping +
  no-window rationale), first-article.md dry-fit now measures boot/jack
  z bands and names the v3.4 params, case/README v3.4 entry.

## User QA round on v3.4: drop-in proof + "lowering" ID (2026-10-17)
- **Question 1 (TRRS circle drop-in)**: user read the round bore's
  top-clip as an insertion blocker for the PCB + jack. Resolved by
  measurement, not by shape change: parsed the vendored
  `pcb/kicad/Hojicha44.3dshapes/PJ-320A.step` (506 pts). The earlier
  "6.4-tall" memory was wrong — the model says body **6.1 wide
  (±3.05), top face FLAT at z 5.0**, rear tail local y −2.0, plastic
  mouth face at local y 12.1 (a face RECESSED 0.99mm — the old
  "0.99mm-proud" claim was wrong, corrected in review), THT pin tips
  at z −3.0, and a mouth-face centre vertex at z **2.5** (= the plug
  axis). The jack is inboard of the cavity line everywhere — the
  recessed mouth face (see above) means NOTHING of the jack crosses
  the wall band during the straight drop-in; the conservative worst
  corner
  (±3.05, 5.0) is r 3.94 about the axis vs bore r 4.75 → ~0.8mm clear;
  the boot ball (≤8.5 about z 2.5) also stays inside (chord 2.41 at the
  z 6.0 clip). The "circle curving back in above the top" region
  (z > 5.0) hosts no jack material in service or in the drop.
- **Params**: `TRRS_MOUTH_ZC` 2.4 → **2.5** (measured, no longer an
  estimate); comment now carries the STEP-measured dims. Case rebuilt:
  breach march unchanged (usb out=19.00 / trrs out=9.50, z-independent),
  volume 68.3/68.3 cm³, wall 1.49/1.50, webs 1.25/1.15, STEP/STL
  re-exported.
- **probe_bores.py gained a drop-in group**: per half, the jack face
  section (b ±2.9, spares at ±3.3, wall resuming at +0.2 past the local
  circle) probed at z {0.15, zc, 4.85} × t {0.7, 3.5} — void inside,
  solid outside, plus a design-break fail if the bore can't host the
  face corner. All pass both halves.
- **Question 2 ("slight lowering in front of the microcontroller")**:
  that is the **USB plug seating notch** — 11 wide × ~5.45 deep in the
  PCB RIM at each `usb` point (spec/electronics.yaml: "the notch alone
  provides plug seating"; the module's USB shell sits ~9mm inboard and
  does not overhang). It exists since the first PCB/plate/case chain —
  v3.4 changed nothing there except the bore band 2.0..lip cut into
  that wall. **Not an antenna feature**: the antenna keepout is at the
  module's SOUTH end (5.0mm Cmts circle + 3mm case rule), nearest
  material measured 14.15mm; the notch is 30+mm away and untouched.
- Docs: spec/case.md TRRS contract now states the measured dims +
  drop-in proof; first-article.md dry-fit names the z 2.5 axis
  (still caliper-verify). npm test + release --check CLEAN @eb6678f6640f.
- **Case v3.5 — PWR mouth finalized on raw Edge.Cuts**: the north rim
  near the switch is a y=58.0 plateau across x 97.5..110.5 (mirror
  181..194); the WS-SLTV (footprint 104/187.5, 51, body top z 5.0)
  never crosses the wall, so the wall question was a MOUTH: 5.0-wide
  slot z 4.3..top with 0.8 fillets (nail entry 0.7 below body top).
  Frame anchored EXACT (no resample phase — a wobbling anchor x left
  the slot 0.87 from tab-4's pocket at x=100.59; SAT gate rejected;
  mouth centre 106.3/185.2 → SAT 3.21/3.13, ~1.8 web to the USB
  mouth). Lever sweep ~3.6 assumed (datasheet blade + ±0.8 travel);
  first-article flick test closes it.
- **Case v3.5 — magnet stations (v3.5)**: `magnet_stations()` walks
  the cavity boundary outward: local band ≥6.4 → ≥1.1 webs (mid-band
  premise re-checked against the true boundaries), SAT ≥5.1 from every
  port/pocket rect using rect-aware distance — a point INSIDE a rect
  is 0, edge-distance alone once parked a phantom station inside the
  USB-notch void and the pocket web probes caught it — antenna ≥10.1,
  spacing ≥14, slots at perimeter/8, rings rotated to the USB anchor
  (Left/Right mirror measured 1.29mm — exact-mirrored generation
deferred, tolerance documented). Result: 8/half, band min 6.48/6.49,
  Ø4.2×2.2 pockets face-flush at the lip plane. Retention stack:
  tub magnets face-UP, cover magnets face-DOWN — faces meet at 6.0
  (rigid zero-gap stop; the 0.2 glue seat is the only compliance), so
  the poron preload stays geometric (uncompressed 6.5 vs ring 6.0).
- **Ring cover v1 shipped** (`case/gen_cover.py`): skin prism 6.0..9.0
  minus the cavity prism — outer face flush with the tub skin
  (intentional lid seam), inner edge = cavity line. [HISTORICAL — the
  v3.5 review round below moved the interior to the PCB rim + 0.5 so
  the ring bridges the tabs; numbers superseded there.] Passages via
  `compute_ports` verbatim: W1 full-depth (the plug's overmold pokes ~0.2 past the top at ~9.2
abs — the module tops 7.7; wording corrected in review), TRRS = the
  same Ø9.5 cylinder as a BLIND tunnel in
  the 6..9 slice (tops 7.25 > boot swing 6.75 chord ≤4.82 < band ⇒ ring
  NOT split), pwrsw full-depth but 1.1 inner web (W1 stays the only
  radial severance ⇒ single solid; first attempt with a full radial
  slot would have made 2 pieces). First hand-placed ring-resume probes
  were wrong for the wider bite outline — replaced by a port-agnostic
  skin-hug battery (resume solid 0.6mm inside every skin sample hugging
  a port rect). Measured: cover 7.7/7.7 cm³, wall_min 1.49/1.50,
  station bands 6.48/6.49. [HISTORICAL pre-review numbers; the review
  round re-measured cover 9.0/9.0 cm³ (T4 pockets), census wall 5.85.] Shared helpers now live in gen_case
  (compute_ports / pocket_layout (extracted adaptive-nose rule) /
  magnet_stations); `pocket_layout` reused for station SAT.
- **Case v3.5 — census + gates**: per-port census prints every tub run
  (usb housing 0.83/side + plug bottom 0.8; trrs boot 0.50/side + face
  drop-in 0.81; pwrsw sweep 0.70/side; breach outs; pocket SAT) plus a
  magnet line (count, coords, band/web min, ant margin 14.15). Tub
  68.0/68.0 cm³ (−0.3 from magnets+pwrsw), bbox unchanged. probe_bores
  gained a 7-probe pwrsw group/half (sill below, flank, fillet
  envelope, wall resume past w/2, lip-plane top). npm test pass;
  `pcb/make_release.py --check` CLEAN @eb6678f6640f (case-only changes
  leave the boards byte-stable). Docs: spec/case.md (stack rows, port
  contract pwrsw bullet, new "Retention: recessed magnets + ring
  cover" chapter), spec/first-article.md (pwrsw flick / magnet glue /
  ring dry-fit items), case/README.md v3.5 entry + gen_cover listed.

## Review round on case v3.5 + plate encoder (user solo review, 2026-10-17)
- **Finding A (HIGH) — the ring did not press the top pads**: v1 cut its
  interior prism from the plate OUTLINE, so every tab pocket left a
  tab-shaped bite in the ring; the reviewer probed all 8 pad centres VOID
  at z 6.2 AND 7.5 (the cover's pads were decorative). Fix: the cover's
  interior is the PCB rim + RIM_CLEAR (0.5) now, NOT the outline — the
  ring bridges every tab zone at the lip plane and presses the top poron
  at the designed 16.7% (6.5 uncompressed vs 6.0 ring underside).
  `cav_poly` still drives `magnet_stations`/`pocket_layout`, so
  tub↔cover station identity is untouched (band 6.48/6.49, mirror
  1.29). New gate: every pad centre must be ring material at 6.2 and
  7.5 — it FAILS in the bite state, so this exact bug can't return.
  Measured after: cover 8.9/8.9 cm³ (bites backfilled, +1.2), census
  wall_min 5.85 (was 1.49, measured against the bites — the census now
  measures the rim-based ring), volumes well inside the tripwire band.
  Fix in `gen_cover.py` + docs (case.md stack/retention, first-article
  dry-fit now plate-in/foam-mark based, case/README, this log).
- **Encoder hole 12.5 → 12.7** (`plate/gen_plate.py`): the vendored
  EC11 STEP measures 12.30 wide in the plate band (z 2.0..3.5) — the
  old "~11.7 body" premise was wrong (0.4/side claimed vs 0.20/side
  real). Both halves re-generated + re-gated CLEAN; predicted enc↔SW17
  web ~3.55 (was 3.75 at 12.5) — still ≥2.5 target. Docs: README plate
  row, layout.yaml, first-article (hole refs + bullet rewritten to the
  measured margins + explicit §1 pre-order order), case.md
  plate-openings, bom.md knob/plate rows.
- **Words batch (findings C/D/E)**: TRRS drop-in narrative corrected —
  the 0.99 mouth face is RECESSED behind the board edge (typo "prooud"
  also fixed), so NOTHING of the jack crosses the wall band; the bore
  probes stand as conservative bounds (params/probe_bores/case.md/
  notes q+a entry). USB socket stack corrected to ~4.5 → module
  4.5..7.7 (receptacle mid ~6.1 unchanged; params/case.md/notes v3.4
  entry). Notch depth states the measured 6.3–10.3 below the LOCAL rim
  (case.md; "~5.45" was a one-point figure). "Module pokes ~0.2" → the
  plug's overmold pokes, module tops 7.7 (case.md/first-article/
  case/README/notes v3.5 entry). PWR slot 4.3 is a SILL 0.7 below the
  body top (first-article). Magnet mirror documented ≤1.3 (1.29
  measured; exact-mirror generation deferred). `PWRSW_COVER_IN = 1.6`
  replaces the derived t_web in gen_cover. first-article gained a
  print-orientation note (PETG/ASA, no supports as oriented except
  possibly the mouth arc bridges on a poor bridger).
- Deferred (recorded, not done): PWR pad shift 2mm west (slice-test
  lever sweep item; the current margin stands), exact-mirror station
  generation (1.29 documented instead), poron pad shift to root+2.5
  (burns 1.0 of the tip spare for a 0.5 sliver → rev-2 only), wrl
  envelope touch-up (datasheet supersedes).

## Multi-model review round 2 on plate + case v3.5 (2026-10-18)
Six free models fanned out read-only, four reported; every finding
re-verified against 1a93095 before acting. One BLOCKER, one HIGH, eight
MEDIUM, a LOW doc cluster. What was done:

- **B1 (BLOCKER, verified in code before touching anything)** — the tab
  pillar fuse (`gen_case.py`) re-added a 1.5mm strip of cavity material
  (rim−1.0..rim+0.5, FLOOR_Z..SHELF_Z) under the PCB at all 8 stations:
  the board would rest ~1.05mm high on 8 pillar strips and unload the
  bottom pads. First fix attempt (delete the fuse as "redundant") was
  WRONG — the gates caught it immediately (shelf void at root+4.0: the
  tab lobes are cavity in v3.1's no-bulge dilation, the wall over a tab
  tip is only 1.5 wide, the fuse IS the shelf). Correct fix: keep the
  fuse, clamp its inboard edge to +0.3 outboard of the rim (PCB-edge
  fab tolerance; the foam pad spans rim..rim+4 so the 0.3 sliver just
  bridges). New gates: "pcb footprint clear" (air at root−0.5, z
  −1.0/−0.7, per tab) + a plan-wide sweep of the PCB rim footprint at
  z −1.0 (3mm grid, rim-edge 0.3 exclusion; the sweep initially false-
  positive on tab lobes — the footprint is the PCB RIM, not the plate
  outline). Tub 68.0 → 67.4 cm³ (exactly the removed strips), all else
  unchanged.
- **T4 (M4, user-picked over thickening)** — cover magnets Ø4×2 →
  Ø4×1.5 (16 pcs), cover pocket depth 1.7, floor 0.8 → 1.3mm. Faces
  still meet at the lip plane; tub keeps its 2.0s. Cover 8.9 → 9.0 cm³,
  wall/stations unchanged. BOM rows added (both magnet sizes were
  MISSING from the BOM entirely — caught while writing this up).
  First-article pull test added: ≥1.5 kg straight lift with plate in.
- **M2 (3-source) — pwrsw actuator reach**: footprint shifted 2mm WEST
  (ergogen pwrsw shift [9,14] → [7,14], mirror follows) so the blade
  band sits under the SAT-constrained mouth window (mouth stays at
  106.3/185.2 — it cannot move). Cascade, honestly larger than a
  constant change:
  - Left: the two hand-routed pwrsw stubs' pad-side endpoints moved
    (104→102, 101.46→99.46).
  - Right: 25 hand-routed pwrsw chain segments + 6 hand vias were tuned
    to the OLD router output and pad positions — deleted as stale; the
    router re-routed both stubs fresh.
  - Router upgrades (generator-owned, all gate-verified): (a) the
    dangle/keepout checker now sees the MERGED board copper with
    dangle-reporting restricted to PRESERVED items (the preserved-only
    view false-flagged GUI junctions that meet router copper; the
    router-only view cannot see stale GUI breaks); (b) the router's
    obstacle model is now seeded with the preserved GUI copper at
    EXACT clearance (no MARGIN) — the MARGIN-inflated seed rejected the
    legal COL5_R corridor past the GND GUI via (0.85mm centerline,
    0.825 needed) and produced a detour with a dangling end; (c) router
    vias co-locating with GUI vias are dropped (DRC co-location
    warning).
  - Final: gen_pcb exit 0, DRC both halves clean modulo the W1 set
    (28 lib mismatches), GUI items stable {L 9, R 12}.
- **M1 — floor derivation rewritten to the measured ruler** (the hotswap
  sockets are TOP-side; they never provisioned the floor): encoder legs
  −3.65 (vendored ROT_EC11E STEP maps 1:1 into the PCB frame — rotate 0,
  no z offset), TRRS pins −3.0, socket bump −1.25, slide-switch legs
  ≤−3.5 (family), JST ~−2.5 (family). Deepest −3.65 → FLOOR_Z −5.6
  keeps ~1.95mm; NO geometry change. params.py + spec/case.md floor
  text rewritten; first-article keeps a caliper item for the family
  bounds.
- **H1 — Choc cutout stays 15.0, wording fixed**: the PG1350 lower body
  passes at 13.8 square (the 15.0 outline includes the clip wings) →
  ~0.6/side at 15.0 and the clips never engage — coherent with the 1.5
  PC plate anyway (clips need ~1.3mm plate gap; 1.2mm-class plates
  click). "Friction fit" replaced with the real mechanism; rev-2 option
  (~14.0 + 1.2mm plate) decided by the §1 laser coupon A/B, not before.
- **M6/M7/M8 — gate hardening**: gen_cover.py added to checks.yml (it
  was committed ungated); stack-ties check in spec_checks.cjs (GAP ==
  PLATE_UNDER, TOP_LIP_Z == PLATE_UNDER+PLATE_THICK+2.5, cover pocket
  floor ≥1.2); plate tab-eligibility now excludes the pwrsw mouth rect
  (regen diff: both DXFs byte-identical — today's placement clears it
  for real, now enforced); gen_plate prints definitive encoder webs
  (cutouts 9.15 / windows 3.65 / ports 4.92–5.35 — the disputed
  "~3.55 vs 1.75" pair confusion resolved: neither was the cutout web).
- **LOW doc cluster, one pass**: TRRS cover chord ≤4.82 → the honest
  6.42-at-lip figure (conclusion unchanged via the 1.75 roof); encoder
  neighbor rationale 18.18 (footprint origin) → 24.04 (shaft center);
  stale pre-fix cover rows annotated HISTORICAL in notes + case/README;
  DXF layer docstring GASKET → PORON (matches the emitted layer);
  v3.4 changelog TRRS axis z 2.4 → measured 2.5 noted; USB notch-to-pad
  0.78 loupe item already present in first-article §4 (no change).
- **No-action, for the record**: M3 (poron 0.35 corner margin) stays the
  documented measure-first rev-2 trigger; M5 (wall 1.49/1.50 vs 1.40
  gate floor) stays informational — the census prints it every run.
- Deferred: none new; M2's printed-slice flick test remains the
  first-article confirmation of the shifted footprint.

## M3: power-switch relocation — origins centred on the windows (2026-10-18)

**Trigger**: multi-model re-verification (grok 4.7 + gemini + space-bunny +
nvidia deepseek-v4.1 + muse reflection; all vector-extracted from the
450301014042 drawing) overturned the M2 chirality theory. The M3-attempted
artwork rotation is withdrawn.

- **Corrected actuator model**: the neutral lever band = footprint origin
  ±1.8 (2.0 blade + 1.6 travel), centred on the COM pin / footprint
  origin in both files' frames; the drawn nub (3.21..5.21 from the pin-②
  end) is one travel *extreme*, not the neutral. The ±4.2 "offset" the
  M2-era audit chased is the pin-③ end cell's ~Ø1.0 flush indicator dot
  (at +4.265 local), not the lever. Consequence: assembly rotation is a
  geometric no-op for visibility, and rot-180 artwork would swap
  pad2/pad3 board holes under nets 20 (/VBAT_SW) / 47 (NC-Pad3) — the
  hand stub at (99.46,51) would land on the NC pad (short + floating
  rail pad). Rejected.
- **Real defect found**: both origins sat 4.3mm OUTBOARD of their
  SAT-pinned windows (Left 102 vs 106.3; Right 189.5 vs 185.2) → swept
  bands touched the window edges exactly, zero visible blade on both
  halves. M2's "shift 2mm WEST" had the right magnitude but the wrong
  sign (the pre-M2 remedy was +2.3 EAST); the audit's ±0.8-based
  arithmetic then hid it.
- **Fix**: ergogen pwrsw anchor shift [7,14] → [11.3,14] (Left origin
  102 → 106.3; mirror follows to 185.2). Bands now 104.5..108.1 /
  183.4..187.0 vs windows = 0.70/side both halves. Mirror-pure, no
  asymmetric fallback needed.
- **Plateau frozen BEFORE the move**: the board outline's two plateau
  corners re-referenced from pwrsw/mirror_pwrsw to
  matrix_inner_top/mirror_matrix_inner_top (95,37 / 196.5,37 — the
  mirrored half needs PLAIN shifts, ergogen negates shift.x for
  mirror_ refs, and the mirrored corner ORDER (181 before 194) matters
  for the shoulder fillets). Freeze values = the COMMITTED boards'
  Edge.Cuts (97.5..110.5 / 181..194 at y53.5), NOT "today's
  pwrsw(102) corners" (95.5..108.5) — archaeology: M2 moved the switch
  points and the boards but never re-cut the ergogen board.dxf, so the
  whole v3.5 mouth/SAT math silently assumed the pre-M2 outline; the
  freeze pins that outline permanently (the plateau never moves with
  the switch again). board.dxf regenerated 71/71 entities identical.
- **Routing**: nets 20 (VBAT_SW) and 45 (J_2-Pin_1 pack+) are now
  100% router-owned on both halves (Right kept 0 GUI items; Left kept
  9 — the committed file carried TWO parallel net-20/45 route
  families; the zero-indent family ended at the moved-away pads and
  was deleted as stale). Left pad-side endpoints were first retargeted
  +4.3 (103.76/106.3) per the M2 hand-stub precedent; gen_pcb's
  re-route superseded them with fresh corridor beams and the dedupe
  keeps both co-existing — DRC-clean either way.
- **Silk ref**: the SW ref field (left-justified 8-char string at local
  (0,−2.54)) began at the footprint origin, so at the inboard
  positions its glyphs ran into the nice!nano socket's silk spill
  (x≥109.05, y≈48.07) and, on the Right, westward into the bite
  shoulder at x=179. New gen_pcb hook `ref_shift` moves it away from
  the inner bite wall with MIRRORED signs: −3 on L (→103.3), +3 on R
  (→188.2); DRC clean both halves.
- **Case/plate**: plate regen = the pwrsw pass-through window follows
  the switch (committed cut was still 104-centred — pre-M2 stale —
  first time placed at 102 or 106.3); window now 100.05..112.55 /
  178.95..191.45 (13-wide; exact mirrors about x 145.75); north-edge
  outline + all other cutouts
  unchanged, plate gates CLEAN. Case regen (gen_case.py) = ZERO diff
  (mouth 103.8..108.8 × z4.3 is SAT-absolute, never referenced the
  switch point); census now reports lever sweep 3.6 vs slot 5.0 =
  0.70/side; cover regen unchanged (stations/z/wall_min as before).
- **Gates**: gen_pcb exit 0, ERC 0, DRC both halves only the 28
  W1-waived lib_footprint_mismatch; npm test all-pass (w1-gate exact
  28/half, zmk-structure, stack-ties). Body clears the side cavity
  walls by 1.20mm both halves (112.5/179.0 walls vs body ends
  111.3/180.2).
- **First-article additions**: caliper the lever-vs-COM at both detents
  (band interpretation, not a gate) — see spec/first-article.md §2.

## Hand-copper manifest pipeline + post-audit P0 landing (2026-10-19)

### Why the pipeline changed: the kept-classification never converged

gen_pcb classified "GUI copper" by reproduction — an unseeded phase-1
plan was run purely to guess which tracked items were hand-tuned
("not reproduced = GUI"), then a seeded phase-2 plan de-conflicted
against that guess. But the seeded plan diverges near its own seeds,
so the NEXT run classified phase-2's output as GUI and churned the
board on every regen — observed this round: Left kept oscillated
0 → 11 → 15 → 59 items; Right vias 100 → 117 in one run; idempotency broke wherever the previous run's output fed the next
extraction (the compounding hazard).

The clean capture against the M3 baseline (PCB_KEPT_DEBUG, evidence:
opencode/pcb_capture.log) settled the truth once: L had 15 kept, of
which exactly 9 are genuine hand copper (nets /VBAT_SW_L +
Net-(J_L2-Pin_1), the M2-round switch-bay family — triple-confirmed:
notes.md M3 record above, forensics, capture) and 6 are router-owned
corridor drift; R had 11 (ENC_B_R + GND chains), router-owned per the
M3 record ("Right kept 0"). The L corridor 6 also carried the exact
frozen collision that jammed routing (hand via (78.0,−10.5) 1.0607mm
from the fresh COL3 via spot = 0.0143 inside the cross-net via-pad
rule 1.075) — preserving them would have baked the jam in.

### The redesign (option C): provenance beats reproduction

- `pcb/kicad/hand-copper.txt` — the authoritative preserve set,
  scoped per half (`[Left]`/`[Right]`), human-readable signatures
  (kind, net, layer, geometry, r2). To hand-tune: edit the board,
  commit, review the census, capture lines from
  `PCB_KEPT_DEBUG=1` (dropped items print paste-ready). A manifest
  line the committed board lacks = hard error.
- `gen_pcb.py`: extraction reads the COMMITTED baseline
  (`git show HEAD:...`) — a failed build on disk can never become its
  own next input; gates (containment, copper/dangle/keepout) run
  BEFORE the write; on DRC rejection main() archives the build to
  `opencode/rejected-*.kicad_pcb` and reverts the board, so the
  worktree always lands regen-ready. Uncommitted working-board edits
  are archived (`opencode/pre-regen-*.kicad_pcb`) before overwrite.
  The rev-tag drop branch and the via-size migration hook are gone
  (provenance replaced both); the co-located-via drop pass stays.
- `gen_route.py` rules stand from the prior half of this session:
  signal via pads 0.60 → 0.65 (annular floor), ROUTER_VERSION
  unchanged (r13, no bump); seeded `avoid_vias` now drives
  via-placement rules — same-net pairs keep the drill rule (0.55
  center→center), cross-net pairs use the pad rule (1.075 for
  0.65+1.0) so later nets yield to earlier vias bidirectionally.
- Hand via kept as authored: (94.75,45.75) Ø1.0/drill 0.5 (POWER).

Proof: three consecutive regens produced byte-identical boards
(modulo uuid/date) with DRC clean ×2 (`28` W1-waived only): L keeps
exactly the 9, corridor regenerated fresh and CONVERGED (the jam is
gone: run E/F/G2 logs, exit 0); R pure-router 590 items.

### First-contact gate failures the new pipelines caught

- `plate/gen_plate.py` — my H1 USB-plug bay derived its span from a
  14mm band min: the west-edge outline points (x −0.64..0.35) beat
  the run, the floor cluster was 0.99 wide, the 9.0..13.0 assert
  fired. Fix: locate the mouth the way check_board referees notch
  openness — the config `usb`/`mirror_usb` anchor, the in-window
  below-anchor maximum = floor; the floor flat's run gives the span.
  Both halves CLEAN (encoder webs 9.15/3.65/5.62 L).
- `case/params.py` + `gen_case.py` — the P0 magnet policy (pocket
  Ø4.3, ≥1.15 webs, band 6.6) hit a **6.5 physical band**
  (CASE_OUTSET 7.0 − RIM_CLEAR 0.5): `d ≥ MAG_STATION_BAND` zeroed
  every candidate except the notch pocket (USB slot rect kills it) —
  "none eligible", tubs AND cover. probe (opencode/probe_mags.py)
  split the failures; minimal fix: **CASE_OUTSET 7.0 → 7.1**, band
  6.6 exactly. Census: wall_min 1.60 (tab tips were 1.49), web 1.15,
  band 6.60, stations 6 (L) / 7 (R) mirrored, volume 68.1/68.2; cover
  wall_min 5.94, web 1.15, stations 6/7. spec/case.md + case/README
  updated; wall-over-tab-tip is now 1.6.
- `npm test` all-green throughout (w1-gate negative test included,
  zmk-structure 46/3, stack-ties); audit_silk symmetric OK; ERC
  untouched (netlist drives the schematic, copper rounds don't).

### Everything shipped together

Regen order this round: gen_pcb → gen_plate → gen_case → gen_cover →
npm test / audit_silk; the release re-cut follows the Stage-2 commit
(`make_release.py` refuses dirty trees and gates the ERC/DRC
reports). Evidence logs retained under `opencode/` (pcb_runE/F/G2,
capture, plate_run2, case_run3, cover_run2, probe_mags.py).

### CI verdict on the pushed v0.3.1 (d19dab7)

First push verdict came back same-day with two failures — both real,
both fixed in place:

- Static checks died on `layout/generated/v2/points/points.yaml`
  missing: an untracked generator output that TWO gates read for the
  usb anchors (`check_board.py` notch gate, `plate/gen_plate --check`
  mouth scan). The board-gates CI job only started running in this
  push, so the dependency shipped untested. Fix: track the file
  (3.5k lines / 55 KB) via gitignore negation — it is gate input, and
  committed geometry should be certified geometry. A regen that moves
  points now dirties the tree visibly and must ride the next commit.
- ZMK failed on both halves: `devicetree error: /behaviors/
  transparent lacks #sensor-binding-cells` — the L2 raise layer's
  `sensor-bindings = <&trans &trans>` (net-new in the batch, never
  compile-validated locally; spec_checks excluded sensor lines from
  every check). Fix: mirror the base volume pair
  (`&inc_dec_kp C_VOL_UP C_VOL_DN`) — a layer without sensor-bindings
  would eat sensor events while L2 is held; caveat documented in the
  keymap (L1+L2 chord reads volume instead of scroll, provisional).
  spec_checks now rejects &trans/&none in sensor-bindings and wants
  one sensor-bindings per layer.

Ordering-readiness facts confirmed en route: plate DXF `$INSUNITS = 4`
(mm), and `make_release --check` stays green for non-board commits
(`board_commit()` scopes pcb/kicad + generators + spec/electronics.yaml,
so the @ab06523 stamp stays current until boards change).

Round 2 on 0db0399's CI — one symptom class ("CI lacks KiCad / full
history"):

- `make_release --check` failed first on CI-only state: the deferred
  fetch-depth fix turned out load-bearing — on depth-1 checkouts
  `board_commit()` diffs the tip against the empty tree, so every board
  path counts as touched at HEAD and the manifest stamp can never
  match. Fix: `fetch-depth: 0` on all four Static-repo checkouts.
- `check_board` died in `G.load_nets` — the schematic netlist came
  from a kicad-cli runtime call (macOS path hardcoded). Fix:
  `load_nets` exports straight into tracked
  `pcb/kicad/Hojicha44-{Left,Right}.net` (kicadsexpr; the header
  `(date …)` line neutralized — it was the export's only
  nondeterministic bytes), and when kicad-cli is absent it parses the
  committed file. The `KICAD_CLI` env override enables local testing
  of the KiCad-absent path: verified 3× byte-identical exports and
  `KICAD_CLI=/nonexistent check_board` CLEAN.
- The gen_pcb change is board-affecting by the currency gate's own
  definition, so a full release re-cut rides it (release commit
  touches only generated/release). Round 3: the copper-reconstruction
  path also reads `board.dxf` (via build_placements → pick_fiducials)
  — tracked now too (5.5 KB, same negation), completing the "CI checks
  the committed duo of layout outputs" set (points.yaml + board.dxf).
  Round 4: pick_fiducials then resolved pad geometry from the STOCK
  KiCad footprint libs (machine macOS path) — `pcb/stock/` now vendors
  byte-identical copies of the six non-project footprints in FP_SRC
  (Diode/Encoder/JST/PwrSw/Fiducial/MountingHole, cmp-verified against
  the 10.0.6 install; fp-lib-table untouched so KiCad sees nothing
  new); `fp_source` prefers the vendored copy. With that, the
  `KICAD_CLI=/nonexistent` check_board simulation is CLEAN end to end.

## 2026-10-20 — design-review synthesis round (six reviewers, user-directed)

The review batch (4 first-round + 2 background max-thinking agents —
beam-free, nemotron-3-ultra ×2, longcat-2.5-preview, GLM-5.3,
MiniMax-M3.1 — READ-ONLY prompts, spec → generators → artifacts) landed
12+7+12+12+7 findings net of noise. Six… actually the usable count:
**31 accepted/discriminated findings** triaged into: implement now,
verify-at-first-article, reject-with-evidence.

### Implemented (this round, all gates re-run CLEAN)

1. **Magnet stations symmetric-by-construction** (consensus: longcat P1,
   beam P2, nemotron P1, GLM P1, MiniMax P1): `magnet_stations()` now
   computes the LEFT set once per geometry, then mirrors for Right
   (`x -> 291.5 - x` = 2·`MIRROR_AX`) and re-validates every mirrored
   station against the right boundaries/obstructions/antenna — failure
   aborts the build instead of drifting counts. Root cause of 6/7 was
   the per-half slot walk (resample phase + literal drift), not real
   geometry.
2. **Case margins to the reviewer floors**: CASE_OUTSET 7.1 → 8.2
   (wall 1.595 measured → 2.62/2.70; clears the MJF-2.0 floor beam and
   nemotron both flagged), MAG_STATION_BAND 6.6 → 7.5 (web ≥1.6 floor,
   measured 1.69), MAG_MIN_STATIONS 6 → 8 (GLM's doc-chain finding: the
   16+16 BOM and the pull-test math promise 8/half — Left had been ON
   the ≥1.5 kg gate at 6/7; now 8/8 exact mirrors, band 7.68 — the
   STATION SET is exactly mirrored; the tub OUTLINES are not (the polygon
   offsetting leaves wall_min 2.62 L vs 2.70 R, a 0.08mm difference
   inside every floor).
   Volume tripwires widened [55,82] tub / [6,13] cover (75.7/10.7).
3. **Wall census sampling**: every resampled skin point instead of
   every 2nd/4th (GLM P2) — the "chord sag ≤0.03" claim no longer has
   to be taken on trust; tub gate raised with the wall floor
   (OUTSET−TAB_L−RIM_CLEAR−0.3), cover ring gate 1.40 → 5.0 (7.20
   measured; the 7.20 thin spot is the W2/pwrsw shoulder, not a fault).
4. **Plate**: PORON_PAD_L 8.0 → 7.0 (beam + nemotron + minimax P2
   consensus; corner-edge 0.35 → 0.71 measured both halves, kerf
   fragility closed); port keep-rects mirror-DERIVED from the Left
   literals (GLM P2; usb/trrs carried +0.5 drafting drift — pwrsw was
   already exact-mirrored; webs 5.62 both halves, was 5.21 right);
   encoder-hole corner maths written down (GLM#? — body 8.628 extreme
   vs 0.5-fillet hole reach 8.773 → 0.145 clearance; MiniMax's
   tangency concern resolves: tangency needs a 0.85 fillet, nowhere
   near our 0.5).
5. **check_board gates** (5 new, all CLEAN both halves): pad+via
   containment (nemotron P0 — a library drift walking TRRS THT pins off
   the edge now fails the committed gate), antenna keepout re-measured
   at commit level (GLM P2 — GUI-passing preserved boards can't
   silently violate the r5 zone; pad edge-distance ≥5.0, via centres
   ≥5.0), TRRS crossover pin-map (nemotron P1 — L: U pin1 TX→T,
   pin2 RX→R1; R crossed; jack identity both halves), W1 pad-content
   equality vs vendored stock for all 28 waived refs (MiniMax P2 — the
   exact-set gate proved drift, never content; probe found 0 diffs, so
   the gate starts honest), silk-to-edge floor 0.20 (measured floor:
   jack outline silk 0.24 is the closest real silk; label silks
   0.49/0.78).
6. **gen_pcb build-time guards**: MCU socket pad columns pinned against
   the vendored source ({−15.24, 0} = 15.24 apart, audit probe) and the
   SOD-123 co-invariant asserted ("DIODE ⇒ strip_silk must be on — the
   tick may not double-mark a native bar") (nemotron P2/P1 ×2).
7. **Doc reconciliation sweep**: electronics.yaml 48→47 nets, via fab
   lines (0.8-0.4 → 0.3-in-0.65 + 0.5-in-1.0; "ours 0.15/0.25" →
   "0.175 annular, JLC-verified"), antenna-figure wording (centre
   13.65 / circle 8.65; "circle ≥13.6" was centre-only), socket
   height-ban rewrite (ban the 2.11mm height, not the 315 family;
   first-article caliper item added), case.md Ø4.2→Ø4.3 everywhere +
   station/pocket/census/tripwire numbers refreshed to the OUTSET-8.2
   census, antenna claim restated in-plane 14.15 + floor 5.60, encoder
   corner maths + hole-web relabel (first-article's "3.35mm web to
   SW_L17" was really the W2-window web; SW_L17 stays ~9.15),
   case.md gate table current, case/README gets the v3.6 entry,
   MANUFACTURING.md plate default = PC per spec (POM stays the
   upgrade) and the phantom "snap lip" wording removed, first-article
   live-census quotes refreshed (out=20.20/10.70/10.70), diode assembly
   map added (deterministic: D_xxx ↔ SW_xxx at the switch's +x;
   thumb-arc exceptions listed), magnet station example coordinates
   refreshed.

### Rejected / deferred with rationale (recorded, not silently dropped)

- **D_L99 "29th waiver" (nemotron round 2)** — misread: D_L99 is the
  W1 gate's deliberate negative-test injection (npm test adds a 29th
  and expects rejection); the committed boards carry exactly 28.
- **"No antenna gate exists" (nemotron round 2)** — rejected: the gate
  exists (gen_case.py check_half, envelope rings at 24 azimuths × 4 z
  planes + ring-boundary distances; the COVER carries it too). What
  WAS true and is now fixed: the SPEC claim quoted 14.15mm as "to the
  nearest case material", which is the wall-only in-plane figure — the
  floor slab stands 5.60mm below in 3D. Document + census line added.
- **Right overlay `uart0` disabled (beam)** — rejected as misread: the
  right overlay's own comment documents wired-debug as left-half-only,
  and electronics.yaml scopes the TRRS as bring-up/debug fallback
  (BLE primary; splitkb advises against cabling two battery halves).
  No functional wired split is claimed, so nothing is missing.
- **Signal via pad 0.65 → 0.7 bump (beam/nemotron/minimax)** —
  declined after measurement: annular 0.175 is +0.025 in hand vs JLC's
  finished-hole floor; growing signal pads to 0.7 tightens the harder
  constraint (cross-net via clearance needs (0.7+1.0)/2+0.25 = 1.10
  where the current design enforces 1.075) and jeopardizes the L
  corridor the router only just resolved. Documented as a rev-2
  trade, not changed.
- **Reverse-polarity ideal-diode FET (beam)** — deferred to rev-2
  hardware: the procedural gates exist (pigtail polarity metered
  BEFORE first plug-in; JST '+' silk; slide switch = charge
  disconnect). Recorded in electronics.yaml; not cut into this
  release.
- **Via "0.15 fab min annular" claim (MiniMax)** — corrected the doc to
  real values (0.175 measured, ≥0.15 floor ✓) instead of treating it
  as a board defect.

### Self-review findings (same round, caught before sign-off)

Re-reading my own diff with fresh eyes turned up three real defects and
one unverified assumption — all fixed, all with evidence:

1. **The new silk-to-edge gate sampled only polyline VERTICES** — a silk
   line running parallel to the board edge is closest along its
   INTERIOR, and a silk line that CROSSES the edge has true distance 0
   while its endpoints sit far away. Both would have read as clear.
   Replaced with exact segment-to-segment distance (crossing = 0);
   negative control: an injected silk line crossing the edge reports
   0.00mm and fails the gate, where the old scan reported 2.00mm and
   passed it.
2. **The station cache was keyed on a rounded ring-perimeter
   fingerprint** — an unrelated plate-outline tweak could make the
   Right lookup miss and then blame the CALL ORDER instead of the real
   cause. Replaced with a single slot (one geometry pair per process)
   plus an explicit mirror-consistency check (perimeters within 1.0mm)
   that names the actual problem.
3. **The plate/case port anchors had two homes** (case/gen_case.py's
   PORTS dict vs the plate's hand-written keep-rects) — exactly the
   drift the reviewers flagged, still possible. PORTS moved to
   case/params.py (stdlib-only) as the single source of truth, and the
   plate gate now ASSERTS every case port anchor sits inside its
   keep-rect (negative control: moving the Left trrs anchor to
   (200,-22) fails the build with the anchor/rect pair named).
4. **gen_pcb is NOT byte-reproducible** — KiCad mints a random uuid per
   element, so a rebuild churns ~7800 lines of the board file while the
   GEOMETRY is identical (verified: uuid/date-stripped files are
   byte-equal). Two consequences: the committed boards are the
   certified artifact by definition (the manifest hashes the EXPORTS
   **and the board bytes** — the release manifest carries board sha256,
   make_release.py enforces it), and any local rebuild must be reverted
   rather than
   committed. Worth knowing before a future "let me just regenerate"
   reflex; the board-affecting pathspec treats a generator edit as a
   board change anyway.
5. **CI never runs gen_pcb** (no KiCad in the static checks) — so the
   two new build-time asserts are exercised only locally. Ran the
   builder explicitly: it completes, the DRC/ERC reports are unchanged,
   and the boards come out geometry-identical (the asserts are
   behaviour-neutral). The CI case job runs `gen_case.py` with no
   arguments, so the Left-before-Right contract of the mirrored
   station build holds there (verified in the workflow, not assumed).

### Rejected / deferred — continued

- **TRRS mouth widening (beam P2, ±0.34/side chord margin)** —
  NOT widened, and deliberately: the margin the reviewer measured was
  the ring's remaining width beside the TRRS bore, and widening the
  mouth would CONSUME it, not restore it. The band growth (OUTSET
  7.1 → 8.2, ring wall 7.7) is what restores the margin; the bore
  stays Ø9.5 (0.50/side over the Ø8.5 boot swing) and the cover's
  blind-tunnel chord (6.42 at the lip plane) is re-proved by the gates
  on every build.

### Process receipts

- Pre-commit battery: `npm test` (7/7 checks incl. the W1 negative
  control), `check_board.py` CLEAN ×2, `audit_silk` symmetric OK,
  `plate --check` CLEAN ×2, `gen_case.py` + `gen_cover.py` gates
  exit-0 both halves.
- The fix batch touches pcb/generators (board-affecting by
  `board_commit()` pathspec) → full release re-cut follows with the
  manifest stamp recomputed on a CLEAN tree (this also retires the
  stale `-dirty` tag MiniMax found in MANIFEST.txt — the stamp line
  was computed before the previous cut's outputs were committed).

## 2026-10-21 — second review round (three max-thinking reviewers, one at a time)

Three fresh READ-ONLY passes over the repo, run sequentially (not
parallel) so each was independent: **MiniMax M3.1 Flash Free**, **GLM-5.3
Flash Free**, **DeepSeek V4.1 Flash Free** (opencode zen, max thinking).
31 raw findings; the three converged hard on the same systemic shape.

### The systemic finding: gates that re-derived instead of read

All three independently proved the same thing with negative controls:
`check_board.py` re-derived pad geometry from the vendored footprint
library + generator placements (`R.Board`), so **a hand-edited committed
board passed every gate** — a TRRS pad moved 90mm off-board, a diode pad
parked on the antenna centre, a pad's net swapped, all clean. The
file's own docstring claimed it verified "against the BUILT .kicad_pcb".
Fixed: the gates now parse the COMMITTED board's own pad blocks
(`committed_pads()`, flip/y-axis convention verified pad-for-pad against
the model) and everything that was checked against the model is now
checked against the artifact:

- containment, antenna keepout (pads + vias + **tracks**, which nothing
  covered at all), the TRRS crossover pin-map (from the board's own pad
  nets), W1 content (now including the pad's LOCAL position), plus two
  new gates: **artifact-vs-model drift** (every committed copper pad must
  equal what the generator would produce — position, size, drill AND
  net; catches a hand edit on ANY footprint, not only the 28 waived
  refs) and the **diode cathode tick** (the only polarity mark on 44
  diodes, and CI never runs the builder that draws it).
- Negative controls, all now failing loudly: TRRS pad off-board, diode
  pad on the antenna centre, pad net swapped, tick moved, tick deleted,
  track through the keepout, waived-ref pad resized, MCU TRRS nets
  swapped, jack T/R1 swapped.
- The UART gate ALSO had a second hole of its own (it read the
  netlist, not the board) — now asserted on the artifact AND the
  netlist.

### Release chain (the deepest one)

DeepSeek found the worst hole, and the cut's own comment proves it was
known-but-unimplemented: "a failing **or stale** report must not ride
beside fresh gerbers" — the cut detected the *failing* case only. It
copied the generator's committed ERC/DRC reports, so a hand-edited board
shipped with fresh gerbers beside a stale clean report. The cut now
**re-runs** `kicad-cli pcb drc` / `sch erc` on the exact board and
schematic it exports, gates on those, and the MANIFEST records the
**board sha256** so the release names the bytes it certifies.

### Derived thresholds that could not police themselves

Three floors were computed from the very constants they were meant to
police, so shrinking the constant shrank the floor (all three reviewers
proved it by reverting the constant and watching the build stay green):
`wall_gate = OUTSET-TAB_L-RIM_CLEAR-0.3`, the magnet web
`(MAG_STATION_BAND-MAG_DIA)/2`, and `PORON_PAD_L` (no floor at all —
8.0mm pads, the 0.35mm kerf-fragile state, passed every gate).
Now ABSOLUTE floors: `WALL_MIN_ABS 2.0` (the MJF pass), `MAG_WEB_MIN
1.6` (the reviewer floor, measured on the TRUE per-boundary web — the
old derived number overstated it on oblique points), `PORON_EDGE_MIN
0.6` (measured 0.707), and `spec_checks.cjs` moved 1.10 -> 1.60 and
from a presence-only `diode-direction` test to the exact `col2row`
value (a flipped value read the matrix backwards and passed).

### Also fixed

- `load_nets()` re-exported the netlist IN PLACE whenever kicad-cli
  existed, so a read-only gate rewrote a tracked file and locally
  tested different bytes than CI. Now read-only by default; the
  builder passes `refresh=True`.
- `board_commit()` ignored three board-affecting input trees
  (`points.yaml`, `board.dxf`, `pcb/stock`) — editing any of them did
  not move the release stamp. Now in the pathspec.
- The Choc hotswap SOCKETS (44) had **no order line anywhere** — they
  are footprint-only parts, so they never appear in the released
  `bom.csv`; `pcb/BOM_ORDER.md` now has the line, and
  `pcb/MANUFACTURING.md` names them in the hand-solder list.
- The concave-outline **TAB-ROUTE ONLY, NO V-CUT** order instruction
  existed only in `spec/bom.md`; it is now in both ordering docs
  (measured min copper-to-edge 0.292mm).
- Stale numbers reconciled: poron 8x4 -> **7x4** everywhere (case.md,
  first-article, BOM_ORDER) with the force corrected 78 gf -> **~68 gf**
  (28 mm²) and the strip yield 11 -> **12 pads/90mm**; the 0.35mm kerf
  margin -> **0.71mm**; the "0.8-0.4mm via" line -> the real
  0.30-in-0.65 signal / 0.50-in-1.00 power; BOM_ORDER's case volumes
  68.1/68.2 -> **75.7/75.7**; MANUFACTURING's stale board stamp ->
  the MANIFEST's own `git commit:` / `board sha256:` lines.
- The first-article "verify the spare input toggles" step could not
  pass (D10 has no binding and no test pad) — replaced with a DMM
  check naming the pin (MCU D10 = P0.09).
- The assembly order was ambiguous ("sockets" meant two different parts)
  and never said when the PCB/plate/cover go in — rewritten as one
  numbered 12-step order.
- The case's port anchors were not mirror-exact (the trrs pair was
  rounded to 1 dp and broke the mirror by 0.1mm) — now 134.55 /
  156.95, exactly mirrored.
- The "Choc sockets are top-side" wording contradicted
  `spec/electronics.yaml` ("soldered beneath (B.Cu pads)") — the
  electronics spec is right (the footprint's pads are B.Cu); the case
  docs and `case/params.py` were corrected.
- "8/8 exact mirrors" is now qualified: the STATION SET is exactly
  mirrored; the tub OUTLINES are not (polygon offsetting leaves
  wall_min 2.62 L vs 2.70 R — inside every floor, but not "exact").

### Deferred / not acted on (with reasons)

- **PORTS vs the physical jack position** (GLM): the case's trrs anchor
  is not asserted against the committed board's TRRS footprint. Real
  gap, but the fix needs the footprint's local mouth offset (12.1) as
  a second source of truth; noted here rather than half-implemented.
- **The 0.04mm silk-floor headroom** (MiniMax P3-4): the floor is 0.20
  and the measured minimum is 0.24 — the gap is the TRRS jack's own
  outline silk, which is DESIGNED to sit at the edge (its aperture IS
  the edge). Left as is, with the reason in the constant's comment.
- **The paper-fit PDF** (MiniMax P3-9) is unversioned scratch with no
  documented regeneration command; the checklist already says
  "regenerate first".
- **`fp_source()` falling back to the local KiCad install** (MiniMax
  P3-8): all six vendored files are present and tracked, so the
  fallback never fires today.
- **Battery price** (DeepSeek P3): BOM_ORDER said EUR 8.90,
  `spec/bom.md` said 18.90 — offline neither can be verified, so both
  now cite the EUR 8.90-18.90 range with "re-check at checkout".
- **The W2 "0.64mm side web" claim** (DeepSeek explicitly dropped it):
  the bore chord is tangential and the ring band is radial, so the
  number was meaningless; the single-solid gate is the real severance
  check.
- **Live prices, the magnet pull force, the poron compression, the
  plug dimensions, the cell stack height and the MJF printability**
  all remain first-article measurements — no offline check can settle
  them (every reviewer said so).

---

## Open to-do log — 2026-10-22 (after support strategy b, release v0.5.0)

State at this entry: the rev-2 stack is implemented and gated, the
release is cut and clean, and nothing has been ordered or pushed. What
is left is the work that **cannot be done in software** plus three
decisions that are the owner's to make.

### A. Pre-order gates — these block the ORDER, not the work

1. **Choc cutout test coupon** (`spec/first-article.md` §1). One
   100 x 100mm sheet of 1.2mm PC: four 20x20mm squares with 13.8 /
   14.0 / 14.2 / 15.0mm holes, plus a fifth with a 14.0 hole and the
   0.55mm diode-relief pocket (the RELIEF layer of the plate DXF).
   Test: does the 13.8 body pass the hole, does the clip lip
   (0.9–1.3mm above the PCB) grab the 1.00mm underside, do the 14.8mm
   ears seat on the 2.20mm top face, is the pocket 0.55mm and NOT
   through. **If 14.0 does not catch, drop to 13.9 and re-cut the
   coupon** — do not discover this after two plates and 44 switches.
2. **Fabricator partial-depth capability.** The plate needs a 0.55mm
   pocket in the underside of 1.2mm PC (0.65mm left under it). A
   through-cut would leave the switch without plate support; a
   through-cut vendor cannot do a partial pass is a real sourcing
   constraint, not a detail. Ask the plate vendor before the order.
3. ~~**Keymap layer decisions**~~ **CLOSED 2026-10-22** (M3.3;
   see the entry at the end of this log): L1 = digits/shifted/F-keys,
   L2 = nav/media/BT, the L1+L2 chord = Adjust, all four modifiers are
   home-row mod-taps, Backspace/Delete have thumb + L2 homes, and the
   map is a GENERATED artifact (4 variants) with a proven gate.

### B. Not a pre-order gate — but do not forget it

4. **Bluetooth SIG** — only if a unit is **sold or branded**
   (the SIG's trigger: "selling, branding, manufacturing, or
   representing a product as its own"). Adopter membership is $0; the
   one-off Product Qualification Fee is $12,000 + a $1,250 Company
   Identifier for one design, and our keyboard is an Unmodified Design
   (Nordic's qualified nRF52840 + ZMK → listing, no new RF testing).
   A self-built, never-sold pilot owes the SIG nothing. See
   `spec/compliance.md`.
5. **ACMA Responsible Supplier registration** — free, but the RCM may
   not be applied to the product before it exists. Do it when the
   first unit is built, not before.
6. **The RCM label is a sticker**, not case printing, until the market
   is fixed (AU/NZ now; the US/EU paths are in `spec/compliance.md`).

### C. Physical first-article measurements (no offline check can settle these)

- plate flatness and the 0.40mm pocket depth on the real part;
- the magnet pull force at 8 stations per half (the retention
  arithmetic says ≥3 kg against a ~200 g half — measure it);
- the poron compression (the design assumes ~16.7% preload);
- the LiPo polarity gate before the first plug-in (RAW-B+ / GND-B- /
  RAW-VCC open / charge-ON);
- the TRRS gap on the printed halves (20.42mm edge-to-edge, 22.40mm
  mouth-to-mouth) and the 90-degree plug fit;
- the 301230 cell's outline in the printed bay.

### E. BLOCKER found by the rev-2 audit (2026-10-22) — FIXED, but read this

**The encoder did not fit the rev-2 plate.** The rev-1 encoder hole was
a 12.7mm square sized for the rev-1 plate band (z 2.0..3.5), where
the EC11E's body is 12.30 wide. The rev-2 band is **z 1.00..2.20**,
and measuring the project's OWN vendored ROT_EC11E STEP shows the
encoder's **terminal blocks span 14.95mm for z 0.0..1.5** (the
12.30 waist starts at z 1.6). The rev-2 band sits inside the terminal
blocks: the 12.7 hole fouled the encoder by **1.41mm/side** and it
would not have gone through the plate at all — the first article would
have caught it, at the cost of two plates and a re-cut.

Fixed by sizing the window to the measured ENVELOPE: **16.2 x 12.4**
(~0.34/side over 14.95 x 11.70), symmetric about the shaft so the
halves stay exact mirrors (the encoder is a translated, not mirrored,
part). `gen_plate.py` now ASSERTS the window cannot shrink below
envelope + 0.2/side. A first-article caliper check on the real
encoder's terminals is in `spec/first-article.md`.

The lesson is the same one as the diode height, and it is worth
stating twice: **a component that moves relative to a hole must have
its clearance envelope re-measured in the NEW band.** The encoder's
own datasheet number (12.30) was still in the spec, still true, and
still wrong for the hole.

### D. Process lessons from this round (do not repeat them)

- **Research before deferring.** BLK-2 sat open for a session because
  the PG1350 drawing was "not vendored" — the data was one search
  away (Kailh's outline drawing + a community STEP model). Deferring
  a task to a human who has to go and find the data is a cop-out; the
  agent can find it. Two searches later the whole support strategy
  had hard numbers.
- **Measure, do not inherit.** The stack's "diodes are 1.35mm" was an
  inherited comment, 0.09mm pessimistic; KiCad's own D_SOD-123.step
  says **1.260mm**. Measuring it (one CadQuery bbox) changed the
  relief depth and the clearance budget. Every dimension in this
  design should have a source next to it — a drawing, a STEP, or a
  measurement — not a number someone typed.
- **A decided plan can be infeasible; prove it and take the fallback.**
  "Diodes to B.Cu" was implemented and then **proven impossible** by
  the geometry: the Choc socket is a bottom-side part with asymmetric
  tabs and body whose orientation the switch fixes, so the two
  halves' bottom copper cannot be mirror-symmetric. The decision
  already carried a fallback (a plate relief pocket) and it was used —
  0.35mm at the first 1.05mm gap, then 0.40mm at the final 1.00mm
  gap so the pocket floor stays at 1.40mm. Record *why* the primary path
  died, or the next person will try it again.
- **Quote fee schedules, not headlines.** The first summary said the
  Bluetooth SIG Adopter tier costs $12,000; it is $0, and the $12,000
  is a one-off qualification fee that only bites if you sell. Read the
  actual schedule.
- **A cheap test piece beats an expensive rework.** The cutout coupon
  is a few dollars and a day; a wrong 0.2mm hole size costs two
  plates, 44 switches and a re-cut of the case stack.
- **Ask the question that ends the task.** "Why is this not fixed?"
  was answered by implementing it; "wdym coupon" by writing the
  coupon down as a drawing request.

## M3.3: keymap finalisation — 4 generated variants, home-row mods (2026-10-22)

The owner's four calls: macOS-heavy (offer both mac and win variants),
left-space AND right-space variants (4 total), thumb table confirmed.
Implementation:

- **The keymap is a generated artifact now.** `config/gen_keymap.py`
  derives every binding from `spec/layout.yaml` (legends + thumbs +
  `keymap.variants`) and emits `config/hojicha44.keymap` (the ACTIVE
  variant, what CI builds — default `mac_left`) plus all 4 variant
  files in `config/variants/`. Hand-editing them is an anti-pattern;
  `--use <variant>` switches (one commit, CI rebuilds). CI deliberately
  builds only the ACTIVE variant: the upstream v0.3 reusable workflow
  pins one `ZMK_CONFIG` per call, so per-variant CI would need 4 config
  dirs (a follow-up if wanted, not a pilot blocker).
- **Home-row mods = ZMK's own "timeless" recipe**, verified against the
  pinned v0.3 binding schema (all properties exist there, incl.
  `require-prior-idle-ms`): `flavor = "balanced"`,
  `require-prior-idle-ms 150`, `tapping-term-ms 280` (high — the
  positional triggers decide), `quick-tap-ms 175`,
  `hold-trigger-key-positions` = COMPUTED other-hand 22 positions,
  `hold-trigger-on-release`. One behavior per hand. GACS (win) /
  CAGS (mac): Shift on F/J both ways; Cmd(GUI) moves D/K on macOS.
- **Layer content**: L1 = 1–0 in QWERTY order + shifted row + F1–F12
  (sensor: scroll); L2 = BT profiles + media + clipboard (left) and the
  nav inverted-T + Home/End/PgUp/PgDn/Ins/Caps/PrtSc (right), sensor:
  prev/next; Adjust = L1+L2 chord via `conditional_layers`, `&bootloader`
  at W / `&sys_reset` at E (the v0.3 label is `bootloader`; `&boot` is a
  later rename — the dev-docs page says `&boot` and v0.3 does not), else
  `&none`.
  Thumbs: Esc | L1 | Tab | Space /// Del | L2 | Backspace | Enter
  (right-space variant swaps Space↔Enter only). Inner-bottom leaves
  the thumb layer: `-` (left) and `'` (right) joined the base layer;
  letters/digits/QWERTY order untouched.
- **Gates**: `zmk-structure` now shells `gen_keymap.py --check`
  (byte-compare of 5 files + structural validation: 46×4 bindings vs
  the dtsi RC count, sensor rules, mod positions, trigger lists,
  chord, sideband). Five negative controls all fail loudly and revert
  clean (incl. legend drift in the spec — the "single source" claim is
  enforced, not asserted).
- **Doc drift found and fixed while writing the bench**: the rev-2
  audit had bumped `DIODE_RELIEF_D` 0.40→0.55 but the coupon, BOM
  vendor instruction and case-spec relief sentences still said 0.40 /
  floor 1.40 / 0.14 — now 0.55 / floor 1.55 / 0.15 worst-case
  (0.65mm of plate stays under the pocket). Coupon/vendor text must
  track the generator, so they now quote the assert, not a number.
- No board-affecting path touched (`pcb/…`, `spec/electronics.yaml`,
  `layout/generated/v2/{points,outlines}`, `pcb/stock` all unaffected;
  legends live in `spec/layout.yaml` and firmware is not in the
  release bundle) — **no release re-cut required**; release stays
  v0.5.0 @4adf5fbf8e9c.

## M3.4: three-round production-readiness audit cycle (2026-10-23)

Three staged fresh-eye audits, one subagent at a time (free-provider rate
limits). Standing rule held end to end: **verify every finding locally
before fixing; refute on the primary source, never by assertion; every new
gate gets a negative control proving it bites.** Findings: round 1 = F01–
F07 (firmware/keymap), round 2 = 14 mechanical, round 3 = 3 P2. All
resolved or refuted with evidence; release v0.5.0 stays CLEAN
@4adf5fbf8e9c (no board-affecting change entered the repo since the
stamp). Commits: bc27556, 8b5f99d, 7ef1296, 62caad9 (round 1), 4066571
(round 2), this commit (round 3).

### Round 1 — firmware/keymap/bindings
- F01 binding `;`: dtc 1.8.1 harness (`opencode/dtc_keymap_test.py`,
  untracked scratch) — `<&kp 7; &kp 7>`, `<7;>`, `<7;\n7;>` all error AT
  the `;`; newline-separated rows compile clean; the CI-compiled draft
  (063e47e) carries no `;` inside arrays. Fix: 5 keymaps regenerated with
  newline rows + validate() gate rejecting any interior `;`. Negative
  control: the harness FAILs on the pre-fix file, naming the guilty row.
  (bc27556)
- F03 EC11 semantics: ZMK v0.3 `ec11.c` computes val = pulses×360/steps —
  a delta from the per-pulse reading the datasheet wording invites.
  Primary sources: vendored `alps,ec11.yaml`, ZMK
  `app/module/drivers/sensor/ec11/`, sofle shield (steps `<80>` / TPR 20)
  corroborating the ratio. Fix: dtsi `steps = <60>` (TPR stays 30),
  spec_checks gate 15→60; the Alps "15 pulses/rev" wording stays in
  electronics.yaml/bom.md (mechanical truth; the ZMK steps value
  quantizes it). (8b5f99d)
- F04+F05: full 10-slot thumb asserts (positions 36–45) on every variant,
  sideband wiring asserts (`kscan = <&enc_push_kscan>`, `row = <0>`,
  `column = <0>`), CANON_MAP_ORDER ordered-transform gate; 5 hand-built
  mutants all caught. (7ef1296)
- F06+F07 stale-string purge: layout.yaml R=91.2/13.9 sync, dead "Tab is
  an L1+Space combo" dropped, keycap-W/E adjust anchors, spec_checks
  header "exactly 4 layers", hojicha44.conf documents the deliberate
  absence of `_right.conf`. (62caad9)
- Residual F02 = the CI-compile proof itself: 32+ commits unpushed; the
  binding gates + dtc harness are local, but the green CI run on the
  pushed tip is the final artifact — awaits push approval.

### Round 2 — mechanical plate/case/order docs (minimax m3.1)
- F-01 (P0): BOM_ORDER plate row carries the DXF layer contract
  (OUTLINE/CUTOUT through; RELIEF = 22× 0.55 partial-depth pockets, do
  NOT cut through; PORON = punch template) + ask-the-shop-FIRST on 0.55
  partial-depth capability.
- F-02 (P1): relief pocket re-derived — DS30086 rev 31-2 p4 as primary
  (E = length 2.55–2.85, D = WIDTH 1.40–1.70, A = height 1.00–1.35) + the
  vendored STEP's widest section at the plate plane (2.700×1.550; the old
  2.566×1.416 basis was the chamfered top face) → pocket **3.15×2.00**;
  assert pins the pocket basis to the STEP section. The old 2.866×1.716
  left 0.008 mm/side against a datasheet-max part — inside mill
  tolerance.
- F-04 REFUTED on the same source: the finding read D as height; DS30086
  says D = body width (typ 1.55 = exactly the STEP's measured width).
  The 1.40 "height ceiling" does not exist; the 0.55 relief stands on
  A_max 1.35 + seat.
- F-03 (P1): `gen_plate.py --check` now regenerates into a tempdir and
  byte-compares DXF/SVG/lands.json vs the tracked artifacts (the old
  check only replayed geometry gates — the auditor's CUTOUT=15 mutant
  sailed through); absolute assert holds CUTOUT 14.0 ±0.02. Negative
  controls: CUTOUT=14.015 mutant (inside the assert window) → `STALE` +
  exit 1 naming the four drifted files; tampered lands.json byte →
  print-manifest FAIL naming the file; CI-parity proven in a /tmp
  extract with no `case/out` (skipped cleanly).
- F-14: capture-window derivation documented and guarded — the Choc v1
  clip captures the plate underside inside the lip band z 0.9..1.3;
  settled gap = 2.2 − plate thickness → 1.3 = lip tip (marginal),
  1.5/1.6 = below the band = friction-only (the documented failure).
  Assert keeps PLATE_THICK in 1.0..1.25; the coupon calipers the real
  plate first.
- F-05..F-13: webs 7.90/3.80/4.38 measured off the regenerated artifacts,
  x/y window clearance 0.625/0.375 asymmetry documented, lip 4.70/5.20,
  docstring/SVG-legend/encoder-comment fixes (24.04 shaft-based), knob
  swept-circle note (13×13 square sweeps ~Ø18.4 at the corners) + shaft
  D-flat alignment notes, order-record MANIFEST (sha256 of 6 tracked
  plate files + 8 case solids; `.gitignore` re-include; npm
  print-manifest gate), mirror gate added to the CI case job. (4066571)

### Round 3 — electronics/process
- Model note: two launch attempts on deepseek-v4.1-flash (opencode zen)
  died at startup ("Insufficient account funds"); GLM 5.3-flash #max ran
  the round. An independent verification pass over this round runs
  re-bound on nvidia NIM (deepseek-v4.1-flash) — verdict appended below
  when it lands.
- Verdict: **zero P0, zero P1** — first round with none. Verified-clean
  (evidence re-checked locally): ERC = exactly the 5 waived spare labels
  (matches `spec/electronics.yaml:305-309`); DRC = 28×
  `lib_footprint_mismatch` waiver both halves, 0 non-waived; W1 = 22
  diodes + 4 thumb Choc + socket + TRRS per half; extents 150.499×114.627
  both halves; vias 0.30/0.65 + 0.5/1.0 and tracks {0.25, 0.5} per
  MANUFACTURING.md; min copper→edge 0.292 (Left notch corridor) / 0.330
  (Right) vs the 0.3 fab rule — top carried concern: have the fab confirm
  in writing or nudge one track at reorder; bom.csv 49 rows/half;
  pos-smt = the 22 top-side diodes only (paste SHIPS for hand placement:
  B_Paste carries the 44 socket-pad apertures, F_Paste the 44 diode
  apertures — an earlier draft of this entry said "B_Paste empty",
  corrected by the NIM pass); JST "+" silk on the pin-1/VBAT side; PCB 5.0 vs case 3.0 antenna rules
  are two documented lanes, not a contradiction.
- R3-01 (P2, fixed): the transport memo carried "UN 3480, PI 965 Section
  II (packed with equipment)" — doubly wrong. IATA deleted PI 965 § II
  (DGR 63rd ed., eff. 1 Apr 2022; the FAA 2024 guide lists the removal;
  the IATA 2026 guidance = DGR 67th ed. lists bare cells only as PI 965
  § IA passenger-forbidden / § IB, ≤30% SoC from 1 Jan 2026 per SP A331),
  and "packed with equipment" mispairs the UN number (UN 3481 = with
  equipment: PI 966 § II packed-with, PI 967 § II contained-in). Memo
  bullet rewritten with sources; `spec/electronics.yaml:51-54`
  (UN 3481/PI 967 § II) was already correct.
- R3-02 (P2, fixed): notes.md Left census "446 copper items" predates the
  last copper pass; re-measured on the committed board: 384 `(segment` +
  71 `(via` = 455 (the identical metric reproduces Right 590 = 490+100).
  Corrected inline with the re-measure note.
- R3-03 (P2, DEFERRED): `pcb/kicad/Hojicha44-*.net` headers carry an
  absolute single-machine `(source "/Users/martinchen/…")` and
  `(date "")`. Evidence: gen_pcb.py:168-173 nulls the date deliberately
  (determinism — KiCad stamps wall-clock there), the source path is
  whatever kicad-cli wrote at export, and NO gate or tool consumes either
  field (grep across pcb/generators + tests: only the writer). Any fix
  (fold a source-path relativize into the date-null re.sub, or edit the
  tracked .net) is a board-affecting change that would tip the v0.5.0
  stamp and force a gerber re-cut for zero content change → fold into
  the next natural re-cut.

### Standing order gates (user actions)
- Cutout coupon (13.8/14.0/14.2/15.0 + 0.55-deep relief; pocket now
  3.15×2.00), fabricator written 0.55-partial-depth confirmation
  (embedded in the BOM_ORDER plate row), Bluetooth-SIG consultant.
  Push approval → CI green closes round-1 F02.

### Round 3 verification pass (nvidia NIM deepseek-v4.1-flash re-bind)
- The GLM round-3 session re-bound to NIM (no zen respawn — deepseek
  v4.1 was the originally requested auditor family; the zen route was
  unfunded). Independent pass: fresh six-area sweep FIRST, then verify
  the three resolutions.
- Part B: R3-02 **VERIFY** (count reproduced: 384+71=455 Left,
  490+100=590 Right, edge segs 111/111); R3-03 **VERIFY — defer sound**
  (refresh=False reads the .net read-only; the parser touches only
  net/code/name/class + pins; board_commit() covers pcb/kicad +
  pcb/generators, so any fix moves the stamp); R3-01 **QUALIFY** — one
  clause wrong, fixed this commit.
- R3-01 fix detail: the ≤30% SoC rule for bare UN 3480 applies **since
  2016** (the ICAO April-2016 rule — rechargebatteries.org guidance;
  lion.com), not from 2026. 1 Jan 2026 is when it extends into PI 966
  **packed with equipment** (DGR-66: "extended into PI 966, initially
  as a recommendation in 2025, and becoming mandatory in 2026"; IATA
  fact sheet; >2.7 Wh per the DGR-66 change — the 0.407 Wh cell is
  under that threshold either way). SP A331 is the **exception**
  (transport at >30% SoC with State approval), not the limit's basis.
  And BOTH § IA and § IB are cargo-aircraft-only for UN 3480. Memo
  corrected against these sources.
- New findings, all P2, **no new P0/P1**:
  - A-01: rev drift — committed board/sch title blocks say `(rev "0.3")`
    while spec/electronics.yaml is 0.5.0 and gen_schematic.py:663
    derives REV = spec MAJOR.MINOR; electronics.yaml:314-315 claims the
    sheet "cannot drift", but gen_schematic.py:1230-1237 skips an
    already-placed board and gen_pcb.py:1300 rebuilds from the frozen
    head, so it cannot self-heal. DEFERRED with R3-03 to the next
    re-cut: one-time re-stamp + a KiCad-free CI gate (title-block rev
    vs spec MAJOR.MINOR). Inert for ordering — the fab gets gerbers (no
    title block) + drill + BOM + pos; the gbrjob GeneralSpecs rev is
    cosmetic.
  - A-02 (fixed this commit): notes.md said the manifest "hashes the
    EXPORTS, not the board" — wrong: the release manifest carries board
    sha256 and make_release.py:292-306 enforces it. Corrected.
  - A-03: gen_pcb.py:144 comment "byte-stable like the boards" wrong
    (uuid4 per element; the truth is geometry-stable, notes.md:1558).
    Comment-only edit in pcb/generators = board-affecting → DEFERRED to
    the next re-cut.
  - Self-correction adopted: round 3's "B_Paste contains only headers"
    was wrong — B_Paste carries 44 aperture flashes (22 sockets × 2
    pads), F_Paste 44 (diodes × 2); consistent with hand assembly
    (pos-smt.csv = the 22 diodes only, a deliberate make_release
    filter). Entry line above corrected.
- **F02 CLOSED (2026-10-23):** 39 commits pushed (03c5f49..ca48bd4);
  CI green on both workflows at ca48bd4 — Static repo checks run
  39864726437, ZMK firmware build run 39864726932. The audit cycle is
  fully closed: every finding fixed, refuted on a primary source, or
  explicitly deferred (next-re-cut batch: R3-03, A-01, A-03). Remaining
  before orders = user-action gates only (coupon, partial-depth
  confirm, copper-edge confirm, Bluetooth-SIG).

## M3.5: fab-capability research — clearances, partial depth; BT-SIG gate dropped (2026-10-23)

- **Bluetooth-SIG gate DROPPED (owner decision)**: the build carries an
  off-the-shelf pre-certified module (nice_nano_v2) and the units are a
  hobby build, not marketed for sale — the SIG self-listing requirement
  re-appears only if units are ever sold. Decision recorded in the
  research-open-items Bluetooth row; the fee analysis there (:85–104)
  stands as reference.
- **Copper-to-edge 0.292mm: PASSES the applicable rule — written fab
  confirmation gate collapsed.** The "0.3mm fab rule" was the V-CUT
  rule all along. JLCPCB's 2026 layout guide: "minimum
  board-edge-to-copper clearance of 0.3mm for V-cut panelization and
  0.2mm for tab-routing"; outline blog: "at least 0.2mm clearance from
  routed edges to copper features". Our order is TAB-ROUTE → 0.292mm ≥
  0.2mm with 0.092mm margin. CNC routing tolerance ±0.1mm (precision) /
  ±0.2mm (regular) per the capabilities page (fetched 2026-10-23) —
  prefer the precision tier at quote if offered, to protect the notch
  corridor. BOM_ORDER + MANUFACTURING updated with the sources; the
  verbatim TAB-ROUTE order note stays (concave outline still forbids
  V-cut on its own terms).
- **Trace/space**: unchanged and comfortably inside JLCPCB's published
  limits (repo check 2026-10-14 in spec/bom.md; our 0.25mm tracks and
  ≥0.2mm clearances vs fab minimums an order of magnitude lower) —
  no action.
- **Partial depth (0.55mm relief pockets in the 1.2mm plate) —
  researched:**
  - JLCPCB: NO published controlled-depth milling service. Full
    capabilities fetch (2026-10-23): outline options are V-scoring
    (±0.4mm) and CNC routing (±0.1/0.2mm); no Z-axis/depth row anywhere.
  - PCBWay: Z-Axis Milling IS documented — help page (updated
    2026-02-02) lists "Pocket milling" among applications, "in general,
    milling does not require any additional charges", contours drawn as
    0.2mm lines; capabilities page states "depth tolerance is
    controlled 0.15mm". Depth math for us: order **0.70mm nominal** →
    delivered 0.55–0.85 (±0.15) — the minimum still clears the
    worst-case diode, floor stays 0.35–0.65mm; the coupon calipers the
    delivered depth before any plate batch. Quote-time questions: does
    PCBWay accept a no-copper FR4 plate board, and confirm the "refrain
    from milling the copper" rule is moot (bare FR4, no copper layers).
  - Laser route (plan A, unchanged): plain laser CUTTING cannot make
    the pockets, but controlled-depth laser ENGRAVING on FR4/G10 is
    standard laser-shop work — the coupon-first procedure stays; no
    major online service confirmed for depth engraving, so plan A =
    the laser shop already in BOM_ORDER (ask-first), plan B = PCBWay
    Z-milling with the 0.70mm-nominal spec.
- Net effect on the order gates: (1) coupon — STANDS (now also verifies
  delivered pocket depth if PCBWay is chosen); (2) partial-depth
  confirm — RESEARCHED, reduces to the quote-time ask with the PCBWay
  fallback documented; (3) copper-edge confirm — DROPPED (documented
  pass at 0.2mm tab-route rule); (4) Bluetooth-SIG — DROPPED (owner
  decision). Sources: jlcpcb.com/blog/pcb-board-outline;
  jlcpcb.com/blog/pcb-layout-process-guide-2026-mastering-pcb-design;
  jlcpcb.com/capabilities/pcb-capabilities; pcbway.com/helpcenter/
  ordering_parameter_instruction/What_is_PCB_Z_Axis_Milling_.html;
  pcbway.com/capabilities.html.

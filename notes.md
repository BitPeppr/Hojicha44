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

The halves differ **only** in the TX/RX swap, which is the cost of a straight
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
3. **USB notch** — 11×5.4mm at each `usb` point; the module's USB shell must
   overhang that edge.
4. **Diode placement.** The Choc hotswap courtyard is ±7.75mm but **pad 2 sits
   at x=8.5**, outside it. A SOD-123 centred 7.62mm to the right (where the
   schematic draws it) trips courtyard overlap. All 44 diodes go in the 3.55mm
   inter-key gaps, rotated 90°.
5. **Cell choice.** The layout config moved to a 301230 (3×12×30) — note the
   spec still describes a 302030 (20mm wide, wider than the 18mm module).
   Reconcile the two before ordering cells.
6. **`decisions/` and `experiments/proposed/` are empty** — the roadmap's
   Phase 0/1 artefacts were never written down.

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

Both blockers from the review + `fix.md` are applied, regenerated and
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

- The routing decisions in `fix.md` §8 (layers, TRRS vs 4-pin JST).
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
needs full chip erase on first flash). Bigger correction: **no TX/RX
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

A second review (`fix.md`, untracked) was verified item by item against the
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

Final: Left 54 fp / 48 nets / 111 edge segs / 446 copper items, Right
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
  fix.md §5.3 now carries the exact verified commands (explicit `-l` layer
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

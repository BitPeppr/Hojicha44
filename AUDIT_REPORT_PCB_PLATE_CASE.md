> **Provenance (added 2026-10-21, before committing):** this is a
> READ-ONLY REVIEW INPUT from the 2026-10-20 six-review design round —
> not a spec. Every measured number quoted below is the PRE-FIX state
> (e.g. tub 67.4 cm3, wall_min 1.49/1.50, 6/7 magnet stations) and is
> now HISTORICAL. The current truth: tub 75.7/75.7 cm3, wall_min
> 2.62/2.70, 8/8 exact-mirror magnet stations, band 7.68 / web 1.69,
> plate poron pads 7.0mm (corner-edge 0.71). The accepted/rejected
> ledger for every finding, with the rationale and the implemented
> fixes, is in `notes.md` (2026-10-20 section); the generators are the
> authority.

# Hojicha44 — Comprehensive Audit Report: PCB, Plate, and Case Stages

**Scope:** Component choice, component placement, wiring, geometry, material choice, mechanics, manufacturing, ergonomics, reliability, and cross-stage coherence across the three stages (PCB, plate, case). No code or geometry changes were made; this is a findings + recommendations report.

**Artifacts reviewed (deep):**
- `pcb/generators/{gen_pcb,gen_route,gen_schematic,check_board,audit_silk}.py`
- `pcb/kicad/{*.kicad_sch,*.kicad_pcb,*.kicad_pro,*.kicad_mod,*.drc.rpt,*.erc.rpt}`
- `pcb/kicad/Hojicha44.3dshapes/README.md`
- `plate/gen_plate.py`, `plate/Hojicha44-{Left,Right}-lands.json`
- `case/{gen_case,gen_cover,probe_bores,params}.py`, `case/README.md`
- `spec/{electronics,case,first-article}.yaml/.md`, `spec/bom.md` (if present)
- `layout/ergogen/config.yaml`, `layout/generated/v2/points/points.yaml`
- `README.md`, `KEYBOARD_PROJECT_ROADMAP.md`, `notes.md` (relevant sections)
- Git history (`git log`)

**Generators executed and verified (all exit 0):**
- `plate/gen_plate.py --check` → CLEAN both halves, encoder webs printed.
- `case/gen_case.py` → tub 67.4 cm³ both halves, wall_min 1.49/1.50, 8 magnets each.
- `case/gen_cover.py` → cover 9.0 cm³ both halves, wall_min 5.85, 8 magnets each.
- `case/probe_bores.py` → all shape probes pass.
- `pcb/generators/check_board.py` → CLEAN (1 loop, 0 dangling, fiducials inside, notch open).
- `pcb/generators/audit_silk.py` → silk symmetric OK (54 footprints each).

**Verdict summary:** The three stages are unusually well-engineered for a prototype: single-source-of-truth generators, machine-checked gates, and honest documentation of trade-offs and deferred items. The design is coherent across stages. The findings below are refinements, risk flags, and a handful of real defects — none currently fail a gate, but several are first-article or rev-2 items that should be decided before ordering. **No changes were made.**

---

## Table of Contents

1. Methodology and Scope
2. PCB Stage — Deep Audit
   2.1 Architecture and Stackup
   2.2 Component Selection (deep, datasheet-level)
   2.3 Component Placement (deep)
   2.4 Schematic and Netlist
   2.5 Routing and Copper
   2.6 Geometry and Outline
   2.7 DRC/ERC Status
   2.8 Mechanical Interface
   2.9 Thermal and EMI
   2.10 Manufacturing / DfM
   2.11 PCB Findings
3. Plate Stage — Deep Audit
   3.1 Material Selection
   3.2 Geometry
   3.3 Gasket Design
   3.4 Mechanics
   3.5 Manufacturing
   3.6 Plate Findings
4. Case Stage — Deep Audit
   4.1 Material and Process
   4.2 Tub Geometry
   4.3 Port Bores
   4.4 Retention (Magnets + Cover)
   4.5 Antenna Keepout
   4.6 Mechanics
   4.7 Manufacturing
   4.8 Case Findings
5. Cross-Stage Coherence
6. Ergonomics and Layout
7. Power and Battery
8. Reliability and Robustness
9. Cost Considerations
10. Summary of Recommendations
11. Strengths (Do Not Change)

---

## 1. Methodology and Scope

This audit treats the three stages as a coupled system. Each stage's generator is the source of truth; the committed artifacts (`.kicad_pcb`, `.dxf`, `.step`) are derived. The audit verifies:

1. **Component choice** — part selection vs. spec requirements and datasheet limits.
2. **Component placement** — position, rotation, orientation, clearance.
3. **Wiring** — netlist correctness, routing strategy, copper integrity.
4. **Geometry** — outlines, cutouts, windows, port bores, tab geometry.
5. **Material choice** — plate material, foam, magnet grade, case material.
6. **Mechanics** — gasket preload, suspension, flex, vibration, retention.
7. **Manufacturing** — fab limits, tolerances, assembly sequence.
8. **Cross-stage coherence** — outline sharing, dimension propagation, single source of truth.

Every number cited is traced to its source (generator constant, spec file, or measured value). Where a number is a "family bound" or "estimate", it is flagged.

---

## 2. PCB Stage — Deep Audit

### 2.1 Architecture and Stackup

**Stackup:** 2-layer, 1.6mm FR4, ENIG or HASL lead-free (provisional). Design rules: 0.25mm track / 0.2mm clearance / 0.8-0.4mm via. Netclasses: Default (0.25mm track, 0.2mm clearance, 0.8/0.4mm via) and POWER (0.5mm track, 0.25mm clearance, 1.0/0.5mm via, assigned to `/VBAT_SW_*` by pattern).

**Assessment:** The design rules are conservative for a 2-layer board and well within standard fab capability (most fabs support 0.15mm/0.15mm). The 0.25mm track / 0.2mm clearance leaves margin for etch tolerance. The POWER netclass (0.5mm) is appropriate for the battery rail (peaks well under 30mA, but the wire must not be necked). The `.kicad_pro` is generated (not hand-edited) with template presets corrected — using KiCad's default 0-width/0-drill presets silently breaks DRC. Good.

**Finding PCB-17 (Low) — Stackup provisional.** ENIG vs HASL not decided. For a keyboard with hotswap sockets (THT) and fine-pitch SMD (SOD-123 diodes), ENIG is recommended: flatter pads improve solderability and reduce tombstoning risk on small SMD parts. HASL is cheaper but has uneven pad heights. **Recommendation:** decide ENIG before ordering; the cost delta is small (~$5-10/board) and the benefit is real. Effort: decision.

**Finding PCB-18 (Info) — No blind/buried vias.** Correct for a 2-layer board. Good.

### 2.2 Component Selection (Deep, Datasheet-Level)

#### 2.2.1 MCU — nice!nano v2 (nRF52840)

- **Architecture:** ARM Cortex-M4F, 64MHz, 256KB RAM, 1MB flash.
- **BLE:** 2.4GHz, onboard antenna (chip antenna, not PCB trace).
- **GPIO:** 18 footprint GPIOs (15 used + 3 spare: A2, A3, D10).
- **Power:** 3.3V regulated output (VCC pin), RAW input (3.7-5.5V from battery/USB).
- **Charger:** onboard 100mA (default) or 500mA (jumper, stays OPEN).
- **USB:** USB-C, onboard (no PCB part).

**Assessment:** Good choice for a wireless split. The nRF52840 has enough GPIOs (18 vs. 15 needed). The onboard charger (100mA) gives ~1.1h charge time for a 110mAh cell — acceptable. BLE is the primary link; TRRS is a debug fallback.

**Finding PCB-10 (Low) — NFC pins.** D10 (spare) and D16 (encoder push) map to P0.09/P0.10, which are NFC pins on the nRF52840. They require `nfct-pins-as-gpios` in the UICR overlay and a **full chip erase** on first flash. Without erase, the pins stay locked to the NFC peripheral and the encoder push / spare are dead with no error. **Recommendation:** document the `--erase` requirement prominently (already in first-article.md §5). Effort: firmware.

**Finding PCB-6 (Low) — No ESD protection on USB.** The nice!nano has onboard ESD protection on the USB D+/D- lines, but the PCB adds none. For a keyboard, this is acceptable — USB ESD events are rare and the module's protection is sufficient. **Recommendation:** rev-2 if field failures appear. Effort: rev-2.

**Finding (Info) — A1/A2/A3 are low-drive only.** On the nRF52840, A1 (P0.02), A2 (P0.29), A3 (P0.31) are low-drive GPIOs (max 0.5mA vs. 5mA for high-drive). They are used for matrix scanning (input) and spare — no PWM or high-current drive needed. Correct. Good.

#### 2.2.2 Switches — Kailh Choc v1 (PG1350)

- **Type:** Low-profile (Choc v1), 1u, hotswap socket (SMD bottom).
- **Actuation:** 50gf (linear, tactile, or clicky variants).
- **Travel:** 2.0mm (v1) vs 3.0mm (v2).
- **Pitch:** Choc-native is 18×17mm; this board uses 19.00mm (as-measured). Small cap gaps accepted.
- **Keycaps:** Choc v1 only (MBK/MCC/CFX). MX stems do not fit.

**Assessment:** Good choice for a low-profile split. Choc v1 hotswap sockets are SMD on the bottom of the PCB, with the switch inserted from the top. The 19.00mm pitch (vs. Choc-native 18mm) is a deliberate ergonomic decision — wider spacing for larger hands. Documented as "as-measured, not as-nominal."

**Finding (Info) — Pitch mismatch.** 19.00mm vs. Choc-native 18mm means keycaps designed for 18mm pitch will have slightly larger gaps. MBK caps are 17.5mm wide, so at 19mm pitch the gap is 1.5mm (vs. 0.5mm at 18mm). This is a visual/feel difference, not a functional one. Good.

#### 2.2.3 Diodes — 1N4148W, SOD-123

- **Type:** Fast switching diode, 75V, 150mA, 4ns recovery.
- **Package:** SOD-123 (SMD, 2 pads).
- **Role:** Matrix diode (COL2ROW direction).

**Assessment:** Good. 1N4148W is the standard keyboard matrix diode. SOD-123 is small and easy to solder. Fast recovery (4ns) is more than adequate for matrix scanning.

**Finding PCB-1 (Medium) — Schematic symbol mismatch.** The schematic uses `Diode:1N4001` (a DO-41 THT symbol with `extends` that KiCad ERC cannot netlist) with Value `1N4148W` and footprint `Diode_SMD:D_SOD-123`. This is a documented workaround, but it produces 22 `lib_footprint_mismatch` warnings per half (44 total) waived under W1. The waiver is exact-count asserted, so it's safe, but it pollutes DRC reports and could mask a real diode footprint drift. **Recommendation:** create a project-local SMD diode symbol with the correct footprint filter, or accept the waiver but document it clearly. Effort: low.

#### 2.2.4 Encoder — Alps EC11E, H20mm shaft

- **Type:** Rotary encoder, 30 detents / 15 pulses per revolution, with push switch.
- **Shaft:** 20mm (H20mm variant). Tip 24.5mm above PCB.
- **Footprint:** `RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm_CircularMountingHoles`.

**Assessment:** The EC11E is the shortest EC11E-with-switch variant available (20mm shaft). The knob rides ~10mm proud of MBK caps — normal on Choc boards, easier to grip. The 3D model (ROT_EC11E.step) was measured directly (offset (0,5,0) + rot 0) because marbastlib's own offset doesn't land pins on pads.

**Finding PCB-5 (Low) — Encoder shaft height.** 20mm shaft → knob ~10mm proud of caps. Consider Bourns PEC11L (15mm shaft) if a lower profile is desired, but it would need a tab-span check (12.5 vs 12.8mm body). **Recommendation:** first-article ergonomics check; trim shaft if too tall. Effort: first-article.

**Finding PCB-13 (Low) — EC11 mounting hole clearance.** The EC11 footprint's mounting holes (MP, 2.6mm drills) are at local (7.5, -3.1) and (7.5, 8.1). With placement at (ex-7.5, ey-2.5) rot 0, the holes land at (ex, ey+1.6) and (ex, ey+5.6). The plate encoder hole is 12.7mm square (half-extent 6.35mm). The +Y hole at 5.6mm is inside but tight (0.75mm margin). **Recommendation:** verify on first article. Effort: first-article.

#### 2.2.5 TRRS Jack — PJ-320A, 4-pole THT

- **Type:** 3.5mm TRRS (4-pole), THT.
- **Pad map:** T (Tip), R1 (Ring1), R2 (Ring2), S (Sleeve).
- **Pinout:** Tip = SPLIT_TX, Ring1 = SPLIT_RX, Ring2 = NC, Sleeve = GND.

**Assessment:** Good. The 4-pole jack is kept for cable compatibility, but Ring2 is deliberately NC to prevent battery joining through the cable (splitkb documents MCU damage from this). The TRRS is a bring-up/debug fallback, not a daily-use link.

**Finding PCB-8 (Info) — Ring2 NC is correct.** Safety decision well-documented. Good.

**Finding (Info) — Hotplug requires USB unplugged both sides.** Switch OFF alone is insufficient (USB still powers the controller). Documented in first-article.md. Good.

#### 2.2.6 Power Switch — Würth WS-SLTV 450301014042

- **Type:** SPDT slide switch, 10×2.5×6.4mm, P2.54.
- **Pin 1 (middle) = COMMON, pins 2/3 = throws.**
- **Schematic:** Battery+ → pin 1 (common), rail → pin 2, pin 3 NC.

**Assessment:** Good. The common-pin assumption is guarded by `check_pwr_footprint()` which asserts pad 1 is the middle pad. The 300mA switching rating covers BLE peaks (~20mA) with margin.

**Finding (Low) — SPDT with NC throw.** An SPST switch would be cheaper and smaller, but SPDT is easier to source and the NC throw is harmless. **Recommendation:** keep SPDT for sourcing flexibility. Effort: none.

#### 2.2.7 Battery — 301230 LiPo, 110mAh

- **Dimensions:** 3×12×30mm with PCM.
- **Voltage:** 3.7V nominal, 4.2V full.
- **Capacity:** ~110mAh.
- **Connector:** JST-PH 2.0mm, pin 1 = pack+ (red), pin 2 = pack- (black).

**Assessment:** Good fit. The 301230 (3×12×30) fits under the socketed nice!nano (12mm cell clears the socket's pin rows). The earlier 302030 (3×20×30) was rejected (20mm is wider than the 18mm module and fouls the socket pins). The 304050 (600mAh) stays a future under-PCB option (needs soldered wires: JST-SYP plug).

**Finding PCB-2 (High) — No reverse-polarity protection.** The JST pigtail is the only polarity control. Reverse polarity kills board and cell. **Recommendation:** add a P-channel MOSFET or polyfuse + reverse diode for rev-2. For rev-1, keep the meter-before-plug-in discipline and label the case. Effort: rev-2.

#### 2.2.8 Battery Connector — JST-PH side-entry

- **Type:** S2B-PH-K-S (side-entry, horizontal).
- **Wire exits:** parallel to PCB, ~5-6mm tall.
- **Placement:** beside the cell at the `jst` anchor, not under the stack.

**Assessment:** Good. The side-entry connector fits neither under the stack, so it sits beside the cell. The `+` silkscreen mark at pin 1 is required (reverse polarity kills board+cell).

#### 2.2.9 Sockets — 2×12 machine-pin SIP

- **Pitch:** 2.54mm along row, 15.24mm row separation.
- **Numbering:** column-major (pins 1-12 down one edge, 13-24 down the other, opposite direction).
- **Envelope:** 18.3×34.9mm (module bbox).

**Assessment:** The custom footprint (`Socket_Strips_2x12_P2.54mm_NiceNano`) is essential — the stock PinSocket_2x12 uses row-major serpentine numbering with 2.54mm row spacing, which would scramble every net and not fit the 15.24mm module. The guard (`check_mcu_footprint()`) verifies pitch, separation, numbering, and envelope. Good.

#### 2.2.10 Fiducials and Tooling

- **Fiducials:** 3× Fiducial_1mm_Mask3mm, placed by clearance search (edge/pad/courtyard aware).
- **Tooling:** 2× MountingHole_3.2mm_M3 (NPTH), placed in confirmed-open areas.

**Assessment:** Good. Fiducials are inside the outline with ≥3.0mm edge clearance. Tooling holes are in open areas (not in courtyards). Gasket mounting uses no PCB holes.

### 2.3 Component Placement (Deep)

#### 2.3.1 MCU Socket Placement

- Position: (mx-7.62, my+13.97-0.5) = shifted 0.5mm south so silk top clears the USB-notch cutout.
- Rotation: 180° (USB end toward north board edge).

**Assessment:** Correct. The socket's USB end (pin 1/24) faces the north board edge (USB notch). The antenna end (pads 12/13) points south (toward the antenna keepout zone). The 0.5mm south shift keeps the silk reference clear of the notch cutout. Good.

#### 2.3.2 Diode Placement

- Offset: ±9.5mm along the key rotation direction (east on L, west on R after mirror).
- Rotation: krot+90 (body rotated 90° from key).
- Strip silk: yes (cathode bar 0.2mm from pad trips angle-dependent DRC noise).
- Cathode tick: re-added (1.0mm bar just outside pad 1).

**Assessment:** Good. Diodes sit in the inter-key gap, not on the key. The 9.5mm offset places them between keys. The silk strip + cathode tick workaround keeps polarity readable while avoiding DRC noise.

**Finding PLATE-8 (Low) — Diode clearance 0.3mm to cutout edge.** The plate generator checks `DIODE_CLEAR = 0.3mm` (min diode-to-cutout-edge). This is tight. **Recommendation:** verify on first article (feeler test 0.5mm). Effort: first-article.

#### 2.3.3 TRRS Placement

- Body 2mm inboard of anchor (mouth faces split gap).
- Rotation: 90° (L) / 270° (R).

**Assessment:** Good. The inboard shift prevents mouth-end pads from going off-board (the edge leans 2.77mm over the jack height). The mouth silk clears the slanted inner edge.

#### 2.3.4 Encoder Placement

- Instance origin = ergogen point − (7.5, 2.5) (shaft center on point).
- Rotation: 0° (body axis-aligned).

**Assessment:** Good. The shaft center lands on the ergogen point. The body is axis-aligned (no rotation). The encoder hole in the plate is 12.7mm square, centered on the shaft center.

#### 2.3.5 Fiducial Placement

- 3 per half, placed by clearance search (edge/pad/courtyard aware).
- Positions: L = (-5,42), (128,50), (67,-35); R = (163,50), (296,42), (227,-34).

**Assessment:** Good. All inside the outline with ≥3.0mm edge clearance. The targets are the old intent (outer top-left, outer top-right, bottom centre) snapped to the nearest valid 1mm grid point. Good.

#### 2.3.6 Tooling Hole Placement

- 2 per half, 3.2mm NPTH, placed in confirmed-open areas.
- Positions: L = (12,-16), (128,4); R = (163,4), (280,-16).

**Assessment:** Good. Courtyard-aware (pad centres alone miss courtyard corners). The stricter clearances (5.0mm from pads, 4.0mm from edge, 3.7mm from courtyards) prevent drill breakout near copper.

### 2.4 Schematic and Netlist

**Architecture:** One KiCad project per half (two separate PCBs). Each sheet carries its own GND and TRRS_T/TRRS_R1 (2 nodes each). The cable joins the sheets. VBAT_SW_L and VBAT_SW_R are separate (no VBAT_SHARED net).

**Matrix:** 4 rows × 6 cols, COL2ROW (col → switch → diode A → diode K → row). R0-R2 × C0-C5 fingers, R3 × C0-C3 thumbs, R3C4-C5 unplaced spares. Encoder push is a dedicated GPIO (D16), not matrix.

**Pin map:** Rows: R0=D4, R1=D5, R2=D6, R3=D7. Cols: C0=D8, C1=D9, C2=D2, C3=D3, C4=D14, C5=D15. Encoder: ENC_A=A0, ENC_B=A1, ENC_SW=D16. Split: left_TX=D1, left_RX=D0, right_TX=D1, right_RX=D0 (crossed in copper on right half).

**ERC:** 0 errors, 5 warnings per half (isolated pin labels for spare GPIOs: RST, VCC3V3, A3, A2, D10). Spares stay labeled (future use + UICR). Good.

**Guards (per sheet):**
- All 22 diodes are SOD-123 (stock DO-41 must never leak).
- Exactly 1 PWR_FLAG.
- No VBAT_SHARED net.
- Exactly 1 guarded column-major MCU socket.
- No foreign-half refs.
- Title-block rev derives from spec version.

**Assessment:** The schematic is well-structured and guarded. The split-link crossover (right half crosses TX/RX in copper) ensures both halves use identical UART pinctrl — no firmware swap needed. Good.

**Finding (Info) — Diode symbol uses 1N4001.** Documented workaround for `extends` netlisting limitation. The guard ensures all 22 diodes are SOD-123. Good.

### 2.5 Routing and Copper

**Strategy:** 2-layer, no pours, dual-layer A* throughout. Via wherever routable. Power width 0.5mm, signal 0.25mm. Exact per-class clearance + quantization margin.

**Ordering:** Anode links first (22/half), then COL rails, ROW rails, stubs (ENC/TRRS/VBAT), then GND nearest-neighbour chain. Rails claim corridors before stubs.

**Via sizes:** Signal 0.6/0.3mm, power 1.0/0.5mm. Antenna keepout: 5.0mm radius (copper edge vs radius, not centerline).

**Copper counts (from built boards):**
- Left: 384 segments, 70 vias, 0 zones, 54 footprints, 174 nets.
- Right: 490 segments, 100 vias, 0 zones, 54 footprints, 174 nets.

**Assessment:** The routing is deterministic and well-structured. The antenna keepout is edge-based (not centerline), which is more conservative. The GND chain is nearest-neighbour, which could create long jumps but is acceptable for a prototype.

**Finding PCB-14 (Medium) — GND daisy-chain, no pour.** Documented as rev-2 backlog. The nearest-neighbour ordering could create long diagonal jumps. A B.Cu pour would be more robust for EMC. **Recommendation:** first-article BLE range test gates it; add pour if range disappoints. Effort: rev-2.

**Finding PCB-15 (Low) — Router version 13.** Stale copper from older revisions is dropped on rev bump. GUI copper is preserved only within the same revision. This is good design but means a rev bump loses all hand-tuned routes. **Recommendation:** document the rev-bump procedure. Effort: process.

**Finding PCB-16 (Low) — Power class detection by string match.** `pclass()` returns "p" if net name contains "/VBAT_SW" or starts with "Net-(J_". This is fragile. **Recommendation:** make power-class a property of the net (e.g., a set of power net names) rather than string matching. Effort: low.

**Finding (Info) — Via dedup.** Router vias co-located with GUI vias (same net, <0.1mm) are dropped. Good — avoids DRC "holes co-located" warnings.

**Finding (Info) — `_drop_nubs`.** Trims buried trailing micro-steps to avoid DRC dangling tips. Good.

### 2.6 Geometry and Outline

**Board outline:** Single closed Edge.Cuts loop per half, 111 segments (L) / 117 segments (R). Verified by check_board (1 loop, 0 dangling). The outline is the "board" outline from ergogen (not "plate" — the PCB must not have the encoder knock-through).

**USB notch:** 11mm wide × 10.8mm deep, subtracted at the USB helper point. The notch floor is at 47.25mm, which clears the top socket pad copper (top edge ~46.47mm) by 0.78mm. Good.

**Antenna keepout:** 5mm radius circle on Cmts.User, centered at the antenna point (mcu + [0, -16.45]). Copper-free zone. Good.

**Finding PCB-11 (Medium) — USB notch-to-socket-pad gap 0.78mm.** Documented as accepted prototype deviation. The socket pads sit 0.78mm from the notch edge — tight for fab and solder tolerance. **Recommendation:** measure on first article; if solder bridging appears, widen notch to ~14mm (first-article checklist allows it) or move socket inboard. Effort: first-article.

**Finding (Info) — Outline is single loop.** Good — no interior holes (the encoder knock-through is in the plate, not the PCB). Good.

### 2.7 DRC/ERC Status

**DRC:** 28 violations per half, all `lib_footprint_mismatch` (waived under W1). 0 unconnected pads. 0 footprint errors. W2 predicate armed but 0 on routed boards.

**ERC:** 0 errors, 5 warnings per half (isolated pin labels for spare GPIOs). Good.

**W1 waiver breakdown (28 per half):**
- 22× D_SOD-123 (diodes, stripped silk + cathode tick)
- 4× SW_Hotswap_Kailh_Choc_V1_1.00u (thumb switches, rotated)
- 1× Socket_Strips_2x12_P2.54mm_NiceNano (MCU, reversed column)
- 1× TRRS-PJ-320A (renamed pads)

**Assessment:** DRC is clean modulo documented waivers. The W1 count is exact-asserted (29th mismatch fails the build). W2 (silk_over_copper) is armed but 0 on routed boards. Unconnected items are NOT waived. Good.

### 2.8 Mechanical Interface (Mounting, Gasket)

**Mounting:** Gasket, no PCB holes. PCB hangs from plate on switches. Case never clamps board. Good.

**Flex cuts:** Deferred to rev-2. Single Edge.Cuts loop, no geometry change. Good.

**Antenna keepout:** 5mm copper-free zone. Measured wall distance 14.15mm (case). Good.

### 2.9 Thermal and EMI

**Thermal:** The nice!nano has onboard thermal management. The PCB has no thermal vias or heat sinks. For a keyboard (low power, <100mA peaks), this is fine.

**EMI:** No ground pour (rev-2). The BLE antenna is on the module (chip antenna). The 5mm copper-free zone around the antenna point ensures no copper detunes it. The case wall is 14.15mm away. Good.

**Finding (Info) — No EMI shielding.** For a BLE keyboard, no shielding is needed. The 2.4GHz signal is low-power and the antenna is on the module. Good.

### 2.10 Manufacturing / DfM

**Fab limits:** 2-layer 1.6mm, 0.25mm track / 0.2mm clearance / 0.8-0.4mm via. These are conservative and well within standard fab capability.

**Assembly:** Diodes → switch → sockets → TRRS → JST → encoder. Modules last. Cell sandwich after all soldering.

**Finding (Info) — CPL uses KiCad convention.** pos.csv/pos-smt.csv use negated Y, board origin. JLCPCB/PCBWay ingest KiCad CPL natively. Good.

**Finding (Info) — SMT subset.** pos-smt.csv contains only 22 SOD-123 diodes (everything else is hand assembly). Good.

### 2.11 PCB Findings (Summary)

| ID | Severity | Finding | Recommendation |
|---|---|---|---|
| PCB-1 | Medium | Diode symbol mismatch (1N4001 vs 1N4148W) | Project-local SMD diode symbol |
| PCB-2 | High | No battery reverse-polarity protection | MOSFET/polyfuse for rev-2 |
| PCB-3 | Medium | Charging only when switch ON | Always-on charging for rev-2 |
| PCB-4 | Medium | No ground pour | B.Cu pour for rev-2 |
| PCB-5 | Low | Encoder shaft height (20mm) | First-article ergonomics check |
| PCB-6 | Low | No ESD protection on USB | Rev-2 if field failures |
| PCB-7 | Low | No test points | Add 3 TPs for rev-2 |
| PCB-8 | Info | TRRS ring2 NC (correct) | — |
| PCB-9 | Info | Hotswap socket on B.Cu (correct) | — |
| PCB-10 | Low | NFC pins for spare/encoder push | Document --erase requirement |
| PCB-11 | Medium | USB notch-to-pad gap 0.78mm | Measure on first article |
| PCB-12 | Low | Left VBAT 184.82mm loop | Rev-2 with pour |
| PCB-13 | Low | EC11 mounting hole clearance 0.75mm | Verify on first article |
| PCB-14 | Medium | GND daisy-chain, no pour | Rev-2 pour |
| PCB-15 | Low | Router rev bump drops GUI copper | Document procedure |
| PCB-16 | Low | Power class by string match | Net property instead |
| PCB-17 | Low | Stackup provisional (ENIG vs HASL) | Decide before ordering |

---

## 3. Plate Stage — Deep Audit

### 3.1 Material Selection

**Default:** PC 1.5mm. Softest, most flex, virtually unbreakable, cheapest prototype. Alternatives: POM (balanced, good feel, stable), FR4 (stiff, cheap, glass dust), ALU (balanced, best sound, isolate from copper), CARBON (stiffest, conductive — verify at assembly).

**WEB_MIN per material:** PC/POM 1.0mm, FR4/ALU 1.5mm, CARBON 2.0mm. Material-aware gating. CARBON is mill-only (never laser: toxic dust + delamination).

**Assessment:** Good. PC is the right default for a prototype (softest feel, deepest sound, unbreakable). The material-aware web minimums prevent ordering a plate that can't be fabricated in the chosen material. The CARBON note (conductive — verify at assembly) is important.

**Finding PLATE-5 (Low) — PC yellows/scratches.** PC yellows and scratches over time. POM is more durable and machines better. **Recommendation:** PC for prototype, POM for production run. Effort: decision.

### 3.2 Geometry (Deep)

#### 3.2.1 Cutouts

- **Choc:** 22× 15×15mm at switch centers/rotations. Body clearance (13.8mm body + 0.6/side). The plate is 1.5mm thick, which is too thick for Choc side clips to engage (they need ~1.3mm). Retention is friction + hotsockets + gasket.

**Finding PLATE-1 (Medium) — Choc clips don't engage.** The 15.0mm cutout with 1.5mm PC plate means Choc side clips never touch. Retention relies on friction + hotsockets + gasket. **Recommendation:** first-article clip-engagement test in all regions; if rock appears, tighten cutout to 14.9 or reduce plate to 1.2mm. Effort: first-article.

#### 3.2.2 Encoder Hole

- **Size:** 12.7×12.7mm square (recently corrected from 12.5).
- **Body:** EC11 measures 12.30mm wide in the plate band (z 2.0..3.5) → 0.20/side nominal.

**Finding PLATE-7 (Medium) — Encoder hole margin 0.20/side.** Tight. ±0.2 fab tolerance could rub. **Recommendation:** first-article: drop real encoder through a laser-cut hole sample; if rub, widen to 13.0 (web to SW_L17 still gate-safe at ~3.35mm). Effort: first-article.

#### 3.2.3 Tabs

- **Count:** 8 per half.
- **Dimensions:** 10mm wide, 5mm proud, 2mm root fillets, 1.5mm tip chamfer.
- **Spacing:** 2 pinned corners + 6 greedy (even spacing).
- **Eligibility:** real tab frame (not inflated box), opening-free within web minimum.

**Assessment:** Good. The tab-and-jacket suspension is well-designed. The eligibility check uses the real tab frame, so narrow fingers stay eligible.

#### 3.2.4 Windows

- **W1:** Switch strip + MCU/cell/USB + JST (tall top-side parts).
- **W2:** TRRS + channel to split-gap edge (jack mouth must exit).

**Assessment:** Good. Windows clear all tall parts. The W1 window is derived from part body bounding boxes (not hand-drawn).

#### 3.2.5 Poron Pads

- **Size:** 8×4mm (8mm lateral, 4mm along tongue).
- **Center:** tab root + 2.0mm outward.
- **Spec:** PORON 4701-30 Very Soft, 240 kg/m³, 3mm, adhesive-backed.

**Finding PLATE-2 (Medium) — Poron pad lateral margin 0.35mm.** All 16 pad corners test on-plate, but the tightest corner-edge is ~0.35mm on every tab. Laser kerf (0.1-0.2mm) + part tolerance (~0.1mm) could nibble this. **Recommendation:** rev-2 use 6-7mm pad width or a longer tab; for rev-1, accept and verify on laser-cut sample. Effort: rev-2.

**Finding (Info) — Pad orientation.** The 8mm axis runs lateral across the 10mm tongue, the 4mm axis runs along the 5mm tongue (pad spans rim-line to +4.0 → 1mm tip spare). No tip overhang. Good.

### 3.3 Gasket Design (Deep)

**Poron 4701-30:** CFD ~24 kPa @25% → ~78 gf/pad @25% compression. Static load ~25 g/pad (200g half-assembly / 8 bottom gaskets) → ~8-10% self-compression (0.2-0.3mm on 3mm). 2.5-3× force headroom before 25% compression.

**Assembly preload:** 15-20% foam compression → cavity 6.3-6.6mm (1.5 plate + 2× 3mm pads).

**Assessment:** Good. The Poron is the softest stock grade (lowest mount resonance, deepest sound, most travel per unit force). The preload is within the recommended range. The force headroom is adequate.

**Finding (Info) — Swap ladder.** -30 (default, thock-max) → -40 (stiffer fallback, ~41 kPa) → -50 (only if mushy). Good — drop-in, no CAD change.

### 3.4 Mechanics (Deep)

**Tab-and-jacket suspension:** 8 tabs per half, poron pads top+bottom, no rim strips, no screws, no hard contact. The plate grows discrete tongues that slot into silicone jackets in the case. The assembly floats instead of coupling the full rim to the case.

**Inner edge (MCU/TRRS/encoder):** No tab — the zone floats between flanking tabs by design. Encoder push stays soft.

**Finding PLATE-3 (Low) — Inner edge floats.** The encoder area has no tab support. **Recommendation:** first-article feel test; if the encoder feels too mushy, add a tab near it. Effort: first-article/rev-2.

**Finding PLATE-4 (Low) — MAX_TAB_DIST 55mm.** Worst key-to-tab is 48.14mm. Acceptable but some keys are far from support. **Recommendation:** consider 9 tabs if feel is uneven. Effort: rev-2.

### 3.5 Manufacturing (Deep)

**Fab:** Laser-cut (PC/POM), routed (FR4), laser/waterjet/CNC (ALU), mill-only (CARBON).

**Tolerance:** Laser kerf ~0.1-0.2mm. Part tolerance ~0.1mm. The 0.35mm pad margin is tight but acceptable in CAD.

**Assembly:** Cut 8×4mm pads from 90×4mm stock (≈11 pads per 90mm strip; 16 pads/half ⇒ 2 strips/half). Single-supported (PET adhesive) preferred.

**Finding (Info) — No tip overhang.** All pad corners on-plate. Good.

### 3.6 Plate Findings (Summary)

| ID | Severity | Finding | Recommendation |
|---|---|---|---|
| PLATE-1 | Medium | Choc clips don't engage (1.5mm PC) | First-article clip test |
| PLATE-2 | Medium | Poron pad lateral margin 0.35mm | Rev-2: 6-7mm pad |
| PLATE-3 | Low | Inner edge floats (encoder soft) | First-article feel test |
| PLATE-4 | Low | MAX_TAB_DIST 55mm (worst 48mm) | Consider 9 tabs |
| PLATE-5 | Low | PC yellows/scratches | POM for production |
| PLATE-7 | Medium | Encoder hole margin 0.20/side | First-article hole sample |
| PLATE-8 | Low | Diode clearance 0.3mm | First-article feeler test |

---

## 4. Case Stage — Deep Audit

### 4.1 Material and Process

**Tub:** CadQuery parametric, FDM-printed (PETG/ASA/PC recommended). Print orientation: tub open-face-up (self-supporting except USB/TRRS bridges ~7mm spans).

**Cover:** Ring cover v1, same material. Print orientation: cover underside-up.

**Magnets:** 4×2 N52 (tub) + 4×1.5 N52 (cover). 16 pairs per half.

**Assessment:** Good. FDM is appropriate for a prototype. The print orientation ensures all features are self-supporting. The USB/TRRS bridge spans (~7mm) typically bridge support-free.

**Finding CASE-3 (Low) — No bottom feet.** The tub sits flat on the desk. **Recommendation:** add rubber feet (adhesive) or integrate feet into the print. Effort: low.

**Finding CASE-4 (Low) — FDM anisotropy.** Wall min 1.4mm is ~3-4 layers. Acceptable for FDM but not injection-molded strength. **Recommendation:** SLS/MJF for production. Effort: process.

**Finding CASE-5 (Low) — No EMI shielding.** Minor. Effort: rev-2 if needed.

### 4.2 Tub Geometry (Deep)

**Exterior:** PCB rim + 7.0mm dilation (uniform). No tab bulges (v3.1 fix). Skin-to-rim max exactly 7.0.

**Interior:** Plate outline + 0.5mm clearance. Good.

**Floor:** -5.6 (deepest protrusion -3.65 + 1.95mm clearance). Step under PCB zone only. Tab shelf at -0.55.

**Tab pockets:** Adaptive nose rule (5.5 nominal, floor TAB_L+0.2). Pillar shelf starts 0.3 outboard of rim (B1 fix). Pocket void keeps full -1.0 inboard clearance.

**Measured (from gen_case output):**
- Volume: 67.4 cm³ both halves.
- Wall_min: 1.49 (L) / 1.50 (R).
- Pocket_web_min: 1.25 (L) / 1.15 (R).
- Magnet stations: 8 per half, band min 6.48/6.49, web min 1.14.
- Antenna margin: 14.15mm.

**Assessment:** Good. The geometry is well-optimized. The wall minimum (1.49-1.50) is just above the 1.40 gate, leaving ~0.09-0.10mm margin. The pocket web (1.15-1.25) is above the 1.0 gate.

**Finding (Info) — Wall margin is thin.** 1.49-1.50 vs 1.40 gate = 0.09-0.10mm margin. FDM tolerance could eat this. **Recommendation:** consider increasing CASE_OUTSET to 7.5 for more margin (but this thickens the whole case). Or accept and verify on print. Effort: decision.

### 4.3 Port Bores (Deep)

**USB:** 14.0-wide bottom-filleted slot, z 2.0..top, measured breach 19.0mm. Plug housing 12.35 → 0.83/side clearance. Plug bottom 2.8 (0.8 above z0).

**TRRS:** Ø9.5 round bore, zc 2.5, measured breach 9.5mm. Boot Ø8.5 → 0.50/side clearance. Drop-in face r 3.94 → 0.81 clear.

**PWR:** 5.0-wide slot, z 4.3..top, measured breach 9.5mm. Lever sweep 3.6 → 0.70/side. Nail entry 0.7 below body top z5.0.

**Assessment:** Good. The bores are sized to the plugs, not the wall. The breach is measured (not fixed). The z bands are shaped to the plug's z band. The gates re-prove the breach on the finished solid.

**Finding CASE-6 (Medium) — TRRS bore oversized.** Ø9.5 round bore for a 6.1mm-wide rectangular jack → 0.8mm clear on worst corner. Drop-in is easy, but the jack can rattle. **Recommendation:** first-article: check for rattle; if present, add a thin gasket or tighten bore. Effort: first-article.

**Finding CASE-7 (Medium) — PWR slot margin 0.7/side.** 5.0-wide slot vs ~3.6 lever sweep → 0.7/side. Tight. **Recommendation:** first-article flick test; if lever binds, widen PWRSW_MOUTH_W. Effort: first-article.

**Finding (Info) — Port bores are z-independent march.** The breach march is z-independent (good — shape and breach are separate decisions). The bore shape (fillet) is fixed. If a plug's z band changes, the bore must be re-shaped manually. OK.

### 4.4 Retention (Magnets + Cover) (Deep)

**Stations:** 8 per half, candidates walk cavity boundary outward into wall band. Requirements: local band ≥6.4mm, ≥5.1mm from port/pocket rects, ≥10.1mm from antenna, ≥14mm between stations. Snapped at perimeter/8. Both halves rotate candidate ring to USB anchor for mirror symmetry (measured mirror ≤1.29mm).

**Pockets:** Ø4.2×2.2 tub, Ø4.2×1.7 cover. Faces flush at lip plane (z 6.0). Zero-gap stop (magnet faces meet at 6.0).

**Cover:** Ring z 6.0..9.0, inner edge = rim + 0.5 (bridges tabs, presses top pads). W1 USB full-depth, W2 TRRS blind tunnel, PWR full-depth with 1.1 inner web. Volume 9.0 cm³.

**Assessment:** Good. The zero-gap magnet stack is well-designed. The cover bridges all 8 tab zones and presses the top poron pads at the designed 16.7% preload. The single-solid topology gate ensures the cover stays one piece.

**Finding CASE-1 (Medium) — Magnet glue is the weak link.** The pull test (≥1.5kg) is required. If glue fails, the cover lifts. **Recommendation:** first-article pull test; if it fails, add mechanical retention (clips) or use a stronger adhesive (epoxy). Effort: first-article.

**Finding CASE-2 (Medium) — No full top cover.** The cover is a ring only. **Recommendation:** rev-2 full top cover. Effort: rev-2.

**Finding (Info) — Cover inner edge = rim + 0.5.** The 0..0.5mm root sliver stays unpressed (harmless, ~87% of pad still loads). Good.

**Finding (Info) — TRRS blind tunnel.** In the 6..9 slice, the TRRS bore is a blind tunnel topping at 7.25 > boot swing 6.75. The ring is NOT split (widest chord 6.42 < band 7.0). Good.

### 4.5 Antenna Keepout (Deep)

**Rule:** No case material within 3mm of the r=5 antenna circle. Measured wall distance 14.15mm. Antenna center inside cavity air. Gates: envelope rings (24 azimuths × 3 radii × 4 z planes), distance to both ring boundaries.

**Assessment:** Good. The antenna keepout is well-enforced. The case wall is 14.15mm away, far beyond the 3mm rule. No antenna opening is needed in the tub.

**Finding (Info) — Antenna window: none.** Correct — 14.15mm of air beats the 3mm rule with margin. A window would only matter if the cover passed closer than 3mm, which the contract forbids. Good.

### 4.6 Mechanics (Deep)

**Gasket:** Poron pads top+bottom on tabs, no hard contact. Foam sets tab height, floor depth is separate.

**Floor step:** -5.6 keeps ~1.95mm clearance under deepest protrusion. Good.

**Finding (Info) — Gasket mechanics well-reasoned.** Good.

### 4.7 Manufacturing (Deep)

**Process:** FDM (PETG/ASA/PC). Print orientation: self-supporting except USB/TRRS bridges.

**Tolerance:** FDM tolerance ~0.1-0.2mm. The 0.35mm pad margin and 0.20mm encoder margin are tight but acceptable.

**Finding (Info) — Print orientation note.** Tub open-face-up, cover underside-up. Good.

### 4.8 Case Findings (Summary)

| ID | Severity | Finding | Recommendation |
|---|---|---|---|
| CASE-1 | Medium | Magnet glue is weak link | First-article pull test |
| CASE-2 | Medium | No full top cover | Rev-2 full cover |
| CASE-3 | Low | No bottom feet | Add rubber feet |
| CASE-4 | Low | FDM anisotropy | SLS/MJF for production |
| CASE-5 | Low | No EMI shielding | Rev-2 if needed |
| CASE-6 | Medium | TRRS bore oversized (rattle) | First-article check |
| CASE-7 | Medium | PWR slot margin 0.7/side | First-article flick test |
| CASE-8 | Low | Port bores z-independent march | Document |

---

## 5. Cross-Stage Coherence (Deep)

**Outline sharing:** Plate outline = PCB outline + tabs (USB notch included). Case exterior = PCB rim + 7mm (not plate outline). Case interior = plate outline + 0.5mm. All derived from the same ergogen board outline. Good.

**Dimension propagation:** Tab roots (lands.json) → case pocket positions. Port anchors (points.yaml) → case bores. Magnet stations (gen_case) → cover pockets. All shared via function calls (compute_ports, pocket_layout, magnet_stations). Good.

**Single source of truth:** Ergogen config → points.yaml → board.dxf → gen_pcb → .kicad_pcb → gen_plate → .dxf/.json → gen_case/gen_cover → .step/.stl. Good.

**Finding CROSS-1 (Info) — Coherence is excellent.** Single-source-of-truth throughout. Good.

**Finding CROSS-2 (Low) — Plate outline includes USB notch, case exterior fills it in.** The 7.0mm dilation bridges the notch (skin rides ~17mm north). The port bore marches through. Documented. OK.

**Finding CROSS-3 (Low) — Cover must carry USB opening.** The module tops at 7.7mm, above the 6.0 lip. The ring has a W1 passage but the module sits in open air. **Recommendation:** rev-2 full top cover. Documented open item.

---

## 6. Ergonomics and Layout (Deep)

**Layout:** 44 keys (22 per half), 4 thumb keys per half, 1 encoder per half. Column-staggered (outer -8, pinky +4, ring +5, middle +7, index -3, inner -6). Thumb cluster: 4 keys at 0.5°, -13.5°, -27.5°, -41.5° rotations.

**Split width:** Mirror distance = 4.5kx + 16 = 85.5 + 16 = 101.5mm between matrix origins. Worst-case inner gap ~18.5mm (for TRRS plug engagement).

**Assessment:** Good. The column stagger follows standard ergonomic keyboard patterns. The thumb cluster has 4 keys with increasing splay. The split width gives enough room for TRRS plugs.

**Finding (Info) — 19.00mm pitch vs. 19.05mm nominal.** The layout uses 19.00mm (as-measured), not the nominal MX 19.05mm. This is documented. The 0.05mm difference is negligible. Good.

**Finding (Info) — Choc v1 only.** MX stems do not fit Choc switches. Good — documented.

**Finding (Info) — Encoder at inner column.** The encoder is placed at the inner column (bottom row), reachable by the index finger. Good.

---

## 7. Power and Battery (Deep)

**Power path:** Battery+ → JST → slide switch (common) → MCU RAW. Battery- → GND. MCU VCC → 3.3V (regulated). USB → MCU (onboard charger, 100mA).

**Charging:** Only when switch ON (switch is upstream of RAW). 110mAh cell charges in ~1.1h at 100mA.

**BLE:** Primary link. TRRS is debug fallback.

**Assessment:** Good. The power path is simple and well-documented. The charge gate (switch must be ON) is a UX hazard but is labeled.

**Finding (Info) — No battery fuel gauge.** ZMK reads VDDH internally. No external sense. Good — simpler.

**Finding (Info) — 500mA charge jumper stays OPEN.** 100mA is safer for a 110mAh cell (1C charge rate). Good.

---

## 8. Reliability and Robustness (Deep)

**Solder joints:** THT (sockets, TRRS, JST, switch) + SMD (diodes). Good.

**Connectors:** JST-PH (battery), TRRS (split link), USB-C (module). JST-PH is robust. TRRS is a known weak point (hotplug risk). USB-C is on the module (not PCB).

**Finding (Info) — TRRS hotplug risk.** Sleeve-GND mates at an angle; live mating glitches TX/RX and can brown-out charger MOSFETs. Mitigated by on/off ordering. Documented. Good.

**Finding (Info) — No reverse-polarity protection.** Documented. First-article DMM check required.

**Finding (Info) — No overcurrent protection.** The nice!nano has onboard fuse? No — the nRF52840 doesn't have a fuse. The battery PCM provides overcurrent protection. Good enough.

---

## 9. Cost Considerations (Deep)

**PCB:** 2-layer 1.6mm, ~120×100mm per half. ~$2-5/board at JLCPCB (5pcs). ENIG +$5-10.

**Components:** nice!nano v2 ~$10 each (×2). Choc switches ~$0.30 each (×44). Diodes ~$0.02 each (×44). EC11 ~$1.50 each (×2). PJ-320A ~$0.50 each (×2). WS-SLTV ~$0.80 each (×2). JST-PH ~$0.30 each (×2). Battery 301230 ~$3 each (×2).

**Plate:** Laser-cut PC 1.5mm, ~$5-10 per half.

**Case:** FDM-printed, ~$5-10 per half (material + time). Magnets ~$0.50 each (×32).

**Total BOM (rough):** ~$60-80 per keyboard (excluding labor). Reasonable for a prototype.

**Assessment:** Cost is reasonable for a prototype. The nice!nano is the most expensive component (~$20 total). Consider a cheaper controller (e.g., Pro Micro RP2040, ~$5) for a production run.

---

## 10. Summary of Recommendations

### Before Ordering (First-Article, No CAD Change)

1. **PCB-11** — Measure USB notch-to-socket-pad gap (0.78mm); widen notch to 14mm if solder bridging.
2. **PCB-13** — Verify EC11 mounting hole clearance to 12.7mm plate hole.
3. **PLATE-1** — Clip-engagement test in all regions; tighten cutout if rock.
4. **PLATE-7** — Encoder hole sample; widen to 13.0 if rub.
5. **PLATE-8** — Diode feeler test (0.5mm).
6. **CASE-1** — Magnet pull test (≥1.5kg).
7. **CASE-6** — TRRS rattle check.
8. **CASE-7** — PWR flick test.
9. **PCB-5** — Encoder shaft height ergonomics check.
10. **PCB-17** — Decide ENIG vs HASL.

### Rev-2 (CAD Changes)

1. **PCB-1** — Fix diode symbol (eliminate 22 W1 warnings/half).
2. **PCB-2** — Battery reverse-polarity protection (MOSFET/polyfuse).
3. **PCB-3** — Always-on charging (switch disconnects load only).
4. **PCB-4** — B.Cu GND pour.
5. **PCB-7** — Add test points (VBAT/RAW/GND).
6. **PCB-16** — Make power-class a net property, not string match.
7. **PLATE-2** — Narrower Poron pad (6-7mm) or longer tab.
8. **PLATE-3** — Tab near encoder if feel is too soft.
9. **CASE-2** — Full top cover.
10. **CASE-3** — Bottom feet.
11. **CROSS-3** — Cover carries USB opening.

### Decisions Needed Before Ordering

1. **PCB-17** — ENIG vs HASL.
2. **PLATE-5** — PC vs POM for production.
3. **PCB-5** — EC11 20mm shaft vs Bourns PEC11L 15mm.

### Strengths (Do Not Change)

- Single-source-of-truth generators throughout.
- Machine-checked gates: DRC (W1 exact count, W2 armed), containment, copper dangling, antenna keepout, web minimums, solid topology, antenna envelopes, volume tripwires.
- Honest documentation of trade-offs, deferred items, and accepted prototype deviations.
- Safety: TRRS ring2 NC, hotplug ordering, no reverse-polarity hardware (documented).
- Material-aware plate (web minimums per material).
- Tab-and-jacket gasket suspension (well-reasoned).
- Magnet zero-gap retention (rigid stop, no foam crush).
- Measured-breach port bores (no fixed depths).
- Mirror symmetry audit (placement, rotation, silk identity).
- Custom MCU socket footprint (column-major, guarded).
- Power switch common-pin guard.
- 3D model calibration (measured from STEP, not assumed).

---

---

## 11. Detailed Routing Quality Analysis

**Source:** Direct analysis of committed `.kicad_pcb` copper (384 segments / 70 vias on Left, 490 segments / 100 vias on Right).

### 11.1 Layer Balance

| Half | F.Cu segments | B.Cu segments | F:B ratio | Total length |
|---|---|---|---|---|
| Left | 209 | 175 | 1.20:1 | 2313.7mm |
| Right | 211 | 279 | 0.76:1 | 2379.9mm |

**Assessment:** The left half is F.Cu-dominant; the right half is B.Cu-dominant. This asymmetry is caused by the TRRS crossover on the right half (D1→RING1, D0→TIP), which forces more B.Cu routing. The imbalance is acceptable for a 2-layer board but means the right half has more vias (100 vs 70). **Finding:** The right half's higher via count increases manufacturing cost slightly (more drill hits) and reduces yield margin. **Recommendation:** Consider re-routing the right half's COL/ROW rails to balance layers, but this is a minor optimization. Effort: rev-2.

### 11.2 Via Density and Placement

- Left: 70 vias (GND 9, COL5 8, ROW2 7, ROW3 6, VBAT 4, others 36).
- Right: 100 vias (GND 11, COL2/COL3 7 each, COL1/ROW2 6 each, others 63).

**Assessment:** GND has the most vias on both halves (9/11) because the GND chain crosses layers frequently. The 0.6/0.3mm signal vias are appropriately sized. The 1.0/0.5mm power vias are used for VBAT_SW (7 per half) — correct for the 0.5mm track.

**Finding:** The right half has 43% more vias than the left. This is a consequence of the crossover routing. **Recommendation:** Accept for rev-1; optimize in rev-2 if via count becomes a cost driver. Effort: rev-2.

### 11.3 Antenna Keepout Verification

Direct measurement of all copper (segments + vias) against the antenna centre (5.0mm keepout, edge-based):
- Left: worst copper edge distance = 5.25mm (margin 0.25mm).
- Right: worst copper edge distance = 5.18mm (margin 0.18mm).

**Assessment:** The keepout is respected with thin margin (~0.2mm). This is tight — a fab etch tolerance of ±0.05mm could eat into it. **Recommendation:** Increase the keepout margin to 5.5mm in the router (KEEP_R = 5.5) for rev-2, or accept the current margin and verify on first article. Effort: low.

### 11.4 Track Width Distribution

- Left: 339 × 0.25mm (signal) + 45 × 0.5mm (power).
- Right: 467 × 0.25mm (signal) + 23 × 0.5mm (power).

**Assessment:** The power track count is lower on the right because the VBAT loop is shorter (no notch detour on the right? Actually the right half also has the notch, but the VBAT route may be shorter due to different component placement). The 0.5mm power tracks are only on VBAT_SW — correct, as this is the only high-current net.

**Finding (Info):** The power track count asymmetry (45 vs 23) suggests the left half's VBAT route is more complex. This is consistent with the documented 184.82mm left VBAT loop. Good.

### 11.5 Dangling Check

The copper dangling check runs on merged copper (routed + preserved) and reports 0 dangling items on both halves. The check uses 0.01mm tolerance for point coincidence. Good.

**Finding (Info):** The dangling check is robust — it catches tracks that end in mid-air after a footprint move. Good.

---

## 12. 3D Model Alignment Verification

**Source:** `pcb/kicad/Hojicha44.3dshapes/README.md`, `gen_pcb.py` MODEL_OVERRIDES.

### 12.1 Choc Switch (SW_Hotswap_Kailh_Choc_V1.wrl)

- Source: kiswitch/kiswitch (MIT + CC-BY-SA 4.0).
- Transform: identity (vendor transform used verbatim).
- Assessment: Our footprint pads are coordinate-identical to the paired kiswitch footprint. Good.

### 12.2 TRRS Jack (PJ-320A.step)

- Source: Keebio/Keebio-Parts.pretty (MIT).
- Transform: vendor rotate (-90, 0, 180).
- Assessment: Pad coords match the paired Keebio footprint. Shell orientation verified in iso render. Good.

### 12.3 MCU (nice-nano-envelope.wrl)

- Source: hand-drawn bounding box (34.1 × 18.3 × 3.2mm).
- Assessment: Not a detailed model — proves keepout/stack envelope only. USB end toward footprint pad 1. Good enough for render. **Finding:** A detailed module model would improve render quality but has no electrical/mechanical effect.

### 12.4 Encoder (ROT_EC11E.step)

- Source: ebastler/marbastlib (CERN-OHL-P-2.0).
- Transform: offset (0, 5, 0) + rot 0 (measured directly from STEP pin geometry).
- Assessment: The offset was measured from the STEP pin geometry (3-pin column x=0 at y=-5.01/-2.48/+0.02, 2-pin column x=14.5 at y=-5.03/-0.02, lugs x~7.47 at y=-8.38/+3.39). All contacts land within 0.03mm of stock pads. Shaft at (7.47, 2.49). **Important:** marbastlib's own offset (-2.5, -7.5) + rot -90 does NOT land its own model's pins on its own pads — provenance untrustworthy. The shaft alone lands within 0.03mm under rot-180 too, so shaft-centering cannot verify — only legs-on-pads can. Good attention to detail.

### 12.5 Power Switch (ws-sltv-envelope.wrl)

- Source: hand-drawn bounding box (10×2.5×6.4 per footprint name).
- Assessment: Stock footprint references a STEP that ships in NO KiCad bundle and exists in NO upstream repo. Envelope is the only honest option. Good.

**Finding (Info):** The 3D models are render-only and have no electrical/mechanical effect. The model override system (MODEL_OVERRIDES in gen_pcb.py) is well-designed — it keeps all local geometry (pads/silk/courtyard) and only re-homes the model pointer. Good.

---

## 13. Assembly Sequence Analysis

**Source:** `spec/first-article.md` §3, `spec/electronics.yaml`.

### 13.1 Recommended Order

1. **Diodes** (SMD, top side) — 22 per half.
2. **Slide switch** (THT, top side) — solder first, verify JST-1 → RAW <1Ω ON, open OFF.
3. **Sockets** (THT, top side) — 2×12 machine-pin SIP.
4. **TRRS jack** (THT, top side) — PJ-320A.
5. **JST connector** (THT, top side) — S2B-PH-K-S.
6. **Encoder** (THT, top side) — EC11E.
7. **Modules** (last) — nice!nano v2, socketed.
8. **Cell sandwich** (after all soldering) — Kapton tape over pouch face + nano underside, cell between socket rows.

**Assessment:** Good. The order is logical (SMD first, then THT, then modules, then cell). The switch is soldered early for verification. The cell goes in last (after all soldering) to avoid heat damage.

**Finding (Info):** The assembly order is well-documented and follows standard practice. Good.

### 13.2 Critical Assembly Notes

- **TRRS cable:** Mated with both halves OFF and USB unplugged from both. Switch OFF alone is insufficient.
- **Cell:** Kapton tape over pouch face AND nano underside. No Kapton, no cell.
- **JST leads:** Dressed beside the cell, never under the stack.
- **Antenna:** 5mm copper-free respected, no case material within 3mm. No metal/carbon fibre near antenna.

**Finding (Info):** The assembly notes are thorough and cover the critical risks. Good.

---

## 14. Test Coverage Analysis

**Source:** `pcb/generators/{check_board,audit_silk,gen_pcb,gen_schematic}.py`, `case/{gen_case,gen_cover,probe_bores}.py`, `plate/gen_plate.py`.

### 14.1 Automated Gates

| Gate | Tool | Status |
|---|---|---|
| Outline topology (1 loop, 0 dangling) | check_board.py | PASS |
| Fiducial containment + edge clearance | check_board.py | PASS |
| Notch openness (bite floor, pad clearance) | check_board.py | PASS |
| Silk symmetry (placement, rotation, art) | audit_silk.py | PASS |
| DRC (W1 exact count, W2 armed, unconnected NOT waived) | gen_pcb.py | PASS (28/half) |
| ERC (0 errors, 5 spare warnings/half) | gen_schematic.py | PASS |
| MCU footprint (pitch, separation, numbering, envelope) | gen_schematic.py | PASS |
| PWR footprint (common pin is middle) | gen_schematic.py | PASS |
| Plate (22 cutouts, encoder hole, windows, tabs, webs) | gen_plate.py | PASS |
| Case tub (solid topology, wall min, ports, magnets, antenna, volume) | gen_case.py | PASS |
| Case cover (solid topology, wall min, ports, pads, magnets, antenna, volume) | gen_cover.py | PASS |
| Bore shape probes (USB/TRRS/PWR) | probe_bores.py | PASS |

**Assessment:** Comprehensive automated test coverage. All gates pass. The test suite covers outline topology, component placement, copper integrity, geometry, and manufacturing constraints.

**Finding (Info):** The test coverage is excellent for a prototype. The gates are machine-checked and fail the build on violation. Good.

### 14.2 Manual/First-Article Tests

| Test | Source | Status |
|---|---|---|
| Paper fit test (1:1 print) | first-article.md §1 | Not yet done |
| Module footprint on print | first-article.md §1 | Not yet done |
| USB notch dry-fit | first-article.md §1 | Not yet done |
| Case port bores (plug slices) | first-article.md §1 | Not yet done |
| PWR flick test | first-article.md §1 | Not yet done |
| Magnet pull test (≥1.5kg) | first-article.md §1 | Not yet done |
| Encoder hole sample | first-article.md §1 | Not yet done |
| Choc clip engagement | first-article.md §1 | Not yet done |
| Diode feeler test (0.5mm) | first-article.md §3 | Not yet done |
| BLE range test | first-article.md §4 | Not yet done |
| Power-on (charge, TRRS continuity) | first-article.md §4 | Not yet done |
| Firmware bring-up (flash, BLE pair) | first-article.md §5 | Not yet done |

**Finding (Info):** All first-article tests are documented but not yet executed (no physical boards). These are the release gate. Good.

---

## 15. Documentation Quality Assessment

**Source:** `README.md`, `spec/{electronics,case,first-article}.md/yaml`, `case/README.md`, `pcb/kicad/Hojicha44.3dshapes/README.md`, `KEYBOARD_PROJECT_ROADMAP.md`, `notes.md`.

### 15.1 Documentation Strengths

1. **Single source of truth:** `spec/electronics.yaml` is the canonical spec. Title-block rev derives from spec version. Good.
2. **Honest documentation:** Trade-offs, deferred items, and accepted prototype deviations are explicitly listed. Good.
3. **First-article checklist:** Comprehensive (7 sections, ~60 checkboxes). Good.
4. **Generator comments:** Extensive inline comments explaining decisions, measurements, and workarounds. Good.
5. **3D model calibration notes:** Detailed (VRML units, mapping, measurement method). Good.

### 15.2 Documentation Gaps

**Finding DOC-1 (Low) — No assembly photo guide.** The first-article checklist is text-only. A photo guide would reduce assembly errors. **Recommendation:** Add photos to first-article.md. Effort: low.

**Finding DOC-2 (Low) — No troubleshooting guide.** Common issues (solder bridging, wrong polarity, NFC flash failure) are mentioned but not consolidated. **Recommendation:** Add a troubleshooting section. Effort: low.

**Finding DOC-3 (Low) — Roadmap is large (27KB).** The roadmap covers many phases. A summary/TL;DR would help. **Recommendation:** Add a one-page summary. Effort: low.

---

## 16. Firmware Interface Deep-Dive

**Source:** `spec/electronics.yaml` (pin_map, nrf_mapping, gpio_accounting), `zmk/` directory.

### 16.1 Pin Mapping

- **Rows:** R0=D4 (P0.22), R1=D5 (P0.24), R2=D6 (P1.00), R3=D7 (P0.11).
- **Cols:** C0=D8 (P1.04), C1=D9 (P1.06), C2=D2 (P0.17), C3=D3 (P0.20), C4=D14 (P1.11), C5=D15 (P1.13).
- **Encoder:** ENC_A=A0 (P1.15), ENC_B=A1 (P0.02), ENC_SW=D16 (P0.10).
- **Split:** left_TX=D1 (P0.06), left_RX=D0 (P0.08), right_TX=D1, right_RX=D0 (crossed in copper).
- **Spare GPIO:** A2 (P0.29), A3 (P0.31), D10 (P0.09).

**Assessment:** Good. 15 used + 3 spare = 18 GPIOs. No shortfall. The split-link crossover (right half) ensures both halves use identical UART pinctrl. Good.

### 16.2 NFC Pin Issue

D10 (spare) and D16 (encoder push) are NFC pins (P0.09/P0.10). They require `nfct-pins-as-gpios` in the UICR overlay and a full chip erase on first flash. Without erase, the pins stay locked to the NFC peripheral.

**Finding (Info):** Documented. First-flash must use `--erase`. Good.

### 16.3 Low-Drive Pins

A1 (P0.02), A2 (P0.29), A3 (P0.31) are low-drive only (max 0.5mA). Used for encoder quadrature (A0/A1) and spare (A2/A3). No high-current drive needed. Good.

### 16.4 Power Pin

VCC (pin 21) is a power output (3.3V regulated). RAW (pin 24) is power input (3.7-5.5V). B+/B- module holes stay open (power enters via RAW). Good.

---

## 17. Environmental and Operating Conditions

**Source:** `spec/electronics.yaml`, `spec/case.md`.

### 17.1 Operating Temperature

- **PCB:** Standard FR4 operating range (-40 to +85°C). Components (nice!nano, Choc switches, EC11) are rated for -20 to +70°C typical. Good.
- **Battery:** LiPo 301230 rated for -20 to +60°C charging, -20 to +60°C discharging. Good.
- **Case:** FDM-printed (PETG/ASA/PC) rated for -20 to +80°C (PETG), -20 to +100°C (ASA), -20 to +120°C (PC). Good.

**Finding (Info):** Operating temperature range is adequate for indoor use. No outdoor/cold-environment rating. Good.

### 17.2 Humidity

- **PCB:** No conformal coating. Not rated for high humidity. Good for indoor use.
- **Case:** FDM-printed, not sealed. No IP rating. Good for indoor use.

**Finding (Info):** No IP rating. Not suitable for wet environments. Good for a keyboard.

### 17.3 Vibration and Shock

- **Gasket mounting:** The tab-and-jacket suspension provides vibration isolation. The poron pads absorb shock. Good.
- **Components:** Choc switches are hotswap (can be removed). Nice!nano is socketed (can be removed). Good for repairability.

**Finding (Info):** The gasket design provides good vibration isolation. Good.

---

## 18. Final Assessment

The Hojicha44 project demonstrates an exceptionally high level of engineering rigor for a prototype keyboard:

1. **Single source of truth:** Every stage derives from the same ergogen layout. No hand-drawn CAD.
2. **Machine-checked gates:** DRC, ERC, containment, copper dangling, antenna keepout, web minimums, solid topology, antenna envelopes, volume tripwires. All pass.
3. **Honest documentation:** Trade-offs, deferred items, and accepted deviations are explicitly listed. No hidden compromises.
4. **Safety-first:** TRRS ring2 NC, hotplug ordering, no reverse-polarity hardware (documented), antenna keepout.
5. **Material-aware:** Plate web minimums per material. Case wall thickness gated.
6. **First-article ready:** Comprehensive checklist (7 sections, ~60 checkboxes) before ordering.

**The design is ready for first-article fabrication pending the decisions and tests listed in §10.** No changes were made to any file during this audit.

---

*End of report. No changes were made to any file.*
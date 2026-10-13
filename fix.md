# Hojicha44 — Fix Plan

Scope: everything found in the layout, schematic, and PCB review of 2026-10-13.
Goal: a board pair that is safe to send to fabrication (Gerbers, drill, BOM, CPL).

Status of this document: **plan only. No project files were changed by this review.**
All geometry numbers below were measured from the current generated files
(`pcb/kicad/Hojicha44-{Left,Right}.kicad_pcb`, 11:12 on 13 Oct) and the Ergogen
config (`layout/ergogen yaml/config.yaml`). Re-measure after each change.

---

## 0. Corrections to the earlier review

- **Battery / RAW (downgraded).** The earlier review called the RAW-based battery
  path a blocker because the official nice!nano pages only name B+/B-. A later
  check of the joric/nrfmicro wiki (the nRF52 keyboard-controller community
  reference) says RAW/GND and B+/B- "are internally connected so they are
  essentially the same", and that RAW is the charger input. So the design is
  probably electrically correct. It still needs a physical continuity check
  (item S1). The spec's *citation* ("official docs") is wrong and must be fixed.
- **Socket and RAW reasoning.** The spec's use of RAW is forced by the socket:
  the module's B+/B- pads sit on its top edge (official FAQ: "2 extra pins at
  the top of the board") and are not on a socket pin. RAW is socket pin 24.
  Keeping RAW is the right choice, but cite the correct source.

---

## 1. Summary table (priority order)

**Status, 2026-10-13 (PCB-design start).** **P0-1, P0-2, P0-3 and P1-1 are
done** — applied, regenerated, and re-measured on the regenerated files (see
`notes.md` → "PCB-design start": single outline loop per half, notch open to
47.25 vs a 60.00 board edge, 3 fiducials per half all inside with ≥3.03mm edge
clearance, '+' mark 0.86mm off the JST silk). P0-4 is unblocked but not started:
the generator now *preserves* copper instead of deleting it, so routing can be
done by hand or by a router without the next regeneration erasing it.
P0-5, P0-6 and every P2 row are still open; the P2 rows are decisions, not
defects.

| ID | Severity | Area | Issue | Fix section |
|---|---|---|---|---|
| P0-1 | Blocker | PCB outline | USB notch is an enclosed hole, not an open edge notch (both halves) | §2.1 |
| P0-2 | Blocker | PCB fiducials | All 6 fiducials sit outside the board outline | §2.2 |
| P0-3 | Blocker | Pipeline | `gen_pcb.py` (11:13) is newer than the PCB it generated (11:12), and layout outputs are gitignored | §2.3 |
| P0-4 | Blocker | Routing | No copper exists (0 tracks, 0 vias, no pour); 77 unconnected items per half (→ §9: DONE — routed, 0 unconnected) | §2.4 |
| P0-5 | Blocker (verify) | Battery | Battery RAW vs B+ path needs a physical continuity check and spec citation fix | §2.5 |
| P0-6 | Blocker (order) | BOM | No locked MPNs: switch, slide switch, encoder, JST, battery, socket height (→ §9: DONE — MPNs in symbols + spec/bom.md; cell/knob locked to stock) | §2.6 |
| P1-1 | Must-fix | Silk | `+` polarity mark overlaps JST silk (DRC error) | §3.1 |
| P1-2 | Must-fix | Silk | Silk over pads on diodes, TRRS, and a back-side switch pad | §3.2 |
| P1-3 | Must-fix | Silk | Reference text overlaps silk on SW_L20/L21 and SW_R20/R21 | §3.3 |
| P1-4 | Must-fix | Footprints | 28 `lib_footprint_mismatch` per half (embedded copies diverge from library) | §3.4 |
| P1-5 | Must-fix | Fab gate | Tooling holes missing (spec gate) | §3.5 |
| P1-6 | Should | ERC | 5 warnings per half are intentional spares; mark them as no-connects | §3.6 |
| P1-7 | Should | Docs | Spec/notes contradictions (flip, TRRS comment, battery citation, 302030) | §3.7 |
| P1-8 | Should | Silk | TRRS silk runs past the board edge (warning) | §3.2 |
| P2-1 | Decision | Split link | TRRS is wired while batteries are connected (FAQ warns against it) | §4.1 |
| P2-2 | Decision | Routing | 2-layer routing with diode vias: feasibility risk | §4.2 |
| P2-3 | Ergonomics | Layout | Stagger step, zero splay, encoder reach, overall size | §4.3 |
| P2-4 | Feature | Hardware | No reset button on the module RST pin | §4.4 |
| P2-5 | Feature | Hardware | Power switch rating and pad-2 check still open | §4.5 |
| P2-6 | Feature | Firmware | ZMK NFC-pin setting for D10/D16 | §4.6 |

---

## 2. Blockers

### P0-1 — USB notch is enclosed (both halves)

**Measured.** The `usb` notch is an 11 × 5.4 mm rectangle, x 112.50–123.50,
y 47.25–52.65 (left; right is the same at x +55.5). In the Edge.Cuts data it is
a *separate closed loop* — 2 loops per half where there should be 1. The
closest outer-edge point is 0.021 mm away (at x ≈ 117). Outer edge heights above
the notch: x 112.5 → 57.53; x 115 → 54.03; x 117 → 52.67; x 118 → 52.80;
x 120 → 53.06; x 123.5 → 53.51.

**Cause.** `usb` is at `mcu + (0, 17.95)` and the notch is 5.4 tall, so it
stops at `mcu + 20.65` (y = 52.65). The outline was expanded 4.5 mm
(`expand: 4.5`), putting the north edge near `mcu + 21.95`. The config comment
says the notch "clears the topmost socket pads by ~0.5 mm" — that was checked
against the raw polygon, not the expanded one. The notch never reaches the
edge, so the USB plug has no opening.

**Why it matters.** The plug must enter through the open north edge. An
enclosed hole is a fabrication defect, and a 0.02 mm sliver is below any board
edge tolerance.

**Fix (`layout/ergogen yaml/config.yaml`, `outlines.board`, the USB subtract):**

```yaml
    # USB-C seat notch: open to the north edge. Top must clear the expanded
    # edge (min ~54.0 at x=115, 57.5 at x=112.5). Bottom stays >=0.9 mm above
    # the top socket pad copper (pad 1/24 centre at mcu+13.47, radius ~0.85).
    - operation: subtract
      what: rectangle
      where: [usb, mirror_usb]
      size: [11, 10.8]
      adjust:
        shift: [0, 2.7]        # rect spans y = usb-2.7 .. usb+8.1  -> 47.25 .. 58.05
```

Also change the `_usb` preview outline to the same size so the preview matches.

**Pre-check done (temporary copy only, nothing applied to the project):** the
patched config runs under Ergogen 4.2.1 (exit 0). In the board DXF the notch
no longer forms a closed interior region (closed regions: 2 in the current file,
both notches; 0 in the patched file). The outer ring could not be checked for
closure from the DXF, because endpoints differ at 0.001 mm; that check must be
run on the KiCad board after regeneration (step 1 below).

**Verification (acceptance):**
1. Regenerate layout (§2.3), then re-run the loop check. Each half must have
   **exactly 1** Edge.Cuts loop (the notch must merge with the outer loop).
2. The notch's top edge must be above the outer edge over its full width
   (every sample point x in 112.5–123.5 has outer-edge y < 58.05).
3. The minimum distance from top-pad copper (y 46.3) to the notch bottom
   (y 47.25) must be ≥ 0.5 mm (here 0.95 mm).
4. Re-run DRC: no `copper_edge_clearance` or `invalid_outline` violations.

**Reasoning.** Making the cut taller and anchoring it to the usb point keeps the
module-to-board relationship intact. The alternative (moving `usb` north) would
change the MCU zone and the `_usb` anchor used elsewhere.

Sources: the reference measurements come from this project's generated geometry
(local files, §7 items 9–11). The plug-seat requirement is a mechanical fit check, not a
cited standard; confirm on a physical module.

### P0-2 — Fiducials are off the board (both halves)

**Measured.** Fiducials are placed at bounding-box corners inset 5 mm
(`gen_pcb.py`, `FID_{tag}{i}`). Because the outline is irregular, all six fall
outside it:

| Ref | Position (mm) | Inside outline? |
|---|---|---|
| FID_L1 | (-9.00, 55.00) | no |
| FID_L2 | (131.50, 55.00) | no |
| FID_L3 | (61.25, -49.63) | no |
| FID_R1 | (160.00, 55.00) | no |
| FID_R2 | (300.50, 55.00) | no |
| FID_R3 | (230.25, -49.63) | no |

**Fix (`pcb/generators/gen_pcb.py`, the fiducial block).** Replace the
bbox-corner rule with a search over the real outline:

```python
# Pseudocode for gen_pcb.py fiducial placement (replace bbox corners):
#   candidates = grid points (1 mm step) inside the Edge.Cuts polygon
#   keep p if dist(p, every Edge.Cuts segment) >= 3.0 mm   # fab edge margin
#   keep p if no pad/courtyard within 2.0 mm of p          # mask clearance
#   choose 3 points that are mutually far apart (max min-distance)
# Fix the chosen coordinates in the generator (don't re-search at build time)
# so the layout stays reproducible.
```

Reuse the point-in-polygon and segment-distance helpers from the audit script
(§5). Prefer fiducials near the two outer top corners and one bottom-centre
location, all inside solid board.

**Acceptance.** Each fiducial's centre tests *inside* the outline with
≥ 3.0 mm to the edge, and it is clear of components. A 1 mm pad with 3 mm
solder-mask opening is standard (`Fiducial_1mm_Mask3mm`).

**Reasoning.** Pick-and-place machines and reflow inspection need the marks
on copper within the board; a fiducial off the board is rejected or misread by
the assembler. Standard practice is 3 mm from the edge (the spec's own gate
asks for 3 fiducials).

### P0-3 — Generated outputs are stale and not reproducible

**Measured.** `gen_pcb.py` was modified at 11:13, after the PCB it generated
(11:12). `layout/generated/` is gitignored, so `--clean` in the regen
command destroys outputs with no history (README "Regenerate" section).

**Fix.**
1. Before any regen, back up `layout/generated/v2` and `pcb/kicad/*.kicad_pcb`
   (copy to `/tmp/` or a dated folder).
2. Regenerate in this order: Ergogen → `dump_points.cjs` → `gen_schematic.py`
   → `gen_pcb.py` (exact commands in §6).
3. Commit the layout config and both generators. Track generated outputs
   with a hash manifest, since they are gitignored.
4. Add a check that fails if `gen_pcb.py` is newer than its output.

**Acceptance.** Fresh regen completes, the audit passes, and all §2 checks pass.

Source: project `README.md` ("Regenerate"; "`layout/generated/` is gitignored,
so `--clean` destroys outputs with no history") and `notes.md` (toolchain gotchas).

### P0-4 — No routing exists

**Measured.** 0 tracks, 0 vias, no zones. DRC reports 77 unconnected items per
half. The boards are blank in copper.

**Prerequisite, done 2026-10-13.** `gen_pcb.py` rebuilt the whole board body
from `head + gfx + body`, so it deleted any copper on the next run — proven by
injecting a fake `(segment …)` into a sandbox copy (it did not survive
`build_board()`). Now `extract_copper()` preserves `(segment …)`, `(via …)` and
`(zone …)` verbatim, remaps net codes **by name**, and `check_copper()` fails
the build if preserved copper no longer attaches to a pad/via/track (stranded by
a footprint move) or enters the r=5mm antenna keepout. Without this, routing by
hand and regenerating would silently produce a board with no tracks, and DRC
would report it only as the same `unconnected_items` the pre-routing waiver
already accepts.

**Plan (2-layer, see §4.2 for the risk).** Layer assignment follows the hot-swap
footprint as vendored:

- **B.Cu:** Choc socket pads (switch pins 1 and 2, the socket footprint is
  on the back), column nets, the GND pour (see below).
- **F.Cu:** diodes (SOD-123), rows, and the row-to-diode path.
- **Per key:** one via from switch pin 2 (B.Cu, anode net) to the diode anode
  (F.Cu). Diode cathode → row on F.Cu.

Routing order:
1. Power and MCU: RAW ↔ `VBAT_SW_*` (POWER class, 0.5 mm), GND, `VCC3V3`.
2. Matrix: columns on B.Cu, per-key vias, rows on F.Cu.
3. Encoder: A/B/push traces, C/S2 to GND.
4. TRRS: T, R1, S; ring2 stays unconnected (no trace; leave the pad floating).
5. Battery: JST → switch → RAW (short, POWER class, away from the antenna).
6. GND pour on B.Cu (and F.Cu where free), with the antenna keepout excluded (see below).
7. Silk, mask, and DRC clean-up (§3).

Keepouts to enforce during routing:
- **Antenna keepout:** r = 5 mm copper-free circle at `antenna` (and mirror).
  No pour, no traces, on either layer. The `antenna_keepout` outline marks it.
- **USB notch:** keep copper ≥ 0.5 mm from the notch edge.
- **Socket pads:** keep the 2×12 socket pad rows clear of other copper.

**Acceptance.** DRC shows 0 unconnected items. ERC and DRC are clean except the
intentional items documented in §3.6. Gerber outputs are non-empty.

Sources: none external. The 2-layer per-key-via plan is this review's own
reasoning, from the vendored footprint's pad layers (B.Cu socket pads, F.Cu diodes).
It is not checked against a published Lily58 or Corne layout; treat it as an
assumption to verify by routing (see §4.2).

### P0-5 — Battery RAW vs B+ path (verify, don't redesign)

**What the sources say.**
- nicekeyboards getting-started page: "the 301230 battery … fits underneath a
  socketed nice!nano"; the simplest wiring is to "hardwire the battery to the two
  pad +/- on the top of the nice!nano."
- nicekeyboards FAQ: "each has an individual Li-Po battery connected to it via 2
  extra pins at the top of the board (called B+ and B-)."
- joric/nrfmicro wiki, *Batteries*: "Use RAW / GND or B+ / B- pairs of pins for
  the battery (those pairs of pins are internally connected so they are
  essentially the same)." Also: RAW is "for the charger only" (in the
  Helix/Gherkin warning, where RAW-to-VCC kills the controller). And V2 uses a
  BQ24072 charger.

**Conclusion.** RAW/GND is a defensible choice, and it is the only battery
pair reachable through a socket pin. The design holds, but the spec must cite
joric (not "official docs").

**Fix.**
- **S1 (physical check on a real module, before the board is ordered):**
  - Continuity RAW ↔ B+ and GND ↔ B- on the module (multimeter, both halves).
  - Continuity RAW ↔ VCC = **no** (joric: tying them kills the controller).
  - Confirm the charger's behaviour: charge with the slide switch ON; the orange
    LED should light.
- **S2:** update `spec/electronics.yaml` (`battery_wiring`) and the README to
  cite joric's wiki and the RAW-internally-connected statement. Remove "per
  official nice!nano docs".
- **S3:** keep the "charge only when switch ON" note (`spec/electronics.yaml`,
  `charger`). It follows from the switch sitting upstream of RAW.

**Acceptance.** S1 passes on both halves, and the spec cites the correct source.

### P0-6 — Parts not locked (must be done before ordering)

Locking these gates is required before Gerber release. Each is listed in the
spec's `pcb_gates` or `PCB GATE` comments.

| Part | Open item | Action | Source / note |
|---|---|---|---|
| Slide switch (WS-SLTV) | MPN, ≥300 mA rating, pad-2 common | Record MPN; check the Würth datasheet: pad 2 is common (symbol assumes 2 = common, 1 = rail) | `spec/electronics.yaml` `switch`; Würth WS-SLTV datasheet |
| EC11E encoder | Shaft and bushing height (H20 mm footprint) | Confirm knob height vs case cutout; pick a shorter variant if needed; record MPN | `spec/electronics.yaml` `encoder_per_half` |
| JST-PH | Pin-1 polarity, `+` mark | Keep the `+` mark (P1-1); record connector MPN | `spec/electronics.yaml` `battery_connector` |
| Battery | 301230, 80 vs 110 mAh | Record supplier; joric notes both labels exist | joric wiki, *301230* section |
| MCU socket | Stack height TBD | Joric says 301230 "fits snugly between two 4.5 mm tall machine pin sockets"; choose a socket, measure stack height (PCB + socket + module + cell) | joric wiki, *301230*; nicekeyboards docs |
| TRRS PJ-320A | Terminal continuity vs datasheet | Continuity test of T/R1/S on a sample jack | `spec/electronics.yaml` `split_connector` |

---

## 3. Must-fix (fabrication cleanliness)

### P1-1 — `+` polarity mark overlaps JST silk (DRC error)

**Measured.** `gr_text "+"` at (115.5, 9.5) on F.SilkS sits on the JST outline
silk (segment at (115.94, 5.54)). Right half: (171.0, 9.5) vs (171.44, 5.54).

**Fix.** In `gen_pcb.py`, place the `+` next to pin 1 *outside* the JST silk
body: compute pin 1's pad position from the footprint, then offset ≥ 1.0 mm
clear of the silk outline. Keep it on F.SilkS.

**Acceptance.** No `silk_overlap` for the `+`. The mark is readable and adjacent
to pin 1.

Source: `spec/electronics.yaml` `pcb_gates` (JST `+` mark gate).

### P1-2 — Silk over pads (diodes, TRRS, back-side switch pad)

**Measured (DRC `silk_over_copper`, all "Local override; error"):**
- Diodes D_L20/21 and D_R20/21 (ROW3 thumbs): F.SilkS segments over pad 1.
- TRRS J_L1 / J_R1: F.SilkS segments over pads R1 and R2 (silk clipped by
  mask at (126.9, -25.35), (130.1, -24.3), (133.1, -24.3)).
- SW_R19 (B.SilkS) over pad 2 (`Net-(D_R19-A)`) at (221.35, -21.71).

**Fix.**
- Diodes: trim the F.SilkS polarity bar in the vendored `D_SOD-123` footprint so
  it sits ≥ 0.15 mm beyond the pad edges. Keep the cathode band readable (spec
  gate: "diode polarity silk readable").
- TRRS: trim the silk outline in `TRRS-PJ-320A.kicad_mod` so it clears pads R1/R2
  by 0.15 mm.
- SW_R19: trim the B.SilkS segment in the Choc footprint over pad 2.

Edit the vendored footprints in `pcb/kicad/Hojicha44.pretty/`, not the generated
PCB copies, so the fix survives regeneration.

**Acceptance.** No `silk_over_copper` violations. Polarity remains visible.

Source: DRC report (`pcb/kicad/Hojicha44-{Left,Right}-drc.rpt`) and the spec's
diode-silk gate.

### P1-3 — Reference text overlaps silk (SW_L20/L21, SW_R20/R21)

**Measured.** `silk_overlap` for reference fields of SW_L20, SW_L21, SW_R20,
SW_R21 against adjacent silk segments (e.g. (95.84, -35.68), (113.24, -46.84)).

**Fix.** Keep switch reference designators but move them clear of the silk: in
`gen_pcb.py` set the reference for thumb switches (row 3) to a clear position,
or hide the reference (as already done for diodes, `hide_ref`). Hiding is
acceptable because the schematic carries the refdes; note it in the fab notes.

**Acceptance.** No `silk_overlap` for these references.

### P1-4 — Footprint library mismatch (28 per half)

**Measured.** 22 × `D_SOD-123` (Diode_SMD), plus 4 × Choc, 1 × TRRS, 1 × socket
per half: "does not match copy in library … Local override".

**Cause.** `gen_pcb.py` embeds each footprint with nets, fresh UUIDs, and
`hide_ref`, so the embedded copy differs from the library copy. KiCad flags any
difference.

**Fix.** Pick one approach and document it:
- **(a) Preferred:** in KiCad's GUI, run "Update footprints from library" on a
  copy, confirm nets and positions survive, and check whether the warnings
  clear. If they do, keep the generator in sync with the library.
- **(b)** If they don't clear, document each remaining difference (hide-ref,
  nets) as an accepted local override in the notes, then ask the reviewer to sign
  off. Don't suppress the DRC rule.

**Acceptance.** Either zero mismatches, or a written list of accepted overrides
in `notes.md` with a reason for each.

Source: DRC report; KiCad library behaviour (not fetched).

### P1-5 — Tooling holes missing (spec gate)

**Measured.** No NPTH tooling holes. The spec's `pcb_gates` lists "3× fiducials +
tooling holes for SMD diode assembly". Fiducials are fixed in P0-2; tooling holes
are not.

**Fix.** Add two NPTH tooling holes outside the keyboard footprint, on the
fabrication rail, using the fab's recommended diameter (commonly 1.15–1.5 mm;
confirm with the fab). Keep them clear of the outline and copper. Add them in
`gen_pcb.py` as `(footprint "MountingHole_*")`-style NPTH, not in the outline.

**Acceptance.** Two NPTH holes present in each board, clear of copper and edge.

Source: the spec's `pcb_gates`; fab practice (confirm with the chosen fab).

### P1-6 — ERC warnings for intentional spares

**Measured.** 5 warnings per half: `RST`, `VCC3V3`, `A2`, `A3`, `D10` (single
pins, intentional).

**Fix.** Place `no_connect` markers on those pins (in `gen_schematic.py`, the
spare pins), so ERC reports them as deliberately unconnected instead of as
warnings. Don't disable the ERC rule.

**Acceptance.** `erc` reports 0 errors and 0 warnings per half.

Sources: ERC report (`pcb/kicad/Hojicha44-{Left,Right}-erc.rpt`).

### P1-7 — Documentation contradictions

| File | Problem | Fix |
|---|---|---|
| `notes.md` ("Open before routing" item 4 vs gen_pcb) | Says "place the footprint flipped" | Generator and spec both say *not flipped*; pads on B.Cu. Update `notes.md`. |
| `spec/electronics.yaml` `split_link` comment | "left tip (left TX) meets right ring1 (right RX)" | Netlist has right ring1 = right TX, right tip = right RX; cable is tip-to-tip. Correct the comment. |
| `spec/electronics.yaml` `battery_wiring` | Cites "official nice!nano docs" | Cite joric wiki (§P0-5). |
| `notes.md` item 5 | Still says the spec describes a 302030 cell | Spec now says 301230. Update the note. |
| `spec/layout.yaml` `usb` comment | Says the USB notch "opens the seat notch" | Update after P0-1; the notch geometry changes. |

**Acceptance.** `grep -n "flip\|302030\|official"` returns only correct,
current statements.

### P1-8 — TRRS silk runs past the board edge (warning)

**Measured.** `silk_edge_clearance` warnings for J_L1 / J_R1 silk at (126.9,
-18.65), (126.9, -25.35), against the Edge.Cuts segment near (136.49, -8.31).
The PJ-320A mouth sits 3.46 mm proud of the edge by design.

**Fix.** Trim the TRRS body silk to within the outline, or keep the silk inside
and accept the warning with a note. The mouth protrusion is intentional
(`layout/ergogen yaml/config.yaml`, `_trrs`).

**Acceptance.** No `silk_edge_clearance` warnings, or a justified note.

---

## 4. Decisions and design options

### P2-1 — TRRS wired with batteries connected

**Source.** nicekeyboards FAQ: "using a TRRS jack with the batteries still
connected is strongly discouraged … can cause a short circuit and damage the IO
pins on the nice!nano." The spec already flags this (`split_connector.hotplug`).

**Options:**
- **(a) Keep TRRS as a bring-up / debug link only** (current spec). Enforce
  power-off order on the case: "plug cable, then switch on." Acceptance: a
  documented assembly note and a case label.
- **(b) Replace TRRS with a 4-pin JST between halves**, carrying TX, RX, GND, and
  optionally a power-isolated VBAT. Acceptance: a new connector footprint and an
  updated `split_connector` spec. This is the recommended option for everyday
  use.

**Decision needed from you.** (a) for prototype, (b) for a daily-use build.

### P2-2 — Two-layer routing feasibility

**Risk.** 22 switches per half, each needing a via from B.Cu (socket pad) to
F.Cu (diode), plus column routing on B.Cu around the anode pads. The socket
pads and diodes are close (~3.55 mm gap). Routing may fail in 2 layers.

**Options:**
- **(a)** Try two layers first, with the per-key via plan in §2 (P0-4). If the
  router fails, move to (b).
- **(b)** Move to four layers (cost ↑, routing ↑). Update the spec's stackup
  (`pcb.stackup`) and the fab order.

**Decision needed from you.** Accept the cost risk of (b) if (a) fails.

### P2-3 — Layout and ergonomics

Reference values here are from general knowledge of Corne, Lily58, and Sofle.
Confirm against their Ergogen configs before acting.

| Item | Current | Reference | Action |
|---|---|---|---|
| Key count | 22 per side (6×3 + 4 thumbs) | Corne 6×3 + 3 thumbs; Lily58 6×4 + 4; Sofle 6×4 + 5–6 | Keep. Corne-like with one extra thumb. |
| Column stagger (mm) | outer −8, pinky +4, ring +5, middle +7, index −3, inner −6 | Reference boards usually use a smoother arc | Test a smaller middle→index step (currently 10 mm, about half a key). Make a printed mock or KLE overlay and compare. |
| Splay | 0 (parallel columns) | Corne, Lily58, Sofle use some splay | Keep as a deliberate choice; test a small splay in Ergogen (`splay` per zone). |
| Encoder | inner-home +(23, −26) | Reachable by thumb / inner-bottom finger | Check reach on the printed mock. |
| Overall size | ~150 × 115 mm per half (MCU/battery block outboard) | Varies by reference | Check against the desk and case. |

Sources: Ergogen points documentation (https://docs.ergogen.xyz/points/).

**Acceptance.** A printed mock reviewed for reach; a stagger/splay decision
recorded in `spec/layout.yaml` with status.

### P2-4 — Reset button

**Gap.** The nice!nano's RST pin (socket pin 22) is a spare with no button.
Recovery needs a double-tap or a bridge.

**Fix (feature).** Add a tactile switch between RST (socket pin 22) and GND.
A footprint and a schematic net (`RST_L` / `RST_R`) are needed.

Source: the nRF52 bootloader and reset pin are not covered in the sources fetched for
this review. Confirm the recovery procedure (double-tap, RST-to-GND) against the
nice!nano FAQ / troubleshooting page before relying on it.

### P2-5 — Power switch rating and pad 2

**Gap.** The WS-SLTV MPN and rating are not recorded; pad 2 = common is an
assumption.

**Fix.** Record the MPN, check the datasheet for ≥300 mA (the spec's requirement),
and confirm pad 2 = common with a continuity test on a sample switch. If the
rating is short, pick an SPDT slide switch rated for the peak current.

Source: `spec/electronics.yaml` (`switch`, `pcb_gates`).

### P2-6 — NFC pins for the encoder push and spare

**Gap.** D10 (P0.09) and D16 (P0.10) are NFC pins. ZMK needs the NFC-as-GPIO
setting in the board overlay.

**Fix.** Add the ZMK overlay setting so D16 (encoder push) works on first flash.
Confirm the exact Kconfig/DT option in the ZMK version used.

Source: `spec/electronics.yaml` (`firmware_note`); ZMK documentation.

---

## 5. Verification plan

### 5.1 Checks to run after every change

Run them in this order; each must pass before the next.

1. **Schematic:** `python3 pcb/generators/gen_schematic.py` — the audit, guards,
   and ERC must pass.
2. **PCB placement:** `python3 pcb/generators/gen_pcb.py` — placement, then DRC.
3. **Outline topology (new):** each half has **1** Edge.Cuts loop, no dangling
   segments (script: `/tmp/pcbcheck.py`, to be moved into
   `pcb/generators/check_board.py`).
4. **Fiducials (new):** each fiducial is inside the outline with ≥ 3.0 mm edge
   clearance (script: `/tmp/fid.py`, to be moved).
5. **Notch open (new):** the notch merges with the outer loop (check 3), and
   top-pad copper ≥ 0.5 mm from the notch edge.
6. **DRC:** `kicad-cli pcb drc` — 0 unconnected after routing; silk, mismatch,
   and edge items resolved per §3.
7. **ERC:** 0 errors and 0 warnings per half.

### 5.2 Pre-Gerber checklist

- [ ] Both outlines: 1 loop each; notch open; no dangling segments.
- [ ] Fiducials on board, ≥ 3.0 mm from edge; 2 tooling holes NPTH.
- [ ] 0 unconnected items; 0 DRC errors; silk clean (§3).
- [ ] Antenna keepout copper-free on both layers.
- [ ] Battery S1 continuity test recorded (RAW ↔ B+, RAW ↔ VCC = open).
- [ ] MPNs recorded for switch, slide switch, encoder, JST, battery, socket.
- [ ] Spec `pcb_gates` each closed or explicitly accepted.
- [ ] Release manifest: spec version, git commit, tool versions (kicad-cli 10.0.6),
      generator hashes.

### 5.3 Gerber and fab outputs (after the checklist)

Commands use the KiCad CLI at
`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`. Check the exact flags with
`--help` before running; this list is the intended set, not verified against
KiCad 10.0.6:

```sh
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
for half in Left Right; do
  $K pcb export gerbers    --output out/$half/gerbers  pcb/kicad/Hojicha44-$half.kicad_pcb
  $K pcb export drill      --output out/$half/drill    pcb/kicad/Hojicha44-$half.kicad_pcb
  $K pcb export pos        --output out/$half/pos.csv  pcb/kicad/Hojicha44-$half.kicad_pcb
  $K sch export bom        --output out/$half/bom.csv  pcb/kicad/Hojicha44-$half.kicad_sch
done
```

Then: open the Gerbers in a viewer (e.g. KiCad's gerber viewer) and confirm the
outline, the notch, the fiducials, the tooling holes, and the silk.

---

## 6. Regeneration commands (in order)

Back up first (P0-3). Then:

```sh
# 1. Layout (config changed in P0-1 and P0-2 pending)
cp -R layout/generated/v2 /tmp/hojicha-v2-backup-$(date +%Y%m%d%H%M)
npx ergogen "layout/ergogen yaml" -o layout/generated/v2 --svg --clean
node layout/generators/dump_points.cjs
python3 layout/generators/export_kle.py --check
node layout/generators/render_preview.mjs

# 2. Schematic (audit + ERC)
python3 pcb/generators/gen_schematic.py

# 3. PCB placement + DRC
python3 pcb/generators/gen_pcb.py
```

Warning: `--clean` deletes `layout/generated/v2` (gitignored). The backup
above is the only copy.

---

## 7. Sources

Primary, external:
1. nice!nano getting-started and battery guidance — https://nicekeyboards.com/docs/nice-nano/ (B+/B- wiring; 301230 "fits underneath a socketed nice!nano").
2. nice!nano FAQ — https://nicekeyboards.com/docs/nice-nano/faq/ (B+/B- individual battery; TRRS warning; charger at 100 mA).
3. joric/nrfmicro wiki, *Batteries* — https://github.com/joric/nrfmicro/wiki/Batteries (RAW/GND and B+/B- internally connected; RAW for charger; RAW-VCC warning; 301230 between 4.5 mm sockets; BQ24072 in V2).
4. joric/nrfmicro wiki, *Alternatives* — https://github.com/joric/nrfmicro/wiki/ALternatives (nice!nano V2 uses BQ24072; V1 uses LN2054Y42AMR).
5. splitkb nice!nano FAQ — https://docs.splitkb.com/product-guides/nice-nano/frequently-asked-questions (TRRS and battery warning; search-snippet only, not fetched in full).
6. Kailh Choc v1 hole sizes (1.9 mm and 3.4 mm, per the spec sheet cited in the discussion) — Reddit r/ErgoMechKeyboards thread (search-snippet only; the Reddit page returned a certificate error when fetched).
7. Ergogen points documentation — https://docs.ergogen.xyz/points/ (stagger, splay, zone definitions).

Local (this project):
8. `spec/electronics.yaml`, `spec/layout.yaml`, `notes.md`, `README.md`.
9. `pcb/generators/gen_schematic.py`, `pcb/generators/gen_pcb.py`.
10. `pcb/kicad/Hojicha44-{Left,Right}-erc.rpt`, `…-drc.rpt` (generated 10:50 and 11:04).
11. `layout/ergogen yaml/config.yaml` (usb, mcu, outline definitions).

Not verified online (open): the nice!nano v2 pinout image and schematic; the
WS-SLTV datasheet; the EC11E shaft/bushing datasheet; the ZMK NFC overlay setting
for the chosen ZMK release.

---

## 8. Decisions needed from you

1. **TRRS:** keep as bring-up only (P2-1a), or replace with a 4-pin JST (P2-1b)?
2. **Routing layers:** start with 2 layers and move to 4 if needed (P2-2a), or go
   straight to 4 layers?
3. **Stagger and splay:** test a smaller middle→index step and a small splay
   (P2-3), or keep the current layout?
4. **Reset button:** add to both halves (P2-4)?
5. **Socket height and encoder:** pick the socket and the encoder variant now,
   or after a printed mock?

---

## 9. Status refresh (2026-10-14 — verified against the current files)

The table in §1 is stale as written; per-ID current state (evidence: fresh
`gen_schematic.py` / `gen_pcb.py` / `audit_silk.py` runs, both DRC reports):

- **P0-4 routing: DONE.** Deterministic 2-layer router (`gen_route.py`
  r10): Left 408 / Right 586 copper items, `unconnected_items` 0 both
  halves. DRC shows only waiver W1 (28× mismatch/half).
- **P0-5 battery: locked to orderable stock**, DMM outstanding. Primary
  kriscables 301230 110mAh + JST PH 2.0mm (verified listing: 3×12×30,
  3.7V, 100mA→full ~1.1h = 0.9C); alternates KEEBD / Typeractive (check
  stock). PCM mandatory; see `spec/bom.md`.
- **P0-6 parts: locked.** MPNs in schematic symbols + populated BOM
  export (`spec/bom.md`); cell + knob locked above; WS-SLTV pad-1-common
  verified; EC11E15244G1 locked.
- **P1-1 `+` mark: done**, no overlap (JST `+` rides translated).
- **P1-2 silk-over-pads: done by trim**, not waiver. All five sub-0.3mm
  Choc B.SilkS corners pulled to ≥0.49mm local clearance in the vendored
  footprint (rotation-proof); 0 `silk_over_copper` both halves. The W2
  waiver predicate stays in the gate unused.
- **P1-3 refdes overlap: no longer present** (0 `silk_overlap` either half).
- **P1-4 mismatch: kept as documented waiver W1, deliberately.**
  Project-local footprints (reversed socket column, renamed TRRS pads,
  pulled-in Choc silk) diverge from stock by design; the boards use the
  embedded copies. Never "update footprints from library" — it would erase
  these fixes. Accepted local override, no DRC-rule suppression.
- **P1-5 tooling: done** (2× 3.2mm NPTH/half, clearance-searched).
- **P1-6 ERC spares: kept as warnings, deliberately — no-connect NOT
  applied.** The 5 single-pin spares (RST, VCC3V3, A3, A2, D10) stay
  labeled: `no_connect` markers would hide future-use + UICR intent
  (recorded decision in `notes.md`). ERC reports 0 errors / 5 warnings
  per half and the build gate is green.
- **P1-7 docs: fixed** (flip wording, TRRS tip-to-tip prose matches the
  netlist — left TIP=TX/right TIP=RX crossover in right-half copper,
  joric battery citation, 301230 everywhere, USB-notch comment).
- **P1-8 TRRS silk edge: no longer present** (0 `silk_edge_clearance`).
- **P2-1 TRRS: (a) bring-up only**, documented fallback + power-off order.
- **P2-2 layers: resolved on 2 layers** — DRC-clean, no 4-layer move.
- **P2-3 ergonomics: frozen layout stands** (print test in first-article).
- **P2-4 reset: declined** (UF2 + bootloader; gasket seal; RST on pin 22
  for pogo). **P2-5: MPN locked.** **P2-6: NFC overlay drafted.**

Still genuinely open (need parts/toolchain): first-article procedure
(`spec/first-article.md` + 1:1 prints in `out/fit/`), `west build`,
keymap content.

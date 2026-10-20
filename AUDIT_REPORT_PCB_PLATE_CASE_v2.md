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

# Hojicha44 — Engineering Audit v2: PCB, Plate, Case

**Date:** 2026-10-19 · **Mode:** read-only (no repo changes; scratch scripts under the system temp dir)
**Supersedes:** `AUDIT_REPORT_PCB_PLATE_CASE.md` (v1 draft) — v1 remains valid for its PCB-netlist/routing
findings; this document adds the two findings v1 missed (§3) and re-verified/re-ranked the rest.
Working tree state at audit: **dirty** — the M3 power-switch relocation (boards, case, spec, notes)
exists only as uncommitted changes (HEAD = `112a2ff`).

---

## 1. Method

- Parsed both `.kicad_pcb` files with a custom sexp parser (footprints, nets, tracks, vias, edge
  clearances, antenna keepout, fiducials, matrix topology) — scratch script `audit_pcb.py`.
- Read every spec/source file: `spec/electronics.yaml`, `spec/layout.yaml`, `spec/case.md`,
  `spec/bom.md`, `spec/first-article.md`, `notes.md` (incl. all three review rounds),
  `case/params.py`, `case/gen_case.py`, `case/gen_cover.py`, `plate/gen_plate.py`,
  `pcb/make_release.py`.
- Parsed generated artefacts: plate DXFs (layer/entity census, cutout sizes, PORON pads),
  released drill files in both `generated/release/v0.3.1/` and `pcb/- FINAL/`, DRC/ERC reports.
- Measured the vendored 3D models: PJ-320A STEP, ROT_EC11E STEP, Choc hotswap socket WRL
  (KiCad units ×2.54), and the **PG1350 switch model** (koktoh `choc/v1/KiCad/red.wrl`, fetched
  per the URL vendored in `pcb/render.py:44`; my parse reproduces the project's own
  "15.0×15.0×11.0 = published profile exactly" check, validating the pipeline).
- Cross-checked external facts (Choc plate standards, nice!nano reset button, socket dimensions).

---

## 2. Executive summary — act on these first

| # | Sev | Finding | Action |
|---|-----|---------|--------|
| B1 | BLOCKER | The only released gerbers (`generated/release/v0.3.1`) contain the **known-defective M2 power-switch position** (102.0/189.5); the correct M3 board (106.3/185.2) is **uncommitted**; `make_release.py --check` reports **false CLEAN** because it ignores dirty working trees. A second stale tree (`pcb/- FINAL/`, 104.0/187.5) is also tracked. | Commit M3, re-cut the release, quarantine `pcb/- FINAL/`, harden `--check`. |
| B2 | BLOCKER | **The PCB has no vertical support.** The plate cutout (15.0) is exactly the Choc clip-wing envelope (15.0 measured), which sits *inside* the plate band → zero bearing area, zero friction. The load path claimed in three places ("the PCB hangs from the plate on the switches") does not exist. On assembly the board **sags ~1.95 mm onto the case floor**, breaking USB, TRRS and the power-switch aperture. | Decide the support strategy (§3.2 a/b/c) before ordering plate or case. |
| H1 | HIGH | `case/params.py` M1 comment and the case spec claim Choc hotswap sockets are **top-side**; they are on **B.Cu** (bottom). FLOOR_Z −5.6 still clears, but the ruler's frame/value are wrong and the rationale is false. | Fix docs/ruler; no CAD change. |
| H2 | HIGH | First-article test *"clips engage, no rock"* is **unachievable** with a 15.0 cutout and contradicts `spec/case.md`'s own *"clips never touch"*; the suggested rev-2 tweak (15.0 → 14.9) would not create retention. | Rewrite the test to the real load path (after B2 is decided). |

---

## 3. BLOCKER findings

### B1 — Release package is stale; the release gate gives a false CLEAN

**Evidence (three different power-switch positions across four artefacts):**

| Artefact | Left pwrsw centre | Right pwrsw centre | Provenance |
|---|---|---|---|
| `generated/release/v0.3.1/{Left,Right}/*.drl` (authoritative) | **102.00** | **189.50** | manifest commit `8092ca2`, tag `…-dirty` |
| `pcb/kicad/Hojicha44-*.kicad_pcb` @ HEAD `112a2ff` | 102.0 | 189.5 | committed board state (= M2) |
| `pcb/kicad/Hojicha44-*.kicad_pcb` **working tree** | **106.3** | **185.2** | uncommitted M3 fix |
| `pcb/- FINAL/` (older tracked release) | 104.00 | 187.50 | manifest commit `3016153` (16 Oct) |

- `notes.md` M3 entry (uncommitted): the M2 "2 mm WEST" shift *"ran the wrong way and left the
  blade band wholly behind the wall"* — i.e. **the released position (102.0) is a documented real
  defect**, and the case mouth in `case/gen_case.py:213` is cut for the M3 position (106.3/185.2).
- `pcb/make_release.py:43-51` `board_commit()` compares the manifest commit against
  `git log -1 --format=%H -- <board sources>` — **it cannot see uncommitted modifications**. With
  the M3 board edits sitting in the working tree, `make_release.py --check` prints
  `CLEAN (boards @8092ca28ce3c)` while the only correct board exists nowhere in git.
- Consequence: ordering boards today from either tracked gerber tree yields a power switch whose
  lever band sits **2.3 mm (pcb/- FINAL) or 4.3 mm (v0.3.1) west of the case mouth** — the exact
  defect M3 was written to fix (lever hidden behind the wall).

**Why it matters:** fabricated boards are the one artefact that cannot be patched; the case (cut for
106.3) and the boards (102.0) would never align.

**Fix:**
1. Commit the M3 state (boards, `case/params.py`, `case/gen_case.py`, `spec/first-article.md`,
   `notes.md`, regenerated DXFs) as one reviewable commit.
2. Re-cut `generated/release/v0.3.1` (or cut v0.3.2) so the drill shows 106.3/185.2; verify the
   MANIFEST stamp.
3. Quarantine `pcb/- FINAL/`: delete it or add a `README-LEGACY.md` marking it superseded — two
   tracked gerber trees with different content is a standing footgun.
4. Harden the gate: `make_release.py --check` must fail when
   `git status --porcelain -- pcb/kicad pcb/generators spec/electronics.yaml` is non-empty, and
   (optionally) diff drill hole sets against the working-tree boards.

---

### B2 — The PCB is vertically unsupported; the "hangs off the switches" load path does not exist

This is a geometry fact, established from the project's own vendored PG1350 model, and it
contradicts the project's own mounting axiom.

#### 3.2.1 Measured PG1350 cross-section (koktoh red.wrl; z = 0 at PCB top, pins to −3.0, 3.2 mm
boss to −1.5 — consistent with the footprint's 3.45 NPTH and the socket contact zone −0.42…−3.47):

| Height band (above PCB top) | Switch envelope |
|---|---|
| z 0.0–0.5 | 12.96 sq |
| **z 0.5–1.0** | **14.5 × 13.6** (base flange; top face at z = 1.0) |
| z 1.0–1.5 | 13.8 sq |
| z 1.4–2.1 | waist 10.8–12.0 |
| **z 2.2–3.0** | **exactly 15.000 × 15.000** — the clip-wing envelope (four corner-diagonal ears; 5 176 model points reach ±7.4–7.5 in both axes; bottom face ring at z 2.2, top face ring at z 3.0) |
| z 3.0–3.5 | ≤ 13.8 (upper housing) |
| z 4.5–5.0 | 12.7 |

Reference mechanics: the standard Kailh Choc plate mount uses a **13.8 mm cutout in a 1.2 mm
plate**; the plate lives in the groove between the base-flange top (z = 1.0) and the wing bottom
face (z = 2.2) — a 1.2 mm groove — and is retained because the flange (14.5) and the wings (15.0)
are both larger than the hole. Plate-to-PCB gap in that scheme ≈ 1.0–1.2 mm.

#### 3.2.2 What this design does

- `plate/gen_plate.py:58`: `CUTOUT = 15.0  # switch body is 15x15`; 18 axis-aligned + 4 rotated
  cutouts per half, all exactly 15.000 (DXF-verified).
- Plate band: underside +2.0, top +3.5 (`spec/case.md` stack table).
- Therefore the clip-wing envelope (15.0, z 2.2–3.0) sits **inside the plate band** with
  **exactly zero clearance** — cutout = wing envelope = 15.000:
  - **Zero bearing area:** the wing's bottom-face annulus lies entirely *inside* the hole's plan
    (material starts at ≥ 15.0). Contact could only occur on a mathematical line.
  - **Not even line contact at nominal:** the wing bottom face (z 2.2) is **0.2 mm above** the
    plate underside (z 2.0).
  - **The project's own kerf expectation kills any doubt:** `spec/first-article.md:168` —
    *"Laser kerf enlarges cutouts ~0.1–0.2 mm, so expect a slip fit"* → hole ≈ 15.1–15.2 >
    wing 15.0 → the wings pass through freely; friction = 0 (no normal force).
  - The base flange (14.5) also passes freely (14.5 < 15.1), so the plate cannot bottom out on
    the switch either — it just floats, foam-set at 2.0.

#### 3.2.3 The load path the design relies on — quoted contradicting claims

| Claim | Location |
|---|---|
| "PCB … hangs from the plate on the switches" | `spec/case.md:33` |
| "poron pads hold TABS, PCB hangs off the switches; the case never clamps the board" | `spec/electronics.yaml:288` |
| "the PCB hangs from the plate on the switches; bottom-case foam is acoustic only" | `plate/gen_plate.py:593` |
| "body clearance, not a clip fit … 15.0 gives ~0.6/side and the side clips never touch … retention here is friction + the hotsockets" | `spec/case.md:270-274` |
| "Seat one real Choc switch per region: clips engage, no rock" | `spec/first-article.md:167` |
| "switch body is 15×15" (used to justify 15.0) | `plate/gen_plate.py:58` |

These cannot all be true, and the measurements say which way each one fails:

- *"Lower body passes at 13.8, 0.6/side"* — the section in/near the plate band is the **15.0 wing
  envelope** (0.0/side); 13.8 applies to the upper housing at z 3.0–3.5 and the neck at 1.0–1.5;
  the base flange is **14.5** (0.25/side). The quoted numbers describe the wrong features.
- *"Clips never touch"* — true only in the kerf'd sense; at nominal they are exactly flush, and in
  neither case is there any retention.
- *"Retention is friction + the hotswap sockets"* — friction needs a normal force; there is none.
  The hotswap sockets retain **switch↔PCB**, not **PCB↔plate**.
- *"PCB hangs from the plate on the switches"* — impossible: no vertical force path exists between
  the plate and the switch at CUTOUT = 15.0, and the groove geometry that *would* provide one
  (1.0–2.2) is incompatible with the 2.0 mm gap chosen for the 1.35 mm top-side diodes and with a
  1.5 mm plate.

#### 3.2.4 Consequence: the sag

Nothing else holds the board up (verified):
- Bottom gaskets sit on the tab tongues, spanning plate-rim → +4.0 mm outboard — **0 mm overlap**
  with the PCB rim; they pre-load the *plate*, never the board.
- Case cavity = plate outline + 0.5 mm — no vertical constraint.
- The floor was left deliberately clear: `case/params.py:24-31` — deepest known protrusion
  **−3.65 (encoder legs)** → `FLOOR_Z −5.6` "keeps ~1.95 mm clearance".

So the PCB + switches + sockets assembly free-falls until its deepest bottom-side features rest on
the floor: **sag ≈ 1.95 mm** (encoder legs touch at 1.95; slide-switch legs −3.5 and socket bodies
−3.47 at 2.0–2.13). The board settles ~1.95 mm low, slightly tilted, resting on leg tips.

Port damage from a 1.95 mm sag (all numbers case-frame, at nominal vs sagged):

| Port | Nominal | After sag | Verdict |
|---|---|---|---|
| pwrsw lever band | z 5.0–6.4, aperture sill 4.3 | 3.05–4.45 | 0.15 mm sliver above the sill — **flick impossible**; negates the entire M3 fix |
| USB plug overmold bottom | 2.8 vs sill 2.0 | 0.85 vs 2.0 | overmold hits the wall — **plug cannot fully seat** |
| TRRS jack axis | 2.5 (bore Ø9.5 @ 2.5) | 0.55 | plug shaft centres at ~2.5 in the bore but the jack opening is at 0.55 (±0.5 window) — **plug jams on the jack face** |
| plate↔PCB gap | 2.0 (diode clearance 0.65) | ~3.95 | diode feeler passes *vacuously*; every "gap = 2.0" stack check becomes meaningless |
| encoder knob | rides 18 above plate | 16 | cosmetic/feel only |

**Why it matters:** the board is buildable and still fails on first assembly — and no test in
`spec/first-article.md` catches the *cause*: the "Gasket preload" test stacks plate + pads **without
the PCB**; the diode-feeler test passes with an oversized gap; the port-bore checks compare the
*case* to *nominal* coordinates. Only the PWR flick / plug-insertion tests would reveal the symptom,
after everything is fabricated.

#### 3.2.5 Fix options (decide first, then re-derive the stack)

- **(a) Support the board from the case — recommended for this geometry.** Add poron risers under
  the PCB rim (e.g. duplicate/relocate the 8×4 pads inward so they lie beneath the board edge and
  step the local floor to ≈ −1.6 − 2.55 = −4.15 under them), keeping the board foam-borne at
  nominal height. Update `spec/electronics.yaml:288` ("the case never clamps the board" →
  "foam-borne, not clamped") and the case stack table. Port bores, foam percentages and the 1.95 mm
  floor margin then hold as designed.
- **(b) Make the hang real** (bigger change): diodes → B.Cu, cutout → 13.8–14.0, plate → 1.2 mm.
  The switch groove (1.0–2.2) then does the retaining, the plate gap drops to ≈1.0–1.2, and the
  whole z-chain (shelf, lip, port z, foam percentages, encoder band) must be re-derived. Note this
  is close to the repo's own rev-2 sketch (`spec/case.md:276` "~14.0 cutout + 1.2 mm plate") — that
  sketch, as written, would collide the 1.35 mm diodes with the plate unless they move.
- **(c) Keep 15.0/2.0 and delete the hang claim**: make the floor the datum (FLOOR_Z = −1.6 − ε,
  solid contact). This contradicts the acoustic-floor design and moves every port z; least
  attractive.

Add to the first article (regardless of choice): *with switches seated and the case open, measure
the plate-to-PCB gap (expect 2.0; ≈4.0 confirms the sag), and lift the plate alone — if the PCB
does not come with it, retention is absent.* This replaces the unachievable "clips engage" test
(see H2).

---

## 4. HIGH findings

### H1 — "Hotswap sockets are top-side" is false; they are on B.Cu

- Claim: `case/params.py:21-23` — *"M1, review-corrected: the hotswap SOCKETS are top-side —
  module 4.5..7.7 — and never hang below the board"*, with the FLOOR_Z ruler listing *"Choc socket
  bump −1.25 (Kailh datasheet)"*. The case stack note repeats the idea by lumping "sockets +
  clearance" into the floor rationale.
- Ground truth: the hotswap pads are on **B.Cu** (`Hojicha44.pretty/SW_Hotswap_Kailh_Choc_V1_1.00u.
  kicad_mod`, socket pads `B.Cu`), the socket WRL spans z −0.42…−3.47 (≈1.9 mm below the PCB
  bottom; body per Adafruit 13.0×5.6×3.0), i.e. socket bottom ≈ **−3.47**, not a top-side +1.25 bump.
  (The comment conflates the nice!nano sockets — genuinely top-side, module 4.5–7.7 — with the Choc
  hotswap sockets.)
- Impact: `FLOOR_Z −5.6` still clears (2.13 mm under sockets; 1.95 mm under encoder legs remains the
  binding number) — **no CAD change needed** — but the ruler's frame and value are wrong, and any
  future re-derivation from "sockets never hang below the board" would produce a floor that
  collides. Fix the comment/ruler: "Choc socket bottom ≈ −3.47 (measured, kiswitch WRL); encoder
  legs −3.65 binding".

### H2 — First-article switch test is unachievable and self-contradictory

`spec/first-article.md:165-170`: *"Seat one real Choc switch per region … clips engage, no rock …
If loose in every region, rev-2 cutout tightens 15.0 → 14.9."*

- With CUTOUT = 15.0 the clips cannot engage (flush at nominal, free with kerf) — the test as
  written cannot pass, and it contradicts `spec/case.md:270-273` ("clips never touch").
- "No rock" will likely **fail** after kerf (0.05–0.1 mm/side slip), by the project's own criterion.
- The proposed remedy (14.9) would give a 0.05 mm-wide bearing ring engaged only after 0.2 mm of
  sag — not retention.
- Rewrite after B2 is decided: e.g. "switch seated, plate at nominal: measure plate-to-PCB gap =
  2.0 ±0.2; lift plate — PCB+switches follow (hang) or do not (case-supported, per B2a)".

### H3 — PORON layer in the cuttable plate DXF can sever the gasket tabs

The PORON layer contains the 8×4 mm pad rectangles (closed polylines) that lie **on top of** the
tab tongues: radially they span plate-rim → +4.0 on a 5.0 mm tab. If the fab "cuts all closed
shapes", each tab loses its outer 4 mm — the gasket surface and half the jacket entry. The DXF
carries 3 real layers (OUTLINE/CUTOUT/PORON) plus entity noise; layer-separated quoting is common
but not guaranteed. **Fix:** ship the PORON layer as a placement drawing only (PDF, or an explicit
fab note "PORON layer = adhesive pad placement, do not cut"), or move pads to a clearly
non-cut layer name.

---

## 5. MEDIUM findings

### M1 — pwrsw wall bore is likely redundant
The switch actuator (y ≈ 51) sits ≥6.25 mm inside the open cavity (north rim plateau y = 58) and is
reachable from above with the cover fitted (the ring cover spans only the wall band; the cavity
interior is open). The M2 flick test already flicks it from above. The side mouth costs ring
integrity (the design itself warns a full-width cut would break the ring) and adds the entire M3
complexity. Rev-2 option: delete the side aperture; keep the switch, flick from above.

### M2 — Encoder shaft clearance depends on foam-set lateral position
Shaft/hole clearance is 0.20/side (12.30 body vs 12.7 hole), but the PCB's lateral position is set
only by foam shear and the 0.5 mm cavity margin. The shaft can rub the hole edge on hard foam or
after drops. First article: knob-on wiggle test (±1 mm expected free, no scrape).

### M3 — Minimum copper-to-edge 0.292 mm (Left half)
Below the 0.3 mm class figure quoted elsewhere in the project's own review notes (Right half:
0.626 mm to the nearest pad). Within typical fab capability (≥0.2 mm) — accept explicitly or nudge
the offending track in rev-2; do not leave it as an unremarked sub-0.3.

### M4 — Case material/process unspecified
`spec/case.md` fixes geometry and magnet pockets; first-article fixes print orientation only. No
material (PETG/ABS/PLA?), nozzle/layer height, wall count or infill is specified for the tub and
ring — all of which drive warpage, magnet-pocket tolerance (Ø4.2 press), and port-bore dimensional
drift on which the ±0.5 mm port checks depend. Add a materials line, e.g. "PETG, 0.4 nozzle,
0.2 layer, ≥4 perimeters, 30-40 % gyroid".

### M5 — USB slot length vs overmoulds
14.0 mm slot vs 12.35 mm receptacle housing (0.8/side) is fine for bare connectors; overmoulded
cables and strain-relief boots are frequently 14–16 mm wide. Under B2's sag the margin inverts.
First article: test ≥3 real cables; consider 15.0 mm in rev-2.

### M6 — Diode symbol/MPN mismatch
`Diode:1N4001` symbols carry MPN `1N4148W`. Electrically verified correct (COL2ROW pad mapping
checked end-to-end), but the symbol name will mislead assembly and BOM review, and contributes to
the 28 `lib_footprint_mismatch` W1 waivers per half. Rev-2: swap to a 1N4148-family symbol.

---

## 6. LOW / NIT

- **L1** — Pinned-tab prose in `spec/case.md` ("top edge above the outer column, bottom-inner under
  the MCU") does not match the actual tab coordinates (T4 ≈ 95.0, 57.8 north/inner; T6 ≈ 120.9,
  −53.5 south). Doc-only; align the prose or delete it (the generator is the contract).
- **L2** — No bottom-side fiducials/pos entries: correct for the current hand-solder-44-sockets BOM,
  but note it if an assembly house ever builds the B.Cu side.
- **L3** — Two tracked release trees (see B1): even after quarantining `pcb/- FINAL/`, consider
  gitignoring `generated/release/` build outputs or tagging releases so "which folder do I order
  from?" has one answer (`generated/release/…`).
- **L4** — `nice!nano` has an onboard reset button reachable through the open ring interior —
  no case reset access required (verified; recorded so it is not re-raised).
- **L5** — ERC's 5 isolated-label warnings per half are the documented intentional spares; the
  waiver trail is good. No action.
- **NIT** — The vendored EC11 STEP contains stray construction geometry (bbox unreliable); the
  project already benches-verifies encoder dimensions — keep that test.

---

## 7. Verified claims (checked in this audit; all confirmed)

**PCB (both halves unless noted)**
- 54 footprints, 48 nets; DRC: 0 errors, 0 unconnected, 28 W1 `lib_footprint_mismatch` per half.
- Track widths: 0.25 signal / 0.5 `VBAT_SW`; vias 0.6/0.3 (signal) and 1.0/0.5 (power).
- Matrix: COL → SW.1 → SW.2 → D.A (anonymous net) → D.K → ROW = COL2ROW; diodes on F.Cu;
  hotswap pads on B.Cu.
- TRRS crossover correct on both halves (Left D1→TIP, D0→RING1; Right D1→RING1, D0→TIP) — a
  straight cable yields TX↔RX; RING2 unconnected both ends.
- MCU pin map matches `pin_map` (pads 5–20: COL2/COL3/ROW0-3/COL0/COL1/D10/ENC_SW/COL4/COL5/
  ENC_A/ENC_B; VCC/RST/GND/RAW).
- Antenna keepout: r = 5 copper-free; antenna centre 13.65 mm from board edge; case generators gate
  ≥3 mm of non-plastic-free material.
- Fiducials non-collinear (valid for vision).
- Switch pitch exactly 19.00 mm.

**Plate**
- Per half: 18× 15.000² switch cutouts + 4 rotated (thumb) + 1× 12.7² encoder square; OUTLINE
  bbox 155.65×123.88; PORON layer present (8 pads × 8 tabs × top/bottom placement).
- Tab/pad geometry: tab 10 wide × 5.0 protrusion; pad 8×4 centred +2.0 outward → radial span
  rim → +4.0 (0 mm overlap with PCB rim — basis of B2's "pads cannot support the board").

**Case**
- `SHELF_Z = −0.55 = 2.0 − 3.0×0.85`; bottom foam −0.55 → 2.0 = 2.55 mm = 15 % ✓; top foam
  3.5 → 6.0 = 2.5 mm = 16.7 % ✓; cover ring 6.0–9.0; lip clearance chain closes.
- Wall over tab tip = 7.0 − 5.0 − 0.5 = 1.5 mm ✓; magnet pockets Ø4.2×2.2.
- Port anchors: USB slot 14.0 @ z 2.0–6.0; TRRS bore Ø9.5 @ axis z 2.5; pwrsw aperture sill 4.3.
- FLOOR_Z −5.6 clears the true deepest protrusion (encoder legs −3.65) by 1.95 mm; socket bottoms
  (−3.47) clear by 2.13 mm.
- Generator gates (prior runs, unmodified by this audit): `gen_plate --check` CLEAN; tub 67.4 cm³,
  wall_min 1.49/1.50; cover 9.0 cm³, wall_min 5.85; `check_board.py` CLEAN; `audit_silk.py` OK.

---

## 8. Open questions

1. **B2 strategy (a/b/c)** — decides the floor, plate gap, cutout, plate thickness and the entire
   foam/port z-chain. Everything else waits on this.
2. **Real PG1350 wing tolerance** — the model measures exactly 15.000. Measure a real switch on the
   first-article coupon: ≥15.05 means even a nominal-15.0 plate would jam; ≤14.95 leaves a
   knife-edge ring. Neither outcome is a fix; both confirm B2.
3. **Release hygiene** — keep or delete `pcb/- FINAL/` from the tree? Single source of truth for
   ordering?
4. **Case material** (M4) — print process to be fixed in the spec before the first tub is printed.
5. **Side access to the power switch** (M1) — required at all, or is top-flick sufficient?

---

## 9. Suggested action order

1. Commit M3; re-cut the release; harden `make_release.py --check`; quarantine `pcb/- FINAL/` (B1).
2. Decide the PCB support strategy and re-derive the affected z-chain (B2) — then update
   `spec/case.md`, `spec/electronics.yaml`, `case/params.py`, `plate/gen_plate.py` together.
3. Fix the socket-side docs/ruler (H1) and rewrite the first-article switch test (H2).
4. Add the PORON fab note (H3); sweep the MEDIUM/LOW doc and rev-2 items.

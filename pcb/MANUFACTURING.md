# Manufacturing order guide (v0.5.0)

The exact answers for the JLCPCB Online PCB Quote, derived from the
committed design + vendor research (2026-10; sources at the bottom).
The live quote remains the only authority for anything price-shaped,
but every design-shaped field below has exactly one right answer.

## Frozen design facts (why several fields have one right answer)

| fact | where it's pinned |
|---|---|
| thickness **1.6mm** | `case/params.py` models the PCB bottom at -1.6 (case shelf/floor geometry) |
| outline **150.5 × 114.6mm** per half | Edge.Cuts extents — bigger than the 100×100 quote cell |
| smallest via **drill 0.30 / pad 0.65** | `gen_route.py` via rules (0.6/0.3 → 0.65/0.30); min drill scan = 0.30 both halves |
| smallest copper clearance **0.20 / 0.25** | signal / power pad classes |
| currents ≤ **0.5A** (charge jumper open; BLE-only) | `spec/electronics.yaml` charger block |
| finish **ENIG** | stamped into each `*.gbrjob` by `pcb/make_release.py` |
| no pours, no gold fingers, no castellations, no UL | by design (DRC-clean 28-waived release) |
| silk text **1.0mm / 0.15 stroke** | `gen_pcb.py` gr_text/fonts — at the vendor's guaranteed minimum, not below |

## The quote, field by field

| form field | value | why |
|---|---|---|
| Base Material | **FR-4** | RF is a pre-certified module; substrate RF loss is irrelevant. Nothing else is honest.
| Layers | **2** | as designed |
| Product Type | **Industrial/Consumer** | standard QC flow; Aerospace/Medical = fees for inspection we neither need nor asked for |
| PCB Qty | **5 per design** (10 total) | JLC minimum is 5 per design; qty 5 carries the fixed setup cost — hobby demand ≈ 5 |
| PCB Thickness | **1.6mm** | case constant (above); ±10% metal tolerance (1.44–1.76) is why the case keeps freeboard |
| PCB Color | **Black** (alt: purple) | aesthetic-only; current JLC policy = same fee for all standard colors **(verify in live quote)**; white-on-black hides solder flux best |
| Silkscreen | **White** | pairs with black mask; our art is already 1.0mm/0.15 = the guaranteed legibility floor |
| Material Type | **FR4-TG135** (first option) | TG class matters only for lead-free *reflow* (PCBA) or sub-5-mil pricing; 2-layer won't be there |
| Surface Finish | **ENIG** | flat pads (hotswap sockets sit flat), long shelf life, no HASL dome under sockets, and ENIG tolerates the sub-0.2mm exposed-clearance rules that HASL bridging restrictions would fight. Black-pad is a reflow/BGA failure mode — hand-solder doesn't hit it |
| Outer Copper Weight | **1 oz** | ≤0.5A and no pours: 2oz costs more, changes min-trace rules, buys nothing |
| Via Covering | **Tented** | sealed vias can't wick solder while hand-soldering near sockets; mask openings in the gerbers rule regardless of this toggle |
| Via Plating Method | **Not Specified** | the standard plating is implicit; the other two are filled-via/HDI-class options |
| Min via hole size/diameter | **0.3mm/(0.4/0.45mm)** tier | smallest finished hole = 0.30 with 0.65 pads — comfortably inside the free tier |
| Board Outline Tolerance | **±0.2mm (Regular)** | case clearances were designed ≥0.5mm; ±0.1 buys nothing (and thickness ±10% dominates any fit conversation) |
| Confirm Production file | **No** | nothing ambiguous in the files; a "Yes" adds an email-confirm roundtrip. If JLC sends an engineer question anyway, answer it before they build |
| Mark on PCB | **Remove Mark** | no fab barcodes on a finished keyboard half (~$1.50); the free 2D barcode is the cosmetic alternative |
| Electrical Test | **Flying Probe Fully Test** | trivial adder at qty 5; catches what the eye won't |
| Gold fingers / Castellated / Edge plating / Blind slots / UL / Humidity card | **No ×6** | none apply; edge plating would even trigger extra review |

## Ordering mechanics (two designs, one keyboard)

- **Left and Right are two separate designs.** Either one checkout with
  "Different Design: 2", or two orders — each design is billed its own
  5-pc minimum. Don't merge them into one panel/gerber: per-extra-design
  fees exist and a shared panel of this size gains nothing.
- The released artifacts are `generated/release/v0.5.0/{Left,Right}/`
  (9 gerbers + job + drill + pos + pos-smt + bom + ERC/DRC each; zip
  each half's folder for upload). Cross-check the MANIFEST stamp
  (`git commit:` / `board sha256:` lines in
  `generated/release/v0.5.0/MANIFEST.txt`) — the ERC/DRC reports in the
  release are re-run at cut time, and the manifest records the board's
  hash, so the release certifies those exact bytes.
- **Only `generated/release/vX.Y.Z/` is fab-pointable.** The pre-M3
  `pcb/- FINAL/` tree is removed; it had stale power-switch pads and
  pinned an uncommitted board (`3016153-dirty`). Historical audit
  reports may still mention it.
- **Frame note (v0.5.0):** the `.kicad_pcb` is stored y-negated so
  KiCad's y-up Gerber/drill/pos exports land in the plate/case design
  frame. The board title block records
  `(comment 3 "frame: storage-yneg")`; readers convert with
  `pcb/generators/frame.py`. The release gate
  `python3 pcb/generators/check_board.py --self-test` proves the
  released T12/T10 holes and USB-notch outline match the plate, and
  proves a Y-negated control fails. DRC is run on the geometrically
  identical design-frame reflection (same project rules), because
  KiCad compares footprint-local geometry to the libraries.
- **Concave outline — TAB-ROUTE ONLY, NO V-CUT / V-SCORE.** The
  measured minimum copper-to-edge is 0.292mm — below the 0.3mm a V-cut
  wants (and the outline is concave: V-cut wants a straight edge), but
  ABOVE the 0.2mm **tab-route** rule (JLCPCB 2026 layout guide: "0.3mm
  for V-cut panelization and 0.2mm for tab-routing"; outline blog:
  "at least 0.2mm clearance from routed edges to copper features"), so
  the notch corridor passes the applicable published rule with 0.092mm
  margin (re-verified 2026-10-23). CNC routing tolerance ±0.1mm
  precision / ±0.2mm regular (capabilities page) — prefer the
  precision tier at quote if offered. Put this in the fab order verbatim:
  `CONCAVE OUTLINE — TAB-ROUTE ONLY, NO V-CUT / V-SCORE`
- The ENIG pick in the **gbrjob is informational only** — the form's
  Surface Finish choice is what the fab actually executes. Pick ENIG
  there or the stamp ships nothing.
- Budget reality: >100×100mm boards scale their fabric+finish cost with
  area; a 5-pc ENIG order of this size has been seen around
  **$35–70 before shipping** (unconfirmed — the live quote decides; both
  halves carry the surcharge).

## Assembly

- **Intent is hand-solder**: diodes (D_L*/D_R*), the **44 Choc v1
  hotswap sockets** (soldered on B.Cu under each switch — they are
  footprint-only parts, so they carry no MPN and never appear in the
  released `bom.csv`; order them from `pcb/BOM_ORDER.md`), the 2
  **EC11E15244G1 encoders**, the Nice!Nano socket headers, TRRS THT,
  and the pwrsw/JST. The SWITCHES themselves are never soldered (they
  plug into the hotswap sockets). ENIG is the friendly finish for
  exactly this.
- JLC machine PCBA is *possible* (`pos-smt.csv` shipped for it) but low-
  value here: the bulk of the part count is hand-placement-class, and
  their parts library won't hold the keyboard-bit parts. Skip unless a
  coupon credit is burning a hole in the account.

## Non-PCB orders (case, plate, magnets)

- **Case tub + ring cover: MJF PA12 nylon.** Best press-fit realism for
  the Ø4.3×2.2 magnet recesses, gasket compression and the magnet
  zero-gap stop (the retention is recessed magnets — there is NO snap
  lip in this design; the ring magnet seats against the tub lip
  plane); JLC MJF build ~72h. Generate with
  `case/.venv/bin/python case/gen_case.py` +
  `case/gen_cover.py` (STEP out; volumes 71.1/71.1 cm³ at OUTSET 8.2,
  measured 2026-10-22 with the current generators — 75.7 predates the
  top-lip 4.70 rev).
- **Plate at 1.2mm: PC (default, per spec/case.md — the generator's
  MATERIAL constant) or POM (the firmer upgrade) or CNC aluminum.**
  **1.2mm is not a free choice: the Choc v1 clip only engages a 1.2mm
  plate** (at 1.5/1.6mm the switch has no retention).  The plate also
  carries a **0.55mm relief pocket in its underside under each of the
  22 diodes** (RELIEF layer in the DXF; the DXF text entity repeats the
  depth) — machine that depth, do NOT cut through it.  The **encoder
  window is 16.2 x 12.4** (rev 1's 12.7 square fouled the encoder's
  terminal blocks at the rev-2 plate height — measured off the
  vendored EC11E STEP).  The
  plate's W1 windows keep the MCU/battery/USB region clear, so even
  metal doesn't blanket the module; PC wins all-round for rev 1 (quiet,
  cheapest prototype, laser-cut, no antenna-second-guessing). Files:
  `plate/gen_plate.py`
  (DXF/SVG kept in `plate/`).
- Acrylic is the anti-recommendation: brittle at the gasket tabs.
- **Magnets ordered separately** (N52 Ø4×2, axially magnetized) — see
  `spec/first-article.md` for the seat-force verify gates and the
  tub/cover polarity pairing note.
- **H-7 mirror gate (v0.4.0+):** the plate/case halves must be exact
  mirrors before ordering. Run `python3
  pcb/generators/check_board.py --self-test` (board 0.0000mm, plate
  0.0100mm) and `case/.venv/bin/python case/mirror_gate.py` (tub
  0.0094mm, cover 0.0000mm); the floor is 0.05mm and both gates include
  negative controls. The right plate's gasket tabs are now derived from
  the left roots (`plate/gen_plate.py`), not re-walked independently.

- **Compliance (decided, see `spec/compliance.md`):** the pilot market
  is **AU/NZ** and the path is the **RCM via an ACMA-only Responsible
  Supplier** (free registration) + the ACMA **C02 SDoC** + the RCM
  label.  Do NOT buy a certification at pilot volume (a lab SDoC is
  ~AUD 600–1,500, 1–3 weeks).  Two things to settle BEFORE the board
  order: (1) the **Bluetooth SIG** listing — the Adopter tier is
  **free**, and the money is the one-off Product Qualification Fee
  (**USD 12,000** + a **USD 1,250** Company Identifier) which is only
  due if a unit is **sold or branded** (the SIG's trigger is
  "selling, branding, manufacturing, or representing a product as its
  own"). Our keyboard is an Unmodified Design (Nordic's qualified
  nRF52840 + ZMK), so it lists with no new RF testing. A self-built
  pilot that is never sold owes the SIG nothing; SIG membership is
  also company-only, so an individual needs an entity. (2) keep the RCM
  label a **sticker**, not case printing, until the market is fixed.
- **Pilot batch: 5 half-pairs (10 halves)** — see `spec/first-article.md`
  §0 for the order quantities and the indicative ~USD 35–70/half unit
  cost.

## Before you click buy

1. Live-quote the size surcharge (both halves, separately) and any
   current color fee — the numbers above are research, the quote is
   truth.
2. Confirm the coupon's T&Cs: ENIG/big-area orders are a common
   exclusion from promos.
3. The silk text ships at exactly the vendor's guaranteed minimum
   (1.0mm/0.15) — passing today, but don't shrink anything.
4. DIY assembly needs: 1N4148W + pin headers + modules + magnets;
   distributor SKUs are the open BOM homework (see the release BOM or
   spec/bom.md).

## Sources (research basis, 2026-10)

- https://jlcpcb.com/help/article/different-design-in-your-pcb-files
- https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra
- https://jlcpcb.com/blog/pcb-pricing-breakdown
- https://jlcpcb.com/help/article/pcb-via-covering
- https://jlcpcb.com/capabilities/pcb-capabilities
- https://blog.poly.nomial.co.uk/2025-07-05-tips-for-getting-pcbs-made-with-jlcpcb.html
- https://jlcpcb.com/help/article/how-to-confirm-the-production-file

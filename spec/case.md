# Hojicha44 — case interface (plate + gasket contract, rev-1)

Source of truth for plate geometry: `plate/gen_plate.py`
(derives from the placed PCB; never hand-edit CAD).
Preview: `plate/Hojicha44-{Left,Right}-plate.svg`
Laser file: `plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm)
Tab map: `plate/Hojicha44-{Left,Right}-lands.json` (root centers for
jacket pockets)

## Mounting: tab-and-jacket suspension

The plate grows 8 discrete tongues per half (10mm wide, 5mm proud,
2mm root fillets, chamfered tips), each carrying a poron pad top and
bottom — no rim strips, no plate screws, no hard contact anywhere. Two
tabs are pinned (top edge above the outer key column, bottom-inner
corner under the MCU); the rest spread even. Support uniformity comes
from identical poron-padded tabs at even spacing, not from foam
proximity. The inner
(microcontroller) edge carries no tab: MCU/TRRS/encoder windows occupy
it fully and the remaining rim finger is narrower than a tab root, so
that zone floats between its flanking tabs by design — encoder push
stays soft there.
Encoder push over the window zone stays soft by design.

## Stack (top to bottom, per half)

| Layer | Spec |
|---|---|
| Top case | BUILT — **top plate v4** (`case/gen_cover.py`, gates exit-0): thin plate spanning z **3.20..5.20** (lip 3.20 = plate top 2.20 + 1.00 compressed top foam; 2.0mm thick). It covers the key field between caps and the MCU/encoder strip: ONE merged key-field opening around the 22 KLP cap footprints (17.48×16.48 + 1.0/side), windows for the MCU, the EC11 body (12.0×11.7 measured at the cover band +0.5/side, hiding the terminal base), the pwrsw body/nail, the shared USB slot and a **Ø6.0 round TRRS side hole** (zc 1.5) closed by a 0.7mm roof (straight 3.5mm plugs; the old Ø9.5 boot bore was the "gaping" opening the review rejected). The cover is **FLAT (no-indent)**: the 0.8mm ledge was removed after the second geometry review ("questionable near the encoder; don't be afraid to simplify") — the only embellishment is a **0.4mm chamfer on the outer-rim top edges**. Openings are CAP_CLEAR **1.5/side** so the 19mm-pitch caps merge across rows AND columns — one clean field, zero row-webs/enclosed scraps (the 0.52mm webs read as "ridges and dots" at 1.0). Renders wear the KLP **Normal_Tilted** caps (top ~11.1mm, **5.9mm proud of the plate**); the case geometry is cap-agnostic (Saddle foot shared). Presses the top poron pads; 8×Ø4.3×0.7 magnet pockets mirroring the tub's; no cover material within 3mm of the antenna (gated) |
| Top gaskets | Poron pads 7×4mm on each tab (PORON layer in the DXF), **1.5mm** thick (thin-top revision; compressed to 1.00 at 33% — TOP_FOAM_T/TOP_PRELOAD in `case/params.py`) |
| Plate | **1.2mm** (material below), outline = PCB outline + tabs (USB notch included). 1.2mm is the Choc v1 clip-engagement thickness (Keebio: a Choc plate must be 1.2mm for the clip to engage; at 1.5/1.6mm the "lower catch doesn't engage" and the switch is held by friction alone) |
| Plate↔PCB gap | **1.00mm** — the Choc v1 clip band. MEASURED from the Kailh Choc v1 outline drawing + a community STEP model (`spec/research-open-items-2026-10-21.md` §PG1350): above the PCB the switch is skirt 0–0.9, **flexible clip arms 0.9–1.3 (their lip grabs the plate underside)**, then the **14.8–15.0 "ears" at 2.2–3.0 that bear on the plate's top**. So the plate must sit between the lip (≤1.3) and the ears (2.2): a 1.2mm plate on a 1.00mm gap occupies **1.00–2.20** — the lip grabs the underside, the ears seat exactly on the top. A 1.05 gap lifts the ears 0.05 into the plate; a 1.3 gap drives the plate top through the ears (no grab at all). The 22 top-side diodes are the only thing under the plate in the matrix field, so the plate carries a **0.55mm relief pocket** under each one (RELIEF layer in the DXF: machine 0.55mm into the underside, do NOT cut through; `plate/gen_plate.py` `DIODE_RELIEF_D`, asserted against `DIODE_TOP_MAX_Z = 1.40`). The pocket XY is the **SOD-123 outline MAX (DS30086 rev 31-2: E 2.55–2.85 long, D 1.40–1.70 wide — `D` is width, A 1.00–1.35 is the height)**, which also covers the KiCad STEP's widest section (2.700 × 1.550 at the plate plane; the earlier 2.566 × 1.416 was the chamfered top face), + **0.15/side** → pocket **3.15 × 2.00** (measured top **1.260mm**; relief floor at 1.00 + 0.55 = **1.55mm**, **0.15mm** over the 1.40 window top and 0.65mm of plate under it) |
| PCB | 1.6mm, rev-1 release (hangs from the plate on the switches) |
| Bottom gaskets | Same 7×4 pads (3.0mm, compressed to 2.55 at 15%) under each tab (pairs at one XY); tub floor steps to −4.65 under the PCB zone (sockets + clearance) — foam sets tab height, floor depth is separate (see `case/params.py`) |
| Bottom case | BUILT — bottom tub v4.1 (`case/gen_case.py`, gates exit-0; shaped ports + recessed magnet stations; floor −4.65, slab 1.7, tub bottom −6.35 → **assembled case 11.55mm tall**, desk→cap-top 13.93); acoustic foam optional, non-structural |

- **Bottom-case floor (case design):** floor under the PCB zone sits at
  FLOOR_Z −4.65 (PCB-top frame), provisioned by the BELOW-PCB protrusions
  (M1, review-corrected 2026-10-18; wording fixed 2026-10-21 — the
  hotswap SOCKETS are SOLDERED BENEATH (their pads are on B.Cu, the
  footprint body on B.Fab/B.SilkS) and dip ~1.25 below the board
  bottom (≈ −2.85 abs), so the floor is provisioned by the deeper
  protrusions below, never by the sockets):
  encoder legs **−3.65** (measured off the vendored ROT_EC11E STEP,
  which the footprint maps 1:1 into the PCB frame — rotate 0, no z
  offset), TRRS THT pin tips **−3.0** (vendored PJ-320A STEP), Choc
  socket bump **−1.25** (Kailh datasheet), slide-switch legs ≤**−3.5**
  (WS-SLTV family bound — caliper on the first article), JST PH ~**−2.5**
  (family bound). Deepest known = −3.65 (no trimming; leads left long)
  → FLOOR_Z −4.65 keeps 1.0mm clearance, and the floor slab is
  **FLOOR_T 1.7** (tub bottom −6.35; the earlier −5.6/2.0 slab cost
  1.2mm of overall height the user wanted back). The tab-support shelf
  at SHELF_Z −1.55 is a separate feature (foam sets tab height, floor
  depth is separate — `case/params.py`).

- **Strength & materials (2026-10-24 review round; user: "strong enough
  in PETG, 100% infill okay, no exotic materials"):** measured minimum
  features on the gated solids, all >= 1.2mm except one non-spanning
  rim: tub wall 2.62, tab-pocket web 2.45, floor slab 1.70, cover web
  1.69, ledge web 1.20 (cover 2.0 − ledge 0.8, by construction — the
  ledge cutter spans past the cover top), magnet-pocket floor 1.30,
  TRRS hole roof 0.70 (plate material around a Ø6.0 hole, not a
  spanning beam). Load paths: the cover's center press deflects
  ~0.3–0.9mm for a firm 5N press (strip model) against the 1.0mm foam
  gap — the foam/plate bounds it, magnets only retain; the tub walls
  take desk/grip loads in compression or in-plane; the only through-
  layer tension is the 8 magnet-pocket floors (~0.7MPa under a 1kgf
  magnet — trivial vs PETG's ~20MPa through-layer strength). PETG at
  100% infill (E ≈ 2.1 GPa, tensile ≈ 50 MPa) is STIFFER and as strong
  as the MJF PA12 reference (E ≈ 1.65 GPa, ≈ 48 MPa) on every path;
  the PETG risks are warp/dimensional, not strength: brim the 167mm
  tub, 4+ perimeters, calibrate XY (measure the 166.9 outer width),
  print as oriented (tub open-face-up, cover underside-up). Gate:
  `tests/spec_checks.cjs` pins FLOOR_T >= 1.5 and the ledge web
  >= 1.0; `plate/gen_plate.py --check` carries the new z-stack gate.
  The plate stays shop-cut 1.2mm PC (do NOT print it in PETG: flex +
  creep defeat the Choc clip).

- **Silhouette vs sandwich cases (research round 2026-10-24; user: "the
  classics don't have beefy top cases"):** Sofle / Corne / Lily58 class
  builds use an acrylic/FR4 **sandwich** — bottom plate + PCB + a TOP
  PLATE that IS the switch plate, joined by standoffs (commonly 7mm choc
  / 10mm+ MX; Aurora Corne plates 1.5–1.6mm). There is no enclosure over
  the keycaps: the plate is the top, caps tower above it, and the
  underside is open foam. Hojicha44 keeps the same plate stack (plate at
  the Choc clip band) and adds a thin magnetic cosmetic cover over
  everything — that is the design intent (enclosed acoustic volume,
  no visible fasteners), and the 0.8mm ledge keeps the CAPS as the
  visual top. Height at the front edge: **11.55mm** (desk→cover top;
  desk→cap top 13.93 with flat Saddle caps, ~17.5 with the rendered
  Normal_Tilted) — at or below typical choc sandwich builds (~12–16mm
  at the edge) and far under MX sandwiches (~18–30mm). The classics'
  numbers vary with standoff choice and are not published per design;
  treat the ranges, not decimals.

## Sources (suppliers, verified)

- **Rogers PORON** small sheets (4701-30-15, 3.18–6.35 mm):
  McMaster-Carr (search "Rogers 4701-30"), silicone-foams.com
  resogoo.com, h-oproducts. Min order is usually a 300×300 mm sheet
  — ≫ what 16×7×4 mm pads need.
- **Drop-in keyboard strips** (4701-40 stiffer fallback, 3×90×4 mm
  self-adhesive, ≈$8–12): Keebox (AliExpress), ThockKing universal pad,
  eBay 20-packs, Amazon BTNCL/GMMK. No Rogers part number on listings,
  CFD unstated — treat as ≈41 kPa / 134 g per pad worst case, splice 2
  strips per half.
- **Adhesive**: supported grade has PET film; keep strip adhesive
  surface toward the tab. Store sheets below 40 °C / 80 % RH or the
  adhesive bonds permanently to PET release liner.
- **Shear / punch**: 7×4 pads cut cleanly with a sharp craft knife or
  a 4/8 mm punch on a mat (no hot knife — poron tears). 1:1 paper print
  = cut template.
- Spec: PORON **4701-30 Very Soft, 240 kg/m³ (15 pcf)** — the least-dense
  -30 sub-grade — 3mm thick, single-sided adhesive-backed. CFD ~24 kPa
  (~3.5 psi) @ 25% → **~68 gf per 7×4mm pad at 25% compression** (28 mm² —
  the force scales with pad area; the old 8×4 pad's 78 gf was the
  pre-audit figure, corrected 2026-10-21).
- Static load ~25 g/pad (≈200 g half-assembly / 8 bottom gaskets) →
  ≈8–10% self-compression (≈0.2–0.3 mm on 3 mm), leaving ≈2.5–3× of
  force headroom before 25% compression.
  Softest stock grade ⇒ lowest mount resonance (deepest sound, most
  high-frequency isolation) and most travel per unit force (bounciest of
  the options). Every higher rung (-40 ≈ 41 kPa / 134 g/pad; denser
  -20/-30 suffixes) moves brighter and firmer — the wrong way for thock.
- Swap ladder (all drop-in, no CAD change): **-30-15** (default, thock-max;
  cut from sheet/strip stock) → **-40 stiffer-fallback off-the-shelf strips**
  (e.g. Keebox 32-pack, ~41 kPa / ~134 g/pad, static ≈ 5%) → **-50** only
  if the build feels mushy.
- Assembly preload: design the case cavity for 15–20% foam compression —
  never near 0% (rattle, pads can't damp unloaded) and never past ~50%
  (cell densification = accidental hard mount, harsh sound). Per half:
  cavity = 1.2 + 6×(1−c), c ∈ [0.15, 0.20] → **6.0–6.3 mm** sandwich
  for a pair of 3mm pads. The thin-top revision deliberately runs the
  top foam harder: **4.75 mm** (shelf −1.55 → lip 3.20 = 2.55 bottom +
  1.2 plate + 1.00 top), i.e. 3.0mm bottom at 15% and 1.5mm top at 33%
  — inside the ≤50% ceiling, and the cover face is the rigid stop.
- Plate note: foam spec is plate-agnostic; recommended **PC 1.2 mm**
  (softest, most flex, deepest sound) or **POM 1.2 mm** (balanced,
  good feel, stable). Bounce comes from plate span between tabs; foam
  sets mount resonance and damping. (FR4/ALU/CARBON change downstream
  only via `MATERIAL` — web minimums re-gate.)
- Cut 7×4 mm pads from 90×4 mm stock (≈12 pads per 90 mm strip; 16 pads/half
  ⇒ 2 strips/half). Single-supported (PET adhesive) preferred; unsupported
  stock needs spray/transfer adhesive and holds less well.
- Pads stick to the TABs (plate), top and bottom — never to the case,
  so the assembly keeps its gaskets on disassembly. Pad centers = tab
  root centers + 2.0mm outward (`lands.json`); placement map on the PORON DXF layer.
- USB/TRRS port openings in the case walls per the notch/mouth positions
  in `spec/electronics.yaml`; antenna end keeps the 3mm plastic-only rule
  (rationale: it is a dielectric-loss/shadowing guard around the module's
  own keepout practice, not a λ/10 detune rule — at 2.4GHz λ/4 ≈ 31mm, so
  full shadowing avoidance is impossible in any closed case; the real
  validation is the BLE range bench in first-article §5)

## Port-bore contract (v3.3 breach + v3.4 shaping + v3.5 pwrsw, gate-enforced)

The rim dilation (CASE_OUTSET 8.2 today; 7.0 when this note was written v3.4) BRIDGES the USB notch (the notch floor sits
6.3–10.3mm below the local rim line depending on which shoulder you
measure against — "~5.45 deep" was a one-point figure; the skin
envelope rides ~17mm north of the rim there
— arc around the notch-mouth corners), so a fixed-DEPTH slot shipped
sealed shut in v3.2. Contract is
now structural, not numeric:

- Every port bore's OUTER FACE must actually exit the skin: `gen_case.py`
  measures the needed extent per port (marches the face outward until the
  whole face clears the skin ring, +1.0mm travel; prints
  `usb out=20.20 / trrs out=10.70 / pwrsw out=10.70` at OUTSET 8.2) —
  do not hand-pin a depth (the
  v3.1-v3.2 fixed `SLOT_OUT = 8.5` was the failure). The march is
  z-independent — breach proof and bore shape are separate decisions.
- Bore z bands are sized to the PLUGS, not to the wall (v3.2 introduced
  the full-wall z band and v3.3 kept it while fixing the depth: 14×11.6
  / 9.5×11.6 rectangles the user called "big gaping"; v3.4 shapes the
  z band):
  - USB = **14.0-wide slot with 1.2mm bottom fillets spanning z 2.0..top**
    (`SLOT_PAST_TOP` pushes the cut past the case top plane so the
    mouth's top face is the solid's own face). Plug stack: sockets
    ~4.5 → module 4.5..7.7 → receptacle mid ~6.1, i.e. the plug AXIS
    rides at the lip plane; its overmold tops ~3.2 above the lip
    (~9.2 abs) and bottoms ~2.8, so only ~2.8..lip of the plug
    crosses the wall band — the neck above the lip exits through the
    OPEN TOP and is the future cover's duty (see Stack/open-IF cover).
  - TRRS = **round Ø9.5 bore centered on the jack axis z 2.5**
    (measured off the vendored PJ-320A STEP: body 6.1 wide, top face
    flat at z 5.0). The required right-angle plug's ball boot (≤8.5)
    swings freely about that axis; ball-vs-bore margins hold for
    ±0.5mm axis drift. The bore is clipped flat by the lip only where
    it would pass above the open top — the jack itself tops at z 5.0
    below the lip. Drop-in is measured-clear with margin to spare: the
    jack's 0.99mm-RECESSED mouth face never enters the wall band at
    all (review-measured); the worst-corner bound — face corner r
    3.94 vs bore r 4.75, ~0.8mm clear — is conservative
    (case/probe_bores.py gates this against the finished solid).
  - PWR = **5.0-wide actuator slot spanning z 4.3..top with 0.8mm
    bottom fillets**, opening through the north rim plateau — the raw
    Edge.Cuts line y=58.0 across x 97.5..110.5 (mirror 181..194), so
    the slot frame is EXACT axis-aligned (no resample phase: a wobbling
    anchor x had the slot 0.87 from tab-4's pocket at x=100.59, which
    the SAT gate rejected; mouth centre 106.3/185.2 clears the pocket
    by ≥3.2 and the USB mouth by ~1.8). The WS-SLTV body (10×2.5×6.4)
    sits wholly inside the cavity — nothing internal ever crosses the
    wall; the red actuator (1.4 tall, top z 6.4) shows through the slot
    and flicks with a fingernail entering from above (~0.7 slot margin
    over the ~3.6 assumed lever sweep; blade exacts at first article).
- `check_half` re-proves it on the finished solid: mouth probes across
  the bore cross-section at two z planes (0.9 of the bore half-width;
  z planes inside each bore) must be void, air just beyond the face
  must stay air at those planes, the slab under each bore stays solid
  (no bottom holes), skin-band probing is bore-aware at z=0 (USB's
  band stays solid below its z0=2.0 bore), wall census minimum is
  printed (2.62 L / 2.70 R measured at OUTSET 8.2) with pocket-corner webs (2.45 / 2.35),
  and SAT keeps every bore ≥3mm from tab pockets (bounding-rect proof
  is conservative: fillet/circle regions are subsets of the rect).
- **Antenna window: none.** The antenna circle keeps ≥13mm of air
  (measured **14.15mm** in-plane, to the nearest case WALL on both
  halves; the nearest 3D material is the floor slab below at
  **5.60mm** — both printed per build by the new `census antenna`
  line) —
  the 3mm rule (electronics.yaml) is met with margin; plastic beyond
  3mm is not a radio problem. A window would only become required if
  the future COVER had to pass closer than 3mm over the zone, which
  the cover contract already forbids.
- Widths/axes are first-article-verified against the real plugs
  (`spec/first-article.md`): USB 14 covers the 12.35 housing, the TRRS
  bore covers the boot swing inside it, and the boot/jack z bands get
  measured at the slice dry-fit.

## Retention: recessed magnets + ring cover (v3.5, gate-enforced)

User-approved scheme: ring-cover retention with recessed magnets — no
snap lips, no heat-set inserts, nothing internal pokes through the
exterior.

- **Stations** (`gen_case.magnet_stations()`, symmetric build v3.6):
  the LEFT half is computed once per build; the RIGHT half is its exact
  mirror (`x -> 291.5 - x`, the `MIRROR_AX` axis) re-validated against
  the right boundaries/obstructions/antenna — any asymmetric rejection
  aborts the build instead of yielding unequal counts (the 2026-10-20
  six-review audit caught the old per-half walk resolving to 6/7
  stations and putting Left's retention ON the pull-test gate). A
  station centres a Ø4.3×2.2 pocket where the local band is ≥7.5mm
  (web ≥1.6 to BOTH boundaries — the reviewer floor, at OUTSET 8.2 /
  RIM_CLEAR 0.5 the straight-rim band is 7.7 so the premise holds with
  slack), ≥5.15mm from every port rect and tab pocket rect (rect-aware
  distance: a point INSIDE a rect is distance 0 — edge-distance alone
  once read a deep-inside point as "far" and placed a phantom station
  over the USB-notch void; the pocket web probes caught it), ≥10.1mm
  from the antenna centre, and ≥14mm from every other station, snapped
  at perimeter/8 spacing (8 per half — measured 8/8 exact mirrors at
  band min 7.68 / web min 1.69; the gate floor is ≥8).
- **Pockets**: vertical cylinders cut down from the band top, faces
  flush at the lip plane (z 4.70) — the magnet (2.0 thick) glues in
  face-UP. The cover glues its magnets FACE-DOWN opposite, so the
  adjacent faces meet exactly at 4.70: a rigid zero-gap stop (the 0.2mm
  glue seat in the 2.2 pocket is the only compliance). The preload
  stays geometric: uncompressed top foam 5.20 (plate top 2.20 + 3.0)
  vs the 4.70 ring underside
  = the designed 15-20% poron compression from this spec, enforced by
  the magnet stack instead of pressing force. 8 pairs of 4×2 N52 hold
  the cover far beyond the ~200g half-load.
- **Ring cover** (`case/gen_cover.py`, gates exit-0):
  prism(skin) z 4.70..7.70 minus prism(rim + RIM_CLEAR) — the inner edge
  follows the PCB RIM, not the plate outline, the outer face is the
  skin face itself (the lid seam is intentional and flush), and the
  ring bridges all 8 tab pockets so its underside presses the top
  poron pads at the designed 16.7% (review-feed: v1 cut the outline
  cavity and left tab-shaped bites — pads pressing nothing; the pad
  press gate now fails in that state; the 0..0.5mm sliver at each pad
  root stays unpressed, ~87% of the pad still loads). The key field
  stays exactly the rim line. Passages come from
  `compute_ports` VERBATIM (same anchors, widths and measured extents
  as the tub):
  - W1 USB: full-depth 14.0 slot — the plug's overmold rides through
    and pokes ~0.2 past the top face (~9.2 abs; the module itself tops
    at 7.7, below the ring).
  - W2 TRRS: the SAME Ø9.5 cylinder. In the 6..9 slice it is a BLIND
    tunnel topping at 7.25 > boot swing 6.75, and its widest chord in
    that slice (6.42 at the lip plane) never reaches the local band
    width (7.7 at OUTSET 8.2) — the ring is NOT split (the old "≤4.82" was the
    bore's chord below the lip, not the slice's).
  - PWR: full-depth 5.0 slot BUT starting 1.6 outboard, leaving a 1.1
    web next to the cavity edge: W1 must remain the ring's ONLY full
    radial severance or the cover falls into two pieces (the
    single-solid gate proves one piece; the lever reaches through, the
    nail enters from above).
  Magnet pockets cut up from the underside (faces at 4.70, 1.3mm floor
  above). Gates: bbox z window, single solid, ring census ≥5.0,
  passage voids at real band t, pwrsw inner web solid, trrs ceiling
  solid, pocket void/floor/web battery, station floor, antenna rings +
  no-plastic-over-antenna, volume tripwire [6,13] cm³, and a
  port-agnostic skin-hug battery: the ring must be solid 0.6mm inside
  every skin sample hugging (≤1.6mm from) a port rect — ring resumes
  everywhere a passage meets an outer face, with no hand-placed resume
  coordinates (the USB bite's outline is wider than the mouth frame).

## Poron pad-to-tab margin (rev-1 verified 2026-10-16; fix adopted 2026-10-20)

Pad orientation from the generator (`hl` scales the transverse vector,
`hw` the outward one): the **7 mm axis runs LATERAL** across the 10 mm
tongue, the **4 mm axis runs ALONG** the 5 mm tongue (pad spans rim-line
to +4.0 → 1 mm tip spare, no tip overhang). All pad corners test
on-plate (point-in-poly within 0.1 mm). The August-rev 8 mm pad left the
**tightest corner-edge ≈ 0.35 mm** — a laser kerf of ≈0.1–0.2 mm plus
≈0.1 mm part tolerance could nibble it. The six-review audit (2026-10-20)
adopted the rev-2 carve: **7 mm pads, corner-edge 0.71 mm measured on
both halves** — no longer kerf-fragile; strip stock still cuts 12 pads on
90 mm.
- No tip overhang — projection proof over all 8 tabs × both halves: every
  pad spans +0.0→+4.0 along the tongue against the +5.0 tip (1.0 mm spare),
  lateral half-width 4.0 against 5.0 nominal. Support is structural, not
  marginal: tongues splice outward of solid rim, tab eligibility bars any
  opening within web minimum of the tab frame, so solid material sits
  under every pad — the 0.71 mm is purely a manufacturing-tolerance
  margin, not a support question.
## Plate materials (pick one, re-run the generator to re-gate)

| Material | Fab | Notes |
|---|---|---|
| PC 1.2mm (default) | laser | softest feel, virtually unbreakable, cheapest prototype. **1.2mm is mandatory for Choc v1 clip engagement** — a thicker plate does not clip |
| POM 1.2mm | mill/laser | machines beautifully, slightly firmer than PC |
| FR4 1.6mm | route | stiff, cheap; glass dust when routing |
| ALU 1.2mm | laser/waterjet/CNC | balanced feel, best sound; isolate from copper |
| CARBON 1.2mm | mill ONLY (never laser: toxic dust + delamination) | stiffest; **conductive** — plate touches switch plastic + jackets only by construction, verify at assembly |

`MATERIAL` in the generator re-gates every web minimum
(PC/POM 1.0, FR4/ALU 1.5, CARBON 2.0); tab roots carry 2mm fillets
against crack initiation in every material.

## Plate openings (both halves)

- 22× 14×14mm Choc cutouts at switch centers/rotations (rev 2) — **body
  clearance, not a clip fit**: the PG1350 lower body passes at 13.8
  square (Kailh's plate-footprint datum; the 15.0 outline is the CLIP
  WING span).  Rev-2 (support strategy b, ADOPTED) uses a **14.0mm
  cutout in a 1.2mm plate**: 0.10mm/side on the 13.8 body (a 13.8
  hole is line-to-line and risks a switch that will not insert) while
  the 15.0 clip wing still overlaps the plate by 0.50mm/side — the
  overlap the clip arm hooks under.  The old 15.0 hole + 1.5mm plate
  had NO retention: the switch rocked, lifted out and was held by
  friction and the hotswap sockets alone.  First-article coupon
  (spec/first-article.md): cut 13.8 / 14.0 / 14.2 / 15.0 squares in
  1.2mm PC and measure insertion + retention before the plate order.
  **Tolerance stack (the clip band is only 1.3mm tall):** the capture
  window for the plate's underside is the clip-lip band z **0.9–1.3**
  (below 0.9 the plate falls out of the band = friction-only, which is
  the documented 1.5/1.6 failure; above 1.3 the lip never reaches the
  underside). In the assembled state the ears seat the plate from
  above, so the settled gap = **2.2 − plate_thickness**: for a 1.2mm
  plate that is **1.00**, between the capture limits with **0.10 of
  margin below and 0.30 above**. The ±0.1 laser slice tolerance spends
  the entire bottom margin at 1.3mm (lip tip, marginal capture), which
  is why the coupon gate rejects any plate thicker than 1.25 and the
  first article calipers the real plate. The +0.1 plate does NOT push
  the switch off the stack: the ears seat the plate 0.1 lower and the
  switch stays put (the failure mode of a too-thick plate is "no
  scan-row retention", not "the switch sits high") — verify both on
  the first article (caliper the plate and the gap, confirm every
  switch is flush with its neighbours and the clip catches).
- **16.2 × 12.4mm encoder window** (instance rot 0, body axis-aligned).
  **CHANGED IN REV 2, and it was a blocker.** The rev-1 hole was a
  12.7mm square sized off the vendored ROT_EC11E STEP for the rev-1
  plate band (z 2.0..3.5), where the encoder's body is 12.30 wide.
  The rev-2 plate band is **z 1.00..2.20** (1.00 gap + 1.20 plate),
  and measuring the SAME vendored STEP gives the encoder's
  cross-section as **14.95 wide × 11.70 deep for z 0.0..1.5** (the
  A/B/C and S1/S2 terminal blocks stand proud of the 12.30 body) and
  12.30 × 11.70 for z 1.6..2.3 (the waist). The rev-2 band therefore
  sits **inside the terminal blocks**: the 12.7 hole fouled the
  encoder by up to **1.41mm/side** and the encoder would not pass
  through the plate at all. The window is now sized to the measured
  ENVELOPE, not the waist: 16.2 × 12.4 gives **0.625/side in x (0.375
  on the tight side — the shaft is 0.25 off the envelope's centre) and
  0.35/side in y** over 14.95 × 11.70, and stays symmetric about the
  shaft so the two halves' windows remain exact mirrors (the encoder is a translated,
  NOT mirrored, part — an offset window would break the mirror gate).
  Nothing is lost: the encoder is located by its PCB pins, and the
  rev-1 hole had 0.20/side, i.e. clearance only. `gen_plate.py` asserts
  the window can never shrink below envelope + 0.2/side.
  **First article:** caliper the real encoder's terminals at
  z 1.0..1.5; if they do not protrude above ~1.5mm (the STEP may
  overstate them) the window may be reduced to 12.7 square, but the
  shipped plate must clear the model as it stands.
  Corner relief maths (audit 2026-10-20): body extreme over the
  diagonal = (12.30/2)·√2 − 0.17·(√2−1) ≈ 8.63 vs the hole's 0.5
  fillet-relief reach ≈ 8.77 → 0.145mm nominal corner clearance;
  tangency would need a 0.85 fillet or the 13.0-hole fallback, both
  rejected as needless (hand insert).
  The 13mm knob rides HIGH on the 20mm shaft — its bore never enters
  the hole. Note the knob is SQUARE: as it turns it sweeps an
  Ø18.4mm circumscribed circle about the shaft centre, so any rub
  against a case wall would come from the corners at 45°, not the
  faces — the first-article spin check is what verifies the corners
  (the knob sits above the plate and below the cover's inner edge,
  its own z window). A 17mm round hole was rejected: the encoder SHAFT center
  sits 24.04mm from the nearest switch center (SW_L17; the old "18.18"
  was the raw EC11 footprint origin, not the shaft center — the "18.2
  pitch" cited by earlier revs is the same off-center figure), so a
  17mm hole plus that neighbour's 15mm key cutout leaves next to no
  web once the rows' splay is accounted. The generator now prints the
  definitive webs each run (`gen_plate.py`): **enc↔cutouts 7.90,
  enc↔windows 3.80, enc↔port rects 4.38 (both halves — the audit-round
  mirroring removed the old L/R asymmetry)**
  — the old "~3.55" figure was approximately the window web, not the
  cutout web.
- W1 windows: slide-switch strip + MCU/cell/USB core (tall top-side parts).
- W2 window + channel to the split-gap edge: TRRS mouth must exit; the
  plug overlaps plate-top height, so no solid edge allowed there.

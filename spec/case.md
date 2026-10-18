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
| Top case | BUILT — **ring cover v1** (`case/gen_cover.py`, gates exit-0): flush bezel ring spanning z 6.0..9.0 across the wall band (outer face = the tub skin face, inner edge = PCB rim + 0.5 — BRIDGES every tab pocket and presses the top poron pads at the designed 16.7%, gated per pad); USB + pwrsw passages full-depth, TRRS as a blind tunnel (ring stays one piece), 8×Ø4.2 magnet pockets mirroring the tub's stations; no cover material within 3mm of the antenna (gated like the tub) |
| Top gaskets | Poron pads 8×4mm on each tab (PORON layer in the DXF), 3mm thick |
| Plate | 1.5mm (material below), outline = PCB outline + tabs (USB notch included) |
| Plate↔PCB gap | 2.0mm nominal (top-side diodes are 1.35mm) |
| PCB | 1.6mm, rev-1 release (hangs from the plate on the switches) |
| Bottom gaskets | Same 8×4 pads under each tab (pairs at one XY); tub floor steps to −5.6 under the PCB zone (sockets + clearance) — foam sets tab height, floor depth is separate (see `case/params.py`) |
| Bottom case | BUILT — bottom tub v3.5 (`case/gen_case.py`, gates exit-0; shaped ports + recessed magnet stations); acoustic foam optional, non-structural |

- **Bottom-case floor (case design):** floor under the PCB zone sits at
  FLOOR_Z −5.6 (PCB-top frame), provisioned by the BELOW-PCB protrusions
  (M1, review-corrected 2026-10-18: the hotswap SOCKETS are top-side —
  they never hang below the board and do not provision the floor):
  encoder legs **−3.65** (measured off the vendored ROT_EC11E STEP,
  which the footprint maps 1:1 into the PCB frame — rotate 0, no z
  offset), TRRS THT pin tips **−3.0** (vendored PJ-320A STEP), Choc
  socket bump **−1.25** (Kailh datasheet), slide-switch legs ≤**−3.5**
  (WS-SLTV family bound — caliper on the first article), JST PH ~**−2.5**
  (family bound). Deepest known = −3.65 → FLOOR_Z −5.6 keeps ~1.95mm
  clearance; the tab-support shelf at SHELF_Z −0.55 is a separate
  feature (foam sets tab height, floor depth is separate —
  `case/params.py`).

## Sources (suppliers, verified)

- **Rogers PORON** small sheets (4701-30-15, 3.18–6.35 mm):
  McMaster-Carr (search "Rogers 4701-30"), silicone-foams.com
  resogoo.com, h-oproducts. Min order is usually a 300×300 mm sheet
  — ≫ what 16×8×4 mm pads need.
- **Drop-in keyboard strips** (4701-40 stiffer fallback, 3×90×4 mm
  self-adhesive, ≈$8–12): Keebox (AliExpress), ThockKing universal pad,
  eBay 20-packs, Amazon BTNCL/GMMK. No Rogers part number on listings,
  CFD unstated — treat as ≈41 kPa / 134 g per pad worst case, splice 2
  strips per half.
- **Adhesive**: supported grade has PET film; keep strip adhesive
  surface toward the tab. Store sheets below 40 °C / 80 % RH or the
  adhesive bonds permanently to PET release liner.
- **Shear / punch**: 8×4 pads cut cleanly with a sharp craft knife or
  a 4/8 mm punch on a mat (no hot knife — poron tears). 1:1 paper print
  = cut template.
- Spec: PORON **4701-30 Very Soft, 240 kg/m³ (15 pcf)** — the least-dense
  -30 sub-grade — 3mm thick, single-sided adhesive-backed. CFD ~24 kPa
  (~3.5 psi) @ 25% → **~78 gf per 8×4mm pad at 25% compression**.
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
  cavity = 1.5 + 6×(1−c), c ∈ [0.15, 0.20] → **6.3–6.6 mm** sandwich
  (1.5 plate + 2× 3mm pads).
- Plate note: foam spec is plate-agnostic; recommended **PC 1.5 mm**
  (softest, most flex, deepest sound) or **POM 1.5 mm** (balanced,
  good feel, stable). Bounce comes from plate span between tabs; foam
  sets mount resonance and damping. (FR4/ALU/CARBON change downstream
  only via `MATERIAL` — web minimums re-gate.)
- Cut 8×4 mm pads from 90×4 mm stock (≈11 pads per 90 mm strip; 16 pads/half
  ⇒ 2 strips/half). Single-supported (PET adhesive) preferred; unsupported
  stock needs spray/transfer adhesive and holds less well.
- Pads stick to the TABs (plate), top and bottom — never to the case,
  so the assembly keeps its gaskets on disassembly. Pad centers = tab
  root centers + 2.0mm outward (`lands.json`); placement map on the PORON DXF layer.
- USB/TRRS port openings in the case walls per the notch/mouth positions
  in `spec/electronics.yaml`; antenna end keeps the 3mm plastic-only rule.

## Port-bore contract (v3.3 breach + v3.4 shaping + v3.5 pwrsw, gate-enforced)

The 7.0mm rim dilation BRIDGES the USB notch (the notch floor sits
6.3–10.3mm below the local rim line depending on which shoulder you
measure against — "~5.45 deep" was a one-point figure; the skin
envelope rides ~17mm north of the rim there
— arc around the notch-mouth corners), so a fixed-DEPTH slot shipped
sealed shut in v3.2. Contract is
now structural, not numeric:

- Every port bore's OUTER FACE must actually exit the skin: `gen_case.py`
  measures the needed extent per port (marches the face outward until the
  whole face clears the skin ring, +1.0mm travel; prints
  `usb out=19.00 / trrs out=9.50 / pwrsw out=9.50`) — do not hand-pin
  a depth (the
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
  printed (1.49-1.50 measured) with pocket-corner webs (1.15-1.55),
  and SAT keeps every bore ≥3mm from tab pockets (bounding-rect proof
  is conservative: fillet/circle regions are subsets of the rect).
- **Antenna window: none.** The antenna circle keeps ≥13mm of air
  (measured **14.15mm**) to the nearest case material on both halves —
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

- **Stations** (`gen_case.magnet_stations()`): candidates walk the
  cavity boundary outward into the wall band; a station centres a
  Ø4.2×2.2 pocket where the local band is ≥6.4mm (≥1.1 web to BOTH
  boundaries — the mid-band premise is re-checked against the true
  boundaries so oblique corners don't eat the webs), ≥5.1mm from every
  port rect and tab pocket rect (rect-aware distance: a point INSIDE a
  rect is distance 0 — edge-distance alone once read a deep-inside
  point as "far" and placed a phantom station over the USB-notch void;
  the pocket web probes caught it), ≥10.1mm from the antenna centre,
  and ≥14mm from every other station, snapped at perimeter/8 spacing
  (8 per half; the gate floor is ≥6). Both halves rotate their
  candidate ring to the USB anchor so Left/Right pick mirrored
  stations (measured mirror vs the resample phase: ≤1.3mm — 1.29mm
  exact; exact-mirrored generation deferred, documented tolerance).
- **Pockets**: vertical cylinders cut down from the band top, faces
  flush at the lip plane (z 6.0) — the magnet (2.0 thick) glues in
  face-UP. The cover glues its magnets FACE-DOWN opposite, so the
  adjacent faces meet exactly at 6.0: a rigid zero-gap stop (the 0.2mm
  glue seat in the 2.2 pocket is the only compliance). The preload
  stays geometric: uncompressed top foam 6.5 vs the 6.0 ring underside
  = the designed 15-20% poron compression from this spec, enforced by
  the magnet stack instead of pressing force. 8 pairs of 4×2 N52 hold
  the cover far beyond the ~200g half-load.
- **Ring cover** (`case/gen_cover.py`, gates exit-0):
  prism(skin) z 6.0..9.0 minus prism(rim + RIM_CLEAR) — the inner edge
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
    width (7.0) — the ring is NOT split (the old "≤4.82" was the
    bore's chord below the lip, not the slice's).
  - PWR: full-depth 5.0 slot BUT starting 1.6 outboard, leaving a 1.1
    web next to the cavity edge: W1 must remain the ring's ONLY full
    radial severance or the cover falls into two pieces (the
    single-solid gate proves one piece; the lever reaches through, the
    nail enters from above).
  Magnet pockets cut up from the underside (faces at 6.0, 0.8mm floor
  above). Gates: bbox z window, single solid, ring census ≥1.40,
  passage voids at real band t, pwrsw inner web solid, trrs ceiling
  solid, pocket void/floor/web battery, station floor, antenna rings +
  no-plastic-over-antenna, volume tripwire [6,10] cm³, and a
  port-agnostic skin-hug battery: the ring must be solid 0.6mm inside
  every skin sample hugging (≤1.6mm from) a port rect — ring resumes
  everywhere a passage meets an outer face, with no hand-placed resume
  coordinates (the USB bite's outline is wider than the mouth frame).

## Poron pad-to-tab margin (rev-1, verified 2026-10-16)

Pad orientation from the generator (`hl` scales the transverse vector,
`hw` the outward one): the **8 mm axis runs LATERAL** across the 10 mm
tongue, the **4 mm axis runs ALONG** the 5 mm tongue (pad spans rim-line
to +4.0 → 1 mm tip spare, no tip overhang). All 16 pad corners test
on-plate (point-in-poly within 0.1 mm), but the lateral squeeze is tight:
**tightest corner-edge ≈ 0.35 mm on every tab, both halves** (uniform by
construction). The 1.5 mm tip chamfers narrow the tongue exactly where
the pad's outer corners sit. A laser kerf of ≈0.1–0.2 mm on top of ≈0.1 mm
part tolerance could nibble that margin in the real world. Rev-2:
slightly narrower pad (6–7 mm wide) or a longer tab. Current geometry is
plate-safe in CAD.
- No tip overhang — projection proof over all 8 tabs × both halves: every
  pad spans +0.0→+4.0 along the tongue against the +5.0 tip (1.0 mm spare),
  lateral half-width 4.0 against 5.0 nominal. Support is structural, not
  marginal: tongues splice outward of solid rim, tab eligibility bars any
  opening within web minimum of the tab frame, so solid material sits
  under every pad — the 0.35 mm is purely a manufacturing-tolerance
  margin, not a support question.
## Plate materials (pick one, re-run the generator to re-gate)

| Material | Fab | Notes |
|---|---|---|
| PC 1.5mm (default) | laser | softest feel, virtually unbreakable, cheapest prototype |
| POM 1.5mm | mill/laser | machines beautifully, slightly firmer than PC |
| FR4 1.6mm | route | stiff, cheap; glass dust when routing |
| ALU 1.5mm | laser/waterjet/CNC | balanced feel, best sound; isolate from copper |
| CARBON 1.5mm | mill ONLY (never laser: toxic dust + delamination) | stiffest; **conductive** — plate touches switch plastic + jackets only by construction, verify at assembly |

`MATERIAL` in the generator re-gates every web minimum
(PC/POM 1.0, FR4/ALU 1.5, CARBON 2.0); tab roots carry 2mm fillets
against crack initiation in every material.

## Plate openings (both halves)

- 22× 15×15mm Choc cutouts at switch centers/rotations — **body
  clearance, not a clip fit**: the PG1350 lower body passes at 13.8
  square (common plate-footprint datum; the 15.0 outline includes the
  clip wings), so 15.0 gives ~0.6/side and the side clips never touch.
  With the 1.5mm PC plate this is coherent anyway — Choc clips need a
  ~1.3mm plate gap to click (1.2mm-class plates), so retention here is
  friction + the hotsockets. Rev-2 option (laser coupon A/B at §1 of
  first-article decides): ~14.0 cutout + 1.2mm plate.
- 12.7×12.7mm square encoder hole (instance rot 0, body axis-aligned).
  Sized off the vendored ROT_EC11E STEP: the body measures **12.30 wide
  in the plate band (z 2.0..3.5)** (12.00 up to z 4.0), so 12.7 gives
  0.20/side nominal (the old 12.5 was spec'd 0.4/side off the "11mm
  class" — the real part is wider; bench-verify with the real encoder
  before the plate order).
  The 13mm knob rides HIGH on the 20mm shaft — its bore never enters
  the hole. A 17mm round hole was rejected: the encoder SHAFT center
  sits 24.04mm from the nearest switch center (SW_L17; the old "18.18"
  was the raw EC11 footprint origin, not the shaft center — the "18.2
  pitch" cited by earlier revs is the same off-center figure), so a
  17mm hole plus that neighbour's 15mm key cutout leaves next to no
  web once the rows' splay is accounted. The generator now prints the
  definitive webs each run (`gen_plate.py`): **enc↔cutouts 9.15,
  enc↔windows 3.65, enc↔port rects 4.92..5.35** (Left; Right symmetric)
  — the old "~3.55" figure was approximately the window web, not the
  cutout web.
- W1 windows: slide-switch strip + MCU/cell/USB core (tall top-side parts).
- W2 window + channel to the split-gap edge: TRRS mouth must exit; the
  plug overlaps plate-top height, so no solid edge allowed there.

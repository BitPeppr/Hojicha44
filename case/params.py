"""Hojicha44 case parameters (design constants; sources annotated in-line).

Frame: KiCad board frame, mm. z = 0 is the PCB TOP surface.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- stack (spec/case.md "Stack", all per half) ----
# SUPPORT STRATEGY (b), rev-2: the plate now carries the Choc v1 clip
# engagement (14.0mm cutout, 1.2mm plate) and sits at the Choc gap of
# 1.00mm above the PCB top, so the whole top of the case comes DOWN
# 1.30mm (plate top 3.50 -> 2.20).  The diodes stay on the PCB's top
# side and the plate relieves 0.55mm over them (measured SOD-123 top
# = 1.26mm, part tolerance up to 1.40; see plate/gen_plate.py).
PLATE_UNDER = 1.00  # PCB top -> plate underside (Choc v1 clip band:
                    # the plate must sit between the clip lip <=1.3 and the
                    # 14.8 ears at 2.2 -> 1.0 gap + 1.2 plate = 1.0..2.2)
PLATE_T = 1.2       # plate thickness (Choc v1 clip engagement)
FOAM_T = 3.0        # poron pads under each tab (bottom gaskets)
TOP_FOAM_T = 1.5    # poron pads above each tab (top gaskets).  Thin
                    # STOCK on purpose: the top gap is now 1.28mm at
                    # the same 15% preload, so the top case sits just
                    # above the plate instead of 2.5mm above it.  The
                    # user review called the old 2.5mm foil stack
                    # "massive spaces above the gaskets".
PRELOAD = 0.15      # bottom-gasket assembly compression (spec: 0.15-0.20)
TOP_PRELOAD = 0.333 # top-gasket compression: the review wanted the caps
                    # to stand proud, so the 1.5mm top foam runs at 1/3
                    # compression (inside the spec's <=50% ceiling) and
                    # the whole top case sits at 2.20+1.00
TAB_W = 10.0        # tab width (plate/gen_plate.py)
TAB_L = 5.0         # tab protrusion past outline

PLATE_TOP = PLATE_UNDER + PLATE_T          # +2.20 (was 3.50)
# Tab-support shelf: bottom foam compressed under the tab.
# SHELF_Z = PLATE_UNDER - FOAM_T*(1-PRELOAD) = 1.00 - 2.55 = -1.55
SHELF_Z = PLATE_UNDER - FOAM_T * (1 - PRELOAD)   # = -1.55
# Top gap = compressed top foam between plate top and lip underside:
TOP_GAP = TOP_FOAM_T * (1 - TOP_PRELOAD)         # = 1.00
# Floor under the PCB zone: provisioned by the BELOW-PCB protrusions
# (M1, review-corrected; wording fixed 2026-10-21 — the hotswap SOCKETS
# are SOLDERED BENEATH (B.Cu pads, body on B.Fab/B.SilkS) and dip ~1.25
# below the board bottom, i.e. ~-2.85 abs, so they stay well clear of
# the -5.6 floor; the module itself is 4.5..7.7 above the board).
# Measured ruler: encoder
# legs -3.65 (vendored ROT_EC11E STEP; footprint maps it 1:1 into the
# PCB frame — rotate 0, no z offset), TRRS THT pin tips -3.0 (vendored
# PJ-320A STEP), Choc socket bump -1.25 (Kailh datasheet), slide-switch
# legs <=-3.5 (WS-SLTV family bound; caliper on first article), JST PH
# ~-2.5 (family bound). Deepest known -3.65 -> -5.6 keeps ~1.95mm
# clearance. A flat floor at sandwich depth still collides (the PCB
# bottom is -1.6); the tub MUST step down here (spec/case.md).
FLOOR_Z = -5.6  # floor top surface (spec-derived, see ruler above;
# first-article caliper re-measures the family bounds)

# ---- outer skin (v3: uniform dilation, Sofle/Corne/Lily lesson) ----
# ONE constant offset of the PCB RIM (gen_case.py). Notches shallower
# than the offset (USB ~5.45 deep, TRRS channel) fill in and vanish
# from the silhouette — breaching them is the port slots' job.
# STRENGTH HISTORY: at 6.0 the wall over every tab tip measured 0.5
# (skin rim+6.0 vs cavity tab tip rim+5.5) — 1-2 FDM extrusion lines
# over an 11mm span at each of 8 stations; the whole case thickened
# (user-sanctioned) to close the pockets without creating local
# swells (v2 sin, rejected).
CASE_OUTSET = 8.2   # wall over tab tip = 8.2 - TAB_L - RIM_CLEAR = 2.7
                    # (6-review audit 2026-10-20: 7.1 gave 1.595 measured
                    # wall — under both the 1.6 design floor and the MJF
                    # 2.0 pass; 8.2 clears them with margin and grows the
                    # band to 7.7 so MAG_STATION_BAND 7.5 fits with 0.2
                    # slack and magnet webs reach 1.6)
SKIN_MIN = 1.0      # min material between any pocket corner and the skin
SKIN_STEP = 1.0     # ring resample step for the outer skin (folds gone;
                    # verified crossing-free at 1.0/0.6/0.4)
MIRROR_AX = 145.75  # shared left/right mirror axis: RIGHT = 2 * MIRROR_AX
                    # - LEFT in frame coordinates (291.5 - x). Every
                    # per-half constant below is asserted or derived with
                    # this (6-review audit 2026-10-20: asymmetric
                    # derivations produced 6/7 magnet stations and +0.5mm
                    # plate keep-zone drift; symmetric sources replaced
                    # them).
TOP_LIP_Z = 3.20    # lip at plate top + TOP_GAP (2.20 + 1.00):
                    # the 1.5mm top foam runs at 33% compression and the
                    # top case sits right above the plate, so the caps
                    # stand 2.4mm proud of the 2.0mm top plate instead of
                    # barely 1.6mm. The tie TOP_LIP_Z == PLATE_UNDER +
                    # PLATE_T + TOP_GAP is enforced by
                    # tests/spec_checks.cjs (stack-ties).
#   NOTE: the USB-C module stack tops ~7.7 above the PCB, the EC11 body
#   tops ~5.2 and its shaft ~24.5 — the COVER carries windows for both
#   (gen_cover.py).

# ---- fastening (REVISED: no visible fasteners on the exterior) ----
# Rev-1 tub: friction fit (plate + poron preload holds the assembly).
# Future top cover: recessed magnets or internal clips — decided at
# cover-design time, NOT screws/bosses through the skin.
#   OPEN (cover): cover MUST carry the W1/W2 windows + USB notch + TRRS
#   channel openings (they exist in the plate outline today; do not lose
#   them in the cover) AND the plug passages above the slots — the USB
#   overmold tops ~3.2 and the socketed module ~7.7, both above the lip;
#   and it must keep ANT_R_MM + ANT_CASE_CLEAR clearance over the
#   antenna zones in case/params.py below.

# ---- tab pockets (lands.json roots; jackets swallow tab + both foams) ----
POCKET_CLEAR = 0.5        # side clearance in the pocket
POCKET_IN = 1.0           # pocket starts 1mm inside the rim line
POCKET_OUT = TAB_L + 0.5  # pocket nose past the tab tip
POCKET_BOT = SHELF_Z       # pocket floor IS the shelf (foam rests on it)
POCKET_TOP = TOP_LIP_Z     # open to the top (cover presses upper foam)

# ---- port mouths (v3.4: shaped bores, NOT full-height wall slots) ----
# The rim's USB notch (11 wide) fills in under CASE_OUTSET dilation, so
# ports still breach via explicit bores anchored on the RIM, SLOT_IN
# into the cavity through the skin and past it, and the outer extent
# stays MEASURED (gen_case.py marches the bore face outward until it
# clears the skin ring across the whole width + margin). v3.3 closed
# the same contract with full-wall 14x11.6 / 9.5x11.6 rectangles the
# user rightly called "gaping"; v3.4 shapes each mouth to the plug:
#   USB  = 14.0-wide port with 1.2 fillets UNDER it only (flat top,
#          z band 2.0..lip). Plug stack math: sockets ~4.5 (measured —
#          the old ~3.0 figure was wrong) -> module 4.5..7.7 ->
#          receptacle mid ~6.1 = the plug AXIS rides AT the lip plane;
#          overmold tops ~3.2 ABOVE
#          the lip (~9.2 abs), bottom ~2.8, so only 2.8..lip of the
#          plug crosses the wall band — its neck above the lip rides
#          through the open top plane, which the future COVER carries.
#   TRRS = round bore (9.5 dia) centered on the jack axis:
#          PJ-320A measured off the vendored model
#          (pcb/kicad/Hojicha44.3dshapes/PJ-320A.step): body 6.1 wide,
#          top face flat at z 5.0, plastic mouth face RECESSED 0.99mm
#          behind the board edge (review: nothing of the jack then
#          crosses the wall band on the straight drop-in — the worst
#          corner analysis stands as a conservative bound: r=3.94
#          (face corner (3.05, 5.0) about axis 2.5)
#          vs bore 4.75 -> ~0.8mm clear). The right-angle plug's ball
#          boot (<=8.5) swings about that axis and stays inside for
#          +/-0.5 axis drift. The bore is clipped flat by the lip only
#          where it would pass above the open top (jack top 5.0 < lip
#          6.0: the clip region is empty above the jack in service).
USB_MOUTH_W = 14.0     # notch is 11; +3 for housing shoulders
USB_MOUTH_Z0 = 2.0     # overmold bottom ~2.8 (axis ~6.1, h ~6.5) + margin
USB_MOUTH_R = 1.2      # bottom-corner fillet (flat top, see above)
TRRS_MOUTH_R = 2.6     # Ø5.2 SIDE HOLE, not the old Ø9.5 boot bore.
#   Review: the Ø9.5 bore + thin cover cut a rectangular window open to
#   the top ("gaping"); a 3.5mm plug's METAL barrel is ~Ø3.5-4.0 and the
#   grip stays outside the 7.6mm wall, so a round Ø5.0 hole passes it.
#   Its top (zc+r = 4.5) stays 0.7mm under the 5.2 cover top, so the
#   cover keeps a closed roof over the port. Right-angle plug boots no
#   longer swing inside; the first article measures the real plug.
TRRS_MOUTH_ZC = 1.9    # hole centre: jack axis 2.5 dropped to 1.9 so the
#   Ø5.2 top (4.5) clears under the 5.2 cover top with a 0.7mm roof. The
#   hole still passes a straight Ø3.5-4.0 barrel (spans 0.75..4.25 at
#   the jack axis) with margin.

# ---- power-switch actuator window (v3.5, north rim) ----
# WS-SLTV (450301014042, Wuerth datasheet + KiCad footprint name
# 10x2.5x6.4): body 10 x 2.5, body top z 5.0 above the PCB, red
# actuator 1.4 tall on top (z 5.0..6.4), slide travel 0.8/side along
# the 10mm axis, flick = fingernail entering the aperture from above.
# Placement: footprint at (106.3,51) Left / (185.2,51) Right (M3:
# origin centred on this window; the M2 "2mm WEST" shift ran the wrong
# way and left the blade band wholly behind the wall); the north rim
# runs a STRAIGHT plateau y=58 across x 97.5..110.5 (frozen in the
# ergogen outline — does not follow the switch), so the whole switch
# (its most outboard point y=52.25) sits >=6.25mm INSIDE the cavity — no bodyor
# pin ever crosses the wall band. The mouth is therefore only the
# actuator aperture, and it must NOT span the 7.0 wall band fully: a
# full-width cut breaks the ring into two disconnected arcs (2 solids).
PWRSW_MOUTH_W = 5.0    # lever (~3 swept with throw) + nail entry; ALSO
#   the ring-safety cap: (7.0 band - w)/2 >= 1.0 web.
PWRSW_MOUTH_Z0 = 4.3   # 0.7 below the body top for nail entry angle.
#   With the thin-cover lip at 3.48 this is ABOVE the tub, so the tub
#   has no pwrsw bore at all (compute_ports marks it skipped); the
#   COVER carries the body window + nail slot (PWRSW_WIN/PWRSW_NAIL_W).
PWRSW_COVER_IN = 1.6   # cover slot starts this far outboard of the port
                       # anchor, leaving the 1.1mm inner web next to the
                       # cavity edge (W1 must stay the ring's ONLY full
                       # radial severance — single-solid gate)
PWRSW_MOUTH_R = 0.8    # bottom fillets (molded look, matches USB)

# ---- plug envelopes the census prints against (gen_case.py table) ----
# Same sources as the port comments above: USB housing from the plug
# stack math, boot/face from the vendored PJ-320A STEP, lever from the
# Wuerth WS-SLTV datasheet (blade ~2.0 + travel 1.6; verify first art.)
USB_HOUSING_W = 12.35       # overmold body widest around the axis
TRRS_PLUG_DIA = 4.0         # straight plug metal barrel, <= Ø4.0 (the
#   grip/overmold stays outside the wall, so it never needs a bore)
TRRS_FACE_HW = 3.05         # PJ-320A mouth face half-width (STEP)
TRRS_FACE_TOP = 5.0         # PJ-320A mouth face top plane (STEP)
PWRSW_LEVER_SWEEP = 3.6     # actuator blade ~2.0 + travel 1.6 (verify)

# ---- retention magnets (v3.5 tub + ring cover, recessed both sides) ----
# Zero-gap stack: tub magnet faces flush at TOP_LIP_Z, ring magnet faces
# flush at the cover underside — adjacent faces MEET at the lip plane, a
# rigid stop, so the ring bottom cannot pass the lip plane and the
# poron top-pad preload stays purely geometric (uncompressed 6.5 vs ring
# bottom 6.0 = the designed 16.7%); the ~3-4 kg magnet pull is reacted
# by the band-face contact, NOT by crushing the foam. 4x2 N52 pairs:
# ~0.4-0.6 kg/pair x 8 >= 3 kg vs a ~200 g half; nothing pokes outside.
MAG_DIA = 4.3          # pocket bore for a Ø4.0 magnet: 0.15/side glue film
                       # (post-audit P1 full adoption; Ø4.2 was starved after
                       # FDM shrink — see spec/case.md retention)
MAG_DEPTH = 2.2        # TUB pocket depth (2.0 magnet + glue line)
COVER_MAG_DEPTH = 0.7  # COVER pocket depth (thin-cover round): cover-
#   side magnets are Ø4x0.5 -> pocket floor 2.0-0.7 = 1.3mm, the same
#   floor the T4 review demanded, on a 2.0mm cover. Faces still meet
#   exactly at the lip plane; Ø4x2 (tub) vs Ø4x0.5 (cover) is
#   asymmetric-tolerant (force drops, 8 pairs must still cover the
#   ~200 g half; the rigid zero-gap stop is the face plane, not the
#   pull; first-article pull test re-gates the thinner cover magnet).
MAG_STATION_BAND = 7.5 # local band needed: pocket + >=1.6 web both faces
                       # (6-review audit 2026-10-20: the web >= 1.6 reviewer
                       # floor is NOW met in-band — webs (7.5-4.3)/2 = 1.6,
                       # straight-rim band is 7.7 = OUTSET 8.2 - RIM 0.5)
MAG_WEB_MIN = 1.6      # ABSOLUTE magnet-pocket web floor (reviewer floor).
                       # The derived gate ((MAG_STATION_BAND - MAG_DIA)/2)
                       # shrinks with the band it polices, so it can never
                       # catch a thinner pocket — this constant can
                       # (3-review audit 2026-10-21: all three reviewers
                       # found the derived floor unenforceable).
WALL_MIN_ABS = 2.0     # ABSOLUTE tub wall floor (the MJF 2.0 print pass).
                       # The derived gate (OUTSET - TAB_L - RIM_CLEAR - 0.3)
                       # moves with OUTSET and therefore cannot detect an
                       # absolute thinning (same audit).
MAG_MIN_SEP = 14.0     # arc separation between stations
MAG_MAX_STATIONS = 8
MAG_MIN_STATIONS = 8   # retention gate on station count (audit: the doc
                       # chain promises 8/half — BOM 16+16, first-article
                       # pull math; the old per-half generation yielded
                       # 6/7 and Left sat ON the 1.5 kg pull gate)

# ---- port anchors (slot frame anchors, KiCad frame) ----
# SOURCE OF TRUTH for both the case bores and the plate's port
# keep-rects (plate/gen_plate.py asserts every anchor sits inside
# its keep-rect — the two files cannot drift apart silently).
# usb   = points.yaml helper usb / mirror_usb (mcu + [0,17.95])
# trrs  = jack MOUTH centres derived from the layout trrs anchor
#         (130.5/-22) via the PCB placement chain: anchor ± 8.05
#         (gen_pcb.py TRRS rot-90 dX) + footprint mouth y 12.1
#         -> 134.55 (L) / 156.95 (R), rounded.
# pwrsw = the ACTUATOR MOUTH centre on the north rim plateau, NOT the
#         switch footprint (SW_LPWR1/SW_RPWR1 sit at 106.3/185.2, 51 after
#         M3 — origins centred on this fixed window, band = origin +/-1.8
#         vs the 5.0-wide mouth = 0.70/side; M2's "2mm WEST" shift had run
#         the WRONG way and left the band wholly behind the west/east
#         wall). The mouth itself cannot move: SAT-constrained,
#         pocket >=3.2 / USB ~1.8 margins. The plateau is the raw
#         Edge.Cuts line y=58.0 across x 97.5..110.5 (mirror 181..194,
#         frozen in the ergogen outline), so the frame is axis-aligned
#         EXACT (no resample-phase wobble): a wobbly +/-.5 anchor x
#         swings the slot into tab-4's pocket (east edge x=100.59; SAT
#         floor 3 wants west edge >= 103.6) or onto the notch shoulder
#         (110.5). The mouth centre 106.3 clears both; blade/throw stays
#         exposed (body spans x 101.3..111.3 / 180.2..190.2).
# Slots are explicit rects whose outer extent is measured to actually
# breach the skin.
# The trrs pair is mirror-exact to 0.01 (the 2026-10-21 audit found the
# 1-decimal rounding had broken the mirror by 0.1mm: 134.6 <-> 156.9,
# not 157.0 — the derived pair is 134.55 / 156.95).
PORTS = {"Left": {"usb": (118.0, 49.95), "trrs": (134.55, -22.0),
                  "pwrsw": (106.3, 58.0)},
         "Right": {"usb": (173.5, 49.95), "trrs": (156.95, -22.0),
                   "pwrsw": (185.2, 58.0)}}

# ---- ring cover (v3.5: flush bezel ring on the lip) ----
# Underside = TOP_LIP_Z (presses the top poron), top = +COVER_T (stays
# below the keycap field ~9.5-10.5). Openings: W1 = USB plug
# neck/housing band to its top ~9.2 (full-depth pass), W2 = TRRS boot
# swing past the lip (top ~6.75: the Ø9.5 cylinder cut reaches 7.25 and
# its chord in the 6..9 slice stays <=6.42 at the lip plane so the ring is
# NOT split),
# the pwrsw flick slot, and the magnet pockets. Outer face = the skin
# face FLUSH (an intentional lid seam).
COVER_T = 2.0          # 3.20..5.20 (TOP_LIP_Z + 2.0): a thin top
                    # plate that also covers the MCU/encoder strip and
                    # the key field between caps (key-field opening +
                    # component windows), instead of a bare rim ring.
                    # 1.3 floor over the 0.7 magnet pockets
# ---- top-cover openings (thin top plate, gen_cover.py) ----
# The cover is no longer a bare rim ring: it also spans the key field,
# so it hides the plate/switch bodies between caps and covers the
# MCU/encoder wiring strip. Openings are fixed here so the render and
# the CAD read the same numbers:
#   key field = union of the 22 cap footprints (KLP Lamé Saddle/Thumb
#               are all 17.48x16.48 in plan) dilated CAP_CLEAR/side —
#               1.0 makes the 19mm-pitch caps merge into ONE opening
#   MCU       = module courtyard + margin; the south edge is pulled to
#               y=12.0 so the cover is >=3mm (in 3D) from the antenna
#               centre at (118, 15.55) (ANT_CASE_CLEAR)
#   encoder   = EC11 body 16.2x12.4 + 0.2/side
#   USB/TRRS  = the SAME compute_ports passages as the tub (shared
#               anchors; TRRS is now an edge notch because the lip is
#               below the bore top)
#   pwrsw     = body window + nail slot to the north skin
CAP_FOOT_W = 17.48     # KLP Saddle / Thumb plan footprint (measured)
CAP_FOOT_H = 16.48
CAP_CLEAR = 1.0        # key-field opening clearance per side. gen_cover
                       # fills the union's enclosed holes, so the
                       # staggered caps become ONE opening with no cover
                       # islands while the inner web to the MCU window
                       # stays ~1.5mm.
CAP_ROUND = 2.0        # cutter corner radius (molded look)
MCU_WIN = (106.5, 12.0, 129.0, 48.6)      # x0, y0, x1, y1
ENC_WIN = (111.5, -14.35, 124.5, -1.65)   # x0, y0, x1, y1: EC11
                       # BODY at the cover band (measured 12.0x11.7 at
                       # z 3.2..5.2, centred (118,-8)) + 0.5/side. The
                       # old 17.2x13.2 window exposed the whole part;
                       # this one covers the rectangular terminal base
                       # and leaves only the body top + bushing/shaft.
PWRSW_WIN = (101.0, 56.4, 111.6, 70.0)    # x0, y0, x1, y1: body window
                       # extended through the north skin in ONE clean
                       # notch (a 5mm nail slot beside the USB slot left
                       # an enclosed 3x7mm cover island between them).

SLOT_PAST_TOP = 0.5    # bore cut extends past the case top plane so the
#   mouth's top face is the solid's own face, not a coincident-face seam
SLOT_IN = 2.0          # bore starts inside the cavity (anchored in material)
SLOT_OUT = CASE_OUTSET + 1.5   # scan start / minimum outer extent
SLOT_BREACH_MARGIN = 1.0   # extra travel past the skin along the face

# ---- antenna keepout (spec/electronics.yaml antenna_keepout block) ----
# NB: the keepout circle drawn on each board's Cmts.User has radius 5.0
# (pcb gen_pcb.py ANT_R_MM) at the antenna centre; this file must match.
# CONSUMED by the case gate (envelope rings + wall-distance floor).
# Antenna centres = layout helper points antenna/mirror_antenna
# (mcu + [0, -16.45]) in layout/generated/v2/points/points.yaml.
ANT_R_MM = 5.0
ANT_CASE_CLEAR = 3.0   # "no case material within 3mm" (electronics.yaml)
ANTENNA_L = (118.0, 15.55)
ANTENNA_R = (173.5, 15.55)

# ---- internals carried over ----
RIM_CLEAR = 0.5   # plate-to-wall clearance (spec/case.md stack table)

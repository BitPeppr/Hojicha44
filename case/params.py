"""Hojicha44 case parameters (design constants; sources annotated in-line).

Frame: KiCad board frame, mm. z = 0 is the PCB TOP surface.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- stack (spec/case.md "Stack", all per half) ----
PLATE_UNDER = 2.0   # PCB top -> plate underside (diodes are 1.35)
PLATE_T = 1.5       # plate thickness
FOAM_T = 3.0        # poron pads, top + bottom of each tab
PRELOAD = 0.15      # design assembly compression (spec: 0.15-0.20)
TAB_W = 10.0        # tab width (plate/gen_plate.py)
TAB_L = 5.0         # tab protrusion past outline

PLATE_TOP = PLATE_UNDER + PLATE_T          # +3.5
# Tab-support shelf: bottom foam compressed under the tab.
# SHELF_Z = PLATE_UNDER - FOAM_T*(1-PRELOAD) = 2.0 - 2.55 = -0.55
SHELF_Z = PLATE_UNDER - FOAM_T * (1 - PRELOAD)   # = -0.55
# Floor under the PCB zone: provisioned by the BELOW-PCB protrusions
# (M1, review-corrected: the hotswap SOCKETS are top-side — module
# 4.5..7.7 — and never hang below the board). Measured ruler: encoder
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
TOP_LIP_Z = 6.0     # lip at plate top +2.5: leaves a 2.5mm gap = 16.7%
#   preload on the 3.0 top foam ((3.0 - 2.5) / 3.0), matching the ~15%
#   bottom preload (2.55 of 3.0); receives the future top cover / upper
#   foam. NOTE: the USB-C module stack tops ~7.7 above the PCB — the
#   COVER must carry that opening (open decisions below).

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
TRRS_MOUTH_R = 4.75    # Ø9.5: boot ball <=8.5 + 0.5/side swing clearance
TRRS_MOUTH_ZC = 2.5    # jack axis: mouth-face centre vertex z=2.5 in the
#   vendored STEP; ±0.5 drift stays covered. Verify on the first article.

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
PWRSW_MOUTH_Z0 = 4.3   # 0.7 below the body top for nail entry angle
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
TRRS_BOOT_DIA = 8.5         # right-angle plug's ball boot, <= Ø8.5
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
COVER_MAG_DEPTH = 1.7  # COVER pocket depth (T4, review M4): cover-side
#   magnets are Ø4x1.5 -> pocket floor 3.0-1.7 = 1.3mm (was 0.8 over a
#   2.2 pocket = 2 FDM passes). Faces still meet exactly at the lip
#   plane; Ø4x2 vs Ø4x1.5 is an asymmetric-tolerant pair (force drops
#   to ~0.7-0.85x/face, 8 pairs still >= 2 kg vs a ~200 g half — the
#   rigid zero-gap stop is the face plane, not the pull; first-article
#   pull test gates the change).
MAG_STATION_BAND = 7.5 # local band needed: pocket + >=1.6 web both faces
                       # (6-review audit 2026-10-20: the web >= 1.6 reviewer
                       # floor is NOW met in-band — webs (7.5-4.3)/2 = 1.6,
                       # straight-rim band is 7.7 = OUTSET 8.2 - RIM 0.5)
MAG_MIN_SEP = 14.0     # arc separation between stations
MAG_MAX_STATIONS = 8
MAG_MIN_STATIONS = 8   # retention gate on station count (audit: the doc
                       # chain promises 8/half — BOM 16+16, first-article
                       # pull math; the old per-half generation yielded
                       # 6/7 and Left sat ON the 1.5 kg pull gate)

# ---- ring cover (v3.5: flush bezel ring on the lip) ----
# Underside = TOP_LIP_Z (presses the top poron), top = +COVER_T (stays
# below the keycap field ~9.5-10.5). Openings: W1 = USB plug
# neck/housing band to its top ~9.2 (full-depth pass), W2 = TRRS boot
# swing past the lip (top ~6.75: the Ø9.5 cylinder cut reaches 7.25 and
# its chord in the 6..9 slice stays <=4.82 so the ring is NOT split),
# the pwrsw flick slot, and the magnet pockets. Outer face = the skin
# face FLUSH (an intentional lid seam).
COVER_T = 3.0          # 6.0..9.0; 1.3 floor over the 1.7 magnet pockets
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

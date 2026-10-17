"""Hojicha44 case parameters — every number cites its spec source.

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
SHELF_Z = PLATE_UNDER - FOAM_T * (1 - PRELOAD)   # 2.0 - 2.55 = -0.55
# Floor under the PCB zone: PCB bottom (-1.6) + sockets (~3.0) + 1.0 clear.
# A flat floor at sandwich depth collides — the tub MUST step down here
# (spec/case.md audit trail). -5.6 abs = -7.6 rel. plate underside.
FLOOR_Z = -5.6  # floor top surface (spec-derived: -1.6 PCB, ~3.0 sockets,
# 1.0 clearance; first-article measures pin/socket protrusion)

# ---- outer skin (v3: uniform dilation, Sofle/Corne/Lily lesson) ----
# ONE constant offset of the plate outline. Straight rims need
# 5.5 (pocket nose) + SKIN_MIN = 5.9; curved/valley rims measure >= 4.2
# (valley dilation bridges far out). Notches shallower than the offset
# (USB 5.4, TRRS channel) fill in and vanish from the silhouette.
# Chunky = milled-case look, intended. (6.5 was tried on a false alarm:
# the containment gate tested 10.5mm phantom corners from the v0 span
# bug — fixed 2026-10-17, outset restored to the true requirement.)
CASE_OUTSET = 6.0   # constant plate-outline -> exterior offset
SKIN_MIN = 0.4      # min material between any pocket corner and the skin
SKIN_STEP = 1.0     # ring resample step for the outer skin (folds gone;
#                   verified crossing-free at 1.0/0.6/0.4)
TOP_LIP_Z = 6.0     # rim top: symmetric 16.7% top preload ((6.0-3.5)/3.0),
#   matching the 15% bottom; receives the future top cover / upper foam.

# ---- fastening (REVISED: no visible fasteners on the exterior) ----
# Rev-1 tub: friction fit (plate + poron preload holds the assembly).
# Future top cover: recessed magnets or internal clips — decided at
# cover-design time, NOT screws/bosses through the skin.
#   OPEN (cover): cover MUST carry the W1/W2 windows + USB notch + TRRS
#   channel openings (they exist in the plate outline today; do not lose
#   them in the cover) and close the lip at TOP_LIP_Z.

# ---- tab pockets (lands.json roots; jackets swallow tab + both foams) ----
POCKET_CLEAR = 0.5        # side clearance in the pocket
POCKET_IN = 1.0           # pocket starts 1mm inside the rim line
POCKET_OUT = TAB_L + 0.5  # pocket nose past the tab tip
POCKET_BOT = SHELF_Z       # pocket floor IS the shelf (foam rests on it)
POCKET_TOP = TOP_LIP_Z     # open to the top (cover presses upper foam)

# ---- port slots (explicit full-height wall openings) ----
# The rim's USB notch (11 wide) fills in under CASE_OUTSET dilation, and
# real plug housings are wider anyway, so ports breach via explicit
# slots anchored on the RIM, spanning the whole wall band: SLOT_IN into
# the cavity through SLOT_OUT past the skin. Verify with the actual
# plug on the first article (dry-fit gates in first-article.md).
USB_SLOT_W = 14.0    # notch is 11; +3 for housing shoulders
TRRS_SLOT_W = 12.0   # jack mouth; 90-degree plug boot needs ~12
SLOT_IN = 2.0        # slot starts inside the cavity (breach proof)
SLOT_OUT = CASE_OUTSET + 1.5   # slot ends past the skin (breach proof)

# ---- internals carried over ----
RIM_CLEAR = 0.5   # plate-to-wall clearance (spec/case.md stack table)

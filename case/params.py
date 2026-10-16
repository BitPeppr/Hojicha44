"""Hojicha44 case parameters — every number cites its spec source.

Frame: KiCad board frame, mm. z = 0 is the PCB TOP surface.
"""
import math
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- stack (spec/case.md "Stack", all per half) ----
PLATE_UNDER = 2.0   # PCB top -> plate underside (diodes are 1.35)
PLATE_T = 1.5       # plate thickness
FOAM_T = 3.0        # poron pads, top + bottom of each tab
PRELOAD = 0.15      # design assembly compression (spec: 0.15-0.20)
PORON_PAD_L = 8.0   # lateral (plate/gen_plate.py: pad frame)
PORON_PAD_W = 4.0   # along tongue
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

# ---- rim (spec/case.md: cavity = plate outline + tabs, + clearance) ----
RIM_CLEAR = 0.5   # plate-to-wall clearance (spec/case.md stack table)
WALL_T = 2.0      # rim wall thickness, FDM default (undecided fab, default FDM)
WALL_FLARE = 1.0  # extra outward offset at the floor: walls step outward
#   going down (+3.5/+3.0/+2.5 stacked-layer look, not a blunt box).
#   (True loft/draft was tried: OCP profile pairing + tapered extrude both
#   choke on this outline — steps are the honest version.)
TOP_LIP_Z = 6.0   # rim top: symmetric 16.7% top preload ((6.0-3.5)/3.0),
#   matching the 15% bottom; receives the future top cover / upper foam.

# ---- fastening (decided: secure, NO heat-set inserts, NO metal) ----
# M3 nylon screws + captive hex nuts in printed pockets (bottom-loaded).
# Nylon keeps metal away from the antenna end entirely; nuts are trapped,
# serviceable, and need no heat. Bosses bulge outward from the rim band
# (never into the cavity); a future top cover bolts down into the same nuts.
FAST_R = 4.5          # boss radius
FAST_C = 5.5          # boss center offset outside the plate outline
NUT_AF = 5.7          # hex pocket across-flats for M3 nut (5.5 + 0.2)
NUT_DEPTH = 3.0       # blind pocket depth from below (nut loads from bottom)
NUT_FLARE_R = 0.5     # mouth flare extra circumradius (elephant-foot + insertion)
NUT_FLARE_H = 0.5     # flare height from the case bottom (stepped ~45 deg)
SCREW_R = 1.7         # M3 clearance pilot through the boss (future cover)
N_BOSS = 4            # bosses per half, midway between tab roots
#   OPEN (top): open, keys exposed for now; MCU cover later (separate part
#   reusing these same nuts). Learn from Sofle/Corne/Lily proportions (low,
#   slim bezel) but designed, sound-focused — not a tray-mount box.
#   Cover MUST carry the W1/W2 windows + USB notch + TRRS channel openings
#   (they exist in the plate outline today; do not lose them in the cover).

# ---- tab pockets (lands.json roots; jackets swallow tab + both foams) ----
POCKET_CLEAR = 0.5        # side clearance in the pocket
POCKET_IN = 1.0           # pocket starts 1mm inside the rim line
POCKET_OUT = TAB_L + 0.5  # pocket nose past the tab tip
# Pocket vertical span swallows tab (1.5) + both foams (2x3.0 uncompressed):
POCKET_BOT = SHELF_Z          # pocket floor IS the shelf (foam rests on it)
POCKET_TOP = TOP_LIP_Z          # open to the top (cover presses upper foam)

# ---- wall openings ----
# USB notch + TRRS channel propagate via the plate outline itself (the rim
# follows the notched outline outward); verified on the 1:1 print + dry-fit
# gates in spec/first-article.md, not duplicated here.

FAB_NOTE = "defaults assume FDM printing (0.2 layer, 0.4 nozzle); revisit WALL_T/tolerances for CNC/SLS"

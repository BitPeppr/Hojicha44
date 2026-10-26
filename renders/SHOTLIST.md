# Hojicha44 render programme — round 9 target state

Written 2026-10-25, after the round-8 review. This file is the single
source of truth for WHAT gets rendered and WHY. Pipeline notes live in
`renders/README.md`; this is the shot plan.

## What the successful campaigns actually show

Research digest (round 9):

- **Keyboardio Model 01/100** ($652k, then $1M+ relaunch): leads with
  macro-detail shots — "a swooping motion control camera with a macro
  lens showed off all the beautiful detail". Heirloom-materials story.
- **Das Keyboard DeltaForce 65** (787%): construction story (gasket
  mount explained visually) + FOUR colourways, each with a pattern,
  extended onto a matching desk mat.
- **Keychron K2 HE** ($1.17M): one innovation (magnetic switches)
  explained + dual gamer/pro positioning.
- **X-Bows** (CA$324k): per-key lighting demos + colourways unlocked as
  stretch goals — colourways SELL.
- **Lofree Flow Lite** ($1M+): premium-minimal lifestyle; comparison
  displays.
- **Kinesis Freestyle Edge** (split, $89k): the split-gaming angle —
  palm supports, RGB variant, "same specs, versatile form".

Common threads: (1) hero 3/4 shot; (2) colourway SETS, not one; (3)
construction/exploded credibility; (4) macro detail; (5) top layout
view; (6) use-case scenes (gaming + professional); (7) wireless/
portability story.

## Shot list

### bright/ — product, standard colourway
| shot | status | notes |
|---|---|---|
| hero | keep | unchanged pose/colourway |
| top | keep | orthographic layout proof |
| exploded | REWORK | see exploded spec below |
| orbit_02, orbit_08 | keep 2 of 12 | delete the other ten |
| ~~macro_encoder, macro_keys~~ | DELETE | round-8 review: not needed |

### dark/ — "stealth" colourway on dark marble (round 10)
Black case (near-black alu look), dark-grey keycaps, near-black plate,
brass knob, **DARK swirly marble floor** (nero-marquina style: near-
black stone, gold-white vein accents, hard coat — round-10 review:
"dark, marbly, swirly, above all dark; not a kitchen slab"). Lighting:
gentle + atmospheric, LOW grazing accent lights sweeping across the
board at table height (nothing overhead, no window-like glare), tight
cool rim. Shots: hero, top, orbit_02, orbit_08. No exploded.

### colourways/ — fun sets (round 10: OUTSIDE the professional sets)
- **play** — multicolour keycaps from a curated 6-colour palette,
  scattered-but-balanced assignment; mid-grey case, silver plate.
  Shots: hero (+top). Its own directory set, never mixed into
  bright/dark.
- **artisan** — a NICHE FUN SET of singular expressive shots: the
  sculpted accent cap (oblate dome, concentric ridge rings, centre
  button, resin-teal + coat) gets its own closeup (`--colourway
  artisan --shots artisan`), never a slot in the professional hero
  sets.

### env/ — desk environments (UPGRADED)
- **desk** — wireless story (all keyboard cables hidden); upgraded
  props from `env_props.py`: sculpted ergonomic RH mouse (two buttons,
  thumb buttons), detailed ceramic mug, notebook with visible page
  blocks, lamp with real bulb + rocker switch, generic mini PC with
  side vents + full I/O + power/data cables (power comes from the
  wall — show it), elaborate monitor stand, `proc_walnut2` desk.
- **mat** — cable FIXED (rounds 9-10): three-point single dip (no
  W/quintic wiggles), plugs built from the EXACT posed hole position
  (computed through the tub's matrix_world — the bbox estimates both
  rounds read as "floating outside the port"), split 120 mm, camera
  raised to a ~37 deg down-angle (round 10: "not from the tabletop"),
  bokeh f/8.

### scenes/ — use-case scenes (NEXT round)
- **gaming** — dark room, PC tower with RGB fans glowing behind the
  halves.
- **dev** — top-down over the desk: mug between the halves, notebook,
  terminal glow on the screen. "software dev setup".

## Exploded spec (round-8 review fixes)

The round-8 exploded failed: radical colours (purple case, turquoise
plate — review: "slight colour variations, not something this
radical"), no interior detail (PCB hidden inside the un-exploded tub;
switches were black rectangles; no visible jack/MCU/encoder/pwrsw),
and it needed clean labels.

Round 9:
- **Motion**: tub drops −58 (PCB finally visible); gaskets +14;
  plate+switches +30; caps +48; cover +66; knob +82. Board at 0 = the
  reference layer.
- **Palette**: warm-neutral ladder, slight steps — graphite case,
  sand gasket, REAL-LOOK PCB (dark green + procedural gold trace web +
  vias, `proc_pcb`), silver plate, cream switch housings (real choc
  geometry, not rectangles), bone caps, warm-grey cover, brass knob.
- **Geometry**: real choc switches (`choc.glb`) instanced at every
  position; audio jack, MCU, encoder, power switch visible and
  distinctly tinted (gold jack, gunmetal encoder, charcoal MCU).
- **Labels**: 7 minimalist sans labels, billboards facing the camera,
  right side, one per layer with a hairline leader:
  bottom case / poron gasket / PCB + hotswap / plate + switches /
  keycaps / top plate / encoder knob. No boxes, no arrows, no slop.

## Render discipline (unchanged)
- Every camera passes `--framecheck` NDC pre-flight before sampling.
- Pixel-stat calibration for every new lighting setup:
  mean luma 0.30-0.45, blown < 1%, shadows p05 < 0.10.
- All outputs hashed in `MANIFEST.json` via `renders/manifest.py`.

# Hojicha44 3D models (render-only; no electrical/mechanical effect)

Vendored for `pcb render` eye candy. Placement/copper stay generator-owned.

- `SW_Hotswap_Kailh_Choc_V1.wrl` — Kailh CPG135001S30 socket, from
  kiswitch/kiswitch (`library/3dmodels/3d-library.3dshapes/`), MIT +
  CC-BY-SA 4.0 (footprint exception waives share-alike for board files).
  Our footprint pads are coordinate-identical to the paired kiswitch
  footprint, so the vendor identity transform is used verbatim.
- `PJ-320A.step` — XKB TRRS jack shell, from Keebio/Keebio-Parts.pretty
  (`3dmodels/PJ-320A.step`), MIT. Our pad coords match the paired Keebio
  footprint; vendor rotate (-90, 0, 180) kept. Verify shell orientation
  in the iso render after any footprint touch.
- `nice-nano-envelope.wrl` — hand-drawn bounding box (34.1 x 18.3 x 3.2mm
  per retailer dims), NOT a detailed module model. Proves keepout/stack
  envelope only. USB end toward footprint pad 1.

## Calibration note (2026-10-14)

KiCad reads VRML in 0.1-inch units (1 unit = 2.54mm) and maps VRML +y to
footprint-local -y — both proven by staged render tests (10-unit cubes at
known footprint origins, then a red envelope measured pixel-exact over the
MCU pads). Hand-written WRL must use /2.54 dims and (lx,-ly) mapping.

- `ROT_EC11E.step` — Alps EC11E rotary encoder body, from
  ebastler/marbastlib (`3dmodels/ROT_EC11E.step`), CERN-OHL-P-2.0.
  Paired in marbastlib as offset (-2.5,-7.5,0) + rotate (0,0,-90) on
  THEIR pad frame; ours remaps to offset (15,0,0) + rotate (0,0,180)
  via the verified 7-pad rigid correspondence (no mirror needed).
  Render-verified on first use; re-verify after any footprint touch.
- `ws-sltv-envelope.wrl` — hand-drawn bounding box for the Wuerth
  WS-SLTV slide switch (10x2.5x6.4 per footprint name). The stock
  footprint references a STEP that ships in NO KiCad bundle and exists
  in NO upstream repo (footprint added without its model), so an
  envelope is the only honest option short of drawing the part.

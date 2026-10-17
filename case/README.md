# Hojicha44 — case CAD (CadQuery, parametric)

Bottom tub + (later) top cover, derived from the laser plate — never
hand-drawn. Roadmap Phase 5: CadQuery generates, FreeCAD inspects,
Blender visualises.

## Layout

- `params.py` — every dimension with its spec source. Change here.
- `gen_case.py` — tub generator + self-checks. Outputs to `case/out/`
  (gitignored): STEP (exchange), STL (print).
- `requirements.txt` — pinned CadQuery (`case/.venv`, Python 3.12).

## Conventions (match the rest of the repo)

- Units mm. Frame = KiCad board frame (same as `lands.json` / plate DXF).
- z = 0 is the PCB top surface. Plate underside +2.0, plate top +3.5.
- Single source of truth: `plate/Hojicha44-{half}-plate.dxf` (OUTLINE +
  tab geometry via `lands.json`). Spec numbers: `spec/case.md`.
- Generators own geometry; `case/out/` is scratch like `out/fit`.

## Status

- v3.2 (strength + ports + antenna, user review round): **CASE_OUTSET
  6.0 → 7.0** — the wall over every tab tip measured exactly 0.5 (skin
  vs tab tip + RIM_CLEAR), 1-2 FDM extrusion lines at 8 stations, the
  "concerningly thin" sections the user flagged. Census now: wall min
  1.50 at all tab stations (gate ≥ 1.40), 6.50 typical. **Port slots
  re-z'd** — v3.1's cut ran from the case bottom and punched two
  through-holes in the floor slab at the anchors (the "hole in the
  bottom" the user found); slots now open the wall from FLOOR_Z (slab
  top) to the lip, sill intact, battery-probed. **TRRS slot 12 → 9.5**
  (molds the 90° boot, bore-side ≤ 8.5, not the jack body) — first
  article measures the real boot. **Antenna**: "no case material within
  3mm" (electronics.yaml) is now battery-gated at the module points
  (118/173.5, 15.55) at three z bands; nearest tub material is >19mm
  away by construction, so no antenna opening exists or is required in
  the tub — the duty moves to the future top cover.
- v3.1 (bulges fixed): the exterior dilates the PCB RIM, not the plate
  outline — the tabs are spliced INTO the plate outline, so dilating it
  gave the case eight 5mm bulges. Rim dilation keeps the wall uniform
  (measured: skin-to-rim max exactly 6.0, ~1.0 cover over every tab
  tip). Port slots re-anchored on the rim and span the full wall band
  (v3's were silent no-ops — battery passed by probing outside the
  case). Pocket noses adaptive per tab (5.5 nominal, floor TAB_L+0.2)
  where rim curvature eats the corner web.
- v3: uniform 6.0mm dilation of the plate outline — superseded by v3.1
  (dilating the tabbed outline bulged at every tab).
- v2: per-tab smooth swells — superseded (walls varied in thickness;
  uniform dilation is the reference-case answer). v1: stepped walls +
  bosses — superseded (jutting pockets, layer lines).
- Verify: `case/.venv/bin/python case/gen_case.py` (exit 0 = all gates).
  Inspect in FreeCAD when available; Blender for renders (not installed).

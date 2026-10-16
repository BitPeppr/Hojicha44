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

- v2: smooth homogeneous exterior: single vertical skin swollen gently
  over each tab (internal blind pockets, nothing punches through), no
  bosses/screws (friction now; cover fastening decided at cover time),
  explicit full-height USB/TRRS port slots (the wall-offset notch is too
  narrow for real plugs). No layer steps anywhere.
- v1: stepped wall + captive-nut bosses — superseded: exterior had
  jutting pockets/bosses and layer lines. Interior logic carried over.
- Verify: `case/.venv/bin/python case/gen_case.py` (exit 0 = all gates).
  Inspect in FreeCAD when available; Blender for renders (not installed).

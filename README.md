# kbd — split columnar keyboard (layout phase)

Custom split columnar mechanical keyboard. Roadmap: `KEYBOARD_PROJECT_ROADMAP.md`.
**Current phase: layout** (roadmap Phase 2). PCB / CAD / firmware come later
and live in their own top-level dirs when they do — nothing for them yet.

## Layout

| What | Where | Notes |
|---|---|---|
| Parametric source of truth | `layout/ergogen yaml/config.yaml` | Ergogen 4.2.1, 46 pts: 6×3 + 4 thumbs + encoder/side |
| KLE sketch (derived) | `layout/iterations/keyboard_layout_v2.json` | Do not hand-edit; regenerate |
| KLE sketch (archive) | `layout/iterations/keyboard_layout_v1.json` | Original row-staggered sketch |
| Layout decisions | `spec/layout.yaml` | Keymap, thumb roles, relocated keys |
| Generators | `layout/generators/` | `export_kle.py` (points → KLE), `render_preview.mjs` (KLE → labeled PNG) |
| Ergogen outputs | `layout/generated/v2/` | Points, outlines, demo SVGs, keymap render |
| Snapshots | `layout/iterations/` | v1–v4 KLE, v5–v6 Ergogen (frozen) |

## Regenerate

```sh
npx ergogen "layout/ergogen yaml" -o layout/generated/v2   # may need a second run; CLI quirk
python3 layout/generators/export_kle.py --check
node layout/generators/render_preview.mjs
```

## Previews

- Paste `layout/iterations/keyboard_layout_v2.json` into keyboard-layout-editor.
- Paste `layout/ergogen yaml/config.yaml` into ergogen.xyz.
- `layout/generated/v2/keymap.png` (+`.svg`) is a labeled render with the
  keymap baked in — no Ergogen PNG export exists, so this script draws it
  from the KLE (ImageMagick required).
- Never cross-paste: the KLE importer rejects mid-row rotation by design.

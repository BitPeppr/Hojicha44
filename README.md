# kbd — split columnar keyboard (layout phase)

Custom split columnar mechanical keyboard. Roadmap: `KEYBOARD_PROJECT_ROADMAP.md`.
**Current phase: layout** (roadmap Phase 2). PCB / CAD / firmware come later
and live in their own top-level dirs when they do — nothing for them yet.

## Layout

| What | Where | Notes |
|---|---|---|
| Parametric source of truth | `layout/ergogen yaml/config.yaml` | Ergogen 4.2.1, 44 pts: 6×3 + 4 thumbs/side |
| KLE sketch (derived) | `layout/versions/keyboard_layout_v2.json` | Do not hand-edit; regenerate |
| KLE sketch (archive) | `layout/versions/keyboard_layout_v1.json` | Original row-staggered sketch |
| Layout decisions | `spec/layout.yaml` | Keymap, thumb roles, relocated keys |
| Generator | `layout/generators/export_kle.py` | Ergogen points → KLE |
| Ergogen outputs | `layout/generated/v2/` | Points, outlines, demo SVGs |

## Regenerate

```sh
npx ergogen "layout/ergogen yaml" -o layout/generated/v2   # may need a second run; CLI quirk
python3 layout/generators/export_kle.py --check
```

## Previews

- Paste `layout/versions/keyboard_layout_v2.json` into keyboard-layout-editor.
- Paste `layout/ergogen yaml/config.yaml` into ergogen.xyz.
- Never cross-paste: the KLE importer rejects mid-row rotation by design.

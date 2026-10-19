# Hojicha44 — split columnar keyboard (PCB phase)

Custom split columnar mechanical keyboard (44 keys + 2 encoders, nice!nano x2).
Roadmap: `KEYBOARD_PROJECT_ROADMAP.md`.
**Current phase: placed+routed (r13), plate rev-8 gated, release cut, ZMK CI green** (roadmap Phase 4 done). Layout geometry lives in
`layout/ergogen/config.yaml` (frozen snapshot: `layout/- FINAL/keyboard_layout_v7`);
each half has a placed+routed board file — see [Schematic](#schematic).

## Layout

| What | Where | Notes |
|---|---|---|
| Parametric source of truth | `layout/ergogen/config.yaml` | Ergogen 4.2.1, 46 pts: 6×3 + 4 thumbs + encoder/side |
| KLE sketch (derived) | `layout/- FINAL/keyboard_layout_v2.json` | Do not hand-edit; regenerate |
| KLE sketch (archive) | `layout/- FINAL/keyboard_layout_v1.json` | Original row-staggered sketch |
| Layout decisions | `spec/layout.yaml` | Keymap, thumb roles, relocated keys |
| Board outline | `layout/generated/v2/outlines/board.dxf` | PCB edge, no encoder hole — the EC11E needs copper under it |
| Plate outline | `plate/Hojicha44-{Left,Right}-plate.dxf` | Same contour + tabs, 12.7mm square encoder hole |
| Generators | `layout/generators/` | `export_kle.py` (points → KLE), `render_preview.mjs` (KLE → labeled PNG) |
| Ergogen outputs | `layout/generated/v2/` | Points, outlines, demo SVGs, keymap render |
| Snapshots | `layout/- FINAL/` | v1–v4 KLE, v5–v6 Ergogen, v7 config, v8 layout (frozen) |

## Schematic

| What | Where | Notes |
|---|---|---|
| Electronics spec | `spec/electronics.yaml` | Source of truth: matrix, pin map, parts |
| Generator | `pcb/generators/gen_schematic.py` | Spec → `.kicad_sch` + ERC + net audit; never hand-edit the schematic |
| Left project | `pcb/kicad/Hojicha44-Left.kicad_sch` | One project + one board file per half (a split is two PCBs) |
| Right project | `pcb/kicad/Hojicha44-Right.kicad_sch` | Same; both share the vendored libs below |
| Board files | `pcb/kicad/Hojicha44-{Left,Right}.kicad_pcb` | Placed+routed: 54 footprints / 48 nets per half, outline from `board.dxf`. Hand copper is preserved via `hand-copper.txt`; router-owned copper regenerates on every run |
| Hand-copper manifest | `pcb/kicad/hand-copper.txt` | The authoritative preserve set, scoped per half (`[Left]`/`[Right]`). A regen keeps only items matching manifest signatures; a manifest line the committed board lacks is a hard error |
| Placement generator | `pcb/generators/gen_pcb.py` | Points + outline + netlist → boards. Extraction reads the committed baseline (git HEAD), gates run before the write, and a DRC-rejected board is reverted so it can never leak into the next build |
| ZMK firmware | `boards/shields/hojicha44/` + `config/` | Shield dtsi/overlays/Kconfig + keymap/conf; compiled by CI (`.github/workflows/build.yml`), no local `west build` |
| ZMK evidence | `zmk/gpio-map.md` | Machine-generated GPIO continuity map |
| Project symbols | `pcb/kicad/Hojicha44.kicad_sym` | Local `nice!nano` (stock libs cover the rest) |
| Project footprints | `pcb/kicad/Hojicha44.pretty/` | Choc hotswap, PJ-320A, 2x12 nice!nano socket (vendored, see spec `sources`) |

Why two projects: a single flat sheet produces one netlist, so
"Update PCB from schematic" would drop both halves into one board file.
One project per half keeps each outline, netlist and DRC separate; the
half-to-half link (TRRS_T/TRRS_R1 crossover) lives in the spec, not the netlist.

Each half differs from the other only in the TRRS TX/RX swap: `D1→TRRS_T`
on the left, `D1→TRRS_R1` on the right, for a straight cable. The crossover
is copper, so both halves share identical UART pinctrl (`TX=P0.06 RX=P0.08`)
— no firmware swap; see `zmk/`.

```sh
python3 pcb/generators/gen_schematic.py   # spec check + both sheets + audit + ERC
```

```sh
python3 pcb/generators/gen_pcb.py         # place both boards + containment + DRC gate
```

The schematic generator also asserts the two things ERC and DRC cannot catch:

- **Socket rows are 15.24mm apart, pitch 2.54mm.** `Socket_Strips_2x12_P2.54mm_NiceNano` numbers 1–12
  down the TX/D1 edge and 13–24 down the RAW edge in the *opposite*
  direction, so pads 1 (D1) and 24 (RAW) share the USB end. The stock
  `PinSocket_2x12` is row-major with 2.54mm row spacing and would land every MCU net on the wrong
  pad while still passing both checks — and the module would not fit.
- **Reference designators.** KiCad treats a refdes not ending in a digit as
  un-annotated, which makes every netlist/PCB export warn even though ERC is
  clean.

`kicad-cli` lives inside the KiCad bundle
(`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, v10.0.6 here) —
it is not on `PATH` by default. The generator finds it automatically.

## Build notes (things that will bite you at assembly)

**TRRS cable — buy a 90° right-angle one.** The two jack mouths face each other across
22.40mm of mouth-to-mouth clearance (plastic faces; 20.42mm board-edge to
board-edge, each mouth 0.99mm recessed behind its edge — silk tops at
21.40mm, still recessed). A molded *straight* plug protrudes ~12mm
past the jack face, so the pair needs ~24mm and **is a tight fit at best**. A
90° plug protrudes only ~2–4mm axially because the boot exits perpendicular, so
the current gap is ample. 90° is the community standard for splits anyway (less
port torque). Size the cable port-to-port **+2–5cm minimum** — both cables exit
upward and arch over the gap.

**Always power-cycle in this order:** plug/unplug the TRRS with **both halves
switched OFF *and* USB unplugged from both**, then switch on. Switch OFF alone
is insufficient — USB still powers the controller. Sleeve-GND mates at an angle
during insertion, so connecting live can glitch TX/RX.

**Don't treat TRRS as a daily link.** splitkb's own nice!nano FAQ is blunt:
*"Do not use a cable between the halves… shorting connections when unplugging
while the battery is still on… unbalanced charging when two batteries are
connected."* This design already isolates ring 2, which blocks the charging half;
the shorting half is only mitigated by the power-off ordering above. TRRS here is
a bring-up/debug fallback — move to 4-pin JST if you want it in normal use.

**Battery: the 301230 goes directly under the module. This is correct.** The
cell's south 5mm sits over the antenna keepout circle, which looks alarming on
the preview but is exactly what Lily58, Corne, Sofle, the whole splitkb Aurora
series, and nicekeyboards' own docs do — none apply a cell keepout. The r=5
copper keepout is on *our* PCB and is honoured independently; the cell is a
different layer. A PCB trace antenna has a null perpendicular to its plane, so a
cell 3mm below the antenna end is in the null, not shadowing the main lobe.
If BLE range ever disappoints, the documented upgrades are a 301228 (90mAh) or a
306080 between PCB and bottom plate with 9mm standoffs.

## Regenerate

```sh
npx ergogen layout/ergogen -o layout/generated/v2 --svg --clean
node layout/generators/dump_points.cjs            # restores the JSON/YAML sidecars (4.2.1 no longer writes them)
python3 layout/generators/export_kle.py --check
node layout/generators/render_preview.mjs
```

PCB (place + route; generator copper + preserved GUI copper):

```sh
python3 pcb/generators/gen_schematic.py   # spec check + both sheets + guards + audit + ERC
python3 pcb/generators/gen_pcb.py         # place + route + containment + copper checks + DRC
```

`gen_pcb.py` owns the outline, footprints, nets, placement and generator
copper (deterministic router `gen_route.py`, revision-tagged so stale copper
is dropped, never silently kept). **GUI copper is the
other way round:** `(segment …)`, `(via …)` and `(zone …)` are preserved verbatim
from the board file (net codes remapped by *name*, since codes are not stable
across netlist exports). GUI routes survive regeneration (generator copper is
revision-tagged, so a router rev drops only stale generator copper, never
GUI copper). The build fails, rather than quietly producing a
broken board, if preserved copper no longer lands on a pad/via/track — the usual
result of moving a footprint without re-routing — or if it enters the r=5mm
antenna keepout.

## Previews

- Paste `layout/- FINAL/keyboard_layout_v2.json` into keyboard-layout-editor.
- Paste `layout/ergogen/config.yaml` into ergogen.xyz.
- `layout/generated/v2/keymap.png` (+`.svg`) is a labeled render with the
  keymap baked in — no Ergogen PNG export exists, so this script draws it
  from the KLE (ImageMagick required).
- Never cross-paste: the KLE importer rejects mid-row rotation by design.

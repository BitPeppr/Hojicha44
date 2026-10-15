# Hojicha44 — bill of materials (per half ×2, plus assembly notes)

Source of truth for part numbers: `spec/electronics.yaml`. Schematic symbols
carry `MPN` (all parts) and `Datasheet` (controller) properties from
`pcb/generators/gen_schematic.py`; verify with:

```sh
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$K sch export bom --fields "Reference,Value,Footprint,MPN,Datasheet,QUANTITY" \
  -o /tmp/bom.csv pcb/kicad/Hojicha44-Left.kicad_sch
```

`Datasheet` holds a URL only where one is certain (controller docs); every
other part is identified by exact `MPN` text — no guessed vendor links.

## SMT (fab assembly)

| Qty | Part | Notes |
|---|---|---|
| 22 | 1N4148W, SOD-123 (example MPN: Diodes Incorporated 1N4148W-7-F, SOD-123 — listed at DigiKey `1N4148W-7-F` and Mouser `1N4148W-7-F`, manufacturer page `diodes.com/part/view/1N4148W`; or equivalent) | matrix diodes, front side |

## Hand assembly (through-hole / modules / mechanical)

| Qty | Part | Notes |
|---|---|---|
| 22 | Kailh PG1350 (Choc v1) switches | top side, seat into sockets — PG1350 names the family/series; builder chooses the exact feel/variant as a kit part (e.g. linear/tactile/clicky) — any PG1350 Choc v1 fits |
| 22 | Kailh Choc v1 hotswap sockets | SMD bottom (pads part of footprint) |
| 1 | nice!nano v2 module | socketed, USB end to board notch |
| 2 | machine-pin SIP strips 2×12, 2.54mm pitch, 4.5–5.0mm stack | socket rows 15.24mm apart; Mill-Max 315 2.11mm banned (needs 3.5mm min for the cell) |
| 1 | Alps EC11E15244G1 | vertical, 30 detents / 15 pulses, knob ~10mm proud (trim shaft fallback) |
| 1 | Knob, 6mm bore, ≤13mm dia (kriscables anodized aluminium EC11 knob, 13×13mm, €4.90) | clears the 16mm plate cutout; set-screw clamps anywhere on the 20mm shaft — first-article: spin + push clearance vs plate |
| 1 | XKB PJ-320A TRRS 3.5mm | bring-up/debug link only; 90° cable required |
| 1 | TRRS cable, 4-pole CTIA, right-angle 3.5mm both ends, short | mouths face each other across a 22.40mm gap — straight plugs collide head-on; measure the boot, must clear the recessed mouths (0.99mm). No vendor link guessed; any CTIA right-angle cable meeting the fit check in §1 does |
| 1 | Kapton (polyimide) tape, ≥10mm wide | cell sandwich: pouch face + nano underside before the cell goes in |
| 1 | JST S2B-PH-K-S + PHR-2 housing + 2× SPH-002T-P0.5S crimps | battery connector set, side-entry |
| 1 | Würth WS-SLTV 450301014042 | slide SPDT, pad 1 (middle) = common, 300mA switching (fine at 100mA default; leave charge-boost open) |
| 1 | 301230 LiPo cell (see below) | with protection PCM + JST-PH 2.0mm pigtail |

## Case (rev-1 plate + gaskets, per half ×2)

| Qty | Part | Notes |
|---|---|---|
| 1 | Switch plate, 1.5mm, laser-cut | `plate/Hojicha44-{Left,Right}-plate.dxf` (R12, mm); material per `spec/case.md` (default PC); 22× 15×15 Choc cutouts, 12.5² encoder hole, component windows, 8 gasket tabs (NO screws/holes beyond openings) |
| ~2 | Poron gasket strip, 90×4×3mm, 4701-40 adhesive (Keebox 32-pack or equivalent) | per half: 16 pads (8 tabs × 2 faces) cut 8×4 from strip; -30 softer / -50 firmer swap without CAD change |

## Cell — locked to orderable stock (was TBD)

- Primary: kriscables 301230 110mAh + JST PH 2.0mm (€18.90, SKU
  `Li-Po Battery 110mah-1`, tagged nice!nano — order 2 for a split).
  Verified on the listing: 3×12×30mm, 3.7V, 110mAh, PH 2.0mm, ~3cm leads.
  Charge math on the same page: 100mA → ~1.1h, i.e. 0.9C — suitable.
- Alternates (same class, check stock): KEEBD 301230 110mAh (states PCM
  explicitly, PH 2.0mm options, $5.00) and Typeractive 110mAh 301230
  (PH 2.0mm, "fits snugly underneath a nice!nano", $3.00) — both were
  sold out at check time.
- Hard requirements any cell must meet: 301230 size (302030 does NOT fit —
  20mm fouls the socket pins), 3.7V, ≥100mAh, protection PCM (reject any
  unprotected pouch on arrival), JST-PH 2.0mm pigtail with red=pack+.
- Pack+ (red) to switch common, pack− (black) to GND; charges only with
  the switch ON. Meter the pigtail polarity against JST pin 1 BEFORE the
  first plug-in (reverse polarity kills board and cell).
- First-article DMM checks (both halves): RAW↔B+ short, GND↔B− short,
  RAW↔VCC open; charge-ON orange LED.
- Charge-ON labeling: mark the case at each half "charge only when ON"
  (switch upstream of RAW — OFF does nothing); first-article verifies the
  orange LED lights with switch ON and stays dark with OFF.

## Fab limits — confirm with the chosen fab BEFORE ordering

- Confirm minima/cost for this 2-layer 1.6mm stackup: 0.25mm track /
  0.2mm clearance / 0.8-0.4mm via, plus routed-slot rules for rev-2 flex
  cuts (typically >=1mm). Do not order until the fab accepts the
  Gerber/drill pack against these limits.

## Not parts (fab features)

3× fiducials + 2× 3.2mm NPTH tooling holes per half, placed by the
generator. Gasket mounting uses no PCB holes.

## Fab note

Each half is ~150×115mm — over the 100×100mm value tier at JLCPCB/PCBWay,
so price both tiers (and panel-by-2 quotes) before ordering. Design-vs-fab
limits, checked 2026-10-14 against JLCPCB's published 1–2 layer
capabilities (PCBWay comparable — recheck its page if you use them):
0.25mm tracks (min 0.10), 0.2mm clearance (min 0.10), 0.3/0.6mm signal
vias + 0.5/1.0mm power vias (min drill 0.15, annular ≥0.15; ours 0.15/0.25),
150×115mm halves (2-layer max 670×600), 1.6mm/0.3 drill = 5.3:1 aspect
(max 8:1). Order **tab-routed, not V-scored**: V-cut wants 0.3mm
copper-to-edge and our measured minimum is 0.29. The outline is concave,
so put this in the fab order comment verbatim: `CONCAVE OUTLINE —
TAB-ROUTE ONLY, NO V-CUT / V-SCORE` — otherwise the outline is rejected
or broken at depaneling.

Stack budget (cell under module, per half): 4.5mm sockets − 3.0 cell −
~0.5 PCM − ~0.2 tape ≈ 0.8mm spare (1.3 with 5.0mm rows). Mill-Max 2.11mm
goes negative — banned, as specified. Confirm PCM/tape thickness and wire
dressing on the first cell; JST lives beside the cell, never under it.

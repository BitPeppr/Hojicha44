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
| 22 | 1N4148W, SOD-123 | matrix diodes, front side |

## Hand assembly (through-hole / modules / mechanical)

| Qty | Part | Notes |
|---|---|---|
| 22 | Kailh PG1350 (Choc v1) switches | top side, seat into sockets |
| 22 | Kailh Choc v1 hotswap sockets | SMD bottom (pads part of footprint) |
| 1 | nice!nano v2 module | socketed, USB end to board notch |
| 2 | machine-pin SIP strips 2×12, 2.54mm pitch, 4.5–5.0mm stack | socket rows 15.24mm apart; Mill-Max 315 2.11mm banned (needs 3.5mm min for the cell) |
| 1 | Alps EC11E15244G1 | vertical, 30 detents / 15 pulses, knob ~10mm proud (trim shaft fallback) |
| 1 | Knob, 6mm bore, ≤13mm dia (kriscables anodized aluminium EC11 knob, 13×13mm, €4.90) | clears the 16mm plate cutout; set-screw clamps anywhere on the 20mm shaft — first-article: spin + push clearance vs plate |
| 1 | XKB PJ-320A TRRS 3.5mm | bring-up/debug link only; 90° cable required |
| 1 | JST S2B-PH-K-S + PHR-2 housing + 2× SPH-002T-P0.5S crimps | battery connector set, side-entry |
| 1 | Würth WS-SLTV 450301014042 | slide SPDT, pad 1 (middle) = common, 500mA/12VDC |
| 1 | 301230 LiPo cell (see below) | with protection PCM + JST-PH 2.0mm pigtail |

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

## Not parts (fab features)

3× fiducials + 2× 3.2mm NPTH tooling holes per half, placed by the
generator. Gasket mounting uses no PCB holes.

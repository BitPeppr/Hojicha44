# Vendored stock footprints (plate/gen_plate.py inputs)

Two footprints from the STOCK KiCad library are read by `plate/gen_plate.py`
to derive the W1 component windows (power-switch courtyard, JST F.Fab):

- `Button_Switch_THT.pretty/SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm.kicad_mod`
- `Connector_JST.pretty/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.kicad_mod`

They are vendored (copied verbatim) so the plate gates run on any machine
and in CI without a KiCad installation. `gen_plate.py` reads this directory
FIRST and falls back to the local KiCad install (`KICAD_STOCK_FP` env var,
default `/Applications/KiCad/KiCad.app/...` macOS path).

## Provenance

- Source: KiCad official footprint libraries, shipped with **KiCad 10.0.6**
  (the same version listed in every `generated/release/*/MANIFEST.txt`).
- License: KiCad libraries header, files are CC-BY-SA 4.0
  (https://www.kicad.org/libraries/license/). These two files carry the
  standard attribution header block at the top.

## Update rule

If the switch/JST instances in the PCBs are ever re-placed with different
footprints, update `fp_source` consumers + re-vendor the matching file from
the same KiCad version the release manifests cite.

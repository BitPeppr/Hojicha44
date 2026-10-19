# Vendored stock footprints

Byte-identical copies of six stock KiCad footprint definitions
(KiCad 10.0.6 `SharedSupport/footprints`), for the libs `gen_pcb.FP_SRC`
resolves outside `Hojicha44.pretty`: Diode_SMD, Rotary_Encoder,
Connector_JST, Button_Switch_THT, Fiducial, MountingHole.

Why: `check_board`'s notch-copper gate reconstructs the builder's
placement/pad model, which reads footprint geometry via `fp_source`. CI
has no KiCad install (and the macOS path is machine-specific), so the
stock sources ship in-repo. `fp_source` prefers these copies and falls
back to the local install.

Not referenced by any KiCad project config (`fp-lib-table` untouched) —
KiCad resolves libraries from its own environment during build/DRC, so
these files change nothing about what KiCad sees; they are a
construction-input convenience for the Python pipeline only.

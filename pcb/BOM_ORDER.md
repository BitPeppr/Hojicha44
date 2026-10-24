# Part order list (v0.5.0) — with live-verified SKUs

Prices/stock verified 2026-10-19 against vendor pages — they WILL drift;
re-check at cart time. PCB fab choices are NOT here: see
`MANUFACTURING.md`. Quantity basis: the full split (2 halves).

## A. SMD pass (DigiKey)

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | 50 | Diodes Inc **1N4148W-7-F** (DigiKey `1N4148W-7-F`) | $3.84 | SOD-123 matrix diodes, 44 needed + spares; same MPN as footprint/schematic |

## B. Modules (splitkb.com)

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | 2 | **nice!nano v2** | €21.44 ea | Typeractive $25 is sold out (restock notify); KEEBD $25 stock spotty |
| ☐ | 2 | **Mill-Max low-profile socket set** (sockets **315-43-112-41-003000** + 3320-series pins) | €6.60/set | matches `spec/bom.md` 4.5–5.0mm stack → 12mm cell clearance; NOT the banned 2.11mm 315 variant; Typeractive set $6.50 is the same class |

## C. Distribution pass (DigiKey / TME / LCSC)

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | 2 | **Short-shaft EC11-class rotary encoder, D-flat Ø6, with push** — the generic "EC11 10–15mm D-shaft, 30-detent/15-pulse, with push" (the class the Sofle Choc build guide documents: "prefer short shaft… 10mm, D-shaped shaft, 30 positions"); the tip must land **≤14mm above the PCB** and the body must match the EC11E 11mm-class envelope (the case window is sized to it) — **verify tip height + "with switch" on the listing before ordering** | ~$1.50–2.50 | ⚠ ALPS **EC11E15244G1** (TME, $2.58) is the fallback: it is the **20mm-actuator** part (tip 24.55mm — the low knob's bore tops out ~15.1), so pair it with a tall knob or trim the shaft. The **ALPS EC12** (e.g. EC12E1220301, ≈8.5mm total) is the lowest same-footprint-family part but has **NO push switch** (the keymap's encoder-push binding orphans) and a 12.4mm body that needs the case window opened ~0.5mm — a case rev, not a drop-in |
| ☐ | 2 | Würth **450301014042** (DigiKey) | $2.15 | WS-SLTV slide SPDT; no drop-in alternate (clones need footprint check) |
| ☐ | 2 | JST **S2B-PH-K-S** (DigiKey) | $0.12 | side-entry battery header |
| ☐ | 2 | JST **PHR-2** housing | $0.10 | |
| ☐ | 1 | JST **SPH-002T-P0.5S** contacts, strip of 100 | $4.09 | 4 needed; strip = cheapest entry + spares |
| ☐ | 2 | XKB **PJ-320A** (LCSC **C2884926**, MOQ 5) | $0.75 | footprint is PJ-320A-specific — don't substitute PJ-3xx variants |
| ☐ | 2 | **Low round EC11 knob, Ø6 D bore**: OD 15–17mm, height ≤12mm, bore deep enough to swallow the ~13.5mm shaft tip — e.g. a fluted aluminium EC11 knob (beekeeb stocks ≤15.5mm ones) or print the committed geometry (`renders/build_assets.py` knob_glb: Ø16.8 × 9.2, 18 flutes) | ~$4–8 | committed geometry: skirt bottom at 6.1 abs — must stay ≥0.9mm above the 5.2 cover (EC11 push travel 0.5±0.3); the Ø16.8 sweep clears the nearest cap (SW_L17, 24.04mm centre) by 3.6mm at every angle. The old kriscables 13×13 **square** knob is a tall-shaft part — do not pair it with the short-shaft encoder. Shaft is D-flat: align the bore's flat on press-on |

## D. Keyboard-specialty pass

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | 2 | kriscables **301230 110mAh LiPo**, PCM + JST-PH pigtail | €8.90–18.90 ea (two listings seen; re-check at checkout) | spec-locked size (30×12×3 — 302030 does NOT fit); meter pigtail polarity vs JST pin 1 BEFORE first plug-in |
| ☐ | 2 | **Polyfuse (PPTC), 0.5–1A hold, ≥16V** (axial/radial) | ~$1–2 | series with pack+ (1/half; the 10-half pilot buys 20) — wired, NOT on the PCB; research §2b/2d |
| ☐ | 5 | Kailh **PG1350 Choc v1** switches (Typeractive, $5.50/10) | $27.50 | 44 needed; pick feel family; any PG1350 fits the hotswap socket |
| ☐ | 44 | **Kailh Choc v1 hotswap SOCKETS** (socketed, bottom side) | ~$1–2 ea | **not in the released bom.csv** — the release BOM only lists parts with an MPN, and a footprint-only socket has none, so this line is the ONLY place the 44 sockets get ordered. Sockets solder on B.Cu under each switch; the diode sits beside its switch, not under it. Verify the variant matches the vendored `SW_Hotswap_Kailh_Choc_V1_1.00u` footprint (the spec fixes the footprint, not the SKU) |
| ☐ | 1 | KEEBD **24cm dual right-angle TRRS cable**, 4-pole CTIA | $6.00 | both ends MUST be 90° — straight plugs collide across the 22.4mm mouth gap |
| ☐ | 44–50 | **MBK Choc keycaps** (PBT, Typeractive ~$1/cap) | ~$44 | Choc v1 stems only (MX won't fit); MBK legend sets spotted sold out at splitkb — CFX (~$25/set) is the budget fallback |
| ☐ | 1 | supermagnete **S-04-02-N** ×20 (Ø4×2mm) | €5.60 | TUB magnets, face-up flush, 16 needed |
| ☐ | 1 | supermagnete **S-04-1.5-N** ×20 (Ø4×1.5mm) | €4.60 | COVER magnets, face-down flush, 16 needed; the height pair is deliberate — faces meet at the lip plane |
| ☐ | — | glue for the magnets: **B-7000** | $5 | flexible, nylon-safe (PA12); JB-Weld rigid alt; no hot glue |

## E. Case-shop pass

> **Send exactly the files hashed in `generated/print/v0.5.0/MANIFEST.txt`**
> (sha256, both shops: plate DXF/SVG for the laser, case STEP/STL for MJF).
> If any generator constant changed, regenerate everything and re-record
> the manifest in the same commit — never order from a stale hash.

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | — | Rogers **PORON 4701-30** Very Soft ~3mm sheet (McMaster search "Rogers 4701-30" or silicone-foams.com) | ~$10–15 | 16 pads/half cut **7×4** (4/7mm punch — the audit-round carve; 8mm pads leave only 0.35mm to the plate edge, 7mm leaves 0.71mm); ≈12 pads per 90mm strip; Keebox 32-strip pack (AliExpress) is the sanctioned swap-in fallback; ladder −30→−40→−50, no CAD change |
| ☐ | 2 | plate cut, **1.2mm**, from `plate/Hojicha44-{Left,Right}-plate.dxf` (mm) | ~$10–20 ea | **1.2mm is mandatory** — the Choc v1 clip only engages 1.2mm; 1.5/1.6 gives friction-only, no retention (`MANUFACTURING.md`). Default material PC per `spec/case.md` (POM = the firmer upgrade); 42keebs/PCBWay/JLCCNC accept DXF; ask no kerf comp. **The DXF carries four layers — paste this into the order:** OUTLINE + CUTOUT cut **through**; **RELIEF = 22 × 0.55mm-deep pockets milled into the UNDERSIDE — machine that depth, do NOT cut through** (0.65mm of plate must remain; a diode fouls a through-cut plate); **PORON = gasket punch template, do not cut it**. **Ask the shop FIRST whether they can do the 0.55mm partial depth** (a plain laser CUT cannot; controlled-depth laser ENGRAVING or CNC depth milling can — PCBWay's Z-Axis Milling is a documented service, depth tolerance ±0.15mm → order **0.70mm nominal** and caliper the delivered 0.55–0.85 on the coupon; JLCPCB publishes no controlled-depth service, checked 2026-10-23) — if not, this order waits (see `spec/bom.md` vendor instruction + first-article coupon) |
| ☐ | — | case + top plate **MJF PA12** (JLC), files from `gen_case.py`/`gen_cover.py` | per quote | volumes L 57.5 / R 57.5 cm³ (tub, floor −6.35) + cover 15.2 cm³ (key-field ledge) — measured 2026-10-24 (71.1/10.7 predates the thin-top + floor revs); MJF quotes from volume, so quote THESE. Self-print alternative: **PETG 100% infill** is supported (strength audit in `spec/case.md`) — a printed set is the cheap pre-MJF fit article |
| ☐ | 1 roll | Kapton/polyimide tape ≥10mm | $2–5 | cell sandwich + nano underside |
| ☐ | 1 | SAC305 no-clean 0.5mm solder (e.g. SRA) + **NC-559-class flux pen** | ~$25 + ~$10 | ENIG pads, hand work |

## PCB order note (must be pasted into the fab order)

The outline is CONCAVE, so the board MUST be tab-routed (a V-cut
wants a straight edge anyway). The measured minimum copper-to-edge is
**0.406mm Left / 0.575mm Right** (M3.6 nudge, 2026-10-23 — was
0.292/0.330), which passes BOTH published rules with margin:
JLCPCB's 0.2mm tab-route rule ("0.3mm for V-cut panelization and
0.2mm for tab-routing") AND PCBWay's 0.3mm profile-to-copper figure —
the board is fab-agnostic, no written confirmation needed. CNC
routing tolerance is ±0.1mm (precision) / ±0.2mm (regular) per
JLCPCB's capabilities page — if the quote offers the precision tier
for a small fee, prefer it to protect the notch corridor. Put this in
the order verbatim:

```
CONCAVE OUTLINE — TAB-ROUTE ONLY, NO V-CUT / V-SCORE
```

(also stated in `spec/bom.md`; the fab rejects or breaks the panel
otherwise).

## Cart mechanics

- Order-split reality: DigiKey/TME/LCSC (A+C), splitkb (B),
  kriscables (knob, battery), Typeractive (switches/caps/sockets,
  in-stock check first), KEEBD (cable), supermagnete, then the
  case/plate services. They don't consolidate — expect 5–7 carts.
- **Pending stock at check time**: Typeractive nice!nano +
  sockets, MBK legend sets. splitkb fills those roles now; set
  restock notifications as backup.
- **PCBs are a separate order** — see `MANUFACTURING.md` (the two
  designs are ordered as two 5-pc line items, ENIG chosen in the form).
- Rough part total **~$310–350** firm picks (ex-PCBs, ex-shipping);
  ~$230–250 with budget alternates.
- Message-order across carts (polarity-critical first): everything
  above can be bought simultaneously EXCEPT nothing — no part here
  depends on another's arrival. Only *assembly* has gates
  (`spec/first-article.md`).

## Verify-at-cart flags (things research flagged or spec demands)

1. **Encoder must have the push switch** (ALPS "G1" suffix; the B2 clone is cheaper and wrong — and the generic short-shaft parts come with and without push: order WITH).
2. **Socket kit = 3.0mm 315 sockets + pins** (assembled 4.5–5.0mm). The
   2.11mm set is banned by the cell sandwich.
3. **Battery = 301230 only** (30×12×3). Any other clearance story is
   fiction; measure nothing, just match the size.
4. **TRRS cable: right-angle both ends.**
5. **Magnet codes**: S-04-02-N and S-04-1.5-N (supermagnete).
6. KiCad 10.0.6 measurements hold steady in this doc; if the layout
   ever re-cuts, re-read `spec/bom.md` first — this list derives from it.

## Sources

Prices from live vendor listings 2026-10-19 via research pass:
DigiKey (1N4148W-7-F, 450301014042, JST PH items), TME (EC11E15244G1),
LCSC C2884926, splitkb (nano, Mill-Max sets), Typeractive (switches,
caps), kriscables (knob, 301230), KEEBD (TRRS cable),
supermagnete S-04 data sheets, SRA (SAC305), 42keebs (laser plate).
Key repo sources of truth: `spec/bom.md`, `spec/electronics.yaml`,
`spec/first-article.md`, `spec/case.md`.

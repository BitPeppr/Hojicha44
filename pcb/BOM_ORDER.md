# Part order list (v0.3.1) — with live-verified SKUs

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
| ☐ | 2 | Alps **EC11E15244G1** (TME) | $2.58 | ⚠ must be the **G1** (with push switch — mute sideband); LCSC's cheaper EC11E15244**B2** has NO switch: wrong part |
| ☐ | 2 | Würth **450301014042** (DigiKey) | $2.15 | WS-SLTV slide SPDT; no drop-in alternate (clones need footprint check) |
| ☐ | 2 | JST **S2B-PH-K-S** (DigiKey) | $0.12 | side-entry battery header |
| ☐ | 2 | JST **PHR-2** housing | $0.10 | |
| ☐ | 1 | JST **SPH-002T-P0.5S** contacts, strip of 100 | $4.09 | 4 needed; strip = cheapest entry + spares |
| ☐ | 2 | XKB **PJ-320A** (LCSC **C2884926**, MOQ 5) | $0.75 | footprint is PJ-320A-specific — don't substitute PJ-3xx variants |
| ☐ | 2 | kriscables **anodized EC11 knob 13×13mm**, 6mm bore | €4.90 | ≤13×13 square constraint per `spec/bom.md` (first-article spin/push check) |

## D. Keyboard-specialty pass

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | 2 | kriscables **301230 110mAh LiPo**, PCM + JST-PH pigtail | €8.90–18.90 ea (two listings seen; re-check at checkout) | spec-locked size (30×12×3 — 302030 does NOT fit); meter pigtail polarity vs JST pin 1 BEFORE first plug-in |
| ☐ | 5 | Kailh **PG1350 Choc v1** switches (Typeractive, $5.50/10) | $27.50 | 44 needed; pick feel family; any PG1350 fits the hotswap socket |
| ☐ | 44 | **Kailh Choc v1 hotswap SOCKETS** (socketed, bottom side) | ~$1–2 ea | **not in the released bom.csv** — the release BOM only lists parts with an MPN, and a footprint-only socket has none, so this line is the ONLY place the 44 sockets get ordered. Sockets solder on B.Cu under each switch; the diode sits beside its switch, not under it. Verify the variant matches the vendored `SW_Hotswap_Kailh_Choc_V1_1.00u` footprint (3.4×2.5mm pad pair per spec) |
| ☐ | 1 | KEEBD **24cm dual right-angle TRRS cable**, 4-pole CTIA | $6.00 | both ends MUST be 90° — straight plugs collide across the 22.4mm mouth gap |
| ☐ | 44–50 | **MBK Choc keycaps** (PBT, Typeractive ~$1/cap) | ~$44 | Choc v1 stems only (MX won't fit); MBK legend sets spotted sold out at splitkb — CFX (~$25/set) is the budget fallback |
| ☐ | 1 | supermagnete **S-04-02-N** ×20 (Ø4×2mm) | €5.60 | TUB magnets, face-up flush, 16 needed |
| ☐ | 1 | supermagnete **S-04-1.5-N** ×20 (Ø4×1.5mm) | €4.60 | COVER magnets, face-down flush, 16 needed; the height pair is deliberate — faces meet at the lip plane |
| ☐ | 1 | glue for the magnets: **B-7000** | $5 | flexible, nylon-safe (PA12); JB-Weld rigid alt; no hot glue |

## E. Case-shop pass

| Buy | Qty | Part | ~Price | Note |
|---|---|---|---|---|
| ☐ | — | Rogers **PORON 4701-30** Very Soft ~3mm sheet (McMaster search "Rogers 4701-30" or silicone-foams.com) | ~$10–15 | 16 pads/half cut **7×4** (4/7mm punch — the audit-round carve; 8mm pads leave only 0.35mm to the plate edge, 7mm leaves 0.71mm); ≈12 pads per 90mm strip; Keebox 32-strip pack (AliExpress) is the sanctioned swap-in fallback; ladder −30→−40→−50, no CAD change |
| ☐ | 2 | plate cut, **1.5mm**, from `plate/Hojicha44-{Left,Right}-plate.dxf` (mm) | ~$10–20 ea | default material PC per `spec/case.md` (POM = the firmer upgrade, see MANUFACTURING.md); 42keebs/PCBWay/JLCCNC accept DXF; ask no kerf comp |
| ☐ | — | case + ring cover **MJF PA12** (JLC), files from `gen_case.py`/`gen_cover.py` | per quote | volumes L 75.7 / R 75.7 cm³ (tub, OUTSET 8.2) + cover 10.7 cm³ — MJF quotes from volume, so quote THESE |
| ☐ | 1 roll | Kapton/polyimide tape ≥10mm | $2–5 | cell sandwich + nano underside |
| ☐ | 1 | SAC305 no-clean 0.5mm solder (e.g. SRA) + **NC-559-class flux pen** | ~$25 + ~$10 | ENIG pads, hand work |

## PCB order note (must be pasted into the fab order)

The outline is CONCAVE and the measured minimum copper-to-edge is
**0.292mm** — below the 0.3mm a V-cut wants, so the board MUST be
tab-routed. Put this in the order verbatim:

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

1. **EC11 = "G1" suffix** (with switch). The B2 clone is cheaper and wrong.
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

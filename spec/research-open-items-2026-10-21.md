# Hojicha44 — Research Memo on Open Production Decisions

Date: 2026-10-21. Scope: compliance, LiPo protection, module hold-down, pilot quantities, Choc v1 plate cutout.
Items marked **[UNVERIFIED]** could not be confirmed from a primary/authoritative source in this pass.

---

## 1. Compliance market

### 1a. Australia / New Zealand

**Two independent regimes, one mark.**

- **EESS (electrical safety)** — EESS Level 1 equipment may only be sold by a **Responsible Supplier registered on the EESS database**, marked with the RCM per AS/NZS 4417.1 & 4417.2, with evidence of compliance to standards held and producible within **10 business days**, retained **5 years**. Level 1 registration is **voluntary**; a CoS is voluntary. Source: https://www.eess.gov.au/registration/registration-in-scope-electrical-equipment/level-1/
- **ACMA (EMC / radiocommunications)** — Registration on the same database as an "ACMA-only" Responsible Supplier costs **nothing**; the Declaration (ACMA) does **not** require equipment registration. Source: https://www.eess.gov.au/responsible-supplier/responsible-supplier-declarations and https://www.eess.gov.au/rcm/acma-requirements-use-of-rcm/ ("There are no fees for ACMA registration").
- **Marking**: the RCM symbol is the only compliance label since 1 March 2016; label must be applied to a readily accessible surface, legible to the unaided eye; a QR code linking to a page displaying the RCM prominently is also acceptable. Source: https://www.acma.gov.au/step-5-label-your-product (updated 31 March 2025).
- **Before labelling with the RCM** the supplier must be registered on the national database (or hold a supplier code number). Source: Radiocommunications (Compliance Labelling – Devices) Notice 2014, s.11 — https://www.legislation.gov.au/F2014L01236/2017-10-27/2017-10-27/text/original/pdf
- **SDoC**: ACMA form **C02 "Supplier's declaration of conformity"** (May 2023) is the prescribed form for the Radiocommunications Equipment (General) Rules 2021 and the Radiocommunications Labelling (EMC) Notice 2017. It is retained by the supplier (not returned to ACMA). Real-world completed example: https://assets.ctfassets.net/isxmxtc67n72/1glIFkuSZ1yJ85mzMUIrLv/feca1bef683a6b33487fce1a51457c6b/BL-SZ2450638D01_RCM_SDOC.pdf ; form: https://www.acma.gov.au/sites/default/files/2026-07/form_c02_-_suppliers_declaration_of_conformity_may_2023.pdf
- **ACMA standards for BLE**: the general standard for short-range equipment is **Part 15 of Schedule 5 to the General Equipment Rules**; Bluetooth/wi-fi devices are explicitly in scope. Source: https://www.acma.gov.au/technical-standards
- **Penalties**: supplying a product with no label, or labelling before complying, can attract a fine of up to **500 penalty units**; failure to keep records up to 30 penalty units. Source: https://www.acma.gov.au/step-1-check-rules-follow
- **NZ**: the NZ RCM mark is the ACMA RCM (joint EESS/ACMA mark); NZ also runs the **Radiocommunications (Compliance) Notice 2013** and requires a **Supplier Code Number** for a "supplier" (e.g. a NZ importer) — this is a real per-country cost item, not a free extra. Source: https://www.eess.gov.au/rcm/acma-requirements-use-of-rcm/ and the Compliance Labelling Notice reference to the "New Zealand Compliance Notice".

**Cost / timeline for an AU/NZ SDoC** — **[UNVERIFIED]**: I did not find a primary published price list from an ACMA-accredited lab in this pass. Typical market quotes seen for a single-module SDoC package (BLE radio + EMC + safety evidence review + DoC + label artwork) are **AUD 600–1,500 per model**, **1–3 weeks**. *Treat as an estimate to be confirmed by quote from a lab such as EMC Bay / MiCOM Labs / TÜV Rheinland Australia.* At 5–20 units a bespoke lab SDoC is disproportionate; see recommendation.

### 1b. United States

- BLE digital devices fall under **FCC Part 15 Subpart C (§15.247)**. Two authorisation routes exist: **Certification** (granted to the equipment) and **Supplier's Declaration of Conformity (SDoC)** (§2.1077) for **Class B** unintentional radiators / devices where the responsible party is not an equipment authorisation holder.
- **The XIAO nRF52840 already holds a Single Modular Approval**: **FCC ID Z4T-XIAONRF52840**, Seeed Technology Co., Ltd., granted **2022-04-22** by Bay Area Compliance Laboratory (TCB), Equipment Class DTS, Part 15C, 2402–2480 MHz, 0.0032 W conducted. Source: https://fccid.io/Z4TXIAONRF52840 and the grant PDF: https://files.seeedstudio.com/Seeed_Certificate/documents_certificate/102010571-FCC.pdf
- Grant conditions relevant to you: module sold to OEM integrators and installed by the OEM; only antennas tested or of equal/lesser gain; **"Compliance of this device in all final host configurations is the responsibility of the Grantee"**; installation into a portable RF-exposure-category host requires a **Class II permissive change or new application**; end-users may not be provided module installation instructions.
- **Class A vs B**: the XIAO datasheet carries the standard **Class B** statement ("tested and found to comply with the limits for a Class B digital device, pursuant to Part 15"). Class B is what a consumer keyboard needs (residential environment). Source: https://files.seeedstudio.com/Bazaar/product_pdf/102010448.pdf
- **Labelling (§15.19 / §15.21)**: the finished keyboard must carry the FCC ID/Class B statement and the user manual must carry §15.21 "Caution: Any changes or modifications to this device…" If the keyboard uses a modular-approved radio, the typical label is the **FCC ID of the module plus the host's own Class B statement** — the host does **not** get its own FCC ID. **[UNVERIFIED]** I did not retrieve the exact 47 CFR text of §15.19 in this pass; treat the above as the standard interpretation.
- **Cost / timeline** — **[UNVERIFIED]**: no primary price list retrieved. Indicative: **SDoC test (Part 15C + Part 15B/Part 18, Class B) ≈ USD 1,500–3,000 per model, 2–3 weeks**; **certification ≈ USD 4,000–8,000, 4–8 weeks + TCB review**.

### 1c. European Union

- **RED 2014/53/EU** applies (Art. 3.1(a) safety, 3.1(b) EMC, 3.2 spectrum). Harmonised standards typically used for a BLE keyboard: **EN 300 328** (2.4 GHz wideband data), **EN 301 489-1 / -17** (EMC for radio equipment; -17 covers radio equipment using BW ≤ 1 MHz), **EN 62368-1** (safety of ICT equipment, replacing EN 60950-1), plus **EN IEC 61000-3-2** / **61000-3-3** if mains-connected (not applicable, battery), and **EN 50665:2017** (RF exposure assessment — Seeed uses this in its own RED DoCs, e.g. https://files.seeedstudio.com/Seeed_Certificate/documents_certificate/114992867-EUDOC.pdf).
- **RED cybersecurity delegated regulation**: Commission Delegated Regulation **(EU) 2022/30** activates Art. 3(3)(d),(e),(f) from **1 August 2025**. Source: EUR-Lex COM(2023)4823 — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML?uri=PI_COM%3AC(2023)4823 ; European Commission RED page — https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red_en
- Harmonised standards **EN 18031-1/-2/-3:2024** were cited in the OJ "with restrictions" (Jan 2025); self-declaration is only possible if the restrictions do not apply to your product, otherwise a **Notified Body** is required. Source: Spanish government application guide — https://digital.gob.es/content/dam/portal-mtdfp/avance-digital/telecomunicacion-e-infraestructuras-digitales/areas_interes/equipos_telecomunicacion/documents/Guia-aplicacion-EN-18031.pdf ; BSI RED guide — https://www.bsigroup.com/siteassets/pdf/en/products-and-services/gl-rs-pcert-lg-ict-dt-nsp-mp-digitaldomain-0025-red-guide-and-readiness.pdf
- **Repeal**: Commission Delegated Regulation **(EU) 2026/339** (16 Feb 2026, published OJ 29 Apr 2026) repeals 2022/30 **with effect from 11 December 2027**, aligning with the Cyber Resilience Act (EU) 2024/2847. Source: https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red_en
- **WEEE / RoHS**: WEEE Directive 2012/19/EU (producer registration per member state; in DE = Stiftung EAR) and **RoHS Directive 2011/65/EU** (plus (EU) 2015/863 for restricted substances). For a battery-powered device, RoHS applies to the whole EEE; WEEE applies if the product is placed on the market in the EU.
- **Cost / timeline** — **[UNVERIFIED]** no primary quote retrieved. Indicative RED self-declaration with a lab test report for a BLE product: **EUR 2,000–5,000, 3–5 weeks**; with Notified Body (only if EN 18031 restrictions bite) add EUR 5,000–15,000 and 4–8 weeks.

### 1d. Status of the Seeed XIAO nRF52840 / nice!nano specifically

| Regime | Status of the module | Evidence |
|---|---|---|
| FCC | **Single Modular Approval, FCC ID Z4T-XIAONRF52840** (2022-04-22). nRF52840 Plus/Sense Plus: **Z4T-XIAO52840P** (2025-04-27). | https://fccid.io/Z4TXIAONRF52840 ; https://fccid.io/Z4TXIAO52840P |
| CE / RED | Seeed publishes RED **EU Declarations of Conformity** for XIAO products (listing RED 2014/53/EU + RoHS 2011/65/EU and EN 50665:2017 etc.) and a "XIAO nRF52840 CE \| FCC \| MIC" document set. **[UNVERIFIED]** I did not open the XIAO-BLE-specific CE/DoC PDF in this pass to confirm the exact standards list and that the DoC covers XIAO BLE nRF52840. Treat as "CE/RED claimed by Seeed via its certificate portal", and request the file from Seeed before relying on it. | https://files.seeedstudio.com/Bazaar/product_pdf/102010448.pdf (links "XIAO nRF52840 CE \| FCC \| MIC"); https://files.seeedstudio.com/Seeed_Certificate/documents_certificate/114992867-EUDOC.pdf |
| Japan (TELEC/MIC) | Seeed holds MIC Radio Certificate of Type Approval 211-220207 for XIAO nRF52840 Sense. | https://files.seeedstudio.com/Seeed_Certificate/documents_certificate/102010469-TELEC.pdf |
| **RCM / EESS (AU/NZ)** | **No evidence found of an RCM/EESS certification or a supplier code number for the XIAO nRF52840.** **[UNVERIFIED — but likely "none"**: I searched Seeed's certificate index and found FCC/TELEC/CE files only, no RCM/ACMA/EESS file. | seeedstudio.com product page / certificate directory |
| **Bluetooth SIG** | The nRF52840 SoC is qualified by Nordic; the **XIAO module itself is not a SIG "Qualified Product"**. A finished keyboard is a Bluetooth "Product" that **must** be listed by its own member account before sale: "Your supplier or other member companies cannot qualify your products on your behalf" and "The Bluetooth Qualification Process must be completed before you take products to market". | https://www.bluetooth.com/develop-with-bluetooth/qualification-listing ; https://www.bluetooth.com/develop-with-bluetooth/qualify/ |

**Bluetooth SIG cost (primary source)**: Schedule of dues and fees effective 01 March 2026 — **Adopter membership $0/yr**, **Adopter full qualification fee $12,000** per design (first product), **Company Identifier (Adopter) $1,250**, Associate membership $11,250–52,500 with qualification at $6,000. Source: https://bluetooth.com/fee-schedule
*Interpretation for Hojicha44*: a keyboard built on a Nordic-based module can usually be listed by declaring the module's **QDID** as the design and doing an **End Product Listing (EPL)**-style listing, which is the cheap path (no new RF testing if the module is used as-is). But the **Adopter full qualification fee of $12,000** is the headline cost if you do not reuse an existing design declaration. Confirm with a Bluetooth Qualification Consultant before committing. **[UNVERIFIED]** the exact fee that applies to "declare an existing Nordic design" for an Adopter.

### 1e. What the builder inherits vs. still owes

**Inherited from the pre-approved module (FCC):** Part 15C radio compliance, conducted-power characterisation, antenna/PCB layout constraints (must not change antenna or layout), RF exposure assumptions. **Not inherited:** the host's own unintentional-emitter (Part 15.107/109) compliance, the host's Class A/B classification, the §15.19/§15.21 user-manual/label statements, host-level EMC immunity/ESD, safety of the host, and the grant note that "compliance in all final host configurations is the responsibility of the Grantee".

**Still owed by the builder (all markets):**
1. **Bluetooth SIG product listing** under your own member account, matching the marketed model number. Fees above.
2. **ACMA/EMC evidence + RCM + Responsible Supplier registration + C02 SDoC** for AU/NZ. No RCM exists for the module → you cannot just "inherit" AU compliance.
3. **EU RED**: a RED DoC for the finished keyboard, with EN 300 328 / EN 301 489-1/-17 / EN 62368-1 test evidence for the *host* configuration; plus 2022/30 Art.3(3)(d)–(f) cybersecurity assessment if you sell into the EU after 1 Aug 2025 (ZMK is open source and auditable; EN 18031-1 is the relevant part). WEEE + RoHS producer obligations.
4. **Host-level safety**: for a LiPo-powered device, the practical requirement is UN 38.3 / IEC 62133 evidence and cell-level protection (see §2).

### 1f. Recommendation for a 5–20 set AU/NZ-first builder

- **Do not buy a certification.** At 5–20 units, an AU lab SDoC package (est. AUD 600–1,500) costs more per unit than the keyboards.
- **Do the ACMA/EESS self-declaration path only**: register as an **ACMA-only Responsible Supplier on the EESS database (free)**, obtain a **Supplier Code Number** if needed, produce a **C02 SDoC**, keep your test evidence, and apply the **RCM** to each unit. Use the XIAO's **FCC test report / Seeed's EN 300 328 + EN 301 489 evidence** as the radio technical evidence where the host is electrically identical to the module — this is the "international documents" route ACMA explicitly contemplates ("you may be able to use international documents … to show your product complies", but "generally you will still have to label your product with the RCM"). Source: https://www.acma.gov.au/node/177
- **Get one cheap targeted test** (a few hundred AUD) from an Australian EMC lab for the *host* only if they say the module evidence is insufficient for your antenna position/PCB; the highest-risk item is **unintentional radiators from your host PCB and the USB-C charging path**, not the BLE radio.
- **Bluetooth SIG**: as an Adopter ($0 membership, $1,250 Company Identifier), list the keyboard reusing the Nordic/seeed design declaration. Budget **USD 1,250–12,000 depending on whether the fee applies**; confirm before printing product. Note: SIG enforcement is real ("products which appear to have not completed the Bluetooth Qualification Process may be impounded by customs' authorities").
- **Sequence**: build the pilot → get a lab quote → decide AU-only (self-declare) vs AU+US+EU (pay for module-inclusive host testing). Retrofitting compliance to a shipped design is more expensive than testing the pilot.

---

## 2. LiPo protection (301230, 3.7 V, 110 mAh, PCM'd)

### 2a. What the PCM actually protects

A PCM is a small PCB with a protection IC (typically **DW01A** or **DW01**) plus two MOSFETs, one N-channel and one P-channel. The DW01A datasheet (PJSEMI) specifies:

| Function | DW01A typical | Datasheet |
|---|---|---|
| Overcharge protection voltage | **4.28 V** (4.230–4.330 V, ±50 mV) | http://www.pingjingsemi.com/UploadFile/pdf/DW01A.pdf |
| Overcharge release | 4.08 V | same |
| Over-discharge protection | **2.40 V** (2.30–2.50 V) | same |
| Over-discharge release | 3.00 V | same |
| Discharge over-current threshold | 160 mV across the sense element (±20 mV) | same |
| Short-circuit protection threshold | 1.00 V (0.70–1.30 V), 300 µs delay | same |
| Charge over-current / short | also detected (charger detection −1.2…−0.2 V) | same |
| Quiescent current | 1.5 µA normal, 0.7 µA in over-discharge | same |

(DW01 datasheet variant: VOCP 4.30 V, VODP 2.40 V, VOIP 150 mV, VSIP 1.0 V — https://datasheet.lcsc.com/datasheet/pdf/00b79dd32674301abc7b805eecca8cc7.pdf)

**So the PCM covers: overcharge, over-discharge, over-current, and short-circuit.** It does **not** cover: reverse polarity, reverse current (cell plugged in backwards into the host), thermal runaway from a mechanical puncture, or a poor-quality charger.

Note also that a **PCM'd cell is typically protected against over-charge only to 4.2–4.28 V**, which is compatible with the nice!nano/XIAO onboard charger (BQ25101-based, charging to 4.2 V per the XIAO docs). **[UNVERIFIED]** I did not confirm the XIAO's charge termination voltage from the BQ25101 datasheet in this pass — verify before relying on it.

### 2b. Does a PCM'd cell still need more protection?

| Item | Needed? | Reason |
|---|---|---|
| **(a) Reverse-polarity protection on the PCB** | **Yes, if there is any chance the pack can be inserted backwards.** A reversed LiPo into a charger is a fire risk and the PCM does not prevent it. | PCM only sees current direction relative to *its own* terminals; a reversed pack+ that reaches the host's RAW rail is not covered by the cell's PCM. If the pack uses a keyed JST-PH 2.0 pigtail, reversal requires deliberate mis-assembly of the connector, but a soldered pack does not. |
| **(b) DW01A + 8205A on the PCB** | **No, not if the pack already has a PCM, and no if the charger is a proper CC/CV charger.** | The XIAO's charger is a CC/CV Li-ion charger with its own regulation; a second protection IC on the host would duplicate the cell's function and add a second failure mode. It *would* add host-side protection if the pack were bare (no PCM). |
| **(c) A fuse** | **Optional but cheap insurance.** The PCM's over-current threshold (160 mV across a ~0.1–0.3 Ω sense element ≈ 0.5–1.5 A, and the 1.0 V short threshold ≈ several amps) is far above the ~200 mA the XIAO can draw. A **polyfuse (PPTC, e.g. 0.5–1 A hold)** in series with the pack+ prevents a PCB short or a crushed battery from sourcing a large current into the module/charger. | also protects the PCB trace and the switch |

**Slide switch placement**: the switch should be in the **+ (pack+) leg before the module RAW rail**, as you have it, so that "off" disconnects the battery entirely. One subtlety: with a **PCM'd cell, over-discharge protection is what saves you** if the module is left on and the cell is flattened — the PCM disconnects at ~2.4 V, but that is **below the useful end of the LiPo curve**; the cell will be permanently "latched off" and need a charger to recover (DW01A supports 0 V charge recovery from 1.2 V, per datasheet). This argues for a **switch that is genuinely reachable and not lost in a bag**, and for **not** relying on firmware-only power gating.

### 2c. Transport / safety documentation for shipping the cells

- **UN 38.3** test summary (Manual of Tests and Criteria Part III, sub-section 38.3, §38.3.5) must be **made available by manufacturers and distributors**; since 1 Jan 2022 this applies to cells manufactured after 1 Jan 2008. Source: PHMSA Lithium Battery Guide — https://www.phmsa.dot.gov/sites/phmsa.dot.gov/files/2023-07/Lithium%20Battery%20Guide.pdf ; UN/SCETDG/57/INF.39 — https://www.unece.org/fileadmin/DAM/trans/doc/2020/dgac10c3/UN-SCETDG-57-INF39.e.pdf ; IATA guidance — https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-shipping-guidelines.pdf
- **IATA/air**: a 301230 110 mAh cell = **3.7 V × 0.110 Ah = 0.407 Wh** — far below the **20 Wh/cell** limit, so it is a **Section II / "small" lithium ion cell**: UN 3480, PI 965 Section II (packed with equipment) or PI 967 Section II (contained in equipment). Section II requires the **lithium battery mark** on the package, no Shipper's Declaration for PI 967 Section II (ELI), and quantity limits (e.g. ≤2 batteries or ≤4 cells per package for PI 967 Section II; Australia Post caps at **2 batteries or 4 cells per package**).
- **Australia Post / AU-specific**: lithium ion up to **20 Wh per cell** and **100 Wh per battery**; international/air requires the batteries to be **installed in the device**; standalone cells need the **"Australia Post Road Transport Only"** label and are domestic-only. Source: https://auspost.com.au/content/dam/auspost_corp/media/documents/lithium-batteries-quick-reference-guide.pdf and https://auspost.com.au/business/shipping/shipping-guidelines/dangerous-prohibited-items ; Dangerous Goods Guide (July 2026) https://auspost.com.au/content/dam/auspost_corp/media/documents/dangerous-goods-guide.pdf — which also states "All cells and batteries must be tested in accordance with the UN Manual of Tests and Criteria Part III, Subsection 38.3 (DGR 3.9.2.6)".
- **IEC 62133 / UL 2054**: IEC 62133-2 is the cell safety standard; UL 2054 is the UL equivalent for lithium cells. Neither is a *legal* shipping requirement (UN 38.3 is), but buyers/insurers often ask, and **AU/NZ electrical safety of the end product** references the pack's evidence. **[UNVERIFIED]** whether EESS treats a LiPo pack as "in scope electrical equipment" for the keyboard — EESS scope normally excludes ELV/battery-only products; confirm with EESS.
- **Practical**: choose a cell **with a documented UN 38.3 test summary and SDS**. KEEBD's 301230 110 mAh listing explicitly states "**Built-in protection circuit (PCM) to prevent over charging/discharging**" — https://keebd.com/en-us/products/301230-3-7v-110mah-lipo-battery (A$6.00 AUD; also 351230 120 mAh A$7.00 — https://keebd.com/collections/batteries).

### 2d. Recommendation

**Use a PCM'd cell, keep the PCB simple, and add a fuse.** Specifically:

- **Recommended (lowest risk, 0 extra PCB parts):** PCM'd cell + **slide switch in the pack+ leg** + **polyfuse in series with pack+**. The PCM already covers overcharge/over-discharge/over-current/short *of the cell*; the polyfuse covers the *host* fault case the PCM cannot see (PCB short, crushed pack, mis-wired host). Failure mode prevented: a hot trace / burnt PCB / damaged charger MOSFET instead of a runaway cell.
- **Optional if you solder the pack with a keyed connector and control assembly:** add a **P-channel MOSFET ideal-diode reverse-polarity** stage (source-drain with gate to ground via the module's GND, ~4 parts: P-MOSFET + gate resistor + optional zener). Failure mode prevented: **reversed pack+ driving the charger and RAW rail backwards**, which the cell PCM will not catch and which can destroy the XIAO's charger IC. Cost: ~US$0.10 and 3–4 parts.
- **Do not add a DW01A+8205A to the PCB** if the cell has a PCM: it duplicates protection, costs ~US$0.20 and 3 parts, adds its own tolerances, and does not protect against the reverse-polarity case either (a DW01A is not a reverse-blocking device).
- If you must ship **bare cells** (no PCM) then a DW01A+8205A on the PCB becomes mandatory, but then the pack's protection depends on the user's wiring — prefer a PCM'd pack.

---

## 3. Module hold-down (nice!nano / XIAO nRF52840)

### 3a. Size facts (correcting the brief)

- **Seeed XIAO nRF52840 is 21.0 × 17.8 mm**, single-sided SMD with castellated stamp holes, mid-mount USB-C. Source: https://files.seeedstudio.com/Bazaar/product_pdf/102010448.pdf and https://wiki.seeedstudio.com/XIAO_BLE/ — "Ultra Small Size: 21 x 17.8mm"; the XIAO family standard is 21×17.8 mm (https://www.seeedstudio.com/blog/xiao-new-page).
- **nice!nano** is a Pro Micro-form-factor board built on the same nRF52840 + XIAO footprint, **3.2 mm thick** with a mid-mount USB-C. Source: https://nicekeyboards.com/docs/nice-nano/ and https://nicekeyboards.com/nice-nano ("Mid mount USB-C port making the board a 3.2mm total thickness"). The "18 × 18 mm" in the brief is the **Pro Micro** footprint, not the XIAO/nice!nano outline — **design the bay to 21 × 17.8 mm** (plus clearance) for a XIAO, or use the actual nice!nano STEP/footprint file if you use nice!nano. **[UNVERIFIED]** I did not retrieve a published nice!nano mechanical drawing with hole positions — download the STEP from Nice Keyboards before cutting the pocket.

### 3b. Real-world retention practice

- **The socket is the standard retention mechanism.** Nice Keyboards' own docs are emphatic: "It's highly recommended that you socket your nice!nano. It offers ease of access to the battery and makes debugging your keyboard so much easier." and the socketed build guide uses **MillMax spring-pin headers** with the module soldered to the pins. Sources: https://nicekeyboards.com/docs/nice-nano/ ; https://nicekeyboards.com/docs/nice-nano/getting-started
  - Consequence: with a socket, the module's solder joints carry all mechanical load; the PCB solder pads must be the load path, and the module itself is not fixed to the case at all — it floats in the socket. The **case holds the PCB**, not the module.
  - Nice also notes: "Be wary of flipped nice!nanos with pins and other parts poking out underneath (you don't want to puncture your battery!)" and "In most cases the battery should fit underneath the socketed nice!nano" — i.e. the standard geometry is: socketed module on top, 301230 cell underneath.
- **socket vs solder**: nice!nano's standard practice is **soldering the module to a female socket** (headers) or **direct-solder on the PCB**; the "socket alone" (spring headers) is what is recommended precisely because it avoids the module being the hard point for USB plug force.
- **Case examples** (XIAO/nice!nano in a printed case): the Seeed 3D-Printing Case Studies pack shows snap-fit XIAO cases, XIAO+battery+slide-switch enclosures (https://files.seeedstudio.com/wiki/XIAO/3D-Printing-Case-Studies.pdf ; https://www.printables.com/model/1782472-xiao-nrf52840-with-battery-enclosure/). For split keyboards: **Corne, Lily58, Sofle, osprey and keyball** all mount the controller on the PCB (socketed or soldered) and the *case* retains the PCB via standoffs/screws — **the module is never independently retained in the case**. osprey: "The PCB is 'floating' inside the case and the switches are held in-place by a 1.2 mm FR4 plate" — https://github.com/ebastler/osprey
- **Adhesive**: 3M/VHB tape on a bare (unsocketed) module is used in hobby builds but **I found no primary documentation recommending it** — flag as community practice, and note it blocks the "remove module to flash/replace battery" workflow.

### 3c. Published bay/clearance dimensions

- **XIAO = 21 × 17.8 mm** (datasheet). **No published "bay" dimension for a 21 × 17.8 mm XIAO module in a keyboard case was found** in this pass. **[UNVERIFIED]**
- Engineering recommendation: pocket **21.4 × 18.2 mm** (0.2 mm per side clearance) if the module sits in a printed pocket; **height 3.5–3.8 mm** for the nice!nano (3.2 mm board + 0.3 mm). Add **0.2 mm** extra if the printed pocket must be a slide fit.
- MJF PA12 dimensional tolerance: SLS/MJF parts are typically accurate to about **±0.15–0.25 mm** on external features, with slight dimensional variation from thermal/laser effects — **[UNVERIFIED, general knowledge]**; therefore **do not design a press/tight fit**. Design a **0.2–0.3 mm clearance slip fit with a small retention lip or a soft pad**, never an interference fit.

### 3d. USB strain relief and the levering risk

- The XIAO/nice!nano uses a **mid-mount USB-C receptacle** (cable plugs in from the board edge, perpendicular to the PCB plane).
- **Failure mode**: every time the cable is unplugged, the plug body applies a moment to the connector and, through it, to the PCB and to whatever is holding the PCB. If the module is retained **only** by adhesive, or if the PCB is retained only at the connector end, an unplug will lever the board out of its bay or crack the USB-C pads. If the module is **socketed**, the moment goes into the PCB solder pads (much stronger) rather than the module.
- **Mitigations** (increasing robustness):
  1. **Retain the PCB, not the module** — the module is held by the socket; the PCB is screwed to 4 standoffs / heat-set inserts. (Standard practice, osprey/Corne/Lily58.)
  2. **Do not use the USB plug as a structural element.** Never design a bay whose only restraint is the module's own weight or the connector.
  3. **Printed USB-C strain-relief boot**: an overhanging printed lip/hood around the connector opening that the plug's overmould bears against, so the pull load is taken by the case, not the connector. This is standard practice in printed enclosures (Seeed's own XIAO cases use a cover with an opening for the USB-C connector — https://files.seeedstudio.com/wiki/XIAO/3D-Printing-Case-Studies.pdf).
  4. **Shorten the cable** / use a right-angle cable if the design allows, so the plug is not a long lever.
- **Weight**: XIAO nRF52840 board weight is **~4 g** (unverified) — the concern is not the module's weight but that it is the **only thing holding the USB connector's moment arm**, and that any case flex (nylon is compliant) lets the PCB bow.

### 3e. Recommendation for a MJF PA12 case

**Socket the module on the PCB (MillMax or equivalent spring-pin headers, 2×7), retain the PCB to the case with 4 screws into heat-set inserts or self-tapping standoffs, and give the module a printed pocket with 0.2–0.3 mm clearance that only *locates* it (no press fit, no glue).** Add a printed USB-C strain-relief hood.
- Rationale: nylon PA12 is slightly compliant and dimensionally variable; a press fit will either rattle or split. A screw + socket path carries plug forces into the PCB's solder joints and the case's insert threads, which are the strongest elements in the assembly.
- If you want the module removable for flashing/battery access, the socket gives you that for free, and the pocket can be a simple two-wall pocket.
- **Avoid**: 3M tape as the only retention (blocks service, creeps under warmth, and the module can still lever the PCB), and any design where the USB-C plug bears on the module.

---

## 4. Pilot batch quantity and unit costs

### 4a. Component costs (with source)

| Item | MOQ / minimum | Unit cost | Source |
|---|---|---|---|
| **FR4 PCB, 1.6 mm, 2-layer, ENIG** | JLCPCB sells from **5 pcs** | "From **$2.00 / 5 pcs**" for FR-4 base; ENIG adds a per-board surcharge **[UNVERIFIED — exact ENIG adder needs a live quote]** | https://jlcpcb.com/ ; capabilities: ENIG is offered for 2L 1.6 mm (https://jlcpcb.com/capabilities/pcb-assembly-capabilities) |
| **PCBA (assembly)** | 5 pcs boards + BOM/CPL | setup **$8.00–$8.18**, stencil $1.50, **$0.0016–0.0017 per solder joint** | https://jlcpcb.com/help/article/pcb-assembly-price ; https://jlcpcb.com/pcb-assembly |
| **Plate, 1.2 mm PC** | Use a **1.2 mm FR4/PCB-as-plate** (cheap, dimensionally stable) rather than laser/waterjet PC | ≈ the price of 2-layer PCBs; Sofle Choc ships its top plate as a **PCB** (Gerbers) | https://github.com/josefadamcik/SofleKeyboard/blob/master/docs/build_guide_choc.md ; Sofle Choc V2 fork BOM estimate "5x top plates ~$5–10" — https://github.com/alxyzc/SofleKeyboard-ChocV2/blob/master/CHOC_V2_README.md |
| **MJF PA12 case** | **Formlabs does not publish a service MOQ** **[UNVERIFIED]**; third-party MJF bureaus explicitly advertise **"No minimum order quantity … even just one (1) unit"** (Simple Machining: https://www.simplemachining.com/mjf-3d-printing-service) | Nylon 12 powder **$45–100/kg** (Formlabs); MJF has a ~**20% powder refresh rate** and ~8–10% volume packing density; a keyboard half-case (~20–30 g) ⇒ roughly **US$1.5–4 per half in powder + labour**, and more from a bureau | https://formlabs.com/global/white-papers/calculating-sls-cost-per-part/ ; https://formlabs.com/uk/compare/formlabs-fuse-1-30w-vs-hp-multi-jet-fusion-1200/ ; https://www.cadimensions.com/... (MJF packing density/refresh) |
| **Kailh Choc v1 (PG1350) switches** | Sold in **35-packs** | **¥2,695 / 35 = ¥77 each** (¥115 single) — Yushakobo (Choc v2 listing; Choc v1 sold similarly) | https://shop.yushakobo.jp/en/products/kailh-choc-v2 |
| **301230 110 mAh LiPo** | 10 pcs packs | **C$21.99 / 10 = C$2.20** (AliExpress); **US$1.54** at MOQ 10 (B2B listings); **A$6.00** (KEEBD, AU, tax incl., PCM'd) | https://www.aliexpress.com/item/1005008947472882.html ; https://keebd.com/en-us/products/301230-3-7v-110mah-lipo-battery |
| **N52 4 × 2 mm magnets** | MOQ 100 | **$0.01–0.08** each at MOQ 100; made-in-china **$0.005–0.10** MOQ 100 | https://www.accio.com/plp/n52-neodymium-magnet (Nanjing Huajin) ; https://nbycmagnet.en.made-in-china.com/... |
| **PG1350 hotswap socket (CPG135001S30)** | Kailh pack = **2,000/reel, 20,000/carton**; AliExpress retail usually by the strip/100 | **[UNVERIFIED — no per-piece price retrieved]**; budget **US$0.15–0.40 each** | https://m.kailhswitch.com/mechanical-keyboard-switches/box-switches/choc-type-hot-swap-socket.html ; https://www.aliexpress.com/wholesale/kailh-hotswap-socket-choc.html |
| **Diodes 1N4148W** | 100 (bag of 200) | **$0.0092** each @100, $0.0074 @1000 (SOD-123) | https://www.ebee.com/product-detail/goodwork-1n4148w_324694.html |

### 4b. Recommended pilot quantity

**Build 5 half-pairs = 10 halves = 5 complete keyboards' worth of halves.** Rationale: each half must be tested for switch retention, plate fit, case fit and battery life, and you need at least 2 complete sets to test the wireless link (left↔right pairing) and to test battery life on one unit while the other is being reworked. 5 pairs also gives you a spare if one half is scrap.

**Buy quantities (per 10 halves) + spares:**

| Part | Need (10 halves) | Buy | Why |
|---|---|---|---|
| PCBs | 10 (+ assembly spares) | **20** | JLCPCB min 5; order 10 + 10 spare. PCBs are cheap; a bad PCB is a dead half. |
| PC plates (1.2 mm) | 10 | **20** | Plate cutout is the #1 thing being validated — you will reprint. |
| Case halves (MJF PA12) | 10 | **12–15** | Cheapest to reprint; allow for fit iteration. |
| Switches (PG1350) | ~40–45/half → ~430 | **490 (14 × 35-packs)** | 10% + a full pack of spares. Choc v1 clip damage during plate assembly is the top mechanical failure. |
| Hotswap sockets (CPG135001S30) | ~430 | **450–500** | Soldering rejects; sockets are the #1 solder-error part. |
| Diodes 1N4148 | ~430 | **500** | $0.01 each; buy 500. |
| LiPo 301230 | 10 | **12–14** | Cheap; also lets you test charging behaviour and keep one cell as a known-good reference. |
| N52 4×2 magnets | ~8–12/half → ~100 | **150** | Small, cheap, and easy to misplace. |
| nice!nano / XIAO | 10 | **12** | Includes 2 spares for the return/RMA path. |
| Polyfuses (PPTC ~1 A) | 10 | **20** | Add to BOM per §2. |
| MillMax headers (if socketing) | 10 sets | **12 sets** | |

**Total per-half BOM (excluding labour, compliance and shipping) is roughly US$35–70 per half** at these quantities, dominated by the module (US$9.90 XIAO, https://files.seeedstudio.com/Bazaar/product_pdf/102010448.pdf), switches (~$0.50 each ≈ $22/half), and MJF case (~$2–4).

---

## 5. Choc v1 plate cutout, thickness and gap

### 5a. Cutout size

| Source | Cutout for Choc v1 (CPG1350) | Note |
|---|---|---|
| ai03 Plate Generator | **14.0 × 14.0 mm** — "Identical cutout to basic Cherry MX switches" | https://kbplate.ai03.com/ |
| KLE-NG Plate Generator | **14.0 × 14.0 mm** (CPG1350), vs Mini Choc CPG1232 at 13.7 × 12.7 | https://editor.keyboard-tools.xyz/docs/development/plate-generator.html |
| SofleKeyboard-ChocV2 README (community) | Choc **v1: 13.8 × 13.8 mm**, Choc v2: 14 × 14 | https://github.com/alxyzc/SofleKeyboard-ChocV2/blob/master/CHOC_V2_README.md |
| swillkb Plate & Case Builder docs | a **14.0 mm nominal** cutout with **0.2 mm kerf** yields a **13.8 mm as-built** hole | http://builder-docs.swillkb.com/features |
| osprey | uses a **1.2 mm FR4 plate**; **exact cutout dimension not verified** (repo README did not state it) — **[UNVERIFIED]** | https://github.com/ebastler/osprey |

**Reconciliation:** 14.0 mm is the *nominal/design* cutout; depending on process (laser/waterjet/PCB routing) the as-built hole lands at **13.8–14.2 mm**. **Target: design 14.0 mm nominal**, verify the as-built hole after the first plate is cut (measure with calipers) before committing to a batch. Do **not** design 15.0 mm.

### 5b. Plate thickness

- Keebio (authoritative for Choc): "If you're designing your own switch plate for Choc switches, your plate **must be 1.2 mm thick** so that the Choc stabilizers can clip into the plate properly. The stabilizers will not clip into thicker plates properly." — https://docs.keeb.io/choc-stabs
- Kailh's own switch drawing indicates the Choc switch "bump"/retention geometry is **1.3 mm**; community plate at 1.3 mm (https://imgur.com/a/Rv9xgRU). Source thread: https://github.com/josefadamcik/SofleKeyboard/issues/136
- **Sofle issue #136 (brianlow, the Sofle Choc designer)**: he manufactured both — "The switches snap into the **1.2 mm** plates but don't [snap] into the **1.6 mm** [plates]. 1.6 mm still works – the switches are held in firmly by friction … but they are easier to remove from a 1.6 mm plate than a 1.2 mm because **the lower catch doesn't engage**." — https://github.com/josefadamcik/SofleKeyboard/issues/136
- Other builders' experience in the same thread: lyteDev — "I ordered 1.2 mm plates and they worked great."
- **osprey uses a 1.2 mm FR4 plate** — https://github.com/ebastler/osprey

**Conclusion: use a 1.2 mm plate.** 1.3 mm works; 1.6 mm only gives friction retention (the lower catch does not engage), which is exactly the failure mode you do not want in a shipping product.

### 5c. PCB-to-plate gap and PCB thickness

- Kailh's own "Precautions" for Choc (quoted in the Sofle thread): "**Please use the thickness 1.6 mm PCB**" — i.e. the PCB should be 1.6 mm, and with a 1.2 mm plate the resulting **PCB-top-to-plate-underside gap is 1.3 mm** (matching the switch's 1.3 mm retention geometry). This is the "space between the PCB and the Switch Plate (standard thickness) is 1.0 mm" cited for a 1.3 mm plate — https://www.printables.com/model/262231-kalih-choc-v1-plate-support-fork
- The Choc hotswap socket's plastic "bump" is **1.25 mm** tall, so a **1.2 mm PCB would let the bump protrude 0.05 mm and stop the keycaps sitting flat** (johnnytshi in the Sofle thread). **Therefore: 1.6 mm PCB + 1.2 mm plate.**
- Sofle Choc build guide agrees on 1.6 mm PCB: "The PCB should be 1.6mm thick though 1.2mm may be better" (wording is about plate/PCB thickness in the guide) — https://github.com/josefadamcik/SofleKeyboard/blob/master/docs/build_guide_choc.md
- Keebio PCB-as-plate thickness options include a "3mm Plate" and a "1.2 mm" option in the plate generator; the generator's Choc V1 cutout is the 14 mm MX-equivalent. — https://plate.keeb.io/

**Recommended geometry for Hojicha44:** PCB **1.6 mm**, plate **1.2 mm**, PCB-top-to-plate-underside gap **1.3 mm** (i.e. standoffs/case features set 1.3 mm), switch cutout **14.0 mm nominal**.

### 5d. Failure mode of a too-large cutout (e.g. 15.0 mm with a 1.2 mm plate)

Choc v1 retains itself in the plate via **two small flexible plastic clips on the top housing** that snap into the plate cutout. The effective retention width is therefore set by the clip engagement, not by the 15 × 15 mm switch body (Kailh's Choc body is 15 × 15 mm overall, https://m.kailhswitch.com/info/kailh-choc-switch-41232795.html).

With a **15.0 mm** cutout (≈1.0 mm of slack per side, vs ≈0.1 mm at the nominal 14.0 mm):
- The **clips cannot reach the plate edge** → they never engage → **no positive retention at all**. The switch is only held by gravity/friction and by the keycap.
- Symptoms: **no audible click** when pressing the switch into the plate; the switch **rises out of the plate** when you press it (or rocks); **visible gap/wobble** around the switch; the switch can be **knocked out sideways or lifted** during transport or if the case is inverted; keycap **rattle**; the switch can **lean and bind** at the end of travel, and on a hotswap board the **socket pins can be bent** by the tilted switch.
- With a 1.2 mm plate specifically, the plate's own stiffness is the only thing holding the switch down, so an oversize cutout removes essentially all retention.
- **Mechanistically the same failure as the "too thick plate" case documented in Sofle issue #136**: there, the 1.6 mm plate prevented the lower catch from engaging, leaving friction-only retention and switches that came out when pulled. A too-large cutout is the mirror image — the plate is thin enough but the hole is too big for the clips to hook.

**[UNVERIFIED]** I could not obtain the Kailh mechanical drawing with the clip geometry/engagement dimension, so I cannot quote the maximum allowable cutout tolerance from the manufacturer. The reasoning above is mechanical analysis of the documented plate/clip behaviour in Sofle #136 combined with the Choc body dimension; **validate empirically on the pilot plates**: cut one test plate at 13.8, 14.0, 14.2 and 15.0 mm, press switches in, and measure retention force / lift-out. This is a 20-minute test that de-risks the single highest-volume mechanical decision.

---

## Open items I could not close in this pass

1. Published per-model prices and lead times from an **ACMA-accredited test lab** for an SDoC, and whether Seeed's module reports can be used as-is for the host.
2. Whether **EESS treats the LiPo pack / keyboard** as in-scope electrical equipment (probably out of scope as ELV, unconfirmed).
3. The exact **Bluetooth SIG fee path** for an Adopter listing an existing Nordic/seeed design (vs. the USD 12,000 Adopter full qualification fee).
4. **Seeed's XIAO nRF52840 RED/DoC document** and the exact standards it cites (CE claimed, document not opened).
5. **nice!nano mechanical drawing / STEP** and its exact hole pattern; XIAO hole positions.
6. **Formlabs (or bureau) minimum order / minimum spend** for SLS PA12 parts.
7. **Choc v1 clip geometry from Kailh** — the maximum cutout tolerance.
8. Per-piece **PG1350 hotswap socket price** and the XIAO/nice!nano **charge termination voltage** (BQ25101).

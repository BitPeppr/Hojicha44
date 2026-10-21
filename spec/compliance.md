# Compliance — Hojicha44 (status: DECIDED for the pilot market, per-market paths recorded)

Date: 2026-10-21. Source: research memo `spec/research-open-items-2026-10-21.md` + the
primary regulator/vendor sources cited there. Numbers marked
**[UNVERIFIED]** were not confirmed from a primary source in that pass.

The keyboard is a battery-powered Bluetooth LE (2.4 GHz) device: one
nice!nano / Seeed XIAO nRF52840 per half, USB-C, a 301230 LiPo per half.
That makes it a **short-range (SRD) intentional radiator** in every market
we might ship to.

---

## 1. DECISION — pilot market

**The pilot batch is for Australia / New Zealand. The compliance path is
the RCM via an ACMA "Responsible Supplier" self-declaration, NOT a
bespoke certification.**

Why:

- At 5–20 units, a lab SDoC (AU ~AUD 600–1,500, 1–3 weeks) is
  disproportionate, and a full certification (US ~USD 4,000–8,000, EU
  with a Notified Body EUR 5,000–15,000) is absurd at this volume.
- The radio module already carries the hard radio approvals; what the
  builder owes is the HOST's EMC/label/declaration, and that is exactly
  what a self-declaration covers.
- Nothing about the PCB or the case has to change for the US or the EU
  later — the same board ships; only the label, the manual statement and
  the paperwork differ. (Recorded so the decision is not revisited
  later: **do not print a market-specific label on the case** until the
  market is fixed; the label is a separate sticker.)

## 2. Australia / New Zealand — the path

Two independent regimes, one mark:

| Regime | What it covers | What we owe |
|---|---|---|
| **ACMA** (EMC + radiocommunications) | Part 15 of Schedule 5 to the Radiocommunications (General) Rules 2021; BLE/wifi SRDs are explicitly in scope | Register as an **"ACMA-only" Responsible Supplier** on the EESS database — **free**, no fees (eess.gov.au). Complete **ACMA form C02 "Supplier's declaration of conformity"** (May 2023). Apply the **RCM** mark (AS/NZS 4417.1). Keep the evidence and be able to produce it within **10 business days**; retain **5 years**. |
| **EESS (electrical safety)** | Level 1 equipment | Level 1 registration and a CoS are **voluntary**; skip at pilot volume. |
| **NZ** | NZ has its own Radiocommunications (Compliance) Notice 2013 and wants a **Supplier Code Number** for a supplier/importer | Same RCM mark; get an SCN if the units are imported into NZ. |

- The RCM label must be on a readily accessible surface, legible to the
  unaided eye, or a QR code linking to a page showing the RCM
  prominently (acma.gov.au "label your product").
- Penalties: supplying with no label, or labelling before complying,
  can attract up to **500 penalty units**.
- **Bluetooth SIG** is the one unavoidable cost item: a finished
  keyboard is a Bluetooth "Product" and must be listed under the
  builder's own account before sale ("your supplier cannot qualify your
  products on you behalf"). Adopter membership is $0/yr; the headline
  **Adopter full qualification fee is USD 12,000** per design, and the
  **Company Identifier is USD 1,250** (bluetooth.com/fee-schedule,
  effective 2026-03-01). A keyboard built on a Nordic-based module can
  usually be listed by declaring the module's QDID as the design (an
  End-Product-Listing style path) — **confirm that reuse path with a
  Bluetooth qualification consultant BEFORE the board order**; it
  changes the unit economics of the whole kit. **[UNVERIFIED]: the
  exact fee that applies to "declare an existing Nordic design".**

## 3. United States — the path (if/when units go to the US)

- BLE digital devices: **FCC Part 15 Subpart C (§15.247)**. Two
  routes: Certification, or a **Supplier's Declaration of Conformity
  (§2.1077)** for Class B unintentional radiators.
- The module is already a **Single Modular Approval: FCC ID
  Z4T-XIAONRF52840** (Seeed, granted 2022-04-22, Part 15C, 2402–2480
  MHz, 0.0032 W conducted).
- The grant explicitly says **"compliance of this device in all final
  host configurations is the responsibility of the Grantee"** — the
  host's own EMC/immunity/ESD and its labelling are NOT inherited.
- Labelling: the finished keyboard carries the **module's FCC ID plus
  the host's own Class B statement** (§15.19); the user manual carries
  the §15.21 modification statement. The host does **not** get its own
  FCC ID. **[UNVERIFIED]: the exact §15.19 text was not retrieved in
  the research pass — treat the label wording above as the standard
  interpretation and confirm with the test lab.**
- Indicative cost: SDoC test ≈ USD 1,500–3,000 per model, 2–3 weeks;
  certification ≈ USD 4,000–8,000, 4–8 weeks. **[UNVERIFIED: no
  primary price list retrieved.]**

## 4. European Union — the path (if/when units go to the EU)

- **RED 2014/53/EU**: Art. 3.1(a) safety, 3.1(b) EMC, 3.2 spectrum.
  Harmonised standards typically used: **EN 300 328** (2.4 GHz
  wideband data), **EN 301 489-1 / -17** (EMC), **EN 62368-1** (safety
  of ICT equipment), **EN 50665:2017** (RF exposure — Seeed cites it
  in its own RED DoCs).
- **Cybersecurity**: Delegated Regulation **(EU) 2022/30** activates
  Art. 3(3)(d)-(f) from **1 August 2025**. The harmonised standards
  **EN 18031-1/-2/-3:2024** were cited in the OJ *with restrictions*,
  so self-declaration is only possible if those restrictions do not
  apply — otherwise a **Notified Body** is required. Delegated
  Regulation **(EU) 2026/339** repeals 2022/30 with effect from
  **11 December 2027**, aligning with the Cyber Resilience Act
  (EU) 2024/2847.
- **WEEE** (producer registration per member state) and **RoHS
  2011/65/EU** apply to the finished product.
- Seeed publishes RED EU Declarations of Conformity for XIAO products.
  **[UNVERIFIED: the XIAO-BLE-specific DoC was not opened — request
  the file from Seeed before relying on it.]**
- Indicative cost: RED self-declaration with a lab report EUR
  2,000–5,000, 3–5 weeks; with a Notified Body add EUR 5,000–15,000,
  4–8 weeks. **[UNVERIFIED: no primary quote retrieved.]**

## 5. What is inherited vs. what is owed (all markets)

**Inherited from the module:** the radio conformity (Part 15C / RED
radio), the conducted-power characterisation, the antenna/layout
constraints (do not change the antenna or the keepout), the RF-exposure
assumptions.

**Owed by the builder:** the host's own unintentional-emitter
compliance and its Class A/B classification, the §15.19/§15.21 (or
equivalent) label and manual statements, host-level EMC immunity/ESD,
electrical safety of the host, and the Bluetooth SIG listing.

## 6. Action list before the pilot ships

1. Register as an ACMA-only Responsible Supplier (free) — the RCM is
   illegal to apply before this.
2. Get the module's evidence: XIAO nRF52840 RED DoC, the datasheet's
   Class B statement, the FCC grant.
3. Confirm with a Bluetooth qualification consultant whether the
   Nordic-design reuse path applies (the USD 12,000 vs USD 1,250
   question) — **this gates the whole kit's economics**.
4. Order an AU SDoC package from an ACMA-accredited lab (EMC Bay /
   MiCOM / TÜV Rheinland Australia) — quote first; budget AUD 600–1,500
   and 1–3 weeks. **[UNVERIFIED price — confirm by quote.]**
5. Produce the RCM label artwork as a **sticker**, not as case
   printing, until the market is fixed.
6. Keep the evidence (test report, module certificates, this file) for
   5 years, producible within 10 business days.

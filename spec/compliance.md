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

**Distribution status (2026-10-24): personal builds only.** No sale or
supply of units is planned for v0.5.0; the product-level obligations
below (RCM label, user manual with §15.21 text, EESS registration,
UN 38.3 per cell batch) become live only if that changes. Note the
module-grant nuance: installing the nice!nano myself is fine, but
INSTRUCTING an end-user to install it is a compliance act — another
reason this stays a self-build (review §8).

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
| **ACMA** (EMC + radiocommunications) | Part 15 of Schedule 5 to the Radiocommunications (General) Rules 2021; BLE/wifi SRDs are explicitly in scope | Register as an **"ACMA-only" Responsible Supplier** on the EESS database — **free**, no fees (eess.gov.au: "There are no fees for ACMA-only registration"; a prompt to pay means you picked the wrong box). Complete **ACMA form C02 "Supplier's declaration of conformity"** (May 2023). Apply the **RCM** mark (AS/NZS 4417.1). Keep the evidence and be able to produce it within **10 business days**; retain **5 years**. |
| **EESS (electrical safety)** | **NOT APPLICABLE — the keyboard is out of scope entirely** | See below: extra-low-voltage equipment (<50 V AC RMS / <120 V ripple-free DC) is **"not in-scope"** under the EESS, and "Responsible Suppliers of electrical equipment that is not in-scope ... **do not have to register, or register equipment** in the EESS Registration Database" (eess.gov.au/equipment/not-in-scope/). Our keyboard runs off a 3.7 V cell and 5 V USB — it is not Level 1 equipment at all (Level 1 requires an input rating ≥50 VA / ≥120 VDC). **There is no EESS registration, no EESS CoS and no EESS compliance folder.** (An earlier draft of this file said "Level 1 registration is voluntary, skip it" — the correct statement is stronger: nothing applies. The ACMA FAQ confirms the two regimes are independent: "If my device is not covered by the EESS, can I apply the RCM for ACMA requirements only? Yes.") |
| **NZ** | NZ has its own Radiocommunications (Compliance) Notice 2013 and wants a **Supplier Code Number** for a supplier/importer | Same RCM mark; get an SCN if the units are imported into NZ. |

- The RCM label must be on a readily accessible surface, legible to the
  unaided eye, or a QR code linking to a page showing the RCM
  prominently (acma.gov.au "label your product").
- **Compliance level 1 — TESTING IS NOT REQUIRED.** The ACMA sorts
  devices into compliance levels (Radiocommunications Labelling (EMC)
  Notice 2017, s.4): "**Compliance level 1 — low risk device: There
  are no additional requirements for a low risk device that complies
  with an applicable standard**", and the ACMA's own summary table
  says level 1 = "Testing is not required but you may choose to obtain
  a test report from a testing body". Bluetooth/Wi-Fi short-range
  devices are the canonical level-1 case. A BLE keyboard is therefore
  a **level 1 (low risk) device**: the supplier prepares a **device
  description** and signs a **declaration of conformity** (form C02),
  and may optionally obtain a test report. **A paid lab test is NOT
  required** — which is why the cost line below is a budget for an
  OPTIONAL report, not a fixed cost. Note the medium-risk definition
  ("contains a microprocessor / a transistor switching circuit")
  explicitly excludes battery-powered devices: "A battery-powered
  device is not a medium risk device unless the ACMA has declared the
  device to be a medium risk device".
  [UNVERIFIED: the ACMA's exact level-1/2 boundary for a BLE device
  with a wired TRRS port and USB — the level-1/2 split turns on the
  device class, and no primary text I could reach states the boundary
  for "short-range device + host". The module's own FCC/CE evidence
  plus the device description is the conservative path.]
- Penalties: supplying with no label, or labelling before complying,
  can attract up to **500 penalty units**.
- **Bluetooth SIG** is the one item with a real fee, and the numbers
  are worth stating precisely (SIG schedule of dues and fees, effective
  **2026-03-01**, fetched 2026-10-22):

  | Item | Fee |
  |---|---|
  | **Adopter membership** (annual) | **$0 — the tier is free** |
  | Product Qualification Fee — Adopter, full qualification | $12,000 |
  | Product Qualification Fee — Contributing Adopter (new tier), first qualification each membership year (33% off) | $8,000 (membership $3,500 small / $16,500 large per year) |
  | Product Qualification Fee — Associate (50% off every qualification) | $6,000 (membership $11,250 small / $52,500 large per year) |
  | Company Identifier — Adopter / Contributing Adopter | $1,250 |
  | Company Identifier — Associate | $0 |

  - The Product Qualification Fee (the old "Declaration Fee", renamed)
    is charged **once per design**; further products on the same
    unmodified design are added to the existing listing for free
    (SIG quick-start guide). Our keyboard is an **Unmodified Design**
    — Nordic's qualified nRF52840 + ZMK, referenced by QDID/Design
    Number, with no change to the Bluetooth implementation — so it
    takes the **listing/declaration path with no new RF testing**.
  - **The arithmetic, for this kit specifically:** one design, listed
    once. Adopter = $0 membership + $12,000 + $1,250 identifier =
    **$13,250 total**. Associate = $11,250/yr + $6,000 = **$17,250**
    and buys a discount you would not use (it also pays 50% off
    *every* future qualification, which only pays off if a second
    design is qualified in the same year). So **the free Adopter tier
    is the right choice for this project** — the money is in the
    one-off qualification, not the membership.
  - **Scope, and why this may not bite at all:** the SIG's own FAQ
    says "every company **selling, branding, manufacturing, or
    representing a product as its own** must pay a Product
    Qualification Fee", and separately that to **"market a product
    that implements Bluetooth technology and/or uses any of the
    Bluetooth trademarks (including the word 'Bluetooth')"** you must
    be a member AND complete the qualification. So a self-built
    keyboard that is never sold, never branded as a product and never
    uses the word "Bluetooth" (name it "Hojicha44", not "Hojicha44
    Bluetooth") has **no SIG obligation**; SIG membership is also open
    to **companies, not individuals** (an individual would need a
    sole-trader/company entity). For a **non-commercial pilot this is
    $0 of work**; it becomes a real line item the moment a unit is
    sold or branded.
  - Action: confirm the Nordic-design listing path with a Bluetooth
    qualification consultant **before** any unit is sold (not before
    the board order), and get the entity question answered first.

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
3. If the pilot units will be **sold or branded**, get a Bluetooth
   qualification consultant to confirm the Unmodified-Design listing
   path on Nordic's nRF52840 QDID, and settle the entity question
   (SIG membership is company-only). Budget **USD 13,250** (Adopter
   $0 + $12,000 Product Qualification Fee + $1,250 Company
   Identifier) — one-off, and only if you sell. If the pilot is
   self-built and never sold, this is $0 of work.
4. Write the **device description** (model, the XIAO's FCC ID and its
   reports, the firmware version, photos) and sign the **C02 SDoC**.
   **A lab test report is OPTIONAL, not required** — a level-1 (low
   risk) BLE device needs no testing; if you want one anyway, quote an
   ACMA-accredited lab (EMC Bay / MiCOM / TÜV Rheinland Australia) —
   budget AUD 600–1,500 and 1–3 weeks. **[UNVERIFIED price — confirm
   by quote.]**
5. Produce the RCM label artwork as a **sticker**, not as case
   printing, until the market is fixed.
6. Keep the evidence (test report, module certificates, this file) for
   5 years, producible within 10 business days.

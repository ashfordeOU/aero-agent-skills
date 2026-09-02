# AeroSkills — Legal & Export-Control Research Brief
**Brief 06 · ITAR/EAR, standards licensing, EU dual-use controls, and the AeroSkills publish-safe / publish-gated policy**

**Prepared for:** Ashforde OU (Estonia) — AeroSkills open-source (Apache-2.0) aerospace engineering skills library for AI agents
**Date:** 30 August 2026
**Status:** Legal research briefing. **This document is informational, not legal advice.** Engage qualified counsel (US export-control counsel + Estonian/EU trade counsel) before publishing any USML-specific or gated content.

---

## 0. Executive summary

- AeroSkills' core proposition — **methodology, workflows, tool-usage guidance, and general engineering principles** — is on the *publish-safe* side of every relevant export-control regime, provided three conditions hold: (1) the skills contain **no technical data about specific defense articles** (no designs, dimensions, tolerances, materials, or performance parameters of ITAR/EAR-controlled items); (2) the repository is **genuinely unrestricted** (public GitHub repo, no access controls, Apache-2.0, free); and (3) **no verbatim text from proprietary standards** (DO-178C, DO-254, ARP4754A, AS9100) is reproduced.
- The legal basis is explicit and identical across regimes: ITAR excludes "general scientific, mathematical, or engineering principles commonly taught" and information in the public domain (22 CFR §120.33(b), §120.34); the EAR excludes "published" technology/software (15 CFR §734.7) and fundamental research (15 CFR §734.8); the EU dual-use regime excludes information "in the public domain" and "basic scientific research" (General Technology Note, Annex I to Regulation (EU) 2021/821 — and copyright restrictions do *not* remove information from the EU "public domain" definition).
- The founder's flag is correct: **standards licensing is the sharpest near-term risk** (verbatim DO-178C text = copyright infringement; RTCA/SAE actively enforce DRM and single-user licenses). ITAR/EAR risk is real only if skills start embedding defense-article-specific technical data.
- Recommended posture: publish methodology openly; keep a **private/gated tier** for anything touching USML/CCL-controlled technical data or standards verbatim text; add a compliance notice + responsible-use disclaimer in the README; adopt per-skill frontmatter flags; and never rely on a disclaimer to launder controlled data (the exemption is *public availability*, not intent).

---

## 1. ITAR — the International Traffic in Arms Regulations

### 1.1 Statutory and regulatory framework
- **Arms Export Control Act (AECA), §38, 22 U.S.C. §2778** — grants the President authority to control export/import of "defense articles" and "defense services" and to maintain the **United States Munitions List (USML)**.
- **Executive Order 13637** (78 FR 16129, 2013) delegates administration to the Secretary of State; the **Directorate of Defense Trade Controls (DDTC)** of the Department of State administers the ITAR (22 CFR Part 120.1(a)).
- ITAR is codified at **22 CFR Parts 120–130**. The USML is **22 CFR Part 121** — 21 categories.
- **Enforcement/penalties:** AECA civil penalties up to the greater of **$1,200,000 per violation** or twice the transaction value (22 U.S.C. §2778(e)); criminal violations up to 20 years imprisonment / $1,000,000 (22 U.S.C. §2778(d)); related 18 U.S.C. §§542/545/554 (false statements, smuggling) for technical data.

### 1.2 Aerospace-relevant USML categories (22 CFR §121.1)
- **Category IV** — Rockets, ballistic missiles, launch vehicles, and munitions/military explosives.
- **Category VIII** — Aircraft and related articles (military aircraft; note (h)(1) enumerations such as F-35, F-22, MQ-25, RQ-170 and "future variants thereof").
- **Category X** — Propulsion systems, space vehicles and related equipment.
- **Category XV** — Spacecraft and related articles (post-Export Control Reform, largely narrowed; many items moved to EAR 600-series).
- **Category XIX** — Gas turbine engines and associated equipment (military).
- **Category XXI** — "Articles, technical data, and defense services not otherwise enumerated" (catch-all).
- Since 2013, **Export Control Reform** moved less-sensitive items (aircraft parts, gas turbine engines, spacecraft components) to the Commerce Control List as **"600-series" ECCNs** (e.g., 9A610 aircraft parts, 9E610 technology; BIS "600 Series Items FAQs," Dec. 2016). Technical data for 600-series items is EAR-controlled "technology," not ITAR technical data — but still export-controlled.

### 1.3 What is ITAR "technical data"? — 22 CFR §120.33(a)
> "Technical data" means … (1) Information, other than software …, which is **required for the design, development, production, manufacture, assembly, operation, repair, testing, maintenance, or modification of defense articles** — including blueprints, drawings, photographs, plans, instructions, or documentation; (2) classified information relating to defense articles/defense services; (3) information covered by an invention secrecy order; (4) software directly related to defense articles.

**Statutory exclusions — 22 CFR §120.33(b)** (the crucial paragraph for AeroSkills):
> "The definition in paragraph (a) does **not** include information concerning **general scientific, mathematical, or engineering principles commonly taught in schools, colleges, and universities**, or **information in the public domain** as defined in §120.34, or telemetry data … It also does not include basic marketing information on function or purpose or general system descriptions of defense articles."

### 1.4 Public domain — 22 CFR §120.34(a)
"Public domain" = information **published** and **generally accessible or available to the public**, including through: (1) newsstand/bookstore sales; (2) unrestricted subscriptions; (3) second-class mailing privileges; (4) public libraries; (5) patents; (6) unlimited distribution at open conferences/meetings in the US; (7) public release after approval by the cognizant US Government department/agency; (8) **fundamental research** at accredited US institutions where results are ordinarily published and shared broadly (defined as basic/applied research published broadly in the scientific community, distinguished from restricted/proprietary research).

**Practical note for GitHub publication under ITAR:** unlike EAR §734.7(a)(4), the ITAR list does *not* contain an explicit "posting on the Internet" clause. DDTC has long treated unrestricted public posting as "published and generally accessible" for §120.34 purposes, and open-source publication of public-domain info is not ITAR-controlled — but the *safe* reading requires the posting to be genuinely unrestricted (no gated access, no NDA, no partial embargo). Also, **classified information and invention secrecy order information are never "public domain"** — even if posted.

### 1.5 Defense services — 22 CFR §120.32
A "defense service" includes (1) the furnishing of **assistance (including training)** to foreign persons in the design, development, engineering, manufacture, production, assembly, testing, repair, maintenance, modification, operation, demilitarization, destruction, processing, or use of defense articles; and (2) the furnishing of **technical data controlled under the USML** to foreign persons. This matters to AeroSkills: a skill that *teaches* a foreign user how to build/modify a USML defense article (e.g., "how to modify an F-35 avionics component") would constitute furnishing a defense service, absent the public-domain/general-principles exclusions.

### 1.6 Does publishing engineering *skills/workflows/methodology* trigger ITAR? — the analysis
**Short answer: No, if the skills convey method; Yes, if they convey defense-article-specific technical data.**

- **Methodology = general engineering principles.** Workflows describing *how to do* requirements capture, system safety assessment, DO-178C objective-based software certification, verification, configuration management, or tool usage fall squarely within "general scientific, mathematical, or engineering principles commonly taught in schools, colleges, and universities" (22 CFR §120.33(b)). They describe *process*, not a *particular defense article*.
- **The line is drawn by the content, not the format.** A "SKILL.md" that says "produce a Plan for Software Aspects of Certification per DO-178C, with the 10 system objectives from Table A-1" is methodology. A skill that embeds actual design parameters ("the F-35 radar antenna uses element spacing X at frequency Y with material Z") is technical data required for design/development of a defense article — ITAR-controlled regardless of how it is packaged.
- **General system descriptions and marketing info are also excluded** (22 CFR §120.33(b), final sentence).
- **Deemed-export/visibility rule:** an ITAR "export" includes disclosing technical data to a foreign person (22 CFR §120.17; release to foreign nationals = deemed export). Publishing to an open internet repo accessible abroad is, for non-public-domain data, an export to every downloader — which is precisely why the public-domain/general-principles exclusions must be affirmatively confirmed for every skill before release.
- **Recommendation:** write a per-skill ITAR/EAR self-classification line (see §8 policy), and maintain a **no-USML-data rule**: no specific parameters, tolerances, drawings, part numbers, or performance data of USML/600-series items anywhere in the public repo.

---

## 2. EAR — Export Administration Regulations and dual-use items

### 2.1 Framework
- **Export Administration Regulations (EAR), 15 CFR Parts 730–774**, administered by the **Bureau of Industry and Security (BIS)**, Department of Commerce. Statutory basis: Export Control Reform Act of 2018 (50 U.S.C. §4801 et seq., esp. §4819–4820).
- **Dual-use items** (civil items with military applicability) are on the **Commerce Control List (CCL), 15 CFR Part 774**, classified by **Export Control Classification Number (ECCN)**.
- "Technology" under the EAR (15 CFR §772.1) = **"specific information" necessary for the development, production, or use of a product**; the definition's Notes clarify that technology is *not* "general knowledge" (information "in the public domain" or "basic scientific research") and not "general scientific, mathematical, or engineering principles commonly known in the public domain." (Note: §772.1's "technology" definition expressly excludes "general knowledge"; the ITAR exclusion is the mirror image at §120.33(b).)

### 2.2 Aerospace-relevant CCL entries
- **Category 9 — Aerospace and Propulsion:** 9A001 (aero gas turbine engines with certain technologies), 9A004 (UAVs), 9A991 (uncontrolled-but-noted aero items), **9D** (software), **9E003** (technology for gas turbine engine development/production — e.g., blade manufacturing technology), 9E610 (technology for 600-series aircraft items).
- **Category 7 — Navigation and avionics** (7A003 etc.); **Category 5 Part 2 — Information security** (5D002 encryption software; see §2.4).
- **600-series** ECCNs (xY6zz) hold munitions items moved off the USML (BIS "600 Series Items FAQs," 2016): e.g., **9A610** (aircraft and related articles), **9E610** (technology). Technical data for 600-series items is EAR "technology" requiring a license for export unless published/publicly available.

### 2.3 The "published" exception — 15 CFR §734.7 (critical for open source)
> "(a) Except as set forth in paragraphs (b) and (c), **unclassified 'technology' or 'software' is 'published,' and is thus not subject to the EAR**, when it has been made available to the public without restrictions upon its further dissemination, such as through: (1) unrestricted subscriptions; (2) public libraries/collections; (3) unlimited distribution at open conferences; (4) **public dissemination … including posting on the Internet on sites available to the public**; or (5) submission of a written composition … with the intention that it will be made publicly available if accepted for publication."

**Open-source software distributed free and without restriction is "published"** — this is the doctrinal foundation for the entire open-source ecosystem's EAR compliance. The Linux Foundation's *LF Guidance: Policy and Best Practices — US EAR* confirms: "standards and open source software that are published or are intended to be published … are not ordinarily subject to the EAR." BIS supplement no. 1 to part 732 (Questions G(1)/G(2)) confirms publicly available source code — and its compiled form — is not subject to the EAR. The libfprint project's documented consultation with the US exports office reached the same conclusion.

### 2.4 Other relevant exclusions/limits
- **Fundamental research — 15 CFR §734.8:** technology/software arising from fundamental research (science, engineering, or mathematics, ordinarily published and shared broadly, no proprietary/national-security restrictions) intended for publication is not subject to the EAR.
- **Encryption caveat — 15 CFR §734.7(b), §742.15:** published *encryption source code* under ECCN **5D002** remains subject to the EAR unless it qualifies for the publicly-available encryption object-code/source-code provisions of §742.15(b). (Relevant only if AeroSkills ships crypto code — not expected for aerospace process skills, but note it.)
- **Firearm-file caveat — 15 CFR §734.7(c):** posting ready-to-print firearm production files does *not* qualify for the published exception. (Not relevant to AeroSkills, but illustrative that the "published" exception has carve-outs.)

---

## 3. The Wassenaar Arrangement

- **Wassenaar Arrangement on Export Controls for Conventional Arms and Dual-Use Goods and Technologies** (est. 1996, Vienna secretariat, 42 participating states) — the multilateral regime whose **List of Dual-Use Goods and Technologies** (10 categories, incl. **Category 9 – Aerospace and Propulsion**) underpins both the EAR and the EU dual-use list. Politically binding; implemented nationally.
- **2013 Wassenaar amendment — "intrusion software" and IP-network surveillance** (WA 4.A.5, 4.D.4, 4.E.1.c): controls software/technology "specially designed or modified for the generation, operation or delivery of, or communication with, intrusion software." This is the canonical **dual-use precedent for security/engineering tooling**: the security research community (USENIX, Privacy International, Dartmouth's "Why Wassenaar's Definitions of Intrusion Software…" comment) argued the definition would chill legitimate research tooling; BIS proposed implementing rules at 80 FR 28853 (2015). Two points matter for AeroSkills:
  1. **Public-domain and basic-scientific-research exclusions apply** — open, published tooling is not controlled even where the underlying technique is WA-listed.
  2. The episode shows that **even generic engineering tooling can be caught by list-based controls when it is "specially designed" for a controlled purpose** — and that open publication is the standard decontrol mechanism. For aerospace *process* skills (certification, V&V, toolchains), no WA-listed "technology" (e.g., 9E003 turbine-manufacturing technology) should be embedded; referencing it is fine.

---

## 4. How open-source software handles ITAR/EAR — precedents and practice

| Precedent | Approach | Legal basis |
|---|---|---|
| Apache Software Foundation projects (Apache-2.0) | Publish openly; no per-release export screening for ordinary OSS; Apache-2.0 inbound/outbound licensing discipline | "Published" per EAR §734.7; ITAR §120.34 public domain |
| Linux Foundation (LF Guidance: US EAR best practices) | Published standards + OSS not ordinarily subject to the EAR; publish-first posture; seek legal advice for crypto | EAR §734.7, §734.8 |
| libfprint (fingerprint imaging OSS) | Documented analysis + BIS consultation confirming open-source distribution = publicly available = not subject to EAR | EAR §734.3(b)(3), §734.7 |
| Metasploit / exploit tooling (infosec dual-use) | Open publication of offensive tooling; rely on public-domain/generally-available decontrols; responsible-use disclaimers accompany but are *not* the legal basis | WA "intrusion software" decontrols; public-domain exclusions |
| NIST NBIS (export-controlled code) | Kept off open distribution (CDROM + address screening) — the *counterexample* of what not to do for a community project | ECCN 3D980 (crime-control software) |

**Key lesson:** the mechanism that keeps open source legal is **public availability**, not intent. A disclaimer ("for authorized use only") is good hygiene and shapes user behavior but does **not** decontrol data. Conversely, genuinely public, unrestricted publication *does* decontrol — so AeroSkills should (a) keep the repo fully open and unrestricted, and (b) never mix in content that would be controlled *even if published* (classified info, invention secrecy orders, 5D002 crypto code outside §742.15(b), firearm-file-type carve-outs — none expected here).

---

## 5. Standards licensing — DO-178C, DO-254, ARP4754A, AS9100, FAR/CS-25

### 5.1 Ownership and availability matrix

| Standard | Publisher / owner | Status of text | License terms |
|---|---|---|---|
| **DO-178C** *Software Considerations in Airborne Systems and Equipment Certification* (2011) | RTCA (US) & EUROCAE (EU) jointly (EUROCAE twin: **ED-12C**) | **Proprietary, sold** (~$340–700 depending on format/currency); DRM-protected PDF | RTCA Electronic License Agreement: **single-user, personal use; no copying, resale, transfer, redistribution; additional copies require additional licenses; violations prosecuted** (RTCA FAQ). Content of RTCA documents is "RTCA proprietary information"; requests to reference/extract content require RTCA President's approval (RTCA Proprietary References Policy) |
| **DO-254** *Design Assurance Guidance for Airborne Electronic Hardware* (2000) (EUROCAE twin: **ED-80**) | RTCA / EUROCAE | Proprietary, sold | Same RTCA terms |
| **ARP4754A** *Guidelines for Development of Civil Aircraft and Systems* (2010; rev. ARP4754B 2023) | **SAE International** (S-18 committee) | Proprietary, sold (~$180 USD) | SAE single-purchase digital license; no redistribution |
| **AS9100** *Quality Management Systems – Requirements for Aviation, Space and Defense Organizations* (AS9100D 2016; current AS9100E) | **IAQG** (International Aerospace Quality Group) develops; **SAE** publishes (Americas); also EN/JISQ twins (Europe: EN9100) | Proprietary, sold (occasional IAQG free-download windows, e.g., AS9100D promotional period) | SAE/IAQG terms; no verbatim reproduction |
| **FAR Part 25** (14 CFR Part 25, *Airworthiness Standards: Transport Category Airplanes*) | **US Government (FAA)** | **Public domain — US government work** (17 U.S.C. §105); free at eCFR.gov | Freely quotable with citation; no license needed |
| **CS-25** *Certification Specifications and Acceptable Means of Compliance for Large Aeroplanes* | **EASA** (EU agency) | Free PDFs on EASA website (incl. "Easy Access Rules") | © European Union Aviation Safety Agency; "**Reproduction is authorised, provided the source is acknowledged**, save where otherwise stated" (EASA copyright notice) |

### 5.2 Copyright vs. publicly-available — the practical rules for skills

1. **Standards are copyrighted expression.** The *text* (sentence-level prose, tables of objectives, appendix content) of DO-178C/DO-254/ARP4754A/AS9100 is protected by copyright and distributed under restrictive single-user licenses with DRM. Copying text from them into SKILL.md files (or into any repo file) is infringement **unless** it falls under fair use (17 U.S.C. §107, US; shorter quotation + attribution is defensible; wholesale reproduction of tables/objective lists is not) or permission.
2. **Facts, ideas, and names are not protected.** The *existence* of the standard, its title, its scope, the general structure of its process ("DO-178C defines five software levels and an objective-based process"), and its role in certification (FAA AC 20-115D references DO-178C as acceptable means of compliance) are ideas/information you may state. Summarize **in your own words**.
3. **Quoting vs. summarizing:**
   - *Safe:* "DO-178C (RTCA, 2011) is the primary means of compliance for airborne software under FAA AC 20-115D. It defines software levels A–E and an objective-based process including planning, development, verification, configuration management, and airworthiness liaison." — this is summary + facts.
   - *Safe (fair use):* short verbatim quotes (< ~100 words) with explicit attribution and quotation marks, used for commentary/education.
   - *Unsafe:* reproducing Table A-1's objective lists, appendix text, section text, or any multi-line verbatim block; posting the PDF; including it in a repo; distributing via the skills library.
4. **Never include DRM-stripped or shared-purchase standards content.** RTCA actively enforces (license cancellation + prosecution per its FAQ).
5. **Do not copy material from illegally hosted copies** of standards (piracy sites) — same infringement, plus the repo inherits it.
6. **FAR/CS-25 are different:** FAR 25 text is US government work (public domain); CS-25 is freely published by EASA with an attribution-only reproduction notice. Both may be quoted with citation. (Still prefer paraphrase for clarity, but the risk is minimal.)
7. **Trademarks:** use standard names (DO-178C, ARP4754A, AS9100) nominatively to identify; don't imply endorsement by RTCA/SAE/IAQG; a "Not affiliated with / not endorsed by RTCA, SAE, IAQG, EASA, or FAA" notice is prudent.

---

## 6. Compliance structure of successful open-source security/engineering libraries

### 6.1 Anthropic's own skills repo (github.com/anthropics/skills)
- Public "Agent Skills" repository (Apache-2.0 for most skills); the docx/pdf/pptx/xlsx skills are **source-available, not open source** — a clean precedent for **mixing license tiers in one repo**.
- README disclaimer: "**These skills are provided for demonstration and educational purposes only.**"

### 6.2 Anthropic Cybersecurity Skills library (the closest structural analogue to AeroSkills)
The community "Anthropic Cybersecurity Skills" libraries (Apache-2.0, agentskills.io standard, MITRE ATT&CK / NIST CSF 2.0 / ATLAS / D3FEND / AI RMF mapped, 700+ SKILL.md files) demonstrate the *de facto* compliance stack for a dual-use skills library:
1. **License:** Apache-2.0 (full LICENSE file), per-skill `license: Apache-2.0` frontmatter.
2. **README responsible-use banner:** "⚠️ Authorized & lawful use only … offensive and dual-use techniques … intended for authorized penetration testing, security research, defense, and education. Only use them against systems you own or have explicit written permission to test … You are solely responsible for how you use these skills."
3. **SECURITY.md** — responsible-disclosure policy; **CODE_OF_CONDUCT.md**; **CONTRIBUTING.md** with review gates; **CITATION.cff**.
4. **Structured SKILL.md anatomy:** YAML frontmatter (name, description, domain, subdomain, tags, framework mappings, version, author, license) + body sections (When to Use / Prerequisites / Workflow / Verification) — progressive disclosure, ~30 tokens to scan.
5. **No controlled data embedded:** the skills describe *how to run tools and interpret results*, not controlled designs — the same posture AeroSkills should adopt.
6. **Infosec dual-use precedent:** Metasploit & friends publish offensive tooling openly, relying on the public-domain/generally-available decontrols discussed in §3–4; disclaimers accompany but are not the compliance mechanism.

### 6.3 Recommended AeroSkills compliance stack
- Apache-2.0 LICENSE; NOTICE file naming Ashforde OU.
- README compliance banner (template in §8.4): "civil aerospace engineering methodology; educational; not ITAR/EAR-controlled technical data; standards referenced, not reproduced; users responsible for their own compliance."
- SECURITY.md (disclosure), CONTRIBUTING.md (contributors must certify their submissions contain no ITAR/EAR/USML data, no classified content, no verbatim standards text), CODE_OF_CONDUCT.md, DCO or CLA.
- Per-skill frontmatter: `compliance: none | ITAR-GATED | EAR-GATED | STANDARDS-REF` flag + `standards: [DO-178C, ARP4754A]` + `gated: false`.
- `GATED/` directory (or separate private repo) for any controlled-content tier; gate via manual approval, not public distribution.
- Export-control notice in LICENSE or README stating the EU/Estonian legal basis (public-domain exclusion per Regulation (EU) 2021/821 Annex I GTN) and that the work is not subject to EU dual-use export authorization as published.

---

## 7. EU / Estonian angle

### 7.1 EU framework — Regulation (EU) 2021/821
- **Regulation (EU) 2021/821** of 20 May 2021 (OJ L 206, 11.6.2021, pp. 1–461), in force **9 September 2021**, recasting Regulation (EC) No 428/2009. Sets up the Union regime for controls on **exports, brokering, technical assistance, transit and transfer of dual-use items**.
- **Dual-use items** = items, including software and technology, usable for both civil and military purposes, listed in **Annex I** (updated via delegated regulations, e.g., 2023/996, 2023/2616, 2024/2547, and the September 2025 update). Annex I mirrors the Wassenaar list: Category 9 – Aerospace and propulsion (9A001 aero gas turbines, 9A004 UAVs, 9D software, **9E003** technology for gas turbine development/production); Category 5 Part 2 – information security (5D002); Category 7 – navigation/avionics.
- **Export authorization required** for exports of Annex I items outside the EU customs territory (Art. 3); **catch-all controls** (Art. 4) for non-listed items intended for WMD use or military end-use in arms-embargoed countries; **brokering** (Art. 7) and **technical assistance** (Art. 8) authorizations; **intra-EU transfer controls** for Annex IV (high-sensitivity) items (Art. 9(2) — relevant for Category 5 Part 2 items; Estonia implements a 24-hour electronic customs notification for intra-Community transfers of Category 5 Part 2 items per the Strategic Goods Act).
- **Electronic transmission = export** (recital 11): "Transmission of dual-use software and technology by means of electronic media, fax or telephone to destinations outside the customs territory of the Union should also be controlled."
- **Records:** exporters keep detailed records for **5 years** (Art. 15(3)); **Internal Compliance Programmes (ICPs)** encouraged (Art. 12(3)) — the EU "Best Practice Guidelines on ICPs" (Wassenaar, 2025) are the reference.
- **Union General Export Authorisations (EUGEAs)** — Annex II (EU001–EU008); **Delegated Regulation (EU) 2022/699** removed Russia from EUGEA scope (sanctions context).
- **THE decontrol clause (Annex I, General Technology Note):**
  > "Controls on 'technology' transfer do **not** apply to information **'in the public domain'**, to **'basic scientific research'**, or to the minimum necessary information for patent applications. … **'In the public domain'** … means 'technology' or 'software' which has been made available **without restrictions upon its further dissemination** (**copyright restrictions do not remove** 'technology' or 'software' from being 'in the public domain')."
  And Regulation recital 13 + Art. 8(3)(b) extend the public-domain/basic-scientific-research exclusion to technical assistance.
  **Implication for AeroSkills:** a free, unrestricted, Apache-2.0 public GitHub repo is *prima facie* "in the public domain" under the EU GTN — no EU export authorization is required for the published content. This is the EU-side mirror of EAR §734.7.

### 7.2 Estonia — what an Estonian OU must consider
- **National law: Strategic Goods Act** (*Strateegilise kauba seadus*; consolidated text RT I, 17.04.2025, 1, in force 27.04.2025), implementing Regulation (EU) 2021/821 and the military-goods regime. Under the Act, **"export" expressly includes "the transfer of software and technology related to military goods from Estonia"** and "the export of dual-use items to a non-EU country" per Art. 2(2) of Regulation 2021/821, plus provision of services abroad.
- **Competent authority: the Strategic Goods Commission (SGC)** under the **Estonian Ministry of Foreign Affairs** (Islandi väljak 1, 15049 Tallinn; stratkom@vm.ee; +372 637 7400). License applications: ~30 working days processing; state fees €13 (license application), €13 (registration as user of a general permit), €64 (military-goods broker register, undertaking certification) etc. In 2025 the SGC issued 522 licenses (+43% YoY) — enforcement is active (8 criminal proceedings initiated in 2025 re Strategic Goods Act violations).
- **Relevant Estonian lists:** List of Military Goods (riigiteataja, Government regulation annex), the EU dual-use list (Annex I 2021/821), the torture-goods list (Regulation (EU) 2019/125).
- **What Ashforde OU must consider:**
  1. **Publication posture:** publishing AeroSkills openly on GitHub = an "export" of technology/software to non-EU recipients *in form*, but the **public-domain/basic-scientific-research exclusions** (GTN; recital 13) mean **no license is required** for the open library as designed. Keep it free, unrestricted, and fully public to stay inside the exclusion.
  2. **Don't import controlled content:** never include Annex I Category 9-listed "technology" that is not public domain (e.g., 9E003 turbine-manufacturing specifics from a client), US ITAR data, or national classified content. Gated content must be handled via the SGC (export authorization), not published.
  3. **Catch-all awareness (Art. 4):** even non-listed content could trigger controls if it has an apparent WMD/embargoed-military end-use. Civil-aircraft certification methodology does not, but weapons-adjacent skills (missile guidance, warhead fuzing, stealth design) should be **gated or excluded**.
  4. **Sanctions screening:** Russian/Belarusian (and other) sanctions post-2022; Delegated Regulation 2022/699 removed Russia from EUGEAs; the SGC's 2025 overview stresses preventing goods reaching aggressor states. Open publication is generally compatible, but any gated/exchange channel must screen end-users.
  5. **Records & ICP:** keep a simple internal compliance file (content classification memos per skill family, contributor certifications) — proportionate ICP for a small OU; the Wassenaar "Best Practice Guidelines on Internal Compliance Programmes" (Dec. 2025) is the template.
  6. **No US jurisdictional hook from Estonia:** the ITAR/EAR apply to AeroSkills only insofar as the *content* is US-controlled technical data or the OU does US-jurisdiction acts (e.g., receiving ITAR data under a US agreement, US persons involved). Ashforde OU publishing EU-authored civil methodology has no US licensing obligation — **but** the library's *content* must still avoid US-controlled data, because once USML/CCL technical data is embedded, US jurisdiction follows the data, not the author.
  7. **European Defence Fund / EDF participation caveat:** Estonian aerospace companies active in EDF projects increasingly deal with SGC licensing; if AeroSkills later integrates EDF-project knowledge, that content is gated by default.

---

## 8. AeroSkills publish-safe / publish-gated content policy

### 8.1 Publish-safe (open, Apache-2.0, unrestricted public repo)

| Category | Examples | Legal footing |
|---|---|---|
| **Methodology & workflows** | Requirements capture, V&V, certification-planning workflows, configuration management, safety-assessment process flow, tool-integration procedures | ITAR §120.33(b) general engineering principles; EAR "general knowledge"; EU GTN (public domain) |
| **General scientific/mathematical/engineering principles** | Physics of flight, structural analysis basics, systems-engineering theory, probability for safety analysis | ITAR §120.33(b) (explicit); EAR; EU GTN |
| **Tool usage** | How to use Simulink, DOORS, Polarion, static analyzers, traceability tools; command-level guidance **without embedded design data** | Methodology, not technical data for a specific defense article |
| **Standards references** | Naming DO-178C/DO-254/ARP4754A/AS9100, paraphrased objective summaries in own words, short attributed quotes (<~100 words), links to official stores | Copyright: summary/fair-use; facts and ideas unprotected |
| **Regulatory text (public)** | FAR 25 (14 CFR Part 25, US government work) quoting; CS-25 quoting with EASA attribution ("reproduction authorised, provided the source is acknowledged") | Public domain / EASA attribution license |
| **Compliance hooks** | "Before exporting technical data, verify ITAR/EAR/EU classification"; checklists referencing regulatory concepts | General principles; improves user compliance |
| **Process checklists in your own words** | Verification activity lists paraphrased from DO-178C objectives (not verbatim tables) | Original expression; no copyright issue |

### 8.2 Publish-gated (private repo, access-controlled, or excluded entirely)

| Category | Why gated | Handling |
|---|---|---|
| **Technical data for USML/600-series defense articles** | Specific designs, dimensions, tolerances, materials, part numbers, performance parameters of e.g. military aircraft, missiles, engines | Exclude from public repo; if needed, private repo + ITAR-compliant handling (or omit entirely) |
| **EAR "technology" for CCL items (non-public)** | 9E003-class turbine-manufacturing technology, 7E-class avionics tech received under license | Exclude unless published/public-domain; otherwise BIS/EU license analysis |
| **Verbatim proprietary standards text** | DO-178C tables/objectives/appendix text; ARP4754A/AS9100 text | Never reproduce; summarize + link to purchase; obtain RTCA/SAE permission for any substantial extraction |
| **Classified content** | Any national-security classification (any country) | Never — excluded from scope entirely |
| **Invention secrecy order information** | US 22 CFR §120.33(a)(3) | Never |
| **Encryption source code (if ever)** | EAR §734.7(b)/§742.15(b), EU Cat 5 Part 2 | Only with dedicated export-control review |
| **Client/proprietary data** | NDA'd design data, EDF-project data | Gate by contract; never publish |

### 8.3 Operating rules
1. **The "no-USML-data" rule:** every skill must pass a self-classification check: "Does this convey specific information required to design/develop/produce a USML or 600-series defense article? If yes → gate." Default = methodology → publish.
2. **Genuine openness:** free, no access controls, no NDAs, Apache-2.0 — required to keep the "published"/"public domain" decontrols intact in all three regimes.
3. **Standards discipline:** name + paraphrase + short attributed quotes + links only; no verbatim tables; no PDFs; maintain a `STANDARDS.md` that states which standards are referenced and that texts are © RTCA/SAE/IAQG and must be purchased.
4. **Contributor controls:** CONTRIBUTING.md certification (no ITAR/EAR/USML data, no classified content, no verbatim standards text, own original work); DCO; review gate before merge.
5. **Frontmatter flags:** `compliance: none|ITAR-GATED|EAR-GATED|STANDARDS-REF`; `standards: [...]`; `gated: bool` — enables automated sweep.
6. **Sweep & audit:** quarterly content scan for red-flag terms (part numbers, classified markings, "ITAR," specific military platform parameters); remove/gate on detection.
7. **Disclaimer hygiene:** README compliance banner (below) + per-skill "authorized use" where dual-use relevant — remembering disclaimers shape behavior but **public availability is the legal mechanism**.
8. **Threshold for counsel:** engage US export counsel before adding any USML-specific or 600-series-referencing skill; engage an Estonian trade lawyer before any gated-content distribution from the OU.
9. **Never mark public content as ITAR/EAR-controlled** (mis-marking is itself a compliance failure and spooks downstream users); instead mark as "not controlled technical data as published — verify before use."

### 8.4 Template — README compliance banner (adapt for AeroSkills)
> **Compliance notice.** AeroSkills is an open, unrestricted library of *civil aerospace engineering methodology* for AI agents, published by Ashforde OU (Estonia) under Apache-2.0. The content consists of general engineering principles, processes, and tool-usage guidance; it does **not** contain ITAR/EAR-controlled technical data, classified information, or proprietary standards text. Standards (DO-178C, DO-254, ARP4754A, AS9100, FAR/CS-25) are referenced and summarized; the standards themselves are © RTCA, EUROCAE, SAE, and IAQG and must be purchased from the publishers. As published without restrictions, this library falls within the "published information" (15 CFR §734.7), ITAR public domain (22 CFR §120.34), and EU dual-use "public domain" (Annex I General Technology Note, Regulation (EU) 2021/821) exclusions. Users are solely responsible for compliance with export-control and sanctions laws applicable to their own use, including any gated content. Not affiliated with or endorsed by RTCA, SAE, IAQG, EASA, FAA, or any government.

---

## 9. Sources (citation-style)

**Primary legal texts**
- Arms Export Control Act, §38, 22 U.S.C. §2778 (esp. (d), (e) penalties).
- Executive Order 13637, 78 FR 16129 (2013).
- ITAR, 22 CFR Parts 120–130; esp. §120.1 (authority), §120.32 (defense service), §120.33 (technical data), §120.34 (public domain), Part 121 (USML Categories IV, VIII, X, XV, XIX, XXI).
- EAR, 15 CFR Parts 730–774; esp. §734.3(b)(3) (publicly available tech/software not subject), §734.7 (published; internet posting), §734.8 (fundamental research), §734.16/§734.17 (releases, encryption), §742.15 (publicly available encryption), §772.1 ("technology," "specially designed"); CCL 15 CFR Part 774 (ECCNs 9A004, 9A610, 9E003, 9E610, 5D002); BIS "600 Series Items FAQs" (2014/2016).
- Regulation (EU) 2021/821 (OJ L 206, 11.6.2021), esp. recitals 11, 13; Arts. 2, 3, 4, 7, 8, 9, 12, 15; Annex I (incl. General Technology Note; Category 5 Part 2; Category 9); Annex II (EUGEAs); Annex IV; Delegated Regulations 2022/699, 2023/996, 2023/2616, 2024/2547, 2025 update.
- Estonia: Strategic Goods Act (RT I, 17.04.2025, 1, in force 27.04.2025); Strategic Goods Commission, Ministry of Foreign Affairs (vm.ee — license application, fees €13, 30-working-day processing, stratkom@vm.ee).
- Wassenaar Arrangement — Initial Elements (1996); List of Dual-Use Goods and Technologies (2024/2025 lists); Best Practice Guidelines on Internal Compliance Programmes (Dec. 2025); BIS proposed rule, 80 FR 28853 (2015) (WA 2013 intrusion/surveillance implementation).

**Standards/licensing**
- RTCA: DO-178C (2011, SC-205), DO-254 (2000), DO-331/332/333; RTCA Electronic License Agreement & FAQs (rtca.org/standards/faqs); RTCA "Policy for Proprietary References in RTCA Documents" (2019); FAA AC 20-115D (DO-178C means of compliance).
- EUROCAE: ED-12C (joint with DO-178C), ED-80 (joint with DO-254).
- SAE International: ARP4754A (2010, 115 pp, ~$180; DOI 10.4271/ARP4754A), ARP4754B (2023), ARP4761, AS9100 series (DOI 10.4271/AS9100); SAE store terms.
- IAQG: iaqg.org — 9100 QMS standard, 24 published standards, publisher relationships.
- FAA: 14 CFR Part 25 (eCFR). EASA: CS-25 (Amendments; Easy Access Rules); EASA copyright notice ("Reproduction is authorised, provided the source is acknowledged").

**Open-source/dual-use precedent**
- Linux Foundation, *Guidance: Policy and Best Practices — US EAR* (bestpractices.linuxfoundation.org).
- libfprint, "US Export Control" analysis (fprint.freedesktop.org) — EAR §734.3(b)(3)/§734.7 application; BIS supplement no. 1 to part 732, Questions G(1)/G(2).
- ASF legal/licensing policies (apache.org/legal); Apache License 2.0.
- Anthropic: github.com/anthropics/skills (Apache-2.0; "demonstration and educational purposes" disclaimer); Anthropic Cybersecurity Skills libraries (mukul975 et al.; Apache-2.0; README "Authorized & lawful use only" banner; SECURITY.md; agentskills.io standard).
- Wassenaar/intrusion-software debate: Privacy International, "Export controls and the implications for security research tools" (2013); USENIX ;login, "Why Wassenaar's Definitions of 'Intrusion Software' Put Security Research and Defense at Risk" (2014); Dartmouth public comment (2015).
- University guidance: Univ. of Pittsburgh Research Security (publicly-available/public-domain statuses, ITAR 120.10/120.11, EAR 734.3/734.7–734.11); LBNL Fundamental Research Exclusion note.

---

*End of brief. Next step: legal review of the first batch of skills against §8; consider engaging counsel for the gated-content tier and any USML-adjacent skills.*

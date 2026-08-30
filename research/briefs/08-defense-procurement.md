# 08 — Defense & Aerospace Procurement and Enterprise Adoption of AI Developer Tools

**Date:** 2026-08-30 · **Prepared for:** AeroSkills GTM research · **Status:** Research brief
**Scope:** How primes (Boeing, Lockheed Martin, Northrop Grumman, RTX, GE Aerospace, Airbus, BAE, Saab, Leonardo) and their suppliers buy software, adopt AI, and what an enterprise sale looks like. All facts below are sourced from cited public reporting; figures are point-in-time and should be re-verified before external use.

---

## Executive Summary

- Defense/aerospace is the most security-gated software market on earth: every tool is vetted against **ITAR/EAR export controls**, **CMMC 2.0 / NIST SP 800-171** contractor obligations, **FedRAMP/DISA IL** cloud authorizations, and prime-specific **approved-tool and vendor-risk processes**. Commercial feature superiority alone disqualifies ~78% of tools before a demo.
- Demand is real and accelerating: the DoD CDAO issued a call for AI-enabled coding tools for **tens of thousands** of developers requiring **FedRAMP High, DISA IL5, and air-gapped deployment**. Primes are building internal "AI Factories" (Lockheed: 7,000 engineers, 75,000 users; Boeing: 70+ GenAI apps, Code Assistant) — and they prefer **on-prem, air-gapped, open-weight-model** tooling over public SaaS.
- Regulatory clock: CMMC 2.0 phases in **Nov 2025 → Nov 2028** (self-assessment now, C3PAO certification Nov 2026, Level 3 Nov 2027, full implementation Nov 2028). Any SaaS touching CUI must be **FedRAMP Moderate-equivalent**; failure to certify = loss of contract eligibility + False Claims Act exposure.
- Enterprise sales cycles run **6–18+ months** (regulated buyers at the long end). The buyer is a **committee** — engineering director/CTO (value), security architect (compliance), IT/procurement (contract), and an internal champion (individual engineer). Land-and-expand from engineer expense accounts is the realistic entry, but it is **structurally blocked** in fully cleared/air-gapped environments, so a top-down enterprise motion is required there.
- MBSE/digital engineering is a genuine tailwind: **DoDI 5000.97 (Dec 2023)** mandates digital engineering for new programs; MBSE market ≈ $4.5B (2026) growing ~16.5% CAGR; MBSE tooling (Cameo/MagicDraw, DOORS, Capella, Rhapsody) has a documented workforce skill gap and is now being augmented by LLM/agent tooling — the exact wedge AeroSkills occupies.

---

## 1. How Large Aerospace/Defense Organizations Buy Software

### 1.1 Procurement structure

- **Primes** (Boeing, Lockheed, Northrop, RTX, GE Aerospace, Airbus, BAE, Saab, Leonardo) operate multi-layered IT procurement: centralized **enterprise IT** (approved tool catalogs, enterprise licenses), **program-level engineering budgets** (tooling funded per contract/program), and **innovation/digital-engineering offices** (new-technology pilot budgets, e.g., Lockheed's AI Center/LAIC, Boeing's Digital & AI org).
- **Tier 2/3 suppliers** (hundreds of thousands of DIB companies; ~220,000 contractors in the U.S. Defense Industrial Base) buy tools that their **primes require** — primes flow down compliance requirements contractually (CMMC, ITAR data handling, quality systems) *ahead* of the formal DoD timeline, so vendor questionnaires from primes are arriving now.
- **Government end-customers** buy through the Adaptive Acquisition Framework: the **Software Acquisition Pathway (SWP)** (DoDI 5000.87), **Other Transactions (10 U.S.C. § 4022)** and **Commercial Solutions Openings (10 U.S.C. § 3458)** are now the *default* solicitation/award vehicles for software (March 2025 DoD acquisition-preference memo). FY20 NDAA Section 800 created the SWP; software programs are not treated as MDAPs and must deliver usable capability within one year of first obligation.
- DoD consolidates to speed up: the Army's **$10B, 10-year Palantir Enterprise Agreement (July 2025)** folded 75 contracts into one to "remove contract and re-seller pass-through fees" and shorten procurement timelines. Enterprise agreements with volume discounts are the pattern for strategic software.

### 1.2 Vendor onboarding: approved lists, vetting, security review

- **Approved Products Lists**: DISA maintains the **DoDIN Approved Products List (APL)** (DoDI 8100.04) for products touching the DoD information network; primes maintain their own internal **approved-software catalogs** — a tool not on the catalog requires an exception request routed through IT security.
- **Vendor security vetting** at DCSA-cleared firms follows a 12-point checklist involving the **Facility Security Officer (FSO)** and IT security; evaluation typically takes **4–6 weeks minimum**. Red flags for buyers: no completed **VSAQ** (Vendor Security Assessment Questionnaire) within 10 business days, vague data-residency/subprocessor answers, no incident-response plan, no defense-contractor references.
- **Security questionnaires**: standard instruments are the **VSAQ**, the **SIG (Standardized Information Gathering) questionnaire** (Shared Assessments), and custom NIST-mapped questionnaires (CSF, SP 800-53, SP 800-171). Deloitte 2025 VRM data: security reviews add **4–8 weeks** in regulated sectors; **62% of enterprises require SOC 2 and GDPR compliance upfront**; having SOC 2 ready shortens cycles by ~3 months versus bespoke questionnaires.
- **Compliance floor for cloud tools**: any SaaS handling CUI must be **FedRAMP Moderate authorized (or equivalency)** under DFARS 252.204-7012; DoD RFPs increasingly hard-require FedRAMP Moderate; AI coding tooling for DoD specifically requires **FedRAMP High + DISA IL5 Provisional Authorization**. FedRAMP Moderate = ~325 controls and continuous monitoring; a vendor-written SSP/POA&M alternative runs 6–12 months and ~$180K+ in consulting.
- **78% of commercial tools are eliminated before a single demo** because of security compliance, not features (GovCon proposal-software analysis, 2026).

### 1.3 ITAR/EAR restrictions on tooling

- **ITAR** (International Traffic in Arms Regulations, 22 CFR 120–130, USML): software "specifically designed" for military applications (weapons C2, military intel, military crypto, satellites/space defense) is a **defense article**. Sharing ITAR technical data with a **foreign person is an export (deemed export)** — so ITAR-controlled dev environments must be restricted to **U.S. persons**; offshore/outsourced development on ITAR projects is effectively prohibited. Civil penalties up to **$1M/violation**, criminal up to 20 years, debarment.
- **EAR** (Export Administration Regulations, 15 CFR 730–774, CCL): dual-use software — encryption (ECCN **5D002**), intrusion/surveillance software, high-performance computing, cybersecurity tooling — is controlled; license exceptions (e.g., **ENC**) apply but require classification, notification, and records. Civil penalties up to **$300K/violation or 2× transaction value**.
- **Practical consequences for a dev-tool vendor**:
  - Data residency: cannot route CUI/ITAR data through foreign-hosted services; needs **U.S.-only or on-prem deployment**.
  - Personnel: support/engineering staff touching controlled environments may need **U.S.-person or cleared** status.
  - **Cloud AI APIs are a red line**: sending controlled code to a public LLM endpoint (OpenAI/Anthropic/Google consumer tiers) is an unlicensed export. This is why primes deploy **on-prem/air-gapped open-weight models** (Llama at Lockheed Skunk Works, Gemini on Google Distributed Cloud at Lockheed).
  - **ITAR-free positioning is a procurement gate in Europe** (see §6): European programs (BAE, Saab, Leonardo, Airbus DS, Thales, Rheinmetall) increasingly require stacks free of U.S.-export-controlled components for coalition sharing and supply-chain sovereignty. EU controls run through **Regulation (EU) 2021/821** (dual-use, including software and technology), the **EU General Export Authorisations (EUGEAs)** including an encryption EUGEA, and national regimes; **AQAP-2110** (NATO software quality) and **ISO 27001** are baseline procurement requirements for European prime subcontracting.

### 1.4 Air-gapped environments

- Classified work (SIPRNet/JWICS/NSANet, SCIFs) runs on **fully disconnected networks**: no internet, no outbound connections, updates delivered on physical media. "Air-gapped" is also used loosely for **on-prem, no-external-API** commercial deployments (the tier that matters for most unclassified-but-controlled work).
- Deployment tiers that matter commercially: (1) public SaaS, (2) **VPC/tenant isolation + regional data residency**, (3) **on-prem/self-hosted in customer facilities** (CUI, ITAR), (4) **fully air-gapped** (classified). Most defense work AeroSkills would touch sits in tiers 2–3; classified programs need tier 4 (on-prem model weights, offline updates, no telemetry).
- The DoD's own AI-coding-tools solicitation explicitly requires deployment **"within customer-managed cloud environments, on-premise infrastructure, and air-gapped or disconnected networks"** — a template every prime now applies to AI tooling.

---

## 2. AI Coding Agents and LLM Adoption in Defense

### 2.1 DoD demand signal (the macro trend)

- **Feb 2026**: DoD CDAO + Army issued a call for solutions for AI-enabled coding tools for **"tens of thousands"** of military and civilian developers, explicitly naming two modalities — **IDE-based coding assistance** and **CLI-based agentic coding** (multistep terminal processes). Requirements: FedRAMP High, DISA IL5 PA, deployment at scale across desktop/VDI/web, in customer-managed cloud, on-prem, and air-gapped. DoD stated its workforce "lacks standardized, enterprise-wide access to AI-enabled coding tools… commonplace in the commercial sector."
- **Agentic AI is a DoD priority**: Applied AI is a top critical-technology area; CSIAC (2025) published "Agentic AI: Strategic Adoption in the DoD"; the **DIU Thunderforge project** (Scale AI, 2025) brings agentic AI to military planning; Army cyber task forces are building agents to hunt on DoD networks.
- **Governance is forming**: NIST AI 600-1 (12 GenAI risk categories), NIST AI RMF, DoD Responsible AI (RAI) principles, and emerging AI-use-case reporting (AIUC-1 in some states) now apply; buyers will ask vendors to map to these.
- **Policy direction**: DoD Software Modernization Strategy (Feb 2022) → DevSecOps software factories (Platform One/Air Force, Overmatch Software Armory/Navy, etc.), **continuous Authorization to Operate (cATO)**, and 8 new software-engineering work roles in the Cyber Workforce Framework. Coding agents are being bought *into* this software-factory ecosystem, not around it.

### 2.2 Primes building internal AI platforms (the enterprise pattern)

- **Lockheed Martin**: "AI Factory" on NVIDIA DGX SuperPOD — 7,000 engineers/developers, **75,000 employees** using Navigator secure chat, **16,000+ AI agents** built via the Genesis framework since early 2025, 1B+ tokens/week, hundreds of LLM apps; **Llama open-weight models at Skunk Works** for JSE flight simulation training; **Oct 2025: Google Gemini on Google Distributed Cloud in Lockheed on-prem/air-gapped environments**; **Astris AI** (Dec 2024) commercializes the platform; AI Center (LAIC) founded 2021. Quote-worthy outcome: dev environment provisioning went from *weeks to minutes*.
- **Boeing**: 70+ GenAI applications; **Code Assistant** (intelligent code generation in "seconds"); **Boeing Conversational AI** (2023, first enterprise-scale GenAI platform on secure network); **GenAI Academy** trained 8,000 employees, certified 2,600 "super users"; AI co-pilots saving up to 2 hours/day; agentic AI under human supervision is the stated next phase. Data-integrity rule: "no proprietary or regulated information leaves its secure network."
- **Northrop Grumman** initially **blocked ChatGPT** (2023) until vetted — the canonical example of defense's default-close posture toward unvetted AI SaaS.
- **Palantir**: Army Vantage (since 2018; 100,000+ users; 30,000+ datasets; $3.3B unliquidated-obligations found), follow-on **$400.7M/4-yr ($618.9M ceiling) Vantage contract (Dec 2024)**, **$10B 10-year Enterprise Agreement (Jul 2025)**; **AIP (AI Platform)** at all classification levels incl. SCI/SAP; Maven Smart System; OpenAI integration in Vantage; **Anduril–Palantir consortium (Dec 2024)** for edge-to-enterprise AI data pipeline.
- **Google**: **Gemini for Government** (FedRAMP High; DoD IL4/IL5 deployment guidance); classified Gemini deployments on air-gapped SIPR/JWICS (2026); ~3M DoD employees given Gemini agents on unclassified networks; Google Distributed Cloud (air-gapped, on-prem) is the product pattern primes are buying.
- **OpenAI**: DoD contract (2026), per Pentagon CTO; **Anthropic refused classified work and was subsequently placed on DoD's supply-chain risk list (blacklisted, Mar 2026)** — a cautionary tale: in defense, *declining the market gets you designated as risk*.
- **Scale AI**: Thunderforge (DIU contract 2025) — agentic AI for military planning/operations.

### 2.3 What this means for a coding-agent vendor

- The DoD and primes are buying **deployable, compliant coding agents**, not models. The winning architecture: self-hostable models (open-weight or government-licensed), no telemetry, on-prem/air-gapped deployment, FedRAMP-High/IL5-grade infrastructure, audit logging, and **human-in-the-loop guardrails** (agent outputs traced, approval gates) — mirroring the cognitive-guardrail pattern (TDD/DoR/DoD) now standard in agentic software engineering.
- Defense opinion pieces argue agentic coding will compress build times so much that **accreditation/ATO and deployment, not coding, becomes the bottleneck** — i.e., vendors that reduce compliance/deployment friction (pre-approved, composable, CMMC-ready) win.

---

## 3. The Defense Software Landscape: CMMC 2.0, DFARS, Supply-Chain Security

### 3.1 CMMC 2.0 (the certification regime)

- **What**: DoD certification program (32 CFR Part 170, final rule effective **Dec 16, 2024**) verifying contractors protect **FCI** (Federal Contract Information) and **CUI** (Controlled Unclassified Information). Replaced the 5-level CMMC 1.0 with 3 levels:
  - **Level 1 (Foundational)**: 15 basic safeguarding requirements from FAR 52.204-21; annual **self-assessment** + senior-official affirmation in **SPRS**.
  - **Level 2 (Advanced)**: all **110 controls of NIST SP 800-171 Rev 2**; mostly **C3PAO third-party assessment every 3 years** (some contracts allow annual self-assessment); POA&M rules — must score ≥88, deferrable items limited, **5-point controls (MFA, FIPS crypto) not deferrable**, close items within 180 days.
  - **Level 3 (Expert)**: subset of NIST SP 800-172 enhanced controls (DoD-approved parameters); **government-led DIBCAC assessment**; highest-risk programs.
- **Scope**: applies across the whole DIB — primes, subcontractors, and any **SaaS/MSP vendor that stores/processes/transmits CUI**, even two tiers down.
- **Phased rollout of DFARS 252.204-7021**:
  - **Phase 1 — Nov 10, 2025**: L1/L2 **self-assessments** required in applicable solicitations (SPRS submission + annual affirmation).
  - **Phase 2 — Nov 2026**: **C3PAO certification** mandatory for prioritized (high-value) contracts.
  - **Phase 3 — Nov 2027**: **Level 3** requirements activate.
  - **Phase 4 — Nov 2028**: full implementation across all applicable contracts.
  - Primes flow requirements down **ahead of schedule**; vendors are seeing CMMC language in questionnaires now.
- **Costs/timeline**: from a typical commercial posture, **9–18 months** to assessment-ready (scoping 4–8 weeks, remediation 6–12 months, evidence maturation, then C3PAO booking — C3PAO capacity is scarce, book early); C3PAO assessments **$40K–$100K+** for mid-size scope. FedRAMP Moderate authorization is the fast path for SaaS (inheritable controls); **12–18 months is the typical full CMMC compliance journey** for a contractor without it.
- **Enforcement teeth**: ineligible for award without certification; **DOJ Civil Cyber-Fraud Initiative / False Claims Act** actions against contractors who misrepresented compliance (treble damages). ~34% of DIB breaches involve CUI mishandled by third-party SaaS (DCSA 2024). **DFARS 252.204-7012**: breach reporting to DoD within **72 hours**, contractor pays remediation.

### 3.2 DFARS clauses to know

| Clause | Content |
|---|---|
| 252.204-7012 | Safeguarding CUI; 72-hr incident reporting; FedRAMP Moderate (or equivalent) for CSPs; flow-down to subs |
| 252.204-7019 | NIST SP 800-171 assessment score **must be in SPRS** |
| 252.204-7020 | NIST SP 800-171 DoD Assessment Methodology (self-assessment scoring: start 110, −5/−3/−1 per control) |
| 252.204-7021 | **CMMC** level requirement in the contract (phased rollout above) |
| 252.204-7016 | (related) CMMC assessment requirement provisions |

### 3.3 Supply-chain security (the SBOM era)

- CMMC 2.0 assessments now implicitly require **software bills of materials (SBOMs)**, third-party component risk, and **build-pipeline integrity** evidence (NIST SP 800-171 CM/RA/SI families + SP 800-161 SCRM; EO 14028 + OMB M-22-18 push NTIA/CISA-minimum SBOMs). Assessors want *artifacts*, not policy: dependency inventories, vulnerability-scan history tied to builds, remediation tickets (control 3.11.2/3.14.1), SBOM per release.
- **Implication for AeroSkills**: if AeroSkills ships agent skills/packages that touch CUI environments, its own **SBOM, provenance, and dependency hygiene** become buyer evidence. Any package manager / skill-install channel must support **offline, pinned, hashed artifacts** and produce a component inventory — this is a differentiator, not overhead.
- **CSP vs ESP**: under 32 CFR §170.4, a **Cloud Service Provider** (SaaS/IaaS/PaaS storing CUI) must be FedRAMP Moderate authorized (Class C) or equivalent; an **External Service Provider** (manages a tenant) does not carry the CSP FedRAMP burden but still generates assessment evidence. Know which you are in each deal.
- **FedRAMP 20x** (2025+) is streamlining authorization (months → weeks, removing agency-sponsorship for some paths) — watch it; it lowers the bar to becoming defense-sellable.

---

## 4. What an Enterprise Sale to an Aerospace/Defense Org Looks Like

### 4.1 The buyer is a committee

| Role | What they own | What they ask |
|---|---|---|
| **Individual engineer** (champion) | personal productivity, expense-account spend | "does it make me faster on Cameo/DOORS/C++?" |
| **Engineering director / VP Engineering** | team budget, productivity metrics, tool standardization | ROI, adoption depth, integration footprint |
| **Digital engineering / MBSE group lead** | model-based toolchain, digital thread | integration with Cameo/Teamcenter/DOORS, traceability |
| **CTO / Chief Digital & AI officer** | enterprise AI strategy, AI factory/GenAI platform | deployability (on-prem/air-gapped), model governance, roadmap fit |
| **Innovation office / research** | pilot budgets, OTAs, DIU/DIANA channels | speed-to-pilot, small proof contracts |
| **IT director / procurement** | contract, MSA, budget line item | pricing model, vendor onboarding pack, PO/insurance/W-9 |
| **Security architect / FSO / CISO** | compliance gate | SOC 2 Type II, SIG/VSAQ, pen test, subprocessors, data residency, CMMC/FedRAMP posture, audit logs, AI-output ownership clauses |

- In defense the **security architect effectively has veto** — deals die in security review, not in the demo. The GovCon pattern: allocate **4–6 weeks for vendor vetting**; MSA negotiation alone **30–60 days** (liability caps, indemnification, data-residency, audit rights, **AI-output ownership clauses** — now ubiquitous).

### 4.2 Deal sizes and timelines

- **Benchmarks (commercial enterprise, 2025–26)**: enterprise software journeys **6–12 months**; **12–18+ months** for complex/regulated/heavily-integrated; $100K–$500K deals **6–12 months**; **>$1M deals 12–24 months**; regulated sectors (gov, defense, fin, health) sit at the long end; security review adds **4–8 weeks**; internal change management adds **20–30%**.
- **Defense-specific**: prime subcontracting arrangements **12–36+ months** (greenfield programs); EDF (EU) calls **18–36 months**; NATO DIANA / national innovation units **months to ~1 year**; existing IDIQ/enterprise-agreement vehicles can compress to **~12 months** or less. Realistic planning: **6–9 months** for a well-championed team-level deal, **12–18 months** for an enterprise license at a prime, **24+ months** for a DoD-prime strategic deal.
- **Price points that map to the market**: per-seat developer tooling $20–60/seat/mo at the team tier; enterprise commitments at primes typically **$100K–$1M+ ACV** once standardized; AI-platform consumption (tokens/agents) layered on top. Palantir-scale ($400M–$10B) is the extreme end; AeroSkills should plan for **$25K–$250K initial enterprise deals, expanding to $500K+** via seat/agent expansion.

### 4.3 Security questionnaire requirements (checklist to prepare now)

1. SOC 2 **Type II** report (Type I insufficient for most); ISO 27001 as accelerant (~60–70% objective overlap with NIST 800-171).
2. **SIG / VSAQ / CAIQ** responses pre-written; **NIST SP 800-171 crosswalk** (AeroSkills' own posture mapped to the 110 controls).
3. **Penetration test summary** (recent, reputable firm), **subprocessor list**, **data-residency map** (U.S.-only option).
4. **FedRAMP status** (even "in process" + roadmap helps; authorized Moderate = table stakes for DoD-facing SaaS; High+IL5 only for DoD-prime AI deals).
5. **CMMC roadmap** (Level 1 self-assessment now; Level 2 C3PAO path by Phase 2).
6. **Incident response plan** with 72-hour breach notification alignment (DFARS 7012).
7. **SBOM + dependency inventory** for shipped artifacts; **offline/air-gapped installation** documentation.
8. **AI governance**: training-data provenance, no-training-on-customer-data commitments, AI-output ownership terms, NIST AI RMF/600-1 mapping, audit logging for agent actions.
9. **DPA + GDPR** (EU customers), **TCN/foreign-national access controls** (ITAR), **deemed-export** documentation.
10. **Vendor onboarding pack**: W-9, insurance certificates, supplier-diversity data, PO setup — compress procurement by weeks.

---

## 5. The Digital-Engineering / MBSE Wave (Demand Engine for Agent Skills)

### 5.1 Policy and market

- **DoD Digital Engineering Strategy (June 2018)** and **DoDI 5000.97 (Dec 21, 2023)**: digital engineering (MBSE, PLM, CAD, digital twins, digital thread) is now **required to be addressed in acquisition strategy**; applies to new programs after Dec 2023; program managers must plan digital-engineering resources; DoD retains IP rights in models per program IP strategy.
- **Markets**: MBSE market **$4.49B (2026) → $17.77B (2035), 16.5% CAGR**; Defense Digital Engineering market **$9.8B (2024)**; Systems Engineering & MBSE tool market **$1.09B (2025) → $2.17B (2033)**; Digital Twin in A&D **$13.5B (2025) → $31B (2033)**. >72% of engineering orgs report using digital-engineering frameworks.
- **Toolchain**: **Cameo Systems Modeler / MagicDraw** (Dassault, now CATIA Magic), **IBM Rhapsody/DOORS** (IBM ELM), **Capella** (open source, Thales), **Papyrus**, **Simulink**, **Teamcenter/Polarion** (Siemens), **SysML v1 → SysML v2** (machine-readable, executable models; ISO/IEC 19514; Dassault pushing "AI-augmented engineering" on SysML v2), INCOSE 2025 vision. Enterprise integration (Cameo↔Teamcenter↔DOORS/Polarion "digital thread") is a multi-year, multi-$M program of record at primes.
- **Workforce gap is real and measured**: an AI-based competency study mined **1,960 MBSE job postings** (2025, Systems journal) and found a documented industry skill gap; INCOSE and industry report steep learning curves, interoperability pain, and chronic shortage of systems engineers who can model. Certification/credentialing demand is exploding.

### 5.2 Why this creates agent-skill demand

- MBSE is **knowledge-intensive and tool-syntax-heavy**: SysML diagrams, requirement-to-architecture traceability, verification artifacts. LLM/agent tooling is entering exactly here: requirements extraction/NLP, SysML model generation, digital-certification artifact generation (Papyrus/MATLAB and CATIA MSoSA workflows for EASA CS-23), traceability automation, model review — with the caveat that **hallucination makes LLMs unsuitable as the primary requirements mechanism without guardrails** (Dassault's position; agent-driven design validation with human approval is the emerging pattern).
- Defense orgs converting to MBSE need: **skills/training at scale** (GenAI Academy pattern), **domain expertise packaged as tools** (the AeroSkills wedge), and **audit-grade traceability** (CMMC/SBOM-adjacent). Agent skills that encode aerospace domain knowledge (airworthiness regs, MIL-STDs, SysML patterns, DO-178C artifacts, engineering standards) directly serve the "digital engineering culture and workforce enablers" goal in the DoD strategy.

---

## 6. Realistic Path: Land-and-Expand + Defense GTM Strategy for AeroSkills

### 6.1 The land-and-expand ladder in defense

1. **Individual engineers (expense accounts / self-serve)** — works only in **non-cleared, internet-connected** areas of primes and their suppliers: tool evaluation via personal cards or small POs. This is the discovery wedge; expect **shadow-IT discovery** by security within months (GTM Labs: security flags SaaS on the network; be ready to convert).
2. **Team pilots** — engineering director funds a pilot on program budget; requires: working pilot with measurable developer outcomes (adoption-depth report: users, feature depth, longevity), ROI estimate, enterprise-readiness pack (SOC 2, SSO, audit log, SLA). Trigger for an AE: **5+ users or multi-team usage inside one account**.
3. **Standardization / enterprise license** — CIO/VP Eng makes it a standard (not a "sanctioned exception"); unlocks seats, modules, multi-year terms. The political question: which incumbent toolchain does AeroSkills displace? Removing reasons to say no (security packet, template MSA, onboarding playbook) is the job.
4. **Program/prime-wide deployment** — via digital-engineering groups, AI Factories, or software factories; requires CMMC/FedRAMP-grade posture, on-prem/air-gapped deployment, and a named exec sponsor (CTO/CDO/AI Factory lead).

### 6.2 Defense-specific realities that reshape the ladder

- **Bottom-up is structurally blocked in cleared/air-gapped environments** (every tool needs IT pre-approval before install) — there, an enterprise AE motion is required from the start; bottom-up works in the "commercialized" parts of primes (their enterprise IT, R&D labs, suppliers).
- **Prime-approved catalogs are the real gate**: get on the approved-tool list early (VSAQ + SOC 2 + FedRAMP-in-process + CMMC roadmap), or every champion effort dies at exception-request review.
- **Timing advantage**: CMMC Phase 2 (Nov 2026) forces ~220,000 DIB companies to rebuild software posture — they will buy compliant tooling in 2026–2028. AeroSkills arriving with a **CMMC-ready posture and SBOM'd skill artifacts** rides the compliance wave; primes are also actively *reducing* approved-vendor friction for tools that prove compliance.

### 6.3 Recommended defense GTM strategy

**Positioning**: "Aerospace-domain agent skills that run **on your network** — on-prem, air-gapped-capable, ITAR-safe, with audit-grade traceability." Dual-use framing (civil aerospace + defense) for EU; **ITAR-free** architecture (no U.S.-export-controlled components in the skill runtime) for European/coalition deals; U.S.-only data path for U.S. primes.

**Product/compliance to-dos (pre-sales gate)**
1. SOC 2 Type II + ISO 27001; NIST SP 800-171 crosswalk; CMMC Level 1 self-assessment **now**, Level 2 C3PAO path by late 2026.
2. FedRAMP Moderate (or documented equivalency) for any cloud component; **FedRAMP High + IL5** only when chasing DoD-prime AI deals; always offer **on-prem/air-gapped** deployment with offline update + pinned/hashed skill artifacts + SBOM.
3. Pre-write: SIG/VSAQ responses, pen-test summary, subprocessor list, DPA/GDPR, AI-output ownership terms, IR plan with 72-hr notification, template MSA (30–60-day negotiation compressed).
4. U.S.-person support option; no-training-on-customer-data guarantees; agent audit logging + approval gates (human-in-the-loop).

**Channels**
- **Bottom-up**: engineers inside primes' commercial divisions + tier-2/3 suppliers (Boeing IT, Lockheed enterprise, Airbus, Saab, Leonardo civil units); conference/community presence in MBSE/systems-engineering (INCOSE events, PLM/ALM ecosystems).
- **Top-down**: digital-engineering offices and **AI Factory / GenAI platform leads** at primes (Lockheed Astris AI, Boeing Digital & AI, RTX, GE Aerospace); innovation offices with OTA/DIU/DIANA budgets (months-long cycles); NATO DIANA and EU EDF consortia for European funding + credibility.
- **Ecosystem plays**: integrate alongside **Cameo/MagicDraw, DOORS, Teamcenter, Polarion, Capella** (their consultancies and value-added resellers sell training + skills); partner with CMMC/FedRAMP compliance consultancies that already own the buyer's security conversation; position for **software-factory** ecosystems (Platform One, Overmatch) where DoD buys tooling centrally.

**Metrics/sequencing (24 months)**
- Months 0–6: compliance artifacts; 10–20 design partners (engineers + digital-engineering groups); first team deals ($25–75K).
- Months 6–12: 3–5 prime or top-tier-supplier enterprise deals ($100–250K); FedRAMP/CMMC milestones; ITAR-free + on-prem GA.
- Months 12–24: standardization wins at 2–3 primes (multi-year, $500K+); European channel via prime subcontracting + EDF/DIANA; CMMC Phase-2 wave capture.

**Risks**: 18-month sales cycles burn runway (fund accordingly); security veto is binary (one missing artifact kills deals — build the pack before the demo); AI-hallucination concerns in MBSE demand guardrails and traceability as core product claims; model/copyright and AI-output-ownership terms are new and negotiated per deal; Anthropic's blacklisting shows refusing the defense market has commercial consequences — commit to a clear defense policy early.

---

## Sources (selected)

- DoD CMMC Model Overview v2.13 & Assessment Guide L2 (dodcio.defense.gov); 32 CFR Part 170; DFARS Subpart 204.75 & 252.204-7012/7019/7020/7021 (acquisition.gov)
- DefenseScoop (2026-02-26): "DOD wants AI-enabled coding tools for tens of thousands of users"
- DoD Software Modernization Strategy (Feb 2022) + FY25-26 Implementation Plan; DoD Enterprise DevSecOps Strategy Guide; AAF Software Acquisition Pathway (DAU); March 2025 acquisition-preference memo (OT/CSO default)
- DoDI 5000.97 Digital Engineering (Dec 2023); 2018 DoD Digital Engineering Strategy
- Reuters / Army.mil (2025-07-31): Palantir $10B Enterprise Agreement; Defense One (2024-12): Vantage follow-on; Palantir Army Vantage page
- Lockheed Martin (NVIDIA case study; Google Public Sector release 2025-10-29; Astris AI); Boeing Innovation Quarterly (2025-12) "Shaping AI for the Sky"; HR Brew (2023): Northrop ChatGPT block
- Google Cloud: Gemini for Government deployment guidance; NeuralWired/LetsDataScience (2026): Google classified Gemini deal, OpenAI DoD, Anthropic blacklisting
- GovCon ProposalEngine (2026-07): defense software vendor vetting, FedRAMP floor, CMMC SaaS stats; DCSA; Deltek FedRAMP/CMMC; WM-Synergy FedRAMP ERP; The Defense Compliance Report CSP/ESP; Safeguard.sh CMMC series; VSO/Winston & Strawn/Delve CMMC phased rollout
- ITAR/EAR: Safeguard.sh export-control software guide; Aaron Hall (US export control triggers); EU Regulation 2021/821 (EUR-Lex); EU Commission dual-use guidance; Corvus Intelligence defense-procurement guide (EDF/DIANA timelines, ITAR-free, AQAP-2110)
- GTM Labs "Selling Developer Tools to Enterprise IT"; Above the API PLG-to-enterprise playbook; Abmatic ABM for DevTools; Gain/Prospeo/Pedowitz enterprise sales-cycle benchmarks
- MBSE market reports (Business Research Insights; Growth Market Reports; Verified Market Reports); MDPI/Systems MBSE competency study; HCLTech Cameo-Teamcenter case; Dassault SysML v2; Visure LLMs-in-systems-engineering; Colab AI-for-MBSE; CSIAC Agentic AI in DoD (2025); The Defense Post (2026-06) agentic software development

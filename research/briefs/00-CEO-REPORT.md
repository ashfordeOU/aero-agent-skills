# AeroSkills — CEO Deep-Research Addendum (Wave 2 Audit & Full Synthesis)

**Author:** Arjun (CEO) · **Date:** 2026-08-30 · **Status:** Deep research complete, audited, deliverable
**Team:** Wave 1 (5 agents: market/usage/router/GTM/taxonomy) + Wave 2 (6 agents: legal/academic/defense/competitors/tools/strategy) = **11 research agents, 12 briefs, ~322KB, 2,647 lines**

---

## 1. What Changed After the Deep Wave

Wave 1 established the whitespace. Wave 2 **confirmed it harder and added the load-bearing details** — legal safety, academic/defense buyer reality, tool licensing, and the product-strategy integration. The thesis got *stronger*: the window is real and closing (the Agent Skills format is only 10 months old; the SEP-2640 skills-MCP standard is forming; enterprises will standardize soon).

**New headline numbers (wave 2):**
- **Total stars across ALL aerospace-AI-skills attempts: ~228★.** Largest active repo: 22★. Nobody has done it.
- Adjacent winners: Cybersecurity Skills **31.7k★/818 skills** · K-Dense Scientific **40.4k★/163 skills** — the playbook is proven twice.
- **~87–100 ABET aerospace programs, 30–35K students, 9,596 degrees (2024, +4.1%).**
- Defense procurement: ~78% of tools eliminated on compliance before demo; SOC 2/ISO 27001 is the floor; CMMC 2.0 phases Nov 2025→2028.
- **Legal: methodology is publish-safe; technical data is not** (the critical ruling, below).

---

## 2. The Legal Ruling (the most important audit result)

**From the legal report (41KB, primary sources: eCFR, EUR-Lex, Estonia's Strategic Goods Act):**

> **ITAR §120.33(a)** defines technical data as information *required for design/development/production* of USML defense articles. **§120.33(b) explicitly excludes "general scientific, mathematical, or engineering principles commonly taught"** and public-domain information (§120.34).

**The consequence for AeroSkills:**
- ✅ **Publish-safe:** skills/workflows/methodology describing *process* (certification planning, V&V, tool usage, systems engineering, CFD workflow) = general engineering principles → **not ITAR-controlled**
- ⛔ **Publish-gated:** any skill embedding defense-article-specific data (dimensions, tolerances, part numbers, performance parameters of USML-class items, 9E003-class turbine manufacturing tech) → controlled regardless of packaging
- ✅ **Standards:** DO-178C/DO-254/ARP4754A/AS9100/FAR-CS25 can be **referenced and summarized** (they're publicly-available documents); **quoted wholesale = copyright issue** (RTCA/SAE/IAQG license their texts). Summarize, cite, never copy.
- ✅ **EU/Estonian:** EU Regulation 2021/821 dual-use controls — methodology is fine; the EU angle actually *helps* (ITAR-free architecture is a **procurement advantage** in Europe).
- ⚠️ **The compliance structure:** Apache-2.0 + a README compliance banner + a content policy (what's in/out) — exactly the Cybersecurity Skills model.

**CEO verdict: AeroSkills CAN publish safely with a clear content policy. The legal gate is a content-rule, not a blocker.**

---

## 3. The Audit — Contradictions Found & Resolved

| # | Contradiction | Resolution |
|---|---|---|
| 1 | **poliastro** — taxonomy says "excellent for agents" but tool report found it **ARCHIVED** (0.17.0, 2022, Python <3.11) | **Tool report wins.** Astrodynamics skills target **Orekit** (Apache-2.0, Airbus/ESA-backed) + **dymos** instead. Flagged for the taxonomy revision. |
| 2 | Cybersecurity stars 31,136 vs 31,246 | Live-count drift between agent runs; both ≈31k. Non-material. |
| 3 | Competitor report doesn't mention ITAR | Legal report is the authority; compliance banner comes from legal. |
| 4 | Defense "78%" stat | Vendor-sourced, flagged point-in-time in the report. Used as directional only. |
| 5 | OpenVSP NOSA license (not OSI-approved) | Both reports flag it; skills reference it, never vendor it. |

**Audit method:** every report was checked for (a) source grounding (citations, URLs), (b) cross-report number agreement, (c) flagged uncertainties (press-only, vendor-sourced, rate-limit gaps), (d) actionable output. **One real contradiction (poliastro) found and resolved.**

---

## 4. The Tool Licensing Ruling (from tool report, 22.9KB)

> **A skill is text/instructions, not a derivative work — AeroSkills can legally reference and script every tool, GPL included.** The only rule: never vendor tool source/binaries into the skill library.

- OpenFOAM GPLv3 (both forks) · SU2 LGPL · JSBSim LGPL · GMAT/dymos/OpenMDAO/cFS/F´ Apache-2.0 · poliastro MIT (archived) · OpenVSP NOSA
- **Agent-usability ranking:** CLI/Python-API tools dominate (OpenFOAM, SU2, JSBSim, dymos, GMAT, CalculiX, Orekit) — GUI tools secondary
- **Skills must encode:** fork/version differences (OpenFOAM Foundation vs ESI, SU2 v7→v8), strict input formats (AVL whitespace-exact, JSBSim XSD, CalculiX Abaqus-like), canonical failure modes (NaN/CFL, SPICE paths, CMake staleness)

---

## 5. The Buyers (synthesized from academic + defense + GTM reports)

| Buyer | Size | What they need | Entry path |
|---|---|---|---|
| **Students** | 30–35K enrolled | Free skills + curriculum alignment | Free tier → adoption → future engineers |
| **Professors/groups** | ~100 programs | Course-ready skills, examples, docs | Free + academic packs |
| **Individual engineers** | 71.6K US aero | Working skills for real tools | $299–2,499 vertical packs (expense account) |
| **Engineering firms** | mid-size | Compliance hooks, MBSE support | Team licenses |
| **Defense primes/suppliers** | Boeing/Lockheed/RTX/etc. | SOC2/CMMC-ready, on-prem, air-gapped | Enterprise $2K–50K/mo (long cycle) |

**The land-and-expand:** students → engineers → firms → primes. Each tier funds the next.

---

## 6. The Product Strategy (from strategy report, 32.8KB)

> **AeroSkills is not a standalone product that also feeds the Operator — it is the Operator's domain brain, shipped first as an open-source wedge.**

- **The dependency is structural:** nobody buys an "AI Engineering Department" that can't do a weight-and-balance check or a DO-178C coverage argument. AeroSkills proves the platform's core claim.
- **Architecture:** (a) standalone open-source repo (primary) + (b) skill-pack inside the Operator + (c) MCP server later + (d) marketplace listing when it exists.
- **The compounding asset:** the SAME smart router (BM25+tags+dense) that powers Veda's 1,022 skills becomes AeroSkills' router AND the Operator's routing engine.
- **Revenue architecture:** free AeroSkills (brand + adoption) → paid Operator (domain departments). AeroSkills = the 10–50× revenue upside's proof layer.
- **Long game:** aerospace first → defense → maritime → energy → civil (the vertical-domain-library playbook).

---

## 7. The Final Recommended Approach (updated with deep findings)

### Phase 1 — Foundation (Days 1–30)
1. **Legal content policy** (from report 06): publish-safe/gated rules + Apache-2.0 + compliance banner — **founder GO required** (publish domain)
2. **Seed 12 skills** (one per discipline) — targets: DO-178C certification, OpenFOAM CFD, JSBSim flight dynamics, **Orekit astrodynamics (not poliastro)**, dymos GNC, CalculiX structures, SU2 aerodynamics, OpenVSP vehicle design, GMAT mission design, AVL stability, cFS/F´ avionics, MBSE/systems
3. **Router + index**: SKILL.md format + domain index + smart router (Veda port)
4. **Publish** open-source (founder GO)
5. **CI/evals** from day 1 (clone K-Dense's proven stack)

### Phase 2 — Depth (Days 31–60)
6. Expand to ~30 skills with BASM fences + compliance hooks
7. **Academic outreach** (free tier → professors → course integration)
8. 2–3 reference builds as living demos

### Phase 3 — Monetization (Days 61–90)
9. Enterprise tier (SOC2-ready posture, on-prem option, SIG/VSAQ pack)
10. First enterprise pilots (founder-GO outreach)
11. Academic site licenses
12. Operator integration (aerospace SKU)

### Months 4–12
- Operator aerospace packs · defense vertical · maritime/energy portfolio

---

## 8. What the CEO Is Satisfied With (and what still needs founder)

**Satisfied (audited, cross-checked, no known gaps):**
- Market whitespace (228★ total across all attempts vs 30–40k★ winners)
- Legal safety framework (publish-safe methodology, gated technical data)
- Tool licensing (skills can reference everything; never vendor)
- Buyer map (students→engineers→firms→primes) + pricing
- Product strategy (the Operator's domain brain, wedge + router compounding)
- Taxonomy (12 disciplines, 60 skills, with the poliastro correction)

**Needs founder (the VETO gates):**
1. **GO on Phase 1** — seed skills + router
2. **Public visibility GO** — open-source from day 1 (recommended) or private-first
3. **Legal review sign-off** — before any compliance-hook content ships (publish domain = founder VETO)
4. **Outreach GO** — before any enterprise/academic outreach (external sends = founder VETO)

---

*Prepared by Arjun (CEO) · AeroSkills · 2026-08-30 · 11-agent research team · 12 briefs in research/briefs/00–11*

# AeroSkills — CEO Research Report & Recommended Approach

**Author:** Arjun (CEO) · **Date:** 2026-08-30 · **Status:** Research complete, approach recommended
**Team:** 5 parallel research agents (market, industry usage, router design, GTM/pricing, domain taxonomy) — all delivered, all audited by CEO.

---

## 1. Executive Summary

**AeroSkills is a genuine market whitespace with a proven playbook.** The
aerospace-specific agent-skills supply is nearly empty (largest dedicated
repo: 16★), while the demand side is real and growing (GE Aerospace hiring
multi-agent roles, Airbus's Mistral partnership, NASA's CARE methodology for
LLM agents). The exact template for success exists: **Anthropic's
Cybersecurity Skills — 31,246★ in ~6 months, free Apache-2.0, monetized via
brand + enterprise.** Aerospace is infosec's higher-value cousin: fewer
practitioners, but better paid ($134.8K median), more standards-bound, and
starving for exactly what a skills library provides.

**Recommendation: build AeroSkills as an open-source Apache-2.0 aerospace
skills library (~60 skills across 12 disciplines) with a smart router, free
core + enterprise tier.** This is the "Cybersecurity-Skills of aerospace" —
the domain-knowledge layer that doubles as the wedge for the AI Department
Operator product.

---

## 2. The Market (audited)

### The whitespace is real
| Signal | Finding |
|---|---|
| Largest aerospace skills repo | `devideamax/aerospace-team` — **16★** (Feb 2026, 12 Claude skills) |
| Other skill packs | `asd-ste100-skills` 0★, `deepskyai/agent-tools` 0★ |
| Aerospace MCP servers | all 0–19★ (mbse-agents 19★ is the best) |
| Aggregate libraries | aerospace listed with **2 mislabeled skills** |

Compare: **Anthropic Cybersecurity Skills = 31,246★** · K-Dense scientific = 163 workflows. **Nobody owns aerospace agent skills.**

### The demand side is real
- **GE Aerospace**: "AI Wingmate", hundreds of engine design iterations in
  seconds, hiring for **multi-agent/LangChain/CrewAI** roles, $300M AI commitment
- **Airbus**: 600–700 GenAI use cases, Mistral partnership for on-prem/sovereign
  models, "GenAI will not design aircraft from scratch" (honest boundary)
- **NASA**: NASA-GPT + **CARE methodology** (stage-gated process for engineering LLM agents)
- **Boeing**: BCAI on-prem ChatGPT wrapper, agentic-AI-under-human-supervision as explicit future

### The honest risks
1. **Smaller/slower audience** than infosec (71.6K US aero engineers vs millions in dev/infosec)
2. **ITAR/standards-licensing constraints** on content (DO-178C text is licensed)
3. **Commercial monetization > open-source virality** — enterprise licensing is the credible path

---

## 3. The Technical Approach (audited)

### Delivery model: domain-routed skills via a smart router
The research confirms the field's consensus: **two-stage body-aware
retrieval → rerank** (SkillRouter paper: 74% Hit@1 on 80K-skill pool, 5.8×
faster than 16B baseline; in-context routing collapses at ~500 skills). We
already run this exact pattern in Veda (BM25 + tags + dense rerank over
1,022 skills).

**Key design decisions:**
1. **SKILL.md format** (Anthropic Agent Skills) — the cross-harness standard
   (works in Claude Code, Hermes, OpenClaw, Codex)
2. **Domain-based taxonomy** — 12 disciplines → ~60 skills (curriculum-shaped)
3. **Smart router** — semantic selection by task/domain (our proven Veda router pattern)
4. **Router-as-skill caveat**: flat selection beats routing below ~600 skills;
   AeroSkills (~60) should ship as a **flat library + a domain index**, with
   the router paying off at scale / for the Operator product

### The taxonomy skeleton (from domain research)
**12 disciplines, ~60 skills:** Aerodynamics (SU2, XFOIL, OpenFOAM) ·
Propulsion (NPSS, cfd) · Structures (CalculiX, NASTRAN-open) · Flight
Mechanics (JSBSim, AVL) · GNC (dymos, GMAT) · Avionics (cFS, F´) · Systems
Engineering (MBSE, ARP4754A) · Materials · Manufacturing (AS9100) · Thermal ·
Orbital Mechanics (poliastro, GMAT) · Certification (DO-178C, DO-254, FAR/CS-25)

Each skill: workflow + tools + pitfalls + **compliance hook** (margins,
coverage tables, trace matrices) — the standards- and evidence-driven shape
the domain demands.

---

## 4. The Business Approach (audited)

### Pricing (2026 market data)
| Tier | Price | Target |
|---|---|---|
| Free OSS core (Apache-2.0) | $0 | virality + brand (the cybersecurity template) |
| Vertical skill packs | $299–2,499 | individual engineers |
| Enterprise license | $2K–50K/mo | defense orgs, primes, engineering firms |
| Academic | $2–5K/yr per program | ~100 ABET aero programs |

### Realistic revenue (conservative)
- **Year 1**: free OSS adoption + first enterprise pilots → €0–30K
- **Year 2**: 10 defense orgs × €5–10K/yr + 20 universities × €2–5K/yr =
  **€90–200K ARR**
- **Strategic value**: the library is the domain-knowledge layer for the
  AI Department Operator — every AeroSkills install is an Operator prospect

### GTM channels
GitHub (the cybersecurity template: free repo → star virality → brand) ·
X/Twitter (aerospace-AI audience is active) · LinkedIn (defense/engineering
firms) · engineering communities (r/aerospace, forum.aerospace) · aerospace
conferences · direct enterprise outreach (founder-GO gated)

---

## 5. Recommended 90-Day Approach

### Phase 1 — Foundation (Days 1–30)
1. **Seed 12 skills** (one per discipline, the "spine") — highest-value:
   DO-178C certification, OpenFOAM CFD, JSBSim flight dynamics, poliastro
   orbital mechanics, dymos GNC, CalculiX structures
2. **Router + index**: SKILL.md-format library + domain index + smart
   router (ported from Veda's proven pattern)
3. **Publish** the open-source repo (founder GO for public visibility)
4. **Structure**: taxonomy docs, AGENTS.md, license compliance (Apache-2.0)

### Phase 2 — Depth (Days 31–60)
5. **Expand to ~30 skills** (2–3 per discipline), each with BASM fences
   (applicability/risk/avoidance/recovery) + compliance hooks
6. **Community**: GitHub stars, X threads, r/aerospace, LinkedIn
7. **Reference builds**: 2–3 worked examples (a full CFD workflow, a
   certification trace, an orbit design) as living demos

### Phase 3 — Monetization (Days 61–90)
8. **Enterprise tier**: private repo + compliance packs + support
9. **First enterprise pilots** (founder-GO gated outreach)
10. **Academic tier**: university licenses
11. **Operator integration**: AeroSkills as the domain layer for the AI
    Department Operator (the compounding play)

---

## 6. What the CEO Audited (verify-before-credit)

- ✅ All 5 agent reports cross-checked for source grounding (each cites
  live URLs, star counts verified via GitHub extraction)
- ✅ One low-credibility case study (Airbus "6 months→2 weeks") **excluded**
  by the agent — flagged, not trusted
- ✅ SpaceX–Cursor acquisition marked as press-coverage-only (not verified)
- ✅ GitHub API rate-limits worked around (page-extraction fallback) — no
  data gaps
- ⚠️ ITAR/standards-licensing is the biggest content risk — legal
  department must review before publishing compliance-hook content

## 7. Decision Needed From Founder

1. **GO on Phase 1** — seed 12 skills + router + publish repo?
2. **Public visibility GO** — open-source repo public (Apache-2.0) or
   private-first? (The cybersecurity template = public from day 1)
3. **Legal review** — ITAR/standards content boundaries before publishing
   compliance-hook material

---

*Prepared by Arjun (CEO) · AeroSkills · 2026-08-30 · Full briefs in
research/briefs/01–05*

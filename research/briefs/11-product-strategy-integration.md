# AeroSkills — Product-Strategy Integration with the AI Department Operator

**Research date:** 2026-08-30 · **Scope:** how AeroSkills slots into the AI Department Operator platform (the "domain brain"), the wedge strategy, architecture options, the shared router asset, revenue architecture, and the vertical-library long game.
**Status:** complete — builds on briefs 01–05 (market, industry, router, GTM/pricing, taxonomy) and Veda internal doctrine (Department-as-Code).

---

## 0. Executive Summary

AeroSkills is not a standalone product that *also* feeds the Operator. It is the **domain-knowledge layer of the Operator**, shipped first as an open-source wedge because that is the fastest, cheapest way to (a) prove the Operator's core thesis — agents with real domain skills outperform generic agents — and (b) build the trust that enterprise aerospace/defense buyers require.

The architecture conclusion is a **four-surface combination, one spine**:

- **Spine:** filesystem-first SKILL.md library, Apache-2.0, standards-mapped (DO-178C/DO-254/ARP4754A/AS9100) — the open agentskills.io format gives free portability across every agent host.
- **(a) Standalone OSS repo** — the wedge, the brand, the funnel top (the Anthropic-Cybersecurity-Skills play: 31,700★ in ~6 months, free, monetized around it).
- **(b) Operator domain packs** — the monetization: the same library packaged as an "Aerospace Engineering Department" inside the Operator, with role charters, budget ledgers, schedules, and verification gates.
- **(c) MCP server** — the enterprise/air-gapped delivery adapter (metadata listing + `get_skill`), never the source of truth.
- **(d) Marketplace listings** — distribution amplifiers (Anthropic Marketplace 85/15, SkillExchange, etc.), near-zero marginal cost.

The **smart router (BM25 + tags + dense rerank, body-aware)** is the compounding asset: one codebase already proven at Veda over 1,022 skills becomes the AeroSkills router at ~60–600 skills, then the Operator's skill-routing engine across *all* domain libraries (aerospace → defense → maritime → energy → civil). Every new library improves the router; the router makes every new library usable. This is the moat.

Revenue thesis: **free AeroSkills is the loss-leader that converts at the enterprise tier and the Operator.** Dev-tools free→paid conversion averages 11.7% at $187/mo ARPU; vertical SaaS ARPU $324/mo; enterprise skill licensing $2K–50K/mo. Realistic path: €0–30K (Y1) → €90–200K ARR (Y2) → €0.5–1.5M ARR (Y3) as the Operator domain-department SKUs take over from standalone licensing.

---

## 1. The AI Department Operator and where the domain brain fits

### 1.1 The concept (the locked trinity)

The product line is three layers of one idea, already validated by Veda's live operation (25 agent profiles / 24 departments, 2 cron jobs, 140+ managed skills + 818 cyber playbooks, knowledge graph 261 nodes / 1,107 edges):

| Layer | What it is | Audience hook |
|---|---|---|
| **AI Department Operator** | The *role*: a human who runs a company as AI departments instead of hiring a team. Judgment + approvals held by the human; execution by agents. | Founders |
| **Department-as-Code** | The *method*: the org chart as versioned, executable config. A department is a folder — `README.md` (mission), `AGENTS.md` (rules), `skills/` (procedural memory), `agents/` (role briefs), `schedules.cron`, `evidence/` (proof), `reports/` (approval surface). | Engineers |
| **Agent Org Charts** | The *artifact*: the company as a living graph of agents + humans. Veda's knowledge graph is the reference implementation. | Executives |

The market context (from the 2026-08-28 competitive scan): agent *frameworks* are crowded (LangGraph, CrewAI, AutoGen/AG2, Google ADK, OpenAI Agents SDK, Claude Agent SDK/Agent Teams, FrontierAgent ~1,149★/6d), but **none ship org-chart + governance together**. Governance-layer funding is real ($101.5M in 2026 into Convey/Sapiom/Naive; SuperOrgs $500/mo; Chartav $99/mo; Paperclip OSS 67–79K★; halofy 446★/7d governance layer) — the category is forming and the governance+structure wedge is still open. Deloitte's 2026 A&D outlook confirms agentic AI is "reshaping A&D" but adoption is "uneven and early" — which is exactly where a standards-bound domain library lands hardest: it de-risks the agentic-AI purchase for a regulation-heavy industry.

### 1.2 The "domain brain": skills are the department's procedural memory

In the Department-as-Code model, a department's competence = its `skills/` folder. Skills are not documentation; they are **operating procedure**: workflow + tools + pitfalls + evidence gates, triggered by description, loaded on demand (progressive disclosure). A department without domain skills is a generic agent with a title; a department *with* them is a credible specialist.

AeroSkills is the **aerospace domain brain** for the Operator:

- **What it encodes:** the 12 disciplines (aerodynamics/CFD, propulsion, structures, flight mechanics, GNC, avionics, systems engineering/MBSE, materials, manufacturing/AS9100, thermal, orbital mechanics, certification) — ~60 skills, each with workflow + tool-driving (OpenFOAM, SU2, JSBSim, poliastro, dymos, CalculiX, cFS, F´…) + pitfalls + **compliance hooks**.
- **Why compliance hooks are the differentiator:** aerospace is standards- and evidence-driven. A skill that produces a number without a validation/compliance step is useless. Every AeroSkills skill carries margins, coverage tables, DAL-level awareness (A–E), trace matrices — the shape the domain demands. This is the "proof-of-quality" that no competitor has and that enterprise buyers can verify.
- **The recursive proof:** AeroSkills itself runs as a Department-as-Code company (9 departments, AGENTS.md, one main branch, evidence gates) — the product is dogfooded from day 1, which is the Operator's own selling point demonstrated publicly.

### 1.3 The dependency is structural, not cosmetic

The Operator's value proposition — "run your engineering department as agents" — is empty without domain competence. Nobody buys an "AI Engineering Department" that can't do a weight-and-balance check or a DO-178C coverage argument. AeroSkills is not an optional add-on to the Operator; it is **the reason the Operator's aerospace SKU is credible at all**. Conversely, AeroSkills standalone caps at enterprise-licensing revenue (€90–200K ARR realistic Y2); the Operator is the 10–50× upside (see §5).

---

## 2. The wedge strategy: open-source library as top-of-funnel and proof-of-quality

### 2.1 The template: how cybersecurity built Anthropic's enterprise credibility

The path is now well documented and multi-layered:

1. **Free open-source skills → practitioner trust.** `Anthropic-Cybersecurity-Skills` (818 skills, 34 domains, mapped to MITRE ATT&CK, NIST CSF 2.0, ATLAS, D3FEND, AI RMF) hit **31,700★ / 3,818 forks in ~6 months**, Apache-2.0, monetized only via brand + consulting + adjacent products. Framework mapping (the compliance hook) is the credibility engine: "one skill, five compliance checkboxes."
2. **Free product → enterprise product.** The same domain competence became **Claude Security** — Mythos-5-powered codebase scanning, "public beta for Claude Enterprise," findings with CWE + confidence + suggested patches, adversarial verification pass, human-approval gates. This is the pattern: *free skills prove the capability, paid product packages it with governance.*
3. **Practitioner credibility → CISO/board credibility.** Anthropic's CISO guide to agentic AI, the Zero Trust for AI Agents white paper, and the "how Anthropic's own security team uses Claude" (CLUE platform) narrative converted the security community into enterprise door-openers. Deputy CISO-authored frameworks are the enterprise entry ticket.
4. **Ecosystem programs → institutional legitimacy.** Project Glasswing (hardening critical open-source software, partnered with AWS, Microsoft, Linux Foundation), the $35M Defender Advantage Fund, the Cyber Verification Program. Open-source security work became Anthropic's enterprise *identity*, not a marketing sidebar.
5. **Partner distribution → revenue.** Snowflake Cortex AI embedding Claude for "cybersecurity investigations, financial analysis" — partners sell the domain capability into governed enterprise environments.

**The transferable law: in domain-heavy industries, the open-source library is the proof-of-quality document; the enterprise product is the governance wrapper around the same capability; the C-suite (CISO/CTO/Chief Engineer) is reached through the practitioners the library already won.**

### 2.2 The aerospace translation

AeroSkills is the same play with a different domain and a *higher-value* buyer:

| Cybersecurity (Anthropic) | Aerospace (AeroSkills) |
|---|---|
| MITRE ATT&CK / NIST CSF mapping | **DO-178C / DO-254 / ARP4754A / AS9100 / MIL-STD-881 mapping** |
| Free 818-skill library → 31K★ | Free ~60-skill library → target 2–10K★ (smaller audience, higher per-user value) |
| Claude Security (enterprise product) | **Operator Aerospace Engineering Department** (enterprise product) |
| CISO guide → CISO credibility | **Chief Engineer / Head of Digital Engineering guide** → engineering-leadership credibility |
| Glasswing / Defender fund → ecosystem | **AIAA SciTech presence, academic program, standards-body liaison** |
| Snowflake/CrowdStrike partners | **MBSE tool vendors (Cameo/SysML), open-tool ecosystem (OpenFOAM, JSBSim), primes' digital-engineering groups** |

Why this works *better* for aerospace: the audience is smaller (71.6K US aero engineers vs millions in infosec) but better paid (median $134.8K/yr), more standards-bound (every workflow must end in a compliance hook), and currently **unserved** — the largest existing aero skills repo (devideamax/aerospace-team) has 21★. The demand side is live: GE Aerospace ("AI Wingmate," multi-agent hiring, $300M AI commitment), Airbus (600–700 GenAI use cases), NASA (CARE methodology for engineering LLM agents), Boeing (agentic-AI-under-human-supervision as explicit future). The whitespace is the wedge; the wedge is the proof.

### 2.3 The funnel mechanics

```
Free OSS library (GitHub stars, adoption)
   → proves quality: standards mapping + reference builds + real tool output
   → captures leads: newsletter, enterprise-intent signals (air-gapped/MCP requests)
   → converts: Pro packs → enterprise license → Operator Aerospace Department
   → compounds: every install is a future Operator prospect
```

Key numbers (from brief 04): OSS stars 2K–10K ≈ $800–5,000/mo passive; 10K+ ≈ $3–15K/mo; dev-tools free→paid conversion 11.7% median with $187/mo ARPU after conversion; vertical SaaS ARPU $324/mo; security-software ARPU $487/mo; solo founders with a niche audience made $1,400–8,483 in their first month selling vertical skills (Q1 2026). AeroSkills' realistic organic baseline: 500–2,000★ in 90 days, €2–5K MRR in 3 months, €10K MRR in 6–9 months with founder-led enterprise outreach — and each of those enterprise conversations is a **domain-department (Operator) conversation** by the time the platform exists.

---

## 3. Product architecture options

### 3.1 The four surfaces compared

| Option | Mechanics | Strengths | Weaknesses | Verdict |
|---|---|---|---|---|
| **(a) Standalone OSS repo** | Filesystem SKILL.md library, Apache-2.0, `npx skills add`, install into Claude Code/Hermes/OpenClaw/Codex | The wedge: zero-friction adoption, portability everywhere, star virality, enterprise proof-of-quality; the cybersecurity template | No direct revenue; piracy of file-based content; needs ongoing authoring discipline | **PRIMARY (the spine)** |
| **(b) Skill-pack inside the Operator** | Same skills, packaged as domain departments: role charters, budget ledgers, schedules, evidence gates, approval workflow | Monetization: the Operator is where domain knowledge becomes a *system*; per-department SKUs; governance is the enterprise purchase | Depends on Operator maturity; no standalone buyer yet | **MONETIZATION (phase 2)** |
| **(c) MCP server** | Metadata listing + `search_skills`/`get_skill` tools, following aeroastro.org Aerospace MCP pattern; files remain source of truth | Multi-client, programmatic, centralized updates, auth/permissions; enterprise/air-gapped delivery; the Skills-over-MCP WG (SEP-2640) is standardizing this | MCP still stabilizing; tool-list bloat reintroduces selection problem; ecosystem case studies (pm-skills-mcp) show files-first is the recommendation | **ADAPTER (enterprise delivery), never primary** |
| **(d) Marketplace listing** | Anthropic Skills Marketplace (85/15), SkillExchange (80–85%), Agensi, SkillHQ, Smithery/mcp.so | Discovery + ratings + some passive income; winner-takes-most means being the *only* aerospace player is a real advantage | Marketplaces are young (Anthropic's May 2026); platform cut; cannot be the primary distribution bet | **AMPLIFIER (low effort, ship early)** |

### 3.2 The recommended combination

**Filesystem-first OSS repo (a) as the spine and wedge + Operator domain packs (b) as the monetization + MCP adapter (c) for enterprise/air-gapped delivery + marketplace listings (d) for discovery. One source of truth (SKILL.md files, Apache-2.0 core, gated enterprise packs), four surfaces.**

Rationale, grounded in the router research (brief 03):

1. **The format is the distribution.** SKILL.md (agentskills.io spec) is natively consumed by Claude Code, Hermes, OpenClaw, Codex — the open standard is the zero-integration moat. MCP is an adapter, not the backbone: the ecosystem's own case studies and the Skills-over-MCP WG treat SKILL.md as canonical.
2. **Launch delivery matches library size.** At ~60 skills, flat + tags + native host discovery beats routing (routers lose below ~600 skills on lazy-loading hosts). The router is *architected in* but *activated at scale* — and immediately for the Operator.
3. **Enterprise buys governance, not files.** Defense/ITAR buyers cannot just clone a repo; they need on-prem/air-gapped delivery, private packs, support SLAs, CMMC-aware deployment. That is the Operator + MCP combination, priced at enterprise rates.
4. **The Operator pack is where the same content becomes a product.** A SKILL.md folder is a free download; an "Aerospace Certification Department" (role charter + budget ledger + schedule + evidence gates + the 12-skill certification spine) is a €2–10K/yr purchase.

**Anti-patterns to avoid:** MCP as the primary (reintroduces tool-bloat and selection problems); marketplace-first (platform risk, winner-takes-most dependence); monetizing the free core (kills the wedge); separate content branches for repo vs Operator (one source of truth, or the two rot apart).

---

## 4. The router: the shared technology and the compounding asset

### 4.1 One codebase, three deployments

The router is the only piece of the stack that compounds *across products*:

| Deployment | Library | Router role |
|---|---|---|
| **Veda (today)** | 1,022 skills, BM25 + tag filtering → dense rerank (local `nomic-embed-text`, 768-dim) over top-40, body read from disk on demand; usage telemetry (`log`/`popular`) | Proven pattern, verified 2026-08-28 — the reference implementation |
| **AeroSkills (launch)** | ~60 skills: flat + domain index; router activated past ~100–600 skills | Domain routing by task/discipline ("size a battery for a 12U CubeSat" → orbital/power skills) |
| **Operator (scale)** | 1,000+ skills across *all* domain libraries (aerospace + defense + …) | The skill-routing engine: every department's procedural memory, routed per task |

The research backing (brief 03, SkillRouter arXiv 2603.22455): body-aware retrieve→rerank hits 74% Hit@1 on an 80K-skill pool at 1.2B params, 5.8× faster than a 16B baseline; the skill **body** is the decisive signal (removing it costs 31–44pp); on-demand loading cuts context cost ~99% (46.9K → ~560 tokens/task at ~1K skills); in-context routing collapses past ~500 skills (Match@1 0.85 → 0.12). Veda's router already implements the state of the art.

### 4.2 Why this is the moat

1. **Skill-quality flywheel:** router telemetry (selection logs, popularity, failure rates) tells you which skills are weak → description/index refinement → better routing → better task success (routing gains transfer end-to-end to task success). Veda's `log`/`popular` loop is the seed.
2. **Library-scale flywheel:** the two training adaptations that matter in homogeneous pools — false-negative filtering (+4.0pp) and listwise reranking (+30.7pp) — improve exactly as the library grows toward thousands of near-duplicate domain skills. Every new vertical library makes the router better at every other vertical.
3. **Multi-product leverage:** the same router is (a) a feature of the free repo (at scale), (b) the Operator's skill-routing engine, (c) the MCP server's `search_skills` backend. One investment, three products, one compounding asset.
4. **The "router as product" option:** at 10,000+ skills across verticals, the router itself becomes licensable infrastructure ("bring your own library, we route it") — the enterprise version of what Veda runs internally. This is the long-tail monetization the marketplace platforms (skills.sh ~670K skills) will need but don't have done well.

**Design discipline (from brief 03):** descriptions are the router — "what + when + trigger keywords," written for the orchestrator; taxonomy is organization, never routing; index bodies not metadata; skip the reranker until the library is past a few hundred skills; keep a small eval harness (realistic aerospace tasks) to track Hit@1 as the library grows.

---

## 5. Revenue architecture: free AeroSkills → paid Operator

### 5.1 The conversion logic

Free AeroSkills does three revenue jobs, in order:

1. **Brand & adoption (the top of the funnel).** The repo is the proof-of-quality document. Target: 2–10K★ within 6–12 months (vs the 31K★ cybersecurity comp on a smaller audience). Every star, fork, install, and marketplace download is a lead with *demonstrated* aerospace-AI intent.
2. **Direct monetization (the cash bridge).** While the Operator is being built: Pro subscriptions (€29–99/mo), vertical packs (€99–2,499 one-time), enterprise licenses (€2–10K/yr), academic campus licenses (€2–5K/yr), consulting (€799–2,499). This funds the build and validates willingness-to-pay.
3. **Operator conversion (the prize).** Every AeroSkills user is an Operator prospect: the library proved domain quality; the Operator packages it with governance. The enterprise AeroSkills buyer (engineering director at a prime/supplier, already through security review) is the shortest possible path to the Operator's domain-department SKU.

### 5.2 The numbers

**Funnel math (calibrated to brief 04 data):**

| Stage | Volume | Conversion | Result |
|---|---|---|---|
| OSS adoption (6–12 mo) | 2,000–10,000★, ~1,000+ installs | — | brand + proof |
| Captured leads (newsletter/enterprise-intent) | 5–10% of installs = 50–500 | — | contactable pipeline |
| Free→paid (dev-tools benchmark) | 11.7% | $187/mo avg ARPU | 6–58 paid × $187 ≈ $1.1–10.8K/mo |
| Enterprise AeroSkills deals | 1–3 per quarter, founder-led | $2–10K/yr each | €10–50K ARR by Y2 |
| Operator domain-department SKUs | 2–10 orgs | €5–20K/yr per department | the Y3 prize |

**Blended P&L path:**

| Period | Revenue mix | ARR |
|---|---|---|
| **Y1 (build + launch)** | OSS adoption; first Pro subs + packs; 1–3 enterprise pilots; marketplace drip | **€0–30K** |
| **Y2 (cash bridge)** | 10 defense/engineering orgs × €5–10K/yr + 20 universities × €2–5K/yr + 100–300 Pro subs + marketplace | **€90–200K** |
| **Y3 (Operator pivot)** | Operator launched; aerospace dept SKUs convert from AeroSkills enterprise base; 20–50 orgs × €10–25K/yr blended | **€0.5–1.5M** |

**Unit economics sanity check:** a domain-department SKU at €15K/yr vs the buyer's existing tool budget (MATLAB $940/yr/seat, ANSYS $5–50K/yr entry, avg enterprise deal ~$320K/yr) is a rounding error — pricing power is high and the procurement path (engineering + IT security review) is the same one the enterprise AeroSkills deal already opened.

**The honest risks:** aerospace is a smaller, slower audience than infosec; enterprise sales cycles run 6–18 months in defense; the €10K-MRR-by-Nov-2026 target requires founder-led 1:1 outreach, not organic GTM; marketplace dependence is a trap (direct distribution is the job). ITAR/standards-licensing content boundaries must be settled before publishing compliance hooks (brief 06).

---

## 6. The long game: the vertical-domain-library playbook

### 6.1 Why aerospace first

Aerospace is the ideal first vertical because it maximizes the *proof* per unit of effort: **highest standards density** (certification = verifiable compliance hooks = objective quality signal), **prestige halo** (aerospace credibility legitimizes every later vertical), **active demand** (GE/Airbus/NASA/Boeing all publicly investing in agentic engineering), **near-empty supply** (devideamax/aerospace-team, 21★ incumbent), and **high buyer value** (defense budgets, $134.8K median salaries). Deloitte 2026 confirms A&D agentic adoption is early — the library lands before the wave.

### 6.2 The portfolio: one playbook, five verticals

The playbook is identical each time: (1) map the vertical's standards backbone, (2) author 12–60 skills with compliance hooks, (3) seed reference builds, (4) publish free OSS → brand, (5) enterprise/air-gapped packs → revenue, (6) Operator domain-department SKU → platform revenue.

| # | Vertical | Standards backbone (the moat) | Demand evidence | Buyer ARPU |
|---|---|---|---|---|
| 1 | **Aerospace** (now) | DO-178C/DO-254, ARP4754A/4761A, AS9100, FAR/CS-25, MIL-STD-881 | GE, Airbus, NASA CARE, Boeing (brief 02) | €2–50K/mo enterprise |
| 2 | **Defense** (mo 6–12) | MIL-STD-810H/461G/516C, STANAG, CMMC 2.0, DFARS, ITAR/EAR | Physical-AI adoption most advanced in defense (Deloitte); $101.5M agent-governance funding wave | highest; air-gapped premium |
| 3 | **Maritime** (Y2) | IMO SOLAS, classification societies (DNV/ABS/Lloyd's), IACS | ABS reporting AI/digitalization take-up across marine/offshore; 2026 "automation turn" | €2–20K/mo |
| 4 | **Energy** (Y2–3) | IEC 61508/61511 (functional safety), ASME, API, IEEE, NERC CIP | OT/ICS AI adoption, grid + oil & gas + renewables | €5–50K/mo |
| 5 | **Civil / industrial** (Y3) | AASHTO, Eurocodes, ISO 9001 variants | largest volume, lower ARPU | €1–10K/mo |

### 6.3 Why the portfolio compounds

- **The router is the portfolio's shared brain** — one routing engine, N libraries; each new library improves retrieval for all (homogeneous-pool training adaptations).
- **The Operator is the portfolio's shared chassis** — every vertical is a department pack on the same platform; marginal cost of a new vertical ≈ authoring cost only (no new infra, no new GTM machinery, no new router).
- **The brand is the portfolio's shared halo** — "the people who nailed aerospace certification agents" opens defense, which opens energy. This is exactly the Anthropic trajectory: cybersecurity credibility → enterprise trust → partner distribution.
- **Marketplace compounding** — being the category owner in aerospace, then defense, makes each new listing cheaper to seed and more likely to win the winner-takes-most slots.
- **Data flywheel** — cross-vertical routing telemetry and skill-usage data is the proprietary asset competitors can't clone; it is what makes the Operator's departments measurably better over time.

**Sequencing rule:** never start a new vertical until the previous one has (a) a published standards map, (b) ≥30 shipped skills, (c) ≥500★ or 10 enterprise-intent leads, and (d) at least one paid customer or pilot. Vertical #2 (defense) can overlap aerospace's enterprise phase because the buyers overlap, but each *new* vertical needs its own proof loop.

---

## 7. Consolidated architecture recommendation

```
                        ┌─────────────────────────────────────────────┐
                        │         ONE SOURCE OF TRUTH (Git)          │
                        │   SKILL.md library · Apache-2.0 core        │
                        │   standards-mapped · compliance hooks       │
                        └──────────────────┬──────────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
   ┌──────────▼──────────┐     ┌───────────▼───────────┐    ┌───────────▼───────────┐
   │ (a) OSS repo        │     │ (b) Operator packs   │    │ (c) MCP server        │
   │ wedge + brand       │     │ domain departments   │    │ enterprise/air-gapped │
   │ npx skills add      │     │ charters+ledgers+    │    │ metadata + get_skill  │
   │                    │     │ schedules+gates      │    │  (SEP-2640-aligned)    │
   └──────────┬──────────┘     └───────────┬───────────┘    └───────────┬───────────┘
              │                            │                            │
              └──────────────┬─────────────┴─────────────┬──────────────┘
                             │                           │
                  ┌──────────▼──────────┐      ┌─────────▼──────────┐
                  │ (d) Marketplace     │      │ THE ROUTER         │
                  │ listings (85/15 etc)│◄────►│ BM25+tags+dense    │
                  │ discovery amplifier │      │ body-aware rerank  │
                  └─────────────────────┘      │ Veda→Aero→Operator │
                                               └────────────────────┘
```

**Decision table:**

| Question | Answer |
|---|---|
| What is the source of truth? | SKILL.md files in git (agentskills.io spec), Apache-2.0 core, gated enterprise packs |
| What ships first? | The OSS repo + marketplace listings (wedge, proof, leads) |
| What monetizes? | Pro packs → enterprise license → **Operator domain-department SKUs** |
| What delivers to enterprise? | MCP adapter + private repo + on-prem Operator (ITAR/CMMC-aware) |
| What compounds? | The router: Veda 1,022-skill engine → AeroSkills router → Operator skill-routing engine |
| What is the moat? | Standards mapping + compliance hooks + routing telemetry across verticals |

---

## 8. Roadmap

**Phase 0 — Foundation (Days 1–30)**
- Seed 12 skills (one per discipline; DO-178C certification spine first)
- Port Veda's router (BM25+tags, flat + domain index at this size); build the eval harness (realistic tasks: "size a battery for a 12U CubeSat," "draft a DO-178C coverage argument")
- Legal review of ITAR/standards content boundaries (brief 06) before publishing
- Publish OSS repo (founder GO), Apache-2.0, AGENTS.md, taxonomy docs; list on Anthropic Marketplace + SkillExchange + 2 more

**Phase 1 — Depth (Days 31–60)**
- Expand to ~30 skills with BASM fences + compliance hooks; 2–3 reference builds (full CFD workflow, certification trace, orbit design)
- Community: X build-in-public, r/AerospaceEngineering (131–138K subs), LinkedIn, AIAA groups; target 500–2,000★
- MCP adapter v1 (metadata + search/get, files as source of truth); router activated

**Phase 2 — Monetization (Days 61–90)**
- AeroSkills Pro (€29–99/mo) + vertical packs; enterprise/air-gapped tier (€2–10K/yr); academic campus tier
- Founder-led 1:1 outreach to 20–50 engineering firms/defense subs; 1–3 pilots; AIAA SciTech presence (Jan)
- Operator integration spec: define the Aerospace Engineering Department pack (charters, ledger, gates)

**Phase 3 — Operator pivot (Months 4–6)**
- Operator v1 with aerospace domain packs; convert the AeroSkills enterprise base
- Router becomes the Operator's skill-routing engine; ship department templates (skills/agents/schedules/evidence/reports)
- Reference implementation = AeroSkills itself runs as Operator departments (dogfood, public)

**Phase 4 — Vertical #2: defense (Months 6–12)**
- MIL-STD/CMMC standards map; defense skills pack; air-gapped enterprise delivery; defense pilots
- Portfolio math in force: aerospace must have ≥1 paid customer before defense authoring ramps

**Phase 5 — Portfolio (Year 2)**
- Maritime (IMO/class societies) then energy (IEC 61508/61511); marketplace as compounding channel
- Router at 5,000+ skills across verticals; evaluate "router as product" (route-any-library enterprise licensing)

---

## 9. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Aerospace audience smaller/slower than infosec | Price power (higher ARPU), academic channel, defense overlap; the Operator is the 10–50× upside |
| Enterprise sales cycles 6–18 months (defense) | Land-and-expand: individual engineers (expense account) → teams → org license; Pro tier as bridge revenue |
| ITAR/standards-licensing content risk | Legal-reviewed publish-safe/publish-gated policy (brief 06); free core generic, certification specifics gated |
| Piracy of file-based skills | Subscription (updates as value), hosted/Operator access, enterprise contracts |
| Marketplace dependence | Direct distribution is the job; marketplaces are amplifiers only |
| Router unnecessary at launch size | Correct: flat + index at ~60 skills; router pays off at 100s–1,000s — exactly when the Operator needs it |
| Operator build dilutes AeroSkills focus | AeroSkills IS the Operator's domain layer; roadmap sequences them (wedge first, platform second) |
| Standards text copyright (DO-178C etc.) | Reference + summarize, never reproduce; same approach as MITRE-mapped cyber skills |

---

## 10. Sources

- Veda internal: Department-as-Code skill; AI Department Operator trinity memo (2026-08-25); competitive scans (2026-08-28: FrontierAgent, halofy, Paperclip, SuperOrgs, Chartav, Convey/Sapiom/Naive funding); Veda router (1,018–1,022 skills, BM25+tags+dense rerank, verified 2026-08-28)
- AeroSkills briefs 01–05 (market, industry usage, router design, GTM/pricing, domain taxonomy) — all figures on stars, pricing, conversion, taxonomy drawn from those audited briefs
- Anthropic: claude.com/solutions/cybersecurity; claude.com/product/claude-security; "How Anthropic's cybersecurity team built a threat detection platform with Claude Code"; "CISO's guide to agentic AI"; "Bringing the cybersecurity capabilities of Claude Mythos 5 to more defenders" ($35M Defender Advantage Fund, Cyber Verification Program, Project Glasswing); Snowflake–Anthropic enterprise press release
- GitHub: mukul975/Anthropic-Cybersecurity-Skills (31,700★, 818 skills, 5-framework mapping); anthropics/skills (official, ~171.8K★); frankxai/claude-skills-library (free catalog → paid flagship packs pattern)
- MCP ecosystem: 10,000+ active public servers (Anthropic Dec 2025 update); Linux Foundation AAIF donation; Skills-over-MCP WG (SEP-2640); aeroastro.org Aerospace MCP
- Skill routing: SkillRouter (arXiv 2603.22455); Enrich-Retrieve-Rank (arXiv 2608.22695); AnamKwon/agent-skill-router benchmarks; agentskills.io spec
- Vertical SaaS: Stackmatix vertical GTM playbook; Blume vertical-SaaS playsheet; Deloitte 2026 A&D outlook; ABS maritime AI report; maritime-executive 2026 automation editorial
- Monetization benchmarks (from brief 04): Monetizely, DollarPocket, CompareTiers, 500k.io Q1 2026 founder sales data, StrongMocha marketplace retrospective, SkillExchange playbook

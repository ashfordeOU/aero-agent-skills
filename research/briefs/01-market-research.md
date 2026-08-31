# Market Research: Aerospace Engineering Skills Library for AI Agents (AeroSkills)

**Date:** 2026-08-30 · **Method:** GitHub API + GitHub repo pages (verified star counts) + web search · **Currency note:** all star counts verified 2026-08-30 unless marked "unverified"; canonical live baseline 2026-08-31 in ops/automation/numbers.yaml (K-Dense 39,111 · cyber 31,700 · devideamax 21 · ajhcs 22)

---

## 1. Executive Summary

- The **agent-skills market overall is enormous and hyper-saturated** (anthropics/skills 172.5k★, addyosmani/agent-skills 90.5k★, sickn33/agentic-awesome-skills 45.5k★), but it is dominated by **generic software-development skills**.
- The **domain-vertical skill library model is proven by exactly two breakout winners**: cybersecurity (mukul975/Anthropic-Cybersecurity-Skills, 31.7k★, 818 skills) and science (K-Dense/scientific-agent-skills, 39.9k★, ~163 skills). Both are ~10 months old, both built by individuals/small startups, both on the open agentskills.io standard.
- **Aerospace is effectively an empty category.** The largest dedicated aerospace agent-skills repo on GitHub is **devideamax/aerospace-team at 21★** (12 skills). All aerospace MCP servers have 0–15 stars. Aggregate skill libraries list "aerospace" as a category with **2 skills** (and those are mislabeled web-dev skills).
- **Whitespace conclusion: genuine and large.** Demand-side proof exists (cybersecurity and scientific libraries grew 30–40k stars in months with identical positioning: standards-aligned, framework-mapped, agentskills.io-compliant skill packs). Supply side for aerospace is near-zero, fragmented across hobby-scale MCP servers, and the commercial players (Vecteur, Navier, AwerX, Deepsky) are building closed platforms, not open skill libraries.
- Risk: aerospace is a smaller, slower-moving buyer population than infosec/research; skills must target real engineering workflows (certification, MDAO, mission design) and the "smart router" delivery has a direct precedent (sickn33 AAS Core control plane) that is worth copying.

---

## 2. Aerospace-Specific AI Agent Skills / Libraries / Packages (all GitHub, stars verified)

### 2a. Actual "agent skills" libraries (closest competitors)

| Repo | Stars | Created | What it covers |
|---|---|---|---|
| **devideamax/aerospace-team** (github.com/devideamax/aerospace-team) | **21** | 2026-02 | "Space Engineering Pack": **12 Claude Code skills** for spacecraft & launch vehicle design — propulsion, orbital mechanics, structural, thermal, satellite comms, power systems, GNC, payload, mission architect, ground systems. Each skill: expert persona, reference data, formulas (vis-viva, link budgets), worked examples, error catalogs, cross-skill connectors. Built by IDEAMAX Skills Factory (ideamax.eu). **The closest direct competitor in format.** |
| **hakimzulkufli/asd-ste100-skills** (github.com/hakimzulkufli/asd-ste100-skills) | 0 | 2026-07 | 2 agent skills for **ASD-STE100 Simplified Technical English** (aerospace maintenance documentation standard, 53 writing rules, Issue 9 vocab). Niche but authentic aerospace-standard skill. |
| **deepskyai/agent-tools** (github.com/deepskyai/agent-tools) | 0 | 2026-04 | Aviation compliance skills + free remote MCP for **CASA/FAA/EASA/ICAO regulations search** + flight-ops calculators. By **Deepsky** ("The Compliance Team — Vanta for aviation"). Proof an aviation startup ships agent skills as a funnel. |

### 2b. Aerospace MCP servers (tool servers, not skill libraries)

| Repo | Stars | What it covers |
|---|---|---|
| **IO-Aerospace-software-engineering/mcp-server** (github.com/IO-Aerospace-software-engineering/mcp-server) | **15** | Hosted astrodynamics MCP at mcp.io-aerospace.org: celestial ephemeris, orbital mechanics, DSN ground stations, time systems. C#/AGPL. Single maintainer (sylvain-guillet). |
| **ajhcs/mbse-agents** (github.com/ajhcs/mbse-agents) | **22** | Not MCP — **MBSE domain agents** (5 agents, 30+ standards): ARP4761A, DO-178C, ISO 26262, SysML/Capella, aerospace + defense + medical. "Agent files that turn AI coding assistants into principal systems engineers." Closest to a standards-mapped aerospace library. |
| **0xchamin/skyintel** (github.com/0xchamin/skyintel) | 19 | VoyageIntel: air/sea/space tracking MCP, 25+ tools, agent skills, 3D globe. |
| **cheesejaguar/aerospace-mcp** (github.com/cheesejaguar/aerospace-mcp) | 4 | Flight planning + space: 7,861 IATA airports, OpenAP performance, ISA atmosphere, ECEF/ECI frames, rocket trajectory, orbital mechanics. |
| **benajaero/rocket-tools** (github.com/benajaero/rocket-tools) | 1 | "35 MCP tools for aerospace engineering" + a **skills/ library**: structural, margin-of-safety, trusses, aerodynamics, compressible flow, thermodynamics, aircraft performance, nozzle design, mission planning. 265 tests, 74% coverage. |
| **muroc-aero/the-hangar** (github.com/muroc-aero/the-hangar) | 1 | **Hosted MCP servers for aerospace MDO** (mcp.lakesideai.dev): OAS aerostructural analysis, OCP aircraft conceptual design, PYC gas-turbine cycles, OMD OpenMDAO planner, EVT eVTOL sizing. Reproduces Brelje & Martins 2018. Org-backed (Lakeside AI). |
| **astro-tools/astrodynamics-mcp** (github.com/astro-tools/astrodynamics-mcp) | 1 | TLE/SGP4, Lambert, ground-station access, porkchop, B-plane; optional NASA GMAT + SPICE. Has an Inspect AI eval suite. |
| **aerospace-mcp-tools/outgassing-mcp-server** (github.com/aerospace-mcp-tools/outgassing-mcp-server) | 1 | NASA outgassing database (13,582 materials), NASA-STD-6016 compliance. Org `aerospace-mcp-tools` also runs **ecss-mcp-server** (ECSS standards documents). |
| ProgramComputer/NASA-MCP-server, PaulMRamirez/yamcs-mcp-server, imonroe/flightaware-mcp | small (unverified) | NASA APIs, Yamcs mission control, FlightAware aviation data. |

### 2c. Hobby/experimental aerospace agents (noise, ~0★): zhiling31/AerospaceAgent, PoseZhaoyutao/aerospace-agent (orbit design + GNC, CN), maia-felipe/aerospace-agent, lihaichuan6686/atk-connect-agent (ANSYS ATK mission simulation), mftnakrsu/rag-vs-agentic (DO-178C RAG research), Samuelson777/OpenSat-Mission-Lab, TheJayVachhani/factory-os-mcp (aerospace manufacturing demo), jdbruh18/defenseops-aerospace-mcp-platform (defense telemetry demo).

### 2d. Aerospace inside aggregate libraries

- **christophacham/agent-skills-library** (60★): 2,622 skills from 48 sources, 34 categories — `aerospace` category = **2 skills** (and they are Nx/JS build-tool content, i.e., mislabeled — no real aerospace content).
- **agent-skills-hub/agent-skills-hub** (86★): 2,005+ general skills, zero aerospace-specific coverage.
- GitHub topic `aerospace` (1,363 repos) is dominated by **simulation tools** (OpenRocket, RocketPy, AeroSandbox, SUAVE, OpenVSP, elodin-sys/elodin), not agent skills.

---

## 3. Companies / Projects Building Domain-Specific Agent Skill Libraries for Engineering

### Open-source domain libraries (the direct playbook)
| Project | Stars | Domain | Structure / marketing |
|---|---|---|---|
| **K-Dense-AI/scientific-agent-skills** | **39,925** | Science (bio/chem/med/drug discovery) | 163–165 validated skills; 78+ scientific databases via a unified `database-lookup` skill; 70+ version-scoped Python-package skills; MIT; `plugin.json` packaging; BYOK local runner (k-dense-byok); claims "used by 190,000+ scientists"; heavy outbound (X, LinkedIn, YouTube webinars, Reddit); versioned releases (v2.65.0); CI security scan + skill tests. |
| **mukul975/Anthropic-Cybersecurity-Skills** | **31,700** | Cybersecurity | 818 skills, 34 domains, **mapped to 6 frameworks** (MITRE ATT&CK v19.1, NIST CSF 2.0, MITRE ATLAS, D3FEND, NIST AI RMF, MITRE F3); agentskills.io standard; Apache-2.0; works on 26+ platforms; install via `npx skills add`; release train + changelog; author academic survey (GARS-2026) for credibility. Community project, not affiliated with Anthropic. |
| **GPTomics/bioSkills** | 1,187 | Bioinformatics | SKILLS.md workflows; **ARCHIVED** 2026 — lesson: single-topic science skills don't survive without a maintainer/business behind them. |
| **briiirussell/cybersecurity-skills** | 366 | Security | Smaller competitor, MIT. |
| **trailofbits/skills** | 6,895 | Security research | Claude Code plugin marketplace from a respected security firm — **company-branded skills as marketing/credibility**. |
| **hashicorp/agent-skills** | 855 | Terraform/Packer | Vendor product skills (16 + 4), MPL-2.0 — pattern: **a vendor ships agent skills for its own products**. |
| **addyosmani/agent-skills** | 90,528 | Software engineering | Production-grade SDLC skills (DEFINE→SHIP). |
| **VoltAgent/awesome-agent-skills** | 33,335 | Curated index | 1,497+ skills; "hand-picked, not AI-slop generated" positioning. |
| **sickn33/agentic-awesome-skills** | 45,545 | General catalog | 2,005+ skills + **AAS Core: a local control plane (CLI + read-only MCP + catalog + `compose_stack` validation + immutable plan)** — i.e., the "smart router / delivery layer" concept already exists as OSS; AeroSkills' router must be materially better than this. |
| **tech-leads-club/agent-skills** | small | General | "Secure, validated skill registry" — validated-registry positioning. |

### Commercial aerospace-AI players (closed platforms, not open skill libraries — validate the market, not the format)
- **Vecteur** (vecteur.space, Toulouse) — "Space systems engineering, automated": deterministic physics engines, Phase 0/A (orbit sizing, constellation coverage, link budgets, LEO-PNT), reviewable outputs, MCP integration. **Closest commercial analogue to AeroSkills' vision** (domain delivery layer for space engineering).
- **AwerX** (awerx.ai) — "Agentic Engineering for Aerospace & Advanced Manufacturing"; autonomous agents + physics-based simulation + generative CAD.
- **Navier AI** (navier.ai) — agent-driven CFD/simulation platform, aerospace & defense vertical (external aero, GNC, supersonic).
- **Aerospace.ai** — AI agents for aerospace design, predictive maintenance, flight simulation (US Air Force experience).
- **Neodustria** (neodustria.com) — aerospace intelligence platform, physics-aware AI + digital twins (EU).
- **Godel Space** (godel.space) — autonomous AI agents on satellite payloads (on-orbit perception/triage).
- **Deepsky** (deepskyai.com) — "Vanta for aviation": audit automation + free regulations MCP/skills as a funnel.
- **Pathfinder Labs / Charles Lambert** — agentic AI engineering tools for A&D; **Intellectyx** — services; **Cadence** — agentic AI in EDA/aerospace.

---

## 4. Market Size & Maturity Assessment

**How many exist:** Dedicated aerospace agent-skills repos: **~3** (aerospace-team 12 skills; asd-ste100 2; deepsky 2). Aerospace MCP servers: **~12–15**, all single-digit stars. Compare: cybersecurity skills repos >20 with one at 31.7k★; scientific >10 with K-Dense at 39.9k★.

**Maturity by segment:**
- Generic/coding skills: hyper-mature, crowded, star inflation (anthropics 172k, addyosmani 90k, sickn33 45k, VoltAgent 33k). Entry pointless.
- Vertical skill libraries (security, science): **proven demand, young market** — both leaders created Oct 2025–Feb 2026 and hit 30k+ stars in ~6–10 months. Distribution levers: agentskills.io standard + `npx skills add` + plugin marketplaces + LobeHub/agent-skill.co aggregators.
- Aerospace vertical: **pre-seed / nascent.** Highest-star dedicated asset = devideamax/aerospace-team at 21★. No standards-mapped aerospace library exists (no DO-178C/ARP4754A/ARP4761A/ECSS/MIL-STD skill packs anywhere — mbse-agents at 22★ is the only standards-flavored asset, in MBSE-agent form, not skill form).
- Delivery/router layer: OSS precedents exist (sickn33 AAS Core, tech-leads-club registry, skills.sh, LobeHub market) — the "smart router" is an execution differentiator, not a category creation.

**Buyer/demand reality check (honest):** cybersecurity skills rode a 4.8M-person workforce shortage narrative and a huge developer-adjacent audience; scientific skills rode academia/open-science culture. Aerospace engineers are fewer, more conservative, ITAR/export-controlled, and mostly inside primes — the organic-star path will be slower. The credible wedge is **standards & certification workflows** (the highest-leverage, most-agent-valuable aerospace knowledge) plus mission design/MDAO for the new-space startup population (Vecteur's target).

---

## 5. Whitespace Assessment (AeroSkills)

**Verdict: significant whitespace in supply, proven demand model, with real but manageable risk.**

1. **No direct competitor exists.** No one ships a broad, standards-mapped, agentskills.io-compliant aerospace engineering skill library (aircraft + spacecraft + defense + MRO + certification). Closest formats: aerospace-team (12 skills, single author, no standards mapping), mbse-agents (agents not skills, no router), MCP servers (tools, not knowledge/workflow skills).
2. **The playbook to copy is explicit and proven**: agentskills.io + SKILL.md progressive disclosure + framework/standards mapping (aerospace analog: DO-178C/DO-254/ARP4754A/ARP4761A/ECSS/MIL-STD-810 + certification artifacts) + YAML-frontmatter discovery + `npx skills add` install + versioned releases + plugin packaging + free BYOK-style runner + content marketing. K-Dense and mukul975 both executed exactly this and hit 30–40k stars in under a year.
3. **Differentiators available to AeroSkills**: (a) the Veda 1,022-skill base including 818 cybersecurity skills gives instant credibility and cross-domain bundling; (b) a genuine smart router / domain delivery layer (better than AAS Core's read-only compose_stack); (c) standards-clause-level accuracy and validation (no other aerospace library does this); (d) certification-workflow focus (DO-178C traceability, ARP4761A safety assessments, ECSS documents) where agents currently fail and where aerospace orgs pay.
4. **Risk flags**: smaller TAM and slower star growth than security/science; aerospace content requires careful sourcing (ITAR, proprietary standards licensing — ECSS/SAE documents are not free); commercial monetization (enterprise licensing to primes/MRO/startups) is more credible than open-source virality; defense-adjacent content may face export-control handling costs.

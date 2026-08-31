# AeroSkills — Business & Go-To-Market Research Report

**Research date:** August 30, 2026 · **Purpose:** Evaluate AeroSkills (aerospace engineering skills library for AI agents) as a standalone product and/or a wedge into the AI Department Operator product. All figures from live web research (links inline). Targets: €10k MRR by 2026-11-15.

---

## Executive Summary

- The "domain-specific skills library" play is **proven, not hypothetical**: Anthropic-Cybersecurity-Skills (818 skills, Apache 2.0, free) hit **31,700 GitHub stars and 3,818 forks in ~6 months** — the direct template for AeroSkills.
- Skills libraries are a **distribution and trust asset first, a revenue product second**. The free OSS library builds the audience; revenue comes from premium skill packs, subscriptions, enterprise/on-prem licensing, and consulting — not from selling the free files.
- Concrete 2026 comps: solo founders selling vertical Claude skills made **$1,400–$8,483 in their first month** (4 founders, Q1 2026); median skill-marketplace creator earns **$300–$1,500/mo**, top decile **$5–25K/mo**; enterprise skill licensing runs **$2K–$50K/mo**.
- Aerospace market tailwind is real: MBSE-in-aerospace **$6.8B (2025) → $15.2B (2034)**, AI-in-aerospace-engineering **$12.5B (2024) → $45.8B (2034)**, aerospace AI at **~43–45% CAGR**.
- **€10k MRR by 2026-11-15 is a stretch but not absurd** — it requires founder-network-driven enterprise deals (2–4 orgs at €2–5K) plus premium pack sales. Realistic median outcome on organic GTM alone: €2–5K MRR in 3 months, €10K in 6–9 months.

---

## 1. Pricing Models for Developer Tools & AI Agent Skill Libraries

### 1.1 Benchmark anchors: what dev tools charge (2025–2026)

| Metric | Value | Source |
|---|---|---|
| Median entry-level SaaS plan (account-based) | **$29/user/mo** | Monetizely 2025 (100+ cos.) |
| Median per-user price, all SaaS | $45/user/mo | Monetizely |
| Security/compliance software median | **$89/user/mo** | Monetizely (vertical benchmark) |
| Dev tools — dominant pricing model | **Usage-based (52% of tools)** | CompareTiers 2026 (521 tools) |
| Dev tools — free tier offered | 21% | CompareTiers |
| Dev tools — freemium free→paid conversion | **11.7%** (best of all categories), median 124 days to convert | DollarPocket (500+ cos.) |
| Dev tools — ARPU after conversion | **$187/mo** | DollarPocket |
| Vertical SaaS median ARPU | $324/mo | DollarPocket |
| Security software median ARPU | $487/mo | DollarPocket |
| Infrastructure/DevOps median ARPU | $847/mo | DollarPocket |
| GitHub Enterprise | $21/user/mo list, $12–16 transaction | VendorBenchmark |
| GitLab Ultimate | $99/user/yr list, $55–75 transaction | VendorBenchmark |
| MATLAB individual license | **$940/yr** (~€964/yr EU); student suite $119 incl. Aerospace Toolbox/Blockset ($29 each) | mathworks.com |
| ANSYS | ~$5K–50K+/yr entry; **avg enterprise deal ~$320K/yr** (Vendr); academic research license ~$330/yr | Ozen, Vendr, ITQlick |

**Key insight:** aerospace engineers are used to **$940–$50,000/yr per-seat engineering software**. A skills library priced at €19–99/mo is a rounding error against their existing tool budgets — pricing power is high, but expectations of "serious engineering tool = serious price" also mean a $10 one-time price signals low quality.

### 1.2 Pricing models for AI agent skills (live marketplaces, 2026)

| Model | Typical price range | Notes |
|---|---|---|
| **Free / open-source** | $0 | Lead-gen & brand; standard in security space (see §2) |
| **One-time download** | $5–$500 | Agensi guidance: $5–15 single-purpose; $20–50 comprehensive; $299–2,499 vertical expertise (500k.io) |
| **Per-use / per-invocation** | **$0.001–$0.50/call** (sweet spot $0.005–0.05) | ClawMerchants x402: $0.01–0.05/access; mcpmeter: $0.0002/call |
| **Subscription** | $9–$999/mo (typical $19–99) | Security/audit category: $29.99–199.99/mo (SkillExchange playbook) |
| **Enterprise license** | **$2K–$50K/mo** (SkillExchange); $5K–50K/yr license + $1K–10K setup + 20–30% support SLA | Best fit for defense/air-gapped |
| **Outcome-based** | $0.10–$1.00 per outcome | "Charge for value, not compute" |
| **Hybrid** | base per-call + premium sub | The "pro move" per SkillExchange playbook |

**Platform revenue splits (who takes what):**

| Platform | Creator keeps | Notes |
|---|---|---|
| Anthropic Skills Marketplace (launched May 1, 2026) | 85% | ~600 skills at launch; paid skills = one-time install fee or monthly sub; 15% platform cut |
| SkillExchange | 80–85% | Pro plan €19/mo for unlimited skills + 85/15 split |
| SkillHQ | 80–85% | CLI install, anti-piracy fingerprinting |
| Agensi | 70% | Curated, security-scanned |
| OpenAI GPT Store (analog) | 75% | — |

**Value-based pricing method (Claude Lab, working founders):** estimate time saved × user hourly cost × monthly uses → **charge 10–20% of captured value**. A skill saving an engineer 2 hrs/wk at $150/hr ≈ $1,200/mo value → **$120–240/mo is defensible; most sellers underprice at €2–20.**

### 1.3 Open-source monetization ladder (real 2026 numbers)

| GitHub stars | Realistic monthly income |
|---|---|
| 0–500 | $0–50/mo (goodwill phase) |
| 500–2,000 | $100–800/mo |
| 2,000–10,000 | $800–5,000/mo |
| 10,000+ | $3,000–15,000+/mo |

- Median OSS project earns **<$200/mo** from GitHub Sponsors; median annual donation income **<$5,000** (Open Collective).
- **Sponsorware** (early access to features for sponsors, open-source later) converts **2–4x better** than donation asks.
- GitHub Sponsors: 0% fee on personal sponsorships; org sponsors pay ~3–6%.
- 63-developer OSS monetization survey: top earners $200–8,400/mo; **expect 12–18 months to consistent revenue**; distribution (HN/newsletter) is the bottleneck, not code quality.

---

## 2. Successful Domain-Specific AI Tool Libraries & Their Monetization

### 2.1 The definitive comp: cybersecurity skills libraries

| Project | Size | Adoption | Monetization |
|---|---|---|---|
| **Anthropic-Cybersecurity-Skills** (mukul975) | 818 skills, 34 domains, MITRE/NIST-mapped, Apache 2.0 | **31,700 stars, 3,818 forks** in ~6 months | **None directly** — free; author monetizes via personal brand (mahipal.engineer), surveys (GARS-2026), consulting pipeline |
| Trail of Bits /skills | Security research skills | Well-known, cited by Snyk | Free → feeds **consulting funnel** (Trail of Bits sells audits) |
| transilienceai/communitytools, claude-pentest-skills, awesome-claude-skills-security | Pentest/bug-bounty skills | Community adoption | Free |
| Snyk's "Top 9 Claude Skills for Cybersecurity" | — | Editorial coverage drives traffic | Content marketing for Snyk |

**The pattern:** in security, every serious library is **free + Apache/MIT + framework-mapped** (MITRE ATT&CK, NIST CSF). Monetization happens *around* the library: consulting, enterprise deployments, brand, adjacent products. **AeroSkills should copy this: free core, mapped to aerospace standards (DO-178C, DO-254, ARP4754A, AS9100, MIL-STD-881), monetize around it.**

### 2.2 Skill marketplaces & MCP monetization — revenue reality

- **SkillExchange** (agent-native, MCP/A2A): creators earn €200–20,000+/mo; top 10% earn **€2,500+/mo within 6 months**; enterprise licensing deals €2,000–50,000/mo.
- **500k.io founder data (Q1 2026, direct sales via Gumroad):**
  - $39 productivity skill → 144 sales/mo = **$5,616**
  - $99 workflow skill → 47 sales = **$4,653** (12K X followers)
  - $299 vertical-expertise skill → 23 sales = **$6,877** (8.5K LinkedIn)
  - $499 vertical bundle → 17 sales = **$8,483** (niche community)
  - Their framework: **Tier 1 generic $5–29; Tier 2 workflow $49–199; Tier 3 vertical expertise $299–2,499.** Realistic solo range: **$500–5,000/mo in 6–9 months; top 10% $10K+/mo.**
- **StrongMocha 6-month retrospective:** skills ecosystem at 4,200+ skills, 120K monthly visitors; **winner-takes-most** (top 5–10 skills per category = 60–80% of revenue); **hosted access ≈ 10x file-sales revenue**; median creator $300–1,500/mo, top decile $5–25K/mo; guidance: **price domain expertise at $99–499/mo, hosted/access-based not file-based.**
- **MCP servers:** Smithery (6,000+ servers) Free / **Pro $20/mo** / Enterprise; monetization playbooks: free tier → rate-limit → Stripe upgrade ($9–19/mo typical); Nevermined/Radius/Zeo push usage-based, outcome-based, value-based metering (Zeo: MCP cuts dev context switching ~40%).
- **Agensi top sellers (early, small):** keyword-research $7 × 89 installs = $436; gtm-engine $6 × 28 = $117 — evidence that **$5–20 impulse pricing works for discovery but caps revenue**.

### 2.3 What this means for AeroSkills

| Strategy | Revenue ceiling | Fit for AeroSkills |
|---|---|---|
| Free OSS library only | $0–1K/mo (sponsors) | Required as foundation (distribution/trust) |
| Premium skill packs (one-time $29–299) | $1–8K/mo | Good cash early; piracy-prone; no recurring |
| Pro subscription ($29–99/mo, updates + enterprise features) | $3–20K/mo at 100–500 subs | **Best standalone product model** |
| Enterprise/on-prem license ($2–10K/yr per org) | $10–50K+/mo at scale | **Best fit for defense/ITAR buyers; highest LTV** |
| Consulting/setup ($799–2,499 per engagement) | $1–5K/mo | Fast cash, validates enterprise need |
| Hosted access (runs on your infra) | 10x file sales | Later; infra cost |

---

## 3. Target Buyers

### 3.1 Market size

| Segment | Size | Source |
|---|---|---|
| US aerospace engineers (narrow SOC 17-2011) | **71,600 jobs**, median pay **$134,830/yr** | BLS 2024 |
| US aerospace engineers (broader CPS definition) | 160K–187K | DataUSA / FRED |
| US A&D industry total workforce | **2.1–2.2M** (914K direct) | AIA 2025 |
| Aeronautics/aircraft direct jobs | 434K–468K | AIA |
| Space sector direct jobs | 156K–192K | AIA |
| Avg A&D labor income | $115K (56% above national avg) | AIA |
| Aerospace engineers in engineering services firms | ~11K (BLS) | BLS |
| ABET-accredited aerospace engineering programs (US) | ~80–110 (of 3,100+ ABET programs / 660+ institutions) | ABET |
| Global aerospace engineering programs | several hundred | est. |

### 3.2 Buyer segments & willingness to pay

**A. Individual aerospace engineers** (~72K US, more globally)
- Median pay $134,830 → ~$65/hr. A skill saving 2 hrs/wk = ~$6,500/yr value.
- Pay $119–940/yr for MATLAB already; will pay €10–30/mo for tools that remove drudgery (requirements traceability, standard-compliance checks, FMEA/FRACAS templates, sizing spreadsheets).
- **Channels:** GitHub, X, Reddit, LinkedIn. **Price: €10–30/mo or $99–199 one-time.**

**B. Engineering firms / consulting firms** (aero engineering services ~11K US engineers; firms range 5–5,000 people)
- Buy seats in blocks (5–50). Care about productivity, standard compliance, brandable output.
- **Price: €29–99/user/mo, team tiers.** ACV $3–10K for a 20-seat team is an easy procurement (vs. their $50–100K ANSYS spend).

**C. Defense contractors** (the 54% share of A&D employment)
- **Hard requirements: CMMC 2.0 compliance, ITAR/EAR awareness, air-gapped/on-prem deployment, GovCloud.** AI trained on/integrated with controlled technical data can trigger ITAR obligations — a text/methodology skills library is generally fine, but **selling on-prem licenses + private-repo delivery is a decisive advantage** vs. cloud-hosted competitors.
- Buy via procurement, POs, annual licenses. **Price: €2–10K/yr per organization** (site license). 1,000+ prime/subcontractor addressable orgs (US primes + tier-1/2 suppliers).
- Existing competitors prove the market: AirgapAI (2,800+ gov workflows), Zylon AI, VRLA Tech (sold to General Dynamics).

**D. Universities** (~100 ABET US programs + global; also NASA-affiliated labs)
- Campus-wide licenses are the norm (MATLAB campus licenses; ANSYS academic $330/yr; free student editions).
- Buy once per semester/academic year; student licensing = long-term habit formation.
- **Price: €1–5K/yr campus license; free for students** (identical to MathWorks playbook).

**E. Space startups / eVTOL / NewSpace** (hundreds of orgs, e.g., eVTOL market projected $3B+ annual aircraft revenue by 2035)
- Fast-moving, less bureaucratic, but price-sensitive. **€49–199/mo team plans.**

---

## 4. Go-To-Market Channels

### 4.1 Channel playbook with conversion data (from 500k.io founder study + SaaS benchmarks)

| Channel | Approx. conversion | Best for | Effort |
|---|---|---|---|
| Email/newsletter (engaged) | **2–8%** open-to-buy | Premium packs, enterprise | High (months) |
| Niche communities (Synapse-Circle-like, aerospace Discords/Slacks) | 3–10% | Mid/high tiers | Medium |
| Podcast appearances | 5–15% (small N) | Tier 2–3 | High per episode |
| LinkedIn (engaged) | 1–3% post→click | B2B, firms, defense | Medium |
| **1:1 cold outreach** | **5–20%** (variable) | Enterprise/Tier 3 | Very high per deal |
| X/Twitter | 0.3–1% | Awareness, Tier 1–2 | Medium |
| Reddit (genuine participation) | 0.1–0.5% | Tier 1, community building | High |
| GitHub (stars→sponsors/enterprise) | ~11.7% free→paid (dev tools avg) | All | High |

### 4.2 Specific channels for aerospace

1. **GitHub (primary):** open-source AeroSkills core (agentskills.io standard, Apache 2.0). Comp proves ceiling: 31.7K stars in 6 months for cybersecurity. Publish to **Anthropic Skills Marketplace** (15% cut, ~600-skill catalog, discovery + ratings), **SkillExchange, Agensi, SkillHQ, Smithery/mcp.so** (if MCP tools included). Add `llms.txt` + `/.well-known/skills/` for agent discoverability (GEO).
2. **X/Twitter:** build-in-public, aerospace Twitter is a massive, engaged niche (SpaceX-community scale). Post demos of skills doing real engineering tasks (e.g., "agent ran a constraint check against DO-178C"). Founder B comp: 12K followers → 47 sales of a $99 skill.
3. **Reddit:** r/AerospaceEngineering (**131–138K subscribers**), r/aerospace, r/AskEngineers, r/CFD, r/spaceflight. Genuine participation + "we built this free library" posts; no hard selling (0.1–0.5% conversion but cheap trust).
4. **LinkedIn:** aerospace is a strong B2B vertical. Post engineering-AI case studies; target engineering managers at Boeing/Airbus/Rolls-Royce/Lockheed suppliers. Founder C comp: 8.5K followers → 23 sales of $299 skill.
5. **Conferences (enterprise wedge):**
   - **AIAA SciTech Forum** — world's largest aerospace R&D event, **4,000–6,000+ attendees, ~1,000–1,100 organizations, 45 countries**; exhibitor/sponsor packages; technical sessions where a skills demo lands with decision-makers.
   - AIAA ASCEND (space), Farnborough International Airshow 2026, Paris Air Show 2027, Dubai Airshow — the big deal-making shows.
   - Budget note: exhibiting at SciTech costs ~$3–10K; sponsor packages more. **Attendance + side-events first, exhibition later.**
6. **Universities:** reach ABET aero programs via department chairs, AIAA student branches, and faculty. Campus license + free student tier.
7. **Content/SEO:** blog posts, YouTube demos, case studies ("we cut requirements-review time 35%" — MBSE+AI reports cite 35% requirements-analysis time reduction). Newsletter as the retention engine.

### 4.3 Positioning angle (moat)

The cybersecurity library won on **framework mapping** (MITRE ATT&CK, NIST CSF). AeroSkills should map to: **DO-178C / DO-254 (avionics certification), ARP4754A (systems), AS9100 (quality), MIL-STD-881 (WBS), EASA Part 21, FMEA/FRACAS, MBSE/SysML 2.0, requirement traceability, airworthiness.** No existing library does this — it's the defensible niche.

---

## 5. Realistic Adoption Path & Revenue Potential

### 5.1 Timeline to €10k MRR (target 2026-11-15, ~11 weeks away)

| Phase | Weeks | Actions | Milestone |
|---|---|---|---|
| **0. Build** | 1–2 | 20–50 high-quality skills (aero, structures, propulsion, GNC, systems, MBSE, certification); agentskills.io standard; Apache 2.0; demos; landing page; newsletter signup | Repo live, 3–5 demo videos |
| **1. Distribution** | 2–6 | GitHub launch post (HN/Show HN), X build-in-public, Reddit genuine posts, LinkedIn case studies, publish to Anthropic Marketplace + 3–4 skill marketplaces; AIAA member communities | **500–2,000 stars**; 500+ newsletter subs; marketplace listings live |
| **2. Monetize** | 6–10 | Launch **AeroSkills Pro** (€29/mo or €199/yr: full library, updates, enterprise templates, support) + premium packs (€99–299 one-time) + enterprise/on-prem (€2–10K/yr) + consulting (€799–2,499 setup) | First 50–100 paid users; 1–3 enterprise pilots |
| **3. Enterprise push** | 10–16 | 1:1 outreach to engineering firms & defense subs; AIAA SciTech (Jan) presence; university campus licenses | €10K+ MRR mix: ~2–4 enterprise deals + 100–200 Pro subs |

### 5.2 Revenue model math to €10k MRR

| Path | Math | Feasibility by Nov 15 |
|---|---|---|
| Premium one-time packs | 35 sales × €299 ≈ €10K | Hard from cold start; possible with 5K+ engaged audience |
| Pro subscriptions | 167 subs × €59 avg ≈ €10K/mo | Not enough time to build 167 subs from zero |
| **Blended realistic** | **2–4 enterprise/team deals (€2–5K) + 50–100 Pro subs (€29–59) + marketplace/one-time sales (€1–2K)** | **€6–12K — achievable only with founder network + aggressive 1:1 outreach** |
| Organic-only median | OSS sponsors + marketplace + a few subs | **€500–2,000/mo in 3 months** (honest baseline) |

### 5.3 Benchmarks for calibration

- Solo skill founders, first month with existing audience: **$1,400–8,483** (500k.io, Q1 2026).
- Median skill-marketplace creator: **$300–1,500/mo**; top decile **$5–25K/mo** (StrongMocha).
- Top 10% of SkillExchange creators: **€2,500+/mo within 6 months**.
- Realistic solo range with vertical expertise: **$500–5,000/mo in 6–9 months; top 10% $10K+/mo** (500k.io).
- Open-source only: 2K–10K stars = **$800–5,000/mo**; 10K+ = $3K–15K/mo.

### 5.4 12–24 month upside

- **Enterprise licensing to defense contractors** (ITAR-friendly on-prem): 10 orgs × €5–10K/yr = €50–100K ARR. Addressable: 1,000+ US primes/subs; plus EU equivalents.
- **University campus licenses:** 20 programs × €2–5K/yr = €40–100K ARR.
- **Integration into AI Department Operator:** skills library as the "domain knowledge layer" — this is the strategic prize. The library de-risks and accelerates the €10K MRR AI Department Operator target by providing the wedge, proof points, and an existing customer base.
- **Marketplace passive income:** Anthropic Marketplace (15% cut) + 3–4 other platforms — small but compounding.

### 5.5 Risks & watch-outs

- **Winner-takes-most marketplaces:** top 5–10 skills per category capture 60–80% of revenue → differentiate via aerospace niche (currently empty) and quality bar.
- **Piracy of file-based skills:** mitigate with subscriptions (updates as the value), hosted access later, enterprise contracts.
- **ITAR/export-control:** skills containing controlled technical data need review; keep the free core generic, gate certification-specific content behind enterprise licenses.
- **Marketplace timeline risk:** Anthropic marketplace is new (May 2026); don't depend on it — direct distribution is the job.
- **€10K by Nov 15 needs a founder-sales sprint:** enterprise deals don't close from content alone; cold 1:1 outreach (5–20% conversion) is the highest-leverage activity in the window.

---

## Sources (selected)

- skill exchange market (SkillExchange pricing playbook, creator economics, monetization guide) — skillexchange.market
- 500k.io — "How to Sell Claude Skills (Pricing, Distribution, the Real Math)" and "Anthropic Skills Marketplace launch 2026"
- StrongMocha — "The Skills Marketplace, Six Months Later: Predicted vs Actual"
- Agensi — "How to Sell AI Agent Skills"; SkillHQ — "How to Make Money Selling Claude Code Skills"
- ClawMerchants — "Per-Access Agent Skills vs One-Time Downloads"
- Claude Lab — "Turning Claude Skills and Claude Code Plugins Into Products That Actually Sell"
- Monetizely SaaS Pricing Benchmark 2025; DollarPocket SaaS benchmarks; CompareTiers 2026; Dupple SaaS Pricing Index
- VendorBenchmark DevOps pricing; Vendr ANSYS buyer guide; Ozen Engineering ANSYS pricing; MathWorks pricing pages
- GitHub: mukul975/Anthropic-Cybersecurity-Skills (31.7K stars); trailofbits/skills; anthropics/skills; agentskills.io spec; Claude Code skills docs
- BLS OES 17-2011 (71,600 jobs, $134,830 median); DataUSA; FRED; AIA 2025 Facts & Figures (2.1–2.2M workforce)
- Dataintelo/GrowthMarketReports/MarketIntelo MBSE-in-aerospace reports; HTF/Technavio/Precedence AI-in-aerospace reports
- Reddit r/AerospaceEngineering (131–138K subs); AIAA SciTech sponsor/exhibit pages; Vendelux aerospace conference list
- ITERNAL (AirgapAI), Zylon AI, VRLA Tech, Sphere — defense/ITAR/CMMC AI deployment

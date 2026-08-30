# AI Agents in Aerospace Engineering — Industry Research Report

**Prepared for:** AeroSkills (aerospace engineering skills library for AI agents)
**Date:** August 30, 2026
**Method:** Web research (industry publications, OEM announcements, arXiv papers, vendor documentation, developer surveys, practitioner accounts). All claims below are sourced to named companies/publications; where a source is weak or unverified it is flagged.

---

## 1. Executive Summary

- **The industry is in the "copilot → pilot" transition.** Every major OEM (Boeing, Airbus, GE Aerospace, Lockheed Martin) has deployed internal generative-AI platforms and is explicitly exploring **agentic AI under human supervision**. But **production-grade autonomous engineering agents are rare**: survey data (Sogeti, 200 A&D orgs, 2026) shows only **8% scaled agentic-AI adoption**; Deloitte expects agentic AI to scale in 2026–2028 in *non-safety-critical* functions first (procurement, logistics, maintenance, admin, decision support).
- **Where AI agents are real today:** (a) internal LLM copilots/chatbots over corporate knowledge (Boeing BCAI, Airbus GenAiR/Gemini, GE "AI Wingmate", NASA-GPT); (b) coding agents for software-adjacent work; (c) **academic/open-source agent frameworks for CFD/FEA/GNC** (Foam-Agent, ChatCFD, FeaGPT, OpenAeroStruct agents) that are credible but not yet certified production tools; (d) **vendor-built agent tooling around engineering software** (MathWorks MATLAB/Simulink Agentic Toolkits, Bentley MCP servers, Siemens Simcenter "Engineering Foundry" vision, Navier AI Stella/Stokes/Ferro).
- **The regulatory wall is the defining constraint.** DO-178C/DO-330 tool qualification, MC/DC coverage, bi-directional traceability, and EASA's new DS.AI rulemaking shape *where* AI can and cannot be used. Consensus view in the industry: **"AI writing flight software" is years away; AI automating the repetitive edges of safety-critical development is happening now** (practitioner consensus, 2026).
- **The most defensible positioning for AeroSkills:** agent skills for the *pre-certification and verification-support* layers — conceptual/systems design, CFD/FEA/GNC simulation setup and post-processing, requirements parsing and traceability, test-case generation, documentation/artifacts, code review, DO-178C evidence assembly — with human-in-the-loop gates. Not autonomous generation of DAL-A flight code.

---

## 2. How Aerospace Companies Actually Use AI Coding Agents & LLMs Today

### 2.1 Boeing
- **BCAI = Boeing's on-premise ChatGPT wrapper** (internal OpenAI models, per employee accounts on r/boeing): usage "at user discretion" in Boeing Global Services; **heavily restricted in defense (BDS) and closed areas**; executives publicly encourage "leaning in." No third-party/cloud models allowed for work. This pattern — internal gated model access with per-business-unit restrictions — is the norm across ITAR-constrained firms.
- **Corporate AI strategy:** four-pillar AI strategy (data foundations, AI platforms, AI talent, business capabilities — per Larridin tracker); Boeing AnalytX analytics platform; 2025 "Shaping AI for the Sky" innovation report explicitly names **"a deep dive into agentic AI, enabling technology to perform tasks autonomously under human supervision"** as a future initiative.
- **Boeing Defense, Space & Security + Palantir (Sept 2025):** deploying Palantir Foundry to standardize data analytics/AI across defense and classified programs.
- **MRO/maintenance AI:** "intelligent aircraft platform with 46+ data products, graph intelligence, and autonomous agents transforming maintenance decisions" (Boeing Global Services principal architect, LinkedIn); Transportation Intelligence Environment (TIE) for military logistics; AI-driven assembly line automation (reported ~50% assembly-time reductions on certain processes via AI-assisted manufacturing).
- **Note:** most public Boeing AI is *data/analytics/ops*, not engineering-design automation. Engineering-side LLM usage is informal (BCAI, personal Copilot) rather than a formalized agent program.

### 2.2 Airbus
- **Company-wide GenAI program:** 2023 working group identified **600–700 use cases** in <1 year; **GenAiR ("Generative AI Responsible")** governance structure with self-assessment, mandatory human validation of every AI decision, and a "human garant" per project. Philosophy: **"AI as an assistant"** — Airbus explicitly says GenAI will *not* design future aircraft from scratch (Fabrice Valentin, head of AI & Advanced Analytics).
- **Deployment stats (2025–26):** ~**€50M/year AI investment**; 250-expert AI community; **half of the 157k workforce using Google Gemini**; 46,000 employees took AI courses in one year; Gemini Workspace access gated behind an ethics webinar + quiz.
- **Concrete engineering use cases:** chatbot over Standard Operating Instructions (manufacturing) — e.g., "which torque spanner for this operation"; engineering assistants; contract analytics; Skywise platform ($200M/yr customer savings).
- **Mistral AI partnership (May 2026):** full Mistral stack on-prem/trusted cloud; collaboration areas include **technical document automation, AI-driven simulations for aircraft part optimization, ad-hoc support to engineers during development/test/certification phases, edge AI on board, and sovereign defense coding assistants**.
- **Avionics AI-engineering team (Toulouse):** intern-level public profiles show LLM agents, RAG pipelines (Pinecone/Vertex AI Vector Search), and Vertex AI Agent Builder being applied to avionics engineering processes.

### 2.3 GE Aerospace
- **"AI Wingmate":** company-wide generative-AI platform on **Azure OpenAI Service** (launched ~2025); "step change in how employees work."
- **Design-side generative AI:** app that "produces hundreds of design iterations for new commercial and military flight engine concepts in seconds instead of months"; **generative-AI design studies for hypersonic ramjets** (completed, public); **AI for Materials** with DARPA (MACH hypersonics program); exascale supercomputing (DOE) for Open Fan design.
- **Quality/engineering assistant:** AI Engineering & Quality assistant "trained on 30+ years of nonconforming hardware data" to standardize part evaluations and traceability.
- **Hiring signals:** AI/ML roles explicitly require "exposure to designing and building **agentic workflows or multi-agent systems**; orchestration frameworks (LangChain, AutoGen, CrewAI)"; RAG/vector DB/LLM-eval skills; 2026: multi-year **$300M AI investment** commitment (per Sogeti report).
- **Manufacturing:** AI-guided White Light Robot inspection ("repeatable results in about half the time").

### 2.4 Lockheed Martin
- **AI Factory ecosystem** + Google GenAI integration (March 2025) for "traceable, reliable, monitored" AI across predictive maintenance, **optimized engineering design**, supply chains, secure software development.
- **AI Fight Club (2026):** LAIC pits AI agents against each other in synthetic aerial combat (Cogniverse); simulated ~114 years of flight tests in a month. (Mission-AI validation, not engineering design.)
- Third-party analyses (StackAI) propose agentic use cases for defense systems engineering: requirements co-pilot + traceability agent, V&V evidence agent, engineering change impact agent, design-reuse/lessons-learned agent, obsolescence agent — with the operating principle **"agents prepare, humans approve"** and "no autonomous engineering changes."

### 2.5 NASA
- **NASA-GPT (Ames):** internally hosted, non-cloud chatbot + AI search over NTRS/JPL TRS and repositories.
- **CARE methodology (Marshall, 2026):** "Collaborative Agent Reasoning Engineering" — a **stage-gated, artifact-driven methodology for engineering LLM agents** with SMEs, developers, and helper agents (vs. trial-and-error prompting). Case study: Earth-science data-discovery agent over the NASA CMR API, beating a baseline (Recall@1 71.7% vs 69.1%).
- Research: LLMs for spacecraft control (fine-tuned Llama-2 thrust commands; GRPO-reasoning controllers), Lunar Gateway "talking" mission-ops assistant concept, runtime-verification toolchain Copilot (deterministic generator, NASA-classified Class D tool) — useful contrast: *deterministic* generators get certified; stochastic LLMs do not yet.
- **NASA's Science Discovery Engine / SMD AI initiative** for data discovery.

### 2.6 SpaceX / new-space & startups
- **Reported acquisition of Anysphere (Cursor) for ~$60B (June 2026, per MSN/NBC/Unite.AI coverage):** if accurate, the strongest signal yet of autonomous coding agents moving into aerospace — cited targets: flight-control software, manufacturing automation, ground ops, Starlink constellation management. (Treat specifics with caution: heavy media coverage, limited independent verification of details.)
- **Anduril:** Lattice AI platform (autonomy); $20B U.S. Army counter-drone contract (2026); aggressive Seattle-area engineering hiring (~1,000 engineers) for AI-driven defense products.
- **AFRL XQ-58A Valkyrie (July 2023):** first flight of ML-trained **AI agents piloting an uncrewed jet** (Skyborg/AACO lineage; trained in sim + X-62 VISTA + HIL). Proves agent autonomy in flight — for autonomy research, not engineering-workflow agents.
- **Forerunner AI (2024):** aerospace copilot startup by ex-SpaceX/Anduril/NASA engineers — natural-language queries over engineering data (Confluence/GitHub), propulsion design assistance, requirements tracking, Slackbot interface. Early-stage.
- **Navier AI:** agent-driven engineering platform — **Stella** (GNC & mission simulation: natural-language prompt → full 6-DOF sims + flight software in Rust, autonomous run-analyze-fix loops, "up to 50x speedup"), **Stokes** (CFD/aerodynamics agent, automated parameter sweeps), **Ferro** (structural analysis agent, beta). Key design choice: physics primitives live in a **validated, human-authored Rust library (StellaRust)**; the agent composes, never invents core math.

### 2.7 Developer-side reality (what individual engineers actually do)
- **Stack Overflow 2025:** 84% of developers use/plan AI tools; 51% daily. **AI agents are not mainstream: only ~14% use agents at work daily; 38% have no plans.**
- **Sonar "State of Code" 2026:** 42% of committed code is AI-generated/assisted; 64% have tried AI agents (25% regularly); top agent uses = documentation, test generation, code review; **enterprises apply more rigorous compliance review to AI code (39% vs 28% SMB)**; top concern = data exposure (57%).
- **LeadDev 2025 (883 eng leaders):** 66% adopted AI in production; Cursor 45%, Copilot 37%; 59% feel productivity up; **60% cite lack of metrics** as top challenge; 54% expect less junior hiring long-term.
- **Aerospace practitioner voices (LinkedIn, 2026):** "The opportunity is not 'AI writing flight software.' The opportunity is engineers using AI to automate the repetitive edges of safety-critical development" — with the caveat that **DO-330 tool qualification of non-deterministic AI tools is unsolved**. Engineers already use AI (Claude Code/Codex/ChatGPT) for: requirements parsing and trace alignment, LLR↔source cross-referencing, test scaffolding, MC/DC test-vector drafting, inconsistency detection in structured documents, compliance-tooling prototypes.

---

## 3. Aerospace Workflows Where Agent Skills Add Value (with concrete tools)

Ranked by (a) value and (b) regulatory feasibility. **Green = safe now; Yellow = pilot-safe with human review; Red = blocked/very hard.**

| Workflow | Toolchain | Agent-skill opportunity | Feasibility |
|---|---|---|---|
| **CFD setup & post-processing** | OpenFOAM, ANSYS Fluent/CFX, STAR-CCM+, SU2, Gmsh, ParaView | Natural-language → runnable case: meshing, BCs, solver config, error self-healing, convergence checks, report generation. **Proven in research**: Foam-Agent (6 specialist agents bound to OpenFOAM stages; 110-case benchmark, 88.2%→100% success w/ Claude Opus 4.6; MCP-exposed), ChatCFD (DeepSeek-R1/V3, RAG, 205 tutorials), MetaOpenFOAM 2.0 (86.9% pass), OpenFOAMGPT. Vendor: Navier Stokes. | 🟢 (non-cert analysis; human-validated results) |
| **FEA / structural analysis** | ANSYS Mechanical, Abaqus, Nastran, CalculiX, Gmsh | Model/load-case setup, mesh adaptation, results extraction, sizing loops. **Proven in research**: FeaGPT (end-to-end agentic FEA), ALL-FEM (fine-tuned LLM, 71.8% code-level success in agentic loop), 2D-frame multi-agent (Llama-3.3-70B), VFEAgent (multimodal). Vendor: Bentley STAAD.Pro MCP server, Navier Ferro (beta). | 🟢 (analysis support) |
| **Conceptual & systems design** | MATLAB/Simulink, Cameo/MagicDraw (SysML), CATIA V5/V6, Rhino+Grasshopper, OpenVSP | Architecture synthesis, configurator scripts, trade studies, UML/SysML drafting. **Proven**: Linköping LLM study (hybrid-electric propulsion config via Python configurators → Hopsan/Modelica); Southampton **WingBuilder copilot** (Grasshopper plugin; user trial with Airbus engineers: hard-task completion 2/6→5/6, time 259s→173s; easy tasks slower). | 🟢 |
| **Flight dynamics / GNC / trajectory** | MATLAB/Simulink, JSBSim, pymap3d, custom 6-DOF | Sim scaffolding, guidance-law drafting, Monte-Carlo campaigns, autopilot gain iteration. **Vendor**: Navier Stella (validated StellaRust primitives; autonomous run-fix loop). **Research**: LLM+GRPO spacecraft control, LLM thrust-command generation, ASTRA (KSP flight agent via Claude Code/Codex). | 🟡 (simulation only; flight code stays human-owned) |
| **Propulsion & engine design** | NPSS, pyCycle, Chemkin/Cantera, GE's internal tools | Cycle-deck setup, component sizing iteration, trade-space exploration. Practitioner report: GPT-4 "works well with small projects, context-window limited; would not trust it to design an engine yet." | 🟡 |
| **Requirements & MBSE (ARP4754A)** | DOORS/DOORS NG, Jama, Cameo, Polarion, Azure DevOps | **Highest near-term ROI**: requirement normalization, ambiguity/conflict detection ("shall" audits), trace-link proposal (req↔design↔test), change-impact analysis, V&V evidence packaging. Vendor/practice: StackAI's LM agentic blueprint; Agents4DevOps DO-178C req management. | 🟢 (proposals gated by human approval) |
| **DO-178C / DO-254 verification artifacts** | VectorCAST, LDRA TBrun, Parasoft C/C++test, AdaCore GNATprobe/SPARK, MATLAB Code Inspector | Draft MC/DC test vectors, traceability matrices, structural-coverage gap analysis, code-review notes, SAS/PSAC draft sections, test procedure templates. **Key constraint:** outputs must be human-reviewed; coverage measurement stays on qualified tools. | 🟡 |
| **Code generation (avionics)** | Ada/SPARK, MISRA C, Simulink→Embedded Coder, QGen | **Autonomous LLM code gen is blocked for DAL-A/B** without tool qualification (DO-330 TQL-1) — currently only deterministic generators qualify (AdaCore QGen TQL-1 for Simulink/Stateflow; Thales autocode generator TQL-2). LLM *assistants* for MISRA-compliant code drafting + SPARK contracts are plausible with review; AdaCore has published an "Agentic AI: migrating C to SPARK" playbook. | 🔴 (autonomous) / 🟡 (assisted) |
| **Materials & manufacturing** | DARPA MACH, additive-mfg toolchains, CMM/CAD inspection | Materials informatics (GE/DARPA), process-parameter optimization, inspection-data review. | 🟢 |
| **Flight test data analysis** | MATLAB, Python, FRED/ARINC-647A decoding | Anomaly triage, sensor-parameter translation, trend reporting (Boeing/NASA patterns). | 🟢 |
| **Certification evidence & compliance** | ARP4754A, DO-178C, EASA/FAA portals | Drafting compliance matrices, gap analysis vs. certification plans, audit-prep evidence assembly, regulatory-question answering grounded in RAG'd standards. | 🟡 (human sign-off mandatory) |

**Cross-cutting enabler — MCP and "skills":** the industry is converging on the **Model Context Protocol** as the agent↔engineering-tool standard:
- **MathWorks:** MATLAB/Simulink **Agentic Toolkits** (MCP tools + "curated skills" for Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI), MATLAB AI Agent SDK, MATLAB MCP Server; press release "MathWorks Enables AI Agents to Execute and Validate Engineering Workflows within MATLAB" (July 2026).
- **Bentley:** MCP servers for STAAD.Pro and MicroStation (structural analysis via natural language; "secure sandbox"); long-term vision of agents orchestrating cross-product workflows.
- **Autodesk:** Fusion MCP server, Product Help MCP; Revit MCP in tech preview (read-only first).
- **Siemens Simcenter:** "Engineering Foundry" research vision for **Agentic AI-Aided Engineering (A³E)** — specialized Task Agents (CFD setup agent, ROM agent, PLM/Teamcenter agent) coordinated by orchestrators, expert-defined workflows; thesis: "covering 80% of standard tasks automatically is enough."
- **Rescale:** MCP server bridging agents to HPC simulation stacks.
- **MCP spec:** "Skills over MCP" working group — structured agent skill distribution is an active standardization area.
- **Open-source:** CAD/CAE Copilot (build123d/OpenCASCADE + CalculiX, SKILL.md agent contracts, approval-gated mutations, V&V-40 credibility tiers, .aieng provenance packages).

---

## 4. Regulatory Context and Its Effect on AI Adoption

### 4.1 The standards stack (what agents must respect)
- **ARP4754A / ED-79A** — development of civil aircraft & systems; requirements-based development assurance; traceability expectations.
- **DO-178C / ED-12C** — airborne software certification. Objectives-based; **DAL A–E** (A = catastrophic, requires MC/DC for structural coverage at statement/decision/condition level). Requires: bi-directional traceability (system reqs → high-level → low-level → source → tests), artifact evidence, independence of verification.
- **DO-330 / ED-215** — tool qualification. **TQL-1…5**; a tool that *creates* flight code needs TQL-1 (qualification process ≈ certifying the tool itself). This is the crux for LLM code generation.
- **DO-331 (model-based dev), DO-332 (OOT), DO-333 (formal methods)** — technology supplements (formal methods can substitute for some testing — relevant to SPARK-style agent assistance).
- **DO-254/ED-80** — airborne electronic hardware.
- **EASA AI framework** — AI Roadmap 1.0 (2020) & 2.0; Concept Papers; **NPA 2025-07 (B): DS.AI** — proposed detailed specifications on AI trustworthiness (consultation; formal rulemaking via RMT.0742, aligned with EU AI Act Art. 108). Introduces **AI levels 0–3** (0: low automation; 1: assistance to human [1A augmentation, 1B decision support]; 2: human-AI cooperation/collaboration; 3: advanced automation [3A supervised, 3B unsupervised]) and **assurance levels (AL) / tool qualification levels (TQL)** for AI constituents. Recognizes **EUROCAE ED-324 / SAE ARP6983** (learning assurance) as acceptable means of compliance. **Key exclusions:** AI in catastrophic-failure-contributing functions, online/adaptive learning, LKB/hybrid AI beyond "no safety effect," and **AI-based verification tools verifying AI-generated artifacts unless a human independently verifies every output**.
- **FAA side:** no equivalent binding AI rule yet — FAA is research/guidance-led (AI/ML technical discipline under AIR, "Roadmap to AI/ML at the FAA," human-factors guidance for AI/ML in FAA systems; favors **Overarching Properties** and incremental/contained applications). FAA historically certifies tools via Order 8110.49 + DO-330.
- **Defense/space:** DO-178C applies to military avionics by contract; NASA uses NPR 7150.2 (class-based) — e.g., the deterministic Copilot RV tool is NASA Class D. **ITAR/EAR/export control** restricts cloud LLM use (classified/export-controlled data cannot touch public models) — a major driver for on-prem/sovereign deployments (Airbus–Mistral on-prem, Boeing BCAI, sovereign defense offerings).

### 4.2 How regulation shapes adoption (honest read)
1. **LLM agents cannot (yet) be certified as flight-code generators.** DO-330 TQL-1 presumes deterministic, requirements-tested tools; LLMs are stochastic, so qualification "as DO-330 currently stands" is widely seen as impossible today. **Consequence:** agents for DAL-A/B code generation stay in research; expectations must be managed.
2. **Agents can safely operate *outside* certification credit paths** — anything supporting the process without being claimed as evidence (drafts, proposals, parsing, triage, internal tooling). EASA's DS.AI even carves out AI-based verification tools only if humans verify outputs — a de-facto "human-in-the-loop required" rule for AI-assisted verification.
3. **The certification-support layer is the realistic target:** traceability matrices, requirements hygiene, MC/DC test-vector drafting (measured on qualified tools), evidence packaging, audit prep — all high-value, human-gated, and currently enormous time sinks (this is where practitioners already use AI).
4. **Agile + DO-178C is explicitly allowed** (RTCA FAS topic paper: no mandated life cycle) — so agent-assisted iterative development can coexist with artifact-based compliance, provided baselines, traceability, and independence rules are respected.
5. **Governance is the gate:** Airbus GenAiR (mandatory human validation), "no autonomous engineering changes" (defense practice), ITAR-secure on-prem models, and workforce readiness (Sogeti: 68% of A&D engineering workforce needs reskilling; biggest capability gap = AI governance/compliance awareness) — adoption will be governed, not viral.

---

## 5. Known Adoptions & Pilots (timeline)

| When | Who | What |
|---|---|---|
| 2023 | Airbus | Company-wide GenAI group; 600+ use cases; GenAiR governance; SOI chatbot |
| Jul 2023 | AFRL | AI agents fly XQ-58A Valkyrie (autonomy, not engineering) |
| 2023–24 | Boeing | BCAI on-prem ChatGPT wrapper; exec push; Palantir Foundry (2025) |
| 2024 | NASA Ames | NASA-GPT internal chatbot/search |
| 2024 | GE Aerospace | AI Wingmate (Azure OpenAI); genAI engine design iterations; DARPA MACH materials |
| 2025 | Lockheed Martin | Google GenAI into AI Factory; AI Fight Club (2026) |
| 2025 | MathWorks | MATLAB/Simulink Agentic Toolkits + MCP server; AI Agent SDK |
| 2025–26 | Bentley / Autodesk / Trimble / Bluebeam / Siemens / Rescale | MCP servers for STAAD.Pro, MicroStation, Fusion, SketchUp, Revu; Simcenter A³E vision; Rescale MCP |
| 2025 | EASA | NPA 2025-07 (DS.AI) consultation |
| 2026 | Airbus–Mistral | Full Mistral stack on-prem; engineering/cert-support, edge AI, sovereign defense |
| 2026 | GE Aerospace | Up to $300M AI investment |
| 2026 | SpaceX | Reported ~$60B Cursor (Anysphere) acquisition for autonomous code engineering |
| 2026 | NASA Marshall | CARE methodology (structured LLM-agent engineering) |
| 2026 | Sogeti survey | Agentic AI scaled adoption in A&D: **8%** (APAC ~20%, China 20–25%) |

**Academic/research frameworks (not yet production):** Foam-Agent 1.0/2.0 (OpenFOAM), ChatCFD, MetaOpenFOAM 2.0, OpenFOAMGPT, OptMetaOpenFOAM, FeaGPT, ALL-FEM, VFEAgent, SimuAgent (Simulink + RL, SimuBench 5,300 tasks), OpenAeroStruct LLM agent (6-agent aerostructural optimization pipeline), Southampton WingBuilder (Grasshopper + GPT-5.4 ReAct copilot), Linköping LLM system-configuration study, LLM-GRPO spacecraft control.

---

## 6. Honest Usability Assessment (for AeroSkills)

**What works today (high confidence):**
- **Knowledge copilots over corporate/regulatory corpora** — RAG'd chatbots over standards (DO-178C, ARP4754A, MIL-STD-882), manuals, SOIs, nonconformance data. Proven at scale (Airbus, GE, Boeing).
- **Simulation-workflow automation** — CFD/FEA case setup, meshing, solver config, error recovery, post-processing, parameter sweeps. Research systems reach 85–100% success on benchmark suites; vendor products (Navier, Bentley MCP, MathWorks toolkits) are shipping. **Caveat:** physics verification still requires human judgment; benchmarks are tutorial-level, not airworthiness-level.
- **Requirements & traceability assistance** — normalization, gap/ambiguity detection, trace-link proposals, change impact, evidence assembly. Low risk (proposals only), highest ROI per unit effort.
- **Documentation/artifact generation** — drafts of PSAC/SAS sections, compliance matrices, test procedures, reports. Universally adopted.
- **Coding agents for tooling/scripts** — the #1 de-facto use ("90% of aerospace problems are software problems," per practitioner; "intern-level for many tasks").

**What is borderline (proceed with guardrails):**
- **MC/DC / verification-artifact drafting** — useful drafts, but coverage *measurement* must happen on qualified tools (VectorCAST/LDRA/Parasoft); audits require human-authored rationale.
- **GNC/flight-dynamics code generation** — excellent in simulation (Navier Stella-style, validated-primitives architecture); flight-code handoff still needs human ownership and qualification pathways.
- **Agentic multi-tool orchestration across PLM/CAD/CAE** — technically demonstrated (MCP), but enterprise data governance, ITAR, and tool-qualification questions are unresolved; expect 2027+ for scale.

**What does NOT work / is blocked:**
- **Autonomous generation of DAL-A/B flight software** — blocked by DO-330 (stochastic tools not qualifiable as TQL-1 today), EASA DS.AI exclusions, and industry consensus. Position it as research/assist, never as a deliverable.
- **Agents as the *sole* verifier of AI-generated artifacts** — explicitly excluded by EASA DS.AI draft (human independent verification required).
- **Cloud models on ITAR/export-controlled data** — hard requirement for on-prem/sovereign inference (Airbus–Mistral on-prem, BCAI pattern).
- **Unsupervised agents in safety decision paths** — "no autonomous engineering changes," human approval gates are industry-standard practice.

**Key market stats to cite:** Sogeti 2026 (200 A&D orgs): 78% prioritize efficiency/automation; 66% see AI as answer to **engineering talent constraints**; agentic AI scaled only 8%; 68% of workforce needs upskilling. Deloitte 2026: US A&D AI spend → $5.8B by 2029 (3.5× 2025); agentic AI in decision-making/procurement/logistics/MRO first; "AI-driven factory operations unlikely before 2028." Deloitte 2025: 81% of A&D firms using/planning AI.

**Strategic recommendation for AeroSkills:** build skills in four tiers —
1. **Knowledge & compliance** (standards-grounded RAG, DO-178C/ARP4754A/EASA guidance, traceability, compliance-matrix drafting);
2. **Simulation orchestration** (OpenFOAM/ANSYS-class case setup + post-processing, MATLAB/Simulink agentic toolkits, MCP-first design);
3. **Design & analysis assistance** (parametric CAD/geometry, conceptual sizing, FEA, flight dynamics — human-gated outputs, provenance packages);
4. **Verification-support** (MC/DC vector drafting, coverage-gap analysis, evidence packaging — explicitly labeled "human review required," integrated with qualified tools).
All skills should ship with: human-approval gates, provenance/audit trails (EASA DS.AI alignment), ITAR/on-prem guidance, and explicit "certification credit: none / assist-only" labeling.

---

## 7. Sources (selected)

Boeing: boeing.com Innovation Quarterly 2025-12 ("Shaping AI for the Sky"); Boeing–Palantir PR (Sep 2025); Larridin AI tracker; r/boeing practitioner thread (BCAI); LinkedIn (BGS AI architecture). Airbus: airbus.com GenAI story (May 2024); Airbus–Mistral PR (May 2026); IMechE Paris Air Show coverage (Jun 2025); La Revue du Digital (GenAiR); HR Leaders podcast. GE Aerospace: geaerospace.com/artificial-intelligence; AI Wingmate PR; DARPA MACH. Lockheed: Sogeti A&D report (2026); TheDefenseWatch (AI Fight Club); StackAI analysis. NASA: NTRS CARE tech memo (202660000926); NASA@SC24 NASA-GPT. SpaceX: Unite.AI / NBC News / MSN coverage of Cursor acquisition (2026). Research: arXiv 2506.02019 (ChatCFD), 2509.18178 (Foam-Agent 2.0), 2502.00498 (MetaOpenFOAM 2.0), 2510.21993 (FeaGPT), S0045782526002586 (ALL-FEM), 2606.16806 (WingBuilder, Southampton), ecp.ep.liu.se (LLM aerospace system design), 2601.05187 (SimuAgent), 2601.04334 (LLM-GRPO control). Regulation: EASA AI Roadmap 1.0/2.0, EASA Concept Paper L1 ML, NPA 2025-07 (DS.AI), MLEAP; RTCA DO-178C/DO-330; FAA AR-06-35 tool-qual handbook; FAA AI/ML discipline pages; EUROCAE ED-324/SAE ARP6983. Vendors: MathWorks (AI Agent SDK, Agentic Toolkits, MCP), Bentley MCP, Autodesk MCP, Siemens Simcenter Foundry, Rescale, AdaCore (QGen TQL-1, SPARK, agentic playbook), Navier AI. Surveys: Sogeti 2026 A&D, Deloitte 2026 A&D outlook, Stack Overflow 2025, Sonar State of Code 2026, LeadDev AI Impact 2025.

# AeroSkills — Smart Router Technical Design Research

Research date: 2026-08-30 · Scope: skill routing in AI agent systems, delivery models, SKILL.md ecosystem, large-collection organization, aerospace-specific router design.

---

## 1. How skill routers work in AI agent systems

**The problem.** Agent hosts expose skills via *progressive disclosure*: at startup they preload only each skill's `name` + `description` (level 1); the full `SKILL.md` body loads only when the agent decides the skill is relevant (level 2); `scripts/`, `references/`, `assets/` load on demand (level 3). The router's job is to make the level-1 → level-2 decision well. In-context routing (listing every skill in the system prompt) collapses at scale: Match@1 drops **0.85 → 0.12 as N grows past ~500** (Enrich-Retrieve-Rank, arXiv 2608.22695). Real registries are far past that (skills.sh lists ~670K skills; benchmarks use ~80K pools).

**Three router architectures dominate:**

| Architecture | How it works | Strengths | Weaknesses |
|---|---|---|---|
| **In-context / LLM-judged** | All skill metadata in system prompt; the model picks | Zero infra, no latency | Dies past ~200–500 skills; token cost grows ~10 tokens/skill |
| **Retrieval → rerank** ("SkillRouter" pattern) | BM25/dense bi-encoder retrieves candidates; cross-encoder reranks full skill text | Best accuracy at scale; body-aware | Needs index build + embedding/reranker infra |
| **Semantic/embedding routing** (aurelio-labs `semantic-router`, LiteLLM auto_router) | Pre-embed route utterances per skill; cosine match at query time, no LLM call | Sub-ms, deterministic, cheap | Brittle on synonyms/overlapping domains; no reasoning about task context |
| **Router-as-skill** (chrishan17/skill-router, AnamKwon/agent-skill-router) | A synthesized router `SKILL.md` per domain; sub-skills get `disable-model-invocation: true` so only the router description stays resident | Constant resident context cost (one description per domain), works inside any SKILL.md host | Extra category-mapping step can mis-route; taxonomy maintenance burden |

**Key empirical findings (SkillRouter, arXiv 2603.22455 — the field's reference paper):**
- **The skill BODY is the decisive routing signal.** Removing body text costs **31–44pp** of routing accuracy across sparse/dense/rerank baselines on an ~80K-skill pool; body-distilled descriptions only partially recover the gap.
- A compact **1.2B body-aware retrieve-and-rerank pipeline (0.6B bi-encoder + 0.6B cross-encoder) hits 74% Hit@1** — beating the strongest 16B pipeline at 13× fewer parameters and 5.8× lower latency (sub-second median on real pools). An 8B+8B scaled config reaches 76%.
- Two training adaptations are essential in *homogeneous* pools (many near-duplicate skills): **false-negative filtering** (+4.0pp) and **listwise reranking** (+30.7pp over pointwise).
- Routing gains transfer end-to-end: better routing → better task success across four coding agents (more pronounced for more capable models).
- Latency/context math: on-demand loading cuts context cost ~99% (≈46.9K → ≈560 tokens/task at ~1K skills).

**Our Veda precedent already matches the state of the art:** `skill-router.py` runs BM25 + tag filtering → dense rerank (local `nomic-embed-text`, 768-dim) over the BM25 top-40 → shortlist; the index stores name/desc/tags/tf but rerank reads the **body from disk on demand** (the decisive-signal finding); 1,018 skills indexed; usage telemetry via `log`/`popular`. Verified 2026-08-28 with 1,018 skills indexed.

**Router-as-skill nuance (AnamKwon/agent-skill-router, benchmarked on Claude Code):** below a few hundred skills on a *lazy-loading* host, the native skill system beats a router (flat selection 100% vs routed 85% at 600 skills). Routers pay off at hundreds-to-thousands scale, on hosts that eagerly load bodies, or in long multi-turn sessions — exactly the regime AeroSkills targets.

---

## 2. Delivery models — comparison

| Model | Mechanics | Context cost | Accuracy @ scale | Distribution effort | Best for |
|---|---|---|---|---|---|
| **Flat skill library** | All skills in one root (`~/.hermes/skills`, `.claude/skills`); host's native discovery | ~10 tokens/skill, linear | Great < ~200 skills; collapses past ~500 | Zero | Small libraries, single-host |
| **Domain-based routing** | Category dirs + one router SKILL.md per domain, leaves hidden (`disable-model-invocation: true`) | Constant (router descriptions only) | Good at 100s–1,000s; ~85% vs flat 100% at 600 in one test | Medium (taxonomy upkeep) | 100s–1,000s of skills, eager-loading hosts |
| **Semantic router** | Embedding index of skill metadata/utterances; cosine at query time | ~0 (index external) | Good recall on well-separated domains; weak on overlap | Low | Cheap stage-1 filter, fast pre-filtering |
| **Smart router (retrieve + rerank)** | BM25/tags → dense rerank over full bodies → top-N shortlist | ~0 until shortlist loads | **Best at scale** (74% Hit@1 @80K) | Medium (index build, reranker) | 1K+ skills, overlapping domains — the recommended backbone |
| **MCP-server-delivered skills** | Skills exposed as MCP tools/resources/prompts (e.g. `pm-skills-mcp`: 59 tools; `skills-server`: metadata-only tool listing + lazy-MCP bridge; MCP working-group SEP-2640 "Skills Extension" standardizing discovery) | Metadata-only listing (~50 tokens/skill), full content on `get_skill` | Independent of client model; selection quality depends on server | Low for consumers (`npx pm-skills-mcp`), high to build | Multi-client distribution, programmatic access, hot-reload/central updates, auth/permissions |

**MCP delivery notes:**
- Proven pattern: **aeroastro.org** ships exactly this for aerospace — an "Aerospace MCP" exposing flight planning, orbital mechanics, aerodynamics, aircraft performance, GNC tools as typed Python functions with `search_aerospace_tools` / `list_tool_categories` discovery, deliberately built for Anthropic's deferred tool loading. Same domain, same delivery question, already solved in MCP form.
- The MCP **Skills-over-MCP working group** (SEP-2640) is standardizing skill representation/discovery inside MCP, coordinating with the agentskills.io content format — an emerging standard, not yet stable.
- Watch-outs: skills-as-instructions (agent reads & follows) vs skills-as-tools (agent calls) are different ergonomics; MCP tool-list bloat reintroduces the selection problem at the tool level; most file-based hosts (Claude Code, Hermes, OpenClaw) consume SKILL.md natively without MCP.
- **pm-skills-mcp case study:** the same 40-skill PM library ships as both file-based skills and an MCP server — the author explicitly maintains both and notes MCP is in "maintenance mode" vs the file-based path being recommended for new users. Strong signal: **filesystem-first, MCP as an adapter, not the primary**.

---

## 3. SKILL.md format (agentskills.io open standard) and how hosts load it

**Format (spec: agentskills.io/specification; Anthropic, Dec 2025):**
```
skill-name/
├── SKILL.md        # required: YAML frontmatter + markdown instructions
├── scripts/        # optional: executable code (run, not read)
├── references/     # optional: docs loaded on demand (REFERENCE.md, FORMS.md, domain files)
└── assets/         # optional: templates, images, data
```
- **Frontmatter:** `name` (required, ≤64 chars, lowercase/numbers/hyphens, must match parent dir name), `description` (required, ≤1024 chars, "what + when", keyword-rich), `license`, `compatibility` (≤500 chars), `metadata` (arbitrary key→value map — the sanctioned place for tags/version/domain), `allowed-tools` (experimental).
- **Body discipline:** recommended < 500 lines (< ~5K tokens); references one level deep from SKILL.md (deep nesting causes partial `head -100` reads); ToC at top of references >100 lines; relative paths only.
- **Validation:** `skills-ref validate ./skill` lints frontmatter + naming.

**How hosts load:**

| Host | Discovery | Loading | Distribution |
|---|---|---|---|
| **Claude Code** | Preloads all name+description into system prompt at startup | Reads SKILL.md via bash Read when triggered; scripts executed without loading; refs on demand | Plugin marketplaces (`/plugin marketplace add anthropics/skills`), skills.sh (`npx skills add`), anthropic/skills repo |
| **Hermes** | System-prompt index of name+description (first ~57 chars visible) grouped by category dirs | `skill_view` loads full SKILL.md on demand; `skill_view file_path` loads linked refs/templates/scripts; slash-command invocation; up to 5 skills stackable per message | `~/.hermes/skills/` source of truth; hub-installed skills; external skill directories; agentskills.io compatible |
| **OpenClaw** | Scans `SKILL.md` up to 6 levels deep under any configured root (grouped layouts); filters at load time by environment/config/binary presence | Name from frontmatter (folder path is organization only) | Precedence: workspace > project `.agents/skills` > personal > managed > bundled/custodian > extra dirs; ClawHub; node-hosted skills; `openclaw migrate` from Codex |

All three implement the same 3-level progressive disclosure; all three are **drop-in targets for a standard SKILL.md library** — the portability argument for authoring to the open spec.

---

## 4. Best practices for organizing large domain collections

**Taxonomy:**
- <100 skills: flat + tags. 100–1,000s: ≤2 levels of domain categories (categories are *organization*, never routing paths — hosts key off frontmatter `name`/`description`).
- **SkillWiki** (arXiv 2606.16523) proposes the governance model: taxonomy of atomic → functional → strategic skills, plus lifecycle states (Raw → Candidate → Draft → Verified → Released → Degraded → Deprecated → Archived) with provenance graphs and Git-style review/version governance.
- **Aerospace precedent — LunCoSim/space-engineering-skills** (real, domain-organized): categories = Architecture, Management, Analysis, Operations, Programmatic, Cost & Production, Human Spaceflight, Constellation, Ground Segment; skills *reference each other in chains* (requirements-manager → trade-study-manager → domain assessments → v-and-v-manager). Soljourner/claude-engineering-skills: 100+ skills in Databases/Packages/Integrations/Helpers/Thinking. These are the models to crib.

**Naming (Claude platform best practices):** consistent kebab-case; gerund form (`process-pdfs`) or noun phrases (`pdf-processing`); avoid `helper`, `utils`, `tools`, `documents`, `data`; avoid reserved words (anthropic, claude); consistent pattern across the whole collection.

**Descriptions are the router:** one field, ~50–150 words, "what it does + when to use it + specific trigger keywords". Write for the orchestrator, not the human. This single field dominates selection quality at every scale — it is the highest-leverage authoring investment.

**Metadata:** use the spec's `metadata` block for `domain`, `tags`, `version` (SemVer), `author`, `license`; vendor-prefix proprietary fields; add `compatibility`/`model_min` for environment floors. Geodocs' manifest spec adds registry-grade fields: `version` (SemVer, required for registry publishing, immutable once published), `homepage`, `tags`, `inputs`/`outputs` schemas, `tools` (expected MCP servers), `requires_network`, `requires_filesystem`.

**Versioning:** SemVer in frontmatter; treat published versions as immutable (bump, never rewrite); registry convention `/skills/<name>/<version>/SKILL.md`; CHANGELOG; lint with `skills-ref validate`; CI-gate skill changes.

**Governance loop:** usage telemetry (Veda's `log`/`popular`), review/approval for new skills (OpenClaw "Skill Workshop"), periodic re-evaluation (SkillWiki's self-management agents detect degradation → propose evolution).

---

## 5. Recommended AeroSkills smart-router architecture

**Recommendation: filesystem-first SKILL.md library + two-stage retrieve-rerank router (the SkillRouter/Veda pattern) + optional MCP adapter.** Rationale: the research is unambiguous that (a) body-aware retrieve→rerank is the accuracy leader at scale, (b) the SKILL.md spec gives free portability across Claude Code/Hermes/OpenClaw/Codex, (c) MCP is a distribution *adapter*, not the backbone (pm-skills-mcp and the MCP WG treat skills content as agentskills.io).

**Layer 1 — Content (what gets routed):**
- Author every skill to the agentskills.io spec: ≤64-char kebab-case name, ≤1024-char description with explicit "Use when …" triggers, body <500 lines, refs one level deep.
- Organize by an aerospace taxonomy (≤2 levels), e.g.: `aircraft-systems/` (airframe, propulsion, avionics, flight-controls), `operations/` (flight planning, MRO, dispatch, ATC), `space-systems/` (orbital mechanics, GNC, propulsion, thermal, power, comms), `engineering/` (aero, structures, systems engineering, V&V, cost), `regulatory/` (FAA/EASA/ICAO, DO-178C/DO-254, ATA chapters). Crib category structure from LunCoSim; map to ATA chapters where applicable since aerospace engineers already speak that taxonomy.
- Every skill carries `metadata: {domain: <slug>, tags: [...], version: semver}`.

**Layer 2 — Router (how skills get selected):**
1. **Stage 0 (cheap pre-filter):** optional semantic/tag filter if the library is huge; skip at 100s scale.
2. **Stage 1 (retrieve):** BM25 + tag boost over name/description/body (Veda-proven). Index body text, not just metadata — body is the decisive signal (31–44pp).
3. **Stage 2 (rerank):** dense cross-encoder over top-20/40 candidates reading full skill text from disk; local model (nomic-embed-text/bge-m3, or a fine-tuned 0.6B reranker if budget allows — 74% Hit@1 is achievable at that size).
4. **Stage 3 (constrain):** the agent loads the top 1–5 shortlist via its native skill loader (`skill_view` in Hermes, bash-read in Claude Code, auto in OpenClaw) — never enumerate the pool in-context.
5. **Feedback:** log every selection → popularity signal → description/index refinement loop; run a small evaluation harness of realistic aerospace tasks (e.g., "size a battery for a 12U CubeSat", "draft a preflight weight-and-balance sheet", "plan an engine-overhaul checklist") to track Hit@1 as the library grows.

**Layer 3 — Delivery (how customers get it):**
- **Primary: file-based.** A repo (like LunCoSim/space-engineering-skills or anthropics/skills) installable via `npx skills add AeroSkills/aerospace-skills`, manual copy, or Hermes external skill directories. Works on every host listed in §3 with zero integration.
- **Secondary: MCP server** exposing the same catalog (metadata-only tool listing + `get_skill`/`search_skills` tools + optional `list_skill_categories`), following the aeroastro.org pattern; ideal for multi-client/enterprise programmatic access and centralized updates. Keep it an adapter — the SKILL.md files stay the source of truth.
- **Optional: router-skills for eager-loading hosts** — one synthesized domain router SKILL.md per category with `disable-model-invocation: true` on leaves (chrishan17 pattern) if customers run hosts that eagerly load bodies; only adopt where flat metadata is measurably losing (the AnamKwon benchmark says routers lose below ~600 skills on lazy-loading hosts).

**Decision table:**

| AeroSkills stage | Library size | Recommended delivery |
|---|---|---|
| Launch (tens of skills) | < 100 | Flat library + tags; native host discovery; skip the router |
| Growth (100s) | 100–600 | Domain category dirs + BM25-tags retrieval router (Veda pattern); optional router skills |
| Scale (1,000+) | 600+ | Two-stage body-aware retrieve→rerank router (0.6B local reranker viable); router skills per domain; MCP adapter for enterprise clients |

**Risks / gotchas:**
- Don't let MCP become the primary: the ecosystem's own case studies (pm-skills-mcp) and the Skills-over-MCP WG treat SKILL.md files as the canonical format; MCP is still stabilizing (SEP-2640).
- Taxonomy is organization, not routing: hosts name skills from frontmatter — keep category dirs shallow and description-driven.
- Reranker failure mode: indexer must follow symlinks and read bodies on demand (Veda pitfall: `Path.rglob` misses symlinked libraries).
- Router accuracy is bounded by description quality — invest in "what + when + triggers" descriptions before adding routing machinery.

---

## Sources
- SkillRouter (arXiv 2603.22455, GitHub zhengyanzhao1997/SkillRouter) — body-aware retrieve-rerank, 80K pool, 74% Hit@1
- Enrich-Retrieve-Rank (arXiv 2608.22695) — in-context routing collapse at ~500 skills
- agentskills.io/specification — open SKILL.md standard; anthropics/skills; Anthropic engineering blog "Equipping agents for the real world with Agent Skills"
- Claude Platform docs — skill authoring best practices (naming, descriptions, progressive disclosure)
- Hermes docs (hermes-agent.nousresearch.com — Skills System; work-with-skills)
- OpenClaw docs (docs.openclaw.ai/tools/skills)
- chrishan17/skill-router; AnamKwon/agent-skill-router (benchmarks); aurelio-labs/semantic-router; LiteLLM auto_router
- MCP: Skills-over-MCP WG / SEP-2640; pm-skills-mcp; ivanenev/skills-server; aeroastro.org Aerospace MCP
- skills.sh (Vercel registry, `npx skills add`, 20+ agents, ~670K skills)
- LunCoSim/space-engineering-skills; Soljourner/claude-engineering-skills; geodocs agent-skill-manifest spec; SkillWiki (arXiv 2606.16523)
- Veda internal: `productivity/skill-router` skill (BM25+tags+dense rerank, 1,018 skills, verified 2026-08-28)

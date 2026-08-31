# Peer Skill Repo Audit — input for AeroSkills README v0.2

Date: 2026-08-31
Author: Scout (Research)
Track: P3.4 REWORK. Founder verbatim: "audit readme - its not designed very
well either - refer to other such skill repos to see how they do everything.
run an audit of them first."

Scope: README structure (badges, TOC, tables, install), harness-integration
documentation (Claude Code, Codex, Gemini CLI, Cursor, Copilot, OpenCode,
agentskills.io, OpenClaw, Hermes), skill-catalog and expansion presentation.
Output: patterns + recommendations for README v0.2.

## Method and receipts

- All 5 repos fetched LIVE via GitHub API on 2026-08-31:
  `gh api repos/<owner>/<repo>` for metadata, `gh api repos/<owner>/<repo>/readme
  -H "Accept: application/vnd.github.raw"` for raw README text.
- Star counts are live API reads, not quoted numbers (field lesson: K-Dense
  stars have been misquoted as 31.9k/38.0k in past sessions; live reads
  2026-08-31 are below).
- Raw READMEs kept as process artifacts in /tmp/peeraudit (re-fetchable via
  the commands above).

| Repo | Stars (live) | Forks | License | README size | Type |
|---|---|---|---|---|---|
| K-Dense-AI/scientific-agent-skills | 39,855 | 3,707 | MIT | 72.9 KB / 952 lines | domain library (science) |
| mukul975/Anthropic-Cybersecurity-Skills | 31,756 | 3,826 | Apache-2.0 | 31.2 KB / 465 lines | domain library (security) |
| AminBlg/SimpleEnglish | 3,010 | 105 | MIT | 12.4 KB / 219 lines | single-skill showcase |
| VoltAgent/awesome-agent-skills | 33,419 | 3,535 | MIT | 248.7 KB / 2,002 lines | curated catalog |
| VoltAgent/awesome-openclaw-skills | 52,275 | 5,010 | MIT | 134.0 KB / 1,262 lines | registry-derived catalog |

## 1. K-Dense-AI/scientific-agent-skills — the closest analog

AeroSkills' direct peer: domain library, standards-adjacent content,
script-shipping skills; K-Dense at 39,855 stars. README is the most complete of the five.

README structure:
- 14 badges: license, version (from pyproject.toml), skill count, database
  count, two standards badges (Agent Skills + Agent Plugins), TWO CI badges
  (security-scan.yml, skill-tests.yml), "Works with Cursor | Claude Code |
  Codex | Google Antigravity", 4 social badges (X/LinkedIn/YouTube/Reddit).
- Callout banner stack before the TOC: rename notice, BYOK product promo,
  webinar link, social follow line.
- Full TOC, 16 anchors.
- "What's Included" — counts by bucket: 163 skills / 100+ databases /
  70+ package skills / 9 integrations / 30+ analysis tools / 10+ research tools.
- Install = 3 options + host fallbacks (see harness integration below).
- Security Disclaimer: "Skills can execute code and influence your coding
  agent's behavior. Review what you install." Cisco AI Defense skill scanner,
  weekly scans, results published to docs/security-report.md.
- Prerequisites: Python 3.13+, uv, client, OS; uv install instructions for
  macOS/Linux/Windows.
- Quick Examples: 6 worked research prompts, each ending with a
  "Skills Used: <names>" line. Shows the library doing real work before
  listing it.
- Use Cases: per-domain bullet lists.
- Available Skills: categories with counts (e.g. "Bioinformatics & Genomics
  (27 skills)") and short bullets; points to docs/skills.md for the full list.
- Blog: 19 links organized into 5 groups (start here / benchmarks /
  workflow layer / security / complementary projects).
- Contributing: fork-branch-PR steps, guideline checklist, testing
  requirement (tests/_meta structural contract), security scanning.
- Troubleshooting (6 problems incl. one real historical breakage: the
  scientific-skills/ → skills/ rename in v2.43.0), FAQ (12 Q&As in 3
  groups), Support, Citation (BibTeX/APA/MLA/plain), License + per-skill
  license warning, Star History chart.

Harness integration documentation:
- Option 1 `npx skills add K-Dense-AI/scientific-agent-skills` — "common
  standards-based installer for supported Agent Skills hosts, including
  current versions of Claude Code, Claude Cowork, Codex, Gemini CLI, Google
  Antigravity, and Cursor".
- Option 2 `gh skill install` (GitHub CLI v2.90+): per-agent flags
  (`--agent cursor|claude-code|codex|gemini`), version pinning
  (`--pin v2.65.0` / `--pin <sha>`), update flow (`gh skill update --all`).
- Option 3 Agent Plugins 1.0.0 package (plugin.json + skills/): exact Cursor
  symlink commands into ~/.cursor/plugins/local, `codex plugins install .`.
- Other hosts: manual clone into ~/.agents/skills/ or .agents/skills/
  (user vs project level), `hermes skills tap add`, NemoClaw/OpenShell
  network pre-approval note. Caveat that hosts vary on frontmatter support.
- Explicit "verify behavior on the target host" honesty — no false promises.

Catalog + expansion:
- Catalog lives in the README (categories with counts), full list in docs/.
- Expansion documented: CONTRIBUTING.md + tests/_meta contract + scanner.

What AeroSkills can take: the 3-option install ladder with per-host commands;
CI badges; version badge; Security Disclaimer; Quick Examples with
"Skills Used" lines; category counts; "verify on your host" honesty.
What NOT to copy: "used by 190,000+ scientists" (unverifiable claim,
violates verify-before-credit); social badge wall; 952-line length.

## 2. mukul975/Anthropic-Cybersecurity-Skills — best structure for AeroSkills' standards map

Anthropic-Cybersecurity-Skills at 31,756 stars. The closest template for AeroSkills' differentiator (standards
mapping) and for the 12-skill catalog table.

README structure:
- Banner image, centered title, tagline "The largest open-source
  cybersecurity skills library for AI agents".
- 14 badges: license, skills count (818), frameworks count (6), MITRE F3,
  domains (34), platforms (26+), GitHub stars/forks/last-commit,
  agentskills.io standard, PRs welcome, + 2 affiliate badges (survey,
  playground). Includes a "Hermes Agent compatible" badge.
- TOC: 5 anchors only.
- Two disclaimers up front: community-project (not affiliated with
  Anthropic) + authorized-use warning (offensive skills, responsible use).
- "Six frameworks, one skill library": framework table (version, scope,
  what it maps) + a 2-row example mapping table (skill → per-framework
  technique IDs) + a per-tactic coverage table (tactic | ID | skills).
  Claims are verification-backed: "all 123 F3 v1.1 technique IDs were
  verified against the upstream STIX bundle."
- Quick start: `npx skills add` OR `git clone` — two commands, nothing else.
- What's Inside: 34-domain table (domain | skills | key capabilities) — the
  single best catalog format in this audit.
- "How AI agents use these skills": token-cost progressive disclosure
  (~30 tokens to scan frontmatter, 500-2,000 to load) + a worked agent
  internal process (scan 818 frontmatters → load top 3 → execute → verify).
- Skill anatomy: directory tree, real YAML frontmatter example, Markdown
  body sections (When to Use / Prerequisites / Workflow / Verification).
- Compatible platforms: 4 groups naming 26+ platforms (AI code assistants /
  CLI agents / autonomous agents / agent frameworks & SDKs) + "All platforms
  that support the agentskills.io standard can load these skills".
- Social proof: testimonials with links, "Featured in" table (awesome lists,
  directories), contributor avatar grid.
- Releases table (version | date | highlights) — signals motion even with
  one release.
- Contributing: SCOPE.md first, one skill per PR, title convention, thin-
  domain callout ("Data Protection and Purple Team have one skill each").
- Citation (BibTeX), License, star/fork/discuss/contribute footer.

Harness integration documentation: thinner than K-Dense (npx + clone +
platform name lists) but the "4 groups of compatible platforms" presentation
is the cleanest way to show breadth without per-host commands.

Catalog + expansion: domain table with counts; SCOPE.md + one-skill-per-PR +
thin-domain callouts drive expansion toward gaps.

What AeroSkills can take: framework/standards mapping table format (directly
mirrors standards-map.yaml); domain catalog table (domain | skills | key
capabilities); token-cost progressive disclosure explanation; skill-anatomy
+ frontmatter example; compatible-platforms 4-group list; releases table;
authorized-use/responsible-use notice pattern (AeroSkills' compliance notice
is the aerospace equivalent — peers make it prominent, not a footnote).
What NOT to copy: affiliate survey badge, playground promo, testimonial wall.

## 3. AminBlg/SimpleEnglish — single-skill showcase, best install section

3.0k stars. One skill, aerospace-adjacent (ASD-STE100 — the controlled
language used by aviation). Proves install documentation is the
differentiator.

README structure:
- 6 badges, all evidence-carrying: "STE violations −74.6% measured",
  "benchmarked on 7 Claude models", agentskills.io standard, version 1.3.0,
  MIT, stars. Plus a Trendshift badge.
- TOC: 6 anchors.
- Before/after table FIRST (real unedited model output vs skill output) —
  demo before explanation.
- Install section — 5 paths, the best in the audit:
  1. `npx skills add AminBlg/SimpleEnglish` (primary; CLI detects Claude
     Code, Cursor, Codex, Copilot, Gemini CLI "and more")
  2. `npx skills use ...@simple-english` (try before installing)
  3. Claude Code plugin marketplace (`claude plugin marketplace add` +
     `claude plugin install`)
  4. Claude Code output style (/config → Output style) — always-on variant
  5. Prompt-paste fallback for hosts with no SKILL.md support
     (prompts/system-prompt.md + a ~60-token version)
- No-terminal paths: claude.ai upload steps, ChatGPT custom instructions,
  Gemini Gem — covers web/consumer surfaces peers ignore.
- "The rules": table (STE rule | what it kills) — educational, not
  marketing.
- Benchmarks: 7-model table + Pi cross-check (4 models) + blind pairwise
  judge + method + reproduction command (`python3 evals/run_bench.py`).
  Every number has a receipt.
- Receipts: TDD story, community audit issue link, A/B fix test.
- FAQ (4 Q&As), license note (paraphrased, zero spec text, not affiliated
  with ASD/STEMG).

Harness integration: the deepest per-host coverage of the five (5 install
paths + web-app fallbacks), and the only one documenting a "try before
install" path.

Catalog + expansion: single skill — N/A, but the repo layout (skills/<name>/
SKILL.md + references/ + evals/) is the model for one-skill-per-folder.

What AeroSkills can take: try-before-install (`npx skills use`); per-host
install paths incl. no-terminal/web fallbacks; evidence badges
("−74.6% measured") over vanity badges; receipts section; the honesty that
"this README breaks half of the rules; marketing is out of scope" — voice
matches AeroSkills' cold-truth rule.
What NOT to copy: before/after marketing tables are harder for a 12-skill
library (AeroSkills has eval gates instead — show gate output, not prose).

## 4. VoltAgent/awesome-agent-skills — curated catalog

33.4k stars. 1,497+ skills from official teams + community.

README structure:
- Banner, tagline "Hand-picked, not AI-slop generated".
- 5 badges (Awesome, Skills Count 1497+, Last Update, VoltAgent, Discord).
- Sponsors section (2 paid placements + "Become a Sponsor") — monetized
  awesome list.
- TOC: 4-column anchor table by publisher team.
- Catalog: <details> sections per publisher; entry format
  `**[owner/skill](url)** - description`. Collapsible keeps 248 KB readable.
- Security Notice: "curated, not audited" + scanner recommendations.
- **Skills Paths table** (the harness-integration artifact): Tool | Project
  Path | Global Path | Official Docs — Antigravity, Claude Code, Codex,
  Cursor, Gemini CLI, GitHub Copilot, OpenCode, Windsurf. (Hermes missing —
  a real gap; K-Dense documents hermes skills tap add.)
- Skill Quality Standards: description (third person, what + when, agent
  keywords), progressive disclosure (<100 tokens metadata, <500-line body),
  no absolute paths, scoped tools — matches AeroSkills' desc-lint gate.
- Contributing: "don't submit skills you created 3 hours ago" — quality bar.

Harness integration: the paths table IS the integration doc. No install
commands — it is a catalog, entries deep-link to officialskills.sh.

Catalog + expansion: catalog is the README; expansion via PR with quality
bar + CONTRIBUTING.md.

What AeroSkills can take: the Skills Paths table format (project/global path
+ docs per host) — the single most copyable artifact in this audit;
collapsible <details> for long sections; quality-standards section.

## 5. VoltAgent/awesome-openclaw-skills — registry-derived catalog

52.3k stars (awesome-openclaw-skills). 5,300+ skills filtered from the official ClawHub registry.

README structure:
- Banner, tagline "Discover 5300+ community-built OpenClaw skills,
  organized by category".
- 5 badges (Awesome, Skills 5200, Last Update, VoltAgent, Discord).
- Installation (3 routes): `openclaw skills install <slug>`, `npx clawhub
  install <slug>`, manual copy table (Global ~/.openclaw/skills/ vs
  Workspace <project>/skills/ + priority order).
- "Why This List Exists": filter-transparency table (excluded: 4,065 spam,
  1,040 dup, 851 low-quality, 886 crypto, 373 malicious = 7,215 total) —
  the best trust signal in the audit.
- Contribution rule: only registry-published skills (no personal repos).
- Ecosystem tools section: paid placements (SerpApi, trentclaw).
- Security Notice: "curated, not audited" + VirusTotal partnership +
  scanner list (Snyk agent-scan, Agent Trust Hub).
- TOC: 3-column table with per-category counts.
- Catalog: <details> per category, clawskills.sh links, "View all N skills
  →" pointer to per-category .md files — pagination for a 5k-entry list.

Harness integration: OpenClaw-only (it is a single-harness collection) —
one CLI + one manual table. Narrow but complete for its host.

Catalog + expansion: registry-sourced; expansion = publish to registry
first, then PR here.

What AeroSkills can take: filter-transparency table (AeroSkills' 5-gate
definition of "verified" deserves the same explicit what-was-checked
treatment); the manual-install paths table; "view all →" pagination pattern
for the future 12+ discipline catalog.

## Cross-repo patterns (what the best all do)

1. Badge row up top — 5-14 badges. Core set: license, skill/library count,
   agentskills.io standard, last commit, version. Winners add CI status
   (K-Dense ×2) and evidence badges (SimpleEnglish measured result).
2. TOC — every repo has one; short (5-7 anchors) beats long (16).
3. Install section is the differentiator. Every top repo leads with
   `npx skills add <owner>/<repo>`; the best add try-before-install, gh
   skill with --agent flags, plugin/packaging routes, manual path tables,
   and no-terminal/web fallbacks. One-command clone+validate is the
   minimum, not the ceiling.
4. Harness integration is explicit and per-host: a platform list (4-group
   format) OR a paths table (tool | project path | global path | docs) OR
   per-host commands (K-Dense, SimpleEnglish). "Works with any
   agentskills.io host" is claimed by all and then substantiated per host.
5. Security/trust section is now standard: "skills execute code — review
   what you install", scanner tooling, curated-not-audited disclaimers,
   responsible-use warnings. Domain libraries (K-Dense, cybersecurity) make
   it prominent.
6. Catalog = table with counts + one-line descriptions. Domain table
   (cybersecurity) and category counts (K-Dense) beat plain bullet lists.
   Long catalogs use <details> + "view all" pagination.
7. Evidence: benchmark tables with method + reproduction command
   (SimpleEnglish), CI badges (K-Dense), verification claims with receipts
   (cybersecurity STIX check). Stars ≠ quality — the repos themselves say
   so ("stars are a popularity signal, not a quality review").
8. Expansion is documented in-README: CONTRIBUTING.md link, one-skill-per-
   PR, thin-domain callouts, quality standards.
9. License clarity: repo license + per-skill license warning (K-Dense,
   cybersecurity), affiliation disclaimers (not Anthropic, not ASD).
10. Honesty conventions: "verify behavior on your host" (K-Dense),
    "marketing is out of STE scope" (SimpleEnglish), "curated, not
    audited" (both VoltAgent lists). Buyers reward the caveat.

## Current AeroSkills README v0.1 gaps (verified against file, 6.3 KB / 144 lines)

1. No badges at all — peers lead with 5-14.
2. No TOC — buyers must scroll a 144-line compliance-heavy doc.
3. Install = one clone+make validate block. No npx skills add, no gh skill,
   no per-host paths, no try-before-install. Hosts named in one sentence
   ("Claude Code, Hermes, OpenClaw, Codex") with no commands.
4. Catalog = 12 plain bullets. No table, no per-domain counts, no DAL/scope
   column, no standards-mapped column.
5. No harness-integration section: no platform list, no paths table, no
   per-host commands. Frontmatter declares compatibility; README does not
   show it.
6. Evidence in prose only: "make validate runs 5 REAL gates" — no gate
   table, no badge, no per-gate reproducibility. Standards map mentioned
   but no mapping table (cybersecurity shows how).
7. No security/review section. AeroSkills skills ship scripts (same risk
   profile as K-Dense) but there is no "review what you install" guidance
   beyond the compliance notice.
8. No contributing/expansion path in the README (CONTRIBUTING.md exists but
   is footer-linked only).
9. No version line/badge; "Draft v0.1" in prose; no last-commit signal.
10. Compliance notice is buried mid-page for the buyer's first screen —
    it is AeroSkills' unique asset and should be a headed, linked section,
    not a wall of blockquotes above the value proposition.

## Recommendations for README v0.2 (ordered by impact)

1. Badge row (7): Apache-2.0 license · version (add a VERSION file or reuse
   pyproject) · skills count (12) · standards mapped (9) · agentskills.io ·
   "5/5 gates" (static until CI exists; add CI badges when CI lands) ·
   last commit. No stars badge while private — never fake one.
2. TOC: Why · What's here · Standards map · Install · Harness integration ·
   Evidence · Security · Contributing · Roadmap · License. Keep the
   compliance notice as a headed section near the top, linked from TOC.
3. Install ladder (3 options + table): Option 1 clone + make validate
   (existing); Option 2 `npx skills add arjun-0077/aeroskills` when public;
   Option 3 per-host manual table modeled on VoltAgent's paths table:
   Claude Code (.claude/skills/, ~/.claude/skills/), Codex
   (.agents/skills/, ~/.agents/skills/), Cursor (.cursor/skills/),
   OpenCode (.opencode/skills/, ~/.config/opencode/skills/), Hermes
   (verify — hermes skills tap add per K-Dense, confirm against Hermes
   docs before writing), OpenClaw (~/.openclaw/skills/). Add a
   "verify paths against your host's current docs" line (K-Dense honesty).
4. Catalog table: skill path | domain | one-line what-it-does | DAL/scope |
   standards mapped | gate status. Model: cybersecurity domain table.
   Keep per-domain counts. Move the 12-bullet list into the table; full
   per-skill detail stays in skills/.
5. Harness integration section: "Compatible hosts" 4-group platform list
   (cybersecurity format) + the paths table + SEP-2640 MCP adapter as the
   enterprise differentiator (no peer has it — say so).
6. Evidence section: gate table (gate | what it checks | how to run) for
   the 5 gates + make validate + link docs/harness-contract.md. State what
   verified does NOT mean (already in v0.1 — keep, it is the compliance
   notice's peer: "not certification, not approval, not airworthy").
7. Security section (5 lines): skills ship scripts and execute code; review
   SKILL.md before use; no-verbatim gate means standards are referenced,
   never copied; report via SECURITY.md. Add scanner recommendation once
   adopted.
8. Contributing (5 lines): read CONTRIBUTING.md, one skill per PR, must
   pass make validate (5/5) + attest, thin-domain callout (space/ecss = 1
   skill, mbse = 1 — next authoring pass targets).
9. FAQ (5 Q&As, K-Dense format): license? is it certification? export
   control? how are skills verified? affiliated with RTCA/SAE? — answers
   already exist in the compliance notice + Evidence; compress them.
10. Keep, don't copy: keep the compliance notice (unique asset), the
    verify-before-credit voice, the draft/founder-gated honesty (peers ship
    stable; AeroSkills must not overclaim). Do NOT copy: sponsor sections,
    testimonial walls, star-history charts, unverifiable user-count claims,
    AI-slop taglines.

## Verification

- Fetch + metadata commands: see Method. Raw READMEs in /tmp/peeraudit.
- Live numbers 2026-08-31: K-Dense 39,855★; cybersecurity 31,756★;
  SimpleEnglish 3,010★; awesome-agent-skills 33,419★;
  awesome-openclaw-skills 52,275★.
- AeroSkills v0.1 README verified at 144 lines / 6.3 KB; SKILL.md frontmatter
  carries `compatibility: "agentskills.io SKILL.md; any SKILL.md host
  (Claude Code, Hermes, OpenClaw)"`; Makefile exposes 5 gates + attest.

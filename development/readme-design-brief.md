# AeroSkills README — Design Brief (draft, research-backed)

**Date:** 2026-09-01 · **Status:** in-progress (3 parallel research agents running)
**Owner:** CEO (Arjun) · **Gate:** founder review before release

## Goal

Make the AeroSkills README the highest-class README in the agent-skills
ecosystem. It must convert viewers in the first 10 seconds, prove value
with evidence (not promises), and scale visually to 1,460 skills.

## First-hand research findings (this session)

### 1. Addy Osmani `addyosmani/agent-skills` — the gold standard for skills READMEs
Patterns observed (extracted directly):
- **Bold one-line value prop** first: "Production-grade engineering skills for AI coding agents."
- **Hero image** (branded banner) immediately after the one-liner
- **ASCII lifecycle diagram** (DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP) — tells the story visually
- **Commands table** (9 slash commands, what/why)
- **Quick Start FIRST** — before anything else: `npx skills add addyosmani/agent-skills`
- **Skills table**: `Skill | What It Does | Use When` — the canonical catalog pattern
- **Why section** — the philosophy: "AI coding agents default to the shortest path... Agent Skills gives agents structured workflows"

### 2. ComposioHQ/awesome-claude-skills (74K★, 1,000+ skills)
- **Category-based navigation** (9 categories) — how to handle large catalogs
- **Quickstart-first with real commands**
- **Education section** ("What Are Claude Skills?")
- Massive star count = social proof; badge bar on top

### 3. vercel-labs/skills (30K★) — the install mechanism
- `npx skills add owner/repo` is THE standard install path (70+ agents)
- README must feature this prominently — one-command install = zero friction

### 4. shadcn/ui (122K★) — restraint is premium
- Minimal README: one-liner, hero image, docs link. No badge spam, no walls of text
- "Use this to build your own component library" — confident, specific

### 5. htmx — ultra-compact
- Value props as inline links ("small, dependency-free & extendable")
- Every line earns its place

### 6. awesome-readme elements (matiassingers/awesome-readme)
- Logo/banner, informative badges, TOC, screenshots/GIFs, clear install, links
- "Elements in beautiful READMEs include: images, screenshots, GIFs, text formatting"

## Design principles synthesized (so far)

1. **First 10 seconds = value + proof.** One-liner, hero, evidence. No "welcome to our repo" filler.
2. **Quick start above the fold.** Install in one command, run in 2 minutes.
3. **Evidence over claims.** "Replayable by anyone: clone, run make validate, exit 0."
4. **Catalog scales with tables + categories**, not walls of links.
5. **Badges are metadata, not decoration** — only real signals (license, gates, skills count, standards).
6. **Restraint.** Fewer sections, each earning its place.
7. **Both audiences:** humans (10-second scan) AND AI agents (machine-readable install, routing).
8. **The lane is empty** — own the "aerospace knowledge layer" positioning explicitly.

## AeroSkills-specific assets (from positioning doc)
- One-liner: "The aerospace engineering knowledge layer for AI agents"
- Wedge: the standards map (20 standards, machine-readable, no aerospace repo has this)
- Proof: 5 REAL gates, make validate, Hit@1 routing
- The lane: aerospace unserved (~228★ total across all attempts); adjacent domains (Anthropic-Cybersecurity-Skills 31.7K★) prove the play
- Compliance posture: methodology not designs, no certification claims

## Open questions (agent reports pending)
- Exact hero visual technique (SVG vs PNG banner vs ASCII)
- Optimal catalog presentation at 1,460 skills (per-pack tables? index?)
- Badge set that maximizes trust without noise
- Whether to include a "for agents" vs "for humans" split view

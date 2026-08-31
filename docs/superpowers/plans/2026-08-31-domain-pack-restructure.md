# AeroSkills Domain-Pack Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure skills/ into five installable domain packs per the 12-discipline taxonomy (research/briefs/05-domain-taxonomy.md), each with a router SKILL.md and domain/pack frontmatter, per founder directive 2026-08-31.

**Architecture:** Filesystem-first SKILL.md library (per research/briefs/03-router-design.md section 5). Pack = top-level domain folder with a router SKILL.md whose `name` equals the pack folder name; leaves keep their existing standard/activity structure inside the pack (pack/standard/activity/SKILL.md). Routing stays description+tag-driven; domain/pack frontmatter fields are added to every SKILL.md so any router or installer can filter on them. A deterministic offline pack-inventory script exposes the pack tree for per-domain installs.

**Tech Stack:** bash (git mv), YAML frontmatter, python3 stdlib (pack_inventory.py), existing gate suite (spec_lint.py / desc_lint.py / router_eval.py / pytest-contract / no-verbatim).

**Spec:** founder directive 2026-08-31 (verbatim in session task); research/briefs/05-domain-taxonomy.md (12 disciplines); research/briefs/03-router-design.md (router-as-skill pattern, section 5); docs/harness-contract.md (5 gates).

## Global Constraints

- Repo stays PRIVATE. No external sends, no pricing changes.
- Do NOT touch: LICENSE, NOTICE, SECURITY.md, CONTRIBUTING.md, STANDARDS.md, numbers.yaml, the README compliance banner text, AGENTS.md.
- One branch `main`. Every commit complete (code + docs + tests + state together) and gate-green at rest (AGENTS.md).
- Gates non-negotiable at every commit: `make validate` 5/5 (28/28 Hit@1), `make attest` 3/3, `bash ops/automation/test/run-tests.sh` ALL PASS.
- Zero em dashes (—) in README.md.
- git mv only (history preserved); every SKILL.md + scripts/ intact.
- Do not delegate. Owner: Ops Manager (@vedahq_bhishma_bot), one build.
- Post as self to group topic 160, tag @vedahq_draupadi_bot.

## Pack mapping (taxonomy discipline -> pack folder)

| Taxonomy discipline (kebab) | Pack folder | Leaves moved in |
|---|---|---|
| avionics | skills/avionics/ | do178c/{planning,development,verification,configuration-management}, do254/hardware-planning, far-cs25/airworthiness (already in place) |
| space-systems | skills/space-systems/ | ecss/software-engineering (from skills/space/) |
| systems-engineering-safety | skills/systems-engineering-safety/ | arp4754a/systems-planning, arp4761a/safety-assessment, mbse/systems-engineering |
| manufacturing-quality | skills/manufacturing-quality/ | as9100/quality |
| cross-cutting | skills/cross-cutting/ | sep2640/skill-delivery |

Frontmatter mapping (domain: and pack: both = pack folder name; metadata.domain normalized to match; metadata.subdomain unchanged):

| Leaf | domain / pack |
|---|---|
| avionics/do178c/* (4), avionics/do254/hardware-planning, avionics/far-cs25/airworthiness | avionics |
| space-systems/ecss/software-engineering | space-systems |
| systems-engineering-safety/arp4754a/systems-planning, arp4761a/safety-assessment, mbse/systems-engineering | systems-engineering-safety |
| manufacturing-quality/as9100/quality | manufacturing-quality |
| cross-cutting/sep2640/skill-delivery | cross-cutting |

---

### Task 1: Taxonomy move + path fixes

**Files:**
- Move (git mv): skills/space -> skills/space-systems; skills/arp4754a, skills/arp4761a, skills/mbse -> skills/systems-engineering-safety/; skills/as9100 -> skills/manufacturing-quality/; skills/sep2640 -> skills/cross-cutting/
- Modify: eval/hit1-corpus.yaml (expected_skill for sp1 sp2 sa1 sa2 q1 q2 e1 e2 m1 m2 s1 s2 + future_pin t3 + header comment)
- Modify: docs/glossary.md lines 176, 186, 214
- Modify: development/expansion-pipeline-P3.5.md lines 43-48, 104, 125

- [ ] **Step 1:** git mv all five moves.
- [ ] **Step 2:** Update eval/hit1-corpus.yaml expected_skill paths (see Pack mapping). Keep all 28 tasks and both pins per task; only paths change.
- [ ] **Step 3:** Update docs/glossary.md and development/expansion-pipeline-P3.5.md path references.
- [ ] **Step 4:** Run `make validate` — expect 5/5 with 28/28 Hit@1 on NEW paths (routers not yet added).
- [ ] **Step 5:** Commit: `refactor: organize skills into domain packs (taxonomy move)` with Signed-off-by.

### Task 2: Pack router SKILL.md + domain/pack frontmatter

**Files:**
- Create: skills/avionics/SKILL.md, skills/space-systems/SKILL.md, skills/systems-engineering-safety/SKILL.md, skills/manufacturing-quality/SKILL.md, skills/cross-cutting/SKILL.md
- Modify: all 12 leaf SKILL.md (add top-level `domain:` + `pack:`; normalize metadata.domain to the discipline)

**Interfaces:**
- Router frontmatter: name == pack folder name (spec-lint gate 1); description 50-150 words with action verb + "Use when" + "Trigger" with >=2 keywords (desc-lint gate 2); license Apache-2.0; compliance STANDARDS-REF; standards non-empty and resolvable in standards-map.yaml (avionics: do-178c, do-254, far-25, cs-25; space-systems: ecss; systems-engineering-safety: arp4754a, arp4761a; manufacturing-quality: as9100; cross-cutting: sep-2640); gated: false with gated standards reference-only: true; metadata.version + metadata.author; top-level domain + pack = pack name; tags: [] (keeps routers out of the tag-weighted Hit@1 competition).
- Router body: (a) domain description, (b) sub-skill list with relative paths, (c) "route here when" guidance. <500 lines, no verbatim markers, no content-policy red flags.

- [ ] **Step 1:** Write the five router SKILL.md files.
- [ ] **Step 2:** Patch all 12 leaf SKILL.md frontmatters (add domain/pack; normalize metadata.domain).
- [ ] **Step 3:** Run `make validate` — MUST stay 28/28 Hit@1 with the 5 routers now in the candidate pool. If any task regresses, adjust the offending router description (never weaken the gate).
- [ ] **Step 4:** Commit: `feat: add pack routers and domain/pack frontmatter` with Signed-off-by.

### Task 3: Pack inventory tooling (per-domain install)

**Files:**
- Create: scripts/pack_inventory.py
- Create: ops/automation/test/fixture-pack-bad/SKILL.md (missing domain/pack), ops/automation/test/fixture-pack-good/SKILL.md (present)
- Modify: Makefile (add `packs` target), ops/automation/test/run-tests.sh (P1-P4 tests)

**Interfaces:**
- scripts/pack_inventory.py [--pack NAME] [--domain NAME] <skills_dir=skills>
  - Exit 0 + pack tree on stdout; exit 1 when a SKILL.md lacks domain/pack/name (honest, deterministic, stdlib-only).
  - Output: one line per leaf: `<pack>/<rel-path>` and a summary line `packs=N skills=M`.

- [ ] **Step 1 (RED):** Add P1-P4 tests to run-tests.sh:
  - P1: real repo, no args -> exit 0, stdout lists 5 packs and 12 skills.
  - P2: --pack avionics -> exit 0, lists only the 6 avionics leaves.
  - P3: --domain systems-engineering-safety -> exit 0, lists 3 leaves.
  - P4 (negative): fixture-pack-bad (no domain/pack) -> exit 1.
- [ ] **Step 2:** Run run-tests.sh — expect P1-P4 FAIL (script missing).
- [ ] **Step 3 (GREEN):** Implement scripts/pack_inventory.py.
- [ ] **Step 4:** Add `packs` target to Makefile: `packs: ; @python3 scripts/pack_inventory.py`.
- [ ] **Step 5:** Run run-tests.sh — expect ALL PASS (12 checks + P1-P4).
- [ ] **Step 6:** Run `make validate` and `make attest` — still green.
- [ ] **Step 7:** Commit: `feat: add pack inventory for per-domain install` with Signed-off-by.

### Task 4: README per-domain install + harness docs + contract

**Files:**
- Modify: README.md (Install + Harness integration sections per-domain; What's here table paths; Contributing thin-domain callout). Keep compliance banner, badges, standards map, links. Zero em dashes.
- Modify: docs/harness-integration.md (pack-level examples; keep the evidence content)
- Modify: docs/harness-contract.md (pack layout, 17 SKILL.md under gate 1, domain/pack frontmatter, 28 tasks with updated paths)
- Add: docs/superpowers/plans/2026-08-31-domain-pack-restructure.md (this plan, as the design record)

- [ ] **Step 1:** Rewrite README Install + Harness integration to show avionics pack install, space-systems pack install, full library install (flatten leaf folders into host skills dir).
- [ ] **Step 2:** Update What's here table paths + Contributing thin-domain callout.
- [ ] **Step 3:** Update docs/harness-integration.md examples and docs/harness-contract.md prose.
- [ ] **Step 4:** Verify zero em dashes in README (`grep -c "—" README.md` -> 0).
- [ ] **Step 5:** Run all gates fresh: make validate 5/5, make attest 3/3, run-tests.sh ALL PASS.
- [ ] **Step 6:** Commit: `docs: per-domain install docs for domain packs` with Signed-off-by.

### Task 5: Final verification + push

- [ ] **Step 1:** make snapshot-live (fresh evidence for the final commit).
- [ ] **Step 2:** make validate (5/5, 28/28), make attest (3/3), bash ops/automation/test/run-tests.sh (ALL PASS).
- [ ] **Step 3:** git status clean; commit any snapshot evidence; HEAD == origin/main after push.
- [ ] **Step 4:** Final self-review: full diff vs every directive requirement (1-8 + constraints).
- [ ] **Step 5:** Push to origin main; confirm tree clean, HEAD == origin/main.
- [ ] **Step 6:** Post to group topic 160 (3-15 lines) as @vedahq_bhishma_bot, tag @vedahq_draupadi_bot.

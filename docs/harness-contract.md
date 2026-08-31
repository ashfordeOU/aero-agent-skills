# AeroSkills Eval Harness Contract (Phase 0)

Status: contract landed 2026-09-02. Harness REAL on skill 1
(avionics/do178c/planning) — 09-04 milestone landed early 2026-08-31.
P2.1 (2026-08-31): six published skills; gate 3 runs six contract tests,
gate 5 runs thirteen corpus tasks. Owner: Ops Manager, Phase 0 build.
Sources: research/briefs/03-router-design.md (routing, Hit@1), research/briefs/05-domain-taxonomy.md
(skill anatomy, section 6), research/briefs/06-legal-export-control.md (compliance flags, section 8).

## Purpose

A deterministic, offline gate suite that proves a skill is shippable: agentskills.io
conformant, router-usable, legally clean, and behavior-tested. `make validate` must
exit 0 before any skill is committed as shippable.

## Commitments

- 2026-09-02: standards-map.yaml + this contract in repo. DONE.
- 2026-09-04: harness green on skill 1: all 5 gates exit 0. DONE (landed early 2026-08-31).

## Determinism rules

- No network calls. All gates run locally with stdlib or pinned preinstalled tools
  (python3, PyYAML, stdlib unittest).
- Fixed inputs (corpus, grep patterns); stable ordering (sorted finds); exit-code based.
- A gate with nothing to check reports that state and exits 0.
- No gate prints (STUB): stubs were the Phase 0 spine; all five are REAL.

## Gates

| # | Gate | Checks | Pass criteria | Status |
|---|------|--------|---------------|--------|
| 1 | Spec lint (agentskills.io conformance + compliance flags) | frontmatter, naming, description, body limits, compliance flags | every SKILL.md: name <=64 chars kebab-case matching parent dir; description <=1024 chars; compatibility <=500 chars; body <500 lines; references one level deep, relative paths only; license == Apache-2.0; compliance in {none, ITAR-GATED, EAR-GATED, STANDARDS-REF}; standards non-empty, each resolvable in standards-map.yaml; gated bool consistent with standards-map (gated standards must be reference-only or skill gated:true); metadata.version + metadata.author present | REAL |
| 2 | Description lint (what+when+trigger) | description written for the orchestrator (brief 03 section 4) | description contains action/what clause, explicit "Use when ...", 'Trigger' keyword with >=2 trigger keywords; 50-150 words | REAL |
| 3 | Per-skill pytest contract (DAL A-E determination) | skill behavior test per ARP4754A/ARP4761A | skill 1 test: failure-condition severity maps to correct DAL/FDAL/IDAL and DO-178C level; coverage depth A=MC/DC, B=decision, C=statement, D/E=none; all tests pass; stdlib-only imports | REAL |
| 4 | No-verbatim RTCA/SAE/IAQG grep | copyright control (brief 06 section 5.2) | zero verbatim-text markers AND zero objective-table blocks across skills/ and docs/ | REAL |
| 5 | Hit@1 corpus | router selection quality (brief 03 section 5) | 3/3 corpus tasks resolve to expected skill as top-1 (deterministic offline router) | REAL |

## Gate detail

### Gate 1: Spec lint (agentskills.io conformance)

Checks per SKILL.md, per the open agentskills.io specification and brief 03 section 3,
plus the compliance flags of brief 06 section 8.3.5:
- File present at skills/<path>/SKILL.md.
- YAML frontmatter parses.
- `name` required, <=64 chars, lowercase/numbers/hyphens, matches parent directory name.
- `description` required, <=1024 chars.
- `compatibility` <=500 chars when present.
- Body <500 lines (<~5K tokens).
- References one level deep from SKILL.md; relative paths only.
- `license` must equal `Apache-2.0`.
- `compliance` must be one of `none | ITAR-GATED | EAR-GATED | STANDARDS-REF`.
- `standards` non-empty list; every entry (string or `{id, reference-only}`
  mapping) must resolve against standards-map.yaml (by id or name).
- `gated` boolean consistent with the map: a standard whose map entry is
  `gated: true` must be listed `reference-only` in the skill, or the skill
  must be `gated: true`.
- `metadata.version` and `metadata.author` present.

Runner: scripts/gate-spec-lint.sh -> scripts/spec_lint.py per file.

### Gate 2: Description lint (what+when+trigger)

Checks that the description field is written for the orchestrator, not the human
(brief 03 section 4: descriptions are the router; this single field dominates selection
quality). Pass criteria:
- Contains an action/what clause (action verb: determine/draft/scope/run/...).
- Contains a when-to-use clause (explicit "Use when ...").
- Contains 'Trigger' keyword followed by >=2 trigger keywords for the skill's discipline.
- 50-150 words.

Runner: scripts/gate-desc-lint.sh -> scripts/desc_lint.py per file.

### Gate 3: Per-skill pytest contract (DAL A-E determination)

Each skill ships a behavior test that exercises the skill's core logic.
Skill 1 (avionics/do178c/planning) ships a DAL determination test per
ARP4754A/ARP4761A: given a failure-condition severity classification
(Catastrophic/Hazardous/Major/Minor/No safety effect), the test asserts the
correct DAL, FDAL/IDAL, and DO-178C software level, including coverage-depth
implications (A=MC/DC, B=decision, C=statement, D=none, E=none). Tested
logic lives in scripts/do178c_levels.py (importable module); the test is
scripts/test_do178c_levels.py. Every subsequent skill ships its own
behavior contract as skills/<path>/scripts/test_*.py alongside a sibling
logic module (stdlib unittest, offline). P2.1 ships five: development
(traceability closure per DAL), verification (coverage depth + independence),
configuration-management (baselines/change control/release gate),
systems-planning (FDAL/IDAL + planning artifacts), hardware-planning
(DO-254 AEH simple/complex classification). All are discovered and run the
same way.

Runner: scripts/gate-pytest-contract.sh.

### Gate 4: No-verbatim RTCA/SAE/IAQG grep (copyright control)

Scans published content (skills/ and docs/) for verbatim-text markers from
proprietary standards: RTCA/SAE/IAQG copyright boilerplate, DRM/license-restriction
lines, watermark fragments from pirated copies, and objective-table blocks
(DO-178C/DO-254 style 'Table A-1' / 'A-1.1' runs). Zero matches required. The rule
it enforces (brief 06 section 5.2): name + paraphrase + short attributed quotes
(<100 words) + links only; never reproduce objective tables, appendix text, or
multi-line verbatim blocks. Public-domain standards (FAR-25) and attribution-licensed
text (CS-25, ECSS) are quotable with citation and must not trip the gate.

Runner: scripts/gate-no-verbatim.sh (markers) + scripts/verbatim_table_scan.py (blocks).

### Gate 5: Hit@1 corpus

Fixed corpus of active tasks (eval/hit1-corpus.yaml), resolved by the
flat+tags router (brief 03 section 5 layer 2 stage 1: token overlap over
tags/name/description/body with tag boost; deterministic, offline). Pass =
top-1 == expected_skill for all tasks (13 as of P2.1).

Phase 0 pinned the active tasks to skill 1 (avionics/do178c/planning).
P2.1 promotes tasks for every published skill: the corpus now carries
thirteen active tasks across the six skills (three DO-178C planning, two
development, two verification, two configuration-management, two ARP4754A
systems-planning, two DO-254 hardware-planning). The brief-03 canonical
queries (CubeSat battery, weight-and-balance, engine overhaul) are
preserved as future_pins and promoted into tasks as those skills publish.

Runner: scripts/gate-hit1-corpus.sh -> scripts/router_eval.py.

## Wiring

Makefile target `validate` runs all five REAL gates and must exit 0:

    make validate

Wired and REAL: gate 1 (spec lint), gate 2 (description lint), gate 3 (pytest
contract), gate 4 (no-verbatim), gate 5 (Hit@1 corpus).

## Definition of done

`make validate` exits 0 on a clean checkout with no network access, on skill 1
(avionics/do178c/planning) and every subsequent skill.

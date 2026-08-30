# AeroSkills Eval Harness Contract (Phase 0)

Status: contract landed 2026-09-02. Harness REAL on skill 1 (avionics/do178c/planning) by 2026-09-04.
Owner: Ops Manager, Phase 0 build.
Sources: research/briefs/03-router-design.md (routing, Hit@1), research/briefs/05-domain-taxonomy.md
(skill anatomy, section 6), research/briefs/06-legal-export-control.md (compliance flags, section 8).

## Purpose

A deterministic, offline gate suite that proves a skill is shippable: agentskills.io
conformant, router-usable, legally clean, and behavior-tested. `make validate` must
exit 0 before any skill is committed as shippable.

## Commitments

- 2026-09-02: standards-map.yaml + this contract in repo. DONE.
- 2026-09-04: harness green on skill 1: all 5 gates exit 0.

## Determinism rules

- No network calls. All gates run locally with stdlib or pinned tools.
- Fixed inputs (corpus, grep patterns); stable ordering; exit-code based.
- A gate with nothing to check reports its own stub state and exits 0.
- Stubs print (STUB) in their output line. Stubs are not the deliverable;
  they are the spine. Real implementations land 2026-09-04.

## Gates

| # | Gate | Checks | Pass criteria | Status |
|---|------|--------|---------------|--------|
| 1 | Spec lint (agentskills.io conformance) | frontmatter, naming, description, body limits | every SKILL.md: name <=64 chars kebab-case matching parent dir; description <=1024 chars what+when+trigger; body <500 lines; references one level deep | STUB today: frontmatter parse + required keys; full conformance 09-04 |
| 2 | Description lint (what+when+trigger) | description written for the orchestrator (brief 03 section 4) | description contains action/what, when-to-use, trigger keywords; 50-150 words | pending wiring 09-04 |
| 3 | Per-skill pytest contract (DAL A-E determination) | skill behavior test per ARP4754A/ARP4761A | skill 1 test: failure-condition severity maps to correct DAL/FDAL/IDAL and DO-178C level; all skill tests pass | pending wiring 09-04 |
| 4 | No-verbatim RTCA/SAE/IAQG grep | copyright control (brief 06 section 5.2) | zero matches for verbatim-text markers across skills/ and published docs | STUB today: marker grep over skills/ |
| 5 | Hit@1 corpus | router selection quality (brief 03 section 5) | 3/3 corpus tasks resolve to expected skill as top-1 | STUB today: corpus presence; real eval 09-04 |

## Gate detail

### Gate 1: Spec lint (agentskills.io conformance)

Checks per SKILL.md, per the open agentskills.io specification and brief 03 section 3:
- File present at skills/<path>/SKILL.md.
- YAML frontmatter parses.
- `name` required, <=64 chars, lowercase/numbers/hyphens, matches parent directory name.
- `description` required, <=1024 chars, what + when, keyword-rich.
- Body <500 lines (<~5K tokens).
- References one level deep from SKILL.md; relative paths only.

Runner: scripts/gate-spec-lint.sh. Full conformance (name-match, length caps, body limits,
ref depth) lands 09-04. Today the stub verifies frontmatter parses and carries name +
description.

### Gate 2: Description lint (what+when+trigger)

Checks that the description field is written for the orchestrator, not the human
(brief 03 section 4: descriptions are the router; this single field dominates selection
quality). Pass criteria:
- Contains an action/what clause.
- Contains a when-to-use clause (explicit "Use when ..." or equivalent).
- Contains domain trigger keywords for the skill's discipline.
- 50-150 words.

Runner: scripts/gate-desc-lint.sh (wired 09-04).

### Gate 3: Per-skill pytest contract (DAL A-E determination)

Each skill ships a behavior test that exercises the skill's core logic. Skill 1
(avionics/do178c/planning) ships a DAL determination test per ARP4754A/ARP4761A:
given a failure-condition severity classification (Catastrophic/Hazardous/Major/
Minor/No safety effect), the test asserts the correct DAL, FDAL/IDAL, and DO-178C
software level, including coverage-depth implications (A=MC/DC, B=decision,
C=statement, D=none, E=no safety effect). Tests run with stdlib unittest so the
harness stays dependency-free and network-free.

Runner: scripts/gate-pytest-contract.sh (wired 09-04).

### Gate 4: No-verbatim RTCA/SAE/IAQG grep (copyright control)

Scans published content for verbatim-text markers from proprietary standards:
RTCA/SAE/IAQG copyright boilerplate, DRM/single-user license lines, watermark
fragments from pirated copies. Zero matches required. The rule it enforces
(brief 06 section 5.2): name + paraphrase + short attributed quotes (<100 words) +
links only; never reproduce objective tables, appendix text, or multi-line verbatim
blocks. Public-domain standards (FAR-25) and attribution-licensed text (CS-25, ECSS)
are quotable with citation and must not trip the gate.

Runner: scripts/gate-no-verbatim.sh. Extended scan (all published docs, additional
markers, multi-line block detection) lands 09-04.

### Gate 5: Hit@1 corpus

Fixed corpus of 3 realistic aerospace tasks (eval/hit1-corpus.yaml), from brief 03
section 5:
1. Size a battery for a 12U CubeSat.
2. Draft a preflight weight-and-balance sheet.
3. Plan an engine-overhaul checklist.

Pass = the router/host returns the expected skill as top-1 for all 3 queries.
Expected skills are placeholders pinned when seed skills publish. Today the stub
verifies the corpus file exists and contains the 3 seed tasks. Real retrieval eval
lands 09-04.

## Wiring

Makefile target `validate` runs the wired gates and must exit 0:

    make validate

Wired today: gate 1 (spec lint), gate 4 (no-verbatim), gate 5 (Hit@1 corpus) as
stubs. Gates 2 and 3 are defined by this contract and wired when real by 09-04.

## Definition of done

`make validate` exits 0 on a clean checkout with no network access, on skill 1
(avionics/do178c/planning) and every subsequent skill.

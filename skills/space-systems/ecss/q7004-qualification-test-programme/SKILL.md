---
name: q7004-qualification-test-programme
description: "Plan the qualification variant of an ECSS thermal test as a ladder of test article levels rather than a single run. Use when the ECSS-Q-ST-70-04C method variants have to become a qualification programme: build the ladder from coupon through subassembly to equipment, take each level's cycle count as the larger of its own floor and a whole multiple of the acceptance programme and report which governed, allow a waiver only where the policy permits one and only against a named heritage reference, size the articles and chamber loads, then sum the levels into one duration. Trigger: ecss, q-st-70-04-thermal-testing-scope, qualification-test-article-levels, qualification-cycle-count-derivation, qualification-level-waiver, qualification-article-sizing, qualification-programme-duration."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-qualification-test-programme, qualification-test-article-levels, qualification-cycle-count-derivation, qualification-level-waiver, qualification-article-sizing, qualification-programme-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Qualification Test Programme (space-systems/ecss/q7004-qualification-test-programme)

Use when the task is the qualification variant of ECSS-Q-ST-70-04C — which
levels of test article are run, how many cycles each of them takes, how many
articles that costs, and what the whole ladder adds up to in chamber time.

## Domain quick reference

- Qualification is a ladder, not a run. Coupons answer the material
  question, subassemblies answer the joint and interface question, and
  equipment answers the only question that ships: whether the flight
  configuration survives.
- A missing rung is invisible in the summary. A programme with no
  equipment-level article reads as qualified and has demonstrated nothing
  about the assembly that flies.
- Two numbers compete for each level's cycle count: the level's own floor
  and a whole multiple of the acceptance programme. The qualification count
  is the larger, and which one governed has to travel with the number.
- A level governed by the acceptance multiple is not settled. It moves every
  time the acceptance programme moves, so it needs re-deriving rather than
  transcribing into the next revision.
- A waiver is a substitution of evidence, not a deletion. It is permitted
  only at levels the policy allows and only against a named heritage
  reference; without the reference it is just a skipped rung.
- Article counts and chamber capacity are independent. Articles beyond one
  load become sequential runs at that level, and only the run count
  multiplies the duration.

## Workflow

1. Build the ladder from the coupon up to the highest article level being
   qualified. Do not start halfway up because the lower levels look routine.
2. Resolve the waivers against the ladder, refusing a waiver at a level the
   policy protects and refusing one with no reference behind it.
3. For each surviving level, derive the cycle count from the level floor and
   the acceptance multiple, keeping the governing source.
4. Take the article count from the policy unless one is declared, compare a
   declared count against the policy count, and split the articles into
   chamber loads by integer ceiling division.
5. Multiply cycles by cycle duration by runs per level and sum the levels.
6. Raise the findings — governed-by-acceptance levels, thin article counts,
   waived rungs, a missing equipment level — and carry the standing duties.

## Pitfalls

- Reporting a single cycle count for the programme. Each level has its own
  and they are derived differently; one number hides which level is actually
  carrying the qualification.
- Transcribing a cycle count governed by the acceptance multiple into the
  next revision. Acceptance moved, the qualification did not, and the margin
  the factor was there to provide quietly disappeared.
- Accepting a waiver with a heritage claim but no reference. The claim
  cannot be checked later, and the rung is gone either way.
- Multiplying the duration by article count. The chamber runs a load, and a
  level with four articles in one load costs the same time as one article.
- Rounding the run count in floating point. It is an integer question, and a
  float ceiling that lands just under an integer leaves an article untested.
- Returning qualification articles to the flight build. They have spent
  their life in the chamber, and the programme is the reason they cannot
  fly.

## Behavior contract (gate 3)

The ladder construction, waiver resolution with its protected levels and
reference requirement, the cycle count contest between the level floor and
the acceptance multiple, article sizing, integer run counts, per-level and
total durations and the standing duties are exercised by the gate 3 contract
test: scripts/test_q7004_qualification_test_programme.py against
scripts/q7004_qualification_test_programme_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q7004_qualification_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

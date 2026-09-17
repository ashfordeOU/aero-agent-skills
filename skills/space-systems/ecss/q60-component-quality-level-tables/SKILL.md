---
name: q60-component-quality-level-tables
description: "Determine the quality level a component family must reach, and the testing it carries, under ECSS-Q-ST-60C clause 7. Use when a project reliability class is fixed and a proposed part has to be judged against tables 7-1 to 7-3: map the family and the class onto the required level, build the coverage from a cumulative level baseline plus the tests the family carries for its own failure modes, keep the family tests that answer a failure mode the part has however it is bought, compare stringency ordinals rather than level digits, and return a verdict with the tests an uprating would add. Trigger: ecss, q-st-60c-clause-7-quality-levels, component-family-quality-level-table, reliability-class-to-quality-level, quality-level-test-coverage-set, component-uprating-additional-testing, proposed-part-level-shortfall."
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
  tags: [ecss, q-st-60c-eee-component-scope, q60-component-quality-level-tables, q-st-60c-clause-7-quality-levels, component-family-quality-level-table, reliability-class-to-quality-level, quality-level-test-coverage-set, component-uprating-additional-testing, proposed-part-level-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Component Quality Level Tables (space-systems/ecss/q60-component-quality-level-tables)

Use when the task is the quality level provisions of ECSS-Q-ST-60C clause 7,
tables 7-1 to 7-3 — taking a component family and the reliability class the
project was put in, and turning them into the level a part has to reach and
the testing that level brings with it.

## Domain quick reference

- The three tables are one lookup with two indices. Family alone does not
  determine a level and class alone does not either; a family that demands
  the top level in the most stringent class can be ordinary in the least.
- Stringency runs the opposite way to the level number. Level 1 is the
  demanding one, so every comparison is made on an ordinal and never on the
  digit in the name — reading the digit inverts the answer silently.
- Coverage is cumulative. A level carries everything the levels below it
  carry and adds its own, so the sets are built by inheritance rather than
  written out three times and left to drift apart.
- Families bring their own tests. Burn-in belongs to active devices, surge
  current to solid tantalum, contact endurance to relays; the level says how
  much confidence is wanted and the family says where the part fails.
- A few family tests do not drop away with the level. A tantalum part has its
  surge failure mode and a fuse has its interruption duty however either is
  bought, so those stay required at the least demanding level too.
- An uprating is a top-up, not a rebuild. One stringency step can be closed
  by adding the missing tests; two steps means the part was never a candidate
  and the shortfall is structural.
- A part can sit at the right level and still be short. The level is one test
  and the coverage is another, so a level match with a missing test is
  reported as a shortfall rather than waved through.

## Workflow

1. Validate the inputs: part number, component family, project reliability
   class, the quality level proposed and the tests already performed.
2. Look the family and the class up in the tables to get the quality level
   required.
3. Build the required coverage: the cumulative baseline for that level, plus
   the family's own tests, keeping only the level-independent ones where the
   required level is the least demanding.
4. Compare the proposed level's stringency ordinal against the required one
   and count the uprating steps between them.
5. Compute the missing tests and the coverage fraction the proposal already
   holds against the required set.
6. Return the verdict — the level is met, an uprating can close it, or the
   part is not acceptable — with every finding behind it.

## Pitfalls

- Comparing level numbers. Level 3 is not better than level 1, and an
  ordering taken from the digit accepts exactly the parts it should stop.
- Reading one table. The level is only meaningful next to the class the
  project is in, and quoting a family's level with no class attached is an
  answer to a question nobody asked.
- Writing the coverage sets out per level. Three hand-maintained lists drift,
  and the drift shows up as a test quietly required at level 2 but not at
  level 1.
- Dropping every family test at the lowest level. Surge current and
  interruption duty answer the part's own failure mode, not the buyer's
  confidence, and dropping them buys nothing.
- Treating any shortfall as an uprating. Two stringency steps is a different
  part, and calling that an uprating puts a commercial part into a class it
  was never built for.
- Stopping at the level match. A part at the right level with a missing test
  is still short, and only the coverage comparison finds it.

## Behavior contract (gate 3)

The family and class validation, the two-index table lookup, the stringency
ordinal, the cumulative level baseline, the family and level-independent test
sets, the required coverage build, the coverage fraction and missing test
list, the uprating step count judged at the coverage floor under a named
tolerance and the verdict are exercised by the gate 3 contract test:
scripts/test_q60_component_quality_level_tables.py against
scripts/q60_component_quality_level_tables_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_component_quality_level_tables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

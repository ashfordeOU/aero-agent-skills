---
name: e1003-eq-acceptance
description: "Use when defining the acceptance test baseline for a piece of equipment under ECSS-E-ST-10-03C: derive per-test-type acceptance levels and durations from the equipment's qualification baseline and its margin/duration reduction rules, guard against an acceptance level or duration that fails to sit below its qualification counterpart, and check the baseline for coverage gaps before it is released to the test programme. Anchor: E-ST-10-03C clause 5.3 + Tables 5-3/5-4. Trigger: equipment acceptance test, acceptance test baseline, acceptance level, acceptance duration, Table 5-3, Table 5-4, e-st-10-03, ecss testing."
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
  tags: [ecss, e-st-10-03c, equipment-testing, acceptance-test, test-levels, test-durations]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Acceptance Test Baseline (space-systems/ecss/e1003-eq-acceptance)

Use when the task is defining the acceptance test baseline (levels and
durations, per test type) for a piece of equipment under
ECSS-E-ST-10-03C, ahead of general equipment test execution (sibling
e1003-eq-general-tests, e1003-eq-mechanical, e1003-eq-thermal, etc.
leaves) and test documentation release (sibling e1003-test-docs leaf).

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.3 and Tables 5-3/5-4 define the acceptance
  test baseline for equipment: for each applicable test type, an
  acceptance level and an acceptance duration (or cycle count),
  derived from -- and always sitting below -- the same test type's
  qualification level and duration (sibling e1003-eq-qual leaf,
  clause 5.2 + Tables 5-1/5-2).
- An acceptance test is run at the equipment's flight-limit level
  without the extra margin used in qualification to demonstrate design
  robustness, and for a shorter duration or fewer cycles, because its
  purpose is to precipitate workmanship defects and confirm
  performance -- not to re-prove margin already shown on the
  qualification model.
- This baseline only applies to equipment following the acceptance
  test path (as opposed to protoflight); equipment on the protoflight
  path is covered instead by the protoflight test baseline (sibling
  e1003-eq-protoflight leaf, clause 5.4 + Tables 5-5/5-6), which
  substitutes for a separate acceptance campaign.
- The baseline must cover every mandatory test type applicable to the
  equipment (per the general and category-specific test requirements
  in clauses 5.5.1-5.5.6); a released baseline missing a required test
  type is incomplete.

## Workflow

1. Confirm the equipment's test path: this leaf applies only when the
   equipment follows the acceptance path. If the equipment follows the
   protoflight path, stop here and hand off to e1003-eq-protoflight
   instead of producing a separate acceptance baseline.
2. For each applicable test type, capture the equipment's already-set
   qualification level and duration (from e1003-eq-qual) together with
   the test type's margin-reduction factor (how much the qualification
   level exceeds the acceptance level) and duration-reduction factor
   (how much shorter the acceptance duration/cycle count is than
   qualification).
3. Derive the acceptance level and duration for each test type from
   its qualification value and reduction factors, and validate the
   result: the acceptance level must sit strictly below the
   qualification level, and the acceptance duration must not exceed
   the qualification duration. Flag any test type whose derived values
   fail this check instead of accepting them silently -- it signals a
   miscalibrated reduction factor, not a valid baseline entry.
4. Assemble the baseline as one entry per test type and confirm every
   test type required for the equipment's applicability set (general,
   mechanical, pressure, thermal, electrical, mission-specific, as
   applicable) is present -- an incomplete baseline cannot be released.
5. Release the baseline for the test programme only when every
   required test type has a valid, flag-free entry; otherwise list the
   missing test types and the flagged entries as the open items
   blocking release.

## Pitfalls

- Deriving an acceptance level or duration that equals or exceeds its
  qualification counterpart -- that inverts the qualification/
  acceptance margin relationship and must be flagged, not treated as a
  conservative choice.
- Building an acceptance baseline for equipment that is actually on
  the protoflight path, instead of deferring to the protoflight test
  baseline that already covers it.
- Releasing a baseline that silently omits a required test type
  because it was never entered, rather than treating the gap as a
  release blocker.
- Copying the qualification test's level and duration verbatim into
  the acceptance entry "to be safe" -- that discards the margin/
  duration relationship the acceptance test depends on.

## Behavior contract (gate 3)

The test-path gate, level/duration derivation, consistency-guard, and
baseline-completeness logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_acceptance.py against
scripts/e1003_eq_acceptance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

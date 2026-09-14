---
name: e2008-external-diode-acceptance-tests
description: "Verify that an acceptance programme for external protection diodes is drawn from the tabulated test list of clause 9.4.3 of ECSS-E-ST-20-08C. Resolve the table against the configuration declared for the build, confirm every mandatory row is present, admit an optional row only where it is declared, refuse a test the table does not hold, reject a duplicate entry, grade the running order against the tabulated order, and return the programme with gaps, untabulated extras and ordering breaks ranked. Use when an external diode acceptance programme, test matrix or sequence sheet has to be built or reviewed. Trigger: ecss, e-st-20-08c, external-diode-acceptance-tests, external-protection-diode-test-table, external-diode-mandatory-test-coverage, external-diode-conditional-test-resolution, external-diode-test-sequence-order, external-diode-acceptance-programme-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-external-diode-acceptance-tests, external-diode-acceptance-tests, external-protection-diode-test-table, external-diode-mandatory-test-coverage, external-diode-conditional-test-resolution, external-diode-test-sequence-order, external-diode-acceptance-programme-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS External Protection Diodes — Acceptance Tests (space-systems/ecss/e2008-external-diode-acceptance-tests)

Use when the task is clause 9.4.3 of ECSS-E-ST-20-08C: the acceptance programme
for external protection diodes is drawn from a tabulated list of tests. This
leaf resolves that table against the build configuration and grades a proposed
programme on coverage, admissibility and running order.

## Domain quick reference

- The table is the authority on what the programme may contain, in both
  directions. A row left out is a gap; a test that is not a row at all is not a
  stricter programme, it is an unagreed one, and it consumes parts and schedule
  nobody costed.
- Rows are not uniform in standing. A mandatory row is owed by every external
  diode programme. A conditional row is owed only where the build configuration
  raises it. An optional row is owed by nobody and is admitted only where the
  project has declared it.
- Conditional rows are where programmes quietly go wrong. Resolving them
  against an assumption instead of against the declared configuration either
  drops work the build needs or adds work it does not, and both read as a clean
  matrix afterwards.
- A conditional row whose condition token is not declared for the build is not
  a gap. Reporting it as one trains reviewers to wave findings through.
- A configuration token the table never references is a sign the configuration
  sheet and the table are out of step; it is reported rather than ignored,
  because the usual cause is a renamed condition.
- The tabulated order matters as much as the content. Electrical characterisation
  placed after the environmental exposure it was supposed to bracket cannot show
  what changed, so the order is graded as its own result.
- Ordering is graded on relative position, not on absolute slot numbers, and
  only over entries the table holds. A programme that inserts a project-specific
  step between two rows is still in tabulated order, and an untabulated entry
  has no tabulated position to be judged against -- the coverage grade owns it.
- A duplicate entry is a defect, not redundancy. Two rows with the same test
  make the coverage arithmetic lie and leave the running order ambiguous.
- Coverage is a quotient of two test counts, so a programme that covers exactly
  the declared fraction of the required set can evaluate a unit in the last
  place below it; the comparison absorbs that while the minimum stays as
  declared.

## Workflow

1. Validate the configuration: a non-empty build identifier and condition
   tokens the table actually references. Report an unreferenced token instead
   of silently dropping it.
2. Resolve the required set from the table: every mandatory row, plus each
   conditional row whose condition is declared for this build.
3. Validate the proposed programme: each entry names a tabulated test and an
   integer position, and no test appears twice.
4. Compute coverage: which required rows are present, which are missing, and
   the covered share against the declared minimum.
5. Separate the admissible extras from the inadmissible ones -- a declared
   optional row is admissible, a test absent from the table is not.
6. Grade the running order: project the programme onto the tabulated order and
   report every pair whose relative position is inverted.
7. Return the programme verdict with missing rows first, then untabulated
   entries, then duplicates, then ordering breaks.

## Pitfalls

- Treating the table as a floor and adding tests freely. An untabulated test is
  unagreed scope that burns parts and schedule.
- Resolving conditional rows against an assumed configuration. The build sheet
  is the input; assuming it is what drops the row that mattered.
- Reporting an unraised conditional row as a gap. It was never owed, and the
  false finding buries the real one.
- Admitting an optional row because it looks prudent. Optional means the project
  declares it or it stays out of the programme.
- Grading the running order by absolute slot number. A project step inserted
  between two tabulated rows is not an ordering break.
- Letting a duplicate entry stand. It inflates coverage and leaves the order
  ambiguous at the point the duplicate sits.
- Judging a covered share that lands exactly on its declared minimum by bare
  arithmetic, when the share is a quotient of two test counts.

## Behavior contract (gate 3)

The table lookup, the configuration validation, the mandatory and conditional
resolution, the optional admissibility rule, the duplicate refusal, the
untabulated refusal, the covered share against the declared minimum, the
relative ordering grade and the rolled-up programme verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_external_diode_acceptance_tests.py against
scripts/e2008_external_diode_acceptance_tests_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_external_diode_acceptance_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

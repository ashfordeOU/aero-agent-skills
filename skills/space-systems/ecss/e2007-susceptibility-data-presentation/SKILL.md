---
name: e2007-susceptibility-data-presentation
description: "Audit an EMC susceptibility report against its agreed pass criteria. Use when susceptibility results are written up under ECSS-E-ST-20-07C clause 5.2.10.4: confirm every presented result restates the criterion it was graded against, confirm each criterion carries a customer agreement reference, evaluate each observed value against its own limit and direction, raise a result citing no criterion and a criterion no result covers, and require the report fields a reader needs to reproduce the verdict, then group the graded results by the function each criterion governs. Trigger: ecss, e-st-20-07c, susceptibility-data-presentation, agreed-pass-criteria-restatement, susceptibility-result-coverage, criterion-agreement-reference, emc-test-report-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-susceptibility-data-presentation, susceptibility-data-presentation, agreed-pass-criteria-restatement, susceptibility-result-coverage, criterion-agreement-reference, emc-test-report-completeness, susceptibility-verdict-reproducibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Susceptibility — Data Presentation (space-systems/ecss/e2007-susceptibility-data-presentation)

Use when the task is the presentation half of ECSS-E-ST-20-07C clause
5.2.10.4 -- writing up susceptibility results so that the pass criteria
agreed beforehand are restated beside them, every agreed criterion is
answered by a result, and every presented result names the criterion it
was graded against.

## Domain quick reference

- The clause is about what the reader can reconstruct. A susceptibility
  result with no criterion beside it is an observation, not a verdict:
  the reader cannot tell whether four revolutions per minute of speed
  error was acceptable without the number that was agreed.
- A criterion counts only if it was agreed, and the agreement has a
  reference. A limit written into the report during the write-up, with
  no record of who agreed it and when, is a limit invented after the
  measurement it grades.
- Criterion identifiers have to be unique. Two criteria under one
  identifier make every result citing it ambiguous, and the ambiguity is
  invisible in the finished report.
- The comparison runs in a direction. A speed error is a ceiling, a link
  margin is a floor, and grading a floor as though it were a ceiling
  inverts the verdict while the arithmetic still looks right.
- Coverage runs both ways. A result citing a criterion nobody agreed is
  an orphan; an agreed criterion that no result answers is a gap in the
  campaign. Both are findings, and only checking one direction leaves
  the other standing.
- A result that passes by a hair is still a pass, but a reader needs to
  see it. Carrying a proximity band turns a passing result near its
  limit into a stated limitation rather than a silent one.
- The fields that make a verdict reproducible travel with it: the
  frequency, the injected level, the modulation, the observed value, and
  the criterion identifier. Dropping the modulation alone makes two
  results at the same frequency incomparable.

## Workflow

1. Build the agreed-criteria register: each criterion agreed, carrying
   an agreement reference, a named function and parameter, a numeric
   limit with its unit and a recognized direction, under a unique
   identifier.
2. Validate each presented result: all the reproducibility fields
   present, positive frequency, recognized modulation, a numeric
   observed value and a cited criterion identifier.
3. Check coverage in both directions: results citing an identifier that
   is not in the register, and register entries that no result answers.
4. Grade each result against its own criterion in its own direction,
   computing a signed margin. Absorb representation error at the limit
   with a named tolerance so a result exactly on its limit passes; never
   relax the agreed limit itself.
5. Mark a passing result inside the proximity band as close to its
   criterion, and carry it as a limitation.
6. Restate each criterion as one line beside its result, so the report
   carries the requirement and the measurement together.
7. Aggregate: pass and fail counts, results grouped by the function
   their criterion governs, findings (failures, orphans, uncovered
   criteria) and limitations. The package is complete only when there
   are no findings.

## Pitfalls

- Presenting results and criteria in separate sections and leaving the
  reader to match them. The clause asks for them together.
- Restating a limit that was never agreed, or agreed with no traceable
  reference. The restatement then carries no more authority than the
  result.
- Checking only that every result has a criterion. The agreed criterion
  that no result answers is the gap that reaches the review unnoticed.
- Grading a floor criterion with a ceiling comparison. The margin sign
  flips and a failing link margin reads as a comfortable pass.
- Reporting a pass that sits a thousandth inside its limit with no
  remark. It is a pass, but the reader is entitled to know how close.
- Dropping the modulation or the injected level from the presented
  result. The verdict is then not reproducible from the report alone.

## Behavior contract (gate 3)

The criteria-register construction, result-field validation, two-way
coverage check, direction-aware evaluation, proximity banding,
restatement and aggregation logic is exercised by the gate 3 contract
test: scripts/test_e2007_susceptibility_data_presentation.py against
scripts/e2007_susceptibility_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_susceptibility_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q60-class-1-destructive-physical-analysis
description: "Evaluate a delivered Class 1 EEE lot by destructive physical analysis under ECSS-Q-ST-60C clause 4.3.9. Use when partitioning a shipment into date-code groups, sizing the teardown sample each group owes, grading observed construction anomalies as major or minor from a project defect register, and testing wire bond pull forces against the minimum the wire diameter carries before turning the record into a lot disposition. Refuses an unregistered defect code, an unlisted wire diameter, a repeated serial, and a date-code group too small to give up its sample without eating the flight units. Trigger: ecss, q-st-60c, class-1-destructive-physical-analysis, date-code-group-teardown-sample, construction-anomaly-grading, wire-bond-pull-strength-minimum, class-1-lot-teardown-disposition, teardown-second-sample-rule."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-destructive-physical-analysis, date-code-group-teardown-sample, construction-anomaly-grading, wire-bond-pull-strength-minimum, class-1-lot-teardown-disposition, teardown-second-sample-rule]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Destructive Physical Analysis (space-systems/ecss/q60-class-1-destructive-physical-analysis)

Use when the task is the destructive physical analysis of ECSS-Q-ST-60C
clause 4.3.9 — tearing down a sample of a delivered Class 1 lot to
confirm that what is inside the package matches the construction the
part was procured on, before the rest of the lot reaches a build.

## Domain quick reference

- A shipment that spans several date codes is several populations, not
  one lot. Each date-code group owes its **own** teardown sample,
  because a build and a bond process drift between date codes and a
  single sample only evidences the group it was drawn from.
- Teardown units are destroyed. The sample has to come out of the
  **spare** units, so a group that cannot give its sample up and still
  meet the build demand is refused rather than quietly under-sampled.
- Sample size is a fraction of the group, floored at a minimum and
  capped. The cap exists because a wider teardown of a large group buys
  very little more: the anomalies that matter are systemic to the
  assembly line, not rare and random.
- An anomaly is graded against a **project register**, not on the
  analyst's judgement at the bench. A code the register never listed is
  refused, because an ungraded anomaly cannot be counted as major or
  minor and so cannot be disposed of either way.
- Bond pull minima come from the **wire diameter**. A diameter the
  register does not list is refused, never interpolated between two
  neighbours — an interpolated minimum is an invented acceptance
  criterion.
- A major anomaly and a failed bond pull both end the lot. Minor
  anomalies have an allowance, and exceeding it may buy a second sample
  where the project permits one — but only once, and never in place of a
  major finding.

## Workflow

1. Partition the delivered units into date-code groups, refusing a
   repeated serial or a missing date code.
2. Size the teardown sample each group owes, and check it against the
   spare units left after the build demand.
3. Grade every teardown observation from the project defect register,
   refusing an unregistered code or an observation citing a date code
   the shipment does not hold.
4. Read the minimum bond pull force off the wire diameter and evaluate
   every measured pull against it, reporting the weakest and the mean.
5. Dispose of the lot: a major anomaly or a bond under its minimum
   rejects it outright, before any minor count is weighed.
6. Where only minor anomalies exceed the allowance, offer a second
   sample if the project permits one and this is the first sample;
   otherwise reject.
7. Report the sampling plan alongside the verdict, so the record shows
   how much of each date code was actually examined.

## Pitfalls

- Drawing one sample from a mixed shipment. It evidences one date code
  and silently passes the others.
- Sizing the sample against the whole group when part of it is already
  committed to the build. The teardown then consumes flight units, and
  the shortfall surfaces at kitting rather than at incoming.
- Grading an anomaly at the bench because it is not in the register. A
  register gap is a refusal and a register update, not a field call.
- Interpolating a bond minimum for an unlisted wire diameter. The
  register is the acceptance criterion; between two entries there is no
  criterion at all.
- Weighing the minor count before the major one. A lot with a major
  anomaly is finished, and reading the minors first invites the second
  sample to be argued for.
- Offering a second sample after a second sample. The allowance exists
  to absorb cosmetic variation once, not to be re-drawn until a clean
  sample appears.

## Behavior contract (gate 3)

The date-code partition, sample sizing against spare units, defect
grading from the register, bond pull evaluation against the diameter
minimum and the lot disposition are exercised by the gate 3 contract
test: scripts/test_q60_class_1_destructive_physical_analysis.py against
scripts/q60_class_1_destructive_physical_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

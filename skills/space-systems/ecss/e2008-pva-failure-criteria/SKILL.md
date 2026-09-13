---
name: e2008-pva-failure-criteria
description: "Determine which conditions observed during subgroup testing of a photovoltaic assembly count as a failure under ECSS-E-ST-20-08C clause 5.6.1. Use when a subgroup test record has to become a verdict rather than a list of observations: validate every observation, separate the conditions that are a failure on occurrence alone from those governed by a declared limit, compare each measured value against its limit in the direction of merit that condition carries, check that every declared sample carries a record for every required condition, and name the samples that failed. Trigger: ecss, e-st-20-08c, clause-5-6-1, photovoltaic-assembly-failure-criteria, subgroup-test-failure-condition, solar-array-coupon-continuity-loss, pva-power-degradation-limit, subgroup-sample-record-coverage, failure-on-occurrence-condition."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-failure-criteria, e-st-20-08c, clause-5-6-1, photovoltaic-assembly-failure-criteria, subgroup-test-failure-condition, solar-array-coupon-continuity-loss, pva-power-degradation-limit, subgroup-sample-record-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Subgroup Failure Criteria (space-systems/ecss/e2008-pva-failure-criteria)

Use when the task is the clause 5.6.1 question of ECSS-E-ST-20-08C: a
photovoltaic assembly has been through a test subgroup, observations have
come back, and the record has to be read against the conditions that
constitute a failure of the assembly.

## Domain quick reference

- The conditions split into two families and they are not read the same
  way. One family is a failure the moment it occurs — a lost conduction
  path, an unintended one, a component that came away, a coverglass that
  did not stay on. There is no limit that makes any of these acceptable,
  so a limit supplied against one of them is an input defect.
- The other family only becomes a failure once a declared limit is
  crossed, and each such condition carries its own direction of merit. A
  degradation, a cracked-area fraction, a discontinuity count and a
  defect count are acceptable while they stay at or under their limit; a
  power-retention ratio and an insulation resistance are acceptable only
  while they reach theirs. Reading one in the other's direction inverts
  the verdict silently.
- A limit that was never declared is not a zero limit. An undeclared
  limit means the acceptance basis for that condition does not exist yet,
  which is a question for the test specification, not something the
  evaluation can default its way past.
- The verdict belongs to the subgroup, not to a single reading. Every
  sample the subgroup declared has to carry a record for every condition
  the subgroup was supposed to read, and a reading that arrives from a
  sample the subgroup never contained means the sample list and the
  record disagree.
- An incomplete record is not a pass and it is not a failure either. It
  is a verdict that cannot yet be formed, and it stays visible beside the
  failure count rather than being folded into it.

## Workflow

1. Validate each observation: which sample, which recognized condition,
   and the occurrence flag or the measured value that condition is read
   through. Reject the wrong one of the two rather than defaulting it.
2. Evaluate each occurrence condition on its flag alone, and each
   limit-governed condition against its declared limit in that
   condition's direction of merit, admitting an exact equality at the
   limit through a named tolerance and reporting the margin beside it.
3. Refuse a repeated reading of one condition on one sample: two values
   for one measurement is a record defect, not an average.
4. Build the coverage record: per declared sample, which required
   conditions have no reading.
5. Raise a finding for every failing observation, every reading from an
   undeclared sample and every gap in the coverage record.
6. The subgroup fails on any failing observation; report the failing
   sample list, the failing observation count and the record-complete
   flag together so a near miss and a thin record stay distinguishable.

## Pitfalls

- Giving an occurrence condition a limit. A detached component does not
  become acceptable below some count; treating it as limit-governed is
  how a hard failure leaves the record as a margin.
- Comparing a retention ratio against a ceiling. Retention and
  degradation move in opposite directions, and the same numeric limit
  applied the wrong way turns a failed coupon into a passed one.
- Reading a missing limit as zero. Nothing in the record says the limit
  is zero; it says nobody declared one, and that is a finding of its own.
- Calling a subgroup clean when a sample never reported. The absence of a
  failing reading from a sample that was never read is not evidence about
  that sample, which is exactly what the coverage record preserves.
- Averaging two readings of one condition on one sample. They disagree
  for a reason, and the reason is the finding.
- Nudging a value that landed exactly on its limit. An equality at the
  bound is a representation question, handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The observation validation, the occurrence-versus-limit split, the
direction-of-merit comparison with its equality tolerance, the duplicate
reading refusal, the per-sample coverage record and the aggregated
subgroup verdict are exercised by the gate 3 contract test:
scripts/test_e2008_pva_failure_criteria.py against
scripts/e2008_pva_failure_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_pva_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

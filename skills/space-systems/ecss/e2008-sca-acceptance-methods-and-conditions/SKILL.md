---
name: e2008-sca-acceptance-methods-and-conditions
description: "Use when an SCA acceptance procedure, test condition table or method reuse justification has to be reviewed. Verify that solar cell assembly acceptance activities reuse the qualification methods and conditions clause 6.3.2 of ECSS-E-ST-20-08C points back to: trace each acceptance activity to its baseline entry, refuse a substituted measurement method, compare every condition against the baseline under its own sense and tolerance, report a relaxation that leaves acceptance weaker than the qualification it inherits, report an escalation that over-tests delivered hardware, name a condition the procedure omitted or invented, and return one reuse verdict. Trigger: ecss, e-st-20-08c, sca-acceptance-methods-and-conditions, sca-qualification-method-reuse, sca-acceptance-condition-deviation, sca-acceptance-method-substitution, sca-acceptance-over-test, sca-test-condition-baseline."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-acceptance-methods-and-conditions, e-st-20-08c, sca-acceptance-methods-and-conditions, sca-qualification-method-reuse, sca-acceptance-condition-deviation, sca-acceptance-method-substitution, sca-acceptance-over-test, sca-test-condition-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Acceptance Methods and Conditions (space-systems/ecss/e2008-sca-acceptance-methods-and-conditions)

Use when the task is clause 6.3.2 of ECSS-E-ST-20-08C: the methods and
conditions already fixed for cell assembly qualification are the ones
acceptance runs at. This leaf grades a declared acceptance procedure against
the qualification baseline it claims to inherit, activity by activity and
condition by condition.

## Domain quick reference

- Reuse is what makes an acceptance number mean something. The qualification
  data set fixed what a sound assembly looks like under one method at one set
  of conditions; a number produced any other way cannot be read against it,
  however good the alternative is on its own terms.
- A substituted method is the deepest defect, not the smallest. Swapping a
  microscope inspection for an unaided one, or an air-mass-zero simulator
  sweep for a quicker probe, invalidates every condition underneath it, so
  the method is settled before any condition is compared.
- Conditions are not all reused the same way. A severity condition — sweep
  point count, magnification, illumination — is reused at least as severely.
  A limit condition, such as a pull rate, is reused no more severely. A
  settings condition is simply reproduced. The sense belongs to the condition
  and is carried in the baseline, not assumed by the reader.
- Relaxation and escalation are both deviations and they cost different
  things. A relaxed condition makes acceptance weaker than the qualification
  it inherits, so it passes hardware the campaign would have caught; an
  escalated one over-tests good hardware and can reject an assembly that
  would have flown. The relaxation is ranked first because it ships defects.
- Conservatism inside an agreed factor is not an escalation. A condition run
  a little harder than baseline is normal test-house practice, so the
  over-test finding only opens beyond a declared factor.
- An omitted condition and an invented one are the same failure of reuse
  seen from two sides: the procedure is no longer the baseline procedure.
  Both are named, neither is silently defaulted.
- A baseline activity nobody repeats at acceptance is not a defect. Not every
  qualification test is part of the acceptance set, so it is listed for the
  reader and kept out of the findings.

## Workflow

1. Validate the baseline: each entry carries a method identifier and its
   conditions, each condition a value, a sense and a relative tolerance.
2. Trace every declared acceptance activity to a baseline entry. An activity
   that traces to nothing is reported immediately and compared no further.
3. Compare the method identifiers. A substitution sets the activity verdict
   on its own.
4. Compare each baseline condition with the declared value under its sense,
   inside its tolerance band, absorbing floating-point representation error
   at the band edge with a named relative tolerance rather than by widening
   the band.
5. Beyond the band, split the deviation by direction: weaker than baseline is
   a relaxation, stronger than baseline by more than the agreed over-test
   factor is an escalation, and stronger within the factor is still reuse.
6. Name any baseline condition the procedure omits and any declared condition
   the baseline does not carry.
7. Rank the activity — no baseline, substituted method, relaxation,
   escalation — and roll the procedure up: activities grouped by verdict, the
   reuse share, the baseline activities not repeated, and every finding in
   rank order.

## Pitfalls

- Comparing condition values and skipping the method. Two procedures can
  agree on every number and still measure different things, which is the
  failure mode a condition table cannot show.
- Applying one tolerance to every condition. An irradiance level and a pull
  rate are not held to the same precision, so the tolerance travels with the
  condition in the baseline.
- Reading every deviation as a relaxation. Direction and sense decide it,
  and an escalation is reported separately because the fix is different.
- Treating a stronger-than-baseline condition as automatically safe.
  Over-testing delivered hardware can reject assemblies the design qualified
  for, so conservatism is bounded by an agreed factor.
- Defaulting an omitted condition to the baseline value. The procedure that
  the operator follows is the one on the page; filling in the gap in the
  review is how an unreused condition reaches the floor.
- Flagging every qualification test that acceptance does not repeat. The
  acceptance set is smaller by design; the unrepeated baseline activities are
  listed, not raised.
- Judging a condition that lands exactly on its tolerance edge by bare
  arithmetic. The deviation is a ratio of floats and the edge is a round
  fraction, so a condition meant to sit on the edge can land a few units in
  the last place outside it; the comparison absorbs that while the tolerance
  stays as declared.

## Behavior contract (gate 3)

The baseline validation, the method comparison, the per-condition sense and
tolerance comparison, the relaxation and escalation split, the omitted and
unbaselined condition detectors, the ranked activity verdict and the
rolled-up reuse share are exercised by the gate 3 contract test:
scripts/test_e2008_sca_acceptance_methods_and_conditions.py against
scripts/e2008_sca_acceptance_methods_and_conditions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_acceptance_methods_and_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

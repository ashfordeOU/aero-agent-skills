---
name: q7005-acceptance-criteria-application
description: "Evaluate an infrared organic contamination result against the cleanliness level the surface has to meet under ECSS-Q-ST-70-01C. Use when a measured areal level, its expanded uncertainty and a required level have to produce a verdict rather than a number: lift an indirect result by its extraction recovery before anything is compared, apply the declared decision rule so the uncertainty is spent on the side the contract put it, treat a non-detect as a bound that proves nothing once the quantitation limit is coarser than the level, and carry an over-level surface only on a deviation with a contamination effects assessment behind it. Trigger: ecss, q-st-70-05-ir-contamination-scope, ir-contamination-acceptance-verdict, areal-cleanliness-level-limit, conformity-decision-rule-guard-band, extraction-recovery-correction, non-detect-quantitation-bound."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-acceptance-criteria-application, ir-contamination-acceptance-verdict, areal-cleanliness-level-limit, conformity-decision-rule-guard-band, extraction-recovery-correction, non-detect-quantitation-bound]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Acceptance Criteria Application (space-systems/ecss/q7005-acceptance-criteria-application)

Use when the task is the acceptance step of an ECSS-Q-ST-70-05C infrared
contamination measurement — turning a level that has been measured on a
surface into a verdict against the level that surface was allocated by
the contamination and cleanliness control plan of ECSS-Q-ST-70-01C.

## Domain quick reference

- The requirement and the result have to be the same quantity before
  they can be compared. Both are organic mass per unit area on a named
  surface, and a result that is still expressed as a residue weight, or
  as a level on a coupon standing in for the hardware, is not yet
  comparable to anything.
- An indirect result is what the solvent recovered, not what was on the
  part. Dividing by the recovery fraction is the step that turns one
  into the other, and skipping it biases every verdict the same way:
  towards passing. A recovery of two thirds hides half as much again as
  the number on the report.
- The decision rule says who pays for the uncertainty, and it is a
  contractual choice, not an analyst's preference. Simple acceptance
  compares the value alone. Guarded acceptance requires the value plus
  its expanded uncertainty to clear the level, so the applicant carries
  the doubt. A banded rule leaves a region either side of the level
  where the measurement decides nothing and says so.
- A non-detect is a bound. It demonstrates compliance when the
  quantitation limit itself sits at or under the required level, and
  demonstrates nothing when the method is coarser than the level being
  verified — which is the common case for the tightest surfaces, and is
  a finding about the method, not about the hardware.
- A surface over its level is not automatically out, but the route is
  narrow: an approved deviation and an assessment of what the excess
  does to the contamination budget. Either one alone is an assertion.
  An indeterminate result cannot take that route at all, because the
  size of what would be deviated is exactly what is unknown.

## Workflow

1. Validate each result: a named surface, a detection with a level or a
   non-detect with a quantitation limit, and a recovery fraction
   whenever the method was indirect. Refuse a record that offers a
   non-detect and a measured level at once.
2. Resolve the required level, whether it arrives as a named cleanliness
   level or as an explicit areal limit.
3. Bring the result onto the surface: divide an indirect level, and an
   indirect non-detect bound, by the recovery fraction.
4. Form the interval the declared decision rule compares — the value
   alone, the value raised by its expanded uncertainty, or the band
   either side of it.
5. Compare against the level, absorbing floating-point representation
   error at the boundary with a named tolerance rather than by relaxing
   the level.
6. Grade a non-detect on its bound, and record a finding when the bound
   cannot reach the level.
7. Assign the verdict: compliant, indeterminate when a banded rule or a
   coarse bound leaves the question open, compliant on deviation when a
   deviation and an effects assessment both stand behind an over-level
   value, non-compliant otherwise — naming the missing half of an
   incomplete deviation package.
8. Aggregate across the surfaces, keeping compliant, on-deviation,
   indeterminate and non-compliant groups apart.

## Pitfalls

- Comparing the extracted level with the required level. That is the
  solvent's result, not the surface's, and the error always favours
  acceptance.
- Reading a non-detect as a zero. It is an upper bound whose size is the
  quantitation limit, and a bound above the required level is silence.
- Letting the analyst pick the decision rule after seeing the number.
  The rule belongs to the requirement and is chosen before the run,
  otherwise the uncertainty is quietly spent on whichever side helps.
- Folding an indeterminate result into the failures. They need different
  responses: a failure needs a deviation or a clean, an indeterminate
  result needs a better measurement.
- Accepting a deviation reference as the whole justification. Without
  the effects assessment nobody has said what the excess costs the
  contamination budget.
- Widening the level so a value sitting on it passes. Equality at the
  level is a representation question, handled by the tolerance inside
  the comparison; the level itself stays as allocated.

## Behavior contract (gate 3)

The result validation, the level lookup and numeric requirement, the
recovery correction, the decision-rule interval, the non-detect bound
rule, the deviation package rule and the aggregation groups are
exercised by the gate 3 contract test:
scripts/test_q7005_acceptance_criteria_application.py against
scripts/q7005_acceptance_criteria_application_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_acceptance_criteria_application.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

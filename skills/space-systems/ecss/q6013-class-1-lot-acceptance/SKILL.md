---
name: q6013-class-1-lot-acceptance
description: "Use when lot acceptance results have to become a flight-release verdict for one date code. Assess whether one date-code lot of a highest-assurance commercial part passes lot acceptance testing under ECSS-Q-ST-60-13C clause 4.3.5: refuse a malformed date code and a delivery mixing several, check every sample against the lot it was drawn from, take each subgroup's failures against its accept number, convert them into a percent defective and compare that with the declared allowance, count the units that drifted past their delta limit, and hold the lot when any single subgroup rejects rather than averaging the subgroups together. Trigger: ecss, q-st-60-13c-clause-4-3-5, commercial-eee-lot-acceptance, date-code-lot-verdict, lat-subgroup-accept-number, lot-percent-defective-allowance, parameter-drift-reject-count, marginal-lot-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-lot-acceptance, commercial-eee-lot-acceptance, date-code-lot-verdict, lat-subgroup-accept-number, lot-percent-defective-allowance, parameter-drift-reject-count, marginal-lot-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Highest Assurance Lot Acceptance (space-systems/ecss/q6013-class-1-lot-acceptance)

Use when the task is the clause 4.3.5 lot acceptance decision of
ECSS-Q-ST-60-13C: a date code of a commercial part has been through its
lot acceptance tests, and the question is whether that date code is
released for flight or held.

## Domain quick reference

- The unit of the decision is the date code, not the delivery and not
  the part number. Units built in different weeks came off different
  material, so a delivery carrying two date codes is two lots and takes
  two verdicts; merging them lets a good week carry a bad one.
- Each subgroup -- burn-in, electrical end points, life test,
  construction analysis -- has its own sample and its own accept number.
  The subgroups are judged separately and the lot is held when any one
  of them rejects. A pooled percentage across subgroups hides the
  failure mode the split was built to expose.
- Two limits sit on the same sample: the accept number, an integer count
  of failures the subgroup tolerates, and the allowable percent
  defective, a rate applied to the sample size. A small sample can meet
  its accept number while sitting far above the rate; a large sample can
  sit under the rate with more failures than the accept number allows.
  Both have to hold.
- Parameter drift is a separate reject path. A unit whose measured delta
  between initial and post-stress readings exceeds the declared limit is
  a reject even when its end points are still inside the datasheet
  window, because a drifting commercial die is what the burn-in subgroup
  is there to find.
- A lot accepted close to its allowance is a result worth reporting. The
  next date code of the same build is the one that will cross, and a
  bare pass hides that the margin is gone.

## Workflow

1. Resolve the date code the lot is offered under; refuse a malformed
   YYWW code, and refuse a delivery whose units carry more than one code
   instead of picking the majority.
2. Validate each subgroup against the lot: a sample larger than the lot,
   a zero sample, a negative count or more failures than units sampled
   is an input error, not a degenerate case to clamp.
3. For each subgroup, compare failures with the accept number and the
   percent defective with the allowance, absorbing floating-point
   representation error at the boundary with a named tolerance rather
   than by relaxing the allowance.
4. Run the parameter-drift readings against the drift limit, taking the
   magnitude of the relative change so a downward drift counts, and
   refusing a zero initial reading where relative drift is undefined.
5. Accept the lot only when every subgroup accepts and no unit drifted;
   otherwise hold it and name every rejecting subgroup, not the first.
6. Report the disposition with each subgroup's margin, the worst drift
   seen, and a marginal-lot advisory where an accepted subgroup has used
   up most of its allowance.

## Pitfalls

- Pooling the subgroups into one percentage. Pooling lets a large clean
  burn-in sample bury a life-test failure; the subgroups are separate
  gates and are reported separately.
- Taking the accept number as the whole criterion. The allowable percent
  defective is a second, independent limit on the same sample, and a
  small sample meeting its accept number can still be far over the rate.
- Accepting a mixed date-code delivery under one verdict. That is the
  defect the date-code traceability of a commercial part exists to
  prevent; split the delivery and test each code.
- Judging drift on the end-point limits alone. A unit inside its
  datasheet window that moved more than the declared delta is a reject,
  and reading only the final value loses that entirely.
- Widening the allowance to pass an exact-equality case. An equality at
  the limit is a representation question handled by the tolerance inside
  the comparison; the declared allowance stays as specified.

## Behavior contract (gate 3)

The date-code resolution, sample validation, subgroup accept-number and
percent-defective comparisons, parameter-drift counting and the overall
hold-or-release disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_lot_acceptance.py against
scripts/q6013_class_1_lot_acceptance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_1_lot_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7080-build-lot-qualification
description: "Assess whether a build lot or first article still stands on its qualification, and whether the witness coupons support the allowable the design uses. Use when a lot of additively manufactured parts is presented under ECSS-Q-ST-70-80C qualification: sort every declared change against the configuration baseline into no impact, a delta needing fresh evidence, or a break that reruns the qualification, then take the mean, the spread and a one-sided tolerance bound from the coupons built alongside the parts, count them against what the part type owes, and rule on the lot. Trigger: ecss, q-st-70-80-additive-manufacturing-scope, am-build-lot-qualification, first-article-qualification, witness-coupon-statistics, one-sided-tolerance-bound, am-configuration-baseline-change, delta-qualification-trigger."
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
  tags: [ecss, q-st-70-80-additive-manufacturing-scope, q7080-build-lot-qualification, am-build-lot-qualification, first-article-qualification, witness-coupon-statistics, one-sided-tolerance-bound, am-configuration-baseline-change, delta-qualification-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Build Lot Qualification (space-systems/ecss/q7080-build-lot-qualification)

Use when the task is the qualification step of ECSS-Q-ST-70-80C on a
first article or a build lot -- deciding whether the lot still rests on
the qualification already held, and whether the coupons built alongside
it carry the allowable the design was sized against.

## Domain quick reference

- Additive manufacturing makes the material and the part in the same
  operation, so a qualification is never of a design alone. It is of a
  design built on a named machine, from a named feedstock, under a
  named parameter set, in a named orientation, and finished on a named
  post-process route.
- Changes therefore sort into three impacts, not two. Some leave the
  evidence standing. Some -- a new powder lot, a different orientation,
  a changed support or surface route -- leave the process recognisable
  but need fresh witness evidence against the existing qualification. A
  few -- the machine, the feedstock specification, the parameter set,
  the layer thickness, the atmosphere, the thermal post-process --
  produce a different material, and the qualification is run again.
- Where several changes land at once the worst one governs, and the
  driver is named. A lot that quietly stacks two deltas is still a
  delta; a lot that stacks a delta and a machine change is a
  requalification, and recording only the delta hides why.
- Witness coupons give a mean and a spread, and neither is an
  allowable. A one-sided tolerance bound turns them into a value a
  design can be held against, and that bound widens sharply as the
  coupon count falls -- which is exactly why a minimum count exists and
  why three coupons buy so much less than nine.
- The tolerance table is entered conservatively. A count between two
  tabulated sizes takes the factor of the smaller one, so extra coupons
  never credit a bound the table has not earned.
- Scatter is its own signal. A coefficient of variation well above what
  the process is held to says the build is not in control, whatever the
  mean says, and a wide-scatter lot can clear its allowable and still
  be evidence of an unstable process.
- A first article owes more coupons than a repeat lot, because it is
  the run that establishes the baseline every later lot is compared
  against.

## Workflow

1. Declare the part type and whether this is the first article. Reject
   an uncategorized part type rather than defaulting it, because the
   coupon count hangs off it.
2. List every configuration item that changed since the qualified
   baseline and take the worst impact across them, keeping the driver
   named.
3. Where the impact is a break, stop: the lot cannot be closed on the
   existing evidence however good the coupons are.
4. Count the witness coupons against what the part type owes, doubled
   for a first article, and report a shortfall as insufficient evidence
   rather than assessing the mean anyway.
5. Compute the mean, the sample spread, the scatter and the one-sided
   tolerance bound, and compare the bound with the design allowable.
   Report a bound that cannot be formed at all separately from one that
   is formed and falls short.
6. Close with the verdict: qualified, delta supported by fresh
   evidence, evidence insufficient, allowable not supported, or
   requalification required -- each with the finding that drove it.

## Pitfalls

- Quoting the coupon mean as the allowable. The mean is where half the
  coupons fall below, so a design held against it fails half its
  builds; the bound, not the mean, is the number a design uses.
- Treating a powder-lot change as invisible because the specification
  did not change. A new lot has its own particle size distribution,
  oxygen pickup and reuse history, and it is precisely the input that
  moves without any paperwork moving.
- Adding coupons from an earlier lot to reach the count. The count is
  evidence about this build, and coupons from a different build carry
  a different machine state, powder and thermal history.
- Reading a falling tolerance factor as a reward for testing. It is a
  statement about confidence: with few coupons the spread itself is
  poorly known, so the bound is pushed down to cover that ignorance.
- Passing a lot on the allowable while ignoring the scatter. A wide
  coefficient of variation says the process is not in control, and a
  lot that happens to clear its bound on a noisy build is a result, not
  a qualification.
- Comparing the bound with the allowable by bare arithmetic. The bound
  is a mean less a scaled square root, so a lot meant to sit exactly on
  its allowable can land a few units in the last place below it; the
  comparison absorbs that representation error while the allowable
  stays untouched.

## Behavior contract (gate 3)

The change impact grouping, coupon statistics, tolerance factor and
bound, witness count requirement and the lot verdict are exercised by
the gate 3 contract test:
scripts/test_q7080_build_lot_qualification.py against
scripts/q7080_build_lot_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_build_lot_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

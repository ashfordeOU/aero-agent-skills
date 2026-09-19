---
name: e3301-margin-of-safety-factors-of-safety
description: "Compute the yield and ultimate margins of safety a spacecraft mechanism structure has to show under ECSS-E-ST-33-01 clauses 4.7.5.2.5 and 4.7.5.2.6. Use when the factors of safety the verification route carries have to be applied to the design limit load rather than to the allowable, a special factor added for a joint or material that fails without warning, a separate margin taken against yield and against ultimate, a yield margin refused for a category that has no yield point, and the governing case named so a vanishing or negative reserve stays visible. Trigger: ecss, e-st-33-01-mechanisms, mechanism-margin-of-safety, mechanism-factor-of-safety-policy, yield-versus-ultimate-margin, mechanism-governing-load-case, brittle-category-special-factor."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-margin-of-safety-factors-of-safety, mechanism-margin-of-safety, mechanism-factor-of-safety-policy, yield-versus-ultimate-margin, mechanism-governing-load-case, brittle-category-special-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Margin of Safety and Factors of Safety (space-systems/ecss/e3301-margin-of-safety-factors-of-safety)

Use when the task is the margin demonstration of ECSS-E-ST-33-01
clauses 4.7.5.2.5 and 4.7.5.2.6 -- turning an agreed design limit load
and an agreed allowable into the two margins a mechanism structure owes,
one against yield and one against ultimate, for every load case in the
schedule.

## Domain quick reference

- The factors of safety are not a property of the part. They are the
  price of the verification route: a structure qualified on a dedicated
  test article carries the lightest pair, a protoflight article more,
  and a structure verified by analysis alone the heaviest. Changing the
  route changes the margins without touching the hardware.
- A special factor sits on top for a category whose failure gives no
  ductile warning -- a brittle metal, a fibre-dominated laminate, a
  bonded joint, a glass or ceramic element. It multiplies the factored
  load, so it is felt equally by both margins.
- All factors act on the load. The allowable stays the material
  property it was established as, which is what lets the same allowable
  be quoted across parts on different routes without being re-derived.
- The yield margin and the ultimate margin are independent results.
  They use different allowables and different factors, so which one
  governs cannot be read off the load, and reporting only the smaller
  one without naming its mode hides which failure is being approached.
- A material category with no yield point has no yield margin. Reporting
  zero there, or copying the ultimate margin across, states a result
  that was never computed; the honest output is that the mode does not
  apply and the ultimate margin governs alone.
- A margin is a quotient minus one, so a part dimensioned exactly to its
  allowable can land a few units in the last place either side of zero.
  A zero margin is a real engineering condition -- no reserve at all --
  and is reported as its own outcome rather than as a random sign.

## Workflow

1. Declare the item: identifier, verification route and material
   category. Reject an unknown route or category rather than defaulting
   to the lightest factors.
2. Resolve the factor set: the yield factor, the ultimate factor and the
   special factor the category carries.
3. Enter each load case with its design limit load and the yield and
   ultimate allowables that apply to it. The load is the one already
   raised by the model and project factors upstream.
4. Compute each applicable margin as the allowable over the load times
   the route factor times the special factor, minus one.
5. Grade each margin: a clear reserve, a zero margin within
   representation tolerance, or a genuine shortfall. Record a missing
   allowable as a finding, never as an infinite margin.
6. Report the governing margin for each case, then the driving case and
   mode for the item, plus every case sitting exactly at zero so the
   reviewer sees the ones with nothing left.

## Pitfalls

- Dividing the allowable by the factor instead of multiplying the load.
  The single-case arithmetic agrees, but the factored allowable then
  escapes into other parts and other routes where it is simply wrong.
- Applying the special factor to only one of the two modes. It prices
  the absence of warning before failure, which applies to the ultimate
  check and to any yield check that still exists.
- Quoting a yield margin for a laminate or a bonded joint. The number
  has no physical referent, and a reviewer who sees it assumes a ductile
  reserve that the part does not have.
- Treating a missing allowable as a pass. A case with no ultimate
  allowable has not been shown to have margin; it has been shown to have
  no evidence, and the two are opposite conclusions.
- Reporting the arithmetic mean or the count of positive margins. One
  negative case sizes the redesign, and an average over a schedule
  dilutes it out of sight.
- Comparing a margin against zero with a bare strict inequality. A case
  that is exactly on its allowable can land either side of zero, so the
  comparison absorbs that last-place error and grades the case as the
  zero-reserve condition it actually is.

## Behavior contract (gate 3)

The factor tables, the yield-point applicability rule, the
margin-of-safety computation, the positive, zero and negative grouping,
per-case findings for missing and category-inconsistent allowables, and
the item-level driving case and mode are exercised by the gate 3
contract test:
scripts/test_e3301_margin_of_safety_factors_of_safety.py against
scripts/e3301_margin_of_safety_factors_of_safety_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_margin_of_safety_factors_of_safety.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

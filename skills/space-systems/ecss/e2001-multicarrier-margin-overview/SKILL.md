---
name: e2001-multicarrier-margin-overview
description: "Use when evaluate the numerical multipactor margins ECSS-E-ST-20-01C clause 4.7.1 places on a multicarrier radio-frequency chain: normalize the verification route as analysis-based or test-based, read the base decibel-margin that route owes, add the uplifts the design-heritage and a computed rather than measured anchoring threshold attract, build the reference power the margin applies to -- the coherent peak-envelope-power for the analysis route, the applied multicarrier level for the test route -- and report both routes side by side with the demonstration power and crest-factor each carrier plan demands. Trigger: ecss, e-st-20-01c, multicarrier-multipactor, multicarrier-margin-policy, peak-envelope-power, multipactor-verification-route, crest-factor, carrier-plan-power."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multicarrier-margin-overview, multicarrier-multipactor, multicarrier-margin-policy, peak-envelope-power, multipactor-verification-route, crest-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Multicarrier Margin Overview (space-systems/ecss/e2001-multicarrier-margin-overview)

Use when the task is the numerical margin policy of ECSS-E-ST-20-01C clause
4.7.1 -- which decibel value a multicarrier multipactor assessment owes, which
reference power that value is applied to, and how the demand differs between
the analysis route and the test route for the same carrier plan.

## Domain quick reference

- A multicarrier chain carries at least two carriers at once, so there is no
  single power to margin against. Two aggregates matter: the summed average
  power of the carrier plan, and the coherent peak-envelope-power reached when
  every carrier adds in phase, `(sum of sqrt(P_i))^2`. Their ratio is the
  crest-factor, which for N equal carriers is `10*log10(N)` -- four equal
  carriers peak six decibels above their average.
- Clause 4.7.1 fixes the margin numerically per verification route, not per
  project. The analysis route carries the larger base value because it rests on
  a model of the geometry; the test route carries the smaller one because the
  hardware itself was driven. Applying the test value to an analysis-only case
  is the most common way a chain is declared compliant on paper alone.
- Two uplifts sit on top of the base value: design-heritage (recurrent,
  modified, first-of-kind) and the basis of the anchoring single-carrier
  threshold (measured on representative hardware, or computed). A test-based
  route resting on a computed threshold is self-contradictory and is rejected
  rather than priced.
- The reference power differs by route. The analysis route is priced against
  the coherent peak-envelope-power of the declared carrier plan. The test route
  is priced against the multicarrier level actually applied in the test, which
  is an input the campaign must state and not an aggregate the tool can infer.
- The margin is a demand on a power level, and separately a check: the achieved
  margin is the multipactor threshold over the reference power in decibels, and
  the chain is compliant only when it reaches the required value.

## Workflow

1. Validate the carrier plan: at least two carriers, every carrier power finite
   and strictly positive. Reject a single-carrier plan -- it belongs to the
   single-carrier clause, which carries a different margin table.
2. Compute the average power, the coherent peak-envelope-power and the
   crest-factor of the plan, so the numbers the margin will be applied to are
   visible before any decibel value is chosen.
3. Normalize the verification route to analysis-based or test-based and read
   the base decibel-margin that route owes from the policy table.
4. Add the design-heritage uplift and, for an analysis route, the uplift for an
   anchoring single-carrier threshold that was computed rather than measured.
   Reject a test-based route declared against a computed threshold.
5. Select the reference power: the peak-envelope-power for the analysis route,
   the applied multicarrier level for the test route. Convert it into the
   demonstration power the route must reach at the required margin.
6. Where a multipactor threshold is on record, compute the achieved margin and
   compare it against the required value; report the shortfall in decibels.
   A route with no threshold on record is an open finding, not a pass.
7. Report both routes against the same peak-envelope reference when the
   question is which verification strategy is cheaper, and aggregate every
   evaluated case into one verdict for the chain.

## Pitfalls

- Margining against the summed average power of the carrier plan -- the
  envelope peaks well above it, and for equal carriers the gap is the
  crest-factor in decibels, which is exactly the amount by which the assessment
  would be optimistic.
- Carrying the test-route decibel value into an assessment that was only ever
  analysed; the smaller value is paid for by having driven real hardware.
- Letting a test-route declaration rest on a computed threshold, which claims
  test evidence that does not exist.
- Inferring the applied multicarrier test level from the carrier plan -- the
  campaign states the level it actually applied, and guessing it silently
  changes the reference the margin is priced against.
- Treating a missing multipactor threshold as a pass because no exceedance was
  computed; nothing was demonstrated.
- Widening the required margin to absorb an exactly-compliant comparison; the
  limit stays as specified and only floating-point representation error is
  absorbed, by a named tolerance.

## Behavior contract (gate 3)

The route normalization, margin-derivation, reference-power selection,
envelope-power arithmetic and compliance-comparison logic is exercised by the
gate 3 contract test: scripts/test_e2001_multicarrier_margin_overview.py
against scripts/e2001_multicarrier_margin_overview_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multicarrier_margin_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

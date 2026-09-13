---
name: e2001-level-one-single-carrier-method
description: "Use when compute the first-level single-carrier multipactor check of ECSS-E-ST-20-01C clause 5.3.2.2.3: convert the carrier-power on the feeding line into the peak critical-region voltage, carrying the standing-wave rise and the field-concentration factor taken from the electromagnetic field solution, index the susceptibility boundary on the frequency-gap product of the driving gap and its surface-finish, interpolate that boundary in log-log space and refuse to extrapolate outside the charted span, turn the boundary-to-applied voltage ratio into a decibel multipactor-margin, compare it against the margin owed by the chosen verification-route, and invert the procedure for the largest carrier-power that still holds margin. Trigger: ecss, e-st-20-01c, e-st-20-electrical-scope, single-carrier-level-one-method, critical-region-voltage, susceptibility-chart-lookup, frequency-gap-product, multipactor-threshold-voltage, decibel-multipactor-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-level-one-single-carrier-method, single-carrier-level-one-method, critical-region-voltage, susceptibility-chart-lookup, frequency-gap-product, multipactor-threshold-voltage, decibel-multipactor-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Level-One Single-Carrier Method (space-systems/ecss/e2001-level-one-single-carrier-method)

Use when the task is the first-level single-carrier procedure of
ECSS-E-ST-20-01C clause 5.3.2.2.3 -- starting from the peak voltage in
the critical region of a gap already admitted by the level-one geometry
gate, reading the susceptibility boundary at that gap's frequency-gap
product, and turning the two voltages into a decibel margin.

## Domain quick reference

- The first level is a voltage comparison, not a particle simulation.
  Everything upstream of the chart collapses into one number: the peak
  voltage across the critical-region gap. Everything inside the chart
  collapses into a second number: the boundary voltage at which a
  resonant electron trajectory closes for that gap and that surface.
- The applied voltage starts from the forward carrier-power on the
  feeding line. A matched line gives a peak of the square root of twice
  the power times the line impedance; a standing wave raises it by one
  plus the reflection magnitude, and the field-concentration factor
  from the electromagnetic field solution scales the line voltage to
  the gap voltage at the critical region. Skipping either correction
  understates the applied voltage, and the margin inherits the error.
- The boundary is indexed on the frequency-gap product, in GHz.mm, and
  on the surface finish, because the finish sets the secondary-emission
  behaviour that sustains the resonance. A finish with a lower yield
  holds a higher boundary voltage; silver, gold, copper, chromate
  conversion and bare aluminium do not share one curve.
- The boundary curve is close to a straight line in log-log space, so
  interpolation runs on the logarithms of both axes. Outside the
  plotted span there is no curve to interpolate: the correct result is
  a refusal, because extrapolation is not evidence.
- The margin is twenty times the base-ten logarithm of the boundary
  voltage over the applied voltage. A positive but short margin is a
  different finding from a margin at or below zero: the first is a
  design shortfall against the route's requirement, the second is a
  predicted discharge at the operating condition itself.

## Workflow

1. Take the driving critical region from the geometry gate, with its
   effective gap, operating frequency and surface finish.
2. Convert the forward carrier-power into the peak line voltage at the
   declared line impedance, raise it for the worst-case standing wave,
   then scale it by the field-concentration factor to get the peak
   voltage across the gap.
3. Compute the frequency-gap product from the operating frequency and
   the effective gap.
4. Resolve the surface finish to a charted family and interpolate the
   boundary voltage in log-log space. Refuse a product outside the
   charted span instead of extrapolating.
5. Convert the boundary-to-applied ratio into a decibel margin.
6. Look up the margin owed by the verification route in force --
   analysis alone owes more than an analysis backed by a discharge
   test -- and categorize the result as compliant, short of margin, or
   a predicted discharge.
7. Where the result is short, invert the procedure to publish the
   largest carrier-power that still holds the owed margin, and rank
   every assessed region so the worst case drives the design action.

## Pitfalls

- Feeding the chart the matched-line voltage while the unit runs into
  a specified standing wave -- the peak voltage in the critical region
  is the mismatched one, and the difference is most of the margin.
- Taking the line voltage as the gap voltage and dropping the
  field-concentration factor from the field solution, so a locally
  concentrated gap is assessed at the feed value.
- Extrapolating the boundary curve past its plotted span to keep an
  assessment running, then quoting the extrapolated voltage as a
  threshold.
- Interpolating linearly on a curve plotted on logarithmic axes, which
  biases every value between two nodes.
- Assessing one finish for the whole item when a joint, a plating
  break or a bare-aluminium land puts a lower boundary in the same gap.
- Reporting a positive margin as compliant without checking it against
  the margin owed by the verification route actually selected.

## Behavior contract (gate 3)

The critical-region-voltage, frequency-gap-product, boundary-lookup,
margin and inversion logic is exercised by the gate 3 contract test:
scripts/test_e2001_level_one_single_carrier_method.py against
scripts/e2001_level_one_single_carrier_method_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_level_one_single_carrier_method.py

The bundled boundary curve is an in-house monotone stand-in that makes
the procedure runnable offline; a project passes its own digitised
chart into the lookup.

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

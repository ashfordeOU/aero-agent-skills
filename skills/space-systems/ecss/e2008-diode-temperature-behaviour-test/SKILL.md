---
name: e2008-diode-temperature-behaviour-test
description: "Use when a temperature behaviour map for protection diodes is planned or audited. Map the electrical parameters of a protection diode across its whole declared operating temperature range under ECSS-E-ST-20-08C clause 9.6.14: order the sweep and refuse a repeated temperature, take the endpoint gaps against the cold and hot ends of the range, take the widest gap between neighbouring points, fit the forward voltage temperature coefficient by least squares, derive the interval over which the reverse leakage doubles, and hold both against their bands. Trigger: ecss, e-st-20-08c-clause-9-6-14, protection-diode-temperature-sweep, diode-forward-voltage-temperature-coefficient, diode-reverse-leakage-doubling-interval, diode-operating-range-endpoint-gap, protection-diode-sweep-step-resolution."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-temperature-behaviour-test, protection-diode-temperature-sweep, diode-forward-voltage-temperature-coefficient, diode-reverse-leakage-doubling-interval, diode-operating-range-endpoint-gap, protection-diode-sweep-step-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Temperature Behaviour Test (space-systems/ecss/e2008-diode-temperature-behaviour-test)

Use when the task is clause 9.6.14 of ECSS-E-ST-20-08C -- the sweep that
produces a protection diode's parameters as a function of temperature
rather than at one convenient bench temperature. A diode on a solar wing
sees whatever the wing sees, and its forward drop, its leakage and its
knee all move with that. This clause is what turns behaviour anywhere in
the operating range from a guess into a read.

## Domain quick reference

- The map is worth exactly what its sweep is worth. Everything below is
  a property of the sweep, not of the diode, and a deficient sweep
  produces a confident map of a device that was never measured.
- The ends matter more than the middle. A sweep that stops short of the
  declared cold or hot end maps a narrower device than the one flying,
  and the extrapolation past the last point is the region the array
  actually spends its eclipse in.
- The declared operating range is itself checked. A range narrower than
  the span this map is required to cover is a scoping error upstream,
  not a sweep that happened to fit it.
- Step size decides resolution. Between two neighbouring points the
  curve is an assumption, so a knee that falls inside a wide step is
  simply absent from the map however many points sit either side of it.
- One reading per temperature. A duplicated temperature is two readings
  of one point, and a least squares fit run over it silently weights
  that point twice.
- Forward voltage moves close enough to linearly with temperature that
  a least squares slope over the sweep is the coefficient. Reverse
  leakage does not: it moves in decades, so what characterises it is the
  temperature interval over which it doubles.
- Both derived numbers sit inside a band, not under a single limit. A
  coefficient far shallower than expected is as much a finding as one
  far steeper, because a near-flat fit usually means the fixture and its
  lead resistance were measured rather than the junction.

## Workflow

1. Validate the sweep policy first: point floor, step ceiling, endpoint
   gap ceiling, required operating span, and the two derived bands. A
   band whose lower edge sits above its upper edge is refused rather
   than used, and a point floor below three is refused because a slope
   over two points is not a fit.
2. Order the sweep by temperature and refuse a repeated temperature
   before anything is derived from it.
3. Take the endpoint gaps against the declared cold and hot ends, and
   the declared span against the span this map has to cover.
4. Take the widest gap between neighbouring points and the point count.
5. Fit the forward voltage coefficient by least squares over every point
   in the sweep, and derive the leakage doubling interval from the two
   ends. A value landing exactly on a band edge passes; the comparison
   tolerance absorbs representation error and the edge does not move.
6. Report every finding, not the first, then close on one verdict in
   this order -- operating range not covered, temperature coefficient
   out of band, sweep plan deficient, or behaviour map accepted.
   Coverage outranks the fit because a fit over a sweep that misses the
   ends is a fit for a different range.

## Pitfalls

- Fitting the coefficient over a sweep that never reached the ends. The
  slope comes out looking healthy because the middle of the curve is the
  straight part; the ends are where it is not.
- Reading the point count as the resolution. Nine points clustered
  around room temperature and one at each end satisfy a count floor and
  leave a ninety kelvin hole in the middle.
- Judging the coefficient against a single ceiling. A fit far shallower
  than the family is a fixture measurement, and only a band catches it.
- Expressing the leakage trend as a percentage per kelvin. Leakage moves
  in decades over an operating range this wide, so a percentage either
  saturates or vanishes; the doubling interval is what carries it.
- Averaging two readings taken at the same temperature into the sweep
  and leaving both rows in. The fit then weights that temperature twice
  and pulls the slope toward whichever end it sits at.
- Accepting a declared operating range that is simply narrow. A sweep
  fits a narrow range easily, and the map is then correct and useless.
- Comparing a fitted slope or a doubling interval against a band edge by
  bare arithmetic. Both come out of divisions and a logarithm, which
  land a few units in the last place either side of an edge on different
  hosts, so the comparison absorbs that error while the band itself is
  never relaxed.

## Behavior contract (gate 3)

The policy validation, the sweep ordering and repeated-temperature
refusal, the sweep span and widest step, the cold and hot endpoint gaps,
the least squares forward voltage temperature coefficient, the reverse
leakage doubling interval, the two band checks and the behaviour verdict
order are exercised by the gate 3 contract test:
scripts/test_e2008_diode_temperature_behaviour_test.py against
scripts/e2008_diode_temperature_behaviour_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_diode_temperature_behaviour_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

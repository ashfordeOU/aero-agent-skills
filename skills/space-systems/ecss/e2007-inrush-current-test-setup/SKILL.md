---
name: e2007-inrush-current-test-setup
description: "Derive the bench an inrush-current measurement runs on from the standard equipment configuration, under ECSS-E-ST-20-07C clause 5.4.4.3. Use when a switch-on surge setup is built or reviewed: apply each declared delta to the baseline geometry, refuse an unknown delta or one that collapses a band, grade lead length, lead height, probe-to-connector distance, source impedance and bond resistance against their bands, combine probe and recorder bandwidth into one chain rise time, compare it with the surge edge, derive the sample rate and record length the capture needs, and return the governing parameter with the setup verdict. Trigger: ecss, e-st-20-07c, inrush-current-test-setup, switch-on-surge-bench, inrush-measurement-chain-bandwidth, inrush-current-probe-placement, inrush-capture-sample-rate, inrush-bench-deviation-categorization."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-inrush-current-test-setup, switch-on-surge-bench, inrush-measurement-chain-bandwidth, inrush-current-probe-placement, inrush-capture-sample-rate, inrush-bench-deviation-categorization]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Inrush-Current Test Setup (space-systems/ecss/e2007-inrush-current-test-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.4.3 -- arranging the bench that captures the current surge a unit
draws at switch-on. The clause does not build a bench from nothing: it
starts from the standard equipment configuration already used for the
other runs and modifies it only where measuring a fast transient
demands something different.

## Domain quick reference

- The bench is a derived arrangement, not an independent one. Every
  departure from the standard configuration is a declared delta with a
  reason; an undeclared departure is a setup finding even when the
  number it produces looks reasonable. A delta may move a band, never
  close it, so a delta leaving a parameter with no admissible value is
  an input error rather than a very tight bench.
- Geometry still matters at switch-on. Lead length and lead height
  above the ground-plane set the loop inductance the surge has to drive,
  the probe-to-connector distance sets how much of the harness is inside
  the measured loop, and the bond resistance sets the return path. A
  surge measured on a long lead is partly a measurement of the lead.
- The measurement chain has to be faster than the event. Probe and
  recorder rise times add in quadrature, so the combined chain is always
  slower than either instrument alone; only when the chain is several
  times faster than the surge edge is the recorded rise time the unit's
  own rather than the bench's.
- Sample rate follows from the chain, not from habit. The rate has to
  put several points on one chain rise time, so a slower chain needs a
  lower rate and a fast chain paired with a slow digitizer throws away
  the bandwidth that was paid for.
- Record length follows from the settling, not from the peak. The trace
  has to run on until the draw has settled to its steady value, which is
  a multiple of the settling time constant, and the surge peak says
  nothing about how long that takes.
- A shunt and a current probe are not interchangeable in a soft source.
  A shunt inserts the series resistance the surge sees, so in a source
  of negligible declared impedance the captured peak can be a property
  of the bench.

## Workflow

1. Validate the realized bench: a recognized probe type, positive
   geometry, non-negative resistances, positive instrument bandwidths,
   sample rate and record length, and a deviation list naming only
   graded parameters.
2. Resolve the bands: start from the baseline configuration and apply
   each declared delta, refusing an unknown parameter, an unknown delta
   key and any delta that collapses a band.
3. Grade each geometry parameter against its resolved band as
   conforming, a declared deviation, or nonconforming.
4. Combine probe and recorder bandwidth into a chain rise time and
   chain bandwidth, and compare against the bandwidth the declared surge
   edge needs.
5. Derive the sample rate from the chain bandwidth and the record length
   from the settling time constant, then compare both against what the
   bench offers.
6. Rank the graded parameters by their fractional distance from the
   nearer band edge and name the governing one.
7. Aggregate: an undeclared excursion, an inadequate chain, too slow a
   sample rate or too short a record are findings; a declared excursion
   and a shunt in a stiff source are limitations carried with the run.

## Pitfalls

- Treating the inrush bench as a fresh arrangement. It inherits the
  standard configuration, and a parameter nobody thought to declare is
  still being changed silently.
- Comparing the probe bandwidth alone against the surge edge. The
  recorder is in series with it, and the quadrature sum is what the
  transient actually passes through.
- Setting the sample rate from the surge duration. The rate has to
  resolve the rising edge the chain can still pass, which is a much
  shorter time than the event.
- Ending the record at the peak. The clause wants the transient
  behaviour, and the return to the steady draw is the half that shows
  the unit recovered.
- Accepting a declared deviation as if it were conformance. It keeps the
  run usable, but it travels with the results as a limitation and has to
  reach whoever reads them.

## Behavior contract (gate 3)

The bench validation, delta resolution, band grading, chain rise time
and bandwidth combination, sample-rate and record-length derivation,
governing-parameter ranking and the aggregate verdict are exercised by
the gate 3 contract test:
scripts/test_e2007_inrush_current_test_setup.py against
scripts/e2007_inrush_current_test_setup_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_inrush_current_test_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

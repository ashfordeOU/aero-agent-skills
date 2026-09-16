---
name: e2008-equivalent-network-calculation
description: "Use when a cell capacitance figure is quoted without saying which equivalent network it belongs to. Derive the equivalent circuit elements of a solar cell from one measured impedance per ECSS-E-ST-20-08C clause 11.1.4.2.1: split magnitude and phase into the series resistance and reactance, form the series capacitance, the loss tangent and the quality factor, transform that pair into the parallel capacitance and loss resistance, report the spread between the two forms, remove the declared contact and lead resistance, then close by rebuilding the measurement from the derived network. Trigger: ecss, e-st-20-08c-clause-11-1-4-2-1, solar-cell-equivalent-network, series-to-parallel-impedance-conversion, cell-loss-tangent, cell-quality-factor, contact-series-resistance-correction, impedance-closure-residual."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-equivalent-network-calculation, solar-cell-equivalent-network, series-to-parallel-impedance-conversion, cell-loss-tangent, cell-quality-factor, contact-series-resistance-correction, impedance-closure-residual]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Equivalent Network Calculation (space-systems/ecss/e2008-equivalent-network-calculation)

Use when the task is clause 11.1.4.2.1 of ECSS-E-ST-20-08C -- turning
the impedance a bridge or analyser measured on a solar cell into the
element values of an equivalent network. The measurement is two numbers
at one frequency, a magnitude and a phase. A solar cell is not a
capacitor, so those two numbers do not name a capacitance until a
network has been chosen to hold them.

## Domain quick reference

- Two equivalent networks fit the same measurement exactly: a
  resistance in series with a capacitance, and a resistance across a
  capacitance. Both reproduce the measured impedance at the measurement
  frequency, and neither is more correct than the other.
- They are nevertheless different numbers. C_p = C_s / (1 + D squared),
  so the gap between the two forms is D squared over one plus D
  squared. On a low-loss article that is parts per thousand and nobody
  notices; on a lossy cell it is per cent, and a capacitance quoted
  without naming its form is ambiguous by that amount.
- The loss terms are what connect the forms. The dissipation factor is
  the series resistance over the magnitude of the series reactance --
  equivalently the tangent of the angle by which the measurement falls
  short of a quarter turn -- and the quality factor is its reciprocal.
  R_p = R_s (1 + Q squared) follows from the same pair.
- The measured phase has to lie strictly between a quarter turn of lag
  and zero. Zero is a pure resistance, a quarter turn is a lossless
  capacitance no real cell presents, and a positive phase is an
  inductive fixture -- a lead loop or a resonance -- that the
  resolution cannot represent and must refuse rather than fold into a
  capacitance.
- Contact and lead resistance adds to the measured series resistance
  and belongs to the harness, not the cell. It is subtracted before the
  cell's own series resistance is reported, and a harness term that
  reaches a large share of the measurement means the fixture is
  dominating the element being derived.
- The derivation closes on itself. Rebuilding the impedance from the
  derived parallel pair returns the magnitude and phase that went in,
  so a residual above representation error indicates the resolution,
  not the measurement.
- An instrument that also prints a parallel capacitance is a second
  opinion, not a confirmation: a disagreement between its readout and
  the derived value usually means the two are resolving different
  networks or different frequencies.

## Workflow

1. Take the magnitude, the phase and the measurement frequency, and
   refuse the derivation when any of them is absent.
2. Validate the phase as capacitive and strictly inside the quadrant;
   refuse a resistive, lossless or inductive measurement instead of
   clamping it into range.
3. Resolve the magnitude and phase into the series resistance and the
   series reactance, and invert the reactance into the series
   capacitance at the measurement frequency.
4. Form the dissipation factor from the series pair and the quality
   factor from its reciprocal.
5. Transform to the parallel form: the loss resistance from the
   quality factor, the capacitance from the dissipation factor.
6. Report the spread between the two capacitances and raise it as a
   finding once the two forms can no longer be used interchangeably.
7. Subtract the declared contact and lead resistance to leave the
   cell's own series resistance, and report the share the harness
   carried.
8. Rebuild the impedance from the derived parallel pair, take the
   closure residual against the measurement, and reconcile any
   instrument readout that was supplied.
9. Report every element, both forms, the loss terms and a verdict that
   stays open while any finding stands.

## Pitfalls

- Quoting a capacitance with no network named. The figure is only
  unambiguous while the cell is nearly lossless, and the reader has no
  way to tell which form it was.
- Comparing a series capacitance from one instrument with a parallel
  capacitance from another and calling the difference a measurement
  error. It is the transform, and it is predictable from the loss.
- Leaving the contact and lead resistance inside the derived series
  resistance. It biases the loss terms in one direction, which then
  biases the parallel form through both the quality factor and the
  capacitance.
- Folding a positive phase into a capacitance. An inductive reading is
  a fixture fault -- a lead loop or a resonance near the measurement
  frequency -- and resolving it as a capacitance hides the fault in a
  plausible number.
- Treating the closure rebuild as decoration. It is the only check that
  the resolution was carried out correctly at all, and it costs one
  evaluation of the derived network.
- Comparing a spread or a deviation against its limit by bare
  arithmetic. Both are quotients of floats that can land a few units in
  the last place either side of a round fraction, so the comparison
  absorbs that error while the limit itself is never relaxed.
- Reading an instrument's own parallel readout as confirmation of the
  derivation. Until the frequency and the network form behind the
  readout are known, agreement is a coincidence and disagreement is
  undiagnosed.

## Behavior contract (gate 3)

The capacitive phase validation, series resolution, series capacitance,
dissipation and quality factors, series-to-parallel transform, network
spread, contact resistance correction and share, impedance rebuild,
closure residual and instrument readout reconciliation are exercised by
the gate 3 contract test:
scripts/test_e2008_equivalent_network_calculation.py against
scripts/e2008_equivalent_network_calculation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_equivalent_network_calculation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

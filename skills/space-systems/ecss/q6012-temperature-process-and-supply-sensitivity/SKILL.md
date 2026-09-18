---
name: q6012-temperature-process-and-supply-sensitivity
description: "Evaluate the temperature, process and supply spread of an MMIC design. Use when a die must hold its specification over its thermal envelope, lot-to-lot fabrication variation and rail tolerance, per ECSS-Q-ST-60-12C clause 7.2.6: resolve the cold and hot excursions, the rail band and the process sigma the foundry data supports, turn each into a performance excursion through its sensitivity coefficient, add deterministic axes arithmetically and root-sum-square only genuinely independent distributions, emit the corner matrix the simulation must cover, then grade the window against the specification and name the axis owning the spread. Trigger: ecss, q-st-60-12-mmic-scope, mmic-pvt-sensitivity, temperature-excursion-spread, process-sigma-basis, supply-rail-tolerance-excursion, worst-case-corner-matrix, root-sum-square-combination, dominant-sensitivity-axis."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-temperature-process-and-supply-sensitivity, mmic-pvt-sensitivity, temperature-excursion-spread, process-sigma-basis, supply-rail-tolerance-excursion, worst-case-corner-matrix, root-sum-square-combination, dominant-sensitivity-axis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Temperature, Process and Supply Sensitivity (space-systems/ecss/q6012-temperature-process-and-supply-sensitivity)

Use when the task is the sensitivity evaluation of ECSS-Q-ST-60-12C clause
7.2.6: a monolithic microwave integrated circuit is specified at one
temperature, one lot and one rail, and the question is how far its
performance moves once the flight part sits at the ends of its thermal
envelope, comes off a different wafer, and runs on a rail that drifts
inside its regulation band.

## Domain quick reference

- The three axes are not the same kind of quantity, and treating them as
  one is the defect this clause exists to catch. Temperature is a
  deterministic swing: the die genuinely reaches both ends of the
  envelope, so both ends are carried. Process spread is statistical:
  wafers and lots scatter about a foundry mean with a quoted sigma.
  Supply is either, and which one it is depends on whether the rail
  carries a specified tolerance band or a measured regulation
  distribution.
- An excursion is measured from the point the nominal performance was
  actually characterised at, not from the middle of the envelope. A part
  characterised at room temperature inside a minus-forty to
  plus-eighty-five envelope has a longer reach to hot than to cold in
  one direction and the reverse in the other; the asymmetry is real and
  survives into the window.
- A sensitivity coefficient carries a sign. A gain that falls with
  temperature turns the cold excursion into the high end of the
  contribution, so the low and high ends of a contribution are ordered
  after the multiplication, never before it.
- Combination follows the bases. Every contribution added at its extreme
  is the only honest method when no axis carries a distribution.
  Root-sum-square is admissible only when every axis is an independent
  measured distribution -- which temperature never is. The usual MMIC
  case is therefore the hybrid: deterministic axes added arithmetically,
  statistical axes root-sum-squared on top of them.
- The corner set follows the shape of the response. A monotone response
  is bounded by its extremes, so the single-axis corners plus the two
  all-extreme corners and the nominal point cover it. A response that
  turns over inside the envelope is not bounded by its extremes, and the
  full three-level grid on all three axes is carried instead.
- The ranking is the design output. The axis that owns the largest share
  of the spread is the one where a compensation network, a tighter rail
  or a lot-acceptance screen buys the most, and it is rarely the axis
  the designer expected.

## Workflow

1. Declare the data basis of each axis before any number is computed,
   and reject an uncategorized basis rather than defaulting it. The
   basis decides the combination method, so a basis chosen after the
   result is a result with no traceable justification.
2. Resolve the three excursions. Take the cold and hot reach from the
   characterisation temperature, the low and high reach from the nominal
   rail, and the coverage-sigma reach from the foundry parameter sigma.
   Reject a characterisation point that sits outside the envelope and a
   rail nominal that sits outside its band.
3. Turn each excursion into a signed performance contribution through
   its sensitivity coefficient, ordering the low and high ends after the
   sign has been applied.
4. Select the combination method the bases permit, refuse a
   root-sum-square while any axis is a bound, and fold the contributions
   into one low and high spread.
5. Place the spread around the nominal to get the performance window,
   rank the axes by the share of the spread each owns, and emit the
   corner matrix the simulation has to cover.
6. Where a specification window exists, grade the performance window
   against it and report both margins; otherwise close with the spread
   quantified and explicitly not yet graded.

## Pitfalls

- Root-sum-squaring the temperature axis. The statistics of a normal
  population do not apply to a swing every unit experiences in full, so
  squaring it and taking a root understates a value the part genuinely
  reaches. Temperature is added arithmetically whatever the other axes
  do.
- Simulating the nominal corner and calling the design characterised.
  The nominal point is the one operating condition the flight part is
  least likely to sit at, and a spec held at nominal says nothing about
  the ends of the envelope.
- Taking a single wafer's measured spread as the process sigma. One lot
  samples within-lot variation only; the lot-to-lot term that dominates
  a production run is invisible in it, and a sigma derived that way is
  optimistic by the part of the variance it never saw.
- Ignoring the sign of a sensitivity and carrying the larger excursion
  as the larger contribution. The cold end of a falling response is the
  high end of its contribution, and a window built without ordering the
  pair after the multiplication is inverted on that axis.
- Grading the window against the specification by bare arithmetic. The
  window is built through a chain of multiplications and a square root,
  so a design that sits exactly on the specification edge can land a few
  units in the last place outside it; the comparison absorbs that
  representation error while the specification stays untouched.
- Reducing the corner set on a response that turns over. A gain peak or
  a bias-current minimum inside the envelope is not bounded by the
  extremes, and the reduced corner set walks straight past it.

## Behavior contract (gate 3)

The excursion resolution, signed contribution ordering, combination
method selection, root-sum-square refusal, window placement, contributor
ranking, corner-matrix reduction and specification verdict are exercised
by the gate 3 contract test:
scripts/test_q6012_temperature_process_and_supply_sensitivity.py against
scripts/q6012_temperature_process_and_supply_sensitivity_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6012_temperature_process_and_supply_sensitivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-sca-electrical-parameter-test-process
description: "Determine whether a solar cell assembly electrical parameter run under ECSS-E-ST-20-08C clause 6.4.3.3.2 recorded current at enough points to describe the assembly: hold the measured irradiance against the reference illumination and the cell temperature against its control band, confirm the sweep reaches short circuit and open circuit, count the points, size the largest voltage step and the sampling around the maximum power knee, then derive short-circuit current, open-circuit voltage, the peak power point and the fill factor from the recorded points. Use when a current-voltage sweep is about to be accepted as the electrical parameter record for a solar cell assembly. Trigger: ecss, e-st-20-08c-clause-6-4-3-3-2, solar-cell-assembly-electrical-parameter-test, solar-cell-current-voltage-sweep-density, standard-illumination-irradiance-tolerance, solar-cell-temperature-control-band, solar-cell-maximum-power-knee-sampling, solar-cell-fill-factor-derivation."
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
  tags: [ecss, e-st-20-08-solar-cell-assembly-scope, e2008-sca-electrical-parameter-test-process, solar-cell-assembly-electrical-parameter-test, solar-cell-current-voltage-sweep-density, standard-illumination-irradiance-tolerance, solar-cell-temperature-control-band, solar-cell-maximum-power-knee-sampling, solar-cell-fill-factor-derivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Electrical Parameter Test Process (space-systems/ecss/e2008-sca-electrical-parameter-test-process)

Use when the task is clause 6.4.3.3.2 of ECSS-E-ST-20-08C -- recording
the current of a solar cell assembly at many points of its
characteristic curve, under the standard illumination and with the cell
temperature held at a controlled value. The clause's subject is a
recording, not a reading. What separates a record from a set of numbers
is where the points sit and whether the conditions held still while
they were taken.

## Domain quick reference

- Two conditions govern every point on the curve. Illumination sets the
  current almost proportionally, so a per-cent error in irradiance is a
  per-cent error in every recorded current. Cell temperature moves the
  voltage the other way, a few millivolts per kelvin per junction, so a
  warm cell records a lower power at the same illumination and nothing
  in the number says why.
- The temperature that matters is the cell's, not the plate's or the
  chamber's. A junction under a sun simulator runs above whatever the
  fixture is held at, and the control band applies to the junction the
  current comes out of.
- Point placement decides what the record can support. A sweep is
  useless past its own ends: without a point at or below zero volts
  there is no short-circuit current, and without the current crossing
  zero there is no open-circuit voltage. Both are ends of the record,
  not extrapolations from it.
- The knee is the expensive part of the curve. Peak power is taken from
  the recorded points, so a sweep that steps across the knee reports the
  best point it happened to take rather than the assembly's maximum, and
  the error is always in the pessimistic direction.
- A voltage step has to be sized against the open-circuit voltage, not
  fixed in volts. The same 50 mV step is fine on a single junction and
  coarse on a series string, because the curve's features scale with the
  voltage the assembly reaches.
- A recorded current that rises with voltage somewhere along the sweep
  is not noise to average out. It means two conditions, two sweep
  directions or two articles are mixed in one record, and the derived
  parameters cannot be attributed.
- The fill factor is the one derived number that exposes the record
  itself. It is peak power over the product of the two crossings, so a
  missed knee, a drifted illumination and a resistive contact all move
  it, and an implausible value is a signal to re-examine the sweep.

## Workflow

1. Validate the recording policy first: reference irradiance, its
   tolerance, the temperature control point and band, the point floor,
   the step fraction and the knee window. A sampling floor too small to
   describe a curve is refused rather than used.
2. Order the recorded points by voltage and refuse the record outright
   if it repeats a voltage or carries a malformed point -- a recorded
   point has one current, and the ambiguity cannot be resolved later.
3. Check the ends before anything else. A sweep that never reaches
   short circuit or never reaches open circuit yields no crossings, so
   report it as incomplete and stop rather than deriving parameters
   from an interpolation the record does not support.
4. Compare the measured irradiance against the reference level and the
   cell temperature against its control point. A value landing exactly
   on a tolerance is inside it; the comparison absorbs representation
   error and the tolerance itself does not move.
5. Derive the short-circuit current at the zero-voltage crossing, the
   open-circuit voltage at the zero-current crossing, the maximum power
   point from the recorded points, and the fill factor from the three.
   Report them whatever the verdict, since they are what the run was
   for.
6. Size the sampling: the point count against its floor, the largest
   voltage step against the fraction of open-circuit voltage allowed,
   the points inside the knee window against their floor, and the
   current for a rise that should not be there.
7. Close on one verdict -- sweep incomplete, conditions not controlled,
   sweep under-sampled, or electrical parameters recorded -- reporting
   every finding, not only the first.

## Pitfalls

- Quoting a total point count as evidence of a good sweep. Points
  bunched on the flat current plateau cost nothing and buy nothing; the
  count only matters together with the step size and the knee window.
- Taking peak power straight from the recorded points without asking
  how close they sit. The maximum of a coarse sweep is a lower bound on
  the assembly's maximum, and it is reported with the same confidence
  as a dense one.
- Holding the fixture temperature rather than the cell temperature. The
  junction sits above the plate under illumination, and the record
  carries no trace of the difference.
- Fixing the voltage step in volts across articles. A step sized for a
  single junction leaves a series string with a handful of points on
  the knee, and the sweep still looks dense in the point count.
- Treating a missing crossing as something to extrapolate. Running the
  first two points back to zero volts produces a short-circuit current
  that no instrument recorded, and it carries no uncertainty anyone can
  state.
- Comparing a derived step or deviation against its limit by bare
  arithmetic. The limits are fractions of measured quantities, so both
  sides are floats that can land a few units in the last place either
  side of the bound; the comparison absorbs that error while the bound
  itself is never relaxed.
- Averaging a forward and a reverse sweep into one record. The two
  differ wherever the assembly has not settled, and the average has a
  rising current segment that is an artefact of the merge.

## Behavior contract (gate 3)

The policy validation, sweep ordering and rejection rules, short-circuit
and open-circuit crossing checks, linear interpolation at each crossing,
maximum power point, fill factor, knee-window point count, largest
voltage step, irradiance and cell-temperature band checks and the
process verdict are exercised by the gate 3 contract test:
scripts/test_e2008_sca_electrical_parameter_test_process.py against
scripts/e2008_sca_electrical_parameter_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_electrical_parameter_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

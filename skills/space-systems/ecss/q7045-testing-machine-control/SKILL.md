---
name: q7045-testing-machine-control
description: "Verify that a testing machine, its force-measuring channel and its extensometry are fit for a planned mechanical test on a metallic specimen. Use when a laboratory has to clear a frame before a run under ECSS-Q-ST-70-45: turn every verification reading into a relative indication error and grade the force channel on its worst one, hold the planned peak force above the lowest verified force and below capacity, grade the extensometer on whichever of its relative and absolute errors binds at the gauge length in use, convert a required strain rate into the crosshead speed a compliant load train actually needs, and grade alignment on the bending an opposed gauge pair reports. Trigger: ecss, q-st-70-45-mechanical-testing, tensile-machine-force-verification-grade, tensile-extensometer-grade-selection, tensile-crosshead-speed-from-strain-rate, tensile-load-train-alignment-bending, tensile-verified-force-range."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-testing-machine-control, tensile-machine-force-verification-grade, tensile-extensometer-grade-selection, tensile-crosshead-speed-from-strain-rate, tensile-load-train-alignment-bending, tensile-verified-force-range]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Testing Machine Control (space-systems/ecss/q7045-testing-machine-control)

Use when the task is the equipment step of a mechanical test under
ECSS-Q-ST-70-45: a frame, a force channel, an extensometer and a rate
controller are about to be used on a metallic specimen, and the question
is whether the machine as set up can produce a number the acceptance
decision is allowed to rest on.

## Domain quick reference

- A force-measuring system is graded on its worst verification reading,
  not on its average one. One point three percent out at the top of the
  range pulls the whole channel down to the grade that covers it, even
  where every other point sits inside a tenth.
- The grade is only claimed over the span it was verified over. Below
  the lowest verified force a reading carries the accuracy of the bottom
  of the range, so a small specimen pulled on a large frame can be out
  of the verified span while the frame is nominally excellent.
- An extensometer carries two errors and the binding one changes with
  gauge length. A few micrometres of absolute error is negligible on a
  two hundred millimetre gauge length and dominant on a ten millimetre
  one, so the grade has to be taken at the length actually in use.
- Crosshead speed is not strain rate. The crosshead covers the extension
  of the parallel length plus the deflection the load train takes up, so
  on a compliant frame a speed computed from the gauge length alone
  under-drives the specimen through the elastic part of the curve.
- Bending on the load train is read from opposed gauges as the spread
  over twice the mean axial strain. It falsifies a modulus and a proof
  strength long before it shows up as a visibly crooked specimen.

## Workflow

1. Turn every force-verification reading into a relative indication
   error against its reference, take the worst by magnitude, and read
   the grade off the tabulated limits; a reading outside the coarsest
   limit leaves the channel ungraded rather than merely coarse.
2. Compare the grade obtained with the grade the property being measured
   requires, and raise a named finding when it falls short.
3. Place the planned peak force inside the verified span: below capacity
   and above the lowest verified force, defaulting that floor to a
   declared fraction of capacity when no verification floor is stated.
4. Turn the extensometer absolute error into an equivalent relative
   error at the gauge length and strain of interest, report which of the
   two binds, and grade it against the requirement.
5. Compute the crosshead speed as the specimen extension rate plus the
   load-train deflection rate at the force rate of the moment, and
   report it in millimetres per minute.
6. When opposed gauge readings are supplied, form the bending percentage
   and grade it against the alignment limit, absorbing an exact equality
   at the limit as representation error.
7. Declare the setup usable only when nothing above raised a finding,
   and carry every finding forward by name.

## Pitfalls

- Grading the force channel on its mean error. The worst reading is what
  the grade means, and averaging hides exactly the top-of-range point
  the acceptance load sits near.
- Trusting a grade below the verified span. A frame verified from two
  percent of capacity upwards says nothing about a specimen that peaks
  at half a percent of it.
- Taking an extensometer grade from the datasheet without the gauge
  length. The same instrument is class 0.5 on a long gauge length and
  outside the grades on a short one.
- Setting crosshead speed from the gauge length alone on a compliant
  frame. The elastic part of the curve is then run slow, which moves the
  measured modulus and the proof strength with it.
- Treating a quiet load train as an aligned one. Bending is measured
  with opposed gauges, not inferred from the absence of a complaint.

## Behavior contract (gate 3)

The indication-error arithmetic, force-channel grading, verified-span
placement, extensometer grade selection at the gauge length in use,
crosshead-speed conversion with load-train compliance and the alignment
bending percentage are exercised by the gate 3 contract test:
scripts/test_q7045_testing_machine_control.py against
scripts/q7045_testing_machine_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7045_testing_machine_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

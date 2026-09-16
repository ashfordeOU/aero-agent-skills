---
name: e2008-working-standards-with-pulsed-simulators
description: "Use when a reference cell must be read on a flash simulator rather than a steady-state source. Verify that a solar-array working standard answers fast enough in short-circuit mode to be read under a pulsed simulator, per ECSS-E-ST-20-08C clause 10.2.2.3.4: form the short-circuit time constant from the cell capacitance and the loop resistance, size the settling the declared tolerance demands, place the sampling window inside the flash plateau and after that settling, hold the shunt voltage down to a true short circuit, and grade plateau ripple and flash-to-flash repeatability before the reading is kept. Trigger: ecss, e-st-20-08c, solar-array-working-standard-pulsed-response, pulsed-simulator-short-circuit-settling, reference-cell-flash-time-constant, flash-plateau-sampling-window, working-standard-flash-repeatability."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-working-standards-with-pulsed-simulators, solar-array-working-standard-pulsed-response, pulsed-simulator-short-circuit-settling, reference-cell-flash-time-constant, flash-plateau-sampling-window, working-standard-flash-repeatability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Working Standards With Pulsed Simulators (space-systems/ecss/e2008-working-standards-with-pulsed-simulators)

Use when the task is clause 10.2.2.3.4 of ECSS-E-ST-20-08C -- whether a
working standard answers adequately in short-circuit mode while a
pulsed simulator illuminates it. A steady-state source gives the cell
as long as it needs to settle; a flash gives it a plateau a few
milliseconds wide, and the question is whether the standard is already
at its short-circuit current when the window opens.

## Domain quick reference

- The short-circuit loop is a capacitance charged through a
  resistance, so its answer to the flash is an exponential with one
  time constant: the cell capacitance times the series resistance plus
  the shunt. Resistance in ohms times capacitance in microfarads is a
  time constant in microseconds, which is why the electrical side is
  kept in those units and the flash timing, quoted in milliseconds by
  the simulator, is converted once at the boundary.
- Settling is a tolerance, not an event. The current approaches its
  final value and never arrives, so the declared tolerance fixes how
  many time constants the window has to wait: a tenth of a percent is
  about seven, a percent about five. Quoting a settling time without
  the tolerance it was computed against says nothing.
- The window has two edges and both matter. Opening it before the
  plateau catches the rise of the lamp; closing it after the plateau
  catches the decay. A window that fits the plateau but opens too
  early still reads a standard that has not settled, so plateau
  containment and settling are separate findings.
- Short circuit is a claim about the operating point, not about the
  wiring. The shunt develops a voltage across the standard; while that
  voltage stays small against the open-circuit voltage the cell sits on
  the flat part of its curve and the current read is the short-circuit
  current. Let it grow and the reading slides down the knee.
- A two-wire shunt puts the lead resistance inside the measured loop.
  It both lengthens the time constant and lifts the operating point,
  and it is reported on its own line because the repair is a re-wire,
  not a wider window.
- Flash-to-flash spread and plateau ripple are properties of the
  simulator, not of the standard, but they land on the same reading. A
  standard that settles perfectly into a lamp whose plateau ripples is
  still not delivering a number worth keeping.

## Workflow

1. Normalise the standard and the flash. Reject a non-positive
   capacitance, shunt resistance, current or voltage, and reject a
   plateau that ends before it starts, rather than defaulting any of
   them -- every later number is derived from these.
2. Form the time constant from the loop resistance and the cell
   capacitance, then the settling time the declared tolerance demands.
3. Compare the settling against the delay the window actually has, the
   gap between the plateau opening and the window opening, and report
   the residual error still left at that delay.
4. Check plateau containment at both edges, and check separately that
   the plateau is wide enough to hold the settling plus the window.
5. Take the shunt voltage and express it as a fraction of the
   open-circuit voltage, so the short-circuit claim is graded rather
   than assumed, and flag a two-wire shunt on its own line.
6. Grade plateau ripple and, where repeated flashes were taken, their
   spread about the mean, then withhold the adequate verdict unless
   every finding is empty.

## Pitfalls

- Reading a short time constant as a settled standard. The constant is
  the shape of the answer; the window still has to wait several of them
  for the tolerance that was declared, and a cell with a large
  capacitance and a modest series resistance can need milliseconds.
- Quoting the settling as a bare time. Two laboratories settling the
  same standard to different tolerances get different numbers from the
  same hardware, so the tolerance travels with the figure.
- Treating plateau containment and settling as one check. A window can
  sit wholly inside the plateau and still open while the current is
  climbing, which is why the two are reported separately.
- Assuming the shunt makes a short circuit because it is small. Small
  against what decides it: a shunt that is negligible for a quarter-amp
  cell moves a multi-amp string well off short circuit.
- Folding a two-wire connection into the resistance and moving on. The
  loop is then modelled correctly and still measured wrongly, and the
  finding that would have sent someone to the harness is gone.
- Comparing a settling time against a plateau width by bare arithmetic.
  Both are built from an exponential and a converted timing and can
  land a few units in the last place apart for the same hardware on two
  platforms, so the comparison absorbs that representation error while
  the bound itself stays where it was.

## Behavior contract (gate 3)

The standard and flash normalisation, time constant, tolerance-driven
settling time, residual response error, plateau containment, shunt
short-circuit fraction, two-wire finding, plateau ripple and flash
repeatability are exercised by the gate 3 contract test:
scripts/test_e2008_working_standards_with_pulsed_simulators.py against
scripts/e2008_working_standards_with_pulsed_simulators_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_working_standards_with_pulsed_simulators.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

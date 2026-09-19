---
name: q7045-elevated-and-low-temperature-testing
description: "Assess an elevated or low temperature mechanical test on a metallic piece against the thermal-control rules of ECSS-Q-ST-70-45C: derive the deviation allowance that applies at the nominal temperature, size the soak from the section so the piece is at temperature and not merely surrounded by it, place enough thermocouples along the parallel length to see a gradient, grade the axial gradient and the hold stability across the loaded window, and confirm the strain device is rated for the temperature it sat at. Use when reviewing a hot or cryogenic test report, setting up a furnace or cryostat, or explaining a strength figure that drifted. Trigger: ecss, q-st-70-45c, elevated-temperature-mechanical-test, cryogenic-mechanical-test, test-piece-soak-time, furnace-axial-gradient, thermocouple-placement-parallel-length."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-elevated-and-low-temperature-testing, elevated-temperature-mechanical-test, cryogenic-mechanical-test, test-piece-soak-time, furnace-axial-gradient, thermocouple-placement-parallel-length]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Elevated and Low Temperature Testing (space-systems/ecss/q7045-elevated-and-low-temperature-testing)

Use when the task is the non-ambient part of the test-conditions clause of
ECSS-Q-ST-70-45C: holding a test piece at a temperature away from room
conditions, proving it is actually at that temperature, and keeping it there
while the piece is loaded.

## Domain quick reference

- The allowance is a ladder read off the nominal, not one number. In absolute
  kelvin it widens as the furnace gets hotter, because holding a hot chamber
  that tightly is not achievable; as a fraction of the nominal it narrows the
  whole way up. At the cryogenic end it tightens again in absolute terms,
  because a few kelvin there move the property a long way.
- The chamber temperature is not the piece temperature. A furnace at set point
  with a cold piece still inside it will produce a strength that belongs to
  neither, which is why the measurement point is on the piece and the soak is
  what closes the gap.
- Soak time is a section problem. The time to bring the interior of a thick
  piece to temperature scales with the section, and a soak sized on the
  previous thinner piece leaves a core that is still cold and a surface that
  is not.
- One thermocouple cannot see a gradient. A single reading on a long parallel
  length reports one point and says nothing about the two ends, so the number
  of measurement points follows the length being held.
- The axial gradient is a separate acceptance from the deviation of the mean.
  A furnace whose mean sits exactly on the nominal while one end runs hot is
  compliant on the mean and is not holding the piece at one temperature.
- Stability during loading is the acceptance that matters. A drift that would
  be trivial during the soak becomes a moving material property while the
  curve is being recorded, so the loaded window is graded on its own.
- Extensometry has a temperature rating. A device outside its rating produces
  a strain that is partly its own thermal expansion, and at cryogenic
  temperature the same problem appears with the opposite sign.

## Workflow

1. Read the nominal test temperature and take the deviation allowance from the
   ladder rather than from a single remembered figure.
2. Size the soak from the section and the mode, hot or cold, and compare it
   with the soak actually held before loading.
3. Take the number of measurement points the parallel length requires, and
   reject a set that is short, whatever the individual readings show.
4. Compute the mean of the piece readings and its deviation from the nominal,
   and grade it against the allowance.
5. Compute the axial gradient as the spread across the measurement points and
   grade it against its own limit, separately from the deviation of the mean.
6. Grade the stability across the loaded window: the maximum departure of any
   reading from the nominal during loading, against the allowance.
7. Check the strain device rating covers the nominal temperature, and close
   with the findings that bear on whether the result belongs to the material
   at the stated temperature.

## Pitfalls

- Reading the allowance off the chamber controller's display band. The
  controller holds the chamber; the acceptance is on the piece, and a
  well-controlled chamber can sit around a piece that is not at temperature.
- Sizing the soak from the last test. The section changed, and the soak that
  equilibrated a thin strip leaves a thick block with a cold core.
- Accepting a compliant mean with a gradient across the parallel length. The
  mean is one number and the piece has a temperature at every point; the
  gradient is its own acceptance.
- Instrumenting a long parallel length with one thermocouple. It cannot
  measure what it is being used to demonstrate, so the run has no evidence of
  uniformity at all.
- Grading the soak window and the loaded window together. A drift is tolerable
  while the piece equilibrates and is a moving property while the curve is
  recorded.
- Leaving an ambient-rated extensometer on a hot or cryogenic piece. Part of
  the strain it reports is its own, and the sign of the error flips between
  the hot and the cold case.
- Relaxing an allowance to accept a mean that lands exactly on it. The
  equality is a representation question handled by the tolerance inside the
  comparison; the thermal limits stay as specified.

## Behavior contract (gate 3)

The deviation-allowance ladder, the section-driven soak, the thermocouple-count
rule, the mean deviation, the axial-gradient acceptance, the loaded-window
stability grading and the strain-device temperature rating are exercised by the
gate 3 contract test:
scripts/test_q7045_elevated_and_low_temperature_testing.py against
scripts/q7045_elevated_and_low_temperature_testing_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q7045_elevated_and_low_temperature_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

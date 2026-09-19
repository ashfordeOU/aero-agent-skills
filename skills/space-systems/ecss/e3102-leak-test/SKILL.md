---
name: e3102-leak-test
description: "Define the leak test of a two-phase heat transport item under ECSS-E-ST-31-02C clause 5.6.8. Use when the task is deriving the acceptance leak rate from the fluid inventory the item may lose over its life rather than quoting one, picking a method whose sensitivity actually resolves that rate, converting a helium tracer reading to the working fluid through the inverse square root of molar mass, and grading the converted rate against the acceptance value while separating a real measurement from a reading below the instrument floor. Trigger: ecss, e-st-31-02c, derived-acceptance-leak-rate, helium-tracer-molar-mass-conversion, leak-test-method-sensitivity, two-phase-fluid-inventory-loss, instrument-floor-non-detection."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-leak-test, derived-acceptance-leak-rate, helium-tracer-molar-mass-conversion, leak-test-method-sensitivity, two-phase-fluid-inventory-loss, instrument-floor-non-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Leak Test (space-systems/ecss/e3102-leak-test)

Use when the task is the leak test of ECSS-E-ST-31-02C clause 5.6.8 --
what rate the item is allowed to leak, whether the chosen method can
even see that rate, and what a tracer-gas reading has to be turned into
before it is compared with anything.

## Domain quick reference

- The acceptance leak rate is derived, not looked up. A two-phase item
  carries a charge it cannot top up, and what the mission can tolerate
  is a fraction of that inventory lost over the life. That mass becomes
  a throughput through the specific gas constant of the working fluid,
  the reference temperature and the mission duration. A long mission or
  a small charge produces a tight rate, and that is the number the test
  has to demonstrate.
- Sensitivity is a property of the method, and it decides whether the
  test can exist. An instrument whose floor sits near the acceptance
  rate cannot distinguish an article at the limit from one well inside
  it, so the floor has to be finer than the acceptance rate by a
  resolution ratio. Choosing a method that fails this is a defect in the
  test definition, discovered before the article is touched.
- A declared facility sensitivity is honoured when it is coarser than
  the method's best, because rigs are rarely at their theoretical limit.
  A declared sensitivity finer than the method can physically reach is
  refused; it is a transcription error, not a better instrument.
- A helium reading is not the service leak rate. In molecular flow the
  throughput goes with the inverse square root of molar mass, so helium
  streams through a given path faster than a heavier working fluid. The
  tracer number over-reads and has to be converted down before it is
  graded, or an article gets rejected for a leak it does not have.
- A reading below the instrument floor is a non-detection, not a
  measurement. It is still an acceptable result -- the item leaks less
  than anything can see -- but it is reported as a non-detection so
  nobody later treats the floor value as a measured rate.

## Workflow

1. Validate the working-fluid molar mass in kg/mol, refusing a value
   that is plainly in g/mol, and form its specific gas constant.
2. Derive the acceptance leak rate from the allowed inventory loss, the
   reference temperature and the mission duration. Honour an explicitly
   declared acceptance rate as an override, and keep the derived value
   alongside it so the two can be compared.
3. Normalise the method and resolve the sensitivity to grade with: the
   method's best, or a coarser declared facility value.
4. Grade that sensitivity against the acceptance rate at the resolution
   ratio, and report the required sensitivity so an inadequate method
   names its own replacement threshold.
5. Convert the tracer reading to the working fluid by the inverse root
   of molar mass.
6. Grade the converted rate against the acceptance rate, and separately
   report whether the reading sits above the instrument floor.
7. Combine the two checks into one verdict and name each failed check.

## Pitfalls

- Quoting a leak rate from a previous programme. The acceptance rate is
  a function of this item's charge, this mission's duration and this
  fluid; a number carried across is right only by coincidence.
- Grading a helium reading directly against a working-fluid acceptance
  rate. The tracer over-reads, so the article is rejected for a leak
  roughly twice the size of the one it has.
- Converting in the wrong direction. The heavier fluid leaks more
  slowly, so the converted service rate is below the helium reading, not
  above it.
- Choosing a bubble or pressure-decay method for a rate a mass
  spectrometer was needed for. The test then returns a clean result that
  means only that the method could not see the leak.
- Recording an instrument-floor value as the measured leak rate. It is
  a non-detection; treating the floor as a datum turns an unknown into a
  number and, repeated across units, into a trend that does not exist.
- Relaxing the acceptance rate so an exactly-at-limit reading passes.
  Equality at a limit is a representation question, handled by the
  tolerance inside the comparison, not by moving the rate.

## Behavior contract (gate 3)

The molar-mass validation and specific gas constant, acceptance-rate
derivation from inventory loss and mission duration, method
normalisation and sensitivity resolution, sensitivity grading at the
resolution ratio, tracer-to-service conversion, measured-rate grading
with the instrument-floor distinction and the rolled-up verdict are
exercised by the gate 3 contract test: scripts/test_e3102_leak_test.py
against scripts/e3102_leak_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3102_leak_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

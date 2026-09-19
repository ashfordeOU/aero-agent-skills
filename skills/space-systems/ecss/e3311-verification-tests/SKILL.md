---
name: e3311-verification-tests
description: "Define the verification tests an explosive device owes under ECSS-E-ST-33-11C clause 4.14.3, then grade the ones already run. Use when the task is deciding whether an initiator, cartridge or explosively actuated device has actually been tested: holding the specified no-fire current for the full dwell without the unit functioning, demonstrating firing at or below the stated all-fire current with the required output, discharging pin-to-pin and pin-to-case at the electrostatic threshold with no function and no degradation, raising environmental levels above the mission environment by the qualification factor, and keeping every exposed unit out of flight stock. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-verification-test-matrix, initiator-no-fire-dwell-test, all-fire-firing-demonstration, initiator-esd-exposure-test, explosive-environmental-qualification-level, test-exposed-unit-disposition."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-verification-tests, explosive-verification-test-matrix, initiator-no-fire-dwell-test, all-fire-firing-demonstration, initiator-esd-exposure-test, explosive-environmental-qualification-level, test-exposed-unit-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Verification Tests (space-systems/ecss/e3311-verification-tests)

Use when the task is the verification-test requirement of
ECSS-E-ST-33-11C Rev.1 clause 4.14.3 -- settling which tests an
explosive item owes, and whether the tests already on the record
actually demonstrate what their titles claim.

## Domain quick reference

- An explosive device is verified along two opposite axes at once. The
  firing demonstration proves it works when it is meant to; the no-fire
  and discharge exposures prove it does not work when it is not meant
  to. A programme that only ever fires units is half a programme.
- A no-fire test is a dwell, not a pulse. The specified current has to
  be held for the full specified duration, because the mechanism it
  guards against is thermal: a bridgewire that survives a brief
  overcurrent can still reach ignition temperature over minutes at a
  lower one.
- A firing demonstration made by over-driving the unit proves nothing
  about the level written on the datasheet. If the specification names
  an all-fire current, the demonstration is made at that current or
  under it; a unit fired at twice the level has demonstrated only that
  it fires at twice the level.
- Electrostatic discharge reaches an initiator by two distinct paths --
  between the pins, and from a pin to the case -- and they stress
  different insulation. Exercising one and reporting "ESD tested" leaves
  the other path unverified. Passing means neither functioning nor
  degrading: a unit whose bridge resistance moved is a finding even
  though it did not fire.
- Environmental levels are the mission environment raised by the
  qualification factor, never the mission environment itself. Testing at
  the flight level qualifies nothing, because the margin the factor
  buys is exactly what covers build-to-build spread.
- Every unit the programme exposes is consumed by it. A no-fire sample
  has been thermally cycled at the edge of ignition and an
  environmental sample has spent its margin; both are test evidence
  from that point on, not flight stock.

## Workflow

1. Enumerate the owed categories -- functional firing, environmental,
   electrostatic discharge, no-fire -- and report any the declared
   programme never covers, before grading any individual test.
2. Grade the no-fire test on three things together: the current reached
   the specified level, the dwell reached the specified duration, and
   the unit did not function. A pass needs all three.
3. Grade the firing demonstration on the applied current staying at or
   below the specified all-fire value, the unit functioning, and the
   delivered output reaching the required value.
4. Grade the discharge exposure on both paths being exercised, the
   applied voltage reaching the threshold, and the unit neither
   functioning nor degrading afterwards.
5. Compute the required environmental level from the mission level and
   the qualification factor, refusing a factor below unity, and grade
   the applied level against it.
6. Walk the unit register and raise a finding for any unit that was
   exposed by the programme and is still carried as flight stock.
7. Absorb representation error at every level comparison with a named
   tolerance, so an exactly-on-limit test is not failed by the last bit
   of a multiplication.

## Pitfalls

- Reading a no-fire pass off the current alone. A unit that saw the
  right current for a tenth of the dwell has not been tested; the
  duration is half the requirement and is the half usually dropped when
  a schedule tightens.
- Accepting a firing demonstration made above the stated all-fire
  current. This is the most common way an all-fire figure enters a
  datasheet unverified, and it is invisible unless the applied current
  is graded against the specified one rather than against the outcome.
- Treating "did not fire" as a discharge pass. Degradation without
  function is the failure mode that matters for a unit that then flies,
  so the post-exposure measurement is part of the verdict.
- Qualifying at the mission level. The qualification factor is not a
  conservatism to be traded away; testing at the flight level leaves
  zero margin for the unit that is one build-spread worse than the
  sample.
- Returning an exposed sample to flight stock because it "passed". The
  test consumed it. This is a configuration-control failure that the
  test report itself never shows, so it is graded from the unit
  register.
- Widening a level to make an exactly-on-limit case pass. An equality at
  the boundary is a representation question, handled by the tolerance
  inside the comparison; the specified level stays as specified.

## Behavior contract (gate 3)

The category coverage, no-fire dwell grading, all-fire demonstration
grading, discharge-path coverage, qualification-level computation and
exposed-unit disposition are exercised by the gate 3 contract test:
scripts/test_e3311_verification_tests.py against
scripts/e3311_verification_tests_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3311_verification_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

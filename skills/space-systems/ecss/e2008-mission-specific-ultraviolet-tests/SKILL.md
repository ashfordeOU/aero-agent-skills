---
name: e2008-mission-specific-ultraviolet-tests
description: "Determine whether a solar cell assembly earns ultraviolet testing beyond the standard qualification exposure under ECSS-E-ST-20-08C clause 6.4.3.15.4: scale solar intensity by the inverse square of heliocentric distance across every declared mission phase, accumulate the equivalent sun hours a science or planetary profile actually collects, compare that budget with the exposure the standard qualification already covers, then check the planned lamp intensity, the acceleration over the mission mean and the sample temperature keep the accelerated run representative. Use when a near-sun science or planetary profile may outrun the baseline ultraviolet qualification. Trigger: ecss, e-st-20-08c-clause-6-4-3-15-4, mission-specific-ultraviolet-test, solar-cell-assembly-ultraviolet-exposure, equivalent-sun-hours-budget, near-sun-solar-intensity-multiplier, ultraviolet-acceleration-factor-bound, coverglass-ultraviolet-darkening."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-mission-specific-ultraviolet-tests, mission-specific-ultraviolet-test, solar-cell-assembly-ultraviolet-exposure, equivalent-sun-hours-budget, near-sun-solar-intensity-multiplier, ultraviolet-acceleration-factor-bound, coverglass-ultraviolet-darkening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Mission-Specific Ultraviolet Tests (space-systems/ecss/e2008-mission-specific-ultraviolet-tests)

Use when the task is to decide, under ECSS-E-ST-20-08C clause 6.4.3.15.4,
whether a science or planetary mission collects enough ultraviolet for the
solar cell assembly to need exposure beyond the standard qualification run --
and, when it does, whether the accelerated run that is planned actually
delivers that exposure in a way the hardware responds to the same way it will
in flight.

## Domain quick reference

- The standard ultraviolet qualification exposure is sized for an ordinary
  near-Earth mission. A profile that leaves that envelope -- a flyby inside
  half an astronomical unit, an inner-planetary cruise, a solar observatory
  that never enters eclipse -- collects a dose the baseline never bounded.
- Intensity is the inverse square of the heliocentric distance in
  astronomical units. At 0.5 AU the assembly sees four suns; at 0.3 AU it
  sees eleven. Distance, not duration, is what makes these missions extreme.
- The exposure budget is equivalent sun hours: intensity multiplied by
  illuminated hours, accumulated over every declared phase. An eclipse-rich
  orbit spends part of its time collecting nothing, and a profile that omits
  the illuminated fraction overstates its own dose.
- The mean intensity the assembly actually works under is the dose divided by
  the illuminated hours, not the peak. It is the denominator of the
  acceleration factor, so quoting the peak understates how hard the lamp is
  being driven relative to flight.
- Acceleration has a ceiling. Coverglass and adhesive darkening follows the
  dose only while the colour centres fill at a rate the material can anneal
  against; drive the lamp beyond that and the run produces a degradation the
  mission never sees, in either direction.
- Darkening saturates. The rise in solar absorptance fills toward a ceiling
  set by the stack rather than growing with dose without bound, so a long
  mission and a very long mission can end at nearly the same absorptance --
  and the thermal case that follows from it.
- A sample illuminated far from its flight operating temperature is a valid
  measurement of a different article state: darkening and annealing both move
  with temperature, and nothing in the resulting number says which one won.

## Workflow

1. Validate the exposure policy first: standard qualification exposure, the
   margin that earns extra testing, the acceleration ceiling, the facility
   intensity ceiling and the sample temperature allowance. A margin below one
   is refused rather than used.
2. Group the declared mission profiles, rejecting an unrecognised one rather
   than ignoring it, and map each to the exposure the extra testing has to
   demonstrate. Append the shared objective whenever any profile is present.
3. Accumulate the mission exposure budget phase by phase, and keep the
   illuminated hours alongside it so the dose-weighted mean intensity is
   available for the acceleration factor.
4. Decide whether extra testing is earned at all: a declared profile present
   and a budget at or above the standard exposure times the margin. A budget
   landing exactly on the threshold earns the testing; the comparison
   tolerance absorbs representation error and the threshold does not move.
5. When it is earned and a run is planned, compute the exposure that run
   delivers, the acceleration over the mission mean, and the offset between
   the sample temperature and the flight operating temperature.
6. Report the predicted absorptance rise whatever the verdict -- it is the
   thermal input the rest of the panel design waits on.
7. Close on one verdict: extra testing not required, test not planned, test
   inadequate, or mission exposure demonstrated -- reporting every inadequacy
   found, not only the first.

## Pitfalls

- Budgeting the mission dose from the peak intensity. A flyby spends hours at
  perihelion and years in cruise; the peak sizes the thermal case, not the
  ultraviolet dose.
- Forgetting the illuminated fraction. An eclipse-rich planetary orbit can
  collect half the dose its mission duration suggests, and the extra testing
  it earns is sized accordingly.
- Buying dose coverage with lamp intensity alone. The run reaches the number
  and leaves the acceleration factor unbounded, which is the one thing the
  clause's representativeness rests on.
- Asking for an intensity the chamber cannot produce. A plan that needs twenty
  suns from a ten-sun facility is not a schedule problem discovered late; it is
  a plan with no run behind it.
- Illuminating at ambient because the thermal rig was not ready. The dose is
  delivered and the darkening mechanism is not the flight one, so the number
  is precise about the wrong article state.
- Treating a declared profile as sufficient reason to test. A budget below the
  exposure the standard qualification already covers buys nothing, however
  exotic the mission sounds.

## Behavior contract (gate 3)

The policy validation, the inverse-square intensity, the phase and mission
exposure budget, the illuminated hours and dose-weighted mean intensity, the
extra-testing threshold, the acceleration factor and lamp-hour sizing, the
saturating absorptance rise, the profile inventory and objective mapping, and
the campaign verdict are exercised by the gate 3 contract test:
scripts/test_e2008_mission_specific_ultraviolet_tests.py against
scripts/e2008_mission_specific_ultraviolet_tests_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_mission_specific_ultraviolet_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

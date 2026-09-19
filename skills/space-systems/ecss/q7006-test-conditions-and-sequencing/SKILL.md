---
name: q7006-test-conditions-and-sequencing
description: "Define the conditions and the exposure sequence a radiation degradation run is carried out under per ECSS-Q-ST-70-06C: grade the chamber pressure and the achieved specimen temperature against their limit and band, split the total exposure into steps that account for the whole run, build the cumulative exposure and beam hours at every measurement point, grade the flux rate against the mission rate and the acceleration limit, check the agent block order covers each agent once, and bound the air exposure of a property that recovers. Use when writing or reviewing a test procedure. Trigger: ecss, q-st-70-06c, irradiation-chamber-pressure-limit, specimen-temperature-during-exposure, exposure-step-sequencing, cumulative-fluence-measurement-point, combined-or-sequential-agent-order, post-exposure-air-recovery-window."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-test-conditions-and-sequencing, irradiation-chamber-pressure-limit, specimen-temperature-during-exposure, exposure-step-sequencing, cumulative-fluence-measurement-point, combined-or-sequential-agent-order, post-exposure-air-recovery-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Test Conditions and Sequencing (space-systems/ecss/q7006-test-conditions-and-sequencing)

Use when the task is the procedure clause of ECSS-Q-ST-70-06C: the vacuum
and specimen temperature the exposure is held at, the rate it is driven at,
and how the total exposure is broken into steps with measurements between
them.

## Domain quick reference

- Vacuum is a chemistry requirement, not a cleanliness one. Residual oxygen
  and water join the degradation pathway, so an exposure at a soft pressure
  measures accelerated ageing in a thin atmosphere and not the space
  environment the coupons are being qualified for.
- Specimen temperature sets the competition between damage and annealing. The
  same fluence at a higher temperature anneals as it accumulates and reports
  less degradation, so the temperature is specified with a band and the band
  is graded on what was achieved, not on what the controller was asked for.
- The flux rate is bounded on both sides. Too fast and the dose rate changes
  the mechanism; slower than the mission is not conservative either, it
  simply spends beam time producing a result the mission already bounds.
- A single exposure step gives one end point. The campaign exists to produce
  a degradation trend, so the exposure is interrupted at intermediate
  cumulative fluences, and those partial points are what distinguish a
  saturating material from one still degrading at end of life.
- Step fractions have to account for the whole exposure. A set summing to
  less than one leaves the specified level undelivered; a set summing to more
  overshoots it, and either way the last measurement point is not the level
  the specification named.
- Order is part of the procedure. A combined block exposes both agents at
  once; sequential blocks expose them one after the other, and each agent
  appears exactly once — an agent exposed twice doubles its dose and an agent
  omitted leaves the campaign incomplete.
- Some degradation recovers in air. Colour centres bleach and radicals
  quench, so a property with that behaviour is read in place under vacuum, or
  inside a bounded air-exposure window that is part of the procedure rather
  than of the laboratory's habits.

## Workflow

1. Grade the chamber pressure achieved during exposure against the limit,
   and the achieved specimen temperature against the specified value and its
   band, treating the boundary with a named tolerance.
2. Normalise the requested step fractions and refuse a set that does not sum
   to the whole exposure.
3. Build the sequence: per-step exposure from the fraction, step duration
   from the chosen flux, and cumulative exposure and elapsed beam hours at
   every measurement point.
4. Grade the flux rate: compute the acceleration factor against the mission
   flux, and raise a finding above the limit and again below unity.
5. Grade the agent block order against the agents the campaign needs, so
   that each appears exactly once whether combined or sequential.
6. Grade the interruptions: a single step is a finding in its own right, and
   a property that recovers in air is read in place or inside the bounded
   air-exposure window.
7. Return the sequence with its cumulative columns, the acceleration factor
   and every finding, marking the procedure ready only when there are none.

## Pitfalls

- Specifying the vacuum on the pump rather than on the chamber during
  exposure. Outgassing from the coupons and the holder raises the pressure
  once the beam is on, and the base pressure quoted from an empty chamber is
  not the pressure the degradation happened at.
- Recording the setpoint instead of the achieved specimen temperature. The
  coupon is heated by the beam and cooled only by its mount, so its own
  temperature can sit well outside the band the controller reports.
- Running the whole exposure to a single end point. A material that saturated
  at a tenth of the fluence and one still degrading at the end give the same
  final reading, and only the intermediate points separate them.
- Step fractions that do not sum to one. The campaign then reports a level it
  never delivered, and the discrepancy is invisible in the run log because
  every individual step ran exactly as written.
- Leaving the agent order out of the procedure. The two sequential orders do
  not give the same result on a material whose surface is altered by the
  first agent, so an unwritten order cannot be reproduced.
- Measuring an air-sensitive property at the bench hours after the chamber is
  opened. The recovery is fast, the reading is of a partly healed material,
  and the campaign understates the degradation it was run to find.

## Behavior contract (gate 3)

The pressure and temperature grading, step-fraction normalisation, sequence
construction with cumulative exposure and hours, flux-rate grading, agent
order checking and interruption grading are exercised by the gate 3 contract
test: scripts/test_q7006_test_conditions_and_sequencing.py against
scripts/q7006_test_conditions_and_sequencing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7006_test_conditions_and_sequencing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

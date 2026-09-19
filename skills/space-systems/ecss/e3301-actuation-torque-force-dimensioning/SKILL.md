---
name: e3301-actuation-torque-force-dimensioning
description: "Size the actuator of a spacecraft mechanism so the worst-case resistive torque or force stays under the capability actually available throughout life and travel, per ECSS-E-ST-33-01 clause 4.7.5.3.2. Use when nominal actuator capability has to be derated for low bus voltage, temperature extreme, current limit and end-of-life degradation, compared station by station against the factored resistive demand, turned into a motorization margin at each station, and graded over a travel schedule dense enough that no gap hides the crossing point. Trigger: ecss, e-st-33-01-mechanisms, mechanism-motorization-margin, available-actuation-torque-derating, resistive-versus-available-torque, mechanism-travel-station-schedule, end-of-life-actuator-capability."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-actuation-torque-force-dimensioning, mechanism-motorization-margin, available-actuation-torque-derating, resistive-versus-available-torque, mechanism-travel-station-schedule, end-of-life-actuator-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Actuation Torque and Force Dimensioning (space-systems/ecss/e3301-actuation-torque-force-dimensioning)

Use when the task is the actuation sizing of ECSS-E-ST-33-01 clause
4.7.5.3.2 -- holding the factored resistive demand of a mechanism
against the capability its actuator can be relied on to deliver, at
every point of travel and at every life point.

## Domain quick reference

- Both sides of the comparison move with position. An actuator's torque
  varies over its electrical and mechanical cycle, and the resistance a
  hinge or a drive sees varies with harness wrap, bearing preload and
  contact geometry. A single comparison at one operating point proves
  nothing about where the two curves cross.
- Available capability is the nominal value after derations, not the
  catalogue number. The relevant reductions are the lowest qualified
  bus voltage, the temperature extreme the unit operates at, any supply
  current limit, and the degradation accumulated by the life point
  being assessed. Each is a factor at or below unity and they multiply.
- An end-of-life station owes an explicit degradation deration. A
  station labelled end of life whose capability equals its begin-of-life
  value has not been aged; it has only been relabelled.
- The motorization margin is the derated capability over the factored
  resistive demand, minus one. The demand side is the already-factored
  total from the uncertainty build-up, so the factors are not reapplied
  here and are not omitted either.
- The project may require more than a bare positive margin. The
  requirement is carried explicitly so a margin that clears zero but
  misses the programme threshold is reported as short rather than as a
  pass.
- Coverage is part of the result. A schedule that samples only the two
  ends of travel steps over the middle, and a schedule that exists only
  at begin of life says nothing about the end of the mission.

## Workflow

1. Declare the function: identifier, torque or force units, travel
   range, the required motorization margin and the life points the
   assessment has to cover.
2. Enter each station with its travel position, its life point, the
   nominal actuator capability there, the derations that apply, and the
   factored resistive demand at that position.
3. Derate the capability at each station by the product of its
   declared derations, and flag an end-of-life station with no
   degradation deration.
4. Compute the motorization margin at each station and grade it against
   the required margin, treating a margin that lands exactly on the
   requirement as the zero-reserve condition rather than as a random
   sign.
5. Check travel coverage separately at each required life point: both
   ends reached, and no gap between stations wider than the policy
   allows.
6. Report the governing station, its life point and its margin, plus
   every station and coverage finding, so the sizing decision names the
   place where the mechanism is actually short.

## Pitfalls

- Comparing a catalogue torque against a nominal resistance. Both
  numbers are the optimistic end of their own distribution, and the
  pair of them hides the whole of the clause.
- Applying the uncertainty factors again on the demand side. The
  factored total already carries them; a second application inflates
  the demand and drives an unnecessary actuator upsize.
- Assessing only the stall or only the running point. A geared drive
  can be capable at stall and short at speed, and a stepper can be
  capable at speed and short at the detent it has to pull out of.
- Labelling a station end of life without ageing it. The label is not
  the deration, and a begin-of-life capability carried into an
  end-of-life row is the most common way this clause is silently
  failed.
- Treating a positive margin as a pass when the programme requires
  more. The requirement is a declared number; grading against zero
  quietly retailors it.
- Comparing a margin against its requirement by bare arithmetic. A
  station sized exactly to the requirement can land a few units in the
  last place either side of it, so the comparison absorbs that
  representation error instead of alternating between pass and fail.

## Behavior contract (gate 3)

Deration validation, the derated capability product, the motorization
margin, grading against a declared required margin, the end-of-life
degradation check, per-life-point travel coverage, and the governing
station and life point are exercised by the gate 3 contract test:
scripts/test_e3301_actuation_torque_force_dimensioning.py against
scripts/e3301_actuation_torque_force_dimensioning_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_actuation_torque_force_dimensioning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-thermal-cycle-acceptance-general
description: "Assess whether an acceptance thermal cycling run on a photovoltaic assembly holds to the vacuum environment ECSS-E-ST-20-08C clause 5.5.3.7.2 prefers, and size what a gas fill changes when it does not: name the environment from the chamber pressure, derive the molecular mean free path and the Knudsen number against the gap the heat crosses, group the conduction regime, measure the cold dwell against the frost point of the fill, and judge oxidation of exposed metallisation at the hot dwell, all against a recorded justification. Use when a campaign is about to be cycled in atmosphere because the vacuum chamber was busy. Trigger: ecss, e-st-20-08c-clause-5-5-3-7-2, solar-array-vacuum-cycling-preference, ambient-atmosphere-cycling-justification, chamber-knudsen-conduction-regime, cold-dwell-frost-point-margin, interconnect-oxidation-exposure, thermal-vacuum-chamber-pressure-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-thermal-cycle-acceptance-general, solar-array-vacuum-cycling-preference, ambient-atmosphere-cycling-justification, chamber-knudsen-conduction-regime, cold-dwell-frost-point-margin, interconnect-oxidation-exposure, thermal-vacuum-chamber-pressure-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Acceptance Cycling Environment (space-systems/ecss/e2008-thermal-cycle-acceptance-general)

Use when the task is clause 5.5.3.7.2 of ECSS-E-ST-20-08C -- the
general provision that acceptance thermal cycling of a photovoltaic
assembly is preferably carried out under vacuum rather than in ambient
atmosphere. On orbit the assembly exchanges heat by radiation alone and
sits in a dry, non-oxidising environment. A chamber full of gas gives
it none of those conditions, so the preference is about the stress that
actually reaches the article, not about chamber availability.

## Domain quick reference

- The chamber pressure names the environment, and the three cases are
  not on a smooth scale. Vacuum, a rarefied fill and a room-pressure
  atmosphere behave differently enough that a run has to be judged
  against the one it is actually in.
- Gas carries heat that vacuum does not. Whether that matters is a
  Knudsen question: the molecular mean free path, k T over root-two pi
  d squared P, against the gap the heat has to cross. In the continuum
  regime the gas behaves as a fluid and the assembly follows the
  chamber faster and more evenly than radiation alone would carry it.
- Only in the free-molecular regime can the gas path be left out of the
  profile. Between the two, the conduction is real but partial, which
  is the worst place to be because the profile looks plausible and is
  not the flight one.
- Water in the fill deposits on cold surfaces. A coverglass or a bond
  line that frosts at the cold dwell is being tested against a
  mechanism that does not exist on orbit, and the damage that follows
  is indistinguishable afterwards from a workmanship escape.
- Oxygen attacks exposed metallisation at the hot dwell. Silver
  interconnects tarnish in air at elevated temperature, so a run in
  atmosphere can degrade the joints the screen was built to judge.
  The risk needs both conditions: a hot enough dwell and a fill with
  more than trace oxygen.
- Departing from vacuum is not forbidden, it is argued. A dry inert
  purge with a profile compensated for gas conduction is a defensible
  run; the same chamber full of room air is not, and the difference is
  written down rather than assumed.

## Workflow

1. Take the chamber pressure and name the environment. If it is
   vacuum, the preference is met and no gas evidence is owed -- but
   confirm the Knudsen number really is free-molecular, because a
   pressure reading that disagrees with the regime is a reading to
   check before the profile is trusted.
2. For any non-vacuum run, require the gas evidence before judging:
   the frost point of the fill and its oxygen fraction. Missing
   evidence stops the judgement rather than defaulting to a benign
   value.
3. Derive the mean free path at the cold dwell, form the Knudsen
   number against the characteristic gap, and group the conduction
   regime from it.
4. Require a recorded justification for the departure, and require the
   thermal profile to have been compensated whenever the gas
   conduction is not negligible.
5. Measure the cold dwell against the frost point and hold a margin,
   so the cold end cycles the assembly instead of icing it.
6. Judge the hot dwell against the oxygen fraction, and close with the
   verdict the evidence supports: preference met, departure justified,
   or departure not justified.

## Pitfalls

- Reading a chamber pressure gauge as proof of a radiation-limited
  profile. The regime, not the gauge, decides whether the gas is
  carrying heat, and a gap of a centimetre needs a mean free path of
  metres before the gas can be ignored.
- Cycling in a nitrogen purge and calling it vacuum-equivalent. An
  inert fill removes the oxidation problem and leaves the conduction
  one untouched, so the ramp the assembly sees is still not the
  flight ramp.
- Taking the frost point from the bottle rather than from the chamber.
  A dry gas picks up water from the chamber walls and the article, and
  the cold dwell is where that shows up.
- Treating a cold-dwell deposit as a workmanship escape. Frost damage
  is an artefact of the test environment; charging it to the supplier
  buys a corrective action against a mechanism the flight article will
  never meet.
- Comparing a Knudsen number or a frost margin against its boundary by
  bare arithmetic. Both are quotients of derived floats that can land
  a few units in the last place either side of a limit, so the
  comparison absorbs that error while the boundary itself is never
  moved.
- Recording the justification for atmosphere and stopping there. The
  justification is the permission to depart; the sized deviations are
  what make the run reviewable afterwards.

## Behavior contract (gate 3)

The environment naming from chamber pressure, the mean free path and
Knudsen number, the conduction-regime grouping and its negligibility
rule, the gas-evidence requirement, the recorded justification and
profile compensation, the cold-dwell frost margin and the hot-dwell
oxidation exposure are exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycle_acceptance_general.py against
scripts/e2008_thermal_cycle_acceptance_general_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycle_acceptance_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

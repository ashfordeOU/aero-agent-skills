---
name: e2007-radiated-magnetic-susceptibility-purpose
description: "Evaluate whether a radiated magnetic susceptibility test plan serves the aim of ECSS-E-ST-20-07C clause 5.4.10.1. Use when the task is judging a plan against the purpose rather than a limit: confirming a current-carrying loop stands at the declared standoff from the unit face, that the swept band spans the low-frequency magnetic region, that a required field strength and something watching the unit are both on record, and quantifying the swept share of the aim band across decades together with the axial field the loop truly produces at that standoff. Trigger: ecss, e-st-20-07c, radiated-magnetic-susceptibility-purpose, magnetic-radiating-loop-standoff, magnetic-field-strength-requirement, magnetic-susceptibility-band-coverage, loop-axial-field-computation, susceptibility-performance-monitoring."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-magnetic-susceptibility-purpose, radiated-magnetic-susceptibility, magnetic-radiating-loop-standoff, magnetic-field-strength-requirement, magnetic-susceptibility-band-coverage, loop-axial-field-computation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Magnetic Susceptibility Purpose (space-systems/ecss/e2007-radiated-magnetic-susceptibility-purpose)

Use when the task is the aim of the radiated magnetic susceptibility test
in ECSS-E-ST-20-07C clause 5.4.10.1 -- deciding whether a proposed plan
actually produces the evidence the clause exists to obtain, namely that
the unit keeps working while a magnetic field radiated from a loop held
close to it washes over the enclosure and the harness.

## Domain quick reference

- The clause states an aim, not a limit, and the distinction matters. A
  plan can sweep beautifully, log a clean run and satisfy nobody, because
  the loop stood too far back or nothing was watching the unit while the
  field was on.
- The source is a loop held near the unit, not a distant antenna. Close
  to a loop the magnetic part of the field dominates and falls away with
  the cube of the distance rather than the first power, so the aim is
  about near-field coupling into enclosure seams, harness loops and
  magnetically sensitive parts, not about a far-field wave.
- Standoff is therefore the whole experiment. Because the field falls
  with the cube of the slant distance, a loop set back twice as far
  delivers roughly an eighth of the field, and a plan that leaves the
  standoff to the operator has not specified a level at all.
- The field a loop produces is computable from its turns, its current and
  its radius, so the level reaching the unit is a number that can be
  checked before the bench is built rather than discovered afterwards.
  A plan naming a required field but no loop able to produce it is not a
  plan.
- The band is low-frequency and it is wide -- several decades, not a
  narrow window. Coverage is therefore worked in the logarithmic domain:
  a plan starting a decade late has lost a large share of the aim's band
  even though the linear frequency it skipped looks negligible beside the
  top of the sweep.
- Something must watch the unit while the field is applied. Susceptibility
  is a change in the unit's own behaviour, and a plan with no performance
  criterion and no monitoring records only that the field was applied.
- A required field strength with no number behind it is not a
  requirement. The aim is evidence of tolerance to a stated level, so the
  level belongs in the plan rather than in the operator's judgement.

## Workflow

1. Validate each plan: identifier, radiating source, sweep start and stop,
   standoff, required field strength and the monitoring flag. Reject a
   non-positive start, a stop at or below the start, a negative standoff
   or a source that is not a loop.
2. Decide whether the sweep reaches both edges of the aim's band,
   comparing against the edges with a relative tolerance so a plan written
   to the exact edge frequency is not failed by the last place of a float.
3. Quantify the swept share of the aim band: clip the sweep to the band at
   both ends, take the decades of the overlap over the decades of the
   band, and return zero when a sweep sits wholly outside.
4. Compute the axial field the declared loop produces at the declared
   standoff, and convert it to a flux density when the requirement is
   written that way.
5. Grade the five aims -- loop source, standoff, band span, field level
   and performance monitoring -- and report the unserved ones in a fixed
   order so two reviews of one plan read alike.
6. Aggregate over a plan set: mean band coverage, the plans that miss the
   aim by name, and a set verdict that is positive only when every plan
   serves every aim.

## Pitfalls

- Reading a purpose clause as having nothing to check. It is the clause
  that decides whether the rest of the test was worth running, and a plan
  can fail it while passing every procedural requirement.
- Substituting a far-field antenna for the loop. The coupling the aim
  cares about is near-field and magnetic, and an antenna at a workable
  distance simply cannot produce it.
- Leaving the standoff to the operator. With a cube-law fall-off the
  difference between a loop touching the panel and one a hand's width away
  is most of the level the unit was supposed to see.
- Naming a required field strength that the declared loop cannot produce
  at the declared standoff, and finding out on the bench.
- Judging band coverage linearly. Over several decades a linear share is
  dominated by the top of the sweep, so a plan that skipped the bottom
  decade scores as nearly complete.
- Applying the field with nothing watching the unit, then recording the
  run as a pass because no one saw anything.

## Behavior contract (gate 3)

The plan validation, loop axial-field and flux-density computation, band
edge decision, log-domain coverage fraction, aim grading and plan-set
aggregation logic is exercised by the gate 3 contract test:
scripts/test_e2007_radiated_magnetic_susceptibility_purpose.py against
scripts/e2007_radiated_magnetic_susceptibility_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_magnetic_susceptibility_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

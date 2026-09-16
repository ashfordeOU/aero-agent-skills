---
name: e2008-sca-thermal-cycling-process
description: "Use when auditing the execution of a solar cell assembly thermal cycling test. Verify that a solar cell assembly thermal cycling run was executed to the cycle count and temperature extremes its own control drawing fixes, under ECSS-E-ST-20-08C clause 6.4.3.7.2: validate the drawing record is complete and its extremes ordered, build the hot and cold acceptance bands its tolerance gives, walk the recorded cycles and credit one only when both extremes were reached and each dwell held, separate an overstress excursion from a shortfall, and reconcile the credited cycles with the drawing. Trigger: ecss, e-st-20-08c-clause-6-4-3-7-2, sca-control-drawing-cycle-count, sca-cycling-temperature-extremes, sca-thermal-cycle-crediting, sca-cycling-dwell-audit, sca-cycling-overstress-excursion."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-thermal-cycling-process, sca-control-drawing-cycle-count, sca-cycling-temperature-extremes, sca-thermal-cycle-crediting, sca-cycling-dwell-audit, sca-cycling-overstress-excursion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Thermal Cycling Test Process (space-systems/ecss/e2008-sca-thermal-cycling-process)

Use when the task is the clause 6.4.3.7.2 test process of ECSS-E-ST-20-08C --
deciding from the chamber record whether a solar cell assembly was actually
cycled the number of times, and between the extremes, that the control drawing
of that assembly fixes.

## Domain quick reference

- The parameters belong to the assembly, not to the chamber. The cycle count
  and the hot and cold extremes are properties of the build, stated on its
  control drawing at a named issue. A run whose drawing and issue cannot be
  named has nothing to be judged against, so the record is refused before any
  cycle is read.
- An absent drawing field is not a default. A missing cycle count, dwell or
  tolerance is an incomplete record; filling it from a previous assembly is how
  one build gets tested to another build's profile.
- A cycle is credited, not counted. Reaching the hot extreme is not enough on
  its own: the run must reach both extremes inside the drawing tolerance and
  hold each of them for the dwell the drawing fixes. A chamber that turned
  around early delivered a temperature excursion, not a cycle.
- The band edges are part of the band. A peak sitting exactly on the tolerance
  limit, or a dwell exactly equal to the drawing value, is a success, so edge
  membership is inclusive and the comparison absorbs representation error
  rather than moving the limit.
- Going too far is not generosity. A peak beyond the tolerance band takes the
  sample outside the qualified envelope of its own drawing, which is an
  excursion in its own right and outranks any shortfall in the count.
- Overshooting the count does not repair a bad cycle. Extra cycles are recorded
  and reported, but they never turn an uncredited cycle into a credited one,
  and the shortfall is measured against the drawing rather than against the
  number of cycles the chamber logged.

## Workflow

1. Validate the control drawing record: a drawing number, an issue, a whole
   positive cycle count, a cold extreme below the hot extreme, a positive dwell
   and a non-negative tolerance. Refuse a tolerance so wide that the hot and
   cold bands overlap, since no peak could then be attributed to one of them.
2. Build the four acceptance edges the tolerance gives: the coldest a hot dwell
   may be, the hottest the sample may legally see, the warmest a cold dwell may
   be and the coldest the sample may legally see.
3. Walk the recorded cycles in order. For each, refuse an inverted record, then
   decide its disposition: an excursion outside either band first, then an
   extreme that was never reached, then a dwell that was not held, and only
   otherwise credit it.
4. Reconcile the run: credited cycles against the count the drawing fixes, with
   the shortfall reported as a number rather than absorbed into a total, and
   the excursions counted separately from the shortfall.
5. Close on one verdict carrying the drawing identity: outside the drawing
   extremes, short of the drawing cycles, or meeting the control drawing.

## Pitfalls

- Reading the chamber log's cycle counter as the delivered count. The counter
  increments on a turnaround, not on a completed profile, so a run that never
  reached the cold extreme still reports a full count.
- Treating an overshoot as margin. A peak past the tolerance band is a
  condition the assembly was never qualified to, and recording it as a
  comfortable pass hides an overstress that may itself have caused the damage
  found afterwards.
- Taking the extremes from the test specification when the drawing differs. The
  clause points at the assembly's own control drawing; a specification written
  for the array does not override the build record of the sample in the
  chamber.
- Crediting a cycle on temperature alone. Without the dwell, the joints never
  reach the extreme themselves -- only the thermocouple does -- and the fatigue
  the cycle was meant to impose is not delivered.
- Reporting one combined failure count. An excursion and a shortfall call for
  different actions, so folding them together loses the distinction between a
  run that did too little and a run that did too much.

## Behavior contract (gate 3)

The control drawing validation, acceptance band construction, per-cycle
disposition, run reconciliation and the run verdict are exercised by the gate 3
contract test: scripts/test_e2008_sca_thermal_cycling_process.py against
scripts/e2008_sca_thermal_cycling_process_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_sca_thermal_cycling_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

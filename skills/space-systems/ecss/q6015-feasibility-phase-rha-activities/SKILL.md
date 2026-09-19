---
name: q6015-feasibility-phase-rha-activities
description: "Derive the first radiation environment definition and the coarse part-level requirements a feasibility study owes. Use when the ECSS-Q-ST-60-15C clause 4.4.1 feasibility work has to be produced or graded: validate the candidate orbit, place it in an environment regime, name the trapped, solar-event and cosmic-ray components that regime actually contributes, accumulate the mission dose behind one declared reference shielding under a stated solar-activity assumption, apply the feasibility design factor to obtain the preliminary total-dose requirement, read the single-event threshold the regime demands, and list the study deliverables still absent. Trigger: ecss, q-st-60-15c-clause-4-4-1, feasibility-phase-radiation-activities, mission-radiation-environment-definition, orbit-radiation-regime, preliminary-total-dose-requirement, feasibility-design-factor, reference-shielding-assumption."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-feasibility-phase-rha-activities, q-st-60-15c-clause-4-4-1, feasibility-phase-radiation-activities, mission-radiation-environment-definition, orbit-radiation-regime, preliminary-total-dose-requirement, feasibility-design-factor, reference-shielding-assumption]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Feasibility Phase (space-systems/ecss/q6015-feasibility-phase-rha-activities)

Use when the task is the feasibility end of ECSS-Q-ST-60-15C clause 4.4.1 —
turning a candidate orbit and a mission duration into the first radiation
environment statement and the first set of part-level numbers, before any
hardware concept exists to hang them on.

## Domain quick reference

- The feasibility study does not size shielding; it establishes whether the
  mission is survivable at all with parts that can be bought. That makes the
  environment definition, not the design, the deliverable, and it has to be
  coarse, defensible and reproducible rather than accurate.
- The orbit decides the environment, and it decides it in kind as well as in
  magnitude. A low-inclination low orbit sees trapped protons and the residual
  cosmic-ray flux; a polar orbit adds the electron belt and solar particle
  events through the open field lines; a belt-crossing transfer sees every
  component; an escape trajectory loses the trapped components entirely and
  keeps the solar and cosmic ones. Naming the components is what stops a later
  analysis from quietly omitting one.
- Dose is accumulated behind one reference shielding thickness fixed for the
  whole trade. Two candidate orbits compared behind different assumed
  thicknesses are not comparable, so the thickness is recorded as a deliverable
  in its own right and carried into the next phase for revision.
- The solar-activity assumption is part of the answer. The same duration flown
  through solar minimum and through solar maximum gives different totals, so
  the assumption is stated, not left implicit in a single averaged number.
- The design factor applied at feasibility covers environment-model
  uncertainty, not part variability, and it is never below unity. Applying it
  to the accumulated dose gives the preliminary requirement a part has to meet.
- The single-event side of the first requirement set is a threshold, not a
  dose. It is set by how much geomagnetic shielding the regime offers against
  the heavy-ion tail, and it constrains part selection from the first day.

## Workflow

1. Validate the candidate orbit: positive altitudes, a perigee no higher than
   the apogee and an inclination inside the physical range. A malformed orbit
   stops the study rather than being clamped into a regime.
2. Place the orbit in an environment regime, testing the escape case, then the
   low-orbit case, then belt crossing, then the geostationary band, so an
   inclined geosynchronous orbit is not mistaken for a geostationary one.
3. Read the component list of that regime and carry it forward as the
   environment definition.
4. Accumulate the mission dose behind the reference shielding from the regime
   dose rate, the duration and the weighting of the declared solar-activity
   assumption.
5. Apply the feasibility design factor to obtain the preliminary total-dose
   requirement, refusing a factor below unity at the bound with a tolerance
   rather than silently raising it.
6. Read the single-event threshold of the regime, grade the deliverable set
   and return the findings, including the shielding-assumption revisit an
   electron-belt regime forces.

## Pitfalls

- Comparing candidate orbits on dose alone. Two orbits with the same total can
  demand different parts, because one of them carries a heavy-ion tail the
  other is shielded from by the geomagnetic field.
- Leaving the reference shielding implicit. A dose number without the thickness
  it sits behind cannot be reused, and the next phase has nothing to revise.
- Averaging the solar cycle away by default. The averaged case is a legitimate
  assumption but it is still an assumption, and a short mission that sits
  inside one half of the cycle is not represented by it.
- Reading a geosynchronous altitude as geostationary. The inclination is part
  of the test; an inclined geosynchronous orbit sweeps through a different
  environment and belongs in a different regime.
- Treating the feasibility design factor as the design margin. It absorbs
  environment-model uncertainty at a point where no part has been chosen; the
  part-level margin is a later, separate number.

## Behavior contract (gate 3)

The orbit validation, regime placement, component listing, dose accumulation,
design-factor application, single-event threshold lookup and the deliverable
grading are exercised by the gate 3 contract test:
scripts/test_q6015_feasibility_phase_rha_activities.py against
scripts/q6015_feasibility_phase_rha_activities_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6015_feasibility_phase_rha_activities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

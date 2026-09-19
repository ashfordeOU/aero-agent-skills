---
name: q7006-irradiation-facility-requirements
description: "Evaluate candidate irradiation facilities for a space-material degradation campaign under ECSS-Q-ST-70-06C and decide which one the exposure runs at: check agent coverage, energy-window coverage, target-plane uniformity, chamber pressure and the specimen temperature window, compute the acceleration factor the source would be driven at and the beam hours it implies, decide whether the particle and ultraviolet exposures are combined or run in a named sequential order, then rank the admissible candidates by acceleration. Use when choosing a source, writing a facility requirement or reviewing a bid. Trigger: ecss, q-st-70-06c, irradiation-facility-selection, radiation-test-acceleration-factor, combined-uv-particle-exposure, sequential-uv-particle-exposure, beam-uniformity-limit, irradiation-beam-hours."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-irradiation-facility-requirements, irradiation-facility-selection, radiation-test-acceleration-factor, combined-uv-particle-exposure, sequential-uv-particle-exposure, beam-uniformity-limit, irradiation-beam-hours]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Irradiation Facility Requirements (space-systems/ecss/q7006-irradiation-facility-requirements)

Use when the task is the facility clause of ECSS-Q-ST-70-06C: which source
the campaign is run at, whether it can deliver the agents together, and how
hard it may be driven before the run stops representing the mission.

## Domain quick reference

- The facility is chosen against the environment definition, not against
  availability. Agent coverage, energy window, uniformity, base pressure and
  specimen temperature are pass or fail requirements, and a candidate failing
  any of them is not a cheaper option but a different test.
- Acceleration is the central trade. The mission delivers its fluence over
  years and the facility over days, so every campaign is accelerated; beyond
  a limiting ratio the dose rate itself changes the chemistry, diffusion and
  annealing that carry the degradation, and the result no longer maps to the
  mission it was meant to represent.
- The faster source is not the better source. Two admissible candidates are
  ranked by how little acceleration they need, so the slowest facility that
  still fits the schedule is the most representative one.
- Uniformity is a property of the target plane, not of the beam axis. A
  spread across the coupon field appears in the results as material scatter,
  so a plus-or-minus limit about the mean bounds it, and it is measured over
  the area the coupons actually occupy.
- Combined exposure exists because the agents interact. Ultraviolet breaks
  bonds that particle damage then propagates, and a material whose response
  is synergistic degrades further under simultaneous exposure than under the
  same two doses delivered one after the other.
- When a facility cannot combine, the campaign still runs, but the order is
  named and the loss of synergy is recorded. A sequential result on a
  synergistic material is a lower bound on the degradation, and calling it
  the answer overstates the material.
- Vacuum and temperature are part of the source requirement. An exposure at
  the wrong pressure lets oxygen back into the degradation chemistry, and one
  at the wrong temperature anneals the damage as fast as it is made.

## Workflow

1. Validate each candidate: the agents it produces, its energy window, peak
   particle flux and ultraviolet intensity, target-plane uniformity, base
   pressure, specimen temperature window and whether it can run both agents
   at once. A combined claim with one agent is a contradiction.
2. Check agent coverage against the campaign requirement, and for a particle
   exposure check the energy window at both ends.
3. Compare target-plane uniformity with the plus-or-minus limit, absorbing
   representation error at the boundary with a named tolerance rather than by
   relaxing the limit.
4. Check the base pressure against the campaign maximum and the specimen
   temperature against the window the chamber can hold.
5. Compute the acceleration factor from peak flux over mission flux, and the
   beam hours needed for the target fluence; raise a finding when the factor
   passes the limit at which the mechanism changes.
6. Decide the exposure mode: single agent, combined, or a named sequential
   order, recording lost synergy as a finding when the campaign expected an
   interaction the facility cannot produce.
7. Rank the candidates — admissible first, then by lowest acceleration, then
   by name so the choice is reproducible — and return the selection record.

## Pitfalls

- Choosing the fastest available beam. A high acceleration factor buys
  schedule and spends representativeness; the campaign then measures a
  dose-rate artefact and calls it a mission degradation.
- Quoting uniformity on the beam axis. The figure that matters spans the
  coupon field, and an axis figure hides an edge coupon receiving a
  materially different fluence from a centre one.
- Running two agents sequentially on a synergistic material and reporting the
  result as the degradation. The sequential figure is a lower bound, and
  without the finding attached it will be read as the answer.
- Leaving the sequential order unnamed. The two orders do not give the same
  result on a material whose surface chemistry is altered by the first agent,
  so an unnamed order makes the campaign irreproducible.
- Accepting a base pressure close to the limit. Residual oxygen changes the
  degradation pathway outright, and the run then measures accelerated ageing
  in air rather than the space environment.
- Treating specimen temperature as a comfort parameter. It sets the annealing
  rate competing with the damage, so a chamber that cannot hold the specified
  temperature is producing a different material response, not a noisier one.

## Behavior contract (gate 3)

The facility validation, agent and energy coverage, uniformity, pressure and
temperature checks, acceleration and beam-hour computation, exposure-mode
decision and the candidate ranking are exercised by the gate 3 contract test:
scripts/test_q7006_irradiation_facility_requirements.py against
scripts/q7006_irradiation_facility_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7006_irradiation_facility_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

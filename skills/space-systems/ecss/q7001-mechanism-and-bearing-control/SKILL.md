---
name: q7001-mechanism-and-bearing-control
description: "Assess whether the particle population implied by a product cleanliness level threatens a mechanism, a bearing or a slip ring. Use when a moving assembly carries a cleanliness requirement and the argument has to run from the declared level to the largest particle expected over the real wetted area, then to the running-clearance margin, the contact-gap bridging outcome, the drag torque contamination adds to the actuator budget and the distance lubricant creeps toward a sensitive surface. Trigger: ecss, q-st-70-01c, product-cleanliness-level-population, bearing-running-clearance-particle, slip-ring-gap-bridging, mechanism-contamination-drag-torque, lubricant-creep-barrier-margin, largest-expected-particle-size."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-mechanism-and-bearing-control, product-cleanliness-level-population, bearing-running-clearance-particle, slip-ring-gap-bridging, mechanism-contamination-drag-torque, lubricant-creep-barrier-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Mechanisms, Bearings and Slip Rings (space-systems/ecss/q7001-mechanism-and-bearing-control)

Use when the task is the sensitive-hardware branch of ECSS-Q-ST-70-01C that
applies to moving assemblies: showing that a declared product cleanliness
level, over the real wetted area of a bearing, joint or slip ring, leaves
enough running clearance, enough torque margin and enough distance between
the lubricant and whatever it must not reach.

## Domain quick reference

- A cleanliness level is a particle population, not a single size. The count
  above a size follows a squared-logarithm law referred to a reference area,
  so at the level itself exactly one particle is expected over that reference
  area, and the count climbs steeply towards smaller sizes.
- The size that matters to a mechanism is therefore an area question. The
  largest particle statistically expected over a square centimetre of raceway
  is much smaller than over a tenth of a square metre at the same level, and
  quoting the level as though it were the worst-case particle mis-sizes the
  clearance argument in either direction.
- A particle against a gap has three outcomes, and they are grouped, not
  continuous: well below the gap it adds drag, around half the gap and up it
  is marginal, and at or above the gap it bridges. On a slip ring, bridging
  is an electrical event — a short, or contact noise — not a torque one.
- The population also acts collectively. Many particles far below the
  clearance still add drag, and that drag belongs inside the actuator torque
  margin rather than in a separate cleanliness statement nobody reconciles
  with it.
- Transport runs outward too. Lubricant creeping out of a bearing over a
  multi-year mission is itself a molecular source, so the barrier distance to
  the nearest sensitive surface is part of the same assessment as the
  particles coming in.

## Workflow

1. Validate the mechanism: cleanliness level, wetted area, running clearance,
   available and base resisting torque, mission duration, and optionally the
   slip-ring contact gap, lubricant creep rate and barrier distance.
2. Convert the level into the largest particle statistically expected once
   over the wetted area. Report an honest zero where not even a one-micrometre
   particle is expected, rather than inventing a floor.
3. Compare that particle with the running clearance and report the fraction of
   the clearance it leaves free, against the required clearance margin.
4. Group the same particle against the slip-ring or contact gap as clear,
   marginal or bridging, and treat anything but clear as a finding.
5. Convert the population above the drag-relevant size into an added resisting
   torque, add it to the base drag, and recompute the actuator torque margin
   against its requirement.
6. Project the lubricant creep over the mission duration and compare the reach
   with the barrier distance.
7. Report every margin with its limit, absorbing boundary representation error
   with a named tolerance rather than by relaxing a limit.

## Pitfalls

- Reading the cleanliness level as the largest particle present. The level is
  the size expected once over a reference area; over a smaller wetted area the
  expected worst particle is smaller, and over a larger one it is bigger.
- Checking only the biggest particle. A population of particles each a small
  fraction of the clearance adds drag that can consume the torque margin long
  before anything jams.
- Treating a slip ring like a bearing. Its failure mode is electrical, its
  relevant dimension is the contact gap rather than the running clearance, and
  a conductive particle that merely touches both sides is already a problem.
- Arguing cleanliness and torque in separate documents. Contamination drag
  only means something inside the actuator margin, and a level chosen without
  that reconciliation is a number with no acceptance criterion behind it.
- Forgetting outward transport. A bearing that meets every inbound particle
  requirement can still fail the mission by creeping lubricant onto an optic,
  and the barrier is sized by mission duration, not by the level.

## Behavior contract (gate 3)

The population law, area scaling, largest-expected-particle inversion,
clearance margin, gap grouping, contamination drag torque, actuator torque
margin, lubricant creep projection and every boundary comparison are exercised
by the gate 3 contract test:
scripts/test_q7001_mechanism_and_bearing_control.py against
scripts/q7001_mechanism_and_bearing_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_mechanism_and_bearing_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

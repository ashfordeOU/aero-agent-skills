---
name: e3311-cutters-explosively-actuated-valves
description: "Determine whether an explosive cable or pipe cutter and an explosively actuated valve meet ECSS-E-ST-33-11C clauses 4.12.5 and 4.12.6. Use when the task is sizing a severance or a flow change on cartridge energy: reducing a cable bundle, solid round or tube to the section the blade actually shears, building the cut energy from shear strength, blade travel and progressive engagement, grading it against delivered cartridge work, confirming the anvil supports the member, and for a valve sizing the ram against line pressure and seal friction and grading the post-actuation leak rate. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-cable-cutter-shear-energy, explosive-pipe-cutter-anvil-support, explosively-actuated-valve-ram-force, valve-seat-leak-rate-acceptance, cutter-blade-travel-margin."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-cutters-explosively-actuated-valves, explosive-cable-cutter-shear-energy, explosive-pipe-cutter-anvil-support, explosively-actuated-valve-ram-force, valve-seat-leak-rate-acceptance, cutter-blade-travel-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Cutters and Explosively Actuated Valves (space-systems/ecss/e3311-cutters-explosively-actuated-valves)

Use when the task is the cutter and valve requirement of
ECSS-E-ST-33-11C clauses 4.12.5 and 4.12.6 -- showing that a blade
driven by a cartridge fully severs the member it is installed on, and
that an explosively actuated valve drives its ram against line pressure
and seal friction and then holds the seat tight enough afterwards.

## Domain quick reference

- A cutter is graded on the section the blade actually has to shear,
  which is rarely the envelope of the member. A cable bundle shears
  strand by strand, so the load-bearing section is the sum of the
  strand areas, not the circle the outer jacket describes; a tube
  shears an annulus, not a disc.
- Severance is an energy problem, not a force problem. The blade
  travels while the section reduces, so the work is the shear force
  over the travel scaled by a progressive engagement factor, and a
  cutter sized on peak force alone can stall half way through.
- The anvil is part of the cut. Without a support opposite the blade
  the member bends out of the way instead of shearing, and the cutter
  can be perfectly energetic and still leave the cable intact, so the
  anvil is a pass condition in its own right.
- A valve is a force problem with a pressure term. The ram has to move
  against the line pressure acting on the seat area plus the friction
  of every seal it drags, and the line pressure is the worst-case
  pressure the system can present, not the nominal operating pressure.
- The direction of the action matters. A normally-open valve driven
  closed works against the flow it is stopping; a normally-closed
  valve driven open has to break a seal that has been seated for the
  whole mission, so the two carry different friction terms.
- Function is not the end of a valve assessment. A valve that actuates
  and then leaks past the new seat has changed the failure rather than
  removed it, so the post-actuation leak rate is graded against the
  allowance alongside the actuation margin.

## Workflow

1. Declare the device kind. A cutter case needs the member section and
   its dimensions; a valve case needs the action, the seat diameter and
   the line pressure. Reject a case that carries the wrong set.
2. For a cutter, reduce the member to its shear area: the full circle
   for a solid round, the summed strand areas for a bundle, the annulus
   for a tube. Reject a wall thickness that exceeds the tube radius.
3. Build the required cut energy from the shear strength, the shear
   area, the blade travel and the progressive engagement factor, and
   reduce the cartridge rating to delivered work through its conversion
   efficiency.
4. Grade the energy ratio against the cutter margin floor and record
   the anvil support state as a separate pass condition.
5. For a valve, size the required ram force from the line pressure
   across the seat area plus the seal friction for the declared action,
   and grade the delivered ram force against it as a ratio.
6. Grade the post-actuation leak rate against its allowance and combine
   the actuation and leakage verdicts, so a valve that moves but seeps
   does not read as acceptable.

## Pitfalls

- Taking the outer diameter of a cable bundle as its shear section.
  The jacket carries no load, and the strands leave voids, so the
  envelope area can overstate the real section by half and the cutter
  looks capable when it is not.
- Shearing a tube as if it were a bar. A thin-walled tube is an
  annulus, and treating it as a solid round asks the cartridge for an
  order of magnitude more energy than the cut needs, which is how a
  cutter ends up oversized enough to damage its neighbours.
- Sizing a cutter on peak shear force. The blade has to keep moving
  through a reducing section, so the quantity that decides severance is
  work over travel, and force alone says nothing about whether the
  blade stalls part way.
- Assuming the anvil. A cut with no support opposite the blade bends
  the member instead of shearing it, and no amount of extra cartridge
  energy fixes a missing reaction.
- Sizing a valve ram on nominal line pressure. The ram has to move
  against the highest pressure the system can present, and a relief
  setting or a transient above nominal is the case that stalls it.
- Comparing an energy or force ratio with its floor by bare
  arithmetic. Both are quotients of products, so a case that sits
  exactly on the floor can land a few units in the last place below it;
  the comparison absorbs that while the floor stays untouched.

## Behavior contract (gate 3)

The shear-area reduction by section, cut energy build-up, cartridge
conversion, anvil screen, valve ram sizing, leak-rate grading and the
combined verdict are exercised by the gate 3 contract test:
scripts/test_e3311_cutters_explosively_actuated_valves.py against
scripts/e3311_cutters_explosively_actuated_valves_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_cutters_explosively_actuated_valves.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: landing-gear-sizing
description: "Use when you must size the landing gear for an aircraft at the sizing level: split the maximum landing weight over the struts, compute the nose and main gear loads from the CG position and the wheelbase, size the shock absorber stroke from the sink speed and the landing load factor, and check the tire rating margin. Produces the static loads, the required stroke, and a gear sized or tire overloaded verdict that gate the landing gear configuration. Trigger: landing gear, strut load, wheelbase, nose gear, main gear, shock absorber stroke, sink speed, tire rating, landing load factor."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [landing-gear-sizing, landing-gear, strut-load, wheelbase, nose-gear, main-gear, shock-absorber-stroke, sink-speed, tire-rating, landing-load-factor]
  version: 0.1.0
  author: AeroSkills
---
# Landing Gear Sizing (vehicle-design/sizing/landing-gear-sizing)

Use when the task is sizing the landing gear at the conceptual level:
static loads over the struts, nose and main gear load share from the
CG and wheelbase, shock absorber stroke, and the tire rating margin.

## Domain quick reference

- Static loads split the maximum landing weight over the struts;
  with the CG a distance aft of the main gear, static equilibrium
  about the main gear gives nose load = W * cg_aft / wheelbase and
  main load = W - nose load.
- Shock absorber stroke follows from the energy balance
  0.5*m*v**2 = n*m*g*stroke, so stroke = v**2 / (2*n*g) with
  g = 9.80665 m/s**2.
- Tire rating margin is static load over tire rating; the rating
  covers the load when the margin is at most 1.0.
- FAR-25.723 / CS-25.723 shock absorption verification is a drop
  test; this module provides the sizing-level energy check only.

## Workflow

1. Collect the maximum landing weight, strut counts, CG position,
   wheelbase, sink speed, landing load factor, and tire rating.
2. Split the load with static_load_per_strut (even split) or
   main_gear_load_share (CG-based nose/main split).
3. Size the shock absorber with required_shock_stroke.
4. Check the tire with tire_rating_margin.
5. Close with landing_gear_verdict and gate on the verdict.

## Pitfalls

- Treating the sizing-level energy check as the certification drop
  test: FAR-25.723 / CS-25.723 verification is a drop test; this
  module is the sizing-level energy check only.
- A CG aft of the wheelbase: the nose gear would carry negative
  load; the logic raises ValueError.
- Non-positive weight, wheelbase, load factor, or tire rating: the
  logic raises ValueError.
- Reporting the even-split load when the CG is far aft of the main
  gear: use main_gear_load_share for the CG-based split.
- A tire margin above 1.0 means overload: the verdict is
  tire overloaded, not gear sized.

## Behavior contract (gate 3)

The sizing logic is exercised by the gate 3 contract test:
scripts/test_landing_gear_logic.py against
scripts/landing_gear_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_landing_gear_logic.py

## Compliance

- FAR-25 is US government work (public domain) and CS-25 is a free
  EASA download; standards referenced, not reproduced, per
  standards-map.yaml. Sizing methodology is common conceptual design
  practice.
- compliance: STANDARDS-REF, gated: false.

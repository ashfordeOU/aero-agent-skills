---
name: attitude-control-sizing
description: "Use when you must size the attitude control subsystem actuators for a spacecraft: compute the momentum wheel capacity for a commanded slew, check the detumble rate against the allowed rate, and verify the wheel momentum margin before the ADCS design review. Produces the slew momentum requirement, the detumble verdict, and the margin check that gates actuator selection. Trigger: attitude control, momentum wheel, adcs sizing, slew rate, detumble, spacecraft pointing."
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
  subdomain: adcs
  tags: [attitude-control, momentum-wheel, adcs-sizing, slew-rate, detumble, spacecraft-pointing]
  version: 0.1.0
  author: AeroSkills
---

# Spacecraft Attitude Control Sizing (space-systems/adcs/attitude-control-sizing)

Use when the task is spacecraft attitude control actuator sizing:
momentum wheel capacity for slews, detumble rate checks, and wheel
momentum margin.

## Domain quick reference

- Slew momentum: H = I * omega, where I is the spacecraft inertia
  and omega is the slew rate in radians per second.
- A momentum wheel must store the slew momentum with margin;
  typical project bands require 30 percent or more.
- Detumble: the post-separation angular rate must be reduced to
  within the allowed rate before pointing control.
- Attitude control design follows ECSS-E-ST-60 practice.

## Workflow

1. Collect spacecraft inertia and the commanded slew rate.
2. Compute the required wheel momentum with
   slew_momentum_from_deg.
3. Check the detumble rate with detumble_ok.
4. Verify the wheel margin with wheel_margin_ok.
5. Gate actuator selection on the margin verdict.

## Pitfalls

- Mixing degrees per second with radians per second.
- Sizing the wheel to the nominal slew with no margin.
- Skipping the detumble check after separation.

## Behavior contract (gate 3)

The slew momentum, detumble, and margin logic is exercised by the
gate 3 contract test: scripts/test_attitude_control_sizing.py
against scripts/attitude_control_sizing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_attitude_control_sizing.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-60 text is
  copyright ESA; the sizing here is common control physics,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

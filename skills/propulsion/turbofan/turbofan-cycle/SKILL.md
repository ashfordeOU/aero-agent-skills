---
name: turbofan-cycle
description: "Use when you must compute turbofan cycle parameters: calculate the bypass ratio from the fan and core mass flow, the propulsive efficiency from flight and jet velocity, the net thrust from total mass flow and the velocity change, and the specific thrust from net thrust per unit mass flow. Produces the bypass ratio, propulsive efficiency, net thrust, and specific thrust that gate the engine cycle assessment. Trigger: turbofan, bypass ratio, propulsive efficiency, specific thrust, fan mass flow, jet velocity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: turbofan
  tags: [turbofan, bypass-ratio, propulsive-efficiency, specific-thrust, fan-flow, mass-flow]
  version: 0.1.0
  author: AeroSkills
---

# Turbofan Cycle (propulsion/turbofan/turbofan-cycle)

Use when the task is turbofan cycle parameter evaluation: bypass
ratio, propulsive efficiency, net thrust, and specific thrust.

## Domain quick reference

Units are SI throughout:

- Mass flow m_dot in kg/s.
- Velocities in m/s.
- Thrust in N (newtons).
- Efficiency eta_p dimensionless.
- Bypass ratio B dimensionless.

The four parameters:

- Bypass ratio B = m_dot_fan / m_dot_core, the fan stream mass flow
  divided by the core stream mass flow.
- Propulsive efficiency eta_p = 2*v0/(v0 + vj), the fraction of jet
  kinetic energy converted to useful thrust power, from flight
  velocity v0 and jet velocity vj.
- Net thrust F = m_dot_total*(vj - v0), total mass flow times the
  jet-to-flight velocity change.
- Specific thrust F/m_dot_total, net thrust per unit total mass flow
  (m/s).
- Turbofan cycle practice sits in the FAR-33 engine design context.

## Workflow

1. Collect the fan and core mass flows; compute the bypass_ratio.
2. Collect the flight and jet velocities; compute the
   propulsive_efficiency.
3. Collect the total mass flow, jet velocity, and flight velocity;
   compute the thrust.
4. Divide net thrust by total mass flow with the specific_thrust.
5. Gate the engine cycle assessment on the four parameters.

## Pitfalls

- Unit confusion: mass flow in kg/s, velocities in m/s, thrust in N,
  efficiency dimensionless.
- Using total thrust instead of net thrust (the vj - v0 term).
- Treating bypass ratio as a mass fraction: B is a ratio of two mass
  flows, not a fraction of total flow.

## Behavior contract (gate 3)

The bypass, efficiency, thrust, and specific-thrust logic is exercised
by the gate 3 contract test: scripts/test_turbofan_cycle.py against
scripts/turbofan_cycle_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_turbofan_cycle.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain); the cycle parameters are common propulsion
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

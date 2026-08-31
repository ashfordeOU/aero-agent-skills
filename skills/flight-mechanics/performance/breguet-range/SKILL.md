---
name: breguet-range
description: "Use when you must estimate the cruise range of a transport aircraft with the Breguet range equation: combine speed, thrust specific fuel consumption, and lift to drag ratio with the initial and final masses to produce the cruise range in meters, the cruise time from range and speed, and the final mass from the fuel fraction. Produces the range, cruise time, and final mass that gate the mission performance assessment. Trigger: cruise range, TSFC, lift to drag, fuel fraction, cruise time."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [breguet-range, cruise-range, tsfc, lift-to-drag, fuel-fraction, cruise-time]
  version: 0.1.0
  author: AeroSkills
---

# Breguet Range (flight-mechanics/performance/breguet-range)

Use when the task is cruise range estimation from the Breguet
range equation: speed, TSFC, lift-to-drag, and mass ratio inputs,
plus cruise time and final mass from the fuel fraction.

## Domain quick reference

- The Breguet range equation computes still-air cruise range R
  from speed V, thrust specific fuel consumption TSFC, lift to
  drag ratio L/D, and the initial and final masses m0 and m1:
  R = (V / (TSFC * g0)) * (L/D) * ln(m0 / m1).
- Units: speed in m/s, TSFC in kg/(N s), masses in kg, g0 =
  9.80665 m/s^2, range in meters, cruise time in seconds.
- Cruise time is range divided by speed: t = R / V.
- Final mass from the fuel fraction f is m1 = m0 * (1 - f).
- Range analysis sits in the FAR-25 / CS-25 transport performance
  context for cruise fuel planning.

## Workflow

1. Collect speed, TSFC, L/D, and the initial and final masses.
2. Compute the range with breguet_range.
3. Compute cruise time with cruise_time.
4. Compute the final mass with final_mass.
5. Check the mass ratio and fuel fraction sanity before gating.

## Pitfalls

- Confusing TSFC units between kg/(N s) and 1/h; the equation
  needs TSFC per newton second, so g0 converts the thrust terms.
- Using the weight ratio upside down as the mass ratio; m1 >= m0
  makes ln(m0/m1) undefined or negative.
- Using a zero fuel fraction or an empty mass list; final_mass
  with fuel fraction 1.0 or above leaves no vehicle mass.

## Behavior contract (gate 3)

The range, time, and mass logic is exercised by the gate 3
contract test: scripts/test_breguet_range.py against
scripts/breguet_range_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_breguet_range.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  Breguet range equation is common range methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

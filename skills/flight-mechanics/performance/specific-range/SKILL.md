---
name: specific-range
description: "Use when you must compute the specific air range of an aircraft in cruise: divide the true airspeed by the fuel flow to produce the specific air range in meters per kilogram, derive the fuel flow from the thrust specific fuel consumption and the required thrust, estimate the instantaneous range from speed, thrust specific fuel consumption, weight, and lift to drag ratio, and convert a block distance into the fuel burn for the sector. Produces the specific air range, fuel flow, and fuel burn that gate the cruise fuel economy assessment. Trigger: specific air range, fuel flow, instantaneous range, meters per kilogram, sector fuel burn."
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
  tags: [specific-air-range, fuel-flow, instantaneous-range, meters-per-kilogram, cruise-fuel-economy, sector-fuel-burn]
  version: 0.1.0
  author: Aero Agent Skills
---

# Specific Range (flight-mechanics/performance/specific-range)

Use when the task is cruise fuel economy from the specific air
range: true airspeed and fuel flow inputs, plus the fuel flow
from thrust and thrust specific fuel consumption, the
instantaneous range from the aerodynamic efficiency, and the
sector fuel burn from a block distance.

## Domain quick reference

- The specific air range SAR is the distance flown per unit fuel
  mass: SAR = V / mdot, with true airspeed V in m/s and fuel flow
  mdot in kg/s, so SAR is in meters per kilogram.
- Fuel flow follows from the thrust specific fuel consumption
  and the required thrust: mdot = TSFC * T, with TSFC in kg/(N s)
  and thrust T in newtons.
- In steady cruise thrust equals drag, and the instantaneous
  range from aerodynamic inputs is SAR = V * (L/D) / (TSFC * W),
  with the weight W in newtons and L/D the lift to drag ratio.
- The fuel burn for a block distance d is m_fuel = d / SAR, in
  kilograms for d in meters.
- Cruise fuel economy sits in the FAR-25 / CS-25 transport
  performance context for cruise fuel planning.

## Workflow

1. Collect the true airspeed and the fuel flow for the cruise
   point.
2. Compute the specific air range with specific_air_range.
3. Derive the fuel flow from thrust and TSFC with
   fuel_flow_from_thrust.
4. Estimate the instantaneous range from speed, TSFC, weight,
   and lift to drag with instantaneous_range.
5. Convert the block distance into fuel burn with sector_fuel_burn.

## Pitfalls

- Mixing TSFC units between kg/(N s) and 1/h; the fuel flow
  relation needs TSFC per newton second.
- Using the aircraft mass in kilograms where the equations take
  the weight in newtons; multiply the mass by g0 = 9.80665.
- Dividing by a zero or negative fuel flow; specific_air_range
  raises ValueError on non-positive speed or fuel flow.
- Treating the specific air range as a total mission range; SAR
  is a point metric and must be integrated for a full leg.

## Behavior contract (gate 3)

The specific air range, fuel flow, and fuel burn logic is
exercised by the gate 3 contract test: scripts/test_specific_range.py
against scripts/specific_range_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_specific_range.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  specific air range method is common cruise fuel economy
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: payload-range-diagram
description: "Build the payload-range diagram for a conceptual transport aircraft: compute the range at the maximum payload point, the range at the maximum fuel point, the ferry range, and the payload available at the design range from operating empty weight, maximum payload, maximum takeoff weight, and fuel capacity using the Breguet range equation with a reserve fuel policy and fuel fraction. Use when the task is the payload versus range trade-off, max payload, max fuel, design range, ferry range, or reserve fuel sizing in conceptual aircraft design. Produces the diagram corner points that gate the payload-range trade assessment. Trigger: payload-range diagram, max payload, ferry range, design range, payload range trade, reserve fuel."
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
  subdomain: conceptual
  tags: [payload-range-diagram, payload-range-trade, max-payload, max-fuel, ferry-range, design-range, reserve-fuel, breguet-range, fuel-fraction]
  version: 0.1.0
  author: AeroSkills
---

# Payload-Range Diagram (vehicle-design/conceptual/payload-range-diagram)

Use when the task is the payload-range trade of a conceptual transport
aircraft: the corner points of the payload-range diagram, the payload
available at a design range, or the reserve fuel policy that shapes
the trade.

## Domain quick reference

- The payload-range diagram plots payload against range and is the
  standard picture of the payload-range trade. Three corner points
  define it. Point A carries the maximum structural payload at the
  range the fuel permits. Point B carries full fuel at the payload
  the takeoff weight permits. Point C is the ferry range: full fuel,
  zero payload.
- At point A the fuel is capped by the smaller of two limits: tank
  capacity and the MTOW allowance, MTOW - OEW - max payload. When the
  allowance binds, the aircraft cannot take off at max payload with
  full tanks; the fuel is weight-limited.
- At point B the payload is capped by MTOW - OEW - full fuel. When
  that allowance exceeds max payload, the aircraft carries max payload
  with full tanks and points A and B coincide in payload.
- The Breguet range equation turns fuel into range: R = K * ln(w0/w1),
  where the range factor K = (V / (TSFC * g0)) * L/D, w0 is the
  takeoff weight (OEW + payload + fuel), and w1 the landing weight
  (OEW + payload + reserve).
- A reserve fuel policy holds back a fraction of the loaded fuel that
  is never burned; the burnable fuel is (1 - reserve_fraction) *
  fuel. Landing weight therefore includes the reserve.
- The fuel fraction, fuel divided by takeoff weight, ties the diagram
  to weight sizing: the diagram's fuel at each point is the fuel
  fraction times the takeoff weight at that point.

## Workflow

1. Collect OEW, max payload, MTOW, fuel capacity, cruise speed, TSFC,
   and L/D; set the reserve fraction policy.
2. Compute the range factor K with range_factor.
3. Get corner A with max_payload_point: fuel capped by the MTOW
   allowance and tank capacity; check mtow_limited for which limit
   binds.
4. Get corner B with max_fuel_point: payload capped by MTOW at full
   fuel.
5. Get corner C with ferry_range: full fuel, zero payload.
6. For a design range, get the payload with payload_at_design_range;
   a range past the ferry range is infeasible.

## Pitfalls

- Letting the MTOW allowance go negative: MTOW below OEW + max payload
  cannot carry the payload, and full fuel above MTOW - OEW leaves no
  ferry range; the logic raises.
- Forgetting the reserve: burning the reserve fuel in the range
  calculation overstates every range on the diagram.
- Solving the design range on the wrong segment: inside the
  max-payload segment the payload is max_payload; past the max-fuel
  point the tanks are full, not the weight.
- Using TSFC in per-hour units with speed in m/s; the factor needs
  TSFC per newton second so g0 converts the thrust terms.
- Reporting corner B above corner A in payload; the trade line only
  descends once both limits bind.

## Behavior contract (gate 3)

The corner-point and design-range logic is exercised by the gate 3
contract test: scripts/test_payload_range.py against
scripts/payload_range_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_payload_range.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the payload-range
  trade and the Breguet range equation are common conceptual design
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

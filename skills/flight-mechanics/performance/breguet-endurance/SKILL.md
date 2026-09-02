---
name: breguet-endurance
description: "Use when you must compute the loiter endurance time of an aircraft with the Breguet endurance equation: combine the specific fuel consumption and the lift to drag ratio with the initial and final weights to produce the holding endurance in seconds, the final weight after an endurance segment, and the fuel burn for the loiter requirement. Produces the endurance time, final weight, and fuel burn that gate the holding performance check. Trigger: loiter endurance, endurance equation, holding time, specific fuel consumption, lift to drag ratio, fuel burn, maximum endurance."
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
  tags: [breguet-endurance, loiter, endurance, holding, specific-fuel-consumption, lift-to-drag, fuel-burn]
  version: 0.1.0
  author: Aero Agent Skills
---

# Breguet Endurance (flight-mechanics/performance/breguet-endurance)

Use when the task is loiter endurance (holding time) estimation from
the Breguet endurance equation: specific fuel consumption,
lift-to-drag, and the initial and final weights, plus the final
weight after an endurance segment and the fuel burn for the loiter
requirement.

## Domain quick reference

- The Breguet endurance equation computes loiter endurance (holding
  time) E from the specific fuel consumption sfc, the lift to drag
  ratio L/D, and the initial and final weights W0 and W1:
  E = (1 / sfc) * (L/D) * ln(W0 / W1).
- Units: sfc in 1/s (kg of fuel per newton of thrust per second for
  a jet, kg of fuel per watt of shaft power per second for a
  propeller), weights in newtons, endurance in seconds. All SI.
- Final weight after an endurance segment at constant L/D:
  W1 = W0 * exp(-E * sfc / (L/D)).
- Fuel burn for the segment: W0 - W1.
- Endurance is maximized at the maximum lift to drag ratio (L/D)max,
  the minimum-thrust condition; the loiter performance check
  compares the achievable endurance against the required holding
  time.
- Endurance analysis sits in the FAR-25 / CS-25 transport
  performance context for holding fuel planning.

## Workflow

1. Collect the specific fuel consumption, the lift to drag ratio,
   and the initial and final weights.
2. Compute the endurance with jet_endurance (or prop_endurance for
   a propeller aircraft).
3. Compute the final weight after the holding segment with
   final_weight_after_endurance.
4. Compute the fuel burn with endurance_fuel_burn.
5. Check the loiter requirement with loiter_check before gating.

## Pitfalls

- Confusing the SFC basis: jet endurance needs thrust specific fuel
  consumption in kg/(N s) (1/s), propeller endurance needs the
  consumption referred to shaft power in kg/(W s), also 1/s. Mixing
  the bases misstates the endurance.
- Using SFC in 1/h or lb/(lbf h); the equation needs per-second
  units, so convert before computing.
- Confusing endurance with range: endurance is a loiter (holding)
  time problem, E = (1/sfc) * (L/D) * ln(W0/W1), while the Breguet
  range equation adds speed and a gravity conversion for cruise
  distance. Do not apply the range equation to holding.
- Flipping the weight ratio: endurance requires burning fuel, so W1
  must stay below W0; W1 >= W0 makes ln(W0/W1) undefined or
  negative.
- Assuming endurance grows with speed: holding time depends on L/D
  and SFC only, not on speed; (L/D)max is the maximum-endurance
  condition.

## Behavior contract (gate 3)

The loiter endurance logic is exercised by the gate 3 contract test:
scripts/test_breguet_endurance_logic.py against
scripts/breguet_endurance_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_breguet_endurance_logic.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the Breguet
  endurance equation is common endurance methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

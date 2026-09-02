---
name: oei-climb-gradient
description: "Use when you must compute the one engine inoperative climb gradient for a transport aircraft certification analysis: derate the total thrust to the remaining engines, derive the steady climb gradient from the excess thrust over the drag at the aircraft weight, convert the gradient fraction into percent and into a rate of climb, and compare the available gradient against the FAR-25.121 takeoff second segment, approach climb, and landing climb minimum values for the engine count of the twin, trijet, or quad transport. Produces the OEI thrust, the climb gradient in percent, the rate of climb, and the clearance verdict that gate the engine out performance assessment. Trigger: one engine inoperative, OEI, second segment, engine out, approach climb, landing climb, climb gradient."
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
  tags: [oei-climb-gradient, one-engine-inoperative, second-segment, engine-out, approach-climb, landing-climb, climb-gradient, takeoff-climb]
  version: 0.1.0
  author: Aero Agent Skills
---

# One-Engine-Inoperative Climb Gradient (flight-mechanics/performance/oei-climb-gradient)

Use when the task is the engine out climb certification check for
a transport aircraft: OEI thrust, climb gradient, rate of climb,
and the FAR-25.121 minimum gradient clearance for the engine
count.

## Domain quick reference

- OEI thrust from the engine count:
  T_oei = T_total * (n - f) / n, with total thrust T_total in
  newtons (N), n engines installed, and f engines failed (default
  1). The remaining engines carry the derated thrust.
- Steady climb gradient from the excess thrust:
  gamma = (T_oei - D) / W, with drag D and weight W in newtons
  (N); the result is a dimensionless fraction and percent equals
  fraction * 100.
- Rate of climb from the gradient: ROC = gamma * V, with speed V
  in m/s and rate of climb in m/s. A climb exists only when
  T_oei is greater than D.
- FAR-25.121 minimum gradients in percent with one engine
  inoperative (CS-25.121 mirrors the same tables):
  - Second segment, takeoff configuration, gear up, at V2
    (25.121(b)): 2.4 for 2 engines, 2.7 for 3 engines, 3.0 for
    4 engines.
  - Approach climb, gear down, go-around power (25.121(d)):
    2.1 for 2 engines, 2.4 for 3 engines, 2.7 for 4 engines.
  - Landing climb, all engines, landing configuration
    (25.121(e)): 3.2 for every engine count.
- Engine out analysis sits in the FAR-25 / CS-25 transport
  performance certification context for takeoff and landing
  obstacle clearance checks.

## Workflow

1. Collect the total installed thrust, the engine count, the drag
   in the configuration, the aircraft weight, and the speed.
2. Compute the OEI thrust with oei_thrust.
3. Compute the gradient fraction with climb_gradient and convert
   it to percent with gradient_percent.
4. Convert the gradient to a rate of climb with rate_of_climb.
5. Compare the gradient against second_segment_minimum,
   approach_climb_minimum, or landing_climb_minimum for the
   engine count with meets_minimum before gating.
6. Check that the OEI thrust exceeds the drag; a negative
   gradient means the configuration cannot climb.

## Pitfalls

- Using all-engine thrust instead of the OEI thrust: the
  certification check uses the remaining engines only, so derate
  by (n - f) / n before computing the gradient.
- Mixing weight units: W must be the weight in newtons (mass *
  g0), not the mass in kg, or the gradient fraction comes out
  wrong.
- Applying the wrong minimum to the wrong segment: the second
  segment, approach, and landing climbs have different tables
  (25.121(b), (d), (e)), and the engine count selects the value
  within each table.
- Treating a negative gradient as an error: a negative result is
  a legitimate no-climb verdict, not a computation failure.
- Using an engine count outside 2 to 4: the FAR-25.121 minimum
  tables cover twin, trijet, and quad configurations only.

## Behavior contract (gate 3)

The OEI thrust, gradient, rate of climb, and minimum clearance
logic is exercised by the gate 3 contract test:
scripts/test_oei_climb_gradient.py against
scripts/oei_climb_gradient_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_oei_climb_gradient.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  one-engine-inoperative climb gradient method and the 25.121
  minimum values are common flight-mechanics methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

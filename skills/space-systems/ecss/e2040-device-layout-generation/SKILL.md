---
name: e2040-device-layout-generation
description: "Compute whether a device layout generation run satisfies ECSS-E-ST-20-40C 5.6.2 and can be released: derive core utilisation from the placed cell area, take the critical-path slack against the target period with an exact landing counted as met, turn the net list into a routing completion figure while still faulting every single unrouted net, and report the open geometry violations and the floorplan, layer stack, pin assignment, deviation and tool version documentation the record omits. Use when a place and route or full custom layout run has finished. Trigger: ecss, e-st-20-electrical-scope, device-layout-generation, layout-core-utilization, place-and-route-completion, layout-critical-path-slack, unrouted-net-detection, layout-documentation-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-layout-generation, device-layout-generation, layout-core-utilization, place-and-route-completion, layout-critical-path-slack, unrouted-net-detection, layout-documentation-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Layout — Generation (space-systems/ecss/e2040-device-layout-generation)

Use when the task is the implementation duty of ECSS-E-ST-20-40C 5.6.2 --
turning the closed detailed design into a physical layout or a placed and
routed database, and saying whether the run that produced it is complete
enough and documented enough to be released.

## Domain quick reference

- Utilisation is the placed cell area over the core area available to it.
  A run above its ceiling has nowhere to put the routing, and nowhere to
  put the engineering-change cells that always follow, so the ceiling is
  a design rule and not a preference.
- A utilisation figure landing exactly on its ceiling is inside it. The
  division is a computed ratio, so the comparison absorbs representation
  error rather than rejecting a floorplan that is exactly on target.
- Timing is the achieved critical-path period against the target period.
  The difference is the slack, and a run closing exactly on target has met
  it for the same reason.
- Routing completion is a fraction and rounds flattering. Forty-two
  thousand nets with three left open reads as 99.99 per cent complete, so
  any unrouted net at all is a finding in its own right rather than a
  rounding detail.
- Open geometry violations belong to generation, not to the later
  verification activity. They are what the run itself left behind.
- Documentation is part of producing the layout. Floorplan, layer stack,
  pin assignment, the rule deviations taken and the tool and version that
  produced the database -- an undocumented layout cannot be reproduced,
  and the tool version is the item most often omitted.
- Areas and periods are positive quantities. A zero or negative figure is
  an input defect, not a finding about the device.

## Workflow

1. Resolve the run record: implementation style, core and placed cell
   area, target and achieved period, the net counts, the open geometry
   violations and the documentation carried. Refuse unknown keys and any
   non-positive area or period.
2. Compute utilisation and compare it with the ceiling, absorbing a
   figure that lands exactly on it.
3. Compute the critical-path slack and say whether the target period is
   met, absorbing a run that closes exactly on the target.
4. Compute routing completion, then report any unrouted net separately so
   the flattering fraction cannot hide it.
5. Report the geometry violations the run left open.
6. Fold the documentation names and report every required item the record
   does not carry.
7. Declare the run releasable only when no finding stands.

## Pitfalls

- Reading routing completion as the routing verdict. The figure is above
  99 per cent long before the last net is connected, and the nets left
  open are exactly the ones the tool could not solve.
- Rejecting a floorplan whose utilisation lands exactly on the ceiling. A
  computed ratio can sit a unit in the last place either side of the
  bound, and a strict comparison fails a correct floorplan.
- Judging timing on the slack sign alone without treating an exact
  landing as met. A path closing precisely on target is met, not missed.
- Leaving the tool and version out of the record. The database is then
  unreproducible, and the omission is invisible because every other
  documentation item is present.
- Treating a negative area or period as a device finding. It is a defect
  in the run record and has to be refused rather than reported.

## Behavior contract (gate 3)

The style folding, utilisation arithmetic with exact ceiling landings,
slack and target-period comparison, routing completion, unrouted-net
detection, geometry-violation reporting and documentation completeness are
exercised by the gate 3 contract test:
scripts/test_e2040_device_layout_generation.py against
scripts/e2040_device_layout_generation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_layout_generation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

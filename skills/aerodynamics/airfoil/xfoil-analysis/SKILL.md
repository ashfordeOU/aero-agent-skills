---
name: xfoil-analysis
description: "Use when running XFOIL-style airfoil analysis for a given section: plan viscous and inviscid polar runs, validate lift and drag coefficient points against physical plausibility bands, and check NACA 0012 results at Reynolds number 6 million against the classic wind-tunnel anchor (lift coefficient about 0.82 at 10 degrees, zero-lift drag about 0.0079). Distinguishes inviscid runs (drag meaningless) from viscous runs and flags high-drag cases needing transition or mesh-density checks. Trigger: xfoil, airfoil, polar, lift coefficient, drag coefficient, naca, viscous analysis, reynolds number, transition."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: airfoil
  tags: [xfoil, airfoil, polar, lift-coefficient, drag-coefficient, naca, viscous-analysis, reynolds-number, transition]
  version: 0.1.0
  author: Aero Agent Skills
---

# XFOIL Airfoil Polar Analysis (aerodynamics/airfoil/xfoil-analysis)

Use when the task is airfoil section analysis with XFOIL-style
tools: polar run planning, polar-point plausibility checks, and
validation against classic airfoil data.

## Domain quick reference

- XFOIL is a panel-method airfoil analysis tool: inviscid
  (potential-flow) mode plus an integral boundary-layer coupling
  for viscous analysis with free or forced transition.
- Reynolds number scales the viscous solution; typical validation
  runs use Re = 6e6.
- Classic anchor (NACA Report 824, brief 05 item 7): NACA 0012 at
  Re = 6e6 gives cl about 0.82 at 10 degrees angle of attack and
  zero-lift drag coefficient cd0 about 0.0079.
- Inviscid XFOIL runs return drag values that are not meaningful;
  drag requires the viscous analysis.
- Polar plausibility bands: alpha in [-25, 30] degrees, cl in
  [-2.5, 2.5], cd in [0, 0.2].

## Workflow

1. Set the airfoil coordinates, Reynolds number, and Mach number
   for the polar.
2. Plan viscous runs (with transition) for drag; treat inviscid
   runs as lift-only scouting.
3. Run the polar and validate each point structurally with
   scripts/xfoil_analysis_logic.py.
4. Check NACA 0012 at Re = 6e6 results against the anchor bands
   (cl at 10 deg 0.77-0.87, cd0 0.0069-0.0089).
5. Use the drag hints (inviscid-run or high-drag) to decide on
   reruns with transition and finer mesh.

## Pitfalls

- Quoting inviscid drag as a real result.
- cd0 near zero reported without rerunning viscous analysis.
- High cd0 blamed on the airfoil before checking transition
  settings and mesh density.
- Validation against the anchor without matching Re = 6e6.

## Behavior contract (gate 3)

The polar plausibility, validation, and anchor-check logic is
exercised by the gate 3 contract test: scripts/test_xfoil_analysis.py
against scripts/xfoil_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_xfoil_analysis.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: prandtl-meyer
description: "Use when you must compute Prandtl-Meyer expansion relations for supersonic compressible flow: derive the expansion angle from the Mach number, find the downstream Mach number after the flow turns away from itself by a given angle, compute the total turning angle across the expansion fan, and the static pressure ratio across it. Produces the Prandtl-Meyer angle, the downstream Mach number, the turning angle, and the pressure ratio that gate supersonic airfoil, inlet, and nozzle analysis. Trigger: prandtl-meyer, expansion fan, mach number, supersonic flow, turning angle, compressible flow."
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
  subdomain: high-speed
  tags: [prandtl-meyer, expansion-fan, mach-number, supersonic, turning-angle, compressible-flow, isentropic-expansion]
  version: 0.1.0
  author: AeroSkills
---

# Prandtl-Meyer Expansion (aerodynamics/high-speed/prandtl-meyer)

Use when the task is the Prandtl-Meyer expansion of a supersonic
flow: the expansion angle from the Mach number, the downstream Mach
number after the flow turns away from itself, the total turning
angle of the fan, and the static pressure ratio across it.

## Domain quick reference

- Prandtl-Meyer function: nu(M) = sqrt((gamma+1)/(gamma-1)) *
  atan(sqrt((gamma-1)/(gamma+1) * (M^2 - 1))) - atan(sqrt(M^2 - 1)),
  in radians. nu(1.0) = 0.0 exactly: the expansion fan collapses to
  zero width at the sonic point and widens monotonically above it.
  The function is undefined for subsonic Mach numbers (M < 1 raises
  ValueError).
- Specific heat ratio: gamma (default 1.4 for air) must be > 1.
- Total turning angle of an expansion fan: delta = nu(M2) - nu(M1)
  in radians for a flow turning away from itself; positive for an
  expansion (M2 > M1), negative for a compression (not a
  Prandtl-Meyer fan).
- Downstream Mach after a turn: solve nu(M2) = nu(M1) + delta for
  M2, where delta is the turning angle in radians. Bisection on the
  bracket [1, 50] is deterministic and offline; a turning angle too
  large for the bracket raises ValueError.
- Static pressure ratio: p2/p1 = pr(M2) / pr(M1) with the isentropic
  relation pr(M) = (1 + (gamma-1)/2 * M^2)^(-gamma/(gamma-1));
  always < 1 for M2 > M1 (the expansion drops static pressure as it
  accelerates the flow).
- Textbook anchor (Anderson, Modern Compressible Flow, Table A.5):
  nu(2.0) = 26.380 deg at gamma = 1.4; a 10 deg turn from M = 2.0
  gives M2 = 2.385 and p2/p1 = 0.548.

## Workflow

1. Collect the upstream Mach number M1 (must be >= 1) and the
   specific heat ratio gamma (default 1.4).
2. Compute the expansion angle with prandtl_meyer_function; verify
   the flow is supersonic before trusting the fan.
3. For a turn away from itself, find the downstream Mach number with
   mach_after_expansion from the turning angle in degrees.
4. Compute the total turning angle between two Mach numbers with
   flow_turn_angle.
5. Compute the static pressure drop with expansion_pressure_ratio.
6. Get the downstream state at once with expansion_properties for
   the airfoil, inlet, or nozzle analysis.

## Pitfalls

- Feeding a subsonic Mach number: nu(M) is undefined below Mach 1;
  a subsonic input raises, never returns a negative angle.
- Using degrees where radians are expected: prandtl_meyer_function
  and flow_turn_angle return radians; mach_after_expansion takes the
  turning angle in degrees.
- Confusing expansion with compression: a flow turning toward itself
  is a shock, not a Prandtl-Meyer fan; flow_turn_angle is only the
  expansion (M2 > M1) case.
- Asking for an unreachable turning angle: nu(M) is bounded above,
  so a turn too large for the Mach bracket raises instead of
  converging to nonsense.
- Treating the fan as zero width above Mach 1: nu(M) = 0 only at
  M = 1; any M > 1 widens the fan strictly.

## Behavior contract (gate 3)

The Prandtl-Meyer function, turning angle, downstream Mach,
pressure ratio, and downstream state logic is exercised by the gate
3 contract test: scripts/test_prandtl_meyer.py against
scripts/prandtl_meyer_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_prandtl_meyer.py

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  compressible-flow tables (Anderson, Modern Compressible Flow,
  Table A.5 reproduces its values); the Prandtl-Meyer relations are
  standard compressible-flow methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

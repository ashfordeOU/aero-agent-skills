---
name: trim-analysis
description: "Use when you must analyze the stick fixed trim condition of a fixed-wing aircraft: compute the trim lift coefficient from the weight, density, true airspeed, and wing area, derive the elevator deflection required to trim from the pitching moment coefficients and the elevator effectiveness, find the trim speed for a given trim lift coefficient in level flight, and check whether the total pitching moment closes at zero for the trimmed verdict. Produces the trim lift coefficient, the elevator deflection, the trim speed, and the trimmed verdict that gate the pitch trim analysis. Trigger: elevator deflection, trim speed, trim lift coefficient, stick fixed, elevator effectiveness, pitching moment, trim analysis."
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
  subdomain: stability-control
  tags: [trim-analysis, elevator-deflection, trim-speed, trim-lift-coefficient, stick-fixed-trim, elevator-effectiveness, pitching-moment]
  version: 0.1.0
  author: Aero Agent Skills
---

# Trim Analysis (flight-mechanics/stability-control/trim-analysis)

Use when the task is the stick fixed pitch trim condition of an
aircraft: trim lift coefficient, elevator deflection to trim,
trim speed, and the trimmed verdict from the pitching moment
closure.

## Domain quick reference

- The trim lift coefficient in level flight follows from the
  weight, density, true airspeed, and wing area:
  CL_trim = 2W / (rho V^2 S).
- The pitching moment model is Cm = Cm0 + Cm_alpha * alpha +
  Cm_delta_e * de; the trimmed condition closes the moment at
  zero, Cm = 0.
- The angle of attack follows from the lift slope:
  alpha_trim = CL_trim / CL_alpha.
- The elevator deflection to trim is de_trim = -(Cm0 +
  Cm_alpha * alpha_trim) / Cm_delta_e.
- The trim speed for a given trim lift coefficient is
  V_trim = sqrt(2W / (rho S CL_trim)).
- Units: weight in newtons, density in kg/m^3, speed in m/s,
  wing area in m^2, angles in radians, moment slopes per radian.
  Trim requirements sit in the FAR-25 / CS-25 longitudinal
  stability context.

## Workflow

1. Collect the weight, density, true airspeed, and wing area.
2. Compute the trim lift coefficient with trim_lift_coefficient.
3. Derive the elevator deflection to trim with
   elevator_deflection_to_trim.
4. Find the trim speed with trim_speed.
5. Check the pitching moment closure with is_trimmed for the
   trimmed verdict.

## Pitfalls

- Using the aircraft mass in kilograms where the equations take
  the weight in newtons; multiply the mass by g0 = 9.80665.
- A zero elevator effectiveness; Cm_delta_e = 0 leaves no
  control authority and elevator_deflection_to_trim raises
  ValueError.
- A non-positive lift slope; CL_alpha must be greater than zero
  for the alpha_trim division.
- Ignoring the zero-lift angle of attack; the model here uses
  the simplified lift curve CL = CL_alpha * alpha.
- Applying a tight is_trimmed tolerance without stating it; pass
  an explicit tol for the verdict.

## Behavior contract (gate 3)

The trim analysis logic is exercised by the gate 3 contract test:
scripts/test_trim_analysis.py against scripts/trim_analysis_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_trim_analysis.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  trim condition method is common static stability methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

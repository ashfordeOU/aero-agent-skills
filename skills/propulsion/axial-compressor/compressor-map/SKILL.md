---
name: compressor-map
description: "Use when you must analyze an axial compressor operating map: identify map points, correct mass flow and rotor speed to standard-day conditions, compute surge margin and operating-line clearance, and judge whether an operating point sits on-map, approaching the surge line, or on the surge line. Produces surge margin percent, corrected flow in kg/s, corrected speed in rpm, and a surge-risk verdict in SI units that gate the engine acceleration and operability review in the FAR-33 engine design context. Trigger: compressor map, surge line, surge margin, operating line, corrected flow, corrected speed, choke line, map point, engine acceleration."
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
  subdomain: axial-compressor
  tags: [compressor-map, surge-line, surge-margin, operating-line, corrected-flow, corrected-speed, choke-line, map-point, engine-acceleration, axial-compressor]
  version: 0.1.0
  author: AeroSkills
---

# Compressor Map (propulsion/axial-compressor/compressor-map)

Use when the task is an axial compressor operating map: map axes,
surge and operating lines, corrected flow and speed, surge margin,
operating-line clearance, and the surge-risk verdict for a running
point.

## Domain quick reference

- Map axes: total pressure ratio (dimensionless) on the vertical
  axis, corrected mass flow (kg/s) on the horizontal axis. Each
  iso-speed line is a curve in this plane.
- Stable region boundaries: the surge line on the left (locus of
  peak-pressure-ratio points, one per speed) and the choke line on
  the right (blocked flow, flow independent of pressure ratio).
- The operating line is the design locus of running points across
  speeds; it sits below the surge line with a clearance.
- Standard-day correction, T_ref = 288.15 K, P_ref = 101325 Pa:
  theta = Tt/T_ref, delta = Pt/P_ref, both dimensionless.
- Corrected mass flow m_corr = m_actual*sqrt(theta)/delta in kg/s;
  corrected rotor speed N_corr = N_actual/sqrt(theta) in rpm.
- Flow-basis surge margin (percent), at the same corrected speed:
  SM = (q_operating - q_surge)/q_operating*100. The surge point is
  at lower flow than the running point, so positive SM is the safe
  side.
- Operating-line clearance (percent), at the same corrected flow:
  CL = (pr_surge - pr_operating)/pr_operating*100. Positive means
  the operating line is below the surge line.
- Surge-risk verdict at a corrected flow: "on-map" when the
  fractional gap to the surge line exceeds the threshold (default
  5%), "approaching-surge" inside it, "on-surge-line" at or above
  surge pressure ratio.
- Acceleration path: a transient moves the point up a speed line
  toward higher pressure ratio and speed; the transient margin is
  smaller than the steady-state margin because the point must stay
  below the surge line throughout.
- Units: flows in kg/s, speeds in rpm, temperatures in K, pressures
  in Pa, ratios and verdicts dimensionless.

## Workflow

1. Identify the map point: corrected_speed and corrected_flow from
   the measured speed and mass flow with the theta/delta
   corrections.
2. Read the surge-line pressure ratio and flow at that point from
   the map (surge_pr, q_surge).
3. Compute the flow-basis margin with surge_margin_flow.
4. Compute the pressure-ratio clearance with
   operating_line_clearance.
5. Classify the point with map_verdict.
6. Assess the acceleration path: the transient must keep the point
   below the surge line; a verdict of approaching-surge or
   on-surge-line rejects or trims the schedule.
7. Report margin, clearance, and verdict; gate the operability
   review on the clearance staying positive.

## Pitfalls

- Mixing corrected and raw quantities: the map is drawn in
  corrected flow and corrected speed, so raw values must be
  theta/delta corrected before any point lookup.
- Confusing the two margins: flow-basis margin is read at constant
  corrected speed, pressure-ratio clearance at constant corrected
  flow; mixing the reading directions mixes the numbers.
- Forgetting that theta and delta are dimensionless ratios, not
  temperatures or pressures: pass Tt/288.15 and Pt/101325, not Tt
  and Pt themselves.
- Zero or negative inputs (flow, speed, theta, delta, surge
  pressure ratio at or below unity): the functions raise ValueError
  rather than divide by zero; do not catch and continue.
- Treating the default 5% threshold as a requirement: it is a
  default; the engine program sets the transient surge margin
  requirement.
- A negative margin or clearance is not a rounding error: it means
  the operating point is on the unstable side of the surge line.

## Behavior contract (gate 3)

The map logic is exercised by the gate 3 contract test:
scripts/test_compressor_map.py against scripts/compressor_map_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_compressor_map.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not map
  analysis methods; the map conventions and correction relations
  are common turbomachinery methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

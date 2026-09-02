---
name: tail-sizing
description: "Use when you must size the empennage with tail volume coefficients: compute the horizontal and vertical tail volume coefficients from the tail areas, the tail arms, and the wing reference area, solve for the required tail area for a target volume coefficient, and judge the result against the typical transport ranges. Covers V_h = S_h * L_h / (S_w * cbar) and V_v = S_v * L_v / (S_w * b), with the tail arm measured from the wing aerodynamic center to the tail quarter chord. Trigger: tail volume coefficient, tail sizing, horizontal tail, vertical tail, empennage, tail arm, stabilizer sizing."
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
  subdomain: sizing
  tags: [tail-sizing, horizontal-tail, vertical-tail, tail-volume-coefficient, empennage, tail-arm, stabilizer-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# Tail Sizing (vehicle-design/sizing/tail-sizing)

Use when the task is empennage sizing from tail volume coefficients:
computing the horizontal and vertical tail volume coefficients from
the tail areas, tail arms, and wing reference quantities, solving for
the required tail area for a target volume coefficient, and checking
the result against typical conceptual sizing ranges.

## Domain quick reference

- Horizontal tail volume coefficient: V_h = S_h * L_h / (S_w * cbar),
  with S_h the horizontal tail area (m^2), L_h the horizontal tail arm
  (m, wing aerodynamic center to tail quarter chord), S_w the wing
  reference area (m^2), and cbar the wing mean aerodynamic chord (m).
- Vertical tail volume coefficient: V_v = S_v * L_v / (S_w * b), with
  S_v the vertical tail area (m^2), L_v the vertical tail arm (m), and
  b the wing span (m).
- Required tail area for a target coefficient: S_h = V_h * S_w * cbar
  / L_h, and S_v = V_v * S_w * b / L_v; a longer tail arm reduces the
  required area, a larger wing reference area increases it.
- Typical ranges: V_h from 0.5 to 1.0 (transport category about 0.7),
  V_v from 0.04 to 0.07 (transport category about 0.06). Both are
  unitless; all lengths and areas are SI (m and m^2).
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context for
  transport-category stability and control (tail authority, control
  surface sizing); the volume coefficient method itself is common
  conceptual sizing practice.

## Workflow

1. Set the wing reference area S_w and the reference lengths: mean
   aerodynamic chord cbar for the horizontal tail, span b for the
   vertical tail.
2. Set the tail arms L_h and L_v from the layout: wing aerodynamic
   center to horizontal tail quarter chord, and to vertical tail
   quarter chord.
3. Compute V_h and V_v from the candidate tail areas with
   tail_volume_coefficient.
4. Solve for the required tail area for the target volume coefficient
   with tail_area_required; this closes the empennage sizing once the
   tail arms and wing reference quantities are fixed.
5. Judge the pair against the typical ranges with
   volume_coefficient_verdict; rework the layout (tail arm, tail
   area) until h_ok and v_ok are both True.

## Pitfalls

- Swapping the reference lengths: cbar for the horizontal tail, b for
  the vertical tail; exchanging them gives a wrong coefficient with
  no error signal.
- Measuring the tail arm from the wrong point: the arm runs from the
  wing aerodynamic center to the tail quarter chord, not from the
  nose or the wing leading edge.
- Using mixed units: keep areas in m^2 and arms in m; a centimeter
  arm with a meter area silently distorts the coefficient.
- Treating the typical ranges as hard limits: 0.5-1.0 and 0.04-0.07
  are sizing guidance, not a certification requirement; the verdict
  flags outliers for layout rework.
- Passing a zero or negative tail arm to tail_area_required; the
  module raises ValueError instead of dividing by zero.
- Sizing the vertical tail with the horizontal reference length; the
  vertical tail volume coefficient uses the span, not the chord.

## Behavior contract (gate 3)

The tail volume coefficient relations, the required-area inverse, and
the typical-range verdict are exercised by the gate 3 contract test:
scripts/test_tail_sizing.py against scripts/tail_sizing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_tail_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the tail volume
  coefficient equations are common conceptual sizing methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

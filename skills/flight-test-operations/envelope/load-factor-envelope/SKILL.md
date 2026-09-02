---
name: load-factor-envelope
description: "Use when you must build the flight test load factor envelope (V-n diagram): compute the stall speed boundary from the wing loading and the maximum lift coefficient, derive the corner point speed at the positive limit load factor, compute the discrete gust line increment in the FAR 25.341 form, and judge the envelope against the placard speed and the transport positive and negative limit load factors. Produces the stall speed boundary, the corner point speed, the gust load factor increment, and the envelope verdict that gate the flight test program. Trigger: V-n diagram, load factor envelope, gust line, corner point, placard speed."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [v-n-diagram, load-factor-envelope, gust-line, corner-point, placard-speed, gust-load-factor, stall-speed-boundary, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Load Factor Envelope (flight-test-operations/envelope/load-factor-envelope)

Use when the task is the load factor envelope (V-n diagram) for a
flight test: stall speed boundary, corner point, gust line, and
placard speed cap.

## Domain quick reference

- Stall speed boundary: V_s = sqrt(2 * n * W/S / (rho * CL_max)),
  with wing loading W/S in Pa (N/m^2), load factor n dimensionless,
  CL_max dimensionless, and air density rho in kg/m^3. Result in m/s
  EAS. Example: W/S = 6000 Pa, CL_max = 1.8, rho = 1.225 kg/m^3 at
  sea level, n = 1 gives about 73.8 m/s.
- Corner point (maneuvering speed VA): the stall boundary evaluated
  at the positive limit load factor n_lim, V_A = sqrt(2 * n_lim * W/S
  / (rho * CL_max)). Example: the 6000 Pa wing above with n_lim = 2.5
  gives about 116.6 m/s.
- Discrete gust line (FAR 25.341 form, paraphrased): the gust load
  factor increment is delta_n = k_g * rho * U_de * V_eas * a / (2 *
  W/S) in SI units, with k_g the gust alleviation factor (typical
  0.6 to 0.9), U_de the reference gust velocity in m/s EAS, V_eas in
  m/s EAS, and a the lift curve slope per radian. The certification
  formula in mixed units is delta_n = k_g * U_de * V_eas * a / (498 *
  W/S) with U_de in ft/s EAS, V_eas in knots EAS, and W/S in lb/ft^2;
  498 is the sea level density constant. The reference gust velocity
  decreases with altitude (about 66 ft/s EAS at sea level to about
  38 ft/s EAS at high altitude).
- Placard speed cap: the corner point must stay below the placard
  speeds (VNE never exceed, VMO maximum operating limit), and the
  gust line must stay below the positive limit load factor.
- Transport limit maneuvering load factors (FAR 25.337 / CS-25.337
  context): +2.5 positive and -1.0 negative for transport category
  aeroplanes; the envelope is drawn between these limits.

## Workflow

1. Collect the wing loading W/S (Pa), the maximum lift coefficient
   CL_max, the air density rho (kg/m^3), and the limit load factors.
2. Compute the stall speed boundary at n = 1 with
   stall_speed_boundary(wing_loading, cl_max, 1.0, rho).
3. Derive the corner point with corner_speed(wing_loading, cl_max,
   limit_load_factor, rho); verify it stays below the placard speed.
4. Compute the gust line increment with
   gust_load_factor_increment (FAR 25.341 mixed-unit form) or
   gust_load_factor_increment_si (SI form).
5. Judge the whole envelope with envelope_verdict(corner_speed, vne,
   gust_increment, positive_limit, negative_limit) and gate the
   flight test program on the verdict.

## Pitfalls

- Mixing the units of the two gust forms: gust_load_factor_increment
  takes ft/s EAS, knots EAS, and lb/ft^2 exactly as in the
  certification formula; feeding SI values into it silently scales
  the increment. Use gust_load_factor_increment_si for SI input.
- Using the wrong density: the corner point moves with altitude; a
  sea level density applied to a high altitude test point
  under-predicts both the stall speed and the corner point.
- Treating the corner point as fixed: VA is a function of W/S,
  CL_max, and rho, so it changes with weight, configuration, and
  altitude; the placard check must be repeated per condition.
- Forgetting the negative limit: the -1.0 negative limit bounds the
  inverted side of the envelope; the verdict flags any limit set that
  is not the transport +2.5 / -1.0 pair.
- Accepting a gust line above the maneuver line: at the design
  speed the 1 + delta_n gust point must stay below the positive
  limit load factor, otherwise the gust case sizes the structure.
- Passing zero or negative inputs; the module raises ValueError
  instead of returning a nonsense speed or increment.

## Behavior contract (gate 3)

The stall speed boundary, corner point, gust increment, and envelope
verdict logic is exercised by the gate 3 contract test:
scripts/test_load_factor_envelope.py against
scripts/load_factor_envelope.py (stdlib unittest, offline). Run:
python3 scripts/test_load_factor_envelope.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the V-n diagram
  relations and the gust increment form are common flight test
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

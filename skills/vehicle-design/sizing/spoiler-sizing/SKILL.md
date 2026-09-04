---
name: spoiler-sizing
description: "Use when you must size the flight and ground spoiler panels of a transport aircraft: split roll authority between the primary roll channel and the roll spoilers from the roll rate and damping derivative, size flight spoiler panel area and deflection for the roll assist share, size the ground spoiler lift dumper area from the touchdown lift dump, estimate the speed brake and lift dump drag increments, compute the spoiler hinge moment for the actuator, and check the limits. Produces spoiler areas, deflections, drag increments, hinge moments, and a sized verdict. Trigger: spoiler sizing, flight spoiler, ground spoiler, lift dump, speed brake, roll spoiler, roll assist share, spoiler panel area, lift dumper, spoiler deflection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [spoiler-sizing, flight-spoiler, ground-spoiler, lift-dump, speed-brake, roll-spoiler, roll-assist-share, spoiler-panel-area, spoiler-deflection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Spoiler Sizing (vehicle-design/sizing/spoiler-sizing)

Use when the task is sizing the spoiler panels of a transport
aircraft: the flight spoilers that assist the primary roll channel,
the ground spoilers (lift dumpers) that unload the wing on
touchdown, and the same panels used as a speed brake. This leaf
implements the roll share split (roll spoilers carry the share of
the roll authority not assigned to the primary channel), the flight
spoiler area and deflection sizing from the roll damping
derivative, the ground spoiler belt area from the touchdown lift
dump, the speed brake and lift dump drag increments, the hinge
moment for the actuator, and the deflection and geometry limit
checks, in pure Python, stdlib only. It pairs with
vehicle-design/sizing/control-surface-sizing, whose primary roll
surfaces carry the rest of the roll authority,
vehicle-design/sizing/wing-planform-sizing for the wing geometry
inputs, and vehicle-design/conceptual/constraint-analysis for the
field performance margins that the lift dump and speed brake
support.

## Domain quick reference

- Roll share split: the total roll authority coefficient at the
  design roll rate follows the control-surface-sizing damping
  balance, C_l_req = -p_req * b * C_l_p / (2 * V); the primary roll
  channel carries the share f_ail (transport typical 0.6 to 0.7)
  and the roll spoilers carry f_spoil = 1 - f_ail.
- Flight spoiler roll capability: C_l_spoil = cl_delta_spoil *
  (A / S) * delta_eff * (y_arm / b), with cl_delta_spoil the panel
  lift loss per unit area ratio (negative, about -0.3 to -0.5 per
  rad per unit area ratio), A the total flight spoiler area of both
  wings, delta_eff the effective deflection (linear up to 45 deg,
  saturated beyond) in rad, and y_arm the spanwise centroid of the
  outboard panels.
- Flight spoiler area law: A = C_l_spoil_req * S * b /
  (abs(cl_delta_spoil) * delta_eff * y_arm), with C_l_spoil_req =
  f_spoil * C_l_req the rolling moment coefficient share. The
  deflection term is explicit at the reference deflection (45 deg);
  the linear band model is conservative because separated flow at
  high deflection destroys the local lift harder than the linear
  slope.
- Ground spoiler (lift dumper): the dumper must destroy f_dump of
  the lift at the touchdown lift coefficient, dCL_dump =
  -f_dump * C_L_td, and the deployment lift loss is dCL_dump =
  -(A_dump / S) * k_dump * sin(delta), with k_dump in (0, 1.5] and
  A_dump the effective dump belt area, the spanwise run of the dump
  panels times the local wing chord they unload.
- Speed brake and lift dump drag: dCD = (A_deployed / S) *
  cd_spoil * sin(delta) * span_factor, summed over the deployed
  panels, cd_spoil about 1.2 referenced to the panel planform area.
- Hinge moment for the actuator: H = q * A_panel * c_bar_panel *
  (c_h0 + c_h_alpha * alpha + c_h_delta * delta) with
  module-typical hinge moment coefficients (reference-only).
- Limits: deflection 0 < delta <= delta_max (module constant 60
  deg), panel aspect ratio within 1.5 to 4, panel span fraction of
  the wing semi-span within 0.2 to 0.5.
- Units are SI throughout: m^2, m, m/s, Pa, N m, rad (deg where
  noted), derivatives per radian.
- FAR/CS 25 roll capability and landing performance requirements
  frame the sizing context; the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the wing and flight point: reference area S, span b,
   reference speed V, dynamic pressure q, and the design roll rate
   p_req at the maneuver point.
2. Split the roll authority: choose f_aileron_share and get the
   roll spoiler share with roll_spoiler_share; the total
   coefficient follows from roll_coefficient_required.
3. Compute the spoiler share coefficient and its rolling moment
   with spoiler_share_coefficient and roll_moment_share.
4. Size the flight spoiler panels with flight_spoiler_area, then
   divide by the number of outboard panels for the per-panel area.
5. Get the required deflection with flight_spoiler_deflection from
   the lift increment the outboard set must produce.
6. Size the ground spoiler belt with ground_spoiler_area from the
   dump fraction f_dump and the touchdown lift coefficient.
7. Estimate the drag increments with speed_brake_drag_increment
   (flight panels deployed) and lift_dump_drag_increment (dump
   panel planform on the ground).
8. Size the actuator with hinge_moment per panel at the operating
   deflection and angle of attack.
9. Check the deflection and geometry with deflection_limits_check
   and geometry_limits_check, or run the whole loop with
   spoiler_verdict for the sized verdict dict.
10. Confirm the deterministic checks with the contract test
    scripts/test_spoiler_sizing.py.

## Worked example

Transport-class example: S = 122 m^2, b = 34 m, design roll rate
p_req = 0.5 rad/s at V = 85 m/s, q = 4425.31 Pa (sea level),
f_aileron_share = 0.65, cl_delta_spoil = -0.4, y_arm = 13.5 m,
C_l_p = -0.45, dump 60 percent of the touchdown lift coefficient
C_L_td = 1.0 with k_dump = 1.5 at 60 deg.

- Roll share: C_l_req = -0.5 * 34 * (-0.45) / (2 * 85) = 0.045;
  f_spoil = 0.35, so the roll spoiler share is
  C_l_spoil_req = 0.01575 and the share moment is 0.01575 * q * S *
  b = 289110 N m.
- Flight spoiler area: A = 0.01575 * 122 * 34 / (0.4 * 0.7854 *
  13.5) = 15.404 m^2 total, 3.851 m^2 per panel for 4 outboard
  panels (2 per wing). The required lift increment 0.01575 * 34 /
  13.5 = 0.0397 needs a deflection of 45.0 deg, at the top of the
  linear band and inside the 60 deg travel.
- Ground spoiler: A_dump = 0.6 * 1.0 * 122 / (1.5 * sin(60 deg)) =
  56.35 m^2 of dump belt, a run of about 8.05 m per wing at the
  3.5 m local chord, 0.474 of the semi-span.
- Speed brake drag at 45 deg: dCD = (15.404 / 122) * 1.2 * sin(45
  deg) * 0.9 = 0.09642.
- Lift dump drag at 60 deg with the dump planform 0.25 * 56.35 =
  14.09 m^2: dCD = (14.09 / 122) * 1.2 * sin(60 deg) * 0.9 =
  0.108.
- Hinge moment per flight panel at alpha = 4 deg, delta = 45 deg:
  bracket 0.02 + 0.03 * 0.0698 + 0.35 * 0.7854 = 0.29698, so H =
  4425.31 * 3.851 * 1.0 * 0.29698 = 5061 N m per panel.
- Limits: deflection 45 deg within 60 deg travel (margin 15 deg);
  panel aspect ratio 3.851 within the 1.5 to 4 band; panel span
  fraction 0.227 per panel within the 0.2 to 0.5 band; dump run
  fraction 0.474 within band. The verdict reports the sizing as
  within typical limits.


## Pitfalls

- Giving the spoilers the full roll authority: the roll spoilers
  carry only the share not assigned to the primary channel
  (f_spoil = 1 - f_ail = 0.35 in the worked example); sizing the
  flight spoilers for the total C_l_req over-sizes the panels and
  the actuators.
- Sizing deflection beyond the linear band: the deflection law is
  linear up to 45 deg and saturated beyond, and the linear band
  model is conservative because separated flow at high deflection
  destroys lift harder than the linear slope - do not extrapolate
  the area law past the reference deflection.
- Forgetting the dump belt is a spanwise area: the ground spoiler
  area A_dump is the effective dump belt (panel run times local
  chord) that destroys the f_dump share of the touchdown lift;
  sizing it as a single panel area underestimates the unload.
- Confusing the flight and ground drag increments: the speed brake
  increment uses the flight panel planform deployed at the flight
  deflection while the lift dump increment uses the dump planform at
  the ground deflection; both share one formula but with different
  areas and angles.
- Checking the deflection but not the geometry: the limits include
  panel aspect ratio in 1.5 to 4 and panel span fraction in 0.2 to
  0.5 of the semi-span, so a panel that fits the deflection band can
  still fail the geometry check.
- Feeding invalid shares or slopes: f_ail outside (0, 1), negative
  cl_delta_spoil, deflections outside (0, 90], k_dump outside
  (0, 1.5] and non-positive q, area or speed all raise ValueError.
## Verification

- Confirm roll_spoiler_share(0.65) returns 0.35 and the damping
  balance roll_coefficient_required(0.5, 85, 34, -0.45) returns
  0.045.
- Confirm flight_spoiler_area with the share moment returns 15.404
  m^2 and that the capability relation recovers the 0.01575 share
  coefficient.
- Confirm ground_spoiler_area(0.6, 1.0, 122, 1.5, 60) returns
  56.35 m^2 and that the deployment relation reproduces the 0.6
  lift dump.
- Confirm speed_brake_drag_increment returns 0.09642 at 45 deg and
  lift_dump_drag_increment returns 0.108 at 60 deg, and that both
  functions share one formula.
- Confirm hinge_moment returns 5061 N m per panel at the example
  operating point and scales linearly with q and area.
- Confirm deflection_limits_check and geometry_limits_check pass
  the worked example bands and flag out-of-band cases.
- Confirm spoiler_verdict returns the areas, deflections, drag
  increments, hinge moments, and limits verdict of the example.
- Confirm ValueError rejection of non-positive q, area, speed,
  negative cl_delta_spoil, f_ail outside (0, 1), deflections
  outside (0, 90], and k_dump outside (0, 1.5].
- Run the contract test offline: python3
  scripts/test_spoiler_sizing.py (28 tests, deterministic).

## Related leaves

- vehicle-design/sizing/control-surface-sizing: the primary roll
  control surfaces that carry the rest of the roll authority; same
  damping derivative conventions and hinge moment bookkeeping.
- vehicle-design/sizing/wing-planform-sizing: reference area and
  span inputs for the spoiler area ratio and geometry checks.
- vehicle-design/conceptual/constraint-analysis: field performance
  margins that the lift dump and speed brake support.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_spoiler_sizing.py

The test covers the transport worked example (flight spoiler total
and per-panel area, 45 deg deflection, dump belt for the 60 percent
lift dump, speed brake and lift dump drag increments, hinge moment,
limits verdict), the roll share split and damping balance, scaling
laws, round trips (area to capability, dump area to dCL), the
deflection saturation beyond the 45 deg linear band, and ValueError
rejection of non-positive dynamic pressure, area and speed, of
negative cl_delta_spoil, of shares outside (0, 1), of deflections
outside (0, 90], and of k_dump outside (0, 1.5].

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 roll
  capability and landing performance requirements frame the sizing
  context; the spoiler relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

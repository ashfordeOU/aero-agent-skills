---
name: control-surface-effectiveness
description: "Use when you must size and verify the elevator authority and hinge moment requirements of a transport-category airplane: compute the dynamic pressure and the hinge moment coefficient from the tab and angle derivative terms, the hinge moment from the elevator area and chord, the stick force from the gearing arm, the tail volume coefficient and the elevator pitching moment derivative, the elevator deflection needed to trim and to reach a maneuver load factor, the authority margin against the maximum deflection, and the net pitch-up moment about the main gear needed to rotate at the takeoff lift off speed. Produces the hinge moment, stick force, trim and maneuver deflections, authority margin, and controllability verdict that gate the control surface sizing check. Trigger: elevator authority, hinge moment, stick force, elevator deflection, tail volume coefficient, rotation authority, controllability limit."
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
  tags: [control-surface-effectiveness, elevator-authority, hinge-moment, hinge-moment-coefficient, stick-force, elevator-deflection, tail-volume-coefficient, elevator-effectiveness, maneuver-load-factor, rotation-authority]
  version: 0.1.0
  author: Aero Agent Skills
---

# Control Surface Effectiveness (flight-mechanics/stability-control/control-surface-effectiveness)

Use when the task is elevator authority and hinge moment analysis:
the control loads on the elevator, the stick force the pilot must
overcome, the elevator deflection needed to trim and to maneuver, the
authority margin before saturation, and the rotation capability about
the main gear at takeoff.

## Domain quick reference

- Dynamic pressure: q = 0.5 * rho * V^2, with rho the air density in
  kg/m^3 and V the true airspeed in m/s. Worked: q(1.225, 70.0) =
  3001.25 Pa at 70 m/s sea level.
- Hinge moment coefficient: C_h = C_h0 + C_h_alpha * alpha_t +
  C_h_delta * delta_e, with alpha_t the tailplane angle of attack in
  radians and delta_e the elevator deflection in radians (positive
  trailing edge down). Worked: C_h(0.02, 0.25, 0.15, 0.50, 0.30) =
  0.2075. C_h0 carries the tab setting; a negative C_h_delta means the
  hinge moment opposes the deflection, which is the balancing goal.
- Hinge moment: H = C_h * q * S_e * c_e, with S_e the elevator area in
  m^2 and c_e the elevator mean chord in m. Worked: H(0.2075,
  3001.25, 1.2, 0.4) = 298.9245 N m.
- Stick force: P = H / L_gear, with L_gear the effective gearing arm
  in m. Worked: P(298.9245, 0.35) = 854.07 N, which exceeds the
  classical transport stick force gate of about 222 N (50 lbf) for the
  limit maneuver in FAR 25.143 and CS 25.143.
- Tail volume coefficient: V_H = l_t * S_t / (S * c_bar), with l_t the
  tail moment arm in m, S_t the tailplane area in m^2, S the wing area
  in m^2, and c_bar the wing mean chord in m. Worked: V_H(12.0, 9.0,
  50.0, 2.1) = 1.0285714.
- Elevator pitching moment derivative: C_m_delta = -eta_t * V_H *
  C_L_delta_e, with eta_t the tailplane dynamic pressure ratio and
  C_L_delta_e the tail lift slope with elevator deflection in per
  radian. Worked: C_m_delta(1.0285714, 0.9, 1.0) = -0.9257143 per
  radian, negative for an aft tail.
- Trim deflection: delta_e = -(C_m0 + C_m_alpha * alpha) / C_m_delta.
  Worked: trim(0.05, -0.8, 0.1, -0.9257143) = -0.0324074 rad, about
  1.86 degrees trailing edge up.
- Maneuver deflection: at load factor n the angle of attack is n *
  C_L_1g / C_L_alpha and the deflection closes the moment equation.
  Worked: maneuver(0.05, -0.8, 5.5, 0.5, 2.5, -0.9257143) =
  -0.1423962 rad, about 8.16 degrees at the 2.5 g limit.
- Authority margin: delta_max - abs(delta_required). Worked:
  margin(0.35, -0.0324074) = 0.3175926 rad, about 18.2 degrees of
  reserve before the 20 degree stop.
- Takeoff rotation: the elevator download L_t_down on the tail must
  pitch the airplane nose up about the main gear against the weight
  moment: M = L_t_down * l_t - W * x_cg, with x_cg the CG distance
  ahead of the gear in m. Worked: M(8000.0, 12.0, 30000.0, 0.5) =
  81000.0 N m, a positive rotation authority verdict.

## Workflow

1. Establish the flight condition: compute the dynamic pressure with
   dynamic_pressure from the density and true airspeed at the analysis
   point (takeoff lift off, landing flare, or maneuver).
2. Build the hinge moment coefficient with
   hinge_moment_coefficient from the tab term, the tail angle of
   attack derivative, and the elevator deflection derivative.
3. Compute the hinge moment with hinge_moment from the coefficient,
   dynamic pressure, elevator area, and elevator chord, then the stick
   force with stick_force from the gearing arm; check the result
   against the controllability limit with stick_force_limit_check.
4. Size the tail authority: tail_volume_coefficient from the moment
   arm, tailplane area, wing area, and mean chord, then
   elevator_pitching_derivative from the tail volume, the elevator
   lift slope, and the tailplane efficiency.
5. Find the elevator deflection needed to trim with
   trim_elevator_deflection, and the deflection needed at the limit
   load factor with maneuver_elevator_deflection.
6. Compute the authority margin with authority_margin against the
   mechanical stop; a negative margin means the control saturates
   before the maneuver is reached.
7. Check the takeoff rotation with rotation_net_moment about the main
   gear and the verdict with rotation_authority_check; if the moment
   is negative, add tail download capacity, move the CG aft, or
   enlarge the elevator.
8. Iterate the gearing arm, tab setting, or tail volume until the
   stick force and the authority margin both pass the limits.

## Pitfalls

- Confusing the rotation authority check with takeoff-performance:
  takeoff-performance sizes the ground roll and lift off speed; the
  rotation check here verifies the elevator can pitch the airplane
  nose up about the main gear, and does not produce a distance.
- Confusing the flare stick force with landing-performance:
  landing-performance computes approach speed, flare geometry, and
  stopping distance; the hinge moment and stick force at flare are
  control loads, not landing distances.
- Treating the hinge moment as a drag term from the aerodynamics
  drag-polars leaves: drag polars quantify lift to drag ratio, while
  the elevator hinge moment is the load about the hinge line that the
  actuator or the pilot must carry; the two are not interchangeable.
- Mixing the sign conventions: delta_e positive trailing edge down,
  C_m_delta negative for an aft tail, and a negative trim deflection
  meaning trailing edge up; a flipped sign turns the rotation verdict
  around.
- Measuring the dynamic pressure at the wrong speed: q must use the
  true airspeed of the analysis condition, not an equivalent airspeed
  or a different phase of the flight.
- Forgetting the tab balance: C_h0 is the tab-fixed zero term, and an
  untrimmed estimate with C_h0 = 0 overstates the stick force that the
  balancing tab is designed to remove.
- Quoting the maximum deflection as the margin: the authority margin
  is delta_max minus the magnitude of the required deflection, so a
  control at its stop has zero margin even with travel still nominally
  available.
- Computing the rotation moment about the wrong point: the pitch-up
  check balances tail download and weight about the main gear, with
  the CG ahead of the gear; using the CG position aft of the gear
  flips the sign of the weight moment.

## Behavior contract (gate 3)

The control surface effectiveness math is exercised by the gate 3
contract test: scripts/test_control_surface_effectiveness.py against
scripts/control_surface_effectiveness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_control_surface_effectiveness.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; FAR 25.143 and
  CS 25.143 set the controllability and maneuverability basis
  (smooth control transitions, limit load factor without excessive
  stick force), referenced summary-only per standards-map.yaml.
- The hinge moment, tail volume, and rotation authority formulas are
  common flight-mechanics methodology, not reproduced text.
- compliance: STANDARDS-REF, gated: false.

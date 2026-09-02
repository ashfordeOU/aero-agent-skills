---
name: control-surface-sizing
description: "Size the aileron, elevator, and rudder control surfaces of a fixed-wing aircraft from control power: the aileron area from the roll rate requirement with the roll damping derivative, the elevator area from the pitch moment requirement with the elevator effectiveness, the rudder area from the yaw moment requirement for the engine-out case, the hinge moment for the actuator, and the deflection limits against the typical travel ranges. Use when the task is control surface sizing, aileron sizing, elevator area, rudder area, roll rate requirement, pitch moment authority, yaw authority, hinge moment, or deflection limits. Trigger: control surface sizing, aileron sizing, elevator area, rudder area, hinge moment, deflection limits."
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
  tags: [control-surface-sizing, aileron-sizing, elevator-sizing, rudder-sizing, hinge-moment, control-power, deflection-limits, roll-rate-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# Control Surface Sizing (vehicle-design/sizing/control-surface-sizing)

Use when the task is sizing the movable control surfaces of a
fixed-wing aircraft from control power requirements: the aileron area
needed to meet the target roll rate, the elevator area needed to meet
the pitch moment requirement, the rudder area needed to meet the yaw
moment requirement, the hinge moment for the actuator, and the check
of the required deflections against the travel limits.

## Domain quick reference

- Dynamic pressure: q = 0.5 * rho * V^2, with rho the air density in
  kg/m^3 and V the true airspeed in m/s. Worked: q(1.225, 85.0) =
  4425.31 Pa at 85 m/s sea level, the maneuvering speed for the
  aileron sizing anchor.
- Aileron rolling moment derivative: C_l_delta_a = 2 * tau_a *
  C_L_alpha_w * y_a * S_a / (S_w * b), with tau_a the aileron
  effectiveness, C_L_alpha_w the wing lift curve slope in per radian,
  y_a the spanwise centroid of the aileron in m, S_a the total
  aileron area of both wings in m^2, S_w the wing reference area in
  m^2, and b the span in m. Worked: C_l_delta_a(5.67, 0.5, 5.5,
  13.5, 120.0, 34.0) = 0.1032 per radian.
- Steady roll rate: p = -2 * V * C_l_delta * delta / (b * C_l_p),
  the balance of the aileron rolling moment against the roll damping
  derivative C_l_p (negative). Worked: p(0.1032, 0.436, 85.0, 34.0,
  -0.45) = 0.4999 rad/s, about 28.6 deg/s.
- Required aileron area for a roll rate requirement: first C_l_delta =
  -p_req * b * C_l_p / (2 * V * delta_max), then S_a = C_l_delta *
  S_w * b / (2 * tau_a * C_L_alpha_w * y_a). Worked: S_a(0.5, 85.0,
  34.0, -0.45, 0.436, 0.5, 5.5, 13.5, 120.0) = 5.6714 m^2 total,
  about 2.84 m^2 per aileron.
- Elevator pitching moment derivative: C_m_delta_e = -eta_t * V_H *
  C_L_alpha_t * tau_e, with eta_t the tail dynamic pressure ratio,
  V_H the horizontal tail volume coefficient, C_L_alpha_t the tail
  lift curve slope in per radian, and tau_e the elevator
  effectiveness. Worked: C_m_delta_e(0.9, 0.7, 4.5, 0.6) = -1.701
  per radian, negative for an aft tail.
- Required elevator area for a pitch moment requirement: S_e =
  C_m_req * S_t / (eta_t * V_H * C_L_alpha_t * tau_e * delta_max),
  with C_m_req the nose-up pitch moment coefficient the elevator must
  provide and S_t the horizontal tail area in m^2. Worked:
  S_e(0.22, 21.0, 0.9, 0.7, 4.5, 0.6, 0.436) = 6.2295 m^2, about 30%
  of the horizontal tail area.
- Rudder yawing moment derivative: C_n_delta_r = -eta_v * V_V *
  C_L_alpha_v * tau_r, with eta_v the vertical tail dynamic pressure
  ratio, V_V the vertical tail volume coefficient, C_L_alpha_v the
  vertical tail lift curve slope, and tau_r the rudder effectiveness.
  Worked: C_n_delta_r(0.9, 0.06, 3.5, 0.6) = -0.1134 per radian.
- Required rudder area for a yaw moment requirement: S_r = C_n_req *
  S_v / (eta_v * V_V * C_L_alpha_v * tau_r * delta_max), with C_n_req
  the yawing moment coefficient the rudder must provide (typically
  the engine-out case) and S_v the vertical tail area in m^2. Worked:
  S_r(0.022, 18.83, 0.9, 0.06, 3.5, 0.6, 0.524) = 6.9715 m^2, about
  37% of the vertical tail area.
- Control power: |C_delta| * delta_max, the maximum dimensionless
  moment at the deflection limit. Worked: elevator power 1.701 * 0.436
  = 0.7416 against C_m_req = 0.22; rudder power 0.1134 * 0.524 =
  0.0594 against C_n_req = 0.022.
- Hinge moment for the actuator: H = C_h * q * S_surf * c_surf, with
  C_h the hinge moment coefficient, S_surf the control surface area
  in m^2, and c_surf the mean chord of the control surface in m.
  Worked: H(0.1526, 4425.31, 6.22, 0.35) = 1470.13 N m.
- Deflection limits: aileron about +/-25 deg, elevator about +25/-15
  deg (trailing edge down positive), rudder about +/-30 deg; 25 deg
  is 0.436 rad and 30 deg is 0.524 rad.

## Workflow

1. Set the reference quantities: wing area S_w, span b, and the
   maneuvering speed V with the flight density; evaluate the dynamic
   pressure q.
2. Set the aileron parameters: effectiveness tau_a, wing lift curve
   slope C_L_alpha_w, aileron spanwise centroid y_a, maximum
   deflection delta_max, and the roll damping derivative C_l_p
   (negative).
3. Solve for the required total aileron area with
   aileron_area_required; check the round trip with
   aileron_control_derivative and roll_rate_achieved so the roll rate
   requirement is met at the maximum deflection.
4. Set the elevator parameters: tail dynamic pressure ratio eta_t,
   horizontal tail volume coefficient V_H, tail lift curve slope
   C_L_alpha_t, elevator effectiveness tau_e, and maximum deflection.
5. Solve for the required elevator area with elevator_area_required
   and confirm the control power |C_m_delta_e| * delta_max covers the
   pitch moment requirement with control_power.
6. Set the rudder parameters and solve for the required rudder area
   with rudder_area_required; confirm the yaw control power covers
   the engine-out yaw moment requirement.
7. Estimate the hinge moment at the sizing condition with
   hinge_moment for the actuator selection.
8. Check the required deflections against the travel limits with
   deflection_limit_check; rework the surface area or the effectiveness
   until the deflections fit the band with margin.

## Pitfalls

- Confusing this leaf with sizing/tail-sizing: tail-sizing sets the
  horizontal and vertical tail areas from volume coefficients; this
  leaf sizes the movable control surfaces from control power. The
  elevator and rudder areas come out as fractions of the tail areas,
  not the tail areas themselves.
- Confusing this leaf with sizing/ws-tw-trade: ws-tw-trade matches
  wing loading and thrust to weight against takeoff, climb, and
  cruise constraints; it carries no roll rate, control power, or
  deflection limit vocabulary. Roll rate requirements belong here.
- Confusing this leaf with the flight-mechanics stability-control
  leaves: control-surface-effectiveness analyzes the authority of an
  existing elevator (hinge moment, stick force, trim deflection),
  aileron-reversal checks the aeroelastic reversal speed, and
  trim-analysis computes trim deflections. This leaf sizes the areas
  from the control power requirement before those analysis leaves
  take over.
- Using the wrong aileron reference quantities: S_a is the total
  aileron area of both wings and y_a is the spanwise centroid of the
  aileron, not the aileron span and not the wing semi-span; swapping
  them silently distorts the derivative.
- Passing a positive roll damping derivative: C_l_p must be negative;
  a positive value flips the roll rate sign convention and in
  aileron_area_required produces a nonsense negative area, so the
  module raises ValueError instead.
- Mixing degrees and radians: delta_max in the sizing equations is in
  radians (25 deg = 0.436 rad, 30 deg = 0.524 rad) while
  deflection_limit_check takes degrees; converting only one side
  gives an area off by a factor of about 57.
- Treating the sized area as the full tail: the anchors give the
  elevator at about 30% of the horizontal tail and the rudder at
  about 37% of the vertical tail; using the computed value as the
  whole tail area roughly triples the surface.
- Skipping the control power check: sizing to the requirement is
  necessary but not sufficient; verify |C_delta| * delta_max covers
  the requirement (elevator 0.7416 vs 0.22, rudder 0.0594 vs 0.022)
  before accepting the deflection limits.

## Behavior contract (gate 3)

The control surface sizing relations, the control power checks, the
hinge moment estimate, and the deflection limit verdicts are
exercised by the gate 3 contract test:
scripts/test_control_surface_sizing.py against
scripts/control_surface_sizing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_control_surface_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the control
  surface sizing equations are common conceptual sizing methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

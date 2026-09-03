# Wave-29 leaf spec: canard-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/canard-sizing/
- Pack: sizing (existing siblings: battery-sizing, brake-energy-sizing,
  control-surface-sizing, engine-sizing, fuel-tank-sizing,
  fuselage-sizing, ice-protection-sizing, landing-gear-sizing,
  nacelle-sizing, propeller-sizing, spoiler-sizing, tail-sizing,
  tire-sizing, weight-estimation, wing-planform-sizing,
  ws-tw-trade)
- Standards ids: far-25, cs-25 (reference-only; the sizing pack
  convention). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the canard surface of a canard-configured aircraft at the
conceptual sizing level: compute the required canard area from a
target canard volume coefficient and the canard arm, derive the trim
lift share carried by the canard from the longitudinal geometry, check
the canard and wing lift coefficients at the trim condition, and run
the stall-precedence check that the canard reaches maximum lift before
the wing so the nose drops rather than pitches up. Produces the canard
area, trim lift share, trim lift coefficients, and the stall-
precedence verdict that gate the canard configuration sizing.

Does NOT do: size a conventional empennage (tail-sizing owns the
horizontal and vertical tail volume coefficients V_h and V_v);
size control surfaces from control power (control-surface-sizing owns
aileron, elevator, and rudder area from roll, pitch, and yaw
requirements); compute neutral point and static margin of the whole
aircraft (flight-mechanics longitudinal-stability owns the neutral
point and static margin); size the wing planform (wing-planform-sizing
owns the main wing). This leaf sizes the forward canard surface of a
canard or three-surface configuration and checks its trim and stall
behavior.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).

Geometry convention: x is positive aft, origin at the wing
aerodynamic center. The canard lies forward of the wing (x_c < x_w =
0) and the center of gravity lies between them (x_c < x_cg < x_w).
All arms in m, areas in m2.

Functions (pure stdlib, floats):
- canard_volume_coefficient(canard_area, canard_arm, wing_area,
  wing_mac) -> float: V_c = canard_area * canard_arm / (wing_area *
  wing_mac). ValueError on non-positive inputs.
- required_canard_area(target_volume_coefficient, canard_arm,
  wing_area, wing_mac) -> float:
  S_c = target_volume_coefficient * wing_area * wing_mac / canard_arm.
  ValueError on non-positive inputs. (Canard volume coefficient
  convention mirrors V_h with the arm from the wing aerodynamic center
  to the canard aerodynamic center.)
- canard_lift_share(x_cg, x_w, x_c) -> float: the fraction of weight
  carried by the canard in steady level trim from the moment balance
  about the CG (lift up positive; arms as defined above):
  f_c = (x_w - x_cg) / (x_w - x_c). ValueError unless x_c < x_cg <
  x_w.
- trim_lift_coefficients(weight, dynamic_pressure, wing_area,
  canard_area, x_cg, x_w, x_c) -> dict: f_c = canard_lift_share(...);
  L_c = f_c * weight; L_w = weight - L_c;
  Cl_c = L_c / (dynamic_pressure * canard_area);
  Cl_w = L_w / (dynamic_pressure * wing_area);
  returns {canard_lift_share: f_c, canard_lift_N: L_c,
  wing_lift_N: L_w, canard_cl: Cl_c, wing_cl: Cl_w}. ValueError on
  dynamic_pressure <= 0, weight <= 0, or bad geometry.
- stall_precedence(canard_cl, canard_cl_max, wing_cl, wing_cl_max) ->
  dict: margin_ratio_c = canard_cl_max / canard_cl;
  margin_ratio_w = wing_cl_max / wing_cl;
  verdict = "canard-stalls-first" if margin_ratio_c < margin_ratio_w
  else "wing-stalls-first"; returns {canard_margin_ratio,
  wing_margin_ratio, verdict}. A canard configuration requires
  canard-stalls-first for pitch-up avoidance. ValueError if any max
  value <= 0 or any cl <= 0 (cl must be positive at trim for this
  check).
- size_canard(target_volume_coefficient, canard_arm, wing_area,
  wing_mac) -> dict: convenience: returns {canard_area,
  canard_volume_coefficient: target}. ValueErrors propagate.

## Worked example

Canard-configured light aircraft: wing area S = 30 m2, wing MAC cbar
= 2.8 m, canard arm from wing AC to canard AC = 9 m, target V_c =
0.45. Forward CG case x_cg = -3 m (3 m ahead of the wing AC), canard
x_c = -9 m, wing x_w = 0 m. Weight = 1200 kg * g0; dynamic pressure
q = 0.5 * 1.225 * 45^2 = 1240.3 Pa. Canard Cl_max = 1.7, wing Cl_max
= 1.5.

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- required_canard_area(0.45, 9, 30, 2.8) = 4.2 m2 (within 1e-6).
- canard_volume_coefficient(4.2, 9, 30, 2.8) = 0.45 (round-trip
  within 1e-9).
- canard_lift_share(-3, 0, -9) = (0 - (-3)) / (0 - (-9)) = 3/9 =
  0.3333 (within 1e-6).
- trim_lift_coefficients(1200*g0, 1240.3, 30, 4.2, -3, 0, -9):
  f_c = 0.3333, L_c = 3922.7 N (within 1), L_w = 7845.3 N (within 1),
  canard_cl = 0.7526 (within 1e-3), wing_cl = 0.2108 (within 1e-3).
- stall_precedence(0.7526, 1.7, 0.2108, 1.5): margin_ratio_c = 2.259
  (within 0.01), margin_ratio_w = 7.116 (within 0.01), verdict
  "canard-stalls-first".
- Aft CG case x_cg = -1 m: f_c = 1/9 = 0.1111, canard_cl = 0.2510
  (within 1e-3), wing_cl = 0.2811 (within 1e-3);
  stall_precedence verdict = "wing-stalls-first" (margin_ratio_c 6.77
  > margin_ratio_w 5.34), demonstrating the pitch-up risk.
- ValueErrors: target V_c 0, arm 0, x_cg not between x_c and x_w,
  dynamic_pressure 0, weight 0, cl_max 0, cl <= 0.

Keep at least 18 test methods: volume coefficient, required area,
round-trip, lift share forward/aft CG, trim Cl anchors, stall
precedence both verdicts, geometry ValueError, non-positive
ValueErrors. Runs offline in under 20 s.

## Corpus tasks (ids w29-canard-sizing-1/2)

Distinctive tokens: canard sizing, canard volume coefficient, canard
area, forward wing, stall precedence, canard configuration, trim lift
share. Avoid: tail volume coefficient, horizontal tail, vertical tail,
empennage (tail-sizing); aileron elevator rudder area from control
power (control-surface-sizing); neutral point, static margin
(longitudinal-stability); wing area, aspect ratio, mean aerodynamic
chord for the main wing planform (wing-planform-sizing).

1. "size the canard of a canard-configured aircraft: required area
   for a 0.45 canard volume coefficient with a 9 m arm on a 30 m2
   wing, and the trim lift share at the forward CG"
2. "check stall precedence on a canard layout: does the canard reach
   maximum lift before the wing so the nose drops instead of pitching
   up?"

## SKILL body notes

Pair with tail-sizing (conventional empennage sizing for comparison),
longitudinal-stability (the neutral point and static margin that frame
canard trim), control-surface-sizing (if the canard carries control
authority), wing-planform-sizing. State the boundary: canards are a
lifting/trimming forward surface, distinct from the aft empennage the
tail-sizing leaf owns, and the leaf explicitly checks the canard-first
stall behavior that makes the configuration pitch-safe. far-25 and
cs-25 are reference-only for transport-like design practice. Mirror
the sizing pack SKILL body style (SI units, stdlib only, deterministic
offline).

# Wave-25 leaf spec: spoiler-sizing (vehicle-design, priority small family)

- Path: skills/vehicle-design/sizing/spoiler-sizing/
- Pack: sizing (existing: control-surface-sizing owns aileron/elevator/rudder)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: vehicle-design

## Claim

Size the flight and ground spoiler panels of a transport aircraft: split
the roll control requirement between the ailerons and the roll spoilers,
compute the flight spoiler panel area and deflection from the roll
assist share and the roll damping, size the ground spoiler (lift dumper)
panel area from the lift dump needed to unload the wing for braking,
compute the speed-brake drag increment from the deployed spoiler area
and deflection, estimate the spoiler hinge moment for the actuator, and
check the deflection limits against typical travel. Produces the spoiler
panel areas, deflections, lift-dump drag and speed-brake drag, hinge
moments, and a sized verdict.

Does NOT do: aileron/elevator/rudder sizing (control-surface-sizing
owns primary surfaces), flap/slat high-lift increments (aerodynamics
high-lift-systems owns clmax increments of trailing/leading edge
devices), spoiler aerodynamic interference or asymmetric deployment
dynamics. The leaf sizes spoiler panels used for roll assist, lift dump,
and speed braking.

## Model (implement exactly)

- Roll spoiler roll authority share: given the total roll rate
  requirement p_req (rad/s) at a reference speed, the ailerons provide a
  share f_ail (input, default ~0.6-0.7 transport typical) and roll
  spoilers f_spoil = 1 - f_ail. Panel lift increment needed from roll
  spoilers to meet the share: use the roll damping derivative approach,
  L_spoil_delta = p_req * I_xx / (q * S * b * y_spoil_arm) style per
  control-surface-sizing conventions but for the spoiler share only.
- Flight spoiler area: A_spoil = (required roll moment share) /
  (q * b * Cl_delta_spoil * y_arm) with the spoiler lift (drag-generating)
  effectiveness Cl_delta_spoil an input or a module-typical value
  (-0.3..-0.5 per rad per unit area ratio), y_arm the spanwise centroid
  of the outboard spoiler panel. Solve for the area and deflection
  (deflection typically 0-60 deg with effectiveness loss at high
  deflection, use a linear range up to ~45 deg then saturation).
- Lift dump (ground spoilers): the ground spoiler must destroy the wing
  lift on touchdown. Required lift loss = fraction f_dump (input,
  default 0.5-0.7 of the lift at the touchdown lift coefficient). The
  lift loss from spoiler deployment is dCL_dump = -A_dump/S * k_dump *
  sin(deflection) style; solve A_dump from the required dCL and the
  maximum deflection.
- Speed brake drag increment: dCD = A_deployed/S * cd_spoil_typ *
  sin(deflection) * span_factor, summed over the deployed panels.
- Hinge moment: H = q * A_panel * c_bar_panel * ch_delta *
  (c_h0 + c_h_alpha * alpha + c_h_delta * delta) with module-typical
  hinge-moment coefficients (reference-only); return the actuator force
  H / (c_bar_panel * ... ) or the moment directly.
- Deflection and geometry limits: check 0 < delta <= delta_max (module
  constant, typical 60 deg), panel aspect ratio within 1.5-4 band, panel
  span fraction of wing semi-span within 0.2-0.5.
Functions:
- roll_spoiler_share(f_aileron_share) -> f_spoil
- flight_spoiler_area(roll_moment_share, q, s, b, cl_delta_spoil,
  y_arm) -> area
- flight_spoiler_deflection(required_lift_increment, ...) -> delta
- ground_spoiler_area(f_dump, cl_touchdown, s, k_dump, delta_max) -> area
- lift_dump_drag_increment(area_deployed, s, cd_spoil, delta) -> dCD
- speed_brake_drag_increment(area_deployed, s, cd_spoil, delta) -> dCD
- hinge_moment(q, area, c_bar, alpha, delta, coeffs) -> H (Nm)
- spoiler_verdict(...) -> dict (areas, deflections, drag increments,
  hinge moments, limits verdict)
ValueError on: negative q, area, speed; f_ail outside (0,1); delta out
of (0, 90]; cl_delta_spoil >= 0 (must be negative for lift loss), k_dump
out of (0,1.5).

## Worked example

Transport-class example: wing loading S = 122 m2, b = 34 m, design roll
rate p_req = 0.5 rad/s at the maneuver speed, aileron share 0.65, q at
the maneuver point. Compute flight spoiler total area and per-panel
area for 4 outboard panels, ground spoiler total area to dump 60% of
the touchdown CL ~1.0, dCD at 45 deg deployment, hinge moment at q.
Use your module constants; assert your real numbers in tests.

## Corpus tasks (ids w25-spoiler-sizing-1/2)

Distinctive tokens: spoiler sizing, flight spoiler, ground spoiler,
lift dump, speed brake, roll spoiler, roll assist share, spoiler panel
area, lift dumper, spoiler deflection. Avoid: aileron sizing, elevator,
rudder, flap, slat, clmax increment (owned by control-surface-sizing and
high-lift-systems).

1. "size the ground spoiler panels to dump 60 percent of the wing lift
   on touchdown and the flight spoilers for the roll assist share, then
   estimate the speed brake drag increment at the landing speed"
2. "compute the spoiler panel area and deflection that deliver the roll
   damping assist for the outboard wing and the hinge moment for the
   actuator at the maneuver dynamic pressure"

## SKILL body notes

Pair with control-surface-sizing (ailerons provide the primary roll
channel), wing-planform-sizing (span, S), constraint-analysis (field
performance margins). Worked example uses module constants and real
outputs. Compliance: FAR/CS 25 roll and landing performance requirements
referenced by name, no reproduced text.

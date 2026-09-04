# Wave-32 leaf spec: rotorcraft-blade-flapping-dynamics (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-blade-flapping-dynamics/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance,
  rotorcraft-hover-ground-effect, rotorcraft-forward-flight-performance,
  rotorcraft-vertical-climb-performance, rotorcraft-tail-rotor-sizing
  (all momentum-theory POWER leaves); this is the first rotor
  DYNAMICS leaf (blade flapping/coning/Lock number) in the library.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the basic blade-flapping dynamics of a helicopter main rotor:
the blade Lock number from the air density, the lift-curve slope, the
blade chord, the rotor radius and the blade flap moment of inertia,
the steady hover coning angle from the Lock number, the collective
pitch and the uniform inflow ratio, and the rotating flap natural
frequency ratio for a flap-hinge offset. Produces the Lock number, the
hover coning angle in radians and degrees and the flap frequency ratio
that gate a rotor-dynamics assessment. This is the first blade-
dynamics (non-performance) content in the flight-mechanics rotorcraft
subdomain.

Does NOT do: hover power, induced velocity, figure of merit, disk
loading (rotorcraft-hover-performance owns momentum-theory hover
performance); forward-flight power and inflow (rotorcraft-forward-
flight-performance); vertical climb (rotorcraft-vertical-climb-
performance); tail rotor anti-torque sizing (rotorcraft-tail-rotor-
sizing); fixed-wing spin autorotation (flight-mechanics/stability-
control/spin-recovery owns the post-stall autorotative band of a
stalled wing); control-theory lead/lag compensation
(gnc-autonomy/control/lead-lag-compensation is a servo filter topic);
ground resonance or lag dynamics (not modeled here - flap dynamics
only).

## Model (implement exactly)

Module constants:
- RHO_SL = 1.225 (kg/m3).
- A_LIFT_DEFAULT = 5.73 (1/rad, typical section lift-curve slope;
  published rotor Lock numbers fall in the 5-12 band).
- PI = math.pi.

Functions (pure stdlib):

- blade_flap_inertia_uniform(blade_mass_kg, radius_m) -> I_beta =
  blade_mass_kg * radius_m**2 / 3 (uniform blade about the flap hinge
  at the rotation axis). ValueErrors on non-positive inputs.
- lock_number(rho, lift_slope, chord_m, radius_m, flap_inertia) ->
  gamma = rho * lift_slope * chord_m * radius_m**4 / flap_inertia.
  ValueErrors on non-positive inputs. (Johnson Helicopter Theory ch.4;
  Leishman Principles of Helicopter Aerodynamics ch.4 - reference
  paraphrase, no reproduction.)
- hover_coning_angle(gamma, theta0_rad, inflow_ratio) -> a0 =
  0.5 * gamma * (theta0_rad / 4.0 - inflow_ratio / 3.0) [rad].
  Steady hover flap-moment balance for an untwisted centrally hinged
  blade with uniform inflow: aero flap moment = 0.5 * rho * a * c *
  Omega^2 * R^4 * (theta0/4 - lambda/3), centrifugal restoring =
  I_beta * Omega^2 * a0, giving a0 = (gamma/2)*(theta0/4 - lambda/3).
  ValueErrors if gamma <= 0, theta0_rad < 0, inflow_ratio < 0.
- flap_frequency_ratio(hinge_offset_fraction) -> nu =
  sqrt(1 + 1.5 * e / (1 - e)) where e = hinge_offset_fraction in (0,1);
  exact uniform-mass rotating flap frequency ratio about an offset
  hinge, algebraically identical to nu^2 = (1 - 3e/2 + e^3/2)/(1-e)^3.
  At e = 0 the limit is exactly 1.0 (central hinge, 1/rev).
  ValueErrors if e < 0 or e >= 1.
- blade_flapping_summary(blade_mass_kg, radius_m, chord_m, lift_slope
  = A_LIFT_DEFAULT, rho = RHO_SL, theta0_rad, inflow_ratio,
  hinge_offset_fraction) -> dict {lock_number, flap_inertia_kg_m2,
  coning_angle_rad, coning_angle_deg, flap_frequency_ratio,
  flap_frequency_per_rev}. ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Typical light-to-medium helicopter blade: rho = 1.225 kg/m3,
a = 5.73 /rad, chord c = 0.50 m, radius R = 6.0 m, blade mass m_b =
50 kg (I_beta = 600 kg m2), collective theta0 = 0.170 rad, uniform
inflow ratio lambda = 0.050, hinge offset e = 0.05.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- flap_inertia_uniform(50, 6.0) = 600.0 kg m2 exactly.
- lock_number in 6-10 (about 7.58; published rotor Lock numbers are
  5-12).
- coning_angle_rad about 0.0979 rad, coning_angle_deg about 5.61 deg
  (published hover coning 3-8 deg).
- flap_frequency_ratio about 1.0387 (published articulated flap
  frequency 1.02-1.08/rev).
- blade_flapping_summary dict has the documented keys.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive mass/radius/chord/lift slope/density/
  inertia/gamma; theta0 < 0; inflow_ratio < 0; e < 0 or e >= 1.
- flap_inertia_uniform exact: 50 kg, 6.0 m -> 600.0.
- lock_number: gamma = rho*a*c*R^4/I_beta (compute by hand for the
  worked case: 1.225*5.73*0.5*1296/600 = 7.578...).
- coning limiting checks: theta0/4 == inflow_ratio/3 gives a0 = 0.0;
  increasing theta0 increases a0; increasing inflow_ratio decreases a0.
- flap_frequency_ratio: e = 0.05 -> about 1.0387; e = 0 limit exactly
  1.0 (assert flap_frequency_ratio(0.0) == 1.0); larger e gives larger
  nu; e -> 0.5 gives sqrt(1+1.5) = sqrt(2.5) about 1.5811.
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-rotorcraft-blade-flapping-dynamics.yaml)

Query 1 (copy verbatim):
  "compute the blade Lock number and the steady hover coning angle of a helicopter main rotor from the blade geometry and the uniform inflow ratio"
  intent: "flight-mechanics; rotorcraft blade Lock number and hover coning angle"
  expected_skill: "flight-mechanics/performance/rotorcraft-blade-flapping-dynamics"
Query 2 (copy verbatim):
  "determine the rotating flap frequency ratio of an articulated rotor blade for a given flap hinge offset fraction"
  intent: "flight-mechanics; rotorcraft flap frequency ratio from hinge offset"
  expected_skill: "flight-mechanics/performance/rotorcraft-blade-flapping-dynamics"
Task ids: w32-rotorcraft-blade-flapping-dynamics-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the blade-flapping
dynamics of a helicopter main rotor:" and include the outputs in the
Claim. First tag: rotorcraft-blade-flapping-dynamics. Additional tags
ONLY: rotor-blade-flapping, coning-angle, lock-number,
flap-frequency-ratio, rotor-dynamics, hinge-offset. NEVER single
generic words (flapping, blade, rotor, dynamics, hover, coning).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): induced velocity, ideal hover
power, profile power, figure of merit, disk loading, momentum theory
(rotorcraft-hover-performance and the other rotor power leaves);
ground resonance, lead-lag, lag damper (not modeled - decline those
terms); spin, stall autorotation (spin-recovery); lead lag
compensation, phase lead (gnc lead-lag-compensation). The word
"coning" and "flapping" are this leaf's own.

Tags: [rotorcraft-blade-flapping-dynamics, rotor-blade-flapping,
coning-angle, lock-number, flap-frequency-ratio, rotor-dynamics,
hinge-offset]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-hover-performance (the
momentum-theory power leaf; its blade geometry inputs are shared),
flight-mechanics/performance/rotorcraft-tail-rotor-sizing,
flight-mechanics/stability-control/spin-recovery (fixed-wing
autorotation is a different topic).

Ledger Standard: far-29.

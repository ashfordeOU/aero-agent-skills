# Wave-31 leaf spec: rotorcraft-hover-ground-effect (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-hover-ground-effect/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance (wave-30,
  out-of-ground-effect hover momentum theory; its body explicitly defers hover
  in ground effect to "aerodynamics/ground-effects/ground-effect", which is a
  FIXED-WING wing-in-ground-effect leaf: induced drag reduction from height to
  span ratio, image vortex, lift increase. No rotor-disk hover-in-ground-effect
  computation exists anywhere in the library - this leaf fills that rotorcraft
  gap), rotorcraft-vertical-climb-performance and rotorcraft-tail-rotor-sizing
  (this wave).
- Standards ids: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the hover-in-ground-effect (HIGE) performance of a rotorcraft rotor:
the ground-effect induced-power reduction factor from the rotor height above
the ground and the rotor radius, the IGE induced power, the IGE total hover
power with the induced-power factor and the profile power, the power margin
against an available power, and the maximum rotor height at which the
rotorcraft can hover with that available power. Produces the ground-effect
factor, the IGE induced and total power, the IGE power margin, and the maximum
hover height that gate a hover performance check in ground effect.

Does NOT do: out-of-ground-effect hover (rotorcraft-hover-performance owns the
OGE induced velocity, profile power, figure of merit, disk loading at zero
height effect); wing-in-ground-effect aerodynamics (aerodynamics/ground-effects/
ground-effect owns induced drag reduction and lift change for a WING from
height to span ratio and image vortices - a different physical configuration
and different outputs); vertical climb (rotorcraft-vertical-climb-performance);
forward flight power (rotorcraft-forward-flight-performance); recirculation or
partial ground contact modeling. The rotor disk model here is a rotor hovering
over a flat ground plane; the classic Cheeseman-style height correction applies
to the induced POWER (equivalently induced velocity) only; profile power is
unchanged in ground effect.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- RHO_SL = 1.225 (kg/m3).
- K_DEFAULT = 1.15 (induced power factor, same convention as the hover sibling).
- PI = math.pi.
- MIN_Z_RATIO = 0.5 (validity floor: the model is valid for height/radius
  >= 0.5; below that the rotor is in the ground-cushion regime where the
  point-model diverges).

Functions (pure stdlib):
- disk_area(radius) -> float: A = PI * radius**2. ValueError if radius <= 0.
- hover_induced_velocity(thrust, area, rho=RHO_SL) -> float:
  v_h = sqrt(thrust / (2 * rho * area)). ValueErrors on non-positive inputs.
- ground_effect_factor(height, radius) -> float:
  k_ige = 1 - (radius / (4 * height))**2, the Cheeseman-style reduction of the
  induced velocity (and therefore of the induced power at constant thrust) in
  ground effect. ValueError if radius <= 0 or height / radius < MIN_Z_RATIO.
- ige_induced_power(ideal_induced_power, ground_effect_factor) -> float:
  P_i_ige = P_ideal * factor. ValueError if P_ideal < 0 or factor <= 0 or
  factor > 1.
- ige_total_power(ideal_induced_power, profile_power, ground_effect_factor,
  k=K_DEFAULT) -> float: P_total_ige = k * P_ideal * factor + profile_power.
  ValueError if ideal_induced_power < 0, profile_power < 0, factor <= 0 or
  factor > 1, k <= 0.
- power_margin(available_power, required_power) -> float:
  margin = available_power - required_power. ValueError if
  available_power < 0 or required_power < 0.
- oge_total_power(ideal_induced_power, profile_power, k=K_DEFAULT) -> float:
  P_total_oge = k * P_ideal + profile_power. ValueErrors as above. (Used to
  decide whether ground effect matters for a given available power.)
- max_hover_height(weight_kg, radius, available_power, rho=RHO_SL,
  solidity=0.08, drag_coefficient=0.012, tip_speed=220.0, k=K_DEFAULT) ->
  float: largest height z (>= MIN_Z_RATIO*radius) at which the IGE total power
  equals available_power. If available_power >= the OGE total power, the
  rotorcraft can hover at any height: return None (no ground-effect-limited
  ceiling). Otherwise bisect z on [MIN_Z_RATIO*radius, 50*radius] for
  ige_total_power(z) = available_power (IGE total power increases with z and
  asymptotes to the OGE value, so the equation has exactly one root). Raise
  ValueError if available_power < the IGE total power at the lowest valid
  height (hover impossible even in full ground effect).
- hover_ground_effect(weight_kg, radius, height, rho=RHO_SL,
  solidity=0.08, drag_coefficient=0.012, tip_speed=220.0, k=K_DEFAULT,
  available_power=None) -> dict: convenience chain returning
  {thrust_N, area_m2, hover_induced_velocity, ideal_induced_power_W,
  profile_power_W, ground_effect_factor, ige_induced_power_W,
  ige_total_power_W, oge_total_power_W, power_margin_W (None when
  available_power is None), max_hover_height}. thrust = weight_kg * G0.
  ValueErrors propagate. (max_hover_height field None when available_power
  is None or when hover is possible at any height.)

## Worked example

Rotor radius R = 5.0 m, helicopter mass 2200 kg (weight 21574.63 N),
rho = 1.225 kg/m3, solidity 0.08, Cd0 = 0.012, tip speed 220 m/s, k = 1.15,
height above ground z = 5.0 m (z/R = 1.0).

Deterministic anchors (run your module, take the printed values as the assert
targets to 4 significant figures, then CHECK the magnitude bounds):
- hover induced velocity in 9.5-11.5 m/s (about 10.59).
- ideal induced power in 200 000-260 000 W (about 228 448).
- profile power in 100 000-150 000 W (about 122 935).
- ground effect factor at z/R = 1.0 in 0.90-0.97 (about 0.9375).
- IGE total power at z/R = 1.0 in 350 000-390 000 W (about 369 230).
- OGE total power in 350 000-430 000 W (about 385 650).
- ground effect factor at z/R = 2.0 in 0.96-1.00 (about 0.9844); at
  z/R = 0.5 exactly 0.75.
- with available_power = 360 000 W: max_hover_height in 3.0-5.0 m (about 4.0),
  and max_hover_height returns None when available_power = 400 000 W (above
  the OGE total).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: radius <= 0, thrust <= 0, rho <= 0, solidity <= 0, Cd0 <= 0,
  tip_speed <= 0, height / radius < 0.5 (ground_effect_factor and the
  convenience chain), factor <= 0 or > 1, profile_power < 0, k <= 0,
  available_power < 0.
- ground_effect_factor(5.0, 5.0) is exactly 0.9375 (height = radius).
- ige_induced_power equals ideal power times the factor.
- Monotonicity: ground_effect_factor increases toward 1 as height increases.
- max_hover_height returns None when available_power >= OGE total power.
- max_hover_height returns about the anchor value (3.0-5.0 m) at 360 kW.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-rotorcraft-hover-ground-effect.yaml)

Query 1 (copy verbatim):
  "compute the hover-in-ground-effect power of a helicopter rotor at a height of one rotor radius, using the Cheeseman ground-effect reduction factor on the induced power"
  intent: "flight-mechanics; rotorcraft hover-in-ground-effect power reduction"
  expected_skill: "flight-mechanics/performance/rotorcraft-hover-ground-effect"
Query 2 (copy verbatim):
  "determine the ige-hover-ceiling height above the ground at which a rotorcraft can hover with a given available power when out-of-ground-effect hover is not possible"
  intent: "flight-mechanics; rotorcraft IGE hover ceiling height from power margin"
  expected_skill: "flight-mechanics/performance/rotorcraft-hover-ground-effect"
Task ids: w31-rotorcraft-hover-ground-effect-1 and -2.

Forbidden tokens that belong to siblings: do NOT use wing-in-ground-effect,
induced drag reduction, image vortex, height to span ratio, ground cushion,
takeoff lift (aerodynamics ground-effect), figure of merit, disk loading,
blade solidity outputs of the hover OGE leaf beyond the input geometry, climb,
forward flight, autorotation.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the hover-in-ground-effect
performance of a rotorcraft rotor:" and include the outputs listed in the
Claim. First tag: rotorcraft-hover-ground-effect. Additional tags only:
hover-in-ground-effect, ige-power-reduction, ground-effect-factor,
ige-hover-ceiling, rotor-height-ratio. NEVER single generic words
(ground, effect, hover, power, helicopter). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present. Note: the word "ground effect"
may appear in the description but must always be paired with rotorcraft or
rotor tokens; never claim the fixed-wing induced drag ratio outputs.

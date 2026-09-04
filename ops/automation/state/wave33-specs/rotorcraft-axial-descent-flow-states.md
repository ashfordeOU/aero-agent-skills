# Wave-33 leaf spec: rotorcraft-axial-descent-flow-states (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-axial-descent-flow-states/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance,
  rotorcraft-hover-ground-effect, rotorcraft-forward-flight-performance,
  rotorcraft-vertical-climb-performance (rejects negative climb rates:
  Vc < 0 -> ValueError), rotorcraft-tail-rotor-sizing,
  rotorcraft-blade-flapping-dynamics, rotorcraft-autorotative-descent
  (energy-method power-off descent, Talbot empirical minimum descent
  rate in ft/min; its SKILL.md explicitly excludes momentum theory in
  descent, vortex-ring state and vertical zero-airspeed descent),
  rotorcraft-blade-element-hover-performance (coefficient polar).
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Classify the axial flow state of a helicopter rotor in vertical descent
from the descent-rate ratio w = Vd / v_h (vortex-ring/turbulent-wake
band 0 < w < 2 vs windmill-brake state w >= 2), compute the
windmill-brake-state induced velocity from the momentum-theory closed
form, the signed rotor power and torque in descent, and decide whether a
zero-shaft-power (ideal autorotative) equilibrium is reachable by
momentum theory on the physical windmill-brake branch via the
torque-reversal condition c = P_profile / (k T) versus v_h. Produces the
flow-state verdict, the descent induced velocity, the signed power and
torque, and the reachability verdict that proves momentum theory cannot
close to the autorotative equilibrium when c < v_h (the equilibrium
lives in the empirical vortex-ring/turbulent-wake regime).

Does NOT do: power-off minimum descent rate / energy-balance sink-rate
estimation (rotorcraft-autorotative-descent owns the empirical Talbot
correlation); hover or climb induced velocity (hover / vertical-climb
leaves); forward-flight inflow (rotorcraft-forward-flight-performance);
blade flapping or lag dynamics; fixed-wing spin autorotation
(stability-control/spin-recovery). Momentum theory is used ONLY on the
windmill-brake branch where it is valid; the vortex-ring band is
classified and flagged as momentum-invalid (empirical inflow is NOT
computed by this leaf - it is named in the body as the reason the band
is momentum-invalid, NASA TP-2005-213477 public-domain reference).

## Model (implement exactly)

Module constants:
- RHO_SL = 1.225 (kg/m3).
- G = 9.80665 (m/s2).
- K_INDUCED_DEFAULT = 1.15 (induced power factor for the worked case).
- PI = math.pi.

Functions (pure stdlib):

- axial_flow_state(descent_rate, hover_induced_velocity) -> one of
  "hover" | "vortex-ring-band" | "windmill-brake": Vd <= 0 -> "hover"
  (climb or still; this leaf is descent-only, reject Vd < 0 with
  ValueError per the sibling vertical-climb convention? NO: Vd = 0 is
  hover; Vd < 0 is climb -> ValueError "climb is not a descent state"),
  0 < Vd < 2 v_h -> "vortex-ring-band", Vd >= 2 v_h -> "windmill-brake".
  ValueError on v_h <= 0.
- windmill_brake_induced_velocity(descent_rate, v_h) -> v_i =
  Vd/2 - sqrt((Vd/2)^2 - v_h^2) for Vd >= 2 v_h (physical branch).
  ValueError if Vd < 2 v_h ("inside the vortex-ring band, momentum
  theory does not apply"). Returns the boundary identity
  v_i(2 v_h) = v_h exactly.
- rotor_descent_power(thrust_N, descent_rate, v_i, profile_power_W,
  k = K_INDUCED_DEFAULT) -> P = k T (-Vd + v_i) + P_profile (signed:
  negative means the rotor absorbs power from the airstream).
  ValueErrors on non-positive thrust/v_h-style inputs.
- rotor_descent_torque(power_W, rotor_speed_rad_s) -> Q = P / Omega
  (signed). ValueError on Omega <= 0.
- torque_reversal_condition(profile_power_W, thrust_N, k, v_h) ->
  dict {c, v_h, c_less_than_vh: bool, verdict, momentum_root_Vd}: c =
  P_profile / (k T); when c >= v_h the momentum windmill-brake branch
  has a zero-shaft-power root at Vd = c + v_h^2/c (>= 2 v_h, AM-GM);
  when c < v_h no momentum-theory zero-power solution exists (the
  formal crossing would require the non-physical branch), verdict
  "momentum-unreachable: the autorotative equilibrium lies in the
  empirical vortex-ring/turbulent-wake regime".
- vortex_ring_band_limits(v_h) -> (0, 2 v_h).
- descent_summary(thrust_N, disk_loading_or_rho_area_tip...) -> dict
  with flow_state, v_h (from thrust, rho, area: v_h = sqrt(T/(2 rho A))),
  band_limits, induced_velocity (None inside band), power_W, torque_Nm,
  momentum_root_reachable. Keep the signature list tight and documented.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Reference rotor (shared with the sibling hover/BET examples): R = 5.0 m,
m = 2200 kg (T = m g), rho = 1.225 kg/m3, A = pi R^2, v_h about
10.5887 m/s, P_profile = 122935 W, k = 1.15.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- v_h = sqrt(T/(2 rho A)) about 10.59 m/s.
- vortex_ring_band_limits -> (0, 21.18) m/s.
- At Vd = 2 v_h (21.18 m/s): windmill_brake_induced_velocity returns
  v_i = v_h exactly (boundary identity, diff 0.0).
- At Vd = 21.18: power about -139780 W (negative = absorbing).
- At Vd = 25: v_i about 5.857 m/s (0.553 v_h), P about -352019 W.
- At Vd = 30: v_i about 4.376 m/s (0.413 v_h), P about -512829 W,
  torque (Omega = Vtip/R with Vtip 220) Q = P/Omega about -11655 N m
  (torque opposes the engine).
- At Vd = 40: P about -794247 W.
- torque_reversal_condition: c = P_profile/(k T) about 4.955 m/s,
  c < v_h (4.955 < 10.589), verdict momentum-unreachable; the formal
  crossing Vd = c + v_h^2/c about 27.6 m/s would require the
  non-physical branch (its required v_i = Vd - c = v_h^2/c about
  22.6 m/s exceeds v_h, impossible on the windmill-brake branch).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: descent_rate < 0 (climb); v_h <= 0; windmill_brake_
  induced_velocity with Vd < 2 v_h; non-positive thrust; Omega <= 0.
- axial_flow_state boundaries: Vd = 0 -> "hover"; Vd just below 2 v_h
  -> "vortex-ring-band"; Vd = 2 v_h exactly -> "windmill-brake";
  Vd > 2 v_h -> "windmill-brake".
- Boundary identity: windmill_brake_induced_velocity(2 v_h, v_h) == v_h
  to 1e-9; as Vd -> infinity, v_i/v_h -> 0 like v_h/Vd (asymptote check
  at Vd = 5 v_h gives v_i/v_h about 0.2087 -> 1/w at w = 5).
- Signed power: P negative across the windmill-brake band for the
  worked rotor (profile power never overcomes the descent term).
- Torque-reversal math: for a synthetic rotor with c >= v_h (e.g.
  P_profile large enough), the momentum root Vd = c + v_h^2/c is >= 2
  v_h and the function reports reachable; for the worked rotor c < v_h
  reports momentum-unreachable.
- Determinism: identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-rotorcraft-axial-descent-flow-states.yaml)

Query 1 (copy verbatim):
  "classify the rotor axial descent flow state from the vortex ring band boundary at twice the hover induced velocity and the windmill brake state momentum branch"
  intent: "flight-mechanics; rotorcraft axial descent flow-state classification vortex-ring band windmill-brake"
  expected_skill: "flight-mechanics/performance/rotorcraft-axial-descent-flow-states"
Query 2 (copy verbatim):
  "compute the windmill brake state descent induced velocity and signed rotor power and the torque reversal condition for the momentum theory autorotative equilibrium"
  intent: "flight-mechanics; rotorcraft descent induced velocity, signed power, torque-reversal momentum reachability"
  expected_skill: "flight-mechanics/performance/rotorcraft-axial-descent-flow-states"
Task ids: w33-rotorcraft-axial-descent-flow-states-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must classify the axial flow state
of a rotor in vertical descent:" and include the outputs in the Claim.
First tag: rotorcraft-axial-descent-flow-states. Additional tags ONLY:
axial-descent-flow, vortex-ring-state, windmill-brake-state,
descent-induced-velocity, torque-reversal, momentum-theory-reachability.
NEVER single generic words (descent, rotor, flow, state, vortex,
torque, power, momentum). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): autorotative descent, minimum
descent rate, energy balance, Talbot, sink rate in ft/min
(rotorcraft-autorotative-descent); climb induced velocity, vertical
climb (vertical-climb); hover power, figure of merit, disk loading
(hover leaf); forward flight, Glauert, parasite power; blade flapping,
Lock number, coning; ground resonance, lead-lag. The tokens
"vortex-ring", "windmill-brake", "axial descent", "torque reversal" are
this leaf's own. NOTE: the word "autorotation" may appear only in the
reachability verdict phrasing ("the autorotative equilibrium"), never as
a method claim.

Tags: [rotorcraft-axial-descent-flow-states, axial-descent-flow,
vortex-ring-state, windmill-brake-state, descent-induced-velocity,
torque-reversal, momentum-theory-reachability]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-autorotative-descent (the
empirical power-off descent sibling; this leaf's torque-reversal verdict
explains why momentum theory cannot close to the autorotative
equilibrium),
flight-mechanics/performance/rotorcraft-vertical-climb-performance,
flight-mechanics/performance/rotorcraft-hover-performance.

Ledger Standard: far-29.

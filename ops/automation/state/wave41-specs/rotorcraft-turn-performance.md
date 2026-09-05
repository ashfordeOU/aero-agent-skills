# Wave-41 leaf spec: rotorcraft-turn-performance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-turn-performance/
- Pack: performance (verified present at prep with the rotorcraft
  performance siblings rotorcraft-hover-performance, rotorcraft-forward-
  flight-performance, rotorcraft-vertical-climb-performance, rotorcraft-
  autorotative-descent, rotorcraft-axial-descent-flow-states, rotorcraft-
  hover-ground-effect, rotorcraft-range-endurance, rotorcraft-tail-rotor-
  sizing and the fixed-wing turn-performance; leaf rotorcraft-turn-
  performance absent at prep). Whole-tree greps at prep: "rotorcraft.*turn",
  "banked turn" and "turn performance" over skills/flight-mechanics return
  hits ONLY in skills/flight-mechanics/SKILL.md (the family router), the
  turn-performance leaf and its scripts, and prose in the rotorcraft-hover-
  ground-effect scripts; no rotorcraft leaf solves a banked-turn state.
  Corpus grep: tasks turn1 and turn2 route to the fixed-wing turn-
  performance; no rotorcraft banked-turn task exists in eval/hit1-corpus.
  GENUINE rotorcraft n > 1 gap (fresh probe): the banked level turn of a
  helicopter at load factors above one, with the rotor thrust above weight
  and the turning induced velocity, is owned by no leaf. Fences within the
  pack (quoted from the leaves at prep, read in full):
  - turn-performance (fixed-wing lift model, no rotor inflow): its
    frontmatter claims "compute sustained turn performance for a fixed-wing
    aircraft: derive the load factor from the bank angle or the bank angle
    from the load factor, compute the turn rate and turn radius at a given
    airspeed, and check whether the available thrust sustains the turn
    against the increased drag"; its body gives "Load factor from bank
    angle: n = 1 / cos(phi), for a level coordinated turn" and "Sustained
    turn: the drag in the turn is D_turn = D_level * n (level-flight drag
    scaled by the load factor); the turn is sustained when T_available >=
    D_turn". The whole method runs on the fixed-wing lift and drag model:
    no rotor disk, no induced-velocity solve, no power breakdown exists in
    its functions, body or contract tests, and its "Using a load factor
    below 1" pitfall shows the n domain starts at 1 with no rotor-power
    source for n. The shared kinematics omega = g * sqrt(n^2 - 1) / V and
    R = V^2 / (g * sqrt(n^2 - 1)) with g = 9.80665 are standard level-turn
    geometry this leaf reuses for the rotorcraft maneuver, never re-derives
    as a claim.
  - rotorcraft-forward-flight-performance (level flight only, thrust =
    weight): its frontmatter claims "compute the forward-flight power
    required of a rotorcraft rotor with momentum-theory inflow: the Glauert
    induced velocity at a given flight speed, the induced power, the
    parasite power from the equivalent flat-plate drag area, the profile
    power from rotor blade solidity and tip speed, and the total power,
    then find the best endurance speed (minimum total power) and the best
    range speed"; its body fixes the state with "thrust T = weight from
    mass" and spells "Glauert inflow at flight speed V:
    v = T / (2 * rho * A * sqrt(V**2 + v**2))", "Induced power: P_i = T *
    v", "Profile power: P_prof = (1/8) * rho * sigma * Cd0 * A * V_tip**3"
    and "Total power: P_total = k * T * v + P_prof + P_par" with the
    induced power factor k = K_DEFAULT = 1.15. Read in full at prep: no
    load factor above one, no banked disk, no n-times-weight thrust
    anywhere in the body or contract tests; the power terms sit at the
    level-flight thrust only. This leaf supplies the power conventions this
    spec reuses: the Glauert fixed-point form, the (1/8) profile model and
    k = 1.15, and the worked rotor (R = 5.0 m, m = 2200 kg, rho = 1.225,
    sigma = 0.08, Cd0 = 0.012, tip 220 m/s, f = 2.2 m2, k = 1.15).
  - rotorcraft-hover-performance (zero flight speed only): "The rotor
    thrust equals the rotorcraft weight in hover: T = m * g0" with "Ideal
    induced velocity (momentum theory, uniform inflow): v_i = sqrt(T /
    (2 * rho * A))"; the hover state at speed zero is its claim, shared
    only as the v_h reference point and V = 0 limit here.
  - rotorcraft-vertical-climb-performance (axial climb only): "Climb
    induced velocity at vertical climb rate Vc: v_i = -Vc/2 + sqrt((Vc/2)^2
    + v_h^2)" with "vertical climb only with climb rates zero or positive,
    and no wake distortion modeling in descending flight (the model
    rejects negative climb rates)"; axial flow, no forward speed, no bank.
  - rotorcraft-autorotative-descent (power-off descent only): the
    energy-method sink rate and the Talbot-Schoers empirical minimum
    descent rate after engine failure; autorotation is its claim and is
    not touched here.
  - rotorcraft-axial-descent-flow-states (vertical descent only): the
    vortex-ring band and windmill-brake momentum states of axial descent
    with signed rotor power; no forward flight component.
  - rotorcraft-hover-ground-effect (IGE hover only) and rotorcraft-range-
    endurance (fuel closure on the level power curve): both consume the
    level-flight or hover power, never a banked-disk solve.
- Standards id: far-29 (public-domain US government work per standards-
  map.yaml; the rotorcraft performance siblings all reference far-29).
  Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the banked-turn performance of a helicopter rotor from momentum
theory at load factors above one: the rotor thrust rises to n times the
weight in the level turn, the generalized turning induced velocity follows
from the Glauert-style disk momentum solve at that thrust, the turn power
breaks down into the induced, profile and parasite terms, the sustained
load factor follows from a given available power at the turn speed, and
the bank angle, turn rate and turn radius close the maneuver. Produces the
turn thrust, the turning induced velocity, the turn power breakdown, the
power-sustained load factor with its bank angle, turn rate and radius that
gate a rotorcraft maneuvering-power check at a chosen speed and density.
Does NOT do: fixed-wing bank-angle and thrust-drag sustained-turn analysis
(turn-performance); the level-flight power curve and its best endurance
and range speeds (rotorcraft-forward-flight-performance); hover power and
figure of merit (rotorcraft-hover-performance); axial vertical climb and
maximum rate of climb (rotorcraft-vertical-climb-performance); power-off
autorotative descent (rotorcraft-autorotative-descent); axial descent flow
states (rotorcraft-axial-descent-flow-states); ground effect or fuel
closure (rotorcraft-hover-ground-effect, rotorcraft-range-endurance).
Deterministic momentum-theory core only: uniform inflow, fixed iteration
schedules, no RNG, no blade-element sections, no compressibility, no
transient or out-of-trim maneuver dynamics.

## Model (implement exactly)

Uniform-inflow momentum theory for a steady coordinated level turn at true
airspeed V and load factor n >= 1. The rotor disk banks so the thrust axis
carries the resultant n*W; the free stream stays in the disk plane (the
axial free-stream component is the small disk angle of attack term that
the level-flight Glauert convention of the rotorcraft-forward-flight-
performance leaf also neglects), so the inflow equation keeps the
level-flight form at the raised thrust:

    T = n * W = 2 * rho * A * v_i * sqrt(V**2 + v_i**2),  v_i >= 0

with W = m * g0 the weight, A = PI * R^2 the disk area and v_i the turning
induced velocity. The left side rises with v_i (f strictly increasing on
v_i >= 0, f(0) = -n*W < 0), so the root is unique; it is found by a
FIXED-COUNT bisection on [0.0, sqrt(n * W / (2 * rho * A))] (BISECT_ITER =
120 iterations, return the final midpoint, no tolerance-based early exit).
At n = 1 this reproduces the level-flight Glauert value of the forward-
flight leaf exactly, and at V = 0 it returns sqrt(n * W / (2 * rho * A)) =
sqrt(n) * v_h, the hover identity of the hover leaf at n = 1.

Functions (pure stdlib, math only):
- thrust_for_turn(load_factor, weight) -> float load_factor * weight in N;
  ValueError if load_factor < 1.0 or weight <= 0.
- generalized_induced_velocity(load_factor, weight, area, rho, speed) ->
  float v_i in m/s, the fixed-count bisection root of 2 * rho * area *
  v_i * sqrt(speed**2 + v_i**2) - load_factor * weight described above;
  ValueError if load_factor < 1.0, weight <= 0, area <= 0, rho <= 0 or
  speed < 0. Speed zero is valid (returns the sqrt(n) * v_h value).
- induced_power(load_factor, weight, induced_velocity, k = K_DEFAULT) ->
  float k * load_factor * weight * induced_velocity in W (the induced
  power factor k = 1.15 convention of the hover and forward-flight
  leaves); ValueError if k <= 0, load_factor < 1.0, weight <= 0 or
  induced_velocity < 0.
- profile_power(rho, area, solidity, drag_coefficient, tip_speed) ->
  float (1/8) * rho * solidity * drag_coefficient * area * tip_speed**3 in
  W, the average-section-drag model shared verbatim with the hover and
  forward-flight leaves; the turn model keeps the rotor speed fixed so the
  profile power of the turn equals the level-flight value. ValueError if
  any input is <= 0.
- parasite_power(rho, speed, flat_plate_area) -> float 0.5 * rho *
  speed**3 * flat_plate_area in W; ValueError if rho <= 0, speed < 0 or
  flat_plate_area < 0.
- turn_power(load_factor, weight, area, rho, speed, solidity,
  drag_coefficient = CD0_DEFAULT, tip_speed, flat_plate_area,
  k = K_DEFAULT) -> dict {"load_factor", "thrust", "induced_velocity",
  "induced_power", "profile_power", "parasite_power", "total_power"},
  computed in the fixed order thrust_for_turn, generalized_induced_
  velocity, induced_power, profile_power, parasite_power, then total =
  induced + profile + parasite; dict keys exactly as documented; total
  power is strictly increasing in load_factor (both n*W and v_i rise with
  n); propagates every component ValueError.
- sustained_load_factor(available_power, weight, area, rho, speed,
  solidity, drag_coefficient = CD0_DEFAULT, tip_speed, flat_plate_area,
  k = K_DEFAULT, ceiling = N_CEILING) -> dict {"load_factor",
  "bank_angle", "induced_velocity", "induced_power", "profile_power",
  "parasite_power", "total_power", "note"}. h(n) = total power at n minus
  available power is strictly increasing, so a FIXED-COUNT bisection on
  [1.0, ceiling] (BISECT_ITER = 120 iterations) finds the power-sustained
  load factor n_s: the largest n whose turn power the available power
  covers, and the required power at the returned n equals the available
  power. ValueError when the total power at n = 1 exceeds available_power
  (level flight cannot be sustained at this speed) and when
  available_power <= 0 or ceiling <= 1.0. When the total power at n =
  ceiling stays below available_power, return load_factor = ceiling with
  note "power-excess above ceiling" (the bracket convention of the
  rotorcraft-vertical-climb-performance leaf); otherwise note
  "power-limited". bank_angle = acos(1 / load_factor) in rad, the bank of
  the level turn. Non-positive weight, area, rho, solidity,
  drag_coefficient, tip_speed or k raise ValueError; speed < 0 raises.
- bank_from_load_factor(load_factor) -> float acos(1 / load_factor) in
  rad; ValueError if load_factor < 1.0 (the n >= 1 domain of the level
  turn).
- turn_rate(load_factor, speed) -> float G0 * sqrt(load_factor**2 - 1) /
  speed in rad/s with G0 = 9.80665 m/s2, the standard level-turn
  kinematics shared with the turn-performance leaf; ValueError if
  load_factor < 1.0 or speed <= 0.
- turn_radius(load_factor, speed) -> float speed**2 / (G0 *
  sqrt(load_factor**2 - 1)) in m; ValueError if load_factor < 1.0 or
  speed <= 0.
- max_bank_from_power(available_power, weight, area, rho, speed,
  solidity, drag_coefficient = CD0_DEFAULT, tip_speed, flat_plate_area,
  k = K_DEFAULT, ceiling = N_CEILING) -> float acos(1 / load_factor) in
  rad from one sustained_load_factor solve (no double iteration); returns
  the bank angle the power-sustained load factor implies and propagates
  the same ValueErrors.
Module constants: G0 = 9.80665, K_DEFAULT = 1.15, CD0_DEFAULT = 0.012,
N_CEILING = 10.0, BISECT_ITER = 120.

Identities to test: at load factor 1 and any speed the total power equals
the rotorcraft-forward-flight-performance total at the same speed (both
models share the fixed point and the power conventions; at 60 m/s on the
worked rotor the level total is 460336 W in both leaves); at speed 0 the
inflow returns sqrt(n) * v_h (so n = 2 gives sqrt(2) * 10.5887 = 14.9747);
turn rate times turn radius equals the speed V exactly
(omega * R = g*sqrt(n^2-1)/V * V^2/(g*sqrt(n^2-1)) = V); cos(bank) = 1/n;
the generalized inflow at fixed n falls as speed grows; the required turn
power and the sustained load factor are monotone in their arguments.

## Worked example

Shared worked rotor, identical to the rotorcraft-forward-flight-
performance and rotorcraft-hover-performance worked rotors: R = 5.0 m
(A = 78.5398 m2), m = 2200 kg so W = m * g0 = 21574.63 N, rho = 1.225
kg/m3, solidity sigma = 0.08, Cd0 = 0.012, tip speed 220 m/s,
f = 2.2 m2, k = 1.15. Sea level.

Hover reference (V = 0): v_h = sqrt(W / (2 * rho * A)) = 10.5887 m/s at
n = 1; at n = 2 the turn inflow is sqrt(2) * v_h = 14.9747 m/s.

Banked turn at n = 2.0, V = 60 m/s (module outputs): thrust
T = 43149.3 N, turning induced velocity 3.73017 m/s, induced power
185097 W, profile power 122935 W, parasite power 291060 W, total turn
power 599092 W; bank angle acos(1/2) = 1.0472 rad (60 deg), turn rate
0.283094 rad/s, turn radius 211.944 m. The induced velocity at n = 2 is
about twice the level-flight value 1.86778 m/s at the same speed, and the
level-flight total power of 460336 W (the n = 1 identity, matching the
forward-flight leaf worked example) grows by about 138 kW to sustain the
2 g turn at 60 m/s. A second state, n = 1.5 at V = 40 m/s: induced
velocity 4.18175 m/s, induced power 155629 W, total 364804 W. A third
inflow probe, n = 3.0 at V = 60 m/s: induced velocity 5.58195 m/s.

Power-sustained maneuver: available power 600000 W at V = 60 m/s gives
sustained load factor 2.00491, bank angle 1.04861 rad (60.081 deg),
turning induced velocity 3.73929 m/s, induced power 186005 W, total power
at the sustained point 600000 W, turn rate 0.28402 rad/s and turn radius
211.253 m; max_bank_from_power returns 1.04861 rad. With available power
450000 W at V = 40 m/s the sustained load factor falls to 1.86867
(rate 0.387015 rad/s, radius 103.355 m), and at the same power and
V = 50 m/s it falls further to 1.69094 (rate 0.267439 rad/s, radius
186.959 m), the parasite V**3 growth cutting the sustained load factor as
the speed rises at fixed power. Run your module and take the real outputs
as assert targets; the anchors above are prep-verified bounds, computed by
running the prep anchor script /tmp/w41spec/anchor_rotorcraft_turn.py
(prep-verified by stdlib math).

## Validation list (contract test must include)

- generalized_induced_velocity(1.0, 21574.63, 78.5398, 1.225, 60.0) =
  1.86778 m/s within 1e-4 (the level-flight Glauert identity; the
  forward-flight leaf rounds to 1.868); speed 0 at n = 1 returns 10.5887
  within 1e-4.
- generalized_induced_velocity(2.0, 21574.63, 78.5398, 1.225, 60.0) =
  3.73017 within 1e-4 (spec bound 3.5 to 4.0); (1.5, ... , 40.0) = 4.18175
  within 1e-4 (bound 3.9 to 4.5); (3.0, ... , 60.0) = 5.58195 within
  1e-4; speed 0 at n = 2 returns 14.9747 within 1e-4 (bound 14.8 to
  15.2), equal to sqrt(2) times the n = 1 hover value.
- generalized_induced_velocity fixed-n monotone decrease in speed
  (60 m/s below the 40 m/s value at the same n).
- ValueErrors: generalized_induced_velocity at load_factor 0.99, weight 0,
  area 0, rho 0, speed -1.
- thrust_for_turn(2.0, 21574.63) = 43149.26 within 1e-2; ValueError at
  load_factor 0.99 and weight 0.
- profile_power(1.225, 78.5398, 0.08, 0.012, 220.0) = 122935 W within
  1e-1 (bound 115000 to 130000); parasite_power(1.225, 60.0, 2.2) =
  291060 W within 1e-1 (bound 280000 to 305000); ValueError on
  non-positive inputs.
- turn_power(2.0, 21574.63, 78.5398, 1.225, 60.0, 0.08, 0.012, 220.0,
  2.2): induced_velocity 3.73017, induced_power 185097 (bound 170000 to
  200000), total_power 599092 (bound 570000 to 630000), dict keys exactly
  load_factor, thrust, induced_velocity, induced_power, profile_power,
  parasite_power, total_power.
- n = 1 identity: turn_power(1.0, ..., 60.0) total_power 460336 within
  1e-1, equal to the rotorcraft-forward-flight-performance worked total at
  60 m/s; total_power monotone increasing in load_factor.
- sustained_load_factor(600000.0, 21574.63, 78.5398, 1.225, 60.0, 0.08,
  0.012, 220.0, 2.2): load_factor 2.00491 (bound 1.95 to 2.06), bank_angle
  1.04861 rad within 1e-4, note "power-limited", total_power 600000 within
  1e-1 (round trip: turn_power at the returned n reproduces the available
  power).
- sustained_load_factor(450000.0, ..., 40.0) load_factor 1.86867 and
  (450000.0, ..., 50.0) load_factor 1.69094 within 1e-4; the sustained
  load factor falls as the speed rises at fixed available power.
- sustained_load_factor ValueError when the available power sits below the
  n = 1 total power at the speed (level flight not sustainable) and at
  available_power 0; excess case: available power above the total power at
  n = ceiling returns load_factor 10.0 with note "power-excess above
  ceiling" (compute the module boundary value).
- turn_rate(2.0, 60.0) = 0.283094 rad/s within 1e-5 (bound 0.27 to 0.30);
  turn_radius(2.0, 60.0) = 211.944 m within 1e-3 (bound 200 to 225);
  omega * R = V identity; bank_from_load_factor(2.0) = 1.0472 within 1e-5;
  cos(bank) = 1/n identity; ValueErrors at load_factor 0.99 and speed 0.
- max_bank_from_power(600000.0, ..., 60.0) = 1.04861 rad within 1e-4,
  equal to acos(1 / n_sustained) from the sustained solve.
- Determinism: two identical calls return bit-identical values; fixed
  note strings; every ValueError class above covered.

## Corpus fragment (eval/hit1-wave41-rotorcraft-turn-performance.yaml)

Query 1 (copy verbatim, router-verified at prep with scores 33.0 top-1 on
the wave-41 pre-merge simulation, 1120/1120 Hit@1, no pre-existing-task
theft):
  "compute the helicopter banked-turn power from momentum theory: the turning-flight-inflow at the n-times-weight thrust, the banked-turn-power breakdown into induced, profile and parasite power, and the sustained-load-factor the available power supports at the turn speed"
  intent: "flight-mechanics; rotorcraft banked turn inflow and power breakdown at n times weight"
  expected_skill: "flight-mechanics/performance/rotorcraft-turn-performance"
Query 2 (copy verbatim, score 29.0 at prep):
  "find the sustained-load-factor of the helicopter banked turn from the available power against the turning-flight-inflow power required, and the power-limited-bank-angle with the turn rate and turn radius of the rotorcraft-turn-performance model"
  intent: "flight-mechanics; rotorcraft sustained load factor from available power and the power-limited bank angle"
  expected_skill: "flight-mechanics/performance/rotorcraft-turn-performance"
Task ids: w41-rotorcraft-turn-performance-1 and -2. Both queries embed the
leaf's own hyphenated tag tokens (turning-flight-inflow, banked-turn-
power, sustained-load-factor, power-limited-bank-angle, rotorcraft-turn-
performance) and lead with helicopter and banked-turn terms so the
fixed-wing turn-performance tasks turn1 and turn2 keep routing to their
owner, as the prep simulation confirmed.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description EXACTLY (copy verbatim; 908 chars, 126 words, opens with the
action verb, no em dash, no "classified", router-verified at prep):
"Use when you must determine the banked-turn power of a helicopter rotor from momentum theory: the turning-flight-inflow solved for the n-times-weight thrust of the banked level turn, the banked-turn-power breakdown into induced, profile and parasite terms, the sustained-load-factor an available power supports at the turn speed, the power-limited-bank-angle, and the turn rate and radius of the sustained maneuver. Produces the turn induced velocity, the turn power breakdown, the sustained-load-factor, bank angle, turn rate and turn radius that gate a rotorcraft maneuvering-power check at a chosen density. Momentum theory only: level turns above one g, uniform inflow; not the fixed-wing thrust-drag method, not the level-flight power curve, not hover, climb or autorotation. Trigger: helicopter banked turn, turning-flight inflow, rotorcraft turn power, sustained load factor, power-limited bank angle."
First tag: rotorcraft-turn-performance. Additional tags ONLY:
turning-flight-inflow, banked-turn-power, sustained-load-factor,
power-limited-bank-angle. NEVER single generic words (turn, bank, power,
load, factor, rate, radius, angle, inflow, performance, maneuver,
helicopter alone) as tags.

FORBIDDEN TOKENS (belong to siblings; keep them out of the description,
tags and corpus queries): airspeed, bank-angle, load-factor, turn-rate,
turn-radius, sustained-turn, maneuvering (turn-performance); glauert-
inflow, parasite-power, best-endurance-speed, best-range-speed,
equivalent-flat-plate-area, power-sweep (rotorcraft-forward-flight-
performance); figure-of-merit, hover-power, rotor-disk-loading,
rotor-induced-velocity (rotorcraft-hover-performance); vertical-rate-of-
climb, climb-induced-velocity, rotorcraft-climb-power, vertical-climb-
momentum-theory (rotorcraft-vertical-climb-performance);
autorotative-descent, power-off-descent, minimum-descent-rate
(rotorcraft-autorotative-descent); vortex-ring-state, windmill-brake-
state, torque-reversal, descent-induced-velocity (rotorcraft-axial-
descent-flow-states); ground-effect, ige-hover (rotorcraft-hover-ground-
effect); rotorcraft range endurance terms (rotorcraft-range-endurance).
The hyphenated tokens sustained-load-factor and power-limited-bank-angle
are THIS leaf's own compound terms; do not write them with spaces
("sustained load factor", "power limited bank angle") in the description,
because the spaced form tokenizes into the generic words that belong to
the fixed-wing leaf.

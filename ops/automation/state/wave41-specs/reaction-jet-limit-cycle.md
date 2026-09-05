# Wave-41 leaf spec: reaction-jet-limit-cycle (space-systems, adcs pack)

- Path: skills/space-systems/adcs/reaction-jet-limit-cycle/
- Pack: adcs (verified present at prep with the 12 sibling leaves
  attitude-control-sizing, attitude-determination-quest,
  attitude-determination-triad, control-momentum-gyro,
  gravity-gradient-stabilization, gyro-allan-variance,
  magnetometer-calibration, magnetorquer-control, pointing-error-budget,
  reaction-wheel-control, star-tracker and sun-pointing). Closest
  siblings and fences:
  - cold-gas-thruster (propulsion/rocket): hardware Isp and geometry,
    no attitude demand. Its frontmatter claim is "size and assess a cold
    gas thruster for spacecraft reaction control: compute the choked
    mass flow through the nozzle throat from the plenum pressure and
    temperature, the thrust from the mass flow and specific impulse, the
    tank gas mass from the plenum volume and pressure, the isothermal
    blowdown time constant and pressure history, the operating time to
    the minimum usable pressure, and the total impulse available over
    the blowdown" and its body states the boundary: "this leaf is the
    gas thruster flow and blowdown model, not a tank structural sizer
    and not an attitude control law" with Isp treated as an input fixed
    at 40 to 75 s for nitrogen. It owns how much impulse a given gas
    mass yields, not how many impulses attitude hold demands.
  - mission-delta-v-budget (space-systems/mission-design): no attitude
    term. Its claim is to "sum the launch insertion, orbit transfer,
    plane change, station keeping, and deorbit contributions, apply a
    margin allocation, and convert the budget into propellant mass with
    the Tsiolkovsky rocket equation from the dry mass and the specific
    impulse"; its station keeping contribution is the orbital position
    delta-v (about 50 m/s per year for geostationary), never an RCS
    attitude-hold term, and its propellant conversion is the rocket
    equation, not a pulse count.
  - reaction-wheel-control (adcs): wheels, not jets. Its claim is to
    "command wheel torques from quaternion error feedback and body rate
    with PD gains, integrate wheel momentum with the body rate transport
    term, clip torque commands and flag wheel momentum saturation, and
    compute the momentum desaturation command with its magnetorquer
    dipole estimate"; the body states "this leaf is the control law and
    momentum management, not the sizing, not the detumbling law, not the
    attitude determination" and no propellant term appears anywhere in
    the file. Desaturation is by magnetorquer dipole, not by jets.
  - attitude-control-sizing (adcs): wheel-class actuator sizing only:
    "compute the momentum wheel capacity for a commanded slew, check the
    detumble rate against the allowed rate, and verify the wheel
    momentum margin"; no RCS propellant demand.
  - bang-bang-control (gnc-autonomy/optimal-control): trajectory control,
    not RCS attitude hold. Its claim is the "time-optimal bang-bang
    control of a double integrator: the switching curve s = x + v|v|/(2a)
    ... the exact rest-to-rest maneuver time T* = 2*sqrt(d/a)" for
    "single-axis attitude slew and translation bang-bang assessments";
    it sizes one minimum-time maneuver, it does not count limit-cycle
    firings over a mission life and owns no propellant.
  - pointing-error-budget (adcs): treats the control deadband as a
    pointing error contributor in an RSS budget (its corpus tasks ask
    for "the 1 sigma determination, gyro, control deadband, jitter and
    thermal contributors"), not as a firing-rate driver for propellant.
  Whole-tree greps at prep: "limit cycle", "bang-bang", "reaction jet"
  and "rcs propellant" = 0 hits in skills/space-systems (the only
  bang-bang leaf in the tree is gnc-autonomy/optimal-control/bang-bang-
  control, trajectory control as quoted above); in eval/hit1-corpus.yaml
  the only "limit cycle" tasks route to
  flight-test-operations/flutter/limit-cycle-oscillation (aeroelastic
  LCO) and the only "deadband" tasks route to pointing-error-budget
  (error contributor) and to the geostationary east-west deadband drift
  cycle task (longitude-box orbit position station keeping, not attitude
  hold). GENUINE GAP (fresh probe): nothing in the tree computes the
  propellant demand of an RCS attitude-hold limit cycle from the
  deadband geometry and control authority.
- Standards id: ecss (reference-only; ecss exists in standards-map.yaml).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Estimate the RCS attitude-hold propellant demand from the bang-bang
deadband limit cycle of reaction-jet control on one or three axes: the
control angular acceleration from the control torque and axis inertia,
the angular rate at the deadband crossing, the firing duration of each
braking pulse at a deadband edge, the linear delta-V and the propellant
mass per pulse and per limit-cycle (two pulses, one per edge), the
aggregate cycle period, the cycle count and pulse count over the mission
life, and the three-axis lifetime propellant total with an activity duty
factor. Produces the per-axis limit-cycle state (rate, pulse time,
period, cycles, pulses, lifetime propellant) and the three-axis
propellant total that gate whether reaction-jet attitude hold is
propellant-feasible for the life and that feed the ADCS propellant
demand line no other leaf owns. Does NOT do: thruster hardware flow,
Isp, blowdown, tank gas mass or total impulse available (cold-gas-
thruster); the orbital mission delta-v budget, its margin allocation or
the Tsiolkovsky propellant conversion (mission-delta-v-budget); wheel
torque commands, momentum saturation, desaturation or magnetorquer
dipoles (reaction-wheel-control); wheel slew momentum, detumble checks
or wheel margins (attitude-control-sizing); the minimum-time switching
curve of a single slew (bang-bang-control in gnc-autonomy); deadband as
a pointing-error-budget contributor (pointing-error-budget).
Deterministic aggregate estimate only: disturbance torques, minimum
impulse bits, valve dynamics and coupled multiaxis firing sequences are
out of scope, and the fixed-force fixed-Isp assumption means blowdown
effects belong to the hardware leaf.

## Model (implement exactly)

Wertz-class aggregate estimate, paraphrase, deterministic stdlib math
only. Deadband is +/-h about the reference attitude, h the half-angle in
rad. At each deadband edge the crossing rotation is arrested by one
braking pulse of one thruster at force F_t. The estimate idealizes each
half oscillation of the limit cycle as a constant-torque arc under the
control acceleration covering the full deadband width 2h from rest
(2h = alpha_c * tau^2 / 2, so tau = 2 * sqrt(h / alpha_c) per half
cycle), which pins the aggregate cycle period at exactly
T_cycle = 4 * sqrt(h / alpha_c); the detailed coast/fire sequencing and
the disturbance that sustains the cycle are replaced by this aggregate,
documented here as the model idealization. The characteristic crossing
rate omega = sqrt(2 * alpha_c * h) is the constant-torque rate gained
from rest over the half-angle h (v^2 = 2 a s with s = h), and the
braking pulse that removes it lasts t_fire = omega / alpha_c (rate
change alpha_c * t_fire = omega). Each pulse is a fixed linear impulse
F_t * t_fire on the spacecraft mass m, and propellant follows from the
impulse at the fixed specific impulse (no blowdown: F_t and Isp are
constants of the demand model; their hardware variation is the
cold-gas-thruster leaf's domain).

Functions (pure stdlib, math only):
- control_accel(torque_Nm, inertia_kgm2) -> float torque / inertia, the
  control angular acceleration alpha_c in rad/s^2. ValueError if
  torque_Nm <= 0 or inertia_kgm2 <= 0.
- limit_cycle_rate(alpha_c, h_rad) -> float sqrt(2 * alpha_c * h_rad),
  the angular rate omega in rad/s at the deadband crossing. ValueError
  if alpha_c <= 0 or h_rad <= 0.
- pulse_time(omega_rad_s, alpha_c) -> float omega / alpha_c, the firing
  duration t_fire in s of each braking pulse. ValueError if
  omega_rad_s <= 0 or alpha_c <= 0.
- pulse_delta_v(thrust_N, t_fire_s, mass_kg) -> float thrust * t_fire /
  mass, the linear delta-V in m/s of one pulse. ValueError if any input
  <= 0.
- pulse_propellant(thrust_N, t_fire_s, isp_s) -> float thrust * t_fire
  / (isp * G0) with G0 = 9.80665 m/s^2, the propellant mass in kg of
  one pulse. ValueError if any input <= 0.
- delta_v_per_cycle(thrust_N, t_fire_s, mass_kg) -> float
  2 * thrust * t_fire / mass, two pulses per cycle. ValueErrors as
  above.
- propellant_per_cycle(thrust_N, t_fire_s, isp_s) -> float
  2 * thrust * t_fire / (isp * G0). ValueErrors as above.
- cycle_period(h_rad, alpha_c) -> float 4 * sqrt(h_rad / alpha_c), the
  aggregate limit-cycle period T_cycle in s (model idealization above).
  ValueError if h_rad <= 0 or alpha_c <= 0.
- cycles_over_life(life_s, period_s) -> float life / period, the cycle
  count over an active duration. ValueError if life_s <= 0 or
  period_s <= 0.
- propellant_budget(axes, life_s, duty_factor = 1.0) -> dict
  {"axes": {name: {...}}, "propellant_total_kg": float}: one dict entry
  per axis in the input list, each input axis {"name", "mass_kg",
  "inertia_kgm2", "torque_Nm", "thrust_N", "isp_s",
  "deadband_half_rad"}; computes per axis alpha_c, omega, t_fire, the
  per-pulse and per-cycle delta-V and propellant, T_cycle, the cycle
  and pulse counts over the active duration duty_factor * life_s, and
  the lifetime propellant cycles * propellant_per_cycle; the total sums
  the per-axis lifetime propellant. Per-axis output dict keys EXACTLY:
  "alpha_c_rad_s2", "omega_rad_s", "t_fire_s",
  "delta_v_per_pulse_m_s", "delta_v_per_cycle_m_s",
  "propellant_per_pulse_kg", "propellant_per_cycle_kg",
  "cycle_period_s", "cycles", "pulses", "propellant_life_kg".
  ValueError if axes is empty, life_s <= 0, or duty_factor outside
  (0, 1]; component ValueErrors propagate.
Module constant: G0 = 9.80665 (standard gravity, m/s^2).

Identities to test: t_fire equals sqrt(2 * h / alpha_c) exactly (the
omega / alpha_c form collapses); delta_v_per_cycle = 2 * pulse_delta_v;
propellant_per_cycle = 2 * pulse_propellant; per-axis lifetime
propellant = cycles * propellant_per_cycle; propellant_budget total at
duty 0.5 is exactly half the duty 1.0 total; omega is monotone
increasing in alpha_c and in h; t_fire is monotone decreasing in
alpha_c; T_cycle is monotone decreasing in alpha_c and increasing in h;
omega, t_fire and the propellant numbers are independent of the
spacecraft mass except through the delta-V terms; propellant per cycle
is independent of inertia, torque and mass (it depends only on thrust,
Isp and t_fire). Deterministic, no RNG.

## Worked example

A 1000 kg spacecraft, axis inertia I = 120 kg m^2 per axis, thruster
force F_t = 1 N at Isp = 60 s (cold gas class), deadband +/-0.1 deg
(h = 0.1 deg in rad = 1.74533e-3 rad), 2-year mission life = 63,115,200
s (365.25-day years), duty factor 1.0 (all three axes hold continuously).
Example geometry: each braking pulse is one 1 N thruster firing at
moment arm L = 1.0 m about its axis, so the control torque per axis is
T_c = F_t * L = 1.0 N m (documented example assumption; the model takes
T_c as an input and the hardware leaf owns the real geometry).

- alpha_c = T_c / I = 1.0 / 120 = 8.33333e-3 rad/s^2.
- omega = sqrt(2 * alpha_c * h) = sqrt(2 * 8.33333e-3 * 1.74533e-3) =
  5.39341e-3 rad/s = 0.30902 deg/s at the deadband crossing.
- t_fire = omega / alpha_c = 5.39341e-3 / 8.33333e-3 = 0.647209 s per
  braking pulse (also sqrt(2 h / alpha_c) = 0.647209 s).
- Linear impulse per pulse = F_t * t_fire = 0.647209 N s, so
  delta-V per pulse = 6.47209e-4 m/s and per cycle (2 pulses) =
  1.29442e-3 m/s per axis.
- Propellant per pulse = F_t * t_fire / (Isp * g0) = 0.647209 /
  (60 * 9.80665) = 1.09995e-3 kg; per cycle = 2.19990e-3 kg.
- T_cycle = 4 * sqrt(h / alpha_c) = 4 * sqrt(1.74533e-3 / 8.33333e-3) =
  1.83058 s, so 47,198.1 cycles per day and 3.44782e7 cycles over the
  2-year life per axis (6.89564e7 pulses).
- Per-axis lifetime propellant = cycles * propellant_per_cycle =
  3.44782e7 * 2.19990e-3 = 7.58485e4 kg.
- Three-axis total at duty 1.0 = 3 * 7.58485e4 = 2.27546e5 kg; at duty
  0.5 the total halves to 1.13773e5 kg (linear scaling identity).
- Engineering gate note: 2.27546e5 kg of cold gas on a 1000 kg bus is
  physically impossible, and the estimate says so on purpose. A 1 N
  thruster at a 1 m arm yields only 1 N m of authority on a 120 kg m^2
  axis, far too little to arrest the crossing rate of a 0.1 deg deadband
  efficiently, so the aggregate limit cycle degenerates into
  near-continuous firing over the 2-year life. The verdict gates the
  design: fine hold at this deadband belongs to the reaction wheels
  (reaction-wheel-control leaf); an RCS hold with this thrust class
  needs a wider deadband, a shorter hold life or much higher control
  authority, and the real achievable impulse per gas mass is the
  cold-gas-thruster leaf's answer.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds computed by running the prep
anchor script /tmp/w41spec/anchor_rcs_limit_cycle.py (prep-verified by
stdlib math, all identities and 13 ValueError cases pass).

## Validation list (contract test must include)

- control_accel(1.0, 120.0) = 8.33333e-3 within 1e-12; ValueError at
  torque 0 and inertia 0 and negative.
- limit_cycle_rate(8.33333e-3, 1.74533e-3) = 5.39341e-3 within 1e-9
  (0.30902 deg/s); monotone in alpha_c and h; ValueError at zero.
- pulse_time(5.39341e-3, 8.33333e-3) = 0.647209 within 1e-9; identity
  pulse_time(limit_cycle_rate(a, h), a) == sqrt(2 h / a) within 1e-15
  for a second parameter pair; ValueError at zero inputs.
- pulse_delta_v(1.0, 0.647209, 1000.0) = 6.47209e-4 within 1e-12;
  delta_v_per_cycle = 1.29442e-3 within 1e-12 and exactly 2x the pulse
  value; ValueErrors at zero and negative.
- pulse_propellant(1.0, 0.647209, 60.0) = 1.09995e-3 within 1e-12;
  propellant_per_cycle = 2.19990e-3 within 1e-12 and exactly 2x the
  pulse value; Isp 0 and negative raise ValueError.
- cycle_period(1.74533e-3, 8.33333e-3) = 1.83058 within 1e-9; monotone
  decreasing in alpha_c, increasing in h; ValueError at zero.
- cycles_over_life(63115200.0, 1.83058) = 3.44782e7 within 1e3;
  86400.0 / 1.83058 = 47,198.1 within 1.0; ValueError at zero life.
- propellant_budget on the three identical example axes at duty 1.0:
  per-axis "propellant_life_kg" 7.58485e4 within 1.0, total
  2.27546e5 within 1.0; dict keys exactly the eleven listed; the same
  axes at duty 0.5 give exactly half the total; single-axis list with
  one axis gives the per-axis value as the total.
- Budget linearity identity: propellant_total scales linearly with
  duty_factor and with life_s at fixed period.
- ValueErrors across the module: non-positive torque, inertia, h,
  alpha_c, omega, t_fire, thrust, mass, Isp, life_s, period; empty axes
  list; duty_factor 0.0, negative and above 1.0.
- Determinism; no RNG anywhere.

## Corpus fragment (eval/hit1-wave41-reaction-jet-limit-cycle.yaml)

Query 1 (copy verbatim):
  "estimate the rcs attitude-hold propellant demand of the reaction-jet deadband limit cycle: the angular rate at the deadband crossing, the pulse duration of each thruster firing, the delta-v and propellant per cycle, and the cycle period over the mission life"
  intent: "space-systems; RCS attitude-hold propellant from the bang-bang deadband limit-cycle rate, pulse duration and cycle period"
  expected_skill: "space-systems/adcs/reaction-jet-limit-cycle"
Query 2 (copy verbatim):
  "compute the three-axis reaction-jet attitude-hold propellant budget over the mission life from the bang-bang limit-cycle period, the deadband half-angle, the control torque and inertia, and the thruster force and specific impulse"
  intent: "space-systems; three-axis RCS attitude-hold propellant budget from limit-cycle period, deadband half-angle and control torque"
  expected_skill: "space-systems/adcs/reaction-jet-limit-cycle"
Task ids: w41-reaction-jet-limit-cycle-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the RCS attitude-hold
propellant demand of a reaction-jet limit cycle:" and include the
outputs in the Claim. First tag: reaction-jet-limit-cycle. Additional
tags ONLY: rcs-attitude-hold-propellant, limit-cycle-propellant,
deadband-crossing-rate, thruster-pulse-duration,
three-axis-propellant-total. NEVER single generic words (attitude,
propellant, limit, cycle, rate, pulse, thruster, deadband, torque,
inertia, impulse, budget alone). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): tsiolkovsky,
rocket-equation-propellant, station-keeping, launch-insertion,
plane-change, deorbit, margin-allocation (mission-delta-v-budget);
choked-mass-flow, plenum-blowdown, blowdown-time-constant,
throat-area, plenum-pressure, total-impulse, operating-time,
nozzle-throat (cold-gas-thruster); switching-curve,
time-optimal-control, minimum-time-maneuver, rest-to-rest-slew,
double-integrator, bounded-input-control (bang-bang-control in
gnc-autonomy); wheel-torque-command, wheel-momentum-saturation,
momentum-desaturation, quaternion-error-feedback, desaturation-torque,
reaction-wheel-cluster, wheel-momentum (reaction-wheel-control);
momentum-wheel, slew-rate, detumble, adcs-sizing
(attitude-control-sizing); rss-pointing-error, jitter-contributor,
pointing-error-budget terms (pointing-error-budget). "Bang-bang" may
appear in description and body text as the limit-cycle qualifier, never
as a tag and never with the -control compound.

---
name: reaction-jet-limit-cycle
description: "Use when you must estimate the RCS attitude-hold propellant demand of a reaction-jet limit cycle: the control angular acceleration from the control torque and axis inertia, the angular rate at the deadband crossing, the firing duration of each braking pulse, the delta-V and propellant mass per pulse and per cycle, the aggregate cycle period, the cycle count over the mission life, and the three-axis lifetime propellant total with an activity duty factor. Produces the per-axis limit-cycle state and the three-axis propellant total that gate whether reaction-jet attitude hold is propellant-feasible. Trigger: rcs attitude hold, reaction jet limit cycle, deadband crossing rate, braking pulse firing, limit cycle period, thruster pulse, attitude hold propellant."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [reaction-jet-limit-cycle, rcs-attitude-hold-propellant, limit-cycle-propellant, deadband-crossing-rate, thruster-pulse-duration, three-axis-propellant-total]
  version: 0.1.0
  author: AeroSkills
---

# Reaction Jet Limit Cycle (space-systems/adcs/reaction-jet-limit-cycle)

Use when the task is the RCS attitude-hold propellant demand of a
bang-bang reaction-jet deadband limit cycle: the control authority on
an axis, the angular rate built up at the deadband crossing, the short
braking pulse that arrests it, and the propellant each pulse and each
full cycle costs over a mission life. This leaf implements the
Wertz-class aggregate limit-cycle estimate in pure Python, stdlib only.
It pairs with propulsion/rocket/cold-gas-thruster for the hardware
impulse side of the same gas and with
space-systems/mission-design/mission-delta-v-budget for the orbital
delta-v line; neither owns the attitude-hold propellant demand this
leaf computes.

## Domain quick reference

- Control angular acceleration: alpha_c = T_c / I, with T_c the control
  torque in N m and I the axis inertia in kg m^2.
- Deadband crossing rate: omega = sqrt(2 * alpha_c * h), with h the
  deadband half-angle in rad about the reference attitude.
- Braking pulse duration: t_fire = omega / alpha_c, which collapses to
  sqrt(2 * h / alpha_c) exactly; one pulse per deadband edge.
- Per-pulse linear impulse: F_t * t_fire on the spacecraft mass m gives
  delta-V per pulse = F_t * t_fire / m, and two pulses per limit cycle
  double it for the per-cycle delta-V.
- Propellant per pulse: F_t * t_fire / (Isp * g0) at the fixed specific
  impulse, g0 = 9.80665 m/s^2; per cycle it doubles. No blowdown: F_t
  and Isp are constants of the demand model.
- Aggregate limit-cycle period: T_cycle = 4 * sqrt(h / alpha_c). Each
  half oscillation is idealized as a constant-torque arc covering the
  full deadband width 2h from rest, so the detailed coast and fire
  sequencing is replaced by the aggregate period.
- Cycle count over the active duration: cycles = duty_factor * life_s /
  T_cycle; pulses = 2 * cycles; per-axis lifetime propellant = cycles *
  propellant_per_cycle, and the three-axis total sums the axes.
- Units are SI throughout: N, kg, kg m^2, rad, rad/s, rad/s^2, s, m/s.
- ECSS frames the spacecraft control context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. State the attitude-hold demand: the mission life life_s, the
   activity duty factor, and one axis dict per held axis with name,
   mass_kg, inertia_kgm2, torque_Nm, thrust_N, isp_s and
   deadband_half_rad.
2. Fix the control authority: control_accel(torque_Nm, inertia_kgm2)
   returns the control angular acceleration alpha_c in rad/s^2.
3. Find the deadband crossing rate: limit_cycle_rate(alpha_c, h_rad)
   returns omega = sqrt(2 * alpha_c * h) in rad/s.
4. Time the braking pulse: pulse_time(omega_rad_s, alpha_c) returns the
   firing duration t_fire in s of each pulse at a deadband edge.
5. Size the per-pulse impulse: pulse_delta_v(thrust_N, t_fire_s,
   mass_kg) for the linear delta-V and pulse_propellant(thrust_N,
   t_fire_s, isp_s) for the fixed-Isp propellant mass of one pulse.
6. Double to the full cycle: delta_v_per_cycle and
   propellant_per_cycle, two braking pulses per limit cycle.
7. Get the aggregate period: cycle_period(h_rad, alpha_c) returns
   T_cycle = 4 * sqrt(h / alpha_c) in s.
8. Count over the life: cycles_over_life(active_life_s, period_s) gives
   the cycle count; the pulse count is twice it.
9. Roll up the budget: propellant_budget(axes, life_s, duty_factor)
   returns the per-axis limit-cycle state dicts and the three-axis
   propellant_total_kg. Compare the total with the gas mass the
   hardware leaf makes available; if the total is physically
   impossible, the hold belongs to the reaction wheels or needs a wider
   deadband, a shorter hold life or higher control authority.
10. Confirm the deterministic checks with the contract test
    scripts/test_reaction_jet_limit_cycle.py.

## Worked example

A 1000 kg spacecraft, axis inertia I = 120 kg m^2 per axis, thruster
force F_t = 1 N at Isp = 60 s (cold gas class), deadband +/-0.1 deg
(h = 1.74533e-3 rad), 2-year mission life = 63,115,200 s (365.25-day
years), duty factor 1.0. Each braking pulse is one 1 N thruster at
moment arm L = 1.0 m, so the control torque per axis is T_c = 1.0 N m
(document the real geometry in your own study).

- alpha_c = 1.0 / 120 = 8.33333e-3 rad/s^2 (control_accel).
- omega = sqrt(2 * 8.33333e-3 * 1.74533e-3) = 5.39341e-3 rad/s =
  0.30902 deg/s at the deadband crossing (limit_cycle_rate).
- t_fire = 0.647209 s per braking pulse (pulse_time, and sqrt(2 h /
  alpha_c) gives the same value).
- Linear impulse per pulse = 0.647209 N s, so delta-V per pulse =
  6.47209e-4 m/s and per cycle = 1.29442e-3 m/s per axis.
- Propellant per pulse = 0.647209 / (60 * 9.80665) = 1.09995e-3 kg;
  per cycle = 2.19990e-3 kg.
- T_cycle = 4 * sqrt(1.74533e-3 / 8.33333e-3) = 1.83058 s, so 47,198.1
  cycles per day and 3.44782e7 cycles over the 2-year life per axis
  (6.89564e7 pulses).
- Per-axis lifetime propellant = 3.44782e7 * 2.19990e-3 = 7.58485e4 kg.
- Three-axis total at duty 1.0 = 2.27546e5 kg; at duty 0.5 it halves
  to 1.13773e5 kg (linear scaling identity).
- Engineering gate note: 2.27546e5 kg of cold gas on a 1000 kg bus is
  physically impossible, and the estimate says so on purpose. A 1 N
  thruster at a 1 m arm gives only 1 N m of authority on a 120 kg m^2
  axis, far too little to arrest the crossing rate of a 0.1 deg
  deadband efficiently, so the aggregate limit cycle degenerates into
  near-continuous firing over the 2-year life. Fine hold at this
  deadband belongs to the reaction wheels; an RCS hold with this
  thrust class needs a wider deadband, a shorter hold life or much
  higher control authority.

## Verification

- Confirm control_accel(1.0, 120.0) returns 8.33333e-3 rad/s^2.
- Confirm limit_cycle_rate on the example returns 5.39341e-3 rad/s and
  that pulse_time(omega, alpha_c) equals sqrt(2 * h / alpha_c) exactly.
- Confirm delta_v_per_cycle = 2 * pulse_delta_v and
  propellant_per_cycle = 2 * pulse_propellant exactly.
- Confirm propellant_budget on the three example axes at duty 1.0 gives
  2.27546e5 kg total and that duty 0.5 halves it exactly.
- Confirm omega is monotone increasing in alpha_c and h, t_fire is
  monotone decreasing in alpha_c, and T_cycle is monotone decreasing in
  alpha_c and increasing in h.
- Confirm the propellant numbers are independent of the spacecraft mass
  (mass enters only the delta-V terms) and that propellant per cycle
  depends only on thrust, Isp and t_fire, not on inertia, torque or
  mass.
- Confirm ValueError rejection of non-positive torque, inertia,
  half-angle, acceleration, rate, firing time, thrust, mass, Isp, life
  and period, of an empty axes list, and of a duty factor outside
  (0, 1].
- Run the contract test offline: python3
  scripts/test_reaction_jet_limit_cycle.py (33 tests, deterministic).

## Related leaves

- space-systems/adcs/attitude-control-sizing: wheel-class actuator
  sizing and margins; the wheel hold is the feasible alternative when
  the jet hold propellant demand is impossible.
- space-systems/adcs/reaction-wheel-control: the wheel control law that
  owns fine pointing hold without propellant.
- space-systems/adcs/magnetorquer-control: the momentum management
  actuator that avoids jet desaturation firing.
- space-systems/adcs/pointing-error-budget: the deadband as a pointing
  error contributor in an RSS budget, not a firing-rate driver.
- space-systems/mission-design/mission-delta-v-budget: the orbital
  delta-v budget and its propellant conversion line that this leaf does
  not duplicate.
- propulsion/rocket/cold-gas-thruster: the hardware thrust, Isp and
  blowdown model that owns the real impulse per gas mass.
- gnc-autonomy/optimal-control/bang-bang-control: the single-slew
  maneuver leaf in gnc-autonomy; it sizes one maneuver, not the firing
  count over a hold life.

## Pitfalls

- Reading the propellant total as feasible without the gas-mass
  cross-check: the worked example demands 2.27546e5 kg of cold gas for
  a 1000 kg bus, which is impossible, and the estimate flags it. Always
  compare the three-axis total with what the cold-gas-thruster leaf
  says the tank can actually deliver.
- Treating the crossing rate as the peak rate of a coasting arc: the
  aggregate model pins omega = sqrt(2 * alpha_c * h) as the
  constant-torque rate gained from rest over the half-angle h, and
  every downstream term (t_fire, impulse, propellant) inherits it.
- Doubling the pulse terms twice: each limit cycle has two braking
  pulses, one per deadband edge, so the per-cycle delta-V and
  propellant are exactly 2x the per-pulse values. Do not add a third
  factor of two for the two deadband edges.
- Using t_fire as a fixed firing budget per thruster: t_fire is the
  deadband-crossing arrest time of one pulse, and it depends only on h
  and alpha_c (sqrt(2 h / alpha_c)); it is not a valve on-time or a
  minimum impulse bit.
- Forgetting the duty factor on the life: the active hold duration is
  duty_factor * life_s, and the cycle count, pulse count and lifetime
  propellant all scale linearly with it; duty 0.5 halves the total.
- Confusing the delta-V terms with the propellant terms: the linear
  delta-V depends on the spacecraft mass while the fixed-Isp propellant
  per pulse does not, so changing the bus mass moves only the delta-V
  outputs, never the propellant total.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_reaction_jet_limit_cycle.py

The test covers the worked example (control acceleration, crossing
rate, firing duration, per-pulse and per-cycle delta-V and propellant,
aggregate cycle period, cycles per day and over the 2-year life, the
per-axis and three-axis lifetime propellant totals), the exact
identities (t_fire equals sqrt(2 h / alpha_c), per-cycle equals twice
per-pulse, lifetime equals cycles times per-cycle, duty 0.5 halves the
total, linear scaling with life and duty), the monotonicity relations
for omega, t_fire and T_cycle, the mass independence of the propellant
terms, the exact per-axis output key set, budget determinism, and
ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: ECSS covers spacecraft control
  (standards-map.yaml); the limit-cycle relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

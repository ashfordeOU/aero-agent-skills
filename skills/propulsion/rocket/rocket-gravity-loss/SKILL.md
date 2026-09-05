---
name: rocket-gravity-loss
description: "Use when you must account for gravity loss in a launch-vehicle powered ascent: compute the burn time from the propellant load and its flow rate, the launch thrust-to-weight ratio from the sea-level thrust and the initial mass, the gravity loss as g0 times the burn time for a vertical ascent or as g0 times the burn time times the sine of a constant mean flight-path angle for a pitched ascent, and the effective ascent delta-v as the ideal delta-v minus the gravity and drag losses. Produces the burn time, launch thrust-to-weight ratio, gravity loss and effective ascent delta-v that turn an ideal delta-v budget into an ascent-feasible requirement. Trigger: gravity loss, powered ascent, launch vehicle ascent, burn time, thrust-to-weight ratio, vertical ascent, pitched ascent, effective delta-v."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [rocket-gravity-loss, gravity-loss, launch-vehicle-ascent, ascent-delta-v, powered-ascent, burn-time-estimate, launch-thrust-to-weight]
  version: 0.1.0
  author: AeroSkills
---

# Rocket Gravity Loss (propulsion/rocket/rocket-gravity-loss)

Use when the task is the gravity-loss leg of a launch-vehicle powered
ascent: the burn time from the propellant load and flow rate, the launch
thrust-to-weight ratio, the gravity loss for a vertical or pitched ascent,
and the effective and required ideal delta-v that bracket the losses. This
leaf owns the powered-ascent loss-sizing step that no other leaf computes,
turning an ideal delta-v budget into an ascent-feasible requirement. It
pairs with the sibling sizing and staging leaves: propulsion/rocket/
rocket-sizing supplies the ideal delta-v budget this leaf consumes, and
propulsion/rocket/rocket-staging allocates the required ideal delta-v
across stages.

## Domain quick reference

- Standard gravity: g0 = 9.80665 m/s^2, the module constant behind every
  loss relation. SI units throughout: kg, kg/s, N, s, m/s, degrees.
- Burn time: t_b = m_prop / m_dot, the propellant load divided by the
  constant propellant flow rate. A 400000 kg load at 2500 kg/s burns for
  160.0 s.
- Launch thrust-to-weight ratio: TWR = T / (m0 * g0), the sea-level thrust
  over the initial weight. 7.355 MN on a 700000 kg vehicle gives TWR =
  1.071.
- Vertical-ascent gravity loss: dv_grav = g0 * t_b. The 160.0 s burn
  loses 1569.1 m/s to gravity alone.
- Pitched-ascent gravity loss: dv_grav = g0 * t_b * sin(gamma), with gamma
  the constant mean flight-path angle held fixed for the whole burn (the
  leaf envelope, mirroring the wave-38 regime-boundary pattern). At 45
  degrees the loss drops to 1109.5 m/s; at 90 degrees it equals the
  vertical value, at 0 degrees it vanishes.
- Effective ascent delta-v: dv_eff = dv_ideal - dv_grav - dv_drag, the
  ideal budget minus the gravity and drag losses.
- Required ideal delta-v: dv_req = dv_target + dv_grav + dv_drag, the ideal
  budget an ascent must carry to deliver a net target delta-v.
- The ideal delta-v budget itself is the sibling sizing leaf's output, not
  recomputed here; this leaf only converts that budget into an
  ascent-feasible requirement.

## Workflow

1. Fix the ascent point: propellant load m_prop, propellant flow rate
   m_dot, sea-level thrust T, initial mass m0, the ideal delta-v budget
   from the sizing leaf, and the constant mean flight-path angle gamma
   (90 degrees by default, the vertical case).
2. Burn time traverse: burn_time(propellant_mass, mass_flow) returns
   t_b = m_prop / m_dot from the propellant load and flow rate.
3. Launch thrust-to-weight traverse: thrust_to_weight(thrust,
   initial_mass) returns TWR from the sea-level thrust and initial mass.
4. Gravity-loss traverse: gravity_loss_vertical(burn_time_s) returns the
   vertical-ascent loss g0 * t_b; for a pitched ascent run
   gravity_loss_pitched(burn_time_s, mean_path_angle_deg) with the
   constant mean flight-path angle in degrees.
5. Ascent delta-v bookkeeping: effective_delta_v(ideal_delta_v,
   gravity_loss, drag_loss) subtracts the losses from the ideal budget;
   required_ideal_delta_v(target_delta_v, gravity_loss, drag_loss) adds
   the losses to a net target.
6. Ascent report: ascent_report(propellant_mass, mass_flow, thrust,
   initial_mass, ideal_delta_v, target_delta_v, mean_path_angle_deg,
   drag_loss) returns the dict with keys burn_time, thrust_to_weight,
   gravity_loss, effective_delta_v and required_ideal_delta_v.
7. Verify: run python3 scripts/test_rocket_gravity_loss.py (33 tests,
   deterministic, offline) and confirm the worked-example anchors, the
   loss identities, the round trips and every ValueError guard.

## Worked example

Heavy-lift stage: m_prop = 400000 kg, m_dot = 2500 kg/s, T = 7.355 MN,
m0 = 700000 kg, ideal delta-v budget 2492.7 m/s. Module outputs (contract
test anchors in parentheses):

- Burn time: t_b = 400000 / 2500 = 160.0 s (160.0 within 0.1 s).
- Launch thrust-to-weight: TWR = 7354987.5 / (700000 * 9.80665) = 1.0714
  (1.071 within 0.002).
- Vertical-ascent gravity loss: 9.80665 * 160.0 = 1569.1 m/s (1569.1
  within 0.5 m/s), over 60 percent of the ideal budget.
- Pitched-ascent gravity loss at 45 degrees: 1569.1 * sin(45) = 1109.5
  m/s (1109.5 within 0.5 m/s), so pitching the ascent cuts the loss by
  459.6 m/s.
- Effective ascent delta-v: 2492.7 - 1109.5 = 1383.2 m/s (1383.2 within
  0.5 m/s) for the pitched ascent with no drag loss.
- Required ideal delta-v: 1383.2 + 1109.5 = 2492.7 m/s, the exact
  round trip back to the ideal budget.
- Ascent report dict: burn_time 160.0, thrust_to_weight 1.0714,
  gravity_loss 1569.1 (vertical default) or 1109.5 (45 degrees),
  effective_delta_v and required_ideal_delta_v as above.

## Verification

- Confirm burn_time(400000, 2500) returns 160.0 s and that the burn time
  scales linearly with the propellant load and inversely with the flow
  rate.
- Confirm thrust_to_weight(7354987.5, 700000) returns 1.0714 and equals
  T / (m0 * g0) exactly.
- Confirm gravity_loss_vertical(160.0) returns 1569.064 m/s and equals
  g0 times the burn time; gravity_loss_pitched(160.0, 45) returns
  1109.496 m/s and equals g0 * t_b * sin(45 deg) exactly.
- Confirm the loss ordering: the pitched loss at 45 degrees sits below
  the vertical loss, equals it at 90 degrees and vanishes at 0 degrees.
- Confirm effective_delta_v plus the losses equals the ideal delta-v, and
  that required_ideal_delta_v inverts effective_delta_v back to the ideal
  budget.
- Confirm the ascent report returns exactly the five documented keys and
  is deterministic across identical calls.
- Confirm every non-positive propellant load, flow rate, thrust and
  initial mass, every negative burn time, every mean flight-path angle
  outside [0, 90] degrees (95 or -5), and every loss sum that exceeds the
  ideal or target delta-v raises ValueError.
- Run the contract test offline: python3 scripts/test_rocket_gravity_loss.py
  (33 tests, deterministic).

## Related leaves

- propulsion/rocket/rocket-sizing: the sibling that supplies the ideal
  delta-v budget and mass-ratio side of the ascent sizing loop.
- propulsion/rocket/rocket-staging: allocates the required ideal delta-v
  across stages once this leaf has added the gravity and drag losses.
- space-systems/mission-design/mission-delta-v-budget: spacecraft
  post-injection budgeting, downstream of the launch-ascent leg.
- propulsion/rocket/rocket-nozzle-flow-separation and
  propulsion/rocket/nozzle-design: the nozzle flow and thrust side of the
  engine, upstream of the sea-level thrust input.
- propulsion/rocket/solid-rocket-motor and propulsion/rocket/
  hybrid-rocket-motor: grain and regression burn time, distinct from this
  leaf's ascent bookkeeping.

## Pitfalls

- Quoting the ideal delta-v budget as the ascent delta-v: gravity alone
  eats 1569.1 m/s of the 2492.7 m/s ideal budget in the worked example,
  so an ascent-feasible requirement must subtract the losses, not carry
  the ideal number.
- Mixing the vertical and pitched loss models: the pitched loss is g0 *
  t_b * sin(gamma), which is below the vertical g0 * t_b for any positive
  path angle; reporting the vertical loss for a pitched trajectory
  overstates the requirement by (1 - sin(gamma)) * g0 * t_b.
- Confusing the effective and required ideal delta-v: effective
  subtracts the losses from an ideal budget, required adds them to a net
  target, and the two meet at the round trip only when the target equals
  the effective value.
- Feeding an ideal delta-v budget smaller than the losses: the loss sum
  must stay below the ideal or target delta-v, and the module raises
  ValueError instead of returning a negative remainder.
- Recomputing the ideal delta-v here: the rocket-equation side belongs to
  rocket-sizing, and this leaf's claim stops at the loss accounting that
  converts the budget into an ascent-feasible requirement.
- Using a mean flight-path angle outside [0, 90] degrees: 95 or -5
  degrees are rejected, since the constant-mean-angle envelope covers the
  vertical-to-horizontal range only.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rocket_gravity_loss.py

The test covers the worked-example anchors (burn time 160.0 s, launch
thrust-to-weight 1.071, vertical gravity loss 1569.1 m/s, pitched gravity
loss 1109.5 m/s at 45 degrees, effective delta-v 1383.2 m/s), the linear
burn time scalings, the thrust-to-weight closed form, the g0-times-burn
time vertical identity and the sine closed form for the pitched loss, the
pitched-below-vertical ordering with the 90 and 0 degree boundaries, the
effective-plus-losses-equals-ideal identity, the drag-loss reduction
trend, the required-ideal round trip, the exact ascent report keys,
determinism, and ValueError rejection of non-positive loads, flows,
thrusts and masses, negative burn times, out-of-range mean flight-path
angles and loss sums that exceed the ideal or target delta-v.

## Compliance

- Standards referenced, not reproduced: ECSS space-systems standards
  frame the launch-vehicle engineering context (free ESA download,
  ecss.nl/standards); the ascent gravity-loss relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

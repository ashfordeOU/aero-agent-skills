# Wave-39 leaf spec: rocket-gravity-loss (propulsion, rocket pack)

- Path: skills/propulsion/rocket/rocket-gravity-loss/
- Pack: rocket. Closest siblings: rocket-staging (per-stage ideal delta-v,
  structural-index and payload-fraction allocation, equal-stage optimum),
  rocket-sizing (ideal rocket equation, mass ratio from delta-v, propellant
  mass), mission-delta-v-budget (spacecraft post-injection budget; launch
  insertion is an external input, never modeled), rocket-nozzle-flow-
  separation, nozzle-design (ideal thrust at design and ambient
  conditions), solid-rocket-motor and hybrid-rocket-motor (grain and
  regression burn time, not ascent bookkeeping). Whole-tree greps at prep:
  "gravity loss" = 0 owning hits; the powered-ascent loss-sizing function is
  computed by no leaf; launch thrust-to-weight owners are all aircraft-level
  (vehicle-design constraint-analysis, engine-sizing). GENUINE PROP gap
  (fresh probe).
- Standards id: ecss (reference-only; rocket-pack convention). Ledger
  Standard: ecss.
- Family: propulsion

## Claim

Account for the gravity loss in a launch-vehicle powered ascent: compute
the burn time from the propellant mass and the propellant mass flow, the
launch thrust-to-weight ratio from the sea-level thrust and the initial
mass, the gravity loss as g0 times the burn time for a vertical ascent or
g0 times the burn time times the sine of a constant mean flight-path angle
for a pitched ascent, and the effective ascent delta-v as the ideal delta-v
minus the gravity and drag losses. Produces the burn time, thrust-to-weight,
gravity loss and effective delta-v that convert an ideal rocket-equation
budget into an ascent-feasible requirement. Does NOT do: the ideal rocket
equation, mass ratios or staging allocation (rocket-sizing, rocket-staging);
nozzle flow (nozzle-design, rocket-nozzle-flow-separation); spacecraft
post-injection delta-v budgeting (mission-delta-v-budget); grain burn time
(solid-rocket-motor).

## Model (implement exactly)

Module constant G0 = 9.80665 m/s2.

Functions (pure stdlib):
- burn_time(propellant_mass, mass_flow) -> t_b = m_prop / m_dot; ValueError
  if propellant_mass <= 0 or mass_flow <= 0.
- thrust_to_weight(thrust, initial_mass) -> TWR = thrust / (initial_mass *
  G0); ValueError if thrust <= 0 or initial_mass <= 0.
- gravity_loss_vertical(burn_time_s) -> g0 * t_b; ValueError if burn time
  negative.
- gravity_loss_pitched(burn_time_s, mean_path_angle_deg) -> g0 * t_b *
  sin(mean path angle in radians); ValueError if burn time negative or mean
  path angle outside [0, 90] degrees.
- effective_delta_v(ideal_delta_v, gravity_loss, drag_loss=0.0) ->
  ideal - gravity - drag; ValueError if any loss negative or if the losses
  sum to more than the ideal delta-v.
- required_ideal_delta_v(target_delta_v, gravity_loss, drag_loss=0.0) ->
  target + losses; ValueErrors as above.
- ascent_report(...) -> dict with keys burn_time, thrust_to_weight,
  gravity_loss, effective_delta_v, required_ideal_delta_v.

The constant-mean-path-angle assumption is the leaf's documented envelope:
the pitched ascent model holds the flight-path angle fixed at its mean value
for the whole burn, mirroring the wave-38 rocket-nozzle-flow-separation
regime-boundary pattern.

Identity to test: a vertical launch gravity loss equals g0 times the burn
time; the pitched loss is below the vertical loss for any positive path
angle; effective delta-v plus the losses equals the ideal delta-v;
required_ideal_delta_v inverts effective_delta_v.

## Worked example

m_prop = 400,000 kg, m_dot = 2,500 kg/s, Isp = 300 s, m0 = 700,000 kg:
- t_b = 160.0 s.
- T = m_dot * Isp * g0 = 7.355 MN; TWR = 1.071.
- dv_ideal = g0 * Isp * ln(m0/(m0 - m_prop)) = 2492.7 m/s.
- gravity_loss_vertical = 1569.1 m/s; gravity_loss_pitched at 45 deg =
  1109.5 m/s.
- effective_delta_v(2492.7, 1109.5) = 1383.2 m/s.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (independently evaluated at prep).

## Validation list (contract test must include)

- burn_time 160.0 s within 0.1 s.
- thrust 7.355e6 N within 1e3 (from the module formula or given); TWR
  1.071 within 0.002.
- gravity_loss_vertical 1569.1 m/s within 0.5; pitched at 45 deg 1109.5
  within 0.5.
- effective_delta_v 1383.2 within 0.5; required_ideal_delta_v round trip.
- Pitched loss below vertical loss at 45 deg; equal at 90 deg; zero at
  0 deg.
- ValueErrors: propellant or flow <= 0, thrust <= 0, initial mass <= 0,
  path angle 95 or -5, losses exceeding ideal delta-v.
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-rocket-gravity-loss.yaml)

Query 1 (copy verbatim):
  "estimate the gravity-loss delta-v and the launch-vehicle-ascent burn time for a 400 tonne stage at launch-thrust-to-weight 1.07"
  intent: "propulsion; powered-ascent gravity loss and burn time"
  expected_skill: "propulsion/rocket/rocket-gravity-loss"
Query 2 (copy verbatim):
  "compute the effective ascent-delta-v after gravity loss for a vertical launch with a 160 second burn"
  intent: "propulsion; effective delta-v after gravity loss"
  expected_skill: "propulsion/rocket/rocket-gravity-loss"
Task ids: w39-rocket-gravity-loss-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must account for gravity loss in a
launch-vehicle powered ascent:" and include the outputs in the Claim. First
tag: rocket-gravity-loss. Additional tags ONLY: gravity-loss, launch-
vehicle-ascent, ascent-delta-v, powered-ascent, burn-time-estimate,
launch-thrust-to-weight. NEVER single generic words (gravity, loss, launch,
vehicle, ascent, burn, time, delta, v). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): tsiolkovsky, rocket-equation,
mass-ratio, propellant-mass, staging-optimization, payload-fraction,
structural-index, specific-impulse (rocket-sizing, rocket-staging);
margin-allocation (mission-delta-v-budget); nozzle, separation-regime
(nozzle-design, rocket-nozzle-flow-separation); grain, regression-rate
(solid-rocket-motor, hybrid-rocket-motor).

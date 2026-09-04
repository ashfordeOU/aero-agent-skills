# Wave-33 leaf spec: bang-bang-control (gnc-autonomy, optimal-control pack)

- Path: skills/gnc-autonomy/optimal-control/bang-bang-control/
- Pack: optimal-control (3 leaves -> 4: lqr-design, model-predictive-
  control, dymos-trajectory). Sibling receipts: lqr-design owns
  infinite-horizon quadratic cost with linear state feedback (no hard
  limits, no time objective); model-predictive-control owns receding-
  horizon QUADRATIC QP (zero min-time/bang/switching tokens in body or
  logic); dymos-trajectory owns dymos-library phase/convergence/Delta-v
  checking; control-allocation handles effector distribution under
  limits, not limit-optimal steering; pid-control-design anti-windup
  clamps an integrator. Grep time-optimal|bang-bang|minimum-time|
  switching-curve|pontryagin across all 40 leaves AND scripts: zero
  hits. This leaf owns time-optimal bang-bang control.
- Standards id: arp4754a (reference-only; MPC-leaf "none" precedent
  also valid, but the family control leaves cite arp4754a).
  Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Compute the time-optimal (minimum-time) control of a double integrator
under a hard input limit: the bang-bang switching curve, the control
command u = -a sign(s) from the switching function, the exact
rest-to-rest maneuver time T* = 2 sqrt(d/a), the switching state (half
distance, velocity -sqrt(a d) at T*/2), and the general minimum-time
state trajectory for nonzero initial velocity. Produces the switch
point and the maneuver time for attitude-slew and translation
bang-bang assessments.

Does NOT do: quadratic-cost LQR state feedback (lqr-design);
receding-horizon MPC with quadratic cost (model-predictive-control);
collocation trajectory optimization frameworks (dymos-trajectory);
effector distribution under limits (control-allocation); integrator
anti-windup clamping (pid-control-design).

## Model (implement exactly)

Conventions: double integrator x_ddot = u with |u| <= a (a > 0 the
acceleration/rate limit). Switching function s(x, v) = x + v|v|/(2a).
Bang-bang command u = -a sign(s) (with sign(0) convention documented;
the switching curve separates the phase plane).
- Rest-to-rest over distance d: T* = 2 sqrt(d/a); switch at t_s =
  sqrt(d/a), x_s = d/2, v_s = -sqrt(a d) (accelerate half the
  distance, decelerate the rest).
- Minimum-time from (x0, v0) to rest at the origin: standard closed
  form via the switching curve (accelerate toward the curve then
  follow it; the builder implements the documented analytic solution
  and verifies by stepping simulation to within a small tolerance).

Functions (pure stdlib):

- switch_curve(x, v, a) -> x + v*|v|/(2a). ValueError on a <= 0.
- bang_bang_command(x, v, a) -> -a * sign(s) with sign(0) = 0
  documented (or +a convention; pick and document). Return -a, 0, or
  +a.
- min_time_rest_to_rest(d, a) -> 2 sqrt(d/a). ValueErrors on d < 0
  (d = 0 returns 0.0), a <= 0.
- switch_state(d, a) -> dict {switch_time_s, switch_position,
  switch_velocity} = (sqrt(d/a), d/2, -sqrt(a d)).
- min_time_state(x0, v0, a) -> dict {total_time, switch_time,
  switch_position, switch_velocity, command_phases} implementing the
  analytic two-phase solution; verify by a stepping simulation helper
  inside the test (not the logic module) to 1e-3.
- bang_bang_summary(...) -> dict with the maneuver parameters.

## Worked example

Rest-to-rest d = 100 m, a = 1 m/s2: T* = 20.000000 s; switch at
t = 10.00001 s, x = 50.0 m, v = -10.0 m/s (exactly T*/2, d/2,
-sqrt(a d)). A stepping simulation settles about 19.999050 s.
Slew frame: theta0 = 2 rad, alpha = 0.05 rad/s2: T* = 2 sqrt(2/0.05)
about 12.649111 s.
Generic: x0 = 50 m, v0 = +5 m/s, a = 1: total about 20.810 s =
5 + 2 sqrt(62.5) analytic.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds above. If a value falls outside its bound, your
implementation has a bug: find it before writing tests. In the SKILL.md
worked example show your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: a <= 0; d < 0 (d = 0 allowed returning 0).
- Rest-to-rest anchor: min_time_rest_to_rest(100, 1) == 20.0 exactly
  (2 sqrt(100)); switch_state returns (10.0, 50.0, -10.0).
- Slew anchor: 2 sqrt(2/0.05) about 12.649111.
- Generic anchor: the analytic total about 20.810 s.
- Simulation cross-check: stepping the bang-bang command from the
  switch-state lands at the origin within 1e-3.
- Command polarity: bang_bang_command is -a on one side of the
  switching curve and +a on the other (sign consistency).
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-bang-bang-control.yaml)

Query 1 (copy verbatim):
  "derive the bang bang switching curve time optimal control for a double integrator slew with the switch point and the minimum time rest to rest duration under a torque limit"
  intent: "gnc-autonomy; bang-bang time-optimal switching curve and minimum-time rest-to-rest"
  expected_skill: "gnc-autonomy/optimal-control/bang-bang-control"
Query 2 (copy verbatim):
  "compute the time optimal bang bang acceleration profile and switching time for a single axis attitude maneuver with bounded rate"
  intent: "gnc-autonomy; time-optimal bang-bang profile for a bounded single-axis maneuver"
  expected_skill: "gnc-autonomy/optimal-control/bang-bang-control"
Task ids: w33-bang-bang-control-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the time-optimal
bang-bang control of a double integrator:" and include the outputs in
the Claim. First tag: bang-bang-control. Additional tags ONLY:
time-optimal-control, switching-curve, minimum-time-maneuver,
double-integrator, rest-to-rest-slew, bounded-input-control. NEVER
single generic words (optimal, control, time, switch, maneuver,
acceleration, limit, attitude). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): quadratic cost, LQR, Riccati,
infinite horizon (lqr-design); receding horizon, QP, prediction
horizon (model-predictive-control); collocation, phase, dymos
(dymos-trajectory); control allocation, effector mixing (control-
allocation); integral clamp, anti windup (pid-control-design). The
tokens "bang bang", "time optimal", "switching curve", "minimum
time" are this leaf's own.

Tags: [bang-bang-control, time-optimal-control, switching-curve,
minimum-time-maneuver, double-integrator, rest-to-rest-slew,
bounded-input-control]

Sibling-citation lines for Related leaves:
gnc-autonomy/optimal-control/lqr-design (quadratic full-state sibling;
this leaf owns the hard-limit time-optimal law),
gnc-autonomy/optimal-control/model-predictive-control,
gnc-autonomy/control/pid-control-design.

Ledger Standard: arp4754a.

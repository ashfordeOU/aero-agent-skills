# Wave-30 leaf spec: adaptive-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/adaptive-control/
- Pack: control (siblings: control-allocation, frequency-response-design,
  gain-scheduling, lead-lag-compensation, observer-design, pid-control-design,
  python-control-design, root-locus-design, state-space-analysis). The pack
  has no adaptive or robust control leaf; model-reference adaptive control is
  the genuine canon gap.
- Standards ids: arp4754a (reference-only; gnc control pack convention).
  Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design and simulate a model-reference adaptive controller (MRAC) for a
first-order plant with an unknown plant coefficient: run the reference model
from the command, compute the control as the sum of a state-feedback term and
a feedforward term with adaptive gains, update the adaptive gains with the
gradient (Lyapunov-motivated) adaptation law scaled by the tracking error, and
assess convergence of the tracking error and of the gains toward the
ideal-cancellation values. Produces the error history, the gain histories, and
the convergence verdict that gate an adaptive control assessment.

Does NOT do: tune fixed PID gains (pid-control-design owns PID gain tuning);
design LQR or MPC state feedback (lqr-design and model-predictive-control own
those); compensate loops with lead/lag or root-locus methods (lead-lag-
compensation, root-locus-design own the classical design); schedule gains
against Mach/dynamic pressure (gain-scheduling owns the schedule table);
observe unmeasured states (observer-design owns the Luenberger observer);
analyze a plant with KNOWN parameters using fixed state feedback
(state-space-analysis owns controllability/observability and pole placement).
This leaf adapts gains ONLINE for an unknown first-order plant coefficient;
single-input, no noise, no disturbance, sign of the control effectiveness
known positive.

## Model (implement exactly)

Module constants:
- (no magic constants; all gains and model parameters are explicit inputs).
- MAX_STEPS_DEFAULT = 2000.

Functions (pure stdlib; all scalar floats, discrete-time with step dt):
- reference_step(xm, command, a_m, b_m, dt) -> float:
  xm_next = xm + dt * (a_m * xm + b_m * command). (a_m < 0 required.)
- plant_step(x, control, a_p, b_p, dt) -> float:
  x_next = x + dt * (a_p * x + b_p * control).
- control_output(theta_x, theta_r, x, command) -> float:
  u = theta_x * x + theta_r * command.
- ideal_gains(a_p, b_p, a_m, b_m) -> dict: {theta_x_star: (a_m - a_p) / b_p,
  theta_r_star: b_m / b_p}. ValueError if b_p == 0.
- adaptation_step(theta_x, theta_r, error, x, command, gamma_x, gamma_r, dt)
  -> (theta_x_new, theta_r_new): gradient adaptation
  theta_x_new = theta_x - gamma_x * error * x * dt;
  theta_r_new = theta_r - gamma_r * error * command * dt
  (Lyapunov-motivated rule for a plant with known-positive control
  effectiveness; error = x - x_ref). ValueError if gamma_x < 0 or
  gamma_r < 0.
- simulate(plant_a, plant_b, model_a, model_b, dt, gamma_x, gamma_r,
  command=1.0, x0=0.0, steps=MAX_STEPS_DEFAULT) -> dict:
  {t_list, x_list, xm_list, u_list, theta_x_list, theta_r_list,
  error_final, max_abs_error, converged} where converged is True when
  max(abs(error)) over the LAST 200 steps < 1e-4 AND
  abs(theta_x - theta_x_star) < 0.05 AND abs(theta_r - theta_r_star) < 0.05.
  ValueError if model_a >= 0 (reference model must be stable), dt <= 0,
  steps < 2, gamma < 0, plant_b == 0.
- gain_convergence_report(...same kwargs...) -> dict: {theta_x_star,
  theta_r_star, theta_x_final, theta_r_final, theta_x_error,
  theta_r_error, tracking_rmse (root mean square error over the last 500
  steps)}.

## Worked example

Reference model a_m = -1.0, b_m = 1.0. Plant a_p = 1.0 (open-loop unstable),
b_p = 2.0. dt = 0.01, gamma_x = 10.0, gamma_r = 10.0, command = 1.0, x0 = 0.

Deterministic anchors (module outputs as assert targets; bounds):
- ideal gains: theta_x_star = (-1 - 1)/2 = -1.0 EXACT; theta_r_star = 0.5
  EXACT.
- After 2000 steps the tracking error magnitude is < 1e-3 (transient
  settles; bound for error_final: abs < 1e-3) and x tracks xm: xm_final =
  1 - exp(-1 * 20)? xm(t) -> b_m/(-a_m) * 1 = 1.0; x_final in 0.99-1.01.
- theta_x_final in -1.1 to -0.9; theta_r_final in 0.45-0.55.
- converged True on the worked example (run to 3000 steps if needed to
  clear the 0.05 gain tolerance; the spec default 2000 must converge with the
  stated gains - if your run does not converge in 2000, increase steps to
  3000 in the example and document it).
- Determinism: same inputs -> identical arrays.
If a value is outside its bound, debug before writing tests. Show real module
outputs (final gains, final error, converged flag) in the SKILL.md worked
example.

## Validation list (contract test must include)

- ValueError: model_a >= 0, dt <= 0, steps < 2, gamma_x/gamma_r < 0,
  plant_b == 0.
- ideal_gains exactness on the worked example.
- Adaptation monotonic sanity: gamma 0 keeps gains constant (adaptation_step
  with gamma 0 returns unchanged gains).
- Convergence on the worked example (converged True).
- Instability guard: with NO adaptation (gamma 0) and an unstable plant, the
  state magnitude grows (|x| at step 500 > 10) - verifies the controller is
  actually doing the work.
- Determinism.

## Corpus fragment (eval/hit1-wave30-adaptive-control.yaml)

Forbidden tokens (siblings): pid, root-locus, bode, phase-margin, lead-lag,
lqr, riccati, mpc, scheduling, gain-schedule, luenberger. Distinctive tokens
ONLY: adaptive-control, mrac, model-reference, adaptation-law, tracking-
error, unknown-plant.

Query 1: "Design a model-reference adaptive-control (mrac) law for a first
order plant with unknown coefficient and check the tracking-error convergence"
(id w30-adaptive-control-1).
Query 2: "Simulate the adaptation-law gain update for an unstable first order
plant and report the final adaptive gains" (id w30-adaptive-control-2).
intent: "gnc-autonomy; model-reference adaptive control".

## Description/tag guidance

Description opens "Use when you must design and simulate a model-reference
adaptive controller (MRAC) for a first-order plant with an unknown plant
coefficient:" and lists the outputs in the Claim. First tag: adaptive-control.
Additional tags: mrac, model-reference-adaptive, adaptation-law,
tracking-error. No generic single words. 50-150 words, <=1000 chars, no em
dash, no "classified".

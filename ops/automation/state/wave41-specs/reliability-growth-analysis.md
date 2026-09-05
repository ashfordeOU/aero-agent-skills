# Wave-41 leaf spec: reliability-growth-analysis (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/reliability-growth-analysis/
- Pack: arp4761a (verified present at prep with failure-rate-estimation,
  markov-analysis, fault-tree-importance-measures, fta-fmea, ssa-closure,
  reliability-block-diagram, safety-assessment, preliminary-system-safety-
  assessment and the FHA/RBD/Markov siblings). Closest sibling:
  failure-rate-estimation (homogeneous Poisson process with CONSTANT rate
  lambda per flight hour throughout: its body models data "as a Poisson
  process with constant rate lambda per flight hour", its workflow step 1
  says "confirm the constant-rate (Poisson) assumption holds for the
  exposure period", and its functions are the point estimate n / T, the
  chi-square upper-bound, the zero-failure rule, test-hours planning to a
  target rate, and the MTBF bounds; the only Pitfall facing this leaf is
  "Forgetting the constant-rate assumption: infant mortality and wear-out
  data violate the Poisson model and the chi-square bound is not valid",
  and NO function in its body fits a trend, slope, or time-varying rate;
  the growth hypothesis is deliberately excluded there, it is the whole
  claim here). Other fences in the family: in-service-safety-assessment
  (continued-airworthiness pack; ARP5150A/ARP5151 style field review that
  "compare[s] the observed event rate over the fleet exposure ... with the
  predicted rate from the safety objective", a level comparison against
  the SSA prediction where the Poisson exceedance tail is computed but
  "the chi-square failure-rate statistics belong to the failure-rate-
  estimation sibling", and trend enters only as the corrective_route
  trend_direction (-1, 0, 1) routing input, not as a fitted curve over
  time; no growth-curve fit exists in its body), ssa-closure (arp4761a;
  closes the post-implementation SSA by comparing analyst-supplied
  predicted probabilities per flight hour against the per-severity
  targets: "Only post-implementation predicted probabilities are consumed
  here: this leaf does not rate a condition's severity from its effects,
  derive or apportion the safety requirements, plan the assessment
  sequence, or consume observed fleet data from service"). Whole-tree
  greps at prep: "duane", "crow-amsaa", "amsaa", "reliability growth",
  "growth slope" and "power-law process" = 0 hits in skills/. GENUINE
  systems-engineering-safety gap (fresh probe): no leaf answers whether
  the failure rate is improving, constant, or degrading over cumulative
  test time, and no leaf projects test time to a target MTBF under a
  fitted growth model.
- Standards id: arp4761a (present in standards-map.yaml). Ledger
  Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Determine whether a system failure rate is improving over development or
field test time from the ordered failure times, and project test hours to
a target MTBF: fit the Duane plot by ordinary least squares of the log
cumulative failure rate on log cumulative time over the failure-event
cumulative points, giving the growth slope and a beta_duane = slope + 1;
compute the Crow-AMSAA (power-law process) maximum likelihood estimate of
the shape beta by deterministic bisection on the MLE equation, with the
scale lambda and the standard AMSAA current MTBF T / (N beta); project
the MTBF to a target cumulative test time and invert the projection for
the test hours at which the fitted MTBF reaches a target value; and rate
the shape beta with the growth verdict (beta below 1 improving, at 1
consistent with the constant-rate homogeneous Poisson process, above 1
degrading). Produces the Duane growth slope, the fitted current MTBF
under both estimators, the AMSAA beta and lambda, the projected MTBF, the
test-hours-to-target value and the improving/constant/degrading verdict
that decide whether continued testing or a corrective redesign is
warranted before a rate is claimed. Does NOT do: the point failure-rate
estimate, chi-square confidence bounds, the zero-failure demonstration
rule, or test-hours planning for demonstration at a fixed rate under the
constant-rate assumption (failure-rate-estimation); field event review
against SSA predicted rates with the single-event rule
(in-service-safety-assessment); the closure-gate rollup of predicted
versus target probabilities (ssa-closure); fault tree, Markov, or RBD
computation that consumes rates as inputs (fta-fmea, markov-analysis,
reliability-block-diagram). Trend analysis only, never a confidence
interval on the growth parameters; the model is the power-law NHPP with
no covariate or repair-content term.

## Model (implement exactly)

Functions (pure stdlib, math only):
- duane_fit(fail_times, evaluation_time = None) -> dict {"slope",
  "intercept", "beta_duane", "evaluation_time", "current_mtbf"}:
  cumulative point i of the Duane plot is (t_i, i), so the cumulative
  failure rate is i / t_i; OLS of y_i = ln(i / t_i) on x_i = ln(t_i)
  over all N failure events gives slope and intercept, with
  beta_duane = slope + 1 (under the power-law process the cumulative
  rate is lambda t^(beta - 1), so the Duane plot slope equals beta - 1
  and the intercept equals ln(lambda)). current_mtbf is the
  instantaneous MTBF 1 / (lambda beta t^(beta - 1)) of the fitted line
  evaluated at evaluation_time (default the last failure time):
  exp(-intercept) / (beta_duane * evaluation_time**(beta_duane - 1)).
  ValueErrors: fewer than MIN_FAILURES = 2 failures, a non-positive or
  non-finite failure time, decreasing failure times, evaluation_time
  non-positive or below the last failure time, and zero ln-time variance
  (all failure times equal, the OLS division is undefined).
- amsaa_mle(fail_times, total_time) -> dict {"beta_hat", "lambda_hat",
  "n_failures", "total_time", "current_mtbf", "bisection_iterations"}:
  the Crow-AMSAA power-law NHPP E[N(t)] = lambda t^beta (name and
  paraphrase of the MIL-HDBK-189 standard reliability-growth method, no
  verbatim text). The MLE shape beta_hat solves sum over failures of
  ln(total_time / t_i) = N / beta_hat (from the profile likelihood,
  derived in the SKILL body), found by deterministic bisection on
  g(beta) = N / beta - S with S = sum ln(T / t_i) over the FIXED bracket
  [BISECT_LO, BISECT_HI] = [1e-6, 10.0] to BISECT_TOL = 1e-12 with at
  most BISECT_MAX_ITER = 200 iterations; the root equals the closed form
  N / S and the spec anchors check the bisection against it within 1e-9.
  lambda_hat = N / total_time**beta_hat (scale). current_mtbf =
  total_time / (N * beta_hat), the standard AMSAA current MTBF (the
  reciprocal of the instantaneous failure intensity lambda beta
  T^(beta - 1) at the truncation time). ValueErrors: fewer than
  MIN_FAILURES = 2 failures, any failure time non-positive or at or
  above total_time, non-positive total_time, and the MLE root outside
  the fixed bracket (g(BISECT_HI) >= 0, which means beta_hat = N / S
  exceeds 10.0; a fit that extreme is rejected rather than silently
  extrapolated). bisection_iterations counts the bisection loop passes
  to convergence.
- projected_mtbf(target_time, total_time, n_failures, beta_hat) -> float
  current_mtbf * (target_time / total_time)**(1 - beta_hat), the MTBF
  the fitted power-law process reaches at a target cumulative test time
  (closed form of 1 / (lambda beta tau^(beta - 1)) with lambda =
  N / T^beta; at target_time = total_time it returns current_mtbf
  exactly). ValueErrors: non-positive target_time or total_time, fewer
  than MIN_FAILURES failures, non-positive beta_hat.
- test_hours_to_target_mtbf(target_mtbf, total_time, n_failures,
  beta_hat) -> float total_time * (target_mtbf * n_failures * beta_hat /
  total_time)**(1 / (1 - beta_hat)), the cumulative test time tau at
  which the projected MTBF equals the target (inverse of
  projected_mtbf; requires beta_hat < 1 so the instantaneous rate keeps
  falling, else the target is unreachable by continued testing under the
  fitted model). ValueErrors: non-positive target_mtbf or total_time,
  fewer than MIN_FAILURES failures, and beta_hat not in (0, 1).
- growth_verdict(beta) -> dict {"beta", "verdict"} with verdict
  "improving" when beta < 1.0 (failure rate decreasing), "hpp-constant"
  when beta == 1.0 (exactly the homogeneous Poisson process, constant
  rate), "degrading" when beta > 1.0. The comparison is against the
  exact 1.0 boundary; a fitted beta of 1.0 needs no tolerance because the
  verdict is read off the returned float.
Module constants: MIN_FAILURES = 2, BISECT_LO = 1e-6, BISECT_HI = 10.0,
BISECT_TOL = 1e-12, BISECT_MAX_ITER = 200.
Duane is the quick graphical check (OLS on the cumulative points);
amsaa_mle is the reference estimator. The two betas agree closely on
growth data and both sit on the same side of 1.0; the SKILL body states
that when they disagree about the improving/degrading side, the AMSAA MLE
governs the verdict.

## Identity to test

Duane slope plus 1 equals beta_duane; amsaa bisection root equals the
closed form N / S within 1e-9; lambda_hat times total_time**beta_hat
equals n_failures; current_mtbf times n_failures times beta_hat equals
total_time; projected_mtbf at target_time equal to total_time returns
current_mtbf exactly; test_hours_to_target_mtbf inverted through
projected_mtbf returns the target MTBF; on the improving worked set both
beta_duane and beta_hat sit below 1.0 and both Duane slopes are negative;
verdict thresholds sit at 1.0 exactly.

## Worked example

Time-truncated development test: total_time = 8000 h with N = 6 failures
at fail_times = [200, 420, 800, 1500, 3000, 5000] h (inter-failure gaps
growing, an improving system).
- duane_fit(fail_times, evaluation_time = 8000.0): slope =
  -0.465700634065, intercept = -2.63108358662, beta_duane =
  0.534299365935, current_mtbf = 1708.25187489 h. The negative slope is
  the Duane growth signature.
- amsaa_mle(fail_times, 8000.0): S = 12.0634793832, beta_hat =
  0.497379804338 (bisection, 43 iterations, matching the closed form
  N / S to 5.21e-13), lambda_hat = 0.0686804475182, current_mtbf =
  2680.71466051 h (= 8000 / (6 * 0.497379804338)). Both estimators place
  beta below 1: improving.
- growth_verdict(0.497379804338): verdict "improving".
- projected_mtbf(12000.0, 8000.0, 6, 0.497379804338) = 3286.68144148 h,
  the MTBF the fitted process reaches at 12,000 cumulative test hours.
- test_hours_to_target_mtbf(5000.0, 8000.0, 6, 0.497379804338) =
  27650.7080495 cumulative test hours to a 5000 h MTBF; projecting back
  to that tau returns 5000.0 exactly (round-trip identity).
Contrast degrading set: fail_times = [500, 800, 1050, 1250, 1400, 1500]
h, total_time = 1600 h: amsaa beta_hat = 2.20390414872, Duane slope =
0.595086501988, current_mtbf = 120.997397651 h, verdict "degrading" (the
positive Duane slope and beta above 1 flag wear-out style data).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified by running /tmp/w41spec/anchor_growth.py (pure
stdlib math, deterministic).

## Validation list (contract test must include)

- duane_fit([200, 420, 800, 1500, 3000, 5000], 8000.0): slope
  -0.465700634065 within 1e-9, beta_duane 0.534299365935 within 1e-9,
  current_mtbf 1708.25187489 within 1e-3.
- amsaa_mle on the worked set: beta_hat 0.497379804338 within 1e-9,
  lambda_hat 0.0686804475182 within 1e-9, current_mtbf 2680.71466051
  within 1e-3; bisection root equals N / S within 1e-9; identity checks:
  lambda_hat * 8000.0**beta_hat == 6 within 1e-9, current_mtbf * 6 *
  beta_hat == 8000.0 within 1e-9.
- projected_mtbf(12000.0, 8000.0, 6, 0.497379804338) = 3286.68144148
  within 1e-3; projected_mtbf(8000.0, ...) equals current_mtbf exactly;
  monotone increasing in target_time while beta < 1.
- test_hours_to_target_mtbf(5000.0, 8000.0, 6, 0.497379804338) =
  27650.7080495 within 1e-3; projected_mtbf at that tau returns 5000.0
  within 1e-6 (round-trip); target below current MTBF still returns the
  closed-form tau below total_time.
- amsaa_mle([500, 800, 1050, 1250, 1400, 1500], 1600.0): beta_hat
  2.20390414872 within 1e-9, current_mtbf 120.997397651 within 1e-3.
- growth_verdict branches: 0.7 "improving", 1.0 "hpp-constant", 1.3
  "degrading"; the verdict dict keys are exactly beta, verdict.
- ValueErrors: duane_fit and amsaa_mle with fewer than 2 failures, a
  zero or negative failure time, decreasing failure times, a failure time
  at or above total_time, non-positive total_time or evaluation_time,
  duane_fit evaluation_time below the last failure time, duane_fit with
  all failure times equal; amsaa_mle on [1000, 1100, 1150, 1175, 1180,
  1185] at total_time 1200 (N / S = 16.56 above the bracket top 10.0,
  root outside the fixed bracket); test_hours_to_target_mtbf with
  beta_hat 1.0 or above (no growth, target unreachable) and non-positive
  target_mtbf; projected_mtbf with non-positive target_time.
- Determinism: repeated runs return bit-identical dicts; the bisection
  returns the same root across runs.

## Corpus fragment (eval/hit1-wave41-reliability-growth-analysis.yaml)

Query 1 (copy verbatim):
  "fit the duane growth curve and the crow-amsaa power-law model to the failure times from the development test to decide whether the actuator failure rate is improving over cumulative test time, then project the cumulative test time at which the fitted MTBF reaches the 5000 hour target"
  intent: "systems-engineering-safety; reliability growth trend analysis: Duane growth slope and Crow-AMSAA shape beta from failure times, improving or degrading verdict, test time to a target MTBF"
  expected_skill: "systems-engineering-safety/arp4761a/reliability-growth-analysis"
Query 2 (copy verbatim):
  "compute the crow-amsaa shape beta from the cumulative failure times and the truncation time of the field test, report the current MTBF, and state whether the failure rate is improving, constant, or degrading under the growth verdict"
  intent: "systems-engineering-safety; reliability growth trend test on cumulative failure times: Crow-AMSAA shape beta, current MTBF, improving versus degrading verdict"
Task ids: w41-reliability-growth-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine whether a system
failure rate is improving over development or field test time:" and
include the outputs in the Claim. First tag: reliability-growth-analysis.
Additional tags ONLY: duane-growth-slope, amsaa-shape-beta,
growth-verdict, test-time-projection. NEVER single generic words (rate,
failure, trend, reliability, test, time, growth, mtbf, hours alone).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): chi-square, upper-bound,
lower-bound, zero-failure, poisson, confidence, demonstration, constant-
rate point estimate (failure-rate-estimation); service-difficulty-report,
single-event-rule, fleet-exposure, observed-versus-predicted-rate,
safety-significance (in-service-safety-assessment); closure-gate,
condition-margin, severity-target, requirement-closure-status
(ssa-closure); mission-reliability, block-reliability, redundancy-
arrangement, design-life (reliability-block-diagram). The word "MTBF"
alone is shared with failure-rate-estimation and reliability-block-
diagram, so the description and corpus queries must always pair it with a
growth term (current-mtbf under the fitted model, projected-mtbf,
target-mtbf of the projection), never with chi-square or demonstration
language.

"""Reliability growth analysis for development and field test failure times.

Pure stdlib implementation of the two standard ARP4761A reliability-growth
estimators over ordered cumulative failure times, plus the test-time
projection and the growth verdict:

- duane_fit: ordinary least squares of the log cumulative failure rate
  ln(i / t_i) on the log cumulative time ln(t_i) over the N failure-event
  points. The fitted slope is beta_duane - 1 and the intercept is
  ln(lambda), so beta_duane = slope + 1.
- amsaa_mle: maximum likelihood estimate of the Crow-AMSAA power-law
  process shape beta (the MIL-HDBK-189 reliability-growth method, named
  and paraphrased here, no verbatim text) solved by deterministic
  bisection of g(beta) = N / beta - S on the fixed bracket
  [BISECT_LO, BISECT_HI], with S = sum(ln(total_time / t_i)).
- projected_mtbf and test_hours_to_target_mtbf: the MTBF the fitted
  power-law process reaches at a target cumulative test time, and its
  inverse, the cumulative test hours at which the fitted MTBF equals a
  target value.
- growth_verdict: improving below beta 1.0, hpp-constant at exactly
  1.0, degrading above 1.0.

No randomness, no external dependencies: every function is deterministic
and rejects non-physical inputs with ValueError.
"""

import math

MIN_FAILURES = 2
BISECT_LO = 1e-6
BISECT_HI = 10.0
BISECT_TOL = 1e-12
BISECT_MAX_ITER = 200


def _coerce_times(fail_times):
    """Return fail_times as a list of floats after physical-order checks."""
    times = [float(t) for t in fail_times]
    if len(times) < MIN_FAILURES:
        raise ValueError(
            "at least %d failure events are required, got %d"
            % (MIN_FAILURES, len(times)))
    for t in times:
        if not math.isfinite(t) or t <= 0.0:
            raise ValueError("failure times must be positive and finite")
    for prev, nxt in zip(times, times[1:]):
        if nxt < prev:
            raise ValueError("failure times must be non-decreasing over time")
    return times


def _check_positive(value, name):
    """Reject a non-positive or non-finite numeric input."""
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be positive and finite" % name)
    return value


def duane_fit(fail_times, evaluation_time=None):
    """Fit the Duane plot by OLS and return the growth line summary.

    Cumulative point i of the Duane plot is (t_i, i), so the cumulative
    failure rate at t_i is i / t_i. OLS of y_i = ln(i / t_i) on
    x_i = ln(t_i) over all N failure events yields the slope and
    intercept; under the power-law process the cumulative rate is
    lambda * t**(beta - 1), so the Duane slope equals beta - 1 and the
    intercept equals ln(lambda), giving beta_duane = slope + 1.
    current_mtbf is the instantaneous MTBF of the fitted line at
    evaluation_time (default the last failure time):
    exp(-intercept) / (beta_duane * evaluation_time**(beta_duane - 1)).

    ValueErrors: fewer than MIN_FAILURES failures, a non-positive or
    non-finite failure time, decreasing failure times, a non-positive
    evaluation_time, an evaluation_time below the last failure time, and
    zero ln-time variance (all failure times equal).
    """
    times = _coerce_times(fail_times)
    if evaluation_time is None:
        evaluation_time = times[-1]
    else:
        evaluation_time = _check_positive(evaluation_time, "evaluation_time")
    if evaluation_time < times[-1]:
        raise ValueError(
            "evaluation_time must not lie below the last failure time")
    if times[0] == times[-1]:
        raise ValueError(
            "all failure times equal: zero ln-time variance, OLS undefined")
    xs = [math.log(t) for t in times]
    ys = [math.log(float(i + 1) / t) for i, t in enumerate(times)]
    x_bar = sum(xs) / len(xs)
    y_bar = sum(ys) / len(ys)
    sxx = sum((x - x_bar) ** 2 for x in xs)
    sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    if sxx == 0.0:
        raise ValueError(
            "all failure times equal: zero ln-time variance, OLS undefined")
    slope = sxy / sxx
    intercept = y_bar - slope * x_bar
    beta_duane = slope + 1.0
    current_mtbf = math.exp(-intercept) / (
        beta_duane * evaluation_time ** (beta_duane - 1.0))
    return {
        "slope": slope,
        "intercept": intercept,
        "beta_duane": beta_duane,
        "evaluation_time": float(evaluation_time),
        "current_mtbf": current_mtbf,
    }


def _bisect_mle_root(n_failures, s_total):
    """Solve N / beta = S for beta by bisection over the fixed bracket.

    g(beta) = N / beta - S is strictly decreasing on the positive axis,
    so the MLE root N / S is bracketed whenever g(BISECT_HI) < 0. A root
    at or above BISECT_HI (g(BISECT_HI) >= 0, so N / S >= BISECT_HI) is
    rejected rather than silently extrapolated. Returns (root, passes)
    where passes counts the bisection loop passes to convergence.
    """
    if n_failures / BISECT_LO - s_total <= 0.0:
        raise ValueError(
            "MLE root below the fixed bracket: the fit is outside "
            "[BISECT_LO, BISECT_HI]")
    if n_failures / BISECT_HI - s_total >= 0.0:
        raise ValueError(
            "MLE root outside the fixed bracket: N / S reaches or exceeds "
            "the bracket top %.3g; reject rather than extrapolate"
            % BISECT_HI)
    lo = BISECT_LO
    hi = BISECT_HI
    passes = 0
    while (hi - lo) / 2.0 > BISECT_TOL and passes < BISECT_MAX_ITER:
        mid = (lo + hi) / 2.0
        if n_failures / mid - s_total > 0.0:
            lo = mid
        else:
            hi = mid
        passes += 1
    return (lo + hi) / 2.0, passes


def amsaa_mle(fail_times, total_time):
    """Crow-AMSAA power-law process MLE of shape and scale.

    The power-law NHPP mean function is E[N(t)] = lambda * t**beta (the
    MIL-HDBK-189 reliability-growth method, named and paraphrased, no
    verbatim text). With S = sum over failures of ln(total_time / t_i)
    the profile-likelihood MLE equation sum ln(T / t_i) = N / beta_hat
    has the closed form beta_hat = N / S, solved here by deterministic
    bisection on the fixed bracket so the module owns the root; the
    spec anchors check the bisection against N / S within 1e-9.
    lambda_hat = N / total_time**beta_hat, and current_mtbf =
    total_time / (N * beta_hat), the standard AMSAA current MTBF (the
    reciprocal of the instantaneous intensity lambda * beta * T**(beta-1)
    at the truncation time).

    ValueErrors: fewer than MIN_FAILURES failures, any failure time
    non-positive or at or above total_time, a non-positive total_time,
    decreasing failure times, and an MLE root outside the fixed bracket.
    """
    times = _coerce_times(fail_times)
    total = _check_positive(total_time, "total_time")
    for t in times:
        if t >= total:
            raise ValueError(
                "failure time %g lies at or above the truncation time %g"
                % (t, total))
    s_total = sum(math.log(total / t) for t in times)
    beta_hat, passes = _bisect_mle_root(len(times), s_total)
    lambda_hat = len(times) / (total ** beta_hat)
    current_mtbf = total / (len(times) * beta_hat)
    return {
        "beta_hat": beta_hat,
        "lambda_hat": lambda_hat,
        "n_failures": len(times),
        "total_time": total,
        "current_mtbf": current_mtbf,
        "bisection_iterations": passes,
    }


def projected_mtbf(target_time, total_time, n_failures, beta_hat):
    """Project the fitted MTBF to a target cumulative test time.

    Returns current_mtbf * (target_time / total_time)**(1 - beta_hat),
    the closed form of 1 / (lambda * beta * tau**(beta - 1)) with
    lambda = N / total_time**beta_hat and current_mtbf =
    total_time / (N * beta_hat); at target_time equal to total_time it
    returns current_mtbf exactly. ValueErrors: non-positive target_time
    or total_time, fewer than MIN_FAILURES failures, non-positive
    beta_hat.
    """
    target = _check_positive(target_time, "target_time")
    total = _check_positive(total_time, "total_time")
    n_failures = int(n_failures)
    if n_failures < MIN_FAILURES:
        raise ValueError(
            "at least %d failures required for the projection, got %d"
            % (MIN_FAILURES, n_failures))
    beta = _check_positive(beta_hat, "beta_hat")
    current_mtbf = total / (n_failures * beta)
    return current_mtbf * (target / total) ** (1.0 - beta)


def test_hours_to_target_mtbf(target_mtbf, total_time, n_failures, beta_hat):
    """Return the cumulative test hours at which the fitted MTBF reaches target.

    Returns total_time * (target_mtbf * n_failures * beta_hat /
    total_time)**(1 / (1 - beta_hat)), the inverse of projected_mtbf:
    the cumulative test time tau at which the projected MTBF equals the
    target. Requires beta_hat in (0, 1) so the instantaneous rate keeps
    falling; at or above 1.0 the target is unreachable by continued
    testing under the fitted model. ValueErrors: non-positive
    target_mtbf or total_time, fewer than MIN_FAILURES failures,
    beta_hat not in (0, 1).
    """
    target = _check_positive(target_mtbf, "target_mtbf")
    total = _check_positive(total_time, "total_time")
    n_failures = int(n_failures)
    if n_failures < MIN_FAILURES:
        raise ValueError(
            "at least %d failures required for the projection, got %d"
            % (MIN_FAILURES, n_failures))
    beta = _check_positive(beta_hat, "beta_hat")
    if beta >= 1.0:
        raise ValueError(
            "beta_hat %g is not below 1.0: the instantaneous rate is not "
            "falling, the target MTBF is unreachable by continued testing"
            % beta)
    return total * (target * n_failures * beta / total) ** (1.0 / (1.0 - beta))


def growth_verdict(beta):
    """Rate the fitted shape against the exact 1.0 boundary.

    Verdict "improving" when beta < 1.0 (failure rate decreasing),
    "hpp-constant" when beta == 1.0 (exactly the homogeneous Poisson
    process at constant rate), "degrading" when beta > 1.0. The
    comparison is against the exact 1.0 boundary; a fitted beta of 1.0
    needs no tolerance because the verdict is read off the returned
    float. The dict keys are exactly beta and verdict.
    """
    beta = float(beta)
    if beta < 1.0:
        verdict = "improving"
    elif beta == 1.0:
        verdict = "hpp-constant"
    else:
        verdict = "degrading"
    return {"beta": beta, "verdict": verdict}

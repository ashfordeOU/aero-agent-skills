"""L1 adaptive control for a first-order plant with an unknown coefficient.

Pure stdlib, deterministic, discrete-time Euler integration, scalar
state. The controller knows only the design model pole a_m < 0, the
control effectiveness b > 0 and a prior interval on the true plant
coefficient a_p; an unknown constant matched disturbance d acts on the
plant. The truth plant (simulator only) is x_dot = a_p*x + b*u + b*d,
which reads x_dot = a_m*x + b*(u + sigma_true) in the design frame with
the lumped matched uncertainty sigma_true(x) = (a_p - a_m)*x/b + d.

Architecture (Cao and Hovakimyan, L1 Adaptive Control Theory, SIAM
2010, scalar chapter-2 sigma-only specialization):

- State predictor: xh_dot = a_m*xh + b*(u + sigma_hat), run from the
  same initial state as the plant. Prediction error: xt = xh - x.
- Projection-based adaptation law on the prediction error:
  sigma_hat_dot = gamma * Proj(sigma_hat, -xt), discrete clamped Euler
  step raw = sigma_hat - dt*gamma*xt then clamp to [-sigma_b, sigma_b].
- Low-pass filter C(s) = omega_c/(s + omega_c) on the adaptive signal:
  nu_dot = omega_c*(sigma_hat - nu).
- Control law: u = k_g*r - nu with k_g = -a_m/b (feedforward for unit
  DC command tracking minus the filtered cancellation estimate).
- Reference model: xm_dot = a_m*xm + b_m*r sets the command response;
  the tracking error is e = x - xm.

Histories are seeded with the initial values at index 0 and have length
steps + 1, so history[k] is the value at time k*dt (after k advances).
Pinned Euler ordering per step: sample the prediction error, update the
adaptive estimate with the projection law, advance the low-pass filter
on the updated estimate, form the control, advance plant, predictor and
reference model by dt, then append the post-advance histories.

Deterministic: plain explicit scalar arithmetic, math only, no RNG, no
external solvers.
"""

import math

# Module constants (pinned worked scenario).
A_M = -1.0       # design model pole (a_m < 0)
B = 2.0          # control effectiveness, known positive
B_M = 1.0        # reference input gain, unit DC (b_m = -a_m)
R = 1.0          # constant command
X0 = 0.0         # initial state of plant, predictor and reference model
DT = 0.01        # integration step, s
GAMMA = 10.0     # adaptation rate
OMEGA_C = 10.0   # low-pass filter bandwidth, rad/s
SIGMA_B = 2.0    # projection bound on sigma_hat
D = 1.0          # unknown constant matched disturbance
A_LO = -1.0      # prior lower bound on a_p
A_HI = -0.25     # prior upper bound on a_p
PLANT_A = -0.5   # true plant coefficient (simulator secret)
N_STEPS = 6000   # run length in steps (60 s)
TAIL = 1000      # verdict tail window in steps

# Derived constants.
KG = -A_M / B          # 0.5, feedforward gain for unit DC tracking
SIGMA_MISMATCH = (PLANT_A - A_M) / B   # 0.25, x-coupling of sigma_true
E_BOUND = 0.75         # certified transient bound of the worked scenario

# Verdict thresholds used by convergence_report.
_TAIL_PRED_TOL = 1e-4   # max |xt| over the tail
_TAIL_DRIFT_TOL = 1e-6  # max per-step sigma_hat drift over the tail
_SIGMA_DEV_TOL = 0.05   # final |sigma_hat - sigma_ideal|


def _require_finite(*values):
    """Raise ValueError unless every argument is a finite real number."""
    for v in values:
        if not math.isfinite(v):
            raise ValueError("arguments must be finite real numbers")


def projection(sigma_hat, d, sigma_b=SIGMA_B):
    """Continuous projection of direction d at sigma_hat onto [-sigma_b, sigma_b].

    Returns d when sigma_hat is strictly interior, or when sigma_hat is
    at a bound and d points inward (sigma_hat * d <= 0 at the bound);
    returns 0.0 when sigma_hat is at a bound and d points outward.
    """
    if sigma_b <= 0:
        raise ValueError("projection bound sigma_b must be positive")
    if abs(sigma_hat) > sigma_b:
        raise ValueError("|sigma_hat| must not exceed sigma_b")
    if sigma_hat >= sigma_b and d > 0.0:
        return 0.0
    if sigma_hat <= -sigma_b and d < 0.0:
        return 0.0
    return d


def adaptive_update(sigma_hat, pred_err, gamma=GAMMA, dt=DT,
                    sigma_b=SIGMA_B):
    """One clamped Euler projection step of the adaptive law.

    raw = sigma_hat - dt*gamma*pred_err, then clamp to [-sigma_b,
    sigma_b]: sigma_hat_new = max(-sigma_b, min(sigma_b, raw)).
    Guarantees |sigma_hat| <= sigma_b after every step.
    """
    if gamma < 0:
        raise ValueError("adaptation rate gamma must be >= 0")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    if sigma_b <= 0:
        raise ValueError("projection bound sigma_b must be positive")
    _require_finite(sigma_hat, pred_err, gamma, dt, sigma_b)
    raw = sigma_hat - dt * gamma * pred_err
    return max(-sigma_b, min(sigma_b, raw))


def filter_step(nu, sigma_hat, omega_c=OMEGA_C, dt=DT):
    """One Euler step of the L1 low-pass filter nu_dot = omega_c*(sigma_hat - nu)."""
    if omega_c <= 0:
        raise ValueError("filter bandwidth omega_c must be positive")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    _require_finite(nu, sigma_hat, omega_c, dt)
    return nu + dt * omega_c * (sigma_hat - nu)


def control_output(nu, r=R, a_m=A_M, b=B):
    """L1 control law u = (-a_m/b)*r - nu: feedforward minus filtered estimate."""
    if b == 0:
        raise ValueError("control effectiveness b must be nonzero")
    _require_finite(nu, r, a_m, b)
    return (-a_m / b) * r - nu


def plant_step(x, u, plant_a=PLANT_A, b=B, d=D, dt=DT):
    """One Euler step of the truth plant x_dot = a_p*x + b*u + b*d.

    Simulator only: the controller never sees a_p or d directly.
    """
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    _require_finite(x, u, plant_a, b, d, dt)
    return x + dt * (plant_a * x + b * u + b * d)


def predictor_step(xh, u, sigma_hat, a_m=A_M, b=B, dt=DT):
    """One Euler step of the state predictor xh_dot = a_m*xh + b*(u + sigma_hat)."""
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    _require_finite(xh, u, sigma_hat, a_m, b, dt)
    return xh + dt * (a_m * xh + b * (u + sigma_hat))


def reference_step(xm, r=R, a_m=A_M, b_m=B_M, dt=DT):
    """One Euler step of the reference model xm_dot = a_m*xm + b_m*r.

    The reference model must be stable (a_m < 0); it settles at
    b_m*r/(-a_m) for a constant command.
    """
    if a_m >= 0:
        raise ValueError("reference model must be stable (a_m < 0)")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    _require_finite(xm, r, a_m, b_m, dt)
    return xm + dt * (a_m * xm + b_m * r)


def sigma_true(x, plant_a=PLANT_A, a_m=A_M, b=B, d=D):
    """Lumped matched uncertainty (a_p - a_m)*x/b + d in the design frame.

    Simulator bookkeeping only; never an input to the controller.
    """
    if b == 0:
        raise ValueError("control effectiveness b must be nonzero")
    _require_finite(x, plant_a, a_m, b, d)
    return (plant_a - a_m) * x / b + d


def sigma_ideal(x_final, plant_a=PLANT_A, a_m=A_M, b=B, d=D):
    """Ideal cancellation value of sigma_true at the settled state.

    Assessment target only (mirrors ideal_gains of the MRAC sibling
    leaf); never an input to the controller.
    """
    return sigma_true(x_final, plant_a=plant_a, a_m=a_m, b=b, d=d)


def reference_closed_form(k, r=R, a_m=A_M, b_m=B_M, dt=DT):
    """Closed form of the Euler reference-model march from a zero state.

    (b_m*r/(-a_m)) * (1 - (1 + a_m*dt)^k), exact per index k.
    """
    return (b_m * r / (-a_m)) * (1.0 - (1.0 + a_m * dt) ** k)


def filter_closed_form(nu0, sigma_const, omega_c, dt, k):
    """Exact Euler march of the filter under constant input sigma_const.

    sigma_const + (nu0 - sigma_const) * (1 - omega_c*dt)^k.
    """
    return sigma_const + (nu0 - sigma_const) * (1.0 - omega_c * dt) ** k


def no_adaptation_closed_form(k, x0=X0, plant_a=PLANT_A, b=B, d=D, dt=DT):
    """Plant march with sigma_hat identically zero (u = k_g*r constant).

    x_star - (x_star - x0) * (1 + a_p*dt)^k with x_star =
    -(b*k_g*r + b*d)/a_p = 6.0 at the worked plant: the march converges
    to the WRONG equilibrium without adaptation.
    """
    x_star = -(b * KG * R + b * d) / plant_a
    return x_star - (x_star - x0) * (1.0 + plant_a * dt) ** k


def simulate(plant_a=PLANT_A, a_m=A_M, b=B, b_m=B_M, r=R, x0=X0, d=D,
             dt=DT, gamma=GAMMA, omega_c=OMEGA_C, sigma_b=SIGMA_B,
             steps=N_STEPS):
    """Simulate the L1 closed loop and report the histories and metrics.

    All five states start at their initial values (x, xh and xm at x0,
    sigma_hat and nu at 0, control at k_g*r). Pinned Euler ordering per
    step: sample the prediction error xt = xh - x, update sigma_hat
    with the clamped projection law, advance the filter on the updated
    estimate, form the control u = k_g*r - nu, advance plant, predictor
    and reference model by dt, then append the post-advance values.

    Returns a dict with keys x, xm, xh, u, sigma_hat, nu, pred_err,
    track_err (each a list of length steps + 1, index 0 the initial
    value; errors are xh - x and x - xm of the state histories),
    proj_active (count of steps whose raw adaptation step was clamped),
    max_abs_track, max_abs_pred, max_abs_sigma, tail_abs_pred (max |xt|
    over the last TAIL steps) and tail_sigma_drift (max per-step
    |sigma_hat| change over the last TAIL steps).
    """
    if a_m >= 0:
        raise ValueError("reference model must be stable (a_m < 0)")
    if b == 0:
        raise ValueError("control effectiveness b must be nonzero")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    if gamma < 0:
        raise ValueError("adaptation rate gamma must be >= 0")
    if omega_c <= 0:
        raise ValueError("filter bandwidth omega_c must be positive")
    if sigma_b <= 0:
        raise ValueError("projection bound sigma_b must be positive")
    if steps < 2:
        raise ValueError("steps must be at least 2")
    _require_finite(plant_a, a_m, b, b_m, r, x0, d, dt, gamma, omega_c,
                    sigma_b)

    x = x0
    xh = x0
    xm = x0
    sigma_hat = 0.0
    nu = 0.0

    kg = -a_m / b
    u = kg * r

    x_list = [x]
    xm_list = [xm]
    xh_list = [xh]
    u_list = [u]
    sigma_hat_list = [sigma_hat]
    nu_list = [nu]

    proj_active = 0

    for _ in range(steps):
        xt = xh - x
        raw = sigma_hat - dt * gamma * xt
        sigma_hat_new = max(-sigma_b, min(sigma_b, raw))
        if raw > sigma_b or raw < -sigma_b:
            proj_active += 1
        nu = nu + dt * omega_c * (sigma_hat_new - nu)
        u = kg * r - nu
        x = x + dt * (plant_a * x + b * u + b * d)
        xh = xh + dt * (a_m * xh + b * (u + sigma_hat_new))
        xm = xm + dt * (a_m * xm + b_m * r)
        sigma_hat = sigma_hat_new

        x_list.append(x)
        xm_list.append(xm)
        xh_list.append(xh)
        u_list.append(u)
        sigma_hat_list.append(sigma_hat)
        nu_list.append(nu)

    pred_err = [hi - xi for hi, xi in zip(xh_list, x_list)]
    track_err = [xi - mi for xi, mi in zip(x_list, xm_list)]

    # Tail window: the last TAIL step intervals, times 50.00 to 60.00 s
    # at the worked run, i.e. history indices steps - TAIL .. steps.
    tail_start = steps - TAIL
    tail_abs_pred = max(abs(p) for p in pred_err[tail_start:])
    tail_sigma_drift = max(
        abs(sigma_hat_list[i] - sigma_hat_list[i - 1])
        for i in range(tail_start + 1, steps + 1)
    )
    max_abs_track = max(abs(e) for e in track_err)
    max_abs_pred = max(abs(p) for p in pred_err)
    max_abs_sigma = max(abs(s) for s in sigma_hat_list)

    return {
        "x": x_list,
        "xm": xm_list,
        "xh": xh_list,
        "u": u_list,
        "sigma_hat": sigma_hat_list,
        "nu": nu_list,
        "pred_err": pred_err,
        "track_err": track_err,
        "proj_active": proj_active,
        "max_abs_track": max_abs_track,
        "max_abs_pred": max_abs_pred,
        "max_abs_sigma": max_abs_sigma,
        "tail_abs_pred": tail_abs_pred,
        "tail_sigma_drift": tail_sigma_drift,
    }


def convergence_report(res, plant_a=PLANT_A, a_m=A_M, b=B, d=D):
    """Convergence verdict on a simulate() result and its criteria dict.

    Returns (converged, criteria). converged is True iff
    res["tail_abs_pred"] < 1e-4 AND res["tail_sigma_drift"] < 1e-6 AND
    |sigma_hat_final - sigma_ideal(x_final)| < 0.05. The criteria dict
    carries tail_abs_pred, tail_sigma_drift, sigma_dev and sigma_ideal.
    """
    x_final = res["x"][-1]
    sigma_ideal_value = sigma_ideal(x_final, plant_a=plant_a, a_m=a_m,
                                   b=b, d=d)
    sigma_dev = abs(res["sigma_hat"][-1] - sigma_ideal_value)
    criteria = {
        "tail_abs_pred": res["tail_abs_pred"],
        "tail_sigma_drift": res["tail_sigma_drift"],
        "sigma_dev": sigma_dev,
        "sigma_ideal": sigma_ideal_value,
    }
    converged = (res["tail_abs_pred"] < _TAIL_PRED_TOL and
                 res["tail_sigma_drift"] < _TAIL_DRIFT_TOL and
                 sigma_dev < _SIGMA_DEV_TOL)
    return converged, criteria

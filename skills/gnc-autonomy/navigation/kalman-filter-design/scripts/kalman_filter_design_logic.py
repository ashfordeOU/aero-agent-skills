#!/usr/bin/env python3
"""Discrete-time Kalman filter design logic (paraphrase, common knowledge).

The scalar (single-axis) discrete-time Kalman filter is textbook
estimation theory (Gelb, Brown and Hwang, Maybeck): for the linear
model

  x_k = f * x_(k-1) + w_k      w_k ~ N(0, q)   process noise
  z_k = h * x_k + v_k          v_k ~ N(0, r)   measurement noise

the filter alternates a predict step and an update step:

  predict:  x_pred = f * x_prev            p_pred = f^2 * p_prev + q
  update:   y = z - h * x_pred             (innovation)
            S = h^2 * p_pred + r           (innovation variance)
            K = h * p_pred / S             (Kalman gain)
            x_new = x_pred + K * y         (corrected state)
            p_new = (1 - K * h) * p_pred   (corrected covariance)

State x and measurement z carry the unit of the tracked quantity
(meters for a position estimate); the covariances p, q, r carry the
unit squared (m^2, m^2 per step, m^2). The gain K is dimensionless
and lies in [0, 1/h] for h > 0. With a constant model f = 1 and
unit measurement h = 1, the predicted covariance converges to the
steady-state root of the scalar algebraic Riccati equation and the
a-posteriori covariance settles below it, at the root minus the
gain-weighted innovation term.

Reference note: ARP4754A (standards-map.yaml, gated, reference-only)
frames development assurance for aircraft systems; the Kalman filter
itself is common estimation-theory knowledge and is only summarized
here.
"""

import math

_TOL = 1e-12


def _scalar(value, name):
    """Cast a scalar to float; raise ValueError on non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))


def predict(x_prev, p_prev, f, q):
    """Predict step: x_pred = f * x_prev, p_pred = f^2 * p_prev + q.

    Returns (x_pred, p_pred). Raises ValueError on non-numeric input,
    negative covariance p_prev < 0, or process noise q < 0.
    """
    x = _scalar(x_prev, "x_prev")
    p = _scalar(p_prev, "p_prev")
    ff = _scalar(f, "f")
    qq = _scalar(q, "q")
    if p < 0.0:
        raise ValueError("covariance p_prev must be >= 0, got %g" % (p,))
    if qq < 0.0:
        raise ValueError("process noise q must be >= 0, got %g" % (qq,))
    return ff * x, ff * ff * p + qq


def innovation(z, x_pred, h):
    """Innovation y = z - h * x_pred, the measurement residual."""
    zz = _scalar(z, "z")
    xp = _scalar(x_pred, "x_pred")
    hh = _scalar(h, "h")
    return zz - hh * xp


def innovation_variance(p_pred, h, r):
    """Innovation variance S = h^2 * p_pred + r.

    Raises ValueError on negative predicted covariance or measurement
    noise r <= 0 (a zero-variance measurement is degenerate).
    """
    p = _scalar(p_pred, "p_pred")
    hh = _scalar(h, "h")
    rr = _scalar(r, "r")
    if p < 0.0:
        raise ValueError("covariance p_pred must be >= 0, got %g" % (p,))
    if rr <= 0.0:
        raise ValueError("measurement noise r must be > 0, got %g" % (rr,))
    return hh * hh * p + rr


def kalman_gain(p_pred, h, r):
    """Kalman gain K = h * p_pred / (h^2 * p_pred + r).

    Dimensionless, in [0, 1/h] for h > 0. Raises ValueError on
    negative covariance or non-positive measurement noise.
    """
    p = _scalar(p_pred, "p_pred")
    hh = _scalar(h, "h")
    rr = _scalar(r, "r")
    if p < 0.0:
        raise ValueError("covariance p_pred must be >= 0, got %g" % (p,))
    if rr <= 0.0:
        raise ValueError("measurement noise r must be > 0, got %g" % (rr,))
    denom = hh * hh * p + rr
    if denom <= _TOL:
        raise ValueError("innovation variance is zero; filter is degenerate")
    return hh * p / denom


def update(x_pred, p_pred, z, h, r):
    """Full update step from a measurement z.

    Returns a dict with 'innovation' y, 'innovation_variance' S,
    'gain' K, 'state' x_new, and 'covariance' p_new. Raises
    ValueError on invalid covariance or noise inputs.
    """
    xp = _scalar(x_pred, "x_pred")
    p = _scalar(p_pred, "p_pred")
    zz = _scalar(z, "z")
    hh = _scalar(h, "h")
    rr = _scalar(r, "r")
    y = innovation(zz, xp, hh)
    s = innovation_variance(p, hh, rr)
    k = kalman_gain(p, hh, rr)
    x_new = xp + k * y
    p_new = (1.0 - k * hh) * p
    return {
        "innovation": y,
        "innovation_variance": s,
        "gain": k,
        "state": x_new,
        "covariance": p_new,
    }


def kalman_step(x, p, z, f=1.0, h=1.0, q=0.0, r=1.0):
    """One full predict + update cycle at time k.

    Returns a dict with 'predicted_state', 'predicted_covariance',
    'innovation', 'innovation_variance', 'gain', 'state',
    'covariance'. Defaults are the constant-position model with unit
    measurement: f = 1, h = 1.
    """
    x_pred, p_pred = predict(x, p, f, q)
    upd = update(x_pred, p_pred, z, h, r)
    upd["predicted_state"] = x_pred
    upd["predicted_covariance"] = p_pred
    return upd


def run_filter(measurements, x0, p0, f=1.0, h=1.0, q=0.0, r=1.0):
    """Filter a batch of measurements, returning the full trajectory.

    Returns a dict with 'states', 'covariances', 'gains',
    'innovations', and 'innovation_variances' as lists in time order.
    Raises ValueError on an empty measurement list or invalid inputs.
    """
    if not measurements:
        raise ValueError("measurements must be a non-empty list")
    x = _scalar(x0, "x0")
    p = _scalar(p0, "p0")
    ff = _scalar(f, "f")
    hh = _scalar(h, "h")
    qq = _scalar(q, "q")
    rr = _scalar(r, "r")
    states = []
    covs = []
    gains = []
    inns = []
    inn_vars = []
    for z in measurements:
        step = kalman_step(x, p, z, ff, hh, qq, rr)
        x = step["state"]
        p = step["covariance"]
        states.append(x)
        covs.append(p)
        gains.append(step["gain"])
        inns.append(step["innovation"])
        inn_vars.append(step["innovation_variance"])
    return {
        "states": states,
        "covariances": covs,
        "gains": gains,
        "innovations": inns,
        "innovation_variances": inn_vars,
    }


def steady_state_covariance(f, h, q, r):
    """Steady a-priori (predicted) covariance, positive Riccati root.

    Solves the scalar algebraic Riccati equation
    P = f^2 P - f^2 P h^2 P / (h^2 P + r) + q for the positive root,
    the predicted-covariance value the filter converges to after many
    updates (the a-posteriori covariance settles at P - K h P). Valid
    for h nonzero, q >= 0, r > 0. Raises ValueError for h = 0, q < 0,
    or r <= 0.
    """
    ff = _scalar(f, "f")
    hh = _scalar(h, "h")
    qq = _scalar(q, "q")
    rr = _scalar(r, "r")
    if hh == 0.0:
        raise ValueError("measurement matrix h must be nonzero")
    if qq < 0.0:
        raise ValueError("process noise q must be >= 0, got %g" % (qq,))
    if rr <= 0.0:
        raise ValueError("measurement noise r must be > 0, got %g" % (rr,))
    b = rr * (1.0 - ff * ff) - qq * hh * hh
    disc = b * b + 4.0 * hh * hh * qq * rr
    return (-b + math.sqrt(disc)) / (2.0 * hh * hh)

#!/usr/bin/env python3
"""Alpha-beta tracking filter logic (paraphrase, common knowledge).

The alpha-beta filter is a fixed-gain tracking filter for a
constant-velocity target (Kalata tracking index; Benedict and
Bordner; textbook radar tracking literature). At each sample time k
with interval dt:

  predict:  x_pred = x + dt * v          (predicted position)
            v_pred = v                   (predicted velocity)
  residual: r = z - x_pred               (measurement residual)
  update:   x_new = x_pred + alpha * r          (updated position)
            v_new = v_pred + (beta / dt) * r    (updated velocity)

alpha weights the position correction and beta weights the velocity
correction; both are dimensionless constants in the stable region
0 <= alpha < 2 and 0 <= beta < 4 - 2*alpha. With alpha = 1 and
beta = 1 the updated position equals the raw measurement.

Steady-state gain selection:

- Benedict-Bordner critical damping from the smoothing factor:
  beta = alpha^2 / (2 - alpha), valid for alpha in (0, 2).
- Kalata tracking index (maneuverability index):
  lambda = sigma_w * dt^2 / sigma_v, the ratio of target process
  noise sigma_w, sample interval dt, and measurement noise sigma_v.
  Critical-damping gains:

    alpha = -(lambda^2 + 8*lambda - (lambda + 4)*sqrt(lambda^2 + 8*lambda)) / 8
    beta  = (lambda^2 + 4*lambda - lambda*sqrt(lambda^2 + 8*lambda)) / 4

  For lambda -> 0 the gains tend to (0, 0); for lambda -> infinity
  they tend to (1, 2).

Units: positions in the tracked unit (meters), velocities in unit
per second (m/s), dt in seconds, gains dimensionless.

Reference note: ARP4754A (standards-map.yaml, reference-only) frames
development assurance for aircraft systems; the alpha-beta filter
itself is common tracking-filter knowledge and is only summarized
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


def predict(x, v, dt):
    """Predict step: x_pred = x + dt * v, v_pred = v.

    Returns (x_pred, v_pred). Raises ValueError on non-numeric input
    or a non-positive sample interval dt.
    """
    xx = _scalar(x, "x")
    vv = _scalar(v, "v")
    tt = _scalar(dt, "dt")
    if tt <= 0.0:
        raise ValueError("sample interval dt must be > 0, got %g" % (tt,))
    return xx + tt * vv, vv


def residual(z, x_pred):
    """Measurement residual r = z - x_pred."""
    return _scalar(z, "z") - _scalar(x_pred, "x_pred")


def update(x_pred, v_pred, z, dt, alpha, beta):
    """Full update step from a measurement z at interval dt.

    Returns a dict with 'residual' r, 'position' x_new, and
    'velocity' v_new. Raises ValueError on invalid gains, a
    non-positive dt, or non-numeric input.
    """
    xp = _scalar(x_pred, "x_pred")
    vp = _scalar(v_pred, "v_pred")
    zz = _scalar(z, "z")
    tt = _scalar(dt, "dt")
    aa = _scalar(alpha, "alpha")
    bb = _scalar(beta, "beta")
    if tt <= 0.0:
        raise ValueError("sample interval dt must be > 0, got %g" % (tt,))
    if not (0.0 <= aa < 2.0):
        raise ValueError("alpha must be in [0, 2), got %g" % (aa,))
    if not (0.0 <= bb < 4.0 - 2.0 * aa):
        raise ValueError("beta must be in [0, 4 - 2*alpha), got %g" % (bb,))
    r = zz - xp
    x_new = xp + aa * r
    v_new = vp + (bb / tt) * r
    return {"residual": r, "position": x_new, "velocity": v_new}


def step(x, v, z, dt, alpha, beta):
    """One full predict + update cycle at time k.

    Returns a dict with 'predicted_position', 'predicted_velocity',
    'residual', 'position', and 'velocity'.
    """
    x_pred, v_pred = predict(x, v, dt)
    upd = update(x_pred, v_pred, z, dt, alpha, beta)
    upd["predicted_position"] = x_pred
    upd["predicted_velocity"] = v_pred
    return upd


def run_tracker(measurements, dt, alpha, beta, x0=0.0, v0=0.0):
    """Filter a batch of position measurements with fixed gains.

    Returns a dict with 'positions', 'velocities', 'residuals', and
    'predicted_positions' as lists in time order. Raises ValueError
    on an empty measurement list or invalid inputs.
    """
    if not measurements:
        raise ValueError("measurements must be a non-empty list")
    tt = _scalar(dt, "dt")
    aa = _scalar(alpha, "alpha")
    bb = _scalar(beta, "beta")
    x = _scalar(x0, "x0")
    v = _scalar(v0, "v0")
    positions = []
    velocities = []
    residuals = []
    predicted = []
    for z in measurements:
        s = step(x, v, z, tt, aa, bb)
        x = s["position"]
        v = s["velocity"]
        positions.append(x)
        velocities.append(v)
        residuals.append(s["residual"])
        predicted.append(s["predicted_position"])
    return {
        "positions": positions,
        "velocities": velocities,
        "residuals": residuals,
        "predicted_positions": predicted,
    }


def steady_state_gains(alpha):
    """Benedict-Bordner critical-damping gains from the smoothing factor.

    Returns a dict with 'alpha' (unchanged) and 'beta' =
    alpha^2 / (2 - alpha). Valid for alpha in (0, 2); raises
    ValueError otherwise.
    """
    aa = _scalar(alpha, "alpha")
    if not (0.0 < aa < 2.0):
        raise ValueError("smoothing factor alpha must be in (0, 2), got %g" % (aa,))
    return {"alpha": aa, "beta": aa * aa / (2.0 - aa)}


def gains_from_tracking_index(tracking_index):
    """Kalata critical-damping gains from the maneuverability index.

    lambda = sigma_w * dt^2 / sigma_v must be >= 0. Returns a dict
    with 'alpha' and 'beta' from the radical closed forms; lambda = 0
    gives gains (0, 0). Raises ValueError for lambda < 0.
    """
    lam = _scalar(tracking_index, "tracking_index")
    if lam < 0.0:
        raise ValueError("tracking index must be >= 0, got %g" % (lam,))
    if lam == 0.0:
        return {"alpha": 0.0, "beta": 0.0}
    s = math.sqrt(lam * lam + 8.0 * lam)
    alpha = -(lam * lam + 8.0 * lam - (lam + 4.0) * s) / 8.0
    beta = (lam * lam + 4.0 * lam - lam * s) / 4.0
    return {"alpha": alpha, "beta": beta}


def tracking_errors(true_positions, estimates):
    """Root-mean-square and maximum absolute tracking error.

    Compares the true position sequence against the estimated
    position sequence (same length, non-empty). Returns a dict with
    'rmse' and 'max_abs'. Raises ValueError on empty or mismatched
    lists.
    """
    if not true_positions or not estimates:
        raise ValueError("true_positions and estimates must be non-empty")
    if len(true_positions) != len(estimates):
        raise ValueError("true and estimated sequences must match in length")
    diffs = [_scalar(t, "true_positions[i]") - _scalar(e, "estimates[i]")
             for t, e in zip(true_positions, estimates)]
    n = len(diffs)
    rmse = math.sqrt(sum(d * d for d in diffs) / n)
    max_abs = max(abs(d) for d in diffs)
    return {"rmse": rmse, "max_abs": max_abs}


class TrackFilter:
    """Stateful alpha-beta tracking filter for a constant-velocity target.

    Holds position x, velocity v, the sample interval dt, and the
    gains alpha and beta. When beta is omitted it defaults to the
    Benedict-Bordner critical-damping value for the given alpha.
    """

    def __init__(self, x0=0.0, v0=0.0, dt=1.0, alpha=0.5, beta=None):
        self.x = _scalar(x0, "x0")
        self.v = _scalar(v0, "v0")
        self.dt = _scalar(dt, "dt")
        self.alpha = _scalar(alpha, "alpha")
        if beta is None:
            self.beta = steady_state_gains(self.alpha)["beta"]
        else:
            self.beta = _scalar(beta, "beta")
        # Validate the full gain pair up front.
        update(self.x, self.v, self.x, self.dt, self.alpha, self.beta)
        self.residual = 0.0

    def predict(self):
        """Advance the state to the next sample time; return (x_pred, v_pred)."""
        x_pred, v_pred = predict(self.x, self.v, self.dt)
        return x_pred, v_pred

    def update(self, z):
        """Correct the state from measurement z; returns the result dict."""
        x_pred, v_pred = predict(self.x, self.v, self.dt)
        upd = update(x_pred, v_pred, z, self.dt, self.alpha, self.beta)
        self.x = upd["position"]
        self.v = upd["velocity"]
        self.residual = upd["residual"]
        return upd

    def step(self, z):
        """One full predict + update cycle from measurement z."""
        return self.update(z)

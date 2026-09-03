"""Conjunction assessment screening logic (pure stdlib, deterministic).

Linear relative-motion model: given the relative position and constant
relative velocity of a secondary object with respect to a primary at a
screening epoch, compute the time of closest approach (TCA), the miss
distance, and the probability of collision (Pc) under a circular
combined-covariance approximation with a small hard-body model. All
units SI (m, m/s, s). ECSS space safety context is referenced, not
reproduced.
"""

import math

DEFAULT_HARD_BODY_RADIUS_M = 5.0
DEFAULT_SCREEN_THRESHOLD = 1e-4
MAX_VALID_HARD_BODY_RATIO = 0.1
HIGH_SEVERITY_THRESHOLD = 1e-3
WATCH_SEVERITY_THRESHOLD = 1e-4


def _dot(a, b):
    """Dot product of two equal-length vectors."""
    return sum(x * y for x, y in zip(a, b))


def tca_s(rel_pos_m, rel_vel_ms):
    """Time of closest approach in seconds.

    tca = -dot(r, v) / dot(v, v) for a constant relative velocity. A
    closing geometry (position opposed to velocity) gives a positive
    TCA; a receding geometry gives a negative TCA, meaning closest
    approach already passed. Raises ValueError on zero relative
    velocity, for which no closest approach is defined.
    """
    rel_vel_ms = [float(x) for x in rel_vel_ms]
    rel_pos_m = [float(x) for x in rel_pos_m]
    speed_sq = _dot(rel_vel_ms, rel_vel_ms)
    if speed_sq <= 0.0:
        raise ValueError("relative velocity must be non-zero")
    return -_dot(rel_pos_m, rel_vel_ms) / speed_sq


def miss_distance_m(rel_pos_m, rel_vel_ms, tca):
    """Miss distance in meters: |r + v * tca| at the TCA epoch."""
    rel_vel_ms = [float(x) for x in rel_vel_ms]
    rel_pos_m = [float(x) for x in rel_pos_m]
    at_tca = [rel_pos_m[i] + rel_vel_ms[i] * tca for i in range(3)]
    return math.sqrt(_dot(at_tca, at_tca))


def encounter_sigma(sigma_combined_m):
    """Encounter-plane 1-sigma position uncertainty in meters.

    The radial and cross-track sigma projected onto the encounter plane
    equal the combined 1-sigma value under the circular covariance
    approximation used by this screening model. A full 3x3 covariance
    projection onto the encounter plane is out of scope. Raises
    ValueError for non-positive sigma.
    """
    sigma_combined_m = float(sigma_combined_m)
    if sigma_combined_m <= 0.0:
        raise ValueError("combined sigma must be positive")
    return sigma_combined_m


def probability_of_collision(miss_m, sigma_m, hard_body_m):
    """Probability of collision from the small hard-body approximation.

    Pc = exp(-miss^2 / (2*sigma^2)) * (hard_body^2 / (2*sigma^2)),
    the leading term of the 2D Gaussian encounter integral valid when
    hard_body / sigma is at most about 0.1. Returns the float estimate;
    the caller checks the validity ratio for the approximation flag
    (see analyze). Raises ValueError for non-positive sigma, negative
    hard body radius, or negative miss distance.
    """
    miss_m = float(miss_m)
    sigma_m = float(sigma_m)
    hard_body_m = float(hard_body_m)
    if sigma_m <= 0.0:
        raise ValueError("sigma must be positive")
    if hard_body_m < 0.0:
        raise ValueError("hard body radius must be non-negative")
    if miss_m < 0.0:
        raise ValueError("miss distance must be non-negative")
    exponent = -miss_m * miss_m / (2.0 * sigma_m * sigma_m)
    return math.exp(exponent) * (hard_body_m * hard_body_m /
                                 (2.0 * sigma_m * sigma_m))


def screen_verdict(pc, threshold=DEFAULT_SCREEN_THRESHOLD):
    """Screen verdict for a probability of collision.

    Returns {"actionable": bool, "severity": str}: actionable when
    pc >= threshold; severity "high" when pc >= 1e-3, "watch" when
    pc >= 1e-4, else "green". Raises ValueError for a negative
    probability or a non-positive threshold.
    """
    pc = float(pc)
    threshold = float(threshold)
    if pc < 0.0:
        raise ValueError("probability of collision must be non-negative")
    if threshold <= 0.0:
        raise ValueError("screen threshold must be positive")
    if pc >= HIGH_SEVERITY_THRESHOLD:
        severity = "high"
    elif pc >= WATCH_SEVERITY_THRESHOLD:
        severity = "watch"
    else:
        severity = "green"
    return {"actionable": pc >= threshold, "severity": severity}


def analyze(rel_pos_m, rel_vel_ms, sigma_combined_m,
            hard_body_radius_m=DEFAULT_HARD_BODY_RADIUS_M,
            screen_threshold=DEFAULT_SCREEN_THRESHOLD):
    """Full conjunction screen for one close-approach epoch.

    Returns a dict with tca (s), miss_m, sigma_m, pc, actionable,
    severity and valid_approximation. valid_approximation is False when
    hard_body / sigma exceeds the small hard-body validity limit 0.1;
    the Pc value is then only a rough screen indicator.
    """
    tca = tca_s(rel_pos_m, rel_vel_ms)
    miss_m = miss_distance_m(rel_pos_m, rel_vel_ms, tca)
    sigma_m = encounter_sigma(sigma_combined_m)
    hard_body_radius_m = float(hard_body_radius_m)
    if hard_body_radius_m < 0.0:
        raise ValueError("hard body radius must be non-negative")
    pc = probability_of_collision(miss_m, sigma_m, hard_body_radius_m)
    verdict = screen_verdict(pc, screen_threshold)
    valid_approximation = (hard_body_radius_m / sigma_m <=
                           MAX_VALID_HARD_BODY_RATIO)
    return {
        "tca": tca,
        "miss_m": miss_m,
        "sigma_m": sigma_m,
        "pc": pc,
        "actionable": verdict["actionable"],
        "severity": verdict["severity"],
        "valid_approximation": valid_approximation,
    }

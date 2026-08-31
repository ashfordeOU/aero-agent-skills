#!/usr/bin/env python3
"""Orbital rendezvous phasing logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, ecss: free download):
ECSS-E-ST-10-03C covers rendezvous and docking. Phasing is the
classic orbit adjustment: a chaser behind the target speeds up by
lowering its orbit (smaller semi-major axis gives higher mean
motion), drifting through the phase angle, then returning to the
target altitude. Required drift rate is phase angle over transfer
time; the delta-v scales with the mean motion and the semi-major
axis change.
"""

import math

MU_EARTH = 3.986004418e14  # m^3/s^2


def drift_rate_required(phase_deg, transfer_time_s):
    """Drift rate (deg/s) needed to cover phase_deg in transfer_time."""
    if phase_deg < 0:
        raise ValueError("phase angle must be >= 0, got %r" % (phase_deg,))
    if transfer_time_s <= 0:
        raise ValueError("transfer time must be > 0, got %r" % (transfer_time_s,))
    return phase_deg / transfer_time_s


def delta_v_for_drift(r, phase_deg, transfer_time_s, mu=MU_EARTH):
    """Delta-v (m/s) magnitude for a phasing orbit at circular radius
    r (m) drifting phase_deg over transfer_time_s."""
    if r <= 0:
        raise ValueError("radius must be > 0, got %r" % (r,))
    if phase_deg < 0:
        raise ValueError("phase angle must be >= 0, got %r" % (phase_deg,))
    if transfer_time_s <= 0:
        raise ValueError("transfer time must be > 0, got %r" % (transfer_time_s,))
    if phase_deg == 0.0:
        return 0.0
    n = math.sqrt(mu / r ** 3)  # mean motion, rad/s
    drift = math.radians(phase_deg) / transfer_time_s  # rad/s
    da = (2.0 / 3.0) * r * drift / n  # semi-major axis change, m
    return 0.5 * n * da  # tangential burn delta-v, m/s


def closing_rate_ok(rate_mps, allowed_mps):
    """True when the closing rate is within the allowed rate."""
    if rate_mps < 0:
        raise ValueError("closing rate must be >= 0, got %r" % (rate_mps,))
    if allowed_mps <= 0:
        raise ValueError("allowed rate must be > 0, got %r" % (allowed_mps,))
    return rate_mps <= allowed_mps

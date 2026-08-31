#!/usr/bin/env python3
"""Envelope expansion logic for flight test planning (paraphrase, common
knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25.335 and CS-25.335 design airspeeds set the
maneuvering speed context, VA = VS * sqrt(n_max). Flight test practice
expands the speed envelope in equal steps, classifies airspeeds against
the VFE, VA, VNO, VNE categories, and checks the load factor against the
limit at every point. Speeds are in m/s; load factor is dimensionless.
"""

import math


def corner_speed(vs_ms, n_max):
    """Maneuvering speed VA = VS * sqrt(n_max), speeds in m/s.

    Raises ValueError when vs_ms <= 0 or n_max <= 1."""
    if vs_ms <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (vs_ms,))
    if n_max <= 1:
        raise ValueError("limit load factor must be > 1, got %r" % (n_max,))
    return vs_ms * math.sqrt(n_max)


def classify_airspeed(v_ms, vfe, va, vno, vne):
    """Classify a speed into one of the five flight test categories.

    Boundaries are half-open: v < vfe -> below-vfe; vfe <= v < va ->
    vfe-to-va; va <= v < vno -> va-to-vno; vno <= v < vne ->
    vno-to-vne; v >= vne -> at-or-above-vne.

    Raises ValueError when v_ms < 0 or the bound order
    0 < vfe < va < vno < vne is violated."""
    if v_ms < 0:
        raise ValueError("airspeed must be >= 0, got %r" % (v_ms,))
    if not (0 < vfe < va < vno < vne):
        raise ValueError(
            "bound order must be 0 < vfe < va < vno < vne, got %r"
            % ((vfe, va, vno, vne),)
        )
    if v_ms < vfe:
        return "below-vfe"
    if v_ms < va:
        return "vfe-to-va"
    if v_ms < vno:
        return "va-to-vno"
    if v_ms < vne:
        return "vno-to-vne"
    return "at-or-above-vne"


def expansion_step_size(target_v, current_v, n_steps):
    """Per-step speed increment from current_v toward target_v.

    Raises ValueError when n_steps <= 0 or target_v < current_v."""
    if n_steps <= 0:
        raise ValueError("step count must be > 0, got %r" % (n_steps,))
    if target_v < current_v:
        raise ValueError(
            "target must be >= current, got %r < %r" % (target_v, current_v)
        )
    return (target_v - current_v) / float(n_steps)


def load_factor_within_limit(n, n_max):
    """True when the applied load factor is within the limit.

    Raises ValueError when n < 0 or n_max <= 0."""
    if n < 0:
        raise ValueError("load factor must be >= 0, got %r" % (n,))
    if n_max <= 0:
        raise ValueError("limit load factor must be > 0, got %r" % (n_max,))
    return n <= n_max

#!/usr/bin/env python3
"""2-DOF modal analysis logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25: gated false,
reference-only): modal analysis of a structural system solves the
generalized eigenvalue problem (K - w^2 M) phi = 0 for the natural
frequencies w and the mode shapes phi of an undamped mass-spring
model. For a 2-DOF system with masses m1, m2 (kg) and springs k1, k2
(N/m) grounded at both ends, the stiffness matrix is
K = [[k1+k2, -k2], [-k2, k2]] and the mass matrix is
M = diag(m1, m2). This module returns the two natural frequencies in
rad/s (and in Hz), the mode-shape ratio phi2/phi1 per mode, and
checks an excitation frequency against the natural frequencies for
resonance risk.

Units: SI base units throughout. Masses in kg, spring rates in N/m,
natural and excitation frequencies in rad/s (Hz only where the
function name says so). One pressure/unit convention, no mixing.
"""

import math


def _validate(m1, m2, k1, k2):
    """Shared input validation; raises ValueError on invalid inputs."""
    if m1 <= 0 or m2 <= 0:
        raise ValueError(
            "masses must be positive (kg): got m1=%r, m2=%r" % (m1, m2)
        )
    if k1 < 0 or k2 < 0:
        raise ValueError(
            "spring rates must be non-negative (N/m): got k1=%r, k2=%r"
            % (k1, k2)
        )
    if k1 + k2 <= 0:
        raise ValueError(
            "at least one spring rate must be positive (N/m): got k1=%r, k2=%r"
            % (k1, k2)
        )


def natural_frequencies(m1, m2, k1, k2):
    """Natural frequencies (rad/s) of the grounded 2-DOF system, sorted ascending.

    Solves det(K - w^2 M) = 0. The characteristic polynomial
    (k1+k2 - m1 w^2)(k2 - m2 w^2) - k2^2 = 0 is a quadratic in
    x = w^2: m1 m2 x^2 - ((k1+k2) m2 + m1 k2) x + k1 k2 = 0.

    Inputs: m1, m2 in kg (positive); k1, k2 in N/m (non-negative, at
    least one positive). Invalid input raises ValueError. Returns
    [w1, w2] in rad/s with w1 <= w2.
    """
    _validate(m1, m2, k1, k2)
    a = m1 * m2
    b = -((k1 + k2) * m2 + m1 * k2)
    c = k1 * k2
    disc = b * b - 4.0 * a * c
    if disc < 0.0 and disc > -1e-9 * max(1.0, b * b):
        disc = 0.0  # clamp tiny negative from floating-point rounding
    if disc < 0.0:
        raise ValueError(
            "no real eigenvalues for m1=%r, m2=%r, k1=%r, k2=%r"
            % (m1, m2, k1, k2)
        )
    x1 = (-b - math.sqrt(disc)) / (2.0 * a)
    x2 = (-b + math.sqrt(disc)) / (2.0 * a)
    w1 = math.sqrt(max(0.0, x1))
    w2 = math.sqrt(max(0.0, x2))
    return [min(w1, w2), max(w1, w2)]


def frequencies_hz(m1, m2, k1, k2):
    """Natural frequencies in Hz: natural_frequencies() divided by 2*pi.

    Same input contract as natural_frequencies; invalid input raises
    ValueError.
    """
    return [w / (2.0 * math.pi) for w in natural_frequencies(m1, m2, k1, k2)]


def mode_shapes(m1, m2, k1, k2):
    """Mode-shape vectors, one per natural frequency, each [1.0, phi2/phi1].

    For each natural frequency w the singular system (K - w^2 M) phi = 0
    fixes the relative motion of the two masses; from row 1,
    phi2/phi1 = (k1+k2 - m1 w^2) / k2 when k2 > 0. Each shape is
    normalized so its first component is 1.0. Degenerate cases are
    handled: with k2 = 0 the rigid-body mode (w = 0) is returned as
    [0.0, 1.0] because the first mass is then stationary.

    Same input contract as natural_frequencies; invalid input raises
    ValueError.
    """
    wns = natural_frequencies(m1, m2, k1, k2)
    shapes = []
    for w in wns:
        w2 = w * w
        a11 = k1 + k2 - m1 * w2
        a12 = -k2
        a21 = -k2
        a22 = k2 - m2 * w2
        # Null vector of the singular 2x2 matrix A = K - w^2 M. Both
        # (a12, -a11) and (a22, -a21) satisfy A phi = 0; take the
        # better conditioned one so tiny floating-point entries do not
        # dominate (e.g. the decoupled k2 = 0 case).
        if a12 * a12 + a11 * a11 >= a22 * a22 + a21 * a21:
            p1, p2 = a12, -a11
        else:
            p1, p2 = a22, -a21
        if p1 != 0.0:
            shapes.append([1.0, p2 / p1])
        else:
            shapes.append([0.0, 1.0])
    return shapes


def resonance_check(w_excitation, wn_list, tol_frac=0.1):
    """Resonance check: is the excitation frequency near a natural one?

    Returns {"resonance": bool, "nearest": wn}. resonance is True when
    some natural frequency wn > 0 satisfies
    |wn - w_excitation| <= tol_frac * wn, a relative tolerance band
    around the natural frequency (default 10%). Rigid-body modes
    (wn = 0) do not resonate and are skipped. nearest is the natural
    frequency closest to the excitation frequency.

    w_excitation and every wn are in rad/s. tol_frac must lie in
    (0, 1). wn_list must be non-empty. Invalid input raises ValueError.
    """
    if w_excitation < 0.0:
        raise ValueError(
            "excitation frequency must be non-negative (rad/s): got %r"
            % (w_excitation,)
        )
    if not (0.0 < tol_frac < 1.0):
        raise ValueError(
            "tol_frac must be in (0, 1): got %r" % (tol_frac,)
        )
    if not wn_list:
        raise ValueError(
            "wn_list must be a non-empty list of natural frequencies (rad/s)"
        )
    resonance = False
    nearest = None
    best_dist = None
    for wn in wn_list:
        if wn < 0.0:
            raise ValueError(
                "natural frequencies must be non-negative (rad/s): got %r"
                % (wn,)
            )
        dist = abs(wn - w_excitation)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            nearest = wn
        if wn > 0.0 and dist <= tol_frac * wn:
            resonance = True
    return {"resonance": resonance, "nearest": nearest}

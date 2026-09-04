#!/usr/bin/env python3
"""Continuous Euler-Bernoulli beam natural frequencies (pure stdlib).

Common-knowledge summary (standards-map.yaml, far-25: gated false,
reference-only): the transverse free vibration of a uniform
Euler-Bernoulli beam obeys EI y'''' + m y_ddot = 0 with bending
stiffness EI (N m^2) and mass per unit length m (kg/m). Separation of
variables gives a spatial solution in terms of cos, sin, cosh and sinh
of beta x, where beta_n L is the n-th non-dimensional root of the
characteristic equation set by the end conditions:

- Pinned-pinned: beta_n L = n pi exactly (closed form), frequency
  f_n = n^2 pi^2 sqrt(EI / (m L^4)) / 2pi.
- Cantilever (fixed-free): cos x cosh x = -1, first roots
  1.87510407, 4.69409113, 7.85475744, ...
- Clamped-clamped and free-free: cos x cosh x = 1, first roots
  4.73004074, 7.85320462, 10.99560784, ...

Every case shares the frequency law f_n = (beta_n L)^2
sqrt(EI / (m L^4)) / 2pi in hertz. The free-free beam additionally
carries two zero-frequency rigid-body modes (translation, rotation);
this module reports only the elastic modes, whose first root
4.73004074 matches the clamped-clamped first root.

For non-uniform members the exact roots no longer apply; a Rayleigh
quotient with the trial shape phi gives an upper bound to the
fundamental. For a uniform cantilever with the parabolic shape
phi = (x/L)^2 the quotient omega^2 = 20 EI / (m L^4), about 1.272x
the exact fundamental (sqrt(20) / 3.51602).

Units are SI throughout: EI in N m^2, m in kg/m, L in m, frequencies
in Hz. One unit convention, no mixing.

Reference: R. Blevins, Formulas for Natural Frequency and Mode Shape
(characteristic roots); methodology summary only, no standard text
reproduced.
"""

import math

# Module constants (no magic numbers inline).
PI = math.pi
TWO_PI = 2.0 * math.pi
RAYLEIGH_CANTILEVER_COEFF = 20.0  # omega^2 coefficient for phi = (x/L)^2

# Boundary-condition names accepted by the module.
BC_PINNED_PINNED = "pinned-pinned"
BC_CANTILEVER = "cantilever"
BC_CLAMPED_CLAMPED = "clamped-clamped"
BC_FREE_FREE = "free-free"
_BC_NAMES = (BC_PINNED_PINNED, BC_CANTILEVER, BC_CLAMPED_CLAMPED,
             BC_FREE_FREE)

# Bisection brackets (documented, verified to straddle the published
# roots). Cantilever n = 1 root 1.87510407 sits in (1.8, 2.0); for
# n >= 2 the root of cos x cosh x = -1 lies in ((n-1) pi, n pi). The
# cos x cosh x = 1 roots for clamped-clamped and free-free sit within
# about 0.02 of (n + 0.5) pi (n = 1 gives 4.73004074, n = 2 gives
# 7.85320462), so a bracket of (n + 0.5) pi +/- 0.8 straddles exactly
# one root for every n >= 1 (adjacent roots are roughly pi apart).
CANTILEVER_FIRST_BRACKET = (1.8, 2.0)
CLAMPED_BRACKET_MARGIN = 0.8

# Published characteristic roots (Blevins), used by the contract test
# as reference values; the module re-derives them by bisection.
CANTILEVER_ROOTS = (1.87510407, 4.69409113, 7.85475744)
CLAMPED_FREE_FREE_ROOTS = (4.73004074, 7.85320462)

RAYLEIGH_SHAPE_CANTILEVER = "cantilever-parabola"  # phi = (x/L)^2
_RAYLEIGH_SHAPES = (RAYLEIGH_SHAPE_CANTILEVER,)


def _validate_beam(ei, mass_per_len, length_m):
    """Raise ValueError unless ei (N m^2), mass_per_len (kg/m) and
    length_m (m) are all strictly positive."""
    if ei <= 0:
        raise ValueError(
            "bending stiffness EI must be positive (N m^2): got %r" % (ei,))
    if mass_per_len <= 0:
        raise ValueError(
            "mass per unit length must be positive (kg/m): got %r"
            % (mass_per_len,))
    if length_m <= 0:
        raise ValueError(
            "beam length must be positive (m): got %r" % (length_m,))


def _validate_mode(mode_n):
    """Raise ValueError unless mode_n is a positive integer (1, 2, ...)."""
    if (isinstance(mode_n, bool) or not isinstance(mode_n, (int, float))
            or mode_n < 1 or mode_n != int(mode_n)):
        raise ValueError(
            "mode number must be a positive integer: got %r" % (mode_n,))


def _bisect(target, a, b, tol):
    """Bisection root of target(x) = 0 on the bracket [a, b], to width
    tol, returning the midpoint. Raises ValueError if the bracket does
    not straddle a sign change."""
    fa = target(a)
    fb = target(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise ValueError(
            "bracket (%r, %r) does not straddle a root of the "
            "characteristic equation" % (a, b))
    for _ in range(400):  # far more than needed for any physical mode
        mid = 0.5 * (a + b)
        if b - a <= tol:
            return mid
        fm = target(mid)
        if fm == 0.0:
            return mid
        if fa * fm < 0.0:
            b = mid
            fb = fm
        else:
            a = mid
            fa = fm
    return 0.5 * (a + b)


def beam_frequency(beta_n_L, ei, mass_per_len, length_m):
    """Natural frequency (Hz) from a characteristic root beta_n_L.

    f = (beta_n L)^2 sqrt(EI / (m L^4)) / 2pi. beta_n_L is the
    non-dimensional root for the mode; ei, mass_per_len and length_m
    are as documented in the module docstring. Non-positive inputs
    raise ValueError.
    """
    if beta_n_L <= 0:
        raise ValueError(
            "characteristic root beta_n*L must be positive: got %r"
            % (beta_n_L,))
    _validate_beam(ei, mass_per_len, length_m)
    rad_per_sq = math.sqrt(ei / (mass_per_len * length_m ** 4))
    return (beta_n_L ** 2) * rad_per_sq / TWO_PI


def characteristic_root(mode_n, bc, tol=1e-12):
    """n-th non-dimensional characteristic root beta_n L by bisection.

    bc selects the characteristic equation: "cantilever" solves
    cos x cosh x = -1 with root n in the documented bracket (1.8, 2.0)
    for n = 1 and ((n-1) pi, n pi) for n >= 2; "clamped-clamped" and
    "free-free" solve cos x cosh x = 1 with root n in
    (n + 0.5) pi +/- 0.8 (both share the same elastic roots; the
    pinned-pinned case is closed form, beta_n L = n pi, and is served
    by pinned_pinned_frequency without any root search). tol is the
    bisection width at which iteration stops. Returns beta_n L as a
    float. Non-positive or non-integer mode_n and unknown bc names
    raise ValueError.
    """
    _validate_mode(mode_n)
    if bc == BC_CANTILEVER:
        if mode_n == 1:
            lo, hi = CANTILEVER_FIRST_BRACKET
        else:
            lo = (mode_n - 1) * PI
            hi = mode_n * PI

        def target(x):
            return math.cos(x) * math.cosh(x) + 1.0

    elif bc in (BC_CLAMPED_CLAMPED, BC_FREE_FREE):
        center = (mode_n + 0.5) * PI
        lo = center - CLAMPED_BRACKET_MARGIN
        hi = center + CLAMPED_BRACKET_MARGIN

        def target(x):
            return math.cos(x) * math.cosh(x) - 1.0

    else:
        raise ValueError(
            "unknown boundary condition %r for characteristic_root; "
            "valid names: %s (pinned-pinned has the closed-form root "
            "n*pi, use pinned_pinned_frequency)" % (bc, BC_CANTILEVER
            + ", " + BC_CLAMPED_CLAMPED + ", " + BC_FREE_FREE))
    return _bisect(target, lo, hi, tol)


def pinned_pinned_frequency(mode_n, ei, mass_per_len, length_m):
    """n-th pinned-pinned (simply supported) natural frequency in Hz.

    Closed form f_n = n^2 pi^2 sqrt(EI / (m L^4)) / 2pi, i.e. the
    shared frequency law with the exact root beta_n L = n pi. Ratios
    are exact: f_n = n^2 f_1. Non-positive inputs or mode_n < 1 raise
    ValueError.
    """
    _validate_mode(mode_n)
    _validate_beam(ei, mass_per_len, length_m)
    return beam_frequency(mode_n * PI, ei, mass_per_len, length_m)


def cantilever_frequency(mode_n, ei, mass_per_len, length_m):
    """n-th cantilever (fixed-free) natural frequency in Hz.

    Solves cos x cosh x = -1 for beta_n L (roots 1.87510407,
    4.69409113, 7.85475744, ...) and applies the shared frequency
    law. Non-positive inputs or mode_n < 1 raise ValueError.
    """
    _validate_mode(mode_n)
    _validate_beam(ei, mass_per_len, length_m)
    beta_n_L = characteristic_root(mode_n, BC_CANTILEVER)
    return beam_frequency(beta_n_L, ei, mass_per_len, length_m)


def clamped_clamped_frequency(mode_n, ei, mass_per_len, length_m):
    """n-th clamped-clamped natural frequency in Hz.

    Solves cos x cosh x = 1 for beta_n L (roots 4.73004074,
    7.85320462, ...) and applies the shared frequency law. Non-positive
    inputs or mode_n < 1 raise ValueError.
    """
    _validate_mode(mode_n)
    _validate_beam(ei, mass_per_len, length_m)
    beta_n_L = characteristic_root(mode_n, BC_CLAMPED_CLAMPED)
    return beam_frequency(beta_n_L, ei, mass_per_len, length_m)


def free_free_frequency(mode_n, ei, mass_per_len, length_m):
    """n-th free-free elastic natural frequency in Hz.

    A free-free beam also has two zero-frequency rigid-body modes
    (translation and rotation); they are excluded here. The elastic
    modes solve cos x cosh x = 1 exactly like clamped-clamped, so the
    first elastic root is 4.73004074 and mode n of the free-free beam
    equals mode n of the clamped-clamped beam. Non-positive inputs or
    mode_n < 1 raise ValueError.
    """
    _validate_mode(mode_n)
    _validate_beam(ei, mass_per_len, length_m)
    beta_n_L = characteristic_root(mode_n, BC_FREE_FREE)
    return beam_frequency(beta_n_L, ei, mass_per_len, length_m)


def rayleigh_fundamental(ei, mass_per_len, length_m,
                         shape=RAYLEIGH_SHAPE_CANTILEVER):
    """Rayleigh-quotient fundamental frequency (Hz) of a non-uniform
    cantilever from the stored trial shape.

    The Rayleigh quotient omega^2 = int EI phi''^2 dx / int m phi^2 dx
    with the parabolic cantilever shape phi = (x/L)^2 gives, for a
    uniform member, omega^2 = 20 EI / (m L^4). The result is an upper
    bound to the exact fundamental: for the worked beam it is about
    1.272x the exact cantilever f1 (sqrt(20) / 3.51602). Only the
    shape "cantilever-parabola" is implemented. Non-positive inputs or
    an unknown shape raise ValueError.
    """
    _validate_beam(ei, mass_per_len, length_m)
    if shape != RAYLEIGH_SHAPE_CANTILEVER:
        raise ValueError(
            "unknown Rayleigh shape %r; implemented shapes: %s"
            % (shape, ", ".join(_RAYLEIGH_SHAPES)))
    omega_sq = RAYLEIGH_CANTILEVER_COEFF * ei / (
        mass_per_len * length_m ** 4)
    return math.sqrt(omega_sq) / TWO_PI


def beam_mode_frequencies(bc, n_modes, ei, mass_per_len, length_m):
    """List of the first n_modes natural frequencies (Hz), ascending,
    for the given boundary condition.

    bc is one of "pinned-pinned", "cantilever", "clamped-clamped" or
    "free-free" (free-free reports elastic modes only). n_modes must be
    a positive integer. Non-positive ei/mass_per_len/length_m, n_modes
    < 1 and unknown bc names raise ValueError.
    """
    _validate_mode(n_modes)
    _validate_beam(ei, mass_per_len, length_m)
    dispatch = {
        BC_PINNED_PINNED: pinned_pinned_frequency,
        BC_CANTILEVER: cantilever_frequency,
        BC_CLAMPED_CLAMPED: clamped_clamped_frequency,
        BC_FREE_FREE: free_free_frequency,
    }
    if bc not in dispatch:
        raise ValueError(
            "unknown boundary condition %r; valid names: %s"
            % (bc, ", ".join(_BC_NAMES)))
    return [dispatch[bc](n, ei, mass_per_len, length_m)
            for n in range(1, n_modes + 1)]

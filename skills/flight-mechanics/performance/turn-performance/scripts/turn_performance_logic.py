#!/usr/bin/env python3
"""Sustained turn performance logic (fixed-wing, common flight mechanics).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25/CS-25 maneuvering requirements are framed
around the load factor envelope and the speeds at which turns are
flown. The mathematics here is standard flight mechanics: a level
coordinated turn at bank angle phi requires a load factor
n = 1 / cos(phi); the resulting turn rate and turn radius follow from
n and the true airspeed V; a turn is sustained only when the available
thrust covers the drag of the turn.

All angles are in RADIANS. SI units throughout: speed V in m/s,
radius in m, turn rate in rad/s, forces in N, gravitational
acceleration g = 9.80665 m/s^2.
"""

import math

G = 9.80665  # standard gravity, m/s^2


def load_factor_from_bank(phi):
    """Load factor n = 1 / cos(phi) for a level turn, dimensionless.

    phi is the bank angle in RADIANS. Raises ValueError when the bank
    angle is at or beyond pi/2 rad (90 deg) in magnitude: no finite
    load factor exists there (cos(phi) reaches zero).
    """
    if abs(phi) >= math.pi / 2.0:
        raise ValueError(
            "bank angle must be below pi/2 rad (90 deg) in magnitude, got %r rad"
            % (phi,)
        )
    c = math.cos(phi)
    if math.isclose(c, 0.0, abs_tol=1e-12):
        raise ValueError(
            "bank angle must be below pi/2 rad (90 deg), cos(phi) = 0, got %r rad"
            % (phi,)
        )
    return 1.0 / c


def bank_from_load_factor(n):
    """Bank angle phi = acos(1 / n) in RADIANS for load factor n.

    Raises ValueError on n < 1: a load factor below 1 g has no
    corresponding level-turn bank angle.
    """
    if n < 1:
        raise ValueError("load factor must be >= 1, got %r" % (n,))
    return math.acos(1.0 / n)


def turn_rate(n, V):
    """Turn rate omega = g * sqrt(n^2 - 1) / V, in rad/s.

    n is the load factor, V the true airspeed in m/s, g = 9.80665
    m/s^2. Raises ValueError on n < 1 (no turning solution) or
    V <= 0.
    """
    if n < 1:
        raise ValueError("load factor must be >= 1, got %r" % (n,))
    if V <= 0:
        raise ValueError("speed must be > 0, got %r" % (V,))
    return G * math.sqrt(n * n - 1.0) / V


def turn_radius(n, V):
    """Turn radius R = V^2 / (g * sqrt(n^2 - 1)), in m.

    n is the load factor, V the true airspeed in m/s, g = 9.80665
    m/s^2. Raises ValueError on n < 1 (no turning solution) or
    V <= 0.
    """
    if n < 1:
        raise ValueError("load factor must be >= 1, got %r" % (n,))
    if V <= 0:
        raise ValueError("speed must be > 0, got %r" % (V,))
    return V * V / (G * math.sqrt(n * n - 1.0))


def sustained_check(T_available, D_level, n):
    """Whether the turn is sustained with the available thrust.

    The drag in the turn is D_turn = D_level * n (level-flight drag
    D_level in N scaled by the load factor n); the turn is
    'sustained' when T_available >= D_turn, else 'not sustained'.
    Returns {"d_turn": D_turn, "verdict": verdict}. Raises ValueError
    on D_level <= 0 or n < 1.
    """
    if D_level <= 0:
        raise ValueError("level-flight drag must be > 0, got %r" % (D_level,))
    if n < 1:
        raise ValueError("load factor must be >= 1, got %r" % (n,))
    d_turn = D_level * n
    verdict = "sustained" if T_available >= d_turn else "not sustained"
    return {"d_turn": d_turn, "verdict": verdict}

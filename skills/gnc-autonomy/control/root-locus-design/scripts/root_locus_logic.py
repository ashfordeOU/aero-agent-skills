#!/usr/bin/env python3
"""Classical root-locus design logic (paraphrase, common knowledge).

For the canonical type-1 plant G(s) = 1 / (s * (s + a)) with a
forward-path gain K, the closed-loop characteristic equation is
1 + K*G(s) = 0, i.e. s^2 + a*s + K = 0. The closed-loop poles are the
roots of this quadratic; their trajectory in the complex plane as K
varies is the root locus (standard control-theory textbook result,
paraphrase only; ARP4754A supplies the development-assurance context).

Units: a in rad/s (open-loop pole location), K dimensionless
(forward-path gain), zeta dimensionless (damping ratio), poles as
(re, im) pairs in rad/s.

Convention (documented in SKILL.md): a > 0 and K >= 0. Underdamped
(K > a^2/4) poles are -a/2 +/- j*wd with wd = sqrt(K - a^2/4) and
zeta = a / (2*sqrt(K)). Critically damped (K == a^2/4) gives zeta = 1.
Overdamped (K < a^2/4) reports zeta = 1.0 by convention. All functions
validate inputs and raise ValueError on impossible values.
"""

import math


def closed_loop_poles(a, K):
    """Closed-loop pole locations as (re, im) tuples in rad/s for gain K.

    Roots of s^2 + a*s + K = 0 via the quadratic formula. Returns a list
    of two (re, im) tuples; im is 0.0 for real roots.
    """
    if a <= 0:
        raise ValueError("a must be > 0, got %r" % (a,))
    if K < 0:
        raise ValueError("K must be >= 0, got %r" % (K,))
    disc = a * a - 4.0 * K
    if disc >= 0.0:
        r = math.sqrt(disc)
        return [((-a - r) / 2.0, 0.0), ((-a + r) / 2.0, 0.0)]
    wd = math.sqrt(-disc) / 2.0
    return [(-a / 2.0, wd), (-a / 2.0, -wd)]


def gain_for_damping(a, zeta):
    """Forward-path gain K placing the closed-loop poles at damping
    ratio zeta (0 < zeta <= 1). K = a^2 / (4 * zeta^2), dimensionless.
    """
    if a <= 0:
        raise ValueError("a must be > 0, got %r" % (a,))
    if zeta <= 0.0 or zeta > 1.0:
        raise ValueError("zeta must be in (0, 1], got %r" % (zeta,))
    return a * a / (4.0 * zeta * zeta)


def damping_ratio(a, K):
    """Damping ratio of the closed-loop poles for gain K, dimensionless.

    Underdamped (K > a^2/4): zeta = a / (2 * sqrt(K)). Critically
    damped (K == a^2/4): zeta = 1.0. Overdamped (K < a^2/4): reported
    as 1.0 by convention (two real poles).
    """
    if a <= 0:
        raise ValueError("a must be > 0, got %r" % (a,))
    if K < 0:
        raise ValueError("K must be >= 0, got %r" % (K,))
    crit = a * a / 4.0
    if K > crit:
        return a / (2.0 * math.sqrt(K))
    return 1.0


def stability_verdict(a, K):
    """Stability verdict from the closed-loop poles for gain K.

    Stable when every pole has real part < 0; a pole on the imaginary
    axis (K = 0 places one at the origin) is marginal, not stable.
    Returns {"stable": bool, "poles": [(re, im), ...]} with poles in
    rad/s.
    """
    poles = closed_loop_poles(a, K)
    stable = all(re < 0.0 for re, _ in poles)
    return {"stable": stable, "poles": poles}

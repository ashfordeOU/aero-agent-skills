#!/usr/bin/env python3
"""Composite laminate stiffness logic, classical lamination theory
(paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): composite aircraft structures follow classical
lamination theory for section stiffness. A ply has orthotropic
stiffness Q in material axes; rotation to the laminate axes gives
Q-bar; the symmetric laminate A-matrix sums Q-bar times ply
thickness. The coupling terms Q16/Q26 (and A16/A26) vanish for
balanced symmetric laminates.
"""

import math


def ply_stiffness(e1, e2, nu12, g12):
    """(Q11, Q12, Q22, Q66) in material axes."""
    if e1 <= 0 or e2 <= 0:
        raise ValueError("moduli must be > 0, got %r, %r" % (e1, e2))
    if not (0.0 <= nu12 < 1.0):
        raise ValueError("nu12 must be in [0, 1), got %r" % (nu12,))
    if g12 <= 0:
        raise ValueError("G12 must be > 0, got %r" % (g12,))
    nu21 = nu12 * e2 / e1
    denom = 1.0 - nu12 * nu21
    q11 = e1 / denom
    q22 = e2 / denom
    q12 = nu12 * e2 / denom
    return (q11, q12, q22, g12)


def rotated_ply_stiffness(e1, e2, nu12, g12, theta_deg):
    """(Q11b, Q12b, Q16b, Q22b, Q26b, Q66b) rotated to theta_deg."""
    q11, q12, q22, q66 = ply_stiffness(e1, e2, nu12, g12)
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2 = c * c
    s2 = s * s
    c4 = c2 * c2
    s4 = s2 * s2
    s2c2 = s2 * c2
    q11b = q11 * c4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * s4
    q22b = q11 * s4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * c4
    q12b = (q11 + q22 - 4.0 * q66) * s2c2 + q12 * (c4 + s4)
    q66b = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * s2c2 + q66 * (c4 + s4)
    q16b = ((q11 - q12 - 2.0 * q66) * c2
            - (q22 - q12 - 2.0 * q66) * s2) * c * s
    q26b = ((q11 - q12 - 2.0 * q66) * s2
            - (q22 - q12 - 2.0 * q66) * c2) * c * s
    return (q11b, q12b, q16b, q22b, q26b, q66b)


def laminate_a_matrix(plies, e1, e2, nu12, g12):
    """(A11, A12, A16, A22, A26, A66) for a symmetric laminate given
    as a list of (theta_deg, thickness_m) plies."""
    if not plies:
        raise ValueError("laminate must have at least one ply")
    a11 = a12 = a16 = a22 = a26 = a66 = 0.0
    for theta, t in plies:
        if t <= 0:
            raise ValueError("ply thickness must be > 0, got %r" % (t,))
        q = rotated_ply_stiffness(e1, e2, nu12, g12, theta)
        a11 += q[0] * t
        a12 += q[1] * t
        a16 += q[2] * t
        a22 += q[3] * t
        a26 += q[4] * t
        a66 += q[5] * t
    return (a11, a12, a16, a22, a26, a66)

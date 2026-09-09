#!/usr/bin/env python3
"""Laminate bending stiffness logic, classical lamination theory
(paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25 / cs-25: public
regulation and standards context): the bending-extension coupling
matrix B and the bending matrix D follow the same rotated ply
stiffness as the in-plane A matrix, integrated over the ply
z-coordinates with the z-squared and z-cubed thickness moments. A
mirror-symmetric stack drives B to zero to machine precision; an
unsymmetric stack couples bending and extension.
"""

import math


def _check_positive_number(value, label):
    """Raise ValueError unless value is a real positive int/float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("%s must be a positive number, got %s" % (label, value))


def _check_nu12(value):
    """Raise ValueError unless value is a real number in [0, 1)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0.0 <= value < 1.0):
        raise ValueError("poisson ratio nu12 must be in [0, 1), got %s" % (value,))


def ply_rotated_stiffness(e1, e2, nu12, g12, theta_deg):
    """(Qbar11, Qbar12, Qbar16, Qbar22, Qbar26, Qbar66) at theta_deg.

    The per-ply rotated stiffness is the integrand of the A, B and D
    z-moment integrals below; it is never a claimed output on its own.
    """
    _check_positive_number(e1, "modulus E1")
    _check_positive_number(e2, "modulus E2")
    _check_positive_number(g12, "modulus G12")
    _check_nu12(nu12)
    nu21 = nu12 * e2 / e1
    denom = 1.0 - nu12 * nu21
    q11 = e1 / denom
    q22 = e2 / denom
    q12 = nu12 * e2 / denom
    q66 = g12
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2 = c * c
    s2 = s * s
    c4 = c2 * c2
    s4 = s2 * s2
    s2c2 = s2 * c2
    qbar11 = q11 * c4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * s4
    qbar22 = q11 * s4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * c4
    qbar12 = (q11 + q22 - 4.0 * q66) * s2c2 + q12 * (c4 + s4)
    qbar66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * s2c2 + q66 * (c4 + s4)
    qbar16 = ((q11 - q12 - 2.0 * q66) * c2
              - (q22 - q12 - 2.0 * q66) * s2) * c * s
    qbar26 = ((q11 - q12 - 2.0 * q66) * s2
              - (q22 - q12 - 2.0 * q66) * c2) * c * s
    return (qbar11, qbar12, qbar16, qbar22, qbar26, qbar66)


def _ply_interfaces(plies):
    """Bottom-to-top interface z-coordinates and total thickness h.

    The mid-plane sits at z = 0; ply k occupies [z[k], z[k+1]].
    """
    if not plies:
        raise ValueError("laminate must have at least one ply")
    thicknesses = []
    for _theta, t in plies:
        _check_positive_number(t, "ply thickness")
        thicknesses.append(t)
    h = sum(thicknesses)
    z = [-h / 2.0]
    for t in thicknesses:
        z.append(z[-1] + t)
    return z, h


def _abd_moments(plies, e1, e2, nu12, g12):
    """(A, B, D, h): the six-component A/B/D tuples and total thickness.

    A_ij = sum_k Qbar_ij,k (z_k - z_k-1)
    B_ij = (1/2) sum_k Qbar_ij,k (z_k^2 - z_k-1^2)
    D_ij = (1/3) sum_k Qbar_ij,k (z_k^3 - z_k-1^3)
    in the (11, 12, 16, 22, 26, 66) index order.
    """
    z, h = _ply_interfaces(plies)
    a = [0.0] * 6
    b = [0.0] * 6
    d = [0.0] * 6
    for i, (theta, _t) in enumerate(plies):
        qbar = ply_rotated_stiffness(e1, e2, nu12, g12, theta)
        z0, z1 = z[i], z[i + 1]
        dz1 = z1 - z0
        dz2 = z1 * z1 - z0 * z0
        dz3 = z1 ** 3 - z0 ** 3
        for k in range(6):
            a[k] += qbar[k] * dz1
            b[k] += qbar[k] * dz2 * 0.5
            d[k] += qbar[k] * dz3 / 3.0
    return tuple(a), tuple(b), tuple(d), h


def b_coupling_matrix(plies, e1, e2, nu12, g12):
    """(B11, B12, B16, B22, B26, B66) N m, the bending-extension coupling."""
    _a, b, _d, _h = _abd_moments(plies, e1, e2, nu12, g12)
    return b


def d_bending_matrix(plies, e1, e2, nu12, g12):
    """(D11, D12, D16, D22, D26, D66) N m, the bending matrix."""
    _a, _b, d, _h = _abd_moments(plies, e1, e2, nu12, g12)
    return d


def abd_stiffness_matrices(plies, e1, e2, nu12, g12):
    """{"a": ..., "b": ..., "d": ...}: the full ABD assembly.

    The A block is returned only here, as part of the full assembly;
    this module has no standalone A-only function.
    """
    a, b, d, _h = _abd_moments(plies, e1, e2, nu12, g12)
    return {"a": a, "b": b, "d": d}


def laminate_bending_terms(plies, e1, e2, nu12, g12):
    """(D11, D22, D12, D66) N m in the order laminate-plate-buckling fixes."""
    _a, _b, d, _h = _abd_moments(plies, e1, e2, nu12, g12)
    d11, d12, _d16, d22, _d26, d66 = d
    return (d11, d22, d12, d66)


def equivalent_flexural_constants(d11, d22, d12, d66, t_total):
    """(E_bx, E_by, G_bxy, nu_bxy) of a symmetric stack with D16 = D26 = 0."""
    _check_positive_number(d11, "bending stiffness D11")
    _check_positive_number(d22, "bending stiffness D22")
    _check_positive_number(d66, "bending stiffness D66")
    _check_positive_number(t_total, "total thickness")
    det = d11 * d22 - d12 * d12
    if det <= 0:
        raise ValueError(
            "the bending stiffness terms are not positive definite, "
            "got D11 %s, D22 %s, D12 %s" % (d11, d22, d12))
    h3 = t_total ** 3
    e_bx = 12.0 * det / (d22 * h3)
    e_by = 12.0 * det / (d11 * h3)
    g_bxy = 12.0 * d66 / h3
    nu_bxy = d12 / d22
    return (e_bx, e_by, g_bxy, nu_bxy)


def laminate_bending_report(plies, e1, e2, nu12, g12):
    """One-shot dict: a, b, d, d11, d22, d12, d66, t_total, b_max_abs."""
    a, b, d, h = _abd_moments(plies, e1, e2, nu12, g12)
    d11, d12, _d16, d22, _d26, d66 = d
    b_max_abs = max(abs(x) for x in b)
    return {
        "a": a, "b": b, "d": d,
        "d11": d11, "d22": d22, "d12": d12, "d66": d66,
        "t_total": h, "b_max_abs": b_max_abs,
    }

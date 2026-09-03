"""Delamination growth assessment for composite laminates.

Fracture-mechanics delamination at the laminate level: mode I strain
energy release rate of a double cantilever beam (DCB) specimen, mode II
rate of an end-notched flexure (ENF) specimen, the mixed-mode ratio,
the Benzeggagh-Kenane (B-K) critical energy release rate, and the onset
and growth verdict for the delamination tolerance assessment.

Pure Python, stdlib only, deterministic. SI units throughout: load P in
N, lengths a (crack length), b (width), h (arm half-thickness) in m,
modulus E in Pa, energy release rates in J/m2. The beam-theory formulas
assume small deflections and an isotropic-equivalent laminate bending
stiffness; h is the half-thickness of one DCB arm or ENF half-beam, so
the specimen total thickness is 2h.

Non-physical inputs raise ValueError: negative loads, zero or negative
geometry or modulus, non-positive critical rates, and a non-positive
B-K exponent.
"""

__all__ = [
    "dcb_g1",
    "dcb_g1_compliance",
    "enf_g2",
    "mixed_mode_ratio",
    "bk_critical",
    "onset_margin",
    "assess",
]


def dcb_g1(P_N, a_m, b_m, h_m, E_pa):
    """Mode I strain energy release rate of a DCB specimen, J/m2.

    G_I = 12 * P^2 * a^2 / (E * b^2 * h^3) with h the half-thickness of
    one arm (specimen total thickness 2h).
    """
    if P_N < 0:
        raise ValueError("DCB load P must be non-negative")
    if a_m <= 0 or b_m <= 0 or h_m <= 0:
        raise ValueError("DCB crack length, width and half-thickness must be positive")
    if E_pa <= 0:
        raise ValueError("DCB modulus must be positive")
    return 12.0 * P_N * P_N * a_m * a_m / (E_pa * b_m * b_m * h_m ** 3)


def dcb_g1_compliance(P_N, delta_m, b_m, a_m):
    """Mode I rate of a DCB specimen from the load-line opening, J/m2.

    G_I = 3 * P * delta / (2 * b * a), where delta is the total opening
    of both arms at the load line. With the beam-theory opening
    delta = 2 * w and one-arm tip deflection w = P*a^3/(3*E*I),
    I = b*h^3/12, this form equals the load-squared form exactly.
    """
    if P_N < 0:
        raise ValueError("DCB load P must be non-negative")
    if delta_m <= 0 or b_m <= 0 or a_m <= 0:
        raise ValueError("DCB opening, width and crack length must be positive")
    return 3.0 * P_N * delta_m / (2.0 * b_m * a_m)


def enf_g2(P_N, a_m, b_m, h_m, E_pa):
    """Mode II strain energy release rate of an ENF specimen, J/m2.

    G_II = 9 * P^2 * a^2 / (16 * E * b^2 * h^3), h the half-thickness of
    one half-beam.
    """
    if P_N < 0:
        raise ValueError("ENF load P must be non-negative")
    if a_m <= 0 or b_m <= 0 or h_m <= 0:
        raise ValueError("ENF crack length, width and half-thickness must be positive")
    if E_pa <= 0:
        raise ValueError("ENF modulus must be positive")
    return 9.0 * P_N * P_N * a_m * a_m / (16.0 * E_pa * b_m * b_m * h_m ** 3)


def mixed_mode_ratio(g1, g2):
    """Mode II share of the total energy release rate.

    ratio = g2 / (g1 + g2) when g1 + g2 > 0, else 0.0 for the unloaded
    state where both rates vanish.
    """
    if g1 < 0 or g2 < 0:
        raise ValueError("energy release rates must be non-negative")
    total = g1 + g2
    if total <= 0:
        return 0.0
    return g2 / total


def bk_critical(g1, g2, g1c, g2c, eta):
    """Benzeggagh-Kenane critical total rate G_c, J/m2.

    G_T = g1 + g2, ratio = g2 / G_T, and
    G_c = g1c + (g2c - g1c) * ratio^eta.
    Pure mode I (ratio 0) gives g1c, pure mode II (ratio 1) gives g2c.
    """
    if g1 < 0 or g2 < 0:
        raise ValueError("energy release rates must be non-negative")
    if g1c <= 0 or g2c <= 0:
        raise ValueError("critical energy release rates must be positive")
    if eta <= 0:
        raise ValueError("B-K exponent must be positive")
    ratio = mixed_mode_ratio(g1, g2)
    return g1c + (g2c - g1c) * ratio ** eta


def onset_margin(g1, g2, g1c, g2c, eta):
    """Onset margin G_c - G_T, J/m2.

    A negative margin means the total applied rate exceeds the critical
    rate, so delamination onset and growth are predicted.
    """
    return bk_critical(g1, g2, g1c, g2c, eta) - (g1 + g2)


def assess(inputs):
    """Full delamination growth assessment from coupon geometry.

    inputs keys (SI): p_dcb, a_dcb, h_dcb for the DCB coupon load (N),
    crack length (m) and arm half-thickness (m); p_enf, a_enf, h_enf for
    the ENF coupon; b (m) width and e (Pa) flexural modulus shared by
    both coupons; g1c, g2c (J/m2) mode I and mode II critical rates and
    eta the B-K exponent. The DCB and ENF coupons are separate
    specimens, so their crack lengths and half-thicknesses are
    independent.

    Returns dict with g1, g2, g_t (J/m2), ratio, g_c (J/m2), margin
    (J/m2), growth bool (g_t >= g_c) and verdict
    "delamination-growth" or "no-delamination-growth".
    """
    g1 = dcb_g1(inputs["p_dcb"], inputs["a_dcb"], inputs["b"],
                inputs["h_dcb"], inputs["e"])
    g2 = enf_g2(inputs["p_enf"], inputs["a_enf"], inputs["b"],
                inputs["h_enf"], inputs["e"])
    g_t = g1 + g2
    ratio = mixed_mode_ratio(g1, g2)
    g_c = bk_critical(g1, g2, inputs["g1c"], inputs["g2c"], inputs["eta"])
    margin = g_c - g_t
    growth = g_t >= g_c
    return {
        "g1": g1,
        "g2": g2,
        "g_t": g_t,
        "ratio": ratio,
        "g_c": g_c,
        "margin": margin,
        "growth": growth,
        "verdict": "delamination-growth" if growth else "no-delamination-growth",
    }

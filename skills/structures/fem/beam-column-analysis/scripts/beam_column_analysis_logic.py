"""Combined axial compression and bending margin check for slender members.

Pure stdlib beam-column analysis (structures/fem/beam-column-analysis):
the Euler load P_E = pi^2 E I / (K L)^2, the moment amplification factor
delta = c_m / (1 - P/P_E) that grows the primary moment as the axial load
approaches the Euler load, the secant-formula peak compressive stress of an
eccentrically loaded column, and the axial-plus-bending interaction ratio
P/P_cr + M_applied / (M_capacity (1 - P/P_E)) with margin 1/ratio - 1 and the
pass verdict.

SI units throughout: E in Pa, I in m^4, A in m^2, L and eccentricity e in m,
forces in N, moments in N m, stresses in Pa. Deterministic closed form only,
no random state, no module constants beyond math.pi. Non-physical inputs
raise ValueError.
"""

import math

PI = math.pi


def euler_load(e_mod, i, l, k=1.0):
    """Compute the Euler load P_E = pi^2 E I / (K L)^2 of the member.

    The classic ideal-column critical load, same physics as the pure-axial
    Euler anchor; here it serves as the moment amplification denominator
    and the interaction-ratio reference of the combined-loading check.
    ValueError when e_mod, i, l or k is zero or negative.
    """
    if e_mod <= 0.0:
        raise ValueError("euler_load: Young modulus E must be positive (Pa)")
    if i <= 0.0:
        raise ValueError("euler_load: second moment of area I must be positive (m^4)")
    if l <= 0.0:
        raise ValueError("euler_load: member length L must be positive (m)")
    if k <= 0.0:
        raise ValueError("euler_load: effective length factor K must be positive")
    return PI ** 2 * e_mod * i / (k * l) ** 2


def moment_amplification(p, p_euler, c_m=1.0):
    """Return delta = c_m / (1 - P/P_E), the amplified primary moment factor.

    The standard second-order amplification 1/(1 - P/P_E) of the primary
    bending moment by the axial compression; c_m = 1.0 is the worst-case
    constant moment. The factor is 1.0 at zero axial load and grows without
    bound as P approaches P_E from below. ValueError when p < 0,
    p_euler <= 0, c_m <= 0 or p >= p_euler.
    """
    if p < 0.0:
        raise ValueError("moment_amplification: axial load P cannot be negative (N)")
    if p_euler <= 0.0:
        raise ValueError("moment_amplification: Euler load P_E must be positive (N)")
    if c_m <= 0.0:
        raise ValueError("moment_amplification: equivalent moment factor c_m must be positive")
    if p >= p_euler:
        raise ValueError("moment_amplification: axial load P at or above the Euler load P_E")
    return c_m / (1.0 - p / p_euler)


def secant_stress(p, area, ecc, c, r, l, e_mod, k=1.0):
    """Compute the secant-formula peak compressive stress of an eccentrically
    loaded column:

        sigma_max = (P/A) * (1 + (e c / r^2) / cos((K L / (2 r)) sqrt(P/(E A))))

    with e the load eccentricity, c the extreme-fiber distance and r the
    radius of gyration sqrt(I/A). The secant argument equals pi/2 exactly at
    P = P_E, so the stress diverges precisely where the member buckles; the
    argument guard rejects the pole with ValueError. At ecc = 0 the function
    returns P/A exactly, the pure axial stress consistency limit. ValueErrors
    when p <= 0, area <= 0, ecc < 0, c <= 0, r <= 0, l <= 0, e_mod <= 0,
    k <= 0, or when the secant argument reaches pi/2.
    """
    if p <= 0.0:
        raise ValueError("secant_stress: axial load P must be positive (N)")
    if area <= 0.0:
        raise ValueError("secant_stress: section area A must be positive (m^2)")
    if ecc < 0.0:
        raise ValueError("secant_stress: load eccentricity e cannot be negative (m)")
    if c <= 0.0:
        raise ValueError("secant_stress: extreme-fiber distance c must be positive (m)")
    if r <= 0.0:
        raise ValueError("secant_stress: radius of gyration r must be positive (m)")
    if l <= 0.0:
        raise ValueError("secant_stress: member length L must be positive (m)")
    if e_mod <= 0.0:
        raise ValueError("secant_stress: Young modulus E must be positive (Pa)")
    if k <= 0.0:
        raise ValueError("secant_stress: effective length factor K must be positive")
    arg = (k * l / (2.0 * r)) * math.sqrt(p / (e_mod * area))
    if arg >= PI / 2.0:
        raise ValueError(
            "secant_stress: axial load P at or above the Euler load P_E "
            "(secant argument at the pi/2 pole)"
        )
    axial = p / area
    return axial * (1.0 + (ecc * c / r ** 2) / math.cos(arg))


def interaction_check(p, p_cr, m_applied, m_capacity, p_euler):
    """Run the axial-plus-bending interaction check of the combined-loading
    margin:

        ratio = p / p_cr + m_applied / (m_capacity * (1.0 - p / p_euler))
        margin = 1.0 / ratio - 1.0
        pass = ratio <= 1.0   (inclusive)

    The first term is the axial utilization against the Euler-load reference
    P_cr, the second the amplified bending utilization against the section
    moment capacity, the amplification 1/(1 - P/P_E) carried inside. With
    m_applied = 0 the ratio degenerates to p / p_cr and the margin to
    p_cr / p - 1, the pure-axial margin-of-safety identity. Returns a dict
    with keys exactly ratio, margin, pass. ValueErrors when p < 0, p_cr <= 0,
    m_applied < 0, m_capacity <= 0, p_euler <= 0 or p >= p_euler.
    """
    if p < 0.0:
        raise ValueError("interaction_check: axial load P cannot be negative (N)")
    if p_cr <= 0.0:
        raise ValueError("interaction_check: critical (Euler) load P_cr must be positive (N)")
    if m_applied < 0.0:
        raise ValueError("interaction_check: applied moment M cannot be negative (N m)")
    if m_capacity <= 0.0:
        raise ValueError("interaction_check: section moment capacity M_cap must be positive (N m)")
    if p_euler <= 0.0:
        raise ValueError("interaction_check: Euler load P_E must be positive (N)")
    if p >= p_euler:
        raise ValueError("interaction_check: axial load P at or above the Euler load P_E")
    ratio = p / p_cr + m_applied / (m_capacity * (1.0 - p / p_euler))
    margin = 1.0 / ratio - 1.0
    return {"ratio": ratio, "margin": margin, "pass": ratio <= 1.0}

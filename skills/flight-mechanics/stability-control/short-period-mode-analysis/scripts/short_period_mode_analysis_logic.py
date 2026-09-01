#!/usr/bin/env python3
"""Short-period longitudinal mode analysis logic (common flight-mechanics
methodology, paraphrase).

Convention (stability axes): x forward, y out the right wing, z down.
Perturbation states are the angle of attack alpha and the pitch rate q.
The short-period approximation reduces the longitudinal motion to the
(alpha, q) pair; the slow phugoid (speed oscillation) is assumed well
separated in frequency so the two modes do not couple.

Dimensionless stability coefficients (per rad): C_Z_alpha, C_Z_q,
C_m_alpha, C_m_q, C_m_alphadot. They convert to dimensional
per-unit-mass derivatives with the dynamic pressure q_bar, the wing
area S, the mean chord c_bar, the mass m, the pitch inertia I_yy, the
speed V, and the aerodynamic timescale tau = c_bar / (2 * V):

  Z_alpha    =  q_bar * S * C_Z_alpha / m                [m/s^2 per rad]
  Z_q        =  q_bar * S * c_bar * C_Z_q / (2 * V * m)  [m/s per rad]
  M_alpha    =  q_bar * S * c_bar * C_m_alpha / I_yy     [1/s^2 per rad]
  M_q        =  q_bar * S * c_bar^2 * C_m_q / (2 * V * I_yy)  [1/s per rad]
  M_alphadot =  q_bar * S * c_bar^2 * C_m_alphadot / (2 * V * I_yy) [1/s]

The two-DOF pitch model with Z_q neglected (|Z_q| << V is validated by
z_q_negligible) has the state matrix

  A = [[Z_alpha / V, 1],
       [M_alpha + M_alphadot * Z_alpha / V, M_q + M_alphadot]]

with det(A) = M_q * Z_alpha / V - M_alpha (the M_alphadot terms cancel
in the determinant) and tr(A) = Z_alpha / V + M_q + M_alphadot, giving

  omega_nsp = sqrt(M_q * Z_alpha / V - M_alpha)          [rad/s]
  zeta_sp   = -(Z_alpha / V + M_q + M_alphadot) / (2 * omega_nsp)

For a pitch-stable, damped configuration M_alpha < 0, M_q < 0 and
Z_alpha < 0, so the radicand is positive. A non-positive radicand is
categorized as a non-oscillatory or divergent (unstable) mode.

Phugoid separation: the Lanchester phugoid frequency is
omega_np = sqrt(2) * g / V; the short-period approximation is valid
when omega_nsp / omega_np is large (default minimum ratio 5).

Level 1 flying qualities (MIL-F-8785C style summary, reference only,
not reproduced): damping ratio bands 0.35-1.30 (category A),
0.30-2.00 (category B), 0.25-2.00 (category C); minimum natural
frequency 0.28 rad/s (A and C) and 0.10 rad/s (B). Level 1 requires
both criteria; Level 2 is a damped oscillation outside the Level 1
band; undamped, divergent, or non-oscillatory modes are Level 3.

All functions raise ValueError on physically invalid inputs.
"""

import math

G = 9.80665  # standard gravity, m/s^2

# Level 1 flying qualities bands (summary, MIL-F-8785C style):
# (min zeta, max zeta, min omega_n rad/s) per flight phase category.
LEVEL1_BANDS = {
    "A": (0.35, 1.30, 0.28),
    "B": (0.30, 2.00, 0.10),
    "C": (0.25, 2.00, 0.28),
}


def _require_positive(name, value):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def dimensionless_derivative_conversion(
    q_bar, s, c_bar, v, mass, i_yy,
    c_z_alpha, c_z_q, c_m_alpha, c_m_q, c_m_alphadot,
):
    """Convert dimensionless stability coefficients to dimensional
    per-unit-mass derivatives.

    Returns a dict with the aerodynamic timescale tau = c_bar / (2 * V)
    and the derivatives z_alpha, z_q, m_alpha, m_q, m_alphadot.
    C_Z_alpha must be negative (positive lift slope in stability
    axes), C_m_alpha negative (pitch-stable), and C_m_q negative
    (pitch damping); C_Z_q and C_m_alphadot are usually negative but
    carry no sign requirement here.
    """
    _require_positive("dynamic pressure", q_bar)
    _require_positive("wing reference area", s)
    _require_positive("mean chord", c_bar)
    _require_positive("speed", v)
    _require_positive("mass", mass)
    _require_positive("pitch inertia", i_yy)
    if c_z_alpha >= 0:
        raise ValueError(
            "lift coefficient slope must be negative (stability axes), got %r"
            % (c_z_alpha,)
        )
    if c_m_alpha >= 0:
        raise ValueError(
            "pitch stiffness coefficient must be negative (pitch-stable), got %r"
            % (c_m_alpha,)
        )
    if c_m_q >= 0:
        raise ValueError(
            "pitch damping coefficient must be negative, got %r" % (c_m_q,)
        )
    tau = c_bar / (2.0 * v)
    return {
        "timescale": tau,
        "z_alpha": q_bar * s * c_z_alpha / mass,
        "z_q": q_bar * s * c_bar * c_z_q / (2.0 * v * mass),
        "m_alpha": q_bar * s * c_bar * c_m_alpha / i_yy,
        "m_q": q_bar * s * c_bar * c_bar * c_m_q / (2.0 * v * i_yy),
        "m_alphadot": q_bar * s * c_bar * c_bar * c_m_alphadot
        / (2.0 * v * i_yy),
    }


def short_period_frequency(z_alpha, m_alpha, m_q, v):
    """Short-period natural frequency omega_nsp = sqrt(M_q * Z_alpha / V -
    M_alpha), in rad/s.

    Raises ValueError when the radicand is non-positive (non-oscillatory
    or divergent mode) or the speed is non-positive.
    """
    _require_positive("speed", v)
    radicand = m_q * z_alpha / v - m_alpha
    if radicand <= 0:
        raise ValueError(
            "short period radicand must be positive (non-oscillatory or "
            "divergent mode), got %r" % (radicand,)
        )
    return math.sqrt(radicand)


def short_period_damping(z_alpha, m_alpha, m_q, m_alphadot, v):
    """Short-period damping ratio zeta_sp = -(Z_alpha / V + M_q +
    M_alphadot) / (2 * omega_nsp), dimensionless.

    Reuses short_period_frequency for validation. The result may be
    zero (undamped oscillation) or negative (divergent oscillation);
    those cases are categorized by short_period_analysis and
    level1_quality_check, not rejected here.
    """
    omega = short_period_frequency(z_alpha, m_alpha, m_q, v)
    return -(z_alpha / v + m_q + m_alphadot) / (2.0 * omega)


def level1_quality_check(zeta, omega_n, category="A"):
    """Level 1 flying qualities verdict from damping ratio and natural
    frequency.

    Returns (level, reasons) with level in 1, 2, 3. Level 1 needs the
    damping ratio inside the category band and the natural frequency at
    or above the category floor; Level 2 is any damped oscillation
    outside the Level 1 band; Level 3 covers undamped (zeta <= 0) and
    divergent modes. Boundaries are inclusive. omega_n must be > 0 and
    the category one of A, B, C.
    """
    if category not in LEVEL1_BANDS:
        raise ValueError(
            "category must be one of A, B, C: %r" % (category,)
        )
    if omega_n <= 0:
        raise ValueError("natural frequency must be > 0, got %r" % (omega_n,))
    zeta_min, zeta_max, omega_min = LEVEL1_BANDS[category]
    reasons = []
    in_band = zeta_min <= zeta <= zeta_max
    meets_frequency = omega_n >= omega_min
    reasons.append(
        "damping ratio %.4f %s [%.2f, %.2f]"
        % (zeta, "within" if in_band else "outside", zeta_min, zeta_max)
    )
    reasons.append(
        "natural frequency %.4f rad/s %s %.2f rad/s floor"
        % (omega_n, "meets" if meets_frequency else "below", omega_min)
    )
    if in_band and meets_frequency:
        return 1, reasons
    if zeta > 0:
        return 2, reasons
    reasons.append("damping ratio <= 0: undamped or divergent")
    return 3, reasons


def short_period_analysis(z_alpha, m_alpha, m_q, m_alphadot, v,
                          category="A"):
    """Complete short-period mode analysis.

    Returns a dict with stable, oscillatory, omega_n, zeta, level, and
    level_reasons. A non-positive radicand (non-oscillatory or
    divergent mode) yields stable False, oscillatory False, omega_n and
    zeta None, and level 3; a stable oscillatory mode carries the
    natural frequency, damping ratio, and the Level 1/2/3 verdict.
    """
    _require_positive("speed", v)
    if category not in LEVEL1_BANDS:
        raise ValueError(
            "category must be one of A, B, C: %r" % (category,)
        )
    radicand = m_q * z_alpha / v - m_alpha
    if radicand <= 0:
        return {
            "stable": False,
            "oscillatory": False,
            "omega_n": None,
            "zeta": None,
            "level": 3,
            "level_reasons": [
                "non-oscillatory or divergent mode: radicand %.4f <= 0"
                % (radicand,)
            ],
        }
    omega = math.sqrt(radicand)
    zeta = -(z_alpha / v + m_q + m_alphadot) / (2.0 * omega)
    level, reasons = level1_quality_check(zeta, omega, category)
    return {
        "stable": zeta > 0,
        "oscillatory": True,
        "omega_n": omega,
        "zeta": zeta,
        "level": level,
        "level_reasons": reasons,
    }


def phugoid_separation(omega_nsp, v, g=G, min_ratio=5.0):
    """Phugoid separation check for the short-period approximation.

    Lanchester phugoid frequency omega_np = sqrt(2) * g / V. Returns
    (ratio, separated) where separated is True when
    omega_nsp / omega_np >= min_ratio.
    """
    _require_positive("short period frequency", omega_nsp)
    _require_positive("speed", v)
    _require_positive("gravity", g)
    _require_positive("minimum ratio", min_ratio)
    omega_np = math.sqrt(2.0) * g / v
    ratio = omega_nsp / omega_np
    return ratio, ratio >= min_ratio


def z_q_negligible(z_q, v, tol=0.05):
    """Z_q negligibility check: True when |Z_q| / V < tol.

    The short-period state matrix drops the 1 + Z_q / V term; the
    approximation holds when that term is near unity.
    """
    _require_positive("speed", v)
    _require_positive("tolerance", tol)
    return abs(z_q) / v < tol

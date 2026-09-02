#!/usr/bin/env python3
"""Dynamic stability logic (common flight-mechanics methodology, paraphrase).

Documented convention (stability axes): x forward, y out the right
wing, z down. Perturbation states: angle of attack alpha, pitch rate
q. All stability derivatives are per unit mass: M_alpha and M_q use
the pitch inertia I_yy, Z_alpha uses the mass m. The pitch stiffness
M_alpha, the pitch damping M_q, and the vertical force derivative
Z_alpha are negative for a pitch-stable, damped configuration.

- Short period: the reduced-order (alpha, q) state matrix
  A = [[Z_alpha/V, 1], [M_alpha, M_q]] has
  det(A) = M_q * Z_alpha / V - M_alpha = omega_ns^2 and
  tr(A) = Z_alpha / V + M_q = -2 * zeta_s * omega_ns.

- Phugoid (Lanchester): omega_np = sqrt(2) * g / V, period
  T_p = sqrt(2) * pi * V / g, damping zeta_p = 1 / (sqrt(2) * (L/D)).

- Lateral modes: a complex pair is oscillatory (damped Dutch roll
  when the real part is negative, divergent oscillation when it is
  positive); real negative roots are convergent non-oscillatory modes
  (roll subsidence, stable spiral); a real positive root is a
  divergent spiral. For a complex pair lambda = re + im * j:
  omega_n = |lambda| and zeta = -re / |lambda|. A divergent real root
  doubles amplitude in ln(2) / lambda; a convergent real root halves
  it in ln(2) / |lambda|.

- Criteria: FAR-25.181 requires short period oscillations heavily
  damped and phugoid oscillations not growing in amplitude. Common
  level 1 handling-quality criteria (MIL-F-8785C style, summary only):
  short period zeta in [0.3, 2.0]; Dutch roll zeta >= 0.08 and
  zeta * omega_n >= 0.15; roll subsidence time constant <= 1.0 s;
  divergent spiral time to double >= 20 s; phugoid zeta > 0.

All functions raise ValueError on physically invalid inputs.
"""

import math


def z_alpha(q_bar, s, c_l_alpha, mass):
    """Vertical force derivative Z_alpha = -(q_bar * S * C_Lalpha) / m, in
    m/s^2 per rad. q_bar in Pa, S in m^2, C_Lalpha in 1/rad, mass in kg.
    """
    if q_bar <= 0:
        raise ValueError("dynamic pressure must be > 0, got %r" % (q_bar,))
    if s <= 0:
        raise ValueError("wing reference area must be > 0, got %r" % (s,))
    if c_l_alpha <= 0:
        raise ValueError("lift slope must be > 0, got %r" % (c_l_alpha,))
    if mass <= 0:
        raise ValueError("mass must be > 0, got %r" % (mass,))
    return -(q_bar * s * c_l_alpha) / mass


def m_alpha(q_bar, s, c_bar, c_m_alpha, i_yy):
    """Pitch stiffness derivative M_alpha = (q_bar * S * c_bar * C_malpha) /
    I_yy, in 1/s^2 per rad. C_malpha must be negative (pitch-stable).
    """
    if q_bar <= 0:
        raise ValueError("dynamic pressure must be > 0, got %r" % (q_bar,))
    if s <= 0:
        raise ValueError("wing reference area must be > 0, got %r" % (s,))
    if c_bar <= 0:
        raise ValueError("mean chord must be > 0, got %r" % (c_bar,))
    if c_m_alpha >= 0:
        raise ValueError("pitch stiffness coefficient must be negative, got %r" % (c_m_alpha,))
    if i_yy <= 0:
        raise ValueError("pitch inertia must be > 0, got %r" % (i_yy,))
    return (q_bar * s * c_bar * c_m_alpha) / i_yy


def m_q(q_bar, s, c_bar, c_m_q, v, i_yy):
    """Pitch damping derivative M_q = (q_bar * S * c_bar**2 * C_mq) /
    (2 * V * I_yy), in 1/s. C_mq must be negative (damping).
    """
    if q_bar <= 0:
        raise ValueError("dynamic pressure must be > 0, got %r" % (q_bar,))
    if s <= 0:
        raise ValueError("wing reference area must be > 0, got %r" % (s,))
    if c_bar <= 0:
        raise ValueError("mean chord must be > 0, got %r" % (c_bar,))
    if c_m_q >= 0:
        raise ValueError("pitch damping coefficient must be negative, got %r" % (c_m_q,))
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    if i_yy <= 0:
        raise ValueError("pitch inertia must be > 0, got %r" % (i_yy,))
    return (q_bar * s * c_bar * c_bar * c_m_q) / (2.0 * v * i_yy)


def short_period_frequency(z_alpha, m_alpha, m_q, v):
    """Short period natural frequency omega_ns = sqrt(M_q * Z_alpha / V -
    M_alpha), in rad/s.

    Requires V > 0 and a positive radicand (pitch-stable, damped
    configuration).
    """
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    radicand = m_q * z_alpha / v - m_alpha
    if radicand <= 0:
        raise ValueError(
            "short period radicand must be positive, got %r" % (radicand,)
        )
    return math.sqrt(radicand)


def short_period_damping(z_alpha, m_alpha, m_q, v):
    """Short period damping ratio zeta_s = -(Z_alpha / V + M_q) /
    (2 * omega_ns).

    Reuses short_period_frequency for validation and the natural
    frequency.
    """
    omega = short_period_frequency(z_alpha, m_alpha, m_q, v)
    return -(z_alpha / v + m_q) / (2.0 * omega)


def phugoid_frequency(v, g):
    """Phugoid natural frequency omega_np = sqrt(2) * g / V, in rad/s."""
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    if g <= 0:
        raise ValueError("gravity must be > 0, got %r" % (g,))
    return math.sqrt(2.0) * g / v


def phugoid_period(v, g):
    """Phugoid period T_p = 2 * pi / omega_np = sqrt(2) * pi * V / g, in s."""
    return 2.0 * math.pi / phugoid_frequency(v, g)


def phugoid_damping(l_over_d):
    """Phugoid damping ratio zeta_p = 1 / (sqrt(2) * (L/D)).

    The lift-to-drag ratio must be positive; a large L/D gives a
    lightly damped phugoid.
    """
    if l_over_d <= 0:
        raise ValueError("lift-to-drag ratio must be > 0, got %r" % (l_over_d,))
    return 1.0 / (math.sqrt(2.0) * l_over_d)


def damping_ratio(re, im):
    """Damping ratio of a complex eigenvalue pair lambda = re + im * j:
    zeta = -re / |lambda|.

    Requires a non-zero imaginary part (oscillatory mode). Positive
    zeta means a damped oscillation.
    """
    if im == 0.0:
        raise ValueError("damping ratio needs a complex pair, got im = 0")
    return -re / math.sqrt(re * re + im * im)


def classify_mode(re, im):
    """Classify a mode from one eigenvalue.

    Returns (kind, verdict): ("oscillatory"|"non-oscillatory",
    "stable"|"divergent"|"neutral").
    """
    if im != 0.0:
        verdict = "stable" if re < 0.0 else "divergent" if re > 0.0 else "neutral"
        return ("oscillatory", verdict)
    verdict = "stable" if re < 0.0 else "divergent" if re > 0.0 else "neutral"
    return ("non-oscillatory", verdict)


def time_to_double(lam):
    """Time to double amplitude T2 = ln(2) / lambda for a divergent real
    root lambda > 0, in s.
    """
    if lam <= 0:
        raise ValueError("time to double needs a positive root, got %r" % (lam,))
    return math.log(2.0) / lam


def time_to_half(lam):
    """Time to half amplitude T_half = ln(2) / |lambda| for a convergent
    real root lambda < 0, in s.
    """
    if lam >= 0:
        raise ValueError("time to half needs a negative root, got %r" % (lam,))
    return math.log(2.0) / (-lam)


def short_period_damping_adequate(zeta):
    """True when the short period damping ratio is in [0.3, 2.0]
    (level 1 handling-quality band).
    """
    return 0.3 <= zeta <= 2.0


def dutch_roll_adequate(zeta, omega_n):
    """True when the Dutch roll meets the level 1 criterion: zeta >= 0.08
    and zeta * omega_n >= 0.15 (omega_n in rad/s).
    """
    if omega_n <= 0:
        raise ValueError("natural frequency must be > 0, got %r" % (omega_n,))
    return zeta >= 0.08 and zeta * omega_n >= 0.15


def roll_mode_acceptable(tau):
    """True when the roll subsidence time constant tau <= 1.0 s
    (level 1 criterion). tau must be positive.
    """
    if tau <= 0:
        raise ValueError("roll mode time constant must be > 0, got %r" % (tau,))
    return tau <= 1.0


def spiral_acceptable(lam):
    """True when the spiral mode is acceptable: a stable (non-positive)
    root always passes; a divergent root passes only when the time to
    double is at least 20 s.
    """
    if lam <= 0.0:
        return True
    return time_to_double(lam) >= 20.0


def phugoid_acceptable(zeta):
    """True when the phugoid damping ratio is positive (non-divergent)."""
    return zeta > 0.0

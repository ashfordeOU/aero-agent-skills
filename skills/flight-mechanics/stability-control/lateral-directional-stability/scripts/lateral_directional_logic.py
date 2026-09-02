#!/usr/bin/env python3
"""Lateral-directional stability logic (common flight-mechanics
methodology, paraphrase).

Documented convention (stability axes): x forward, y out the right
wing, z down. Sideslip angle beta is positive when the relative wind
comes from the left, so the velocity vector points to the right of the
plane of symmetry. The yawing moment coefficient C_n is positive when
the nose turns toward the relative wind; the rolling moment
coefficient C_l is positive when the right wing rolls down.

- Directional (yaw) stability: a positive sideslip must produce a
  restoring yawing moment, so the total derivative C_n_beta > 0. The
  vertical tail contributes C_n_beta_vt = eta_vt * V_v * a_vt *
  (1 + k_s), where V_v = (S_vt * l_vt) / (S * b) is the vertical tail
  volume coefficient, eta_vt the fin efficiency (sidewash and dynamic
  pressure ratio), a_vt the fin lift slope (1/rad), and k_s the
  sidewash gradient. Texts that define beta with the opposite sign
  write this term with a leading minus; the magnitude is unchanged.

- Lateral (roll) stability: a positive sideslip must produce a
  restoring rolling moment, so the total derivative C_l_beta < 0. The
  first-order dihedral contribution is C_l_beta_gamma = -C_L * gamma,
  with C_L the wing lift coefficient and gamma the dihedral angle in
  radians; the windward panel gains lift and the leeward panel loses
  it for positive dihedral.

- Roll mode: the simplified roll equation p_dot = L_p * p gives the
  roll subsidence time constant tau = -1 / L_p, with the roll damping
  derivative L_p = (q_bar * S * b**2 * C_lp) / (2 * V * I_xx) built
  from the roll damping coefficient C_lp (negative).

- Dutch roll: the simplified yaw-sideslip model (states beta and yaw
  rate r) gives the natural frequency
  omega_n = sqrt(N_beta + (N_r * Y_beta - N_beta * Y_r) / V) and the
  damping ratio zeta = -(Y_beta / V + N_r) / (2 * omega_n), with the
  yaw stiffness N_beta in 1/s^2, the rate derivatives N_r and Y_r in
  1/s, the side force derivative Y_beta in m/s^2, and V in m/s.

- Spiral mode: the slow lateral root approximates
  lambda_s = (g / V) * (L_beta * N_r - L_r * N_beta) / (N_beta * L_p);
  with N_beta > 0 and L_p < 0 the spiral mode is convergent (stable)
  when L_beta * N_r - L_r * N_beta > 0.

All functions raise ValueError on physically invalid inputs.
"""

import math


def vertical_tail_volume(s_vt, l_vt, s, b):
    """Vertical tail volume coefficient V_v = (S_vt * l_vt) / (S * b).

    All inputs are positive; the result is dimensionless.
    """
    if s_vt <= 0:
        raise ValueError("vertical tail area must be > 0, got %r" % (s_vt,))
    if l_vt <= 0:
        raise ValueError("vertical tail arm must be > 0, got %r" % (l_vt,))
    if s <= 0:
        raise ValueError("wing reference area must be > 0, got %r" % (s,))
    if b <= 0:
        raise ValueError("wing span must be > 0, got %r" % (b,))
    return (s_vt * l_vt) / (s * b)


def cn_beta_vertical_tail(eta_vt, v_v, a_vt, sidewash_gradient=0.0):
    """Fin contribution to the directional stability derivative.

    C_n_beta_vt = eta_vt * V_v * a_vt * (1 + sidewash_gradient).

    eta_vt in (0, 1], V_v > 0, a_vt > 0, sidewash_gradient >= 0.
    """
    if not (0.0 < eta_vt <= 1.0):
        raise ValueError("fin efficiency must be in (0, 1], got %r" % (eta_vt,))
    if v_v <= 0:
        raise ValueError("vertical tail volume coefficient must be > 0, got %r" % (v_v,))
    if a_vt <= 0:
        raise ValueError("fin lift slope must be > 0, got %r" % (a_vt,))
    if sidewash_gradient < 0:
        raise ValueError("sidewash gradient must be >= 0, got %r" % (sidewash_gradient,))
    return eta_vt * v_v * a_vt * (1.0 + sidewash_gradient)


def cn_beta_total(cn_beta_vt, cn_beta_fuselage=0.0):
    """Total directional stability derivative: fin plus fuselage.

    The fuselage contribution is usually negative (destabilizing).
    """
    return cn_beta_vt + cn_beta_fuselage


def directionally_stable(cn_beta):
    """True when C_n_beta > 0 (restoring yaw moment for positive sideslip)."""
    return cn_beta > 0.0


def cl_beta_dihedral(c_l, dihedral_deg):
    """Dihedral contribution to the roll stability derivative.

    C_l_beta_gamma = -C_L * gamma, gamma the dihedral angle converted
    from degrees to radians. The lift coefficient must be >= 0; the
    dihedral angle may be negative (anhedral), which destabilizes.
    """
    if c_l < 0:
        raise ValueError("lift coefficient must be >= 0, got %r" % (c_l,))
    return -c_l * math.radians(dihedral_deg)


def laterally_stable(cl_beta):
    """True when C_l_beta < 0 (restoring roll moment for positive sideslip)."""
    return cl_beta < 0.0


def roll_damping_derivative(c_lp, q_bar, s, b, v, i_xx):
    """Roll damping derivative L_p = (q_bar * S * b**2 * C_lp) / (2 * V * I_xx).

    C_lp must be negative (damping); all other inputs positive. Units:
    q_bar in Pa, S in m^2, b in m, V in m/s, I_xx in kg m^2, L_p in 1/s.
    """
    if c_lp >= 0:
        raise ValueError("roll damping coefficient must be negative, got %r" % (c_lp,))
    if q_bar <= 0:
        raise ValueError("dynamic pressure must be > 0, got %r" % (q_bar,))
    if s <= 0:
        raise ValueError("wing reference area must be > 0, got %r" % (s,))
    if b <= 0:
        raise ValueError("wing span must be > 0, got %r" % (b,))
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    if i_xx <= 0:
        raise ValueError("roll inertia must be > 0, got %r" % (i_xx,))
    return (q_bar * s * b * b * c_lp) / (2.0 * v * i_xx)


def roll_mode_time_constant(l_p):
    """Roll subsidence time constant tau = -1 / L_p.

    L_p must be negative (damped roll); the time constant is positive.
    """
    if l_p >= 0:
        raise ValueError("roll damping derivative must be negative, got %r" % (l_p,))
    return -1.0 / l_p


def dutch_roll_frequency(n_beta, n_r, y_beta, y_r, v):
    """Dutch roll natural frequency from the simplified yaw-sideslip model.

    omega_n = sqrt(N_beta + (N_r * Y_beta - N_beta * Y_r) / V).

    The radicand must be positive; V must be positive.
    """
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    radicand = n_beta + (n_r * y_beta - n_beta * y_r) / v
    if radicand <= 0:
        raise ValueError(
            "Dutch roll radicand must be positive, got %r" % (radicand,)
        )
    return math.sqrt(radicand)


def dutch_roll_damping_ratio(n_beta, n_r, y_beta, y_r, v):
    """Dutch roll damping ratio zeta = -(Y_beta / V + N_r) / (2 * omega_n).

    Reuses dutch_roll_frequency for validation and the natural frequency.
    """
    omega = dutch_roll_frequency(n_beta, n_r, y_beta, y_r, v)
    return -(y_beta / v + n_r) / (2.0 * omega)


def spiral_stability_parameter(l_beta, l_r, n_beta, n_r):
    """Spiral criterion term L_beta * N_r - L_r * N_beta.

    With N_beta > 0 and L_p < 0, a positive value means a convergent
    (stable) spiral mode.
    """
    return l_beta * n_r - l_r * n_beta


def spiral_mode_stable(l_beta, l_r, n_beta, n_r):
    """True when the spiral mode is convergent (criterion term > 0)."""
    return spiral_stability_parameter(l_beta, l_r, n_beta, n_r) > 0.0


def spiral_eigenvalue(l_beta, l_r, n_beta, n_r, l_p, g, v):
    """Approximate spiral root lambda_s = (g/V) * (L_beta*N_r - L_r*N_beta) /
    (N_beta * L_p), in 1/s.

    Requires N_beta > 0 (yaw stiffness), L_p < 0 (roll damping),
    g > 0, V > 0. Negative root means a convergent spiral mode.
    """
    if n_beta <= 0:
        raise ValueError("yaw stiffness must be > 0, got %r" % (n_beta,))
    if l_p >= 0:
        raise ValueError("roll damping derivative must be negative, got %r" % (l_p,))
    if g <= 0:
        raise ValueError("gravity must be > 0, got %r" % (g,))
    if v <= 0:
        raise ValueError("speed must be > 0, got %r" % (v,))
    return (g / v) * spiral_stability_parameter(
        l_beta, l_r, n_beta, n_r
    ) / (n_beta * l_p)

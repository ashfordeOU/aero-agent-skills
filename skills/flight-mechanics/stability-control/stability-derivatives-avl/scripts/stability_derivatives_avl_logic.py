#!/usr/bin/env python3
"""Aerodynamic stability derivative estimation from geometry (AVL-style,
common flight-mechanics methodology, paraphrase).

Summary (standards-map.yaml, far-25/cs-25: reference-only regulation
context): transport aeroplanes must show positive static longitudinal
stability and adequate directional stability, which the design
achieves through the wing, the horizontal tail, and the vertical tail
geometry. This module estimates the non-dimensional stability
derivatives from that geometry, in the style of vortex-lattice and
DATCOM-type preliminary methods:

- Wing and tail lift curve slopes CL_alpha per radian from planform
  aspect ratio, quarter-chord sweep, and Mach number (subsonic
  DATCOM-type compressibility correction, valid for M < 0.9).
- Cm_alpha from the wing aerodynamic center, the center of gravity,
  the horizontal tail volume coefficient, the tail lift slope, and the
  downwash gradient.
- The neutral point and the static margin from the longitudinal
  estimates.
- Lateral-directional derivatives: Cn_beta (vertical tail plus
  wing-body sweep contribution), Cl_beta (dihedral contribution),
  Cl_p, Cl_r, Cn_p, and Cn_r (simplified estimates for preliminary
  design).

All angles in radians, all lengths in meters (SI), all areas in square
meters; every returned derivative is per radian unless stated
otherwise. The results are preliminary-design estimates; final designs
are validated with higher-fidelity tools.
"""

import math

TWO_PI = 2.0 * math.pi


def _check_planform(aspect_ratio, sweep_quarter_chord_deg, mach,
                    cl_alpha_airfoil):
    if aspect_ratio <= 0:
        raise ValueError(
            "aspect ratio must be > 0, got %r" % (aspect_ratio,)
        )
    if not (-89.9 < sweep_quarter_chord_deg < 89.9):
        raise ValueError(
            "quarter-chord sweep must be in (-89.9, 89.9) deg, got %r"
            % (sweep_quarter_chord_deg,)
        )
    if not (0.0 <= mach < 0.9):
        raise ValueError(
            "Mach number must be in [0, 0.9), got %r" % (mach,)
        )
    if cl_alpha_airfoil <= 0:
        raise ValueError(
            "section lift slope must be > 0, got %r" % (cl_alpha_airfoil,)
        )


def cl_alpha_wing(aspect_ratio, sweep_quarter_chord_deg, mach,
                  cl_alpha_airfoil=None):
    """Wing lift curve slope CL_alpha per radian (subsonic estimate).

    DATCOM-type planform formula with the compressibility factor
    beta = sqrt(1 - M^2) and the section-slope ratio k = a0 / (2*pi):

      CL_alpha = 2*pi*A / ( 2 + sqrt( (A*beta/k)^2 * (1 + tan^2(Lambda)/
                 beta^2) + 4 ) )

    where A is the aspect ratio, Lambda the quarter-chord sweep, and
    a0 the section (airfoil) lift slope, 2*pi per radian by default.

    Raises ValueError for an invalid aspect ratio, sweep, Mach, or
    section slope. Valid for subsonic flight, M < 0.9.
    """
    if cl_alpha_airfoil is None:
        cl_alpha_airfoil = TWO_PI
    _check_planform(aspect_ratio, sweep_quarter_chord_deg, mach,
                    cl_alpha_airfoil)
    beta = math.sqrt(1.0 - mach * mach)
    k = cl_alpha_airfoil / TWO_PI
    tan_lambda = math.tan(math.radians(sweep_quarter_chord_deg))
    term = (aspect_ratio * beta / k) ** 2 * (
        1.0 + tan_lambda * tan_lambda / (beta * beta)
    )
    return TWO_PI * aspect_ratio / (2.0 + math.sqrt(term + 4.0))


def cl_alpha_tail(aspect_ratio, sweep_quarter_chord_deg, mach,
                  cl_alpha_airfoil=None):
    """Tail (horizontal or vertical surface) lift curve slope per radian.

    The same planform estimate as cl_alpha_wing; the tail surface is a
    finite lifting surface with its own aspect ratio and sweep. Raises
    ValueError for invalid inputs.
    """
    return cl_alpha_wing(aspect_ratio, sweep_quarter_chord_deg, mach,
                         cl_alpha_airfoil)


def downwash_gradient(cl_alpha_wing_val, aspect_ratio):
    """Downwash gradient depsilon/dalpha at the tail (dimensionless).

    Elliptical-loading estimate: depsilon/dalpha = 2*CL_alpha_w/(pi*A).
    A value at or above 1.0 is physically invalid for this model and
    raises ValueError.
    """
    if cl_alpha_wing_val <= 0:
        raise ValueError(
            "wing lift slope must be > 0, got %r" % (cl_alpha_wing_val,)
        )
    if aspect_ratio <= 0:
        raise ValueError(
            "aspect ratio must be > 0, got %r" % (aspect_ratio,)
        )
    val = 2.0 * cl_alpha_wing_val / (math.pi * aspect_ratio)
    if val >= 1.0:
        raise ValueError(
            "downwash gradient %.4f is not in [0, 1)" % (val,)
        )
    return val


def tail_volume_coeff(l_t, s_t, c_bar, s_w):
    """Horizontal tail volume coefficient V_h = l_t*S_t/(c_bar*S_w).

    l_t tail arm (m), S_t tail area (m^2), c_bar mean aerodynamic
    chord (m), S_w wing area (m^2). Dimensionless.
    """
    if l_t <= 0 or s_t <= 0 or c_bar <= 0 or s_w <= 0:
        raise ValueError(
            "tail arm, tail area, mean chord, and wing area must all "
            "be > 0, got %r %r %r %r" % (l_t, s_t, c_bar, s_w)
        )
    return l_t * s_t / (c_bar * s_w)


def vertical_tail_volume_coeff(l_v, s_v, b, s_w):
    """Vertical tail volume coefficient V_v = l_v*S_v/(b*S_w).

    l_v vertical tail arm (m), S_v vertical tail area (m^2), b wing
    span (m), S_w wing area (m^2). Dimensionless.
    """
    if l_v <= 0 or s_v <= 0 or b <= 0 or s_w <= 0:
        raise ValueError(
            "vertical tail arm, vertical tail area, span, and wing "
            "area must all be > 0, got %r %r %r %r" % (l_v, s_v, b, s_w)
        )
    return l_v * s_v / (b * s_w)


def cm_alpha(cl_alpha_wing_val, h_cg, h_ac_w, tail_volume_coeff_val,
             cl_alpha_tail_val, downwash_gradient_val):
    """Pitch stiffness Cm_alpha per radian at the center of gravity.

      Cm_alpha = a_w*(h_cg - h_ac_w) - V_h*a_t*(1 - depsilon/dalpha)

    with a_w and a_t the wing and tail lift slopes, h_cg and h_ac_w the
    center of gravity and wing aerodynamic center as fractions of the
    mean aerodynamic chord, V_h the tail volume coefficient, and
    depsilon/dalpha the downwash gradient. Negative Cm_alpha means a
    pitch-stable configuration.
    """
    if not (0.0 < h_cg < 1.0):
        raise ValueError(
            "center of gravity must be in (0, 1), got %r" % (h_cg,)
        )
    if not (0.0 < h_ac_w < 1.0):
        raise ValueError(
            "wing aerodynamic center must be in (0, 1), got %r" % (h_ac_w,)
        )
    if tail_volume_coeff_val <= 0:
        raise ValueError(
            "tail volume coefficient must be > 0, got %r"
            % (tail_volume_coeff_val,)
        )
    if cl_alpha_tail_val <= 0:
        raise ValueError(
            "tail lift slope must be > 0, got %r" % (cl_alpha_tail_val,)
        )
    if not (0.0 <= downwash_gradient_val < 1.0):
        raise ValueError(
            "downwash gradient must be in [0, 1), got %r"
            % (downwash_gradient_val,)
        )
    wing_term = cl_alpha_wing_val * (h_cg - h_ac_w)
    tail_term = tail_volume_coeff_val * cl_alpha_tail_val * (
        1.0 - downwash_gradient_val
    )
    return wing_term - tail_term


def neutral_point(cl_alpha_wing_val, cl_alpha_tail_val,
                  tail_volume_coeff_val, downwash_gradient_val, h_ac_w):
    """Neutral point as a fraction of mean aerodynamic chord.

      h_np = h_ac_w + V_h*(a_t/a_w)*(1 - depsilon/dalpha)

    The neutral point is the aerodynamic center of the whole aircraft
    (wing plus tail). Raises ValueError for invalid inputs.
    """
    if cl_alpha_wing_val <= 0:
        raise ValueError(
            "wing lift slope must be > 0, got %r" % (cl_alpha_wing_val,)
        )
    if cl_alpha_tail_val <= 0:
        raise ValueError(
            "tail lift slope must be > 0, got %r" % (cl_alpha_tail_val,)
        )
    if tail_volume_coeff_val <= 0:
        raise ValueError(
            "tail volume coefficient must be > 0, got %r"
            % (tail_volume_coeff_val,)
        )
    if not (0.0 <= downwash_gradient_val < 1.0):
        raise ValueError(
            "downwash gradient must be in [0, 1), got %r"
            % (downwash_gradient_val,)
        )
    if not (0.0 < h_ac_w < 1.0):
        raise ValueError(
            "wing aerodynamic center must be in (0, 1), got %r" % (h_ac_w,)
        )
    return h_ac_w + tail_volume_coeff_val * (
        cl_alpha_tail_val / cl_alpha_wing_val
    ) * (1.0 - downwash_gradient_val)


def static_margin(neutral_point_val, h_cg):
    """Static margin: neutral point minus center of gravity position.

    Positive margin means a longitudinally stable configuration.
    Raises ValueError when either position is outside (0, 1).
    """
    if not (0.0 < neutral_point_val < 1.0):
        raise ValueError(
            "neutral point must be in (0, 1), got %r" % (neutral_point_val,)
        )
    if not (0.0 < h_cg < 1.0):
        raise ValueError(
            "center of gravity must be in (0, 1), got %r" % (h_cg,)
        )
    return neutral_point_val - h_cg


def cn_beta_wing_body(c_l, aspect_ratio, sweep_quarter_chord_deg):
    """Wing-body contribution to directional stability Cn_beta per radian.

    Simple-sweep estimate: Cn_beta_wb = -(C_L^2/(pi*A))*tan(Lambda).
    Swept-back wings give a small negative (destabilizing) contribution
    that the vertical tail must overcome. Zero for an unswept wing at
    zero lift.
    """
    if c_l < 0:
        raise ValueError(
            "lift coefficient must be >= 0, got %r" % (c_l,)
        )
    if aspect_ratio <= 0:
        raise ValueError(
            "aspect ratio must be > 0, got %r" % (aspect_ratio,)
        )
    if not (-89.9 < sweep_quarter_chord_deg < 89.9):
        raise ValueError(
            "quarter-chord sweep must be in (-89.9, 89.9) deg, got %r"
            % (sweep_quarter_chord_deg,)
        )
    return -(c_l * c_l / (math.pi * aspect_ratio)) * math.tan(
        math.radians(sweep_quarter_chord_deg)
    )


def cn_beta_vertical_tail(vertical_tail_volume_coeff_val,
                          cl_alpha_tail_val, sidewash_factor=0.72):
    """Vertical tail contribution to directional stability per radian.

      Cn_beta_vt = V_v*a_t*(1 + sigma)

    with V_v the vertical tail volume coefficient, a_t the tail lift
    slope, and sigma the sidewash factor (default 0.72, the common
    preliminary-design value; a value of -1 means the tail contributes
    nothing). Positive (weathercock) stabilizing contribution.
    """
    if vertical_tail_volume_coeff_val <= 0:
        raise ValueError(
            "vertical tail volume coefficient must be > 0, got %r"
            % (vertical_tail_volume_coeff_val,)
        )
    if cl_alpha_tail_val <= 0:
        raise ValueError(
            "tail lift slope must be > 0, got %r" % (cl_alpha_tail_val,)
        )
    if sidewash_factor <= -1.0:
        raise ValueError(
            "sidewash factor must be > -1, got %r" % (sidewash_factor,)
        )
    return vertical_tail_volume_coeff_val * cl_alpha_tail_val * (
        1.0 + sidewash_factor
    )


def cn_beta(c_l, aspect_ratio, sweep_quarter_chord_deg,
            vertical_tail_volume_coeff_val, cl_alpha_tail_val,
            sidewash_factor=0.72):
    """Total directional stability Cn_beta per radian.

    Sum of the vertical tail contribution (stabilizing, positive) and
    the wing-body sweep contribution (destabilizing, negative). A
    positive total means weathercock stability.
    """
    return cn_beta_vertical_tail(
        vertical_tail_volume_coeff_val, cl_alpha_tail_val, sidewash_factor
    ) + cn_beta_wing_body(c_l, aspect_ratio, sweep_quarter_chord_deg)


def cl_beta(cl_alpha_wing_val, dihedral_deg):
    """Dihedral contribution to roll stability Cl_beta per radian.

      Cl_beta = -(a_w/2)*Gamma

    with Gamma the wing dihedral angle in radians. Negative means a
    stabilizing rolling moment in sideslip.
    """
    if cl_alpha_wing_val <= 0:
        raise ValueError(
            "wing lift slope must be > 0, got %r" % (cl_alpha_wing_val,)
        )
    if not (-45.0 < dihedral_deg < 45.0):
        raise ValueError(
            "dihedral must be in (-45, 45) deg, got %r" % (dihedral_deg,)
        )
    return -(cl_alpha_wing_val / 2.0) * math.radians(dihedral_deg)


def _check_taper(taper_ratio):
    if not (0.0 < taper_ratio <= 1.0):
        raise ValueError(
            "taper ratio must be in (0, 1], got %r" % (taper_ratio,)
        )


def cl_p(aspect_ratio, taper_ratio, cl_alpha_wing_val):
    """Roll damping Cl_p per radian of pb/2V (dimensionless rate).

      Cl_p = -(a_w/12)*(1 + 3*lambda)/(1 + lambda)

    with lambda the taper ratio. Always negative (damping).
    """
    _check_taper(taper_ratio)
    if cl_alpha_wing_val <= 0:
        raise ValueError(
            "wing lift slope must be > 0, got %r" % (cl_alpha_wing_val,)
        )
    if aspect_ratio <= 0:
        raise ValueError(
            "aspect ratio must be > 0, got %r" % (aspect_ratio,)
        )
    return -(cl_alpha_wing_val / 12.0) * (
        1.0 + 3.0 * taper_ratio
    ) / (1.0 + taper_ratio)


def cl_r(c_l, taper_ratio):
    """Rolling moment due to yaw rate Cl_r per radian (wing estimate).

      Cl_r = (C_L/4)*(1 + 3*lambda)/(1 + lambda)

    Simplified wing contribution for preliminary design; the vertical
    tail adds a smaller correction.
    """
    _check_taper(taper_ratio)
    if c_l < 0:
        raise ValueError(
            "lift coefficient must be >= 0, got %r" % (c_l,)
        )
    return (c_l / 4.0) * (1.0 + 3.0 * taper_ratio) / (1.0 + taper_ratio)


def cn_p(c_l):
    """Yawing moment due to roll rate Cn_p per radian (wing estimate).

      Cn_p = -C_L/8

    Elliptical-wing estimate for preliminary design.
    """
    if c_l < 0:
        raise ValueError(
            "lift coefficient must be >= 0, got %r" % (c_l,)
        )
    return -c_l / 8.0


def cn_r(vertical_tail_volume_coeff_val, cl_alpha_tail_val, l_v, b):
    """Yaw damping Cn_r per radian (vertical tail estimate).

      Cn_r = -2*V_v*a_t*(l_v/b)

    with l_v the vertical tail arm (m) and b the wing span (m). Always
    negative (damping).
    """
    if vertical_tail_volume_coeff_val <= 0:
        raise ValueError(
            "vertical tail volume coefficient must be > 0, got %r"
            % (vertical_tail_volume_coeff_val,)
        )
    if cl_alpha_tail_val <= 0:
        raise ValueError(
            "tail lift slope must be > 0, got %r" % (cl_alpha_tail_val,)
        )
    if l_v <= 0 or b <= 0:
        raise ValueError(
            "tail arm and span must be > 0, got %r %r" % (l_v, b)
        )
    return -2.0 * vertical_tail_volume_coeff_val * cl_alpha_tail_val * (
        l_v / b
    )


def estimate_derivative_table(
    *,
    aspect_ratio,
    sweep_quarter_chord_deg,
    mach,
    taper_ratio,
    cl_alpha_airfoil=None,
    h_cg,
    h_ac_w,
    l_t,
    s_t,
    c_bar,
    s_w,
    l_v,
    s_v,
    b,
    dihedral_deg,
    c_l,
    sidewash_factor=0.72,
    min_margin=0.05,
):
    """Assemble the full non-dimensional derivative table.

    Takes the wing planform (aspect ratio, quarter-chord sweep, Mach,
    taper ratio, section slope), the center of gravity and wing
    aerodynamic center, the horizontal tail (arm, area, mean chord),
    the vertical tail (arm, area), the span, the wing area, the
    dihedral, and the cruise lift coefficient. Returns a dict with the
    longitudinal derivatives, the neutral point, the static margin,
    the lateral-directional derivatives, and the stability verdicts.
    """
    a_w = cl_alpha_wing(aspect_ratio, sweep_quarter_chord_deg, mach,
                        cl_alpha_airfoil)
    a_t = cl_alpha_tail(aspect_ratio, sweep_quarter_chord_deg, mach,
                        cl_alpha_airfoil)
    deda = downwash_gradient(a_w, aspect_ratio)
    v_h = tail_volume_coeff(l_t, s_t, c_bar, s_w)
    v_v = vertical_tail_volume_coeff(l_v, s_v, b, s_w)
    cm_a = cm_alpha(a_w, h_cg, h_ac_w, v_h, a_t, deda)
    h_np = neutral_point(a_w, a_t, v_h, deda, h_ac_w)
    sm = static_margin(h_np, h_cg)
    cnb = cn_beta(c_l, aspect_ratio, sweep_quarter_chord_deg, v_v, a_t,
                  sidewash_factor)
    return {
        "cl_alpha_wing": a_w,
        "cl_alpha_tail": a_t,
        "downwash_gradient": deda,
        "tail_volume_coeff": v_h,
        "vertical_tail_volume_coeff": v_v,
        "cm_alpha": cm_a,
        "neutral_point": h_np,
        "static_margin": sm,
        "cn_beta": cnb,
        "cl_beta": cl_beta(a_w, dihedral_deg),
        "cl_p": cl_p(aspect_ratio, taper_ratio, a_w),
        "cl_r": cl_r(c_l, taper_ratio),
        "cn_p": cn_p(c_l),
        "cn_r": cn_r(v_v, a_t, l_v, b),
        "pitch_stable": cm_a < 0.0,
        "directionally_stable": cnb > 0.0,
        "statically_stable": sm >= min_margin,
    }


if __name__ == "__main__":
    cfg = dict(
        aspect_ratio=6.0,
        sweep_quarter_chord_deg=25.0,
        mach=0.4,
        taper_ratio=0.4,
        h_cg=0.3,
        h_ac_w=0.25,
        l_t=3.0,
        s_t=2.0,
        c_bar=0.5,
        s_w=20.0,
        l_v=4.0,
        s_v=1.5,
        b=12.0,
        dihedral_deg=5.0,
        c_l=0.5,
    )
    for k, v in estimate_derivative_table(**cfg).items():
        if isinstance(v, float):
            print("%-24s %.6f" % (k, v))
        else:
            print("%-24s %s" % (k, v))

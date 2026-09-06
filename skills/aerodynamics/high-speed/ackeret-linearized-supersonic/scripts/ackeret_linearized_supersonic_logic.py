"""Ackeret linearized supersonic thin-airfoil theory (aerodynamics/high-speed).

Linearized (Ackeret) supersonic thin-airfoil section coefficients,
Liepmann and Roshko ch. 10 / Anderson sec. 9 style. Pure stdlib math,
deterministic, no RNG.

Conventions (pinned in the leaf spec):
- All angles are in RADIANS. Positive alpha: freestream inclined up
  relative to the chord, lower surface windward, cl positive.
- Ackeret parameter beta = sqrt(M^2 - 1), the divisor of every linear
  supersonic coefficient; the coefficients diverge as M -> 1, so every
  mach-bearing function raises ValueError at mach <= 1.0.
- Linearized surface pressure law: on a surface deflected by theta from
  the freestream (positive theta compresses, sign positive windward),
  Cp = +-2*theta/beta. Upper surface cp_u = 2*(phi_u - alpha)/beta and
  lower surface cp_l = 2*(alpha - phi_l)/beta with phi = dy/dx the
  surface slope relative to the chord.
- Section lift: cl = (1/c) int_0^c (cp_l - cp_u) dx = 4*alpha/beta for
  every thin CLOSED section (thickness and camber terms integrate out).
- Leading-edge moment (nose-up positive): cm_le = -(1/c^2) int_0^c x
  (cp_l - cp_u) dx = -2*alpha/beta - (2/(beta c^2)) int (y_u + y_l) dx.
- Wave drag by the linearized pressure resolution, drag direction at
  +alpha to the chord: cd = alpha*cl + (2/(beta c)) int_0^c [phi_u^2 +
  phi_l^2 - alpha*(phi_u + phi_l)] dx.
- Canonical families (chord c, xhat = x/c): flat plate phi = 0;
  biconvex parabolic-arc phi_u = 2*tau*(1 - 2*xhat) = -phi_l;
  cambered circular-arc plate phi_u = phi_l = 4*(h/c)*(1 - 2*xhat).
- The section coefficients are gamma-free; the gamma = 1.4 default is
  honored only by surface_pressure_ratio (p/p_inf = 1 + (gamma/2) M^2 Cp).
"""
import math

GAMMA = 1.4
SIMPSON_PANELS = 2000


def _require_mach(mach):
    """ValueError unless mach is finite and strictly above 1.0."""
    if not math.isfinite(mach) or mach <= 1.0:
        raise ValueError(
            "mach must be finite and > 1.0 for ackeret linear theory, got %r" % (mach,))


def ackeret_parameter(mach):
    """beta = sqrt(M^2 - 1), the divisor of every linear coefficient."""
    _require_mach(mach)
    return math.sqrt(mach * mach - 1.0)


def cp_linear(theta_rad, mach):
    """Cp = 2*theta/beta for a surface deflected by theta_rad (radians).

    theta positive means a compression deflection; the sign convention
    follows the windward/suction split of the pressure law.
    """
    if not math.isfinite(theta_rad):
        raise ValueError("theta_rad must be finite, got %r" % (theta_rad,))
    _require_mach(mach)
    return 2.0 * theta_rad / ackeret_parameter(mach)


def lift_coefficient(alpha_rad, mach):
    """cl = 4*alpha/beta of the thin closed section at angle alpha_rad.

    Lift is independent of thickness and camber in the linear theory.
    """
    if not math.isfinite(alpha_rad):
        raise ValueError("alpha_rad must be finite, got %r" % (alpha_rad,))
    _require_mach(mach)
    return 4.0 * alpha_rad / ackeret_parameter(mach)


def lift_curve_slope(mach):
    """Supersonic lift-curve slope cl_alpha = 4/beta per radian."""
    _require_mach(mach)
    return 4.0 / ackeret_parameter(mach)


def flat_plate(alpha_rad, mach):
    """Flat-plate section: cl, cd_wave, cm_le and x_cp_over_c.

    cl = 4a/b, cd_wave = 4a^2/b, cm_le = -2a/b, x_cp/c = 0.5 (the
    supersonic linear-theory center-of-pressure position).
    """
    if not math.isfinite(alpha_rad):
        raise ValueError("alpha_rad must be finite, got %r" % (alpha_rad,))
    _require_mach(mach)
    beta = ackeret_parameter(mach)
    return {
        "cl": 4.0 * alpha_rad / beta,
        "cd_wave": 4.0 * alpha_rad * alpha_rad / beta,
        "cm_le": -2.0 * alpha_rad / beta,
        "x_cp_over_c": 0.5,
    }


def biconvex_section(alpha_rad, thickness_ratio, mach):
    """Thin biconvex (parabolic-arc) section of thickness ratio tau.

    cl = 4a/b, cd_wave = (4a^2 + (16/3) tau^2)/b (thickness wave drag
    additive with the alpha drag), cm_le = -2a/b.
    """
    if not math.isfinite(alpha_rad):
        raise ValueError("alpha_rad must be finite, got %r" % (alpha_rad,))
    if not math.isfinite(thickness_ratio) or thickness_ratio <= 0.0:
        raise ValueError(
            "thickness_ratio must be finite and > 0.0, got %r" % (thickness_ratio,))
    _require_mach(mach)
    beta = ackeret_parameter(mach)
    return {
        "cl": 4.0 * alpha_rad / beta,
        "cd_wave": (4.0 * alpha_rad * alpha_rad + (16.0 / 3.0)
                    * thickness_ratio * thickness_ratio) / beta,
        "cm_le": -2.0 * alpha_rad / beta,
    }


def cambered_plate(alpha_rad, camber_ratio, mach):
    """Circular-arc cambered thin plate of camber ratio h/c, no thickness.

    cl = 4a/b (camber makes no lift in the linear theory), cd_wave =
    (4a^2 + (64/3) (h/c)^2)/b, cm_le = -2a/b - (8/3)(h/c)/b (the camber
    couple pitches the section nose-down).
    """
    if not math.isfinite(alpha_rad):
        raise ValueError("alpha_rad must be finite, got %r" % (alpha_rad,))
    if not math.isfinite(camber_ratio) or camber_ratio <= 0.0:
        raise ValueError(
            "camber_ratio must be finite and > 0.0, got %r" % (camber_ratio,))
    _require_mach(mach)
    beta = ackeret_parameter(mach)
    return {
        "cl": 4.0 * alpha_rad / beta,
        "cd_wave": (4.0 * alpha_rad * alpha_rad + (64.0 / 3.0)
                    * camber_ratio * camber_ratio) / beta,
        "cm_le": (-2.0 * alpha_rad - (8.0 / 3.0) * camber_ratio) / beta,
    }


def section_coefficients(alpha_rad, mach, slope_upper, slope_lower,
                         chord=1.0, panels=SIMPSON_PANELS):
    """General thin section by the linearized pressure integral.

    slope_upper(x) and slope_lower(x) return the surface slopes
    phi_u = dy_u/dx and phi_l = dy_l/dx at x in [0, chord]. The cl,
    cd_wave and cm_le relations above are integrated by deterministic
    composite Simpson over `panels` (even) intervals, so identical
    inputs give identical bits. Closed-form agreement with the three
    canonical families is an identity of the engine.
    """
    if not math.isfinite(alpha_rad):
        raise ValueError("alpha_rad must be finite, got %r" % (alpha_rad,))
    if not math.isfinite(chord) or chord <= 0.0:
        raise ValueError("chord must be finite and > 0.0, got %r" % (chord,))
    if panels < 2 or panels % 2 != 0:
        raise ValueError("panels must be an even integer >= 2, got %r" % (panels,))
    _require_mach(mach)
    beta = ackeret_parameter(mach)

    h = chord / panels
    upper = []
    lower = []
    for i in range(panels + 1):
        x = i * h
        pu = slope_upper(x)
        pl = slope_lower(x)
        if not (math.isfinite(pu) and math.isfinite(pl)):
            raise ValueError(
                "slope callables must return finite values at x=%r" % (x,))
        upper.append(pu)
        lower.append(pl)

    lift_sum = 0.0
    moment_sum = 0.0
    drag_sum = 0.0
    for i in range(panels + 1):
        weight = 1.0 if (i == 0 or i == panels) else (4.0 if i % 2 else 2.0)
        x = i * h
        cp_u = 2.0 * (upper[i] - alpha_rad) / beta
        cp_l = 2.0 * (alpha_rad - lower[i]) / beta
        cp_diff = cp_l - cp_u
        lift_sum += weight * cp_diff
        moment_sum += weight * x * cp_diff
        drag_sum += weight * (upper[i] * upper[i] + lower[i] * lower[i]
                              - alpha_rad * (upper[i] + lower[i]))

    cl = lift_sum * h / (3.0 * chord)
    cm_le = -moment_sum * h / (3.0 * chord * chord)
    cd_wave = (alpha_rad * cl
               + (2.0 / (beta * chord)) * (drag_sum * h / 3.0))
    return {"cl": cl, "cd_wave": cd_wave, "cm_le": cm_le}


def surface_pressure_ratio(cp, mach, gamma=GAMMA):
    """p/p_inf = 1 + (gamma/2) M^2 Cp on the surface.

    The only gamma-dependent relation of the leaf; gamma defaults to the
    air value 1.4.
    """
    if not math.isfinite(gamma) or gamma <= 1.0:
        raise ValueError("gamma must be finite and > 1.0, got %r" % (gamma,))
    _require_mach(mach)
    return 1.0 + 0.5 * gamma * mach * mach * cp

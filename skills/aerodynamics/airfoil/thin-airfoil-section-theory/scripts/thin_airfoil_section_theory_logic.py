"""Thin-airfoil section theory (aerodynamics/airfoil/thin-airfoil-section-theory).

Analytic section aerodynamics of a thin cambered airfoil from its camber
line, pure stdlib math. The camber slope dz/dx is mapped through the Glauert
theta transform x = (1 - cos(theta))/2 and expanded in the sine-series
coefficients A0, A1, A2 by trapezoid quadrature over theta in [0, pi] on a
uniform grid with n_theta intervals, endpoints included. From the
coefficients the leaf recovers the section zero-lift angle alpha_L0, the
section lift coefficient cl = 2*pi*(alpha - alpha_L0), the quarter-chord
pitching-moment coefficient cm_c4 = (pi/4)*(A2 - A1) and the
center-of-pressure location x_cp/c = 1/4 - cm_c4/cl.

Classical relations (Anderson Fundamentals of Aerodynamics; Katz and
Plotkin), summary form only:
  gamma(theta) = 2U (A0 (1 + cos)/sin + A1 sin(theta) + A2 sin(2 theta))
  A0 = alpha - (1/pi) int dz/dx dtheta
  A1 = (2/pi) int dz/dx cos(theta) dtheta
  A2 = (2/pi) int dz/dx cos(2 theta) dtheta
  cl = 2 pi A0 + pi A1 = 2 pi (alpha - alpha_L0)
  alpha_L0 = (1/pi) int dz/dx (1 - cos theta) dtheta, identical to
             -A0(alpha = 0) - A1/2
  cm_c4 = cm_le + cl/4 with cm_le = -(pi/2)(A0 + A1) + (pi/4) A2, giving
          cm_c4 = (pi/4)(A2 - A1) at the aerodynamic center c/4
  x_cp/c = 1/4 - cm_c4/cl

Camber input routes: NACA 4-digit mean-line parameters (m, p), a
power-series polynomial z(x) = sum(c_i x^i), or sampled (x, z) camber
stations read as a piecewise-linear camber line. Incompressible potential
flow only: no Mach effects, viscosity or stall.
"""

import math

PI = math.pi
MIN_N_THETA = 100
CP_CL_ZERO_TOL = 1e-12
CHORD_SPAN_TOL = 1e-12


def _check_n_theta(n_theta):
    """Reject n_theta that is not an int of at least 100 grid intervals."""
    if not isinstance(n_theta, int) or n_theta < MIN_N_THETA:
        raise ValueError("n_theta must be an int >= %d" % MIN_N_THETA)


def _slope_naca4(m, p):
    """Camber slope dz/dx(x) of the NACA 4-digit mean line with (m, p).

    Front segment x <= p: dz/dx = (2m/p^2)(p - x); aft segment x >= p:
    dz/dx = (2m/(1-p)^2)(p - x); the slope is zero at x = p.
    """
    def slope(x):
        if x <= p:
            return 2.0 * m * (p - x) / (p * p)
        return 2.0 * m * (p - x) / ((1.0 - p) * (1.0 - p))
    return slope


def _slope_poly(coeffs):
    """Camber slope dz/dx(x) = sum_{i>=1} i*c_i*x^(i-1) of a polynomial
    mean line z(x) = sum(coeffs[i]*x^i)."""
    def slope(x):
        total = 0.0
        for i in range(1, len(coeffs)):
            total += i * coeffs[i] * x ** (i - 1)
        return total
    return slope


def _slope_points(xs, zs):
    """Constant-per-segment slope of the piecewise-linear camber through
    (xs, zs): segment i carries (zs[i+1] - zs[i]) / (xs[i+1] - xs[i]).

    The quadrature visits x in increasing order (theta sweeps 0 to pi), so
    the segment cursor only advances and one full pass is O(n_stations).
    """
    seg_slopes = [(zs[i + 1] - zs[i]) / (xs[i + 1] - xs[i])
                  for i in range(len(xs) - 1)]
    last_seg = len(seg_slopes) - 1
    cursor = {"seg": 0}

    def slope(x):
        seg = cursor["seg"]
        while seg < last_seg and x > xs[seg + 1]:
            seg += 1
        cursor["seg"] = seg
        return seg_slopes[seg]

    return slope


def _kernel_integrals(slope, n_theta):
    """Trapezoid-rule integrals over theta in [0, pi] of dz/dx times the
    kernels 1, cos(theta), cos(2 theta) and (1 - cos(theta)) on the uniform
    theta grid with n_theta intervals, endpoints included."""
    h = PI / n_theta
    k0 = 0.0
    k1 = 0.0
    k2 = 0.0
    k3 = 0.0
    for i in range(n_theta + 1):
        th = i * h
        w = 0.5 * h if i == 0 or i == n_theta else h
        c1 = math.cos(th)
        dz = slope(0.5 * (1.0 - c1))
        k0 += w * dz
        k1 += w * dz * c1
        k2 += w * dz * math.cos(2.0 * th)
        k3 += w * dz * (1.0 - c1)
    return k0, k1, k2, k3


def _glauert_from_slope(alpha_rad, slope, n_theta):
    """Assemble (A0, A1, A2, alpha_L0) for one camber slope function.

    A0 = alpha - (1/pi) int dz/dx dtheta;
    A1 = (2/pi) int dz/dx cos(theta) dtheta;
    A2 = (2/pi) int dz/dx cos(2 theta) dtheta;
    alpha_L0 = (1/pi) int dz/dx (1 - cos(theta)) dtheta, which equals
    -A0(alpha = 0) - A1/2 identically (A0 vanishes at the zero-lift angle).
    """
    k0, k1, k2, k3 = _kernel_integrals(slope, n_theta)
    a0 = alpha_rad - k0 / PI
    a1 = 2.0 * k1 / PI
    a2 = 2.0 * k2 / PI
    alpha_l0 = k3 / PI
    return a0, a1, a2, alpha_l0


def glauert_coefficients_naca4(alpha_rad, m, p, n_theta=40000):
    """Glauert coefficients (A0, A1, A2, alpha_L0) for a NACA 4-digit mean
    line given by its camber parameters (m, p), slope from the defining
    relations and trapezoid quadrature over the theta transform.

    ValueError for m outside [0, 0.1] (4-digit max-camber range), p outside
    (0, 1), or n_theta not an int >= 100.
    """
    if m < 0.0 or m > 0.1:
        raise ValueError("m (max camber fraction) must be within [0, 0.1]")
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p (camber position fraction) must be within (0, 1)")
    _check_n_theta(n_theta)
    return _glauert_from_slope(alpha_rad, _slope_naca4(m, p), n_theta)


def glauert_coefficients_poly(alpha_rad, coeffs, n_theta=40000):
    """Glauert coefficients (A0, A1, A2, alpha_L0) for the polynomial mean
    line z(x) = sum(coeffs[i]*x^i), slope sum(i*coeffs[i]*x^(i-1)).

    ValueError if coeffs is not a non-empty list or tuple, or n_theta not an
    int >= 100.
    """
    if not isinstance(coeffs, (list, tuple)) or len(coeffs) == 0:
        raise ValueError("coeffs must be a non-empty list or tuple of "
                         "power-series coefficients")
    _check_n_theta(n_theta)
    return _glauert_from_slope(alpha_rad, _slope_poly(coeffs), n_theta)


def glauert_coefficients_points(alpha_rad, xs, zs, n_theta=40000):
    """Glauert coefficients (A0, A1, A2, alpha_L0) for a sampled camber
    line (xs, zs) read as piecewise-linear camber, slope constant per
    segment.

    ValueError if len(xs) != len(zs) or fewer than 2 stations, xs not
    strictly increasing, xs not spanning the chord from 0.0 to 1.0, or
    n_theta not an int >= 100.
    """
    if len(xs) != len(zs) or len(xs) < 2:
        raise ValueError("xs and zs must have the same length, at least "
                         "2 camber stations")
    for i in range(len(xs) - 1):
        if xs[i] >= xs[i + 1]:
            raise ValueError("xs must be strictly increasing")
    if (abs(xs[0] - 0.0) > CHORD_SPAN_TOL or
            abs(xs[-1] - 1.0) > CHORD_SPAN_TOL):
        raise ValueError("xs must span the chord exactly, from 0.0 to 1.0")
    _check_n_theta(n_theta)
    return _glauert_from_slope(alpha_rad, _slope_points(xs, zs), n_theta)


def lift_coefficient(alpha_rad, alpha_L0_rad):
    """Section lift coefficient cl = 2*pi*(alpha - alpha_L0).

    Thin-airfoil linear range; no stall guard and no range check, per the
    leaf contract.
    """
    return 2.0 * PI * (alpha_rad - alpha_L0_rad)


def quarter_chord_moment(A1, A2):
    """Quarter-chord pitching-moment coefficient cm_c4 = (pi/4)*(A2 - A1).

    The A1 + A2 mistranscription is rejected by the identity
    cm_c4 = cm_le + cl/4 and is off by (pi/2)*A2; see the contract test.
    """
    return PI / 4.0 * (A2 - A1)


def center_of_pressure_over_chord(cl, cm_c4):
    """Center-of-pressure location x_cp/c = 1/4 - cm_c4/cl.

    ValueError when |cl| < 1e-12: no defined center of pressure at zero
    lift.
    """
    if abs(cl) < CP_CL_ZERO_TOL:
        raise ValueError("cl must be nonzero: no defined center of pressure "
                         "at zero lift")
    return 0.25 - cm_c4 / cl

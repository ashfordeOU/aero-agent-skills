"""Two-dimensional incompressible laminar far wake behind a thin plate.

The Goldstein (1933) similarity wake that the attached laminar boundary
layers shed from the trailing edge of a thin flat plate at zero
incidence, in the form Schlichting Boundary-Layer Theory (wakes and
free-shear-layers chapter, wake behind a flat plate) and White Viscous
Fluid Flow (laminar free shear layers, plane wake defect solution)
present it, pure Python stdlib (math only), fully deterministic, closed
form, no iteration.

Far downstream of the trailing edge the velocity defect
u1 = U - u collapses onto the small-defect Gaussian similarity profile
u1(x, y) = u_c(x)*exp(-B(x)*y^2) with spread parameter B = U/(4*nu*x)
(x measured downstream from the trailing edge): the exact solution of
the linearized wake equation U*du1/dx = nu*d2u1/dy2 that conserves the
momentum deficit.  The centerline defect decays as the inverse square
root of downstream distance, u_c(x) = (0.664*U/sqrt(pi))*sqrt(c/x) for
the two-sided Blasius plate, and the wake-momentum-integral drag
identity D = rho*U*integral_{-inf}^{+inf} u1 dy reproduces the plate
drag exactly at every downstream station, the closed-form basis of
wake-survey drag measurement.

The plate of chord c, wetted on both sides with fully laminar Blasius
layers to the trailing edge, carries total drag per unit span
D = 1.328*rho*U^2*sqrt(nu*c/U) = 2*rho*U^2*theta_c with
theta_c = 0.664*sqrt(nu*c/U) the Blasius momentum thickness at the
trailing edge.  The full (nonlinear) momentum deficit
rho*integral u*(U - u) dy lies below the linearized identity by a
relative amount of order u_c/U and converges to it downstream, a
documented honesty check.

SI units throughout.  Incompressible constant-property laminar flow
only, uniform nu and rho, small defect u1 << U (the linearized
far-wake regime, x/c at least of order ten), two-dimensional,
thin-plate small-deficit wakes of a symmetric body at zero incidence.
"""

import math

# Module constants (air at standard conditions and the worked plate).
NU_AIR = 1.46e-5        # m2/s, kinematic viscosity of air
RHO_AIR = 1.225         # kg/m3, density of air at sea level
U_INF = 5.0             # m/s, freestream speed of the worked example
PLATE_CHORD = 1.0       # m, chord of the worked plate
BLASIUS_THETA_COEF = 0.664   # Blasius momentum-thickness coefficient
BLASIUS_DRAG_COEF = 1.328    # both-sides average skin-friction drag coef (2*0.664)
SIDES = 2               # plate wetted on both sides


def reynolds_number(U, x, nu):
    """Reynolds number Re = U*x/nu of the running length x, dimensionless.

    U*x/nu, the Reynolds number used for the attached laminar layer
    state (Re_c = U*c/nu at the trailing edge).

    ValueError if U <= 0, x <= 0 or nu <= 0.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if x <= 0:
        raise ValueError("x must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    return U * x / nu


def momentum_thickness_blasius(U, x, nu):
    """Blasius laminar momentum thickness theta = 0.664*sqrt(nu*x/U), m.

    The attached-layer momentum thickness at running length x,
    0.664*c/sqrt(Re_c) at the trailing edge of a plate of chord c, the
    state the far wake carries downstream.

    ValueError set as reynolds_number.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if x <= 0:
        raise ValueError("x must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    return BLASIUS_THETA_COEF * math.sqrt(nu * x / U)


def plate_drag_per_span(U, rho, nu, c, sides=SIDES):
    """Laminar flat-plate drag per unit span, N/m.

    sides*rho*U^2*theta_c with theta_c the trailing-edge Blasius
    momentum thickness: one side carries rho*U^2*theta_c and the
    default two-sided plate doubles it, D = 1.328*rho*U^2*sqrt(nu*c/U),
    the momentum source of the far wake.

    ValueError if U <= 0, rho <= 0, nu <= 0, c <= 0 or sides < 1.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    if c <= 0:
        raise ValueError("c must be positive")
    if sides < 1:
        raise ValueError("sides must be >= 1")
    return sides * rho * U * U * momentum_thickness_blasius(U, c, nu)


def plate_drag_coefficient(U, rho, nu, c):
    """Two-sided laminar plate drag coefficient C_D, dimensionless.

    plate_drag_per_span(U, rho, nu, c)/(0.5*rho*U^2*c) = 4*theta_c/c =
    2.656/sqrt(Re_c), the two-sided drag coefficient (sides fixed at 2
    internally).

    ValueError set as plate_drag_per_span.
    """
    d = plate_drag_per_span(U, rho, nu, c)
    return d / (0.5 * rho * U * U * c)


def wake_spread_parameter(U, nu, x):
    """Gaussian spread parameter B = U/(4*nu*x) of the far wake, 1/m2.

    The exponent factor of the far-wake similarity profile at station x
    measured downstream from the trailing edge; the profile is
    u1(x, y) = u_c(x)*exp(-B(x)*y^2).

    ValueError if U <= 0, nu <= 0 or x <= 0.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    if x <= 0:
        raise ValueError("x must be positive")
    return U / (4.0 * nu * x)


def centerline_defect_from_drag(D, rho, U, B):
    """Centerline velocity defect u_c that conserves the drag D, m/s.

    u_c = (D/(rho*U))*sqrt(B/pi), the normalization that makes the
    wake-momentum-integral identity D = rho*U*integral u1 dy exact at
    every downstream station.

    ValueError if D <= 0, rho <= 0, U <= 0 or B <= 0.
    """
    if D <= 0:
        raise ValueError("D must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    if B <= 0:
        raise ValueError("B must be positive")
    return (D / (rho * U)) * math.sqrt(B / math.pi)


def centerline_defect_blasius(U, c, x):
    """Centerline defect closed form for the two-sided Blasius plate, m/s.

    u_c = (0.664*U/sqrt(pi))*sqrt(c/x), the collapse of
    centerline_defect_from_drag for the two-sided Blasius plate, giving
    the x^-1/2 centerline-defect decay law explicitly.

    ValueError if U <= 0, c <= 0 or x <= 0.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if c <= 0:
        raise ValueError("c must be positive")
    if x <= 0:
        raise ValueError("x must be positive")
    return (BLASIUS_THETA_COEF * U / math.sqrt(math.pi)) * math.sqrt(c / x)


def velocity_defect_gaussian(u_centerline, B, y):
    """Velocity defect u1 at cross-stream position y, m/s.

    u1 = u_c*exp(-B*y^2), the Gaussian far-wake defect profile, always
    non-negative and symmetric in y about the wake axis.

    ValueError if u_centerline < 0 or B <= 0 (y any sign).
    """
    if u_centerline < 0:
        raise ValueError("u_centerline must be >= 0")
    if B <= 0:
        raise ValueError("B must be positive")
    return u_centerline * math.exp(-B * y * y)


def wake_velocity(U, u_centerline, B, y):
    """Recovered wake velocity u = U - u1 at (x, y), m/s.

    The freestream speed minus the Gaussian velocity defect at y, the
    profile a wake-survey traverse would measure.

    ValueError if U <= 0, u_centerline < 0 or B <= 0.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if u_centerline < 0:
        raise ValueError("u_centerline must be >= 0")
    if B <= 0:
        raise ValueError("B must be positive")
    return U - velocity_defect_gaussian(u_centerline, B, y)


def defect_integral(u_centerline, B):
    """Cross-stream integral of the Gaussian defect, m2/s.

    integral u1 dy = u_c*sqrt(pi/B), independent of x and equal to
    D/(rho*U) at every station (momentum conservation of the
    similarity wake).

    ValueError if u_centerline < 0 or B <= 0.
    """
    if u_centerline < 0:
        raise ValueError("u_centerline must be >= 0")
    if B <= 0:
        raise ValueError("B must be positive")
    return u_centerline * math.sqrt(math.pi / B)


def drag_from_wake(u_centerline, B, rho, U):
    """Wake-survey drag from the momentum identity, N/m.

    D = rho*U*integral u1 dy = rho*U*u_c*sqrt(pi/B), the closed-form
    basis of wake-survey drag measurement; equals the plate drag to
    float noise at every downstream station.

    ValueError if u_centerline < 0, B <= 0, rho <= 0 or U <= 0.
    """
    if u_centerline < 0:
        raise ValueError("u_centerline must be >= 0")
    if B <= 0:
        raise ValueError("B must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return rho * U * defect_integral(u_centerline, B)


def half_defect_width(B):
    """Half-defect width y_half = sqrt(ln(2)/B), m.

    The y where the defect equals half its centerline value,
    u1(x, y_half) = u_c/2, growing as x^1/2 downstream.

    ValueError if B <= 0.
    """
    if B <= 0:
        raise ValueError("B must be positive")
    return math.sqrt(math.log(2.0) / B)


def one_over_e_width(B):
    """One-over-e width y_e = sqrt(1/B), m.

    The y where the defect equals u_c*exp(-1), growing as x^1/2
    downstream; y_e/y_half = sqrt(1/ln(2)) exactly.

    ValueError if B <= 0.
    """
    if B <= 0:
        raise ValueError("B must be positive")
    return math.sqrt(1.0 / B)


def full_momentum_deficit(rho, U, u_centerline, B):
    """Full (nonlinear) momentum deficit of the Gaussian wake, N/m.

    rho*(U*integral u1 dy - integral u1^2 dy) with
    integral u1^2 dy = u_c^2*sqrt(pi/(2*B)) the closed form for the
    Gaussian: rho*(U*defect_integral(u_centerline, B) -
    u_centerline^2*sqrt(pi/(2*B))).  Documented diagnostic: it lies
    below drag_from_wake by a relative amount of order u_c/U and
    converges to it as the wake spreads.

    ValueError if u_centerline < 0, B <= 0, rho <= 0 or U <= 0.
    """
    if u_centerline < 0:
        raise ValueError("u_centerline must be >= 0")
    if B <= 0:
        raise ValueError("B must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    sq = u_centerline * u_centerline * math.sqrt(math.pi / (2.0 * B))
    return rho * (U * defect_integral(u_centerline, B) - sq)

"""Mangler transformation for axisymmetric-body laminar boundary layers.

Maps the steady laminar incompressible boundary layer on a slender body of
revolution into an equivalent 2-D flow (Mangler, 1948), with the sharp-cone
closed-form ratios at equal running length. Pure Python stdlib (math only),
closed form, no iteration and no ODE or quadrature anywhere: the power-law
body family r0(x) = A*x^n makes every defining integral analytic.

Geometry convention: x is the running length along the surface from the apex
(cone) or nose (general body), y is the distance normal to the surface,
r0(x) is the body radius at station x, alpha is the cone semi-vertex angle
in degrees, L is the Mangler reference length in m (the transform is
invariant to L: xi scales as L^-2 and ybar as L^-1, so every physical output
is L-free).

The cone functions consume flat-plate baseline values (cf, wall shear,
thicknesses at the SAME running length x and edge velocity) as arguments:
this leaf implements no Blasius correlation of its own, the flat-plate
values are inputs supplied from the sibling boundary-layer-theory
correlations. Laminar incompressible steady flow only, constant nu.
"""

import math

# Laminar cone factors at equal running length (Mangler closed form).
# Wall shear and skin friction on the sharp cone are SQRT3 times the
# flat-plate values at the same running length x.
SQRT3 = 1.7320508075688772
# The 99-percent, displacement and momentum thicknesses on the cone are
# 1/sqrt(3) times the flat-plate values at the same running length x.
INV_SQRT3 = 0.5773502691896258

# Worked-example air (boundary-layer pack convention, shared with
# stagnation-flow-boundary-layer).
RHO_AIR = 1.225      # kg/m3
NU_AIR = 1.5e-5      # m2/s
# Dynamic viscosity is always derived, never an input.
MU_AIR = RHO_AIR * NU_AIR  # 1.8375e-05 Pa s

# Worked-example geometry: slender cone at 5.0 deg half angle, 2.0 m
# running length, constant edge velocity 30.0 m/s, L = 1.0 m.
HALF_ANGLE_DEG = 5.0
X_RUN = 2.0
U_E = 30.0
REF_LENGTH = 1.0

# Worked-example flat-plate baseline (values CONSUMED from the sibling
# boundary-layer-theory Blasius correlations at Re_x = 4.0e6, held only so
# the worked example is reproducible; the cone functions never see them).
BLASIUS_DELTA_COEFF = 5.0
BLASIUS_DSTAR_COEFF = 1.7208
BLASIUS_THETA_COEFF = 0.664
BLASIUS_CF_COEFF = 0.664
BLASIUS_TAU_COEFF = 0.332


def cone_radius(x, half_angle_deg):
    """Cone surface radius r0(x) = x*tan(alpha) at running length x, m.

    Uses tan(alpha) with alpha the semi-vertex angle in degrees (the
    degrees-to-radians conversion is internal), never the small-angle
    approximation, so the slender-cone mapping stays exact.
    """
    if x <= 0.0:
        raise ValueError("x must be positive (running length from the apex)")
    if half_angle_deg <= 0.0 or half_angle_deg >= 90.0:
        raise ValueError("half_angle_deg must be strictly between 0 and 90")
    return x * math.tan(math.radians(half_angle_deg))


def mangler_xi(x, half_angle_deg, ref_length):
    """Mangler-transformed (equivalent 2-D) running length for the cone, m.

    xi = cone_radius(x)**2 * x / (3.0*ref_length**2), the closed form of
    xi = integral_0^x (r0(t)/L)^2 dt on the cone. xi scales as x^3 along a
    cone: the half-length station has one eighth of the xi of the full
    station.
    """
    r0 = cone_radius(x, half_angle_deg)
    if ref_length <= 0.0:
        raise ValueError("ref_length must be positive")
    return r0 * r0 * x / (3.0 * ref_length * ref_length)


def transformed_normal_coordinate(x, y, half_angle_deg, ref_length):
    """Transformed normal coordinate ybar = (r0(x)/L)*y, m.

    The inverse map is y = ybar*L/r0(x); the wall y = 0 maps to ybar = 0.
    """
    if y < 0.0:
        raise ValueError("y must be non-negative (normal distance)")
    r0 = cone_radius(x, half_angle_deg)
    if ref_length <= 0.0:
        raise ValueError("ref_length must be positive")
    return (r0 / ref_length) * y


def powerlaw_mangler_xi(x, amplitude, exponent, ref_length):
    """Mangler xi for the slender body r0(x) = amplitude*x^exponent, m.

    xi = amplitude**2 * x**(2*exponent + 1) / ((2*exponent + 1)*L**2).
    Exponent 0 is the cylinder, exponent 1 is the cone (identity check
    against mangler_xi with amplitude = tan(alpha)).
    """
    if x <= 0.0:
        raise ValueError("x must be positive (running length from the nose)")
    if amplitude <= 0.0:
        raise ValueError("amplitude must be positive (body radius scale)")
    if exponent < 0.0:
        raise ValueError("exponent must be non-negative")
    if ref_length <= 0.0:
        raise ValueError("ref_length must be positive")
    return (amplitude ** 2) * (x ** (2.0 * exponent + 1.0)) / (
        (2.0 * exponent + 1.0) * ref_length * ref_length
    )


def blasius_cf_at_station(cf_at_x1, x1, x2):
    """Local flat-plate Cf at station x2 from its value at x1, Cf ~ 1/sqrt(x).

    Consumption helper with no Blasius constant inside: evaluates the
    equivalent 2-D layer at the Mangler length xi from the flat-plate value
    at the physical station x.
    """
    if cf_at_x1 <= 0.0:
        raise ValueError("cf_at_x1 must be positive")
    if x1 <= 0.0 or x2 <= 0.0:
        raise ValueError("x1 and x2 must be positive stations")
    return cf_at_x1 * math.sqrt(x1 / x2)


def blasius_delta_at_station(delta_at_x1, x1, x2):
    """99-percent flat-plate thickness at x2 from its value at x1, ~sqrt(x).

    Consumption helper with no Blasius constant inside, the thickness twin
    of blasius_cf_at_station.
    """
    if delta_at_x1 <= 0.0:
        raise ValueError("delta_at_x1 must be positive")
    if x1 <= 0.0 or x2 <= 0.0:
        raise ValueError("x1 and x2 must be positive stations")
    return delta_at_x1 * math.sqrt(x2 / x1)


def cone_skin_friction(cf_flat):
    """Local skin-friction coefficient on the cone at running length x.

    SQRT3*cf_flat from the flat-plate value at the same x and edge
    velocity, dimensionless.
    """
    if cf_flat <= 0.0:
        raise ValueError("cf_flat must be positive")
    return SQRT3 * cf_flat


def cone_wall_shear(tau_w_flat):
    """Wall shear on the cone at running length x, Pa.

    SQRT3*tau_w_flat from the flat-plate value at the same x and edge
    velocity. The shear ratio and the Cf ratio are identical because both
    use the same 0.5*rho*u_e**2 normalization.
    """
    if tau_w_flat <= 0.0:
        raise ValueError("tau_w_flat must be positive")
    return SQRT3 * tau_w_flat


def cone_boundary_layer_thickness(delta_flat):
    """99-percent laminar thickness on the cone at running length x, m.

    INV_SQRT3*delta_flat from the flat-plate value at the same x: the cone
    layer is thinner than the plate layer at the same station.
    """
    if delta_flat <= 0.0:
        raise ValueError("delta_flat must be positive")
    return INV_SQRT3 * delta_flat


def cone_displacement_thickness(delta_star_flat):
    """Displacement thickness on the cone at running length x, m.

    INV_SQRT3*delta_star_flat from the flat-plate value at the same x.
    """
    if delta_star_flat <= 0.0:
        raise ValueError("delta_star_flat must be positive")
    return INV_SQRT3 * delta_star_flat


def cone_momentum_thickness(theta_flat):
    """Momentum thickness on the cone at running length x, m.

    INV_SQRT3*theta_flat from the flat-plate value at the same x.
    """
    if theta_flat <= 0.0:
        raise ValueError("theta_flat must be positive")
    return INV_SQRT3 * theta_flat

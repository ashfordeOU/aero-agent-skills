"""Steady creeping (Stokes, 1851) flow of a viscous fluid past a sphere.

The slow-motion solution of the Navier-Stokes equations with the inertia
terms dropped, valid at Reynolds number well below one, in the form
Schlichting Boundary-Layer Theory section 4 presents it, pure Python
stdlib (math only), fully deterministic, closed form, no iteration.

Spherical polar coordinates (r, theta) with theta measured from the
downstream pole: the uniform stream U runs along +z toward theta = 0 and
the windward stagnation point sits at theta = pi.  Stokes streamfunction
psi = 0.5*U*r^2*sin(theta)^2 * (1 - 1.5*a/r + 0.5*(a/r)^3) is identically
zero on the sphere surface r = a (the surface is a streamline) and
approaches the uniform-stream value 0.5*U*r^2*sin(theta)^2 far away.
Radial and tangential velocity follow from the streamfunction; both
vanish on the surface (no slip) and the field is fore-aft symmetric
about the equator plane, the signature of zero Reynolds number: no
wake, no separation.

Surface pressure p - p_inf = -1.5*(mu*U/a)*cos(theta) is HIGH by
1.5*mu*U/a at the windward stagnation point and LOW by the same amount
at the downstream pole (the reversed-pressure signature of creeping
flow); wall shear tau_w = 1.5*(mu*U/a)*sin(theta) peaks at the equator.
Total drag is the Stokes drag F = 6*pi*mu*a*U, one third pressure
(form) drag F_p = 2*pi*mu*a*U and two thirds friction drag
F_f = 4*pi*mu*a*U, the exact 1:2 form-to-friction split; the drag
coefficient is Cd = 24/Re_D with Re_D = U*2a/nu.  The Oseen first-order
correction multiplies the drag by (1 + (3/8)*Re_a) on the radius-based
Reynolds number Re_a = U*a/nu.  Terminal settling velocity of a small
dense sphere in still fluid balances weight minus buoyancy
(4/3)*pi*a^3*(rho_p - rho_f)*g against the Stokes drag:
U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu.

SI units throughout.  Incompressible constant-property laminar flow
only, uniform mu and nu; dynamic viscosity is always derived
mu = rho * nu, never an input.
"""

import math

# Module constants (air at standard conditions for the worked example).
NU_AIR = 1.46e-5            # m2/s, kinematic viscosity of air
RHO_AIR = 1.225             # kg/m3, density of air at sea level
G = 9.81                    # m/s2, gravitational acceleration
RHO_WATER = 1000.0          # kg/m3, particle (water droplet) density
MU_AIR = RHO_AIR * NU_AIR   # Pa s, dynamic viscosity of air, derived


def stokes_streamfunction(U, a, r, theta):
    """Stokes streamfunction psi(r, theta) of the creeping sphere flow.

    psi = 0.5*U*r^2*sin(theta)^2 * (1 - 1.5*a/r + 0.5*(a/r)^3), m3/s.
    psi(a, theta) = 0 identically (the sphere surface is the psi = 0
    streamline) and psi -> 0.5*U*r^2*sin(theta)^2 as r -> inf (uniform
    stream value).

    ValueError if a <= 0 or r < a (the flow occupies r >= a only).
    """
    if a <= 0:
        raise ValueError("a must be positive")
    if r < a:
        raise ValueError("r must be >= a (the flow occupies r >= a only)")
    ar = a / r
    return (0.5 * U * r * r * math.sin(theta) ** 2
            * (1.0 - 1.5 * ar + 0.5 * ar ** 3))


def radial_velocity(U, a, r, theta):
    """Radial velocity u_r(r, theta) of the creeping sphere flow, m/s.

    u_r = U*cos(theta)*(1 - 1.5*a/r + 0.5*(a/r)^3).  On the axis
    upstream of the windward point (theta = pi) u_r is negative (flow
    approaching the sphere), downstream (theta = 0) positive;
    u_r(a, theta) = 0 (no penetration).

    ValueError set as stokes_streamfunction.
    """
    if a <= 0:
        raise ValueError("a must be positive")
    if r < a:
        raise ValueError("r must be >= a (the flow occupies r >= a only)")
    ar = a / r
    return U * math.cos(theta) * (1.0 - 1.5 * ar + 0.5 * ar ** 3)


def tangential_velocity(U, a, r, theta):
    """Tangential velocity u_theta(r, theta) of the creeping flow, m/s.

    u_theta = -U*sin(theta)*(1 - 0.75*a/r - 0.25*(a/r)^3);
    u_theta(a, theta) = 0 (no slip).  Fore-aft symmetry at zero
    Reynolds number: u_r(2a, 0) = -u_r(2a, pi) = +-0.3125*U.

    ValueError set as stokes_streamfunction.
    """
    if a <= 0:
        raise ValueError("a must be positive")
    if r < a:
        raise ValueError("r must be >= a (the flow occupies r >= a only)")
    ar = a / r
    return -U * math.sin(theta) * (1.0 - 0.75 * ar - 0.25 * ar ** 3)


def stokes_drag(mu, a, U):
    """Total Stokes drag F = 6*pi*mu*a*U on the sphere, N.

    The slow-motion drag of the full creeping-flow solution, valid
    while the diameter Reynolds number stays well below one.

    ValueError if mu <= 0, a <= 0 or U <= 0.
    """
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return 6.0 * math.pi * mu * a * U


def pressure_drag(mu, a, U):
    """Pressure (form) drag F_p = 2*pi*mu*a*U on the sphere, N.

    One third of the Stokes drag, from the surface pressure integral
    of p - p_inf = -1.5*(mu*U/a)*cos(theta).

    ValueError set as stokes_drag.
    """
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return 2.0 * math.pi * mu * a * U


def friction_drag(mu, a, U):
    """Friction drag F_f = 4*pi*mu*a*U on the sphere, N.

    Two thirds of the Stokes drag, from the wall-shear integral of
    tau_w = 1.5*(mu*U/a)*sin(theta), so F_p + F_f = F identically and
    F_p/F_f = 1/2 exactly.

    ValueError set as stokes_drag.
    """
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return 4.0 * math.pi * mu * a * U


def surface_pressure_delta(mu, U, a, theta):
    """Surface pressure difference p - p_inf at polar angle theta, Pa.

    p - p_inf = -1.5*(mu*U/a)*cos(theta): HIGH by 1.5*mu*U/a at the
    windward stagnation point theta = pi, LOW by the same amount at the
    downstream pole theta = 0, zero at the equator theta = pi/2 (the
    reversed-pressure signature of creeping flow, no dynamic-pressure
    head).

    ValueError if mu <= 0, a <= 0 or U <= 0; theta is any real.
    """
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return -1.5 * (mu * U / a) * math.cos(theta)


def wall_shear_stress(mu, U, a, theta):
    """Wall shear stress tau_w at polar angle theta on the sphere, Pa.

    tau_w = 1.5*(mu*U/a)*sin(theta): zero at the stagnation points
    theta = 0 and pi, peak 1.5*mu*U/a at the equator theta = pi/2.

    ValueError set as surface_pressure_delta.
    """
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    return 1.5 * (mu * U / a) * math.sin(theta)


def radius_reynolds(U, a, nu):
    """Radius-based Reynolds number Re_a = U*a/nu (Oseen correction).

    Dimensionless.  The Oseen first-order drag factor is
    1 + (3/8)*Re_a on this radius-based Reynolds number.

    ValueError if U <= 0, a <= 0 or nu <= 0.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    return U * a / nu


def diameter_reynolds(U, a, nu):
    """Diameter-based Reynolds number Re_D = U*2a/nu of Cd = 24/Re_D.

    Dimensionless.  Twice the radius-based Reynolds number; the
    creeping range is Re_D below about 0.1 for the pure Stokes balance.

    ValueError set as radius_reynolds.
    """
    if U <= 0:
        raise ValueError("U must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    return U * 2.0 * a / nu


def drag_coefficient(rho, mu, U, a):
    """Stokes drag coefficient Cd = 12*mu/(rho*U*a), dimensionless.

    Equal to 24/Re_D on the diameter Reynolds number and to
    F/(0.5*rho*U^2*pi*a^2) on the freestream dynamic pressure and
    frontal area.

    ValueError if rho <= 0, mu <= 0, U <= 0 or a <= 0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive")
    if mu <= 0:
        raise ValueError("mu must be positive")
    if U <= 0:
        raise ValueError("U must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    return 12.0 * mu / (rho * U * a)


def oseen_correction(Re_a):
    """Oseen first-order drag factor 1 + (3/8)*Re_a, dimensionless.

    Multiplies the Stokes drag toward Reynolds numbers approaching
    one: 1.1875 at Re_a = 0.5, identical to 1 + (3/16)*Re_D at
    Re_D = 1.0 (the two Reynolds conventions give the same factor).

    ValueError if Re_a < 0.
    """
    if Re_a < 0:
        raise ValueError("Re_a must be >= 0")
    return 1.0 + (3.0 / 8.0) * Re_a


def oseen_drag(mu, a, U, nu):
    """Oseen-corrected drag F = 6*pi*mu*a*U*(1 + (3/8)*Re_a), N.

    Stokes drag times the Oseen first-order correction on the
    radius-based Reynolds number, for Reynolds numbers approaching one.

    ValueError if nu <= 0 plus the stokes_drag set.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    return stokes_drag(mu, a, U) * oseen_correction(radius_reynolds(U, a, nu))


def terminal_velocity(rho_particle, rho_fluid, mu, a):
    """Stokes terminal settling velocity of a small dense sphere, m/s.

    U_t = (2/9)*(rho_particle - rho_fluid)*G*a^2/mu, the closed-form
    balance of weight minus buoyancy (4/3)*pi*a^3*(rho_p - rho_f)*g
    against the Stokes drag, valid while the Reynolds number at U_t
    stays below about 0.1.

    ValueError if rho_particle <= 0, rho_fluid <= 0, rho_particle <=
    rho_fluid (a neutrally or positively buoyant sphere does not
    settle), mu <= 0 or a <= 0.
    """
    if rho_particle <= 0:
        raise ValueError("rho_particle must be positive")
    if rho_fluid <= 0:
        raise ValueError("rho_fluid must be positive")
    if rho_particle <= rho_fluid:
        raise ValueError("rho_particle must exceed rho_fluid for settling")
    if mu <= 0:
        raise ValueError("mu must be positive")
    if a <= 0:
        raise ValueError("a must be positive")
    return (2.0 / 9.0) * (rho_particle - rho_fluid) * G * a * a / mu


def oseen_terminal_velocity(rho_particle, rho_fluid, mu, a, nu):
    """Oseen-corrected terminal settling velocity, m/s.

    The closed-form root U of the corrected balance
    U*(1 + (3/8)*U*a/nu) = U_t, U = (-1 + sqrt(1 + 4*c*U_t))/(2*c)
    with c = (3/8)*(a/nu); lies below the Stokes terminal velocity.

    ValueError set as terminal_velocity plus nu <= 0.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    u_s = terminal_velocity(rho_particle, rho_fluid, mu, a)
    c = (3.0 / 8.0) * (a / nu)
    return (-1.0 + math.sqrt(1.0 + 4.0 * c * u_s)) / (2.0 * c)

"""Exact unsteady laminar Stokes layers over an infinite flat plate.

Closed-form solutions of the one-dimensional vorticity diffusion
equation u_t = nu * u_yy for a quiescent half-space above a plate at
y = 0, pure Python stdlib (math only), fully deterministic.

Stokes first problem (Rayleigh layer): the plate is impulsively started
at t = 0 to speed U and the layer diffuses outward self-similarly with
u/U = erfc(eta), eta = y / (2 * sqrt(nu * t)).  The layer edge sits at
delta = 3.6428 * sqrt(nu * t) where u/U = 0.01, the wall shear decays
as tau_w = rho * U * sqrt(nu / (pi * t)) so that tau_w * sqrt(t) is
constant, and the displacement thickness is delta* = 2 * sqrt(nu*t/pi).

Stokes second problem (oscillating plate): the plate oscillates in its
own plane as U * cos(omega * t) and the steady-periodic solution is
u = U * exp(-y/delta) * cos(omega * t - y/delta) with penetration depth
delta = sqrt(2 * nu / omega).  The wall shear has amplitude
tau_amp = rho * U * sqrt(nu * omega) and, with the resistance-on-plate
convention tau_w = -mu * du/dy|0, leads the plate velocity by 45
degrees: tau_w(t) = tau_amp * cos(omega * t + pi / 4).

SI units throughout.  Incompressible constant-property laminar flow
only, uniform nu; dynamic viscosity is always derived mu = rho * nu,
never an input.
"""

import math

# Module constants (air at standard conditions for the worked example).
NU_AIR = 1.46e-5          # m2/s, kinematic viscosity of air
RHO_AIR = 1.225           # kg/m3, density of air at sea level
DELTA99_COEF = 3.6428     # layer-edge coefficient, 2 * 1.8214 where
                          # erfc(1.8214) = 0.01 (99-percent-deficit point)
PI = math.pi


def stokes_first_velocity(U, nu, y, t):
    """Velocity u(y, t) after an impulsive plate start, m/s.

    u = U * erfc(y / (2 * sqrt(nu * t))), the similarity solution of
    Stokes first problem (Rayleigh layer): u(0, t) = U exactly at the
    wall for all t > 0 and u/U -> 0 deep in the fluid.

    ValueError if nu <= 0 (no diffusion), t <= 0 (the t = 0 step is
    singular) or y < 0 (the fluid occupies the half-space y >= 0).
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    if t <= 0:
        raise ValueError("t must be positive (the impulsive start is singular at t = 0)")
    if y < 0:
        raise ValueError("y must be >= 0 (fluid occupies the half-space y >= 0)")
    eta = y / (2.0 * math.sqrt(nu * t))
    return U * math.erfc(eta)


def rayleigh_layer_thickness(nu, t):
    """Layer edge of Stokes first problem, m.

    delta = DELTA99_COEF * sqrt(nu * t), the 99-percent-deficit point
    where u/U = erfc(1.8214) = 0.01.  Grows as sqrt(t):
    delta(t2)/delta(t1) = sqrt(t2/t1).

    ValueError if nu <= 0 or t <= 0.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    if t <= 0:
        raise ValueError("t must be positive")
    return DELTA99_COEF * math.sqrt(nu * t)


def stokes_first_wall_shear(rho, U, nu, t):
    """Wall shear magnitude of Stokes first problem, Pa.

    tau_w = rho * U * sqrt(nu / (pi * t)), positive for U > 0, from
    mu * |du/dy|0 with du/dy|0 = -U / sqrt(pi * nu * t).  Decays as
    1/sqrt(t) so tau_w * sqrt(t) = rho * U * sqrt(nu / pi) is constant.

    ValueError if rho <= 0, nu <= 0 or t <= 0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    if t <= 0:
        raise ValueError("t must be positive")
    return rho * U * math.sqrt(nu / (PI * t))


def stokes_first_displacement_thickness(nu, t):
    """Displacement thickness of the Rayleigh layer, m.

    delta* = integral_0^inf (1 - u/U) dy = 2 * sqrt(nu * t / pi) (the
    integral of erfc over the half-space is 1/sqrt(pi)).  The momentum
    balance rho * U * d(delta*)/dt = tau_w holds identically.

    ValueError if nu <= 0 or t <= 0.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    if t <= 0:
        raise ValueError("t must be positive")
    return 2.0 * math.sqrt(nu * t / PI)


def stokes_second_velocity(U, nu, omega, y, t):
    """Velocity u(y, t) of the oscillating plate layer, m/s.

    u = U * exp(-y/delta) * cos(omega * t - y/delta) with penetration
    depth delta = sqrt(2 * nu / omega), the real part of
    U * exp(i * omega * t - (1 + i) * k * y), k = 1/delta.  No slip at
    the wall: u(0, t) = U * cos(omega * t) exactly.  t is any real
    (steady-periodic state).

    ValueError if nu <= 0, omega <= 0 or y < 0.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    if omega <= 0:
        raise ValueError("omega must be positive")
    if y < 0:
        raise ValueError("y must be >= 0 (fluid occupies the half-space y >= 0)")
    delta = math.sqrt(2.0 * nu / omega)
    return U * math.exp(-y / delta) * math.cos(omega * t - y / delta)


def stokes_penetration_depth(nu, omega):
    """Penetration depth (Stokes layer thickness) of the oscillating
    plate layer, m.

    delta = sqrt(2 * nu / omega), the depth at which the oscillation
    amplitude is exp(-1) * U and the phase lag is exactly 1 radian.

    ValueError if nu <= 0 or omega <= 0.
    """
    if nu <= 0:
        raise ValueError("nu must be positive")
    if omega <= 0:
        raise ValueError("omega must be positive")
    return math.sqrt(2.0 * nu / omega)


def stokes_second_shear_amplitude(rho, U, nu, omega):
    """Wall shear amplitude of the oscillating plate layer, Pa.

    tau_amp = rho * U * sqrt(nu * omega), equal to mu * U *
    sqrt(omega / nu) with mu = rho * nu.  The wall shear swings between
    +tau_amp and -tau_amp each cycle.

    ValueError if rho <= 0, nu <= 0 or omega <= 0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive")
    if nu <= 0:
        raise ValueError("nu must be positive")
    if omega <= 0:
        raise ValueError("omega must be positive")
    return rho * U * math.sqrt(nu * omega)


def stokes_second_wall_shear(rho, U, nu, omega, t):
    """Wall shear time history of the oscillating plate layer, Pa.

    tau_w(t) = tau_amp * cos(omega * t + pi / 4) with the
    resistance-on-plate convention tau_w = -mu * du/dy|0 (positive
    resisting +x plate motion).  Leads the plate velocity U*cos(omega*t)
    by 45 degrees (one-eighth period) and vanishes at omega * t = pi/4.

    ValueError as stokes_second_shear_amplitude.
    """
    tau_amp = stokes_second_shear_amplitude(rho, U, nu, omega)
    return tau_amp * math.cos(omega * t + PI / 4.0)

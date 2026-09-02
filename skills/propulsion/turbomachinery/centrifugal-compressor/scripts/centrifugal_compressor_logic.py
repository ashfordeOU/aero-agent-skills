#!/usr/bin/env python3
"""Centrifugal compressor stage design and off-design assessment logic.

Convention (Dixon / Watson and Janota): a centrifugal impeller adds
work to the flow through the Euler turbine equation. All angles in
RADIANS. The blade back-sweep angle beta2b is measured from the
radial direction at the impeller exit (0 for radial vanes, positive
backward). Flow slip at the impeller exit is captured by the slip
factor sigma, so the tangential velocity of the throughflow at exit
is Ctheta2 = sigma*u2 - cm2*tan(beta2b).

Quantities (SI units throughout):
- rotational speed n in rpm, diameters d in m
- tip speeds u1 (inducer tip), u2 (impeller exit) in m/s
- meridional/axial velocities cm2 (impeller exit), ca1 (inducer
  inlet) in m/s; prewhirl ctheta1 in m/s (0 for axial inlet)
- slip factor sigma, work input coefficient psi dimensionless
- specific rotor work w in J/kg
- total temperature rise delta_t0 in K; stage pressure ratio
  pi dimensionless
- isentropic efficiency eta dimensionless, cp in J/(kg K),
  gamma dimensionless
- relative velocities w1 (inducer), w2 (impeller exit) in m/s,
  diffusion ratio dr and de Haller number dh dimensionless

FAR-33 is referenced, not reproduced; the slip factor and Euler work
relations are common turbomachinery methodology summarized per
standards-map.yaml.

Functions raise ValueError on non-physical inputs (n <= 0, d <= 0,
z <= 0, t01 <= 0, eta outside (0, 1], |beta2b| >= pi/2, sigma <= 0)
instead of returning nonsense or dividing by zero.
"""

import math


def tip_speed(n_rpm, d):
    """Impeller tip speed U = pi*d*n/60 in m/s.

    n_rpm is the rotational speed in rpm and d the diameter in m
    (impeller exit for U2, inducer tip for U1).
    """
    if n_rpm <= 0:
        raise ValueError("n_rpm must be > 0, got %r" % (n_rpm,))
    if d <= 0:
        raise ValueError("d must be > 0, got %r" % (d,))
    return math.pi * d * n_rpm / 60.0


def wiesner_slip(z, beta2b=0.0):
    """Wiesner slip factor sigma = 1 - sqrt(cos(beta2b))/z**0.7.

    z is the number of impeller blades and beta2b the back-sweep
    angle from the radial direction in radians (0 for radial vanes,
    positive backward). Dimensionless; back sweep slightly raises
    sigma (sqrt(cos(beta2b)) < 1 shrinks the subtracted term).
    """
    if z <= 0:
        raise ValueError("z must be > 0, got %r" % (z,))
    if abs(beta2b) >= math.pi / 2.0:
        raise ValueError("|beta2b| must be < pi/2, got %r" % (beta2b,))
    return 1.0 - math.sqrt(math.cos(beta2b)) / (z ** 0.7)


def stanitz_slip(z):
    """Stanitz slip factor sigma = 1 - 1.98/z for radial-vaned impellers.

    z is the number of impeller blades; the correlation applies to
    radial vanes (beta2b = 0). Dimensionless.
    """
    if z <= 1.98:
        raise ValueError(
            "z must be > 1.98 for a positive Stanitz slip factor, got %r" % (z,)
        )
    return 1.0 - 1.98 / z


def euler_work(u2, sigma, cm2, beta2b=0.0, u1=0.0, ctheta1=0.0):
    """Specific rotor work w = u2*(sigma*u2 - cm2*tan(beta2b)) - u1*ctheta1.

    u2 is the impeller exit tip speed, sigma the slip factor, cm2 the
    exit meridional velocity, beta2b the back-sweep angle, u1 the
    inducer tip speed, and ctheta1 the prewhirl at the inducer inlet
    (0 for an axial inlet). w in J/kg, positive for a compressing
    rotor. With sigma = 1 and beta2b = ctheta1 = 0 the relation
    reduces to the slip-free Euler work w = u2**2.
    """
    if u2 <= 0:
        raise ValueError("u2 must be > 0, got %r" % (u2,))
    if sigma <= 0:
        raise ValueError("sigma must be > 0, got %r" % (sigma,))
    if cm2 < 0:
        raise ValueError("cm2 must be >= 0, got %r" % (cm2,))
    if abs(beta2b) >= math.pi / 2.0:
        raise ValueError("|beta2b| must be < pi/2, got %r" % (beta2b,))
    if u1 < 0 or ctheta1 < 0:
        raise ValueError(
            "u1 and ctheta1 must be >= 0, got %r, %r" % (u1, ctheta1)
        )
    return u2 * (sigma * u2 - cm2 * math.tan(beta2b)) - u1 * ctheta1


def work_input_coefficient(u2, sigma, cm2, beta2b=0.0, u1=0.0, ctheta1=0.0):
    """Work input coefficient psi = w/u2**2, dimensionless."""
    return euler_work(u2, sigma, cm2, beta2b, u1, ctheta1) / (u2 * u2)


def total_temperature_rise(w, cp=1005.0):
    """Stage total temperature rise delta_t0 = w/cp in K.

    w is the specific rotor work in J/kg and cp the specific heat at
    constant pressure in J/(kg K).
    """
    if cp <= 0:
        raise ValueError("cp must be > 0, got %r" % (cp,))
    return w / cp


def stage_pressure_ratio(w, t01, eta=0.9, cp=1005.0, gamma=1.4):
    """Isentropic stage total pressure ratio
    pi = (1 + eta*w/(cp*t01))**(gamma/(gamma-1)), dimensionless.

    w is the specific rotor work in J/kg, t01 the inlet total
    temperature in K, eta the stage isentropic efficiency (default
    0.9), cp and gamma air-standard defaults 1005 J/(kg K) and 1.4.
    """
    if t01 <= 0:
        raise ValueError("t01 must be > 0, got %r" % (t01,))
    if not (0.0 < eta <= 1.0):
        raise ValueError("eta must be in (0, 1], got %r" % (eta,))
    if cp <= 0:
        raise ValueError("cp must be > 0, got %r" % (cp,))
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    return (1.0 + eta * w / (cp * t01)) ** (gamma / (gamma - 1.0))


def relative_velocities(ca1, u1, ctheta1, cm2, beta2b):
    """Inducer and impeller-exit relative velocities (w1, w2) in m/s.

    w1 = sqrt(ca1**2 + (u1 - ctheta1)**2) at the inducer tip and
    w2 = cm2/cos(beta2b) at the impeller exit. ca1 is the inducer
    axial velocity, u1 the inducer tip speed, ctheta1 the prewhirl,
    cm2 the exit meridional velocity, beta2b the back-sweep angle.
    """
    if ca1 <= 0:
        raise ValueError("ca1 must be > 0, got %r" % (ca1,))
    if u1 <= 0:
        raise ValueError("u1 must be > 0, got %r" % (u1,))
    if cm2 <= 0:
        raise ValueError("cm2 must be > 0, got %r" % (cm2,))
    if abs(beta2b) >= math.pi / 2.0:
        raise ValueError("|beta2b| must be < pi/2, got %r" % (beta2b,))
    w1 = math.sqrt(ca1 * ca1 + (u1 - ctheta1) ** 2)
    w2 = cm2 / math.cos(beta2b)
    return w1, w2


def diffusion_ratio(ca1, u1, ctheta1, cm2, beta2b, limit=1.6):
    """Impeller diffusion assessment as a dict.

    Diffusion ratio dr = w1/w2 and de Haller number dh = w2/w1,
    dimensionless, from the inducer and impeller-exit relative
    velocities; diffusion_ok is True when dr <= limit (default 1.6,
    dh >= 0.625). Also returns w1 and w2 in m/s.
    """
    w1, w2 = relative_velocities(ca1, u1, ctheta1, cm2, beta2b)
    dr = w1 / w2
    return {
        "w1": w1,
        "w2": w2,
        "dr": dr,
        "de_haller": w2 / w1,
        "diffusion_ok": dr <= limit,
    }


def design_point(n_rpm, d2, d1, z, cm2, ca1, t01, beta2b=0.0, eta=0.85,
                 cp=1005.0, gamma=1.4, ctheta1=0.0, slip="wiesner"):
    """Full centrifugal compressor stage design-point assessment.

    Assembles the velocity-triangle and stage performance parameters
    for one design point. n_rpm is the rotational speed, d2 the
    impeller exit diameter, d1 the inducer tip diameter, z the blade
    count, cm2 the exit meridional velocity, ca1 the inducer axial
    velocity, t01 the inlet total temperature, beta2b the back-sweep
    angle, eta the isentropic efficiency (default 0.85), and slip the
    correlation selector ('wiesner' or 'stanitz').

    Returns a dict with u2, u1, sigma, work, psi, delta_t0,
    pressure_ratio, w1, w2, dr, de_haller, and diffusion_ok.
    """
    u2 = tip_speed(n_rpm, d2)
    u1 = tip_speed(n_rpm, d1)
    if slip == "wiesner":
        sigma = wiesner_slip(z, beta2b)
    elif slip == "stanitz":
        if beta2b != 0.0:
            raise ValueError(
                "stanitz slip assumes radial vanes, beta2b must be 0"
            )
        sigma = stanitz_slip(z)
    else:
        raise ValueError(
            "slip must be 'wiesner' or 'stanitz', got %r" % (slip,)
        )
    w = euler_work(u2, sigma, cm2, beta2b, u1, ctheta1)
    psi = work_input_coefficient(u2, sigma, cm2, beta2b, u1, ctheta1)
    d_t0 = total_temperature_rise(w, cp)
    pi = stage_pressure_ratio(w, t01, eta, cp, gamma)
    diff = diffusion_ratio(ca1, u1, ctheta1, cm2, beta2b)
    return {
        "u2": u2,
        "u1": u1,
        "sigma": sigma,
        "work": w,
        "psi": psi,
        "delta_t0": d_t0,
        "pressure_ratio": pi,
        "w1": diff["w1"],
        "w2": diff["w2"],
        "dr": diff["dr"],
        "de_haller": diff["de_haller"],
        "diffusion_ok": diff["diffusion_ok"],
    }

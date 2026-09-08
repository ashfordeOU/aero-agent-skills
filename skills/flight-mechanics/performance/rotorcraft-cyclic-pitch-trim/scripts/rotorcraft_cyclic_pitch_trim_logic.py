"""Rotorcraft cyclic-pitch trim: cyclic-forced flap equilibrium and trim inversion.

Pure stdlib, deterministic, no RNG. Extends the wave-46 forward-flight
flapping harmonic balance of an idealized centrally hinged, untwisted,
featherless rotor blade with the cyclic control channel
theta(psi) = theta0 + theta1c*cos(psi) + theta1s*sin(psi) (Johnson,
Helicopter Theory ch. 4; Leishman, Principles of Helicopter Aerodynamics
ch. 4, paraphrased). The steady, cos and sin Fourier projections of the
aerodynamic flap moment about the central hinge are equated to their
structural counterparts, giving the closed-form coning angle a0, the
longitudinal flapping angle a1s and the lateral flapping angle b1s as
algebraic functions of the advance ratio mu, the inflow ratio lambda, the
collective pitch theta0, the blade Lock number gamma and the cyclic
pitches theta1c and theta1s, plus the closed-form trim inversion that
solves for the cyclic command holding the tip-path plane at a target
attitude and its equivalent ideal swashplate tilt.

At theta1c = theta1s = 0 every closed form here reduces exactly to the
rotorcraft-forward-flight-flapping sibling's collective-only closed
forms; that sibling owns the collective-only equilibrium and the
tip-path-plane-tilt quantities themselves. This leaf covers only the
cyclic control channel and the trim inversion, not rotor power,
lead-lag dynamics, hover-state coning or higher flapping harmonics.
"""

import math

# Module constants
DEG = 180.0 / math.pi  # radians to degrees conversion factor
MU_MAX = 1.0            # advance-ratio model boundary (singular at mu = 1)


def _validate_mu_lam(mu, lam):
    """Shared range checks for the advance ratio and inflow ratio."""
    if not math.isfinite(mu):
        raise ValueError("mu must be finite")
    if not math.isfinite(lam):
        raise ValueError("lam must be finite")
    if mu < 0.0:
        raise ValueError("mu (advance ratio) must be non-negative")
    if mu >= MU_MAX:
        raise ValueError("mu (advance ratio) must be below %s" % MU_MAX)
    if lam <= 0.0:
        raise ValueError("lam (inflow ratio) must be positive")


def _validate_theta0(theta0):
    """Range check for the collective pitch input."""
    if not math.isfinite(theta0):
        raise ValueError("theta0 must be finite")
    if theta0 <= 0.0:
        raise ValueError("theta0 (collective pitch) must be positive")


def _validate_gamma(gamma):
    """Range check for the blade Lock number input."""
    if not math.isfinite(gamma):
        raise ValueError("gamma must be finite")
    if gamma <= 0.0:
        raise ValueError("gamma (Lock number) must be positive")


def _validate_finite(**kwargs):
    """Finiteness checks for cyclic pitch and trim-target arguments."""
    for name, value in kwargs.items():
        if not math.isfinite(value):
            raise ValueError("%s must be finite" % name)


def coning_angle(mu, lam, theta0, gamma, theta1s):
    """Cyclic-forced coning angle a0.

    a0 = (gamma / 2) * (theta0 * (1 + mu**2) / 4 - lam / 3 + mu * theta1s / 3),
    the steady Fourier projection of the flap equation gaining the
    mean-lift term mu * theta1s / 3 from the longitudinal cyclic pitch.
    Independent of theta1c, a1s and b1s (their mean couplings cancel
    identically). Reduces exactly to the hover closed form
    0.5 * gamma * (theta0 / 4 - lam / 3) at mu = 0.0. Raises ValueError on
    any non-physical or non-finite argument.
    """
    _validate_mu_lam(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    _validate_finite(theta1s=theta1s)
    return (gamma / 2.0) * (theta0 * (1.0 + mu ** 2) / 4.0 - lam / 3.0 + mu * theta1s / 3.0)


def longitudinal_flapping_angle(mu, lam, theta0, theta1s):
    """Longitudinal flapping angle a1s under the cyclic-forced equilibrium.

    a1s = -[4 * mu * (2 * theta0 / 3 - lam / 2) + theta1s * (1 + 3 * mu**2 / 2)]
    / (1 - mu**2 / 2), the cos(psi) Fourier projection nulled at 1/rev
    resonance. Takes no gamma (it cancels in the 1/rev balance) and no
    theta1c (the cos-harmonic pitch never projects here). Returns exactly
    -theta1s at mu = 0.0. Raises ValueError on any non-physical or
    non-finite argument.
    """
    _validate_mu_lam(mu, lam)
    _validate_theta0(theta0)
    _validate_finite(theta1s=theta1s)
    if mu == 0.0:
        return -theta1s
    numerator = 4.0 * mu * (2.0 * theta0 / 3.0 - lam / 2.0) + theta1s * (1.0 + 3.0 * mu ** 2 / 2.0)
    return -numerator / (1.0 - mu ** 2 / 2.0)


def lateral_flapping_angle(mu, lam, theta0, gamma, theta1c, theta1s):
    """Lateral flapping angle b1s under the cyclic-forced equilibrium.

    b1s = theta1c - (4 * mu / 3) * coning_angle(...) / (1 + mu**2 / 2),
    the sin(psi) Fourier projection. Carries theta1c with unity gain and
    gamma, mu, theta1s through the coning coupling. Returns exactly
    theta1c at mu = 0.0. Raises ValueError on any non-physical or
    non-finite argument.
    """
    _validate_mu_lam(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    _validate_finite(theta1c=theta1c, theta1s=theta1s)
    if mu == 0.0:
        return theta1c
    a0 = coning_angle(mu, lam, theta0, gamma, theta1s)
    return theta1c - (4.0 * mu / 3.0) * a0 / (1.0 + mu ** 2 / 2.0)


def flap_response_summary(mu, lam, theta0, gamma, theta1c, theta1s):
    """One-call cyclic-forced flap equilibrium assessment dict.

    Returns {coning_angle_rad, coning_angle_deg,
    longitudinal_flapping_rad, longitudinal_flapping_deg,
    lateral_flapping_rad, lateral_flapping_deg}. Each _deg value equals
    the corresponding _rad value times DEG (180 / pi), and each
    component matches the standalone function evaluated at the same
    arguments. ValueErrors propagate from the underlying checks.
    """
    a0_rad = coning_angle(mu, lam, theta0, gamma, theta1s)
    a1s_rad = longitudinal_flapping_angle(mu, lam, theta0, theta1s)
    b1s_rad = lateral_flapping_angle(mu, lam, theta0, gamma, theta1c, theta1s)
    return {
        "coning_angle_rad": a0_rad,
        "coning_angle_deg": a0_rad * DEG,
        "longitudinal_flapping_rad": a1s_rad,
        "longitudinal_flapping_deg": a1s_rad * DEG,
        "lateral_flapping_rad": b1s_rad,
        "lateral_flapping_deg": b1s_rad * DEG,
    }


def cyclic_response_gains(mu, lam, theta0, gamma):
    """Affine control-to-flap gains of the cyclic-forced equilibrium map.

    Returns {a1s_free, b1s_free, d_a1s_d_theta1s, d_a1s_d_theta1c,
    d_b1s_d_theta1c, d_b1s_d_theta1s}: a1s_free and b1s_free are the
    wave-46 zero-cyclic flapping angles; d_a1s_d_theta1s =
    -(1 + 3 * mu**2 / 2) / (1 - mu**2 / 2); d_a1s_d_theta1c = 0.0 exactly
    (the cos-harmonic pitch never projects onto the a1s balance);
    d_b1s_d_theta1c = 1.0 exactly; d_b1s_d_theta1s =
    -(2 * gamma * mu**2 / 9) / (1 + mu**2 / 2), the coning-mediated cross
    coupling, zero at mu = 0.0 and quadratic in mu. Validates state and
    gamma only (no cyclic arguments). Raises ValueError on any
    non-physical or non-finite argument.
    """
    _validate_mu_lam(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    a1s_free = longitudinal_flapping_angle(mu, lam, theta0, 0.0)
    b1s_free = lateral_flapping_angle(mu, lam, theta0, gamma, 0.0, 0.0)
    d_a1s_d_theta1s = -(1.0 + 3.0 * mu ** 2 / 2.0) / (1.0 - mu ** 2 / 2.0)
    d_b1s_d_theta1s = -(2.0 * gamma * mu ** 2 / 9.0) / (1.0 + mu ** 2 / 2.0)
    return {
        "a1s_free": a1s_free,
        "b1s_free": b1s_free,
        "d_a1s_d_theta1s": d_a1s_d_theta1s,
        "d_a1s_d_theta1c": 0.0,
        "d_b1s_d_theta1c": 1.0,
        "d_b1s_d_theta1s": d_b1s_d_theta1s,
    }


def trim_cyclic(mu, lam, theta0, gamma, a1s_target, b1s_target):
    """Closed-form trim inversion for the cyclic pitch holding the target attitude.

    Solves the equilibrium map for the cyclic command
    (theta1s, theta1c) that holds the tip-path plane at
    (a1s_target, b1s_target):
    theta1s = -[a1s_target * (1 - mu**2 / 2) + 4 * mu * (2 * theta0 / 3 - lam / 2)]
    / (1 + 3 * mu**2 / 2), then a0 from coning_angle at that theta1s,
    then theta1c = b1s_target + (4 * mu / 3) * a0 / (1 + mu**2 / 2). At
    mu = 0.0 the limiting form is theta1s = -a1s_target,
    theta1c = b1s_target. Returns exactly
    {longitudinal_cyclic_pitch_rad, longitudinal_cyclic_pitch_deg,
    lateral_cyclic_pitch_rad, lateral_cyclic_pitch_deg}. Targets are free
    finite reals. Raises ValueError on any non-physical or non-finite
    argument.
    """
    _validate_mu_lam(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    _validate_finite(a1s_target=a1s_target, b1s_target=b1s_target)
    if mu == 0.0:
        theta1s = -a1s_target
        theta1c = b1s_target
    else:
        theta1s = -(a1s_target * (1.0 - mu ** 2 / 2.0) + 4.0 * mu * (2.0 * theta0 / 3.0 - lam / 2.0)) \
            / (1.0 + 3.0 * mu ** 2 / 2.0)
        a0 = coning_angle(mu, lam, theta0, gamma, theta1s)
        theta1c = b1s_target + (4.0 * mu / 3.0) * a0 / (1.0 + mu ** 2 / 2.0)
    return {
        "longitudinal_cyclic_pitch_rad": theta1s,
        "longitudinal_cyclic_pitch_deg": theta1s * DEG,
        "lateral_cyclic_pitch_rad": theta1c,
        "lateral_cyclic_pitch_deg": theta1c * DEG,
    }


def trim_swashplate_tilt(mu, lam, theta0, gamma, a1s_target, b1s_target):
    """Ideal zero-phase swashplate tilt report of the same trim.

    Under the ideal zero-control-phase swashplate idealization with unit
    pitch gearing, the longitudinal swashplate tilt equals the trim
    theta1c and the lateral swashplate tilt equals the trim theta1s.
    Returns exactly {swashplate_longitudinal_tilt_rad,
    swashplate_longitudinal_tilt_deg, swashplate_lateral_tilt_rad,
    swashplate_lateral_tilt_deg, swashplate_tilt_magnitude_rad,
    swashplate_tilt_magnitude_deg} (magnitude is the hypot of the two
    components). Same ValueErrors as trim_cyclic.
    """
    trim = trim_cyclic(mu, lam, theta0, gamma, a1s_target, b1s_target)
    long_tilt_rad = trim["lateral_cyclic_pitch_rad"]
    lat_tilt_rad = trim["longitudinal_cyclic_pitch_rad"]
    magnitude_rad = math.hypot(long_tilt_rad, lat_tilt_rad)
    return {
        "swashplate_longitudinal_tilt_rad": long_tilt_rad,
        "swashplate_longitudinal_tilt_deg": long_tilt_rad * DEG,
        "swashplate_lateral_tilt_rad": lat_tilt_rad,
        "swashplate_lateral_tilt_deg": lat_tilt_rad * DEG,
        "swashplate_tilt_magnitude_rad": magnitude_rad,
        "swashplate_tilt_magnitude_deg": magnitude_rad * DEG,
    }

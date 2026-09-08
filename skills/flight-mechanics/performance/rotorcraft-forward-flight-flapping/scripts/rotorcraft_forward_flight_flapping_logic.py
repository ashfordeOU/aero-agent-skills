"""Rotorcraft forward-flight blade flapping: first-harmonic flap equilibrium.

Pure stdlib, deterministic, no RNG. Implements the classical harmonic
balance of the flap equation of an idealized centrally hinged, untwisted,
featherless rotor blade in forward flight under uniform inflow (Johnson,
Helicopter Theory ch. 4; Leishman, Principles of Helicopter Aerodynamics
ch. 4, paraphrased). The steady, cos and sin Fourier projections of the
aerodynamic flap moment about the central hinge are equated to their
structural counterparts, giving the closed-form forward-flight coning angle
a0, the longitudinal flapping angle a1s (tip-path-plane aft tilt) and the
lateral flapping angle b1s as algebraic functions of the advance ratio mu,
the inflow ratio lambda, the collective pitch theta0 and the blade Lock
number gamma.

This is the forward-flight extension of the hover-state flap sibling
(rotorcraft-blade-flapping-dynamics): it covers only the first-harmonic
flap equilibrium in forward flight, not rotor power, lead-lag dynamics or
higher flapping harmonics.
"""

import math

# Module constants
DEG = 180.0 / math.pi  # radians to degrees conversion factor


def _validate_common(mu, lam):
    """Shared range checks for mu and lam used by every public function."""
    if not math.isfinite(mu):
        raise ValueError("mu must be finite")
    if not math.isfinite(lam):
        raise ValueError("lam must be finite")
    if mu < 0.0:
        raise ValueError("mu (advance ratio) must be non-negative")
    if mu >= 1.0:
        raise ValueError("mu (advance ratio) must be below 1.0")
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


def forward_coning_angle(mu, lam, theta0, gamma):
    """Forward-flight coning angle a0 from the steady flap-moment balance.

    a0 = (gamma / 2) * (theta0 * (1 + mu**2) / 4 - lam / 3), the mean
    (steady) Fourier projection of the flap equation, carrying the
    theta0 * mu**2 / 4 dynamic-pressure gain of forward flight over the
    hover value. Reduces exactly to the hover coning closed form
    0.5 * gamma * (theta0 / 4 - lam / 3) at mu = 0. Raises ValueError on
    any non-physical or non-finite argument.
    """
    _validate_common(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    return (gamma / 2.0) * (theta0 * (1.0 + mu ** 2) / 4.0 - lam / 3.0)


def longitudinal_flapping_angle(mu, lam, theta0):
    """Longitudinal flapping angle a1s, the tip-path-plane aft tilt.

    a1s = -4 * mu * (2 * theta0 / 3 - lam / 2) / (1 - mu**2 / 2), the
    cos(psi) Fourier projection of the flap equation nulled at 1/rev
    resonance. Takes no gamma: the Lock number cancels between the
    aerodynamic forcing and aerodynamic damping in the 1/rev balance.
    Returns exactly 0.0 at mu = 0.0 (no forward-flight asymmetry).
    Raises ValueError on any non-physical or non-finite argument.
    """
    _validate_common(mu, lam)
    _validate_theta0(theta0)
    if mu == 0.0:
        return 0.0
    return -4.0 * mu * (2.0 * theta0 / 3.0 - lam / 2.0) / (1.0 - mu ** 2 / 2.0)


def lateral_flapping_angle(mu, lam, theta0, gamma):
    """Lateral flapping angle b1s from the coning-coupling identity.

    b1s = -(4 * mu / 3) * a0 / (1 + mu**2 / 2), the sin(psi) Fourier
    projection of the flap equation, proportional to the forward-flight
    coning angle a0 through the advance-ratio coupling factor
    -(4 * mu / 3) / (1 + mu**2 / 2). Returns exactly 0.0 at mu = 0.0.
    Raises ValueError on any non-physical or non-finite argument.
    """
    _validate_common(mu, lam)
    _validate_theta0(theta0)
    _validate_gamma(gamma)
    if mu == 0.0:
        return 0.0
    a0 = forward_coning_angle(mu, lam, theta0, gamma)
    return -(4.0 * mu / 3.0) * a0 / (1.0 + mu ** 2 / 2.0)


def forward_flap_summary(mu, lam, theta0, gamma):
    """One-call first-harmonic flap equilibrium assessment dict.

    Returns {coning_angle_rad, coning_angle_deg,
    longitudinal_flapping_rad, longitudinal_flapping_deg,
    lateral_flapping_rad, lateral_flapping_deg}. Each _deg value equals
    the corresponding _rad value times DEG (180 / pi), and each
    component matches the standalone function evaluated at the same
    arguments. ValueErrors propagate from the underlying checks.
    """
    a0_rad = forward_coning_angle(mu, lam, theta0, gamma)
    a1s_rad = longitudinal_flapping_angle(mu, lam, theta0)
    b1s_rad = lateral_flapping_angle(mu, lam, theta0, gamma)
    return {
        "coning_angle_rad": a0_rad,
        "coning_angle_deg": a0_rad * DEG,
        "longitudinal_flapping_rad": a1s_rad,
        "longitudinal_flapping_deg": a1s_rad * DEG,
        "lateral_flapping_rad": b1s_rad,
        "lateral_flapping_deg": b1s_rad * DEG,
    }

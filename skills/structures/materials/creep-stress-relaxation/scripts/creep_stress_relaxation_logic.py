#!/usr/bin/env python3
"""Creep stress relaxation of a preloaded part at fixed total strain.

Common-knowledge summary (standards-map.yaml, mmpsd: MMPDS documents
creep and creep-rupture design practice for metallic airframe materials;
far-25 frames the elevated-temperature component certification context):
when an initially elastic stress sigma_0 (a bolt preload, a spring
preload or an interference-fit fastener) is held at fixed total strain
while the metal creeps at elevated temperature under the Norton power
law eps_dot = A * sigma^n * exp(-Q / (R * T)), the elastic strain
unloads one-for-one into creep strain and the stress decays by the
relaxation ODE d(sigma)/dt = -E * eps_dot = -K * sigma^n, with the
relaxation rate coefficient K = E * A * exp(-Q / (R * T)) in
Pa^(1-n) / s. The ODE integrates in closed form: for n != 1,
sigma(t) = [sigma_0^(1-n) + (n - 1) * K * t]^(1 / (1 - n)); for n = 1
(the Newtonian viscous branch, the n -> 1 limit) sigma(t) =
sigma_0 * exp(-K * t). The retained fraction f(t) = sigma(t) / sigma_0
lies in (0, 1]; inverting the closed form gives the time to relax to a
target fraction, and the preload-retention margin compares the
retained fraction with a required fraction as available / required - 1,
PASS when the margin is >= 0.

Units: stress in Pa (MPa times 1e6), temperature in K (Celsius plus
273.15), time in seconds (hold times in hours convert by 3600). All
functions raise ValueError on non-positive stress, temperature or
required fraction, on negative time, on a fraction outside (0, 1], on
a stress exponent below 1 (the closed form is a decay only for n >= 1),
or on an unknown material name. Material constants are reference-only
typicals for a representative nickel superalloy at elevated temperature
(Inconel-718 class, the same A, n and Q values the creep-rupture leaf
carries, plus the elastic modulus E the relaxation ODE needs); they are
paraphrased guidance, not a reproduced data table.
"""

import math

R_GAS = 8.314  # J/mol/K, the gas constant

# Reference-only typicals (see module docstring). Norton: A (1/s per
# Pa^n), n (stress exponent), Q (J/mol); E the high-temperature elastic
# modulus in Pa at the operating point, an input constant never derived.
MATERIALS = {
    "inconel-718": {
        "norton_a": 2.0e-47,
        "norton_n": 7.0,
        "norton_q": 360000.0,
        "elastic_modulus": 2.1e11,
    },
}

DEFAULT_MATERIAL = "inconel-718"


def _resolve(material):
    """Return the full constant dict for a material name or override dict.

    A string name must be a key of MATERIALS (ValueError otherwise,
    listing the known names). A dict is merged over the default alloy
    constants so any subset of A, n, Q and E can be overridden (dict
    keys norton_a, norton_n, norton_q, elastic_modulus).
    """
    base = dict(MATERIALS[DEFAULT_MATERIAL])
    if isinstance(material, str):
        if material not in MATERIALS:
            raise ValueError(
                "unknown material %r, known: %s" % (material, ", ".join(sorted(MATERIALS)))
            )
        base.update(MATERIALS[material])
        return base
    if isinstance(material, dict):
        base.update(material)
        return base
    raise ValueError(
        "material must be a registered name or a constant dict, got %r" % (material,)
    )


def _check_sigma0(sigma_0):
    """Reject a non-positive initial stress with the standard message."""
    if sigma_0 <= 0:
        raise ValueError("initial stress must be > 0 Pa, got %r" % (sigma_0,))


def _check_time(time_s):
    """Reject a negative hold time with the standard message."""
    if time_s < 0:
        raise ValueError("hold time must be >= 0 s, got %r" % (time_s,))


def _check_temp(temp_k):
    """Reject a non-positive temperature with the standard message."""
    if temp_k <= 0:
        raise ValueError("temperature must be > 0 K, got %r" % (temp_k,))


def _check_fraction(fraction, what):
    """Reject a retained fraction outside (0, 1] with the standard message."""
    if not (0.0 < fraction <= 1.0):
        raise ValueError("%s must be in (0, 1], got %r" % (what, fraction))


def _check_exponent(consts):
    """Reject a stress exponent below 1 (the closed form decays only for n >= 1)."""
    if consts["norton_n"] < 1.0:
        raise ValueError(
            "stress exponent must be >= 1 for the relaxation closed form, got %r"
            % (consts["norton_n"],)
        )


def _relaxation_coefficient(consts, temp_k):
    """Relaxation rate coefficient K = E * A * exp(-Q / (R * T)), Pa^(1-n) / s."""
    return (
        consts["elastic_modulus"]
        * consts["norton_a"]
        * math.exp(-consts["norton_q"] / (R_GAS * temp_k))
    )


def _validate_relaxation(sigma_0, time_s, temp_k, material):
    """Shared non-physical-input rejection for the stress/retention functions.

    Returns the resolved constants and the relaxation coefficient K.
    """
    _check_sigma0(sigma_0)
    _check_time(time_s)
    _check_temp(temp_k)
    consts = _resolve(material)
    _check_exponent(consts)
    k_coeff = _relaxation_coefficient(consts, temp_k)
    return consts, k_coeff


def relaxed_stress(sigma_0, time_s, temp_k, material=DEFAULT_MATERIAL):
    """Relaxed stress in Pa after time_s of fixed-total-strain relaxation.

    Closed form of d(sigma)/dt = -K * sigma^n at constant total strain:
    sigma(t) = [sigma_0^(1-n) + (n - 1) * K * t]^(1 / (1 - n)) for
    n != 1, sigma(t) = sigma_0 * exp(-K * t) for n = 1, with K =
    E * A * exp(-Q / (R * T)). Accepts time_s = 0 and returns sigma_0
    exactly. Raises ValueError on non-positive sigma_0 or temp_k,
    negative time_s, a stress exponent below 1, or an unknown material.
    """
    consts, k_coeff = _validate_relaxation(sigma_0, time_s, temp_k, material)
    n = consts["norton_n"]
    if n == 1.0:
        return sigma_0 * math.exp(-k_coeff * time_s)
    base = sigma_0 ** (1.0 - n) + (n - 1.0) * k_coeff * time_s
    return base ** (1.0 / (1.0 - n))


def retained_fraction(sigma_0, time_s, temp_k, material=DEFAULT_MATERIAL):
    """Retained-preload fraction sigma(t) / sigma_0 in (0, 1].

    Accepts time_s = 0 and returns 1.0 exactly. Same ValueErrors as
    relaxed_stress.
    """
    consts, k_coeff = _validate_relaxation(sigma_0, time_s, temp_k, material)
    n = consts["norton_n"]
    if n == 1.0:
        return math.exp(-k_coeff * time_s)
    base = sigma_0 ** (1.0 - n) + (n - 1.0) * k_coeff * time_s
    return (base ** (1.0 / (1.0 - n))) / sigma_0


def time_to_relaxed_fraction(fraction, sigma_0, temp_k, material=DEFAULT_MATERIAL):
    """Seconds for the stress to decay to `fraction` of sigma_0.

    Inverts the closed form: t(f) = sigma_0^(1-n) * (f^(1-n) - 1) /
    ((n - 1) * K) for n != 1 and t(f) = -ln(f) / K for n = 1. Smaller
    fractions need longer times. Raises ValueError on fraction outside
    (0, 1], non-positive sigma_0 or temp_k, a stress exponent below 1,
    or an unknown material.
    """
    _check_fraction(fraction, "retained fraction")
    _check_sigma0(sigma_0)
    _check_temp(temp_k)
    consts = _resolve(material)
    _check_exponent(consts)
    k_coeff = _relaxation_coefficient(consts, temp_k)
    n = consts["norton_n"]
    if n == 1.0:
        return -math.log(fraction) / k_coeff
    return sigma_0 ** (1.0 - n) * (fraction ** (1.0 - n) - 1.0) / ((n - 1.0) * k_coeff)


def preload_margin(sigma_0, time_s, temp_k, required_fraction, material=DEFAULT_MATERIAL):
    """Retained-preload margin check dict after the hold time.

    Returns {"retained_fraction", "margin", "verdict"}: the retained
    fraction at the hold, the margin retained / required - 1, and
    "PASS" when the margin is >= 0 else "FAIL". Raises ValueError on
    required_fraction outside (0, 1] and the same rejections as
    retained_fraction.
    """
    _check_fraction(required_fraction, "required fraction")
    retained = retained_fraction(sigma_0, time_s, temp_k, material)
    margin = retained / required_fraction - 1.0
    return {
        "retained_fraction": retained,
        "margin": margin,
        "verdict": "PASS" if margin >= 0.0 else "FAIL",
    }

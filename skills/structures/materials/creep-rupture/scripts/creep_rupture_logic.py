#!/usr/bin/env python3
"""Creep and stress rupture logic (common engineering methodology).

Common-knowledge summary (standards-map.yaml, mmpsd: MMPDS documents the
creep and creep-rupture design practice for metallic airframe materials;
far-25 frames the elevated-temperature component certification context):
the steady-state creep strain rate of a metallic material follows the
Norton power law eps_dot_c = A * sigma^n * exp(-Q / (R * T)), where A is
the creep constant (1/s per Pa^n), n the stress exponent, Q the
activation energy (J/mol), R = 8.314 J/mol/K the gas constant and T the
absolute temperature (K). The rupture life is correlated through the
Larson-Miller parameter LMP = T * (C + log10(t_r)) with t_r in hours and
C a material constant (about 20); the stress-LMP master curve is taken
linear in log10(stress): LMP = lm_a - lm_b * log10(sigma_pa / 1e6). The
Monkman-Grant relation log10(t_r) + m * log10(eps_dot) = C_mg links the
minimum creep rate to the rupture life. Under steady-state creep the
strain accumulated over a service time is eps_c = eps_dot_c * t, and the
time to a target creep strain (for example 1 percent) is target /
eps_dot_c. Design checks compare the time to 1 percent creep strain and
the rupture life with the required life through the margins
margin = t_available / t_required - 1; the lower margin governs.

Units: stress in Pa, temperature in K, time in seconds (rupture lives
are reported in hours where noted), strain dimensionless. All functions
raise ValueError on non-physical inputs (non-positive stress,
temperature, time, target strain, creep rate, negative stress exponent,
unknown material name). Material constants are reference-only typicals
for a representative nickel superalloy at elevated temperature
(Inconel 718 class), internally consistent for design-exercise numbers;
they are paraphrased guidance, not a reproduced data table.
"""

import math

R_GAS = 8.314  # J/mol/K

# Reference-only typicals (see module docstring). Norton: A (1/s per
# Pa^n), n (stress exponent), Q (J/mol). Larson-Miller master curve:
# LMP = lm_a - lm_b * log10(sigma_pa / 1e6), lm_c the material constant
# C in LMP = T * (C + log10(t_r_h)). Monkman-Grant: log10(t_r_h) +
# mg_m * log10(eps_dot_per_hour) = mg_c with the creep rate converted
# to per hour.
MATERIALS = {
    "inconel-718": {
        "norton_a": 2.0e-47,
        "norton_n": 7.0,
        "norton_q": 360000.0,
        "lm_a": 35552.0,
        "lm_b": 6000.0,
        "lm_c": 20.0,
        "mg_m": 1.0,
        "mg_c": -1.645,
    },
}

DEFAULT_MATERIAL = "inconel-718"


def _resolve(material):
    """Return the full constant dict for a material name or override dict.

    A string name must be a key of MATERIALS (ValueError otherwise). A
    dict is merged over the default alloy constants so the user can
    override any subset of A, n, Q and the LMP/MG constants.
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
    raise ValueError("material must be a registered name or a constant dict, got %r" % (material,))


def _check_stress(sigma):
    if sigma <= 0:
        raise ValueError("stress must be > 0 Pa, got %r" % (sigma,))


def _check_temp(temp_k):
    if temp_k <= 0:
        raise ValueError("temperature must be > 0 K, got %r" % (temp_k,))


def norton_creep_rate(sigma, temp_k, material=DEFAULT_MATERIAL):
    """Steady-state creep strain rate eps_dot = A * sigma^n * exp(-Q/(R*T)).

    Stress in Pa, temperature in K; returns the rate in 1/s. Raises
    ValueError on non-positive stress or temperature, a negative stress
    exponent, or an unknown material.
    """
    _check_stress(sigma)
    _check_temp(temp_k)
    consts = _resolve(material)
    if consts["norton_n"] < 0:
        raise ValueError("stress exponent n must be >= 0, got %r" % (consts["norton_n"],))
    return (
        consts["norton_a"]
        * sigma ** consts["norton_n"]
        * math.exp(-consts["norton_q"] / (R_GAS * temp_k))
    )


def larson_miller_parameter(sigma, material=DEFAULT_MATERIAL):
    """Larson-Miller parameter LMP = lm_a - lm_b * log10(sigma_pa / 1e6).

    Stress in Pa, stress expressed in MPa inside the master curve;
    returns LMP in K (temperature times the log10 hours term). Raises
    ValueError on non-positive stress or an unknown material.
    """
    _check_stress(sigma)
    consts = _resolve(material)
    return consts["lm_a"] - consts["lm_b"] * math.log10(sigma / 1e6)


def rupture_life_from_lmp(lmp, temp_k, c_const):
    """Rupture life t_r = 10^(LMP / T - C) from the Larson-Miller equation.

    lmp in K, temperature in K, c_const the material constant C (about
    20); returns the rupture life in hours. Raises ValueError on
    non-positive temperature or c_const.
    """
    _check_temp(temp_k)
    if c_const <= 0:
        raise ValueError("Larson-Miller constant C must be > 0, got %r" % (c_const,))
    log10_tr = lmp / temp_k - c_const
    return 10.0 ** log10_tr


def rupture_life_hours(sigma, temp_k, material=DEFAULT_MATERIAL):
    """Rupture life in hours from the stress-LMP master curve and LMP.

    LMP = larson_miller_parameter(sigma, material), then t_r =
    rupture_life_from_lmp(LMP, temp_k, lm_c). Raises ValueError on
    non-physical inputs or an unknown material.
    """
    consts = _resolve(material)
    lmp = larson_miller_parameter(sigma, material)
    return rupture_life_from_lmp(lmp, temp_k, consts["lm_c"])


def monkman_grant_life(eps_dot_min, material=DEFAULT_MATERIAL):
    """Rupture life in hours from the Monkman-Grant relation.

    log10(t_r_h) + m * log10(eps_dot_per_hour) = C_mg, with the minimum
    creep rate given in 1/s and converted to per hour internally.
    Returns t_r in hours. Raises ValueError on a non-positive creep
    rate, a negative exponent m, or an unknown material.
    """
    if eps_dot_min <= 0:
        raise ValueError("minimum creep rate must be > 0 1/s, got %r" % (eps_dot_min,))
    consts = _resolve(material)
    if consts["mg_m"] < 0:
        raise ValueError("Monkman-Grant exponent m must be >= 0, got %r" % (consts["mg_m"],))
    eps_dot_per_hour = eps_dot_min * 3600.0
    log10_tr = consts["mg_c"] - consts["mg_m"] * math.log10(eps_dot_per_hour)
    return 10.0 ** log10_tr


def creep_strain_accumulated(eps_dot, time_s):
    """Accumulated creep strain eps_c = eps_dot * t (steady-state only).

    Returns the dimensionless strain over the service time. Raises
    ValueError on a non-positive creep rate or negative time.
    """
    if eps_dot <= 0:
        raise ValueError("creep rate must be > 0 1/s, got %r" % (eps_dot,))
    if time_s < 0:
        raise ValueError("service time must be >= 0 s, got %r" % (time_s,))
    return eps_dot * time_s


def time_to_creep_strain(target_strain, eps_dot):
    """Time in seconds to reach a target creep strain: target / eps_dot.

    Raises ValueError on a non-positive target strain or creep rate.
    """
    if target_strain <= 0:
        raise ValueError("target strain must be > 0, got %r" % (target_strain,))
    if eps_dot <= 0:
        raise ValueError("creep rate must be > 0 1/s, got %r" % (eps_dot,))
    return target_strain / eps_dot


def creep_margin(time_required_s, sigma, temp_k, material=DEFAULT_MATERIAL):
    """Design check dict for a required life at the operating point.

    Computes the rupture life at (sigma, temp_k), the time to 1 percent
    creep strain t_1pct = 0.01 / eps_dot, the two margins
    margin = t_available / t_required - 1, and the verdict. The lower
    margin governs (time to 1 percent creep strain or rupture life,
    whichever is reached first). Returns a dict with keys
    rupture_life_h, time_to_1pct_h, margin_rupture, margin_creep,
    governing ('rupture' or 'creep') and verdict ('PASS' when the
    governing margin is >= 0, else 'FAIL'). Raises ValueError on a
    non-positive required time, stress or temperature, or an unknown
    material.
    """
    if time_required_s <= 0:
        raise ValueError("required life must be > 0 s, got %r" % (time_required_s,))
    eps_dot = norton_creep_rate(sigma, temp_k, material)
    t_1pct_s = time_to_creep_strain(0.01, eps_dot)
    rupture_h = rupture_life_hours(sigma, temp_k, material)
    rupture_s = rupture_h * 3600.0
    margin_rupture = rupture_s / time_required_s - 1.0
    margin_creep = t_1pct_s / time_required_s - 1.0
    if margin_creep <= margin_rupture:
        governing = "creep"
        governing_margin = margin_creep
    else:
        governing = "rupture"
        governing_margin = margin_rupture
    return {
        "rupture_life_h": rupture_h,
        "time_to_1pct_h": t_1pct_s / 3600.0,
        "margin_rupture": margin_rupture,
        "margin_creep": margin_creep,
        "governing": governing,
        "governing_margin": governing_margin,
        "verdict": "PASS" if governing_margin >= 0.0 else "FAIL",
    }

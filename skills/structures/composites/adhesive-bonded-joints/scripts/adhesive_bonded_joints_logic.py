"""Adhesive bonded single-lap joint analysis, Volkersen-style shear lag.

Pure stdlib logic for the AeroSkills leaf
structures/composites/adhesive-bonded-joints. For a single-lap joint
between two identical adherends it computes the shear-lag parameter,
the average and peak adhesive shear stresses, the peak to average
stress concentration, and the joint margin against the adhesive
allowable shear stress.

SI units throughout: load in N, lengths in m, moduli and stresses in
Pa. All functions raise ValueError on non-physical inputs.
"""

import math

# Identical-adherend simplification of the Volkersen sum 1/(E1*t1) +
# 1/(E2*t2) for E1 = E2 = E and t1 = t2 = t: the 2.0 factor below.
_IDENTICAL_ADHEREND_FACTOR = 2.0


def _check_positive(value, name):
    if value <= 0.0:
        raise ValueError("%s must be positive" % name)


def shear_lag_beta(adherend_E_pa, adherend_t_m, adhesive_G_pa, adhesive_t_m):
    """Return the Volkersen shear-lag parameter beta in 1/m.

    beta = sqrt((G_a / t_a) * (2.0 / (E * t))) with E the adherend
    modulus, t the adherend thickness, G_a the adhesive shear modulus
    and t_a the adhesive thickness.
    """
    _check_positive(adherend_E_pa, "adherend modulus")
    _check_positive(adherend_t_m, "adherend thickness")
    _check_positive(adhesive_G_pa, "adhesive shear modulus")
    _check_positive(adhesive_t_m, "adhesive thickness")
    compliance = _IDENTICAL_ADHEREND_FACTOR / (adherend_E_pa * adherend_t_m)
    return math.sqrt((adhesive_G_pa / adhesive_t_m) * compliance)


def avg_shear_stress(load_n, width_m, overlap_m):
    """Return the average adhesive shear stress tau_avg = P / (b * L)."""
    if load_n < 0.0:
        raise ValueError("load must not be negative")
    _check_positive(width_m, "bond width")
    _check_positive(overlap_m, "overlap length")
    return load_n / (width_m * overlap_m)


def concentration_factor(beta, overlap_m):
    """Return the peak to average shear concentration factor.

    factor = (beta * L / 2) / tanh(beta * L / 2), which tends to 1 for
    a uniform shear distribution (beta * L small) and grows with
    beta * L.
    """
    _check_positive(beta, "shear-lag parameter")
    _check_positive(overlap_m, "overlap length")
    half_arg = beta * overlap_m / 2.0
    if half_arg < 1.0e-9:
        return 1.0
    return half_arg / math.tanh(half_arg)


def peak_shear_stress(load_n, width_m, overlap_m, beta):
    """Return the peak adhesive shear stress at the overlap ends.

    tau_max = tau_avg * (beta * L / 2) / tanh(beta * L / 2).
    """
    if load_n < 0.0:
        raise ValueError("load must not be negative")
    _check_positive(width_m, "bond width")
    _check_positive(overlap_m, "overlap length")
    _check_positive(beta, "shear-lag parameter")
    tau_avg = load_n / (width_m * overlap_m)
    return tau_avg * concentration_factor(beta, overlap_m)


def joint_margin(allowable_shear_pa, peak_shear_pa):
    """Return the margin ratio allowable / peak for the bondline.

    The MS-style margin of safety is the ratio minus one; callers that
    need it subtract 1.0 or read margin_ms from analyze().
    """
    _check_positive(allowable_shear_pa, "adhesive allowable shear stress")
    _check_positive(peak_shear_pa, "peak shear stress")
    return allowable_shear_pa / peak_shear_pa


def analyze(load_n, width_m, overlap_m, adherend_E_pa, adherend_t_m,
            adhesive_G_pa, adhesive_t_m, allowable_shear_pa):
    """Return the full single-lap adhesive joint analysis dict.

    Keys: beta, tau_avg, tau_max, concentration, margin_ratio,
    margin_ms and pass (True when peak shear does not exceed the
    adhesive allowable).
    """
    _check_positive(allowable_shear_pa, "adhesive allowable shear stress")
    beta = shear_lag_beta(adherend_E_pa, adherend_t_m,
                          adhesive_G_pa, adhesive_t_m)
    tau_avg = avg_shear_stress(load_n, width_m, overlap_m)
    tau_max = peak_shear_stress(load_n, width_m, overlap_m, beta)
    concentration = concentration_factor(beta, overlap_m)
    if tau_max > 0.0:
        margin_ratio = joint_margin(allowable_shear_pa, tau_max)
    else:
        margin_ratio = float("inf")
    return {
        "beta": beta,
        "tau_avg": tau_avg,
        "tau_max": tau_max,
        "concentration": concentration,
        "margin_ratio": margin_ratio,
        "margin_ms": margin_ratio - 1.0,
        "pass": tau_max <= allowable_shear_pa,
    }

"""Strain-life (low-cycle fatigue) analysis for aerospace structures.

Coffin-Manson total strain amplitude versus reversals to failure,
life inversion by bisection on log(2N_f), transition life and regime
categorization, the Ramberg-Osgood cyclic curve, and the Neuber
local-strain rule that bridges a nominal elastic stress to the local
elastic-plastic strain at a notch. Pure stdlib, deterministic.

Material tables hold representative cyclic property typicals,
reference-only (paraphrase of open fatigue literature magnitudes, not
a reproduced MMPDS or standards table). The default material is a
7075-T6 class aluminum; pass a material name key or a full property
dict to use your own Coffin-Manson and Ramberg-Osgood constants.
"""

import math

# Coffin-Manson: eps_a = (sigma_f_prime/E)*(2N_f)^b + eps_f_prime*(2N_f)^c
# Ramberg-Osgood cyclic: eps = sigma/E + (sigma/K_prime)^(1/n_prime)
MATERIALS = {
    "7075-t6-aluminum": {
        "label": "Aluminum 7075-T6 class (representative typical, reference-only)",
        "sigma_f_prime": 690.0e6,   # Pa, fatigue strength coefficient
        "b": -0.10,                 # fatigue strength exponent
        "eps_f_prime": 0.55,        # fatigue ductility coefficient
        "c": -0.60,                 # fatigue ductility exponent
        "E": 71.7e9,                # Pa, elastic modulus
        "K_prime": 900.0e6,         # Pa, cyclic strength coefficient
        "n_prime": 0.10,            # cyclic strain hardening exponent
    },
    "4340-steel": {
        "label": "Aerospace steel 4340 class (representative typical, reference-only)",
        "sigma_f_prime": 1750.0e6,  # Pa
        "b": -0.08,
        "eps_f_prime": 0.50,
        "c": -0.70,
        "E": 200.0e9,               # Pa
        "K_prime": 1800.0e6,        # Pa
        "n_prime": 0.08,
    },
}
DEFAULT_MATERIAL = "7075-t6-aluminum"

_PROP_KEYS = ("sigma_f_prime", "b", "eps_f_prime", "c", "E", "K_prime", "n_prime")


def _validate_props(props, material_name):
    """ValueError unless every physical property is finite and in range."""
    for key in ("sigma_f_prime", "E", "K_prime"):
        if not math.isfinite(props[key]) or props[key] <= 0.0:
            raise ValueError("non-positive or non-finite " + key)
    for key in ("b", "c"):
        if not math.isfinite(props[key]) or props[key] >= 0.0:
            raise ValueError("fatigue exponent " + key + " must be negative")
    if not math.isfinite(props["eps_f_prime"]) or props["eps_f_prime"] <= 0.0:
        raise ValueError("non-positive or non-finite eps_f_prime")
    if not (0.0 < props["n_prime"] < 1.0):
        raise ValueError("n_prime must lie in (0, 1)")
    if material_name is not None:
        props["label"] = material_name
    return props


def material_properties(material=DEFAULT_MATERIAL):
    """Resolve a material name key or a property dict to a full property set.

    A dict input may carry the seven keys sigma_f_prime, b, eps_f_prime,
    c, E, K_prime, n_prime; missing keys fall back to the default
    aluminum table values.
    """
    if isinstance(material, dict):
        base = dict(MATERIALS[DEFAULT_MATERIAL])
        base.update({k: v for k, v in material.items() if k in _PROP_KEYS})
        missing = [k for k in _PROP_KEYS if k not in base]
        if missing:
            raise ValueError("material dict missing keys: " + ", ".join(missing))
        return _validate_props(base, base.get("label"))
    if not isinstance(material, str):
        raise ValueError("material must be a name key or a property dict")
    if material not in MATERIALS:
        raise ValueError("unknown material: " + material)
    return _validate_props(dict(MATERIALS[material]), MATERIALS[material]["label"])


def _positive_finite(x, name):
    if not math.isfinite(x) or x <= 0.0:
        raise ValueError("non-positive or non-finite " + name)
    return x


def strain_amplitude(n_reversals, material=DEFAULT_MATERIAL):
    """Total strain amplitude eps_a at n_reversals (2N_f > 0) by Coffin-Manson."""
    n_rev = _positive_finite(n_reversals, "n_reversals")
    props = material_properties(material)
    elastic = (props["sigma_f_prime"] / props["E"]) * n_rev ** props["b"]
    plastic = props["eps_f_prime"] * n_rev ** props["c"]
    return elastic + plastic


def _life_bisection(eps_a, props, lo_exp, hi_exp):
    """Deterministic bisection on log(2N_f); returns 2N_f float."""
    def resid(lg):
        n_rev = 2.0 ** lg
        amp = ((props["sigma_f_prime"] / props["E"]) * n_rev ** props["b"]
               + props["eps_f_prime"] * n_rev ** props["c"])
        return amp - eps_a
    lo, hi = lo_exp, hi_exp
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if resid(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 2.0 ** (0.5 * (lo + hi))


def reversals_to_failure(eps_a, material=DEFAULT_MATERIAL):
    """Reversals to failure 2N_f for a fully reversed strain amplitude eps_a."""
    eps = _positive_finite(eps_a, "eps_a")
    props = material_properties(material)
    return _life_bisection(eps, props, -40.0, 45.0)


def transition_reversals(material=DEFAULT_MATERIAL):
    """Reversals 2N_t where the elastic and plastic amplitude terms are equal."""
    props = material_properties(material)

    def resid(lg):
        n_rev = 2.0 ** lg
        elastic = (props["sigma_f_prime"] / props["E"]) * n_rev ** props["b"]
        plastic = props["eps_f_prime"] * n_rev ** props["c"]
        return elastic - plastic
    lo, hi = -40.0, 45.0
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if resid(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 2.0 ** (0.5 * (lo + hi))


def regime_classification(eps_a, material=DEFAULT_MATERIAL):
    """Categorize a strain amplitude: 'low-cycle' below 2N_t, else 'high-cycle'."""
    eps = _positive_finite(eps_a, "eps_a")
    props = material_properties(material)
    life = _life_bisection(eps, props, -40.0, 45.0)
    n_trans = transition_reversals(material)
    if life < n_trans:
        return "low-cycle"
    return "high-cycle"


def ramberg_osgood(sigma, e, k_prime, n_prime):
    """Cyclic total strain eps = sigma/e + (sigma/k_prime)^(1/n_prime)."""
    s = _positive_finite(sigma, "sigma")
    e_mod = _positive_finite(e, "e")
    k = _positive_finite(k_prime, "k_prime")
    if not math.isfinite(n_prime) or not (0.0 < n_prime < 1.0):
        raise ValueError("n_prime must lie in (0, 1)")
    return s / e_mod + (s / k) ** (1.0 / n_prime)


def neuber_local_strain(k_f, s_nominal, material=DEFAULT_MATERIAL):
    """Local notch stress and strain from the Neuber rule.

    Solves sigma_loc * eps_loc = (k_f * S)^2 / E with eps_loc from the
    cyclic Ramberg-Osgood curve by deterministic bisection on sigma_loc.
    Returns (sigma_loc, eps_loc, plastic_flag); plastic_flag is True
    when the plastic strain exceeds a tiny relative tolerance.
    """
    kf = float(k_f)
    if not math.isfinite(kf) or kf < 1.0:
        raise ValueError("k_f must be finite and >= 1")
    s_nom = _positive_finite(s_nominal, "s_nominal")
    props = material_properties(material)
    target = (kf * s_nom) ** 2 / props["E"]

    def resid(sigma):
        eps = ramberg_osgood(sigma, props["E"], props["K_prime"],
                             props["n_prime"])
        return sigma * eps - target

    lo, hi = 1.0e-6 * kf * s_nom, max(2.0 * kf * s_nom, 1.0e12)
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if resid(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    sigma_loc = 0.5 * (lo + hi)
    eps_loc = ramberg_osgood(sigma_loc, props["E"], props["K_prime"],
                             props["n_prime"])
    plastic = eps_loc - sigma_loc / props["E"]
    plastic_flag = plastic > 1.0e-8 * eps_loc
    return sigma_loc, eps_loc, plastic_flag


def strain_life_point(s_nominal, k_f, material=DEFAULT_MATERIAL):
    """Full strain-life verdict for a notched load point.

    Applies the Neuber rule to the nominal elastic stress amplitude and
    reads the local strain amplitude back through the Coffin-Manson
    curve for the fully reversed life (mean stress zero by assumption).
    """
    s_nom = _positive_finite(s_nominal, "s_nominal")
    kf = float(k_f)
    if not math.isfinite(kf) or kf < 1.0:
        raise ValueError("k_f must be finite and >= 1")
    sigma_loc, eps_loc, plastic_flag = neuber_local_strain(kf, s_nom, material)
    n_rev = reversals_to_failure(eps_loc, material)
    n_trans = transition_reversals(material)
    regime = "low-cycle" if n_rev < n_trans else "high-cycle"
    verdict = ("low-cycle plastic-dominated fatigue life" if regime == "low-cycle"
               else "high-cycle elastic-dominated fatigue life")
    return {
        "sigma_loc": sigma_loc,
        "eps_loc": eps_loc,
        "plastic_flag": plastic_flag,
        "reversals_to_failure": n_rev,
        "cycles_to_failure": n_rev / 2.0,
        "regime": regime,
        "verdict": verdict,
    }

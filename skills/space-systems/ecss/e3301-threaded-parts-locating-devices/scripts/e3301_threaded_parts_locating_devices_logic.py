"""Threaded parts and locating devices: materials, preload and locking.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.4.10 (threaded parts and locating
devices made from materials with high resistance to stress-corrosion cracking,
tightened under a controlled method to a known preload, and positively locked).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Screen the fastener material against the stress-corrosion resistance
   category the clause expects, allowing a lower category only where a
   justification is on record.
2. Subtract the prevailing torque of the locking feature from the applied
   torque before any preload is derived; prevailing torque stretches nothing.
3. Convert the effective torque band, widened by the torque-wrench tolerance
   and by the nut-factor spread, into a minimum and maximum installed preload.
4. Take the short-term and long-term preload losses -- embedment and thermal
   relaxation -- off the minimum preload to get the residual preload the joint
   actually flies with.
5. Compute the joint margins: gapping against the factored external tensile
   load through the joint stiffness ratio, friction slip against the factored
   shear load, and fastener yield at the maximum installed preload plus its
   share of the external load.
6. Confirm a positive locking feature is present and is one the clause allows.
"""

import math

__all__ = [
    "REQUIRED_SCC_CATEGORY",
    "SCC_CATEGORY_ORDER",
    "DEFAULT_EMBEDMENT_FRACTION",
    "DEFAULT_THERMAL_RELAXATION_FRACTION",
    "MARGIN_TOLERANCE",
    "FASTENER_MATERIALS",
    "LOCKING_FEATURES",
    "validate_positive",
    "fastener_material",
    "locking_feature",
    "tensile_stress_area_mm2",
    "effective_torque_nm",
    "preload_from_torque_n",
    "preload_band_n",
    "preload_losses_n",
    "residual_preload_n",
    "gapping_margin",
    "slip_margin",
    "yield_margin",
    "assess_threaded_part",
]

# Category I is the high stress-corrosion resistance the clause expects.
REQUIRED_SCC_CATEGORY = "I"
SCC_CATEGORY_ORDER = ("I", "II", "III")

# Preload losses taken as a fraction of the installed preload when the joint
# does not declare measured values.
DEFAULT_EMBEDMENT_FRACTION = 0.05
DEFAULT_THERMAL_RELAXATION_FRACTION = 0.03

# Margins are differences of ratios; absorb the representation error at zero.
MARGIN_TOLERANCE = 1e-9

# Fastener stock: stress-corrosion category, yield and ultimate strength.
FASTENER_MATERIALS = {
    "a286": {"scc_category": "I", "yield_mpa": 660.0, "ultimate_mpa": 965.0},
    "inconel-718": {"scc_category": "I", "yield_mpa": 1030.0, "ultimate_mpa": 1275.0},
    "ti-6al-4v": {"scc_category": "I", "yield_mpa": 830.0, "ultimate_mpa": 900.0},
    "aisi-316": {"scc_category": "I", "yield_mpa": 205.0, "ultimate_mpa": 515.0},
    "aisi-410": {"scc_category": "III", "yield_mpa": 620.0, "ultimate_mpa": 800.0},
    "aluminium-7075-t6": {"scc_category": "III", "yield_mpa": 470.0, "ultimate_mpa": 540.0},
    "aluminium-7075-t73": {"scc_category": "II", "yield_mpa": 400.0, "ultimate_mpa": 480.0},
}

# Locking features and the prevailing torque each contributes by default.
LOCKING_FEATURES = {
    "prevailing-torque-nut": {"prevailing_torque_nm": 0.4, "positive": True},
    "locking-helicoil": {"prevailing_torque_nm": 0.3, "positive": True},
    "lockwire": {"prevailing_torque_nm": 0.0, "positive": True},
    "adhesive-threadlocker": {"prevailing_torque_nm": 0.0, "positive": True},
    "staking": {"prevailing_torque_nm": 0.0, "positive": True},
    "spring-washer": {"prevailing_torque_nm": 0.0, "positive": False},
    "none": {"prevailing_torque_nm": 0.0, "positive": False},
}


def validate_positive(label, value, allow_zero=False):
    """Return value as a finite positive (or non-negative) float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %g" % (label, v))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _validate_fraction(label, value):
    v = validate_positive(label, value, allow_zero=True)
    if v >= 1.0:
        raise ValueError("%s must be below 1, got %g" % (label, v))
    return v


def fastener_material(name):
    """Return the property record of a known fastener material."""
    if not isinstance(name, str):
        raise ValueError("fastener material must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in FASTENER_MATERIALS:
        raise ValueError(
            "unknown fastener material %r; known: %s"
            % (name, ", ".join(sorted(FASTENER_MATERIALS)))
        )
    return dict(FASTENER_MATERIALS[key])


def locking_feature(name):
    """Return the property record of a known locking feature."""
    if not isinstance(name, str):
        raise ValueError("locking feature must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in LOCKING_FEATURES:
        raise ValueError(
            "unknown locking feature %r; known: %s"
            % (name, ", ".join(sorted(LOCKING_FEATURES)))
        )
    return dict(LOCKING_FEATURES[key])


def tensile_stress_area_mm2(nominal_diameter_mm, pitch_mm):
    """Tensile stress area of an ISO metric thread, in square millimetres."""
    d = validate_positive("nominal_diameter_mm", nominal_diameter_mm)
    p = validate_positive("pitch_mm", pitch_mm)
    if p >= d:
        raise ValueError("pitch_mm %g must be smaller than the diameter %g" % (p, d))
    effective = d - 0.9382 * p
    return math.pi * 0.25 * effective * effective


def effective_torque_nm(applied_torque_nm, prevailing_torque_nm):
    """Applied torque less the prevailing torque of the locking feature."""
    applied = validate_positive("applied_torque_nm", applied_torque_nm)
    prevailing = validate_positive(
        "prevailing_torque_nm", prevailing_torque_nm, allow_zero=True
    )
    if prevailing >= applied:
        raise ValueError(
            "prevailing torque %g Nm leaves no torque to stretch the fastener at %g Nm"
            % (prevailing, applied)
        )
    return applied - prevailing


def preload_from_torque_n(torque_nm, nominal_diameter_mm, nut_factor):
    """Installed preload from the short-form torque relation, in newtons."""
    torque = validate_positive("torque_nm", torque_nm)
    d = validate_positive("nominal_diameter_mm", nominal_diameter_mm)
    k = validate_positive("nut_factor", nut_factor)
    if k >= 1.0:
        raise ValueError("nut_factor must be below 1, got %g" % k)
    return 1000.0 * torque / (k * d)


def preload_band_n(applied_torque_nm, torque_tolerance_fraction, nominal_diameter_mm,
                   nut_factor_min, nut_factor_max, prevailing_torque_nm=0.0):
    """Return the (min, max) installed preload over torque and friction spread."""
    tolerance = _validate_fraction("torque_tolerance_fraction", torque_tolerance_fraction)
    k_min = validate_positive("nut_factor_min", nut_factor_min)
    k_max = validate_positive("nut_factor_max", nut_factor_max)
    if k_min > k_max:
        raise ValueError("nut_factor_min %g exceeds nut_factor_max %g" % (k_min, k_max))
    applied = validate_positive("applied_torque_nm", applied_torque_nm)
    low_torque = effective_torque_nm(applied * (1.0 - tolerance), prevailing_torque_nm)
    high_torque = effective_torque_nm(applied * (1.0 + tolerance), prevailing_torque_nm)
    return (
        preload_from_torque_n(low_torque, nominal_diameter_mm, k_max),
        preload_from_torque_n(high_torque, nominal_diameter_mm, k_min),
    )


def preload_losses_n(preload_n, embedment_fraction=DEFAULT_EMBEDMENT_FRACTION,
                     thermal_relaxation_fraction=DEFAULT_THERMAL_RELAXATION_FRACTION):
    """Short-term and long-term preload loss, in newtons."""
    preload = validate_positive("preload_n", preload_n)
    embedment = _validate_fraction("embedment_fraction", embedment_fraction)
    thermal = _validate_fraction(
        "thermal_relaxation_fraction", thermal_relaxation_fraction
    )
    if embedment + thermal >= 1.0:
        raise ValueError(
            "declared losses of %g consume the whole preload" % (embedment + thermal)
        )
    return preload * (embedment + thermal)


def residual_preload_n(preload_min_n, losses_n):
    """Preload remaining after the declared losses, in newtons."""
    preload = validate_positive("preload_min_n", preload_min_n)
    losses = validate_positive("losses_n", losses_n, allow_zero=True)
    if losses >= preload:
        raise ValueError(
            "losses of %g N consume the %g N minimum preload" % (losses, preload)
        )
    return preload - losses


def gapping_margin(residual_preload_n_value, external_tensile_load_n, load_factor,
                   stiffness_ratio):
    """Margin of safety against joint gapping under the factored tensile load."""
    residual = validate_positive("residual_preload_n", residual_preload_n_value)
    external = validate_positive(
        "external_tensile_load_n", external_tensile_load_n, allow_zero=True
    )
    factor = validate_positive("load_factor", load_factor)
    phi = _validate_fraction("stiffness_ratio", stiffness_ratio)
    if external == 0.0:
        return float("inf")
    separation_load = residual / (1.0 - phi)
    return separation_load / (external * factor) - 1.0


def slip_margin(residual_preload_n_value, friction_coefficient, shear_load_n,
                load_factor, interfaces=1):
    """Margin of safety against friction slip under the factored shear load."""
    residual = validate_positive("residual_preload_n", residual_preload_n_value)
    mu = validate_positive("friction_coefficient", friction_coefficient)
    shear = validate_positive("shear_load_n", shear_load_n, allow_zero=True)
    factor = validate_positive("load_factor", load_factor)
    if not isinstance(interfaces, int) or isinstance(interfaces, bool):
        raise ValueError("interfaces must be an integer, got %r" % (interfaces,))
    if interfaces < 1:
        raise ValueError("interfaces must be at least 1, got %d" % interfaces)
    if shear == 0.0:
        return float("inf")
    return mu * interfaces * residual / (shear * factor) - 1.0


def yield_margin(preload_max_n, external_tensile_load_n, load_factor, stiffness_ratio,
                 stress_area_mm2, yield_strength_mpa):
    """Margin of safety on fastener yield at the maximum installed preload."""
    preload = validate_positive("preload_max_n", preload_max_n)
    external = validate_positive(
        "external_tensile_load_n", external_tensile_load_n, allow_zero=True
    )
    factor = validate_positive("load_factor", load_factor)
    phi = _validate_fraction("stiffness_ratio", stiffness_ratio)
    area = validate_positive("stress_area_mm2", stress_area_mm2)
    strength = validate_positive("yield_strength_mpa", yield_strength_mpa)
    bolt_load = preload + phi * external * factor
    return strength * area / bolt_load - 1.0


def assess_threaded_part(spec):
    """Run the full clause 4.7.5.4.10 threaded-part assessment.

    spec keys: material, nominal_diameter_mm, pitch_mm, applied_torque_nm,
    torque_tolerance_fraction, nut_factor_min, nut_factor_max, locking,
    external_tensile_load_n, shear_load_n, load_factor, stiffness_ratio,
    friction_coefficient; optional embedment_fraction,
    thermal_relaxation_fraction, interfaces, prevailing_torque_nm,
    scc_justification_recorded.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "material", "nominal_diameter_mm", "pitch_mm", "applied_torque_nm",
        "torque_tolerance_fraction", "nut_factor_min", "nut_factor_max", "locking",
        "external_tensile_load_n", "shear_load_n", "load_factor", "stiffness_ratio",
        "friction_coefficient",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    material = fastener_material(spec["material"])
    lock = locking_feature(spec["locking"])
    prevailing = spec.get("prevailing_torque_nm", lock["prevailing_torque_nm"])
    area = tensile_stress_area_mm2(spec["nominal_diameter_mm"], spec["pitch_mm"])
    preload_min, preload_max = preload_band_n(
        spec["applied_torque_nm"], spec["torque_tolerance_fraction"],
        spec["nominal_diameter_mm"], spec["nut_factor_min"], spec["nut_factor_max"],
        prevailing,
    )
    losses = preload_losses_n(
        preload_min,
        spec.get("embedment_fraction", DEFAULT_EMBEDMENT_FRACTION),
        spec.get("thermal_relaxation_fraction", DEFAULT_THERMAL_RELAXATION_FRACTION),
    )
    residual = residual_preload_n(preload_min, losses)
    gapping = gapping_margin(
        residual, spec["external_tensile_load_n"], spec["load_factor"],
        spec["stiffness_ratio"],
    )
    slip = slip_margin(
        residual, spec["friction_coefficient"], spec["shear_load_n"],
        spec["load_factor"], spec.get("interfaces", 1),
    )
    yielding = yield_margin(
        preload_max, spec["external_tensile_load_n"], spec["load_factor"],
        spec["stiffness_ratio"], area, material["yield_mpa"],
    )

    findings = []
    scc_ok = material["scc_category"] == REQUIRED_SCC_CATEGORY
    if not scc_ok:
        if spec.get("scc_justification_recorded", False):
            scc_ok = True
            findings.append(
                "%s sits in stress-corrosion category %s and is retained on a "
                "recorded justification"
                % (spec["material"], material["scc_category"])
            )
        else:
            findings.append(
                "%s sits in stress-corrosion category %s with no justification on "
                "record; category %s is expected"
                % (spec["material"], material["scc_category"], REQUIRED_SCC_CATEGORY)
            )
    locking_ok = lock["positive"]
    if not locking_ok:
        findings.append(
            "locking feature %r is not a positive locking device" % spec["locking"]
        )
    margins = {"gapping": gapping, "slip": slip, "yield": yielding}
    margin_ok = True
    for label in ("gapping", "slip", "yield"):
        value = margins[label]
        ok = value > 0.0 or math.isclose(
            value, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
        )
        if not ok:
            margin_ok = False
            findings.append("%s margin of safety is %.4f" % (label, value))

    return {
        "scc_category": material["scc_category"],
        "tensile_stress_area_mm2": area,
        "prevailing_torque_nm": float(prevailing),
        "preload_min_n": preload_min,
        "preload_max_n": preload_max,
        "preload_losses_n": losses,
        "residual_preload_n": residual,
        "gapping_margin": gapping,
        "slip_margin": slip,
        "yield_margin": yielding,
        "positive_locking": locking_ok,
        "compliant": scc_ok and locking_ok and margin_ok,
        "findings": findings,
    }

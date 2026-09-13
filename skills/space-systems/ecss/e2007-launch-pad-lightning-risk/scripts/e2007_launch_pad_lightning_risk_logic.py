#!/usr/bin/env python3
"""Launch-pad lightning risk assessment (direct and indirect effects).

Anchor: ECSS-E-ST-20-07C clause 4.2.3.2 (risk assessment against direct
and indirect lightning effects while the system stands on the pad). The
clause is paraphrased into an implementable procedure; no standard text
is reproduced.

Model used throughout:
  direct attachment      -> rolling-sphere protected volume built by the
                            pad lightning-masts at the declared
                            protection-level
  indirect coupling      -> loop voltage from the stroke
                            current-derivative, the enclosed loop-area
                            and the distance to the channel
  conducted umbilical    -> shield-transfer voltage from the shared
                            stroke current, the transfer-impedance per
                            unit length and the exposed run length
  residual risk          -> likelihood-severity matrix, worst component

Stdlib only, deterministic, offline.
"""

import math

VACUUM_PERMEABILITY_H_PER_M = 4.0e-7 * math.pi

# --- threat components ------------------------------------------------------

THREAT_DIRECT = "direct-attachment"
THREAT_INDIRECT = "indirect-magnetic-coupling"
THREAT_UMBILICAL = "conducted-umbilical-transient"

THREAT_KINDS = (THREAT_DIRECT, THREAT_INDIRECT, THREAT_UMBILICAL)

THREAT_ALIASES = {
    "direct-strike": THREAT_DIRECT,
    "direct-attachment": THREAT_DIRECT,
    "attachment": THREAT_DIRECT,
    "nearby-strike": THREAT_INDIRECT,
    "indirect-magnetic-coupling": THREAT_INDIRECT,
    "magnetic-field-coupling": THREAT_INDIRECT,
    "conducted-umbilical-transient": THREAT_UMBILICAL,
    "umbilical-conducted": THREAT_UMBILICAL,
    "ground-support-umbilical": THREAT_UMBILICAL,
}

# --- rolling sphere ---------------------------------------------------------

ROLLING_SPHERE_RADIUS_M = {
    "level-i": 20.0,
    "level-ii": 30.0,
    "level-iii": 45.0,
    "level-iv": 60.0,
}

GEOMETRY_TOLERANCE_M = 1e-9
WITHSTAND_TOLERANCE_V = 1e-6

# --- risk matrix ------------------------------------------------------------

LIKELIHOOD_SCALE = ("improbable", "remote", "occasional", "probable", "frequent")
SEVERITY_SCALE = ("negligible", "marginal", "critical", "catastrophic")

RISK_LOW_MAX = 3
RISK_MEDIUM_MAX = 8
RISK_HIGH_MAX = 14

RISK_LEVELS = ("low", "medium", "high", "unacceptable")


def _finite_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % label)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    return value


# --- threat categorization --------------------------------------------------


def threat_component_kind(raw_kind):
    """Resolve a declared threat component to one of the three kinds."""
    key = str(raw_kind).strip().lower()
    if not key:
        raise ValueError("threat component kind must not be blank")
    if key not in THREAT_ALIASES:
        raise ValueError("unrecognised threat component: %r" % (raw_kind,))
    return THREAT_ALIASES[key]


def uncovered_threat_components(declared_kinds):
    """Threat kinds the assessment does not cover at all."""
    if not isinstance(declared_kinds, (list, tuple, set, frozenset)):
        raise ValueError("declared threat components must be a list, tuple or set")
    covered = set(threat_component_kind(k) for k in declared_kinds)
    return tuple(k for k in THREAT_KINDS if k not in covered)


# --- rolling-sphere geometry ------------------------------------------------


def rolling_sphere_radius_m(protection_level):
    """Sphere radius associated with a declared protection level."""
    key = str(protection_level).strip().lower()
    if key not in ROLLING_SPHERE_RADIUS_M:
        raise ValueError("unrecognised protection level: %r" % (protection_level,))
    return ROLLING_SPHERE_RADIUS_M[key]


def _chord_term(height_m, sphere_radius_m):
    """sqrt(2*R*h - h^2), the horizontal chord of the rolling sphere."""
    value = 2.0 * sphere_radius_m * height_m - height_m * height_m
    if value < 0.0:
        value = 0.0
    return math.sqrt(value)


def protective_radius_m(mast_height_m, point_height_m, sphere_radius_m):
    """Protected radius around one mast at a given height.

    Two branches. A mast no taller than the sphere radius protects out
    to the difference of the two chord terms. A mast taller than the
    sphere radius lets the sphere rest against its flank, so the
    protected radius falls to zero at the height of the radius and the
    volume above that is exposed to a side strike.
    """
    radius = _finite_number(sphere_radius_m, "sphere radius")
    if radius <= 0.0:
        raise ValueError("sphere radius must be positive")
    mast = _finite_number(mast_height_m, "mast height")
    if mast <= 0.0:
        raise ValueError("mast height must be positive")
    point = _finite_number(point_height_m, "point height")
    if point < 0.0:
        raise ValueError("point height must not be negative")
    if point > mast:
        return 0.0
    if mast <= radius:
        return max(0.0, _chord_term(mast, radius) - _chord_term(point, radius))
    if point >= radius:
        return 0.0
    return max(0.0, radius - _chord_term(point, radius))


def is_within_protected_volume(
    mast_height_m, point_height_m, horizontal_offset_m, sphere_radius_m
):
    """True when a point lies inside one mast's protected volume."""
    offset = _finite_number(horizontal_offset_m, "horizontal offset")
    if offset < 0.0:
        raise ValueError("horizontal offset must not be negative")
    reach = protective_radius_m(mast_height_m, point_height_m, sphere_radius_m)
    return offset < reach or math.isclose(
        offset, reach, rel_tol=0.0, abs_tol=GEOMETRY_TOLERANCE_M
    )


def vehicle_is_protected(masts, vehicle_height_m, sphere_radius_m):
    """True when at least one pad mast covers the vehicle."""
    if not isinstance(masts, (list, tuple)) or not masts:
        raise ValueError("at least one pad mast record is required")
    for mast in masts:
        if not isinstance(mast, dict):
            raise ValueError("mast record must be a mapping")
        if is_within_protected_volume(
            mast.get("height_m"),
            vehicle_height_m,
            mast.get("horizontal_offset_m"),
            sphere_radius_m,
        ):
            return True
    return False


# --- stroke coupling --------------------------------------------------------


def normalize_stroke(raw):
    """Normalize the design stroke parameters."""
    if not isinstance(raw, dict):
        raise ValueError("stroke record must be a mapping")
    peak = _finite_number(raw.get("peak_current_ka"), "peak current")
    if peak <= 0.0:
        raise ValueError("peak current must be positive")
    rise = _finite_number(raw.get("rise_time_us"), "rise time")
    if rise <= 0.0:
        raise ValueError("rise time must be positive")
    distance = _finite_number(raw.get("distance_m"), "stroke distance")
    if distance <= 0.0:
        raise ValueError("stroke distance must be positive")
    return {
        "peak_current_ka": peak,
        "rise_time_us": rise,
        "distance_m": distance,
    }


def current_derivative_a_per_s(peak_current_ka, rise_time_us):
    """Average current-derivative of the stroke front, in amperes per second."""
    peak = _finite_number(peak_current_ka, "peak current")
    if peak <= 0.0:
        raise ValueError("peak current must be positive")
    rise = _finite_number(rise_time_us, "rise time")
    if rise <= 0.0:
        raise ValueError("rise time must be positive")
    return (peak * 1.0e3) / (rise * 1.0e-6)


def induced_loop_voltage_v(stroke, loop_area_m2):
    """Voltage induced in a wiring loop by a nearby stroke."""
    normalized = normalize_stroke(stroke) if isinstance(stroke, dict) else None
    if normalized is None:
        raise ValueError("stroke record must be a mapping")
    area = _finite_number(loop_area_m2, "loop area")
    if area < 0.0:
        raise ValueError("loop area must not be negative")
    didt = current_derivative_a_per_s(
        normalized["peak_current_ka"], normalized["rise_time_us"]
    )
    return (
        VACUUM_PERMEABILITY_H_PER_M
        * area
        * didt
        / (2.0 * math.pi * normalized["distance_m"])
    )


def umbilical_transient_voltage_v(
    peak_current_ka, share_fraction, transfer_impedance_ohm_per_m, length_m
):
    """Shield-transfer voltage developed along the umbilical run."""
    peak = _finite_number(peak_current_ka, "peak current")
    if peak <= 0.0:
        raise ValueError("peak current must be positive")
    share = _finite_number(share_fraction, "shield current share")
    if not 0.0 <= share <= 1.0:
        raise ValueError("shield current share must lie between 0 and 1")
    transfer = _finite_number(
        transfer_impedance_ohm_per_m, "shield transfer impedance"
    )
    if transfer < 0.0:
        raise ValueError("shield transfer impedance must not be negative")
    length = _finite_number(length_m, "umbilical length")
    if length <= 0.0:
        raise ValueError("umbilical length must be positive")
    return peak * 1.0e3 * share * transfer * length


def withstands(applied_v, withstand_v, tolerance=WITHSTAND_TOLERANCE_V):
    """True when an applied stress stays within the withstand level.

    The applied voltage is a product and quotient of physical constants,
    so an exactly compliant case can land a few units in the last place
    above the level. The representation error is absorbed here; the
    withstand level itself is never raised.
    """
    applied = _finite_number(applied_v, "applied voltage")
    if applied < 0.0:
        raise ValueError("applied voltage must not be negative")
    level = _finite_number(withstand_v, "withstand level")
    if level <= 0.0:
        raise ValueError("withstand level must be positive")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    return applied < level or math.isclose(
        applied, level, rel_tol=0.0, abs_tol=tolerance
    )


def stress_ratio(applied_v, withstand_v):
    """Applied stress expressed as a fraction of the withstand level."""
    applied = _finite_number(applied_v, "applied voltage")
    if applied < 0.0:
        raise ValueError("applied voltage must not be negative")
    level = _finite_number(withstand_v, "withstand level")
    if level <= 0.0:
        raise ValueError("withstand level must be positive")
    return applied / level


# --- risk grading -----------------------------------------------------------


def risk_level(likelihood, severity):
    """Grade one threat component on the likelihood-severity matrix."""
    like = str(likelihood).strip().lower()
    if like not in LIKELIHOOD_SCALE:
        raise ValueError("unrecognised likelihood: %r" % (likelihood,))
    sev = str(severity).strip().lower()
    if sev not in SEVERITY_SCALE:
        raise ValueError("unrecognised severity: %r" % (severity,))
    score = (LIKELIHOOD_SCALE.index(like) + 1) * (SEVERITY_SCALE.index(sev) + 1)
    if score <= RISK_LOW_MAX:
        return "low"
    if score <= RISK_MEDIUM_MAX:
        return "medium"
    if score <= RISK_HIGH_MAX:
        return "high"
    return "unacceptable"


def likelihood_from_ratio(ratio):
    """Map a stress ratio onto the likelihood scale."""
    value = _finite_number(ratio, "stress ratio")
    if value < 0.0:
        raise ValueError("stress ratio must not be negative")
    if value >= 2.0:
        return "frequent"
    if value > 1.0:
        return "probable"
    if value > 0.5:
        return "occasional"
    if value > 0.1:
        return "remote"
    return "improbable"


def worst_risk_level(levels):
    """Worst level in a set of graded components."""
    if not isinstance(levels, (list, tuple)) or not levels:
        raise ValueError("at least one graded component is required")
    worst = 0
    for level in levels:
        key = str(level).strip().lower()
        if key not in RISK_LEVELS:
            raise ValueError("unrecognised risk level: %r" % (level,))
        worst = max(worst, RISK_LEVELS.index(key))
    return RISK_LEVELS[worst]


# --- top-level assessment ---------------------------------------------------


def assess_pad_lightning_risk(config):
    """Run the clause 4.2.3.2 pad lightning risk assessment."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    stroke = normalize_stroke(config.get("stroke"))
    radius = rolling_sphere_radius_m(config.get("protection_level"))
    vehicle_height = _finite_number(config.get("vehicle_height_m"), "vehicle height")
    if vehicle_height <= 0.0:
        raise ValueError("vehicle height must be positive")
    protected = vehicle_is_protected(config.get("masts"), vehicle_height, radius)

    victim = config.get("victim")
    if not isinstance(victim, dict):
        raise ValueError("victim circuit record must be a mapping")
    loop_voltage = induced_loop_voltage_v(stroke, victim.get("loop_area_m2"))
    loop_withstand = victim.get("transient_withstand_v")
    loop_ok = withstands(loop_voltage, loop_withstand)
    loop_ratio = stress_ratio(loop_voltage, loop_withstand)

    umbilical = config.get("umbilical")
    if not isinstance(umbilical, dict):
        raise ValueError("umbilical record must be a mapping")
    umbilical_voltage = umbilical_transient_voltage_v(
        stroke["peak_current_ka"],
        umbilical.get("share_fraction"),
        umbilical.get("transfer_impedance_ohm_per_m"),
        umbilical.get("length_m"),
    )
    umbilical_withstand = umbilical.get("transient_withstand_v")
    umbilical_ok = withstands(umbilical_voltage, umbilical_withstand)
    umbilical_ratio = stress_ratio(umbilical_voltage, umbilical_withstand)

    uncovered = uncovered_threat_components(config.get("assessed_components", ()))

    direct_risk = risk_level(
        "improbable" if protected else "occasional", "catastrophic"
    )
    indirect_risk = risk_level(likelihood_from_ratio(loop_ratio), "critical")
    umbilical_risk = risk_level(likelihood_from_ratio(umbilical_ratio), "critical")

    findings = []
    for kind in uncovered:
        findings.append("threat-component-not-assessed:%s" % kind)
    if not protected:
        findings.append("vehicle-outside-protected-volume")
    if not loop_ok:
        findings.append("indirect-coupling-exceeds-withstand")
    if not umbilical_ok:
        findings.append("umbilical-transient-exceeds-withstand")

    return {
        "sphere_radius_m": radius,
        "direct_attachment_protected": protected,
        "induced_loop_voltage_v": loop_voltage,
        "loop_stress_ratio": loop_ratio,
        "umbilical_voltage_v": umbilical_voltage,
        "umbilical_stress_ratio": umbilical_ratio,
        "component_risk": {
            THREAT_DIRECT: direct_risk,
            THREAT_INDIRECT: indirect_risk,
            THREAT_UMBILICAL: umbilical_risk,
        },
        "residual_risk": worst_risk_level(
            [direct_risk, indirect_risk, umbilical_risk]
        ),
        "uncovered_components": uncovered,
        "findings": tuple(findings),
        "acceptable": not findings,
    }

"""Leakage current and residual output voltage permitted while the device is off.

Anchor: ECSS-E-ST-20-20C clause 5.4.1.3.1 (the maximum leakage current and the
maximum residual output voltage a limiter presents at its output in the off
state). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Decide whether the clause bites. It addresses devices that hold a genuine
   commanded off state; a foldback or retriggerable limiter regulates rather
   than switching off and is reported outside the clause rather than failed by
   it.
2. Validate the declared off-state limits -- a maximum leakage current, a
   maximum residual output voltage and the off-state load resistance the
   residual voltage develops across.
3. Cross-check the two limits against each other before looking at a single
   measurement. Leakage and residual voltage are one phenomenon seen twice:
   the leakage limit, pushed through the off-state load resistance, develops a
   voltage of its own. Where that voltage is above the declared residual
   voltage limit the two limits cannot both be honoured, and the governing
   leakage ceiling is the tighter of the two, not the one on the data sheet.
4. Grade every measurement corner against both limits, keep the margins, and
   name the worst corner on each.
5. Report a corner set that does not bound the parameter. Off-state leakage is
   temperature-driven; a channel measured at ambient alone has been measured
   where the leakage is smallest.

The governing leakage ceiling is the number a review needs: a data-sheet
leakage figure that the residual voltage limit does not actually permit is the
common way a compliant-looking off state turns into a load that never fully
de-energises.
"""

import math

__all__ = [
    "LEAKAGE_TOLERANCE_UA",
    "VOLTAGE_TOLERANCE_V",
    "REQUIRED_CORNERS",
    "MEASUREMENT_CORNERS",
    "LIMITER_CATEGORIES",
    "OFF_STATE_CATEGORIES",
    "normalise_category",
    "normalise_corner",
    "validate_limits",
    "validate_measurements",
    "implied_residual_voltage_v",
    "governing_leakage_ceiling_ua",
    "leakage_margin_ua",
    "residual_voltage_margin_v",
    "grade_corner",
    "worst_corner",
    "assess_off_state",
]

# Leakage is quoted in microamperes and residual voltage in volts; a part
# routinely measures exactly on its limit. Absorb the representation error,
# never the engineering margin.
LEAKAGE_TOLERANCE_UA = 1e-9
VOLTAGE_TOLERANCE_V = 1e-9

# Off-state leakage is temperature-driven, so a bounding data set needs the
# temperature extremes as well as ambient.
REQUIRED_CORNERS = ("cold", "ambient", "hot")
MEASUREMENT_CORNERS = REQUIRED_CORNERS

# Categories that hold a commanded off state and therefore carry an off-state
# leakage and residual voltage limit.
OFF_STATE_CATEGORIES = ("latching", "high-power")
LIMITER_CATEGORIES = OFF_STATE_CATEGORIES + ("retriggerable", "foldback")

_CATEGORY_ALIASES = {
    "lcl": "latching",
    "latching-current-limiter": "latching",
    "hpc": "high-power",
    "high-power-limiter": "high-power",
    "rcl": "retriggerable",
    "fcl": "foldback",
}

_CORNER_ALIASES = {
    "low-temperature": "cold",
    "cold-qualification": "cold",
    "room": "ambient",
    "room-temperature": "ambient",
    "nominal": "ambient",
    "high-temperature": "hot",
    "hot-qualification": "hot",
}


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive and finite, got %g" % (label, number))
    return number


def _non_negative_real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(
            "%s must be non-negative and finite, got %g" % (label, number)
        )
    return number


def normalise_category(category):
    """Return the canonical limiter category name."""
    key = _text(category, "category")
    key = _CATEGORY_ALIASES.get(key, key)
    if key not in LIMITER_CATEGORIES:
        raise ValueError(
            "unknown limiter category %r; known: %s"
            % (category, ", ".join(LIMITER_CATEGORIES))
        )
    return key


def normalise_corner(corner):
    """Return the canonical measurement corner name."""
    key = _text(corner, "corner")
    key = _CORNER_ALIASES.get(key, key)
    if key not in MEASUREMENT_CORNERS:
        raise ValueError(
            "unknown measurement corner %r; known: %s"
            % (corner, ", ".join(MEASUREMENT_CORNERS))
        )
    return key


def validate_limits(spec):
    """Return the validated off-state limits of one device.

    spec keys: category, max_leakage_ua, max_residual_voltage_v,
    load_off_resistance_ohm.
    """
    if not isinstance(spec, dict):
        raise ValueError("limits spec must be a mapping")
    required = (
        "category",
        "max_leakage_ua",
        "max_residual_voltage_v",
        "load_off_resistance_ohm",
    )
    for key in required:
        if key not in spec:
            raise ValueError("limits spec missing required key '%s'" % key)
    return {
        "category": normalise_category(spec["category"]),
        "max_leakage_ua": _positive_real(spec["max_leakage_ua"], "max_leakage_ua"),
        "max_residual_voltage_v": _positive_real(
            spec["max_residual_voltage_v"], "max_residual_voltage_v"
        ),
        "load_off_resistance_ohm": _positive_real(
            spec["load_off_resistance_ohm"], "load_off_resistance_ohm"
        ),
    }


def validate_measurements(raw):
    """Return the validated off-state measurements, indexed by corner."""
    if not isinstance(raw, (list, tuple)):
        raise ValueError("measurements must be a sequence")
    if not raw:
        raise ValueError("at least one off-state measurement is required")
    measurements = {}
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("measurements[%d] must be a mapping" % i)
        for key in ("corner", "leakage_ua", "residual_voltage_v"):
            if key not in item:
                raise ValueError("measurements[%d] missing required key '%s'" % (i, key))
        corner = normalise_corner(item["corner"])
        if corner in measurements:
            raise ValueError("corner %r is measured twice" % corner)
        measurements[corner] = {
            "corner": corner,
            "leakage_ua": _non_negative_real(
                item["leakage_ua"], "measurements[%d]['leakage_ua']" % i
            ),
            "residual_voltage_v": _non_negative_real(
                item["residual_voltage_v"],
                "measurements[%d]['residual_voltage_v']" % i,
            ),
        }
    return measurements


def implied_residual_voltage_v(leakage_ua, load_off_resistance_ohm):
    """Return the voltage a leakage current develops across the off-state load."""
    leakage = _non_negative_real(leakage_ua, "leakage_ua")
    resistance = _positive_real(load_off_resistance_ohm, "load_off_resistance_ohm")
    return leakage * resistance / 1.0e6


def governing_leakage_ceiling_ua(limits):
    """Return the leakage ceiling once both declared limits are honoured."""
    from_voltage = (
        limits["max_residual_voltage_v"] * 1.0e6 / limits["load_off_resistance_ohm"]
    )
    return min(limits["max_leakage_ua"], from_voltage)


def leakage_margin_ua(limits, measurement):
    """Return the governing leakage ceiling less the measured leakage."""
    return governing_leakage_ceiling_ua(limits) - measurement["leakage_ua"]


def residual_voltage_margin_v(limits, measurement):
    """Return the residual voltage limit less the measured residual voltage."""
    return limits["max_residual_voltage_v"] - measurement["residual_voltage_v"]


def _below_bound(margin, tolerance):
    """Return True when a margin is negative by more than representation error."""
    return margin < 0.0 and not math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=tolerance
    )


def grade_corner(limits, measurement):
    """Grade one measurement corner against both off-state limits."""
    leakage_margin = leakage_margin_ua(limits, measurement)
    voltage_margin = residual_voltage_margin_v(limits, measurement)
    implied = implied_residual_voltage_v(
        measurement["leakage_ua"], limits["load_off_resistance_ohm"]
    )
    findings = []
    if _below_bound(leakage_margin, LEAKAGE_TOLERANCE_UA):
        findings.append(
            "leakage %g uA at the %s corner is above the %g uA the off state "
            "permits"
            % (
                measurement["leakage_ua"],
                measurement["corner"],
                governing_leakage_ceiling_ua(limits),
            )
        )
    if _below_bound(voltage_margin, VOLTAGE_TOLERANCE_V):
        findings.append(
            "residual output voltage %g V at the %s corner is above the %g V "
            "limit"
            % (
                measurement["residual_voltage_v"],
                measurement["corner"],
                limits["max_residual_voltage_v"],
            )
        )
    return {
        "corner": measurement["corner"],
        "leakage_ua": measurement["leakage_ua"],
        "residual_voltage_v": measurement["residual_voltage_v"],
        "implied_residual_voltage_v": implied,
        "leakage_margin_ua": leakage_margin,
        "residual_voltage_margin_v": voltage_margin,
        "within_limits": not findings,
        "findings": findings,
    }


def worst_corner(records, margin_key):
    """Return the corner name holding the smallest margin on the given key."""
    if not records:
        raise ValueError("no graded corners to compare")
    if margin_key not in ("leakage_margin_ua", "residual_voltage_margin_v"):
        raise ValueError("unknown margin key %r" % (margin_key,))
    worst = records[0]
    for record in records[1:]:
        if record[margin_key] < worst[margin_key]:
            worst = record
    return worst["corner"]


def assess_off_state(spec):
    """Grade one device's off-state leakage and residual voltage.

    spec keys: category, max_leakage_ua, max_residual_voltage_v,
    load_off_resistance_ohm, measurements.
    """
    if not isinstance(spec, dict):
        raise ValueError("off-state spec must be a mapping")
    if "measurements" not in spec:
        raise ValueError("off-state spec missing required key 'measurements'")
    limits = validate_limits(spec)
    measurements = validate_measurements(spec["measurements"])

    scope_findings = []
    findings = []

    in_scope = limits["category"] in OFF_STATE_CATEGORIES
    if not in_scope:
        scope_findings.append(
            "category %s holds no commanded off state, so the clause places no "
            "off-state leakage or residual voltage limit on it"
            % limits["category"]
        )

    ceiling = governing_leakage_ceiling_ua(limits)
    implied_from_limit = implied_residual_voltage_v(
        limits["max_leakage_ua"], limits["load_off_resistance_ohm"]
    )
    limits_consistent = not _below_bound(
        limits["max_residual_voltage_v"] - implied_from_limit, VOLTAGE_TOLERANCE_V
    )
    if not limits_consistent:
        findings.append(
            "the %g uA leakage limit develops %g V across the %g ohm off-state "
            "load, above the %g V residual voltage limit; the governing leakage "
            "ceiling is %g uA"
            % (
                limits["max_leakage_ua"],
                implied_from_limit,
                limits["load_off_resistance_ohm"],
                limits["max_residual_voltage_v"],
                ceiling,
            )
        )

    records = [grade_corner(limits, measurements[c]) for c in sorted(measurements)]
    for record in records:
        findings.extend(record["findings"])

    missing = [c for c in REQUIRED_CORNERS if c not in measurements]
    if missing:
        findings.append(
            "off-state leakage is temperature-driven and the %s corner(s) were "
            "not measured, so the declared limits are not bounded"
            % ", ".join(missing)
        )

    compliant = not findings
    if not in_scope:
        verdict = "out-of-scope"
    elif compliant:
        verdict = "compliant"
    else:
        verdict = "non-compliant"

    return {
        "category": limits["category"],
        "in_scope": in_scope,
        "declared_leakage_limit_ua": limits["max_leakage_ua"],
        "governing_leakage_ceiling_ua": ceiling,
        "residual_voltage_from_leakage_limit_v": implied_from_limit,
        "limits_consistent": limits_consistent,
        "measured_corners": sorted(measurements),
        "missing_corners": missing,
        "corner_records": records,
        "worst_leakage_corner": worst_corner(records, "leakage_margin_ua"),
        "worst_residual_voltage_corner": worst_corner(
            records, "residual_voltage_margin_v"
        ),
        "compliant": compliant,
        "verdict": verdict,
        "findings": scope_findings + findings,
    }

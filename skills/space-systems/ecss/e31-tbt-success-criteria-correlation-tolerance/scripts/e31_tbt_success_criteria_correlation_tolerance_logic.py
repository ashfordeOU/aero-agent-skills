"""Thermal balance test success criteria and correlation tolerance.

Anchor: ECSS-E-ST-31C clause 4.5.3.2 (success criteria of the thermal balance
test: the tolerance between predicted and measured temperatures and the
resulting verdict). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate each sensor record and separate the excluded sensors, requiring a
   recorded reason for every exclusion and capping the excluded weight.
2. Mark each graded sensor against the per-sensor correlation tolerance band.
3. Spend the exceedance budget by sensor weight rather than by headcount.
4. Grade the weighted bias and the weighted spread against their own
   allowances, so a model that is right on average and wrong everywhere still
   fails.
5. Return a verdict that names the gates that failed.
"""

import math

__all__ = [
    "CRITERION_TOLERANCE",
    "GATE_NAMES",
    "validate_sensor_record",
    "partition_sensors",
    "sensor_deviation_k",
    "mark_against_band",
    "weighted_exceedance_fraction",
    "weighted_bias_k",
    "weighted_spread_k",
    "grade_correlation",
]

# A fraction or a deviation can land exactly on its criterion. Absorb the
# representation error here instead of moving the criterion.
CRITERION_TOLERANCE = 1e-9

# The gates a verdict can fail on, in the order they are reported.
GATE_NAMES = (
    "exclusion_record",
    "excluded_weight",
    "per_sensor_band",
    "bias",
    "spread",
)


def _require_real(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _require_real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _require_non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _require_real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _require_fraction(value, label):
    """Return value as a fraction in the closed unit interval."""
    out = _require_real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, out))
    return out


def validate_sensor_record(record):
    """Return one validated correlation record.

    record keys: name, predicted_k, measured_k; optional weight (default one),
    excluded (default false) and exclusion_reason.
    """
    if not isinstance(record, dict):
        raise ValueError("sensor record must be a mapping")
    for key in ("name", "predicted_k", "measured_k"):
        if key not in record:
            raise ValueError("sensor record missing required key '%s'" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("sensor name must be a non-empty string")
    predicted = _require_real(record["predicted_k"], "predicted_k")
    measured = _require_real(record["measured_k"], "measured_k")
    for label, value in (("predicted_k", predicted), ("measured_k", measured)):
        if value <= 0.0:
            raise ValueError("%s must be an absolute temperature above zero" % label)
    weight = _require_positive(record.get("weight", 1.0), "weight")
    excluded = record.get("excluded", False)
    if not isinstance(excluded, bool):
        raise ValueError("excluded must be a boolean")
    reason = record.get("exclusion_reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("exclusion_reason must be a string when present")
    return {
        "name": name,
        "predicted_k": predicted,
        "measured_k": measured,
        "weight": weight,
        "excluded": excluded,
        "exclusion_reason": reason,
    }


def partition_sensors(records):
    """Split the sensor set into graded and excluded, with exclusion findings."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of sensor records")
    graded = []
    excluded = []
    findings = []
    seen = set()
    for record in records:
        validated = validate_sensor_record(record)
        if validated["name"] in seen:
            raise ValueError("duplicate sensor name '%s'" % validated["name"])
        seen.add(validated["name"])
        if validated["excluded"]:
            reason = validated["exclusion_reason"]
            if not isinstance(reason, str) or not reason.strip():
                findings.append(
                    "sensor %s is excluded with no recorded reason" % validated["name"]
                )
            excluded.append(validated)
        else:
            graded.append(validated)
    if not graded:
        raise ValueError("every sensor was excluded; there is nothing to grade")
    return {"graded": graded, "excluded": excluded, "findings": findings}


def sensor_deviation_k(record):
    """Return the predicted-minus-measured deviation of one sensor."""
    validated = validate_sensor_record(record)
    return validated["predicted_k"] - validated["measured_k"]


def mark_against_band(graded, tolerance_k):
    """Mark each graded sensor inside or outside the per-sensor tolerance band."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence")
    band = _require_positive(tolerance_k, "tolerance_k")
    marked = []
    for record in graded:
        validated = validate_sensor_record(record)
        deviation = validated["predicted_k"] - validated["measured_k"]
        marked.append({
            "name": validated["name"],
            "weight": validated["weight"],
            "deviation_k": deviation,
            "within_band": abs(deviation) <= band + CRITERION_TOLERANCE,
        })
    return marked


def weighted_exceedance_fraction(marked):
    """Return the share of graded weight sitting outside the tolerance band."""
    if not isinstance(marked, (list, tuple)) or not marked:
        raise ValueError("marked must be a non-empty sequence")
    total = 0.0
    outside = 0.0
    for index, item in enumerate(marked):
        if not isinstance(item, dict) or "within_band" not in item:
            raise ValueError("marked[%d] must carry 'within_band'" % index)
        weight = _require_positive(item.get("weight", 1.0), "marked[%d] weight" % index)
        total += weight
        if not item["within_band"]:
            outside += weight
    return outside / total


def weighted_bias_k(marked):
    """Return the weighted mean deviation of the graded sensors."""
    if not isinstance(marked, (list, tuple)) or not marked:
        raise ValueError("marked must be a non-empty sequence")
    total = 0.0
    accumulated = 0.0
    for index, item in enumerate(marked):
        if not isinstance(item, dict) or "deviation_k" not in item:
            raise ValueError("marked[%d] must carry 'deviation_k'" % index)
        weight = _require_positive(item.get("weight", 1.0), "marked[%d] weight" % index)
        deviation = _require_real(item["deviation_k"], "marked[%d] deviation_k" % index)
        total += weight
        accumulated += weight * deviation
    return accumulated / total


def weighted_spread_k(marked):
    """Return the weighted spread of the graded deviations about their bias."""
    bias = weighted_bias_k(marked)
    total = 0.0
    accumulated = 0.0
    for item in marked:
        weight = float(item.get("weight", 1.0))
        deviation = float(item["deviation_k"])
        total += weight
        accumulated += weight * (deviation - bias) ** 2
    return math.sqrt(accumulated / total)


def grade_correlation(records, criteria):
    """Grade a thermal balance test against its correlation success criteria.

    criteria keys: tolerance_k; optional exceedance_budget (weight fraction
    allowed outside the band, default zero), bias_tolerance_k,
    spread_tolerance_k and max_excluded_fraction.
    """
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping")
    if "tolerance_k" not in criteria:
        raise ValueError("criteria missing required key 'tolerance_k'")
    band = _require_positive(criteria["tolerance_k"], "tolerance_k")
    budget = _require_fraction(
        criteria.get("exceedance_budget", 0.0), "exceedance_budget"
    )
    partition = partition_sensors(records)
    graded = partition["graded"]
    marked = mark_against_band(graded, band)
    exceedance = weighted_exceedance_fraction(marked)
    bias = weighted_bias_k(marked)
    spread = weighted_spread_k(marked)
    graded_weight = sum(item["weight"] for item in marked)
    excluded_weight = sum(item["weight"] for item in partition["excluded"])
    total_weight = graded_weight + excluded_weight
    excluded_fraction = excluded_weight / total_weight
    failed_gates = []
    findings = list(partition["findings"])
    if findings:
        failed_gates.append("exclusion_record")
    max_excluded = criteria.get("max_excluded_fraction")
    if max_excluded is not None:
        max_excluded = _require_fraction(max_excluded, "max_excluded_fraction")
        if excluded_fraction > max_excluded + CRITERION_TOLERANCE:
            failed_gates.append("excluded_weight")
            findings.append(
                "%.3f of the sensor weight was excluded against a %.3f cap"
                % (excluded_fraction, max_excluded)
            )
    if exceedance > budget + CRITERION_TOLERANCE:
        failed_gates.append("per_sensor_band")
        findings.append(
            "%.3f of the graded weight sits outside the %.3f K band against a "
            "%.3f budget" % (exceedance, band, budget)
        )
    bias_tolerance = criteria.get("bias_tolerance_k")
    if bias_tolerance is not None:
        bias_tolerance = _require_non_negative(bias_tolerance, "bias_tolerance_k")
        if abs(bias) > bias_tolerance + CRITERION_TOLERANCE:
            failed_gates.append("bias")
            findings.append(
                "the weighted bias %.3f K exceeds the %.3f K allowance"
                % (bias, bias_tolerance)
            )
    spread_tolerance = criteria.get("spread_tolerance_k")
    if spread_tolerance is not None:
        spread_tolerance = _require_non_negative(spread_tolerance, "spread_tolerance_k")
        if spread > spread_tolerance + CRITERION_TOLERANCE:
            failed_gates.append("spread")
            findings.append(
                "the weighted spread %.3f K exceeds the %.3f K allowance"
                % (spread, spread_tolerance)
            )
    worst = max(marked, key=lambda item: abs(item["deviation_k"]))
    return {
        "marked": marked,
        "excluded": [item["name"] for item in partition["excluded"]],
        "excluded_weight_fraction": excluded_fraction,
        "exceedance_fraction": exceedance,
        "bias_k": bias,
        "spread_k": spread,
        "worst_sensor": worst["name"],
        "worst_deviation_k": worst["deviation_k"],
        "failed_gates": failed_gates,
        "findings": findings,
        "verdict": "pass" if not failed_gates else "fail",
    }

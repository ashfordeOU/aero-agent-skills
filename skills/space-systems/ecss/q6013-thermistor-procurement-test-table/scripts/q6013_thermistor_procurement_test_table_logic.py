"""Thermistor procurement test-matrix evaluation for a commercial EEE lot.

Anchor: ECSS-Q-ST-60-13C Table 8-8 (the procurement test matrix applied to
thermistors: which test groups are run, on what sample of the lot, and
against which measured acceptance limits). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the lot the matrix is offered against. No sample may be drawn
   larger than the lot it came from, so a zero or negative device count is
   an input error rather than a degenerate case to be clamped.
2. Check the declared matrix covers every required thermistor test group and
   that no group is declared twice under two methods -- a duplicated group
   is two programmes, and the weaker of the two would otherwise decide the
   lot.
3. Resolve each row's sample size from its declared rule: the whole lot, a
   fixed sample, or a percentage of the lot with a floor. A percentage is
   rounded up to whole devices, with the representation error of the product
   absorbed before the rounding so a sample landing exactly on an integer
   does not gain a device.
4. Reduce the thermistor's own characteristic before any row is judged: a
   two-point resistance reading gives the beta constant of the device, and
   the beta constant with the reference resistance predicts the resistance
   at any other temperature in the matrix. Both the reference resistance and
   the derived beta carry their own procurement tolerance.
5. Take each row's failures against its accept number, and each measured
   parameter -- resistance tolerance, post-stress resistance drift,
   dissipation constant, thermal time constant, insulation resistance --
   against its limit in the direction that limit is written in.
6. Hold the lot when ANY row rejects or the characteristic misses its
   tolerance. Rows are not averaged, and a row that used its accept number
   in full is reported as marginal rather than as a bare pass.
"""

import math

__all__ = [
    "ABSOLUTE_ZERO_C",
    "CEIL_TOLERANCE",
    "LIMIT_TOLERANCE",
    "REQUIRED_TEST_GROUPS",
    "LIMIT_DIRECTIONS",
    "SAMPLE_MODES",
    "REFERENCE_TEMPERATURE_C",
    "validate_lot_size",
    "to_kelvin",
    "predict_resistance",
    "derive_beta_constant",
    "relative_deviation_percent",
    "resolve_sample_size",
    "within_limit",
    "evaluate_measurement",
    "evaluate_characteristic",
    "matrix_coverage",
    "row_verdict",
    "assess_thermistor_test_table",
]

# Below this the Kelvin conversion is not physical; a temperature at or under
# it is an input error, not a cold case.
ABSOLUTE_ZERO_C = -273.15

# The reference temperature a thermistor's nominal resistance is quoted at
# unless the procurement specification names another one.
REFERENCE_TEMPERATURE_C = 25.0

# A percentage of an integer lot is a binary floating-point product and can
# land a few units in the last place above a whole device. Absorb that here,
# before the rounding up, never by relaxing the declared percentage.
CEIL_TOLERANCE = 1e-9

# A measured value sitting exactly on its limit is a representation
# question, not an engineering one.
LIMIT_TOLERANCE = 1e-9

# The thermistor test groups a procurement matrix has to cover before any
# row verdict means anything.
REQUIRED_TEST_GROUPS = (
    "visual-inspection",
    "dimension-check",
    "reference-resistance-measurement",
    "beta-constant-measurement",
    "dissipation-constant",
    "thermal-time-constant",
    "insulation-resistance",
    "thermal-shock",
    "moisture-resistance",
    "life-test",
    "terminal-strength",
    "destructive-physical-analysis",
)

# How a declared acceptance limit is read: an upper bound, a lower bound, or
# a bound on the magnitude of a drift that may move either way.
LIMIT_DIRECTIONS = ("max", "min", "abs-delta")

# How a row's sample is drawn from the lot.
SAMPLE_MODES = ("all", "fixed", "percent")


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_lot_size(lot_size):
    """Return the validated device count of the lot the matrix applies to."""
    size = _count("lot_size", lot_size)
    if size < 1:
        raise ValueError("lot_size must be at least one device, got %d" % size)
    return size


def to_kelvin(celsius):
    """Return an absolute temperature in kelvin for a Celsius reading."""
    value = _real("temperature", celsius)
    if value <= ABSOLUTE_ZERO_C:
        raise ValueError("temperature must be above absolute zero, got %g C" % value)
    return value - ABSOLUTE_ZERO_C


def predict_resistance(reference_ohm, beta_kelvin, temperature_c,
                       reference_c=REFERENCE_TEMPERATURE_C):
    """Return the resistance of a thermistor at a stated temperature.

    The single-parameter model of a negative-temperature-coefficient device:
    the resistance falls exponentially with the reciprocal of the absolute
    temperature, scaled by the beta constant of the material.
    """
    r_ref = _positive("reference resistance", reference_ohm)
    beta = _positive("beta constant", beta_kelvin)
    t_abs = to_kelvin(temperature_c)
    t_ref = to_kelvin(reference_c)
    return r_ref * math.exp(beta * (1.0 / t_abs - 1.0 / t_ref))


def derive_beta_constant(low_ohm, low_temperature_c, high_ohm, high_temperature_c):
    """Return the beta constant implied by a two-point resistance reading.

    The two readings must be at genuinely different temperatures, and the
    colder point must carry the higher resistance: a negative-coefficient
    device whose resistance rose with temperature is a measurement or a
    polarity error, not a device with a negative beta.
    """
    r_low = _positive("low-temperature resistance", low_ohm)
    r_high = _positive("high-temperature resistance", high_ohm)
    t_low = to_kelvin(low_temperature_c)
    t_high = to_kelvin(high_temperature_c)
    if t_high <= t_low:
        raise ValueError(
            "the second reading must be at a higher temperature than the first"
        )
    if r_high >= r_low:
        raise ValueError(
            "resistance must fall with temperature for a negative-coefficient device"
        )
    return math.log(r_low / r_high) / (1.0 / t_low - 1.0 / t_high)


def relative_deviation_percent(measured, nominal):
    """Return the signed deviation of a measured value from its nominal, in percent."""
    value = _real("measured value", measured)
    reference = _positive("nominal value", nominal)
    return 100.0 * (value - reference) / reference


def resolve_sample_size(rule, lot_size):
    """Return the whole-device sample size a row's sampling rule resolves to.

    rule keys: mode ('all', 'fixed' or 'percent'); size for a fixed sample;
    percent and an optional minimum for a percentage of the lot.
    """
    lot = validate_lot_size(lot_size)
    if not isinstance(rule, dict):
        raise ValueError("sampling rule must be a mapping, got %r" % (rule,))
    mode = rule.get("mode")
    if mode not in SAMPLE_MODES:
        raise ValueError("sampling mode must be one of %r, got %r" % (SAMPLE_MODES, mode))
    if mode == "all":
        return lot
    if mode == "fixed":
        if "size" not in rule:
            raise ValueError("a fixed sampling rule needs a 'size'")
        size = _count("sample size", rule["size"])
        if size < 1:
            raise ValueError("a fixed sample must be at least one device, got %d" % size)
        if size > lot:
            raise ValueError(
                "a sample of %d cannot be drawn from a lot of %d" % (size, lot)
            )
        return size
    percent = _real("sampling percent", rule.get("percent"))
    if percent <= 0.0 or percent > 100.0:
        raise ValueError("sampling percent must lie in (0, 100], got %g" % percent)
    minimum = _count("sampling minimum", rule.get("minimum", 1))
    if minimum < 1:
        raise ValueError("a sampling minimum must be at least one device")
    if minimum > lot:
        raise ValueError(
            "a sampling minimum of %d cannot be drawn from a lot of %d" % (minimum, lot)
        )
    raw = lot * percent / 100.0
    size = int(math.ceil(raw - CEIL_TOLERANCE))
    if size < minimum:
        size = minimum
    if size > lot:
        size = lot
    return size


def within_limit(measured, limit, direction):
    """Return True when a measured value sits inside its declared limit."""
    value = _real("measured value", measured)
    bound = _real("limit", limit)
    if direction not in LIMIT_DIRECTIONS:
        raise ValueError(
            "limit direction must be one of %r, got %r" % (LIMIT_DIRECTIONS, direction)
        )
    if direction == "max":
        return value <= bound + LIMIT_TOLERANCE
    if direction == "min":
        return value >= bound - LIMIT_TOLERANCE
    if bound < 0.0:
        raise ValueError("an abs-delta limit must be non-negative, got %g" % bound)
    return abs(value) <= bound + LIMIT_TOLERANCE


def evaluate_measurement(measurement):
    """Return the record of one measured parameter against its limit.

    measurement keys: parameter, measured, limit, direction.
    """
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    for key in ("parameter", "measured", "limit", "direction"):
        if key not in measurement:
            raise ValueError("measurement missing required key '%s'" % key)
    parameter = measurement["parameter"]
    if not isinstance(parameter, str) or not parameter.strip():
        raise ValueError("measurement parameter must be a non-empty name")
    ok = within_limit(measurement["measured"], measurement["limit"], measurement["direction"])
    return {
        "parameter": parameter.strip(),
        "measured": _real("measured value", measurement["measured"]),
        "limit": _real("limit", measurement["limit"]),
        "direction": measurement["direction"],
        "within_limit": ok,
    }


def evaluate_characteristic(characteristic):
    """Return the record of the thermistor characteristic against its tolerances.

    characteristic keys: nominal_resistance_ohm, resistance_tolerance_percent,
    nominal_beta_kelvin, beta_tolerance_percent, measured_resistance_ohm and a
    two_point mapping (low_ohm, low_temperature_c, high_ohm,
    high_temperature_c). An optional check_temperature_c asks for the
    resistance the derived characteristic predicts at another temperature.
    """
    if not isinstance(characteristic, dict):
        raise ValueError("characteristic must be a mapping, got %r" % (characteristic,))
    required = (
        "nominal_resistance_ohm",
        "resistance_tolerance_percent",
        "nominal_beta_kelvin",
        "beta_tolerance_percent",
        "measured_resistance_ohm",
        "two_point",
    )
    for key in required:
        if key not in characteristic:
            raise ValueError("characteristic missing required key '%s'" % key)
    nominal_r = _positive("nominal resistance", characteristic["nominal_resistance_ohm"])
    tol_r = _positive(
        "resistance tolerance", characteristic["resistance_tolerance_percent"]
    )
    nominal_beta = _positive("nominal beta", characteristic["nominal_beta_kelvin"])
    tol_beta = _positive("beta tolerance", characteristic["beta_tolerance_percent"])
    measured_r = _positive("measured resistance", characteristic["measured_resistance_ohm"])
    two_point = characteristic["two_point"]
    if not isinstance(two_point, dict):
        raise ValueError("two_point must be a mapping, got %r" % (two_point,))
    for key in ("low_ohm", "low_temperature_c", "high_ohm", "high_temperature_c"):
        if key not in two_point:
            raise ValueError("two_point missing required key '%s'" % key)
    derived_beta = derive_beta_constant(
        two_point["low_ohm"],
        two_point["low_temperature_c"],
        two_point["high_ohm"],
        two_point["high_temperature_c"],
    )
    resistance_deviation = relative_deviation_percent(measured_r, nominal_r)
    beta_deviation = relative_deviation_percent(derived_beta, nominal_beta)
    resistance_ok = within_limit(resistance_deviation, tol_r, "abs-delta")
    beta_ok = within_limit(beta_deviation, tol_beta, "abs-delta")
    reference_c = characteristic.get("reference_temperature_c", REFERENCE_TEMPERATURE_C)
    record = {
        "nominal_resistance_ohm": nominal_r,
        "measured_resistance_ohm": measured_r,
        "resistance_deviation_percent": resistance_deviation,
        "resistance_within_tolerance": resistance_ok,
        "nominal_beta_kelvin": nominal_beta,
        "derived_beta_kelvin": derived_beta,
        "beta_deviation_percent": beta_deviation,
        "beta_within_tolerance": beta_ok,
        "findings": [],
    }
    if "check_temperature_c" in characteristic:
        record["predicted_resistance_ohm"] = predict_resistance(
            measured_r,
            derived_beta,
            characteristic["check_temperature_c"],
            reference_c,
        )
        record["check_temperature_c"] = _real(
            "check temperature", characteristic["check_temperature_c"]
        )
    if not resistance_ok:
        record["findings"].append(
            "reference resistance deviates %.3f%% against a %.3f%% tolerance"
            % (resistance_deviation, tol_r)
        )
    if not beta_ok:
        record["findings"].append(
            "derived beta constant deviates %.3f%% against a %.3f%% tolerance"
            % (beta_deviation, tol_beta)
        )
    record["acceptable"] = not record["findings"]
    return record


def matrix_coverage(entries):
    """Return the coverage record of a declared matrix against the required groups."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of matrix rows")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        group = entry.get("group")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("entries[%d] needs a non-empty 'group'" % index)
        group = group.strip()
        if group in seen and group not in duplicates:
            duplicates.append(group)
        if group not in seen:
            seen.append(group)
        if group not in REQUIRED_TEST_GROUPS and group not in unknown:
            unknown.append(group)
    missing = [g for g in REQUIRED_TEST_GROUPS if g not in seen]
    return {
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def row_verdict(entry, lot_size):
    """Return the verdict record for one row of the thermistor matrix.

    entry keys: group, method, sampling, failures, accept_number and an
    optional measurements list.
    """
    if not isinstance(entry, dict):
        raise ValueError("a matrix row must be a mapping, got %r" % (entry,))
    for key in ("group", "method", "sampling", "failures", "accept_number"):
        if key not in entry:
            raise ValueError("matrix row missing required key '%s'" % key)
    group = entry["group"]
    if not isinstance(group, str) or not group.strip():
        raise ValueError("matrix row needs a non-empty 'group'")
    method = entry["method"]
    if not isinstance(method, str) or not method.strip():
        raise ValueError("matrix row needs a non-empty 'method' reference")
    sample_size = resolve_sample_size(entry["sampling"], lot_size)
    failures = _count("failures", entry["failures"])
    accept_number = _count("accept_number", entry["accept_number"])
    name = group.strip()
    if failures > sample_size:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d" % (name, failures, sample_size)
        )
    if accept_number > sample_size:
        raise ValueError(
            "row '%s' has an accept number of %d for a sample of %d"
            % (name, accept_number, sample_size)
        )
    measurements = entry.get("measurements") or []
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("row measurements must be a sequence")
    records = [evaluate_measurement(m) for m in measurements]
    out_of_limit = [r["parameter"] for r in records if not r["within_limit"]]
    count_accepted = failures <= accept_number
    accepted = count_accepted and not out_of_limit
    findings = []
    if not count_accepted:
        findings.append(
            "row '%s' took %d failures against an accept number of %d"
            % (name, failures, accept_number)
        )
    for parameter in out_of_limit:
        findings.append("row '%s' parameter '%s' is outside its limit" % (name, parameter))
    marginal = accepted and accept_number > 0 and failures == accept_number
    return {
        "group": name,
        "method": method.strip(),
        "sample_size": sample_size,
        "failures": failures,
        "accept_number": accept_number,
        "measurements": records,
        "accepted": accepted,
        "marginal": marginal,
        "findings": findings,
    }


def assess_thermistor_test_table(spec):
    """Run the full Table 8-8 thermistor procurement matrix assessment.

    spec keys: lot_size, entries (the declared matrix rows) and an optional
    characteristic mapping for the device's own resistance and beta
    tolerances.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_size = validate_lot_size(spec["lot_size"])
    coverage = matrix_coverage(spec["entries"])
    rows = [row_verdict(entry, lot_size) for entry in spec["entries"]]
    findings = []
    for group in coverage["missing"]:
        findings.append("required test group '%s' is absent from the matrix" % group)
    for group in coverage["duplicated"]:
        findings.append("test group '%s' is declared more than once" % group)
    characteristic = None
    if spec.get("characteristic") is not None:
        characteristic = evaluate_characteristic(spec["characteristic"])
        findings.extend(characteristic["findings"])
    for row in rows:
        findings.extend(row["findings"])
    advisories = [
        "row '%s' used its accept number in full" % row["group"]
        for row in rows
        if row["marginal"]
    ]
    rejecting = [row["group"] for row in rows if not row["accepted"]]
    accepted = not findings
    return {
        "lot_size": lot_size,
        "coverage": coverage,
        "characteristic": characteristic,
        "rows": rows,
        "rejecting_groups": rejecting,
        "total_devices_tested": sum(row["sample_size"] for row in rows),
        "accepted": accepted,
        "disposition": "accept" if accepted else "hold",
        "findings": findings,
        "advisories": advisories,
    }

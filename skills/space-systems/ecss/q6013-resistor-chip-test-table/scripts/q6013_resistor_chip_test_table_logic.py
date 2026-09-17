"""Resistor chip test-matrix evaluation for a commercial EEE lot.

Anchor: ECSS-Q-ST-60-13C Table 8-7 (the test matrix applied to resistor
chips: which test groups are run, by what method, on what sample of the
lot, and against which acceptance limits). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the lot the matrix is offered against. A sample is never
   larger than the lot it came from, so a zero or negative lot size is an
   input error rather than a degenerate case to be clamped.
2. Check the declared matrix covers every test group a resistor chip
   owes, and that no group is declared twice under two methods. A
   duplicated group is two programmes, and the weaker one would
   otherwise decide the lot.
3. Resolve each row's sample size from its rule: the whole lot, a fixed
   sample, or a percentage of the lot with a floor. The percentage is
   rounded up to whole devices, with the representation error of the
   product absorbed before the rounding so a sample landing exactly on
   an integer does not gain a device.
4. Judge each row twice. The count path is failures against the accept
   number. The parameter path is the resistor's own measurands --
   resistance against its tolerance band, temperature coefficient,
   insulation resistance, dielectric withstanding voltage and noise --
   each against its limit in the direction that limit is written in.
5. Hold the lot when ANY row rejects. Rows are not averaged, and a row
   that used its accept number exactly accepts but is reported as
   marginal.
"""

import math

__all__ = [
    "CEIL_TOLERANCE",
    "LIMIT_TOLERANCE",
    "REQUIRED_TEST_GROUPS",
    "LIMIT_DIRECTIONS",
    "SAMPLE_MODES",
    "validate_lot_size",
    "resolve_sample_size",
    "resistance_tolerance_band",
    "within_tolerance_band",
    "temperature_coefficient_ppm",
    "within_limit",
    "evaluate_measurement",
    "matrix_coverage",
    "row_verdict",
    "assess_resistor_chip_test_table",
]

# A percentage of an integer lot is a binary floating-point product, so a
# sample that should land on a whole device can land a few units in the
# last place above it. Absorb that here, before the rounding up.
CEIL_TOLERANCE = 1e-9

# A measured value exactly on its declared limit is inside it; the
# equality is a representation question, not an engineering one.
LIMIT_TOLERANCE = 1e-9

# The groups a resistor chip matrix covers before any row verdict means
# anything. A matrix missing one is incomplete however well its other
# rows performed.
REQUIRED_TEST_GROUPS = (
    "visual-inspection",
    "dimension-check",
    "resistance-measurement",
    "temperature-coefficient-of-resistance",
    "short-time-overload",
    "insulation-resistance",
    "dielectric-withstanding-voltage",
    "thermal-shock",
    "humidity-steady-state",
    "life-test",
    "terminal-strength",
    "destructive-physical-analysis",
)

# How a declared limit is read: an upper bound, a lower bound, or a bound
# on the magnitude of a change that may move either way.
LIMIT_DIRECTIONS = ("max", "min", "abs-delta")

# How a row's sample is drawn from the lot.
SAMPLE_MODES = ("all", "fixed", "percent")

# A row that consumed its whole accept number still accepts, but it is
# reported as marginal: the next build of the same part is the one that
# crosses.
MARGINAL_FRACTION = 1.0


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
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


def resolve_sample_size(rule, lot_size):
    """Return the whole-device sample size a row's sampling rule resolves to.

    rule keys: mode ('all', 'fixed' or 'percent'); size for a fixed
    sample; percent with an optional minimum for a percentage of the lot.
    A percentage resolves upward to whole devices because half a chip
    cannot be tested, and never above the lot it is drawn from.
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
            raise ValueError("a sample of %d cannot be drawn from a lot of %d" % (size, lot))
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


def resistance_tolerance_band(nominal_ohms, tolerance_percent):
    """Return the (low, high) resistance band a chip's marking permits.

    nominal_ohms must be strictly positive: a resistor with no nominal
    value has no band. tolerance_percent must lie in (0, 100); a chip
    whose band reaches zero ohms is not a resistor specification.
    """
    nominal = _real("nominal_ohms", nominal_ohms)
    if nominal <= 0.0:
        raise ValueError("nominal_ohms must be strictly positive, got %g" % nominal)
    tolerance = _real("tolerance_percent", tolerance_percent)
    if tolerance <= 0.0 or tolerance >= 100.0:
        raise ValueError("tolerance_percent must lie in (0, 100), got %g" % tolerance)
    span = nominal * tolerance / 100.0
    return (nominal - span, nominal + span)


def within_tolerance_band(measured_ohms, nominal_ohms, tolerance_percent):
    """Return True when a measured resistance sits inside its marked band.

    The band edges are absorbed by LIMIT_TOLERANCE, scaled by the nominal
    value, so a chip measuring exactly at an edge is inside the band on
    every platform rather than on the ones whose product rounds down.
    """
    value = _real("measured_ohms", measured_ohms)
    low, high = resistance_tolerance_band(nominal_ohms, tolerance_percent)
    slack = LIMIT_TOLERANCE * max(1.0, abs(float(nominal_ohms)))
    return (low - slack) <= value <= (high + slack)


def temperature_coefficient_ppm(reference_ohms, measured_ohms, reference_c, measured_c):
    """Return the temperature coefficient of resistance in ppm per kelvin.

    The coefficient is the fractional change in resistance divided by the
    temperature change that produced it, expressed in parts per million.
    A zero or negative reference resistance has no fraction to take, and
    two measurements at the same temperature give no coefficient at all,
    so both raise rather than returning an infinity.
    """
    r_ref = _real("reference_ohms", reference_ohms)
    if r_ref <= 0.0:
        raise ValueError("reference_ohms must be strictly positive, got %g" % r_ref)
    r_meas = _real("measured_ohms", measured_ohms)
    if r_meas < 0.0:
        raise ValueError("measured_ohms must be non-negative, got %g" % r_meas)
    t_ref = _real("reference_c", reference_c)
    t_meas = _real("measured_c", measured_c)
    delta_t = t_meas - t_ref
    if delta_t == 0.0:
        raise ValueError(
            "the two measurements are at the same temperature, so no coefficient exists"
        )
    return ((r_meas - r_ref) / r_ref) / delta_t * 1.0e6


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
    ok = within_limit(
        measurement["measured"], measurement["limit"], measurement["direction"]
    )
    return {
        "parameter": parameter.strip(),
        "measured": _real("measured value", measurement["measured"]),
        "limit": _real("limit", measurement["limit"]),
        "direction": measurement["direction"],
        "within_limit": ok,
    }


def matrix_coverage(entries):
    """Return the coverage record of a declared matrix against the required groups."""
    if isinstance(entries, (str, bytes)) or not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of matrix rows, got %r" % (entries,))
    if not entries:
        raise ValueError("entries must carry at least one matrix row")
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
        if group in seen:
            if group not in duplicates:
                duplicates.append(group)
        else:
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
    """Return the verdict record for one row of the resistor chip matrix.

    entry keys: group, method, sampling, failures, accept_number, an
    optional measurements list, and an optional resistance record with
    'measured_ohms', 'nominal_ohms' and 'tolerance_percent'.
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
    group = group.strip()
    sample_size = resolve_sample_size(entry["sampling"], lot_size)
    failures = _count("failures", entry["failures"])
    accept_number = _count("accept_number", entry["accept_number"])
    if failures > sample_size:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d" % (group, failures, sample_size)
        )
    if accept_number > sample_size:
        raise ValueError(
            "row '%s' has an accept number of %d for a sample of %d"
            % (group, accept_number, sample_size)
        )
    measurements = entry.get("measurements") or []
    if isinstance(measurements, (str, bytes)) or not isinstance(measurements, (list, tuple)):
        raise ValueError("row measurements must be a sequence")
    records = [evaluate_measurement(m) for m in measurements]
    out_of_limit = [r["parameter"] for r in records if not r["within_limit"]]
    resistance = entry.get("resistance")
    resistance_in_band = None
    if resistance is not None:
        if not isinstance(resistance, dict):
            raise ValueError("row resistance record must be a mapping")
        for key in ("measured_ohms", "nominal_ohms", "tolerance_percent"):
            if key not in resistance:
                raise ValueError("row resistance record missing '%s'" % key)
        resistance_in_band = within_tolerance_band(
            resistance["measured_ohms"],
            resistance["nominal_ohms"],
            resistance["tolerance_percent"],
        )
    count_accepted = failures <= accept_number
    accepted = count_accepted and not out_of_limit and resistance_in_band is not False
    findings = []
    if not count_accepted:
        findings.append(
            "row '%s' took %d failures against an accept number of %d"
            % (group, failures, accept_number)
        )
    for parameter in out_of_limit:
        findings.append("row '%s' parameter '%s' is outside its limit" % (group, parameter))
    if resistance_in_band is False:
        findings.append("row '%s' measured resistance is outside its marked band" % group)
    marginal = accepted and accept_number > 0 and failures >= int(
        math.ceil(accept_number * MARGINAL_FRACTION)
    )
    return {
        "group": group,
        "method": method.strip(),
        "sample_size": sample_size,
        "failures": failures,
        "accept_number": accept_number,
        "measurements": records,
        "resistance_in_band": resistance_in_band,
        "accepted": accepted,
        "marginal": marginal,
        "findings": findings,
    }


def assess_resistor_chip_test_table(spec):
    """Run the full Table 8-7 resistor chip matrix assessment.

    spec keys: lot_size and entries (the declared matrix rows). Returns
    the coverage record, every row verdict, the rejecting groups, the
    total devices the programme consumes, a flat findings list, the
    marginal-row advisories, and an accept-or-hold disposition.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
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
        "rows": rows,
        "rejecting_groups": rejecting,
        "total_devices_tested": sum(row["sample_size"] for row in rows),
        "accepted": accepted,
        "disposition": "accept" if accepted else "hold",
        "findings": findings,
        "advisories": advisories,
    }

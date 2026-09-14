"""Ceramic capacitor chip test-matrix evaluation for a commercial EEE lot.

Anchor: ECSS-Q-ST-60-13C Table 8-1 (the test matrix applied to ceramic
capacitor chips: which test groups are run, on what sample of the lot, and
against which measured limits). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the lot the matrix is offered against. A sample can never be
   drawn larger than the lot it came from, so a zero or negative lot size is
   an input error rather than a degenerate case to be clamped.
2. Check the declared matrix covers every required test group for a ceramic
   chip, and that no group is declared twice under two different methods --
   a duplicated group is two programmes, not one, and the weaker of the two
   would otherwise decide the lot.
3. Resolve each row's sample size from its declared rule: the whole lot, a
   fixed sample, or a percentage of the lot with a floor. The percentage is
   rounded up to a whole device, with the representation error of the
   product absorbed before the rounding so a sample that lands exactly on an
   integer does not become one device larger.
4. Take each row's failures against its accept number, and each row's
   measured parameters -- capacitance drift, dissipation factor, insulation
   resistance, dielectric withstanding voltage -- against its limit in the
   direction that limit is written in.
5. Hold the lot when ANY row rejects. Rows are not averaged together, and a
   row that used its accept number exactly is reported as marginal instead
   of as a bare pass.
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
    "within_limit",
    "evaluate_measurement",
    "matrix_coverage",
    "row_verdict",
    "assess_ceramic_chip_test_table",
]

# Sample sizes come from a percentage of an integer lot, so the product can
# land a few ULPs above a whole device. Absorb that here, before the rounding
# up, instead of by relaxing the declared percentage.
CEIL_TOLERANCE = 1e-9

# Measured parameters are compared with a declared limit; an exact equality
# at the limit is a representation question, not an engineering one.
LIMIT_TOLERANCE = 1e-9

# The test groups a ceramic chip matrix has to cover before any row verdict
# means anything. A matrix missing one of these is incomplete, however well
# the rows it does carry perform.
REQUIRED_TEST_GROUPS = (
    "visual-inspection",
    "dimension-check",
    "electrical-measurement",
    "dielectric-withstanding-voltage",
    "thermal-shock",
    "humidity-steady-state",
    "life-test",
    "terminal-strength",
    "destructive-physical-analysis",
)

# How a declared limit is read: an upper bound, a lower bound, or a bound on
# the magnitude of a drift that may move either way.
LIMIT_DIRECTIONS = ("max", "min", "abs-delta")

# How a row's sample is drawn from the lot.
SAMPLE_MODES = ("all", "fixed", "percent")

# A row that consumed this share of its accept number still accepts, but it
# is reported as marginal: the next build of the same part is the one that
# will cross.
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

    rule keys: mode ('all', 'fixed' or 'percent'); size for a fixed sample;
    percent and optional minimum for a percentage of the lot.
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
    minimum = rule.get("minimum", 1)
    minimum = _count("sampling minimum", minimum)
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
    """Return the verdict record for one row of the ceramic chip matrix.

    entry keys: group, method, sampling (rule), failures, accept_number and
    an optional measurements list.
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
    if failures > sample_size:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d"
            % (group.strip(), failures, sample_size)
        )
    if accept_number > sample_size:
        raise ValueError(
            "row '%s' has an accept number of %d for a sample of %d"
            % (group.strip(), accept_number, sample_size)
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
            % (group.strip(), failures, accept_number)
        )
    for parameter in out_of_limit:
        findings.append("row '%s' parameter '%s' is outside its limit" % (group.strip(), parameter))
    marginal = accepted and accept_number > 0 and failures >= int(
        math.ceil(accept_number * MARGINAL_FRACTION)
    )
    return {
        "group": group.strip(),
        "method": method.strip(),
        "sample_size": sample_size,
        "failures": failures,
        "accept_number": accept_number,
        "measurements": records,
        "accepted": accepted,
        "marginal": marginal,
        "findings": findings,
    }


def assess_ceramic_chip_test_table(spec):
    """Run the full Table 8-1 ceramic chip matrix assessment.

    spec keys: lot_size, entries (the declared matrix rows).
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

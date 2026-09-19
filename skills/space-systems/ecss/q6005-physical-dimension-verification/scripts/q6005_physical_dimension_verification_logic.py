"""Physical dimension verification of finished hybrid packages.

Anchor: ECSS-Q-ST-60-05C clause 10.3.8 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the limits from the drawing, not from the nominal. A tolerance
   is two numbers and they need not be equal: a dimension that may grow
   by a little and shrink by a lot has an asymmetric band, and folding
   it into a single plus-or-minus moves one of the two limits.
2. Grade the reading against the limits with its own uncertainty in
   hand. A value that sits inside a limit by less than the measurement
   uncertainty has not been shown to conform; it is indeterminate, and
   calling it a pass hands the decision to the noise in the gauge.
3. Check the gauge before the part. If the expanded uncertainty is a
   large fraction of the tolerance band, the instrument cannot resolve
   the requirement at all, and every result it produced is a statement
   about the instrument.
4. Fit the package to the host at its worst case, not at its nominal.
   The site has to accept the largest package the drawing permits, with
   the keep-out clearance still intact, or the assembly that passes
   incoming inspection is the one that will not go in.
5. Accumulate terminal position along the row. A per-pitch tolerance
   does not stay per-pitch: over a long row it accumulates, worst case
   linearly and statistically as the square root of the span, and the
   far terminal is the one that misses its pad.

Stdlib only, offline, deterministic.
"""

import math

# Least ratio of tolerance band to the full uncertainty interval that
# still leaves the gauge able to resolve the requirement.
MIN_GAUGE_CAPABILITY_RATIO = 4.0

ACCUMULATION_METHODS = ("worst-case", "statistical")

WITHIN = "within-limits"
INDETERMINATE = "indeterminate"
OUTSIDE = "outside-limits"

# A limit comparison is a subtraction of two decimals, so a reading that
# sits exactly on a limit can land a unit in the last place outside it.
# This absorbs that representation error without widening any tolerance.
COMPARISON_TOLERANCE = 1.0e-12

PASS = "package-accepted"
FAIL = "package-rejected"


def _number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _positive_number(label, value):
    value = _number(label, value)
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_number(label, value):
    value = _number(label, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _positive_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def validate_dimension(spec):
    """Validate one drawing dimension and return a normalized copy."""
    if not isinstance(spec, dict):
        raise ValueError("dimension must be a mapping")
    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("dimension needs a non-empty string name")
    plus = _non_negative_number("dimension %s plus_tolerance" % name, spec.get("plus_tolerance"))
    minus = _non_negative_number(
        "dimension %s minus_tolerance" % name, spec.get("minus_tolerance")
    )
    if plus == 0.0 and minus == 0.0:
        raise ValueError("dimension %s has a zero-width tolerance band" % name)
    return {
        "name": name,
        "nominal_mm": _positive_number(
            "dimension %s nominal_mm" % name, spec.get("nominal_mm")
        ),
        "plus_tolerance": plus,
        "minus_tolerance": minus,
        "measured_mm": _positive_number(
            "dimension %s measured_mm" % name, spec.get("measured_mm")
        ),
        "expanded_uncertainty": _non_negative_number(
            "dimension %s expanded_uncertainty" % name,
            spec.get("expanded_uncertainty", 0.0),
        ),
    }


def limits(spec):
    """Lower and upper drawing limits of a dimension."""
    norm = validate_dimension(spec)
    return (
        norm["nominal_mm"] - norm["minus_tolerance"],
        norm["nominal_mm"] + norm["plus_tolerance"],
    )


def tolerance_band(spec):
    """Full width of the band a dimension is allowed to occupy."""
    norm = validate_dimension(spec)
    return norm["plus_tolerance"] + norm["minus_tolerance"]


def deviation(spec):
    """Signed departure of the reading from the drawing nominal."""
    norm = validate_dimension(spec)
    return norm["measured_mm"] - norm["nominal_mm"]


def tolerance_utilization(spec):
    """Fraction of the side of the band the reading has consumed."""
    norm = validate_dimension(spec)
    delta = deviation(norm)
    if delta >= 0.0:
        allowance = norm["plus_tolerance"]
    else:
        allowance = norm["minus_tolerance"]
    if allowance == 0.0:
        return math.inf if delta != 0.0 else 0.0
    return abs(delta) / allowance


def gauge_capability_ratio(spec):
    """Tolerance band over the full uncertainty interval of the gauge."""
    norm = validate_dimension(spec)
    if norm["expanded_uncertainty"] == 0.0:
        return math.inf
    return tolerance_band(norm) / (2.0 * norm["expanded_uncertainty"])


def dimension_status(spec):
    """Grade a reading as within, outside, or not shown either way."""
    norm = validate_dimension(spec)
    lower, upper = limits(norm)
    value = norm["measured_mm"]
    uncertainty = norm["expanded_uncertainty"]
    if value < lower - COMPARISON_TOLERANCE or value > upper + COMPARISON_TOLERANCE:
        return OUTSIDE
    if uncertainty > 0.0 and (
        value - lower < uncertainty - COMPARISON_TOLERANCE
        or upper - value < uncertainty - COMPARISON_TOLERANCE
    ):
        return INDETERMINATE
    return WITHIN


def assess_dimension(spec):
    """Assess one drawing dimension and name what it found."""
    norm = validate_dimension(spec)
    lower, upper = limits(norm)
    status = dimension_status(norm)
    findings = []
    if status == OUTSIDE:
        findings.append("dimension-outside-the-drawing-limits")
    elif status == INDETERMINATE:
        findings.append("conformity-not-shown-inside-the-measurement-uncertainty")
    if gauge_capability_ratio(norm) < MIN_GAUGE_CAPABILITY_RATIO - COMPARISON_TOLERANCE:
        findings.append("gauge-uncertainty-too-large-for-the-tolerance-band")
    return {
        "name": norm["name"],
        "nominal_mm": norm["nominal_mm"],
        "measured_mm": norm["measured_mm"],
        "lower_limit_mm": lower,
        "upper_limit_mm": upper,
        "deviation_mm": deviation(norm),
        "tolerance_band_mm": tolerance_band(norm),
        "tolerance_utilization": tolerance_utilization(norm),
        "gauge_capability_ratio": gauge_capability_ratio(norm),
        "status": status,
        "findings": findings,
    }


def worst_case_extent(spec):
    """Largest value the drawing permits a dimension to take."""
    norm = validate_dimension(spec)
    return norm["nominal_mm"] + norm["plus_tolerance"]


def envelope_clearance(package_extent_mm, site_extent_mm, keep_out_mm):
    """Clearance left in the host site once the package is at its largest."""
    package = _positive_number("package_extent_mm", package_extent_mm)
    site = _positive_number("site_extent_mm", site_extent_mm)
    keep_out = _non_negative_number("keep_out_mm", keep_out_mm)
    return site - package - 2.0 * keep_out


def accumulated_position_tolerance(pitch_tolerance_mm, terminal_count, method):
    """Position tolerance accumulated along a row of terminals."""
    pitch_tol = _positive_number("pitch_tolerance_mm", pitch_tolerance_mm)
    count = _positive_integer("terminal_count", terminal_count)
    if method not in ACCUMULATION_METHODS:
        raise ValueError(
            "unknown accumulation method %r (expected one of %s)"
            % (method, ", ".join(ACCUMULATION_METHODS))
        )
    if count < 2:
        raise ValueError("a row needs at least two terminals to accumulate")
    spans = count - 1
    if method == "worst-case":
        return pitch_tol * spans
    return pitch_tol * math.sqrt(spans)


def validate_package(record):
    """Validate one package verification record and normalize it."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    dims = record.get("dimensions")
    if not isinstance(dims, list) or not dims:
        raise ValueError("unit %s needs a non-empty dimensions list" % unit_id)
    normalized = [validate_dimension(d) for d in dims]
    names = [d["name"] for d in normalized]
    if len(set(names)) != len(names):
        raise ValueError("unit %s repeats a dimension name" % unit_id)
    method = record.get("accumulation_method", "worst-case")
    if method not in ACCUMULATION_METHODS:
        raise ValueError(
            "unit %s has unknown accumulation_method %r" % (unit_id, method)
        )
    return {
        "id": unit_id,
        "dimensions": normalized,
        "body_extent_name": record.get("body_extent_name", names[0]),
        "site_extent_mm": _positive_number(
            "unit %s site_extent_mm" % unit_id, record.get("site_extent_mm")
        ),
        "keep_out_mm": _non_negative_number(
            "unit %s keep_out_mm" % unit_id, record.get("keep_out_mm", 0.0)
        ),
        "terminal_count": _positive_integer(
            "unit %s terminal_count" % unit_id, record.get("terminal_count")
        ),
        "pitch_tolerance_mm": _positive_number(
            "unit %s pitch_tolerance_mm" % unit_id, record.get("pitch_tolerance_mm")
        ),
        "host_position_allowance_mm": _positive_number(
            "unit %s host_position_allowance_mm" % unit_id,
            record.get("host_position_allowance_mm"),
        ),
        "accumulation_method": method,
    }


def body_dimension(record):
    """The dimension a package presents to the host site."""
    norm = validate_package(record)
    for dim in norm["dimensions"]:
        if dim["name"] == norm["body_extent_name"]:
            return dim
    raise ValueError(
        "unit %s names body extent %r which is not a measured dimension"
        % (norm["id"], norm["body_extent_name"])
    )


def check_fit(record):
    """Findings about the package fitting its host site at worst case."""
    norm = validate_package(record)
    clearance = envelope_clearance(
        worst_case_extent(body_dimension(norm)),
        norm["site_extent_mm"],
        norm["keep_out_mm"],
    )
    if clearance < -COMPARISON_TOLERANCE:
        return ["worst-case-envelope-exceeds-the-host-site"]
    return []


def check_terminal_accumulation(record):
    """Findings about position accumulated along the terminal row."""
    norm = validate_package(record)
    accumulated = accumulated_position_tolerance(
        norm["pitch_tolerance_mm"],
        norm["terminal_count"],
        norm["accumulation_method"],
    )
    allowance = norm["host_position_allowance_mm"]
    if accumulated > allowance * (1.0 + COMPARISON_TOLERANCE):
        return ["accumulated-terminal-position-exceeds-the-host-allowance"]
    return []


def assess_package(record):
    """Assess one finished package against clause 10.3.8."""
    norm = validate_package(record)
    dimension_reports = [assess_dimension(d) for d in norm["dimensions"]]
    findings = []
    for report in dimension_reports:
        findings.extend(report["findings"])
    findings.extend(check_fit(norm))
    findings.extend(check_terminal_accumulation(norm))
    ordered = []
    for finding in findings:
        if finding not in ordered:
            ordered.append(finding)
    return {
        "id": norm["id"],
        "dimensions": dimension_reports,
        "worst_utilization": max(
            r["tolerance_utilization"] for r in dimension_reports
        ),
        "envelope_clearance_mm": envelope_clearance(
            worst_case_extent(body_dimension(norm)),
            norm["site_extent_mm"],
            norm["keep_out_mm"],
        ),
        "accumulated_position_mm": accumulated_position_tolerance(
            norm["pitch_tolerance_mm"],
            norm["terminal_count"],
            norm["accumulation_method"],
        ),
        "host_position_allowance_mm": norm["host_position_allowance_mm"],
        "findings": ordered,
        "disposition": FAIL if ordered else PASS,
    }


def assess_verification_lot(records):
    """Run the clause 10.3.8 verification over a measured sample."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_package(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if r["disposition"] == FAIL]
    return {
        "units": results,
        "accepted_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "rejected_ids": rejected,
        "worst_utilization": max(r["worst_utilization"] for r in results),
        "tightest_clearance_mm": min(r["envelope_clearance_mm"] for r in results),
        "sample_accepted": not rejected,
    }


def dimensions_not_shown(record):
    """Dimensions the measurement could not decide either way."""
    norm = validate_package(record)
    return [d["name"] for d in norm["dimensions"] if dimension_status(d) == INDETERMINATE]

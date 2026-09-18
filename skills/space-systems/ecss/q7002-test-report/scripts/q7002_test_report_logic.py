"""Outgassing screening test report: conditions, results, uncertainties.

Anchor: ECSS-Q-ST-70-02C, the reporting clause of the thermal-vacuum
outgassing screening test (paraphrased into an implementable procedure;
no standard text is reproduced).

Procedure implemented here:

1. A screening report identifies what was tested tightly enough for
   someone else to obtain the same thing: designation, manufacturer,
   batch or lot, and the processing state the specimen was in. A trade
   name alone identifies a family, not a material.
2. It records the conditions the run was actually held at, not the
   conditions it was meant to be held at. Each condition has a window,
   and a value outside its window is reportable with a deviation behind
   it -- an out-of-window condition with no deviation on record is the
   defect the clause exists to catch.
3. It reports the results with an uncertainty. The components combine in
   quadrature into a combined standard uncertainty, and the expanded
   uncertainty is that figure times the coverage factor the report
   declares.
4. Value and uncertainty are reported at the same resolution. A value
   rounded coarser than its own uncertainty throws away the digits the
   uncertainty was computed for; an uncertainty far finer than the
   reporting step is arithmetic nobody can read off the report.
5. The report is reportable only when identification, conditions,
   results and uncertainty are all present and self-consistent.

Stdlib only, offline, deterministic.
"""

import math

IDENTIFICATION_FIELDS = (
    "report_id",
    "material_designation",
    "manufacturer",
    "batch_or_lot",
    "processing_state",
)

RESULT_FIELDS = (
    "total_mass_loss_pct",
    "cvcm_pct",
    "specimen_count",
)

# Condition windows as (nominal, half-width) in the field's own units.
CONDITION_WINDOWS = {
    "preconditioning_temperature_c": (23.0, 2.0),
    "preconditioning_humidity_pct": (50.0, 5.0),
    "specimen_temperature_c": (125.0, 1.0),
    "collector_temperature_c": (25.0, 1.0),
}

# Conditions held to a floor: the run has to last at least this long.
CONDITION_MINIMA = {
    "preconditioning_duration_h": 24.0,
    "test_duration_h": 24.0,
}

# Conditions held to a ceiling: the chamber has to be at least this good.
CONDITION_MAXIMA = {
    "chamber_pressure_pa": 1.0e-3,
}

CONDITION_FIELDS = (
    tuple(sorted(CONDITION_WINDOWS))
    + tuple(sorted(CONDITION_MINIMA))
    + tuple(sorted(CONDITION_MAXIMA))
)

# Results and uncertainties are reported to this many decimal places.
REPORT_DECIMALS = 2
REPORT_STEP_PCT = 0.01

DEFAULT_COVERAGE_FACTOR = 2.0
MIN_COVERAGE_FACTOR = 1.0
MAX_COVERAGE_FACTOR = 3.0

MIN_SPECIMEN_COUNT = 3

# Conditions and uncertainties are compared against windows built from
# decimal literals, so a value sitting exactly on a window edge can land
# a few units in the last place past it. This tolerance absorbs that
# representation error only; no window is ever widened.
CONDITION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def missing_identification(report):
    """Identification fields absent or blank in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    missing = []
    for field in IDENTIFICATION_FIELDS:
        value = report.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return missing


def missing_conditions(report):
    """Condition fields absent or non-numeric in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    missing = []
    for field in CONDITION_FIELDS:
        value = report.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            missing.append(field)
    return missing


def missing_results(report):
    """Result fields absent or non-numeric in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    missing = []
    for field in RESULT_FIELDS:
        value = report.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            missing.append(field)
    return missing


def condition_within_window(field, value):
    """True when one condition value sits inside the window it is held to."""
    if field in CONDITION_WINDOWS:
        nominal, half_width = CONDITION_WINDOWS[field]
        val = _numeric(field, value)
        return abs(val - nominal) <= half_width + CONDITION_TOLERANCE
    if field in CONDITION_MINIMA:
        return _numeric(field, value) >= CONDITION_MINIMA[field] - CONDITION_TOLERANCE
    if field in CONDITION_MAXIMA:
        return _numeric(field, value) <= CONDITION_MAXIMA[field] + CONDITION_TOLERANCE
    raise ValueError("unknown condition field %r" % (field,))


def out_of_window_conditions(report):
    """Condition fields whose recorded value sits outside its window."""
    present = set(CONDITION_FIELDS) - set(missing_conditions(report))
    return [f for f in CONDITION_FIELDS
            if f in present and not condition_within_window(f, report[f])]


def combined_standard_uncertainty(components):
    """Combine uncertainty components in quadrature."""
    if not isinstance(components, dict) or not components:
        raise ValueError("components must be a non-empty mapping")
    total = 0.0
    for name, value in components.items():
        _text("uncertainty component name", name)
        contribution = _numeric("uncertainty component %s" % name, value, 0.0)
        total += contribution * contribution
    return math.sqrt(total)


def expanded_uncertainty(combined, coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Expanded uncertainty from the combined figure and a coverage factor."""
    u_c = _numeric("combined", combined, 0.0)
    k = _numeric("coverage_factor", coverage_factor)
    if k < MIN_COVERAGE_FACTOR or k > MAX_COVERAGE_FACTOR:
        raise ValueError(
            "coverage_factor %r is outside the reportable range %r..%r"
            % (k, MIN_COVERAGE_FACTOR, MAX_COVERAGE_FACTOR)
        )
    return k * u_c


def round_to_report(value):
    """Round a percentage to the resolution the report is written at."""
    return round(_numeric("value", value), REPORT_DECIMALS)


def check_uncertainty_resolution(value, expanded):
    """Findings about the match between a value and its uncertainty."""
    val = _numeric("value", value, 0.0)
    exp = _numeric("expanded", expanded, 0.0)
    findings = []
    if exp > val + CONDITION_TOLERANCE:
        findings.append("expanded-uncertainty-exceeds-the-reported-value")
    if exp + CONDITION_TOLERANCE < REPORT_STEP_PCT / 2.0:
        findings.append("expanded-uncertainty-finer-than-the-reporting-step")
    return findings


def assess_test_report(report):
    """Assess one outgassing screening test report for reportability."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")

    findings = []
    missing_id = missing_identification(report)
    missing_cond = missing_conditions(report)
    missing_res = missing_results(report)
    if missing_id:
        findings.append("identification-incomplete")
    if missing_cond:
        findings.append("test-conditions-incomplete")
    if missing_res:
        findings.append("results-incomplete")

    deviations = report.get("deviations", [])
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence")
    deviation_fields = set()
    for item in deviations:
        if not isinstance(item, dict):
            raise ValueError("each deviation must be a mapping")
        deviation_fields.add(_text("deviation condition", item.get("condition")))
        _text("deviation justification", item.get("justification"))

    out_of_window = out_of_window_conditions(report)
    undeclared = [f for f in out_of_window if f not in deviation_fields]
    if out_of_window:
        findings.append("test-condition-outside-its-window")
    if undeclared:
        findings.append("out-of-window-condition-without-a-recorded-deviation")
    unused = sorted(deviation_fields - set(out_of_window))
    if unused:
        findings.append("deviation-recorded-for-an-in-window-condition")

    count = report.get("specimen_count")
    if isinstance(count, int) and not isinstance(count, bool):
        if count < MIN_SPECIMEN_COUNT:
            findings.append("fewer-specimens-than-the-method-requires")
    elif "specimen_count" not in missing_res:
        findings.append("specimen-count-is-not-a-whole-number")

    components = report.get("uncertainty_components_pct")
    combined = None
    expanded = None
    if not isinstance(components, dict) or not components:
        findings.append("uncertainty-budget-absent")
    else:
        combined = combined_standard_uncertainty(components)
        expanded = expanded_uncertainty(
            combined, report.get("coverage_factor", DEFAULT_COVERAGE_FACTOR)
        )
        if "cvcm_pct" not in missing_res:
            findings.extend(
                check_uncertainty_resolution(report["cvcm_pct"], expanded)
            )

    reported = {}
    for field in ("total_mass_loss_pct", "cvcm_pct"):
        if field not in missing_res:
            reported[field] = round_to_report(report[field])
    if expanded is not None:
        reported["expanded_uncertainty_pct"] = round_to_report(expanded)

    return {
        "report_id": report.get("report_id"),
        "missing_identification": missing_id,
        "missing_conditions": missing_cond,
        "missing_results": missing_res,
        "out_of_window_conditions": out_of_window,
        "undeclared_deviations": undeclared,
        "combined_standard_uncertainty_pct": combined,
        "expanded_uncertainty_pct": expanded,
        "reported_values": reported,
        "findings": findings,
        "reportable": not findings,
    }

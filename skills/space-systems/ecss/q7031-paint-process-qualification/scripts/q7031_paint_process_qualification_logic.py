#!/usr/bin/env python3
"""Qualification of a painting process and the facility that runs it.

Anchor: ECSS-Q-ST-70-31C, the Process control clause on process and facility
qualification. The procedure below is a paraphrased, implementable restatement
-- no verbatim standard text. Offline, deterministic, Python standard library
only.

A painting process is qualified as a whole -- material, parameters, facility
and the people operating it -- and the evidence is a coupon set sprayed under
the same conditions as the hardware. This module sizes the coupon set the
application owes, grades the facility environment including the dew-point
margin over the substrate, grades every process parameter against its
qualified window, checks operator currency, and dates the qualification.
"""

import math

__all__ = [
    "COUPON_KINDS",
    "BASE_COUPON_KINDS",
    "APPLICATION_COUPONS",
    "DEFAULT_DEW_POINT_MARGIN_C",
    "MINIMUM_COUPONS_PER_KIND",
    "parse_day",
    "add_months",
    "dew_point_c",
    "dew_point_margin_c",
    "required_coupon_kinds",
    "coupon_coverage_findings",
    "parameter_within_window",
    "process_parameter_findings",
    "environment_findings",
    "operator_currency_findings",
    "qualification_expiry_day",
    "assess_process_qualification",
    "assess_facility_set",
]

# A parameter sitting exactly on the edge of its qualified window is inside it,
# and a dew point computed through a logarithm lands a few ULP either side of a
# decimal margin depending on the maths library. These tolerances absorb that
# and nothing else; no qualified window is widened by them.
QUAL_REL_TOL = 1e-9
QUAL_ABS_TOL = 1e-12

# Magnus coefficients over water, in the form used for shop-floor dew point.
MAGNUS_A = 17.62
MAGNUS_B = 243.12

DEFAULT_DEW_POINT_MARGIN_C = 3.0
MINIMUM_COUPONS_PER_KIND = 3

COUPON_KINDS = (
    "adhesion",
    "dry-film-thickness",
    "thermo-optical",
    "outgassing",
    "thermal-cycling",
    "humidity-resistance",
    "surface-resistivity",
    "flexibility",
)

BASE_COUPON_KINDS = ("adhesion", "dry-film-thickness", "outgassing", "humidity-resistance")

# What the coating is for adds coupons on top of the base set.
APPLICATION_COUPONS = {
    "general-protective": (),
    "thermal-control": ("thermo-optical", "thermal-cycling"),
    "electrically-conductive": ("surface-resistivity", "thermal-cycling"),
}

PROCESS_PARAMETERS = (
    "spray_pressure_bar",
    "gun_distance_mm",
    "pass_count",
    "flash_off_minutes",
    "cure_temperature_c",
    "cure_duration_minutes",
)


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=QUAL_REL_TOL, abs_tol=QUAL_ABS_TOL)


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    return [31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31][month - 1]


def parse_day(label, text):
    """Parse a strict ISO calendar day into a comparable (year, month, day) tuple."""
    if not isinstance(text, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    parts = text.strip().split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) or len(parts[0]) != 4:
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    year, month, day = (int(p) for p in parts)
    if not 1 <= month <= 12:
        raise ValueError("%s has no month %d" % (label, month))
    if not 1 <= day <= _days_in_month(year, month):
        raise ValueError("%s has no day %d in month %d of %d" % (label, day, month, year))
    return (year, month, day)


def add_months(day, months):
    """Advance a calendar day by whole months, clamping to the shorter month.

    A qualification granted on the 31st expires on the last day of a 30-day
    month rather than rolling into the next one, which would silently extend
    the validity by a day.
    """
    if isinstance(months, bool) or not isinstance(months, int) or months < 0:
        raise ValueError("months must be a non-negative integer, got %r" % (months,))
    year, month, dom = day
    index = (year * 12 + (month - 1)) + months
    new_year, new_month = divmod(index, 12)
    new_month += 1
    return (new_year, new_month, min(dom, _days_in_month(new_year, new_month)))


def dew_point_c(air_temperature_c, relative_humidity_pct):
    """Dew point of the booth air, by the Magnus relation used on the shop floor."""
    temperature = _finite_number(air_temperature_c, "air_temperature_c")
    humidity = _finite_number(relative_humidity_pct, "relative_humidity_pct")
    if not -60.0 <= temperature <= 80.0:
        raise ValueError("air temperature %r is outside any paint booth" % (air_temperature_c,))
    if not 0.0 < humidity <= 100.0:
        raise ValueError("relative humidity must lie in (0,100], got %r" % (relative_humidity_pct,))
    gamma = math.log(humidity / 100.0) + (MAGNUS_A * temperature) / (MAGNUS_B + temperature)
    return (MAGNUS_B * gamma) / (MAGNUS_A - gamma)


def dew_point_margin_c(air_temperature_c, relative_humidity_pct, substrate_temperature_c):
    """How far the substrate sits above the dew point of the air around it.

    A substrate at or below the dew point is condensing, and paint applied onto
    condensate has no adhesion whatever the gun settings were.
    """
    substrate = _finite_number(substrate_temperature_c, "substrate_temperature_c")
    return substrate - dew_point_c(air_temperature_c, relative_humidity_pct)


def required_coupon_kinds(application):
    """Coupon kinds the qualification owes for this coating application."""
    if not isinstance(application, str) or not application.strip():
        raise ValueError("application must be a non-empty string")
    key = application.strip().lower()
    if key not in APPLICATION_COUPONS:
        raise ValueError("unrecognized coating application: %r" % (application,))
    return tuple(sorted(set(BASE_COUPON_KINDS) | set(APPLICATION_COUPONS[key])))


def coupon_coverage_findings(coupons, application, minimum_per_kind=MINIMUM_COUPONS_PER_KIND):
    """Findings about the coupon set backing the qualification."""
    if isinstance(minimum_per_kind, bool) or not isinstance(minimum_per_kind, int) \
            or minimum_per_kind < 1:
        raise ValueError("minimum_per_kind must be a positive integer, got %r" % (minimum_per_kind,))
    if not isinstance(coupons, dict):
        raise ValueError("coupons must be a mapping of kind to count, got %r" % type(coupons))
    for kind, count in coupons.items():
        if kind not in COUPON_KINDS:
            raise ValueError("unrecognized coupon kind: %r" % (kind,))
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("coupon count for %r must be a non-negative integer" % (kind,))
    findings = []
    for kind in required_coupon_kinds(application):
        count = coupons.get(kind, 0)
        if count == 0:
            findings.append("coupon-kind-absent:%s" % kind)
        elif count < minimum_per_kind:
            findings.append("coupon-count-short:%s" % kind)
    return sorted(findings)


def parameter_within_window(value, window, label="parameter"):
    """True when a process parameter sits inside its qualified window, edges included."""
    number = _finite_number(value, label)
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("%s window must be a low,high pair, got %r" % (label, window))
    low = _finite_number(window[0], "%s window low" % label)
    high = _finite_number(window[1], "%s window high" % label)
    if high < low:
        raise ValueError("%s window is inverted" % label)
    return _at_or_below(low, number) and _at_or_below(number, high)


def process_parameter_findings(parameters, windows):
    """Findings from every process parameter the qualification pins down."""
    if not isinstance(parameters, dict) or not isinstance(windows, dict):
        raise ValueError("parameters and windows must both be mappings")
    findings = []
    for name in PROCESS_PARAMETERS:
        window = windows.get(name)
        if window is None:
            findings.append("parameter-window-absent:%s" % name)
            continue
        if name not in parameters:
            findings.append("parameter-not-recorded:%s" % name)
            continue
        if not parameter_within_window(parameters[name], window, name):
            findings.append("parameter-outside-window:%s" % name)
    return sorted(findings)


def environment_findings(environment, envelope):
    """Findings about the booth environment during the qualification run."""
    if not isinstance(environment, dict) or not isinstance(envelope, dict):
        raise ValueError("environment and envelope must both be mappings")
    findings = []
    for key in ("air_temperature_c", "relative_humidity_pct", "air_velocity_m_s"):
        window = envelope.get(key)
        if window is None:
            findings.append("environment-window-absent:%s" % key)
            continue
        if key not in environment:
            findings.append("environment-not-recorded:%s" % key)
            continue
        if not parameter_within_window(environment[key], window, key):
            findings.append("environment-outside-window:%s" % key)

    cleanliness = environment.get("particulate_class")
    limit = envelope.get("particulate_class_limit")
    if cleanliness is None or limit is None:
        findings.append("particulate-class-not-verified")
    else:
        measured = _finite_number(cleanliness, "particulate_class")
        allowed = _finite_number(limit, "particulate_class_limit")
        if not _at_or_below(measured, allowed):
            findings.append("particulate-class-exceeded")

    if "substrate_temperature_c" in environment and "air_temperature_c" in environment \
            and "relative_humidity_pct" in environment:
        margin = dew_point_margin_c(
            environment["air_temperature_c"],
            environment["relative_humidity_pct"],
            environment["substrate_temperature_c"],
        )
        floor = _finite_number(
            envelope.get("dew_point_margin_c", DEFAULT_DEW_POINT_MARGIN_C), "dew_point_margin_c"
        )
        if not _at_or_below(floor, margin):
            findings.append("dew-point-margin-insufficient")
    else:
        findings.append("dew-point-margin-not-evaluated")
    return sorted(findings)


def operator_currency_findings(operators, reference_day, validity_months=24):
    """Findings about the people who sprayed the qualification coupons."""
    if not isinstance(operators, (list, tuple)) or not operators:
        raise ValueError("at least one qualified operator is required")
    reference = parse_day("reference_day", reference_day)
    findings = []
    for index, operator in enumerate(operators):
        if not isinstance(operator, dict):
            raise ValueError("operator %d must be a mapping" % index)
        identifier = operator.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("operator %d requires a non-empty id" % index)
        certified = parse_day("operator %s certified_day" % identifier, operator.get("certified_day"))
        expiry = add_months(certified, operator.get("validity_months", validity_months))
        if reference > expiry:
            findings.append("operator-certification-lapsed:%s" % identifier.strip())
    return sorted(findings)


def qualification_expiry_day(granted_day, validity_months):
    """Day the process qualification stops being current."""
    return add_months(parse_day("granted_day", granted_day), validity_months)


def assess_process_qualification(spec):
    """Grade one painting process and facility and issue its qualification state."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % type(spec))
    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("qualification requires a non-empty name")
    reference = spec.get("reference_day")
    findings = []
    findings.extend(coupon_coverage_findings(
        spec.get("coupons", {}),
        spec.get("application"),
        spec.get("minimum_coupons_per_kind", MINIMUM_COUPONS_PER_KIND),
    ))
    findings.extend(process_parameter_findings(
        spec.get("parameters", {}), spec.get("parameter_windows", {})
    ))
    findings.extend(environment_findings(
        spec.get("environment", {}), spec.get("environment_envelope", {})
    ))
    findings.extend(operator_currency_findings(
        spec.get("operators"), reference, spec.get("operator_validity_months", 24)
    ))
    expiry = qualification_expiry_day(
        spec.get("granted_day"), spec.get("validity_months", 36)
    )
    if parse_day("reference_day", reference) > expiry:
        findings.append("qualification-expired")

    findings = sorted(set(findings))
    blocking = [
        f for f in findings
        if f.startswith("coupon-kind-absent")
        or f.startswith("parameter-outside-window")
        or f.startswith("environment-outside-window")
        or f in ("dew-point-margin-insufficient", "particulate-class-exceeded",
                 "qualification-expired")
    ]
    if not findings:
        state = "qualified"
    elif blocking:
        state = "not-qualified"
    else:
        state = "conditionally-qualified"
    return {
        "name": name.strip(),
        "application": spec.get("application"),
        "required_coupons": required_coupon_kinds(spec.get("application")),
        "expiry_day": expiry,
        "findings": findings,
        "state": state,
        "qualified": state == "qualified",
    }


def assess_facility_set(specs):
    """Grade a set of process qualifications across facilities."""
    if not isinstance(specs, (list, tuple)) or not specs:
        raise ValueError("at least one qualification spec is required")
    results = [assess_process_qualification(item) for item in specs]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("qualification names must be unique within a set")
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "qualifications": results,
        "not_qualified": sorted(i["name"] for i in results if i["state"] == "not-qualified"),
        "open_findings": open_findings,
        "set_qualified": not open_findings,
    }

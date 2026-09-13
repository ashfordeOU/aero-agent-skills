#!/usr/bin/env python3
"""Emission-yield measurement temperature-range check.

Anchor: ECSS-E-ST-20-01C clause 9.4.1.4 (the supplier defines the
temperature range over which emission yield is measured, and the customer
approves it). Paraphrased into an implementable procedure; no standard
text is reproduced.

The clause makes the measurement range a two-party artefact: the supplier
states it, the customer approves it, and it only means something if it
actually brackets the temperatures the hardware sees in service. This
module turns that into a deterministic check:

  * normalise declared and predicted ranges from kelvin or celsius;
  * confirm the declared range envelops the predicted in-service range and
    report the margin (or the shortfall) at each end;
  * categorize the approval state from the supplier declaration date, the
    customer approval date and the declaration revision;
  * grade the measurement setpoints for endpoint anchoring and for gaps
    wider than the interpolation limit;
  * check the thermometry uncertainty against the span it has to resolve.

Boundary cases that are physically compliant -- a declared endpoint that
equals the in-service endpoint, a setpoint ladder whose accumulated step
lands a few units in the last place above the gap limit -- are absorbed by
a named representation tolerance, never by relaxing the engineering limit.

stdlib only, offline, deterministic.
"""

import datetime
import math

ABSOLUTE_ZERO_K = 0.0
KELVIN_AT_ZERO_CELSIUS = 273.15
TEMPERATURE_UNITS = ("K", "degC")

# Representation tolerance only: it exists so an accumulated float that
# physically equals a limit is not read as a violation. It is never a
# licence to widen the limit itself.
REL_TOL = 1e-9
ABS_TOL_K = 1e-9

DEFAULT_MAX_SETPOINT_GAP_K = 25.0
DEFAULT_ENDPOINT_TOLERANCE_K = 2.0
DEFAULT_THERMOMETRY_FRACTION = 0.02

APPROVAL_STATES = (
    "approved",
    "pending-customer-approval",
    "approval-superseded",
)


def _numeric(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, type(value)))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _not_below(value, limit):
    return value > limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL_K
    )


def to_kelvin(value, unit="K"):
    """Normalise a declared temperature to kelvin."""
    if unit not in TEMPERATURE_UNITS:
        raise ValueError("unknown temperature unit '%r' (expected K or degC)" % (unit,))
    value = _numeric(value, "temperature")
    kelvin = value if unit == "K" else value + KELVIN_AT_ZERO_CELSIUS
    if not _not_below(kelvin, ABSOLUTE_ZERO_K):
        raise ValueError("temperature %r K lies below absolute zero" % kelvin)
    return kelvin


def validate_temperature_range(spec):
    """Normalise one temperature range record to a (min_k, max_k) pair."""
    if not isinstance(spec, dict):
        raise ValueError("temperature range must be a mapping, got %r" % (type(spec),))
    unit = spec.get("unit", "K")
    if "min" not in spec or "max" not in spec:
        raise ValueError("temperature range needs both 'min' and 'max'")
    low = to_kelvin(spec["min"], unit)
    high = to_kelvin(spec["max"], unit)
    if high < low or math.isclose(high, low, rel_tol=REL_TOL, abs_tol=ABS_TOL_K):
        raise ValueError(
            "temperature range is empty or inverted: min %r K, max %r K" % (low, high)
        )
    return (low, high)


def range_span_k(spec):
    """Width of a temperature range in kelvin."""
    low, high = validate_temperature_range(spec)
    return high - low


def range_margins_k(declared, service):
    """Cold-end and hot-end margin of the declared range over the service range.

    A negative value is a shortfall: the declared range stops short of the
    temperature the hardware is predicted to reach at that end.
    """
    d_low, d_high = validate_temperature_range(declared)
    s_low, s_high = validate_temperature_range(service)
    return {"cold_margin_k": s_low - d_low, "hot_margin_k": d_high - s_high}


def envelops_service_range(declared, service):
    """True when the declared measurement range brackets the service range."""
    margins = range_margins_k(declared, service)
    cold_ok = _not_below(margins["cold_margin_k"], 0.0)
    hot_ok = _not_below(margins["hot_margin_k"], 0.0)
    return cold_ok and hot_ok


def _as_date(value, label):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("%s is not an ISO date: %s" % (label, exc))


def approval_state(record):
    """Categorize the two-party state of a declared measurement range.

    The supplier declaration is mandatory input: without it there is
    nothing to approve and the record is rejected. An approval older than
    the declaration revision it is meant to cover is superseded, not valid.
    """
    if not isinstance(record, dict):
        raise ValueError("approval record must be a mapping, got %r" % (type(record),))
    supplier = record.get("supplier_declaration_date")
    if supplier is None:
        raise ValueError("no supplier declaration date on record")
    declared_on = _as_date(supplier, "supplier_declaration_date")
    revision = record.get("revision_date")
    revised_on = _as_date(revision, "revision_date") if revision else declared_on
    if revised_on < declared_on:
        raise ValueError("revision date precedes the original declaration date")
    approval = record.get("customer_approval_date")
    if approval is None:
        return "pending-customer-approval"
    approved_on = _as_date(approval, "customer_approval_date")
    if approved_on < revised_on:
        return "approval-superseded"
    return "approved"


def setpoint_coverage(
    setpoints_k,
    declared,
    max_gap_k=DEFAULT_MAX_SETPOINT_GAP_K,
    endpoint_tolerance_k=DEFAULT_ENDPOINT_TOLERANCE_K,
):
    """Grade the measurement setpoints spanning the declared range."""
    if not isinstance(setpoints_k, (list, tuple)) or len(setpoints_k) < 2:
        raise ValueError("at least two measurement setpoints are required")
    gap_limit = _numeric(max_gap_k, "max_gap_k")
    if gap_limit <= 0.0:
        raise ValueError("max_gap_k must be positive")
    endpoint_tolerance = _numeric(endpoint_tolerance_k, "endpoint_tolerance_k")
    if endpoint_tolerance < 0.0:
        raise ValueError("endpoint_tolerance_k must be non-negative")
    low, high = validate_temperature_range(declared)
    points = sorted({_numeric(p, "setpoint") for p in setpoints_k})
    if len(points) < 2:
        raise ValueError("setpoints collapse to a single distinct temperature")

    outside = [
        p
        for p in points
        if not (_not_below(p, low - ABS_TOL_K) and _not_below(high + ABS_TOL_K, p))
    ]
    gaps = []
    wide = []
    for first, second in zip(points, points[1:]):
        gap = second - first
        gaps.append(gap)
        if gap > gap_limit and not math.isclose(
            gap, gap_limit, rel_tol=REL_TOL, abs_tol=ABS_TOL_K
        ):
            wide.append((first, second))
    cold_anchored = _not_below(endpoint_tolerance, abs(points[0] - low))
    hot_anchored = _not_below(endpoint_tolerance, abs(points[-1] - high))
    return {
        "setpoints_k": points,
        "count": len(points),
        "gaps_k": gaps,
        "largest_gap_k": max(gaps),
        "wide_gaps": wide,
        "setpoints_outside_range": outside,
        "cold_endpoint_anchored": cold_anchored,
        "hot_endpoint_anchored": hot_anchored,
        "covered": not wide and not outside and cold_anchored and hot_anchored,
    }


def thermometry_adequate(
    uncertainty_k, span_k, max_fraction=DEFAULT_THERMOMETRY_FRACTION
):
    """True when sensor uncertainty stays inside its share of the span."""
    uncertainty = _numeric(uncertainty_k, "uncertainty_k")
    if uncertainty <= 0.0:
        raise ValueError("thermometry uncertainty must be positive")
    span = _numeric(span_k, "span_k")
    if span <= 0.0:
        raise ValueError("span_k must be positive")
    fraction = _numeric(max_fraction, "max_fraction")
    if not 0.0 < fraction < 1.0:
        raise ValueError("max_fraction must lie in (0, 1)")
    allowed = span * fraction
    return _not_below(allowed, uncertainty)


def assess_temperature_range(record):
    """Full clause 9.4.1.4 report for one declared measurement range."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (type(record),))
    declared = record.get("declared_range")
    service = record.get("predicted_service_range")
    if declared is None or service is None:
        raise ValueError("record needs 'declared_range' and 'predicted_service_range'")
    d_low, d_high = validate_temperature_range(declared)
    validate_temperature_range(service)
    span = d_high - d_low
    margins = range_margins_k(declared, service)
    state = approval_state(record)
    coverage = setpoint_coverage(
        record.get("setpoints_k", []),
        declared,
        record.get("max_setpoint_gap_k", DEFAULT_MAX_SETPOINT_GAP_K),
        record.get("endpoint_tolerance_k", DEFAULT_ENDPOINT_TOLERANCE_K),
    )
    uncertainty = record.get("thermometry_uncertainty_k")
    if uncertainty is None:
        thermometry_ok = None
    else:
        thermometry_ok = thermometry_adequate(
            uncertainty,
            span,
            record.get("thermometry_fraction", DEFAULT_THERMOMETRY_FRACTION),
        )

    findings = []
    if margins["cold_margin_k"] < 0.0 and not math.isclose(
        margins["cold_margin_k"], 0.0, rel_tol=REL_TOL, abs_tol=ABS_TOL_K
    ):
        findings.append(
            {
                "code": "cold-end-not-enveloped",
                "detail": "declared cold end stops %.4g K short of the predicted"
                " service minimum" % abs(margins["cold_margin_k"]),
            }
        )
    if margins["hot_margin_k"] < 0.0 and not math.isclose(
        margins["hot_margin_k"], 0.0, rel_tol=REL_TOL, abs_tol=ABS_TOL_K
    ):
        findings.append(
            {
                "code": "hot-end-not-enveloped",
                "detail": "declared hot end stops %.4g K short of the predicted"
                " service maximum" % abs(margins["hot_margin_k"]),
            }
        )
    if state == "pending-customer-approval":
        findings.append(
            {
                "code": "customer-approval-missing",
                "detail": "supplier range is declared but not approved by the"
                " customer",
            }
        )
    elif state == "approval-superseded":
        findings.append(
            {
                "code": "customer-approval-superseded",
                "detail": "approval predates the declaration revision it is"
                " meant to cover",
            }
        )
    if coverage["setpoints_outside_range"]:
        findings.append(
            {
                "code": "setpoint-outside-declared-range",
                "detail": "%d setpoints sit outside the declared range"
                % len(coverage["setpoints_outside_range"]),
            }
        )
    if coverage["wide_gaps"]:
        findings.append(
            {
                "code": "setpoint-gap-exceeds-limit",
                "detail": "largest gap %.4g K exceeds the interpolation limit"
                % coverage["largest_gap_k"],
            }
        )
    if not coverage["cold_endpoint_anchored"] or not coverage["hot_endpoint_anchored"]:
        findings.append(
            {
                "code": "range-endpoint-not-measured",
                "detail": "a declared endpoint carries no setpoint within the"
                " endpoint tolerance",
            }
        )
    if thermometry_ok is None:
        findings.append(
            {
                "code": "thermometry-uncertainty-not-on-record",
                "detail": "no sensor uncertainty was captured; an unset value is"
                " a finding, not a pass",
            }
        )
    elif not thermometry_ok:
        findings.append(
            {
                "code": "thermometry-uncertainty-excessive",
                "detail": "sensor uncertainty takes more than its allowed share"
                " of the %.4g K span" % span,
            }
        )
    justification = record.get("range_justification")
    if justification is None or (
        isinstance(justification, str) and not justification.strip()
    ):
        findings.append(
            {
                "code": "range-justification-missing",
                "detail": "no rationale on record for the declared range",
            }
        )

    return {
        "item": record.get("id", "unnamed-item"),
        "declared_range_k": (d_low, d_high),
        "declared_span_k": span,
        "margins_k": margins,
        "envelops_service_range": envelops_service_range(declared, service),
        "approval_state": state,
        "coverage": coverage,
        "thermometry_adequate": thermometry_ok,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }

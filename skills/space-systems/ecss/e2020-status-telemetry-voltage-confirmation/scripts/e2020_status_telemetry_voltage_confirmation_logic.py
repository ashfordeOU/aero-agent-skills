#!/usr/bin/env python3
"""Status telemetry that confirms the output voltage, not just the command.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A limiter reports an on or off state to the housekeeping stream. The
clause makes that bit mean something specific: an on report is a
statement that the output voltage is actually inside its nominal band,
not that a command was accepted or that a drive signal is present. The
bit is therefore only as good as the sense chain that derives it, so
the work is to fix the band, check the thresholds the sense chain uses
sit where they have to, derive the state that chain would report, and
categorize the reported state against the measured output.

State categories
    on-confirmed           reports on, output measured inside the band
    on-unconfirmed-under   reports on, output below the band floor
    on-unconfirmed-over    reports on, output above the band ceiling
    off-confirmed          reports off, output measured de-energised
    off-contradicted       reports off, output still carrying voltage

The dangerous category is on-unconfirmed-under: a bit that reads on
while the output has collapsed lets an operator and an onboard
procedure believe a load is powered when it is not.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STATES = ("on", "off")

ON_CONFIRMED = "on-confirmed"
ON_UNCONFIRMED_UNDER = "on-unconfirmed-under"
ON_UNCONFIRMED_OVER = "on-unconfirmed-over"
OFF_CONFIRMED = "off-confirmed"
OFF_CONTRADICTED = "off-contradicted"

CATEGORIES = (
    ON_CONFIRMED,
    ON_UNCONFIRMED_UNDER,
    ON_UNCONFIRMED_OVER,
    OFF_CONFIRMED,
    OFF_CONTRADICTED,
)

CONFIRMING_CATEGORIES = (ON_CONFIRMED, OFF_CONFIRMED)

VERDICT_CONFIRMS = "status-confirms-output-voltage"
VERDICT_DOES_NOT_CONFIRM = "status-does-not-confirm-output-voltage"

# A residual level below which the output counts as de-energised, as a
# fraction of the nominal output. Leakage and a discharging filter keep
# a switched-off rail from reaching exactly zero.
DEFAULT_DE_ENERGISED_FRACTION = 0.10

# Smallest hysteresis the sense chain may carry, as a fraction of the
# nominal output. Below this the bit chatters on ripple alone.
DEFAULT_MIN_HYSTERESIS_FRACTION = 0.01

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value >= 1.0:
        raise ValueError("%s must be below one, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A band edge is a product of a nominal and a tolerance fraction, so a
    measurement meant to sit exactly on an edge can land a few units in
    the last place below it. The band is never widened; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def nominal_voltage_band(
    nominal_output_v, lower_tolerance_fraction, upper_tolerance_fraction
):
    """Band the output has to sit in for an on report to be truthful."""
    nominal = _require_positive("nominal_output_v", nominal_output_v)
    lower = _require_fraction("lower_tolerance_fraction", lower_tolerance_fraction)
    upper = _require_non_negative(
        "upper_tolerance_fraction", upper_tolerance_fraction
    )
    return {
        "nominal_v": nominal,
        "min_v": nominal * (1.0 - lower),
        "max_v": nominal * (1.0 + upper),
    }


def in_band(measured_output_v, band):
    """Whether a measurement sits inside the band, edges included."""
    measured = _require_non_negative("measured_output_v", measured_output_v)
    return _at_least(measured, band["min_v"]) and _at_most(measured, band["max_v"])


def confirmation_margin_v(measured_output_v, band):
    """Distance from the measurement to the nearer band edge.

    Positive inside the band, negative outside it, so the sign is the
    in-band answer and the size says how much room the report has.
    """
    measured = _require_non_negative("measured_output_v", measured_output_v)
    return min(measured - band["min_v"], band["max_v"] - measured)


def validate_sense_thresholds(
    band,
    on_threshold_v,
    off_threshold_v,
    min_hysteresis_fraction=DEFAULT_MIN_HYSTERESIS_FRACTION,
):
    """Check the sense chain's thresholds can support an honest on bit.

    The on threshold has to sit inside the band. Placed below the band
    floor the chain will assert on for an output that has already fallen
    out of tolerance, which is exactly the false confirmation the clause
    is written against. Placed above the ceiling the chain can never
    assert on for a compliant output at all.
    """
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    on_v = _require_positive("on_threshold_v", on_threshold_v)
    off_v = _require_non_negative("off_threshold_v", off_threshold_v)
    if off_v >= on_v:
        raise ValueError(
            "off_threshold_v %g V must sit below on_threshold_v %g V; the "
            "sense chain has no hysteresis" % (off_v, on_v)
        )
    hysteresis = on_v - off_v
    min_hysteresis = _require_fraction(
        "min_hysteresis_fraction", min_hysteresis_fraction
    ) * band["nominal_v"]
    findings = []
    on_inside = _at_least(on_v, band["min_v"]) and _at_most(on_v, band["max_v"])
    if not _at_least(on_v, band["min_v"]):
        findings.append(
            "on threshold %g V sits below the band floor %g V; the bit can "
            "report on for an out-of-tolerance output"
            % (on_v, band["min_v"])
        )
    elif not _at_most(on_v, band["max_v"]):
        findings.append(
            "on threshold %g V sits above the band ceiling %g V; a compliant "
            "output can never assert the bit" % (on_v, band["max_v"])
        )
    if not _at_least(hysteresis, min_hysteresis):
        findings.append(
            "hysteresis %g V is below the %g V floor; the bit chatters on "
            "ripple alone" % (hysteresis, min_hysteresis)
        )
    return {
        "on_threshold_v": on_v,
        "off_threshold_v": off_v,
        "hysteresis_v": hysteresis,
        "on_threshold_inside_band": on_inside,
        "thresholds_adequate": not findings,
        "findings": findings,
    }


def derive_status(measured_output_v, on_threshold_v, off_threshold_v, previous_state):
    """State the hysteretic sense chain would report for a measurement."""
    measured = _require_non_negative("measured_output_v", measured_output_v)
    on_v = _require_positive("on_threshold_v", on_threshold_v)
    off_v = _require_non_negative("off_threshold_v", off_threshold_v)
    _require_choice("previous_state", previous_state, STATES)
    if off_v >= on_v:
        raise ValueError("off_threshold_v must sit below on_threshold_v")
    if _at_least(measured, on_v):
        return "on"
    if _at_most(measured, off_v):
        return "off"
    return previous_state


def categorize_report(
    reported_state,
    measured_output_v,
    band,
    de_energised_fraction=DEFAULT_DE_ENERGISED_FRACTION,
):
    """Group a reported state against the measured output."""
    _require_choice("reported_state", reported_state, STATES)
    measured = _require_non_negative("measured_output_v", measured_output_v)
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    de_energised_v = _require_fraction(
        "de_energised_fraction", de_energised_fraction
    ) * band["nominal_v"]
    if reported_state == "on":
        if in_band(measured, band):
            return ON_CONFIRMED
        if measured < band["min_v"]:
            return ON_UNCONFIRMED_UNDER
        return ON_UNCONFIRMED_OVER
    if _at_most(measured, de_energised_v):
        return OFF_CONFIRMED
    return OFF_CONTRADICTED


def assess_status_confirmation(case):
    """Full clause 5.2.8.1.1 assessment with a verdict and findings.

    The bit is only accepted when three things agree: the thresholds can
    support an honest report, the sense chain would derive the state the
    housekeeping stream carries, and that state is confirmed by the
    measured output.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    band = nominal_voltage_band(
        case.get("nominal_output_v"),
        case.get("lower_tolerance_fraction"),
        case.get("upper_tolerance_fraction"),
    )
    thresholds = validate_sense_thresholds(
        band,
        case.get("on_threshold_v"),
        case.get("off_threshold_v"),
        case.get(
            "min_hysteresis_fraction", DEFAULT_MIN_HYSTERESIS_FRACTION
        ),
    )
    measured = _require_non_negative(
        "measured_output_v", case.get("measured_output_v")
    )
    reported = _require_choice("reported_state", case.get("reported_state"), STATES)
    previous = _require_choice(
        "previous_state", case.get("previous_state", reported), STATES
    )
    derived = derive_status(
        measured, thresholds["on_threshold_v"], thresholds["off_threshold_v"], previous
    )
    category = categorize_report(
        reported,
        measured,
        band,
        case.get("de_energised_fraction", DEFAULT_DE_ENERGISED_FRACTION),
    )
    findings = list(thresholds["findings"])
    if derived != reported:
        findings.append(
            "housekeeping reports %s but the sense chain on %g V would derive "
            "%s; the reported bit does not come from the output"
            % (reported, measured, derived)
        )
    if category == ON_UNCONFIRMED_UNDER:
        findings.append(
            "reports on at %g V, below the %g V band floor; a load believed "
            "powered is not" % (measured, band["min_v"])
        )
    elif category == ON_UNCONFIRMED_OVER:
        findings.append(
            "reports on at %g V, above the %g V band ceiling; the output is "
            "outside its nominal band" % (measured, band["max_v"])
        )
    elif category == OFF_CONTRADICTED:
        findings.append(
            "reports off while the output still stands at %g V; the load is "
            "not isolated" % (measured,)
        )
    confirms = (
        category in CONFIRMING_CATEGORIES
        and derived == reported
        and thresholds["thresholds_adequate"]
    )
    return {
        "band": band,
        "measured_output_v": measured,
        "reported_state": reported,
        "derived_state": derived,
        "category": category,
        "confirmation_margin_v": confirmation_margin_v(measured, band),
        "hysteresis_v": thresholds["hysteresis_v"],
        "thresholds_adequate": thresholds["thresholds_adequate"],
        "confirms": confirms,
        "verdict": VERDICT_CONFIRMS if confirms else VERDICT_DOES_NOT_CONFIRM,
        "findings": findings,
    }

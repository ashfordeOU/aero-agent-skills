#!/usr/bin/env python3
"""Calibration control of a test facility measurement chain.

Anchor: ECSS-Q-ST-20-07 clause 5.6.3, the requirement that facility
measurement chains and instrumentation are covered by a calibration
plan and by calibration records. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Four things follow from what the clause is for.

A measurement is a chain, not an instrument. A transducer, its
conditioner, the cabling and the acquisition card each contribute, and
the chain uncertainty is their root-sum-square when the contributions
are independent, not the worst element and not their arithmetic sum. A
group declared correlated is summed linearly first, because treating it
as independent understates the chain.

The accuracy ratio is the decision. A chain is fit when the tolerance
the measured parameter owes is enough times wider than the chain
uncertainty, so the same chain is fit for a coarse parameter and unfit
for a tight one.

Validity is read at the last day of the run. A certificate expiring
mid-campaign leaves the data recorded after it with nothing behind it,
and differs from one already expired only in the corrective action.

An element driven outside its calibrated range is uncalibrated at the
point of use, whatever the certificate says.

The policy numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NO_CALIBRATION_PLAN = "test-facility-chain-not-under-calibration-plan"
CERTIFICATE_EXPIRED = "test-facility-calibration-certificate-expired"
ELEMENT_OUT_OF_RANGE = "test-facility-element-outside-calibrated-range"
PLAN_COVERAGE_SHORT = "test-facility-calibration-plan-coverage-short"
ACCURACY_RATIO_SHORT = "test-facility-accuracy-ratio-short"
CERTIFICATE_EXPIRING = "test-facility-certificate-expiring-in-campaign"
CHAIN_FIT_FOR_CAMPAIGN = "test-facility-chain-fit-for-campaign"

DEFAULT_CALIBRATION_POLICY = {
    "required_accuracy_ratio": 4.0,
    "expiry_notice_days": 30,
    "min_plan_coverage": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_calibration_policy(policy):
    """Check the policy the measurement chain is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    ratio = _require_positive(
        "required_accuracy_ratio", policy.get("required_accuracy_ratio")
    )
    if ratio < 1.0:
        raise ValueError(
            "required_accuracy_ratio below one asks the chain to be less "
            "accurate than the tolerance it measures, got %r" % (ratio,)
        )
    _require_count("expiry_notice_days", policy.get("expiry_notice_days"))
    _require_fraction("min_plan_coverage", policy.get("min_plan_coverage"))
    return policy


def validate_chain_element(element):
    """Read one element of the facility measurement chain."""
    if not isinstance(element, dict):
        raise ValueError("chain element must be a mapping, got %r" % (element,))
    range_min = _require_number("range_min", element.get("range_min"))
    range_max = _require_number("range_max", element.get("range_max"))
    if range_max <= range_min:
        raise ValueError(
            "element %r declares an inverted calibrated range %r to %r"
            % (element.get("element_id"), range_min, range_max)
        )
    group = element.get("correlation_group")
    if group is not None:
        group = _require_label("correlation_group", group)
    in_plan = element.get("in_calibration_plan", True)
    if not isinstance(in_plan, bool):
        raise ValueError("in_calibration_plan must be true or false, got %r" % (in_plan,))
    return {
        "element_id": _require_label("element_id", element.get("element_id")),
        "uncertainty": _require_positive("uncertainty", element.get("uncertainty")),
        "range_min": range_min,
        "range_max": range_max,
        "certificate_expiry_day": _require_count(
            "certificate_expiry_day", element.get("certificate_expiry_day")
        ),
        "correlation_group": group,
        "in_calibration_plan": in_plan,
    }


def validate_chain(elements):
    """Read the whole chain, refusing the same element twice."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("chain must be a sequence of chain elements")
    checked = []
    seen = set()
    for element in elements:
        record = validate_chain_element(element)
        if record["element_id"] in seen:
            raise ValueError("chain element %r appears twice" % record["element_id"])
        seen.add(record["element_id"])
        checked.append(record)
    if not checked:
        raise ValueError("the measurement chain declares no elements at all")
    return tuple(checked)


def plan_coverage(elements):
    """Share of chain elements the calibration plan actually names."""
    checked = validate_chain(elements)
    planned = sum(1 for record in checked if record["in_calibration_plan"])
    return planned / float(len(checked))


def unplanned_elements(elements):
    """Chain elements carrying unbounded uncertainty for want of a plan."""
    return tuple(
        record["element_id"]
        for record in validate_chain(elements)
        if not record["in_calibration_plan"]
    )


def chain_uncertainty(elements):
    """Combine element uncertainties: correlated linearly, then in quadrature."""
    checked = validate_chain(elements)
    groups = {}
    independent = []
    for record in checked:
        if record["correlation_group"] is None:
            independent.append(record["uncertainty"])
        else:
            groups[record["correlation_group"]] = (
                groups.get(record["correlation_group"], 0.0) + record["uncertainty"]
            )
    terms = independent + list(groups.values())
    return math.sqrt(sum(term * term for term in terms))


def accuracy_ratio(elements, parameter_tolerance):
    """How many times wider the parameter tolerance is than the chain."""
    tolerance = _require_positive("parameter_tolerance", parameter_tolerance)
    return tolerance / chain_uncertainty(elements)


def validate_campaign_range(campaign):
    """Read the range the campaign will drive the chain elements to."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    low = _require_number("campaign_min", campaign.get("campaign_min"))
    high = _require_number("campaign_max", campaign.get("campaign_max"))
    if high < low:
        raise ValueError(
            "the campaign range runs backwards, %r to %r" % (low, high)
        )
    return low, high


def elements_outside_range(elements, campaign):
    """Elements the campaign drives beyond what their certificate covers."""
    low, high = validate_campaign_range(campaign)
    outside = []
    for record in validate_chain(elements):
        below = low < record["range_min"] and not math.isclose(
            low, record["range_min"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
        above = high > record["range_max"] and not math.isclose(
            high, record["range_max"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
        if below or above:
            outside.append(record["element_id"])
    return tuple(outside)


def expired_certificates(elements, last_run_day):
    """Elements whose certificate does not reach the last day of the run."""
    day = _require_count("last_run_day", last_run_day)
    return tuple(
        record["element_id"]
        for record in validate_chain(elements)
        if record["certificate_expiry_day"] < day
    )


def certificates_expiring(elements, last_run_day, policy=None):
    """Elements valid to the last run day but only just."""
    policy = validate_calibration_policy(policy or DEFAULT_CALIBRATION_POLICY)
    day = _require_count("last_run_day", last_run_day)
    notice = int(policy["expiry_notice_days"])
    return tuple(
        record["element_id"]
        for record in validate_chain(elements)
        if day <= record["certificate_expiry_day"] <= day + notice
    )


def assess_facility_calibration(case):
    """Grade a facility measurement chain and say whether it may be used."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_calibration_policy(
        case.get("policy") or DEFAULT_CALIBRATION_POLICY
    )

    findings = []
    advisories = []
    result = {
        "elements": 0,
        "plan_coverage": None,
        "unplanned_elements": (),
        "chain_uncertainty": None,
        "accuracy_ratio": None,
        "elements_outside_range": (),
        "expired_certificates": (),
        "expiring_certificates": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    chain = case.get("chain")
    if chain is None:
        findings.append(
            "no measurement chain was supplied, so there is nothing to "
            "calibrate against the parameter"
        )
        result["verdict"] = NO_CALIBRATION_PLAN
        return result
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping, got %r" % (chain,))

    elements = chain.get("elements")
    if not elements:
        findings.append(
            "the measurement chain names no elements, so no calibration plan "
            "can cover it"
        )
        result["verdict"] = NO_CALIBRATION_PLAN
        return result

    checked = validate_chain(elements)
    result["elements"] = len(checked)
    result["plan_coverage"] = plan_coverage(checked)
    result["unplanned_elements"] = unplanned_elements(checked)

    if not chain.get("calibration_plan", True):
        findings.append(
            "the chain stands outside any calibration plan, so its "
            "uncertainty is unbounded whatever the elements report"
        )
        result["verdict"] = NO_CALIBRATION_PLAN
        return result

    last_run_day = _require_count("last_run_day", chain.get("last_run_day"))
    expired = expired_certificates(checked, last_run_day)
    result["expired_certificates"] = expired
    if expired:
        findings.append(
            "certificate(s) for %s do not reach the last run day %d"
            % (", ".join(expired), last_run_day)
        )
        result["verdict"] = CERTIFICATE_EXPIRED
        return result

    campaign = chain.get("campaign_range")
    if campaign is not None:
        outside = elements_outside_range(checked, campaign)
        result["elements_outside_range"] = outside
        if outside:
            findings.append(
                "the campaign drives %s past the range their certificate "
                "covers, so they are uncalibrated at the point of use"
                % ", ".join(outside)
            )
            result["verdict"] = ELEMENT_OUT_OF_RANGE
            return result

    if not _at_least(result["plan_coverage"], float(policy["min_plan_coverage"])):
        findings.append(
            "%d of %d chain element(s) are absent from the calibration plan: %s"
            % (
                len(result["unplanned_elements"]),
                len(checked),
                ", ".join(result["unplanned_elements"]),
            )
        )
        result["verdict"] = PLAN_COVERAGE_SHORT
        return result

    uncertainty = chain_uncertainty(checked)
    result["chain_uncertainty"] = uncertainty
    tolerance = chain.get("parameter_tolerance")
    if tolerance is None:
        raise ValueError(
            "the chain declares no parameter tolerance, so the accuracy ratio "
            "has no denominator and the chain cannot be graded"
        )
    ratio = accuracy_ratio(checked, tolerance)
    result["accuracy_ratio"] = ratio
    if not _at_least(ratio, float(policy["required_accuracy_ratio"])):
        findings.append(
            "the chain reaches an accuracy ratio of %.4g against the %.4g the "
            "test centre requires" % (ratio, float(policy["required_accuracy_ratio"]))
        )
        result["verdict"] = ACCURACY_RATIO_SHORT
        return result

    expiring = certificates_expiring(checked, last_run_day, policy)
    result["expiring_certificates"] = expiring
    if expiring:
        advisories.append(
            "certificate(s) for %s expire within %d day(s) of the last run "
            "day, so a recalibration falls inside the campaign window"
            % (", ".join(expiring), int(policy["expiry_notice_days"]))
        )
        result["verdict"] = CERTIFICATE_EXPIRING
        return result

    result["verdict"] = CHAIN_FIT_FOR_CAMPAIGN
    return result

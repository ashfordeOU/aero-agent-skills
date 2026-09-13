#!/usr/bin/env python3
"""Antenna single-point-failure failure-rate agreement (ECSS-E-ST-20C 7.2.1.3).

Paraphrased procedure, no verbatim standard text. An antenna kept in a
spacecraft design without a redundant functional string is a
single-point-failure item. The clause admits that situation only when the
antenna failure-rate is agreed with the customer, captured in the
requirement-baseline, and demonstrated by evidence rather than asserted.

Deterministic, offline, stdlib only. Failure rates are carried in FIT
(failures per 1e9 hours).

Public entry points
-------------------
categorize_redundancy           is the antenna a single-point-failure item?
validate_failure_rate_record    is a usable failure-rate record on file?
grade_demonstration_evidence    how strong is the demonstration route?
failure_rate_within_specified   does demonstrated stay inside specified?
reliability_from_failure_rate   exponential survival over the mission
series_reliability              chain of retained single-point-failure items
assess_antenna                  per-antenna finding list
assess_antenna_set              programme roll-up against the allocation
"""

import math

FIT_TO_PER_HOUR = 1e-9

# Redundancy scheme -> True when the scheme leaves one functional string.
REDUNDANCY_SCHEMES = {
    "none": True,
    "single-string": True,
    "cold-standby": False,
    "hot-standby": False,
    "cross-strapped": False,
    "functionally-redundant": False,
}

# Demonstration routes, strongest first.
EVIDENCE_RANK = {
    "test": 4,
    "in-orbit-heritage": 3,
    "similarity": 2,
    "analysis": 1,
}

# Similarity or better closes the demonstration obligation; a bare
# handbook analysis does not.
MIN_EVIDENCE_RANK = 2

REL_TOL = 1e-9
ABS_TOL = 1e-12


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _require_number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % label)
    if minimum is not None and number < minimum and not math.isclose(
        number, minimum, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError("%s must be >= %s" % (label, minimum))
    if maximum is not None and number > maximum and not math.isclose(
        number, maximum, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError("%s must be <= %s" % (label, maximum))
    return number


def _require_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _not_less(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_redundancy(scheme, causes_loss_of_function):
    """Categorize one antenna as a single-point-failure item or not.

    A non-redundant antenna whose failure removes a spacecraft function is a
    single-point-failure item and falls under the agreement obligation. A
    non-redundant antenna whose loss is absorbed elsewhere is tolerated, and
    any redundant scheme is outside the obligation.
    """
    key = _require_text(scheme, "redundancy scheme")
    if key not in REDUNDANCY_SCHEMES:
        raise ValueError("unknown redundancy scheme: %r" % (scheme,))
    _require_flag(causes_loss_of_function, "causes_loss_of_function")
    if not REDUNDANCY_SCHEMES[key]:
        return "redundant"
    if causes_loss_of_function:
        return "single-point-failure"
    return "non-redundant-tolerated"


def grade_demonstration_evidence(evidence):
    """Rank a demonstration route; higher is stronger."""
    key = _require_text(evidence, "demonstration evidence")
    if key not in EVIDENCE_RANK:
        raise ValueError("unknown demonstration evidence route: %r" % (evidence,))
    return EVIDENCE_RANK[key]


def validate_failure_rate_record(record):
    """Normalize one failure-rate record, rejecting unusable input."""
    if not isinstance(record, dict):
        raise ValueError("failure-rate record must be a mapping")
    if "specified_fit" not in record:
        raise ValueError("failure-rate record is missing 'specified_fit'")
    specified = _require_number(record["specified_fit"], "specified_fit", minimum=0.0)
    if specified <= 0.0:
        raise ValueError("specified_fit must be greater than zero")
    demonstrated = record.get("demonstrated_fit")
    if demonstrated is not None:
        demonstrated = _require_number(demonstrated, "demonstrated_fit", minimum=0.0)
    evidence = record.get("evidence")
    if evidence is not None:
        grade_demonstration_evidence(evidence)
        evidence = evidence.strip().lower()
    return {
        "specified_fit": specified,
        "demonstrated_fit": demonstrated,
        "evidence": evidence,
        "customer_agreed": _require_flag(
            record.get("customer_agreed", False), "customer_agreed"
        ),
        "baseline_specified": _require_flag(
            record.get("baseline_specified", False), "baseline_specified"
        ),
    }


def failure_rate_within_specified(demonstrated_fit, specified_fit):
    """True when the demonstrated failure-rate stays inside the specified one."""
    demonstrated = _require_number(demonstrated_fit, "demonstrated_fit", minimum=0.0)
    specified = _require_number(specified_fit, "specified_fit", minimum=0.0)
    if specified <= 0.0:
        raise ValueError("specified_fit must be greater than zero")
    return demonstrated <= specified or math.isclose(
        demonstrated, specified, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def reliability_from_failure_rate(fit, mission_hours):
    """Exponential survival probability for a constant failure-rate in FIT."""
    rate = _require_number(fit, "fit", minimum=0.0)
    hours = _require_number(mission_hours, "mission_hours", minimum=0.0)
    if hours <= 0.0:
        raise ValueError("mission_hours must be greater than zero")
    return math.exp(-rate * FIT_TO_PER_HOUR * hours)


def series_reliability(fits, mission_hours):
    """Survival of a chain in which any one item ends the function."""
    if not isinstance(fits, (list, tuple)):
        raise ValueError("fits must be a list or tuple")
    if len(fits) == 0:
        raise ValueError("fits must not be empty")
    product = 1.0
    for index, fit in enumerate(fits):
        product *= reliability_from_failure_rate(fit, mission_hours)
        if product <= 0.0:
            raise ValueError("chain reliability underflowed at item %d" % index)
    return product


def assess_antenna(item, mission_hours):
    """Apply the clause to one antenna and return its finding list."""
    if not isinstance(item, dict):
        raise ValueError("antenna item must be a mapping")
    ident = _require_text(item.get("id"), "antenna id")
    hours = _require_number(mission_hours, "mission_hours", minimum=0.0)
    if hours <= 0.0:
        raise ValueError("mission_hours must be greater than zero")
    category = categorize_redundancy(
        item.get("redundancy_scheme"), item.get("causes_loss_of_function", True)
    )
    result = {
        "id": ident,
        "category": category,
        "applicable": category == "single-point-failure",
        "specified_fit": None,
        "demonstrated_fit": None,
        "effective_fit": None,
        "reliability": None,
        "findings": [],
    }
    record = item.get("failure_rate")
    if record is not None:
        normalized = validate_failure_rate_record(record)
        result["specified_fit"] = normalized["specified_fit"]
        result["demonstrated_fit"] = normalized["demonstrated_fit"]
        effective = normalized["demonstrated_fit"]
        if effective is None:
            effective = normalized["specified_fit"]
        result["effective_fit"] = effective
        result["reliability"] = reliability_from_failure_rate(effective, hours)
    if not result["applicable"]:
        result["compliant"] = True
        return result
    if record is None:
        result["findings"].append(
            "single-point-failure antenna '%s' carries no failure-rate record" % ident
        )
        result["compliant"] = False
        return result
    normalized = validate_failure_rate_record(record)
    if not normalized["customer_agreed"]:
        result["findings"].append(
            "failure-rate of '%s' is not agreed with the customer" % ident
        )
    if not normalized["baseline_specified"]:
        result["findings"].append(
            "failure-rate of '%s' is not captured in the requirement-baseline" % ident
        )
    if normalized["evidence"] is None:
        result["findings"].append(
            "failure-rate of '%s' has no demonstration evidence on record" % ident
        )
    elif grade_demonstration_evidence(normalized["evidence"]) < MIN_EVIDENCE_RANK:
        result["findings"].append(
            "demonstration route '%s' is too weak to close the failure-rate of '%s'"
            % (normalized["evidence"], ident)
        )
    if normalized["demonstrated_fit"] is None:
        result["findings"].append(
            "no demonstrated failure-rate is recorded for '%s'" % ident
        )
    elif not failure_rate_within_specified(
        normalized["demonstrated_fit"], normalized["specified_fit"]
    ):
        result["findings"].append(
            "demonstrated failure-rate of '%s' exceeds the specified value" % ident
        )
    allocated = item.get("min_reliability")
    if allocated is not None:
        floor = _require_number(allocated, "min_reliability", minimum=0.0, maximum=1.0)
        if not _not_less(result["reliability"], floor):
            result["findings"].append(
                "reliability of '%s' falls below its allocated floor" % ident
            )
    result["compliant"] = not result["findings"]
    return result


def assess_antenna_set(items, mission_hours, allocated_reliability):
    """Roll every antenna up and compare the chain against the allocation."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list or tuple")
    if len(items) == 0:
        raise ValueError("items must not be empty")
    allocation = _require_number(
        allocated_reliability, "allocated_reliability", minimum=0.0, maximum=1.0
    )
    if allocation <= 0.0:
        raise ValueError("allocated_reliability must be greater than zero")
    assessments = [assess_antenna(item, mission_hours) for item in items]
    seen = set()
    for assessment in assessments:
        if assessment["id"] in seen:
            raise ValueError("duplicate antenna id: %r" % assessment["id"])
        seen.add(assessment["id"])
    chain_fits = [
        a["effective_fit"]
        for a in assessments
        if a["applicable"] and a["effective_fit"] is not None
    ]
    chain = series_reliability(chain_fits, mission_hours) if chain_fits else 1.0
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])
    allocation_met = _not_less(chain, allocation)
    if not allocation_met:
        findings.append(
            "chain of retained single-point-failure antennas misses the allocation"
        )
    return {
        "assessments": assessments,
        "single_point_failure_count": sum(1 for a in assessments if a["applicable"]),
        "series_reliability": chain,
        "allocated_reliability": allocation,
        "allocation_met": allocation_met,
        "findings": findings,
        "compliant": not findings,
    }

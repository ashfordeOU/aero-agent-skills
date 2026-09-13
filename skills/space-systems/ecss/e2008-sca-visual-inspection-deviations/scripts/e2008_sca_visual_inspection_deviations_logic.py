#!/usr/bin/env python3
"""Departures from the cell assembly visible defect rules, and what makes one usable.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause allows an assembly to depart from the visible defect rules
when the departure does not harm performance and the customer agrees to
it. Two conditions, and they fail independently. A technically flawless
case with no recorded agreement is not usable, and a recorded agreement
does not repair a departure that costs performance. Running them as one
test is how an article ends up flying on a rationale nobody signed.

Five things decide a single request.

Whether the criterion can be departed from at all. Some conditions
carry no allowance: the finding is decided by presence, so there is no
size below which it passes and nothing for a measurement to argue
about. A request against one of those is refused where it stands.

How far outside the criterion it asks to go. The requested value over
the criterion value is the exceedance, and past a declared ratio the
request stops being a departure and becomes a different article.

What it costs. Each departure carries a predicted electrical debit, and
one above the single-departure allowance is refused however good the
evidence behind it.

What the case is made of. Test evidence, analysis, an inspection record
and an argument from similarity are not interchangeable. Below a
declared strength the case is not solid enough to put to a customer at
all, so it goes to review rather than into the agreement queue.

Whether the customer has actually agreed. Granted makes a surviving
request usable as is. Refused sends the article to rework. Requested or
not yet requested leaves it pending -- which is a real state, not a
pass, and an article carrying pending departures is not accepted.

Then the package-level step that a per-request loop never catches: the
debits add. Departures individually inside the single allowance can sum
past the cumulative one, and when they do every carried departure goes
back for review together rather than each one passing on its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

EVIDENCE_KINDS = (
    "test",
    "analysis",
    "inspection-record",
    "similarity-heritage",
)

AGREEMENT_STATES = (
    "not-requested",
    "requested",
    "granted",
    "refused",
)

ACCEPT_AS_IS = "accept-as-is"
PENDING = "pending-customer-agreement"
REFER = "refer-for-review"
REWORK = "rework"
REJECT = "reject"
DEVIATION_DISPOSITIONS = (ACCEPT_AS_IS, PENDING, REFER, REWORK, REJECT)

PACKAGE_USABLE = "departures-usable-as-is"
PACKAGE_OPEN = "departures-open"

_DISPOSITION_ORDER = {ACCEPT_AS_IS: 0, PENDING: 1, REFER: 2, REWORK: 3, REJECT: 4}

DEFAULT_DEVIATION_POLICY = {
    "non_deviable_criteria": (
        "cracked-cell",
        "open-interconnector",
        "delaminated-coverglass",
    ),
    "max_exceedance_ratio": 1.5,
    "max_single_performance_debit": 0.005,
    "max_cumulative_performance_debit": 0.010,
    "min_evidence_strength": 0.70,
    "evidence_strength": {
        "test": 1.00,
        "analysis": 0.80,
        "inspection-record": 0.50,
        "similarity-heritage": 0.40,
    },
}

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


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An exceedance is a quotient of two declared limits and a cumulative
    debit is a sum of measured fractions, so a request sitting exactly
    on an allowance can evaluate a few units in the last place above
    it. The allowance is never raised; only the comparison tolerates
    the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT_AS_IS
    for disposition in dispositions:
        if _DISPOSITION_ORDER[disposition] > _DISPOSITION_ORDER[worst]:
            worst = disposition
    return worst


def validate_deviation_policy(policy):
    """Check a departure policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    criteria = policy.get("non_deviable_criteria")
    if not isinstance(criteria, (list, tuple)):
        raise ValueError(
            "policy non_deviable_criteria must be a sequence, got %r" % (criteria,)
        )
    for criterion in criteria:
        _require_identifier("policy non-deviable criterion", criterion)
    ratio = _require_positive(
        "policy max_exceedance_ratio", policy.get("max_exceedance_ratio")
    )
    if ratio <= 1.0:
        raise ValueError(
            "policy max_exceedance_ratio must exceed one; at unity no departure "
            "could ever be asked for, got %r" % (ratio,)
        )
    single = _require_fraction(
        "policy max_single_performance_debit",
        policy.get("max_single_performance_debit"),
    )
    cumulative = _require_fraction(
        "policy max_cumulative_performance_debit",
        policy.get("max_cumulative_performance_debit"),
    )
    if cumulative < single:
        raise ValueError(
            "policy max_cumulative_performance_debit %r sits below the single "
            "departure allowance %r, so one compliant departure would breach the "
            "package" % (cumulative, single)
        )
    _require_fraction(
        "policy min_evidence_strength", policy.get("min_evidence_strength")
    )
    strengths = policy.get("evidence_strength")
    if not isinstance(strengths, dict):
        raise ValueError(
            "policy evidence_strength must be a mapping, got %r" % (strengths,)
        )
    for kind in EVIDENCE_KINDS:
        if kind not in strengths:
            raise ValueError(
                "policy evidence_strength has no entry for %s; an unscored "
                "evidence kind would silently pass" % (kind,)
            )
        _require_fraction("policy evidence_strength %s" % kind, strengths[kind])
    return policy


def assess_deviation_request(request, policy=DEFAULT_DEVIATION_POLICY):
    """Disposition one requested departure from a visible defect criterion."""
    validate_deviation_policy(policy)
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % (request,))
    deviation_id = _require_identifier("deviation_id", request.get("deviation_id"))
    criterion_id = _require_identifier("criterion_id", request.get("criterion_id"))
    criterion_limit = _require_positive(
        "criterion_limit", request.get("criterion_limit")
    )
    requested_limit = _require_positive(
        "requested_limit", request.get("requested_limit")
    )
    debit = _require_fraction(
        "performance_debit", request.get("performance_debit")
    )
    evidence = _require_choice("evidence", request.get("evidence"), EVIDENCE_KINDS)
    agreement = _require_choice(
        "customer_agreement", request.get("customer_agreement"), AGREEMENT_STATES
    )
    strength = policy["evidence_strength"][evidence]
    exceedance = requested_limit / criterion_limit

    def _result(disposition, reasons):
        return {
            "deviation_id": deviation_id,
            "criterion_id": criterion_id,
            "disposition": disposition,
            "carried": disposition in (ACCEPT_AS_IS, PENDING),
            "exceedance_ratio": exceedance,
            "performance_debit": debit,
            "evidence": evidence,
            "evidence_strength": strength,
            "customer_agreement": agreement,
            "reasons": list(reasons),
        }

    if criterion_id in tuple(policy["non_deviable_criteria"]):
        return _result(
            REJECT,
            [
                "criterion %s carries no allowance at all, so it is decided by "
                "presence and there is nothing for a departure to be measured "
                "against" % (criterion_id,)
            ],
        )

    if _at_most(requested_limit, criterion_limit):
        raise ValueError(
            "deviation %s asks for %r against a criterion of %r; a departure has "
            "to ask for more than the criterion allows, and a request at or "
            "inside it is a conforming article recorded as a nonconformance"
            % (deviation_id, requested_limit, criterion_limit)
        )

    if not _at_most(exceedance, policy["max_exceedance_ratio"]):
        return _result(
            REJECT,
            [
                "asks for %.4f times the criterion against a %.4f limit; past "
                "that the request is a different article rather than a departure "
                "from this one"
                % (exceedance, policy["max_exceedance_ratio"])
            ],
        )

    if not _at_most(debit, policy["max_single_performance_debit"]):
        return _result(
            REJECT,
            [
                "predicts a %.5f performance debit against a %.5f single "
                "departure allowance; the departure is not free of harm and the "
                "customer agreement route is not open to it"
                % (debit, policy["max_single_performance_debit"])
            ],
        )

    if not _at_least(strength, policy["min_evidence_strength"]):
        return _result(
            REFER,
            [
                "rests on %s, scored %.2f against a %.2f floor; the case is not "
                "solid enough to put to a customer and needs strengthening "
                "before it joins the agreement queue" % (evidence, strength,
                                                         policy["min_evidence_strength"])
            ],
        )

    if agreement == "granted":
        return _result(
            ACCEPT_AS_IS,
            [
                "no harm shown and the customer has agreed, so the assembly is "
                "usable with the departure in place"
            ],
        )
    if agreement == "refused":
        return _result(
            REWORK,
            [
                "the technical case stands but the customer has refused, and "
                "agreement is a condition in its own right, so the article goes "
                "back rather than out"
            ],
        )
    return _result(
        PENDING,
        [
            "the technical case stands but the customer agreement is %s; an "
            "article carrying a departure nobody has agreed to is not accepted"
            % (agreement,)
        ],
    )


def assess_deviation_package(package, policy=DEFAULT_DEVIATION_POLICY):
    """Clause 6.4.3.1.3 departures over one cell assembly, debits included."""
    validate_deviation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    assembly_id = _require_identifier("assembly_id", package.get("assembly_id"))
    requests = package.get("deviations")
    if not isinstance(requests, (list, tuple)):
        raise ValueError("deviations must be a list, got %r" % (requests,))

    seen = set()
    assessed = []
    for request in requests:
        result = assess_deviation_request(request, policy)
        marker = result["deviation_id"]
        if marker in seen:
            raise ValueError(
                "duplicate deviation id %r on assembly %s" % (marker, assembly_id)
            )
        seen.add(marker)
        assessed.append(result)

    findings = []
    cumulative = sum(
        result["performance_debit"] for result in assessed if result["carried"]
    )
    allowance = policy["max_cumulative_performance_debit"]
    cumulative_breached = not _at_most(cumulative, allowance)
    if cumulative_breached:
        findings.append(
            "the carried departures cost %.5f together against a %.5f package "
            "allowance, even though each one sits inside the single departure "
            "limit; they are reviewed together rather than one at a time"
            % (cumulative, allowance)
        )
        for result in assessed:
            if result["carried"]:
                result["disposition"] = _worst((result["disposition"], REFER))
                result["carried"] = False
                result["reasons"].append(
                    "held with the rest of the package while the cumulative "
                    "performance debit is resolved"
                )

    counts = dict((state, 0) for state in DEVIATION_DISPOSITIONS)
    for result in assessed:
        counts[result["disposition"]] += 1
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["deviation_id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])
    usable = verdict == ACCEPT_AS_IS
    outstanding = [
        result["deviation_id"]
        for result in assessed
        if result["disposition"] == PENDING
    ]
    return {
        "assembly_id": assembly_id,
        "verdict": PACKAGE_USABLE if usable else PACKAGE_OPEN,
        "worst_disposition": verdict,
        "usable_as_is": usable,
        "cumulative_performance_debit": cumulative,
        "cumulative_allowance": allowance,
        "cumulative_allowance_breached": cumulative_breached,
        "disposition_counts": counts,
        "accept_as_is_ids": [
            result["deviation_id"]
            for result in assessed
            if result["disposition"] == ACCEPT_AS_IS
        ],
        "awaiting_agreement_ids": outstanding,
        "agreement_outstanding_count": len(outstanding),
        "rework_ids": [
            result["deviation_id"]
            for result in assessed
            if result["disposition"] == REWORK
        ],
        "review_ids": [
            result["deviation_id"]
            for result in assessed
            if result["disposition"] == REFER
        ],
        "rejected_ids": [
            result["deviation_id"]
            for result in assessed
            if result["disposition"] == REJECT
        ],
        "deviations": assessed,
        "findings": findings,
    }

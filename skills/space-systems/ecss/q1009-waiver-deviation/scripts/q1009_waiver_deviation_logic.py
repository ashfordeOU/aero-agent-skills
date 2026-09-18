#!/usr/bin/env python3
"""Deviation and waiver requests against an agreed requirement.

Anchor: ECSS-Q-ST-10-09C clause 5.2.3.5, with the configuration
management rules of the M-ST-40 branch. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two request types, separated by one fact — whether the departure has
already been incurred:

    deviation   asked for before the item is built or the activity is
                performed, so the departure is authorised in advance
    waiver      asked for once the departure exists, so the request is
                to accept hardware or work that already departs

Both are configuration management records: they name the requirement
departed from, the configuration item, the effectivity they cover and
how long they last. Neither authorises anything until it is approved,
and using an affected item before approval is itself a nonconformance.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import re

REQUEST_TYPES = ("deviation", "waiver")

DURATIONS = ("one-off", "limited-effectivity", "permanent")

APPROVAL_STATES = ("draft", "submitted", "approved", "rejected")

REQUIRED_FIELDS = (
    "request_id",
    "configuration_item",
    "requirement_id",
    "departure_description",
    "justification",
    "affected_items",
    "duration",
    "impact_assessment",
)

IMPACT_KEYS = ("safety", "reliability", "interfaces", "lifetime", "verification")

CUSTOMER_AUTHORITY = "customer-configuration-control-board"
SUPPLIER_AUTHORITY = "supplier-configuration-control-board"

VERDICT_INCOMPLETE = "request-incomplete"
VERDICT_READY = "request-ready-to-submit"
VERDICT_PENDING = "request-pending-approval"
VERDICT_APPROVED = "request-approved"
VERDICT_REJECTED = "request-rejected"
VERDICT_EXPIRED = "request-authorisation-spent"
VERDICT_VIOLATION = "use-before-approval"

_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def parse_date(name, value):
    """ISO calendar date, rejected rather than guessed when malformed."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (name, value))


def request_identifier_ok(value):
    """A configuration record needs an identifier the register can hold."""
    return bool(_ID_RE.match(value)) if isinstance(value, str) else False


def determine_request_type(departure_already_incurred):
    """Deviation before the departure exists, waiver once it does."""
    _require_flag("departure_already_incurred", departure_already_incurred)
    return "waiver" if departure_already_incurred else "deviation"


def check_impact_assessment(impact):
    """Every impact heading must be answered, yes or no, never omitted."""
    if not isinstance(impact, dict):
        raise ValueError("impact_assessment must be a mapping, got %r" % (impact,))
    missing = [key for key in IMPACT_KEYS if key not in impact]
    for key in IMPACT_KEYS:
        if key in impact:
            _require_flag("impact_assessment[%s]" % key, impact[key])
    affected = [key for key in IMPACT_KEYS if impact.get(key) is True]
    return {
        "missing_headings": tuple(missing),
        "complete": not missing,
        "affected_areas": tuple(affected),
    }


def check_request_completeness(request):
    """Which configuration-management fields the request still owes."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % (request,))
    missing = []
    for field in REQUIRED_FIELDS:
        value = request.get(field)
        if field == "impact_assessment":
            if not isinstance(value, dict) or not value:
                missing.append(field)
            continue
        if field == "affected_items":
            if not isinstance(value, (list, tuple)) or not value:
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    findings = []
    if "request_id" not in missing and not request_identifier_ok(request["request_id"]):
        findings.append(
            "request_id %r is not a register identifier" % (request["request_id"],)
        )
    if "duration" not in missing:
        _require_choice("duration", request["duration"], DURATIONS)
    if "impact_assessment" not in missing:
        impact = check_impact_assessment(request["impact_assessment"])
        if not impact["complete"]:
            findings.append(
                "impact assessment leaves %s unanswered"
                % ", ".join(impact["missing_headings"])
            )
    return {
        "missing_fields": tuple(missing),
        "complete": not missing and not findings,
        "findings": tuple(findings),
    }


def approval_authority(request):
    """Who has to sign: the customer board, or the supplier's own."""
    impact = check_impact_assessment(request.get("impact_assessment", {}))
    baseline = _require_flag(
        "requirement_in_customer_baseline",
        request.get("requirement_in_customer_baseline"),
    )
    escalating = [
        area for area in impact["affected_areas"] if area in ("safety", "interfaces")
    ]
    if baseline or escalating:
        reason = (
            "requirement sits in the customer-approved baseline"
            if baseline
            else "departure reaches %s" % ", ".join(escalating)
        )
        return {"authority": CUSTOMER_AUTHORITY, "reason": reason}
    return {
        "authority": SUPPLIER_AUTHORITY,
        "reason": "departure stays inside supplier-controlled requirements",
    }


def authorisation_remaining(request, as_of):
    """Units and calendar life left on an approved deviation or waiver."""
    authorised = _require_count(
        "units_authorised", request.get("units_authorised"), minimum=1
    )
    used = _require_count("units_used", request.get("units_used", 0), minimum=0)
    today = parse_date("as_of", as_of)
    expiry = request.get("expiry_date")
    expired = False
    days_left = None
    if expiry is not None:
        expiry_date = parse_date("expiry_date", expiry)
        days_left = (expiry_date - today).days
        expired = days_left < 0
    return {
        "units_remaining": authorised - used,
        "units_overrun": max(0, used - authorised),
        "days_left": days_left,
        "expired": expired,
        "spent": used >= authorised or expired,
    }


def prepare_waiver_request(case, as_of="2026-01-01"):
    """Full clause 5.2.3.5 handling of one deviation or waiver request."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    incurred = _require_flag(
        "departure_already_incurred", case.get("departure_already_incurred")
    )
    state = _require_choice(
        "approval_state", case.get("approval_state"), APPROVAL_STATES
    )
    used_before_approval = _require_flag(
        "items_used_before_approval", case.get("items_used_before_approval", False)
    )
    completeness = check_request_completeness(case)
    findings = list(completeness["findings"])
    result = {
        "request_type": determine_request_type(incurred),
        "approval_state": state,
        "missing_fields": completeness["missing_fields"],
        "authority": None,
        "authorisation": None,
        "release_permitted": False,
        "findings": findings,
    }
    if not completeness["complete"]:
        if completeness["missing_fields"]:
            findings.append(
                "request owes %s before it can be submitted"
                % ", ".join(completeness["missing_fields"])
            )
        result["verdict"] = VERDICT_INCOMPLETE
        return result
    routing = approval_authority(case)
    result["authority"] = routing["authority"]
    findings.append("approval routed to %s: %s" % (routing["authority"], routing["reason"]))
    if used_before_approval and state != "approved":
        findings.append(
            "affected items were used before the request was approved; raise that "
            "use as a nonconformance in its own right"
        )
        result["verdict"] = VERDICT_VIOLATION
        return result
    if state == "draft":
        result["verdict"] = VERDICT_READY
        return result
    if state == "submitted":
        result["verdict"] = VERDICT_PENDING
        return result
    if state == "rejected":
        findings.append("request rejected; the affected items stay unusable as they are")
        result["verdict"] = VERDICT_REJECTED
        return result
    authorisation = authorisation_remaining(case, as_of)
    result["authorisation"] = authorisation
    if authorisation["spent"]:
        if authorisation["expired"]:
            findings.append("approval expired %d day(s) ago" % -authorisation["days_left"])
        if authorisation["units_remaining"] <= 0:
            findings.append(
                "authorised effectivity of %d unit(s) is used up"
                % case["units_authorised"]
            )
        result["verdict"] = VERDICT_EXPIRED
        return result
    result["verdict"] = VERDICT_APPROVED
    result["release_permitted"] = True
    return result

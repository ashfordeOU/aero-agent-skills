#!/usr/bin/env python3
"""A coverglass type may only be supplied once the customer has granted it.

Anchor: ECSS-E-ST-20-08C clause 8.6.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Qualification status of a coverglass type is not a state the supplier walks
into by finishing its own test programme. It is an act performed by the
customer, and the clause puts that act before supply: the grant has to exist,
and has to have existed, at the moment the coverglass type is handed over.
Two questions are therefore asked about every shipment, and they fail for
different reasons:

    authority   is there a grant on record at all, was it issued by the
                customer rather than by the supplier about its own product,
                and does its scope reach the configuration being shipped
    currency    was the grant in force on the shipment date -- issued before
                it rather than backdated onto it, not withdrawn, and not past
                the validity date the customer put on it

The arms are ranked rather than merged, because they ask for different work.
No grant at all comes first: nothing else can be said about a shipment the
customer never saw. A grant from the wrong party comes next, because it is
not a weak grant, it is a supplier agreeing with itself. Then a scope that
does not reach the article, then a withdrawn grant, then a grant issued
after the shipment it is supposed to authorise -- retroactive paperwork that
describes a decision taken later than the act it covers -- and last a grant
that has simply run out and can be renewed.

Dates are ISO calendar dates supplied by the caller. Nothing is read from
the clock, so the same programme returns the same verdict every run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
from datetime import date

COVERGLASS_CONFIGURATION_KEYS = (
    "coverglass_material",
    "supplier",
    "coating_configuration",
    "thickness_class",
)

GRANTING_AUTHORITY = "customer"
ACCEPTED_AUTHORITIES = ("customer", "supplier", "third-party-laboratory")

GRANT_STATES = ("issued", "withdrawn")

SUPPLY_AUTHORISED = "supply-authorised"
SUPPLY_NO_GRANT = "supply-blocked-no-grant"
SUPPLY_AUTHORITY_INVALID = "supply-blocked-grant-authority-invalid"
SUPPLY_SCOPE_MISMATCH = "supply-blocked-grant-scope-mismatch"
SUPPLY_GRANT_WITHDRAWN = "supply-blocked-grant-withdrawn"
SUPPLY_GRANT_NOT_YET_IN_FORCE = "supply-blocked-grant-not-yet-in-force"
SUPPLY_GRANT_EXPIRED = "supply-blocked-grant-expired"

PROGRAMME_FULLY_AUTHORISED = "coverglass-supply-fully-authorised"
PROGRAMME_NOT_FULLY_AUTHORISED = "coverglass-supply-not-fully-authorised"

VERDICT_RANK = (
    SUPPLY_NO_GRANT,
    SUPPLY_AUTHORITY_INVALID,
    SUPPLY_SCOPE_MISMATCH,
    SUPPLY_GRANT_WITHDRAWN,
    SUPPLY_GRANT_NOT_YET_IN_FORCE,
    SUPPLY_GRANT_EXPIRED,
    SUPPLY_AUTHORISED,
)

DEFAULT_AUTHORITY_POLICY = {
    "require_customer_grant": True,
    "admit_supplier_self_declaration": False,
    "admit_retroactive_grant": False,
    "require_scope_match": True,
    "enforce_validity_end": True,
    "min_authorised_shipment_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_date(name, value):
    """Read an ISO calendar date, refusing anything that is not one."""
    if isinstance(value, date):
        return value
    text = _require_text(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))


def validate_authority_policy(policy):
    """Check a supply authorisation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_customer_grant",
        "admit_supplier_self_declaration",
        "admit_retroactive_grant",
        "require_scope_match",
        "enforce_validity_end",
    ):
        _require_flag(key, policy.get(key))
    _require_fraction(
        "min_authorised_shipment_fraction",
        policy.get("min_authorised_shipment_fraction"),
    )
    return policy


def coverglass_configuration(article):
    """The identity attributes a grant's scope is matched against."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    missing = sorted(
        key for key in COVERGLASS_CONFIGURATION_KEYS if key not in article
    )
    if missing:
        raise ValueError("article is missing %s" % ", ".join(missing))
    return {
        key: _require_text(key, article[key])
        for key in COVERGLASS_CONFIGURATION_KEYS
    }


def configuration_delta(article, scope):
    """Which identity attributes the granted scope does not cover."""
    delivered = coverglass_configuration(article)
    granted = coverglass_configuration(scope)
    return sorted(
        key for key in COVERGLASS_CONFIGURATION_KEYS if delivered[key] != granted[key]
    )


def grant_issuing_authority(grant, policy=DEFAULT_AUTHORITY_POLICY):
    """Who made the grant, and is that a party allowed to make it."""
    validate_authority_policy(policy)
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    issued_by = _require_text("issued_by", grant.get("issued_by")).lower()
    if issued_by not in ACCEPTED_AUTHORITIES:
        raise ValueError(
            "issued_by must be one of %s, got %r"
            % (", ".join(ACCEPTED_AUTHORITIES), issued_by)
        )
    if issued_by == GRANTING_AUTHORITY:
        valid = True
    elif issued_by == "supplier":
        valid = bool(policy["admit_supplier_self_declaration"])
    else:
        valid = not policy["require_customer_grant"]
    return {"issued_by": issued_by, "valid": valid}


def grant_validity_window(grant, supply_date, policy=DEFAULT_AUTHORITY_POLICY):
    """Was the grant in force on the day the coverglass type was handed over."""
    validate_authority_policy(policy)
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    issued_on = _require_date("issued_on", grant.get("issued_on"))
    supplied_on = _require_date("supply_date", supply_date)
    valid_until = grant.get("valid_until")
    expires_on = None if valid_until is None else _require_date(
        "valid_until", valid_until
    )
    if expires_on is not None and expires_on < issued_on:
        raise ValueError(
            "grant expires on %s, before it was issued on %s"
            % (expires_on.isoformat(), issued_on.isoformat())
        )
    state = grant.get("state")
    state = "issued" if state is None else _require_text("state", state).lower()
    if state not in GRANT_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (", ".join(GRANT_STATES), state)
        )
    in_force_from = issued_on <= supplied_on
    if policy["admit_retroactive_grant"]:
        in_force_from = True
    not_expired = True
    if expires_on is not None and policy["enforce_validity_end"]:
        not_expired = supplied_on <= expires_on
    return {
        "issued_on": issued_on.isoformat(),
        "supply_date": supplied_on.isoformat(),
        "valid_until": None if expires_on is None else expires_on.isoformat(),
        "state": state,
        "withdrawn": state == "withdrawn",
        "in_force_from": in_force_from,
        "not_expired": not_expired,
        "days_before_supply": (supplied_on - issued_on).days,
        "in_force": in_force_from and not_expired and state != "withdrawn",
    }


def find_grant(grant_register, coverglass_type):
    """The grant on record for this coverglass type, or nothing."""
    if not isinstance(grant_register, (list, tuple)):
        raise ValueError("grant_register must be a sequence, got %r" % (grant_register,))
    wanted = _require_text("coverglass_type", coverglass_type)
    found = None
    for grant in grant_register:
        if not isinstance(grant, dict):
            raise ValueError("grant must be a mapping, got %r" % (grant,))
        named = _require_text("coverglass_type", grant.get("coverglass_type"))
        if named != wanted:
            continue
        if found is not None:
            raise ValueError(
                "the register holds more than one grant for coverglass type %s"
                % wanted
            )
        found = grant
    return found


def assess_supply_authorisation(
    shipment, grant_register, policy=DEFAULT_AUTHORITY_POLICY
):
    """May this coverglass shipment leave, and if not, on which arm."""
    validate_authority_policy(policy)
    if not isinstance(shipment, dict):
        raise ValueError("shipment must be a mapping, got %r" % (shipment,))
    shipment_id = _require_text("shipment_id", shipment.get("shipment_id"))
    coverglass_type = _require_text(
        "coverglass_type", shipment.get("coverglass_type")
    )
    supply_date = _require_date("supply_date", shipment.get("supply_date"))
    configuration = coverglass_configuration(shipment)

    grant = find_grant(grant_register, coverglass_type)
    findings = []
    if grant is None:
        return {
            "shipment_id": shipment_id,
            "coverglass_type": coverglass_type,
            "supply_date": supply_date.isoformat(),
            "configuration": configuration,
            "grant_id": None,
            "authority": None,
            "window": None,
            "scope_delta": [],
            "verdict": SUPPLY_NO_GRANT,
            "authorised": False,
            "findings": [
                "coverglass type %s ships on shipment %s with no qualification "
                "grant on record at all" % (coverglass_type, shipment_id)
            ],
        }

    grant_id = _require_text("grant_id", grant.get("grant_id"))
    authority = grant_issuing_authority(grant, policy)
    window = grant_validity_window(grant, supply_date, policy)
    scope = grant.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("grant %s declares no scope mapping" % grant_id)
    delta = configuration_delta(shipment, scope)

    if not authority["valid"]:
        verdict = SUPPLY_AUTHORITY_INVALID
        findings.append(
            "grant %s was issued by the %s, and qualification status is granted "
            "by the %s" % (grant_id, authority["issued_by"], GRANTING_AUTHORITY)
        )
    elif policy["require_scope_match"] and delta:
        verdict = SUPPLY_SCOPE_MISMATCH
        findings.append(
            "grant %s does not reach the %s of shipment %s"
            % (grant_id, ", ".join(delta), shipment_id)
        )
    elif window["withdrawn"]:
        verdict = SUPPLY_GRANT_WITHDRAWN
        findings.append(
            "grant %s has been withdrawn, so shipment %s leaves unqualified"
            % (grant_id, shipment_id)
        )
    elif not window["in_force_from"]:
        verdict = SUPPLY_GRANT_NOT_YET_IN_FORCE
        findings.append(
            "grant %s is dated %s and shipment %s left on %s, so the grant "
            "records a decision taken after the supply it authorises"
            % (
                grant_id,
                window["issued_on"],
                shipment_id,
                window["supply_date"],
            )
        )
    elif not window["not_expired"]:
        verdict = SUPPLY_GRANT_EXPIRED
        findings.append(
            "grant %s ran to %s and shipment %s left on %s"
            % (
                grant_id,
                window["valid_until"],
                shipment_id,
                window["supply_date"],
            )
        )
    else:
        verdict = SUPPLY_AUTHORISED

    return {
        "shipment_id": shipment_id,
        "coverglass_type": coverglass_type,
        "supply_date": supply_date.isoformat(),
        "configuration": configuration,
        "grant_id": grant_id,
        "authority": authority,
        "window": window,
        "scope_delta": delta,
        "verdict": verdict,
        "authorised": verdict == SUPPLY_AUTHORISED,
        "findings": findings,
    }


def worst_supply_verdict(verdicts):
    """The verdict that has to be closed first across a set of shipments."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    ranked = []
    for verdict in verdicts:
        verdict = _require_text("verdict", verdict)
        if verdict not in VERDICT_RANK:
            raise ValueError("unknown supply verdict %s" % verdict)
        ranked.append(VERDICT_RANK.index(verdict))
    return VERDICT_RANK[min(ranked)]


def assess_coverglass_supply_programme(programme, policy=DEFAULT_AUTHORITY_POLICY):
    """Full clause 8.6.1 sweep over the shipments a supply programme makes."""
    validate_authority_policy(policy)
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping, got %r" % (programme,))
    programme_id = _require_text("programme_id", programme.get("programme_id"))
    register = programme.get("grant_register")
    if not isinstance(register, (list, tuple)):
        raise ValueError("programme grant_register must be a sequence of mappings")
    shipments = programme.get("shipments")
    if not isinstance(shipments, (list, tuple)) or not shipments:
        raise ValueError("programme shipments must be a non-empty sequence")

    seen = set()
    assessments = []
    for shipment in shipments:
        assessed = assess_supply_authorisation(shipment, register, policy)
        if assessed["shipment_id"] in seen:
            raise ValueError(
                "programme declares shipment %s twice" % assessed["shipment_id"]
            )
        seen.add(assessed["shipment_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["shipment_id"])

    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])

    authorised = [entry for entry in assessments if entry["authorised"]]
    blocked = sorted(
        entry["shipment_id"] for entry in assessments if not entry["authorised"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["shipment_id"])

    total = len(assessments)
    authorised_fraction = len(authorised) / float(total)
    minimum = float(policy["min_authorised_shipment_fraction"])
    share_ok = _at_least(authorised_fraction, minimum)
    if not share_ok:
        findings.append(
            "the programme authorises %d of %d coverglass shipments against a "
            "required share of %.3f" % (len(authorised), total, minimum)
        )

    ungranted_types = sorted(
        {
            entry["coverglass_type"]
            for entry in assessments
            if entry["verdict"] == SUPPLY_NO_GRANT
        }
    )
    return {
        "verdict": PROGRAMME_FULLY_AUTHORISED
        if share_ok and not blocked
        else PROGRAMME_NOT_FULLY_AUTHORISED,
        "programme_id": programme_id,
        "shipment_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "blocked_shipment_ids": blocked,
        "ungranted_coverglass_types": ungranted_types,
        "worst_verdict": worst_supply_verdict(
            [entry["verdict"] for entry in assessments]
        ),
        "authorised_shipment_fraction": authorised_fraction,
        "required_shipment_fraction": minimum,
        "every_shipment_authorised": not blocked,
        "findings": findings,
    }

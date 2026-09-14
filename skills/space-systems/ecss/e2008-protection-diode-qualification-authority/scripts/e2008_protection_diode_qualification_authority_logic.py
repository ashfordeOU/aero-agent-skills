#!/usr/bin/env python3
"""Protection diode qualification is granted by the customer, to one producer's diodes.

Anchor: ECSS-E-ST-20-08C clause 9.5.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A protection diode is qualified because the customer granted it, and the
grant is written against a named producer and a named diode kind. Both
halves of that are load bearing:

    producer     the grant reaches the diodes of the producer it names and
                 nobody else's. A second source shipping an electrically
                 equivalent part is outside it, however equivalent
    kind         external and integral protection diodes are different
                 articles. A diode grown into the cell assembly and a
                 discrete diode mounted beside it share a function and
                 almost nothing else, so a grant on one does not carry the
                 other
    authority    the grant is an act by the customer. A supplier that has
                 run every test has produced a dossier, not a grant, and a
                 laboratory report is the input to the decision rather than
                 the decision
    time         the grant sits before the supply. A grant signed after the
                 diodes shipped records a decision taken later than the act
                 it is meant to authorise, and only reading the register as
                 it stands today hides that completely

The population is supplies, not diode types. One type can ship five times
and only the fourth fall outside the validity window, which a type-level
roll-up never shows.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

DIODE_KINDS = ("external", "integral")

CONFIGURATION_KEYS = (
    "producer",
    "diode_kind",
    "diode_type",
    "process_baseline",
)

ISSUING_PARTIES = ("customer", "supplier", "producer", "test-laboratory")

ADMISSIBLE_ISSUING_PARTIES = ("customer",)

SUPPLY_AUTHORISED = "supply-authorised"
SUPPLY_NO_GRANT = "supply-no-grant"
SUPPLY_ISSUER_INADMISSIBLE = "supply-issuer-inadmissible"
SUPPLY_SCOPE_MISS = "supply-scope-miss"
SUPPLY_GRANT_WITHDRAWN = "supply-grant-withdrawn"
SUPPLY_GRANT_POSTDATED = "supply-grant-postdated"
SUPPLY_GRANT_EXPIRED = "supply-grant-expired"

ARM_RANK = (
    SUPPLY_NO_GRANT,
    SUPPLY_ISSUER_INADMISSIBLE,
    SUPPLY_SCOPE_MISS,
    SUPPLY_GRANT_WITHDRAWN,
    SUPPLY_GRANT_POSTDATED,
    SUPPLY_GRANT_EXPIRED,
)

PROGRAMME_AUTHORISED = "programme-authorised"
PROGRAMME_NOT_AUTHORISED = "programme-not-authorised"

DEFAULT_DIODE_AUTHORITY_POLICY = {
    "admit_supplier_self_grant": False,
    "require_producer_match": True,
    "require_kind_match": True,
    "min_authorised_supply_fraction": 1.0,
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
    text = _require_text(name, value)
    try:
        return datetime.date(*(int(part) for part in text.split("-")))
    except (TypeError, ValueError):
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))


def validate_diode_authority_policy(policy):
    """Check an authority policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("admit_supplier_self_grant", policy.get("admit_supplier_self_grant"))
    _require_flag("require_producer_match", policy.get("require_producer_match"))
    _require_flag("require_kind_match", policy.get("require_kind_match"))
    _require_fraction(
        "min_authorised_supply_fraction",
        policy.get("min_authorised_supply_fraction"),
    )
    return policy


def diode_kinds():
    """The two protection diode kinds a grant is written against."""
    return tuple(DIODE_KINDS)


def normalise_diode_kind(value):
    """Read a diode kind, refusing anything that is neither external nor integral."""
    kind = _require_text("diode_kind", value).lower()
    if kind not in DIODE_KINDS:
        raise ValueError(
            "diode_kind must be one of %s, got %r" % (", ".join(DIODE_KINDS), value)
        )
    return kind


def grant_key(producer, diode_kind):
    """The register key a grant is filed under: one producer, one diode kind."""
    return "%s::%s" % (
        _require_text("producer", producer).lower(),
        normalise_diode_kind(diode_kind),
    )


def supply_configuration(supply):
    """The four attributes a grant has to reach for this supply."""
    if not isinstance(supply, dict):
        raise ValueError("supply must be a mapping, got %r" % (supply,))
    configuration = {}
    for key in CONFIGURATION_KEYS:
        if key == "diode_kind":
            configuration[key] = normalise_diode_kind(supply.get(key))
        else:
            configuration[key] = _require_text(key, supply.get(key)).lower()
    return configuration


def grant_scope_delta(supply, grant, policy=DEFAULT_DIODE_AUTHORITY_POLICY):
    """Which configuration attributes the grant does not actually reach."""
    validate_diode_authority_policy(policy)
    supplied = supply_configuration(supply)
    granted = supply_configuration(grant)
    skipped = set()
    if not policy["require_producer_match"]:
        skipped.add("producer")
    if not policy["require_kind_match"]:
        skipped.add("diode_kind")
    delta = [
        key
        for key in CONFIGURATION_KEYS
        if key not in skipped and supplied[key] != granted[key]
    ]
    return {
        "supplied_configuration": supplied,
        "granted_configuration": granted,
        "attributes_out_of_scope": sorted(delta),
        "in_scope": not delta,
    }


def issuing_authority(grant, policy=DEFAULT_DIODE_AUTHORITY_POLICY):
    """Was the grant issued by a party that may grant a qualification at all."""
    validate_diode_authority_policy(policy)
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    party = _require_text("issued_by", grant.get("issued_by")).lower()
    if party not in ISSUING_PARTIES:
        raise ValueError(
            "issued_by must be one of %s, got %r" % (", ".join(ISSUING_PARTIES), party)
        )
    admissible = party in ADMISSIBLE_ISSUING_PARTIES
    if not admissible and party == "supplier" and policy["admit_supplier_self_grant"]:
        admissible = True
    return {
        "issuing_party": party,
        "admissible": admissible,
        "self_granted": party in ("supplier", "producer"),
    }


def grant_validity(grant, supply_date):
    """Was this grant in force on the day the diodes were supplied."""
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    issued_on = _require_date("issued_on", grant.get("issued_on"))
    supplied_on = _require_date("supply_date", supply_date)
    withdrawn = grant.get("withdrawn", False)
    if not isinstance(withdrawn, bool):
        raise ValueError("withdrawn must be a boolean, got %r" % (withdrawn,))
    valid_until = grant.get("valid_until")
    expiry = None
    if valid_until is not None:
        expiry = _require_date("valid_until", valid_until)
        if expiry < issued_on:
            raise ValueError(
                "grant expires on %s, before it was issued on %s"
                % (expiry.isoformat(), issued_on.isoformat())
            )
    postdated = issued_on > supplied_on
    expired = expiry is not None and expiry < supplied_on
    return {
        "issued_on": issued_on.isoformat(),
        "supply_date": supplied_on.isoformat(),
        "valid_until": expiry.isoformat() if expiry is not None else None,
        "withdrawn": withdrawn,
        "postdated": postdated,
        "expired": expired,
        "in_force": not (withdrawn or postdated or expired),
    }


def lookup_grant(register, producer, diode_kind):
    """Find the one grant filed for this producer and diode kind."""
    if not isinstance(register, (list, tuple)):
        raise ValueError("register must be a sequence of grants, got %r" % (register,))
    wanted = grant_key(producer, diode_kind)
    found = []
    for grant in register:
        if not isinstance(grant, dict):
            raise ValueError("grant must be a mapping, got %r" % (grant,))
        key = grant_key(grant.get("producer"), grant.get("diode_kind"))
        if key == wanted:
            found.append(grant)
    if len(found) > 1:
        raise ValueError("register holds %d grants for %s" % (len(found), wanted))
    return found[0] if found else None


def assess_diode_supply(supply, register, policy=DEFAULT_DIODE_AUTHORITY_POLICY):
    """Verdict for one protection diode supply, with the arms ranked."""
    validate_diode_authority_policy(policy)
    configuration = supply_configuration(supply)
    supply_id = _require_text("supply_id", supply.get("supply_id"))
    supply_date = _require_text("supply_date", supply.get("supply_date"))
    grant = lookup_grant(register, configuration["producer"], configuration["diode_kind"])
    findings = []

    if grant is None:
        return {
            "supply_id": supply_id,
            "configuration": configuration,
            "grant_key": grant_key(
                configuration["producer"], configuration["diode_kind"]
            ),
            "grant_id": None,
            "authority": None,
            "scope": None,
            "validity": None,
            "verdict": SUPPLY_NO_GRANT,
            "authorised": False,
            "findings": [
                "supply %s ships %s %s protection diodes with no grant on record"
                % (supply_id, configuration["producer"], configuration["diode_kind"])
            ],
        }

    grant_id = _require_text("grant_id", grant.get("grant_id"))
    authority = issuing_authority(grant, policy)
    scope = grant_scope_delta(supply, grant, policy)
    validity = grant_validity(grant, supply_date)

    if not authority["admissible"]:
        verdict = SUPPLY_ISSUER_INADMISSIBLE
        findings.append(
            "grant %s was issued by the %s, which cannot grant qualification to its "
            "own product" % (grant_id, authority["issuing_party"])
        )
    elif not scope["in_scope"]:
        verdict = SUPPLY_SCOPE_MISS
        findings.append(
            "grant %s does not reach the %s of supply %s"
            % (grant_id, ", ".join(scope["attributes_out_of_scope"]), supply_id)
        )
    elif validity["withdrawn"]:
        verdict = SUPPLY_GRANT_WITHDRAWN
        findings.append(
            "grant %s has been withdrawn, so supply %s ships on a decision the "
            "customer has taken back" % (grant_id, supply_id)
        )
    elif validity["postdated"]:
        verdict = SUPPLY_GRANT_POSTDATED
        findings.append(
            "grant %s was issued on %s, after supply %s left on %s"
            % (grant_id, validity["issued_on"], supply_id, validity["supply_date"])
        )
    elif validity["expired"]:
        verdict = SUPPLY_GRANT_EXPIRED
        findings.append(
            "grant %s ran out on %s, before supply %s left on %s"
            % (grant_id, validity["valid_until"], supply_id, validity["supply_date"])
        )
    else:
        verdict = SUPPLY_AUTHORISED

    return {
        "supply_id": supply_id,
        "configuration": configuration,
        "grant_key": grant_key(configuration["producer"], configuration["diode_kind"]),
        "grant_id": grant_id,
        "authority": authority,
        "scope": scope,
        "validity": validity,
        "verdict": verdict,
        "authorised": verdict == SUPPLY_AUTHORISED,
        "findings": findings,
    }


def worst_arm(verdicts):
    """The arm that has to be closed first across a set of supply verdicts."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)):
        raise ValueError("verdicts must be a sequence, got %r" % (verdicts,))
    present = set(verdicts)
    for arm in ARM_RANK:
        if arm in present:
            return arm
    return None


def assess_diode_qualification_authority(case, policy=DEFAULT_DIODE_AUTHORITY_POLICY):
    """Full clause 9.5.1 sweep over a set of protection diode supplies."""
    validate_diode_authority_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    register = case.get("grant_register")
    if not isinstance(register, (list, tuple)):
        raise ValueError("case must carry a grant_register sequence")
    supplies = case.get("supplies")
    if not isinstance(supplies, (list, tuple)) or not supplies:
        raise ValueError("case supplies must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for supply in supplies:
        assessed = assess_diode_supply(supply, register, policy)
        if assessed["supply_id"] in seen:
            raise ValueError("case declares supply %s twice" % assessed["supply_id"])
        seen.add(assessed["supply_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["supply_id"])

    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])

    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["supply_id"])

    ungranted = sorted(
        {entry["grant_key"] for entry in assessments if entry["grant_id"] is None}
    )
    authorised = [entry["supply_id"] for entry in assessments if entry["authorised"]]
    blocked = sorted(
        entry["supply_id"] for entry in assessments if not entry["authorised"]
    )
    authorised_fraction = len(authorised) / float(len(assessments))
    minimum = float(policy["min_authorised_supply_fraction"])
    share_ok = _at_least(authorised_fraction, minimum)
    if not share_ok:
        findings.append(
            "%d of %d supplies are authorised against a required share of %.3f"
            % (len(authorised), len(assessments), minimum)
        )
    return {
        "verdict": (
            PROGRAMME_AUTHORISED
            if share_ok and not blocked
            else PROGRAMME_NOT_AUTHORISED
        ),
        "supply_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "ungranted_producer_kinds": ungranted,
        "authorised_supply_ids": sorted(authorised),
        "blocked_supply_ids": blocked,
        "authorised_supply_fraction": authorised_fraction,
        "required_supply_fraction": minimum,
        "close_first": worst_arm([entry["verdict"] for entry in assessments]),
        "findings": findings,
    }

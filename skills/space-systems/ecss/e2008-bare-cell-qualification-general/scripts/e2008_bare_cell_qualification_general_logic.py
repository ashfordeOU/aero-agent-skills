#!/usr/bin/env python3
"""Bare solar cells are qualified by a customer grant, once the evidence is in.

Anchor: ECSS-E-ST-20-08C clause 7.4.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Qualification of a bare solar cell is not something a supplier reaches by
finishing its own test programme. The programme produces evidence; the
customer reads the evidence and grants the qualification, and until that
grant exists the cell is a cell with a good test history. Two things are
therefore being judged at once, and they fail independently:

    substance   is the qualification evidence set complete, is every declared
                activity actually backed by a report, and is anything still
                open against the article
    act         is there a grant on record, was it issued by the customer
                rather than by the supplier about itself, and does its scope
                cover the configuration being delivered

The arms are ranked rather than merged, because they ask for different work.
Evidence that is not complete is reported ahead of everything else: a grant
resting on it is void whatever else is true of it. An open non-conformance
comes next, then a grant issued by the wrong party, then a grant whose scope
does not reach the article, and last a grant that simply has not been asked
for yet -- which is the only finding a single email can close.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONFIGURATION_KEYS = ("cell_type", "supplier", "process_baseline")

REQUIRED_QUALIFICATION_EVIDENCE = (
    "bare-cell-visual-inspection",
    "bare-cell-electrical-performance-measurement",
    "bare-cell-spectral-response-measurement",
    "bare-cell-contact-adherence-measurement",
    "bare-cell-thermal-cycling",
    "bare-cell-electron-irradiation",
    "bare-cell-humidity-exposure",
)

GRANTING_AUTHORITY = "customer"
ACCEPTED_AUTHORITIES = ("customer", "supplier", "third-party-laboratory")

QUALIFICATION_GRANTED = "qualification-granted"
GRANT_EVIDENCE_INCOMPLETE = "grant-withheld-evidence-incomplete"
GRANT_BLOCKED_OPEN_NONCONFORMANCE = "grant-blocked-open-nonconformance"
GRANT_AUTHORITY_INVALID = "grant-authority-invalid"
GRANT_SCOPE_MISMATCH = "grant-scope-mismatch"
GRANT_NOT_ISSUED = "grant-not-issued"

PROGRAMME_FULLY_QUALIFIED = "programme-fully-qualified"
PROGRAMME_NOT_FULLY_QUALIFIED = "programme-not-fully-qualified"

DEFAULT_GRANT_POLICY = {
    "require_customer_grant": True,
    "admit_supplier_self_declaration": False,
    "allow_grant_with_open_nonconformance": False,
    "require_evidence_complete": True,
    "require_scope_match": True,
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


def validate_grant_policy(policy):
    """Check a qualification grant policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_customer_grant",
        "admit_supplier_self_declaration",
        "allow_grant_with_open_nonconformance",
        "require_evidence_complete",
        "require_scope_match",
    ):
        _require_flag(key, policy.get(key))
    return policy


def required_qualification_evidence():
    """The evidence set a bare-cell qualification grant is read against."""
    return tuple(REQUIRED_QUALIFICATION_EVIDENCE)


def article_configuration(article):
    """The identity attributes a grant's scope is matched against."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    missing = sorted(key for key in CONFIGURATION_KEYS if key not in article)
    if missing:
        raise ValueError("article is missing %s" % ", ".join(missing))
    return {key: _require_text(key, article[key]) for key in CONFIGURATION_KEYS}


def configuration_delta(article, scope):
    """Which identity attributes the grant's scope does not match."""
    left = article_configuration(article)
    right = article_configuration(scope)
    return sorted(key for key in CONFIGURATION_KEYS if left[key] != right[key])


def evidence_completeness(dossier, policy=DEFAULT_GRANT_POLICY):
    """Is every required qualification activity present and backed by a report."""
    validate_grant_policy(policy)
    if not isinstance(dossier, dict):
        raise ValueError("dossier must be a mapping, got %r" % (dossier,))
    entries = dossier.get("evidence")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("dossier evidence must be a sequence, got %r" % (entries,))
    backed = []
    unbacked = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
        activity = _require_text("activity", entry.get("activity"))
        if activity not in REQUIRED_QUALIFICATION_EVIDENCE:
            raise ValueError("dossier declares an unknown activity %s" % activity)
        if activity in seen:
            raise ValueError("dossier declares %s twice" % activity)
        seen.add(activity)
        report = entry.get("report_ref")
        if isinstance(report, str) and report.strip():
            backed.append(activity)
        else:
            unbacked.append(activity)
    absent = sorted(set(REQUIRED_QUALIFICATION_EVIDENCE) - seen)
    findings = []
    if absent:
        findings.append(
            "the dossier holds no evidence of %s" % ", ".join(absent)
        )
    if unbacked:
        findings.append(
            "the dossier claims %s without naming a report" % ", ".join(sorted(unbacked))
        )
    total = len(REQUIRED_QUALIFICATION_EVIDENCE)
    fraction = len(backed) / float(total)
    return {
        "backed_activities": sorted(backed),
        "unbacked_activities": sorted(unbacked),
        "absent_activities": absent,
        "evidence_fraction": fraction,
        "complete": _at_least(fraction, 1.0),
        "findings": findings,
    }


def open_nonconformances(dossier):
    """The non-conformances still standing against the article."""
    if not isinstance(dossier, dict):
        raise ValueError("dossier must be a mapping, got %r" % (dossier,))
    entries = dossier.get("nonconformances")
    if entries is None:
        return []
    if not isinstance(entries, (list, tuple)):
        raise ValueError(
            "dossier nonconformances must be a sequence, got %r" % (entries,)
        )
    still_open = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("nonconformance must be a mapping, got %r" % (entry,))
        ncr_id = _require_text("ncr_id", entry.get("ncr_id"))
        if ncr_id in seen:
            raise ValueError("dossier declares nonconformance %s twice" % ncr_id)
        seen.add(ncr_id)
        state = _require_text("state", entry.get("state")).lower()
        if state not in ("open", "closed"):
            raise ValueError(
                "nonconformance %s has state %r, expected open or closed"
                % (ncr_id, state)
            )
        if state == "open":
            still_open.append(ncr_id)
    return sorted(still_open)


def grant_authority(grant, policy=DEFAULT_GRANT_POLICY):
    """Was the grant issued by the party entitled to issue it."""
    validate_grant_policy(policy)
    if grant is None:
        return {
            "issued": False,
            "issued_by": None,
            "authority_valid": False,
            "findings": [],
        }
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    issuer = _require_text("issued_by", grant.get("issued_by")).lower()
    if issuer not in ACCEPTED_AUTHORITIES:
        raise ValueError(
            "grant issued_by must be one of %s, got %r"
            % (", ".join(ACCEPTED_AUTHORITIES), issuer)
        )
    _require_text("grant_ref", grant.get("grant_ref"))
    findings = []
    if issuer == GRANTING_AUTHORITY:
        valid = True
    elif issuer == "supplier":
        valid = bool(policy["admit_supplier_self_declaration"])
        if not valid:
            findings.append(
                "the qualification is declared by the supplier about its own "
                "article; the grant is the customer's to make"
            )
    else:
        valid = not policy["require_customer_grant"]
        if not valid:
            findings.append(
                "the qualification rests on a %s statement rather than a customer "
                "grant" % issuer
            )
    return {
        "issued": True,
        "issued_by": issuer,
        "authority_valid": valid,
        "findings": findings,
    }


def grant_scope(grant, article, policy=DEFAULT_GRANT_POLICY):
    """Does the grant cover the configuration actually being delivered."""
    validate_grant_policy(policy)
    if grant is None:
        return {
            "scoped": False,
            "configuration_delta": sorted(CONFIGURATION_KEYS),
            "scope_matches": False,
            "findings": [],
        }
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    scope = grant.get("scope")
    if scope is None:
        return {
            "scoped": False,
            "configuration_delta": sorted(CONFIGURATION_KEYS),
            "scope_matches": not policy["require_scope_match"],
            "findings": ["the grant names no configuration it applies to"],
        }
    delta = configuration_delta(article, scope)
    findings = []
    if delta:
        findings.append(
            "the grant covers a configuration that differs from the article in %s"
            % ", ".join(delta)
        )
    matches = not delta or not policy["require_scope_match"]
    return {
        "scoped": True,
        "configuration_delta": delta,
        "scope_matches": matches,
        "findings": findings,
    }


def assess_qualification_grant(case, policy=DEFAULT_GRANT_POLICY):
    """Verdict for one bare-cell article put forward for qualification."""
    validate_grant_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    article = case.get("article")
    if not isinstance(article, dict):
        raise ValueError("case article must be a mapping, got %r" % (article,))
    article_id = _require_text("article_id", article.get("article_id"))
    configuration = article_configuration(article)
    dossier = case.get("dossier")
    if not isinstance(dossier, dict):
        raise ValueError("case dossier must be a mapping, got %r" % (dossier,))

    evidence = evidence_completeness(dossier, policy)
    ncrs = open_nonconformances(dossier)
    grant = case.get("grant")
    authority = grant_authority(grant, policy)
    scope = grant_scope(grant, article, policy)

    findings = list(evidence["findings"])
    if ncrs:
        findings.append(
            "article %s carries %s still open against it"
            % (article_id, ", ".join(ncrs))
        )
    findings.extend(authority["findings"])
    findings.extend(scope["findings"])

    evidence_ok = evidence["complete"] or not policy["require_evidence_complete"]
    ncr_ok = not ncrs or bool(policy["allow_grant_with_open_nonconformance"])

    if not evidence_ok:
        verdict = GRANT_EVIDENCE_INCOMPLETE
        if authority["issued"]:
            findings.append(
                "article %s holds a grant that rests on an incomplete evidence set"
                % article_id
            )
    elif not ncr_ok:
        verdict = GRANT_BLOCKED_OPEN_NONCONFORMANCE
    elif not authority["issued"]:
        verdict = GRANT_NOT_ISSUED
        findings.append(
            "article %s has the evidence but no customer grant on record"
            % article_id
        )
    elif not authority["authority_valid"]:
        verdict = GRANT_AUTHORITY_INVALID
    elif not scope["scope_matches"]:
        verdict = GRANT_SCOPE_MISMATCH
    else:
        verdict = QUALIFICATION_GRANTED
    return {
        "article_id": article_id,
        "configuration": configuration,
        "evidence": evidence,
        "open_nonconformance_ids": ncrs,
        "authority": authority,
        "scope": scope,
        "verdict": verdict,
        "qualified": verdict == QUALIFICATION_GRANTED,
        "findings": findings,
    }


def assess_qualification_programme(case, policy=DEFAULT_GRANT_POLICY):
    """Full clause 7.4.1 sweep over the bare-cell articles a programme delivers."""
    validate_grant_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    submissions = case.get("submissions")
    if not isinstance(submissions, (list, tuple)) or not submissions:
        raise ValueError("case submissions must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for submission in submissions:
        record = assess_qualification_grant(submission, policy)
        if record["article_id"] in seen:
            raise ValueError("case declares article %s twice" % record["article_id"])
        seen.add(record["article_id"])
        records.append(record)
    records.sort(key=lambda entry: entry["article_id"])

    delivered = case.get("delivered_article_ids")
    if delivered is None:
        delivered_ids = sorted(seen)
    else:
        if not isinstance(delivered, (list, tuple)) or not delivered:
            raise ValueError(
                "case delivered_article_ids must be a non-empty sequence when given"
            )
        delivered_ids = sorted(
            {_require_text("delivered article id", item) for item in delivered}
        )

    findings = []
    for record in records:
        findings.extend(record["findings"])
    unsubmitted = sorted(set(delivered_ids) - seen)
    for article_id in unsubmitted:
        findings.append(
            "article %s is delivered but was never put forward for qualification"
            % article_id
        )
    considered = [r for r in records if r["article_id"] in delivered_ids]
    qualified = sorted(r["article_id"] for r in considered if r["qualified"])
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["article_id"])
    total = len(delivered_ids)
    fraction = len(qualified) / float(total) if total else 0.0
    open_ids = sorted(
        set(unsubmitted) | {r["article_id"] for r in considered if not r["qualified"]}
    )
    return {
        "verdict": PROGRAMME_FULLY_QUALIFIED
        if not open_ids
        else PROGRAMME_NOT_FULLY_QUALIFIED,
        "article_records": records,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "delivered_article_ids": delivered_ids,
        "unsubmitted_article_ids": unsubmitted,
        "qualified_article_ids": qualified,
        "open_article_ids": open_ids,
        "qualified_fraction": fraction,
        "every_article_qualified": _at_least(fraction, 1.0) and not unsubmitted,
        "findings": findings,
    }

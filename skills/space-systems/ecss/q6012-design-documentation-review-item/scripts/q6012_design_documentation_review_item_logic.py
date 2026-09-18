#!/usr/bin/env python3
"""Design documentation review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.13. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The review item grades the record rather than the design. A die can be
sound and its documentation still fail, because the record is what
another organisation will have to build, screen and accept the part
from years after the design team has moved on. Three properties decide
the item.

Complete
    Every document the programme requires of a die exists. A required
    type with nothing behind it is a hole, and no amount of quality in
    the documents that are present fills it.

Current
    The record is a set of issues, not a set of documents. What matters
    is the latest issue of each: whether it is released rather than
    still in draft, whether an earlier issue is still circulating as
    released, and whether it predates the baseline freeze.

Traceable
    Documents point at the documents they derive from. A reference to
    something the record does not contain breaks the chain; a document
    with nothing above it hangs outside the chain; a chain that returns
    to where it started is not a chain at all.

An item closes only when the record is complete, its latest issues are
released and current, and every trace resolves.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DOCUMENT_FIELDS = (
    "document_id",
    "document_type",
    "issue",
    "issued_day",
    "status",
    "parent_id",
)

DOCUMENT_STATES = (
    "document-released",
    "document-draft",
    "document-superseded",
    "document-withdrawn",
)

REQUIRED_DOCUMENT_TYPES = (
    "die-detail-specification",
    "die-layout-drawing",
    "die-process-identification",
    "die-electrical-test-plan",
    "die-qualification-report",
    "die-summary-design-sheet",
)

ROOT_DOCUMENT_TYPE = "die-detail-specification"

COMPLETENESS_COMPLETE = "design-record-complete"
COMPLETENESS_INCOMPLETE = "design-record-incomplete"

CURRENCY_CURRENT = "design-record-current"
CURRENCY_STALE = "design-record-stale-issue"
CURRENCY_NOT_RELEASED = "design-record-not-released"

TRACE_RESOLVED = "design-record-traceable"
TRACE_ORPHAN = "design-record-orphan-document"
TRACE_BROKEN = "design-record-broken-trace"

VERDICT_CLOSED = "design-documentation-item-closed"
VERDICT_ACTIONED = "design-documentation-item-open-with-actions"
VERDICT_REJECTED = "design-documentation-item-rejected"

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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of one or more, got %r" % (name, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _reject_unknown_fields(name, record, allowed):
    unknown = sorted(set(record) - set(allowed))
    if unknown:
        raise ValueError("%s carries unknown fields: %s" % (name, ", ".join(unknown)))


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _below(value, limit):
    """value < limit, with a value sitting on the limit counted as on it."""
    return value < limit and not _close(value, limit)


def canonical_document_id(raw_identifier):
    """One spelling for an identifier typed by several hands.

    Design records are assembled from drawing offices, process owners and
    test groups, so the same document arrives with stray inner space and
    mixed case. Matching on the identifier as typed turns one document
    into two and breaks the trace that would otherwise resolve.
    """
    text = _require_identifier("document identifier", raw_identifier)
    return " ".join(text.split()).upper()


def normalize_documents(records, required_types=None):
    """Canonical, duplicate-free issues of the documents in the record."""
    rows = _require_sequence("records", records)
    if not rows:
        raise ValueError("records must contain at least one document issue")
    allowed_types = (
        REQUIRED_DOCUMENT_TYPES
        if required_types is None
        else tuple(_require_sequence("required_types", required_types))
    )
    normalized = []
    seen = set()
    types_by_id = {}
    for position, record in enumerate(rows):
        label = "document %d" % position
        row = _require_mapping(label, record)
        _reject_unknown_fields(label, row, DOCUMENT_FIELDS)
        document_id = canonical_document_id(row.get("document_id"))
        document_type = _require_identifier(
            "%s document_type" % label, row.get("document_type")
        )
        issue = _require_positive_integer("%s issue" % label, row.get("issue"))
        issued_day = _require_non_negative("%s issued_day" % label, row.get("issued_day"))
        status = _require_choice("%s status" % label, row.get("status"), DOCUMENT_STATES)
        raw_parent = row.get("parent_id")
        parent_id = None if raw_parent is None else canonical_document_id(raw_parent)
        if parent_id == document_id:
            raise ValueError("document %s derives from itself" % document_id)
        key = (document_id, issue)
        if key in seen:
            raise ValueError(
                "document %s is stated twice at issue %d" % (document_id, issue)
            )
        seen.add(key)
        if types_by_id.setdefault(document_id, document_type) != document_type:
            raise ValueError(
                "document %s is issued under two types: %s and %s"
                % (document_id, types_by_id[document_id], document_type)
            )
        normalized.append(
            {
                "document_id": document_id,
                "document_type": document_type,
                "issue": issue,
                "issued_day": issued_day,
                "status": status,
                "parent_id": parent_id,
            }
        )
    unexpected = sorted(
        {row["document_type"] for row in normalized} - set(allowed_types)
    )
    if unexpected:
        raise ValueError(
            "the record carries document types the programme does not define: %s"
            % ", ".join(unexpected)
        )
    normalized.sort(key=lambda row: (row["document_id"], row["issue"]))
    return tuple(normalized)


def latest_issues(documents):
    """The controlling issue of every document in the record."""
    latest = {}
    for row in documents:
        current = latest.get(row["document_id"])
        if current is None or row["issue"] > current["issue"]:
            latest[row["document_id"]] = row
    return latest


def assess_completeness(latest, required_types=None):
    """Decide whether every document the programme requires exists."""
    _require_mapping("latest", latest)
    required = (
        REQUIRED_DOCUMENT_TYPES
        if required_types is None
        else tuple(_require_sequence("required_types", required_types))
    )
    if not required:
        raise ValueError("required_types must name at least one document type")
    present = {row["document_type"] for row in latest.values()}
    absent = tuple(sorted(set(required) - present))
    coverage = float(len(required) - len(absent)) / float(len(required))
    findings = []
    if absent:
        status = COMPLETENESS_INCOMPLETE
        findings.append(
            "the record has nothing behind %d required document type(s): %s"
            % (len(absent), ", ".join(absent))
        )
    else:
        status = COMPLETENESS_COMPLETE
    return {
        "status": status,
        "absent_types": absent,
        "present_types": tuple(sorted(present)),
        "coverage_share": coverage,
        "findings": findings,
    }


def assess_currency(documents, latest, baseline_freeze_day):
    """Decide whether the controlling issues are released and not stale."""
    freeze = _require_non_negative("baseline_freeze_day", baseline_freeze_day)
    not_released = []
    stale = []
    lingering = []
    findings = []
    for document_id in sorted(latest):
        row = latest[document_id]
        if row["status"] == "document-released":
            if _below(row["issued_day"], freeze):
                stale.append(document_id)
                findings.append(
                    "%s is released at issue %d but dates from day %.2f, before "
                    "the baseline froze on day %.2f"
                    % (document_id, row["issue"], row["issued_day"], freeze)
                )
        else:
            not_released.append(document_id)
            findings.append(
                "the controlling issue of %s is %s, so the record has no released "
                "document behind it" % (document_id, row["status"])
            )
    for row in documents:
        controlling = latest[row["document_id"]]
        if row["issue"] == controlling["issue"]:
            continue
        if row["status"] == "document-released":
            lingering.append((row["document_id"], row["issue"]))
            findings.append(
                "%s issue %d is still marked released while issue %d controls"
                % (row["document_id"], row["issue"], controlling["issue"])
            )
    if not_released:
        status = CURRENCY_NOT_RELEASED
    elif stale or lingering:
        status = CURRENCY_STALE
    else:
        status = CURRENCY_CURRENT
    return {
        "status": status,
        "not_released": tuple(not_released),
        "stale": tuple(stale),
        "lingering_released_issues": tuple(lingering),
        "baseline_freeze_day": freeze,
        "findings": findings,
    }


def trace_chain(latest, document_id):
    """The derivation chain from a document up to its root."""
    _require_mapping("latest", latest)
    start = canonical_document_id(document_id)
    if start not in latest:
        raise ValueError("the record does not contain %s" % start)
    chain = [start]
    seen = {start}
    cursor = latest[start]["parent_id"]
    while cursor is not None:
        if cursor not in latest:
            return {"chain": tuple(chain), "resolution": "dangling", "missing": cursor}
        if cursor in seen:
            return {"chain": tuple(chain), "resolution": "cycle", "missing": cursor}
        chain.append(cursor)
        seen.add(cursor)
        cursor = latest[cursor]["parent_id"]
    return {"chain": tuple(chain), "resolution": "root", "missing": None}


def assess_traceability(latest, root_type=None):
    """Decide whether every document resolves to a root of the record."""
    _require_mapping("latest", latest)
    root = ROOT_DOCUMENT_TYPE if root_type is None else _require_identifier(
        "root_type", root_type
    )
    dangling = []
    cyclic = []
    orphans = []
    findings = []
    depths = {}
    for document_id in sorted(latest):
        result = trace_chain(latest, document_id)
        depths[document_id] = len(result["chain"])
        if result["resolution"] == "dangling":
            dangling.append((document_id, result["missing"]))
            findings.append(
                "%s derives from %s, which the record does not contain"
                % (document_id, result["missing"])
            )
        elif result["resolution"] == "cycle":
            cyclic.append(document_id)
            findings.append(
                "the derivation chain from %s returns to %s, so it never reaches "
                "a root" % (document_id, result["missing"])
            )
        elif (
            latest[document_id]["parent_id"] is None
            and latest[document_id]["document_type"] != root
        ):
            orphans.append(document_id)
            findings.append(
                "%s names no document it derives from and is not the root of the "
                "record" % document_id
            )
    if dangling or cyclic:
        status = TRACE_BROKEN
    elif orphans:
        status = TRACE_ORPHAN
    else:
        status = TRACE_RESOLVED
    return {
        "status": status,
        "dangling": tuple(dangling),
        "cyclic": tuple(cyclic),
        "orphans": tuple(orphans),
        "depths": depths,
        "findings": findings,
    }


def review_design_documentation_item(case):
    """Full clause 7.3.13 design documentation review item with a verdict."""
    row = _require_mapping("case", case)
    required_types = row.get("required_types")
    documents = normalize_documents(row.get("documents"), required_types)
    latest = latest_issues(documents)
    completeness = assess_completeness(latest, required_types)
    currency = assess_currency(documents, latest, row.get("baseline_freeze_day"))
    traceability = assess_traceability(latest, row.get("root_type"))
    findings = (
        list(completeness["findings"])
        + list(currency["findings"])
        + list(traceability["findings"])
    )
    actions = []
    blocking = (
        completeness["status"] == COMPLETENESS_INCOMPLETE
        or currency["status"] == CURRENCY_NOT_RELEASED
        or traceability["status"] == TRACE_BROKEN
    )
    if currency["status"] == CURRENCY_STALE:
        actions.append("reissue or withdraw the issues that predate the baseline")
    if traceability["status"] == TRACE_ORPHAN:
        actions.append("attach the orphan documents to the record they derive from")
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_CLOSED
    return {
        "verdict": verdict,
        "documents": documents,
        "latest": latest,
        "completeness": completeness,
        "currency": currency,
        "traceability": traceability,
        "actions": actions,
        "findings": findings,
    }

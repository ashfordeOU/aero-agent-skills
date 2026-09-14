#!/usr/bin/env python3
"""Deliverable planar blocking diodes against their process document.

Anchor: ECSS-E-ST-20-08C clause 12.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A delivered planar blocking diode is not deliverable because somebody
inspected it. It is deliverable because it was processed and inspected
against the process identification document that governs it -- a
released, issue-controlled document that names every processing step
and every inspection step the part owes. The document is the build
standard; the traveller is only evidence that the standard was followed.

Three questions have to be answered in order, and skipping the first is
what makes a clean traveller meaningless:

    which issue   a document carries issues, and the one that governs a
                  lot is the issue released and in force on the day the
                  lot was processed -- not the newest one on the shelf
    what was run  every step the governing issue declares, split into
                  processing steps and inspection steps, graded on what
                  the traveller actually records
    what else     any step the traveller records that the governing
                  issue does not declare, which is a process nobody
                  authorised rather than extra diligence

Both step kinds are owed. A lot that ran every processing step and no
inspection step has been built and not verified, and it is the failure
this clause is written against; grading the two kinds as one pool hides
it behind a comfortable overall figure.

Four record states are kept apart because different people disposition
them: no record at all, recorded as not performed, recorded as failed,
recorded as performed. Absence is the worst, because nobody can tell
whether the step was skipped, lost or never scheduled.

The step kinds, the inspection coverage minimum and the issue policy
below are declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

STEP_PROCESS = "process"
STEP_INSPECTION = "inspection"
STEP_KINDS = (STEP_PROCESS, STEP_INSPECTION)

OUTCOME_PERFORMED = "performed"
OUTCOME_NOT_PERFORMED = "not-performed"
OUTCOME_FAILED = "failed"
OUTCOMES = (OUTCOME_PERFORMED, OUTCOME_NOT_PERFORMED, OUTCOME_FAILED)

ISSUE_IN_FORCE = "issue-in-force"
ISSUE_SUPERSEDED = "issue-superseded"
ISSUE_UNRELEASED = "issue-unreleased"
ISSUE_NOT_YET_EFFECTIVE = "issue-not-yet-effective"
ISSUE_UNKNOWN = "issue-unknown"

LOT_NO_DOCUMENT = "lot-process-document-not-established"
LOT_STEP_NO_RECORD = "lot-step-not-recorded"
LOT_UNAUTHORISED_STEP = "lot-unauthorised-process-step"
LOT_STEP_NOT_PERFORMED = "lot-step-not-performed"
LOT_STEP_FAILED = "lot-step-failed"
LOT_CLEAR = "lot-processing-clear"

LOT_RANK = {
    LOT_NO_DOCUMENT: 0,
    LOT_STEP_NO_RECORD: 1,
    LOT_UNAUTHORISED_STEP: 2,
    LOT_STEP_NOT_PERFORMED: 3,
    LOT_STEP_FAILED: 4,
    LOT_CLEAR: 5,
}

DELIVERY_ACCEPTED = "blocking-diode-delivery-accepted"
DELIVERY_NOT_ACCEPTED = "blocking-diode-delivery-not-accepted"

DEFAULT_DELIVERY_POLICY = {
    "min_inspection_coverage": 1.0,
    "min_process_coverage": 1.0,
    "allow_superseded_issue": False,
    "carry_dispositioned_failure": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def _require_date(name, value):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (name, value))


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage figure is a quotient of two step counts, so a traveller
    that recorded exactly the owed number of steps can evaluate a unit in
    the last place below its declared minimum. The comparison absorbs
    that; the declared minimum is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_DELIVERY_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_fraction(
        "min_inspection_coverage", settings.get("min_inspection_coverage")
    )
    _require_fraction("min_process_coverage", settings.get("min_process_coverage"))
    _require_flag("allow_superseded_issue", settings.get("allow_superseded_issue"))
    _require_flag(
        "carry_dispositioned_failure", settings.get("carry_dispositioned_failure")
    )
    return settings


def validate_process_document(document):
    """Check a process identification document and its issue history."""
    doc = _require_mapping("process_document", document)
    doc_id = _require_label("document_id", doc.get("document_id"))
    issues = doc.get("issues")
    if not isinstance(issues, (list, tuple)) or not issues:
        raise ValueError("process document must carry a non-empty issues sequence")

    cleaned = []
    seen = set()
    for entry in issues:
        block = _require_mapping("issue", entry)
        label = _require_label("issue", block.get("issue"))
        if label in seen:
            raise ValueError("issue %r appears twice in one document" % label)
        seen.add(label)
        released = _require_flag("released", block.get("released"))
        effective = _require_date("effective", block.get("effective"))
        steps = _require_mapping("steps", block.get("steps") or {})
        if not steps:
            raise ValueError("issue %r declares no steps at all" % label)
        graded_steps = {}
        for step, kind in steps.items():
            step_name = _require_label("step", step)
            graded_steps[step_name] = _require_choice(
                "kind for step %s" % step_name, kind, STEP_KINDS
            )
        cleaned.append(
            {
                "issue": label,
                "released": released,
                "effective": effective,
                "steps": graded_steps,
            }
        )
    cleaned.sort(key=lambda i: (i["effective"], i["issue"]))
    return {"document_id": doc_id, "issues": cleaned}


def issue_in_force(document, on_date):
    """Name the released issue governing work done on a given day."""
    doc = validate_process_document(document)
    day = _require_date("on_date", on_date)
    candidates = [
        i for i in doc["issues"] if i["released"] and i["effective"] <= day
    ]
    if not candidates:
        return None
    return candidates[-1]


def categorize_issue(document, named_issue, processed_on):
    """Grade the issue a lot was built to against the one in force."""
    doc = validate_process_document(document)
    day = _require_date("processed_on", processed_on)
    governing = issue_in_force(doc, day)
    label = named_issue.strip() if isinstance(named_issue, str) else None
    if not label:
        return {
            "named_issue": None,
            "governing_issue": governing["issue"] if governing else None,
            "state": ISSUE_UNKNOWN,
        }
    match = next((i for i in doc["issues"] if i["issue"] == label), None)
    if match is None:
        state = ISSUE_UNKNOWN
    elif not match["released"]:
        state = ISSUE_UNRELEASED
    elif match["effective"] > day:
        state = ISSUE_NOT_YET_EFFECTIVE
    elif governing is not None and match["issue"] != governing["issue"]:
        state = ISSUE_SUPERSEDED
    else:
        state = ISSUE_IN_FORCE
    return {
        "named_issue": label,
        "governing_issue": governing["issue"] if governing else None,
        "state": state,
    }


def _coverage(passed, owed):
    if not owed:
        return 1.0
    return len(passed) / len(owed)


def assess_lot_processing(lot, document, policy=None):
    """Grade one delivered lot against its governing document issue."""
    settings = resolve_policy(policy)
    doc = validate_process_document(document)
    entry = _require_mapping("lot", lot)
    lot_id = _require_label("lot_id", entry.get("lot_id"))
    document_id = _require_label("document_id", entry.get("document_id"))
    if document_id != doc["document_id"]:
        raise ValueError(
            "lot %r names document %r, which is not the document supplied"
            % (lot_id, document_id)
        )
    processed_on = _require_date("processed_on", entry.get("processed_on"))
    issue_state = categorize_issue(doc, entry.get("issue"), processed_on)

    records = _require_mapping("step_records", entry.get("step_records") or {})
    graded_records = {}
    for step, outcome in records.items():
        step_name = _require_label("step", step)
        graded_records[step_name] = _require_choice(
            "outcome for step %s" % step_name, outcome, OUTCOMES
        )

    findings = []
    built_to = next(
        (i for i in doc["issues"] if i["issue"] == issue_state["named_issue"]), None
    )
    if issue_state["state"] != ISSUE_IN_FORCE:
        findings.append(
            "%s: the lot was processed against a document issue in state %s; "
            "the issue in force on %s was %r"
            % (
                lot_id,
                issue_state["state"],
                processed_on.isoformat(),
                issue_state["governing_issue"],
            )
        )
    if built_to is None:
        return {
            "lot_id": lot_id,
            "document_id": doc["document_id"],
            "issue": issue_state,
            "declared_steps": {},
            "missing": [],
            "not_performed": [],
            "failed": [],
            "performed": [],
            "unauthorised": sorted(graded_records),
            "process_coverage": 0.0,
            "inspection_coverage": 0.0,
            "meets_coverage": False,
            "verdict": LOT_NO_DOCUMENT,
            "findings": findings
            + [
                "%s: no established document issue governs this lot, so no "
                "traveller entry can be shown to follow a build standard" % lot_id
            ],
        }

    declared = built_to["steps"]
    process_steps = sorted(s for s, k in declared.items() if k == STEP_PROCESS)
    inspection_steps = sorted(s for s, k in declared.items() if k == STEP_INSPECTION)

    missing = sorted(s for s in declared if s not in graded_records)
    not_performed = sorted(
        s for s in declared if graded_records.get(s) == OUTCOME_NOT_PERFORMED
    )
    failed = sorted(s for s in declared if graded_records.get(s) == OUTCOME_FAILED)
    performed = sorted(
        s for s in declared if graded_records.get(s) == OUTCOME_PERFORMED
    )
    unauthorised = sorted(s for s in graded_records if s not in declared)

    process_coverage = _coverage(
        [s for s in performed if declared[s] == STEP_PROCESS], process_steps
    )
    inspection_coverage = _coverage(
        [s for s in performed if declared[s] == STEP_INSPECTION], inspection_steps
    )
    meets_coverage = _at_least(
        process_coverage, settings["min_process_coverage"]
    ) and _at_least(inspection_coverage, settings["min_inspection_coverage"])

    for step in missing:
        findings.append(
            "%s: no record at all for %s (%s step); nobody can tell whether it "
            "was skipped, lost or never scheduled" % (lot_id, step, declared[step])
        )
    for step in unauthorised:
        findings.append(
            "%s: %s was performed but issue %r declares no such step; that is a "
            "process nobody authorised"
            % (lot_id, step, built_to["issue"])
        )
    for step in not_performed:
        findings.append(
            "%s: %s (%s step) is recorded as not performed"
            % (lot_id, step, declared[step])
        )
    for step in failed:
        findings.append(
            "%s: %s (%s step) is recorded as failed and needs a disposition"
            % (lot_id, step, declared[step])
        )
    if inspection_steps and not _at_least(
        inspection_coverage, settings["min_inspection_coverage"]
    ):
        findings.append(
            "%s: inspection coverage %.4g sits below the declared %.4g; the lot "
            "has been built and not verified"
            % (lot_id, inspection_coverage, settings["min_inspection_coverage"])
        )

    if issue_state["state"] in (ISSUE_UNRELEASED, ISSUE_NOT_YET_EFFECTIVE):
        verdict = LOT_NO_DOCUMENT
    elif issue_state["state"] == ISSUE_SUPERSEDED and not settings[
        "allow_superseded_issue"
    ]:
        verdict = LOT_NO_DOCUMENT
    elif missing:
        verdict = LOT_STEP_NO_RECORD
    elif unauthorised:
        verdict = LOT_UNAUTHORISED_STEP
    elif not_performed:
        verdict = LOT_STEP_NOT_PERFORMED
    elif failed:
        verdict = LOT_STEP_FAILED
    else:
        verdict = LOT_CLEAR

    return {
        "lot_id": lot_id,
        "document_id": doc["document_id"],
        "issue": issue_state,
        "declared_steps": dict(declared),
        "missing": missing,
        "not_performed": not_performed,
        "failed": failed,
        "performed": performed,
        "unauthorised": unauthorised,
        "process_coverage": process_coverage,
        "inspection_coverage": inspection_coverage,
        "meets_coverage": meets_coverage,
        "verdict": verdict,
        "findings": findings,
    }


def assess_deliverable_blocking_diodes(case):
    """Full clause 12.2.2 roll-up over a delivery of planar blocking diodes."""
    _require_mapping("case", case)
    part_id = _require_label("part_id", case.get("part_id"))
    settings = resolve_policy(case.get("policy"))
    document = validate_process_document(case.get("process_document"))

    lots = case.get("lots")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("case must carry a non-empty lots sequence")

    seen = set()
    graded = []
    for lot in lots:
        result = assess_lot_processing(lot, document, settings)
        if result["lot_id"] in seen:
            raise ValueError("lot %r appears twice in one delivery" % result["lot_id"])
        seen.add(result["lot_id"])
        graded.append(result)

    findings = []
    for result in graded:
        findings.extend(result["findings"])

    grouped = {}
    for result in graded:
        grouped.setdefault(result["verdict"], []).append(result["lot_id"])
    for names in grouped.values():
        names.sort()

    blocking = set(grouped) - {LOT_CLEAR}
    if settings["carry_dispositioned_failure"]:
        blocking -= {LOT_STEP_FAILED}

    coverage_short = any(not r["meets_coverage"] for r in graded)
    if not blocking and not coverage_short:
        verdict = DELIVERY_ACCEPTED
    else:
        verdict = DELIVERY_NOT_ACCEPTED

    weakest = min(graded, key=lambda r: (LOT_RANK[r["verdict"]], r["lot_id"]))
    deliverable = sorted(r["lot_id"] for r in graded if r["verdict"] == LOT_CLEAR)
    return {
        "part_id": part_id,
        "document_id": document["document_id"],
        "lots": graded,
        "grouped_lots": grouped,
        "deliverable_lots": deliverable,
        "weakest_lot": weakest["lot_id"],
        "verdict": verdict,
        "findings": findings,
    }

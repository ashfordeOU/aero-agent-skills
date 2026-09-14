#!/usr/bin/env python3
"""Process identification document for external protection diodes.

Anchor: ECSS-E-ST-20-08C clause 9.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Before an external protection diode is put through qualification, the
supplier writes down which processes make it. The document is the thing
qualification is granted against, so two questions run ahead of every
other: is there a written document at all, and does the part in front of
you belong inside its scope.

Document forms
    written-and-issued  a written document, issued, under configuration
    written-draft       written, not issued, nobody signed it
    presentation-pack   slides shown at a review
    verbal-baseline     described in a meeting
    absent              nothing

Diode roles, which decide scope
    external-protection-diode  a discrete part, in scope for this clause
    integral-protection-diode  built into the assembly, controlled there

Processes an external diode is made by
    die-attach, package-seal, lead-forming, lead-finish,
    screening-burn-in, electrical-test, marking, packing

Five of those are qualification critical -- die attach, package seal,
lead finish, screening and burn-in, and electrical test -- because each
one changes what the part is rather than how it is presented.

Every declared process has to do three things: name the production
document that controls it, name the qualification lot that carries its
evidence, and exist before that lot was built. The last one is date
arithmetic, and it is the check that catches a document written
backwards from a lot that had already been made.

The critical set, the entry floor and the roles below are declared
project policy, not physical constants; a project may substitute
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

DOCUMENT_FORMS = (
    "written-and-issued",
    "written-draft",
    "presentation-pack",
    "verbal-baseline",
    "absent",
)

DIODE_ROLES = ("external-protection-diode", "integral-protection-diode")

DIODE_PROCESSES = (
    "die-attach",
    "package-seal",
    "lead-forming",
    "lead-finish",
    "screening-burn-in",
    "electrical-test",
    "marking",
    "packing",
)

QUALIFICATION_CRITICAL = (
    "die-attach",
    "package-seal",
    "lead-finish",
    "screening-burn-in",
    "electrical-test",
)

PID_ACCEPTED = "document-identifies-the-processes"
PID_INCOMPLETE = "document-incomplete-for-qualification"
PID_NOT_IN_FORCE = "no-written-document-in-force"

PID_RANK = {
    PID_NOT_IN_FORCE: 0,
    PID_INCOMPLETE: 1,
    PID_ACCEPTED: 2,
}

DEFAULT_CONTROL_POLICY = {
    "critical_processes": QUALIFICATION_CRITICAL,
    "min_entry_share": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_date(name, value):
    text = _require_label(name, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            "%s must be an ISO calendar date such as 2026-03-01, got %r"
            % (name, value)
        )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Entry coverage is a quotient of counted processes, so a document
    sitting exactly on its floor can evaluate a unit in the last place
    under it. The comparison absorbs that; the floor stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def document_form_standing(document_form):
    """Decide whether what the supplier wrote is a written document at all."""
    form = _require_choice("document_form", document_form, DOCUMENT_FORMS)
    findings = []
    written = form in ("written-and-issued", "written-draft")
    in_force = form == "written-and-issued"

    if form == "written-draft":
        findings.append(
            "the document is written and never issued, so nothing holds the "
            "supplier to the processes it describes"
        )
    elif form == "presentation-pack":
        findings.append(
            "slides shown at a review are not a process identification "
            "document; they are not under configuration and cannot be reissued"
        )
    elif form == "verbal-baseline":
        findings.append(
            "the processes were described rather than written down, so there is "
            "nothing for qualification to be granted against"
        )
    elif form == "absent":
        findings.append("no process identification document exists")
    return {
        "document_form": form,
        "written": written,
        "in_force": in_force,
        "findings": findings,
    }


def qualification_entry_scope(diode_role, enters_qualification):
    """Decide whether this part belongs inside this document's scope.

    The clause covers external protection diodes going into
    qualification. An integral diode is controlled through the assembly
    that carries it, and an external diode that is not being qualified is
    not what this document is for. Carrying either one inside the
    document puts evidence against a part the document does not govern.
    """
    role = _require_choice("diode_role", diode_role, DIODE_ROLES)
    entering = _require_flag("enters_qualification", enters_qualification)
    findings = []
    in_scope = role == "external-protection-diode" and entering

    if role != "external-protection-diode":
        findings.append(
            "an integral protection diode is controlled through the assembly it "
            "is built into, not through this document"
        )
    elif not entering:
        findings.append(
            "the part is not entering qualification, so this document has "
            "nothing to identify processes for"
        )
    return {
        "diode_role": role,
        "enters_qualification": entering,
        "in_scope": in_scope,
        "findings": findings,
    }


def process_coverage(declared_processes, processes_used, critical=None):
    """Compare the processes declared with the processes the part is made by."""
    if not isinstance(declared_processes, (list, tuple)):
        raise ValueError("declared_processes must be a sequence of process names")
    if not isinstance(processes_used, (list, tuple)) or not processes_used:
        raise ValueError("processes_used must be a non-empty sequence")
    critical_set = tuple(
        QUALIFICATION_CRITICAL if critical is None else critical
    )
    for name in critical_set:
        _require_choice("critical process", name, DIODE_PROCESSES)

    declared = []
    for item in declared_processes:
        name = _require_choice("declared process", item, DIODE_PROCESSES)
        if name in declared:
            raise ValueError("process %r is declared twice" % name)
        declared.append(name)

    used = []
    for item in processes_used:
        name = _require_choice("used process", item, DIODE_PROCESSES)
        if name not in used:
            used.append(name)

    undeclared = sorted(name for name in used if name not in declared)
    unused = sorted(name for name in declared if name not in used)
    missing_critical = sorted(
        name for name in critical_set if name not in declared
    )
    covered = [name for name in used if name in declared]
    return {
        "declared": declared,
        "used": used,
        "undeclared": undeclared,
        "declared_not_used": unused,
        "missing_critical": missing_critical,
        "coverage_share": len(covered) / len(used),
    }


def control_and_evidence_links(entries):
    """Find declared processes with no controlling document or no evidence."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of declarations")
    uncontrolled = []
    unqualified = []
    for entry in entries:
        _require_mapping("entry", entry)
        name = _require_choice(
            "process", entry.get("process"), DIODE_PROCESSES
        )
        controlling = entry.get("controlling_document")
        lot = entry.get("qualification_lot")
        if not isinstance(controlling, str) or not controlling.strip():
            uncontrolled.append(name)
        if not isinstance(lot, str) or not lot.strip():
            unqualified.append(name)
    return {
        "entries": len(entries),
        "uncontrolled": sorted(set(uncontrolled)),
        "never_entered_qualification": sorted(set(unqualified)),
    }


def document_precedes_lot(document_issue_date, lot_build_date):
    """Date arithmetic between the document issue and the lot it covers.

    A document issued after the lot was built describes a lot that had
    already been made, which is a record rather than a commitment.
    """
    issued = _require_date("document_issue_date", document_issue_date)
    built = _require_date("lot_build_date", lot_build_date)
    days = (built - issued).days
    findings = []
    if days < 0:
        findings.append(
            "the document was issued %d day(s) after the qualification lot was "
            "built, so it records the lot instead of committing to it"
            % (-days)
        )
    return {
        "document_issue_date": issued.isoformat(),
        "lot_build_date": built.isoformat(),
        "days_ahead": days,
        "ordered": days >= 0,
        "findings": findings,
    }


def entry_coverage_share(declared, entered, critical=None):
    """Share of the critical processes that reach qualification at all.

    A critical process only enters qualification when the document
    declares it and evidence from a qualification lot stands behind it.
    Declaring it and never qualifying it counts for nothing here.
    """
    critical_set = tuple(
        QUALIFICATION_CRITICAL if critical is None else critical
    )
    if not critical_set:
        raise ValueError(
            "a policy with no qualification-critical processes leaves the "
            "document nothing to be graded against"
        )
    for name in critical_set:
        _require_choice("critical process", name, DIODE_PROCESSES)
    declared_set = [
        _require_choice("declared process", name, DIODE_PROCESSES)
        for name in declared
    ]
    entered_set = [
        _require_choice("entered process", name, DIODE_PROCESSES)
        for name in entered
    ]
    reached = [
        name
        for name in critical_set
        if name in declared_set and name in entered_set
    ]
    return {
        "critical": list(critical_set),
        "entered": sorted(reached),
        "short": sorted(name for name in critical_set if name not in reached),
        "entry_share": len(reached) / len(critical_set),
    }


def assess_process_identification_document(case):
    """Full clause 9.3.2 review of one supplier document."""
    _require_mapping("case", case)
    document_id = _require_label("document_id", case.get("document_id"))
    settings = dict(DEFAULT_CONTROL_POLICY)
    if case.get("policy") is not None:
        settings.update(_require_mapping("policy", case.get("policy")))
    critical = tuple(settings.get("critical_processes"))
    floor = settings.get("min_entry_share")
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError("min_entry_share must be a number, got %r" % (floor,))
    floor = float(floor)

    standing = document_form_standing(case.get("document_form"))
    scope = qualification_entry_scope(
        case.get("diode_role"), case.get("enters_qualification")
    )

    entries = case.get("declared_entries")
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("case must carry a non-empty declared_entries sequence")
    links = control_and_evidence_links(entries)
    declared_names = [entry.get("process") for entry in entries]
    coverage = process_coverage(
        declared_names, case.get("processes_used"), critical
    )
    entered_names = [
        name
        for name in coverage["declared"]
        if name not in links["never_entered_qualification"]
    ]
    entry = entry_coverage_share(coverage["declared"], entered_names, critical)
    chronology = document_precedes_lot(
        case.get("document_issue_date"), case.get("lot_build_date")
    )

    findings = ["%s: %s" % (document_id, f) for f in standing["findings"]]
    findings.extend("%s: %s" % (document_id, f) for f in scope["findings"])
    findings.extend("%s: %s" % (document_id, f) for f in chronology["findings"])
    for name in coverage["undeclared"]:
        findings.append(
            "%s: the part is made by %s and the document never declares it, so "
            "that process was never put forward for qualification"
            % (document_id, name)
        )
    for name in coverage["missing_critical"]:
        findings.append(
            "%s: %s is qualification critical and is absent from the document"
            % (document_id, name)
        )
    for name in coverage["declared_not_used"]:
        findings.append(
            "%s: %s is declared and the part is not made by it; the declaration "
            "describes a different build" % (document_id, name)
        )
    for name in links["uncontrolled"]:
        findings.append(
            "%s: %s is declared with no production document controlling it"
            % (document_id, name)
        )
    for name in links["never_entered_qualification"]:
        findings.append(
            "%s: %s names no qualification lot, so it never entered "
            "qualification" % (document_id, name)
        )

    entry_met = _at_least(entry["entry_share"], floor)
    if not entry_met:
        findings.append(
            "%s: %.4g of the qualification-critical processes reach "
            "qualification against a %.4g floor"
            % (document_id, entry["entry_share"], floor)
        )

    if not standing["in_force"] or not scope["in_scope"]:
        verdict = PID_NOT_IN_FORCE
    elif (
        coverage["undeclared"]
        or coverage["missing_critical"]
        or coverage["declared_not_used"]
        or links["uncontrolled"]
        or links["never_entered_qualification"]
        or not chronology["ordered"]
        or not entry_met
    ):
        verdict = PID_INCOMPLETE
    else:
        verdict = PID_ACCEPTED

    return {
        "document_id": document_id,
        "standing": standing,
        "scope": scope,
        "coverage": coverage,
        "links": links,
        "entry": entry,
        "entry_floor_met": entry_met,
        "chronology": chronology,
        "verdict": verdict,
        "findings": findings,
    }

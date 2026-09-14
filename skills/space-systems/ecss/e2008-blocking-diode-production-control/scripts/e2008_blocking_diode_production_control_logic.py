#!/usr/bin/env python3
"""Process document for the production of qualified blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The supplier writes down how a qualified blocking diode is produced.
The word that carries the clause is "qualified": the document is not a
description of a build, it is the thing that keeps the build the same as
the one qualification was granted on. So the review runs on five axes.

Document forms
    issued-and-in-force  written, issued, under configuration
    written-draft        written, never issued, nothing signed
    presentation-pack    slides shown at a review
    verbal-account       described in a meeting
    absent               nothing

Constructions, which decide scope
    planar-blocking-diode      a discrete planar part, in scope
    mesa-blocking-diode        a discrete mesa part, in scope
    integrated-blocking-diode  built into the assembly, controlled there

Process steps a discrete blocking diode is made by
    junction-formation, surface-passivation, die-attach, package-seal,
    lead-attach, lead-finish, screening-burn-in, electrical-test,
    marking, packing

Six of those are qualification critical -- junction formation, surface
passivation, die attach, package seal, screening and burn-in, and
electrical test -- because each one changes what the diode is rather
than how it is presented.

Every declared step carries a qualified baseline revision and a current
revision. A step whose revision has moved is only still standing as
qualified when the move is carried: a major change needs a
requalification reference, a minor change needs a change notice. A step
that moved with neither is a build that drifted away from the one
qualification was granted on, and nothing in the paperwork says so.

The critical set, the standing floor and the constructions below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

DOCUMENT_FORMS = (
    "issued-and-in-force",
    "written-draft",
    "presentation-pack",
    "verbal-account",
    "absent",
)

CONSTRUCTIONS = (
    "planar-blocking-diode",
    "mesa-blocking-diode",
    "integrated-blocking-diode",
)

PROCESS_STEPS = (
    "junction-formation",
    "surface-passivation",
    "die-attach",
    "package-seal",
    "lead-attach",
    "lead-finish",
    "screening-burn-in",
    "electrical-test",
    "marking",
    "packing",
)

QUALIFICATION_CRITICAL = (
    "junction-formation",
    "surface-passivation",
    "die-attach",
    "package-seal",
    "screening-burn-in",
    "electrical-test",
)

CHANGE_CATEGORIES = ("unchanged", "minor-change", "major-change")

PC_ACCEPTED = "document-controls-the-qualified-build"
PC_INCOMPLETE = "document-incomplete-for-the-qualified-build"
PC_NOT_IN_FORCE = "no-controlled-process-document"

PC_RANK = {
    PC_NOT_IN_FORCE: 0,
    PC_INCOMPLETE: 1,
    PC_ACCEPTED: 2,
}

DEFAULT_CONTROL_POLICY = {
    "critical_steps": QUALIFICATION_CRITICAL,
    "min_standing_share": 1.0,
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

    Both shares below are quotients of counted steps, so a document
    sitting exactly on its floor can evaluate a unit in the last place
    under it. The comparison absorbs that; the floor stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def document_standing(document_form):
    """Decide whether what the supplier submitted is a document at all."""
    form = _require_choice("document_form", document_form, DOCUMENT_FORMS)
    findings = []
    written = form in ("issued-and-in-force", "written-draft")
    in_force = form == "issued-and-in-force"

    if form == "written-draft":
        findings.append(
            "the process document is written and never issued, so nothing "
            "holds the supplier to the build it describes"
        )
    elif form == "presentation-pack":
        findings.append(
            "review slides are not a process document; they are not under "
            "configuration and cannot be reissued when the build moves"
        )
    elif form == "verbal-account":
        findings.append(
            "the production route was described rather than written down, so "
            "there is nothing for the qualified build to be held against"
        )
    elif form == "absent":
        findings.append("no process document exists for the blocking diode")
    return {
        "document_form": form,
        "written": written,
        "in_force": in_force,
        "findings": findings,
    }


def construction_scope(construction, qualification_granted):
    """Decide whether this diode belongs inside this document's scope.

    The clause covers the production of qualified blocking diodes. A
    blocking diode integrated into the assembly is controlled through
    that assembly's own process controls, and a discrete part that was
    never granted qualification has no qualified build for a document to
    hold steady.
    """
    kind = _require_choice("construction", construction, CONSTRUCTIONS)
    granted = _require_flag("qualification_granted", qualification_granted)
    findings = []
    discrete = kind != "integrated-blocking-diode"
    in_scope = discrete and granted

    if not discrete:
        findings.append(
            "an integrated blocking diode is controlled through the assembly "
            "it is built into, not through a diode process document"
        )
    elif not granted:
        findings.append(
            "the part carries no qualification, so this document has no "
            "qualified build to keep the production route aligned with"
        )
    return {
        "construction": kind,
        "qualification_granted": granted,
        "discrete": discrete,
        "in_scope": in_scope,
        "findings": findings,
    }


def step_coverage(declared_steps, steps_used, critical=None):
    """Compare the steps declared with the steps the diode is built by."""
    if not isinstance(declared_steps, (list, tuple)):
        raise ValueError("declared_steps must be a sequence of step names")
    if not isinstance(steps_used, (list, tuple)) or not steps_used:
        raise ValueError("steps_used must be a non-empty sequence")
    critical_set = tuple(
        QUALIFICATION_CRITICAL if critical is None else critical
    )
    for name in critical_set:
        _require_choice("critical step", name, PROCESS_STEPS)

    declared = []
    for item in declared_steps:
        name = _require_choice("declared step", item, PROCESS_STEPS)
        if name in declared:
            raise ValueError("step %r is declared twice" % name)
        declared.append(name)

    used = []
    for item in steps_used:
        name = _require_choice("used step", item, PROCESS_STEPS)
        if name not in used:
            used.append(name)

    undeclared = sorted(name for name in used if name not in declared)
    declared_not_used = sorted(name for name in declared if name not in used)
    missing_critical = sorted(
        name for name in critical_set if name not in declared
    )
    covered = [name for name in used if name in declared]
    return {
        "declared": declared,
        "used": used,
        "undeclared": undeclared,
        "declared_not_used": declared_not_used,
        "missing_critical": missing_critical,
        "coverage_share": len(covered) / len(used),
    }


def baseline_drift(entries):
    """Grade each declared step against the baseline qualification ran on.

    A step whose revision has not moved is still the qualified step. A
    step that moved is only still standing when the move is carried: a
    major change by a requalification reference, a minor change by a
    change notice. A step that moved with neither has drifted, and the
    diode is no longer produced the way it was qualified.
    """
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of step records")

    standing = []
    drifted = []
    unnotified = []
    uncontrolled = []
    seen = []
    rows = []
    for entry in entries:
        _require_mapping("entry", entry)
        name = _require_choice("step", entry.get("step"), PROCESS_STEPS)
        if name in seen:
            raise ValueError("step %r appears twice in the entries" % name)
        seen.append(name)
        baseline = _require_label("baseline_revision", entry.get("baseline_revision"))
        current = _require_label("current_revision", entry.get("current_revision"))
        category = _require_choice(
            "change_category", entry.get("change_category"), CHANGE_CATEGORIES
        )
        if (baseline == current) != (category == "unchanged"):
            raise ValueError(
                "step %r reports change_category %r against revisions %r and %r"
                % (name, category, baseline, current)
            )
        controlling = entry.get("controlling_document")
        requal = entry.get("requalification_reference")
        notice = entry.get("change_notice")
        controlled = isinstance(controlling, str) and bool(controlling.strip())
        has_requal = isinstance(requal, str) and bool(requal.strip())
        has_notice = isinstance(notice, str) and bool(notice.strip())

        if not controlled:
            uncontrolled.append(name)

        if category == "unchanged":
            still = True
        elif category == "major-change":
            still = has_requal
            if not has_requal:
                drifted.append(name)
        else:
            still = has_notice
            if not has_notice:
                unnotified.append(name)

        if still:
            standing.append(name)
        rows.append(
            {
                "step": name,
                "change_category": category,
                "controlled": controlled,
                "stands_as_qualified": still,
            }
        )
    return {
        "rows": rows,
        "steps": sorted(seen),
        "standing": sorted(standing),
        "drifted": sorted(drifted),
        "unnotified": sorted(unnotified),
        "uncontrolled": sorted(uncontrolled),
    }


def standing_share(standing_steps, critical=None):
    """Share of the critical steps still produced as they were qualified."""
    critical_set = tuple(
        QUALIFICATION_CRITICAL if critical is None else critical
    )
    if not critical_set:
        raise ValueError(
            "a policy with no qualification-critical steps leaves the document "
            "nothing to be graded against"
        )
    for name in critical_set:
        _require_choice("critical step", name, PROCESS_STEPS)
    held = [
        _require_choice("standing step", name, PROCESS_STEPS)
        for name in standing_steps
    ]
    reached = [name for name in critical_set if name in held]
    return {
        "critical": list(critical_set),
        "standing": sorted(reached),
        "short": sorted(name for name in critical_set if name not in reached),
        "standing_share": len(reached) / len(critical_set),
    }


def document_precedes_lot(document_issue_date, lot_build_date):
    """Date arithmetic between the document issue and the lot it covers.

    A document issued after the lot was built records that lot instead of
    committing the next one to anything.
    """
    issued = _require_date("document_issue_date", document_issue_date)
    built = _require_date("lot_build_date", lot_build_date)
    days = (built - issued).days
    findings = []
    if days < 0:
        findings.append(
            "the process document was issued %d day(s) after the lot it covers "
            "was built, so it records that lot instead of controlling it"
            % (-days)
        )
    return {
        "document_issue_date": issued.isoformat(),
        "lot_build_date": built.isoformat(),
        "days_ahead": days,
        "ordered": days >= 0,
        "findings": findings,
    }


def assess_blocking_diode_production_control(case):
    """Full clause 12.3 review of one supplier process document."""
    _require_mapping("case", case)
    document_id = _require_label("document_id", case.get("document_id"))
    settings = dict(DEFAULT_CONTROL_POLICY)
    if case.get("policy") is not None:
        settings.update(_require_mapping("policy", case.get("policy")))
    critical = tuple(settings.get("critical_steps"))
    floor = settings.get("min_standing_share")
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError("min_standing_share must be a number, got %r" % (floor,))
    floor = float(floor)

    standing_doc = document_standing(case.get("document_form"))
    scope = construction_scope(
        case.get("construction"), case.get("qualification_granted")
    )

    entries = case.get("declared_steps")
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("case must carry a non-empty declared_steps sequence")
    drift = baseline_drift(entries)
    coverage = step_coverage(drift["steps"], case.get("steps_used"), critical)
    share = standing_share(drift["standing"], critical)
    chronology = document_precedes_lot(
        case.get("document_issue_date"), case.get("lot_build_date")
    )

    findings = ["%s: %s" % (document_id, f) for f in standing_doc["findings"]]
    findings.extend("%s: %s" % (document_id, f) for f in scope["findings"])
    findings.extend("%s: %s" % (document_id, f) for f in chronology["findings"])
    for name in coverage["undeclared"]:
        findings.append(
            "%s: the diode is built by %s and the document never declares it, "
            "so that step is produced outside any control" % (document_id, name)
        )
    for name in coverage["missing_critical"]:
        findings.append(
            "%s: %s is qualification critical and is absent from the document"
            % (document_id, name)
        )
    for name in coverage["declared_not_used"]:
        findings.append(
            "%s: %s is declared and the diode is not built by it; the document "
            "describes a different route" % (document_id, name)
        )
    for name in drift["drifted"]:
        findings.append(
            "%s: %s carries a major change with no requalification behind it, "
            "so the diode is no longer produced as it was qualified"
            % (document_id, name)
        )
    for name in drift["unnotified"]:
        findings.append(
            "%s: %s carries a minor change with no change notice, so the move "
            "away from the baseline was never declared" % (document_id, name)
        )
    for name in drift["uncontrolled"]:
        findings.append(
            "%s: %s names no production document controlling it"
            % (document_id, name)
        )

    floor_met = _at_least(share["standing_share"], floor)
    if not floor_met:
        findings.append(
            "%s: %.4g of the qualification-critical steps still stand as "
            "qualified against a %.4g floor"
            % (document_id, share["standing_share"], floor)
        )

    if not standing_doc["in_force"] or not scope["in_scope"]:
        verdict = PC_NOT_IN_FORCE
    elif (
        coverage["undeclared"]
        or coverage["missing_critical"]
        or coverage["declared_not_used"]
        or drift["drifted"]
        or drift["unnotified"]
        or drift["uncontrolled"]
        or not chronology["ordered"]
        or not floor_met
    ):
        verdict = PC_INCOMPLETE
    else:
        verdict = PC_ACCEPTED

    return {
        "document_id": document_id,
        "standing": standing_doc,
        "scope": scope,
        "coverage": coverage,
        "drift": drift,
        "share": share,
        "standing_floor_met": floor_met,
        "chronology": chronology,
        "verdict": verdict,
        "findings": findings,
    }

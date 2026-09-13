#!/usr/bin/env python3
"""Deliverable solar cell assemblies, against the approved process document.

Anchor: ECSS-E-ST-20-08C clause 6.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What is delivered under this clause is not simply a cell assembly: it
is a cell assembly produced by the process the customer approved and
inspected by the inspections that process calls for. Two questions
therefore decide every unit in a delivery lot. Was the process
identification document that governed the build the approved one, at
the approved issue? And was every inspection that document requires
actually performed, with a result, rather than merely listed on a
travelling sheet?

Process document standing
    approved     the document the customer signed
    draft        circulated, not signed; it governs nothing
    superseded   approved once, replaced since
    withdrawn    pulled; it governs nothing and never will again

Inspection outcomes
    passed          performed, result acceptable
    failed          performed, result not acceptable
    not-performed   no result exists

Unit dispositions
    deliverable                    releases on the records as they are
    deliverable-under-concession   releases only on a written concession
    withheld                       does not release

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DOCUMENT_STATES = ("approved", "draft", "superseded", "withdrawn")
INSPECTION_OUTCOMES = ("passed", "failed", "not-performed")

STANDING_CURRENT = "governing-current-issue"
STANDING_OFF_ISSUE = "governing-off-issue"
STANDING_NONE = "not-governing"

DELIVERABLE = "deliverable"
CONCESSION = "deliverable-under-concession"
WITHHELD = "withheld"

DISPOSITION_RANK = {WITHHELD: 0, CONCESSION: 1, DELIVERABLE: 2}

LOT_RELEASABLE = "lot-releasable"
LOT_RELEASABLE_WITH_CONCESSIONS = "lot-releasable-with-concessions"
LOT_WITHHELD = "lot-withheld"

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


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or not 0.0 <= number <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A release share is a quotient of two unit counts, so a lot that
    exactly meets its required share can evaluate a unit in the last
    place below it. The comparison absorbs that; the counts themselves
    are untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def document_standing(document_state, approved_issue, build_issue):
    """Decide whether the process document actually governed this build."""
    state = _require_choice("document_state", document_state, DOCUMENT_STATES)
    approved = _require_label("approved_issue", approved_issue)
    built_to = _require_label("build_issue", build_issue)
    findings = []

    if state == "draft":
        findings.append(
            "the process document cited for the build is a draft; a draft was "
            "never approved, so nothing was produced under an approved process"
        )
        return {"standing": STANDING_NONE, "findings": findings}

    if state == "withdrawn":
        findings.append(
            "the process document cited for the build has been withdrawn and "
            "cannot be reinstated by the delivery it is cited on"
        )
        return {"standing": STANDING_NONE, "findings": findings}

    if state == "superseded":
        findings.append(
            "the build ran to issue %s of a process document since superseded; "
            "the delta to the approved issue %s has to be dispositioned before "
            "release" % (built_to, approved)
        )
        return {"standing": STANDING_OFF_ISSUE, "findings": findings}

    if built_to != approved:
        findings.append(
            "the build ran to issue %s while issue %s is the approved one; the "
            "unit was produced under a process the customer did not approve"
            % (built_to, approved)
        )
        return {"standing": STANDING_OFF_ISSUE, "findings": findings}

    return {"standing": STANDING_CURRENT, "findings": findings}


def inspection_completeness(records, required_inspections):
    """Grade the inspection records against the inspections the process calls for."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of inspection records")
    if not isinstance(required_inspections, (list, tuple)) or not required_inspections:
        raise ValueError(
            "required_inspections must be a non-empty sequence; a process that "
            "calls for no inspection gives the records nothing to satisfy"
        )
    required = [_require_label("required inspection", r) for r in required_inspections]
    if len(set(required)) != len(required):
        raise ValueError("an inspection is required twice by the process document")

    outcomes = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("inspection record %d must be a mapping" % index)
        kind = _require_label("inspection kind", record.get("kind"))
        outcome = _require_choice(
            "outcome", record.get("outcome"), INSPECTION_OUTCOMES
        )
        if kind in outcomes:
            raise ValueError("inspection %r is recorded twice for one unit" % kind)
        outcomes[kind] = outcome

    missing = sorted(k for k in required if k not in outcomes)
    unperformed = sorted(
        k for k in required if outcomes.get(k) == "not-performed"
    )
    failed = sorted(k for k in required if outcomes.get(k) == "failed")
    passed = sorted(k for k in required if outcomes.get(k) == "passed")
    off_process = sorted(k for k in outcomes if k not in required)

    findings = []
    for kind in missing:
        findings.append(
            "the process calls for the %s inspection and no record of it "
            "exists; an absent record is not a pass" % kind
        )
    for kind in unperformed:
        findings.append(
            "the %s inspection is listed on the records but carries no result" % kind
        )
    for kind in failed:
        findings.append("the %s inspection was performed and not accepted" % kind)

    return {
        "required": sorted(required),
        "passed": passed,
        "failed": failed,
        "missing": missing,
        "unperformed": unperformed,
        "off_process": off_process,
        "completeness": len(passed) / len(required),
        "findings": findings,
    }


def disposition_unit(unit, required_inspections):
    """Decide whether one delivered cell assembly releases, and on what."""
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping, got %r" % (unit,))
    serial = _require_label("serial", unit.get("serial"))
    standing = document_standing(
        unit.get("document_state"),
        unit.get("approved_issue"),
        unit.get("build_issue"),
    )
    inspections = inspection_completeness(
        unit.get("inspections", []), required_inspections
    )
    concession = unit.get("concession_reference")
    if concession is not None:
        concession = _require_label("concession_reference", concession)

    findings = ["%s: %s" % (serial, f) for f in standing["findings"]]
    findings.extend("%s: %s" % (serial, f) for f in inspections["findings"])

    blocking = (
        standing["standing"] == STANDING_NONE
        or bool(inspections["failed"])
        or bool(inspections["missing"])
        or bool(inspections["unperformed"])
    )
    needs_concession = standing["standing"] == STANDING_OFF_ISSUE

    if blocking:
        disposition = WITHHELD
        if concession is not None:
            findings.append(
                "%s: a concession is cited, but a failed or absent inspection "
                "is not a matter a concession can carry" % serial
            )
    elif needs_concession:
        if concession is None:
            disposition = WITHHELD
            findings.append(
                "%s: the unit was built off the approved issue and cites no "
                "concession, so there is nothing to release it on" % serial
            )
        else:
            disposition = CONCESSION
    else:
        disposition = DELIVERABLE
        if concession is not None:
            findings.append(
                "%s: a concession is cited against records that need none; it "
                "can be closed out rather than carried into the delivery" % serial
            )

    return {
        "serial": serial,
        "standing": standing["standing"],
        "inspections": inspections,
        "concession_reference": concession,
        "disposition": disposition,
        "findings": findings,
    }


def assess_delivery_lot(case):
    """Full clause 6.1.3 roll-up over a lot of delivered cell assemblies."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_id = _require_label("lot_id", case.get("lot_id"))
    units = case.get("units")
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("case must carry a non-empty units sequence")
    required = case.get("required_inspections")
    required_share = _require_fraction(
        "required_release_share", case.get("required_release_share", 1.0)
    )

    seen = set()
    assessments = []
    findings = []
    for unit in units:
        assessment = disposition_unit(unit, required)
        if assessment["serial"] in seen:
            raise ValueError(
                "unit %r appears twice in the lot" % assessment["serial"]
            )
        seen.add(assessment["serial"])
        assessments.append(assessment)
        findings.extend(assessment["findings"])

    total = len(assessments)
    withheld = [a["serial"] for a in assessments if a["disposition"] == WITHHELD]
    on_concession = [a["serial"] for a in assessments if a["disposition"] == CONCESSION]
    releasable = total - len(withheld)
    release_share = releasable / total

    if withheld:
        verdict = LOT_WITHHELD if not _at_least(release_share, required_share) else (
            LOT_RELEASABLE_WITH_CONCESSIONS
        )
    elif on_concession:
        verdict = LOT_RELEASABLE_WITH_CONCESSIONS
    else:
        verdict = LOT_RELEASABLE

    if withheld and not _at_least(release_share, required_share):
        findings.append(
            "the lot releases %d of %d units, below the %r share the delivery "
            "was accepted against" % (releasable, total, required_share)
        )

    weakest = min(
        assessments,
        key=lambda a: (
            DISPOSITION_RANK[a["disposition"]],
            a["inspections"]["completeness"],
            a["serial"],
        ),
    )
    return {
        "lot_id": lot_id,
        "assessments": assessments,
        "verdict": verdict,
        "withheld_units": sorted(withheld),
        "concession_units": sorted(on_concession),
        "release_share": release_share,
        "required_release_share": required_share,
        "weakest_unit": weakest["serial"],
        "findings": findings,
    }

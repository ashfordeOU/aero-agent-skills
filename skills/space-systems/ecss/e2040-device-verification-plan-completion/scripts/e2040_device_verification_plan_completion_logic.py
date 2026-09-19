#!/usr/bin/env python3
"""Verification plan completion at design-phase start (ECSS-E-ST-20-40C 5.4.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The design phase does not open on a verification plan that is under
construction. The clause puts the COMPLETE plan at the start of the
phase, and complete is a property of every entry, not of the document.

* an entry is complete only with all five fields behind it: method,
  level, facility, success criterion and schedule slot. Four of five
  reads as an entry on the page and cannot be executed;
* a field filled with a placeholder is not filled. TBD, TBC and their
  spellings are the commonest way a plan reaches full completeness on
  paper with the work still to do, so a placeholder is treated as an
  empty field and reported by name;
* a success criterion has to say what result closes the requirement. A
  facility has to exist by the date the entry is scheduled into, or the
  slot is fictional;
* the plan has to be approved at the phase start. A draft plan is not
  the plan the clause asks for, however complete its entries are;
* completeness is complete entries over requirements owed, and a
  requirement with no entry at all stays in the denominator. Dropping
  it produces a plan reporting full completeness of the requirements it
  chose to count.

The completeness fraction lands on a threshold only by arithmetic
accident, so the comparison absorbs representation error.
"""

import datetime
import math

# Fields an executable verification entry needs.
ENTRY_FIELDS = ("method", "level", "facility", "success_criterion", "schedule_slot")

# Approval states the plan may be in, least mature first.
APPROVAL_STATES = ("draft", "under-review", "approved")

_APPROVAL_ALIASES = {
    "draft": "draft",
    "working": "draft",
    "under-review": "under-review",
    "under review": "under-review",
    "in review": "under-review",
    "approved": "approved",
    "released": "approved",
    "signed": "approved",
}

# Tokens that look like a filled field and are not one.
PLACEHOLDER_TOKENS = ("tbd", "tbc", "tba", "to be defined", "to be confirmed", "n/a", "-")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_PLAN_REQUIRED_KEYS = ("requirements", "entries", "approval_state", "phase_start")
_PLAN_OPTIONAL_KEYS = ("facilities", "completeness_threshold")
_ENTRY_KEYS = ("requirement",) + ENTRY_FIELDS
_FACILITY_KEYS = ("name", "available_from")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def parse_date(name, value):
    """Read an ISO calendar date, refusing anything that is not one."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(name, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (name, value))


def is_placeholder(value):
    """True when a field is filled with something that fills nothing."""
    if not isinstance(value, str):
        raise ValueError("a field value must be a string, got %r" % (value,))
    folded = " ".join(value.strip().lower().replace("_", " ").split())
    if not folded:
        return False
    stripped = folded.rstrip(".").strip()
    return stripped in PLACEHOLDER_TOKENS


def normalize_approval(value):
    """Fold an approval state onto draft, under-review or approved."""
    key = _key("approval_state", value)
    if key in _APPROVAL_ALIASES:
        return _APPROVAL_ALIASES[key]
    raise ValueError(
        "unknown approval state %r; use one of %s" % (value, ", ".join(APPROVAL_STATES))
    )


def approval_rank(value):
    """Ordinal of an approval state, so two states can be compared."""
    return APPROVAL_STATES.index(normalize_approval(value))


def validate_facilities(entries):
    """Check the facility list and return availability keyed by name."""
    if entries is None:
        return {}
    if not isinstance(entries, (list, tuple)):
        raise ValueError("facilities must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("facilities[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_FACILITY_KEYS))
        if unknown:
            raise ValueError("facilities[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        if "name" not in entry:
            raise ValueError("facilities[%d] missing key: name" % index)
        name = _text("facilities[%d].name" % index, entry["name"])
        if name in resolved:
            raise ValueError("duplicate facility %r" % name)
        available = entry.get("available_from")
        resolved[name] = parse_date("facilities[%d].available_from" % index, available) if available else None
    return resolved


def missing_fields(entry):
    """Fields an entry leaves empty, placeholders counted as empty."""
    gaps = []
    for field in ENTRY_FIELDS:
        value = entry.get(field, "")
        if not value or is_placeholder(value):
            gaps.append(field)
    return gaps


def entry_is_complete(entry):
    """True when every field an executable entry needs is really filled."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    return not missing_fields(entry)


def validate_entries(entries):
    """Check the entry list and return it keyed by requirement."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ENTRY_KEYS))
        if unknown:
            raise ValueError("entries[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        if "requirement" not in entry:
            raise ValueError("entries[%d] missing key: requirement" % index)
        requirement = _text("entries[%d].requirement" % index, entry["requirement"])
        if requirement in resolved:
            raise ValueError("requirement %r carries two verification entries" % requirement)
        resolved[requirement] = {
            "requirement": requirement,
            "method": _text("entries[%d].method" % index, entry.get("method", ""), allow_empty=True),
            "level": _text("entries[%d].level" % index, entry.get("level", ""), allow_empty=True),
            "facility": _text(
                "entries[%d].facility" % index, entry.get("facility", ""), allow_empty=True
            ),
            "success_criterion": _text(
                "entries[%d].success_criterion" % index,
                entry.get("success_criterion", ""),
                allow_empty=True,
            ),
            "schedule_slot": _text(
                "entries[%d].schedule_slot" % index,
                entry.get("schedule_slot", ""),
                allow_empty=True,
            ),
        }
    return resolved


def completeness(requirements, entries):
    """Fraction of requirements owed that carry a complete entry."""
    if not requirements:
        raise ValueError("completeness needs at least one requirement")
    complete = sum(
        1
        for requirement in requirements
        if requirement in entries and entry_is_complete(entries[requirement])
    )
    return complete / len(requirements)


def meets_completeness_threshold(achieved, threshold):
    """True when completeness reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def assess_plan_completion(plan):
    """Full clause 5.4.2 readiness judgement on one verification plan.

    Returns the completeness fraction, the entries still short of
    executable, the findings and whether the design phase may open on it.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of requirements, entries and approval")
    known = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    missing = [key for key in _PLAN_REQUIRED_KEYS if key not in plan]
    if missing:
        raise ValueError("plan missing required keys: %s" % ", ".join(missing))

    requirements_in = plan["requirements"]
    if not isinstance(requirements_in, (list, tuple)):
        raise ValueError("requirements must be a list of identifiers")
    requirements = []
    for index, value in enumerate(requirements_in):
        item = _text("requirements[%d]" % index, value)
        if item in requirements:
            raise ValueError("duplicate requirement %r" % item)
        requirements.append(item)
    if not requirements:
        raise ValueError("plan must cover at least one requirement")

    entries = validate_entries(plan["entries"])
    approval = normalize_approval(plan["approval_state"])
    phase_start = parse_date("phase_start", plan["phase_start"])
    facilities = validate_facilities(plan.get("facilities"))

    findings = []
    blocking = False
    incomplete = []

    if approval_rank(approval) < approval_rank("approved"):
        findings.append(
            {
                "code": "plan-not-approved-at-phase-start",
                "approval_state": approval,
                "detail": "the plan is %s at the design phase start and the clause asks "
                "for the complete, approved plan" % approval,
            }
        )
        blocking = True

    for requirement in requirements:
        entry = entries.get(requirement)
        if entry is None:
            findings.append(
                {
                    "code": "requirement-without-entry",
                    "requirement": requirement,
                    "detail": "requirement %s carries no verification entry at all"
                    % requirement,
                }
            )
            incomplete.append(requirement)
            blocking = True
            continue
        gaps = missing_fields(entry)
        if gaps:
            incomplete.append(requirement)
            blocking = True
            placeholders = [
                field
                for field in gaps
                if entry.get(field) and is_placeholder(entry[field])
            ]
            findings.append(
                {
                    "code": "entry-incomplete",
                    "requirement": requirement,
                    "fields": gaps,
                    "detail": "the entry for %s leaves %s unfilled, so it cannot be "
                    "executed" % (requirement, ", ".join(gaps)),
                }
            )
            for field in placeholders:
                findings.append(
                    {
                        "code": "entry-field-carries-placeholder",
                        "requirement": requirement,
                        "field": field,
                        "value": entry[field],
                        "detail": "the %s on %s reads %r, which fills the field and "
                        "nothing else" % (field, requirement, entry[field]),
                    }
                )
        if entry["facility"] and not is_placeholder(entry["facility"]):
            if facilities and entry["facility"] not in facilities:
                findings.append(
                    {
                        "code": "entry-names-unknown-facility",
                        "requirement": requirement,
                        "facility": entry["facility"],
                        "detail": "the entry for %s books %s, which is not a declared "
                        "facility" % (requirement, entry["facility"]),
                    }
                )
                blocking = True
            else:
                available = facilities.get(entry["facility"])
                if available is not None and available > phase_start:
                    findings.append(
                        {
                            "code": "facility-not-available-at-phase-start",
                            "requirement": requirement,
                            "facility": entry["facility"],
                            "available_from": available.isoformat(),
                            "detail": "the entry for %s books %s, which is not available "
                            "until %s" % (requirement, entry["facility"], available.isoformat()),
                        }
                    )

    for requirement in sorted(entries):
        if requirement not in requirements:
            findings.append(
                {
                    "code": "entry-for-unknown-requirement",
                    "requirement": requirement,
                    "detail": "the plan carries an entry for %s, which is not in the "
                    "requirement set it covers" % requirement,
                }
            )

    achieved = completeness(requirements, entries)
    threshold = plan.get("completeness_threshold")
    if threshold is not None:
        threshold_value = _fraction("completeness_threshold", threshold)
        if not meets_completeness_threshold(achieved, threshold_value):
            findings.append(
                {
                    "code": "completeness-threshold-missed",
                    "achieved": achieved,
                    "threshold": threshold_value,
                    "detail": "the plan is %.1f %% complete against a %.1f %% threshold"
                    % (100.0 * achieved, 100.0 * threshold_value),
                }
            )
            blocking = True

    if blocking:
        verdict = "not-ready"
    elif findings:
        verdict = "ready-with-actions"
    else:
        verdict = "ready"

    return {
        "requirement_count": len(requirements),
        "entry_count": len(entries),
        "completeness": achieved,
        "incomplete_requirements": incomplete,
        "approval_state": approval,
        "findings": findings,
        "verdict": verdict,
        "design_phase_may_open": verdict != "not-ready",
    }

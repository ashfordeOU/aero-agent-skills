#!/usr/bin/env python3
"""What marks a coverglass failed during a subgroup test and its inspection.

Anchor: ECSS-E-ST-20-08C clause 8.8.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A subgroup of coverglasses is measured, put through an environmental test,
measured again and then looked at. The clause fixes what turns that pair of
readings plus the inspection into the word "failed", and it does so on two
independent arms:

    measured   an optical or coating property that moved further between the
               before and the after reading than the specification allows it
               to move
    observed   a condition the inspection can see -- a crack, a coating that
               has lifted, blistered or discoloured, a chip past its limit --
               which fails the piece on its own, whatever the numbers said

The arms do not offset each other. A piece whose readings are comfortably
inside every allowance is still failed if the inspection finds a listed
condition, and a piece that looks perfect is still failed if a property
moved too far. A piece missing an after reading is not a pass: it has not
been evaluated, and saying so is the only honest verdict available.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MEASURED_PROPERTIES = (
    "solar-transmittance",
    "surface-conductivity",
    "solar-absorptance",
)

# Which way a property has to move before the movement counts as degradation.
DEGRADATION_SENSE = {
    "solar-transmittance": "decrease",
    "surface-conductivity": "decrease",
    "solar-absorptance": "increase",
}

OBSERVABLE_CONDITIONS = (
    "coverglass-crack",
    "coating-delamination",
    "coating-blistering",
    "visible-discolouration",
    "chip-beyond-limit",
    "adhering-contamination",
)

COATING_CONDUCTION_LOST = "coating-conduction-lost"

SPECIMEN_FAILED = "specimen-failed"
SPECIMEN_PASSED = "specimen-passed"
SPECIMEN_NOT_EVALUATED = "specimen-not-evaluated"

SUBGROUP_MEETS_CRITERIA = "subgroup-meets-criteria"
SUBGROUP_FAILED = "subgroup-failed"
SUBGROUP_NOT_EVALUABLE = "subgroup-not-evaluable"

DEFAULT_FAILURE_CRITERIA = {
    "specification_reference": "coverglass-specification-issue-c",
    "property_allowances": {
        "solar-transmittance": 0.02,
        "surface-conductivity": 0.20,
        "solar-absorptance": 0.05,
    },
    "disqualifying_conditions": (
        "coverglass-crack",
        "coating-delamination",
        "coating-blistering",
        "visible-discolouration",
        "chip-beyond-limit",
    ),
    "max_failed_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _within(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
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


def _require_reading(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be a finite non-negative reading, got %r" % (name, value))
    return value


def measured_properties():
    """The coverglass properties a subgroup test is graded on."""
    return tuple(MEASURED_PROPERTIES)


def observable_conditions():
    """The conditions the post-test inspection can raise against a piece."""
    return tuple(OBSERVABLE_CONDITIONS)


def validate_failure_criteria(criteria):
    """Check a declared criteria set can decide anything at all."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_text("specification_reference", criteria.get("specification_reference"))

    allowances = criteria.get("property_allowances")
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError("property_allowances must be a non-empty mapping")
    for name, allowance in allowances.items():
        name = _require_text("property_allowances key", name)
        if name not in MEASURED_PROPERTIES:
            raise ValueError("property_allowances names an unknown property %s" % name)
        _require_fraction("allowance for %s" % name, allowance)

    conditions = criteria.get("disqualifying_conditions")
    if not isinstance(conditions, (list, tuple, set, frozenset)) or not conditions:
        raise ValueError("disqualifying_conditions must be a non-empty sequence")
    for condition in conditions:
        condition = _require_text("disqualifying condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("unknown disqualifying condition %s" % condition)

    _require_fraction("max_failed_fraction", criteria.get("max_failed_fraction"))
    return criteria


def property_change(prop, before, after):
    """How far one property moved, and how much of that movement is decay."""
    prop = _require_text("property", prop)
    if prop not in MEASURED_PROPERTIES:
        raise ValueError("unknown measured property %s" % prop)
    before = _require_reading("before reading for %s" % prop, before)
    after = _require_reading("after reading for %s" % prop, after)
    if before == 0.0:
        raise ValueError("before reading for %s must be positive" % prop)
    sense = DEGRADATION_SENSE[prop]
    signed = after - before
    decay = -signed if sense == "decrease" else signed
    return {
        "property": prop,
        "sense": sense,
        "before": before,
        "after": after,
        "signed_change": signed,
        "degradation": decay,
        "relative_degradation": decay / before,
    }


def property_within_allowance(prop, before, after, allowance):
    """Did this property stay inside its allowance, a tie being admissible."""
    allowance = _require_fraction("allowance for %s" % prop, allowance)
    change = property_change(prop, before, after)
    relative = change["relative_degradation"]
    inside = relative <= 0.0 or _within(relative, allowance)
    change["allowance"] = allowance
    change["margin"] = allowance - relative
    change["within_allowance"] = inside
    return change


def assess_coverglass_specimen(specimen, criteria=DEFAULT_FAILURE_CRITERIA):
    """Failure call for one coverglass, naming every mode it shows."""
    validate_failure_criteria(criteria)
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    specimen_id = _require_text("specimen_id", specimen.get("specimen_id"))

    before = specimen.get("before_readings")
    after = specimen.get("after_readings")
    if not isinstance(before, dict) or not before:
        raise ValueError("before_readings must be a non-empty mapping")
    if not isinstance(after, dict):
        raise ValueError("after_readings must be a mapping, got %r" % (after,))

    allowances = criteria["property_allowances"]
    modes = []
    findings = []
    changes = {}
    unread = []

    for prop in sorted(allowances):
        if prop not in before:
            unread.append(prop)
            findings.append(
                "%s has no before reading for %s, so nothing can be taken against "
                "its allowance" % (specimen_id, prop)
            )
            continue
        if prop not in after or after.get(prop) is None:
            unread.append(prop)
            findings.append(
                "%s has no after reading for %s, so the piece has not been "
                "evaluated on it" % (specimen_id, prop)
            )
            continue
        change = property_within_allowance(
            prop, before[prop], after[prop], allowances[prop]
        )
        changes[prop] = change
        if not change["within_allowance"]:
            mode = "%s-degradation-exceeded" % prop
            modes.append(mode)
            findings.append(
                "%s lost %.4f of its %s against an allowance of %.4f"
                % (specimen_id, change["relative_degradation"], prop, change["allowance"])
            )

    conduction = changes.get("surface-conductivity")
    if conduction is not None and conduction["after"] == 0.0:
        modes.append(COATING_CONDUCTION_LOST)
        findings.append(
            "%s reads no surface conductivity after the test, so the coating no "
            "longer bleeds charge at all" % specimen_id
        )

    observed = specimen.get("observed_conditions", ())
    if not isinstance(observed, (list, tuple, set, frozenset)):
        raise ValueError("observed_conditions must be a sequence, got %r" % (observed,))
    declared = set(criteria["disqualifying_conditions"])
    seen_conditions = []
    for condition in observed:
        condition = _require_text("observed condition", condition)
        if condition not in OBSERVABLE_CONDITIONS:
            raise ValueError("inspection reports an unknown condition %s" % condition)
        seen_conditions.append(condition)
        if condition in declared and condition not in modes:
            modes.append(condition)
            findings.append(
                "%s shows %s, which the specification lists as disqualifying on "
                "its own" % (specimen_id, condition)
            )

    modes = sorted(set(modes))
    if modes:
        verdict = SPECIMEN_FAILED
    elif unread:
        verdict = SPECIMEN_NOT_EVALUATED
    else:
        verdict = SPECIMEN_PASSED

    margins = {
        prop: change["margin"] for prop, change in changes.items()
    }
    limiting = min(margins.values()) if margins else None
    return {
        "specimen_id": specimen_id,
        "verdict": verdict,
        "failed": verdict == SPECIMEN_FAILED,
        "evaluated": not unread,
        "failure_modes": modes,
        "property_changes": changes,
        "margins": margins,
        "limiting_margin": limiting,
        "unread_properties": sorted(set(unread)),
        "observed_conditions": sorted(set(seen_conditions)),
        "findings": findings,
    }


def assess_subgroup(subgroup, criteria=DEFAULT_FAILURE_CRITERIA):
    """Full clause 8.8.1 sweep over one tested coverglass subgroup."""
    validate_failure_criteria(criteria)
    if not isinstance(subgroup, dict):
        raise ValueError("subgroup must be a mapping, got %r" % (subgroup,))
    subgroup_id = _require_text("subgroup_id", subgroup.get("subgroup_id"))
    _require_text("test_reference", subgroup.get("test_reference"))

    specimens = subgroup.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("subgroup specimens must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for specimen in specimens:
        assessed = assess_coverglass_specimen(specimen, criteria)
        if assessed["specimen_id"] in seen:
            raise ValueError("subgroup declares specimen %s twice" % assessed["specimen_id"])
        seen.add(assessed["specimen_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["specimen_id"])

    failed = [e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_FAILED]
    passed = [e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_PASSED]
    unevaluated = [
        e["specimen_id"] for e in assessments if e["verdict"] == SPECIMEN_NOT_EVALUATED
    ]

    total = len(assessments)
    failed_fraction = len(failed) / float(total)
    allowance = float(criteria["max_failed_fraction"])
    share_ok = _within(failed_fraction, allowance)

    mode_tally = {}
    for entry in assessments:
        for mode in entry["failure_modes"]:
            mode_tally.setdefault(mode, []).append(entry["specimen_id"])

    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])
    if unevaluated:
        findings.append(
            "subgroup %s cannot be closed while %s carry no complete reading pair"
            % (subgroup_id, ", ".join(sorted(unevaluated)))
        )
    if not share_ok:
        findings.append(
            "subgroup %s failed %d of %d pieces, a share of %.4f against an "
            "allowance of %.4f" % (subgroup_id, len(failed), total, failed_fraction, allowance)
        )

    if unevaluated:
        verdict = SUBGROUP_NOT_EVALUABLE
    elif not share_ok:
        verdict = SUBGROUP_FAILED
    else:
        verdict = SUBGROUP_MEETS_CRITERIA

    return {
        "verdict": verdict,
        "subgroup_id": subgroup_id,
        "specimen_assessments": assessments,
        "failed_specimen_ids": sorted(failed),
        "passed_specimen_ids": sorted(passed),
        "unevaluated_specimen_ids": sorted(unevaluated),
        "failed_fraction": failed_fraction,
        "allowed_failed_fraction": allowance,
        "failed_share_within_allowance": share_ok,
        "modes_by_specimen": {k: sorted(v) for k, v in mode_tally.items()},
        "findings": findings,
    }

#!/usr/bin/env python3
"""Packing, dispatch, handling and storage rules for coverglasses.

Anchor: ECSS-E-ST-20-08C clause 8.11. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Clause 8.11 is a pointer clause. It does not set out how coverglasses are
packed, dispatched, handled or stored; it hands all four activities to the
referenced product assurance standard and expects the project to be able
to say, per activity, which rule set governs and at which issue. The work
a pointer clause creates is therefore resolution work:

    resolve    each activity declares a reference, and the KIND of that
               reference decides whether the activity is governed,
               governed only while a tailoring record is approved, or not
               governed at all
    stand      a product assurance reference is also read for its ISSUE.
               A rule set cited at an issue the governing one has replaced
               is a rule set nobody is working to, and an activity resting
               on it is governed in name only
    protect    a coverglass is a coated optical part, so packing and
               handling are the two activities that must also name the
               measure keeping one coated face off the next
    bound      storage is the activity that carries numbers: the
               environment the glass is held in, and how much of its
               permitted storage life is still unspent

An activity resting on a supplier's own instruction, or on nothing, is
reported as open rather than assumed acceptable: the point of the pointer
is that the referenced product assurance standard, not local custom, is
the governing text.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ACTIVITY_GOVERNED",
    "ACTIVITY_GOVERNED_ON_TAILORING",
    "ACTIVITY_NOT_GOVERNED",
    "ACTIVITY_SUPERSEDED_ISSUE",
    "CONDITIONS_IN_ENVELOPE",
    "CONDITIONS_OUT_OF_ENVELOPE",
    "DEFAULT_COVERGLASS_STORAGE_POLICY",
    "GOVERNED_ACTIVITIES",
    "PROTECTED_ACTIVITIES",
    "REFERENCE_KINDS",
    "RULES_OPEN",
    "RULES_RESOLVED",
    "STORAGE_LIFE_EXPIRED",
    "STORAGE_LIFE_MARGIN_THIN",
    "STORAGE_LIFE_OK",
    "evaluate_packing_and_storage",
    "normalize_activity",
    "normalize_reference_kind",
    "resolve_activity",
    "storage_conditions_state",
    "storage_life_state",
    "validate_policy",
]

GOVERNED_ACTIVITIES = ("packing", "dispatch", "handling", "storage")

# Packing and handling are the two activities where a coated face can meet
# another surface, so both have to name the measure that stops it.
PROTECTED_ACTIVITIES = ("packing", "handling")

REFERENCE_KINDS = (
    "product-assurance-standard",
    "project-tailoring",
    "supplier-instruction",
    "undeclared",
)

ACTIVITY_GOVERNED = "activity-governed"
ACTIVITY_GOVERNED_ON_TAILORING = "activity-governed-on-tailoring"
ACTIVITY_SUPERSEDED_ISSUE = "activity-governed-at-superseded-issue"
ACTIVITY_NOT_GOVERNED = "activity-not-governed"

CONDITIONS_IN_ENVELOPE = "storage-conditions-in-envelope"
CONDITIONS_OUT_OF_ENVELOPE = "storage-conditions-out-of-envelope"

STORAGE_LIFE_OK = "storage-life-margin-adequate"
STORAGE_LIFE_MARGIN_THIN = "storage-life-margin-thin"
STORAGE_LIFE_EXPIRED = "storage-life-overrun"

RULES_RESOLVED = "coverglass-packing-rules-resolved"
RULES_OPEN = "coverglass-packing-rules-open"

DEFAULT_COVERGLASS_STORAGE_POLICY = {
    "require_approved_tailoring": True,
    "require_coated_surface_protection": True,
    "min_storage_life_margin_fraction": 0.20,
    "storage_envelope": {
        "min_temperature_celsius": 15.0,
        "max_temperature_celsius": 25.0,
        "max_relative_humidity_percent": 55.0,
    },
}

# An envelope bound is a declared round number; a reading comes back from
# an instrument log, and a margin is arrived at by arithmetic. A value
# meant to sit exactly on its bound can land a unit in the last place
# either side of it, so the comparisons absorb that while the declared
# bound stays exactly as declared.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _number(label, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _non_negative(label, value):
    number = _number(label, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _positive(label, value):
    number = _number(label, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _issue(label, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer issue number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=_REL_TOL,
                                          abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=_REL_TOL,
                                          abs_tol=_ABS_TOL)


def normalize_activity(activity, label="activity"):
    """Return one of the four activities the clause hands over."""
    if not isinstance(activity, str):
        raise ValueError("%s must be a string, got %r" % (label, activity))
    cleaned = activity.strip().lower()
    if cleaned not in GOVERNED_ACTIVITIES:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, activity, ", ".join(GOVERNED_ACTIVITIES))
        )
    return cleaned


def normalize_reference_kind(kind, label="reference_kind"):
    """Return one of the recognized reference kinds."""
    if not isinstance(kind, str):
        raise ValueError("%s must be a string, got %r" % (label, kind))
    cleaned = kind.strip().lower()
    if cleaned not in REFERENCE_KINDS:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, kind, ", ".join(REFERENCE_KINDS))
        )
    return cleaned


def validate_policy(policy=None):
    """Return the declared policy merged onto the default, fully checked."""
    merged = {
        "require_approved_tailoring":
            DEFAULT_COVERGLASS_STORAGE_POLICY["require_approved_tailoring"],
        "require_coated_surface_protection":
            DEFAULT_COVERGLASS_STORAGE_POLICY["require_coated_surface_protection"],
        "min_storage_life_margin_fraction":
            DEFAULT_COVERGLASS_STORAGE_POLICY["min_storage_life_margin_fraction"],
        "storage_envelope":
            dict(DEFAULT_COVERGLASS_STORAGE_POLICY["storage_envelope"]),
    }
    if policy is None:
        return merged
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping or None")
    unknown = set(policy) - set(merged)
    if unknown:
        raise ValueError("policy carries unknown key(s): %s"
                         % ", ".join(sorted(unknown)))
    if "require_approved_tailoring" in policy:
        merged["require_approved_tailoring"] = _flag(
            "require_approved_tailoring", policy["require_approved_tailoring"]
        )
    if "require_coated_surface_protection" in policy:
        merged["require_coated_surface_protection"] = _flag(
            "require_coated_surface_protection",
            policy["require_coated_surface_protection"],
        )
    if "min_storage_life_margin_fraction" in policy:
        fraction = _number(
            "min_storage_life_margin_fraction",
            policy["min_storage_life_margin_fraction"],
        )
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(
                "min_storage_life_margin_fraction must lie between 0 and 1, got %r"
                % (policy["min_storage_life_margin_fraction"],)
            )
        merged["min_storage_life_margin_fraction"] = fraction
    if "storage_envelope" in policy:
        envelope = policy["storage_envelope"]
        if not isinstance(envelope, dict):
            raise ValueError("storage_envelope must be a mapping")
        unknown_env = set(envelope) - set(merged["storage_envelope"])
        if unknown_env:
            raise ValueError("storage_envelope carries unknown key(s): %s"
                             % ", ".join(sorted(unknown_env)))
        for key, value in envelope.items():
            merged["storage_envelope"][key] = _number("storage_envelope.%s" % key,
                                                      value)
        env = merged["storage_envelope"]
        if env["min_temperature_celsius"] > env["max_temperature_celsius"]:
            raise ValueError(
                "storage_envelope minimum temperature exceeds its maximum"
            )
        if env["max_relative_humidity_percent"] < 0.0:
            raise ValueError("storage_envelope humidity ceiling must not be negative")
    return merged


def resolve_activity(declaration, policy=None):
    """Say which rule set governs one activity, and whether it stands.

    The kind of reference decides the disposition, not the fact that some
    reference exists; a product assurance reference is then read for its
    issue, because a rule set cited at a superseded issue governs in name
    only.
    """
    settings = validate_policy(policy)
    if not isinstance(declaration, dict):
        raise ValueError("activity declaration must be a mapping")
    for key in ("activity", "reference_kind"):
        if key not in declaration:
            raise ValueError("activity declaration missing required key '%s'" % key)
    activity = normalize_activity(declaration["activity"])
    kind = normalize_reference_kind(declaration["reference_kind"])

    reasons = []
    reference_id = declaration.get("reference_id")
    if kind in ("product-assurance-standard", "project-tailoring"):
        reference_id = _text("reference_id", reference_id)
    elif reference_id is not None:
        reference_id = _text("reference_id", reference_id)

    if kind == "undeclared":
        state = ACTIVITY_NOT_GOVERNED
        reasons.append("%s declares no reference at all" % activity)
    elif kind == "supplier-instruction":
        state = ACTIVITY_NOT_GOVERNED
        reasons.append(
            "%s rests on a supplier instruction rather than the referenced "
            "product assurance standard" % activity
        )
    elif kind == "project-tailoring":
        approved = _flag("tailoring_approved",
                         declaration.get("tailoring_approved", False))
        if approved or not settings["require_approved_tailoring"]:
            state = ACTIVITY_GOVERNED_ON_TAILORING
        else:
            state = ACTIVITY_NOT_GOVERNED
            reasons.append(
                "%s rests on tailoring %s whose record is not approved"
                % (activity, reference_id)
            )
    else:
        cited = _issue("reference_issue",
                       declaration.get("reference_issue", 1))
        governing = _issue("governing_issue",
                           declaration.get("governing_issue", cited))
        if cited < governing:
            state = ACTIVITY_SUPERSEDED_ISSUE
            reasons.append(
                "%s cites %s at issue %d, superseded by issue %d"
                % (activity, reference_id, cited, governing)
            )
        else:
            state = ACTIVITY_GOVERNED

    protection = declaration.get("coated_surface_protection")
    protection_required = (
        settings["require_coated_surface_protection"]
        and activity in PROTECTED_ACTIVITIES
    )
    if protection is not None:
        protection = _text("coated_surface_protection", protection)
    if protection_required and protection is None:
        reasons.append(
            "%s names no measure keeping one coated coverglass face off the next"
            % activity
        )

    return {
        "activity": activity,
        "reference_kind": kind,
        "reference_id": reference_id,
        "state": state,
        "governed": state in (ACTIVITY_GOVERNED, ACTIVITY_GOVERNED_ON_TAILORING),
        "coated_surface_protection": protection,
        "protection_required": protection_required,
        "reasons": tuple(reasons),
    }


def storage_conditions_state(conditions, policy=None):
    """Hold declared storage temperature and humidity to the envelope."""
    settings = validate_policy(policy)
    envelope = settings["storage_envelope"]
    if not isinstance(conditions, dict):
        raise ValueError("storage conditions must be a mapping")
    for key in ("temperature_celsius", "relative_humidity_percent"):
        if key not in conditions:
            raise ValueError("storage conditions missing required key '%s'" % key)
    temperature = _number("temperature_celsius", conditions["temperature_celsius"])
    humidity = _non_negative(
        "relative_humidity_percent", conditions["relative_humidity_percent"]
    )
    reasons = []
    if not _at_least(temperature, envelope["min_temperature_celsius"]):
        reasons.append(
            "storage temperature %.3f C is below the %.3f C envelope floor"
            % (temperature, envelope["min_temperature_celsius"])
        )
    if not _at_most(temperature, envelope["max_temperature_celsius"]):
        reasons.append(
            "storage temperature %.3f C is above the %.3f C envelope ceiling"
            % (temperature, envelope["max_temperature_celsius"])
        )
    if not _at_most(humidity, envelope["max_relative_humidity_percent"]):
        reasons.append(
            "storage relative humidity %.3f %% is above the %.3f %% ceiling"
            % (humidity, envelope["max_relative_humidity_percent"])
        )
    return {
        "temperature_celsius": temperature,
        "relative_humidity_percent": humidity,
        "envelope": dict(envelope),
        "state": CONDITIONS_IN_ENVELOPE if not reasons else CONDITIONS_OUT_OF_ENVELOPE,
        "in_envelope": not reasons,
        "reasons": tuple(reasons),
    }


def storage_life_state(elapsed_days, permitted_days, policy=None):
    """Work out how much of the permitted storage life is still unspent."""
    settings = validate_policy(policy)
    elapsed = _non_negative("elapsed_storage_days", elapsed_days)
    permitted = _positive("permitted_storage_days", permitted_days)
    unspent = (permitted - elapsed) / permitted
    floor = settings["min_storage_life_margin_fraction"]
    if unspent < 0.0 and not math.isclose(unspent, 0.0, abs_tol=_ABS_TOL):
        state = STORAGE_LIFE_EXPIRED
        reason = (
            "storage life is overrun: %.1f of %.1f permitted days are spent"
            % (elapsed, permitted)
        )
    elif _at_least(unspent, floor):
        state = STORAGE_LIFE_OK
        reason = None
    else:
        state = STORAGE_LIFE_MARGIN_THIN
        reason = (
            "storage life margin %.4f is under the declared %.4f floor"
            % (unspent, floor)
        )
    return {
        "elapsed_storage_days": elapsed,
        "permitted_storage_days": permitted,
        "unspent_fraction": unspent,
        "min_margin_fraction": floor,
        "state": state,
        "acceptable": state == STORAGE_LIFE_OK,
        "reason": reason,
    }


def evaluate_packing_and_storage(case):
    """Run the clause 8.11 rule-resolution check over one declaration.

    case keys: case_id, activities; optional storage_conditions,
    elapsed_storage_days, permitted_storage_days and policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("case_id", "activities"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    case_id = _text("case_id", case["case_id"])
    settings = validate_policy(case.get("policy"))
    declarations = case["activities"]
    if not isinstance(declarations, (list, tuple)) or not declarations:
        raise ValueError("case must declare at least one activity")

    resolved = []
    seen = set()
    for declaration in declarations:
        entry = resolve_activity(declaration, settings)
        if entry["activity"] in seen:
            raise ValueError("activity %s is declared twice" % entry["activity"])
        seen.add(entry["activity"])
        resolved.append(entry)
    resolved.sort(key=lambda e: GOVERNED_ACTIVITIES.index(e["activity"]))

    findings = []
    for entry in resolved:
        findings.extend(entry["reasons"])
    undeclared = tuple(a for a in GOVERNED_ACTIVITIES if a not in seen)
    for activity in undeclared:
        findings.append(
            "case %s says nothing about %s, so nobody can name the rules that "
            "govern it" % (case_id, activity)
        )

    storage = next((e for e in resolved if e["activity"] == "storage"), None)
    storage_governed = storage is not None and storage["governed"]

    conditions = None
    if "storage_conditions" in case and case["storage_conditions"] is not None:
        if storage_governed:
            conditions = storage_conditions_state(case["storage_conditions"], settings)
            findings.extend(conditions["reasons"])
        else:
            conditions = None

    life = None
    if case.get("permitted_storage_days") is not None:
        if storage_governed:
            life = storage_life_state(
                case.get("elapsed_storage_days", 0.0),
                case["permitted_storage_days"],
                settings,
            )
            if life["reason"]:
                findings.append(life["reason"])
        else:
            life = None

    governed_count = sum(1 for e in resolved if e["governed"])
    return {
        "case_id": case_id,
        "activities": tuple(resolved),
        "undeclared_activities": undeclared,
        "governed_count": governed_count,
        "resolved_fraction": governed_count / float(len(GOVERNED_ACTIVITIES)),
        "storage_conditions": conditions,
        "storage_life": life,
        "storage_numbers_measured": bool(storage_governed
                                         and (conditions is not None
                                              or life is not None)),
        "findings": tuple(findings),
        "verdict": RULES_RESOLVED if not findings else RULES_OPEN,
        "accepted": not findings,
    }

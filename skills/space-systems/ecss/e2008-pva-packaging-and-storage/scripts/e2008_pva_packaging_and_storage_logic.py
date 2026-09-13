#!/usr/bin/env python3
"""Packing, dispatch, handling and storage rules for a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Clause 5.9 is a pointer clause. It does not itself set out how a
photovoltaic assembly (PVA) is packed, dispatched, handled or stored; it
hands those four activities to the product assurance rule set and expects
the project to be able to say, for each one, which rule set applies and at
which issue. The work a pointer clause actually creates is therefore
resolution work:

    resolve    each of the four activities carries a declared reference,
               and the kind of reference decides whether the activity is
               governed, governed only on an approved tailoring record,
               or not governed at all
    cover      all four activities must be resolved; an activity nobody
               declared is an open activity, not a governed one
    bound      storage is the one activity that also carries numbers --
               the environment it is held in and how much of its
               permitted storage life is still unspent

An activity governed by a supplier instruction or by nothing at all is
reported as open rather than assumed acceptable, because the whole point
of the pointer is that the product assurance rules, not local custom, are
the governing text.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GOVERNED_ACTIVITIES = ("packing", "dispatch", "handling", "storage")

REFERENCE_KINDS = (
    "product-assurance-standard",
    "project-tailoring",
    "supplier-instruction",
    "undeclared",
)

ACTIVITY_GOVERNED = "activity-governed"
ACTIVITY_GOVERNED_ON_TAILORING = "activity-governed-on-tailoring"
ACTIVITY_NOT_GOVERNED = "activity-not-governed"
ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE = "activity-conditions-out-of-envelope"

RULES_RESOLVED = "packaging-rules-resolved"
RULES_OPEN = "packaging-rules-open"

DEFAULT_PACKAGING_POLICY = {
    "require_approved_tailoring": True,
    "min_storage_life_margin_fraction": 0.20,
    "storage_envelope": {
        "min_temperature_celsius": 15.0,
        "max_temperature_celsius": 25.0,
        "max_relative_humidity_percent": 55.0,
    },
    "reference_disposition": {
        "product-assurance-standard": ACTIVITY_GOVERNED,
        "project-tailoring": ACTIVITY_GOVERNED_ON_TAILORING,
        "supplier-instruction": ACTIVITY_NOT_GOVERNED,
        "undeclared": ACTIVITY_NOT_GOVERNED,
    },
}

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


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An envelope bound is a declared round number and the reading comes back
    from an instrument log, so a condition meant to sit exactly on the bound
    can land a few units in the last place outside it. The bound is never
    widened; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _is_declared(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def validate_packaging_policy(policy):
    """Check a packing, dispatch, handling and storage policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_approved_tailoring", policy.get("require_approved_tailoring"))
    margin = _require_non_negative(
        "min_storage_life_margin_fraction",
        policy.get("min_storage_life_margin_fraction"),
    )
    if margin >= 1.0:
        raise ValueError(
            "min_storage_life_margin_fraction must be below one, got %r" % (margin,)
        )
    envelope = policy.get("storage_envelope")
    if not isinstance(envelope, dict):
        raise ValueError("policy storage_envelope must be a mapping")
    low = _require_number(
        "storage_envelope min_temperature_celsius",
        envelope.get("min_temperature_celsius"),
    )
    high = _require_number(
        "storage_envelope max_temperature_celsius",
        envelope.get("max_temperature_celsius"),
    )
    if high <= low:
        raise ValueError(
            "storage_envelope max_temperature_celsius must exceed the minimum"
        )
    humidity = _require_positive(
        "storage_envelope max_relative_humidity_percent",
        envelope.get("max_relative_humidity_percent"),
    )
    if humidity > 100.0:
        raise ValueError(
            "storage_envelope max_relative_humidity_percent must not exceed 100"
        )
    table = policy.get("reference_disposition")
    if not isinstance(table, dict):
        raise ValueError("policy reference_disposition must be a mapping")
    missing = set(REFERENCE_KINDS) - set(table)
    if missing:
        raise ValueError(
            "policy reference_disposition is missing kinds: %s"
            % ", ".join(sorted(missing))
        )
    for kind in REFERENCE_KINDS:
        _require_choice(
            "policy reference_disposition[%s]" % kind,
            table[kind],
            (
                ACTIVITY_GOVERNED,
                ACTIVITY_GOVERNED_ON_TAILORING,
                ACTIVITY_NOT_GOVERNED,
            ),
        )
    return policy


def governed_activities():
    """The four activities clause 5.9 hands to the product assurance rules."""
    return GOVERNED_ACTIVITIES


def resolve_reference_disposition(
    kind, tailoring_approved=False, policy=DEFAULT_PACKAGING_POLICY
):
    """Disposition an activity from the kind of reference it declares."""
    validate_packaging_policy(policy)
    _require_choice("reference kind", kind, REFERENCE_KINDS)
    _require_flag("tailoring_approved", tailoring_approved)
    disposition = policy["reference_disposition"][kind]
    if (
        disposition == ACTIVITY_GOVERNED_ON_TAILORING
        and policy["require_approved_tailoring"]
        and not tailoring_approved
    ):
        return ACTIVITY_NOT_GOVERNED
    return disposition


def storage_envelope_status(conditions, policy=DEFAULT_PACKAGING_POLICY):
    """Hold declared storage conditions against the governing envelope."""
    validate_packaging_policy(policy)
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping, got %r" % (conditions,))
    envelope = policy["storage_envelope"]
    temperature = _require_number(
        "temperature_celsius", conditions.get("temperature_celsius")
    )
    humidity = _require_non_negative(
        "relative_humidity_percent", conditions.get("relative_humidity_percent")
    )
    if humidity > 100.0:
        raise ValueError(
            "relative_humidity_percent must not exceed 100, got %r" % (humidity,)
        )
    low = float(envelope["min_temperature_celsius"])
    high = float(envelope["max_temperature_celsius"])
    limit = float(envelope["max_relative_humidity_percent"])
    temperature_ok = _at_least(temperature, low) and _at_most(temperature, high)
    humidity_ok = _at_most(humidity, limit)
    findings = []
    if not temperature_ok:
        findings.append(
            "storage temperature %.4f C sits outside the %.4f to %.4f C envelope"
            % (temperature, low, high)
        )
    if not humidity_ok:
        findings.append(
            "storage relative humidity %.4f%% exceeds the %.4f%% envelope limit"
            % (humidity, limit)
        )
    return {
        "temperature_celsius": temperature,
        "relative_humidity_percent": humidity,
        "temperature_ok": temperature_ok,
        "humidity_ok": humidity_ok,
        "within_envelope": temperature_ok and humidity_ok,
        "findings": findings,
    }


def storage_life_margin(
    permitted_storage_days, elapsed_storage_days, policy=DEFAULT_PACKAGING_POLICY
):
    """How much of the permitted storage life is still unspent."""
    validate_packaging_policy(policy)
    permitted = _require_positive("permitted_storage_days", permitted_storage_days)
    elapsed = _require_non_negative("elapsed_storage_days", elapsed_storage_days)
    remaining = permitted - elapsed
    fraction = remaining / permitted
    required = float(policy["min_storage_life_margin_fraction"])
    sufficient = _at_least(fraction, required)
    exceeded = remaining < 0.0 and not math.isclose(remaining, 0.0, abs_tol=_ABS_TOL)
    findings = []
    if exceeded:
        findings.append(
            "storage has run %.4f days past the permitted %.4f days"
            % (-remaining, permitted)
        )
    elif not sufficient:
        findings.append(
            "storage life leaves %.4f of its span against a required %.4f"
            % (fraction, required)
        )
    return {
        "remaining_days": remaining,
        "remaining_fraction": fraction,
        "required_fraction": required,
        "sufficient": sufficient,
        "exceeded": exceeded,
        "findings": findings,
    }


def assess_activity(declaration, policy=DEFAULT_PACKAGING_POLICY):
    """Resolve the governing rules for one of the four activities."""
    validate_packaging_policy(policy)
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping, got %r" % (declaration,))
    activity = _require_choice(
        "activity", declaration.get("activity"), GOVERNED_ACTIVITIES
    )
    kind = _require_choice(
        "reference kind", declaration.get("reference_kind"), REFERENCE_KINDS
    )
    reference = declaration.get("reference")
    if kind != "undeclared" and not _is_declared(reference):
        raise ValueError(
            "activity %s declares kind %s but names no reference" % (activity, kind)
        )
    approved = declaration.get("tailoring_approved", False)
    _require_flag("tailoring_approved", approved)
    verdict = resolve_reference_disposition(kind, approved, policy)
    record = {
        "activity": activity,
        "reference_kind": kind,
        "reference": reference.strip() if isinstance(reference, str) else None,
        "tailoring_approved": approved,
        "envelope": None,
        "storage_life": None,
        "findings": [],
    }
    if verdict == ACTIVITY_NOT_GOVERNED:
        record["verdict"] = ACTIVITY_NOT_GOVERNED
        if kind == "undeclared":
            record["findings"].append(
                "%s names no governing product assurance reference" % activity
            )
        elif kind == "project-tailoring":
            record["findings"].append(
                "%s rests on a tailoring record that is not approved" % activity
            )
        else:
            record["findings"].append(
                "%s is governed by a %s rather than the product assurance rules"
                % (activity, kind.replace("-", " "))
            )
        return record
    if activity == "storage":
        conditions = declaration.get("conditions")
        if conditions is not None:
            envelope = storage_envelope_status(conditions, policy)
            record["envelope"] = envelope
            record["findings"].extend(envelope["findings"])
        life_declared = declaration.get("permitted_storage_days") is not None
        if life_declared:
            life = storage_life_margin(
                declaration.get("permitted_storage_days"),
                declaration.get("elapsed_storage_days", 0.0),
                policy,
            )
            record["storage_life"] = life
            record["findings"].extend(life["findings"])
        out_of_envelope = record["envelope"] is not None and not record["envelope"][
            "within_envelope"
        ]
        life_short = record["storage_life"] is not None and not record["storage_life"][
            "sufficient"
        ]
        if out_of_envelope or life_short:
            record["verdict"] = ACTIVITY_CONDITIONS_OUT_OF_ENVELOPE
            return record
    record["verdict"] = verdict
    return record


def assess_packaging_and_storage(case, policy=DEFAULT_PACKAGING_POLICY):
    """Full clause 5.9 sweep over the four governed PVA activities."""
    validate_packaging_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    declarations = case.get("declarations")
    if not isinstance(declarations, (list, tuple)) or not declarations:
        raise ValueError("case declarations must be a non-empty sequence of mappings")
    records = [assess_activity(entry, policy) for entry in declarations]
    named = [record["activity"] for record in records]
    repeated = sorted({a for a in named if named.count(a) > 1})
    if repeated:
        raise ValueError("case declares an activity twice: %s" % ", ".join(repeated))
    uncovered = [a for a in GOVERNED_ACTIVITIES if a not in named]
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["activity"])
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for activity in uncovered:
        findings.append("%s is not declared by the case at all" % activity)
    resolved = [
        record["activity"]
        for record in records
        if record["verdict"]
        in (ACTIVITY_GOVERNED, ACTIVITY_GOVERNED_ON_TAILORING)
    ]
    open_activities = sorted(
        set(uncovered)
        | {
            record["activity"]
            for record in records
            if record["activity"] not in resolved
        }
    )
    return {
        "verdict": RULES_RESOLVED if not open_activities else RULES_OPEN,
        "activity_records": records,
        "grouped_by_verdict": grouped,
        "uncovered_activities": uncovered,
        "resolved_activities": sorted(resolved),
        "resolved_fraction": len(resolved) / float(len(GOVERNED_ACTIVITIES)),
        "open_activities": open_activities,
        "findings": findings,
    }

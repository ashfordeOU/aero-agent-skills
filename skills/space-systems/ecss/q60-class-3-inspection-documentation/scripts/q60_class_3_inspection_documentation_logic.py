#!/usr/bin/env python3
"""Recording inspection and control outcomes across a Class 3 parts programme.

Anchor: ECSS-Q-ST-60C clause 6.7 (recording the outcomes of the inspection and
control activities carried out across the Class 3 parts programme). Paraphrased
into an implementable procedure; no standard text is reproduced.

The question this clause settles is not whether the inspections happened. It is
whether, years later and with nobody from the original team in the room, the
outcome of each one can be reconstructed from what was written down. Class 3
widens who may write the record — a supplier may record its own outcome — but
a self-declaration that nobody countersigned records an opinion rather than an
outcome, and a record nobody kept long enough to reach the anomaly review
records nothing at all.

Procedure implemented here
--------------------------
1. Put the performed activities into audit order and group the submitted
   records under the activity each one covers.
2. Name every performed activity that carries no record at all.
3. Test each record for a traceable lot identity, an accepted recording
   authority with a countersignature where the authority is the supplier
   itself, an evidence reference, four stated quantities that reconcile, a
   nonconformance reference behind every rejected quantity, no deferred
   quantity left open, and a retention period that outlives the mission.
4. Measure outcome coverage as the share of performed activities covered by at
   least one defect-free record and judge it against its floor.
5. Measure the programme acceptance yield and raise an advisory when it sits
   below the advisory floor.
6. Return one disposition: outcomes recorded, outcomes partially recorded, or
   outcomes not reconstructable.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CLASS_3_INSPECTION_ACTIVITIES",
    "RECORDING_AUTHORITIES",
    "SELF_DECLARATION_AUTHORITY",
    "QUANTITY_FIELDS",
    "DEFAULT_CLASS3_DOCUMENTATION_POLICY",
    "OUTCOMES_RECORDED",
    "OUTCOMES_PARTIALLY_RECORDED",
    "OUTCOMES_NOT_RECONSTRUCTABLE",
    "BOUND_TOLERANCE",
    "validate_documentation_policy",
    "ordered_activities",
    "record_activity",
    "stated_quantities",
    "reconciliation_residual",
    "required_retention_years",
    "record_defects",
    "group_records_by_activity",
    "unrecorded_activities",
    "defective_records",
    "reconciled_activities",
    "outcome_coverage",
    "coverage_meets_floor",
    "acceptance_yield",
    "recording_disposition",
    "compile_class3_inspection_outcomes",
]

# Coverage is a quotient of small counts and the residual is a difference of
# stated quantities; a case sitting exactly on a bound can land a few units in
# the last place on the wrong side. Absorb the representation error here, never
# by moving the bound itself.
BOUND_TOLERANCE = 1e-9

# The inspection and control activities whose outcome a Class 3 parts
# programme records, in the order the records are presented for audit.
CLASS_3_INSPECTION_ACTIVITIES = (
    "part-approval-review",
    "incoming-inspection",
    "screening-verification",
    "nonconformance-review",
    "delivery-acceptance-review",
)

_ACTIVITY_ORDER = {
    name: index for index, name in enumerate(CLASS_3_INSPECTION_ACTIVITIES)
}

# Class 3 lets the outcome be written up by the supplier itself as well as by
# the project or a delegate. Anyone outside this list records that somebody was
# present, not that the outcome was taken.
RECORDING_AUTHORITIES = (
    "project-quality-assurance",
    "delegated-inspector",
    "component-manufacturer",
    "procurement-agent",
    "supplier-self-declaration",
)

# The one authority that grades its own work, and so owes a countersignature.
SELF_DECLARATION_AUTHORITY = "supplier-self-declaration"

# The four counts an outcome record owes. inspected is the total presented; the
# other three account for where every presented part went.
QUANTITY_FIELDS = ("inspected", "accepted", "rejected", "deferred")

DEFAULT_CLASS3_DOCUMENTATION_POLICY = {
    # Share of performed activities that must carry a defect-free record.
    "outcome_coverage_floor": 0.8,
    # Acceptance yield below this raises an advisory, never a defect: a low
    # yield is a real outcome, honestly recorded.
    "acceptance_yield_advisory_floor": 0.9,
    # Years a record is kept beyond the end of the mission it covers.
    "retention_margin_years": 2.0,
    # Whether a supplier self-declaration owes a countersignature.
    "require_countersigned_self_declaration": True,
    # Whether a record must state how long it will be kept.
    "require_retention_period": True,
}

OUTCOMES_RECORDED = "q60-c3-outcomes-recorded"
OUTCOMES_PARTIALLY_RECORDED = "q60-c3-outcomes-partially-recorded"
OUTCOMES_NOT_RECONSTRUCTABLE = "q60-c3-outcomes-not-reconstructable"


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value, allow_negative=False):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    number = float(value)
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (name, number))
    return number


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def validate_documentation_policy(policy=None):
    """Return a complete Class 3 documentation policy with defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CLASS3_DOCUMENTATION_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("documentation policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CLASS3_DOCUMENTATION_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS3_DOCUMENTATION_POLICY:
            raise ValueError("unknown documentation policy key %r" % (key,))
        merged[key] = value
    for key in ("outcome_coverage_floor", "acceptance_yield_advisory_floor"):
        number = _require_positive(key, merged[key])
        if number > 1.0:
            raise ValueError("%s must not exceed 1.0, got %r" % (key, merged[key]))
    _require_number("retention_margin_years", merged["retention_margin_years"])
    for flag in (
        "require_countersigned_self_declaration",
        "require_retention_period",
    ):
        if not isinstance(merged[flag], bool):
            raise ValueError("%s must be a boolean" % flag)
    return merged


def ordered_activities(performed_activities):
    """Put the performed activities into audit order, without duplicates."""
    if not isinstance(performed_activities, (list, tuple, set, frozenset)):
        raise ValueError(
            "performed_activities must be a list, tuple or set, got %r"
            % (performed_activities,)
        )
    seen = []
    for activity in performed_activities:
        if not _is_text(activity):
            raise ValueError("every performed activity must be a non-empty string")
        folded = activity.strip().lower()
        if folded not in _ACTIVITY_ORDER:
            raise ValueError(
                "performed activity must be one of %s, got %r"
                % (", ".join(CLASS_3_INSPECTION_ACTIVITIES), activity)
            )
        if folded not in seen:
            seen.append(folded)
    if not seen:
        raise ValueError("performed_activities must name at least one activity")
    return tuple(sorted(seen, key=lambda name: _ACTIVITY_ORDER[name]))


def record_activity(record):
    """The activity a submitted record covers."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    activity = record.get("activity")
    if not _is_text(activity):
        raise ValueError("record must name the activity it covers")
    folded = activity.strip().lower()
    if folded not in _ACTIVITY_ORDER:
        raise ValueError("record names an unknown activity: %r" % (activity,))
    return folded


def stated_quantities(record):
    """The four counts a record states, validated."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    quantities = {}
    for field in QUANTITY_FIELDS:
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer count, got %r" % (field, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %r" % (field, value))
        quantities[field] = value
    return quantities


def reconciliation_residual(record):
    """Presented parts less the parts accounted for. Zero when they reconcile."""
    quantities = stated_quantities(record)
    return quantities["inspected"] - (
        quantities["accepted"] + quantities["rejected"] + quantities["deferred"]
    )


def required_retention_years(mission_duration_years, policy=None):
    """Years a record has to survive to reach the last review that needs it."""
    resolved = validate_documentation_policy(policy)
    duration = _require_positive("mission_duration_years", mission_duration_years)
    return duration + resolved["retention_margin_years"]


def record_defects(record, mission_duration_years, policy=None):
    """Everything that stops one record from reconstructing its outcome."""
    resolved = validate_documentation_policy(policy)
    record_activity(record)
    needed_retention = required_retention_years(mission_duration_years, resolved)
    defects = []

    if not _is_text(record.get("lot_identity")):
        defects.append("no-traceable-lot-identity")

    authority = record.get("recording_authority")
    if not _is_text(authority) or authority.strip().lower() not in RECORDING_AUTHORITIES:
        defects.append("unrecognised-recording-authority")
    elif (
        authority.strip().lower() == SELF_DECLARATION_AUTHORITY
        and resolved["require_countersigned_self_declaration"]
        and not _is_text(record.get("countersigned_by"))
    ):
        defects.append("self-declaration-without-countersignature")

    if not _is_text(record.get("evidence_reference")):
        defects.append("no-evidence-reference")

    if reconciliation_residual(record) != 0:
        defects.append("quantities-do-not-reconcile")

    quantities = stated_quantities(record)
    if quantities["rejected"] > 0 and not _is_text(
        record.get("nonconformance_reference")
    ):
        defects.append("rejected-quantity-without-nonconformance-reference")

    if quantities["deferred"] > 0 and not _is_text(
        record.get("deferral_closure_reference")
    ):
        defects.append("deferred-quantity-left-open")

    if resolved["require_retention_period"]:
        retention = record.get("retention_years")
        if not _is_finite_number(retention) or retention < 0.0:
            defects.append("no-stated-retention-period")
        elif not _at_least(float(retention), needed_retention):
            defects.append("retention-below-required-period")

    return tuple(defects)


def group_records_by_activity(records):
    """Group submitted records under the activity each one covers."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (records,))
    grouped = {}
    for record in records:
        grouped.setdefault(record_activity(record), []).append(record)
    return grouped


def unrecorded_activities(performed_activities, records):
    """Performed activities that carry no record at all."""
    performed = ordered_activities(performed_activities)
    grouped = group_records_by_activity(records)
    return tuple(activity for activity in performed if activity not in grouped)


def defective_records(records, mission_duration_years, policy=None):
    """Every submitted record that carries at least one defect, with its defects."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (records,))
    findings = []
    for index, record in enumerate(records):
        defects = record_defects(record, mission_duration_years, policy)
        if defects:
            findings.append(
                {
                    "index": index,
                    "activity": record_activity(record),
                    "defects": defects,
                }
            )
    return tuple(findings)


def reconciled_activities(
    performed_activities, records, mission_duration_years, policy=None
):
    """Performed activities covered by at least one defect-free record."""
    performed = ordered_activities(performed_activities)
    grouped = group_records_by_activity(records)
    covered = []
    for activity in performed:
        for record in grouped.get(activity, ()):
            if not record_defects(record, mission_duration_years, policy):
                covered.append(activity)
                break
    return tuple(covered)


def outcome_coverage(
    performed_activities, records, mission_duration_years, policy=None
):
    """Share of performed activities covered by at least one defect-free record."""
    performed = ordered_activities(performed_activities)
    covered = reconciled_activities(
        performed, records, mission_duration_years, policy
    )
    return len(covered) / float(len(performed))


def coverage_meets_floor(coverage, policy=None):
    """Whether an outcome coverage figure reaches its floor."""
    resolved = validate_documentation_policy(policy)
    value = _require_number("coverage", coverage)
    return _at_least(value, resolved["outcome_coverage_floor"])


def acceptance_yield(records):
    """Accepted parts as a share of the parts presented across the programme."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (records,))
    inspected = 0
    accepted = 0
    for record in records:
        quantities = stated_quantities(record)
        inspected += quantities["inspected"]
        accepted += quantities["accepted"]
    if inspected == 0:
        raise ValueError("no parts were presented, so no yield can be taken")
    return accepted / float(inspected)


def recording_disposition(coverage, has_unrecorded_activity, policy=None):
    """The three-way recording disposition."""
    resolved = validate_documentation_policy(policy)
    value = _require_number("coverage", coverage)
    if value <= 0.0:
        return OUTCOMES_NOT_RECONSTRUCTABLE
    if coverage_meets_floor(value, resolved) and not has_unrecorded_activity:
        return OUTCOMES_RECORDED
    return OUTCOMES_PARTIALLY_RECORDED


def compile_class3_inspection_outcomes(case, policy=None):
    """Full clause 6.7 Class 3 recording assessment with a disposition."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for field in ("performed_activities", "records", "mission_duration_years"):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    resolved = validate_documentation_policy(policy)
    performed = ordered_activities(case["performed_activities"])
    records = case["records"]
    duration = case["mission_duration_years"]

    missing = unrecorded_activities(performed, records)
    defective = defective_records(records, duration, resolved)
    covered = reconciled_activities(performed, records, duration, resolved)
    coverage = len(covered) / float(len(performed))
    meets_floor = coverage_meets_floor(coverage, resolved)
    disposition = recording_disposition(coverage, bool(missing), resolved)

    findings = []
    if missing:
        findings.append("no record covers %s" % ", ".join(missing))
    for entry in defective:
        findings.append(
            "the %s record carries %s"
            % (entry["activity"], ", ".join(entry["defects"]))
        )
    if not meets_floor:
        findings.append(
            "outcome coverage is %.3f, below its floor" % coverage
        )

    advisories = []
    yield_value = None
    try:
        yield_value = acceptance_yield(records)
    except ValueError:
        advisories.append("no parts were presented, so no acceptance yield was taken")
    if yield_value is not None and not _at_least(
        yield_value, resolved["acceptance_yield_advisory_floor"]
    ):
        advisories.append(
            "the programme accepted %.3f of what it presented" % yield_value
        )

    return {
        "disposition": disposition,
        "recorded": disposition == OUTCOMES_RECORDED,
        "performed_activities": performed,
        "unrecorded_activities": missing,
        "defective_records": defective,
        "reconciled_activities": covered,
        "outcome_coverage": coverage,
        "coverage_meets_floor": meets_floor,
        "required_retention_years": required_retention_years(duration, resolved),
        "acceptance_yield": yield_value,
        "findings": findings,
        "advisories": advisories,
    }

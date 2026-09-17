"""Recording of inspection and control outcomes across a class 2 parts programme.

Anchor: ECSS-Q-ST-60C clause 5.7 (recording the outcomes of the inspection and
control activities carried out across the class 2 parts programme). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Put the performed activities into audit order and group the submitted
   records under the activity each one covers.
2. Name every performed activity that carries no record at all.
3. Test each record for a traceable lot identity, an accepted recording
   authority, an evidence reference, four stated quantities that reconcile, a
   nonconformance reference behind every rejected quantity, and no deferred
   quantity left open.
4. Measure outcome coverage as the share of performed activities covered by at
   least one defect-free record and judge it against its floor.
5. Measure the programme acceptance yield and raise an advisory when it sits
   below the advisory floor.
6. Return one disposition: outcomes-recorded, outcomes-partially-recorded or
   outcomes-not-reconstructable.
"""

import math

__all__ = [
    "ACCEPTANCE_YIELD_ADVISORY_FLOOR",
    "BOUND_TOLERANCE",
    "CLASS_2_INSPECTION_ACTIVITIES",
    "OUTCOME_COVERAGE_FLOOR",
    "QUANTITY_FIELDS",
    "RECORDING_AUTHORITIES",
    "ordered_activities",
    "record_activity",
    "stated_quantities",
    "reconciliation_residual",
    "record_defects",
    "group_records_by_activity",
    "unrecorded_activities",
    "defective_records",
    "reconciled_activities",
    "outcome_coverage",
    "coverage_meets_floor",
    "acceptance_yield",
    "recording_disposition",
    "compile_class_2_inspection_outcomes",
]

# Coverage is a quotient of small counts and the residual is a difference of
# measured quantities; a case sitting exactly on a bound can land a few ULP on
# the wrong side. Absorb the representation error here, never by moving the
# bound itself.
BOUND_TOLERANCE = 1e-9

# The inspection and control activities whose outcome a class 2 parts
# programme records, in the order the records are presented for audit.
CLASS_2_INSPECTION_ACTIVITIES = (
    "part-approval-review",
    "manufacturer-surveillance",
    "incoming-inspection",
    "lot-acceptance-test",
    "screening-verification",
    "nonconformance-review",
    "delivery-acceptance-review",
)

_ACTIVITY_ORDER = {
    name: index for index, name in enumerate(CLASS_2_INSPECTION_ACTIVITIES)
}

# Class 2 lets the outcome be written up by a delegated or supplier-side
# authority as well as by the project. Anyone outside this list records that
# somebody was present, not that the outcome was taken.
RECORDING_AUTHORITIES = (
    "project-quality-assurance",
    "delegated-inspector",
    "component-manufacturer",
    "procurement-agent",
)

# The four counts an outcome record owes. inspected is the total presented;
# the other three account for where every presented part went.
QUANTITY_FIELDS = ("inspected", "accepted", "rejected", "deferred")

# Share of performed activities that must carry a defect-free record.
OUTCOME_COVERAGE_FLOOR = 0.9

# Programme acceptance yield below this raises an advisory, never a defect:
# a low yield is a real outcome, honestly recorded.
ACCEPTANCE_YIELD_ADVISORY_FLOOR = 0.95


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _normalise_authorities(accepted_authorities):
    """Return the accepted recording authorities, folded for comparison."""
    if accepted_authorities is None:
        accepted_authorities = RECORDING_AUTHORITIES
    if not isinstance(accepted_authorities, (list, tuple, set, frozenset)):
        raise ValueError("accepted_authorities must be a sequence or set")
    names = set()
    for item in accepted_authorities:
        names.add(_require_text(item, "recording authority").casefold())
    if not names:
        raise ValueError("accepted_authorities must name at least one authority")
    return names


def ordered_activities(activities):
    """Return the activities in audit order, rejecting unknown or repeated names."""
    if not isinstance(activities, (list, tuple, set, frozenset)):
        raise ValueError("activities must be a sequence or set")
    names = []
    for item in activities:
        name = _require_text(item, "activity").casefold()
        if name not in _ACTIVITY_ORDER:
            raise ValueError(
                "unknown inspection activity %r; expected one of %r"
                % (item, list(CLASS_2_INSPECTION_ACTIVITIES))
            )
        if name in names:
            raise ValueError("activity %r listed twice" % name)
        names.append(name)
    return sorted(names, key=lambda name: _ACTIVITY_ORDER[name])


def record_activity(record):
    """Return the recognised activity a record covers, or None.

    A record naming nothing, or naming something outside the activity list,
    covers no activity and cannot close one.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    named = record.get("activity")
    if not _is_text(named):
        return None
    folded = named.strip().casefold()
    if folded not in _ACTIVITY_ORDER:
        return None
    return folded


def stated_quantities(record):
    """Return the four stated counts of one record as floats, or raise.

    A count that is absent, non-numeric or negative is not a stated count, and
    a record without four of them states no outcome at all.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    counts = {}
    for field in QUANTITY_FIELDS:
        if field not in record:
            raise ValueError("record states no %s quantity" % field)
        counts[field] = _require_number(record[field], "%s quantity" % field)
    return counts


def reconciliation_residual(record):
    """Return inspected minus the accounted-for counts of one record.

    Zero means every presented part is accounted for. A positive residual
    means parts went unaccounted; a negative one means the record accounts for
    more parts than it says were presented.
    """
    counts = stated_quantities(record)
    return counts["inspected"] - (
        counts["accepted"] + counts["rejected"] + counts["deferred"]
    )


def record_defects(record, accepted_authorities=None):
    """Return the defect codes one outcome record carries.

    An empty list means the record states a reconciled outcome. record keys
    read here: activity, lot_code, recording_authority, evidence_reference,
    inspected, accepted, rejected, deferred and nonconformance_reference.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    accepted = _normalise_authorities(accepted_authorities)
    defects = []
    if record_activity(record) is None:
        defects.append("activity-not-recognised")
    if not _is_text(record.get("lot_code")):
        defects.append("lot-identity-not-traceable")
    authority = record.get("recording_authority")
    if not _is_text(authority):
        defects.append("recording-authority-not-named")
    elif authority.strip().casefold() not in accepted:
        defects.append("recording-authority-not-accepted")
    if not _is_text(record.get("evidence_reference")):
        defects.append("evidence-reference-missing")
    try:
        counts = stated_quantities(record)
    except ValueError:
        defects.append("quantities-not-stated")
        return defects
    if counts["inspected"] <= BOUND_TOLERANCE:
        defects.append("no-quantity-inspected")
    residual = counts["inspected"] - (
        counts["accepted"] + counts["rejected"] + counts["deferred"]
    )
    if abs(residual) > BOUND_TOLERANCE:
        defects.append("quantities-do-not-reconcile")
    if counts["rejected"] > BOUND_TOLERANCE and not _is_text(
        record.get("nonconformance_reference")
    ):
        defects.append("rejected-quantity-without-nonconformance-reference")
    if counts["deferred"] > BOUND_TOLERANCE:
        defects.append("deferred-quantity-still-open")
    return defects


def group_records_by_activity(records):
    """Return the submitted records grouped under the activity each covers.

    Records naming no recognised activity are grouped under the None key, so
    they stay visible rather than being silently dropped.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    grouped = {}
    for record in records:
        grouped.setdefault(record_activity(record), []).append(record)
    return grouped


def unrecorded_activities(activities_performed, records):
    """Return the performed activities carrying no record at all, in audit order."""
    performed = ordered_activities(activities_performed)
    grouped = group_records_by_activity(records)
    return [name for name in performed if not grouped.get(name)]


def defective_records(records, accepted_authorities=None):
    """Return one entry per defective record, keeping submission order.

    Each entry names the record reference and the defect codes it carries.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    findings = []
    for index, record in enumerate(records):
        defects = record_defects(record, accepted_authorities)
        if defects:
            if isinstance(record, dict) and _is_text(record.get("record_id")):
                reference = record["record_id"].strip()
            else:
                reference = "record-%d" % index
            findings.append({"record": reference, "defects": defects})
    return findings


def reconciled_activities(activities_performed, records,
                          accepted_authorities=None):
    """Return the performed activities covered by a defect-free record."""
    performed = ordered_activities(activities_performed)
    grouped = group_records_by_activity(records)
    covered = []
    for name in performed:
        for record in grouped.get(name, []):
            if not record_defects(record, accepted_authorities):
                covered.append(name)
                break
    return covered


def outcome_coverage(activities_performed, records, accepted_authorities=None):
    """Return the share of performed activities with a defect-free record."""
    performed = ordered_activities(activities_performed)
    if not performed:
        raise ValueError("activities_performed must name at least one activity")
    covered = reconciled_activities(performed, records, accepted_authorities)
    return len(covered) / float(len(performed))


def coverage_meets_floor(coverage, floor=OUTCOME_COVERAGE_FLOOR):
    """Return True when the coverage share reaches its floor.

    A share sitting exactly on the floor meets it; the tolerance absorbs the
    representation error rather than moving the floor.
    """
    value = _require_number(coverage, "coverage")
    limit = _require_number(floor, "floor")
    if value > 1.0 + BOUND_TOLERANCE:
        raise ValueError("coverage must not exceed one, got %g" % value)
    return value >= limit - BOUND_TOLERANCE


def acceptance_yield(records):
    """Return accepted parts over inspected parts across the stated records.

    Records that state no quantities contribute nothing; a record set stating
    no quantities at all has no yield to report.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    inspected = 0.0
    accepted = 0.0
    stated = 0
    for record in records:
        try:
            counts = stated_quantities(record)
        except ValueError:
            continue
        stated += 1
        inspected += counts["inspected"]
        accepted += counts["accepted"]
    if stated == 0:
        raise ValueError("no record states a quantity; no yield to report")
    if inspected <= BOUND_TOLERANCE:
        raise ValueError("no part was inspected; no yield to report")
    return accepted / inspected


def recording_disposition(unrecorded, coverage):
    """Return the disposition implied by the record set.

    A performed activity with no record at all cannot be reconstructed from
    anything else, so it outranks a coverage shortfall.
    """
    if not isinstance(unrecorded, (list, tuple)):
        raise ValueError("unrecorded must be a sequence, got %r" % (unrecorded,))
    share = _require_number(coverage, "coverage")
    if unrecorded:
        return "outcomes-not-reconstructable"
    if not coverage_meets_floor(share):
        return "outcomes-partially-recorded"
    return "outcomes-recorded"


def compile_class_2_inspection_outcomes(programme):
    """Audit the clause 5.7 outcome record set of one class 2 parts programme.

    programme keys: activities_performed, records, an optional
    accepted_authorities list and an optional programme_id.
    """
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    performed = ordered_activities(programme.get("activities_performed", []))
    if not performed:
        raise ValueError("activities_performed must name at least one activity")
    records = programme.get("records", [])
    accepted = programme.get("accepted_authorities")
    missing = unrecorded_activities(performed, records)
    defects = defective_records(records, accepted)
    covered = reconciled_activities(performed, records, accepted)
    coverage = outcome_coverage(performed, records, accepted)
    advisories = []
    try:
        yield_share = acceptance_yield(records)
    except ValueError:
        yield_share = None
        advisories.append("acceptance-yield-not-reportable")
    else:
        if yield_share < ACCEPTANCE_YIELD_ADVISORY_FLOOR - BOUND_TOLERANCE:
            advisories.append("acceptance-yield-below-advisory-floor")
    disposition = recording_disposition(missing, coverage)
    return {
        "activities_performed": performed,
        "unrecorded_activities": missing,
        "defective_records": defects,
        "reconciled_activities": covered,
        "outcome_coverage": coverage,
        "coverage_meets_floor": coverage_meets_floor(coverage),
        "acceptance_yield": yield_share,
        "advisories": advisories,
        "disposition": disposition,
        "audit_ready": disposition == "outcomes-recorded",
    }

"""Documentation of inspection and control outcomes across a class 1 parts programme.

Anchor: ECSS-Q-ST-60C clause 4.7 (recording the outcomes of the inspection and
control activities carried out across the class 1 parts programme). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group the submitted records by the activity each one covers and name every
   performed activity that carries no record at all.
2. Test each record for the fields an auditable record owes: a traceable lot
   identity, a stated outcome, an authorised signatory, an evidence reference
   and a disposition behind every failed outcome.
3. Measure the retention shortfall between the programme retention period and
   the period the records are actually kept for.
4. Measure documentation completeness as the fraction of performed activities
   covered by at least one defect-free record.
5. Return one disposition: documentation-complete, documentation-incomplete or
   documentation-not-auditable.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "INSPECTION_ACTIVITIES",
    "RECORD_OUTCOMES",
    "RETENTION_REQUIREMENT_YEARS",
    "ordered_activities",
    "record_activity",
    "record_defects",
    "group_records_by_activity",
    "unrecorded_activities",
    "defective_records",
    "sound_activities",
    "retention_shortfall_years",
    "documentation_completeness",
    "documentation_disposition",
    "compile_class_1_inspection_records",
]

# Completeness is a quotient of small counts and the retention shortfall is a
# difference of measured years; a case sitting exactly on a bound can land a
# few ULP on the wrong side. Absorb the representation error here, never by
# moving the bound itself.
BOUND_TOLERANCE = 1e-9

# Every inspection and control activity whose outcome the programme records,
# in the order the records are presented for audit.
INSPECTION_ACTIVITIES = (
    "parts-approval-review",
    "manufacturer-source-inspection",
    "incoming-inspection",
    "lot-acceptance-test",
    "destructive-physical-analysis",
    "radiation-verification",
    "nonconformance-review",
    "delivery-acceptance-review",
)

_ACTIVITY_ORDER = {name: index for index, name in enumerate(INSPECTION_ACTIVITIES)}

# The outcomes a record may state. Anything else is an unstated outcome.
RECORD_OUTCOMES = ("pass", "fail", "pending")

# Years after delivery the inspection evidence must remain retrievable.
RETENTION_REQUIREMENT_YEARS = 10.0


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


def _normalise_signatories(authorised_signatories):
    """Return the authorised signatory names, folded for comparison."""
    if not isinstance(authorised_signatories, (list, tuple, set, frozenset)):
        raise ValueError("authorised_signatories must be a sequence or set")
    names = set()
    for item in authorised_signatories:
        names.add(_require_text(item, "authorised signatory").casefold())
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
                % (item, list(INSPECTION_ACTIVITIES))
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


def record_defects(record, authorised_signatories):
    """Return the defect codes one inspection record carries.

    An empty list means the record is auditable as it stands. record keys read
    here: activity, lot_code, outcome, signatory, evidence_reference and
    nonconformance_disposition.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    authorised = _normalise_signatories(authorised_signatories)
    defects = []
    if record_activity(record) is None:
        defects.append("activity-not-recognised")
    if not _is_text(record.get("lot_code")):
        defects.append("lot-identity-not-traceable")
    outcome = record.get("outcome")
    stated = _is_text(outcome) and outcome.strip().casefold() in RECORD_OUTCOMES
    if not stated:
        defects.append("outcome-not-stated")
    signatory = record.get("signatory")
    if not _is_text(signatory):
        defects.append("signatory-not-named")
    elif signatory.strip().casefold() not in authorised:
        defects.append("signatory-not-authorised")
    if not _is_text(record.get("evidence_reference")):
        defects.append("evidence-reference-missing")
    if stated and outcome.strip().casefold() == "fail":
        if not _is_text(record.get("nonconformance_disposition")):
            defects.append("failed-outcome-without-disposition")
    if stated and outcome.strip().casefold() == "pending":
        defects.append("outcome-still-open")
    return defects


def group_records_by_activity(records):
    """Return the submitted records grouped under the activity each covers.

    Records naming no recognised activity are grouped under the None key, so
    they are visible rather than silently dropped.
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


def defective_records(records, authorised_signatories):
    """Return one entry per defective record, keeping submission order.

    Each entry names the record reference and the defect codes it carries.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    findings = []
    for index, record in enumerate(records):
        defects = record_defects(record, authorised_signatories)
        if defects:
            if isinstance(record, dict) and _is_text(record.get("record_id")):
                reference = record["record_id"].strip()
            else:
                reference = "record-%d" % index
            findings.append({"record": reference, "defects": defects})
    return findings


def sound_activities(activities_performed, records, authorised_signatories):
    """Return the performed activities covered by a defect-free record."""
    performed = ordered_activities(activities_performed)
    grouped = group_records_by_activity(records)
    sound = []
    for name in performed:
        for record in grouped.get(name, []):
            if not record_defects(record, authorised_signatories):
                sound.append(name)
                break
    return sound


def retention_shortfall_years(retained_years):
    """Return the years by which the retention period falls short, never below zero."""
    retained = _require_number(retained_years, "retained_years")
    shortfall = RETENTION_REQUIREMENT_YEARS - retained
    if shortfall <= BOUND_TOLERANCE:
        return 0.0
    return shortfall


def documentation_completeness(activities_performed, records,
                               authorised_signatories):
    """Return the fraction of performed activities with a defect-free record."""
    performed = ordered_activities(activities_performed)
    if not performed:
        raise ValueError("activities_performed must name at least one activity")
    sound = sound_activities(performed, records, authorised_signatories)
    return len(sound) / float(len(performed))


def documentation_disposition(unrecorded, defects, shortfall_years):
    """Return the disposition implied by the record set.

    A retention shortfall overrides everything: evidence that will not survive
    to the audit cannot be called complete however sound it reads today.
    """
    for label, value in (("unrecorded", unrecorded), ("defects", defects)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    shortfall = _require_number(shortfall_years, "shortfall_years")
    if shortfall > BOUND_TOLERANCE:
        return "documentation-not-auditable"
    if unrecorded or defects:
        return "documentation-incomplete"
    return "documentation-complete"


def compile_class_1_inspection_records(programme):
    """Audit the clause 4.7 record set of one class 1 parts programme.

    programme keys: activities_performed, records, authorised_signatories and
    retention_years, plus an optional programme_id.
    """
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    performed = ordered_activities(programme.get("activities_performed", []))
    if not performed:
        raise ValueError("activities_performed must name at least one activity")
    records = programme.get("records", [])
    authorised = programme.get("authorised_signatories", [])
    missing = unrecorded_activities(performed, records)
    defects = defective_records(records, authorised)
    sound = sound_activities(performed, records, authorised)
    shortfall = retention_shortfall_years(programme.get("retention_years", 0.0))
    completeness = documentation_completeness(performed, records, authorised)
    disposition = documentation_disposition(missing, defects, shortfall)
    return {
        "activities_performed": performed,
        "unrecorded_activities": missing,
        "defective_records": defects,
        "sound_activities": sound,
        "retention_shortfall_years": shortfall,
        "documentation_completeness": completeness,
        "disposition": disposition,
        "audit_ready": disposition == "documentation-complete",
    }

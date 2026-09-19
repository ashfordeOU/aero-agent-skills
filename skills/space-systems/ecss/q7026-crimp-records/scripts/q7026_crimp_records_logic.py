"""Completeness and traceability of crimping records.

Anchor: ECSS-Q-ST-70-26C, the records clause of the crimping practice
-- what each crimping entry has to carry, what each entry has to
resolve into, and how long the dossier is kept (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. A record is only worth what it resolves into. A tool identifier
   that is not in the calibration register, an operator identifier
   that is not in the personnel register and a lot number with no
   receiving record are text, not traceability.
2. Certification is checked on the date of the crimp, not the date of
   the audit. An operator certified today may not have been certified
   the morning the harness was built, and that is the question the
   dossier answers.
3. A lot that was received but never accepted is not traceable in the
   sense that matters. The chain has to end in an accepted receiving
   record, otherwise it ends in an open question.
4. Periodic pull-test samples police a run, so the cadence is graded
   across the record set in date order, not inside one entry. A gap
   between samples larger than the declared interval leaves the
   terminations in between unpoliced.
5. A missing field and an unresolved reference are different failures
   and go to different people. One is completed at the bench, the
   other is an investigation, so they are reported apart.
6. Retention runs in calendar years from the crimp date, and the last
   day of retention is still inside it. A record disposed of a day
   early is a finding whatever the arithmetic said.

Stdlib only, offline, deterministic.
"""

import datetime

REQUIRED_FIELDS = (
    "record_id",
    "crimp_date",
    "tool_id",
    "operator_id",
    "contact_lot",
    "wire_lot",
    "terminations_made",
)

COMPLETE = "record-complete-and-traceable"
INCOMPLETE = "record-incomplete"
UNTRACEABLE = "record-not-traceable-to-its-registers"

DOSSIER_ACCEPTED = "dossier-accepted"
DOSSIER_ACCEPTED_WITH_FINDINGS = "dossier-accepted-with-findings"
DOSSIER_REJECTED = "dossier-rejected"

RETAINED = "within-retention"
RETENTION_ELAPSED = "retention-period-elapsed"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_date(label, value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(label, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def add_years(start, years):
    """Add whole calendar years, stepping a 29 February back to the 28th."""
    reference = parse_date("start", start)
    count = _count("years", years, 0)
    try:
        return reference.replace(year=reference.year + count)
    except ValueError:
        return reference.replace(year=reference.year + count, day=28)


def validate_policy(policy):
    """Validate the declared records policy."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    return {
        "pull_test_every_n_terminations": _count(
            "pull_test_every_n_terminations",
            policy.get("pull_test_every_n_terminations"),
            1,
        ),
        "retention_years": _count(
            "retention_years", policy.get("retention_years"), 1
        ),
    }


def validate_registers(registers):
    """Validate the registers a crimping record has to resolve into."""
    if not isinstance(registers, dict):
        raise ValueError("registers must be a mapping")

    tools = registers.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("tools must be a non-empty list")
    tool_ids = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("each tool entry must be a mapping")
        tool_ids.add(_text("tool_id", tool.get("tool_id")).upper())

    operators = registers.get("operators")
    if not isinstance(operators, list) or not operators:
        raise ValueError("operators must be a non-empty list")
    operator_windows = {}
    for entry in operators:
        if not isinstance(entry, dict):
            raise ValueError("each operator entry must be a mapping")
        key = _text("operator_id", entry.get("operator_id")).upper()
        start = parse_date("certified_from", entry.get("certified_from"))
        end = parse_date("certified_until", entry.get("certified_until"))
        if end < start:
            raise ValueError(
                "operator %r has a certification window ending before it starts"
                % key
            )
        operator_windows[key] = (start, end)

    lots = registers.get("lots")
    if not isinstance(lots, list) or not lots:
        raise ValueError("lots must be a non-empty list")
    lot_accepted = {}
    for lot in lots:
        if not isinstance(lot, dict):
            raise ValueError("each lot entry must be a mapping")
        key = _text("lot_id", lot.get("lot_id")).upper()
        lot_accepted[key] = _flag(
            "receiving_accepted", lot.get("receiving_accepted")
        )

    return {
        "tool_ids": tool_ids,
        "operator_windows": operator_windows,
        "lot_accepted": lot_accepted,
    }


def validate_record(record):
    """Validate one crimping record entry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    pull_ref = record.get("pull_test_reference")
    if pull_ref is not None:
        pull_ref = _text("pull_test_reference", pull_ref)
    return {
        "record_id": _text("record_id", record.get("record_id")),
        "crimp_date": parse_date("crimp_date", record.get("crimp_date")),
        "tool_id": _text("tool_id", record.get("tool_id")).upper(),
        "operator_id": _text("operator_id", record.get("operator_id")).upper(),
        "contact_lot": _text("contact_lot", record.get("contact_lot")).upper(),
        "wire_lot": _text("wire_lot", record.get("wire_lot")).upper(),
        "terminations_made": _count(
            "terminations_made", record.get("terminations_made"), 1
        ),
        "pull_test_reference": pull_ref,
    }


def missing_fields(record):
    """Which mandatory fields the entry does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    absent = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None:
            absent.append(field)
        elif isinstance(value, str) and not value.strip():
            absent.append(field)
    return absent


def resolve_references(record, registers):
    """Resolve the tool, operator and lot references of one entry."""
    checked = validate_record(record)
    known = validate_registers(registers)
    unresolved = []

    if checked["tool_id"] not in known["tool_ids"]:
        unresolved.append("tool-identifier-not-in-the-calibration-register")

    window = known["operator_windows"].get(checked["operator_id"])
    if window is None:
        unresolved.append("operator-identifier-not-in-the-personnel-register")
    elif not (window[0] <= checked["crimp_date"] <= window[1]):
        unresolved.append("operator-not-certified-on-the-date-of-the-crimp")

    for field, label in (
        ("contact_lot", "contact-lot"),
        ("wire_lot", "wire-lot"),
    ):
        lot = checked[field]
        if lot not in known["lot_accepted"]:
            unresolved.append("%s-has-no-receiving-record" % label)
        elif not known["lot_accepted"][lot]:
            unresolved.append("%s-receiving-inspection-not-accepted" % label)

    return {"unresolved": unresolved, "traceable": not unresolved}


def retention_state(record, policy, as_of):
    """Whether this entry is still inside its retention period."""
    checked = validate_record(record)
    rules = validate_policy(policy)
    today = parse_date("as_of", as_of)
    retain_until = add_years(checked["crimp_date"], rules["retention_years"])
    return {
        "retain_until": retain_until,
        "state": RETAINED if today <= retain_until else RETENTION_ELAPSED,
        "still_required": today <= retain_until,
    }


def audit_record(record, registers, policy, as_of):
    """Audit one crimping record for completeness and traceability."""
    absent = missing_fields(record)
    if absent:
        return {
            "record_id": record.get("record_id") or "unidentified-record",
            "disposition": INCOMPLETE,
            "missing_fields": absent,
            "unresolved": [],
            "retention": None,
            "acceptable": False,
        }
    checked = validate_record(record)
    references = resolve_references(record, registers)
    retention = retention_state(record, policy, as_of)
    disposition = COMPLETE if references["traceable"] else UNTRACEABLE
    return {
        "record_id": checked["record_id"],
        "disposition": disposition,
        "missing_fields": [],
        "unresolved": references["unresolved"],
        "retention": retention,
        "acceptable": disposition == COMPLETE,
    }


def pull_test_cadence(records, policy):
    """Grade the periodic pull-test cadence across a record set."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    rules = validate_policy(policy)
    checked = [validate_record(r) for r in records]
    checked.sort(key=lambda r: (r["crimp_date"], r["record_id"]))

    interval = rules["pull_test_every_n_terminations"]
    unpoliced = 0
    gaps = []
    for entry in checked:
        unpoliced += entry["terminations_made"]
        if entry["pull_test_reference"] is not None:
            if unpoliced > interval:
                gaps.append(entry["record_id"])
            unpoliced = 0
    trailing = unpoliced > interval
    if trailing:
        gaps.append("open-run-at-the-end-of-the-set")
    return {
        "interval": interval,
        "gaps": gaps,
        "unpoliced_at_end": unpoliced,
        "cadence_held": not gaps,
    }


def audit_dossier(records, registers, policy, as_of):
    """Audit a harness dossier of crimping records."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = [audit_record(r, registers, policy, as_of) for r in records]
    incomplete = [
        r["record_id"] for r in results if r["disposition"] == INCOMPLETE
    ]
    untraceable = [
        r["record_id"] for r in results if r["disposition"] == UNTRACEABLE
    ]

    cadence = None
    findings = []
    if not incomplete:
        cadence = pull_test_cadence(records, policy)
        if not cadence["cadence_held"]:
            findings.append("periodic-pull-test-cadence-not-held")
    expired = [
        r["record_id"]
        for r in results
        if r["retention"] is not None and not r["retention"]["still_required"]
    ]
    if expired:
        findings.append("entries-past-their-retention-period")

    if incomplete or untraceable:
        verdict = DOSSIER_REJECTED
    elif findings:
        verdict = DOSSIER_ACCEPTED_WITH_FINDINGS
    else:
        verdict = DOSSIER_ACCEPTED

    return {
        "results": results,
        "verdict": verdict,
        "incomplete": incomplete,
        "untraceable": untraceable,
        "findings": findings,
        "past_retention": expired,
        "cadence": cadence,
    }

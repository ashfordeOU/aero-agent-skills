"""Source buy-off release decision for an intermediate assurance commercial lot.

Anchor: ECSS-Q-ST-60-13C clause 5.3.6 (the final source inspection that
releases a lot of the intermediate assurance class for delivery). Paraphrased
into an implementable procedure; no standard text is reproduced.

What the intermediate class changes
-----------------------------------
The buy-off may be carried out by a delegate rather than by the customer in
person, and it may be carried out at a distance. Both concessions move the
question from "was the lot inspected" to "was the inspection credible", so the
procedure below validates the delegation and the attendance mode before it
looks at a single piece of evidence.

Procedure implemented here
--------------------------
1. Validate the delegation record: a named delegate, a named delegating
   organisation, and a validity window that covers the day of the buy-off. An
   organisation that delegated the witness of its own lot to itself has not
   delegated anything.
2. Take the evidence set the declared attendance mode demands. A documentary
   buy-off substitutes a photographic record set and a supplier release note
   for the presence that was given up; a remote-witnessed buy-off substitutes
   the recording of the live witness.
3. Score each required item as seen directly, carried by a named supplier data
   pack reference, or absent. A referenced item counts below a direct one and
   a reference with no document named behind it is absent.
4. Scale the open-minor allowance to the lot in integer arithmetic so the same
   lot size yields the same allowance on every machine.
5. Check the sequence: a buy-off dated before the lot conformance review closed
   released a lot the review had not yet judged.
6. Return one of three dispositions. An uncredible delegation escalates to a
   witnessed buy-off, blocking findings hold the lot at source, and only a
   clean pass on every gate releases it for delivery.
"""

import datetime
import math

__all__ = [
    "ATTENDANCE_MODES",
    "BASE_EVIDENCE",
    "MODE_EXTRA_EVIDENCE",
    "REFERENCED_CREDIT",
    "DOCUMENTARY_COVERAGE_FLOOR",
    "SEVERITIES",
    "STATES",
    "MAX_MINOR_ALLOWANCE",
    "required_evidence",
    "normalize_evidence",
    "evidence_coverage",
    "minor_allowance",
    "group_findings",
    "parse_buy_off_date",
    "validate_delegation",
    "sequence_gap",
    "assess_class_2_buy_off",
]

# How the buy-off was attended. Each mode buys back, with evidence, whatever
# presence it gave up.
ATTENDANCE_MODES = ("on-site", "remote-witnessed", "documentary")

# The evidence every intermediate class buy-off needs, whatever the mode.
BASE_EVIDENCE = (
    "traceability-records",
    "lot-conformance-review-report",
    "screening-report",
    "packaging-and-marking-evidence",
    "certificate-of-conformity",
)

# What each mode adds on top of the base set.
MODE_EXTRA_EVIDENCE = {
    "on-site": (),
    "remote-witnessed": ("live-witness-recording",),
    "documentary": ("photographic-record-set", "supplier-release-note"),
}

# An item carried by a named data pack reference counts, but below an item the
# witness saw for himself.
REFERENCED_CREDIT = 0.6

# A documentary buy-off whose weighted coverage falls below this share is not
# credible enough to release on; it escalates to a witnessed buy-off.
DOCUMENTARY_COVERAGE_FLOOR = 0.8

SEVERITIES = ("major", "minor")
STATES = ("open", "closed", "waived")

# The lot-scaled minor allowance never grows past this.
MAX_MINOR_ALLOWANCE = 5


def _at_least(value, bound, tolerance=1e-9):
    """Return True when value is at or above bound, absorbing float error."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=tolerance)


def required_evidence(mode):
    """Return the evidence set the declared attendance mode demands."""
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("attendance mode must be a non-empty string")
    key = mode.strip().lower()
    if key not in ATTENDANCE_MODES:
        raise ValueError("attendance mode must be one of %s, got %r" % (ATTENDANCE_MODES, mode))
    return tuple(BASE_EVIDENCE) + tuple(MODE_EXTRA_EVIDENCE[key])


def normalize_evidence(evidence):
    """Return the evidence record as item name to one of seen/referenced/absent."""
    states = ("seen", "referenced", "absent")
    if isinstance(evidence, (list, tuple, set, frozenset)):
        evidence = {str(item): "seen" for item in evidence}
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping or a sequence of item names")
    normalized = {}
    for key, value in evidence.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("evidence item names must be non-empty strings, got %r" % (key,))
        name = key.strip().lower()
        if isinstance(value, bool):
            normalized[name] = "seen" if value else "absent"
            continue
        if not isinstance(value, str) or value.strip().lower() not in states:
            raise ValueError(
                "evidence['%s'] must be one of %s or a boolean, got %r" % (name, states, value)
            )
        normalized[name] = value.strip().lower()
    return normalized


def evidence_coverage(evidence, mode, references=None):
    """Return the weighted coverage of the evidence set for this attendance mode.

    A referenced item needs a named entry in references; a reference with no
    document behind it is counted as absent, because nothing can be audited
    from it later.
    """
    required = required_evidence(mode)
    record = normalize_evidence(evidence)
    if references is None:
        references = {}
    if not isinstance(references, dict):
        raise ValueError("references must be a mapping of item name to document reference")
    refs = {}
    for key, value in references.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("reference keys must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("reference for '%s' must be a non-empty string" % key.strip())
        refs[key.strip().lower()] = value.strip()
    direct = []
    referenced = []
    absent = []
    unsupported = []
    for item in required:
        state = record.get(item, "absent")
        if state == "seen":
            direct.append(item)
        elif state == "referenced":
            if item in refs:
                referenced.append(item)
            else:
                unsupported.append(item)
                absent.append(item)
        else:
            absent.append(item)
    weighted = (len(direct) + REFERENCED_CREDIT * len(referenced)) / len(required)
    return {
        "mode": mode.strip().lower(),
        "required": list(required),
        "direct": direct,
        "referenced": referenced,
        "absent": absent,
        "unsupported_references": unsupported,
        "coverage": weighted,
        "complete": not absent,
    }


def minor_allowance(lot_size, base=1):
    """Return the open-minor allowance for a lot, in integer arithmetic only."""
    for label, value in (("lot_size", lot_size), ("base", base)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if lot_size < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot_size)
    if base < 0:
        raise ValueError("base must be non-negative, got %d" % base)
    scaled = base + math.isqrt(lot_size) // 10
    return min(scaled, MAX_MINOR_ALLOWANCE)


def group_findings(items, allowance):
    """Group the buy-off findings by severity and state.

    Each item is a mapping with an id, a severity in SEVERITIES and a state in
    STATES; a waived item carries the reference of the approved waiver.
    """
    if not isinstance(allowance, int) or isinstance(allowance, bool):
        raise ValueError("allowance must be an integer")
    if allowance < 0:
        raise ValueError("allowance must be non-negative, got %d" % allowance)
    if items is None:
        items = []
    if not isinstance(items, (list, tuple)):
        raise ValueError("findings must be a sequence of mappings")
    open_major = []
    open_minor = []
    waived = []
    closed = []
    seen_ids = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("findings[%d] must be a mapping" % index)
        for key in ("id", "severity", "state"):
            if key not in item:
                raise ValueError("findings[%d] missing required key '%s'" % (index, key))
        ident = item["id"]
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError("findings[%d] id must be a non-empty string" % index)
        ident = ident.strip()
        if ident in seen_ids:
            raise ValueError("finding id '%s' appears more than once" % ident)
        seen_ids.add(ident)
        severity = item["severity"]
        if not isinstance(severity, str) or severity.strip().lower() not in SEVERITIES:
            raise ValueError(
                "findings[%d] severity must be one of %s, got %r" % (index, SEVERITIES, severity)
            )
        severity = severity.strip().lower()
        state = item["state"]
        if not isinstance(state, str) or state.strip().lower() not in STATES:
            raise ValueError(
                "findings[%d] state must be one of %s, got %r" % (index, STATES, state)
            )
        state = state.strip().lower()
        if state == "waived":
            reference = item.get("waiver_ref")
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError(
                    "finding '%s' is waived without an approved waiver reference" % ident
                )
            waived.append(ident)
        elif state == "closed":
            closed.append(ident)
        elif severity == "major":
            open_major.append(ident)
        else:
            open_minor.append(ident)
    return {
        "open_major": open_major,
        "open_minor": open_minor,
        "waived": waived,
        "closed": closed,
        "allowance": allowance,
        "minor_over_allowance": len(open_minor) > allowance,
        "blocking": bool(open_major) or len(open_minor) > allowance,
    }


def parse_buy_off_date(value, label="date"):
    """Return an ISO yyyy-mm-dd value parsed into a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, value))


def validate_delegation(record, buy_off_date):
    """Return the validated delegation behind an intermediate class buy-off.

    record keys: delegate, delegate_organisation, delegating_organisation,
    valid_from and valid_to as ISO dates, and the producing organisation the
    lot came from.
    """
    if not isinstance(record, dict):
        raise ValueError("delegation must be a mapping")
    required = (
        "delegate",
        "delegate_organisation",
        "delegating_organisation",
        "valid_from",
        "valid_to",
        "producer_organisation",
    )
    for key in required:
        if key not in record:
            raise ValueError("delegation missing required key '%s'" % key)
    names = {}
    for key in ("delegate", "delegate_organisation", "delegating_organisation", "producer_organisation"):
        value = record[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("delegation %s must be a non-empty string" % key)
        names[key] = value.strip()
    when = parse_buy_off_date(buy_off_date, "buy_off_date")
    valid_from = parse_buy_off_date(record["valid_from"], "valid_from")
    valid_to = parse_buy_off_date(record["valid_to"], "valid_to")
    if valid_to < valid_from:
        raise ValueError("delegation valid_to precedes valid_from")
    producer = names["producer_organisation"].lower()
    self_delegated = names["delegate_organisation"].lower() == producer
    return {
        "delegate": names["delegate"],
        "delegate_organisation": names["delegate_organisation"],
        "delegating_organisation": names["delegating_organisation"],
        "producer_organisation": names["producer_organisation"],
        "valid_from": valid_from.isoformat(),
        "valid_to": valid_to.isoformat(),
        "in_force": valid_from <= when <= valid_to,
        "self_delegated": self_delegated,
        "credible": (valid_from <= when <= valid_to) and not self_delegated,
    }


def sequence_gap(review_completed, buy_off_date):
    """Return the signed day gap from the lot conformance review to the buy-off."""
    completed = parse_buy_off_date(review_completed, "review_completed")
    when = parse_buy_off_date(buy_off_date, "buy_off_date")
    return (when - completed).days


def assess_class_2_buy_off(spec):
    """Run the full clause 5.3.6 source buy-off release assessment.

    spec keys: lot_id, lot_size, buy_off_date, review_completed, attendance
    mode, delegation, evidence, and optionally data_pack_references, findings
    and allowance_base.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "lot_id",
        "lot_size",
        "buy_off_date",
        "review_completed",
        "attendance_mode",
        "delegation",
        "evidence",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_id = spec["lot_id"]
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string")
    delegation = validate_delegation(spec["delegation"], spec["buy_off_date"])
    coverage = evidence_coverage(
        spec["evidence"], spec["attendance_mode"], spec.get("data_pack_references")
    )
    gap = sequence_gap(spec["review_completed"], spec["buy_off_date"])
    allowance = minor_allowance(spec["lot_size"], spec.get("allowance_base", 1))
    grouped = group_findings(spec.get("findings"), allowance)

    escalation_reasons = []
    if not delegation["in_force"]:
        escalation_reasons.append(
            "delegation not in force on %s (valid %s to %s)"
            % (
                parse_buy_off_date(spec["buy_off_date"], "buy_off_date").isoformat(),
                delegation["valid_from"],
                delegation["valid_to"],
            )
        )
    if delegation["self_delegated"]:
        escalation_reasons.append(
            "the producing organisation '%s' delegated the witness of its own lot to itself"
            % delegation["producer_organisation"]
        )
    if coverage["mode"] == "documentary" and not _at_least(
        coverage["coverage"], DOCUMENTARY_COVERAGE_FLOOR
    ):
        escalation_reasons.append(
            "documentary buy-off coverage %.3f below the floor of %.3f"
            % (coverage["coverage"], DOCUMENTARY_COVERAGE_FLOOR)
        )

    hold_reasons = []
    if coverage["absent"]:
        hold_reasons.append("evidence not presented: %s" % ", ".join(coverage["absent"]))
    if coverage["unsupported_references"]:
        hold_reasons.append(
            "item(s) claimed by reference with no data pack named: %s"
            % ", ".join(coverage["unsupported_references"])
        )
    if gap < 0:
        hold_reasons.append(
            "buy-off precedes the close of the lot conformance review by %d day(s)" % (-gap)
        )
    if grouped["open_major"]:
        hold_reasons.append("open major finding(s): %s" % ", ".join(grouped["open_major"]))
    if grouped["minor_over_allowance"]:
        hold_reasons.append(
            "%d open minor findings exceed the lot-scaled allowance of %d"
            % (len(grouped["open_minor"]), allowance)
        )

    advisories = []
    if coverage["referenced"]:
        advisories.append(
            "carried by data pack reference rather than seen: %s"
            % ", ".join(coverage["referenced"])
        )

    if escalation_reasons:
        disposition = "escalate-to-witnessed-buy-off"
    elif hold_reasons:
        disposition = "hold-at-source"
    else:
        disposition = "release-for-delivery"
    return {
        "lot_id": lot_id.strip(),
        "delegation": delegation,
        "coverage": coverage,
        "gap_days": gap,
        "minor_allowance": allowance,
        "findings": grouped,
        "escalation_reasons": escalation_reasons,
        "hold_reasons": hold_reasons,
        "advisories": advisories,
        "released": disposition == "release-for-delivery",
        "disposition": disposition,
    }

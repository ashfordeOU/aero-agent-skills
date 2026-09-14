"""Source buy-off inspection readiness for a highest-assurance commercial lot.

Anchor: ECSS-Q-ST-60-13C clause 4.3.6 (final inspection carried out at the
manufacturer's premises before a lot of the highest assurance category is
released for shipment). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the inspection event itself: a named inspector, a qualification
   that is still current on the day of the inspection, and independence from
   the production organisation that built the lot.
2. Check the mandatory evidence pack is on the table -- traceability records,
   the lot acceptance report, the screening report, the packaging and marking
   evidence and the certificate of conformity. A missing mandatory item is a
   hold, not a percentage.
3. Check the sequence: a buy-off dated before the lot acceptance testing
   finished inspected something the test had not yet judged.
4. Sort the open nonconformances by severity. An open major holds the lot; an
   approved waiver closes one only when it carries a waiver reference; minors
   are tolerated up to a declared allowance.
5. Authorise shipment only when every gate holds, and report a readiness
   advisory when the optional evidence is thin even though shipment is
   authorised.
"""

import datetime
import math

__all__ = [
    "REQUIRED_EVIDENCE",
    "DEFAULT_MINOR_ALLOWANCE",
    "SEVERITIES",
    "STATUSES",
    "normalize_evidence",
    "missing_evidence",
    "evidence_completeness",
    "categorize_nonconformances",
    "validate_inspector",
    "parse_inspection_date",
    "validate_sequence",
    "assess_buy_off",
]

# The evidence a source buy-off of the highest assurance category cannot be
# carried out without. Each is a document or an observation the inspector makes
# at the manufacturer, before the lot leaves.
REQUIRED_EVIDENCE = (
    "traceability-records",
    "lot-acceptance-report",
    "screening-report",
    "esd-packaging",
    "part-marking",
    "certificate-of-conformity",
)

# Open minor nonconformances tolerated before the lot is held at source.
DEFAULT_MINOR_ALLOWANCE = 2

SEVERITIES = ("major", "minor")
STATUSES = ("open", "closed", "waived")

# An authorised shipment whose optional evidence sits at or below this share of
# what was offered is reported as thin, without blocking the shipment.
THIN_EVIDENCE_FRACTION = 0.5


def normalize_evidence(evidence):
    """Return the evidence pack as an ordered mapping of item name to presence."""
    if isinstance(evidence, (list, tuple, set, frozenset)):
        evidence = {str(item): True for item in evidence}
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping or a sequence of item names")
    normalized = {}
    for key, value in evidence.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("evidence item names must be non-empty strings, got %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError(
                "evidence['%s'] must be True or False, got %r" % (key.strip(), value)
            )
        normalized[key.strip().lower()] = value
    return normalized


def missing_evidence(evidence, required=REQUIRED_EVIDENCE):
    """Return the mandatory evidence items absent or marked not-seen."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of item names")
    pack = normalize_evidence(evidence)
    absent = []
    for item in required:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("required item names must be non-empty strings")
        key = item.strip().lower()
        if not pack.get(key, False):
            absent.append(key)
    return absent


def evidence_completeness(evidence, required=REQUIRED_EVIDENCE):
    """Return the share of mandatory evidence items actually seen, in 0..1."""
    absent = missing_evidence(evidence, required)
    total = len(required)
    return (total - len(absent)) / total


def categorize_nonconformances(items, minor_allowance=DEFAULT_MINOR_ALLOWANCE):
    """Group the lot's nonconformances by severity and open/closed state.

    Each item is a mapping with an id, a severity in SEVERITIES and a status in
    STATUSES; a waived item must carry the reference of the approved waiver.
    """
    if not isinstance(minor_allowance, int) or isinstance(minor_allowance, bool):
        raise ValueError("minor_allowance must be an integer")
    if minor_allowance < 0:
        raise ValueError("minor_allowance must be non-negative, got %d" % minor_allowance)
    if items is None:
        items = []
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence of nonconformance mappings")
    open_major = []
    open_minor = []
    waived = []
    closed = []
    seen_ids = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        for key in ("id", "severity", "status"):
            if key not in item:
                raise ValueError("items[%d] missing required key '%s'" % (index, key))
        ident = item["id"]
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError("items[%d] id must be a non-empty string" % index)
        ident = ident.strip()
        if ident in seen_ids:
            raise ValueError("nonconformance id '%s' appears more than once" % ident)
        seen_ids.add(ident)
        severity = item["severity"]
        if not isinstance(severity, str) or severity.strip().lower() not in SEVERITIES:
            raise ValueError(
                "items[%d] severity must be one of %s, got %r" % (index, SEVERITIES, severity)
            )
        severity = severity.strip().lower()
        status = item["status"]
        if not isinstance(status, str) or status.strip().lower() not in STATUSES:
            raise ValueError(
                "items[%d] status must be one of %s, got %r" % (index, STATUSES, status)
            )
        status = status.strip().lower()
        if status == "waived":
            reference = item.get("waiver_ref")
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError(
                    "nonconformance '%s' is waived without an approved waiver reference" % ident
                )
            waived.append(ident)
        elif status == "closed":
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
        "minor_allowance": minor_allowance,
        "minor_over_allowance": len(open_minor) > minor_allowance,
        "blocking": bool(open_major) or len(open_minor) > minor_allowance,
    }


def parse_inspection_date(value, label="date"):
    """Return an ISO yyyy-mm-dd string parsed into a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, value))


def validate_inspector(inspector, inspection_date):
    """Return the validated inspector record for the buy-off.

    inspector keys: name, organisation, qualification_expiry (ISO date) and
    optional produced_the_lot flag marking a non-independent inspector.
    """
    if not isinstance(inspector, dict):
        raise ValueError("inspector must be a mapping")
    for key in ("name", "organisation", "qualification_expiry"):
        if key not in inspector:
            raise ValueError("inspector missing required key '%s'" % key)
    name = inspector["name"]
    organisation = inspector["organisation"]
    for label, value in (("name", name), ("organisation", organisation)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("inspector %s must be a non-empty string" % label)
    when = parse_inspection_date(inspection_date, "inspection_date")
    expiry = parse_inspection_date(inspector["qualification_expiry"], "qualification_expiry")
    produced = inspector.get("produced_the_lot", False)
    if not isinstance(produced, bool):
        raise ValueError("inspector produced_the_lot must be True or False")
    return {
        "name": name.strip(),
        "organisation": organisation.strip(),
        "qualification_expiry": expiry.isoformat(),
        "qualification_current": expiry >= when,
        "independent": not produced,
    }


def validate_sequence(lot_acceptance_completed, inspection_date):
    """Return the day gap between lot acceptance completion and the buy-off."""
    completed = parse_inspection_date(lot_acceptance_completed, "lot_acceptance_completed")
    when = parse_inspection_date(inspection_date, "inspection_date")
    return (when - completed).days


def assess_buy_off(spec):
    """Run the full clause 4.3.6 source buy-off readiness assessment.

    spec keys: lot_id, inspection_date, lot_acceptance_completed, inspector,
    evidence, optional nonconformances, minor_allowance and optional_evidence.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_id", "inspection_date", "lot_acceptance_completed", "inspector", "evidence"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_id = spec["lot_id"]
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string")
    inspector = validate_inspector(spec["inspector"], spec["inspection_date"])
    gap_days = validate_sequence(spec["lot_acceptance_completed"], spec["inspection_date"])
    absent = missing_evidence(spec["evidence"])
    completeness = evidence_completeness(spec["evidence"])
    nonconformances = categorize_nonconformances(
        spec.get("nonconformances"), spec.get("minor_allowance", DEFAULT_MINOR_ALLOWANCE)
    )
    findings = []
    if absent:
        findings.append("mandatory evidence not presented: %s" % ", ".join(absent))
    if not inspector["qualification_current"]:
        findings.append(
            "inspector qualification expired on %s, before the buy-off"
            % inspector["qualification_expiry"]
        )
    if not inspector["independent"]:
        findings.append(
            "inspector '%s' produced the lot; the buy-off needs an independent witness"
            % inspector["name"]
        )
    if gap_days < 0:
        findings.append(
            "buy-off precedes the end of lot acceptance testing by %d day(s)" % (-gap_days)
        )
    if nonconformances["open_major"]:
        findings.append(
            "open major nonconformance(s): %s" % ", ".join(nonconformances["open_major"])
        )
    if nonconformances["minor_over_allowance"]:
        findings.append(
            "%d open minor nonconformances exceed the allowance of %d"
            % (len(nonconformances["open_minor"]), nonconformances["minor_allowance"])
        )
    optional = spec.get("optional_evidence")
    optional_share = None
    if optional is not None:
        offered = normalize_evidence(optional)
        if not offered:
            raise ValueError("optional_evidence, when supplied, must name at least one item")
        seen = sum(1 for value in offered.values() if value)
        optional_share = seen / len(offered)
        if optional_share < THIN_EVIDENCE_FRACTION or math.isclose(
            optional_share, THIN_EVIDENCE_FRACTION, rel_tol=0.0, abs_tol=1e-12
        ):
            findings.append(
                "optional evidence thin: %d of %d items seen" % (seen, len(offered))
            )
    authorised = (
        not absent
        and inspector["qualification_current"]
        and inspector["independent"]
        and gap_days >= 0
        and not nonconformances["blocking"]
    )
    return {
        "lot_id": lot_id.strip(),
        "inspector": inspector,
        "gap_days": gap_days,
        "missing_evidence": absent,
        "evidence_completeness": completeness,
        "optional_evidence_share": optional_share,
        "nonconformances": nonconformances,
        "authorised": authorised,
        "disposition": "authorize-shipment" if authorised else "hold-at-source",
        "findings": findings,
    }

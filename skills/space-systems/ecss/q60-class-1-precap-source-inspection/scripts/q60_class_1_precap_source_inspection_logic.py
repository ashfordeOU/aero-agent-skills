"""Pre-cap source inspection assessment for Class 1 production lots.

Anchor: ECSS-Q-ST-60C clause 4.3.4 — the witnessed inspection carried out at
the manufacturer before the package is sealed, covering the Class 1
production lots of an order. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Place the witness point in the manufacturing flow. The inspection has to
   sit before the seal operation: once the package is closed the cavity
   cannot be seen again without destroying the device.
2. Report any assembly or rework step sitting between the witnessed
   inspection and the seal. Anything built into the package after the witness
   left was never witnessed, whatever the flow calls the step.
3. Validate the witness. A source inspection is witnessed by somebody
   independent of the manufacturer; the manufacturer's own inspector
   repeating an in-house check is not the same event.
4. Compute the notice actually given, in working days and excluding declared
   non-working days, and compare it with the notice the order requires. A
   witness point nobody could reach is a witness point that did not happen.
5. Size the sample each lot owes from its device count, taking the larger of
   a percentage and a floor, and report a lot inspected below it.
6. Reconcile the lots of the order against the lots inspected, admitting a
   lot sealed without a witness only where a nonconformance carries both a
   reference and an agreed alternative route.
7. Report the per-lot records, the witnessed fraction and a verdict carrying
   every finding.
"""

import datetime
import math

__all__ = [
    "WORKING_WEEKDAYS",
    "RESTRICTED_BETWEEN_INSPECTION_AND_SEAL",
    "SAMPLE_TOLERANCE",
    "normalize_token",
    "parse_iso_date",
    "working_days_between",
    "required_sample_size",
    "sequence_findings",
    "witness_findings",
    "notice_findings",
    "assess_lot_inspection",
    "assess_precap_campaign",
]

# Monday through Friday count as working days.
WORKING_WEEKDAYS = (0, 1, 2, 3, 4)

# Steps that may not sit between the witnessed inspection and the seal: each
# one changes what is inside the package after the witness has signed.
RESTRICTED_BETWEEN_INSPECTION_AND_SEAL = (
    "die-attach",
    "wire-bond",
    "rework",
    "die-replacement",
    "internal-cleaning",
)

# Sample sizes come from a percentage of a device count; a product landing on
# a whole number must not be rounded up on representation alone.
SAMPLE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _require_count(value, label):
    """Return a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def parse_iso_date(value, label):
    """Return a date parsed from an ISO calendar string, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got '%s'" % (label, text))


def working_days_between(start, end, non_working_days=()):
    """Return the working days in the half-open span from start up to end."""
    first = parse_iso_date(start, "notification date")
    last = parse_iso_date(end, "inspection date")
    if last < first:
        raise ValueError(
            "inspection date %s precedes the notification date %s"
            % (last.isoformat(), first.isoformat())
        )
    if not isinstance(non_working_days, (list, tuple, set, frozenset)):
        raise ValueError("non_working_days must be a collection of calendar dates")
    excluded = set(
        parse_iso_date(day, "non_working_days entry") for day in non_working_days
    )
    count = 0
    day = first
    while day < last:
        if day.weekday() in WORKING_WEEKDAYS and day not in excluded:
            count += 1
        day += datetime.timedelta(days=1)
    return count


def required_sample_size(devices_in_lot, sample_percent, minimum_devices):
    """Return the devices a lot owes to the witnessed inspection."""
    lot = _require_count(devices_in_lot, "devices_in_lot")
    if lot < 1:
        raise ValueError("devices_in_lot must be at least 1")
    if not isinstance(sample_percent, (int, float)) or isinstance(sample_percent, bool):
        raise ValueError("sample_percent must be a real number, got %r" % (sample_percent,))
    percent = float(sample_percent)
    if not 0.0 <= percent <= 100.0:
        raise ValueError("sample_percent must lie in 0..100, got %g" % percent)
    floor = _require_count(minimum_devices, "minimum_devices")
    proportional = math.ceil(lot * percent / 100.0 - SAMPLE_TOLERANCE)
    return min(lot, max(floor, int(proportional)))


def sequence_findings(flow, inspection_step, seal_step):
    """Return the findings raised by where the witness point sits in the flow."""
    if not isinstance(flow, (list, tuple)) or not flow:
        raise ValueError("flow must be a non-empty sequence of manufacturing steps")
    steps = []
    for index, value in enumerate(flow):
        token = normalize_token(value, "flow[%d]" % index)
        if token in steps:
            raise ValueError("step '%s' appears twice in the flow" % token)
        steps.append(token)

    inspection = normalize_token(inspection_step, "inspection step")
    seal = normalize_token(seal_step, "seal step")
    if inspection not in steps:
        raise ValueError("inspection step '%s' is not in the flow" % inspection)
    if seal not in steps:
        raise ValueError("seal step '%s' is not in the flow" % seal)

    findings = []
    at = steps.index(inspection)
    closed = steps.index(seal)
    if at > closed:
        findings.append(
            "the witnessed inspection '%s' is scheduled after the seal '%s'; the cavity "
            "cannot be seen once closed" % (inspection, seal)
        )
        return findings
    if at == closed:
        findings.append(
            "the witnessed inspection and the seal are the same step '%s'" % seal
        )
        return findings
    for token in steps[at + 1:closed]:
        if token in RESTRICTED_BETWEEN_INSPECTION_AND_SEAL:
            findings.append(
                "step '%s' runs between the witnessed inspection and the seal, so what "
                "it changed was never witnessed" % token
            )
    return findings


def witness_findings(witness):
    """Return the findings raised by who witnessed the inspection."""
    if not isinstance(witness, dict):
        raise ValueError("witness must be a mapping")
    for key in ("name", "organisation", "independent_of_manufacturer"):
        if key not in witness:
            raise ValueError("witness missing required key '%s'" % key)
    name = _require_text(witness["name"], "witness name")
    organisation = _require_text(witness["organisation"], "witness organisation")
    independent = witness["independent_of_manufacturer"]
    if not isinstance(independent, bool):
        raise ValueError("independent_of_manufacturer must be a boolean")
    findings = []
    if not independent:
        findings.append(
            "witness '%s' of '%s' is not independent of the manufacturer, so the "
            "inspection is an in-house check" % (name, organisation)
        )
    return findings


def notice_findings(notification_date, inspection_date, required_days, non_working_days=()):
    """Return the notice actually given and any shortfall against the requirement."""
    required = _require_count(required_days, "required notice days")
    given = working_days_between(notification_date, inspection_date, non_working_days)
    findings = []
    if given < required:
        findings.append(
            "the manufacturer gave %d working days of notice, short of the %d required"
            % (given, required)
        )
    return {"working_days_given": given, "working_days_required": required, "findings": findings}


def assess_lot_inspection(lot, policy):
    """Return one production-lot record carrying its findings."""
    if not isinstance(lot, dict):
        raise ValueError("each lot must be a mapping")
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in ("sample_percent", "minimum_devices", "required_notice_days"):
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    if "lot_id" not in lot:
        raise ValueError("lot missing required key 'lot_id'")
    lot_id = _require_text(lot["lot_id"], "lot_id")

    waiver = lot.get("nonconformance")
    if lot.get("witnessed", True) is False or waiver is not None:
        findings = []
        if not isinstance(waiver, dict):
            findings.append(
                "lot '%s' was sealed with no witnessed pre-cap inspection and no "
                "nonconformance" % lot_id
            )
        else:
            reference = (waiver.get("reference") or "").strip()
            alternative = (waiver.get("alternative_route") or "").strip()
            if not reference:
                findings.append(
                    "lot '%s' is waived without a nonconformance reference" % lot_id
                )
            if not alternative:
                findings.append(
                    "lot '%s' is waived without an agreed alternative route" % lot_id
                )
        return {
            "lot_id": lot_id,
            "witnessed": False,
            "devices_in_lot": None,
            "required_sample": None,
            "devices_inspected": None,
            "notice": None,
            "findings": findings,
            "acceptable": not findings,
        }

    for key in (
        "devices_in_lot",
        "devices_inspected",
        "flow",
        "inspection_step",
        "seal_step",
        "witness",
        "notification_date",
        "inspection_date",
    ):
        if key not in lot:
            raise ValueError("lot '%s' missing required key '%s'" % (lot_id, key))

    devices_in_lot = _require_count(lot["devices_in_lot"], "devices_in_lot")
    if devices_in_lot < 1:
        raise ValueError("lot '%s' must carry at least one device" % lot_id)
    inspected = _require_count(lot["devices_inspected"], "devices_inspected")
    if inspected > devices_in_lot:
        raise ValueError(
            "lot '%s' inspected %d of %d devices" % (lot_id, inspected, devices_in_lot)
        )

    findings = []
    findings.extend(sequence_findings(lot["flow"], lot["inspection_step"], lot["seal_step"]))
    findings.extend(witness_findings(lot["witness"]))

    notice = notice_findings(
        lot["notification_date"],
        lot["inspection_date"],
        policy["required_notice_days"],
        policy.get("non_working_days", ()),
    )
    findings.extend(notice["findings"])

    owed = required_sample_size(
        devices_in_lot, policy["sample_percent"], policy["minimum_devices"]
    )
    if inspected < owed:
        findings.append(
            "lot '%s' witnessed %d devices, short of the %d its size owes"
            % (lot_id, inspected, owed)
        )

    return {
        "lot_id": lot_id,
        "witnessed": True,
        "devices_in_lot": devices_in_lot,
        "required_sample": owed,
        "devices_inspected": inspected,
        "notice": notice,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_precap_campaign(campaign):
    """Run the full clause 4.3.4 pre-cap source inspection assessment.

    campaign keys: order_reference, policy, ordered_lot_ids, lots.
    """
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    for key in ("order_reference", "policy", "ordered_lot_ids", "lots"):
        if key not in campaign:
            raise ValueError("campaign missing required key '%s'" % key)

    order_reference = _require_text(campaign["order_reference"], "order_reference")
    ordered = campaign["ordered_lot_ids"]
    if not isinstance(ordered, (list, tuple)) or not ordered:
        raise ValueError("ordered_lot_ids must be a non-empty sequence")
    ordered_ids = []
    for index, value in enumerate(ordered):
        lot_id = _require_text(value, "ordered_lot_ids[%d]" % index)
        if lot_id in ordered_ids:
            raise ValueError("production lot '%s' is listed twice on the order" % lot_id)
        ordered_ids.append(lot_id)

    lots = campaign["lots"]
    if not isinstance(lots, (list, tuple)):
        raise ValueError("lots must be a sequence")

    records = []
    reported = []
    for lot in lots:
        record = assess_lot_inspection(lot, campaign["policy"])
        if record["lot_id"] in reported:
            raise ValueError("production lot '%s' is reported twice" % record["lot_id"])
        reported.append(record["lot_id"])
        records.append(record)

    findings = []
    unreported = [l for l in ordered_ids if l not in reported]
    for lot_id in unreported:
        findings.append(
            "production lot '%s' on the order has no pre-cap inspection record" % lot_id
        )
    surplus = [l for l in reported if l not in ordered_ids]
    for lot_id in surplus:
        findings.append(
            "inspection record '%s' names a production lot the order does not carry" % lot_id
        )
    for record in records:
        findings.extend(record["findings"])

    witnessed = [r["lot_id"] for r in records if r["witnessed"] and r["acceptable"]]
    return {
        "order_reference": order_reference,
        "ordered_lot_ids": ordered_ids,
        "lots": records,
        "unreported_lots": unreported,
        "surplus_records": surplus,
        "witnessed_fraction": len(witnessed) / float(len(ordered_ids)),
        "campaign_complete": not findings,
        "findings": findings,
    }

"""Recalibration currency of the antennas, probes and sensors of an EMC chain.

Anchor: ECSS-E-ST-20-07C clause 5.2.11.1 (measurement devices are recalibrated
at least every two years, and again whenever the device has been damaged).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalize each device record: identifier, device kind (antenna, probe or
   sensor), date of its last calibration, any dates on which it was damaged,
   and an optional house interval no longer than the biennial maximum.
2. Take the interval anniversary of the last calibration as the ordinary end
   of validity, honouring month lengths so a leap-day calibration lands on a
   real date.
3. Bring that end of validity forward to the day before the earliest damage
   that happened on or after the last calibration: a damaged device stops
   being usable at the damage, not at the anniversary.
4. Grade the device against the reference date and, when a measurement window
   is declared, against the end of that window, so a device whose validity
   lapses part way through a campaign is caught before the run.
5. Aggregate the inventory: the ordered recalibration schedule, the conforming
   fraction and one finding per device that cannot cover the window.
"""

import calendar
import datetime

__all__ = [
    "MAX_INTERVAL_MONTHS",
    "DEVICE_KINDS",
    "STATUS_CURRENT",
    "STATUS_DUE_WITHIN_CAMPAIGN",
    "STATUS_EXPIRED",
    "STATUS_DAMAGE_INVALIDATED",
    "parse_date",
    "add_months",
    "validate_interval_months",
    "interval_valid_until",
    "damage_valid_until",
    "effective_validity",
    "normalize_device",
    "assess_device",
    "recalibration_schedule",
    "assess_inventory",
]

# The clause fixes a two-year ceiling on the recalibration interval. A house
# policy may be tighter; it may never be looser, so a declared interval above
# this ceiling is an input error rather than a finding.
MAX_INTERVAL_MONTHS = 24

# Only the device families the clause governs are graded here; anything else
# in the laboratory inventory belongs to a different rule.
DEVICE_KINDS = ("antenna", "probe", "sensor")

STATUS_CURRENT = "current"
STATUS_DUE_WITHIN_CAMPAIGN = "due-within-campaign"
STATUS_EXPIRED = "expired"
STATUS_DAMAGE_INVALIDATED = "damage-invalidated"

_DEVICE_KEYS = ("id", "kind", "last_calibration", "damage_events", "interval_months")


def parse_date(value, label="date"):
    """Return a calendar date from a date object or an ISO 'YYYY-MM-DD' string."""
    if isinstance(value, datetime.datetime):
        raise ValueError("%s must be a calendar date, not a timestamp" % label)
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("%s must not be blank" % label)
        try:
            parsed = datetime.date.fromisoformat(text)
        except ValueError:
            raise ValueError("%s must be an ISO calendar date, got %r" % (label, value))
        return parsed
    raise ValueError("%s must be a date or an ISO date string, got %r" % (label, value))


def add_months(day, months):
    """Return the date months after day, clamped to the length of that month."""
    if not isinstance(day, datetime.date) or isinstance(day, datetime.datetime):
        raise ValueError("day must be a calendar date")
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer")
    total = day.year * 12 + (day.month - 1) + months
    year, index = divmod(total, 12)
    month = index + 1
    if year < datetime.MINYEAR or year > datetime.MAXYEAR:
        raise ValueError("shifting %s by %d months leaves the calendar" % (day, months))
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day.day, last_day))


def validate_interval_months(months):
    """Return the recalibration interval in months, refusing a looser one."""
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("interval_months must be an integer number of months")
    if months <= 0:
        raise ValueError("interval_months must be positive, got %d" % months)
    if months > MAX_INTERVAL_MONTHS:
        raise ValueError(
            "interval_months %d exceeds the %d-month ceiling; a looser interval "
            "is not a finding, it is an invalid policy" % (months, MAX_INTERVAL_MONTHS)
        )
    return months


def interval_valid_until(last_calibration, interval_months=MAX_INTERVAL_MONTHS):
    """Return the last date the ordinary interval keeps the device usable."""
    day = parse_date(last_calibration, "last_calibration")
    return add_months(day, validate_interval_months(interval_months))


def damage_valid_until(last_calibration, damage_events, reference_date=None):
    """Return the last usable date imposed by damage, or None when undamaged.

    Damage before the last calibration is superseded by that calibration.
    Damage on or after it stops the device on the damage date itself, so the
    last usable date is the day before.
    """
    calibrated = parse_date(last_calibration, "last_calibration")
    if damage_events is None:
        return None
    if isinstance(damage_events, (str, bytes)) or not isinstance(damage_events, (list, tuple)):
        raise ValueError("damage_events must be a sequence of dates")
    relevant = []
    for index, item in enumerate(damage_events):
        day = parse_date(item, "damage_events[%d]" % index)
        if reference_date is not None and day > reference_date:
            raise ValueError(
                "damage_events[%d] %s is later than the reference date %s"
                % (index, day, reference_date)
            )
        if day >= calibrated:
            relevant.append(day)
    if not relevant:
        return None
    return min(relevant) - datetime.timedelta(days=1)


def effective_validity(last_calibration, damage_events=None,
                       interval_months=MAX_INTERVAL_MONTHS, reference_date=None):
    """Return (last usable date, driver) where driver is 'interval' or 'damage'."""
    by_interval = interval_valid_until(last_calibration, interval_months)
    by_damage = damage_valid_until(last_calibration, damage_events, reference_date)
    if by_damage is not None and by_damage <= by_interval:
        return (by_damage, "damage")
    return (by_interval, "interval")


def normalize_device(device):
    """Return a validated device record."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    unknown = sorted(set(device) - set(_DEVICE_KEYS))
    if unknown:
        raise ValueError("unknown device key(s): %s" % ", ".join(unknown))
    for key in ("id", "kind", "last_calibration"):
        if key not in device:
            raise ValueError("device missing required key '%s'" % key)
    identifier = device["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("device id must be a non-blank string")
    kind = device["kind"]
    if not isinstance(kind, str) or kind.strip().lower() not in DEVICE_KINDS:
        raise ValueError(
            "device kind must be one of %s, got %r" % (", ".join(DEVICE_KINDS), kind)
        )
    interval = device.get("interval_months", MAX_INTERVAL_MONTHS)
    return {
        "id": identifier.strip(),
        "kind": kind.strip().lower(),
        "last_calibration": parse_date(device["last_calibration"], "last_calibration"),
        "damage_events": list(device.get("damage_events") or []),
        "interval_months": validate_interval_months(interval),
    }


def assess_device(device, reference_date, campaign_end=None):
    """Grade one device against the reference date and the measurement window."""
    record = normalize_device(device)
    today = parse_date(reference_date, "reference_date")
    if record["last_calibration"] > today:
        raise ValueError(
            "last_calibration %s is later than the reference date %s"
            % (record["last_calibration"], today)
        )
    window_end = None
    if campaign_end is not None:
        window_end = parse_date(campaign_end, "campaign_end")
        if window_end < today:
            raise ValueError(
                "campaign_end %s precedes the reference date %s" % (window_end, today)
            )
    valid_until, driver = effective_validity(
        record["last_calibration"],
        record["damage_events"],
        record["interval_months"],
        today,
    )
    if today > valid_until:
        status = STATUS_DAMAGE_INVALIDATED if driver == "damage" else STATUS_EXPIRED
    elif window_end is not None and window_end > valid_until:
        status = STATUS_DUE_WITHIN_CAMPAIGN
    else:
        status = STATUS_CURRENT
    return {
        "id": record["id"],
        "kind": record["kind"],
        "last_calibration": record["last_calibration"],
        "interval_months": record["interval_months"],
        "valid_until": valid_until,
        "driver": driver,
        "status": status,
        "days_remaining": (valid_until - today).days,
        "covers_campaign": window_end is None or window_end <= valid_until,
    }


def recalibration_schedule(devices, reference_date, campaign_end=None):
    """Return the device gradings ordered by the date each one falls due."""
    if isinstance(devices, dict) or not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must be a non-empty sequence of device records")
    gradings = [assess_device(item, reference_date, campaign_end) for item in devices]
    seen = set()
    for grading in gradings:
        if grading["id"] in seen:
            raise ValueError("duplicate device id %r in the inventory" % grading["id"])
        seen.add(grading["id"])
    return sorted(gradings, key=lambda g: (g["valid_until"], g["id"]))


def assess_inventory(spec):
    """Run the full clause 5.2.11.1 inventory assessment.

    spec keys: devices, reference_date, optional campaign_end.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("devices", "reference_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    gradings = recalibration_schedule(
        spec["devices"], spec["reference_date"], spec.get("campaign_end")
    )
    findings = []
    for grading in gradings:
        if grading["status"] == STATUS_DAMAGE_INVALIDATED:
            findings.append(
                "%s (%s) was damaged after its last calibration and may not be used "
                "until it is recalibrated" % (grading["id"], grading["kind"])
            )
        elif grading["status"] == STATUS_EXPIRED:
            findings.append(
                "%s (%s) passed its recalibration due date %s"
                % (grading["id"], grading["kind"], grading["valid_until"])
            )
        elif grading["status"] == STATUS_DUE_WITHIN_CAMPAIGN:
            findings.append(
                "%s (%s) falls due on %s, inside the declared measurement window"
                % (grading["id"], grading["kind"], grading["valid_until"])
            )
    conforming = [g for g in gradings if g["status"] == STATUS_CURRENT]
    return {
        "schedule": gradings,
        "device_count": len(gradings),
        "conforming_count": len(conforming),
        "conforming_fraction": len(conforming) / float(len(gradings)),
        "next_due": gradings[0],
        "findings": findings,
        "compliant": not findings,
    }

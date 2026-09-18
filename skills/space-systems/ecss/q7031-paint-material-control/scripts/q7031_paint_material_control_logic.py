"""Batch control of a paint material: traceability, shelf life, storage, outgassing.

Anchor: ECSS-Q-ST-70-31C materials clause -- the control a paint, primer or
hardener batch is under from receipt to the moment it is mixed, and the
outgassing evidence it has to carry (the screening limits are the vacuum
outgassing ones of ECSS-Q-ST-70-02C). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the batch record carries every traceability item; a batch that cannot
   be traced is not a shelf-life question, it is an unusable batch.
2. Convert the manufacture date and the declared shelf life into an expiry
   date, and return the days remaining at the intended use date.
3. Convert the logged storage excursions above the declared storage ceiling
   into a shelf-life penalty in days, so hot storage shortens the usable life
   instead of being recorded and ignored.
4. Screen the declared outgassing figures against the vacuum-outgassing
   screening limits, reporting each metric separately.
5. Close with one disposition -- release, retest or reject -- and the findings
   that produced it.
"""

import datetime
import math

__all__ = [
    "TML_LIMIT_PCT",
    "CVCM_LIMIT_PCT",
    "RML_LIMIT_PCT",
    "OUTGASSING_TOLERANCE_PCT",
    "REQUIRED_TRACEABILITY",
    "EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR",
    "RETEST_WINDOW_DAYS",
    "DISPOSITIONS",
    "parse_date",
    "add_months",
    "expiry_date",
    "excursion_penalty_days",
    "shelf_life_remaining_days",
    "missing_traceability",
    "screen_outgassing",
    "assess_batch",
]

# Vacuum outgassing screening limits, in percent.
TML_LIMIT_PCT = 1.00
CVCM_LIMIT_PCT = 0.10
RML_LIMIT_PCT = 1.00

# Outgassing figures are reported to two decimals but arrive as floats; a value
# that should sit exactly on a limit can land a few ULPs above it.
OUTGASSING_TOLERANCE_PCT = 1e-9

REQUIRED_TRACEABILITY = (
    "batch-number",
    "manufacture-date",
    "certificate-of-conformity",
    "outgassing-data-reference",
    "storage-temperature-record",
)

# Each kelvin-hour above the declared storage ceiling costs this much shelf life.
EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR = 0.02

# An expired but unopened batch may be re-qualified by retest inside this window.
RETEST_WINDOW_DAYS = 90

DISPOSITIONS = ("release", "retest", "reject")


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def parse_date(value):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str):
        raise ValueError("date must be an ISO string or a date, got %r" % (value,))
    text = value.strip()
    if not text:
        raise ValueError("date must not be empty")
    try:
        parts = [int(p) for p in text.split("-")]
    except ValueError:
        raise ValueError("date '%s' is not ISO yyyy-mm-dd" % text)
    if len(parts) != 3:
        raise ValueError("date '%s' is not ISO yyyy-mm-dd" % text)
    try:
        return datetime.date(parts[0], parts[1], parts[2])
    except ValueError as exc:
        raise ValueError("date '%s' is not a real calendar date (%s)" % (text, exc))


def add_months(start, months):
    """Return the date `months` calendar months after `start`, clamped in-month."""
    base = parse_date(start)
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    if months < 0:
        raise ValueError("months must be non-negative, got %d" % months)
    total = base.month - 1 + months
    year = base.year + total // 12
    month = total % 12 + 1
    day = base.day
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1
            if day < 1:
                raise ValueError("cannot place day of month for %d-%02d" % (year, month))


def expiry_date(manufacture_date, shelf_life_months):
    """Return the nominal expiry date of a batch."""
    return add_months(manufacture_date, shelf_life_months)


def excursion_penalty_days(excursions, storage_ceiling_c):
    """Return the shelf-life penalty owed by logged over-temperature storage."""
    if not isinstance(storage_ceiling_c, (int, float)) or isinstance(storage_ceiling_c, bool):
        raise ValueError("storage_ceiling_c must be a real number")
    ceiling = float(storage_ceiling_c)
    if not math.isfinite(ceiling):
        raise ValueError("storage_ceiling_c must be finite")
    if excursions is None:
        return 0.0
    if not isinstance(excursions, (list, tuple)):
        raise ValueError("excursions must be a sequence of mappings")
    penalty = 0.0
    for i, entry in enumerate(excursions):
        if not isinstance(entry, dict):
            raise ValueError("excursions[%d] must be a mapping" % i)
        for key in ("temperature_c", "duration_h"):
            if key not in entry:
                raise ValueError("excursions[%d] missing '%s'" % (i, key))
        temp = entry["temperature_c"]
        if not isinstance(temp, (int, float)) or isinstance(temp, bool):
            raise ValueError("excursions[%d] temperature_c must be a real number" % i)
        temp = float(temp)
        if not math.isfinite(temp):
            raise ValueError("excursions[%d] temperature_c must be finite" % i)
        hours = _non_negative(entry["duration_h"], "excursions[%d] duration_h" % i)
        over = temp - ceiling
        if over > 0.0:
            penalty += over * hours * EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR
    return penalty


def shelf_life_remaining_days(manufacture_date, shelf_life_months, use_date,
                              excursions=None, storage_ceiling_c=25.0):
    """Return the shelf-life days left at the use date, after storage penalty."""
    expiry = expiry_date(manufacture_date, shelf_life_months)
    use = parse_date(use_date)
    made = parse_date(manufacture_date)
    if use < made:
        raise ValueError("use date %s precedes manufacture date %s" % (use, made))
    gross = (expiry - use).days
    return gross - excursion_penalty_days(excursions, storage_ceiling_c)


def missing_traceability(record):
    """Return the required traceability items the batch record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = []
    for item in REQUIRED_TRACEABILITY:
        value = record.get(item)
        if value is None:
            missing.append(item)
        elif isinstance(value, str) and not value.strip():
            missing.append(item)
        elif isinstance(value, (list, tuple)) and not value:
            missing.append(item)
    return missing


def _at_or_under(value, limit):
    if value < limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=OUTGASSING_TOLERANCE_PCT)


def screen_outgassing(tml_pct, cvcm_pct, rml_pct=None):
    """Return the per-metric outgassing verdicts and the overall screening result."""
    tml = _non_negative(tml_pct, "tml_pct")
    cvcm = _non_negative(cvcm_pct, "cvcm_pct")
    verdicts = {
        "tml": _at_or_under(tml, TML_LIMIT_PCT),
        "cvcm": _at_or_under(cvcm, CVCM_LIMIT_PCT),
    }
    if rml_pct is not None:
        rml = _non_negative(rml_pct, "rml_pct")
        if rml > tml + OUTGASSING_TOLERANCE_PCT:
            raise ValueError(
                "recovered mass loss %g exceeds total mass loss %g" % (rml, tml)
            )
        verdicts["rml"] = _at_or_under(rml, RML_LIMIT_PCT)
    verdicts["overall"] = all(v for k, v in verdicts.items() if k != "overall")
    return verdicts


def assess_batch(record):
    """Return the control disposition for one paint-material batch."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("manufacture_date", "shelf_life_months", "use_date",
                "tml_pct", "cvcm_pct"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    missing = missing_traceability(record)
    findings = ["traceability-missing-%s" % item for item in missing]
    outgassing = screen_outgassing(
        record["tml_pct"], record["cvcm_pct"], record.get("rml_pct")
    )
    for metric in ("tml", "cvcm", "rml"):
        if metric in outgassing and not outgassing[metric]:
            findings.append("outgassing-%s-over-limit" % metric)
    remaining = shelf_life_remaining_days(
        record["manufacture_date"],
        record["shelf_life_months"],
        record["use_date"],
        record.get("storage_excursions"),
        record.get("storage_ceiling_c", 25.0),
    )
    penalty = excursion_penalty_days(
        record.get("storage_excursions"), record.get("storage_ceiling_c", 25.0)
    )
    if penalty > 0.0:
        findings.append("storage-excursion-penalty-applied")
    if remaining < 0.0:
        findings.append("shelf-life-expired")
    if missing:
        disposition = "reject"
    elif not outgassing["overall"]:
        disposition = "reject"
    elif remaining < -float(RETEST_WINDOW_DAYS):
        disposition = "reject"
    elif remaining < 0.0 or penalty > 0.0:
        disposition = "retest"
    else:
        disposition = "release"
    return {
        "disposition": disposition,
        "findings": findings,
        "remaining_days": remaining,
        "penalty_days": penalty,
        "outgassing": outgassing,
    }

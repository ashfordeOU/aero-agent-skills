"""Handling and storage control for highest-assurance commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 4.4 (electrostatic protection, storage
conditions and shelf life for parts procured at the highest assurance level).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Place the part in a human-body-model sensitivity band from its declared
   withstand voltage, and derive the electrostatic controls that band owes.
2. Compare the controls the storage area actually operates with the owed set
   and report the missing ones.
3. Grade the storage environment: the temperature and relative-humidity
   excursions of the store against the declared limits, with the boundary
   handled by a named tolerance.
4. Grade moisture exposure: the fraction of the floor life a moisture-
   sensitive part has consumed since the dry pack was opened, credited for an
   approved bake.
5. Grade shelf life: the days remaining against the declared shelf life and
   whether a solderability re-test has fallen due.
6. Rank the findings and return one storage verdict: released,
   released-with-actions, or quarantined.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "HBM_BANDS",
    "BASELINE_ESD_CONTROLS",
    "ENHANCED_ESD_CONTROLS",
    "FLOOR_LIFE_HOURS",
    "SEVERITY_ORDER",
    "hbm_sensitivity_band",
    "required_esd_controls",
    "missing_esd_controls",
    "environment_excursion",
    "floor_life_consumed",
    "shelf_life_remaining_days",
    "solderability_retest_due",
    "storage_verdict",
    "assess_handling_and_storage",
]

# Excursion and consumed-fraction comparisons are quotients and differences of
# measured values; a case sitting exactly on a limit can land a few ULP on the
# wrong side. Absorb the representation error here, never by moving the limit.
BOUND_TOLERANCE = 1e-9

# Human-body-model sensitivity bands, as (band, lower withstand volts
# inclusive, upper withstand volts exclusive). A lower withstand voltage means
# a more sensitive part and a stricter handling regime.
HBM_BANDS = (
    ("0", 0.0, 250.0),
    ("1A", 250.0, 500.0),
    ("1B", 500.0, 1000.0),
    ("1C", 1000.0, 2000.0),
    ("2", 2000.0, 4000.0),
    ("3A", 4000.0, 8000.0),
    ("3B", 8000.0, float("inf")),
)

# Controls every band owes once a part is inside the protected area.
BASELINE_ESD_CONTROLS = (
    "grounded-dissipative-worksurface",
    "personnel-grounding-wrist-strap",
    "static-shielding-storage-bag",
)

# Additional controls the most sensitive bands owe.
ENHANCED_ESD_CONTROLS = (
    "protected-area-ionizer",
    "continuous-wrist-strap-monitoring",
    "protected-area-entry-log",
)

ENHANCED_BANDS = ("0", "1A")

# Floor-life allowance in hours outside the dry pack, by moisture sensitivity
# level. Level 1 is unrestricted; level 6 has no floor life and is baked
# before use.
FLOOR_LIFE_HOURS = {
    "1": None,
    "2": 8760.0,
    "2A": 672.0,
    "3": 168.0,
    "4": 72.0,
    "5": 48.0,
    "5A": 24.0,
    "6": 0.0,
}

SEVERITY_ORDER = ("critical", "major", "minor")


def _require_number(value, label, allow_zero=True, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    if not allow_zero and number == 0.0:
        raise ValueError("%s must be non-zero" % label)
    return number


def _require_date(value, label):
    """Return a date parsed from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s %r is not an ISO yyyy-mm-dd date" % (label, value))
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def hbm_sensitivity_band(withstand_volts):
    """Return the human-body-model sensitivity band of a part."""
    volts = _require_number(withstand_volts, "withstand_volts")
    for band, lower, upper in HBM_BANDS:
        if lower <= volts < upper:
            return band
    raise ValueError("withstand_volts %g falls in no sensitivity band" % volts)


def required_esd_controls(band):
    """Return the sorted control set a sensitivity band owes."""
    if not isinstance(band, str):
        raise ValueError("band must be a string, got %r" % (band,))
    known = [name for name, _lo, _hi in HBM_BANDS]
    key = band.strip().upper()
    if key not in known:
        raise ValueError("band %r is not one of %r" % (band, known))
    controls = set(BASELINE_ESD_CONTROLS)
    if key in ENHANCED_BANDS:
        controls |= set(ENHANCED_ESD_CONTROLS)
    return sorted(controls)


def missing_esd_controls(band, controls_present):
    """Return the owed controls the storage area does not operate."""
    if not isinstance(controls_present, (list, tuple, set, frozenset)):
        raise ValueError("controls_present must be a sequence or set")
    present = set()
    for item in controls_present:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each control must be a non-empty string, got %r" % (item,))
        present.add(item.strip().lower())
    return [c for c in required_esd_controls(band) if c not in present]


def environment_excursion(measured, limits, label="environment"):
    """Return the signed excursion of a measured value beyond its limits.

    Zero means inside the band (an exact-limit value counts as inside, within
    the named tolerance). A positive value is the amount above the upper
    limit; a negative value is the amount below the lower limit.
    """
    value = _require_number(measured, "%s measured value" % label, allow_negative=True)
    if not isinstance(limits, (list, tuple)) or len(limits) != 2:
        raise ValueError("%s limits must be a (lower, upper) pair" % label)
    lower = _require_number(limits[0], "%s lower limit" % label, allow_negative=True)
    upper = _require_number(limits[1], "%s upper limit" % label, allow_negative=True)
    if lower > upper:
        raise ValueError("%s limits run backwards: %g > %g" % (label, lower, upper))
    if value > upper and not math.isclose(
        value, upper, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    ):
        return value - upper
    if value < lower and not math.isclose(
        value, lower, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    ):
        return value - lower
    return 0.0


def floor_life_consumed(msl_level, hours_exposed, bake_credit_hours=0.0):
    """Return the fraction of the floor life a moisture-sensitive part used.

    An unrestricted level returns 0.0. A level with no floor life returns
    positive infinity once any exposure is recorded, because the part is baked
    before use rather than rationed.
    """
    if not isinstance(msl_level, str):
        raise ValueError("msl_level must be a string, got %r" % (msl_level,))
    key = msl_level.strip().upper()
    if key not in FLOOR_LIFE_HOURS:
        raise ValueError(
            "msl_level %r is not one of %r" % (msl_level, sorted(FLOOR_LIFE_HOURS))
        )
    exposed = _require_number(hours_exposed, "hours_exposed")
    credit = _require_number(bake_credit_hours, "bake_credit_hours")
    if credit > exposed:
        raise ValueError(
            "bake credit %g h exceeds the recorded exposure %g h" % (credit, exposed)
        )
    allowance = FLOOR_LIFE_HOURS[key]
    if allowance is None:
        return 0.0
    net = exposed - credit
    if allowance == 0.0:
        return float("inf") if net > 0.0 else 0.0
    return net / allowance


def shelf_life_remaining_days(storage_start, review_date, shelf_life_days):
    """Return the days of declared shelf life left at the review date."""
    start = _require_date(storage_start, "storage_start")
    review = _require_date(review_date, "review_date")
    if review < start:
        raise ValueError("review_date %s precedes storage_start %s" % (review, start))
    if not isinstance(shelf_life_days, int) or isinstance(shelf_life_days, bool):
        raise ValueError("shelf_life_days must be an integer, got %r" % (shelf_life_days,))
    if shelf_life_days <= 0:
        raise ValueError("shelf_life_days must be positive, got %d" % shelf_life_days)
    return shelf_life_days - (review - start).days


def solderability_retest_due(storage_start, review_date, retest_interval_days,
                             last_retest=None):
    """Return True when a solderability re-test has fallen due."""
    start = _require_date(storage_start, "storage_start")
    review = _require_date(review_date, "review_date")
    if not isinstance(retest_interval_days, int) or isinstance(retest_interval_days, bool):
        raise ValueError(
            "retest_interval_days must be an integer, got %r" % (retest_interval_days,)
        )
    if retest_interval_days <= 0:
        raise ValueError(
            "retest_interval_days must be positive, got %d" % retest_interval_days
        )
    reference = start if last_retest is None else _require_date(last_retest, "last_retest")
    if reference < start:
        raise ValueError("last_retest %s precedes storage_start %s" % (reference, start))
    if review < reference:
        raise ValueError("review_date %s precedes the reference date %s" % (review, reference))
    return (review - reference).days >= retest_interval_days


def _finding(severity, topic, message):
    if severity not in SEVERITY_ORDER:
        raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
    return {"severity": severity, "topic": topic, "message": message}


def storage_verdict(findings):
    """Return the storage verdict implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must carry a severity")
        severities.add(finding["severity"])
    if "critical" in severities:
        return "quarantined"
    if severities:
        return "released-with-actions"
    return "released"


def assess_handling_and_storage(record):
    """Grade one stored class 1 lot against clause 4.4.

    record keys: withstand_volts, controls_present, temperature_c,
    temperature_limits, humidity_percent, humidity_limits, storage_start,
    review_date, shelf_life_days, retest_interval_days, optional last_retest,
    optional msl_level, hours_exposed and bake_credit_hours.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in (
        "withstand_volts",
        "controls_present",
        "temperature_c",
        "temperature_limits",
        "humidity_percent",
        "humidity_limits",
        "storage_start",
        "review_date",
        "shelf_life_days",
        "retest_interval_days",
    ):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)

    band = hbm_sensitivity_band(record["withstand_volts"])
    missing = missing_esd_controls(band, record["controls_present"])
    temperature = environment_excursion(
        record["temperature_c"], record["temperature_limits"], label="temperature"
    )
    humidity = environment_excursion(
        record["humidity_percent"], record["humidity_limits"], label="humidity"
    )
    remaining = shelf_life_remaining_days(
        record["storage_start"], record["review_date"], record["shelf_life_days"]
    )
    retest_due = solderability_retest_due(
        record["storage_start"],
        record["review_date"],
        record["retest_interval_days"],
        record.get("last_retest"),
    )
    msl_level = record.get("msl_level")
    if msl_level is None:
        consumed = 0.0
    else:
        consumed = floor_life_consumed(
            msl_level,
            record.get("hours_exposed", 0.0),
            record.get("bake_credit_hours", 0.0),
        )

    findings = []
    for control in missing:
        findings.append(
            _finding(
                "critical",
                "electrostatic-protection",
                "band %s owes %s and the store does not operate it" % (band, control),
            )
        )
    if temperature != 0.0:
        findings.append(
            _finding(
                "critical" if abs(temperature) > 5.0 else "major",
                "storage-environment",
                "store temperature sits %.2f C outside the declared band" % temperature,
            )
        )
    if humidity != 0.0:
        findings.append(
            _finding(
                "critical" if abs(humidity) > 10.0 else "major",
                "storage-environment",
                "store humidity sits %.2f percent outside the declared band" % humidity,
            )
        )
    over_floor = consumed > 1.0 and not math.isclose(
        consumed, 1.0, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    if over_floor:
        if math.isfinite(consumed):
            message = (
                "floor life consumed reads %.4f of the allowance; bake before use"
                % consumed
            )
        else:
            message = "the level carries no floor life; bake before use"
        findings.append(_finding("critical", "moisture-sensitivity", message))
    elif consumed > 0.75:
        findings.append(
            _finding(
                "minor",
                "moisture-sensitivity",
                "floor life consumed reads %.4f of the allowance" % consumed,
            )
        )
    if remaining < 0:
        findings.append(
            _finding(
                "critical",
                "shelf-life",
                "declared shelf life expired %d days before the review" % (-remaining),
            )
        )
    elif remaining == 0:
        findings.append(
            _finding("major", "shelf-life", "declared shelf life expires on the review date")
        )
    if retest_due:
        findings.append(
            _finding(
                "major",
                "shelf-life",
                "solderability re-test interval has elapsed since the reference date",
            )
        )
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["topic"]))
    verdict = storage_verdict(findings)
    return {
        "sensitivity_band": band,
        "required_controls": required_esd_controls(band),
        "missing_controls": missing,
        "temperature_excursion_c": temperature,
        "humidity_excursion_percent": humidity,
        "floor_life_consumed": consumed,
        "shelf_life_remaining_days": remaining,
        "solderability_retest_due": retest_due,
        "findings": findings,
        "verdict": verdict,
        "released": verdict == "released",
    }

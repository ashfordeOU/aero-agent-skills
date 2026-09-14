"""Protected handling and controlled storage for class 2 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 5.4 (protected handling and controlled
storage of commercial parts procured at the intermediate assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Band the part by its declared electrostatic withstand voltage and derive
   the protection measures that band owes inside a protected area.
2. Compare the measures the store operates with the owed set, crediting an
   equivalent substitute only where the substitution is recorded and
   approved, and rejecting the rest.
3. Grade the storage environment twice: the signed excursion beyond the
   declared band, and the margin fraction that says how close an inside
   reading runs to its nearest limit.
4. Count the dry-pack floor life consumed since the pack was opened, net of
   a dry-cabinet pause and of an approved bake.
5. Read the shelf-life clock and the periodic re-inspection clock, which run
   independently of one another.
6. Name every declared handler whose electrostatic qualification has lapsed
   at the review date.
7. Rank the findings and return one verdict: released,
   released-with-actions, or quarantined.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "ESD_BANDS",
    "BASELINE_MEASURES",
    "ENHANCED_MEASURES",
    "ENHANCED_BANDS",
    "DRY_FLOOR_LIFE_HOURS",
    "SEVERITY_ORDER",
    "esd_band",
    "owed_protection_measures",
    "protection_measure_gaps",
    "environment_margin",
    "floor_life_consumed",
    "shelf_life_state",
    "handling_qualification_gaps",
    "storage_verdict",
    "assess_class_two_handling_and_storage",
]

# Margin fractions, consumed fractions and excursions are quotients and
# differences of measured values, so a reading sitting exactly on a limit can
# land a few ULP on the wrong side. Absorb that here, never by moving a limit.
BOUND_TOLERANCE = 1e-9

# Electrostatic sensitivity bands as (band, lower withstand volts inclusive,
# upper withstand volts exclusive). A lower withstand voltage is a more
# sensitive part and a stricter handling regime.
ESD_BANDS = (
    ("0", 0.0, 250.0),
    ("1A", 250.0, 500.0),
    ("1B", 500.0, 1000.0),
    ("1C", 1000.0, 2000.0),
    ("2", 2000.0, 4000.0),
    ("3A", 4000.0, 8000.0),
    ("3B", 8000.0, float("inf")),
)

# Measures every band owes once a part is inside the protected area.
BASELINE_MEASURES = (
    "marked-esd-protected-area",
    "grounded-dissipative-worksurface",
    "personnel-grounding-wrist-strap",
    "static-shielding-transport-bag",
)

# Measures the most sensitive bands owe on top of the baseline. The
# intermediate class accepts a periodic verification of the personnel ground
# where the class above asks for a continuously monitored one.
ENHANCED_MEASURES = (
    "protected-area-ionizer",
    "periodic-wrist-strap-verification",
)

ENHANCED_BANDS = ("0", "1A")

# Floor-life allowance in hours outside the dry pack, by moisture sensitivity
# level. Level 1 is unrestricted; level 6 carries no floor life and is baked
# before use rather than rationed.
DRY_FLOOR_LIFE_HOURS = {
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

# An inside reading closer than this fraction of the half-span to its nearest
# limit is reported as running close to the edge of its band.
EDGE_MARGIN_FRACTION = 0.10


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
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


def _require_text(value, label):
    """Return a stripped non-empty string or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_int(value, label, positive=True):
    """Return a validated integer or raise ValueError."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def esd_band(withstand_volts):
    """Return the electrostatic sensitivity band of a part."""
    volts = _require_number(withstand_volts, "withstand_volts")
    for band, lower, upper in ESD_BANDS:
        if lower <= volts < upper:
            return band
    raise ValueError("withstand_volts %g falls in no sensitivity band" % volts)


def owed_protection_measures(band):
    """Return the sorted protection measures a sensitivity band owes."""
    if not isinstance(band, str):
        raise ValueError("band must be a string, got %r" % (band,))
    known = [name for name, _lo, _hi in ESD_BANDS]
    key = band.strip().upper()
    if key not in known:
        raise ValueError("band %r is not one of %r" % (band, known))
    measures = set(BASELINE_MEASURES)
    if key in ENHANCED_BANDS:
        measures |= set(ENHANCED_MEASURES)
    return sorted(measures)


def _normalise_substitutions(substitutions):
    """Return (credited_measures, rejected_records) from the declared records.

    A substitution is credited only when it names the owed measure it stands
    in for, names a different substitute, and carries an approval reference.
    """
    if substitutions is None:
        return set(), []
    if not isinstance(substitutions, (list, tuple)):
        raise ValueError("substitutions must be a sequence of records")
    credited = set()
    rejected = []
    for record in substitutions:
        if not isinstance(record, dict):
            raise ValueError("each substitution must be a mapping, got %r" % (record,))
        measure = record.get("measure")
        if not isinstance(measure, str) or not measure.strip():
            raise ValueError("each substitution must name the measure it replaces")
        key = measure.strip().lower()
        substitute = record.get("substitute")
        approval = record.get("approval")
        substitute_ok = isinstance(substitute, str) and bool(substitute.strip())
        approval_ok = isinstance(approval, str) and bool(approval.strip())
        distinct = substitute_ok and substitute.strip().lower() != key
        if substitute_ok and approval_ok and distinct:
            credited.add(key)
        else:
            rejected.append(key)
    return credited, sorted(set(rejected))


def protection_measure_gaps(band, measures_operated, substitutions=None):
    """Return the owed measures the store neither operates nor substitutes.

    Returns a mapping with the unmet measures, the measures covered by a
    credited substitution, and the substitution records that were refused
    because they were incompletely recorded.
    """
    if not isinstance(measures_operated, (list, tuple, set, frozenset)):
        raise ValueError("measures_operated must be a sequence or set")
    operated = set()
    for item in measures_operated:
        operated.add(_require_text(item, "protection measure").lower())
    credited, rejected = _normalise_substitutions(substitutions)
    owed = owed_protection_measures(band)
    unmet = []
    substituted = []
    for measure in owed:
        if measure in operated:
            continue
        if measure in credited:
            substituted.append(measure)
        else:
            unmet.append(measure)
    return {
        "unmet": unmet,
        "substituted": substituted,
        "rejected_substitutions": [m for m in rejected if m in set(owed)],
    }


def environment_margin(measured, limits, label="environment"):
    """Return the excursion and the normalised margin of a stored reading.

    excursion is zero inside the band, positive above the upper limit and
    negative below the lower limit. margin_fraction is the distance to the
    nearest limit divided by the half-span: positive inside, negative outside.
    """
    value = _require_number(measured, "%s measured value" % label, allow_negative=True)
    if not isinstance(limits, (list, tuple)) or len(limits) != 2:
        raise ValueError("%s limits must be a (lower, upper) pair" % label)
    lower = _require_number(limits[0], "%s lower limit" % label, allow_negative=True)
    upper = _require_number(limits[1], "%s upper limit" % label, allow_negative=True)
    if lower >= upper:
        raise ValueError("%s limits must span a non-zero band: %g >= %g" % (label, lower, upper))
    half_span = (upper - lower) / 2.0
    excursion = 0.0
    if value > upper and not math.isclose(value, upper, rel_tol=0.0, abs_tol=BOUND_TOLERANCE):
        excursion = value - upper
    elif value < lower and not math.isclose(value, lower, rel_tol=0.0, abs_tol=BOUND_TOLERANCE):
        excursion = value - lower
    if excursion == 0.0:
        nearest = min(upper - value, value - lower)
        if nearest < 0.0:
            nearest = 0.0
        margin = nearest / half_span
    else:
        margin = -abs(excursion) / half_span
    return {
        "measured": value,
        "excursion": excursion,
        "inside": excursion == 0.0,
        "margin_fraction": margin,
    }


def floor_life_consumed(msl_level, hours_open, dry_cabinet_hours=0.0,
                        bake_credit_hours=0.0):
    """Return the fraction of the dry-pack floor life a lot has consumed.

    An unrestricted level returns zero. A level carrying no floor life returns
    positive infinity once any net exposure is recorded, because the lot is
    baked before use rather than rationed.
    """
    if not isinstance(msl_level, str):
        raise ValueError("msl_level must be a string, got %r" % (msl_level,))
    key = msl_level.strip().upper()
    if key not in DRY_FLOOR_LIFE_HOURS:
        raise ValueError(
            "msl_level %r is not one of %r" % (msl_level, sorted(DRY_FLOOR_LIFE_HOURS))
        )
    exposed = _require_number(hours_open, "hours_open")
    cabinet = _require_number(dry_cabinet_hours, "dry_cabinet_hours")
    bake = _require_number(bake_credit_hours, "bake_credit_hours")
    if cabinet + bake > exposed:
        raise ValueError(
            "dry-cabinet and bake credits total %g h, above the recorded %g h"
            % (cabinet + bake, exposed)
        )
    allowance = DRY_FLOOR_LIFE_HOURS[key]
    if allowance is None:
        return 0.0
    net = exposed - cabinet - bake
    if allowance == 0.0:
        return float("inf") if net > 0.0 else 0.0
    return net / allowance


def shelf_life_state(entry_date, review_date, shelf_life_days,
                     reinspection_interval_days, last_inspection=None):
    """Return the shelf-life and periodic re-inspection state of a stored lot."""
    entry = _require_date(entry_date, "entry_date")
    review = _require_date(review_date, "review_date")
    if review < entry:
        raise ValueError("review_date %s precedes entry_date %s" % (review, entry))
    life = _require_int(shelf_life_days, "shelf_life_days")
    interval = _require_int(reinspection_interval_days, "reinspection_interval_days")
    reference = entry if last_inspection is None else _require_date(
        last_inspection, "last_inspection"
    )
    if reference < entry:
        raise ValueError("last_inspection %s precedes entry_date %s" % (reference, entry))
    if review < reference:
        raise ValueError("review_date %s precedes the inspection reference %s" % (review, reference))
    remaining = life - (review - entry).days
    since = (review - reference).days
    return {
        "remaining_days": remaining,
        "expired": remaining < 0,
        "expires_on_review": remaining == 0,
        "days_since_inspection": since,
        "reinspection_due": since >= interval,
    }


def handling_qualification_gaps(handlers, review_date):
    """Return the declared handlers whose electrostatic training has lapsed.

    A qualification whose expiry falls on the review date is still current;
    the day it names is the last day it covers.
    """
    if not isinstance(handlers, (list, tuple)):
        raise ValueError("handlers must be a sequence of records")
    review = _require_date(review_date, "review_date")
    seen = set()
    lapsed = []
    for record in handlers:
        if not isinstance(record, dict):
            raise ValueError("each handler must be a mapping, got %r" % (record,))
        name = _require_text(record.get("name"), "handler name")
        key = name.lower()
        if key in seen:
            raise ValueError("handler %r is declared twice" % name)
        seen.add(key)
        expiry = _require_date(record.get("qualification_expiry"), "qualification_expiry")
        if expiry < review:
            lapsed.append(name)
    return sorted(lapsed)


def _finding(severity, topic, message):
    if severity not in SEVERITY_ORDER:
        raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
    return {"severity": severity, "topic": topic, "message": message}


def storage_verdict(findings):
    """Return the verdict implied by the ranked findings."""
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


REQUIRED_KEYS = (
    "lot_id",
    "withstand_volts",
    "measures_operated",
    "temperature_c",
    "temperature_limits",
    "humidity_percent",
    "humidity_limits",
    "entry_date",
    "review_date",
    "shelf_life_days",
    "reinspection_interval_days",
)


def assess_class_two_handling_and_storage(record):
    """Grade one stored class 2 commercial EEE lot against clause 5.4.

    record keys: lot_id, withstand_volts, measures_operated, temperature_c,
    temperature_limits, humidity_percent, humidity_limits, entry_date,
    review_date, shelf_life_days, reinspection_interval_days, and optionally
    substitutions, handlers, last_inspection, msl_level, hours_open,
    dry_cabinet_hours and bake_credit_hours.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in REQUIRED_KEYS:
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)

    lot_id = _require_text(record["lot_id"], "lot_id")
    band = esd_band(record["withstand_volts"])
    gaps = protection_measure_gaps(
        band, record["measures_operated"], record.get("substitutions")
    )
    temperature = environment_margin(
        record["temperature_c"], record["temperature_limits"], label="temperature"
    )
    humidity = environment_margin(
        record["humidity_percent"], record["humidity_limits"], label="humidity"
    )
    shelf = shelf_life_state(
        record["entry_date"],
        record["review_date"],
        record["shelf_life_days"],
        record["reinspection_interval_days"],
        record.get("last_inspection"),
    )
    lapsed = handling_qualification_gaps(
        record.get("handlers", []), record["review_date"]
    )
    msl_level = record.get("msl_level")
    if msl_level is None:
        consumed = 0.0
    else:
        consumed = floor_life_consumed(
            msl_level,
            record.get("hours_open", 0.0),
            record.get("dry_cabinet_hours", 0.0),
            record.get("bake_credit_hours", 0.0),
        )

    findings = []
    for measure in gaps["unmet"]:
        findings.append(
            _finding(
                "critical",
                "electrostatic-protection",
                "band %s owes %s and the store neither operates nor substitutes it"
                % (band, measure),
            )
        )
    for measure in gaps["rejected_substitutions"]:
        findings.append(
            _finding(
                "major",
                "electrostatic-protection",
                "the substitution offered for %s is not fully recorded" % measure,
            )
        )
    for reading, label, unit, critical_at in (
        (temperature, "temperature", "C", 5.0),
        (humidity, "humidity", "percent", 10.0),
    ):
        if not reading["inside"]:
            findings.append(
                _finding(
                    "critical" if abs(reading["excursion"]) > critical_at else "major",
                    "storage-environment",
                    "store %s sits %.2f %s outside the declared band"
                    % (label, reading["excursion"], unit),
                )
            )
        elif reading["margin_fraction"] < EDGE_MARGIN_FRACTION:
            findings.append(
                _finding(
                    "minor",
                    "storage-environment",
                    "store %s holds only %.4f of its half-span to the nearest limit"
                    % (label, reading["margin_fraction"]),
                )
            )
    over_floor = consumed > 1.0 and not math.isclose(
        consumed, 1.0, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    if over_floor:
        if math.isfinite(consumed):
            message = "floor life consumed reads %.4f of the allowance; bake before use" % consumed
        else:
            message = "the declared level carries no floor life; bake before use"
        findings.append(_finding("critical", "moisture-sensitivity", message))
    elif consumed > 0.75:
        findings.append(
            _finding(
                "minor",
                "moisture-sensitivity",
                "floor life consumed reads %.4f of the allowance" % consumed,
            )
        )
    if shelf["expired"]:
        findings.append(
            _finding(
                "critical",
                "shelf-life",
                "declared shelf life ran out %d days before the review" % (-shelf["remaining_days"]),
            )
        )
    elif shelf["expires_on_review"]:
        findings.append(
            _finding("major", "shelf-life", "declared shelf life ends on the review date")
        )
    if shelf["reinspection_due"]:
        findings.append(
            _finding(
                "major",
                "shelf-life",
                "the periodic re-inspection interval has elapsed since the reference date",
            )
        )
    for name in lapsed:
        findings.append(
            _finding(
                "critical" if band in ENHANCED_BANDS else "major",
                "handling-authorisation",
                "handler %s holds no current electrostatic qualification" % name,
            )
        )
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["topic"], f["message"]))
    verdict = storage_verdict(findings)
    return {
        "lot_id": lot_id,
        "sensitivity_band": band,
        "owed_measures": owed_protection_measures(band),
        "unmet_measures": gaps["unmet"],
        "substituted_measures": gaps["substituted"],
        "rejected_substitutions": gaps["rejected_substitutions"],
        "temperature": temperature,
        "humidity": humidity,
        "floor_life_consumed": consumed,
        "shelf_life": shelf,
        "lapsed_handlers": lapsed,
        "findings": findings,
        "verdict": verdict,
        "released": verdict == "released",
    }

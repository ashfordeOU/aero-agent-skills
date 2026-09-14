"""Handling protection and storage conditions at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.4 (protected handling and storage of
commercial EEE parts procured at the lowest assurance class). Paraphrased
into an implementable procedure; no standard text is reproduced.

The question the clause answers
-------------------------------
Commercial parts are in a store that was never built to the standard of a
flight parts bay, and the question before they are issued is whether what
the store actually operates is enough for what is inside the bags.

What this class does differently
--------------------------------
1. The owed measure set is a minimum rather than a full regime, and an
   equivalent measure may be substituted for an owed one without prior
   approval, provided the substitution was recorded at the time of use. The
   record is the whole of the control: an unrecorded substitution is a gap.
2. The relaxation has a floor under it. On the most sensitive band no
   substitution is credited at all, because a part that goes down to a few
   hundred volts does not survive an improvisation nobody reviewed.
3. The storage environment is graded on a duration-weighted dose rather than
   on a peak reading. A store two degrees over its band for a whole summer
   and a store fifteen degrees over it for twenty minutes are the same
   yes-or-no answer and completely different dispositions, and the dose is
   what separates them.
4. Packaging is read as evidence rather than as a checkbox. The humidity
   indicator is what says whether the barrier did its job, so a breached bag
   with a dry indicator and an intact bag with a saturated one are different
   findings.

Procedure implemented here
--------------------------
1. Band the part by its declared electrostatic withstand voltage.
2. Derive the minimum measure set that band owes, credit an equivalent
   measure recorded at the time of use, and refuse the substitution on a
   band this class will not relax.
3. Integrate the temperature and relative-humidity segments into an
   over-limit and under-limit dose, and grade the dose into a severity.
4. Read the packaging: barrier, desiccant and the humidity indicator against
   its limit.
5. Take the shelf-life margin in days at the review date.
6. Rank every finding by severity and return one verdict: released,
   released-with-actions or quarantined.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "DEFAULT_STORAGE_POLICY",
    "ESD_BANDS",
    "BASELINE_MEASURES",
    "SENSITIVE_EXTRA_MEASURES",
    "SENSITIVE_BANDS",
    "NO_SUBSTITUTION_BANDS",
    "SEVERITY_ORDER",
    "DOSE_NONE",
    "DOSE_MINOR",
    "DOSE_MAJOR",
    "DOSE_CRITICAL",
    "INDICATOR_DRY",
    "INDICATOR_MARGINAL",
    "INDICATOR_SATURATED",
    "RELEASED",
    "RELEASED_WITH_ACTIONS",
    "QUARANTINED",
    "validate_storage_policy",
    "esd_band",
    "minimum_measures",
    "measure_gaps",
    "excursion_dose",
    "dose_severity",
    "humidity_indicator_state",
    "shelf_life_margin_days",
    "storage_verdict",
    "assess_class_three_handling_and_storage",
]

# Doses, margins and indicator readings are sums and differences of measured
# values, so a reading sitting exactly on a limit can land a few ULP on the
# wrong side. Absorb that here, never by moving a limit.
BOUND_TOLERANCE = 1e-9

DEFAULT_STORAGE_POLICY = {
    # Duration-weighted dose thresholds, in limit-units multiplied by hours.
    "minor_dose": 5.0,
    "major_dose": 50.0,
    "critical_dose": 200.0,
    # How far past its limit an indicator reading is still only marginal.
    "indicator_margin_percent": 5.0,
    # A shelf life running out inside this horizon is raised before issue.
    "review_horizon_days": 30,
}

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

# The minimum every band owes once a part is out of its shipping carton.
BASELINE_MEASURES = (
    "marked-esd-protected-area",
    "grounded-dissipative-worksurface",
    "personnel-grounding-wrist-strap",
    "static-shielding-transport-bag",
)

# What the sensitive bands owe on top of the minimum.
SENSITIVE_EXTRA_MEASURES = (
    "protected-area-ionizer",
    "wrist-strap-check-at-shift-start",
)

SENSITIVE_BANDS = ("0", "1A")

# Bands this class will not relax: no substitution is credited here.
NO_SUBSTITUTION_BANDS = ("0",)

SEVERITY_ORDER = ("critical", "major", "minor")

DOSE_NONE = "within-band"
DOSE_MINOR = "minor-excursion-dose"
DOSE_MAJOR = "major-excursion-dose"
DOSE_CRITICAL = "critical-excursion-dose"

INDICATOR_DRY = "indicator-dry"
INDICATOR_MARGINAL = "indicator-marginal"
INDICATOR_SATURATED = "indicator-saturated"

RELEASED = "released"
RELEASED_WITH_ACTIONS = "released-with-actions"
QUARANTINED = "quarantined"


def _at_or_above(value, limit):
    """True when value is at or above limit, absorbing representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
    )


def _at_or_below(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
    )


def _require_number(value, label, allow_negative=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _require_date(value, label):
    """Return a date parsed from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))
    raise ValueError("%s must be a date or an ISO yyyy-mm-dd string" % label)


def validate_storage_policy(policy):
    """Validate a storage policy and return it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in DEFAULT_STORAGE_POLICY:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    minor = _require_number(policy["minor_dose"], "minor_dose")
    major = _require_number(policy["major_dose"], "major_dose")
    critical = _require_number(policy["critical_dose"], "critical_dose")
    if not (minor < major < critical):
        raise ValueError(
            "the dose thresholds must rise: minor %g, major %g, critical %g"
            % (minor, major, critical)
        )
    if minor <= 0.0:
        raise ValueError("minor_dose must lie above zero, got %g" % minor)
    _require_number(policy["indicator_margin_percent"], "indicator_margin_percent")
    horizon = policy["review_horizon_days"]
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 0:
        raise ValueError("review_horizon_days must be a whole number of days")
    return policy


def esd_band(withstand_volts):
    """Return the sensitivity band of a part from its declared withstand."""
    volts = _require_number(withstand_volts, "withstand_volts")
    for band, lower, upper in ESD_BANDS:
        if volts >= lower and volts < upper:
            return band
    raise ValueError("no sensitivity band covers %g V" % volts)


def minimum_measures(band):
    """Return the ordered minimum measure set a sensitivity band owes."""
    key = _require_text(band, "band").upper()
    if key not in {name for name, _, _ in ESD_BANDS}:
        raise ValueError("sensitivity band '%s' is not in the register" % key)
    measures = list(BASELINE_MEASURES)
    if key in SENSITIVE_BANDS:
        measures.extend(SENSITIVE_EXTRA_MEASURES)
    return measures


def measure_gaps(band, operated, substitutions=None):
    """Compare what the store operates with what the band owes.

    substitutions maps an owed measure to a mapping carrying the equivalent
    measure offered in its place and whether the substitution was recorded at
    the time of use. An unrecorded substitution, or one offered on a band
    this class will not relax, is refused rather than credited.
    """
    key = _require_text(band, "band").upper()
    owed = minimum_measures(key)
    if not isinstance(operated, (list, tuple, set, frozenset)):
        raise ValueError("operated must be a sequence of measure names")
    running = set()
    for name in operated:
        running.add(_require_text(name, "operated measure").lower())
    offered = {}
    if substitutions is not None:
        if not isinstance(substitutions, dict):
            raise ValueError("substitutions must be a mapping")
        for name, detail in substitutions.items():
            owed_name = _require_text(name, "substituted measure").lower()
            if owed_name not in owed:
                raise ValueError(
                    "'%s' is not owed by band %s, so nothing stands in for it"
                    % (owed_name, key)
                )
            if not isinstance(detail, dict):
                raise ValueError("substitution for '%s' must be a mapping" % owed_name)
            for field in ("equivalent", "recorded"):
                if field not in detail:
                    raise ValueError(
                        "substitution for '%s' missing key '%s'" % (owed_name, field)
                    )
            equivalent = _require_text(detail["equivalent"], "equivalent measure").lower()
            if equivalent == owed_name:
                raise ValueError(
                    "the equivalent offered for '%s' is the measure itself" % owed_name
                )
            offered[owed_name] = {
                "equivalent": equivalent,
                "recorded": _require_flag(detail["recorded"], "recorded"),
            }
    missing = []
    substituted = []
    refused = []
    for name in owed:
        if name in running:
            continue
        detail = offered.get(name)
        if detail is None:
            missing.append(name)
            continue
        if key in NO_SUBSTITUTION_BANDS:
            refused.append(name)
            missing.append(name)
            continue
        if not detail["recorded"]:
            refused.append(name)
            missing.append(name)
            continue
        substituted.append(name)
    return {
        "band": key,
        "owed": owed,
        "missing": missing,
        "substituted": substituted,
        "refused_substitutions": refused,
    }


def excursion_dose(segments, lower_limit, upper_limit):
    """Integrate a logged environment into an over- and under-limit dose.

    Each segment carries the reading that held and how many hours it held
    for. The dose is the magnitude of the excursion multiplied by its
    duration and summed, so a small excursion held for a season and a large
    one held for an hour stop looking alike.
    """
    lower = _require_number(lower_limit, "lower_limit", allow_negative=True)
    upper = _require_number(upper_limit, "upper_limit", allow_negative=True)
    if not lower < upper:
        raise ValueError(
            "the declared band is empty: lower %g is not below upper %g" % (lower, upper)
        )
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("segments must be a non-empty sequence of logged readings")
    over = 0.0
    under = 0.0
    peak_over = 0.0
    peak_under = 0.0
    hours = 0.0
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError("segment %d must be a mapping" % index)
        for field in ("value", "hours"):
            if field not in segment:
                raise ValueError("segment %d missing key '%s'" % (index, field))
        value = _require_number(
            segment["value"], "segment %d value" % index, allow_negative=True
        )
        span = _require_number(segment["hours"], "segment %d hours" % index)
        if span == 0.0:
            raise ValueError("segment %d holds for no time at all" % index)
        hours += span
        if not _at_or_below(value, upper):
            excess = value - upper
            over += excess * span
            if excess > peak_over:
                peak_over = excess
        elif not _at_or_above(value, lower):
            shortfall = lower - value
            under += shortfall * span
            if shortfall > peak_under:
                peak_under = shortfall
    return {
        "over_dose": over,
        "under_dose": under,
        "dose": over + under,
        "peak_over": peak_over,
        "peak_under": peak_under,
        "hours": hours,
    }


def dose_severity(dose, policy=None):
    """Grade a duration-weighted dose into a severity."""
    policy = validate_storage_policy(
        DEFAULT_STORAGE_POLICY if policy is None else policy
    )
    value = _require_number(dose, "dose")
    if _at_or_above(value, float(policy["critical_dose"])):
        return DOSE_CRITICAL
    if _at_or_above(value, float(policy["major_dose"])):
        return DOSE_MAJOR
    if _at_or_above(value, float(policy["minor_dose"])):
        return DOSE_MINOR
    return DOSE_NONE


def humidity_indicator_state(reading_percent, limit_percent, policy=None):
    """Read a humidity indicator against the limit printed on it."""
    policy = validate_storage_policy(
        DEFAULT_STORAGE_POLICY if policy is None else policy
    )
    reading = _require_number(reading_percent, "reading_percent")
    limit = _require_number(limit_percent, "limit_percent")
    if limit <= 0.0:
        raise ValueError("limit_percent must lie above zero, got %g" % limit)
    if _at_or_below(reading, limit):
        return INDICATOR_DRY
    if _at_or_below(reading, limit + float(policy["indicator_margin_percent"])):
        return INDICATOR_MARGINAL
    return INDICATOR_SATURATED


def shelf_life_margin_days(storage_entry, shelf_life_days, review_date):
    """Return whole days of shelf life left at the review date.

    Day counts are integers throughout, so the margin is the same number on
    every platform the leaf runs on.
    """
    entry = _require_date(storage_entry, "storage_entry")
    review = _require_date(review_date, "review_date")
    if not isinstance(shelf_life_days, int) or isinstance(shelf_life_days, bool):
        raise ValueError("shelf_life_days must be a whole number of days")
    if shelf_life_days <= 0:
        raise ValueError("shelf_life_days must lie above zero, got %r" % shelf_life_days)
    if review < entry:
        raise ValueError("the review date falls before the lot entered store")
    expiry = entry + datetime.timedelta(days=shelf_life_days)
    return (expiry - review).days


def storage_verdict(findings):
    """Return the verdict the ranked findings produce."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence of (severity, text) pairs")
    seen = set()
    for finding in findings:
        if not isinstance(finding, (list, tuple)) or len(finding) != 2:
            raise ValueError("each finding must be a (severity, text) pair")
        severity = _require_text(finding[0], "severity").lower()
        if severity not in SEVERITY_ORDER:
            raise ValueError("severity '%s' is not in the register" % severity)
        _require_text(finding[1], "finding text")
        seen.add(severity)
    if "critical" in seen:
        return QUARANTINED
    if "major" in seen:
        return RELEASED_WITH_ACTIONS
    return RELEASED


def assess_class_three_handling_and_storage(case, policy=None):
    """Run the clause 6.4 assessment for one stored commercial lot.

    case keys: withstand_volts, measures_operated, substitutions,
    temperature_segments, temperature_limits, humidity_segments,
    humidity_limits, moisture_barrier_intact, desiccant_present,
    indicator_reading_percent, indicator_limit_percent, storage_entry,
    shelf_life_days, review_date.
    """
    policy = validate_storage_policy(
        DEFAULT_STORAGE_POLICY if policy is None else policy
    )
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in (
        "withstand_volts",
        "measures_operated",
        "substitutions",
        "temperature_segments",
        "temperature_limits",
        "humidity_segments",
        "humidity_limits",
        "moisture_barrier_intact",
        "desiccant_present",
        "indicator_reading_percent",
        "indicator_limit_percent",
        "storage_entry",
        "shelf_life_days",
        "review_date",
    ):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    band = esd_band(case["withstand_volts"])
    gaps = measure_gaps(band, case["measures_operated"], case["substitutions"])
    t_limits = case["temperature_limits"]
    h_limits = case["humidity_limits"]
    for label, limits in (("temperature_limits", t_limits), ("humidity_limits", h_limits)):
        if not isinstance(limits, (list, tuple)) or len(limits) != 2:
            raise ValueError("%s must be a (lower, upper) pair" % label)
    temperature = excursion_dose(
        case["temperature_segments"], t_limits[0], t_limits[1]
    )
    humidity = excursion_dose(case["humidity_segments"], h_limits[0], h_limits[1])
    t_severity = dose_severity(temperature["dose"], policy)
    h_severity = dose_severity(humidity["dose"], policy)
    barrier = _require_flag(case["moisture_barrier_intact"], "moisture_barrier_intact")
    desiccant = _require_flag(case["desiccant_present"], "desiccant_present")
    indicator = humidity_indicator_state(
        case["indicator_reading_percent"], case["indicator_limit_percent"], policy
    )
    margin = shelf_life_margin_days(
        case["storage_entry"], case["shelf_life_days"], case["review_date"]
    )
    findings = []
    strict = band in SENSITIVE_BANDS
    for name in gaps["missing"]:
        findings.append(
            (
                "critical" if strict else "major",
                "band %s owes '%s' and the store does not operate it" % (band, name),
            )
        )
    for name in gaps["refused_substitutions"]:
        findings.append(
            (
                "major",
                "the substitution offered for '%s' is not credited on band %s"
                % (name, band),
            )
        )
    for label, reading, severity in (
        ("temperature", temperature, t_severity),
        ("relative humidity", humidity, h_severity),
    ):
        if severity == DOSE_CRITICAL:
            findings.append(
                (
                    "critical",
                    "%s ran a dose of %g outside its band over %g hour(s)"
                    % (label, reading["dose"], reading["hours"]),
                )
            )
        elif severity == DOSE_MAJOR:
            findings.append(
                (
                    "major",
                    "%s ran a dose of %g outside its band over %g hour(s)"
                    % (label, reading["dose"], reading["hours"]),
                )
            )
        elif severity == DOSE_MINOR:
            findings.append(
                (
                    "minor",
                    "%s ran a dose of %g outside its band; log the deviation"
                    % (label, reading["dose"]),
                )
            )
    if not barrier and indicator == INDICATOR_SATURATED:
        findings.append(
            ("critical", "the moisture barrier is breached and the indicator is wet")
        )
    elif indicator == INDICATOR_SATURATED:
        findings.append(("major", "the humidity indicator reads past its limit"))
    elif indicator == INDICATOR_MARGINAL:
        findings.append(("minor", "the humidity indicator is close to its limit"))
    elif not barrier:
        findings.append(
            ("major", "the moisture barrier is breached though the indicator is dry")
        )
    if barrier and not desiccant:
        findings.append(("minor", "the sealed bag carries no desiccant"))
    if margin < 0:
        findings.append(
            ("critical", "the shelf life ran out %d day(s) ago" % (-margin))
        )
    elif margin <= policy["review_horizon_days"]:
        findings.append(
            ("major", "the shelf life runs out in %d day(s)" % margin)
        )
    verdict = storage_verdict(findings)
    return {
        "band": band,
        "owed_measures": gaps["owed"],
        "missing_measures": gaps["missing"],
        "substituted_measures": gaps["substituted"],
        "refused_substitutions": gaps["refused_substitutions"],
        "temperature": temperature,
        "humidity": humidity,
        "temperature_severity": t_severity,
        "humidity_severity": h_severity,
        "indicator_state": indicator,
        "shelf_life_margin_days": margin,
        "findings": findings,
        "verdict": verdict,
        "released": verdict != QUARANTINED,
    }

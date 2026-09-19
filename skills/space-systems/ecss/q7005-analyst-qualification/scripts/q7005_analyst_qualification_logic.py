"""Qualification of an analyst to interpret IR contamination spectra.

Anchor: ECSS-Q-ST-70-05C, the quality assurance provision on the
qualification of the person who interprets the spectra (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Qualification is held per contaminant family, not per person. A
   spectrum of a fluorinated oil and a spectrum of a silicone are read
   against different expectations, and an endorsement in one says
   nothing about the other.
2. Two error rates are tracked, not one. Failing to see contamination
   and naming the wrong species are different failures with different
   consequences downstream, so a correct-reading rate and a
   misidentification rate are graded against separate thresholds.
3. A rate needs enough rounds behind it to mean anything. Below the
   minimum round count the evidence is absent, and absent evidence is
   refused rather than scored as a zero rate or as a pass.
4. Qualification lapses. Currency runs from the last qualifying activity
   by whole calendar months, and a short window past expiry is a
   provisional state rather than an immediate disqualification.
5. Provisional is a real outcome, not a soft refusal. An analyst short
   on supervised interpretations, or just past currency, may interpret
   with an independent check by someone fully qualified in that family,
   and the record says which.

Stdlib only, offline, deterministic.
"""

import calendar
import datetime

OUTCOME_CORRECT = "correct"
OUTCOME_MISSED = "missed"
OUTCOME_MISIDENTIFIED = "misidentified"

VALID_OUTCOMES = (OUTCOME_CORRECT, OUTCOME_MISSED, OUTCOME_MISIDENTIFIED)

QUALIFIED = "qualified"
PROVISIONAL = "provisional-with-independent-check"
NOT_QUALIFIED = "not-qualified"

DEFAULT_POLICY = {
    "minimum_supervised_interpretations": 10,
    "minimum_proficiency_rounds": 3,
    "minimum_correct_rate": 0.80,
    "maximum_misidentification_rate": 0.10,
    "currency_months": 24,
    "provisional_grace_months": 6,
}

# Rates are counts over counts, so a value that should sit exactly on a
# threshold can land a few units in the last place either side of it.
RATE_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _whole(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %r" % (label, minimum, value))
    return value


def parse_date(text):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(text, datetime.date):
        return text
    if not isinstance(text, str):
        raise ValueError("date must be an ISO yyyy-mm-dd string, got %r" % (text,))
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("date %r is not in yyyy-mm-dd form" % (text,))
    try:
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date %r is not a real calendar date" % (text,))


def add_calendar_months(start, months):
    """Advance a date by whole calendar months, clamping to the month end."""
    begin = parse_date(start)
    count = _whole("months", months, 1)
    total = begin.month - 1 + count
    year = begin.year + total // 12
    month = total % 12 + 1
    day = min(begin.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def resolved_policy(policy=None):
    """Merge a caller policy over the defaults and validate it."""
    merged = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping")
        unknown = sorted(set(policy) - set(DEFAULT_POLICY))
        if unknown:
            raise ValueError("unknown policy keys: %s" % ", ".join(unknown))
        merged.update(policy)
    _whole("minimum_supervised_interpretations",
           merged["minimum_supervised_interpretations"], 0)
    _whole("minimum_proficiency_rounds", merged["minimum_proficiency_rounds"], 1)
    _numeric("minimum_correct_rate", merged["minimum_correct_rate"], 0.0, 1.0)
    _numeric("maximum_misidentification_rate",
             merged["maximum_misidentification_rate"], 0.0, 1.0)
    _whole("currency_months", merged["currency_months"], 1)
    _whole("provisional_grace_months", merged["provisional_grace_months"], 0)
    return merged


def validate_round(entry):
    """Validate one proficiency round and return a normalized copy."""
    if not isinstance(entry, dict):
        raise ValueError("proficiency round must be a mapping")
    family = entry.get("family")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("proficiency round needs a non-empty contaminant family")
    outcome = entry.get("outcome")
    if outcome not in VALID_OUTCOMES:
        raise ValueError(
            "outcome %r must be one of %s" % (outcome, ", ".join(VALID_OUTCOMES))
        )
    return {
        "family": family.strip(),
        "outcome": outcome,
        "date": parse_date(entry["date"]) if entry.get("date") else None,
    }


def proficiency_rates(rounds, family):
    """Correct and misidentification rates over one family's rounds."""
    if not isinstance(rounds, list):
        raise ValueError("rounds must be a list")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    family = family.strip()
    graded = [validate_round(r) for r in rounds]
    subset = [r for r in graded if r["family"] == family]
    if not subset:
        raise ValueError("no proficiency rounds recorded for family %r" % family)
    total = float(len(subset))
    correct = sum(1 for r in subset if r["outcome"] == OUTCOME_CORRECT)
    wrong_name = sum(1 for r in subset if r["outcome"] == OUTCOME_MISIDENTIFIED)
    missed = sum(1 for r in subset if r["outcome"] == OUTCOME_MISSED)
    return {
        "family": family,
        "rounds": len(subset),
        "correct": correct,
        "missed": missed,
        "misidentified": wrong_name,
        "correct_rate": correct / total,
        "misidentification_rate": wrong_name / total,
    }


def validate_analyst(record):
    """Validate an analyst record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("analyst must be a mapping")
    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("analyst needs a non-empty string name")
    name = name.strip()
    families = record.get("endorsed_families")
    if not isinstance(families, (list, tuple)) or not families:
        raise ValueError("%s needs a non-empty endorsed_families list" % name)
    cleaned = []
    for family in families:
        if not isinstance(family, str) or not family.strip():
            raise ValueError("%s has an empty endorsed family entry" % name)
        cleaned.append(family.strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("%s lists a duplicate endorsed family" % name)
    supervised = _whole(
        "%s supervised_interpretations" % name,
        record.get("supervised_interpretations"),
        0,
    )
    rounds = record.get("proficiency_rounds")
    if not isinstance(rounds, list):
        raise ValueError("%s needs a proficiency_rounds list" % name)
    return {
        "name": name,
        "training_reference": record.get("training_reference") or None,
        "endorsed_families": tuple(cleaned),
        "supervised_interpretations": supervised,
        "proficiency_rounds": [validate_round(r) for r in rounds],
        "last_qualifying_activity": parse_date(record["last_qualifying_activity"])
        if record.get("last_qualifying_activity")
        else None,
    }


def currency_expiry(record, policy=None):
    """Date an analyst's currency runs out, or None when never established."""
    norm = validate_analyst(record)
    rules = resolved_policy(policy)
    if norm["last_qualifying_activity"] is None:
        return None
    return add_calendar_months(
        norm["last_qualifying_activity"], rules["currency_months"]
    )


def assess_analyst(record, family, on_date, policy=None):
    """Decide whether one analyst may interpret spectra of one family."""
    norm = validate_analyst(record)
    rules = resolved_policy(policy)
    day = parse_date(on_date)
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    family = family.strip()

    blocking = []
    provisional = []
    rates = None

    if not norm["training_reference"]:
        blocking.append("no-training-record-on-file")

    if family not in norm["endorsed_families"]:
        blocking.append("family-outside-the-endorsement")
    else:
        try:
            rates = proficiency_rates(norm["proficiency_rounds"], family)
        except ValueError:
            rates = None
        if rates is None or rates["rounds"] < rules["minimum_proficiency_rounds"]:
            blocking.append("too-few-proficiency-rounds-to-support-a-rate")
        else:
            if rates["correct_rate"] + RATE_TOLERANCE < rules[
                "minimum_correct_rate"
            ]:
                blocking.append("correct-reading-rate-below-the-threshold")
            if rates["misidentification_rate"] > rules[
                "maximum_misidentification_rate"
            ] + RATE_TOLERANCE:
                blocking.append("misidentification-rate-above-the-ceiling")

    expiry = currency_expiry(norm, rules)
    if expiry is None:
        blocking.append("no-qualifying-activity-on-record")
        days_left = None
    else:
        days_left = (expiry - day).days
        if days_left < 0:
            grace_end = expiry
            if rules["provisional_grace_months"] > 0:
                grace_end = add_calendar_months(
                    expiry, rules["provisional_grace_months"]
                )
            if day <= grace_end:
                provisional.append("currency-lapsed-inside-the-grace-window")
            else:
                blocking.append("currency-lapsed-beyond-the-grace-window")

    if norm["supervised_interpretations"] < rules[
        "minimum_supervised_interpretations"
    ]:
        provisional.append("supervised-interpretation-count-short")

    if blocking:
        verdict = NOT_QUALIFIED
    elif provisional:
        verdict = PROVISIONAL
    else:
        verdict = QUALIFIED

    return {
        "analyst": norm["name"],
        "family": family,
        "on_date": day.isoformat(),
        "currency_expiry": expiry.isoformat() if expiry else None,
        "days_of_currency_left": days_left,
        "proficiency": rates,
        "blocking_findings": blocking,
        "provisional_findings": provisional,
        "verdict": verdict,
        "independent_check_required": verdict == PROVISIONAL,
    }


def assign_interpretation(analysts, family, on_date, policy=None):
    """Pick who may read a spectrum of one family, and who must check them."""
    if not isinstance(analysts, list) or not analysts:
        raise ValueError("analysts must be a non-empty list")
    rules = resolved_policy(policy)
    assessed = []
    seen = set()
    for record in analysts:
        row = assess_analyst(record, family, on_date, rules)
        if row["analyst"] in seen:
            raise ValueError("duplicate analyst %r" % (row["analyst"],))
        seen.add(row["analyst"])
        assessed.append(row)

    qualified = sorted(
        r["analyst"] for r in assessed if r["verdict"] == QUALIFIED
    )
    provisional = sorted(
        r["analyst"] for r in assessed if r["verdict"] == PROVISIONAL
    )
    refused = sorted(
        r["analyst"] for r in assessed if r["verdict"] == NOT_QUALIFIED
    )

    findings = []
    if qualified:
        assigned = qualified[0]
        check_required = False
        may_proceed = True
    elif provisional:
        assigned = provisional[0]
        check_required = True
        may_proceed = False
        findings.append("provisional-analyst-with-no-qualified-checker-available")
    else:
        assigned = None
        check_required = False
        may_proceed = False
        findings.append("no-endorsed-analyst-available-for-this-family")

    return {
        "family": family,
        "on_date": parse_date(on_date).isoformat(),
        "assessments": assessed,
        "qualified": qualified,
        "provisional": provisional,
        "not_qualified": refused,
        "assigned_analyst": assigned,
        "independent_check_required": check_required,
        "findings": findings,
        "interpretation_may_proceed": may_proceed,
    }

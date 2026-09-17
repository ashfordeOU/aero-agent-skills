"""Sample teardown of a delivered Class 3 EEE lot.

Anchor: ECSS-Q-ST-60C clause 6.3.9 -- the sample teardown analysis performed per
lot or date code to confirm Class 3 construction quality. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Which date codes of a Class 3 shipment owe their own teardown, how many pieces
each one gives up, and what the bench observations do to the lot.

1. Population. A shipment spanning several date codes is several populations. A
   build drifts between date codes, so one teardown evidences only the group it
   was drawn from.
2. Delegation. Class 3 is the class where a manufacturer teardown report for the
   same date code, still inside its validity, can stand in for the project's
   own. A credited group gives up a confirmation piece instead of a full sample.
3. Baseline. Every torn-down piece is compared attribute by attribute against
   the construction baseline the part was procured on. An attribute the
   baseline never declared is refused; an attribute that differs is a
   construction change.
4. Contagion. A construction change is about the line, not about the piece. It
   revokes the delegation credit for its own date code and for every later date
   code in the shipment, because a report raised before the change cannot speak
   for parts built after it.
5. Seal. A hermetic package is judged on its measured leak rate against the
   project limit, compared through a relative tolerance so a reading sitting on
   the limit is decided by the rule rather than by the last bit.
6. Disposition. A critical observation or a leaking package ends the lot. A
   construction change goes to the parts control board, which is the body that
   can accept a changed build. Only cosmetic counts buy a second sample.
"""

from fractions import Fraction
from datetime import date

__all__ = [
    "BASELINE_ATTRIBUTES",
    "OBSERVATION_CATEGORIES",
    "DEFAULT_SAMPLE_FRACTION",
    "MINIMUM_SAMPLE",
    "MAXIMUM_SAMPLE",
    "CONFIRMATION_SAMPLE",
    "DEFAULT_MINOR_ALLOWANCE",
    "DEFAULT_DELEGATION_VALIDITY_MONTHS",
    "DEFAULT_FINE_LEAK_LIMIT",
    "RELATIVE_TOLERANCE",
    "DISPOSITION_PRECEDENCE",
    "share",
    "parse_day",
    "date_code_week_start",
    "months_elapsed",
    "partition_by_date_code",
    "teardown_sample_size",
    "delegation_credited",
    "compare_construction",
    "categorize_observation",
    "summarize_observations",
    "seal_within_limit",
    "teardown_plan",
    "assess_class_3_teardown",
]

# The construction attributes a Class 3 baseline declares.
BASELINE_ATTRIBUTES = (
    "die-marking",
    "passivation",
    "metallization-system",
    "die-attach-medium",
    "lid-seal-method",
    "wire-material",
)

# How a bench observation is graded, worst first.
OBSERVATION_CATEGORIES = ("critical", "major", "minor")

# Share of a date-code group torn down when the group owes its own sample.
DEFAULT_SAMPLE_FRACTION = Fraction(1, 100)

# No teardown draws fewer pieces than this unless the group is smaller.
MINIMUM_SAMPLE = 2

# Above this a wider teardown buys little; the findings are systemic.
MAXIMUM_SAMPLE = 8

# What a delegated group gives up instead of a full sample.
CONFIRMATION_SAMPLE = 1

# Cosmetic observations tolerated on a sample before it is re-drawn.
DEFAULT_MINOR_ALLOWANCE = 2

# A manufacturer teardown report older than this no longer stands in.
DEFAULT_DELEGATION_VALIDITY_MONTHS = 18

# Fine leak limit in the project's leak-rate unit.
DEFAULT_FINE_LEAK_LIMIT = 5e-8

# Absorbs representation error at the leak limit. It is not an engineering
# allowance and is never widened to pass a leaking package.
RELATIVE_TOLERANCE = 1e-9

# Lot dispositions, worst first; the first one that fires wins.
DISPOSITION_PRECEDENCE = (
    "reject",
    "refer-to-parts-control-board",
    "second-sample",
    "accept",
)


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def _positive(label, value):
    """Return value as a strictly positive float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not number > 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _share(label, value):
    """Return value as a Fraction strictly inside (0, 1]."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ValueError("%s must be an int or Fraction share, got %r" % (label, value))
    share = Fraction(value)
    if share <= 0 or share > 1:
        raise ValueError("%s must lie in (0, 1], got %s" % (label, share))
    return share


def _ceil(value):
    """Return the ceiling of a Fraction as an int, without float rounding."""
    return -(-value.numerator // value.denominator)


def share(numerator, denominator):
    """Return an exact rational share built from two integers.

    Callers hand sizing shares in as rationals so the arithmetic stays exact.
    This builds one without the caller reaching for a module of its own; the
    range is checked where the share is used, not here, so an out-of-range
    share can still be constructed and refused at the point that cares.
    """
    for label, value in (("numerator", numerator), ("denominator", denominator)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if denominator == 0:
        raise ValueError("denominator must not be zero")
    return Fraction(numerator, denominator)


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def date_code_week_start(date_code, century_base=2000):
    """Return the first day of the build week a YYWW date code names."""
    text = _text("date_code", date_code)
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (date_code,))
    base = _count("century_base", century_base)
    if base % 100:
        raise ValueError("century_base must be a whole century, got %d" % base)
    year = base + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (date_code,))
    try:
        return date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError("calendar year %d has no week %02d" % (year, week))


def months_elapsed(start_day, end_day):
    """Return the whole calendar months from start_day to end_day."""
    start = parse_day("start_day", start_day)
    end = parse_day("end_day", end_day)
    if end < start:
        raise ValueError("end day %s precedes start day %s" % (end, start))
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def partition_by_date_code(units, century_base=2000):
    """Return the shipment split into date-code groups, oldest build first.

    units: sequence of mappings with serial and date_code, optionally
    build_demand-bearing via a committed flag. A repeated serial is refused,
    because it means two records describe the same piece and every count built
    on them is wrong.
    """
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of delivered pieces")
    groups = {}
    seen = set()
    for index, item in enumerate(units):
        if not isinstance(item, dict):
            raise ValueError("units[%d] must be a mapping" % index)
        for key in ("serial", "date_code"):
            if key not in item:
                raise ValueError("units[%d] missing required key '%s'" % (index, key))
        serial = _text("units[%d].serial" % index, item["serial"])
        if serial in seen:
            raise ValueError("serial '%s' appears more than once in the shipment" % serial)
        seen.add(serial)
        code = _text("units[%d].date_code" % index, item["date_code"])
        week = date_code_week_start(code, century_base)
        committed = _flag("units[%d].committed" % index, item.get("committed", False))
        group = groups.setdefault(
            code, {"date_code": code, "week_start": week, "size": 0, "committed": 0}
        )
        group["size"] += 1
        if committed:
            group["committed"] += 1
    ordered = sorted(groups.values(), key=lambda g: g["week_start"])
    for group in ordered:
        group["spare"] = group["size"] - group["committed"]
    return ordered


def teardown_sample_size(
    group_size,
    sample_fraction=DEFAULT_SAMPLE_FRACTION,
    minimum=MINIMUM_SAMPLE,
    maximum=MAXIMUM_SAMPLE,
):
    """Return the pieces a date-code group gives up to its own teardown."""
    held = _count("group_size", group_size)
    if held < 1:
        raise ValueError("group_size must be at least 1, got %d" % held)
    share = _share("sample_fraction", sample_fraction)
    floor_sample = _count("minimum", minimum)
    cap = _count("maximum", maximum)
    if floor_sample < 1:
        raise ValueError("minimum must be at least 1, got %d" % floor_sample)
    if cap < floor_sample:
        raise ValueError("maximum %d is below minimum %d" % (cap, floor_sample))
    drawn = _ceil(Fraction(held) * share)
    if drawn < floor_sample:
        drawn = floor_sample
    if drawn > cap:
        drawn = cap
    if drawn > held:
        drawn = held
    return drawn


def delegation_credited(
    group,
    reports,
    as_of_day,
    validity_months=DEFAULT_DELEGATION_VALIDITY_MONTHS,
):
    """Return whether a manufacturer teardown report stands in for a group.

    reports: sequence of mappings with date_code and issued_day. The report has
    to name the same date code -- a neighbouring week is a different build and
    cannot speak for this one.
    """
    if not isinstance(group, dict) or "date_code" not in group:
        raise ValueError("group must be a mapping carrying a date_code")
    if reports is None:
        reports = ()
    if not isinstance(reports, (list, tuple)):
        raise ValueError("reports must be a sequence of manufacturer teardown reports")
    validity = _count("validity_months", validity_months)
    if validity < 1:
        raise ValueError("validity_months must be at least 1, got %d" % validity)
    reasons = []
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            raise ValueError("reports[%d] must be a mapping" % index)
        for key in ("date_code", "issued_day"):
            if key not in report:
                raise ValueError("reports[%d] missing required key '%s'" % (index, key))
        code = _text("reports[%d].date_code" % index, report["date_code"])
        age = months_elapsed(report["issued_day"], as_of_day)
        if code != group["date_code"]:
            continue
        if age > validity:
            reasons.append(
                "report for date code %s is %d month(s) old against a %d month validity"
                % (code, age, validity)
            )
            continue
        return {"credited": True, "age_months": age, "reasons": []}
    return {"credited": False, "age_months": None, "reasons": reasons}


def compare_construction(observed, baseline):
    """Return the attribute-by-attribute comparison against the baseline.

    Both mappings carry every declared baseline attribute. An attribute the
    baseline never declared is refused, because there is nothing to compare it
    with and a bench call is not a baseline.
    """
    if not isinstance(observed, dict) or not isinstance(baseline, dict):
        raise ValueError("observed and baseline must both be mappings")
    for name in BASELINE_ATTRIBUTES:
        if name not in baseline:
            raise ValueError("baseline missing declared attribute '%s'" % name)
        if name not in observed:
            raise ValueError("observed construction missing attribute '%s'" % name)
    for name in observed:
        if name not in BASELINE_ATTRIBUTES:
            raise ValueError(
                "attribute '%s' is not a declared baseline attribute" % name
            )
    deviations = []
    for name in BASELINE_ATTRIBUTES:
        want = _text("baseline['%s']" % name, baseline[name]).lower()
        got = _text("observed['%s']" % name, observed[name]).lower()
        if want != got:
            deviations.append(
                {"attribute": name, "baseline": want, "observed": got}
            )
    return {
        "deviations": deviations,
        "matches_baseline": not deviations,
        "findings": [
            "construction attribute '%s' reads '%s' against a baseline of '%s'"
            % (d["attribute"], d["observed"], d["baseline"])
            for d in deviations
        ],
    }


def categorize_observation(code, register):
    """Return the category a project register gives one bench observation.

    A code the register never listed is refused. An ungraded observation can be
    counted neither as critical nor as cosmetic, so it cannot be disposed of.
    """
    name = _text("observation code", code)
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of code to category")
    if name not in register:
        raise ValueError("observation code '%s' is not in the project register" % name)
    category = _text("register['%s']" % name, register[name]).lower()
    if category not in OBSERVATION_CATEGORIES:
        raise ValueError(
            "register grades '%s' as %r, not one of %s"
            % (name, register[name], ", ".join(OBSERVATION_CATEGORIES))
        )
    return category


def summarize_observations(observations, register):
    """Return the bench observations grouped by their registered category."""
    if observations is None:
        observations = ()
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence of observation codes")
    counts = {category: 0 for category in OBSERVATION_CATEGORIES}
    detail = {category: [] for category in OBSERVATION_CATEGORIES}
    for index, item in enumerate(observations):
        code = _text("observations[%d]" % index, item)
        category = categorize_observation(code, register)
        counts[category] += 1
        detail[category].append(code)
    return {
        "counts": counts,
        "detail": detail,
        "total": sum(counts.values()),
        "worst": next((c for c in OBSERVATION_CATEGORIES if counts[c]), None),
    }


def seal_within_limit(
    leak_rate, limit=DEFAULT_FINE_LEAK_LIMIT, tolerance=RELATIVE_TOLERANCE
):
    """Return whether a measured fine leak rate sits inside the project limit.

    A reading exactly on the limit passes; the tolerance absorbs how the
    measurement represented itself, not any part of the limit.
    """
    measured = _positive("leak_rate", leak_rate)
    bound = _positive("limit", limit)
    slack = _positive("tolerance", tolerance)
    return measured <= bound * (1.0 + slack)


def teardown_plan(
    groups,
    reports,
    as_of_day,
    options=None,
    deviation_from_week=None,
):
    """Return the sample each date-code group owes.

    A group whose delegation credit was revoked by a construction change, or
    which never earned one, owes its own sample; a credited group gives up a
    confirmation piece. A group that cannot spare what it owes is reported
    infeasible rather than quietly under-sampled.
    """
    if not isinstance(groups, (list, tuple)) or not groups:
        raise ValueError("groups must be a non-empty sequence of date-code groups")
    settings = dict(options or {})
    validity = settings.get("validity_months", DEFAULT_DELEGATION_VALIDITY_MONTHS)
    planned = []
    for group in groups:
        credit = delegation_credited(group, reports, as_of_day, validity)
        revoked = (
            deviation_from_week is not None
            and group["week_start"] >= deviation_from_week
        )
        credited = credit["credited"] and not revoked
        if credited:
            sample = min(
                _count("confirmation_sample", settings.get("confirmation_sample", CONFIRMATION_SAMPLE)),
                group["size"],
            )
        else:
            sample = teardown_sample_size(
                group["size"],
                settings.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
                settings.get("minimum_sample", MINIMUM_SAMPLE),
                settings.get("maximum_sample", MAXIMUM_SAMPLE),
            )
        spare = _count("group spare", group.get("spare", group["size"]))
        feasible = sample <= spare
        findings = list(credit["reasons"])
        if revoked and credit["credited"]:
            findings.append(
                "delegation credit for date code %s is revoked by a construction "
                "change at or before this build week" % group["date_code"]
            )
        if not feasible:
            findings.append(
                "date code %s owes %d piece(s) but only %d spare(s) remain"
                % (group["date_code"], sample, spare)
            )
        planned.append(
            {
                "date_code": group["date_code"],
                "size": group["size"],
                "spare": spare,
                "delegated": credited,
                "sample": sample,
                "feasible": feasible,
                "findings": findings,
            }
        )
    return planned


def assess_class_3_teardown(spec):
    """Return the clause 6.3.9 teardown disposition for one Class 3 shipment.

    spec keys: units, baseline, register and as_of_day; optional reports,
    observations, observed_construction, leak_rate, leak_limit, minor_allowance,
    sample_number, second_sample_permitted and the sizing settings.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "baseline", "register", "as_of_day"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    century_base = spec.get("century_base", 2000)
    groups = partition_by_date_code(spec["units"], century_base)
    construction = None
    deviation_from_week = None
    findings = []
    if spec.get("observed_construction") is not None:
        construction = compare_construction(
            spec["observed_construction"], spec["baseline"]
        )
        findings.extend(construction["findings"])
        if construction["deviations"]:
            code = _text("deviation_date_code", spec.get("deviation_date_code", groups[0]["date_code"]))
            deviation_from_week = date_code_week_start(code, century_base)
    options = {
        "validity_months": spec.get(
            "validity_months", DEFAULT_DELEGATION_VALIDITY_MONTHS
        ),
        "sample_fraction": spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        "minimum_sample": spec.get("minimum_sample", MINIMUM_SAMPLE),
        "maximum_sample": spec.get("maximum_sample", MAXIMUM_SAMPLE),
        "confirmation_sample": spec.get("confirmation_sample", CONFIRMATION_SAMPLE),
    }
    plan = teardown_plan(
        groups, spec.get("reports"), spec["as_of_day"], options, deviation_from_week
    )
    for entry in plan:
        findings.extend(entry["findings"])
    observations = summarize_observations(spec.get("observations"), spec["register"])
    allowance = _count(
        "minor_allowance", spec.get("minor_allowance", DEFAULT_MINOR_ALLOWANCE)
    )
    minor_over = observations["counts"]["minor"] > allowance
    if minor_over:
        findings.append(
            "%d cosmetic observation(s) against an allowance of %d"
            % (observations["counts"]["minor"], allowance)
        )
    seal = None
    if spec.get("leak_rate") is not None:
        seal = seal_within_limit(
            spec["leak_rate"], spec.get("leak_limit", DEFAULT_FINE_LEAK_LIMIT)
        )
        if not seal:
            findings.append("measured fine leak rate sits above the project limit")
    sample_number = _count("sample_number", spec.get("sample_number", 1))
    if sample_number < 1:
        raise ValueError("sample_number must be at least 1, got %d" % sample_number)
    second_permitted = _flag(
        "second_sample_permitted", spec.get("second_sample_permitted", True)
    )
    critical = observations["counts"]["critical"] > 0
    major = observations["counts"]["major"] > 0
    changed = bool(construction and construction["deviations"])
    if critical or seal is False:
        disposition = "reject"
    elif changed:
        disposition = "refer-to-parts-control-board"
    elif major:
        disposition = "reject"
    elif minor_over and second_permitted and sample_number == 1:
        disposition = "second-sample"
    elif minor_over:
        disposition = "reject"
    else:
        disposition = "accept"
    return {
        "groups": groups,
        "plan": plan,
        "total_sample": sum(entry["sample"] for entry in plan),
        "feasible": all(entry["feasible"] for entry in plan),
        "construction": construction,
        "observations": observations,
        "minor_allowance": allowance,
        "minor_over_allowance": minor_over,
        "seal_within_limit": seal,
        "sample_number": sample_number,
        "disposition": disposition,
        "findings": findings,
    }

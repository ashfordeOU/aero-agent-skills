"""Lot homogeneity assessment before class 1 sampling.

Anchor: ECSS-Q-ST-60-13C clause 4.5.5 (drawing test specimens from a genuinely
uniform production lot). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivered population: every unit carries an identifier, a wafer
   lot, an assembly lot, a manufacturing site and a four-digit date code.
2. Group the units on their traceability key. Each distinct key is a sub-lot:
   material that shared a diffusion run, an assembly run and a site.
3. Take the date-code span of the population in whole weeks and compare it with
   the span the sampling policy admits for one lot.
4. Size the sample from the lot with integer arithmetic so the same lot size
   always yields the same required count on any machine.
5. Confirm the drawn specimens reach every sub-lot rather than clustering in
   the largest one, and report each sub-lot the sample never touched.
6. Return one verdict: the span is too wide, the population is several sub-lots
   where only one was admitted, the sample is not representative, or the lot is
   uniform and the specimens may be drawn.
"""

__all__ = [
    "WEEKS_PER_YEAR",
    "DEFAULT_SAMPLING_POLICY",
    "HOMOGENEOUS_LOT",
    "MULTIPLE_SUB_LOTS",
    "DATE_CODE_SPAN_EXCEEDED",
    "SAMPLE_NOT_REPRESENTATIVE",
    "validate_sampling_policy",
    "parse_date_code",
    "date_code_week_index",
    "validate_unit",
    "validate_population",
    "traceability_key",
    "group_units",
    "date_code_span_weeks",
    "largest_sub_lot_share",
    "required_sample_size",
    "sample_coverage",
    "assess_lot_homogeneity",
]

# A date code carries two digits of year and two of week. Week 53 is folded
# onto the first week of the following year; that is inside the resolution a
# date code can claim, and it keeps the index arithmetic in integers.
WEEKS_PER_YEAR = 52

HOMOGENEOUS_LOT = "homogeneous-lot"
MULTIPLE_SUB_LOTS = "multiple-sub-lots"
DATE_CODE_SPAN_EXCEEDED = "date-code-span-exceeded"
SAMPLE_NOT_REPRESENTATIVE = "sample-not-representative"

DEFAULT_SAMPLING_POLICY = {
    # Widest date-code span one lot may cover, in whole weeks.
    "max_date_code_span_weeks": 13,
    # Sample fraction of the lot, held as an exact integer ratio.
    "sample_numerator": 1,
    "sample_denominator": 10,
    "min_sample_units": 5,
    "max_sample_units": 45,
    # Whether a population made of several traceability groups may still be
    # sampled as one lot, provided every group is reached.
    "allow_sub_lots": False,
    "require_every_sub_lot_sampled": True,
}

_TRACEABILITY_FIELDS = ("wafer_lot", "assembly_lot", "manufacturing_site")


def validate_sampling_policy(policy=None):
    """Return a complete sampling policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_SAMPLING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("sampling policy must be a mapping")
    merged = dict(DEFAULT_SAMPLING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_SAMPLING_POLICY:
            raise ValueError("unknown sampling policy key %r" % (key,))
        merged[key] = value
    for key in ("max_date_code_span_weeks", "sample_numerator",
                "sample_denominator", "min_sample_units", "max_sample_units"):
        value = merged[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (key, value))
    for key in ("allow_sub_lots", "require_every_sub_lot_sampled"):
        if not isinstance(merged[key], bool):
            raise ValueError("%s must be a boolean" % key)
    if merged["max_date_code_span_weeks"] < 0:
        raise ValueError("max_date_code_span_weeks must not be negative")
    if merged["sample_numerator"] <= 0 or merged["sample_denominator"] <= 0:
        raise ValueError("the sample ratio must be built from positive integers")
    if merged["sample_numerator"] > merged["sample_denominator"]:
        raise ValueError("the sample ratio must not exceed the whole lot")
    if merged["min_sample_units"] <= 0:
        raise ValueError("min_sample_units must be positive")
    if merged["max_sample_units"] < merged["min_sample_units"]:
        raise ValueError("max_sample_units must not fall below min_sample_units")
    return merged


def parse_date_code(code):
    """Return the (year, week) pair a four-digit date code carries."""
    if not isinstance(code, str):
        raise ValueError("date_code must be a four-digit string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must read YYWW, got %r" % (code,))
    year = int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (code,))
    return (year, week)


def date_code_week_index(code):
    """Return a monotone integer week index for a date code."""
    year, week = parse_date_code(code)
    return year * WEEKS_PER_YEAR + (week - 1)


def validate_unit(unit):
    """Return a normalised unit record, raising on any missing traceability."""
    if not isinstance(unit, dict):
        raise ValueError("each unit must be a mapping, got %r" % (type(unit).__name__,))
    identifier = unit.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each unit needs a non-empty 'id'")
    record = {"id": identifier.strip()}
    for field in _TRACEABILITY_FIELDS:
        value = unit.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "unit %s carries no '%s'; traceability is a precondition of the "
                "homogeneity judgement" % (record["id"], field)
            )
        record[field] = value.strip()
    code = unit.get("date_code")
    record["date_code"] = code.strip() if isinstance(code, str) else code
    record["week_index"] = date_code_week_index(record["date_code"])
    return record


def validate_population(units):
    """Return the validated list of units making up the delivered population."""
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of unit records")
    records = []
    seen = set()
    for unit in units:
        record = validate_unit(unit)
        if record["id"] in seen:
            raise ValueError("duplicate unit id %r in the population" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    years = {parse_date_code(r["date_code"])[0] for r in records}
    if any(y >= 90 for y in years) and any(y <= 9 for y in years):
        raise ValueError(
            "date codes straddle a century rollover; the span cannot be taken "
            "from two-digit years alone"
        )
    return records


def traceability_key(unit):
    """Return the tuple that decides which sub-lot a unit belongs to."""
    record = unit if "week_index" in unit else validate_unit(unit)
    return tuple(record[field] for field in _TRACEABILITY_FIELDS)


def group_units(records):
    """Return an ordered mapping of traceability key to the unit ids under it."""
    groups = {}
    for record in records:
        groups.setdefault(traceability_key(record), []).append(record["id"])
    return groups


def date_code_span_weeks(records):
    """Return the whole-week span between the oldest and newest date code."""
    if not records:
        raise ValueError("cannot take a date-code span of an empty population")
    indices = [record["week_index"] for record in records]
    return max(indices) - min(indices)


def largest_sub_lot_share(groups, lot_size):
    """Return the share of the lot sitting in its single largest sub-lot."""
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping")
    if not isinstance(lot_size, int) or isinstance(lot_size, bool) or lot_size <= 0:
        raise ValueError("lot_size must be a positive integer")
    largest = max(len(ids) for ids in groups.values())
    return float(largest) / float(lot_size)


def required_sample_size(lot_size, policy=None):
    """Return the number of specimens the policy requires from this lot size."""
    settings = validate_sampling_policy(policy)
    if not isinstance(lot_size, int) or isinstance(lot_size, bool):
        raise ValueError("lot_size must be an integer, got %r" % (lot_size,))
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    numerator = settings["sample_numerator"]
    denominator = settings["sample_denominator"]
    # Exact ceiling division: no float ever touches the sample count, so the
    # same lot size yields the same answer on every platform.
    proportional = -((-lot_size * numerator) // denominator)
    size = max(proportional, settings["min_sample_units"])
    size = min(size, settings["max_sample_units"])
    return min(size, lot_size)


def sample_coverage(groups, sample_ids):
    """Return how many drawn specimens landed in each sub-lot, and which got none."""
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping")
    if not isinstance(sample_ids, (list, tuple)):
        raise ValueError("sample_ids must be a sequence of unit ids")
    drawn = []
    seen = set()
    for identifier in sample_ids:
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("every drawn specimen needs a non-empty id")
        name = identifier.strip()
        if name in seen:
            raise ValueError("unit %r was drawn twice" % (name,))
        seen.add(name)
        drawn.append(name)
    membership = {}
    for key, ids in groups.items():
        for identifier in ids:
            membership[identifier] = key
    unknown = [name for name in drawn if name not in membership]
    if unknown:
        raise ValueError(
            "drawn specimens are not part of the population: %s" % ", ".join(sorted(unknown))
        )
    counts = {key: 0 for key in groups}
    for name in drawn:
        counts[membership[name]] += 1
    unsampled = sorted(key for key, count in counts.items() if count == 0)
    return {"counts": counts, "unsampled_sub_lots": unsampled, "drawn": drawn}


def assess_lot_homogeneity(case):
    """Run the clause 4.5.5 homogeneity assessment over a delivered population.

    case keys: units (sequence of unit records), optional sample (sequence of
    unit ids already drawn), optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "units" not in case:
        raise ValueError("case missing required key 'units'")
    settings = validate_sampling_policy(case.get("policy"))
    records = validate_population(case["units"])
    lot_size = len(records)
    groups = group_units(records)
    span = date_code_span_weeks(records)
    needed = required_sample_size(lot_size, settings)
    sample_ids = case.get("sample") or []
    coverage = sample_coverage(groups, sample_ids)
    drawn = coverage["drawn"]

    findings = []
    span_exceeded = span > settings["max_date_code_span_weeks"]
    if span_exceeded:
        findings.append(
            "the population spans %d weeks of date code against the %d week "
            "limit for a single lot" % (span, settings["max_date_code_span_weeks"])
        )
    split = len(groups) > 1
    if split and not settings["allow_sub_lots"]:
        findings.append(
            "the population is %d traceability groups, not one uniform lot" % len(groups)
        )
    undersized = len(drawn) < needed
    if undersized:
        findings.append(
            "%d specimens were drawn against the %d this lot size requires"
            % (len(drawn), needed)
        )
    uncovered = []
    if settings["require_every_sub_lot_sampled"] and drawn:
        uncovered = coverage["unsampled_sub_lots"]
        for key in uncovered:
            findings.append(
                "sub-lot %s received no specimen; the sample cannot speak for it"
                % ("/".join(key),)
            )

    if span_exceeded:
        verdict = DATE_CODE_SPAN_EXCEEDED
    elif split and not settings["allow_sub_lots"]:
        verdict = MULTIPLE_SUB_LOTS
    elif undersized or uncovered:
        verdict = SAMPLE_NOT_REPRESENTATIVE
    else:
        verdict = HOMOGENEOUS_LOT

    return {
        "verdict": verdict,
        "lot_size": lot_size,
        "sub_lot_count": len(groups),
        "sub_lots": {key: list(ids) for key, ids in groups.items()},
        "date_code_span_weeks": span,
        "max_date_code_span_weeks": settings["max_date_code_span_weeks"],
        "required_sample_size": needed,
        "sample_size": len(drawn),
        "largest_sub_lot_share": largest_sub_lot_share(groups, lot_size),
        "unsampled_sub_lots": uncovered,
        "sub_lot_counts": coverage["counts"],
        "homogeneous": verdict == HOMOGENEOUS_LOT,
        "findings": findings,
    }

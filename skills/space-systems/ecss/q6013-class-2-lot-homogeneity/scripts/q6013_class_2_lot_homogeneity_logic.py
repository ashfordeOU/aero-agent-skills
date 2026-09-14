"""Lot uniformity demonstration before class 2 sampling tests.

Anchor: ECSS-Q-ST-60-13C clause 5.5.5 (showing that the population test
specimens are drawn from is one inspection lot at the intermediate assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the sampling policy: the sub-lot cap the intermediate class admits,
   the date-code span limit, the sample ratio held as two integers with a floor
   and a cap, the allocation slack and whether an equivalence basis may stand
   in for missing wafer-lot data.
2. Validate the delivered population. A unit with full traceability is placed
   on its wafer lot, assembly lot and site; a unit with no wafer lot is placed
   on the declared equivalence basis instead, and refused where no basis is
   declared.
3. Group the units into sub-lots and take the date-code span of the whole
   population in whole weeks.
4. Size the required sample from the lot with exact integer arithmetic, so the
   same lot size yields the same count on any machine.
5. Allocate that sample across the sub-lots in proportion to their size by the
   largest-remainder method, again in integers, so the target for each sub-lot
   is reproducible rather than a rounding artefact.
6. Compare the specimens actually drawn against each sub-lot's target inside
   the declared slack, and name every sub-lot under-drawn or never reached.
7. Return one verdict: no equivalence basis for an untraceable unit, a
   date-code span too wide, more sub-lots than the class admits, a sample that
   is undersized or not proportional, or a lot the specimens may be drawn from.
"""

__all__ = [
    "WEEKS_PER_YEAR",
    "DEFAULT_SAMPLING_POLICY",
    "EQUIVALENCE_BASIS_NOT_DECLARED",
    "DATE_CODE_SPAN_EXCEEDED",
    "SUB_LOT_CAP_EXCEEDED",
    "SAMPLE_NOT_PROPORTIONAL",
    "LOT_ADMITTED_FOR_SAMPLING",
    "validate_sampling_policy",
    "parse_date_code",
    "date_code_week_index",
    "validate_unit",
    "validate_population",
    "sub_lot_key",
    "group_units",
    "date_code_span_weeks",
    "required_sample_size",
    "proportional_allocation",
    "allocation_shortfalls",
    "assess_lot_uniformity",
]

# A date code carries two digits of year and two of week. Week 53 is folded
# onto the first week of the following year; that is inside the resolution a
# date code can claim and it keeps the index arithmetic in integers.
WEEKS_PER_YEAR = 52

EQUIVALENCE_BASIS_NOT_DECLARED = "equivalence-basis-not-declared"
DATE_CODE_SPAN_EXCEEDED = "date-code-span-exceeded"
SUB_LOT_CAP_EXCEEDED = "sub-lot-cap-exceeded"
SAMPLE_NOT_PROPORTIONAL = "sample-not-proportional"
LOT_ADMITTED_FOR_SAMPLING = "lot-admitted-for-sampling"

DEFAULT_SAMPLING_POLICY = {
    # How many sub-lots the intermediate class will still treat as one
    # inspection lot, given every one of them is sampled in proportion.
    "max_sub_lots": 3,
    # Widest date-code span one inspection lot may cover, in whole weeks.
    "max_date_code_span_weeks": 26,
    # Sample fraction of the lot, held as an exact integer ratio.
    "sample_numerator": 1,
    "sample_denominator": 10,
    "min_sample_units": 5,
    "max_sample_units": 45,
    # Specimens a sub-lot may fall short of its proportional target by.
    "allocation_slack_units": 0,
    # Whether a unit carrying no wafer lot may be placed on a declared
    # equivalence basis instead of being refused outright.
    "allow_equivalence_basis": True,
}

_FULL_TRACEABILITY_FIELDS = ("wafer_lot", "assembly_lot", "manufacturing_site")
_EQUIVALENCE_FIELDS = ("assembly_lot", "manufacturing_site")

_INTEGER_POLICY_KEYS = (
    "max_sub_lots",
    "max_date_code_span_weeks",
    "sample_numerator",
    "sample_denominator",
    "min_sample_units",
    "max_sample_units",
    "allocation_slack_units",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _clean_text(value):
    return value.strip() if isinstance(value, str) else ""


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
    for key in _INTEGER_POLICY_KEYS:
        if not _is_int(merged[key]):
            raise ValueError("%s must be an integer, got %r" % (key, merged[key]))
    if not isinstance(merged["allow_equivalence_basis"], bool):
        raise ValueError("allow_equivalence_basis must be a boolean")
    if merged["max_sub_lots"] < 1:
        raise ValueError("max_sub_lots must admit at least one sub-lot")
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
    if merged["allocation_slack_units"] < 0:
        raise ValueError("allocation_slack_units must not be negative")
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


def validate_unit(unit, policy=None):
    """Return a normalised unit record, placed on full traceability or a basis."""
    settings = validate_sampling_policy(policy)
    if not isinstance(unit, dict):
        raise ValueError("each unit must be a mapping, got %r" % (type(unit).__name__,))
    identifier = _clean_text(unit.get("id"))
    if not identifier:
        raise ValueError("each unit needs a non-empty 'id'")
    record = {"id": identifier}
    for field in _EQUIVALENCE_FIELDS:
        value = _clean_text(unit.get(field))
        if not value:
            raise ValueError(
                "unit %s carries no '%s'; it cannot be placed in any sub-lot"
                % (identifier, field)
            )
        record[field] = value
    wafer = _clean_text(unit.get("wafer_lot"))
    basis = _clean_text(unit.get("equivalence_basis"))
    if wafer:
        record["wafer_lot"] = wafer
        record["placed_on_basis"] = False
        record["equivalence_basis"] = ""
    else:
        if not settings["allow_equivalence_basis"]:
            raise ValueError(
                "unit %s carries no wafer lot and the policy admits no equivalence "
                "basis" % identifier
            )
        record["wafer_lot"] = ""
        record["placed_on_basis"] = True
        record["equivalence_basis"] = basis
    record["date_code"] = _clean_text(unit.get("date_code"))
    record["week_index"] = date_code_week_index(record["date_code"])
    return record


def validate_population(units, policy=None):
    """Return the validated list of units making up the delivered population."""
    settings = validate_sampling_policy(policy)
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of unit records")
    records = []
    seen = set()
    for unit in units:
        record = validate_unit(unit, settings)
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


def sub_lot_key(record):
    """Return the tuple deciding which sub-lot a unit belongs to."""
    if record["placed_on_basis"]:
        return ("basis", record["equivalence_basis"]) + tuple(
            record[field] for field in _EQUIVALENCE_FIELDS
        )
    return ("traced", record["wafer_lot"]) + tuple(
        record[field] for field in _EQUIVALENCE_FIELDS
    )


def group_units(records):
    """Return a mapping of sub-lot key to the unit ids sitting under it."""
    groups = {}
    for record in records:
        groups.setdefault(sub_lot_key(record), []).append(record["id"])
    return groups


def date_code_span_weeks(records):
    """Return the whole-week span between the oldest and newest date code."""
    if not records:
        raise ValueError("cannot take a date-code span of an empty population")
    indices = [record["week_index"] for record in records]
    return max(indices) - min(indices)


def required_sample_size(lot_size, policy=None):
    """Return the number of specimens the policy requires from this lot size."""
    settings = validate_sampling_policy(policy)
    if not _is_int(lot_size):
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


def proportional_allocation(groups, total):
    """Return how many specimens each sub-lot is owed, by largest remainder.

    All integer arithmetic: the base share is a floor division and the leftover
    specimens go to the largest remainders, ties broken on the sub-lot key, so
    the allocation is identical on every machine.
    """
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping")
    if not _is_int(total) or total < 0:
        raise ValueError("total must be a non-negative integer")
    lot_size = sum(len(ids) for ids in groups.values())
    if lot_size <= 0:
        raise ValueError("the population behind the groups is empty")
    if total > lot_size:
        raise ValueError("cannot allocate more specimens than the lot holds")
    allocation = {}
    remainders = []
    for key in sorted(groups):
        size = len(groups[key])
        base, remainder = divmod(size * total, lot_size)
        allocation[key] = min(base, size)
        remainders.append((remainder, key))
    leftover = total - sum(allocation.values())
    remainders.sort(key=lambda item: (-item[0], item[1]))
    index = 0
    while leftover > 0 and index < len(remainders) * 2:
        _, key = remainders[index % len(remainders)]
        if allocation[key] < len(groups[key]):
            allocation[key] += 1
            leftover -= 1
        index += 1
    return allocation


def allocation_shortfalls(groups, allocation, sample_ids, slack=0):
    """Return the sub-lots drawn short of their target, and the drawn specimens."""
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping")
    if not isinstance(sample_ids, (list, tuple)):
        raise ValueError("sample_ids must be a sequence of unit ids")
    if not _is_int(slack) or slack < 0:
        raise ValueError("slack must be a non-negative integer")
    membership = {}
    for key, ids in groups.items():
        for identifier in ids:
            membership[identifier] = key
    drawn = []
    seen = set()
    for identifier in sample_ids:
        name = _clean_text(identifier)
        if not name:
            raise ValueError("every drawn specimen needs a non-empty id")
        if name in seen:
            raise ValueError("unit %r was drawn twice" % (name,))
        seen.add(name)
        if name not in membership:
            raise ValueError("drawn specimen %r is not part of the population" % (name,))
        drawn.append(name)
    counts = {key: 0 for key in groups}
    for name in drawn:
        counts[membership[name]] += 1
    short = sorted(
        key for key in groups if counts[key] + slack < allocation.get(key, 0)
    )
    untouched = sorted(key for key in groups if counts[key] == 0)
    return {
        "counts": counts,
        "short_sub_lots": short,
        "untouched_sub_lots": untouched,
        "drawn": drawn,
    }


def assess_lot_uniformity(case):
    """Run the clause 5.5.5 uniformity demonstration over a delivered population.

    case keys: units (sequence of unit records), optional sample (sequence of
    unit ids already drawn), optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "units" not in case:
        raise ValueError("case missing required key 'units'")
    settings = validate_sampling_policy(case.get("policy"))
    records = validate_population(case["units"], settings)
    lot_size = len(records)
    groups = group_units(records)
    span = date_code_span_weeks(records)
    needed = required_sample_size(lot_size, settings)
    allocation = proportional_allocation(groups, needed)
    coverage = allocation_shortfalls(
        groups, allocation, case.get("sample") or [], settings["allocation_slack_units"]
    )
    drawn = coverage["drawn"]

    findings = []
    undeclared = sorted(
        r["id"] for r in records if r["placed_on_basis"] and not r["equivalence_basis"]
    )
    for identifier in undeclared:
        findings.append(
            "unit %s carries no wafer lot and no equivalence basis was declared for it"
            % identifier
        )

    span_exceeded = span > settings["max_date_code_span_weeks"]
    if span_exceeded:
        findings.append(
            "the population spans %d weeks of date code against the %d week limit "
            "for one inspection lot" % (span, settings["max_date_code_span_weeks"])
        )

    cap_exceeded = len(groups) > settings["max_sub_lots"]
    if cap_exceeded:
        findings.append(
            "the delivery holds %d sub-lots against the %d the class admits as one "
            "inspection lot" % (len(groups), settings["max_sub_lots"])
        )

    undersized = len(drawn) < needed
    if undersized:
        findings.append(
            "%d specimens were drawn against the %d this lot size requires"
            % (len(drawn), needed)
        )
    for key in coverage["short_sub_lots"]:
        findings.append(
            "sub-lot %s holds %d specimens against its proportional target of %d"
            % ("/".join(key), coverage["counts"][key], allocation[key])
        )

    if undeclared:
        verdict = EQUIVALENCE_BASIS_NOT_DECLARED
    elif span_exceeded:
        verdict = DATE_CODE_SPAN_EXCEEDED
    elif cap_exceeded:
        verdict = SUB_LOT_CAP_EXCEEDED
    elif undersized or coverage["short_sub_lots"]:
        verdict = SAMPLE_NOT_PROPORTIONAL
    else:
        verdict = LOT_ADMITTED_FOR_SAMPLING

    return {
        "verdict": verdict,
        "lot_size": lot_size,
        "sub_lot_count": len(groups),
        "sub_lots": {key: list(ids) for key, ids in groups.items()},
        "date_code_span_weeks": span,
        "max_date_code_span_weeks": settings["max_date_code_span_weeks"],
        "required_sample_size": needed,
        "sample_size": len(drawn),
        "allocation": allocation,
        "drawn_per_sub_lot": coverage["counts"],
        "short_sub_lots": coverage["short_sub_lots"],
        "untouched_sub_lots": coverage["untouched_sub_lots"],
        "units_on_equivalence_basis": sorted(
            r["id"] for r in records if r["placed_on_basis"]
        ),
        "undeclared_basis_units": undeclared,
        "admitted": verdict == LOT_ADMITTED_FOR_SAMPLING,
        "findings": findings,
    }

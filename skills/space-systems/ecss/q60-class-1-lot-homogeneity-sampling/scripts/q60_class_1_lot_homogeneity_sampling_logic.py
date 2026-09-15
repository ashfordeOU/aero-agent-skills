"""Representativeness of a class 1 part sample drawn for lot testing.

Anchor: ECSS-Q-ST-60C clause 4.5.5 (a sample tested in place of the whole lot
has to genuinely stand for that lot). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivered lot: every part carries an identifier and the
   stratum label the purchaser declared the lot to be split on.
2. Group the parts into strata and record which identifiers sit in each.
3. Size the required sample from the lot size with exact integer arithmetic so
   the same lot yields the same count on any machine.
4. Allocate that sample across the strata proportionally by the largest
   remainder method, breaking ties on the stratum label so the allocation is
   reproducible.
5. Map the units actually drawn onto their strata and take the shortfall of
   each against its allocation.
6. Evaluate the defectives found in the sample against the acceptance number
   of the plan.
7. Return one verdict. A sample that is undersized, that misses a stratum or
   that is skewed away from its allocation cannot carry an acceptance to the
   rest of the lot; defectives beyond the acceptance number still reject it,
   because a reject needs no representativeness argument to stand.
"""

__all__ = [
    "DEFAULT_SAMPLING_PLAN",
    "REPRESENTATIVE_SAMPLE",
    "SAMPLE_UNDERSIZED",
    "STRATUM_UNREPRESENTED",
    "ALLOCATION_SKEWED",
    "LOT_REJECTED_ON_DEFECTIVES",
    "validate_sampling_plan",
    "validate_part",
    "validate_lot",
    "stratify_lot",
    "stratum_sizes",
    "required_sample_size",
    "allocate_sample",
    "map_drawn_units",
    "allocation_shortfalls",
    "stratum_coverage_fraction",
    "largest_stratum_share",
    "evaluate_acceptance_number",
    "assess_sample_representativeness",
]

REPRESENTATIVE_SAMPLE = "representative-sample"
SAMPLE_UNDERSIZED = "sample-undersized"
STRATUM_UNREPRESENTED = "stratum-unrepresented"
ALLOCATION_SKEWED = "allocation-skewed"
LOT_REJECTED_ON_DEFECTIVES = "lot-rejected-on-defectives"

DEFAULT_SAMPLING_PLAN = {
    # Sample fraction of the lot, held as an exact integer ratio.
    "sample_numerator": 1,
    "sample_denominator": 10,
    "min_sample_units": 5,
    "max_sample_units": 45,
    # How far a stratum may sit below its proportional allocation, in units,
    # before the draw stops being proportional.
    "max_allocation_shortfall_units": 1,
    # Defectives the plan still accepts in the drawn sample.
    "acceptance_number": 0,
    # Whether every declared stratum has to receive at least one unit.
    "require_every_stratum_drawn": True,
}

_INT_PLAN_KEYS = (
    "sample_numerator",
    "sample_denominator",
    "min_sample_units",
    "max_sample_units",
    "max_allocation_shortfall_units",
    "acceptance_number",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_sampling_plan(plan=None):
    """Return a complete sampling plan with the defaults filled in."""
    if plan is None:
        return dict(DEFAULT_SAMPLING_PLAN)
    if not isinstance(plan, dict):
        raise ValueError("sampling plan must be a mapping")
    merged = dict(DEFAULT_SAMPLING_PLAN)
    for key, value in plan.items():
        if key not in DEFAULT_SAMPLING_PLAN:
            raise ValueError("unknown sampling plan key %r" % (key,))
        merged[key] = value
    for key in _INT_PLAN_KEYS:
        if not _is_int(merged[key]):
            raise ValueError("%s must be an integer, got %r" % (key, merged[key]))
    if not isinstance(merged["require_every_stratum_drawn"], bool):
        raise ValueError("require_every_stratum_drawn must be a boolean")
    if merged["sample_numerator"] <= 0 or merged["sample_denominator"] <= 0:
        raise ValueError("the sample ratio must be built from positive integers")
    if merged["sample_numerator"] > merged["sample_denominator"]:
        raise ValueError("the sample ratio must not exceed the whole lot")
    if merged["min_sample_units"] <= 0:
        raise ValueError("min_sample_units must be positive")
    if merged["max_sample_units"] < merged["min_sample_units"]:
        raise ValueError("max_sample_units must not fall below min_sample_units")
    if merged["max_allocation_shortfall_units"] < 0:
        raise ValueError("max_allocation_shortfall_units must not be negative")
    if merged["acceptance_number"] < 0:
        raise ValueError("acceptance_number must not be negative")
    return merged


def validate_part(part):
    """Return a normalised part record, raising when the stratum is missing."""
    if not isinstance(part, dict):
        raise ValueError("each part must be a mapping, got %r" % (type(part).__name__,))
    identifier = part.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each part needs a non-empty 'id'")
    stratum = part.get("stratum")
    if not isinstance(stratum, str) or not stratum.strip():
        raise ValueError(
            "part %s carries no 'stratum' label; an unplaceable part cannot be "
            "shown to be represented by the sample" % (identifier.strip(),)
        )
    return {"id": identifier.strip(), "stratum": stratum.strip()}


def validate_lot(parts):
    """Return the validated part records making up the delivered lot."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence of part records")
    records = []
    seen = set()
    for part in parts:
        record = validate_part(part)
        if record["id"] in seen:
            raise ValueError("duplicate part id %r in the lot" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    return records


def stratify_lot(records):
    """Return a mapping of stratum label to the part ids sitting in it."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    strata = {}
    for record in records:
        key = record["stratum"] if "stratum" in record else validate_part(record)["stratum"]
        strata.setdefault(key, []).append(record["id"])
    return strata


def stratum_sizes(strata):
    """Return the population of each stratum."""
    if not isinstance(strata, dict) or not strata:
        raise ValueError("strata must be a non-empty mapping")
    return {key: len(ids) for key, ids in strata.items()}


def required_sample_size(lot_size, plan=None):
    """Return the specimen count the plan requires from this lot size."""
    settings = validate_sampling_plan(plan)
    if not _is_int(lot_size):
        raise ValueError("lot_size must be an integer, got %r" % (lot_size,))
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    numerator = settings["sample_numerator"]
    denominator = settings["sample_denominator"]
    # Exact ceiling division. No float touches the count, so a lot sitting
    # exactly on the ratio rounds the same way on every platform.
    proportional = -((-lot_size * numerator) // denominator)
    size = max(proportional, settings["min_sample_units"])
    size = min(size, settings["max_sample_units"])
    return min(size, lot_size)


def allocate_sample(sizes, sample_size):
    """Spread a sample across strata proportionally, by largest remainder.

    Whole units first, then the leftover units to the largest remainders, ties
    broken on the stratum label so two reviewers derive the same allocation.
    """
    if not isinstance(sizes, dict) or not sizes:
        raise ValueError("sizes must be a non-empty mapping of stratum to population")
    if not _is_int(sample_size) or sample_size < 0:
        raise ValueError("sample_size must be a non-negative integer")
    for key, value in sizes.items():
        if not _is_int(value) or value <= 0:
            raise ValueError("stratum %r must hold a positive population" % (key,))
    lot_size = sum(sizes.values())
    if sample_size > lot_size:
        raise ValueError("sample_size %d exceeds the lot size %d" % (sample_size, lot_size))
    allocation = {}
    remainders = []
    for key in sorted(sizes):
        scaled = sizes[key] * sample_size
        whole = scaled // lot_size
        allocation[key] = whole
        remainders.append((scaled - whole * lot_size, key))
    leftover = sample_size - sum(allocation.values())
    # Largest remainder first; the label keeps the order total and repeatable.
    remainders.sort(key=lambda item: (-item[0], item[1]))
    for index in range(leftover):
        allocation[remainders[index][1]] += 1
    return allocation


def map_drawn_units(strata, drawn_ids):
    """Return how many drawn units landed in each stratum."""
    if not isinstance(strata, dict) or not strata:
        raise ValueError("strata must be a non-empty mapping")
    if not isinstance(drawn_ids, (list, tuple)):
        raise ValueError("drawn_ids must be a sequence of part ids")
    membership = {}
    for key, ids in strata.items():
        for identifier in ids:
            membership[identifier] = key
    counts = {key: 0 for key in strata}
    names = []
    seen = set()
    for identifier in drawn_ids:
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("every drawn unit needs a non-empty id")
        name = identifier.strip()
        if name in seen:
            raise ValueError("part %r was drawn twice" % (name,))
        seen.add(name)
        if name not in membership:
            raise ValueError("drawn unit %r is not part of the lot" % (name,))
        counts[membership[name]] += 1
        names.append(name)
    return {"counts": counts, "drawn": names}


def allocation_shortfalls(allocation, counts):
    """Return, per stratum, how many units the draw fell short of its allocation."""
    if not isinstance(allocation, dict) or not allocation:
        raise ValueError("allocation must be a non-empty mapping")
    if not isinstance(counts, dict):
        raise ValueError("counts must be a mapping")
    missing = set(allocation) - set(counts)
    if missing:
        raise ValueError("no draw count for stratum %s" % ", ".join(sorted(missing)))
    shortfalls = {}
    for key, wanted in allocation.items():
        gap = wanted - counts[key]
        shortfalls[key] = gap if gap > 0 else 0
    return shortfalls


def stratum_coverage_fraction(counts):
    """Return the fraction of strata that received at least one drawn unit."""
    if not isinstance(counts, dict) or not counts:
        raise ValueError("counts must be a non-empty mapping")
    reached = sum(1 for value in counts.values() if value > 0)
    return float(reached) / float(len(counts))


def largest_stratum_share(sizes, lot_size):
    """Return the share of the lot sitting in its single largest stratum."""
    if not isinstance(sizes, dict) or not sizes:
        raise ValueError("sizes must be a non-empty mapping")
    if not _is_int(lot_size) or lot_size <= 0:
        raise ValueError("lot_size must be a positive integer")
    return float(max(sizes.values())) / float(lot_size)


def evaluate_acceptance_number(defectives, sample_size, plan=None):
    """Return whether the defectives found stay inside the acceptance number."""
    settings = validate_sampling_plan(plan)
    if not _is_int(defectives) or defectives < 0:
        raise ValueError("defectives must be a non-negative integer")
    if not _is_int(sample_size) or sample_size < 0:
        raise ValueError("sample_size must be a non-negative integer")
    if defectives > sample_size:
        raise ValueError(
            "%d defectives cannot come out of a sample of %d" % (defectives, sample_size)
        )
    return defectives <= settings["acceptance_number"]


def assess_sample_representativeness(case):
    """Run the clause 4.5.5 representativeness assessment over a drawn sample.

    case keys: parts (sequence of part records), optional sample (sequence of
    drawn part ids), optional defectives (integer), optional plan.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "parts" not in case:
        raise ValueError("case missing required key 'parts'")
    settings = validate_sampling_plan(case.get("plan"))
    records = validate_lot(case["parts"])
    lot_size = len(records)
    strata = stratify_lot(records)
    sizes = stratum_sizes(strata)
    needed = required_sample_size(lot_size, settings)
    drawn_ids = case.get("sample") or []
    mapped = map_drawn_units(strata, drawn_ids)
    counts = mapped["counts"]
    drawn = mapped["drawn"]
    allocation = allocate_sample(sizes, needed)
    shortfalls = allocation_shortfalls(allocation, counts)
    defectives = case.get("defectives", 0)
    within_acceptance = evaluate_acceptance_number(defectives, len(drawn), settings)

    findings = []
    if not within_acceptance:
        findings.append(
            "%d defectives were found against an acceptance number of %d"
            % (defectives, settings["acceptance_number"])
        )
    undersized = len(drawn) < needed
    if undersized:
        findings.append(
            "%d units were drawn against the %d this lot size requires"
            % (len(drawn), needed)
        )
    unreached = sorted(key for key, value in counts.items() if value == 0)
    if settings["require_every_stratum_drawn"] and unreached:
        for key in unreached:
            findings.append(
                "stratum %s received no unit; the sample cannot speak for it" % (key,)
            )
    skewed = sorted(
        key
        for key, gap in shortfalls.items()
        if gap > settings["max_allocation_shortfall_units"]
    )
    for key in skewed:
        findings.append(
            "stratum %s is %d units below its allocation of %d"
            % (key, shortfalls[key], allocation[key])
        )

    if not within_acceptance:
        verdict = LOT_REJECTED_ON_DEFECTIVES
    elif undersized:
        verdict = SAMPLE_UNDERSIZED
    elif settings["require_every_stratum_drawn"] and unreached:
        verdict = STRATUM_UNREPRESENTED
    elif skewed:
        verdict = ALLOCATION_SKEWED
    else:
        verdict = REPRESENTATIVE_SAMPLE

    return {
        "verdict": verdict,
        "lot_size": lot_size,
        "stratum_count": len(strata),
        "strata": {key: list(ids) for key, ids in strata.items()},
        "stratum_sizes": sizes,
        "required_sample_size": needed,
        "sample_size": len(drawn),
        "allocation": allocation,
        "drawn_per_stratum": counts,
        "allocation_shortfalls": shortfalls,
        "unreached_strata": unreached if settings["require_every_stratum_drawn"] else [],
        "skewed_strata": skewed,
        "stratum_coverage_fraction": stratum_coverage_fraction(counts),
        "largest_stratum_share": largest_stratum_share(sizes, lot_size),
        "defectives": defectives,
        "within_acceptance_number": within_acceptance,
        "representative": verdict == REPRESENTATIVE_SAMPLE,
        "findings": findings,
    }

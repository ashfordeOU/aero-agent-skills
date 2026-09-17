"""Composition of the class 3 radiation test sample set.

Anchor: ECSS-Q-ST-60C clause 6.5.5 (composing the class 3 radiation test
sample set in line with the radiation standard). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the flight population and group it on date code, because at this class
   the delivery is rarely one diffusion lot and the date code is the only axis
   the population can honestly be split on.
2. Size the sample set in integer arithmetic from the test method, the number
   of bias conditions it is run under, and the number of groups, so a wider
   population costs more specimens rather than the same ones spread thinner.
3. Split the set into irradiated, control and spare roles, with a control per
   group so a shift can be separated from a group difference.
4. Measure every offered specimen against the flight reference on the
   uniformity axes, and reject a specimen that is not the same part from the
   same manufacturer in the same package.
5. Check the drawn specimens reach every group, and both ends of the date-code
   window in particular, since the ends are where the spread shows.
6. Limit the population the result may be written to. A result reaches the
   units whose group was actually represented in the beam, and no further.
"""

__all__ = [
    "RADIATION_TEST_METHODS",
    "SPECIMEN_ROLES",
    "UNIFORMITY_AXES",
    "RESULT_SCOPES",
    "PER_GROUP_IRRADIATED_MINIMUM",
    "parse_date_code",
    "validate_bias_conditions",
    "population_groups",
    "group_codes",
    "required_sample_size",
    "role_counts",
    "specimen_axis_mismatches",
    "off_reference_specimens",
    "group_gaps",
    "window_endpoints_covered",
    "supported_population",
    "population_coverage",
    "assess_class_3_sample_set",
]

# What each radiation test method costs in specimens before the population is
# taken into account. 'scales_with_bias' says whether the irradiated count is
# consumed once per bias condition or once in total.
RADIATION_TEST_METHODS = {
    "total-ionising-dose": {
        "base_irradiated": 10,
        "base_controls": 2,
        "base_spares": 2,
        "scales_with_bias": True,
    },
    "displacement-damage": {
        "base_irradiated": 8,
        "base_controls": 2,
        "base_spares": 2,
        "scales_with_bias": False,
    },
    "single-event-effects": {
        "base_irradiated": 4,
        "base_controls": 1,
        "base_spares": 1,
        "scales_with_bias": True,
    },
}

SPECIMEN_ROLES = ("irradiated", "control", "spare")

# Axes a specimen has to share with the flight reference to stand for it.
UNIFORMITY_AXES = ("part_number", "manufacturer", "package_code")

# How far the result may be written, narrowest first.
RESULT_SCOPES = (
    "no-population",
    "represented-groups-only",
    "whole-flight-population",
)

# Irradiated specimens owed by every date-code group present in the population.
PER_GROUP_IRRADIATED_MINIMUM = 2


def parse_date_code(code):
    """Return a four-digit YYWW date code as an ordered (year, week) pair."""
    if not isinstance(code, str):
        raise ValueError("date code must be a string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date code must be four digits YYWW, got %r" % (code,))
    year = 2000 + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date code week must be 1-53, got %r" % (code,))
    return (year, week)


def validate_bias_conditions(bias_conditions):
    """Return the number of bias conditions, which is at least one."""
    if (
        not isinstance(bias_conditions, int)
        or isinstance(bias_conditions, bool)
        or bias_conditions < 1
    ):
        raise ValueError(
            "bias_conditions must be an integer of at least 1, got %r"
            % (bias_conditions,)
        )
    return bias_conditions


def _text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _key(value):
    text = _text(value)
    return text.upper() if text is not None else None


def _check_unit(unit, label):
    if not isinstance(unit, dict):
        raise ValueError("%s must be a mapping" % label)
    for axis in UNIFORMITY_AXES:
        if _text(unit.get(axis)) is None:
            raise ValueError("%s['%s'] must be a non-empty string" % (label, axis))
    code = _text(unit.get("date_code"))
    if code is None:
        raise ValueError("%s['date_code'] must be a non-empty string" % label)
    parse_date_code(code)
    return unit


def population_groups(population):
    """Return how many flight units sit in each date-code group."""
    if not isinstance(population, (list, tuple)):
        raise ValueError("population must be a sequence of flight unit records")
    if not population:
        raise ValueError("population must hold at least one flight unit")
    groups = {}
    for index, unit in enumerate(population):
        _check_unit(unit, "population[%d]" % index)
        code = _text(unit["date_code"])
        groups[code] = groups.get(code, 0) + 1
    return groups


def group_codes(groups):
    """Return the date codes of a grouping, ordered oldest to newest."""
    if not isinstance(groups, dict):
        raise ValueError("groups must be a mapping of date code to count")
    if not groups:
        raise ValueError("groups must hold at least one date code")
    return tuple(sorted(groups, key=parse_date_code))


def required_sample_size(method, group_count, bias_conditions):
    """Return the specimen counts the set owes, by role, in integer arithmetic.

    The irradiated count is whichever is larger: what the method costs across
    its bias conditions, or the per-group floor across the whole population. A
    population spread over more date codes therefore costs more specimens, not
    the same specimens spread thinner. One control is owed per group, so a
    shift can be separated from a difference between groups.
    """
    if method not in RADIATION_TEST_METHODS:
        raise ValueError(
            "method must be one of %s, got %r" % (sorted(RADIATION_TEST_METHODS), method)
        )
    if not isinstance(group_count, int) or isinstance(group_count, bool) or group_count < 1:
        raise ValueError("group_count must be an integer of at least 1")
    conditions = validate_bias_conditions(bias_conditions)
    spec = RADIATION_TEST_METHODS[method]
    irradiated = spec["base_irradiated"] * (conditions if spec["scales_with_bias"] else 1)
    floor = PER_GROUP_IRRADIATED_MINIMUM * group_count
    if floor > irradiated:
        irradiated = floor
    controls = spec["base_controls"]
    if group_count > controls:
        controls = group_count
    spares = spec["base_spares"]
    return {
        "method": method,
        "bias_conditions": conditions,
        "group_count": group_count,
        "irradiated": irradiated,
        "control": controls,
        "spare": spares,
        "total": irradiated + controls + spares,
        "per_group_irradiated_minimum": PER_GROUP_IRRADIATED_MINIMUM,
    }


def role_counts(specimens):
    """Return how many offered specimens sit in each role."""
    if not isinstance(specimens, (list, tuple)):
        raise ValueError("specimens must be a sequence of specimen records")
    counts = {role: 0 for role in SPECIMEN_ROLES}
    seen = set()
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        if "specimen_id" not in specimen:
            raise ValueError("specimens[%d] missing required key 'specimen_id'" % index)
        identifier = _key(specimen["specimen_id"])
        if identifier is None:
            raise ValueError("specimens[%d]['specimen_id'] must be non-empty" % index)
        if identifier in seen:
            raise ValueError(
                "specimen %s is offered twice; one specimen fills one role"
                % _text(specimen["specimen_id"])
            )
        seen.add(identifier)
        role = specimen.get("role")
        if role not in SPECIMEN_ROLES:
            raise ValueError(
                "specimens[%d]['role'] must be one of %s, got %r"
                % (index, list(SPECIMEN_ROLES), role)
            )
        counts[role] += 1
    return counts


def specimen_axis_mismatches(specimen, reference):
    """Return the uniformity axes on which a specimen differs from the flight."""
    _check_unit(specimen, "specimen")
    _check_unit(reference, "reference")
    return tuple(
        axis for axis in UNIFORMITY_AXES if _key(specimen[axis]) != _key(reference[axis])
    )


def off_reference_specimens(specimens, reference):
    """Return the offered specimens that cannot stand for the flight parts."""
    if not isinstance(specimens, (list, tuple)):
        raise ValueError("specimens must be a sequence of specimen records")
    offenders = []
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        mismatched = specimen_axis_mismatches(specimen, reference)
        if mismatched:
            offenders.append(
                "specimen %s differs from the flight parts on %s"
                % (_text(specimen.get("specimen_id")) or "<unnamed>", ", ".join(mismatched))
            )
    return tuple(offenders)


def group_gaps(population_codes, specimens):
    """Return the date-code groups no irradiated specimen was drawn from."""
    if not isinstance(population_codes, (list, tuple)):
        raise ValueError("population_codes must be a sequence of date codes")
    if not isinstance(specimens, (list, tuple)):
        raise ValueError("specimens must be a sequence of specimen records")
    drawn = {}
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        if specimen.get("role") != "irradiated":
            continue
        code = _text(specimen.get("date_code"))
        if code is None:
            raise ValueError("specimens[%d]['date_code'] must be non-empty" % index)
        parse_date_code(code)
        drawn[code] = drawn.get(code, 0) + 1
    gaps = []
    for code in population_codes:
        if drawn.get(code, 0) < PER_GROUP_IRRADIATED_MINIMUM:
            gaps.append(code)
    return tuple(sorted(gaps, key=parse_date_code))


def window_endpoints_covered(population_codes, specimens):
    """Return whether the oldest and newest groups both reached the beam."""
    if not isinstance(population_codes, (list, tuple)) or not population_codes:
        raise ValueError("population_codes must be a non-empty sequence of date codes")
    ordered = sorted((_text(c) for c in population_codes), key=parse_date_code)
    drawn = set()
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        if specimen.get("role") != "irradiated":
            continue
        code = _text(specimen.get("date_code"))
        if code is not None:
            drawn.add(code)
    return {
        "oldest": ordered[0],
        "newest": ordered[-1],
        "oldest_covered": ordered[0] in drawn,
        "newest_covered": ordered[-1] in drawn,
        "both_covered": ordered[0] in drawn and ordered[-1] in drawn,
    }


def supported_population(population, specimens):
    """Return the flight units the result may be written to."""
    if not isinstance(population, (list, tuple)):
        raise ValueError("population must be a sequence of flight unit records")
    covered = set()
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            raise ValueError("specimens[%d] must be a mapping" % index)
        if specimen.get("role") != "irradiated":
            continue
        code = _text(specimen.get("date_code"))
        if code is not None:
            covered.add(code)
    reached = []
    for index, unit in enumerate(population):
        _check_unit(unit, "population[%d]" % index)
        if _text(unit["date_code"]) in covered:
            reached.append(_text(unit.get("unit_id")) or _text(unit["date_code"]))
    return tuple(reached)


def population_coverage(population, specimens):
    """Return the share of flight units the result reaches, exactly and as a float."""
    if not isinstance(population, (list, tuple)):
        raise ValueError("population must be a sequence of flight unit records")
    total = len(population)
    reached = len(supported_population(population, specimens))
    if total == 0:
        return {"numerator": 0, "denominator": 0, "fraction": 0.0}
    return {"numerator": reached, "denominator": total, "fraction": reached / total}


def assess_class_3_sample_set(method, bias_conditions, population, specimens, reference):
    """Run the full clause 6.5.5 composition assessment over one sample set."""
    groups = population_groups(population)
    codes = group_codes(groups)
    required = required_sample_size(method, len(codes), bias_conditions)
    offered = role_counts(specimens)
    _check_unit(reference, "reference")

    findings = list(off_reference_specimens(specimens, reference))

    shortfalls = {}
    for role in SPECIMEN_ROLES:
        gap = required[role] - offered[role]
        shortfalls[role] = gap if gap > 0 else 0
        if gap > 0:
            findings.append(
                "the set offers %d %s specimen(s) against the %d it owes"
                % (offered[role], role, required[role])
            )

    gaps = group_gaps(codes, specimens)
    for code in gaps:
        findings.append(
            "date-code group %s reached the beam with fewer than %d irradiated "
            "specimens, so nothing was measured that stands for it"
            % (code, PER_GROUP_IRRADIATED_MINIMUM)
        )

    endpoints = window_endpoints_covered(codes, specimens)
    if not endpoints["both_covered"]:
        findings.append(
            "the date-code window ends are not both in the beam (oldest %s covered: "
            "%s; newest %s covered: %s), and the ends are where the spread shows"
            % (
                endpoints["oldest"],
                endpoints["oldest_covered"],
                endpoints["newest"],
                endpoints["newest_covered"],
            )
        )

    coverage = population_coverage(population, specimens)
    if coverage["numerator"] == 0:
        scope = "no-population"
    elif coverage["numerator"] == coverage["denominator"] and not gaps:
        scope = "whole-flight-population"
    else:
        scope = "represented-groups-only"
    if scope != "whole-flight-population":
        findings.append(
            "the result may be written to %d of %d flight unit(s) only; the rest "
            "sit in groups nothing in the beam stands for"
            % (coverage["numerator"], coverage["denominator"])
        )

    return {
        "method": method,
        "bias_conditions": required["bias_conditions"],
        "groups": groups,
        "group_codes": codes,
        "required": required,
        "offered": offered,
        "shortfalls": shortfalls,
        "group_gaps": gaps,
        "window_endpoints": endpoints,
        "population_coverage": coverage,
        "result_scope": scope,
        "findings": findings,
        "composed": not findings,
    }

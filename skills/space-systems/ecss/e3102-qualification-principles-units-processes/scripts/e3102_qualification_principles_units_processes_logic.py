#!/usr/bin/env python3
"""Qualification units and process for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02 clause 4.4.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Two answers come out of this clause. Which qualification process the item
owes, and how many qualification units have to exist for that process to
be run. The first is decided by what has changed against the qualified
reference; the second is decided by how many build standards the
qualification has to cover and by how much hardware the programme
destroys on the way.

Change categories, most onerous first
    new-technology        a working principle or fluid with no precedent
    new-design            a design with no qualified predecessor
    performance-change    a qualified design changed where it performs
    source-change         the same design from a new maker or process
    scaled-within-range   the same design resized inside a qualified span
    identical             the qualified item, unchanged

Each category maps to one process. A life or burst test destroys the unit
it is run on, so it adds hardware rather than being absorbed by a unit
already in the count. A retained unit is not an extra unit: retention is
a duty on hardware the programme already built.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CHANGE_CATEGORIES = (
    "new-technology",
    "new-design",
    "performance-change",
    "source-change",
    "scaled-within-range",
    "identical",
)

FULL_QUALIFICATION = "full-qualification"
DELTA_QUALIFICATION = "delta-qualification"
SOURCE_REQUALIFICATION = "source-requalification"
QUALIFICATION_BY_SIMILARITY = "qualification-by-similarity"
QUALIFICATION_BY_HERITAGE = "qualification-by-heritage"

PROCESS_BY_CATEGORY = {
    "new-technology": FULL_QUALIFICATION,
    "new-design": FULL_QUALIFICATION,
    "performance-change": DELTA_QUALIFICATION,
    "source-change": SOURCE_REQUALIFICATION,
    "scaled-within-range": QUALIFICATION_BY_SIMILARITY,
    "identical": QUALIFICATION_BY_HERITAGE,
}

# Units the process cannot be run below, before build standards and
# destructive testing are counted.
MINIMUM_UNITS_BY_PROCESS = {
    FULL_QUALIFICATION: 2,
    DELTA_QUALIFICATION: 1,
    SOURCE_REQUALIFICATION: 1,
    QUALIFICATION_BY_SIMILARITY: 1,
    QUALIFICATION_BY_HERITAGE: 0,
}

# How many build standards one unit is allowed to speak for, by process.
# A full qualification proves one build standard per unit; a similarity
# case is allowed to bound several because the span itself is qualified.
CONFIGURATIONS_PER_UNIT_BY_PROCESS = {
    FULL_QUALIFICATION: 1,
    DELTA_QUALIFICATION: 2,
    SOURCE_REQUALIFICATION: 2,
    QUALIFICATION_BY_SIMILARITY: 4,
    QUALIFICATION_BY_HERITAGE: 0,
}

CHANGE_FLAGS = (
    "new_technology",
    "no_qualified_predecessor",
    "performance_affecting_change",
    "manufacturing_source_change",
    "resized_within_qualified_range",
)


def _require_int(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _ceil_div(numerator, denominator):
    """Integer ceiling division, so no float rounding enters a unit count."""
    if denominator <= 0:
        raise ValueError("denominator must be positive, got %r" % (denominator,))
    return -(-numerator // denominator)


def validate_change_declaration(declaration):
    """Check the change declaration names every flag with a boolean."""
    if not isinstance(declaration, dict):
        raise ValueError("change declaration must be a mapping, got %r" % (declaration,))
    missing = [flag for flag in CHANGE_FLAGS if flag not in declaration]
    if missing:
        raise ValueError(
            "change declaration is missing: %s" % ", ".join(sorted(missing))
        )
    for flag in CHANGE_FLAGS:
        _require_bool(flag, declaration[flag])
    unknown = sorted(set(declaration) - set(CHANGE_FLAGS))
    if unknown:
        raise ValueError("change declaration has unknown flags: %s" % ", ".join(unknown))
    return declaration


def categorize_change(declaration):
    """Reduce the declared changes to the single most onerous category."""
    validate_change_declaration(declaration)
    if declaration["new_technology"]:
        return "new-technology"
    if declaration["no_qualified_predecessor"]:
        return "new-design"
    if declaration["performance_affecting_change"]:
        return "performance-change"
    if declaration["manufacturing_source_change"]:
        return "source-change"
    if declaration["resized_within_qualified_range"]:
        return "scaled-within-range"
    return "identical"


def qualification_process(category):
    """Process the category obliges, with the evidence it has to carry."""
    _require_choice("category", category, CHANGE_CATEGORIES)
    process = PROCESS_BY_CATEGORY[category]
    return {
        "category": category,
        "process": process,
        "minimum_units": MINIMUM_UNITS_BY_PROCESS[process],
        "configurations_per_unit": CONFIGURATIONS_PER_UNIT_BY_PROCESS[process],
        "needs_new_hardware": process != QUALIFICATION_BY_HERITAGE,
    }


def units_for_build_standards(process, build_standards):
    """Units needed to cover the build standards, before destruction."""
    _require_choice("process", process, tuple(MINIMUM_UNITS_BY_PROCESS))
    count = _require_int("build_standards", build_standards, minimum=1)
    per_unit = CONFIGURATIONS_PER_UNIT_BY_PROCESS[process]
    if per_unit == 0:
        return 0
    return max(MINIMUM_UNITS_BY_PROCESS[process], _ceil_div(count, per_unit))


def required_units(process, build_standards, destructive_tests=0):
    """Total qualification units: coverage plus the hardware consumed.

    Each destructive test consumes the unit it is run on, so it adds a
    unit instead of sharing one already counted for coverage.
    """
    coverage = units_for_build_standards(process, build_standards)
    destroyed = _require_int("destructive_tests", destructive_tests, minimum=0)
    if coverage == 0:
        if destroyed:
            raise ValueError(
                "a heritage case builds no qualification unit, so it cannot "
                "run %d destructive test(s)" % destroyed
            )
        return 0
    return coverage + destroyed


def escalate_heritage_claim(claimed_process, category):
    """Refuse a heritage or similarity claim the declared change contradicts."""
    _require_choice("claimed_process", claimed_process, tuple(MINIMUM_UNITS_BY_PROCESS))
    _require_choice("category", category, CHANGE_CATEGORIES)
    obliged = PROCESS_BY_CATEGORY[category]
    order = (
        QUALIFICATION_BY_HERITAGE,
        QUALIFICATION_BY_SIMILARITY,
        SOURCE_REQUALIFICATION,
        DELTA_QUALIFICATION,
        FULL_QUALIFICATION,
    )
    findings = []
    if order.index(claimed_process) < order.index(obliged):
        findings.append(
            "a %s was claimed but the declared change is %s, which obliges a %s"
            % (claimed_process, category, obliged)
        )
    return {"process": obliged, "claimed": claimed_process, "findings": findings}


def plan_qualification(case):
    """Full clause 4.4.1 unit and process plan with an escalation verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    category = categorize_change(case.get("changes"))
    selection = qualification_process(category)
    obliged = selection["process"]
    findings = []
    claimed = case.get("claimed_process")
    if claimed is not None:
        escalation = escalate_heritage_claim(claimed, category)
        findings.extend(escalation["findings"])
    build_standards = _require_int(
        "build_standards", case.get("build_standards"), minimum=1
    )
    destructive = _require_int(
        "destructive_tests", case.get("destructive_tests", 0), minimum=0
    )
    if obliged == QUALIFICATION_BY_HERITAGE and destructive:
        findings.append(
            "%d destructive test(s) were planned on a heritage case that "
            "builds no qualification unit" % destructive
        )
        destructive = 0
    units = required_units(obliged, build_standards, destructive)
    retained = _require_bool("retain_unit", case.get("retain_unit", False))
    if retained and units == 0:
        findings.append(
            "a unit was marked for retention but a heritage case builds none"
        )
    if selection["needs_new_hardware"] and units < selection["minimum_units"]:
        findings.append(
            "the unit count fell below the %d unit floor for a %s"
            % (selection["minimum_units"], obliged)
        )
    return {
        "category": category,
        "process": obliged,
        "build_standards": build_standards,
        "destructive_tests": destructive,
        "coverage_units": units_for_build_standards(obliged, build_standards),
        "qualification_units": units,
        "retain_unit": retained,
        "findings": findings,
        "verdict": "plan-consistent" if not findings else "plan-escalated",
    }

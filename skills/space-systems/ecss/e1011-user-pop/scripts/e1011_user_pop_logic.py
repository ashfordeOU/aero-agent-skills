#!/usr/bin/env python3
"""ECSS-E-ST-10-11 §4.2.1.3 user population definition (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the human
factors standard requires the programme to identify all groups of people who
interact with the system, categorize each into a recognized population type
(crew, ground operator, maintainer), and establish capability ranges across
physical, cognitive, sensory, and training dimensions. A capability range is
a min/max pair for a given dimension; it is internally consistent only when
min <= max and both values fall within the established bounds for that
dimension. All three population types must appear in the set unless the
programme has explicitly descoped one. Design parameters must fall within the
corresponding population's capability range; a value outside that envelope is
a design mismatch. This module implements user-group categorization, capability-
range validation, population-level validation, design-parameter checking,
coverage completeness checking, and full population-set review. It does not
define mission-specific capability values or descoping rationale.
"""

POPULATION_TYPES = frozenset({"crew", "ground_operator", "maintainer"})

CAPABILITY_DIMENSIONS = frozenset(
    {
        "physical_reach_mm",
        "cognitive_load_rating",
        "visual_acuity_log_mar",
        "training_level",
    }
)

# Inclusive [min, max] bounds for each dimension derived from established
# human-factors engineering practice.
DIMENSION_BOUNDS = {
    "physical_reach_mm": (0.0, 3000.0),
    "cognitive_load_rating": (1.0, 10.0),
    "visual_acuity_log_mar": (-0.3, 2.0),
    "training_level": (1.0, 4.0),
}


def categorize_user_group(group_type):
    """Population type for a user group: one of POPULATION_TYPES.
    Raises ValueError for a group type outside the recognized set."""
    if group_type in POPULATION_TYPES:
        return group_type
    raise ValueError(
        "unrecognized user group type %r under E-ST-10-11 §4.2.1.3" % (group_type,)
    )


def validate_capability_range(dimension, range_min, range_max):
    """Violation list (empty if consistent) for one capability-range entry.

    Checks: dimension is recognized; range_min <= range_max; both values
    fall within the established bounds for the dimension. Does not mutate
    its arguments."""
    if dimension not in CAPABILITY_DIMENSIONS:
        return [{"issue": "unrecognized_dimension", "dimension": dimension}]
    violations = []
    if range_min > range_max:
        violations.append(
            {
                "issue": "inverted_range",
                "dimension": dimension,
                "range_min": range_min,
                "range_max": range_max,
            }
        )
    bounds = DIMENSION_BOUNDS[dimension]
    if range_min < bounds[0] or range_max > bounds[1]:
        violations.append(
            {
                "issue": "range_exceeds_dimension_bounds",
                "dimension": dimension,
                "range_min": range_min,
                "range_max": range_max,
                "bounds_min": bounds[0],
                "bounds_max": bounds[1],
            }
        )
    return violations


def validate_population(population):
    """Violation list (empty if valid) for one population dict.

    population: {"population_id": str, "type": str,
                 "capability_ranges": {"dimension": {"min": float, "max": float}}}
    Checks: type is recognized; every capability_range entry is internally
    consistent. Does not mutate population."""
    violations = []
    pop_id = population.get("population_id", "<unknown>")
    pop_type = population.get("type")
    if pop_type not in POPULATION_TYPES:
        violations.append(
            {
                "issue": "unrecognized_population_type",
                "population": pop_id,
                "type": pop_type,
            }
        )
    capability_ranges = population.get("capability_ranges", {})
    for dim, rng in capability_ranges.items():
        for v in validate_capability_range(dim, rng["min"], rng["max"]):
            violations.append(dict(v, population=pop_id))
    return violations


def check_design_parameter(design_value, capability_min, capability_max):
    """True when design_value falls within [capability_min, capability_max].
    Raises ValueError for an inverted capability range."""
    if capability_min > capability_max:
        raise ValueError(
            "capability_min (%r) must be <= capability_max (%r)"
            % (capability_min, capability_max)
        )
    return capability_min <= design_value <= capability_max


def population_coverage_check(populations, required_types=None):
    """List of types from required_types not covered by any entry in populations.

    populations: iterable of dicts with a "type" key.
    required_types: iterable of str (defaults to all POPULATION_TYPES).
    Returns a sorted list of missing type strings."""
    if required_types is None:
        required_types = POPULATION_TYPES
    covered = {p.get("type") for p in populations}
    return sorted(t for t in required_types if t not in covered)


def population_set_review(populations):
    """Full §4.2.1.3 review of a list of population dicts.

    Returns {"populations": [per-population violations],
             "coverage": [missing-type violations]}.
    Does not mutate populations."""
    pop_violations = []
    for pop in populations:
        pop_violations.extend(validate_population(pop))
    missing = population_coverage_check(populations)
    coverage_violations = [
        {"issue": "missing_population_type", "type": t} for t in missing
    ]
    return {"populations": pop_violations, "coverage": coverage_violations}


def is_population_set_compliant(review):
    """True when both lists in a population_set_review result are empty --
    the population set satisfies §4.2.1.3 for this assessment."""
    return all(len(v) == 0 for v in review.values())

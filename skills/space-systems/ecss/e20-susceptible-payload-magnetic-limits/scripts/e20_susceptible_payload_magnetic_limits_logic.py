#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.7.2 static magnetic field limits at
direct-current-sensitive payload units (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires a maximum static (direct
current) magnetic field to be established at payload units whose
performance is degraded by such a field, and requires the spacecraft
magnetic sources to be shown compatible with it. This module implements
the checkable part of that clause: categorization of a payload unit by
its direct-current magnetic susceptibility, selection of the allowable
static field at its reference point, reduction of every onboard source
to an equivalent magnetic dipole moment, inverse-cube propagation of
each dipole to the unit along its axial or equatorial direction,
worst-case or root-sum-square combination of the contributions, the
margined comparison against the allowable field, and the minimum
separation distance a source needs to respect that margined limit. It
does not model shielding materials, does not perform a magnetic-moment
compensation design, and does not cover alternating-field
susceptibility, which belongs to the radiated-susceptibility clauses.
"""

import math

# Magnetic constant divided by four pi, in tesla metre per ampere.
MU0_OVER_4PI_T_M_PER_A = 1.0e-7
TESLA_TO_NANOTESLA = 1.0e9

# Payload unit kinds grouped by how strongly a steady field degrades
# them. The grouping is the input to the allowable-field table below.
SUSCEPTIBILITY_BY_UNIT_KIND = {
    "science_magnetometer": "very_high",
    "fluxgate_sensor": "very_high",
    "atomic_frequency_standard": "high",
    "optically_pumped_sensor": "high",
    "electron_multiplier_detector": "high",
    "star_tracker_head": "moderate",
    "charged_particle_analyser": "moderate",
    "imaging_detector": "low",
    "wheel_drive_electronics": "low",
    "digital_processing_unit": "negligible",
}

# Default allowable static field at the unit reference point, in
# nanotesla, when the payload provider has not supplied a number.
DEFAULT_ALLOWABLE_STATIC_FIELD_NT = {
    "very_high": 1.0,
    "high": 10.0,
    "moderate": 100.0,
    "low": 1000.0,
    "negligible": 10000.0,
}

# Susceptibility groups for which an unanswered unit-specific limit is
# itself a finding rather than an acceptable default.
LIMIT_ON_RECORD_REQUIRED = frozenset({"very_high", "high", "moderate"})

# Source kinds whose dipole moment is taken directly from measurement.
MEASURED_MOMENT_SOURCE_KINDS = frozenset(
    {
        "permanent_magnet",
        "magnetorquer_remanence",
        "latching_relay",
        "soft_magnetic_remanence",
    }
)
# Source kinds whose dipole moment is derived from a circuit geometry.
LOOP_MOMENT_SOURCE_KINDS = frozenset({"current_loop", "harness_return_loop"})

# Field of a dipole at a given distance relative to its equatorial
# value: the axial direction is twice the equatorial one, and an
# unresolved orientation is treated axially.
ORIENTATION_FACTOR = {"axial": 2.0, "equatorial": 1.0, "worst_case": 2.0}

COMBINATION_RULES = frozenset({"worst_case", "root_sum_square"})

DEFAULT_DESIGN_MARGIN_FACTOR = 2.0

# Relative tolerance used to absorb floating-point representation error
# when a field or a distance lands exactly on its limit. It widens no
# engineering limit; it only stops a physically compliant equality from
# reading as a violation a few units in the last place over.
BOUNDARY_REL_TOL = 1e-9


def categorize_unit_susceptibility(unit_kind):
    """Direct-current magnetic susceptibility group of a payload unit
    kind: "very_high", "high", "moderate", "low" or "negligible".
    Raises ValueError for a unit kind that is not on the clause 6.3.7.2
    susceptibility list."""
    try:
        return SUSCEPTIBILITY_BY_UNIT_KIND[unit_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized payload unit kind %r under "
            "E-ST-20C clause 6.3.7.2" % (unit_kind,)
        )


def allowable_static_field_nt(susceptibility, declared_limit_nt=None):
    """Allowable static field at the unit reference point in nanotesla.
    A unit-specific limit supplied by the payload provider supersedes
    the susceptibility default. Raises ValueError for an unknown
    susceptibility group or a non-positive declared limit."""
    if susceptibility not in DEFAULT_ALLOWABLE_STATIC_FIELD_NT:
        raise ValueError(
            "unrecognized susceptibility group %r" % (susceptibility,)
        )
    if declared_limit_nt is None:
        return DEFAULT_ALLOWABLE_STATIC_FIELD_NT[susceptibility]
    if declared_limit_nt <= 0:
        raise ValueError("declared_limit_nt must be > 0")
    return float(declared_limit_nt)


def loop_dipole_moment(current_a, loop_area_m2, turns=1):
    """Equivalent dipole moment of a circuit loop in ampere square
    metres: turns times enclosed area times steady current. Raises
    ValueError for a negative area, a non-integer or non-positive turn
    count, or a current magnitude that is not finite."""
    if not isinstance(turns, int) or isinstance(turns, bool):
        raise ValueError("turns must be an integer")
    if turns <= 0:
        raise ValueError("turns must be >= 1")
    if loop_area_m2 < 0:
        raise ValueError("loop_area_m2 must be >= 0")
    if not math.isfinite(current_a):
        raise ValueError("current_a must be finite")
    return abs(current_a) * loop_area_m2 * turns


def source_dipole_moment(source):
    """Equivalent dipole moment in ampere square metres for one entry
    of the magnetic source inventory.

    source: {"kind": str, ...}. A measured-moment kind carries
    "dipole_moment_am2"; a loop kind carries "current_a",
    "loop_area_m2" and an optional "turns". Raises ValueError for an
    unrecognized kind, a missing measured moment or a negative moment.
    """
    kind = source.get("kind")
    if kind in MEASURED_MOMENT_SOURCE_KINDS:
        if "dipole_moment_am2" not in source:
            raise ValueError(
                "source kind %r requires 'dipole_moment_am2'" % (kind,)
            )
        moment = source["dipole_moment_am2"]
        if moment is None:
            raise ValueError(
                "source kind %r has no measured dipole moment on record"
                % (kind,)
            )
        if moment < 0:
            raise ValueError("dipole_moment_am2 must be >= 0")
        return float(moment)
    if kind in LOOP_MOMENT_SOURCE_KINDS:
        return loop_dipole_moment(
            source["current_a"],
            source["loop_area_m2"],
            source.get("turns", 1),
        )
    raise ValueError(
        "unrecognized magnetic source kind %r under "
        "E-ST-20C clause 6.3.7.2" % (kind,)
    )


def dipole_static_field_nt(moment_am2, distance_m, orientation="worst_case"):
    """Static field in nanotesla produced by a dipole at a distance,
    falling with the cube of that distance. The axial direction gives
    twice the equatorial value; an unresolved orientation is treated
    axially. Raises ValueError for a negative moment, a non-positive
    distance or an unrecognized orientation."""
    if moment_am2 < 0:
        raise ValueError("moment_am2 must be >= 0")
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    try:
        factor = ORIENTATION_FACTOR[orientation]
    except (KeyError, TypeError):
        raise ValueError("unrecognized orientation %r" % (orientation,))
    field_t = (
        MU0_OVER_4PI_T_M_PER_A * factor * moment_am2 / (distance_m ** 3)
    )
    return field_t * TESLA_TO_NANOTESLA


def combine_field_contributions(contributions_nt, combination="worst_case"):
    """Combined static field in nanotesla from a sequence of individual
    contributions. "worst_case" sums them directly (no orientation
    knowledge); "root_sum_square" combines independent, randomly
    oriented sources. An empty sequence gives zero. Raises ValueError
    for an unrecognized rule or a negative contribution."""
    if combination not in COMBINATION_RULES:
        raise ValueError("unrecognized combination rule %r" % (combination,))
    total_squared = 0.0
    total = 0.0
    for value in contributions_nt:
        if value < 0:
            raise ValueError("field contributions must be >= 0")
        total += value
        total_squared += value * value
    if combination == "worst_case":
        return total
    return math.sqrt(total_squared)


def margined_field_limit_nt(limit_nt, margin_factor=DEFAULT_DESIGN_MARGIN_FACTOR):
    """Target field the assessment must meet: the allowable field
    divided by the required design margin factor. Raises ValueError for
    a non-positive limit or a margin factor below one."""
    if limit_nt <= 0:
        raise ValueError("limit_nt must be > 0")
    if margin_factor < 1.0:
        raise ValueError("margin_factor must be >= 1.0")
    return limit_nt / margin_factor


def minimum_separation_distance_m(
    moment_am2, target_field_nt, orientation="worst_case"
):
    """Smallest distance in metres at which a dipole's static field is
    at or below the target field. A zero moment needs no separation.
    Raises ValueError for a negative moment, a non-positive target
    field or an unrecognized orientation."""
    if moment_am2 < 0:
        raise ValueError("moment_am2 must be >= 0")
    if target_field_nt <= 0:
        raise ValueError("target_field_nt must be > 0")
    try:
        factor = ORIENTATION_FACTOR[orientation]
    except (KeyError, TypeError):
        raise ValueError("unrecognized orientation %r" % (orientation,))
    if moment_am2 == 0:
        return 0.0
    target_field_t = target_field_nt / TESLA_TO_NANOTESLA
    return (
        MU0_OVER_4PI_T_M_PER_A * factor * moment_am2 / target_field_t
    ) ** (1.0 / 3.0)


def _exceeds(value, limit):
    """True when value is above limit by more than floating-point
    representation error. A value that only differs from the limit in
    the last few bits is treated as sitting on the limit, which is
    compliant."""
    if value <= limit:
        return False
    return not math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def _falls_short(value, limit):
    """True when value is below limit by more than floating-point
    representation error."""
    if value >= limit:
        return False
    return not math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def field_margin_findings(
    unit_id, field_nt, limit_nt, margin_factor=DEFAULT_DESIGN_MARGIN_FACTOR
):
    """Findings (empty when acceptable) for a combined static field
    against the margined allowable limit. Raises ValueError through
    margined_field_limit_nt for a bad limit or margin, or for a
    negative field."""
    if field_nt < 0:
        raise ValueError("field_nt must be >= 0")
    target_nt = margined_field_limit_nt(limit_nt, margin_factor)
    if _exceeds(field_nt, target_nt):
        return [
            {
                "issue": "static_field_exceeds_margined_limit",
                "unit": unit_id,
                "field_nt": field_nt,
                "target_nt": target_nt,
                "allowable_nt": limit_nt,
                "margin_factor": margin_factor,
            }
        ]
    return []


def separation_findings(unit_id, sources, target_field_nt):
    """Findings (empty when acceptable) for sources mounted closer than
    the separation distance their own dipole moment requires against
    the margined target field. Raises ValueError through the helpers
    for a bad source entry, distance or target field."""
    findings = []
    for source in sources:
        moment_am2 = source_dipole_moment(source)
        distance_m = source["distance_m"]
        if distance_m <= 0:
            raise ValueError("distance_m must be > 0")
        orientation = source.get("orientation", "worst_case")
        required_m = minimum_separation_distance_m(
            moment_am2, target_field_nt, orientation
        )
        if _falls_short(distance_m, required_m):
            findings.append(
                {
                    "issue": "source_below_minimum_separation_distance",
                    "unit": unit_id,
                    "source": source.get("source_id"),
                    "distance_m": distance_m,
                    "required_distance_m": required_m,
                    "dipole_moment_am2": moment_am2,
                }
            )
    return findings


def unit_field_review(unit):
    """Full clause 6.3.7.2 review for one direct-current-sensitive
    payload unit.

    unit: {"unit_id": str, "unit_kind": str, "declared_limit_nt": float
    or None, "design_margin_factor": float (optional), "combination":
    "worst_case" or "root_sum_square" (optional), "sources": [source
    entries, each with "distance_m" and an optional "orientation" and
    "source_id"]}.

    Returns {"field": [...], "separation": [...], "record": [...]}.
    Raises ValueError through the helpers for an unrecognized unit or
    source kind or an invalid magnetic input. Does not mutate unit."""
    unit_id = unit["unit_id"]
    susceptibility = categorize_unit_susceptibility(unit["unit_kind"])
    declared_limit_nt = unit.get("declared_limit_nt")
    limit_nt = allowable_static_field_nt(susceptibility, declared_limit_nt)
    margin_factor = unit.get(
        "design_margin_factor", DEFAULT_DESIGN_MARGIN_FACTOR
    )
    combination = unit.get("combination", "worst_case")
    sources = list(unit.get("sources", []))
    contributions = [
        dipole_static_field_nt(
            source_dipole_moment(source),
            source["distance_m"],
            source.get("orientation", "worst_case"),
        )
        for source in sources
    ]
    total_nt = combine_field_contributions(contributions, combination)
    target_nt = margined_field_limit_nt(limit_nt, margin_factor)
    record = []
    if (
        susceptibility in LIMIT_ON_RECORD_REQUIRED
        and declared_limit_nt is None
        and sources
    ):
        record.append(
            {
                "issue": "unit_allowable_field_not_on_record",
                "unit": unit_id,
                "susceptibility": susceptibility,
                "default_used_nt": limit_nt,
            }
        )
    return {
        "field": field_margin_findings(
            unit_id, total_nt, limit_nt, margin_factor
        ),
        "separation": separation_findings(unit_id, sources, target_nt),
        "record": record,
    }


def is_unit_compliant(review):
    """True when every finding list in a unit_field_review result is
    empty -- the unit's static magnetic environment respects the
    clause 6.3.7.2 limit with margin and the limit itself is on
    record."""
    return all(len(findings) == 0 for findings in review.values())

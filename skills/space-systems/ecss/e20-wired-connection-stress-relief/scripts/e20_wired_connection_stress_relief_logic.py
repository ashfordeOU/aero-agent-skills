#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.5 wired connection strain relief
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires wired
connections to be provided with strain relief so that the wire itself,
and the termination at its end, do not carry excessive mechanical load.
The load in question is the quasi-static inertial load of the harness
mass between two restraint points, amplified by the launch design
acceleration and a design safety factor; it is reacted either by a
restraining provision (a clamp or saddle onto structure, a connector
backshell relief, a lacing tie to a support, a potted transition, a
bonded service loop) or -- if none is fitted -- by the conductor and
its termination. A soldered termination is a poor primary load path:
its pull-out capability is a fraction of the conductor's own, so a
connection whose only restraint is the joint is a finding regardless of
the number that comes out of the margin computation. Relief also has a
geometric side: the clamp or backshell must not force the bundle below
its minimum bend radius.

This module implements provision categorization, quasi-static inertial
load accounting, conductor and termination allowable derivation, load
margin, the maximum unsupported span an allowable permits, bend-radius
adequacy, load-path adequacy and the aggregated per-connection review.
It does not model dynamic amplification, vibration-induced fatigue
cycling, or the qualification of the relief hardware itself.
"""

STANDARD_GRAVITY_M_S2 = 9.80665

# Provisions that actually react the harness inertial load into
# structure before it reaches the wire and its termination.
RESTRAINING_RELIEF_PROVISIONS = frozenset(
    {
        "clamp_saddle",
        "connector_backshell_relief",
        "lacing_tie_to_support",
        "potted_transition",
        "bonded_service_loop",
    }
)

# Provisions recorded on a drawing that do not react load: the wire and
# its termination remain the load path.
NON_RESTRAINING_RELIEF_PROVISIONS = frozenset(
    {
        "none",
        "adhesive_dot_only",
        "free_hanging_loop",
        "sleeving_only",
    }
)

# Pull-out capability of a termination as a fraction of the conductor's
# own tensile allowable. Soldered and wrapped terminations sit well
# below the conductor; crimped and welded terminations approach it.
TERMINATION_STRENGTH_FRACTION = {
    "crimp_contact": 0.85,
    "resistance_weld": 0.90,
    "solder_cup": 0.35,
    "solder_lug": 0.30,
    "wire_wrap": 0.25,
}

# Terminations whose joint must not be left as the primary mechanical
# load path even when the computed margin is positive.
SOLDERED_TERMINATIONS = frozenset({"solder_cup", "solder_lug"})

# Below this applied load the connection is treated as carrying no
# meaningful mechanical load (self-weight of a short pigtail on orbit).
DE_MINIMIS_LOAD_N = 0.05

_REQUIRED_CONNECTION_KEYS = (
    "connection_id",
    "relief_provision",
    "termination_type",
    "conductor_area_mm2",
    "allowable_stress_mpa",
    "unsupported_span_m",
    "mass_per_metre_kg_m",
    "design_acceleration_g",
    "safety_factor",
)


def _require_keys(mapping, keys, what):
    """Raise ValueError naming the first missing key of a record."""
    for key in keys:
        if key not in mapping:
            raise ValueError("%s record is missing required key %r" % (what, key))


def categorize_relief_provision(provision):
    """Restraint category for a strain-relief provision:
    "restraining" or "non_restraining". Raises ValueError for a
    provision outside both known sets -- an unrecognized entry cannot be
    credited with reacting load under clause 4.2.5."""
    if provision in RESTRAINING_RELIEF_PROVISIONS:
        return "restraining"
    if provision in NON_RESTRAINING_RELIEF_PROVISIONS:
        return "non_restraining"
    raise ValueError(
        "unrecognized strain relief provision %r under "
        "E-ST-20C clause 4.2.5" % (provision,)
    )


def segment_inertial_load_n(
    segment_mass_kg, design_acceleration_g, safety_factor
):
    """Quasi-static tensile load (N) an unrestrained harness segment
    applies to the wire at its end: mass x acceleration x g0 x safety
    factor. Raises ValueError for a negative mass or acceleration, or a
    safety factor below 1.0 (a factor under unity relieves the design
    instead of covering it)."""
    if segment_mass_kg < 0:
        raise ValueError("segment_mass_kg must be >= 0")
    if design_acceleration_g < 0:
        raise ValueError("design_acceleration_g must be >= 0")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0")
    return (
        segment_mass_kg
        * design_acceleration_g
        * STANDARD_GRAVITY_M_S2
        * safety_factor
    )


def conductor_allowable_load_n(conductor_area_mm2, allowable_stress_mpa):
    """Tensile allowable (N) of the conductor: area (mm^2) x allowable
    stress (MPa), the two units multiplying directly to newtons. Raises
    ValueError for a non-positive area or stress."""
    if conductor_area_mm2 <= 0:
        raise ValueError("conductor_area_mm2 must be > 0")
    if allowable_stress_mpa <= 0:
        raise ValueError("allowable_stress_mpa must be > 0")
    return conductor_area_mm2 * allowable_stress_mpa


def termination_allowable_load_n(termination_type, conductor_allowable_n):
    """Pull-out allowable (N) of the termination: the conductor
    allowable scaled by the termination's strength fraction. Raises
    ValueError for an unrecognized termination type or a negative
    conductor allowable."""
    if termination_type not in TERMINATION_STRENGTH_FRACTION:
        raise ValueError("unrecognized termination type %r" % (termination_type,))
    if conductor_allowable_n < 0:
        raise ValueError("conductor_allowable_n must be >= 0")
    return TERMINATION_STRENGTH_FRACTION[termination_type] * conductor_allowable_n


def load_margin(allowable_load_n, applied_load_n):
    """Fractional margin of the allowable over the applied load:
    allowable / applied - 1. Returns positive infinity for a zero
    applied load. Raises ValueError for a negative allowable or applied
    load."""
    if allowable_load_n < 0:
        raise ValueError("allowable_load_n must be >= 0")
    if applied_load_n < 0:
        raise ValueError("applied_load_n must be >= 0")
    if applied_load_n == 0:
        return float("inf")
    return allowable_load_n / applied_load_n - 1.0


def max_unsupported_span_m(
    allowable_load_n, mass_per_metre_kg_m, design_acceleration_g, safety_factor
):
    """Longest unsupported harness span (m) whose inertial load stays
    within the allowable -- the clamp spacing the design must not
    exceed. Raises ValueError for a negative allowable, a non-positive
    mass per metre or acceleration, or a safety factor below 1.0."""
    if allowable_load_n < 0:
        raise ValueError("allowable_load_n must be >= 0")
    if mass_per_metre_kg_m <= 0:
        raise ValueError("mass_per_metre_kg_m must be > 0")
    if design_acceleration_g <= 0:
        raise ValueError("design_acceleration_g must be > 0")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0")
    load_per_metre = (
        mass_per_metre_kg_m
        * design_acceleration_g
        * STANDARD_GRAVITY_M_S2
        * safety_factor
    )
    return allowable_load_n / load_per_metre


def bend_radius_findings(
    connection_id, bend_radius_mm, bundle_outer_diameter_mm, min_bend_ratio
):
    """Finding list (empty when compliant) for the geometry the relief
    imposes on the bundle: the radius at the relief must be at least
    min_bend_ratio x outer diameter. Raises ValueError for a negative
    radius, a non-positive diameter or a non-positive ratio."""
    if bend_radius_mm < 0:
        raise ValueError("bend_radius_mm must be >= 0")
    if bundle_outer_diameter_mm <= 0:
        raise ValueError("bundle_outer_diameter_mm must be > 0")
    if min_bend_ratio <= 0:
        raise ValueError("min_bend_ratio must be > 0")
    required = min_bend_ratio * bundle_outer_diameter_mm
    if bend_radius_mm >= required:
        return []
    return [
        {
            "issue": "relief_forces_bend_below_minimum_radius",
            "connection": connection_id,
            "bend_radius_mm": bend_radius_mm,
            "required_radius_mm": required,
        }
    ]


def load_path_findings(
    connection_id, relief_provision, termination_type, applied_load_n
):
    """Finding list (empty when compliant) for the mechanical load path
    of one connection. A connection carrying more than a de-minimis load
    with no restraining provision leaves the wire itself as the load
    path; if its termination is soldered, the joint is additionally
    reported, because a solder joint is not a primary structural
    element whatever the computed margin says."""
    if applied_load_n < 0:
        raise ValueError("applied_load_n must be >= 0")
    if termination_type not in TERMINATION_STRENGTH_FRACTION:
        raise ValueError("unrecognized termination type %r" % (termination_type,))
    category = categorize_relief_provision(relief_provision)
    if category == "restraining" or applied_load_n <= DE_MINIMIS_LOAD_N:
        return []
    findings = [
        {
            "issue": "wire_carries_load_without_strain_relief",
            "connection": connection_id,
            "relief_provision": relief_provision,
            "applied_load_n": applied_load_n,
        }
    ]
    if termination_type in SOLDERED_TERMINATIONS:
        findings.append(
            {
                "issue": "soldered_joint_in_primary_load_path",
                "connection": connection_id,
                "termination_type": termination_type,
            }
        )
    return findings


def strength_findings(
    connection_id,
    applied_load_n,
    conductor_allowable_n,
    termination_allowable_n,
    required_margin,
):
    """Finding list (empty when compliant) for the strength of the wire
    and its termination against the applied load, each graded against
    the same required fractional margin. Raises ValueError for a
    required margin below zero."""
    if required_margin < 0:
        raise ValueError("required_margin must be >= 0")
    findings = []
    conductor_margin = load_margin(conductor_allowable_n, applied_load_n)
    if conductor_margin < required_margin:
        findings.append(
            {
                "issue": "conductor_tensile_capability_exceeded",
                "connection": connection_id,
                "margin": conductor_margin,
                "required_margin": required_margin,
            }
        )
    termination_margin = load_margin(termination_allowable_n, applied_load_n)
    if termination_margin < required_margin:
        findings.append(
            {
                "issue": "termination_pull_out_capability_exceeded",
                "connection": connection_id,
                "margin": termination_margin,
                "required_margin": required_margin,
            }
        )
    return findings


def review_connection(connection):
    """Full clause 4.2.5 review of one wired connection.

    connection: mapping with connection_id, relief_provision,
    termination_type, conductor_area_mm2, allowable_stress_mpa,
    unsupported_span_m, mass_per_metre_kg_m, design_acceleration_g,
    safety_factor, and the optional required_margin, bend_radius_mm,
    bundle_outer_diameter_mm and min_bend_ratio. Returns a mapping with
    the computed applied load, the two allowables, the maximum
    permissible unsupported span, and the load_path, strength, span and
    bend_radius finding lists. Raises ValueError for a missing key or an
    out-of-range input."""
    _require_keys(connection, _REQUIRED_CONNECTION_KEYS, "connection")
    connection_id = connection["connection_id"]
    span_m = connection["unsupported_span_m"]
    if span_m < 0:
        raise ValueError("unsupported_span_m must be >= 0")
    mass_per_metre = connection["mass_per_metre_kg_m"]
    if mass_per_metre <= 0:
        raise ValueError("mass_per_metre_kg_m must be > 0")
    acceleration = connection["design_acceleration_g"]
    safety_factor = connection["safety_factor"]
    applied = segment_inertial_load_n(
        span_m * mass_per_metre, acceleration, safety_factor
    )
    conductor_allowable = conductor_allowable_load_n(
        connection["conductor_area_mm2"], connection["allowable_stress_mpa"]
    )
    termination_allowable = termination_allowable_load_n(
        connection["termination_type"], conductor_allowable
    )
    required_margin = connection.get("required_margin", 0.0)
    permissible_span = max_unsupported_span_m(
        min(conductor_allowable, termination_allowable),
        mass_per_metre,
        acceleration,
        safety_factor,
    )
    span_issues = []
    if span_m > permissible_span:
        span_issues.append(
            {
                "issue": "unsupported_span_exceeds_limit",
                "connection": connection_id,
                "unsupported_span_m": span_m,
                "permissible_span_m": permissible_span,
            }
        )
    bend_issues = []
    if "bend_radius_mm" in connection:
        bend_issues = bend_radius_findings(
            connection_id,
            connection["bend_radius_mm"],
            connection.get("bundle_outer_diameter_mm", 1.0),
            connection.get("min_bend_ratio", 3.0),
        )
    return {
        "connection_id": connection_id,
        "applied_load_n": applied,
        "conductor_allowable_n": conductor_allowable,
        "termination_allowable_n": termination_allowable,
        "permissible_span_m": permissible_span,
        "load_path": load_path_findings(
            connection_id,
            connection["relief_provision"],
            connection["termination_type"],
            applied,
        ),
        "strength": strength_findings(
            connection_id,
            applied,
            conductor_allowable,
            termination_allowable,
            required_margin,
        ),
        "span": span_issues,
        "bend_radius": bend_issues,
    }


FINDING_GROUPS = ("load_path", "strength", "span", "bend_radius")


def is_connection_compliant(review):
    """True when every finding group in a review_connection result is
    empty -- the connection satisfies clause 4.2.5 for this
    assessment."""
    return all(len(review[group]) == 0 for group in FINDING_GROUPS)

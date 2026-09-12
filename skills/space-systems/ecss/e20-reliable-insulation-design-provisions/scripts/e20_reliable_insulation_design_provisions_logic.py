#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.1.2.3 reliable-insulation design provisions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires a line exposed
to a hazardous space environment -- meteoroid and debris impact above
all, and the comparable degradation, electrical-stress and wear
hazards -- to carry dedicated insulation provisions rather than to
rely on the bare wire specification. Provision style follows the
hazard family: impact hazards are countered by shield areal density or
by routing behind structure, material-degradation hazards by the
jacket material, electrical-stress hazards by a grounded overshield
and voltage derating, mechanical-wear hazards by chafe protection and
a temperature-rated insulation. "Reliable" insulation is a redundancy
statement: where a single barrier breach would itself be hazardous the
line needs two independent barriers.

This module implements hazard categorization, provision derivation and
gap detection, barrier-redundancy checking, dielectric withstand
margin, a monotonic impact-shield screening size, the routing standoff
check, and the aggregated per-line review. It does not model a
debris-environment flux, does not perform a ballistic-limit
qualification, and does not select a qualified wire part number.
"""

# --- Exposure hazard taxonomy -------------------------------------------

IMPACT_HAZARDS = frozenset({"meteoroid", "orbital_debris"})
MATERIAL_DEGRADATION_HAZARDS = frozenset(
    {"atomic_oxygen", "solar_uv", "charged_particle_dose"}
)
ELECTRICAL_STRESS_HAZARDS = frozenset({"plasma_charging", "corona", "arc_tracking"})
MECHANICAL_WEAR_HAZARDS = frozenset({"chafing", "thermal_cycling"})

HAZARD_FAMILIES = {
    "impact": IMPACT_HAZARDS,
    "material_degradation": MATERIAL_DEGRADATION_HAZARDS,
    "electrical_stress": ELECTRICAL_STRESS_HAZARDS,
    "mechanical_wear": MECHANICAL_WEAR_HAZARDS,
}

# Provisions each hazard demands of the installation design.
HAZARD_PROVISIONS = {
    "meteoroid": ("impact_shield", "routing_behind_structure"),
    "orbital_debris": ("impact_shield", "routing_behind_structure"),
    "atomic_oxygen": ("atomic_oxygen_resistant_jacket",),
    "solar_uv": ("uv_stable_jacket",),
    "charged_particle_dose": ("dose_rated_insulation",),
    "plasma_charging": ("grounded_overshield", "voltage_derating"),
    "corona": ("voltage_derating", "vented_insulation_build"),
    "arc_tracking": ("arc_resistant_insulation", "voltage_derating"),
    "chafing": ("chafe_protection", "stress_relief"),
    "thermal_cycling": ("temperature_rated_insulation", "stress_relief"),
}

# Rated voltage must exceed applied working voltage by this fraction of
# the applied voltage (1.0 => rated at least twice applied) unless the
# line carries its own project-set derating floor.
DEFAULT_MIN_DIELECTRIC_MARGIN = 1.0

# Screening coefficient of the impact sizing relation. Project-set; the
# relation is monotonic in each design-particle term and is used to
# rank and screen candidate shields, not to qualify one.
DEFAULT_IMPACT_SCREENING_COEFFICIENT = 0.6

# Barriers required when a single-barrier breach is itself hazardous.
REDUNDANT_BARRIER_COUNT = 2


def categorize_exposure_hazard(hazard):
    """Family of an exposure hazard: "impact", "material_degradation",
    "electrical_stress" or "mechanical_wear". Raises ValueError for a
    hazard name outside every known family, so an unrecognized hazard
    is rejected rather than silently dropped from the review."""
    for family, members in HAZARD_FAMILIES.items():
        if hazard in members:
            return family
    raise ValueError(
        "unrecognized exposure hazard %r under E-ST-20C clause 4.2.1.2.3"
        % (hazard,)
    )


def required_provisions(hazards):
    """Sorted tuple of the provisions demanded by an iterable of
    exposure hazards, deduplicated across hazards. Raises ValueError
    (via categorize_exposure_hazard) for an unrecognized hazard."""
    demanded = set()
    for hazard in hazards:
        categorize_exposure_hazard(hazard)
        demanded.update(HAZARD_PROVISIONS[hazard])
    return tuple(sorted(demanded))


def missing_provisions(hazards, implemented_provisions):
    """Sorted tuple of demanded provisions the design does not
    implement. implemented_provisions is any iterable of provision
    tokens; unknown tokens in it are ignored (a design may carry
    provisions beyond what these hazards demand)."""
    implemented = set(implemented_provisions)
    return tuple(
        provision
        for provision in required_provisions(hazards)
        if provision not in implemented
    )


def required_barrier_count(single_barrier_failure_hazardous):
    """Independent insulation barriers the line needs: two where the
    loss of one barrier would itself be hazardous, one otherwise."""
    if single_barrier_failure_hazardous:
        return REDUNDANT_BARRIER_COUNT
    return 1


def barrier_redundancy_violations(line_id, barrier_count, single_barrier_failure_hazardous):
    """Violation list (empty if compliant) for barrier redundancy on
    one line. Raises ValueError for a non-integer or negative barrier
    count -- a line with no insulation barrier at all is an input
    error, not a finding to be graded."""
    if isinstance(barrier_count, bool) or not isinstance(barrier_count, int):
        raise ValueError("barrier_count must be an int, got %r" % (barrier_count,))
    if barrier_count < 1:
        raise ValueError("barrier_count must be >= 1, got %d" % (barrier_count,))
    needed = required_barrier_count(single_barrier_failure_hazardous)
    if barrier_count < needed:
        return [
            {
                "issue": "insufficient_independent_insulation_barriers",
                "line": line_id,
                "barrier_count": barrier_count,
                "required_barrier_count": needed,
            }
        ]
    return []


def dielectric_margin(rated_voltage_v, applied_voltage_v):
    """Dielectric withstand margin as a fraction of the applied working
    voltage: (rated - applied) / applied. A margin of 1.0 means the
    insulation is rated at twice the applied voltage. Raises ValueError
    for a non-positive rated voltage or a non-positive applied
    voltage (an unpowered line has no margin to evaluate)."""
    if rated_voltage_v <= 0:
        raise ValueError("rated_voltage_v must be > 0, got %r" % (rated_voltage_v,))
    if applied_voltage_v <= 0:
        raise ValueError("applied_voltage_v must be > 0, got %r" % (applied_voltage_v,))
    return (rated_voltage_v - applied_voltage_v) / float(applied_voltage_v)


def dielectric_margin_violations(
    line_id, rated_voltage_v, applied_voltage_v, min_margin=DEFAULT_MIN_DIELECTRIC_MARGIN
):
    """Violation list (empty if compliant) for the dielectric withstand
    margin on one line. Raises ValueError for a negative derating
    floor or for the voltage errors of dielectric_margin."""
    if min_margin < 0:
        raise ValueError("min_margin must be >= 0, got %r" % (min_margin,))
    margin = dielectric_margin(rated_voltage_v, applied_voltage_v)
    if margin < min_margin:
        return [
            {
                "issue": "dielectric_withstand_margin_below_floor",
                "line": line_id,
                "margin": margin,
                "min_margin": min_margin,
            }
        ]
    return []


def required_shield_areal_density(
    particle_diameter_mm,
    particle_density_g_cm3,
    impact_velocity_km_s,
    coefficient=DEFAULT_IMPACT_SCREENING_COEFFICIENT,
):
    """Screening areal density (g/cm^2) a shield needs against the
    design particle. Monotonic screening relation:

        coefficient * d_cm**1.056 * rho**0.519 * v**(2/3)

    with d_cm the particle diameter in cm, rho its density in g/cm^3
    and v the impact velocity in km/s. Ranks and screens candidate
    shields; it is not a ballistic-limit qualification. Raises
    ValueError for a non-positive diameter, density, velocity or
    coefficient."""
    if particle_diameter_mm <= 0:
        raise ValueError(
            "particle_diameter_mm must be > 0, got %r" % (particle_diameter_mm,)
        )
    if particle_density_g_cm3 <= 0:
        raise ValueError(
            "particle_density_g_cm3 must be > 0, got %r" % (particle_density_g_cm3,)
        )
    if impact_velocity_km_s <= 0:
        raise ValueError(
            "impact_velocity_km_s must be > 0, got %r" % (impact_velocity_km_s,)
        )
    if coefficient <= 0:
        raise ValueError("coefficient must be > 0, got %r" % (coefficient,))
    diameter_cm = particle_diameter_mm / 10.0
    return (
        coefficient
        * diameter_cm ** 1.056
        * particle_density_g_cm3 ** 0.519
        * impact_velocity_km_s ** (2.0 / 3.0)
    )


def impact_protection_violations(line_id, provided_areal_density_g_cm2, required_g_cm2):
    """Violation list (empty if compliant) for impact protection on one
    line. provided_areal_density_g_cm2 None means the provision was
    never captured, which is itself a finding. Raises ValueError for a
    negative provided density or a non-positive requirement."""
    if required_g_cm2 <= 0:
        raise ValueError("required_g_cm2 must be > 0, got %r" % (required_g_cm2,))
    if provided_areal_density_g_cm2 is None:
        return [
            {
                "issue": "shield_areal_density_not_captured",
                "line": line_id,
                "required_g_cm2": required_g_cm2,
            }
        ]
    if provided_areal_density_g_cm2 < 0:
        raise ValueError(
            "provided_areal_density_g_cm2 must be >= 0, got %r"
            % (provided_areal_density_g_cm2,)
        )
    if provided_areal_density_g_cm2 < required_g_cm2:
        return [
            {
                "issue": "impact_shield_under_sized",
                "line": line_id,
                "provided_g_cm2": provided_areal_density_g_cm2,
                "required_g_cm2": required_g_cm2,
            }
        ]
    return []


def routing_standoff_violations(line_id, standoff_mm, min_standoff_mm):
    """Violation list (empty if compliant) for the routing standoff
    between the line and the exposed external surface. standoff_mm
    None means the provision was never captured (a finding). Raises
    ValueError for a negative standoff or a negative requirement."""
    if min_standoff_mm < 0:
        raise ValueError("min_standoff_mm must be >= 0, got %r" % (min_standoff_mm,))
    if standoff_mm is None:
        return [
            {
                "issue": "routing_standoff_not_captured",
                "line": line_id,
                "min_standoff_mm": min_standoff_mm,
            }
        ]
    if standoff_mm < 0:
        raise ValueError("standoff_mm must be >= 0, got %r" % (standoff_mm,))
    if standoff_mm < min_standoff_mm:
        return [
            {
                "issue": "routing_standoff_below_minimum",
                "line": line_id,
                "standoff_mm": standoff_mm,
                "min_standoff_mm": min_standoff_mm,
            }
        ]
    return []


def insulation_provision_review(line):
    """Full clause 4.2.1.2.3 provision review for one line.

    line: {"line_id": str, "hazards": [str, ...],
    "implemented_provisions": [str, ...], "barrier_count": int,
    "single_barrier_failure_hazardous": bool,
    "rated_voltage_v": float, "applied_voltage_v": float,
    "min_dielectric_margin": float (optional),
    "design_particle": {"diameter_mm", "density_g_cm3",
    "velocity_km_s"} (required when an impact hazard is present),
    "shield_areal_density_g_cm2": float | None,
    "routing_standoff_mm": float | None,
    "min_routing_standoff_mm": float (optional, default 0)}.

    Returns {"line_id", "hazard_families", "findings"}. Does not
    mutate the input. Raises ValueError for an unrecognized hazard, a
    bad barrier count, bad voltages, or a missing design particle on a
    line that carries an impact hazard."""
    line_id = line["line_id"]
    hazards = list(line.get("hazards", []))
    families = sorted({categorize_exposure_hazard(h) for h in hazards})
    findings = []

    for provision in missing_provisions(hazards, line.get("implemented_provisions", [])):
        findings.append(
            {
                "issue": "provision_not_implemented",
                "line": line_id,
                "provision": provision,
            }
        )

    findings.extend(
        barrier_redundancy_violations(
            line_id,
            line["barrier_count"],
            bool(line.get("single_barrier_failure_hazardous", False)),
        )
    )
    findings.extend(
        dielectric_margin_violations(
            line_id,
            line["rated_voltage_v"],
            line["applied_voltage_v"],
            line.get("min_dielectric_margin", DEFAULT_MIN_DIELECTRIC_MARGIN),
        )
    )

    if "impact" in families:
        particle = line.get("design_particle")
        if not particle:
            raise ValueError(
                "line %r carries an impact hazard but no design_particle" % (line_id,)
            )
        required = required_shield_areal_density(
            particle["diameter_mm"],
            particle["density_g_cm3"],
            particle["velocity_km_s"],
            particle.get("coefficient", DEFAULT_IMPACT_SCREENING_COEFFICIENT),
        )
        findings.extend(
            impact_protection_violations(
                line_id, line.get("shield_areal_density_g_cm2"), required
            )
        )

    min_standoff = line.get("min_routing_standoff_mm", 0)
    if min_standoff > 0:
        findings.extend(
            routing_standoff_violations(
                line_id, line.get("routing_standoff_mm"), min_standoff
            )
        )

    return {"line_id": line_id, "hazard_families": families, "findings": findings}


def is_provision_compliant(review):
    """True when a insulation_provision_review result carries no
    findings -- the line satisfies clause 4.2.1.2.3 for this review."""
    return len(review["findings"]) == 0

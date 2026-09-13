#!/usr/bin/env python3
"""Tether breakage and debris effects - ECSS-E-ST-20-06C clause 10.2.7.

Offline, deterministic, standard-library-only logic for the mechanical and
debris consequences of a deployed tether severing, whether the sever is
driven by an electrical cause (ohmic burnout of the conductor, erosion at a
sustained arc site) or by a mechanical one (tension overload, a particulate
strike that cuts the strand).

The procedure paraphrased from the clause anchor:

1. Screen every severance initiator against its own limit - conductor
   current-density against the fusing current-density, steady conductor
   temperature against the strand softening temperature, accumulated arc
   energy against the erosion threshold, tension against breaking strength,
   and the cumulative particulate-strike severance probability against the
   mission allowable.
2. Categorize the dominant initiator as the one with the largest exceedance;
   when no initiator reaches its limit the case stays uncategorized.
3. Take the sever as given and size what happens next: the strained strand
   releases its stored elastic energy, so the severed end recoils toward the
   host spacecraft at a speed and over a reach set by the release.
4. Inventory what the sever leaves in orbit - the length still attached to
   the host and the free length that becomes a separate object - and take
   each free object's decay lifetime from its area-to-mass ratio.
5. Judge the outcome: recoil reach against the keep-out standoff, decay
   lifetime against the disposal limit, released object count against the
   mission allowance.

No ECSS text is reproduced; the clause is cited as the anchor only.
"""

import math

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8
MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6378137.0

# Exponential-atmosphere anchor for the decay-lifetime estimate.
REFERENCE_ALTITUDE_KM = 400.0
REFERENCE_DENSITY_KG_M3 = 2.7e-12
SCALE_HEIGHT_KM = 60.0
DRAG_COEFFICIENT = 2.2

DEFAULT_DISPOSAL_LIMIT_YEARS = 25.0
SECONDS_PER_YEAR = 365.25 * 86400.0
MAX_ALTITUDE_KM = 2000.0

# Representation tolerance. Ratios and fourth-root balances are built from
# products and differences of floats, so a case sitting exactly on a limit can
# land a few units in the last place past it. The tolerance absorbs that
# representation error only; no engineering limit is ever widened by it.
REL_TOL = 1e-9

UNCATEGORIZED = "uncategorized"
OHMIC_BURNOUT = "ohmic-burnout"
THERMAL_SOFTENING = "thermal-softening"
ARC_EROSION = "arc-erosion"
MECHANICAL_OVERLOAD = "mechanical-overload"
PARTICULATE_SEVERANCE = "particulate-severance"

# Fixed priority, used only to break an exact tie between two initiators that
# reach their limits by the same ratio.
INITIATOR_PRIORITY = (
    OHMIC_BURNOUT,
    THERMAL_SOFTENING,
    ARC_EROSION,
    MECHANICAL_OVERLOAD,
    PARTICULATE_SEVERANCE,
)

REQUIRED_EVIDENCE_KEYS = (
    "current_density_a_mm2",
    "fusing_current_density_a_mm2",
    "conductor_temperature_k",
    "softening_temperature_k",
    "arc_energy_j",
    "arc_erosion_threshold_j",
    "tension_n",
    "breaking_strength_n",
    "severance_probability",
    "allowable_severance_probability",
)

REQUIRED_CASE_KEYS = (
    "length_m",
    "diameter_mm",
    "linear_density_kg_m",
    "conductor_area_mm2",
    "current_a",
    "fusing_current_density_a_mm2",
    "resistivity_ohm_m",
    "perimeter_mm",
    "emissivity",
    "environment_temperature_k",
    "softening_temperature_k",
    "tension_n",
    "breaking_strength_n",
    "axial_stiffness_n",
    "arc_energy_j",
    "arc_erosion_threshold_j",
    "particulate_flux_per_m2_s",
    "exposure_s",
    "allowable_severance_probability",
    "break_fraction",
    "standoff_m",
    "altitude_km",
)


# --------------------------------------------------------------------------
# input guards
# --------------------------------------------------------------------------


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _positive(name, value):
    value = _number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (name, value))
    return value


def _non_negative(name, value):
    value = _number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %g" % (name, value))
    return value


def _unit_interval(name, value, allow_zero=True):
    value = _number(name, value)
    low = 0.0 if allow_zero else 1e-12
    if value < low or value > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, value))
    return value


def _reaches_limit(ratio):
    """True when a demand/limit ratio reaches 1, absorbing representation error."""
    return ratio >= 1.0 or math.isclose(ratio, 1.0, rel_tol=REL_TOL, abs_tol=0.0)


def _exceeds_limit(value, limit):
    """True when value is genuinely over limit, not merely rounded over it."""
    if math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0):
        return False
    return value > limit


# --------------------------------------------------------------------------
# severance initiators
# --------------------------------------------------------------------------


def conductor_current_density(current_a, conductor_area_mm2):
    """Conductor current density (A/mm2) carried by the tether strand."""
    current = _positive("current_a", current_a)
    area = _positive("conductor_area_mm2", conductor_area_mm2)
    return current / area


def ohmic_burnout_margin(current_density_a_mm2, fusing_current_density_a_mm2):
    """Fusing current-density divided by the operating current-density."""
    operating = _positive("current_density_a_mm2", current_density_a_mm2)
    fusing = _positive("fusing_current_density_a_mm2", fusing_current_density_a_mm2)
    return fusing / operating


def equilibrium_conductor_temperature(current_a, resistivity_ohm_m,
                                      conductor_area_mm2, perimeter_mm,
                                      emissivity, environment_temperature_k):
    """Steady conductor temperature (K) where ohmic heating balances radiation."""
    current = _positive("current_a", current_a)
    resistivity = _positive("resistivity_ohm_m", resistivity_ohm_m)
    area_m2 = _positive("conductor_area_mm2", conductor_area_mm2) * 1.0e-6
    perimeter_m = _positive("perimeter_mm", perimeter_mm) * 1.0e-3
    emis = _unit_interval("emissivity", emissivity)
    if emis <= 0.0:
        raise ValueError("emissivity must be strictly positive to radiate heat")
    env = _positive("environment_temperature_k", environment_temperature_k)
    heat_per_length = current ** 2 * resistivity / area_m2
    radiator = emis * STEFAN_BOLTZMANN_W_M2_K4 * perimeter_m
    return (heat_per_length / radiator + env ** 4) ** 0.25


def severance_probability(particulate_flux_per_m2_s, exposed_area_m2, exposure_s):
    """Cumulative probability that a particulate strike cuts the strand."""
    flux = _non_negative("particulate_flux_per_m2_s", particulate_flux_per_m2_s)
    area = _positive("exposed_area_m2", exposed_area_m2)
    duration = _positive("exposure_s", exposure_s)
    expected_cuts = flux * area * duration
    return 1.0 - math.exp(-expected_cuts)


def exposed_strand_area(length_m, diameter_mm):
    """Projected area (m2) the deployed strand offers to a particulate flux."""
    length = _positive("length_m", length_m)
    diameter = _positive("diameter_mm", diameter_mm)
    return length * diameter * 1.0e-3


def categorize_failure_initiator(evidence):
    """Name the dominant severance initiator, or uncategorized when none reaches
    its limit.

    ``evidence`` carries one demand/limit pair per initiator. The initiator
    with the largest ratio at or above unity wins; an exact tie is broken by a
    fixed priority order so the result is deterministic.
    """
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping, got %r" % (type(evidence).__name__,))
    missing = [key for key in REQUIRED_EVIDENCE_KEYS if key not in evidence]
    if missing:
        raise ValueError(
            "evidence is missing required keys: %s" % ", ".join(sorted(missing))
        )
    ratios = {
        OHMIC_BURNOUT: (
            _positive("current_density_a_mm2", evidence["current_density_a_mm2"])
            / _positive("fusing_current_density_a_mm2",
                        evidence["fusing_current_density_a_mm2"])
        ),
        THERMAL_SOFTENING: (
            _positive("conductor_temperature_k", evidence["conductor_temperature_k"])
            / _positive("softening_temperature_k", evidence["softening_temperature_k"])
        ),
        ARC_EROSION: (
            _non_negative("arc_energy_j", evidence["arc_energy_j"])
            / _positive("arc_erosion_threshold_j", evidence["arc_erosion_threshold_j"])
        ),
        MECHANICAL_OVERLOAD: (
            _positive("tension_n", evidence["tension_n"])
            / _positive("breaking_strength_n", evidence["breaking_strength_n"])
        ),
        PARTICULATE_SEVERANCE: (
            _unit_interval("severance_probability", evidence["severance_probability"])
            / _unit_interval("allowable_severance_probability",
                             evidence["allowable_severance_probability"],
                             allow_zero=False)
        ),
    }
    reaching = [name for name in INITIATOR_PRIORITY if _reaches_limit(ratios[name])]
    if not reaching:
        return {"initiator": UNCATEGORIZED, "ratio": max(ratios.values()),
                "ratios": ratios}
    best = reaching[0]
    for name in reaching[1:]:
        if ratios[name] > ratios[best]:
            best = name
    return {"initiator": best, "ratio": ratios[best], "ratios": ratios}


# --------------------------------------------------------------------------
# post-sever mechanics
# --------------------------------------------------------------------------


def stored_strain_energy(tension_n, length_m, axial_stiffness_n):
    """Elastic energy (J) stored in the strained strand before the sever."""
    tension = _positive("tension_n", tension_n)
    length = _positive("length_m", length_m)
    stiffness = _positive("axial_stiffness_n", axial_stiffness_n)
    return tension ** 2 * length / (2.0 * stiffness)


def recoil_velocity(tension_n, length_m, axial_stiffness_n, segment_mass_kg):
    """Speed (m/s) the severed end reaches as the stored energy is released."""
    energy = stored_strain_energy(tension_n, length_m, axial_stiffness_n)
    mass = _positive("segment_mass_kg", segment_mass_kg)
    return math.sqrt(2.0 * energy / mass)


def recoil_reach(tension_n, length_m, axial_stiffness_n):
    """Elastic contraction (m) of the released strand - how far the end snaps back."""
    tension = _positive("tension_n", tension_n)
    length = _positive("length_m", length_m)
    stiffness = _positive("axial_stiffness_n", axial_stiffness_n)
    return tension * length / stiffness


def recoil_clears_standoff(reach_m, standoff_m):
    """True when the recoiling end stays outside the keep-out standoff."""
    reach = _non_negative("reach_m", reach_m)
    standoff = _positive("standoff_m", standoff_m)
    return not _exceeds_limit(reach, standoff)


# --------------------------------------------------------------------------
# debris inventory and decay
# --------------------------------------------------------------------------


def debris_segment_inventory(length_m, break_fraction, linear_density_kg_m,
                             released_end_mass_kg=0.0):
    """Split the severed tether into the attached and the free object."""
    length = _positive("length_m", length_m)
    fraction = _number("break_fraction", break_fraction)
    if fraction <= 0.0 or fraction >= 1.0:
        raise ValueError(
            "break_fraction must lie strictly inside (0, 1), got %g" % fraction
        )
    density = _positive("linear_density_kg_m", linear_density_kg_m)
    released = _non_negative("released_end_mass_kg", released_end_mass_kg)
    attached_length = length * fraction
    free_length = length - attached_length
    return {
        "attached_length_m": attached_length,
        "attached_mass_kg": attached_length * density,
        "free_length_m": free_length,
        "free_mass_kg": free_length * density + released,
        "released_object_count": 1 + (1 if released > 0.0 else 0),
    }


def area_to_mass_ratio(length_m, diameter_mm, mass_kg):
    """Projected area over mass (m2/kg) of a free tether segment."""
    area = exposed_strand_area(length_m, diameter_mm)
    mass = _positive("mass_kg", mass_kg)
    return area / mass


def orbital_decay_years(altitude_km, area_to_mass_m2_kg,
                        drag_coefficient=DRAG_COEFFICIENT):
    """Decay lifetime (years) of a circular orbit under exponential-atmosphere drag."""
    altitude = _positive("altitude_km", altitude_km)
    if altitude > MAX_ALTITUDE_KM:
        raise ValueError(
            "altitude_km %g is above the drag-decay regime (max %g)"
            % (altitude, MAX_ALTITUDE_KM)
        )
    ballistic_area = _positive("area_to_mass_m2_kg", area_to_mass_m2_kg)
    drag = _positive("drag_coefficient", drag_coefficient)
    density = REFERENCE_DENSITY_KG_M3 * math.exp(
        -(altitude - REFERENCE_ALTITUDE_KM) / SCALE_HEIGHT_KM
    )
    radius = EARTH_RADIUS_M + altitude * 1000.0
    decay_rate = drag * ballistic_area * density * math.sqrt(MU_EARTH_M3_S2 * radius)
    seconds = SCALE_HEIGHT_KM * 1000.0 / decay_rate
    return seconds / SECONDS_PER_YEAR


def disposal_compliant(lifetime_years, limit_years=DEFAULT_DISPOSAL_LIMIT_YEARS):
    """True when a free object clears the orbit inside the disposal limit."""
    lifetime = _non_negative("lifetime_years", lifetime_years)
    limit = _positive("limit_years", limit_years)
    return not _exceeds_limit(lifetime, limit)


# --------------------------------------------------------------------------
# aggregate assessment
# --------------------------------------------------------------------------


def _require_case(case):
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    missing = [key for key in REQUIRED_CASE_KEYS if key not in case]
    if missing:
        raise ValueError("case is missing required keys: %s" % ", ".join(sorted(missing)))
    return case


def assess_tether_breakage(case):
    """Full clause 10.2.7 breakage and debris assessment of one tether case."""
    _require_case(case)
    density = conductor_current_density(case["current_a"], case["conductor_area_mm2"])
    margin = ohmic_burnout_margin(density, case["fusing_current_density_a_mm2"])
    temperature = equilibrium_conductor_temperature(
        case["current_a"],
        case["resistivity_ohm_m"],
        case["conductor_area_mm2"],
        case["perimeter_mm"],
        case["emissivity"],
        case["environment_temperature_k"],
    )
    area = exposed_strand_area(case["length_m"], case["diameter_mm"])
    cut_probability = severance_probability(
        case["particulate_flux_per_m2_s"], area, case["exposure_s"]
    )
    verdict = categorize_failure_initiator(
        {
            "current_density_a_mm2": density,
            "fusing_current_density_a_mm2": case["fusing_current_density_a_mm2"],
            "conductor_temperature_k": temperature,
            "softening_temperature_k": case["softening_temperature_k"],
            "arc_energy_j": case["arc_energy_j"],
            "arc_erosion_threshold_j": case["arc_erosion_threshold_j"],
            "tension_n": case["tension_n"],
            "breaking_strength_n": case["breaking_strength_n"],
            "severance_probability": cut_probability,
            "allowable_severance_probability": case["allowable_severance_probability"],
        }
    )
    inventory = debris_segment_inventory(
        case["length_m"],
        case["break_fraction"],
        case["linear_density_kg_m"],
        case.get("released_end_mass_kg", 0.0),
    )
    reach = recoil_reach(case["tension_n"], case["length_m"], case["axial_stiffness_n"])
    speed = recoil_velocity(
        case["tension_n"],
        case["length_m"],
        case["axial_stiffness_n"],
        inventory["free_mass_kg"],
    )
    ballistic_area = area_to_mass_ratio(
        inventory["free_length_m"], case["diameter_mm"], inventory["free_mass_kg"]
    )
    lifetime = orbital_decay_years(case["altitude_km"], ballistic_area)
    limit_years = _positive(
        "disposal_limit_years",
        case.get("disposal_limit_years", DEFAULT_DISPOSAL_LIMIT_YEARS),
    )
    allowance = case.get("allowable_debris_objects", 1)
    if isinstance(allowance, bool) or not isinstance(allowance, int) or allowance < 1:
        raise ValueError(
            "allowable_debris_objects must be an int of at least 1, got %r" % (allowance,)
        )

    findings = []
    if verdict["initiator"] != UNCATEGORIZED:
        findings.append(
            "severance initiator %s reaches its limit at ratio %.3f"
            % (verdict["initiator"], verdict["ratio"])
        )
    if not _reaches_limit(margin):
        findings.append(
            "ohmic burnout margin %.3f is below unity" % margin
        )
    if not recoil_clears_standoff(reach, case["standoff_m"]):
        findings.append(
            "recoil reach %.3f m enters the %.3f m keep-out standoff"
            % (reach, case["standoff_m"])
        )
    if not disposal_compliant(lifetime, limit_years):
        findings.append(
            "free segment decay lifetime %.2f years exceeds the %.2f year disposal limit"
            % (lifetime, limit_years)
        )
    if inventory["released_object_count"] > allowance:
        findings.append(
            "sever releases %d objects, above the allowance of %d"
            % (inventory["released_object_count"], allowance)
        )
    return {
        "current_density_a_mm2": density,
        "ohmic_burnout_margin": margin,
        "conductor_temperature_k": temperature,
        "exposed_area_m2": area,
        "severance_probability": cut_probability,
        "initiator": verdict["initiator"],
        "initiator_ratios": verdict["ratios"],
        "inventory": inventory,
        "recoil_reach_m": reach,
        "recoil_velocity_m_s": speed,
        "free_area_to_mass_m2_kg": ballistic_area,
        "decay_lifetime_years": lifetime,
        "findings": findings,
        "compliant": not findings,
    }

#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.7.3 attitude-control-driven magnetic
cleanliness (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the spacecraft magnetic
requirements to be derived from the needs of the attitude control
system, and requires both the transient and the long-term variation of
the spacecraft magnetic properties to be limited. This module
implements the checkable part of that clause: a centred-dipole model of
the ambient geomagnetic field at an orbit altitude and magnetic
latitude, conversion of the control system's allowable magnetic
disturbance torque into an allowable spacecraft residual dipole moment,
the split of that allowance into steady, switching-transient and
long-term-drift shares, categorization of every contributor into
exactly one of those families, compounding of a drifting contributor to
end of life, the per-family budget check, and the worst-case momentum
accumulated over one orbit against the desaturation capacity. It does
not design a compensation magnet, does not run a full attitude
simulation, and does not model the field beyond the centred dipole.
"""

import math

EARTH_RADIUS_KM = 6371.0
# Equatorial surface field of the centred-dipole approximation, tesla.
EQUATORIAL_SURFACE_FIELD_T = 3.12e-5
# Earth gravitational parameter, cubic metres per second squared.
EARTH_MU_M3_PER_S2 = 3.986004418e14

MOMENT_CATEGORY_BY_CONTRIBUTOR_KIND = {
    "permanent_magnet": "steady",
    "ferromagnetic_bracket": "steady",
    "structure_remanent_magnetization": "steady",
    "soft_magnetic_core": "steady",
    "heater_switching_loop": "transient",
    "magnetorquer_duty_cycle": "transient",
    "latching_relay_state": "transient",
    "payload_mode_current_loop": "transient",
    "thruster_valve_solenoid": "transient",
    "solar_array_current_degradation": "long_term",
    "battery_current_drift": "long_term",
    "magnet_ageing_demagnetization": "long_term",
    "radiation_induced_remanence_drift": "long_term",
}

MOMENT_CATEGORIES = ("steady", "transient", "long_term")

DEFAULT_ALLOCATION_FRACTIONS = {
    "steady": 0.60,
    "transient": 0.25,
    "long_term": 0.15,
}

# Relative tolerance used to absorb floating-point representation error
# where a sum of allocations or of contributor moments lands exactly on
# its limit. It widens no engineering limit; it only stops a physically
# compliant equality from reading as a violation a few units in the
# last place over.
BOUNDARY_REL_TOL = 1e-9


def _exceeds(value, limit):
    """True when value is above limit by more than floating-point
    representation error. A value differing from the limit only in the
    last few bits is treated as sitting on the limit, which is
    compliant."""
    if value <= limit:
        return False
    return not math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def geomagnetic_field_t(altitude_km, magnetic_latitude_deg):
    """Ambient field magnitude in tesla from a centred-dipole model:
    the equatorial surface value scaled by the cube of the Earth radius
    over the orbit radius, times the latitude term that raises the
    field towards the poles. Raises ValueError for a negative altitude
    or a magnetic latitude outside the pole-to-pole range."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    if not -90.0 <= magnetic_latitude_deg <= 90.0:
        raise ValueError("magnetic_latitude_deg must be within -90..90")
    radius_ratio = EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km)
    sin_lat = math.sin(math.radians(magnetic_latitude_deg))
    latitude_term = math.sqrt(1.0 + 3.0 * sin_lat * sin_lat)
    return EQUATORIAL_SURFACE_FIELD_T * (radius_ratio ** 3) * latitude_term


def orbit_period_s(altitude_km):
    """Circular orbit period in seconds at an altitude above the mean
    Earth radius. Raises ValueError for a negative altitude."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    semi_major_axis_m = (EARTH_RADIUS_KM + altitude_km) * 1000.0
    return 2.0 * math.pi * math.sqrt(
        (semi_major_axis_m ** 3) / EARTH_MU_M3_PER_S2
    )


def magnetic_disturbance_torque_nm(moment_am2, field_t, alignment_factor=1.0):
    """Disturbance torque in newton metres from a residual dipole
    moment in an ambient field. Only the component perpendicular to the
    field produces torque; alignment_factor carries that geometry and
    defaults to the worst case of one. Raises ValueError for a negative
    moment, a non-positive field or an alignment factor outside the
    zero-to-one range."""
    if moment_am2 < 0:
        raise ValueError("moment_am2 must be >= 0")
    if field_t <= 0:
        raise ValueError("field_t must be > 0")
    if not 0.0 <= alignment_factor <= 1.0:
        raise ValueError("alignment_factor must be within 0..1")
    return moment_am2 * field_t * alignment_factor


def allowable_residual_dipole_am2(
    torque_allowance_nm, field_t, alignment_factor=1.0
):
    """Largest spacecraft residual dipole moment in ampere square
    metres whose disturbance torque stays inside the attitude control
    system's allowance. Raises ValueError for a non-positive torque
    allowance or field, or an alignment factor that is not strictly
    positive and at most one -- a zero alignment would make the
    allowance unbounded and is not a design case."""
    if torque_allowance_nm <= 0:
        raise ValueError("torque_allowance_nm must be > 0")
    if field_t <= 0:
        raise ValueError("field_t must be > 0")
    if not 0.0 < alignment_factor <= 1.0:
        raise ValueError("alignment_factor must be within (0..1]")
    return torque_allowance_nm / (field_t * alignment_factor)


def categorize_moment_contributor(contributor_kind):
    """Variation family of a magnetic contributor kind: "steady",
    "transient" or "long_term". Raises ValueError for a kind that is
    not a recognized clause 6.3.7.3 magnetic contributor."""
    try:
        return MOMENT_CATEGORY_BY_CONTRIBUTOR_KIND[contributor_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized magnetic contributor kind %r under "
            "E-ST-20C clause 6.3.7.3" % (contributor_kind,)
        )


def allocate_dipole_budget(allowable_am2, fractions=None):
    """Per-family share of the allowable residual dipole moment, in
    ampere square metres. fractions maps every variation family to its
    share and must be non-negative and sum to the whole allowance.
    Raises ValueError for a non-positive allowance, a missing or
    unknown family, a negative fraction, or a set that does not sum to
    one."""
    if allowable_am2 <= 0:
        raise ValueError("allowable_am2 must be > 0")
    if fractions is None:
        fractions = DEFAULT_ALLOCATION_FRACTIONS
    if set(fractions) != set(MOMENT_CATEGORIES):
        raise ValueError(
            "fractions must cover exactly %s" % (list(MOMENT_CATEGORIES),)
        )
    total = 0.0
    for category in MOMENT_CATEGORIES:
        share = fractions[category]
        if share < 0:
            raise ValueError("allocation fraction for %r must be >= 0" % category)
        total += share
    if not math.isclose(total, 1.0, rel_tol=BOUNDARY_REL_TOL, abs_tol=0.0):
        raise ValueError(
            "allocation fractions must sum to 1.0 (got %r)" % (total,)
        )
    return {
        category: allowable_am2 * fractions[category]
        for category in MOMENT_CATEGORIES
    }


def end_of_life_moment_am2(
    initial_am2, drift_fraction_per_year, mission_years
):
    """Contributor moment at end of life in ampere square metres: the
    delivered moment compounded by its fractional drift per year over
    the mission duration. Raises ValueError for a negative initial
    moment, a drift fraction at or below minus one (which would drive
    the moment non-positive), or a negative mission duration."""
    if initial_am2 < 0:
        raise ValueError("initial_am2 must be >= 0")
    if drift_fraction_per_year <= -1.0:
        raise ValueError("drift_fraction_per_year must be > -1.0")
    if mission_years < 0:
        raise ValueError("mission_years must be >= 0")
    return initial_am2 * ((1.0 + drift_fraction_per_year) ** mission_years)


def momentum_accumulation_nms(torque_nm, duration_s):
    """Worst-case momentum in newton metre seconds accumulated by a
    constant disturbance torque over a duration. Raises ValueError for
    a negative torque or duration."""
    if torque_nm < 0:
        raise ValueError("torque_nm must be >= 0")
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    return torque_nm * duration_s


def category_moment_sums(contributors, mission_years):
    """End-of-life moment per variation family, in ampere square
    metres, as {family: sum}. A long-term contributor is compounded by
    its declared drift; a steady or transient contributor is taken at
    its delivered value. Raises ValueError for an unrecognized
    contributor kind, a missing or negative moment, or a bad drift or
    mission duration. Does not mutate contributors."""
    sums = {category: 0.0 for category in MOMENT_CATEGORIES}
    for contributor in contributors:
        category = categorize_moment_contributor(contributor.get("kind"))
        moment_am2 = contributor.get("moment_am2")
        if moment_am2 is None:
            raise ValueError(
                "contributor %r has no moment_am2 on record"
                % (contributor.get("contributor_id"),)
            )
        if moment_am2 < 0:
            raise ValueError("moment_am2 must be >= 0")
        if category == "long_term":
            drift = contributor.get("drift_fraction_per_year")
            drift = 0.0 if drift is None else drift
            moment_am2 = end_of_life_moment_am2(
                moment_am2, drift, mission_years
            )
        sums[category] += moment_am2
    return sums


def budget_findings(spacecraft_id, sums, allocations):
    """Findings (empty when within budget) for each variation family
    whose end-of-life moment sum exceeds its allocated share. Raises
    ValueError when a family is missing from either mapping."""
    findings = []
    for category in MOMENT_CATEGORIES:
        if category not in sums or category not in allocations:
            raise ValueError("missing variation family %r" % (category,))
        if _exceeds(sums[category], allocations[category]):
            findings.append(
                {
                    "issue": "family_moment_exceeds_allocation",
                    "spacecraft": spacecraft_id,
                    "family": category,
                    "moment_am2": sums[category],
                    "allocation_am2": allocations[category],
                }
            )
    return findings


def momentum_findings(
    spacecraft_id,
    total_moment_am2,
    field_t,
    alignment_factor,
    period_s,
    capacity_nms,
):
    """Findings (empty when acceptable) for the momentum accumulated
    over one orbit by the total end-of-life residual moment. A capacity
    of None yields a record-style finding instead of a silent pass.
    Raises ValueError through the helpers for a bad moment, field,
    alignment factor or period, or for a non-positive capacity."""
    if capacity_nms is None:
        return [
            {
                "issue": "desaturation_capacity_not_on_record",
                "spacecraft": spacecraft_id,
            }
        ]
    if capacity_nms <= 0:
        raise ValueError("capacity_nms must be > 0")
    torque_nm = magnetic_disturbance_torque_nm(
        total_moment_am2, field_t, alignment_factor
    )
    accumulated_nms = momentum_accumulation_nms(torque_nm, period_s)
    if _exceeds(accumulated_nms, capacity_nms):
        return [
            {
                "issue": "orbit_momentum_exceeds_desaturation_capacity",
                "spacecraft": spacecraft_id,
                "accumulated_nms": accumulated_nms,
                "capacity_nms": capacity_nms,
                "torque_nm": torque_nm,
            }
        ]
    return []


def drift_record_findings(spacecraft_id, contributors):
    """Findings (empty when complete) for long-term contributors whose
    fractional drift per year is not on record. The assessment runs
    with a zero drift, which is exactly why the omission has to be
    reported. Raises ValueError for an unrecognized contributor kind."""
    findings = []
    for contributor in contributors:
        category = categorize_moment_contributor(contributor.get("kind"))
        if category != "long_term":
            continue
        if contributor.get("drift_fraction_per_year") is None:
            findings.append(
                {
                    "issue": "long_term_drift_rate_not_on_record",
                    "spacecraft": spacecraft_id,
                    "contributor": contributor.get("contributor_id"),
                    "kind": contributor.get("kind"),
                }
            )
    return findings


def cleanliness_review(spacecraft):
    """Full clause 6.3.7.3 review for one spacecraft magnetic
    cleanliness case.

    spacecraft: {"spacecraft_id": str, "altitude_km": float,
    "magnetic_latitude_deg": float, "torque_allowance_nm": float,
    "alignment_factor": float (optional, default 1.0),
    "allocation_fractions": {family: fraction} (optional),
    "mission_years": float, "momentum_capacity_nms": float or None,
    "contributors": [{"contributor_id", "kind", "moment_am2",
    "drift_fraction_per_year" (long-term only)}]}.

    Returns {"budget": [...], "momentum": [...], "record": [...]}.
    Raises ValueError through the helpers for an unrecognized
    contributor kind or an invalid orbit, torque, allocation or drift
    input. Does not mutate spacecraft."""
    spacecraft_id = spacecraft["spacecraft_id"]
    alignment_factor = spacecraft.get("alignment_factor", 1.0)
    mission_years = spacecraft["mission_years"]
    contributors = list(spacecraft.get("contributors", []))
    field_t = geomagnetic_field_t(
        spacecraft["altitude_km"], spacecraft["magnetic_latitude_deg"]
    )
    allowable_am2 = allowable_residual_dipole_am2(
        spacecraft["torque_allowance_nm"], field_t, alignment_factor
    )
    allocations = allocate_dipole_budget(
        allowable_am2, spacecraft.get("allocation_fractions")
    )
    sums = category_moment_sums(contributors, mission_years)
    total_moment_am2 = sum(sums[category] for category in MOMENT_CATEGORIES)
    return {
        "budget": budget_findings(spacecraft_id, sums, allocations),
        "momentum": momentum_findings(
            spacecraft_id,
            total_moment_am2,
            field_t,
            alignment_factor,
            orbit_period_s(spacecraft["altitude_km"]),
            spacecraft.get("momentum_capacity_nms"),
        ),
        "record": drift_record_findings(spacecraft_id, contributors),
    }


def is_cleanliness_compliant(review):
    """True when every finding list in a cleanliness_review result is
    empty -- the derived magnetic requirement is met by the steady,
    transient and long-term contributions and the accumulated momentum
    stays inside the desaturation capacity."""
    return all(len(findings) == 0 for findings in review.values())

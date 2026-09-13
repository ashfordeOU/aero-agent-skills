#!/usr/bin/env python3
"""Propulsion ground test limitations - ECSS-E-ST-20-06C clause 11.3.1.

Deterministic, offline, stdlib-only implementation of the clause 11.3.1
obligation: establish the vacuum-chamber effects of a ground firing of an
electric-propulsion thruster and their influence on the measured results.
Covers facility background pressure and pumping-speed sizing, residual-gas
charge-exchange enhancement, plume truncation by the chamber wall,
back-sputtered wall material, and the bookkeeping that decides whether every
declared effect is actually established.

Standard is cited as an anchor only; no normative text is reproduced.
"""

import math

BOLTZMANN_J_PER_K = 1.380649e-23
ELEMENTARY_CHARGE_C = 1.602176634e-19
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27

# Recognized facility effects and the family each belongs to.
CHAMBER_EFFECTS = {
    "elevated-background-pressure": "pressure-driven",
    "charge-exchange-enhancement": "pressure-driven",
    "residual-gas-ingestion": "pressure-driven",
    "back-sputtered-wall-material": "wall-material",
    "wall-erosion-contamination": "wall-material",
    "grounded-wall-potential-clamp": "electrical-boundary",
    "artificial-current-return": "electrical-boundary",
    "plume-truncation-by-wall": "geometric-truncation",
    "beam-dump-backscatter": "geometric-truncation",
    "beam-dump-thermal-reflux": "thermal-boundary",
}

# Families that a clause 11.3.1 campaign record has to cover. The thermal
# family is recognized but campaign-specific, so it is not required.
REQUIRED_EFFECT_FAMILIES = (
    "pressure-driven",
    "wall-material",
    "electrical-boundary",
    "geometric-truncation",
)

# Default agreed negligibility tolerance on an effect's relative influence.
DEFAULT_NEGLIGIBLE_INFLUENCE = 0.02

# Named tolerance that absorbs floating-point representation error on an
# exact-boundary comparison. It never widens an engineering limit.
BOUNDARY_REL_TOL = 1.0e-9


def _not_above(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def categorize_chamber_effect(effect_id):
    """Return the facility family of a chamber effect identifier."""
    if not isinstance(effect_id, str) or not effect_id.strip():
        raise ValueError("effect_id must be a non-empty string")
    key = effect_id.strip().lower()
    if key not in CHAMBER_EFFECTS:
        raise ValueError(
            "uncategorized chamber effect %r; expected one of %s"
            % (effect_id, sorted(CHAMBER_EFFECTS))
        )
    return CHAMBER_EFFECTS[key]


def propellant_throughput(mass_flow_kg_s, species_mass_amu, gas_temperature_k):
    """Gas throughput [Pa*m^3/s] of a propellant mass flow at a temperature."""
    if mass_flow_kg_s is None or mass_flow_kg_s < 0.0:
        raise ValueError("mass_flow_kg_s must be >= 0")
    if species_mass_amu is None or species_mass_amu <= 0.0:
        raise ValueError("species_mass_amu must be > 0")
    if gas_temperature_k is None or gas_temperature_k <= 0.0:
        raise ValueError("gas_temperature_k must be > 0")
    particle_mass = species_mass_amu * ATOMIC_MASS_UNIT_KG
    return mass_flow_kg_s * BOLTZMANN_J_PER_K * gas_temperature_k / particle_mass


def background_pressure(
    mass_flow_kg_s, pumping_speed_m3_s, species_mass_amu, gas_temperature_k
):
    """Operating-point chamber background pressure [Pa]."""
    if pumping_speed_m3_s is None or pumping_speed_m3_s <= 0.0:
        raise ValueError("pumping_speed_m3_s must be > 0")
    throughput = propellant_throughput(
        mass_flow_kg_s, species_mass_amu, gas_temperature_k
    )
    return throughput / pumping_speed_m3_s


def required_pumping_speed(
    mass_flow_kg_s, target_pressure_pa, species_mass_amu, gas_temperature_k
):
    """Pumping speed [m^3/s] a target background pressure demands."""
    if target_pressure_pa is None or target_pressure_pa <= 0.0:
        raise ValueError("target_pressure_pa must be > 0")
    throughput = propellant_throughput(
        mass_flow_kg_s, species_mass_amu, gas_temperature_k
    )
    return throughput / target_pressure_pa


def residual_gas_number_density(pressure_pa, gas_temperature_k):
    """Residual-gas number density [m^-3] at a chamber pressure."""
    if pressure_pa is None or pressure_pa < 0.0:
        raise ValueError("pressure_pa must be >= 0")
    if gas_temperature_k is None or gas_temperature_k <= 0.0:
        raise ValueError("gas_temperature_k must be > 0")
    return pressure_pa / (BOLTZMANN_J_PER_K * gas_temperature_k)


def charge_exchange_fraction(
    pressure_pa, path_length_m, cross_section_m2, gas_temperature_k
):
    """Fraction of beam ions undergoing charge exchange over a path length."""
    if path_length_m is None or path_length_m < 0.0:
        raise ValueError("path_length_m must be >= 0")
    if cross_section_m2 is None or cross_section_m2 <= 0.0:
        raise ValueError("cross_section_m2 must be > 0")
    density = residual_gas_number_density(pressure_pa, gas_temperature_k)
    return 1.0 - math.exp(-density * cross_section_m2 * path_length_m)


def wall_interception(axial_distance_m, chamber_radius_m, plume_half_angle_deg):
    """Decide whether the plume divergence cone is contained by the wall."""
    if axial_distance_m is None or axial_distance_m <= 0.0:
        raise ValueError("axial_distance_m must be > 0")
    if chamber_radius_m is None or chamber_radius_m <= 0.0:
        raise ValueError("chamber_radius_m must be > 0")
    if plume_half_angle_deg is None or not 0.0 < plume_half_angle_deg < 90.0:
        raise ValueError("plume_half_angle_deg must be within (0, 90)")
    plume_radius = axial_distance_m * math.tan(math.radians(plume_half_angle_deg))
    contained = _not_above(plume_radius, chamber_radius_m)
    return {
        "plume_radius_m": plume_radius,
        "chamber_radius_m": chamber_radius_m,
        "contained": contained,
        "clearance_m": chamber_radius_m - plume_radius,
        "truncated": not contained,
    }


def back_sputtered_mass_flux(
    beam_current_a,
    sputter_yield,
    target_mass_amu,
    chamber_radius_m,
    return_fraction,
):
    """Back-sputtered wall-material mass flux [kg/(m^2*s)] at the article."""
    if beam_current_a is None or beam_current_a < 0.0:
        raise ValueError("beam_current_a must be >= 0")
    if sputter_yield is None or sputter_yield < 0.0:
        raise ValueError("sputter_yield must be >= 0")
    if target_mass_amu is None or target_mass_amu <= 0.0:
        raise ValueError("target_mass_amu must be > 0")
    if chamber_radius_m is None or chamber_radius_m <= 0.0:
        raise ValueError("chamber_radius_m must be > 0")
    if return_fraction is None or not 0.0 <= return_fraction <= 1.0:
        raise ValueError("return_fraction must be within [0, 1]")
    ion_rate = beam_current_a / ELEMENTARY_CHARGE_C
    returned_atoms = ion_rate * sputter_yield * return_fraction
    area = 4.0 * math.pi * chamber_radius_m * chamber_radius_m
    return returned_atoms * target_mass_amu * ATOMIC_MASS_UNIT_KG / area


def facility_corrected_value(measured_value, correction_factors):
    """Apply facility correction factors to a measured quantity."""
    if measured_value is None:
        raise ValueError("measured_value is required")
    if not isinstance(correction_factors, (list, tuple)):
        raise ValueError("correction_factors must be a list of positive factors")
    corrected = float(measured_value)
    for factor in correction_factors:
        if not isinstance(factor, (int, float)) or isinstance(factor, bool):
            raise ValueError("correction factor %r is not numeric" % (factor,))
        if factor <= 0.0:
            raise ValueError("correction factor must be > 0, got %r" % (factor,))
        corrected *= float(factor)
    return corrected


def effect_is_established(
    effect_record, negligible_influence=DEFAULT_NEGLIGIBLE_INFLUENCE
):
    """Decide whether one declared chamber effect is established."""
    if not isinstance(effect_record, dict):
        raise ValueError("effect_record must be a mapping")
    if negligible_influence is None or negligible_influence < 0.0:
        raise ValueError("negligible_influence must be >= 0")
    family = categorize_chamber_effect(effect_record.get("id"))
    magnitude = effect_record.get("magnitude")
    quantity = effect_record.get("influenced_quantity")
    influence = effect_record.get("relative_influence")
    correction = effect_record.get("correction_factor")
    if magnitude is not None and (
        not isinstance(magnitude, (int, float)) or isinstance(magnitude, bool)
    ):
        raise ValueError("magnitude must be numeric when present")
    if influence is not None and (
        not isinstance(influence, (int, float)) or isinstance(influence, bool)
    ):
        raise ValueError("relative_influence must be numeric when present")
    if correction is not None and (
        not isinstance(correction, (int, float))
        or isinstance(correction, bool)
        or correction <= 0.0
    ):
        raise ValueError("correction_factor must be a positive number when present")
    result = {
        "effect_id": effect_record.get("id"),
        "family": family,
        "established": False,
        "disposition": None,
        "reason": None,
    }
    if magnitude is None:
        result["reason"] = "magnitude-not-established"
        return result
    if not isinstance(quantity, str) or not quantity.strip():
        result["reason"] = "influence-on-result-not-stated"
        return result
    if correction is not None:
        result["established"] = True
        result["disposition"] = "corrected"
        return result
    if influence is not None and _not_above(abs(influence), negligible_influence):
        result["established"] = True
        result["disposition"] = "negligible-within-tolerance"
        return result
    result["reason"] = "uncorrected-and-not-negligible"
    return result


def missing_effect_families(effects):
    """Required facility families with no declared effect covering them."""
    if not isinstance(effects, list):
        raise ValueError("effects must be a list")
    covered = set()
    for effect in effects:
        if not isinstance(effect, dict):
            raise ValueError("every effect must be a mapping")
        covered.add(categorize_chamber_effect(effect.get("id")))
    return [f for f in REQUIRED_EFFECT_FAMILIES if f not in covered]


def assess_ground_test_limitations(campaign, effects):
    """Aggregate clause 11.3.1 assessment of one ground firing campaign."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    if not isinstance(effects, list) or not effects:
        raise ValueError("effects must be a non-empty list")
    temperature = campaign.get("gas_temperature_k", 300.0)
    pressure = background_pressure(
        campaign.get("mass_flow_kg_s"),
        campaign.get("pumping_speed_m3_s"),
        campaign.get("species_mass_amu"),
        temperature,
    )
    limit = campaign.get("max_background_pressure_pa")
    if limit is None or limit <= 0.0:
        raise ValueError("campaign must declare a positive max_background_pressure_pa")
    pressure_ok = _not_above(pressure, limit)
    geometry = wall_interception(
        campaign.get("axial_distance_m"),
        campaign.get("chamber_radius_m"),
        campaign.get("plume_half_angle_deg"),
    )
    cex = charge_exchange_fraction(
        pressure,
        campaign.get("plume_path_length_m", campaign.get("axial_distance_m")),
        campaign.get("cex_cross_section_m2", 5.0e-19),
        temperature,
    )
    findings = []
    if not pressure_ok:
        findings.append(
            "background-pressure %.3e Pa exceeds the facility limit %.3e Pa; "
            "required pumping-speed is %.1f m^3/s"
            % (
                pressure,
                limit,
                required_pumping_speed(
                    campaign.get("mass_flow_kg_s"),
                    limit,
                    campaign.get("species_mass_amu"),
                    temperature,
                ),
            )
        )
    if geometry["truncated"]:
        findings.append(
            "plume-truncation: divergence cone reaches %.3f m against a "
            "chamber radius of %.3f m"
            % (geometry["plume_radius_m"], geometry["chamber_radius_m"])
        )
    tolerance = campaign.get("negligible_influence", DEFAULT_NEGLIGIBLE_INFLUENCE)
    records = []
    seen = set()
    for effect in effects:
        if not isinstance(effect, dict):
            raise ValueError("every effect must be a mapping")
        eid = effect.get("id")
        if eid in seen:
            raise ValueError("duplicate chamber effect id %r" % (eid,))
        seen.add(eid)
        record = effect_is_established(effect, tolerance)
        records.append(record)
        if not record["established"]:
            findings.append(
                "effect %s is not established: %s" % (eid, record["reason"])
            )
    for family in missing_effect_families(effects):
        findings.append("no declared effect covers the %s family" % family)
    corrections = [
        e["correction_factor"]
        for e in effects
        if e.get("correction_factor") is not None
    ]
    return {
        "background_pressure_pa": pressure,
        "background_pressure_within_limit": pressure_ok,
        "charge_exchange_fraction": cex,
        "geometry": geometry,
        "effects": records,
        "correction_factors": corrections,
        "findings": findings,
        "flight_representative": not findings,
    }

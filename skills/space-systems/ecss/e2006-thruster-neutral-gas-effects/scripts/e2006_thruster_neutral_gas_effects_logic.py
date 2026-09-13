#!/usr/bin/env python3
"""Thruster neutral gas effects - ECSS-E-ST-20-06C clause 11.2.5.

Deterministic, offline, stdlib-only implementation of the clause 11.2.5
evidence chain: categorize the neutral gas sources of an electric-propulsion
thruster, propagate their number-density to each high-voltage surface
(forward lobe plus the backflow branch behind the exit plane), convert the
summed density into a local gas pressure and an electron mean-free-path,
evaluate the Paschen breakdown voltage of every biased gap, derive the
ionized plasma density and decide whether a discharge can be sustained.

Standard is cited as an anchor only; no normative text is reproduced.
"""

import math

BOLTZMANN_J_PER_K = 1.380649e-23
ELEMENTARY_CHARGE_C = 1.602176634e-19
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

# Recognized neutral gas emission families of an electric-propulsion system.
GAS_SOURCE_FAMILIES = {
    "beam-directed-efflux": "accelerated-beam",
    "unionized-propellant": "discharge-chamber",
    "neutralizer-flow": "cathode-feed",
    "valve-leak": "feed-system",
}

# Paschen fit coefficients per gas: (a [1/(Pa*m)], b [V/(Pa*m)], gamma [-]).
# Tabulated engineering fits; gamma is the secondary-emission coefficient of
# the cathode-side surface material.
PASCHEN_COEFFICIENTS = {
    "xenon": (14.6, 350.0, 0.020),
    "krypton": (13.0, 320.0, 0.020),
    "argon": (11.0, 176.0, 0.020),
    "nitrogen": (9.0, 256.0, 0.025),
    "air": (11.25, 273.8, 0.010),
}

# Exit-plane backflow branch: peak fraction of the on-axis directionality and
# the angular decay constant behind the exit plane.
BACKFLOW_PEAK_FRACTION = 1.0e-3
BACKFLOW_ANGULAR_DECAY_DEG = 30.0

# Electron density that sustains a struck discharge once it exists [m^-3].
SUSTAINING_PLASMA_DENSITY_M3 = 1.0e14

# Named tolerance that absorbs floating-point representation error on an
# exact-boundary comparison. It never widens an engineering limit: a value
# that equals its limit to within this tolerance is treated as on the limit.
BOUNDARY_REL_TOL = 1.0e-9

_REQUIRED_SURFACE_GEOMETRY = ("id", "range_m", "off_axis_deg")
_EVIDENCE_FIELDS = ("gap_m", "applied_bias_v", "ionization_fraction")


def categorize_gas_source(source_type):
    """Return the emission family of a neutral gas source type."""
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("source_type must be a non-empty string")
    key = source_type.strip().lower()
    if key not in GAS_SOURCE_FAMILIES:
        raise ValueError(
            "uncategorized neutral gas source type %r; expected one of %s"
            % (source_type, sorted(GAS_SOURCE_FAMILIES))
        )
    return GAS_SOURCE_FAMILIES[key]


def emitted_particle_rate(mass_flow_kg_s, species_mass_amu):
    """Particles per second leaving a source of the given mass flow."""
    if mass_flow_kg_s is None or mass_flow_kg_s < 0.0:
        raise ValueError("mass_flow_kg_s must be >= 0")
    if species_mass_amu is None or species_mass_amu <= 0.0:
        raise ValueError("species_mass_amu must be > 0")
    return mass_flow_kg_s / (species_mass_amu * ATOMIC_MASS_UNIT_KG)


def directionality(off_axis_deg, divergence_exponent):
    """Normalized emission directionality [1/sr] at an off-axis angle.

    Ahead of the exit plane this is the cosine-power lobe normalized over the
    forward hemisphere. At and behind the exit plane the lobe is zero and the
    backflow branch takes over: a small named fraction of the on-axis value
    decaying exponentially with angle behind the plane.
    """
    if off_axis_deg is None or not 0.0 <= off_axis_deg <= 180.0:
        raise ValueError("off_axis_deg must be within [0, 180]")
    if divergence_exponent is None or divergence_exponent < 0.0:
        raise ValueError("divergence_exponent must be >= 0")
    peak = (divergence_exponent + 1.0) / (2.0 * math.pi)
    if off_axis_deg < 90.0:
        return peak * math.cos(math.radians(off_axis_deg)) ** divergence_exponent
    decay = (off_axis_deg - 90.0) / BACKFLOW_ANGULAR_DECAY_DEG
    return peak * BACKFLOW_PEAK_FRACTION * math.exp(-decay)


def plume_number_density(
    mass_flow_kg_s,
    species_mass_amu,
    exhaust_speed_m_s,
    range_m,
    off_axis_deg,
    divergence_exponent,
):
    """Neutral number density [m^-3] of one source at one field point."""
    if exhaust_speed_m_s is None or exhaust_speed_m_s <= 0.0:
        raise ValueError("exhaust_speed_m_s must be > 0")
    if range_m is None or range_m <= 0.0:
        raise ValueError("range_m must be > 0")
    rate = emitted_particle_rate(mass_flow_kg_s, species_mass_amu)
    lobe = directionality(off_axis_deg, divergence_exponent)
    return rate * lobe / (exhaust_speed_m_s * range_m * range_m)


def local_gas_pressure(number_density_m3, temperature_k):
    """Equivalent local gas pressure [Pa] of a neutral density."""
    if number_density_m3 is None or number_density_m3 < 0.0:
        raise ValueError("number_density_m3 must be >= 0")
    if temperature_k is None or temperature_k <= 0.0:
        raise ValueError("temperature_k must be > 0")
    return number_density_m3 * BOLTZMANN_J_PER_K * temperature_k


def electron_mean_free_path(number_density_m3, cross_section_m2):
    """Electron mean-free-path [m] in a neutral gas of the given density."""
    if number_density_m3 is None or number_density_m3 < 0.0:
        raise ValueError("number_density_m3 must be >= 0")
    if cross_section_m2 is None or cross_section_m2 <= 0.0:
        raise ValueError("cross_section_m2 must be > 0")
    if number_density_m3 == 0.0:
        return math.inf
    return 1.0 / (number_density_m3 * cross_section_m2)


def paschen_breakdown_voltage(pressure_pa, gap_m, gas):
    """Paschen breakdown voltage [V], or None below the Paschen minimum."""
    if not isinstance(gas, str) or not gas.strip():
        raise ValueError("gas must be a non-empty string")
    key = gas.strip().lower()
    if key not in PASCHEN_COEFFICIENTS:
        raise ValueError(
            "no Paschen fit for gas %r; expected one of %s"
            % (gas, sorted(PASCHEN_COEFFICIENTS))
        )
    if pressure_pa is None or pressure_pa < 0.0:
        raise ValueError("pressure_pa must be >= 0")
    if gap_m is None or gap_m <= 0.0:
        raise ValueError("gap_m must be > 0")
    a_coeff, b_coeff, gamma = PASCHEN_COEFFICIENTS[key]
    pd = pressure_pa * gap_m
    if pd <= 0.0:
        return None
    inner = math.log(1.0 + 1.0 / gamma)
    argument = a_coeff * pd / inner
    if argument <= 1.0:
        return None
    return b_coeff * pd / math.log(argument)


def ionized_plasma_density(number_density_m3, ionization_fraction):
    """Ionized plasma density [m^-3] from a neutral density and its fraction."""
    if number_density_m3 is None or number_density_m3 < 0.0:
        raise ValueError("number_density_m3 must be >= 0")
    if ionization_fraction is None or not 0.0 <= ionization_fraction <= 1.0:
        raise ValueError("ionization_fraction must be within [0, 1]")
    return number_density_m3 * ionization_fraction


def debye_length(plasma_density_m3, electron_temperature_ev):
    """Electron Debye length [m] of the derived plasma."""
    if plasma_density_m3 is None or plasma_density_m3 <= 0.0:
        raise ValueError("plasma_density_m3 must be > 0")
    if electron_temperature_ev is None or electron_temperature_ev <= 0.0:
        raise ValueError("electron_temperature_ev must be > 0")
    numerator = (
        VACUUM_PERMITTIVITY_F_PER_M
        * electron_temperature_ev
        * ELEMENTARY_CHARGE_C
    )
    denominator = plasma_density_m3 * ELEMENTARY_CHARGE_C ** 2
    return math.sqrt(numerator / denominator)


def _not_above(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def _validate_thruster(thruster):
    if not isinstance(thruster, dict):
        raise ValueError("thruster must be a mapping")
    propellant = thruster.get("propellant")
    if not isinstance(propellant, str) or propellant.strip().lower() not in (
        PASCHEN_COEFFICIENTS
    ):
        raise ValueError(
            "thruster propellant %r has no Paschen fit on record" % (propellant,)
        )
    sources = thruster.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("thruster must declare a non-empty 'sources' list")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("every source must be a mapping")
        categorize_gas_source(source.get("type"))
    return propellant.strip().lower(), sources


def surface_neutral_density(thruster, surface):
    """Summed neutral density [m^-3] at one surface, with a per-source split."""
    _, sources = _validate_thruster(thruster)
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    for field in _REQUIRED_SURFACE_GEOMETRY:
        if surface.get(field) is None:
            raise ValueError("surface is missing required field %r" % (field,))
    contributions = {}
    total = 0.0
    for source in sources:
        density = plume_number_density(
            source.get("mass_flow_kg_s"),
            source.get("species_mass_amu", thruster.get("species_mass_amu")),
            source.get("exhaust_speed_m_s", thruster.get("exhaust_speed_m_s")),
            surface["range_m"],
            surface["off_axis_deg"],
            source.get(
                "divergence_exponent", thruster.get("divergence_exponent", 1.0)
            ),
        )
        contributions[source["type"]] = density
        total += density
    return {"total_m3": total, "by_source": contributions, "families": sorted(
        {categorize_gas_source(s["type"]) for s in sources}
    )}


def evaluate_discharge_criteria(
    neutral_density_m3,
    gap_m,
    applied_bias_v,
    gas,
    gas_temperature_k,
    ionization_fraction,
    ionization_cross_section_m2,
    sustaining_density_m3=SUSTAINING_PLASMA_DENSITY_M3,
):
    """Evaluate the three discharge criteria and pick the governing one."""
    if sustaining_density_m3 is None or sustaining_density_m3 <= 0.0:
        raise ValueError("sustaining_density_m3 must be > 0")
    if applied_bias_v is None or applied_bias_v < 0.0:
        raise ValueError("applied_bias_v must be >= 0")
    pressure = local_gas_pressure(neutral_density_m3, gas_temperature_k)
    mfp = electron_mean_free_path(neutral_density_m3, ionization_cross_section_m2)
    breakdown = paschen_breakdown_voltage(pressure, gap_m, gas)
    plasma = ionized_plasma_density(neutral_density_m3, ionization_fraction)

    collisionless = _not_above(gap_m, mfp)
    avalanche_possible = not collisionless
    bias_below_breakdown = breakdown is None or _not_above(applied_bias_v, breakdown)
    density_too_low = _not_above(plasma, sustaining_density_m3)

    sustained = (
        avalanche_possible and not bias_below_breakdown and not density_too_low
    )
    if density_too_low:
        governing = "plasma-density-below-sustaining-threshold"
        margin = math.inf if plasma == 0.0 else sustaining_density_m3 / plasma
    elif bias_below_breakdown:
        governing = (
            "no-breakdown-branch"
            if breakdown is None
            else "applied-bias-below-paschen-breakdown"
        )
        margin = (
            math.inf
            if breakdown is None or applied_bias_v == 0.0
            else breakdown / applied_bias_v
        )
    elif collisionless:
        governing = "gap-collisionless-for-electrons"
        margin = math.inf if gap_m == 0.0 else mfp / gap_m
    else:
        governing = "discharge-sustainable"
        margin = sustaining_density_m3 / plasma if plasma > 0.0 else math.inf
    return {
        "pressure_pa": pressure,
        "pressure_gap_product_pa_m": pressure * gap_m,
        "electron_mean_free_path_m": mfp,
        "breakdown_voltage_v": breakdown,
        "plasma_density_m3": plasma,
        "avalanche_possible": avalanche_possible,
        "bias_below_breakdown": bias_below_breakdown,
        "density_too_low": density_too_low,
        "discharge_sustained": sustained,
        "governing_criterion": governing,
        "margin_ratio": margin,
    }


def assess_surface(thruster, surface):
    """Clause 11.2.5 assessment of one high-voltage surface."""
    propellant, _ = _validate_thruster(thruster)
    density = surface_neutral_density(thruster, surface)
    missing = [f for f in _EVIDENCE_FIELDS if surface.get(f) is None]
    record = {
        "surface_id": surface["id"],
        "neutral_density_m3": density["total_m3"],
        "by_source": density["by_source"],
        "findings": [],
        "compliant": False,
        "criteria": None,
    }
    if missing:
        record["findings"].append(
            "evidence-gap: surface %s has no %s on record"
            % (surface["id"], ", ".join(missing))
        )
        return record
    criteria = evaluate_discharge_criteria(
        density["total_m3"],
        surface["gap_m"],
        surface["applied_bias_v"],
        propellant,
        surface.get("gas_temperature_k", 300.0),
        surface["ionization_fraction"],
        surface.get("ionization_cross_section_m2", 5.0e-19),
    )
    record["criteria"] = criteria
    record["compliant"] = not criteria["discharge_sustained"]
    if criteria["discharge_sustained"]:
        record["findings"].append(
            "discharge-sustainable at surface %s: plasma density %.3e m^-3 with "
            "bias above the Paschen breakdown voltage" % (
                surface["id"], criteria["plasma_density_m3"]
            )
        )
    return record


def assess_thruster_neutral_gas_effects(thruster, surfaces):
    """Aggregate clause 11.2.5 report over every high-voltage surface."""
    _validate_thruster(thruster)
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("surfaces must be a non-empty list")
    seen = set()
    records = []
    findings = []
    for surface in surfaces:
        if not isinstance(surface, dict):
            raise ValueError("every surface must be a mapping")
        sid = surface.get("id")
        if sid in seen:
            raise ValueError("duplicate surface id %r" % (sid,))
        seen.add(sid)
        record = assess_surface(thruster, surface)
        records.append(record)
        findings.extend(record["findings"])
    return {
        "surfaces": records,
        "findings": findings,
        "surface_count": len(records),
        "evidence_complete": not any(
            f.startswith("evidence-gap") for f in findings
        ),
        "compliant": not findings,
    }

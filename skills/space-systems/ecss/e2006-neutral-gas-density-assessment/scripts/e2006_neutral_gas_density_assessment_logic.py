#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 11.3.5 -- induced plasma density from propulsion gas release.

Deterministic, offline, stdlib-only implementation of the clause 11.3.5
procedure: take each propulsion-related gas release on the vehicle, expand
its neutral flow into the free-molecular far field, evaluate the neutral
number density at every observation point of interest, convert the fraction
of that population that becomes ionized into an induced electron density,
add the ambient plasma background, and check the resulting plasma frequency
and Debye length against the compatibility limits held for the point.

The standard is referenced as the procedural anchor only; every model here
is a paraphrased, implementable engineering formulation.
"""

from __future__ import annotations

import math

# --- physical constants -------------------------------------------------
AMU_KG = 1.66053906660e-27
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12
ELECTRON_MASS_KG = 9.1093837015e-31

# --- model constants ----------------------------------------------------
#: Knudsen number at or above which the expansion is free-molecular.
FREE_MOLECULAR_KNUDSEN = 10.0
#: Knudsen number below which the flow is collision-dominated.
CONTINUUM_KNUDSEN = 0.01
#: Hard-sphere collision cross-section used for the mean-free-path, in m^2.
DEFAULT_COLLISION_CROSS_SECTION_M2 = 5.0e-19
#: Relative tolerance applied to a frequency or density sitting exactly on a
#: limit. Representation error must never turn a compliant point red.
LIMIT_TOLERANCE_REL = 1e-9
LIMIT_TOLERANCE_ABS = 1e-12

FLOW_REGIMES = ("continuum", "transitional", "free-molecular")

#: Gas species released by propulsion operation, with the energy an electron
#: must deliver to remove the first bound electron.
PROPELLANT_SPECIES = {
    "xenon": {"mass_amu": 131.29, "ionization_potential_ev": 12.13},
    "krypton": {"mass_amu": 83.80, "ionization_potential_ev": 14.00},
    "argon": {"mass_amu": 39.95, "ionization_potential_ev": 15.76},
    "iodine": {"mass_amu": 126.90, "ionization_potential_ev": 10.45},
    "water-vapour": {"mass_amu": 18.02, "ionization_potential_ev": 12.62},
    "hydrazine-decomposition-products": {
        "mass_amu": 13.40,
        "ionization_potential_ev": 13.60,
    },
    "nitrogen": {"mass_amu": 28.01, "ionization_potential_ev": 15.58},
}

#: Release mechanisms recognised by the clause 11.3.5 assessment. The base
#: rate is the electron-impact ionization rate the release drives at an
#: electron temperature well above the ionization potential; the ceiling is
#: the fraction that mechanism can physically reach.
RELEASE_KINDS = {
    "electric-thruster-plume": {"base_rate_s": 2.5e2, "fraction_ceiling": 0.35},
    "chemical-thruster-plume": {"base_rate_s": 5.0, "fraction_ceiling": 1.0e-3},
    "cold-gas-vent": {"base_rate_s": 1.0e-1, "fraction_ceiling": 1.0e-5},
    "propellant-leak": {"base_rate_s": 1.0e-2, "fraction_ceiling": 1.0e-6},
}


def _positive(value, label):
    """Return value as a strictly positive float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def validate_release_source(record):
    """Validate one propulsion gas release and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("release source must be a mapping, got %r" % (record,))
    source_id = record.get("source_id")
    if not source_id:
        raise ValueError("release source missing source_id")
    species = record.get("species")
    if species not in PROPELLANT_SPECIES:
        raise ValueError("source %s: unknown species %r" % (source_id, species))
    kind = record.get("kind")
    if kind not in RELEASE_KINDS:
        raise ValueError("source %s: unknown release kind %r" % (source_id, kind))
    mass_flow = _positive(record.get("mass_flow_kg_s"), "mass_flow_kg_s")
    velocity = _positive(record.get("exit_velocity_m_s"), "exit_velocity_m_s")
    half_angle = record.get("plume_half_angle_deg")
    try:
        half_angle = float(half_angle)
    except (TypeError, ValueError):
        raise ValueError("plume_half_angle_deg must be numeric, got %r" % (half_angle,))
    if not (0.0 < half_angle < 90.0):
        raise ValueError(
            "source %s: plume_half_angle_deg must lie in (0, 90), got %g"
            % (source_id, half_angle)
        )
    return {
        "source_id": source_id,
        "species": species,
        "kind": kind,
        "mass_flow_kg_s": mass_flow,
        "exit_velocity_m_s": velocity,
        "plume_half_angle_deg": half_angle,
    }


def number_emission_rate_s(mass_flow_kg_s, species):
    """Particles released per second by a mass flow of *species*."""
    if species not in PROPELLANT_SPECIES:
        raise ValueError("unknown species %r" % (species,))
    mass_flow = _positive(mass_flow_kg_s, "mass_flow_kg_s")
    particle_mass = PROPELLANT_SPECIES[species]["mass_amu"] * AMU_KG
    return mass_flow / particle_mass


def plume_shape_exponent(half_angle_deg):
    """Cosine-law exponent whose half-power angle equals *half_angle_deg*.

    A narrow plume yields a large exponent; a wide plume approaches a
    near-uniform hemispherical release.
    """
    try:
        half = float(half_angle_deg)
    except (TypeError, ValueError):
        raise ValueError("half_angle_deg must be numeric, got %r" % (half_angle_deg,))
    if not (0.0 < half < 90.0):
        raise ValueError("half_angle_deg must lie in (0, 90), got %g" % half)
    return math.log(0.5) / math.log(math.cos(math.radians(half)))


def angular_density_factor(field_angle_deg, shape_exponent):
    """Normalized angular distribution of the release, per steradian.

    The factor integrates to one over the forward hemisphere, so the far
    field density follows directly from the emission rate and the range.
    """
    try:
        angle = float(field_angle_deg)
    except (TypeError, ValueError):
        raise ValueError("field_angle_deg must be numeric, got %r" % (field_angle_deg,))
    if not math.isfinite(angle) or not (0.0 <= angle <= 180.0):
        raise ValueError("field_angle_deg must lie in [0, 180], got %g" % angle)
    k = _positive(shape_exponent, "shape_exponent")
    if angle >= 90.0:
        return 0.0
    return ((k + 1.0) / (2.0 * math.pi)) * (math.cos(math.radians(angle)) ** k)


def neutral_number_density_m3(source, distance_m, field_angle_deg):
    """Neutral number density at a point in the far field of one release."""
    src = validate_release_source(source)
    distance = _positive(distance_m, "distance_m")
    rate = number_emission_rate_s(src["mass_flow_kg_s"], src["species"])
    k = plume_shape_exponent(src["plume_half_angle_deg"])
    factor = angular_density_factor(field_angle_deg, k)
    if factor == 0.0:
        return 0.0
    return rate * factor / (src["exit_velocity_m_s"] * distance * distance)


def mean_free_path_m(number_density_m3, cross_section_m2=DEFAULT_COLLISION_CROSS_SECTION_M2):
    """Hard-sphere mean free path of a gas at *number_density_m3*."""
    density = _positive(number_density_m3, "number_density_m3")
    sigma = _positive(cross_section_m2, "cross_section_m2")
    return 1.0 / (math.sqrt(2.0) * density * sigma)


def knudsen_number(number_density_m3, characteristic_length_m, cross_section_m2=DEFAULT_COLLISION_CROSS_SECTION_M2):
    """Ratio of the mean free path to the characteristic length of the flow."""
    length = _positive(characteristic_length_m, "characteristic_length_m")
    return mean_free_path_m(number_density_m3, cross_section_m2) / length


def categorize_flow_regime(kn):
    """Assign a Knudsen number to a flow regime from FLOW_REGIMES."""
    value = _positive(kn, "kn")
    if value >= FREE_MOLECULAR_KNUDSEN:
        return "free-molecular"
    if value >= CONTINUUM_KNUDSEN:
        return "transitional"
    return "continuum"


def residence_time_s(distance_m, exit_velocity_m_s):
    """Time a released particle spends travelling out to *distance_m*."""
    distance = _positive(distance_m, "distance_m")
    velocity = _positive(exit_velocity_m_s, "exit_velocity_m_s")
    return distance / velocity


def ionization_fraction(kind, species, dwell_s, electron_temperature_ev):
    """Fraction of the released neutrals converted into ion-electron pairs.

    The electron-impact rate falls exponentially as the ionization potential
    of the species rises above the electron temperature; the fraction then
    saturates towards the ceiling the release mechanism can reach.
    """
    if kind not in RELEASE_KINDS:
        raise ValueError("unknown release kind %r" % (kind,))
    if species not in PROPELLANT_SPECIES:
        raise ValueError("unknown species %r" % (species,))
    dwell = _non_negative(dwell_s, "dwell_s")
    t_e = _positive(electron_temperature_ev, "electron_temperature_ev")
    potential = PROPELLANT_SPECIES[species]["ionization_potential_ev"]
    mechanism = RELEASE_KINDS[kind]
    rate = mechanism["base_rate_s"] * math.exp(-potential / t_e)
    saturating = 1.0 - math.exp(-rate * dwell)
    return mechanism["fraction_ceiling"] * saturating


def induced_electron_density_m3(neutral_density_m3, fraction, ambient_density_m3=0.0):
    """Electron density at a point: the ionized share plus the ambient plasma."""
    neutral = _non_negative(neutral_density_m3, "neutral_density_m3")
    frac = _non_negative(fraction, "fraction")
    if frac > 1.0:
        raise ValueError("fraction must be <= 1.0, got %g" % frac)
    ambient = _non_negative(ambient_density_m3, "ambient_density_m3")
    return neutral * frac + ambient


def plasma_frequency_hz(electron_density_m3):
    """Electron plasma frequency of a plasma at *electron_density_m3*, in Hz."""
    density = _non_negative(electron_density_m3, "electron_density_m3")
    if density == 0.0:
        return 0.0
    omega_sq = (density * ELEMENTARY_CHARGE_C ** 2) / (
        VACUUM_PERMITTIVITY_F_M * ELECTRON_MASS_KG
    )
    return math.sqrt(omega_sq) / (2.0 * math.pi)


def debye_length_m(electron_density_m3, electron_temperature_ev):
    """Debye shielding length of the local plasma, in metres."""
    density = _positive(electron_density_m3, "electron_density_m3")
    t_e = _positive(electron_temperature_ev, "electron_temperature_ev")
    return math.sqrt(
        (VACUUM_PERMITTIVITY_F_M * t_e) / (density * ELEMENTARY_CHARGE_C)
    )


def _within_limit(value, limit):
    """Value is inside the limit when it is below, or numerically on, it."""
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=LIMIT_TOLERANCE_REL, abs_tol=LIMIT_TOLERANCE_ABS
    )


def assess_rf_compatibility(electron_density_m3, carrier_frequency_hz, margin_factor=1.0):
    """Check a radio-frequency link against the local plasma frequency.

    The link stays usable while the plasma frequency, raised by the required
    margin factor, remains at or below the carrier frequency.
    """
    carrier = _positive(carrier_frequency_hz, "carrier_frequency_hz")
    margin = _positive(margin_factor, "margin_factor")
    f_p = plasma_frequency_hz(electron_density_m3)
    required = f_p * margin
    return {
        "plasma_frequency_hz": f_p,
        "required_headroom_hz": required,
        "carrier_frequency_hz": carrier,
        "compatible": _within_limit(required, carrier),
    }


def assess_observation_point(point, sources, ambient_density_m3, electron_temperature_ev):
    """Evaluate the induced environment at one observation point.

    Every release contributes a neutral density and an ionized share; the
    point is compliant when the summed electron density stays inside its
    plasma-density limit and any radio-frequency link keeps its headroom.
    """
    if not isinstance(point, dict):
        raise ValueError("observation point must be a mapping, got %r" % (point,))
    point_id = point.get("point_id")
    if not point_id:
        raise ValueError("observation point missing point_id")
    distance = _positive(point.get("distance_m"), "distance_m")
    field_angle = point.get("field_angle_deg")
    length = _positive(
        point.get("characteristic_length_m", 1.0), "characteristic_length_m"
    )
    t_e = _positive(electron_temperature_ev, "electron_temperature_ev")
    ambient = _non_negative(ambient_density_m3, "ambient_density_m3")

    neutral_total = 0.0
    contributions = []
    for raw in sources:
        src = validate_release_source(raw)
        neutral = neutral_number_density_m3(src, distance, field_angle)
        if neutral == 0.0:
            continue
        dwell = residence_time_s(distance, src["exit_velocity_m_s"])
        frac = ionization_fraction(src["kind"], src["species"], dwell, t_e)
        neutral_total += neutral
        contributions.append(
            {
                "source_id": src["source_id"],
                "kind": src["kind"],
                "neutral_density_m3": neutral,
                "ionization_fraction": frac,
                "electron_density_m3": neutral * frac,
            }
        )

    electron_total = sum(c["electron_density_m3"] for c in contributions) + ambient
    findings = []
    regime = None
    if neutral_total > 0.0:
        regime = categorize_flow_regime(knudsen_number(neutral_total, length))
        if regime != "free-molecular":
            findings.append(
                "point %s: %s flow (Kn below %g) invalidates the free-molecular "
                "far-field expansion" % (point_id, regime, FREE_MOLECULAR_KNUDSEN)
            )

    limit = point.get("plasma_density_limit_m3")
    if limit is None:
        if contributions:
            findings.append(
                "point %s: propulsion gas reaches it but no plasma-density limit "
                "is on record" % point_id
            )
        density_ok = not contributions
    else:
        limit = _non_negative(limit, "plasma_density_limit_m3")
        density_ok = _within_limit(electron_total, limit)
        if not density_ok:
            findings.append(
                "point %s: induced electron density %.4g per m3 exceeds the limit "
                "%.4g per m3" % (point_id, electron_total, limit)
            )

    rf = None
    carrier = point.get("carrier_frequency_hz")
    if carrier is not None:
        rf = assess_rf_compatibility(
            electron_total, carrier, point.get("rf_margin_factor", 1.0)
        )
        if not rf["compatible"]:
            findings.append(
                "point %s: plasma frequency %.4g Hz with margin exceeds the "
                "carrier at %.4g Hz" % (point_id, rf["plasma_frequency_hz"], carrier)
            )

    return {
        "point_id": point_id,
        "neutral_density_m3": neutral_total,
        "electron_density_m3": electron_total,
        "flow_regime": regime,
        "debye_length_m": debye_length_m(electron_total, t_e) if electron_total > 0.0 else None,
        "plasma_density_limit_m3": limit,
        "rf": rf,
        "contributions": contributions,
        "findings": findings,
        "compliant": density_ok and not findings,
    }


def assess_neutral_gas_environment(points, sources, ambient_density_m3, electron_temperature_ev):
    """Run the clause 11.3.5 assessment across every observation point."""
    if not points:
        raise ValueError("at least one observation point is required")
    if not sources:
        raise ValueError("at least one release source is required")
    results = [
        assess_observation_point(p, sources, ambient_density_m3, electron_temperature_ev)
        for p in points
    ]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    worst = max(results, key=lambda r: r["electron_density_m3"])
    return {
        "points": results,
        "findings": findings,
        "worst_point_id": worst["point_id"],
        "worst_electron_density_m3": worst["electron_density_m3"],
        "compliant": all(r["compliant"] for r in results),
    }

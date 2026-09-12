#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.3 electromagnetic radiation hazard control
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires that people, propellants,
ordnance and actuated thruster valves are not exposed to hazardous
levels of electromagnetic radiation. This module implements the
checkable part of that clause: categorization of a receptor into the
four hazard families, the effective radiated power and far-field
boundary of an emitter, the incident power density evaluated in the
correct field region, the frequency-dependent personnel limit and the
fixed propellant-vapour limit, the power an initiator or valve drive
couples out of that field, the decibel margin of that coupled power
below the firing or actuation threshold, and the separation distance
at which an emitter falls to a stated limit. It does not perform a
full-wave site survey, does not model reflections or multipath, and
does not substitute for a measured hazard survey on the pad.
"""

import math

SPEED_OF_LIGHT_M_PER_S = 299792458.0

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. No engineering limit is
# widened: this only stops a value mathematically equal to the limit
# from reading as an exceedance a few ULPs out.
LIMIT_REL_TOL = 1e-9

RECEPTOR_CATEGORIES = {
    "pad_crew": "personnel",
    "eva_crew": "personnel",
    "ground_operator": "personnel",
    "integration_technician": "personnel",
    "propellant_transfer_line": "fuel",
    "hypergolic_vapour_zone": "fuel",
    "cryogenic_vent_plume": "fuel",
    "electro_explosive_initiator": "ordnance",
    "pyrotechnic_separation_nut": "ordnance",
    "detonator_train": "ordnance",
    "monopropellant_thruster_valve": "thruster_actuation",
    "cold_gas_thruster_valve": "thruster_actuation",
    "latch_valve_actuator": "thruster_actuation",
}

DENSITY_LIMITED_CATEGORIES = frozenset({"personnel", "fuel"})
COUPLING_LIMITED_CATEGORIES = frozenset({"ordnance", "thruster_actuation"})

# Incident density above which a propellant vapour cloud is treated as
# at risk of radio-frequency ignition, in watts per square metre
# (equivalent to 20 milliwatts per square centimetre).
FUEL_HAZARD_LIMIT_W_PER_M2 = 200.0

# Frequency band over which the personnel limit is defined, in hertz.
PERSONNEL_BAND_MIN_HZ = 3.0e6
PERSONNEL_BAND_MAX_HZ = 3.0e11

DEFAULT_COUPLING_MARGIN_DB = {
    "ordnance": 16.5,
    "thruster_actuation": 20.0,
}


def _within_upper_limit(value, limit):
    """True when value is at or below limit, treating a value equal to
    the limit within LIMIT_REL_TOL as within it."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def categorize_radiation_receptor(receptor_kind):
    """Hazard family for a receptor kind: "personnel", "fuel",
    "ordnance" or "thruster_actuation". Raises ValueError for a kind
    that clause 6.3.3 does not protect."""
    try:
        return RECEPTOR_CATEGORIES[receptor_kind]
    except KeyError:
        raise ValueError(
            "unrecognized radiation receptor kind %r under "
            "E-ST-20C clause 6.3.3" % (receptor_kind,)
        )


def wavelength_m(frequency_hz):
    """Free-space wavelength in metres. Raises ValueError for a
    non-positive frequency."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    return SPEED_OF_LIGHT_M_PER_S / frequency_hz


def effective_radiated_power_w(transmit_power_w, gain_dbi, feed_loss_db=0.0):
    """Effective isotropic radiated power in watts: transmitter power
    raised by the antenna gain and lowered by the feed loss, both in
    decibels. Raises ValueError for a non-positive transmit power or a
    negative feed loss."""
    if transmit_power_w <= 0:
        raise ValueError("transmit_power_w must be > 0")
    if feed_loss_db < 0:
        raise ValueError("feed_loss_db must be >= 0")
    return transmit_power_w * 10.0 ** ((gain_dbi - feed_loss_db) / 10.0)


def far_field_boundary_m(aperture_diameter_m, frequency_hz):
    """Start of the far field in metres: twice the squared aperture
    diameter over the wavelength. Raises ValueError for a non-positive
    aperture, or through wavelength_m for a bad frequency."""
    if aperture_diameter_m <= 0:
        raise ValueError("aperture_diameter_m must be > 0")
    return 2.0 * aperture_diameter_m ** 2 / wavelength_m(frequency_hz)


def far_field_power_density_w_per_m2(eirp_w, distance_m):
    """Incident power density in watts per square metre at a far-field
    range: radiated power spread over the sphere of that radius.
    Raises ValueError for a non-positive radiated power or range."""
    if eirp_w <= 0:
        raise ValueError("eirp_w must be > 0")
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    return eirp_w / (4.0 * math.pi * distance_m ** 2)


def near_field_power_density_w_per_m2(transmit_power_w, aperture_diameter_m):
    """On-axis near-field power density in watts per square metre: four
    times the transmitter power over the physical aperture area, the
    conservative plateau value that holds inside the far-field
    boundary. Raises ValueError for a non-positive power or aperture."""
    if transmit_power_w <= 0:
        raise ValueError("transmit_power_w must be > 0")
    if aperture_diameter_m <= 0:
        raise ValueError("aperture_diameter_m must be > 0")
    aperture_area_m2 = math.pi * aperture_diameter_m ** 2 / 4.0
    return 4.0 * transmit_power_w / aperture_area_m2


def power_density_at_range(emitter, distance_m):
    """Incident power density and the field region it was evaluated in.

    emitter: {"transmit_power_w", "gain_dbi", "feed_loss_db" (optional),
    "aperture_diameter_m", "frequency_hz"}. Inside the far-field
    boundary the near-field plateau is used, outside it the spherical
    spreading value. Returns {"region", "power_density_w_per_m2",
    "far_field_boundary_m"}. Raises ValueError through the term
    functions or for a non-positive range."""
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    boundary = far_field_boundary_m(
        emitter["aperture_diameter_m"], emitter["frequency_hz"]
    )
    if distance_m < boundary and not math.isclose(
        distance_m, boundary, rel_tol=LIMIT_REL_TOL
    ):
        density = near_field_power_density_w_per_m2(
            emitter["transmit_power_w"], emitter["aperture_diameter_m"]
        )
        region = "near_field"
    else:
        density = far_field_power_density_w_per_m2(
            effective_radiated_power_w(
                emitter["transmit_power_w"],
                emitter["gain_dbi"],
                emitter.get("feed_loss_db", 0.0),
            ),
            distance_m,
        )
        region = "far_field"
    return {
        "region": region,
        "power_density_w_per_m2": density,
        "far_field_boundary_m": boundary,
    }


def personnel_limit_w_per_m2(frequency_hz):
    """Occupational incident-density limit for people in watts per
    square metre: flat below 400 MHz, rising with frequency through
    the resonance band, flat again above 2 GHz. Raises ValueError for
    a frequency outside the band the limit is defined over."""
    if (
        frequency_hz < PERSONNEL_BAND_MIN_HZ
        or frequency_hz > PERSONNEL_BAND_MAX_HZ
    ):
        raise ValueError(
            "frequency_hz %r is outside the personnel exposure band"
            % (frequency_hz,)
        )
    if frequency_hz < 400.0e6:
        return 10.0
    if frequency_hz < 2.0e9:
        return (frequency_hz / 1.0e6) / 40.0
    return 50.0


def hazard_limit_w_per_m2(category, frequency_hz):
    """Incident-density limit for a density-limited category. Raises
    ValueError for a coupling-limited category -- ordnance and thruster
    actuation are controlled by the power coupled into the initiator or
    valve drive, not by an incident density -- and for an unknown
    category."""
    if category == "personnel":
        return personnel_limit_w_per_m2(frequency_hz)
    if category == "fuel":
        return FUEL_HAZARD_LIMIT_W_PER_M2
    if category in COUPLING_LIMITED_CATEGORIES:
        raise ValueError(
            "category %r is controlled by coupled power, not incident "
            "density" % (category,)
        )
    raise ValueError("unrecognized receptor category %r" % (category,))


def minimum_safe_separation_m(eirp_w, limit_w_per_m2):
    """Range in metres at which a far-field emitter falls to a stated
    density limit. Raises ValueError for a non-positive radiated power
    or limit."""
    if eirp_w <= 0:
        raise ValueError("eirp_w must be > 0")
    if limit_w_per_m2 <= 0:
        raise ValueError("limit_w_per_m2 must be > 0")
    return math.sqrt(eirp_w / (4.0 * math.pi * limit_w_per_m2))


def coupled_power_w(power_density_w_per_m2, pickup_area_m2,
                    coupling_efficiency):
    """Power in watts delivered into an initiator bridgewire or a valve
    drive: incident density times the circuit's effective pickup area
    times its coupling efficiency. Raises ValueError for a negative
    density or pickup area, or an efficiency outside the unit
    interval."""
    if power_density_w_per_m2 < 0:
        raise ValueError("power_density_w_per_m2 must be >= 0")
    if pickup_area_m2 < 0:
        raise ValueError("pickup_area_m2 must be >= 0")
    if not 0.0 <= coupling_efficiency <= 1.0:
        raise ValueError("coupling_efficiency must be within 0.0..1.0")
    return power_density_w_per_m2 * pickup_area_m2 * coupling_efficiency


def coupling_margin_db(threshold_power_w, coupled_w):
    """Decibel margin of the coupled power below the firing or
    actuation threshold: ten times the base-ten logarithm of their
    ratio. Raises ValueError for a non-positive threshold or a coupled
    power that is not positive -- a zero coupled power has no finite
    margin and is handled by the caller."""
    if threshold_power_w <= 0:
        raise ValueError("threshold_power_w must be > 0")
    if coupled_w <= 0:
        raise ValueError("coupled_w must be > 0")
    return 10.0 * math.log10(threshold_power_w / coupled_w)


def receptor_findings(receptor, emitter, required_margin_db=None):
    """Findings (empty when safe) for one receptor exposed to one
    emitter.

    receptor: {"receptor_id", "receptor_kind", "distance_m"} plus, for
    a coupling-limited category, "pickup_area_m2",
    "coupling_efficiency" and "threshold_power_w". A receptor standing
    inside the far-field boundary is additionally reported, because the
    plateau estimate replaces a measured near-field survey. Raises
    ValueError through the term functions."""
    category = categorize_radiation_receptor(receptor["receptor_kind"])
    field = power_density_at_range(emitter, receptor["distance_m"])
    density = field["power_density_w_per_m2"]
    findings = []
    if field["region"] == "near_field":
        findings.append(
            {
                "receptor_id": receptor["receptor_id"],
                "issue": "receptor_inside_far_field_boundary",
                "far_field_boundary_m": field["far_field_boundary_m"],
                "distance_m": receptor["distance_m"],
            }
        )
    if category in DENSITY_LIMITED_CATEGORIES:
        limit = hazard_limit_w_per_m2(category, emitter["frequency_hz"])
        if not _within_upper_limit(density, limit):
            findings.append(
                {
                    "receptor_id": receptor["receptor_id"],
                    "issue": "incident_density_above_limit",
                    "category": category,
                    "power_density_w_per_m2": density,
                    "limit_w_per_m2": limit,
                }
            )
        return findings
    if required_margin_db is None:
        required_margin_db = DEFAULT_COUPLING_MARGIN_DB[category]
    if required_margin_db < 0:
        raise ValueError("required_margin_db must be >= 0")
    coupled = coupled_power_w(
        density, receptor["pickup_area_m2"], receptor["coupling_efficiency"]
    )
    if coupled == 0.0:
        return findings
    margin = coupling_margin_db(receptor["threshold_power_w"], coupled)
    if not _meets_lower_limit(margin, required_margin_db):
        findings.append(
            {
                "receptor_id": receptor["receptor_id"],
                "issue": "coupling_margin_below_requirement",
                "category": category,
                "coupled_power_w": coupled,
                "margin_db": margin,
                "required_margin_db": required_margin_db,
            }
        )
    return findings


def assess_radiation_hazard(scenario):
    """Aggregate clause 6.3.3 review of one emitter against every
    receptor around it.

    scenario: {"emitter" (emitter mapping with "emitter_id"),
    "receptors" (list of receptor mappings)}. Returns the finding list
    and a safe flag that is true only when the list is empty. Raises
    ValueError through the per-receptor checks."""
    emitter = scenario["emitter"]
    findings = []
    for receptor in scenario["receptors"]:
        findings.extend(
            receptor_findings(
                receptor, emitter, receptor.get("required_margin_db")
            )
        )
    return {
        "emitter_id": emitter["emitter_id"],
        "findings": findings,
        "safe": not findings,
    }

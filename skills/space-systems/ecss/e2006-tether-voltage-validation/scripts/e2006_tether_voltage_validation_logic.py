#!/usr/bin/env python3
"""Tether end-to-end voltage validation - ECSS-E-ST-20-06C clause 10.3.

Offline, deterministic, standard-library-only logic for bounding the largest
potential difference that can appear between the two ends of a deployed
tether, and for validating the declared design voltage and the insulation
withstand rating against that bound.

The procedure paraphrased from the clause anchor:

1. Take the relative speed of the tether through the ionospheric plasma:
   circular orbital speed less the along-track part of the corotating plasma
   the tether flies through.
2. Take the field magnitude from a tilted-dipole estimate at the orbit
   radius and the magnetic latitude reached by the orbit; the field roughly
   doubles between the magnetic equator and the magnetic pole.
3. Project the induced field along the deployed line to get the end-to-end
   electromotive force, and sweep the attitude envelope and the magnetic
   latitude range so the worst sample, not the nominal one, sets the bound.
4. Add the circuit terms: an applied supply bias adds to the open-circuit
   value, while operating current, circuit resistance and the plasma-contact
   drops subtract from it. The open-circuit condition is bounding for the
   end-to-end potential precisely because no current flows to drop.
5. Validate: categorize the bounding voltage into a design regime, check the
   declared design voltage covers it, check the insulation withstand rating
   carries the required margin, and check the high-voltage provisions match
   the regime the bound lands in.

No ECSS text is reproduced; the clause is cited as the anchor only.
"""

import math

MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6378137.0
EARTH_ROTATION_RAD_S = 7.2921159e-5
DIPOLE_SURFACE_EQUATORIAL_T = 3.12e-5
MAX_ALTITUDE_KM = 40000.0

# Representation tolerance. A bound and a rating are built from products of
# floats, so a rating written to exactly cover a computed bound can land a few
# units in the last place under it. The tolerance absorbs that representation
# error only; no rating or margin requirement is ever relaxed by it.
REL_TOL = 1e-9

LOW_VOLTAGE = "low-voltage-regime"
HIGH_VOLTAGE = "high-voltage-design-regime"
EXTREME_VOLTAGE = "extreme-high-voltage-regime"

HIGH_VOLTAGE_THRESHOLD_V = 100.0
EXTREME_VOLTAGE_THRESHOLD_V = 1000.0

DEFAULT_SAMPLE_COUNT = 7
MAX_SAMPLE_COUNT = 181
DEFAULT_WITHSTAND_MARGIN = 1.25

REQUIRED_CASE_KEYS = (
    "altitude_km",
    "inclination_deg",
    "length_m",
    "alignment_deg",
    "attitude_deviation_deg",
    "circuit_resistance_ohm",
    "operating_current_a",
    "anode_contact_drop_v",
    "cathode_contact_drop_v",
    "applied_bias_v",
    "declared_design_voltage_v",
    "insulation_withstand_v",
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


def _angle(name, value, low, high):
    value = _number(name, value)
    if value < low or value > high:
        raise ValueError(
            "%s must lie in [%g, %g] degrees, got %g" % (name, low, high, value)
        )
    return value


def _covers(capability, demand):
    """True when a rating covers a demand, absorbing float representation error."""
    return capability >= demand or math.isclose(
        capability, demand, rel_tol=REL_TOL, abs_tol=0.0
    )


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------


def orbital_radius_m(altitude_km):
    altitude = _positive("altitude_km", altitude_km)
    if altitude > MAX_ALTITUDE_KM:
        raise ValueError(
            "altitude_km %g is outside the modelled regime (max %g)"
            % (altitude, MAX_ALTITUDE_KM)
        )
    return EARTH_RADIUS_M + altitude * 1000.0


def orbital_velocity(altitude_km):
    """Circular orbital speed (m/s) at the given altitude."""
    return math.sqrt(MU_EARTH_M3_S2 / orbital_radius_m(altitude_km))


def corotation_velocity(altitude_km, latitude_deg):
    """Speed (m/s) of the corotating plasma at the orbit radius and latitude."""
    radius = orbital_radius_m(altitude_km)
    latitude = _angle("latitude_deg", latitude_deg, -90.0, 90.0)
    return EARTH_ROTATION_RAD_S * radius * math.cos(math.radians(latitude))


def relative_plasma_velocity(altitude_km, inclination_deg, latitude_deg):
    """Tether speed (m/s) through the plasma after removing plasma corotation.

    Only the along-track part of the corotation cancels, so a retrograde or a
    high-inclination orbit keeps more of the orbital speed than an equatorial
    prograde one does.
    """
    orbital = orbital_velocity(altitude_km)
    inclination = _angle("inclination_deg", inclination_deg, 0.0, 180.0)
    corotation = corotation_velocity(altitude_km, latitude_deg)
    return orbital - corotation * math.cos(math.radians(inclination))


def dipole_flux_density(altitude_km, magnetic_latitude_deg):
    """Field magnitude (T) from a centred-dipole estimate at the orbit radius."""
    radius = orbital_radius_m(altitude_km)
    latitude = _angle("magnetic_latitude_deg", magnetic_latitude_deg, -90.0, 90.0)
    scale = (EARTH_RADIUS_M / radius) ** 3
    shape = math.sqrt(1.0 + 3.0 * math.sin(math.radians(latitude)) ** 2)
    return DIPOLE_SURFACE_EQUATORIAL_T * scale * shape


# --------------------------------------------------------------------------
# induced potential
# --------------------------------------------------------------------------


def induced_field_v_per_m(relative_velocity_m_s, flux_density_t,
                          velocity_field_angle_deg=90.0):
    """Motional field strength (V/m) seen by a line moving through the field."""
    speed = _positive("relative_velocity_m_s", relative_velocity_m_s)
    flux = _positive("flux_density_t", flux_density_t)
    angle = _angle("velocity_field_angle_deg", velocity_field_angle_deg, 0.0, 180.0)
    return speed * flux * abs(math.sin(math.radians(angle)))


def end_to_end_emf(field_v_per_m, length_m, alignment_deg):
    """Open-circuit electromotive force (V) across the deployed length."""
    field = _non_negative("field_v_per_m", field_v_per_m)
    length = _positive("length_m", length_m)
    alignment = _angle("alignment_deg", alignment_deg, 0.0, 180.0)
    return field * length * abs(math.cos(math.radians(alignment)))


def circuit_drop(operating_current_a, circuit_resistance_ohm,
                 anode_contact_drop_v, cathode_contact_drop_v):
    """Total voltage (V) consumed inside the circuit when current flows."""
    current = _non_negative("operating_current_a", operating_current_a)
    resistance = _non_negative("circuit_resistance_ohm", circuit_resistance_ohm)
    anode = _non_negative("anode_contact_drop_v", anode_contact_drop_v)
    cathode = _non_negative("cathode_contact_drop_v", cathode_contact_drop_v)
    return current * resistance + anode + cathode


def end_to_end_potential(emf_v, applied_bias_v, drop_v):
    """Potential difference (V) between the two ends, open-circuit and loaded.

    The open-circuit value is the bound: with no current there is nothing for
    the circuit resistance or the plasma contacts to drop.
    """
    emf = _non_negative("emf_v", emf_v)
    bias = _number("applied_bias_v", applied_bias_v)
    drop = _non_negative("drop_v", drop_v)
    open_circuit = abs(emf + bias)
    if open_circuit > drop:
        # Current flows: the circuit resistance and the two plasma contacts
        # consume their drops, so the ends see less than the open-circuit value.
        loaded = open_circuit - drop
        current_flows = True
    else:
        # The driving potential cannot push the contacts into conduction, so no
        # current flows and the ends sit at the open-circuit value.
        loaded = open_circuit
        current_flows = False
    return {
        "open_circuit_v": open_circuit,
        "loaded_v": loaded,
        "current_flows": current_flows,
        "bounding_v": max(open_circuit, loaded),
    }


# --------------------------------------------------------------------------
# worst-case sweep
# --------------------------------------------------------------------------


def sweep_grid(inclination_deg, alignment_deg, attitude_deviation_deg,
               sample_count=DEFAULT_SAMPLE_COUNT):
    """Magnetic-latitude and attitude samples spanning the declared envelope."""
    inclination = _angle("inclination_deg", inclination_deg, 0.0, 180.0)
    alignment = _angle("alignment_deg", alignment_deg, 0.0, 180.0)
    deviation = _non_negative("attitude_deviation_deg", attitude_deviation_deg)
    if deviation > 90.0:
        raise ValueError(
            "attitude_deviation_deg must not exceed 90, got %g" % deviation
        )
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("sample_count must be an int, got %r" % (sample_count,))
    if sample_count < 2 or sample_count > MAX_SAMPLE_COUNT:
        raise ValueError(
            "sample_count must be between 2 and %d, got %d"
            % (MAX_SAMPLE_COUNT, sample_count)
        )
    reach = min(inclination, 180.0 - inclination)
    reach = min(reach, 90.0)
    latitudes = [reach * i / (sample_count - 1) for i in range(sample_count)]
    alignments = sorted(
        {
            min(180.0, max(0.0, alignment - deviation)),
            alignment,
            min(180.0, max(0.0, alignment + deviation)),
        }
    )
    return [
        {"magnetic_latitude_deg": lat, "alignment_deg": ali}
        for lat in latitudes
        for ali in alignments
    ]


def worst_case_end_to_end_potential(case):
    """Largest end-to-end potential (V) over the declared operating envelope."""
    _require_case(case)
    grid = sweep_grid(
        case["inclination_deg"],
        case["alignment_deg"],
        case["attitude_deviation_deg"],
        case.get("sample_count", DEFAULT_SAMPLE_COUNT),
    )
    drop = circuit_drop(
        case["operating_current_a"],
        case["circuit_resistance_ohm"],
        case["anode_contact_drop_v"],
        case["cathode_contact_drop_v"],
    )
    angle = case.get("velocity_field_angle_deg", 90.0)
    worst = None
    for sample in grid:
        speed = relative_plasma_velocity(
            case["altitude_km"], case["inclination_deg"],
            sample["magnetic_latitude_deg"]
        )
        flux = dipole_flux_density(case["altitude_km"],
                                   sample["magnetic_latitude_deg"])
        field = induced_field_v_per_m(speed, flux, angle)
        emf = end_to_end_emf(field, case["length_m"], sample["alignment_deg"])
        potentials = end_to_end_potential(emf, case["applied_bias_v"], drop)
        entry = dict(sample)
        entry.update(potentials)
        entry["field_v_per_m"] = field
        entry["emf_v"] = emf
        if worst is None or entry["bounding_v"] > worst["bounding_v"]:
            worst = entry
    worst["circuit_drop_v"] = drop
    worst["sample_count"] = len(grid)
    return worst


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------


def categorize_voltage_regime(voltage_v):
    """Categorize a bounding voltage into its design regime."""
    voltage = _non_negative("voltage_v", voltage_v)
    if voltage >= EXTREME_VOLTAGE_THRESHOLD_V or math.isclose(
        voltage, EXTREME_VOLTAGE_THRESHOLD_V, rel_tol=REL_TOL, abs_tol=0.0
    ):
        return EXTREME_VOLTAGE
    if voltage >= HIGH_VOLTAGE_THRESHOLD_V or math.isclose(
        voltage, HIGH_VOLTAGE_THRESHOLD_V, rel_tol=REL_TOL, abs_tol=0.0
    ):
        return HIGH_VOLTAGE
    return LOW_VOLTAGE


def withstand_margin(insulation_withstand_v, bounding_voltage_v):
    """Insulation withstand rating divided by the bounding voltage."""
    rating = _positive("insulation_withstand_v", insulation_withstand_v)
    bound = _positive("bounding_voltage_v", bounding_voltage_v)
    return rating / bound


def declared_voltage_covers_bound(declared_design_voltage_v, bounding_voltage_v):
    """True when the declared design voltage covers the computed bound."""
    declared = _positive("declared_design_voltage_v", declared_design_voltage_v)
    bound = _non_negative("bounding_voltage_v", bounding_voltage_v)
    return _covers(declared, bound)


def _require_case(case):
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    missing = [key for key in REQUIRED_CASE_KEYS if key not in case]
    if missing:
        raise ValueError("case is missing required keys: %s" % ", ".join(sorted(missing)))
    return case


def validate_tether_voltage(case):
    """Full clause 10.3 validation of one tether end-to-end voltage case."""
    _require_case(case)
    worst = worst_case_end_to_end_potential(case)
    bound = worst["bounding_v"]
    regime = categorize_voltage_regime(bound)
    required_margin = _positive(
        "required_withstand_margin",
        case.get("required_withstand_margin", DEFAULT_WITHSTAND_MARGIN),
    )
    margin = withstand_margin(case["insulation_withstand_v"], bound) if bound > 0.0 \
        else float("inf")
    provisions = case.get("high_voltage_provisions", False)
    if not isinstance(provisions, bool):
        raise ValueError(
            "high_voltage_provisions must be a bool, got %r" % (provisions,)
        )
    findings = []
    if not declared_voltage_covers_bound(case["declared_design_voltage_v"], bound):
        findings.append(
            "declared design voltage %.1f V does not cover the bounding %.1f V"
            % (case["declared_design_voltage_v"], bound)
        )
    if not _covers(margin, required_margin):
        findings.append(
            "insulation withstand margin %.3f is below the required %.3f"
            % (margin, required_margin)
        )
    if regime != LOW_VOLTAGE and not provisions:
        findings.append(
            "bounding voltage lands in the %s with no high-voltage provisions declared"
            % regime
        )
    return {
        "worst_sample": worst,
        "bounding_voltage_v": bound,
        "open_circuit_voltage_v": worst["open_circuit_v"],
        "loaded_voltage_v": worst["loaded_v"],
        "circuit_drop_v": worst["circuit_drop_v"],
        "regime": regime,
        "withstand_margin": margin,
        "required_withstand_margin": required_margin,
        "findings": findings,
        "compliant": not findings,
    }

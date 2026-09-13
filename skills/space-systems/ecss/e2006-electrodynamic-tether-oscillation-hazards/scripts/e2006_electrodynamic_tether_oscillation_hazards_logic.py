#!/usr/bin/env python3
"""Electrodynamic-tether oscillation hazards - ECSS-E-ST-20-06C clause 10.2.6.

Offline, deterministic, standard-library-only logic for deciding whether the
electrical interaction of a long deployed electrodynamic tether can pump a
dynamic instability into the tether/spacecraft system.

The procedure paraphrased from the clause anchor:

1. Build the mode table of the deployed system: the two gravity-gradient
   libration modes (in-plane at sqrt(3) x mean-motion, out-of-plane at
   2 x mean-motion) plus the taut-string transverse modes and the axial
   longitudinal modes of the tether itself.
2. Build the forcing spectrum that the electrical interaction imposes: the
   geomagnetic field seen by the tether repeats with the orbit, so the
   Lorentz load carries orbital harmonics; a switched or duty-cycled tether
   current adds its own modulation line and harmonic.
3. Categorize every forcing line against the mode table inside a detuning
   band - libration-resonance, transverse-string-resonance,
   longitudinal-resonance or off-resonance.
4. Size the libration response: the net Lorentz torque about the system
   centre-of-mass divided by the modal stiffness, amplified by the resonant
   quality-factor when a libration line is resonant.
5. Judge the response against the dumbbell tumbling separatrix, the mission
   allowable libration angle, and the transverse-sag slack-onset limit that
   marks the tether bowing far enough to lose tension.

No ECSS text is reproduced; the clause is cited as the anchor only.
"""

import math

MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6378137.0
MAX_ALTITUDE_KM = 60000.0

# Representation tolerance. Boundary comparisons are differences and sums of
# floats, so an exactly-on-limit case can land a few units in the last place
# past the limit. The tolerance absorbs that representation error only; the
# engineering limits themselves are never widened.
REL_TOL = 1e-9

IN_PLANE_LIBRATION_FACTOR = math.sqrt(3.0)
OUT_OF_PLANE_LIBRATION_FACTOR = 2.0

# Pitch separatrix of a dumbbell in a circular orbit: beyond this libration
# amplitude the gravity-gradient restoring torque no longer recaptures the
# tether and the system tumbles.
TUMBLE_SEPARATRIX_DEG = 65.9

DEFAULT_DETUNE_FRACTION = 0.05
DEFAULT_SAG_RATIO_LIMIT = 0.05
DEFAULT_ORBITAL_HARMONICS = 2
DEFAULT_MODE_COUNT = 3
MAX_MODE_COUNT = 12
MAX_DAMPING_RATIO = 0.999

IN_PLANE_LIBRATION = "in-plane-libration"
OUT_OF_PLANE_LIBRATION = "out-of-plane-libration"
OFF_RESONANCE = "off-resonance"

RESONANT_CATEGORY_BY_FAMILY = {
    "libration": "libration-resonance",
    "transverse": "transverse-string-resonance",
    "longitudinal": "longitudinal-resonance",
}

REQUIRED_CASE_KEYS = (
    "altitude_km",
    "length_m",
    "linear_density_kg_m",
    "tension_n",
    "axial_stiffness_n",
    "current_a",
    "magnetic_flux_density_t",
    "field_incidence_deg",
    "end_mass_a_kg",
    "end_mass_b_kg",
    "damping_ratio",
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


def _within_band(distance, band):
    """Inside-the-band test that absorbs float representation error.

    ``distance`` is a difference of frequencies and ``band`` a product, so an
    exactly-on-band case can round a few units in the last place high. A line
    sitting on the band edge is treated as resonant, which is the conservative
    reading for a hazard check.
    """
    return distance <= band or math.isclose(distance, band, rel_tol=REL_TOL, abs_tol=0.0)


def _exceeds_limit(value, limit):
    """True when value is genuinely over limit, not merely rounded over it."""
    if math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0):
        return False
    return value > limit


# --------------------------------------------------------------------------
# orbit and mode table
# --------------------------------------------------------------------------


def orbital_mean_motion(altitude_km):
    """Mean motion (rad/s) of a circular orbit at the given altitude."""
    altitude = _positive("altitude_km", altitude_km)
    if altitude > MAX_ALTITUDE_KM:
        raise ValueError(
            "altitude_km %g is outside the deployed-tether regime (max %g)"
            % (altitude, MAX_ALTITUDE_KM)
        )
    radius = EARTH_RADIUS_M + altitude * 1000.0
    return math.sqrt(MU_EARTH_M3_S2 / radius ** 3)


def libration_mode_frequencies(mean_motion_rad_s):
    """Gravity-gradient libration frequencies (rad/s) of a dumbbell tether."""
    n = _positive("mean_motion_rad_s", mean_motion_rad_s)
    return {
        IN_PLANE_LIBRATION: IN_PLANE_LIBRATION_FACTOR * n,
        OUT_OF_PLANE_LIBRATION: OUT_OF_PLANE_LIBRATION_FACTOR * n,
    }


def transverse_mode_frequencies(length_m, tension_n, linear_density_kg_m,
                                mode_count=DEFAULT_MODE_COUNT):
    """Taut-string transverse mode frequencies (rad/s), lowest first."""
    length = _positive("length_m", length_m)
    tension = _positive("tension_n", tension_n)
    density = _positive("linear_density_kg_m", linear_density_kg_m)
    count = _mode_count(mode_count)
    wave_speed = math.sqrt(tension / density)
    return {
        "transverse-mode-%d" % k: k * math.pi * wave_speed / length
        for k in range(1, count + 1)
    }


def longitudinal_mode_frequencies(length_m, axial_stiffness_n, linear_density_kg_m,
                                  mode_count=2):
    """Axial (longitudinal) mode frequencies (rad/s) of the tether strand."""
    length = _positive("length_m", length_m)
    stiffness = _positive("axial_stiffness_n", axial_stiffness_n)
    density = _positive("linear_density_kg_m", linear_density_kg_m)
    count = _mode_count(mode_count)
    wave_speed = math.sqrt(stiffness / density)
    return {
        "longitudinal-mode-%d" % k: k * math.pi * wave_speed / length
        for k in range(1, count + 1)
    }


def _mode_count(mode_count):
    if isinstance(mode_count, bool) or not isinstance(mode_count, int):
        raise ValueError("mode_count must be an int, got %r" % (mode_count,))
    if mode_count < 1 or mode_count > MAX_MODE_COUNT:
        raise ValueError(
            "mode_count must be between 1 and %d, got %d" % (MAX_MODE_COUNT, mode_count)
        )
    return mode_count


def build_mode_table(case):
    """Assemble every mode family of the deployed system into one table."""
    mean_motion = orbital_mean_motion(case["altitude_km"])
    table = dict(libration_mode_frequencies(mean_motion))
    table.update(
        transverse_mode_frequencies(
            case["length_m"],
            case["tension_n"],
            case["linear_density_kg_m"],
            case.get("transverse_mode_count", DEFAULT_MODE_COUNT),
        )
    )
    table.update(
        longitudinal_mode_frequencies(
            case["length_m"],
            case["axial_stiffness_n"],
            case["linear_density_kg_m"],
            case.get("longitudinal_mode_count", 2),
        )
    )
    return table


# --------------------------------------------------------------------------
# electrical forcing
# --------------------------------------------------------------------------


def lorentz_force_per_length(current_a, magnetic_flux_density_t, field_incidence_deg):
    """Transverse Lorentz load per unit length (N/m) on a current-carrying tether."""
    current = _positive("current_a", current_a)
    flux = _positive("magnetic_flux_density_t", magnetic_flux_density_t)
    incidence = _number("field_incidence_deg", field_incidence_deg)
    if incidence < 0.0 or incidence > 180.0:
        raise ValueError(
            "field_incidence_deg must lie in [0, 180], got %g" % incidence
        )
    return current * flux * abs(math.sin(math.radians(incidence)))


def forcing_spectrum(mean_motion_rad_s, current_modulation_hz=None,
                     orbital_harmonics=DEFAULT_ORBITAL_HARMONICS):
    """Forcing lines (rad/s) the electrical interaction imposes on the tether."""
    n = _positive("mean_motion_rad_s", mean_motion_rad_s)
    if isinstance(orbital_harmonics, bool) or not isinstance(orbital_harmonics, int):
        raise ValueError(
            "orbital_harmonics must be an int, got %r" % (orbital_harmonics,)
        )
    if orbital_harmonics < 1 or orbital_harmonics > MAX_MODE_COUNT:
        raise ValueError(
            "orbital_harmonics must be between 1 and %d, got %d"
            % (MAX_MODE_COUNT, orbital_harmonics)
        )
    lines = [
        {"label": "orbital-harmonic-%d" % k, "omega_rad_s": k * n}
        for k in range(1, orbital_harmonics + 1)
    ]
    if current_modulation_hz is not None:
        rate = _positive("current_modulation_hz", current_modulation_hz)
        omega = 2.0 * math.pi * rate
        lines.append({"label": "current-modulation-fundamental", "omega_rad_s": omega})
        lines.append({"label": "current-modulation-harmonic-2", "omega_rad_s": 2.0 * omega})
    return lines


# --------------------------------------------------------------------------
# resonance categorization
# --------------------------------------------------------------------------


def _mode_family(mode_name):
    for family in RESONANT_CATEGORY_BY_FAMILY:
        if family in mode_name:
            return family
    raise ValueError("mode name '%s' belongs to no known mode family" % mode_name)


def categorize_resonance(forcing_omega_rad_s, mode_table,
                         detune_fraction=DEFAULT_DETUNE_FRACTION):
    """Categorize one forcing line against the mode table.

    Returns the nearest mode, its fractional detuning, and the resonance
    category - or off-resonance when no mode sits inside the detuning band.
    """
    omega = _positive("forcing_omega_rad_s", forcing_omega_rad_s)
    if not isinstance(mode_table, dict) or not mode_table:
        raise ValueError("mode_table must be a non-empty mapping of mode -> rad/s")
    fraction = _number("detune_fraction", detune_fraction)
    if fraction <= 0.0 or fraction >= 1.0:
        raise ValueError(
            "detune_fraction must lie in (0, 1), got %g" % fraction
        )
    nearest_name = None
    nearest_distance = None
    for name, mode_omega in mode_table.items():
        mode_omega = _positive("mode frequency '%s'" % name, mode_omega)
        distance = abs(omega - mode_omega)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_name = name
    band = fraction * mode_table[nearest_name]
    resonant = _within_band(nearest_distance, band)
    category = (
        RESONANT_CATEGORY_BY_FAMILY[_mode_family(nearest_name)]
        if resonant
        else OFF_RESONANCE
    )
    return {
        "category": category,
        "mode": nearest_name if resonant else None,
        "nearest_mode": nearest_name,
        "detuning_fraction": nearest_distance / mode_table[nearest_name],
        "resonant": resonant,
    }


def resonant_amplification(damping_ratio):
    """Steady-state amplification at resonance, Q = 1 / (2 zeta)."""
    zeta = _positive("damping_ratio", damping_ratio)
    if zeta > MAX_DAMPING_RATIO:
        raise ValueError(
            "damping_ratio must not exceed %g (critically damped), got %g"
            % (MAX_DAMPING_RATIO, zeta)
        )
    return 1.0 / (2.0 * zeta)


# --------------------------------------------------------------------------
# libration response and slack onset
# --------------------------------------------------------------------------


def center_of_mass_offset(length_m, linear_density_kg_m, end_mass_a_kg, end_mass_b_kg):
    """Distance (m) of the system centre-of-mass from end A."""
    length = _positive("length_m", length_m)
    density = _positive("linear_density_kg_m", linear_density_kg_m)
    mass_a = _non_negative("end_mass_a_kg", end_mass_a_kg)
    mass_b = _non_negative("end_mass_b_kg", end_mass_b_kg)
    tether_mass = density * length
    total = tether_mass + mass_a + mass_b
    if total <= 0.0:
        raise ValueError("total system mass must be strictly positive")
    return (mass_b * length + tether_mass * 0.5 * length) / total


def libration_inertia(length_m, linear_density_kg_m, end_mass_a_kg, end_mass_b_kg):
    """Moment of inertia (kg m^2) of the dumbbell about its centre-of-mass."""
    length = _positive("length_m", length_m)
    density = _positive("linear_density_kg_m", linear_density_kg_m)
    mass_a = _non_negative("end_mass_a_kg", end_mass_a_kg)
    mass_b = _non_negative("end_mass_b_kg", end_mass_b_kg)
    offset = center_of_mass_offset(length, density, mass_a, mass_b)
    tether_mass = density * length
    rod = tether_mass * length ** 2 / 12.0 + tether_mass * (0.5 * length - offset) ** 2
    return mass_a * offset ** 2 + mass_b * (length - offset) ** 2 + rod


def lorentz_libration_torque(force_per_length_n_m, length_m, com_offset_m):
    """Net Lorentz torque (N m) about the centre-of-mass from a uniform load.

    A uniform transverse load on a symmetric tether produces no net torque -
    it only bows the strand - so the torque scales with how far the
    centre-of-mass sits from the geometric midpoint.
    """
    load = _non_negative("force_per_length_n_m", force_per_length_n_m)
    length = _positive("length_m", length_m)
    offset = _non_negative("com_offset_m", com_offset_m)
    if offset > length:
        raise ValueError(
            "com_offset_m %g cannot exceed length_m %g" % (offset, length)
        )
    return abs(load * (0.5 * length ** 2 - length * offset))


def libration_response_deg(torque_n_m, inertia_kg_m2, mode_omega_rad_s,
                           damping_ratio, resonant):
    """Steady-state libration amplitude (deg) under the Lorentz torque."""
    torque = _non_negative("torque_n_m", torque_n_m)
    inertia = _positive("inertia_kg_m2", inertia_kg_m2)
    omega = _positive("mode_omega_rad_s", mode_omega_rad_s)
    if not isinstance(resonant, bool):
        raise ValueError("resonant must be a bool, got %r" % (resonant,))
    quasi_static = torque / (inertia * omega ** 2)
    # Validate the damping ratio on every path, not only the resonant one.
    gain_at_resonance = resonant_amplification(damping_ratio)
    gain = gain_at_resonance if resonant else 1.0
    return math.degrees(quasi_static * gain)


def transverse_sag_ratio(force_per_length_n_m, length_m, tension_n):
    """Mid-span sag divided by span for a taut strand under a uniform load."""
    load = _non_negative("force_per_length_n_m", force_per_length_n_m)
    length = _positive("length_m", length_m)
    tension = _positive("tension_n", tension_n)
    return load * length / (8.0 * tension)


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


def assess_oscillation_hazards(case):
    """Full clause 10.2.6 oscillation-hazard assessment of one tether case."""
    _require_case(case)
    mean_motion = orbital_mean_motion(case["altitude_km"])
    modes = build_mode_table(case)
    detune = case.get("detune_fraction", DEFAULT_DETUNE_FRACTION)
    lines = forcing_spectrum(
        mean_motion,
        case.get("current_modulation_hz"),
        case.get("orbital_harmonics", DEFAULT_ORBITAL_HARMONICS),
    )
    resonances = []
    libration_resonant = False
    for line in lines:
        verdict = categorize_resonance(line["omega_rad_s"], modes, detune)
        entry = dict(line)
        entry.update(verdict)
        resonances.append(entry)
        if verdict["category"] == RESONANT_CATEGORY_BY_FAMILY["libration"]:
            libration_resonant = True

    load = lorentz_force_per_length(
        case["current_a"],
        case["magnetic_flux_density_t"],
        case["field_incidence_deg"],
    )
    offset = center_of_mass_offset(
        case["length_m"],
        case["linear_density_kg_m"],
        case["end_mass_a_kg"],
        case["end_mass_b_kg"],
    )
    inertia = libration_inertia(
        case["length_m"],
        case["linear_density_kg_m"],
        case["end_mass_a_kg"],
        case["end_mass_b_kg"],
    )
    torque = lorentz_libration_torque(load, case["length_m"], offset)
    amplitude = libration_response_deg(
        torque,
        inertia,
        IN_PLANE_LIBRATION_FACTOR * mean_motion,
        case["damping_ratio"],
        libration_resonant,
    )
    sag = transverse_sag_ratio(load, case["length_m"], case["tension_n"])
    sag_limit = _positive("sag_ratio_limit", case.get("sag_ratio_limit",
                                                      DEFAULT_SAG_RATIO_LIMIT))
    findings = []
    for entry in resonances:
        if entry["resonant"]:
            findings.append(
                "%s falls on %s (%s)"
                % (entry["label"], entry["mode"], entry["category"])
            )
    allowable = case.get("allowable_libration_deg")
    if allowable is not None:
        allowable = _positive("allowable_libration_deg", allowable)
        if _exceeds_limit(amplitude, allowable):
            findings.append(
                "libration amplitude %.3f deg exceeds the allowable %.3f deg"
                % (amplitude, allowable)
            )
    if _exceeds_limit(amplitude, TUMBLE_SEPARATRIX_DEG):
        findings.append(
            "libration amplitude %.3f deg crosses the gravity-gradient tumbling "
            "separatrix %.1f deg" % (amplitude, TUMBLE_SEPARATRIX_DEG)
        )
    if _exceeds_limit(sag, sag_limit):
        findings.append(
            "transverse sag ratio %.4f exceeds the slack-onset limit %.4f"
            % (sag, sag_limit)
        )
    return {
        "mean_motion_rad_s": mean_motion,
        "modes": modes,
        "forcing_lines": lines,
        "resonances": resonances,
        "lorentz_load_n_m": load,
        "com_offset_m": offset,
        "libration_inertia_kg_m2": inertia,
        "libration_torque_n_m": torque,
        "libration_amplitude_deg": amplitude,
        "sag_ratio": sag,
        "findings": findings,
        "compliant": not findings,
    }

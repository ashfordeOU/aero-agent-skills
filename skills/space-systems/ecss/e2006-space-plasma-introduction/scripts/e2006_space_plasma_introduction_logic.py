"""Space plasma and the charging risks it creates (ECSS-E-ST-20-06C cl. 4.1.1).

Deterministic, offline, stdlib-only. Turns an ambient plasma record -- electron
density, electron temperature, body characteristic length -- into:

* the debye screening length and the collected electron thermal flux;
* the population category and the sheath regime of the body;
* the families of spacecraft-charging risk that regime puts on the table;
* the build-up timescale of a frame potential of concern.

No ECSS text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "EPSILON_0",
    "ELEMENTARY_CHARGE",
    "ELECTRON_MASS",
    "COLD_BAND_EDGE_EV",
    "WARM_BAND_EDGE_EV",
    "HOT_BAND_EDGE_EV",
    "THIN_SHEATH_RATIO",
    "THICK_SHEATH_RATIO",
    "normalize_environment",
    "debye_length",
    "electron_thermal_speed",
    "electron_thermal_flux",
    "density_class",
    "categorize_population",
    "sheath_ratio",
    "sheath_regime",
    "charging_risk_families",
    "potential_build_up_time",
    "screen_environment",
    "worst_case_environment",
    "summarize_environments",
]

EPSILON_0 = 8.8541878128e-12  # F/m
ELEMENTARY_CHARGE = 1.602176634e-19  # C
ELECTRON_MASS = 9.1093837015e-31  # kg

# Electron-temperature band edges, in electronvolts. A value sitting exactly on
# an edge belongs to the upper band.
COLD_BAND_EDGE_EV = 1.0
WARM_BAND_EDGE_EV = 1.0e3
HOT_BAND_EDGE_EV = 1.0e5

# debye-length / characteristic-length ratio bounds for the sheath regime.
THIN_SHEATH_RATIO = 0.01
THICK_SHEATH_RATIO = 1.0

# Density above which the population counts as dense, in particles per m^3.
DENSE_PLASMA_DENSITY_M3 = 1.0e9

_BAND_TOLERANCE = 1e-9
_RATIO_TOLERANCE = 1e-12


def _positive(value, name):
    """Return value as a float, rejecting anything not strictly positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def _flag(value, name):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def normalize_environment(record):
    """Validate one ambient plasma record and fill its optional fields."""
    if not isinstance(record, dict):
        raise ValueError("environment record must be a mapping, got %r" % (record,))
    for key in ("electron_density_m3", "electron_temperature_ev"):
        if key not in record:
            raise ValueError("environment record missing required field %r" % key)
    name = record.get("name", "unnamed-environment")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("environment name must be a non-empty string")
    return {
        "name": name.strip(),
        "electron_density_m3": _positive(
            record["electron_density_m3"], "electron_density_m3"
        ),
        "electron_temperature_ev": _positive(
            record["electron_temperature_ev"], "electron_temperature_ev"
        ),
        "characteristic_length_m": _positive(
            record.get("characteristic_length_m", 1.0), "characteristic_length_m"
        ),
        "high_voltage_array": _flag(
            record.get("high_voltage_array", False), "high_voltage_array"
        ),
        "eclipse_exposed": _flag(
            record.get("eclipse_exposed", False), "eclipse_exposed"
        ),
    }


def debye_length(electron_density_m3, electron_temperature_ev):
    """Plasma screening length in metres for a temperature given in eV."""
    density = _positive(electron_density_m3, "electron_density_m3")
    temperature = _positive(electron_temperature_ev, "electron_temperature_ev")
    return math.sqrt(EPSILON_0 * temperature / (density * ELEMENTARY_CHARGE))


def electron_thermal_speed(electron_temperature_ev):
    """Mean electron thermal speed in m/s for a temperature given in eV."""
    temperature = _positive(electron_temperature_ev, "electron_temperature_ev")
    return math.sqrt(
        8.0 * ELEMENTARY_CHARGE * temperature / (math.pi * ELECTRON_MASS)
    )


def electron_thermal_flux(electron_density_m3, electron_temperature_ev):
    """Random electron current density collected by a surface, in A/m^2."""
    density = _positive(electron_density_m3, "electron_density_m3")
    speed = electron_thermal_speed(electron_temperature_ev)
    return 0.25 * density * ELEMENTARY_CHARGE * speed


def density_class(electron_density_m3):
    """'dense-plasma' or 'tenuous-plasma' against the density threshold."""
    density = _positive(electron_density_m3, "electron_density_m3")
    if density > DENSE_PLASMA_DENSITY_M3 or math.isclose(
        density, DENSE_PLASMA_DENSITY_M3, rel_tol=_BAND_TOLERANCE, abs_tol=0.0
    ):
        return "dense-plasma"
    return "tenuous-plasma"


def _below_edge(value, edge):
    """True when value sits strictly below edge, ignoring last-place drift."""
    if value >= edge:
        return False
    return not math.isclose(value, edge, rel_tol=_BAND_TOLERANCE, abs_tol=0.0)


def categorize_population(electron_temperature_ev):
    """Population category from the electron-temperature band."""
    temperature = _positive(electron_temperature_ev, "electron_temperature_ev")
    if _below_edge(temperature, COLD_BAND_EDGE_EV):
        return "cold-ionospheric-plasma"
    if _below_edge(temperature, WARM_BAND_EDGE_EV):
        return "warm-magnetospheric-plasma"
    if _below_edge(temperature, HOT_BAND_EDGE_EV):
        return "hot-substorm-plasma"
    return "energetic-electron-population"


def sheath_ratio(screening_length_m, characteristic_length_m):
    """debye-length divided by the characteristic length of the body."""
    screening = _positive(screening_length_m, "screening_length_m")
    body = _positive(characteristic_length_m, "characteristic_length_m")
    return screening / body


def sheath_regime(screening_length_m, characteristic_length_m):
    """'thin-sheath', 'transitional-sheath' or 'thick-sheath'."""
    ratio = sheath_ratio(screening_length_m, characteristic_length_m)
    if ratio < THIN_SHEATH_RATIO or math.isclose(
        ratio, THIN_SHEATH_RATIO, rel_tol=_RATIO_TOLERANCE, abs_tol=0.0
    ):
        return "thin-sheath"
    if ratio > THICK_SHEATH_RATIO or math.isclose(
        ratio, THICK_SHEATH_RATIO, rel_tol=_RATIO_TOLERANCE, abs_tol=0.0
    ):
        return "thick-sheath"
    return "transitional-sheath"


_POPULATION_RISKS = {
    "cold-ionospheric-plasma": ("ram-wake-potential-asymmetry",),
    "warm-magnetospheric-plasma": ("auroral-frame-potential-excursion",),
    "hot-substorm-plasma": (
        "absolute-frame-potential-excursion",
        "differential-surface-potential",
    ),
    "energetic-electron-population": (
        "buried-charge-breakdown",
        "internal-charge-deposition",
    ),
}


def charging_risk_families(
    population, regime, high_voltage_array=False, eclipse_exposed=False
):
    """Sorted, de-duplicated risk families implied by population and regime."""
    if population not in _POPULATION_RISKS:
        raise ValueError("unknown plasma population %r" % (population,))
    if regime not in ("thin-sheath", "transitional-sheath", "thick-sheath"):
        raise ValueError("unknown sheath regime %r" % (regime,))
    _flag(high_voltage_array, "high_voltage_array")
    _flag(eclipse_exposed, "eclipse_exposed")
    risks = set(_POPULATION_RISKS[population])
    if high_voltage_array and regime == "thin-sheath":
        risks.add("high-voltage-array-arcing")
    if eclipse_exposed and population in (
        "warm-magnetospheric-plasma",
        "hot-substorm-plasma",
    ):
        risks.add("eclipse-entry-potential-transient")
    return tuple(sorted(risks))


def potential_build_up_time(
    capacitance_f, area_m2, current_density_a_m2, target_potential_v
):
    """Seconds to reach a frame potential at a collected current density."""
    capacitance = _positive(capacitance_f, "capacitance_f")
    area = _positive(area_m2, "area_m2")
    flux = _positive(current_density_a_m2, "current_density_a_m2")
    if isinstance(target_potential_v, bool) or not isinstance(
        target_potential_v, (int, float)
    ):
        raise ValueError("target_potential_v must be a real number")
    potential = abs(float(target_potential_v))
    if potential == 0.0:
        raise ValueError("target_potential_v must be non-zero")
    return capacitance * potential / (flux * area)


def screen_environment(record):
    """Full screening of one environment record."""
    env = normalize_environment(record)
    screening = debye_length(
        env["electron_density_m3"], env["electron_temperature_ev"]
    )
    flux = electron_thermal_flux(
        env["electron_density_m3"], env["electron_temperature_ev"]
    )
    population = categorize_population(env["electron_temperature_ev"])
    regime = sheath_regime(screening, env["characteristic_length_m"])
    risks = charging_risk_families(
        population,
        regime,
        high_voltage_array=env["high_voltage_array"],
        eclipse_exposed=env["eclipse_exposed"],
    )
    return {
        "name": env["name"],
        "debye_length_m": screening,
        "electron_thermal_flux_a_m2": flux,
        "population": population,
        "density_class": density_class(env["electron_density_m3"]),
        "sheath_ratio": sheath_ratio(screening, env["characteristic_length_m"]),
        "sheath_regime": regime,
        "risk_families": risks,
        "internal_deposition_driver": population == "energetic-electron-population",
    }


def worst_case_environment(records):
    """Record with the highest electron-temperature; density breaks a tie."""
    try:
        rows = list(records)
    except TypeError:
        raise ValueError("records must be an iterable of environment mappings")
    if not rows:
        raise ValueError("at least one environment record is required")
    normalized = [normalize_environment(row) for row in rows]
    return max(
        normalized,
        key=lambda env: (env["electron_temperature_ev"], env["electron_density_m3"]),
    )


def summarize_environments(records):
    """Screen every record and union the risk families across the mission."""
    try:
        rows = list(records)
    except TypeError:
        raise ValueError("records must be an iterable of environment mappings")
    if not rows:
        raise ValueError("at least one environment record is required")
    screened = [screen_environment(row) for row in rows]
    risks = set()
    for item in screened:
        risks.update(item["risk_families"])
    worst = worst_case_environment(rows)
    return {
        "count": len(screened),
        "screened": tuple(screened),
        "risk_families": tuple(sorted(risks)),
        "worst_case": worst["name"],
        "internal_deposition_credible": any(
            item["internal_deposition_driver"] for item in screened
        ),
    }

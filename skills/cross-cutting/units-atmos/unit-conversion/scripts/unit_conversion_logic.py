#!/usr/bin/env python3
"""Aerospace unit conversion logic (deterministic factor tables, stdlib).

Converts between SI and imperial/aviation units for the quantities an
aerospace engineer meets daily: length, speed (including Mach),
temperature (offset scales), pressure, density, mass, and force.
Altitude helpers relate pressure altitude to the ISA pressure field
and geometric altitude to geopotential altitude. The standard
atmosphere context is common reference data (NACA TR-824 is
public-domain US government work; only the context is referenced,
nothing is reproduced).

Every conversion routes through one canonical base unit per quantity:
m, m/s, K, Pa, kg/m3, kg, N. Factors are exact where the unit system
defines them (0.3048 m/ft, 1852 m/NM, 0.45359237 kg/lb,
4.4482216152605 N/lbf) and standard reference values otherwise.

Unit tokens are case-insensitive; '^' is ignored so 'kg/m^3' and
'slug/ft^3' work. Invalid units raise ValueError. Offline, stdlib
only, no network.
"""

import math

# --- canonical constants -----------------------------------------------------

M_PER_FT = 0.3048               # exact: 1 ft = 0.3048 m
M_PER_NM = 1852.0               # exact: 1 NM = 1852 m
M_PER_S_PER_KT = M_PER_NM / 3600.0  # 1 kt = 1852/3600 = 0.514444... m/s
KELVIN_OFFSET = 273.15          # K = C + 273.15
RANKINE_PER_KELVIN = 9.0 / 5.0  # R = K * 9/5
PA_PER_HPA = 100.0              # exact: 1 hPa = 100 Pa
PA_PER_PSI = 6894.757293168     # exact (lb-ft-s system definition)
PA_PER_INHG = 3386.389          # standard reference value at 0 degC
KGM3_PER_SLUGFT3 = 515.3788184  # slug/ft3 -> kg/m3 (derived from lb and ft)
KG_PER_LB = 0.45359237          # exact
KG_PER_SLUG = 14.59390294       # exact (32.174049 lb)
N_PER_LBF = 4.4482216152605     # exact: 0.45359237 kg * 9.80665 m/s2

# ISA sea-level speed of sound, default Mach reference (m/s)
SPEED_OF_SOUND_SL = 340.294

# ISA constants for pressure altitude and geopotential altitude
G = 9.80665          # m/s2
R_AIR = 287.05       # J/(kg K)
LAPSE = 0.0065       # K/m
T0 = 288.15          # K
P0 = 101325.0        # Pa
EARTH_RADIUS_M = 6356766.0  # nominal Earth radius used by the ISA model

# --- factor tables: unit token -> factor to the canonical base ---------------

LENGTH_TO_M = {"m": 1.0, "ft": M_PER_FT, "nm": M_PER_NM}
SPEED_TO_MPS = {"m/s": 1.0, "kt": M_PER_S_PER_KT, "ft/s": M_PER_FT}
PRESSURE_TO_PA = {
    "pa": 1.0,
    "hpa": PA_PER_HPA,
    "psi": PA_PER_PSI,
    "inhg": PA_PER_INHG,
}
DENSITY_TO_KGM3 = {"kg/m3": 1.0, "slug/ft3": KGM3_PER_SLUGFT3}
MASS_TO_KG = {"kg": 1.0, "lb": KG_PER_LB, "slug": KG_PER_SLUG}
FORCE_TO_N = {"n": 1.0, "lbf": N_PER_LBF}

# accepted spellings, normalized to the canonical tokens above
LENGTH_ALIASES = {
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "foot": "ft", "feet": "ft",
    "nmi": "nm", "nautical-mile": "nm", "nautical-miles": "nm",
}
SPEED_ALIASES = {
    "mps": "m/s", "meters-per-second": "m/s", "metres-per-second": "m/s",
    "kts": "kt", "knot": "kt", "knots": "kt",
    "fps": "ft/s", "feet-per-second": "ft/s",
}
PRESSURE_ALIASES = {
    "hectopascal": "hpa", "hectopascals": "hpa",
    "pound-per-square-inch": "psi", "pounds-per-square-inch": "psi",
    "inches-of-mercury": "inhg", "inhg": "inhg",
}
DENSITY_ALIASES = {
    "kilograms-per-cubic-meter": "kg/m3",
    "slugs-per-cubic-foot": "slug/ft3",
}
MASS_ALIASES = {
    "kilograms": "kg", "kilogram": "kg",
    "lbs": "lb", "pound": "lb", "pounds": "lb",
}
FORCE_ALIASES = {
    "newton": "n", "newtons": "n",
    "pound-force": "lbf", "pounds-force": "lbf",
}
TEMP_TOKENS = ("k", "c", "f", "r")
TEMP_ALIASES = {
    "kelvin": "k", "celsius": "c", "centigrade": "c", "degc": "c",
    "fahrenheit": "f", "degf": "f", "rankine": "r",
}


def _temp_token(unit):
    """Resolve a temperature unit token to k/c/f/r or raise."""
    key = _norm(unit)
    key = TEMP_ALIASES.get(key, key)
    if key not in TEMP_TOKENS:
        raise ValueError(
            "unknown temperature unit %r; valid: k, c, f, r" % (unit,)
        )
    return key


def _norm(unit):
    """Lowercase a unit token and drop '^' so kg/m^3 == kg/m3."""
    return str(unit).strip().lower().replace("^", "")


def _canon(table, aliases, unit, quantity):
    """Resolve a user unit token to a canonical table key or raise."""
    key = _norm(unit)
    key = aliases.get(key, key)
    if key not in table:
        valid = ", ".join(sorted(table))
        raise ValueError(
            "unknown %s unit %r; valid units: %s" % (quantity, unit, valid)
        )
    return key


def _convert(value, from_unit, to_unit, table, aliases, quantity):
    """Generic factor-table conversion through the canonical base."""
    f = _canon(table, aliases, from_unit, quantity)
    t = _canon(table, aliases, to_unit, quantity)
    return value * table[f] / table[t]


# --- length ------------------------------------------------------------------

def convert_length(value, from_unit, to_unit):
    """Convert length between m, ft, NM (base: meter)."""
    return _convert(value, from_unit, to_unit, LENGTH_TO_M, LENGTH_ALIASES,
                    "length")


# --- speed -------------------------------------------------------------------

def convert_speed(value, from_unit, to_unit, speed_of_sound_mps=SPEED_OF_SOUND_SL):
    """Convert speed between m/s, kt, ft/s, Mach (base: m/s).

    Mach is a ratio: value_mach * speed_of_sound_mps gives m/s. The
    default speed of sound is the ISA sea-level value 340.294 m/s;
    pass the flight-condition value for altitude-corrected Mach.
    """
    if speed_of_sound_mps <= 0:
        raise ValueError(
            "speed_of_sound_mps must be > 0, got %r" % (speed_of_sound_mps,)
        )
    f = _norm(from_unit)
    f = SPEED_ALIASES.get(f, f)
    t = _norm(to_unit)
    t = SPEED_ALIASES.get(t, t)
    valid = set(SPEED_TO_MPS) | {"mach"}
    if f not in valid or t not in valid:
        raise ValueError(
            "unknown speed unit (from %r, to %r); valid units: %s"
            % (from_unit, to_unit, ", ".join(sorted(valid)))
        )
    if f == "mach" or t == "mach":
        if f == "mach" and t == "mach":
            return value
        if f == "mach":
            return value * speed_of_sound_mps / SPEED_TO_MPS[t]
        return value * SPEED_TO_MPS[f] / speed_of_sound_mps
    return value * SPEED_TO_MPS[f] / SPEED_TO_MPS[t]


def mach_from_speed(speed_mps, speed_of_sound_mps):
    """Mach number from true airspeed (m/s) and speed of sound (m/s)."""
    if speed_of_sound_mps <= 0:
        raise ValueError(
            "speed_of_sound_mps must be > 0, got %r" % (speed_of_sound_mps,)
        )
    return speed_mps / speed_of_sound_mps


# --- temperature (offset scales, NOT plain factors) --------------------------

def _to_kelvin(value, unit):
    if unit == "k":
        return value
    if unit == "c":
        return value + KELVIN_OFFSET
    if unit == "f":
        return (value + 459.67) * 5.0 / 9.0
    if unit == "r":
        return value * 5.0 / 9.0
    raise ValueError("unknown temperature unit %r" % (unit,))


def _from_kelvin(value, unit):
    if unit == "k":
        return value
    if unit == "c":
        return value - KELVIN_OFFSET
    if unit == "f":
        return value * RANKINE_PER_KELVIN - 459.67
    if unit == "r":
        return value * RANKINE_PER_KELVIN
    raise ValueError("unknown temperature unit %r" % (unit,))


def convert_temperature(value, from_unit, to_unit):
    """Convert temperature between K, C, F, R.

    Offset scales need the affine map, not a factor: the code goes
    value -> kelvin -> target. 0 C == 273.15 K == 32 F == 491.67 R.
    """
    f = _temp_token(from_unit)
    t = _temp_token(to_unit)
    return _from_kelvin(_to_kelvin(value, f), t)


# --- pressure, density, mass, force ------------------------------------------

def convert_pressure(value, from_unit, to_unit):
    """Convert pressure between Pa, hPa, psi, inHg (base: pascal)."""
    return _convert(value, from_unit, to_unit, PRESSURE_TO_PA,
                    PRESSURE_ALIASES, "pressure")


def convert_density(value, from_unit, to_unit):
    """Convert density between kg/m3 and slug/ft3 (base: kg/m3)."""
    return _convert(value, from_unit, to_unit, DENSITY_TO_KGM3,
                    DENSITY_ALIASES, "density")


def convert_mass(value, from_unit, to_unit):
    """Convert mass between kg, lb, slug (base: kilogram)."""
    return _convert(value, from_unit, to_unit, MASS_TO_KG, MASS_ALIASES,
                    "mass")


def convert_force(value, from_unit, to_unit):
    """Convert force between N and lbf (base: newton)."""
    return _convert(value, from_unit, to_unit, FORCE_TO_N, FORCE_ALIASES,
                    "force")


# --- altitude conventions ------------------------------------------------------

def pressure_altitude_m(pressure_pa):
    """Pressure altitude (m): inverse ISA troposphere for a pressure.

    The altitude at which the ISA pressure field equals the given
    static pressure; what an altimeter set to 1013.25 hPa (29.92 inHg)
    reads. Pressures at or above ISA sea level return 0.0 m. Valid in
    the troposphere (pressure >= tropopause pressure, about 22632 Pa).
    """
    if pressure_pa <= 0:
        raise ValueError(
            "pressure_pa must be > 0, got %r" % (pressure_pa,)
        )
    if pressure_pa >= P0:
        return 0.0
    return T0 / LAPSE * (1.0 - (pressure_pa / P0) ** (R_AIR * LAPSE / G))


def geometric_to_geopotential_m(h_geom):
    """Geometric altitude (m) to geopotential altitude (m).

    Geopotential altitude removes the inverse-square gravity falloff
    with the nominal Earth radius R_E: h_gp = h * R_E / (R_E + h).
    Flight-mechanics tables use geopotential altitude; barometric and
    radar measurements are geometric.
    """
    if h_geom <= -EARTH_RADIUS_M:
        raise ValueError(
            "h_geom must be > -R_E, got %r" % (h_geom,)
        )
    return h_geom * EARTH_RADIUS_M / (EARTH_RADIUS_M + h_geom)


def geopotential_to_geometric_m(h_geop):
    """Geopotential altitude (m) to geometric altitude (m). Inverse map."""
    if h_geop >= EARTH_RADIUS_M:
        raise ValueError(
            "h_geop must be < R_E, got %r" % (h_geop,)
        )
    return h_geop * EARTH_RADIUS_M / (EARTH_RADIUS_M - h_geop)


def convert_altitude(value, from_unit, to_unit):
    """Convert altitude between geometric (geom) and geopotential (geop)."""
    f = _norm(from_unit)
    t = _norm(to_unit)
    if f not in ("geom", "geopotential") or t not in ("geom", "geopotential"):
        raise ValueError(
            "unknown altitude convention %r; valid: geom, geopotential"
            % (from_unit if f not in ("geom", "geopotential") else to_unit,)
        )
    if f == t:
        return value
    if f == "geom":
        return geometric_to_geopotential_m(value)
    return geopotential_to_geometric_m(value)


# --- reference ---------------------------------------------------------------

def reference_factors():
    """Return the canonical factor tables for documentation checks."""
    return {
        "length_to_m": LENGTH_TO_M,
        "speed_to_mps": SPEED_TO_MPS,
        "pressure_to_pa": PRESSURE_TO_PA,
        "density_to_kgm3": DENSITY_TO_KGM3,
        "mass_to_kg": MASS_TO_KG,
        "force_to_n": FORCE_TO_N,
        "speed_of_sound_sl_mps": SPEED_OF_SOUND_SL,
    }

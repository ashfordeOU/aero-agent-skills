"""Orbits of a mission and what they do to its communication links.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.5 -- orbits. Paraphrased into an
implementable procedure; no standard text is reproduced.

Two normative items sit here and they are separate obligations:

  1. the orbit flown in each mission phase is declared, so no phase reaches
     the link budget without one;
  2. the consequences of those orbits for the communication system are
     derived -- slant range, propagation delay, Doppler shift and the pass a
     ground station actually gets -- and compared against what the link and
     its receivers can absorb.

The geometry used is the circular orbit and an overhead pass:

  slant range at elevation e   sqrt(r^2 - (Re cos e)^2) - Re sin e
  orbital speed                sqrt(mu / r)
  orbital period               2 pi sqrt(r^3 / mu)
  maximum range rate           v sqrt(1 - (Re / r)^2)
  Doppler shift                fc * range rate / c
  pass duration                (acos(Re cos e / r) - e) * T / pi

The pass duration neglects Earth rotation and takes the pass through the
zenith, so it is the longest pass the geometry allows rather than the pass a
given station gets on a given day. For an orbit close to synchronous that
assumption understates real visibility badly, which is a property of the model
and is reported as such rather than patched with a fudge.

Every comparison against an allowance carries a relative tolerance, so an
orbit sized to land exactly on a stated limit is inside it on every machine.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "COMPLIANT",
    "DECLARATION_INCOMPLETE",
    "OUT_OF_ALLOWANCE",
    "REL_TOL",
    "EARTH_RADIUS_KM",
    "EARTH_MU_KM3_S2",
    "LIGHT_SPEED_KM_S",
    "validate_altitude_km",
    "validate_elevation_deg",
    "validate_frequency_hz",
    "orbital_radius_km",
    "orbital_speed_km_s",
    "orbital_period_s",
    "slant_range_km",
    "one_way_delay_s",
    "round_trip_delay_s",
    "max_range_rate_km_s",
    "max_doppler_shift_hz",
    "max_pass_duration_s",
    "within_allowance",
    "link_implications",
    "normalize_phases",
    "undeclared_phases",
    "orphan_orbit_declarations",
    "assess_orbits",
]

COMPLIANT = "compliant"
DECLARATION_INCOMPLETE = "declaration-incomplete"
OUT_OF_ALLOWANCE = "out-of-allowance"

# Relative tolerance on every allowance comparison, so a value written to sit
# exactly on its limit is inside it rather than decided by rounding.
REL_TOL = 1e-9

EARTH_RADIUS_KM = 6378.137
EARTH_MU_KM3_S2 = 398600.4418
LIGHT_SPEED_KM_S = 299792.458


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def validate_altitude_km(value, name="altitude_km"):
    """Return a strictly positive circular orbit altitude in kilometres."""
    altitude = _validate_number(value, name)
    if altitude <= 0.0:
        raise ValueError(
            "%s must be above the surface, got %r" % (name, value)
        )
    return altitude


def validate_elevation_deg(value, name="min_elevation_deg"):
    """Return a ground station mask elevation in [0, 90) degrees."""
    elevation = _validate_number(value, name)
    if elevation < 0.0 or elevation >= 90.0:
        raise ValueError(
            "%s must be at least 0 and below 90 degrees, got %r" % (name, value)
        )
    return elevation


def validate_frequency_hz(value, name="carrier_hz"):
    """Return a strictly positive carrier frequency in hertz."""
    frequency = _validate_number(value, name)
    if frequency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return frequency


def orbital_radius_km(altitude_km):
    """Return the orbit radius from the centre of the Earth."""
    return EARTH_RADIUS_KM + validate_altitude_km(altitude_km)


def orbital_speed_km_s(altitude_km):
    """Return the circular orbit speed."""
    return math.sqrt(EARTH_MU_KM3_S2 / orbital_radius_km(altitude_km))


def orbital_period_s(altitude_km):
    """Return the circular orbit period."""
    radius = orbital_radius_km(altitude_km)
    return 2.0 * math.pi * math.sqrt(radius ** 3 / EARTH_MU_KM3_S2)


def slant_range_km(altitude_km, min_elevation_deg):
    """Return the slant range to the satellite at the mask elevation."""
    radius = orbital_radius_km(altitude_km)
    elevation = math.radians(validate_elevation_deg(min_elevation_deg))
    horizontal = EARTH_RADIUS_KM * math.cos(elevation)
    return math.sqrt(radius * radius - horizontal * horizontal) - EARTH_RADIUS_KM * math.sin(
        elevation
    )


def one_way_delay_s(range_km):
    """Return the one way propagation delay over a slant range."""
    distance = _validate_number(range_km, "range_km")
    if distance < 0.0:
        raise ValueError("range_km must not be negative, got %r" % (range_km,))
    return distance / LIGHT_SPEED_KM_S


def round_trip_delay_s(range_km):
    """Return the round trip propagation delay over a slant range."""
    return 2.0 * one_way_delay_s(range_km)


def max_range_rate_km_s(altitude_km):
    """Return the largest line of sight rate an overhead pass produces."""
    radius = orbital_radius_km(altitude_km)
    ratio = EARTH_RADIUS_KM / radius
    return orbital_speed_km_s(altitude_km) * math.sqrt(1.0 - ratio * ratio)


def max_doppler_shift_hz(carrier_hz, altitude_km):
    """Return the largest Doppler shift the orbit imposes on a carrier."""
    carrier = validate_frequency_hz(carrier_hz)
    return carrier * max_range_rate_km_s(altitude_km) / LIGHT_SPEED_KM_S


def max_pass_duration_s(altitude_km, min_elevation_deg):
    """Return the longest pass the geometry allows above the mask.

    Earth rotation is neglected and the pass is taken through the zenith, so
    this bounds a real pass from above for a low orbit. Near synchronous
    altitude the neglected rotation dominates and the number understates the
    visibility a station really has.
    """
    radius = orbital_radius_km(altitude_km)
    elevation = math.radians(validate_elevation_deg(min_elevation_deg))
    half_angle = math.acos(EARTH_RADIUS_KM * math.cos(elevation) / radius) - elevation
    if half_angle <= 0.0:
        return 0.0
    return half_angle * orbital_period_s(altitude_km) / math.pi


def within_allowance(value, limit, direction="max"):
    """Return True where a value is inside its limit, tolerating the bound."""
    observed = _validate_number(value, "value")
    bound = _validate_number(limit, "limit")
    scale = max(abs(observed), abs(bound), 1.0)
    if direction == "max":
        return observed <= bound + REL_TOL * scale
    if direction == "min":
        return observed >= bound - REL_TOL * scale
    raise ValueError("direction must be 'max' or 'min', got %r" % (direction,))


def link_implications(orbit, carrier_hz):
    """Return what one declared orbit does to the communication link."""
    if not isinstance(orbit, dict):
        raise ValueError("orbit must be a mapping")
    altitude = validate_altitude_km(orbit.get("altitude_km"))
    elevation = validate_elevation_deg(orbit.get("min_elevation_deg"))
    carrier = validate_frequency_hz(carrier_hz)
    reach = slant_range_km(altitude, elevation)
    return {
        "altitude_km": altitude,
        "min_elevation_deg": elevation,
        "orbit_radius_km": orbital_radius_km(altitude),
        "orbital_period_s": orbital_period_s(altitude),
        "slant_range_km": reach,
        "one_way_delay_s": one_way_delay_s(reach),
        "round_trip_delay_s": round_trip_delay_s(reach),
        "max_range_rate_km_s": max_range_rate_km_s(altitude),
        "max_doppler_shift_hz": max_doppler_shift_hz(carrier, altitude),
        "max_pass_duration_s": max_pass_duration_s(altitude, elevation),
    }


def normalize_phases(phases):
    """Return the mission phases as a tuple, in mission order.

    Taken once and reused, so a caller passing a one-shot iterator does not
    see a phase list that empties itself between the two checks.
    """
    if isinstance(phases, (str, bytes)) or not hasattr(phases, "__iter__"):
        raise ValueError("phases must be a sequence of phase names")
    ordered = []
    seen = set()
    for item in phases:
        if isinstance(item, bool) or not isinstance(item, str):
            raise ValueError("phase name must be a string, got %r" % (item,))
        token = item.strip()
        if not token:
            raise ValueError("phase name must not be blank")
        if token in seen:
            raise ValueError("phase %r is declared twice" % token)
        seen.add(token)
        ordered.append(token)
    if not ordered:
        raise ValueError("phases must name at least one mission phase")
    return tuple(ordered)


def undeclared_phases(phases, orbits):
    """Return mission phases with no orbit declared, in mission order."""
    if not isinstance(orbits, dict):
        raise ValueError("orbits must be a mapping of phase name to orbit")
    return tuple(p for p in normalize_phases(phases) if p not in orbits)


def orphan_orbit_declarations(phases, orbits):
    """Return declared orbits that belong to no mission phase."""
    if not isinstance(orbits, dict):
        raise ValueError("orbits must be a mapping of phase name to orbit")
    return tuple(sorted(set(orbits) - set(normalize_phases(phases))))


def assess_orbits(mission):
    """Grade both normative items: orbits declared, implications derived."""
    if not isinstance(mission, dict):
        raise ValueError("mission must be a mapping")
    orbits = mission.get("orbits") or {}
    if not isinstance(orbits, dict):
        raise ValueError("orbits must be a mapping of phase name to orbit")
    phases = normalize_phases(mission.get("phases"))
    carrier = validate_frequency_hz(mission.get("carrier_hz"))
    allowances = mission.get("allowances") or {}
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping")
    absent = undeclared_phases(phases, orbits)
    orphans = orphan_orbit_declarations(phases, orbits)
    per_phase = {}
    findings = []
    for name in phases:
        if name not in orbits:
            continue
        derived = link_implications(orbits[name], carrier)
        per_phase[name] = derived
        limit = allowances.get("max_round_trip_delay_s")
        if limit is not None and not within_allowance(
            derived["round_trip_delay_s"], limit, "max"
        ):
            findings.append(
                "%s round trip delay %.6g s exceeds the %.6g s allowance"
                % (name, derived["round_trip_delay_s"], limit)
            )
        limit = allowances.get("max_doppler_shift_hz")
        if limit is not None and not within_allowance(
            derived["max_doppler_shift_hz"], limit, "max"
        ):
            findings.append(
                "%s Doppler shift %.6g Hz exceeds the %.6g Hz receiver pull-in range"
                % (name, derived["max_doppler_shift_hz"], limit)
            )
        limit = allowances.get("min_pass_duration_s")
        if limit is not None and not within_allowance(
            derived["max_pass_duration_s"], limit, "min"
        ):
            findings.append(
                "%s pass of %.6g s is shorter than the %.6g s the phase needs"
                % (name, derived["max_pass_duration_s"], limit)
            )
    for phase in absent:
        findings.append("phase %s reaches the link budget with no orbit declared" % phase)
    for phase in orphans:
        findings.append("an orbit is declared for %s, which is not a mission phase" % phase)
    if absent or orphans:
        verdict = DECLARATION_INCOMPLETE
    elif findings:
        verdict = OUT_OF_ALLOWANCE
    else:
        verdict = COMPLIANT
    return {
        "phase_count": len(phases),
        "undeclared_phases": absent,
        "orphan_declarations": orphans,
        "implications": per_phase,
        "declaration_complete": not absent and not orphans,
        "verdict": verdict,
        "findings": tuple(findings),
    }

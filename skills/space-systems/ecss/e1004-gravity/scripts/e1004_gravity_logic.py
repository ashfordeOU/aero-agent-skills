#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 4.2 gravity environment model selection and
magnitude/gradient logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
gravity environment for an Earth-orbiting mission combines the Earth
gravity field (point-mass plus geopotential terms), third-body
(Sun/Moon) perturbations, and solid-Earth-tide perturbations. Which
terms matter depends on the orbit regime (LEO needs a high-degree
geopotential; MEO/GEO/HEO need third-body terms as a dominant effect)
and on how long the environment must stay valid (long durations need
tide accumulation, and for LEO, third-body terms too). Gravitational
acceleration magnitude and its radial gradient follow the point-mass
relations g = GM/r^2 and dg/dr = -2*GM/r^3. This module implements the
model-selection, perturbation-term-coverage, altitude-validity,
magnitude, and gradient logic; it does not implement the geopotential
spherical-harmonic expansion itself or ephemeris-based third-body/tide
computation.
"""

EARTH_GM_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6378137.0

MISSION_DURATION_TIDE_THRESHOLD_DAYS = 365.0

MODEL_BY_ORBIT_REGIME = {
    "leo": "high-degree Earth geopotential model (EGM-class spherical harmonics)",
    "meo": "low-degree Earth geopotential model (J2-dominant zonal terms)",
    "geo": "low-degree Earth geopotential model (J2-dominant zonal terms)",
    "heo": "low-degree Earth geopotential model (J2-dominant zonal terms)",
}

BASE_REQUIRED_TERMS_BY_REGIME = {
    "leo": frozenset({"earth_geopotential_high_degree"}),
    "meo": frozenset({"earth_geopotential_low_degree", "third_body"}),
    "geo": frozenset({"earth_geopotential_low_degree", "third_body"}),
    "heo": frozenset({"earth_geopotential_low_degree", "third_body"}),
}

VALIDITY_ALTITUDE_RANGE_M = {
    "leo": (160000.0, 2000000.0),
    "meo": (2000000.0, 31000000.0),
    "geo": (35586000.0, 35986000.0),
    "heo": (200000.0, 40000000.0),
}


def select_gravity_model(orbit_regime):
    """Reference Earth gravity model name for one orbit regime ("leo",
    "meo", "geo", or "heo"). Raises ValueError for an unknown regime."""
    if orbit_regime not in MODEL_BY_ORBIT_REGIME:
        raise ValueError("unknown orbit regime: %r" % (orbit_regime,))
    return MODEL_BY_ORBIT_REGIME[orbit_regime]


def required_perturbation_terms(orbit_regime, mission_duration_days):
    """Minimum perturbation term set required for one orbit regime and
    mission duration (days). MEO/GEO/HEO always require third-body
    terms; any regime whose duration exceeds the tide-accumulation
    threshold also requires the solid-Earth-tide term (and, for LEO,
    the third-body term as well). Raises ValueError for an unknown
    regime or a negative duration."""
    if orbit_regime not in BASE_REQUIRED_TERMS_BY_REGIME:
        raise ValueError("unknown orbit regime: %r" % (orbit_regime,))
    if mission_duration_days < 0:
        raise ValueError("mission duration must not be negative")
    terms = set(BASE_REQUIRED_TERMS_BY_REGIME[orbit_regime])
    if mission_duration_days > MISSION_DURATION_TIDE_THRESHOLD_DAYS:
        terms.add("third_body")
        terms.add("solid_earth_tide")
    return frozenset(terms)


def perturbation_terms_adequate(orbit_regime, mission_duration_days, included_terms):
    """True when included_terms is a superset of the terms required
    for orbit_regime and mission_duration_days."""
    required = required_perturbation_terms(orbit_regime, mission_duration_days)
    return required.issubset(set(included_terms))


def validity_altitude_range(orbit_regime):
    """(min_altitude_m, max_altitude_m) validity range of the selected
    gravity model for one orbit regime. Raises ValueError for an
    unknown regime."""
    if orbit_regime not in VALIDITY_ALTITUDE_RANGE_M:
        raise ValueError("unknown orbit regime: %r" % (orbit_regime,))
    return VALIDITY_ALTITUDE_RANGE_M[orbit_regime]


def altitude_in_validity_range(orbit_regime, altitude_m):
    """True when altitude_m falls inside the validity range of the
    gravity model selected for orbit_regime."""
    min_altitude, max_altitude = validity_altitude_range(orbit_regime)
    return min_altitude <= altitude_m <= max_altitude


def orbital_radius_m(altitude_m):
    """Distance from Earth's center for a given altitude above the
    surface (meters). Raises ValueError when altitude_m is negative."""
    if altitude_m < 0:
        raise ValueError("altitude must not be negative")
    return EARTH_RADIUS_M + altitude_m


def gravity_magnitude(radius_m):
    """Point-mass gravitational acceleration magnitude (m/s^2) at
    radius_m from Earth's center: GM/r^2. Raises ValueError when
    radius_m is not positive."""
    if radius_m <= 0:
        raise ValueError("radius must be positive")
    return EARTH_GM_M3_S2 / (radius_m ** 2)


def gravity_gradient_magnitude(radius_m):
    """Magnitude of the radial gravity gradient (1/s^2), |dg/dr|, at
    radius_m from Earth's center: 2*GM/r^3. Raises ValueError when
    radius_m is not positive."""
    if radius_m <= 0:
        raise ValueError("radius must be positive")
    return 2.0 * EARTH_GM_M3_S2 / (radius_m ** 3)


def assess_gravity_case(case):
    """Full gravity model-selection and compliance assessment for one
    case dict. Required keys: id, orbit_regime, altitude_m,
    mission_duration_days, included_terms. Returns a new dict; does
    not mutate the input. Raises ValueError when 'id' is missing or
    orbit_regime is unknown."""
    if "id" not in case:
        raise ValueError("gravity case is missing an id")
    orbit_regime = case["orbit_regime"]
    model = select_gravity_model(orbit_regime)
    altitude_m = case["altitude_m"]
    mission_duration_days = case["mission_duration_days"]
    included_terms = case["included_terms"]
    required_terms = required_perturbation_terms(orbit_regime, mission_duration_days)
    terms_ok = perturbation_terms_adequate(
        orbit_regime, mission_duration_days, included_terms
    )
    altitude_ok = altitude_in_validity_range(orbit_regime, altitude_m)
    radius_m = orbital_radius_m(altitude_m)
    magnitude = gravity_magnitude(radius_m)
    gradient = gravity_gradient_magnitude(radius_m)
    return {
        "id": case["id"],
        "orbit_regime": orbit_regime,
        "model": model,
        "altitude_m": altitude_m,
        "required_terms": sorted(required_terms),
        "included_terms": sorted(set(included_terms)),
        "terms_adequate": terms_ok,
        "altitude_valid": altitude_ok,
        "gravity_magnitude_m_s2": magnitude,
        "gravity_gradient_1_s2": gradient,
        "compliant": terms_ok and altitude_ok,
    }


def build_gravity_assessment(cases):
    """Assessment record: one assess_gravity_case() result per case,
    in input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_gravity_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate gravity case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support the gravity environment definition
    as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0

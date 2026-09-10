#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex I (informative) particle radiation reference
data (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
Annex I points a mission engineer at the standard reference models for
each particle radiation population rather than defining the models
itself. Trapped protons and trapped electrons are covered by the
AP-8/AP-9 and AE-8/AE-9 belt model families respectively, each valid
over a bounded energy and altitude range; the South Atlantic Anomaly
is a regional enhancement of the inner trapped-proton belt, not a
separate population, and only matters for a low-earth-orbit ground
track that both crosses its altitude band and reaches its
characteristic latitude. Solar energetic particle (SEP) events and
galactic cosmic rays (GCR) are not geomagnetically confined the way
trapped populations are: outside low-earth orbit they always apply,
and inside low-earth orbit they only apply once the orbit inclination
is high enough that the geomagnetic field no longer excludes them.
Albedo neutrons are produced by cosmic-ray interaction with the upper
atmosphere and are only modeled over a bounded low-earth/medium-earth
altitude band. This module implements the model-applicability lookup
by population and orbit regime, the geomagnetic-shielding and South
Atlantic Anomaly determinations that gate low-earth-orbit
applicability, and the energy/altitude range validation for a
selected model; it does not implement any model's internal flux or
fluence computation.
"""

TRAPPED_PROTON = "trapped_proton"
TRAPPED_ELECTRON = "trapped_electron"
SOLAR_ENERGETIC_PARTICLE = "solar_energetic_particle"
GALACTIC_COSMIC_RAY = "galactic_cosmic_ray"
ALBEDO_NEUTRON = "albedo_neutron"

ORBIT_REGIMES = frozenset({"leo", "meo", "geo", "gto", "heo", "interplanetary"})

# Reference-model catalog: energy coverage (MeV), altitude coverage (km,
# None when the population is not altitude-bound), and the orbit regimes
# the model is cataloged against directly. Ranges are reference data, not
# verbatim standard text.
MODEL_CATALOG = {
    TRAPPED_PROTON: {
        "model_id": "AP-8/AP-9 trapped proton model",
        "min_energy_mev": 0.1,
        "max_energy_mev": 400.0,
        "min_altitude_km": 200.0,
        "max_altitude_km": 40000.0,
        "applicable_regimes": frozenset({"leo", "meo", "gto", "heo"}),
    },
    TRAPPED_ELECTRON: {
        "model_id": "AE-8/AE-9 trapped electron model",
        "min_energy_mev": 0.04,
        "max_energy_mev": 7.0,
        "min_altitude_km": 200.0,
        "max_altitude_km": 40000.0,
        "applicable_regimes": frozenset({"leo", "meo", "geo", "gto", "heo"}),
    },
    SOLAR_ENERGETIC_PARTICLE: {
        "model_id": "ESP worst-case SEP fluence model",
        "min_energy_mev": 1.0,
        "max_energy_mev": 500.0,
        "min_altitude_km": None,
        "max_altitude_km": None,
        "applicable_regimes": frozenset({"geo", "gto", "heo", "interplanetary"}),
    },
    GALACTIC_COSMIC_RAY: {
        "model_id": "ISO-15390 GCR model",
        "min_energy_mev": 10.0,
        "max_energy_mev": 1000000.0,
        "min_altitude_km": None,
        "max_altitude_km": None,
        "applicable_regimes": frozenset({"geo", "gto", "heo", "interplanetary"}),
    },
    ALBEDO_NEUTRON: {
        "model_id": "cosmic-ray albedo neutron model",
        "min_energy_mev": 1e-8,
        "max_energy_mev": 1000.0,
        "min_altitude_km": 200.0,
        "max_altitude_km": 2000.0,
        "applicable_regimes": frozenset({"leo", "meo"}),
    },
}

# Populations that are not geomagnetically trapped: outside LEO they always
# apply, inside LEO their applicability is gated by geomagnetic shielding
# rather than by the static applicable_regimes membership above.
SHIELDING_SENSITIVE_POPULATIONS = frozenset({SOLAR_ENERGETIC_PARTICLE, GALACTIC_COSMIC_RAY})

# A LEO orbit inclination at/above this threshold reaches a high enough
# geomagnetic latitude that the field no longer excludes SEP/GCR particles.
POLAR_SHIELDING_INCLINATION_DEG = 55.0

# South Atlantic Anomaly reference band: the inner trapped-proton belt
# altitude range within which the anomaly's proton enhancement is
# significant, and the minimum orbit inclination for a ground track to
# reach the anomaly's characteristic latitude.
SAA_ALTITUDE_RANGE_KM = (200.0, 1000.0)
SAA_MIN_INCLINATION_DEG = 30.0


def _require_known_population(population):
    if population not in MODEL_CATALOG:
        raise ValueError(
            "unrecognized particle population %r under E-ST-10-04C Annex I" % (population,)
        )
    return MODEL_CATALOG[population]


def _require_known_regime(orbit_regime):
    if orbit_regime not in ORBIT_REGIMES:
        raise ValueError("unrecognized orbit regime %r" % (orbit_regime,))


def model_energy_range_mev(population):
    """(min_energy_mev, max_energy_mev) for a cataloged population.
    Raises ValueError for an unrecognized population."""
    entry = _require_known_population(population)
    return entry["min_energy_mev"], entry["max_energy_mev"]


def model_altitude_range_km(population):
    """(min_altitude_km, max_altitude_km) for a cataloged population, or
    (None, None) when the population's model is not altitude-bound
    (solar_energetic_particle, galactic_cosmic_ray). Raises ValueError
    for an unrecognized population."""
    entry = _require_known_population(population)
    return entry["min_altitude_km"], entry["max_altitude_km"]


def is_energy_in_range(population, energy_mev):
    """True when energy_mev falls within the population's cataloged
    energy range (inclusive both ends). Raises ValueError for an
    unrecognized population or a negative energy_mev."""
    if energy_mev < 0:
        raise ValueError("energy_mev must be >= 0")
    min_mev, max_mev = model_energy_range_mev(population)
    return min_mev <= energy_mev <= max_mev


def is_altitude_in_range(population, altitude_km):
    """True when altitude_km falls within the population's cataloged
    altitude range (inclusive both ends). Raises ValueError for an
    unrecognized population, a negative altitude_km, or a population
    whose model is not altitude-bound."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    min_km, max_km = model_altitude_range_km(population)
    if min_km is None:
        raise ValueError(
            "population %r model is not altitude-bound under E-ST-10-04C Annex I" % (population,)
        )
    return min_km <= altitude_km <= max_km


def is_geomagnetically_shielded(orbit_regime, inclination_deg=None):
    """True when a low-earth orbit at inclination_deg is geomagnetically
    shielded from SEP/GCR particles (inclination below
    POLAR_SHIELDING_INCLINATION_DEG). Always False outside LEO. Raises
    ValueError for an unrecognized orbit_regime, a missing
    inclination_deg on a LEO query, or an inclination_deg outside
    [0, 180]."""
    _require_known_regime(orbit_regime)
    if orbit_regime != "leo":
        return False
    if inclination_deg is None:
        raise ValueError("inclination_deg required to evaluate LEO geomagnetic shielding")
    if not (0.0 <= inclination_deg <= 180.0):
        raise ValueError("inclination_deg must be within [0, 180]")
    return inclination_deg < POLAR_SHIELDING_INCLINATION_DEG


def saa_enhancement_applies(orbit_regime, altitude_km, inclination_deg):
    """True when a low-earth orbit's ground track crosses the South
    Atlantic Anomaly: orbit_regime is "leo", altitude_km falls within
    SAA_ALTITUDE_RANGE_KM, and inclination_deg reaches
    SAA_MIN_INCLINATION_DEG. Always False outside LEO or outside the
    anomaly's altitude band. Raises ValueError for an unrecognized
    orbit_regime, a negative altitude_km, or an inclination_deg outside
    [0, 180]."""
    _require_known_regime(orbit_regime)
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    if not (0.0 <= inclination_deg <= 180.0):
        raise ValueError("inclination_deg must be within [0, 180]")
    if orbit_regime != "leo":
        return False
    lo_km, hi_km = SAA_ALTITUDE_RANGE_KM
    if not (lo_km <= altitude_km <= hi_km):
        return False
    return inclination_deg >= SAA_MIN_INCLINATION_DEG


def select_particle_model(population, orbit_regime, inclination_deg=None):
    """Select the cataloged model_id for a population/orbit_regime
    combination.

    Selection rule: for solar_energetic_particle and galactic_cosmic_ray
    in LEO, applicability is decided by geomagnetic shielding rather
    than static regime membership -- an unshielded (high-inclination)
    LEO orbit uses the model, a shielded one does not. Every other
    population/regime combination is decided by the population's
    cataloged applicable_regimes.

    Raises ValueError for an unrecognized population, an unrecognized
    orbit_regime, a LEO SEP/GCR query missing or with an invalid
    inclination_deg, or a combination no cataloged model covers.
    """
    entry = _require_known_population(population)
    _require_known_regime(orbit_regime)

    if population in SHIELDING_SENSITIVE_POPULATIONS and orbit_regime == "leo":
        if is_geomagnetically_shielded(orbit_regime, inclination_deg):
            raise ValueError(
                "no cataloged model covers population=%r orbit_regime=%r "
                "(leo geomagnetically shielded at inclination_deg=%r)"
                % (population, orbit_regime, inclination_deg)
            )
        return entry["model_id"]

    if orbit_regime not in entry["applicable_regimes"]:
        raise ValueError(
            "no cataloged model covers population=%r orbit_regime=%r" % (population, orbit_regime)
        )
    return entry["model_id"]


def particle_reference_review(
    population, orbit_regime, inclination_deg=None, altitude_km=None, energy_mev=None
):
    """Full Annex I particle-reference-model review for one lookup.

    Returns {"model_id": str | None, "saa_applicable": bool | None,
    "issues": [...]}. When no cataloged model covers the
    population/orbit_regime/inclination combination, model_id is None
    and issues carries a single "no_model_coverage" finding. Otherwise
    model_id is the selected model and issues carries an
    "energy_out_of_model_range" finding when energy_mev is supplied and
    outside the model's range, and either an
    "altitude_not_applicable_to_model" or "altitude_out_of_model_range"
    finding when altitude_km is supplied. saa_applicable is the South
    Atlantic Anomaly determination for a trapped_proton query with both
    altitude_km and inclination_deg supplied, otherwise None; it is
    informational and never itself added to issues.

    Raises ValueError only for structurally invalid input (unrecognized
    population, unrecognized orbit_regime, a LEO SEP/GCR query missing
    or with an invalid inclination_deg, a negative energy_mev, or a
    negative altitude_km) -- coverage gaps and range gaps are reported
    as findings, not raised.
    """
    _require_known_population(population)
    _require_known_regime(orbit_regime)

    if orbit_regime == "leo" and population in SHIELDING_SENSITIVE_POPULATIONS:
        if inclination_deg is None:
            raise ValueError(
                "inclination_deg required to evaluate LEO shielding for population %r" % (population,)
            )
        if not (0.0 <= inclination_deg <= 180.0):
            raise ValueError("inclination_deg must be within [0, 180]")

    try:
        model_id = select_particle_model(population, orbit_regime, inclination_deg)
    except ValueError:
        return {
            "model_id": None,
            "saa_applicable": None,
            "issues": [
                {
                    "issue": "no_model_coverage",
                    "population": population,
                    "orbit_regime": orbit_regime,
                }
            ],
        }

    issues = []

    if energy_mev is not None:
        if energy_mev < 0:
            raise ValueError("energy_mev must be >= 0")
        if not is_energy_in_range(population, energy_mev):
            issues.append(
                {
                    "issue": "energy_out_of_model_range",
                    "population": population,
                    "energy_mev": energy_mev,
                }
            )

    if altitude_km is not None:
        if altitude_km < 0:
            raise ValueError("altitude_km must be >= 0")
        min_km, max_km = model_altitude_range_km(population)
        if min_km is None:
            issues.append(
                {"issue": "altitude_not_applicable_to_model", "population": population}
            )
        elif not (min_km <= altitude_km <= max_km):
            issues.append(
                {
                    "issue": "altitude_out_of_model_range",
                    "population": population,
                    "altitude_km": altitude_km,
                }
            )

    saa_flag = None
    if population == TRAPPED_PROTON and altitude_km is not None and inclination_deg is not None:
        saa_flag = saa_enhancement_applies(orbit_regime, altitude_km, inclination_deg)

    return {"model_id": model_id, "saa_applicable": saa_flag, "issues": issues}


def is_particle_review_compliant(review):
    """True when a particle_reference_review result has a selected
    model and no outstanding issues (the South Atlantic Anomaly flag is
    informational and does not affect this determination)."""
    return review["model_id"] is not None and len(review["issues"]) == 0

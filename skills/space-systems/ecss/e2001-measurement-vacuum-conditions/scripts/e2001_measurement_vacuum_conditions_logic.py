#!/usr/bin/env python3
"""Emission-yield measurement vacuum-conditions check.

Anchor: ECSS-E-ST-20-01C clause 9.4.1.3 (emission-yield measurement is
carried out inside a high-vacuum facility held at low pressure).
Paraphrased into an implementable procedure; no standard text is reproduced.

The clause exists because a secondary-electron-emission-yield measurement
is only meaningful while the coupon surface stays as prepared and the
primary-electron path stays collisionless. Both conditions are pressure
driven, so this module turns the qualitative requirement into checkable
numbers:

  * categorize the facility pressure into a vacuum regime;
  * compute the mean-free-path and the Knudsen number for the chamber and
    confirm the beam path is in free-molecular flow;
  * compute the residual-gas impingement rate and the monolayer-formation
    time, and require it to outlast the measurement with margin;
  * audit the residual-gas partial-pressure inventory, including the
    hydrocarbon fraction that would carbon-contaminate the coupon;
  * screen the pressure log for excursions above the declared operating
    limit and check the bake-out record.

stdlib only, offline, deterministic.
"""

import math

BOLTZMANN_J_PER_K = 1.380649e-23
AVOGADRO_PER_MOL = 6.02214076e23

# ISO 3529-1 style regime ladder, coarsest first. Each entry is the upper
# pressure bound (Pa) of the regime named with it; anything above the first
# bound is ambient, anything below the last bound is extreme-high vacuum.
REGIME_LADDER = (
    (1.0e5, "low-vacuum"),
    (1.0e2, "medium-vacuum"),
    (1.0e-1, "high-vacuum"),
    (1.0e-6, "ultra-high-vacuum"),
    (1.0e-10, "extreme-high-vacuum"),
)
AMBIENT_REGIME = "ambient"
EXTREME_REGIME = "extreme-high-vacuum"
KNOWN_REGIMES = tuple([AMBIENT_REGIME] + [n for _, n in REGIME_LADDER])
ACCEPTABLE_REGIMES = ("high-vacuum", "ultra-high-vacuum", EXTREME_REGIME)

DEFAULT_TEMPERATURE_K = 293.15
DEFAULT_MOLECULAR_DIAMETER_M = 3.7e-10
DEFAULT_SITE_DENSITY_PER_M2 = 1.0e19
MOLECULAR_FLOW_KNUDSEN = 10.0
CONTINUUM_FLOW_KNUDSEN = 0.01
DEFAULT_MONOLAYER_MARGIN = 3.0
DEFAULT_HYDROCARBON_FRACTION_LIMIT = 0.05
BAKEOUT_MIN_TEMPERATURE_K = 393.15
BAKEOUT_MIN_DURATION_H = 12.0

MOLAR_MASS_KG_PER_MOL = {
    "hydrogen": 2.016e-3,
    "water": 18.015e-3,
    "nitrogen": 28.014e-3,
    "carbon-monoxide": 28.010e-3,
    "argon": 39.948e-3,
    "carbon-dioxide": 44.010e-3,
    "methane": 16.043e-3,
    "pump-oil-hydrocarbon": 170.0e-3,
}
HYDROCARBON_SPECIES = ("methane", "pump-oil-hydrocarbon")

REL_TOL = 1e-9
ABS_TOL = 1e-300


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, type(value)))
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (label, value))
    return value


def categorize_vacuum_regime(pressure_pa):
    """Name the vacuum regime a chamber pressure sits in.

    A pressure sitting exactly on a ladder bound belongs to the cleaner
    regime the bound opens; the equality is taken with a tolerance so a
    computed pressure a few units in the last place above the bound is not
    demoted by representation error alone.
    """
    pressure = _positive(pressure_pa, "pressure_pa")
    regime = AMBIENT_REGIME
    for bound, name in REGIME_LADDER:
        if pressure > bound and not math.isclose(pressure, bound, rel_tol=REL_TOL):
            break
        regime = name
    return regime


def regime_is_acceptable(regime):
    """True when the regime satisfies the high-vacuum floor of the clause."""
    if not isinstance(regime, str):
        raise ValueError("regime must be a string, got %r" % (type(regime),))
    if regime not in KNOWN_REGIMES:
        raise ValueError("unknown vacuum regime '%s'" % regime)
    return regime in ACCEPTABLE_REGIMES


def mean_free_path_m(
    pressure_pa,
    temperature_k=DEFAULT_TEMPERATURE_K,
    molecular_diameter_m=DEFAULT_MOLECULAR_DIAMETER_M,
):
    """Kinetic-theory mean free path of the residual gas."""
    pressure = _positive(pressure_pa, "pressure_pa")
    temperature = _positive(temperature_k, "temperature_k")
    diameter = _positive(molecular_diameter_m, "molecular_diameter_m")
    denom = math.sqrt(2.0) * math.pi * diameter * diameter * pressure
    return BOLTZMANN_J_PER_K * temperature / denom


def knudsen_number(path_m, characteristic_length_m):
    """Ratio of mean free path to the chamber dimension the beam crosses."""
    path = _positive(path_m, "path_m")
    length = _positive(characteristic_length_m, "characteristic_length_m")
    return path / length


def flow_regime(knudsen):
    """Categorize the flow the primary-electron path travels through."""
    kn = _positive(knudsen, "knudsen")
    if kn >= MOLECULAR_FLOW_KNUDSEN or math.isclose(
        kn, MOLECULAR_FLOW_KNUDSEN, rel_tol=REL_TOL
    ):
        return "free-molecular"
    if kn <= CONTINUUM_FLOW_KNUDSEN or math.isclose(
        kn, CONTINUUM_FLOW_KNUDSEN, rel_tol=REL_TOL
    ):
        return "continuum"
    return "transitional"


def species_molar_mass(species):
    """Molar mass of a known residual-gas species."""
    if species not in MOLAR_MASS_KG_PER_MOL:
        raise ValueError("unknown residual-gas species '%r'" % (species,))
    return MOLAR_MASS_KG_PER_MOL[species]


def impingement_rate_per_m2_s(pressure_pa, temperature_k, species):
    """Hertz-Knudsen wall flux of one residual-gas species."""
    pressure = _positive(pressure_pa, "pressure_pa")
    temperature = _positive(temperature_k, "temperature_k")
    mass = species_molar_mass(species) / AVOGADRO_PER_MOL
    return pressure / math.sqrt(
        2.0 * math.pi * mass * BOLTZMANN_J_PER_K * temperature
    )


def monolayer_formation_time_s(
    pressure_pa,
    temperature_k=DEFAULT_TEMPERATURE_K,
    species="water",
    sticking_coefficient=1.0,
    site_density_per_m2=DEFAULT_SITE_DENSITY_PER_M2,
):
    """Time for the residual gas to lay down one adsorbed monolayer."""
    if isinstance(sticking_coefficient, bool) or not isinstance(
        sticking_coefficient, (int, float)
    ):
        raise ValueError("sticking_coefficient must be numeric")
    sticking = float(sticking_coefficient)
    if not 0.0 < sticking <= 1.0:
        raise ValueError("sticking_coefficient must lie in (0, 1], got %r" % sticking)
    sites = _positive(site_density_per_m2, "site_density_per_m2")
    flux = impingement_rate_per_m2_s(pressure_pa, temperature_k, species)
    return sites / (sticking * flux)


def dominant_species(partial_pressures_pa):
    """Species carrying the largest partial pressure in the inventory."""
    if not isinstance(partial_pressures_pa, dict) or not partial_pressures_pa:
        raise ValueError("partial-pressure inventory must be a non-empty mapping")
    best = None
    for species, value in sorted(partial_pressures_pa.items()):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("partial pressure of '%s' must be numeric" % species)
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(
                "partial pressure of '%s' must be finite and non-negative" % species
            )
        species_molar_mass(species)
        if best is None or value > best[1]:
            best = (species, value)
    return best[0]


def audit_partial_pressures(partial_pressures_pa, total_pressure_pa):
    """Consistency and hydrocarbon audit of the residual-gas inventory."""
    total = _positive(total_pressure_pa, "total_pressure_pa")
    dominant = dominant_species(partial_pressures_pa)
    listed = math.fsum(float(v) for v in partial_pressures_pa.values())
    over = listed > total and not math.isclose(
        listed, total, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    hydrocarbon = math.fsum(
        float(v)
        for k, v in partial_pressures_pa.items()
        if k in HYDROCARBON_SPECIES
    )
    return {
        "dominant_species": dominant,
        "listed_total_pa": listed,
        "unaccounted_pa": max(0.0, total - listed),
        "inventory_exceeds_total": over,
        "hydrocarbon_pa": hydrocarbon,
        "hydrocarbon_fraction": hydrocarbon / total,
    }


def screen_pressure_log(readings_pa, limit_pa):
    """Screen a measurement-run pressure log against the operating limit."""
    if not isinstance(readings_pa, (list, tuple)) or not readings_pa:
        raise ValueError("pressure log must be a non-empty sequence")
    limit = _positive(limit_pa, "limit_pa")
    values = [_positive(r, "pressure reading") for r in readings_pa]
    peak = max(values)
    excursions = [
        v
        for v in values
        if v > limit and not math.isclose(v, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    ]
    return {
        "samples": len(values),
        "peak_pa": peak,
        "floor_pa": min(values),
        "mean_pa": math.fsum(values) / len(values),
        "excursion_count": len(excursions),
        "within_limit": not excursions,
        "swing_decades": math.log10(peak / min(values)),
    }


def bakeout_is_adequate(bakeout):
    """True when the bake-out record clears the water-desorption floor."""
    if bakeout is None:
        return False
    if not isinstance(bakeout, dict):
        raise ValueError("bakeout record must be a mapping or None")
    temperature = _positive(bakeout.get("temperature_k"), "bakeout temperature_k")
    duration = _positive(bakeout.get("duration_h"), "bakeout duration_h")
    hot = temperature >= BAKEOUT_MIN_TEMPERATURE_K or math.isclose(
        temperature, BAKEOUT_MIN_TEMPERATURE_K, rel_tol=REL_TOL
    )
    long_enough = duration >= BAKEOUT_MIN_DURATION_H or math.isclose(
        duration, BAKEOUT_MIN_DURATION_H, rel_tol=REL_TOL
    )
    return hot and long_enough


def assess_vacuum_conditions(facility):
    """Full clause 9.4.1.3 report for one emission-yield measurement run."""
    if not isinstance(facility, dict):
        raise ValueError("facility record must be a mapping, got %r" % (type(facility),))
    log = facility.get("pressure_log_pa")
    limit = _positive(facility.get("pressure_limit_pa"), "pressure_limit_pa")
    temperature = _positive(
        facility.get("temperature_k", DEFAULT_TEMPERATURE_K), "temperature_k"
    )
    length = _positive(facility.get("chamber_length_m"), "chamber_length_m")
    duration = _positive(
        facility.get("measurement_duration_s"), "measurement_duration_s"
    )
    margin = _positive(
        facility.get("monolayer_margin", DEFAULT_MONOLAYER_MARGIN), "monolayer_margin"
    )
    partials = facility.get("residual_gas_partial_pa", {})

    log_report = screen_pressure_log(log, limit)
    working_pressure = log_report["peak_pa"]
    regime = categorize_vacuum_regime(working_pressure)
    path = mean_free_path_m(working_pressure, temperature)
    kn = knudsen_number(path, length)
    flow = flow_regime(kn)
    inventory = audit_partial_pressures(partials, working_pressure)
    species = inventory["dominant_species"]
    sticking = facility.get("sticking_coefficient", 1.0)
    monolayer = monolayer_formation_time_s(
        working_pressure, temperature, species, sticking
    )
    required_monolayer = duration * margin
    hydrocarbon_limit = _positive(
        facility.get("hydrocarbon_fraction_limit", DEFAULT_HYDROCARBON_FRACTION_LIMIT),
        "hydrocarbon_fraction_limit",
    )

    findings = []
    if not regime_is_acceptable(regime):
        findings.append(
            {
                "code": "regime-above-high-vacuum",
                "detail": "working pressure sits in the %s regime" % regime,
            }
        )
    if not log_report["within_limit"]:
        findings.append(
            {
                "code": "pressure-excursion",
                "detail": "%d log samples exceed the declared operating limit"
                % log_report["excursion_count"],
            }
        )
    if flow != "free-molecular":
        findings.append(
            {
                "code": "beam-path-not-collisionless",
                "detail": "Knudsen number %.3g puts the beam path in %s flow"
                % (kn, flow),
            }
        )
    if monolayer < required_monolayer and not math.isclose(
        monolayer, required_monolayer, rel_tol=REL_TOL
    ):
        findings.append(
            {
                "code": "surface-recontamination-risk",
                "detail": "monolayer time %.4g s does not cover %.4g s of"
                " measurement with the declared margin"
                % (monolayer, required_monolayer),
            }
        )
    if inventory["inventory_exceeds_total"]:
        findings.append(
            {
                "code": "partial-pressure-inventory-inconsistent",
                "detail": "listed partials %.4g Pa exceed the total %.4g Pa"
                % (inventory["listed_total_pa"], working_pressure),
            }
        )
    fraction = inventory["hydrocarbon_fraction"]
    if fraction > hydrocarbon_limit and not math.isclose(
        fraction, hydrocarbon_limit, rel_tol=REL_TOL
    ):
        findings.append(
            {
                "code": "hydrocarbon-partial-pressure-excess",
                "detail": "hydrocarbon fraction %.3g exceeds limit %.3g"
                % (fraction, hydrocarbon_limit),
            }
        )
    if not bakeout_is_adequate(facility.get("bakeout")):
        findings.append(
            {
                "code": "bakeout-not-substantiated",
                "detail": "no bake-out on record that clears the"
                " water-desorption floor",
            }
        )

    return {
        "facility": facility.get("id", "unnamed-facility"),
        "working_pressure_pa": working_pressure,
        "regime": regime,
        "mean_free_path_m": path,
        "knudsen_number": kn,
        "flow_regime": flow,
        "dominant_species": species,
        "monolayer_formation_time_s": monolayer,
        "required_monolayer_time_s": required_monolayer,
        "hydrocarbon_fraction": fraction,
        "pressure_log": log_report,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }

#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 6.9 -- neutral-gas release and discharge triggering.

Deterministic, offline, stdlib-only implementation of the clause 6.9
assessment: place each neutral-gas release path in its behaviour family,
compute the local neutral density and pressure the release produces at
exposed high-voltage hardware, form the pressure-gap product, evaluate
the Paschen breakdown voltage of the released species, decide the
breakdown margin against the applied electrode voltage, and derive the
post-launch outgassing-decay inhibit window.

Paraphrased procedure; no verbatim standard text. The clause is the
anchor only.
"""

import math

BOLTZMANN = 1.380649e-23  # J/K
AVOGADRO = 6.02214076e23  # 1/mol
GAS_CONSTANT = 8.314462618  # J/(mol K)

DEFAULT_REQUIRED_MARGIN = 2.0
DEFAULT_SOLID_ANGLE_SR = 2.0 * math.pi  # surface-mounted release into a half space

# Townsend ionisation coefficients converted to SI (1/(Pa m) and V/(Pa m))
# with a representative secondary-emission coefficient per species.
GAS_PROPERTIES = {
    "air": {
        "a_per_pa_m": 11.25,
        "b_v_per_pa_m": 273.8,
        "secondary_emission": 0.01,
        "molar_mass_kg_per_mol": 0.028960,
    },
    "nitrogen": {
        "a_per_pa_m": 9.00,
        "b_v_per_pa_m": 256.5,
        "secondary_emission": 0.01,
        "molar_mass_kg_per_mol": 0.028014,
    },
    "argon": {
        "a_per_pa_m": 9.00,
        "b_v_per_pa_m": 135.0,
        "secondary_emission": 0.02,
        "molar_mass_kg_per_mol": 0.039948,
    },
    "xenon": {
        "a_per_pa_m": 19.50,
        "b_v_per_pa_m": 262.5,
        "secondary_emission": 0.02,
        "molar_mass_kg_per_mol": 0.131293,
    },
    "helium": {
        "a_per_pa_m": 2.25,
        "b_v_per_pa_m": 25.5,
        "secondary_emission": 0.02,
        "molar_mass_kg_per_mol": 0.0040026,
    },
    "water-vapour": {
        "a_per_pa_m": 9.68,
        "b_v_per_pa_m": 216.8,
        "secondary_emission": 0.01,
        "molar_mass_kg_per_mol": 0.018015,
    },
    "carbon-dioxide": {
        "a_per_pa_m": 15.00,
        "b_v_per_pa_m": 349.5,
        "secondary_emission": 0.01,
        "molar_mass_kg_per_mol": 0.044009,
    },
}

RELEASE_PATHS = {
    "propulsion-plume": "commanded-transient",
    "attitude-thruster-plume": "commanded-transient",
    "commanded-vent": "commanded-transient",
    "active-gas-release-experiment": "commanded-transient",
    "propellant-leak": "continuous",
    "pressurant-leak": "continuous",
    "sublimation": "continuous",
    "material-outgassing": "decaying",
    "water-desorption": "decaying",
}

BEHAVIOURS = ("commanded-transient", "continuous", "decaying")


def _gas(species):
    if not isinstance(species, str):
        raise ValueError("species must be a string, got %r" % (species,))
    try:
        return GAS_PROPERTIES[species]
    except KeyError:
        raise ValueError("unknown released species '%s'" % species)


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric" % label)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, value))
    return float(value)


def release_path_behaviour(path):
    """Return the behaviour family of a neutral-gas release path."""
    if not isinstance(path, str):
        raise ValueError("release path must be a string, got %r" % (path,))
    try:
        return RELEASE_PATHS[path]
    except KeyError:
        raise ValueError("unknown neutral-gas release path '%s'" % path)


def paths_with_behaviour(behaviour):
    """Return the sorted release paths sharing one behaviour family."""
    if behaviour not in BEHAVIOURS:
        raise ValueError("unknown release behaviour '%s'" % (behaviour,))
    return sorted(p for p, b in RELEASE_PATHS.items() if b == behaviour)


def mean_thermal_speed(species, temperature_k):
    """Mean thermal speed of a species at a temperature, in m/s."""
    molar_mass = _gas(species)["molar_mass_kg_per_mol"]
    temperature_k = _positive(temperature_k, "temperature")
    return math.sqrt(8.0 * GAS_CONSTANT * temperature_k / (math.pi * molar_mass))


def particle_rate(mass_rate_kg_per_s, species):
    """Convert a released mass rate to a particle rate, in 1/s."""
    mass_rate_kg_per_s = _positive(mass_rate_kg_per_s, "mass rate")
    molar_mass = _gas(species)["molar_mass_kg_per_mol"]
    return mass_rate_kg_per_s * AVOGADRO / molar_mass


def local_number_density(rate_per_s, distance_m, speed_m_per_s,
                         solid_angle_sr=DEFAULT_SOLID_ANGLE_SR):
    """Free-molecular number density at a distance from a release, in 1/m3."""
    rate_per_s = _positive(rate_per_s, "particle rate")
    distance_m = _positive(distance_m, "distance")
    speed_m_per_s = _positive(speed_m_per_s, "flow speed")
    solid_angle_sr = _positive(solid_angle_sr, "expansion solid angle")
    if solid_angle_sr > 4.0 * math.pi:
        raise ValueError("expansion solid angle cannot exceed 4 pi steradian")
    return rate_per_s / (solid_angle_sr * distance_m ** 2 * speed_m_per_s)


def neutral_pressure(number_density_per_m3, temperature_k):
    """Convert a neutral number density to a pressure, in Pa."""
    number_density_per_m3 = _positive(number_density_per_m3, "number density")
    temperature_k = _positive(temperature_k, "temperature")
    return number_density_per_m3 * BOLTZMANN * temperature_k


def local_pressure_from_release(mass_rate_kg_per_s, species, distance_m,
                                temperature_k,
                                solid_angle_sr=DEFAULT_SOLID_ANGLE_SR,
                                flow_speed_m_per_s=None):
    """Local neutral pressure produced by one release path, in Pa."""
    if flow_speed_m_per_s is None:
        speed = mean_thermal_speed(species, temperature_k)
    else:
        speed = _positive(flow_speed_m_per_s, "flow speed")
    rate = particle_rate(mass_rate_kg_per_s, species)
    density = local_number_density(rate, distance_m, speed, solid_angle_sr)
    return neutral_pressure(density, temperature_k)


def critical_pressure_gap_product(species):
    """Pressure-gap product below which no breakdown is possible, in Pa m."""
    gas = _gas(species)
    return math.log(1.0 + 1.0 / gas["secondary_emission"]) / gas["a_per_pa_m"]


def paschen_minimum(species):
    """Return (pressure-gap product, breakdown voltage) at the curve minimum."""
    gas = _gas(species)
    log_term = math.log(1.0 + 1.0 / gas["secondary_emission"])
    pd_min = math.e * log_term / gas["a_per_pa_m"]
    v_min = math.e * gas["b_v_per_pa_m"] * log_term / gas["a_per_pa_m"]
    return pd_min, v_min


def paschen_breakdown_voltage(species, pressure_pa, gap_m):
    """Breakdown voltage for a species at a pressure across a gap, in V.

    Returns math.inf when the pressure-gap product sits at or below the
    critical product, where the electron multiplication cannot close and
    no applied voltage produces breakdown.
    """
    gas = _gas(species)
    pressure_pa = _positive(pressure_pa, "pressure")
    gap_m = _positive(gap_m, "gap")
    pd = pressure_pa * gap_m
    log_term = math.log(1.0 + 1.0 / gas["secondary_emission"])
    denominator = math.log(gas["a_per_pa_m"] * pd) - math.log(log_term)
    if denominator <= 0.0 or math.isclose(denominator, 0.0, abs_tol=1e-15):
        return math.inf
    return gas["b_v_per_pa_m"] * pd / denominator


def paschen_branch(species, pressure_pa, gap_m):
    """Locate a pressure-gap product on the Paschen curve."""
    pd = _positive(pressure_pa, "pressure") * _positive(gap_m, "gap")
    pd_crit = critical_pressure_gap_product(species)
    pd_min, _ = paschen_minimum(species)
    if pd < pd_crit or math.isclose(pd, pd_crit, rel_tol=1e-12):
        return "no-breakdown-possible"
    if math.isclose(pd, pd_min, rel_tol=1e-12):
        return "paschen-minimum"
    return "left-branch" if pd < pd_min else "right-branch"


def breakdown_margin(applied_voltage_v, breakdown_voltage_v):
    """Ratio of breakdown voltage to applied electrode voltage."""
    applied = _positive(applied_voltage_v, "applied voltage")
    if breakdown_voltage_v == math.inf:
        return math.inf
    breakdown = _positive(breakdown_voltage_v, "breakdown voltage")
    return breakdown / applied


def is_margin_met(applied_voltage_v, breakdown_voltage_v,
                  required_margin=DEFAULT_REQUIRED_MARGIN):
    """True when the achieved breakdown margin reaches the required margin.

    The achieved margin is a quotient of computed powers, so an exactly
    compliant design can land a few units in the last place low. The
    representation error is absorbed in the comparison; the required
    margin itself is never reduced.
    """
    required = _positive(required_margin, "required margin")
    achieved = breakdown_margin(applied_voltage_v, breakdown_voltage_v)
    if achieved == math.inf:
        return True
    return achieved > required or math.isclose(achieved, required, rel_tol=1e-12)


def maximum_safe_pressure(species, gap_m, applied_voltage_v,
                          required_margin=DEFAULT_REQUIRED_MARGIN,
                          iterations=200):
    """Highest low-side pressure that still meets the required margin, in Pa.

    Searches the left branch, where the breakdown voltage falls
    monotonically from the critical product down to the curve minimum.
    Returns math.inf when even the curve minimum clears the required
    voltage.
    """
    gap_m = _positive(gap_m, "gap")
    applied = _positive(applied_voltage_v, "applied voltage")
    required = _positive(required_margin, "required margin")
    target_voltage = applied * required
    pd_min, v_min = paschen_minimum(species)
    if v_min > target_voltage or math.isclose(v_min, target_voltage, rel_tol=1e-12):
        return math.inf
    low = critical_pressure_gap_product(species) * 1.000001 / gap_m
    high = pd_min / gap_m
    for _ in range(int(iterations)):
        mid = 0.5 * (low + high)
        if paschen_breakdown_voltage(species, mid, gap_m) >= target_voltage:
            low = mid
        else:
            high = mid
    return low


def outgassing_pressure_at_time(reference_pressure_pa, reference_time_h,
                                time_h, decay_exponent=1.0):
    """Decaying outgassing pressure at an elapsed time, in Pa."""
    reference_pressure_pa = _positive(reference_pressure_pa, "reference pressure")
    reference_time_h = _positive(reference_time_h, "reference time")
    time_h = _positive(time_h, "elapsed time")
    decay_exponent = _positive(decay_exponent, "decay exponent")
    return reference_pressure_pa * (reference_time_h / time_h) ** decay_exponent


def time_to_reach_pressure(reference_pressure_pa, reference_time_h,
                           target_pressure_pa, decay_exponent=1.0):
    """Elapsed time at which a decaying release falls to a pressure, in h."""
    reference_pressure_pa = _positive(reference_pressure_pa, "reference pressure")
    reference_time_h = _positive(reference_time_h, "reference time")
    target_pressure_pa = _positive(target_pressure_pa, "target pressure")
    decay_exponent = _positive(decay_exponent, "decay exponent")
    if target_pressure_pa >= reference_pressure_pa:
        return reference_time_h
    ratio = reference_pressure_pa / target_pressure_pa
    return reference_time_h * ratio ** (1.0 / decay_exponent)


def assess_release_path(scenario):
    """Assess one neutral-gas release path against one electrode geometry."""
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a mapping")
    for key in ("path", "species", "gap_m", "applied_voltage_v"):
        if key not in scenario:
            raise ValueError("scenario missing required key '%s'" % key)
    behaviour = release_path_behaviour(scenario["path"])
    species = scenario["species"]
    gap = _positive(scenario["gap_m"], "gap")
    applied = _positive(scenario["applied_voltage_v"], "applied voltage")
    required = scenario.get("required_margin", DEFAULT_REQUIRED_MARGIN)

    if "local_pressure_pa" in scenario:
        pressure = _positive(scenario["local_pressure_pa"], "local pressure")
    else:
        pressure = local_pressure_from_release(
            scenario.get("mass_rate_kg_per_s"),
            species,
            scenario.get("distance_m"),
            scenario.get("temperature_k"),
            scenario.get("solid_angle_sr", DEFAULT_SOLID_ANGLE_SR),
            scenario.get("flow_speed_m_per_s"),
        )

    branch = paschen_branch(species, pressure, gap)
    breakdown = paschen_breakdown_voltage(species, pressure, gap)
    margin = breakdown_margin(applied, breakdown)
    compliant = is_margin_met(applied, breakdown, required)

    findings = []
    if not compliant:
        findings.append(
            "%s: breakdown margin %.3f below the required %.3f on the %s"
            % (scenario["path"], margin, required, branch)
        )

    inhibit_h = None
    if behaviour == "decaying" and not compliant:
        safe_pressure = maximum_safe_pressure(species, gap, applied, required)
        if safe_pressure == math.inf:
            inhibit_h = 0.0
        else:
            inhibit_h = time_to_reach_pressure(
                pressure,
                scenario.get("reference_time_h", 1.0),
                safe_pressure,
                scenario.get("decay_exponent", 1.0),
            )
            findings.append(
                "%s: high-voltage activation inhibited for %.2f h"
                % (scenario["path"], inhibit_h)
            )

    return {
        "path": scenario["path"],
        "behaviour": behaviour,
        "local_pressure_pa": pressure,
        "pressure_gap_product_pa_m": pressure * gap,
        "branch": branch,
        "breakdown_voltage_v": breakdown,
        "margin": margin,
        "compliant": compliant,
        "activation_inhibit_h": inhibit_h,
        "findings": findings,
    }


def assess_gas_environment(scenarios):
    """Aggregate the clause 6.9 verdict over every release path."""
    if not isinstance(scenarios, (list, tuple)) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")
    results = [assess_release_path(s) for s in scenarios]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    inhibits = [r["activation_inhibit_h"] for r in results
                if r["activation_inhibit_h"] is not None]
    return {
        "results": results,
        "findings": findings,
        "activation_inhibit_h": max(inhibits) if inhibits else 0.0,
        "compliant": all(r["compliant"] for r in results),
    }

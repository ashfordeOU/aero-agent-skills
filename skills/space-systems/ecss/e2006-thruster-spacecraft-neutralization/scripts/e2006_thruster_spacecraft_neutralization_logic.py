#!/usr/bin/env python3
"""Neutralizer emission-capacity sizing against beam and natural currents.

Anchor: ECSS-E-ST-20-06C clause 11.2.1 (paraphrased, not quoted).

Clause 11.2.1 requires the electron-emitting neutralizer of an
electric-propulsion unit to hold an emission capacity above the
extracted beam current plus the natural charging currents the
spacecraft sees, evaluated in the worst-case environment of the
mission. This module implements that sizing as a deterministic
current-balance:

* random-flux current densities of the ambient electron and ion
  populations from density and temperature;
* photoemission, secondary-electron and backscattered-electron
  currents, which remove electrons and drive the body positive;
* the net natural current the neutralizer must offset, per environment;
* selection of the worst-case environment across a mission set;
* the required emission capacity with the agreed sizing margin, and
  the compliance verdict against the declared neutralizer capability.

Sign convention: a current is positive when it drives the spacecraft
potential positive, i.e. when it removes electrons from the body or
deposits positive charge on it.

Standard library only, offline, deterministic.
"""

import math

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837015e-31
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27

# Representative photoemission current density of a sunlit spacecraft
# surface at one astronomical unit, in amperes per square metre. The
# caller overrides it with the material-specific value when known.
DEFAULT_PHOTOEMISSION_DENSITY_A_M2 = 2.0e-5

# Relative tolerance used only to absorb binary-floating-point
# representation error when a declared capability sits exactly on the
# required value. It never lowers the required capacity.
REPRESENTATION_TOLERANCE = 1e-12

# Ion masses of the ambient populations met in flight, in atomic mass
# units. Charge state is carried separately.
AMBIENT_ION_MASS_AMU = {
    "hydrogen": 1.008,
    "helium": 4.0026,
    "atomic-oxygen": 15.999,
    "xenon": 131.293,
}

REQUIRED_ENVIRONMENT_KEYS = (
    "name",
    "electron_density_m3",
    "electron_temperature_ev",
    "collecting_area_m2",
    "sunlit_area_m2",
)


def species_ion_mass_kg(species):
    """Ion mass [kg] of a named ambient population."""
    if not isinstance(species, str) or not species.strip():
        raise ValueError("ion species must be a non-empty string")
    key = species.strip().lower()
    if key not in AMBIENT_ION_MASS_AMU:
        raise ValueError("uncategorized ambient ion species: %r" % (species,))
    return AMBIENT_ION_MASS_AMU[key] * ATOMIC_MASS_UNIT_KG


def thermal_flux_current_density(number_density_m3, temperature_ev,
                                 particle_mass_kg, charge_state=1):
    """Random-flux current density [A/m^2] of a Maxwellian population.

    J = q n sqrt(kT / (2 pi m)), with kT expressed in joules from the
    temperature given in electronvolts.
    """
    if number_density_m3 <= 0:
        raise ValueError("number density must be > 0 m^-3")
    if temperature_ev <= 0:
        raise ValueError("temperature must be > 0 eV")
    if particle_mass_kg <= 0:
        raise ValueError("particle mass must be > 0 kg")
    if not isinstance(charge_state, int) or isinstance(charge_state, bool):
        raise ValueError("charge state must be an integer")
    if charge_state < 1:
        raise ValueError("charge state must be >= 1")
    kt_joule = temperature_ev * ELEMENTARY_CHARGE_C
    speed_term = math.sqrt(kt_joule / (2.0 * math.pi * particle_mass_kg))
    return charge_state * ELEMENTARY_CHARGE_C * number_density_m3 * speed_term


def ambient_electron_current(collecting_area_m2, electron_density_m3,
                             electron_temperature_ev):
    """Ambient electron collection current [A] onto the exposed area.

    Collected electrons supply negative charge, so the returned value
    is the magnitude of a potential-negative-driving current.
    """
    if collecting_area_m2 <= 0:
        raise ValueError("collecting area must be > 0 m^2")
    density = thermal_flux_current_density(electron_density_m3,
                                           electron_temperature_ev,
                                           ELECTRON_MASS_KG)
    return density * collecting_area_m2


def ambient_ion_current(collecting_area_m2, ion_density_m3,
                        ion_temperature_ev, species="atomic-oxygen",
                        charge_state=1):
    """Ambient ion collection current [A] onto the exposed area."""
    if collecting_area_m2 <= 0:
        raise ValueError("collecting area must be > 0 m^2")
    density = thermal_flux_current_density(ion_density_m3, ion_temperature_ev,
                                           species_ion_mass_kg(species),
                                           charge_state)
    return density * collecting_area_m2


def photoemission_current(sunlit_area_m2,
                          current_density_a_m2=DEFAULT_PHOTOEMISSION_DENSITY_A_M2):
    """Photoelectron escape current [A] from the sunlit area."""
    if sunlit_area_m2 < 0:
        raise ValueError("sunlit area must be >= 0 m^2")
    if current_density_a_m2 <= 0:
        raise ValueError("photoemission current density must be > 0 A/m^2")
    return sunlit_area_m2 * current_density_a_m2


def secondary_electron_current(incident_electron_current_a, emission_yield):
    """Secondary-electron escape current [A] for an incident current."""
    if incident_electron_current_a < 0:
        raise ValueError("incident electron current must be >= 0 A")
    if emission_yield < 0:
        raise ValueError("emission yield must be >= 0")
    if emission_yield > 10.0:
        raise ValueError("emission yield above 10 is not physical for surfaces")
    return incident_electron_current_a * emission_yield


def validate_environment(env):
    """Normalise and validate one worst-case environment record."""
    if not isinstance(env, dict):
        raise ValueError("environment must be a mapping")
    for key in REQUIRED_ENVIRONMENT_KEYS:
        if key not in env:
            raise ValueError("environment missing required key %r" % (key,))
    name = env["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("environment name must be a non-empty string")
    out = {
        "name": name.strip().lower(),
        "electron_density_m3": env["electron_density_m3"],
        "electron_temperature_ev": env["electron_temperature_ev"],
        "collecting_area_m2": env["collecting_area_m2"],
        "sunlit_area_m2": env["sunlit_area_m2"],
        "ion_density_m3": env.get("ion_density_m3", env["electron_density_m3"]),
        "ion_temperature_ev": env.get("ion_temperature_ev",
                                      env["electron_temperature_ev"]),
        "ion_species": env.get("ion_species", "atomic-oxygen"),
        "ion_charge_state": env.get("ion_charge_state", 1),
        "secondary_emission_yield": env.get("secondary_emission_yield", 0.0),
        "backscatter_current_a": env.get("backscatter_current_a", 0.0),
        "photoemission_density_a_m2": env.get(
            "photoemission_density_a_m2", DEFAULT_PHOTOEMISSION_DENSITY_A_M2),
    }
    if out["sunlit_area_m2"] < 0:
        raise ValueError("sunlit area must be >= 0 m^2")
    if out["sunlit_area_m2"] > out["collecting_area_m2"]:
        raise ValueError("sunlit area cannot exceed the collecting area")
    if out["backscatter_current_a"] < 0:
        raise ValueError("backscatter current must be >= 0 A")
    return out


def environment_current_balance(env):
    """Current balance [A] of one environment, before the beam current.

    Returns the individual terms and the net natural current the
    neutralizer has to offset. Positive terms drive the body positive
    (photoemission, secondary emission, backscatter, collected ions);
    collected ambient electrons drive it negative.
    """
    checked = validate_environment(env)
    electron_current = ambient_electron_current(
        checked["collecting_area_m2"],
        checked["electron_density_m3"],
        checked["electron_temperature_ev"])
    ion_current = ambient_ion_current(
        checked["collecting_area_m2"],
        checked["ion_density_m3"],
        checked["ion_temperature_ev"],
        checked["ion_species"],
        checked["ion_charge_state"])
    photo_current = photoemission_current(
        checked["sunlit_area_m2"],
        checked["photoemission_density_a_m2"])
    secondary_current = secondary_electron_current(
        electron_current, checked["secondary_emission_yield"])
    positive_driving = (photo_current + secondary_current
                        + checked["backscatter_current_a"] + ion_current)
    net_natural = positive_driving - electron_current
    return {
        "name": checked["name"],
        "electron_collection_a": electron_current,
        "ion_collection_a": ion_current,
        "photoemission_a": photo_current,
        "secondary_emission_a": secondary_current,
        "backscatter_a": checked["backscatter_current_a"],
        "positive_driving_a": positive_driving,
        "net_natural_current_a": net_natural,
    }


def required_emission_capacity(beam_current_a, env, margin=1.2):
    """Required neutralizer emission capacity [A] in one environment.

    The neutralizer must return the beam current and, on top of it, any
    net natural current that would otherwise drive the body positive. A
    plasma dense enough to over-supply electrons earns no credit
    against the beam current, so the natural term is floored at zero.
    """
    if beam_current_a <= 0:
        raise ValueError("beam current must be > 0 A")
    if margin < 1.0:
        raise ValueError("sizing margin must be >= 1.0")
    balance = environment_current_balance(env)
    natural = balance["net_natural_current_a"]
    if natural < 0.0:
        natural = 0.0
    return margin * (beam_current_a + natural)


def worst_case_environment(beam_current_a, environments, margin=1.2):
    """Environment demanding the largest emission capacity.

    Ties are broken by environment name so the result is reproducible.
    """
    if not isinstance(environments, (list, tuple)):
        raise ValueError("environments must be a list")
    if not environments:
        raise ValueError("at least one environment must be supplied")
    ranked = []
    seen = set()
    for env in environments:
        balance = environment_current_balance(env)
        if balance["name"] in seen:
            raise ValueError("duplicate environment name %r" % (balance["name"],))
        seen.add(balance["name"])
        ranked.append((required_emission_capacity(beam_current_a, env, margin),
                       balance["name"], balance))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    required, name, balance = ranked[0]
    return {"name": name, "required_capacity_a": required, "balance": balance}


def verify_emission_capacity(capability_a, required_a):
    """Grade a declared neutralizer capability against the requirement.

    A capability that equals the requirement is compliant; because both
    sides are sums and products of floating-point terms, an exactly
    compliant unit can land a few units in the last place low, so the
    comparison absorbs that representation error rather than relaxing
    the required capacity.
    """
    if capability_a <= 0:
        raise ValueError("neutralizer capability must be > 0 A")
    if required_a <= 0:
        raise ValueError("required capacity must be > 0 A")
    compliant = capability_a >= required_a or math.isclose(
        capability_a, required_a, rel_tol=REPRESENTATION_TOLERANCE, abs_tol=0.0)
    shortfall = 0.0 if compliant else required_a - capability_a
    return {
        "compliant": compliant,
        "capability_a": capability_a,
        "required_a": required_a,
        "utilisation": required_a / capability_a,
        "shortfall_a": shortfall,
    }


def assess_neutralization(config):
    """Full clause 11.2.1 neutralization assessment.

    Required keys: ``beam_current_a``, ``neutralizer_capability_a``,
    ``environments``. Optional: ``margin`` (default 1.2).
    """
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    for key in ("beam_current_a", "neutralizer_capability_a", "environments"):
        if key not in config:
            raise ValueError("configuration missing required key %r" % (key,))
    margin = config.get("margin", 1.2)
    worst = worst_case_environment(config["beam_current_a"],
                                   config["environments"], margin)
    verdict = verify_emission_capacity(config["neutralizer_capability_a"],
                                       worst["required_capacity_a"])
    findings = []
    if not verdict["compliant"]:
        findings.append(
            "emission-capacity-shortfall: %.6e A in environment %s"
            % (verdict["shortfall_a"], worst["name"]))
    if worst["balance"]["net_natural_current_a"] > config["beam_current_a"]:
        findings.append(
            "natural-current-exceeds-beam-current: environment %s"
            % worst["name"])
    return {
        "worst_case_environment": worst["name"],
        "balance": worst["balance"],
        "margin": margin,
        "required_capacity_a": worst["required_capacity_a"],
        "verdict": verdict,
        "findings": findings,
        "neutralization_compliant": verdict["compliant"] and not findings,
    }

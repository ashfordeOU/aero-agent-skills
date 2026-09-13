#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 6.8.4 -- content of a spacecraft-charging model.

Deterministic, offline, stdlib-only implementation of the model-content
check: derive the physical effects a charging simulation must represent
for a given configuration, confirm every represented effect carries a
usable material-parameter set, confirm the current-balance solution
closes at the floating-potential, and confirm the integration step of a
transient run resolves the charging time constant.

Paraphrased procedure; no verbatim standard text. The clause is the
anchor only.
"""

import math

EPSILON_0 = 8.8541878128e-12  # F/m

# --- effect catalogue ----------------------------------------------------

EFFECT_FAMILIES = {
    "ambient-electron-collection": "environment-current",
    "ambient-ion-collection": "environment-current",
    "photoemission": "emission-current",
    "secondary-electron-emission-by-electrons": "emission-current",
    "secondary-electron-emission-by-ions": "emission-current",
    "electron-backscatter": "emission-current",
    "surface-conduction": "charge-transport",
    "bulk-conduction": "charge-transport",
    "radiation-induced-conductivity": "charge-transport",
    "illumination-geometry": "geometry",
    "wake-shadowing-geometry": "geometry",
    "active-plasma-source-current": "external-current",
    "current-balance-solution": "numerical",
    "time-dependent-integration": "numerical",
}

ALWAYS_REQUIRED = (
    "ambient-electron-collection",
    "ambient-ion-collection",
    "secondary-electron-emission-by-electrons",
    "electron-backscatter",
    "current-balance-solution",
)

FLOWING_PLASMA_REGIMES = ("low-earth-orbit", "polar-earth-orbit")
ORBIT_REGIMES = FLOWING_PLASMA_REGIMES + (
    "geostationary-orbit",
    "medium-earth-orbit",
    "interplanetary",
)

CONFIG_FLAGS = (
    "sunlit",
    "dielectric_present",
    "penetrating_radiation",
    "active_plasma_source",
    "transient_analysis",
)

# parameter contracts: effect -> {parameter: (low, high)} inclusive range
PARAMETER_CONTRACTS = {
    "photoemission": {"photoemission_current_density_a_per_m2": (1e-7, 1e-3)},
    "secondary-electron-emission-by-electrons": {
        "see_peak_yield": (0.3, 10.0),
        "see_peak_energy_ev": (10.0, 2000.0),
    },
    "secondary-electron-emission-by-ions": {"ion_induced_yield": (0.0, 5.0)},
    "electron-backscatter": {"backscatter_yield": (0.0, 0.9)},
    "surface-conduction": {"surface_resistivity_ohm_per_square": (1e5, 1e22)},
    "bulk-conduction": {
        "bulk_resistivity_ohm_m": (1e6, 1e22),
        "relative_permittivity": (1.0, 20.0),
    },
    "radiation-induced-conductivity": {
        "ric_coefficient": (1e-20, 1e-10),
        "ric_exponent": (0.5, 1.0),
    },
}

BALANCE_REL_TOL = 1e-6
MAX_STEP_FRACTION = 0.1


def effect_family(effect):
    """Return the current family of an effect id."""
    if not isinstance(effect, str):
        raise ValueError("effect id must be a string, got %r" % (effect,))
    try:
        return EFFECT_FAMILIES[effect]
    except KeyError:
        raise ValueError("unknown charging effect '%s'" % effect)


def effects_in_family(family):
    """Return the sorted effect ids belonging to one family."""
    known = set(EFFECT_FAMILIES.values())
    if family not in known:
        raise ValueError("unknown effect family '%s'" % (family,))
    return sorted(e for e, f in EFFECT_FAMILIES.items() if f == family)


def validate_configuration(config):
    """Normalise and validate an analysis configuration mapping."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    regime = config.get("regime")
    if regime not in ORBIT_REGIMES:
        raise ValueError("unknown orbital regime %r" % (regime,))
    normalised = {"regime": regime}
    for flag in CONFIG_FLAGS:
        value = config.get(flag, False)
        if not isinstance(value, bool):
            raise ValueError("configuration flag '%s' must be boolean" % flag)
        normalised[flag] = value
    for key in config:
        if key != "regime" and key not in CONFIG_FLAGS:
            raise ValueError("unknown configuration key '%s'" % key)
    if normalised["penetrating_radiation"] and not normalised["dielectric_present"]:
        raise ValueError(
            "penetrating_radiation without dielectric_present is not a "
            "meaningful charging configuration"
        )
    return normalised


def required_effects(config):
    """Derive the effect set clause 6.8.4 requires for this configuration."""
    cfg = validate_configuration(config)
    required = set(ALWAYS_REQUIRED)
    if cfg["sunlit"]:
        required.add("photoemission")
        required.add("illumination-geometry")
    if cfg["dielectric_present"]:
        required.add("surface-conduction")
        required.add("bulk-conduction")
    if cfg["dielectric_present"] and cfg["penetrating_radiation"]:
        required.add("radiation-induced-conductivity")
    if cfg["regime"] in FLOWING_PLASMA_REGIMES:
        required.add("wake-shadowing-geometry")
        required.add("secondary-electron-emission-by-ions")
    if cfg["active_plasma_source"]:
        required.add("active-plasma-source-current")
    if cfg["transient_analysis"]:
        required.add("time-dependent-integration")
    return sorted(required)


def check_effect_coverage(config, declared_effects):
    """Compare the declared effect list against the required set."""
    if not isinstance(declared_effects, (list, tuple, set)):
        raise ValueError("declared effects must be a list, tuple or set")
    declared = set()
    for effect in declared_effects:
        effect_family(effect)  # raises on an unknown id
        declared.add(effect)
    required = set(required_effects(config))
    missing = sorted(required - declared)
    extra = sorted(declared - required)
    covered = len(required & declared)
    coverage = 1.0 if not required else covered / float(len(required))
    return {
        "required": sorted(required),
        "declared": sorted(declared),
        "missing": missing,
        "extra_scope": extra,
        "coverage": coverage,
        "complete": not missing,
    }


def check_effect_parameters(effect, parameters):
    """Check one effect's parameter set against its physical ranges."""
    effect_family(effect)
    contract = PARAMETER_CONTRACTS.get(effect)
    if contract is None:
        return []  # geometry and numerical effects carry no coefficient set
    if not isinstance(parameters, dict):
        raise ValueError("parameters for '%s' must be a mapping" % effect)
    findings = []
    for name, (low, high) in sorted(contract.items()):
        if name not in parameters:
            findings.append("%s: missing parameter '%s'" % (effect, name))
            continue
        value = parameters[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                "parameter '%s' of '%s' must be numeric" % (name, effect)
            )
        if math.isnan(value) or math.isinf(value):
            raise ValueError(
                "parameter '%s' of '%s' must be finite" % (name, effect)
            )
        below = value < low and not math.isclose(value, low, rel_tol=1e-12)
        above = value > high and not math.isclose(value, high, rel_tol=1e-12)
        if below or above:
            findings.append(
                "%s: parameter '%s' = %g outside [%g, %g]"
                % (effect, name, value, low, high)
            )
    return findings


def check_parameter_sets(declared_effects, parameter_sets):
    """Check every declared effect that carries a parameter contract."""
    if not isinstance(parameter_sets, dict):
        raise ValueError("parameter sets must be a mapping")
    findings = []
    for effect in sorted(set(declared_effects)):
        effect_family(effect)
        if effect not in PARAMETER_CONTRACTS:
            continue
        params = parameter_sets.get(effect)
        if params is None:
            findings.append("%s: no parameter set supplied" % effect)
            continue
        findings.extend(check_effect_parameters(effect, params))
    return findings


def current_balance_residual(currents):
    """Signed sum of the converged current set, in amperes."""
    if not isinstance(currents, dict) or not currents:
        raise ValueError("currents must be a non-empty mapping")
    total = 0.0
    for name, value in sorted(currents.items()):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("current '%s' must be numeric" % (name,))
        if math.isnan(value) or math.isinf(value):
            raise ValueError("current '%s' must be finite" % (name,))
        total += float(value)
    return total


def is_current_balance_closed(currents, rel_tol=BALANCE_REL_TOL):
    """True when the residual vanishes within a scaled tolerance.

    The residual is a signed sum of currents spanning several decades, so
    a physically closed balance can land a few units in the last place
    away from zero. The tolerance is scaled to the largest contributing
    current; the engineering criterion (a vanishing residual) is not
    widened.
    """
    if rel_tol <= 0.0:
        raise ValueError("rel_tol must be positive")
    residual = current_balance_residual(currents)
    scale = max(abs(float(v)) for v in currents.values())
    if scale == 0.0:
        return True
    return math.isclose(residual, 0.0, abs_tol=scale * rel_tol)


def charging_time_constant(capacitance_per_area_f_per_m2, potential_v,
                           net_current_density_a_per_m2):
    """Time for the net current density to charge a surface to a potential."""
    if capacitance_per_area_f_per_m2 <= 0.0:
        raise ValueError("capacitance per area must be positive")
    if net_current_density_a_per_m2 == 0.0:
        raise ValueError("net current density must be non-zero")
    if potential_v == 0.0:
        raise ValueError("potential must be non-zero")
    return abs(capacitance_per_area_f_per_m2 * potential_v /
               net_current_density_a_per_m2)


def dielectric_relaxation_time(relative_permittivity, bulk_resistivity_ohm_m):
    """Charge relaxation time of a dielectric, in seconds."""
    if relative_permittivity < 1.0:
        raise ValueError("relative permittivity must be >= 1")
    if bulk_resistivity_ohm_m <= 0.0:
        raise ValueError("bulk resistivity must be positive")
    return EPSILON_0 * relative_permittivity * bulk_resistivity_ohm_m


def check_integration_step(step_s, time_constant_s,
                           max_fraction=MAX_STEP_FRACTION):
    """True when the integration step resolves the charging transient."""
    if step_s <= 0.0:
        raise ValueError("integration step must be positive")
    if time_constant_s <= 0.0:
        raise ValueError("time constant must be positive")
    if not 0.0 < max_fraction <= 1.0:
        raise ValueError("max_fraction must lie in (0, 1]")
    limit = max_fraction * time_constant_s
    return step_s < limit or math.isclose(step_s, limit, rel_tol=1e-12)


def assess_model_acceptance(config, model):
    """Aggregate the clause 6.8.4 content verdict for one charging model."""
    if not isinstance(model, dict):
        raise ValueError("model must be a mapping")
    declared = model.get("effects")
    if declared is None:
        raise ValueError("model must declare an 'effects' list")
    coverage = check_effect_coverage(config, declared)
    findings = ["missing effect: %s" % e for e in coverage["missing"]]
    findings.extend(check_parameter_sets(declared, model.get("parameters", {})))

    currents = model.get("currents")
    balance_closed = None
    if currents is not None:
        balance_closed = is_current_balance_closed(currents)
        if not balance_closed:
            findings.append(
                "current-balance residual %g A does not vanish"
                % current_balance_residual(currents)
            )
    elif "current-balance-solution" in coverage["required"]:
        findings.append("no converged current set supplied for the balance check")

    step_ok = None
    cfg = validate_configuration(config)
    if cfg["transient_analysis"]:
        step = model.get("integration_step_s")
        tau = model.get("charging_time_constant_s")
        if step is None or tau is None:
            findings.append(
                "transient analysis without an integration step and time constant"
            )
        else:
            step_ok = check_integration_step(step, tau)
            if not step_ok:
                findings.append(
                    "integration step %g s does not resolve the %g s time constant"
                    % (step, tau)
                )

    return {
        "coverage": coverage,
        "balance_closed": balance_closed,
        "integration_step_ok": step_ok,
        "findings": findings,
        "supports_acceptance": not findings,
    }

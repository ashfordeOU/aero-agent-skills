#!/usr/bin/env python3
"""High-voltage biased surfaces in dense low-orbit plasma - ECSS-E-ST-20-06C
clause 8.1 (anchor only).

A high-voltage solar-array, and any other deliberately biased external
surface, sits immersed in the dense ionospheric plasma of low orbit. The
plasma is conductive enough to close a circuit between the biased surface and
the ambient medium, so the array itself decides where spacecraft ground
floats, and each exposed conductor then collects or repels charge according
to its own potential relative to that plasma.

This module is deterministic, offline and stdlib-only. It:

1. validates the ambient plasma environment and decides whether it is dense
   enough for the clause 8.1 concerns to apply;
2. derives the electron-thermal and ram-ion current densities;
3. solves the linear current-balance that fixes how much of the string
   voltage floats positive of the plasma, and therefore where ground sits;
4. categorizes each biased surface and places its plasma-relative potential
   in the ion-collection, arc-inception, electron-collection or snapover
   regime;
5. computes the parasitic current each surface collects and checks the
   mitigation set and the total against the parasitic-current budget.

No verbatim standard text is reproduced here.
"""

import math

__all__ = [
    "ELEMENTARY_CHARGE_C",
    "ELECTRON_MASS_KG",
    "DENSE_PLASMA_DENSITY_M3",
    "DEFAULT_RAM_VELOCITY_M_S",
    "ARC_INCEPTION_MAGNITUDE_V",
    "SNAPOVER_ONSET_V",
    "SNAPOVER_AREA_FACTOR",
    "DIELECTRIC_LEAK_FRACTION",
    "SURFACE_CATEGORIES",
    "KNOWN_MITIGATIONS",
    "INTERACTION_REGIMES",
    "validate_plasma_environment",
    "is_dense_low_orbit_plasma",
    "electron_thermal_current_density",
    "ram_ion_current_density",
    "categorize_biased_surface",
    "positive_bias_fraction",
    "string_potential_split",
    "categorize_interaction_regime",
    "collected_current_a",
    "check_parasitic_budget",
    "evaluate_surface",
    "assess_high_voltage_surfaces",
]

REL_TOL = 1e-9
ABS_TOL = 1e-15

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837015e-31

# Ionospheric electron density above which the clause 8.1 concerns apply: the
# medium is conductive enough to close the circuit to a biased surface.
DENSE_PLASMA_DENSITY_M3 = 1.0e10

# Orbital velocity dominates the ion thermal speed in low orbit, so ions
# arrive as a ram flux.
DEFAULT_RAM_VELOCITY_M_S = 7800.0

# Magnitude of the negative plasma-relative potential at which arc inception
# on an exposed conductor or a conductor-dielectric junction becomes credible.
ARC_INCEPTION_MAGNITUDE_V = 100.0

# Positive plasma-relative potential above which secondary-electron emission
# turns the surrounding dielectric into a collector and the effective
# collecting area jumps (snapover).
SNAPOVER_ONSET_V = 40.0
SNAPOVER_AREA_FACTOR = 10.0

# Fraction of a dielectric-covered area that still collects, through pinholes
# and coverglass gaps.
DIELECTRIC_LEAK_FRACTION = 1.0e-3

SURFACE_KINDS = {
    "array-interconnect": "exposed-conductor",
    "bus-bar-tab": "exposed-conductor",
    "biased-electrode": "exposed-conductor",
    "coverglass": "dielectric-covered",
    "blanket-outer-layer": "dielectric-covered",
    "array-substrate-face": "dielectric-covered",
    "cell-coverglass-edge": "semi-exposed-junction",
    "cell-gap-triple-junction": "semi-exposed-junction",
}
SURFACE_CATEGORIES = ("exposed-conductor", "dielectric-covered", "semi-exposed-junction")

KNOWN_MITIGATIONS = (
    "encapsulation",
    "gap-filling",
    "plasma-shield",
    "potential-clamping",
)
ARC_INCEPTION_MITIGATIONS = ("encapsulation", "gap-filling", "potential-clamping")
SNAPOVER_MITIGATIONS = ("encapsulation", "plasma-shield")

INTERACTION_REGIMES = (
    "ion-collection",
    "arc-inception-risk",
    "electron-collection",
    "snapover-collection",
)


def _ge(value, limit):
    """value >= limit, tolerant of float representation error at equality."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _le(value, limit):
    """value <= limit, tolerant of float representation error at equality."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _real(value, name, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: %s must be a real number, got %r" % (context, name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: %s must be finite, got %r" % (context, name, value))
    return value


def _positive(value, name, context):
    value = _real(value, name, context)
    if value <= 0.0:
        raise ValueError("%s: %s must be positive, got %g" % (context, name, value))
    return value


def _mapping(value, context):
    if not isinstance(value, dict):
        raise ValueError("%s: expected a mapping, got %s" % (context, type(value).__name__))
    return value


def validate_plasma_environment(env):
    """Validate and normalize the ambient plasma environment.

    Required: ``electron_density_m3`` (> 0), ``electron_temperature_ev`` (> 0).
    Optional: ``ram_velocity_m_s`` (> 0, defaults to a low-orbit value).
    """
    env = _mapping(env, "plasma environment")
    for key in ("electron_density_m3", "electron_temperature_ev"):
        if key not in env:
            raise ValueError("plasma environment: missing required field %r" % key)
    density = _positive(env["electron_density_m3"], "electron_density_m3", "plasma environment")
    temperature = _positive(
        env["electron_temperature_ev"], "electron_temperature_ev", "plasma environment"
    )
    ram = env.get("ram_velocity_m_s", DEFAULT_RAM_VELOCITY_M_S)
    ram = _positive(ram, "ram_velocity_m_s", "plasma environment")
    return {
        "electron_density_m3": density,
        "electron_temperature_ev": temperature,
        "ram_velocity_m_s": ram,
    }


def is_dense_low_orbit_plasma(env, density_threshold_m3=DENSE_PLASMA_DENSITY_M3):
    """True when the ambient density reaches the dense low-orbit regime."""
    normalized = validate_plasma_environment(env)
    threshold = _positive(density_threshold_m3, "density_threshold_m3", "plasma environment")
    return _ge(normalized["electron_density_m3"], threshold)


def electron_thermal_current_density(env):
    """Random electron-flux current density collected by a positive surface.

    j_e = q * n * sqrt(q * Te / (2 * pi * m_e)), with Te expressed in eV.
    """
    normalized = validate_plasma_environment(env)
    speed = math.sqrt(
        ELEMENTARY_CHARGE_C
        * normalized["electron_temperature_ev"]
        / (2.0 * math.pi * ELECTRON_MASS_KG)
    )
    return ELEMENTARY_CHARGE_C * normalized["electron_density_m3"] * speed


def ram_ion_current_density(env):
    """Ion current density collected on the ram face: j_i = q * n * v_ram."""
    normalized = validate_plasma_environment(env)
    return (
        ELEMENTARY_CHARGE_C
        * normalized["electron_density_m3"]
        * normalized["ram_velocity_m_s"]
    )


def categorize_biased_surface(kind):
    """Map a surface kind onto its collection category."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("surface kind must be a non-empty string, got %r" % (kind,))
    category = SURFACE_KINDS.get(kind)
    if category is None:
        raise ValueError(
            "uncategorized biased-surface kind %r; known kinds: %s"
            % (kind, ", ".join(sorted(SURFACE_KINDS)))
        )
    return category


def positive_bias_fraction(env, electron_collecting_area_m2, ion_collecting_area_m2):
    """Fraction of the string voltage that floats positive of the plasma.

    Two-area current-balance approximation: the exposed conductor area on the
    positive side of the string collects the mobile electron flux, the exposed
    conducting area on the negative side (string plus any bare grounded
    structure) collects the far slower ram ion flux, and the array floats
    until the two balance:

        f = (j_i * A_ion) / (j_i * A_ion + j_e * A_elec)

    Because the electron flux per unit area is much larger than the ram ion
    flux, the balance leaves only a small fraction of the string positive of
    the plasma and drives spacecraft ground strongly negative. The result is
    bounded in [0, 1] by construction; the clamp is a defensive guard.
    """
    electron_area = _positive(
        electron_collecting_area_m2, "electron_collecting_area_m2", "bias split"
    )
    ion_area = _positive(ion_collecting_area_m2, "ion_collecting_area_m2", "bias split")
    j_e = electron_thermal_current_density(env)
    j_i = ram_ion_current_density(env)
    ion_term = j_i * ion_area
    fraction = ion_term / (ion_term + j_e * electron_area)
    if fraction < 0.0:
        return 0.0
    if fraction > 1.0:
        return 1.0
    return fraction


def string_potential_split(string_voltage_v, positive_fraction):
    """Potentials of the two string ends relative to the ambient plasma."""
    voltage = _positive(string_voltage_v, "string_voltage_v", "string split")
    fraction = _real(positive_fraction, "positive_fraction", "string split")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("string split: positive_fraction must lie in [0, 1], got %g" % fraction)
    positive_end = fraction * voltage
    negative_end = -(1.0 - fraction) * voltage
    return {
        "positive_end_v": positive_end,
        "negative_end_v": negative_end,
        "ground_potential_v": negative_end,
        "positive_fraction": fraction,
    }


def categorize_interaction_regime(
    potential_v,
    arc_inception_magnitude_v=ARC_INCEPTION_MAGNITUDE_V,
    snapover_onset_v=SNAPOVER_ONSET_V,
):
    """Categorize the plasma interaction of one surface from its potential.

    ``potential_v`` is referred to the ambient plasma. Negative surfaces repel
    electrons and collect ions; past the inception magnitude they can strike
    an arc. Positive surfaces collect electrons; past the snapover onset the
    surrounding dielectric joins in and the collecting area jumps.
    """
    potential = _real(potential_v, "potential_v", "regime")
    inception = _positive(arc_inception_magnitude_v, "arc_inception_magnitude_v", "regime")
    snapover = _positive(snapover_onset_v, "snapover_onset_v", "regime")
    if potential < 0.0:
        if _ge(abs(potential), inception):
            return "arc-inception-risk"
        return "ion-collection"
    if _ge(potential, snapover):
        return "snapover-collection"
    return "electron-collection"


def collected_current_a(category, area_m2, potential_v, env, regime=None):
    """Magnitude of the parasitic current one surface exchanges with the plasma.

    A positive surface collects the electron flux over its effective area; in
    the snapover regime that area is multiplied by the snapover factor. A
    negative surface collects the far smaller ram ion flux. A
    dielectric-covered surface only collects through its pinhole fraction.
    """
    if category not in SURFACE_CATEGORIES:
        raise ValueError("unknown surface category %r" % (category,))
    area = _positive(area_m2, "area_m2", "surface")
    potential = _real(potential_v, "potential_v", "surface")
    if regime is None:
        regime = categorize_interaction_regime(potential)
    if regime not in INTERACTION_REGIMES:
        raise ValueError("unknown interaction regime %r" % (regime,))

    effective_area = area
    if category == "dielectric-covered":
        effective_area *= DIELECTRIC_LEAK_FRACTION
    elif category == "semi-exposed-junction":
        effective_area *= 0.5

    if regime in ("electron-collection", "snapover-collection"):
        if regime == "snapover-collection":
            effective_area *= SNAPOVER_AREA_FACTOR
        return electron_thermal_current_density(env) * effective_area
    return ram_ion_current_density(env) * effective_area


def check_parasitic_budget(currents_a, budget_a):
    """Compare the summed parasitic current against the budget.

    The total is a sum of per-surface currents, so an exactly-compliant total
    can land a few ULPs above the budget; the comparison absorbs that
    representation error without widening the budget.
    """
    if not isinstance(currents_a, (list, tuple)):
        raise ValueError("currents_a must be a list or tuple")
    values = [_real(v, "current", "budget") for v in currents_a]
    for value in values:
        if value < 0.0:
            raise ValueError("budget: per-surface current must be a magnitude, got %g" % value)
    budget = _positive(budget_a, "budget_a", "budget")
    total = math.fsum(values)
    findings = []
    if not _le(total, budget):
        findings.append(
            "total parasitic current %.4g A exceeds the %.4g A budget" % (total, budget)
        )
    return {"total_a": total, "budget_a": budget, "findings": findings}


def evaluate_surface(surface, env, ground_potential_v, **thresholds):
    """Evaluate one biased surface against the clause 8.1 concerns.

    Required keys: ``id``, ``kind``, ``area_m2`` (> 0),
    ``potential_wrt_ground_v``. Optional: ``mitigations`` (list drawn from
    KNOWN_MITIGATIONS).
    """
    surface = _mapping(surface, "surface")
    identifier = surface.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("surface: 'id' must be a non-empty string, got %r" % (identifier,))
    context = "surface %s" % identifier
    for key in ("kind", "area_m2", "potential_wrt_ground_v"):
        if key not in surface:
            raise ValueError("%s: missing required field %r" % (context, key))

    category = categorize_biased_surface(surface["kind"])
    area = _positive(surface["area_m2"], "area_m2", context)
    ground = _real(ground_potential_v, "ground_potential_v", context)
    potential = _real(surface["potential_wrt_ground_v"], "potential_wrt_ground_v", context) + ground

    regime = categorize_interaction_regime(potential, **thresholds)
    current = collected_current_a(category, area, potential, env, regime)

    mitigations = surface.get("mitigations", [])
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("%s: 'mitigations' must be a list" % context)
    for item in mitigations:
        if item not in KNOWN_MITIGATIONS:
            raise ValueError("%s: uncategorized mitigation %r" % (context, item))
    recorded = set(mitigations)

    findings = []
    if regime == "arc-inception-risk" and not recorded.intersection(ARC_INCEPTION_MITIGATIONS):
        findings.append(
            "potential %.4g V relative to the plasma reaches arc inception with no "
            "mitigation on record" % potential
        )
    if regime == "snapover-collection" and not recorded.intersection(SNAPOVER_MITIGATIONS):
        findings.append(
            "potential %.4g V relative to the plasma is past snapover onset with no "
            "mitigation on record" % potential
        )

    return {
        "id": identifier,
        "category": category,
        "plasma_relative_potential_v": potential,
        "regime": regime,
        "collected_current_a": current,
        "findings": findings,
        "compliant": not findings,
    }


def assess_high_voltage_surfaces(
    surfaces,
    env,
    string_voltage_v,
    electron_collecting_area_m2,
    ion_collecting_area_m2,
    parasitic_budget_a,
    **thresholds
):
    """Assess a biased-surface set against the clause 8.1 concerns.

    Computes the floating split of the string, evaluates every surface against
    the resulting ground potential, and checks the summed parasitic current
    against the budget. The set conforms when no surface carries a finding and
    the budget holds.
    """
    if not isinstance(surfaces, (list, tuple)):
        raise ValueError("surfaces must be a list or tuple, got %s" % type(surfaces).__name__)
    if not surfaces:
        raise ValueError("surfaces must not be empty: an empty inventory proves nothing")

    normalized = validate_plasma_environment(env)
    fraction = positive_bias_fraction(
        normalized, electron_collecting_area_m2, ion_collecting_area_m2
    )
    split = string_potential_split(string_voltage_v, fraction)

    results = []
    seen = set()
    for surface in surfaces:
        result = evaluate_surface(surface, normalized, split["ground_potential_v"], **thresholds)
        if result["id"] in seen:
            raise ValueError("duplicate surface id %r in the inventory" % result["id"])
        seen.add(result["id"])
        results.append(result)

    budget = check_parasitic_budget([r["collected_current_a"] for r in results], parasitic_budget_a)
    findings = [f for r in results for f in r["findings"]] + budget["findings"]
    regime_counts = {name: 0 for name in INTERACTION_REGIMES}
    for result in results:
        regime_counts[result["regime"]] += 1

    return {
        "dense_plasma": is_dense_low_orbit_plasma(normalized),
        "split": split,
        "surfaces": results,
        "regime_counts": regime_counts,
        "parasitic": budget,
        "findings": findings,
        "finding_count": len(findings),
        "verdict": "pass" if not findings else "fail",
    }

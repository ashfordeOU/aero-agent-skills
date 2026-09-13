"""ECSS-E-ST-20-06C clause 4.1.3 -- surface-charging physical mechanisms.

Offline, deterministic, stdlib-only model of the way ambient plasma
particles accumulate on an external spacecraft surface and drive its
potential. The module implements the current-balance procedure that the
clause introduces:

  * every current contributor is categorized as ambient-plasma
    collection (electrons, ions) or surface emission (secondary
    electrons, backscattered electrons, photoelectrons);
  * each contributor is evaluated as a function of the surface
    potential, because a charged surface retards the particles that
    carry its own charge sign and attracts the opposite ones;
  * the equilibrium (floating) potential is the potential at which the
    signed sum of every contributor vanishes;
  * the difference between the equilibrium potentials of adjacent
    surfaces is the differential-charging offset that a protection
    assessment compares against a discharge-onset threshold.

Sign convention: a current density is reported as a net positive charge
flow onto the surface. Collected electrons therefore enter with a
negative sign, collected ions and every emitted-electron term with a
positive sign. Units are SI: A/m2 for current densities, volts for
potentials, electronvolts for particle energies and temperatures.

No verbatim standard text is reproduced; the clause is cited as the
anchor of the procedure only.
"""

import math

__all__ = [
    "CURRENT_CONTRIBUTORS",
    "categorize_current_contributor",
    "charge_sign",
    "signed_current_density",
    "net_current_density",
    "secondary_electron_yield",
    "electron_collection_current",
    "ion_collection_current",
    "emission_current",
    "net_current_at_potential",
    "solve_equilibrium_potential",
    "categorize_charging_regime",
    "differential_charging",
    "assess_differential_charging",
    "assess_surface_charging",
]

# Contributor registry: name -> (family, sign of the charge it deposits).
CURRENT_CONTRIBUTORS = {
    "ambient-electron-collection": ("collected", -1.0),
    "ambient-ion-collection": ("collected", 1.0),
    "secondary-electron-emission": ("emitted", 1.0),
    "backscattered-electron-emission": ("emitted", 1.0),
    "photoelectron-emission": ("emitted", 1.0),
}

# Escape energies of the low-energy emitted populations: a positive
# surface pulls its own emitted electrons back, suppressing the term.
DEFAULT_SECONDARY_ESCAPE_EV = 2.0
DEFAULT_PHOTOELECTRON_ESCAPE_EV = 1.5

# Sternglass-type yield curve normalisation constant.
_STERNGLASS_K = 7.4

# Regime band edges on the magnitude of the equilibrium potential.
REGIME_MODERATE_V = 100.0
REGIME_SEVERE_V = 1000.0

# Bisection controls and the tolerances used to absorb representation
# error on physically compliant boundary cases.
DEFAULT_LOWER_POTENTIAL_V = -50000.0
DEFAULT_UPPER_POTENTIAL_V = 1000.0
DEFAULT_POTENTIAL_TOLERANCE_V = 1e-9
MAX_BISECTION_STEPS = 400
BOUNDARY_REL_TOL = 1e-12
BOUNDARY_ABS_TOL = 1e-9


def _require_finite(value, name):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_non_negative(value, name):
    out = _require_finite(value, name)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def _require_positive(value, name):
    out = _require_finite(value, name)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _at_or_below(value, limit):
    """True when value is at or below limit, absorbing float error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL,
                        abs_tol=BOUNDARY_ABS_TOL)


def _at_or_above(value, limit):
    """True when value is at or above limit, absorbing float error."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL,
                        abs_tol=BOUNDARY_ABS_TOL)


def categorize_current_contributor(kind):
    """Return 'collected' or 'emitted' for a current contributor name."""
    if not isinstance(kind, str):
        raise ValueError("contributor kind must be a string, got %r" % (kind,))
    entry = CURRENT_CONTRIBUTORS.get(kind)
    if entry is None:
        raise ValueError(
            "uncategorized current contributor %r; known contributors: %s"
            % (kind, ", ".join(sorted(CURRENT_CONTRIBUTORS)))
        )
    return entry[0]


def charge_sign(kind):
    """Return the signed charge a contributor deposits (-1.0 or +1.0)."""
    categorize_current_contributor(kind)
    return CURRENT_CONTRIBUTORS[kind][1]


def signed_current_density(kind, magnitude):
    """Signed current density (A/m2) of one contributor magnitude."""
    value = _require_non_negative(magnitude, "magnitude")
    return charge_sign(kind) * value


def net_current_density(contributors):
    """Sum signed current densities of an inventory of contributors.

    contributors: iterable of mappings with keys 'kind' and 'magnitude'.
    """
    items = list(contributors)
    if not items:
        raise ValueError("contributor inventory must not be empty")
    total = 0.0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("contributor[%d] must be a mapping" % index)
        if "kind" not in item or "magnitude" not in item:
            raise ValueError(
                "contributor[%d] needs 'kind' and 'magnitude' keys" % index
            )
        total += signed_current_density(item["kind"], item["magnitude"])
    return total


def secondary_electron_yield(impact_energy_ev, yield_max, energy_max_ev):
    """Sternglass-type secondary-electron yield of an impacting electron.

    The yield rises from zero, peaks near energy_max_ev and falls again
    as deeper penetration traps the secondaries in the material.
    """
    energy = _require_non_negative(impact_energy_ev, "impact_energy_ev")
    peak = _require_positive(yield_max, "yield_max")
    energy_peak = _require_positive(energy_max_ev, "energy_max_ev")
    if energy == 0.0:
        return 0.0
    ratio = energy / energy_peak
    return _STERNGLASS_K * peak * ratio * math.exp(-2.0 * math.sqrt(ratio))


def electron_collection_current(ambient_electron_current, potential_v,
                                electron_temperature_ev):
    """Ambient electron current density reaching a surface at potential_v.

    A negative surface retards the Maxwellian electrons exponentially; a
    positive surface attracts them with an orbit-limited linear growth.
    """
    base = _require_non_negative(ambient_electron_current,
                                 "ambient_electron_current")
    potential = _require_finite(potential_v, "potential_v")
    temperature = _require_positive(electron_temperature_ev,
                                    "electron_temperature_ev")
    if potential < 0.0:
        return base * math.exp(potential / temperature)
    return base * (1.0 + potential / temperature)


def ion_collection_current(ambient_ion_current, potential_v,
                           ion_temperature_ev):
    """Ambient ion current density reaching a surface at potential_v.

    A negative surface accelerates the ions, a positive surface retards
    them; the mirror image of the electron-collection behaviour.
    """
    base = _require_non_negative(ambient_ion_current, "ambient_ion_current")
    potential = _require_finite(potential_v, "potential_v")
    temperature = _require_positive(ion_temperature_ev, "ion_temperature_ev")
    if potential > 0.0:
        return base * math.exp(-potential / temperature)
    return base * (1.0 - potential / temperature)


def emission_current(emitted_current, potential_v, escape_energy_ev):
    """Emitted-electron current that actually escapes a surface.

    A positive surface returns the low-energy emitted population, so the
    escaping fraction decays exponentially with the barrier height.
    """
    base = _require_non_negative(emitted_current, "emitted_current")
    potential = _require_finite(potential_v, "potential_v")
    escape = _require_positive(escape_energy_ev, "escape_energy_ev")
    if potential <= 0.0:
        return base
    return base * math.exp(-potential / escape)


def _validated_environment(environment):
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    required = ("electron_current", "ion_current", "electron_temperature_ev",
                "ion_temperature_ev")
    for key in required:
        if key not in environment:
            raise ValueError("environment missing required key %r" % key)
    return {
        "electron_current": _require_non_negative(
            environment["electron_current"], "electron_current"),
        "ion_current": _require_non_negative(
            environment["ion_current"], "ion_current"),
        "electron_temperature_ev": _require_positive(
            environment["electron_temperature_ev"],
            "electron_temperature_ev"),
        "ion_temperature_ev": _require_positive(
            environment["ion_temperature_ev"], "ion_temperature_ev"),
    }


def _validated_surface(surface):
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    for key in ("name", "yield_max", "energy_max_ev"):
        if key not in surface:
            raise ValueError("surface missing required key %r" % key)
    backscatter = _require_non_negative(
        surface.get("backscatter_fraction", 0.0), "backscatter_fraction")
    if backscatter > 1.0:
        raise ValueError("backscatter_fraction must be <= 1, got %r"
                         % (surface.get("backscatter_fraction"),))
    return {
        "name": str(surface["name"]),
        "yield_max": _require_positive(surface["yield_max"], "yield_max"),
        "energy_max_ev": _require_positive(surface["energy_max_ev"],
                                           "energy_max_ev"),
        "backscatter_fraction": backscatter,
        "sunlit": bool(surface.get("sunlit", False)),
        "photoemission_current": _require_non_negative(
            surface.get("photoemission_current", 0.0),
            "photoemission_current"),
        "secondary_escape_ev": _require_positive(
            surface.get("secondary_escape_ev", DEFAULT_SECONDARY_ESCAPE_EV),
            "secondary_escape_ev"),
        "photoelectron_escape_ev": _require_positive(
            surface.get("photoelectron_escape_ev",
                        DEFAULT_PHOTOELECTRON_ESCAPE_EV),
            "photoelectron_escape_ev"),
    }


def net_current_at_potential(environment, surface, potential_v):
    """Net positive charging current density (A/m2) at a trial potential."""
    env = _validated_environment(environment)
    surf = _validated_surface(surface)
    potential = _require_finite(potential_v, "potential_v")

    electrons = electron_collection_current(
        env["electron_current"], potential, env["electron_temperature_ev"])
    ions = ion_collection_current(
        env["ion_current"], potential, env["ion_temperature_ev"])

    impact_energy = env["electron_temperature_ev"] + max(0.0, potential)
    yield_total = secondary_electron_yield(
        impact_energy, surf["yield_max"], surf["energy_max_ev"])
    yield_total += surf["backscatter_fraction"]
    emitted = emission_current(electrons * yield_total, potential,
                               surf["secondary_escape_ev"])

    photo = 0.0
    if surf["sunlit"]:
        photo = emission_current(surf["photoemission_current"], potential,
                                 surf["photoelectron_escape_ev"])
    return -electrons + ions + emitted + photo


def solve_equilibrium_potential(environment, surface,
                                lower_v=DEFAULT_LOWER_POTENTIAL_V,
                                upper_v=DEFAULT_UPPER_POTENTIAL_V,
                                tolerance_v=DEFAULT_POTENTIAL_TOLERANCE_V):
    """Bisect the current balance for the floating potential (volts)."""
    low = _require_finite(lower_v, "lower_v")
    high = _require_finite(upper_v, "upper_v")
    tol = _require_positive(tolerance_v, "tolerance_v")
    if low >= high:
        raise ValueError("lower_v must be below upper_v (%r >= %r)"
                         % (lower_v, upper_v))

    f_low = net_current_at_potential(environment, surface, low)
    f_high = net_current_at_potential(environment, surface, high)
    if f_low <= 0.0:
        raise ValueError(
            "no net positive charging current at %.1f V; the bracket holds "
            "no equilibrium potential (check ion and photoemission input)"
            % low
        )
    if f_high >= 0.0:
        raise ValueError(
            "net current is still positive at %.1f V; widen the bracket or "
            "check the ambient electron current" % high
        )
    steps = 0
    while (high - low) > tol and steps < MAX_BISECTION_STEPS:
        middle = 0.5 * (low + high)
        value = net_current_at_potential(environment, surface, middle)
        if value > 0.0:
            low = middle
        elif value < 0.0:
            high = middle
        else:
            return middle
        steps += 1
    return 0.5 * (low + high)


def categorize_charging_regime(potential_v):
    """Categorize an equilibrium potential into a surface-charging band."""
    potential = _require_finite(potential_v, "potential_v")
    magnitude = abs(potential)
    if _at_or_above(magnitude, REGIME_SEVERE_V):
        band = "severe"
    elif _at_or_above(magnitude, REGIME_MODERATE_V):
        band = "moderate"
    else:
        band = "low"
    polarity = "negative" if potential < 0.0 else "positive"
    return "%s-%s-surface-charging" % (band, polarity)


def differential_charging(potentials):
    """Largest potential difference across a set of adjacent surfaces."""
    if not isinstance(potentials, dict):
        raise ValueError("potentials must be a mapping of name -> volts")
    if len(potentials) < 2:
        raise ValueError(
            "differential-charging needs at least two surfaces, got %d"
            % len(potentials)
        )
    values = {}
    for name, value in potentials.items():
        values[str(name)] = _require_finite(value, "potential of %s" % name)
    high_name = max(values, key=lambda key: (values[key], key))
    low_name = min(values, key=lambda key: (values[key], key))
    return {
        "differential_v": values[high_name] - values[low_name],
        "most_positive": high_name,
        "most_negative": low_name,
    }


def assess_differential_charging(potentials, threshold_v):
    """Compare the differential-charging offset against a threshold."""
    limit = _require_positive(threshold_v, "threshold_v")
    result = differential_charging(potentials)
    differential = result["differential_v"]
    compliant = _at_or_below(differential, limit)
    findings = []
    if not compliant:
        findings.append(
            "differential-charging offset %.3f V between %s and %s exceeds "
            "the %.3f V discharge-onset threshold"
            % (differential, result["most_negative"], result["most_positive"],
               limit)
        )
    result["threshold_v"] = limit
    result["compliant"] = compliant
    result["findings"] = findings
    return result


def assess_surface_charging(environment, surfaces, threshold_v,
                            lower_v=DEFAULT_LOWER_POTENTIAL_V,
                            upper_v=DEFAULT_UPPER_POTENTIAL_V):
    """Full clause 4.1.3 assessment over a set of external surfaces."""
    items = list(surfaces)
    if not items:
        raise ValueError("surface inventory must not be empty")
    limit = _require_positive(threshold_v, "threshold_v")

    per_surface = []
    potentials = {}
    findings = []
    for surface in items:
        surf = _validated_surface(surface)
        if surf["name"] in potentials:
            raise ValueError("duplicate surface name %r" % surf["name"])
        potential = solve_equilibrium_potential(
            environment, surface, lower_v=lower_v, upper_v=upper_v)
        regime = categorize_charging_regime(potential)
        potentials[surf["name"]] = potential
        per_surface.append({
            "name": surf["name"],
            "equilibrium_potential_v": potential,
            "regime": regime,
            "sunlit": surf["sunlit"],
        })
        if regime.startswith("severe"):
            findings.append(
                "surface %s reaches %.1f V (%s)"
                % (surf["name"], potential, regime)
            )

    differential = None
    if len(potentials) >= 2:
        differential = assess_differential_charging(potentials, limit)
        findings.extend(differential["findings"])

    return {
        "surfaces": per_surface,
        "differential": differential,
        "threshold_v": limit,
        "findings": findings,
        "compliant": not findings,
    }

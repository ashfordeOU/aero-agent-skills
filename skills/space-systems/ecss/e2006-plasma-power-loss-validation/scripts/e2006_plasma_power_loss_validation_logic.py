#!/usr/bin/env python3
"""Plasma leakage and power-loss validation, ECSS-E-ST-20-06C clause 8.3.

Deterministic, offline, stdlib-only implementation of the clause 8.3 check:
an exposed conductor held at a potential relative to the surrounding plasma
draws a parasitic current out of that plasma, and the product of potential and
collected current is generated output that never reaches a load. The clause
asks for an analysis showing the summed loss is acceptable.

The procedure implemented here is a paraphrase of the engineering intent, not
of the standard text. The clause is cited as an anchor only.
"""

import math

__all__ = [
    "BUDGET_REL_TOL",
    "GEOMETRY_KEYS",
    "SNAPOVER_ONSET_V",
    "SNAPOVER_AREA_MULTIPLIER",
    "DEFAULT_ALLOWABLE_FRACTION",
    "validate_plasma_environment",
    "electron_thermal_current_density",
    "ion_thermal_current_density",
    "categorize_element_bias",
    "collection_enhancement",
    "element_leakage_current",
    "element_parasitic_power",
    "rank_leakage_contributors",
    "validate_power_loss_budget",
]

#: Relative tolerance that absorbs floating-point representation error when a
#: summed loss is compared against a budget. It does NOT widen the budget: a
#: total that is mathematically equal to the allowance but lands a few ULPs
#: above it after summing several terms still reads as compliant.
BUDGET_REL_TOL = 1e-9

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837015e-31
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27

# Potential magnitude below which an element is treated as sitting at the
# plasma potential and drawing no net parasitic current.
FLOATING_BAND_V = 1.0e-9

# Sheath-collection geometry. A flat conductor collects through roughly its
# own area; a thin cylinder or a small node grows a sheath much larger than
# the hardware, so the collected current outruns the geometric area.
GEOMETRY_KEYS = ("planar-exposed-conductor", "cylindrical-interconnect", "spherical-node")

# Above this bias, secondary electrons knocked off an adjacent dielectric let
# the sheath creep across the insulator and recruit its area as well.
SNAPOVER_ONSET_V = 100.0
SNAPOVER_AREA_MULTIPLIER = 3.5

DEFAULT_ALLOWABLE_FRACTION = 0.01
DOMINANT_CONTRIBUTOR_SHARE = 0.50

BIAS_ELECTRON = "electron-collecting"
BIAS_ION = "ion-collecting"
BIAS_NONE = "non-collecting"


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    out = _require_number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _not_above(value, limit):
    """True when value is at or below limit, tolerating representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=BUDGET_REL_TOL, abs_tol=0.0)


def validate_plasma_environment(env):
    """Validate and normalize the ambient-plasma environment record.

    Keys: electron_density_m3, electron_temperature_ev, ion_temperature_ev
    (defaults to the electron temperature when absent) and ion_mass_amu
    (defaults to atomic oxygen, the dominant ionospheric species).
    """
    if not isinstance(env, dict):
        raise ValueError("plasma environment must be a mapping, got %r" % (env,))
    density = _require_positive(
        env.get("electron_density_m3"), "electron_density_m3"
    )
    te_ev = _require_positive(
        env.get("electron_temperature_ev"), "electron_temperature_ev"
    )
    ti_raw = env.get("ion_temperature_ev", te_ev)
    ti_ev = _require_positive(ti_raw, "ion_temperature_ev")
    mass_amu = _require_positive(env.get("ion_mass_amu", 16.0), "ion_mass_amu")
    return {
        "electron_density_m3": density,
        "electron_temperature_ev": te_ev,
        "ion_temperature_ev": ti_ev,
        "ion_mass_amu": mass_amu,
    }


def electron_thermal_current_density(density_m3, temperature_ev):
    """Random electron flux arriving at a surface at the plasma potential."""
    n = _require_positive(density_m3, "electron_density_m3")
    te = _require_positive(temperature_ev, "electron_temperature_ev")
    speed = math.sqrt(ELEMENTARY_CHARGE_C * te / (2.0 * math.pi * ELECTRON_MASS_KG))
    return ELEMENTARY_CHARGE_C * n * speed


def ion_thermal_current_density(density_m3, temperature_ev, ion_mass_amu=16.0):
    """Random ion flux; heavier and colder, so far weaker than the electron one."""
    n = _require_positive(density_m3, "electron_density_m3")
    ti = _require_positive(temperature_ev, "ion_temperature_ev")
    mass = _require_positive(ion_mass_amu, "ion_mass_amu") * ATOMIC_MASS_UNIT_KG
    speed = math.sqrt(ELEMENTARY_CHARGE_C * ti / (2.0 * math.pi * mass))
    return ELEMENTARY_CHARGE_C * n * speed


def categorize_element_bias(element):
    """Validate one exposed element and categorize which species it draws."""
    if not isinstance(element, dict):
        raise ValueError("exposed element must be a mapping, got %r" % (element,))
    element_id = element.get("element_id")
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("exposed element needs a non-empty element_id")
    geometry = element.get("geometry")
    if geometry not in GEOMETRY_KEYS:
        raise ValueError(
            "element %s has uncategorized geometry %r; known: %s"
            % (element_id, geometry, ", ".join(GEOMETRY_KEYS))
        )
    area = _require_positive(
        element.get("exposed_area_m2"), "exposed_area_m2 of element %s" % element_id
    )
    potential = _require_number(
        element.get("potential_v"), "potential_v of element %s" % element_id
    )
    encapsulated = element.get("encapsulated", False)
    if not isinstance(encapsulated, bool):
        raise ValueError("encapsulated of element %s must be a bool" % element_id)
    adjacent = element.get("dielectric_adjacent", False)
    if not isinstance(adjacent, bool):
        raise ValueError("dielectric_adjacent of element %s must be a bool" % element_id)
    if encapsulated or abs(potential) <= FLOATING_BAND_V:
        bias = BIAS_NONE
    elif potential > 0.0:
        bias = BIAS_ELECTRON
    else:
        bias = BIAS_ION
    return {
        "element_id": element_id,
        "geometry": geometry,
        "exposed_area_m2": area,
        "potential_v": potential,
        "encapsulated": encapsulated,
        "dielectric_adjacent": adjacent,
        "bias": bias,
    }


def collection_enhancement(potential_v, temperature_ev, geometry):
    """Sheath growth factor over the geometric area, by collection geometry.

    Planar hardware collects through roughly its own area. A thin cylinder
    follows the orbit-limited-motion square-root law, a compact node the
    linear law, so a modest bias already multiplies the drawn current.
    """
    if geometry not in GEOMETRY_KEYS:
        raise ValueError("uncategorized geometry %r" % (geometry,))
    magnitude = abs(_require_number(potential_v, "potential_v"))
    temp = _require_positive(temperature_ev, "temperature_ev")
    ratio = magnitude / temp
    if geometry == "planar-exposed-conductor":
        return 1.0
    if geometry == "cylindrical-interconnect":
        return (2.0 / math.sqrt(math.pi)) * math.sqrt(1.0 + ratio)
    return 1.0 + ratio


def element_leakage_current(element, env):
    """Current one exposed element drains out of the surrounding plasma."""
    record = categorize_element_bias(element)
    plasma = validate_plasma_environment(env)
    if record["bias"] == BIAS_NONE:
        record["thermal_current_density_a_m2"] = 0.0
        record["enhancement"] = 0.0
        record["snapover_active"] = False
        record["leakage_current_a"] = 0.0
        return record
    if record["bias"] == BIAS_ELECTRON:
        density = electron_thermal_current_density(
            plasma["electron_density_m3"], plasma["electron_temperature_ev"]
        )
        temperature = plasma["electron_temperature_ev"]
    else:
        density = ion_thermal_current_density(
            plasma["electron_density_m3"],
            plasma["ion_temperature_ev"],
            plasma["ion_mass_amu"],
        )
        temperature = plasma["ion_temperature_ev"]
    enhancement = collection_enhancement(
        record["potential_v"], temperature, record["geometry"]
    )
    snapover = (
        record["bias"] == BIAS_ELECTRON
        and record["dielectric_adjacent"]
        and record["potential_v"] >= SNAPOVER_ONSET_V
    )
    if snapover:
        enhancement *= SNAPOVER_AREA_MULTIPLIER
    record["thermal_current_density_a_m2"] = density
    record["enhancement"] = enhancement
    record["snapover_active"] = snapover
    record["leakage_current_a"] = density * record["exposed_area_m2"] * enhancement
    return record


def element_parasitic_power(element, env):
    """Generated output an element dumps into the plasma instead of a load."""
    record = element_leakage_current(element, env)
    record["parasitic_power_w"] = abs(record["potential_v"]) * record["leakage_current_a"]
    return record


def rank_leakage_contributors(records):
    """Order evaluated elements by parasitic loss, worst first."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list, got %r" % (records,))
    for record in records:
        if not isinstance(record, dict) or "parasitic_power_w" not in record:
            raise ValueError("record %r has not been evaluated" % (record,))
    return sorted(
        records, key=lambda r: (-r["parasitic_power_w"], r["element_id"])
    )


def validate_power_loss_budget(
    elements, env, generated_power_w, allowable_fraction=DEFAULT_ALLOWABLE_FRACTION
):
    """Sum the parasitic loss over every exposed element and judge the budget."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("validate_power_loss_budget needs a non-empty element list")
    generated = _require_positive(generated_power_w, "generated_power_w")
    fraction = _require_number(allowable_fraction, "allowable_fraction")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("allowable_fraction must be in (0, 1], got %r" % (fraction,))
    plasma = validate_plasma_environment(env)
    records = [element_parasitic_power(e, plasma) for e in elements]
    total = math.fsum(r["parasitic_power_w"] for r in records)
    allowance = generated * fraction
    compliant = _not_above(total, allowance)
    findings = []
    if not compliant:
        findings.append(
            "parasitic leakage draws %.6f W, above the %.6f W allowance"
            % (total, allowance)
        )
    ranked = rank_leakage_contributors(records)
    if (
        len(records) > 1
        and total > 0.0
        and ranked[0]["parasitic_power_w"] > DOMINANT_CONTRIBUTOR_SHARE * total
    ):
        findings.append(
            "element %s alone carries more than half the parasitic loss"
            % ranked[0]["element_id"]
        )
    if any(r["snapover_active"] for r in records):
        findings.append(
            "one or more elements bias past the snapover onset against a dielectric"
        )
    return {
        "element_results": records,
        "ranked": ranked,
        "total_parasitic_power_w": total,
        "allowance_w": allowance,
        "loss_fraction": total / generated,
        "margin_w": allowance - total,
        "compliant": compliant,
        "findings": findings,
        "clause_8_3_met": compliant,
    }

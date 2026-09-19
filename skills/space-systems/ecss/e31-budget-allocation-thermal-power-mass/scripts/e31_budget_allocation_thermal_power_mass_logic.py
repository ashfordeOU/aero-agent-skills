"""Thermal, heater power and mass budget allocation and tracking.

Anchor: ECSS-E-ST-31C clause 4.4.2 (budget allocation for the thermal
control subsystem). Paraphrased into an implementable procedure; no
standard text is reproduced.

Scope note: this covers the allocate-and-track discipline of the clause -
three budgets rolled up the same way, each against its own allocation.
Sizing a solar array or a battery from an eclipse profile is a different
job and lives elsewhere.

Procedure implemented here
--------------------------
1. Every budget line carries a raw value and a design-maturity category.
   The category sets the contingency the line carries: an off-the-shelf
   item little, a modified item more, a new design most. A line with no
   category is unknown, not zero, and is refused.
2. Roll the lines up twice - raw and with contingency - so the growth the
   contingency policy is carrying is visible rather than buried.
3. Apply the system-level margin the project holds on top of the rolled-up
   contingency total, giving the value the budget is tracked at.
4. Compare that value with the allocation and report the margin fraction,
   with a named tolerance so a budget landing exactly on its allocation is
   a decision rather than a failure.
5. Do this three times over: the dissipation the radiators must reject
   against the rejection capacity at the hot-case radiator and sink
   temperatures, the cold-case heater demand against the heater power
   allocation, and the thermal hardware mass against the mass allocation.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN_W_PER_M2K4",
    "MATURITY_CONTINGENCY",
    "BUDGET_TOLERANCE",
    "validate_positive",
    "maturity_contingency",
    "line_with_contingency",
    "roll_up",
    "apply_system_margin",
    "budget_status",
    "radiator_rejection_w",
    "assess_thermal_rejection_budget",
    "assess_heater_power_budget",
    "assess_mass_budget",
    "assess_budget_allocation",
]

STEFAN_BOLTZMANN_W_PER_M2K4 = 5.670374419e-8

# Contingency a budget line carries, by the design maturity of the item it
# represents. New designs grow; qualified hardware reused as-is does not.
MATURITY_CONTINGENCY = {
    "off-the-shelf": 0.05,
    "modified": 0.10,
    "new-design": 0.20,
}

# A budget landing exactly on its allocation is a decision, not a failure;
# absorb the representation error at the boundary.
BUDGET_TOLERANCE = 1e-9


def validate_positive(label, value, allow_zero=False):
    """Return value as a positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def maturity_contingency(category):
    """Return the contingency fraction a design-maturity category carries."""
    if not isinstance(category, str):
        raise ValueError("maturity category must be a string, got %r" % (category,))
    if category not in MATURITY_CONTINGENCY:
        raise ValueError(
            "unknown maturity category %r; the categories recognised here are %s"
            % (category, ", ".join(sorted(MATURITY_CONTINGENCY)))
        )
    return MATURITY_CONTINGENCY[category]


def line_with_contingency(line, value_key):
    """Return one budget line value with its maturity contingency applied."""
    if not isinstance(line, dict):
        raise ValueError("budget line must be a mapping")
    if "name" not in line:
        raise ValueError("budget line missing required key 'name'")
    if value_key not in line:
        raise ValueError(
            "budget line %r missing required key %r" % (line["name"], value_key)
        )
    if "maturity" not in line:
        raise ValueError(
            "budget line %r declares no maturity category; an uncategorized "
            "line is unknown, not zero" % (line["name"],)
        )
    raw = validate_positive(
        "%s of %r" % (value_key, line["name"]), line[value_key], allow_zero=True
    )
    return raw * (1.0 + maturity_contingency(line["maturity"]))


def roll_up(lines, value_key):
    """Return the raw and with-contingency totals of a budget line set."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence of budget lines")
    raw_total = 0.0
    loaded_total = 0.0
    names = []
    for line in lines:
        loaded_total += line_with_contingency(line, value_key)
        raw_total += float(line[value_key])
        names.append(line["name"])
    if len(set(names)) != len(names):
        raise ValueError("two budget lines share a name; the roll-up cannot be traced")
    return {"raw": raw_total, "with_contingency": loaded_total}


def apply_system_margin(total, system_margin_fraction):
    """Return a rolled-up total with the system-level margin applied."""
    value = validate_positive("total", total, allow_zero=True)
    margin = validate_positive(
        "system_margin_fraction", system_margin_fraction, allow_zero=True
    )
    if margin >= 1.0:
        raise ValueError(
            "system_margin_fraction must be below one, got %g" % margin
        )
    return value * (1.0 + margin)


def budget_status(tracked_value, allocation):
    """Return the margin fraction and verdict of a tracked budget."""
    tracked = validate_positive("tracked_value", tracked_value, allow_zero=True)
    allowed = validate_positive("allocation", allocation)
    margin = (allowed - tracked) / allowed
    compliant = tracked < allowed or math.isclose(
        tracked, allowed, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )
    return {
        "tracked_value": tracked,
        "allocation": allowed,
        "margin_fraction": margin,
        "compliant": compliant,
    }


def radiator_rejection_w(area_m2, emissivity, radiator_temperature_k, sink_temperature_k):
    """Return the net heat a radiator rejects to its sink, in watts."""
    area = validate_positive("area_m2", area_m2)
    emissivity = validate_positive("emissivity", emissivity)
    if emissivity > 1.0:
        raise ValueError("emissivity must not exceed one, got %g" % emissivity)
    radiator = validate_positive("radiator_temperature_k", radiator_temperature_k)
    sink = validate_positive("sink_temperature_k", sink_temperature_k, allow_zero=True)
    if sink >= radiator:
        raise ValueError(
            "sink temperature %g K is not below the radiator temperature %g K; "
            "no net rejection is possible" % (sink, radiator)
        )
    return emissivity * STEFAN_BOLTZMANN_W_PER_M2K4 * area * (
        radiator ** 4 - sink ** 4
    )


def assess_thermal_rejection_budget(budget):
    """Assess the dissipation roll-up against the radiator rejection capacity."""
    if not isinstance(budget, dict):
        raise ValueError("thermal budget must be a mapping")
    for key in ("lines", "system_margin_fraction", "radiator_area_m2",
                "radiator_emissivity", "radiator_temperature_k",
                "sink_temperature_k"):
        if key not in budget:
            raise ValueError("thermal budget missing required key %r" % key)
    totals = roll_up(budget["lines"], "dissipation_w")
    tracked = apply_system_margin(
        totals["with_contingency"], budget["system_margin_fraction"]
    )
    capacity = radiator_rejection_w(
        budget["radiator_area_m2"], budget["radiator_emissivity"],
        budget["radiator_temperature_k"], budget["sink_temperature_k"],
    )
    status = budget_status(tracked, capacity)
    findings = []
    if not status["compliant"]:
        findings.append(
            "hot-case dissipation %.2f W exceeds the %.2f W the radiator rejects "
            "at its hot-case temperature" % (tracked, capacity)
        )
    return {
        "raw_w": totals["raw"],
        "with_contingency_w": totals["with_contingency"],
        "tracked_w": tracked,
        "rejection_capacity_w": capacity,
        "margin_fraction": status["margin_fraction"],
        "compliant": status["compliant"],
        "findings": findings,
    }


def assess_heater_power_budget(budget):
    """Assess the cold-case heater roll-up against the power allocation."""
    if not isinstance(budget, dict):
        raise ValueError("heater budget must be a mapping")
    for key in ("lines", "system_margin_fraction", "allocation_w"):
        if key not in budget:
            raise ValueError("heater budget missing required key %r" % key)
    totals = roll_up(budget["lines"], "heater_power_w")
    tracked = apply_system_margin(
        totals["with_contingency"], budget["system_margin_fraction"]
    )
    status = budget_status(tracked, budget["allocation_w"])
    findings = []
    if not status["compliant"]:
        findings.append(
            "cold-case heater demand %.2f W exceeds the %.2f W heater power "
            "allocation" % (tracked, status["allocation"])
        )
    return {
        "raw_w": totals["raw"],
        "with_contingency_w": totals["with_contingency"],
        "tracked_w": tracked,
        "allocation_w": status["allocation"],
        "margin_fraction": status["margin_fraction"],
        "compliant": status["compliant"],
        "findings": findings,
    }


def assess_mass_budget(budget):
    """Assess the thermal hardware mass roll-up against the mass allocation."""
    if not isinstance(budget, dict):
        raise ValueError("mass budget must be a mapping")
    for key in ("lines", "system_margin_fraction", "allocation_kg"):
        if key not in budget:
            raise ValueError("mass budget missing required key %r" % key)
    totals = roll_up(budget["lines"], "mass_kg")
    tracked = apply_system_margin(
        totals["with_contingency"], budget["system_margin_fraction"]
    )
    status = budget_status(tracked, budget["allocation_kg"])
    findings = []
    if not status["compliant"]:
        findings.append(
            "thermal hardware mass %.3f kg exceeds the %.3f kg mass allocation"
            % (tracked, status["allocation"])
        )
    return {
        "raw_kg": totals["raw"],
        "with_contingency_kg": totals["with_contingency"],
        "tracked_kg": tracked,
        "allocation_kg": status["allocation"],
        "margin_fraction": status["margin_fraction"],
        "compliant": status["compliant"],
        "findings": findings,
    }


def assess_budget_allocation(spec):
    """Run the full clause 4.4.2 budget allocation and tracking assessment.

    spec keys: thermal, heater_power, mass - each a budget record.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("thermal", "heater_power", "mass"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    thermal = assess_thermal_rejection_budget(spec["thermal"])
    heater = assess_heater_power_budget(spec["heater_power"])
    mass = assess_mass_budget(spec["mass"])
    findings = thermal["findings"] + heater["findings"] + mass["findings"]
    tightest = min(
        (("thermal", thermal["margin_fraction"]),
         ("heater_power", heater["margin_fraction"]),
         ("mass", mass["margin_fraction"])),
        key=lambda pair: pair[1],
    )
    return {
        "thermal": thermal,
        "heater_power": heater,
        "mass": mass,
        "tightest_budget": tightest[0],
        "tightest_margin_fraction": tightest[1],
        "compliant": thermal["compliant"] and heater["compliant"]
        and mass["compliant"],
        "findings": findings,
    }

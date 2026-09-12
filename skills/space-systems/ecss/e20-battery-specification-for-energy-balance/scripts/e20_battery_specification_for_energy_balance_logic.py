#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.6.2 -- battery capacity for mission energy balance.

Deterministic, offline, standard-library-only helpers that size a secondary
battery from a declared mission phase set, verify that the energy balance
closes in every phase including the contingency modes, and carry the sizing
across capacity fade between beginning of life and end of life.

The procedure is a paraphrase of the clause intent; no standard text is
reproduced. The clause is cited as the anchor only.
"""

# Default allowable depth of discharge per phase category. Project values
# override these; they exist so an under-specified phase still has a limit.
DEFAULT_MAX_DOD = {
    "launch": 0.40,
    "transfer": 0.40,
    "nominal-operations": 0.30,
    "eclipse": 0.30,
    "contingency": 0.60,
    "safe-mode": 0.60,
}

CONTINGENCY_CATEGORIES = frozenset({"contingency", "safe-mode"})

PHASE_CATEGORIES = frozenset(DEFAULT_MAX_DOD)


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return float(value)


def _non_negative_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return float(value)


def _unit_fraction(label, value):
    """Fraction in the open-closed interval (0, 1]."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not 0.0 < value <= 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (label, value))
    return float(value)


def validate_phase(phase):
    """Normalize one mission phase record.

    Required keys: name, category, duration_h, load_power_w,
    generated_power_w. Optional: max_dod, in_recurring_cycle.
    """
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping, got %r" % (phase,))
    name = phase.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase needs a non-empty string 'name'")
    name = name.strip()
    category = phase.get("category")
    if category not in PHASE_CATEGORIES:
        raise ValueError(
            "phase %s has unrecognized category %r" % (name, category)
        )
    duration_h = _positive_number("%s duration_h" % name, phase.get("duration_h"))
    load_power_w = _non_negative_number(
        "%s load_power_w" % name, phase.get("load_power_w")
    )
    generated_power_w = _non_negative_number(
        "%s generated_power_w" % name, phase.get("generated_power_w")
    )
    raw_dod = phase.get("max_dod")
    max_dod = (
        DEFAULT_MAX_DOD[category]
        if raw_dod is None
        else _unit_fraction("%s max_dod" % name, raw_dod)
    )
    in_cycle = phase.get("in_recurring_cycle")
    if in_cycle is None:
        in_cycle = category not in CONTINGENCY_CATEGORIES
    elif not isinstance(in_cycle, bool):
        raise ValueError("%s: in_recurring_cycle must be a boolean" % name)
    return {
        "name": name,
        "category": category,
        "duration_h": duration_h,
        "load_power_w": load_power_w,
        "generated_power_w": generated_power_w,
        "max_dod": max_dod,
        "in_recurring_cycle": in_cycle,
        "is_contingency": category in CONTINGENCY_CATEGORIES,
    }


def phase_energy_wh(phase, distribution_efficiency=1.0):
    """Energy produced, consumed and drawn from the store during one phase."""
    normalized = validate_phase(phase)
    eta_dist = _unit_fraction("distribution_efficiency", distribution_efficiency)
    available_wh = normalized["generated_power_w"] * normalized["duration_h"]
    consumed_wh = (
        normalized["load_power_w"] * normalized["duration_h"] / eta_dist
    )
    net_wh = available_wh - consumed_wh
    return {
        "name": normalized["name"],
        "available_wh": available_wh,
        "consumed_wh": consumed_wh,
        "net_wh": net_wh,
        "discharge_wh": max(0.0, -net_wh),
        "surplus_wh": max(0.0, net_wh),
        "in_recurring_cycle": normalized["in_recurring_cycle"],
        "max_dod": normalized["max_dod"],
        "is_contingency": normalized["is_contingency"],
    }


def required_capacity_wh(
    phase, distribution_efficiency=1.0, discharge_efficiency=1.0
):
    """Usable-energy capacity the phase demands, in watt-hours.

    The store must deliver the phase discharge through the discharge path
    while staying inside the allowable depth of discharge, so the rated
    capacity is the phase discharge divided by both fractions.
    """
    energy = phase_energy_wh(phase, distribution_efficiency)
    eta_dis = _unit_fraction("discharge_efficiency", discharge_efficiency)
    if energy["discharge_wh"] == 0.0:
        return 0.0
    return energy["discharge_wh"] / (eta_dis * energy["max_dod"])


def end_of_life_capacity_wh(bol_capacity_wh, annual_fade_fraction, mission_years):
    """Capacity remaining after fade over the mission duration."""
    bol = _positive_number("bol_capacity_wh", bol_capacity_wh)
    if (
        isinstance(annual_fade_fraction, bool)
        or not isinstance(annual_fade_fraction, (int, float))
        or not 0.0 <= annual_fade_fraction < 1.0
    ):
        raise ValueError(
            "annual_fade_fraction must lie in [0, 1), got %r"
            % (annual_fade_fraction,)
        )
    years = _non_negative_number("mission_years", mission_years)
    return bol * (1.0 - float(annual_fade_fraction)) ** years


def bol_capacity_for_eol_wh(
    eol_capacity_wh, annual_fade_fraction, mission_years
):
    """Beginning-of-life capacity needed to still meet an end-of-life demand."""
    eol = _positive_number("eol_capacity_wh", eol_capacity_wh)
    retained = end_of_life_capacity_wh(1.0, annual_fade_fraction, mission_years)
    return eol / retained


def recharge_feasibility(
    discharge_phase, charge_phase, charge_efficiency=1.0,
    distribution_efficiency=1.0,
):
    """Check that the charge window restores what the discharge window drew."""
    eta_chg = _unit_fraction("charge_efficiency", charge_efficiency)
    drawn = phase_energy_wh(discharge_phase, distribution_efficiency)
    window = phase_energy_wh(charge_phase, distribution_efficiency)
    restored_wh = window["surplus_wh"] * eta_chg
    deficit_wh = max(0.0, drawn["discharge_wh"] - restored_wh)
    return {
        "discharge_wh": drawn["discharge_wh"],
        "surplus_wh": window["surplus_wh"],
        "restored_wh": restored_wh,
        "deficit_wh": deficit_wh,
        "feasible": deficit_wh == 0.0,
    }


def size_battery(
    phases, distribution_efficiency=1.0, discharge_efficiency=1.0,
    annual_fade_fraction=0.0, mission_years=0.0,
):
    """Size the store from the driving phase and carry it back to beginning of life."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list of phase records")
    per_phase = []
    for phase in phases:
        normalized = validate_phase(phase)
        demand = required_capacity_wh(
            phase, distribution_efficiency, discharge_efficiency
        )
        per_phase.append(
            {
                "name": normalized["name"],
                "category": normalized["category"],
                "required_capacity_wh": demand,
                "is_contingency": normalized["is_contingency"],
            }
        )
    driving = max(per_phase, key=lambda row: row["required_capacity_wh"])
    eol_required = driving["required_capacity_wh"]
    if eol_required <= 0.0:
        bol_required = 0.0
    else:
        bol_required = bol_capacity_for_eol_wh(
            eol_required, annual_fade_fraction, mission_years
        )
    return {
        "per_phase": tuple(per_phase),
        "driving_phase": driving["name"],
        "required_eol_capacity_wh": eol_required,
        "required_bol_capacity_wh": bol_required,
    }


def verify_energy_balance(
    phases, eol_capacity_wh, distribution_efficiency=1.0,
    discharge_efficiency=1.0,
):
    """Depth of discharge per phase plus the recurring-cycle net energy check."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list of phase records")
    capacity = _positive_number("eol_capacity_wh", eol_capacity_wh)
    eta_dis = _unit_fraction("discharge_efficiency", discharge_efficiency)
    findings = []
    rows = []
    cycle_net_wh = 0.0
    for phase in phases:
        energy = phase_energy_wh(phase, distribution_efficiency)
        dod = energy["discharge_wh"] / (eta_dis * capacity)
        within = dod <= energy["max_dod"]
        if not within:
            findings.append(
                "%s: depth of discharge %.4f exceeds allowable %.4f"
                % (energy["name"], dod, energy["max_dod"])
            )
        if energy["in_recurring_cycle"]:
            cycle_net_wh += energy["net_wh"]
        rows.append(
            {
                "name": energy["name"],
                "discharge_wh": energy["discharge_wh"],
                "depth_of_discharge": dod,
                "max_dod": energy["max_dod"],
                "within_limits": within,
                "margin": energy["max_dod"] - dod,
            }
        )
    if cycle_net_wh < 0.0:
        findings.append(
            "recurring cycle net energy %.4f Wh is negative; the store depletes"
            % cycle_net_wh
        )
    return {
        "per_phase": tuple(rows),
        "cycle_net_wh": cycle_net_wh,
        "findings": tuple(findings),
        "balanced": not findings,
    }


def assess_battery_specification(spec):
    """Top-level clause 5.6.2 assessment over a declared specification."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping, got %r" % (spec,))
    phases = spec.get("phases")
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("specification needs a non-empty 'phases' list")
    eta_dist = _unit_fraction(
        "distribution_efficiency", spec.get("distribution_efficiency", 1.0)
    )
    eta_dis = _unit_fraction(
        "discharge_efficiency", spec.get("discharge_efficiency", 1.0)
    )
    fade = spec.get("annual_fade_fraction", 0.0)
    years = spec.get("mission_years", 0.0)
    sizing = size_battery(phases, eta_dist, eta_dis, fade, years)
    findings = []
    normalized = [validate_phase(phase) for phase in phases]
    if not any(row["is_contingency"] for row in normalized):
        findings.append(
            "phase set declares no contingency or safe mode; the energy "
            "balance is unproven outside nominal operation"
        )
    declared_bol = spec.get("declared_bol_capacity_wh")
    verification = None
    if declared_bol is not None:
        declared_bol = _positive_number("declared_bol_capacity_wh", declared_bol)
        eol_available = end_of_life_capacity_wh(declared_bol, fade, years)
        if eol_available + 1e-9 < sizing["required_eol_capacity_wh"]:
            findings.append(
                "declared capacity gives %.4f Wh at end of life against a "
                "%.4f Wh demand from phase %s"
                % (
                    eol_available,
                    sizing["required_eol_capacity_wh"],
                    sizing["driving_phase"],
                )
            )
        verification = verify_energy_balance(phases, eol_available, eta_dist, eta_dis)
        findings.extend(verification["findings"])
    return {
        "sizing": sizing,
        "verification": verification,
        "findings": tuple(findings),
        "compliant": not findings,
    }

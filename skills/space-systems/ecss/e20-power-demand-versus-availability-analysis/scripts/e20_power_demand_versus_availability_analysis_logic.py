#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.2.2.2 power demand versus availability
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires the power a
spacecraft can supply to be compared against the power its loads
demand, phase by phase across the mission, and explicitly including
peak loads rather than time-averaged consumption alone. Availability is
not one number: the generated power falls with array degradation over
the mission epoch, and during an eclipse the source contributes
nothing, so the stored energy carries the load. Demand is not one
number either: a duty-cycled load consumes its peak only for its duty
fraction, while loads that fire together present their peaks
simultaneously and the bus has to survive that coincidence.

This module builds a phase demand from a load list, degrades the
generated power to the phase epoch, compares availability against both
the averaged and the coincident-peak demand, sizes the battery energy
and depth of discharge needed to cover a deficit, and grades the phase
power margin. It does not design the array, model cell chemistry, or
set project-specific margin values.
"""

# Mission phases the analysis walks. Every phase is graded separately;
# a subsystem that closes on orbit average can still fail at launch or
# in safe mode.
MISSION_PHASES = (
    "launch",
    "leop",
    "transfer",
    "nominal_operations",
    "eclipse",
    "safe_mode",
    "end_of_life",
)

# How a load presents itself on the bus within a phase.
LOAD_CATEGORIES = ("continuous", "duty_cycled", "coincident_peak")

SECONDS_PER_HOUR = 3600.0

FINDING_KEYS = ("energy_balance", "peak_capability", "battery_depth", "margin")


def load_category(load):
    """Category of one load entry, read from its "category" key.
    Raises ValueError for a missing or unrecognized category."""
    category = load.get("category")
    if category not in LOAD_CATEGORIES:
        raise ValueError(
            "uncategorized load %r; expected one of %s"
            % (load.get("load_id", category), list(LOAD_CATEGORIES))
        )
    return category


def load_average_power(peak_power_w, duty_cycle):
    """Time-averaged consumption of a load over the phase: peak power x
    duty cycle. Raises ValueError for a negative peak power or a duty
    cycle outside [0, 1]."""
    if peak_power_w < 0:
        raise ValueError("peak_power_w must be >= 0")
    if not (0.0 <= duty_cycle <= 1.0):
        raise ValueError("duty_cycle must be within [0, 1], got %r" % (duty_cycle,))
    return peak_power_w * duty_cycle


def phase_demand(loads):
    """Averaged and coincident-peak demand for one phase.

    loads: iterable of {"load_id", "category", "peak_power_w",
    "duty_cycle"}. A continuous load runs at duty 1.0 and is forced to
    it. The averaged demand sums every load's time-averaged draw. The
    coincident-peak demand sums the full peak of every coincident_peak
    load plus the averaged draw of the rest, which is what the bus
    actually sees when the peak loads fire together. Raises ValueError
    for an empty load list, a duplicated identifier, or an
    uncategorized load."""
    loads = list(loads)
    if not loads:
        raise ValueError("phase_demand needs at least one load")
    seen = set()
    average_w = 0.0
    peak_w = 0.0
    for load in loads:
        load_id = load.get("load_id")
        if not load_id:
            raise ValueError("load_id must be a non-empty identifier")
        if load_id in seen:
            raise ValueError("duplicate load_id %r in phase" % (load_id,))
        seen.add(load_id)
        category = load_category(load)
        duty = 1.0 if category == "continuous" else load["duty_cycle"]
        averaged = load_average_power(load["peak_power_w"], duty)
        average_w += averaged
        if category == "coincident_peak":
            peak_w += load["peak_power_w"]
        else:
            peak_w += averaged
    return {"average_w": average_w, "peak_w": peak_w, "load_count": len(loads)}


def degraded_available_power(bol_power_w, annual_degradation_fraction, years):
    """Generated power at the phase epoch: beginning-of-life power
    decayed by the annual degradation fraction over the elapsed years.
    Raises ValueError for a negative power or elapsed time, or a
    degradation fraction outside [0, 1)."""
    if bol_power_w < 0:
        raise ValueError("bol_power_w must be >= 0")
    if years < 0:
        raise ValueError("years must be >= 0")
    if not (0.0 <= annual_degradation_fraction < 1.0):
        raise ValueError(
            "annual_degradation_fraction must be within [0, 1), got %r"
            % (annual_degradation_fraction,)
        )
    return bol_power_w * (1.0 - annual_degradation_fraction) ** years


def power_margin_fraction(available_w, demand_w):
    """Fraction of the available power left unspent by the demand;
    negative when demand exceeds supply. Raises ValueError for a
    non-positive availability or a negative demand."""
    if available_w <= 0:
        raise ValueError("available_w must be > 0")
    if demand_w < 0:
        raise ValueError("demand_w must be >= 0")
    return (available_w - demand_w) / available_w


def battery_energy_required_wh(deficit_power_w, duration_s):
    """Energy the store must supply to cover a power deficit held for a
    duration. Raises ValueError for a negative deficit or duration."""
    if deficit_power_w < 0:
        raise ValueError("deficit_power_w must be >= 0")
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    return deficit_power_w * duration_s / SECONDS_PER_HOUR


def depth_of_discharge(energy_drawn_wh, battery_capacity_wh):
    """Fraction of the battery capacity drawn. Raises ValueError for a
    negative draw or a non-positive capacity."""
    if energy_drawn_wh < 0:
        raise ValueError("energy_drawn_wh must be >= 0")
    if battery_capacity_wh <= 0:
        raise ValueError("battery_capacity_wh must be > 0")
    return energy_drawn_wh / battery_capacity_wh


def phase_analysis(phase):
    """Full clause 5.2.2.2 analysis of one mission phase.

    In a phase with no generation the margin graded is the unused
    fraction of the allowed discharge depth rather than a power ratio.

    phase: {"phase_id", "loads", "bol_power_w",
    "annual_degradation_fraction", "years_at_phase", "duration_s",
    "battery_capacity_wh", "max_depth_of_discharge",
    "battery_discharge_capability_w", "required_margin"}. Returns the
    demand, the available power, the achieved margin, the battery draw,
    and a finding list under each of FINDING_KEYS. Raises ValueError for
    an unrecognized phase identifier or through the helpers above."""
    phase_id = phase["phase_id"]
    if phase_id not in MISSION_PHASES:
        raise ValueError(
            "uncategorized mission phase %r under E-ST-20C clause 5.2.2.2"
            % (phase_id,)
        )
    required_margin = phase["required_margin"]
    if not (0.0 <= required_margin < 1.0):
        raise ValueError(
            "required_margin must be within [0, 1), got %r" % (required_margin,)
        )
    demand = phase_demand(phase["loads"])
    available_w = degraded_available_power(
        phase["bol_power_w"],
        phase["annual_degradation_fraction"],
        phase["years_at_phase"],
    )
    deficit_w = max(0.0, demand["average_w"] - available_w)
    energy_wh = battery_energy_required_wh(deficit_w, phase["duration_s"])
    dod = depth_of_discharge(energy_wh, phase["battery_capacity_wh"])
    max_dod = phase["max_depth_of_discharge"]
    if not (0.0 < max_dod <= 1.0):
        raise ValueError(
            "max_depth_of_discharge must be within (0, 1], got %r" % (max_dod,)
        )
    discharge_capability_w = phase["battery_discharge_capability_w"]
    if discharge_capability_w < 0:
        raise ValueError("battery_discharge_capability_w must be >= 0")
    peak_capability_w = available_w + discharge_capability_w

    # A deficit is not by itself a defect: in eclipse it is the design
    # intent, and the store is there to cover it. It becomes a finding
    # only when the store cannot -- either at all (the energy exceeds
    # the whole capacity, so the balance does not close) or not within
    # the depth-of-discharge limit the cell life is sized to.
    energy_balance = []
    battery_depth = []
    if deficit_w > 0:
        if dod > 1.0:
            energy_balance.append(
                {
                    "issue": "phase_energy_balance_not_closed",
                    "phase": phase_id,
                    "deficit_w": deficit_w,
                    "battery_energy_wh": energy_wh,
                    "capacity_wh": phase["battery_capacity_wh"],
                }
            )
        elif dod > max_dod:
            battery_depth.append(
                {
                    "issue": "battery_discharge_depth_exceeded",
                    "phase": phase_id,
                    "depth_of_discharge": dod,
                    "limit": max_dod,
                }
            )
    peak_capability = []
    if demand["peak_w"] > peak_capability_w:
        peak_capability.append(
            {
                "issue": "coincident_peak_exceeds_supply_capability",
                "phase": phase_id,
                "peak_demand_w": demand["peak_w"],
                "capability_w": peak_capability_w,
            }
        )
    margin = []
    if available_w > 0:
        # Generation is present: margin is the unspent fraction of the
        # power the source delivers at this epoch.
        achieved_margin = power_margin_fraction(available_w, demand["average_w"])
        if achieved_margin < required_margin:
            margin.append(
                {
                    "issue": "phase_power_margin_below_requirement",
                    "phase": phase_id,
                    "achieved_margin": achieved_margin,
                    "required_margin": required_margin,
                }
            )
    else:
        # No generation in this phase (eclipse, a stowed array before
        # deployment): the store carries the load, so the reserve to
        # grade is the usable discharge depth still unused, not a power
        # ratio against a zero source.
        achieved_margin = (max_dod - dod) / max_dod
        if achieved_margin < required_margin:
            margin.append(
                {
                    "issue": "stored_energy_margin_below_requirement",
                    "phase": phase_id,
                    "achieved_margin": achieved_margin,
                    "required_margin": required_margin,
                }
            )
    return {
        "phase": phase_id,
        "demand": demand,
        "available_w": available_w,
        "peak_capability_w": peak_capability_w,
        "battery_energy_wh": energy_wh,
        "depth_of_discharge": dod,
        "achieved_margin": achieved_margin,
        "energy_balance": energy_balance,
        "peak_capability": peak_capability,
        "battery_depth": battery_depth,
        "margin": margin,
    }


def mission_analysis(phases):
    """Per-phase analysis for the whole mission, keyed by phase
    identifier. Raises ValueError for an empty phase list or a
    duplicated phase identifier."""
    phases = list(phases)
    if not phases:
        raise ValueError("mission_analysis needs at least one mission phase")
    result = {}
    for phase in phases:
        analysis = phase_analysis(phase)
        if analysis["phase"] in result:
            raise ValueError("duplicate phase_id %r in mission" % (analysis["phase"],))
        result[analysis["phase"]] = analysis
    return result


def phase_is_power_positive(analysis):
    """True when every finding list for one phase is empty -- supply
    covers the averaged demand with its required margin, the bus
    survives the coincident peak, and the store stays within its
    discharge limit."""
    return all(len(analysis[key]) == 0 for key in FINDING_KEYS)


def is_mission_power_positive(analysis_by_phase):
    """True when every phase in a mission_analysis result is power
    positive."""
    return all(
        phase_is_power_positive(analysis) for analysis in analysis_by_phase.values()
    )

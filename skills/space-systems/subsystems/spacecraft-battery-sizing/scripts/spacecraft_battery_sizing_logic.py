"""Spacecraft battery sizing for Earth-orbiting spacecraft power subsystems.

Pure stdlib module implementing the eclipse energy to cell layout chain for
a Li-ion spacecraft battery: eclipse energy (Wh), required nameplate
capacity from the depth-of-discharge limit and discharge efficiency,
capacity in ampere hours at the bus voltage, series/parallel cell layout,
discharge C-rate check against the cell limit, and pack mass from the pack
energy density.

All inputs are physical SI-compatible magnitudes (W, s, V, Ah). Non-physical
inputs raise ValueError. Deterministic, offline, no external dependencies.
"""

import math

EFF_DISCHARGE = 0.95
"""Discharge efficiency of the battery, module default (fraction, in (0, 1])."""

SPEC_ENERGY_WH_KG = 150.0
"""Pack-level specific energy used for the mass estimate (Wh/kg)."""

CELL_VOLTAGE = 3.7
"""Nominal voltage of one Li-ion cell (V), module default."""

CELL_AMPHOUR = 50.0
"""Nominal capacity of one Li-ion cell (Ah), module default."""


def eclipse_energy_wh(eclipse_load_w, eclipse_duration_s):
    """Energy the battery must deliver during the eclipse, E = P * t / 3600.

    Args:
        eclipse_load_w: eclipse power draw (W), must be >= 0.
        eclipse_duration_s: eclipse duration (s), must be > 0.

    Returns:
        Eclipse energy in Wh (float).
    """
    if eclipse_load_w < 0.0:
        raise ValueError("eclipse load must be >= 0 W")
    if eclipse_duration_s <= 0.0:
        raise ValueError("eclipse duration must be > 0 s")
    return eclipse_load_w * eclipse_duration_s / 3600.0


def required_capacity_wh(eclipse_energy_wh_value, dod_limit,
                         discharge_efficiency=EFF_DISCHARGE):
    """Required nameplate capacity from energy, DOD limit and efficiency.

    C = E / (dod_limit * discharge_efficiency).

    Args:
        eclipse_energy_wh_value: eclipse energy (Wh), must be >= 0.
        dod_limit: depth of discharge limit (fraction), must be in (0, 1].
        discharge_efficiency: discharge efficiency (fraction), must be in
            (0, 1]; defaults to the module constant EFF_DISCHARGE.

    Returns:
        Required capacity in Wh (float).
    """
    if eclipse_energy_wh_value < 0.0:
        raise ValueError("eclipse energy must be >= 0 Wh")
    if not 0.0 < dod_limit <= 1.0:
        raise ValueError("depth of discharge limit must be in (0, 1]")
    if not 0.0 < discharge_efficiency <= 1.0:
        raise ValueError("discharge efficiency must be in (0, 1]")
    return eclipse_energy_wh_value / (dod_limit * discharge_efficiency)


def capacity_ah(capacity_wh, bus_voltage):
    """Convert a required capacity to ampere hours at the bus voltage.

    Ah = capacity_wh / bus_voltage.

    Args:
        capacity_wh: capacity (Wh), must be >= 0.
        bus_voltage: regulated bus voltage (V), must be > 0.

    Returns:
        Capacity in Ah (float).
    """
    if capacity_wh < 0.0:
        raise ValueError("capacity must be >= 0 Wh")
    if bus_voltage <= 0.0:
        raise ValueError("bus voltage must be > 0 V")
    return capacity_wh / bus_voltage


def cell_layout(required_capacity_wh, bus_voltage, cell_voltage, cell_ah):
    """Lay out the series and parallel cell counts for the bus.

    n_series = ceil(bus_voltage / cell_voltage); n_parallel = ceil(Ah /
    cell_ah) where Ah is the capacity at the bus voltage. Series cells set
    the pack nominal voltage, parallel strings set the installed capacity.

    Args:
        required_capacity_wh: required capacity (Wh), must be > 0.
        bus_voltage: regulated bus voltage (V), must be > 0.
        cell_voltage: nominal cell voltage (V), must be > 0.
        cell_ah: nominal cell capacity (Ah), must be > 0.

    Returns:
        Dict with n_series, n_parallel, total_cells, pack_nominal_voltage
        (n_series * cell_voltage) and installed_capacity_ah (n_parallel *
        cell_ah).
    """
    if required_capacity_wh <= 0.0:
        raise ValueError("required capacity must be > 0 Wh")
    if cell_voltage <= 0.0:
        raise ValueError("cell voltage must be > 0 V")
    if cell_ah <= 0.0:
        raise ValueError("cell capacity must be > 0 Ah")
    ah_at_bus = capacity_ah(required_capacity_wh, bus_voltage)
    n_series = math.ceil(bus_voltage / cell_voltage)
    n_parallel = math.ceil(ah_at_bus / cell_ah)
    return {
        "n_series": n_series,
        "n_parallel": n_parallel,
        "total_cells": n_series * n_parallel,
        "pack_nominal_voltage": n_series * cell_voltage,
        "installed_capacity_ah": n_parallel * cell_ah,
    }


def discharge_rate_check(orbit_load_w, bus_voltage, installed_capacity_ah,
                         cell_max_c_rate):
    """Check the discharge C-rate against the cell limit.

    I = orbit_load_w / bus_voltage; c_rate = I / installed_capacity_ah.

    Args:
        orbit_load_w: orbit (eclipse) load (W), must be > 0.
        bus_voltage: regulated bus voltage (V), must be > 0.
        installed_capacity_ah: installed pack capacity (Ah), must be > 0.
        cell_max_c_rate: cell maximum C-rate (1/h), must be > 0.

    Returns:
        Dict with current_A, c_rate and within_limit (c_rate <=
        cell_max_c_rate).
    """
    if orbit_load_w <= 0.0:
        raise ValueError("orbit load must be > 0 W")
    if bus_voltage <= 0.0:
        raise ValueError("bus voltage must be > 0 V")
    if installed_capacity_ah <= 0.0:
        raise ValueError("installed capacity must be > 0 Ah")
    if cell_max_c_rate <= 0.0:
        raise ValueError("cell max C-rate must be > 0")
    current_a = orbit_load_w / bus_voltage
    c_rate = current_a / installed_capacity_ah
    return {
        "current_A": current_a,
        "c_rate": c_rate,
        "within_limit": c_rate <= cell_max_c_rate,
    }


def battery_mass_kg(required_capacity_wh, spec_energy_wh_kg=SPEC_ENERGY_WH_KG):
    """Estimate the pack mass from the required capacity and specific energy.

    m = required_capacity_wh / spec_energy_wh_kg.

    Args:
        required_capacity_wh: required capacity (Wh), must be >= 0.
        spec_energy_wh_kg: pack specific energy (Wh/kg), must be > 0;
            defaults to the module constant SPEC_ENERGY_WH_KG.

    Returns:
        Pack mass in kg (float).
    """
    if required_capacity_wh < 0.0:
        raise ValueError("required capacity must be >= 0 Wh")
    if spec_energy_wh_kg <= 0.0:
        raise ValueError("specific energy must be > 0 Wh/kg")
    return required_capacity_wh / spec_energy_wh_kg


def size_battery(eclipse_load_w, eclipse_duration_s, dod_limit, bus_voltage,
                 cell_voltage=CELL_VOLTAGE, cell_ah=CELL_AMPHOUR,
                 cell_max_c_rate=1.0):
    """Run the full battery sizing chain and return the summary dict.

    Chains eclipse_energy_wh, required_capacity_wh, capacity_ah,
    cell_layout, discharge_rate_check and battery_mass_kg. A zero eclipse
    load gives a zero required capacity and is rejected by cell_layout
    (ValueError propagates, as for every non-physical input).

    Args:
        eclipse_load_w: eclipse power draw (W), must be > 0.
        eclipse_duration_s: eclipse duration (s), must be > 0.
        dod_limit: depth of discharge limit (fraction), must be in (0, 1].
        bus_voltage: regulated bus voltage (V), must be > 0.
        cell_voltage: nominal cell voltage (V), default CELL_VOLTAGE.
        cell_ah: nominal cell capacity (Ah), default CELL_AMPHOUR.
        cell_max_c_rate: cell maximum C-rate, default 1.0.

    Returns:
        Dict with eclipse_energy_wh, required_capacity_wh, capacity_ah,
        n_series, n_parallel, total_cells, mass_kg and discharge_verdict
        ("within-cell-limit" or "exceeds-cell-limit").
    """
    eclipse_energy = eclipse_energy_wh(eclipse_load_w, eclipse_duration_s)
    required_capacity = required_capacity_wh(eclipse_energy, dod_limit)
    amp_hours = capacity_ah(required_capacity, bus_voltage)
    layout = cell_layout(required_capacity, bus_voltage, cell_voltage, cell_ah)
    rate = discharge_rate_check(eclipse_load_w, bus_voltage,
                                layout["installed_capacity_ah"],
                                cell_max_c_rate)
    verdict = "within-cell-limit" if rate["within_limit"] \
        else "exceeds-cell-limit"
    return {
        "eclipse_energy_wh": eclipse_energy,
        "required_capacity_wh": required_capacity,
        "capacity_ah": amp_hours,
        "n_series": layout["n_series"],
        "n_parallel": layout["n_parallel"],
        "total_cells": layout["total_cells"],
        "mass_kg": battery_mass_kg(required_capacity),
        "discharge_verdict": verdict,
    }

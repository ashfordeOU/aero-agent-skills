"""Traction battery pack sizing for electric aircraft and eVTOL (pure stdlib).

Converts a mission energy draw into the required pack energy through the
depth of discharge and the discharge efficiency, adds the reserve, lays
out the series and parallel cell arrangement for the target pack
voltage, checks the discharge C-rate against the cell capability,
verifies the minimum cell voltage under load against the cutoff with
the cell internal resistance, and estimates the pack mass and volume
from typical cell and pack energy densities. All values are typical
documented constants (NMC lithium-ion chemistry); actual cells vary.

Vehicle level, electric propulsion battery storage only. This module
does not size liquid fuel tanks, spacecraft power systems, or the
battery thermal management hardware; thermal_estimate is limited to the
discharge-loss heat check.
"""

import math

# Typical documented constants (NMC lithium-ion, cell and pack level).
DOD_MAX = 0.80
EFF_DISCHARGE = 0.95
CELL_GRAV_WH_KG = 250.0
PACK_GRAV_WH_KG = 180.0
CELL_VOL_WH_L = 550.0
PACK_VOL_WH_L = 300.0
THERMAL_LOSS_FRACTION = 0.05

_CELL_KEYS = ("voltage_nom_v", "capacity_ah", "r_internal_ohm",
              "v_cutoff_min_v", "max_c_rate")


def _validate_cell(cell):
    """Reject missing keys, unknown keys, and non-positive cell values."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a dict with the five required keys")
    missing = [k for k in _CELL_KEYS if k not in cell]
    if missing:
        raise ValueError("cell missing required keys: " + ", ".join(missing))
    unknown = [k for k in cell if k not in _CELL_KEYS]
    if unknown:
        raise ValueError("unknown cell keys: " + ", ".join(unknown))
    for key in _CELL_KEYS:
        value = cell[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("cell %s must be numeric, got %r" % (key, value))
        if value <= 0:
            raise ValueError("cell %s must be positive, got %r" % (key, value))


def _positive(value, name):
    """Require a strictly positive numeric input."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _positive_int(value, name):
    """Require a strictly positive integer input (cell count)."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))


def required_pack_energy(mission_energy_kwh, reserve_fraction):
    """Required pack energy from mission draw, reserve, DoD, efficiency.

    E_pack_req = mission * (1 + reserve) / (DOD_MAX * EFF_DISCHARGE).
    ValueError on non-positive mission energy and negative reserve.
    """
    _positive(mission_energy_kwh, "mission_energy_kwh")
    if not isinstance(reserve_fraction, (int, float)) or isinstance(reserve_fraction, bool):
        raise ValueError("reserve_fraction must be numeric, got %r" % (reserve_fraction,))
    if reserve_fraction < 0:
        raise ValueError("reserve_fraction must not be negative, got %r" % (reserve_fraction,))
    return mission_energy_kwh * (1.0 + reserve_fraction) / (DOD_MAX * EFF_DISCHARGE)


def series_cells(target_voltage_v, cell):
    """Series cell count rounding target voltage over nominal cell voltage.

    Half rounds up; ValueError on non-positive target voltage or cell.
    """
    _positive(target_voltage_v, "target_voltage_v")
    _validate_cell(cell)
    ratio = target_voltage_v / cell["voltage_nom_v"]
    return int(math.floor(ratio + 0.5))


def parallel_cells(e_pack_req_kwh, n_series, cell):
    """Parallel cell count ceiling the energy per series string.

    n_parallel = ceil(E_pack_req * 1000 / (n_series * v_nom * cap_ah)).
    """
    _positive(e_pack_req_kwh, "e_pack_req_kwh")
    _positive_int(n_series, "n_series")
    _validate_cell(cell)
    per_string_wh = n_series * cell["voltage_nom_v"] * cell["capacity_ah"]
    return int(math.ceil(e_pack_req_kwh * 1000.0 / per_string_wh))


def pack_energy_kwh(n_series, n_parallel, cell):
    """Installed pack energy from the series and parallel cell counts."""
    _positive_int(n_series, "n_series")
    _positive_int(n_parallel, "n_parallel")
    _validate_cell(cell)
    return (n_series * n_parallel * cell["voltage_nom_v"]
            * cell["capacity_ah"] / 1000.0)


def energy_margin(pack_kwh, mission_energy_kwh, reserve_fraction):
    """Usable and required energy with the pass verdict on the margin."""
    _positive(pack_kwh, "pack_kwh")
    _positive(mission_energy_kwh, "mission_energy_kwh")
    if not isinstance(reserve_fraction, (int, float)) or isinstance(reserve_fraction, bool):
        raise ValueError("reserve_fraction must be numeric, got %r" % (reserve_fraction,))
    if reserve_fraction < 0:
        raise ValueError("reserve_fraction must not be negative, got %r" % (reserve_fraction,))
    usable_kwh = pack_kwh * DOD_MAX * EFF_DISCHARGE
    required_kwh = mission_energy_kwh * (1.0 + reserve_fraction)
    return {
        "usable_kwh": usable_kwh,
        "required_kwh": required_kwh,
        "margin_kwh": usable_kwh - required_kwh,
        "pass": usable_kwh >= required_kwh,
    }


def c_rate_check(max_power_kw, pack_kwh, cell):
    """Discharge C-rate against the cell max C-rate limit."""
    _positive(max_power_kw, "max_power_kw")
    _positive(pack_kwh, "pack_kwh")
    _validate_cell(cell)
    c_rate = max_power_kw / pack_kwh
    limit = cell["max_c_rate"]
    return {"c_rate": c_rate, "limit": limit, "pass": c_rate <= limit}


def voltage_drop_check(max_power_kw, n_series, n_parallel, cell, nominal_pack_v):
    """Minimum cell voltage under the peak load against the cutoff.

    i_total = P / V_pack; i_branch = i_total / n_parallel;
    drop = i_branch * r_internal; v_min = v_nom - drop.
    """
    _positive(max_power_kw, "max_power_kw")
    _positive_int(n_series, "n_series")
    _positive_int(n_parallel, "n_parallel")
    _validate_cell(cell)
    _positive(nominal_pack_v, "nominal_pack_v")
    i_total_a = max_power_kw * 1000.0 / nominal_pack_v
    i_branch_a = i_total_a / n_parallel
    drop_v = i_branch_a * cell["r_internal_ohm"]
    v_min_cell_v = cell["voltage_nom_v"] - drop_v
    return {
        "i_total_a": i_total_a,
        "i_branch_a": i_branch_a,
        "drop_v": drop_v,
        "v_min_cell_v": v_min_cell_v,
        "pass": v_min_cell_v >= cell["v_cutoff_min_v"],
    }


def mass_estimate(pack_kwh):
    """Cell and pack level mass from the gravimetric energy densities."""
    _positive(pack_kwh, "pack_kwh")
    return {
        "cell_mass_kg": pack_kwh * 1000.0 / CELL_GRAV_WH_KG,
        "pack_mass_kg": pack_kwh * 1000.0 / PACK_GRAV_WH_KG,
    }


def volume_estimate(pack_kwh):
    """Cell and pack level volume from the volumetric energy densities."""
    _positive(pack_kwh, "pack_kwh")
    return {
        "cell_volume_L": pack_kwh * 1000.0 / CELL_VOL_WH_L,
        "pack_volume_L": pack_kwh * 1000.0 / PACK_VOL_WH_L,
    }


def thermal_estimate(max_power_kw, duration_h):
    """Discharge-loss heat estimate (simple check, no thermal design).

    heat_kwh = THERMAL_LOSS_FRACTION * max_power_kw * duration_h.
    """
    _positive(max_power_kw, "max_power_kw")
    if not isinstance(duration_h, (int, float)) or isinstance(duration_h, bool):
        raise ValueError("duration_h must be numeric, got %r" % (duration_h,))
    if duration_h < 0:
        raise ValueError("duration_h must not be negative, got %r" % (duration_h,))
    return THERMAL_LOSS_FRACTION * max_power_kw * duration_h


def size_battery(mission_energy_kwh, reserve_fraction, max_power_kw,
                 target_voltage_v, cell):
    """Full battery pack sizing with the overall pass verdict.

    Returns the required pack energy, series and parallel cell counts,
    installed pack energy, nominal pack voltage, the energy margin,
    C-rate and voltage drop check dicts, mass and volume estimates, and
    the verdict {pass, reasons}. Overall FAIL when any of the three
    checks fails, with the failing reasons listed.
    """
    _positive(mission_energy_kwh, "mission_energy_kwh")
    _positive(max_power_kw, "max_power_kw")
    _positive(target_voltage_v, "target_voltage_v")
    if not isinstance(reserve_fraction, (int, float)) or isinstance(reserve_fraction, bool):
        raise ValueError("reserve_fraction must be numeric, got %r" % (reserve_fraction,))
    if reserve_fraction < 0:
        raise ValueError("reserve_fraction must not be negative, got %r" % (reserve_fraction,))
    _validate_cell(cell)

    e_pack_req_kwh = required_pack_energy(mission_energy_kwh, reserve_fraction)
    n_series = series_cells(target_voltage_v, cell)
    n_parallel = parallel_cells(e_pack_req_kwh, n_series, cell)
    pack_kwh = pack_energy_kwh(n_series, n_parallel, cell)
    nominal_pack_v = n_series * cell["voltage_nom_v"]

    energy = energy_margin(pack_kwh, mission_energy_kwh, reserve_fraction)
    c_rate = c_rate_check(max_power_kw, pack_kwh, cell)
    voltage = voltage_drop_check(max_power_kw, n_series, n_parallel, cell,
                                 nominal_pack_v)

    reasons = []
    if not energy["pass"]:
        reasons.append("usable energy %.2f kWh below the required %.2f kWh"
                       % (energy["usable_kwh"], energy["required_kwh"]))
    if not c_rate["pass"]:
        reasons.append("C-rate %.2f exceeds the cell limit of %.1f C"
                       % (c_rate["c_rate"], c_rate["limit"]))
    if not voltage["pass"]:
        reasons.append("minimum cell voltage %.2f V below the %.2f V cutoff"
                       % (voltage["v_min_cell_v"], cell["v_cutoff_min_v"]))

    return {
        "e_pack_req_kwh": e_pack_req_kwh,
        "n_series": n_series,
        "n_parallel": n_parallel,
        "nominal_pack_v": nominal_pack_v,
        "pack_energy_kwh": pack_kwh,
        "energy": energy,
        "c_rate": c_rate,
        "voltage_drop": voltage,
        "mass": mass_estimate(pack_kwh),
        "volume": volume_estimate(pack_kwh),
        "verdict": {"pass": not reasons, "reasons": reasons},
    }

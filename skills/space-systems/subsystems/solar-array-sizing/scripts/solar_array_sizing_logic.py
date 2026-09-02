"""Solar array sizing logic (space-systems/subsystems/solar-array-sizing).

Deterministic, stdlib-only. Every function validates its inputs and raises
ValueError with a clear message. Docstrings carry worked anchor examples
verified by scripts/test_solar_array_sizing.py.

Model (ECSS-E-ST-20C style photovoltaic sizing):
  - The array generates only in daylight: over one orbit the daylight
    energy must cover the orbit-average demand, so the required daylight
    power is P_day = P_demand / (1 - f_eclipse), scaled by the array margin.
  - End-of-life degradation: D = (1 - r_annual) ** mission_years.
  - End-of-life specific power (W/m2): p_eol = G * eta * PF * D, where G is
    the solar irradiance (W/m2), eta the cell efficiency, PF the packing
    factor (panel area fraction covered by cells).
  - Required array area: A = P_day / p_eol.
"""


def _check_power_demand(power_demand_w):
    if not isinstance(power_demand_w, (int, float)):
        raise ValueError("power_demand_w must be a number, got %r" % (power_demand_w,))
    if power_demand_w <= 0:
        raise ValueError("power_demand_w must be > 0 W, got %r" % (power_demand_w,))


def _check_eclipse_fraction(eclipse_fraction):
    if not isinstance(eclipse_fraction, (int, float)):
        raise ValueError("eclipse_fraction must be a number, got %r" % (eclipse_fraction,))
    if eclipse_fraction < 0 or eclipse_fraction >= 1:
        raise ValueError(
            "eclipse_fraction must be in [0, 1), got %r (an eclipse fraction of 1 "
            "means permanent eclipse and no array power at all)" % (eclipse_fraction,)
        )


def _check_margin(array_margin):
    if not isinstance(array_margin, (int, float)):
        raise ValueError("array_margin must be a number, got %r" % (array_margin,))
    if array_margin < 0:
        raise ValueError("array_margin must be >= 0, got %r" % (array_margin,))


def _check_degradation(annual_degradation):
    if not isinstance(annual_degradation, (int, float)):
        raise ValueError(
            "annual_degradation must be a number, got %r" % (annual_degradation,)
        )
    if annual_degradation < 0 or annual_degradation >= 1:
        raise ValueError(
            "annual_degradation must be in [0, 1) per year, got %r" % (annual_degradation,)
        )


def _check_mission_years(mission_years):
    if not isinstance(mission_years, (int, float)):
        raise ValueError("mission_years must be a number, got %r" % (mission_years,))
    if mission_years < 0:
        raise ValueError("mission_years must be >= 0, got %r" % (mission_years,))


def _check_irradiance(solar_irradiance):
    if not isinstance(solar_irradiance, (int, float)):
        raise ValueError("solar_irradiance must be a number, got %r" % (solar_irradiance,))
    if solar_irradiance <= 0:
        raise ValueError("solar_irradiance must be > 0 W/m2, got %r" % (solar_irradiance,))


def _check_efficiency(cell_efficiency):
    if not isinstance(cell_efficiency, (int, float)):
        raise ValueError("cell_efficiency must be a number, got %r" % (cell_efficiency,))
    if cell_efficiency <= 0 or cell_efficiency > 1:
        raise ValueError(
            "cell_efficiency must be in (0, 1], got %r (fraction, not percent)" % (cell_efficiency,)
        )


def _check_packing_factor(packing_factor):
    if not isinstance(packing_factor, (int, float)):
        raise ValueError("packing_factor must be a number, got %r" % (packing_factor,))
    if packing_factor <= 0 or packing_factor > 1:
        raise ValueError(
            "packing_factor must be in (0, 1], got %r (fraction of panel covered by cells)" % (packing_factor,)
        )


def _check_array_area(array_area):
    if not isinstance(array_area, (int, float)):
        raise ValueError("array_area must be a number, got %r" % (array_area,))
    if array_area <= 0:
        raise ValueError("array_area must be > 0 m2, got %r" % (array_area,))


def daylight_power(power_demand_w, eclipse_fraction, array_margin=0.0):
    """Daylight power the array must deliver to meet an orbit-average demand.

    The array only generates outside eclipse, so the daylight power must
    exceed the orbit-average demand by 1 / (1 - f). Optionally scaled by
    (1 + array_margin) for a sizing margin.

    Anchor: P_demand = 500 W, f = 0.35 -> P_day = 500 / 0.65 = 769.2308 W.
    With margin 0.20 -> 923.0769 W.
    """
    _check_power_demand(power_demand_w)
    _check_eclipse_fraction(eclipse_fraction)
    _check_margin(array_margin)
    return power_demand_w / (1.0 - eclipse_fraction) * (1.0 + array_margin)


def degradation_factor(annual_degradation, mission_years):
    """End-of-life degradation factor D = (1 - r) ** n (compound annual loss).

    Anchor: r = 0.02/year, n = 10 years -> 0.98 ** 10 = 0.8170728068875467.
    """
    _check_degradation(annual_degradation)
    _check_mission_years(mission_years)
    return (1.0 - annual_degradation) ** mission_years


def eol_specific_power(
    solar_irradiance,
    cell_efficiency,
    packing_factor,
    annual_degradation,
    mission_years,
):
    """End-of-life power per square meter of panel, p_eol = G * eta * PF * D.

    Anchor: G = 1367 W/m2, eta = 0.30, PF = 0.85, r = 0.02, n = 10 ->
    p_eol = 1367 * 0.30 * 0.85 * 0.8170728068875467 = 284.8193 W/m2.
    """
    _check_irradiance(solar_irradiance)
    _check_efficiency(cell_efficiency)
    _check_packing_factor(packing_factor)
    return (
        solar_irradiance
        * cell_efficiency
        * packing_factor
        * degradation_factor(annual_degradation, mission_years)
    )


def required_array_area(
    power_demand_w,
    eclipse_fraction,
    solar_irradiance,
    cell_efficiency,
    packing_factor,
    annual_degradation,
    mission_years,
    array_margin=0.0,
):
    """Required photovoltaic array area (m2) = P_day / p_eol.

    Anchor: P_demand = 500 W, f = 0.35, G = 1367 W/m2, eta = 0.30,
    PF = 0.85, r = 0.02, n = 10, margin = 0.20 ->
    A = 923.0769 / 284.8193 = 3.2409 m2.
    """
    p_day = daylight_power(power_demand_w, eclipse_fraction, array_margin)
    p_eol = eol_specific_power(
        solar_irradiance,
        cell_efficiency,
        packing_factor,
        annual_degradation,
        mission_years,
    )
    return p_day / p_eol


def array_power_available(
    array_area,
    solar_irradiance,
    cell_efficiency,
    packing_factor,
    annual_degradation,
    mission_years,
):
    """End-of-life daylight power (W) a panel of given area can deliver.

    Inverse of required_array_area: A * G * eta * PF * D.

    Anchor: A = 3.2409 m2, G = 1367 W/m2, eta = 0.30, PF = 0.85,
    r = 0.02, n = 10 -> 3.2409 * 284.8193 = 923.08 W (the sized daylight
    demand with margin 0.20 on a 500 W bus).
    """
    _check_array_area(array_area)
    return (
        array_area
        * eol_specific_power(
            solar_irradiance,
            cell_efficiency,
            packing_factor,
            annual_degradation,
            mission_years,
        )
    )


def power_margin(
    array_area,
    power_demand_w,
    eclipse_fraction,
    solar_irradiance,
    cell_efficiency,
    packing_factor,
    annual_degradation,
    mission_years,
):
    """Array power margin = available / required - 1.

    Positive margin means the array still meets the daylight demand at end
    of life. Anchor: sizing with margin 0.20 gives margin ~ 0.20 when the
    same parameters are fed back through this function.
    """
    available = array_power_available(
        array_area,
        solar_irradiance,
        cell_efficiency,
        packing_factor,
        annual_degradation,
        mission_years,
    )
    required = daylight_power(power_demand_w, eclipse_fraction, 0.0)
    return available / required - 1.0

"""Subsonic intake total-pressure recovery logic for a gas turbine.

Pure stdlib, deterministic, offline. Implements the subsonic-inlet-
recovery leaf (propulsion/gas-turbine-cycle):

- ram recovery ratio from the free-stream Mach number: unity at and
  below Mach 1, with a MIL-E-5008B style roll-off
  1 - 0.075 * (M - 1)^1.35 above Mach 1,
- free-stream stagnation pressure ratio from the isentropic relation
  (1 + 0.2 M^2)^3.5 at gamma = 1.4,
- total pressure delivered at the engine face: free-stream static
  pressure times the stagnation ratio, the ram recovery and the duct
  total-pressure efficiency,
- required capture area for the engine mass flow at the flight speed
  and density: A = m_dot / (rho * V) with rho = p0 / (R T0) and
  V = M * sqrt(gamma R T0),
- capture verdict against the intake highlight area: full-capture when
  the required capture area fits inside the highlight, else spillage.

All inputs SI: p in Pa, T in K, mass flow in kg/s, area in m2, speed in
m/s. Non-physical inputs raise ValueError.
"""

import math

# Module constants (air-breathing propulsion convention).
GAMMA = 1.4
R_AIR = 287.0
RECOVERY_ROLLOFF = 0.075
RECOVERY_EXPONENT = 1.35

# Supersonic roll-off bound: above this Mach the subsonic-intake
# recovery model no longer applies (ramjet-inlet handles that regime).
MACH_MAX = 5.0


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %s" % (name, value))


def ram_recovery(mach):
    """Return the intake total-pressure recovery ratio at mach.

    Unity for mach <= 1.0; above Mach 1 a MIL-E-5008B style roll-off
    1 - RECOVERY_ROLLOFF * (mach - 1.0) ** RECOVERY_EXPONENT applies up
    to mach < 5.0. Raises ValueError for negative mach or mach >= 5.0
    (the supersonic shock-recovery regime belongs to ramjet-inlet).
    """
    if mach < 0:
        raise ValueError("mach must be non-negative, got %s" % mach)
    if mach >= MACH_MAX:
        raise ValueError(
            "mach must be below %s for the subsonic intake model, got %s"
            % (MACH_MAX, mach)
        )
    if mach <= 1.0:
        return 1.0
    return 1.0 - RECOVERY_ROLLOFF * (mach - 1.0) ** RECOVERY_EXPONENT


def stagnation_pressure_ratio(mach):
    """Return the free-stream stagnation pressure ratio at mach.

    p0 / p = (1 + 0.2 * mach**2) ** 3.5 from the isentropic relation at
    gamma = 1.4. Valid for any mach the caller feeds (negative mach
    yields unity and is non-physical, so it raises ValueError).
    """
    if mach < 0:
        raise ValueError("mach must be non-negative, got %s" % mach)
    return (1.0 + 0.2 * mach ** 2) ** 3.5


def face_total_pressure(p0, mach, duct_efficiency):
    """Return the engine-face total pressure Pa delivered by the intake.

    p0 * stagnation_pressure_ratio(mach) * ram_recovery(mach) *
    duct_efficiency, the free-stream static pressure promoted by the
    isentropic stagnation ratio, cut by the ram recovery (unity at
    subsonic mach) and the duct total-pressure efficiency. Raises
    ValueError for p0 <= 0, mach outside the model domain or a duct
    efficiency outside (0, 1].
    """
    _check_positive(p0, "p0")
    if duct_efficiency <= 0 or duct_efficiency > 1.0:
        raise ValueError(
            "duct_efficiency must be in (0, 1], got %s" % duct_efficiency
        )
    recovery = ram_recovery(mach)
    return (
        p0
        * stagnation_pressure_ratio(mach)
        * recovery
        * duct_efficiency
    )


def capture_area(mass_flow, p0, T0, mach):
    """Return the required intake capture area m2 for the engine flow.

    The streamtube area that passes mass_flow at the free-stream speed:
    rho = p0 / (R_AIR * T0), V = mach * sqrt(GAMMA * R_AIR * T0) and
    A = mass_flow / (rho * V). Raises ValueError for mass_flow <= 0,
    p0 <= 0, T0 <= 0 or mach <= 0 (no capture streamtube exists at rest).
    """
    _check_positive(mass_flow, "mass_flow")
    _check_positive(p0, "p0")
    _check_positive(T0, "T0")
    if mach <= 0:
        raise ValueError("mach must be positive, got %s" % mach)
    rho = p0 / (R_AIR * T0)
    speed = mach * math.sqrt(GAMMA * R_AIR * T0)
    return mass_flow / (rho * speed)


def capture_verdict(capture_area_m2, highlight_area_m2):
    """Return the capture verdict string against the highlight area.

    "full-capture" when the required capture area fits at or inside the
    intake highlight area, else "spillage". Raises ValueError for a
    non-positive capture area or highlight area.
    """
    _check_positive(capture_area_m2, "capture_area_m2")
    _check_positive(highlight_area_m2, "highlight_area_m2")
    if capture_area_m2 <= highlight_area_m2:
        return "full-capture"
    return "spillage"

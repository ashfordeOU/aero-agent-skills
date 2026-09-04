"""Ram air turbine (RAT) conceptual sizing logic, pure stdlib.

Sizes the emergency ram air turbine rotor at the conceptual level from the
required emergency power at a fixed emergency airspeed. The model is the
wind-power relation P = 0.5 * rho * V^3 * A * Cp with a fixed design overall
power coefficient that absorbs efficiency and losses.

Conventions: required power in W, airspeed in m/s at the fixed emergency
condition, density in kg/m3 defaulting to ISA sea level.

No numpy, no network, no randomness: deterministic by construction.
"""

import math

# ISA sea level air density, kg/m3.
RHO_SL_DEFAULT = 1.225

# Overall ram air turbine power coefficient including efficiency and
# losses; the fixed design value for sizing.
CP_RAT_DEFAULT = 0.10

# Ideal actuator-disk upper bound on the power coefficient (Betz limit).
BETZ_LIMIT = 16.0 / 27.0

PI = math.pi


def _validate_airspeed_terms(v_m_s, rho, cp):
    """Reject non-physical airspeed, density and coefficient inputs."""
    if v_m_s <= 0:
        raise ValueError("airspeed must be positive, got %r m/s" % v_m_s)
    if rho <= 0:
        raise ValueError("density must be positive, got %r kg/m3" % rho)
    if cp <= 0:
        raise ValueError("power coefficient must be positive, got %r" % cp)
    if cp >= BETZ_LIMIT:
        raise ValueError(
            "power coefficient %r must stay below the Betz bound %r"
            % (cp, BETZ_LIMIT)
        )


def _validate_power_terms(p_req_w, v_m_s, rho, cp):
    """Reject non-physical sizing inputs with ValueError."""
    if p_req_w <= 0:
        raise ValueError("required power must be positive, got %r W" % p_req_w)
    _validate_airspeed_terms(v_m_s, rho, cp)


def rat_swept_area(p_req_w, v_m_s, rho=RHO_SL_DEFAULT, cp=CP_RAT_DEFAULT):
    """Required rotor swept area in m2: p / (0.5 * rho * v^3 * cp)."""
    _validate_power_terms(p_req_w, v_m_s, rho, cp)
    return p_req_w / (0.5 * rho * v_m_s ** 3 * cp)


def disk_diameter(area_m2):
    """Rotor disk diameter in m from the swept area: sqrt(4*A/pi)."""
    if area_m2 <= 0:
        raise ValueError("swept area must be positive, got %r m2" % area_m2)
    return math.sqrt(4.0 * area_m2 / PI)


def rat_available_power(area_m2, v_m_s, rho=RHO_SL_DEFAULT, cp=CP_RAT_DEFAULT):
    """Available wind power in W through the swept area: 0.5*rho*v^3*A*cp."""
    if area_m2 <= 0:
        raise ValueError("swept area must be positive, got %r m2" % area_m2)
    _validate_airspeed_terms(v_m_s, rho, cp)
    return 0.5 * rho * v_m_s ** 3 * area_m2 * cp


def rat_sizing_summary(
    p_req_w,
    v_m_s,
    max_stowage_diameter_m,
    rho=RHO_SL_DEFAULT,
    cp=CP_RAT_DEFAULT,
):
    """Full sizing summary dict for the fixed emergency condition.

    Returns {area_m2, diameter_m, available_w, margin_w, stowage_verdict}
    where margin_w = available_w - p_req_w and stowage_verdict is PASS when
    the disk diameter fits within the stowage diameter limit, else FAIL.
    """
    if max_stowage_diameter_m <= 0:
        raise ValueError(
            "max stowage diameter must be positive, got %r m"
            % max_stowage_diameter_m
        )
    area_m2 = rat_swept_area(p_req_w, v_m_s, rho, cp)
    diameter_m = disk_diameter(area_m2)
    available_w = rat_available_power(area_m2, v_m_s, rho, cp)
    margin_w = available_w - p_req_w
    stowage_verdict = "PASS" if diameter_m <= max_stowage_diameter_m else "FAIL"
    return {
        "area_m2": area_m2,
        "diameter_m": diameter_m,
        "available_w": available_w,
        "margin_w": margin_w,
        "stowage_verdict": stowage_verdict,
    }

"""Fuel feed system sizing logic (pure stdlib).

Sizes the aircraft fuel feed system between the tank outlet and the
engine-driven fuel pump inlet at the conceptual level: feed line
velocity and Reynolds number, major and minor line pressure loss from
the Darcy friction factor, static head gain, net positive suction head
available (NPSHa) against the pump required NPSH, and boost pump
hydraulic power. SI units throughout. Non-physical inputs raise
ValueError.
"""

import math

# Module constants
GRAVITY = 9.80665          # m/s^2, standard gravity
LAMINAR_RE_LIMIT = 2300.0  # laminar to turbulent transition Reynolds number
BLASIUS_COEFF = 0.3164     # turbulent friction factor coefficient
K_LAMINAR = 64.0           # laminar friction factor constant, f = 64/Re
PSI_TO_PA = 6894.757       # pounds per square inch to pascals


def line_velocity(mass_flow_kg_s, density_kg_m3, diameter_m):
    """Feed line mean velocity from mass flow, density and diameter.

    Returns {velocity_m_s, area_m2} with A = pi D^2 / 4 and
    V = m_dot / (rho * A).
    """
    if mass_flow_kg_s <= 0:
        raise ValueError("mass flow must be positive")
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    if diameter_m <= 0:
        raise ValueError("diameter must be positive")
    area_m2 = math.pi * diameter_m ** 2 / 4.0
    velocity_m_s = mass_flow_kg_s / (density_kg_m3 * area_m2)
    return {"velocity_m_s": velocity_m_s, "area_m2": area_m2}


def reynolds_number(velocity_m_s, diameter_m, density_kg_m3, viscosity_pa_s):
    """Reynolds number Re = V D rho / mu."""
    if velocity_m_s < 0:
        raise ValueError("velocity must not be negative")
    if diameter_m <= 0:
        raise ValueError("diameter must be positive")
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    if viscosity_pa_s <= 0:
        raise ValueError("viscosity must be positive")
    return velocity_m_s * diameter_m * density_kg_m3 / viscosity_pa_s


def friction_factor(reynolds):
    """Darcy friction factor: 64/Re laminar, Blasius turbulent."""
    if reynolds <= 0:
        raise ValueError("Reynolds number must be positive")
    if reynolds < LAMINAR_RE_LIMIT:
        return K_LAMINAR / reynolds
    return BLASIUS_COEFF * reynolds ** -0.25


def major_loss_pa(friction, length_m, diameter_m, density_kg_m3, velocity_m_s):
    """Major (friction) line loss f (L/D) rho V^2 / 2 in pascals."""
    if friction <= 0:
        raise ValueError("friction factor must be positive")
    if length_m <= 0:
        raise ValueError("length must be positive")
    if diameter_m <= 0:
        raise ValueError("diameter must be positive")
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    if velocity_m_s <= 0:
        raise ValueError("velocity must be positive")
    return friction * (length_m / diameter_m) * density_kg_m3 * velocity_m_s ** 2 / 2.0


def minor_loss_pa(loss_coefficient_k, density_kg_m3, velocity_m_s):
    """Minor loss K rho V^2 / 2 in pascals from the fitting loss sum K."""
    if loss_coefficient_k < 0:
        raise ValueError("loss coefficient must not be negative")
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    if velocity_m_s < 0:
        raise ValueError("velocity must not be negative")
    return loss_coefficient_k * density_kg_m3 * velocity_m_s ** 2 / 2.0


def static_head_pa(density_kg_m3, height_m):
    """Static head pressure rho g h in pascals.

    height_m is the tank outlet height above the pump inlet; a pump
    above the tank gives a negative height and a head loss.
    """
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    return density_kg_m3 * GRAVITY * height_m


def npsh_available(source_pressure_pa, static_head_pa, line_loss_pa,
                   vapor_pressure_pa, density_kg_m3):
    """Net positive suction head available in metres of fuel column.

    NPSHa = (p_source + p_static - p_line - p_vapor) / (rho g). The
    signed value is returned; a negative result means the pump inlet
    cannot be fed and callers treat it as FAIL.
    """
    if source_pressure_pa < 0:
        raise ValueError("source pressure must not be negative")
    if line_loss_pa < 0:
        raise ValueError("line loss must not be negative")
    if vapor_pressure_pa < 0:
        raise ValueError("vapor pressure must not be negative")
    if density_kg_m3 <= 0:
        raise ValueError("density must be positive")
    numerator = (source_pressure_pa + static_head_pa - line_loss_pa
                 - vapor_pressure_pa)
    return numerator / (density_kg_m3 * GRAVITY)


def feed_verdict(npsh_available_m, npsh_required_m):
    """Feed PASS/FAIL verdict from NPSH available against required.

    Returns {margin_m, verdict}; PASS when available >= required.
    """
    if npsh_required_m < 0:
        raise ValueError("required NPSH must not be negative")
    margin_m = npsh_available_m - npsh_required_m
    verdict = "PASS" if margin_m >= 0.0 else "FAIL"
    return {"margin_m": margin_m, "verdict": verdict}


def boost_pump_power(flow_m3_s, pressure_rise_pa, efficiency):
    """Boost pump hydraulic power P = Q dp / eta.

    Returns {power_w, pressure_rise_pa} with the rise echoed for
    convenience.
    """
    if flow_m3_s <= 0:
        raise ValueError("flow must be positive")
    if pressure_rise_pa <= 0:
        raise ValueError("pressure rise must be positive")
    if efficiency <= 0 or efficiency > 1.0:
        raise ValueError("efficiency must be in (0, 1]")
    power_w = flow_m3_s * pressure_rise_pa / efficiency
    return {"power_w": power_w, "pressure_rise_pa": pressure_rise_pa}


def feed_system_summary(mass_flow_kg_s, density_kg_m3, diameter_m, length_m,
                        viscosity_pa_s, loss_coefficient_k, tank_height_m,
                        source_pressure_pa, vapor_pressure_pa,
                        npsh_required_m, boost_pressure_rise_pa,
                        boost_efficiency):
    """Full fuel feed system sizing in one dict.

    Chains every stage from the feed flow to the boost pump. A zero
    boost pressure rise means no boost pump: npsh_with_boost_m equals
    npsh_available_m and boost_power_w is 0.0.
    """
    vel = line_velocity(mass_flow_kg_s, density_kg_m3, diameter_m)
    velocity_m_s = vel["velocity_m_s"]
    area_m2 = vel["area_m2"]
    reynolds = reynolds_number(velocity_m_s, diameter_m, density_kg_m3,
                               viscosity_pa_s)
    friction = friction_factor(reynolds)
    major = major_loss_pa(friction, length_m, diameter_m, density_kg_m3,
                          velocity_m_s)
    minor = minor_loss_pa(loss_coefficient_k, density_kg_m3, velocity_m_s)
    total_line_loss_pa = major + minor
    static = static_head_pa(density_kg_m3, tank_height_m)
    npsh = npsh_available(source_pressure_pa, static, total_line_loss_pa,
                          vapor_pressure_pa, density_kg_m3)
    verdict = feed_verdict(npsh, npsh_required_m)
    flow_m3_s = mass_flow_kg_s / density_kg_m3
    if boost_pressure_rise_pa > 0:
        boost = boost_pump_power(flow_m3_s, boost_pressure_rise_pa,
                                 boost_efficiency)
        boost_power_w = boost["power_w"]
        npsh_with_boost_m = npsh_available(
            source_pressure_pa + boost_pressure_rise_pa, static,
            total_line_loss_pa, vapor_pressure_pa, density_kg_m3)
    elif boost_pressure_rise_pa == 0:
        boost_power_w = 0.0
        npsh_with_boost_m = npsh
    else:
        raise ValueError("boost pressure rise must not be negative")
    return {
        "velocity_m_s": velocity_m_s,
        "area_m2": area_m2,
        "reynolds": reynolds,
        "friction_factor": friction,
        "major_loss_pa": major,
        "minor_loss_pa": minor,
        "total_line_loss_pa": total_line_loss_pa,
        "static_head_pa": static,
        "npsh_available_m": npsh,
        "npsh_required_m": npsh_required_m,
        "margin_m": verdict["margin_m"],
        "verdict": verdict["verdict"],
        "npsh_with_boost_m": npsh_with_boost_m,
        "boost_pressure_rise_pa": boost_pressure_rise_pa,
        "boost_power_w": boost_power_w,
    }


if __name__ == "__main__":
    print("fuel_feed_system_sizing_logic import OK")

"""Rotorcraft hover-in-ground-effect (HIGE) performance logic.

Pure-stdlib model of a rotor hovering over a flat ground plane. The
classic Cheeseman-style height correction reduces the induced velocity,
and with it the induced power at constant thrust; profile power is
unchanged in ground effect. The rotor disk model here applies to a rotor
hovering over a flat ground plane only: no recirculation, no partial
ground contact, no wing-in-ground-effect aerodynamics, no climb, no
forward flight.

The ground-effect factor at rotor height z above the ground for a rotor
of radius R is k_ige = 1 - (R / (4*z))**2. The model is valid for
height/radius >= MIN_Z_RATIO (0.5); below that the rotor sits in the
ground-cushion regime where the point model diverges.

All quantities are SI (N, m, m/s, W, Pa, kg, s). Module functions raise
ValueError on non-physical inputs. No RNG, no external imports: fully
deterministic.
"""

import math

G0 = 9.80665       # standard gravity, m/s^2
RHO_SL = 1.225     # sea-level air density, kg/m^3
K_DEFAULT = 1.15   # induced power factor (same convention as the hover sibling)
PI = math.pi
MIN_Z_RATIO = 0.5  # validity floor for height / radius

# Default rotor geometry for the ceiling and convenience checks
DEFAULT_SOLIDITY = 0.08
DEFAULT_DRAG_COEFFICIENT = 0.012
DEFAULT_TIP_SPEED = 220.0


def disk_area(radius):
    """Rotor disk area A = PI * radius**2 in m^2. ValueError if radius <= 0."""
    if radius <= 0:
        raise ValueError("radius must be positive")
    return PI * radius ** 2


def hover_induced_velocity(thrust, area, rho=RHO_SL):
    """Momentum-theory ideal induced velocity v_h = sqrt(T / (2*rho*A)) in m/s.

    ValueErrors on non-positive thrust, area or density.
    """
    if thrust <= 0:
        raise ValueError("thrust must be positive")
    if area <= 0:
        raise ValueError("area must be positive")
    if rho <= 0:
        raise ValueError("rho must be positive")
    return math.sqrt(thrust / (2.0 * rho * area))


def ground_effect_factor(height, radius):
    """Cheeseman-style induced-velocity ground-effect reduction factor.

    k_ige = 1 - (radius / (4*height))**2. The factor multiplies the
    ideal induced velocity, and therefore the induced power at constant
    thrust. ValueError if radius <= 0 or height / radius < MIN_Z_RATIO.
    """
    if radius <= 0:
        raise ValueError("radius must be positive")
    if height / radius < MIN_Z_RATIO:
        raise ValueError(
            "height / radius must be >= %s for the ground-effect model"
            % MIN_Z_RATIO
        )
    return 1.0 - (radius / (4.0 * height)) ** 2


def ige_induced_power(ideal_induced_power, ground_effect_factor):
    """Induced power in ground effect P_i_ige = P_ideal * factor, in W.

    ValueError if P_ideal < 0 or factor <= 0 or factor > 1.
    """
    if ideal_induced_power < 0:
        raise ValueError("ideal induced power must be >= 0")
    if ground_effect_factor <= 0 or ground_effect_factor > 1:
        raise ValueError("ground effect factor must lie in (0, 1]")
    return ideal_induced_power * ground_effect_factor


def ige_total_power(ideal_induced_power, profile_power, ground_effect_factor,
                    k=K_DEFAULT):
    """Total hover power in ground effect, in W.

    P_total_ige = k * P_ideal * factor + profile_power, with k the
    induced power factor and profile power unchanged in ground effect.
    ValueErrors on negative powers, factor outside (0, 1] or k <= 0.
    """
    if ideal_induced_power < 0:
        raise ValueError("ideal induced power must be >= 0")
    if profile_power < 0:
        raise ValueError("profile power must be >= 0")
    if ground_effect_factor <= 0 or ground_effect_factor > 1:
        raise ValueError("ground effect factor must lie in (0, 1]")
    if k <= 0:
        raise ValueError("induced power factor k must be positive")
    return k * ideal_induced_power * ground_effect_factor + profile_power


def power_margin(available_power, required_power):
    """Hover power margin margin = available_power - required_power, in W.

    ValueError if available_power < 0 or required_power < 0.
    """
    if available_power < 0:
        raise ValueError("available power must be >= 0")
    if required_power < 0:
        raise ValueError("required power must be >= 0")
    return available_power - required_power


def oge_total_power(ideal_induced_power, profile_power, k=K_DEFAULT):
    """Out-of-ground-effect total hover power, in W.

    P_total_oge = k * P_ideal + profile_power. ValueErrors as above.
    Used to decide whether ground effect matters for a given available
    power: if available power covers the OGE total, hover is possible at
    any height.
    """
    if ideal_induced_power < 0:
        raise ValueError("ideal induced power must be >= 0")
    if profile_power < 0:
        raise ValueError("profile power must be >= 0")
    if k <= 0:
        raise ValueError("induced power factor k must be positive")
    return k * ideal_induced_power + profile_power


def _profile_power(rho, area, solidity, drag_coefficient, tip_speed):
    """Average-section profile power (1/8)*rho*sigma*Cd0*A*Vtip^3, in W.

    Internal helper shared by the ceiling and convenience functions;
    callers validate the geometry inputs first.
    """
    return (
        (1.0 / 8.0)
        * rho
        * solidity
        * drag_coefficient
        * area
        * tip_speed ** 3
    )


def max_hover_height(weight_kg, radius, available_power, rho=RHO_SL,
                     solidity=DEFAULT_SOLIDITY,
                     drag_coefficient=DEFAULT_DRAG_COEFFICIENT,
                     tip_speed=DEFAULT_TIP_SPEED, k=K_DEFAULT):
    """Largest rotor height z (m) with IGE total power <= available power.

    Returns the largest z (>= MIN_Z_RATIO * radius) at which the IGE
    total power equals the available power. If available_power >= the
    OGE total power the rotorcraft can hover at any height: returns None
    (no ground-effect-limited ceiling). Otherwise bisects z on
    [MIN_Z_RATIO * radius, 50 * radius], where the IGE total power
    increases with z and asymptotes to the OGE value, so the equation
    has exactly one root. Raises ValueError if available_power is below
    the IGE total power at the lowest valid height (hover impossible
    even in full ground effect) or on any non-physical input.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if radius <= 0:
        raise ValueError("radius must be positive")
    if available_power < 0:
        raise ValueError("available power must be >= 0")
    if rho <= 0:
        raise ValueError("rho must be positive")
    if solidity <= 0:
        raise ValueError("solidity must be positive")
    if drag_coefficient <= 0:
        raise ValueError("drag coefficient must be positive")
    if tip_speed <= 0:
        raise ValueError("tip speed must be positive")
    if k <= 0:
        raise ValueError("induced power factor k must be positive")

    thrust = weight_kg * G0
    area = disk_area(radius)
    v_h = hover_induced_velocity(thrust, area, rho)
    ideal_power = thrust * v_h
    prof_power = _profile_power(rho, area, solidity, drag_coefficient,
                                tip_speed)

    oge_total = oge_total_power(ideal_power, prof_power, k)
    if available_power >= oge_total:
        # Out of ground effect hover is possible: no ceiling at all.
        return None

    z_low = MIN_Z_RATIO * radius
    power_low = ige_total_power(ideal_power, prof_power,
                                ground_effect_factor(z_low, radius), k)
    if available_power < power_low:
        raise ValueError(
            "available power below the IGE total power at the lowest "
            "valid height; hover impossible even in full ground effect"
        )

    z_high = 50.0 * radius
    power_high = ige_total_power(ideal_power, prof_power,
                                 ground_effect_factor(z_high, radius), k)
    if available_power >= power_high:
        # Root lies above the modeled bracket: ceiling is the bracket top.
        return z_high

    lo, hi = z_low, z_high
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        power_mid = ige_total_power(
            ideal_power, prof_power, ground_effect_factor(mid, radius), k
        )
        if power_mid <= available_power:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def hover_ground_effect(weight_kg, radius, height, rho=RHO_SL,
                        solidity=DEFAULT_SOLIDITY,
                        drag_coefficient=DEFAULT_DRAG_COEFFICIENT,
                        tip_speed=DEFAULT_TIP_SPEED, k=K_DEFAULT,
                        available_power=None):
    """One-call hover-in-ground-effect check returning a result dict.

    thrust = weight_kg * G0. Returns {thrust_N, area_m2,
    hover_induced_velocity, ideal_induced_power_W, profile_power_W,
    ground_effect_factor, ige_induced_power_W, ige_total_power_W,
    oge_total_power_W, power_margin_W, max_hover_height}. power_margin_W
    and max_hover_height are None when available_power is None;
    max_hover_height is None when hover is possible at any height.
    ValueErrors propagate from the primitives.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if radius <= 0:
        raise ValueError("radius must be positive")
    if height / radius < MIN_Z_RATIO:
        raise ValueError(
            "height / radius must be >= %s for the ground-effect model"
            % MIN_Z_RATIO
        )
    if rho <= 0:
        raise ValueError("rho must be positive")
    if solidity <= 0:
        raise ValueError("solidity must be positive")
    if drag_coefficient <= 0:
        raise ValueError("drag coefficient must be positive")
    if tip_speed <= 0:
        raise ValueError("tip speed must be positive")
    if k <= 0:
        raise ValueError("induced power factor k must be positive")

    thrust = weight_kg * G0
    area = disk_area(radius)
    v_h = hover_induced_velocity(thrust, area, rho)
    ideal_power = thrust * v_h
    prof_power = _profile_power(rho, area, solidity, drag_coefficient,
                                tip_speed)
    factor = ground_effect_factor(height, radius)
    ige_induced = ige_induced_power(ideal_power, factor)
    ige_total = ige_total_power(ideal_power, prof_power, factor, k)
    oge_total = oge_total_power(ideal_power, prof_power, k)

    if available_power is not None:
        margin = power_margin(available_power, ige_total)
        ceiling = max_hover_height(weight_kg, radius, available_power, rho,
                                   solidity, drag_coefficient, tip_speed, k)
    else:
        margin = None
        ceiling = None

    return {
        "thrust_N": thrust,
        "area_m2": area,
        "hover_induced_velocity": v_h,
        "ideal_induced_power_W": ideal_power,
        "profile_power_W": prof_power,
        "ground_effect_factor": factor,
        "ige_induced_power_W": ige_induced,
        "ige_total_power_W": ige_total,
        "oge_total_power_W": oge_total,
        "power_margin_W": margin,
        "max_hover_height": ceiling,
    }

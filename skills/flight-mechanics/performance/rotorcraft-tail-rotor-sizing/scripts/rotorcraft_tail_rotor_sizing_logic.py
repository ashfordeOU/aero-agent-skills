"""Tail rotor (anti-torque rotor) sizing for a single-main-rotor rotorcraft.

Pure stdlib, deterministic. The main rotor power is an INPUT to the torque
balance: this module never computes main rotor hover power from weight and
geometry (that belongs to rotorcraft-hover-performance). It sizes the tail
rotor from the main rotor shaft torque, the anti-torque thrust over the tail
arm, disk area and radius at a maximum disk loading, momentum-theory induced
velocity and ideal power, and the total power with the induced-power factor
and a tail-rotor profile power estimate.

All functions raise ValueError on non-physical inputs. Units are SI.
"""

import math

G0 = 9.80665
RHO_SL = 1.225
K_DEFAULT = 1.15
SIGMA_TR_DEFAULT = 0.10
CD_TR_DEFAULT = 0.012
PI = math.pi


def main_rotor_torque(power_w, omega_rad_s):
    """Main rotor shaft torque Q = power / omega (N m).

    ValueError if power_w < 0 or omega_rad_s <= 0.
    """
    if power_w < 0:
        raise ValueError("power_w must be >= 0")
    if omega_rad_s <= 0:
        raise ValueError("omega_rad_s must be > 0")
    return power_w / omega_rad_s


def tail_rotor_thrust(torque_nm, tail_arm_m, margin_factor=1.0):
    """Anti-torque thrust T_tr = margin_factor * torque / tail_arm (N).

    ValueError if torque < 0, tail_arm <= 0, margin_factor <= 0.
    """
    if torque_nm < 0:
        raise ValueError("torque_nm must be >= 0")
    if tail_arm_m <= 0:
        raise ValueError("tail_arm_m must be > 0")
    if margin_factor <= 0:
        raise ValueError("margin_factor must be > 0")
    return margin_factor * torque_nm / tail_arm_m


def tail_rotor_area(thrust, max_disk_loading):
    """Tail rotor disk area A = thrust / max_disk_loading (m2).

    ValueError if thrust < 0 or max_disk_loading <= 0.
    """
    if thrust < 0:
        raise ValueError("thrust must be >= 0")
    if max_disk_loading <= 0:
        raise ValueError("max_disk_loading must be > 0")
    return thrust / max_disk_loading


def tail_rotor_radius(area):
    """Tail rotor radius R = sqrt(area / PI) (m).

    ValueError if area <= 0.
    """
    if area <= 0:
        raise ValueError("area must be > 0")
    return math.sqrt(area / PI)


def tail_rotor_disk_loading(thrust, area):
    """Tail rotor disk loading DL = thrust / area (Pa).

    ValueError if area <= 0 or thrust < 0.
    """
    if area <= 0:
        raise ValueError("area must be > 0")
    if thrust < 0:
        raise ValueError("thrust must be >= 0")
    return thrust / area


def tail_rotor_induced_velocity(thrust, area, rho=RHO_SL):
    """Momentum-theory ideal induced velocity v_i = sqrt(thrust / (2 rho A)).

    ValueError on any non-positive input.
    """
    if thrust <= 0:
        raise ValueError("thrust must be > 0")
    if area <= 0:
        raise ValueError("area must be > 0")
    if rho <= 0:
        raise ValueError("rho must be > 0")
    return math.sqrt(thrust / (2.0 * rho * area))


def tail_rotor_ideal_power(thrust, induced_velocity):
    """Ideal (induced) power P_ideal = thrust * induced_velocity (W).

    ValueError if thrust < 0 or induced_velocity < 0.
    """
    if thrust < 0:
        raise ValueError("thrust must be >= 0")
    if induced_velocity < 0:
        raise ValueError("induced_velocity must be >= 0")
    return thrust * induced_velocity


def tail_rotor_profile_power(rho, area, solidity=SIGMA_TR_DEFAULT,
                             drag_coefficient=CD_TR_DEFAULT, tip_speed=200.0):
    """Tail rotor profile power P_profile = (1/8) rho sigma Cd A tip^3 (W).

    ValueError if any of rho, area, solidity, drag_coefficient, tip_speed
    is <= 0.
    """
    if rho <= 0:
        raise ValueError("rho must be > 0")
    if area <= 0:
        raise ValueError("area must be > 0")
    if solidity <= 0:
        raise ValueError("solidity must be > 0")
    if drag_coefficient <= 0:
        raise ValueError("drag_coefficient must be > 0")
    if tip_speed <= 0:
        raise ValueError("tip_speed must be > 0")
    return 0.125 * rho * solidity * drag_coefficient * area * tip_speed ** 3


def tail_rotor_total_power(ideal_power, profile_power, k=K_DEFAULT):
    """Total tail rotor power P_total = k * ideal_power + profile_power (W).

    ValueError if ideal_power < 0 or profile_power < 0 or k <= 0.
    """
    if ideal_power < 0:
        raise ValueError("ideal_power must be >= 0")
    if profile_power < 0:
        raise ValueError("profile_power must be >= 0")
    if k <= 0:
        raise ValueError("k must be > 0")
    return k * ideal_power + profile_power


def tail_rotor_sizing(main_power_w, omega_rad_s, tail_arm_m,
                      max_disk_loading=300.0, rho=RHO_SL, margin_factor=1.0,
                      solidity=SIGMA_TR_DEFAULT, drag_coefficient=CD_TR_DEFAULT,
                      tip_speed=200.0, k=K_DEFAULT):
    """Convenience chain: size the tail rotor from the main rotor torque
    balance. Returns the documented dict; ValueErrors propagate.
    """
    torque = main_rotor_torque(main_power_w, omega_rad_s)
    thrust = tail_rotor_thrust(torque, tail_arm_m, margin_factor)
    area = tail_rotor_area(thrust, max_disk_loading)
    radius = tail_rotor_radius(area)
    disk_loading = tail_rotor_disk_loading(thrust, area)
    induced_velocity = tail_rotor_induced_velocity(thrust, area, rho)
    ideal_power = tail_rotor_ideal_power(thrust, induced_velocity)
    profile_power = tail_rotor_profile_power(rho, area, solidity,
                                             drag_coefficient, tip_speed)
    total_power = tail_rotor_total_power(ideal_power, profile_power, k)
    return {
        "main_rotor_torque_nm": torque,
        "tail_rotor_thrust_N": thrust,
        "tail_rotor_area_m2": area,
        "tail_rotor_radius_m": radius,
        "tail_rotor_disk_loading_Pa": disk_loading,
        "tail_rotor_induced_velocity": induced_velocity,
        "tail_rotor_ideal_power_W": ideal_power,
        "tail_rotor_profile_power_W": profile_power,
        "tail_rotor_total_power_W": total_power,
    }

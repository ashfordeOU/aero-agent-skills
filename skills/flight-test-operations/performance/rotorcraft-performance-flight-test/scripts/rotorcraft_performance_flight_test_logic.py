"""Rotorcraft performance flight test reduction (measured data only).

Pure stdlib helpers that reduce MEASURED rotorcraft hover and climb
performance flight test data: measured main rotor torque and rotor
speed into shaft power, the measured figure of merit from the ideal
induced power and the measured power, hover power corrected to a
reference weight and density altitude with the induced and profile
fraction split, a measured vertical rate of climb corrected for test
weight, hover power-required points measured across density altitudes
reduced to a hover ceiling against the available power, and the test
day checked against the flight manual limits.

This leaf works only from measured torque, rotor speed, weight,
density and altitude data. It does NOT compute rotor physics from
geometry and weight; the flight-mechanics rotorcraft performance
leaves own the analytic momentum-theory models. Deterministic: no RNG,
run-to-run identical floats.

Module constants:
    G0 = 9.80665  (m/s^2, standard gravity)
    PI = math.pi
"""

import math

G0 = 9.80665
PI = math.pi


def shaft_power_from_torque(torque_nm, omega_rad_s):
    """Shaft power P = torque * omega from a measured torque point.

    Measured main rotor torque (Nm) at a measured rotor speed
    (rad/s). ValueError when torque < 0 or omega <= 0; a zero torque
    at a positive rotor speed is a valid measured point (0 W).
    """
    if torque_nm < 0:
        raise ValueError("measured torque cannot be negative")
    if omega_rad_s <= 0:
        raise ValueError("rotor speed must be positive")
    return torque_nm * omega_rad_s


def ideal_induced_power(thrust_n, rho, area_m2):
    """Ideal induced power P_ideal = T * sqrt(T / (2 * rho * A)).

    The ideal power for a rotor of disk area A carrying thrust T in
    air of density rho (ideal-rotor result). ValueErrors on thrust
    <= 0, rho <= 0 or area <= 0.
    """
    if thrust_n <= 0:
        raise ValueError("thrust must be positive")
    if rho <= 0:
        raise ValueError("air density must be positive")
    if area_m2 <= 0:
        raise ValueError("rotor disk area must be positive")
    return thrust_n * math.sqrt(thrust_n / (2.0 * rho * area_m2))


def measured_figure_of_merit(thrust_n, rho, area_m2, measured_power_w):
    """Figure of merit FM = P_ideal / P_measured from measured power.

    The ratio of the ideal induced power at the evaluation thrust and
    density over the MEASURED shaft power. ValueErrors on
    measured_power <= 0; the ideal induced power cannot exceed the
    measured power for a physical measurement (FM must be <= 1.0).
    """
    if measured_power_w <= 0:
        raise ValueError("measured power must be positive")
    p_ideal = ideal_induced_power(thrust_n, rho, area_m2)
    if p_ideal > measured_power_w:
        raise ValueError("measured power cannot be below the ideal induced power")
    return p_ideal / measured_power_w


def power_correction_weight_density(measured_power_w, weight_meas_n,
                                    weight_ref_n, rho_meas, rho_ref,
                                    induced_fraction=0.6):
    """Correct measured hover power to a reference weight and density.

    P_corr = P_meas * [ f_i * (W_ref / W_meas)^1.5 * sqrt(rho_meas /
    rho_ref) + (1 - f_i) * (rho_ref / rho_meas) ]. The induced power
    fraction f_i scales with the ideal-rotor result W^1.5 / sqrt(rho);
    the profile fraction (1 - f_i) scales with rho. ValueErrors on
    measured_power < 0, weight_meas <= 0, weight_ref <= 0, rho_meas
    <= 0, rho_ref <= 0, induced_fraction outside [0, 1].
    """
    if measured_power_w < 0:
        raise ValueError("measured power cannot be negative")
    if weight_meas_n <= 0:
        raise ValueError("measured weight must be positive")
    if weight_ref_n <= 0:
        raise ValueError("reference weight must be positive")
    if rho_meas <= 0:
        raise ValueError("measured air density must be positive")
    if rho_ref <= 0:
        raise ValueError("reference air density must be positive")
    if not 0.0 <= induced_fraction <= 1.0:
        raise ValueError("induced fraction must lie in [0, 1]")
    induced_term = ((weight_ref_n / weight_meas_n) ** 1.5
                    * math.sqrt(rho_meas / rho_ref))
    profile_term = rho_ref / rho_meas
    factor = (induced_fraction * induced_term
              + (1.0 - induced_fraction) * profile_term)
    return measured_power_w * factor


def corrected_vertical_rate_of_climb(roc_meas_m_s, weight_meas_n,
                                     weight_ref_n):
    """Correct a measured vertical rate of climb for test weight.

    ROC_corr = ROC_meas * weight_meas / weight_ref (excess-power
    scaling: ROC is proportional to excess power over weight).
    ValueErrors on weight_meas <= 0 or weight_ref <= 0. A negative
    measured ROC (descent test point) is allowed through unchanged in
    sign.
    """
    if weight_meas_n <= 0:
        raise ValueError("measured weight must be positive")
    if weight_ref_n <= 0:
        raise ValueError("reference weight must be positive")
    return roc_meas_m_s * weight_meas_n / weight_ref_n


def hover_ceiling_altitude(power_available_w, altitude_m_list,
                           power_required_w_list):
    """Hover ceiling altitude from measured power-required points.

    Linear interpolation of the measured hover power-required versus
    altitude points; returns the altitude where the required power
    equals the available power. Returns None when the required power
    at the lowest altitude already exceeds the available power (hover
    not achieved at the lowest test altitude) or when the required
    power at the highest altitude is still below the available power
    (no ceiling within the tested range; the caller flags the report
    that the ceiling lies above the tested band). ValueErrors on
    mismatched list lengths, fewer than 2 points, or any negative
    altitude, required power or available power.
    """
    altitudes = list(altitude_m_list)
    required = list(power_required_w_list)
    if len(altitudes) != len(required):
        raise ValueError("altitude and power-required lists must match in length")
    if len(altitudes) < 2:
        raise ValueError("at least two ceiling test points are required")
    if power_available_w < 0:
        raise ValueError("available power cannot be negative")
    if any(a < 0 for a in altitudes):
        raise ValueError("test altitudes cannot be negative")
    if any(p < 0 for p in required):
        raise ValueError("power required cannot be negative")
    if required[0] > power_available_w:
        return None
    if required[-1] < power_available_w:
        return None
    for i in range(len(altitudes) - 1):
        span = required[i + 1] - required[i]
        if span == 0:
            if required[i] == power_available_w:
                return altitudes[i]
            continue
        low = min(required[i], required[i + 1])
        high = max(required[i], required[i + 1])
        if low <= power_available_w <= high:
            fraction = (power_available_w - required[i]) / span
            return altitudes[i] + fraction * (altitudes[i + 1] - altitudes[i])
    return None


def torque_to_power_check(torque_nm, omega_rad_s, rated_power_w,
                          tolerance=0.05):
    """Check a measured torque point against the rated shaft power.

    Returns {shaft_power_w, within_rated: bool}; within_rated is True
    when the shaft power does not exceed rated_power * (1 + tolerance).
    ValueErrors as in shaft_power_from_torque (torque < 0, omega <= 0).
    """
    shaft_power_w = shaft_power_from_torque(torque_nm, omega_rad_s)
    within_rated = shaft_power_w <= rated_power_w * (1.0 + tolerance)
    return {"shaft_power_w": shaft_power_w, "within_rated": within_rated}


def rotorcraft_performance_test_reduction(torque_points_nm, omega_rad_s,
                                          weight_meas_n, weight_ref_n,
                                          rho_meas, rho_ref, area_m2,
                                          rated_power_w,
                                          induced_fraction=0.6):
    """Convenience chain for one rotorcraft performance test point.

    omega_rad_s may be a scalar rotor speed (points measured at
    constant rotor speed) or a list matching torque_points_nm.
    Computes the mean measured shaft power, the measured figure of
    merit at the mean torque point, the weight-density corrected
    hover power and the torque check verdict. The reported figure of
    merit is evaluated at the reference hover condition (thrust =
    weight_ref at rho_ref), the same reporting basis as the corrected
    hover power, so it lands in the physical hover band of the
    worked-example anchor. Every ValueError of the primitives
    propagates. Returns exactly {mean_shaft_power_w,
    measured_figure_of_merit, corrected_power_w, within_rated}.
    """
    torques = list(torque_points_nm)
    if len(torques) == 0:
        raise ValueError("at least one torque point is required")
    if isinstance(omega_rad_s, (list, tuple)):
        omegas = list(omega_rad_s)
        if len(omegas) != len(torques):
            raise ValueError("omega list must match the torque list length")
        powers = [shaft_power_from_torque(t, w) for t, w in zip(torques, omegas)]
        check_omega = sum(omegas) / len(omegas)
    else:
        powers = [shaft_power_from_torque(t, omega_rad_s) for t in torques]
        check_omega = omega_rad_s
    mean_shaft_power_w = sum(powers) / len(powers)
    mean_torque_nm = sum(torques) / len(torques)
    figure_of_merit = measured_figure_of_merit(
        weight_ref_n, rho_ref, area_m2, mean_shaft_power_w)
    corrected_power_w = power_correction_weight_density(
        mean_shaft_power_w, weight_meas_n, weight_ref_n, rho_meas,
        rho_ref, induced_fraction)
    within_rated = torque_to_power_check(
        mean_torque_nm, check_omega, rated_power_w)["within_rated"]
    return {
        "mean_shaft_power_w": mean_shaft_power_w,
        "measured_figure_of_merit": figure_of_merit,
        "corrected_power_w": corrected_power_w,
        "within_rated": within_rated,
    }

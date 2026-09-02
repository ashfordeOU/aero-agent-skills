#!/usr/bin/env python3
"""Flight loads survey logic for flight test (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25/cs-25 context): a
flight loads survey calibrates strain gauge stations against known
applied ground loads, then reduces the in-flight strain records of the
load factor versus speed survey (symmetric and rolling maneuvers) to
measured loads, load factor, and lift coefficient for comparison with
the predicted loads envelope (FAR 25.301 / CS-25.301 load conditions
context). The strain gauge relation epsilon = delta_R / (R * GF), the
through-origin least squares calibration slope
K = sum(L_i * epsilon_i) / sum(epsilon_i^2), and the dynamic pressure
q = 0.5 * rho * V^2 with the achieved load factor n = q * CL / (W/S)
are standard flight test methodology. All values are SI (N, Pa, kg/m^3,
m/s EAS, strain dimensionless).
"""

import math

DEFAULT_GAUGE_FACTOR = 2.1  # typical metal foil gauge factor, dimensionless


def _require_finite(value, name):
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _require_positive(value, name):
    _require_finite(value, name)
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def strain_from_delta_resistance(delta_r, nominal_r, gauge_factor):
    """Strain from the gauge resistance change, dimensionless.

    epsilon = delta_R / (R * GF) with delta_R in ohm (negative for
    compression), nominal resistance R in ohm, and gauge factor GF
    dimensionless (typical 2.0 to 2.2). Raises ValueError when
    nominal_r <= 0 or gauge_factor <= 0.
    """
    _require_finite(delta_r, "resistance change")
    _require_positive(nominal_r, "nominal resistance")
    _require_positive(gauge_factor, "gauge factor")
    return delta_r / (nominal_r * gauge_factor)


def calibration_factor(loads, strains):
    """Through-origin least squares calibration slope, load per strain.

    K = sum(L_i * epsilon_i) / sum(epsilon_i^2) from the applied
    calibration loads L_i (N) and the recorded strains epsilon_i
    (dimensionless). Raises ValueError on empty or mismatched input,
    non-finite values, or a zero strain energy sum.
    """
    if len(loads) == 0:
        raise ValueError("calibration loads must not be empty")
    if len(loads) != len(strains):
        raise ValueError(
            "calibration loads and strains must match, got %d and %d"
            % (len(loads), len(strains))
        )
    num = 0.0
    den = 0.0
    for load, strain in zip(loads, strains):
        _require_finite(load, "calibration load")
        _require_finite(strain, "calibration strain")
        num += load * strain
        den += strain * strain
    if den <= 0:
        raise ValueError("calibration strain energy is zero; no valid fit")
    return num / den


def measured_load(calibration_k, strain, zero_strain=0.0):
    """Measured load at a strain gauge station, N.

    L = K * (epsilon - epsilon_0) with K the calibration factor, the
    in-flight strain epsilon, and the pre-flight zero offset
    epsilon_0. Raises ValueError when calibration_k <= 0.
    """
    _require_positive(calibration_k, "calibration factor")
    _require_finite(strain, "strain")
    _require_finite(zero_strain, "zero strain")
    return calibration_k * (strain - zero_strain)


def load_error_percent(measured, predicted):
    """Percent deviation of the measured load from the predicted load.

    (measured - predicted) / predicted * 100, positive when the
    measured load is above the prediction. Raises ValueError when
    predicted == 0.
    """
    _require_finite(measured, "measured load")
    _require_finite(predicted, "predicted load")
    if predicted == 0:
        raise ValueError("predicted load must not be zero")
    return 100.0 * (measured - predicted) / predicted


def dynamic_pressure(rho, v_eas):
    """Dynamic pressure q = 0.5 * rho * V^2, Pa.

    rho in kg/m^3 and V in m/s EAS. Raises ValueError when rho <= 0 or
    v_eas < 0.
    """
    _require_positive(rho, "air density")
    _require_finite(v_eas, "equivalent airspeed")
    if v_eas < 0:
        raise ValueError("equivalent airspeed must be >= 0, got %r" % (v_eas,))
    return 0.5 * rho * v_eas * v_eas


def lift_coefficient_at_maneuver(load_factor, wing_loading, q):
    """Lift coefficient of a survey point, dimensionless.

    CL = n * (W/S) / q with the achieved load factor n, the wing
    loading W/S in Pa, and the dynamic pressure q in Pa. Raises
    ValueError when load_factor <= 0, wing_loading <= 0, or q <= 0.
    """
    _require_positive(load_factor, "load factor")
    _require_positive(wing_loading, "wing loading")
    _require_positive(q, "dynamic pressure")
    return load_factor * wing_loading / q


def symmetric_maneuver_load_factor(v_eas, rho, wing_loading, cl):
    """Achieved load factor of a steady symmetric maneuver, dimensionless.

    n = q * CL / (W/S) = 0.5 * rho * V^2 * CL / (W/S) with V in m/s
    EAS, rho in kg/m^3, W/S in Pa, and CL dimensionless. Raises
    ValueError when rho <= 0, v_eas < 0, wing_loading <= 0, or
    cl <= 0.
    """
    q = dynamic_pressure(rho, v_eas)
    _require_positive(wing_loading, "wing loading")
    _require_positive(cl, "lift coefficient")
    return q * cl / wing_loading


def maneuver_point_feasible(load_factor, wing_loading, q, cl_max):
    """Whether a survey point is reachable without stalling, bool.

    The point is feasible when the required CL = n * (W/S) / q stays at
    or below CL_max; above it the maneuver stalls before reaching the
    target load factor. Raises ValueError when cl_max <= 0 or any
    shared input is invalid.
    """
    _require_positive(cl_max, "maximum lift coefficient")
    required_cl = lift_coefficient_at_maneuver(load_factor, wing_loading, q)
    return required_cl <= cl_max


def load_factor_from_measured_load(measured, reference_weight):
    """Load factor from the measured station load, dimensionless.

    n = L_meas / W_ref with the measured load L_meas in N and the
    reference weight W_ref in N. Raises ValueError when
    reference_weight <= 0.
    """
    _require_finite(measured, "measured load")
    _require_positive(reference_weight, "reference weight")
    return measured / reference_weight


def point_in_calibration_range(strain, strain_min, strain_max):
    """Whether a strain lies inside the calibrated range, bool.

    Inclusive on both ends. Raises ValueError when strain_max <
    strain_min (inverted range).
    """
    _require_finite(strain, "strain")
    _require_finite(strain_min, "minimum calibration strain")
    _require_finite(strain_max, "maximum calibration strain")
    if strain_max < strain_min:
        raise ValueError(
            "maximum calibration strain below minimum, got %r < %r"
            % (strain_max, strain_min)
        )
    return strain_min <= strain <= strain_max


def survey_point_ok(measured_n, target_n, tolerance=0.0):
    """Whether the measured load factor reached the target, bool.

    Passes when measured_n >= target_n - tolerance. Raises ValueError
    when tolerance < 0.
    """
    _require_finite(measured_n, "measured load factor")
    _require_finite(target_n, "target load factor")
    _require_finite(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0, got %r" % (tolerance,))
    return measured_n >= target_n - tolerance

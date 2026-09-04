"""Lateral-directional static stability flight test reduction (pure stdlib).

Reduces steady-heading sideslip (SHS) flight test sweeps into the fitted
rudder, aileron and pedal-force gradients versus sideslip angle, and
combines the control gradients with declared control-power inputs to form
the signed measured estimates of directional (Cn_beta) and lateral
(Cl_beta) stability used in the FAR 25.177-style static stability
demonstration.  This module reduces measured flight test data only; the
control-power parameters are declared inputs, never claimed as measured.

Sign convention (documented in the SKILL body): beta is positive when the
nose is LEFT of the velocity vector (left slip).  delta_r positive = right
pedal, delta_a positive = right aileron (left roll).  A directionally
stable aircraft shows a POSITIVE rudder gradient s_r = d(delta_r)/d(beta)
(the pilot pushes rudder into the slip), so with the signed control power
cn_dr < 0 the estimate Cn_beta_est = -cn_dr * s_r is positive.  A
laterally stable aircraft (dihedral effect) holds the slip with aileron
against the roll, showing a NEGATIVE aileron gradient s_a, so with
cl_da < 0 the estimate Cl_beta_est = -cl_da * s_a is negative.  The
deg/deg and rad/rad gradient ratios are numerically identical, so the
gradients enter the signed estimates as unitless slopes.
"""

import math

# Module constants (no magic numbers).
DEG_TO_RAD = math.pi / 180.0
BETA_SWEEP_MIN = 2  # minimum number of sweep points for a slope fit
BETA_SWEEP_MAX = 40  # planning cap for a sideslip sweep
SIDESLIP_LIMIT_DEG = 15.0  # declared test limit on |beta|

_VERDICT_STABLE = "stable"
_VERDICT_UNSTABLE = "unstable"


def fit_slope(xs, ys):
    """Return dy/dx from a two-parameter (offset + slope) least squares fit.

    Args:
        xs: sequence of x values (sideslip angle in deg, or any abscissa).
        ys: sequence of y values (control deflection or pedal force).

    Returns:
        The fitted slope as a float.

    Raises:
        ValueError: lengths mismatch, fewer than BETA_SWEEP_MIN points, or
        zero x variance (vertical point set).
    """
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have equal length")
    if len(xs) < BETA_SWEEP_MIN:
        raise ValueError("need at least %d points for a slope fit" % BETA_SWEEP_MIN)
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    s_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    s_xx = sum((x - x_mean) ** 2 for x in xs)
    if s_xx == 0.0:
        raise ValueError("zero x variance: cannot fit a slope to vertical points")
    return s_xy / s_xx


def rudder_gradient(beta_deg, delta_r_deg):
    """Fit the rudder deflection gradient s_r = d(delta_r)/d(beta).

    Positive s_r (deg/deg, unitless) is the signature of a directionally
    stable aircraft: the pilot pushes the rudder into the slip.
    """
    return fit_slope(beta_deg, delta_r_deg)


def aileron_gradient(beta_deg, delta_a_deg):
    """Fit the aileron deflection gradient s_a = d(delta_a)/d(beta).

    Negative s_a (deg/deg, unitless) is the signature of a laterally
    stable aircraft (dihedral effect): aileron is held against the roll
    induced by the slip.
    """
    return fit_slope(beta_deg, delta_a_deg)


def pedal_force_gradient(beta_deg, pedal_force_N):
    """Fit the pedal-force gradient g_p = d(F_pedal)/d(beta) in N/deg.

    Taken from the rudder-free run: the pedal force the pilot must apply
    to hold each sideslip angle.
    """
    return fit_slope(beta_deg, pedal_force_N)


def signed_directional_estimate(cn_dr_per_rad, rudder_gradient_per_deg):
    """Estimate the directional stability Cn_beta = -cn_dr * s_r (/rad).

    Args:
        cn_dr_per_rad: declared rudder control power, signed (/rad).
        rudder_gradient_per_deg: fitted rudder gradient (deg/deg, unitless).

    Returns:
        The signed Cn_beta estimate in /rad; positive means weathercock
        (directionally) stable.

    Raises:
        ValueError: cn_dr_per_rad == 0 (no control power declared).
    """
    if cn_dr_per_rad == 0.0:
        raise ValueError("rudder control power cn_dr must be non-zero")
    return -cn_dr_per_rad * rudder_gradient_per_deg


def signed_lateral_estimate(cl_da_per_rad, aileron_gradient_per_deg):
    """Estimate the lateral stability Cl_beta = -cl_da * s_a (/rad).

    Args:
        cl_da_per_rad: declared aileron control power, signed (/rad).
        aileron_gradient_per_deg: fitted aileron gradient (deg/deg, unitless).

    Returns:
        The signed Cl_beta estimate in /rad; negative means dihedrally
        (laterally) stable.

    Raises:
        ValueError: cl_da_per_rad == 0 (no control power declared).
    """
    if cl_da_per_rad == 0.0:
        raise ValueError("aileron control power cl_da must be non-zero")
    return -cl_da_per_rad * aileron_gradient_per_deg


def weathercock_verdict(cn_beta_est_per_rad):
    """Return the directional (weathercock) stability verdict.

    "stable" when Cn_beta_est > 0, else "unstable".  Threshold edges and
    non-positive values count as unstable per the demonstration criteria.
    """
    if cn_beta_est_per_rad > 0.0:
        return _VERDICT_STABLE
    return _VERDICT_UNSTABLE


def dihedral_verdict(cl_beta_est_per_rad):
    """Return the lateral (dihedral) stability verdict.

    "stable" when Cl_beta_est < 0, else "unstable".  Threshold edges and
    non-negative values count as unstable per the demonstration criteria.
    """
    if cl_beta_est_per_rad < 0.0:
        return _VERDICT_STABLE
    return _VERDICT_UNSTABLE


def build_sideslip_matrix(beta_targets_deg, cas_ms, altitude_m):
    """Build the sideslip sweep test matrix rows.

    Args:
        beta_targets_deg: iterable of commanded sideslip angles (deg).
        cas_ms: constant calibrated airspeed for the sweep (m/s).
        altitude_m: test altitude (m).

    Returns:
        List of dicts {beta_target_deg, cas_ms, altitude_m}, one row per
        commanded target, each row carrying the float values.

    Raises:
        ValueError: any beta target outside the declared
        [-SIDESLIP_LIMIT_DEG, SIDESLIP_LIMIT_DEG] band, or cas_ms <= 0.
    """
    if cas_ms <= 0.0:
        raise ValueError("calibrated airspeed must be positive")
    rows = []
    for target in beta_targets_deg:
        if target < -SIDESLIP_LIMIT_DEG or target > SIDESLIP_LIMIT_DEG:
            raise ValueError(
                "beta target %.3f deg outside declared +-%.1f deg limit"
                % (target, SIDESLIP_LIMIT_DEG)
            )
        rows.append(
            {
                "beta_target_deg": float(target),
                "cas_ms": float(cas_ms),
                "altitude_m": float(altitude_m),
            }
        )
    return rows


def reduce_sideslip_sweep(
    beta_deg,
    delta_r_deg,
    delta_a_deg,
    pedal_force_N=None,
    cn_dr_per_rad=None,
    cl_da_per_rad=None,
):
    """Reduce a full steady-heading sideslip sweep in one call.

    Args:
        beta_deg: sideslip angles (deg), positive = left slip.
        delta_r_deg: rudder deflections held at each beta (deg).
        delta_a_deg: aileron deflections held at each beta (deg).
        pedal_force_N: optional pedal forces from the rudder-free run (N).
        cn_dr_per_rad: optional declared rudder control power (/rad).
        cl_da_per_rad: optional declared aileron control power (/rad).

    Returns:
        Dict with exactly the documented keys:
        rudder_gradient_per_deg, aileron_gradient_per_deg,
        pedal_force_gradient_N_per_deg (None without pedal forces),
        cn_beta_estimate_per_rad (None without cn_dr),
        cl_beta_estimate_per_rad (None without cl_da),
        weathercock_verdict (None without cn_dr),
        dihedral_verdict (None without cl_da), point_count.

    Raises:
        ValueError: any fitted quantity rejects its inputs (mismatched or
        too-short series, zero x variance, zero control power).
    """
    result = {
        "rudder_gradient_per_deg": rudder_gradient(beta_deg, delta_r_deg),
        "aileron_gradient_per_deg": aileron_gradient(beta_deg, delta_a_deg),
        "pedal_force_gradient_N_per_deg": None,
        "cn_beta_estimate_per_rad": None,
        "cl_beta_estimate_per_rad": None,
        "weathercock_verdict": None,
        "dihedral_verdict": None,
        "point_count": len(list(beta_deg)),
    }
    if pedal_force_N is not None:
        result["pedal_force_gradient_N_per_deg"] = pedal_force_gradient(
            beta_deg, pedal_force_N
        )
    if cn_dr_per_rad is not None:
        cn_est = signed_directional_estimate(
            cn_dr_per_rad, result["rudder_gradient_per_deg"]
        )
        result["cn_beta_estimate_per_rad"] = cn_est
        result["weathercock_verdict"] = weathercock_verdict(cn_est)
    if cl_da_per_rad is not None:
        cl_est = signed_lateral_estimate(
            cl_da_per_rad, result["aileron_gradient_per_deg"]
        )
        result["cl_beta_estimate_per_rad"] = cl_est
        result["dihedral_verdict"] = dihedral_verdict(cl_est)
    return result


def main():
    """Run the spec worked example and print the real module outputs."""
    beta_deg = [2.0, 5.0, 8.0, 11.0, 14.0]
    delta_r_deg = [0.24, 0.58, 0.96, 1.34, 1.70]
    delta_a_deg = [-0.35, -0.80, -1.30, -1.80, -2.30]
    pedal_force_N = [0.0, -95.0, -185.0, -275.0, -360.0]
    out = reduce_sideslip_sweep(
        beta_deg,
        delta_r_deg,
        delta_a_deg,
        pedal_force_N=pedal_force_N,
        cn_dr_per_rad=-0.90,
        cl_da_per_rad=-0.35,
    )
    print("rudder_gradient_per_deg = %.6f" % out["rudder_gradient_per_deg"])
    print("aileron_gradient_per_deg = %.6f" % out["aileron_gradient_per_deg"])
    print("pedal_force_gradient_N_per_deg = %.6f" % out["pedal_force_gradient_N_per_deg"])
    print("cn_beta_estimate_per_rad = %.6f" % out["cn_beta_estimate_per_rad"])
    print("cl_beta_estimate_per_rad = %.6f" % out["cl_beta_estimate_per_rad"])
    print("weathercock_verdict = %s" % out["weathercock_verdict"])
    print("dihedral_verdict = %s" % out["dihedral_verdict"])
    print("point_count = %d" % out["point_count"])
    for row in build_sideslip_matrix([0.0, 5.0, 10.0], 80.0, 3000.0):
        print("row", row)


if __name__ == "__main__":
    main()

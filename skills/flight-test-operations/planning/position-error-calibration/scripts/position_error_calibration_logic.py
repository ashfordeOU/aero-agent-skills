#!/usr/bin/env python3
"""Airspeed position error calibration (PEC) flight test logic.

Scope: planning and reduction of the airspeed position error
calibration flight test for a fixed-wing aircraft (standards-map.yaml,
far-25 and cs-25: reference-only regulation context, summarized, not
reproduced). This leaf owns the airspeed PEC method: the compressible
calibrated airspeed relations, the tower fly-by, trailing cone and GPS
ground speed doublet references, and the position error correction
curve. It does NOT own recorder channel calibration, smoothing or
combined uncertainty (flight-test-data-reduction), angle of attack
sensor calibration (high-angle-of-attack-testing), or the Vref/V2/Vr
speed rules (v-speeds).

Standard atmosphere airspeed relations (ISA module constants):
    q_c   = p0 * ((1 + 0.2*(V_cas/a0)^2)^3.5 - 1)      impact pressure
    V_cas = a0 * sqrt(5 * ((q_c/p0 + 1)^(2/7) - 1))    calibrated airspeed
with a0 = 340.294 m/s and p0 = 101325 Pa at sea level. The position
error correction is dVp(V_ias) = V_cas - V_ias and the identity
V_cas == V_ias holds when the position error is zero by construction.

All speeds are m/s, heights m, pressures Pa, temperatures K.
Deterministic, stdlib only, no network.
"""

import math

# ISA sea level standard atmosphere module constants.
A0 = 340.294  # m/s, sea level speed of sound
P0 = 101325.0  # Pa, sea level static pressure
RHO0 = 1.225  # kg/m^3, sea level air density
G0 = 9.80665  # m/s^2, standard gravity
R_AIR = 287.053  # J/(kg K), specific gas constant of dry air
T0 = 288.15  # K, sea level temperature
LAPSE = 0.0065  # K/m, troposphere lapse rate
TROPOPAUSE = 11000.0  # m, ISA tropopause height
T_STRAT = 216.65  # K, ISA stratosphere isothermal temperature
_TROP_EXP = G0 / (R_AIR * LAPSE)
# m/s, reference indicated airspeed of the tower fly-by pass used by the
# reduced fly-by form when the pass speed is not supplied (mid range of a
# typical PEC sweep, matching the leaf worked examples).
FLYBY_REFERENCE_CAS = 100.0
# PEC data quality verdict thresholds.
COVERAGE_MIN = 0.95  # minimum fraction of planned points inside the calibrated span
RESIDUAL_RMS_MAX = 1.0  # m/s, maximum residual RMS for an adequate verdict


def _finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def _isa_pressure(altitude_m):
    """ISA static pressure in Pa at a pressure altitude in m (troposphere or
    stratosphere branch). Internal helper for the altimeter scale relation."""
    if not _finite(altitude_m):
        raise ValueError("altitude must be finite, got %r" % (altitude_m,))
    if altitude_m <= TROPOPAUSE:
        p = P0 * (1.0 - LAPSE * altitude_m / T0) ** _TROP_EXP
    else:
        p_tropo = P0 * (1.0 - LAPSE * TROPOPAUSE / T0) ** _TROP_EXP
        p = p_tropo * math.exp(-G0 * (altitude_m - TROPOPAUSE) / (R_AIR * T_STRAT))
    return p


def calibrated_airspeed(qc):
    """Calibrated airspeed V_cas in m/s from the impact pressure qc in Pa.

    V_cas = a0 * sqrt(5 * ((qc/p0 + 1)^(2/7) - 1)), the inverse of the
    compressible impact pressure relation at the ISA sea level condition.
    Raises ValueError for a non-finite or negative impact pressure (a
    negative impact pressure is not physical for forward flight).
    """
    if not _finite(qc) or qc < 0.0:
        raise ValueError(
            "impact pressure must be a finite value >= 0 Pa, got %r" % (qc,)
        )
    return A0 * math.sqrt(5.0 * ((qc / P0 + 1.0) ** (2.0 / 7.0) - 1.0))


def impact_pressure_from_cas(v_cas):
    """Impact pressure qc in Pa for a calibrated airspeed in m/s.

    qc = p0 * ((1 + 0.2*(V_cas/a0)^2)^3.5 - 1). Raises ValueError for a
    non-finite or negative speed.
    """
    if not _finite(v_cas) or v_cas < 0.0:
        raise ValueError(
            "calibrated airspeed must be a finite value >= 0 m/s, got %r" % (v_cas,)
        )
    return P0 * ((1.0 + 0.2 * (v_cas / A0) ** 2.0) ** 3.5 - 1.0)


def position_error(v_ias, v_cas):
    """Position error correction dVp = V_cas - V_ias in m/s.

    Positive when the airspeed indicator reads low (the correction is
    added to the indicated airspeed). Raises ValueError for non-finite or
    negative inputs.
    """
    if not _finite(v_ias) or v_ias < 0.0:
        raise ValueError("indicated airspeed must be a finite value >= 0 m/s")
    if not _finite(v_cas) or v_cas < 0.0:
        raise ValueError("calibrated airspeed must be a finite value >= 0 m/s")
    return v_cas - v_ias


def tower_flyby_position_error(geometric_height, pressure_altitude, temperature,
                               v_ias=None):
    """Position error dVp in m/s from one tower fly-by pass.

    The aircraft flies level at a known geometric height above the tower
    while the altimeter (standard setting) records the pressure altitude.
    The height error of the static source is dh = H_geom - H_p, positive
    when the altimeter reads below the surveyed geometric height. The
    static pressure error follows the altimeter scale (hydrostatic)
    relation dp_s = rho * g0 * dh with rho = p(H_p)/(R*T) evaluated at
    the measured temperature, and the same dp_s displaces the impact
    pressure seen by the standard airspeed indicator by -dp_s, so

        V_cas = V_isa(qc(V_ias) + dp_s),  dVp = V_cas - V_ias

    with the exact compressible airspeed indicator law (calibrated_airspeed
    and impact_pressure_from_cas). Simplified relation used by the reduced
    form: when the pass speed is not supplied (v_ias=None) the indicator
    scale is evaluated at FLYBY_REFERENCE_CAS, the leaf reference fly-by
    speed; pass the scheduled pass indicated airspeed when available. The
    result carries the sign of the height error: a low altimeter reading
    (H_p < H_geom) gives a positive correction.

    Raises ValueError for non-finite inputs, a geometric height below
    zero, a non-positive temperature, or a negative pass speed.
    """
    if not _finite(geometric_height) or geometric_height < 0.0:
        raise ValueError("geometric height must be a finite value >= 0 m")
    if not _finite(pressure_altitude):
        raise ValueError("pressure altitude must be finite, got %r" % (pressure_altitude,))
    if not _finite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be a finite value > 0 K")
    if v_ias is None:
        v_ias = FLYBY_REFERENCE_CAS
    if not _finite(v_ias) or v_ias < 0.0:
        raise ValueError("pass airspeed must be a finite value >= 0 m/s")
    dh = geometric_height - pressure_altitude
    rho = _isa_pressure(pressure_altitude) / (R_AIR * temperature)
    dp_s = rho * G0 * dh
    qc_total = impact_pressure_from_cas(v_ias) + dp_s
    return calibrated_airspeed(qc_total) - v_ias


def gps_doublet_tas(v1g, v2g):
    """True airspeed V_tas in m/s from a GPS ground speed doublet.

    Two runs on reciprocal headings at the same indicated airspeed give
    ground speeds V1g and V2g; with a steady wind the mean
    V_tas = (V1g + V2g)/2 cancels the along-track wind component.
    Raises ValueError for non-finite or negative ground speeds.
    """
    if not _finite(v1g) or v1g < 0.0:
        raise ValueError("ground speed V1g must be a finite value >= 0 m/s")
    if not _finite(v2g) or v2g < 0.0:
        raise ValueError("ground speed V2g must be a finite value >= 0 m/s")
    return 0.5 * (v1g + v2g)


def tas_to_cas(v_tas, density_ratio):
    """Calibrated airspeed V_cas in m/s from the true airspeed.

    V_cas = V_tas * sqrt(rho/rho0) with density_ratio = rho/rho0 the
    density ratio at the test altitude. Raises ValueError for a non-finite
    or negative true airspeed and for a density ratio <= 0.
    """
    if not _finite(v_tas) or v_tas < 0.0:
        raise ValueError("true airspeed must be a finite value >= 0 m/s")
    if not _finite(density_ratio) or density_ratio <= 0.0:
        raise ValueError("density ratio must be a finite value > 0")
    return v_tas * math.sqrt(density_ratio)


def _pec_interp(curve, v_ias):
    """Piecewise linear PEC interpolation at one indicated airspeed.

    curve is the dict from fit_pec_curve. Outside the calibrated span the
    end segment slope is extended. Internal helper.
    """
    breakpoints = curve["breakpoints"]
    knot_dvp = curve["knot_dvp"]
    slopes = curve["slopes"]
    n = len(breakpoints)
    if v_ias <= breakpoints[0]:
        return knot_dvp[0] + slopes[0] * (v_ias - breakpoints[0])
    if v_ias >= breakpoints[-1]:
        return knot_dvp[-1] + slopes[-1] * (v_ias - breakpoints[-1])
    for i in range(n - 1):
        if breakpoints[i] <= v_ias <= breakpoints[i + 1]:
            return knot_dvp[i] + slopes[i] * (v_ias - breakpoints[i])
    raise ValueError("interpolation failed at %r" % (v_ias,))  # pragma: no cover


def fit_pec_curve(points):
    """Fit the piecewise linear PEC curve to the calibrated test points.

    points is a sequence of (v_ias, dVp) reduced observations in m/s;
    repeat passes at a scheduled indicated airspeed are combined by their
    least squares mean into one knot, and the knots are joined by exact
    piecewise linear segments. Returns a curve dict with 'breakpoints'
    (knot indicated airspeeds), 'knot_dvp' (knot corrections, parallel),
    'slopes' (segment slopes between consecutive knots), and
    'residual_rms' (RMS of the observations about the fitted curve, the
    PEC data quality metric; zero when every point is a single clean
    observation). Raises ValueError for an empty point list, fewer than
    two distinct indicated airspeeds, non-finite values, or negative
    indicated airspeeds.
    """
    if not points:
        raise ValueError("at least two calibrated points are required, got none")
    if len(points) < 2:
        raise ValueError("at least two calibrated points are required, got %d" % len(points))
    obs = []
    for v_ias, dvp in points:
        if not _finite(v_ias) or v_ias < 0.0:
            raise ValueError("point indicated airspeed must be finite and >= 0 m/s")
        if not _finite(dvp):
            raise ValueError("point position error must be finite")
        obs.append((float(v_ias), float(dvp)))
    obs.sort(key=lambda p: p[0])
    # Combine repeat passes at the same scheduled indicated airspeed (least
    # squares mean per knot) before joining the knots with linear segments.
    knots = []
    group_ias = obs[0][0]
    group_dvp = [obs[0][1]]
    for v_ias, dvp in obs[1:]:
        same = abs(v_ias - group_ias) < 1e-6 * max(1.0, abs(v_ias))
        if same:
            group_dvp.append(dvp)
        else:
            knots.append((group_ias, sum(group_dvp) / len(group_dvp)))
            group_ias = v_ias
            group_dvp = [dvp]
    knots.append((group_ias, sum(group_dvp) / len(group_dvp)))
    breakpoints = [k[0] for k in knots]
    if len(breakpoints) < 2:
        raise ValueError(
            "at least two distinct indicated airspeeds are required for the PEC curve"
        )
    knot_dvp = [k[1] for k in knots]
    slopes = []
    for i in range(len(breakpoints) - 1):
        slopes.append((knot_dvp[i + 1] - knot_dvp[i]) / (breakpoints[i + 1] - breakpoints[i]))
    curve = {
        "breakpoints": breakpoints,
        "knot_dvp": knot_dvp,
        "slopes": slopes,
        "residual_rms": 0.0,
    }
    sq = 0.0
    for v_ias, dvp in obs:
        sq += (dvp - _pec_interp(curve, v_ias)) ** 2.0
    curve["residual_rms"] = math.sqrt(sq / len(obs))
    return curve


def pec_table(v_ias_list, curve):
    """Build the PEC table rows for a list of indicated airspeeds.

    v_ias_list must be strictly increasing (non-monotonic inputs are
    rejected) with finite non-negative entries. curve is the dict from
    fit_pec_curve. Returns a list of (v_ias, dVp, v_cas) tuples with
    v_cas = v_ias + dVp from the piecewise linear curve.
    """
    if not v_ias_list:
        raise ValueError("PEC table needs at least one indicated airspeed, got none")
    if not isinstance(curve, dict) or "breakpoints" not in curve or "slopes" not in curve:
        raise ValueError("curve must be the dict returned by fit_pec_curve")
    if len(curve["breakpoints"]) != len(curve["knot_dvp"]):
        raise ValueError("malformed curve: breakpoints and knot values must match")
    if len(curve["slopes"]) != len(curve["breakpoints"]) - 1:
        raise ValueError("malformed curve: slopes must join consecutive breakpoints")
    rows = []
    prev = None
    for v_ias in v_ias_list:
        if not _finite(v_ias) or v_ias < 0.0:
            raise ValueError("table airspeed must be finite and >= 0 m/s")
        if prev is not None and v_ias <= prev:
            raise ValueError(
                "table indicated airspeeds must be strictly increasing, got %r after %r"
                % (v_ias, prev)
            )
        prev = v_ias
        dvp = _pec_interp(curve, v_ias)
        rows.append((v_ias, dvp, v_ias + dvp))
    return rows


def pec_verdict(curve, planned_ias, methods):
    """PEC data quality verdict dict for the fitted curve.

    planned_ias is the list of scheduled test point indicated airspeeds
    and methods the list of reference methods actually flown (for example
    'tower-fly-by', 'trailing-cone', 'gps-ground-speed-doublet').
    Returns a dict with 'residual_rms' (from the curve), 'coverage' (the
    fraction of planned points whose indicated airspeed lies inside the
    calibrated span, breakpoints[0] to breakpoints[-1]), 'methods' (the
    method list), and 'verdict' ('adequate' when coverage >= COVERAGE_MIN
    and residual_rms <= RESIDUAL_RMS_MAX, else 'review'). Raises
    ValueError for an empty planned list, an empty method list, or
    non-finite planned airspeeds.
    """
    if not planned_ias:
        raise ValueError("planned test point list must not be empty")
    if not methods:
        raise ValueError("method list must not be empty")
    for v in planned_ias:
        if not _finite(v) or v < 0.0:
            raise ValueError("planned airspeed must be finite and >= 0 m/s")
    breakpoints = curve["breakpoints"]
    lo, hi = breakpoints[0], breakpoints[-1]
    covered = sum(1 for v in planned_ias if lo <= v <= hi)
    coverage = covered / len(planned_ias)
    residual_rms = curve["residual_rms"]
    verdict = "adequate" if coverage >= COVERAGE_MIN and residual_rms <= RESIDUAL_RMS_MAX else "review"
    return {
        "residual_rms": residual_rms,
        "coverage": coverage,
        "methods": list(methods),
        "verdict": verdict,
        "planned": len(planned_ias),
        "calibrated_span": (lo, hi),
    }

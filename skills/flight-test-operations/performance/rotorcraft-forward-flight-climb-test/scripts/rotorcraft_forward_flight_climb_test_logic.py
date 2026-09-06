"""rotorcraft_forward_flight_climb_test_logic.py

Deterministic pure-stdlib reduction of a FAR 29 rotorcraft forward-flight
climb flight test from measured data (name and convention frame only, no
verbatim rule text). Workflow steps of the leaf SKILL.md that this module
implements:

- step 1 (fix the test configuration and the test-day atmosphere): the
  isa_sigma / pressure_altitude_sigma / density_altitude_m atmosphere
  functions fix sigma_test, sigma_ref and the density altitude of the day
  from the recorded pressure altitude and outside air temperature.
- step 2 (reduce every run window to the measured rate of climb): the
  least-squares slope of the pressure-altitude-versus-time window of each
  steady climb run through roc_from_altitude_samples.
- step 3 (convert the recorded airspeeds to true airspeed): TAS from the
  recorded calibrated airspeed at the test-day density ratio through
  tas_from_cas.
- step 4 (correct the measured rates of climb): the rho/weight ratio law
  through corrected_roc, weight ratio linearly and the day's density-ratio
  deviation to the half power.
- step 5 (identify the best-rate-of-climb speed): the discrete maximum
  with neighbour check and the parabola-vertex refinement through
  vy_and_max_roc.
- step 6 (report the one-call sweep reduction): the chained
  reduce_forward_flight_climb_sweep producing the full report dict.
- step 7 (reduce the Vy-schedule runs to the climb ceilings): the service
  ceiling at the 0.5 m/s rotorcraft convention and the absolute ceiling
  through climb_ceilings.

Every input is a flight test measurement: recorder pressure-altitude and
time samples, calibrated airspeed, test gross weight, reference weight,
pressure altitude, outside air temperature. No RNG anywhere; math only.
"""

import math

# --- module constants (pinned by the spec, identical to the prep anchor) --
T0 = 288.15            # ISA sea-level temperature, K
LAPSE = 0.0065         # ISA troposphere lapse rate, K/m
G0 = 9.80665           # standard gravity, m/s^2
R_AIR = 287.053        # specific gas constant of air, J/(kg K)
TROPOPAUSE_M = 11000.0
K_DELTA = G0 / (R_AIR * LAPSE)        # 5.25588..., ISA delta exponent
K_SIGMA = K_DELTA - 1.0               # 4.25588..., ISA sigma exponent
ALT_INV = T0 / LAPSE                  # 44330.77, m
KTAS_TO_MPS = 1852.0 / 3600.0         # 0.514444...
ROC_DENS_EXP = 0.5                    # rho/weight ratio law exponent
SERVICE_ROC_MPS = 0.5                 # service ceiling threshold, m/s
MIN_SAMPLES = 2
SWEEP_MIN = 4
SWEEP_MAX = 40


def isa_sigma(press_alt_m):
    """Standard-day density ratio sigma_ISA at a pressure altitude in the
    ISA troposphere. Workflow step 1. ValueError outside [0, 11000] m."""
    if not (0.0 <= press_alt_m <= TROPOPAUSE_M):
        raise ValueError("pressure altitude outside the 0-11000 m model domain")
    theta = 1.0 - LAPSE * press_alt_m / T0
    return theta ** K_SIGMA


def pressure_altitude_sigma(press_alt_m, oat_c):
    """Test-day density ratio of the recorded day: the ISA pressure ratio
    delta at the pressure altitude times T0/(OAT + 273.15), carrying the
    altitude AND temperature content of the day. Workflow step 1.
    ValueErrors: pressure altitude outside [0, 11000] m, OAT outside
    [-60, 60] C."""
    if not (0.0 <= press_alt_m <= TROPOPAUSE_M):
        raise ValueError("pressure altitude outside the 0-11000 m model domain")
    if not (-60.0 <= oat_c <= 60.0):
        raise ValueError("outside air temperature outside the -60 to 60 C domain")
    theta = 1.0 - LAPSE * press_alt_m / T0
    delta = theta ** K_DELTA
    return delta * T0 / (oat_c + 273.15)


def density_altitude_m(press_alt_m, oat_c):
    """Density altitude of the test day: the ISA altitude whose density
    ratio equals the test-day sigma (invert sigma_ISA). Workflow step 1.
    ValueErrors as pressure_altitude_sigma plus one when the test-day
    sigma falls below the tropopause sigma (density altitude above the
    model domain)."""
    sigma = pressure_altitude_sigma(press_alt_m, oat_c)
    if sigma < isa_sigma(TROPOPAUSE_M):
        raise ValueError("density altitude above the tropopause model domain")
    theta_da = sigma ** (1.0 / K_SIGMA)
    return ALT_INV * (1.0 - theta_da)


def tas_from_cas(cas_kt, sigma):
    """True airspeed in kt from the recorded calibrated airspeed and the
    density ratio: V = CAS/sqrt(sigma). Workflow step 3. ValueErrors:
    cas <= 0 (a forward-flight run has positive airspeed), sigma <= 0."""
    if cas_kt <= 0.0:
        raise ValueError("calibrated airspeed must be positive")
    if sigma <= 0.0:
        raise ValueError("density ratio must be positive")
    return cas_kt / math.sqrt(sigma)


def _lsq_slope(y_list, x_list):
    """Least-squares slope, intercept and r-squared of y against x."""
    n = len(x_list)
    sx = sum(x_list)
    sy = sum(y_list)
    sxx = sum(x * x for x in x_list)
    sxy = sum(x * y for x, y in zip(x_list, y_list))
    denom = n * sxx - sx * sx
    if denom == 0.0:
        raise ValueError("zero fit denominator: all time samples equal")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    ss_res = sum((y - (intercept + slope * x)) ** 2
                 for x, y in zip(x_list, y_list))
    ss_tot = sum((y - sy / n) ** 2 for y in y_list)
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return slope, intercept, r_squared


def roc_from_altitude_samples(press_alt_m_list, time_s_list):
    """Measured rate of climb in m/s of one steady climb run: the
    least-squares slope of the pressure altitude window against time,
    positive while climbing, with the fit quality r_squared (1.0 when the
    window has zero scatter). Workflow step 2. ValueErrors: unequal list
    lengths, fewer than MIN_SAMPLES points, a zero fit denominator (all
    time samples equal), a fitted slope <= 0 (a level or descending
    window is not a climb run)."""
    if len(press_alt_m_list) != len(time_s_list):
        raise ValueError("altitude and time lists must be equal length")
    if len(time_s_list) < MIN_SAMPLES:
        raise ValueError("at least 2 samples required")
    slope, _intercept, r_squared = _lsq_slope(press_alt_m_list, time_s_list)
    if slope <= 0.0:
        raise ValueError("no climb in the window: fitted slope not positive")
    return {"roc_mps": slope, "r_squared": r_squared}


def corrected_roc(roc_mps, w_test_n, w_ref_n, sigma_test, sigma_ref):
    """Correct a measured rate of climb to the reference weight and the
    standard day at the run altitude with the rho/weight ratio law:
    ROC_corr = ROC * (W_test/W_ref) * (sigma_ref/sigma_test)**0.5. The
    weight enters linearly through the excess specific power
    (ROC = P_ex/W); the day's density deviation enters to the half power
    because near the best-rate speed the rotor induced power, the
    dominant term of the climb power at fixed weight and airspeed, scales
    with the inverse square root of the density ratio while the
    flat-rated turboshaft available power does not lapse within its
    rating band. On the standard day at the reference weight the
    correction is identity. A negative measured rate (a run that sank at
    full power near the limit) is a valid input and corrects through the
    same law. Workflow step 4. ValueErrors: w_test or w_ref <= 0,
    sigma_test or sigma_ref <= 0."""
    if w_test_n <= 0.0 or w_ref_n <= 0.0:
        raise ValueError("weights must be positive")
    if sigma_test <= 0.0 or sigma_ref <= 0.0:
        raise ValueError("density ratios must be positive")
    return roc_mps * (w_test_n / w_ref_n) * (
        (sigma_ref / sigma_test) ** ROC_DENS_EXP)


def vy_and_max_roc(tas_kt_list, roc_mps_list):
    """Best-rate-of-climb speed Vy and the maximum corrected rate of
    climb of the corrected ROC-versus-TAS curve: the discrete maximum
    with a neighbour check, refined by the vertex of the parabola through
    the peak triplet when the peak is interior and above both neighbours
    (Newton form y = y0 + d1*(x - x0) + a*(x - x0)*(x - x1), vertex at
    xv = (x0 + x1)/2 - d1/(2*a) when a < 0 and xv lies inside the
    triplet). An endpoint peak reports Vy at the band edge with
    peak_bracketed False (the sweep did not bracket Vy). vy_mps is the
    kt value through KTAS_TO_MPS; max_roc_mps is the curve value at Vy
    (the vertex value when the vertex was used, the discrete value
    otherwise). Workflow step 5. ValueErrors: unequal list lengths, fewer
    than 3 points, TAS not strictly increasing, a maximum corrected ROC
    <= 0 (no positive climb capability anywhere in the tested band)."""
    if len(tas_kt_list) != len(roc_mps_list):
        raise ValueError("speed and ROC lists must be equal length")
    if len(tas_kt_list) < 3:
        raise ValueError("at least 3 sweep points required")
    if any(b <= a for a, b in zip(tas_kt_list, tas_kt_list[1:])):
        raise ValueError("speeds must be strictly increasing")
    peak = max(range(len(roc_mps_list)), key=roc_mps_list.__getitem__)
    if roc_mps_list[peak] <= 0.0:
        raise ValueError("no positive climb capability across the tested band")
    peak_bracketed = 0 < peak < len(tas_kt_list) - 1
    vertex_used = False
    vy = tas_kt_list[peak]
    vy_max = roc_mps_list[peak]
    if peak_bracketed:
        x0, x1, x2 = tas_kt_list[peak - 1:peak + 2]
        y0, y1, y2 = roc_mps_list[peak - 1:peak + 2]
        if y1 > y0 and y1 > y2:
            d1 = (y1 - y0) / (x1 - x0)
            d2 = (y2 - y1) / (x2 - x1)
            a_curv = (d2 - d1) / (x2 - x0)
            if a_curv < 0.0:
                xv = 0.5 * (x0 + x1) - d1 / (2.0 * a_curv)
                if x0 <= xv <= x2:
                    yv = y0 + d1 * (xv - x0) + a_curv * (xv - x0) * (xv - x1)
                    vy = xv
                    vy_max = yv
                    vertex_used = True
    return {"vy_kt": vy, "vy_mps": vy * KTAS_TO_MPS,
            "max_roc_mps": vy_max, "peak_bracketed": peak_bracketed,
            "vertex_used": vertex_used}


def climb_ceilings(roc_corr_mps_list, density_alt_m_list):
    """Climb ceilings from the corrected best-rate-of-climb points of the
    Vy-schedule runs across density altitudes: linear interpolation on
    the measured density-altitude band of the first crossing of the
    0.5 m/s service-ceiling threshold (the FAR 29 climb-demonstration
    framing, about 100 ft/min) and of the zero crossing (the absolute
    ceiling). No crossing inside the tested band returns None for that
    ceiling. Workflow step 7. ValueErrors: unequal list lengths, fewer
    than 2 points, density altitudes not strictly increasing, any
    negative density altitude."""
    if len(roc_corr_mps_list) != len(density_alt_m_list):
        raise ValueError("ROC and density altitude lists must be equal length")
    if len(density_alt_m_list) < 2:
        raise ValueError("at least 2 density altitude points required")
    if any(b <= a for a, b in zip(density_alt_m_list, density_alt_m_list[1:])):
        raise ValueError("density altitudes must be strictly increasing")
    if any(da < 0.0 for da in density_alt_m_list):
        raise ValueError("density altitudes must be non-negative")

    def _crossing(threshold):
        for i in range(len(density_alt_m_list) - 1):
            r0 = roc_corr_mps_list[i] - threshold
            r1 = roc_corr_mps_list[i + 1] - threshold
            if r0 >= 0.0 and r1 <= 0.0:
                if r0 == 0.0:
                    return density_alt_m_list[i]
                if r1 == 0.0:
                    return density_alt_m_list[i + 1]
                frac = r0 / (r0 - r1)
                return (density_alt_m_list[i]
                        + frac * (density_alt_m_list[i + 1]
                                  - density_alt_m_list[i]))
        return None

    return {"service_ceiling_m": _crossing(SERVICE_ROC_MPS),
            "absolute_ceiling_m": _crossing(0.0)}


def reduce_forward_flight_climb_sweep(sweep_cas_kt, roc_meas_mps, w_test_n,
                                      w_ref_n, press_alt_m, oat_c):
    """One-call reduction of the forward-flight climb sweep (workflow
    steps 1, 3, 4, 5 and 6 in chain): the test-day density ratios and
    density altitude, the TAS per run from the recorded calibrated
    airspeeds, the corrected rate of climb per run, then Vy and the
    maximum corrected rate of climb. The per-run measured rates come from
    roc_from_altitude_samples on the run windows (workflow steps 2-3), or
    directly from level-accelerated runs pre-reduced by the total-energy
    method of the level-acceleration-test leaf. Returns exactly the dict
    keys sigma_test, sigma_ref, density_altitude_m, tas_kt,
    roc_corr_mps, vy_kt, vy_mps, max_roc_corr_mps, peak_bracketed,
    vertex_used. ValueErrors: unequal list lengths, fewer than SWEEP_MIN
    or more than SWEEP_MAX runs (the 4-40 sweep convention), calibrated
    airspeeds not strictly increasing, any non-positive CAS, and every
    underlying guard of the chained functions."""
    if len(sweep_cas_kt) != len(roc_meas_mps):
        raise ValueError("CAS and measured ROC lists must be equal length")
    if not (SWEEP_MIN <= len(sweep_cas_kt) <= SWEEP_MAX):
        raise ValueError("sweep must hold 4 to 40 runs")
    if any(b <= a for a, b in zip(sweep_cas_kt, sweep_cas_kt[1:])):
        raise ValueError("calibrated airspeeds must be strictly increasing")
    sigma_test = pressure_altitude_sigma(press_alt_m, oat_c)
    sigma_ref = isa_sigma(press_alt_m)
    da_m = density_altitude_m(press_alt_m, oat_c)
    tas_kt = [tas_from_cas(cas, sigma_test) for cas in sweep_cas_kt]
    roc_corr = [corrected_roc(roc, w_test_n, w_ref_n, sigma_test, sigma_ref)
                for roc in roc_meas_mps]
    vy = vy_and_max_roc(tas_kt, roc_corr)
    return {"sigma_test": sigma_test, "sigma_ref": sigma_ref,
            "density_altitude_m": da_m, "tas_kt": tas_kt,
            "roc_corr_mps": roc_corr, "vy_kt": vy["vy_kt"],
            "vy_mps": vy["vy_mps"], "max_roc_corr_mps": vy["max_roc_mps"],
            "peak_bracketed": vy["peak_bracketed"],
            "vertex_used": vy["vertex_used"]}

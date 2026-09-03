"""Buffet boundary flight test analysis logic (pure stdlib).

Maps the buffet boundary of a transport airplane from flight test pull-up
and steady-turn sweeps: schedule load factor samples at each Mach of a
sweep, detect buffet onset from the vertical accelerometer RMS rise above
a threshold, convert the onset load factor to the boundary lift
coefficient, fit a linear boundary line over the tested Mach band, and
score the buffet margin at a cruise condition against a maneuver buffet
target load factor.

The RMS floor, RMS rise per g and the 0.02 g onset threshold are
documented typical engineering criteria, not regulation values. FAR/CS-25
are referenced for buffet and vibration context by name and paraphrase
only.

All inputs and outputs are SI: kg, m, Pa, kg/m3, m/s; load factors in g.
"""

import math

# --- module constants (documented typical engineering criteria) -----------
G0 = 9.80665  # standard gravity, m/s^2
RMS_ONSET_G = 0.02  # buffet-onset vertical accelerometer RMS threshold, g
RMS_FLOOR_G = 0.004  # RMS level below buffet onset, g
RMS_RISE_PER_G = 0.4  # RMS rise per g of load factor above onset, g/g

# ISA model constants
T0_K = 288.15  # sea level temperature, K
P0_PA = 101325.0  # sea level pressure, Pa
LAPSE_K_PER_M = 0.0065  # troposphere lapse rate, K/m
GAMMA = 1.4  # ratio of specific heats, air
R_GAS = 287.05  # specific gas constant, J/(kg K)
TROPOPAUSE_M = 11000.0  # tropopause altitude, m
T_TROPOPAUSE_K = 216.65  # tropopause temperature, K
P_TROPOPAUSE_PA = 22632.1  # tropopause pressure, Pa
EXP_INDEX = 5.25588  # ISA pressure exponent

# Valid Mach band for the dynamic pressure model.
MACH_MIN = 0.1
MACH_MAX = 2.0


def isa_state(altitude_m):
    """Return dict {T, P, rho} of the ISA atmosphere at altitude_m.

    T in K, P in Pa, rho in kg/m3. Troposphere below 11000 m, isothermal
    stratosphere above. ValueError on negative altitude.
    """
    if altitude_m < 0:
        raise ValueError("altitude below zero is non-physical")
    if altitude_m < TROPOPAUSE_M:
        temp = T0_K - LAPSE_K_PER_M * altitude_m
        press = P0_PA * (temp / T0_K) ** EXP_INDEX
    else:
        temp = T_TROPOPAUSE_K
        press = P_TROPOPAUSE_PA * math.exp(
            -G0 * (altitude_m - TROPOPAUSE_M) / (R_GAS * T_TROPOPAUSE_K)
        )
    rho = press / (R_GAS * temp)
    return {"T": temp, "P": press, "rho": rho}


def dynamic_pressure(mach, altitude_m):
    """Return the free stream dynamic pressure q = 0.5 * rho * V^2 (Pa).

    V = mach * a with a the ISA speed of sound at altitude_m. ValueError
    on mach outside the valid (0.1, 2.0) band.
    """
    if not (MACH_MIN < mach < MACH_MAX):
        raise ValueError("mach outside the valid (0.1, 2.0) band")
    state = isa_state(altitude_m)
    speed_of_sound = math.sqrt(GAMMA * R_GAS * state["T"])
    vel = mach * speed_of_sound
    return 0.5 * state["rho"] * vel * vel


def onset_detect(samples, onset_rms_g=RMS_ONSET_G):
    """Detect the buffet-onset load factor from (n, rms_g) samples.

    samples is a list of (load_factor, rms_g) tuples sorted by increasing
    load factor. The rms sequence must be non-decreasing in load factor.
    The onset load factor is the linear interpolation of the first
    crossing of onset_rms_g between two consecutive samples. ValueError
    on fewer than two samples, non-monotonic rms, a non-positive
    threshold, or no crossing within the sampled band.
    """
    if onset_rms_g <= 0:
        raise ValueError("onset rms threshold must be positive")
    if samples is None or len(samples) < 2:
        raise ValueError("rms table needs at least two samples")
    for idx in range(1, len(samples)):
        if samples[idx][1] < samples[idx - 1][1]:
            raise ValueError("non-monotonic rms table")
    for idx, (load_factor, rms_g) in enumerate(samples):
        if rms_g >= onset_rms_g:
            if idx == 0:
                # Onset already reached at the first sample: report the
                # first sampled load factor as the upper bound.
                return load_factor
            n_prev, rms_prev = samples[idx - 1]
            frac = (onset_rms_g - rms_prev) / (rms_g - rms_prev)
            return n_prev + frac * (load_factor - n_prev)
    raise ValueError("no onset crossing")


def boundary_lift_coefficient(onset_n, q, weight_kg, wing_area_m2):
    """Return the buffet-boundary lift coefficient at one Mach.

    cl_buf = onset_n * W / (q * S) with W = weight_kg * G0. ValueError on
    non-positive weight, area, q, or a negative onset load factor.
    """
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be positive")
    if q <= 0:
        raise ValueError("dynamic pressure must be positive")
    if onset_n < 0:
        raise ValueError("onset load factor cannot be negative")
    weight_n = weight_kg * G0
    return onset_n * weight_n / (q * wing_area_m2)


def fit_boundary_line(mach_list, cl_buf_list, cruise_mach=None):
    """Least-squares linear fit cl_buf = slope * mach + intercept.

    Local 2x2 normal equations over the tested Mach band. Returns
    {slope, intercept, cl_at_cruise, residuals}; cl_at_cruise is the line
    evaluated at cruise_mach, or None when cruise_mach is omitted (the
    cruise Mach is supplied by the caller when a margin is wanted).
    ValueError on fewer than two points or mismatched list lengths.
    """
    if mach_list is None or cl_buf_list is None:
        raise ValueError("fit needs mach and cl_buf lists")
    if len(mach_list) != len(cl_buf_list):
        raise ValueError("mismatched table lengths")
    if len(mach_list) < 2:
        raise ValueError("fit needs at least two points")
    n = float(len(mach_list))
    sum_x = sum(mach_list)
    sum_y = sum(cl_buf_list)
    sum_xx = sum(m * m for m in mach_list)
    sum_xy = sum(m * c for m, c in zip(mach_list, cl_buf_list))
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        raise ValueError("fit degenerate: all mach values identical")
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    residuals = [
        c - (slope * m + intercept) for m, c in zip(mach_list, cl_buf_list)
    ]
    cl_at_cruise = None
    if cruise_mach is not None:
        cl_at_cruise = slope * cruise_mach + intercept
    return {
        "slope": slope,
        "intercept": intercept,
        "cl_at_cruise": cl_at_cruise,
        "residuals": residuals,
    }


def buffet_margin(n_buf_at_cruise, target_n):
    """Return the buffet margin n_buf_at_cruise - target_n in g."""
    if target_n <= 0:
        raise ValueError("buffet target load factor must be positive")
    return n_buf_at_cruise - target_n


def analyze(inputs):
    """Run the buffet boundary analysis over one test point schedule.

    inputs keys: weight_kg, wing_area_m2, mach_list, altitude_m,
    rms_table (one (n, rms_g) sample list per Mach), cruise_mach, and
    optional onset_rms_g (default RMS_ONSET_G) and buffet_target_n
    (default 1.3).

    Returns per-Mach q, onset_n and cl_buf, the fitted boundary line with
    cl_buf at cruise_mach, n_buf_cruise, the margin against
    buffet_target_n and the verdict string. ValueError on non-physical
    inputs, mismatched table lengths, and cruise_mach outside the fitted
    Mach band (extrapolation guard).
    """
    weight_kg = inputs["weight_kg"]
    wing_area_m2 = inputs["wing_area_m2"]
    mach_list = list(inputs["mach_list"])
    altitude_m = inputs["altitude_m"]
    rms_table = inputs["rms_table"]
    cruise_mach = inputs["cruise_mach"]
    onset_rms_g = inputs.get("onset_rms_g", RMS_ONSET_G)
    target_n = inputs.get("buffet_target_n", 1.3)

    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be positive")
    if target_n <= 0:
        raise ValueError("buffet target load factor must be positive")
    if len(mach_list) != len(rms_table):
        raise ValueError("mismatched table lengths")
    if len(mach_list) < 2:
        raise ValueError("at least two mach points are required")
    if cruise_mach < min(mach_list) or cruise_mach > max(mach_list):
        raise ValueError("cruise mach outside the fitted band")

    points = []
    cl_buf_list = []
    for mach, samples in zip(mach_list, rms_table):
        q = dynamic_pressure(mach, altitude_m)
        onset_n = onset_detect(samples, onset_rms_g)
        cl_buf = boundary_lift_coefficient(
            onset_n, q, weight_kg, wing_area_m2
        )
        points.append(
            {"mach": mach, "q": q, "onset_n": onset_n, "cl_buf": cl_buf}
        )
        cl_buf_list.append(cl_buf)

    fit = fit_boundary_line(mach_list, cl_buf_list, cruise_mach)
    q_cruise = dynamic_pressure(cruise_mach, altitude_m)
    cl_buf_cruise = fit["cl_at_cruise"]
    n_buf_cruise = (
        cl_buf_cruise * q_cruise * wing_area_m2 / (weight_kg * G0)
    )
    margin_n = buffet_margin(n_buf_cruise, target_n)
    verdict = "buffet-margin-pass" if margin_n >= 0.0 else "buffet-margin-fail"
    return {
        "points": points,
        "fit": fit,
        "cruise_mach": cruise_mach,
        "q_cruise": q_cruise,
        "cl_buf_cruise": cl_buf_cruise,
        "n_buf_cruise": n_buf_cruise,
        "margin_n": margin_n,
        "buffet_target_n": target_n,
        "verdict": verdict,
    }

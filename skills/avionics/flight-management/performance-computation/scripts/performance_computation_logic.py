#!/usr/bin/env python3
"""FMS performance computation logic (paraphrase, simplified model).

Common-knowledge summary (standards-map.yaml: do-178c reference-only,
far-25/cs-25 public airworthiness context): a flight management system
selects an economic (ECON) cruise speed from the cost index, which is
the ratio of time cost per hour to fuel cost per kilogram. A higher
cost index favors speed (less time, more fuel); a lower cost index
favors fuel economy. The speed that minimizes total cost per nautical
mile is found where the marginal fuel cost of flying faster balances
the marginal time saving. Step-climb logic trades the extra climb fuel
against the lower cruise fuel at a higher flight level, and vertical
navigation (VNAV) computes the top of descent from the altitude to
lose and the descent gradient, corrected for wind.

The aerodynamic model here is a documented simplified three-term drag
form (parasite, induced, compressibility) with ISA atmosphere, stdlib
only and fully deterministic. Coefficients are order-of-magnitude for
a mid-size transport and must be calibrated per aircraft against the
FMS performance manual; no proprietary performance tables are
reproduced.
"""

import math

# --- Physical constants (SI) ---
G0 = 9.80665            # standard gravity, m/s^2
R_AIR = 287.0529        # specific gas constant for air, J/(kg K)
GAMMA = 1.4             # ratio of specific heats for air
ISA_SL_TEMP = 288.15    # ISA sea level temperature, K
ISA_SL_PRESSURE = 101325.0  # ISA sea level pressure, Pa
ISA_LAPSE = -0.0065     # ISA temperature lapse rate below tropopause, K/m
TROPOPAUSE_M = 11000.0  # ISA tropopause altitude, m
FT_TO_M = 0.3048
NM_TO_M = 1852.0
KTS_TO_MS = 0.5144444444
MS_TO_KTS = 1.943844492
FT_PER_NM = 6076.1154   # feet per nautical mile

# --- Aircraft defaults (mid-size transport, order-of-magnitude) ---
# Calibrate per aircraft; see module docstring.
WING_AREA_M2 = 122.0
CD0 = 0.0210            # zero-lift (parasite) drag coefficient
OSWALD_E = 0.82         # Oswald span efficiency
ASPECT_RATIO = 9.4
SFC_KG_N_S = 0.0000165  # thrust specific fuel consumption, kg/(N s)
COMPRESSIBILITY = 2.4e-16  # transonic drag-rise coefficient (V^7 term)

M_MIN = 0.70            # ECON Mach lower clamp (below long-range cruise)
M_MMO = 0.82            # maximum operating Mach upper clamp
CLIMB_FUEL_KG_PER_FT = 0.07  # extra fuel per foot of step climb, kg/ft

_NEWTON_MAX_ITER = 60
_NEWTON_TOL = 1e-9


# ---------------------------------------------------------------------------
# ISA atmosphere helpers
# ---------------------------------------------------------------------------

def isa_temperature_k(altitude_ft):
    """ISA temperature in kelvin at altitude_ft (feet, may be negative)."""
    h = altitude_ft * FT_TO_M
    if h <= TROPOPAUSE_M:
        return ISA_SL_TEMP + ISA_LAPSE * h
    return ISA_SL_TEMP + ISA_LAPSE * TROPOPAUSE_M  # isothermal stratosphere


def isa_density_kgm3(altitude_ft):
    """ISA air density in kg/m^3 at altitude_ft (feet)."""
    h = altitude_ft * FT_TO_M
    if h <= TROPOPAUSE_M:
        t = ISA_SL_TEMP + ISA_LAPSE * h
        p = ISA_SL_PRESSURE * (t / ISA_SL_TEMP) ** (-G0 / (R_AIR * ISA_LAPSE))
    else:
        t_tropo = ISA_SL_TEMP + ISA_LAPSE * TROPOPAUSE_M
        p_tropo = ISA_SL_PRESSURE * (t_tropo / ISA_SL_TEMP) ** (
            -G0 / (R_AIR * ISA_LAPSE)
        )
        p = p_tropo * math.exp(
            -G0 * (h - TROPOPAUSE_M) / (R_AIR * t_tropo)
        )
        t = t_tropo
    return p / (R_AIR * t)


def speed_of_sound_kts(altitude_ft):
    """Speed of sound in knots at altitude_ft (feet)."""
    t = isa_temperature_k(altitude_ft)
    return math.sqrt(GAMMA * R_AIR * t) * MS_TO_KTS


def mach_from_tas(tas_kts, altitude_ft):
    """Mach number from true airspeed in knots at altitude_ft."""
    if tas_kts <= 0.0:
        raise ValueError("tas_kts must be positive: %r" % (tas_kts,))
    return tas_kts / speed_of_sound_kts(altitude_ft)


def tas_from_mach(mach, altitude_ft):
    """True airspeed in knots for a Mach number at altitude_ft."""
    if mach <= 0.0:
        raise ValueError("mach must be positive: %r" % (mach,))
    return mach * speed_of_sound_kts(altitude_ft)


# ---------------------------------------------------------------------------
# Cost index
# ---------------------------------------------------------------------------

def cost_index(time_cost_per_hour, fuel_cost_per_kg):
    """Cost index = time cost per hour / fuel cost per kg (kg/hour).

    The cost index trades time against fuel: a high value makes the
    FMS fly faster, a low value makes it fly more slowly. Both inputs
    must be strictly positive (a zero time cost would make the index
    meaningless for ECON selection).
    """
    if time_cost_per_hour < 0.0:
        raise ValueError(
            "time_cost_per_hour must be >= 0: %r" % (time_cost_per_hour,)
        )
    if fuel_cost_per_kg <= 0.0:
        raise ValueError(
            "fuel_cost_per_kg must be positive: %r" % (fuel_cost_per_kg,)
        )
    return time_cost_per_hour / fuel_cost_per_kg


# ---------------------------------------------------------------------------
# Drag / fuel model
# ---------------------------------------------------------------------------

def _fuel_per_nm_coeffs(weight_kg, altitude_ft):
    """Coefficients of the cruise fuel-per-nm model.

    fuel_per_nm(V) = SFC * NM_TO_M * (c1 * V + c2 / V^3 + c3 * V^7)
    with V in m/s: c1 is the parasite term (linear in V), c2 the
    induced term (falls with V^3), c3 the transonic drag-rise term
    (grows with V^7). Units work out to kg per nautical mile.
    """
    rho = isa_density_kgm3(altitude_ft)
    weight_n = weight_kg * G0
    c1 = 0.5 * rho * WING_AREA_M2 * CD0
    c2 = 2.0 * weight_n ** 2 / (rho * WING_AREA_M2 * math.pi * OSWALD_E * ASPECT_RATIO)
    return c1, c2, COMPRESSIBILITY


def fuel_per_nm(weight_kg, altitude_ft, tas_kts):
    """Cruise fuel burn in kg per nautical mile at tas_kts (knots)."""
    if weight_kg <= 0.0:
        raise ValueError("weight_kg must be positive: %r" % (weight_kg,))
    if tas_kts <= 0.0:
        raise ValueError("tas_kts must be positive: %r" % (tas_kts,))
    c1, c2, c3 = _fuel_per_nm_coeffs(weight_kg, altitude_ft)
    v = tas_kts * KTS_TO_MS
    return SFC_KG_N_S * NM_TO_M * (c1 * v + c2 / v ** 3 + c3 * v ** 7)


def max_range_speed_kts(weight_kg, altitude_ft):
    """TAS in knots at which fuel per nm is minimum (max-range speed).

    Solves d(fuel_per_nm)/dV = 0 by Newton iteration from a parasite-
    only estimate; deterministic and stdlib only.
    """
    c1, c2, c3 = _fuel_per_nm_coeffs(weight_kg, altitude_ft)
    a = SFC_KG_N_S * NM_TO_M
    # g(V) = a*(c1 - 3 c2/V^4 + 7 c3 V^6); root is the max-range speed.
    def g(v):
        return c1 - 3.0 * c2 / v ** 4 + 7.0 * c3 * v ** 6

    def gp(v):
        return 12.0 * c2 / v ** 5 + 42.0 * c3 * v ** 5

    v = (3.0 * c2 / c1) ** 0.25  # parasite + induced only
    for _ in range(_NEWTON_MAX_ITER):
        f = g(v)
        df = gp(v)
        if df == 0.0:
            break
        step = f / df
        v -= step
        if v <= 1.0:
            v = 1.0
        if abs(step) < _NEWTON_TOL:
            break
    return v * MS_TO_KTS


# ---------------------------------------------------------------------------
# ECON speed selection
# ---------------------------------------------------------------------------

def _econ_tas_ms(ci_kg_per_h, weight_kg, altitude_ft):
    """TAS in m/s minimizing total cost per nm (fuel + CI * time)."""
    c1, c2, c3 = _fuel_per_nm_coeffs(weight_kg, altitude_ft)
    a = SFC_KG_N_S * NM_TO_M
    # Time per nm in hours: t(V) = (NM_TO_M / V) / 3600.
    # Total cost per nm: C(V) = a*(c1 V + c2/V^3 + c3 V^7) + ci * t(V).
    # dC/dV = a*(c1 - 3 c2/V^4 + 7 c3 V^6) - ci*NM_TO_M/(3600 V^2).
    time_scale = NM_TO_M / 3600.0

    def g(v):
        return a * (c1 - 3.0 * c2 / v ** 4 + 7.0 * c3 * v ** 6) - ci_kg_per_h * time_scale / v ** 2

    def gp(v):
        return a * (12.0 * c2 / v ** 5 + 42.0 * c3 * v ** 5) + 2.0 * ci_kg_per_h * time_scale / v ** 3

    v = max_range_speed_kts(weight_kg, altitude_ft) * KTS_TO_MS
    for _ in range(_NEWTON_MAX_ITER):
        f = g(v)
        df = gp(v)
        if df == 0.0:
            break
        step = f / df
        v -= step
        if v <= 1.0:
            v = 1.0
        if abs(step) < _NEWTON_TOL:
            break
    return v


def econ_mach_from_cost_index(ci_kg_per_h, weight_kg, altitude_ft):
    """ECON cruise Mach for a cost index (kg/h), weight and altitude.

    Clamps the unconstrained optimum into [M_MIN, M_MMO]. A cost index
    of zero selects the max-range (minimum fuel per nm) speed. Negative
    cost index raises ValueError.
    """
    if ci_kg_per_h < 0.0:
        raise ValueError(
            "ci_kg_per_h must be >= 0: %r" % (ci_kg_per_h,)
        )
    if weight_kg <= 0.0:
        raise ValueError("weight_kg must be positive: %r" % (weight_kg,))
    v = _econ_tas_ms(ci_kg_per_h, weight_kg, altitude_ft)
    mach = v / math.sqrt(GAMMA * R_AIR * isa_temperature_k(altitude_ft))
    return min(M_MMO, max(M_MIN, mach))


def econ_speed_summary(ci_kg_per_h, weight_kg, altitude_ft):
    """ECON selection detail: Mach, TAS, fuel per nm, time per nm.

    Returns a dict with the clamped Mach, the corresponding TAS in
    knots, the fuel burn per nm, the time per nm in hours, and the
    total fuel-equivalent cost per nm. Deterministic.
    """
    mach = econ_mach_from_cost_index(ci_kg_per_h, weight_kg, altitude_ft)
    tas = tas_from_mach(mach, altitude_ft)
    return {
        "mach": mach,
        "tas_kts": tas,
        "fuel_per_nm_kg": fuel_per_nm(weight_kg, altitude_ft, tas),
        "time_per_nm_h": 1.0 / tas,
        "cost_per_nm_kg": fuel_per_nm(weight_kg, altitude_ft, tas)
        + ci_kg_per_h / tas,
    }


def fuel_time_trade(ci_kg_per_h, weight_kg, altitude_ft, mach_a, mach_b,
                    distance_nm):
    """Fuel and time for two candidate cruise speeds over distance_nm.

    Returns a dict with fuel and time for both speeds, the time saved
    by the faster speed, the extra fuel it burns, and the net cost
    change in fuel-equivalent kg (extra_fuel + CI * delta_time).
    """
    if distance_nm <= 0.0:
        raise ValueError("distance_nm must be positive: %r" % (distance_nm,))
    if ci_kg_per_h < 0.0:
        raise ValueError("ci_kg_per_h must be >= 0: %r" % (ci_kg_per_h,))
    if mach_a <= 0.0 or mach_b <= 0.0:
        raise ValueError("candidate Mach numbers must be positive")
    if mach_a == mach_b:
        raise ValueError("candidate Mach numbers must differ")

    def leg(mach):
        tas = tas_from_mach(mach, altitude_ft)
        fuel = fuel_per_nm(weight_kg, altitude_ft, tas) * distance_nm
        hours = distance_nm / tas
        return fuel, hours

    fuel_a, time_a = leg(mach_a)
    fuel_b, time_b = leg(mach_b)
    if mach_b > mach_a:
        fast, slow = mach_b, mach_a
        fuel_fast, fuel_slow = fuel_b, fuel_a
        time_fast, time_slow = time_b, time_a
    else:
        fast, slow = mach_a, mach_b
        fuel_fast, fuel_slow = fuel_a, fuel_b
        time_fast, time_slow = time_a, time_b
    extra_fuel = fuel_fast - fuel_slow
    time_saved = time_slow - time_fast
    return {
        "mach_a": mach_a,
        "mach_b": mach_b,
        "fuel_a_kg": fuel_a,
        "fuel_b_kg": fuel_b,
        "time_a_h": time_a,
        "time_b_h": time_b,
        "faster_mach": fast,
        "extra_fuel_kg": extra_fuel,
        "time_saved_h": time_saved,
        "cost_delta_kg": extra_fuel + ci_kg_per_h * (-time_saved),
    }


# ---------------------------------------------------------------------------
# Step climb
# ---------------------------------------------------------------------------

def step_climb_benefit(weight_kg, fl_a_ft, fl_b_ft, distance_nm,
                       mach=None, climb_fuel_per_ft=CLIMB_FUEL_KG_PER_FT,
                       step_margin_kg=0.0):
    """Trip fuel comparison for a step climb from fl_a_ft to fl_b_ft.

    Benefit = cruise fuel at the lower level minus cruise fuel at the
    higher level minus the climb fuel penalty. A positive benefit
    exceeding step_margin_kg supports the step climb. Raises ValueError
    if fl_b_ft <= fl_a_ft (a step climb must gain altitude), if weight
    or distance are non-positive, or if the climb fuel factor is not
    positive.
    """
    if weight_kg <= 0.0:
        raise ValueError("weight_kg must be positive: %r" % (weight_kg,))
    if distance_nm <= 0.0:
        raise ValueError("distance_nm must be positive: %r" % (distance_nm,))
    if fl_b_ft <= fl_a_ft:
        raise ValueError(
            "fl_b_ft must exceed fl_a_ft: %r <= %r" % (fl_b_ft, fl_a_ft)
        )
    if climb_fuel_per_ft <= 0.0:
        raise ValueError(
            "climb_fuel_per_ft must be positive: %r" % (climb_fuel_per_ft,)
        )
    if mach is None:
        mach = econ_mach_from_cost_index(0.0, weight_kg, fl_a_ft)
    cruise_fuel_a = fuel_per_nm(weight_kg, fl_a_ft, tas_from_mach(mach, fl_a_ft)) * distance_nm
    cruise_fuel_b = fuel_per_nm(weight_kg, fl_b_ft, tas_from_mach(mach, fl_b_ft)) * distance_nm
    climb_penalty = climb_fuel_per_ft * (fl_b_ft - fl_a_ft)
    benefit = cruise_fuel_a - cruise_fuel_b - climb_penalty
    return {
        "fl_a_ft": fl_a_ft,
        "fl_b_ft": fl_b_ft,
        "cruise_fuel_a_kg": cruise_fuel_a,
        "cruise_fuel_b_kg": cruise_fuel_b,
        "climb_penalty_kg": climb_penalty,
        "benefit_kg": benefit,
        "step_advised": benefit > step_margin_kg,
    }


# ---------------------------------------------------------------------------
# VNAV top of descent
# ---------------------------------------------------------------------------

def top_of_descent(cruise_alt_ft, target_alt_ft, fpa_deg=3.0,
                   tas_kts=None, headwind_kts=0.0):
    """Top-of-descent geometry for a constant flight path angle.

    Returns a dict with the altitude to lose (feet), the air gradient
    (ft/nm), the air distance and the wind-corrected ground distance
    (nm) from the TOD to the target. With a headwind the aircraft
    covers ground more slowly, so the ground distance is longer; a
    tailwind shortens it. An altitude to lose of zero or less yields a
    zero TOD distance. fpa_deg must be positive, tas_kts positive when
    given (otherwise the speed of sound at cruise altitude is used),
    and headwind_kts must be below the true airspeed.
    """
    alt_to_lose = cruise_alt_ft - target_alt_ft
    if alt_to_lose <= 0.0:
        return {
            "alt_to_lose_ft": 0.0,
            "air_gradient_ft_per_nm": math.tan(math.radians(fpa_deg)) * FT_PER_NM,
            "air_distance_nm": 0.0,
            "ground_distance_nm": 0.0,
            "fpa_deg": fpa_deg,
        }
    if fpa_deg <= 0.0:
        raise ValueError("fpa_deg must be positive: %r" % (fpa_deg,))
    if tas_kts is None:
        tas_kts = speed_of_sound_kts(cruise_alt_ft) * 0.78
    if tas_kts <= 0.0:
        raise ValueError("tas_kts must be positive: %r" % (tas_kts,))
    if headwind_kts >= tas_kts:
        raise ValueError(
            "headwind_kts must be below tas_kts: %r >= %r"
            % (headwind_kts, tas_kts)
        )
    gradient = math.tan(math.radians(fpa_deg)) * FT_PER_NM
    air_distance = alt_to_lose / gradient
    groundspeed = tas_kts - headwind_kts
    ground_distance = air_distance * tas_kts / groundspeed
    return {
        "alt_to_lose_ft": alt_to_lose,
        "air_gradient_ft_per_nm": gradient,
        "air_distance_nm": air_distance,
        "ground_distance_nm": ground_distance,
        "fpa_deg": fpa_deg,
    }

"""Hydrogen peroxide monopropellant thruster station logic (propulsion, rocket pack).

Pure stdlib (math only), deterministic, closed form plus one bisection.
Model: liquid high-test hydrogen peroxide (HTP) at mass concentration w
(fraction H2O2 in water, the water dilution) decomposes catalytically over a
silver catalyst bed, 2 H2O2(l) -> 2 H2O(g) + O2(g), exothermic. The dilution
water is carried through as vaporized steam in the products. The adiabatic
decomposition (chamber) temperature T_c solves the Hess-law energy balance at
the 298.15 K reference state: the net heat released per mole of H2O2 fed
(products all vapor) equals the product sensible heat from T_REF to T_c,
using documented quadratic heat-capacity fits cp(T) for H2O(g) and O2(g). The
frozen steam-oxygen product mixture then expands isentropically to vacuum
(gamma evaluated at the chamber state): v_e = sqrt(2 g/(g-1) R_mix T_c),
vacuum specific impulse Isp = v_e / G0, and propellant mass flow at a
vacuum thrust point mdot = F / v_e (no exit pressure term). The
silver-catalyst-bed temperature band verdict is advisory and reference-only.
"""

import math

# ---------------------------------------------------------------------------
# Module constants (every fixed number lives here)
# ---------------------------------------------------------------------------
G0 = 9.80665                      # standard gravity, m/s^2 (sibling rocket convention)
T_REF = 298.15                    # reference state, K (liquid H2O2/H2O feed, ideal gas products)
R_UNIV = 8.314462618              # universal gas constant, J/(mol K)
R_UNIV_KMOL = 8314.462618         # universal gas constant, J/(kmol K)
M_H2O2 = 34.01468                 # g/mol H2O2 (H = 1.00794, O = 15.9994)
M_H2O = 18.01528                  # g/mol H2O
M_O2 = 31.9988                    # g/mol O2
DELTA_HF_H2O2_LIQ = -187780.0     # J/mol formation enthalpy H2O2(l) at T_REF (NIST)
DELTA_HF_H2O_LIQ = -285830.0      # J/mol formation enthalpy H2O(l) at T_REF (NIST)
DELTA_HF_H2O_GAS = -241826.4      # J/mol formation enthalpy H2O(g) at T_REF (NIST)
Q_BASE = -(DELTA_HF_H2O_GAS - DELTA_HF_H2O2_LIQ)  # 54046.4 J/mol, gas-product release
DELTA_H_VAP_H2O_298 = DELTA_HF_H2O_GAS - DELTA_HF_H2O_LIQ  # 44003.6 J/mol, water vap load
# cp(T) = a + b*T + c*T^2 in J/(mol K), exact quadratic through the documented
# NIST-JANAF (Chase 1998) reference points (298.15, 1000, 2000 K).
CP_H2O = (30.150107726136, 0.011714838411, -0.000000594946)  # 33.59, 41.27, 51.20 J/(mol K)
CP_O2 = (26.190482217943, 0.011559276673, -0.000002889759)   # 29.38, 34.86, 37.75
T_SOLVE_HI = 2600.0               # bisection upper bracket, K (pure-peroxide limit ~1271 K inside)
DECOMPOSITION_SUPPORT_MIN_W = 0.85  # documented silver-catalyst HTP service floor, mass fraction
# Silver-catalyst-bed operating band, K. Published reference data (823.15 K,
# 550 C, to 1234.93 K, 961.78 C, the silver melting point), reference-only,
# never enforced: the verdict is advisory.
SILVER_BED_BAND_LO = 823.15
SILVER_BED_BAND_HI = 1234.93


# ---------------------------------------------------------------------------
# Pure functions (the public API)
# ---------------------------------------------------------------------------
def dilution_water_moles(w):
    """Moles of liquid dilution water per mole of H2O2 fed, at peroxide
    concentration w (mass fraction H2O2 in water): (1-w)/w * M_H2O2/M_H2O.
    ValueError if w is not finite or lies outside [0.85, 1.0]."""
    if not math.isfinite(w) or w < DECOMPOSITION_SUPPORT_MIN_W or w > 1.0:
        raise ValueError("peroxide concentration must lie in [0.85, 1.0]")
    return (1.0 - w) / w * M_H2O2 / M_H2O


def product_mole_numbers(w):
    """Moles of H2O and O2 in the decomposed products per mole H2O2 fed:
    (1 + n_w, 0.5), from 2 H2O2 -> 2 H2O + O2 plus the vaporized dilution
    water. ValueError domain as dilution_water_moles."""
    n_w = dilution_water_moles(w)
    return 1.0 + n_w, 0.5


def total_product_moles(w):
    """Total moles of gas products per mole H2O2 fed: n_tot = 1.5 + n_w.
    ValueError domain as dilution_water_moles."""
    n_h2o, n_o2 = product_mole_numbers(w)
    return n_h2o + n_o2


def decomposition_heat_released(w):
    """Net heat released by the decomposition at T_REF, J per mole H2O2 fed
    (Hess-law balance, products all vapor): Q(w) = Q_BASE - n_w *
    DELTA_H_VAP_H2O_298, linear and strictly increasing in w. ValueError
    domain as dilution_water_moles."""
    n_w = dilution_water_moles(w)
    return Q_BASE - n_w * DELTA_H_VAP_H2O_298


def _cp(species, t_k):
    """cp(T) = a + b*T + c*T^2, J/(mol K). species in {'H2O','O2'}."""
    a, b, c = {"H2O": CP_H2O, "O2": CP_O2}[species]
    return a + b * t_k + c * t_k * t_k


def product_heat_capacity(w, t_k):
    """Product mixture heat capacity Sigma n_i cp_i(T) at temperature t_k,
    J/(K mol H2O2 fed). ValueError domain as dilution_water_moles plus t_k
    not positive and finite."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    n_h2o, n_o2 = product_mole_numbers(w)
    return n_h2o * _cp("H2O", t_k) + n_o2 * _cp("O2", t_k)


def product_sensible_heat(w, t_k):
    """Product sensible heat from T_REF to t_k, J per mole H2O2 fed (the
    integral of product_heat_capacity from T_REF to t_k). ValueError domain
    as product_heat_capacity."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    n_h2o, n_o2 = product_mole_numbers(w)
    total = 0.0
    for n, coeff in ((n_h2o, CP_H2O), (n_o2, CP_O2)):
        a, b, c = coeff
        total += n * (a * (t_k - T_REF)
                      + 0.5 * b * (t_k * t_k - T_REF * T_REF)
                      + (c / 3.0) * (t_k ** 3 - T_REF ** 3))
    return total


def decomposition_temperature(w):
    """Adiabatic decomposition (chamber) temperature T_c in K: the root of
    product_sensible_heat(T) = decomposition_heat_released(w), found by
    bisection on [T_REF, T_SOLVE_HI] (300 iterations, monotone increasing
    left side, so the root is unique). ValueError domain as
    dilution_water_moles, plus a defensive ValueError if the solved root is
    not physical."""
    q = decomposition_heat_released(w)
    lo, hi = T_REF, T_SOLVE_HI
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if product_sensible_heat(w, mid) < q:
            lo = mid
        else:
            hi = mid
    t_c = 0.5 * (lo + hi)
    if not math.isfinite(t_c) or t_c <= T_REF:
        raise ValueError("solved decomposition temperature is not physical")
    return t_c


def product_mole_fractions(w):
    """Steam-oxygen mole fractions (y_h2o, y_o2) of the product mixture,
    summing to 1. ValueError domain as dilution_water_moles."""
    n_h2o, n_o2 = product_mole_numbers(w)
    n_tot = n_h2o + n_o2
    return n_h2o / n_tot, n_o2 / n_tot


def product_mass_fractions(w):
    """Steam-oxygen mass fractions (x_h2o, x_o2) of the product mixture,
    summing to 1 (x_o2 the oxygen fraction carried in the exhaust).
    ValueError domain as dilution_water_moles."""
    n_h2o, n_o2 = product_mole_numbers(w)
    m_h2o = n_h2o * M_H2O
    m_o2 = n_o2 * M_O2
    m_tot = m_h2o + m_o2
    return m_h2o / m_tot, m_o2 / m_tot


def mixture_molar_mass(w):
    """Mean molar mass of the product mixture, g/mol: feed mass per mole
    H2O2 fed / n_tot (the propellant mass is conserved). ValueError domain
    as dilution_water_moles."""
    n_w = dilution_water_moles(w)
    feed_mass = M_H2O2 + n_w * M_H2O
    n_tot = total_product_moles(w)
    return feed_mass / n_tot


def mixture_gas_constant(w):
    """Specific gas constant of the product mixture, J/(kg K):
    R_UNIV_KMOL / mixture_molar_mass. ValueError domain as
    dilution_water_moles."""
    return R_UNIV_KMOL / mixture_molar_mass(w)


def mixture_gamma(w, t_k):
    """Isentropic exponent of the product mixture at t_k (frozen
    composition, mole-weighted cp): gamma = cp_mix / (cp_mix - R_UNIV).
    ValueError domain as dilution_water_moles plus t_k not positive and
    finite."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    n_h2o, n_o2 = product_mole_numbers(w)
    n_tot = n_h2o + n_o2
    cp_mix = (n_h2o * _cp("H2O", t_k) + n_o2 * _cp("O2", t_k)) / n_tot
    return cp_mix / (cp_mix - R_UNIV)


def vacuum_exhaust_velocity(w):
    """Fully expanded vacuum exhaust velocity of the steam-oxygen product
    mixture, m/s: sqrt(2 gamma/(gamma-1) R_mix T_c) with T_c =
    decomposition_temperature(w), gamma = mixture_gamma(w, T_c) and R_mix =
    mixture_gas_constant(w). Frozen-composition isentropic expansion.
    ValueError domain as dilution_water_moles."""
    t_c = decomposition_temperature(w)
    gamma = mixture_gamma(w, t_c)
    r_mix = mixture_gas_constant(w)
    return math.sqrt(2.0 * gamma / (gamma - 1.0) * r_mix * t_c)


def vacuum_specific_impulse(w, g0=G0):
    """Vacuum specific impulse, s: vacuum_exhaust_velocity(w) / g0.
    ValueError domain as dilution_water_moles plus g0 not positive and
    finite."""
    if not math.isfinite(g0) or g0 <= 0.0:
        raise ValueError("g0 must be positive and finite")
    return vacuum_exhaust_velocity(w) / g0


def propellant_mass_flow(thrust_n, w):
    """Propellant mass flow required at the vacuum thrust point, kg/s:
    thrust_n / vacuum_exhaust_velocity(w) (vacuum thrust F = mdot v_e, no
    pressure term). ValueError if thrust_n is not positive and finite or w
    out of domain."""
    if not math.isfinite(thrust_n) or thrust_n <= 0.0:
        raise ValueError("thrust must be positive and finite")
    return thrust_n / vacuum_exhaust_velocity(w)


def within_silver_catalyst_bed_band(t_k):
    """Advisory verdict: True iff t_k lies inside the documented
    silver-catalyst-bed operating band [SILVER_BED_BAND_LO,
    SILVER_BED_BAND_HI] K. The band is reported reference-only, never
    enforced. ValueError if t_k is not positive and finite."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    return SILVER_BED_BAND_LO <= t_k <= SILVER_BED_BAND_HI

"""Hydrazine monopropellant thruster station logic (propulsion, rocket pack).

Pure stdlib (math only), deterministic, closed form plus one bisection.
Model: liquid hydrazine at T_REF decomposes catalytically to (4/3) NH3 +
(1/3) N2 (exothermic, heat of decomposition released) while a documented
fraction x of the ammonia formed dissociates endothermically into N2 and H2
(ammonia-dissociation-fraction input). Products per mole N2H4 fed:

    n_NH3 = (4/3)(1-x), n_N2 = 1/3 + (2/3)x, n_H2 = 2x.

The adiabatic decomposition (chamber) temperature T_c solves the Hess-law
energy balance: net heat released Q(x) equals the product sensible heat from
T_REF to T_c, using documented quadratic heat-capacity fits cp(T) for NH3,
N2 and H2. The frozen product mixture then expands isentropically to vacuum
(gamma evaluated at the chamber state): v_e = sqrt(2 g/(g-1) R_mix T_c),
vacuum specific impulse Isp = v_e / G0, and propellant mass flow at a
vacuum thrust point mdot = F / v_e (no exit pressure term). The
catalyst-bed temperature band verdict is advisory and reference-only.
"""

import math

# ---------------------------------------------------------------------------
# Module constants (every fixed number lives here)
# ---------------------------------------------------------------------------
G0 = 9.80665                      # standard gravity, m/s^2 (sibling rocket convention)
T_REF = 298.15                    # reference state, K (liquid N2H4 feed, ideal gas products)
R_UNIV = 8.314462618              # universal gas constant, J/(mol K)
R_UNIV_KMOL = 8314.462618         # universal gas constant, J/(kmol K)
HYDRAZINE_MOLAR_MASS = 32.04516   # g/mol N2H4 (also kg/kmol)
NH3_MOLAR_MASS = 17.03052         # g/mol = 14.0067 + 3*1.00794
N2_MOLAR_MASS = 28.0134           # g/mol = 2*14.0067
H2_MOLAR_MASS = 2.01588           # g/mol = 2*1.00794
DELTA_HF_NH3_GAS = -45.94e3       # J/mol formation enthalpy NH3(g) at T_REF
DELTA_HF_N2H4_LIQ = 50.63e3       # J/mol formation enthalpy N2H4(l) at T_REF
DELTA_H_DISS_NH3 = 45.94e3        # J/mol NH3(g), endothermic dissociation enthalpy at T_REF
# cp(T) = a + b*T + c*T^2 in J/(mol K), exact quadratic through the documented
# reference points (298.15, 1000, 2000 K), 298-2000 K reference data.
CP_NH3 = (27.1444498084, 3.018332529e-02, -6.227775096e-06)  # 35.59, 51.10, 62.60 J/(mol K)
CP_N2 = (27.2889646381, 6.451553043e-03, -1.040517681e-06)    # 29.12, 32.70, 36.03
CP_H2 = (28.4133255181, 1.280011723e-03, 5.066627591e-07)     # 28.84, 30.20, 33.00
T_SOLVE_HI = 2600.0               # bisection upper bracket, K (frozen limit ~1734 K is inside)
# Catalyst-bed continuous operating band, K. Reported from published hydrazine
# thruster catalyst-bed design monographs (800 to 1150 C class continuous
# steady-firing duty), reference-only, never enforced: the verdict is advisory.
CATALYST_BED_BAND_LO = 1073.15
CATALYST_BED_BAND_HI = 1423.15


# ---------------------------------------------------------------------------
# Pure functions (the public API)
# ---------------------------------------------------------------------------
def decomposition_products(x):
    """Moles of NH3, N2, H2 in the decomposed products per mole N2H4 fed, at
    ammonia dissociation fraction x (fraction of the (4/3) NH3 formed that
    dissociates). Returns (n_nh3, n_n2, n_h2). ValueError if x is not finite
    or lies outside [0, 1]."""
    if not math.isfinite(x) or x < 0.0 or x > 1.0:
        raise ValueError("ammonia dissociation fraction must lie in [0, 1]")
    n_nh3 = (4.0 / 3.0) * (1.0 - x)
    n_n2 = 1.0 / 3.0 + (2.0 / 3.0) * x
    n_h2 = 2.0 * x
    return n_nh3, n_n2, n_h2


def total_product_moles(x):
    """Total moles of gas products per mole N2H4 fed: 5/3 + (4/3)x (1.6667
    frozen, 3.0 fully dissociated). ValueError domain as decomposition_products."""
    n_nh3, n_n2, n_h2 = decomposition_products(x)
    return n_nh3 + n_n2 + n_h2


def decomposition_heat_released(x):
    """Net heat released by the decomposition at T_REF, J per mole N2H4 fed:
    Q(x) = Q_BASE - (4/3) x DELTA_H_DISS_NH3 with Q_BASE the exothermic
    release of N2H4(l) to (4/3) NH3 + (1/3) N2, 111883.333... J/mol. Linear
    and strictly decreasing in x. ValueError domain as decomposition_products."""
    decomposition_products(x)          # domain check only
    q_base = -((4.0 / 3.0) * DELTA_HF_NH3_GAS - DELTA_HF_N2H4_LIQ)
    return q_base - (4.0 / 3.0) * x * DELTA_H_DISS_NH3


def _cp(species, t_k):
    """cp(T) = a + b*T + c*T^2, J/(mol K). species in {'NH3','N2','H2'}."""
    a, b, c = {"NH3": CP_NH3, "N2": CP_N2, "H2": CP_H2}[species]
    return a + b * t_k + c * t_k * t_k


def product_heat_capacity(x, t_k):
    """Product mixture heat capacity Sigma n_i cp_i(T) at temperature t_k,
    J/(K mol N2H4). ValueError domain as decomposition_products plus t_k not
    positive and finite."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    n_nh3, n_n2, n_h2 = decomposition_products(x)
    return (n_nh3 * _cp("NH3", t_k) + n_n2 * _cp("N2", t_k) + n_h2 * _cp("H2", t_k))


def _sensible_heat(x, t_k):
    """Product sensible heat from T_REF to t_k, J per mole N2H4 fed (the
    integral of product_heat_capacity from T_REF to t_k)."""
    n_nh3, n_n2, n_h2 = decomposition_products(x)
    total = 0.0
    for n, coeff in ((n_nh3, CP_NH3), (n_n2, CP_N2), (n_h2, CP_H2)):
        a, b, c = coeff
        total += n * (a * (t_k - T_REF)
                      + 0.5 * b * (t_k * t_k - T_REF * T_REF)
                      + (c / 3.0) * (t_k ** 3 - T_REF ** 3))
    return total


def decomposition_temperature(x):
    """Adiabatic decomposition (chamber) temperature T_c in K: the root of
    sensible_heat(T) = decomposition_heat_released(x), found by bisection on
    [T_REF, T_SOLVE_HI] (300 iterations, monotone increasing left side, so
    the root is unique). ValueError domain as decomposition_products."""
    decomposition_products(x)          # domain check
    q = decomposition_heat_released(x)
    lo, hi = T_REF, T_SOLVE_HI
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if _sensible_heat(x, mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def mixture_molar_mass(x):
    """Mean molar mass of the product mixture, g/mol: hydrazine molar mass /
    n_tot (the propellant mass is conserved; only the mole count changes).
    ValueError domain as decomposition_products."""
    return HYDRAZINE_MOLAR_MASS / total_product_moles(x)


def mixture_gas_constant(x):
    """Specific gas constant of the product mixture, J/(kg K):
    R_UNIV_KMOL / mixture_molar_mass. ValueError domain as decomposition_products."""
    return R_UNIV_KMOL / mixture_molar_mass(x)


def mixture_gamma(x, t_k):
    """Isentropic exponent of the product mixture at t_k (frozen composition,
    mole-weighted cp): gamma = cp_mix / (cp_mix - R_UNIV). ValueError domain
    as decomposition_products plus t_k not positive and finite."""
    if not math.isfinite(t_k) or t_k <= 0.0:
        raise ValueError("temperature must be positive and finite")
    n_nh3, n_n2, n_h2 = decomposition_products(x)
    n_tot = n_nh3 + n_n2 + n_h2
    cp_mix = (n_nh3 * _cp("NH3", t_k) + n_n2 * _cp("N2", t_k)
              + n_h2 * _cp("H2", t_k)) / n_tot
    return cp_mix / (cp_mix - R_UNIV)


def vacuum_exhaust_velocity(x):
    """Fully expanded vacuum exhaust velocity of the decomposed mixture,
    m/s: sqrt(2 gamma/(gamma-1) R_mix T_c) with T_c = decomposition_temperature(x),
    gamma = mixture_gamma(x, T_c) and R_mix = mixture_gas_constant(x).
    Frozen-composition isentropic expansion. ValueError domain as
    decomposition_products."""
    t_c = decomposition_temperature(x)
    gamma = mixture_gamma(x, t_c)
    r_mix = mixture_gas_constant(x)
    return math.sqrt(2.0 * gamma / (gamma - 1.0) * r_mix * t_c)


def vacuum_specific_impulse(x, g0=G0):
    """Vacuum specific impulse, s: vacuum_exhaust_velocity(x) / g0.
    ValueError domain as decomposition_products plus g0 not positive and finite."""
    if not math.isfinite(g0) or g0 <= 0.0:
        raise ValueError("g0 must be positive and finite")
    return vacuum_exhaust_velocity(x) / g0


def propellant_mass_flow(thrust_n, x):
    """Propellant mass flow required at the vacuum thrust point, kg/s:
    thrust_n / vacuum_exhaust_velocity(x) (vacuum thrust F = mdot v_e, no
    pressure term). ValueError if thrust_n is not positive and finite or x
    out of domain."""
    if not math.isfinite(thrust_n) or thrust_n <= 0.0:
        raise ValueError("thrust must be positive and finite")
    return thrust_n / vacuum_exhaust_velocity(x)


def within_catalyst_bed_band(t_k):
    """Advisory verdict: True iff t_k lies inside the documented catalyst-bed
    continuous operating band [CATALYST_BED_BAND_LO, CATALYST_BED_BAND_HI] K.
    The band is reported reference-only, never enforced. ValueError if t_k
    is not finite."""
    if not math.isfinite(t_k):
        raise ValueError("temperature must be finite")
    return CATALYST_BED_BAND_LO <= t_k <= CATALYST_BED_BAND_HI

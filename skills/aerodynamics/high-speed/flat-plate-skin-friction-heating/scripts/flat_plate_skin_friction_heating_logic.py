"""Flat plate skin friction heating logic: non-stagnation surface heating.

Eckert reference-temperature skin friction and Reynolds-analogy style
convective heat transfer for a compressible boundary layer on a flat
plate (or vehicle skin) away from the stagnation point. Pure Python
stdlib, deterministic, offline.

The module implements the classical flat-plate boundary-layer model:
recovery factor (laminar sqrt(PR), turbulent PR**(1/3)), adiabatic wall
temperature, Eckert reference temperature, Sutherland viscosity,
local skin friction coefficient at the reference conditions, and the
cold-wall heat flux from a Reynolds-analogy style heat transfer
coefficient. SI units throughout (Pa, K, kg/m3, m/s, W/m2).

Module constants: GAMMA, R, CP, PR, MU_REF, T_REF, SUTH_S per the leaf
spec (air at high-speed flight conditions).
"""

import math

# Gas and boundary-layer constants for air, SI units.
GAMMA = 1.4        # ratio of specific heats
R = 287.0          # specific gas constant, J/(kg K)
CP = 1005.0        # specific heat at constant pressure, J/(kg K)
PR = 0.71          # Prandtl number
MU_REF = 1.716e-5  # reference dynamic viscosity, Pa s
T_REF = 273.15     # reference temperature, K
SUTH_S = 110.4     # Sutherland constant, K

# Correlation coefficients (Eckert reference temperature and local
# skin friction, classical flat-plate compressible boundary layer).
ECKERT_M2_COEF = 0.032   # Mach-squared term in the reference temperature
ECKERT_TW_COEF = 0.58    # wall-to-freestream temperature ratio term
LAMINAR_CF_COEF = 0.664  # Blasius local skin friction numerator
TURB_CF_COEF = 0.0592    # 1/7-power turbulent local skin friction numerator
TURB_CF_EXP = 0.2        # 1/5 exponent in the turbulent Re term

# Valid flow regimes.
REGIMES = ("laminar", "turbulent")


def _check_regime(regime):
    """Return regime after raising ValueError on an unknown string."""
    if regime not in REGIMES:
        raise ValueError(
            "regime must be 'laminar' or 'turbulent', got %r" % (regime,))
    return regime


def _check_mach(M):
    """Raise ValueError unless 0 < M < 20 (compressible flow range)."""
    if M <= 0 or M >= 20:
        raise ValueError(
            "Mach number must be in (0, 20), got %r" % (M,))


def _check_mach_allow_zero(M):
    """Raise ValueError unless 0 <= M < 20 (zero-speed limit allowed)."""
    if M < 0 or M >= 20:
        raise ValueError(
            "Mach number must be in [0, 20), got %r" % (M,))


def recovery_factor(regime):
    """Recovery factor r for a flat-plate boundary layer.

    Laminar: sqrt(PR) ~ 0.8426. Turbulent: PR**(1/3) ~ 0.8921.
    Raises ValueError if regime is not 'laminar' or 'turbulent'.
    """
    _check_regime(regime)
    if regime == "laminar":
        return math.sqrt(PR)
    return PR ** (1.0 / 3.0)


def adiabatic_wall_temperature(M, T_inf, regime):
    """Adiabatic (recovery) wall temperature, K.

    T_aw = T_inf * (1 + r * (GAMMA - 1) / 2 * M**2).
    M = 0 is admitted as the zero-speed limit (identity T_aw = T_inf);
    raises ValueError for M < 0, M >= 20, T_inf <= 0 or a bad regime.
    """
    _check_mach_allow_zero(M)
    if T_inf <= 0:
        raise ValueError(
            "freestream static temperature must be positive, got %r" % (T_inf,))
    r = recovery_factor(regime)
    return T_inf * (1.0 + r * (GAMMA - 1.0) / 2.0 * M ** 2)


def reference_temperature(M, T_inf, T_wall):
    """Eckert reference temperature T_star, K.

    T_star = T_inf * (1 + 0.032 * M**2 + 0.58 * (T_wall / T_inf - 1)).
    Raises ValueError for M outside (0, 20), T_inf <= 0 or T_wall <= 0.
    """
    _check_mach(M)
    if T_inf <= 0:
        raise ValueError(
            "freestream static temperature must be positive, got %r" % (T_inf,))
    if T_wall <= 0:
        raise ValueError(
            "wall temperature must be positive, got %r" % (T_wall,))
    return T_inf * (
        1.0
        + ECKERT_M2_COEF * M ** 2
        + ECKERT_TW_COEF * (T_wall / T_inf - 1.0)
    )


def sutherland_viscosity(T):
    """Dynamic viscosity at temperature T by the Sutherland law, Pa s.

    mu = MU_REF * (T / T_REF)**1.5 * (T_REF + SUTH_S) / (T + SUTH_S).
    Raises ValueError if T <= 0.
    """
    if T <= 0:
        raise ValueError(
            "temperature must be positive, got %r" % (T,))
    return (
        MU_REF
        * (T / T_REF) ** 1.5
        * (T_REF + SUTH_S)
        / (T + SUTH_S)
    )


def _edge_velocity(M, T_inf):
    """Boundary-layer edge velocity U_e = M * sqrt(GAMMA * R * T_inf)."""
    return M * math.sqrt(GAMMA * R * T_inf)


def skin_friction_coefficient(M, T_inf, p_inf, T_wall, x, regime):
    """Local skin friction coefficient at Eckert reference conditions.

    Returns dict {T_star, rho_star, mu_star, Re_star, Cf} with
    rho_star = p_inf / (R * T_star), Re_star = rho_star * U_e * x /
    mu_star; laminar Cf = 0.664 / sqrt(Re_star), turbulent
    Cf = 0.0592 / Re_star**0.2. Raises ValueError on non-physical
    inputs (M outside (0, 20), non-positive T_inf, p_inf, x, T_wall or
    a bad regime).
    """
    _check_mach(M)
    if T_inf <= 0:
        raise ValueError(
            "freestream static temperature must be positive, got %r" % (T_inf,))
    if p_inf <= 0:
        raise ValueError(
            "freestream static pressure must be positive, got %r" % (p_inf,))
    if T_wall <= 0:
        raise ValueError(
            "wall temperature must be positive, got %r" % (T_wall,))
    if x <= 0:
        raise ValueError(
            "running length x must be positive, got %r" % (x,))
    _check_regime(regime)

    T_star = reference_temperature(M, T_inf, T_wall)
    rho_star = p_inf / (R * T_star)
    mu_star = sutherland_viscosity(T_star)
    u_e = _edge_velocity(M, T_inf)
    re_star = rho_star * u_e * x / mu_star
    if regime == "laminar":
        cf = LAMINAR_CF_COEF / math.sqrt(re_star)
    else:
        cf = TURB_CF_COEF / re_star ** TURB_CF_EXP
    return {
        "T_star": T_star,
        "rho_star": rho_star,
        "mu_star": mu_star,
        "Re_star": re_star,
        "Cf": cf,
    }


def heat_transfer_coefficient(cf, rho_star, u_e):
    """Convective heat transfer coefficient by the Reynolds analogy.

    h_c = 0.5 * Cf * rho_star * U_e * CP, W/(m2 K). Raises ValueError
    if cf, rho_star or u_e is not positive.
    """
    if cf <= 0:
        raise ValueError(
            "skin friction coefficient must be positive, got %r" % (cf,))
    if rho_star <= 0:
        raise ValueError(
            "reference density must be positive, got %r" % (rho_star,))
    if u_e <= 0:
        raise ValueError(
            "edge velocity must be positive, got %r" % (u_e,))
    return 0.5 * cf * rho_star * u_e * CP


def cold_wall_heat_flux(M, T_inf, p_inf, T_wall, x, regime):
    """Cold-wall convective heat flux on a flat plate, W/m2.

    Chains recovery factor, adiabatic wall temperature, Eckert
    reference conditions, skin friction and the Reynolds-analogy heat
    transfer coefficient: q = h_c * (T_aw - T_wall). Returns dict
    {r, T_aw, T_star, Re_star, Cf, h_c, q_cold_wall}. Raises ValueError
    on non-physical inputs or a bad regime.
    """
    _check_mach(M)
    if T_inf <= 0:
        raise ValueError(
            "freestream static temperature must be positive, got %r" % (T_inf,))
    if p_inf <= 0:
        raise ValueError(
            "freestream static pressure must be positive, got %r" % (p_inf,))
    if T_wall <= 0:
        raise ValueError(
            "wall temperature must be positive, got %r" % (T_wall,))
    if x <= 0:
        raise ValueError(
            "running length x must be positive, got %r" % (x,))
    _check_regime(regime)

    r = recovery_factor(regime)
    t_aw = adiabatic_wall_temperature(M, T_inf, regime)
    sf = skin_friction_coefficient(M, T_inf, p_inf, T_wall, x, regime)
    u_e = _edge_velocity(M, T_inf)
    h_c = heat_transfer_coefficient(
        sf["Cf"], sf["rho_star"], u_e)
    return {
        "r": r,
        "T_aw": t_aw,
        "T_star": sf["T_star"],
        "Re_star": sf["Re_star"],
        "Cf": sf["Cf"],
        "h_c": h_c,
        "q_cold_wall": h_c * (t_aw - T_wall),
    }

"""Rough-wall turbulent skin friction on a flat plate (pure stdlib).

Estimates the turbulent skin-friction coefficient of a rough flat plate in
incompressible flow: smooth-wall turbulent baseline Cf from the local
Reynolds number, friction velocity from that baseline, roughness Reynolds
number k+ of the equivalent sand roughness, surface regime classification
(smooth, transitional, fully-rough), the Schlichting fully-rough
correlation for the fetch, a non-iterative coefficient selection with a
documented log-linear blend across the transitional band, and the
critical-roughness Reynolds trip test for a roughness element or trip
strip.

All module constants come from the wave-40 leaf spec; every function
raises ValueError on non-physical inputs. Deterministic, no RNG, no
network, math only.
"""

import math

# Module constants from the leaf spec: hydraulically smooth / fully rough
# bands for the roughness Reynolds number k+, the validity floor on the
# fetch ratio x / k_s for the fully-rough correlation, and the classical
# critical roughness Reynolds number for the trip test.
SMOOTH_K_PLUS = 5.0
FULLY_ROUGH_K_PLUS = 70.0
ROUGH_MIN_X_OVER_KS = 100.0
TRIP_RE_K = 600.0

# Fixed per-regime treatment strings returned in the note key.
NOTE_SMOOTH = (
    "surface hydraulically smooth: k+ below the 5.0 threshold, "
    "smooth-wall coefficient retained"
)
NOTE_TRANSITIONAL = (
    "transitional roughness: log-linear blend of the smooth baseline and "
    "the fully-rough value across the k+ band from 5.0 to 70.0"
)
NOTE_FULLY_ROUGH = (
    "fully-rough surface: Schlichting fully-rough correlation value "
    "used directly"
)


def classify_regime(k_s_plus):
    """Return the roughness regime string for a roughness Reynolds number.

    Workflow step 5: classify the surface on the classic bands, smooth
    below SMOOTH_K_PLUS, transitional across the band up to and including
    FULLY_ROUGH_K_PLUS, fully-rough above it.
    """
    if k_s_plus < 0.0:
        raise ValueError("k_s_plus must be non-negative")
    if k_s_plus < SMOOTH_K_PLUS:
        return "smooth"
    if k_s_plus <= FULLY_ROUGH_K_PLUS:
        return "transitional"
    return "fully-rough"


def smooth_turbulent_cf(re_x):
    """Return the smooth-wall turbulent local friction coefficient.

    Workflow step 2: 1/7 power-law turbulent local friction on a smooth
    plate, Cf = 0.0592 * re_x**-0.2, the anchor shared with the
    boundary-layer-theory and flat-plate-skin-friction-heating smooth
    correlations.
    """
    if re_x <= 0.0:
        raise ValueError("re_x must be positive")
    return 0.0592 * re_x ** -0.2


def friction_velocity(u_inf, cf):
    """Return the friction velocity u_tau = u_inf * sqrt(cf / 2).

    Workflow step 3: convert the skin-friction coefficient into the shear
    velocity that drives the roughness Reynolds number.
    """
    if u_inf <= 0.0:
        raise ValueError("u_inf must be positive")
    if cf <= 0.0:
        raise ValueError("cf must be positive")
    return u_inf * math.sqrt(cf / 2.0)


def sand_roughness_reynolds(rho, u_tau, k_s, mu):
    """Return the roughness Reynolds number k+ = rho * u_tau * k_s / mu.

    Workflow step 4: form the roughness Reynolds number of the equivalent
    sand roughness from the flow state and the sand-grain height.
    """
    if rho <= 0.0:
        raise ValueError("rho must be positive")
    if u_tau <= 0.0:
        raise ValueError("u_tau must be positive")
    if k_s <= 0.0:
        raise ValueError("k_s must be positive")
    if mu <= 0.0:
        raise ValueError("mu must be positive")
    return rho * u_tau * k_s / mu


def rough_wall_cf(x, k_s):
    """Return the Schlichting fully-rough turbulent friction value.

    Workflow step 6: cf_rough = (2.87 + 1.58 * log10(x / k_s))**(-2.5),
    the classical fully-rough turbulent flat-plate correlation for the
    fetch x over the equivalent sand roughness k_s. The correlation is
    calibrated for long fetches, so x / k_s must reach the
    ROUGH_MIN_X_OVER_KS floor of 100.0.
    """
    if x <= 0.0:
        raise ValueError("x must be positive")
    if k_s <= 0.0:
        raise ValueError("k_s must be positive")
    x_over_ks = x / k_s
    if x_over_ks < ROUGH_MIN_X_OVER_KS:
        raise ValueError(
            "x / k_s below the 100.0 validity floor of the fully-rough "
            "correlation"
        )
    return (2.87 + 1.58 * math.log10(x_over_ks)) ** -2.5


def _transitional_blend(cf_smooth, cf_rough, k_s_plus):
    """Return the log-linear blend of the two coefficients in ln(k+).

    Workflow step 7 internals: frac = (ln k+ - ln SMOOTH_K_PLUS) /
    (ln FULLY_ROUGH_K_PLUS - ln SMOOTH_K_PLUS) and cf = exp(ln cf_smooth
    + frac * (ln cf_rough - ln cf_smooth)); continuous and monotone in k+,
    returning cf_smooth at k+ 5 and cf_rough at k+ 70 exactly. The blend
    is a documented engineering approximation across the transitional
    band.
    """
    ln_frac = (
        math.log(k_s_plus) - math.log(SMOOTH_K_PLUS)
    ) / (
        math.log(FULLY_ROUGH_K_PLUS) - math.log(SMOOTH_K_PLUS)
    )
    return math.exp(
        math.log(cf_smooth) + ln_frac * (math.log(cf_rough) - math.log(cf_smooth))
    )


def cf_with_roughness(re_x, x, k_s, rho, u_inf, mu):
    """Return the rough-wall friction report dict for one fetch station.

    Workflow step 7: chain the single-pass sequence without iteration.
    Step order: (1) smooth baseline cf_smooth from smooth_turbulent_cf,
    (2) friction velocity from friction_velocity on cf_smooth, (3) k+ from
    sand_roughness_reynolds, (4) regime from classify_regime, (5) the
    fully-rough correlation value from rough_wall_cf, (6) selection: the
    smooth regime keeps cf_smooth, the fully-rough regime uses cf_rough
    directly, and the transitional regime takes the log-linear blend;
    cf_rough_or_iterated holds the value the roughness treatment produces
    and cf_used equals it by construction.

    Returns the dict with exactly the keys regime, k_s_plus, cf_smooth,
    cf_rough_or_iterated, cf_used and note.
    """
    cf_smooth = smooth_turbulent_cf(re_x)
    u_tau = friction_velocity(u_inf, cf_smooth)
    k_s_plus = sand_roughness_reynolds(rho, u_tau, k_s, mu)
    regime = classify_regime(k_s_plus)
    cf_rough = rough_wall_cf(x, k_s)
    if regime == "smooth":
        selected = cf_smooth
        note = NOTE_SMOOTH
    elif regime == "fully-rough":
        selected = cf_rough
        note = NOTE_FULLY_ROUGH
    else:
        selected = _transitional_blend(cf_smooth, cf_rough, k_s_plus)
        note = NOTE_TRANSITIONAL
    return {
        "regime": regime,
        "k_s_plus": k_s_plus,
        "cf_smooth": cf_smooth,
        "cf_rough_or_iterated": selected,
        "cf_used": selected,
        "note": note,
    }


def trip_criterion(u, k, nu, re_k_crit=TRIP_RE_K):
    """Return the critical-roughness Reynolds trip test dict.

    Workflow step 8: re_k = u * k / nu for a roughness element or trip
    strip of height k in a boundary layer with edge speed u and kinematic
    viscosity nu; trip is expected when re_k >= re_k_crit, inclusive at
    the boundary, with re_k_crit defaulting to the classical TRIP_RE_K of
    600.0 (paraphrase of the standard trip-sizing guidance).
    """
    if u <= 0.0:
        raise ValueError("u must be positive")
    if k <= 0.0:
        raise ValueError("k must be positive")
    if nu <= 0.0:
        raise ValueError("nu must be positive")
    if re_k_crit <= 0.0:
        raise ValueError("re_k_crit must be positive")
    re_k = u * k / nu
    return {
        "re_k": re_k,
        "trip_expected": re_k >= re_k_crit,
        "re_k_crit": re_k_crit,
    }

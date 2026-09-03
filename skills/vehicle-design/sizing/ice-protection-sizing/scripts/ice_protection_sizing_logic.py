"""Steady thermal ice protection system sizing (vehicle-design/sizing/ice-protection-sizing).

Pure stdlib conceptual model for anti-ice versus de-ice system sizing on an
aircraft surface in FAR/CS 25 Appendix C continuous maximum icing
(reference-only context, paraphrased). The surface is protected by either
evaporative anti-icing, running-wet anti-icing, or cyclic de-icing; the module
computes the protected area, the droplet catch efficiency from the median
volume diameter (MVD) and airspeed, the water catch rate, the evaporative
heat flux, the running-wet surface temperature against the freezing fraction,
the required power or bleed air mass flow, and the protect verdict.

All relations are standard engineering methodology with the module constants
stated below; they summarize, never reproduce, proprietary standard text.
Units are SI throughout (K, m, m/s, kg/m3, micron for MVD, W, W/m2, kg/s).

Assumptions recorded in the SKILL body:
- Adiabatic wall temperature equals the free-stream total temperature
  (turbulent recovery factor of about 1).
- Droplets arrive at the free-stream static temperature (slightly
  conservative for the sensible-heating term of the evaporative mode).
- The catch efficiency correlation is a preliminary, reference-only curve.
"""

# --- Module constants (state exactly in the SKILL body) ---------------------

# Kinetic heating: T_tot = T_inf * (1 + MACH_KINETIC * M^2) for air at
# gamma = 1.4, so 0.2 = (gamma - 1) / 2.
MACH_KINETIC = 0.2

# Catch efficiency correlation eta = min(1, ETA_K1 * (mvd / MVD_REF) ** 0.6 *
# (v / V_REF) ** 0.4 * (CHORD_REF / chord) ** 0.5). Preliminary curve,
# reference-only; eta rises with mvd and v and falls with chord.
ETA_K1 = 0.55
MVD_REF = 20.0        # micron, reference median volume diameter
V_REF = 100.0         # m/s, reference airspeed
CHORD_REF = 0.5       # m, reference protected-band scale

# Water thermophysics.
CP_WATER = 4186.0     # J/(kg K), specific heat of water
LATENT_HEAT_FUSION = 3.34e5      # J/kg, water at 0 C
LATENT_HEAT_VAPORIZATION = 2.501e6  # J/kg, water at 0 C
T_FREEZE = 273.15     # K, freezing temperature of water

# Surface temperature set points.
T_EVAP_SURFACE = 303.15  # K, representative evaporative anti-ice skin temp
T_SHED = 276.15          # K, de-ice shed temperature (~273.15 K + 3 K margin)

# Air properties, power-law fits referenced to 273.15 K.
T_PROP_REF = 273.15   # K
MU_AIR_REF = 1.716e-5 # Pa s, viscosity of air at 273.15 K
K_AIR_REF = 0.0244    # W/(m K), conductivity of air at 273.15 K
MU_EXP = 0.75         # viscosity temperature exponent
K_EXP = 0.85          # conductivity temperature exponent
PRANDTL = 0.72        # Prandtl number of air
TURBULENT_COEFF = 0.0296  # flat plate turbulent skin correlation constant

CP_AIR = 1005.0       # J/(kg K), specific heat of air (bleed flow)


def _require_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_nonnegative(value, name):
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def total_temperature(t_inf_k, mach):
    """Free-stream total temperature T_tot = T_inf * (1 + 0.2 * M^2).

    Adiabatic wall temperature equals T_tot under the turbulent recovery
    factor of about 1 stated in the SKILL body.
    """
    _require_positive(t_inf_k, "t_inf_k")
    _require_nonnegative(mach, "mach")
    return t_inf_k * (1.0 + MACH_KINETIC * mach * mach)


def kinetic_temperature_rise(t_inf_k, mach):
    """Kinetic heating rise T_kin = T_tot - T_inf, in kelvin."""
    _require_positive(t_inf_k, "t_inf_k")
    _require_nonnegative(mach, "mach")
    return t_inf_k * MACH_KINETIC * mach * mach


def catch_efficiency(mvd, v, chord):
    """Droplet catch efficiency eta in [0, 1] from the median volume
    diameter mvd (micron), airspeed v (m/s) and surface chord (m).

    Preliminary reference-only correlation, monotone: eta rises with mvd
    and v and falls with chord:
    eta = min(1, ETA_K1 * (mvd / MVD_REF) ** 0.6 * (v / V_REF) ** 0.4 *
    (CHORD_REF / chord) ** 0.5).
    """
    _require_positive(mvd, "mvd")
    _require_nonnegative(v, "v")
    _require_positive(chord, "chord")
    eta = ETA_K1 * ((mvd / MVD_REF) ** 0.6) * ((v / V_REF) ** 0.4) * (
        (CHORD_REF / chord) ** 0.5)
    return min(1.0, max(0.0, eta))


def water_catch_rate(eta, lwc, v, chord):
    """Water catch rate m_wdot = eta * LWC * v * chord, kg/s per m span."""
    if not (0.0 <= eta <= 1.0):
        raise ValueError("eta must lie in [0, 1], got %r" % (eta,))
    _require_nonnegative(lwc, "lwc")
    _require_nonnegative(v, "v")
    _require_positive(chord, "chord")
    return eta * lwc * v * chord


def freezing_fraction(t_surf_k):
    """Simplified running-wet freezing fraction n in [0, 1]:
    n = min(1, max(0, cp_water * (T_freeze - T_surf) / L_fusion)).

    Evaporative anti-ice runs n = 0 (all catch evaporates); running wet
    holds 0 < n < 1 (part freezes) below the freeze temperature and n = 0
    at or above it.
    """
    _require_positive(t_surf_k, "t_surf_k")
    n = CP_WATER * (T_FREEZE - t_surf_k) / LATENT_HEAT_FUSION
    return min(1.0, max(0.0, n))


def _air_properties(t_film_k):
    """(conductivity k, viscosity mu) of air at the film temperature.

    Power-law fits: k = K_AIR_REF * (T / T_PROP_REF) ** 0.85 and
    mu = MU_AIR_REF * (T / T_PROP_REF) ** 0.75, referenced to 273.15 K.
    """
    _require_positive(t_film_k, "t_film_k")
    ratio = t_film_k / T_PROP_REF
    k = K_AIR_REF * ratio ** K_EXP
    mu = MU_AIR_REF * ratio ** MU_EXP
    return k, mu


def convective_heat_transfer_coefficient(v, rho, c, t_film):
    """Flat plate turbulent heat transfer coefficient h_c (W/m2K):
    h_c = 0.0296 * k * Re^0.8 * Pr^(1/3) / c with Re = rho * v * c / mu
    and k, mu evaluated at the film temperature (reference-only standard
    form). The flat plate value is the running-wet reference; stagnation
    region values run higher.
    """
    _require_nonnegative(v, "v")
    _require_positive(rho, "rho")
    _require_positive(c, "c")
    _require_positive(t_film, "t_film")
    if v == 0.0:
        return 0.0
    k, mu = _air_properties(t_film)
    reynolds = rho * v * c / mu
    h_c = TURBULENT_COEFF * k * reynolds ** 0.8 * PRANDTL ** (1.0 / 3.0) / c
    return h_c


def convective_heat_loss(h_c, t_surf_k, t_inf_k):
    """Convective heat loss q_conv = h_c * (T_surf - T_inf), W/m2.

    Positive when the surface is hotter than the air (heat leaves the
    surface); negative values are an aerodynamic heating gain.
    """
    _require_nonnegative(h_c, "h_c")
    _require_positive(t_surf_k, "t_surf_k")
    _require_positive(t_inf_k, "t_inf_k")
    return h_c * (t_surf_k - t_inf_k)


def evaporative_heat_loss(m_evap_dot, area):
    """Evaporative heat loss q_evap = m_evap_dot * L_vaporization / area,
    W/m2, for the evaporated water rate m_evap_dot (kg/s) over the
    protected area (m2).
    """
    _require_nonnegative(m_evap_dot, "m_evap_dot")
    _require_positive(area, "area")
    return m_evap_dot * LATENT_HEAT_VAPORIZATION / area


def anti_ice_evaporative_heat_flux(h_c, t_surf_k, t_inf_k, m_evap_dot,
                                   area, t_catch_k=None):
    """Required heat flux q_req (W/m2) for evaporative anti-icing:
    q_req = q_conv + q_evap + sensible heating of the catch to T_surf.
    The surface stays above freezing and the whole catch evaporates.
    t_catch_k is the arrival temperature of the catch; the default is the
    free-stream static temperature (slightly conservative).
    """
    if t_catch_k is None:
        t_catch_k = t_inf_k
    _require_positive(t_catch_k, "t_catch_k")
    q_conv = convective_heat_loss(h_c, t_surf_k, t_inf_k)
    q_evap = evaporative_heat_loss(m_evap_dot, area)
    q_sensible = m_evap_dot * CP_WATER * (t_surf_k - t_catch_k) / area
    return q_conv + q_evap + q_sensible


def running_wet_heat_flux(h_c, t_surf_k, t_inf_k, t_kin_k):
    """Required heat flux q_req (W/m2) for running-wet anti-icing at the
    surface temperature t_surf_k: q_req = q_conv - kinetic heating
    contribution = h_c * (T_surf - T_inf - T_kin), with the kinetic
    heating contribution h_c * T_kin offsetting the convective loss
    against the adiabatic wall temperature.
    """
    _require_nonnegative(h_c, "h_c")
    _require_positive(t_surf_k, "t_surf_k")
    _require_positive(t_inf_k, "t_inf_k")
    _require_nonnegative(t_kin_k, "t_kin_k")
    return h_c * (t_surf_k - t_inf_k - t_kin_k)


def running_wet_surface_temperature(q_flux, h_c, t_inf_k, t_kin_k):
    """Running-wet surface temperature T_surf (K) sustained by the heat
    flux q_flux: T_surf = T_inf + T_kin + q_flux / h_c. At the protected
    limit q_flux = running_wet_heat_flux(h_c, T_freeze, ...), T_surf
    equals T_freeze and the freezing fraction is zero.
    """
    _require_nonnegative(q_flux, "q_flux")
    _require_positive(h_c, "h_c")
    _require_positive(t_inf_k, "t_inf_k")
    _require_nonnegative(t_kin_k, "t_kin_k")
    return t_inf_k + t_kin_k + q_flux / h_c


def de_ice_heat_flux(h_c, t_inf_k):
    """Required heat flux q_req (W/m2) for cyclic de-icing: q_req =
    q_conv at the shed temperature T_SHED (about 273.15 K + 3 K margin,
    no shedding dynamics). The surface sheds the accumulated ice in the
    run-back zone once the burst has raised it to T_SHED.
    """
    _require_nonnegative(h_c, "h_c")
    _require_positive(t_inf_k, "t_inf_k")
    return convective_heat_loss(h_c, T_SHED, t_inf_k)


def protected_area(chord, span, band_fraction):
    """Two-sided protected area A = 2 * band_fraction * chord * span (m2)
    for a wing leading edge band (band length chord fraction x chord x
    span, both surfaces) or the equivalent surface band.
    """
    _require_positive(chord, "chord")
    _require_positive(span, "span")
    if not (0.0 < band_fraction <= 1.0):
        raise ValueError("band_fraction must lie in (0, 1], got %r"
                         % (band_fraction,))
    return 2.0 * band_fraction * chord * span


def required_power(heat_flux, area):
    """Required power P_req = q_req * A_protected (W)."""
    _require_nonnegative(heat_flux, "heat_flux")
    _require_positive(area, "area")
    return heat_flux * area


def bleed_mass_flow(power, cp_air, t_bleed_k, t_inf_k):
    """Bleed air mass flow m_dot = P_req / (cp_air * (T_bleed - T_inf)),
    kg/s, for a bleed-powered (pneumatic) anti-ice system.
    """
    _require_nonnegative(power, "power")
    _require_positive(cp_air, "cp_air")
    _require_positive(t_bleed_k, "t_bleed_k")
    _require_positive(t_inf_k, "t_inf_k")
    if t_bleed_k <= t_inf_k:
        raise ValueError("t_bleed_k must exceed t_inf_k, got %r <= %r"
                         % (t_bleed_k, t_inf_k))
    return power / (cp_air * (t_bleed_k - t_inf_k))


def protect_verdict(area, power_req, power_avail, icing_critical):
    """Protect verdict dict for the surface. The surface is protected when
    it is on the icing-critical list and the required power sits within
    the available power margin; otherwise the dict flags the shortfall or
    the non-critical status.
    """
    _require_positive(area, "area")
    _require_nonnegative(power_req, "power_req")
    _require_nonnegative(power_avail, "power_avail")
    if not icing_critical:
        return {
            "icing_critical": False,
            "protect": False,
            "protected_area": area,
            "power_required": power_req,
            "power_available": power_avail,
            "reason": "surface not on the icing-critical list, no ice "
                      "protection required",
        }
    if power_req <= power_avail:
        return {
            "icing_critical": True,
            "protect": True,
            "protected_area": area,
            "power_required": power_req,
            "power_available": power_avail,
            "reason": "required power within the available margin",
        }
    return {
        "icing_critical": True,
        "protect": False,
        "protected_area": area,
        "power_required": power_req,
        "power_available": power_avail,
        "reason": "required power exceeds the available margin, flag for "
                  "a lower flux mode or more power",
    }

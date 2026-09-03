"""Hybrid rocket motor ballistics (hybrid-rocket-motor leaf).

Pure stdlib, SI units. Design-level model of a hybrid rocket motor with a
solid fuel grain and a fluid (liquid or gaseous) oxidizer: fuel regression
rate from the oxidizer mass flux through the port, oxidizer to fuel ratio
from the fuel production, chamber pressure equilibrium between the total
production and the choked nozzle discharge, mass flow, thrust, total
impulse, burn time, and the O/F shift as the port opens. The oxidizer
flow is feed-limited (an input), so the chamber pressure is set directly
by m_dot * c* / A_t; the regression law is flux-driven, not
pressure-driven. That is the defining difference from the all-solid
grain ballistics owned by solid-rocket-motor. All typical-value
constants are reference-only with the documented
assumption; no reproduced standard tables.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2 (kept for reference and tests)

# Reference-only typical regression and motor constants per fuel pair.
# Entry: a = regression coefficient, m/s per (kg/m2/s)^n evaluated at the
# reference grain length L_ref (m); n = mass-flux exponent in (0, 1);
# m = grain-length exponent in the ratio form (L_grain / L_ref)^m;
# rho_f = solid fuel density, kg/m3; c_star = characteristic velocity,
# m/s. The classic hybrid regression law is
#   r_dot = a * G_o^n * (L_grain / L_ref)^m
# with G_o the oxidizer mass flux through the port. The exponents and
# coefficients are reference-only typicals for lab-scale grains (e.g.
# HTPB/N2O a near 0.1 to 0.2 mm/s per (kg/m2/s)^n with n near 0.5 to
# 0.7); the negative length exponent reflects the mild decay of the
# space-averaged regression rate with a longer grain in flux-based
# correlations.
FUELS = {
    "HTPB-N2O": {
        "a": 1.2e-4,     # m/s per (kg/m2/s)^n at L_ref, reference-only
        "n": 0.55,       # mass-flux exponent, dimensionless
        "m": -0.20,      # grain-length exponent, dimensionless
        "L_ref": 0.6,    # reference grain length, m
        "rho_f": 920.0,  # HTPB fuel density, kg/m3
        "c_star": 1500.0,  # HTPB/N2O characteristic velocity, m/s
    },
    "HTPB-LOX": {
        "a": 1.8e-4,     # m/s per (kg/m2/s)^n at L_ref, reference-only
        "n": 0.50,       # mass-flux exponent, dimensionless
        "m": -0.15,      # grain-length exponent, dimensionless
        "L_ref": 0.6,    # reference grain length, m
        "rho_f": 920.0,  # HTPB fuel density, kg/m3
        "c_star": 1750.0,  # HTPB/LOX characteristic velocity, m/s
    },
}

DEFAULT_FUEL = "HTPB-N2O"
THRUST_COEFF_DEFAULT = 1.4  # reference-only typical nozzle thrust coefficient


def _require_finite(*values):
    for value in values:
        if value is None or not math.isfinite(value):
            raise ValueError("inputs must be finite, got {0!r}".format(value))


def fuel_properties(fuel):
    """Return the reference-only property dict for a named fuel pair."""
    try:
        props = FUELS[fuel]
    except (KeyError, TypeError):
        raise ValueError(
            "unknown fuel: {0}; known fuels: {1}".format(fuel, ", ".join(sorted(FUELS))))
    if not (0.0 < props["n"] < 1.0):
        raise ValueError("regression exponent n must lie in (0, 1)")
    if not math.isfinite(props["a"]) or props["a"] <= 0.0:
        raise ValueError("regression coefficient a must be positive and finite")
    return props


def regression_rate(g_o, fuel):
    """Classic hybrid regression rate, m/s, at the fuel reference length.

    r_dot = a * G_o^n with the length ratio (L_grain / L_ref)^m equal to
    one at the reference grain length L_ref of the fuel record. Motors
    with a different grain length scale the rate by the documented length
    ratio through hybrid_motor_summary.
    """
    _require_finite(g_o)
    if g_o <= 0.0:
        raise ValueError("oxidizer mass flux must be positive, got {0}".format(g_o))
    props = fuel_properties(fuel)
    return props["a"] * g_o ** props["n"]


def regression_rate_at_length(g_o, fuel, length):
    """Hybrid regression rate, m/s, for an actual grain length.

    r_dot = a * G_o^n * (L_grain / L_ref)^m. Length is the cylindrical
    grain length in meters; the ratio form keeps the coefficient
    dimensionally simple.
    """
    _require_finite(length)
    if length <= 0.0:
        raise ValueError("grain length must be positive, got {0}".format(length))
    props = fuel_properties(fuel)
    base = regression_rate(g_o, fuel)
    return base * (length / props["L_ref"]) ** props["m"]


def oxidizer_mass_flux(m_dot_o, port_area):
    """Oxidizer mass flux through the port, kg/m2/s: m_dot_o / A_port."""
    _require_finite(m_dot_o, port_area)
    if m_dot_o <= 0.0:
        raise ValueError("oxidizer mass flow must be positive, got {0}".format(m_dot_o))
    if port_area <= 0.0:
        raise ValueError("port area must be positive, got {0}".format(port_area))
    return m_dot_o / port_area


def port_area_circular(radius):
    """Circular port cross-section area, m2: pi * r^2."""
    _require_finite(radius)
    if radius <= 0.0:
        raise ValueError("port radius must be positive, got {0}".format(radius))
    return math.pi * radius * radius


def burn_area_cylindrical(radius, length):
    """Cylindrical port burn area, m2: pi * D_port * L_grain."""
    _require_finite(radius, length)
    if radius <= 0.0:
        raise ValueError("port radius must be positive, got {0}".format(radius))
    if length <= 0.0:
        raise ValueError("grain length must be positive, got {0}".format(length))
    return math.pi * 2.0 * radius * length


def fuel_mass_flow(rho_f, r_dot, burn_area):
    """Fuel mass flow from the burning surface, kg/s: rho_f * r_dot * A_burn."""
    _require_finite(rho_f, r_dot, burn_area)
    if rho_f <= 0.0:
        raise ValueError("fuel density must be positive, got {0}".format(rho_f))
    if r_dot < 0.0:
        raise ValueError("regression rate must not be negative, got {0}".format(r_dot))
    if burn_area < 0.0:
        raise ValueError("burn area must not be negative, got {0}".format(burn_area))
    return rho_f * r_dot * burn_area


def of_ratio(m_dot_o, m_dot_f):
    """Oxidizer to fuel ratio, dimensionless: m_dot_o / m_dot_f."""
    _require_finite(m_dot_o, m_dot_f)
    if m_dot_o <= 0.0:
        raise ValueError("oxidizer mass flow must be positive, got {0}".format(m_dot_o))
    if m_dot_f <= 0.0:
        raise ValueError("fuel mass flow must be positive, got {0}".format(m_dot_f))
    return m_dot_o / m_dot_f


def chamber_pressure(m_dot, c_star, area_throat):
    """Chamber pressure equilibrium, Pa: p_c * A_t / c* = m_dot.

    With a feed-limited oxidizer flow the total mass flow m_dot through
    the choked throat is known, so the equilibrium is direct: p_c =
    m_dot * c* / A_t. The mass balance (fuel production plus oxidizer
    flow equals the nozzle discharge) is asserted by the summary.
    """
    _require_finite(m_dot, c_star, area_throat)
    if m_dot <= 0.0:
        raise ValueError("total mass flow must be positive, got {0}".format(m_dot))
    if c_star <= 0.0:
        raise ValueError("characteristic velocity must be positive, got {0}".format(c_star))
    if area_throat <= 0.0:
        raise ValueError("throat area must be positive, got {0}".format(area_throat))
    return m_dot * c_star / area_throat


def thrust(thrust_coeff, p_c, area_throat):
    """Nozzle thrust, N: F = c_f * p_c * A_t."""
    _require_finite(thrust_coeff, p_c, area_throat)
    if thrust_coeff <= 0.0:
        raise ValueError("thrust coefficient must be positive, got {0}".format(thrust_coeff))
    if p_c <= 0.0:
        raise ValueError("chamber pressure must be positive, got {0}".format(p_c))
    if area_throat <= 0.0:
        raise ValueError("throat area must be positive, got {0}".format(area_throat))
    return thrust_coeff * p_c * area_throat


def burn_time(web, r_dot_avg):
    """Burn time, s: web / r_dot_avg with the burned web of fuel."""
    _require_finite(web, r_dot_avg)
    if web <= 0.0:
        raise ValueError("burned web must be positive, got {0}".format(web))
    if r_dot_avg <= 0.0:
        raise ValueError("average regression rate must be positive, got {0}".format(r_dot_avg))
    return web / r_dot_avg


def of_shift(m_dot_o, fuel, rho_f, r_initial, r_final, length):
    """O/F shift over the burn, comparing the open and the closed port.

    The port grows from r_initial to r_final as the web burns, so the
    oxidizer flux G_o = m_dot_o / A_port decays and the fuel production
    changes with it. Returns dict(of_initial, of_final, shift,
    direction) with shift = of_final - of_initial; a positive shift means
    the mixture leans oxidizer-rich as the port opens, the classic hybrid
    trend.
    """
    _require_finite(rho_f)
    if rho_f <= 0.0:
        raise ValueError("fuel density must be positive, got {0}".format(rho_f))
    if r_initial <= 0.0:
        raise ValueError("initial port radius must be positive, got {0}".format(r_initial))
    if r_final <= r_initial:
        raise ValueError("final port radius must exceed the initial radius")
    fuel_properties(fuel)
    m_dot_f_initial = _fuel_flow_at(m_dot_o, fuel, rho_f, r_initial, length)
    m_dot_f_final = _fuel_flow_at(m_dot_o, fuel, rho_f, r_final, length)
    of_initial = of_ratio(m_dot_o, m_dot_f_initial)
    of_final = of_ratio(m_dot_o, m_dot_f_final)
    shift = of_final - of_initial
    if shift > 1.0e-12:
        direction = "increases"
    elif shift < -1.0e-12:
        direction = "decreases"
    else:
        direction = "holds"
    return {
        "of_initial": of_initial,
        "of_final": of_final,
        "shift": shift,
        "direction": direction,
    }


def _fuel_flow_at(m_dot_o, fuel, rho_f, radius, length):
    """Fuel mass flow, kg/s, at one port radius along the burn."""
    port_area = port_area_circular(radius)
    g_o = oxidizer_mass_flux(m_dot_o, port_area)
    r_dot = regression_rate_at_length(g_o, fuel, length)
    burn_area = burn_area_cylindrical(radius, length)
    return fuel_mass_flow(rho_f, r_dot, burn_area)


def hybrid_motor_summary(m_dot_o, fuel, r_initial, r_final, length,
                         area_throat, rho_f=None, c_star=None,
                         thrust_coeff=None):
    """Full hybrid motor ballistics summary dict for one burn.

    Scheme: the port radius grows linearly in the burned web from
    r_initial to r_final. Fuel production and the chamber equilibrium
    are evaluated at three stations, the initial and the final port and
    the mid-burn geometry (r_mid = (r_initial + r_final) / 2). The burn
    time uses the regression rate at the mid-burn geometry (burn-average
    flux scheme) with t_b = web / r_dot_mid, and the total impulse is
    the mid-burn thrust times the burn time. rho_f and c_star default to
    the fuel record reference typicals; thrust_coeff defaults to
    THRUST_COEFF_DEFAULT. Returns the ballistics summary with the O/F
    shift trend.
    """
    props = fuel_properties(fuel)
    rho_f_use = props["rho_f"] if rho_f is None else rho_f
    c_star_use = props["c_star"] if c_star is None else c_star
    cf_use = THRUST_COEFF_DEFAULT if thrust_coeff is None else thrust_coeff
    _require_finite(rho_f_use, c_star_use, cf_use)
    if rho_f_use <= 0.0:
        raise ValueError("fuel density must be positive, got {0}".format(rho_f_use))
    if c_star_use <= 0.0:
        raise ValueError("characteristic velocity must be positive, got {0}".format(c_star_use))
    if cf_use <= 0.0:
        raise ValueError("thrust coefficient must be positive, got {0}".format(cf_use))
    if r_initial <= 0.0:
        raise ValueError("initial port radius must be positive, got {0}".format(r_initial))
    if r_final <= r_initial:
        raise ValueError("final port radius must exceed the initial radius")
    if length <= 0.0:
        raise ValueError("grain length must be positive, got {0}".format(length))
    if area_throat <= 0.0:
        raise ValueError("throat area must be positive, got {0}".format(area_throat))

    radii = {"initial": r_initial, "mid": 0.5 * (r_initial + r_final),
             "final": r_final}
    station = {}
    for tag, radius in radii.items():
        port_area = port_area_circular(radius)
        g_o = oxidizer_mass_flux(m_dot_o, port_area)
        r_dot = regression_rate_at_length(g_o, fuel, length)
        burn_area = burn_area_cylindrical(radius, length)
        m_dot_f = fuel_mass_flow(rho_f_use, r_dot, burn_area)
        m_dot_total = m_dot_o + m_dot_f
        p_c = chamber_pressure(m_dot_total, c_star_use, area_throat)
        f = thrust(cf_use, p_c, area_throat)
        station[tag] = {
            "radius": radius,
            "port_area": port_area,
            "g_o": g_o,
            "r_dot": r_dot,
            "burn_area": burn_area,
            "m_dot_f": m_dot_f,
            "m_dot_total": m_dot_total,
            "p_c": p_c,
            "thrust": f,
            "of": of_ratio(m_dot_o, m_dot_f),
        }

    web = r_final - r_initial
    t_b = burn_time(web, station["mid"]["r_dot"])
    total_impulse = station["mid"]["thrust"] * t_b
    fuel_consumed = rho_f_use * math.pi * (r_final * r_final -
                                           r_initial * r_initial) * length
    # Mass balance: fuel production plus the oxidizer flow must equal the
    # nozzle discharge used for the chamber equilibrium at every station.
    mass_balance_error = max(
        abs(station[tag]["m_dot_f"] + m_dot_o - station[tag]["m_dot_total"])
        for tag in station)
    shift = of_shift(m_dot_o, fuel, rho_f_use, r_initial, r_final, length)

    verdict = (
        "{0} hybrid motor: oxidizer {1:.3f} kg/s against an HTPB-type solid "
        "grain, chamber pressure {2:.2f} MPa at ignition settling to "
        "{3:.2f} MPa as the port opens, mid-burn thrust {4:.0f} N over "
        "{5:.1f} s gives {6:.0f} N s total impulse; O/F {7:.2f} to {8:.2f} "
        "{9} over the burn".format(
            fuel, m_dot_o, station["initial"]["p_c"] / 1.0e6,
            station["final"]["p_c"] / 1.0e6, station["mid"]["thrust"],
            t_b, total_impulse, shift["of_initial"], shift["of_final"],
            shift["direction"]))

    return {
        "fuel": fuel,
        "m_dot_o": m_dot_o,
        "rho_f": rho_f_use,
        "c_star": c_star_use,
        "thrust_coeff": cf_use,
        "length": length,
        "r_initial": r_initial,
        "r_final": r_final,
        "web": web,
        "area_throat": area_throat,
        "initial": station["initial"],
        "mid": station["mid"],
        "final": station["final"],
        "of_shift": shift,
        "burn_time": t_b,
        "total_impulse": total_impulse,
        "fuel_consumed": fuel_consumed,
        "mass_balance_error": mass_balance_error,
        "verdict": verdict,
    }

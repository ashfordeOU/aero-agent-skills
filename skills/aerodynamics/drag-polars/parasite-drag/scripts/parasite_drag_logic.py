#!/usr/bin/env python3
"""Parasite (zero-lift) drag buildup logic (common knowledge, stdlib only).

The component buildup method estimates the parasite drag of a fixed-wing
aircraft as the sum over components of

    CD_i = Cf * FF * Q * S_wet_i / S_ref

where Cf is the flat-plate skin-friction coefficient evaluated at the
component Reynolds number Re = rho * V * L / mu, FF is the component
form factor, Q the interference factor, S_wet_i the wetted area, and
S_ref the reference area used to nondimensionalize drag. The total
parasite drag CD_parasite = sum_i CD_i; the equivalent skin-friction
coefficient Cf_e = CD_parasite * S_ref / S_wet_total backs out the
fleet-average skin friction implied by the buildup.

Flat-plate skin friction (incompressible, common textbook forms):
  laminar  Cf = 1.328 / sqrt(Re)                 (Blasius)
  turbulent Cf = 0.455 / (log10(Re))^2.58        (Schlichting)
  mixed (laminar to Re_tr, turbulent beyond):
      Cf = Cf_turb(Re) - (Re_tr/Re) * (Cf_turb(Re_tr) - Cf_lam(Re_tr))

Form factors (common textbook estimates, preliminary design only):
  wing/tail (airfoil)  FF = 1 + 2*(t/c) + 100*(t/c)^4
  fuselage (body)      FF = 1 + 60/(l/d)^3 + 0.0025*(l/d)
  nacelle              FF = 1 + 0.35/(l/d)

All functions are pure, deterministic, offline, and use only the Python
standard library.
"""

import math


def reynolds_number(rho, v, l, mu):
    """Reynolds number Re = rho * V * L / mu for a component of length L.

    Raises ValueError unless all inputs are strictly positive.
    """
    if rho <= 0 or v <= 0 or l <= 0 or mu <= 0:
        raise ValueError(
            "rho, v, l, mu must all be > 0, got (%r, %r, %r, %r)" % (rho, v, l, mu)
        )
    return rho * v * l / mu


def cf_flat_plate_laminar(re):
    """Laminar flat-plate skin friction Cf = 1.328 / sqrt(Re).

    Raises ValueError for Re <= 0.
    """
    if re <= 0:
        raise ValueError("Reynolds number must be > 0 for laminar Cf, got %r" % (re,))
    return 1.328 / math.sqrt(re)


def cf_flat_plate_turbulent(re):
    """Fully turbulent flat-plate skin friction Cf = 0.455 / (log10 Re)^2.58.

    Requires Re > 10 so log10(Re) is defined and positive; raises
    ValueError otherwise.
    """
    if re <= 10:
        raise ValueError(
            "Reynolds number must be > 10 for turbulent Cf, got %r" % (re,)
        )
    return 0.455 / (math.log10(re) ** 2.58)


def cf_flat_plate_mixed(re, re_transition):
    """Mixed laminar-turbulent skin friction with transition at Re_tr.

    Cf = Cf_turb(Re) - (Re_tr/Re) * (Cf_turb(Re_tr) - Cf_lam(Re_tr)).
    Raises ValueError unless 10 < re_transition < re.
    """
    if re <= 10:
        raise ValueError("Reynolds number must be > 10, got %r" % (re,))
    if re_transition <= 10 or re_transition >= re:
        raise ValueError(
            "transition Reynolds number must satisfy 10 < Re_tr < Re, "
            "got Re_tr=%r, Re=%r" % (re_transition, re)
        )
    cf_t = cf_flat_plate_turbulent(re)
    cf_t_tr = cf_flat_plate_turbulent(re_transition)
    cf_l_tr = cf_flat_plate_laminar(re_transition)
    return cf_t - (re_transition / re) * (cf_t_tr - cf_l_tr)


def form_factor(kind, t_over_c=None, l_over_d=None):
    """Form factor FF for a component kind.

    wing/tail use the airfoil thickness ratio t/c (0 < t/c < 0.5):
        FF = 1 + 2*(t/c) + 100*(t/c)^4
    fuselage uses the fineness ratio l/d (> 1):
        FF = 1 + 60/(l/d)^3 + 0.0025*(l/d)
    nacelle uses the fineness ratio l/d (> 1):
        FF = 1 + 0.35/(l/d)

    Raises ValueError for unknown kinds or out-of-range geometry.
    """
    kind = str(kind).lower()
    if kind in ("wing", "tail"):
        if t_over_c is None or t_over_c <= 0 or t_over_c >= 0.5:
            raise ValueError(
                "t_over_c must be in (0, 0.5) for wing/tail, got %r" % (t_over_c,)
            )
        return 1.0 + 2.0 * t_over_c + 100.0 * t_over_c ** 4
    if kind in ("fuselage", "nacelle"):
        if l_over_d is None or l_over_d <= 1.0:
            raise ValueError(
                "l_over_d must be > 1.0 for fuselage/nacelle, got %r" % (l_over_d,)
            )
        if kind == "fuselage":
            return 1.0 + 60.0 / (l_over_d ** 3) + 0.0025 * l_over_d
        return 1.0 + 0.35 / l_over_d
    raise ValueError(
        "unknown component kind %r (use wing, tail, fuselage, or nacelle)" % (kind,)
    )


def component_parasite_drag(cf, ff, q, s_wet, s_ref):
    """Component parasite drag coefficient CD = Cf * FF * Q * S_wet / S_ref.

    Raises ValueError when cf <= 0, ff < 1, q < 1, s_wet <= 0, or
    s_ref <= 0.
    """
    if cf <= 0:
        raise ValueError("skin-friction coefficient must be > 0, got %r" % (cf,))
    if ff < 1.0:
        raise ValueError("form factor must be >= 1, got %r" % (ff,))
    if q < 1.0:
        raise ValueError("interference factor must be >= 1, got %r" % (q,))
    if s_wet <= 0:
        raise ValueError("wetted area must be > 0, got %r" % (s_wet,))
    if s_ref <= 0:
        raise ValueError("reference area must be > 0, got %r" % (s_ref,))
    return cf * ff * q * s_wet / s_ref


def total_parasite_drag(component_cds):
    """Total parasite drag coefficient as the sum of component CD values.

    An empty list sums to 0.0 (no drag contributions).
    """
    return float(sum(component_cds))


def equivalent_skin_friction(cd_total, s_ref, s_wet_total):
    """Equivalent skin-friction coefficient Cf_e = CD * S_ref / S_wet_total.

    Raises ValueError when cd_total < 0, s_ref <= 0, or s_wet_total <= 0.
    """
    if cd_total < 0:
        raise ValueError("total parasite drag must be >= 0, got %r" % (cd_total,))
    if s_ref <= 0:
        raise ValueError("reference area must be > 0, got %r" % (s_ref,))
    if s_wet_total <= 0:
        raise ValueError("total wetted area must be > 0, got %r" % (s_wet_total,))
    return cd_total * s_ref / s_wet_total


def wing_wetted_area(s_exposed, t_over_c):
    """First-order wetted-area estimate S_wet = 2 * S_exposed * (1 + 0.2*t/c).

    Classic two-surface estimate: the exposed planform area counted on
    both sides, inflated by the thickness chord ratio. Raises ValueError
    for s_exposed <= 0 or t/c outside (0, 0.5).
    """
    if s_exposed <= 0:
        raise ValueError("exposed area must be > 0, got %r" % (s_exposed,))
    if t_over_c <= 0 or t_over_c >= 0.5:
        raise ValueError(
            "t_over_c must be in (0, 0.5), got %r" % (t_over_c,)
        )
    return 2.0 * s_exposed * (1.0 + 0.2 * t_over_c)

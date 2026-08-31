#!/usr/bin/env python3
"""Bypass ratio design trade logic (first-order, common knowledge).

Units (one convention throughout, asserted here):
- mass flow mdot in kg/s
- velocity V in m/s
- thrust F in N (newtons)
- specific thrust F/mdot in m/s (N per kg/s)
- TSFC in g/(kN*s): grams of fuel per kilonewton per second

First-order fan/core split model at fixed core conditions and fixed
total mass flow (documented, common propulsion methodology):

  mdot_fan  = BPR/(1+BPR) * mdot_total
  mdot_core = mdot_total/(1+BPR)
  F_core = mdot_core * (Vj_core - V0)
  F_fan  = mdot_fan  * (Vj_fan  - V0)
  F_total = F_core + F_fan
  specific_thrust = F_total / mdot_total
  mdot_fuel = f * mdot_core   (f = core fuel/air ratio, e.g. 0.02)
  tsfc [g/(kN*s)] = 1000 * mdot_fuel[g/s] / (F_total[kN])
                  = 1e6 * f * mdot_core / F_total
  propulsive efficiency eta_p = 2 / (1 + Vj/V0) for a stream at jet
  velocity Vj in flight at V0.

Design trend: raising BPR shifts mass flow to the fan stream, whose jet
velocity is much lower than the core's, so the average jet velocity
drops, propulsive efficiency rises, and TSFC falls. Fixed-core caveat:
holding the core and fan jet velocities constant while raising BPR
grows fan diameter, weight, and drag, and the fan pressure ratio (FPR)
rises with fan jet velocity, which cuts the efficiency gain.

FAR-33 is referenced, not reproduced; this model is common propulsion
methodology summarized per standards-map.yaml.
"""


def _check_bpr_mdot(bpr, mdot_total):
    if bpr < 0:
        raise ValueError("bpr must be >= 0, got %r" % (bpr,))
    if mdot_total <= 0:
        raise ValueError("mdot_total must be > 0, got %r" % (mdot_total,))


def _check_velocities(Vj_core, Vj_fan, V0):
    for name, v in (("Vj_core", Vj_core), ("Vj_fan", Vj_fan), ("V0", V0)):
        if v <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, v))


def thrust_split(bpr, mdot_total, Vj_core, Vj_fan, V0):
    """Thrust split between fan and core streams (dict, N and kg/s).

    Net thrust per stream F = mdot*(Vj - V0). Each jet velocity must
    exceed the flight velocity so the stream produces positive thrust.
    Returns mdot_fan, mdot_core, F_core, F_fan, F_total.
    """
    _check_bpr_mdot(bpr, mdot_total)
    _check_velocities(Vj_core, Vj_fan, V0)
    if Vj_core <= V0:
        raise ValueError(
            "Vj_core must be > V0 (core stream must thrust), got Vj_core=%r V0=%r"
            % (Vj_core, V0)
        )
    if Vj_fan <= V0:
        raise ValueError(
            "Vj_fan must be > V0 (fan stream must thrust), got Vj_fan=%r V0=%r"
            % (Vj_fan, V0)
        )
    mdot_core = mdot_total / (1.0 + bpr)
    mdot_fan = mdot_total * bpr / (1.0 + bpr)
    F_core = mdot_core * (Vj_core - V0)
    F_fan = mdot_fan * (Vj_fan - V0)
    return {
        "mdot_fan": mdot_fan,
        "mdot_core": mdot_core,
        "F_core": F_core,
        "F_fan": F_fan,
        "F_total": F_core + F_fan,
    }


def specific_thrust(F_total, mdot_total):
    """Net thrust per unit total mass flow (m/s = N per kg/s)."""
    if F_total < 0:
        raise ValueError("F_total must be >= 0, got %r" % (F_total,))
    if mdot_total <= 0:
        raise ValueError("mdot_total must be > 0, got %r" % (mdot_total,))
    return F_total / mdot_total


def propulsive_efficiency(vj, v0):
    """Propulsive efficiency eta_p = 2/(1 + vj/v0), dimensionless.

    Unity when the jet velocity equals the flight velocity; falls as
    the jet velocity rises above the flight velocity.
    """
    if vj <= 0 or v0 <= 0:
        raise ValueError("vj and v0 must be > 0, got vj=%r v0=%r" % (vj, v0))
    return 2.0 / (1.0 + vj / v0)


def tsfc(bpr, mdot_total, Vj_core, Vj_fan, V0, f):
    """Thrust-specific fuel consumption in g/(kN*s).

    Fuel flow mdot_fuel = f * mdot_core (kg/s), with f the core
    fuel/air ratio (dimensionless, e.g. 0.02). Conversion factor:
    1000 g/kg over the thrust expressed in kN, hence 1e6 * f *
    mdot_core / F_total.
    """
    if not 0.0 < f < 1.0:
        raise ValueError("f must be in (0, 1), got %r" % (f,))
    split = thrust_split(bpr, mdot_total, Vj_core, Vj_fan, V0)
    mdot_fuel = f * split["mdot_core"]  # kg/s
    return 1e6 * mdot_fuel / split["F_total"]  # g/(kN*s)


def bpr_trend(bprs, mdot_total, Vj_core, Vj_fan, V0, f):
    """Trend of F_total, specific thrust, and TSFC across bypass ratios.

    Returns one dict per bypass ratio, in input order: bpr, F_total,
    specific_thrust, tsfc. Fixed core conditions and fixed total mass
    flow: higher BPR shifts flow to the fan stream, lowering the
    average jet velocity and TSFC. Caveat: the gain costs fan diameter,
    weight, and drag, and the fan pressure ratio rise with fan jet
    velocity offsets part of the efficiency gain.
    """
    if not bprs:
        raise ValueError("bprs must not be empty")
    out = []
    for b in bprs:
        split = thrust_split(b, mdot_total, Vj_core, Vj_fan, V0)
        out.append(
            {
                "bpr": b,
                "F_total": split["F_total"],
                "specific_thrust": specific_thrust(split["F_total"], mdot_total),
                "tsfc": tsfc(b, mdot_total, Vj_core, Vj_fan, V0, f),
            }
        )
    return out


def fan_pressure_ratio_note(fpr):
    """Qualitative FPR trade verdict for a fan pressure ratio value.

    Fan pressure ratio is fan exit total pressure over fan inlet total
    pressure; values at or below 1 are not a working fan. A higher FPR
    raises the fan jet velocity: better fan loading and a smaller,
    lighter fan, but lower propulsive efficiency and higher TSFC.
    """
    if fpr <= 1.0:
        raise ValueError("fpr must be > 1, got %r" % (fpr,))
    if fpr < 1.3:
        return (
            "low fan pressure ratio: low fan jet velocity, high "
            "propulsive efficiency and low TSFC, at the price of a "
            "large fan diameter"
        )
    if fpr < 1.6:
        return (
            "moderate fan pressure ratio: balanced fan loading, "
            "propulsive efficiency, and fan diameter"
        )
    return (
        "high fan pressure ratio: higher fan jet velocity, better fan "
        "loading and smaller diameter, but lower propulsive efficiency "
        "and higher TSFC"
    )

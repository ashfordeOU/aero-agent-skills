"""Fuel tank inerting sizing logic (pure stdlib, offline deterministic).

Conceptual sizing of the fuel tank inerting system from the ullage
oxygen washout by nitrogen-enriched air (NEA). The ullage is modeled as
a well-mixed volume whose oxygen fraction decays exponentially toward
the NEA oxygen fraction:

    C(t) = C_NEA + (C0 - C_NEA) * exp(-Q * t / V)

with V the ullage volume in m3 and Q the NEA volumetric flow in m3/s.
Inverting that relation gives the required NEA flow to reach a target
oxygen fraction within a required time:

    Q = (V / t) * ln((C0 - C_NEA) / (C_tgt - C_NEA))

All functions are pure, deterministic, and raise ValueError on
non-physical inputs. Units follow the spec: ullage volume in m3, flows
in m3/s, oxygen fractions as volume fractions in 0..1, time in s.
"""

import math

# Initial ullage oxygen fraction (air at sea level).
C0_AIR = 0.21
# Oxygen fraction of the nitrogen-enriched air supply, default 5%.
C_NEA_DEFAULT = 0.05
# 1 m3/s = 2118.88 SCFM (standard cubic feet per minute).
SCFM_PER_M3S = 2118.88


def _check_supply_bounds(c_nea, c0):
    """Raise ValueError when the NEA or initial oxygen fractions are
    non-physical: c0 must lie in (0, 1) and c_nea in (0, c0)."""
    if c0 <= 0.0 or c0 >= 1.0:
        raise ValueError(
            "initial oxygen fraction c0 must be in (0, 1), got %r" % (c0,)
        )
    if c_nea <= 0.0 or c_nea >= c0:
        raise ValueError(
            "NEA oxygen fraction c_nea must be in (0, c0), got %r" % (c_nea,)
        )


def _check_target_bounds(target_o2_fraction, c_nea, c0):
    """Raise ValueError when the target oxygen fraction is unreachable:
    it must lie strictly between c_nea and c0."""
    if target_o2_fraction <= c_nea or target_o2_fraction >= c0:
        raise ValueError(
            "target oxygen fraction must lie in (c_nea, c0) = (%r, %r), "
            "got %r" % (c_nea, c0, target_o2_fraction)
        )


def nea_flow_required(ullage_m3, target_o2_fraction, time_s, c_nea=C_NEA_DEFAULT,
                      c0=C0_AIR):
    """Required NEA volumetric flow to reach the target oxygen fraction
    within the required time.

    Q = (V / t) * ln((c0 - c_nea) / (target - c_nea))

    Returns a dict with keys flow_m3_s and flow_scfm.
    """
    if ullage_m3 <= 0.0:
        raise ValueError("ullage volume must be positive, got %r" % (ullage_m3,))
    if time_s <= 0.0:
        raise ValueError("required time must be positive, got %r" % (time_s,))
    _check_supply_bounds(c_nea, c0)
    _check_target_bounds(target_o2_fraction, c_nea, c0)
    flow = (ullage_m3 / time_s) * math.log(
        (c0 - c_nea) / (target_o2_fraction - c_nea)
    )
    return {"flow_m3_s": flow, "flow_scfm": flow * SCFM_PER_M3S}


def ullage_o2_fraction(ullage_m3, nea_flow_m3_s, time_s, c_nea=C_NEA_DEFAULT,
                       c0=C0_AIR):
    """Ullage oxygen fraction after time_s at a fixed NEA flow.

    C(t) = c_nea + (c0 - c_nea) * exp(-flow * t / V)

    time_s == 0 returns c0; flow == 0 leaves the fraction at c0.
    """
    if ullage_m3 <= 0.0:
        raise ValueError("ullage volume must be positive, got %r" % (ullage_m3,))
    if nea_flow_m3_s < 0.0:
        raise ValueError(
            "NEA flow must be non-negative, got %r" % (nea_flow_m3_s,)
        )
    if time_s < 0.0:
        raise ValueError("time must be non-negative, got %r" % (time_s,))
    _check_supply_bounds(c_nea, c0)
    if nea_flow_m3_s == 0.0 or time_s == 0.0:
        return c0
    return c_nea + (c0 - c_nea) * math.exp(
        -nea_flow_m3_s * time_s / ullage_m3
    )


def washout_time(ullage_m3, nea_flow_m3_s, target_o2_fraction, c_nea=C_NEA_DEFAULT,
                 c0=C0_AIR):
    """Time in seconds to wash the ullage down to the target oxygen
    fraction at a fixed NEA flow.

    t = (V / flow) * ln((c0 - c_nea) / (target - c_nea))
    """
    if ullage_m3 <= 0.0:
        raise ValueError("ullage volume must be positive, got %r" % (ullage_m3,))
    if nea_flow_m3_s <= 0.0:
        raise ValueError("NEA flow must be positive, got %r" % (nea_flow_m3_s,))
    _check_supply_bounds(c_nea, c0)
    _check_target_bounds(target_o2_fraction, c_nea, c0)
    return (ullage_m3 / nea_flow_m3_s) * math.log(
        (c0 - c_nea) / (target_o2_fraction - c_nea)
    )


def inerting_summary(ullage_m3, target_o2_fraction, time_s, max_nea_capacity_m3_s,
                     c_nea=C_NEA_DEFAULT, c0=C0_AIR):
    """Full inerting sizing summary for one design point.

    Returns a dict with keys flow_m3_s, flow_scfm, o2_at_time and
    capacity_verdict; capacity_verdict is PASS when the required flow
    does not exceed the NEA generator capacity limit, else FAIL.
    """
    if max_nea_capacity_m3_s <= 0.0:
        raise ValueError(
            "NEA generator capacity must be positive, got %r"
            % (max_nea_capacity_m3_s,)
        )
    flow = nea_flow_required(ullage_m3, target_o2_fraction, time_s, c_nea, c0)
    o2_at_time = ullage_o2_fraction(
        ullage_m3, flow["flow_m3_s"], time_s, c_nea, c0
    )
    return {
        "flow_m3_s": flow["flow_m3_s"],
        "flow_scfm": flow["flow_scfm"],
        "o2_at_time": o2_at_time,
        "capacity_verdict": "PASS" if flow["flow_m3_s"] <= max_nea_capacity_m3_s
        else "FAIL",
    }

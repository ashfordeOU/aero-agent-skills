#!/usr/bin/env python3
"""Bolted joint analysis in composite laminates (stdlib only).

Analyzes a single fastener row in a composite laminate joint under
bearing and bypass loading: bolt bearing stress, net-tension stress
across the net section, shear-out stress at the edge distance, and
the joint margin against each allowable. Paraphrase of standard
mechanical joint analysis methodology; FAR-25 / CS-25 are referenced
only as the certification context for structural joint
substantiation, no standard text is quoted.

Conventions (single fastener row, double shear applies the same
formulas with the total load P):
- Bearing stress: sigma_b = P_b / (D * t), where P_b is the load
  transferred through the bolt (bearing load), D the bolt diameter
  and t the laminate thickness. With a bypass ratio r (fraction of
  the total load carried around the hole through the laminate),
  P_b = (1 - r) * P and P_bp = r * P.
- Net-tension stress: sigma_nt = P / ((w - D) * t), the total load
  crossing the net section of width (w - D) and thickness t. For a
  multi-fastener row the tributary width per fastener is
  min(w, pitch).
- Shear-out stress: sigma_so = P / (2 * e * t), two shear planes of
  length e (edge distance from the hole center to the free edge in
  the load direction) over the thickness t.
- Joint margin: M = F_allow / sigma_applied - 1. A margin >= 0 means
  the applied stress is at or below the allowable.
- Joint efficiency: eta = (w - D) / w, the net-section to gross-
  section width ratio of the joint.

Units: consistent units in, any system (e.g. N, mm, MPa; or lbf, in,
psi); stresses and allowables share the same unit.

All quantities must be strictly positive and the bolt diameter must
be smaller than the width (positive net section). The bypass ratio
must lie in [0, 1]. Violations raise ValueError.
"""

import math


def _require_positive(name, value):
    if value is None or value <= 0.0:
        raise ValueError("%s must be strictly positive: got %r" % (name, value))


def bypass_split(total_load, bypass_ratio):
    """Split total_load into (bypass_load, bearing_load).

    bypass_load = r * P, bearing_load = (1 - r) * P with r the
    bypass ratio in [0, 1]. Raises ValueError otherwise.
    """
    _require_positive("total_load", total_load)
    if bypass_ratio is None or not (0.0 <= bypass_ratio <= 1.0):
        raise ValueError(
            "bypass_ratio must be in [0, 1]: got %r" % (bypass_ratio,)
        )
    bypass_load = bypass_ratio * total_load
    bearing_load = (1.0 - bypass_ratio) * total_load
    return bypass_load, bearing_load


def bearing_stress(bearing_load, bolt_diameter, thickness):
    """Bolt bearing stress sigma_b = P_b / (D * t)."""
    _require_positive("bearing_load", bearing_load)
    _require_positive("bolt_diameter", bolt_diameter)
    _require_positive("thickness", thickness)
    return bearing_load / (bolt_diameter * thickness)


def net_tension_stress(total_load, width, bolt_diameter, thickness):
    """Net-tension stress sigma_nt = P / ((w - D) * t).

    Raises ValueError when the net section (w - D) is not positive.
    """
    _require_positive("total_load", total_load)
    _require_positive("width", width)
    _require_positive("bolt_diameter", bolt_diameter)
    _require_positive("thickness", thickness)
    if bolt_diameter >= width:
        raise ValueError(
            "bolt_diameter must be smaller than width: got D=%.6g, w=%.6g"
            % (bolt_diameter, width)
        )
    return total_load / ((width - bolt_diameter) * thickness)


def shear_out_stress(total_load, edge_distance, thickness):
    """Shear-out stress sigma_so = P / (2 * e * t)."""
    _require_positive("total_load", total_load)
    _require_positive("edge_distance", edge_distance)
    _require_positive("thickness", thickness)
    return total_load / (2.0 * edge_distance * thickness)


def margin_of(allowable, applied):
    """Joint margin M = allowable / applied - 1.

    M >= 0 is a pass against the allowable; M < 0 is a failure.
    """
    _require_positive("allowable", allowable)
    _require_positive("applied", applied)
    return allowable / applied - 1.0


def joint_efficiency(width, bolt_diameter):
    """Joint efficiency eta = (w - D) / w (net/gross width ratio)."""
    _require_positive("width", width)
    _require_positive("bolt_diameter", bolt_diameter)
    if bolt_diameter >= width:
        raise ValueError(
            "bolt_diameter must be smaller than width: got D=%.6g, w=%.6g"
            % (bolt_diameter, width)
        )
    return (width - bolt_diameter) / width


def _effective_width(width, pitch):
    """Tributary width per fastener: min(width, pitch) when pitch set."""
    if pitch is None:
        return width
    _require_positive("pitch", pitch)
    return min(width, pitch)


def joint_analysis(
    load,
    bolt_diameter,
    thickness,
    width,
    edge_distance,
    bearing_allowable,
    net_tension_allowable,
    shear_out_allowable,
    bypass_ratio=0.0,
    pitch=None,
):
    """One-shot bolted joint report in a composite laminate.

    Returns a dict with the bypass and bearing load split, the
    bearing, net-tension and shear-out stresses, the margin of each
    mode against its allowable, the governing mode (lowest margin),
    a pass/fail verdict, and the joint efficiency. bypass_ratio is
    the fraction of the total load carried around the hole; pitch
    (when given) sets the tributary width per fastener for the net
    section.
    """
    _require_positive("load", load)
    _require_positive("bearing_allowable", bearing_allowable)
    _require_positive("net_tension_allowable", net_tension_allowable)
    _require_positive("shear_out_allowable", shear_out_allowable)
    bypass_load, bearing_load = bypass_split(load, bypass_ratio)
    eff_w = _effective_width(width, pitch)
    sigma_b = bearing_stress(bearing_load, bolt_diameter, thickness)
    sigma_nt = net_tension_stress(load, eff_w, bolt_diameter, thickness)
    sigma_so = shear_out_stress(load, edge_distance, thickness)
    m_b = margin_of(bearing_allowable, sigma_b)
    m_nt = margin_of(net_tension_allowable, sigma_nt)
    m_so = margin_of(shear_out_allowable, sigma_so)
    modes = [("bearing", m_b), ("net-tension", m_nt), ("shear-out", m_so)]
    modes.sort(key=lambda pair: (pair[1], pair[0]))
    governing, min_margin = modes[0]
    return {
        "bypass_ratio": bypass_ratio,
        "bypass_load": bypass_load,
        "bearing_load": bearing_load,
        "bearing_stress": sigma_b,
        "net_tension_stress": sigma_nt,
        "shear_out_stress": sigma_so,
        "bearing_margin": m_b,
        "net_tension_margin": m_nt,
        "shear_out_margin": m_so,
        "governing_mode": governing,
        "min_margin": min_margin,
        "passes": min_margin >= 0.0,
        "joint_efficiency": joint_efficiency(eff_w, bolt_diameter),
        "effective_width": eff_w,
    }

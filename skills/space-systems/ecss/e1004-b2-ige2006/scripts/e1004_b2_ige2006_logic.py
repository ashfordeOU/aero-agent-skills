#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.2 IGE-2006 geostationary trapped-electron
flux model logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
IGE-2006 is the ECSS reference model for the long-term-average and
worst-case trapped energetic-electron environment near geostationary
orbit (GEO) and nearby geosynchronous orbits. It gives electron
differential flux as a function of electron energy and L-shell (a band
centered on the nominal GEO L-shell, not a single value), at multiple
confidence levels (a long-term mean plus worst-case percentiles). The
model is defined on a discrete grid of energy and L-shell nodes,
so evaluating it away from a tabulated node requires interpolation,
and a query outside the tabulated node range is an extrapolation that
must be flagged rather than silently clamped. This module implements
that table lookup, interpolation, confidence-level scaling, and
extrapolation/compliance logic; it does not implement the sibling
e1004-geo-ige leaf's decision of when/how to invoke the model for a
mission's GEO flux specification, nor the worst-case internal-charging
electron models (FLUMIC / NASA worst-case GEO, sibling
e1004-internal-charging).
"""

import math

ENERGY_NODES_MEV = (0.03, 0.1, 0.3, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 5.2)

REFERENCE_DIFFERENTIAL_FLUX = {
    0.03: 5.0e7,
    0.1: 1.2e7,
    0.3: 2.0e6,
    0.7: 3.5e5,
    1.0: 1.1e5,
    1.5: 2.0e4,
    2.0: 4.5e3,
    3.0: 3.0e2,
    4.0: 2.5e1,
    5.2: 2.0,
}

L_SHELL_NODES = (5.5, 6.0, 6.6, 7.0)

L_SHELL_SCALE_FACTOR = {
    5.5: 0.4,
    6.0: 0.8,
    6.6: 1.0,
    7.0: 0.6,
}

CONFIDENCE_LEVELS = {
    "mean": 0.50,
    "p90": 0.90,
    "p95": 0.95,
    "p99": 0.99,
}


def _interpolate(x, nodes, values_by_node, log_scale):
    """Shared interpolation core for a value tabulated at ascending
    nodes. Returns (value, extrapolated). Extrapolated is True when x
    falls outside [nodes[0], nodes[-1]], in which case the nearest
    boundary node's value is returned alongside the flag. Raises
    ValueError when x is not positive."""
    if x <= 0:
        raise ValueError("x must be positive")
    if x <= nodes[0]:
        return values_by_node[nodes[0]], (x < nodes[0])
    if x >= nodes[-1]:
        return values_by_node[nodes[-1]], (x > nodes[-1])
    for lo, hi in zip(nodes, nodes[1:]):
        if lo <= x <= hi:
            # Exact node match: return the tabulated value untouched so
            # reference nodes reproduce bit-for-bit (no float drift from
            # the interpolation arithmetic, which otherwise yields e.g.
            # 110000.00000000009 for the 110000.0 reference node).
            if x == lo:
                return values_by_node[lo], False
            if x == hi:
                return values_by_node[hi], False
            y_lo = values_by_node[lo]
            y_hi = values_by_node[hi]
            frac = (x - lo) / (hi - lo)
            if log_scale:
                log_y = math.log10(y_lo) + frac * (math.log10(y_hi) - math.log10(y_lo))
                return 10 ** log_y, False
            return y_lo + frac * (y_hi - y_lo), False
    raise ValueError("x not bracketed by nodes: %r" % (x,))


def interpolate_energy_flux(energy_mev):
    """Reference differential flux at energy_mev (MeV) by log-linear
    interpolation between ENERGY_NODES_MEV. Returns
    (flux, extrapolated)."""
    return _interpolate(energy_mev, ENERGY_NODES_MEV, REFERENCE_DIFFERENTIAL_FLUX, True)


def interpolate_l_shell_scale(l_shell):
    """L-shell scale factor at l_shell by linear interpolation between
    L_SHELL_NODES. Returns (scale_factor, extrapolated)."""
    return _interpolate(l_shell, L_SHELL_NODES, L_SHELL_SCALE_FACTOR, False)


def confidence_scale_factor(confidence_level):
    """Flux scale factor for a named confidence level: 1.0 for "mean",
    increasing for higher worst-case percentiles. Raises ValueError
    for an unrecognized confidence_level."""
    if confidence_level not in CONFIDENCE_LEVELS:
        raise ValueError("unknown confidence level: %r" % (confidence_level,))
    percentile = CONFIDENCE_LEVELS[confidence_level]
    return 1.0 + 8.0 * max(0.0, percentile - 0.5)


def compute_differential_flux(energy_mev, l_shell, confidence_level):
    """Full IGE-2006 differential flux at one (energy, L-shell,
    confidence level) point. Returns a new dict with the flux and the
    extrapolation flags from the energy and L-shell lookups. Raises
    ValueError for a non-positive energy/l_shell or an unrecognized
    confidence_level."""
    base_flux, energy_extrapolated = interpolate_energy_flux(energy_mev)
    l_scale, l_shell_extrapolated = interpolate_l_shell_scale(l_shell)
    conf_scale = confidence_scale_factor(confidence_level)
    return {
        "energy_mev": energy_mev,
        "l_shell": l_shell,
        "confidence_level": confidence_level,
        "differential_flux": base_flux * l_scale * conf_scale,
        "energy_extrapolated": energy_extrapolated,
        "l_shell_extrapolated": l_shell_extrapolated,
        "within_valid_range": not (energy_extrapolated or l_shell_extrapolated),
    }


def build_energy_spectrum_table(energy_mev_list, l_shell, confidence_level):
    """Spectrum table: one compute_differential_flux() entry per
    energy in energy_mev_list, in input order. Raises ValueError when
    energy_mev_list is empty."""
    if not energy_mev_list:
        raise ValueError("energy_mev_list must not be empty")
    return [
        compute_differential_flux(energy_mev, l_shell, confidence_level)
        for energy_mev in energy_mev_list
    ]


def assess_flux_request(case):
    """Full IGE-2006 request assessment for one case dict. Required
    keys: id, energy_mev_list, l_shell, confidence_level. Returns a
    new dict; does not mutate the input. Raises ValueError when 'id'
    is missing."""
    if "id" not in case:
        raise ValueError("flux request case is missing an id")
    table = build_energy_spectrum_table(
        case["energy_mev_list"], case["l_shell"], case["confidence_level"]
    )
    compliant = all(entry["within_valid_range"] for entry in table)
    return {
        "id": case["id"],
        "l_shell": case["l_shell"],
        "confidence_level": case["confidence_level"],
        "spectrum_table": table,
        "compliant": compliant,
    }


def build_assessment(cases):
    """Assessment record: one assess_flux_request() result per case,
    in input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_flux_request(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate flux request case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these carry an extrapolated energy or L-shell lookup and
    cannot support the radiation environment specification as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0

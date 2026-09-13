#!/usr/bin/env python3
"""Surface metallic part bonding (ECSS-E-ST-20-06C clause 6.3.1).

Paraphrased, implementable procedure -- no standard text is reproduced.

Structural and mechanical metallic parts have to be tied to the structural
reference so that differential charging between metal surfaces stays
controlled. The check has four layers:

  1. reachability -- a route must exist from the part to the reference;
  2. series/parallel combination -- joints add, redundant straps divide;
  3. a bond-category ceiling on the lowest-resistance route;
  4. the potential the bond sustains, quasi-static (collected plasma
     current across the bond) and transient (a discharge current through
     the strap resistance plus its inductive term, L * di/dt).

Stdlib only, offline, deterministic.
"""

import heapq
import math

__all__ = [
    "REL_TOL",
    "BOND_CATEGORY_LIMITS_OHM",
    "VACUUM_PERMEABILITY",
    "bond_category_limit",
    "series_resistance",
    "parallel_resistance",
    "strap_inductance",
    "collected_current",
    "quasi_static_potential",
    "transient_bond_potential",
    "within_limit",
    "build_bond_network",
    "effective_resistance_to_reference",
    "evaluate_part_bond",
    "assess_bonding_network",
]

# Relative tolerance used when a measured resistance meets a ceiling
# exactly. A summed route resistance is a sum of powers of ten and can land
# a few ULPs above the algebraic value; the tolerance absorbs that
# representation error without relaxing the engineering ceiling.
REL_TOL = 1e-9

VACUUM_PERMEABILITY = 4.0e-7 * math.pi  # H/m

# DC resistance ceilings (ohm) by bond category. A bond that only has to
# bleed electrostatic charge off a fitting is allowed orders of magnitude
# more than a primary-structure bond.
BOND_CATEGORY_LIMITS_OHM = {
    "primary-structure": 2.5e-3,
    "secondary-structure": 1.0e-2,
    "mechanism-metal": 5.0e-2,
    "electrostatic-bleed": 1.0,
}

DEFAULT_ALLOWABLE_DIFFERENTIAL_POTENTIAL_V = 1.0

_REQUIRED_PART_KEYS = ("id", "category")
_KNOWN_PART_KEYS = set(_REQUIRED_PART_KEYS) | {"exposed_area_m2"}
_REQUIRED_BOND_KEYS = ("from", "to", "resistance_ohm")
_KNOWN_BOND_KEYS = set(_REQUIRED_BOND_KEYS)


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _require_non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def _require_id(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def bond_category_limit(category):
    """DC resistance ceiling (ohm) for a bond category."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    try:
        return BOND_CATEGORY_LIMITS_OHM[category]
    except KeyError:
        raise ValueError(
            "unknown bond category '%s'; known: %s"
            % (category, ", ".join(sorted(BOND_CATEGORY_LIMITS_OHM)))
        )


def series_resistance(segments):
    """Total resistance (ohm) of joints and straps in series."""
    if not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a list or tuple")
    if not segments:
        raise ValueError("segments must not be empty")
    total = 0.0
    for i, segment in enumerate(segments):
        total += _require_non_negative("segments[%d]" % i, segment)
    return total


def parallel_resistance(paths):
    """Effective resistance (ohm) of redundant straps in parallel."""
    if not isinstance(paths, (list, tuple)):
        raise ValueError("paths must be a list or tuple")
    if not paths:
        raise ValueError("paths must not be empty")
    conductance = 0.0
    for i, path in enumerate(paths):
        conductance += 1.0 / _require_positive("paths[%d]" % i, path)
    return 1.0 / conductance


def strap_inductance(length_m, width_m):
    """Series inductance (H) of a flat bonding strap.

    Standard flat-conductor approximation L = (mu0 / 2pi) * l *
    (ln(2 l / w) + 0.5), valid while the strap is long compared with its
    width -- which is exactly the geometry the clause pushes away from.
    """
    length = _require_positive("length_m", length_m)
    width = _require_positive("width_m", width_m)
    if length <= width:
        raise ValueError(
            "strap length %r must exceed its width %r for this approximation"
            % (length_m, width_m)
        )
    return (VACUUM_PERMEABILITY / (2.0 * math.pi)) * length * (
        math.log(2.0 * length / width) + 0.5
    )


def collected_current(current_density_a_m2, exposed_area_m2):
    """Quasi-static current (A) collected by an exposed metal surface."""
    j = _require_non_negative("current_density_a_m2", current_density_a_m2)
    area = _require_positive("exposed_area_m2", exposed_area_m2)
    return j * area


def quasi_static_potential(current_a, resistance_ohm):
    """Potential (V) a bond sustains under a steady collected current."""
    current = _require_non_negative("current_a", current_a)
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    return current * resistance


def transient_bond_potential(peak_current_a, rise_time_s, resistance_ohm, inductance_h=0.0):
    """Potential (V) a bond sustains during a discharge transient.

    Resistive term I * R plus inductive term L * I / t_rise. The inductive
    term dominates for a fast event through a long strap.
    """
    current = _require_positive("peak_current_a", peak_current_a)
    rise = _require_positive("rise_time_s", rise_time_s)
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    inductance = _require_non_negative("inductance_h", inductance_h)
    return current * resistance + inductance * current / rise


def within_limit(value, limit):
    """True when value <= limit, absorbing float representation error."""
    v = _require_non_negative("value", value)
    lim = _require_positive("limit", limit)
    if v <= lim:
        return True
    return math.isclose(v, lim, rel_tol=REL_TOL, abs_tol=0.0)


def build_bond_network(parts, bonds, reference):
    """Adjacency map {node: {neighbour: effective_resistance}}.

    Redundant straps between the same endpoint pair are combined in
    parallel. Raises ValueError on a malformed part, a malformed bond, an
    unknown endpoint or a reference that no bond reaches.
    """
    ref = _require_id("reference", reference)
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a list or tuple")
    if not parts:
        raise ValueError("parts must not be empty")
    if not isinstance(bonds, (list, tuple)):
        raise ValueError("bonds must be a list or tuple")
    if not bonds:
        raise ValueError("bonds must not be empty")

    part_ids = []
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("each part must be a mapping, got %r" % (type(part).__name__,))
        unknown = sorted(set(part) - _KNOWN_PART_KEYS)
        if unknown:
            raise ValueError("part has unknown keys: %s" % ", ".join(unknown))
        for key in _REQUIRED_PART_KEYS:
            if key not in part:
                raise ValueError("part is missing required key '%s'" % key)
        part_id = _require_id("part id", part["id"])
        if part_id == ref:
            raise ValueError(
                "part id '%s' collides with the structural reference" % part_id
            )
        if part_id in part_ids:
            raise ValueError("duplicate part id '%s'" % part_id)
        bond_category_limit(part["category"])
        part_ids.append(part_id)

    known = set(part_ids) | {ref}
    straps = {}
    for bond in bonds:
        if not isinstance(bond, dict):
            raise ValueError("each bond must be a mapping, got %r" % (type(bond).__name__,))
        unknown = sorted(set(bond) - _KNOWN_BOND_KEYS)
        if unknown:
            raise ValueError("bond has unknown keys: %s" % ", ".join(unknown))
        for key in _REQUIRED_BOND_KEYS:
            if key not in bond:
                raise ValueError("bond is missing required key '%s'" % key)
        a = _require_id("bond from", bond["from"])
        b = _require_id("bond to", bond["to"])
        if a == b:
            raise ValueError("bond '%s' loops onto itself" % a)
        for endpoint in (a, b):
            if endpoint not in known:
                raise ValueError(
                    "bond endpoint '%s' is neither a part nor the structural reference" % endpoint
                )
        resistance = _require_positive("bond resistance_ohm", bond["resistance_ohm"])
        straps.setdefault(tuple(sorted((a, b))), []).append(resistance)

    network = {node: {} for node in known}
    for (a, b), values in straps.items():
        effective = parallel_resistance(values)
        network[a][b] = effective
        network[b][a] = effective
    if not network[ref]:
        raise ValueError("structural reference '%s' is not an endpoint of any bond" % ref)
    return network


def effective_resistance_to_reference(network, reference):
    """Lowest series resistance (ohm) from each node to the reference.

    Unreachable nodes map to None. Deterministic shortest-path accumulation
    over the bond network.
    """
    if not isinstance(network, dict) or not network:
        raise ValueError("network must be a non-empty mapping")
    ref = _require_id("reference", reference)
    if ref not in network:
        raise ValueError("reference '%s' is not in the network" % ref)
    best = {node: None for node in network}
    best[ref] = 0.0
    queue = [(0.0, ref)]
    settled = set()
    while queue:
        total, node = heapq.heappop(queue)
        if node in settled:
            continue
        settled.add(node)
        for neighbour, resistance in sorted(network[node].items()):
            if neighbour in settled:
                continue
            candidate = total + resistance
            if best[neighbour] is None or candidate < best[neighbour]:
                best[neighbour] = candidate
                heapq.heappush(queue, (candidate, neighbour))
    return best


def evaluate_part_bond(
    part,
    resistance_ohm,
    current_density_a_m2=0.0,
    allowable_potential_v=DEFAULT_ALLOWABLE_DIFFERENTIAL_POTENTIAL_V,
    discharge=None,
):
    """Evaluate one part against the clause 6.3.1 bonding criteria.

    discharge, when given, is a mapping with peak_current_a, rise_time_s and
    optionally inductance_h.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = _require_id("part id", part.get("id"))
    limit = bond_category_limit(part.get("category"))
    allowable = _require_positive("allowable_potential_v", allowable_potential_v)

    result = {
        "id": part_id,
        "category": part["category"],
        "limit_ohm": limit,
        "resistance_ohm": resistance_ohm,
        "quasi_static_potential_v": None,
        "transient_potential_v": None,
        "findings": [],
    }

    if resistance_ohm is None:
        result["disposition"] = "electrically-isolated"
        result["within_category_limit"] = False
        result["findings"].append("no conductive route to the structural reference")
        return result

    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    within = within_limit(resistance, limit)
    result["within_category_limit"] = within
    if not within:
        result["findings"].append(
            "bond resistance above the %s ceiling" % part["category"]
        )

    area = part.get("exposed_area_m2")
    if area is None:
        result["findings"].append(
            "exposed_area_m2 not declared; quasi-static potential check not performed"
        )
    else:
        current = collected_current(current_density_a_m2, area)
        potential = quasi_static_potential(current, resistance)
        result["quasi_static_potential_v"] = potential
        if not within_limit(potential, allowable):
            result["findings"].append("quasi-static differential potential above the allowable")

    if discharge is not None:
        if not isinstance(discharge, dict):
            raise ValueError("discharge must be a mapping")
        unknown = sorted(set(discharge) - {"peak_current_a", "rise_time_s", "inductance_h"})
        if unknown:
            raise ValueError("discharge has unknown keys: %s" % ", ".join(unknown))
        transient = transient_bond_potential(
            discharge.get("peak_current_a"),
            discharge.get("rise_time_s"),
            resistance,
            inductance_h=discharge.get("inductance_h", 0.0),
        )
        result["transient_potential_v"] = transient
        if not within_limit(transient, allowable):
            result["findings"].append("transient bond potential above the allowable")

    if not result["findings"]:
        result["disposition"] = "bonded-compliant"
    elif area is None and within and len(result["findings"]) == 1:
        result["disposition"] = "incomplete-evidence"
    else:
        result["disposition"] = "bonding-non-compliant"
    return result


def assess_bonding_network(
    parts,
    bonds,
    reference,
    current_density_a_m2=0.0,
    allowable_potential_v=DEFAULT_ALLOWABLE_DIFFERENTIAL_POTENTIAL_V,
    discharge=None,
):
    """Full clause 6.3.1 assessment over a bonding network."""
    network = build_bond_network(parts, bonds, reference)
    resistances = effective_resistance_to_reference(network, reference)
    evaluations = []
    for part in parts:
        evaluations.append(
            evaluate_part_bond(
                part,
                resistances.get(part["id"]),
                current_density_a_m2=current_density_a_m2,
                allowable_potential_v=allowable_potential_v,
                discharge=discharge,
            )
        )
    counts = {
        "bonded-compliant": 0,
        "incomplete-evidence": 0,
        "bonding-non-compliant": 0,
        "electrically-isolated": 0,
    }
    for evaluation in evaluations:
        counts[evaluation["disposition"]] += 1
    isolated = sorted(
        e["id"] for e in evaluations if e["disposition"] == "electrically-isolated"
    )
    return {
        "evaluations": evaluations,
        "counts": counts,
        "isolated_parts": isolated,
        "compliant": counts["bonded-compliant"] == len(evaluations),
    }

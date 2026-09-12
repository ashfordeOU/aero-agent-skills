#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.1.1 single-fault propagation containment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires that a single hardware fault
in one item does not propagate into neighbouring circuits, components
or interfaces. This module turns that requirement into a checkable
procedure: every postulated fault mode is reduced to a propagation
family, every neighbour is reached only through a named coupling
path, a declared containment barrier is credited only where its
coverage includes that family on that path, and a credited series
protection device is additionally checked for selectivity against the
neighbour's steady demand and against the upstream source current
limit. It does not size the protection device itself, derive the
fault-mode list (an FMEA input), or model arc energy.
"""

# Coupling paths through which a fault in one item can reach a neighbour.
PROPAGATION_PATHS = frozenset(
    {
        "shared_power_bus",
        "shared_return_path",
        "harness_adjacency",
        "common_connector_pin",
        "shared_signal_net",
        "thermal_coupling",
    }
)

# Postulated fault mode -> propagation family. A barrier stops a family,
# never a mode, so the mapping is applied before any coverage check.
FAULT_MODE_FAMILIES = {
    "short_to_ground": "conducted_overcurrent",
    "short_to_supply": "conducted_overcurrent",
    "pin_to_pin_short": "conducted_overcurrent",
    "shorted_part": "conducted_overcurrent",
    "regulator_runaway": "conducted_overvoltage",
    "transient_overvoltage": "conducted_overvoltage",
    "open_circuit": "loss_of_continuity",
    "connector_disconnect": "loss_of_continuity",
    "broken_interconnect": "loss_of_continuity",
    "insulation_breakdown": "dielectric_breakdown",
    "surface_arc_tracking": "dielectric_breakdown",
}

PROPAGATION_FAMILIES = frozenset(FAULT_MODE_FAMILIES.values())

# Barrier -> family -> the coupling paths that barrier actually interrupts.
BARRIER_COVERAGE = {
    "series_protection_device": {
        "conducted_overcurrent": frozenset(
            {"shared_power_bus", "common_connector_pin"}
        ),
    },
    "series_blocking_diode": {
        "conducted_overcurrent": frozenset({"shared_power_bus"}),
        "conducted_overvoltage": frozenset({"shared_power_bus"}),
    },
    "galvanic_isolation": {
        "conducted_overcurrent": frozenset(
            {"shared_signal_net", "common_connector_pin", "shared_return_path"}
        ),
        "conducted_overvoltage": frozenset(
            {"shared_signal_net", "common_connector_pin", "shared_return_path"}
        ),
        "dielectric_breakdown": frozenset(
            {"shared_signal_net", "common_connector_pin"}
        ),
    },
    "dedicated_return": {
        "conducted_overcurrent": frozenset({"shared_return_path"}),
        "conducted_overvoltage": frozenset({"shared_return_path"}),
    },
    "clamping_network": {
        "conducted_overvoltage": frozenset(
            {"shared_power_bus", "shared_signal_net", "common_connector_pin"}
        ),
    },
    "physical_separation": {
        "conducted_overcurrent": frozenset({"harness_adjacency"}),
        "dielectric_breakdown": frozenset(
            {"harness_adjacency", "common_connector_pin"}
        ),
    },
    "thermal_isolation": {
        "conducted_overcurrent": frozenset({"thermal_coupling"}),
        "conducted_overvoltage": frozenset({"thermal_coupling"}),
        "loss_of_continuity": frozenset({"thermal_coupling"}),
        "dielectric_breakdown": frozenset({"thermal_coupling"}),
    },
    "redundant_supply_branch": {
        "loss_of_continuity": frozenset(
            {"shared_power_bus", "shared_return_path", "common_connector_pin"}
        ),
    },
}

# Series protection device sizing margins (clause 4.2.1.1 containment
# is defeated if the upstream source current-limits before the device
# clears, or if the device nuisance trips on the neighbour's demand).
DEFAULT_LOAD_MARGIN = 1.25
DEFAULT_CLEARING_MARGIN = 2.0


def fault_family(fault_mode):
    """Propagation family of a postulated fault mode. Raises ValueError
    for a fault mode outside the recognised set."""
    try:
        return FAULT_MODE_FAMILIES[fault_mode]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized fault mode %r under E-ST-20C clause 4.2.1.1"
            % (fault_mode,)
        )


def barrier_blocks(barrier, family, path):
    """True when `barrier` interrupts propagation family `family` on
    coupling path `path`. Raises ValueError for an unrecognised
    barrier, family or path -- an unknown barrier must never be
    silently credited."""
    if barrier not in BARRIER_COVERAGE:
        raise ValueError("unrecognized containment barrier %r" % (barrier,))
    if family not in PROPAGATION_FAMILIES:
        raise ValueError("unrecognized propagation family %r" % (family,))
    if path not in PROPAGATION_PATHS:
        raise ValueError("unrecognized coupling path %r" % (path,))
    return path in BARRIER_COVERAGE[barrier].get(family, frozenset())


def propagation_blocked(fault_mode, path, barriers):
    """Containment result for one (fault mode, coupling path) pair.

    barriers: iterable of declared barrier names. Returns
    {"family": str, "blocked": bool, "barrier": str | None} where
    "barrier" names the first barrier whose coverage includes the
    family on that path. Raises ValueError via fault_family /
    barrier_blocks for any unrecognised input."""
    family = fault_family(fault_mode)
    if path not in PROPAGATION_PATHS:
        raise ValueError("unrecognized coupling path %r" % (path,))
    for barrier in barriers:
        if barrier_blocks(barrier, family, path):
            return {"family": family, "blocked": True, "barrier": barrier}
    return {"family": family, "blocked": False, "barrier": None}


def protection_selectivity(
    steady_demand_a,
    protection_rating_a,
    source_current_limit_a,
    load_margin=DEFAULT_LOAD_MARGIN,
    clearing_margin=DEFAULT_CLEARING_MARGIN,
):
    """Selectivity of a credited series protection device.

    Returns {"load_ratio": rating/demand, "clearing_ratio":
    source_limit/rating, "selective": bool, "findings": [str]}. The
    device is selective when it sits far enough above the neighbour's
    steady demand not to nuisance trip and far enough below the
    upstream source current limit to clear before the source limits.
    Raises ValueError for a non-positive current or a margin < 1."""
    for label, value in (
        ("steady_demand_a", steady_demand_a),
        ("protection_rating_a", protection_rating_a),
        ("source_current_limit_a", source_current_limit_a),
    ):
        if value <= 0:
            raise ValueError("%s must be > 0 (got %r)" % (label, value))
    for label, value in (
        ("load_margin", load_margin),
        ("clearing_margin", clearing_margin),
    ):
        if value < 1.0:
            raise ValueError("%s must be >= 1.0 (got %r)" % (label, value))
    load_ratio = protection_rating_a / steady_demand_a
    clearing_ratio = source_current_limit_a / protection_rating_a
    findings = []
    if load_ratio < load_margin:
        findings.append("protection_rating_below_load_margin")
    if clearing_ratio < clearing_margin:
        findings.append("source_limits_before_protection_clears")
    return {
        "load_ratio": load_ratio,
        "clearing_ratio": clearing_ratio,
        "selective": not findings,
        "findings": findings,
    }


def containment_violations(item):
    """Propagation findings for one faulted item.

    item: {"item_id": str, "fault_modes": [str], "couplings":
    [{"neighbour": str, "path": str}], "barriers": [str]}. Returns a
    list of findings, one per uncontained (fault mode, coupling) pair.
    Raises ValueError for a missing item_id or any unrecognised fault
    mode, path or barrier. Does not mutate `item`."""
    item_id = item.get("item_id")
    if not item_id:
        raise ValueError("item is missing a non-empty 'item_id'")
    barriers = list(item.get("barriers", []))
    findings = []
    for fault_mode in item.get("fault_modes", []):
        for coupling in item.get("couplings", []):
            path = coupling["path"]
            result = propagation_blocked(fault_mode, path, barriers)
            if not result["blocked"]:
                findings.append(
                    {
                        "issue": "fault_propagates_to_neighbour",
                        "item": item_id,
                        "fault_mode": fault_mode,
                        "family": result["family"],
                        "path": path,
                        "neighbour": coupling["neighbour"],
                    }
                )
    return findings


def protection_violations(item):
    """Protection-sizing findings for one faulted item. Evaluated only
    when the item declares a "protection" mapping with keys
    "steady_demand_a", "protection_rating_a", "source_current_limit_a"
    (optional "load_margin", "clearing_margin"). An item crediting
    "series_protection_device" without a protection mapping is itself
    a finding -- the barrier cannot be verified."""
    item_id = item.get("item_id")
    if not item_id:
        raise ValueError("item is missing a non-empty 'item_id'")
    protection = item.get("protection")
    if protection is None:
        if "series_protection_device" in item.get("barriers", []):
            return [
                {
                    "issue": "credited_protection_device_not_sized",
                    "item": item_id,
                }
            ]
        return []
    result = protection_selectivity(
        protection["steady_demand_a"],
        protection["protection_rating_a"],
        protection["source_current_limit_a"],
        protection.get("load_margin", DEFAULT_LOAD_MARGIN),
        protection.get("clearing_margin", DEFAULT_CLEARING_MARGIN),
    )
    return [
        {
            "issue": finding,
            "item": item_id,
            "load_ratio": result["load_ratio"],
            "clearing_ratio": result["clearing_ratio"],
        }
        for finding in result["findings"]
    ]


def containment_review(item):
    """Full clause 4.2.1.1 containment review for one item. Returns
    {"propagation": [...], "protection": [...]}, each a finding list."""
    return {
        "propagation": containment_violations(item),
        "protection": protection_violations(item),
    }


def is_single_fault_contained(review):
    """True when both finding lists in a containment_review result are
    empty -- the item's single-fault containment argument holds."""
    return all(len(findings) == 0 for findings in review.values())

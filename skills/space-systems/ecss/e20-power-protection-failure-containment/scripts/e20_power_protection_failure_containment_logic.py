#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.3 power protection and failure containment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the protection functions of a
power converter or regulator to be independent of the functions they
protect, so that a single fault is contained in its own branch instead
of propagating onto the distribution bus. This module implements the
checkable part of that argument: categorization of a protection
function into its family, detection of shared failure-prone resources
between a protection and the function it protects, derivation of the
feasible trip-threshold window from load current, inrush and the
harness/source fault rating, selectivity between a downstream and an
upstream protection, and comparison of the protection response time
against the bus ride-through time. It does not model device physics
(arc energy, fuse I2t curves, semiconductor safe operating area) and
it does not select protection hardware.
"""

CURRENT_LIMITING_PROTECTIONS = frozenset(
    {
        "latching_current_limiter",
        "foldback_current_limiter",
        "fuse",
        "circuit_breaker",
    }
)
VOLTAGE_LIMITING_PROTECTIONS = frozenset(
    {"overvoltage_trip", "undervoltage_lockout", "transient_clamp"}
)
THERMAL_PROTECTIONS = frozenset({"overtemperature_trip", "thermal_foldback"})
ISOLATING_PROTECTIONS = frozenset(
    {"series_isolation_switch", "blocking_diode", "galvanic_barrier"}
)

# Resources whose sharing between a protection function and the function
# it protects defeats containment: one failure then takes out both.
CONTAINMENT_BREAKING_RESOURCES = frozenset(
    {
        "sense_element",
        "voltage_reference",
        "control_loop",
        "housekeeping_supply",
        "return_path",
    }
)

DEFAULT_TRIP_MARGIN_FRACTION = 0.20
DEFAULT_SELECTIVITY_RATIO = 1.50

TRIP_SETTING_OK = "ok"
TRIP_SETTING_BELOW_WINDOW = "below_window"
TRIP_SETTING_ABOVE_WINDOW = "above_window"
TRIP_WINDOW_INFEASIBLE = "infeasible_window"


def categorize_protection_function(protection_type):
    """Protection family for a device type: "current_limiting",
    "voltage_limiting", "thermal" or "isolating". Raises ValueError for
    a device type that is not a clause 5.3 protection function."""
    if protection_type in CURRENT_LIMITING_PROTECTIONS:
        return "current_limiting"
    if protection_type in VOLTAGE_LIMITING_PROTECTIONS:
        return "voltage_limiting"
    if protection_type in THERMAL_PROTECTIONS:
        return "thermal"
    if protection_type in ISOLATING_PROTECTIONS:
        return "isolating"
    raise ValueError(
        "unrecognized protection function type %r under "
        "E-ST-20C clause 5.3" % (protection_type,)
    )


def independence_findings(
    protection_id, shared_resources, powered_from_protected_rail=False
):
    """Findings (empty when independent) for one protection function.

    shared_resources: iterable of resource names shared between the
    protection and the function it protects. Every entry that is in
    CONTAINMENT_BREAKING_RESOURCES is reported; entries outside that
    set (for example a shared mechanical bracket) are ignored.
    powered_from_protected_rail: True when the protection draws its own
    housekeeping power from the rail it is meant to disconnect, which
    is reported as a separate dependency. Raises ValueError when
    protection_id is empty."""
    if not protection_id:
        raise ValueError("protection_id must be a non-empty identifier")
    findings = []
    for resource in sorted(set(shared_resources)):
        if resource in CONTAINMENT_BREAKING_RESOURCES:
            findings.append(
                {
                    "issue": "shared_resource_defeats_independence",
                    "protection": protection_id,
                    "resource": resource,
                }
            )
    if powered_from_protected_rail:
        findings.append(
            {
                "issue": "protection_powered_from_protected_rail",
                "protection": protection_id,
            }
        )
    return findings


def trip_threshold_window(
    load_steady_a,
    inrush_peak_a,
    fault_rating_a,
    margin_fraction=DEFAULT_TRIP_MARGIN_FRACTION,
):
    """Feasible (min_trip_a, max_trip_a) window for a current-limiting
    protection.

    Lower bound: the larger of steady-state draw and inrush peak raised
    by margin_fraction, so normal transients do not nuisance-trip.
    Upper bound: the harness/source fault rating reduced by the same
    fraction, so the protection acts before the wiring or the source.
    The window may be empty (min > max); that is a sizing defect the
    caller detects with check_trip_setting, not an input error.
    Raises ValueError for negative currents, a non-positive fault
    rating, an inrush peak below the steady-state draw, or a
    margin_fraction outside [0, 1)."""
    if load_steady_a < 0:
        raise ValueError("load_steady_a must be >= 0")
    if inrush_peak_a < 0:
        raise ValueError("inrush_peak_a must be >= 0")
    if inrush_peak_a < load_steady_a:
        raise ValueError("inrush_peak_a must be >= load_steady_a")
    if fault_rating_a <= 0:
        raise ValueError("fault_rating_a must be > 0")
    if not 0 <= margin_fraction < 1:
        raise ValueError("margin_fraction must be in [0, 1)")
    min_trip_a = max(load_steady_a, inrush_peak_a) * (1.0 + margin_fraction)
    max_trip_a = fault_rating_a * (1.0 - margin_fraction)
    return (min_trip_a, max_trip_a)


def check_trip_setting(trip_setting_a, window):
    """Verdict for an as-designed trip setting against a
    trip_threshold_window result: TRIP_WINDOW_INFEASIBLE when the
    window is empty, TRIP_SETTING_BELOW_WINDOW / _ABOVE_WINDOW when the
    setting falls outside it, TRIP_SETTING_OK otherwise. Raises
    ValueError for a non-positive setting."""
    if trip_setting_a <= 0:
        raise ValueError("trip_setting_a must be > 0")
    min_trip_a, max_trip_a = window
    if min_trip_a > max_trip_a:
        return TRIP_WINDOW_INFEASIBLE
    if trip_setting_a < min_trip_a:
        return TRIP_SETTING_BELOW_WINDOW
    if trip_setting_a > max_trip_a:
        return TRIP_SETTING_ABOVE_WINDOW
    return TRIP_SETTING_OK


def selectivity_ratio(downstream_trip_a, upstream_trip_a):
    """Ratio of the source-side trip level to the load-side one. A ratio
    above 1 means the downstream protection is set to act first. Raises
    ValueError for a non-positive level."""
    if downstream_trip_a <= 0:
        raise ValueError("downstream_trip_a must be > 0")
    if upstream_trip_a <= 0:
        raise ValueError("upstream_trip_a must be > 0")
    return upstream_trip_a / downstream_trip_a


def selectivity_findings(
    branch_id,
    downstream_trip_a,
    upstream_trip_a,
    minimum_ratio=DEFAULT_SELECTIVITY_RATIO,
):
    """Findings (empty when coordinated) for the downstream/upstream
    trip pair on a branch. Raises ValueError for a minimum_ratio that is
    not greater than 1, or via selectivity_ratio for a bad level."""
    if minimum_ratio <= 1:
        raise ValueError("minimum_ratio must be > 1")
    ratio = selectivity_ratio(downstream_trip_a, upstream_trip_a)
    if ratio < minimum_ratio:
        return [
            {
                "issue": "insufficient_trip_selectivity",
                "branch": branch_id,
                "ratio": ratio,
                "minimum_ratio": minimum_ratio,
            }
        ]
    return []


def response_time_findings(branch_id, response_time_ms, bus_ride_through_ms):
    """Findings (empty when fast enough) for the protection clearing
    time against the bus ride-through time. Equal times are a finding:
    clearing must complete strictly before the bus leaves its
    undervoltage limit. Raises ValueError for a non-positive response
    time or ride-through time."""
    if response_time_ms <= 0:
        raise ValueError("response_time_ms must be > 0")
    if bus_ride_through_ms <= 0:
        raise ValueError("bus_ride_through_ms must be > 0")
    if response_time_ms >= bus_ride_through_ms:
        return [
            {
                "issue": "protection_slower_than_bus_ride_through",
                "branch": branch_id,
                "response_time_ms": response_time_ms,
                "bus_ride_through_ms": bus_ride_through_ms,
            }
        ]
    return []


def containment_review(branch):
    """Full clause 5.3 containment review for one protected branch.

    branch: {"branch_id": str, "protections": [{"protection_id": str,
    "protection_type": str, "shared_resources": [str],
    "powered_from_protected_rail": bool}], "load_steady_a": float,
    "inrush_peak_a": float, "fault_rating_a": float,
    "trip_setting_a": float, "upstream_trip_a": float,
    "response_time_ms": float, "bus_ride_through_ms": float,
    "margin_fraction": float (optional),
    "minimum_selectivity_ratio": float (optional)}.

    Returns {"independence": [...], "threshold": [...],
    "selectivity": [...], "timing": [...]}. Raises ValueError through
    the helpers for an unrecognized protection type or an invalid
    electrical input. Does not mutate branch."""
    branch_id = branch["branch_id"]
    independence = []
    for protection in branch.get("protections", []):
        categorize_protection_function(protection["protection_type"])
        independence.extend(
            independence_findings(
                protection["protection_id"],
                protection.get("shared_resources", ()),
                protection.get("powered_from_protected_rail", False),
            )
        )
    window = trip_threshold_window(
        branch["load_steady_a"],
        branch["inrush_peak_a"],
        branch["fault_rating_a"],
        branch.get("margin_fraction", DEFAULT_TRIP_MARGIN_FRACTION),
    )
    verdict = check_trip_setting(branch["trip_setting_a"], window)
    threshold = []
    if verdict != TRIP_SETTING_OK:
        threshold.append(
            {
                "issue": "trip_setting_%s" % verdict,
                "branch": branch_id,
                "trip_setting_a": branch["trip_setting_a"],
                "window": window,
            }
        )
    return {
        "independence": independence,
        "threshold": threshold,
        "selectivity": selectivity_findings(
            branch_id,
            branch["trip_setting_a"],
            branch["upstream_trip_a"],
            branch.get("minimum_selectivity_ratio", DEFAULT_SELECTIVITY_RATIO),
        ),
        "timing": response_time_findings(
            branch_id, branch["response_time_ms"], branch["bus_ride_through_ms"]
        ),
    }


def is_containment_compliant(review):
    """True when every finding list in a containment_review result is
    empty -- the branch contains its own faults for this assessment."""
    return all(len(findings) == 0 for findings in review.values())

"""Frequency band selection for a space link.

Anchor: ECSS-E-ST-50C clause 5.6.12.2 -- requirements on the selection of the
frequency band a space link operates in. Paraphrased into an implementable
procedure; no standard text is reproduced.

One normative obligation is implemented: the band chosen for a link is one
allocated to the service that link performs, in the region it operates over,
and the whole of the bandwidth the link necessarily occupies sits inside that
allocation. A band that merely overlaps an allocation is not a band the link
may use, and a secondary allocation is usable but carries no protection from
the primary services sharing it -- so the status is reported, never folded into
a pass.

Arithmetic stays with add, subtract, multiply and divide so the result is
reproducible across platforms, and containment is decided with a tolerance so a
band whose edge lands exactly on an allocation boundary comes out the same way
everywhere.
"""

import math

__all__ = [
    "ALLOCATED_PRIMARY",
    "ALLOCATED_SECONDARY",
    "PARTIALLY_OUTSIDE",
    "NOT_ALLOCATED",
    "STATUSES",
    "REL_TOL",
    "validate_frequency",
    "validate_bandwidth",
    "validate_region",
    "normalize_allocation",
    "normalize_request",
    "occupied_band",
    "allocation_occupancy",
    "feasible_centre_range",
    "assess_band_choice",
    "rank_candidate_allocations",
]

ALLOCATED_PRIMARY = "allocated-primary"
ALLOCATED_SECONDARY = "allocated-secondary"
PARTIALLY_OUTSIDE = "partially-outside-allocation"
NOT_ALLOCATED = "not-allocated"

STATUSES = ("primary", "secondary")

# Relative tolerance for the containment comparison, scaled by the frequency
# in play. A band edge that should sit exactly on an allocation boundary must
# not be pushed outside by the last bit of an addition.
REL_TOL = 1e-12


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_frequency(value, name="frequency_hz"):
    """Return a strictly positive frequency in hertz."""
    frequency = _validate_number(value, name)
    if frequency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return frequency


def validate_bandwidth(value, name="bandwidth_hz"):
    """Return a strictly positive bandwidth in hertz."""
    bandwidth = _validate_number(value, name)
    if bandwidth <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return bandwidth


def validate_region(value, name="region"):
    """Return one of the three regulatory regions as an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be the integer 1, 2 or 3" % name)
    if value not in (1, 2, 3):
        raise ValueError("%s must be 1, 2 or 3, got %r" % (name, value))
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    return value.strip()


def normalize_allocation(record):
    """Return one regulatory allocation as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("allocation must be a mapping")
    for key in ("service", "lower_hz", "upper_hz", "status"):
        if key not in record:
            raise ValueError("allocation is missing %s" % key)
    lower = validate_frequency(record["lower_hz"], "lower_hz")
    upper = validate_frequency(record["upper_hz"], "upper_hz")
    if upper <= lower:
        raise ValueError("allocation upper_hz must exceed lower_hz")
    status = _text(record["status"], "status").lower()
    if status not in STATUSES:
        raise ValueError("status must be primary or secondary, got %r" % status)
    regions = record.get("regions", (1, 2, 3))
    if isinstance(regions, (str, dict)) or not isinstance(regions, (list, tuple)):
        raise ValueError("regions must be a list or tuple of region numbers")
    if not regions:
        raise ValueError("regions must not be empty")
    normalized_regions = tuple(sorted({validate_region(r) for r in regions}))
    return {
        "service": _text(record["service"], "service").lower(),
        "lower_hz": lower,
        "upper_hz": upper,
        "width_hz": upper - lower,
        "status": status,
        "regions": normalized_regions,
    }


def normalize_request(record):
    """Return one band request as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("request must be a mapping")
    for key in ("service", "centre_hz", "necessary_bandwidth_hz"):
        if key not in record:
            raise ValueError("request is missing %s" % key)
    centre = validate_frequency(record["centre_hz"], "centre_hz")
    bandwidth = validate_bandwidth(
        record["necessary_bandwidth_hz"], "necessary_bandwidth_hz"
    )
    if bandwidth >= 2.0 * centre:
        raise ValueError(
            "necessary_bandwidth_hz would place the lower band edge at or below "
            "zero hertz"
        )
    return {
        "service": _text(record["service"], "service").lower(),
        "centre_hz": centre,
        "necessary_bandwidth_hz": bandwidth,
        "region": validate_region(record.get("region", 1)),
    }


def occupied_band(centre_hz, necessary_bandwidth_hz):
    """Return the lower and upper edge the link necessarily occupies."""
    centre = validate_frequency(centre_hz, "centre_hz")
    bandwidth = validate_bandwidth(necessary_bandwidth_hz, "necessary_bandwidth_hz")
    half = bandwidth / 2.0
    if half >= centre:
        raise ValueError("necessary_bandwidth_hz places the lower edge at or below zero")
    return (centre - half, centre + half)


def allocation_occupancy(allocation, necessary_bandwidth_hz):
    """Return how much of an allocation this link's bandwidth consumes."""
    allocation = normalize_allocation(allocation)
    bandwidth = validate_bandwidth(necessary_bandwidth_hz, "necessary_bandwidth_hz")
    return bandwidth / allocation["width_hz"]


def feasible_centre_range(allocation, necessary_bandwidth_hz):
    """Return the centre frequencies at which this bandwidth fits the allocation.

    Raises when the allocation is narrower than the bandwidth the link needs --
    there is no centre that would make it fit, and returning an inverted range
    would let a caller act on nonsense.
    """
    allocation = normalize_allocation(allocation)
    bandwidth = validate_bandwidth(necessary_bandwidth_hz, "necessary_bandwidth_hz")
    if bandwidth > allocation["width_hz"] * (1.0 + REL_TOL):
        raise ValueError(
            "necessary_bandwidth_hz %r exceeds the allocation width %r"
            % (bandwidth, allocation["width_hz"])
        )
    half = bandwidth / 2.0
    return (allocation["lower_hz"] + half, allocation["upper_hz"] - half)


def _applies(allocation, request):
    return (
        allocation["service"] == request["service"]
        and request["region"] in allocation["regions"]
    )


def _contains(allocation, lower, upper, tolerance):
    return (
        lower >= allocation["lower_hz"] - tolerance
        and upper <= allocation["upper_hz"] + tolerance
    )


def _overlaps(allocation, lower, upper, tolerance):
    return (
        upper > allocation["lower_hz"] + tolerance
        and lower < allocation["upper_hz"] - tolerance
    )


def _normalize_allocations(allocations):
    if isinstance(allocations, dict) or not isinstance(allocations, (list, tuple)):
        raise ValueError("allocations must be a list or tuple of mappings")
    if not allocations:
        raise ValueError("allocations must not be empty")
    return [normalize_allocation(record) for record in allocations]


def assess_band_choice(request, allocations):
    """Decide whether a requested band may be used for this link.

    Returns the occupied edges, the allocation the band sits inside where one
    exists, the status of that allocation, and a four-way verdict separating a
    contained primary allocation, a contained secondary allocation, a band that
    spills out of the allocation it overlaps, and a band with no allocation for
    the service at all.
    """
    request = normalize_request(request)
    catalogue = _normalize_allocations(allocations)
    lower, upper = occupied_band(
        request["centre_hz"], request["necessary_bandwidth_hz"]
    )
    tolerance = REL_TOL * request["centre_hz"]

    applicable = [item for item in catalogue if _applies(item, request)]
    containing = [
        item for item in applicable if _contains(item, lower, upper, tolerance)
    ]
    overlapping = [
        item
        for item in applicable
        if _overlaps(item, lower, upper, tolerance)
        and not _contains(item, lower, upper, tolerance)
    ]

    findings = []
    matched = None
    if containing:
        primary = [item for item in containing if item["status"] == "primary"]
        matched = primary[0] if primary else containing[0]
        verdict = (
            ALLOCATED_PRIMARY if matched["status"] == "primary" else ALLOCATED_SECONDARY
        )
        if verdict == ALLOCATED_SECONDARY:
            findings.append(
                "the allocation is secondary; the link must accept interference "
                "from and cause none to the primary services sharing the band"
            )
    elif overlapping:
        matched = overlapping[0]
        verdict = PARTIALLY_OUTSIDE
        spill_low = max(0.0, matched["lower_hz"] - lower)
        spill_high = max(0.0, upper - matched["upper_hz"])
        findings.append(
            "the necessary bandwidth spills %.6g Hz below and %.6g Hz above the "
            "allocation it overlaps" % (spill_low, spill_high)
        )
    else:
        verdict = NOT_ALLOCATED
        findings.append(
            "no allocation for service %r in region %d covers this band"
            % (request["service"], request["region"])
        )

    return {
        "service": request["service"],
        "region": request["region"],
        "centre_hz": request["centre_hz"],
        "necessary_bandwidth_hz": request["necessary_bandwidth_hz"],
        "lower_edge_hz": lower,
        "upper_edge_hz": upper,
        "allocation": matched,
        "status": matched["status"] if matched else None,
        "occupancy": (
            request["necessary_bandwidth_hz"] / matched["width_hz"] if matched else None
        ),
        "usable": verdict in (ALLOCATED_PRIMARY, ALLOCATED_SECONDARY),
        "protected": verdict == ALLOCATED_PRIMARY,
        "verdict": verdict,
        "findings": findings,
    }


def rank_candidate_allocations(request, allocations):
    """Return the allocations this link could sit inside, best first.

    Primary allocations rank ahead of secondary ones, and within a status the
    allocation the link consumes least of ranks first, because that is the one
    leaving room for the rest of the mission.
    """
    request = normalize_request(request)
    catalogue = _normalize_allocations(allocations)
    bandwidth = request["necessary_bandwidth_hz"]
    candidates = []
    for allocation in catalogue:
        if not _applies(allocation, request):
            continue
        if bandwidth > allocation["width_hz"] * (1.0 + REL_TOL):
            continue
        low_centre, high_centre = feasible_centre_range(allocation, bandwidth)
        candidates.append(
            {
                "service": allocation["service"],
                "lower_hz": allocation["lower_hz"],
                "upper_hz": allocation["upper_hz"],
                "status": allocation["status"],
                "occupancy": bandwidth / allocation["width_hz"],
                "centre_range_hz": (low_centre, high_centre),
            }
        )
    candidates.sort(
        key=lambda item: (
            0 if item["status"] == "primary" else 1,
            item["occupancy"],
            item["lower_hz"],
        )
    )
    return candidates

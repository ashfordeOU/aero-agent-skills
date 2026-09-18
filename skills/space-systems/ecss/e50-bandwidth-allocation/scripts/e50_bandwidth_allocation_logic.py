"""Bandwidth allocation for a space communication link.

Anchor: ECSS-E-ST-50C clause 5.3.1 -- allocation of link bandwidth to the data
flows the communication system carries. Paraphrased into an implementable
procedure; no standard text is reproduced.

Two normative obligations are implemented:
  (a) each data flow is allocated the bandwidth it needs, sized from its own
      rate and the overhead the protocol stack adds to it -- the allocation is
      what the flow costs on the link, not what the application emits;
  (b) the sum of the allocations, together with the margin the design reserves,
      stays inside the capacity of the link they share, so an oversubscribed
      link is a design-time finding rather than a first-pass surprise.

Arithmetic is kept to add, subtract, multiply and divide so the result is
reproducible across platforms, and the capacity comparison carries a relative
tolerance so a flow set landing exactly on the usable capacity is feasible
everywhere rather than only where the rounding fell kindly.
"""

import math

__all__ = [
    "WITHIN_CAPACITY",
    "MARGIN_SHORT",
    "OVERSUBSCRIBED",
    "REL_TOL",
    "validate_rate",
    "validate_overhead_factor",
    "validate_margin_fraction",
    "flow_allocation",
    "normalize_flow",
    "allocate_bandwidth",
    "required_capacity",
    "scale_to_capacity",
]

WITHIN_CAPACITY = "within-capacity"
MARGIN_SHORT = "margin-short"
OVERSUBSCRIBED = "oversubscribed"

# Relative tolerance for the capacity comparison. A total that should equal the
# usable capacity must not fail on the last bit of a division.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_rate(value, name="rate_bps"):
    """Return a strictly positive data rate in bits per second."""
    rate = _validate_number(value, name)
    if rate <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return rate


def validate_overhead_factor(value, name="overhead_factor"):
    """Return the protocol overhead factor, which never shrinks a flow."""
    factor = _validate_number(value, name)
    if factor < 1.0:
        raise ValueError(
            "%s must be at least 1.0; overhead cannot make a flow smaller than "
            "its own payload, got %r" % (name, value)
        )
    return factor


def validate_margin_fraction(value, name="margin_fraction"):
    """Return the reserved margin as a fraction of capacity in [0, 1)."""
    margin = _validate_number(value, name)
    if margin < 0.0 or margin >= 1.0:
        raise ValueError(
            "%s must be at least 0 and less than 1, got %r" % (name, value)
        )
    return margin


def flow_allocation(rate_bps, overhead_factor=1.0):
    """Return what one flow costs on the link, overhead included."""
    return validate_rate(rate_bps) * validate_overhead_factor(overhead_factor)


def normalize_flow(record):
    """Return one declared flow as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("flow must be a mapping with name and rate_bps")
    if "name" not in record:
        raise ValueError("flow is missing name")
    if not isinstance(record["name"], str) or not record["name"].strip():
        raise ValueError("flow name must be a non-empty string")
    if "rate_bps" not in record:
        raise ValueError("flow %r is missing rate_bps" % record["name"])
    overhead = record.get("overhead_factor", 1.0)
    return {
        "name": record["name"].strip(),
        "rate_bps": validate_rate(record["rate_bps"]),
        "overhead_factor": validate_overhead_factor(overhead),
    }


def _normalize_flows(flows):
    if isinstance(flows, dict) or not isinstance(flows, (list, tuple)):
        raise ValueError("flows must be a list or tuple of flow mappings")
    if not flows:
        raise ValueError("flows must not be empty")
    normalized = [normalize_flow(record) for record in flows]
    seen = set()
    for flow in normalized:
        if flow["name"] in seen:
            raise ValueError("flow %r declared more than once" % flow["name"])
        seen.add(flow["name"])
    return normalized


def allocate_bandwidth(flows, capacity_bps, margin_fraction=0.0):
    """Allocate the link to the flows and report whether it fits.

    Returns the per-flow allocations, the aggregate, the usable capacity once
    margin is reserved, the margin actually achieved, and the shortfall when the
    flows do not fit.
    """
    normalized = _normalize_flows(flows)
    capacity = validate_rate(capacity_bps, "capacity_bps")
    margin = validate_margin_fraction(margin_fraction)
    allocations = []
    total = 0.0
    for flow in normalized:
        allocated = flow["rate_bps"] * flow["overhead_factor"]
        allocations.append(
            {
                "name": flow["name"],
                "rate_bps": flow["rate_bps"],
                "overhead_factor": flow["overhead_factor"],
                "allocated_bps": allocated,
                "share_of_capacity": allocated / capacity,
            }
        )
        total += allocated
    usable = capacity * (1.0 - margin)
    tolerance = REL_TOL * capacity
    fits_usable = total <= usable + tolerance
    fits_capacity = total <= capacity + tolerance
    achieved_margin = (capacity - total) / capacity
    if fits_usable:
        verdict = WITHIN_CAPACITY
    elif fits_capacity:
        verdict = MARGIN_SHORT
    else:
        verdict = OVERSUBSCRIBED
    shortfall = 0.0 if fits_usable else total - usable
    findings = []
    if verdict == MARGIN_SHORT:
        findings.append(
            "flows fit the link but eat into the reserved margin; %.6g bit/s of "
            "headroom is missing" % shortfall
        )
    elif verdict == OVERSUBSCRIBED:
        findings.append(
            "allocated %.6g bit/s against a usable %.6g bit/s; the link is "
            "oversubscribed" % (total, usable)
        )
    return {
        "allocations": allocations,
        "total_allocated_bps": total,
        "capacity_bps": capacity,
        "usable_bps": usable,
        "margin_fraction": margin,
        "achieved_margin_fraction": achieved_margin,
        "shortfall_bps": shortfall,
        "feasible": fits_usable,
        "verdict": verdict,
        "findings": findings,
    }


def required_capacity(flows, margin_fraction=0.0):
    """Return the capacity these flows need with the margin reserved."""
    normalized = _normalize_flows(flows)
    margin = validate_margin_fraction(margin_fraction)
    total = 0.0
    for flow in normalized:
        total += flow["rate_bps"] * flow["overhead_factor"]
    return total / (1.0 - margin)


def scale_to_capacity(flows, capacity_bps, margin_fraction=0.0):
    """Scale every flow by one common factor so the set fits the usable capacity.

    A proportional cut is the neutral answer when the clause's obligation cannot
    be met as declared: it holds the relative sizing the design chose, and it
    makes the size of the problem explicit as a single number.
    """
    result = allocate_bandwidth(flows, capacity_bps, margin_fraction)
    if result["feasible"]:
        factor = 1.0
    else:
        factor = result["usable_bps"] / result["total_allocated_bps"]
    scaled = []
    for allocation in result["allocations"]:
        scaled.append(
            {
                "name": allocation["name"],
                "allocated_bps": allocation["allocated_bps"] * factor,
            }
        )
    return {
        "scale_factor": factor,
        "allocations": scaled,
        "feasible_as_declared": result["feasible"],
        "verdict": result["verdict"],
    }

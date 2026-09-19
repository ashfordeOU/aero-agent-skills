"""Management service for an inter-spacecraft network.

Anchor: ECSS-E-ST-50C clause 5.7.4.3 -- inter-spacecraft network management
service. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that the inter-spacecraft network provides a
management service to the entity that operates it. A service either exists or
it does not, so the assessment has three parts a reviewer can check:

  coverage    -- the management functions the service declares against the
                 functions an operable network needs;
  cost        -- the management traffic the service itself puts on the link,
                 as a share of the capacity the user data was sized for;
  timeliness  -- how long the network takes to notice a topology change and
                 settle again, against the time the operator has.

Sizing is the same model read backwards: the longest polling period that still
converges in time, and the largest member count the overhead allowance holds.
"""

import math

__all__ = [
    "COMPLETE",
    "DEFICIENT",
    "REQUIRED_FUNCTIONS",
    "REL_TOL",
    "validate_nonnegative",
    "validate_positive",
    "validate_count",
    "function_coverage",
    "management_overhead_bps",
    "overhead_fraction",
    "detection_time_s",
    "convergence_time_s",
    "max_poll_period_s",
    "max_managed_members",
    "assess_management_service",
]

COMPLETE = "management-service-complete"
DEFICIENT = "management-service-deficient"

# Relative tolerance on every bound comparison, so a design landing exactly on
# an allowance reads the same on every build host.
REL_TOL = 1e-9

# What an operator has to be able to do to a running inter-spacecraft network.
REQUIRED_FUNCTIONS = frozenset(
    [
        "member-join-and-leave",
        "address-assignment",
        "route-maintenance",
        "link-state-monitoring",
        "configuration-control",
        "performance-reporting",
    ]
)


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_nonnegative(value, name="value"):
    """Return a non-negative float."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive float."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_count(value, name="count"):
    """Return a strictly positive whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def function_coverage(declared):
    """Compare the declared management functions against the required set.

    An unrecognised name is reported rather than ignored: it is usually a
    required function spelled differently, and silently dropping it turns a
    naming slip into a missing function nobody sees.
    """
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared functions must be a sequence or set")
    names = set()
    for item in declared:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each declared function must be a non-empty string")
        names.add(item.strip().lower())
    return {
        "present": sorted(names & REQUIRED_FUNCTIONS),
        "missing": sorted(REQUIRED_FUNCTIONS - names),
        "unrecognised": sorted(names - REQUIRED_FUNCTIONS),
        "complete": not (REQUIRED_FUNCTIONS - names),
    }


def management_overhead_bps(members, exchange_bits, poll_period_s):
    """Return the management traffic the service puts on the link."""
    count = validate_count(members, "members")
    bits = validate_nonnegative(exchange_bits, "exchange_bits")
    period = validate_positive(poll_period_s, "poll_period_s")
    return count * bits / period


def overhead_fraction(overhead_bps, capacity_bps):
    """Return the share of link capacity spent on managing the network."""
    overhead = validate_nonnegative(overhead_bps, "overhead_bps")
    capacity = validate_positive(capacity_bps, "capacity_bps")
    return overhead / capacity


def detection_time_s(poll_period_s, miss_threshold):
    """Return how long a silent member goes unnoticed."""
    period = validate_positive(poll_period_s, "poll_period_s")
    misses = validate_count(miss_threshold, "miss_threshold")
    return period * misses


def convergence_time_s(
    poll_period_s, miss_threshold, diameter_hops, hop_latency_s, reconfiguration_s
):
    """Return how long the network takes to settle after a topology change."""
    detect = detection_time_s(poll_period_s, miss_threshold)
    hops = validate_count(diameter_hops, "diameter_hops")
    latency = validate_nonnegative(hop_latency_s, "hop_latency_s")
    settle = validate_nonnegative(reconfiguration_s, "reconfiguration_s")
    return detect + hops * latency + settle


def max_poll_period_s(
    miss_threshold, diameter_hops, hop_latency_s, reconfiguration_s, required_s
):
    """Return the longest polling period that still converges in time.

    Zero means propagation and reconfiguration already spend the whole
    allowance, so polling faster cannot recover it.
    """
    misses = validate_count(miss_threshold, "miss_threshold")
    hops = validate_count(diameter_hops, "diameter_hops")
    latency = validate_nonnegative(hop_latency_s, "hop_latency_s")
    settle = validate_nonnegative(reconfiguration_s, "reconfiguration_s")
    required = validate_positive(required_s, "required_s")
    budget = required - (hops * latency + settle)
    if budget <= 0.0:
        return 0.0
    return budget / misses


def max_managed_members(exchange_bits, poll_period_s, capacity_bps, allowance):
    """Return the largest member count the overhead allowance holds."""
    bits = validate_positive(exchange_bits, "exchange_bits")
    period = validate_positive(poll_period_s, "poll_period_s")
    capacity = validate_positive(capacity_bps, "capacity_bps")
    share = validate_positive(allowance, "allowance")
    if share > 1.0:
        raise ValueError("allowance must be a fraction of capacity, got %r" % allowance)
    exact = share * capacity * period / bits
    return int(math.floor(exact + REL_TOL * max(1.0, exact)))


def assess_management_service(
    declared_functions,
    members,
    exchange_bits,
    poll_period_s,
    capacity_bps,
    overhead_allowance,
    miss_threshold,
    diameter_hops,
    hop_latency_s,
    reconfiguration_s,
    required_convergence_s,
):
    """Grade one declared inter-spacecraft network management service."""
    coverage = function_coverage(declared_functions)
    overhead = management_overhead_bps(members, exchange_bits, poll_period_s)
    fraction = overhead_fraction(overhead, capacity_bps)
    allowance = validate_positive(overhead_allowance, "overhead_allowance")
    if allowance > 1.0:
        raise ValueError("overhead_allowance must be a fraction of capacity")
    converge = convergence_time_s(
        poll_period_s, miss_threshold, diameter_hops, hop_latency_s, reconfiguration_s
    )
    required = validate_positive(required_convergence_s, "required_convergence_s")
    overhead_ok = fraction <= allowance + REL_TOL * allowance
    converge_ok = converge <= required + REL_TOL * required
    longest_period = max_poll_period_s(
        miss_threshold, diameter_hops, hop_latency_s, reconfiguration_s, required
    )
    largest_membership = max_managed_members(
        exchange_bits, poll_period_s, capacity_bps, allowance
    )
    findings = []
    if coverage["missing"]:
        findings.append(
            "management service declares no %s; the operator cannot act on the "
            "network without it" % ", ".join(coverage["missing"])
        )
    if coverage["unrecognised"]:
        findings.append(
            "unrecognised declared function: %s; confirm it is not a required "
            "function under another name" % ", ".join(coverage["unrecognised"])
        )
    if not overhead_ok:
        findings.append(
            "management traffic takes %.6g of capacity against a %.6g allowance; "
            "the allowance holds %d members at this polling period"
            % (fraction, allowance, largest_membership)
        )
    if not converge_ok:
        if longest_period == 0.0:
            findings.append(
                "propagation and reconfiguration alone take %.6g s of a %.6g s "
                "allowance; polling faster cannot recover it"
                % (diameter_hops * hop_latency_s + reconfiguration_s, required)
            )
        else:
            findings.append(
                "convergence takes %.6g s against a %.6g s allowance; a polling "
                "period of at most %.6g s meets it" % (converge, required, longest_period)
            )
    return {
        "coverage": coverage,
        "overhead_bps": overhead,
        "overhead_fraction": fraction,
        "overhead_allowance": allowance,
        "overhead_within_allowance": overhead_ok,
        "detection_time_s": detection_time_s(poll_period_s, miss_threshold),
        "convergence_time_s": converge,
        "required_convergence_s": required,
        "convergence_within_allowance": converge_ok,
        "max_poll_period_s": longest_period,
        "max_members": largest_membership,
        "verdict": COMPLETE
        if (coverage["complete"] and overhead_ok and converge_ok)
        else DEFICIENT,
        "findings": findings,
    }

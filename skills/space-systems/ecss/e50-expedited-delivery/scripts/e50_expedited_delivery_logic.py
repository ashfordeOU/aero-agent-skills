"""Expedited delivery on a space data transfer service.

Anchor: ECSS-E-ST-50C clause 5.6.14.3 -- expedited delivery of urgent data.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that urgent data reaches the far end ahead of the
traffic already queued for the link. That is a queueing property, so the
procedure models the queue rather than the rate:

  none            -- no expedited class: the urgent unit waits for the unit in
                     service and for every unit queued ahead of it;
  non-preemptive  -- the urgent unit jumps the queue but cannot interrupt the
                     unit already going out, so the residual of that unit is
                     the irreducible wait;
  preemptive      -- the unit in service is interrupted at a switch cost, and
                     is either resumed later or resent in full.

Alongside the latency, the cost of the priority: an expedited load that
consumes the service rate starves the normal queue however healthy the urgent
latency looks.

Stdlib only, offline, deterministic.
"""

import math

POLICY_NONE = "none"
POLICY_NON_PREEMPTIVE = "non-preemptive"
POLICY_PREEMPTIVE = "preemptive"
VALID_POLICIES = (POLICY_NONE, POLICY_NON_PREEMPTIVE, POLICY_PREEMPTIVE)

# Policies ordered from the one that delivers latest to the one that delivers
# earliest, so a remedy can name the least intrusive policy that works.
POLICY_ORDER = (POLICY_NONE, POLICY_NON_PREEMPTIVE, POLICY_PREEMPTIVE)

MEETS_DEADLINE = "meets-deadline"
MISSES_DEADLINE = "misses-deadline"

# Relative tolerance for the deadline and share comparisons, so a design landing
# exactly on its bound decides the same way on every platform.
REL_TOL = 1e-9

__all__ = [
    "POLICY_NONE",
    "POLICY_NON_PREEMPTIVE",
    "POLICY_PREEMPTIVE",
    "VALID_POLICIES",
    "POLICY_ORDER",
    "MEETS_DEADLINE",
    "MISSES_DEADLINE",
    "REL_TOL",
    "validate_policy",
    "validate_rate",
    "validate_bits",
    "validate_nonnegative_bits",
    "validate_count",
    "validate_time",
    "validate_positive_time",
    "queued_bits",
    "expedited_latency_s",
    "latency_by_policy",
    "required_service_rate_bps",
    "least_policy_meeting_deadline",
    "expedited_share",
    "assess_expedited_delivery",
]


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_policy(value, name="policy"):
    """Return a recognised expedited queuing policy."""
    if value not in VALID_POLICIES:
        raise ValueError("%s must be one of %s, got %r" % (name, list(VALID_POLICIES), value))
    return value


def validate_rate(value, name="service_rate_bps"):
    """Return a strictly positive service rate in bits per second."""
    rate = _number(value, name)
    if rate <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return rate


def validate_bits(value, name="unit_bits"):
    """Return a strictly positive size in bits."""
    size = _number(value, name)
    if size <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return size


def validate_nonnegative_bits(value, name="bits"):
    """Return a non-negative size in bits."""
    size = _number(value, name)
    if size < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return size


def validate_count(value, name="count", minimum=0):
    """Return an integer count at or above the minimum."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def validate_positive_time(value, name="time_s"):
    """Return a strictly positive time in seconds."""
    seconds = _number(value, name)
    if seconds <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return seconds


def validate_time(value, name="time_s"):
    """Return a non-negative time in seconds."""
    seconds = _number(value, name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return seconds


def queued_bits(queued_units, queued_unit_bits):
    """Return the bits waiting in the normal queue ahead of the urgent unit."""
    count = validate_count(queued_units, "queued_units")
    size = validate_bits(queued_unit_bits, "queued_unit_bits")
    return count * size


def expedited_latency_s(
    policy,
    service_rate_bps,
    urgent_unit_bits,
    queued_units,
    queued_unit_bits,
    in_service_remaining_bits,
    preemption_switch_s=0.0,
):
    """Return the seconds an urgent unit waits before it is fully delivered.

    With no expedited class the urgent unit is behind the unit in service and
    the whole queue. A non-preemptive class removes the queue but not the
    residual of the unit in service. A preemptive class removes the residual
    too and pays the switch cost instead.
    """
    name = validate_policy(policy)
    rate = validate_rate(service_rate_bps)
    urgent = validate_bits(urgent_unit_bits, "urgent_unit_bits")
    waiting = queued_bits(queued_units, queued_unit_bits)
    residual = validate_nonnegative_bits(in_service_remaining_bits, "in_service_remaining_bits")
    switch = validate_time(preemption_switch_s, "preemption_switch_s")
    if name == POLICY_NONE:
        ahead_bits = residual + waiting
        return (ahead_bits + urgent) / rate
    if name == POLICY_NON_PREEMPTIVE:
        return (residual + urgent) / rate
    return switch + (urgent / rate)


def latency_by_policy(
    service_rate_bps,
    urgent_unit_bits,
    queued_units,
    queued_unit_bits,
    in_service_remaining_bits,
    preemption_switch_s=0.0,
):
    """Return the urgent latency under each of the three policies."""
    return {
        name: expedited_latency_s(
            name,
            service_rate_bps,
            urgent_unit_bits,
            queued_units,
            queued_unit_bits,
            in_service_remaining_bits,
            preemption_switch_s,
        )
        for name in VALID_POLICIES
    }


def required_service_rate_bps(
    policy,
    deadline_s,
    urgent_unit_bits,
    queued_units,
    queued_unit_bits,
    in_service_remaining_bits,
    preemption_switch_s=0.0,
):
    """Return the service rate that meets the deadline under this policy.

    None means no rate does: a preemptive switch cost already past the deadline
    is not something a faster link recovers.
    """
    name = validate_policy(policy)
    deadline = validate_positive_time(deadline_s, "deadline_s")
    urgent = validate_bits(urgent_unit_bits, "urgent_unit_bits")
    waiting = queued_bits(queued_units, queued_unit_bits)
    residual = validate_nonnegative_bits(in_service_remaining_bits, "in_service_remaining_bits")
    switch = validate_time(preemption_switch_s, "preemption_switch_s")
    if name == POLICY_NONE:
        bits = residual + waiting + urgent
        budget = deadline
    elif name == POLICY_NON_PREEMPTIVE:
        bits = residual + urgent
        budget = deadline
    else:
        bits = urgent
        budget = deadline - switch
    if budget <= 0.0:
        return None
    return bits / budget


def least_policy_meeting_deadline(
    deadline_s,
    service_rate_bps,
    urgent_unit_bits,
    queued_units,
    queued_unit_bits,
    in_service_remaining_bits,
    preemption_switch_s=0.0,
):
    """Return the least intrusive policy that meets the deadline at this rate.

    None means no policy does, which points at the rate rather than the queue.
    """
    deadline = validate_positive_time(deadline_s, "deadline_s")
    latencies = latency_by_policy(
        service_rate_bps,
        urgent_unit_bits,
        queued_units,
        queued_unit_bits,
        in_service_remaining_bits,
        preemption_switch_s,
    )
    for name in POLICY_ORDER:
        if latencies[name] <= deadline + REL_TOL * deadline:
            return name
    return None


def expedited_share(expedited_load_bps, service_rate_bps):
    """Return the fraction of the link the expedited class consumes."""
    load = validate_nonnegative_bits(expedited_load_bps, "expedited_load_bps")
    rate = validate_rate(service_rate_bps)
    return load / rate


def assess_expedited_delivery(
    policy,
    service_rate_bps,
    urgent_unit_bits,
    queued_units,
    queued_unit_bits,
    in_service_remaining_bits,
    deadline_s,
    expedited_load_bps=0.0,
    normal_share_floor=0.1,
    preemption_switch_s=0.0,
):
    """Assess one expedited delivery design against the clause."""
    name = validate_policy(policy)
    rate = validate_rate(service_rate_bps)
    urgent = validate_bits(urgent_unit_bits, "urgent_unit_bits")
    count = validate_count(queued_units, "queued_units")
    queued_size = validate_bits(queued_unit_bits, "queued_unit_bits")
    residual = validate_nonnegative_bits(in_service_remaining_bits, "in_service_remaining_bits")
    deadline = validate_positive_time(deadline_s, "deadline_s")
    load = validate_nonnegative_bits(expedited_load_bps, "expedited_load_bps")
    floor = _number(normal_share_floor, "normal_share_floor")
    if not 0.0 <= floor < 1.0:
        raise ValueError("normal_share_floor must lie in [0, 1), got %r" % (normal_share_floor,))
    switch = validate_time(preemption_switch_s, "preemption_switch_s")

    latencies = latency_by_policy(rate, urgent, count, queued_size, residual, switch)
    latency = latencies[name]
    meets = latency <= deadline + REL_TOL * deadline
    needed_rate = required_service_rate_bps(
        name, deadline, urgent, count, queued_size, residual, switch
    )
    needed_policy = least_policy_meeting_deadline(
        deadline, rate, urgent, count, queued_size, residual, switch
    )
    share = expedited_share(load, rate)
    normal_share = 1.0 - share
    starves = normal_share < floor - REL_TOL * max(floor, 1.0)

    findings = []
    if not meets:
        if needed_policy is None and needed_rate is None:
            findings.append(
                "urgent latency %.6g s misses the %.6g s deadline and neither a policy "
                "change nor a faster link recovers it at this switch cost"
                % (latency, deadline)
            )
        else:
            policy_text = (
                "%s meets it at this rate" % needed_policy
                if needed_policy is not None
                else "no policy meets it at this rate"
            )
            rate_text = (
                "%.6g bit/s meets it under %s" % (needed_rate, name)
                if needed_rate is not None
                else "no rate meets it under %s" % name
            )
            findings.append(
                "urgent latency %.6g s misses the %.6g s deadline; %s, and %s"
                % (latency, deadline, policy_text, rate_text)
            )
    if name == POLICY_NONE:
        findings.append(
            "no expedited class is provided; urgent data waits behind the %d queued "
            "unit(s) like any other traffic" % count
        )
    if starves:
        findings.append(
            "the expedited class takes %.4g of the link, leaving the normal queue %.4g "
            "against a floor of %.4g; the normal queue grows without bound"
            % (share, normal_share, floor)
        )

    verdict = MEETS_DEADLINE if (meets and name != POLICY_NONE and not starves) else MISSES_DEADLINE
    return {
        "policy": name,
        "service_rate_bps": rate,
        "urgent_unit_bits": urgent,
        "queued_units": count,
        "queued_bits": queued_bits(count, queued_size),
        "in_service_remaining_bits": residual,
        "preemption_switch_s": switch,
        "latency_s": latency,
        "latency_by_policy": latencies,
        "deadline_s": deadline,
        "meets_deadline": meets,
        "required_service_rate_bps": needed_rate,
        "least_policy_meeting_deadline": needed_policy,
        "expedited_share": share,
        "normal_share": normal_share,
        "normal_share_floor": floor,
        "starves_normal_traffic": starves,
        "verdict": verdict,
        "findings": findings,
    }

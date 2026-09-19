"""Deterministic performance of a time-critical on-board network path.

Anchor: ECSS-E-ST-50C clause 5.7.1.2 -- deterministic performance of the
on-board communication network. Paraphrased into an implementable procedure;
no standard text is reproduced.

The single normative item asks for performance that is deterministic: a
time-critical exchange must have a latency that can be BOUNDED, not merely one
that is small when the network happens to be quiet. That turns into a
response-time model of one path:

  transmission -- the message itself, once per link it crosses;
  blocking     -- one lower-priority frame already on the wire when the
                  message becomes ready, which cannot be pre-empted;
  interference -- every higher-priority stream that can win arbitration while
                  the message waits, counted over the busy period it creates;
  switching    -- fixed store-and-forward cost at each intermediate node;
  access       -- the fixed medium-access overhead of the link.

The interference term is recursive, because a longer wait admits more
higher-priority arrivals. It is solved as a fixed point, and the fixed point
exists only while the path utilisation stays below one. Above that there is no
bound at all, and the honest answer is "unbounded", not a large number.
"""

import math

__all__ = [
    "DETERMINISTIC",
    "DEADLINE_MISS",
    "JITTER_EXCEEDED",
    "UNBOUNDED",
    "CEIL_TOL",
    "REL_TOL",
    "MAX_ITERATIONS",
    "validate_positive",
    "validate_nonnegative",
    "validate_hops",
    "validate_streams",
    "transmission_time_s",
    "path_utilisation",
    "best_case_latency_s",
    "link_response_time_s",
    "worst_case_latency_s",
    "jitter_s",
    "assess_deterministic_performance",
]

DETERMINISTIC = "deterministic"
DEADLINE_MISS = "deadline-miss"
JITTER_EXCEEDED = "jitter-exceeded"
UNBOUNDED = "unbounded"

# Snap a ceiling that lands on an integer, so an arrival pattern that divides
# the response time exactly is counted the same on every build host.
CEIL_TOL = 1e-9
# Relative tolerance for the deadline and jitter comparisons, so a path sized
# to exactly meet its deadline passes everywhere rather than on some machines.
REL_TOL = 1e-9
MAX_ITERATIONS = 200


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name):
    """Return a strictly positive float."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_nonnegative(value, name):
    """Return a float that is zero or above."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_hops(value, name="hops"):
    """Return the number of links the message crosses, at least one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer" % name)
    if value < 1:
        raise ValueError("%s must be at least one link, got %r" % (name, value))
    return value


def validate_streams(streams, name="interferers"):
    """Return higher-priority streams as a list of (bits, period_s) pairs."""
    if streams is None:
        return []
    if isinstance(streams, dict) or isinstance(streams, (str, bytes)):
        raise ValueError("%s must be a sequence of stream mappings" % name)
    checked = []
    for index, stream in enumerate(streams):
        if not isinstance(stream, dict):
            raise ValueError("%s[%d] must be a mapping" % (name, index))
        missing = {"bits", "period_s"} - set(stream)
        if missing:
            raise ValueError(
                "%s[%d] is missing %s" % (name, index, ", ".join(sorted(missing)))
            )
        bits = validate_positive(stream["bits"], "%s[%d].bits" % (name, index))
        period = validate_positive(
            stream["period_s"], "%s[%d].period_s" % (name, index)
        )
        checked.append((bits, period))
    return checked


def _snapped_ceil(value):
    """Ceiling that treats a near-integer as the integer it is trying to be."""
    if value <= 0.0:
        return 0
    nearest = math.floor(value + 0.5)
    if abs(value - nearest) <= CEIL_TOL * max(1.0, abs(value)):
        return int(nearest)
    return int(math.ceil(value))


def transmission_time_s(bits, rate_bps):
    """Return the seconds a frame of this size occupies one link."""
    size = validate_positive(bits, "bits")
    rate = validate_positive(rate_bps, "rate_bps")
    return size / rate


def path_utilisation(own_bits, own_period_s, rate_bps, interferers=None):
    """Return the fraction of one link consumed by the message and its betters."""
    own = transmission_time_s(own_bits, rate_bps)
    period = validate_positive(own_period_s, "own_period_s")
    rate = validate_positive(rate_bps, "rate_bps")
    load = own / period
    for bits, stream_period in validate_streams(interferers):
        load += (bits / rate) / stream_period
    return load


def best_case_latency_s(own_bits, rate_bps, hops, switch_latency_s=0.0,
                        access_latency_s=0.0):
    """Return the latency of an otherwise idle path: no blocking, no rivals."""
    own = transmission_time_s(own_bits, rate_bps)
    links = validate_hops(hops)
    switching = validate_nonnegative(switch_latency_s, "switch_latency_s")
    access = validate_nonnegative(access_latency_s, "access_latency_s")
    return links * (own + access) + (links - 1) * switching


def link_response_time_s(own_bits, own_period_s, rate_bps, blocking_bits=0.0,
                         interferers=None):
    """Return the worst-case time the message needs to clear ONE link.

    None means the fixed point does not exist: the link is loaded at or above
    its capacity, so the queue grows without limit and no bound can be quoted.
    """
    own = transmission_time_s(own_bits, rate_bps)
    rate = validate_positive(rate_bps, "rate_bps")
    period = validate_positive(own_period_s, "own_period_s")
    blocking_size = validate_nonnegative(blocking_bits, "blocking_bits")
    streams = validate_streams(interferers)
    blocking = blocking_size / rate
    load = own / period
    for bits, stream_period in streams:
        load += (bits / rate) / stream_period
    if load >= 1.0 - REL_TOL:
        return None
    response = own + blocking
    for _ in range(MAX_ITERATIONS):
        interference = 0.0
        for bits, stream_period in streams:
            interference += _snapped_ceil(response / stream_period) * (bits / rate)
        candidate = own + blocking + interference
        if abs(candidate - response) <= REL_TOL * max(1.0, response):
            return candidate
        response = candidate
    return None


def worst_case_latency_s(own_bits, own_period_s, rate_bps, hops,
                         blocking_bits=0.0, interferers=None,
                         switch_latency_s=0.0, access_latency_s=0.0):
    """Return the bounded end-to-end latency, or None when no bound exists."""
    links = validate_hops(hops)
    switching = validate_nonnegative(switch_latency_s, "switch_latency_s")
    access = validate_nonnegative(access_latency_s, "access_latency_s")
    per_link = link_response_time_s(
        own_bits, own_period_s, rate_bps, blocking_bits, interferers
    )
    if per_link is None:
        return None
    return links * (per_link + access) + (links - 1) * switching


def jitter_s(worst_s, best_s):
    """Return the spread between the bound and the idle-path latency."""
    if worst_s is None:
        return None
    worst = validate_nonnegative(worst_s, "worst_s")
    best = validate_nonnegative(best_s, "best_s")
    if best > worst + REL_TOL * max(1.0, worst):
        raise ValueError("best_s must not exceed worst_s")
    return max(worst - best, 0.0)


def assess_deterministic_performance(own_bits, own_period_s, rate_bps, hops,
                                     deadline_s, blocking_bits=0.0,
                                     interferers=None, switch_latency_s=0.0,
                                     access_latency_s=0.0,
                                     jitter_budget_s=None):
    """Decide whether one time-critical path performs deterministically."""
    deadline = validate_positive(deadline_s, "deadline_s")
    best = best_case_latency_s(
        own_bits, rate_bps, hops, switch_latency_s, access_latency_s
    )
    worst = worst_case_latency_s(
        own_bits, own_period_s, rate_bps, hops, blocking_bits, interferers,
        switch_latency_s, access_latency_s,
    )
    load = path_utilisation(own_bits, own_period_s, rate_bps, interferers)
    findings = []
    spread = jitter_s(worst, best) if worst is not None else None
    budget = None
    if jitter_budget_s is not None:
        budget = validate_nonnegative(jitter_budget_s, "jitter_budget_s")
    if worst is None:
        verdict = UNBOUNDED
        findings.append(
            "link load is %.6g of capacity, so the queue has no fixed point and "
            "the latency cannot be bounded at all" % load
        )
        margin = None
    else:
        margin = deadline - worst
        tolerance = REL_TOL * max(1.0, deadline)
        meets_deadline = worst <= deadline + tolerance
        within_jitter = True
        if budget is not None:
            within_jitter = spread <= budget + REL_TOL * max(1.0, budget)
        if not meets_deadline:
            verdict = DEADLINE_MISS
            findings.append(
                "bounded latency %.6g s exceeds the %.6g s deadline by %.6g s"
                % (worst, deadline, worst - deadline)
            )
        elif not within_jitter:
            verdict = JITTER_EXCEEDED
            findings.append(
                "latency is bounded and meets the deadline, but the %.6g s "
                "spread exceeds the %.6g s jitter budget" % (spread, budget)
            )
        else:
            verdict = DETERMINISTIC
    if worst is not None and interferers in (None, []) and blocking_bits == 0.0:
        findings.append(
            "no higher-priority stream and no blocking frame were declared, so "
            "this bound is an idle-path figure, not a worst case"
        )
    return {
        "best_case_latency_s": best,
        "worst_case_latency_s": worst,
        "jitter_s": spread,
        "jitter_budget_s": budget,
        "deadline_s": deadline,
        "margin_s": margin,
        "link_utilisation": load,
        "bounded": worst is not None,
        "verdict": verdict,
        "findings": findings,
    }

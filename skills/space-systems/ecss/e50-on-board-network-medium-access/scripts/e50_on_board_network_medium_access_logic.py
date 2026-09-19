"""Medium access on a spacecraft on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.1.5 -- medium access on the on-board
communication network. Paraphrased into an implementable procedure; no
standard text is reproduced.

The single normative item is about how a node is granted the shared medium.
The design has to say which arbitration governs the medium and, having said
it, has to be able to state the longest a node can be kept off it. Some
arbitration schemes give that bound by construction and some cannot give it at
all, which is the distinction this module exists to make:

  time-slotted  -- a fixed round of slots; a node waits at most the rest of
                   the round, and collisions are impossible by construction;
  token         -- the right to send circulates; a node waits at most one
                   rotation less its own holding time;
  fixed-priority-- bitwise arbitration resolves contention without a
                   collision, but a node waits for one non-pre-emptable frame
                   already on the wire plus every higher-priority frame that
                   arrives while it waits, which is a recursion;
  contention    -- collisions are detected and retried after a random backoff,
                   so there is no bound at all and the honest answer is that
                   the medium has no access guarantee.

Every scheme also fails once the medium is loaded at or beyond capacity, and
the bound is then meaningless whatever the arbitration.
"""

import math

__all__ = [
    "BOUNDED",
    "UNBOUNDED",
    "OVERSUBSCRIBED",
    "BUDGET_EXCEEDED",
    "SCHEMES",
    "TIME_SLOTTED",
    "TOKEN",
    "FIXED_PRIORITY",
    "CONTENTION",
    "REL_TOL",
    "MAX_ITERATIONS",
    "validate_positive",
    "validate_nonnegative",
    "validate_scheme",
    "validate_nodes",
    "frame_time_s",
    "medium_utilisation",
    "tdma_slot_time_s",
    "tdma_access_delay_s",
    "token_rotation_time_s",
    "token_access_delay_s",
    "fixed_priority_access_delay_s",
    "assess_medium_access",
]

BOUNDED = "bounded"
UNBOUNDED = "unbounded"
OVERSUBSCRIBED = "oversubscribed"
BUDGET_EXCEEDED = "budget-exceeded"

TIME_SLOTTED = "time-slotted"
TOKEN = "token"
FIXED_PRIORITY = "fixed-priority"
CONTENTION = "contention"
SCHEMES = (TIME_SLOTTED, TOKEN, FIXED_PRIORITY, CONTENTION)

# Relative tolerance for the load and budget comparisons, and for snapping an
# arbitration count that lands on a whole number.
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


def validate_scheme(scheme, name="scheme"):
    """Return a known arbitration scheme, refusing an undeclared one.

    An unrecognised scheme is refused rather than defaulted, because the whole
    point of the clause is that the medium access method is stated.
    """
    if not isinstance(scheme, str):
        raise ValueError("%s must be a string" % name)
    key = scheme.strip().lower()
    if key not in SCHEMES:
        raise ValueError(
            "%s %r is not one of %s" % (name, scheme, ", ".join(SCHEMES))
        )
    return key


def validate_nodes(nodes, name="nodes"):
    """Return the contending nodes as (name, frame_bits, period_s) triples.

    Order is priority order for fixed-priority arbitration: highest first.
    """
    if nodes is None or isinstance(nodes, (dict, str, bytes)):
        raise ValueError("%s must be a sequence of node mappings" % name)
    checked = []
    seen = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError("%s[%d] must be a mapping" % (name, index))
        missing = {"name", "frame_bits", "period_s"} - set(node)
        if missing:
            raise ValueError(
                "%s[%d] is missing %s" % (name, index, ", ".join(sorted(missing)))
            )
        label = node["name"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("%s[%d].name must be a non-empty string" % (name, index))
        if label in seen:
            raise ValueError("%s has two nodes named %r" % (name, label))
        seen.add(label)
        bits = validate_positive(node["frame_bits"], "%s[%d].frame_bits" % (name, index))
        period = validate_positive(node["period_s"], "%s[%d].period_s" % (name, index))
        checked.append((label, bits, period))
    if not checked:
        raise ValueError("%s must contain at least one node" % name)
    return checked


def _snapped_ceil(value):
    if value <= 0.0:
        return 0
    nearest = math.floor(value + 0.5)
    if abs(value - nearest) <= REL_TOL * max(1.0, abs(value)):
        return int(nearest)
    return int(math.ceil(value))


def frame_time_s(frame_bits, rate_bps, overhead_bits=0.0, guard_s=0.0):
    """Return the time one frame holds the medium, framing and guard included."""
    bits = validate_positive(frame_bits, "frame_bits")
    rate = validate_positive(rate_bps, "rate_bps")
    overhead = validate_nonnegative(overhead_bits, "overhead_bits")
    guard = validate_nonnegative(guard_s, "guard_s")
    return (bits + overhead) / rate + guard


def medium_utilisation(nodes, rate_bps, overhead_bits=0.0, guard_s=0.0):
    """Return the fraction of the medium the offered traffic consumes."""
    checked = validate_nodes(nodes)
    load = 0.0
    for _, bits, period in checked:
        load += frame_time_s(bits, rate_bps, overhead_bits, guard_s) / period
    return load


def tdma_slot_time_s(nodes, rate_bps, overhead_bits=0.0, guard_s=0.0):
    """Return the uniform slot a round has to give every node.

    A round is sized on the longest frame, because a slot too short for one
    node is a slot that node cannot use.
    """
    checked = validate_nodes(nodes)
    return max(
        frame_time_s(bits, rate_bps, overhead_bits, guard_s)
        for _, bits, _ in checked
    )


def tdma_access_delay_s(node_count, slot_s):
    """Return the longest a node waits for its slot in a fixed round."""
    if isinstance(node_count, bool) or not isinstance(node_count, int):
        raise ValueError("node_count must be an integer")
    if node_count < 1:
        raise ValueError("node_count must be at least one, got %r" % node_count)
    slot = validate_positive(slot_s, "slot_s")
    return (node_count - 1) * slot


def token_rotation_time_s(nodes, rate_bps, token_pass_s=0.0, overhead_bits=0.0,
                          guard_s=0.0):
    """Return one full circulation of the right to send."""
    checked = validate_nodes(nodes)
    token_pass = validate_nonnegative(token_pass_s, "token_pass_s")
    total = 0.0
    for _, bits, _ in checked:
        total += frame_time_s(bits, rate_bps, overhead_bits, guard_s)
    return total + len(checked) * token_pass


def token_access_delay_s(node_name, nodes, rate_bps, token_pass_s=0.0,
                         overhead_bits=0.0, guard_s=0.0):
    """Return the longest a named node waits for the token to come round."""
    checked = validate_nodes(nodes)
    rotation = token_rotation_time_s(
        nodes, rate_bps, token_pass_s, overhead_bits, guard_s
    )
    for label, bits, _ in checked:
        if label == node_name:
            return rotation - frame_time_s(bits, rate_bps, overhead_bits, guard_s)
    raise ValueError("no node named %r" % node_name)


def fixed_priority_access_delay_s(node_name, nodes, rate_bps, blocking_bits=0.0,
                                  overhead_bits=0.0, guard_s=0.0):
    """Return the longest a node loses arbitration before it starts sending.

    None means the fixed point does not exist: the higher-priority traffic
    alone saturates the medium, so a lower-priority node can be kept off it
    indefinitely and no bound can be quoted.
    """
    checked = validate_nodes(nodes)
    rate = validate_positive(rate_bps, "rate_bps")
    blocking_size = validate_nonnegative(blocking_bits, "blocking_bits")
    labels = [label for label, _, _ in checked]
    if node_name not in labels:
        raise ValueError("no node named %r" % node_name)
    position = labels.index(node_name)
    higher = checked[:position]
    blocking = blocking_size / rate
    load = 0.0
    for _, bits, period in higher:
        load += frame_time_s(bits, rate, overhead_bits, guard_s) / period
    if load >= 1.0 - REL_TOL:
        return None
    wait = blocking
    for _ in range(MAX_ITERATIONS):
        interference = 0.0
        for _, bits, period in higher:
            interference += _snapped_ceil(wait / period) * frame_time_s(
                bits, rate, overhead_bits, guard_s
            )
        candidate = blocking + interference
        if abs(candidate - wait) <= REL_TOL * max(1.0, wait):
            return candidate
        wait = candidate
    return None


def assess_medium_access(scheme, nodes, rate_bps, token_pass_s=0.0,
                         blocking_bits=0.0, overhead_bits=0.0, guard_s=0.0,
                         access_delay_budget_s=None):
    """Say what the medium guarantees each node, and whether it guarantees anything."""
    key = validate_scheme(scheme)
    checked = validate_nodes(nodes)
    rate = validate_positive(rate_bps, "rate_bps")
    load = medium_utilisation(nodes, rate, overhead_bits, guard_s)
    budget = None
    if access_delay_budget_s is not None:
        budget = validate_nonnegative(access_delay_budget_s, "access_delay_budget_s")
    slot = None
    rotation = None
    delays = {}
    if key == TIME_SLOTTED:
        slot = tdma_slot_time_s(nodes, rate, overhead_bits, guard_s)
        shared = tdma_access_delay_s(len(checked), slot)
        for label, _, _ in checked:
            delays[label] = shared
    elif key == TOKEN:
        rotation = token_rotation_time_s(
            nodes, rate, token_pass_s, overhead_bits, guard_s
        )
        for label, _, _ in checked:
            delays[label] = token_access_delay_s(
                label, nodes, rate, token_pass_s, overhead_bits, guard_s
            )
    elif key == FIXED_PRIORITY:
        for label, _, _ in checked:
            delays[label] = fixed_priority_access_delay_s(
                label, nodes, rate, blocking_bits, overhead_bits, guard_s
            )
    else:
        for label, _, _ in checked:
            delays[label] = None
    bounded = all(value is not None for value in delays.values())
    worst_name = None
    worst_delay = None
    if bounded:
        worst_name, worst_delay = max(delays.items(), key=lambda item: item[1])
    findings = []
    if key == CONTENTION:
        verdict = UNBOUNDED
        findings.append(
            "contention with random backoff gives no access bound at all, so "
            "this medium cannot carry traffic with an access requirement"
        )
    elif not bounded:
        verdict = UNBOUNDED
        starved = sorted(k for k, v in delays.items() if v is None)
        findings.append(
            "higher-priority traffic alone saturates the medium, so %s can be "
            "kept off it indefinitely" % ", ".join(starved)
        )
    elif load >= 1.0 - REL_TOL:
        verdict = OVERSUBSCRIBED
        findings.append(
            "offered traffic is %.6g of the medium, so the arbitration has "
            "nothing left to schedule and no bound survives" % load
        )
    elif budget is not None and worst_delay > budget + REL_TOL * max(1.0, budget):
        verdict = BUDGET_EXCEEDED
        findings.append(
            "worst access delay %.6g s at %s exceeds the %.6g s budget"
            % (worst_delay, worst_name, budget)
        )
    else:
        verdict = BOUNDED
    if key == FIXED_PRIORITY and blocking_bits == 0.0:
        findings.append(
            "no blocking frame was declared, so the lowest-priority bound "
            "omits the non-pre-emptable frame already on the wire"
        )
    return {
        "scheme": key,
        "node_count": len(checked),
        "medium_utilisation": load,
        "slot_time_s": slot,
        "token_rotation_s": rotation,
        "access_delay_s": delays,
        "bounded": bounded,
        "worst_node": worst_name,
        "worst_access_delay_s": worst_delay,
        "access_delay_budget_s": budget,
        "verdict": verdict,
        "findings": findings,
    }

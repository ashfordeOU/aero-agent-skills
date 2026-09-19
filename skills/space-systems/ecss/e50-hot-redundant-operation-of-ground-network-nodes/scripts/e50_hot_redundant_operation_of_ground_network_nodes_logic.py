"""Hot redundant operation of ground network nodes.

Anchor: ECSS-E-ST-50C clause 5.8.5 -- hot redundant operation of the nodes of
the ground network. Paraphrased into an implementable procedure; no standard
text is reproduced.

The single normative item is that redundant nodes run hot. The word that
carries the obligation is "hot": the spare is already powered, already
configured and already carrying the state it needs, so a failure costs the
detection and switch time and nothing else. A spare that has to be started,
loaded or synchronised is a standby node wearing the wrong label, and the
difference shows up as a service gap nobody budgeted for.

Three numbers decide whether a design earns the word:

  redundancy  -- the probability that at least k of n nodes are up, which is
                 the binomial tail and not the availability of one node;
  gap         -- detection plus switchover plus, for a node that is not
                 actually hot, the start-up and state-recovery time it needs
                 before it can serve;
  downtime    -- that gap multiplied by how often it happens, expressed as the
                 unavailability the gap alone contributes over a period.

The two inverses a designer asks for are the number of hot nodes that reaches
an availability target, and the largest gap a target can tolerate at a given
failure rate.
"""

import math

__all__ = [
    "HOT_COMPLIANT",
    "GAP_EXCEEDED",
    "NOT_HOT",
    "INSUFFICIENT_REDUNDANCY",
    "REL_TOL",
    "ABS_TOL_S",
    "validate_availability",
    "validate_non_negative",
    "validate_positive",
    "validate_node_count",
    "k_of_n_availability",
    "service_gap_s",
    "is_hot_transition",
    "gap_unavailability",
    "combined_availability",
    "outage_seconds_per_period",
    "minimum_hot_nodes",
    "maximum_tolerable_gap_s",
    "assess_hot_redundancy",
]

HOT_COMPLIANT = "hot-compliant"
GAP_EXCEEDED = "gap-exceeded"
NOT_HOT = "not-hot"
INSUFFICIENT_REDUNDANCY = "insufficient-redundancy"

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

REL_TOL = 1e-9
ABS_TOL_S = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_availability(value, name="availability"):
    """Return an availability in the closed interval zero to one."""
    a = _validate_number(value, name)
    if a < 0.0 or a > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return a


def validate_non_negative(value, name="value"):
    """Return a value of zero or more."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive value."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_node_count(value, name="nodes"):
    """Return a node count of one or more."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def k_of_n_availability(node_availability, nodes, required):
    """Return the probability that at least `required` of `nodes` are up."""
    a = validate_availability(node_availability, "node_availability")
    n = validate_node_count(nodes, "nodes")
    k = validate_node_count(required, "required")
    if k > n:
        raise ValueError("required (%d) cannot exceed nodes (%d)" % (k, n))
    total = 0.0
    for up in range(k, n + 1):
        total += math.comb(n, up) * (a ** up) * ((1.0 - a) ** (n - up))
    if total > 1.0:
        return 1.0
    return total


def service_gap_s(detection_s, switchover_s, startup_s=0.0, state_recovery_s=0.0):
    """Return the seconds of service lost when one node fails over.

    A genuinely hot node contributes nothing from start-up or state recovery,
    because it is already running and already holds the state. Passing a
    non-zero value for either is the honest way to describe a node that is
    called hot but is not.
    """
    detection = validate_non_negative(detection_s, "detection_s")
    switchover = validate_non_negative(switchover_s, "switchover_s")
    startup = validate_non_negative(startup_s, "startup_s")
    recovery = validate_non_negative(state_recovery_s, "state_recovery_s")
    return detection + switchover + startup + recovery


def is_hot_transition(startup_s, state_recovery_s):
    """Return whether the spare was already running and already in state."""
    startup = validate_non_negative(startup_s, "startup_s")
    recovery = validate_non_negative(state_recovery_s, "state_recovery_s")
    return startup <= ABS_TOL_S and recovery <= ABS_TOL_S


def gap_unavailability(gap_s, failures_per_period, period_s):
    """Return the unavailability the switchover gap alone contributes."""
    gap = validate_non_negative(gap_s, "gap_s")
    failures = validate_non_negative(failures_per_period, "failures_per_period")
    period = validate_positive(period_s, "period_s")
    lost = gap * failures
    if lost >= period:
        return 1.0
    return lost / period


def combined_availability(redundancy_availability, gap_unavailability_value):
    """Return the availability left once the switchover gap is charged."""
    a = validate_availability(redundancy_availability, "redundancy_availability")
    u = validate_availability(gap_unavailability_value, "gap_unavailability_value")
    return a * (1.0 - u)


def outage_seconds_per_period(availability, period_s=SECONDS_PER_YEAR):
    """Return the seconds of outage an availability implies over a period."""
    a = validate_availability(availability, "availability")
    period = validate_positive(period_s, "period_s")
    return (1.0 - a) * period


def minimum_hot_nodes(
    node_availability,
    required,
    target_availability,
    gap_unavailability_value=0.0,
    ceiling=64,
):
    """Return the smallest node count that reaches the target, or None.

    The switchover gap is charged against every candidate count, because a
    recommendation that only makes the redundancy term reach the target is a
    recommendation the built system will miss. None means no count inside the
    ceiling reaches it, which happens whenever the target asks for more than
    adding identical nodes behind this gap can ever deliver.
    """
    a = validate_availability(node_availability, "node_availability")
    k = validate_node_count(required, "required")
    target = validate_availability(target_availability, "target_availability")
    gap_u = validate_availability(
        gap_unavailability_value, "gap_unavailability_value"
    )
    limit = validate_node_count(ceiling, "ceiling")
    if k > limit:
        raise ValueError("required (%d) cannot exceed ceiling (%d)" % (k, limit))
    tolerance = REL_TOL * max(target, 1e-300)
    for n in range(k, limit + 1):
        reachable = combined_availability(k_of_n_availability(a, n, k), gap_u)
        if reachable >= target - tolerance:
            return n
    return None


def maximum_tolerable_gap_s(
    target_availability, redundancy_availability, failures_per_period, period_s
):
    """Return the longest switchover gap the target still tolerates.

    None means the redundancy on its own already misses the target, so no gap
    however short rescues it; zero means only an instantaneous switch does.
    """
    target = validate_availability(target_availability, "target_availability")
    redundancy = validate_availability(
        redundancy_availability, "redundancy_availability"
    )
    failures = validate_positive(failures_per_period, "failures_per_period")
    period = validate_positive(period_s, "period_s")
    tolerance = REL_TOL * max(target, 1e-300)
    if redundancy < target - tolerance:
        return None
    if redundancy == 0.0:
        return None
    allowed_gap_unavailability = 1.0 - (target / redundancy)
    if allowed_gap_unavailability <= 0.0:
        return 0.0
    return allowed_gap_unavailability * period / failures


def assess_hot_redundancy(
    node_availability,
    nodes,
    required,
    detection_s,
    switchover_s,
    startup_s=0.0,
    state_recovery_s=0.0,
    max_gap_s=0.0,
    target_availability=0.0,
    failures_per_period=1.0,
    period_s=SECONDS_PER_YEAR,
):
    """Grade a redundant ground network node set against clause 5.8.5."""
    a = validate_availability(node_availability, "node_availability")
    n = validate_node_count(nodes, "nodes")
    k = validate_node_count(required, "required")
    allowed_gap = validate_non_negative(max_gap_s, "max_gap_s")
    target = validate_availability(target_availability, "target_availability")
    redundancy = k_of_n_availability(a, n, k)
    hot = is_hot_transition(startup_s, state_recovery_s)
    gap = service_gap_s(detection_s, switchover_s, startup_s, state_recovery_s)
    gap_u = gap_unavailability(gap, failures_per_period, period_s)
    achieved = combined_availability(redundancy, gap_u)
    gap_tolerance = ABS_TOL_S + REL_TOL * allowed_gap
    target_tolerance = REL_TOL * max(target, 1e-300)
    findings = []
    if not hot:
        findings.append(
            "spare needs %.6g s of start-up and %.6g s of state recovery before "
            "it can serve, so it is a standby node and not a hot one"
            % (float(startup_s), float(state_recovery_s))
        )
    if gap > allowed_gap + gap_tolerance:
        findings.append(
            "switchover costs %.6g s of service against an allowance of %.6g s"
            % (gap, allowed_gap)
        )
    if n <= k:
        findings.append(
            "%d node(s) with %d required leaves no spare, so a single failure "
            "takes the service down" % (n, k)
        )
    if achieved < target - target_tolerance:
        spare = minimum_hot_nodes(a, k, target, gap_u)
        if spare is None:
            findings.append(
                "no reachable node count meets an availability of %.9g behind a "
                "gap that already costs %.9g; the node or the gap has to improve"
                % (target, gap_u)
            )
        else:
            findings.append(
                "achieved availability %.9g misses the target %.9g; %d hot "
                "node(s) would carry the redundancy term" % (achieved, target, spare)
            )
    if not hot:
        verdict = NOT_HOT
    elif n <= k:
        verdict = INSUFFICIENT_REDUNDANCY
    elif gap > allowed_gap + gap_tolerance:
        verdict = GAP_EXCEEDED
    elif achieved < target - target_tolerance:
        verdict = INSUFFICIENT_REDUNDANCY
    else:
        verdict = HOT_COMPLIANT
    return {
        "nodes": n,
        "required_nodes": k,
        "node_availability": a,
        "redundancy_availability": redundancy,
        "hot": hot,
        "service_gap_s": gap,
        "max_gap_s": allowed_gap,
        "gap_unavailability": gap_u,
        "achieved_availability": achieved,
        "target_availability": target,
        "outage_seconds_per_period": outage_seconds_per_period(achieved, period_s),
        "minimum_hot_nodes": minimum_hot_nodes(a, k, target, gap_u)
        if target > 0.0
        else k,
        "maximum_tolerable_gap_s": maximum_tolerable_gap_s(
            target, redundancy, failures_per_period, period_s
        )
        if target > 0.0
        else None,
        "verdict": verdict,
        "findings": findings,
    }

"""Redundancy management for an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.5 -- on-board network redundancy
management. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that the network manages its redundancy: a
failure in the path in use is survived by moving the traffic to a redundant
path. Two things decide whether that happens, and they are usually reviewed by
different people.

Topology decides whether there is anywhere to go. An element carried by both
the nominal and the redundant path is a single point of failure: when it
fails, both paths fail with it, and no amount of switching logic helps. Some
shared elements are accepted deliberately -- a passive backplane, a structural
harness -- but only when the design says so by name.

Timing decides whether the move happens soon enough. The outage runs from the
failure to the moment traffic flows again, and it is the sum of detecting the
failure, deciding to switch, and reconfiguring. That sum is compared against
the longest outage the mission tolerates, and it inverts into the detection
budget a design has left once decision and reconfiguration are fixed.
"""

import math

__all__ = [
    "EFFECTIVE",
    "SINGLE_POINT_OF_FAILURE",
    "TOO_SLOW",
    "REL_TOL",
    "validate_time",
    "validate_path",
    "shared_elements",
    "single_points_of_failure",
    "switchover_time",
    "detection_budget",
    "assess_redundancy_management",
]

EFFECTIVE = "effective"
SINGLE_POINT_OF_FAILURE = "single-point-of-failure"
TOO_SLOW = "too-slow"

# Relative tolerance for the outage comparison, so a switchover budget that
# lands exactly on the tolerated outage passes on every platform rather than on
# whichever one rounded in its favour.
REL_TOL = 1e-9


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_time(value, name="time_s", allow_zero=True):
    """Return a non-negative duration in seconds."""
    seconds = _number(value, name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if not allow_zero and seconds == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return seconds


def validate_path(value, name="path"):
    """Return an ordered tuple of distinct element names along one path."""
    if isinstance(value, str):
        raise ValueError("%s must be a list of element names, not a single string" % name)
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of element names" % name)
    if not value:
        raise ValueError("%s must name at least one element" % name)
    out = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s[%d] must be a non-empty string, got %r" % (name, index, item))
        element = item.strip()
        if element in out:
            raise ValueError("%s repeats element %r" % (name, element))
        out.append(element)
    return tuple(out)


def shared_elements(nominal_path, redundant_path):
    """Return the elements both paths depend on, in nominal-path order."""
    nominal = validate_path(nominal_path, "nominal_path")
    redundant = set(validate_path(redundant_path, "redundant_path"))
    return tuple(element for element in nominal if element in redundant)


def single_points_of_failure(nominal_path, redundant_path, tolerated=()):
    """Return the shared elements the design has not accepted by name.

    A tolerated element that is not actually shared is an input error: the
    design is claiming to accept a risk it does not carry, which usually means
    a path was renamed and the acceptance was never revisited.
    """
    shared = shared_elements(nominal_path, redundant_path)
    if isinstance(tolerated, str):
        raise ValueError("tolerated must be a list of element names, not a single string")
    if not isinstance(tolerated, (list, tuple, set, frozenset)):
        raise ValueError("tolerated must be a collection of element names")
    accepted = set()
    for item in tolerated:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("tolerated element must be a non-empty string, got %r" % (item,))
        name = item.strip()
        if name not in shared:
            raise ValueError(
                "tolerated element %r is not shared by the two paths" % name
            )
        accepted.add(name)
    return tuple(element for element in shared if element not in accepted)


def switchover_time(detection_s, decision_s, reconfiguration_s):
    """Return the outage a switchover costs, in seconds."""
    return (
        validate_time(detection_s, "detection_s")
        + validate_time(decision_s, "decision_s")
        + validate_time(reconfiguration_s, "reconfiguration_s")
    )


def detection_budget(decision_s, reconfiguration_s, max_outage_s):
    """Return the detection time left once decision and reconfiguration are fixed.

    None means there is none: decision and reconfiguration alone already run
    past the tolerated outage, so faster detection cannot save the design.
    """
    decision = validate_time(decision_s, "decision_s")
    reconfiguration = validate_time(reconfiguration_s, "reconfiguration_s")
    outage = validate_time(max_outage_s, "max_outage_s", allow_zero=False)
    left = outage - decision - reconfiguration
    if left < 0.0:
        return None
    return left


def assess_redundancy_management(
    nominal_path,
    redundant_path,
    detection_s,
    decision_s,
    reconfiguration_s,
    max_outage_s,
    tolerated_shared=(),
):
    """Judge one redundant on-board network arrangement against the clause."""
    nominal = validate_path(nominal_path, "nominal_path")
    redundant = validate_path(redundant_path, "redundant_path")
    shared = shared_elements(nominal, redundant)
    spofs = single_points_of_failure(nominal, redundant, tolerated_shared)
    outage = switchover_time(detection_s, decision_s, reconfiguration_s)
    tolerated = validate_time(max_outage_s, "max_outage_s", allow_zero=False)
    tolerance = REL_TOL * max(outage, tolerated, 1.0)
    fast_enough = outage <= tolerated + tolerance
    identical = set(nominal) == set(redundant)
    findings = []
    if spofs:
        findings.append(
            "both paths depend on %s, so a failure there is not survived by "
            "switching" % ", ".join(spofs)
        )
    if identical:
        findings.append(
            "the redundant path uses the same elements as the nominal path, so "
            "it is a second name rather than a second path"
        )
    if not fast_enough:
        budget = detection_budget(decision_s, reconfiguration_s, tolerated)
        if budget is None:
            findings.append(
                "decision and reconfiguration alone run past the %.6g s tolerated "
                "outage, so faster detection cannot meet it" % tolerated
            )
        else:
            findings.append(
                "switchover takes %.6g s against a %.6g s tolerated outage; "
                "detection must come down to %.6g s" % (outage, tolerated, budget)
            )
    if spofs:
        verdict = SINGLE_POINT_OF_FAILURE
    elif not fast_enough:
        verdict = TOO_SLOW
    else:
        verdict = EFFECTIVE
    return {
        "nominal_path": list(nominal),
        "redundant_path": list(redundant),
        "shared_elements": list(shared),
        "tolerated_shared": sorted(set(shared) - set(spofs)),
        "single_points_of_failure": list(spofs),
        "paths_identical": identical,
        "switchover_time_s": outage,
        "max_outage_s": tolerated,
        "outage_margin_s": tolerated - outage,
        "detection_budget_s": detection_budget(decision_s, reconfiguration_s, tolerated),
        "fast_enough": fast_enough,
        "single_failure_survivable": not spofs,
        "verdict": verdict,
        "findings": findings,
    }

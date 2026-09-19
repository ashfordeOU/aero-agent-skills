"""Hot redundant operation of nodes on a spacecraft on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.1.6 -- hot redundant operation of space
network nodes. Paraphrased into an implementable procedure; no standard text
is reproduced.

Two normative items sit at this clause, and they pull in opposite directions:

  item 1 -- the network supports HOT redundant operation. Both units of a
            redundant pair are powered and attached to the network at the same
            time, so a takeover costs a switchover and not a power-up. A unit
            that is off, or off the network, is a cold or warm spare whatever
            the drawing calls it.

  item 2 -- having both units on the network must not itself harm the network,
            and the takeover must be quick enough to be worth having. That
            means exactly one transmitter is enabled at a time, the two units
            can be told apart well enough to poll the standby's health, the
            pair does not hang off one segment whose loss takes both, and
            detection plus switchover plus re-initialisation fits the outage
            the system allows.

Item 1 met without item 2 is the dangerous case: a second powered transmitter
on a shared medium is a new failure mode, not redundancy.
"""

import math

__all__ = [
    "HOT_REDUNDANT",
    "NOT_HOT_REDUNDANT",
    "NETWORK_CONFLICT",
    "SINGLE_POINT_OF_FAILURE",
    "OUTAGE_EXCEEDED",
    "REL_TOL",
    "UNIT_FIELDS",
    "validate_nonnegative",
    "validate_unit",
    "is_hot_redundant",
    "network_conflicts",
    "single_point_segment",
    "failover_outage_s",
    "required_detection_s",
    "assess_hot_redundancy",
]

HOT_REDUNDANT = "hot-redundant"
NOT_HOT_REDUNDANT = "not-hot-redundant"
NETWORK_CONFLICT = "network-conflict"
SINGLE_POINT_OF_FAILURE = "single-point-of-failure"
OUTAGE_EXCEEDED = "outage-exceeded"

# Relative tolerance for the outage comparison, so a failover chain sized to
# exactly meet its budget passes on every host rather than on some of them.
REL_TOL = 1e-9

UNIT_FIELDS = ("powered", "attached", "segments", "address", "drives_medium")


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_nonnegative(value, name):
    """Return a duration that is zero or above."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_unit(unit, name="unit"):
    """Return one validated unit of a redundant pair.

    Every field is required. A missing 'powered' or 'attached' is the exact
    ambiguity this clause is about, so it is refused rather than assumed.
    """
    if not isinstance(unit, dict):
        raise ValueError("%s must be a mapping" % name)
    missing = set(UNIT_FIELDS) - set(unit)
    if missing:
        raise ValueError("%s is missing %s" % (name, ", ".join(sorted(missing))))
    for flag in ("powered", "attached", "drives_medium"):
        if not isinstance(unit[flag], bool):
            raise ValueError("%s.%s must be a boolean" % (name, flag))
    segments = unit["segments"]
    if isinstance(segments, (str, bytes)) or not isinstance(segments, (list, tuple, set)):
        raise ValueError("%s.segments must be a sequence of segment names" % name)
    named = []
    for segment in segments:
        if not isinstance(segment, str) or not segment.strip():
            raise ValueError("%s.segments entries must be non-empty strings" % name)
        named.append(segment.strip())
    if not named:
        raise ValueError("%s.segments must name at least one segment" % name)
    address = unit["address"]
    if isinstance(address, bool) or not isinstance(address, (int, str)):
        raise ValueError("%s.address must be an integer or a string" % name)
    if isinstance(address, str) and not address.strip():
        raise ValueError("%s.address must not be blank" % name)
    return {
        "powered": unit["powered"],
        "attached": unit["attached"],
        "segments": frozenset(named),
        "address": address.strip() if isinstance(address, str) else address,
        "drives_medium": unit["drives_medium"],
    }


def is_hot_redundant(nominal, redundant):
    """Say whether both units are powered and on the network at once."""
    first = validate_unit(nominal, "nominal")
    second = validate_unit(redundant, "redundant")
    return all(
        unit["powered"] and unit["attached"] for unit in (first, second)
    )


def network_conflicts(nominal, redundant):
    """Return every way this pair being on the network at once harms it."""
    first = validate_unit(nominal, "nominal")
    second = validate_unit(redundant, "redundant")
    both_attached = first["attached"] and second["attached"]
    conflicts = []
    if both_attached and first["drives_medium"] and second["drives_medium"]:
        conflicts.append(
            "two transmitters are enabled on one medium, so the standby can "
            "corrupt traffic the active unit is sending"
        )
    if both_attached and first["address"] == second["address"]:
        conflicts.append(
            "both units answer to address %r, so the standby's health cannot "
            "be polled apart from the active unit's" % (first["address"],)
        )
    return conflicts


def single_point_segment(nominal, redundant):
    """Return the segment whose loss takes both units, or None when there is none.

    A pair is safe from a segment failure as soon as one unit can still be
    reached another way, so the fault only exists when BOTH units hang off the
    same single segment.
    """
    first = validate_unit(nominal, "nominal")
    second = validate_unit(redundant, "redundant")
    if len(first["segments"]) == 1 and first["segments"] == second["segments"]:
        return sorted(first["segments"])[0]
    return None


def failover_outage_s(detection_s, switchover_s, reinitialisation_s):
    """Return how long the function is unavailable across a takeover."""
    detection = validate_nonnegative(detection_s, "detection_s")
    switchover = validate_nonnegative(switchover_s, "switchover_s")
    reinit = validate_nonnegative(reinitialisation_s, "reinitialisation_s")
    return detection + switchover + reinit


def required_detection_s(outage_budget_s, switchover_s, reinitialisation_s):
    """Return the detection time the outage budget leaves.

    None means no detection time helps: switchover and re-initialisation alone
    already spend the budget, so the fix is a faster takeover, not a faster
    alarm.
    """
    budget = validate_nonnegative(outage_budget_s, "outage_budget_s")
    switchover = validate_nonnegative(switchover_s, "switchover_s")
    reinit = validate_nonnegative(reinitialisation_s, "reinitialisation_s")
    remaining = budget - switchover - reinit
    if remaining < 0.0:
        return None
    return remaining


def assess_hot_redundancy(nominal, redundant, detection_s=0.0, switchover_s=0.0,
                          reinitialisation_s=0.0, outage_budget_s=None):
    """Grade one redundant node pair against both items of the clause."""
    first = validate_unit(nominal, "nominal")
    second = validate_unit(redundant, "redundant")
    hot = is_hot_redundant(nominal, redundant)
    conflicts = network_conflicts(nominal, redundant)
    shared_segment = single_point_segment(nominal, redundant)
    outage = failover_outage_s(detection_s, switchover_s, reinitialisation_s)
    budget = None
    if outage_budget_s is not None:
        budget = validate_nonnegative(outage_budget_s, "outage_budget_s")
    within_budget = True
    if budget is not None:
        within_budget = outage <= budget + REL_TOL * max(1.0, budget)
    findings = []
    if not hot:
        verdict = NOT_HOT_REDUNDANT
        for label, unit in (("nominal", first), ("redundant", second)):
            if not unit["powered"]:
                findings.append(
                    "the %s unit is unpowered, so a takeover costs a power-up "
                    "and this is a cold spare" % label
                )
            elif not unit["attached"]:
                findings.append(
                    "the %s unit is powered but off the network, so a takeover "
                    "costs an attach and this is a warm spare" % label
                )
    elif conflicts:
        verdict = NETWORK_CONFLICT
        findings.extend(conflicts)
    elif shared_segment is not None:
        verdict = SINGLE_POINT_OF_FAILURE
        findings.append(
            "both units hang off segment %r alone, so losing it takes the pair "
            "and the redundancy buys nothing against a segment fault"
            % shared_segment
        )
    elif not within_budget:
        verdict = OUTAGE_EXCEEDED
        headroom = required_detection_s(budget, switchover_s, reinitialisation_s)
        findings.append(
            "failover takes %.6g s against a %.6g s outage budget"
            % (outage, budget)
        )
        if headroom is None:
            findings.append(
                "no detection time fits: switchover and re-initialisation "
                "alone spend the budget, so the takeover itself has to shorten"
            )
        else:
            findings.append(
                "detection has to come down to %.6g s, or the budget up to "
                "%.6g s" % (headroom, outage)
            )
    else:
        verdict = HOT_REDUNDANT
    if budget is None:
        findings.append(
            "no outage budget was declared, so the failover chain is reported "
            "but not graded"
        )
    return {
        "hot_redundant": hot,
        "conflicts": conflicts,
        "single_point_segment": shared_segment,
        "cross_strapped": shared_segment is None,
        "failover_outage_s": outage,
        "outage_budget_s": budget,
        "within_outage_budget": within_budget,
        "required_detection_s": (
            None if budget is None
            else required_detection_s(budget, switchover_s, reinitialisation_s)
        ),
        "verdict": verdict,
        "findings": findings,
    }

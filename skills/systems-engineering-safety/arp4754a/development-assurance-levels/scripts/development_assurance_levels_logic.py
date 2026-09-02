#!/usr/bin/env python3
"""ARP4754A development assurance levels (DAL) logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a / arp4761a):
a failure condition is rated by severity from its effect on the
aircraft and occupants, using the ARP4761A FHA categories
(catastrophic, hazardous, major, minor, no safety effect). The
severity drives the development assurance level of the function that
can cause it: A = Catastrophic down to E = No safety effect (paraphrase
of the ARP4754A severity-to-DAL assignment). The function development
assurance level (FDAL) is assigned to each function; the item
development assurance level (IDAL) is assigned to each item that
implements a function. The IDAL of an item must not be lower than the
FDAL of the function it implements unless an approved justification
supports the lower level; validated independence between redundant
items is the classic alternative to raising the item DAL. All logic is
deterministic, stdlib only, offline.

Worked anchors (verified by scripts/test_development_assurance_levels.py):
    dal_from_severity("Catastrophic") == "A"
    dal_from_severity("No safety effect") == "E"
    severity_from_dal("B") == "Hazardous"
    severity_rank("Major") == 3
    dal_index("C") == 3
    validate_dal_propagation("A", "A") is True
    validate_dal_propagation("C", "A") is True
    validate_dal_propagation("A", "C") raises ValueError (item below function)
    independence_justifies_lower_item_dal("A", "C", False) is False
    independence_justifies_lower_item_dal("A", "C", True) is True
    assurance_assignment("Autopilot", "Loss of all pitch authority",
        "Catastrophic")["fdal"] == "A"
"""

SEVERITY_TO_DAL = {
    "Catastrophic": "A",
    "Hazardous": "B",
    "Major": "C",
    "Minor": "D",
    "No safety effect": "E",
}

DAL_TO_SEVERITY = {dal: severity for severity, dal in SEVERITY_TO_DAL.items()}

# 5 = most severe, used for ordering and propagation comparison.
SEVERITY_RANK = {
    "Catastrophic": 5,
    "Hazardous": 4,
    "Major": 3,
    "Minor": 2,
    "No safety effect": 1,
}

# A = highest assurance; a higher index means a higher (stricter) level.
DAL_INDEX = {
    "A": 5,
    "B": 4,
    "C": 3,
    "D": 2,
    "E": 1,
}


def _check_severity(severity):
    if severity not in SEVERITY_TO_DAL:
        raise ValueError(
            "unknown failure-condition severity: %r (expected one of %s)"
            % (severity, ", ".join(sorted(SEVERITY_TO_DAL)))
        )


def _check_dal(dal):
    if dal not in DAL_INDEX:
        raise ValueError(
            "unknown development assurance level: %r (expected one of %s)"
            % (dal, ", ".join(sorted(DAL_INDEX)))
        )


def _check_bool(flag, name):
    if not isinstance(flag, bool):
        raise ValueError("%s must be a bool, got %r" % (name, flag))


def severity_rank(severity):
    """Rank of a severity category, 5 = catastrophic down to 1 = no
    safety effect. Anchor: severity_rank("Major") == 3;
    severity_rank("Catastrophic") == 5."""
    _check_severity(severity)
    return SEVERITY_RANK[severity]


def dal_index(dal):
    """Index of a development assurance level, A = 5 down to E = 1.
    Anchor: dal_index("C") == 3; dal_index("A") == 5."""
    _check_dal(dal)
    return DAL_INDEX[dal]


def dal_from_severity(severity):
    """Development assurance level (A through E) for a failure condition
    severity. Anchor: dal_from_severity("Catastrophic") == "A";
    dal_from_severity("Hazardous") == "B";
    dal_from_severity("No safety effect") == "E".
    Raises ValueError on an unknown severity."""
    _check_severity(severity)
    return SEVERITY_TO_DAL[severity]


def severity_from_dal(dal):
    """Severity category that a development assurance level corresponds
    to. Anchor: severity_from_dal("A") == "Catastrophic";
    severity_from_dal("B") == "Hazardous". Raises ValueError on an
    unknown level."""
    _check_dal(dal)
    return DAL_TO_SEVERITY[dal]


def validate_dal_propagation(function_dal, item_dal):
    """Check DAL propagation from a function to an item.

    The IDAL of an item must not be lower than the FDAL of the function
    it implements (a higher index is a stricter level). Returns True
    when the item DAL is at or above the function DAL; raises ValueError
    when the item DAL is lower (an unjustified reduction) or when either
    level is unknown. Anchor:
    validate_dal_propagation("A", "A") is True;
    validate_dal_propagation("C", "A") is True;
    validate_dal_propagation("A", "C") raises ValueError."""
    _check_dal(function_dal)
    _check_dal(item_dal)
    if DAL_INDEX[item_dal] < DAL_INDEX[function_dal]:
        raise ValueError(
            "item DAL %s is lower than function DAL %s; the reduction "
            "must be justified (for example by validated independence)"
            % (item_dal, function_dal)
        )
    return True


def independence_justifies_lower_item_dal(function_dal, item_dal,
                                          independence_established):
    """Bookkeeping check for the independence alternative to raising the
    item DAL.

    When the item DAL is at or above the function DAL there is nothing
    to justify and the result is True. When the item DAL is lower, the
    reduction is acceptable only if a validated independence argument
    (no common cause between the redundant items, per the ARP4761A
    common-cause analysis) is recorded. Anchor:
    independence_justifies_lower_item_dal("A", "A", False) is True;
    independence_justifies_lower_item_dal("A", "C", False) is False;
    independence_justifies_lower_item_dal("A", "C", True) is True."""
    _check_dal(function_dal)
    _check_dal(item_dal)
    _check_bool(independence_established, "independence_established")
    if DAL_INDEX[item_dal] >= DAL_INDEX[function_dal]:
        return True
    return independence_established


def assurance_assignment(function, failure_condition, severity,
                         independence_established=False):
    """FDAL/IDAL assignment record for one function and the items that
    implement it.

    The FDAL comes from the severity of the failure condition; the
    initial IDAL of the items equals the FDAL (the ARP4754A starting
    point), and any later reduction must be justified. The record also
    carries whether a validated independence argument exists for the
    items; the final item levels are recorded in the item development
    plan. Anchor:
    assurance_assignment("Autopilot", "Loss of all pitch authority",
    "Catastrophic")["fdal"] == "A" and ["idal"] == "A"."""
    for name, value in (("function", function),
                        ("failure_condition", failure_condition)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string" % name)
    _check_severity(severity)
    _check_bool(independence_established, "independence_established")
    fdal = SEVERITY_TO_DAL[severity]
    return {
        "function": function.strip(),
        "failure_condition": failure_condition.strip(),
        "severity": severity,
        "fdal": fdal,
        "idal": fdal,
        "independence_established": independence_established,
        "propagation_ok": True,
    }


def demonstrate():
    """Print a demonstration of severity-to-DAL assignment and
    propagation checks."""
    rows = [
        ("Autopilot", "Loss of all pitch authority", "Catastrophic"),
        ("Thrust Reverser", "Inadvertent deployment in flight", "Hazardous"),
        ("Cabin Lighting", "Loss of cabin lighting", "Minor"),
    ]
    for function, failure_condition, severity in rows:
        record = assurance_assignment(function, failure_condition, severity)
        print("%-16s %-34s -> severity=%-16s FDAL=%s IDAL=%s propagation=%s"
              % (function, failure_condition, severity, record["fdal"],
                 record["idal"], record["propagation_ok"]))
    print("propagation (A, C) without independence ->",
          independence_justifies_lower_item_dal("A", "C", False))
    print("propagation (A, C) with independence ->",
          independence_justifies_lower_item_dal("A", "C", True))


if __name__ == "__main__":
    demonstrate()

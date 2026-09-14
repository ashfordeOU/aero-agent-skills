"""Purchasing-control assessment for class 2 commercial EEE part procurement.

Anchor: ECSS-Q-ST-60-13C clause 5.3.1 (the purchasing controls that have to
sit around a buy of commercial electrical, electronic and electromechanical
parts so that what is delivered matches the intermediate assurance
expectations). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared supply channel. The channel sizes the control
   register, so an undeclared or unrecognized channel is refused rather than
   defaulted to the direct route.
2. Build the control register for that channel: the base controls every buy
   carries, plus the controls the channel adds because the manufacturer's own
   chain of custody no longer covers them.
3. Validate each declared assignment: the control it names, a normalized owner
   drawn from the permitted roles, an evidence reference, and, where the
   control is delegated to the supplier, the flow-down clause it was imposed
   under and the certificate that came back.
4. Grade every control in the register as held by the project, delegated to
   the supplier at a credited weight, or open carrying the reason it is open.
   This class permits delegation, which the class above does not, and the
   credit is what stops a buy assembled entirely out of supplier certificates
   reading the same as one the project verified itself.
5. Report any assignment naming a control the register does not carry.
6. Take the covered share and the weighted coverage of the register and
   compare the weighted figure with the declared floor under a named
   tolerance.
7. Close on one verdict carrying every finding.
"""

import math

__all__ = [
    "SUPPLY_CHANNELS",
    "BASE_CONTROLS",
    "CHANNEL_EXTRA_CONTROLS",
    "PROJECT_ROLES",
    "SUPPLIER_ROLE",
    "COVERAGE_TOLERANCE",
    "validate_channel",
    "control_register",
    "validate_coverage_policy",
    "validate_control_assignment",
    "collect_assignments",
    "grade_control",
    "coverage_figures",
    "assess_procurement_overview",
]

# The supply channels a class 2 buy may declare.
SUPPLY_CHANNELS = (
    "manufacturer-direct",
    "franchised-distributor",
    "independent-distributor",
    "open-market-broker",
)

# The controls every buy carries whatever the channel.
BASE_CONTROLS = (
    "part-requirements-stated-on-the-order",
    "supplier-approved-for-this-supply",
    "delivery-verified-against-the-order",
    "lot-traceability-recorded",
)

# What each channel adds on top of the base register.
CHANNEL_EXTRA_CONTROLS = {
    "manufacturer-direct": (),
    "franchised-distributor": ("franchise-status-confirmed-at-the-order-date",),
    "independent-distributor": (
        "manufacturer-traceability-rebuilt",
        "counterfeit-avoidance-screening",
    ),
    "open-market-broker": (
        "manufacturer-traceability-rebuilt",
        "counterfeit-avoidance-screening",
        "authenticity-test-on-receipt",
        "source-risk-accepted-by-the-project",
    ),
}

# Who inside the arrangement may own a control.
PROJECT_ROLES = (
    "project-component-engineer",
    "procurement-officer",
    "product-assurance-manager",
)

# The one owner outside the project a control may be delegated to.
SUPPLIER_ROLE = "supplier"

# Coverage is a ratio of small integers scaled by a credit; an exactly met
# floor must not fail on representation alone.
COVERAGE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _unit_interval(value, label):
    """Return a finite float inside the closed unit interval."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, number))
    return number


def validate_channel(channel):
    """Return the validated supply channel the buy was made through."""
    if channel is None:
        raise ValueError(
            "supply channel is undeclared; the channel sizes the control "
            "register and cannot be defaulted to the direct route"
        )
    token = _normalize_token(channel, "supply channel")
    if token not in SUPPLY_CHANNELS:
        raise ValueError(
            "supply channel '%s' is not recognized; expected one of %s"
            % (token, ", ".join(SUPPLY_CHANNELS))
        )
    return token


def control_register(channel):
    """Return the ordered control register the declared channel has to meet."""
    token = validate_channel(channel)
    return tuple(BASE_CONTROLS) + tuple(CHANNEL_EXTRA_CONTROLS[token])


def validate_coverage_policy(policy):
    """Return the validated coverage policy for the buy."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in ("coverage_floor", "delegation_credit"):
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    coverage_floor = _unit_interval(policy["coverage_floor"], "coverage_floor")
    delegation_credit = _unit_interval(
        policy["delegation_credit"], "delegation_credit"
    )
    if delegation_credit <= 0.0:
        raise ValueError(
            "delegation_credit must be positive; a credit of nothing makes a "
            "delegated control indistinguishable from an open one"
        )
    if delegation_credit >= 1.0:
        raise ValueError(
            "delegation_credit must be below 1; a full credit makes a buy of "
            "pure supplier certificates score as one the project verified"
        )
    return {
        "coverage_floor": coverage_floor,
        "delegation_credit": delegation_credit,
    }


def validate_control_assignment(assignment):
    """Return one validated assignment of a purchasing control to an owner."""
    if not isinstance(assignment, dict):
        raise ValueError("each assignment must be a mapping")
    for key in ("control", "owner"):
        if key not in assignment:
            raise ValueError("assignment missing required key '%s'" % key)
    control = _normalize_token(assignment["control"], "control")
    owner = _normalize_token(assignment["owner"], "owner")
    evidence = assignment.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        raise ValueError(
            "evidence for control '%s' must be a string reference or None" % control
        )
    flow_down = assignment.get("flow_down_clause")
    if flow_down is not None and not isinstance(flow_down, str):
        raise ValueError(
            "flow_down_clause for control '%s' must be a string or None" % control
        )
    certificate = assignment.get("supplier_certificate")
    if certificate is not None and not isinstance(certificate, str):
        raise ValueError(
            "supplier_certificate for control '%s' must be a string or None" % control
        )
    return {
        "control": control,
        "owner": owner,
        "evidence": (evidence or "").strip(),
        "flow_down_clause": (flow_down or "").strip(),
        "supplier_certificate": (certificate or "").strip(),
    }


def collect_assignments(assignments):
    """Return the validated assignments keyed by control, rejecting a repeat."""
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("assignments must be a sequence")
    collected = {}
    for assignment in assignments:
        record = validate_control_assignment(assignment)
        if record["control"] in collected:
            raise ValueError(
                "control '%s' is assigned twice" % record["control"]
            )
        collected[record["control"]] = record
    return collected


def grade_control(name, assignment, policy):
    """Return the graded state of one control in the register."""
    graded_policy = validate_coverage_policy(policy)
    control = _normalize_token(name, "control name")
    if assignment is None:
        return {
            "control": control,
            "state": "open",
            "reason": "no owner assigned",
            "owner": None,
            "weight": 0.0,
        }
    if not isinstance(assignment, dict) or "owner" not in assignment:
        raise ValueError("assignment for '%s' must be a validated mapping" % control)
    owner = assignment["owner"]
    if owner == SUPPLIER_ROLE:
        if not assignment.get("flow_down_clause"):
            return {
                "control": control,
                "state": "open",
                "reason": "delegated to the supplier under no flow-down clause",
                "owner": owner,
                "weight": 0.0,
            }
        if not assignment.get("supplier_certificate"):
            return {
                "control": control,
                "state": "open",
                "reason": "delegated to the supplier with no certificate returned",
                "owner": owner,
                "weight": 0.0,
            }
        return {
            "control": control,
            "state": "delegated",
            "reason": None,
            "owner": owner,
            "weight": graded_policy["delegation_credit"],
        }
    if owner not in PROJECT_ROLES:
        return {
            "control": control,
            "state": "open",
            "reason": "owner '%s' has no standing in the arrangement" % owner,
            "owner": owner,
            "weight": 0.0,
        }
    if not assignment.get("evidence"):
        return {
            "control": control,
            "state": "open",
            "reason": "assigned with no evidence cited",
            "owner": owner,
            "weight": 0.0,
        }
    return {
        "control": control,
        "state": "held",
        "reason": None,
        "owner": owner,
        "weight": 1.0,
    }


def coverage_figures(graded):
    """Return the covered share and the weighted coverage of the register."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded controls")
    total = len(graded)
    covered = 0
    weight = 0.0
    for entry in graded:
        if not isinstance(entry, dict) or "state" not in entry:
            raise ValueError("each graded control must be a mapping with a state")
        if entry["state"] in ("held", "delegated"):
            covered += 1
        weight += float(entry.get("weight", 0.0))
    return {
        "register_size": total,
        "covered": covered,
        "covered_share": covered / total,
        "weighted_coverage": weight / total,
    }


def assess_procurement_overview(case):
    """Run the full clause 5.3.1 purchasing-control assessment.

    case keys: policy, supply_channel, assignments.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("policy", "supply_channel", "assignments"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)

    policy = validate_coverage_policy(case["policy"])
    channel = validate_channel(case["supply_channel"])
    register = control_register(channel)
    collected = collect_assignments(case["assignments"])

    graded = [grade_control(name, collected.get(name), policy) for name in register]
    figures = coverage_figures(graded)

    findings = []
    open_controls = [entry for entry in graded if entry["state"] == "open"]
    for entry in open_controls:
        findings.append(
            "purchasing control '%s' is open: %s" % (entry["control"], entry["reason"])
        )

    extraneous = [name for name in collected if name not in register]
    for name in sorted(extraneous):
        findings.append(
            "assignment names control '%s', which the '%s' register does not carry"
            % (name, channel)
        )

    coverage_short = figures["weighted_coverage"] < policy["coverage_floor"] and \
        not math.isclose(
            figures["weighted_coverage"], policy["coverage_floor"],
            rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE,
        )
    if coverage_short:
        findings.append(
            "weighted purchasing coverage %.3f is below the declared floor %.3f"
            % (figures["weighted_coverage"], policy["coverage_floor"])
        )

    delegated = [entry["control"] for entry in graded if entry["state"] == "delegated"]

    if not collected:
        verdict = "purchasing controls not established"
    elif open_controls:
        verdict = "purchasing control open"
    elif coverage_short:
        verdict = "purchasing coverage below the declared floor"
    else:
        verdict = "purchasing controls meet class 2 expectations"

    return {
        "policy": policy,
        "supply_channel": channel,
        "register": list(register),
        "graded": graded,
        "open_controls": [entry["control"] for entry in open_controls],
        "delegated_controls": delegated,
        "extraneous_assignments": sorted(extraneous),
        "figures": figures,
        "verdict": verdict,
        "acceptable": verdict == "purchasing controls meet class 2 expectations",
        "findings": findings,
    }

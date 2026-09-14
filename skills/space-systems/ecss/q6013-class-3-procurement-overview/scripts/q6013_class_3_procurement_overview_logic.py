"""Purchasing-control assessment for lowest-assurance commercial EEE buys.

Anchor: ECSS-Q-ST-60-13C clause 6.3.1 (the purchasing controls that have to
sit around an order for commercial electrical, electronic and electromechanical
parts bought at the lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

What makes this class different from the classes above is that the order is an
ordinary commercial order. Nothing about the transaction makes it a controlled
buy on its own, so each control is graded on the rigour actually reached rather
than on whether somebody was named against it.

Procedure implemented here
--------------------------
1. Validate the assurance policy: the floor the weighted purchasing assurance
   index has to reach.
2. Validate the declared supply channel. The channel sizes the control
   register and sets the rigour minimum of the controls it adds, so an
   undeclared or unrecognized channel is refused rather than defaulted.
3. Build the register for that channel: the controls every order carries at
   their class 3 minimum rigour, plus the controls the channel adds.
4. Validate every declared control and place its claimed rigour on the ladder
   not-performed < supplier-declared < project-recorded < project-verified.
5. Demote a claim of project-recorded or better that cites no evidence to a
   supplier declaration, because an undocumented claim is an assertion.
6. Grade each control in the register: met, short of its minimum, or never
   performed, crediting a short control by the ratio of the rigour reached to
   the rigour required.
7. Report a declaration naming a control the register does not carry.
8. Take the purchasing assurance index and compare it with the floor under a
   named tolerance, then close on one verdict carrying every finding.
"""

import math

__all__ = [
    "RIGOUR_LADDER",
    "SUPPLY_CHANNELS",
    "BASE_CONTROL_MINIMA",
    "CHANNEL_CONTROL_MINIMA",
    "ASSURANCE_TOLERANCE",
    "rigour_index",
    "validate_channel",
    "control_register",
    "validate_assurance_policy",
    "validate_control_declaration",
    "collect_declarations",
    "effective_rigour",
    "grade_purchasing_control",
    "assurance_index",
    "assess_class3_procurement",
]

# The rigour a purchasing control can reach, weakest first. The position on
# this ladder is the whole grading currency at this class.
RIGOUR_LADDER = (
    "not-performed",
    "supplier-declared",
    "project-recorded",
    "project-verified",
)

# The supply channels an order at this class may declare.
SUPPLY_CHANNELS = (
    "manufacturer-direct",
    "authorized-distributor",
    "independent-distributor",
    "open-market-broker",
)

# The controls every order carries, with the rigour this class asks of each.
BASE_CONTROL_MINIMA = (
    ("manufacturer-part-number-and-variant-fixed-on-the-order", "project-recorded"),
    ("single-manufacturer-per-part-type-across-the-build", "project-recorded"),
    ("date-code-band-requested-on-the-order", "project-recorded"),
    ("packaging-and-esd-condition-stated-on-the-order", "supplier-declared"),
    ("receipt-record-kept-against-the-order", "project-recorded"),
)

# What each channel adds, and at what rigour, because the chain of custody the
# manufacturer would otherwise supply stops at the channel.
CHANNEL_CONTROL_MINIMA = {
    "manufacturer-direct": (),
    "authorized-distributor": (
        ("distributor-authorization-valid-at-the-order-date", "project-recorded"),
    ),
    "independent-distributor": (
        ("origin-evidence-obtained-from-the-distributor", "project-recorded"),
        ("counterfeit-avoidance-screening-performed", "project-verified"),
    ),
    "open-market-broker": (
        ("origin-evidence-obtained-from-the-distributor", "project-recorded"),
        ("counterfeit-avoidance-screening-performed", "project-verified"),
        ("authenticity-verification-on-receipt", "project-verified"),
        ("residual-source-risk-accepted-by-the-project", "project-recorded"),
    ),
}

# The index is a mean of ratios of small integers; a figure landing exactly on
# the floor must not fail on representation alone.
ASSURANCE_TOLERANCE = 1e-9


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


def rigour_index(rigour):
    """Return the position of a rigour level on the ladder."""
    token = _normalize_token(rigour, "rigour")
    if token not in RIGOUR_LADDER:
        raise ValueError(
            "rigour '%s' is not on the ladder; expected one of %s"
            % (token, ", ".join(RIGOUR_LADDER))
        )
    return RIGOUR_LADDER.index(token)


def validate_channel(channel):
    """Return the validated supply channel the order was placed through."""
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
    """Return the ordered register of controls and rigour minima for a channel."""
    token = validate_channel(channel)
    return tuple(BASE_CONTROL_MINIMA) + tuple(CHANNEL_CONTROL_MINIMA[token])


def validate_assurance_policy(policy):
    """Return the validated purchasing assurance policy for the order."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    if "assurance_floor" not in policy:
        raise ValueError("policy missing required key 'assurance_floor'")
    floor = _unit_interval(policy["assurance_floor"], "assurance_floor")
    if floor <= 0.0:
        raise ValueError(
            "assurance_floor must be positive; a floor of nothing accepts an "
            "order with no purchasing control performed at all"
        )
    return {"assurance_floor": floor}


def validate_control_declaration(declaration):
    """Return one validated declaration of a purchasing control and its rigour."""
    if not isinstance(declaration, dict):
        raise ValueError("each declaration must be a mapping")
    for key in ("control", "rigour"):
        if key not in declaration:
            raise ValueError("declaration missing required key '%s'" % key)
    control = _normalize_token(declaration["control"], "control")
    rigour = RIGOUR_LADDER[rigour_index(declaration["rigour"])]
    evidence = declaration.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        raise ValueError(
            "evidence for control '%s' must be a string reference or None" % control
        )
    return {
        "control": control,
        "claimed_rigour": rigour,
        "evidence": (evidence or "").strip(),
    }


def collect_declarations(declarations):
    """Return the validated declarations keyed by control, rejecting a repeat."""
    if not isinstance(declarations, (list, tuple)):
        raise ValueError("declarations must be a sequence")
    collected = {}
    for declaration in declarations:
        record = validate_control_declaration(declaration)
        if record["control"] in collected:
            raise ValueError("control '%s' is declared twice" % record["control"])
        collected[record["control"]] = record
    return collected


def effective_rigour(declaration):
    """Return the rigour a declaration actually earns, after demotion.

    A claim of project-recorded or better that cites no evidence is an
    assertion, and an assertion is worth no more than a supplier declaration.
    """
    if not isinstance(declaration, dict) or "claimed_rigour" not in declaration:
        raise ValueError("declaration must be a validated mapping")
    claimed = rigour_index(declaration["claimed_rigour"])
    recorded = RIGOUR_LADDER.index("project-recorded")
    if claimed >= recorded and not declaration.get("evidence"):
        return RIGOUR_LADDER.index("supplier-declared"), True
    return claimed, False


def grade_purchasing_control(control, required_rigour, declaration):
    """Return the graded state of one control against its rigour minimum."""
    name = _normalize_token(control, "control name")
    required = rigour_index(required_rigour)
    if required <= 0:
        raise ValueError(
            "control '%s' cannot require the not-performed level" % name
        )
    if declaration is None:
        return {
            "control": name,
            "required_rigour": RIGOUR_LADDER[required],
            "reached_rigour": RIGOUR_LADDER[0],
            "state": "not-performed",
            "reason": "no purchasing control declared",
            "demoted": False,
            "credit": 0.0,
        }
    reached, demoted = effective_rigour(declaration)
    credit = min(reached / required, 1.0)
    if reached <= 0:
        state = "not-performed"
        reason = "declared at the not-performed level"
    elif reached >= required:
        state = "met"
        reason = None
    else:
        state = "short"
        reason = "reached %s where %s is required" % (
            RIGOUR_LADDER[reached],
            RIGOUR_LADDER[required],
        )
    if demoted and state != "met":
        reason = "%s (claim demoted: no evidence cited)" % reason
    return {
        "control": name,
        "required_rigour": RIGOUR_LADDER[required],
        "reached_rigour": RIGOUR_LADDER[reached],
        "state": state,
        "reason": reason,
        "demoted": demoted,
        "credit": credit,
    }


def assurance_index(graded):
    """Return the weighted purchasing assurance index of a graded register."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded controls")
    total = 0.0
    met = 0
    for entry in graded:
        if not isinstance(entry, dict) or "credit" not in entry:
            raise ValueError("each graded control must be a mapping with a credit")
        total += float(entry["credit"])
        if entry.get("state") == "met":
            met += 1
    size = len(graded)
    return {
        "register_size": size,
        "controls_met": met,
        "met_share": met / size,
        "assurance_index": total / size,
    }


def assess_class3_procurement(case):
    """Run the full clause 6.3.1 purchasing assessment for a class 3 order.

    case keys: policy, supply_channel, declarations.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("policy", "supply_channel", "declarations"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)

    policy = validate_assurance_policy(case["policy"])
    channel = validate_channel(case["supply_channel"])
    register = control_register(channel)
    collected = collect_declarations(case["declarations"])

    graded = [
        grade_purchasing_control(name, minimum, collected.get(name))
        for name, minimum in register
    ]
    figures = assurance_index(graded)

    findings = []
    not_performed = [e for e in graded if e["state"] == "not-performed"]
    short = [e for e in graded if e["state"] == "short"]
    for entry in not_performed:
        findings.append(
            "purchasing control '%s' is not performed: %s"
            % (entry["control"], entry["reason"])
        )
    for entry in short:
        findings.append(
            "purchasing control '%s' is below its minimum: %s"
            % (entry["control"], entry["reason"])
        )

    register_names = [name for name, _ in register]
    extraneous = [name for name in collected if name not in register_names]
    for name in sorted(extraneous):
        findings.append(
            "declaration names control '%s', which the '%s' register does not carry"
            % (name, channel)
        )

    index_short = figures["assurance_index"] < policy["assurance_floor"] and not \
        math.isclose(
            figures["assurance_index"],
            policy["assurance_floor"],
            rel_tol=0.0,
            abs_tol=ASSURANCE_TOLERANCE,
        )
    if index_short:
        findings.append(
            "purchasing assurance index %.3f is below the declared floor %.3f"
            % (figures["assurance_index"], policy["assurance_floor"])
        )

    if not collected:
        verdict = "purchasing controls not declared"
    elif not_performed:
        verdict = "purchasing control not performed"
    elif short:
        verdict = "purchasing control below its required rigour"
    elif index_short:
        verdict = "purchasing assurance below the declared floor"
    else:
        verdict = "purchasing controls meet class 3 expectations"

    return {
        "policy": policy,
        "supply_channel": channel,
        "register": [{"control": n, "required_rigour": r} for n, r in register],
        "graded": graded,
        "controls_not_performed": [e["control"] for e in not_performed],
        "controls_short": [e["control"] for e in short],
        "demoted_claims": [e["control"] for e in graded if e["demoted"]],
        "extraneous_declarations": sorted(extraneous),
        "figures": figures,
        "verdict": verdict,
        "acceptable": verdict == "purchasing controls meet class 3 expectations",
        "findings": findings,
    }

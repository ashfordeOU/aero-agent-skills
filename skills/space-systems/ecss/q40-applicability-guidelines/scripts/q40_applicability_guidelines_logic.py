"""Applicability guidelines: which safety requirement groups bite, and when.

Anchor: the informative annex of ECSS-Q-ST-40C that gives applicability
guidelines for the safety requirements by product type and by programme phase,
used when the requirements are tailored onto a specific project. Paraphrased
into an implementable procedure; no standard text is reproduced. The annex is
informative, so the output here is advice a tailoring board weighs, not a
verdict it is bound by.

Procedure implemented here
--------------------------
1. For a product type, each requirement group has an earliest phase at which it
   starts to bite, or is out of scope for that product entirely, or bites only
   in a reduced form. That is three different answers and they must not be
   collapsed into applicable / not applicable.
2. Applicability is therefore a function of two inputs, product type and
   phase, and asking about one without the other gives an answer that is right
   half the time.
3. A tailoring proposal is then graded against that guideline: deleting a group
   the guideline has biting is the case that needs an argument and customer
   agreement, and deleting it with no justification at all is the finding.
4. The mirror case is retaining a group the guideline puts out of scope. That
   is not a safety finding; it is cost, and it belongs in the report as cost.
5. Roll the proposals up into a tailoring position with the arguable deletions
   separated from the unjustified ones.
"""

__all__ = [
    "PRODUCT_TYPES",
    "PHASES",
    "REQUIREMENT_GROUPS",
    "ACTIONS",
    "APPLICABILITY_STATES",
    "GUIDELINES",
    "validate_context",
    "guideline_for",
    "applicability",
    "applicable_groups",
    "validate_proposal",
    "assess_tailoring_proposal",
    "assess_tailoring_set",
]

PRODUCT_TYPES = (
    "launch-vehicle",
    "manned-orbital-system",
    "unmanned-orbital-system",
    "reentry-vehicle",
    "payload-instrument",
    "ground-segment-equipment",
)

PHASES = ("phase-0", "phase-a", "phase-b", "phase-c", "phase-d", "phase-e", "phase-f")

REQUIREMENT_GROUPS = (
    "safety-programme",
    "hazard-analysis",
    "safety-risk-assessment",
    "safety-verification",
    "ground-equipment-conformity",
    "operational-safety",
    "disposal-safety",
)

ACTIONS = ("retain", "tailor", "delete", "defer")

APPLICABILITY_STATES = (
    "applicable",
    "applicable-reduced",
    "not-yet-applicable",
    "out-of-scope",
)

# Per product type: group -> the earliest phase at which the group bites, or
# None when the group is out of scope for that product. A group listed in
# "reduced" bites in a reduced form rather than in full.
GUIDELINES = {
    "launch-vehicle": {
        "from": {
            "safety-programme": "phase-0",
            "hazard-analysis": "phase-a",
            "safety-risk-assessment": "phase-a",
            "safety-verification": "phase-b",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-c",
            "disposal-safety": "phase-b",
        },
        "reduced": (),
    },
    "manned-orbital-system": {
        "from": {
            "safety-programme": "phase-0",
            "hazard-analysis": "phase-0",
            "safety-risk-assessment": "phase-a",
            "safety-verification": "phase-b",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-b",
            "disposal-safety": "phase-b",
        },
        "reduced": (),
    },
    "unmanned-orbital-system": {
        "from": {
            "safety-programme": "phase-0",
            "hazard-analysis": "phase-a",
            "safety-risk-assessment": "phase-a",
            "safety-verification": "phase-b",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-c",
            "disposal-safety": "phase-b",
        },
        "reduced": ("operational-safety",),
    },
    "reentry-vehicle": {
        "from": {
            "safety-programme": "phase-0",
            "hazard-analysis": "phase-a",
            "safety-risk-assessment": "phase-a",
            "safety-verification": "phase-b",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-b",
            "disposal-safety": "phase-a",
        },
        "reduced": (),
    },
    "payload-instrument": {
        "from": {
            "safety-programme": "phase-a",
            "hazard-analysis": "phase-b",
            "safety-risk-assessment": "phase-b",
            "safety-verification": "phase-c",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-d",
            "disposal-safety": None,
        },
        "reduced": ("safety-programme", "ground-equipment-conformity"),
    },
    "ground-segment-equipment": {
        "from": {
            "safety-programme": "phase-b",
            "hazard-analysis": "phase-b",
            "safety-risk-assessment": "phase-c",
            "safety-verification": "phase-c",
            "ground-equipment-conformity": "phase-c",
            "operational-safety": "phase-d",
            "disposal-safety": None,
        },
        "reduced": ("safety-risk-assessment",),
    },
}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _member(value, label, allowed):
    token = _text(value, label).lower()
    if token not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return token


def validate_context(product_type, phase):
    """Return the normalised product type and programme phase."""
    return (
        _member(product_type, "product_type", PRODUCT_TYPES),
        _member(phase, "phase", PHASES),
    )


def guideline_for(product_type):
    """Return the applicability guideline entry for a product type."""
    return GUIDELINES[_member(product_type, "product_type", PRODUCT_TYPES)]


def applicability(product_type, phase, group):
    """Return the applicability state of one requirement group in this context."""
    product, phase = validate_context(product_type, phase)
    group = _member(group, "group", REQUIREMENT_GROUPS)
    entry = guideline_for(product)
    start = entry["from"][group]
    if start is None:
        return "out-of-scope"
    if PHASES.index(phase) < PHASES.index(start):
        return "not-yet-applicable"
    if group in entry["reduced"]:
        return "applicable-reduced"
    return "applicable"


def applicable_groups(product_type, phase):
    """Return the groups biting in this context, keyed by applicability state."""
    product, phase = validate_context(product_type, phase)
    grouped = dict((state, []) for state in APPLICABILITY_STATES)
    for group in REQUIREMENT_GROUPS:
        grouped[applicability(product, phase, group)].append(group)
    return grouped


def validate_proposal(record):
    """Return a normalised tailoring proposal for one requirement group."""
    if not isinstance(record, dict):
        raise ValueError("proposal must be a mapping")
    justification = record.get("justification")
    if justification is not None:
        justification = _text(justification, "justification")
    agreed = record.get("customer_agreed", False)
    if not isinstance(agreed, bool):
        raise ValueError("customer_agreed must be true or false, got %r" % (agreed,))
    product, phase = validate_context(
        record.get("product_type"), record.get("phase")
    )
    return {
        "product_type": product,
        "phase": phase,
        "group": _member(record.get("group"), "group", REQUIREMENT_GROUPS),
        "action": _member(record.get("action"), "action", ACTIONS),
        "justification": justification,
        "customer_agreed": agreed,
    }


def assess_tailoring_proposal(record):
    """Return the advisory grading of one tailoring proposal."""
    norm = validate_proposal(record)
    state = applicability(norm["product_type"], norm["phase"], norm["group"])
    findings = []
    consistent = True

    if norm["action"] == "delete":
        if state in ("applicable", "applicable-reduced"):
            consistent = False
            if norm["justification"] is None:
                findings.append(
                    "deletes %s, which the guideline has %s here, with no"
                    " justification recorded" % (norm["group"], state)
                )
            elif not norm["customer_agreed"]:
                findings.append(
                    "deletes %s against the guideline with a justification the"
                    " customer has not agreed" % norm["group"]
                )
            else:
                findings.append(
                    "deletes %s against the guideline; justified and agreed, so"
                    " carry it in the tailoring record" % norm["group"]
                )
        elif state == "not-yet-applicable":
            findings.append(
                "deletes %s before it starts to bite; defer would keep it in"
                " view for the phase that needs it" % norm["group"]
            )
    elif norm["action"] == "retain":
        if state == "out-of-scope":
            findings.append(
                "retains %s, which the guideline puts out of scope for this"
                " product; that is cost, not safety" % norm["group"]
            )
    elif norm["action"] == "tailor":
        if state == "out-of-scope":
            findings.append(
                "tailors %s, which is out of scope here, so there is nothing to"
                " tailor" % norm["group"]
            )
        elif state == "applicable" and norm["justification"] is None:
            consistent = False
            findings.append(
                "tailors %s, which the guideline has applicable in full, with no"
                " justification recorded" % norm["group"]
            )
    elif norm["action"] == "defer":
        if state in ("applicable", "applicable-reduced"):
            consistent = False
            findings.append(
                "defers %s past the phase at which the guideline has it biting"
                % norm["group"]
            )

    return {
        "product_type": norm["product_type"],
        "phase": norm["phase"],
        "group": norm["group"],
        "action": norm["action"],
        "guideline_state": state,
        "findings": findings,
        "consistent_with_guideline": consistent,
        "needs_customer_agreement": norm["action"] == "delete"
        and state in ("applicable", "applicable-reduced"),
    }


def assess_tailoring_set(records):
    """Return the advisory tailoring position across a set of proposals."""
    items = list(records)
    if not items:
        raise ValueError("at least one tailoring proposal is needed")
    reports = [assess_tailoring_proposal(item) for item in items]
    seen = set()
    for report in reports:
        key = (report["product_type"], report["phase"], report["group"])
        if key in seen:
            raise ValueError(
                "requirement group %r is proposed twice for the same context"
                % report["group"]
            )
        seen.add(key)

    unjustified = [
        r["group"]
        for r in reports
        if not r["consistent_with_guideline"]
        and any("no justification recorded" in f for f in r["findings"])
    ]
    arguable = [
        r["group"]
        for r in reports
        if not r["consistent_with_guideline"] and r["group"] not in unjustified
    ]
    advisory = [r["group"] for r in reports if r["consistent_with_guideline"] and r["findings"]]
    consistent_ratio = sum(
        1 for r in reports if r["consistent_with_guideline"]
    ) / float(len(reports))

    if unjustified:
        position = "tailoring-unsupported"
    elif arguable:
        position = "tailoring-needs-agreement"
    else:
        position = "tailoring-consistent"

    return {
        "proposals": reports,
        "unjustified_groups": unjustified,
        "arguable_groups": arguable,
        "advisory_groups": advisory,
        "consistent_ratio": consistent_ratio,
        "position": position,
    }

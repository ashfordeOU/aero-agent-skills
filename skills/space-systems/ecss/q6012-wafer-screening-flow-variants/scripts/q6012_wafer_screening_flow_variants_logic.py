"""Alternative screening and acceptance sequences per procurement situation.

Anchor: ECSS-Q-ST-60-12C clause 10.2.2 -- the screening and acceptance
measurement flow varies with how the parts were procured. Paraphrased into an
implementable procedure; no standard text is reproduced.

Two questions live here and they are answered in order:

  1. Which variant applies. The procurement facts -- wafers or die, screened by
     the supplier or not, a process already approved or a first lot -- select
     exactly one reference sequence. A combination no variant covers is
     refused, because inventing a flow for it is how an unscreened die lot gets
     accepted on a wafer lot's paperwork.
  2. Whether a proposed sequence is that variant. A flow is not graded by
     matching the reference list position for position: stages that are free to
     run in either order may. It is graded on two things instead -- every stage
     the variant requires is present, and no ordering constraint the evidence
     depends on is inverted.

The ordering constraints are the part that carries meaning. A measurement taken
before a stress and a measurement taken after it are a drift pair; run in the
other order they are two unrelated datasets that happen to exist. Constraints
apply to whichever stages the flow actually contains, so a reduced variant is
held to the subset that applies to it and not to stages it never runs.

A stage a variant does not require is reported as an addition, not a defect: a
buyer may run more than the minimum, and the flow is still the variant.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "EQUIVALENT",
    "REORDER_REQUIRED",
    "INCOMPLETE",
    "SUPPLIER_DATA_REVIEW",
    "INITIAL_INSPECTION",
    "PRE_STRESS_MEASUREMENT",
    "WAFER_LEVEL_STRESS",
    "POST_STRESS_MEASUREMENT",
    "DRIFT_ASSESSMENT",
    "ACCEPTANCE_MEASUREMENT",
    "LOT_ACCEPTANCE_DECISION",
    "KNOWN_STAGES",
    "ORDERING_CONSTRAINTS",
    "SITUATIONS",
    "validate_situation",
    "validate_sequence",
    "select_situation",
    "reference_sequence",
    "required_stages",
    "applicable_constraints",
    "missing_stages",
    "added_stages",
    "inverted_pairs",
    "drift_pairs_available",
    "stage_coverage_fraction",
    "assess_flow",
]

EQUIVALENT = "equivalent"
REORDER_REQUIRED = "reorder-required"
INCOMPLETE = "incomplete"

SUPPLIER_DATA_REVIEW = "supplier-data-review"
INITIAL_INSPECTION = "initial-visual-inspection"
PRE_STRESS_MEASUREMENT = "pre-stress-measurement"
WAFER_LEVEL_STRESS = "wafer-level-stress"
POST_STRESS_MEASUREMENT = "post-stress-measurement"
DRIFT_ASSESSMENT = "drift-assessment"
ACCEPTANCE_MEASUREMENT = "acceptance-measurement"
LOT_ACCEPTANCE_DECISION = "lot-acceptance-decision"

KNOWN_STAGES = (
    SUPPLIER_DATA_REVIEW,
    INITIAL_INSPECTION,
    PRE_STRESS_MEASUREMENT,
    WAFER_LEVEL_STRESS,
    POST_STRESS_MEASUREMENT,
    DRIFT_ASSESSMENT,
    ACCEPTANCE_MEASUREMENT,
    LOT_ACCEPTANCE_DECISION,
)

# (before, after) pairs the evidence itself demands. Each applies only where
# both of its stages are present in the flow being graded.
ORDERING_CONSTRAINTS = (
    (INITIAL_INSPECTION, WAFER_LEVEL_STRESS),
    (PRE_STRESS_MEASUREMENT, WAFER_LEVEL_STRESS),
    (WAFER_LEVEL_STRESS, POST_STRESS_MEASUREMENT),
    (PRE_STRESS_MEASUREMENT, DRIFT_ASSESSMENT),
    (POST_STRESS_MEASUREMENT, DRIFT_ASSESSMENT),
    (SUPPLIER_DATA_REVIEW, ACCEPTANCE_MEASUREMENT),
    (DRIFT_ASSESSMENT, LOT_ACCEPTANCE_DECISION),
    (ACCEPTANCE_MEASUREMENT, LOT_ACCEPTANCE_DECISION),
)

# One reference sequence per procurement situation.
SITUATIONS = {
    "unscreened-wafer-procurement": (
        INITIAL_INSPECTION,
        PRE_STRESS_MEASUREMENT,
        WAFER_LEVEL_STRESS,
        POST_STRESS_MEASUREMENT,
        DRIFT_ASSESSMENT,
        ACCEPTANCE_MEASUREMENT,
        LOT_ACCEPTANCE_DECISION,
    ),
    "supplier-screened-wafer-procurement": (
        SUPPLIER_DATA_REVIEW,
        INITIAL_INSPECTION,
        ACCEPTANCE_MEASUREMENT,
        LOT_ACCEPTANCE_DECISION,
    ),
    "screened-die-procurement": (
        SUPPLIER_DATA_REVIEW,
        ACCEPTANCE_MEASUREMENT,
        LOT_ACCEPTANCE_DECISION,
    ),
    "recurrent-lot-approved-process": (
        SUPPLIER_DATA_REVIEW,
        WAFER_LEVEL_STRESS,
        POST_STRESS_MEASUREMENT,
        ACCEPTANCE_MEASUREMENT,
        LOT_ACCEPTANCE_DECISION,
    ),
}


def validate_situation(name):
    """Return a known procurement situation name."""
    if isinstance(name, bool) or not isinstance(name, str):
        raise ValueError("situation must be a string, got %r" % (name,))
    token = name.strip()
    if token not in SITUATIONS:
        raise ValueError(
            "unknown procurement situation %r; known: %s"
            % (token, ", ".join(sorted(SITUATIONS)))
        )
    return token


def validate_sequence(stages):
    """Return the proposed stages as a tuple, refusing junk and repeats."""
    if isinstance(stages, (str, bytes)) or not hasattr(stages, "__iter__"):
        raise ValueError("stages must be a sequence of stage names")
    out = []
    seen = set()
    for item in stages:
        if isinstance(item, bool) or not isinstance(item, str):
            raise ValueError("stage must be a string, got %r" % (item,))
        token = item.strip()
        if not token:
            raise ValueError("stage must not be blank")
        if token not in KNOWN_STAGES:
            raise ValueError(
                "unknown stage %r; known: %s" % (token, ", ".join(KNOWN_STAGES))
            )
        if token in seen:
            raise ValueError("stage %r appears twice in the flow" % token)
        seen.add(token)
        out.append(token)
    if not out:
        raise ValueError("the proposed flow names no stages")
    return tuple(out)


def select_situation(context):
    """Return the variant the procurement facts select.

    context keys: delivery_form ('wafer' or 'die'), supplier_screened (bool)
    and process_previously_approved (bool). A combination no variant covers
    raises rather than falling back to the fullest flow.
    """
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping")
    form = context.get("delivery_form")
    if isinstance(form, bool) or not isinstance(form, str):
        raise ValueError("delivery_form must be 'wafer' or 'die'")
    form = form.strip().lower()
    if form not in ("wafer", "die"):
        raise ValueError("delivery_form must be 'wafer' or 'die', got %r" % form)
    screened = context.get("supplier_screened")
    approved = context.get("process_previously_approved")
    for label, flag in (("supplier_screened", screened), ("process_previously_approved", approved)):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean, got %r" % (label, flag))
    if form == "die":
        if not screened:
            raise ValueError(
                "die delivered without supplier screening is not covered by a "
                "variant; wafer level screening cannot be run on separated die"
            )
        return "screened-die-procurement"
    if screened:
        return "supplier-screened-wafer-procurement"
    if approved:
        return "recurrent-lot-approved-process"
    return "unscreened-wafer-procurement"


def reference_sequence(situation):
    """Return the reference stage order for a situation."""
    return SITUATIONS[validate_situation(situation)]


def required_stages(situation):
    """Return the stages the situation's variant requires, in order."""
    return reference_sequence(situation)


def applicable_constraints(stages):
    """Return the ordering pairs whose two stages are both in this flow."""
    present = set(validate_sequence(stages))
    return tuple(
        (a, b) for a, b in ORDERING_CONSTRAINTS if a in present and b in present
    )


def missing_stages(situation, proposed):
    """Return required stages the proposal omits, in reference order."""
    needed = required_stages(situation)
    have = set(validate_sequence(proposed))
    return tuple(s for s in needed if s not in have)


def added_stages(situation, proposed):
    """Return stages beyond the variant, in the order proposed."""
    needed = set(required_stages(situation))
    return tuple(s for s in validate_sequence(proposed) if s not in needed)


def inverted_pairs(proposed):
    """Return the ordering pairs this flow runs the wrong way round."""
    order = validate_sequence(proposed)
    position = {stage: i for i, stage in enumerate(order)}
    out = []
    for a, b in applicable_constraints(order):
        if position[a] > position[b]:
            out.append((a, b))
    return tuple(out)


def drift_pairs_available(proposed):
    """Return 1 where a measurement straddles the stress, else 0.

    A pre-stress and a post-stress measurement on either side of the stress
    are a drift pair. Run in any other order they are two datasets, so the
    count is a property of the order and not of the stage list.
    """
    order = validate_sequence(proposed)
    position = {stage: i for i, stage in enumerate(order)}
    needed = (PRE_STRESS_MEASUREMENT, WAFER_LEVEL_STRESS, POST_STRESS_MEASUREMENT)
    if any(stage not in position for stage in needed):
        return 0
    if position[PRE_STRESS_MEASUREMENT] < position[WAFER_LEVEL_STRESS] < position[POST_STRESS_MEASUREMENT]:
        return 1
    return 0


def stage_coverage_fraction(situation, proposed):
    """Return the share of the variant's stages the proposal contains."""
    needed = required_stages(situation)
    have = set(validate_sequence(proposed))
    return sum(1 for s in needed if s in have) / float(len(needed))


def assess_flow(situation, proposed):
    """Grade a proposed screening and acceptance flow against its variant."""
    name = validate_situation(situation)
    order = validate_sequence(proposed)
    absent = missing_stages(name, order)
    added = added_stages(name, order)
    inverted = inverted_pairs(order)
    findings = []
    for stage in absent:
        findings.append("the %s variant requires %s, which the flow omits" % (name, stage))
    for a, b in inverted:
        findings.append("%s is run after %s; the evidence needs the other order" % (a, b))
    for stage in added:
        findings.append("%s is run beyond the %s variant" % (stage, name))
    if absent:
        verdict = INCOMPLETE
    elif inverted:
        verdict = REORDER_REQUIRED
    else:
        verdict = EQUIVALENT
    return {
        "situation": name,
        "reference_sequence": reference_sequence(name),
        "proposed_sequence": order,
        "missing_stages": absent,
        "added_stages": added,
        "inverted_pairs": inverted,
        "drift_pairs_available": drift_pairs_available(order),
        "stage_coverage_fraction": stage_coverage_fraction(name, order),
        "acceptable": verdict == EQUIVALENT,
        "verdict": verdict,
        "findings": tuple(findings),
    }

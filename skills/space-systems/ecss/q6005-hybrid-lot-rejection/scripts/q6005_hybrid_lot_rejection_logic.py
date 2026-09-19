"""Declaring a hybrid production lot unacceptable after screening or acceptance.

Anchor: ECSS-Q-ST-60-05C clause 10.4 (the framework for declaring a production
batch of hybrid microcircuits unacceptable following screening or acceptance
results). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the recorded stage verdicts against the mandatory screening and
   lot-acceptance sequence, refusing an unknown stage, an unknown verdict or a
   stage recorded twice.
2. Measure the evidence chain: how much of the mandatory sequence actually ran.
   A stage that never ran contributes no information, and an absent verdict is
   not a pass.
3. Find the earliest failing stage. Order matters: the stage that first
   revealed the defect is the one the lot decision and any later re-screen are
   anchored to.
4. Decide the scope of a rejection. It falls on the whole lot unless the
   failures are confined to one sublot that is both physically segregated and
   still traceable.
5. Return accepted, rejected or indeterminate, say whether the declaration is
   admissible on the evidence, and name the obligations the status carries.
"""

import math

__all__ = [
    "EVIDENCE_TOLERANCE",
    "MANDATORY_SEQUENCE",
    "STATUS_OBLIGATIONS",
    "VERDICTS",
    "declare_lot_status",
    "evidence_completeness",
    "first_failing_stage",
    "missing_stages",
    "rejection_scope",
    "stage_order",
    "status_obligations",
    "validate_stage_verdicts",
]

# The mandatory screening and lot-acceptance sequence a delivered hybrid lot
# passes through, in the order it is worked.
MANDATORY_SEQUENCE = (
    "internal-visual",
    "stabilization-bake",
    "temperature-cycling",
    "constant-acceleration",
    "burn-in",
    "final-electrical",
    "seal-fine-leak",
    "seal-gross-leak",
    "external-visual",
    "lot-acceptance-tests",
)

VERDICTS = ("pass", "fail", "not-run")

# Completeness is a quotient of integers that lands exactly on one for a fully
# worked lot. The comparison absorbs representation error here rather than by
# relaxing the condition.
EVIDENCE_TOLERANCE = 1e-9

STATUS_OBLIGATIONS = {
    "accepted": (
        "release-the-lot-with-its-screening-record",
    ),
    "rejected": (
        "quarantine-the-lot",
        "open-a-failure-analysis",
        "notify-the-customer",
        "hold-disposition-until-the-customer-is-notified",
    ),
    "indeterminate": (
        "quarantine-the-lot",
        "complete-the-missing-stage-evidence",
    ),
}


def _clean_token(value, label):
    """Return a name normalised for case and separator, raising on non-strings."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def stage_order(stage):
    """Return the position of a mandatory stage in the worked sequence."""
    token = _clean_token(stage, "stage")
    if token not in MANDATORY_SEQUENCE:
        raise ValueError("unknown screening stage %r" % (stage,))
    return MANDATORY_SEQUENCE.index(token)


def validate_stage_verdicts(records):
    """Return the recorded stage verdicts, normalised and in worked order.

    Each record names a mandatory stage and one of the permitted verdicts. A
    stage recorded twice is refused rather than resolved: two verdicts for one
    stage means the lot record itself is in doubt.
    """
    if isinstance(records, dict) or not isinstance(records, (list, tuple)):
        raise ValueError("stage verdicts must be a sequence of records")
    if not records:
        raise ValueError("no stage verdicts recorded for the lot")
    seen = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("stage verdicts[%d] must be a mapping" % index)
        for key in ("stage", "verdict"):
            if key not in record:
                raise ValueError("stage verdicts[%d] needs a '%s'" % (index, key))
        stage = _clean_token(record["stage"], "stage verdicts[%d]['stage']" % index)
        if stage not in MANDATORY_SEQUENCE:
            raise ValueError("unknown screening stage %r" % (record["stage"],))
        verdict = _clean_token(record["verdict"], "stage verdicts[%d]['verdict']" % index)
        if verdict not in VERDICTS:
            raise ValueError("unknown verdict %r for stage %s" % (record["verdict"], stage))
        if stage in seen:
            raise ValueError("stage %s carries two verdicts" % stage)
        seen[stage] = verdict
    return [
        {"stage": stage, "verdict": seen[stage], "order": order}
        for order, stage in enumerate(MANDATORY_SEQUENCE)
        if stage in seen
    ]


def _verdict_map(records):
    return {item["stage"]: item["verdict"] for item in validate_stage_verdicts(records)}


def missing_stages(records):
    """Return the mandatory stages with no run verdict, in worked order."""
    verdicts = _verdict_map(records)
    return [
        stage
        for stage in MANDATORY_SEQUENCE
        if verdicts.get(stage, "not-run") == "not-run"
    ]


def evidence_completeness(records):
    """Return the fraction of the mandatory sequence that actually ran."""
    absent = len(missing_stages(records))
    return (len(MANDATORY_SEQUENCE) - absent) / float(len(MANDATORY_SEQUENCE))


def first_failing_stage(records):
    """Return the earliest mandatory stage that failed, or None."""
    verdicts = _verdict_map(records)
    for stage in MANDATORY_SEQUENCE:
        if verdicts.get(stage) == "fail":
            return stage
    return None


def rejection_scope(context):
    """Return whether a rejection falls on the whole lot or on one sublot.

    A sublot-scoped rejection needs all three of: failures confined to that
    sublot, the sublot physically segregated, and its traceability intact. Any
    one of them absent and the rejection is lot-wide.
    """
    if not isinstance(context, dict):
        raise ValueError("scope context must be a mapping")
    keys = (
        "failures_confined_to_one_sublot",
        "sublot_physically_segregated",
        "sublot_traceability_intact",
    )
    values = []
    for key in keys:
        value = context.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (key, value))
        values.append(value)
    return "sublot" if all(values) else "whole-lot"


def status_obligations(status):
    """Return the obligations a declared lot status carries."""
    token = _clean_token(status, "status")
    if token not in STATUS_OBLIGATIONS:
        raise ValueError("unknown lot status %r" % (status,))
    return STATUS_OBLIGATIONS[token]


def declare_lot_status(spec):
    """Run the full clause 10.4 lot-rejection declaration.

    spec keys: stage_verdicts, declared_by, plus the optional scope context
    keys read by rejection_scope.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("stage_verdicts", "declared_by"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    declared_by = _clean_token(spec["declared_by"], "declared_by")
    records = validate_stage_verdicts(spec["stage_verdicts"])
    absent = missing_stages(spec["stage_verdicts"])
    completeness = evidence_completeness(spec["stage_verdicts"])
    complete = math.isclose(completeness, 1.0, rel_tol=0.0, abs_tol=EVIDENCE_TOLERANCE)
    failing = first_failing_stage(spec["stage_verdicts"])

    findings = []
    if failing is not None:
        status = "rejected"
    elif absent:
        status = "indeterminate"
        findings.append(
            "no failure recorded, but %d mandatory stage(s) never ran: %s"
            % (len(absent), ", ".join(absent))
        )
    else:
        status = "accepted"

    scope = rejection_scope(spec) if status == "rejected" else "not-applicable"

    admissible = True
    if status == "rejected":
        gap = [stage for stage in absent if stage_order(stage) < stage_order(failing)]
        if gap:
            admissible = False
            findings.append(
                "declaration rests on an incomplete chain: %s never ran before %s"
                % (", ".join(gap), failing)
            )
        if scope == "sublot":
            findings.append(
                "rejection scoped to the segregated sublot; the rest of the lot "
                "keeps its screening record"
            )
    return {
        "status": status,
        "first_failing_stage": failing,
        "missing_stages": absent,
        "evidence_completeness": completeness,
        "evidence_complete": complete,
        "recorded_stage_count": len(records),
        "scope": scope,
        "declared_by": declared_by,
        "admissible": admissible,
        "obligations": list(status_obligations(status)),
        "findings": findings,
        "rejected": status == "rejected",
    }

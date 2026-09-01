"""Corrective action (CAPA) record logic for aerospace manufacturing.

Paraphrase of AS9100 corrective action practice (clause framing,
summarized, not copied): a corrective action record progresses
through containment, root cause analysis (five whys), corrective
action definition, and effectiveness verification before it can
close a nonconformance. The module is a deterministic state machine
over a record dict; it computes no physical quantities.

Record keys: problem (str), containment (str), whys (list of str),
corrective_action (str), preventive_action (str, optional),
effectiveness_evidence (str, optional), root_cause_statement
(str, optional, used for the circular-evidence check).
"""

MIN_WHY_DEPTH = 3

# Ordered closure stages; each gates the next.
STAGES = ("containment", "root-cause", "corrective-action", "effectiveness")

# Placeholder answers that do not count as recorded actions.
NON_ANSWERS = frozenset(("", "none", "n/a", "na", "no", "unknown", "not-applicable"))

# Required record keys.
REQUIRED_KEYS = ("problem", "containment", "whys", "corrective_action")


def _clean(text):
    return (text or "").strip()


def containment_ok(containment):
    """True when a containment action is recorded and not a placeholder.

    Containment is the immediate action that isolates the effect of a
    nonconformance; 'none' or an empty string does not count.
    """
    c = _clean(containment)
    return bool(c) and c.lower() not in NON_ANSWERS


def root_cause_chain_ok(whys, min_depth=MIN_WHY_DEPTH):
    """Five-whys chain check: enough levels, each answer non-empty and
    distinct from the previous answer.

    A repeated adjacent answer is circular (asking 'why' again returns
    the same text), so it fails. A chain shorter than min_depth is
    incomplete regardless of content.
    """
    if not isinstance(whys, (list, tuple)):
        return False
    chain = [_clean(w) for w in whys]
    if len(chain) < min_depth:
        return False
    prev = None
    for w in chain:
        if not w or w.lower() in NON_ANSWERS:
            return False
        if prev is not None and w.lower() == prev.lower():
            return False
        prev = w
    return True


def corrective_action_ok(action):
    """True when a corrective action is recorded and not a placeholder.

    The corrective action removes the root cause; a blank or
    placeholder entry cannot close the record.
    """
    a = _clean(action)
    return bool(a) and a.lower() not in NON_ANSWERS


def effectiveness_evidence_ok(evidence, root_cause_statement=None):
    """True when effectiveness evidence exists and does not restate the
    root cause.

    Evidence that merely repeats the root cause statement proves
    nothing (circular evidence); it must describe an observed result.
    """
    e = _clean(evidence)
    if not e or e.lower() in NON_ANSWERS:
        return False
    rc = _clean(root_cause_statement)
    return not (rc and e.lower() == rc.lower())


def record_status(record):
    """Closure stage of a corrective action record.

    Returns one of: containment-missing, root-cause-incomplete,
    corrective-action-missing, effectiveness-pending, closed. Raises
    ValueError for a non-dict record or a missing required key.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a dict, got %r" % (record,))
    missing = [k for k in REQUIRED_KEYS if k not in record]
    if missing:
        raise ValueError("record missing required key(s): %s" % ", ".join(missing))
    if not containment_ok(record.get("containment")):
        return "containment-missing"
    if not root_cause_chain_ok(record.get("whys")):
        return "root-cause-incomplete"
    if not corrective_action_ok(record.get("corrective_action")):
        return "corrective-action-missing"
    if not effectiveness_evidence_ok(
        record.get("effectiveness_evidence"), record.get("root_cause_statement")
    ):
        return "effectiveness-pending"
    return "closed"


def closure_verdict(record):
    """Dict with the stage status and the items still missing.

    The missing list names exactly what the record needs before it can
    move to the next stage.
    """
    status = record_status(record)
    if status == "containment-missing":
        missing = ["containment"]
    elif status == "root-cause-incomplete":
        missing = ["whys (at least %d distinct levels)" % MIN_WHY_DEPTH]
    elif status == "corrective-action-missing":
        missing = ["corrective_action"]
    elif status == "effectiveness-pending":
        missing = ["effectiveness_evidence"]
    else:
        missing = []
    return {"status": status, "missing": missing}


def stage_required_fields(stage):
    """Record keys required up to and including the given stage.

    Raises ValueError for an unknown stage name.
    """
    if stage not in STAGES:
        raise ValueError(
            "unknown stage %r; expected one of %s" % (stage, ", ".join(STAGES))
        )
    fields = ["problem"]
    if stage in ("root-cause", "corrective-action", "effectiveness"):
        fields.append("containment")
    if stage in ("corrective-action", "effectiveness"):
        fields.append("whys")
    if stage == "effectiveness":
        fields.append("corrective_action")
    return fields

"""Reconciling the crimping practice with the harness manufacturing rules.

Anchor: the interface between ECSS-Q-ST-70-26C and ECSS-Q-ST-20-30C --
both reach the same harness bench, so each shared topic needs one
owning document and the shop needs one instruction (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Every shared topic is allocated to exactly one governing document.
   A topic named in one document only is governed by that one; the
   interesting cases are the topics both reach.
2. Where both state a limit in the same direction, the stricter limit
   governs and the looser one is recorded as superseded. Stricter
   means the larger value for a floor and the smaller for a ceiling,
   which is why the direction is carried with the value.
3. Where an applicability matrix makes one document subordinate for a
   topic, the senior document governs whatever the numbers say. A
   project can flow a harness rule down over a process rule, and that
   decision outranks the arithmetic.
4. Two limits in opposite directions are not a strictness question.
   A floor from one document and a ceiling from the other describe a
   band, and if the band is empty the topic is a conflict rather than
   a choice.
5. Two differing non-numeric rules with no subordination declared are
   an unresolved conflict. Picking one silently is how a harness gets
   built to an instruction nobody approved.
6. A required topic neither document reaches is a gap, not a free
   choice. It is reported so the project writes it down somewhere.
7. Two limits that are numerically equal agree. The comparison
   absorbs representation error from a unit conversion rather than
   declaring a conflict over the last bit.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

MINIMUM = "minimum"
MAXIMUM = "maximum"

SINGLE = "single-document-governs"
STRICTER = "stricter-limit-governs"
SENIOR = "senior-document-governs"
AGREED = "both-documents-agree"
CONFLICT = "unresolved-conflict-escalate"
GAP = "topic-allocated-to-neither-document"

RECONCILED = "instruction-set-reconciled"
RECONCILED_WITH_GAPS = "instruction-set-reconciled-with-gaps"
ESCALATE = "escalate-the-conflicts-to-the-project"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    return float(value)


def validate_interface(spec):
    """Validate the declared document interface."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    crimping = _text("crimping_document", spec.get("crimping_document")).lower()
    harness = _text("harness_document", spec.get("harness_document")).lower()
    if crimping == harness:
        raise ValueError("the two documents must be different")

    topics = spec.get("required_topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("required_topics must be a non-empty list")
    required = sorted({_text("required_topic", t).lower() for t in topics})

    subordination = spec.get("subordination", {})
    if not isinstance(subordination, dict):
        raise ValueError("subordination must be a mapping")
    resolved = {}
    for topic, senior in subordination.items():
        key = _text("subordination_topic", topic).lower()
        document = _text("senior_document", senior).lower()
        if document not in (crimping, harness):
            raise ValueError(
                "senior document %r for topic %r is not one of the two "
                "documents" % (document, key)
            )
        resolved[key] = document

    return {
        "crimping_document": crimping,
        "harness_document": harness,
        "required_topics": required,
        "subordination": resolved,
    }


def validate_requirement(requirement, spec):
    """Validate one requirement stated by one of the two documents."""
    checked_spec = validate_interface(spec)
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    document = _text("document", requirement.get("document")).lower()
    if document not in (
        checked_spec["crimping_document"],
        checked_spec["harness_document"],
    ):
        raise ValueError("document %r is outside this interface" % document)

    topic = _text("topic", requirement.get("topic")).lower()
    kind = _text("kind", requirement.get("kind")).lower()
    if kind == "limit":
        direction = _text("direction", requirement.get("direction")).lower()
        if direction not in (MINIMUM, MAXIMUM):
            raise ValueError(
                "direction %r must be a minimum or a maximum" % direction
            )
        return {
            "document": document,
            "topic": topic,
            "kind": kind,
            "direction": direction,
            "value": _numeric("value", requirement.get("value")),
            "rule_id": None,
        }
    if kind == "rule":
        return {
            "document": document,
            "topic": topic,
            "kind": kind,
            "direction": None,
            "value": None,
            "rule_id": _text("rule_id", requirement.get("rule_id")).lower(),
        }
    raise ValueError("kind %r must be a limit or a rule" % kind)


def stricter_limit(first, second):
    """Which of two same-direction limits is the stricter one."""
    if first["direction"] != second["direction"]:
        raise ValueError("limits in opposite directions are not comparable")
    if abs(first["value"] - second["value"]) <= TOLERANCE:
        return None
    if first["direction"] == MINIMUM:
        return first if first["value"] > second["value"] else second
    return first if first["value"] < second["value"] else second


def band_is_empty(first, second):
    """Do a floor from one document and a ceiling from the other overlap?"""
    if first["direction"] == second["direction"]:
        raise ValueError("both limits point the same way; this is not a band")
    floor = first if first["direction"] == MINIMUM else second
    ceiling = second if first["direction"] == MINIMUM else first
    return floor["value"] > ceiling["value"] + TOLERANCE


def allocate_topic(topic, requirements, spec):
    """Decide which document governs one topic, and with what."""
    checked_spec = validate_interface(spec)
    name = _text("topic", topic).lower()
    stated = [
        validate_requirement(r, spec)
        for r in requirements
        if _text("topic", r.get("topic")).lower() == name
    ]

    if not stated:
        return {
            "topic": name,
            "basis": GAP,
            "governing_document": None,
            "instruction": None,
            "superseded": [],
        }

    documents = sorted({r["document"] for r in stated})
    if len(documents) == 1:
        chosen = stated[0]
        return {
            "topic": name,
            "basis": SINGLE,
            "governing_document": chosen["document"],
            "instruction": chosen,
            "superseded": [],
        }

    senior = checked_spec["subordination"].get(name)
    if senior is not None:
        chosen = [r for r in stated if r["document"] == senior][0]
        return {
            "topic": name,
            "basis": SENIOR,
            "governing_document": senior,
            "instruction": chosen,
            "superseded": [r["document"] for r in stated if r is not chosen],
        }

    first = [r for r in stated if r["document"] == documents[0]][0]
    second = [r for r in stated if r["document"] == documents[1]][0]

    if first["kind"] == "limit" and second["kind"] == "limit":
        if first["direction"] == second["direction"]:
            chosen = stricter_limit(first, second)
            if chosen is None:
                return {
                    "topic": name,
                    "basis": AGREED,
                    "governing_document": first["document"],
                    "instruction": first,
                    "superseded": [],
                }
            other = second if chosen is first else first
            return {
                "topic": name,
                "basis": STRICTER,
                "governing_document": chosen["document"],
                "instruction": chosen,
                "superseded": [other["document"]],
            }
        if band_is_empty(first, second):
            return {
                "topic": name,
                "basis": CONFLICT,
                "governing_document": None,
                "instruction": None,
                "superseded": [],
                "reason": "the-two-limits-leave-an-empty-band",
            }
        return {
            "topic": name,
            "basis": STRICTER,
            "governing_document": None,
            "instruction": {"kind": "band", "limits": [first, second]},
            "superseded": [],
        }

    if (
        first["kind"] == "rule"
        and second["kind"] == "rule"
        and first["rule_id"] == second["rule_id"]
    ):
        return {
            "topic": name,
            "basis": AGREED,
            "governing_document": first["document"],
            "instruction": first,
            "superseded": [],
        }

    return {
        "topic": name,
        "basis": CONFLICT,
        "governing_document": None,
        "instruction": None,
        "superseded": [],
        "reason": "the-two-documents-state-different-requirements",
    }


def reconcile_interface(spec, requirements):
    """Reconcile both documents into one instruction set for the shop."""
    checked_spec = validate_interface(spec)
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")

    stated_topics = sorted(
        {validate_requirement(r, spec)["topic"] for r in requirements}
    )
    for topic in stated_topics:
        if topic not in checked_spec["required_topics"]:
            raise ValueError(
                "topic %r is stated but is not in the required topic list"
                % topic
            )

    allocations = [
        allocate_topic(topic, requirements, spec)
        for topic in checked_spec["required_topics"]
    ]
    conflicts = [a["topic"] for a in allocations if a["basis"] == CONFLICT]
    gaps = [a["topic"] for a in allocations if a["basis"] == GAP]

    if conflicts:
        verdict = ESCALATE
    elif gaps:
        verdict = RECONCILED_WITH_GAPS
    else:
        verdict = RECONCILED

    return {
        "allocations": allocations,
        "verdict": verdict,
        "conflicts": conflicts,
        "gaps": gaps,
        "governed_by_crimping": [
            a["topic"]
            for a in allocations
            if a["governing_document"] == checked_spec["crimping_document"]
        ],
        "governed_by_harness": [
            a["topic"]
            for a in allocations
            if a["governing_document"] == checked_spec["harness_document"]
        ],
        "shop_has_one_instruction": not conflicts and not gaps,
    }

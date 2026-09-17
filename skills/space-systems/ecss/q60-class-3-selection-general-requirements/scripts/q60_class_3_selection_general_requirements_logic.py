"""General expectations governing Class 3 part selection before procurement.

Anchor: ECSS-Q-ST-60C clause 6.2.1 (the overarching expectations a Class 3
part selection has to satisfy before a procurement decision is taken).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the selection prerequisites as a fixed ledger. Each carries a weight,
   because they are not equal, and a blocking flag, because some of them stop
   a purchase order outright while others only cost the project later.
2. Declare every prerequisite as closed, open or not applicable. A
   prerequisite nobody declared is open, not absent, and a not-applicable
   declaration without a recorded justification is open as well.
3. Refuse a waiver raised against a blocking prerequisite. A waiver on a
   non-blocking one closes it for the readiness reading when a rationale was
   recorded, and is reported as closed under waiver rather than simply closed.
4. Weight the prerequisites that still apply, compute the readiness index over
   them, and list the blocking prerequisites still open.
5. Name the single prerequisite worth closing next, so the project is told what
   to do rather than only how far it has to go.
6. Return one selection verdict with findings ranked worst first.
"""

import math

__all__ = [
    "PREREQUISITES",
    "PREREQUISITE_NAMES",
    "READINESS_TOLERANCE",
    "SELECTION_STATES",
    "validate_candidate_id",
    "prerequisite_weight",
    "prerequisite_is_blocking",
    "normalise_state",
    "declare_prerequisite",
    "readiness_index",
    "blocking_open",
    "next_prerequisite_to_close",
    "assess_class_3_selection_readiness",
]

# name -> (weight, blocking). Declaration order is the tie-break order.
PREREQUISITES = (
    ("parts-control-plan-approved", 3, True),
    ("application-and-derating-assessment", 3, True),
    ("radiation-environment-suitability", 3, True),
    ("procurement-specification-issued", 2, True),
    ("manufacturer-source-acceptability", 2, True),
    ("declared-components-list-entry", 2, True),
    ("package-and-mounting-compatibility", 2, False),
    ("obsolescence-and-availability-check", 1, False),
    ("lead-time-and-delivery-plan", 1, False),
    ("prior-use-heritage-evidence", 1, False),
)

PREREQUISITE_NAMES = tuple(name for name, _weight, _blocking in PREREQUISITES)

_WEIGHT = {name: weight for name, weight, _blocking in PREREQUISITES}
_BLOCKING = {name: blocking for name, _weight, blocking in PREREQUISITES}
_ORDER = {name: position for position, name in enumerate(PREREQUISITE_NAMES)}

SELECTION_STATES = ("closed", "open", "not-applicable")

# The readiness index is a ratio of summed weights. An exactly-met level can
# land a few units in the last place low; absorb that here, not by moving it.
READINESS_TOLERANCE = 1e-9

_SEVERITY = {
    "waiver-on-blocking-prerequisite": 0,
    "blocking-prerequisite-open": 1,
    "prerequisite-not-declared": 2,
    "not-applicable-without-justification": 3,
    "waiver-without-rationale": 4,
    "prerequisite-open": 5,
    "closed-under-waiver": 6,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _has_text(value):
    """Return True when a value is a string carrying something."""
    return isinstance(value, str) and bool(value.strip())


def validate_candidate_id(value):
    """Return the validated identifier of the candidate part."""
    return _require_text(value, "part_id")


def prerequisite_weight(name):
    """Return the weight of one named selection prerequisite."""
    text = _require_text(name, "prerequisite name").lower()
    if text not in _WEIGHT:
        raise ValueError(
            "unknown prerequisite %r; known: %s"
            % (name, ", ".join(PREREQUISITE_NAMES))
        )
    return _WEIGHT[text]


def prerequisite_is_blocking(name):
    """Return True when a prerequisite stops a procurement decision outright."""
    text = _require_text(name, "prerequisite name").lower()
    if text not in _BLOCKING:
        raise ValueError(
            "unknown prerequisite %r; known: %s"
            % (name, ", ".join(PREREQUISITE_NAMES))
        )
    return _BLOCKING[text]


def normalise_state(value):
    """Return the lower-cased declared state of one prerequisite."""
    state = _require_text(value, "state").lower()
    if state not in SELECTION_STATES:
        raise ValueError(
            "unknown state %r; known: %s" % (value, ", ".join(SELECTION_STATES))
        )
    return state


def declare_prerequisite(name, entry):
    """Return the resolved ledger record of one selection prerequisite.

    entry is the project's declaration: a state, an optional justification for
    a not-applicable declaration, and an optional waiver mapping. A missing
    entry is an open prerequisite, never an absent one.
    """
    weight = prerequisite_weight(name)
    blocking = prerequisite_is_blocking(name)
    canonical = _require_text(name, "prerequisite name").lower()
    record = {
        "prerequisite": canonical,
        "weight": weight,
        "blocking": blocking,
        "declared_state": None,
        "applies": True,
        "satisfied": False,
        "disposition": "prerequisite-not-declared",
    }
    if entry is None:
        return record
    if not isinstance(entry, dict):
        raise ValueError("the declaration of %s must be a mapping" % canonical)
    if "state" not in entry or entry["state"] is None:
        return record

    state = normalise_state(entry["state"])
    record["declared_state"] = state

    waiver = entry.get("waiver")
    if waiver is not None and not isinstance(waiver, dict):
        raise ValueError("the waiver on %s must be a mapping" % canonical)
    waived = bool(waiver and waiver.get("granted") is True)

    if state == "not-applicable":
        if _has_text(entry.get("justification")):
            record["applies"] = False
            record["satisfied"] = False
            record["disposition"] = "not-applicable-justified"
        else:
            record["disposition"] = "not-applicable-without-justification"
        return record

    if state == "closed":
        record["satisfied"] = True
        record["disposition"] = "closed"
        return record

    if waived:
        if blocking:
            record["disposition"] = "waiver-on-blocking-prerequisite"
            return record
        if not _has_text(waiver.get("rationale")):
            record["disposition"] = "waiver-without-rationale"
            return record
        record["satisfied"] = True
        record["disposition"] = "closed-under-waiver"
        return record

    record["disposition"] = (
        "blocking-prerequisite-open" if blocking else "prerequisite-open"
    )
    return record


def readiness_index(records):
    """Return the weighted share of the applicable prerequisites satisfied."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of ledger records")
    applicable = 0
    satisfied = 0
    for record in records:
        if not isinstance(record, dict) or "applies" not in record:
            raise ValueError("each record must carry 'applies'")
        if not record["applies"]:
            continue
        applicable += record["weight"]
        if record["satisfied"]:
            satisfied += record["weight"]
    if applicable == 0:
        raise ValueError(
            "every prerequisite was declared not applicable; nothing is left to read"
        )
    return satisfied / applicable


def blocking_open(records):
    """Return the blocking prerequisites still standing in the way."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of ledger records")
    return tuple(
        record["prerequisite"]
        for record in records
        if record["blocking"] and record["applies"] and not record["satisfied"]
    )


def next_prerequisite_to_close(records):
    """Return the prerequisite worth closing next, or None when none is left.

    Blocking items come first, then the heaviest, then the ledger order, so
    the answer is stable and points at the item that unblocks the most.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of ledger records")
    open_records = [
        record
        for record in records
        if record["applies"] and not record["satisfied"]
    ]
    if not open_records:
        return None
    best = min(
        open_records,
        key=lambda record: (
            0 if record["blocking"] else 1,
            -record["weight"],
            _ORDER[record["prerequisite"]],
        ),
    )
    return best["prerequisite"]


def assess_class_3_selection_readiness(spec):
    """Run the full clause 6.2.1 pre-procurement selection assessment.

    spec keys: candidate (mapping carrying part_id), prerequisites (mapping of
    prerequisite name -> declaration), optional required_readiness (default
    1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("candidate", "prerequisites"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    candidate = spec["candidate"]
    if not isinstance(candidate, dict):
        raise ValueError("spec['candidate'] must be a mapping")
    part_id = validate_candidate_id(candidate.get("part_id"))

    declarations = spec["prerequisites"]
    if not isinstance(declarations, dict):
        raise ValueError("spec['prerequisites'] must be a mapping")
    for name in declarations:
        text = _require_text(name, "prerequisite name").lower()
        if text not in _WEIGHT:
            raise ValueError(
                "unknown prerequisite %r; known: %s"
                % (name, ", ".join(PREREQUISITE_NAMES))
            )

    normalised = {
        _require_text(name, "prerequisite name").lower(): entry
        for name, entry in declarations.items()
    }

    required = spec.get("required_readiness", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_readiness must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_readiness must lie in [0, 1], got %r"
            % (spec["required_readiness"],)
        )

    records = [
        declare_prerequisite(name, normalised.get(name)) for name in PREREQUISITE_NAMES
    ]

    index = readiness_index(records)
    blockers = blocking_open(records)
    nxt = next_prerequisite_to_close(records)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition in ("closed", "not-applicable-justified"):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 5),
                "reference": record["prerequisite"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = index > required or math.isclose(
        index, required, rel_tol=0.0, abs_tol=READINESS_TOLERANCE
    )
    ready = meets and not blockers
    return {
        "part_id": part_id,
        "records": records,
        "readiness_index": index,
        "required_readiness": required,
        "blocking_open": blockers,
        "next_to_close": nxt,
        "findings": findings,
        "ready_for_procurement": ready,
        "verdict": "proceed-to-procurement" if ready else "hold",
    }


def _finding_detail(record):
    """Return the reason one prerequisite is not cleanly closed."""
    disposition = record["disposition"]
    if disposition == "prerequisite-not-declared":
        return "nobody declared this prerequisite, so it stands open"
    if disposition == "not-applicable-without-justification":
        return "declared not applicable with no justification on record"
    if disposition == "waiver-on-blocking-prerequisite":
        return "a waiver was raised against a prerequisite that cannot be waived"
    if disposition == "waiver-without-rationale":
        return "the waiver carries no rationale, so it closes nothing"
    if disposition == "blocking-prerequisite-open":
        return "this prerequisite stops the procurement decision while it is open"
    if disposition == "closed-under-waiver":
        return "closed on a waiver rather than on evidence; carried as a residual"
    return "still open and costs the project later if it is left"

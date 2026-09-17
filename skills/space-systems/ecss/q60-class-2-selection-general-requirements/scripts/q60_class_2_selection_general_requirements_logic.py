"""Overarching expectations governing Class 2 part selection before procurement.

Anchor: ECSS-Q-ST-60C clause 5.2.1 (general requirements a Class 2 programme
meets before a part selection is taken to a procurement decision). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the weight table the project grades its selection prerequisites on.
2. Take a declaration for every prerequisite - satisfied, open, tailored, or not
   applicable - and refuse a state the clause does not admit: a blocking
   prerequisite cannot be tailored and cannot be declared inapplicable, and
   neither tailoring nor inapplicability stands without the record that
   justifies it.
3. Weight the prerequisites still in force and compute the readiness index over
   them, crediting a tailored prerequisite partially rather than fully, so the
   Class 2 relief shows up as the partial ground it is.
4. Name the blocking prerequisites still open. Any one of them stops the
   decision whatever the index reads.
5. Compare the index with the threshold, absorbing representation error with a
   named tolerance rather than by lowering the threshold, and return the
   verdict, the tailoring on the record, and the single prerequisite worth
   closing next.
"""

import math

__all__ = [
    "INDEX_TOLERANCE",
    "PREREQUISITE_WEIGHTS",
    "BLOCKING_PREREQUISITES",
    "DECLARATION_STATES",
    "TAILORING_CREDIT",
    "READINESS_THRESHOLD",
    "validate_weight_table",
    "validate_state",
    "normalize_declarations",
    "prerequisite_credit",
    "readiness_index",
    "open_blocking_prerequisites",
    "next_prerequisite_to_close",
    "assess_class_2_selection_readiness",
]

# The index is a quotient of two weight sums and the threshold is a decimal
# literal; an index built to land exactly on the threshold can sit a few units
# in the last place below it. Absorb that here, never by moving the threshold.
INDEX_TOLERANCE = 1e-9

# The ground a Class 2 selection stands on, and what each part of it is worth.
# Weights are not costs and they are not opinions about importance in the
# abstract: they are how much of the decision each prerequisite carries.
PREREQUISITE_WEIGHTS = {
    "mission-environment-defined": 3.0,
    "component-requirements-specified": 3.0,
    "component-control-plan-approved": 3.0,
    "declared-components-list-entry": 3.0,
    "quality-level-target-agreed": 2.0,
    "radiation-environment-assessed": 2.0,
    "derating-rules-agreed": 2.0,
    "obsolescence-and-lead-time-assessed": 1.0,
    "procurement-source-identified": 1.0,
}

# The prerequisites a Class 2 selection cannot proceed without. The Class 2 set
# is narrower than a Class 1 one; what is in it is not negotiable.
BLOCKING_PREREQUISITES = frozenset(
    (
        "mission-environment-defined",
        "component-requirements-specified",
        "component-control-plan-approved",
    )
)

DECLARATION_STATES = ("satisfied", "open", "tailored", "not-applicable")

# What a tailored prerequisite is worth against one met in full. Tailoring is
# partial ground, so it earns partial credit and stays in the denominator.
TAILORING_CREDIT = 0.5

# The share of the weighted ground that has to be in place before a Class 2
# selection may be taken to a procurement decision.
READINESS_THRESHOLD = 0.80

_CREDIT = {
    "satisfied": 1.0,
    "tailored": TAILORING_CREDIT,
    "open": 0.0,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _recorded(value):
    """Return whether a free-text record actually says something."""
    return isinstance(value, str) and bool(value.strip())


def validate_weight_table(weights):
    """Return the validated prerequisite weight table."""
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping of prerequisite -> weight")
    validated = {}
    for raw_name, weight in weights.items():
        name = _require_text(raw_name, "prerequisite name").lower()
        if name in validated:
            raise ValueError("prerequisite %s is weighted twice" % name)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("weight for %s must be a real number, got %r" % (name, weight))
        weight = float(weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("weight for %s must be finite and strictly positive" % name)
        validated[name] = weight
    for blocking in BLOCKING_PREREQUISITES:
        if blocking not in validated:
            raise ValueError(
                "weight table omits the blocking prerequisite %s" % blocking
            )
    return validated


def validate_state(value):
    """Return the validated declaration state of one prerequisite."""
    state = _require_text(value, "declaration state").lower()
    if state not in DECLARATION_STATES:
        raise ValueError(
            "unknown declaration state %r; known: %s"
            % (value, ", ".join(DECLARATION_STATES))
        )
    return state


def normalize_declarations(declarations, weights=None):
    """Return prerequisite -> normalized declaration, refusing a state not admitted.

    A declaration is either the state as a bare string, or a mapping carrying the
    state plus the record that justifies it.
    """
    table = validate_weight_table(PREREQUISITE_WEIGHTS if weights is None else weights)
    if not isinstance(declarations, dict) or not declarations:
        raise ValueError("declarations must be a non-empty mapping")

    normalized = {}
    for raw_name, raw in declarations.items():
        name = _require_text(raw_name, "prerequisite name").lower()
        if name not in table:
            raise ValueError(
                "declaration names %s, which is not a weighted prerequisite" % name
            )
        if name in normalized:
            raise ValueError("prerequisite %s is declared twice" % name)
        if isinstance(raw, str):
            entry = {"state": validate_state(raw)}
        elif isinstance(raw, dict):
            if "state" not in raw:
                raise ValueError("declaration for %s does not carry a state" % name)
            entry = {"state": validate_state(raw["state"])}
            for key in ("rationale", "approval_reference", "justification"):
                if key in raw and raw[key] is not None:
                    entry[key] = raw[key]
        else:
            raise ValueError(
                "declaration for %s must be a state string or a mapping" % name
            )

        state = entry["state"]
        if state == "tailored":
            if name in BLOCKING_PREREQUISITES:
                raise ValueError(
                    "%s is a blocking prerequisite and cannot be tailored" % name
                )
            if not _recorded(entry.get("rationale")):
                raise ValueError("tailoring of %s carries no rationale" % name)
            if not _recorded(entry.get("approval_reference")):
                raise ValueError("tailoring of %s carries no approval reference" % name)
        if state == "not-applicable":
            if name in BLOCKING_PREREQUISITES:
                raise ValueError(
                    "%s is a blocking prerequisite and always applies" % name
                )
            if not _recorded(entry.get("justification")):
                raise ValueError("%s is declared inapplicable with no justification" % name)
        normalized[name] = entry

    undeclared = sorted(set(table) - set(normalized))
    if undeclared:
        raise ValueError(
            "no declaration for %s; silence is not a state" % ", ".join(undeclared)
        )
    return normalized


def prerequisite_credit(state):
    """Return what one declaration state is worth against a fully met one."""
    validated = validate_state(state)
    if validated == "not-applicable":
        return None
    return _CREDIT[validated]


def readiness_index(normalized, weights=None):
    """Return (index, in_force_weight, credited_weight) over prerequisites in force."""
    table = validate_weight_table(PREREQUISITE_WEIGHTS if weights is None else weights)
    if not isinstance(normalized, dict) or not normalized:
        raise ValueError("normalized declarations must be a non-empty mapping")
    in_force = 0.0
    credited = 0.0
    for name, entry in normalized.items():
        if name not in table:
            raise ValueError("declaration names an unweighted prerequisite %s" % name)
        credit = prerequisite_credit(entry["state"])
        if credit is None:
            continue
        in_force += table[name]
        credited += table[name] * credit
    if in_force <= 0.0:
        raise ValueError("every prerequisite was declared inapplicable; nothing is in force")
    return (credited / in_force, in_force, credited)


def open_blocking_prerequisites(normalized):
    """Return the blocking prerequisites still open, worst-carrying first by name."""
    if not isinstance(normalized, dict):
        raise ValueError("normalized declarations must be a mapping")
    return tuple(
        sorted(
            name
            for name, entry in normalized.items()
            if name in BLOCKING_PREREQUISITES and entry["state"] == "open"
        )
    )


def next_prerequisite_to_close(normalized, weights=None):
    """Return the single open prerequisite worth closing next, blocking first."""
    table = validate_weight_table(PREREQUISITE_WEIGHTS if weights is None else weights)
    if not isinstance(normalized, dict):
        raise ValueError("normalized declarations must be a mapping")
    candidates = [
        name for name, entry in normalized.items() if entry["state"] == "open"
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda name: (
            0 if name in BLOCKING_PREREQUISITES else 1,
            -table[name],
            name,
        ),
    )


def assess_class_2_selection_readiness(spec):
    """Run the full clause 5.2.1 Class 2 selection readiness assessment.

    spec keys: declarations (prerequisite -> state or mapping), optional
    candidate_part, optional weights, optional readiness_threshold.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "declarations" not in spec:
        raise ValueError("spec missing required key 'declarations'")
    weights = validate_weight_table(spec.get("weights", PREREQUISITE_WEIGHTS))
    normalized = normalize_declarations(spec["declarations"], weights)

    threshold = spec.get("readiness_threshold", READINESS_THRESHOLD)
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("readiness_threshold must be a real number")
    threshold = float(threshold)
    if not math.isfinite(threshold) or threshold < 0.0 or threshold > 1.0:
        raise ValueError(
            "readiness_threshold must lie in [0, 1], got %r"
            % (spec["readiness_threshold"],)
        )

    candidate = spec.get("candidate_part")
    candidate = _require_text(candidate, "candidate_part") if candidate is not None else None

    index, in_force, credited = readiness_index(normalized, weights)
    blocking_open = open_blocking_prerequisites(normalized)
    tailored = tuple(
        sorted(n for n, e in normalized.items() if e["state"] == "tailored")
    )
    inapplicable = tuple(
        sorted(n for n, e in normalized.items() if e["state"] == "not-applicable")
    )
    still_open = tuple(sorted(n for n, e in normalized.items() if e["state"] == "open"))

    meets = index > threshold or math.isclose(
        index, threshold, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )
    if blocking_open:
        verdict = "blocked"
    elif not meets:
        verdict = "hold"
    elif tailored:
        verdict = "authorize-with-tailoring"
    else:
        verdict = "authorize"

    return {
        "candidate_part": candidate,
        "declarations": normalized,
        "readiness_index": index,
        "in_force_weight": in_force,
        "credited_weight": credited,
        "readiness_threshold": threshold,
        "meets_threshold": meets,
        "blocking_open": blocking_open,
        "open_prerequisites": still_open,
        "tailored_prerequisites": tailored,
        "not_applicable_prerequisites": inapplicable,
        "next_to_close": next_prerequisite_to_close(normalized, weights),
        "authorized": verdict in ("authorize", "authorize-with-tailoring"),
        "verdict": verdict,
    }

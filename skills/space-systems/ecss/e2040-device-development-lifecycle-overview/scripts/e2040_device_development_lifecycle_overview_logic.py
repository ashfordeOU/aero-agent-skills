"""Device need derivation across the development phases.

Anchor: ECSS-E-ST-20-40C clause 4.1 (how a device supplier derives its
functional, performance and environmental needs across the development
phases). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Fold the phase and need-category spellings a supplier actually writes onto
   a canonical ordered set, refusing an unrecognised one rather than guessing.
2. Index the declared needs, refusing a repeated identifier, and walk each
   need back to the higher-level need it was derived from so an orphan or a
   circular derivation is found rather than inherited.
3. Check the derivation order in time: a need cannot be derived in a phase
   earlier than the need it came from.
4. Track maturity per category across the phase order and report a category
   that goes backwards, or that has not reached the maturity a phase gate
   asks of it.
5. Report the categories the supplier never addressed at all, because the
   three the clause names are the floor, not a menu.
"""

__all__ = [
    "PHASE_SEQUENCE",
    "PHASE_ALIASES",
    "NEED_CATEGORIES",
    "MANDATORY_CATEGORIES",
    "CATEGORY_ALIASES",
    "MATURITY_LEVELS",
    "normalize_phase",
    "phase_index",
    "normalize_category",
    "normalize_maturity",
    "maturity_index",
    "validate_need",
    "build_need_index",
    "derivation_chain",
    "needs_by_phase",
    "needs_by_category",
    "category_coverage",
    "maturity_by_phase",
    "assess_lifecycle_derivation",
]

# The project phases a device development runs through, in order.
PHASE_SEQUENCE = (
    "phase-0",
    "phase-a",
    "phase-b",
    "phase-c",
    "phase-d",
    "phase-e",
)

PHASE_ALIASES = {
    "0": "phase-0",
    "phase 0": "phase-0",
    "mission-analysis": "phase-0",
    "a": "phase-a",
    "phase a": "phase-a",
    "feasibility": "phase-a",
    "b": "phase-b",
    "phase b": "phase-b",
    "preliminary-definition": "phase-b",
    "c": "phase-c",
    "phase c": "phase-c",
    "detailed-definition": "phase-c",
    "d": "phase-d",
    "phase d": "phase-d",
    "qualification-production": "phase-d",
    "e": "phase-e",
    "phase e": "phase-e",
    "utilisation": "phase-e",
}

# The need categories the clause puts on a device supplier. The first three
# are the ones it names outright; the rest are common additions.
MANDATORY_CATEGORIES = ("functional", "performance", "environmental")

NEED_CATEGORIES = MANDATORY_CATEGORIES + ("interface", "operational", "reliability")

CATEGORY_ALIASES = {
    "function": "functional",
    "functions": "functional",
    "perf": "performance",
    "performances": "performance",
    "environment": "environmental",
    "environments": "environmental",
    "env": "environmental",
    "interfaces": "interface",
    "operations": "operational",
    "operability": "operational",
    "dependability": "reliability",
}

# How firm a need is, from a statement of intent to a demonstrated property.
MATURITY_LEVELS = ("stated", "derived", "budgeted", "specified", "verified")


def _clean_token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-")


def normalize_phase(value):
    """Fold a phase spelling onto the canonical phase token."""
    token = _clean_token(value, "phase")
    spaced = token.replace("-", " ")
    if token in PHASE_SEQUENCE:
        return token
    if token in PHASE_ALIASES:
        return PHASE_ALIASES[token]
    if spaced in PHASE_ALIASES:
        return PHASE_ALIASES[spaced]
    raise ValueError("unrecognised development phase %r" % (value,))


def phase_index(value):
    """Return the position of a phase in the development order."""
    return PHASE_SEQUENCE.index(normalize_phase(value))


def normalize_category(value):
    """Fold a need-category spelling onto the canonical category token."""
    token = _clean_token(value, "need category")
    if token in NEED_CATEGORIES:
        return token
    if token in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[token]
    raise ValueError("unrecognised need category %r" % (value,))


def normalize_maturity(value):
    """Fold a maturity spelling onto the canonical maturity token."""
    token = _clean_token(value, "maturity")
    if token in MATURITY_LEVELS:
        return token
    raise ValueError("unrecognised need maturity %r" % (value,))


def maturity_index(value):
    """Return the position of a maturity level in the firmness order."""
    return MATURITY_LEVELS.index(normalize_maturity(value))


def validate_need(need):
    """Return one need folded onto canonical tokens."""
    if not isinstance(need, dict):
        raise ValueError("each need must be a mapping")
    for key in ("id", "category", "phase", "maturity"):
        if key not in need:
            raise ValueError("need missing required key '%s'" % key)
    identifier = need["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("need id must be a non-empty string, got %r" % (identifier,))
    parent = need.get("parent")
    if parent is not None:
        if not isinstance(parent, str) or not parent.strip():
            raise ValueError("parent of %s must be a non-empty string or None" % identifier)
        parent = parent.strip()
        if parent == identifier.strip():
            raise ValueError("need %s is its own parent" % identifier)
    return {
        "id": identifier.strip(),
        "category": normalize_category(need["category"]),
        "phase": normalize_phase(need["phase"]),
        "maturity": normalize_maturity(need["maturity"]),
        "parent": parent,
        "title": need.get("title", ""),
    }


def build_need_index(needs):
    """Return {id: need} for the declared needs, refusing a repeated id."""
    if isinstance(needs, dict) or not isinstance(needs, (list, tuple)):
        raise ValueError("needs must be a sequence of need mappings")
    index = {}
    for raw in needs:
        need = validate_need(raw)
        if need["id"] in index:
            raise ValueError("need identifier %r declared twice" % need["id"])
        index[need["id"]] = need
    return index


def derivation_chain(index, need_id):
    """Return the chain from a need up to its root need."""
    if not isinstance(index, dict):
        raise ValueError("index must be the mapping returned by build_need_index")
    if need_id not in index:
        raise ValueError("no need with identifier %r" % (need_id,))
    chain = []
    seen = set()
    current = need_id
    while current is not None:
        if current in seen:
            raise ValueError("derivation of %r is circular at %r" % (need_id, current))
        seen.add(current)
        if current not in index:
            raise ValueError(
                "need %r derives from %r, which is not a declared need"
                % (chain[-1]["id"], current)
            )
        node = index[current]
        chain.append(node)
        current = node["parent"]
    return chain


def needs_by_phase(index):
    """Group the need identifiers by the phase they were derived in."""
    grouped = {phase: [] for phase in PHASE_SEQUENCE}
    for need in index.values():
        grouped[need["phase"]].append(need["id"])
    for phase in grouped:
        grouped[phase].sort()
    return grouped


def needs_by_category(index):
    """Group the need identifiers by need category."""
    grouped = {}
    for need in index.values():
        grouped.setdefault(need["category"], []).append(need["id"])
    for category in grouped:
        grouped[category].sort()
    return grouped


def category_coverage(index):
    """Return the mandatory categories present and the ones never addressed."""
    present = {need["category"] for need in index.values()}
    missing = [c for c in MANDATORY_CATEGORIES if c not in present]
    return {
        "present": sorted(present),
        "missing_mandatory": missing,
        "complete": not missing,
    }


def maturity_by_phase(index):
    """Return the highest maturity reached per category at each phase."""
    table = {}
    for need in index.values():
        category = need["category"]
        row = table.setdefault(category, {})
        level = maturity_index(need["maturity"])
        phase = need["phase"]
        if phase not in row or level > row[phase]:
            row[phase] = level
    return table


def assess_lifecycle_derivation(spec):
    """Run the full clause 4.1 need-derivation assessment.

    spec keys: needs (sequence of need mappings), optional
    required_maturity_at_phase (mapping phase -> maturity token).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "needs" not in spec:
        raise ValueError("spec missing required key 'needs'")
    index = build_need_index(spec["needs"])
    if not index:
        raise ValueError("at least one need is required to assess a derivation")

    findings = []

    orphans = []
    for need in index.values():
        parent = need["parent"]
        if parent is not None and parent not in index:
            orphans.append(need["id"])
    orphans.sort()
    for identifier in orphans:
        findings.append(
            "need %s derives from %r, which is not a declared need"
            % (identifier, index[identifier]["parent"])
        )

    early = []
    for need in index.values():
        parent = need["parent"]
        if parent is None or parent not in index:
            continue
        if PHASE_SEQUENCE.index(need["phase"]) < PHASE_SEQUENCE.index(index[parent]["phase"]):
            early.append(need["id"])
    early.sort()
    for identifier in early:
        findings.append(
            "need %s is derived in %s, before its parent %s in %s"
            % (
                identifier,
                index[identifier]["phase"],
                index[identifier]["parent"],
                index[index[identifier]["parent"]]["phase"],
            )
        )

    cycles = []
    for identifier in sorted(index):
        try:
            derivation_chain(index, identifier)
        except ValueError as exc:
            if "circular" in str(exc):
                cycles.append(identifier)
    for identifier in cycles:
        findings.append("derivation of need %s is circular" % identifier)

    coverage = category_coverage(index)
    for category in coverage["missing_mandatory"]:
        findings.append("no %s need was derived at any phase" % category)

    table = maturity_by_phase(index)
    regressions = []
    for category in sorted(table):
        row = table[category]
        best = -1
        for phase in PHASE_SEQUENCE:
            if phase not in row:
                continue
            if row[phase] < best:
                regressions.append((category, phase))
                findings.append(
                    "%s needs are less mature in %s than in an earlier phase"
                    % (category, phase)
                )
            else:
                best = row[phase]

    gate_shortfalls = []
    required = spec.get("required_maturity_at_phase") or {}
    if not isinstance(required, dict):
        raise ValueError("required_maturity_at_phase must be a mapping")
    for raw_phase, raw_level in required.items():
        phase = normalize_phase(raw_phase)
        wanted = maturity_index(raw_level)
        limit = PHASE_SEQUENCE.index(phase)
        for category in MANDATORY_CATEGORIES:
            row = table.get(category, {})
            reached = -1
            for candidate in PHASE_SEQUENCE[: limit + 1]:
                if candidate in row and row[candidate] > reached:
                    reached = row[candidate]
            if reached < wanted:
                gate_shortfalls.append((phase, category))
                findings.append(
                    "%s needs have not reached %s maturity by %s"
                    % (category, MATURITY_LEVELS[wanted], phase)
                )

    return {
        "needs": index,
        "by_phase": needs_by_phase(index),
        "by_category": needs_by_category(index),
        "coverage": coverage,
        "maturity_table": table,
        "orphans": orphans,
        "derived_before_parent": early,
        "circular": cycles,
        "maturity_regressions": regressions,
        "gate_shortfalls": gate_shortfalls,
        "findings": findings,
        "compliant": not findings,
    }

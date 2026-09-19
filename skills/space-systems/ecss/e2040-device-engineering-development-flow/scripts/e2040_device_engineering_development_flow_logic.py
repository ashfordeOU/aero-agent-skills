"""Device engineering development flow: phases, milestones and activities.

Anchor: ECSS-E-ST-20-40C clause 5.1.3 (the phase sequence and milestone
mapping used to structure device engineering work). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Fold the milestone spellings a programme uses onto the canonical review
   sequence and map each review onto the project phase it closes.
2. Check the declared flow is a subsequence of that order: milestones may be
   left out of a small development, but never reordered or repeated.
3. Attach each engineering activity to the milestone that closes it, and
   refuse an activity attached to a milestone the flow does not hold.
4. Walk the activity dependencies: an activity cannot be gated by a milestone
   earlier than one it depends on, and a dependency loop is refused rather
   than silently ordered.
5. Report the milestones the flow declares that nothing closes, and compute
   the longest dependency chain so the flow's real length is visible rather
   than the milestone count.
"""

__all__ = [
    "MILESTONE_SEQUENCE",
    "MILESTONE_ALIASES",
    "MILESTONE_PHASE",
    "PHASE_SEQUENCE",
    "normalize_milestone",
    "milestone_index",
    "milestone_phase",
    "validate_flow",
    "validate_activity",
    "build_activity_index",
    "activities_by_milestone",
    "milestones_without_closure",
    "dependency_violations",
    "longest_dependency_chain",
    "assess_development_flow",
]

# The review sequence a device engineering development is structured around.
MILESTONE_SEQUENCE = ("prr", "srr", "pdr", "cdr", "qr", "ar")

MILESTONE_ALIASES = {
    "preliminary-requirements-review": "prr",
    "requirements-review": "prr",
    "system-requirements-review": "srr",
    "device-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
    "delivery-review": "ar",
}

# The project phase each review closes.
MILESTONE_PHASE = {
    "prr": "phase-a",
    "srr": "phase-b",
    "pdr": "phase-b",
    "cdr": "phase-c",
    "qr": "phase-d",
    "ar": "phase-d",
}

PHASE_SEQUENCE = ("phase-a", "phase-b", "phase-c", "phase-d")


def _clean_token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def normalize_milestone(value):
    """Fold a milestone spelling onto a canonical review token."""
    token = _clean_token(value, "milestone")
    if token in MILESTONE_SEQUENCE:
        return token
    if token in MILESTONE_ALIASES:
        return MILESTONE_ALIASES[token]
    raise ValueError("unrecognised development milestone %r" % (value,))


def milestone_index(value):
    """Return the position of a milestone in the canonical review order."""
    return MILESTONE_SEQUENCE.index(normalize_milestone(value))


def milestone_phase(value):
    """Return the project phase a milestone closes."""
    return MILESTONE_PHASE[normalize_milestone(value)]


def validate_flow(sequence):
    """Return the declared milestone flow, refusing a reorder or a repeat."""
    if isinstance(sequence, str) or not isinstance(sequence, (list, tuple)):
        raise ValueError("flow must be a sequence of milestone names")
    if not sequence:
        raise ValueError("a development flow needs at least one milestone")
    flow = []
    last = -1
    for item in sequence:
        token = normalize_milestone(item)
        position = MILESTONE_SEQUENCE.index(token)
        if token in flow:
            raise ValueError("milestone %r appears twice in the flow" % token)
        if position < last:
            raise ValueError(
                "milestone %r is declared after %r, which is out of review order"
                % (token, flow[-1])
            )
        last = position
        flow.append(token)
    return flow


def validate_activity(activity):
    """Return one engineering activity folded onto canonical tokens."""
    if not isinstance(activity, dict):
        raise ValueError("each activity must be a mapping")
    for key in ("id", "closes_at"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    identifier = activity["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("activity id must be a non-empty string, got %r" % (identifier,))
    identifier = identifier.strip()

    raw_depends = activity.get("depends_on") or []
    if isinstance(raw_depends, str) or not isinstance(raw_depends, (list, tuple)):
        raise ValueError("depends_on of %s must be a sequence of activity ids" % identifier)
    depends = []
    for item in raw_depends:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("a dependency of %s has no usable activity id" % identifier)
        token = item.strip()
        if token == identifier:
            raise ValueError("activity %s depends on itself" % identifier)
        if token in depends:
            raise ValueError("activity %s lists dependency %r twice" % (identifier, token))
        depends.append(token)

    return {
        "id": identifier,
        "closes_at": normalize_milestone(activity["closes_at"]),
        "depends_on": depends,
        "title": activity.get("title", ""),
    }


def build_activity_index(activities):
    """Return {id: activity}, refusing a repeated activity identifier."""
    if isinstance(activities, dict) or not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence of activity mappings")
    index = {}
    for raw in activities:
        record = validate_activity(raw)
        if record["id"] in index:
            raise ValueError("activity identifier %r declared twice" % record["id"])
        index[record["id"]] = record
    return index


def activities_by_milestone(index, flow=None):
    """Group the activity identifiers by the milestone that closes them."""
    if not isinstance(index, dict):
        raise ValueError("index must be the mapping returned by build_activity_index")
    keys = list(MILESTONE_SEQUENCE) if flow is None else validate_flow(flow)
    grouped = {milestone: [] for milestone in keys}
    outside = []
    for record in index.values():
        if record["closes_at"] in grouped:
            grouped[record["closes_at"]].append(record["id"])
        else:
            outside.append(record["id"])
    for milestone in grouped:
        grouped[milestone].sort()
    outside.sort()
    return {"grouped": grouped, "outside_the_flow": outside}


def milestones_without_closure(index, flow):
    """Return the declared milestones that no activity closes."""
    grouped = activities_by_milestone(index, flow)["grouped"]
    return [milestone for milestone in validate_flow(flow) if not grouped[milestone]]


def dependency_violations(index):
    """Return activities gated earlier than something they depend on."""
    if not isinstance(index, dict):
        raise ValueError("index must be the mapping returned by build_activity_index")
    violations = []
    unknown = []
    for identifier in sorted(index):
        record = index[identifier]
        own = MILESTONE_SEQUENCE.index(record["closes_at"])
        for dependency in record["depends_on"]:
            if dependency not in index:
                unknown.append({"activity": identifier, "dependency": dependency})
                continue
            other = MILESTONE_SEQUENCE.index(index[dependency]["closes_at"])
            if own < other:
                violations.append(
                    {
                        "activity": identifier,
                        "closes_at": record["closes_at"],
                        "dependency": dependency,
                        "dependency_closes_at": index[dependency]["closes_at"],
                    }
                )
    return {"violations": violations, "unknown_dependencies": unknown}


def longest_dependency_chain(index):
    """Return the longest chain of dependent activities, refusing a loop."""
    if not isinstance(index, dict):
        raise ValueError("index must be the mapping returned by build_activity_index")
    if not index:
        return []
    memo = {}
    visiting = set()

    def walk(identifier):
        if identifier in memo:
            return memo[identifier]
        if identifier in visiting:
            raise ValueError("activity dependencies form a loop at %r" % identifier)
        visiting.add(identifier)
        best = [identifier]
        for dependency in index[identifier]["depends_on"]:
            if dependency not in index:
                continue
            candidate = walk(dependency) + [identifier]
            if len(candidate) > len(best):
                best = candidate
        visiting.discard(identifier)
        memo[identifier] = best
        return best

    longest = []
    for identifier in sorted(index):
        chain = walk(identifier)
        if len(chain) > len(longest):
            longest = chain
    return longest


def assess_development_flow(spec):
    """Run the full clause 5.1.3 development flow assessment.

    spec keys: flow (sequence of milestone names), activities (sequence of
    activity mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("flow", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    flow = validate_flow(spec["flow"])
    index = build_activity_index(spec["activities"])
    if not index:
        raise ValueError("at least one engineering activity is needed")

    grouping = activities_by_milestone(index, flow)
    empty = milestones_without_closure(index, flow)
    dependencies = dependency_violations(index)
    chain = longest_dependency_chain(index)

    findings = []
    skipped = [m for m in MILESTONE_SEQUENCE if m not in flow]
    if skipped:
        findings.append(
            "flow omits %s; each omission is a review the device skips"
            % ", ".join(skipped)
        )
    for identifier in grouping["outside_the_flow"]:
        findings.append(
            "activity %s closes at %s, which the declared flow does not hold"
            % (identifier, index[identifier]["closes_at"])
        )
    for milestone in empty:
        findings.append("milestone %s closes no engineering activity" % milestone)
    for violation in dependencies["violations"]:
        findings.append(
            "activity %s is gated at %s but depends on %s, which only closes at %s"
            % (
                violation["activity"],
                violation["closes_at"],
                violation["dependency"],
                violation["dependency_closes_at"],
            )
        )
    for entry in dependencies["unknown_dependencies"]:
        findings.append(
            "activity %s depends on %s, which is not a declared activity"
            % (entry["activity"], entry["dependency"])
        )

    return {
        "flow": flow,
        "phases": [milestone_phase(m) for m in flow],
        "by_milestone": grouping["grouped"],
        "outside_the_flow": grouping["outside_the_flow"],
        "milestones_without_closure": empty,
        "dependency_violations": dependencies["violations"],
        "unknown_dependencies": dependencies["unknown_dependencies"],
        "longest_chain": chain,
        "longest_chain_length": len(chain),
        "findings": findings,
        "compliant": not findings,
    }

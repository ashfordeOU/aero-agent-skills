"""Tailoring a device requirement set by device type and criticality category.

Anchor: ECSS-E-ST-20-40C clause 5.1.2 (adapting the requirement set to the
device type and its assigned criticality category). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Fold the criticality and device type spellings onto ordered canonical sets
   so two organisations writing the same category the same way are counted
   together, and an unrecognised spelling is refused rather than guessed.
2. Read the baseline: each requirement declares the device types it reaches
   and the least severe criticality at which it still applies, plus whether
   it is one the project may not remove.
3. Derive the tailored set for one device: the requirements whose type reach
   covers it and whose criticality floor its assigned category meets.
4. Check the baseline is monotonic in criticality -- raising a device's
   category may only add requirements, never take one away -- because a
   baseline that is not monotonic makes the category meaningless.
5. Overlay the project delta and report each addition, each removal, each
   removal with no justification, and each removal of a requirement the
   baseline marks non-removable.
"""

__all__ = [
    "CRITICALITY_ORDER",
    "CRITICALITY_ALIASES",
    "DEVICE_TYPES",
    "DEVICE_TYPE_ALIASES",
    "normalize_criticality",
    "criticality_rank",
    "normalize_device_type",
    "validate_requirement",
    "build_baseline",
    "applies_to_device",
    "tailor_requirement_set",
    "check_criticality_monotonic",
    "apply_project_delta",
    "assess_tailoring",
]

# Criticality categories from least to most severe consequence.
CRITICALITY_ORDER = ("minor", "major", "critical", "catastrophic")

CRITICALITY_ALIASES = {
    "4": "minor",
    "iv": "minor",
    "negligible": "minor",
    "3": "major",
    "iii": "major",
    "marginal": "major",
    "2": "critical",
    "ii": "critical",
    "1": "catastrophic",
    "i": "catastrophic",
}

# The kinds of device a requirement set is tailored for.
DEVICE_TYPES = (
    "asic",
    "fpga",
    "hybrid",
    "multi-chip-module",
    "board-level-device",
)

DEVICE_TYPE_ALIASES = {
    "application-specific-integrated-circuit": "asic",
    "mixed-signal-asic": "asic",
    "digital-asic": "asic",
    "field-programmable-gate-array": "fpga",
    "programmable-logic": "fpga",
    "hybrid-microcircuit": "hybrid",
    "thick-film-hybrid": "hybrid",
    "mcm": "multi-chip-module",
    "board": "board-level-device",
    "printed-circuit-board-assembly": "board-level-device",
}

_ALL_TYPES_TOKEN = "all"


def _clean_token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def normalize_criticality(value):
    """Fold a criticality spelling onto a canonical category."""
    token = _clean_token(value, "criticality category")
    if token in CRITICALITY_ORDER:
        return token
    if token in CRITICALITY_ALIASES:
        return CRITICALITY_ALIASES[token]
    raise ValueError("unrecognised criticality category %r" % (value,))


def criticality_rank(value):
    """Return the severity rank of a criticality category, least severe first."""
    return CRITICALITY_ORDER.index(normalize_criticality(value))


def normalize_device_type(value):
    """Fold a device type spelling onto a canonical device type."""
    token = _clean_token(value, "device type")
    if token in DEVICE_TYPES:
        return token
    if token in DEVICE_TYPE_ALIASES:
        return DEVICE_TYPE_ALIASES[token]
    raise ValueError("unrecognised device type %r" % (value,))


def validate_requirement(requirement):
    """Return one baseline requirement folded onto canonical tokens."""
    if not isinstance(requirement, dict):
        raise ValueError("each baseline requirement must be a mapping")
    for key in ("id", "applies_to_types", "minimum_criticality"):
        if key not in requirement:
            raise ValueError("baseline requirement missing required key '%s'" % key)
    identifier = requirement["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("requirement id must be a non-empty string, got %r" % (identifier,))
    identifier = identifier.strip()

    raw_types = requirement["applies_to_types"]
    if isinstance(raw_types, str):
        if _clean_token(raw_types, "applies_to_types") != _ALL_TYPES_TOKEN:
            raise ValueError(
                "applies_to_types of %s must be 'all' or a sequence of device types"
                % identifier
            )
        types = _ALL_TYPES_TOKEN
    else:
        if not isinstance(raw_types, (list, tuple)) or not raw_types:
            raise ValueError(
                "applies_to_types of %s must be 'all' or a non-empty sequence"
                % identifier
            )
        folded = []
        for item in raw_types:
            token = normalize_device_type(item)
            if token in folded:
                raise ValueError(
                    "device type %r listed twice for requirement %s" % (token, identifier)
                )
            folded.append(token)
        types = tuple(sorted(folded))

    removable = requirement.get("removable", True)
    if not isinstance(removable, bool):
        raise ValueError("removable of %s must be a boolean" % identifier)

    return {
        "id": identifier,
        "applies_to_types": types,
        "minimum_criticality": normalize_criticality(requirement["minimum_criticality"]),
        "removable": removable,
        "title": requirement.get("title", ""),
    }


def build_baseline(requirements):
    """Return {id: requirement} for the baseline, refusing a repeated id."""
    if isinstance(requirements, dict) or not isinstance(requirements, (list, tuple)):
        raise ValueError("baseline must be a sequence of requirement mappings")
    if not requirements:
        raise ValueError("baseline must hold at least one requirement")
    baseline = {}
    for raw in requirements:
        record = validate_requirement(raw)
        if record["id"] in baseline:
            raise ValueError("baseline requirement %r declared twice" % record["id"])
        baseline[record["id"]] = record
    return baseline


def applies_to_device(requirement, device_type, criticality):
    """Decide whether one baseline requirement reaches this device."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    canonical = {"id", "applies_to_types", "minimum_criticality", "removable"}
    record = requirement if canonical <= set(requirement) else validate_requirement(requirement)
    wanted_type = normalize_device_type(device_type)
    rank = criticality_rank(criticality)
    types = record["applies_to_types"]
    if types != _ALL_TYPES_TOKEN and wanted_type not in types:
        return False
    return rank >= CRITICALITY_ORDER.index(record["minimum_criticality"])


def tailor_requirement_set(baseline, device_type, criticality):
    """Return the sorted requirement ids that apply to this device."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be the mapping returned by build_baseline")
    return sorted(
        identifier
        for identifier, record in baseline.items()
        if applies_to_device(record, device_type, criticality)
    )


def check_criticality_monotonic(baseline, device_type):
    """Check that raising the criticality never removes a requirement."""
    sets = {}
    for category in CRITICALITY_ORDER:
        sets[category] = set(tailor_requirement_set(baseline, device_type, category))
    violations = []
    for index in range(1, len(CRITICALITY_ORDER)):
        lower = CRITICALITY_ORDER[index - 1]
        higher = CRITICALITY_ORDER[index]
        lost = sorted(sets[lower] - sets[higher])
        if lost:
            violations.append({"from": lower, "to": higher, "lost": lost})
    return {
        "sets": {k: sorted(v) for k, v in sets.items()},
        "violations": violations,
        "monotonic": not violations,
    }


def apply_project_delta(baseline, tailored, delta):
    """Overlay a project delta on a tailored set and report what it changed."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be the mapping returned by build_baseline")
    if not isinstance(tailored, (list, tuple, set)):
        raise ValueError("tailored must be a sequence of requirement ids")
    if delta is None:
        delta = {}
    if not isinstance(delta, dict):
        raise ValueError("delta must be a mapping")

    current = set(tailored)
    added = []
    removed = []
    unjustified = []
    protected = []
    unknown = []

    for entry in delta.get("added", []) or []:
        identifier, reason = _delta_entry(entry, "added")
        if identifier in current:
            raise ValueError(
                "delta adds %r, which the tailored set already holds" % identifier
            )
        if identifier not in baseline:
            unknown.append(identifier)
        current.add(identifier)
        added.append({"id": identifier, "justification": reason})

    for entry in delta.get("removed", []) or []:
        identifier, reason = _delta_entry(entry, "removed")
        if identifier not in current:
            raise ValueError(
                "delta removes %r, which the tailored set does not hold" % identifier
            )
        current.discard(identifier)
        removed.append({"id": identifier, "justification": reason})
        if not reason:
            unjustified.append(identifier)
        if identifier in baseline and not baseline[identifier]["removable"]:
            protected.append(identifier)

    return {
        "tailored": sorted(tailored),
        "final": sorted(current),
        "added": added,
        "removed": removed,
        "removed_without_justification": sorted(unjustified),
        "removed_though_protected": sorted(protected),
        "added_outside_the_baseline": sorted(unknown),
        "reduction": len(removed) - len(added),
    }


def _delta_entry(entry, label):
    """Return (id, justification) from one delta entry."""
    if isinstance(entry, str):
        if not entry.strip():
            raise ValueError("a %s delta entry has a blank requirement id" % label)
        return (entry.strip(), "")
    if isinstance(entry, dict):
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("a %s delta entry has no usable requirement id" % label)
        reason = entry.get("justification", "")
        if reason is None:
            reason = ""
        if not isinstance(reason, str):
            raise ValueError("justification of %s must be a string" % identifier.strip())
        return (identifier.strip(), reason.strip())
    raise ValueError("a %s delta entry must be an id or a mapping" % label)


def assess_tailoring(spec):
    """Run the full clause 5.1.2 tailoring assessment.

    spec keys: baseline (sequence of requirement mappings), device_type,
    criticality, optional delta with 'added' and 'removed' entries.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("baseline", "device_type", "criticality"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    baseline = build_baseline(spec["baseline"])
    device_type = normalize_device_type(spec["device_type"])
    criticality = normalize_criticality(spec["criticality"])
    tailored = tailor_requirement_set(baseline, device_type, criticality)
    monotonic = check_criticality_monotonic(baseline, device_type)
    delta = apply_project_delta(baseline, tailored, spec.get("delta"))

    findings = []
    if not tailored:
        findings.append(
            "no baseline requirement reaches a %s %s device; the type or the "
            "category is wrong, or the baseline does not cover this device"
            % (criticality, device_type)
        )
    for violation in monotonic["violations"]:
        findings.append(
            "baseline is not monotonic: moving from %s to %s drops %s"
            % (violation["from"], violation["to"], ", ".join(violation["lost"]))
        )
    for identifier in delta["removed_without_justification"]:
        findings.append("requirement %s was removed with no justification" % identifier)
    for identifier in delta["removed_though_protected"]:
        findings.append(
            "requirement %s is marked non-removable in the baseline and the "
            "project delta removed it" % identifier
        )
    for identifier in delta["added_outside_the_baseline"]:
        findings.append(
            "requirement %s was added but is not in the baseline, so nothing "
            "records what it is" % identifier
        )

    return {
        "device_type": device_type,
        "criticality": criticality,
        "criticality_rank": criticality_rank(criticality),
        "tailored": tailored,
        "final": delta["final"],
        "delta": delta,
        "monotonic": monotonic,
        "findings": findings,
        "compliant": not findings,
    }

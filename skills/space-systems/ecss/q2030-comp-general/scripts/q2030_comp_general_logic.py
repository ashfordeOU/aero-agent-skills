"""Complementary requirement information and general provisions.

Anchor: ECSS-Q-ST-20-30C sections 7.1 and 7.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

The harness standard builds on an external acceptance basis
(IPC/WHMA-A-620 and its space addendum) and then adds a set of
complementary requirements of its own. Section 7.1 says what those
complementary requirements are for, and section 7.2 fixes how they
sit against the criteria they complement. This module implements that
resolution.

Procedure implemented here:

1. Take the requirement records that bear on one harness build, each
   carrying a topic, the source it comes from, the criterion it states
   and the harness types and assurance levels it applies to.
2. Filter by applicability. A requirement that does not apply to this
   harness type or this assurance level is not in the contest for that
   topic at all, and reporting it as overridden would misread the
   result.
3. Rank the surviving sources. A complementary requirement outranks an
   addendum row, and an addendum row outranks the base external
   criterion. An approved project deviation sits above all three; a
   deviation with no approved waiver reference is demoted out of the
   contest and reported, because an unapproved relaxation is not a
   requirement.
4. Resolve each topic to the highest-ranking applicable source, and
   report a disagreement between two sources at the same rank rather
   than silently picking one.
5. Report the topics left governed by the external basis alone. They
   are legitimate, but they are also where the standard has added
   nothing, and a reviewer usually wants that list.

Stdlib only, offline, deterministic.
"""

SOURCE_PROJECT_DEVIATION = "project-deviation"
SOURCE_ECSS_COMPLEMENTARY = "ecss-complementary"
SOURCE_ECSS_ADDENDUM = "ecss-addendum"
SOURCE_EXTERNAL_BASE = "external-base"

SOURCE_RANK = {
    SOURCE_PROJECT_DEVIATION: 4,
    SOURCE_ECSS_COMPLEMENTARY: 3,
    SOURCE_ECSS_ADDENDUM: 2,
    SOURCE_EXTERNAL_BASE: 1,
}

ECSS_SOURCES = (SOURCE_ECSS_COMPLEMENTARY, SOURCE_ECSS_ADDENDUM)

ANY = "any"

# Findings that stop the requirement set from being usable as it
# stands. A topic left on the external basis alone is reported but does
# not block: the basis is a requirement source in its own right.
BLOCKING_FINDINGS = frozenset(
    (
        "deviation-without-an-approved-waiver",
        "conflicting-sources-at-the-same-precedence-rank",
        "topic-has-no-applicable-requirement",
    )
)


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _scope(label, value):
    if value is None:
        return (ANY,)
    if isinstance(value, str):
        raise ValueError("%s must be a sequence of strings, not a bare string" % label)
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("%s must be a non-empty sequence" % label)
    out = []
    for item in value:
        out.append(_string("%s entry" % label, item))
    return tuple(out)


def validate_harness(harness):
    """Validate the harness the requirement set is resolved against."""
    if not isinstance(harness, dict):
        raise ValueError("harness must be a mapping")
    return {
        "id": _string("harness id", harness.get("id")),
        "harness_type": _string("harness harness_type", harness.get("harness_type")),
        "assurance_level": _string(
            "harness assurance_level", harness.get("assurance_level")
        ),
    }


def validate_requirement(requirement):
    """Validate one requirement record and return a normalized copy."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    topic = _string("requirement topic", requirement.get("topic"))
    source = requirement.get("source")
    if source not in SOURCE_RANK:
        raise ValueError(
            "requirement %s has unknown source %r (expected one of %s)"
            % (topic, source, ", ".join(sorted(SOURCE_RANK)))
        )
    waiver = requirement.get("waiver_reference")
    if waiver is not None:
        waiver = _string("requirement %s waiver_reference" % topic, waiver)
    if waiver is not None and source != SOURCE_PROJECT_DEVIATION:
        raise ValueError(
            "requirement %s carries a waiver reference but is not a project "
            "deviation" % topic
        )
    return {
        "topic": topic,
        "source": source,
        "criterion": _string("requirement %s criterion" % topic, requirement.get("criterion")),
        "applies_to_types": _scope(
            "requirement %s applies_to_types" % topic, requirement.get("applies_to_types")
        ),
        "applies_to_levels": _scope(
            "requirement %s applies_to_levels" % topic,
            requirement.get("applies_to_levels"),
        ),
        "waiver_reference": waiver,
    }


def source_rank(source):
    """Precedence rank of a requirement source; higher governs."""
    if source not in SOURCE_RANK:
        raise ValueError("unknown source %r" % (source,))
    return SOURCE_RANK[source]


def requirement_applies(requirement, harness):
    """Whether one requirement bears on this harness at all."""
    norm = validate_requirement(requirement)
    target = validate_harness(harness)
    type_ok = ANY in norm["applies_to_types"] or target["harness_type"] in norm["applies_to_types"]
    level_ok = (
        ANY in norm["applies_to_levels"]
        or target["assurance_level"] in norm["applies_to_levels"]
    )
    return type_ok and level_ok


def effective_rank(requirement):
    """Rank a requirement actually carries once waivers are accounted for."""
    norm = validate_requirement(requirement)
    if norm["source"] == SOURCE_PROJECT_DEVIATION and norm["waiver_reference"] is None:
        return 0
    return source_rank(norm["source"])


def resolve_topic(requirements, harness):
    """Resolve one topic to its governing requirement, with findings."""
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")
    normalized = [validate_requirement(r) for r in requirements]
    topics = {r["topic"] for r in normalized}
    if len(topics) != 1:
        raise ValueError("resolve_topic needs requirements for exactly one topic")
    target = validate_harness(harness)
    findings = []
    applicable = []
    for norm in normalized:
        if not requirement_applies(norm, target):
            continue
        if effective_rank(norm) == 0:
            if "deviation-without-an-approved-waiver" not in findings:
                findings.append("deviation-without-an-approved-waiver")
            continue
        applicable.append(norm)
    if not applicable:
        findings.append("topic-has-no-applicable-requirement")
        return None, findings
    top = max(effective_rank(r) for r in applicable)
    contenders = [r for r in applicable if effective_rank(r) == top]
    criteria = {r["criterion"] for r in contenders}
    if len(criteria) > 1:
        findings.append("conflicting-sources-at-the-same-precedence-rank")
    governing = sorted(contenders, key=lambda r: (r["source"], r["criterion"]))[0]
    if governing["source"] == SOURCE_EXTERNAL_BASE:
        findings.append("topic-governed-by-the-external-basis-alone")
    return governing, findings


def group_by_topic(requirements):
    """Group a requirement set by topic, preserving first-seen order."""
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")
    grouped = {}
    order = []
    for requirement in requirements:
        norm = validate_requirement(requirement)
        if norm["topic"] not in grouped:
            grouped[norm["topic"]] = []
            order.append(norm["topic"])
        grouped[norm["topic"]].append(norm)
    return [(topic, grouped[topic]) for topic in order]


def resolve_requirement_set(requirements, harness):
    """Resolve a whole requirement set against one harness."""
    target = validate_harness(harness)
    resolved = []
    findings = []
    governed_by = {name: 0 for name in SOURCE_RANK}
    for topic, group in group_by_topic(requirements):
        governing, topic_findings = resolve_topic(group, target)
        if governing is not None:
            governed_by[governing["source"]] += 1
        for finding in topic_findings:
            if finding not in findings:
                findings.append(finding)
        resolved.append(
            {
                "topic": topic,
                "governing_source": governing["source"] if governing else None,
                "governing_criterion": governing["criterion"] if governing else None,
                "findings": topic_findings,
            }
        )
    ecss_governed = sum(governed_by[name] for name in ECSS_SOURCES)
    total = len(resolved)
    blocking = [f for f in findings if f in BLOCKING_FINDINGS]
    return {
        "harness_id": target["id"],
        "topics": resolved,
        "governed_by": governed_by,
        "external_basis_only_topics": [
            entry["topic"]
            for entry in resolved
            if entry["governing_source"] == SOURCE_EXTERNAL_BASE
        ],
        "unresolved_topics": [
            entry["topic"] for entry in resolved if entry["governing_source"] is None
        ],
        "ecss_governed_fraction": (ecss_governed / total) if total else 0.0,
        "findings": findings,
        "blocking_findings": blocking,
        "compliant": not blocking,
    }

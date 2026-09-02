#!/usr/bin/env python3
"""DO-254 hardware requirements capture logic (paraphrase).

Common-knowledge summary (standards-map.yaml, do-254: proprietary RTCA,
summary only): DO-254 requires hardware requirements that are complete,
correct, and verifiable, captured with unique identifiers and trace links,
with derived requirements (added during design with no direct higher-level
source) identified and justified. The checks here are requirement-
characteristic heuristics: vague-term detection, identifier and trace
presence, and capture-readiness accounting with a project-defined
threshold.
"""

VAGUE_TERMS = (
    "suitable", "adequate", "approximately", "etc", "as required",
    "or better", "and so on", "reasonable",
)


def req_issues(requirement):
    """List of issue flags for one requirement mapping.

    Recognized flags: missing-id, empty-text, vague, not-traceable."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    issues = []
    rid = requirement.get("id") or ""
    text = requirement.get("text") or ""
    if not str(rid).strip():
        issues.append("missing-id")
    if not str(text).strip():
        issues.append("empty-text")
    lower = str(text).lower()
    if any(term in lower for term in VAGUE_TERMS):
        issues.append("vague")
    if not requirement.get("traceable"):
        issues.append("not-traceable")
    return issues


def classify_derived(has_higher_level_source):
    """'derived' when there is no direct higher-level source, else 'allocated'."""
    if has_higher_level_source:
        return "allocated"
    return "derived"


def capture_readiness(requirements):
    """(ready, score) fraction of requirements with no issues.

    Raises ValueError on an empty list. Ready means score >= 0.7
    (project-defined threshold)."""
    if not requirements:
        raise ValueError("requirements list must not be empty")
    clean = 0
    for req in requirements:
        if not req_issues(req):
            clean += 1
    score = clean / float(len(requirements))
    return (score >= 0.7, score)

#!/usr/bin/env python3
"""DO-330 tool qualification logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-330: gated):
DO-330 (Software Tool Qualification Considerations) is referenced by
DO-178C section 12.2 for tool credit. Applicable tool criteria 1-5 map
to tool qualification levels TQL-1..TQL-5; criterion 1 (tool output
part of the airborne software and not verified by another means)
demands the highest rigor (TQL-1) and criterion 5 (tool could fail to
detect an error but its output is verified by another means) the lowest
(TQL-5). Lower TQL numbers are stricter. Key artifacts are the tool
operational requirements (TOR), the qualification plan, and the tool
accomplishment summary.
"""

import re

_TQL_RE = re.compile(r"^TQL-([1-5])$")

REQUIRED_ARTIFACTS = (
    "tor",
    "qualification_plan",
    "tool_accomplishment_summary",
)


def _check_criterion(criterion):
    if not isinstance(criterion, int) or criterion not in range(1, 6):
        raise ValueError(
            "tool criterion must be an integer 1..5, got %r" % (criterion,)
        )


def tql_for_criterion(criterion):
    """DO-330 tool criterion (1-5) to its tool qualification level
    TQL-N, where lower N means higher rigor."""
    _check_criterion(criterion)
    return "TQL-%d" % criterion


def tql_rank(tql):
    """Rigor rank of a TQL string: 1 (strictest) .. 5 (least strict)."""
    if not isinstance(tql, str):
        raise ValueError("TQL must be a string like 'TQL-1', got %r" % (tql,))
    m = _TQL_RE.match(tql.strip())
    if not m:
        raise ValueError("malformed TQL: %r (expected TQL-1 .. TQL-5)" % (tql,))
    return int(m.group(1))


def tql_meets_requirement(tql, required_tql):
    """True when the tool's TQL is at least as rigorous as required
    (lower TQL number satisfies a higher-number requirement)."""
    return tql_rank(tql) <= tql_rank(required_tql)


def tor_artifacts_complete(artifacts):
    """(complete, missing) for the DO-330 artifacts: TOR, qualification
    plan, tool accomplishment summary."""
    provided = set(artifacts)
    missing = [a for a in REQUIRED_ARTIFACTS if a not in provided]
    return (not missing, missing)


def tool_category_from_criteria(criteria):
    """Governing tool criterion: the highest applicable criterion number
    when several criteria apply."""
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("criteria must be a non-empty list of criterion numbers")
    for c in criteria:
        _check_criterion(c)
    return max(criteria)

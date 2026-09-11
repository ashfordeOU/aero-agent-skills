#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.10.3 HFE assessment tools selection and coverage
validation (paraphrase, not copy).

Under §4.10.3 of the ECSS human engineering standard the HFE assessment
programme employs four tool families: simulation tools (computer models,
mockups, virtual environments), development tests (ground-based functional
and usability tests), space analogue tests (neutral buoyancy facility NBF
for underwater EVA simulation; partial-gravity parabolic flight PF for
short-duration microgravity), and consensus reports (structured expert
panel review). Each identified HFE concern area must be addressed by at
least one tool; EVA-related concern areas must additionally be covered by
at least one space analogue test (NBF or PF) because ground-based tools
cannot replicate the biomechanical loading of a weightless environment.
This module implements tool-family recognition, EVA concern identification,
concern-to-tool coverage checking, and assessment plan violation reporting.
"""

TOOL_TYPES = frozenset({
    "simulation",        # computer models, mockups, virtual environments
    "development_test",  # ground-based functional/usability tests
    "analogue_nbf",      # neutral buoyancy facility (EVA underwater analogue)
    "analogue_pf",       # parabolic flight (partial-gravity / zero-g analogue)
    "consensus_report",  # structured expert panel review
})

SPACE_ANALOGUE_TYPES = frozenset({"analogue_nbf", "analogue_pf"})

# EVA-related concern areas that require at least one space analogue tool.
# Ground simulation and consensus reports cannot satisfy this requirement.
EVA_CONCERN_AREAS = frozenset({
    "eva_task_execution",
    "eva_suit_donning",
    "eva_reach_envelope",
    "eva_tool_handling",
})


def categorize_tool(tool_type):
    """Return tool_type unchanged when it belongs to a recognized §4.10.3
    family; raise ValueError for any type outside TOOL_TYPES."""
    if tool_type in TOOL_TYPES:
        return tool_type
    raise ValueError(
        "unrecognized §4.10.3 assessment tool type %r" % (tool_type,)
    )


def is_space_analogue(tool_type):
    """True when tool_type is a space analogue (NBF or PF).
    Raises ValueError for an unrecognized tool_type."""
    categorize_tool(tool_type)
    return tool_type in SPACE_ANALOGUE_TYPES


def is_eva_concern(concern_area):
    """True when concern_area is an EVA-related activity that requires
    a space analogue test under §4.10.3."""
    return concern_area in EVA_CONCERN_AREAS


def check_coverage(concern_areas, applied_tools):
    """Coverage analysis for an assessment plan.

    concern_areas: iterable of str (HFE concern area identifiers).
    applied_tools: iterable of dicts, each with keys:
        "tool_type"  – one of TOOL_TYPES; raises ValueError if unrecognized.
        "addresses"  – iterable of str concern area identifiers this tool covers.

    Returns a dict:
        "uncovered"            – sorted list of concern areas with no tool.
        "eva_without_analogue" – sorted list of EVA concern areas addressed
                                 only by non-analogue tools (NBF or PF absent).

    Does not mutate inputs.
    """
    concern_set = set(concern_areas)
    covered_by = {c: [] for c in concern_set}

    for tool in applied_tools:
        t_type = categorize_tool(tool["tool_type"])
        for concern in tool.get("addresses", []):
            if concern in covered_by:
                covered_by[concern].append(t_type)

    uncovered = sorted(c for c, tools in covered_by.items() if not tools)

    eva_without_analogue = sorted(
        c for c, tools in covered_by.items()
        if c in EVA_CONCERN_AREAS
        and tools
        and not any(t in SPACE_ANALOGUE_TYPES for t in tools)
    )

    return {
        "uncovered": uncovered,
        "eva_without_analogue": eva_without_analogue,
    }


def plan_violations(plan):
    """Violation list (empty when compliant) for a §4.10.3 assessment plan.

    plan: {
        "concern_areas": [str, ...],
        "tools": [{"tool_type": str, "addresses": [str, ...]}, ...]
    }

    Each violation dict carries at minimum an "issue" key:
        "concern_not_covered"       – no tool addresses this concern area.
        "eva_concern_lacks_analogue"– EVA concern addressed only by
                                     non-analogue tools.

    Raises ValueError for an unrecognized tool_type in plan["tools"].
    """
    result = check_coverage(
        plan.get("concern_areas", []),
        plan.get("tools", []),
    )
    violations = []
    for concern in result["uncovered"]:
        violations.append({"issue": "concern_not_covered", "concern_area": concern})
    for concern in result["eva_without_analogue"]:
        violations.append({"issue": "eva_concern_lacks_analogue", "concern_area": concern})
    return violations


def is_plan_compliant(violations):
    """True when plan_violations returned an empty list."""
    return len(violations) == 0

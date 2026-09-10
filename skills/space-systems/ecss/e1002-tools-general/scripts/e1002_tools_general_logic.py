#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.6.1 verification tool classification and
qualification-status assignment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): every
tool used in verification (test equipment, ground support equipment,
simulators, software tools, facilities) must be identified, categorized
by type, and given a qualification status before its output is accepted
as verification evidence. This module implements that general
classification and category-assignment step; it does not implement the
family-specific qualification detail owned by the sibling e1002-gse-tools,
e1002-simulators, e1002-sw-tools, and e1002-facilities leaves.
"""

TOOL_TYPES = ("test_equipment", "gse", "simulator", "software_tool", "facility", "other")
CRITICALITY_LEVELS = ("safety_critical", "mission_critical", "standard", "negligible")
CATEGORIES = ("A", "B", "C", "D")
CATEGORY_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}

QUALIFICATION_ACTIONS = {
    "A": "full qualification with configuration control and traceable calibration before use",
    "B": "documented qualification against defined performance requirements plus calibration traceability",
    "C": "calibration or checkout against the manufacturer specification, recorded in the tool's usage record",
    "D": "basic serviceability check; no formal qualification record required",
}


def classify_tool_type(tool_type):
    """Validate and return the tool type. Raises ValueError for an
    unknown tool type."""
    if tool_type not in TOOL_TYPES:
        raise ValueError("unknown tool type: %r" % (tool_type,))
    return tool_type


def determine_qualification_category(generates_verification_evidence, criticality, independent_corroboration=False):
    """Qualification-status category for one tool, by fixed precedence:
    a tool that does not generate accepted verification evidence ->
    category D; safety-critical with no corroboration -> A;
    safety-critical with corroboration, or mission-critical with no
    corroboration -> B; mission-critical with corroboration, or standard
    criticality -> C; negligible criticality -> D. Raises ValueError for
    an unknown criticality."""
    if criticality not in CRITICALITY_LEVELS:
        raise ValueError("unknown requirement criticality: %r" % (criticality,))
    if not generates_verification_evidence:
        return "D"
    if criticality == "safety_critical":
        return "B" if independent_corroboration else "A"
    if criticality == "mission_critical":
        return "C" if independent_corroboration else "B"
    if criticality == "standard":
        return "C"
    return "D"  # negligible


def qualification_actions(category):
    """Expected qualification actions for a category. Raises ValueError
    for an unknown category."""
    if category not in CATEGORIES:
        raise ValueError("unknown qualification category: %r" % (category,))
    return QUALIFICATION_ACTIONS[category]


def classify_and_qualify_tool(tool):
    """(type, category, actions) assignment for one tool dict. Required
    keys: id, tool_type, generates_verification_evidence, criticality;
    optional key: independent_corroboration (defaults False). Returns a
    new dict; does not mutate the input. Raises ValueError if 'id' is
    missing."""
    if "id" not in tool:
        raise ValueError("tool is missing an id")
    tool_type = classify_tool_type(tool["tool_type"])
    category = determine_qualification_category(
        tool["generates_verification_evidence"],
        tool["criticality"],
        tool.get("independent_corroboration", False),
    )
    return {
        "id": tool["id"],
        "tool_type": tool_type,
        "category": category,
        "actions": qualification_actions(category),
    }


def build_tool_register(tools):
    """Tool register: one classification dict per tool, in input order.
    Raises ValueError on a duplicate tool id."""
    register = []
    seen_ids = set()
    for tool in tools:
        entry = classify_and_qualify_tool(tool)
        if entry["id"] in seen_ids:
            raise ValueError("duplicate tool id: %r" % (entry["id"],))
        seen_ids.add(entry["id"])
        register.append(entry)
    return register


def missing_tool_classifications(all_tool_ids, register):
    """Tool ids present in all_tool_ids but absent from the register, in
    all_tool_ids order -- the clause 5.2.6.1 completeness check (every
    tool used in verification must be categorized)."""
    categorized_ids = {entry["id"] for entry in register}
    return [tid for tid in all_tool_ids if tid not in categorized_ids]


def apply_manual_category_override(register, overrides):
    """New register with per-id category overrides applied (overrides:
    dict id -> category); entries without an override are copied
    unchanged. Does not mutate the input register. Raises ValueError for
    an unknown override category."""
    for category in overrides.values():
        if category not in CATEGORIES:
            raise ValueError("unknown qualification category: %r" % (category,))
    return [
        dict(entry, category=overrides.get(entry["id"], entry["category"]))
        for entry in register
    ]


def find_understated_categories(register, tools_by_id):
    """Tool ids in the register whose assigned category is weaker (less
    stringent) than the category the criticality/corroboration rule
    would compute from tools_by_id -- the condition E-ST-10-02C guards
    against for safety- and mission-critical tools. Returns ids in
    register order."""
    understated = []
    for entry in register:
        tool = tools_by_id[entry["id"]]
        required = determine_qualification_category(
            tool["generates_verification_evidence"],
            tool["criticality"],
            tool.get("independent_corroboration", False),
        )
        if CATEGORY_RANK[entry["category"]] > CATEGORY_RANK[required]:
            understated.append(entry["id"])
    return understated

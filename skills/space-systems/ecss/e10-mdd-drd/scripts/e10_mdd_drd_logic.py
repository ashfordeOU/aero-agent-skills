#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex B Mission Description Document (MDD) DRD
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
MDD is produced early in the project (phase 0) and states what the
mission is for and under what constraints, ahead of the mission
definition review (MDR) and before candidate concepts are traded in
the System Concept Report (see the sibling e10-scr-drd leaf). This
module implements the DRD's completeness checks: the four mandatory
sections, the mission-statement fields, the mission-scenario phase
order, and constraint categorisation. It does not draft document prose
or run the review itself.
"""

REQUIRED_SECTIONS = ("objectives", "mission_statement", "mission_scenario", "constraints")
MISSION_STATEMENT_FIELDS = ("objective", "target", "timeframe")
CONSTRAINT_CATEGORIES = ("programmatic", "technical", "operational", "environmental")
SCENARIO_PHASES = ("launch", "commissioning", "operations", "disposal")


def _is_empty(value):
    """True when value is absent-equivalent: None, or an empty
    str/list/tuple/dict."""
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict)):
        return len(value) == 0
    return False


def missing_sections(mdd):
    """Required MDD section keys that are absent or empty in mdd, in
    REQUIRED_SECTIONS order. Raises ValueError if mdd is not a dict."""
    if not isinstance(mdd, dict):
        raise ValueError("mdd must be a dict")
    return [section for section in REQUIRED_SECTIONS if _is_empty(mdd.get(section))]


def missing_statement_fields(mission_statement):
    """MISSION_STATEMENT_FIELDS absent or empty in mission_statement,
    in field order. Raises ValueError if mission_statement is not a
    dict."""
    if not isinstance(mission_statement, dict):
        raise ValueError("mission_statement must be a dict")
    return [
        field
        for field in MISSION_STATEMENT_FIELDS
        if _is_empty(mission_statement.get(field))
    ]


def validate_scenario_order(phases):
    """Phase names from `phases` that regress behind an earlier phase
    already seen (violating the launch -> commissioning -> operations
    -> disposal canonical order), in input order. A phase may be
    omitted or repeated without violation. Raises ValueError if any
    phase is not in SCENARIO_PHASES."""
    for phase in phases:
        if phase not in SCENARIO_PHASES:
            raise ValueError("unknown mission scenario phase: %r" % (phase,))
    violations = []
    highest_index_seen = -1
    for phase in phases:
        index = SCENARIO_PHASES.index(phase)
        if index < highest_index_seen:
            violations.append(phase)
        else:
            highest_index_seen = index
    return violations


def classify_constraints(constraints):
    """New dict {"valid": [...], "invalid": [...]} of constraint ids
    from `constraints` (each a dict with 'id' and 'category'),
    partitioned by whether category is a member of
    CONSTRAINT_CATEGORIES. Does not mutate the input. Raises
    ValueError if any constraint is missing an id."""
    valid_ids = []
    invalid_ids = []
    for constraint in constraints:
        if "id" not in constraint:
            raise ValueError("constraint is missing an id")
        if constraint.get("category") in CONSTRAINT_CATEGORIES:
            valid_ids.append(constraint["id"])
        else:
            invalid_ids.append(constraint["id"])
    return {"valid": valid_ids, "invalid": invalid_ids}


def build_completeness_report(mdd):
    """New completeness report dict for `mdd` combining section,
    mission-statement, scenario-order, and constraint-category checks.
    Keys: sections_missing, statement_fields_missing, scenario_order_
    violations, constraints_invalid, complete. Does not mutate mdd."""
    sections_missing = missing_sections(mdd)

    statement_fields_missing = (
        []
        if "mission_statement" in sections_missing
        else missing_statement_fields(mdd["mission_statement"])
    )
    scenario_order_violations = (
        []
        if "mission_scenario" in sections_missing
        else validate_scenario_order(mdd["mission_scenario"])
    )
    constraints_invalid = (
        []
        if "constraints" in sections_missing
        else classify_constraints(mdd["constraints"])["invalid"]
    )

    complete = not (
        sections_missing
        or statement_fields_missing
        or scenario_order_violations
        or constraints_invalid
    )
    return {
        "sections_missing": sections_missing,
        "statement_fields_missing": statement_fields_missing,
        "scenario_order_violations": scenario_order_violations,
        "constraints_invalid": constraints_invalid,
        "complete": complete,
    }


def drd_gate_verdict(report):
    """"ready" if report["complete"] is True, else "not_ready". Raises
    ValueError if report has no "complete" key."""
    if "complete" not in report:
        raise ValueError("report is missing the 'complete' key")
    return "ready" if report["complete"] else "not_ready"

#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex C System Concept Report (SCR) DRD
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
SCR is produced during phase 0/A and captures the candidate system
concepts developed to satisfy the mission stated in the Mission
Description Document (see the sibling e10-mdd-drd leaf), the trade-off
performed among them, and the concept recommended to carry forward
into system/segment requirements (see the sibling e10-req-analysis
leaf). This module implements the DRD's completeness checks: the four
mandatory sections, candidate-concept descriptions, trade-criteria
coverage, feasibility-verdict classification, and recommendation
validity. It does not draft document prose or run the down-select
itself.
"""

REQUIRED_SECTIONS = (
    "candidate_concepts",
    "trade_summary",
    "feasibility_assessment",
    "recommended_concept",
)
TRADE_CRITERIA = ("technical", "programmatic", "cost", "risk")
FEASIBILITY_VERDICTS = ("feasible", "feasible_with_risk", "not_feasible")


def _is_empty(value):
    """True when value is absent-equivalent: None, or an empty
    str/list/tuple/dict."""
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict)):
        return len(value) == 0
    return False


def missing_sections(scr):
    """Required SCR section keys that are absent or empty in scr, in
    REQUIRED_SECTIONS order. Raises ValueError if scr is not a dict."""
    if not isinstance(scr, dict):
        raise ValueError("scr must be a dict")
    return [section for section in REQUIRED_SECTIONS if _is_empty(scr.get(section))]


def incomplete_concepts(candidate_concepts):
    """Candidate concept ids missing a description, in list order.
    Raises ValueError if any concept is missing an id."""
    missing = []
    for concept in candidate_concepts:
        if "id" not in concept:
            raise ValueError("candidate concept is missing an id")
        if _is_empty(concept.get("description")):
            missing.append(concept["id"])
    return missing


def missing_trade_criteria(trade_summary, concept_ids):
    """New dict {concept_id: [missing criteria in TRADE_CRITERIA
    order]} for every concept_id in concept_ids that lacks a
    trade_summary entry for one or more TRADE_CRITERIA. Concepts with
    no gaps are omitted. Does not mutate inputs. Raises ValueError if
    a trade_summary entry references a concept_id outside concept_ids
    or an unknown criterion."""
    covered = {concept_id: set() for concept_id in concept_ids}
    for entry in trade_summary:
        concept_id = entry.get("concept_id")
        criterion = entry.get("criterion")
        if concept_id not in covered:
            raise ValueError(
                "trade_summary entry references unknown concept_id: %r" % (concept_id,)
            )
        if criterion not in TRADE_CRITERIA:
            raise ValueError(
                "trade_summary entry has unknown criterion: %r" % (criterion,)
            )
        covered[concept_id].add(criterion)

    gaps = {}
    for concept_id in concept_ids:
        missing = [c for c in TRADE_CRITERIA if c not in covered[concept_id]]
        if missing:
            gaps[concept_id] = missing
    return gaps


def classify_feasibility(feasibility_assessment, concept_ids):
    """New dict {"not_feasible": [...], "invalid": [...], "missing":
    [...]} built by matching feasibility_assessment entries to every
    id in concept_ids, in concept_ids order: not_feasible lists
    concept ids whose verdict is "not_feasible", invalid lists concept
    ids whose verdict is not a member of FEASIBILITY_VERDICTS, and
    missing lists concept ids with no assessment entry. Does not
    mutate inputs. Raises ValueError if an entry has no concept_id or
    references a concept_id outside concept_ids."""
    verdict_by_id = {}
    for entry in feasibility_assessment:
        if "concept_id" not in entry:
            raise ValueError("feasibility assessment entry is missing a concept_id")
        concept_id = entry["concept_id"]
        if concept_id not in concept_ids:
            raise ValueError(
                "feasibility assessment references unknown concept_id: %r" % (concept_id,)
            )
        verdict_by_id[concept_id] = entry.get("verdict")

    not_feasible = []
    invalid = []
    missing = []
    for concept_id in concept_ids:
        if concept_id not in verdict_by_id:
            missing.append(concept_id)
            continue
        verdict = verdict_by_id[concept_id]
        if verdict not in FEASIBILITY_VERDICTS:
            invalid.append(concept_id)
        elif verdict == "not_feasible":
            not_feasible.append(concept_id)
    return {"not_feasible": not_feasible, "invalid": invalid, "missing": missing}


def validate_recommendation(recommended_concept, concept_ids, feasibility_assessment):
    """List of problems with recommended_concept, empty if none:
    "unknown_concept" if recommended_concept is not in concept_ids,
    "no_feasibility_assessment" if feasibility_assessment has no entry
    for it, "not_feasible" if its verdict is "not_feasible". Raises
    ValueError if recommended_concept is empty."""
    if _is_empty(recommended_concept):
        raise ValueError("recommended_concept must be a non-empty identifier")

    if recommended_concept not in concept_ids:
        return ["unknown_concept"]

    verdict = None
    found = False
    for entry in feasibility_assessment:
        if entry.get("concept_id") == recommended_concept:
            verdict = entry.get("verdict")
            found = True
            break

    if not found:
        return ["no_feasibility_assessment"]
    if verdict == "not_feasible":
        return ["not_feasible"]
    return []


def build_completeness_report(scr):
    """New completeness report dict for `scr` combining section,
    candidate-concept, trade-criteria-coverage,
    feasibility-classification, and recommendation checks. Keys:
    sections_missing, concepts_incomplete, trade_criteria_gaps,
    feasibility_issues, recommendation_issues, complete. A not_feasible
    verdict on a candidate that is not the recommendation does not
    block completeness. Does not mutate scr."""
    sections_missing = missing_sections(scr)

    concept_ids = (
        []
        if "candidate_concepts" in sections_missing
        else [concept["id"] for concept in scr["candidate_concepts"]]
    )
    concepts_incomplete = (
        []
        if "candidate_concepts" in sections_missing
        else incomplete_concepts(scr["candidate_concepts"])
    )
    trade_criteria_gaps = (
        {}
        if "candidate_concepts" in sections_missing
        or "trade_summary" in sections_missing
        else missing_trade_criteria(scr["trade_summary"], concept_ids)
    )
    feasibility_issues = (
        {"not_feasible": [], "invalid": [], "missing": []}
        if "candidate_concepts" in sections_missing
        or "feasibility_assessment" in sections_missing
        else classify_feasibility(scr["feasibility_assessment"], concept_ids)
    )
    recommendation_issues = (
        []
        if "candidate_concepts" in sections_missing
        or "feasibility_assessment" in sections_missing
        or "recommended_concept" in sections_missing
        else validate_recommendation(
            scr["recommended_concept"], concept_ids, scr["feasibility_assessment"]
        )
    )

    complete = not (
        sections_missing
        or concepts_incomplete
        or trade_criteria_gaps
        or feasibility_issues["invalid"]
        or feasibility_issues["missing"]
        or recommendation_issues
    )
    return {
        "sections_missing": sections_missing,
        "concepts_incomplete": concepts_incomplete,
        "trade_criteria_gaps": trade_criteria_gaps,
        "feasibility_issues": feasibility_issues,
        "recommendation_issues": recommendation_issues,
        "complete": complete,
    }


def drd_gate_verdict(report):
    """"ready" if report["complete"] is True, else "not_ready". Raises
    ValueError if report has no "complete" key."""
    if "complete" not in report:
        raise ValueError("report is missing the 'complete' key")
    return "ready" if report["complete"] else "not_ready"

"""FMEA-to-FHA coverage analysis logic (ARP4761A failure modes and effects summary).

Pure stdlib, deterministic. Maps failure-mode effect rows onto the
functional-hazard condition set, flags unlinked rows as orphans, reports
the coverage ratio and the per-severity-class coverage, and scores
row-to-condition text similarity to suggest candidate condition ids.
"""

import re


def normalize(text):
    """Return the lowercase alphanumeric tokens of text (workflow step 2).

    Uses re.findall(r"[a-z0-9]+", text.lower()), which strips case,
    punctuation and whitespace runs deterministically.
    """
    return re.findall(r"[a-z0-9]+", text.lower())


def condition_match_score(row_text, condition_text):
    """Return the Jaccard similarity of row text and condition text.

    Computes |A and B| / |A or B| over the normalized token sets, in
    [0, 1]. Both token sets empty gives 0.0 (no evidence to match on).
    Text-only helper for suggesting candidate condition ids to the
    analyst, not a substitute for the analyst's condition_id assignment.
    """
    row_tokens = set(normalize(row_text))
    condition_tokens = set(normalize(condition_text))
    if not row_tokens and not condition_tokens:
        return 0.0
    return len(row_tokens & condition_tokens) / len(row_tokens | condition_tokens)


def _validated_row_ids_and_links(conditions, rows):
    """Shared linkage validation for both coverage functions.

    Returns (condition_by_id, linked_set, orphan_row_ids). Raises
    ValueError on an empty conditions list, a row missing row_id or
    condition_id keys, or a row whose condition_id is not an id in
    conditions (typo guard); a row with condition_id None is an orphan.
    """
    if not conditions:
        raise ValueError("empty conditions list: no condition table to cover")
    condition_by_id = {condition["id"]: condition for condition in conditions}
    linked = set()
    orphan_row_ids = []
    for row in rows:
        if "row_id" not in row or "condition_id" not in row:
            raise ValueError("row missing row_id or condition_id key: %r" % (row,))
        condition_id = row["condition_id"]
        if condition_id is None:
            orphan_row_ids.append(row["row_id"])
            continue
        if condition_id not in condition_by_id:
            raise ValueError("row links to unknown condition id: %r" % (condition_id,))
        linked.add(condition_id)
    return condition_by_id, linked, orphan_row_ids


def coverage_score(conditions, rows):
    """Map every FMEA row to the condition it demonstrates (workflow step 4).

    Returns {"covered_conditions": condition ids with at least one row in
    conditions input order, "uncovered_conditions": ids with no row in
    conditions input order, "orphan_rows": row ids with condition_id None
    in rows input order, "coverage": len(covered) / len(conditions)}.
    """
    condition_by_id, linked, orphan_row_ids = _validated_row_ids_and_links(
        conditions, rows
    )
    condition_ids = list(condition_by_id)
    covered = [cid for cid in condition_ids if cid in linked]
    uncovered = [cid for cid in condition_ids if cid not in linked]
    return {
        "covered_conditions": covered,
        "uncovered_conditions": uncovered,
        "orphan_rows": orphan_row_ids,
        "coverage": len(covered) / len(condition_ids),
    }


def coverage_by_severity(conditions, rows):
    """Break the coverage down per severity class (workflow step 5).

    Returns {severity: {"covered": count, "uncovered": count,
    "coverage": covered / (covered + uncovered)}} with dict order
    following first appearance in conditions; severities with no
    conditions are omitted. ValueErrors as in coverage_score plus a
    ValueError when a condition has no severity field.
    """
    condition_by_id, linked, _ = _validated_row_ids_and_links(conditions, rows)
    for condition in conditions:
        if "severity" not in condition:
            raise ValueError(
                "condition %r has no severity field" % (condition.get("id"),)
            )
    result = {}
    for condition in conditions:
        severity = condition["severity"]
        if severity not in result:
            result[severity] = {"covered": 0, "uncovered": 0, "coverage": 0.0}
        if condition["id"] in linked:
            result[severity]["covered"] += 1
        else:
            result[severity]["uncovered"] += 1
    for counts in result.values():
        total = counts["covered"] + counts["uncovered"]
        counts["coverage"] = counts["covered"] / total if total else 0.0
    return result

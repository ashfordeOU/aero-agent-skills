"""
ECSS-E-ST-10C §8.2.6 — Requirement identifiability logic.

Each requirement must carry a stable, unique identifier (UID).
Four checks are implemented:
  1. presence   — every requirement has a non-empty, non-placeholder identifier
  2. format     — every identifier matches the agreed pattern
  3. uniqueness — no two requirements share an identifier
  4. gap scan   — large numeric gaps within a prefix group flag potential
                  renumbering events (advisory, not a compliance block)
"""

import re
from collections import defaultdict

DEFAULT_ID_PATTERN = r'^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[0-9]{3,4}$'

_PLACEHOLDER_SENTINELS = frozenset({"", None, "N/A", "TBD", "TBC", "NA"})


def validate_identifier_format(req_id, pattern=DEFAULT_ID_PATTERN):
    """
    Check whether req_id conforms to pattern.

    Returns:
        dict with keys "valid" (bool) and "message" (str).
    """
    if req_id in _PLACEHOLDER_SENTINELS:
        return {"valid": False, "message": "identifier is absent or a placeholder"}
    if not isinstance(req_id, str):
        return {
            "valid": False,
            "message": "identifier must be a string, got {}".format(type(req_id).__name__),
        }
    if re.fullmatch(pattern, req_id):
        return {"valid": True, "message": "identifier matches the agreed format"}
    return {
        "valid": False,
        "message": "identifier '{}' does not match pattern '{}'".format(req_id, pattern),
    }


def find_missing_identifiers(requirements):
    """
    Return a sorted list of 0-based indices for requirements that lack a valid identifier.

    A requirement is a dict.  The identifier field is keyed 'id'.
    Missing means the 'id' key is absent, None, empty, or a placeholder sentinel.
    """
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list of dicts")
    missing = []
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            raise TypeError("each requirement must be a dict, entry {} is {}".format(
                i, type(req).__name__))
        req_id = req.get("id")
        if req_id in _PLACEHOLDER_SENTINELS:
            missing.append(i)
    return missing


def find_duplicate_identifiers(requirements):
    """
    Return a dict mapping each duplicated identifier to the list of indices where it appears.

    Requirements without a valid identifier are skipped (they are caught by
    find_missing_identifiers, not here).  Single-occurrence identifiers are not included.
    """
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list of dicts")
    seen = defaultdict(list)
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            raise TypeError("each requirement must be a dict, entry {} is {}".format(
                i, type(req).__name__))
        req_id = req.get("id")
        if req_id not in _PLACEHOLDER_SENTINELS:
            seen[req_id].append(i)
    return {k: v for k, v in seen.items() if len(v) > 1}


def check_format_violations(requirements, pattern=DEFAULT_ID_PATTERN):
    """
    Return a list of violation dicts for identifiers that fail the format pattern.

    Requirements with missing identifiers are excluded (they are handled by
    find_missing_identifiers).  Each violation entry:
        {"index": int, "id": str, "message": str}
    """
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list of dicts")
    violations = []
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            raise TypeError("each requirement must be a dict, entry {} is {}".format(
                i, type(req).__name__))
        req_id = req.get("id")
        if req_id in _PLACEHOLDER_SENTINELS:
            continue
        result = validate_identifier_format(req_id, pattern)
        if not result["valid"]:
            violations.append({"index": i, "id": req_id, "message": result["message"]})
    return violations


def detect_numeric_gaps(requirements, prefix):
    """
    Scan identifiers that start with prefix, extract trailing numeric suffixes,
    sort them, and return gap descriptors for gaps larger than 1 missing number.

    A difference of 2 between adjacent IDs (one number missing) is tolerated;
    a difference > 2 (two or more numbers missing) is a stability warning that
    may indicate a renumbering event.

    Returns:
        list of dicts: {"after": int, "before": int, "missing_count": int, "message": str}
    """
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list of dicts")
    if not isinstance(prefix, str):
        raise TypeError("prefix must be a string")
    nums = []
    for req in requirements:
        req_id = req.get("id") if isinstance(req, dict) else None
        if req_id and isinstance(req_id, str) and req_id.startswith(prefix):
            m = re.search(r'(\d+)$', req_id)
            if m:
                nums.append(int(m.group(1)))
    if len(nums) < 2:
        return []
    nums_sorted = sorted(nums)
    gaps = []
    for a, b in zip(nums_sorted, nums_sorted[1:]):
        gap = b - a
        if gap > 2:
            gaps.append({
                "after": a,
                "before": b,
                "missing_count": gap - 1,
                "message": (
                    "gap of {} between {}{} and {}{}; "
                    "possible renumbering event".format(
                        gap - 1, prefix, a, prefix, b
                    )
                ),
            })
    return gaps


def assess_identifiability(requirements, id_pattern=DEFAULT_ID_PATTERN):
    """
    Run the full identifiability assessment for a requirement set.

    Args:
        requirements: list of dicts, each with at minimum an 'id' key.
        id_pattern:   regex string for the agreed identifier format.

    Returns:
        {
          "compliant": bool,
          "findings": {
            "missing_ids":        [int, ...],
            "format_violations":  [{"index", "id", "message"}, ...],
            "duplicates":         {id: [int, ...], ...},
          },
          "summary": str
        }

    Raises:
        TypeError if requirements is not a list.
    """
    if not isinstance(requirements, list):
        raise TypeError("requirements must be a list of dicts")

    missing = find_missing_identifiers(requirements)
    format_violations = check_format_violations(requirements, id_pattern)
    duplicates = find_duplicate_identifiers(requirements)

    compliant = not (missing or format_violations or duplicates)

    parts = []
    if missing:
        parts.append("{} requirement(s) lack an identifier".format(len(missing)))
    if format_violations:
        parts.append("{} format violation(s)".format(len(format_violations)))
    if duplicates:
        parts.append("{} duplicate identifier(s)".format(len(duplicates)))

    summary = (
        "All identifiability checks passed."
        if compliant
        else "Findings: " + "; ".join(parts) + "."
    )

    return {
        "compliant": compliant,
        "findings": {
            "missing_ids": missing,
            "format_violations": format_violations,
            "duplicates": duplicates,
        },
        "summary": summary,
    }

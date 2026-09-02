"""SysML requirements modeling helpers for model-based systems engineering.

Deterministic, offline, stdlib-only helpers for building and reviewing
a SysML requirements diagram: requirement id validation, requirement
text screening (shall clause count for atomicity, vague term detection,
verifiability verdict), relationship kind checks, derive chain checks,
verification status roll-up through the requirement tree, satisfy and
verify link coverage, and the combined model review verdict.

Contract exercised by scripts/test_requirements_modeling.py.
"""

import re

VALID_RELATIONSHIP_KINDS = ("derive", "satisfy", "verify", "refine", "trace")
VERIFICATION_METHODS = ("test", "analysis", "demonstration", "inspection")

VAGUE_TERMS = (
    "adequate",
    "approximately",
    "etc",
    "suitable",
    "and/or",
    "as required",
    "timely",
    "minimize",
    "maximize",
)

ID_PATTERN = re.compile(r"^[A-Z]{2,4}-[0-9]{3,5}$")


def validate_requirement_id(requirement_id):
    """Return True when the id matches the canonical requirement id format.

    The format is 2 to 4 uppercase letters, a hyphen, then 3 to 5
    digits, for example SYS-001 or FC-0001. Requirement ids feed the
    tree roll-up and the coverage reports, so the format check runs
    before the model review.

    Raises ValueError for a non-string id.
    """
    if not isinstance(requirement_id, str):
        raise ValueError("requirement id must be a string, got %r" % (requirement_id,))
    return bool(ID_PATTERN.fullmatch(requirement_id))


def count_shall_clauses(text):
    """Return the number of shall clauses in the requirement text.

    Atomicity requires exactly one shall clause per requirement; two
    shall clauses in one text are two requirements that must be split
    before the model review.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    return len(re.findall(r"\bshall\b", text.lower()))


def find_vague_terms(text):
    """Return the sorted list of vague terms found in the requirement text.

    Vague terms such as adequate, approximately, etc, suitable, and/or,
    as required, timely, minimize, and maximize carry no measurable
    acceptance bound, so a requirement containing one cannot be
    verified as written.

    Raises ValueError for a non-string text.
    """
    if not isinstance(text, str):
        raise ValueError("requirement text must be a string, got %r" % (text,))
    lowered = text.lower()
    found = []
    for term in VAGUE_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", lowered):
            found.append(term)
    return sorted(found)


def requirement_verifiability(requirement):
    """Return a verdict dict for one requirement mapping.

    The mapping carries id, text, and method. A requirement is
    verifiable when its text has exactly one shall clause, no vague
    terms, and a method in {test, analysis, demonstration, inspection}.
    The verdict dict carries the id, the verifiable boolean, and the
    sorted reason list when not verifiable.

    Raises ValueError for a missing required key or a non-string text.
    """
    for key in ("id", "text", "method"):
        if key not in requirement:
            raise ValueError("requirement missing key %r" % (key,))
    if not isinstance(requirement["text"], str):
        raise ValueError("requirement text must be a string")
    reasons = []
    shall_count = count_shall_clauses(requirement["text"])
    if shall_count != 1:
        reasons.append("shall-clause count %d, expected 1" % shall_count)
    vague = find_vague_terms(requirement["text"])
    if vague:
        reasons.append("vague terms: %s" % ", ".join(vague))
    if requirement["method"] not in VERIFICATION_METHODS:
        reasons.append(
            "method %r not in %s"
            % (requirement["method"], ", ".join(VERIFICATION_METHODS))
        )
    return {
        "id": requirement["id"],
        "verifiable": not reasons,
        "reasons": sorted(reasons),
    }


def rollup_verification_status(child_statuses):
    """Return the rolled-up verification status of a requirement tree.

    A parent is verified only when every child is verified; any failed
    child fails the parent; any in-review child keeps the parent
    in-review; a tree with no assessed children is not-assessed. Empty
    child list returns not-assessed.

    Raises ValueError for a non-list input.
    """
    if not isinstance(child_statuses, list):
        raise ValueError("child statuses must be a list, got %r" % (child_statuses,))
    if not child_statuses:
        return "not-assessed"
    if all(s == "verified" for s in child_statuses):
        return "verified"
    if any(s == "failed" for s in child_statuses):
        return "failed"
    if any(s == "in-review" for s in child_statuses):
        return "in-review"
    return "not-assessed"


def satisfy_coverage(requirement_ids, satisfy_links):
    """Return (fraction, unsatisfied ids) for satisfy link coverage.

    satisfy_links is a list of (requirement_id, design_element) pairs.
    A requirement is satisfied when it appears as the first element of
    at least one pair. The fraction is satisfied over total; the gap
    list is the sorted unsatisfied ids. Empty requirement list returns
    (1.0, []).

    Raises ValueError for a non-list input.
    """
    if not isinstance(requirement_ids, list) or not isinstance(satisfy_links, list):
        raise ValueError("requirement ids and satisfy links must be lists")
    if not requirement_ids:
        return 1.0, []
    satisfied_ids = {pair[0] for pair in satisfy_links}
    satisfied = [rid for rid in requirement_ids if rid in satisfied_ids]
    missing = sorted(set(requirement_ids) - satisfied_ids)
    return len(satisfied) / float(len(requirement_ids)), missing


def verify_coverage(requirement_ids, verify_links):
    """Return (fraction, unverified ids) for verify link coverage.

    verify_links is a list of (requirement_id, verification_item)
    pairs. A requirement is verified-linked when it appears as the
    first element of at least one pair. The fraction is
    verify-linked over total; the gap list is the sorted unverified
    ids. Empty requirement list returns (1.0, []).

    Raises ValueError for a non-list input.
    """
    if not isinstance(requirement_ids, list) or not isinstance(verify_links, list):
        raise ValueError("requirement ids and verify links must be lists")
    if not requirement_ids:
        return 1.0, []
    verified_ids = {pair[0] for pair in verify_links}
    verified = [rid for rid in requirement_ids if rid in verified_ids]
    missing = sorted(set(requirement_ids) - verified_ids)
    return len(verified) / float(len(requirement_ids)), missing


def derive_chain_check(links):
    """Return (valid, issues) for the derive relationship list.

    Each link is a (source_id, target_id) pair meaning the target is
    derived from the source. A self-derive (source equals target) or a
    link whose source id fails validate_requirement_id or whose target
    id fails validate_requirement_id is an issue. The issues list is
    sorted.

    Raises ValueError for a non-list input.
    """
    if not isinstance(links, list):
        raise ValueError("derive links must be a list, got %r" % (links,))
    issues = []
    for pair in links:
        source, target = pair
        if source == target:
            issues.append("self-derive %r" % (source,))
        if not validate_requirement_id(source):
            issues.append("invalid source id %r" % (source,))
        if not validate_requirement_id(target):
            issues.append("invalid target id %r" % (target,))
    return (not issues), sorted(set(issues))


def relationship_kind_valid(kind):
    """Return True when kind is a SysML requirement relationship kind.

    Valid kinds are derive, satisfy, verify, refine, and trace.
    """
    return kind in VALID_RELATIONSHIP_KINDS


def model_review_verdict(requirement_ids, satisfy_links, verify_links, child_statuses):
    """Return the combined model review verdict dict.

    Combines satisfy coverage, verify coverage, and the status roll-up:
    verdict is ready when both coverages are 1.0 with no gaps and the
    roll-up is verified; otherwise verdict is gaps with the reason
    list (unsatisfied ids, unverified ids, and the roll-up status).
    """
    sat_frac, sat_missing = satisfy_coverage(requirement_ids, satisfy_links)
    ver_frac, ver_missing = verify_coverage(requirement_ids, verify_links)
    rollup = rollup_verification_status(child_statuses)
    reasons = []
    if sat_missing:
        reasons.append("unsatisfied: %s" % ", ".join(sat_missing))
    if ver_missing:
        reasons.append("unverified: %s" % ", ".join(ver_missing))
    if rollup != "verified":
        reasons.append("roll-up status %s" % rollup)
    return {
        "satisfy_fraction": sat_frac,
        "verify_fraction": ver_frac,
        "rollup": rollup,
        "verdict": "ready" if not reasons else "gaps",
        "reasons": reasons,
    }

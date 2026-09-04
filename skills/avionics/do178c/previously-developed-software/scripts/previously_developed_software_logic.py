"""Reuse scoping for previously developed software (PDS) under DO-178C.

Pure standard library helpers that turn user-declared facts about a
reused software item into a reuse classification, a delta objective
coverage assessment and a bounded regression scope. No RTCA objective
count tables are reproduced here: the required and covered objective
counts are caller inputs to the coverage function.

Functions:
- classify_pds: reuse class and credit path from origin standard,
  modification state and assurance level match.
- delta_objective_coverage: coverage ratio, delta objective count and
  verdict against a required objective set.
- modified_scope: regression scope from changed code fraction and
  touched interface fraction.
- pds_report: combined reuse scoping report for one item.
"""

UNCHANGED_DIRECT_CREDIT = "unchanged-direct-credit"
MODIFIED_PDS = "modified-pds"
LEVEL_UPGRADE = "level-upgrade"
FULL_COVERAGE = "full-coverage"
DELTA_QUALIFICATION_REQUIRED = "delta-qualification-required"
BOUNDED_REGRESSION = "bounded-regression"
BROAD_REGRESSION = "broad-regression"

CHANGED_FRACTION_LIMIT = 0.2
INTERFACE_FRACTION_LIMIT = 0.5

_UNCHANGED_CREDIT_PATH = (
    "accepted as-is at the target assurance level from existing data; "
    "no delta objectives required"
)
_MODIFIED_CREDIT_PATH = (
    "delta qualification over the changed scope plus affected interfaces"
)
_LEVEL_UPGRADE_PATH = (
    "additional verification at the higher assurance level required, "
    "treating the level gap as the delta scope"
)


def classify_pds(origin_standard, modified, level_meets):
    """Rate the reuse credit of a previously developed item.

    Args:
        origin_standard: declared origin standard id, non-empty string.
        modified: True when the reused item is changed for this use.
        level_meets: True when the item's development assurance level
            meets the target level.

    Returns:
        Dict with reuse_class and credit_path keys.

    Raises:
        ValueError: origin_standard is not a non-empty string.
    """
    if not isinstance(origin_standard, str) or not origin_standard.strip():
        raise ValueError("origin_standard must be a non-empty string")
    if not isinstance(modified, bool) or not isinstance(level_meets, bool):
        raise ValueError("modified and level_meets must be booleans")
    if not level_meets:
        return {"reuse_class": LEVEL_UPGRADE, "credit_path": _LEVEL_UPGRADE_PATH}
    if not modified:
        return {
            "reuse_class": UNCHANGED_DIRECT_CREDIT,
            "credit_path": _UNCHANGED_CREDIT_PATH,
        }
    return {"reuse_class": MODIFIED_PDS, "credit_path": _MODIFIED_CREDIT_PATH}


def delta_objective_coverage(required_objectives, covered_objectives):
    """Assess delta objective coverage against a required objective set.

    Args:
        required_objectives: count of objectives required for the item.
        covered_objectives: count already satisfied by prior data.

    Returns:
        Dict with required, covered, delta_objectives, coverage_ratio
        and verdict keys. coverage_ratio is covered / required rounded
        to 4 decimals; delta_objectives is required - covered; verdict
        is delta-qualification-required while covered is below required
        and full-coverage once they are equal.

    Raises:
        ValueError: required_objectives <= 0, covered_objectives < 0 or
            covered_objectives > required_objectives.
    """
    if required_objectives <= 0:
        raise ValueError("required_objectives must be positive")
    if covered_objectives < 0:
        raise ValueError("covered_objectives must be non-negative")
    if covered_objectives > required_objectives:
        raise ValueError("covered_objectives cannot exceed required_objectives")
    coverage_ratio = round(covered_objectives / required_objectives, 4)
    verdict = (
        FULL_COVERAGE
        if covered_objectives == required_objectives
        else DELTA_QUALIFICATION_REQUIRED
    )
    return {
        "required": required_objectives,
        "covered": covered_objectives,
        "delta_objectives": required_objectives - covered_objectives,
        "coverage_ratio": coverage_ratio,
        "verdict": verdict,
    }


def modified_scope(changed_loc, total_loc, touched_interfaces, total_interfaces):
    """Scope the regression of a modified reused item.

    Args:
        changed_loc: lines of code changed in the reused item.
        total_loc: total lines of code of the reused item.
        touched_interfaces: interfaces of the item that were changed.
        total_interfaces: total interfaces of the item.

    Returns:
        Dict with changed_fraction, interface_fraction and scope keys.
        changed_fraction and interface_fraction are rounded to 4
        decimals; scope is bounded-regression when both stay at or
        under their limits, else broad-regression.

    Raises:
        ValueError: changed_loc < 0, total_loc <= 0, changed_loc >
            total_loc, touched_interfaces < 0 or touched_interfaces >
            total_interfaces.
    """
    if changed_loc < 0:
        raise ValueError("changed_loc must be non-negative")
    if total_loc <= 0:
        raise ValueError("total_loc must be positive")
    if changed_loc > total_loc:
        raise ValueError("changed_loc cannot exceed total_loc")
    if touched_interfaces < 0:
        raise ValueError("touched_interfaces must be non-negative")
    if touched_interfaces > total_interfaces:
        raise ValueError("touched_interfaces cannot exceed total_interfaces")
    changed_fraction = round(changed_loc / total_loc, 4)
    interface_fraction = round(touched_interfaces / total_interfaces, 4)
    raw_changed = changed_loc / total_loc
    raw_interfaces = touched_interfaces / total_interfaces
    if (
        raw_changed <= CHANGED_FRACTION_LIMIT
        and raw_interfaces <= INTERFACE_FRACTION_LIMIT
    ):
        scope = BOUNDED_REGRESSION
    else:
        scope = BROAD_REGRESSION
    return {
        "changed_fraction": changed_fraction,
        "interface_fraction": interface_fraction,
        "scope": scope,
    }


def pds_report(
    origin_standard,
    modified,
    level_meets,
    required_objectives,
    covered_objectives,
    changed_loc,
    total_loc,
    touched_interfaces,
    total_interfaces,
):
    """Build the combined reuse scoping report for one item.

    Delegates to classify_pds, delta_objective_coverage and
    modified_scope and merges their outputs into a single dict.
    """
    classification = classify_pds(origin_standard, modified, level_meets)
    coverage = delta_objective_coverage(required_objectives, covered_objectives)
    scope = modified_scope(
        changed_loc, total_loc, touched_interfaces, total_interfaces
    )
    report = {}
    report.update(classification)
    report.update(coverage)
    report.update(scope)
    return report

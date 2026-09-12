#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 6.3.4 contained/restrained item compliance check
(paraphrase; not a copy of the standard).

Summary (anchor: ECSS-E-ST-32C clause 6.3.4): A spacecraft structural item
held within a vessel or enclosure, or secured by a mechanical restraint,
latch, or tether is subject to a verification sequence. The item is first
placed into one of four categories (container, restrained, latched,
tethered). The load path from the item through its restraint element to the
primary structure is then defined and sized for all design load cases. Factors
of safety on the restraint are checked against clause minimums: limit FoS
must not fall below 1.0 and ultimate FoS must not fall below 1.5. Every
potential failure mode is documented with a consequence category, and items
whose release could be catastrophic or critical must carry a redundant load
path. This module implements the categorization gate, the FoS check, a
restraint margin-of-safety calculator, the failure-mode/consequence check,
the redundancy requirement, and a full per-item compliance evaluator.
"""

import math

VALID_ITEM_TYPES = frozenset(['container', 'restrained', 'latched', 'tethered'])
VALID_CONSEQUENCES = frozenset(['catastrophic', 'critical', 'marginal', 'negligible'])
REDUNDANCY_CONSEQUENCES = frozenset(['catastrophic', 'critical'])

FOS_LIMIT_MIN = 1.0
FOS_ULTIMATE_MIN = 1.5


class ContainedRestrainedError(ValueError):
    pass


def _require_positive(value, name):
    if value <= 0:
        raise ContainedRestrainedError(f"{name} must be > 0, got {value!r}")


def _require_non_negative(value, name):
    if value < 0:
        raise ContainedRestrainedError(f"{name} must be >= 0, got {value!r}")


def categorize_item(item_type):
    """Return item_type if it is a recognized category, else raise ContainedRestrainedError."""
    if item_type not in VALID_ITEM_TYPES:
        raise ContainedRestrainedError(
            f"Unknown item type: {item_type!r}. "
            f"Valid types: {sorted(VALID_ITEM_TYPES)}"
        )
    return item_type


def check_factor_of_safety(fos_limit_actual, fos_ult_actual):
    """Return list of FoS violations.

    Checks limit FoS >= FOS_LIMIT_MIN and ultimate FoS >= FOS_ULTIMATE_MIN.
    An empty list means both checks pass.
    """
    violations = []
    if fos_limit_actual < FOS_LIMIT_MIN:
        violations.append(
            f"limit FoS {fos_limit_actual:.4f} < required {FOS_LIMIT_MIN}"
        )
    if fos_ult_actual < FOS_ULTIMATE_MIN:
        violations.append(
            f"ultimate FoS {fos_ult_actual:.4f} < required {FOS_ULTIMATE_MIN}"
        )
    return violations


def restraint_margin_of_safety(allowable, applied):
    """Margin of safety for a restraint element: MS = allowable / applied - 1.

    Returns math.inf when applied == 0 (no load case).
    Raises ContainedRestrainedError for non-positive allowable or negative applied.
    """
    _require_positive(allowable, "allowable")
    _require_non_negative(applied, "applied")
    if applied == 0.0:
        return math.inf
    return allowable / applied - 1.0


def check_failure_mode_doc(failure_mode_text, consequence):
    """Return list of documentation violations.

    Checks that failure_mode_text is non-empty and consequence is a recognized
    category. Both must be satisfied; each failure produces a separate entry.
    """
    violations = []
    if not failure_mode_text or not failure_mode_text.strip():
        violations.append("failure mode description is missing or empty")
    if consequence not in VALID_CONSEQUENCES:
        violations.append(
            f"unrecognized consequence category: {consequence!r}. "
            f"Valid: {sorted(VALID_CONSEQUENCES)}"
        )
    return violations


def check_redundancy_requirement(consequence, has_redundant_restraint):
    """Return list of redundancy violations.

    Items with catastrophic or critical consequence require a redundant restraint
    path. Items with marginal or negligible consequence have no such requirement.
    """
    if consequence in REDUNDANCY_CONSEQUENCES and not has_redundant_restraint:
        return [
            f"redundant restraint required for consequence category '{consequence}'"
        ]
    return []


def evaluate_item_compliance(item):
    """Evaluate full contained/restrained compliance for one item.

    item dict keys:
      item_id                  str   -- unique identifier
      item_type                str   -- container|restrained|latched|tethered
      load_path_defined        bool  -- True if load path to primary structure is documented
      fos_limit_actual         float -- actual limit factor of safety
      fos_ult_actual           float -- actual ultimate factor of safety
      failure_mode_doc         str   -- description of primary failure mode
      consequence              str   -- catastrophic|critical|marginal|negligible
      has_redundant_restraint  bool  -- True if a backup restraint path exists

    Returns dict with keys:
      item_id    str
      compliant  bool
      violations list[str]
    """
    violations = []

    try:
        categorize_item(item['item_type'])
    except ContainedRestrainedError as exc:
        violations.append(str(exc))

    if not item.get('load_path_defined', False):
        violations.append("load path to primary structure not defined")

    violations.extend(
        check_factor_of_safety(item['fos_limit_actual'], item['fos_ult_actual'])
    )

    violations.extend(
        check_failure_mode_doc(
            item.get('failure_mode_doc', ''),
            item.get('consequence', '')
        )
    )

    violations.extend(
        check_redundancy_requirement(
            item.get('consequence', ''),
            item.get('has_redundant_restraint', False)
        )
    )

    return {
        'item_id': item['item_id'],
        'compliant': len(violations) == 0,
        'violations': violations,
    }


def evaluate_batch(items):
    """Evaluate a list of items and return a batch summary.

    Returns dict with keys:
      results              list of per-item evaluate_item_compliance dicts
      all_compliant        bool
      non_compliant_count  int
    """
    results = [evaluate_item_compliance(item) for item in items]
    return {
        'results': results,
        'all_compliant': all(r['compliant'] for r in results),
        'non_compliant_count': sum(1 for r in results if not r['compliant']),
    }

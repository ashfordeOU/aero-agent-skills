"""Pre-acceptance review of an incoming aerospace purchase order.

Pure stdlib implementation of the AS9100-style order requirements review
(ISO 9001:2015 base with aerospace requirements review): checks the eight
canonical order elements, classifies declared special requirements against
the eight aerospace classes, applies the feasibility gates, and returns the
order acceptance verdict (reject-review, accept-with-fai-condition, accept).

Deterministic: every output derived from input sets is returned sorted.
Input tokens are stripped and lowercased before set comparison; callers pass
the canonical hyphenated slugs exposed by the module constants below.
"""

REQUIRED_ORDER_ELEMENTS = frozenset([
    "product-identification",
    "spec-drawing-revision",
    "quantity-schedule",
    "delivery-date",
    "acceptance-criteria",
    "special-requirements",
    "preservation-packaging",
    "records",
])

SPECIAL_REQUIREMENT_CLASSES = frozenset([
    "fai",
    "delta-fai-notification",
    "key-characteristic-control",
    "counterfeit-free-evidence",
    "special-process-approval",
    "source-verification",
    "certificate-of-conformance",
    "serialization",
])

VERDICT_REJECT_REVIEW = "reject-review"
VERDICT_ACCEPT_WITH_FAI_CONDITION = "accept-with-fai-condition"
VERDICT_ACCEPT = "accept"

BLOCKER_UNQUALIFIED_SPECIAL_PROCESS = "unqualified-special-process"
BLOCKER_UNAPPROVED_MATERIAL = "unapproved-material"
BLOCKER_NO_NDT_CAPABILITY = "no-ndt-capability"
BLOCKER_DELIVERY_EXCEEDS_FROZEN_LEAD_TIME = "delivery-exceeds-frozen-lead-time"

_BLOCKER_CODES = (
    BLOCKER_UNQUALIFIED_SPECIAL_PROCESS,
    BLOCKER_UNAPPROVED_MATERIAL,
    BLOCKER_NO_NDT_CAPABILITY,
    BLOCKER_DELIVERY_EXCEEDS_FROZEN_LEAD_TIME,
)

_SUMMARY_KEYS = (
    "complete",
    "missing",
    "recognized_specials",
    "unrecognized_specials",
    "blockers",
    "fai_pending",
    "verdict",
)


def _normalize_tokens(declared):
    """Return the lowercased, stripped token set, rejecting bad tokens."""
    tokens = set()
    for token in declared:
        if not isinstance(token, str):
            raise ValueError("declared tokens must be strings, got %r" % (token,))
        normalized = token.strip().lower()
        if not normalized:
            raise ValueError("declared tokens must not be empty")
        tokens.add(normalized)
    return tokens


def requirements_completeness(declared):
    """Return (complete, missing) against the 8 canonical order elements.

    complete is True when every canonical element is declared; missing is
    the sorted list of canonical elements absent from the declaration. An
    empty declaration therefore reports all 8 elements missing.
    """
    declared_tokens = _normalize_tokens(declared)
    missing = sorted(REQUIRED_ORDER_ELEMENTS - declared_tokens)
    complete = not missing
    return complete, missing


def classify_special_requirements(declared):
    """Return (recognized, unrecognized) special-requirement classes.

    recognized holds declared tokens that match one of the 8 aerospace
    classes; unrecognized holds every other declared token. Both lists are
    sorted for determinism.
    """
    declared_tokens = _normalize_tokens(declared)
    recognized = sorted(declared_tokens & SPECIAL_REQUIREMENT_CLASSES)
    unrecognized = sorted(declared_tokens - SPECIAL_REQUIREMENT_CLASSES)
    return recognized, unrecognized


def _validate_day(value, name):
    """Return value after checking it is a non-negative real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number of days, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))
    return value


def _validate_gate(value, name):
    """Return value after checking it is a boolean gate result."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a bool, got %r" % (name, value))
    return value


def feasibility_blockers(special_process_qualified, material_approved,
                         ndt_capability_ok, quoted_delivery_days,
                         frozen_lead_time_days):
    """Return the sorted list of feasibility blocker codes that fire.

    Each gate fires independently and only on its own condition: the
    special process must be qualified, the material approved, NDT
    capability available, and the quoted delivery must not exceed the
    frozen lead time. Delivery is a blocker exactly when
    quoted_delivery_days > frozen_lead_time_days (equality is not a
    blocker). Days are non-negative numbers; gate arguments are bools.
    """
    special_process_qualified = _validate_gate(
        special_process_qualified, "special_process_qualified")
    material_approved = _validate_gate(material_approved, "material_approved")
    ndt_capability_ok = _validate_gate(ndt_capability_ok, "ndt_capability_ok")
    quoted_delivery_days = _validate_day(
        quoted_delivery_days, "quoted_delivery_days")
    frozen_lead_time_days = _validate_day(
        frozen_lead_time_days, "frozen_lead_time_days")

    blockers = []
    if not special_process_qualified:
        blockers.append(BLOCKER_UNQUALIFIED_SPECIAL_PROCESS)
    if not material_approved:
        blockers.append(BLOCKER_UNAPPROVED_MATERIAL)
    if not ndt_capability_ok:
        blockers.append(BLOCKER_NO_NDT_CAPABILITY)
    if quoted_delivery_days > frozen_lead_time_days:
        blockers.append(BLOCKER_DELIVERY_EXCEEDS_FROZEN_LEAD_TIME)
    return blockers


def _validate_code_list(values, name):
    """Return values after checking it is a list of non-empty strings."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (name, values))
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s entries must be non-empty strings, got %r"
                             % (name, value))
    return list(values)


def order_acceptance_verdict(missing, unrecognized, blockers, fai_pending):
    """Return the order acceptance verdict under strict precedence.

    Precedence, evaluated in order:
      1. any missing canonical element, any unrecognized special
         requirement, or any feasibility blocker -> "reject-review";
      2. otherwise, fai_pending True -> "accept-with-fai-condition";
      3. otherwise -> "accept".
    A rejected order is returned for review regardless of the other
    conditions; FAI pending only matters once the order is otherwise clean.
    """
    missing = _validate_code_list(missing, "missing")
    unrecognized = _validate_code_list(unrecognized, "unrecognized")
    blockers = _validate_code_list(blockers, "blockers")
    fai_pending = _validate_gate(fai_pending, "fai_pending")

    if missing or unrecognized or blockers:
        return VERDICT_REJECT_REVIEW
    if fai_pending:
        return VERDICT_ACCEPT_WITH_FAI_CONDITION
    return VERDICT_ACCEPT


def order_review_summary(declared_elements, declared_specials,
                         special_process_qualified, material_approved,
                         ndt_capability_ok, quoted_delivery_days,
                         frozen_lead_time_days, fai_pending):
    """Return the convenience review dict with exactly the documented keys.

    Keys: complete, missing, recognized_specials, unrecognized_specials,
    blockers, fai_pending, verdict. The verdict follows
    order_acceptance_verdict precedence on the intermediate results.
    """
    complete, missing = requirements_completeness(declared_elements)
    recognized, unrecognized = classify_special_requirements(declared_specials)
    blockers = feasibility_blockers(special_process_qualified,
                                    material_approved, ndt_capability_ok,
                                    quoted_delivery_days,
                                    frozen_lead_time_days)
    fai_pending = _validate_gate(fai_pending, "fai_pending")
    verdict = order_acceptance_verdict(missing, unrecognized, blockers,
                                       fai_pending)
    return {
        "complete": complete,
        "missing": missing,
        "recognized_specials": recognized,
        "unrecognized_specials": unrecognized,
        "blockers": blockers,
        "fai_pending": fai_pending,
        "verdict": verdict,
    }

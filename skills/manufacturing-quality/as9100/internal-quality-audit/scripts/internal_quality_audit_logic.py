"""Internal quality audit program logic for an AS9100-style QMS.

Pure stdlib, fully deterministic (no RNG). Implements the audit program
mechanics only: risk-based audit scheduling, auditor independence and
competence checks, record sampling, finding categorization, and closure
verification. See the leaf SKILL.md for the pairing leaves that own the
audit focus area clause mapping (quality) and the corrective action
record (corrective-action).

Module constants:
- BASE_INTERVAL_MONTHS = 12.0, the default audit interval.
- RISK_MULTIPLIERS: high risk processes are audited more often, so the
  interval multiplier is smaller than for low risk processes.
"""

import calendar
import math
from datetime import date, datetime

BASE_INTERVAL_MONTHS = 12.0

RISK_MULTIPLIERS = {"low": 1.5, "medium": 1.0, "high": 0.5}

# Confidence anchors for the sample size factor: (confidence, factor).
# 0.90 -> 0.8, 0.95 -> 1.0, 0.99 -> 1.2; other levels interpolate.
_CONFIDENCE_ANCHORS = ((0.90, 0.8), (0.95, 1.0), (0.99, 1.2))

_MAJOR = "major"
_MINOR = "minor"
_OFI = "ofi"


def _confidence_factor(confidence_level):
    """Confidence scaling factor for the sample size.

    Exact anchor levels hit their table factor exactly; other levels
    interpolate linearly between the bracketing anchors (flat outside
    the anchor range, so 0.90 and below use 0.8 and 0.99 and above use
    1.2). The result is rounded to 9 decimals so float products of
    exact anchors stay exact.
    """
    for anchor, factor in _CONFIDENCE_ANCHORS:
        if confidence_level == anchor:
            return factor
    if confidence_level <= 0.90:
        return 0.8
    if confidence_level <= 0.95:
        factor = 0.8 + (confidence_level - 0.90) * 4.0
    elif confidence_level <= 0.99:
        factor = 1.0 + (confidence_level - 0.95) * 5.0
    else:
        factor = 1.2
    return round(factor, 9)


def _add_calendar_months(day, total_months):
    """Add whole calendar months, clamping the day to the month end."""
    month_index = day.year * 12 + (day.month - 1) + total_months
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def audit_due_date(last_audit_date_iso, risk_category,
                   base_interval_months=BASE_INTERVAL_MONTHS):
    """Due date of the next audit as an ISO date string.

    The span is base_interval_months times the risk multiplier for the
    process risk category, added as calendar months with the day clamped
    to the end of the target month. The default constants yield whole
    month spans; a fractional span is rounded to the nearest whole
    calendar month. Raises ValueError for a malformed date or an
    unknown risk category.
    """
    if risk_category not in RISK_MULTIPLIERS:
        raise ValueError("risk_category must be one of: low, medium, high")
    try:
        last_date = datetime.strptime(last_audit_date_iso,
                                      "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("last_audit_date_iso must be an ISO date "
                         "string YYYY-MM-DD") from None
    span_months = base_interval_months * RISK_MULTIPLIERS[risk_category]
    total_months = int(round(span_months))
    return _add_calendar_months(last_date, total_months).isoformat()


def auditor_independent(auditor_name, area_owner_name, independence_ok=True):
    """Check that the auditor is not the owner of the audited area.

    Returns {independent: bool, reason}. Independence fails when the
    auditor name matches the area owner name (compared case
    insensitively after trimming) or when a conflict is declared via
    independence_ok=False.
    """
    auditor = auditor_name.strip().lower() if auditor_name else ""
    owner = area_owner_name.strip().lower() if area_owner_name else ""
    if auditor == owner and auditor != "":
        return {
            "independent": False,
            "reason": ("the auditor is the owner of the audited area, "
                       "so independence fails"),
        }
    if not independence_ok:
        return {
            "independent": False,
            "reason": "a conflict of interest is declared for the assignment",
        }
    return {
        "independent": True,
        "reason": "the auditor is not the area owner and no conflict is declared",
    }


def auditor_competent(qualifications, audit_scope_areas, required_areas=None):
    """Check the auditor qualification list against the required areas.

    True when every required area appears in the auditor qualification
    list (case insensitive substring match). When required_areas is not
    given it falls back to the audit scope areas, so a two argument
    call checks the whole assigned scope. Raises ValueError when the
    effective required area list is empty.
    """
    if required_areas is None:
        required_areas = audit_scope_areas
    if not required_areas:
        raise ValueError("required_areas must not be empty")
    quals = [q.strip().lower() for q in (qualifications or [])]
    for required in required_areas:
        needle = required.strip().lower()
        if not any(needle in q for q in quals):
            return False
    return True


def audit_sample_size(lot_size, confidence_level=0.95):
    """Sample size for a records audit: ceil(sqrt(lot_size) * factor).

    The square root sample is scaled by the confidence factor (1.0 at
    0.95, 1.2 at 0.99, 0.8 at 0.90, interpolated in between) and rounded
    up, with a floor of 1. Raises ValueError for lot_size below 1 or a
    confidence level outside [0.5, 0.999].
    """
    if lot_size < 1:
        raise ValueError("lot_size must be at least 1")
    if not 0.5 <= confidence_level <= 0.999:
        raise ValueError("confidence_level must be within [0.5, 0.999]")
    factor = _confidence_factor(confidence_level)
    size = math.ceil(round(math.sqrt(lot_size) * factor, 9))
    return max(1, size)


def classify_finding(impact_severity, containment_required, systemic):
    """Categorize an audit finding on the 1-5 impact severity scale.

    "major" when impact_severity >= 4 or containment_required;
    "minor" when impact_severity >= 2; otherwise "ofi" (opportunity
    for improvement). A systemic finding escalates minor to major.
    Raises ValueError when impact_severity is outside 1-5.
    """
    if not 1 <= impact_severity <= 5:
        raise ValueError("impact_severity must be an integer in 1-5")
    if impact_severity >= 4 or containment_required:
        return _MAJOR
    if impact_severity >= 2:
        return _MAJOR if systemic else _MINOR
    return _OFI


def verify_closure(corrective_action_taken, root_cause_stated,
                   effectiveness_check):
    """True only when all three closure evidence elements are set."""
    return bool(corrective_action_taken and root_cause_stated
                and effectiveness_check)


def internal_audit_review(last_audit_date_iso, risk_category, lot_size,
                          auditor_name, area_owner_name, required_areas,
                          qualifications, impact_severity,
                          containment_required, systemic,
                          corrective_action_taken, root_cause_stated,
                          effectiveness_check,
                          base_interval_months=BASE_INTERVAL_MONTHS,
                          confidence_level=0.95):
    """Convenience chain over the audit program checks.

    Returns exactly {due_date, interval_months, auditor_independent,
    auditor_competent, sample_size, finding_classification,
    closure_verified}. interval_months is the raw span product
    base_interval_months * RISK_MULTIPLIERS[risk_category].
    """
    if risk_category not in RISK_MULTIPLIERS:
        raise ValueError("risk_category must be one of: low, medium, high")
    interval_months = base_interval_months * RISK_MULTIPLIERS[risk_category]
    return {
        "due_date": audit_due_date(last_audit_date_iso, risk_category,
                                   base_interval_months),
        "interval_months": interval_months,
        "auditor_independent": auditor_independent(auditor_name,
                                                   area_owner_name),
        "auditor_competent": auditor_competent(qualifications,
                                               required_areas),
        "sample_size": audit_sample_size(lot_size, confidence_level),
        "finding_classification": classify_finding(impact_severity,
                                                   containment_required,
                                                   systemic),
        "closure_verified": verify_closure(corrective_action_taken,
                                           root_cause_stated,
                                           effectiveness_check),
    }

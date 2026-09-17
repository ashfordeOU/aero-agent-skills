"""Receiving quality control entry point for class 2 EEE parts.

Anchor: ECSS-Q-ST-60C clause 5.5.1 (the entry point to the control measures
applied to class 2 parts once they have been received). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the lot may be booked in at all: an untraceable identity, an
   empty quantity, a missing conformity certificate or an unstated date code
   stops the lot before any control activity is opened.
2. Derive the baseline control activities the lot owes from its package style,
   temperature duty, radiation duty, source history and age since manufacture.
3. Decide whether the delivered procurement flow reaches the flow the
   application demands; when it does not, the project owes the upscreening
   delta itself.
4. Credit back the activities the manufacturer's own accepted evidence already
   carries, which is the difference between class 2 and the highest assurance
   class, but only while that evidence is current, the source is qualified and
   no upscreening delta is owed.
5. Order the remaining activities so every non-destructive activity is closed
   before a destructive one consumes parts, and size each sample from the
   delivered quantity.
6. Return the outstanding activities, the coverage fraction and one entry
   disposition: controls-complete, controls-outstanding or lot-not-admissible.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "CONTROL_ACTIVITIES",
    "BASELINE_OWED",
    "CREDITABLE_ACTIVITIES",
    "SAMPLE_PLANS",
    "FULL_LOT_ACTIVITIES",
    "FLOW_GRADES",
    "UPSCREENING_ACTIVITIES",
    "AGE_TRIGGER_MONTHS",
    "EVIDENCE_VALIDITY_MONTHS",
    "lot_admissibility",
    "upscreening_required",
    "baseline_controls",
    "credited_controls",
    "required_controls",
    "ordered_control_plan",
    "sample_size",
    "outstanding_controls",
    "coverage_fraction",
    "entry_disposition",
    "plan_class_2_receiving_controls",
]

# Coverage is a quotient of small counts, and both the age trigger and the
# evidence validity window are comparisons of measured months; a case sitting
# exactly on a bound can land a few ULP on the wrong side. Absorb the
# representation error here, never by moving the bound itself.
BOUND_TOLERANCE = 1e-9

# Every receiving control activity, in the order it may be performed, with a
# flag saying whether it consumes the parts it touches. Non-destructive work
# comes first so a lot is never reduced before the cheap evidence is in.
CONTROL_ACTIVITIES = (
    ("certificate-of-conformity-review", False),
    ("external-visual-examination", False),
    ("electrical-measurement-at-room-temperature", False),
    ("electrical-measurement-at-temperature-extremes", False),
    ("particle-impact-noise-detection", False),
    ("solderability-verification", True),
    ("radiation-lot-verification", True),
    ("destructive-physical-analysis", True),
)

_ACTIVITY_ORDER = {name: index for index, (name, _d) in enumerate(CONTROL_ACTIVITIES)}
_DESTRUCTIVE = {name: destructive for name, destructive in CONTROL_ACTIVITIES}

# Activities a class 2 lot owes whatever its history, before any credit.
BASELINE_OWED = (
    "certificate-of-conformity-review",
    "external-visual-examination",
    "electrical-measurement-at-room-temperature",
)

# Activities the manufacturer's own accepted evidence can carry for a class 2
# lot. The conformity review, the radiation verification and the destructive
# analysis stay with the project whatever the manufacturer supplies.
CREDITABLE_ACTIVITIES = (
    "external-visual-examination",
    "electrical-measurement-at-room-temperature",
    "electrical-measurement-at-temperature-extremes",
    "particle-impact-noise-detection",
    "solderability-verification",
)

# Sample-size bands by lot quantity, as (upper bound of the band inclusive,
# devices drawn). The last band applies to everything larger. A class 2 plan
# draws fewer devices than the highest assurance class because the
# manufacturer's flow carries part of the evidence.
SAMPLE_PLANS = {
    "destructive-physical-analysis": ((25, 1), (100, 2), (500, 3), (None, 5)),
    "solderability-verification": ((100, 3), (1000, 4), (None, 6)),
    "radiation-lot-verification": ((200, 4), (2000, 6), (None, 8)),
}

# Activities performed on the whole delivered quantity rather than a sample.
FULL_LOT_ACTIVITIES = (
    "certificate-of-conformity-review",
    "external-visual-examination",
    "electrical-measurement-at-room-temperature",
    "electrical-measurement-at-temperature-extremes",
    "particle-impact-noise-detection",
)

# Procurement flow grades, weakest first. A part delivered below the grade the
# application demands has to be upscreened by the project.
FLOW_GRADES = ("commercial", "automotive", "military", "space")

_FLOW_RANK = {name: index for index, name in enumerate(FLOW_GRADES)}

# The delta the project owes when it upscreens a lot itself.
UPSCREENING_ACTIVITIES = (
    "electrical-measurement-at-temperature-extremes",
    "destructive-physical-analysis",
)

# Age at which a lot owes a solderability verification before it is used.
AGE_TRIGGER_MONTHS = 24.0

# Age past which manufacturer evidence no longer carries a control activity.
EVIDENCE_VALIDITY_MONTHS = 36.0


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _require_count(value, label):
    """Return a validated positive integer or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_mapping(value, label):
    """Return a validated mapping or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, value))
    return value


def _require_flow(value, label):
    """Return a validated procurement flow grade or raise."""
    name = _require_text(value, label).casefold()
    if name not in _FLOW_RANK:
        raise ValueError(
            "%s must be one of %r, got %r" % (label, list(FLOW_GRADES), value)
        )
    return name


def _past_bound(value, bound):
    """Return True only when value is clear of bound by more than the tolerance."""
    return value > bound and not math.isclose(
        value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )


def lot_admissibility(lot):
    """Return the reasons a received class 2 lot cannot enter the control plan.

    An empty list means the lot may be booked in. The reasons are ordered from
    identity outwards, because a lot nobody can name is not a sampling problem.
    """
    _require_mapping(lot, "lot")
    reasons = []
    identity = lot.get("lot_code")
    if not isinstance(identity, str) or not identity.strip():
        reasons.append("lot-identity-not-traceable")
    quantity = lot.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        reasons.append("delivered-quantity-not-stated")
    date_code = lot.get("date_code")
    if not isinstance(date_code, str) or not date_code.strip():
        reasons.append("date-code-not-stated")
    if not _require_flag(lot.get("conformity_certificate", False),
                         "conformity_certificate"):
        reasons.append("conformity-certificate-missing")
    return reasons


def upscreening_required(lot):
    """Return True when the delivered flow sits below the flow demanded."""
    _require_mapping(lot, "lot")
    delivered = _require_flow(lot.get("procured_flow", "space"), "procured_flow")
    demanded = _require_flow(lot.get("required_flow", "space"), "required_flow")
    return _FLOW_RANK[delivered] < _FLOW_RANK[demanded]


def baseline_controls(lot):
    """Return the activities a class 2 lot owes before any manufacturer credit.

    lot keys read here: hermetic_package, temperature_extremes_duty,
    radiation_duty, qualified_source, months_since_manufacture, plus the
    procured_flow and required_flow pair that decides the upscreening delta.
    """
    _require_mapping(lot, "lot")
    owed = set(BASELINE_OWED)
    if _require_flag(lot.get("hermetic_package", False), "hermetic_package"):
        owed.add("particle-impact-noise-detection")
    if _require_flag(lot.get("temperature_extremes_duty", False),
                     "temperature_extremes_duty"):
        owed.add("electrical-measurement-at-temperature-extremes")
    if _require_flag(lot.get("radiation_duty", False), "radiation_duty"):
        owed.add("radiation-lot-verification")
    if not _require_flag(lot.get("qualified_source", True), "qualified_source"):
        owed.add("solderability-verification")
        owed.add("destructive-physical-analysis")
    months = _require_number(lot.get("months_since_manufacture", 0.0),
                             "months_since_manufacture")
    if _past_bound(months, AGE_TRIGGER_MONTHS):
        owed.add("solderability-verification")
    if upscreening_required(lot):
        owed.update(UPSCREENING_ACTIVITIES)
    return ordered_control_plan(owed)


def credited_controls(lot):
    """Return the owed activities the manufacturer's evidence already carries.

    Credit is withdrawn entirely when the source is not qualified, when the
    evidence is older than the validity window, or when the lot owes an
    upscreening delta the manufacturer never performed.
    """
    _require_mapping(lot, "lot")
    evidence = lot.get("manufacturer_evidence", [])
    if not isinstance(evidence, (list, tuple, set, frozenset)):
        raise ValueError("manufacturer_evidence must be a sequence or set")
    if not _require_flag(lot.get("qualified_source", True), "qualified_source"):
        return []
    evidence_age = _require_number(lot.get("evidence_age_months", 0.0),
                                   "evidence_age_months")
    if _past_bound(evidence_age, EVIDENCE_VALIDITY_MONTHS):
        return []
    if upscreening_required(lot):
        return []
    owed = set(baseline_controls(lot))
    granted = set()
    for item in evidence:
        name = _require_text(item, "manufacturer evidence").casefold()
        if name not in _ACTIVITY_ORDER:
            raise ValueError(
                "unknown control activity %r; expected one of %r"
                % (item, list(_ACTIVITY_ORDER))
            )
        if name in CREDITABLE_ACTIVITIES and name in owed:
            granted.add(name)
    return ordered_control_plan(granted)


def required_controls(lot):
    """Return the activities the project itself still owes on a class 2 lot."""
    owed = set(baseline_controls(lot))
    owed -= set(credited_controls(lot))
    return ordered_control_plan(owed)


def ordered_control_plan(activities):
    """Return the activities in performance order, non-destructive first."""
    if not isinstance(activities, (list, tuple, set, frozenset)):
        raise ValueError("activities must be a sequence or set")
    names = []
    for item in activities:
        name = _require_text(item, "control activity").casefold()
        if name not in _ACTIVITY_ORDER:
            raise ValueError(
                "unknown control activity %r; expected one of %r"
                % (item, list(_ACTIVITY_ORDER))
            )
        if name in names:
            raise ValueError("control activity %r listed twice" % name)
        names.append(name)
    return sorted(names, key=lambda name: (_DESTRUCTIVE[name], _ACTIVITY_ORDER[name]))


def sample_size(activity, lot_quantity):
    """Return the devices a control activity draws from the delivered lot.

    A full-lot activity returns the whole delivered quantity. A sampled
    activity returns its banded sample, never more than the lot holds.
    """
    name = _require_text(activity, "activity").casefold()
    if name not in _ACTIVITY_ORDER:
        raise ValueError(
            "unknown control activity %r; expected one of %r"
            % (activity, list(_ACTIVITY_ORDER))
        )
    quantity = _require_count(lot_quantity, "lot_quantity")
    if name in FULL_LOT_ACTIVITIES:
        return quantity
    for upper, drawn in SAMPLE_PLANS[name]:
        if upper is None or quantity <= upper:
            return min(drawn, quantity)
    raise ValueError("no sample band covers lot_quantity %d" % quantity)


def outstanding_controls(owed, closed):
    """Return the owed activities not yet closed, in performance order."""
    owed_names = ordered_control_plan(owed)
    if not isinstance(closed, (list, tuple, set, frozenset)):
        raise ValueError("closed must be a sequence or set")
    done = set()
    for item in closed:
        name = _require_text(item, "closed activity").casefold()
        if name not in _ACTIVITY_ORDER:
            raise ValueError(
                "unknown control activity %r; expected one of %r"
                % (item, list(_ACTIVITY_ORDER))
            )
        done.add(name)
    return [name for name in owed_names if name not in done]


def coverage_fraction(owed, closed):
    """Return the fraction of the project-owed plan already closed."""
    owed_names = ordered_control_plan(owed)
    if not owed_names:
        raise ValueError("owed must name at least one control activity")
    remaining = outstanding_controls(owed_names, closed)
    return (len(owed_names) - len(remaining)) / float(len(owed_names))


def entry_disposition(admissibility_reasons, remaining):
    """Return the entry disposition implied by the plan state."""
    if not isinstance(admissibility_reasons, (list, tuple)):
        raise ValueError("admissibility_reasons must be a sequence")
    if not isinstance(remaining, (list, tuple)):
        raise ValueError("remaining must be a sequence")
    if admissibility_reasons:
        return "lot-not-admissible"
    if remaining:
        return "controls-outstanding"
    return "controls-complete"


def plan_class_2_receiving_controls(lot):
    """Open the clause 5.5.1 control plan for one received class 2 lot.

    lot keys: lot_code, quantity, date_code, conformity_certificate, and the
    optional hermetic_package, temperature_extremes_duty, radiation_duty,
    qualified_source, months_since_manufacture, procured_flow, required_flow,
    manufacturer_evidence and controls_closed.
    """
    _require_mapping(lot, "lot")
    reasons = lot_admissibility(lot)
    baseline = baseline_controls(lot)
    credited = credited_controls(lot)
    owed = required_controls(lot)
    closed = lot.get("controls_closed", [])
    remaining = outstanding_controls(owed, closed)
    coverage = coverage_fraction(owed, closed) if owed else 1.0
    if reasons:
        samples = {}
    else:
        samples = {name: sample_size(name, lot["quantity"]) for name in owed}
    disposition = entry_disposition(reasons, remaining)
    return {
        "admissibility_reasons": reasons,
        "admissible": not reasons,
        "baseline_plan": baseline,
        "credited_to_manufacturer": credited,
        "control_plan": owed,
        "upscreening_owed": upscreening_required(lot),
        "destructive_activities": [name for name in owed if _DESTRUCTIVE[name]],
        "sample_sizes": samples,
        "outstanding_controls": remaining,
        "coverage_fraction": coverage,
        "disposition": disposition,
        "ready_for_release": disposition == "controls-complete",
    }

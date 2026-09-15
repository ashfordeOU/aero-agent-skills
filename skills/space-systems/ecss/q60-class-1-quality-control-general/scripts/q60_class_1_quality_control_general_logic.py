"""Receiving quality control entry point for class 1 EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.5.1 (the entry point to the control measures
applied to class 1 parts once they have been received). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the lot is admissible at all: an untraceable identity, an
   empty quantity or a rejected data package stops the lot at the door before
   any control activity is opened.
2. Derive the control activities the lot owes from its package style, source
   history, radiation duty and age since manufacture.
3. Order the owed activities so every non-destructive activity is closed
   before a destructive one consumes parts.
4. Size the sample each activity needs from the lot quantity.
5. Compare the activities already closed against the owed set and return the
   outstanding ones and the coverage fraction.
6. Return one entry disposition: controls-complete, controls-outstanding, or
   lot-not-admissible.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "CONTROL_ACTIVITIES",
    "ALWAYS_OWED",
    "SAMPLE_PLANS",
    "FULL_LOT_ACTIVITIES",
    "AGE_TRIGGER_MONTHS",
    "lot_admissibility",
    "required_controls",
    "ordered_control_plan",
    "sample_size",
    "outstanding_controls",
    "coverage_fraction",
    "entry_disposition",
    "plan_class_1_receiving_controls",
]

# Coverage is a quotient of small counts and the age trigger is a comparison
# of measured months; a case sitting exactly on a bound can land a few ULP on
# the wrong side. Absorb the representation error here, never by moving the
# bound itself.
BOUND_TOLERANCE = 1e-9

# Every receiving control activity, in the order it may be performed, with a
# flag saying whether it consumes the parts it touches. Non-destructive work
# comes first so a lot is never reduced before the cheap evidence is in.
CONTROL_ACTIVITIES = (
    ("data-package-review", False),
    ("external-visual-examination", False),
    ("particle-impact-noise-detection", False),
    ("electrical-measurement-at-temperature-extremes", False),
    ("radiation-lot-verification", True),
    ("solderability-verification", True),
    ("destructive-physical-analysis", True),
)

_ACTIVITY_ORDER = {name: index for index, (name, _d) in enumerate(CONTROL_ACTIVITIES)}
_DESTRUCTIVE = {name: destructive for name, destructive in CONTROL_ACTIVITIES}

# Activities a class 1 lot owes whatever its history.
ALWAYS_OWED = (
    "data-package-review",
    "external-visual-examination",
    "electrical-measurement-at-temperature-extremes",
    "destructive-physical-analysis",
)

# Sample-size bands by lot quantity, as (upper bound of the band inclusive,
# devices drawn). The last band applies to everything larger.
SAMPLE_PLANS = {
    "destructive-physical-analysis": ((10, 2), (50, 3), (200, 5), (1000, 8), (None, 10)),
    "solderability-verification": ((50, 3), (500, 5), (None, 8)),
    "radiation-lot-verification": ((100, 5), (1000, 10), (None, 12)),
}

# Activities performed on the whole delivered quantity rather than a sample.
FULL_LOT_ACTIVITIES = (
    "data-package-review",
    "external-visual-examination",
    "particle-impact-noise-detection",
    "electrical-measurement-at-temperature-extremes",
)

# Age at which a lot owes a solderability verification before it is used.
AGE_TRIGGER_MONTHS = 24.0


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


def lot_admissibility(lot):
    """Return the reasons a received lot cannot enter the control plan.

    An empty list means the lot may be booked in. The reasons are ordered
    from identity outwards, because a lot nobody can name is not a sampling
    problem.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    reasons = []
    identity = lot.get("lot_code")
    if not isinstance(identity, str) or not identity.strip():
        reasons.append("lot-identity-not-traceable")
    quantity = lot.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        reasons.append("delivered-quantity-not-stated")
    if not _require_flag(lot.get("data_package_accepted", False),
                         "data_package_accepted"):
        reasons.append("data-package-not-accepted")
    return reasons


def required_controls(lot):
    """Return the control activities a received class 1 lot owes.

    lot keys read here: hermetic_package, qualified_source,
    radiation_duty and months_since_manufacture.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    owed = set(ALWAYS_OWED)
    if _require_flag(lot.get("hermetic_package", False), "hermetic_package"):
        owed.add("particle-impact-noise-detection")
    if not _require_flag(lot.get("qualified_source", True), "qualified_source"):
        owed.add("solderability-verification")
    if _require_flag(lot.get("radiation_duty", False), "radiation_duty"):
        owed.add("radiation-lot-verification")
    months = _require_number(lot.get("months_since_manufacture", 0.0),
                             "months_since_manufacture")
    past_age_trigger = months > AGE_TRIGGER_MONTHS and not math.isclose(
        months, AGE_TRIGGER_MONTHS, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    if past_age_trigger:
        owed.add("solderability-verification")
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
    """Return the fraction of the owed control plan already closed."""
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


def plan_class_1_receiving_controls(lot):
    """Open the clause 4.5.1 control plan for one received class 1 lot.

    lot keys: lot_code, quantity, data_package_accepted, and the optional
    hermetic_package, qualified_source, radiation_duty,
    months_since_manufacture and controls_closed.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    reasons = lot_admissibility(lot)
    owed = required_controls(lot)
    closed = lot.get("controls_closed", [])
    remaining = outstanding_controls(owed, closed)
    coverage = coverage_fraction(owed, closed)
    if reasons:
        samples = {}
    else:
        samples = {name: sample_size(name, lot["quantity"]) for name in owed}
    disposition = entry_disposition(reasons, remaining)
    return {
        "admissibility_reasons": reasons,
        "admissible": not reasons,
        "control_plan": owed,
        "destructive_activities": [name for name in owed if _DESTRUCTIVE[name]],
        "sample_sizes": samples,
        "outstanding_controls": remaining,
        "coverage_fraction": coverage,
        "disposition": disposition,
        "ready_for_release": disposition == "controls-complete",
    }

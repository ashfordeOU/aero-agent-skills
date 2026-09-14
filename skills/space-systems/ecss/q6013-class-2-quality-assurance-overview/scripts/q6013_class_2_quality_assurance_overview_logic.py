"""Quality assurance duties owed at the intermediate commercial EEE class.

Anchor: ECSS-Q-ST-60-13C clause 5.5.1 (the quality assurance duties that
apply to commercial EEE parts procured at the intermediate assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the assurance policy: the two coverage floors, the plan
   revalidation interval, and whether an escalation route is demanded of an
   embedded quality function.
2. Validate every declared duty record and dispose it as established, waived,
   or short of an owner, a procedure reference or an evidence reference.
3. Test each waiver: a duty the class makes mandatory cannot be waived at
   all, and a discretionary duty may be waived only against a recorded
   rationale and an approval.
4. Take two coverage figures over the duty catalogue: the plain coverage that
   counts an admissibly waived duty as disposed, and the evidenced coverage
   that counts only duties carrying real evidence.
5. Read the quality plan: it must exist, and it must have been revalidated
   inside the declared interval.
6. Read independence: a quality function reporting inside a function it
   grades is tolerated at this class only where an escalation route is
   declared.
7. Close on one verdict naming the first blocking condition, or on the
   intermediate class being met.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "QA_DUTIES",
    "MANDATORY_DUTIES",
    "DISCRETIONARY_DUTIES",
    "GRADED_FUNCTIONS",
    "DUTY_STATES",
    "DEFAULT_POLICY",
    "validate_policy",
    "waiver_admissible",
    "duty_state",
    "dispose_duties",
    "coverage_figures",
    "plan_reference_state",
    "independence_state",
    "quality_assurance_verdict",
    "assess_class_two_quality_assurance",
]

# Coverage figures are quotients of small integers, so a count that lands
# exactly on a floor can fall a few ULP short of it. Absorb that here, never
# by lowering the floor.
BOUND_TOLERANCE = 1e-9

# The quality assurance duties the intermediate class recognises, with the
# ones it will not let a programme drop marked mandatory.
QA_DUTIES = {
    "procurement-document-review": True,
    "incoming-inspection-control": True,
    "nonconformance-processing": True,
    "traceability-and-lot-identity": True,
    "alert-and-advisory-dissemination": True,
    "quality-records-retention": True,
    "supplier-surveillance": False,
    "process-and-handling-audit": False,
}

MANDATORY_DUTIES = tuple(sorted(d for d, m in QA_DUTIES.items() if m))
DISCRETIONARY_DUTIES = tuple(sorted(d for d, m in QA_DUTIES.items() if not m))

# Functions whose own output the quality function grades. Reporting inside
# one of them is the embedding this clause prices.
GRADED_FUNCTIONS = ("design", "production", "procurement", "integration")

DUTY_STATES = (
    "established",
    "waived",
    "evidence-missing",
    "procedure-missing",
    "unowned",
)

DEFAULT_POLICY = {
    "plain_floor": 1.0,
    "evidenced_floor": 0.75,
    "plan_revalidation_days": 730,
    "escalation_route_required": True,
}


def _require_text(value, label):
    """Return a stripped non-empty string or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _optional_text(value):
    """Return a stripped string, or None when the field is blank or absent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("reference fields must be strings, got %r" % (value,))
    stripped = value.strip()
    return stripped or None


def _require_fraction(value, label):
    """Return a validated fraction in the closed unit interval."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %g" % (label, number))
    return number


def _require_date(value, label):
    """Return a date parsed from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s %r is not an ISO yyyy-mm-dd date" % (label, value))
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def validate_policy(policy=None):
    """Return a validated assurance policy, filled from the default."""
    merged = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping, got %r" % (policy,))
        unknown = sorted(set(policy) - set(DEFAULT_POLICY))
        if unknown:
            raise ValueError("policy carries unknown keys %r" % unknown)
        merged.update(policy)
    plain = _require_fraction(merged["plain_floor"], "plain_floor")
    evidenced = _require_fraction(merged["evidenced_floor"], "evidenced_floor")
    if evidenced > plain and not math.isclose(
        evidenced, plain, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    ):
        raise ValueError(
            "evidenced_floor %g cannot sit above plain_floor %g" % (evidenced, plain)
        )
    days = merged["plan_revalidation_days"]
    if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
        raise ValueError("plan_revalidation_days must be a positive integer, got %r" % (days,))
    route = merged["escalation_route_required"]
    if not isinstance(route, bool):
        raise ValueError("escalation_route_required must be a boolean, got %r" % (route,))
    return {
        "plain_floor": plain,
        "evidenced_floor": evidenced,
        "plan_revalidation_days": days,
        "escalation_route_required": route,
    }


def waiver_admissible(duty, waiver):
    """Return whether a waiver against a duty may be accepted, and why not.

    A duty the class makes mandatory is never waivable. A discretionary duty
    is waivable only against a recorded rationale and a named approval.
    """
    key = _require_text(duty, "duty").lower()
    if key not in QA_DUTIES:
        raise ValueError("duty %r is not one of %r" % (duty, sorted(QA_DUTIES)))
    if waiver is None:
        return {"admissible": False, "reason": "no waiver declared"}
    if not isinstance(waiver, dict):
        raise ValueError("waiver must be a mapping, got %r" % (waiver,))
    if QA_DUTIES[key]:
        return {"admissible": False, "reason": "duty is mandatory at this class"}
    rationale = _optional_text(waiver.get("rationale"))
    approval = _optional_text(waiver.get("approval"))
    if rationale is None:
        return {"admissible": False, "reason": "waiver carries no recorded rationale"}
    if approval is None:
        return {"admissible": False, "reason": "waiver carries no named approval"}
    return {"admissible": True, "reason": "waiver recorded and approved"}


def duty_state(entry):
    """Return the disposition of one declared duty record.

    The first missing element is the one reported: an unowned duty is not
    also graded on the procedure it does not have.
    """
    if not isinstance(entry, dict):
        raise ValueError("each duty record must be a mapping, got %r" % (entry,))
    duty = _require_text(entry.get("duty"), "duty").lower()
    if duty not in QA_DUTIES:
        raise ValueError("duty %r is not one of %r" % (duty, sorted(QA_DUTIES)))
    waiver = entry.get("waiver")
    if waiver is not None:
        verdict = waiver_admissible(duty, waiver)
        if verdict["admissible"]:
            return {"duty": duty, "state": "waived", "detail": verdict["reason"]}
        return {"duty": duty, "state": "unowned", "detail": verdict["reason"]}
    owner = _optional_text(entry.get("owner"))
    if owner is None:
        return {"duty": duty, "state": "unowned", "detail": "no owner named"}
    if _optional_text(entry.get("procedure_ref")) is None:
        return {"duty": duty, "state": "procedure-missing", "detail": "no procedure reference"}
    if _optional_text(entry.get("evidence_ref")) is None:
        return {"duty": duty, "state": "evidence-missing", "detail": "no evidence reference"}
    return {"duty": duty, "state": "established", "detail": "owner, procedure and evidence named"}


def dispose_duties(declared):
    """Return the disposition of every duty in the catalogue.

    A duty the programme never declared is reported unowned rather than
    dropped, so the catalogue length always matches the report length.
    """
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared duties must be a sequence")
    by_duty = {}
    for entry in declared:
        state = duty_state(entry)
        if state["duty"] in by_duty:
            raise ValueError("duty %r is declared twice" % state["duty"])
        by_duty[state["duty"]] = state
    report = []
    for duty in sorted(QA_DUTIES):
        report.append(
            by_duty.get(
                duty,
                {"duty": duty, "state": "unowned", "detail": "duty not declared"},
            )
        )
    return report


def coverage_figures(report):
    """Return the plain and evidenced coverage over the duty catalogue."""
    if not isinstance(report, (list, tuple)) or not report:
        raise ValueError("report must be a non-empty sequence of dispositions")
    total = 0
    established = 0
    disposed = 0
    for item in report:
        if not isinstance(item, dict) or "state" not in item:
            raise ValueError("each disposition must carry a state")
        if item["state"] not in DUTY_STATES:
            raise ValueError("state %r is not one of %r" % (item["state"], DUTY_STATES))
        total += 1
        if item["state"] == "established":
            established += 1
            disposed += 1
        elif item["state"] == "waived":
            disposed += 1
    return {
        "plain_coverage": disposed / total,
        "evidenced_coverage": established / total,
        "established": established,
        "disposed": disposed,
        "total": total,
    }


def plan_reference_state(plan_ref, plan_issue_date, review_date, revalidation_days):
    """Return whether the quality plan exists and is still inside its interval."""
    reference = _optional_text(plan_ref)
    if reference is None:
        return {"present": False, "age_days": None, "revalidation_overdue": True}
    issued = _require_date(plan_issue_date, "plan_issue_date")
    review = _require_date(review_date, "review_date")
    if review < issued:
        raise ValueError("review_date %s precedes plan_issue_date %s" % (review, issued))
    if not isinstance(revalidation_days, int) or isinstance(revalidation_days, bool):
        raise ValueError("revalidation_days must be an integer, got %r" % (revalidation_days,))
    if revalidation_days <= 0:
        raise ValueError("revalidation_days must be positive, got %d" % revalidation_days)
    age = (review - issued).days
    return {
        "present": True,
        "reference": reference,
        "age_days": age,
        "revalidation_overdue": age > revalidation_days,
    }


def independence_state(reports_to, escalation_route, route_required=True):
    """Return whether the quality function is embedded and whether that is paid for."""
    line = _require_text(reports_to, "reports_to").lower()
    route = _optional_text(escalation_route)
    embedded = line in GRADED_FUNCTIONS
    if not isinstance(route_required, bool):
        raise ValueError("route_required must be a boolean, got %r" % (route_required,))
    satisfied = True
    if embedded and route_required and route is None:
        satisfied = False
    return {
        "reports_to": line,
        "embedded": embedded,
        "escalation_route": route,
        "satisfied": satisfied,
    }


REQUIRED_KEYS = ("programme", "duties", "reports_to", "review_date")


def quality_assurance_verdict(state):
    """Return the verdict implied by an assembled assurance state."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping")
    for key in ("mandatory_waived", "mandatory_unassigned", "plan", "independence", "coverage", "policy"):
        if key not in state:
            raise ValueError("state missing required key '%s'" % key)
    if not state["plan"]["present"]:
        return "quality-assurance-not-established"
    if state["mandatory_waived"]:
        return "mandatory-duty-waived"
    if state["mandatory_unassigned"]:
        return "mandatory-duty-unassigned"
    coverage = state["coverage"]
    policy = state["policy"]
    for figure, floor in (
        ("plain_coverage", "plain_floor"),
        ("evidenced_coverage", "evidenced_floor"),
    ):
        value = coverage[figure]
        bound = policy[floor]
        if value < bound and not math.isclose(
            value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
        ):
            return "duty-coverage-short"
    if not state["independence"]["satisfied"]:
        return "escalation-route-not-declared"
    if state["plan"]["revalidation_overdue"]:
        return "plan-revalidation-overdue"
    return "quality-assurance-meets-class-two"


def assess_class_two_quality_assurance(record):
    """Grade one programme quality assurance arrangement against clause 5.5.1.

    record keys: programme, duties, reports_to, review_date, and optionally
    policy, quality_plan_ref, plan_issue_date and escalation_route.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in REQUIRED_KEYS:
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    programme = _require_text(record["programme"], "programme")
    policy = validate_policy(record.get("policy"))
    report = dispose_duties(record["duties"])
    coverage = coverage_figures(report)

    declared_waivers = {}
    if isinstance(record["duties"], (list, tuple)):
        for entry in record["duties"]:
            if isinstance(entry, dict) and entry.get("waiver") is not None:
                name = _optional_text(entry.get("duty"))
                if name:
                    declared_waivers[name.lower()] = entry["waiver"]
    mandatory_waived = sorted(d for d in declared_waivers if QA_DUTIES.get(d) is True)
    mandatory_unassigned = sorted(
        item["duty"]
        for item in report
        if QA_DUTIES[item["duty"]] and item["state"] not in ("established",)
    )

    plan = plan_reference_state(
        record.get("quality_plan_ref"),
        record.get("plan_issue_date", record["review_date"]),
        record["review_date"],
        policy["plan_revalidation_days"],
    )
    independence = independence_state(
        record["reports_to"],
        record.get("escalation_route"),
        policy["escalation_route_required"],
    )
    state = {
        "mandatory_waived": mandatory_waived,
        "mandatory_unassigned": mandatory_unassigned,
        "plan": plan,
        "independence": independence,
        "coverage": coverage,
        "policy": policy,
    }
    verdict = quality_assurance_verdict(state)
    gaps = [item for item in report if item["state"] not in ("established", "waived")]
    return {
        "programme": programme,
        "policy": policy,
        "duty_report": report,
        "gaps": gaps,
        "mandatory_waived": mandatory_waived,
        "mandatory_unassigned": mandatory_unassigned,
        "plain_coverage": coverage["plain_coverage"],
        "evidenced_coverage": coverage["evidenced_coverage"],
        "plan": plan,
        "independence": independence,
        "verdict": verdict,
        "meets_class_two": verdict == "quality-assurance-meets-class-two",
    }

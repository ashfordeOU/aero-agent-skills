"""Quality assurance arrangement for lowest-assurance commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 6.5 (the quality assurance arrangement covering
commercial EEE parts procured to the lowest assurance class, and the in-service
duties that arrangement carries). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the assurance policy and every declared duty record.
2. Dispose every duty in the class 3 catalogue as retained, relieved or
   unassigned, including the duties the programme never declared, so the
   report length always matches the catalogue length.
3. Refuse relief against a duty the lowest class still makes mandatory, and
   admit a discretionary relief only against a recorded rationale and an
   approval taken at the authority level the duty weight and the item
   criticality earn.
4. Carry three coverage figures: a plain one that credits an admissible
   relief, an evidenced one that credits only a duty with a real record, and
   a weighted evidenced one that lets a heavy duty outweigh a light one.
5. Read the quality plan against its revalidation interval and the quality
   function against the functions it grades.
6. Close on the first blocking condition, in a fixed order.
"""

import datetime

__all__ = [
    "QA_DUTY_CATALOGUE",
    "RELIEF_AUTHORITY_ORDER",
    "GRADED_FUNCTIONS",
    "CRITICALITY_LEVELS",
    "CRITICALITY_ESCALATION_FLOOR",
    "COVERAGE_TOLERANCE",
    "duty_catalogue",
    "is_mandatory_duty",
    "duty_weight",
    "authority_rank",
    "required_relief_authority",
    "relief_admissible",
    "dispose_duty",
    "coverage_figures",
    "plan_age_months",
    "plan_current",
    "reporting_line_embedded",
    "assess_quality_assurance",
]

# The duties the lowest assurance class still recognises. 'mandatory' says the
# class refuses relief outright; 'weight' says how much of the arrangement the
# duty carries, and drives both the weighted coverage and the authority a
# relief has to be taken at.
QA_DUTY_CATALOGUE = {
    "procurement-document-review": {"mandatory": True, "weight": 3},
    "nonconformance-processing": {"mandatory": True, "weight": 3},
    "alert-watch": {"mandatory": True, "weight": 3},
    "records-retention": {"mandatory": True, "weight": 2},
    "incoming-verification": {"mandatory": False, "weight": 3},
    "traceability-records": {"mandatory": False, "weight": 2},
    "handling-and-storage-control": {"mandatory": False, "weight": 2},
    "manufacturer-data-review": {"mandatory": False, "weight": 1},
    "audit-and-surveillance": {"mandatory": False, "weight": 1},
    "training-and-certification": {"mandatory": False, "weight": 1},
}

# Approval authorities, lowest first. A relief is admissible only when the
# approval was taken at or above the level the duty earns.
RELIEF_AUTHORITY_ORDER = (
    "none",
    "project-quality-manager",
    "project-manager",
    "customer",
)

# Functions a quality role cannot grade from inside without an escalation route.
GRADED_FUNCTIONS = ("design", "production", "procurement", "integration", "test")

# Item criticality, 1 being the most critical.
CRITICALITY_LEVELS = (1, 2, 3, 4)

# At or below this criticality the approval authority for a relief moves up one
# level, because the item cannot absorb the duty being stood down.
CRITICALITY_ESCALATION_FLOOR = 2

# Absorbs the float comparison when a coverage lands exactly on its floor.
COVERAGE_TOLERANCE = 1e-9

_POLICY_KEYS = (
    "plain_coverage_floor",
    "evidenced_coverage_floor",
    "weighted_coverage_floor",
    "plan_revalidation_months",
    "require_escalation_route",
)

_DUTY_RECORD_KEYS = (
    "duty",
    "owner",
    "procedure_reference",
    "evidence_reference",
    "relief_requested",
    "relief_rationale",
    "relief_approval_authority",
)


def duty_catalogue():
    """Return the class 3 duty names in a stable order."""
    return tuple(sorted(QA_DUTY_CATALOGUE))


def _duty_entry(duty):
    if not isinstance(duty, str) or duty not in QA_DUTY_CATALOGUE:
        raise ValueError(
            "duty must be one of %s, got %r" % (sorted(QA_DUTY_CATALOGUE), duty)
        )
    return QA_DUTY_CATALOGUE[duty]


def is_mandatory_duty(duty):
    """Return True when the lowest class refuses relief against this duty."""
    return bool(_duty_entry(duty)["mandatory"])


def duty_weight(duty):
    """Return the share of the arrangement this duty carries."""
    return int(_duty_entry(duty)["weight"])


def authority_rank(level):
    """Return the ordinal of an approval authority level."""
    if level not in RELIEF_AUTHORITY_ORDER:
        raise ValueError(
            "approval authority must be one of %s, got %r"
            % (list(RELIEF_AUTHORITY_ORDER), level)
        )
    return RELIEF_AUTHORITY_ORDER.index(level)


def _validate_criticality(criticality):
    if isinstance(criticality, bool) or criticality not in CRITICALITY_LEVELS:
        raise ValueError(
            "criticality must be one of %s, got %r"
            % (list(CRITICALITY_LEVELS), criticality)
        )
    return criticality


def required_relief_authority(duty, criticality):
    """Return the authority level a relief against this duty has to be taken at."""
    entry = _duty_entry(duty)
    _validate_criticality(criticality)
    if entry["mandatory"]:
        return "not-relievable"
    weight = entry["weight"]
    if weight >= 3:
        rank = authority_rank("customer")
    elif weight == 2:
        rank = authority_rank("project-manager")
    else:
        rank = authority_rank("project-quality-manager")
    if criticality <= CRITICALITY_ESCALATION_FLOOR:
        rank = min(rank + 1, len(RELIEF_AUTHORITY_ORDER) - 1)
    return RELIEF_AUTHORITY_ORDER[rank]


def relief_admissible(duty, criticality, rationale, approval_authority):
    """Return whether a relief against this duty is admissible, and why not."""
    required = required_relief_authority(duty, criticality)
    refusals = []
    if required == "not-relievable":
        refusals.append(
            "duty '%s' stays mandatory at the lowest assurance class and admits "
            "no relief" % duty
        )
    if not isinstance(rationale, str) or not rationale.strip():
        refusals.append("relief carries no recorded rationale")
    taken = authority_rank(approval_authority)
    if required != "not-relievable" and taken < authority_rank(required):
        refusals.append(
            "relief was approved at %s but duty '%s' earns %s"
            % (approval_authority, duty, required)
        )
    if required == "not-relievable" and taken == authority_rank("none"):
        refusals.append("relief carries no named approval")
    return {
        "duty": duty,
        "required_authority": required,
        "approval_authority": approval_authority,
        "admissible": not refusals,
        "refusals": refusals,
    }


def _text(value):
    """Return a stripped string, or None when the field is absent or blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected a string reference, got %r" % (value,))
    stripped = value.strip()
    return stripped or None


def _validate_duty_record(record, index):
    if not isinstance(record, dict):
        raise ValueError("duty record[%d] must be a mapping" % index)
    for key in record:
        if key not in _DUTY_RECORD_KEYS:
            raise ValueError(
                "duty record[%d] carries unknown key '%s'" % (index, key)
            )
    if "duty" not in record:
        raise ValueError("duty record[%d] missing required key 'duty'" % index)
    duty = record["duty"]
    _duty_entry(duty)
    requested = record.get("relief_requested", False)
    if not isinstance(requested, bool):
        raise ValueError(
            "duty record[%d]['relief_requested'] must be a boolean" % index
        )
    authority = record.get("relief_approval_authority", "none")
    if authority is None:
        authority = "none"
    authority_rank(authority)
    return {
        "duty": duty,
        "owner": _text(record.get("owner")),
        "procedure_reference": _text(record.get("procedure_reference")),
        "evidence_reference": _text(record.get("evidence_reference")),
        "relief_requested": requested,
        "relief_rationale": _text(record.get("relief_rationale")),
        "relief_approval_authority": authority,
    }


def dispose_duty(duty, record, criticality):
    """Return the disposition of one catalogue duty against its declared record."""
    _duty_entry(duty)
    _validate_criticality(criticality)
    if record is None:
        return {
            "duty": duty,
            "status": "unassigned",
            "evidenced": False,
            "weight": duty_weight(duty),
            "gap": "duty '%s' was never declared by the programme" % duty,
        }
    # Re-validating an already-normalised record is idempotent: it carries
    # exactly the known keys and stripped values.
    normalised = _validate_duty_record(dict(record, duty=duty), 0)
    if normalised["relief_requested"]:
        verdict = relief_admissible(
            duty,
            criticality,
            normalised["relief_rationale"],
            normalised["relief_approval_authority"],
        )
        if verdict["admissible"]:
            return {
                "duty": duty,
                "status": "relieved",
                "evidenced": False,
                "weight": duty_weight(duty),
                "gap": None,
            }
        return {
            "duty": duty,
            "status": "unassigned",
            "evidenced": False,
            "weight": duty_weight(duty),
            "gap": verdict["refusals"][0],
        }
    if not normalised["owner"]:
        return {
            "duty": duty,
            "status": "unassigned",
            "evidenced": False,
            "weight": duty_weight(duty),
            "gap": "duty '%s' names no owner" % duty,
        }
    if not normalised["procedure_reference"]:
        return {
            "duty": duty,
            "status": "unassigned",
            "evidenced": False,
            "weight": duty_weight(duty),
            "gap": "duty '%s' has an owner but no procedure reference" % duty,
        }
    if not normalised["evidence_reference"]:
        return {
            "duty": duty,
            "status": "retained",
            "evidenced": False,
            "weight": duty_weight(duty),
            "gap": "duty '%s' has a procedure but no evidence record" % duty,
        }
    return {
        "duty": duty,
        "status": "retained",
        "evidenced": True,
        "weight": duty_weight(duty),
        "gap": None,
    }


def coverage_figures(dispositions):
    """Return the plain, evidenced and weighted evidenced coverages."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    total = len(dispositions)
    total_weight = 0
    disposed = 0
    evidenced = 0
    evidenced_weight = 0
    for entry in dispositions:
        if not isinstance(entry, dict) or "status" not in entry:
            raise ValueError("each disposition must be a mapping with a 'status'")
        weight = int(entry.get("weight", 1))
        total_weight += weight
        if entry["status"] in ("retained", "relieved"):
            disposed += 1
        if entry.get("evidenced"):
            evidenced += 1
            evidenced_weight += weight
    if total_weight <= 0:
        raise ValueError("catalogue weights must sum above zero")
    return {
        "duty_count": total,
        "plain_coverage": disposed / total,
        "evidenced_coverage": evidenced / total,
        "weighted_evidenced_coverage": evidenced_weight / total_weight,
    }


def _parse_date(value, label):
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def plan_age_months(issue_date, as_of_date):
    """Return the whole months elapsed between a plan issue and the review date."""
    issued = _parse_date(issue_date, "issue_date")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < issued:
        raise ValueError("as_of_date %s precedes issue_date %s" % (as_of, issued))
    months = (as_of.year - issued.year) * 12 + (as_of.month - issued.month)
    if as_of.day < issued.day:
        months -= 1
    return max(months, 0)


def plan_current(issue_date, as_of_date, revalidation_months):
    """Return True when the plan age is still inside its revalidation interval."""
    if (
        isinstance(revalidation_months, bool)
        or not isinstance(revalidation_months, int)
        or revalidation_months <= 0
    ):
        raise ValueError(
            "revalidation_months must be a positive integer, got %r"
            % (revalidation_months,)
        )
    return plan_age_months(issue_date, as_of_date) <= revalidation_months


def reporting_line_embedded(reporting_line):
    """Return True when the quality function reports inside a function it grades."""
    if not isinstance(reporting_line, str) or not reporting_line.strip():
        raise ValueError("reporting_line must be a non-empty string")
    return reporting_line.strip().lower() in GRADED_FUNCTIONS


def _validate_policy(policy):
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in policy:
        if key not in _POLICY_KEYS:
            raise ValueError("policy carries unknown key '%s'" % key)
    for key in _POLICY_KEYS:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    floors = {}
    for key in (
        "plain_coverage_floor",
        "evidenced_coverage_floor",
        "weighted_coverage_floor",
    ):
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("policy['%s'] must be a number" % key)
        if value < 0.0 or value > 1.0:
            raise ValueError("policy['%s'] must lie in [0, 1], got %r" % (key, value))
        floors[key] = float(value)
    if floors["evidenced_coverage_floor"] > floors["plain_coverage_floor"]:
        raise ValueError(
            "evidenced coverage floor cannot exceed the plain coverage floor"
        )
    months = policy["plan_revalidation_months"]
    if isinstance(months, bool) or not isinstance(months, int) or months <= 0:
        raise ValueError("policy['plan_revalidation_months'] must be a positive integer")
    escalation = policy["require_escalation_route"]
    if not isinstance(escalation, bool):
        raise ValueError("policy['require_escalation_route'] must be a boolean")
    floors["plan_revalidation_months"] = months
    floors["require_escalation_route"] = escalation
    return floors


def _at_least(value, floor):
    """Return True when value reaches floor, absorbing the float landing case."""
    return value >= floor - COVERAGE_TOLERANCE


def assess_quality_assurance(arrangement, as_of_date):
    """Run the full clause 6.5 assurance-arrangement assessment."""
    if not isinstance(arrangement, dict):
        raise ValueError("arrangement must be a mapping")
    for key in ("policy", "criticality", "declared_duties", "reporting_line"):
        if key not in arrangement:
            raise ValueError("arrangement missing required key '%s'" % key)
    policy = _validate_policy(arrangement["policy"])
    criticality = _validate_criticality(arrangement["criticality"])
    declared = arrangement["declared_duties"]
    if not isinstance(declared, (list, tuple)):
        raise ValueError("arrangement['declared_duties'] must be a sequence")
    records = {}
    for index, item in enumerate(declared):
        normalised = _validate_duty_record(item, index)
        if normalised["duty"] in records:
            raise ValueError("duty '%s' is declared twice" % normalised["duty"])
        records[normalised["duty"]] = normalised

    dispositions = [
        dispose_duty(duty, records.get(duty), criticality)
        for duty in duty_catalogue()
    ]
    coverages = coverage_figures(dispositions)

    plan_reference = _text(arrangement.get("quality_plan_reference"))
    plan_issue = arrangement.get("quality_plan_issue_date")
    plan_present = bool(plan_reference) and plan_issue is not None
    plan_age = plan_age_months(plan_issue, as_of_date) if plan_present else None
    plan_is_current = (
        plan_current(plan_issue, as_of_date, policy["plan_revalidation_months"])
        if plan_present
        else False
    )

    embedded = reporting_line_embedded(arrangement["reporting_line"])
    escalation_route = _text(arrangement.get("escalation_route"))
    escalation_ok = (not embedded) or (not policy["require_escalation_route"]) or bool(
        escalation_route
    )

    gaps = [entry["gap"] for entry in dispositions if entry["gap"]]

    mandatory_relief_refused = [
        entry["duty"]
        for entry in dispositions
        if is_mandatory_duty(entry["duty"])
        and records.get(entry["duty"], {}).get("relief_requested")
    ]
    mandatory_unassigned = [
        entry["duty"]
        for entry in dispositions
        if entry["status"] == "unassigned" and is_mandatory_duty(entry["duty"])
    ]

    plain_ok = _at_least(coverages["plain_coverage"], policy["plain_coverage_floor"])
    evidenced_ok = _at_least(
        coverages["evidenced_coverage"], policy["evidenced_coverage_floor"]
    )
    weighted_ok = _at_least(
        coverages["weighted_evidenced_coverage"], policy["weighted_coverage_floor"]
    )

    if not plan_present:
        verdict = "no-quality-plan"
    elif mandatory_relief_refused:
        verdict = "mandatory-duty-relief-refused"
    elif mandatory_unassigned:
        verdict = "mandatory-duty-unassigned"
    elif not (plain_ok and evidenced_ok and weighted_ok):
        verdict = "coverage-short"
    elif not escalation_ok:
        verdict = "no-escalation-route"
    elif not plan_is_current:
        verdict = "quality-plan-revalidation-overdue"
    else:
        verdict = "class-3-arrangement-met"

    return {
        "criticality": criticality,
        "duties": dispositions,
        "coverage": coverages,
        "plain_coverage_met": plain_ok,
        "evidenced_coverage_met": evidenced_ok,
        "weighted_coverage_met": weighted_ok,
        "quality_plan_present": plan_present,
        "quality_plan_age_months": plan_age,
        "quality_plan_current": plan_is_current,
        "reporting_line_embedded": embedded,
        "escalation_route_satisfied": escalation_ok,
        "mandatory_relief_refused": mandatory_relief_refused,
        "mandatory_unassigned": mandatory_unassigned,
        "gaps": gaps,
        "verdict": verdict,
        "acceptable": verdict == "class-3-arrangement-met",
    }

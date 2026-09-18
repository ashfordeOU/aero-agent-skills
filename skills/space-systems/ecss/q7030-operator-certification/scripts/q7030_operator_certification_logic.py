"""Certification of wrapping operators per wire and terminal combination.

Anchor: ECSS-Q-ST-70-30C, wrapping personnel clauses (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Treat every wire-gauge and terminal-type pair as its own
   endorsement. A hand set for a coarse conductor on a square post is
   not the same hand on a fine conductor or a different post section,
   so a certification covers the combination it was demonstrated on and
   nothing else.
2. Grade the evidence behind each endorsement: a theory result above
   the pass mark, and a practical demonstration of enough wraps that
   were visually accepted and survived the pull test.
3. Hold the endorsement in date. A certification period runs from the
   examination or the last requalification, and the vision check the
   work depends on runs on its own clock.
4. Suspend on discontinuity. An endorsement whose combination has not
   been worked inside the continuity window is suspended pending a
   fresh demonstration rather than revoked, because the qualification
   was earned and only the currency has lapsed.
5. Answer the operational question: on this date, may this operator
   wrap this gauge on this terminal type, and if not, why not.

Every threshold is a declared project policy value the caller may
override, because the qualification scheme a programme adopts belongs
to its own process specification.

Stdlib only, offline, deterministic.
"""

import datetime

VALID_GAUGES = (20, 22, 24, 26, 28, 30)
VALID_TERMINAL_TYPES = (
    "square-post",
    "rectangular-post",
    "round-pin-adapter",
    "double-post",
)

# Evidence thresholds behind one endorsement.
MIN_THEORY_SCORE = 80
MIN_PRACTICAL_WRAPS = 10
MIN_PULL_TESTS_PASSED = 3

# Clocks, in days.
CERTIFICATION_VALIDITY_DAYS = 365
VISION_VALIDITY_DAYS = 365
CONTINUITY_WINDOW_DAYS = 180

CERTIFIED = "endorsement-current"
EXPIRED = "endorsement-expired"
SUSPENDED = "endorsement-suspended-for-continuity"
NOT_QUALIFIED = "endorsement-not-qualified"

PERMITTED = "assignment-permitted"
REFUSED = "assignment-refused"


def _whole(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %r" % (label, minimum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _date(label, value):
    if isinstance(value, datetime.datetime) or not isinstance(value, datetime.date):
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                raise ValueError("%s must be an ISO date, got %r" % (label, value))
        raise ValueError("%s must be a date, got %r" % (label, value))
    return value


def combination_key(gauge, terminal_type):
    """Identity of one wire-gauge and terminal-type combination."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer, got %r" % (gauge,))
    if gauge not in VALID_GAUGES:
        raise ValueError(
            "gauge %r is outside the qualification scheme (have %s)"
            % (gauge, ", ".join(str(g) for g in VALID_GAUGES))
        )
    if terminal_type not in VALID_TERMINAL_TYPES:
        raise ValueError(
            "terminal_type %r is unknown (expected one of %s)"
            % (terminal_type, ", ".join(VALID_TERMINAL_TYPES))
        )
    return (gauge, terminal_type)


def days_between(earlier, later):
    """Whole days from the earlier date to the later one."""
    start = _date("earlier", earlier)
    end = _date("later", later)
    return (end - start).days


def validate_endorsement(endorsement):
    """Validate one endorsement record and return a normalized copy."""
    if not isinstance(endorsement, dict):
        raise ValueError("endorsement must be a mapping")
    key = combination_key(
        endorsement.get("gauge"), endorsement.get("terminal_type")
    )
    return {
        "gauge": key[0],
        "terminal_type": key[1],
        "examination_date": _date("examination_date", endorsement.get("examination_date")),
        "theory_score": _whole("theory_score", endorsement.get("theory_score", 0)),
        "practical_wraps_accepted": _whole(
            "practical_wraps_accepted", endorsement.get("practical_wraps_accepted", 0)
        ),
        "pull_tests_passed": _whole(
            "pull_tests_passed", endorsement.get("pull_tests_passed", 0)
        ),
        "last_production_date": _date(
            "last_production_date",
            endorsement.get("last_production_date", endorsement.get("examination_date")),
        ),
    }


def validate_operator(operator):
    """Validate one operator file and return a normalized copy."""
    if not isinstance(operator, dict):
        raise ValueError("operator must be a mapping")
    operator_id = _text("operator id", operator.get("id"))
    endorsements = operator.get("endorsements", [])
    if not isinstance(endorsements, (list, tuple)) or not endorsements:
        raise ValueError("operator %s needs a non-empty endorsement list" % operator_id)
    normalized = []
    seen = set()
    for endorsement in endorsements:
        norm = validate_endorsement(endorsement)
        key = (norm["gauge"], norm["terminal_type"])
        if key in seen:
            raise ValueError(
                "operator %s has two endorsements for %r" % (operator_id, key)
            )
        seen.add(key)
        normalized.append(norm)
    return {
        "id": operator_id,
        "vision_check_date": _date(
            "operator %s vision_check_date" % operator_id,
            operator.get("vision_check_date"),
        ),
        "endorsements": normalized,
    }


def evidence_findings(endorsement):
    """Findings about the evidence behind one endorsement."""
    norm = validate_endorsement(endorsement)
    findings = []
    if norm["theory_score"] < MIN_THEORY_SCORE:
        findings.append("theory-score-below-pass-mark")
    if norm["practical_wraps_accepted"] < MIN_PRACTICAL_WRAPS:
        findings.append("too-few-accepted-practical-wraps")
    if norm["pull_tests_passed"] < MIN_PULL_TESTS_PASSED:
        findings.append("too-few-passed-practical-pull-tests")
    return findings


def endorsement_status(endorsement, on_date):
    """Status of one endorsement on a given date, with its findings."""
    norm = validate_endorsement(endorsement)
    day = _date("on_date", on_date)
    findings = evidence_findings(norm)
    if findings:
        return NOT_QUALIFIED, findings
    age = days_between(norm["examination_date"], day)
    if age < 0:
        raise ValueError("examination_date is later than the assessment date")
    if age > CERTIFICATION_VALIDITY_DAYS:
        return EXPIRED, ["certification-period-elapsed"]
    idle = days_between(norm["last_production_date"], day)
    if idle > CONTINUITY_WINDOW_DAYS:
        return SUSPENDED, ["continuity-window-elapsed-without-production"]
    return CERTIFIED, []


def vision_findings(operator, on_date):
    """Findings about the operator-level vision check."""
    norm = validate_operator(operator)
    age = days_between(norm["vision_check_date"], on_date)
    if age < 0:
        raise ValueError("vision_check_date is later than the assessment date")
    if age > VISION_VALIDITY_DAYS:
        return ["vision-check-out-of-date"]
    return []


def assess_operator(operator, on_date):
    """Status of every endorsement in one operator file on a date."""
    norm = validate_operator(operator)
    vision = vision_findings(norm, on_date)
    endorsements = []
    for endorsement in norm["endorsements"]:
        status, findings = endorsement_status(endorsement, on_date)
        if vision and status == CERTIFIED:
            status = SUSPENDED
            findings = list(vision)
        endorsements.append(
            {
                "gauge": endorsement["gauge"],
                "terminal_type": endorsement["terminal_type"],
                "status": status,
                "findings": findings,
            }
        )
    return {
        "id": norm["id"],
        "vision_findings": vision,
        "endorsements": endorsements,
        "current_combinations": [
            (e["gauge"], e["terminal_type"])
            for e in endorsements
            if e["status"] == CERTIFIED
        ],
    }


def assignment_verdict(operator, gauge, terminal_type, on_date):
    """Whether one operator may wrap one combination on a given date."""
    key = combination_key(gauge, terminal_type)
    assessed = assess_operator(operator, on_date)
    for endorsement in assessed["endorsements"]:
        if (endorsement["gauge"], endorsement["terminal_type"]) == key:
            permitted = endorsement["status"] == CERTIFIED
            return {
                "operator_id": assessed["id"],
                "combination": key,
                "status": endorsement["status"],
                "findings": endorsement["findings"],
                "verdict": PERMITTED if permitted else REFUSED,
                "permitted": permitted,
            }
    return {
        "operator_id": assessed["id"],
        "combination": key,
        "status": NOT_QUALIFIED,
        "findings": ["no-endorsement-for-this-combination"],
        "verdict": REFUSED,
        "permitted": False,
    }

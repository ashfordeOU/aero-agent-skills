"""SCC-critical application identification.

Anchor: ECSS-Q-ST-70-36C, the framework clauses that decide which applications
are stress-corrosion-cracking critical. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Test the three conditions the cracking mechanism needs at the same time: a
   susceptible alloy state, a sustained tensile stress held long enough to
   matter, and an environment able to promote cracking.
2. Absent any one of the three, the application is not SCC critical and the
   reason is recorded, so a later change to that one condition is visible as
   the thing that would reopen the question.
3. With all three present, grade the application on the consequence of the
   crack: a load path whose failure is catastrophic and unbacked by redundancy
   is SCC critical; anything else is placed under monitoring.
4. Return the actions each grade owes, and aggregate an application list into
   counts plus a findings list naming every critical item.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "SUSTAINED_HOURS_MIN",
    "STRESS_RATIO_FLOOR",
    "RESISTANCE_CATEGORIES",
    "ENVIRONMENT_SEVERITIES",
    "FAILURE_CONSEQUENCES",
    "normalize_category",
    "normalize_severity",
    "normalize_consequence",
    "alloy_condition_met",
    "stress_condition_met",
    "environment_condition_met",
    "coexisting_conditions",
    "required_actions",
    "grade_application",
    "assess_criticality",
]

# Stress ratio and duration are compared against fixed boundaries; a value the
# analyst means to sit exactly on the boundary must not fall off it through a
# float representation error.
RATIO_TOLERANCE = 1e-9

# A load held for less than this many hours is a transient, not the sustained
# tensile stress the cracking mechanism needs.
SUSTAINED_HOURS_MIN = 24.0

# Below this fraction of the yield strength the sustained tensile stress is not
# treated as a cracking driver on its own.
STRESS_RATIO_FLOOR = 0.10

# Resistance ratings, ordered from most to least resistant. Only the lowest two
# ratings put the alloy condition on the table.
RESISTANCE_CATEGORIES = ("high", "medium", "low")

# Environment grades. "benign" cannot promote cracking on its own.
ENVIRONMENT_SEVERITIES = ("benign", "moderate", "severe")

# Consequence of the crack for the function the part serves.
FAILURE_CONSEQUENCES = ("minor", "major", "catastrophic")

_CATEGORY_ALIASES = {
    "table-i": "high",
    "high-resistance": "high",
    "resistant": "high",
    "moderate": "medium",
    "medium-resistance": "medium",
    "intermediate": "medium",
    "low-resistance": "low",
    "susceptible": "low",
}

_SEVERITY_ALIASES = {
    "none": "benign",
    "inert": "benign",
    "dry": "benign",
    "mild": "moderate",
    "aggressive": "severe",
    "harsh": "severe",
}

_CONSEQUENCE_ALIASES = {
    "negligible": "minor",
    "significant": "major",
    "critical": "catastrophic",
    "loss-of-mission": "catastrophic",
}


def _token(value, label):
    """Return a lower-cased dash-normalized token, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_real(value, label, allow_zero=True):
    """Return a finite float, raising on a bad or negative input."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def normalize_category(value):
    """Return the canonical SCC resistance rating token."""
    token = _token(value, "resistance category")
    token = _CATEGORY_ALIASES.get(token, token)
    if token not in RESISTANCE_CATEGORIES:
        raise ValueError(
            "resistance category %r is not one of %s"
            % (value, ", ".join(RESISTANCE_CATEGORIES))
        )
    return token


def normalize_severity(value):
    """Return the canonical environment severity token."""
    token = _token(value, "environment severity")
    token = _SEVERITY_ALIASES.get(token, token)
    if token not in ENVIRONMENT_SEVERITIES:
        raise ValueError(
            "environment severity %r is not one of %s"
            % (value, ", ".join(ENVIRONMENT_SEVERITIES))
        )
    return token


def normalize_consequence(value):
    """Return the canonical failure-consequence token."""
    token = _token(value, "failure consequence")
    token = _CONSEQUENCE_ALIASES.get(token, token)
    if token not in FAILURE_CONSEQUENCES:
        raise ValueError(
            "failure consequence %r is not one of %s"
            % (value, ", ".join(FAILURE_CONSEQUENCES))
        )
    return token


def alloy_condition_met(resistance_category):
    """Return True when the alloy state is susceptible enough to matter."""
    return normalize_category(resistance_category) in ("medium", "low")


def stress_condition_met(stress_ratio, sustained_hours):
    """Return True when a tensile stress is both large enough and held long enough.

    The ratio is the sustained tensile stress as a fraction of the yield
    strength. Both boundaries are inclusive: a value the analyst intends to be
    exactly at the boundary counts, and the equality is resolved with a
    tolerance rather than by moving the boundary.
    """
    ratio = _positive_real(stress_ratio, "stress_ratio")
    hours = _positive_real(sustained_hours, "sustained_hours")
    if ratio > 1.5:
        raise ValueError(
            "stress_ratio %g exceeds 1.5 of yield; check the units, this is a ratio" % ratio
        )
    big_enough = ratio > STRESS_RATIO_FLOOR or math.isclose(
        ratio, STRESS_RATIO_FLOOR, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    long_enough = hours > SUSTAINED_HOURS_MIN or math.isclose(
        hours, SUSTAINED_HOURS_MIN, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    return bool(big_enough and long_enough)


def environment_condition_met(severity):
    """Return True when the environment can promote cracking."""
    return normalize_severity(severity) in ("moderate", "severe")


def coexisting_conditions(application):
    """Return the three condition flags for one application record."""
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping")
    for key in (
        "id",
        "resistance_category",
        "stress_ratio",
        "sustained_hours",
        "environment_severity",
        "failure_consequence",
    ):
        if key not in application:
            raise ValueError("application missing required key %r" % key)
    return {
        "alloy": alloy_condition_met(application["resistance_category"]),
        "stress": stress_condition_met(
            application["stress_ratio"], application["sustained_hours"]
        ),
        "environment": environment_condition_met(application["environment_severity"]),
    }


def required_actions(grade):
    """Return the actions a criticality grade owes, most binding first."""
    if grade == "scc-critical":
        return [
            "select an alloy state rated resistant, or justify the state with test evidence",
            "hold the sustained tensile stress below the threshold for the state",
            "protect or control the environment across every exposure phase",
            "record the disposition for review",
        ]
    if grade == "scc-monitored":
        return [
            "record the alloy state, sustained stress and environment in the materials list",
            "re-open the assessment if any of the three conditions worsens",
        ]
    if grade == "not-scc-critical":
        return ["record which condition is absent so a later change re-opens the assessment"]
    raise ValueError("unknown criticality grade %r" % (grade,))


def grade_application(application):
    """Grade one application and return its criticality record."""
    conditions = coexisting_conditions(application)
    app_id = _token(application.get("id", ""), "application id")
    consequence = normalize_consequence(application["failure_consequence"])
    redundant = bool(application.get("redundant", False))
    absent = [name for name, met in sorted(conditions.items()) if not met]
    if absent:
        grade = "not-scc-critical"
        rationale = "cracking needs all three conditions together; absent here: %s" % (
            ", ".join(absent),
        )
    elif consequence == "catastrophic" and not redundant:
        grade = "scc-critical"
        rationale = "all three conditions coexist on a single-load-path catastrophic failure"
    else:
        grade = "scc-monitored"
        rationale = (
            "all three conditions coexist, but the consequence is %s%s"
            % (consequence, " and the load path is redundant" if redundant else "")
        )
    return {
        "id": app_id,
        "conditions": conditions,
        "absent_conditions": absent,
        "failure_consequence": consequence,
        "redundant": redundant,
        "grade": grade,
        "rationale": rationale,
        "actions": required_actions(grade),
    }


def assess_criticality(applications):
    """Grade an application list and report the SCC-critical population."""
    if not isinstance(applications, (list, tuple)) or not applications:
        raise ValueError("applications must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for application in applications:
        record = grade_application(application)
        if record["id"] in seen:
            raise ValueError("duplicate application id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    critical = [r for r in records if r["grade"] == "scc-critical"]
    monitored = [r for r in records if r["grade"] == "scc-monitored"]
    findings = [
        "application %s is SCC critical: %s" % (r["id"], r["rationale"]) for r in critical
    ]
    return {
        "records": records,
        "critical_count": len(critical),
        "monitored_count": len(monitored),
        "cleared_count": len(records) - len(critical) - len(monitored),
        "any_critical": bool(critical),
        "findings": findings,
    }

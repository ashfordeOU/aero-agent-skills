"""Safety programme of a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.9.1 (safety programme: safety organization,
hazard control, and accident, incident and emergency preparedness per
5.9.1.2). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Rank each identified hazard by consequence and likelihood, combine them
   into a risk index and read the acceptance band the index falls in.
2. Rank the control applied to the hazard on the control hierarchy, and
   refuse a severe hazard held only by a procedural or protective control.
3. Assess the safety organization: an appointed safety officer, that officer
   independent of the test-execution line, deputy cover, and the trained
   fraction of the staff on shift.
4. Assess accident, incident and emergency preparedness: a response plan and
   a drill for every credible scenario, and the drill interval respected.
5. Aggregate: the programme stands only when no hazard sits in an
   unacceptable band, no severe hazard is weakly controlled, the organization
   is staffed and independent, and every scenario is drilled and current.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "CONSEQUENCE_RANK",
    "LIKELIHOOD_RANK",
    "CONTROL_RANK",
    "DESIGN_CONTROL_MAX_RANK",
    "UNACCEPTABLE_MIN",
    "UNDESIRABLE_MIN",
    "REVIEW_MIN",
    "EXECUTION_LINE",
    "risk_index",
    "risk_acceptance",
    "control_rank",
    "assess_hazard",
    "drill_status",
    "assess_scenario",
    "assess_organization",
    "assess_safety_programme",
]

FRACTION_TOLERANCE = 1e-9

# Consequence of the hazard if it is realised, worst first.
CONSEQUENCE_RANK = {
    "catastrophic": 4,
    "critical": 3,
    "marginal": 2,
    "negligible": 1,
}

# Likelihood of realisation over the life of the facility, worst first.
LIKELIHOOD_RANK = {
    "frequent": 5,
    "probable": 4,
    "occasional": 3,
    "remote": 2,
    "improbable": 1,
}

# Control hierarchy, strongest first. A lower rank removes the hazard; a
# higher rank only asks a person to avoid it.
CONTROL_RANK = {
    "elimination": 1,
    "substitution": 2,
    "engineered-control": 3,
    "interlock": 3,
    "warning-device": 4,
    "procedure": 5,
    "protective-equipment": 6,
}

# A catastrophic or critical hazard has to be held by a control at least this
# strong; anything weaker leaves the outcome to a person not making a mistake.
DESIGN_CONTROL_MAX_RANK = 3

# Reporting lines that sit inside test execution, so an officer reporting
# there is overseeing the people who direct the officer.
EXECUTION_LINE = ("test conductor", "test operations", "test manager")

# Bands on the product of the two ranks, so the bounds are exact integers.
UNACCEPTABLE_MIN = 15
UNDESIRABLE_MIN = 9
REVIEW_MIN = 4


def risk_index(consequence, likelihood):
    """Return the integer risk index of a hazard from its two ordinals."""
    if consequence not in CONSEQUENCE_RANK:
        raise ValueError(
            "unknown consequence %r; expected one of %s"
            % (consequence, ", ".join(sorted(CONSEQUENCE_RANK)))
        )
    if likelihood not in LIKELIHOOD_RANK:
        raise ValueError(
            "unknown likelihood %r; expected one of %s"
            % (likelihood, ", ".join(sorted(LIKELIHOOD_RANK)))
        )
    return CONSEQUENCE_RANK[consequence] * LIKELIHOOD_RANK[likelihood]


def risk_acceptance(index):
    """Return the acceptance band a risk index falls in."""
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("risk index must be an integer, got %r" % (index,))
    if index < 1 or index > 20:
        raise ValueError("risk index must lie in [1, 20], got %d" % index)
    if index >= UNACCEPTABLE_MIN:
        return "unacceptable"
    if index >= UNDESIRABLE_MIN:
        return "undesirable"
    if index >= REVIEW_MIN:
        return "acceptable-with-review"
    return "acceptable"


def control_rank(control):
    """Return the hierarchy rank of a control, strongest being one."""
    if control not in CONTROL_RANK:
        raise ValueError(
            "unknown control %r; expected one of %s"
            % (control, ", ".join(sorted(CONTROL_RANK)))
        )
    return CONTROL_RANK[control]


def assess_hazard(hazard):
    """Assess one identified hazard of the test centre."""
    if not isinstance(hazard, dict):
        raise ValueError("hazard must be a mapping")
    for key in ("id", "consequence", "likelihood", "controls"):
        if key not in hazard:
            raise ValueError("hazard missing required key '%s'" % key)
    hz_id = hazard["id"]
    if not isinstance(hz_id, str) or not hz_id.strip():
        raise ValueError("hazard id must be a non-empty string")
    controls = hazard["controls"]
    if not isinstance(controls, (list, tuple)):
        raise ValueError("hazard controls must be a sequence")
    if not controls:
        raise ValueError("hazard %s names no control; an uncontrolled hazard "
                         "cannot be graded, it has to be controlled" % hz_id)
    ranks = [control_rank(c) for c in controls]
    strongest = min(ranks)
    index = risk_index(hazard["consequence"], hazard["likelihood"])
    band = risk_acceptance(index)
    severe = CONSEQUENCE_RANK[hazard["consequence"]] >= CONSEQUENCE_RANK["critical"]
    findings = []
    if band == "unacceptable":
        findings.append(
            "%s carries risk index %d, an unacceptable residual risk" % (hz_id, index)
        )
    if severe and strongest > DESIGN_CONTROL_MAX_RANK:
        findings.append(
            "%s is a %s hazard held only by a rank-%d control; a design control "
            "is required" % (hz_id, hazard["consequence"], strongest)
        )
    verified = hazard.get("control_verified", False)
    if not isinstance(verified, bool):
        raise ValueError("'control_verified' must be a boolean")
    if severe and not verified:
        findings.append("%s has an unverified control on a severe hazard" % hz_id)
    return {
        "id": hz_id,
        "risk_index": index,
        "acceptance": band,
        "strongest_control_rank": strongest,
        "severe": severe,
        "control_verified": verified,
        "findings": findings,
        "controlled": not findings,
    }


def drill_status(interval_days, elapsed_days):
    """Return 'current', 'due' or 'overdue' for a drill against its interval."""
    for label, value in (
        ("interval_days", interval_days),
        ("elapsed_days", elapsed_days),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer number of days" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if interval_days == 0:
        raise ValueError("interval_days must be at least one day")
    if elapsed_days > interval_days:
        return "overdue"
    if elapsed_days == interval_days:
        return "due"
    return "current"


def assess_scenario(scenario):
    """Assess one accident, incident or emergency scenario."""
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a mapping")
    for key in ("name", "interval_days", "elapsed_days"):
        if key not in scenario:
            raise ValueError("scenario missing required key '%s'" % key)
    name = scenario["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("scenario name must be a non-empty string")
    plan = scenario.get("response_plan", False)
    if not isinstance(plan, bool):
        raise ValueError("'response_plan' must be a boolean")
    reporting = scenario.get("reporting_route", None)
    status = drill_status(scenario["interval_days"], scenario["elapsed_days"])
    findings = []
    if not plan:
        findings.append("%s has no documented response plan" % name)
    if status == "overdue":
        findings.append(
            "%s drill is overdue at %d days against a %d day interval"
            % (name, scenario["elapsed_days"], scenario["interval_days"])
        )
    if not (isinstance(reporting, str) and reporting.strip()):
        findings.append("%s has no accident and incident reporting route" % name)
    return {
        "name": name,
        "drill_status": status,
        "response_plan": plan,
        "reporting_route": reporting if isinstance(reporting, str) else None,
        "findings": findings,
        "prepared": not findings,
    }


def assess_organization(org):
    """Assess the safety organization of the test centre."""
    if not isinstance(org, dict):
        raise ValueError("organization must be a mapping")
    for key in ("safety_officer", "reports_to", "trained_staff", "staff_on_shift"):
        if key not in org:
            raise ValueError("organization missing required key '%s'" % key)
    officer = org["safety_officer"]
    if officer is not None and not isinstance(officer, str):
        raise ValueError("safety_officer must be a name or None")
    reports_to = org["reports_to"]
    if not isinstance(reports_to, str) or not reports_to.strip():
        raise ValueError("reports_to must be a non-empty string")
    for key in ("trained_staff", "staff_on_shift"):
        value = org[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % key)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (key, value))
    trained = org["trained_staff"]
    on_shift = org["staff_on_shift"]
    if on_shift == 0:
        raise ValueError("staff_on_shift must be at least one")
    if trained > on_shift:
        raise ValueError(
            "trained_staff %d exceeds staff_on_shift %d" % (trained, on_shift)
        )
    required = org.get("required_trained_fraction", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_trained_fraction must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_trained_fraction must lie in [0, 1]")
    deputy = org.get("deputy_appointed", False)
    if not isinstance(deputy, bool):
        raise ValueError("'deputy_appointed' must be a boolean")
    fraction = float(trained) / float(on_shift)
    findings = []
    if not (isinstance(officer, str) and officer.strip()):
        findings.append("no safety officer is appointed")
    independent = reports_to.strip().lower() not in EXECUTION_LINE
    if not independent:
        findings.append(
            "the safety officer reports to %s, inside the line being overseen"
            % reports_to
        )
    if not deputy:
        findings.append("no deputy is appointed to cover the safety officer")
    met = fraction > required or math.isclose(
        fraction, required, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    if not met:
        findings.append(
            "%.4f of the staff on shift is safety trained, below the required %.4f"
            % (fraction, required)
        )
    return {
        "safety_officer": officer,
        "reports_to": reports_to,
        "independent": independent,
        "deputy_appointed": deputy,
        "trained_fraction": fraction,
        "required_trained_fraction": required,
        "findings": findings,
        "adequate": not findings,
    }


def assess_safety_programme(spec):
    """Run the full clause 5.9.1 safety-programme assessment.

    spec keys: organization, hazards, scenarios.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("organization", "hazards", "scenarios"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    hazards = spec["hazards"]
    if not isinstance(hazards, (list, tuple)) or not hazards:
        raise ValueError("spec['hazards'] must be a non-empty sequence")
    scenarios = spec["scenarios"]
    if not isinstance(scenarios, (list, tuple)) or not scenarios:
        raise ValueError("spec['scenarios'] must be a non-empty sequence")
    org_record = assess_organization(spec["organization"])
    hazard_records = [assess_hazard(h) for h in hazards]
    scenario_records = [assess_scenario(s) for s in scenarios]
    seen = set()
    for record in hazard_records:
        if record["id"] in seen:
            raise ValueError("duplicate hazard id %r" % record["id"])
        seen.add(record["id"])
    findings = list(org_record["findings"])
    for record in hazard_records:
        findings.extend(record["findings"])
    for record in scenario_records:
        findings.extend(record["findings"])
    worst = max(r["risk_index"] for r in hazard_records)
    return {
        "organization": org_record,
        "hazards": hazard_records,
        "scenarios": scenario_records,
        "worst_risk_index": worst,
        "worst_acceptance": risk_acceptance(worst),
        "unacceptable_count": sum(
            1 for r in hazard_records if r["acceptance"] == "unacceptable"
        ),
        "overdue_drill_count": sum(
            1 for r in scenario_records if r["drill_status"] == "overdue"
        ),
        "findings": findings,
        "programme_sound": not findings,
    }

"""Evaluation campaign coverage for Class 2 commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 5.2.3.1 (the evaluation activity that has to
stand behind a commercial part before it is used at the intermediate
assurance class, taken as one campaign rather than as a stack of tests).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The campaign is a set of elements, each carrying a weight that says how much
  of the assurance it supplies. Two of them -- the manufacturer assessment and
  the constructional analysis -- answer questions nothing else in the campaign
  answers, so at the intermediate class they still cannot be bought with a
  waiver or a similarity argument.
* Some elements are conditional. Whether they apply is a property of the
  mission profile, not of the part: a radiation evaluation is owed only when a
  radiation requirement exists, an assembly compatibility check only when the
  assembly process departs from the qualified one. An element the profile
  makes inapplicable leaves the denominator entirely; it is neither credit nor
  a gap, and pretending otherwise either flatters or punishes the campaign.
* Each element is in a state, and the state fixes the credit it earns. The
  intermediate class credits a similarity argument more generously than the
  highest class does, because the assurance it is buying is lower.
* A heritage claim is graded rather than merely accepted or refused. A
  different manufacturer, a different part number, a notified process change
  or evidence outside its validity period each break the claim outright. A
  different assembly site does not: at this class it downgrades the credit and
  raises a finding, because an audit can still recover it.
* The intermediate class closes on a coverage threshold rather than on total
  coverage, but the two unwaivable elements have to be whole regardless of
  what the fraction says.
"""

from __future__ import annotations

import math

# Campaign elements and the share of the assurance each supplies.
ELEMENT_WEIGHTS = {
    "manufacturer-assessment": 1.0,
    "constructional-analysis": 1.0,
    "radiation-evaluation": 0.9,
    "endurance-life-test": 0.8,
    "environmental-mechanical-test": 0.7,
    "electrical-characterisation-over-temperature": 0.7,
    "assembly-compatibility-check": 0.5,
    "materials-and-finish-review": 0.4,
}

# Elements no waiver and no similarity argument may buy, at any class.
UNWAIVABLE_ELEMENTS = (
    "manufacturer-assessment",
    "constructional-analysis",
)

# Elements owed only when the mission profile raises the driver behind them.
CONDITIONAL_ELEMENTS = {
    "radiation-evaluation": "radiation_requirement",
    "assembly-compatibility-check": "non_standard_assembly_process",
}

# Credit an element state earns before the heritage and unwaivable rules.
ELEMENT_STATE_CREDIT = {
    "performed-on-this-part-type": 1.0,
    "covered-by-heritage-claim": 1.0,
    "performed-on-similar-part-type": 0.7,
    "waived-with-approved-justification": 1.0,
    "waived-without-justification": 0.0,
    "planned-not-yet-performed": 0.0,
    "element-absent": 0.0,
}

# A heritage record older than this is outside its validity period at Class 2.
HERITAGE_VALIDITY_MONTHS = 48

# Credit left to a heritage claim whose only defect is the assembly site.
HERITAGE_SITE_DOWNGRADE_CREDIT = 0.7

HERITAGE_OUTCOMES = (
    "heritage-claim-stands",
    "heritage-claim-downgraded",
    "heritage-claim-inadmissible",
)

# Coverage the intermediate class closes on.
CLASS_2_COVERAGE_THRESHOLD = 0.8

VERDICTS = (
    "evaluation-campaign-complete",
    "evaluation-campaign-open-actions",
    "evaluation-campaign-incomplete",
)

# Coverage is a ratio of sums of weights; a campaign that is materially at the
# threshold can land a few units in the last place below it.
COVERAGE_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def element_weight(name):
    """Weight of one campaign element; unknown element names are rejected."""
    if name not in ELEMENT_WEIGHTS:
        raise ValueError(
            "unknown campaign element %r (known: %s)"
            % (name, ", ".join(sorted(ELEMENT_WEIGHTS)))
        )
    return ELEMENT_WEIGHTS[name]


def state_credit(state):
    """Credit an element state earns before the heritage rules are applied."""
    if state not in ELEMENT_STATE_CREDIT:
        raise ValueError(
            "unknown element state %r (known: %s)"
            % (state, ", ".join(sorted(ELEMENT_STATE_CREDIT)))
        )
    return ELEMENT_STATE_CREDIT[state]


def normalize_profile(profile):
    """Validate a mission profile and fill the drivers it left unstated."""
    if profile is None:
        profile = {}
    if not isinstance(profile, dict):
        raise ValueError("mission profile must be a mapping, got %r" % (type(profile).__name__,))
    drivers = {}
    for driver in sorted(set(CONDITIONAL_ELEMENTS.values())):
        value = profile.get(driver, False)
        if not isinstance(value, bool):
            raise ValueError("mission profile driver %s must be a boolean, got %r" % (driver, value))
        drivers[driver] = value
    for key in profile:
        if key not in drivers:
            raise ValueError(
                "unknown mission profile driver %r (known: %s)"
                % (key, ", ".join(sorted(drivers)))
            )
    return drivers


def element_applicable(name, drivers):
    """Decide whether the mission profile owes this element at all."""
    element_weight(name)  # validation only
    driver = CONDITIONAL_ELEMENTS.get(name)
    if driver is None:
        return True
    if not isinstance(drivers, dict) or driver not in drivers:
        raise ValueError("mission profile does not state the driver %r" % (driver,))
    return bool(drivers[driver])


def grade_heritage(claim):
    """Grade a heritage claim into an outcome, a credit factor and its reasons.

    A different assembly site downgrades at this class rather than breaking
    the claim, because an audit can still recover it. Everything else that
    fails breaks it outright, and every broken rule is named, because each one
    names a different repair.
    """
    if not isinstance(claim, dict):
        raise ValueError("heritage claim must be a mapping, got %r" % (type(claim).__name__,))
    breaking = []
    for key, reason in (
        ("same_manufacturer", "heritage-manufacturer-differs"),
        ("same_part_number", "heritage-part-number-differs"),
    ):
        value = claim.get(key)
        if not isinstance(value, bool):
            raise ValueError("%s of a heritage claim must be a boolean, got %r" % (key, value))
        if not value:
            breaking.append(reason)
    site = claim.get("same_assembly_site")
    if not isinstance(site, bool):
        raise ValueError("same_assembly_site of a heritage claim must be a boolean, got %r" % (site,))
    notified = claim.get("process_change_notified", False)
    if not isinstance(notified, bool):
        raise ValueError("process_change_notified must be a boolean, got %r" % (notified,))
    if notified:
        breaking.append("heritage-superseded-by-process-change")
    age = _real(claim.get("evidence_age_months"), "evidence_age_months")
    if age < 0.0:
        raise ValueError("evidence_age_months must not be negative, got %r" % (age,))
    if age > float(HERITAGE_VALIDITY_MONTHS):
        breaking.append("heritage-evidence-out-of-validity")
    reasons = list(breaking)
    if not site:
        reasons.append("heritage-assembly-site-differs")
    if breaking:
        return ("heritage-claim-inadmissible", 0.0, reasons)
    if not site:
        return ("heritage-claim-downgraded", HERITAGE_SITE_DOWNGRADE_CREDIT, reasons)
    return ("heritage-claim-stands", 1.0, reasons)


def normalize_element(raw):
    """Validate one campaign element declaration and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("element must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("element")
    element_weight(name)  # validation only
    state = raw.get("state", "element-absent")
    state_credit(state)  # validation only
    claim = raw.get("heritage_claim")
    if state == "covered-by-heritage-claim" and claim is None:
        raise ValueError(
            "element %r declares heritage but carries no heritage_claim" % (name,)
        )
    if claim is not None and not isinstance(claim, dict):
        raise ValueError("heritage_claim of %r must be a mapping" % (name,))
    return {"element": name, "state": state, "heritage_claim": claim}


def assess_element(raw, applicable=True):
    """Grade one campaign element into a credit and its findings."""
    element = normalize_element(raw)
    if not isinstance(applicable, bool):
        raise ValueError("applicable must be a boolean, got %r" % (applicable,))
    name = element["element"]
    state = element["state"]
    weight = element_weight(name)
    if not applicable:
        return {
            "element": name,
            "state": state,
            "applicable": False,
            "weight": 0.0,
            "credit": 0.0,
            "weighted_credit": 0.0,
            "heritage_outcome": None,
            "heritage_reasons": [],
            "findings": [],
        }
    credit = state_credit(state)
    findings = []
    outcome = None
    reasons = []
    if state == "covered-by-heritage-claim":
        outcome, factor, reasons = grade_heritage(element["heritage_claim"])
        credit = credit * factor
        if outcome == "heritage-claim-inadmissible":
            findings.append("heritage-claim-inadmissible")
        elif outcome == "heritage-claim-downgraded":
            findings.append("heritage-claim-downgraded-on-assembly-site")
    elif state == "performed-on-similar-part-type":
        findings.append("similarity-credit-taken")
    elif state == "waived-with-approved-justification":
        findings.append("element-waived-under-justification")
    elif state == "waived-without-justification":
        findings.append("element-waived-without-justification")
    elif state == "planned-not-yet-performed":
        findings.append("element-planned-not-performed")
    elif state == "element-absent":
        findings.append("element-absent-from-campaign")
    if name in UNWAIVABLE_ELEMENTS and state in (
        "waived-with-approved-justification",
        "performed-on-similar-part-type",
    ):
        credit = 0.0
    if name in UNWAIVABLE_ELEMENTS and credit < 1.0 - COVERAGE_TOLERANCE:
        findings.append("unwaivable-element-not-covered")
    return {
        "element": name,
        "state": state,
        "applicable": True,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "heritage_outcome": outcome,
        "heritage_reasons": reasons,
        "findings": findings,
    }


def campaign_coverage(records):
    """Weighted credit of the applicable elements over their total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a campaign must carry at least one element")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        if not record.get("applicable", True):
            continue
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("no applicable element carries any weight")
    return earned / total_weight


def meets_class_2_threshold(coverage, threshold=CLASS_2_COVERAGE_THRESHOLD):
    """Decide whether a coverage fraction reaches the intermediate threshold."""
    value = _real(coverage, "coverage")
    bound = _real(threshold, "threshold")
    return value >= bound - COVERAGE_TOLERANCE


def outstanding_elements(records):
    """Applicable elements short of full credit, heaviest first, then by name."""
    short = [
        r
        for r in records
        if r.get("applicable", True) and r["credit"] < 1.0 - COVERAGE_TOLERANCE
    ]
    return sorted(short, key=lambda r: (-r["weight"], r["element"]))


def assess_campaign(part_id, elements, mission_profile=None):
    """Grade the whole evaluation campaign standing behind one part type.

    Every element the class owes is graded, including the ones the declaration
    left out entirely -- an element nobody mentioned is absent, not excused --
    and excluding the ones the mission profile does not owe at all.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple, got %r" % (type(elements).__name__,))
    drivers = normalize_profile(mission_profile)
    declared = {}
    for raw in elements:
        element = normalize_element(raw)
        if element["element"] in declared:
            raise ValueError("duplicate campaign element %r" % (element["element"],))
        declared[element["element"]] = element
    records = []
    for name in sorted(ELEMENT_WEIGHTS):
        applicable = element_applicable(name, drivers)
        records.append(
            assess_element(
                declared.get(name, {"element": name, "state": "element-absent"}),
                applicable=applicable,
            )
        )
    coverage = campaign_coverage(records)
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"element": record["element"], "finding": finding})
    short = outstanding_elements(records)
    unwaivable_short = [
        r["element"]
        for r in records
        if r["element"] in UNWAIVABLE_ELEMENTS
        and r.get("applicable", True)
        and r["credit"] < 1.0 - COVERAGE_TOLERANCE
    ]
    at_threshold = meets_class_2_threshold(coverage)
    if unwaivable_short or not at_threshold:
        verdict = "evaluation-campaign-incomplete"
    elif findings:
        verdict = "evaluation-campaign-open-actions"
    else:
        verdict = "evaluation-campaign-complete"
    return {
        "part_id": part_id,
        "records": records,
        "applicable_elements": [r["element"] for r in records if r["applicable"]],
        "inapplicable_elements": [r["element"] for r in records if not r["applicable"]],
        "coverage_fraction": coverage,
        "meets_threshold": at_threshold,
        "outstanding_elements": [r["element"] for r in short],
        "unwaivable_shortfalls": unwaivable_short,
        "findings": findings,
        "verdict": verdict,
        "suitable_for_class_2": verdict == "evaluation-campaign-complete",
    }

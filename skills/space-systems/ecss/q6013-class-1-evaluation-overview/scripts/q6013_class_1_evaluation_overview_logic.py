"""Evaluation campaign coverage for Class 1 commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 4.2.3.1 (the evaluation a commercial part
undergoes before it can be used in the highest assurance class, taken as a
whole campaign rather than as one test).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The campaign is a set of elements, each carrying a weight that says how much
  of the assurance it supplies. A few of them are load-bearing: the
  manufacturer assessment, the construction analysis and the radiation
  evaluation answer questions nothing else in the campaign answers, so they
  cannot be waived and cannot be bought with similarity.
* Each element is in a state, and the state fixes the credit it earns.
  Performing it on the part type itself earns full credit. Claiming heritage
  earns full credit only when the claim survives the admissibility rules.
  Similarity to another part type earns partial credit and leaves a finding.
  An approved waiver earns credit but never silence. A plan, an unjustified
  waiver and an absent element all earn nothing.
* A heritage claim is admissible only when the same manufacturer, the same
  part number and the same assembly site are behind it, no process change has
  been notified since, and the evidence is inside its validity period. Every
  rule that fails is named, because each names a different repair.
* Coverage is the weighted credit over the total weight. It is a fraction, not
  a pass mark: a campaign is complete only when every element is fully
  covered, and the fraction exists to rank what is outstanding when it is not.
"""

from __future__ import annotations

import math

# Campaign elements and the share of the assurance each supplies.
ELEMENT_WEIGHTS = {
    "manufacturer-assessment": 1.0,
    "construction-analysis": 1.0,
    "radiation-evaluation": 1.0,
    "endurance-life-test": 1.0,
    "environmental-mechanical-test": 0.8,
    "electrical-characterisation-over-temperature": 0.8,
    "assembly-compatibility-check": 0.6,
    "materials-and-outgassing-review": 0.4,
}

# Elements that answer a question nothing else in the campaign answers.
MANDATORY_ELEMENTS = (
    "manufacturer-assessment",
    "construction-analysis",
    "radiation-evaluation",
)

# Credit earned by an element state, before the heritage and mandatory rules.
ELEMENT_STATE_CREDIT = {
    "performed-on-this-part-type": 1.0,
    "covered-by-heritage-claim": 1.0,
    "performed-on-similar-part-type": 0.5,
    "waived-with-approved-justification": 1.0,
    "waived-without-justification": 0.0,
    "planned-not-yet-performed": 0.0,
    "element-absent": 0.0,
}

# A heritage record older than this is outside its validity period.
HERITAGE_VALIDITY_MONTHS = 36

VERDICTS = (
    "evaluation-campaign-complete",
    "evaluation-campaign-open-actions",
    "evaluation-campaign-incomplete",
)

# Coverage is a ratio of sums of weights; a campaign that is materially
# complete can land a few units in the last place below one.
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


def heritage_admissible(claim):
    """Decide whether a heritage claim may stand in for a performed element.

    Returns ``(admissible, reasons)``; ``reasons`` names every rule that
    failed, because each one names a different repair.
    """
    if not isinstance(claim, dict):
        raise ValueError("heritage claim must be a mapping, got %r" % (type(claim).__name__,))
    reasons = []
    for key, reason in (
        ("same_manufacturer", "heritage-manufacturer-differs"),
        ("same_part_number", "heritage-part-number-differs"),
        ("same_assembly_site", "heritage-assembly-site-differs"),
    ):
        value = claim.get(key)
        if not isinstance(value, bool):
            raise ValueError("%s of a heritage claim must be a boolean, got %r" % (key, value))
        if not value:
            reasons.append(reason)
    notified = claim.get("process_change_notified", False)
    if not isinstance(notified, bool):
        raise ValueError(
            "process_change_notified must be a boolean, got %r" % (notified,)
        )
    if notified:
        reasons.append("heritage-superseded-by-process-change")
    age = _real(claim.get("evidence_age_months"), "evidence_age_months")
    if age < 0.0:
        raise ValueError("evidence_age_months must not be negative, got %r" % (age,))
    if age > float(HERITAGE_VALIDITY_MONTHS):
        reasons.append("heritage-evidence-out-of-validity")
    return (len(reasons) == 0, reasons)


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


def assess_element(raw):
    """Grade one campaign element into a credit and its findings."""
    element = normalize_element(raw)
    name = element["element"]
    state = element["state"]
    weight = element_weight(name)
    credit = state_credit(state)
    findings = []
    heritage_reasons = []
    if state == "covered-by-heritage-claim":
        admissible, heritage_reasons = heritage_admissible(element["heritage_claim"])
        if not admissible:
            credit = 0.0
            findings.append("heritage-claim-inadmissible")
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
    if name in MANDATORY_ELEMENTS and credit < 1.0 - COVERAGE_TOLERANCE:
        findings.append("mandatory-element-not-covered")
    if name in MANDATORY_ELEMENTS and state in (
        "waived-with-approved-justification",
        "performed-on-similar-part-type",
    ):
        credit = 0.0
        if "mandatory-element-not-covered" not in findings:
            findings.append("mandatory-element-not-covered")
    return {
        "element": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "heritage_reasons": heritage_reasons,
        "findings": findings,
    }


def campaign_coverage(records):
    """Weighted credit of a set of assessed elements over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a campaign must carry at least one element")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total campaign weight must be positive")
    return earned / total_weight


def outstanding_elements(records):
    """Elements short of full credit, heaviest first, then by element name."""
    short = [r for r in records if r["credit"] < 1.0 - COVERAGE_TOLERANCE]
    return sorted(short, key=lambda r: (-r["weight"], r["element"]))


def assess_campaign(part_id, elements):
    """Grade the whole evaluation campaign standing behind one part type.

    Every element the standard owes is graded, including the ones the
    declaration left out entirely -- an element nobody mentioned is absent,
    not excused.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple, got %r" % (type(elements).__name__,))
    declared = {}
    for raw in elements:
        element = normalize_element(raw)
        if element["element"] in declared:
            raise ValueError("duplicate campaign element %r" % (element["element"],))
        declared[element["element"]] = element
    records = []
    for name in sorted(ELEMENT_WEIGHTS):
        records.append(
            assess_element(declared.get(name, {"element": name, "state": "element-absent"}))
        )
    coverage = campaign_coverage(records)
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"element": record["element"], "finding": finding})
    short = outstanding_elements(records)
    if short:
        verdict = "evaluation-campaign-incomplete"
    elif findings:
        verdict = "evaluation-campaign-open-actions"
    else:
        verdict = "evaluation-campaign-complete"
    return {
        "part_id": part_id,
        "records": records,
        "coverage_fraction": coverage,
        "outstanding_elements": [r["element"] for r in short],
        "findings": findings,
        "verdict": verdict,
        "suitable_for_class_1": verdict == "evaluation-campaign-complete",
    }

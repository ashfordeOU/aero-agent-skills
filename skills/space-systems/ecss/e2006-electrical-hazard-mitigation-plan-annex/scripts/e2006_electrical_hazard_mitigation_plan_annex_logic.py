#!/usr/bin/env python3
"""ECSS-E-ST-20-06C Annex A -- electrical hazard mitigation plan content check.

Deterministic, offline, stdlib-only implementation of the Annex A document
procedure: confirm the plan carries every required section, categorize each
declared hazard into a family, score its assessment outcome on the
severity-by-likelihood grid, credit only the mitigations whose verification
has actually progressed, recompute the residual risk, and decide whether the
annex is ready for release.

The standard is referenced as the procedural anchor only; every rule here is
a paraphrased, implementable engineering procedure.
"""

from __future__ import annotations

import math

# --- model constants ----------------------------------------------------
#: Weighted residual score at or below which the annex is releasable.
DEFAULT_ACCEPTANCE_SCORE = 6.0
#: Relative tolerance applied to a score sitting exactly on the acceptance
#: threshold. Representation error must never turn a compliant annex red.
SCORE_TOLERANCE_REL = 1e-9
SCORE_TOLERANCE_ABS = 1e-12

#: Sections the Annex A plan document has to carry, in reading order.
REQUIRED_SECTIONS = (
    "scope-and-applicability",
    "applicable-and-reference-documents",
    "hazard-inventory",
    "assessment-outcomes",
    "mitigation-measures",
    "verification-status",
    "residual-risk-statement",
)

#: Optional sections a project may add without affecting completeness.
OPTIONAL_SECTIONS = (
    "configuration-baseline",
    "open-work-and-waivers",
    "responsibility-matrix",
)

#: Electrical hazards the annex may declare, each mapped to its family.
HAZARD_TYPES = {
    "surface-charging-differential": "electrostatic",
    "internal-charging-deep-dielectric": "electrostatic",
    "electrostatic-discharge-arc": "electrostatic",
    "plume-induced-erosion": "propulsion-interaction",
    "thruster-beam-neutralization-loss": "propulsion-interaction",
    "induced-plasma-coupling": "propulsion-interaction",
    "arc-tracking-in-harness": "power-distribution",
    "insulation-breakdown-low-pressure": "power-distribution",
    "bonding-discontinuity": "grounding-and-bonding",
    "structure-return-current-loop": "grounding-and-bonding",
}

SEVERITY_RANK = {
    "negligible": 1,
    "marginal": 2,
    "critical": 3,
    "catastrophic": 4,
}

LIKELIHOOD_RANK = {
    "improbable": 1,
    "remote": 2,
    "occasional": 3,
    "probable": 4,
}

RISK_BANDS = ("acceptable", "tolerable-with-review", "unacceptable")
UNACCEPTABLE_INDEX = 12
TOLERABLE_INDEX = 6

#: Mitigation classes, the rank credit each earns once verified, and the
#: axis of the risk grid it acts on.
MITIGATION_CLASSES = {
    "grounding-bond": {"credit": 1, "reduces": "likelihood"},
    "conductive-surface-treatment": {"credit": 2, "reduces": "likelihood"},
    "shielding-augmentation": {"credit": 2, "reduces": "likelihood"},
    "operational-constraint": {"credit": 1, "reduces": "likelihood"},
    "material-substitution": {"credit": 2, "reduces": "likelihood"},
    "filter-network": {"credit": 1, "reduces": "severity"},
    "redundant-return-path": {"credit": 2, "reduces": "severity"},
}

VERIFICATION_METHODS = (
    "analysis",
    "test-campaign",
    "inspection",
    "review-of-design",
    "similarity",
)

VERIFICATION_STATES = ("open", "in-progress", "closed")
#: Credit a mitigation earns while its verification is still running.
PROVISIONAL_CREDIT_CAP = 1


def _positive(value, label):
    """Return value as a strictly positive float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def categorize_hazard(hazard_type):
    """Return the family an electrical hazard type belongs to."""
    if hazard_type not in HAZARD_TYPES:
        raise ValueError("unknown electrical hazard type %r" % (hazard_type,))
    return HAZARD_TYPES[hazard_type]


def risk_index(severity, likelihood):
    """Grid index of an assessment outcome: severity rank times likelihood rank."""
    if severity not in SEVERITY_RANK:
        raise ValueError("unknown severity %r" % (severity,))
    if likelihood not in LIKELIHOOD_RANK:
        raise ValueError("unknown likelihood %r" % (likelihood,))
    return SEVERITY_RANK[severity] * LIKELIHOOD_RANK[likelihood]


def categorize_risk(index):
    """Place a grid index in one of RISK_BANDS."""
    try:
        value = int(index)
    except (TypeError, ValueError):
        raise ValueError("risk index must be an integer, got %r" % (index,))
    if value != index or not (1 <= value <= 16):
        raise ValueError("risk index must lie in [1, 16], got %r" % (index,))
    if value >= UNACCEPTABLE_INDEX:
        return "unacceptable"
    if value >= TOLERABLE_INDEX:
        return "tolerable-with-review"
    return "acceptable"


def validate_hazard(record):
    """Validate one declared hazard and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("hazard record must be a mapping, got %r" % (record,))
    hazard_id = record.get("hazard_id")
    if not hazard_id:
        raise ValueError("hazard record missing hazard_id")
    hazard_type = record.get("hazard_type")
    family = categorize_hazard(hazard_type)
    severity = record.get("severity")
    likelihood = record.get("likelihood")
    index = risk_index(severity, likelihood)
    weight = _positive(record.get("exposure_weight", 1.0), "exposure_weight")
    return {
        "hazard_id": hazard_id,
        "hazard_type": hazard_type,
        "family": family,
        "severity": severity,
        "likelihood": likelihood,
        "severity_rank": SEVERITY_RANK[severity],
        "likelihood_rank": LIKELIHOOD_RANK[likelihood],
        "initial_index": index,
        "initial_band": categorize_risk(index),
        "exposure_weight": weight,
    }


def validate_mitigation(record):
    """Validate one mitigation entry and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("mitigation record must be a mapping, got %r" % (record,))
    mitigation_id = record.get("mitigation_id")
    if not mitigation_id:
        raise ValueError("mitigation record missing mitigation_id")
    hazard_id = record.get("hazard_id")
    if not hazard_id:
        raise ValueError("mitigation %s missing hazard_id" % mitigation_id)
    mitigation_class = record.get("mitigation_class")
    if mitigation_class not in MITIGATION_CLASSES:
        raise ValueError(
            "mitigation %s: unknown mitigation class %r"
            % (mitigation_id, mitigation_class)
        )
    method = record.get("verification_method")
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "mitigation %s: unknown verification method %r" % (mitigation_id, method)
        )
    status = record.get("verification_status")
    if status not in VERIFICATION_STATES:
        raise ValueError(
            "mitigation %s: unknown verification status %r" % (mitigation_id, status)
        )
    return {
        "mitigation_id": mitigation_id,
        "hazard_id": hazard_id,
        "mitigation_class": mitigation_class,
        "verification_method": method,
        "verification_status": status,
    }


def mitigation_credit(mitigation):
    """Rank credit a mitigation earns, and the grid axis it acts on.

    A closed verification earns the full credit of its class; a running one
    earns a capped provisional credit; an open one earns nothing at all.
    """
    entry = validate_mitigation(mitigation)
    spec = MITIGATION_CLASSES[entry["mitigation_class"]]
    status = entry["verification_status"]
    if status == "closed":
        credit = spec["credit"]
    elif status == "in-progress":
        credit = min(spec["credit"], PROVISIONAL_CREDIT_CAP)
    else:
        credit = 0
    return credit, spec["reduces"]


def check_sections(sections):
    """Return the required Annex A sections absent from *sections*."""
    if not isinstance(sections, (list, tuple, set)):
        raise ValueError("sections must be a list, tuple or set, got %r" % (sections,))
    present = set(sections)
    known = set(REQUIRED_SECTIONS) | set(OPTIONAL_SECTIONS)
    for name in present:
        if name not in known:
            raise ValueError("unknown annex section %r" % (name,))
    return [name for name in REQUIRED_SECTIONS if name not in present]


def residual_risk(hazard, mitigations):
    """Recompute a hazard grid position after crediting its mitigations."""
    haz = validate_hazard(hazard)
    severity_credit = 0
    likelihood_credit = 0
    applied = []
    findings = []
    for raw in mitigations:
        entry = validate_mitigation(raw)
        if entry["hazard_id"] != haz["hazard_id"]:
            continue
        credit, axis = mitigation_credit(entry)
        if axis == "severity":
            severity_credit += credit
        else:
            likelihood_credit += credit
        applied.append(
            {
                "mitigation_id": entry["mitigation_id"],
                "mitigation_class": entry["mitigation_class"],
                "verification_status": entry["verification_status"],
                "credit": credit,
                "axis": axis,
            }
        )
        if entry["verification_status"] == "open":
            findings.append(
                "hazard %s: mitigation %s has an open verification and earns no "
                "credit" % (haz["hazard_id"], entry["mitigation_id"])
            )
    if not applied:
        findings.append(
            "hazard %s: no mitigation is recorded against it" % haz["hazard_id"]
        )
    residual_severity = max(1, haz["severity_rank"] - severity_credit)
    residual_likelihood = max(1, haz["likelihood_rank"] - likelihood_credit)
    index = residual_severity * residual_likelihood
    band = categorize_risk(index)
    if band == "unacceptable":
        findings.append(
            "hazard %s: residual risk remains unacceptable at index %d"
            % (haz["hazard_id"], index)
        )
    return {
        "hazard_id": haz["hazard_id"],
        "family": haz["family"],
        "initial_index": haz["initial_index"],
        "initial_band": haz["initial_band"],
        "residual_severity_rank": residual_severity,
        "residual_likelihood_rank": residual_likelihood,
        "residual_index": index,
        "residual_band": band,
        "exposure_weight": haz["exposure_weight"],
        "mitigations": applied,
        "findings": findings,
    }


def weighted_residual_score(results):
    """Exposure-weighted mean of the residual grid indices."""
    if not results:
        raise ValueError("at least one residual result is required")
    total_weight = 0.0
    total = 0.0
    for result in results:
        weight = _positive(result["exposure_weight"], "exposure_weight")
        total += result["residual_index"] * weight
        total_weight += weight
    return total / total_weight


def _within_threshold(score, threshold):
    """Score is acceptable when it is below, or numerically on, the threshold."""
    if score <= threshold:
        return True
    return math.isclose(
        score, threshold, rel_tol=SCORE_TOLERANCE_REL, abs_tol=SCORE_TOLERANCE_ABS
    )


def assess_plan_annex(annex, acceptance_score=DEFAULT_ACCEPTANCE_SCORE):
    """Run the Annex A content and readiness check over a plan document.

    Returns the missing sections, the per-hazard residual results, the
    weighted score, every finding raised, and whether the annex is ready.
    """
    if not isinstance(annex, dict):
        raise ValueError("annex must be a mapping, got %r" % (annex,))
    threshold = _positive(acceptance_score, "acceptance_score")
    hazards = annex.get("hazards")
    if not hazards:
        raise ValueError("annex must declare at least one hazard")
    mitigations = annex.get("mitigations", [])
    missing = check_sections(annex.get("sections", []))

    findings = ["annex section %r is missing" % name for name in missing]
    hazard_ids = set()
    results = []
    for hazard in hazards:
        result = residual_risk(hazard, mitigations)
        if result["hazard_id"] in hazard_ids:
            raise ValueError("duplicate hazard_id %r" % (result["hazard_id"],))
        hazard_ids.add(result["hazard_id"])
        results.append(result)
        findings.extend(result["findings"])

    for raw in mitigations:
        entry = validate_mitigation(raw)
        if entry["hazard_id"] not in hazard_ids:
            findings.append(
                "mitigation %s points at hazard %s, which the inventory does not "
                "declare" % (entry["mitigation_id"], entry["hazard_id"])
            )

    score = weighted_residual_score(results)
    within = _within_threshold(score, threshold)
    if not within:
        findings.append(
            "weighted residual score %.4f exceeds the acceptance threshold %.4f"
            % (score, threshold)
        )
    worst = max(results, key=lambda r: r["residual_index"])
    return {
        "missing_sections": missing,
        "hazards": results,
        "weighted_residual_score": score,
        "acceptance_score": threshold,
        "worst_hazard_id": worst["hazard_id"],
        "worst_residual_index": worst["residual_index"],
        "findings": findings,
        "ready_for_release": within and not findings,
    }

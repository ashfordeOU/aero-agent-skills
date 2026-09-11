#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.3 environment-driven margins (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space-systems standard requires every radiation environment assessment to
carry an explicit margin approach -- either deterministic (apply a radiation
design margin factor to the predicted total ionising dose) or probabilistic
(agree a confidence level with the customer or authority and confirm the
model run meets it). For missions in geostationary orbit an AE-8 worst-case
exemption is available when the mission epoch within the solar cycle is
uncertain; the exemption is orbit-specific and does not extend to MEO or HEO.
Model-uncertainty evidence (model name, version, and known uncertainty factors)
must be on record before the environment input is released to design.

The minimum RDM factor below is illustrative. Real projects must substitute
their approved minimum from the applicable project radiation control plan.
"""

MARGIN_APPROACH_DETERMINISTIC = "deterministic"
MARGIN_APPROACH_PROBABILISTIC = "probabilistic"
MARGIN_APPROACHES = frozenset(
    {MARGIN_APPROACH_DETERMINISTIC, MARGIN_APPROACH_PROBABILISTIC}
)

ORBIT_GEO = "geo"
ORBIT_LEO = "leo"
ORBIT_MEO = "meo"
ORBIT_HEO = "heo"
ORBIT_TYPES = frozenset({ORBIT_GEO, ORBIT_LEO, ORBIT_MEO, ORBIT_HEO})

AE8_MODEL_NAMES = frozenset({"ae8", "ae8_max", "ae8_min"})
TRAPPED_ELECTRON_MODELS = AE8_MODEL_NAMES | frozenset({"ae9", "ae9_max", "ae9_min"})

# Illustrative minimum -- projects must substitute their approved value.
MIN_RDM_FACTOR = 2.0

# Required fields for model-uncertainty documentation.
_UNCERTAINTY_REQUIRED_FIELDS = frozenset({"model_name", "model_version", "uncertainty_factors"})


def categorize_margin_approach(approach):
    """Return the approach string unchanged after confirming it is one of the
    two recognised values. Raises ValueError for any other string."""
    if approach not in MARGIN_APPROACHES:
        raise ValueError(
            "unrecognized margin approach %r; must be one of %r"
            % (approach, sorted(MARGIN_APPROACHES))
        )
    return approach


def check_ae8_geo_exemption(orbit_type, model_name, use_worst_case):
    """Determine whether the AE-8 worst-case GEO trapped-electron exemption
    applies for the given orbit, model, and worst-case flag.

    Returns True only when orbit_type is 'geo', model_name is an AE-8 variant,
    and use_worst_case is True. Returns False in all other valid combinations.
    Raises ValueError for unrecognized orbit_type or model_name.
    """
    if orbit_type not in ORBIT_TYPES:
        raise ValueError(
            "unrecognized orbit type %r; must be one of %r"
            % (orbit_type, sorted(ORBIT_TYPES))
        )
    if model_name not in TRAPPED_ELECTRON_MODELS:
        raise ValueError(
            "unrecognized trapped-electron model %r; must be one of %r"
            % (model_name, sorted(TRAPPED_ELECTRON_MODELS))
        )
    return orbit_type == ORBIT_GEO and model_name in AE8_MODEL_NAMES and bool(use_worst_case)


def compute_design_dose(total_dose, rdm_factor):
    """Design dose = total_dose * rdm_factor.

    Raises ValueError when total_dose or rdm_factor is not a real number,
    or when rdm_factor is below MIN_RDM_FACTOR.
    """
    if isinstance(total_dose, bool) or not isinstance(total_dose, (int, float)):
        raise ValueError(
            "total_dose must be a real number, got %r" % (total_dose,)
        )
    if isinstance(rdm_factor, bool) or not isinstance(rdm_factor, (int, float)):
        raise ValueError(
            "rdm_factor must be a real number, got %r" % (rdm_factor,)
        )
    if rdm_factor < MIN_RDM_FACTOR:
        raise ValueError(
            "rdm_factor %r is below the project minimum %r; a formal reduced-margin "
            "approval is required before using a lower value" % (rdm_factor, MIN_RDM_FACTOR)
        )
    return total_dose * rdm_factor


def validate_probabilistic_agreement(confidence_level, agreed_level):
    """Return True when confidence_level meets or exceeds agreed_level.

    Both values must be in the range (0, 1]. Raises ValueError otherwise.
    """
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise ValueError(
            "confidence_level must be a real number in (0, 1], got %r"
            % (confidence_level,)
        )
    if isinstance(agreed_level, bool) or not isinstance(agreed_level, (int, float)):
        raise ValueError(
            "agreed_level must be a real number in (0, 1], got %r"
            % (agreed_level,)
        )
    if not (0 < confidence_level <= 1):
        raise ValueError(
            "confidence_level %r is out of range (0, 1]" % (confidence_level,)
        )
    if not (0 < agreed_level <= 1):
        raise ValueError(
            "agreed_level %r is out of range (0, 1]" % (agreed_level,)
        )
    return confidence_level >= agreed_level


def check_model_uncertainty_documented(evidence):
    """Return a sorted list of missing required field names from the evidence
    dict. An empty list means documentation is complete.

    Required fields: 'model_name', 'model_version', 'uncertainty_factors'.
    """
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a dict, got %r" % type(evidence).__name__)
    return sorted(_UNCERTAINTY_REQUIRED_FIELDS - set(evidence.keys()))


def assess_margins(assessment):
    """Full §5.3 environment-driven margin assessment for one spacecraft item.

    assessment keys:
      item_id                  str   -- identifier for findings
      orbit_type               str   -- one of ORBIT_TYPES
      trapped_electron_model   str   -- one of TRAPPED_ELECTRON_MODELS
      use_worst_case_geo       bool  -- whether the AE-8 GEO worst-case flag is set
      margin_approach          str   -- "deterministic" or "probabilistic"
      model_uncertainty_evidence dict -- must contain model_name, model_version,
                                         uncertainty_factors
      total_dose               float -- required for deterministic approach (krad Si)
      rdm_factor               float -- required for deterministic approach
      confidence_level         float -- required for probabilistic approach (0, 1]
      agreed_confidence_level  float -- required for probabilistic approach (0, 1]

    Returns:
      {
        "findings": list of finding dicts (empty => compliant),
        "design_dose": float or None,
        "geo_exemption_applies": bool,
        "probability_agreement_met": bool or None,
      }

    Raises ValueError for unrecognized orbit_type, model, or margin_approach.
    """
    item_id = assessment["item_id"]
    findings = []

    approach = assessment["margin_approach"]
    try:
        categorize_margin_approach(approach)
    except ValueError as exc:
        raise ValueError("item %r: %s" % (item_id, str(exc)))

    orbit_type = assessment["orbit_type"]
    model_name = assessment["trapped_electron_model"]
    try:
        geo_exemption = check_ae8_geo_exemption(
            orbit_type, model_name, assessment.get("use_worst_case_geo", False)
        )
    except ValueError as exc:
        raise ValueError("item %r: %s" % (item_id, str(exc)))

    evidence = assessment.get("model_uncertainty_evidence", {})
    missing_fields = check_model_uncertainty_documented(evidence)
    for field in missing_fields:
        findings.append(
            {
                "issue": "missing_model_uncertainty_evidence",
                "item": item_id,
                "missing_field": field,
            }
        )

    design_dose = None
    if approach == MARGIN_APPROACH_DETERMINISTIC:
        total_dose = assessment.get("total_dose")
        rdm_factor = assessment.get("rdm_factor")
        if total_dose is None:
            findings.append({"issue": "missing_total_dose", "item": item_id})
        elif rdm_factor is None:
            findings.append({"issue": "missing_rdm_factor", "item": item_id})
        else:
            try:
                design_dose = compute_design_dose(total_dose, rdm_factor)
            except ValueError as exc:
                findings.append(
                    {"issue": "rdm_error", "item": item_id, "detail": str(exc)}
                )

    prob_agreement_met = None
    if approach == MARGIN_APPROACH_PROBABILISTIC:
        confidence_level = assessment.get("confidence_level")
        agreed_level = assessment.get("agreed_confidence_level")
        if confidence_level is None:
            findings.append({"issue": "missing_confidence_level", "item": item_id})
        elif agreed_level is None:
            findings.append(
                {"issue": "missing_agreed_confidence_level", "item": item_id}
            )
        else:
            try:
                prob_agreement_met = validate_probabilistic_agreement(
                    confidence_level, agreed_level
                )
                if not prob_agreement_met:
                    findings.append(
                        {
                            "issue": "confidence_level_below_agreed",
                            "item": item_id,
                            "confidence_level": confidence_level,
                            "agreed_level": agreed_level,
                        }
                    )
            except ValueError as exc:
                findings.append(
                    {
                        "issue": "confidence_level_error",
                        "item": item_id,
                        "detail": str(exc),
                    }
                )

    return {
        "findings": findings,
        "design_dose": design_dose,
        "geo_exemption_applies": geo_exemption,
        "probability_agreement_met": prob_agreement_met,
    }


def is_margin_compliant(result):
    """True when an assess_margins result carries no findings."""
    return len(result["findings"]) == 0

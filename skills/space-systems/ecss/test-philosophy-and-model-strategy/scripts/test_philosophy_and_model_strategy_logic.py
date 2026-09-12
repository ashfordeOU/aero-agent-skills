#!/usr/bin/env python3
"""ECSS-E-ST-32C clauses 4.6.3.1-4.6.3.6 structural model philosophy and
test campaign logic (paraphrase, not copy).

Paraphrase of common-knowledge content: E-ST-32C organises the structural
verification programme around three test phases. Development testing is
performed early on non-flight articles to reduce design risk; it has no
fixed contractual level. Qualification testing demonstrates design margins
on a dedicated article that is not subsequently flown. Acceptance testing
screens each flight unit for workmanship defects at levels strictly below
the qualification test level, so that the flight unit is not fatigue-
penalised by re-qualification loading. Each article is assigned to exactly
one of three categories: development article (PTM, STM), qualification
article (QM), or flight article (FM or PFM). The proto-flight model runs
its qualification test at qualification levels with a reduced duration
relative to a dedicated QM. Qualification by similarity is permitted when
the design, materials, manufacturing process, and target environment of the
candidate item are no more demanding than those of a previously qualified
reference item.
"""

VALID_MODEL_TYPES = frozenset({"PTM", "PFM", "QM", "FM", "STM"})
VALID_TEST_PHASES = frozenset(
    {"development_test", "qualification_test", "acceptance_test"}
)
VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})

MODEL_REQUIRED_PHASES = {
    "PTM": frozenset({"development_test"}),
    "STM": frozenset({"development_test"}),
    "QM":  frozenset({"qualification_test"}),
    "FM":  frozenset({"acceptance_test"}),
    "PFM": frozenset({"qualification_test", "acceptance_test"}),
}

FLIGHT_INTENDED = {
    "PTM": False,
    "STM": False,
    "QM":  False,
    "FM":  True,
    "PFM": True,
}

# Minimum fraction of the QM reference duration allowed for a PFM qualification test
PFM_MIN_DURATION_FRACTION = 0.25


def categorize_model(model_type):
    """Article category for a model type: "development_article" for PTM and
    STM, "qualification_article" for QM, "flight_article" for FM and PFM.
    Raises ValueError for an unrecognized model type."""
    if model_type not in VALID_MODEL_TYPES:
        raise ValueError(
            "unrecognized model type %r under E-ST-32C clause 4.6.3" % (model_type,)
        )
    if model_type in {"PTM", "STM"}:
        return "development_article"
    if model_type == "QM":
        return "qualification_article"
    return "flight_article"


def required_test_phases(model_type):
    """Frozenset of test phases required for a model type under E-ST-32C
    4.6.3.1-4.6.3.4. Raises ValueError for an unrecognized model type."""
    if model_type not in VALID_MODEL_TYPES:
        raise ValueError(
            "unrecognized model type %r under E-ST-32C clause 4.6.3" % (model_type,)
        )
    return MODEL_REQUIRED_PHASES[model_type]


def is_flight_intended(model_type):
    """True when the model type is intended to be the operational flight unit.
    FM and PFM are flight-intended; PTM, STM, and QM are not.
    Raises ValueError for an unrecognized model type."""
    if model_type not in VALID_MODEL_TYPES:
        raise ValueError(
            "unrecognized model type %r under E-ST-32C clause 4.6.3" % (model_type,)
        )
    return FLIGHT_INTENDED[model_type]


def select_qualification_strategy(num_flight_units, risk_level, schedule_constraint_binds):
    """Qualification strategy string for a programme.

    num_flight_units: number of flight units planned (must be >= 1).
    risk_level: "low", "medium", or "high".
    schedule_constraint_binds: True when schedule precludes a dedicated QM.

    Returns one of:
      "ptm_plus_fm"  — separate development PTM, then FM at acceptance only;
      "proto_flight" — single PFM: qualified (reduced duration) then accepted;
      "qm_plus_fm"   — dedicated QM plus one or more FM at acceptance only.

    Raises ValueError for invalid inputs.
    """
    if num_flight_units < 1:
        raise ValueError("num_flight_units must be >= 1")
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            "unrecognized risk_level %r; must be one of %r"
            % (risk_level, sorted(VALID_RISK_LEVELS))
        )
    if num_flight_units > 1:
        return "qm_plus_fm"
    # Single flight unit path
    if schedule_constraint_binds:
        return "proto_flight"
    if risk_level == "high":
        return "ptm_plus_fm"
    return "proto_flight"


def check_test_level(test_phase, test_level, reference_level):
    """Violation list (empty if valid) for a test level against a reference.

    For qualification_test: test_level must be >= reference_level (the minimum
    required qualification level including the specified margin over spec).
    For acceptance_test: test_level must be strictly less than reference_level
    (the qualification test level — acceptance must be less severe to avoid
    fatigue-penalising the flight unit).
    For development_test: no level constraint; always returns an empty list.

    Raises ValueError for a negative level or an unrecognized test phase.
    """
    if test_level < 0:
        raise ValueError("test_level must be >= 0")
    if reference_level < 0:
        raise ValueError("reference_level must be >= 0")
    if test_phase not in VALID_TEST_PHASES:
        raise ValueError("unrecognized test_phase %r" % (test_phase,))
    if test_phase == "development_test":
        return []
    if test_phase == "qualification_test":
        if test_level < reference_level:
            return [
                {
                    "issue": "qualification_level_not_met",
                    "test_phase": test_phase,
                    "test_level": test_level,
                    "required_minimum": reference_level,
                }
            ]
        return []
    # acceptance_test
    if test_level >= reference_level:
        return [
            {
                "issue": "acceptance_level_at_or_above_qualification",
                "test_phase": test_phase,
                "test_level": test_level,
                "qualification_test_level": reference_level,
            }
        ]
    return []


def check_pfm_duration(pfm_duration_s, qm_reference_duration_s):
    """Violation list (empty if valid) for a PFM qualification test duration.

    A PFM qualification test is run at qualification levels but with a
    reduced duration. pfm_duration_s must be strictly less than
    qm_reference_duration_s and at least PFM_MIN_DURATION_FRACTION of it.

    Raises ValueError for non-positive durations.
    """
    if pfm_duration_s <= 0:
        raise ValueError("pfm_duration_s must be > 0")
    if qm_reference_duration_s <= 0:
        raise ValueError("qm_reference_duration_s must be > 0")
    if pfm_duration_s >= qm_reference_duration_s:
        return [
            {
                "issue": "pfm_duration_not_reduced",
                "pfm_duration_s": pfm_duration_s,
                "qm_reference_duration_s": qm_reference_duration_s,
            }
        ]
    minimum_s = PFM_MIN_DURATION_FRACTION * qm_reference_duration_s
    if pfm_duration_s < minimum_s:
        return [
            {
                "issue": "pfm_duration_below_minimum_fraction",
                "pfm_duration_s": pfm_duration_s,
                "minimum_duration_s": minimum_s,
            }
        ]
    return []


def check_similarity(reference, candidate):
    """Similarity assessment for qualification-by-similarity.

    reference: {
        "item_id": str, "is_qualified": bool, "design_version": str,
        "qualification_environment": {"random_grms": float, "sine_g": float,
                                       "shock_srs_g": float},
        "material_spec": str, "manufacturing_process": str
    }
    candidate: {
        "item_id": str, "design_version": str,
        "target_environment": {"random_grms": float, "sine_g": float,
                                "shock_srs_g": float},
        "material_spec": str, "manufacturing_process": str
    }

    Returns {"is_similar": bool, "findings": list}. Similarity holds only when
    the reference is qualified, the design version, material spec, and
    manufacturing process match exactly, and no target environment field
    exceeds the reference qualification environment. Does not mutate inputs.
    """
    findings = []
    if not reference.get("is_qualified", False):
        findings.append(
            {"issue": "reference_not_qualified", "reference_id": reference["item_id"]}
        )
    if reference.get("design_version") != candidate.get("design_version"):
        findings.append(
            {
                "issue": "design_version_differs",
                "reference": reference.get("design_version"),
                "candidate": candidate.get("design_version"),
            }
        )
    if reference.get("material_spec") != candidate.get("material_spec"):
        findings.append(
            {
                "issue": "material_spec_differs",
                "reference": reference.get("material_spec"),
                "candidate": candidate.get("material_spec"),
            }
        )
    if reference.get("manufacturing_process") != candidate.get("manufacturing_process"):
        findings.append(
            {
                "issue": "manufacturing_process_differs",
                "reference": reference.get("manufacturing_process"),
                "candidate": candidate.get("manufacturing_process"),
            }
        )
    ref_env = reference.get("qualification_environment", {})
    cand_env = candidate.get("target_environment", {})
    for field in ("random_grms", "sine_g", "shock_srs_g"):
        ref_val = ref_env.get(field, 0.0)
        cand_val = cand_env.get(field, 0.0)
        if cand_val > ref_val:
            findings.append(
                {
                    "issue": "environment_more_severe",
                    "field": field,
                    "reference_qualification_value": ref_val,
                    "candidate_target_value": cand_val,
                }
            )
    return {"is_similar": len(findings) == 0, "findings": findings}


def validate_test_campaign(model_type, test_records):
    """Full test campaign validation for a model article.

    model_type: one of VALID_MODEL_TYPES.
    test_records: list of {
        "phase": str,              # test phase performed
        "test_level": float,       # level at which the test was run
        "reference_level": float,  # minimum qual level (for QT) or qual level (for AT)
    }

    Returns {"valid": bool, "findings": list}. Findings arise when the model
    type is unrecognized, a test phase in the records is not required for the
    model type, a required phase has no record, or a test level is invalid for
    its phase. Does not mutate test_records.
    """
    if model_type not in VALID_MODEL_TYPES:
        return {
            "valid": False,
            "findings": [{"issue": "unrecognized_model_type", "model_type": model_type}],
        }
    required = required_test_phases(model_type)
    performed = set()
    findings = []
    for record in test_records:
        phase = record["phase"]
        if phase not in required:
            findings.append(
                {
                    "issue": "phase_not_required_for_model_type",
                    "phase": phase,
                    "model_type": model_type,
                }
            )
            continue
        performed.add(phase)
        findings.extend(
            check_test_level(phase, record["test_level"], record["reference_level"])
        )
    for phase in required:
        if phase not in performed:
            findings.append(
                {
                    "issue": "required_phase_not_performed",
                    "phase": phase,
                    "model_type": model_type,
                }
            )
    return {"valid": len(findings) == 0, "findings": findings}

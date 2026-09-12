"""
e1012_bg_experimental_logic.py

ECSS-E-ST-10C §10.4.8 — Experimental irradiation data in background assessments.

Implements deterministic procedures for:
  - validating experimental irradiation data records
  - comparing measurements against reference environment model values
  - determining whether experimental data supersede or supplement a model
  - computing combined background assessment values with propagated uncertainty
  - checking data provenance completeness
"""

VALID_PARTICLE_TYPES = {"proton", "electron", "heavy_ion", "gamma"}
VALID_QUANTITIES = {"flux", "fluence", "dose_rate", "dose"}
VALID_QUALITY_FLAGS = {"valid", "suspect", "invalid"}

REQUIRED_EXPERIMENTAL_FIELDS = frozenset({
    "source", "particle_type", "quantity", "value",
    "uncertainty_pct", "duration_s", "quality_flag", "provenance",
})
REQUIRED_REFERENCE_FIELDS = frozenset({
    "particle_type", "quantity", "value", "model_name",
})

MAX_SUPERSEDE_UNCERTAINTY_PCT = 20.0
MAX_OFFSET_FOR_SUPERSEDE_PCT = 50.0
DEFAULT_MODEL_UNCERTAINTY_PCT = 30.0


class AssessmentError(ValueError):
    """Raised when a record is invalid or assessment inputs are inconsistent."""


def validate_experimental_record(record):
    """
    Validate an experimental irradiation data record.
    Returns (is_valid: bool, issues: list[str]).
    """
    issues = []

    missing = REQUIRED_EXPERIMENTAL_FIELDS - set(record.keys())
    if missing:
        issues.append("Missing required fields: {}".format(sorted(missing)))
        return False, issues

    if record["particle_type"] not in VALID_PARTICLE_TYPES:
        issues.append(
            "Invalid particle_type '{}'; expected one of {}".format(
                record["particle_type"], sorted(VALID_PARTICLE_TYPES)
            )
        )

    if record["quantity"] not in VALID_QUANTITIES:
        issues.append(
            "Invalid quantity '{}'; expected one of {}".format(
                record["quantity"], sorted(VALID_QUANTITIES)
            )
        )

    if not isinstance(record["value"], (int, float)):
        issues.append("'value' must be numeric")
    elif record["value"] < 0:
        issues.append("'value' must be >= 0, got {}".format(record["value"]))

    if not isinstance(record["uncertainty_pct"], (int, float)):
        issues.append("'uncertainty_pct' must be numeric")
    elif not (0 < record["uncertainty_pct"] <= 100):
        issues.append(
            "'uncertainty_pct' must be in (0, 100], got {}".format(
                record["uncertainty_pct"]
            )
        )

    if not isinstance(record["duration_s"], (int, float)):
        issues.append("'duration_s' must be numeric")
    elif record["duration_s"] <= 0:
        issues.append("'duration_s' must be > 0, got {}".format(record["duration_s"]))

    if record["quality_flag"] not in VALID_QUALITY_FLAGS:
        issues.append(
            "Invalid quality_flag '{}'; expected one of {}".format(
                record["quality_flag"], sorted(VALID_QUALITY_FLAGS)
            )
        )

    if not isinstance(record["source"], str) or not record["source"].strip():
        issues.append("'source' must be a non-empty string")

    if not isinstance(record["provenance"], str) or not record["provenance"].strip():
        issues.append("'provenance' must be a non-empty string")

    return len(issues) == 0, issues


def validate_reference_record(record):
    """
    Validate a reference environment model record.
    Returns (is_valid: bool, issues: list[str]).
    """
    issues = []

    missing = REQUIRED_REFERENCE_FIELDS - set(record.keys())
    if missing:
        issues.append("Missing required fields: {}".format(sorted(missing)))
        return False, issues

    if record["particle_type"] not in VALID_PARTICLE_TYPES:
        issues.append(
            "Invalid particle_type '{}'; expected one of {}".format(
                record["particle_type"], sorted(VALID_PARTICLE_TYPES)
            )
        )

    if record["quantity"] not in VALID_QUANTITIES:
        issues.append(
            "Invalid quantity '{}'; expected one of {}".format(
                record["quantity"], sorted(VALID_QUANTITIES)
            )
        )

    if not isinstance(record["value"], (int, float)):
        issues.append("'value' must be numeric")
    elif record["value"] <= 0:
        issues.append(
            "Reference 'value' must be > 0, got {}".format(record["value"])
        )

    if not isinstance(record["model_name"], str) or not record["model_name"].strip():
        issues.append("'model_name' must be a non-empty string")

    return len(issues) == 0, issues


def compute_offset_pct(experimental, reference):
    """
    Compute the signed percentage offset of the experimental value from the
    reference model value: (experimental - reference) / reference * 100.

    Raises AssessmentError if the records cover different particle_type or
    quantity, or if the reference value is zero.
    """
    if experimental["particle_type"] != reference["particle_type"]:
        raise AssessmentError(
            "Cannot compare records with different particle_type: '{}' vs '{}'".format(
                experimental["particle_type"], reference["particle_type"]
            )
        )
    if experimental["quantity"] != reference["quantity"]:
        raise AssessmentError(
            "Cannot compare records with different quantity: '{}' vs '{}'".format(
                experimental["quantity"], reference["quantity"]
            )
        )
    if reference["value"] == 0:
        raise AssessmentError(
            "Reference value is zero; cannot compute percentage offset"
        )
    return (experimental["value"] - reference["value"]) / reference["value"] * 100.0


def assess_supersedes_model(experimental, offset_pct):
    """
    Determine whether experimental data supersede the reference model.
    Returns (supersedes: bool, rationale: str).

    All three criteria must hold for supersedure:
      1. quality_flag == "valid"
      2. uncertainty_pct <= MAX_SUPERSEDE_UNCERTAINTY_PCT
      3. |offset_pct| <= MAX_OFFSET_FOR_SUPERSEDE_PCT
    """
    if experimental["quality_flag"] != "valid":
        return False, (
            "quality_flag is '{}'; only 'valid' records may supersede the "
            "reference model".format(experimental["quality_flag"])
        )

    if experimental["uncertainty_pct"] > MAX_SUPERSEDE_UNCERTAINTY_PCT:
        return False, (
            "uncertainty_pct {:.1f}% exceeds threshold {:.1f}%; data supplements "
            "but does not supersede the model".format(
                experimental["uncertainty_pct"], MAX_SUPERSEDE_UNCERTAINTY_PCT
            )
        )

    abs_offset = abs(offset_pct)
    if abs_offset > MAX_OFFSET_FOR_SUPERSEDE_PCT:
        return False, (
            "|offset| {:.1f}% exceeds {:.1f}%; discrepancy requires engineering "
            "review before supersedure is accepted".format(
                abs_offset, MAX_OFFSET_FOR_SUPERSEDE_PCT
            )
        )

    return True, (
        "Supersedure accepted: quality_flag=valid, "
        "uncertainty={:.1f}% <= {:.1f}%, |offset|={:.1f}% <= {:.1f}%".format(
            experimental["uncertainty_pct"], MAX_SUPERSEDE_UNCERTAINTY_PCT,
            abs_offset, MAX_OFFSET_FOR_SUPERSEDE_PCT,
        )
    )


def compute_combined_assessment(
    experimental,
    reference,
    supersedes,
    model_uncertainty_pct=DEFAULT_MODEL_UNCERTAINTY_PCT,
):
    """
    Compute the combined background assessment value and its relative uncertainty.

    If the experimental data supersede the model, the combined result equals the
    experimental value and uncertainty directly.

    Otherwise, inverse-variance weighting on absolute uncertainties is applied
    (sigma_i = relative_uncertainty_i * value_i), and the combined relative
    uncertainty is propagated from the combined variance.

    Returns (combined_value: float, combined_uncertainty_pct: float).
    Raises AssessmentError on invalid inputs (non-positive reference value or
    zero absolute uncertainty outside the supersedure path).
    """
    exp_val = experimental["value"]
    ref_val = reference["value"]

    if ref_val <= 0:
        raise AssessmentError(
            "Reference value must be > 0, got {}".format(ref_val)
        )

    if supersedes:
        return float(exp_val), float(experimental["uncertainty_pct"])

    if exp_val <= 0:
        raise AssessmentError(
            "Experimental value must be > 0 for weighted average computation; "
            "use supersedes=True path for a zero experimental value"
        )

    exp_rel = experimental["uncertainty_pct"] / 100.0
    ref_rel = model_uncertainty_pct / 100.0

    exp_sigma = exp_rel * exp_val
    ref_sigma = ref_rel * ref_val

    if exp_sigma == 0 or ref_sigma == 0:
        raise AssessmentError(
            "Absolute uncertainty is zero; cannot compute inverse-variance weight"
        )

    w_exp = 1.0 / (exp_sigma ** 2)
    w_ref = 1.0 / (ref_sigma ** 2)
    w_total = w_exp + w_ref

    combined_value = (w_exp * exp_val + w_ref * ref_val) / w_total
    combined_sigma = (1.0 / w_total) ** 0.5

    if combined_value == 0:
        raise AssessmentError(
            "Combined value is zero; cannot compute relative uncertainty"
        )

    combined_uncertainty_pct = combined_sigma / combined_value * 100.0
    return combined_value, combined_uncertainty_pct


def check_provenance(record):
    """
    Verify that an experimental record carries sufficient provenance information.
    Checks: non-empty 'source', non-empty 'provenance', and positive 'duration_s'.
    Returns (complete: bool, missing_fields: list[str]).
    """
    missing = []

    source = record.get("source", "")
    if not isinstance(source, str) or not source.strip():
        missing.append("source")

    provenance = record.get("provenance", "")
    if not isinstance(provenance, str) or not provenance.strip():
        missing.append("provenance")

    duration_s = record.get("duration_s", 0)
    if not isinstance(duration_s, (int, float)) or duration_s <= 0:
        missing.append("duration_s")

    return len(missing) == 0, missing


def run_background_assessment(
    experimental_records,
    reference_records,
    model_uncertainty_pct=DEFAULT_MODEL_UNCERTAINTY_PCT,
):
    """
    Run a complete background radiation assessment for a list of experimental
    irradiation records matched against a list of reference model records.

    Records are matched on (particle_type, quantity). Experimental records
    with no matching reference are included in results with an issue flag.

    Returns a dict keyed by (particle_type, quantity) tuples.
    Raises AssessmentError if any record fails validation.
    """
    ref_index = {}
    for rec in reference_records:
        valid, issues = validate_reference_record(rec)
        if not valid:
            raise AssessmentError("Invalid reference record: {}".format(issues))
        key = (rec["particle_type"], rec["quantity"])
        ref_index[key] = rec

    results = {}

    for exp_rec in experimental_records:
        valid, issues = validate_experimental_record(exp_rec)
        if not valid:
            raise AssessmentError("Invalid experimental record: {}".format(issues))

        prov_ok, prov_missing = check_provenance(exp_rec)
        key = (exp_rec["particle_type"], exp_rec["quantity"])

        if key not in ref_index:
            results[key] = {
                "experimental_value": exp_rec["value"],
                "experimental_uncertainty_pct": exp_rec["uncertainty_pct"],
                "reference_value": None,
                "model_name": None,
                "offset_pct": None,
                "supersedes": False,
                "rationale": "No reference model available for this particle_type/quantity pair",
                "combined_value": exp_rec["value"],
                "combined_uncertainty_pct": exp_rec["uncertainty_pct"],
                "provenance_complete": prov_ok,
                "provenance_missing": prov_missing,
                "issues": ["No reference model record found"],
            }
            continue

        ref_rec = ref_index[key]
        offset = compute_offset_pct(exp_rec, ref_rec)
        supersedes, rationale = assess_supersedes_model(exp_rec, offset)
        combined_val, combined_unc = compute_combined_assessment(
            exp_rec, ref_rec, supersedes, model_uncertainty_pct
        )

        entry_issues = []
        if not prov_ok:
            entry_issues.append(
                "Incomplete provenance: missing {}".format(prov_missing)
            )
        if exp_rec["quality_flag"] == "invalid":
            entry_issues.append(
                "Experimental record is flagged 'invalid'; exclude from assessment"
            )

        results[key] = {
            "experimental_value": exp_rec["value"],
            "experimental_uncertainty_pct": exp_rec["uncertainty_pct"],
            "reference_value": ref_rec["value"],
            "model_name": ref_rec["model_name"],
            "offset_pct": offset,
            "supersedes": supersedes,
            "rationale": rationale,
            "combined_value": combined_val,
            "combined_uncertainty_pct": combined_unc,
            "provenance_complete": prov_ok,
            "provenance_missing": prov_missing,
            "issues": entry_issues,
        }

    return results

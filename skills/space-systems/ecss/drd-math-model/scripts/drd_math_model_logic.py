"""
ECSS-E-ST-32C Annex I — Mathematical Model Description Document (MMDD) logic.

Implements deterministic checks for model-type categorization,
MMDD field validation, eigenfrequency and MAC correlation, and
delivery-package completeness.  Stdlib only; no third-party dependencies.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_TYPES = {"FINITE_ELEMENT", "ANALYTICAL", "HYBRID"}
FIDELITY_LEVELS = {"LINEAR", "NONLINEAR"}

# Eigenfrequency correlation tolerance (±%)
FREQ_TOLERANCE_PCT = 5.0

# Modal Assurance Criterion minimum acceptance value
MAC_THRESHOLD = 0.90

# Required MMDD documentation fields (ECSS-E-ST-32C Annex I, clause 32-03)
REQUIRED_MMDD_FIELDS = [
    "model_id",
    "model_type",
    "fidelity",
    "coordinate_system_defined",
    "boundary_conditions_described",
    "loading_cases_listed",
    "element_types_listed",
    "material_properties_complete",
    "dof_count",
    "correlation_test_ref",
]

# Mandatory items in the MMDD delivery package
REQUIRED_DELIVERY_ITEMS = [
    "mmdd_document",
    "model_file",
    "correlation_report",
    "coordinate_system_definition",
    "version_identifier",
    "interface_description",
]


# ---------------------------------------------------------------------------
# Model type
# ---------------------------------------------------------------------------

def categorize_model_type(model_type: str) -> str:
    """Return the normalized model-type label.

    Raises ValueError for any label not in MODEL_TYPES.
    """
    normalized = model_type.strip().upper()
    if normalized not in MODEL_TYPES:
        raise ValueError(
            f"Unknown model type '{model_type}'. "
            f"Must be one of: {sorted(MODEL_TYPES)}."
        )
    return normalized


def validate_fidelity(fidelity: str) -> str:
    """Return the normalized fidelity label.

    Raises ValueError if the label is not LINEAR or NONLINEAR.
    """
    normalized = fidelity.strip().upper()
    if normalized not in FIDELITY_LEVELS:
        raise ValueError(
            f"Unknown fidelity level '{fidelity}'. "
            f"Must be one of: {sorted(FIDELITY_LEVELS)}."
        )
    return normalized


# ---------------------------------------------------------------------------
# MMDD field validation
# ---------------------------------------------------------------------------

def validate_mmdd_fields(fields: dict) -> list:
    """Check that all required MMDD fields are present and non-empty.

    Returns a list of missing or empty field names.
    """
    missing = []
    for field in REQUIRED_MMDD_FIELDS:
        value = fields.get(field)
        if value is None or value == "" or value is False:
            missing.append(field)
    return missing


# ---------------------------------------------------------------------------
# Eigenfrequency correlation
# ---------------------------------------------------------------------------

def check_frequency_correlation(measured_hz: float, predicted_hz: float) -> dict:
    """Check a single eigenfrequency correlation pair.

    Returns a result dict with error_pct and whether it is within tolerance.
    Raises ValueError if either frequency is non-positive.
    """
    if measured_hz <= 0.0:
        raise ValueError(
            f"Measured frequency must be positive, got {measured_hz}."
        )
    if predicted_hz <= 0.0:
        raise ValueError(
            f"Predicted frequency must be positive, got {predicted_hz}."
        )
    error_pct = abs(predicted_hz - measured_hz) / measured_hz * 100.0
    return {
        "measured_hz": measured_hz,
        "predicted_hz": predicted_hz,
        "error_pct": round(error_pct, 6),
        "within_tolerance": error_pct <= FREQ_TOLERANCE_PCT,
        "tolerance_pct": FREQ_TOLERANCE_PCT,
    }


# ---------------------------------------------------------------------------
# MAC correlation
# ---------------------------------------------------------------------------

def check_mac_value(mac: float) -> dict:
    """Check a single Modal Assurance Criterion value against the threshold.

    Returns a result dict indicating whether the threshold is met.
    Raises ValueError if mac is outside [0.0, 1.0].
    """
    if not (0.0 <= mac <= 1.0):
        raise ValueError(
            f"MAC value must be in [0.0, 1.0], got {mac}."
        )
    return {
        "mac": mac,
        "meets_threshold": mac >= MAC_THRESHOLD,
        "threshold": MAC_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Combined correlation assessment
# ---------------------------------------------------------------------------

def assess_correlation(freq_pairs: list, mac_values: list) -> dict:
    """Assess full model correlation from frequency pairs and MAC values.

    freq_pairs: list of (measured_hz, predicted_hz) tuples.
    mac_values: list of float MAC values, one per correlated mode.

    Returns aggregated pass/fail and per-mode details.
    """
    if not freq_pairs:
        raise ValueError("freq_pairs must not be empty.")
    if not mac_values:
        raise ValueError("mac_values must not be empty.")
    if len(freq_pairs) != len(mac_values):
        raise ValueError(
            f"freq_pairs length ({len(freq_pairs)}) must equal "
            f"mac_values length ({len(mac_values)})."
        )

    freq_results = [
        check_frequency_correlation(m, p) for m, p in freq_pairs
    ]
    mac_results = [check_mac_value(m) for m in mac_values]

    freq_pass = all(r["within_tolerance"] for r in freq_results)
    mac_pass = all(r["meets_threshold"] for r in mac_results)

    return {
        "frequency_results": freq_results,
        "mac_results": mac_results,
        "frequency_correlation_pass": freq_pass,
        "mac_correlation_pass": mac_pass,
        "correlated": freq_pass and mac_pass,
    }


# ---------------------------------------------------------------------------
# Delivery package completeness
# ---------------------------------------------------------------------------

def check_delivery_package(package: dict) -> list:
    """Check MMDD delivery package completeness.

    Returns a list of missing mandatory item names.
    """
    missing = []
    for item in REQUIRED_DELIVERY_ITEMS:
        if not package.get(item):
            missing.append(item)
    return missing


# ---------------------------------------------------------------------------
# Full MMDD compliance assessment
# ---------------------------------------------------------------------------

def assess_mmdd_compliance(
    fields: dict,
    freq_pairs: list,
    mac_values: list,
    delivery_package: dict,
) -> dict:
    """Perform a full MMDD compliance assessment.

    Combines field validation, correlation checks, and delivery-package
    completeness into a single result dict.  The model is compliant only
    when all three areas are free of findings.
    """
    missing_fields = validate_mmdd_fields(fields)
    correlation = assess_correlation(freq_pairs, mac_values)
    missing_delivery = check_delivery_package(delivery_package)

    compliant = (
        len(missing_fields) == 0
        and correlation["correlated"]
        and len(missing_delivery) == 0
    )

    return {
        "missing_mmdd_fields": missing_fields,
        "correlation": correlation,
        "missing_delivery_items": missing_delivery,
        "compliant": compliant,
    }

"""
ECSS-E-ST-32C Annex O / section 32-11 — Test-Analysis Correlation (TAC) DRD logic.
Paraphrased procedures; ECSS-E-ST-32C + Annex O cited as anchor only.
stdlib only — no external dependencies.
"""

VALID_QUANTITY_TYPES = frozenset({
    "frequency",
    "mode_shape",
    "static_deflection",
    "stress",
    "damping",
})

REQUIRED_DRD_SECTIONS = (
    "scope",
    "applicable_documents",
    "test_configuration",
    "analysis_model_description",
    "pre_test_predictions",
    "test_results",
    "correlation_assessment",
    "model_update_justification",
    "conclusions",
)

# Default acceptance thresholds (paraphrased from ECSS-E-ST-32C Annex O guidance).
# Programme-specific criteria take precedence over these defaults.
DEFAULT_FREQUENCY_THRESHOLD   = 0.05   # 5% relative delta
DEFAULT_DAMPING_THRESHOLD     = 0.20   # 20% relative delta
DEFAULT_DEFLECTION_THRESHOLD  = 0.10   # 10% relative delta
DEFAULT_STRESS_THRESHOLD      = 0.10   # 10% relative delta
DEFAULT_MAC_THRESHOLD         = 0.90   # MAC >= 0.90 for mode-shape correlation

_DEFAULT_THRESHOLDS = {
    "frequency":         DEFAULT_FREQUENCY_THRESHOLD,
    "damping":           DEFAULT_DAMPING_THRESHOLD,
    "static_deflection": DEFAULT_DEFLECTION_THRESHOLD,
    "stress":            DEFAULT_STRESS_THRESHOLD,
}


def categorize_quantity(quantity_type):
    """
    Return quantity_type if it is a recognized measurable quantity.
    Raises ValueError for any unrecognized type — an uncategorized quantity
    must not silently enter the correlation assessment.
    """
    if quantity_type not in VALID_QUANTITY_TYPES:
        raise ValueError(
            f"Unrecognized quantity type '{quantity_type}'. "
            f"Accepted types: {sorted(VALID_QUANTITY_TYPES)}"
        )
    return quantity_type


def compute_relative_delta(predicted, measured):
    """
    Compute the relative delta between a predicted value and a measured value:
        delta = |predicted - measured| / |measured|
    A zero measured value produces an undefined relative delta; raises ValueError.
    """
    if measured == 0.0:
        raise ValueError(
            "Measured value must be non-zero; a zero measurement produces an "
            "undefined relative delta."
        )
    return abs(predicted - measured) / abs(measured)


def check_frequency_correlation(predicted_freq, measured_freq, threshold=None):
    """
    Assess the correlation between a predicted and a measured natural frequency.

    Returns a result dict:
        predicted   : float
        measured    : float
        delta       : float  — relative delta (dimensionless)
        threshold   : float
        status      : "pass" | "fail"

    Raises ValueError if either frequency is non-positive or threshold is invalid.
    """
    if predicted_freq <= 0.0:
        raise ValueError(f"Predicted frequency must be positive; got {predicted_freq}")
    if measured_freq <= 0.0:
        raise ValueError(f"Measured frequency must be positive; got {measured_freq}")
    effective_threshold = threshold if threshold is not None else DEFAULT_FREQUENCY_THRESHOLD
    if effective_threshold <= 0.0:
        raise ValueError(f"Threshold must be positive; got {effective_threshold}")
    delta = compute_relative_delta(predicted_freq, measured_freq)
    return {
        "predicted": predicted_freq,
        "measured": measured_freq,
        "delta": round(delta, 6),
        "threshold": effective_threshold,
        "status": "pass" if delta <= effective_threshold else "fail",
    }


def check_mac_correlation(mac_value, threshold=None):
    """
    Assess whether a Modal Assurance Criterion (MAC) value satisfies the
    mode-shape correlation threshold. MAC ranges from 0 (no correlation) to
    1 (perfect correlation); a value at or above the threshold is a pass.

    Returns a result dict:
        mac_value   : float
        threshold   : float
        status      : "pass" | "fail"

    Raises ValueError if mac_value is outside [0, 1] or threshold is invalid.
    """
    if not (0.0 <= mac_value <= 1.0):
        raise ValueError(f"MAC value must be in [0, 1]; got {mac_value}")
    effective_threshold = threshold if threshold is not None else DEFAULT_MAC_THRESHOLD
    if not (0.0 < effective_threshold <= 1.0):
        raise ValueError(f"MAC threshold must be in (0, 1]; got {effective_threshold}")
    return {
        "mac_value": mac_value,
        "threshold": effective_threshold,
        "status": "pass" if mac_value >= effective_threshold else "fail",
    }


def assess_quantity_correlation(quantity_type, predicted, measured, threshold=None):
    """
    Assess the correlation for a single measured quantity.

    For 'mode_shape', `predicted` is the MAC value; `measured` is ignored.
    For all other quantity types, a relative-delta check is applied.

    Returns a result dict:
        quantity_type : str
        delta         : float or None  — relative delta (None for mode_shape)
        mac_value     : float or None  — MAC value (None for non-mode_shape)
        threshold     : float
        status        : "pass" | "fail"
    """
    categorize_quantity(quantity_type)

    if quantity_type == "mode_shape":
        mac_threshold = threshold if threshold is not None else DEFAULT_MAC_THRESHOLD
        result = check_mac_correlation(predicted, mac_threshold)
        return {
            "quantity_type": quantity_type,
            "delta": None,
            "mac_value": result["mac_value"],
            "threshold": result["threshold"],
            "status": result["status"],
        }

    effective_threshold = threshold if threshold is not None else _DEFAULT_THRESHOLDS[quantity_type]
    delta = compute_relative_delta(predicted, measured)
    return {
        "quantity_type": quantity_type,
        "delta": round(delta, 6),
        "mac_value": None,
        "threshold": effective_threshold,
        "status": "pass" if delta <= effective_threshold else "fail",
    }


def check_drd_completeness(sections_present):
    """
    Return the list of required DRD section names absent from sections_present.
    An empty return list means the document satisfies the Annex O content check.
    """
    present = set(sections_present)
    return [s for s in REQUIRED_DRD_SECTIONS if s not in present]


def build_correlation_summary(correlation_results):
    """
    Aggregate a list of assess_quantity_correlation outputs into a summary.

    Returns:
        summary  : dict {keyed label: status string}
        failing  : list of 0-based indices of failing entries
    """
    summary = {}
    failing = []
    for i, result in enumerate(correlation_results):
        key = f"{result['quantity_type']}_{i}"
        summary[key] = result["status"]
        if result["status"] == "fail":
            failing.append(i)
    return summary, failing


def determine_model_update_required(failing_correlations):
    """
    A model update is required when any correlation entry has failed.
    Returns True when failing_correlations is non-empty, False otherwise.
    """
    return len(failing_correlations) > 0

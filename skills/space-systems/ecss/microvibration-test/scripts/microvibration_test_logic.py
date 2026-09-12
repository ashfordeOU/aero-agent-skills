"""
Micro-vibration test assessment logic — ECSS-E-ST-32C clause 4.6.3.12.

Implements disturbance source categorization, frequency coverage checks,
amplitude margin computation, and per-source and overall pass/fail evaluation.
Stdlib only; deterministic; offline.
"""

VALID_SOURCE_TYPES = {"tonal", "broadband", "transient"}
VALID_MEASUREMENT_TYPES = {"force-platform", "accelerometer", "load-cell"}


def categorize_source(source_type: str) -> str:
    """
    Return the normalized disturbance category for a source type string.

    Valid inputs: 'tonal', 'broadband', 'transient' (case-insensitive).
    Raises ValueError for any unrecognized type.
    """
    normalized = source_type.strip().lower()
    if normalized not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Unrecognized disturbance source type: {source_type!r}. "
            f"Expected one of {sorted(VALID_SOURCE_TYPES)}."
        )
    return normalized


def check_frequency_coverage(
    measured_low_hz: float,
    measured_high_hz: float,
    required_low_hz: float,
    required_high_hz: float,
) -> dict:
    """
    Verify that the measured frequency range fully spans the required range.

    Returns a dict:
      covered (bool): True when measured range fully covers required range.
      gaps (list[str]): Human-readable descriptions of any uncovered bounds.

    Raises ValueError when either range is degenerate (low >= high).
    """
    if measured_low_hz >= measured_high_hz:
        raise ValueError(
            f"measured_low_hz ({measured_low_hz}) must be less than "
            f"measured_high_hz ({measured_high_hz})."
        )
    if required_low_hz >= required_high_hz:
        raise ValueError(
            f"required_low_hz ({required_low_hz}) must be less than "
            f"required_high_hz ({required_high_hz})."
        )

    gaps = []
    if measured_low_hz > required_low_hz:
        gaps.append(
            f"lower bound not covered: measurement starts at {measured_low_hz} Hz "
            f"but required from {required_low_hz} Hz."
        )
    if measured_high_hz < required_high_hz:
        gaps.append(
            f"upper bound not covered: measurement ends at {measured_high_hz} Hz "
            f"but required to {required_high_hz} Hz."
        )

    return {"covered": len(gaps) == 0, "gaps": gaps}


def compute_disturbance_margin(
    measured_amplitude: float, budget_amplitude: float
) -> float:
    """
    Compute margin as budget minus measured amplitude.

    Positive or zero margin → compliant.
    Negative margin → exceedance.

    Both arguments must be non-negative (physical amplitudes).
    Raises ValueError otherwise.
    """
    if measured_amplitude < 0:
        raise ValueError(
            f"measured_amplitude must be non-negative; got {measured_amplitude}."
        )
    if budget_amplitude < 0:
        raise ValueError(
            f"budget_amplitude must be non-negative; got {budget_amplitude}."
        )
    return budget_amplitude - measured_amplitude


def evaluate_source(
    source: dict,
    budget: dict,
    freq_range_required: tuple,
) -> dict:
    """
    Evaluate a single disturbance source against its budget and frequency coverage.

    source dict keys:
      name            (str)   — identifier
      type            (str)   — 'tonal' | 'broadband' | 'transient'
      amplitude       (float) — measured force/torque amplitude (N or Nm)
      freq_low_hz     (float) — lower bound of measured frequency range
      freq_high_hz    (float) — upper bound of measured frequency range
      measurement_type (str)  — 'force-platform' | 'accelerometer' | 'load-cell'

    budget dict keys:
      amplitude (float) — allowable amplitude for this source

    freq_range_required: (low_hz, high_hz) tuple specifying the mandatory coverage.

    Returns a result dict:
      name, type, measurement_type, margin, frequency_covered, passed, findings.

    Raises ValueError for unrecognized source type, measurement type, or missing budget.
    """
    name = source.get("name", "unnamed")

    source_type = categorize_source(source["type"])

    meas_type = source.get("measurement_type", "").strip().lower()
    if meas_type not in VALID_MEASUREMENT_TYPES:
        raise ValueError(
            f"Unrecognized measurement type: {meas_type!r} for source {name!r}. "
            f"Expected one of {sorted(VALID_MEASUREMENT_TYPES)}."
        )

    if "amplitude" not in budget:
        raise ValueError(
            f"No amplitude budget provided for source {name!r}. "
            "Budget dict must contain an 'amplitude' key."
        )

    margin = compute_disturbance_margin(source["amplitude"], budget["amplitude"])

    req_low, req_high = freq_range_required
    freq_result = check_frequency_coverage(
        source["freq_low_hz"], source["freq_high_hz"], req_low, req_high
    )

    passed = margin >= 0 and freq_result["covered"]

    findings = []
    if margin < 0:
        findings.append(
            f"Amplitude exceeds budget by {abs(margin):.4g} "
            f"(measured={source['amplitude']:.4g}, budget={budget['amplitude']:.4g})."
        )
    findings.extend(freq_result["gaps"])

    return {
        "name": name,
        "type": source_type,
        "measurement_type": meas_type,
        "margin": margin,
        "frequency_covered": freq_result["covered"],
        "passed": passed,
        "findings": findings,
    }


def run_microvibration_test_assessment(
    sources: list,
    budgets: dict,
    freq_range_required: tuple,
) -> dict:
    """
    Run a full micro-vibration test assessment across all disturbance sources.

    sources: list of source dicts (see evaluate_source).
    budgets: mapping of source name → budget dict (must contain 'amplitude').
    freq_range_required: (low_hz, high_hz) mandatory measurement coverage tuple.

    Returns:
      overall_passed   (bool)       — True only when every source passes.
      source_count     (int)        — total number of sources evaluated.
      failing_sources  (list[str])  — names of sources that did not pass.
      results          (list[dict]) — per-source evaluation dicts.

    Raises ValueError when sources is empty or a source has no matching budget entry.
    """
    if not sources:
        raise ValueError(
            "At least one disturbance source must be provided for assessment."
        )

    results = []
    for source in sources:
        name = source.get("name", "unnamed")
        budget = budgets.get(name)
        if budget is None:
            raise ValueError(
                f"No budget entry found for source {name!r}. "
                "Each source name must have a corresponding entry in the budgets dict."
            )
        result = evaluate_source(source, budget, freq_range_required)
        results.append(result)

    overall_passed = all(r["passed"] for r in results)
    failing_sources = [r["name"] for r in results if not r["passed"]]

    return {
        "overall_passed": overall_passed,
        "source_count": len(results),
        "failing_sources": failing_sources,
        "results": results,
    }

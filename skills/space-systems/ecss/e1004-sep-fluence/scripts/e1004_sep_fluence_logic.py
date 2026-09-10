#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.2.2 + Annex B.6 -- solar proton fluence
via the ESP (Emission of Solar Protons) model (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): solar
particle events are stochastic, so the ESP model reports the cumulative
proton fluence (integral flux above a stated energy threshold,
accumulated over a stated mission duration) that is exceeded with a
stated probability (1 - confidence_level). Fluence must not decrease
when duration increases at fixed confidence level, and must not
decrease when confidence level increases at fixed duration. Fluence
reported above a higher energy threshold must not exceed fluence
reported above a lower one, because the higher-threshold population is
a subset of the lower-threshold one.

This module scopes only the workflow around the ESP model: input
validation, per-threshold invocation, and cross-checking the resulting
spectrum for the invariants above. The ESP model's own numeric
coefficients are out of scope here and are supplied by the caller as a
pluggable model_fn(energy_threshold_mev, confidence_level_pct,
duration_years) -> fluence_cm2, consistent with the dedicated Annex B.6
implementation (sibling leaf e1004-b6-esp). Worst-case single-event peak
flux is out of scope (sibling leaf e1004-sep-peakflux).
"""

HIGH_CONFIDENCE_CAVEAT_THRESHOLD_PCT = 99.0


def validate_confidence_level(confidence_level_pct):
    """Raise ValueError unless 0 < confidence_level_pct < 100. A
    confidence level of 0 or 100 is degenerate for a stochastic model
    (no exceedance protection, or an undefined/infinite fluence)."""
    if not (0 < confidence_level_pct < 100):
        raise ValueError(
            "confidence_level_pct must be in (0, 100): %r" % (confidence_level_pct,)
        )


def validate_mission_duration(duration_years):
    """Raise ValueError unless duration_years > 0."""
    if duration_years <= 0:
        raise ValueError("duration_years must be > 0: %r" % (duration_years,))


def confidence_level_caveat(confidence_level_pct):
    """Return a caveat string if confidence_level_pct is at or above
    HIGH_CONFIDENCE_CAVEAT_THRESHOLD_PCT (extrapolates well beyond the
    ESP model's historical solar-cycle database), else None."""
    validate_confidence_level(confidence_level_pct)
    if confidence_level_pct >= HIGH_CONFIDENCE_CAVEAT_THRESHOLD_PCT:
        return (
            "confidence_level_pct %.2f extrapolates beyond the ESP model's "
            "limited historical solar-cycle database; treat the fluence as "
            "carrying materially larger statistical uncertainty than a "
            "mid-range confidence level." % confidence_level_pct
        )
    return None


def compute_threshold_fluence(
    energy_threshold_mev, confidence_level_pct, duration_years, model_fn
):
    """Compute the ESP fluence for one energy threshold. Validates
    inputs, calls model_fn(energy_threshold_mev, confidence_level_pct,
    duration_years), and checks the returned fluence is a finite,
    non-negative number. Returns a new dict; raises ValueError on
    invalid input or an invalid model_fn result."""
    if energy_threshold_mev <= 0:
        raise ValueError(
            "energy_threshold_mev must be > 0: %r" % (energy_threshold_mev,)
        )
    validate_confidence_level(confidence_level_pct)
    validate_mission_duration(duration_years)

    fluence_cm2 = model_fn(energy_threshold_mev, confidence_level_pct, duration_years)
    if not isinstance(fluence_cm2, (int, float)) or fluence_cm2 != fluence_cm2:
        raise ValueError("model_fn must return a finite number: %r" % (fluence_cm2,))
    if fluence_cm2 < 0:
        raise ValueError("model_fn returned a negative fluence: %r" % (fluence_cm2,))

    return {
        "energy_threshold_mev": energy_threshold_mev,
        "confidence_level_pct": confidence_level_pct,
        "duration_years": duration_years,
        "fluence_cm2": fluence_cm2,
    }


def compute_fluence_spectrum(
    energy_thresholds_mev, confidence_level_pct, duration_years, model_fn
):
    """Compute the fluence spectrum across energy_thresholds_mev (a
    non-empty iterable) for one duration/confidence policy. Returns a
    new dict with entries sorted ascending by energy threshold and a
    threshold_order_violations list: pairs of (lower, higher) threshold
    entries where the higher-threshold fluence exceeds the
    lower-threshold fluence (should be empty for a consistent
    spectrum). Raises ValueError if energy_thresholds_mev is empty."""
    thresholds = sorted(set(energy_thresholds_mev))
    if not thresholds:
        raise ValueError("energy_thresholds_mev must be non-empty")

    entries = [
        compute_threshold_fluence(t, confidence_level_pct, duration_years, model_fn)
        for t in thresholds
    ]

    violations = []
    for lower, higher in zip(entries, entries[1:]):
        if higher["fluence_cm2"] > lower["fluence_cm2"]:
            violations.append((lower, higher))

    return {
        "confidence_level_pct": confidence_level_pct,
        "duration_years": duration_years,
        "entries": entries,
        "threshold_order_violations": violations,
    }


def check_confidence_monotonicity(
    energy_threshold_mev, duration_years, confidence_levels_pct, model_fn
):
    """For one energy threshold and duration, compute fluence across
    confidence_levels_pct (a non-empty iterable) and check fluence does
    not decrease as confidence level increases. Returns a new dict with
    the sorted (confidence_level_pct, fluence_cm2) pairs and a
    monotonic bool. Raises ValueError if confidence_levels_pct is
    empty."""
    levels = sorted(set(confidence_levels_pct))
    if not levels:
        raise ValueError("confidence_levels_pct must be non-empty")

    pairs = [
        (
            level,
            compute_threshold_fluence(
                energy_threshold_mev, level, duration_years, model_fn
            )["fluence_cm2"],
        )
        for level in levels
    ]

    monotonic = all(
        pairs[i][1] <= pairs[i + 1][1] for i in range(len(pairs) - 1)
    )

    return {
        "energy_threshold_mev": energy_threshold_mev,
        "duration_years": duration_years,
        "pairs": pairs,
        "monotonic": monotonic,
    }


def check_duration_monotonicity(
    energy_threshold_mev, confidence_level_pct, durations_years, model_fn
):
    """For one energy threshold and confidence level, compute fluence
    across durations_years (a non-empty iterable) and check fluence
    does not decrease as duration increases. Returns a new dict with
    the sorted (duration_years, fluence_cm2) pairs and a monotonic
    bool. Raises ValueError if durations_years is empty."""
    durations = sorted(set(durations_years))
    if not durations:
        raise ValueError("durations_years must be non-empty")

    pairs = [
        (
            duration,
            compute_threshold_fluence(
                energy_threshold_mev, confidence_level_pct, duration, model_fn
            )["fluence_cm2"],
        )
        for duration in durations
    ]

    monotonic = all(
        pairs[i][1] <= pairs[i + 1][1] for i in range(len(pairs) - 1)
    )

    return {
        "energy_threshold_mev": energy_threshold_mev,
        "confidence_level_pct": confidence_level_pct,
        "pairs": pairs,
        "monotonic": monotonic,
    }


def sep_fluence_specification(
    energy_thresholds_mev, confidence_level_pct, duration_years, model_fn
):
    """Assemble the fluence entry for the mission's radiation
    environment specification: the fluence spectrum plus a verified
    bool that is True only when threshold_order_violations is empty.
    Also carries the confidence_level_caveat (None if not applicable).
    Returns a new dict."""
    spectrum = compute_fluence_spectrum(
        energy_thresholds_mev, confidence_level_pct, duration_years, model_fn
    )
    verified = not spectrum["threshold_order_violations"]
    updated = dict(spectrum)
    updated["verified"] = verified
    updated["caveat"] = confidence_level_caveat(confidence_level_pct)
    return updated

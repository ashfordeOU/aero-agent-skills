#!/usr/bin/env python3
"""Zero-current reporting of a power-supply current telemetry channel.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.6.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause recommends that a current telemetry channel stay able to
report a current all the way down to zero while remaining inside the
accuracy it was specified to. Whether it can is not a matter of
opinion: the error of such a channel carries terms that scale with the
reading and terms that do not, and only the fixed terms survive at zero
load.

Error model (worst-case linear sum, declared as such)
    gain term          gain_error_percent of the reading
    offset term        a fixed current, independent of the reading
    quantisation term  half a step of the acquisition resolution
    noise term         a fixed readout noise contribution

Budget model
    reading term       accuracy_percent_of_reading of the reading
    full-scale term    accuracy_percent_of_full_scale of full scale

Both are affine in the reported current, so the lowest current the
channel reports inside budget follows in closed form. At zero the
reading terms vanish from both sides and the comparison reduces to the
fixed error against the full-scale part of the budget.

A declared blanking deadband -- a threshold under which the channel
forces a zero reading -- is not a zero reading at all: currents inside
it are unreportable, so it raises the floor and is recorded.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FIXED_TERMS = ("telemetry-offset", "acquisition-quantisation", "readout-noise")

ZERO_REPORTABLE = "zero-current-reportable"
FLOOR_LIMITED = "floor-limited-readout"
BUDGET_NOT_MET = "accuracy-budget-not-met"

RECOMMENDATION_MET = "recommendation-met"
RECOMMENDATION_NOT_MET = "recommendation-not-met-deviation-required"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15

REQUIRED_KEYS = (
    "full_scale_a",
    "accuracy_percent_of_reading",
    "accuracy_percent_of_full_scale",
    "gain_error_percent",
    "offset_error_a",
    "adc_bits",
    "noise_a",
)


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A channel sized so that its fixed error exactly consumes the
    full-scale part of the budget can land a few units in the last place
    either side of the bound. The budget is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def quantisation_step_a(full_scale_a, adc_bits):
    """Current represented by one step of the acquisition resolution."""
    full_scale = _require_positive("full_scale_a", full_scale_a)
    if isinstance(adc_bits, bool) or not isinstance(adc_bits, int):
        raise ValueError("adc_bits must be an integer, got %r" % (adc_bits,))
    if adc_bits < 1:
        raise ValueError("adc_bits must be at least 1, got %r" % (adc_bits,))
    if adc_bits > 32:
        raise ValueError("adc_bits above 32 is not a telemetry channel, got %r" % (adc_bits,))
    return full_scale / float(1 << adc_bits)


def validate_channel(channel):
    """Check a channel description carries every term the model needs."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    missing = [k for k in REQUIRED_KEYS if channel.get(k) is None]
    if missing:
        raise ValueError("channel is missing entries: %s" % ", ".join(sorted(missing)))
    _require_positive("full_scale_a", channel["full_scale_a"])
    _require_non_negative("accuracy_percent_of_reading", channel["accuracy_percent_of_reading"])
    _require_non_negative(
        "accuracy_percent_of_full_scale", channel["accuracy_percent_of_full_scale"]
    )
    _require_non_negative("gain_error_percent", channel["gain_error_percent"])
    _require_non_negative("offset_error_a", channel["offset_error_a"])
    _require_non_negative("noise_a", channel["noise_a"])
    quantisation_step_a(channel["full_scale_a"], channel["adc_bits"])
    blanking = _require_non_negative(
        "blanking_threshold_a", channel.get("blanking_threshold_a", 0.0)
    )
    if blanking > float(channel["full_scale_a"]):
        raise ValueError("blanking_threshold_a exceeds full_scale_a; the channel reports nothing")
    if float(channel["accuracy_percent_of_reading"]) == 0.0 and float(
        channel["accuracy_percent_of_full_scale"]
    ) == 0.0:
        raise ValueError("the accuracy budget is zero on both terms; nothing can meet it")
    return channel


def fixed_error_terms_a(channel):
    """The three error terms that do not vanish as the load falls."""
    validate_channel(channel)
    return {
        "telemetry-offset": float(channel["offset_error_a"]),
        "acquisition-quantisation": 0.5
        * quantisation_step_a(channel["full_scale_a"], channel["adc_bits"]),
        "readout-noise": float(channel["noise_a"]),
    }


def error_at_current_a(channel, current_a):
    """Worst-case reported-current error at one load point."""
    validate_channel(channel)
    current = _require_non_negative("current_a", current_a)
    if current > float(channel["full_scale_a"]):
        raise ValueError(
            "current_a %g A is above the channel full scale %g A"
            % (current, channel["full_scale_a"])
        )
    fixed = sum(fixed_error_terms_a(channel).values())
    return fixed + (float(channel["gain_error_percent"]) / 100.0) * current


def budget_at_current_a(channel, current_a):
    """Error the accuracy specification allows at one load point."""
    validate_channel(channel)
    current = _require_non_negative("current_a", current_a)
    if current > float(channel["full_scale_a"]):
        raise ValueError(
            "current_a %g A is above the channel full scale %g A"
            % (current, channel["full_scale_a"])
        )
    reading_term = (float(channel["accuracy_percent_of_reading"]) / 100.0) * current
    full_scale_term = (
        float(channel["accuracy_percent_of_full_scale"]) / 100.0
    ) * float(channel["full_scale_a"])
    return reading_term + full_scale_term


def zero_margin_a(channel):
    """Budget left over at zero load: positive means zero is reportable."""
    return budget_at_current_a(channel, 0.0) - error_at_current_a(channel, 0.0)


def accuracy_floor_a(channel):
    """Lowest current the channel reports inside budget, ignoring blanking.

    Error and budget are both affine in the reported current, so the
    crossing is closed form. None means no point in the range meets the
    budget at all.
    """
    validate_channel(channel)
    full_scale = float(channel["full_scale_a"])
    fixed = sum(fixed_error_terms_a(channel).values())
    allowed_fixed = (
        float(channel["accuracy_percent_of_full_scale"]) / 100.0
    ) * full_scale
    slope_error = float(channel["gain_error_percent"]) / 100.0
    slope_budget = float(channel["accuracy_percent_of_reading"]) / 100.0
    if _at_most(fixed, allowed_fixed):
        return 0.0
    if _at_most(slope_budget, slope_error):
        return None
    crossing = (fixed - allowed_fixed) / (slope_budget - slope_error)
    if crossing > full_scale and not math.isclose(
        crossing, full_scale, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return None
    return min(crossing, full_scale)


def budget_upper_limit_a(channel):
    """Highest current still inside budget when the gain term outruns it.

    None means the budget holds to full scale. A limit below full scale
    is a separate defect from the zero-end one and is reported as such.
    """
    validate_channel(channel)
    full_scale = float(channel["full_scale_a"])
    fixed = sum(fixed_error_terms_a(channel).values())
    allowed_fixed = (
        float(channel["accuracy_percent_of_full_scale"]) / 100.0
    ) * full_scale
    slope_error = float(channel["gain_error_percent"]) / 100.0
    slope_budget = float(channel["accuracy_percent_of_reading"]) / 100.0
    if _at_most(slope_error, slope_budget):
        return None
    if not _at_most(fixed, allowed_fixed):
        return None
    crossing = (allowed_fixed - fixed) / (slope_error - slope_budget)
    if crossing >= full_scale or math.isclose(
        crossing, full_scale, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return None
    return crossing


def dominant_fixed_term(channel):
    """Fixed term that contributes most of the error at zero load."""
    terms = fixed_error_terms_a(channel)
    return max(FIXED_TERMS, key=lambda name: terms[name])


def assess_zero_current_readout(channel):
    """Full clause 5.2.8.6.1 assessment of a current telemetry channel."""
    validate_channel(channel)
    full_scale = float(channel["full_scale_a"])
    blanking = float(channel.get("blanking_threshold_a", 0.0))
    error_zero = error_at_current_a(channel, 0.0)
    budget_zero = budget_at_current_a(channel, 0.0)
    margin = budget_zero - error_zero
    floor = accuracy_floor_a(channel)
    upper = budget_upper_limit_a(channel)
    findings = []
    if floor is None:
        reportable_floor = None
        verdict = BUDGET_NOT_MET
        findings.append(
            "no load point in the channel range meets the accuracy budget; the "
            "fixed error %.6g A is never absorbed" % error_zero
        )
    else:
        reportable_floor = max(floor, blanking)
        if _at_most(reportable_floor, 0.0):
            verdict = ZERO_REPORTABLE
        else:
            verdict = FLOOR_LIMITED
    if blanking > 0.0:
        findings.append(
            "a blanking deadband of %.6g A forces a zero reading below it; currents "
            "inside the deadband are unreportable rather than measured zero" % blanking
        )
    if floor is not None and floor > 0.0:
        findings.append(
            "the accuracy budget is first met at %.6g A (%.3f%% of full scale); %s "
            "dominates the fixed error"
            % (floor, 100.0 * floor / full_scale, dominant_fixed_term(channel))
        )
    if upper is not None:
        findings.append(
            "the gain term outruns the reading part of the budget above %.6g A; the "
            "upper end of the range is a separate shortfall" % upper
        )
    shortfall = 0.0 if _at_most(error_zero, budget_zero) else error_zero - budget_zero
    return {
        "verdict": verdict,
        "recommendation_status": (
            RECOMMENDATION_MET if verdict == ZERO_REPORTABLE else RECOMMENDATION_NOT_MET
        ),
        "error_at_zero_a": error_zero,
        "budget_at_zero_a": budget_zero,
        "zero_margin_a": margin,
        "zero_shortfall_a": shortfall,
        "accuracy_floor_a": floor,
        "lowest_reportable_current_a": reportable_floor,
        "budget_upper_limit_a": upper,
        "fixed_error_terms_a": fixed_error_terms_a(channel),
        "dominant_fixed_term": dominant_fixed_term(channel),
        "findings": findings,
    }


def retirement_options_a(channel):
    """Reduction in each fixed term that alone would reach zero reporting."""
    result = assess_zero_current_readout(channel)
    shortfall = result["zero_shortfall_a"]
    terms = result["fixed_error_terms_a"]
    options = {}
    for name in FIXED_TERMS:
        if shortfall <= 0.0:
            options[name] = 0.0
        elif _at_most(shortfall, terms[name]):
            options[name] = shortfall
        else:
            options[name] = None
    return options

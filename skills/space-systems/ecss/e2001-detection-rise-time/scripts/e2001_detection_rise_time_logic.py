#!/usr/bin/env python3
"""Global detection rise time against the applied pulse (ECSS-E-ST-20-01C 7.3.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A pulsed multipactor run gives a global detection chain only the duration
of one pulse in which to rise, settle and register a discharge. Speed is
therefore expressed as a ratio between the chain rise time and the applied
pulse width, and four independent criteria decide whether the chain is
fast enough:

* the chain rise time against the required fraction of the pulse width;
* the observation window left in the pulse once turn-on blanking and the
  rise itself are subtracted;
* the digitiser sample rate against the samples wanted across the edge;
* the baseline recovery time against the inter-pulse gap.

Stage rise times combine root-sum-square. A stage quoted by bandwidth is
converted through the rise-time-bandwidth product, about 0.35 for the
single-pole and Gaussian responses of detector diodes, video amplifiers
and digitiser front ends.
"""

import math

# Rise-time x bandwidth for a single-pole / Gaussian response (10-90 %).
RISE_TIME_BANDWIDTH_PRODUCT = 0.35
# Default commitment: the chain answers an order faster than the pulse.
DEFAULT_SPEED_RATIO = 0.1
# Beyond this ratio the chain is not usable on the pulse at all.
MARGINAL_SPEED_RATIO = 0.25
# Samples wanted across the leading edge to place the onset.
DEFAULT_SAMPLES_PER_EDGE = 5.0
# Recovery to baseline scales with the chain rise time.
DEFAULT_RECOVERY_FACTOR = 3.0
# Fraction of the pulse that must survive blanking and the edge.
DEFAULT_MIN_WINDOW_FRACTION = 0.5
# Comparisons absorb representation error only; limits are never widened.
REL_TOL = 1e-12
ABS_TOL = 1e-18

_REQUIRED_KEYS = ("pulse_width_s",)
_ONE_OF_KEYS = ("stage_rise_times_s", "stage_bandwidths_hz")
_OPTIONAL_KEYS = (
    "speed_ratio",
    "blanking_s",
    "duty_cycle",
    "sample_rate_hz",
    "samples_per_edge",
    "recovery_factor",
    "min_window_fraction",
)


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, out))
    return out


def _non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, out))
    return out


def _fraction(name, value):
    out = _as_float(name, value)
    if not 0.0 < out <= 1.0:
        raise ValueError("%s must lie in (0, 1], got %g" % (name, out))
    return out


def within_limit(value, limit):
    """True when ``value`` is at or under ``limit``.

    The tolerance absorbs representation error carried by a root-sum-square
    or a product of floats; the engineering limit itself is untouched.
    """
    value = _as_float("value", value)
    limit = _as_float("limit", limit)
    return value < limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def rise_time_from_bandwidth(bandwidth_hz, coefficient=RISE_TIME_BANDWIDTH_PRODUCT):
    """Stage 10-90 % rise time implied by its bandwidth."""
    bandwidth = _positive("bandwidth_hz", bandwidth_hz)
    factor = _positive("coefficient", coefficient)
    return factor / bandwidth


def bandwidth_from_rise_time(rise_time_s, coefficient=RISE_TIME_BANDWIDTH_PRODUCT):
    """Bandwidth a stage needs to reach a wanted rise time."""
    rise = _positive("rise_time_s", rise_time_s)
    factor = _positive("coefficient", coefficient)
    return factor / rise


def chain_rise_time_s(stage_rise_times_s):
    """Root-sum-square combination of cascaded stage rise times."""
    if not isinstance(stage_rise_times_s, (list, tuple)):
        raise ValueError("stage_rise_times_s must be a list or tuple of stage times")
    if len(stage_rise_times_s) == 0:
        raise ValueError("stage_rise_times_s must hold at least one stage")
    total = 0.0
    for index, value in enumerate(stage_rise_times_s):
        stage = _non_negative("stage_rise_times_s[%d]" % index, value)
        total += stage * stage
    if total <= 0.0:
        raise ValueError("at least one stage rise time must be > 0")
    return math.sqrt(total)


def dominant_stage_index(stage_rise_times_s):
    """Index of the stage that sets the chain; ties resolve to the first."""
    chain_rise_time_s(stage_rise_times_s)  # validation only
    best_index, best_value = 0, -1.0
    for index, value in enumerate(stage_rise_times_s):
        stage = float(value)
        if stage > best_value:
            best_index, best_value = index, stage
    return best_index


def required_rise_time_s(pulse_width_s, speed_ratio=DEFAULT_SPEED_RATIO):
    """Longest chain rise time the speed commitment allows for this pulse."""
    pulse = _positive("pulse_width_s", pulse_width_s)
    ratio = _fraction("speed_ratio", speed_ratio)
    return ratio * pulse


def shortest_supported_pulse_width_s(chain_rise_s, speed_ratio=DEFAULT_SPEED_RATIO):
    """Shortest pulse this chain can still answer inside."""
    rise = _positive("chain_rise_s", chain_rise_s)
    ratio = _fraction("speed_ratio", speed_ratio)
    return rise / ratio


def meets_speed_requirement(
    chain_rise_s, pulse_width_s, speed_ratio=DEFAULT_SPEED_RATIO
):
    """True when the chain answers within the committed fraction of the pulse."""
    rise = _positive("chain_rise_s", chain_rise_s)
    return within_limit(rise, required_rise_time_s(pulse_width_s, speed_ratio))


def categorize_detection_speed(chain_rise_s, pulse_width_s):
    """Name the speed regime of a chain on a given pulse width."""
    rise = _positive("chain_rise_s", chain_rise_s)
    pulse = _positive("pulse_width_s", pulse_width_s)
    ratio = rise / pulse
    if within_limit(ratio, DEFAULT_SPEED_RATIO):
        return "prompt"
    if within_limit(ratio, MARGINAL_SPEED_RATIO):
        return "marginal"
    return "too-slow"


def observation_window_s(pulse_width_s, chain_rise_s, blanking_s=0.0):
    """Time left inside the pulse for a decision, never negative."""
    pulse = _positive("pulse_width_s", pulse_width_s)
    rise = _positive("chain_rise_s", chain_rise_s)
    blanking = _non_negative("blanking_s", blanking_s)
    if blanking > pulse:
        raise ValueError(
            "blanking_s (%g s) exceeds the pulse width (%g s): the drive "
            "transient cannot outlast its own pulse" % (blanking, pulse)
        )
    window = pulse - blanking - rise
    return window if window > 0.0 else 0.0


def window_fraction(pulse_width_s, chain_rise_s, blanking_s=0.0):
    """Observation window as a fraction of the pulse width."""
    pulse = _positive("pulse_width_s", pulse_width_s)
    return observation_window_s(pulse, chain_rise_s, blanking_s) / pulse


def minimum_sample_rate_hz(chain_rise_s, samples_per_edge=DEFAULT_SAMPLES_PER_EDGE):
    """Digitiser rate needed to place the onset on the leading edge."""
    rise = _positive("chain_rise_s", chain_rise_s)
    samples = _positive("samples_per_edge", samples_per_edge)
    if samples < 2.0:
        raise ValueError(
            "samples_per_edge must be >= 2 to place an edge, got %g" % samples
        )
    return samples / rise


def inter_pulse_gap_s(pulse_width_s, duty_cycle):
    """Off time between pulses implied by the pulse width and duty cycle."""
    pulse = _positive("pulse_width_s", pulse_width_s)
    duty = _fraction("duty_cycle", duty_cycle)
    return pulse / duty - pulse


def baseline_recovery_s(chain_rise_s, recovery_factor=DEFAULT_RECOVERY_FACTOR):
    """Time the detector needs to settle back to baseline after a pulse."""
    rise = _positive("chain_rise_s", chain_rise_s)
    factor = _positive("recovery_factor", recovery_factor)
    return factor * rise


def evaluate_detection_chain(spec):
    """Full clause 7.3.3 speed assessment of one detection chain.

    Accepts stages as rise times or as bandwidths (exactly one of the two)
    plus the pulse pattern, and returns the chain figures, the speed
    category, the findings and the verdict.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of chain and pulse inputs")
    known = set(_REQUIRED_KEYS) | set(_ONE_OF_KEYS) | set(_OPTIONAL_KEYS)
    unknown = set(spec) - known
    if unknown:
        raise ValueError("unknown spec keys: %s" % ", ".join(sorted(unknown)))
    missing = [key for key in _REQUIRED_KEYS if key not in spec]
    if missing:
        raise ValueError("spec missing required keys: %s" % ", ".join(missing))
    given = [key for key in _ONE_OF_KEYS if key in spec]
    if len(given) != 1:
        raise ValueError(
            "spec must carry exactly one of %s, got %d"
            % (" or ".join(_ONE_OF_KEYS), len(given))
        )

    if given[0] == "stage_bandwidths_hz":
        bandwidths = spec["stage_bandwidths_hz"]
        if not isinstance(bandwidths, (list, tuple)) or len(bandwidths) == 0:
            raise ValueError("stage_bandwidths_hz must be a non-empty list")
        stages = [
            rise_time_from_bandwidth(_positive("stage_bandwidths_hz[%d]" % i, b))
            for i, b in enumerate(bandwidths)
        ]
    else:
        stages = list(spec["stage_rise_times_s"])

    pulse = _positive("pulse_width_s", spec["pulse_width_s"])
    ratio = _fraction("speed_ratio", spec.get("speed_ratio", DEFAULT_SPEED_RATIO))
    blanking = _non_negative("blanking_s", spec.get("blanking_s", 0.0))
    min_fraction = _fraction(
        "min_window_fraction", spec.get("min_window_fraction", DEFAULT_MIN_WINDOW_FRACTION)
    )
    samples = _positive(
        "samples_per_edge", spec.get("samples_per_edge", DEFAULT_SAMPLES_PER_EDGE)
    )
    recovery_factor = _positive(
        "recovery_factor", spec.get("recovery_factor", DEFAULT_RECOVERY_FACTOR)
    )

    chain = chain_rise_time_s(stages)
    required = required_rise_time_s(pulse, ratio)
    findings = []
    if not within_limit(chain, required):
        findings.append(
            {
                "code": "chain-too-slow-for-pulse",
                "chain_rise_time_s": chain,
                "required_rise_time_s": required,
                "detail": "chain rise time %.3e s exceeds the %.3e s allowed by the "
                "speed ratio" % (chain, required),
            }
        )
    window = observation_window_s(pulse, chain, blanking)
    fraction = window / pulse
    if not (fraction > min_fraction or math.isclose(
        fraction, min_fraction, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )):
        findings.append(
            {
                "code": "observation-window-too-short",
                "observation_window_s": window,
                "window_fraction": fraction,
                "detail": "only %.1f %% of the pulse survives blanking and the edge"
                % (100.0 * fraction),
            }
        )
    minimum_rate = minimum_sample_rate_hz(chain, samples)
    if "sample_rate_hz" in spec:
        actual_rate = _positive("sample_rate_hz", spec["sample_rate_hz"])
        if not within_limit(minimum_rate, actual_rate):
            findings.append(
                {
                    "code": "sample-rate-too-low",
                    "sample_rate_hz": actual_rate,
                    "minimum_sample_rate_hz": minimum_rate,
                    "detail": "digitiser at %.3e Sa/s under-samples a %.3e s edge"
                    % (actual_rate, chain),
                }
            )
    gap = None
    if "duty_cycle" in spec:
        gap = inter_pulse_gap_s(pulse, spec["duty_cycle"])
        recovery = baseline_recovery_s(chain, recovery_factor)
        if not within_limit(recovery, gap):
            findings.append(
                {
                    "code": "baseline-not-recovered",
                    "inter_pulse_gap_s": gap,
                    "baseline_recovery_s": recovery,
                    "detail": "gap of %.3e s is shorter than the %.3e s the detector "
                    "needs to settle" % (gap, recovery),
                }
            )
    return {
        "chain_rise_time_s": chain,
        "required_rise_time_s": required,
        "dominant_stage_index": dominant_stage_index(stages),
        "speed_category": categorize_detection_speed(chain, pulse),
        "observation_window_s": window,
        "window_fraction": fraction,
        "minimum_sample_rate_hz": minimum_rate,
        "inter_pulse_gap_s": gap,
        "shortest_supported_pulse_width_s": shortest_supported_pulse_width_s(
            chain, ratio
        ),
        "findings": findings,
        "compliant": not findings,
    }

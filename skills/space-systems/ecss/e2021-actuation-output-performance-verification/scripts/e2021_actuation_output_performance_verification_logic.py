#!/usr/bin/env python3
"""Actuation output performance verification under ECSS-E-ST-20-21C
clause 5.5.1.

Paraphrased, implementable procedure (no verbatim standard text):

* The performance an actuator electronics claims is not verified by the
  actuator having moved. It is verified by showing that the firing current
  it delivered and the output voltage it presented both sat inside the
  limits the interface declares for them.
* A firing pulse is not one number. It rises, holds and falls, and the
  quantity the limits apply to is the held part -- the plateau. Reading a
  transient overshoot as the delivered current, or averaging the rise and
  the fall into it, both produce a figure the limits were never written
  against.
* A measurement carries an uncertainty, and the uncertainty has a
  direction that depends on which limit is being tested. Against a floor
  the reading is taken at its lowest credible value; against a ceiling at
  its highest. Applying it in the flattering direction, or leaving it out,
  is how a channel sitting on a limit is reported as passing.
* Current and voltage are graded separately and both must hold. A channel
  can deliver the required current while presenting an output voltage
  outside its band, which points at the drive stage rather than at the
  load, so the report names which of the two fell short.
* The verdict is taken on the worst channel. Averaging a set of firing
  lines buries one bad channel among good ones, and one channel outside
  its limits holds the verification.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations, and every limit comparison runs through a named
tolerance so a reading landing exactly on a limit does not turn on the
last bit of a sum.
"""

import math

# Named tolerance absorbing representation error in a limit comparison.
# It is NOT a measurement allowance: the declared limits are never relaxed.
LIMIT_EPS = 1e-9

TOWARD_FLOOR = "toward-floor"
TOWARD_CEILING = "toward-ceiling"
UNCERTAINTY_DIRECTIONS = (TOWARD_FLOOR, TOWARD_CEILING)

FIRING_CURRENT = "firing-current"
OUTPUT_VOLTAGE = "output-voltage"
GRADED_QUANTITIES = (FIRING_CURRENT, OUTPUT_VOLTAGE)

DEFAULT_PERFORMANCE_SPEC = {
    "min_firing_current_a": 3.5,
    "max_firing_current_a": 8.0,
    "min_output_voltage_v": 22.0,
    "max_output_voltage_v": 34.0,
    "plateau_fraction": 0.9,
    "min_plateau_samples": 3.0,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=LIMIT_EPS
    )


def _at_most(value, ceiling_value):
    """True when value stays under ceiling_value, absorbing representation error."""
    return value <= ceiling_value or math.isclose(
        value, ceiling_value, rel_tol=0.0, abs_tol=LIMIT_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the declared interface performance limits."""
    spec = dict(DEFAULT_PERFORMANCE_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_PERFORMANCE_SPEC:
            raise ValueError("unrecognized performance specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number <= 0.0:
            raise ValueError("spec %r must be positive, got %r" % (key, value))
        spec[key] = number
    if not (0.0 < spec["plateau_fraction"] <= 1.0):
        raise ValueError(
            "plateau_fraction must lie in (0, 1], got %r" % (spec["plateau_fraction"],)
        )
    if spec["min_plateau_samples"] < 1.0:
        raise ValueError(
            "min_plateau_samples must be at least one, got %r"
            % (spec["min_plateau_samples"],)
        )
    if spec["min_firing_current_a"] >= spec["max_firing_current_a"]:
        raise ValueError("firing current limits do not bracket a band")
    if spec["min_output_voltage_v"] >= spec["max_output_voltage_v"]:
        raise ValueError("output voltage limits do not bracket a band")
    return spec


def plateau_value(samples, fraction=0.9, min_samples=3.0):
    """Held value of a firing pulse, taken over its plateau samples only."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence")
    values = [_require_number(s, "pulse sample") for s in samples]
    fraction = _require_number(fraction, "plateau fraction")
    min_samples = _require_number(min_samples, "minimum plateau samples")
    if not (0.0 < fraction <= 1.0):
        raise ValueError("plateau fraction must lie in (0, 1], got %r" % (fraction,))
    peak = max(values)
    if peak <= 0.0:
        raise ValueError("pulse peak must be positive, got %r" % (peak,))
    threshold = peak * fraction
    held = [v for v in values if _at_least(v, threshold)]
    if len(held) < min_samples:
        raise ValueError(
            "pulse holds only %d sample(s) at or above %r; %r are required"
            % (len(held), threshold, min_samples)
        )
    total = 0.0
    for v in held:
        total += v
    return total / len(held)


def apply_uncertainty(value, uncertainty, direction):
    """Reading pushed in the direction that works against the case."""
    value = _require_number(value, "reading")
    uncertainty = _require_number(uncertainty, "uncertainty")
    if uncertainty < 0.0:
        raise ValueError("uncertainty must not be negative, got %r" % (uncertainty,))
    if direction not in UNCERTAINTY_DIRECTIONS:
        raise ValueError(
            "unrecognized uncertainty direction %r (expected one of %s)"
            % (direction, ", ".join(UNCERTAINTY_DIRECTIONS))
        )
    if direction == TOWARD_FLOOR:
        return value - uncertainty
    return value + uncertainty


def grade_quantity(reading, uncertainty, floor_value, ceiling_value):
    """Grade one reading against its own floor and ceiling."""
    floor_value = _require_number(floor_value, "floor")
    ceiling_value = _require_number(ceiling_value, "ceiling")
    if floor_value >= ceiling_value:
        raise ValueError(
            "floor %r is not below ceiling %r" % (floor_value, ceiling_value)
        )
    low = apply_uncertainty(reading, uncertainty, TOWARD_FLOOR)
    high = apply_uncertainty(reading, uncertainty, TOWARD_CEILING)
    floor_ok = _at_least(low, floor_value)
    ceiling_ok = _at_most(high, ceiling_value)
    shortfall = max(0.0, floor_value - low)
    excess = max(0.0, high - ceiling_value)
    return {
        "reading": _require_number(reading, "reading"),
        "worst_low": low,
        "worst_high": high,
        "floor": floor_value,
        "ceiling": ceiling_value,
        "floor_ok": floor_ok,
        "ceiling_ok": ceiling_ok,
        "shortfall": shortfall,
        "excess": excess,
        "within_limits": floor_ok and ceiling_ok,
        "miss_fraction": max(shortfall / floor_value, excess / ceiling_value),
        "headroom_fraction": min(
            (low - floor_value) / floor_value, (ceiling_value - high) / ceiling_value
        ),
    }


def _channel_reading(channel, direct_key, samples_key, spec, label):
    if direct_key in channel and samples_key in channel:
        raise ValueError(
            "channel declares both %r and %r; give one %s source"
            % (direct_key, samples_key, label)
        )
    if direct_key in channel:
        return _require_number(channel[direct_key], "channel %r" % direct_key)
    if samples_key in channel:
        return plateau_value(
            channel[samples_key], spec["plateau_fraction"], spec["min_plateau_samples"]
        )
    raise ValueError(
        "channel gives no %s reading (expected %r or %r)"
        % (label, direct_key, samples_key)
    )


def evaluate_channel(channel, spec=None):
    """Performance verdict for one actuation output channel."""
    resolved = resolve_spec(spec)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    name = _require_text(channel.get("name"), "channel 'name'")
    current = _channel_reading(
        channel, "firing_current_a", "current_samples_a", resolved, "firing current"
    )
    voltage = _channel_reading(
        channel, "output_voltage_v", "voltage_samples_v", resolved, "output voltage"
    )
    current_grade = grade_quantity(
        current,
        channel.get("current_uncertainty_a", 0.0),
        resolved["min_firing_current_a"],
        resolved["max_firing_current_a"],
    )
    voltage_grade = grade_quantity(
        voltage,
        channel.get("voltage_uncertainty_v", 0.0),
        resolved["min_output_voltage_v"],
        resolved["max_output_voltage_v"],
    )
    if current_grade["within_limits"] and voltage_grade["within_limits"]:
        dominant = "none"
    elif not current_grade["within_limits"] and not voltage_grade["within_limits"]:
        dominant = (
            FIRING_CURRENT
            if current_grade["miss_fraction"] >= voltage_grade["miss_fraction"]
            else OUTPUT_VOLTAGE
        )
    elif not current_grade["within_limits"]:
        dominant = FIRING_CURRENT
    else:
        dominant = OUTPUT_VOLTAGE
    return {
        "name": name,
        "firing_current": current_grade,
        "output_voltage": voltage_grade,
        "dominant_shortfall": dominant,
        "verified": current_grade["within_limits"] and voltage_grade["within_limits"],
    }


def channel_headroom_fraction(result):
    """Least fractional headroom the channel holds on either quantity."""
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping, got %r" % (result,))
    for key in ("firing_current", "output_voltage"):
        if key not in result:
            raise ValueError("result missing required key %r" % (key,))
    return min(
        result["firing_current"]["headroom_fraction"],
        result["output_voltage"]["headroom_fraction"],
    )


def worst_channel(results):
    """The channel holding the least fractional headroom to its own limits."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    worst = results[0]
    worst_headroom = channel_headroom_fraction(worst)
    for result in results[1:]:
        headroom = channel_headroom_fraction(result)
        if headroom < worst_headroom:
            worst, worst_headroom = result, headroom
    return worst


def verification_status(findings):
    """Gate token for the finding list of one performance verification."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "output-performance-verified" if not findings else "hold-output-performance"


def evaluate_verification(config):
    """End-to-end clause 5.5.1 verification over a set of output channels."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "channels" not in config:
        raise ValueError("config missing required key 'channels'")
    channels = config["channels"]
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("channels must be a non-empty sequence")
    spec = resolve_spec(config.get("spec"))
    results = [evaluate_channel(channel, config.get("spec")) for channel in channels]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("channel names must be unique, got %r" % (names,))

    findings = []
    for result in results:
        if not result["firing_current"]["within_limits"]:
            findings.append(
                "%s delivers a firing current outside its limits (worst low %.6f A, worst high %.6f A)"
                % (
                    result["name"],
                    result["firing_current"]["worst_low"],
                    result["firing_current"]["worst_high"],
                )
            )
        if not result["output_voltage"]["within_limits"]:
            findings.append(
                "%s presents an output voltage outside its limits (worst low %.6f V, worst high %.6f V)"
                % (
                    result["name"],
                    result["output_voltage"]["worst_low"],
                    result["output_voltage"]["worst_high"],
                )
            )
    worst = worst_channel(results)
    return {
        "spec": spec,
        "channels": results,
        "worst_channel": worst,
        "worst_channel_headroom_fraction": channel_headroom_fraction(worst),
        "findings": findings,
        "status": verification_status(findings),
        "verified": not findings,
    }

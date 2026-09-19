#!/usr/bin/env python3
"""Firing telemetry sampling rate for long duration actuators under
ECSS-E-ST-20-21C clause 5.5.3.

Paraphrased, implementable procedure (no verbatim standard text):

* While a long duration actuator is firing, the current it draws and the
  voltage across it are worth sampling into housekeeping at a rate that
  makes the record usable afterwards. This is a recommendation, and it
  applies to firings long enough for a record to exist at all.
* The first question is therefore whether the firing is long duration.
  Below the threshold there is nothing to sample against and the
  recommendation does not bite; a firing exactly at the threshold does
  count, because the threshold is the entry condition and not an
  exclusion.
* The rate is driven by the shortest feature the record has to show --
  the current step at initiation, a dropout, a resistance change part way
  through. A bare Nyquist pair of samples per feature proves the feature
  existed; an oversampling factor of several samples per feature is what
  lets its shape be read, so the rate is sized from the factor and not
  from the Nyquist limit.
* A recommended floor sits underneath that. A slow feature must not pull
  the rate below the floor, so the rate adopted is the larger of the two.
* Rate alone does not deliver a record. The housekeeping buffer has to
  hold the samples the firing will generate, counted across every
  monitored channel -- current and voltage are two channels, not one --
  and the duration the buffer actually covers is what says whether the
  end of the firing survives.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations, and every rate and coverage comparison runs through a
named tolerance so a case sitting exactly on a limit does not turn on the
last bit of a division.
"""

import math

# Named tolerance absorbing representation error in a rate or coverage
# comparison. It is NOT an engineering allowance: no recommended figure is
# reduced by it.
RATE_EPS = 1e-9

DEFAULT_SAMPLING_SPEC = {
    "long_duration_threshold_s": 1.0,
    "recommended_min_rate_hz": 100.0,
    "oversampling_factor": 10.0,
    "monitored_channels": 2.0,
}

APPLICABLE = "recommendation-applies"
NOT_APPLICABLE = "recommendation-not-applicable"


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
        value, floor_value, rel_tol=0.0, abs_tol=RATE_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the recommended sampling specification."""
    spec = dict(DEFAULT_SAMPLING_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_SAMPLING_SPEC:
            raise ValueError("unrecognized sampling specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number <= 0.0:
            raise ValueError("spec %r must be positive, got %r" % (key, value))
        spec[key] = number
    if spec["oversampling_factor"] < 2.0:
        raise ValueError(
            "oversampling_factor must be at least two samples per feature, got %r"
            % (spec["oversampling_factor"],)
        )
    if spec["monitored_channels"] < 1.0:
        raise ValueError(
            "monitored_channels must be at least one, got %r"
            % (spec["monitored_channels"],)
        )
    return spec


def is_long_duration(firing_duration_s, threshold_s):
    """True when a firing is long enough for the recommendation to bite."""
    firing_duration_s = _require_number(firing_duration_s, "firing duration")
    threshold_s = _require_number(threshold_s, "long duration threshold")
    if firing_duration_s <= 0.0:
        raise ValueError(
            "firing duration must be positive, got %r" % (firing_duration_s,)
        )
    if threshold_s <= 0.0:
        raise ValueError(
            "long duration threshold must be positive, got %r" % (threshold_s,)
        )
    return _at_least(firing_duration_s, threshold_s)


def feature_driven_rate_hz(shortest_feature_s, oversampling_factor):
    """Rate that puts the required number of samples inside the shortest feature."""
    shortest_feature_s = _require_number(shortest_feature_s, "shortest feature")
    oversampling_factor = _require_number(oversampling_factor, "oversampling factor")
    if shortest_feature_s <= 0.0:
        raise ValueError(
            "shortest feature must be positive, got %r" % (shortest_feature_s,)
        )
    if oversampling_factor < 2.0:
        raise ValueError(
            "oversampling factor must be at least two, got %r" % (oversampling_factor,)
        )
    return oversampling_factor / shortest_feature_s


def required_rate_hz(shortest_feature_s, spec=None):
    """The larger of the feature-driven rate and the recommended floor."""
    resolved = resolve_spec(spec)
    driven = feature_driven_rate_hz(
        shortest_feature_s, resolved["oversampling_factor"]
    )
    floor_rate = resolved["recommended_min_rate_hz"]
    return driven if driven > floor_rate else floor_rate


def sample_interval_s(rate_hz):
    """Housekeeping sample interval implied by a sampling rate."""
    rate_hz = _require_number(rate_hz, "sampling rate")
    if rate_hz <= 0.0:
        raise ValueError("sampling rate must be positive, got %r" % (rate_hz,))
    return 1.0 / rate_hz


def samples_over_firing(firing_duration_s, rate_hz, monitored_channels):
    """Samples a firing generates across every monitored channel."""
    firing_duration_s = _require_number(firing_duration_s, "firing duration")
    rate_hz = _require_number(rate_hz, "sampling rate")
    monitored_channels = _require_number(monitored_channels, "monitored channels")
    if firing_duration_s <= 0.0:
        raise ValueError(
            "firing duration must be positive, got %r" % (firing_duration_s,)
        )
    if rate_hz <= 0.0:
        raise ValueError("sampling rate must be positive, got %r" % (rate_hz,))
    if monitored_channels < 1.0:
        raise ValueError(
            "monitored channels must be at least one, got %r" % (monitored_channels,)
        )
    return firing_duration_s * rate_hz * monitored_channels


def covered_duration_s(buffer_samples, rate_hz, monitored_channels):
    """Firing duration a housekeeping buffer of this depth actually covers."""
    buffer_samples = _require_number(buffer_samples, "buffer depth")
    rate_hz = _require_number(rate_hz, "sampling rate")
    monitored_channels = _require_number(monitored_channels, "monitored channels")
    if buffer_samples < 0.0:
        raise ValueError("buffer depth must not be negative, got %r" % (buffer_samples,))
    if rate_hz <= 0.0:
        raise ValueError("sampling rate must be positive, got %r" % (rate_hz,))
    if monitored_channels < 1.0:
        raise ValueError(
            "monitored channels must be at least one, got %r" % (monitored_channels,)
        )
    return buffer_samples / (rate_hz * monitored_channels)


def evaluate_actuator(actuator, spec=None):
    """Sampling plan and verdict for one firing actuator."""
    resolved = resolve_spec(spec)
    if not isinstance(actuator, dict):
        raise ValueError("actuator must be a mapping, got %r" % (actuator,))
    name = _require_text(actuator.get("name"), "actuator 'name'")
    duration = _require_number(
        actuator.get("firing_duration_s"), "actuator %r firing duration" % name
    )
    feature = _require_number(
        actuator.get("shortest_feature_s"), "actuator %r shortest feature" % name
    )
    if feature > duration:
        raise ValueError(
            "actuator %r declares a feature longer than the firing itself" % (name,)
        )
    long_duration = is_long_duration(duration, resolved["long_duration_threshold_s"])
    required = required_rate_hz(feature, spec)
    declared = actuator.get("declared_rate_hz")
    if declared is None:
        adopted = required
        rate_adequate = True
    else:
        adopted = _require_number(declared, "actuator %r declared rate" % name)
        if adopted <= 0.0:
            raise ValueError(
                "actuator %r declared rate must be positive, got %r" % (name, adopted)
            )
        rate_adequate = _at_least(adopted, required)
    channels = resolved["monitored_channels"]
    needed = samples_over_firing(duration, adopted, channels)
    buffer_samples = _require_number(
        actuator.get("telemetry_buffer_samples", needed),
        "actuator %r telemetry buffer" % name,
    )
    covered = covered_duration_s(buffer_samples, adopted, channels)
    buffer_covers = _at_least(buffer_samples, needed)
    return {
        "name": name,
        "firing_duration_s": duration,
        "shortest_feature_s": feature,
        "long_duration": long_duration,
        "applicability": APPLICABLE if long_duration else NOT_APPLICABLE,
        "feature_driven_rate_hz": feature_driven_rate_hz(
            feature, resolved["oversampling_factor"]
        ),
        "recommended_min_rate_hz": resolved["recommended_min_rate_hz"],
        "required_rate_hz": required,
        "adopted_rate_hz": adopted,
        "sample_interval_s": sample_interval_s(adopted),
        "monitored_channels": channels,
        "samples_over_firing": needed,
        "telemetry_buffer_samples": buffer_samples,
        "covered_duration_s": covered,
        "coverage_fraction": covered / duration,
        "rate_adequate": rate_adequate,
        "buffer_covers_firing": buffer_covers,
        "adequate": (not long_duration) or (rate_adequate and buffer_covers),
    }


def worst_actuator(results):
    """The actuator whose housekeeping covers the least of its own firing."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    worst = results[0]
    for result in results[1:]:
        if result["coverage_fraction"] < worst["coverage_fraction"]:
            worst = result
    return worst


def sampling_status(findings):
    """Gate token for the finding list of one sampling plan."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "sampling-plan-adequate" if not findings else "hold-sampling-plan"


def evaluate_plan(config):
    """End-to-end clause 5.5.3 sampling plan over a set of firing actuators."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "actuators" not in config:
        raise ValueError("config missing required key 'actuators'")
    actuators = config["actuators"]
    if not isinstance(actuators, (list, tuple)) or not actuators:
        raise ValueError("actuators must be a non-empty sequence")
    spec = resolve_spec(config.get("spec"))
    results = [evaluate_actuator(a, config.get("spec")) for a in actuators]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("actuator names must be unique, got %r" % (names,))

    findings = []
    for result in results:
        if not result["long_duration"]:
            continue
        if not result["rate_adequate"]:
            findings.append(
                "%s samples at %.6f Hz against a required %.6f Hz"
                % (result["name"], result["adopted_rate_hz"], result["required_rate_hz"])
            )
        if not result["buffer_covers_firing"]:
            findings.append(
                "%s has housekeeping for %.6f s of a %.6f s firing"
                % (
                    result["name"],
                    result["covered_duration_s"],
                    result["firing_duration_s"],
                )
            )
    worst = worst_actuator(results)
    return {
        "spec": spec,
        "actuators": results,
        "worst_actuator": worst,
        "worst_coverage_fraction": worst["coverage_fraction"],
        "findings": findings,
        "status": sampling_status(findings),
        "adequate": not findings,
    }

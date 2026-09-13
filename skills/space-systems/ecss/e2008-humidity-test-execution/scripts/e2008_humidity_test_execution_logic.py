"""Chamber-run accounting for a photovoltaic assembly humidity test.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.4.4 (humidity test -- test execution: the
specimen is held inside a humidity chamber at ambient pressure for the defined
duration). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the chamber log: time-ordered samples, each carrying a relative
   humidity, an air temperature and a chamber pressure.
2. Validate the three control bands -- humidity, temperature and the ambient
   pressure band the chamber is supposed to sit in.
3. Walk consecutive samples. An interval counts toward the conditioned dwell
   only when both of its endpoints sit inside all three bands; otherwise it is
   an excursion interval.
4. Accumulate the conditioned dwell, the cumulative excursion time, the longest
   single excursion, the number of separate excursions, and separately the time
   the chamber spent away from ambient pressure.
5. Compare the conditioned dwell with the defined duration and the excursions
   with their agreed limits, absorbing floating-point representation error at
   the boundaries with a named tolerance.
6. Report the accounting and every finding: dwell shortfall, an excursion that
   ran too long, too much cumulative excursion, or any departure from ambient
   pressure.
"""

import math

__all__ = [
    "AMBIENT_PRESSURE_BAND_KPA",
    "DEFAULT_MAX_SINGLE_EXCURSION_H",
    "DEFAULT_MAX_CUMULATIVE_EXCURSION_H",
    "DWELL_TOLERANCE_REL",
    "validate_band",
    "validate_sample",
    "validate_log",
    "value_in_band",
    "sample_conditioned",
    "sample_at_ambient_pressure",
    "accumulate_dwell",
    "assess_execution",
]

# The clause holds the chamber at ambient pressure: the run is a humidity
# exposure, not an altitude or a vacuum exposure. This is the default band a
# sea-level laboratory sits in.
AMBIENT_PRESSURE_BAND_KPA = (86.0, 106.0)

# A single control loss the chamber recovers from quickly does not invalidate
# the run; a long one changes the exposure the specimen saw.
DEFAULT_MAX_SINGLE_EXCURSION_H = 1.0
DEFAULT_MAX_CUMULATIVE_EXCURSION_H = 4.0

# Dwell is a sum of sample intervals and the limits are read from a test
# specification. A run that physically lands exactly on its duration can sum a
# few ULP either side of it, so the comparisons absorb that rather than moving
# the required duration.
DWELL_TOLERANCE_REL = 1e-9

_SAMPLE_KEYS = ("time_h", "relative_humidity_pct", "air_temperature_c", "pressure_kpa")


def validate_band(band, label):
    """Return a validated (low, high) control band."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    values = []
    for edge in band:
        if not isinstance(edge, (int, float)) or isinstance(edge, bool):
            raise ValueError("%s edges must be real numbers" % label)
        edge = float(edge)
        if not math.isfinite(edge):
            raise ValueError("%s edges must be finite" % label)
        values.append(edge)
    if values[0] > values[1]:
        raise ValueError("%s is inverted: %g above %g" % (label, values[0], values[1]))
    return (values[0], values[1])


def validate_sample(sample, index):
    """Return one validated chamber-log sample."""
    if not isinstance(sample, dict):
        raise ValueError("chamber log sample %d must be a mapping" % index)
    for key in _SAMPLE_KEYS:
        if key not in sample:
            raise ValueError("chamber log sample %d is missing '%s'" % (index, key))
        value = sample[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("chamber log sample %d '%s' must be a real number" % (index, key))
        if not math.isfinite(float(value)):
            raise ValueError("chamber log sample %d '%s' must be finite" % (index, key))
    record = dict((key, float(sample[key])) for key in _SAMPLE_KEYS)
    if record["time_h"] < 0.0:
        raise ValueError("chamber log sample %d has a negative time stamp" % index)
    if record["relative_humidity_pct"] < 0.0 or record["relative_humidity_pct"] > 100.0:
        raise ValueError(
            "chamber log sample %d relative humidity outside 0-100 %%: %g"
            % (index, record["relative_humidity_pct"])
        )
    if record["pressure_kpa"] <= 0.0:
        raise ValueError("chamber log sample %d pressure must be positive" % index)
    record["index"] = index
    return record


def validate_log(samples):
    """Return the validated, strictly time-ordered chamber log."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("chamber log needs at least two samples to bound an interval")
    log = [validate_sample(sample, i) for i, sample in enumerate(samples)]
    for i in range(1, len(log)):
        if log[i]["time_h"] <= log[i - 1]["time_h"]:
            raise ValueError(
                "chamber log time stamps must strictly increase (sample %d at %g h "
                "follows %g h)" % (i, log[i]["time_h"], log[i - 1]["time_h"])
            )
    return log


def value_in_band(value, band):
    """Return True when a value sits inside a band, edges included."""
    low, high = validate_band(band, "band")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if math.isclose(value, low, rel_tol=DWELL_TOLERANCE_REL, abs_tol=0.0):
        return True
    if math.isclose(value, high, rel_tol=DWELL_TOLERANCE_REL, abs_tol=0.0):
        return True
    return low < value < high


def sample_conditioned(sample, humidity_band, temperature_band):
    """Return True when a sample sits inside the humidity and temperature bands."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("relative_humidity_pct", "air_temperature_c"):
        if key not in sample:
            raise ValueError("sample is missing '%s'" % key)
    return value_in_band(sample["relative_humidity_pct"], humidity_band) and value_in_band(
        sample["air_temperature_c"], temperature_band
    )


def sample_at_ambient_pressure(sample, pressure_band=AMBIENT_PRESSURE_BAND_KPA):
    """Return True when a sample sits inside the ambient pressure band."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    if "pressure_kpa" not in sample:
        raise ValueError("sample is missing 'pressure_kpa'")
    return value_in_band(sample["pressure_kpa"], pressure_band)


def accumulate_dwell(samples, humidity_band, temperature_band,
                     pressure_band=AMBIENT_PRESSURE_BAND_KPA):
    """Walk the chamber log and return the dwell and excursion accounting."""
    log = validate_log(samples)
    humidity_band = validate_band(humidity_band, "humidity_band")
    temperature_band = validate_band(temperature_band, "temperature_band")
    pressure_band = validate_band(pressure_band, "pressure_band")

    conditioned = []
    excursions = []
    pressure_loss = []
    runs = []
    current_run = 0.0
    in_run = False
    for i in range(1, len(log)):
        start = log[i - 1]
        end = log[i]
        span = end["time_h"] - start["time_h"]
        held = (
            sample_conditioned(start, humidity_band, temperature_band)
            and sample_conditioned(end, humidity_band, temperature_band)
            and sample_at_ambient_pressure(start, pressure_band)
            and sample_at_ambient_pressure(end, pressure_band)
        )
        if not (
            sample_at_ambient_pressure(start, pressure_band)
            and sample_at_ambient_pressure(end, pressure_band)
        ):
            pressure_loss.append(span)
        if held:
            conditioned.append(span)
            if in_run:
                runs.append(current_run)
                current_run = 0.0
                in_run = False
        else:
            excursions.append(span)
            current_run += span
            in_run = True
    if in_run:
        runs.append(current_run)

    return {
        "sample_count": len(log),
        "log_span_h": log[-1]["time_h"] - log[0]["time_h"],
        "conditioned_dwell_h": math.fsum(conditioned),
        "excursion_h": math.fsum(excursions),
        "pressure_excursion_h": math.fsum(pressure_loss),
        "longest_excursion_h": max(runs) if runs else 0.0,
        "excursion_count": len(runs),
    }


def _within_limit(value, limit):
    """Return True when value does not exceed limit, boundary absorbed."""
    if math.isclose(value, limit, rel_tol=DWELL_TOLERANCE_REL, abs_tol=0.0):
        return True
    return value < limit


def _reaches(value, target):
    """Return True when value reaches target, boundary absorbed."""
    if math.isclose(value, target, rel_tol=DWELL_TOLERANCE_REL, abs_tol=0.0):
        return True
    return value > target


def assess_execution(spec):
    """Run the full clause 5.5.1.4.4 test-execution assessment.

    spec keys: chamber_log, humidity_band, temperature_band, required_duration_h,
    optional pressure_band, max_single_excursion_h and max_cumulative_excursion_h.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("chamber_log", "humidity_band", "temperature_band", "required_duration_h"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = spec["required_duration_h"]
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_duration_h must be a real number")
    required = float(required)
    if not math.isfinite(required) or required <= 0.0:
        raise ValueError("required_duration_h must be positive and finite")
    single_limit = spec.get("max_single_excursion_h", DEFAULT_MAX_SINGLE_EXCURSION_H)
    cumulative_limit = spec.get(
        "max_cumulative_excursion_h", DEFAULT_MAX_CUMULATIVE_EXCURSION_H
    )
    for label, value in (
        ("max_single_excursion_h", single_limit),
        ("max_cumulative_excursion_h", cumulative_limit),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("%s must be non-negative and finite" % label)
    single_limit = float(single_limit)
    cumulative_limit = float(cumulative_limit)

    accounting = accumulate_dwell(
        spec["chamber_log"],
        spec["humidity_band"],
        spec["temperature_band"],
        spec.get("pressure_band", AMBIENT_PRESSURE_BAND_KPA),
    )

    findings = []
    if not _reaches(accounting["conditioned_dwell_h"], required):
        findings.append(
            "conditioned dwell of %.3f h falls short of the defined duration %.3f h"
            % (accounting["conditioned_dwell_h"], required)
        )
    if not _within_limit(accounting["longest_excursion_h"], single_limit):
        findings.append(
            "a single control excursion ran %.3f h against a limit of %.3f h"
            % (accounting["longest_excursion_h"], single_limit)
        )
    if not _within_limit(accounting["excursion_h"], cumulative_limit):
        findings.append(
            "cumulative control excursion of %.3f h exceeds the limit of %.3f h"
            % (accounting["excursion_h"], cumulative_limit)
        )
    if accounting["pressure_excursion_h"] > 0.0:
        findings.append(
            "chamber left the ambient pressure band for %.3f h; the run is no longer "
            "an ambient-pressure humidity exposure"
            % accounting["pressure_excursion_h"]
        )

    result = dict(accounting)
    result["required_duration_h"] = required
    result["max_single_excursion_h"] = single_limit
    result["max_cumulative_excursion_h"] = cumulative_limit
    result["duration_satisfied"] = not findings
    result["findings"] = findings
    return result

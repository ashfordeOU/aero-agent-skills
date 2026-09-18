"""Cure schedule verification for an applied paint system.

Anchor: ECSS-Q-ST-70-31C, Cure. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the logged cure profile as an ordered list of segments, each with a
   duration, a hold temperature and, where the system needs it, a relative
   humidity.
2. Award cure credit segment by segment. A segment below the system's minimum
   cure temperature earns nothing, because the reaction has effectively
   stopped rather than merely slowed. A segment above the maximum earns
   nothing either and raises an overbake finding, because heat past the
   qualified ceiling changes the film rather than advancing its cure.
3. Convert each earning segment to equivalent hours at the reference
   temperature through the ten-degree rule: a ten kelvin rise multiplies the
   rate by the system's declared factor.
4. Enforce the schedule's other conditions: total equivalent hours against
   the requirement, continuous dwell at or above the minimum temperature, the
   humidity window while the film is still reactive, and the ramp rate
   between consecutive holds.
5. Return a single cure-complete verdict with every finding named.
"""

import math

__all__ = [
    "CURE_TOLERANCE",
    "DEFAULT_Q10",
    "validate_positive",
    "validate_segment",
    "validate_profile",
    "equivalent_hours",
    "segment_credit",
    "ramp_rates_c_per_h",
    "longest_dwell_h",
    "accumulate_cure",
    "assess_cure",
]

# Logged durations and thresholds are decimal values that land exactly on a
# requirement. Absorb the representation error here, not in the schedule.
CURE_TOLERANCE = 1e-9

# Rate multiplier for a ten kelvin rise, when the system declares none.
DEFAULT_Q10 = 2.0


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_positive(value, label):
    """Return a validated strictly positive float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_segment(segment, index=0):
    """Return a validated cure segment as a plain mapping."""
    if not isinstance(segment, dict):
        raise ValueError("profile[%d] must be a mapping" % index)
    for key in ("duration_h", "temperature_c"):
        if key not in segment:
            raise ValueError("profile[%d] missing required key '%s'" % (index, key))
    duration = validate_positive(segment["duration_h"], "profile[%d].duration_h" % index)
    temperature = _real(segment["temperature_c"], "profile[%d].temperature_c" % index)
    if temperature < -80.0 or temperature > 400.0:
        raise ValueError(
            "profile[%d].temperature_c %g is outside any plausible cure range"
            % (index, temperature)
        )
    humidity = segment.get("relative_humidity_pct")
    if humidity is not None:
        humidity = _real(humidity, "profile[%d].relative_humidity_pct" % index)
        if humidity < 0.0 or humidity > 100.0:
            raise ValueError(
                "profile[%d].relative_humidity_pct must lie in [0, 100], got %g"
                % (index, humidity)
            )
    return {
        "duration_h": duration,
        "temperature_c": temperature,
        "relative_humidity_pct": humidity,
    }


def validate_profile(profile):
    """Return the validated ordered list of cure segments."""
    if not isinstance(profile, (list, tuple)) or not profile:
        raise ValueError("profile must be a non-empty sequence of cure segments")
    return [validate_segment(seg, i) for i, seg in enumerate(profile)]


def equivalent_hours(duration_h, temperature_c, reference_temperature_c, q10=DEFAULT_Q10):
    """Return hours at the reference temperature equivalent to this hold."""
    duration = validate_positive(duration_h, "duration_h")
    temperature = _real(temperature_c, "temperature_c")
    reference = _real(reference_temperature_c, "reference_temperature_c")
    factor = validate_positive(q10, "q10")
    if factor <= 1.0:
        raise ValueError("q10 must exceed 1 to describe a thermally driven cure, got %g" % factor)
    return duration * math.pow(factor, (temperature - reference) / 10.0)


def segment_credit(segment, schedule):
    """Return the equivalent-hour credit and any finding for one segment."""
    seg = validate_segment(segment)
    minimum = _real(schedule["min_temperature_c"], "min_temperature_c")
    maximum = _real(schedule["max_temperature_c"], "max_temperature_c")
    if minimum > maximum:
        raise ValueError(
            "min_temperature_c %g exceeds max_temperature_c %g" % (minimum, maximum)
        )
    reference = _real(schedule["reference_temperature_c"], "reference_temperature_c")
    factor = schedule.get("q10", DEFAULT_Q10)
    findings = []
    if seg["temperature_c"] > maximum + CURE_TOLERANCE:
        findings.append(
            "hold at %g degC for %g h exceeds the qualified ceiling %g degC"
            % (seg["temperature_c"], seg["duration_h"], maximum)
        )
        return {"segment": seg, "credit_h": 0.0, "earning": False, "findings": findings}
    if seg["temperature_c"] < minimum - CURE_TOLERANCE:
        findings.append(
            "hold at %g degC for %g h sits below the minimum cure temperature %g degC"
            % (seg["temperature_c"], seg["duration_h"], minimum)
        )
        return {"segment": seg, "credit_h": 0.0, "earning": False, "findings": findings}
    band = schedule.get("humidity_band")
    if band is not None:
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("humidity_band must be a (low, high) pair")
        low = _real(band[0], "humidity_band low")
        high = _real(band[1], "humidity_band high")
        if low > high:
            raise ValueError("humidity_band low %g exceeds high %g" % (low, high))
        measured = seg["relative_humidity_pct"]
        if measured is None:
            findings.append(
                "hold at %g degC carries no humidity reading, but the system declares a window"
                % seg["temperature_c"]
            )
            return {"segment": seg, "credit_h": 0.0, "earning": False, "findings": findings}
        if measured < low - CURE_TOLERANCE or measured > high + CURE_TOLERANCE:
            findings.append(
                "hold at %g degC ran at %g percent relative humidity, outside [%g, %g]"
                % (seg["temperature_c"], measured, low, high)
            )
            return {"segment": seg, "credit_h": 0.0, "earning": False, "findings": findings}
    credit = equivalent_hours(
        seg["duration_h"], seg["temperature_c"], reference, factor
    )
    return {"segment": seg, "credit_h": credit, "earning": True, "findings": findings}


def ramp_rates_c_per_h(profile):
    """Return the ramp rate between each pair of consecutive holds."""
    segments = validate_profile(profile)
    rates = []
    for i in range(1, len(segments)):
        delta = segments[i]["temperature_c"] - segments[i - 1]["temperature_c"]
        span = 0.5 * (segments[i]["duration_h"] + segments[i - 1]["duration_h"])
        rates.append(delta / span)
    return rates


def longest_dwell_h(credits):
    """Return the longest run of consecutive earning segments, in hours."""
    if not isinstance(credits, (list, tuple)):
        raise ValueError("credits must be a sequence of segment credit records")
    best = 0.0
    run = 0.0
    for record in credits:
        if record.get("earning"):
            run += record["segment"]["duration_h"]
            if run > best:
                best = run
        else:
            run = 0.0
    return best


def accumulate_cure(profile, schedule):
    """Return the per-segment credits and the accumulated cure totals."""
    segments = validate_profile(profile)
    credits = [segment_credit(seg, schedule) for seg in segments]
    total_equivalent = sum(record["credit_h"] for record in credits)
    elapsed = sum(seg["duration_h"] for seg in segments)
    return {
        "credits": credits,
        "total_equivalent_h": total_equivalent,
        "elapsed_h": elapsed,
        "longest_dwell_h": longest_dwell_h(credits),
        "findings": [text for record in credits for text in record["findings"]],
    }


def assess_cure(spec):
    """Run the full cure-schedule assessment for one applied system.

    spec keys: profile, reference_temperature_c, min_temperature_c,
    max_temperature_c, required_equivalent_h; optional q10, humidity_band,
    min_dwell_h, max_ramp_c_per_h.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "profile",
        "reference_temperature_c",
        "min_temperature_c",
        "max_temperature_c",
        "required_equivalent_h",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = validate_positive(spec["required_equivalent_h"], "required_equivalent_h")
    totals = accumulate_cure(spec["profile"], spec)
    findings = list(totals["findings"])

    met = totals["total_equivalent_h"] >= required - CURE_TOLERANCE
    if not met:
        findings.append(
            "accumulated %.3f equivalent hours against a required %.3f"
            % (totals["total_equivalent_h"], required)
        )
    dwell_ok = True
    min_dwell = spec.get("min_dwell_h")
    if min_dwell is not None:
        min_dwell = validate_positive(min_dwell, "min_dwell_h")
        dwell_ok = totals["longest_dwell_h"] >= min_dwell - CURE_TOLERANCE
        if not dwell_ok:
            findings.append(
                "longest continuous in-window dwell %.3f h is short of the required %.3f h"
                % (totals["longest_dwell_h"], min_dwell)
            )
    ramp_ok = True
    rates = ramp_rates_c_per_h(spec["profile"])
    max_ramp = spec.get("max_ramp_c_per_h")
    if max_ramp is not None:
        max_ramp = validate_positive(max_ramp, "max_ramp_c_per_h")
        for i, rate in enumerate(rates):
            if abs(rate) > max_ramp + CURE_TOLERANCE:
                ramp_ok = False
                findings.append(
                    "ramp of %.2f degC/h between hold %d and hold %d exceeds the %.2f degC/h limit"
                    % (rate, i, i + 1, max_ramp)
                )
    return {
        "credits": totals["credits"],
        "total_equivalent_h": totals["total_equivalent_h"],
        "elapsed_h": totals["elapsed_h"],
        "longest_dwell_h": totals["longest_dwell_h"],
        "ramp_rates_c_per_h": rates,
        "required_equivalent_h": required,
        "equivalent_hours_met": met,
        "dwell_met": dwell_ok,
        "ramp_within_limit": ramp_ok,
        "findings": findings,
        "cure_complete": not findings,
    }

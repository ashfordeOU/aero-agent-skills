"""Pressure cycling (fatigue) test definition for two-phase heat transport.

Anchor: ECSS-E-ST-31-02C clause 5.6.6 (pressure cycle test: conditions and
criteria). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Cycle count: the service cycle count -- ground pressurisations, flight
   transients and thermally driven excursions all counted -- is multiplied by
   the life scatter factor and rounded up to whole cycles.
2. Pressure range: the applied cycle has to envelop the service cycle at both
   ends. A cycle that starts above the service minimum or stops below the
   service maximum leaves part of the duty cycle untested, and the range it
   does apply is the amplitude the fatigue damage is accumulated at.
3. Rate: the cycle rate and the pressure ramp rate are bounded, because a
   fast cycle heats the working fluid and stops being the mechanical duty
   cycle it is supposed to reproduce.
4. Temperature: the cycling is run inside the declared temperature band.
5. Acceptance: the article completes the required count without leakage and
   passes the post-cycling leak measurement against its allowable rate.
"""

import math

__all__ = [
    "CYCLE_TOLERANCE",
    "MIN_SCATTER_FACTOR",
    "DEFAULT_MAX_RAMP_RATE_PA_PER_S",
    "DEFAULT_MAX_CYCLE_RATE_HZ",
    "require_real",
    "require_positive",
    "require_non_negative",
    "require_count",
    "validate_scatter_factor",
    "required_cycle_count",
    "validate_pressure_range",
    "assess_pressure_range",
    "cycle_rate_hz",
    "assess_cycle_rate",
    "assess_ramp_rate",
    "assess_cycle_count",
    "assess_temperature_band",
    "assess_post_cycle_leak",
    "assess_pressure_cycle_test",
]

# Counts, rates and pressures are float comparisons a correct campaign lands
# exactly on. Absorb the representation error, never the requirement.
CYCLE_TOLERANCE = 1e-9

# A life scatter factor below unity would test less than the service life.
MIN_SCATTER_FACTOR = 1.0

DEFAULT_MAX_RAMP_RATE_PA_PER_S = 1.0e5

DEFAULT_MAX_CYCLE_RATE_HZ = 0.5


def require_real(label, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def require_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    out = require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def require_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    out = require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def require_count(label, value):
    """Return value as a positive whole cycle count or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer cycle count, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=CYCLE_TOLERANCE)


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=CYCLE_TOLERANCE)


def validate_scatter_factor(scatter_factor):
    """Return a usable life scatter factor or raise ValueError."""
    factor = require_positive("scatter_factor", scatter_factor)
    if factor < MIN_SCATTER_FACTOR and not math.isclose(
            factor, MIN_SCATTER_FACTOR, rel_tol=0.0, abs_tol=CYCLE_TOLERANCE):
        raise ValueError(
            "scatter_factor must be at least %.3f, got %r"
            % (MIN_SCATTER_FACTOR, scatter_factor)
        )
    return factor


def required_cycle_count(service_cycles, scatter_factor):
    """Return the whole number of cycles the test owes."""
    service = require_count("service_cycles", service_cycles)
    factor = validate_scatter_factor(scatter_factor)
    exact = service * factor
    return int(math.ceil(exact - CYCLE_TOLERANCE))


def validate_pressure_range(low_pa, high_pa, label="pressure range"):
    """Return a validated (low, high) pressure pair in Pa."""
    low = require_non_negative("%s low_pa" % label, low_pa)
    high = require_positive("%s high_pa" % label, high_pa)
    if high <= low:
        raise ValueError("%s high %g Pa must exceed low %g Pa" % (label, high, low))
    return (low, high)


def assess_pressure_range(applied_low_pa, applied_high_pa,
                          service_low_pa, service_high_pa):
    """Grade the applied cycle range against the service range it must envelop."""
    applied = validate_pressure_range(applied_low_pa, applied_high_pa, "applied")
    service = validate_pressure_range(service_low_pa, service_high_pa, "service")
    covers_low = _at_most(applied[0], service[0])
    covers_high = _at_least(applied[1], service[1])
    findings = []
    if not covers_low:
        findings.append(
            "applied cycle bottoms out at %.4f Pa, above the service minimum "
            "%.4f Pa; the low end of the duty cycle is untested"
            % (applied[0], service[0])
        )
    if not covers_high:
        findings.append(
            "applied cycle peaks at %.4f Pa, below the service maximum %.4f Pa; "
            "the damaging end of the duty cycle is untested"
            % (applied[1], service[1])
        )
    applied_amplitude = applied[1] - applied[0]
    service_amplitude = service[1] - service[0]
    return {
        "applied_range_pa": applied,
        "service_range_pa": service,
        "applied_amplitude_pa": applied_amplitude,
        "service_amplitude_pa": service_amplitude,
        "amplitude_ratio": applied_amplitude / service_amplitude,
        "covers_low": covers_low,
        "covers_high": covers_high,
        "compliant": covers_low and covers_high,
        "findings": findings,
    }


def cycle_rate_hz(cycles, duration_s):
    """Return the mean cycle rate of a run in hertz."""
    count = require_count("cycles", cycles)
    duration = require_positive("duration_s", duration_s)
    return count / duration


def assess_cycle_rate(cycles, duration_s, max_rate_hz=DEFAULT_MAX_CYCLE_RATE_HZ):
    """Grade the mean cycle rate against its ceiling."""
    limit = require_positive("max_rate_hz", max_rate_hz)
    rate = cycle_rate_hz(cycles, duration_s)
    compliant = _at_most(rate, limit)
    findings = []
    if not compliant:
        findings.append(
            "mean cycle rate %.6f Hz exceeds the ceiling %.6f Hz; the run heats "
            "the working fluid instead of reproducing the mechanical duty cycle"
            % (rate, limit)
        )
    return {
        "rate_hz": rate,
        "max_rate_hz": limit,
        "compliant": compliant,
        "findings": findings,
    }


def assess_ramp_rate(applied_rate_pa_per_s,
                     max_rate_pa_per_s=DEFAULT_MAX_RAMP_RATE_PA_PER_S):
    """Grade the pressure ramp rate against its ceiling."""
    applied = require_positive("applied_rate_pa_per_s", applied_rate_pa_per_s)
    limit = require_positive("max_rate_pa_per_s", max_rate_pa_per_s)
    compliant = _at_most(applied, limit)
    findings = []
    if not compliant:
        findings.append("ramp rate %.4f Pa/s exceeds the ceiling %.4f Pa/s"
                        % (applied, limit))
    return {
        "applied_rate_pa_per_s": applied,
        "max_rate_pa_per_s": limit,
        "compliant": compliant,
        "findings": findings,
    }


def assess_cycle_count(applied_cycles, service_cycles, scatter_factor):
    """Grade the applied cycle count against the required life."""
    applied = require_count("applied_cycles", applied_cycles)
    required = required_cycle_count(service_cycles, scatter_factor)
    compliant = applied >= required
    findings = []
    if not compliant:
        findings.append("test applied %d cycles; %d required at a scatter factor of %g"
                        % (applied, required, float(scatter_factor)))
    return {
        "applied_cycles": applied,
        "required_cycles": required,
        "shortfall": max(0, required - applied),
        "compliant": compliant,
        "findings": findings,
    }


def assess_temperature_band(test_temperature_k, band_low_k, band_high_k):
    """Grade the cycling temperature against the declared band."""
    temperature = require_positive("test_temperature_k", test_temperature_k)
    low = require_positive("band_low_k", band_low_k)
    high = require_positive("band_high_k", band_high_k)
    if high <= low:
        raise ValueError("band_high_k %g must exceed band_low_k %g" % (high, low))
    inside = _at_least(temperature, low) and _at_most(temperature, high)
    findings = []
    if not inside:
        findings.append("cycling temperature %.4f K is outside the declared band "
                        "[%.4f, %.4f] K" % (temperature, low, high))
    return {
        "test_temperature_k": temperature,
        "band_k": (low, high),
        "compliant": inside,
        "findings": findings,
    }


def assess_post_cycle_leak(leak_detected_during, measured_leak_rate,
                           allowable_leak_rate):
    """Grade the post-cycling leak evidence."""
    if not isinstance(leak_detected_during, bool):
        raise ValueError("leak_detected_during must be a boolean observation, got %r"
                         % (leak_detected_during,))
    measured = require_non_negative("measured_leak_rate", measured_leak_rate)
    allowable = require_positive("allowable_leak_rate", allowable_leak_rate)
    within = _at_most(measured, allowable)
    findings = []
    if leak_detected_during:
        findings.append("leakage observed during cycling; the article did not "
                        "complete the life")
    if not within:
        findings.append("post-cycling leak rate %g exceeds the allowable %g"
                        % (measured, allowable))
    return {
        "leak_detected_during": leak_detected_during,
        "measured_leak_rate": measured,
        "allowable_leak_rate": allowable,
        "margin": allowable - measured,
        "compliant": within and not leak_detected_during,
        "findings": findings,
    }


def assess_pressure_cycle_test(spec):
    """Run the whole clause 5.6.6 pressure cycle test assessment.

    spec keys: service_cycles, scatter_factor, applied_cycles, duration_s,
    applied_low_pa, applied_high_pa, service_low_pa, service_high_pa,
    ramp_rate_pa_per_s, test_temperature_k, band_low_k, band_high_k,
    leak_detected_during, measured_leak_rate, allowable_leak_rate; optional
    max_cycle_rate_hz, max_ramp_rate_pa_per_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("service_cycles", "scatter_factor", "applied_cycles", "duration_s",
                "applied_low_pa", "applied_high_pa", "service_low_pa",
                "service_high_pa", "ramp_rate_pa_per_s", "test_temperature_k",
                "band_low_k", "band_high_k", "leak_detected_during",
                "measured_leak_rate", "allowable_leak_rate"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    count = assess_cycle_count(spec["applied_cycles"], spec["service_cycles"],
                               spec["scatter_factor"])
    pressure = assess_pressure_range(spec["applied_low_pa"], spec["applied_high_pa"],
                                     spec["service_low_pa"], spec["service_high_pa"])
    rate = assess_cycle_rate(spec["applied_cycles"], spec["duration_s"],
                             spec.get("max_cycle_rate_hz", DEFAULT_MAX_CYCLE_RATE_HZ))
    ramp = assess_ramp_rate(
        spec["ramp_rate_pa_per_s"],
        spec.get("max_ramp_rate_pa_per_s", DEFAULT_MAX_RAMP_RATE_PA_PER_S),
    )
    temperature = assess_temperature_band(spec["test_temperature_k"],
                                          spec["band_low_k"], spec["band_high_k"])
    leak = assess_post_cycle_leak(spec["leak_detected_during"],
                                  spec["measured_leak_rate"],
                                  spec["allowable_leak_rate"])
    checks = {
        "cycle_count": count,
        "pressure_range": pressure,
        "cycle_rate": rate,
        "ramp_rate": ramp,
        "temperature": temperature,
        "leak": leak,
    }
    findings = []
    for name in ("cycle_count", "pressure_range", "cycle_rate", "ramp_rate",
                 "temperature", "leak"):
        for item in checks[name]["findings"]:
            findings.append("%s: %s" % (name, item))
    return {
        "checks": checks,
        "failed_checks": sorted(n for n in checks if not checks[n]["compliant"]),
        "findings": findings,
        "compliant": all(checks[n]["compliant"] for n in checks),
    }

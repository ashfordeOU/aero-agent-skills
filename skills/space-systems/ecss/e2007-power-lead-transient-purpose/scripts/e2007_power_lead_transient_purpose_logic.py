#!/usr/bin/env python3
"""Power-lead transient purpose, ECSS-E-ST-20-07C 5.4.9.1.

Paraphrased purpose, no verbatim standard text. The clause states what the
power-lead transient test exists to show: that a unit keeps performing as
specified while brief voltage transients -- the ones other loads, switching
events and the harness itself couple onto the supply -- are applied to its
power leads. This module decides whether a set of injected transient records
actually demonstrates that:

  pulse record -> signed peak, half-amplitude width, volt-second area
  stress       -> applied peak against the level the interface specifies
  response     -> observed behaviour against the allowed performance category
  reduction    -> worst event per lead, then the governing lead
  coverage     -> both polarities and the required repeats on every lead

An under-driven pulse is the central trap: the unit survived something, but
not the specified transient, so it demonstrates nothing.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Absolute tolerance for voltage comparisons, volts. It absorbs float
# representation error at a specified level; it never lowers that level.
VOLTAGE_TOL = 1e-9

# Generic relative tolerance used for time comparisons.
REL_TOL = 1e-12

# Fraction of the specified level within which an applied peak is reported as
# sitting on the level rather than comfortably past it.
DEFAULT_AT_LEVEL_FRACTION = 0.02

POLARITY_POSITIVE = "positive"
POLARITY_NEGATIVE = "negative"
POLARITIES = (POLARITY_POSITIVE, POLARITY_NEGATIVE)

# Performance categories, ordered from the most benign outcome to the worst.
PERFORMANCE_NO_EFFECT = "no-effect"
PERFORMANCE_SELF_RECOVERING = "self-recovering"
PERFORMANCE_OPERATOR_RECOVERABLE = "operator-recoverable"
PERFORMANCE_PERMANENT = "permanent-degradation"
PERFORMANCE_ORDER = (
    PERFORMANCE_NO_EFFECT,
    PERFORMANCE_SELF_RECOVERING,
    PERFORMANCE_OPERATOR_RECOVERABLE,
    PERFORMANCE_PERMANENT,
)

STRESS_APPLIED = "stress-applied"
STRESS_AT_LEVEL = "stress-at-specified-level"
STRESS_SHORT = "stress-short-of-specified"

RESPONSE_ACCEPTED = "within-allowed-category"
RESPONSE_AT_CATEGORY = "at-allowed-category"
RESPONSE_REJECTED = "past-allowed-category"

VERDICT_DEMONSTRATED = "purpose-demonstrated"
VERDICT_NOT_DEMONSTRATED = "purpose-not-demonstrated"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def at_least(value, floor, tol=VOLTAGE_TOL):
    """True when value reaches the floor, absorbing float error only."""
    if value >= floor:
        return True
    return math.isclose(value, floor, rel_tol=0.0, abs_tol=tol)


def normalize_lead(lead):
    """Return the normalized designation of a power lead."""
    if not isinstance(lead, str):
        raise ValueError("power lead must be a string, got %r" % (lead,))
    key = lead.strip().lower()
    if not key:
        raise ValueError("power lead designation must not be empty")
    return key


def normalize_polarity(polarity):
    """Return the recognized polarity for a raw polarity name."""
    if not isinstance(polarity, str):
        raise ValueError("polarity must be a string, got %r" % (polarity,))
    key = polarity.strip().lower()
    if key not in POLARITIES:
        raise ValueError(
            "unrecognized polarity %r; recognized: %s"
            % (polarity, ", ".join(POLARITIES))
        )
    return key


def normalize_performance(category):
    """Return the recognized performance category for a raw category name."""
    if not isinstance(category, str):
        raise ValueError("performance category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in PERFORMANCE_ORDER:
        raise ValueError(
            "unrecognized performance category %r; recognized: %s"
            % (category, ", ".join(PERFORMANCE_ORDER))
        )
    return key


def validate_pulse(samples):
    """Validate an injected transient and return it as ordered float pairs."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples: must be a list of (time_s, volts) pairs")
    if len(samples) < 2:
        raise ValueError("samples: at least two samples are required")
    pulse = []
    previous_t = None
    for index, pair in enumerate(samples):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "samples[%d]: must be a (time_s, volts) pair, got %r" % (index, pair)
            )
        time_s = _number({"v": pair[0]}, "v", "samples[%d].time_s" % index)
        volts = _number({"v": pair[1]}, "v", "samples[%d].volts" % index)
        if previous_t is not None and time_s <= previous_t:
            raise ValueError(
                "samples[%d]: time_s %g does not advance past %g"
                % (index, time_s, previous_t)
            )
        previous_t = time_s
        pulse.append((time_s, volts))
    return pulse


def peak_amplitude_v(samples):
    """Largest excursion the transient reaches, keeping its sign."""
    pulse = validate_pulse(samples)
    return max((volts for _, volts in pulse), key=lambda v: (abs(v), v))


def pulse_polarity(samples):
    """Polarity of the transient, taken from its largest excursion."""
    peak = peak_amplitude_v(samples)
    if abs(peak) <= VOLTAGE_TOL:
        raise ValueError("transient never leaves zero; polarity is undefined")
    return POLARITY_POSITIVE if peak > 0.0 else POLARITY_NEGATIVE


def half_amplitude_width_s(samples):
    """Width of the transient at half its peak excursion, seconds.

    The crossings are interpolated between samples rather than snapped to the
    nearest one, so the width does not carry a sample interval of bias at
    each end.
    """
    pulse = validate_pulse(samples)
    peak = max((volts for _, volts in pulse), key=lambda v: (abs(v), v))
    if abs(peak) <= VOLTAGE_TOL:
        raise ValueError("transient never leaves zero; width is undefined")
    sign = 1.0 if peak > 0.0 else -1.0
    threshold = abs(peak) * 0.5
    trace = [(t, v * sign) for t, v in pulse]
    crossings = []
    for (t0, v0), (t1, v1) in zip(trace, trace[1:]):
        if (v0 < threshold <= v1) or (v1 < threshold <= v0):
            share = (threshold - v0) / (v1 - v0)
            crossings.append(t0 + (t1 - t0) * share)
    if len(crossings) < 2:
        raise ValueError(
            "transient does not cross half amplitude twice; the capture window "
            "does not hold the whole pulse"
        )
    return crossings[-1] - crossings[0]


def volt_second_area(samples):
    """Area the transient carries, volt-seconds, taken on its magnitude."""
    pulse = validate_pulse(samples)
    total = 0.0
    for (t0, v0), (t1, v1) in zip(pulse, pulse[1:]):
        total += (abs(v0) + abs(v1)) * 0.5 * (t1 - t0)
    return total


def applied_stress_ratio(applied_peak_v, specified_peak_v):
    """How much of the specified transient level was actually applied."""
    applied = abs(_scalar(applied_peak_v, "applied_peak_v"))
    specified = _scalar(specified_peak_v, "specified_peak_v")
    if specified <= 0.0:
        raise ValueError("specified_peak_v must be > 0, got %g" % specified)
    return applied / specified


def applied_stress_margin_db(applied_peak_v, specified_peak_v):
    """Applied level relative to the specified level, decibels."""
    ratio = applied_stress_ratio(applied_peak_v, specified_peak_v)
    if ratio <= 0.0:
        raise ValueError("applied_peak_v must be non-zero to form a margin")
    return 20.0 * math.log10(ratio)


def grade_stress(
    applied_peak_v, specified_peak_v, at_level_fraction=DEFAULT_AT_LEVEL_FRACTION
):
    """Categorize the stress one event applied against the specified level."""
    applied = abs(_scalar(applied_peak_v, "applied_peak_v"))
    specified = _scalar(specified_peak_v, "specified_peak_v")
    fraction = _scalar(at_level_fraction, "at_level_fraction")
    if specified <= 0.0:
        raise ValueError("specified_peak_v must be > 0, got %g" % specified)
    if not 0.0 <= fraction < 1.0:
        raise ValueError("at_level_fraction must lie in [0, 1), got %g" % fraction)
    if not at_least(applied, specified):
        return STRESS_SHORT
    if applied <= specified * (1.0 + fraction):
        return STRESS_AT_LEVEL
    return STRESS_APPLIED


def grade_response(observed, allowed):
    """Categorize the observed behaviour against the allowed category."""
    seen = normalize_performance(observed)
    permitted = normalize_performance(allowed)
    seen_rank = PERFORMANCE_ORDER.index(seen)
    permitted_rank = PERFORMANCE_ORDER.index(permitted)
    if seen_rank > permitted_rank:
        return RESPONSE_REJECTED
    if seen_rank == permitted_rank:
        return RESPONSE_AT_CATEGORY
    return RESPONSE_ACCEPTED


def assess_transient_event(event, spec, at_level_fraction=DEFAULT_AT_LEVEL_FRACTION):
    """Reduce one injected transient event to a graded record."""
    if not isinstance(event, dict):
        raise ValueError("event: record must be a mapping")
    if not isinstance(spec, dict):
        raise ValueError("spec: record must be a mapping")
    for field in ("lead", "samples", "observed"):
        if field not in event:
            raise ValueError("event: missing required field %r" % field)
    lead = normalize_lead(event["lead"])
    pulse = validate_pulse(event["samples"])
    peak = max((volts for _, volts in pulse), key=lambda v: (abs(v), v))
    polarity = pulse_polarity(pulse)
    declared = event.get("polarity")
    if declared is not None and normalize_polarity(declared) != polarity:
        raise ValueError(
            "event: declared polarity %r does not match the record, which is %s"
            % (declared, polarity)
        )
    specified = _number(spec, "specified_peak_v", "spec")
    allowed = spec.get("allowed_performance", PERFORMANCE_SELF_RECOVERING)
    width = half_amplitude_width_s(pulse)
    record = {
        "lead": lead,
        "polarity": polarity,
        "peak_v": peak,
        "specified_peak_v": specified,
        "stress_ratio": applied_stress_ratio(peak, specified),
        "stress_margin_db": applied_stress_margin_db(peak, specified),
        "half_amplitude_width_s": width,
        "volt_second_area": volt_second_area(pulse),
        "stress_grade": grade_stress(peak, specified, at_level_fraction),
        "response_grade": grade_response(event["observed"], allowed),
        "observed": normalize_performance(event["observed"]),
        "allowed_performance": normalize_performance(allowed),
    }
    required_width = spec.get("specified_width_s")
    if required_width is not None:
        wanted = _scalar(required_width, "spec.specified_width_s")
        if wanted <= 0.0:
            raise ValueError("spec: specified_width_s must be > 0, got %g" % wanted)
        record["specified_width_s"] = wanted
        record["width_ok"] = at_least(width, wanted, tol=wanted * REL_TOL)
    else:
        record["specified_width_s"] = None
        record["width_ok"] = True
    return record


def assess_power_lead_transient_purpose(
    events,
    spec,
    required_polarities=POLARITIES,
    required_repeats=1,
    at_level_fraction=DEFAULT_AT_LEVEL_FRACTION,
):
    """Full clause 5.4.9.1 judgement on a power-lead transient campaign."""
    if not isinstance(events, (list, tuple)) or len(events) == 0:
        raise ValueError("events: at least one transient event is required")
    if isinstance(required_repeats, bool) or not isinstance(required_repeats, int):
        raise ValueError(
            "required_repeats must be a whole number, got %r" % (required_repeats,)
        )
    if required_repeats < 1:
        raise ValueError("required_repeats must be >= 1, got %d" % required_repeats)
    if not isinstance(required_polarities, (list, tuple)) or not required_polarities:
        raise ValueError("required_polarities: at least one polarity is required")
    wanted = [normalize_polarity(p) for p in required_polarities]

    graded = [assess_transient_event(event, spec, at_level_fraction) for event in events]

    counts = {}
    for record in graded:
        counts[(record["lead"], record["polarity"])] = (
            counts.get((record["lead"], record["polarity"]), 0) + 1
        )

    per_lead = {}
    for record in graded:
        worst = per_lead.get(record["lead"])
        if worst is None or _severity(record) > _severity(worst):
            per_lead[record["lead"]] = record

    governing = max(
        per_lead.values(), key=lambda rec: (_severity(rec), rec["lead"])
    )

    findings = []
    limitations = []
    for lead in sorted({rec["lead"] for rec in graded}):
        for polarity in wanted:
            applied = counts.get((lead, polarity), 0)
            if applied == 0:
                findings.append(
                    "lead %s never saw a %s transient" % (lead, polarity)
                )
            elif applied < required_repeats:
                findings.append(
                    "lead %s saw %d %s transients, short of the %d required"
                    % (lead, applied, polarity, required_repeats)
                )
    for record in graded:
        if record["stress_grade"] == STRESS_SHORT:
            findings.append(
                "lead %s %s pulse reached %.1f V, under the %.1f V specified, so it "
                "demonstrates nothing"
                % (
                    record["lead"],
                    record["polarity"],
                    abs(record["peak_v"]),
                    record["specified_peak_v"],
                )
            )
        elif record["stress_grade"] == STRESS_AT_LEVEL:
            limitations.append(
                "lead %s %s pulse sits on the %.1f V specified level"
                % (record["lead"], record["polarity"], record["specified_peak_v"])
            )
        if record["response_grade"] == RESPONSE_REJECTED:
            findings.append(
                "lead %s %s pulse produced %s, past the allowed %s"
                % (
                    record["lead"],
                    record["polarity"],
                    record["observed"],
                    record["allowed_performance"],
                )
            )
        elif record["response_grade"] == RESPONSE_AT_CATEGORY:
            limitations.append(
                "lead %s %s pulse reached the allowed %s with nothing in hand"
                % (record["lead"], record["polarity"], record["allowed_performance"])
            )
        if not record["width_ok"]:
            findings.append(
                "lead %s %s pulse was %.3g s wide at half amplitude, under the %.3g s "
                "specified"
                % (
                    record["lead"],
                    record["polarity"],
                    record["half_amplitude_width_s"],
                    record["specified_width_s"],
                )
            )

    return {
        "events": graded,
        "applied_counts": counts,
        "worst_per_lead": per_lead,
        "governing_lead": governing["lead"],
        "governing_polarity": governing["polarity"],
        "required_polarities": wanted,
        "required_repeats": required_repeats,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_DEMONSTRATED if not findings else VERDICT_NOT_DEMONSTRATED,
    }


def _severity(record):
    """Rank a graded event so the worst one on a lead can be picked out."""
    response_rank = PERFORMANCE_ORDER.index(record["observed"])
    stress_rank = 1 if record["stress_grade"] == STRESS_SHORT else 0
    width_rank = 0 if record["width_ok"] else 1
    return (response_rank, stress_rank, width_rank, -record["stress_ratio"])

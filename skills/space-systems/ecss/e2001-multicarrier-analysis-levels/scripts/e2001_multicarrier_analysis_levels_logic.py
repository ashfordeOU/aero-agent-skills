#!/usr/bin/env python3
"""Multicarrier multipactor analysis levels (ECSS-E-ST-20-01C clause 4.7.2.1).

Deterministic, offline, stdlib-only implementation of the rule that picks
between the two design analysis levels available for a multicarrier multipactor
assessment:

* the first level -- a worst-case envelope check, where every carrier is taken
  to add in phase and the resulting peak envelope power, raised by the required
  margin, is compared against the single-carrier multipactor threshold;
* the second level -- a time-resolved envelope check, where an excursion above
  the margined threshold is tolerated only while it is shorter than the time an
  electron needs to make the agreed number of gap crossings.

The first level is sufficient whenever it closes. The second level is required
only when the worst-case check fails, and it needs inputs the first level never
asks for: the carrier frequencies, the resonance order and the number of gap
crossings the project credits. The clause is the anchor for the procedure, not
a reproduction of the standard's text.
"""

import cmath
import math

# Representation-error absorption only; never a relaxation of a limit.
POWER_REL_TOLERANCE = 1e-12
TIME_REL_TOLERANCE = 1e-12

MIN_CARRIERS = 2
DEFAULT_GAP_CROSSINGS = 20
DEFAULT_RESONANCE_ORDER = 1
DEFAULT_ENVELOPE_SAMPLES = 4096
# The sampled envelope must resolve the fastest beat in the carrier plan; below
# this many samples per fastest beat cycle the dwell time is not trustworthy.
MIN_SAMPLES_PER_BEAT = 16

LEVEL_ONE = "level-1"
LEVEL_TWO = "level-2"


def _check_positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return value


def validate_carriers(carriers):
    """Return the carrier plan as a frequency-sorted tuple of (hertz, watts)."""
    if not isinstance(carriers, (list, tuple)):
        raise ValueError("carriers must be a list of carrier records")
    if len(carriers) < MIN_CARRIERS:
        raise ValueError(
            "a multicarrier assessment needs at least %d carriers, got %d"
            % (MIN_CARRIERS, len(carriers))
        )
    plan = []
    for index, carrier in enumerate(carriers):
        if isinstance(carrier, dict):
            for key in ("frequency_hz", "power_w"):
                if key not in carrier:
                    raise ValueError("carrier[%d] missing required key %r" % (index, key))
            raw_freq = carrier["frequency_hz"]
            raw_power = carrier["power_w"]
        elif isinstance(carrier, (tuple, list)) and len(carrier) == 2:
            # Accept an already-normalized (hertz, watts) pair so the module can
            # re-validate its own output without rebuilding the mappings.
            raw_freq, raw_power = carrier
        else:
            raise ValueError(
                "carrier[%d] must be a mapping or a (hertz, watts) pair, got %r"
                % (index, carrier)
            )
        freq = _check_positive(raw_freq, "carrier[%d] frequency_hz" % index)
        power = _check_positive(raw_power, "carrier[%d] power_w" % index)
        plan.append((freq, power))
    plan.sort()
    for i in range(1, len(plan)):
        if plan[i][0] == plan[i - 1][0]:
            raise ValueError("two carriers share the frequency %r Hz" % plan[i][0])
    return tuple(plan)


def peak_envelope_power_w(carriers):
    """Return the coherent peak envelope power of the carrier plan in watts."""
    plan = validate_carriers(carriers)
    amplitude = sum(math.sqrt(power) for _, power in plan)
    return amplitude * amplitude


def average_power_w(carriers):
    """Return the summed average power of the carrier plan in watts."""
    return float(sum(power for _, power in validate_carriers(carriers)))


def fundamental_beat_hz(carriers):
    """Return the fundamental beat frequency of the carrier plan in hertz.

    The envelope repeats at the greatest common divisor of the carrier
    frequency offsets, which is the carrier spacing for an evenly spaced plan
    and a coarser value for an irregular one. Offsets are resolved to whole
    hertz; a sub-hertz offset is rejected rather than silently rounded away.
    """
    plan = validate_carriers(carriers)
    base = plan[0][0]
    offsets = []
    for freq, _ in plan[1:]:
        diff = freq - base
        rounded = int(round(diff))
        if rounded <= 0:
            raise ValueError(
                "carrier offset %r Hz is below the one-hertz resolution of the "
                "beat calculation" % diff
            )
        offsets.append(rounded)
    beat = offsets[0]
    for offset in offsets[1:]:
        beat = math.gcd(beat, offset)
    return float(beat)


def envelope_period_s(carriers):
    """Return the repetition period of the multicarrier envelope in seconds."""
    return 1.0 / fundamental_beat_hz(carriers)


def gap_crossing_time_s(frequency_hz, order=DEFAULT_RESONANCE_ORDER):
    """Return the time an electron takes to cross the gap once, in seconds."""
    freq = _check_positive(frequency_hz, "frequency_hz")
    if isinstance(order, bool) or not isinstance(order, int):
        raise ValueError("order must be an integer, got %r" % (order,))
    if order < 1:
        raise ValueError("order must be at least 1, got %d" % order)
    if order % 2 == 0:
        raise ValueError("resonance order must be odd, got %d" % order)
    return order / (2.0 * freq)


def gap_crossing_window_s(
    frequency_hz, crossings=DEFAULT_GAP_CROSSINGS, order=DEFAULT_RESONANCE_ORDER
):
    """Return the longest excursion the gap-crossing rule tolerates, in seconds."""
    if isinstance(crossings, bool) or not isinstance(crossings, int):
        raise ValueError("crossings must be an integer, got %r" % (crossings,))
    if crossings < 1:
        raise ValueError("crossings must be at least 1, got %d" % crossings)
    return crossings * gap_crossing_time_s(frequency_hz, order=order)


def margined_threshold_w(threshold_w, margin_db):
    """Return the power level the envelope must respect once the margin is paid."""
    threshold = _check_positive(threshold_w, "threshold_w")
    if isinstance(margin_db, bool) or not isinstance(margin_db, (int, float)):
        raise ValueError("margin_db must be a number, got %r" % (margin_db,))
    margin = float(margin_db)
    if not math.isfinite(margin):
        raise ValueError("margin_db must be finite, got %r" % (margin_db,))
    if margin < 0.0:
        raise ValueError("margin_db must not be negative, got %r" % (margin_db,))
    return threshold / (10.0 ** (margin / 10.0))


def envelope_power_samples(carriers, samples=DEFAULT_ENVELOPE_SAMPLES):
    """Return one period of the envelope power, sampled uniformly, in watts."""
    plan = validate_carriers(carriers)
    if isinstance(samples, bool) or not isinstance(samples, int):
        raise ValueError("samples must be an integer, got %r" % (samples,))
    if samples < MIN_SAMPLES_PER_BEAT:
        raise ValueError(
            "samples must be at least %d, got %d" % (MIN_SAMPLES_PER_BEAT, samples)
        )
    beat = fundamental_beat_hz(carriers)
    period = 1.0 / beat
    base = plan[0][0]
    fastest = max(freq - base for freq, _ in plan)
    cycles = fastest / beat
    if samples < MIN_SAMPLES_PER_BEAT * cycles:
        raise ValueError(
            "sample count %d cannot resolve %g beat cycles per envelope period; "
            "supply at least %d samples"
            % (samples, cycles, int(math.ceil(MIN_SAMPLES_PER_BEAT * cycles)))
        )
    amplitudes = [(math.sqrt(power), freq - base) for freq, power in plan]
    out = []
    for index in range(samples):
        time_s = period * index / samples
        total = 0j
        for amplitude, offset in amplitudes:
            total += amplitude * cmath.exp(2j * math.pi * offset * time_s)
        out.append(abs(total) ** 2)
    return out


def longest_dwell_above_s(carriers, level_w, samples=DEFAULT_ENVELOPE_SAMPLES):
    """Return the longest contiguous time the envelope stays at or above a level."""
    level = _check_positive(level_w, "level_w")
    powers = envelope_power_samples(carriers, samples=samples)
    period = envelope_period_s(carriers)
    step = period / len(powers)
    above = [p >= level or math.isclose(p, level, rel_tol=POWER_REL_TOLERANCE)
             for p in powers]
    if not any(above):
        return 0.0
    if all(above):
        return period
    doubled = above + above
    best = run = 0
    for flag in doubled:
        run = run + 1 if flag else 0
        if run > best:
            best = run
    return min(best, len(powers)) * step


def level_one_check(carriers, threshold_w, margin_db):
    """Run the worst-case envelope check that the first analysis level makes."""
    peak = peak_envelope_power_w(carriers)
    allowed = margined_threshold_w(threshold_w, margin_db)
    within = peak <= allowed or math.isclose(peak, allowed, rel_tol=POWER_REL_TOLERANCE)
    return {
        "peak_envelope_power_w": peak,
        "allowed_power_w": allowed,
        "exceedance_w": 0.0 if within else peak - allowed,
        "within_allowance": within,
    }


def select_analysis_level(carriers, threshold_w, margin_db):
    """Return the analysis level clause 4.7.2.1 requires for this case."""
    check = level_one_check(carriers, threshold_w, margin_db)
    if check["within_allowance"]:
        return {
            "level": LEVEL_ONE,
            "reason": "the coherent peak envelope stays within the margined "
                      "threshold, so the worst-case level closes the case",
            "level_one": check,
        }
    return {
        "level": LEVEL_TWO,
        "reason": "the coherent peak envelope exceeds the margined threshold by "
                  "%.3f W, so the time-resolved level is required" % check["exceedance_w"],
        "level_one": check,
    }


def level_two_check(
    carriers,
    threshold_w,
    margin_db,
    crossings=DEFAULT_GAP_CROSSINGS,
    order=DEFAULT_RESONANCE_ORDER,
    samples=DEFAULT_ENVELOPE_SAMPLES,
):
    """Run the time-resolved gap-crossing check of the second analysis level."""
    plan = validate_carriers(carriers)
    allowed = margined_threshold_w(threshold_w, margin_db)
    dwell = longest_dwell_above_s(plan, allowed, samples=samples)
    # The shortest tolerated excursion comes from the highest carrier, whose gap
    # crossings are the quickest; taking it keeps the check conservative.
    highest = max(freq for freq, _ in plan)
    window = gap_crossing_window_s(highest, crossings=crossings, order=order)
    within = dwell <= window or math.isclose(dwell, window, rel_tol=TIME_REL_TOLERANCE)
    return {
        "allowed_power_w": allowed,
        "longest_dwell_s": dwell,
        "gap_crossing_window_s": window,
        "reference_frequency_hz": highest,
        "envelope_period_s": envelope_period_s(plan),
        "within_allowance": within,
    }


def assess_multicarrier_case(case):
    """Select the analysis level and run it, returning one closed verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for key in ("id", "carriers", "single_carrier_threshold_w", "margin_db"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    identifier = case["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("case id must be a non-empty string, got %r" % (identifier,))
    carriers = validate_carriers(case["carriers"])
    threshold = case["single_carrier_threshold_w"]
    margin = case["margin_db"]
    selection = select_analysis_level(carriers, threshold, margin)
    findings = []
    if selection["level"] == LEVEL_ONE:
        return {
            "id": identifier.strip(),
            "level": LEVEL_ONE,
            "reason": selection["reason"],
            "level_one": selection["level_one"],
            "level_two": None,
            "compliant": True,
            "findings": findings,
        }
    crossings = case.get("gap_crossings", DEFAULT_GAP_CROSSINGS)
    order = case.get("resonance_order", DEFAULT_RESONANCE_ORDER)
    samples = case.get("envelope_samples", DEFAULT_ENVELOPE_SAMPLES)
    detail = level_two_check(
        carriers, threshold, margin, crossings=crossings, order=order, samples=samples
    )
    if not detail["within_allowance"]:
        findings.append(
            "envelope stays above the margined threshold for %.3e s, longer than "
            "the %.3e s the gap-crossing rule tolerates"
            % (detail["longest_dwell_s"], detail["gap_crossing_window_s"])
        )
    return {
        "id": identifier.strip(),
        "level": LEVEL_TWO,
        "reason": selection["reason"],
        "level_one": selection["level_one"],
        "level_two": detail,
        "compliant": detail["within_allowance"],
        "findings": findings,
    }


def summarize_cases(cases):
    """Aggregate assessed cases into a level-selection overview."""
    if not isinstance(cases, (list, tuple)) or len(cases) == 0:
        raise ValueError("cases must be a non-empty list")
    results = []
    seen = set()
    for case in cases:
        result = assess_multicarrier_case(case)
        if result["id"] in seen:
            raise ValueError("duplicate case id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "cases": len(results),
        "results": results,
        "level_one_ids": [r["id"] for r in results if r["level"] == LEVEL_ONE],
        "level_two_ids": [r["id"] for r in results if r["level"] == LEVEL_TWO],
        "open_ids": [r["id"] for r in results if not r["compliant"]],
        "all_compliant": all(r["compliant"] for r in results),
    }

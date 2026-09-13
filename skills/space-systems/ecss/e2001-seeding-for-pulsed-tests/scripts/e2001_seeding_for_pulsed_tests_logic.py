#!/usr/bin/env python3
"""Electron seeding under pulsed drive (ECSS-E-ST-20-01C clause 6.5.3).

Deterministic, offline, stdlib-only support logic for the seeding arrangement
of a multipactor run driven with a pulsed carrier.  Paraphrased engineering
procedure only -- no standard text is reproduced.

Chain implemented here:

1. Derive the drive duty-cycle and the number of pulses held at each step,
   and confirm the drive is still in the pulsed regime.
2. Resolve the seed source: a free-running emitter, of which only the share
   arriving inside an on-time is useful, or a burst source gated to each
   pulse.
3. Count the seed electrons available inside one radio-frequency on-time and
   accumulate the initiation probability over the pulse train.
4. Check the gate advance of a synchronized burst against the electron
   transit time and the off-time it has to fit into.
5. Confirm each pulse spans enough carrier cycles for the avalanche to grow
   from one electron to a detectable population, and that the off-time
   clears residual charge between pulses.
6. Aggregate findings; the arrangement is acceptable only when none remain.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

SYNC_FREE_RUNNING = "free-running"
SYNC_PULSE_LOCKED = "pulse-synchronized"
SYNCHRONIZATION_MODES = (SYNC_FREE_RUNNING, SYNC_PULSE_LOCKED)

DEFAULT_CONFIDENCE = 0.99
DEFAULT_MAX_DUTY = 0.5


# --------------------------------------------------------------------------
# numeric guards -- absorb representation error at a limit, never widen it
# --------------------------------------------------------------------------
def _at_least(value, limit):
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _at_most(value, limit):
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


# --------------------------------------------------------------------------
# input validation
# --------------------------------------------------------------------------
def _require_mapping(obj, label):
    if not isinstance(obj, dict):
        raise ValueError("%s must be a mapping, got %s" % (label, type(obj).__name__))
    return obj


def _scalar(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % name)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % name)
    return value


def _number(mapping, key, label):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    return _scalar(mapping[key], "%s field '%s'" % (label, key))


def _positive(mapping, key, label):
    value = _number(mapping, key, label)
    if value <= 0.0:
        raise ValueError("%s field '%s' must be greater than zero" % (label, key))
    return value


def _non_negative(mapping, key, label):
    value = _number(mapping, key, label)
    if value < 0.0:
        raise ValueError("%s field '%s' cannot be negative" % (label, key))
    return value


def _text(mapping, key, label, allowed=None):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s field '%s' must be a non-empty string" % (label, key))
    value = value.strip().lower()
    if allowed is not None and value not in allowed:
        raise ValueError("%s field '%s' holds an unrecognised value '%s'" % (label, key, value))
    return value


# --------------------------------------------------------------------------
# step 1 -- pulse-train geometry
# --------------------------------------------------------------------------
def duty_cycle(pulse_width_s, pulse_period_s):
    """Share of the pulse period during which the carrier is applied."""
    pulse_width_s = _scalar(pulse_width_s, "pulse width")
    pulse_period_s = _scalar(pulse_period_s, "pulse period")
    if pulse_width_s <= 0.0:
        raise ValueError("pulse width must be greater than zero")
    if pulse_period_s <= 0.0:
        raise ValueError("pulse period must be greater than zero")
    if pulse_width_s > pulse_period_s and not math.isclose(
        pulse_width_s, pulse_period_s, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError("pulse width cannot exceed the pulse period")
    return min(pulse_width_s / pulse_period_s, 1.0)


def pulses_in_dwell(dwell_s, pulse_period_s):
    """Whole pulses delivered while a drive step is held."""
    dwell_s = _scalar(dwell_s, "dwell")
    pulse_period_s = _scalar(pulse_period_s, "pulse period")
    if dwell_s <= 0.0:
        raise ValueError("dwell must be greater than zero")
    if pulse_period_s <= 0.0:
        raise ValueError("pulse period must be greater than zero")
    count = int(math.floor(dwell_s / pulse_period_s))
    if count < 1:
        raise ValueError("dwell is shorter than one pulse period")
    return count


def cycles_in_pulse(pulse_width_s, carrier_frequency_hz):
    """Carrier cycles contained in one radio-frequency on-time."""
    pulse_width_s = _scalar(pulse_width_s, "pulse width")
    carrier_frequency_hz = _scalar(carrier_frequency_hz, "carrier frequency")
    if pulse_width_s <= 0.0:
        raise ValueError("pulse width must be greater than zero")
    if carrier_frequency_hz <= 0.0:
        raise ValueError("carrier frequency must be greater than zero")
    return pulse_width_s * carrier_frequency_hz


def build_up_cycles_required(growth_per_cycle, detectable_population):
    """Carrier cycles needed to grow one electron to a detectable population."""
    growth_per_cycle = _scalar(growth_per_cycle, "growth per cycle")
    detectable_population = _scalar(detectable_population, "detectable population")
    if growth_per_cycle <= 1.0:
        raise ValueError("growth per cycle must exceed unity for an avalanche to build")
    if detectable_population <= 1.0:
        raise ValueError("detectable population must exceed a single electron")
    return math.log(detectable_population) / math.log(growth_per_cycle)


# --------------------------------------------------------------------------
# step 2 -- seed source resolution
# --------------------------------------------------------------------------
def categorize_seed_synchronization(source, label="seed source"):
    """Resolve how the seed source is timed relative to the pulse train."""
    _require_mapping(source, label)
    mode = _text(source, "synchronization", label, SYNCHRONIZATION_MODES)
    if mode == SYNC_FREE_RUNNING:
        _positive(source, "delivered_rate_per_s", label)
    else:
        _positive(source, "burst_population", label)
        _non_negative(source, "gate_advance_s", label)
        _positive(source, "electron_transit_s", label)
    return {"synchronization": mode, "gated": mode == SYNC_PULSE_LOCKED}


def seed_electrons_per_pulse(source, pulse_width_s, label="seed source"):
    """Seed electrons available inside one radio-frequency on-time."""
    category = categorize_seed_synchronization(source, label)
    pulse_width_s = _scalar(pulse_width_s, "pulse width")
    if pulse_width_s <= 0.0:
        raise ValueError("pulse width must be greater than zero")
    if category["gated"]:
        return _positive(source, "burst_population", label)
    return _positive(source, "delivered_rate_per_s", label) * pulse_width_s


def synchronization_findings(source, pulse_width_s, pulse_period_s, label="seed source"):
    """Timing findings for a burst source gated to the pulse train."""
    category = categorize_seed_synchronization(source, label)
    if not category["gated"]:
        return []
    width = _scalar(pulse_width_s, "pulse width")
    period = _scalar(pulse_period_s, "pulse period")
    duty_cycle(width, period)
    off_time = period - width
    advance = _non_negative(source, "gate_advance_s", label)
    transit = _positive(source, "electron_transit_s", label)
    findings = []
    if not _at_least(advance, transit):
        findings.append("seed-burst-arrives-after-field-rise")
    if not _at_most(advance, off_time):
        findings.append("seed-burst-launched-inside-preceding-pulse")
    return findings


# --------------------------------------------------------------------------
# step 3 -- initiation statistics over the pulse train
# --------------------------------------------------------------------------
def cumulative_initiation_probability(electrons_per_pulse, pulse_count):
    """Probability that the train delivers a starting electron at least once."""
    electrons_per_pulse = _scalar(electrons_per_pulse, "seed electrons per pulse")
    if electrons_per_pulse <= 0.0:
        raise ValueError("seed electrons per pulse must be greater than zero")
    if isinstance(pulse_count, bool) or not isinstance(pulse_count, int):
        raise ValueError("pulse count must be a whole number of pulses")
    if pulse_count < 1:
        raise ValueError("pulse count must be at least one")
    return 1.0 - math.exp(-electrons_per_pulse * pulse_count)


def required_pulse_count(electrons_per_pulse, confidence=DEFAULT_CONFIDENCE):
    """Whole pulses needed to reach the stated seeding confidence."""
    electrons_per_pulse = _scalar(electrons_per_pulse, "seed electrons per pulse")
    if electrons_per_pulse <= 0.0:
        raise ValueError("seed electrons per pulse must be greater than zero")
    confidence = _scalar(confidence, "confidence")
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    exact = -math.log(1.0 - confidence) / electrons_per_pulse
    whole = int(math.ceil(exact))
    if math.isclose(float(whole - 1), exact, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        whole -= 1
    return max(whole, 1)


# --------------------------------------------------------------------------
# step 4 -- per-step assessment
# --------------------------------------------------------------------------
def evaluate_pulsed_step(
    step,
    source,
    confidence=DEFAULT_CONFIDENCE,
    residual_clearing_s=0.0,
    max_duty=DEFAULT_MAX_DUTY,
    label="drive step",
):
    """Score one pulsed drive step against the seeding and build-up rules."""
    _require_mapping(step, label)
    step_id = _text(step, "step_id", label)
    width = _positive(step, "pulse_width_s", label)
    period = _positive(step, "pulse_period_s", label)
    dwell = _positive(step, "dwell_s", label)
    frequency = _positive(step, "carrier_frequency_hz", label)
    growth = _positive(step, "growth_per_cycle", label)
    detectable = _positive(step, "detectable_population", label)
    residual_clearing_s = _scalar(residual_clearing_s, "residual clearing time")
    if residual_clearing_s < 0.0:
        raise ValueError("residual clearing time cannot be negative")
    max_duty = _scalar(max_duty, "maximum duty")
    if max_duty <= 0.0 or max_duty > 1.0:
        raise ValueError("maximum duty must lie in (0, 1]")
    duty = duty_cycle(width, period)
    count = pulses_in_dwell(dwell, period)
    per_pulse = seed_electrons_per_pulse(source, width)
    probability = cumulative_initiation_probability(per_pulse, count)
    needed = required_pulse_count(per_pulse, confidence)
    cycles = cycles_in_pulse(width, frequency)
    cycles_needed = build_up_cycles_required(growth, detectable)
    off_time = period - width
    findings = list(synchronization_findings(source, width, period))
    if not _at_least(float(count), float(needed)):
        findings.append("seeding-confidence-not-reached")
    if not _at_least(cycles, cycles_needed):
        findings.append("pulse-too-short-for-avalanche-build-up")
    if not _at_least(off_time, residual_clearing_s):
        findings.append("off-time-short-of-residual-clearing")
    if not _at_most(duty, max_duty):
        findings.append("drive-duty-outside-pulsed-regime")
    return {
        "step_id": step_id,
        "duty_cycle": duty,
        "pulse_count": count,
        "required_pulse_count": needed,
        "seed_electrons_per_pulse": per_pulse,
        "initiation_probability": probability,
        "carrier_cycles_per_pulse": cycles,
        "required_build_up_cycles": cycles_needed,
        "off_time_s": off_time,
        "findings": findings,
        "sufficient": not findings,
    }


def assess_pulsed_seeding(plan):
    """Assess the seeding arrangement of one pulsed multipactor run."""
    _require_mapping(plan, "plan")
    source = plan.get("source")
    _require_mapping(source, "seed source")
    category = categorize_seed_synchronization(source)
    confidence = plan.get("confidence", DEFAULT_CONFIDENCE)
    residual = plan.get("residual_clearing_s", 0.0)
    max_duty = plan.get("max_duty", DEFAULT_MAX_DUTY)
    steps = plan.get("steps")
    if not isinstance(steps, (list, tuple)):
        raise ValueError("plan field 'steps' must be a list of drive steps")
    if not steps:
        raise ValueError("plan must declare at least one pulsed drive step")
    results = []
    findings = []
    seen = set()
    for step in steps:
        result = evaluate_pulsed_step(step, source, confidence, residual, max_duty)
        if result["step_id"] in seen:
            raise ValueError("duplicate drive step identifier '%s'" % result["step_id"])
        seen.add(result["step_id"])
        results.append(result)
        for finding in result["findings"]:
            findings.append("%s:%s" % (result["step_id"], finding))
    return {
        "synchronization": category["synchronization"],
        "confidence": confidence,
        "steps": results,
        "step_count": len(results),
        "findings": findings,
        "compliant": not findings,
    }

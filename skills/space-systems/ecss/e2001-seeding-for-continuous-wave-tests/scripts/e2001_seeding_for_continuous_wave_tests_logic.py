#!/usr/bin/env python3
"""Electron seeding under continuous-wave drive (ECSS-E-ST-20-01C clause 6.5.2).

Deterministic, offline, stdlib-only support logic for the seeding arrangement
of a multipactor run driven with an uninterrupted carrier.  Paraphrased
engineering procedure only -- no standard text is reproduced.

Chain implemented here:

1. Categorize the seed source and its emission mode (continuously emitting,
   or repetitively pulsed with an emission duty below unity).
2. Decay-correct the emission of a radioactive source to the run date.
3. Reduce the emission to the seed-electron rate actually delivered into the
   gap through the transport and capture fractions.
4. Convert that rate into a Poisson initiation probability over the dwell
   held at each drive step, and into the dwell the stated seeding confidence
   requires.
5. Bound the accumulated seed-electron fluence so the seed itself does not
   over-irradiate the article.
6. Aggregate findings; the arrangement is acceptable only when none remain.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

CONTINUOUS_SOURCES = ("beta-emitter", "ultraviolet-lamp", "electron-gun-dc")
PULSED_SOURCES = ("electron-gun-pulsed",)
DECAYING_SOURCES = ("beta-emitter",)
SEED_SOURCE_KINDS = CONTINUOUS_SOURCES + PULSED_SOURCES

MODE_CONTINUOUS = "continuous-emission"
MODE_REPETITIVE = "repetitively-pulsed"

DEFAULT_CONFIDENCE = 0.99


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


def _number(mapping, key, label):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s field '%s' must be a real number" % (label, key))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s field '%s' must be finite" % (label, key))
    return value


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


def _fraction(mapping, key, label):
    value = _number(mapping, key, label)
    if value <= 0.0 or value > 1.0:
        raise ValueError("%s field '%s' must lie in (0, 1]" % (label, key))
    return value


def _flag(mapping, key, label):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if not isinstance(value, bool):
        raise ValueError("%s field '%s' must be true or false" % (label, key))
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
# step 1 -- seed source category
# --------------------------------------------------------------------------
def categorize_seed_source(source, label="seed source"):
    """Return the emission mode and duty of a seed source.

    A continuously emitting source delivers electrons at every instant of the
    dwell, so its emission duty is unity.  A repetitively pulsed source emits
    only during its own bursts and must declare the duty that derates its
    average delivery.
    """
    _require_mapping(source, label)
    kind = _text(source, "kind", label, SEED_SOURCE_KINDS)
    if kind in PULSED_SOURCES:
        duty = _fraction(source, "emission_duty", label)
        mode = MODE_REPETITIVE
    else:
        mode = MODE_CONTINUOUS
        duty = 1.0
        if "emission_duty" in source:
            declared = _fraction(source, "emission_duty", label)
            if not math.isclose(declared, 1.0, rel_tol=REL_TOL, abs_tol=ABS_TOL):
                raise ValueError(
                    "%s of kind '%s' emits continuously and cannot declare a duty below unity"
                    % (label, kind)
                )
    return {
        "kind": kind,
        "emission_mode": mode,
        "emission_duty": duty,
        "decaying": kind in DECAYING_SOURCES,
    }


# --------------------------------------------------------------------------
# step 2 -- decay correction of a radioactive source
# --------------------------------------------------------------------------
def decay_corrected_emission(initial_rate_per_s, half_life_days, elapsed_days):
    """Emission rate of a decaying source after an elapsed interval."""
    for name, value in (
        ("initial emission rate", initial_rate_per_s),
        ("half life", half_life_days),
        ("elapsed interval", elapsed_days),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % name)
        if math.isnan(float(value)) or math.isinf(float(value)):
            raise ValueError("%s must be finite" % name)
    initial_rate_per_s = float(initial_rate_per_s)
    half_life_days = float(half_life_days)
    elapsed_days = float(elapsed_days)
    if initial_rate_per_s <= 0.0:
        raise ValueError("initial emission rate must be greater than zero")
    if half_life_days <= 0.0:
        raise ValueError("half life must be greater than zero")
    if elapsed_days < 0.0:
        raise ValueError("elapsed interval cannot be negative")
    return initial_rate_per_s * math.pow(2.0, -elapsed_days / half_life_days)


# --------------------------------------------------------------------------
# step 3 -- seed-electron rate delivered into the gap
# --------------------------------------------------------------------------
def effective_seed_rate(source, label="seed source"):
    """Seed electrons per second actually entering the gap volume."""
    category = categorize_seed_source(source, label)
    emission = _positive(source, "emission_rate_per_s", label)
    if category["decaying"]:
        half_life = _positive(source, "half_life_days", label)
        elapsed = _non_negative(source, "elapsed_days", label)
        emission = decay_corrected_emission(emission, half_life, elapsed)
    transport = _fraction(source, "transport_fraction", label)
    capture = _fraction(source, "gap_capture_fraction", label)
    return emission * transport * capture * category["emission_duty"]


def mean_seed_interval(rate_per_s):
    """Average wait between seed electrons entering the gap."""
    if isinstance(rate_per_s, bool) or not isinstance(rate_per_s, (int, float)):
        raise ValueError("seed rate must be a real number")
    rate_per_s = float(rate_per_s)
    if math.isnan(rate_per_s) or math.isinf(rate_per_s):
        raise ValueError("seed rate must be finite")
    if rate_per_s <= 0.0:
        raise ValueError("seed rate must be greater than zero")
    return 1.0 / rate_per_s


# --------------------------------------------------------------------------
# step 4 -- initiation probability over a dwell
# --------------------------------------------------------------------------
def initiation_probability(rate_per_s, dwell_s):
    """Probability that at least one seed electron enters during the dwell."""
    interval = mean_seed_interval(rate_per_s)
    if isinstance(dwell_s, bool) or not isinstance(dwell_s, (int, float)):
        raise ValueError("dwell must be a real number")
    dwell_s = float(dwell_s)
    if math.isnan(dwell_s) or math.isinf(dwell_s):
        raise ValueError("dwell must be finite")
    if dwell_s <= 0.0:
        raise ValueError("dwell must be greater than zero")
    return 1.0 - math.exp(-dwell_s / interval)


def required_dwell(rate_per_s, confidence=DEFAULT_CONFIDENCE):
    """Dwell needed before a seed electron is present at the stated confidence."""
    interval = mean_seed_interval(rate_per_s)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be a real number")
    confidence = float(confidence)
    if math.isnan(confidence) or math.isinf(confidence):
        raise ValueError("confidence must be finite")
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    return -math.log(1.0 - confidence) * interval


def evaluate_drive_step(step, rate_per_s, confidence=DEFAULT_CONFIDENCE, label="drive step"):
    """Score the dwell held at one drive step against the seeding confidence."""
    _require_mapping(step, label)
    step_id = _text(step, "step_id", label)
    forward_power_w = _positive(step, "forward_power_w", label)
    dwell_s = _positive(step, "dwell_s", label)
    needed = required_dwell(rate_per_s, confidence)
    probability = initiation_probability(rate_per_s, dwell_s)
    sufficient = _at_least(dwell_s, needed)
    findings = [] if sufficient else ["seeding-confidence-not-reached"]
    return {
        "step_id": step_id,
        "forward_power_w": forward_power_w,
        "dwell_s": dwell_s,
        "required_dwell_s": needed,
        "initiation_probability": probability,
        "sufficient": sufficient,
        "findings": findings,
    }


# --------------------------------------------------------------------------
# step 5 -- accumulated seed-electron fluence
# --------------------------------------------------------------------------
def seed_electron_fluence(rate_per_s, gap_area_cm2, exposure_s):
    """Seed electrons per unit gap area accumulated over an exposure."""
    mean_seed_interval(rate_per_s)
    for name, value in (("gap area", gap_area_cm2), ("exposure", exposure_s)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % name)
        if math.isnan(float(value)) or math.isinf(float(value)):
            raise ValueError("%s must be finite" % name)
        if float(value) <= 0.0:
            raise ValueError("%s must be greater than zero" % name)
    return float(rate_per_s) * float(exposure_s) / float(gap_area_cm2)


# --------------------------------------------------------------------------
# step 6 -- whole-run assessment
# --------------------------------------------------------------------------
def assess_cw_seeding(plan):
    """Assess the seeding arrangement of one continuous-wave multipactor run."""
    _require_mapping(plan, "plan")
    source = plan.get("source")
    _require_mapping(source, "seed source")
    rate = effective_seed_rate(source)
    confidence = plan.get("confidence", DEFAULT_CONFIDENCE)
    gap_area_cm2 = _positive(plan, "gap_area_cm2", "plan")
    fluence_limit = _positive(plan, "max_fluence_per_cm2", "plan")
    obstructs = _flag(plan, "seed_source_in_drive_path", "plan")
    steps = plan.get("steps")
    if not isinstance(steps, (list, tuple)):
        raise ValueError("plan field 'steps' must be a list of drive steps")
    if not steps:
        raise ValueError("plan must declare at least one drive step")
    results = []
    findings = []
    seen = set()
    previous_power = None
    total_dwell = 0.0
    for step in steps:
        result = evaluate_drive_step(step, rate, confidence)
        if result["step_id"] in seen:
            raise ValueError("duplicate drive step identifier '%s'" % result["step_id"])
        seen.add(result["step_id"])
        if previous_power is not None and result["forward_power_w"] <= previous_power:
            raise ValueError(
                "drive steps must rise in forward power; '%s' does not" % result["step_id"]
            )
        previous_power = result["forward_power_w"]
        total_dwell += result["dwell_s"]
        results.append(result)
        for finding in result["findings"]:
            findings.append("%s:%s" % (result["step_id"], finding))
    fluence = seed_electron_fluence(rate, gap_area_cm2, total_dwell)
    if not _at_most(fluence, fluence_limit):
        findings.append("seed-electron-fluence-exceeds-limit")
    if obstructs:
        findings.append("seed-source-obstructs-drive-path")
    return {
        "seed_rate_per_s": rate,
        "mean_seed_interval_s": mean_seed_interval(rate),
        "confidence": confidence,
        "steps": results,
        "total_dwell_s": total_dwell,
        "fluence_per_cm2": fluence,
        "fluence_limit_per_cm2": fluence_limit,
        "findings": findings,
        "compliant": not findings,
    }

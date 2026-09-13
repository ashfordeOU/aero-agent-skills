#!/usr/bin/env python3
"""Electron seeding for multiple-carrier multipactor runs.

Anchor: ECSS-E-ST-20-01C clause 6.5.4 -- use of an electron seed source
when a multipactor verification is run in a multiple-carrier
environment. Paraphrased into an implementable procedure; no standard
text is reproduced.

Offline, deterministic, stdlib only.
"""

import math

REL_TOL = 1e-12
ABS_TOL = 1e-15

# Deliverable free-electron generation rate ceiling into a gap volume
# (electrons per second) and the RF perturbation current each seeding
# technique typically injects at that ceiling.
SEED_TECHNIQUES = {
    "radioactive-source": {
        "max_rate_per_s": 3.0e6,
        "needs_sight_line": True,
        "typical_perturbation_current_a": 1.0e-12,
    },
    "ultraviolet-illumination": {
        "max_rate_per_s": 1.0e9,
        "needs_sight_line": True,
        "typical_perturbation_current_a": 5.0e-11,
    },
    "electron-gun": {
        "max_rate_per_s": 6.0e12,
        "needs_sight_line": True,
        "typical_perturbation_current_a": 1.0e-6,
    },
}

_SPEC_KEYS = (
    "carrier_powers_w",
    "carrier_spacing_hz",
    "breakdown_threshold_w",
    "gap_volume_cm3",
    "background_rate_per_cm3_s",
    "seeding_confidence",
)


def _ge(value, limit):
    """value >= limit, absorbing float representation error only."""
    return value > limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _le(value, limit):
    """value <= limit, absorbing float representation error only."""
    return value < limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def validate_carrier_powers(carrier_powers_w):
    """Return the carrier level list as floats, or raise ValueError."""
    if not isinstance(carrier_powers_w, (list, tuple)):
        raise ValueError("carrier_powers_w must be a list or tuple")
    if len(carrier_powers_w) < 2:
        raise ValueError(
            "a multiple-carrier environment needs at least 2 carriers, got %d"
            % len(carrier_powers_w)
        )
    out = []
    for i, item in enumerate(carrier_powers_w):
        level = _number(item, "carrier_powers_w[%d]" % i)
        if level <= 0.0:
            raise ValueError("carrier_powers_w[%d] must be > 0, got %r" % (i, level))
        out.append(level)
    return out


def envelope_peak_w(carrier_powers_w):
    """Coherent peak of the carrier envelope: square of the summed amplitudes."""
    levels = validate_carrier_powers(carrier_powers_w)
    amplitude = math.fsum(math.sqrt(p) for p in levels)
    return amplitude * amplitude


def beat_period_s(carrier_spacing_hz):
    """Envelope repetition period for uniformly spaced carriers."""
    spacing = _number(carrier_spacing_hz, "carrier_spacing_hz")
    if spacing <= 0.0:
        raise ValueError("carrier_spacing_hz must be > 0, got %r" % spacing)
    return 1.0 / spacing


def envelope_at_s(carrier_powers_w, carrier_spacing_hz, t_s):
    """Instantaneous envelope level at time t within the beat-period."""
    levels = validate_carrier_powers(carrier_powers_w)
    spacing = _number(carrier_spacing_hz, "carrier_spacing_hz")
    if spacing <= 0.0:
        raise ValueError("carrier_spacing_hz must be > 0, got %r" % spacing)
    t = _number(t_s, "t_s")
    real = 0.0
    imag = 0.0
    for index, level in enumerate(levels):
        phase = 2.0 * math.pi * index * spacing * t
        amplitude = math.sqrt(level)
        real += amplitude * math.cos(phase)
        imag += amplitude * math.sin(phase)
    return real * real + imag * imag


def above_threshold_fraction(
    carrier_powers_w, carrier_spacing_hz, breakdown_threshold_w, samples=2048
):
    """Fraction of one beat-period the envelope holds at or above threshold."""
    threshold = _number(breakdown_threshold_w, "breakdown_threshold_w")
    if threshold <= 0.0:
        raise ValueError("breakdown_threshold_w must be > 0, got %r" % threshold)
    if isinstance(samples, bool) or not isinstance(samples, int):
        raise ValueError("samples must be an int, got %r" % (samples,))
    if samples < 16:
        raise ValueError("samples must be >= 16 to resolve the envelope, got %d" % samples)
    period = beat_period_s(carrier_spacing_hz)
    levels = validate_carrier_powers(carrier_powers_w)
    hits = 0
    for k in range(samples):
        value = envelope_at_s(levels, carrier_spacing_hz, k * period / samples)
        if _ge(value, threshold):
            hits += 1
    return hits / float(samples)


def above_threshold_dwell_s(
    carrier_powers_w, carrier_spacing_hz, breakdown_threshold_w, samples=2048
):
    """Seconds per beat-period spent above the breakdown threshold."""
    fraction = above_threshold_fraction(
        carrier_powers_w, carrier_spacing_hz, breakdown_threshold_w, samples
    )
    return fraction * beat_period_s(carrier_spacing_hz)


def natural_electron_population(gap_volume_cm3, background_rate_per_cm3_s, dwell_s):
    """Expected free electrons from background ionisation during the dwell."""
    volume = _number(gap_volume_cm3, "gap_volume_cm3")
    if volume <= 0.0:
        raise ValueError("gap_volume_cm3 must be > 0, got %r" % volume)
    rate = _number(background_rate_per_cm3_s, "background_rate_per_cm3_s")
    if rate < 0.0:
        raise ValueError("background_rate_per_cm3_s must be >= 0, got %r" % rate)
    dwell = _number(dwell_s, "dwell_s")
    if dwell < 0.0:
        raise ValueError("dwell_s must be >= 0, got %r" % dwell)
    return volume * rate * dwell


def required_population(seeding_confidence):
    """Expected electron count implied by a Poisson presence confidence."""
    confidence = _number(seeding_confidence, "seeding_confidence")
    if not 0.0 < confidence < 1.0:
        raise ValueError("seeding_confidence must lie in (0, 1), got %r" % confidence)
    return -math.log(1.0 - confidence)


def presence_probability(population):
    """Poisson probability that at least one electron is in the gap."""
    lam = _number(population, "population")
    if lam < 0.0:
        raise ValueError("population must be >= 0, got %r" % lam)
    return 1.0 - math.exp(-lam)


def seeding_is_required(natural_population, required_population_value):
    """True when background ionisation alone misses the confidence target."""
    natural = _number(natural_population, "natural_population")
    needed = _number(required_population_value, "required_population_value")
    if natural < 0.0 or needed <= 0.0:
        raise ValueError("populations must be >= 0 and the requirement > 0")
    return not _ge(natural, needed)


def required_seed_rate_per_s(required_population_value, natural_population, dwell_s):
    """Seed electron generation rate that closes the population shortfall."""
    needed = _number(required_population_value, "required_population_value")
    natural = _number(natural_population, "natural_population")
    dwell = _number(dwell_s, "dwell_s")
    if needed <= 0.0:
        raise ValueError("required_population_value must be > 0, got %r" % needed)
    if natural < 0.0:
        raise ValueError("natural_population must be >= 0, got %r" % natural)
    if dwell <= 0.0:
        raise ValueError("dwell_s must be > 0 to size a seed rate, got %r" % dwell)
    deficit = needed - natural
    if _le(deficit, 0.0):
        return 0.0
    return deficit / dwell


def grade_technique(technique, delivered_rate_per_s, perturbation_current_a,
                    max_perturbation_current_a):
    """Grade one seeding technique against its ceiling and the bed limit."""
    if technique not in SEED_TECHNIQUES:
        raise ValueError(
            "unknown seeding technique %r; known: %s"
            % (technique, ", ".join(sorted(SEED_TECHNIQUES)))
        )
    rate = _number(delivered_rate_per_s, "delivered_rate_per_s")
    if rate <= 0.0:
        raise ValueError("delivered_rate_per_s must be > 0, got %r" % rate)
    current = _number(perturbation_current_a, "perturbation_current_a")
    if current < 0.0:
        raise ValueError("perturbation_current_a must be >= 0, got %r" % current)
    limit = _number(max_perturbation_current_a, "max_perturbation_current_a")
    if limit <= 0.0:
        raise ValueError("max_perturbation_current_a must be > 0, got %r" % limit)
    entry = SEED_TECHNIQUES[technique]
    findings = []
    if not _le(rate, entry["max_rate_per_s"]):
        findings.append("seed-rate-above-technique-ceiling")
    if not _le(current, limit):
        findings.append("rf-perturbation-current-exceeded")
    return {
        "technique": technique,
        "delivered_rate_per_s": rate,
        "technique_ceiling_per_s": entry["max_rate_per_s"],
        "needs_sight_line": entry["needs_sight_line"],
        "perturbation_current_a": current,
        "findings": findings,
        "admissible": not findings,
    }


def assess_multicarrier_seeding(spec):
    """Full clause 6.5.4 assessment for one multiple-carrier run."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a dict")
    for key in _SPEC_KEYS:
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    samples = spec.get("samples", 2048)
    levels = validate_carrier_powers(spec["carrier_powers_w"])
    period = beat_period_s(spec["carrier_spacing_hz"])
    peak = envelope_peak_w(levels)
    threshold = _number(spec["breakdown_threshold_w"], "breakdown_threshold_w")
    if threshold <= 0.0:
        raise ValueError("breakdown_threshold_w must be > 0, got %r" % threshold)
    fraction = above_threshold_fraction(
        levels, spec["carrier_spacing_hz"], threshold, samples
    )
    dwell = fraction * period
    natural = natural_electron_population(
        spec["gap_volume_cm3"], spec["background_rate_per_cm3_s"], dwell
    )
    needed = required_population(spec["seeding_confidence"])
    findings = []
    if not _ge(peak, threshold):
        findings.append("envelope-below-breakdown-threshold")
    required_rate = 0.0
    if dwell > 0.0:
        required_rate = required_seed_rate_per_s(needed, natural, dwell)
    required_seeding = seeding_is_required(natural, needed)
    technique = spec.get("technique")
    technique_report = None
    seeded_population = natural
    if required_seeding and technique is None:
        findings.append("seed-source-absent-for-multicarrier-environment")
    elif technique is not None:
        technique_report = grade_technique(
            technique,
            spec.get("delivered_rate_per_s", 0.0),
            spec.get("perturbation_current_a", 0.0),
            spec.get("max_perturbation_current_a", 1.0),
        )
        findings.extend(technique_report["findings"])
        seeded_population = natural + technique_report["delivered_rate_per_s"] * dwell
        if not _ge(seeded_population, needed):
            findings.append("delivered-seed-rate-below-requirement")
    return {
        "beat_period_s": period,
        "envelope_peak_w": peak,
        "above_threshold_fraction": fraction,
        "above_threshold_dwell_s": dwell,
        "natural_population": natural,
        "natural_presence_probability": presence_probability(natural),
        "required_population": needed,
        "seeding_required": required_seeding,
        "required_seed_rate_per_s": required_rate,
        "seeded_population": seeded_population,
        "seeded_presence_probability": presence_probability(seeded_population),
        "technique_report": technique_report,
        "findings": findings,
        "compliant": not findings,
    }

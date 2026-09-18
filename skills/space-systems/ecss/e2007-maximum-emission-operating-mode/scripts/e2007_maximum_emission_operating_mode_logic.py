#!/usr/bin/env python3
"""Maximum-emission operating mode for ECSS-E-ST-20-07C clause 5.2.7.1.

Paraphrased, implementable procedure (no verbatim standard text):

* An emission measurement characterizes a unit only if the unit is running in
  the operating mode that emits the most. A quiescent or stand-by mode gives
  a clean plot and no information about the configuration that flies.
* The candidate modes are surveyed first -- a short, comparable sweep of each
  mode over each measurement band -- and the survey levels are ranked band by
  band. The worst mode is a property of the band, not of the unit: a switching
  converter can dominate the low band while a transmitter dominates the high
  one.
* A pulsed emitter is compared on the same footing as a continuous one. The
  survey peak of a mode that runs at a duty cycle below unity is corrected to
  an effective average level before the ranking, because two modes read with
  different detectors are not comparable.
* The mode declared for the formal run is then measured against the survey:
  for each band, the decibel shortfall between the worst surveyed level and
  the level of the declared mode. A shortfall inside the allowed margin is
  survey noise; a shortfall beyond it means the formal run would be taken in
  the wrong mode and that band needs its own run.
* Any band whose shortfall exceeds the margin holds the emission run until
  either the declared mode changes or the band is added to the run list.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in decibel sums and
# differences. It is NOT an engineering allowance: the shortfall margin
# itself is never widened.
EMISSION_EPS = 1e-9

DEFAULT_MODE_SPEC = {
    "allowed_shortfall_db": 2.0,
    "min_modes_surveyed": 2.0,
    "min_duty_cycle": 1.0e-6,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=EMISSION_EPS)


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=EMISSION_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard mode-selection specification."""
    spec = dict(DEFAULT_MODE_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_MODE_SPEC:
            raise ValueError("unrecognized mode specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def duty_cycle_correction_db(duty_cycle, spec=None):
    """Peak-to-average correction in dB for an emitter running at a duty cycle."""
    spec = resolve_spec(spec)
    duty_cycle = _require_number(duty_cycle, "duty_cycle")
    if duty_cycle <= 0.0 or duty_cycle > 1.0:
        raise ValueError(
            "duty_cycle must lie in (0, 1], got %r" % (duty_cycle,)
        )
    if duty_cycle < spec["min_duty_cycle"]:
        raise ValueError(
            "duty_cycle %r is below the resolvable minimum %r"
            % (duty_cycle, spec["min_duty_cycle"])
        )
    return 20.0 * math.log10(duty_cycle)


def normalize_mode(mode, spec=None):
    """Validate one surveyed operating mode and return its effective levels."""
    spec = resolve_spec(spec)
    if not isinstance(mode, dict):
        raise ValueError("mode must be a mapping, got %r" % (mode,))
    name = mode.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("mode needs a non-empty 'name', got %r" % (name,))
    levels = mode.get("levels_dbuv")
    if not isinstance(levels, dict) or not levels:
        raise ValueError("mode %r needs a non-empty 'levels_dbuv' mapping" % (name,))
    duty = mode.get("duty_cycle", 1.0)
    correction = duty_cycle_correction_db(duty, spec)
    effective = {}
    for band, level in levels.items():
        if not isinstance(band, str) or not band.strip():
            raise ValueError("mode %r has a band name that is not a string: %r" % (name, band))
        effective[band] = _require_number(level, "mode %r band %r level" % (name, band)) + correction
    return {
        "name": name,
        "duty_cycle": float(duty),
        "correction_db": correction,
        "levels_dbuv": effective,
    }


def normalize_survey(modes, spec=None):
    """Validate a whole emission survey: unique names, one common band set."""
    spec = resolve_spec(spec)
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("modes must be a non-empty sequence")
    normalized = [normalize_mode(m, spec) for m in modes]
    names = [m["name"] for m in normalized]
    if len(set(names)) != len(names):
        raise ValueError("mode names must be unique, got %r" % (names,))
    band_sets = [frozenset(m["levels_dbuv"]) for m in normalized]
    if len(set(band_sets)) != 1:
        raise ValueError(
            "every mode must be surveyed over the same bands, got %r"
            % ([sorted(b) for b in band_sets],)
        )
    return normalized


def survey_bands(modes, spec=None):
    """Band names covered by a survey, in a deterministic order."""
    normalized = normalize_survey(modes, spec)
    return sorted(normalized[0]["levels_dbuv"])


def worst_mode_per_band(modes, spec=None):
    """Highest-emitting mode in each band, ties broken by mode name."""
    normalized = normalize_survey(modes, spec)
    worst = {}
    for band in sorted(normalized[0]["levels_dbuv"]):
        ranked = sorted(
            normalized, key=lambda m: (-m["levels_dbuv"][band], m["name"])
        )
        leader = ranked[0]
        worst[band] = {"mode": leader["name"], "level_dbuv": leader["levels_dbuv"][band]}
    return worst


def dominant_mode(modes, spec=None):
    """Mode that leads the most bands; ties go to the highest single level."""
    normalized = normalize_survey(modes, spec)
    worst = worst_mode_per_band(modes, spec)
    wins = {m["name"]: 0 for m in normalized}
    for entry in worst.values():
        wins[entry["mode"]] += 1
    peak = {m["name"]: max(m["levels_dbuv"].values()) for m in normalized}
    return sorted(wins, key=lambda n: (-wins[n], -peak[n], n))[0]


def mode_shortfall_db(modes, declared_mode, spec=None):
    """Decibels by which the declared mode falls short of the worst, per band."""
    normalized = normalize_survey(modes, spec)
    if not isinstance(declared_mode, str) or not declared_mode.strip():
        raise ValueError("declared_mode must be a non-empty string, got %r" % (declared_mode,))
    by_name = {m["name"]: m for m in normalized}
    if declared_mode not in by_name:
        raise ValueError(
            "declared_mode %r was not surveyed (surveyed: %s)"
            % (declared_mode, ", ".join(sorted(by_name)))
        )
    worst = worst_mode_per_band(modes, spec)
    declared = by_name[declared_mode]
    return {
        band: max(0.0, entry["level_dbuv"] - declared["levels_dbuv"][band])
        for band, entry in worst.items()
    }


def bands_needing_additional_run(modes, declared_mode, spec=None):
    """Bands where the declared mode understates the emission beyond the margin."""
    resolved = resolve_spec(spec)
    shortfalls = mode_shortfall_db(modes, declared_mode, spec)
    return sorted(
        band
        for band, value in shortfalls.items()
        if not _not_above(value, resolved["allowed_shortfall_db"])
    )


def emission_mode_readiness(findings):
    """Gate token for the finding list of one mode selection."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "ready-for-emission-run" if not findings else "hold-mode-selection"


def evaluate_mode_selection(config):
    """End-to-end clause 5.2.7.1 operating-mode check for one emission run."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("modes", "declared_mode"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    spec = resolve_spec(config.get("spec"))
    normalized = normalize_survey(config["modes"], config.get("spec"))
    declared = config["declared_mode"]
    worst = worst_mode_per_band(config["modes"], config.get("spec"))
    shortfalls = mode_shortfall_db(config["modes"], declared, config.get("spec"))
    extra_bands = bands_needing_additional_run(config["modes"], declared, config.get("spec"))
    leader = dominant_mode(config["modes"], config.get("spec"))

    findings = []
    if not _at_least(float(len(normalized)), spec["min_modes_surveyed"]):
        findings.append("fewer operating modes surveyed than the selection requires")
    for band in extra_bands:
        findings.append(
            "band %s emits more in mode %s than in the declared mode"
            % (band, worst[band]["mode"])
        )

    return {
        "modes": normalized,
        "declared_mode": declared,
        "dominant_mode": leader,
        "worst_per_band": worst,
        "shortfall_db": shortfalls,
        "max_shortfall_db": max(shortfalls.values()),
        "bands_needing_additional_run": extra_bands,
        "findings": findings,
        "status": emission_mode_readiness(findings),
        "ready": not findings,
    }

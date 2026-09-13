#!/usr/bin/env python3
"""Discharge and event definitions for a multipactor-qualification run.

Anchor: ECSS-E-ST-20-01C clause 8.5.1 (meanings of event, discharge and
multipactor recalled before a run result is judged). Paraphrased into an
implementable procedure; no standard text is reproduced.

Deterministic, offline, Python standard library only.
"""

import math

# Chamber-pressure regime limits (Pa). Below the first limit the fixture is
# in genuine vacuum and secondary-electron-multiplication is the credible
# mechanism; above the second, residual gas is present and ionisation is the
# credible mechanism; between them both mechanisms are live.
HIGH_VACUUM_LIMIT_PA = 1.0e-4
RESIDUAL_GAS_LIMIT_PA = 1.0e-3

# Susceptibility band of the frequency-gap-product, expressed in GHz-mm.
FD_BAND_MIN_GHZ_MM = 0.1
FD_BAND_MAX_GHZ_MM = 100.0

# Representation tolerance. It absorbs floating-point error at an inclusive
# limit; it never widens the engineering limit itself.
REL_TOL = 1e-12
ABS_TOL = 1e-15

CATEGORY_MULTIPACTOR = "multipactor"
CATEGORY_GAS_DISCHARGE = "gas-discharge"
CATEGORY_UNDETERMINED = "undetermined-event"
CATEGORY_NO_EVENT = "no-event"

REGIME_HIGH_VACUUM = "high-vacuum"
REGIME_TRANSITION = "transition"
REGIME_RESIDUAL_GAS = "residual-gas"

_TERMS = {
    "event": (
        "Any excursion on a monitored detection-channel that reaches or "
        "crosses the trip-threshold declared for that channel. The widest "
        "of the three terms: it records that a deviation occurred, without "
        "yet attributing a mechanism."
    ),
    "discharge": (
        "An event produced by ionisation of residual gas in the fixture "
        "(corona or arc). Its signature is pressure-sensitivity: it tracks "
        "the chamber-pressure reading and appears once the fixture leaves "
        "the high-vacuum-regime."
    ),
    "multipactor": (
        "An event produced by resonant secondary-electron-multiplication "
        "between surfaces in genuine vacuum. Its signature is a "
        "power-threshold: onset above a drive level, extinction when the "
        "drive is taken back below it, and a repeatable onset level."
    ),
}

_REQUIRED_FLAGS = (
    "extinguishes_below_onset",
    "reproducible_onset",
    "pressure_sensitive",
    "seeding_active",
)


def term_definition(term):
    """Return the paraphrased meaning of one of the three defined terms."""
    if not isinstance(term, str):
        raise ValueError("term must be a string, got %r" % (term,))
    key = term.strip().lower()
    if key not in _TERMS:
        raise ValueError(
            "unknown term %r; defined terms are %s"
            % (term, ", ".join(sorted(_TERMS)))
        )
    return _TERMS[key]


def _positive_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _finite_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _at_or_above(value, limit):
    """Inclusive comparison that absorbs floating-point representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def validate_observation(obs):
    """Validate one run-log observation and return a normalised copy."""
    if not isinstance(obs, dict):
        raise ValueError("observation must be a mapping, got %r" % (obs,))
    ident = obs.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("observation id must be a non-empty string")
    channels = obs.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise ValueError("observation %s: channels must be a non-empty mapping" % ident)
    norm_channels = {}
    for name, entry in channels.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("observation %s: channel name must be a non-empty string" % ident)
        if not isinstance(entry, dict):
            raise ValueError("observation %s: channel %s must be a mapping" % (ident, name))
        reading = _finite_float(entry.get("reading"), "channel %s reading" % name)
        threshold = _finite_float(entry.get("threshold"), "channel %s threshold" % name)
        if threshold <= 0.0:
            raise ValueError(
                "observation %s: channel %s trip-threshold must be > 0" % (ident, name)
            )
        norm_channels[name] = {"reading": reading, "threshold": threshold}
    normalised = {
        "id": ident,
        "channels": norm_channels,
        "chamber_pressure_pa": _positive_float(
            obs.get("chamber_pressure_pa"), "chamber_pressure_pa"
        ),
        "frequency_hz": _positive_float(obs.get("frequency_hz"), "frequency_hz"),
        "gap_m": _positive_float(obs.get("gap_m"), "gap_m"),
    }
    for flag in _REQUIRED_FLAGS:
        value = obs.get(flag)
        if not isinstance(value, bool):
            raise ValueError(
                "observation %s: %s must be a boolean, got %r" % (ident, flag, value)
            )
        normalised[flag] = value
    return normalised


def crossed_channels(obs):
    """Return the sorted names of detection-channels at or above trip-threshold."""
    normalised = validate_observation(obs)
    crossed = []
    for name, entry in normalised["channels"].items():
        reading = _finite_float(entry["reading"], "channel %s reading" % name)
        threshold = _finite_float(entry["threshold"], "channel %s threshold" % name)
        if _at_or_above(reading, threshold):
            crossed.append(name)
    return sorted(crossed)


def pressure_regime(pressure_pa):
    """Place a chamber-pressure reading in its regime."""
    pressure = _positive_float(pressure_pa, "chamber_pressure_pa")
    if pressure < HIGH_VACUUM_LIMIT_PA or math.isclose(
        pressure, HIGH_VACUUM_LIMIT_PA, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        return REGIME_HIGH_VACUUM
    if _at_or_above(pressure, RESIDUAL_GAS_LIMIT_PA):
        return REGIME_RESIDUAL_GAS
    return REGIME_TRANSITION


def frequency_gap_product_ghz_mm(frequency_hz, gap_m):
    """Frequency-gap-product in GHz-mm from drive frequency and gap dimension."""
    freq = _positive_float(frequency_hz, "frequency_hz")
    gap = _positive_float(gap_m, "gap_m")
    return (freq / 1.0e9) * (gap * 1.0e3)


def in_susceptibility_band(fd_ghz_mm):
    """True when the frequency-gap-product sits inside the susceptibility band."""
    fd = _positive_float(fd_ghz_mm, "fd_ghz_mm")
    lower_ok = _at_or_above(fd, FD_BAND_MIN_GHZ_MM)
    upper_ok = fd < FD_BAND_MAX_GHZ_MM or math.isclose(
        fd, FD_BAND_MAX_GHZ_MM, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    return lower_ok and upper_ok


def categorize_observation(obs):
    """Categorize one observation against the clause 8.5.1 term definitions."""
    rec = validate_observation(obs)
    crossed = crossed_channels(rec)
    regime = pressure_regime(rec["chamber_pressure_pa"])
    fd = frequency_gap_product_ghz_mm(rec["frequency_hz"], rec["gap_m"])
    in_band = in_susceptibility_band(fd)
    result = {
        "id": rec["id"],
        "crossed_channels": crossed,
        "regime": regime,
        "fd_ghz_mm": fd,
        "in_susceptibility_band": in_band,
        "reasons": [],
    }
    if not crossed:
        result["category"] = CATEGORY_NO_EVENT
        result["reasons"].append("no detection-channel reached its trip-threshold")
        return result
    result["reasons"].append(
        "trip-threshold crossed on: %s" % ", ".join(crossed)
    )
    multipactor_signature = (
        regime in (REGIME_HIGH_VACUUM, REGIME_TRANSITION)
        and in_band
        and rec["extinguishes_below_onset"]
        and rec["reproducible_onset"]
    )
    gas_signature = rec["pressure_sensitive"] and regime in (
        REGIME_TRANSITION,
        REGIME_RESIDUAL_GAS,
    )
    if multipactor_signature and not gas_signature:
        result["category"] = CATEGORY_MULTIPACTOR
        result["reasons"].append(
            "%s regime, frequency-gap-product %.4f GHz-mm inside band, "
            "extinction below onset, repeatable onset" % (regime, fd)
        )
        return result
    if gas_signature and not multipactor_signature:
        result["category"] = CATEGORY_GAS_DISCHARGE
        result["reasons"].append(
            "pressure-sensitive excursion in %s regime" % regime
        )
        return result
    result["category"] = CATEGORY_UNDETERMINED
    if multipactor_signature and gas_signature:
        result["reasons"].append(
            "both signatures met at once; mechanism not resolved"
        )
    else:
        if regime == REGIME_RESIDUAL_GAS:
            result["reasons"].append(
                "residual-gas-regime rules out the vacuum multiplication mechanism"
            )
        if not in_band:
            result["reasons"].append(
                "frequency-gap-product %.4f GHz-mm outside the susceptibility band" % fd
            )
        if not rec["extinguishes_below_onset"]:
            result["reasons"].append("no extinction when the drive dropped below onset")
        if not rec["reproducible_onset"]:
            result["reasons"].append("onset level did not repeat")
        if not rec["pressure_sensitive"]:
            result["reasons"].append("no pressure-sensitivity observed")
    return result


def is_reportable(category):
    """Every category except no-event is carried into the run report."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    known = {
        CATEGORY_MULTIPACTOR,
        CATEGORY_GAS_DISCHARGE,
        CATEGORY_UNDETERMINED,
        CATEGORY_NO_EVENT,
    }
    if category not in known:
        raise ValueError("unknown category %r" % (category,))
    return category != CATEGORY_NO_EVENT


def summarize_run(observations):
    """Categorize a whole run log and report whether it is ready to be judged."""
    if not isinstance(observations, (list, tuple)) or not observations:
        raise ValueError("observations must be a non-empty list")
    counts = {
        CATEGORY_MULTIPACTOR: 0,
        CATEGORY_GAS_DISCHARGE: 0,
        CATEGORY_UNDETERMINED: 0,
        CATEGORY_NO_EVENT: 0,
    }
    categorized = []
    for obs in observations:
        outcome = categorize_observation(obs)
        counts[outcome["category"]] += 1
        categorized.append(outcome)
    undetermined = [c["id"] for c in categorized if c["category"] == CATEGORY_UNDETERMINED]
    reportable = [c["id"] for c in categorized if is_reportable(c["category"])]
    return {
        "counts": counts,
        "observations": categorized,
        "reportable_events": reportable,
        "undetermined_events": undetermined,
        "multipactor_evidence": counts[CATEGORY_MULTIPACTOR] > 0,
        "judgeable": not undetermined,
    }

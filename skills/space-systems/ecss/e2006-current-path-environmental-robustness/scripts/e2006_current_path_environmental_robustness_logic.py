#!/usr/bin/env python3
"""Environmental robustness of bonding current paths --
ECSS-E-ST-20-06C clause 6.8.3 (paraphrased procedure).

Offline, deterministic, stdlib only. The clause asks for evidence that the
mechanical and thermal environments a spacecraft sees do not interrupt or
degrade a bonding current path. This module grades that evidence: which
exposures a path class must have seen, whether each exposure was run at or
above the qualification level for long enough, whether continuity was
monitored while the path was excited, and whether the pre/post bond
resistance drifted beyond what the path can absorb.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-15

ENVIRONMENT_ALIASES = {
    "random-vibration": "random-vibration",
    "random-vib": "random-vibration",
    "broadband-random-vibration": "random-vibration",
    "sine-vibration": "sine-vibration",
    "swept-sine-vibration": "sine-vibration",
    "mechanical-shock": "mechanical-shock",
    "pyroshock": "mechanical-shock",
    "separation-shock": "mechanical-shock",
    "thermal-cycling": "thermal-cycling",
    "thermal-cycle": "thermal-cycling",
    "thermal-vacuum": "thermal-vacuum",
    "tvac": "thermal-vacuum",
    "humidity-and-corrosion": "humidity-and-corrosion",
    "humidity-exposure": "humidity-and-corrosion",
    "acoustic-noise": "acoustic-noise",
    "diffuse-acoustic-field": "acoustic-noise",
}

# Level unit per environment -- a level compared across units is meaningless.
ENVIRONMENT_UNITS = {
    "random-vibration": "grms",
    "sine-vibration": "g-peak",
    "mechanical-shock": "g-srs-peak",
    "thermal-cycling": "cycle-count",
    "thermal-vacuum": "cycle-count",
    "humidity-and-corrosion": "exposure-hours",
    "acoustic-noise": "decibel-overall",
}

# Exposures a current path of each class must have on record.
PATH_CLASS_EXPOSURES = {
    "fault-current-return-path": (
        "random-vibration",
        "mechanical-shock",
        "thermal-cycling",
    ),
    "discharge-return-path": (
        "random-vibration",
        "mechanical-shock",
        "thermal-cycling",
    ),
    "signal-reference-bond": (
        "random-vibration",
        "thermal-cycling",
    ),
    "static-bleed-path": (
        "random-vibration",
        "humidity-and-corrosion",
    ),
}

# Post-exposure bond resistance the path must still meet, in ohm.
PATH_CLASS_POST_LIMIT_OHM = {
    "fault-current-return-path": 2.5e-3,
    "discharge-return-path": 1.0e-2,
    "signal-reference-bond": 1.0e-2,
    "static-bleed-path": 1.0e9,
}

# Fractional resistance drift a path may absorb across an exposure.
DEFAULT_ALLOWABLE_DRIFT = 0.10

# A monitored open of this duration or longer counts as a discontinuity.
DISCONTINUITY_THRESHOLD_US = 1.0

# Environments that excite the joint mechanically must be monitored live;
# an intermittent open can close again before the post-exposure reading.
LIVE_MONITORING_REQUIRED = ("random-vibration", "sine-vibration", "mechanical-shock", "acoustic-noise")


def _le(value, bound):
    return value <= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _ge(value, bound):
    return value >= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _positive(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    if value <= 0.0:
        raise ValueError("%s must be positive" % label)
    return value


def categorize_environment(kind):
    """Map an environment name onto its canonical key."""
    if not isinstance(kind, str):
        raise ValueError("environment must be a string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-")
    if not key:
        raise ValueError("environment must not be blank")
    if key not in ENVIRONMENT_ALIASES:
        raise ValueError("unrecognized environment %r" % (kind,))
    return ENVIRONMENT_ALIASES[key]


def required_exposures(path_class):
    """Exposures a current path of this class must have on record."""
    if not isinstance(path_class, str):
        raise ValueError("path_class must be a string, got %r" % (path_class,))
    key = path_class.strip().lower().replace("_", "-")
    if key not in PATH_CLASS_EXPOSURES:
        raise ValueError("unrecognized current-path class %r" % (path_class,))
    return PATH_CLASS_EXPOSURES[key]


def post_exposure_limit(path_class):
    """Bond resistance the path must still meet after the environments."""
    if not isinstance(path_class, str):
        raise ValueError("path_class must be a string, got %r" % (path_class,))
    key = path_class.strip().lower().replace("_", "-")
    if key not in PATH_CLASS_POST_LIMIT_OHM:
        raise ValueError("unrecognized current-path class %r" % (path_class,))
    return PATH_CLASS_POST_LIMIT_OHM[key]


def check_exposure_level(environment, applied_level, qualification_level, unit=None):
    """Confirm the applied level reaches the qualification level.

    Raises ValueError on a non-positive or non-numeric level, or on a unit
    that does not belong to the environment.
    """
    environment = categorize_environment(environment)
    expected_unit = ENVIRONMENT_UNITS[environment]
    if unit is not None and unit != expected_unit:
        raise ValueError(
            "%s levels are expressed in %r, got %r" % (environment, expected_unit, unit)
        )
    applied = _positive("applied_level", applied_level)
    required = _positive("qualification_level", qualification_level)
    adequate = _ge(applied, required)
    return {
        "environment": environment,
        "unit": expected_unit,
        "applied_level": applied,
        "qualification_level": required,
        "ratio": applied / required,
        "adequate": adequate,
        "findings": []
        if adequate
        else ["%s run at %.6g %s, below the %.6g %s qualification level"
              % (environment, applied, expected_unit, required, expected_unit)],
    }


def count_discontinuity_events(event_durations_us, threshold_us=DISCONTINUITY_THRESHOLD_US):
    """Count monitored opens at or beyond the discontinuity threshold."""
    if not isinstance(event_durations_us, (list, tuple)):
        raise ValueError("event_durations_us must be a list of durations")
    limit = _positive("threshold_us", threshold_us)
    count = 0
    for i, raw in enumerate(event_durations_us):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("event duration %d must be numeric, got %r" % (i, raw))
        duration = float(raw)
        if not math.isfinite(duration):
            raise ValueError("event duration %d must be finite" % i)
        if duration < 0.0:
            raise ValueError("event duration %d must not be negative" % i)
        if _ge(duration, limit):
            count += 1
    return count


def resistance_drift(pre_ohm, post_ohm):
    """Absolute and fractional drift of the bond resistance across exposure."""
    pre = _positive("pre_ohm", pre_ohm)
    if isinstance(post_ohm, bool) or not isinstance(post_ohm, (int, float)):
        raise ValueError("post_ohm must be numeric, got %r" % (post_ohm,))
    post = float(post_ohm)
    if not math.isfinite(post):
        raise ValueError("post_ohm must be finite")
    if post < 0.0:
        raise ValueError("post_ohm must not be negative")
    delta = post - pre
    return {"pre_ohm": pre, "post_ohm": post, "delta_ohm": delta, "fraction": delta / pre}


def evaluate_exposure(path_class, record, allowable_drift=DEFAULT_ALLOWABLE_DRIFT):
    """Grade one environmental exposure of one current path.

    record keys: environment, applied_level, qualification_level, optional
    unit, duration_s, required_duration_s, monitored (bool),
    discontinuity_events_us (list), pre_ohm, post_ohm.
    """
    if not isinstance(record, dict):
        raise ValueError("exposure record must be a mapping, got %r" % (type(record).__name__,))
    limit = post_exposure_limit(path_class)
    drift_limit = _positive("allowable_drift", allowable_drift)
    environment = categorize_environment(record.get("environment"))
    level = check_exposure_level(
        environment,
        record.get("applied_level"),
        record.get("qualification_level"),
        record.get("unit"),
    )
    findings = list(level["findings"])
    duration = record.get("duration_s")
    required_duration = record.get("required_duration_s")
    if duration is not None or required_duration is not None:
        applied_s = _positive("duration_s", duration)
        required_s = _positive("required_duration_s", required_duration)
        if not _ge(applied_s, required_s):
            findings.append(
                "%s held for %.6g s against a %.6g s requirement" % (environment, applied_s, required_s)
            )
    monitored = record.get("monitored", False)
    if not isinstance(monitored, bool):
        raise ValueError("monitored must be a boolean, got %r" % (monitored,))
    events = record.get("discontinuity_events_us", [])
    event_count = count_discontinuity_events(events)
    if environment in LIVE_MONITORING_REQUIRED and not monitored:
        findings.append("%s ran without live continuity monitoring of the path" % environment)
    if event_count:
        findings.append("%d monitored discontinuity event(s) during %s" % (event_count, environment))
    drift = resistance_drift(record.get("pre_ohm"), record.get("post_ohm"))
    if not _le(abs(drift["fraction"]), drift_limit):
        findings.append(
            "bond resistance drifted %.3f%% across %s against a %.3f%% allowance"
            % (drift["fraction"] * 100.0, environment, drift_limit * 100.0)
        )
    if not _le(drift["post_ohm"], limit):
        findings.append(
            "post-exposure resistance %.6g ohm exceeds the %.6g ohm limit for the path class"
            % (drift["post_ohm"], limit)
        )
    return {
        "environment": environment,
        "level_adequate": level["adequate"],
        "level_ratio": level["ratio"],
        "discontinuity_events": event_count,
        "drift_fraction": drift["fraction"],
        "post_ohm": drift["post_ohm"],
        "passed": not findings,
        "findings": findings,
    }


def assess_current_path(path, allowable_drift=DEFAULT_ALLOWABLE_DRIFT):
    """Grade one bonding current path against clause 6.8.3.

    path keys: id, path_class, exposures (list of exposure records).
    """
    if not isinstance(path, dict):
        raise ValueError("path must be a mapping, got %r" % (type(path).__name__,))
    ident = path.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("path needs a non-blank string id")
    path_class = path.get("path_class")
    needed = required_exposures(path_class)
    raw = path.get("exposures")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("path %s carries no exposure records" % ident)
    results = []
    seen = []
    findings = []
    for record in raw:
        result = evaluate_exposure(path_class, record, allowable_drift)
        if result["environment"] in seen:
            raise ValueError(
                "duplicate %s exposure on path %s" % (result["environment"], ident)
            )
        seen.append(result["environment"])
        results.append(result)
        findings.extend(result["findings"])
    missing = [env for env in needed if env not in seen]
    for env in missing:
        findings.append("%s exposure required for this path class and absent" % env)
    worst_post = max(r["post_ohm"] for r in results)
    return {
        "id": ident,
        "path_class": path_class,
        "exposures": results,
        "environments_covered": sorted(seen),
        "missing_exposures": missing,
        "worst_post_ohm": worst_post,
        "max_drift_fraction": max(abs(r["drift_fraction"]) for r in results),
        "status": "robust" if not findings else "not-demonstrated",
        "findings": findings,
    }


def summarize_robustness_campaign(paths, allowable_drift=DEFAULT_ALLOWABLE_DRIFT):
    """Roll per-path verdicts into a campaign-level statement."""
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty list")
    results = [assess_current_path(p, allowable_drift) for p in paths]
    open_ids = [r["id"] for r in results if r["status"] != "robust"]
    return {
        "paths": results,
        "robust_count": len(results) - len(open_ids),
        "open_ids": open_ids,
        "campaign_closed": not open_ids,
    }

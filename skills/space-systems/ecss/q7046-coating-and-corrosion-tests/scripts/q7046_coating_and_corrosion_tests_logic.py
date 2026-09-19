#!/usr/bin/env python3
"""Coating and corrosion acceptance for threaded fasteners.

Anchor: ECSS-Q-ST-70-46 testing clause on threaded fasteners, with the
durability tests it hands to the companion coatings standard
ECSS-Q-ST-70-17. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Thickness has a floor and a ceiling. Too thin is short protection; too
thick fouls the thread fit and moves the torque-tension relation the
joint was designed around. The verdict is per reading, because the
thinnest spot is where corrosion starts.

Adhesion is judged by the method the coating calls for; a result
recorded against another method is an invalid test rather than a pass.

Corrosion exposure scales with where the hardware lives before launch.
Two corrosion products mean two things: a sacrificial bloom is the
coating working and is tolerated after a fraction of the exposure,
while base-metal attack fails at whatever hour it appears.

An electrodeposited coating on a high-strength fastener carries a
hydrogen risk. The relief bake must start inside a short window after
plating and run its full duration; starting late is not recoverable by
running longer.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

#: Relative slack on a comparison whose two sides are both computed.
COATING_REL_TOL = 1e-9

MIN_THICKNESS_READINGS = 3

ADHESION_BEND = "bend-and-inspect"
ADHESION_TAPE = "tape-pull"
ADHESION_BURNISH = "burnish-and-inspect"

ADHESION_INTACT = "no-detachment"
ADHESION_FLAKING = "flaking"
ADHESION_BLISTERING = "blistering"
ADHESION_RESULTS = (ADHESION_INTACT, ADHESION_FLAKING, ADHESION_BLISTERING)

CORROSION_NONE = "no-corrosion-product"
CORROSION_SACRIFICIAL = "sacrificial-bloom"
CORROSION_BASE_METAL = "base-metal-attack"
CORROSION_OBSERVATIONS = (
    CORROSION_NONE,
    CORROSION_SACRIFICIAL,
    CORROSION_BASE_METAL,
)

#: Fraction of the required exposure before a bloom is tolerated.
SACRIFICIAL_TOLERATED_AFTER = 0.5

#: Relief bake must start within this many hours of plating.
RELIEF_BAKE_WINDOW_HOURS = 4.0

#: and run for at least this many hours once started.
RELIEF_BAKE_DURATION_HOURS = 23.0

VERDICT_ACCEPT = "coating-accepted"
VERDICT_THICKNESS = "coating-thickness-out-of-band"
VERDICT_ADHESION = "coating-adhesion-failure"
VERDICT_CORROSION = "corrosion-resistance-failure"
VERDICT_RELIEF = "embrittlement-relief-non-conformance"
VERDICT_INVALID = "coating-test-invalid"

_COATING_SPECS = {
    "zinc-nickel-plating": {
        "thickness_min_um": 5.0,
        "thickness_max_um": 12.0,
        "adhesion_method": ADHESION_BEND,
        "base_exposure_hours": 500.0,
        "electrodeposited": True,
        "durability_tests": (
            "coating-thermal-cycling",
            "coating-humidity-exposure",
        ),
    },
    "aluminium-ion-vapour-deposition": {
        "thickness_min_um": 8.0,
        "thickness_max_um": 25.0,
        "adhesion_method": ADHESION_BEND,
        "base_exposure_hours": 500.0,
        "electrodeposited": False,
        "durability_tests": ("coating-thermal-cycling",),
    },
    "chromate-conversion": {
        "thickness_min_um": 0.5,
        "thickness_max_um": 3.0,
        "adhesion_method": ADHESION_TAPE,
        "base_exposure_hours": 168.0,
        "electrodeposited": False,
        "durability_tests": ("coating-humidity-exposure",),
    },
    "silver-plating": {
        "thickness_min_um": 3.0,
        "thickness_max_um": 10.0,
        "adhesion_method": ADHESION_BURNISH,
        "base_exposure_hours": 96.0,
        "electrodeposited": True,
        "durability_tests": (
            "coating-thermal-cycling",
            "coating-galling-and-wear",
        ),
    },
    "dry-film-lubricant": {
        "thickness_min_um": 5.0,
        "thickness_max_um": 15.0,
        "adhesion_method": ADHESION_TAPE,
        "base_exposure_hours": 48.0,
        "electrodeposited": False,
        "durability_tests": (
            "coating-galling-and-wear",
            "coating-repeated-installation-wear",
            "coating-vacuum-outgassing",
        ),
    },
}

COATING_TYPES = tuple(sorted(_COATING_SPECS))

#: Exposure multiplier for where the hardware waits before launch.
_ENVIRONMENT_FACTORS = {
    "clean-room-storage": 0.5,
    "integration-hall": 1.0,
    "coastal-launch-site": 2.0,
    "in-orbit-vacuum": 0.25,
}

ENVIRONMENTS = tuple(sorted(_ENVIRONMENT_FACTORS))

#: Durability tests the environment adds on top of the coating's own.
_ENVIRONMENT_DURABILITY = {
    "coastal-launch-site": ("coating-salt-fog-durability",),
    "in-orbit-vacuum": ("coating-vacuum-outgassing",),
}


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be finite and non-negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, bound, rel_tol=COATING_REL_TOL):
    return value >= bound - abs(bound) * rel_tol


def _at_most(value, bound, rel_tol=COATING_REL_TOL):
    return value <= bound + abs(bound) * rel_tol


def coating_spec(coating_type):
    """Thickness band, adhesion method and exposure of one coating."""
    _require_choice("coating_type", coating_type, COATING_TYPES)
    spec = _COATING_SPECS[coating_type]
    return {
        "coating_type": coating_type,
        "thickness_min_um": spec["thickness_min_um"],
        "thickness_max_um": spec["thickness_max_um"],
        "adhesion_method": spec["adhesion_method"],
        "base_exposure_hours": spec["base_exposure_hours"],
        "electrodeposited": spec["electrodeposited"],
        "durability_tests": list(spec["durability_tests"]),
    }


def environment_factor(environment):
    """Exposure multiplier for where the hardware waits before launch."""
    _require_choice("environment", environment, ENVIRONMENTS)
    return _ENVIRONMENT_FACTORS[environment]


def required_exposure_hours(coating_type, environment):
    """Corrosion exposure the lot owes, scaled to the environment."""
    spec = coating_spec(coating_type)
    return spec["base_exposure_hours"] * environment_factor(environment)


def thickness_verdict(readings_um, coating_type):
    """Judge every thickness reading against the band, not the mean."""
    if isinstance(readings_um, (str, dict)) or not isinstance(
        readings_um, (list, tuple)
    ):
        raise ValueError(
            "readings_um must be a sequence of numbers, got %r" % (readings_um,)
        )
    if len(readings_um) < MIN_THICKNESS_READINGS:
        raise ValueError(
            "%d thickness reading(s) given; at least %d are needed to speak "
            "for a lot" % (len(readings_um), MIN_THICKNESS_READINGS)
        )
    values = [_require_positive("thickness reading", v) for v in readings_um]
    spec = coating_spec(coating_type)
    thinnest = min(values)
    thickest = max(values)
    below = [v for v in values if not _at_least(v, spec["thickness_min_um"])]
    above = [v for v in values if not _at_most(v, spec["thickness_max_um"])]
    findings = []
    if below:
        findings.append(
            "%d reading(s) below the %.1f um floor, thinnest %.2f um; the "
            "protection is short where it is thinnest"
            % (len(below), spec["thickness_min_um"], thinnest)
        )
    if above:
        findings.append(
            "%d reading(s) above the %.1f um ceiling, thickest %.2f um; the "
            "thread fit and the torque-tension relation are both affected"
            % (len(above), spec["thickness_max_um"], thickest)
        )
    return {
        "coating_type": coating_type,
        "thinnest_um": thinnest,
        "thickest_um": thickest,
        "mean_um": sum(values) / len(values),
        "below_floor": len(below),
        "above_ceiling": len(above),
        "thread_fit_risk": bool(above),
        "in_band": not (below or above),
        "findings": findings,
    }


def adhesion_verdict(coating_type, method_used, result):
    """Judge adhesion, after confirming the method suits the coating."""
    spec = coating_spec(coating_type)
    _require_choice("result", result, ADHESION_RESULTS)
    expected = spec["adhesion_method"]
    if method_used != expected:
        return {
            "valid": False,
            "passed": False,
            "expected_method": expected,
            "method_used": method_used,
            "findings": [
                "adhesion was recorded by %r but %s calls for %r; the result "
                "does not speak to this coating"
                % (method_used, coating_type, expected)
            ],
        }
    passed = result == ADHESION_INTACT
    findings = []
    if not passed:
        findings.append(
            "adhesion test by %s showed %s" % (expected, result)
        )
    return {
        "valid": True,
        "passed": passed,
        "expected_method": expected,
        "method_used": method_used,
        "findings": findings,
    }


def corrosion_verdict(
    coating_type,
    environment,
    hours_run,
    observation,
    observed_at_hours=None,
):
    """Judge corrosion exposure, splitting bloom from base-metal attack."""
    required = required_exposure_hours(coating_type, environment)
    run = _require_non_negative("hours_run", hours_run)
    _require_choice("observation", observation, CORROSION_OBSERVATIONS)
    findings = []
    if observation != CORROSION_NONE:
        if observed_at_hours is None:
            raise ValueError(
                "observed_at_hours is required when a corrosion product was "
                "seen; the hour it appeared decides the verdict"
            )
        seen_at = _require_non_negative("observed_at_hours", observed_at_hours)
        if seen_at > run:
            raise ValueError(
                "observed_at_hours %.1f is beyond the %.1f hours the test ran"
                % (seen_at, run)
            )
    else:
        seen_at = None

    exposure_complete = _at_least(run, required)
    if not exposure_complete and observation != CORROSION_BASE_METAL:
        findings.append(
            "exposure ran %.1f h of the %.1f h required for %s in a %s "
            "environment" % (run, required, coating_type, environment)
        )

    passed = exposure_complete
    if observation == CORROSION_BASE_METAL:
        passed = False
        findings.append(
            "base-metal attack seen at %.1f h; the substrate is corroding and "
            "the hour it appeared does not soften that" % seen_at
        )
    elif observation == CORROSION_SACRIFICIAL:
        tolerated_from = required * SACRIFICIAL_TOLERATED_AFTER
        if _at_least(seen_at, tolerated_from):
            findings.append(
                "sacrificial bloom from %.1f h, at or beyond the %.1f h point "
                "where it is tolerated" % (seen_at, tolerated_from)
            )
        else:
            passed = False
            findings.append(
                "sacrificial bloom at %.1f h, before the %.1f h point where it "
                "is tolerated" % (seen_at, tolerated_from)
            )

    return {
        "required_hours": required,
        "hours_run": run,
        "observation": observation,
        "observed_at_hours": seen_at,
        "exposure_complete": exposure_complete,
        "passed": passed,
        "findings": findings,
    }


def relief_bake_verdict(
    coating_type,
    baked=False,
    start_delay_hours=None,
    duration_hours=None,
):
    """Check the embrittlement relief bake where the deposit needs one."""
    spec = coating_spec(coating_type)
    if not spec["electrodeposited"]:
        return {
            "required": False,
            "conforming": True,
            "findings": [],
        }
    if not baked:
        return {
            "required": True,
            "conforming": False,
            "findings": [
                "%s is electrodeposited and no relief bake was recorded"
                % coating_type
            ],
        }
    delay = _require_non_negative("start_delay_hours", start_delay_hours)
    duration = _require_positive("duration_hours", duration_hours)
    findings = []
    if not _at_most(delay, RELIEF_BAKE_WINDOW_HOURS):
        findings.append(
            "the bake started %.1f h after plating, outside the %.1f h window; "
            "running it longer does not recover a late start"
            % (delay, RELIEF_BAKE_WINDOW_HOURS)
        )
    if not _at_least(duration, RELIEF_BAKE_DURATION_HOURS):
        findings.append(
            "the bake ran %.1f h of the %.1f h it owes"
            % (duration, RELIEF_BAKE_DURATION_HOURS)
        )
    return {
        "required": True,
        "conforming": not findings,
        "start_delay_hours": delay,
        "duration_hours": duration,
        "findings": findings,
    }


def durability_tests_owed(coating_type, environment):
    """Durability tests the companion coatings standard adds."""
    spec = coating_spec(coating_type)
    _require_choice("environment", environment, ENVIRONMENTS)
    owed = list(spec["durability_tests"])
    for test in _ENVIRONMENT_DURABILITY.get(environment, ()):
        if test not in owed:
            owed.append(test)
    return owed


def assess_coating_programme(case):
    """Thickness, adhesion, corrosion and relief bake in one verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    coating_type = _require_choice(
        "coating_type", case.get("coating_type"), COATING_TYPES
    )
    environment = _require_choice(
        "environment", case.get("environment"), ENVIRONMENTS
    )
    thickness = thickness_verdict(case.get("thickness_readings_um"), coating_type)
    adhesion = adhesion_verdict(
        coating_type,
        case.get("adhesion_method"),
        case.get("adhesion_result"),
    )
    corrosion = corrosion_verdict(
        coating_type,
        environment,
        case.get("exposure_hours_run", 0.0),
        case.get("corrosion_observation", CORROSION_NONE),
        case.get("corrosion_observed_at_hours"),
    )
    relief = relief_bake_verdict(
        coating_type,
        bool(case.get("relief_bake_done", False)),
        case.get("relief_bake_delay_hours"),
        case.get("relief_bake_duration_hours"),
    )

    owed = durability_tests_owed(coating_type, environment)
    recorded = case.get("durability_tests_recorded", ())
    if isinstance(recorded, (str, dict)) or not isinstance(recorded, (list, tuple)):
        raise ValueError(
            "durability_tests_recorded must be a sequence, got %r" % (recorded,)
        )
    outstanding = [test for test in owed if test not in set(recorded)]

    findings = []
    findings.extend(thickness["findings"])
    findings.extend(adhesion["findings"])
    findings.extend(corrosion["findings"])
    findings.extend(relief["findings"])
    if outstanding:
        findings.append(
            "%d durability test(s) graded against the companion coatings "
            "standard have no record: %s" % (len(outstanding), ", ".join(outstanding))
        )

    if not adhesion["valid"]:
        verdict = VERDICT_INVALID
    elif not thickness["in_band"]:
        verdict = VERDICT_THICKNESS
    elif not adhesion["passed"]:
        verdict = VERDICT_ADHESION
    elif not corrosion["passed"]:
        verdict = VERDICT_CORROSION
    elif not relief["conforming"]:
        verdict = VERDICT_RELIEF
    else:
        verdict = VERDICT_ACCEPT

    return {
        "coating_type": coating_type,
        "environment": environment,
        "thickness": thickness,
        "adhesion": adhesion,
        "corrosion": corrosion,
        "relief_bake": relief,
        "durability_tests_owed": owed,
        "durability_tests_outstanding": outstanding,
        "findings": findings,
        "verdict": verdict,
    }

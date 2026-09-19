#!/usr/bin/env python3
"""Mission phase and environment definition for a mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Before a mechanism is sized, the mission it has to survive is written
down: the phases it passes through, and in each phase the environments
that drive the design. Five categories are carried here because each
one drives different hardware:

    thermal            the temperature extremes the materials and
                       lubricants see
    random-vibration   the broadband level that sizes the structure
                       and the launch restraint
    shock              the transient the release devices impose on
                       everything nearby
    radiation          the dose accumulated over the whole mission,
                       which is what degrades polymers and lubricants
    life-cycles        the number of actuations, which is what wears
                       the tribological pairs out

The envelope is taken across phases: the coldest cold, the hottest
hot, the worst level, and the totals that accumulate. A phase that
leaves a category unstated is a gap, not a zero -- the envelope refuses
to run over one, because an envelope over an unknown is not an
envelope.

Qualification levels are the envelope raised by the declared margins:
a temperature margin in kelvin, a vibration margin in decibel, a shock
factor, a radiation design margin on dose, and a life factor on
cycles.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ENVIRONMENT_CATEGORIES = (
    "thermal",
    "random-vibration",
    "shock",
    "radiation",
    "life-cycles",
)

_CATEGORY_FIELDS = {
    "thermal": ("min_temperature_c", "max_temperature_c"),
    "random-vibration": ("random_vibration_grms",),
    "shock": ("shock_srs_peak_g",),
    "radiation": ("radiation_dose_krad",),
    "life-cycles": ("actuation_cycles",),
}

DEFAULT_ENVIRONMENT_POLICY = {
    "thermal_qualification_margin_k": 10.0,
    "random_vibration_qualification_db": 3.0,
    "shock_qualification_factor": 1.4,
    "radiation_design_margin": 2.0,
    "life_test_factor": 4.0,
    "required_categories": ENVIRONMENT_CATEGORIES,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_environment_policy(policy):
    """Check the margin policy names every factor the levels need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative(
        "thermal_qualification_margin_k", policy.get("thermal_qualification_margin_k")
    )
    _require_non_negative(
        "random_vibration_qualification_db",
        policy.get("random_vibration_qualification_db"),
    )
    for key in (
        "shock_qualification_factor",
        "radiation_design_margin",
        "life_test_factor",
    ):
        factor = _require_positive(key, policy.get(key))
        if factor < 1.0:
            raise ValueError("policy %s must be at least unity, got %g" % (key, factor))
    required = policy.get("required_categories")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required_categories must be a non-empty sequence")
    for category in required:
        if category not in ENVIRONMENT_CATEGORIES:
            raise ValueError("unknown environment category %r" % (category,))
    return policy


def undeclared_categories(phase, policy=DEFAULT_ENVIRONMENT_POLICY):
    """Environment categories a phase is required to state but does not.

    A missing field is an omission, never a zero. Reporting it is the
    point: a phase with no radiation entry has not survived a zero
    dose, it has simply not been written down yet.
    """
    validate_environment_policy(policy)
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping, got %r" % (phase,))
    gaps = []
    for category in policy["required_categories"]:
        for field in _CATEGORY_FIELDS[category]:
            if phase.get(field) is None:
                if category not in gaps:
                    gaps.append(category)
    return gaps


def validate_phase(phase, policy=DEFAULT_ENVIRONMENT_POLICY):
    """Normalise one mission phase, refusing an undeclared category."""
    validate_environment_policy(policy)
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping, got %r" % (phase,))
    name = phase.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase name must be a non-empty string, got %r" % (name,))
    gaps = undeclared_categories(phase, policy)
    if gaps:
        raise ValueError(
            "phase %s leaves %s undeclared; an unstated environment is not a "
            "zero one" % (name, ", ".join(gaps))
        )
    record = {
        "name": name,
        "duration_h": _require_non_negative("duration_h", phase.get("duration_h")),
        "min_temperature_c": _require_number(
            "min_temperature_c", phase.get("min_temperature_c")
        ),
        "max_temperature_c": _require_number(
            "max_temperature_c", phase.get("max_temperature_c")
        ),
        "random_vibration_grms": _require_non_negative(
            "random_vibration_grms", phase.get("random_vibration_grms")
        ),
        "shock_srs_peak_g": _require_non_negative(
            "shock_srs_peak_g", phase.get("shock_srs_peak_g")
        ),
        "radiation_dose_krad": _require_non_negative(
            "radiation_dose_krad", phase.get("radiation_dose_krad")
        ),
        "actuation_cycles": _require_count(
            "actuation_cycles", phase.get("actuation_cycles"), 0
        ),
    }
    if record["max_temperature_c"] < record["min_temperature_c"]:
        raise ValueError(
            "phase %s states a maximum temperature below its minimum" % name
        )
    return record


def envelope_environments(phases, policy=DEFAULT_ENVIRONMENT_POLICY):
    """Worst case across every phase, plus the quantities that accumulate."""
    validate_environment_policy(policy)
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence")
    seen = set()
    records = []
    for phase in phases:
        record = validate_phase(phase, policy)
        if record["name"] in seen:
            raise ValueError("duplicate phase name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    return {
        "phase_count": len(records),
        "total_duration_h": sum(r["duration_h"] for r in records),
        "min_temperature_c": min(r["min_temperature_c"] for r in records),
        "max_temperature_c": max(r["max_temperature_c"] for r in records),
        "max_random_vibration_grms": max(r["random_vibration_grms"] for r in records),
        "max_shock_srs_peak_g": max(r["shock_srs_peak_g"] for r in records),
        "total_radiation_dose_krad": sum(r["radiation_dose_krad"] for r in records),
        "total_actuation_cycles": sum(r["actuation_cycles"] for r in records),
        "driving_phases": {
            "cold": min(records, key=lambda r: r["min_temperature_c"])["name"],
            "hot": max(records, key=lambda r: r["max_temperature_c"])["name"],
            "vibration": max(records, key=lambda r: r["random_vibration_grms"])["name"],
            "shock": max(records, key=lambda r: r["shock_srs_peak_g"])["name"],
        },
    }


def decibel_to_amplitude_factor(decibel):
    """Amplitude factor of a level expressed in decibel."""
    return 10.0 ** (_require_number("decibel", decibel) / 20.0)


def qualification_levels(envelope, policy=DEFAULT_ENVIRONMENT_POLICY):
    """Raise the mission envelope to the levels the design is proved at."""
    validate_environment_policy(policy)
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping, got %r" % (envelope,))
    for key in (
        "min_temperature_c",
        "max_temperature_c",
        "max_random_vibration_grms",
        "max_shock_srs_peak_g",
        "total_radiation_dose_krad",
        "total_actuation_cycles",
    ):
        if envelope.get(key) is None:
            raise ValueError("envelope is missing %s" % key)
    margin = policy["thermal_qualification_margin_k"]
    factor = decibel_to_amplitude_factor(policy["random_vibration_qualification_db"])
    cycles = _require_count(
        "total_actuation_cycles", envelope["total_actuation_cycles"], 0
    )
    return {
        "qualification_min_temperature_c": envelope["min_temperature_c"] - margin,
        "qualification_max_temperature_c": envelope["max_temperature_c"] + margin,
        "qualification_random_vibration_grms": envelope["max_random_vibration_grms"]
        * factor,
        "qualification_shock_srs_peak_g": envelope["max_shock_srs_peak_g"]
        * policy["shock_qualification_factor"],
        "design_radiation_dose_krad": envelope["total_radiation_dose_krad"]
        * policy["radiation_design_margin"],
        "life_test_cycles": int(math.ceil(cycles * policy["life_test_factor"])),
    }


def assess_environment_definition(case, policy=DEFAULT_ENVIRONMENT_POLICY):
    """Full clause 4.3 verdict: coverage, envelope, levels and capability."""
    validate_environment_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    phases = case.get("phases")
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("case must carry a non-empty phases sequence")
    gaps = {}
    for phase in phases:
        missing = undeclared_categories(phase, policy)
        if missing:
            name = phase.get("name") if isinstance(phase, dict) else repr(phase)
            gaps[str(name)] = missing
    if gaps:
        return {
            "definition_complete": False,
            "undeclared": gaps,
            "verdict": "environment-definition-incomplete",
            "compliant": False,
            "findings": [
                "phase %s leaves %s undeclared" % (name, ", ".join(missing))
                for name, missing in sorted(gaps.items())
            ],
        }
    envelope = envelope_environments(phases, policy)
    levels = qualification_levels(envelope, policy)
    capability = case.get("declared_capability")
    findings = []
    if capability is None:
        return {
            "definition_complete": True,
            "undeclared": {},
            "envelope": envelope,
            "qualification_levels": levels,
            "compliant": None,
            "verdict": "capability-not-evaluated",
            "findings": [
                "the environment definition is complete but no design "
                "capability was declared to grade it against"
            ],
        }
    if not isinstance(capability, dict):
        raise ValueError("declared_capability must be a mapping")
    checks = (
        ("min_temperature_c", "qualification_min_temperature_c", "at_most"),
        ("max_temperature_c", "qualification_max_temperature_c", "at_least"),
        ("random_vibration_grms", "qualification_random_vibration_grms", "at_least"),
        ("shock_srs_peak_g", "qualification_shock_srs_peak_g", "at_least"),
        ("radiation_dose_krad", "design_radiation_dose_krad", "at_least"),
        ("actuation_cycles", "life_test_cycles", "at_least"),
    )
    shortfalls = []
    for field, level_key, sense in checks:
        declared = capability.get(field)
        if declared is None:
            shortfalls.append(field)
            findings.append("design capability does not state %s" % field)
            continue
        declared = _require_number(field, declared)
        needed = float(levels[level_key])
        held = _at_most(declared, needed) if sense == "at_most" else _at_least(
            declared, needed
        )
        if not held:
            shortfalls.append(field)
            findings.append(
                "declared %s of %g does not cover the required %g"
                % (field, declared, needed)
            )
    compliant = not shortfalls
    return {
        "definition_complete": True,
        "undeclared": {},
        "envelope": envelope,
        "qualification_levels": levels,
        "shortfalls": shortfalls,
        "compliant": compliant,
        "verdict": "environments-covered" if compliant else "capability-shortfall",
        "findings": findings,
    }

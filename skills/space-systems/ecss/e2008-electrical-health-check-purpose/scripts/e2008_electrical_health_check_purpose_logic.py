#!/usr/bin/env python3
"""Why continuity, insulation and related checks make an electrical health
assessment of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.1. The reasoning below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly has exactly two electrical things that can go
wrong and no third. Current can fail to go where it should -- an
interconnector joint that has cracked, a bus bar that has lifted, a
diode that no longer conducts -- and current can go where it should
not, across an isolation barrier that has been bridged by a solder
ball, a swarf particle or damaged insulation. Continuity checks look
for the first and insulation checks for the second, and between them
they span the failure space. That is why the clause groups them into
one assessment rather than listing them as separate tests.

Two things therefore decide how much a health assessment is worth, and
neither of them is the measured value.

The first is coverage. The assessment is a statement about the whole
assembly, so every declared current-carrying path needs a continuity
check and every declared isolation barrier needs an insulation check.
A path nobody measured is not healthy; it is unmeasured, and the two
have to read differently.

The second is discrimination. A check can only report a defect its
instrument could have resolved. A continuity measurement with a
one ohm resolution cannot find a degraded joint that added two
hundred milliohms, and an insulation measurement taken below the
barrier's rated voltage never stressed the barrier it was there to
prove. Such a check returns indeterminate: it did not pass and it did
not fail, and calling it healthy is the defect this module exists to
prevent.

Check kinds
    continuity            resistance of a current-carrying path
    insulation-resistance resistance across an isolation barrier
    polarity              which way round a string is wired
    bypass-diode-function forward drop and reverse leakage of a diode
    grounding-bond        resistance of a structure bonding strap

Outcomes are healthy, indeterminate, degraded and failed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CHECK_KINDS = (
    "continuity",
    "insulation-resistance",
    "polarity",
    "bypass-diode-function",
    "grounding-bond",
)

PATH_CHECK_KINDS = ("continuity",)
BARRIER_CHECK_KINDS = ("insulation-resistance",)

HEALTHY = "healthy"
INDETERMINATE = "indeterminate"
DEGRADED = "degraded"
FAILED = "failed"
HEALTH_OUTCOMES = (HEALTHY, INDETERMINATE, DEGRADED, FAILED)

_SEVERITY_ORDER = {HEALTHY: 0, INDETERMINATE: 1, DEGRADED: 2, FAILED: 3}

POLARITIES = ("positive", "negative")

REQUIRED_CHECK_FIELDS = {
    "continuity": (
        "expected_resistance_ohm",
        "measured_resistance_ohm",
        "resolution_ohm",
    ),
    "insulation-resistance": (
        "measured_resistance_ohm",
        "applied_voltage_v",
        "rated_voltage_v",
    ),
    "polarity": ("expected_polarity", "measured_polarity"),
    "bypass-diode-function": ("forward_drop_v", "reverse_leakage_a"),
    "grounding-bond": ("measured_resistance_ohm", "resolution_ohm"),
}

DEFAULT_HEALTH_CRITERIA = {
    "min_resolution_ratio": 10.0,
    "continuity_tolerance_fraction": 0.20,
    "continuity_degraded_factor": 2.0,
    "min_insulation_resistance_ohm": 1.0e8,
    "insulation_degraded_factor": 10.0,
    "max_grounding_bond_resistance_ohm": 0.1,
    "grounding_degraded_factor": 2.0,
    "min_diode_forward_drop_v": 0.3,
    "max_diode_forward_drop_v": 1.2,
    "max_diode_reverse_leakage_a": 1.0e-5,
    "diode_leakage_degraded_factor": 10.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every band here is a product of a criteria fraction and an expected
    value, so a measurement sitting exactly on a band edge can evaluate
    a few units in the last place outside it. The band is never
    widened; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(outcomes):
    worst = HEALTHY
    for outcome in outcomes:
        if _SEVERITY_ORDER[outcome] > _SEVERITY_ORDER[worst]:
            worst = outcome
    return worst


def validate_health_criteria(criteria):
    """Check a health criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "min_resolution_ratio",
        "continuity_tolerance_fraction",
        "min_insulation_resistance_ohm",
        "max_grounding_bond_resistance_ohm",
        "min_diode_forward_drop_v",
        "max_diode_forward_drop_v",
        "max_diode_reverse_leakage_a",
    ):
        _require_positive("criteria %s" % key, criteria.get(key))
    tolerance = criteria["continuity_tolerance_fraction"]
    if tolerance >= 1.0:
        raise ValueError(
            "criteria continuity_tolerance_fraction must be below one; a band as "
            "wide as the expected resistance accepts an open circuit"
        )
    if criteria["min_diode_forward_drop_v"] >= criteria["max_diode_forward_drop_v"]:
        raise ValueError(
            "criteria min_diode_forward_drop_v must be below "
            "max_diode_forward_drop_v"
        )
    for key in (
        "continuity_degraded_factor",
        "insulation_degraded_factor",
        "grounding_degraded_factor",
        "diode_leakage_degraded_factor",
    ):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one, got %r" % (key, factor)
            )
    ratio = criteria["min_resolution_ratio"]
    if ratio < 1.0:
        raise ValueError(
            "criteria min_resolution_ratio must be at least one; an instrument "
            "coarser than the accept band cannot discriminate at all"
        )
    return criteria


def discrimination_ratio(accept_band, instrument_resolution):
    """How many instrument steps fit inside the band a check has to judge.

    A ratio at or above the criteria minimum means the instrument could
    have seen a defect sitting just outside the band. Below it, a
    reading inside the band says as much about the instrument as about
    the assembly.
    """
    band = _require_positive("accept_band", accept_band)
    resolution = _require_positive("instrument_resolution", instrument_resolution)
    return band / resolution


def assess_continuity(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Judge one current-carrying path against its expected resistance."""
    validate_health_criteria(criteria)
    expected = _require_positive(
        "expected_resistance_ohm", check.get("expected_resistance_ohm")
    )
    measured = _require_non_negative(
        "measured_resistance_ohm", check.get("measured_resistance_ohm")
    )
    resolution = _require_positive("resolution_ohm", check.get("resolution_ohm"))
    band = expected * criteria["continuity_tolerance_fraction"]
    deviation = abs(measured - expected)
    ratio = discrimination_ratio(band, resolution)
    discriminating = _at_least(ratio, criteria["min_resolution_ratio"])

    reasons = []
    if _at_most(deviation, band):
        outcome = HEALTHY
    elif _at_most(deviation, band * criteria["continuity_degraded_factor"]):
        outcome = DEGRADED
        reasons.append(
            "path reads %.4f ohm against %.4f ohm expected, outside the %.4f ohm "
            "band; a joint is carrying more resistance than it was built with"
            % (measured, expected, band)
        )
    else:
        outcome = FAILED
        reasons.append(
            "path reads %.4f ohm against %.4f ohm expected; the current is not "
            "going where the design sends it" % (measured, expected)
        )
    if not discriminating:
        reasons.append(
            "the instrument resolves %.4f ohm into a %.4f ohm band, %.2f steps "
            "against the %.2f the criteria ask for, so a small degradation would "
            "not have shown"
            % (resolution, band, ratio, criteria["min_resolution_ratio"])
        )
        if outcome == HEALTHY:
            outcome = INDETERMINATE
    return {
        "outcome": outcome,
        "deviation_ohm": deviation,
        "accept_band_ohm": band,
        "discrimination_ratio": ratio,
        "discriminating": discriminating,
        "reasons": reasons,
    }


def assess_insulation(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Judge one isolation barrier, and whether it was actually stressed."""
    validate_health_criteria(criteria)
    measured = _require_positive(
        "measured_resistance_ohm", check.get("measured_resistance_ohm")
    )
    applied = _require_positive("applied_voltage_v", check.get("applied_voltage_v"))
    rated = _require_positive("rated_voltage_v", check.get("rated_voltage_v"))
    floor = criteria["min_insulation_resistance_ohm"]

    reasons = []
    if _at_least(measured, floor):
        outcome = HEALTHY
    elif _at_least(measured * criteria["insulation_degraded_factor"], floor):
        outcome = DEGRADED
        reasons.append(
            "barrier reads %.3e ohm against a %.3e ohm floor; it is still an "
            "insulator but it is on its way down" % (measured, floor)
        )
    else:
        outcome = FAILED
        reasons.append(
            "barrier reads %.3e ohm against a %.3e ohm floor; current has a path "
            "it was not given" % (measured, floor)
        )
    stressed = _at_least(applied, rated)
    if not stressed:
        reasons.append(
            "the barrier was held at %.1f V against a %.1f V rating, so it was "
            "never stressed to the level it has to survive and a defect that only "
            "opens under voltage would not have shown" % (applied, rated)
        )
        if outcome == HEALTHY:
            outcome = INDETERMINATE
    return {
        "outcome": outcome,
        "measured_resistance_ohm": measured,
        "resistance_floor_ohm": floor,
        "stressed_to_rating": stressed,
        "reasons": reasons,
    }


def assess_polarity(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Judge one polarity check: it is right or it is not."""
    validate_health_criteria(criteria)
    expected = _require_choice(
        "expected_polarity", check.get("expected_polarity"), POLARITIES
    )
    measured = _require_choice(
        "measured_polarity", check.get("measured_polarity"), POLARITIES
    )
    if expected == measured:
        return {"outcome": HEALTHY, "reasons": []}
    return {
        "outcome": FAILED,
        "reasons": [
            "the string is wired %s where %s was expected; every downstream "
            "check reads a mirror of the assembly that was built"
            % (measured, expected)
        ],
    }


def assess_bypass_diode(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Judge one bypass diode on forward drop and reverse leakage."""
    validate_health_criteria(criteria)
    drop = _require_positive("forward_drop_v", check.get("forward_drop_v"))
    leakage = _require_non_negative(
        "reverse_leakage_a", check.get("reverse_leakage_a")
    )
    low = criteria["min_diode_forward_drop_v"]
    high = criteria["max_diode_forward_drop_v"]
    leak_limit = criteria["max_diode_reverse_leakage_a"]

    reasons = []
    outcome = HEALTHY
    if not _at_least(drop, low):
        outcome = FAILED
        reasons.append(
            "forward drop %.3f V is below the %.3f V floor; the diode is closer "
            "to a short than to a junction" % (drop, low)
        )
    elif not _at_most(drop, high):
        outcome = FAILED
        reasons.append(
            "forward drop %.3f V exceeds the %.3f V limit; the diode will not "
            "take the string current when a cell shades" % (drop, high)
        )
    if not _at_most(leakage, leak_limit):
        if _at_most(leakage, leak_limit * criteria["diode_leakage_degraded_factor"]):
            outcome = _worst((outcome, DEGRADED))
            reasons.append(
                "reverse leakage %.3e A exceeds the %.3e A limit; the diode is "
                "bleeding string power in the dark" % (leakage, leak_limit)
            )
        else:
            outcome = FAILED
            reasons.append(
                "reverse leakage %.3e A is far past the %.3e A limit"
                % (leakage, leak_limit)
            )
    return {
        "outcome": outcome,
        "forward_drop_v": drop,
        "reverse_leakage_a": leakage,
        "reasons": reasons,
    }


def assess_grounding_bond(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Judge one structure bonding strap."""
    validate_health_criteria(criteria)
    measured = _require_non_negative(
        "measured_resistance_ohm", check.get("measured_resistance_ohm")
    )
    resolution = _require_positive("resolution_ohm", check.get("resolution_ohm"))
    limit = criteria["max_grounding_bond_resistance_ohm"]
    ratio = discrimination_ratio(limit, resolution)
    discriminating = _at_least(ratio, criteria["min_resolution_ratio"])

    reasons = []
    if _at_most(measured, limit):
        outcome = HEALTHY
    elif _at_most(measured, limit * criteria["grounding_degraded_factor"]):
        outcome = DEGRADED
        reasons.append(
            "bond reads %.4f ohm against the %.4f ohm limit" % (measured, limit)
        )
    else:
        outcome = FAILED
        reasons.append(
            "bond reads %.4f ohm against the %.4f ohm limit; charge has nowhere "
            "to go and the assembly will build a potential" % (measured, limit)
        )
    if not discriminating:
        reasons.append(
            "the instrument resolves %.4f ohm against a %.4f ohm limit, %.2f "
            "steps against the %.2f the criteria ask for"
            % (resolution, limit, ratio, criteria["min_resolution_ratio"])
        )
        if outcome == HEALTHY:
            outcome = INDETERMINATE
    return {
        "outcome": outcome,
        "discrimination_ratio": ratio,
        "discriminating": discriminating,
        "reasons": reasons,
    }


_ASSESSORS = {
    "continuity": assess_continuity,
    "insulation-resistance": assess_insulation,
    "polarity": assess_polarity,
    "bypass-diode-function": assess_bypass_diode,
    "grounding-bond": assess_grounding_bond,
}


def assess_check(check, criteria=DEFAULT_HEALTH_CRITERIA):
    """Route one electrical check to its assessor and return the outcome."""
    validate_health_criteria(criteria)
    if not isinstance(check, dict):
        raise ValueError("check must be a mapping, got %r" % (check,))
    kind = _require_choice("kind", check.get("kind"), CHECK_KINDS)
    check_id = _require_identifier("check id", check.get("id"))
    target = _require_identifier("check target", check.get("target"))
    for field in REQUIRED_CHECK_FIELDS[kind]:
        if check.get(field) is None:
            raise ValueError("a %s check needs %s" % (kind, field))
    result = _ASSESSORS[kind](check, criteria)
    result["id"] = check_id
    result["kind"] = kind
    result["target"] = target
    return result


def evaluate_electrical_health(assembly, criteria=DEFAULT_HEALTH_CRITERIA):
    """Clause 5.5.3.3.1 health assessment over one photovoltaic assembly.

    The assessment is the union of the checks, bounded by which paths
    and barriers they reached and by whether each instrument could have
    resolved the defect it was there to find.
    """
    validate_health_criteria(criteria)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = _require_identifier("assembly_id", assembly.get("assembly_id"))
    paths = assembly.get("declared_paths")
    barriers = assembly.get("declared_barriers")
    checks = assembly.get("checks")
    for name, value in (
        ("declared_paths", paths),
        ("declared_barriers", barriers),
        ("checks", checks),
    ):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a list, got %r" % (name, value))
    for path in paths:
        _require_identifier("declared path", path)
    for barrier in barriers:
        _require_identifier("declared barrier", barrier)
    if len(set(paths)) != len(paths):
        raise ValueError("declared_paths repeats an identifier on %s" % (assembly_id,))
    if len(set(barriers)) != len(barriers):
        raise ValueError(
            "declared_barriers repeats an identifier on %s" % (assembly_id,)
        )
    if not paths and not barriers:
        raise ValueError(
            "an assembly with no declared path and no declared barrier has "
            "nothing for the assessment to cover"
        )

    seen = set()
    assessed = []
    covered_paths = set()
    covered_barriers = set()
    for check in checks:
        result = assess_check(check, criteria)
        if result["id"] in seen:
            raise ValueError(
                "duplicate check id %r on assembly %s" % (result["id"], assembly_id)
            )
        seen.add(result["id"])
        if result["kind"] in PATH_CHECK_KINDS:
            covered_paths.add(result["target"])
        if result["kind"] in BARRIER_CHECK_KINDS:
            covered_barriers.add(result["target"])
        assessed.append(result)

    stray = sorted(
        (covered_paths - set(paths)) | (covered_barriers - set(barriers))
    )
    if stray:
        raise ValueError(
            "checks target %s, which the assembly does not declare"
            % (", ".join(stray),)
        )

    findings = []
    counts = dict((state, 0) for state in HEALTH_OUTCOMES)
    for result in assessed:
        counts[result["outcome"]] += 1
        for reason in result["reasons"]:
            findings.append("%s (%s): %s" % (result["id"], result["target"], reason))

    uncovered_paths = sorted(set(paths) - covered_paths)
    uncovered_barriers = sorted(set(barriers) - covered_barriers)
    outcome = _worst([result["outcome"] for result in assessed]) if assessed else HEALTHY
    complete = not uncovered_paths and not uncovered_barriers
    if uncovered_paths:
        findings.append(
            "%d of %d current-carrying paths were never continuity checked (%s); "
            "an unmeasured path is not a healthy one"
            % (len(uncovered_paths), len(paths), ", ".join(uncovered_paths))
        )
    if uncovered_barriers:
        findings.append(
            "%d of %d isolation barriers were never insulation checked (%s); the "
            "assessment says nothing about where current could still go"
            % (len(uncovered_barriers), len(barriers), ", ".join(uncovered_barriers))
        )
    if not complete:
        outcome = _worst((outcome, INDETERMINATE))

    denominator = len(paths) + len(barriers)
    coverage = (denominator - len(uncovered_paths) - len(uncovered_barriers)) / float(
        denominator
    )
    return {
        "assembly_id": assembly_id,
        "outcome": outcome,
        "assessment_complete": complete,
        "coverage_fraction": coverage,
        "uncovered_paths": uncovered_paths,
        "uncovered_barriers": uncovered_barriers,
        "outcome_counts": counts,
        "indeterminate_check_ids": [
            result["id"] for result in assessed if result["outcome"] == INDETERMINATE
        ],
        "unhealthy_check_ids": [
            result["id"]
            for result in assessed
            if result["outcome"] in (DEGRADED, FAILED)
        ],
        "checks": assessed,
        "findings": findings,
    }

#!/usr/bin/env python3
"""Tensile and proof-load acceptance for threaded fasteners.

Anchor: ECSS-Q-ST-70-46 testing clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Two loads come out of one geometry. The thread stress area is formed
from the nominal diameter reduced by a fixed multiple of the pitch:

    As = (pi / 4) * (d - 0.938194 * P) ** 2

Multiplying it by the proof stress of the property class gives the
proof load, a non-destructive hold the fastener must come back from
without a permanent set. Multiplying it by the minimum ultimate stress
gives the load the destructive tensile test has to reach.

Where the specimen broke decides whether the reading counts. A break in
the free threaded length or the plain shank is valid. A break inside
the grips is a fixture artefact and invalidates the specimen, which is
replaced rather than counted against the lot. A break at the
head-to-shank fillet or in the thread run-out is a defect verdict at
any load.

Every comparison against a computed bound carries a relative tolerance,
because the stress area is a float and the boundary case lands on it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

#: Relative slack on a comparison whose two sides are both computed.
LOAD_REL_TOL = 1e-9

#: Multiple of the pitch subtracted from the nominal diameter.
PITCH_FACTOR = 0.938194

#: Permanent set allowed after the proof load is released, in mm.
PERMANENT_SET_LIMIT_MM = 0.0125

FRACTURE_FREE_THREAD = "free-threaded-length"
FRACTURE_SHANK = "plain-shank"
FRACTURE_HEAD_FILLET = "head-to-shank-fillet"
FRACTURE_THREAD_RUNOUT = "thread-run-out"
FRACTURE_IN_GRIPS = "inside-the-grips"

FRACTURE_LOCATIONS = (
    FRACTURE_FREE_THREAD,
    FRACTURE_SHANK,
    FRACTURE_HEAD_FILLET,
    FRACTURE_THREAD_RUNOUT,
    FRACTURE_IN_GRIPS,
)

#: Locations that make the reading usable as a strength result.
VALID_FRACTURE_LOCATIONS = (FRACTURE_FREE_THREAD, FRACTURE_SHANK)

RESULT_PASS = "pass"
RESULT_FAIL = "fail"
RESULT_INVALID = "invalid-repeat-specimen"

VERDICT_ACCEPT = "lot-accepted"
VERDICT_REJECT = "lot-rejected"
VERDICT_NO_VALID_SPECIMEN = "no-valid-specimen"

#: proof stress and minimum ultimate stress in MPa. A class with a
#: diameter split carries a second entry keyed by the diameter above
#: which the higher pair applies.
_PROPERTY_CLASSES = {
    "8.8": {
        "proof_mpa": 580.0,
        "ultimate_mpa": 800.0,
        "split_above_mm": 16.0,
        "proof_above_mpa": 600.0,
        "ultimate_above_mpa": 830.0,
    },
    "10.9": {"proof_mpa": 830.0, "ultimate_mpa": 1040.0},
    "12.9": {"proof_mpa": 970.0, "ultimate_mpa": 1220.0},
    "A2-70": {"proof_mpa": 450.0, "ultimate_mpa": 700.0},
    "A4-80": {"proof_mpa": 600.0, "ultimate_mpa": 800.0},
}

PROPERTY_CLASSES = tuple(sorted(_PROPERTY_CLASSES))


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


def _at_least(value, bound, rel_tol=LOAD_REL_TOL):
    """value >= bound, with slack so a value landing on it passes."""
    return value >= bound - abs(bound) * rel_tol


def _at_most(value, bound, rel_tol=LOAD_REL_TOL):
    """value <= bound, with slack so a value landing on it passes."""
    return value <= bound + abs(bound) * rel_tol


def thread_stress_area(nominal_diameter_mm, pitch_mm):
    """Thread stress area in mm^2 from nominal diameter and pitch."""
    diameter = _require_positive("nominal_diameter_mm", nominal_diameter_mm)
    pitch = _require_positive("pitch_mm", pitch_mm)
    effective = diameter - PITCH_FACTOR * pitch
    if effective <= 0.0:
        raise ValueError(
            "pitch %.4f mm is too coarse for a %.4f mm thread; the stress "
            "area would not be positive" % (pitch, diameter)
        )
    return math.pi / 4.0 * effective * effective


def class_stresses(property_class, nominal_diameter_mm):
    """Proof and minimum ultimate stress in MPa for a class and size."""
    if property_class not in _PROPERTY_CLASSES:
        raise ValueError(
            "property_class must be one of %s, got %r"
            % (", ".join(PROPERTY_CLASSES), property_class)
        )
    diameter = _require_positive("nominal_diameter_mm", nominal_diameter_mm)
    spec = _PROPERTY_CLASSES[property_class]
    proof = spec["proof_mpa"]
    ultimate = spec["ultimate_mpa"]
    split = spec.get("split_above_mm")
    if split is not None and diameter > split:
        proof = spec["proof_above_mpa"]
        ultimate = spec["ultimate_above_mpa"]
    return {
        "property_class": property_class,
        "proof_mpa": proof,
        "ultimate_mpa": ultimate,
        "diameter_split_applied": bool(split is not None and diameter > split),
    }


def proof_load_n(nominal_diameter_mm, pitch_mm, property_class):
    """Proof load in newtons the fastener must return from unyielded."""
    area = thread_stress_area(nominal_diameter_mm, pitch_mm)
    stresses = class_stresses(property_class, nominal_diameter_mm)
    return stresses["proof_mpa"] * area


def min_ultimate_load_n(nominal_diameter_mm, pitch_mm, property_class):
    """Minimum breaking load in newtons the tensile test must reach."""
    area = thread_stress_area(nominal_diameter_mm, pitch_mm)
    stresses = class_stresses(property_class, nominal_diameter_mm)
    return stresses["ultimate_mpa"] * area


def permanent_set_mm(length_before_mm, length_after_mm):
    """Length the specimen kept after the proof load was released."""
    before = _require_positive("length_before_mm", length_before_mm)
    after = _require_positive("length_after_mm", length_after_mm)
    if after < before - PERMANENT_SET_LIMIT_MM:
        raise ValueError(
            "length_after_mm %.5f is shorter than length_before_mm %.5f by "
            "more than the measurement limit; check the gauge" % (after, before)
        )
    return after - before


def evaluate_proof_test(
    applied_load_n,
    required_proof_load_n,
    length_before_mm,
    length_after_mm,
    set_limit_mm=PERMANENT_SET_LIMIT_MM,
):
    """Judge one proof specimen on load reached and permanent set."""
    applied = _require_non_negative("applied_load_n", applied_load_n)
    required = _require_positive("required_proof_load_n", required_proof_load_n)
    limit = _require_positive("set_limit_mm", set_limit_mm)
    residual = permanent_set_mm(length_before_mm, length_after_mm)
    findings = []
    load_ok = _at_least(applied, required)
    if not load_ok:
        findings.append(
            "applied load %.1f N did not reach the proof load of %.1f N; the "
            "specimen was not proof tested" % (applied, required)
        )
    set_ok = _at_most(residual, limit)
    if not set_ok:
        findings.append(
            "permanent set %.5f mm exceeds the %.5f mm limit; the specimen "
            "yielded under the proof load" % (residual, limit)
        )
    return {
        "result": RESULT_PASS if (load_ok and set_ok) else RESULT_FAIL,
        "applied_load_n": applied,
        "required_proof_load_n": required,
        "permanent_set_mm": residual,
        "set_limit_mm": limit,
        "findings": findings,
    }


def fracture_is_valid(location):
    """True when a break at this location makes the load reading usable."""
    if location not in FRACTURE_LOCATIONS:
        raise ValueError(
            "fracture location must be one of %s, got %r"
            % (", ".join(FRACTURE_LOCATIONS), location)
        )
    return location in VALID_FRACTURE_LOCATIONS


def evaluate_tensile_test(breaking_load_n, required_ultimate_load_n, location):
    """Judge one tensile specimen on fracture location, then on load."""
    breaking = _require_non_negative("breaking_load_n", breaking_load_n)
    required = _require_positive(
        "required_ultimate_load_n", required_ultimate_load_n
    )
    findings = []
    if location == FRACTURE_IN_GRIPS:
        findings.append(
            "the specimen broke inside the grips; the reading measures the "
            "fixture and the specimen is replaced, not counted against the lot"
        )
        return {
            "result": RESULT_INVALID,
            "breaking_load_n": breaking,
            "required_ultimate_load_n": required,
            "fracture_location": location,
            "findings": findings,
        }
    if not fracture_is_valid(location):
        findings.append(
            "the specimen broke at the %s at %.1f N; a break outside the "
            "threaded length is a defect verdict whatever load was reached"
            % (location, breaking)
        )
        return {
            "result": RESULT_FAIL,
            "breaking_load_n": breaking,
            "required_ultimate_load_n": required,
            "fracture_location": location,
            "findings": findings,
        }
    load_ok = _at_least(breaking, required)
    if not load_ok:
        findings.append(
            "breaking load %.1f N is below the minimum ultimate load of "
            "%.1f N" % (breaking, required)
        )
    return {
        "result": RESULT_PASS if load_ok else RESULT_FAIL,
        "breaking_load_n": breaking,
        "required_ultimate_load_n": required,
        "fracture_location": location,
        "findings": findings,
    }


def assess_tensile_programme(case):
    """Roll a set of proof and tensile specimens up to a lot verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    diameter = _require_positive(
        "nominal_diameter_mm", case.get("nominal_diameter_mm")
    )
    pitch = _require_positive("pitch_mm", case.get("pitch_mm"))
    property_class = case.get("property_class")
    area = thread_stress_area(diameter, pitch)
    required_proof = proof_load_n(diameter, pitch, property_class)
    required_ultimate = min_ultimate_load_n(diameter, pitch, property_class)

    proof_specimens = case.get("proof_specimens", ())
    tensile_specimens = case.get("tensile_specimens", ())
    for name, seq in (
        ("proof_specimens", proof_specimens),
        ("tensile_specimens", tensile_specimens),
    ):
        if isinstance(seq, dict) or not isinstance(seq, (list, tuple)):
            raise ValueError("%s must be a sequence of mappings, got %r" % (name, seq))

    findings = []
    proof_results = []
    for index, specimen in enumerate(proof_specimens):
        if not isinstance(specimen, dict):
            raise ValueError("proof specimen %d must be a mapping" % index)
        outcome = evaluate_proof_test(
            specimen.get("applied_load_n"),
            required_proof,
            specimen.get("length_before_mm"),
            specimen.get("length_after_mm"),
            specimen.get("set_limit_mm", PERMANENT_SET_LIMIT_MM),
        )
        proof_results.append(outcome)
        for note in outcome["findings"]:
            findings.append("proof specimen %d: %s" % (index + 1, note))

    tensile_results = []
    for index, specimen in enumerate(tensile_specimens):
        if not isinstance(specimen, dict):
            raise ValueError("tensile specimen %d must be a mapping" % index)
        outcome = evaluate_tensile_test(
            specimen.get("breaking_load_n"),
            required_ultimate,
            specimen.get("fracture_location"),
        )
        tensile_results.append(outcome)
        for note in outcome["findings"]:
            findings.append("tensile specimen %d: %s" % (index + 1, note))

    valid_tensile = [r for r in tensile_results if r["result"] != RESULT_INVALID]
    invalid_count = len(tensile_results) - len(valid_tensile)
    if invalid_count:
        findings.append(
            "%d tensile specimen(s) invalidated by the fixture and owed as "
            "replacements" % invalid_count
        )

    if not proof_results and not valid_tensile:
        return {
            "stress_area_mm2": area,
            "required_proof_load_n": required_proof,
            "required_ultimate_load_n": required_ultimate,
            "proof_results": proof_results,
            "tensile_results": tensile_results,
            "invalid_specimens": invalid_count,
            "worst_breaking_load_n": None,
            "findings": findings + ["no valid specimen to judge the lot on"],
            "verdict": VERDICT_NO_VALID_SPECIMEN,
        }

    worst = min((r["breaking_load_n"] for r in valid_tensile), default=None)
    failed = [r for r in proof_results + valid_tensile if r["result"] == RESULT_FAIL]
    return {
        "stress_area_mm2": area,
        "required_proof_load_n": required_proof,
        "required_ultimate_load_n": required_ultimate,
        "proof_results": proof_results,
        "tensile_results": tensile_results,
        "invalid_specimens": invalid_count,
        "worst_breaking_load_n": worst,
        "findings": findings,
        "verdict": VERDICT_REJECT if failed else VERDICT_ACCEPT,
    }

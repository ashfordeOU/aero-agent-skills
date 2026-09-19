#!/usr/bin/env python3
"""Acceptance of a brazed joint against the limits its class carries.

Anchor: the acceptance provisions of the ECSS brazing standard. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Acceptance is a set of criteria read together, and each one points in
a direction:

    fill fraction              a floor    the joint must reach it
    total void area fraction   a ceiling  the joint must stay under it
    largest single void        a ceiling
    longest continuous run     a ceiling
    indication count           a ceiling

Some defects are not gradeable at all. A crack is rejected in every
class whatever the measured fill says, and a disbond at the loaded edge
of an overlap is rejected in the structural classes.

A measurement sitting exactly on a limit is acceptable: fractions are
quotients of measured areas and lengths, so a joint built deliberately
to a limit can land a few units in the last place on the wrong side of
it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BRAZE_CLASSES = ("class-a", "class-b", "class-c")
STRUCTURAL_CLASSES = ("class-a", "class-b")

FLOOR = "floor"
CEILING = "ceiling"

CRITERION_SENSE = {
    "fill_fraction": FLOOR,
    "total_void_area_fraction": CEILING,
    "largest_single_void_fraction": CEILING,
    "longest_linear_void_fraction": CEILING,
    "indication_count": CEILING,
}

ACCEPTANCE_LIMITS = {
    "class-a": {
        "fill_fraction": 0.90,
        "total_void_area_fraction": 0.10,
        "largest_single_void_fraction": 0.05,
        "longest_linear_void_fraction": 0.10,
        "indication_count": 3,
    },
    "class-b": {
        "fill_fraction": 0.80,
        "total_void_area_fraction": 0.20,
        "largest_single_void_fraction": 0.10,
        "longest_linear_void_fraction": 0.15,
        "indication_count": 6,
    },
    "class-c": {
        "fill_fraction": 0.70,
        "total_void_area_fraction": 0.30,
        "largest_single_void_fraction": 0.20,
        "longest_linear_void_fraction": 0.25,
        "indication_count": 10,
    },
}

CRACK = "crack"
LOADED_EDGE_DISBOND = "loaded-edge-disbond"
DEFECT_TYPES = (
    CRACK,
    LOADED_EDGE_DISBOND,
    "scattered-porosity",
    "flux-entrapment",
    "excess-filler",
    "base-metal-erosion",
)

# Defects whose limit is their existence rather than their size.
ALWAYS_REJECTED = (CRACK,)
STRUCTURAL_CLASS_REJECTED = (LOADED_EDGE_DISBOND,)

ACCEPT = "brazement-accepted"
REJECT = "brazement-rejected"

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


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A fill fraction is a quotient of measured areas, so a joint built
    deliberately to the limit can land a few units in the last place
    below it. The limit is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def acceptance_limits(braze_class):
    """Limits the joint class sets, with the direction of each criterion."""
    _require_choice("braze_class", braze_class, BRAZE_CLASSES)
    return {
        name: {"limit": limit, "sense": CRITERION_SENSE[name]}
        for name, limit in ACCEPTANCE_LIMITS[braze_class].items()
    }


def fill_fraction_from_areas(joint_area_mm2, voided_area_mm2):
    """Filled share of the joint computed from the measured areas."""
    joint = _require_positive("joint_area_mm2", joint_area_mm2)
    if not _is_finite_number(voided_area_mm2):
        raise ValueError(
            "voided_area_mm2 must be a finite number, got %r" % (voided_area_mm2,)
        )
    if voided_area_mm2 < 0.0:
        raise ValueError(
            "voided_area_mm2 must not be negative, got %r" % (voided_area_mm2,)
        )
    if voided_area_mm2 > joint:
        raise ValueError(
            "voided area %g mm2 exceeds the joint area %g mm2; the measurement "
            "set is inconsistent" % (float(voided_area_mm2), joint)
        )
    return (joint - float(voided_area_mm2)) / joint


def grade_criterion(name, measured, limit):
    """Grade one criterion in its own direction and report the margin."""
    sense = CRITERION_SENSE.get(name)
    if sense is None:
        raise ValueError(
            "unknown criterion %r; expected one of %s"
            % (name, ", ".join(sorted(CRITERION_SENSE)))
        )
    if sense == FLOOR:
        compliant = _at_least(measured, limit)
        margin = measured - limit
    else:
        compliant = _at_most(measured, limit)
        margin = limit - measured
    relative = margin / float(limit) if limit else float(margin)
    return {
        "criterion": name,
        "sense": sense,
        "measured": measured,
        "limit": limit,
        "compliant": compliant,
        "margin": margin,
        "relative_margin": relative,
    }


def non_gradeable_findings(defect_types, braze_class):
    """Defects rejected on existence rather than on size."""
    _require_choice("braze_class", braze_class, BRAZE_CLASSES)
    if not isinstance(defect_types, (list, tuple)):
        raise ValueError("defect_types must be a sequence, got %r" % (defect_types,))
    findings = []
    for defect in defect_types:
        _require_choice("defect type", defect, DEFECT_TYPES)
        if defect in ALWAYS_REJECTED:
            findings.append(
                "a %s is rejected in every class whatever the measured fill" % defect
            )
        elif defect in STRUCTURAL_CLASS_REJECTED and braze_class in STRUCTURAL_CLASSES:
            findings.append(
                "a %s is rejected in %s because the overlap edge carries the load"
                % (defect, braze_class)
            )
    return findings


def normalise_measurement(measurement):
    """Normalise one inspection record and reject an impossible set."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    braze_class = _require_choice(
        "braze_class", measurement.get("braze_class"), BRAZE_CLASSES
    )
    if "joint_area_mm2" in measurement:
        fill = fill_fraction_from_areas(
            measurement.get("joint_area_mm2"), measurement.get("voided_area_mm2", 0.0)
        )
        fill_source = "computed-from-areas"
    elif "fill_fraction" in measurement:
        fill = _require_fraction("fill_fraction", measurement.get("fill_fraction"))
        fill_source = "declared"
    else:
        raise ValueError(
            "measurement needs either a joint_area_mm2 pair or a fill_fraction"
        )
    total_void = _require_fraction(
        "total_void_area_fraction", measurement.get("total_void_area_fraction", 0.0)
    )
    largest = _require_fraction(
        "largest_single_void_fraction",
        measurement.get("largest_single_void_fraction", 0.0),
    )
    longest = _require_fraction(
        "longest_linear_void_fraction",
        measurement.get("longest_linear_void_fraction", 0.0),
    )
    count = _require_count("indication_count", measurement.get("indication_count", 0))
    defects = list(measurement.get("defect_types", ()))
    if largest > total_void and total_void > 0.0:
        raise ValueError(
            "the largest single void fraction %g exceeds the total void area "
            "fraction %g; the measurement set is inconsistent" % (largest, total_void)
        )
    if count == 0 and total_void > 0.0:
        raise ValueError(
            "a non-zero void area was recorded with no indications counted; the "
            "measurement set is inconsistent"
        )
    return {
        "id": measurement.get("id"),
        "braze_class": braze_class,
        "fill_fraction": fill,
        "fill_source": fill_source,
        "total_void_area_fraction": total_void,
        "largest_single_void_fraction": largest,
        "longest_linear_void_fraction": longest,
        "indication_count": count,
        "defect_types": defects,
    }


def assess_brazement(measurement):
    """Accept or reject one brazement and name the binding criterion."""
    record = normalise_measurement(measurement)
    braze_class = record["braze_class"]
    limits = ACCEPTANCE_LIMITS[braze_class]
    criteria = {}
    for name, limit in limits.items():
        criteria[name] = grade_criterion(name, record[name], limit)

    findings = non_gradeable_findings(record["defect_types"], braze_class)
    failed = [c for c in criteria.values() if not c["compliant"]]

    if findings:
        verdict = REJECT
        binding = "non-gradeable-defect"
    elif failed:
        verdict = REJECT
        binding = min(failed, key=lambda c: c["relative_margin"])["criterion"]
        for criterion in sorted(failed, key=lambda c: c["relative_margin"]):
            findings.append(
                "%s measured %.6g against a %s limit of %.6g"
                % (
                    criterion["criterion"],
                    criterion["measured"],
                    criterion["sense"],
                    criterion["limit"],
                )
            )
    else:
        verdict = ACCEPT
        binding = min(
            criteria.values(), key=lambda c: c["relative_margin"]
        )["criterion"]

    return {
        "id": record["id"],
        "braze_class": braze_class,
        "fill_fraction": record["fill_fraction"],
        "fill_source": record["fill_source"],
        "criteria": criteria,
        "verdict": verdict,
        "accepted": verdict == ACCEPT,
        "binding_criterion": binding,
        "findings": findings,
    }


def grade_lot(measurements):
    """Roll a set of brazements up to accepted, rejected and the worst case."""
    if not isinstance(measurements, (list, tuple)) or not measurements:
        raise ValueError("measurements must be a non-empty sequence")
    results = [assess_brazement(m) for m in measurements]
    accepted = [r for r in results if r["accepted"]]
    rejected = [r for r in results if not r["accepted"]]
    binding_counts = {}
    for result in rejected:
        binding_counts[result["binding_criterion"]] = (
            binding_counts.get(result["binding_criterion"], 0) + 1
        )
    return {
        "results": results,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "acceptance_fraction": len(accepted) / float(len(results)),
        "binding_criterion_counts": binding_counts,
    }

#!/usr/bin/env python3
"""Adequacy of the equipment and viewing approach used to inspect cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is about the instrument, not the verdict. It asks what
resolution the inspection equipment provides and how the assembly is
looked at. Both are bounds on every defect call that comes afterwards:
an examination cannot report a feature it could not resolve, and a face
nobody viewed contributes nothing whatever the equipment was capable of.

Resolution comes out of the station, and the three station kinds reach
it by different arithmetic.

An unaided station is limited by the eye. The angular acuity converted
to a length at the working distance is the smallest feature it can
show, so standing further back coarsens it in direct proportion.

A magnified station divides that length by its power. A station calling
itself magnified and running at unity is an unaided one with a lens in
front of it, and is rejected rather than credited with a magnification
it does not have.

An imaging station is limited by sampling. The field of view spread
over the sensor gives a pixel pitch at the article, and a feature needs
more than one pixel to exist in the image, so the resolved feature is
the pitch times the samples a feature is required to span.

The viewing approach then degrades whatever the station produced.
Looking at a surface off its normal foreshortens it: a feature of a
given extent presents a shorter one to the instrument by the cosine of
the incidence angle, so the effective resolved feature grows as the
reciprocal of that cosine. At sixty degrees off normal a station
resolves twice as coarsely as its datasheet says. Illumination is the
other half -- below an illuminance floor a look stops being a detection
activity regardless of optics.

Adequacy is then a margin question against the smallest feature the
defect criteria name. Resolving a feature exactly at its own size is
not detection, it is a coincidence, so a station is credited only when
it resolves the feature several times over, and a station that lands
between those two points is marginal rather than capable.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STATION_KINDS = ("unaided-visual", "magnified-visual", "imaging-camera")

CAPABLE = "capable"
MARGINAL = "marginal"
REFER = "refer-for-review"
NOT_CAPABLE = "not-capable"
STATION_VERDICTS = (CAPABLE, MARGINAL, REFER, NOT_CAPABLE)

PROCESS_ADEQUATE = "process-adequate"
PROCESS_INADEQUATE = "process-inadequate"

_VERDICT_ORDER = {CAPABLE: 0, MARGINAL: 1, REFER: 2, NOT_CAPABLE: 3}

DEFAULT_INSPECTION_POLICY = {
    "unaided_acuity_arcmin": 1.0,
    "samples_per_feature": 2.0,
    "detection_margin": 3.0,
    "min_illuminance_lux": 1000.0,
    "max_incidence_angle_deg": 60.0,
    "max_working_distance_mm": 500.0,
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


def _require_angle(name, value):
    angle = _require_non_negative(name, value)
    if angle >= 90.0:
        raise ValueError(
            "%s must be under ninety degrees; at ninety the instrument looks "
            "along the surface and sees no extent at all, got %r" % (name, value)
        )
    return angle


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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A resolved feature comes out of a trigonometric conversion and a
    cosine division, and the required feature is a quotient of a
    criterion and a margin, so a station sitting exactly on a bound can
    evaluate a few units in the last place above it. The bound is never
    relaxed; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(verdicts):
    worst = CAPABLE
    for verdict in verdicts:
        if _VERDICT_ORDER[verdict] > _VERDICT_ORDER[worst]:
            worst = verdict
    return worst


def validate_inspection_policy(policy):
    """Check an inspection-adequacy policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "unaided_acuity_arcmin",
        "samples_per_feature",
        "detection_margin",
        "min_illuminance_lux",
        "max_working_distance_mm",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    margin = policy["detection_margin"]
    if margin < 1.0:
        raise ValueError(
            "policy detection_margin must be at least one; a margin below unity "
            "would credit a station that cannot resolve the feature at all, "
            "got %r" % (margin,)
        )
    samples = policy["samples_per_feature"]
    if samples < 2.0:
        raise ValueError(
            "policy samples_per_feature must be at least two; a feature landing "
            "on a single pixel is not distinguishable from noise, got %r"
            % (samples,)
        )
    _require_angle(
        "policy max_incidence_angle_deg", policy.get("max_incidence_angle_deg")
    )
    return policy


def unaided_resolved_feature_mm(working_distance_mm, acuity_arcmin=1.0):
    """Smallest feature the unaided eye can show at a working distance."""
    distance = _require_positive("working_distance_mm", working_distance_mm)
    acuity = _require_positive("acuity_arcmin", acuity_arcmin)
    angle_rad = math.radians(acuity / 60.0)
    return 2.0 * distance * math.tan(angle_rad / 2.0)


def sampled_resolved_feature_mm(field_of_view_mm, pixel_count, samples_per_feature=2.0):
    """Smallest feature an imaging station can show, set by sensor sampling."""
    field = _require_positive("field_of_view_mm", field_of_view_mm)
    pixels = _require_count("pixel_count", pixel_count)
    samples = _require_positive("samples_per_feature", samples_per_feature)
    if samples < 2.0:
        raise ValueError(
            "samples_per_feature must be at least two, got %r" % (samples_per_feature,)
        )
    return samples * field / float(pixels)


def station_resolved_feature_mm(station, policy=DEFAULT_INSPECTION_POLICY):
    """Resolved feature of one station, before the viewing approach degrades it."""
    validate_inspection_policy(policy)
    if not isinstance(station, dict):
        raise ValueError("station must be a mapping, got %r" % (station,))
    kind = _require_choice("kind", station.get("kind"), STATION_KINDS)
    if kind == "imaging-camera":
        return sampled_resolved_feature_mm(
            station.get("field_of_view_mm"),
            station.get("pixel_count"),
            policy["samples_per_feature"],
        )
    unaided = unaided_resolved_feature_mm(
        station.get("working_distance_mm"), policy["unaided_acuity_arcmin"]
    )
    magnification = _require_positive(
        "magnification", station.get("magnification", 1.0)
    )
    if kind == "unaided-visual":
        if not math.isclose(magnification, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            raise ValueError(
                "an unaided station runs at unity magnification; %r describes an "
                "aided one and belongs to the magnified kind" % (magnification,)
            )
        return unaided
    if magnification <= 1.0 or math.isclose(
        magnification, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "a magnified station must magnify; %r is an unaided station with a "
            "lens in front of it" % (magnification,)
        )
    return unaided / magnification


def assess_inspection_station(
    station, smallest_criterion_mm, policy=DEFAULT_INSPECTION_POLICY
):
    """Judge whether one station and its viewing approach can carry defect calls."""
    validate_inspection_policy(policy)
    if not isinstance(station, dict):
        raise ValueError("station must be a mapping, got %r" % (station,))
    station_id = _require_identifier("station_id", station.get("station_id"))
    kind = _require_choice("kind", station.get("kind"), STATION_KINDS)
    criterion = _require_positive("smallest_criterion_mm", smallest_criterion_mm)
    illuminance = _require_non_negative(
        "illuminance_lux", station.get("illuminance_lux")
    )
    incidence = _require_angle(
        "incidence_angle_deg", station.get("incidence_angle_deg", 0.0)
    )
    faces = station.get("faces_examined")
    if not isinstance(faces, (list, tuple)) or not faces:
        raise ValueError(
            "station %s must name at least one face it examines, got %r"
            % (station_id, faces)
        )
    for face in faces:
        _require_identifier("face", face)
    if len(set(faces)) != len(faces):
        raise ValueError("station %s repeats a face: %r" % (station_id, faces))

    resolved = station_resolved_feature_mm(station, policy)
    foreshortening = math.cos(math.radians(incidence))
    effective = resolved / foreshortening
    required = criterion / policy["detection_margin"]

    findings = []
    if _at_most(effective, required):
        verdict = CAPABLE
    elif _at_most(effective, criterion):
        verdict = MARGINAL
        findings.append(
            "resolves %.5f mm against a %.5f mm criterion; it can show the "
            "feature but not with the %.1fx margin a defect call rests on"
            % (effective, criterion, policy["detection_margin"])
        )
    else:
        verdict = NOT_CAPABLE
        findings.append(
            "resolves %.5f mm against a %.5f mm criterion, so a defect at the "
            "criterion size would not appear at all" % (effective, criterion)
        )

    conditions_met = True
    if not _at_least(illuminance, policy["min_illuminance_lux"]):
        conditions_met = False
        findings.append(
            "lit to %.0f lux against a %.0f lux floor; under the floor a look "
            "stops being a detection activity whatever the optics do"
            % (illuminance, policy["min_illuminance_lux"])
        )
    if not _at_most(incidence, policy["max_incidence_angle_deg"]):
        conditions_met = False
        findings.append(
            "viewed %.1f degrees off normal against a %.1f degree limit; the "
            "foreshortening already coarsened the station by %.2fx"
            % (
                incidence,
                policy["max_incidence_angle_deg"],
                1.0 / foreshortening,
            )
        )
    if kind != "imaging-camera":
        distance = _require_positive(
            "working_distance_mm", station.get("working_distance_mm")
        )
        if not _at_most(distance, policy["max_working_distance_mm"]):
            conditions_met = False
            findings.append(
                "stood off %.1f mm against a %.1f mm working distance; the "
                "resolved feature grows in direct proportion"
                % (distance, policy["max_working_distance_mm"])
            )
    if not conditions_met:
        verdict = _worst((verdict, REFER))

    return {
        "station_id": station_id,
        "kind": kind,
        "verdict": verdict,
        "credited": verdict == CAPABLE,
        "conditions_met": conditions_met,
        "resolved_feature_mm": resolved,
        "effective_resolved_feature_mm": effective,
        "foreshortening_factor": 1.0 / foreshortening,
        "required_feature_mm": required,
        "faces_examined": list(faces),
        "findings": findings,
    }


def qualify_inspection_process(process, policy=DEFAULT_INSPECTION_POLICY):
    """Clause 6.4.3.1.2 adequacy of a whole cell assembly inspection setup."""
    validate_inspection_policy(policy)
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    assembly_id = _require_identifier("assembly_id", process.get("assembly_id"))
    criterion = _require_positive(
        "smallest_criterion_mm", process.get("smallest_criterion_mm")
    )
    declared = process.get("declared_faces")
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError(
            "assembly %s must declare the faces the defect rules cover, got %r"
            % (assembly_id, declared)
        )
    for face in declared:
        _require_identifier("declared face", face)
    if len(set(declared)) != len(declared):
        raise ValueError("assembly %s repeats a declared face" % (assembly_id,))
    stations = process.get("stations")
    if not isinstance(stations, (list, tuple)) or not stations:
        raise ValueError(
            "assembly %s carries no inspection stations; an unspecified setup "
            "cannot be shown adequate" % (assembly_id,)
        )

    seen = set()
    assessed = []
    for station in stations:
        result = assess_inspection_station(station, criterion, policy)
        marker = result["station_id"]
        if marker in seen:
            raise ValueError(
                "duplicate station id %r on assembly %s" % (marker, assembly_id)
            )
        seen.add(marker)
        for face in result["faces_examined"]:
            if face not in declared:
                raise ValueError(
                    "station %s examines %r, which is not a declared face of %s"
                    % (marker, face, assembly_id)
                )
        assessed.append(result)

    findings = []
    counts = dict((verdict, 0) for verdict in STATION_VERDICTS)
    face_bound = {}
    for result in assessed:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s: %s" % (result["station_id"], finding))
        if not result["credited"]:
            continue
        for face in result["faces_examined"]:
            bound = result["effective_resolved_feature_mm"]
            if face not in face_bound or bound < face_bound[face]:
                face_bound[face] = bound

    uncovered = [face for face in declared if face not in face_bound]
    for face in uncovered:
        findings.append(
            "face %s is reached by no credited station; a defect there would not "
            "be found and the inspection says nothing about it" % (face,)
        )

    verdict = _worst([result["verdict"] for result in assessed])
    adequate = not uncovered and verdict == CAPABLE
    bounded_at = max(face_bound.values()) if face_bound else None
    if bounded_at is not None:
        findings.append(
            "every defect call from this setup is bounded at %.5f mm; nothing "
            "smaller was either found or ruled out" % (bounded_at,)
        )
    return {
        "assembly_id": assembly_id,
        "verdict": PROCESS_ADEQUATE if adequate else PROCESS_INADEQUATE,
        "worst_station_verdict": verdict,
        "process_adequate": adequate,
        "smallest_criterion_mm": criterion,
        "station_verdict_counts": counts,
        "face_bound_mm": face_bound,
        "uncovered_faces": uncovered,
        "not_credited_ids": [
            result["station_id"] for result in assessed if not result["credited"]
        ],
        "statement_bounded_at_mm": bounded_at,
        "stations": assessed,
        "findings": findings,
    }

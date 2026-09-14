#!/usr/bin/env python3
"""Coverglass scratch and dig graded against the source control drawing.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The largest scratch and the largest dig a solar-cell coverglass is
allowed to carry are not general numbers. They are fixed by the source
control drawing for that coverglass, so the drawing is an input to this
screen and not a default inside it: with no drawing in hand there is no
limit to grade against, and a house figure substituted for the missing
one grades the part against a requirement nobody imposed.

A drawing states the limits as a scratch grade and a dig grade. A grade
is a designation, not a length, and it becomes a length only through the
unit the drawing declares:

    scratch     the permitted apparent width of a scratch, one grade
                step being one scratch unit of width
    dig         the permitted diameter of a dig, one grade step being
                one dig unit of diameter

so a measured width or diameter in millimetres is converted to a grade
before anything is compared, and a grade is never compared with a
millimetre.

The largest feature is not the only question the drawing answers. A face
carrying nothing oversize can still carry too much of it, so the graded
scratches are summed as length weighted by their grade and the graded
digs are summed as grade over the aperture, and both go against their own
allowance.

Features inside the declared edge exclusion band are outside the optical
path: they are reported rather than graded. A coverglass that was never
examined is not a clean coverglass; it is an ungraded one, and an empty
feature list means examined and clean while no feature list at all means
not examined.

Dispositions are accept, review -- meaning referred to the drawing
authority, because a scratch cannot be worked out of glass -- and reject.
The review margins below are a declared project convention, not part of
the drawing; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
import re

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
COVERGLASS_DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

SCRATCH = "scratch"
DIG = "dig"
FEATURE_KINDS = (SCRATCH, DIG)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

DIG_CONCENTRATION_BASE_MM = 20.0

DESIGNATION_PATTERN = re.compile(r"^\s*(\d{1,3})\s*[-/]\s*(\d{1,3})\s*$")

DEFAULT_SCRATCH_UNIT_MM = 0.001
DEFAULT_DIG_UNIT_MM = 0.01

DEFAULT_SCRATCH_DIG_MARGINS = {
    "review_margin_factor": 1.5,
    "max_affected_coverglass_fraction": 0.05,
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


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A grade is a measured millimetre figure divided by a declared unit of
    a thousandth or a hundredth of a millimetre, and neither the unit nor
    the quotient is exactly representable, so a feature measured exactly
    at the drawing limit can evaluate a few units in the last place past
    its grade, and it lands differently on different machines. The
    drawing limit is never moved; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def _validate_margins(margins):
    if not isinstance(margins, dict):
        raise ValueError("margins must be a mapping, got %r" % (margins,))
    factor = margins.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "margins review_margin_factor must be at least one, got %r" % (factor,)
        )
    _require_fraction(
        "margins max_affected_coverglass_fraction",
        margins.get("max_affected_coverglass_fraction"),
    )
    return margins


def parse_scratch_dig_designation(designation):
    """Split a drawing designation such as 60-40 into its two grades.

    The first number is the scratch grade and the second the dig grade.
    They are designations: neither is a length until the drawing's units
    are applied to it.
    """
    _require_text("designation", designation)
    match = DESIGNATION_PATTERN.match(designation)
    if not match:
        raise ValueError(
            "scratch-dig designation %r is not two numbers separated by a dash "
            "or a slash, so the drawing limit cannot be read from it"
            % (designation,)
        )
    scratch_grade = int(match.group(1))
    dig_grade = int(match.group(2))
    if scratch_grade <= 0 or dig_grade <= 0:
        raise ValueError(
            "scratch-dig designation %r carries a zero grade; a zero limit "
            "permits no feature at all and is not a drawing callout"
            % (designation,)
        )
    return {"scratch_grade": scratch_grade, "dig_grade": dig_grade}


def validate_source_control_drawing(drawing):
    """Check the drawing carries the limits this screen is graded against."""
    if not isinstance(drawing, dict):
        raise ValueError(
            "the source control drawing must be supplied as a mapping, got %r; "
            "the scratch and dig limits belong to the drawing and there is no "
            "default to fall back on" % (drawing,)
        )
    _require_text("drawing_id", drawing.get("drawing_id"))
    _require_text("revision", drawing.get("revision"))
    designation = drawing.get("designation")
    grades = parse_scratch_dig_designation(designation)
    for key, value in (
        ("scratch_unit_mm", drawing.get("scratch_unit_mm", DEFAULT_SCRATCH_UNIT_MM)),
        ("dig_unit_mm", drawing.get("dig_unit_mm", DEFAULT_DIG_UNIT_MM)),
        ("aperture_reference_mm", drawing.get("aperture_reference_mm")),
    ):
        _require_positive(key, value)
    _require_non_negative(
        "edge_exclusion_mm", drawing.get("edge_exclusion_mm", 0.0)
    )
    _require_positive(
        "aggregate_scratch_length_fraction",
        drawing.get("aggregate_scratch_length_fraction"),
    )
    _require_positive(
        "dig_concentration_factor", drawing.get("dig_concentration_factor")
    )
    if drawing["aggregate_scratch_length_fraction"] > 1.0:
        raise ValueError(
            "the drawing permits a summed scratch length of %r of the aperture "
            "reference dimension, which is more scratch than there is aperture"
            % (drawing["aggregate_scratch_length_fraction"],)
        )
    if drawing.get("edge_exclusion_mm", 0.0) * 2.0 >= drawing["aperture_reference_mm"]:
        raise ValueError(
            "an edge exclusion band of %r mm a side consumes an aperture "
            "reference of %r mm, leaving nothing to grade"
            % (drawing.get("edge_exclusion_mm", 0.0), drawing["aperture_reference_mm"])
        )
    return grades


def drawing_limits(drawing):
    """Drawing grades resolved into the millimetre figures they mean."""
    grades = validate_source_control_drawing(drawing)
    scratch_unit = float(drawing.get("scratch_unit_mm", DEFAULT_SCRATCH_UNIT_MM))
    dig_unit = float(drawing.get("dig_unit_mm", DEFAULT_DIG_UNIT_MM))
    reference = float(drawing["aperture_reference_mm"])
    return {
        "drawing_id": drawing["drawing_id"],
        "revision": drawing["revision"],
        "designation": drawing["designation"],
        "max_scratch_grade": float(grades["scratch_grade"]),
        "max_dig_grade": float(grades["dig_grade"]),
        "scratch_unit_mm": scratch_unit,
        "dig_unit_mm": dig_unit,
        "max_scratch_width_mm": grades["scratch_grade"] * scratch_unit,
        "max_dig_diameter_mm": grades["dig_grade"] * dig_unit,
        "aperture_reference_mm": reference,
        "edge_exclusion_mm": float(drawing.get("edge_exclusion_mm", 0.0)),
        "max_summed_scratch_length_mm": (
            float(drawing["aggregate_scratch_length_fraction"]) * reference
        ),
        "max_summed_dig_grade": (
            float(drawing["dig_concentration_factor"])
            * grades["dig_grade"]
            * (reference / DIG_CONCENTRATION_BASE_MM)
        ),
    }


def scratch_grade_from_width(width_mm, drawing):
    """A measured scratch width expressed in the drawing's scratch grade."""
    limits = drawing_limits(drawing)
    width = _require_positive("scratch width_mm", width_mm)
    return width / limits["scratch_unit_mm"]


def dig_grade_from_diameter(diameter_mm, drawing):
    """A measured dig diameter expressed in the drawing's dig grade."""
    limits = drawing_limits(drawing)
    diameter = _require_positive("dig diameter_mm", diameter_mm)
    return diameter / limits["dig_unit_mm"]


def measure_feature(feature, drawing):
    """One observed surface feature reduced to its grade and its place."""
    limits = drawing_limits(drawing)
    if not isinstance(feature, dict):
        raise ValueError("feature must be a mapping, got %r" % (feature,))
    kind = feature.get("kind")
    if kind not in FEATURE_KINDS:
        raise ValueError(
            "feature kind must be one of %s, got %r"
            % (", ".join(FEATURE_KINDS), kind)
        )
    band = limits["edge_exclusion_mm"]
    distance = _require_non_negative(
        "distance_from_edge_mm", feature.get("distance_from_edge_mm", band)
    )
    in_aperture = distance >= band or math.isclose(
        distance, band, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    measured = {
        "kind": kind,
        "distance_from_edge_mm": distance,
        "in_active_aperture": in_aperture,
    }
    if kind == SCRATCH:
        width = _require_positive("scratch width_mm", feature.get("width_mm"))
        length = _require_positive("scratch length_mm", feature.get("length_mm"))
        if length > limits["aperture_reference_mm"] and not math.isclose(
            length, limits["aperture_reference_mm"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "a scratch %r mm long was recorded on an aperture whose "
                "reference dimension is %r mm; one of the two is wrong"
                % (length, limits["aperture_reference_mm"])
            )
        measured["width_mm"] = width
        measured["length_mm"] = length
        measured["grade"] = width / limits["scratch_unit_mm"]
        measured["grade_limit"] = limits["max_scratch_grade"]
    else:
        diameter = _require_positive("dig diameter_mm", feature.get("diameter_mm"))
        measured["diameter_mm"] = diameter
        measured["grade"] = diameter / limits["dig_unit_mm"]
        measured["grade_limit"] = limits["max_dig_grade"]
    measured["within_grade_limit"] = _at_most(
        measured["grade"], measured["grade_limit"]
    )
    return measured


def screen_surface_features(features, drawing):
    """Measured features grouped by kind, with the two aggregate sums."""
    limits = drawing_limits(drawing)
    if not isinstance(features, (list, tuple)):
        raise ValueError("features must be a list, got %r" % (features,))
    scratches = []
    digs = []
    in_band = []
    for feature in features:
        measured = measure_feature(feature, drawing)
        if not measured["in_active_aperture"]:
            in_band.append(measured)
        elif measured["kind"] == SCRATCH:
            scratches.append(measured)
        else:
            digs.append(measured)
    weighted_length = math.fsum(
        item["length_mm"] * item["grade"] / limits["max_scratch_grade"]
        for item in scratches
    )
    summed_dig_grade = math.fsum(item["grade"] for item in digs)
    worst_scratch = max((item["grade"] for item in scratches), default=0.0)
    worst_dig = max((item["grade"] for item in digs), default=0.0)
    return {
        "scratches": scratches,
        "digs": digs,
        "edge_band_features": in_band,
        "scratch_count": len(scratches),
        "dig_count": len(digs),
        "edge_band_count": len(in_band),
        "worst_scratch_grade": worst_scratch,
        "worst_dig_grade": worst_dig,
        "weighted_scratch_length_mm": weighted_length,
        "summed_dig_grade": summed_dig_grade,
        "max_summed_scratch_length_mm": limits["max_summed_scratch_length_mm"],
        "max_summed_dig_grade": limits["max_summed_dig_grade"],
    }


def assess_coverglass_scratch_and_dig(
    record, drawing, margins=DEFAULT_SCRATCH_DIG_MARGINS
):
    """Grade one coverglass against the drawing's scratch and dig limits."""
    _validate_margins(margins)
    limits = drawing_limits(drawing)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    coverglass_id = _require_text("coverglass_id", record.get("coverglass_id"))
    part_drawing = _require_text(
        "drawing_id on %s" % coverglass_id, record.get("drawing_id")
    )
    if part_drawing != limits["drawing_id"]:
        raise ValueError(
            "%s is built to drawing %r while the drawing in hand is %r; the "
            "scratch and dig limits of one part are not the limits of another"
            % (coverglass_id, part_drawing, limits["drawing_id"])
        )
    part_revision = _require_text(
        "drawing_revision on %s" % coverglass_id, record.get("drawing_revision")
    )
    if part_revision != limits["revision"]:
        raise ValueError(
            "%s was released against revision %r of drawing %s while the "
            "limits in hand are revision %r; a superseded limit is not the "
            "limit the part was accepted to"
            % (coverglass_id, part_revision, part_drawing, limits["revision"])
        )

    features = record.get("features")
    examined = isinstance(features, (list, tuple))
    findings = []
    dispositions = [ACCEPT]
    factor = margins["review_margin_factor"]
    screen = None

    if examined:
        screen = screen_surface_features(features, drawing)
        for item in screen["scratches"] + screen["digs"]:
            if item["within_grade_limit"]:
                continue
            if _at_most(item["grade"], item["grade_limit"] * factor):
                dispositions.append(REVIEW)
            else:
                dispositions.append(REJECT)
            findings.append(
                "a %s grades %.2f against the %.2f the drawing fixes"
                % (item["kind"], item["grade"], item["grade_limit"])
            )
        if not _at_most(
            screen["weighted_scratch_length_mm"],
            screen["max_summed_scratch_length_mm"],
        ):
            if _at_most(
                screen["weighted_scratch_length_mm"],
                screen["max_summed_scratch_length_mm"] * factor,
            ):
                dispositions.append(REVIEW)
            else:
                dispositions.append(REJECT)
            findings.append(
                "the scratches sum to %.4f mm of grade-weighted length against "
                "the %.4f mm the drawing permits, although each one is within "
                "its own limit"
                % (
                    screen["weighted_scratch_length_mm"],
                    screen["max_summed_scratch_length_mm"],
                )
            )
        if not _at_most(screen["summed_dig_grade"], screen["max_summed_dig_grade"]):
            if _at_most(
                screen["summed_dig_grade"], screen["max_summed_dig_grade"] * factor
            ):
                dispositions.append(REVIEW)
            else:
                dispositions.append(REJECT)
            findings.append(
                "the digs sum to grade %.2f across the aperture against the "
                "%.2f the drawing permits"
                % (screen["summed_dig_grade"], screen["max_summed_dig_grade"])
            )

    verdict = _worst(dispositions)
    if not examined:
        findings.append(
            "no surface examination is recorded; an absent feature list is not "
            "an empty one, so the coverglass is not graded until it is looked at"
        )
    elif screen["edge_band_count"]:
        findings.append(
            "%d features sit inside the %.3f mm edge exclusion band and are "
            "reported rather than graded"
            % (screen["edge_band_count"], limits["edge_exclusion_mm"])
        )
    return {
        "coverglass_id": coverglass_id,
        "drawing_id": limits["drawing_id"],
        "revision": limits["revision"],
        "designation": limits["designation"],
        "verdict": verdict,
        "examined": examined,
        "screen": screen,
        "findings": findings,
    }


def inspect_coverglass_scratch_and_dig(
    lot, drawing, margins=DEFAULT_SCRATCH_DIG_MARGINS
):
    """Clause 8.7.1.3.2 scratch and dig screen over one coverglass lot."""
    _validate_margins(margins)
    limits = drawing_limits(drawing)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    declared = _require_count(
        "declared_coverglass_count", lot.get("declared_coverglass_count")
    )
    records = lot.get("coverglasses")
    if not isinstance(records, (list, tuple)):
        raise ValueError("coverglasses must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d coverglass records against a declared count of %d on lot %s"
            % (len(records), declared, lot_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_coverglass_scratch_and_dig(record, drawing, margins)
        if result["coverglass_id"] in seen:
            raise ValueError(
                "duplicate coverglass id %r on lot %s"
                % (result["coverglass_id"], lot_id)
            )
        seen.add(result["coverglass_id"])
        screened.append(result)

    inspected = len(screened)
    counts = dict((state, 0) for state in COVERGLASS_DISPOSITIONS)
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    unexamined = []
    for result in screened:
        counts[result["verdict"]] += 1
        dispositions.append(result["verdict"])
        if result["findings"]:
            affected += 1
        if not result["examined"]:
            unexamined.append(result["coverglass_id"])
        for finding in result["findings"]:
            findings.append("%s %s" % (result["coverglass_id"], finding))

    allowed = margins["max_affected_coverglass_fraction"] * inspected
    factor = margins["review_margin_factor"]
    if inspected and not _at_most(affected, allowed):
        if _at_most(affected, allowed * factor):
            dispositions.append(REVIEW)
            findings.append(
                "%d of %d coverglasses carry a finding, past the %.2f the lot "
                "allowance permits" % (affected, inspected, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d coverglasses carry a finding, past the review margin "
                "of %.2f" % (affected, inspected, allowed * factor)
            )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0 and not unexamined
    if missing:
        findings.append(
            "%d of %d coverglasses carry no examination record; a lot allowance "
            "applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    if unexamined:
        findings.append(
            "%d coverglasses were never examined; the drawing fixes a limit, "
            "not a presumption" % len(unexamined)
        )
    if not complete:
        verdict = INSPECTION_INCOMPLETE
    return {
        "lot_id": lot_id,
        "drawing_id": limits["drawing_id"],
        "revision": limits["revision"],
        "designation": limits["designation"],
        "max_scratch_width_mm": limits["max_scratch_width_mm"],
        "max_dig_diameter_mm": limits["max_dig_diameter_mm"],
        "verdict": verdict,
        "inspection_complete": complete,
        "declared_coverglass_count": declared,
        "inspected_count": inspected,
        "missing_record_count": missing,
        "unexamined_coverglass_ids": unexamined,
        "disposition_counts": counts,
        "affected_count": affected,
        "affected_fraction": affected / float(inspected) if inspected else 0.0,
        "affected_allowance": allowed,
        "remaining_affected_allowance": allowed - affected,
        "not_accepted_ids": [
            result["coverglass_id"]
            for result in screened
            if result["verdict"] != ACCEPT
        ],
        "coverglasses": screened,
        "findings": findings,
    }

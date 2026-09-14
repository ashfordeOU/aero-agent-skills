#!/usr/bin/env python3
"""Coated coverglass faces screened for an even coating and point defects.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar-cell coverglass carries a deposited coating -- an anti-reflective
stack, a conductive layer -- and the clause asks two things of the coated
face at once:

    the field      whether the coating looks even across the coated area,
                   which is a property of the whole face and not of any
                   one spot on it
    the points     whether the face carries pinholes, voids or spatter,
                   which are individual features with a size and a place

The field question is answered by sampling appearance readings across the
face and reducing them to a non-uniformity spread; the point question is
answered by sizing each feature and asking where it sits. A face can pass
one and fail the other, so both are graded and neither substitutes for
the other.

A feature that falls in the declared edge exclusion band is outside the
active aperture and is reported rather than graded, because the band is
not the optical path. A face whose readings were never taken is not an
even face by omission: it is an ungraded face, and it leaves the lot
open.

Dispositions are accept, rework -- meaning the coating is stripped and
redeposited -- and reject. The allowance set below is a declared project
allowance set, not a physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
COVERGLASS_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

PINHOLE = "pinhole"
VOID = "void"
SPATTER = "spatter"
DEFECT_CATEGORIES = (PINHOLE, VOID, SPATTER)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

MM2_PER_CM2 = 100.0

DEFAULT_APPEARANCE_ALLOWANCES = {
    "max_uniformity_spread": 0.10,
    "max_defect_diameter_mm": 0.20,
    "max_defect_density_per_cm2": 2.0,
    "max_obscured_area_fraction": 0.005,
    "max_affected_coverglass_fraction": 0.05,
    "min_appearance_readings": 5,
    "rework_margin_factor": 2.0,
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

    An obscured-area fraction is a sum of circle areas over a rectangle
    of area, and a defect density is a count over an area converted
    between square millimetres and square centimetres, so a value that
    should land exactly on its limit can evaluate a few units in the
    last place past it, and it lands differently on different machines.
    The limit is never moved; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_appearance_allowances(allowances):
    """Check an appearance allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    for key in (
        "max_uniformity_spread",
        "max_obscured_area_fraction",
        "max_affected_coverglass_fraction",
    ):
        _require_fraction("allowances %s" % key, allowances.get(key))
    _require_positive(
        "allowances max_defect_diameter_mm", allowances.get("max_defect_diameter_mm")
    )
    _require_positive(
        "allowances max_defect_density_per_cm2",
        allowances.get("max_defect_density_per_cm2"),
    )
    _require_count(
        "allowances min_appearance_readings", allowances.get("min_appearance_readings")
    )
    if allowances["min_appearance_readings"] < 2:
        raise ValueError(
            "allowances ask for %d appearance reading, and evenness is a "
            "property of a field; a single reading cannot show a spread"
            % allowances["min_appearance_readings"]
        )
    factor = allowances.get("rework_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances rework_margin_factor must be at least one, got %r" % (factor,)
        )
    return allowances


def validate_coated_area(geometry):
    """Check the coated face geometry and its declared edge exclusion band."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    _require_text("coating_id", geometry.get("coating_id"))
    width = _require_positive("coated_width_mm", geometry.get("coated_width_mm"))
    height = _require_positive("coated_height_mm", geometry.get("coated_height_mm"))
    band = _require_non_negative(
        "edge_exclusion_mm", geometry.get("edge_exclusion_mm", 0.0)
    )
    if 2.0 * band >= min(width, height):
        raise ValueError(
            "an edge exclusion band of %r mm a side consumes a coated face of "
            "%r by %r mm, leaving no active aperture to grade"
            % (band, width, height)
        )
    return geometry


def active_aperture(geometry):
    """Coated face reduced to the aperture the clause actually grades."""
    validate_coated_area(geometry)
    width = float(geometry["coated_width_mm"])
    height = float(geometry["coated_height_mm"])
    band = float(geometry.get("edge_exclusion_mm", 0.0))
    active_width = width - 2.0 * band
    active_height = height - 2.0 * band
    return {
        "coating_id": geometry["coating_id"],
        "coated_area_mm2": width * height,
        "active_width_mm": active_width,
        "active_height_mm": active_height,
        "active_area_mm2": active_width * active_height,
        "edge_exclusion_mm": band,
    }


def coating_uniformity_spread(readings, allowances=DEFAULT_APPEARANCE_ALLOWANCES):
    """Sampled appearance readings reduced to a non-uniformity spread.

    The spread is the range of the readings over their mean, so it is
    dimensionless and does not care whether the readings are reflectance
    percentages, transmittance percentages or densitometer counts, as
    long as one face was read in one unit.
    """
    validate_appearance_allowances(allowances)
    if not isinstance(readings, (list, tuple)):
        raise ValueError("appearance readings must be a list, got %r" % (readings,))
    if len(readings) < allowances["min_appearance_readings"]:
        raise ValueError(
            "%d appearance readings against the %d the allowance asks for; an "
            "even look is a property of the field and a short sample cannot "
            "show it" % (len(readings), allowances["min_appearance_readings"])
        )
    values = []
    for index, reading in enumerate(readings):
        values.append(
            _require_positive("appearance reading %d" % index, reading)
        )
    minimum = min(values)
    maximum = max(values)
    mean = math.fsum(values) / len(values)
    return {
        "reading_count": len(values),
        "minimum": minimum,
        "maximum": maximum,
        "mean": mean,
        "spread": (maximum - minimum) / mean,
    }


def defect_projected_area_mm2(defect):
    """Projected area a single point defect takes out of the aperture."""
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    category = defect.get("category")
    if category not in DEFECT_CATEGORIES:
        raise ValueError(
            "defect category must be one of %s, got %r"
            % (", ".join(DEFECT_CATEGORIES), category)
        )
    diameter = _require_positive("defect diameter_mm", defect.get("diameter_mm"))
    return math.pi * diameter * diameter / 4.0


def screen_coated_defects(defects, geometry, allowances=DEFAULT_APPEARANCE_ALLOWANCES):
    """Group the point defects by where they sit and sum what they obscure."""
    validate_appearance_allowances(allowances)
    aperture = active_aperture(geometry)
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list, got %r" % (defects,))
    band = aperture["edge_exclusion_mm"]
    in_aperture = []
    in_band = []
    counts = dict((category, 0) for category in DEFECT_CATEGORIES)
    obscured = []
    largest = 0.0
    for index, defect in enumerate(defects):
        area = defect_projected_area_mm2(defect)
        distance = _require_non_negative(
            "distance_from_edge_mm on defect %d" % index,
            defect.get("distance_from_edge_mm", band),
        )
        entry = {
            "category": defect["category"],
            "diameter_mm": float(defect["diameter_mm"]),
            "projected_area_mm2": area,
            "distance_from_edge_mm": distance,
        }
        if distance < band and not math.isclose(
            distance, band, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            entry["in_active_aperture"] = False
            in_band.append(entry)
            continue
        entry["in_active_aperture"] = True
        in_aperture.append(entry)
        counts[entry["category"]] += 1
        obscured.append(area)
        largest = max(largest, entry["diameter_mm"])
    obscured_area = math.fsum(obscured)
    active_area = aperture["active_area_mm2"]
    return {
        "active_area_mm2": active_area,
        "graded_defects": in_aperture,
        "edge_band_defects": in_band,
        "graded_count": len(in_aperture),
        "edge_band_count": len(in_band),
        "category_counts": counts,
        "largest_diameter_mm": largest,
        "obscured_area_mm2": obscured_area,
        "obscured_area_fraction": obscured_area / active_area,
        "defect_density_per_cm2": len(in_aperture) / (active_area / MM2_PER_CM2),
    }


def assess_coated_coverglass(
    record, geometry, allowances=DEFAULT_APPEARANCE_ALLOWANCES
):
    """Grade one coated coverglass face for evenness and point defects."""
    validate_appearance_allowances(allowances)
    aperture = active_aperture(geometry)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    coverglass_id = _require_text("coverglass_id", record.get("coverglass_id"))
    coating = _require_text(
        "coating_id on %s" % coverglass_id, record.get("coating_id")
    )
    if coating != geometry["coating_id"]:
        raise ValueError(
            "%s carries coating %r while the coated-area definition in hand is "
            "for %r; the aperture and the allowances would be applied to the "
            "wrong coating" % (coverglass_id, coating, geometry["coating_id"])
        )
    defects = screen_coated_defects(record.get("defects", []), geometry, allowances)
    readings = record.get("appearance_readings")
    findings = []
    dispositions = [ACCEPT]
    factor = allowances["rework_margin_factor"]

    sampled = isinstance(readings, (list, tuple)) and len(readings) >= allowances[
        "min_appearance_readings"
    ]
    uniformity = None
    if sampled:
        uniformity = coating_uniformity_spread(readings, allowances)
        if not _at_most(uniformity["spread"], allowances["max_uniformity_spread"]):
            if _at_most(
                uniformity["spread"], allowances["max_uniformity_spread"] * factor
            ):
                dispositions.append(REWORK)
                findings.append(
                    "the coated area reads %.4f across the face, past the %.4f "
                    "spread that counts as even"
                    % (uniformity["spread"], allowances["max_uniformity_spread"])
                )
            else:
                dispositions.append(REJECT)
                findings.append(
                    "the coated area reads %.4f across the face, past the rework "
                    "margin of %.4f"
                    % (
                        uniformity["spread"],
                        allowances["max_uniformity_spread"] * factor,
                    )
                )

    if defects["graded_count"]:
        if not _at_most(
            defects["largest_diameter_mm"], allowances["max_defect_diameter_mm"]
        ):
            if _at_most(
                defects["largest_diameter_mm"],
                allowances["max_defect_diameter_mm"] * factor,
            ):
                dispositions.append(REWORK)
            else:
                dispositions.append(REJECT)
            findings.append(
                "the largest point defect measures %.4f mm across, past the "
                "%.4f mm the allowance permits"
                % (
                    defects["largest_diameter_mm"],
                    allowances["max_defect_diameter_mm"],
                )
            )
        if not _at_most(
            defects["defect_density_per_cm2"],
            allowances["max_defect_density_per_cm2"],
        ):
            if _at_most(
                defects["defect_density_per_cm2"],
                allowances["max_defect_density_per_cm2"] * factor,
            ):
                dispositions.append(REWORK)
            else:
                dispositions.append(REJECT)
            findings.append(
                "pinholes, voids and spatter run %.3f per square centimetre of "
                "aperture, past the %.3f the allowance permits"
                % (
                    defects["defect_density_per_cm2"],
                    allowances["max_defect_density_per_cm2"],
                )
            )
        if not _at_most(
            defects["obscured_area_fraction"],
            allowances["max_obscured_area_fraction"],
        ):
            if _at_most(
                defects["obscured_area_fraction"],
                allowances["max_obscured_area_fraction"] * factor,
            ):
                dispositions.append(REWORK)
            else:
                dispositions.append(REJECT)
            findings.append(
                "point defects obscure %.5f of the active aperture, past the "
                "%.5f the allowance permits"
                % (
                    defects["obscured_area_fraction"],
                    allowances["max_obscured_area_fraction"],
                )
            )

    verdict = _worst(dispositions)
    if not sampled:
        findings.append(
            "the coated area carries no appearance sample; evenness is a "
            "property of the field, so the face is not graded until it is read"
        )
    if defects["edge_band_count"]:
        findings.append(
            "%d point defects sit inside the %.3f mm edge exclusion band and "
            "are reported rather than graded, because the band is not the "
            "optical path"
            % (defects["edge_band_count"], aperture["edge_exclusion_mm"])
        )
    return {
        "coverglass_id": coverglass_id,
        "coating_id": coating,
        "verdict": verdict,
        "appearance_sampled": sampled,
        "uniformity": uniformity,
        "uniformity_spread": uniformity["spread"] if uniformity else None,
        "defects": defects,
        "findings": findings,
    }


def inspect_coated_coverglass_appearance(
    lot, geometry, allowances=DEFAULT_APPEARANCE_ALLOWANCES
):
    """Clause 8.7.1.3.1 coated-appearance screen over one coverglass lot."""
    validate_appearance_allowances(allowances)
    validate_coated_area(geometry)
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
        result = assess_coated_coverglass(record, geometry, allowances)
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
    unsampled = []
    for result in screened:
        counts[result["verdict"]] += 1
        dispositions.append(result["verdict"])
        if result["findings"]:
            affected += 1
        if not result["appearance_sampled"]:
            unsampled.append(result["coverglass_id"])
        for finding in result["findings"]:
            findings.append("%s %s" % (result["coverglass_id"], finding))

    allowed = allowances["max_affected_coverglass_fraction"] * inspected
    factor = allowances["rework_margin_factor"]
    if inspected and not _at_most(affected, allowed):
        if _at_most(affected, allowed * factor):
            dispositions.append(REWORK)
            findings.append(
                "%d of %d coated coverglasses carry a finding, past the %.2f the "
                "lot allowance permits" % (affected, inspected, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d coated coverglasses carry a finding, past the rework "
                "margin of %.2f" % (affected, inspected, allowed * factor)
            )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0 and not unsampled
    if missing:
        findings.append(
            "%d of %d coverglasses carry no appearance record; a lot allowance "
            "applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    if unsampled:
        findings.append(
            "%d coated faces were never read; an unread face is ungraded, not "
            "even" % len(unsampled)
        )
    if not complete:
        verdict = INSPECTION_INCOMPLETE
    return {
        "lot_id": lot_id,
        "coating_id": geometry["coating_id"],
        "verdict": verdict,
        "inspection_complete": complete,
        "declared_coverglass_count": declared,
        "inspected_count": inspected,
        "missing_record_count": missing,
        "unsampled_coverglass_ids": unsampled,
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

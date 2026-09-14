#!/usr/bin/env python3
"""Bubbles and inclusions in coverglass capped by their projected area.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar-cell coverglass may carry bubbles left in the melt and solid
inclusions carried into it. The clause caps what one of them is allowed
to take out of the optical path, and it states that cap as a projected
area -- two hundredths of a square millimetre -- not as a length:

    projected area   the shadow the feature casts on the cell beneath
                     it, which is what the cell actually loses

so a feature measured as two axes, as a diameter or as an area is
reduced to one projected area before anything is compared, and a cap
expressed in square millimetres is never compared with a diameter.

Two features close enough to sit under one shadow are one feature for
this purpose. Grading them apart is the usual way a coverglass with a
cluster well over the cap passes: each member is under it. Features are
therefore grouped by edge-to-edge separation before the cap is applied,
and the group carries the summed area.

A feature inside the declared edge exclusion band is out of the optical
path and is reported rather than graded. A feature recorded smaller than
the method can resolve is refused rather than believed, because a figure
below the resolution of the measurement is not a measurement.

Beyond the per-feature cap the aperture has a budget: the summed
projected area over the active aperture goes against its own allowance,
so a face where every feature is under the cap can still be losing too
much of the cell.

Dispositions are accept, review -- meaning referred to the drawing
authority, because glass does not give the inclusion back -- and reject.
The allowance set below is a declared project allowance set carrying the
clause cap; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
COVERGLASS_DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

BUBBLE = "bubble"
INCLUSION = "inclusion"
FEATURE_KINDS = (BUBBLE, INCLUSION)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

MM2_PER_CM2 = 100.0

CLAUSE_PROJECTED_AREA_CAP_MM2 = 0.02

DEFAULT_INCLUSION_ALLOWANCES = {
    "max_feature_projected_area_mm2": CLAUSE_PROJECTED_AREA_CAP_MM2,
    "merge_separation_mm": 0.05,
    "max_total_area_fraction": 0.002,
    "max_affected_coverglass_fraction": 0.05,
    "min_resolvable_area_mm2": 1e-5,
    "review_margin_factor": 1.5,
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

    A projected area is a product of pi with two measured axes over four,
    a summed fraction is that divided by an aperture, and an equivalent
    radius comes back through a square root, so a feature measured
    exactly at the cap can evaluate a few units in the last place past
    it, and it lands differently on different machines. The cap is never
    moved; only the comparison tolerates the representation error.
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


def validate_inclusion_allowances(allowances):
    """Check an inclusion allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    cap = _require_positive(
        "allowances max_feature_projected_area_mm2",
        allowances.get("max_feature_projected_area_mm2"),
    )
    resolution = _require_positive(
        "allowances min_resolvable_area_mm2", allowances.get("min_resolvable_area_mm2")
    )
    _require_non_negative(
        "allowances merge_separation_mm", allowances.get("merge_separation_mm")
    )
    for key in ("max_total_area_fraction", "max_affected_coverglass_fraction"):
        _require_fraction("allowances %s" % key, allowances.get(key))
    factor = allowances.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances review_margin_factor must be at least one, got %r" % (factor,)
        )
    if resolution >= cap:
        raise ValueError(
            "the method resolves no finer than %r square millimetres while the "
            "cap on one feature is %r; every feature would arrive either "
            "unmeasurable or already over" % (resolution, cap)
        )
    return allowances


def validate_coverglass_aperture(geometry):
    """Check the coverglass aperture the summed area is taken over."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    _require_text("coverglass_type", geometry.get("coverglass_type"))
    width = _require_positive("width_mm", geometry.get("width_mm"))
    height = _require_positive("height_mm", geometry.get("height_mm"))
    band = _require_non_negative(
        "edge_exclusion_mm", geometry.get("edge_exclusion_mm", 0.0)
    )
    if 2.0 * band >= min(width, height):
        raise ValueError(
            "an edge exclusion band of %r mm a side consumes a coverglass of %r "
            "by %r mm, leaving no aperture to grade" % (band, width, height)
        )
    return geometry


def active_aperture(geometry):
    """Coverglass reduced to the aperture the clause actually grades."""
    validate_coverglass_aperture(geometry)
    width = float(geometry["width_mm"])
    height = float(geometry["height_mm"])
    band = float(geometry.get("edge_exclusion_mm", 0.0))
    active_width = width - 2.0 * band
    active_height = height - 2.0 * band
    return {
        "coverglass_type": geometry["coverglass_type"],
        "width_mm": width,
        "height_mm": height,
        "edge_exclusion_mm": band,
        "active_width_mm": active_width,
        "active_height_mm": active_height,
        "active_area_mm2": active_width * active_height,
    }


def equivalent_diameter_mm(area_mm2):
    """Diameter of the circle that projects the same area."""
    area = _require_positive("projected area_mm2", area_mm2)
    return math.sqrt(4.0 * area / math.pi)


def projected_area_mm2(feature, allowances=DEFAULT_INCLUSION_ALLOWANCES):
    """Projected area of one bubble or inclusion, however it was measured.

    Exactly one of a measured area, a diameter or a pair of axes is
    accepted. Two of them are a contradiction rather than a cross-check,
    because nothing here says which one to believe.
    """
    validate_inclusion_allowances(allowances)
    if not isinstance(feature, dict):
        raise ValueError("feature must be a mapping, got %r" % (feature,))
    kind = feature.get("kind")
    if kind not in FEATURE_KINDS:
        raise ValueError(
            "feature kind must be one of %s, got %r" % (", ".join(FEATURE_KINDS), kind)
        )
    given = [
        key
        for key in ("projected_area_mm2", "diameter_mm", "major_axis_mm")
        if feature.get(key) is not None
    ]
    if len(given) != 1:
        raise ValueError(
            "a %s must be measured exactly one way -- a projected area, a "
            "diameter, or a major and minor axis -- and %r carries %d of them"
            % (kind, sorted(given), len(given))
        )
    if given[0] == "projected_area_mm2":
        area = _require_positive(
            "projected_area_mm2", feature.get("projected_area_mm2")
        )
    elif given[0] == "diameter_mm":
        diameter = _require_positive("diameter_mm", feature.get("diameter_mm"))
        area = math.pi * diameter * diameter / 4.0
    else:
        major = _require_positive("major_axis_mm", feature.get("major_axis_mm"))
        minor = _require_positive("minor_axis_mm", feature.get("minor_axis_mm"))
        if minor > major and not math.isclose(
            minor, major, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "the minor axis %r mm is longer than the major axis %r mm; the "
                "two have been swapped" % (minor, major)
            )
        area = math.pi * major * minor / 4.0
    if area < allowances["min_resolvable_area_mm2"] and not math.isclose(
        area, allowances["min_resolvable_area_mm2"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "a %s projecting %r square millimetres is below the %r the method "
            "resolves; a figure under the resolution of the measurement is not "
            "a measurement" % (kind, area, allowances["min_resolvable_area_mm2"])
        )
    return area


def measure_feature(feature, geometry, allowances=DEFAULT_INCLUSION_ALLOWANCES):
    """One bubble or inclusion reduced to an area, a radius and a place."""
    aperture = active_aperture(geometry)
    area = projected_area_mm2(feature, allowances)
    band = aperture["edge_exclusion_mm"]
    distance = _require_non_negative(
        "distance_from_edge_mm", feature.get("distance_from_edge_mm", band)
    )
    in_aperture = distance >= band or math.isclose(
        distance, band, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    return {
        "kind": feature["kind"],
        "projected_area_mm2": area,
        "equivalent_diameter_mm": equivalent_diameter_mm(area),
        "equivalent_radius_mm": equivalent_diameter_mm(area) / 2.0,
        "x_mm": _require_number("x_mm", feature.get("x_mm", 0.0)),
        "y_mm": _require_number("y_mm", feature.get("y_mm", 0.0)),
        "distance_from_edge_mm": distance,
        "in_active_aperture": in_aperture,
    }


def edge_separation_mm(first, second):
    """Gap between the rims of two features, negative where they overlap."""
    centre_distance = math.hypot(first["x_mm"] - second["x_mm"],
                                 first["y_mm"] - second["y_mm"])
    return centre_distance - (
        first["equivalent_radius_mm"] + second["equivalent_radius_mm"]
    )


def group_adjacent_features(measured, allowances=DEFAULT_INCLUSION_ALLOWANCES):
    """Features close enough to sit under one shadow read as one feature.

    Grouping is single-link: a chain of features each within the merge
    separation of the next is one group, because the shadow they cast is
    continuous even where the two ends are far apart.
    """
    validate_inclusion_allowances(allowances)
    if not isinstance(measured, (list, tuple)):
        raise ValueError("measured features must be a list, got %r" % (measured,))
    separation = allowances["merge_separation_mm"]
    parent = list(range(len(measured)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i in range(len(measured)):
        for j in range(i + 1, len(measured)):
            if _at_most(edge_separation_mm(measured[i], measured[j]), separation):
                root_i, root_j = find(i), find(j)
                if root_i != root_j:
                    parent[root_j] = root_i

    buckets = {}
    for index, item in enumerate(measured):
        buckets.setdefault(find(index), []).append(item)

    groups = []
    for root in sorted(buckets):
        members = buckets[root]
        area = math.fsum(item["projected_area_mm2"] for item in members)
        groups.append(
            {
                "member_count": len(members),
                "kinds": sorted(set(item["kind"] for item in members)),
                "projected_area_mm2": area,
                "equivalent_diameter_mm": equivalent_diameter_mm(area),
                "merged": len(members) > 1,
                "members": members,
            }
        )
    return groups


def screen_coverglass_features(
    features, geometry, allowances=DEFAULT_INCLUSION_ALLOWANCES
):
    """Recorded features measured, grouped and summed over the aperture."""
    validate_inclusion_allowances(allowances)
    aperture = active_aperture(geometry)
    if not isinstance(features, (list, tuple)):
        raise ValueError("features must be a list, got %r" % (features,))
    graded = []
    in_band = []
    for feature in features:
        measured = measure_feature(feature, geometry, allowances)
        if measured["in_active_aperture"]:
            graded.append(measured)
        else:
            in_band.append(measured)
    groups = group_adjacent_features(graded, allowances)
    total_area = math.fsum(group["projected_area_mm2"] for group in groups)
    active_area = aperture["active_area_mm2"]
    largest = max((group["projected_area_mm2"] for group in groups), default=0.0)
    return {
        "active_area_mm2": active_area,
        "graded_feature_count": len(graded),
        "edge_band_count": len(in_band),
        "edge_band_features": in_band,
        "groups": groups,
        "group_count": len(groups),
        "merged_group_count": sum(1 for group in groups if group["merged"]),
        "largest_projected_area_mm2": largest,
        "total_projected_area_mm2": total_area,
        "total_area_fraction": total_area / active_area,
        "feature_density_per_cm2": len(graded) / (active_area / MM2_PER_CM2),
    }


def assess_coverglass_inclusions(
    record, geometry, allowances=DEFAULT_INCLUSION_ALLOWANCES
):
    """Grade one coverglass for bubbles and inclusions against the cap."""
    validate_inclusion_allowances(allowances)
    aperture = active_aperture(geometry)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    coverglass_id = _require_text("coverglass_id", record.get("coverglass_id"))
    part_type = _require_text(
        "coverglass_type on %s" % coverglass_id, record.get("coverglass_type")
    )
    if part_type != aperture["coverglass_type"]:
        raise ValueError(
            "%s is a %r coverglass while the aperture in hand is for a %r; the "
            "summed area would be taken over the wrong aperture"
            % (coverglass_id, part_type, aperture["coverglass_type"])
        )

    features = record.get("features")
    examined = isinstance(features, (list, tuple))
    findings = []
    dispositions = [ACCEPT]
    factor = allowances["review_margin_factor"]
    cap = allowances["max_feature_projected_area_mm2"]
    screen = None

    if examined:
        screen = screen_coverglass_features(features, geometry, allowances)
        for group in screen["groups"]:
            if _at_most(group["projected_area_mm2"], cap):
                continue
            if _at_most(group["projected_area_mm2"], cap * factor):
                dispositions.append(REVIEW)
            else:
                dispositions.append(REJECT)
            if group["merged"]:
                findings.append(
                    "%d features within the merge separation project %.5f square "
                    "millimetres together, past the %.5f cap, although each is "
                    "under it alone"
                    % (group["member_count"], group["projected_area_mm2"], cap)
                )
            else:
                findings.append(
                    "a %s projects %.5f square millimetres, past the %.5f cap"
                    % (
                        group["kinds"][0],
                        group["projected_area_mm2"],
                        cap,
                    )
                )
        allowed_fraction = allowances["max_total_area_fraction"]
        if not _at_most(screen["total_area_fraction"], allowed_fraction):
            if _at_most(screen["total_area_fraction"], allowed_fraction * factor):
                dispositions.append(REVIEW)
            else:
                dispositions.append(REJECT)
            findings.append(
                "bubbles and inclusions take %.6f of the aperture between them, "
                "past the %.6f the allowance permits, although no single one is "
                "over the cap"
                % (screen["total_area_fraction"], allowed_fraction)
            )

    verdict = _worst(dispositions)
    if not examined:
        findings.append(
            "no feature record is present; an absent list is not an empty one, "
            "so the coverglass is not graded until it is examined"
        )
    elif screen["edge_band_count"]:
        findings.append(
            "%d features sit inside the %.3f mm edge exclusion band and are "
            "reported rather than graded"
            % (screen["edge_band_count"], aperture["edge_exclusion_mm"])
        )
    return {
        "coverglass_id": coverglass_id,
        "coverglass_type": part_type,
        "verdict": verdict,
        "examined": examined,
        "projected_area_cap_mm2": cap,
        "screen": screen,
        "findings": findings,
    }


def inspect_coverglass_bubbles_and_inclusions(
    lot, geometry, allowances=DEFAULT_INCLUSION_ALLOWANCES
):
    """Clause 8.7.1.3.3 bubble and inclusion screen over one coverglass lot."""
    validate_inclusion_allowances(allowances)
    aperture = active_aperture(geometry)
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
        result = assess_coverglass_inclusions(record, geometry, allowances)
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

    allowed = allowances["max_affected_coverglass_fraction"] * inspected
    factor = allowances["review_margin_factor"]
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
            "%d of %d coverglasses carry no feature record; a lot allowance "
            "applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    if unexamined:
        findings.append(
            "%d coverglasses were never examined; an unexamined coverglass is "
            "ungraded, not clear" % len(unexamined)
        )
    if not complete:
        verdict = INSPECTION_INCOMPLETE
    return {
        "lot_id": lot_id,
        "coverglass_type": aperture["coverglass_type"],
        "projected_area_cap_mm2": allowances["max_feature_projected_area_mm2"],
        "cap_equivalent_diameter_mm": equivalent_diameter_mm(
            allowances["max_feature_projected_area_mm2"]
        ),
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

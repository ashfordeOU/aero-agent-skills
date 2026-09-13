#!/usr/bin/env python3
"""Unaided cleanliness inspection of the surfaces of a photovoltaic coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.21. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks for coupon surfaces that appear clean when they are
looked at without a magnification aid. That phrasing bounds the result
twice over. It bounds what can be found -- the unaided eye resolves
roughly a tenth of a millimetre at a working distance, so nothing
smaller can be reported either present or absent -- and it bounds what
may be credited, because an examination carried out through a
magnifier is a different, more sensitive instrument and its findings
are not the unaided statement the clause wants.

So the useful output is not a bare clean or dirty. It is a verdict
plus the detection floor the verdict rests on, per surface and rolled
up over the coupon, together with the examination conditions that were
or were not met.

Deposit kinds
    particulate       discrete particles on the surface
    smear-or-film     a spread film rather than discrete particles
    fingerprint       handling residue, ionic and hygroscopic
    adhesive-residue  process adhesive left outside its bond line
    staining          a colour change of the surface itself
    fibre             a lint or cloth fibre, long and bridging

Dispositions are accept, clean-and-reinspect, refer-for-review and
reject. The criteria below are a declared coupon criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEPOSIT_KINDS = (
    "particulate",
    "smear-or-film",
    "fingerprint",
    "adhesive-residue",
    "staining",
    "fibre",
)

ACCEPT = "accept"
CLEAN = "clean-and-reinspect"
REFER = "refer-for-review"
REJECT = "reject"
CLEANLINESS_DISPOSITIONS = (ACCEPT, CLEAN, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, CLEAN: 1, REFER: 2, REJECT: 3}

REQUIRED_DEPOSIT_FIELDS = {
    "particulate": ("max_dimension_mm", "count"),
    "smear-or-film": ("area_mm2", "removable"),
    "fingerprint": ("area_mm2",),
    "adhesive-residue": ("area_mm2", "removable"),
    "staining": ("area_mm2",),
    "fibre": ("length_mm",),
}

DEFAULT_CLEANLINESS_CRITERIA = {
    "unaided_acuity_arcmin": 1.0,
    "max_magnification": 1.0,
    "max_viewing_distance_mm": 500.0,
    "min_illuminance_lux": 1000.0,
    "max_particle_size_mm": 0.5,
    "particle_review_factor": 2.0,
    "max_particles_per_100cm2": 5,
    "max_deposit_area_fraction": 0.005,
    "deposit_review_factor": 3.0,
    "fibre_length_factor": 4.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_MM2_PER_100CM2 = 10000.0


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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The detection floor comes out of a trigonometric conversion and the
    deposit limits are products of a criteria value and a measured
    area, so a measurement sitting exactly on a limit can evaluate a
    few units in the last place above it. The limit is never raised;
    only the comparison tolerates the representation error.
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


def validate_cleanliness_criteria(criteria):
    """Check a cleanliness criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "unaided_acuity_arcmin",
        "max_viewing_distance_mm",
        "min_illuminance_lux",
        "max_particle_size_mm",
        "max_deposit_area_fraction",
        "fibre_length_factor",
    ):
        _require_positive("criteria %s" % key, criteria.get(key))
    fraction = criteria.get("max_deposit_area_fraction")
    if fraction > 1.0:
        raise ValueError(
            "criteria max_deposit_area_fraction must not exceed one, got %r"
            % (fraction,)
        )
    for key in ("particle_review_factor", "deposit_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one, got %r" % (key, factor)
            )
    magnification = _require_positive(
        "criteria max_magnification", criteria.get("max_magnification")
    )
    if magnification < 1.0:
        raise ValueError(
            "criteria max_magnification must be at least one; unity is the "
            "unaided eye and the clause asks for no aid above it"
        )
    _require_count(
        "criteria max_particles_per_100cm2", criteria.get("max_particles_per_100cm2")
    )
    return criteria


def resolvable_feature_mm(viewing_distance_mm, acuity_arcmin=1.0, magnification=1.0):
    """Smallest feature an examination at these conditions could show.

    The angular acuity is converted to a length at the working
    distance, and an aid divides that length by its magnification. The
    number is a detection floor: below it the examination reports
    nothing, so the absence of a deposit smaller than the floor is not
    evidence that the surface is free of it.
    """
    distance = _require_positive("viewing_distance_mm", viewing_distance_mm)
    acuity = _require_positive("acuity_arcmin", acuity_arcmin)
    power = _require_positive("magnification", magnification)
    if power < 1.0:
        raise ValueError(
            "magnification must be at least one; an aid cannot resolve less than "
            "the unaided eye, got %r" % (magnification,)
        )
    angle_rad = math.radians(acuity / 60.0)
    return 2.0 * distance * math.tan(angle_rad / 2.0) / power


def assess_deposit(deposit, surface_area_mm2, detection_floor_mm, criteria=DEFAULT_CLEANLINESS_CRITERIA):
    """Disposition one observed deposit against the criteria set."""
    validate_cleanliness_criteria(criteria)
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping, got %r" % (deposit,))
    kind = _require_choice("kind", deposit.get("kind"), DEPOSIT_KINDS)
    area = _require_positive("surface_area_mm2", surface_area_mm2)
    floor = _require_positive("detection_floor_mm", detection_floor_mm)
    for field in REQUIRED_DEPOSIT_FIELDS[kind]:
        if deposit.get(field) is None:
            raise ValueError("a %s deposit needs %s" % (kind, field))

    reasons = []
    deposit_area = 0.0
    below_floor = False

    if kind == "particulate":
        size = _require_positive("max_dimension_mm", deposit.get("max_dimension_mm"))
        count = _require_count("count", deposit.get("count"))
        if count == 0:
            raise ValueError("a particulate observation needs a count above zero")
        deposit_area = count * size * size
        density = count * _MM2_PER_100CM2 / area
        limit = criteria["max_particle_size_mm"]
        review_limit = limit * criteria["particle_review_factor"]
        below_floor = size < floor and not math.isclose(
            size, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
        if below_floor:
            disposition = REFER
            reasons.append(
                "a %.4f mm particle sits under the %.4f mm unaided detection "
                "floor, so this record did not come from the examination the "
                "clause describes" % (size, floor)
            )
        elif not _at_most(size, review_limit):
            disposition = REJECT
            reasons.append(
                "particle %.3f mm across exceeds the %.3f mm review limit"
                % (size, review_limit)
            )
        elif not _at_most(size, limit):
            disposition = CLEAN
            reasons.append(
                "particle %.3f mm across exceeds the %.3f mm limit; remove it and "
                "look at the surface again" % (size, limit)
            )
        elif not _at_most(density, float(criteria["max_particles_per_100cm2"])):
            disposition = CLEAN
            reasons.append(
                "%.2f particles per 100 cm2 exceeds the %d allowed even though "
                "each one is inside the size limit"
                % (density, criteria["max_particles_per_100cm2"])
            )
        else:
            disposition = ACCEPT
    elif kind == "fingerprint":
        deposit_area = _require_positive("area_mm2", deposit.get("area_mm2"))
        disposition = CLEAN
        reasons.append(
            "handling residue is ionic and draws water, so it is removed and the "
            "surface looked at again rather than accepted at size"
        )
    elif kind == "staining":
        deposit_area = _require_positive("area_mm2", deposit.get("area_mm2"))
        disposition = REFER
        reasons.append(
            "a stain is a change of the surface itself, not a deposit sitting on "
            "it, so cleaning does not answer it"
        )
    elif kind == "fibre":
        length = _require_positive("length_mm", deposit.get("length_mm"))
        width = length / 20.0
        deposit_area = length * width
        limit = criteria["max_particle_size_mm"] * criteria["fibre_length_factor"]
        if _at_most(length, limit):
            disposition = CLEAN
            reasons.append(
                "a fibre is removed and the surface looked at again; it bridges "
                "rather than sits, so its length is not its footprint"
            )
        else:
            disposition = REFER
            reasons.append(
                "fibre %.3f mm long exceeds the %.3f mm limit and can bridge "
                "between features" % (length, limit)
            )
    else:  # smear-or-film and adhesive-residue
        deposit_area = _require_positive("area_mm2", deposit.get("area_mm2"))
        removable = _require_bool("removable", deposit.get("removable"))
        fraction = deposit_area / area
        limit = criteria["max_deposit_area_fraction"]
        review_limit = limit * criteria["deposit_review_factor"]
        if not removable:
            disposition = REFER
            reasons.append(
                "the deposit will not come off, so it stays on the surface for "
                "the life of the article"
            )
            if not _at_most(fraction, review_limit):
                disposition = REJECT
                reasons.append(
                    "and it covers %.5f of the surface, past the %.5f review "
                    "limit" % (fraction, review_limit)
                )
        elif _at_most(fraction, limit):
            disposition = CLEAN
            reasons.append(
                "the deposit is removable; clean the surface and look at it again "
                "before the coupon counts as accepted"
            )
        elif _at_most(fraction, review_limit):
            disposition = REFER
            reasons.append(
                "deposit covers %.5f of the surface against the %.5f allowance"
                % (fraction, limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "deposit covers %.5f of the surface, past the %.5f review limit"
                % (fraction, review_limit)
            )

    if not _at_most(deposit_area, area):
        raise ValueError(
            "deposit %r claims %.3f mm2 of a %.3f mm2 surface"
            % (deposit.get("id"), deposit_area, area)
        )
    return {
        "id": deposit.get("id"),
        "kind": kind,
        "deposit_area_mm2": deposit_area,
        "below_detection_floor": below_floor,
        "disposition": disposition,
        "reasons": reasons,
    }


def assess_surface(record, criteria=DEFAULT_CLEANLINESS_CRITERIA):
    """Judge one coupon surface and the conditions it was looked at under."""
    validate_cleanliness_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    surface_id = record.get("surface_id")
    if not isinstance(surface_id, str) or not surface_id.strip():
        raise ValueError("each surface record needs a non-empty surface_id")
    area = _require_positive("area_mm2", record.get("area_mm2"))
    distance = _require_positive(
        "viewing_distance_mm", record.get("viewing_distance_mm")
    )
    illuminance = _require_non_negative(
        "illuminance_lux", record.get("illuminance_lux")
    )
    magnification = _require_positive(
        "magnification", record.get("magnification", 1.0)
    )
    if magnification < 1.0:
        raise ValueError(
            "magnification must be at least one, got %r" % (magnification,)
        )
    floor = resolvable_feature_mm(
        distance, criteria["unaided_acuity_arcmin"], magnification
    )
    unaided_floor = resolvable_feature_mm(distance, criteria["unaided_acuity_arcmin"])

    findings = []
    conditions_met = True
    aided = not _at_most(magnification, criteria["max_magnification"])
    if aided:
        conditions_met = False
        findings.append(
            "the surface was looked at through a %.2fx aid; that is a more "
            "sensitive instrument than the clause names, so its result is not "
            "the unaided statement" % (magnification,)
        )
    if not _at_most(distance, criteria["max_viewing_distance_mm"]):
        conditions_met = False
        findings.append(
            "viewed from %.1f mm against a %.1f mm working distance; the "
            "detection floor grows with the distance"
            % (distance, criteria["max_viewing_distance_mm"])
        )
    if illuminance < criteria["min_illuminance_lux"] and not math.isclose(
        illuminance, criteria["min_illuminance_lux"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        conditions_met = False
        findings.append(
            "examined at %.0f lux against a %.0f lux floor; below the floor a "
            "surface look stops being a detection activity"
            % (illuminance, criteria["min_illuminance_lux"])
        )

    deposits = record.get("deposits", [])
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("deposits must be a list, got %r" % (deposits,))
    seen = set()
    assessed = []
    for deposit in deposits:
        result = assess_deposit(deposit, area, floor, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate deposit id %r on surface %s" % (marker, surface_id)
                )
            seen.add(marker)
        assessed.append(result)

    covered = sum(result["deposit_area_mm2"] for result in assessed)
    if not _at_most(covered, area):
        raise ValueError(
            "deposit area %.3f mm2 exceeds the %.3f mm2 surface %s"
            % (covered, area, surface_id)
        )
    coverage_fraction = covered / area

    verdict = _worst([result["disposition"] for result in assessed])
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    if not _at_most(coverage_fraction, criteria["max_deposit_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "deposits cover %.5f of the surface together, past the %.5f "
            "allowance, even though no single one did"
            % (coverage_fraction, criteria["max_deposit_area_fraction"])
        )
    if not conditions_met:
        verdict = _worst((verdict, REFER))
    return {
        "surface_id": surface_id,
        "verdict": verdict,
        "appears_clean": verdict == ACCEPT and conditions_met,
        "conditions_met": conditions_met,
        "aided": aided,
        "detection_floor_mm": floor,
        "unaided_detection_floor_mm": unaided_floor,
        "deposit_coverage_fraction": coverage_fraction,
        "deposits": assessed,
        "findings": findings,
    }


def inspect_coupon_cleanliness(coupon, criteria=DEFAULT_CLEANLINESS_CRITERIA):
    """Clause 5.5.3.2.21 unaided cleanliness look over the whole coupon."""
    validate_cleanliness_criteria(criteria)
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("coupon_id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty coupon_id")
    declared = coupon.get("declared_surface_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_surface_count must be a positive integer, got %r" % (declared,)
        )
    records = coupon.get("surfaces")
    if not isinstance(records, (list, tuple)):
        raise ValueError("surfaces must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d surface records against a declared count of %d on %s"
            % (len(records), declared, coupon_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_surface(record, criteria)
        marker = result["surface_id"]
        if marker in seen:
            raise ValueError(
                "duplicate surface id %r on coupon %s" % (marker, coupon_id)
            )
        seen.add(marker)
        screened.append(result)

    findings = []
    counts = dict((state, 0) for state in CLEANLINESS_DISPOSITIONS)
    for result in screened:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["surface_id"], finding))

    missing = declared - len(screened)
    verdict = _worst([result["verdict"] for result in screened])
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d declared surfaces carry no record; a coupon is only as "
            "clean as the face nobody looked at" % (missing, declared)
        )
    floor = max(
        (result["detection_floor_mm"] for result in screened), default=None
    )
    if floor is not None:
        findings.append(
            "the clean statement for this coupon is bounded at %.4f mm; nothing "
            "smaller than that was either found or ruled out" % (floor,)
        )
    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "appears_clean_unaided": complete
        and all(result["appears_clean"] for result in screened),
        "inspection_complete": complete,
        "missing_record_count": missing,
        "screened_count": len(screened),
        "disposition_counts": counts,
        "statement_bounded_at_mm": floor,
        "not_accepted_ids": [
            result["surface_id"]
            for result in screened
            if result["verdict"] != ACCEPT
        ],
        "surfaces": screened,
        "findings": findings,
    }

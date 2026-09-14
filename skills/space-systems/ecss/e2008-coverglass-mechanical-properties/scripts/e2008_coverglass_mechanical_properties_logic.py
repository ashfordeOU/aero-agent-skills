#!/usr/bin/env python3
"""Dimensional and mass record of every coverglass configuration on test.

Anchor: ECSS-E-ST-20-08C clause 8.7.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass test campaign runs several configurations at once -- a
thickness family, a coating family, a doped and an undoped glass -- and
each one has to arrive at the optical and environmental tests with its
own dimensional and mass record. Four families of measurement carry
that record and each fails in its own way:

    length_mm     the outline the cell laydown assumes. Oversize and
    width_mm      the coverglass overhangs the cell edge into the gap
                  the interconnector needs; undersize and the cell
                  perimeter is left bare to the environment.
    thickness_um  the shielding depth the radiation analysis was run
                  at, and the term that dominates the coverglass mass.
    mass_mg       what the piece weighs, against its band. Coverglass
                  mass is an array budget: a few per cent per piece
                  becomes kilograms across a wing.

Two things separate this from arithmetic on a measurement sheet.

First, a coverglass is bought to a drawing and cannot be machined back
into tolerance without breaking the polish and the coating. There is no
rework disposition. What exists instead is a review band: a deviation
outside tolerance but inside a declared multiple of it is raised as a
non-conformance and submitted for a use-as-is decision. Past that
multiple the piece is refused.

Second, the four measurements are not independent. Mass divided by the
outline area gives the areal density the array mass budget consumes,
and mass divided by the full volume gives the bulk density of the
glass, which the material already fixes. A measured bulk density that
departs from the declared material density says one of the four
measurements is wrong -- a thickness read off the wrong datum, a
chipped piece weighed short, or the wrong configuration on the sheet --
and that cross-check runs before any single band is believed.

A configuration the test matrix declares but the record sheet omits is
unknown, not conforming, and a record for a configuration the matrix
never declared is a matrix mismatch rather than a deviation.

Dimensional states are within-tolerance, above-upper-limit and
below-lower-limit. Dispositions are accept, review and reject. The
bands and the material density below travel with the coverglass
specification, not with this module.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIMENSION_WITHIN = "within-tolerance"
DIMENSION_ABOVE = "above-upper-limit"
DIMENSION_BELOW = "below-lower-limit"
DIMENSION_STATES = (DIMENSION_WITHIN, DIMENSION_ABOVE, DIMENSION_BELOW)

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

# Bands every coverglass configuration has to carry.
REQUIRED_BANDS = (
    "length_mm",
    "width_mm",
    "thickness_um",
    "mass_mg",
)

DEFAULT_REVIEW_BAND_FACTOR = 2.0
DEFAULT_BULK_DENSITY_TOLERANCE = 0.08

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


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a nominal plus a tolerance and a review limit multiplies
    that tolerance again, so a measurement meant to sit exactly on a
    limit can evaluate a few units in the last place to either side. The
    limit is never moved; only the comparison tolerates the error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_band(name, band):
    """Check one nominal-plus-tolerance band and return it normalised."""
    if not isinstance(band, dict):
        raise ValueError("band %s must be a mapping, got %r" % (name, band))
    nominal = _require_positive("band %s nominal" % name, band.get("nominal"))
    minus = _require_non_negative("band %s minus" % name, band.get("minus"))
    plus = _require_non_negative("band %s plus" % name, band.get("plus"))
    if minus <= 0.0 and plus <= 0.0:
        raise ValueError(
            "band %s has no width; a zero-tolerance band cannot be measured "
            "against and would refuse every real coverglass" % name
        )
    if minus > nominal:
        raise ValueError(
            "band %s allows a lower limit at or below zero; the minus "
            "tolerance exceeds the nominal" % name
        )
    return {"nominal": nominal, "minus": minus, "plus": plus}


def validate_coverglass_specification(spec):
    """Check the test-matrix specification carries every band it needs."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping, got %r" % (spec,))

    declared = spec.get("configurations")
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError(
            "specification must declare at least one coverglass configuration; "
            "clause 8.7.4 records the properties per configuration under test"
        )

    configurations = {}
    order = []
    for entry in declared:
        if not isinstance(entry, dict):
            raise ValueError("each configuration must be a mapping, got %r" % (entry,))
        config_id = _require_identifier("configuration id", entry.get("id"))
        if config_id in configurations:
            raise ValueError(
                "duplicate configuration id %r in the specification" % config_id
            )
        bands = {}
        for name in REQUIRED_BANDS:
            if name not in entry:
                raise ValueError(
                    "configuration %s is missing the %s band; an unstated band "
                    "is not an open one" % (config_id, name)
                )
            bands[name] = validate_band("%s %s" % (config_id, name), entry[name])
        population = entry.get("population", 1)
        if not isinstance(population, int) or isinstance(population, bool):
            raise ValueError(
                "configuration %s population must be a whole number of pieces, "
                "got %r" % (config_id, population)
            )
        if population < 1:
            raise ValueError(
                "configuration %s population must be at least one piece" % config_id
            )
        configurations[config_id] = {"bands": bands, "population": population}
        order.append(config_id)

    material_density = _require_positive(
        "material_density_g_per_cm3", spec.get("material_density_g_per_cm3")
    )

    factor = _require_positive(
        "review_band_factor", spec.get("review_band_factor", DEFAULT_REVIEW_BAND_FACTOR)
    )
    if factor < 1.0 and not _close(factor, 1.0):
        raise ValueError(
            "review_band_factor cannot be under one; the review band widens a "
            "tolerance, it never narrows one"
        )

    density_tolerance = _require_positive(
        "bulk_density_tolerance",
        spec.get("bulk_density_tolerance", DEFAULT_BULK_DENSITY_TOLERANCE),
    )
    if density_tolerance >= 1.0:
        raise ValueError(
            "bulk_density_tolerance is a fraction of the declared density and "
            "must stay under one; a tolerance of one accepts every measurement"
        )

    return {
        "configurations": configurations,
        "order": tuple(order),
        "material_density_g_per_cm3": material_density,
        "review_band_factor": factor,
        "bulk_density_tolerance": density_tolerance,
    }


def evaluate_dimension(name, measured, band, review_band_factor=DEFAULT_REVIEW_BAND_FACTOR):
    """Place one measurement inside its band and name the disposition."""
    checked = validate_band(name, band)
    value = _require_number("%s measured" % name, measured)
    factor = _require_positive("review_band_factor", review_band_factor)
    lower = checked["nominal"] - checked["minus"]
    upper = checked["nominal"] + checked["plus"]
    review_lower = checked["nominal"] - checked["minus"] * factor
    review_upper = checked["nominal"] + checked["plus"] * factor

    if _at_least(value, lower) and _at_most(value, upper):
        state = DIMENSION_WITHIN
        disposition = ACCEPT
    elif value > upper:
        state = DIMENSION_ABOVE
        disposition = REVIEW if _at_most(value, review_upper) else REJECT
    else:
        state = DIMENSION_BELOW
        disposition = REVIEW if _at_least(value, review_lower) else REJECT

    if state == DIMENSION_WITHIN:
        margin = min(value - lower, upper - value)
    elif state == DIMENSION_ABOVE:
        margin = upper - value
    else:
        margin = value - lower

    return {
        "name": name,
        "measured": value,
        "nominal": checked["nominal"],
        "lower_limit": lower,
        "upper_limit": upper,
        "deviation": value - checked["nominal"],
        "margin": margin,
        "state": state,
        "disposition": disposition,
    }


def outline_area_cm2(length_mm, width_mm):
    """Plan area of one coverglass, in square centimetres."""
    length = _require_positive("length_mm", length_mm)
    width = _require_positive("width_mm", width_mm)
    return (length * width) / 100.0


def areal_density_mg_per_cm2(mass_mg, length_mm, width_mm):
    """Mass per unit of outline area -- the term the array budget consumes."""
    mass = _require_positive("mass_mg", mass_mg)
    return mass / outline_area_cm2(length_mm, width_mm)


def bulk_density_g_per_cm3(mass_mg, length_mm, width_mm, thickness_um):
    """Mass per unit of full volume -- the density the glass material fixes."""
    mass = _require_positive("mass_mg", mass_mg)
    thickness = _require_positive("thickness_um", thickness_um)
    volume_cm3 = outline_area_cm2(length_mm, width_mm) * (thickness / 10000.0)
    return (mass / 1000.0) / volume_cm3


def mass_contribution_g(mass_mg, population):
    """What one configuration adds to the array mass budget, in grams."""
    mass = _require_positive("mass_mg", mass_mg)
    if not isinstance(population, int) or isinstance(population, bool):
        raise ValueError(
            "population must be a whole number of pieces, got %r" % (population,)
        )
    if population < 1:
        raise ValueError("population must be at least one piece, got %r" % (population,))
    return (mass * population) / 1000.0


def assess_coverglass_configuration(record, spec):
    """Clause 8.7.4 dimensional and mass check of one coverglass record."""
    checked = validate_coverglass_specification(spec)
    return _assess_against_checked(record, checked)


def _assess_against_checked(record, checked):
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    config_id = _require_identifier("configuration_id", record.get("configuration_id"))
    if config_id not in checked["configurations"]:
        raise ValueError(
            "record names configuration %r, which the test matrix does not "
            "declare; an undeclared configuration is a matrix mismatch, not a "
            "deviation" % config_id
        )
    sample_id = _require_identifier("sample_id", record.get("sample_id"))

    entry = checked["configurations"][config_id]
    factor = checked["review_band_factor"]

    dimensions = []
    for name in REQUIRED_BANDS:
        if name not in record:
            raise ValueError(
                "record %s is missing the %s measurement; an unmeasured "
                "property is unknown, not conforming" % (sample_id, name)
            )
        dimensions.append(
            evaluate_dimension(name, record[name], entry["bands"][name], factor)
        )

    areal_density = areal_density_mg_per_cm2(
        record["mass_mg"], record["length_mm"], record["width_mm"]
    )
    bulk_density = bulk_density_g_per_cm3(
        record["mass_mg"],
        record["length_mm"],
        record["width_mm"],
        record["thickness_um"],
    )
    material_density = checked["material_density_g_per_cm3"]
    density_tolerance = checked["bulk_density_tolerance"]
    density_error = abs(bulk_density / material_density - 1.0)
    density_consistent = _at_most(density_error, density_tolerance)

    calls = [item["disposition"] for item in dimensions]
    findings = []
    for item in dimensions:
        if item["state"] != DIMENSION_WITHIN:
            findings.append(
                "%s measures %.4f against the %.4f to %.4f band (%s)"
                % (
                    item["name"],
                    item["measured"],
                    item["lower_limit"],
                    item["upper_limit"],
                    item["state"],
                )
            )
    if not density_consistent:
        calls.append(REVIEW)
        findings.append(
            "the measured bulk density %.4f g/cm3 departs from the declared "
            "material density %.4f g/cm3 by %.4f, past the %.4f allowance; the "
            "outline, thickness and mass disagree and one of the four "
            "measurements is suspect"
            % (bulk_density, material_density, density_error, density_tolerance)
        )

    verdict = _worst(calls)
    if verdict == ACCEPT and not findings:
        findings.append(
            "every recorded property sits inside its band and the mass, "
            "outline and thickness agree on the glass density; the record "
            "stands as the clause 8.7.4 evidence for this configuration"
        )

    return {
        "configuration_id": config_id,
        "sample_id": sample_id,
        "verdict": verdict,
        "dimensions": dimensions,
        "outline_area_cm2": outline_area_cm2(
            record["length_mm"], record["width_mm"]
        ),
        "areal_density_mg_per_cm2": areal_density,
        "bulk_density_g_per_cm3": bulk_density,
        "material_density_g_per_cm3": material_density,
        "bulk_density_error_fraction": density_error,
        "bulk_density_consistent": density_consistent,
        "mass_contribution_g": mass_contribution_g(
            record["mass_mg"], entry["population"]
        ),
        "population": entry["population"],
        "out_of_tolerance_names": [
            item["name"] for item in dimensions if item["state"] != DIMENSION_WITHIN
        ],
        "nonconformance_review_required": verdict == REVIEW,
        "findings": findings,
    }


def assess_coverglass_test_matrix(records, spec):
    """Roll the per-configuration records up into one matrix verdict."""
    checked = validate_coverglass_specification(spec)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list, got %r" % (records,))

    results = []
    covered = set()
    seen_samples = set()
    for record in records:
        result = _assess_against_checked(record, checked)
        if result["sample_id"] in seen_samples:
            raise ValueError(
                "duplicate sample_id %r; two records cannot describe the same "
                "piece" % result["sample_id"]
            )
        seen_samples.add(result["sample_id"])
        covered.add(result["configuration_id"])
        results.append(result)

    missing = [name for name in checked["order"] if name not in covered]
    if missing:
        raise ValueError(
            "no dimensional and mass record for configuration(s) %s; a "
            "configuration under test with no record is unknown, not "
            "conforming" % ", ".join(missing)
        )

    matrix_mass_g = 0.0
    for name in checked["order"]:
        for result in results:
            if result["configuration_id"] == name:
                matrix_mass_g += result["mass_contribution_g"]
                break

    verdict = _worst([result["verdict"] for result in results])
    return {
        "verdict": verdict,
        "configurations_recorded": tuple(checked["order"]),
        "records": results,
        "matrix_mass_contribution_g": matrix_mass_g,
        "rejected_samples": [
            result["sample_id"] for result in results if result["verdict"] == REJECT
        ],
        "review_samples": [
            result["sample_id"] for result in results if result["verdict"] == REVIEW
        ],
        "density_inconsistent_samples": [
            result["sample_id"]
            for result in results
            if not result["bulk_density_consistent"]
        ],
    }

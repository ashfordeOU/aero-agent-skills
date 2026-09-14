#!/usr/bin/env python3
"""Bulk and surface resistivity reduction for coated coverglass components.

Anchor: ECSS-E-ST-20-08C clause 8.7.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause asks for the electro-optical resistivity behaviour of the
coverglass component, and behaviour here means two numbers, not one.

Bulk volume resistivity describes the path straight through the glass,
from the outer face to the cell. It is what stops a charged outer surface
from dumping into the junction, and it is reduced from a guarded-electrode
measurement as the measured resistance times the electrode area divided by
the specimen thickness.

Surface resistivity describes the path along the outer face. On a coated
coverglass that is the path the coating exists to provide: it bleeds
deposited charge sideways to the array frame instead of letting it sit and
build to an arc. It is reduced from the measured resistance times a
geometry factor set by the electrode arrangement -- for concentric rings,
two pi over the natural log of the radius ratio; for a rectangular bar,
the electrode width over the gap between the electrodes.

The two have opposite senses and that is the trap. Bulk resistivity is
wanted inside a declared band: too low is a leakage path, and a value far
above the band is usually the instrument's range limit reported as a
measurement rather than the glass. Surface resistivity on a coated part is
wanted at or below a ceiling, because a coating that does not conduct is a
coating that is not doing its job.

The sense of the surface figure depends on whether there is a coating at
all. An uncoated coverglass has no charge-bleed duty, so its surface
figure is characterisation only and no ceiling applies to it. Applying the
coated ceiling to an uncoated part fails a part that was never required to
pass it.

A component is characterized only when both properties are present.
One number and a promise about the other is not the behaviour the clause
asks for, so a half-populated record closes the assessment as incomplete
rather than passing on the half that was measured.

Spread across the measured articles is reported beside the verdict. A
coating whose articles differ by orders of magnitude is a real finding
about process control even when every article sits inside its band.

The bands and the ceiling below are declared policy, not physical
constants: a project substitutes what its drawing fixes.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BULK_PROPERTY = "bulk-volume-resistivity"
SURFACE_PROPERTY = "surface-resistivity"
REQUIRED_PROPERTIES = (BULK_PROPERTY, SURFACE_PROPERTY)

GUARDED_ELECTRODE = "guarded-electrode"
CONCENTRIC_RING = "concentric-ring"
RECTANGULAR_BAR = "rectangular-bar"
RECOGNISED_SURFACE_GEOMETRIES = (CONCENTRIC_RING, RECTANGULAR_BAR)

REQUIREMENT_NOT_ESTABLISHED = "declared-band-not-established"
PROPERTY_SET_INCOMPLETE = "property-set-incomplete"
OUTSIDE_DECLARED_BAND = "outside-declared-band"
PROPERTIES_CHARACTERIZED = "both-properties-characterized"

DEFAULT_CHARACTERIZATION_POLICY = {
    "max_article_spread_decades": 2.0,
    "require_surface_ceiling_when_coated": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-300


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_characterization_policy(policy):
    """Check a characterization policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "max_article_spread_decades", policy.get("max_article_spread_decades")
    )
    _require_flag(
        "require_surface_ceiling_when_coated",
        policy.get("require_surface_ceiling_when_coated"),
    )
    return policy


def bulk_volume_resistivity_ohm_m(resistance_ohm, electrode_area_m2, thickness_m):
    """Volume resistivity through the glass from a guarded-electrode reading."""
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    area = _require_positive("electrode_area_m2", electrode_area_m2)
    thickness = _require_positive("thickness_m", thickness_m)
    return resistance * area / thickness


def concentric_ring_geometry_factor(inner_radius_m, outer_radius_m):
    """Geometry factor of a concentric-ring surface electrode pair."""
    inner = _require_positive("inner_radius_m", inner_radius_m)
    outer = _require_positive("outer_radius_m", outer_radius_m)
    if not outer > inner:
        raise ValueError(
            "outer_radius_m %g must be above inner_radius_m %g; rings that "
            "touch enclose no measurement gap" % (outer, inner)
        )
    return 2.0 * math.pi / math.log(outer / inner)


def rectangular_bar_geometry_factor(electrode_width_m, electrode_gap_m):
    """Geometry factor of a pair of parallel bar electrodes."""
    width = _require_positive("electrode_width_m", electrode_width_m)
    gap = _require_positive("electrode_gap_m", electrode_gap_m)
    return width / gap


def surface_resistivity_ohm_per_square(resistance_ohm, geometry_factor):
    """Sheet resistivity along the face from a resistance and a geometry factor."""
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    factor = _require_positive("geometry_factor", geometry_factor)
    return resistance * factor


def surface_geometry_factor(geometry):
    """Geometry factor for one declared surface electrode arrangement."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    arrangement = _require_label("geometry arrangement", geometry.get("arrangement"))
    if arrangement == CONCENTRIC_RING:
        return concentric_ring_geometry_factor(
            geometry.get("inner_radius_m"), geometry.get("outer_radius_m")
        )
    if arrangement == RECTANGULAR_BAR:
        return rectangular_bar_geometry_factor(
            geometry.get("electrode_width_m"), geometry.get("electrode_gap_m")
        )
    raise ValueError(
        "unknown surface electrode arrangement %r; recognised arrangements "
        "are %s" % (arrangement, ", ".join(RECOGNISED_SURFACE_GEOMETRIES))
    )


def reduce_article(article):
    """Reduce one measured coverglass to its two resistivity figures."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    identifier = _require_label("article id", article.get("id"))
    if not identifier:
        raise ValueError("article id must not be blank")
    coated = _require_flag("coating_present", article.get("coating_present"))

    bulk = None
    bulk_record = article.get("bulk_measurement")
    if bulk_record is not None:
        if not isinstance(bulk_record, dict):
            raise ValueError(
                "bulk_measurement on %s must be a mapping, got %r"
                % (identifier, bulk_record)
            )
        if "resistivity_ohm_m" in bulk_record:
            bulk = _require_positive(
                "resistivity_ohm_m on %s" % identifier,
                bulk_record.get("resistivity_ohm_m"),
            )
        else:
            bulk = bulk_volume_resistivity_ohm_m(
                bulk_record.get("resistance_ohm"),
                bulk_record.get("electrode_area_m2"),
                bulk_record.get("thickness_m"),
            )

    surface = None
    surface_record = article.get("surface_measurement")
    if surface_record is not None:
        if not isinstance(surface_record, dict):
            raise ValueError(
                "surface_measurement on %s must be a mapping, got %r"
                % (identifier, surface_record)
            )
        if "resistivity_ohm_per_square" in surface_record:
            surface = _require_positive(
                "resistivity_ohm_per_square on %s" % identifier,
                surface_record.get("resistivity_ohm_per_square"),
            )
        else:
            surface = surface_resistivity_ohm_per_square(
                surface_record.get("resistance_ohm"),
                surface_geometry_factor(surface_record.get("geometry")),
            )

    missing = []
    if bulk is None:
        missing.append(BULK_PROPERTY)
    if surface is None:
        missing.append(SURFACE_PROPERTY)

    return {
        "id": identifier,
        "coating_present": coated,
        "bulk_volume_resistivity_ohm_m": bulk,
        "surface_resistivity_ohm_per_square": surface,
        "missing_properties": tuple(missing),
        "properties_complete": not missing,
    }


def validate_declared_band(band):
    """Check the drawing-fixed bands can be judged against."""
    if not isinstance(band, dict):
        raise ValueError("declared band must be a mapping, got %r" % (band,))
    reference = _require_label("drawing_reference", band.get("drawing_reference"))
    low = _require_positive("bulk_min_ohm_m", band.get("bulk_min_ohm_m"))
    high = _require_positive("bulk_max_ohm_m", band.get("bulk_max_ohm_m"))
    if not high > low:
        raise ValueError(
            "bulk_max_ohm_m %g must be above bulk_min_ohm_m %g" % (high, low)
        )
    ceiling = band.get("surface_max_ohm_per_square")
    if ceiling is not None:
        ceiling = _require_positive("surface_max_ohm_per_square", ceiling)
    return reference, low, high, ceiling


def within_band(value, low, high):
    """True when a value sits inside a band; either edge is admissible."""
    number = _require_positive("value", value)
    lower = _require_positive("low", low)
    upper = _require_positive("high", high)
    if not upper > lower:
        raise ValueError("high must be above low")
    return _at_least(number, lower) and _at_most(number, upper)


def meets_surface_ceiling(value, ceiling):
    """True when a coating conducts at or better than its ceiling."""
    number = _require_positive("value", value)
    limit = _require_positive("ceiling", ceiling)
    return _at_most(number, limit)


def spread_ratio(values):
    """Largest over smallest across the measured articles."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    numbers = [_require_positive("value", value) for value in values]
    return max(numbers) / min(numbers)


def spread_decades(values):
    """The spread expressed in decades, for a process-control advisory."""
    return math.log10(spread_ratio(values))


def assess_electro_optical_properties(
    case, policy=DEFAULT_CHARACTERIZATION_POLICY
):
    """Full clause 8.7.3 characterization decision for one measured subgroup."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_characterization_policy(policy)

    findings = []
    advisories = []
    result = {
        "drawing_reference": None,
        "bulk_min_ohm_m": None,
        "bulk_max_ohm_m": None,
        "surface_max_ohm_per_square": None,
        "articles": [],
        "incomplete_ids": (),
        "outside_band_ids": (),
        "bulk_spread_decades": None,
        "surface_spread_decades": None,
        "findings": findings,
        "advisories": advisories,
    }

    band = case.get("declared_band")
    if band is None:
        findings.append(
            "no drawing-fixed resistivity band is referenced, so there is "
            "nothing these figures can be judged against"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result
    reference, low, high, ceiling = validate_declared_band(band)
    result["drawing_reference"] = reference
    result["bulk_min_ohm_m"] = low
    result["bulk_max_ohm_m"] = high
    result["surface_max_ohm_per_square"] = ceiling
    if not reference:
        findings.append(
            "the band carries no drawing reference; a resistivity limit with "
            "no drawing behind it is not the criterion of this clause"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result

    articles = case.get("articles")
    if not isinstance(articles, (list, tuple)):
        raise ValueError("case is missing an articles record")
    if not articles:
        raise ValueError(
            "no article was measured, so there is no behaviour to characterize"
        )

    reduced = []
    seen = set()
    coated_seen = False
    for article in articles:
        entry = reduce_article(article)
        if entry["id"] in seen:
            raise ValueError("duplicate article id %r in the record" % entry["id"])
        seen.add(entry["id"])
        if entry["coating_present"]:
            coated_seen = True
        reduced.append(entry)
    result["articles"] = reduced

    incomplete = tuple(e["id"] for e in reduced if not e["properties_complete"])
    result["incomplete_ids"] = incomplete
    for entry in reduced:
        if not entry["properties_complete"]:
            findings.append(
                "article %s reports only %s; the clause asks for the bulk and "
                "the surface behaviour together, and one number with a promise "
                "about the other is not a characterization"
                % (entry["id"], " and ".join(entry["missing_properties"]))
            )
    if incomplete:
        result["verdict"] = PROPERTY_SET_INCOMPLETE
        return result

    if coated_seen and ceiling is None:
        if policy["require_surface_ceiling_when_coated"]:
            findings.append(
                "a coated article is present and the drawing fixes no surface "
                "resistivity ceiling; the charge-bleed duty of the coating "
                "cannot be judged without one"
            )
            result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
            return result
        advisories.append(
            "no surface resistivity ceiling is declared, so the coated "
            "articles are reported as characterization only"
        )

    outside = []
    for entry in reduced:
        bulk = entry["bulk_volume_resistivity_ohm_m"]
        if not within_band(bulk, low, high):
            outside.append(entry["id"])
            findings.append(
                "article %s reads %.4g ohm metre bulk resistivity, outside the "
                "%.4g to %.4g ohm metre band of drawing %s"
                % (entry["id"], bulk, low, high, reference)
            )
        surface = entry["surface_resistivity_ohm_per_square"]
        if entry["coating_present"] and ceiling is not None:
            if not meets_surface_ceiling(surface, ceiling):
                if entry["id"] not in outside:
                    outside.append(entry["id"])
                findings.append(
                    "article %s reads %.4g ohm per square surface resistivity, "
                    "above the %.4g ohm per square ceiling; a coating that does "
                    "not conduct is not bleeding charge off the face"
                    % (entry["id"], surface, ceiling)
                )
        elif not entry["coating_present"]:
            advisories.append(
                "article %s carries no coating, so its %.4g ohm per square "
                "surface figure is characterization only and no ceiling is "
                "applied to it" % (entry["id"], surface)
            )
    result["outside_band_ids"] = tuple(outside)

    bulk_values = [e["bulk_volume_resistivity_ohm_m"] for e in reduced]
    surface_values = [e["surface_resistivity_ohm_per_square"] for e in reduced]
    result["bulk_spread_decades"] = spread_decades(bulk_values)
    result["surface_spread_decades"] = spread_decades(surface_values)
    spread_limit = float(policy["max_article_spread_decades"])
    for label, decades in (
        ("bulk", result["bulk_spread_decades"]),
        ("surface", result["surface_spread_decades"]),
    ):
        if not _at_most(decades, spread_limit):
            advisories.append(
                "the %s resistivity spread across the measured articles is "
                "%.2f decades against a %.2f decade expectation; every article "
                "can sit inside its band and the process still be adrift"
                % (label, decades, spread_limit)
            )

    if outside:
        result["verdict"] = OUTSIDE_DECLARED_BAND
        return result
    result["verdict"] = PROPERTIES_CHARACTERIZED
    return result

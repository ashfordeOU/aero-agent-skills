#!/usr/bin/env python3
"""Microsection examination of a crimp, where cross-sectioning is required.

Anchor: ECSS-Q-ST-70-26 Quality clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The microsection is the only view of what actually happened inside the
barrel. Height and pull-off measure the outside and the outcome; the
section measures the compression itself. Six things are read off it:

compression     the sectioned conductor area against the undeformed
                area of the same strands. Too little and the strands
                are still round with gas paths between them; too much
                and the material has been driven past its limit.
voids           unfilled space between strands and barrel. Each one is
                a path for gas and a place the cold weld did not form.
deformation     the strands that actually deformed. A bundle where the
                outer strands flattened and the core stayed round has
                a correct area and no weld in the middle.
wall thinning   the barrel wall at its thinnest. A wall driven thin is
                the crack that opens under thermal cycling.
plane           where the cut was taken. A section outside the crimp
                zone measures a barrel nobody compressed, and it is
                invalid rather than failing.
frequency       how many sections the lot and its setup changes
                demanded against how many were taken.

Dispositions rank accept < review < reject. Review is what an invalid
section and an unread characteristic earn: neither is a pass, and
neither is a defect.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MICRO_ACCEPT = "accept"
MICRO_REVIEW = "review"
MICRO_REJECT = "reject"

_RANK = {MICRO_ACCEPT: 0, MICRO_REVIEW: 1, MICRO_REJECT: 2}

COMPRESSION_IN_BAND = "in-band"
COMPRESSION_OVER = "over-compressed"
COMPRESSION_UNDER = "under-compressed"

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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    value = _require_count(name, value)
    if value == 0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A compression ratio is a quotient of two measured areas, so a
    section specified to land exactly on a band edge routinely
    evaluates a few units in the last place past it. The band is never
    relaxed; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = MICRO_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def validate_microsection_limits(table):
    """Normalise the per-contact microsection acceptance limits."""
    if not isinstance(table, dict) or not table:
        raise ValueError("limits table must be a non-empty mapping")
    normalised = {}
    for part, entry in table.items():
        if not isinstance(part, str) or not part.strip():
            raise ValueError("contact key must be a non-empty string, got %r" % (part,))
        if not isinstance(entry, dict):
            raise ValueError("contact %s entry must be a mapping" % part)
        ratio_min = _require_fraction(
            "contact %s compression_ratio_min" % part, entry.get("compression_ratio_min")
        )
        ratio_max = _require_fraction(
            "contact %s compression_ratio_max" % part, entry.get("compression_ratio_max")
        )
        if ratio_max < ratio_min:
            raise ValueError(
                "contact %s compression band is inverted: max %g below min %g"
                % (part, ratio_max, ratio_min)
            )
        if ratio_min <= 0.0:
            raise ValueError(
                "contact %s compression_ratio_min must be above zero; a band that "
                "starts at zero accepts a conductor that was cut through" % part
            )
        voids = _require_count(
            "contact %s max_void_count" % part, entry.get("max_void_count", 0)
        )
        void_area = _require_fraction(
            "contact %s max_void_area_fraction" % part,
            entry.get("max_void_area_fraction", 0.0),
        )
        deformed = _require_fraction(
            "contact %s min_deformed_strand_fraction" % part,
            entry.get("min_deformed_strand_fraction", 1.0),
        )
        wall = _require_fraction(
            "contact %s min_wall_fraction" % part, entry.get("min_wall_fraction")
        )
        if wall <= 0.0:
            raise ValueError(
                "contact %s min_wall_fraction must be above zero; a wall limit of "
                "zero accepts a barrel cut through" % part
            )
        zone_min = _require_non_negative(
            "contact %s crimp_zone_min_mm" % part, entry.get("crimp_zone_min_mm")
        )
        zone_max = _require_positive(
            "contact %s crimp_zone_max_mm" % part, entry.get("crimp_zone_max_mm")
        )
        if zone_max <= zone_min:
            raise ValueError(
                "contact %s crimp zone %g..%g mm has no width" % (part, zone_min, zone_max)
            )
        strands = _require_positive_count(
            "contact %s strand_count" % part, entry.get("strand_count")
        )
        normalised[part] = {
            "contact": part,
            "compression_ratio_min": ratio_min,
            "compression_ratio_max": ratio_max,
            "max_void_count": voids,
            "max_void_area_fraction": void_area,
            "min_deformed_strand_fraction": deformed,
            "min_wall_fraction": wall,
            "crimp_zone_min_mm": zone_min,
            "crimp_zone_max_mm": zone_max,
            "strand_count": strands,
        }
    return normalised


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict)
            and "compression_ratio_min" in entry
            and "contact" in entry
            for entry in table.values()
        )
    )


def lookup_microsection_limits(table, part):
    """Return the section limits for one contact; nothing is interpolated."""
    normalised = table if _looks_normalised(table) else validate_microsection_limits(table)
    if part not in normalised:
        raise ValueError(
            "contact %r is not tabulated (have %s); a compression band is not "
            "derived from a neighbouring part"
            % (part, ", ".join(sorted(normalised)))
        )
    return normalised[part]


def compression_ratio(deformed_area_mm2, undeformed_area_mm2):
    """Sectioned conductor area over the undeformed area of the same strands."""
    deformed = _require_positive("deformed_area_mm2", deformed_area_mm2)
    undeformed = _require_positive("undeformed_area_mm2", undeformed_area_mm2)
    if deformed > undeformed and not math.isclose(
        deformed, undeformed, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "sectioned conductor area %g mm2 exceeds the undeformed area %g mm2; "
            "compression cannot add material" % (deformed, undeformed)
        )
    return deformed / undeformed


def evaluate_compression(ratio, entry):
    """Grade the compression ratio against the two-sided band."""
    if ratio is None:
        return {
            "ratio": None,
            "read": False,
            "state": None,
            "disposition": MICRO_REVIEW,
            "findings": [
                "the compression ratio was not derived; the section is the only "
                "view of what the die actually did"
            ],
        }
    value = _require_positive("ratio", ratio)
    low = entry["compression_ratio_min"]
    high = entry["compression_ratio_max"]
    over = not _at_least(value, low)
    under = not _at_most(value, high)
    findings = []
    if over:
        state = COMPRESSION_OVER
        findings.append(
            "compression ratio %.4f is below the %.4f floor; the conductor has "
            "been driven past its limit and the strands are cut" % (value, low)
        )
    elif under:
        state = COMPRESSION_UNDER
        findings.append(
            "compression ratio %.4f is above the %.4f ceiling; the strands are "
            "still round and gas paths remain between them" % (value, high)
        )
    else:
        state = COMPRESSION_IN_BAND
    return {
        "ratio": value,
        "read": True,
        "compression_percent": (1.0 - value) * 100.0,
        "band_min": low,
        "band_max": high,
        "state": state,
        "disposition": MICRO_ACCEPT if state == COMPRESSION_IN_BAND else MICRO_REJECT,
        "findings": findings,
    }


def evaluate_voids(entry, void_count=None, void_area_mm2=None, bore_area_mm2=None):
    """Count the unfilled space between strands and barrel wall."""
    if void_count is None:
        return {
            "read": False,
            "void_count": None,
            "void_area_fraction": None,
            "disposition": MICRO_REVIEW,
            "findings": [
                "voids were not counted; an unfilled section is not assumed solid"
            ],
        }
    count = _require_count("void_count", void_count)
    findings = []
    dispositions = [MICRO_ACCEPT]
    if count > entry["max_void_count"]:
        dispositions.append(MICRO_REJECT)
        findings.append(
            "%d voids against an allowance of %d; each one is a gas path and a "
            "place the cold weld did not form" % (count, entry["max_void_count"])
        )
    fraction = None
    if void_area_mm2 is not None:
        area = _require_non_negative("void_area_mm2", void_area_mm2)
        bore = _require_positive("bore_area_mm2", bore_area_mm2)
        if area > bore and not math.isclose(
            area, bore, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "void area %g mm2 exceeds the %g mm2 bore it sits in" % (area, bore)
            )
        fraction = area / bore
        if not _at_most(fraction, entry["max_void_area_fraction"]):
            dispositions.append(MICRO_REJECT)
            findings.append(
                "void area is %.4f of the bore against a %.4f allowance"
                % (fraction, entry["max_void_area_fraction"])
            )
    elif count > 0:
        dispositions.append(MICRO_REVIEW)
        findings.append(
            "%d voids were counted but none were sized, so the area they occupy "
            "is unknown" % count
        )
    return {
        "read": True,
        "void_count": count,
        "void_area_fraction": fraction,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def evaluate_strand_deformation(entry, deformed_strands=None):
    """Check that the core strands deformed, not only the outer ones."""
    expected = entry["strand_count"]
    if deformed_strands is None:
        return {
            "read": False,
            "deformed": None,
            "expected": expected,
            "disposition": MICRO_REVIEW,
            "findings": [
                "strand deformation was not counted; a correct area can hide a "
                "core of strands that stayed round"
            ],
        }
    deformed = _require_count("deformed_strands", deformed_strands)
    if deformed > expected:
        raise ValueError(
            "%d deformed strands counted where the contact carries %d"
            % (deformed, expected)
        )
    fraction = deformed / expected
    required = entry["min_deformed_strand_fraction"]
    acceptable = _at_least(fraction, required)
    findings = []
    if not acceptable:
        findings.append(
            "%d of %d strands deformed, a fraction of %.4f against the %.4f "
            "required; the undeformed strands carry no weld"
            % (deformed, expected, fraction, required)
        )
    return {
        "read": True,
        "deformed": deformed,
        "expected": expected,
        "deformed_fraction": fraction,
        "required_fraction": required,
        "disposition": MICRO_ACCEPT if acceptable else MICRO_REJECT,
        "findings": findings,
    }


def evaluate_wall_thinning(entry, min_wall_mm=None, nominal_wall_mm=None):
    """Grade the barrel wall at its thinnest point against the nominal."""
    if min_wall_mm is None or nominal_wall_mm is None:
        return {
            "read": False,
            "wall_fraction": None,
            "disposition": MICRO_REVIEW,
            "findings": [
                "barrel wall thinning was not measured; the thinnest wall is "
                "where a thermal cycling crack opens"
            ],
        }
    thinnest = _require_positive("min_wall_mm", min_wall_mm)
    nominal = _require_positive("nominal_wall_mm", nominal_wall_mm)
    if thinnest > nominal and not math.isclose(
        thinnest, nominal, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "measured wall %g mm exceeds the %g mm nominal; compression does not "
            "thicken the barrel" % (thinnest, nominal)
        )
    fraction = thinnest / nominal
    required = entry["min_wall_fraction"]
    acceptable = _at_least(fraction, required)
    findings = []
    if not acceptable:
        findings.append(
            "the barrel wall is %.4f of nominal at its thinnest against a %.4f "
            "limit" % (fraction, required)
        )
    return {
        "read": True,
        "min_wall_mm": thinnest,
        "nominal_wall_mm": nominal,
        "wall_fraction": fraction,
        "required_fraction": required,
        "disposition": MICRO_ACCEPT if acceptable else MICRO_REJECT,
        "findings": findings,
    }


def evaluate_section_plane(plane_mm, entry):
    """Check the cut was taken inside the crimp zone.

    A section outside the zone measured a barrel nobody compressed. That
    is an invalid section, not a failing crimp, so it goes to review and
    the crimp is re-sectioned rather than dispositioned.
    """
    if plane_mm is None:
        return {
            "read": False,
            "plane_mm": None,
            "inside_zone": None,
            "disposition": MICRO_REVIEW,
            "findings": [
                "the section plane position was not recorded, so nothing read "
                "off this section can be placed in the crimp"
            ],
        }
    position = _require_non_negative("plane_mm", plane_mm)
    low = entry["crimp_zone_min_mm"]
    high = entry["crimp_zone_max_mm"]
    inside = _at_least(position, low) and _at_most(position, high)
    findings = []
    if not inside:
        findings.append(
            "the cut was taken at %.3f mm, outside the %.3f..%.3f mm crimp zone; "
            "this section measures a barrel the die never closed on, so it is "
            "invalid rather than failing" % (position, low, high)
        )
    return {
        "read": True,
        "plane_mm": position,
        "zone_min_mm": low,
        "zone_max_mm": high,
        "inside_zone": inside,
        "disposition": MICRO_ACCEPT if inside else MICRO_REVIEW,
        "findings": findings,
    }


def required_section_count(lot_size, interval, setup_changes=0):
    """One section per interval of crimps, plus one per setup change."""
    size = _require_positive_count("lot_size", lot_size)
    step = _require_positive_count("interval", interval)
    changes = _require_count("setup_changes", setup_changes)
    return -(-size // step) + changes


def evaluate_section_frequency(lot_size, interval, sections_taken, setup_changes=0):
    """Grade the sections taken against the ones the lot and setup demanded."""
    required = required_section_count(lot_size, interval, setup_changes)
    taken = _require_count("sections_taken", sections_taken)
    sufficient = taken >= required
    findings = []
    if not sufficient:
        findings.append(
            "%d sections were taken where the lot of %d at one per %d plus %d "
            "setup change(s) demands %d"
            % (taken, lot_size, interval, setup_changes, required)
        )
    return {
        "lot_size": lot_size,
        "interval": interval,
        "setup_changes": setup_changes,
        "required_sections": required,
        "sections_taken": taken,
        "shortfall": max(0, required - taken),
        "sufficient": sufficient,
        "disposition": MICRO_ACCEPT if sufficient else MICRO_REVIEW,
        "findings": findings,
    }


_CHECK_ORDER = (
    "section_plane",
    "compression",
    "voids",
    "strand_deformation",
    "wall_thinning",
)


def examine_microsection(case, table):
    """Full disposition for one crimp microsection."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    entry = lookup_microsection_limits(table, case.get("contact"))
    ratio = case.get("compression_ratio")
    if ratio is None and case.get("deformed_area_mm2") is not None:
        ratio = compression_ratio(
            case.get("deformed_area_mm2"), case.get("undeformed_area_mm2")
        )
    parts = {
        "section_plane": evaluate_section_plane(case.get("plane_mm"), entry),
        "compression": evaluate_compression(ratio, entry),
        "voids": evaluate_voids(
            entry,
            void_count=case.get("void_count"),
            void_area_mm2=case.get("void_area_mm2"),
            bore_area_mm2=case.get("bore_area_mm2"),
        ),
        "strand_deformation": evaluate_strand_deformation(
            entry, deformed_strands=case.get("deformed_strands")
        ),
        "wall_thinning": evaluate_wall_thinning(
            entry,
            min_wall_mm=case.get("min_wall_mm"),
            nominal_wall_mm=case.get("nominal_wall_mm"),
        ),
    }
    plane_valid = parts["section_plane"]["inside_zone"] is True
    if not plane_valid:
        disposition = MICRO_REVIEW
        driving = ["section_plane"]
    else:
        disposition = _worst(part["disposition"] for part in parts.values())
        driving = sorted(
            name
            for name, part in parts.items()
            if _RANK[part["disposition"]] == _RANK[disposition]
            and disposition != MICRO_ACCEPT
        )
    unread = sorted(name for name, part in parts.items() if not part["read"])
    findings = []
    for name in _CHECK_ORDER:
        findings.extend("%s: %s" % (name, text) for text in parts[name]["findings"])
    result = {
        "identifier": case.get("identifier", "unidentified"),
        "contact": entry["contact"],
        "section_valid": plane_valid,
        "disposition": disposition,
        "driving_checks": driving,
        "unread_characteristics": unread,
        "findings": findings,
    }
    result.update(parts)
    return result


def verify_microsection_programme(programme):
    """Roll the sectioning programme for one lot up into one disposition."""
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping, got %r" % (programme,))
    table = validate_microsection_limits(programme.get("limits_table"))
    sections = programme.get("sections")
    if not isinstance(sections, (list, tuple)) or not sections:
        raise ValueError("programme must carry a non-empty sections sequence")
    results = [examine_microsection(case, table) for case in sections]
    valid = [r for r in results if r["section_valid"]]
    frequency = evaluate_section_frequency(
        programme.get("lot_size"),
        programme.get("section_interval"),
        len(valid),
        setup_changes=programme.get("setup_changes", 0),
    )
    disposition = _worst(
        [frequency["disposition"]] + [r["disposition"] for r in results]
    )
    findings = ["frequency: %s" % text for text in frequency["findings"]]
    for result in results:
        findings.extend(
            "%s: %s" % (result["identifier"], text) for text in result["findings"]
        )
    ratios = [
        r["compression"]["ratio"] for r in valid if r["compression"]["ratio"] is not None
    ]
    return {
        "frequency": frequency,
        "section_count": len(results),
        "valid_section_count": len(valid),
        "invalid_section_count": len(results) - len(valid),
        "accepted": sum(1 for r in results if r["disposition"] == MICRO_ACCEPT),
        "review": sum(1 for r in results if r["disposition"] == MICRO_REVIEW),
        "rejected": sum(1 for r in results if r["disposition"] == MICRO_REJECT),
        "min_compression_ratio": min(ratios) if ratios else None,
        "max_compression_ratio": max(ratios) if ratios else None,
        "disposition": disposition,
        "not_accepted": [
            r["identifier"] for r in results if r["disposition"] != MICRO_ACCEPT
        ],
        "sections": results,
        "findings": findings,
    }

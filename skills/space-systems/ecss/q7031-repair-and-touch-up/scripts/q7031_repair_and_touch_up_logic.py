#!/usr/bin/env python3
"""Local repair and touch-up of an applied paint, with re-application limits.

Anchor: ECSS-Q-ST-70-31C, the Rework clause on repair and touch-up. The
procedure below is a paraphrased, implementable restatement -- no verbatim
standard text. Offline, deterministic, Python standard library only.

A local defect in a cured coat is repaired in place only while four budgets
still hold: how deep the defect goes, how much of the painted area the repairs
have consumed, how many times that same area has already been re-coated, and
what the extra film does to local thickness and to the mass budget. This module
grades a touch-up request against all four and dispositions it as a permitted
touch-up, a full strip and repaint, or a refusal.
"""

import math

__all__ = [
    "REPAIR_DEPTHS",
    "DEPTH_SCHEMES",
    "DEFAULT_AREA_FRACTION_LIMIT",
    "DEFAULT_REAPPLICATION_LIMIT",
    "categorize_repair_depth",
    "repair_scheme_for_depth",
    "touch_up_area_fraction",
    "within_area_limit",
    "reapplications_remaining",
    "projected_local_thickness_um",
    "blend_margin_sufficient",
    "added_mass_g",
    "assess_touch_up_request",
    "assess_repair_history",
]

# A fraction or a thickness that lands exactly on its limit is inside it.
# Decimal areas divided by decimal areas land a few ULP either side of a
# decimal bound depending on the maths library; these tolerances absorb that
# and nothing else. No engineering limit is widened by them.
REPAIR_REL_TOL = 1e-9
REPAIR_ABS_TOL = 1e-12

# How far the defect reaches determines what has to be rebuilt, which is the
# first question of a repair and not a cosmetic judgement.
REPAIR_DEPTHS = (
    "topcoat-only",
    "into-primer",
    "to-substrate",
    "substrate-damaged",
)

DEPTH_SCHEMES = {
    "topcoat-only": ("local-abrade", "topcoat"),
    "into-primer": ("local-abrade", "primer", "topcoat"),
    "to-substrate": ("local-abrade", "surface-preparation", "primer", "topcoat"),
}

DEFAULT_AREA_FRACTION_LIMIT = 0.05
DEFAULT_REAPPLICATION_LIMIT = 2
DEFAULT_BLEND_MARGIN_MM = 10.0
DEFAULT_RECOAT_INTERVAL_H = 4.0

CM2_PER_M2 = 10000.0
UM_PER_CM = 10000.0


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REPAIR_REL_TOL, abs_tol=REPAIR_ABS_TOL)


def categorize_repair_depth(depth):
    """Normalize how far a defect reaches into or through the coating system."""
    if not isinstance(depth, str) or not depth.strip():
        raise ValueError("depth must be a non-empty string")
    key = depth.strip().lower()
    if key not in REPAIR_DEPTHS:
        raise ValueError("unrecognized repair depth: %r" % (depth,))
    return key


def repair_scheme_for_depth(depth):
    """Return the ordered rebuild steps a defect of this depth owes.

    A defect that has damaged the substrate itself is not a paint repair. It is
    refused here rather than being papered over with a topcoat, because the
    disposition belongs to structures, not to the paint shop.
    """
    key = categorize_repair_depth(depth)
    if key == "substrate-damaged":
        raise ValueError(
            "substrate damage is not a coating repair; disposition it as hardware damage"
        )
    return DEPTH_SCHEMES[key]


def touch_up_area_fraction(repair_areas_cm2, painted_area_m2):
    """Fraction of the painted area that the repairs -- old and new -- consume."""
    painted = _finite_number(painted_area_m2, "painted_area_m2")
    if painted <= 0.0:
        raise ValueError("painted area must be strictly positive, got %r" % (painted_area_m2,))
    if not isinstance(repair_areas_cm2, (list, tuple)):
        raise ValueError("repair_areas_cm2 must be a sequence, got %r" % type(repair_areas_cm2))
    total = 0.0
    for index, area in enumerate(repair_areas_cm2):
        value = _finite_number(area, "repair area %d" % index)
        if value <= 0.0:
            raise ValueError("repair area %d must be strictly positive" % index)
        total += value
    return total / (painted * CM2_PER_M2)


def within_area_limit(fraction, limit=DEFAULT_AREA_FRACTION_LIMIT):
    """True when the repaired fraction does not exceed the allowed fraction."""
    value = _finite_number(fraction, "fraction")
    bound = _finite_number(limit, "limit")
    if value < 0.0:
        raise ValueError("repaired fraction cannot be negative, got %r" % (fraction,))
    if not 0.0 < bound <= 1.0:
        raise ValueError("area fraction limit must lie in (0,1], got %r" % (limit,))
    return _at_or_below(value, bound)


def reapplications_remaining(prior_applications, limit=DEFAULT_REAPPLICATION_LIMIT):
    """How many further local re-applications this area may still receive.

    Counted in whole applications, never below zero, so an area already at its
    limit reports no remaining budget rather than a negative one.
    """
    if isinstance(prior_applications, bool) or not isinstance(prior_applications, int):
        raise ValueError("prior_applications must be an integer, got %r" % (prior_applications,))
    if prior_applications < 0:
        raise ValueError("prior_applications cannot be negative")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("re-application limit must be a non-negative integer, got %r" % (limit,))
    return max(0, limit - prior_applications)


def projected_local_thickness_um(existing_um, added_um, removed_um=0.0):
    """Local film thickness after abrading back and re-applying.

    The abrasion that precedes a touch-up removes film, so the projection is
    what is left after the local abrade plus what the repair puts back.
    """
    existing = _finite_number(existing_um, "existing_um")
    added = _finite_number(added_um, "added_um")
    removed = _finite_number(removed_um, "removed_um")
    if existing <= 0.0:
        raise ValueError("existing thickness must be strictly positive, got %r" % (existing_um,))
    if added <= 0.0:
        raise ValueError("added thickness must be strictly positive, got %r" % (added_um,))
    if removed < 0.0:
        raise ValueError("removed thickness cannot be negative, got %r" % (removed_um,))
    if removed > existing:
        raise ValueError("abrasion removes more film than the area carries")
    return existing - removed + added


def blend_margin_sufficient(margin_mm, minimum_mm=DEFAULT_BLEND_MARGIN_MM):
    """True when the feathered blend around the repair is wide enough.

    A repair blended over too short a run leaves a visible and mechanically
    abrupt edge, which is where the next delamination starts.
    """
    margin = _finite_number(margin_mm, "margin_mm")
    floor = _finite_number(minimum_mm, "minimum_mm")
    if margin < 0.0:
        raise ValueError("blend margin cannot be negative, got %r" % (margin_mm,))
    if floor <= 0.0:
        raise ValueError("minimum blend margin must be strictly positive, got %r" % (minimum_mm,))
    return _at_or_below(floor, margin)


def added_mass_g(repair_area_cm2, added_um, density_g_cm3):
    """Mass the repair film adds, for the unit mass budget."""
    area = _finite_number(repair_area_cm2, "repair_area_cm2")
    added = _finite_number(added_um, "added_um")
    density = _finite_number(density_g_cm3, "density_g_cm3")
    if area <= 0.0:
        raise ValueError("repair area must be strictly positive, got %r" % (repair_area_cm2,))
    if added <= 0.0:
        raise ValueError("added thickness must be strictly positive, got %r" % (added_um,))
    if density <= 0.0:
        raise ValueError("density must be strictly positive, got %r" % (density_g_cm3,))
    return area * (added / UM_PER_CM) * density


def assess_touch_up_request(request):
    """Grade one touch-up request and issue its repair disposition."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % type(request))
    name = request.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("touch-up request requires a non-empty name")

    depth = categorize_repair_depth(request.get("depth"))
    findings = []
    if depth == "substrate-damaged":
        return {
            "name": name.strip(),
            "depth": depth,
            "scheme": (),
            "area_fraction": 0.0,
            "reapplications_remaining": 0,
            "projected_thickness_um": 0.0,
            "added_mass_g": 0.0,
            "findings": ["substrate-damage-not-a-coating-repair"],
            "disposition": "refused",
            "permitted": False,
        }
    scheme = repair_scheme_for_depth(depth)

    areas = list(request.get("prior_repair_areas_cm2", []))
    areas.append(request.get("repair_area_cm2"))
    fraction = touch_up_area_fraction(areas, request.get("painted_area_m2"))
    if not within_area_limit(fraction, request.get("area_fraction_limit", DEFAULT_AREA_FRACTION_LIMIT)):
        findings.append("repaired-area-fraction-exceeded")

    remaining = reapplications_remaining(
        request.get("prior_applications", 0),
        request.get("reapplication_limit", DEFAULT_REAPPLICATION_LIMIT),
    )
    if remaining == 0:
        findings.append("reapplication-limit-reached")

    projected = projected_local_thickness_um(
        request.get("existing_thickness_um"),
        request.get("added_thickness_um"),
        request.get("removed_thickness_um", 0.0),
    )
    maximum = _finite_number(request.get("maximum_thickness_um"), "maximum_thickness_um")
    if maximum <= 0.0:
        raise ValueError("maximum_thickness_um must be strictly positive")
    if not _at_or_below(projected, maximum):
        findings.append("local-thickness-above-maximum")

    if not blend_margin_sufficient(
        request.get("blend_margin_mm", 0.0),
        request.get("minimum_blend_margin_mm", DEFAULT_BLEND_MARGIN_MM),
    ):
        findings.append("blend-margin-too-narrow")

    interval = _finite_number(request.get("hours_since_last_coat", DEFAULT_RECOAT_INTERVAL_H),
                              "hours_since_last_coat")
    minimum_interval = _finite_number(
        request.get("minimum_recoat_interval_h", DEFAULT_RECOAT_INTERVAL_H),
        "minimum_recoat_interval_h",
    )
    if interval < 0.0 or minimum_interval <= 0.0:
        raise ValueError("recoat interval values must be non-negative and the minimum positive")
    if not _at_or_below(minimum_interval, interval):
        findings.append("recoat-interval-not-met")

    mass = added_mass_g(
        request.get("repair_area_cm2"),
        request.get("added_thickness_um"),
        request.get("paint_density_g_cm3", 1.4),
    )
    allowance = request.get("mass_allowance_g")
    if allowance is not None and not _at_or_below(mass, _finite_number(allowance, "mass_allowance_g")):
        findings.append("repair-mass-allowance-exceeded")

    findings = sorted(set(findings))
    strip_drivers = {
        "repaired-area-fraction-exceeded",
        "reapplication-limit-reached",
        "local-thickness-above-maximum",
    }
    if not findings:
        disposition = "touch-up-permitted"
    elif strip_drivers.intersection(findings):
        disposition = "strip-and-repaint-required"
    else:
        disposition = "corrective-action-required"
    return {
        "name": name.strip(),
        "depth": depth,
        "scheme": scheme,
        "area_fraction": fraction,
        "reapplications_remaining": remaining,
        "projected_thickness_um": projected,
        "added_mass_g": mass,
        "findings": findings,
        "disposition": disposition,
        "permitted": disposition == "touch-up-permitted",
    }


def assess_repair_history(requests):
    """Grade a set of touch-up requests on one unit and summarise the outcome."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("at least one touch-up request is required")
    results = [assess_touch_up_request(item) for item in requests]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("touch-up request names must be unique within a history")
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "requests": results,
        "strip_required": sorted(
            i["name"] for i in results if i["disposition"] == "strip-and-repaint-required"
        ),
        "refused": sorted(i["name"] for i in results if i["disposition"] == "refused"),
        "total_added_mass_g": sum(i["added_mass_g"] for i in results),
        "open_findings": open_findings,
        "history_accepted": not open_findings,
    }

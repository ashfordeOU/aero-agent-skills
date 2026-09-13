#!/usr/bin/env python3
"""Surface-material electrical-control applicability (ECSS-E-ST-20-06C 6.1.1).

Deterministic, offline, stdlib-only support logic for deciding where the
surface-material electrical-control rules apply on a spacecraft, and what
the in-scope surfaces must demonstrate.

The module answers three questions for every external item:

1. Is the item exposed to the ambient plasma at all (exposure category)?
2. How severe is the charging environment of the mission orbit-regime?
3. Does the outer layer actually move collected charge to structure-ground
   (surface-resistivity screening plus charge-bleed-path resistance)?

All comparisons against a ceiling are made with a relative tolerance so an
exactly-at-the-ceiling value -- which is physically compliant -- is not
rejected because of floating-point representation error. The ceiling values
themselves are never widened.
"""

import math

__all__ = [
    "ORBIT_REGIME_SEVERITY",
    "EXPOSURE_CATEGORIES",
    "REQUIREMENT_LEVELS",
    "SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE",
    "BLEED_PATH_RESISTANCE_CEILING_OHM",
    "REL_TOL",
    "regime_severity",
    "categorize_exposure",
    "requirement_level",
    "bleed_path_resistance",
    "required_volume_resistivity",
    "at_or_below_ceiling",
    "screen_surface",
    "assess_item",
    "assess_inventory",
]

# --- constants ------------------------------------------------------------

# Ambient-plasma severity rank of each mission regime. Higher is harsher.
# 4 = hot tenuous plasma with substorm injections, 1 = dense cold ionosphere
# that clamps an exposed surface close to the ambient potential.
ORBIT_REGIME_SEVERITY = {
    "geostationary-orbit": 4,
    "highly-elliptical-orbit": 4,
    "medium-earth-orbit": 3,
    "polar-low-earth-orbit": 3,
    "interplanetary-cruise": 2,
    "equatorial-low-earth-orbit": 1,
}

EXPOSURE_CATEGORIES = ("plasma-exposed", "partially-shielded", "internal")

REQUIREMENT_LEVELS = ("full", "reduced", "none")

# Screening ceilings used by the applicability decision. A surface at or
# below both behaves as a controlled-conductive surface; above either one it
# is a floating-dielectric surface and carries a finding.
SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE = 1.0e9
BLEED_PATH_RESISTANCE_CEILING_OHM = 1.0e9

# Relative tolerance that absorbs representation error at an exact ceiling.
REL_TOL = 1.0e-9

_SEVERE = 4
_INTERMEDIATE = 3
_MILD_MAX = 2


# --- primitives -----------------------------------------------------------


def _finite_positive(value, label):
    """Return value as a float, or raise ValueError if it is not positive."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, out))
    return out


def regime_severity(regime):
    """Severity rank (1..4) of the ambient-plasma environment of a regime.

    An unrecognized regime is rejected rather than defaulted to the severe
    case: a silent worst-case default hides a missing environment
    specification behind a conservative-looking verdict.
    """
    if not isinstance(regime, str) or not regime.strip():
        raise ValueError("orbit regime must be a non-empty string, got %r" % (regime,))
    key = regime.strip().lower()
    if key not in ORBIT_REGIME_SEVERITY:
        raise ValueError(
            "unknown orbit regime %r; known: %s"
            % (regime, ", ".join(sorted(ORBIT_REGIME_SEVERITY)))
        )
    return ORBIT_REGIME_SEVERITY[key]


def categorize_exposure(item):
    """Categorize one item as plasma-exposed, partially-shielded or internal.

    Required keys: ``external`` (bool) and ``shield_coverage_fraction``
    (0.0..1.0). Optional ``ambient_plasma_view`` defaults to True for an
    external item.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (type(item).__name__,))
    if "external" not in item:
        raise ValueError("item %r has no 'external' flag" % (item.get("name"),))
    if not item["external"]:
        return "internal"
    if not item.get("ambient_plasma_view", True):
        return "internal"
    if "shield_coverage_fraction" not in item:
        raise ValueError(
            "external item %r has no 'shield_coverage_fraction'" % (item.get("name"),)
        )
    try:
        cov = float(item["shield_coverage_fraction"])
    except (TypeError, ValueError):
        raise ValueError(
            "shield_coverage_fraction must be a real number, got %r"
            % (item["shield_coverage_fraction"],)
        )
    if not math.isfinite(cov) or cov < 0.0 or cov > 1.0:
        raise ValueError("shield_coverage_fraction must be within 0..1, got %r" % (cov,))
    if cov >= 1.0:
        return "internal"
    if cov > 0.0:
        return "partially-shielded"
    return "plasma-exposed"


def requirement_level(exposure, severity):
    """Map (exposure category, severity rank) to the requirement level."""
    if exposure not in EXPOSURE_CATEGORIES:
        raise ValueError(
            "unknown exposure category %r; known: %s"
            % (exposure, ", ".join(EXPOSURE_CATEGORIES))
        )
    if not isinstance(severity, int) or isinstance(severity, bool):
        raise ValueError("severity rank must be an int, got %r" % (severity,))
    if severity < 1 or severity > _SEVERE:
        raise ValueError("severity rank must be within 1..%d, got %d" % (_SEVERE, severity))
    if exposure == "internal":
        return "none"
    if exposure == "partially-shielded":
        return "reduced"
    return "full" if severity >= _INTERMEDIATE else "reduced"


def bleed_path_resistance(volume_resistivity_ohm_m, thickness_m, contact_area_m2):
    """Resistance through the outer layer to the grounded backing (ohm).

    R = rho_v * t / A -- the path that actually carries collected charge away
    runs from the outer face, through the layer thickness, into the grounded
    contact area.
    """
    rho = _finite_positive(volume_resistivity_ohm_m, "volume_resistivity_ohm_m")
    t = _finite_positive(thickness_m, "thickness_m")
    a = _finite_positive(contact_area_m2, "contact_area_m2")
    return rho * t / a


def required_volume_resistivity(target_resistance_ohm, thickness_m, contact_area_m2):
    """Inverse of :func:`bleed_path_resistance`: rho_v for a target R."""
    r = _finite_positive(target_resistance_ohm, "target_resistance_ohm")
    t = _finite_positive(thickness_m, "thickness_m")
    a = _finite_positive(contact_area_m2, "contact_area_m2")
    return r * a / t


def at_or_below_ceiling(value, ceiling, rel_tol=REL_TOL):
    """True when value <= ceiling, absorbing representation error at equality."""
    v = float(value)
    c = float(ceiling)
    if not math.isfinite(v) or not math.isfinite(c):
        raise ValueError("value and ceiling must be finite, got %r and %r" % (value, ceiling))
    if v <= c:
        return True
    return math.isclose(v, c, rel_tol=rel_tol, abs_tol=0.0)


def screen_surface(item):
    """Screen one in-scope item's outer layer; return findings list.

    Findings are emitted separately per failure mode so a report never
    collapses two distinct causes into one line.
    """
    findings = []
    name = item.get("name", "<unnamed>")

    rho_s = item.get("surface_resistivity_ohm_per_square")
    if rho_s is None:
        findings.append("%s: surface-resistivity not on record" % name)
    else:
        rho_s = _finite_positive(rho_s, "surface_resistivity_ohm_per_square")
        if not at_or_below_ceiling(rho_s, SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE):
            findings.append(
                "%s: surface-resistivity %.3e above ceiling %.3e"
                % (name, rho_s, SURFACE_RESISTIVITY_CEILING_OHM_PER_SQUARE)
            )

    have_path = all(
        item.get(k) is not None
        for k in ("volume_resistivity_ohm_m", "thickness_m", "contact_area_m2")
    )
    if not have_path:
        findings.append("%s: charge-bleed-path data incomplete" % name)
    else:
        resistance = bleed_path_resistance(
            item["volume_resistivity_ohm_m"],
            item["thickness_m"],
            item["contact_area_m2"],
        )
        if not at_or_below_ceiling(resistance, BLEED_PATH_RESISTANCE_CEILING_OHM):
            findings.append(
                "%s: charge-bleed-path resistance %.3e above ceiling %.3e"
                % (name, resistance, BLEED_PATH_RESISTANCE_CEILING_OHM)
            )

    if not item.get("bonded_to_structure_ground", False):
        findings.append("%s: no structure-ground bond on record" % name)
    return findings


def assess_item(item, regime):
    """Full clause-6.1.1 applicability verdict for one item."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (type(item).__name__,))
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item needs a non-empty 'name'")
    material = item.get("outer_material")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("item %r needs a non-empty 'outer_material'" % (name,))

    severity = regime_severity(regime)
    exposure = categorize_exposure(item)
    level = requirement_level(exposure, severity)
    applicable = level != "none"
    findings = screen_surface(item) if applicable else []
    return {
        "name": name,
        "outer_material": material,
        "exposure": exposure,
        "severity": severity,
        "requirement_level": level,
        "applicable": applicable,
        "surface_category": (
            "out-of-scope"
            if not applicable
            else ("controlled-conductive" if not findings else "floating-dielectric")
        ),
        "findings": findings,
    }


def assess_inventory(items, regime):
    """Assess every item; aggregate counts and the open-findings list."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty list of item mappings")
    seen = set()
    results = []
    for item in items:
        result = assess_item(item, regime)
        if result["name"] in seen:
            raise ValueError("duplicate item name %r in inventory" % (result["name"],))
        seen.add(result["name"])
        results.append(result)
    in_scope = [r for r in results if r["applicable"]]
    open_findings = [f for r in results for f in r["findings"]]
    return {
        "regime": regime.strip().lower(),
        "severity": regime_severity(regime),
        "item_count": len(results),
        "in_scope_count": len(in_scope),
        "out_of_scope_count": len(results) - len(in_scope),
        "full_level_count": sum(1 for r in in_scope if r["requirement_level"] == "full"),
        "reduced_level_count": sum(1 for r in in_scope if r["requirement_level"] == "reduced"),
        "open_findings": open_findings,
        "applicability_complete": not open_findings,
        "items": results,
    }

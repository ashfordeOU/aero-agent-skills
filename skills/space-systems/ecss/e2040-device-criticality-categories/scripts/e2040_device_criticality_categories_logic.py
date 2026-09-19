#!/usr/bin/env python3
"""Criticality categorisation of device products and its consequences.

Anchor: ECSS-E-ST-20-40 clause 6.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A device product is placed in a criticality category from the
consequence of its worst credible failure, then moved at most one step
down where the architecture around it genuinely mitigates that failure.

    severity            base category
    catastrophic        category-1
    critical            category-2
    major               category-3
    minor               category-4

The single step of credit is conditional. The redundant path must exist,
must be independent of the path it backs up, and the failure must be
detected by a route the scheme can use in time: a cold standby needs
onboard detection, a hot or cross-strapped path can be credited on
ground detection.

The category is then a budget for assurance: parts screening level,
derating factor, qualification route, review depth and the delivered
documentation all descend from it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SEVERITY_LEVELS = ("catastrophic", "critical", "major", "minor")
CATEGORIES = ("category-1", "category-2", "category-3", "category-4")
REDUNDANCY_SCHEMES = ("none", "cold-standby", "hot-standby", "cross-strapped")
DETECTION_ROUTES = ("detected-onboard", "detected-on-ground", "undetected")
DERATING_PARAMETERS = ("voltage", "current", "power", "junction-temperature")

BASE_CATEGORY_BY_SEVERITY = {
    "catastrophic": "category-1",
    "critical": "category-2",
    "major": "category-3",
    "minor": "category-4",
}

DETECTION_ROUTES_CREDITED = {
    "cold-standby": ("detected-onboard",),
    "hot-standby": ("detected-onboard", "detected-on-ground"),
    "cross-strapped": ("detected-onboard", "detected-on-ground"),
}

CATEGORY_IMPLICATIONS = {
    "category-1": {
        "parts_screening_level": "level-1",
        "qualification_route": "dedicated-qualification",
        "review_depth": "full-formal-review-set",
        "single_point_failure_permitted": False,
        "documentation": (
            "device-specification",
            "design-justification-file",
            "qualification-report",
            "acceptance-data-package",
            "single-point-failure-analysis",
        ),
    },
    "category-2": {
        "parts_screening_level": "level-1",
        "qualification_route": "dedicated-qualification",
        "review_depth": "full-formal-review-set",
        "single_point_failure_permitted": False,
        "documentation": (
            "device-specification",
            "design-justification-file",
            "qualification-report",
            "acceptance-data-package",
        ),
    },
    "category-3": {
        "parts_screening_level": "level-2",
        "qualification_route": "qualification-by-similarity-admissible",
        "review_depth": "delta-review-set",
        "single_point_failure_permitted": True,
        "documentation": (
            "device-specification",
            "qualification-report",
            "acceptance-data-package",
        ),
    },
    "category-4": {
        "parts_screening_level": "level-3",
        "qualification_route": "qualification-by-similarity-admissible",
        "review_depth": "supplier-internal-review",
        "single_point_failure_permitted": True,
        "documentation": ("device-specification", "acceptance-data-package"),
    },
}

DERATING_FACTORS = {
    "category-1": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.50,
        "junction-temperature": 0.60,
    },
    "category-2": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.60,
        "junction-temperature": 0.70,
    },
    "category-3": {
        "voltage": 0.70,
        "current": 0.70,
        "power": 0.70,
        "junction-temperature": 0.80,
    },
    "category-4": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.80,
        "junction-temperature": 0.85,
    },
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A derated limit is a product of a rating and a factor, so a stress
    placed deliberately on the limit can read a few units in the last
    place above it. The limit is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def base_category(severity):
    """Category the failure consequence alone puts the device in."""
    _require_choice("severity", severity, SEVERITY_LEVELS)
    return BASE_CATEGORY_BY_SEVERITY[severity]


def demote_one_step(category):
    """Move a category one step down; the bottom category does not move."""
    _require_choice("category", category, CATEGORIES)
    index = CATEGORIES.index(category)
    return CATEGORIES[min(index + 1, len(CATEGORIES) - 1)]


def redundancy_credit(redundancy_scheme, independent, detection_route):
    """Is the single step of redundancy credit earned, and if not why not."""
    _require_choice("redundancy_scheme", redundancy_scheme, REDUNDANCY_SCHEMES)
    _require_choice("detection_route", detection_route, DETECTION_ROUTES)
    if not isinstance(independent, bool):
        raise ValueError("independent must be a boolean, got %r" % (independent,))
    findings = []
    if redundancy_scheme == "none":
        findings.append(
            "no redundant path exists, so no criticality credit is available"
        )
        return {"credited": False, "findings": findings}
    if not independent:
        findings.append(
            "the %s path shares a cause with the path it backs up; both "
            "branches fail together and no credit is available"
            % redundancy_scheme
        )
    credited_routes = DETECTION_ROUTES_CREDITED[redundancy_scheme]
    if detection_route not in credited_routes:
        findings.append(
            "a %s path can only be credited on %s detection, and the failure "
            "is %s" % (redundancy_scheme, " or ".join(credited_routes), detection_route)
        )
    return {"credited": not findings, "findings": findings}


def category_implications(category):
    """Assurance obligations the category carries."""
    _require_choice("category", category, CATEGORIES)
    implications = dict(CATEGORY_IMPLICATIONS[category])
    implications["derating_factors"] = dict(DERATING_FACTORS[category])
    return implications


def derated_limit(nominal_rating, category, parameter):
    """Operating stress the category permits against a device rating."""
    rating = _require_positive("nominal_rating", nominal_rating)
    _require_choice("category", category, CATEGORIES)
    _require_choice("parameter", parameter, DERATING_PARAMETERS)
    return rating * DERATING_FACTORS[category][parameter]


def within_derating(applied_value, nominal_rating, category, parameter):
    """Does an applied stress sit inside the category derating limit."""
    applied = _require_non_negative("applied_value", applied_value)
    return _at_most(applied, derated_limit(nominal_rating, category, parameter))


def categorise_device(device):
    """Place one device product and read off what its category demands."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    identifier = device.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("device needs a non-empty id, got %r" % (identifier,))
    severity = _require_choice("severity", device.get("severity"), SEVERITY_LEVELS)
    scheme = _require_choice(
        "redundancy_scheme", device.get("redundancy_scheme"), REDUNDANCY_SCHEMES
    )
    detection = _require_choice(
        "detection_route", device.get("detection_route"), DETECTION_ROUTES
    )
    independent = device.get("independent_redundancy", False)
    credit = redundancy_credit(scheme, independent, detection)

    start = base_category(severity)
    category = demote_one_step(start) if credit["credited"] else start
    findings = list(credit["findings"])

    single_point = scheme == "none" or not independent
    implications = category_implications(category)
    if single_point and not implications["single_point_failure_permitted"]:
        findings.append(
            "device %s is a single-point failure and %s does not permit one "
            "without an approved deviation" % (identifier.strip(), category)
        )

    derating_verdicts = {}
    applied = device.get("applied_stress", {})
    if not isinstance(applied, dict):
        raise ValueError("applied_stress must be a mapping, got %r" % (applied,))
    for parameter, values in sorted(applied.items()):
        _require_choice("applied_stress parameter", parameter, DERATING_PARAMETERS)
        if not isinstance(values, dict):
            raise ValueError("applied_stress[%s] must be a mapping" % parameter)
        limit = derated_limit(values.get("rating"), category, parameter)
        ok = within_derating(values.get("applied"), values.get("rating"), category, parameter)
        derating_verdicts[parameter] = {"limit": limit, "compliant": ok}
        if not ok:
            findings.append(
                "applied %s of %.6g exceeds the %s derated limit of %.6g"
                % (parameter, float(values["applied"]), category, limit)
            )

    return {
        "id": identifier.strip(),
        "severity": severity,
        "base_category": start,
        "category": category,
        "redundancy_credited": credit["credited"],
        "single_point_failure": single_point,
        "implications": implications,
        "derating_verdicts": derating_verdicts,
        "findings": findings,
    }


def categorise_device_list(devices):
    """Roll a device list up to counts, the governing category and the SPF list."""
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must be a non-empty sequence")
    results = []
    seen = set()
    for device in devices:
        result = categorise_device(device)
        if result["id"] in seen:
            raise ValueError("duplicate device id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
    counts = {category: 0 for category in CATEGORIES}
    for result in results:
        counts[result["category"]] += 1
    governing = min(results, key=lambda r: CATEGORIES.index(r["category"]))["category"]
    return {
        "devices": results,
        "counts": counts,
        "governing_category": governing,
        "single_point_failures": [r["id"] for r in results if r["single_point_failure"]],
        "deviation_required": [
            r["id"]
            for r in results
            if r["single_point_failure"]
            and not r["implications"]["single_point_failure_permitted"]
        ],
    }

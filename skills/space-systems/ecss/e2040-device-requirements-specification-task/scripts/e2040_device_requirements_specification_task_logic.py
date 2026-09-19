#!/usr/bin/env python3
"""Definition-phase requirements specification task (ECSS-E-ST-20-40C 5.2.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The task is to produce the complete requirement set for the device during
the definition phase. Completeness here is a property of the traces, not
of the line count, and it runs in two directions:

* upward -- every device requirement comes from somewhere. An allocated
  requirement names a source requirement that has to exist; a derived one
  names no parent and owes a justification instead; a heritage one names
  the configuration it was inherited from;
* downward -- every mandatory source requirement ends up in at least one
  device requirement. A set checked only upward is perfectly traceable
  and can still be missing a whole capability.

Two figures are reported alongside the traces. Coverage is the fraction
of mandatory source requirements reached by the device set, and the open
fraction is the share of device requirements still carrying a to-be-
determined marker, compared against the budget the project allows rather
than banned outright. Both land exactly on their bounds, so the
comparisons absorb the representation error of a division.
"""

import math
import re

# How a device requirement came to exist.
ORIGINS = ("allocated", "derived", "heritage")
_ORIGIN_ALIASES = {
    "allocated": "allocated",
    "flowed-down": "allocated",
    "flowed down": "allocated",
    "refined": "allocated",
    "derived": "derived",
    "engineering-derived": "derived",
    "heritage": "heritage",
    "reused": "heritage",
    "recurring": "heritage",
}

# Content areas the device requirement set is organised into.
CONTENT_AREAS = (
    "function",
    "performance",
    "interface",
    "environment",
    "operation",
    "quality",
)
_AREA_ALIASES = {
    "function": "function",
    "functional": "function",
    "performance": "performance",
    "interface": "interface",
    "interfaces": "interface",
    "environment": "environment",
    "environmental": "environment",
    "operation": "operation",
    "operational": "operation",
    "operations": "operation",
    "quality": "quality",
    "product assurance": "quality",
}

# Markers that say a value is not settled yet.
_OPEN_MARKER = re.compile(r"\bTB[DCS]\b|\bto be (?:determined|confirmed)\b", re.I)

REL_TOL = 1e-12
ABS_TOL = 1e-18

_SPEC_REQUIRED_KEYS = ("sources", "requirements")
_SPEC_OPTIONAL_KEYS = ("declared_areas", "open_item_budget", "coverage_target")
_SOURCE_KEYS = ("id", "title", "mandatory")
_REQUIREMENT_KEYS = (
    "id",
    "area",
    "origin",
    "parents",
    "statement",
    "justification",
    "heritage_item",
)


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_coverage_target(achieved, target):
    """True when coverage reaches the target, exact landings included."""
    achieved = _fraction("achieved", achieved)
    target = _fraction("target", target)
    return achieved > target or math.isclose(
        achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def within_open_item_budget(fraction, budget):
    """True when the open fraction stays inside the budget, bound included."""
    fraction = _fraction("fraction", fraction)
    budget = _fraction("budget", budget)
    return fraction < budget or math.isclose(
        fraction, budget, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_origin(value):
    """Fold an origin spelling onto allocated, derived or heritage."""
    key = _key(_text("origin", value))
    for candidate in (key, key.replace(" ", "-")):
        if candidate in _ORIGIN_ALIASES:
            return _ORIGIN_ALIASES[candidate]
    raise ValueError(
        "unknown requirement origin %r; use one of %s" % (value, ", ".join(ORIGINS))
    )


def normalize_area(value):
    """Fold a content area spelling onto one of the recognised areas."""
    key = _key(_text("area", value))
    if key in _AREA_ALIASES:
        return _AREA_ALIASES[key]
    raise ValueError(
        "unknown content area %r; use one of %s" % (value, ", ".join(CONTENT_AREAS))
    )


def has_open_marker(statement):
    """True when a requirement statement still carries an open marker."""
    return bool(_OPEN_MARKER.search(_text("statement", statement, allow_empty=True)))


def validate_sources(entries):
    """Check the source requirement set and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("sources must be a list of source requirements")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("sources[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_SOURCE_KEYS))
        if unknown:
            raise ValueError(
                "sources[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("sources[%d] missing key: id" % index)
        source_id = _text("sources[%d].id" % index, entry["id"])
        if source_id in seen:
            raise ValueError("duplicate source requirement id %r" % source_id)
        seen.add(source_id)
        resolved.append(
            {
                "id": source_id,
                "title": _text(
                    "sources[%d].title" % index,
                    entry.get("title", ""),
                    allow_empty=True,
                ),
                "mandatory": _flag(
                    "sources[%d].mandatory" % index, entry.get("mandatory", True)
                ),
            }
        )
    return resolved


def validate_requirements(entries):
    """Check the device requirement set and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("requirements must be a list of device requirements")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("requirements[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_REQUIREMENT_KEYS))
        if unknown:
            raise ValueError(
                "requirements[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "area", "origin"):
            if key not in entry:
                raise ValueError("requirements[%d] missing key: %s" % (index, key))
        req_id = _text("requirements[%d].id" % index, entry["id"])
        if req_id in seen:
            raise ValueError("duplicate device requirement id %r" % req_id)
        seen.add(req_id)
        parents = entry.get("parents", [])
        if not isinstance(parents, (list, tuple)):
            raise ValueError("requirements[%d].parents must be a list" % index)
        parent_ids = []
        for position, parent in enumerate(parents):
            name = _text("requirements[%d].parents[%d]" % (index, position), parent)
            if name not in parent_ids:
                parent_ids.append(name)
        resolved.append(
            {
                "id": req_id,
                "area": normalize_area(entry["area"]),
                "origin": normalize_origin(entry["origin"]),
                "parents": parent_ids,
                "statement": _text(
                    "requirements[%d].statement" % index,
                    entry.get("statement", ""),
                    allow_empty=True,
                ),
                "justification": _text(
                    "requirements[%d].justification" % index,
                    entry.get("justification", ""),
                    allow_empty=True,
                ),
                "heritage_item": _text(
                    "requirements[%d].heritage_item" % index,
                    entry.get("heritage_item", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def mandatory_sources(sources):
    """Source requirements the device set has to answer."""
    return [source for source in sources if source["mandatory"]]


def uncovered_sources(sources, requirements):
    """Mandatory source ids no device requirement points at."""
    reached = {parent for req in requirements for parent in req["parents"]}
    return sorted(
        source["id"] for source in mandatory_sources(sources)
        if source["id"] not in reached
    )


def source_coverage(sources, requirements):
    """Fraction of mandatory source requirements reached by the device set."""
    mandatory = mandatory_sources(sources)
    if not mandatory:
        raise ValueError("source_coverage needs at least one mandatory source")
    missing = len(uncovered_sources(sources, requirements))
    return (len(mandatory) - missing) / len(mandatory)


def dangling_parents(sources, requirements):
    """Parent identifiers that name nothing in the source set."""
    known = {source["id"] for source in sources}
    out = []
    for requirement in requirements:
        for parent in requirement["parents"]:
            if parent not in known:
                out.append({"requirement": requirement["id"], "parent": parent})
    return out


def open_item_fraction(requirements):
    """Share of the device set still carrying an open marker."""
    if not requirements:
        raise ValueError("open_item_fraction needs at least one requirement")
    open_count = sum(1 for req in requirements if has_open_marker(req["statement"]))
    return open_count / len(requirements)


def unpopulated_areas(requirements, declared_areas):
    """Declared content areas holding no requirement at all."""
    present = {req["area"] for req in requirements}
    return [area for area in declared_areas if area not in present]


def specify_requirement_set(spec):
    """Full clause 5.2.2 assessment of one definition-phase requirement set.

    Returns the coverage and open-item figures, the findings and whether
    the set can be baselined.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of sources and requirements")
    known = set(_SPEC_REQUIRED_KEYS) | set(_SPEC_OPTIONAL_KEYS)
    unknown = sorted(set(spec) - known)
    if unknown:
        raise ValueError("unknown spec keys: %s" % ", ".join(unknown))
    missing = [key for key in _SPEC_REQUIRED_KEYS if key not in spec]
    if missing:
        raise ValueError("spec missing required keys: %s" % ", ".join(missing))

    sources = validate_sources(spec["sources"])
    requirements = validate_requirements(spec["requirements"])
    if not sources:
        raise ValueError("spec must carry at least one source requirement")
    if not requirements:
        raise ValueError("spec must carry at least one device requirement")
    if not mandatory_sources(sources):
        raise ValueError("spec must carry at least one mandatory source requirement")

    raw_areas = spec.get("declared_areas", CONTENT_AREAS)
    if not isinstance(raw_areas, (list, tuple)):
        raise ValueError("declared_areas must be a list of content areas")
    declared_areas = []
    for area in raw_areas:
        folded = normalize_area(area)
        if folded not in declared_areas:
            declared_areas.append(folded)
    if not declared_areas:
        raise ValueError("declared_areas must name at least one content area")

    budget = _fraction("open_item_budget", spec.get("open_item_budget", 0.2))
    target = _fraction("coverage_target", spec.get("coverage_target", 1.0))

    findings = []
    for requirement in requirements:
        if requirement["origin"] == "allocated" and not requirement["parents"]:
            findings.append(
                {
                    "code": "allocated-requirement-without-parent",
                    "requirement": requirement["id"],
                    "detail": "requirement %s is allocated but names no source "
                    "requirement" % requirement["id"],
                }
            )
        if requirement["origin"] == "derived" and not requirement["justification"]:
            findings.append(
                {
                    "code": "derived-requirement-without-justification",
                    "requirement": requirement["id"],
                    "detail": "requirement %s is derived, so nothing above it "
                    "justifies it and no justification is recorded"
                    % requirement["id"],
                }
            )
        if requirement["origin"] == "heritage" and not requirement["heritage_item"]:
            findings.append(
                {
                    "code": "heritage-requirement-without-source-item",
                    "requirement": requirement["id"],
                    "detail": "requirement %s is inherited but names no heritage "
                    "configuration" % requirement["id"],
                }
            )

    for dangling in dangling_parents(sources, requirements):
        findings.append(
            {
                "code": "parent-not-in-source-set",
                "requirement": dangling["requirement"],
                "parent": dangling["parent"],
                "detail": "requirement %s names parent %s, which the source set "
                "does not hold" % (dangling["requirement"], dangling["parent"]),
            }
        )

    for source_id in uncovered_sources(sources, requirements):
        findings.append(
            {
                "code": "source-requirement-uncovered",
                "source": source_id,
                "detail": "mandatory source requirement %s reaches no device "
                "requirement" % source_id,
            }
        )

    for area in unpopulated_areas(requirements, declared_areas):
        findings.append(
            {
                "code": "content-area-unpopulated",
                "area": area,
                "detail": "the %s area is declared for this device and holds no "
                "requirement" % area,
            }
        )

    coverage = source_coverage(sources, requirements)
    if not meets_coverage_target(coverage, target):
        findings.append(
            {
                "code": "coverage-target-missed",
                "achieved": coverage,
                "target": target,
                "detail": "source coverage reaches %.1f %% against a %.1f %% target"
                % (100.0 * coverage, 100.0 * target),
            }
        )

    open_fraction = open_item_fraction(requirements)
    if not within_open_item_budget(open_fraction, budget):
        findings.append(
            {
                "code": "open-item-budget-exceeded",
                "fraction": open_fraction,
                "budget": budget,
                "detail": "%.1f %% of the set still carries an open marker against "
                "a %.1f %% budget" % (100.0 * open_fraction, 100.0 * budget),
            }
        )

    return {
        "requirement_count": len(requirements),
        "mandatory_source_count": len(mandatory_sources(sources)),
        "source_coverage": coverage,
        "coverage_target": target,
        "open_item_fraction": open_fraction,
        "open_item_budget": budget,
        "uncovered_sources": uncovered_sources(sources, requirements),
        "orphan_requirements": sorted(
            req["id"]
            for req in requirements
            if req["origin"] == "allocated" and not req["parents"]
        ),
        "unpopulated_areas": unpopulated_areas(requirements, declared_areas),
        "findings": findings,
        "baseline_ready": not findings,
    }

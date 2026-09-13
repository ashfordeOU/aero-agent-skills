#!/usr/bin/env python3
"""Antenna design-baseline definition (ECSS-E-ST-20C clause 7.2.2.1).

Paraphrased procedure, no verbatim standard text. The clause asks that the
antenna family, its constituent elements, the technology chosen for each
element and the performance-parameter set are fixed early in the design
cycle, so that later work refines a frozen baseline instead of re-opening
it. This module turns that into a deterministic, offline check.

Public entry points
-------------------
categorize_antenna            map a declared build into its antenna family
milestone_index               order a review milestone on the design cycle
validate_element_set          mandatory element roles present for the family
validate_technology_selection technology admissible + mature enough
check_performance_parameters  fixed parameter set complete and in bounds
check_baseline_freeze         nothing still open at or after the freeze
assess_design_baseline        whole-baseline roll-up with a finding list
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

# Antenna family -> element roles that must exist before the freeze.
ANTENNA_FAMILIES = {
    "reflector": ("reflector-surface", "feed-chain", "support-structure"),
    "lens": ("lens-body", "feed-chain", "support-structure"),
    "array": ("radiating-element", "beam-forming-network", "support-structure"),
    "horn": ("horn-aperture", "guided-wave-interface"),
    "wire": ("radiating-element", "ground-plane"),
}

# Declared build -> canonical family.
FAMILY_SYNONYMS = {
    "reflector": "reflector",
    "parabolic-reflector": "reflector",
    "dual-reflector": "reflector",
    "deployable-mesh-reflector": "reflector",
    "lens": "lens",
    "dielectric-lens": "lens",
    "array": "array",
    "phased-array": "array",
    "direct-radiating-array": "array",
    "horn": "horn",
    "corrugated-horn": "horn",
    "wire": "wire",
    "helix": "wire",
    "monopole": "wire",
}

# Element role -> admissible implementation technologies.
ELEMENT_TECHNOLOGIES = {
    "reflector-surface": (
        "carbon-fibre-shell",
        "metallic-shell",
        "deployable-mesh",
    ),
    "lens-body": ("dielectric-lens", "constrained-lens"),
    "feed-chain": ("corrugated-horn", "smooth-wall-horn", "patch-feed"),
    "radiating-element": (
        "microstrip-patch",
        "printed-dipole",
        "cup-dipole",
        "slot-radiator",
    ),
    "beam-forming-network": (
        "stripline-network",
        "waveguide-network",
        "digital-beam-former",
    ),
    "horn-aperture": ("corrugated-horn", "smooth-wall-horn"),
    "guided-wave-interface": ("rectangular-waveguide", "coaxial-line"),
    "support-structure": (
        "carbon-fibre-strut",
        "aluminium-bracket",
        "deployable-boom",
    ),
    "ground-plane": ("metallic-ground-plane", "structure-ground-plane"),
}

# Performance parameters fixed at the baseline; None = categorical.
PERFORMANCE_PARAMETERS = {
    "frequency-band-ghz": (0.1, 300.0),
    "peak-gain-dbi": (-10.0, 70.0),
    "half-power-beamwidth-deg": (0.01, 360.0),
    "axial-ratio-db": (0.0, 20.0),
    "input-return-loss-db": (5.0, 60.0),
    "polarization": None,
}

POLARIZATIONS = (
    "linear-horizontal",
    "linear-vertical",
    "right-hand-circular",
    "left-hand-circular",
    "dual-linear",
    "dual-circular",
)

# Design-cycle reviews in order.
MILESTONES = ("srr", "pdr", "cdr", "qr", "ar")
BASELINE_FREEZE_MILESTONE = "pdr"
MIN_TECHNOLOGY_READINESS_AT_FREEZE = 5


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % label)
    return number


def _within(value, low, high):
    """Inclusive range test that absorbs floating-point representation error."""
    if value < low and not math.isclose(value, low, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return False
    if value > high and not math.isclose(value, high, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return False
    return True


def categorize_antenna(declared_build):
    """Map a declared antenna build onto its canonical family."""
    key = _require_text(declared_build, "declared antenna build")
    if key not in FAMILY_SYNONYMS:
        raise ValueError("unknown antenna build: %r" % (declared_build,))
    return FAMILY_SYNONYMS[key]


def milestone_index(milestone):
    """Position of a review on the design cycle; higher is later."""
    key = _require_text(milestone, "milestone")
    if key not in MILESTONES:
        raise ValueError("unknown design-cycle milestone: %r" % (milestone,))
    return MILESTONES.index(key)


def validate_element_set(family, elements):
    """Check the declared elements against the family's mandatory roles."""
    key = _require_text(family, "antenna family")
    if key not in ANTENNA_FAMILIES:
        raise ValueError("unknown antenna family: %r" % (family,))
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple")
    if len(elements) == 0:
        raise ValueError("elements must not be empty")
    declared = []
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError("each element must be a mapping")
        role = _require_text(element.get("role"), "element role")
        if role not in ELEMENT_TECHNOLOGIES:
            raise ValueError("unknown element role: %r" % (element.get("role"),))
        if role in declared:
            raise ValueError("element role declared twice: %r" % role)
        declared.append(role)
    findings = []
    for role in ANTENNA_FAMILIES[key]:
        if role not in declared:
            findings.append(
                "%s baseline is missing its mandatory '%s' element" % (key, role)
            )
    for role in declared:
        if role not in ANTENNA_FAMILIES[key]:
            findings.append(
                "element '%s' does not belong to a %s antenna baseline" % (role, key)
            )
    return findings


def validate_technology_selection(role, technology, readiness, milestone):
    """Check one element's technology choice and its maturity at a review."""
    role_key = _require_text(role, "element role")
    if role_key not in ELEMENT_TECHNOLOGIES:
        raise ValueError("unknown element role: %r" % (role,))
    technology_key = _require_text(technology, "technology")
    if isinstance(readiness, bool) or not isinstance(readiness, int):
        raise ValueError("technology readiness must be an integer 1-9")
    if readiness < 1 or readiness > 9:
        raise ValueError("technology readiness must be within 1-9")
    index = milestone_index(milestone)
    findings = []
    if technology_key not in ELEMENT_TECHNOLOGIES[role_key]:
        findings.append(
            "technology '%s' is not an admissible implementation of '%s'"
            % (technology_key, role_key)
        )
    if index >= milestone_index(BASELINE_FREEZE_MILESTONE):
        if readiness < MIN_TECHNOLOGY_READINESS_AT_FREEZE:
            findings.append(
                "technology '%s' for '%s' is below the maturity expected at %s"
                % (technology_key, role_key, BASELINE_FREEZE_MILESTONE)
            )
    return findings


def check_performance_parameters(parameters):
    """Check the fixed performance-parameter set for completeness and bounds."""
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping")
    findings = []
    for name, bounds in PERFORMANCE_PARAMETERS.items():
        if name not in parameters:
            findings.append("performance-parameter '%s' is not fixed" % name)
            continue
        value = parameters[name]
        if bounds is None:
            polarization = _require_text(value, "polarization")
            if polarization not in POLARIZATIONS:
                findings.append(
                    "polarization '%s' is not a recognized scheme" % polarization
                )
            continue
        number = _require_number(value, name)
        low, high = bounds
        if not _within(number, low, high):
            findings.append(
                "performance-parameter '%s' (%g) sits outside its declared bounds"
                % (name, number)
            )
    for name in parameters:
        if name not in PERFORMANCE_PARAMETERS:
            findings.append(
                "'%s' is not part of the fixed performance-parameter set" % name
            )
    return findings


def check_baseline_freeze(open_items, milestone):
    """Flag anything still open at or after the baseline-freeze review."""
    if not isinstance(open_items, (list, tuple)):
        raise ValueError("open_items must be a list or tuple")
    index = milestone_index(milestone)
    freeze = milestone_index(BASELINE_FREEZE_MILESTONE)
    findings = []
    if index < freeze:
        return findings
    for item in open_items:
        label = _require_text(item, "open item")
        findings.append(
            "'%s' is still open at %s, after the baseline freeze" % (label, milestone)
        )
    return findings


def assess_design_baseline(definition):
    """Roll the whole antenna design-baseline up into one finding list."""
    if not isinstance(definition, dict):
        raise ValueError("definition must be a mapping")
    ident = _require_text(definition.get("id"), "antenna id")
    family = categorize_antenna(definition.get("build"))
    milestone = _require_text(definition.get("milestone"), "milestone")
    milestone_index(milestone)
    elements = definition.get("elements")
    findings = list(validate_element_set(family, elements))
    for element in elements:
        findings.extend(
            validate_technology_selection(
                element.get("role"),
                element.get("technology"),
                element.get("readiness"),
                milestone,
            )
        )
    findings.extend(check_performance_parameters(definition.get("parameters", {})))
    findings.extend(
        check_baseline_freeze(definition.get("open_items", []), milestone)
    )
    frozen = milestone_index(milestone) >= milestone_index(BASELINE_FREEZE_MILESTONE)
    return {
        "id": ident,
        "family": family,
        "milestone": milestone,
        "frozen_expected": frozen,
        "element_count": len(elements),
        "findings": findings,
        "compliant": not findings,
    }

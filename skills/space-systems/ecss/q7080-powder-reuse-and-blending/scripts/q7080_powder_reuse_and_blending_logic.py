#!/usr/bin/env python3
"""Reuse and blending control for metallic powder bed fusion feedstock.

Anchor: the materials clauses of ECSS-Q-ST-70-80C on powder reuse and
blending. The steps below are a paraphrase into implementable form; no
standard text is reproduced.

Powder is not consumed evenly by a build. What comes back off the plate
has seen the process atmosphere, has lost part of its fine fraction to
the spatter and the filter, and has picked up interstitial oxygen. A
blend therefore has a composition of its own: a mass-weighted oxygen
content, a mass-weighted particle size, a virgin mass fraction, and two
different reuse counts - the mass-weighted one that describes the bulk
and the worst-case one that describes the oldest particle in the drum.
A limit is breached by the worst case, never by the average.

Standard library only, offline, deterministic. Weighted sums are taken
over lots in a fixed identifier order so a rerun reproduces the value.
"""

from __future__ import annotations

import math

POWDER_TESTS = (
    "particle-size-distribution",
    "oxygen-and-nitrogen-chemistry",
    "flowability",
    "apparent-and-tap-density",
    "morphology",
    "moisture",
)

BLEND_ACCEPTED = "blend-accepted"
BLEND_ACCEPTED_AFTER_TEST = "blend-accepted-after-characterisation"
BLEND_REJECTED = "blend-rejected"

DEFAULT_REUSE_LIMITS = {
    "max_reuse_cycles": 10,
    "max_oxygen_ppm": 1800.0,
    "min_virgin_mass_fraction": 0.0,
    "psd_d50_window_um": (25.0, 45.0),
    "max_fines_fraction": 0.10,
    "characterisation_interval_cycles": 5,
    "oxygen_watch_fraction": 0.90,
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


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative whole number, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A mass-weighted property is a sum of quotients, so a blend that sits
    exactly on its limit can land a few units in the last place above
    it. The limit is never relaxed; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_reuse_limits(limits):
    """Check the declared reuse policy is complete and internally sane."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    missing = set(DEFAULT_REUSE_LIMITS) - set(limits)
    if missing:
        raise ValueError(
            "reuse limits are missing entries: %s" % ", ".join(sorted(missing))
        )
    _require_count("max_reuse_cycles", limits["max_reuse_cycles"])
    _require_positive("max_oxygen_ppm", limits["max_oxygen_ppm"])
    _require_fraction("min_virgin_mass_fraction", limits["min_virgin_mass_fraction"])
    _require_fraction("max_fines_fraction", limits["max_fines_fraction"])
    _require_count(
        "characterisation_interval_cycles", limits["characterisation_interval_cycles"]
    )
    _require_fraction("oxygen_watch_fraction", limits["oxygen_watch_fraction"])
    window = limits["psd_d50_window_um"]
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("psd_d50_window_um must be a two-value window")
    low = _require_positive("psd_d50_window_um lower bound", window[0])
    high = _require_positive("psd_d50_window_um upper bound", window[1])
    if low >= high:
        raise ValueError("psd_d50_window_um lower bound is not below the upper bound")
    return limits


def validate_component(component):
    """Normalize one lot offered into a blend."""
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping, got %r" % (component,))
    return {
        "lot_id": _require_text("lot_id", component.get("lot_id")),
        "mass_kg": _require_positive("mass_kg", component.get("mass_kg")),
        "reuse_cycles": _require_count("reuse_cycles", component.get("reuse_cycles")),
        "oxygen_ppm": _require_non_negative("oxygen_ppm", component.get("oxygen_ppm")),
        "psd_d50_um": _require_positive("psd_d50_um", component.get("psd_d50_um")),
        "fines_fraction": _require_fraction(
            "fines_fraction", component.get("fines_fraction")
        ),
        "cycles_since_characterisation": _require_count(
            "cycles_since_characterisation",
            component.get("cycles_since_characterisation"),
        ),
        "exposed_to_atmosphere": _require_bool(
            "exposed_to_atmosphere", component.get("exposed_to_atmosphere", False)
        ),
    }


def blend_composition(components):
    """Mass-weighted composition of a blend built from several lots."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError(
            "components must be a non-empty sequence, got %r" % (components,)
        )
    resolved = [validate_component(c) for c in components]
    identifiers = [c["lot_id"] for c in resolved]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("the same lot identifier was offered twice into one blend")
    resolved.sort(key=lambda c: c["lot_id"])
    total_mass = 0.0
    for component in resolved:
        total_mass += component["mass_kg"]
    weighted = {"oxygen_ppm": 0.0, "psd_d50_um": 0.0, "fines_fraction": 0.0,
                "reuse_cycles": 0.0}
    virgin_mass = 0.0
    for component in resolved:
        share = component["mass_kg"] / total_mass
        for key in weighted:
            weighted[key] += component[key] * share
        if component["reuse_cycles"] == 0:
            virgin_mass += component["mass_kg"]
    return {
        "lot_count": len(resolved),
        "lot_ids": tuple(c["lot_id"] for c in resolved),
        "total_mass_kg": total_mass,
        "virgin_mass_fraction": virgin_mass / total_mass,
        "mass_weighted_oxygen_ppm": weighted["oxygen_ppm"],
        "mass_weighted_d50_um": weighted["psd_d50_um"],
        "mass_weighted_fines_fraction": weighted["fines_fraction"],
        "mass_weighted_reuse_cycles": weighted["reuse_cycles"],
        "worst_case_reuse_cycles": max(c["reuse_cycles"] for c in resolved),
        "cycles_since_characterisation": max(
            c["cycles_since_characterisation"] for c in resolved
        ),
        "any_atmosphere_exposure": any(c["exposed_to_atmosphere"] for c in resolved),
    }


def reuse_cycles_after_next_build(composition):
    """Worst-case reuse count the blend would carry out of the next build."""
    if not isinstance(composition, dict) or "worst_case_reuse_cycles" not in composition:
        raise ValueError("composition must come from blend_composition")
    return composition["worst_case_reuse_cycles"] + 1


def grade_blend(composition, limits=DEFAULT_REUSE_LIMITS):
    """Compare every blend property against its declared limit."""
    validate_reuse_limits(limits)
    if not isinstance(composition, dict) or "total_mass_kg" not in composition:
        raise ValueError("composition must come from blend_composition")
    low, high = limits["psd_d50_window_um"]
    checks = [
        (
            "worst-case-reuse-cycles",
            float(composition["worst_case_reuse_cycles"]),
            float(limits["max_reuse_cycles"]),
            _at_most(
                float(composition["worst_case_reuse_cycles"]),
                float(limits["max_reuse_cycles"]),
            ),
        ),
        (
            "mass-weighted-oxygen-ppm",
            composition["mass_weighted_oxygen_ppm"],
            limits["max_oxygen_ppm"],
            _at_most(composition["mass_weighted_oxygen_ppm"], limits["max_oxygen_ppm"]),
        ),
        (
            "virgin-mass-fraction",
            composition["virgin_mass_fraction"],
            limits["min_virgin_mass_fraction"],
            _at_least(
                composition["virgin_mass_fraction"],
                limits["min_virgin_mass_fraction"],
            ),
        ),
        (
            "mass-weighted-fines-fraction",
            composition["mass_weighted_fines_fraction"],
            limits["max_fines_fraction"],
            _at_most(
                composition["mass_weighted_fines_fraction"],
                limits["max_fines_fraction"],
            ),
        ),
        (
            "mass-weighted-d50-um",
            composition["mass_weighted_d50_um"],
            (low, high),
            _at_least(composition["mass_weighted_d50_um"], low)
            and _at_most(composition["mass_weighted_d50_um"], high),
        ),
    ]
    graded = []
    for name, value, limit, within in checks:
        graded.append(
            {
                "property": name,
                "value": value,
                "limit": limit,
                "verdict": "within-limit" if within else "outside-limit",
            }
        )
    return tuple(graded)


def exceedances(graded):
    """Names of the graded properties that fell outside their limit."""
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence, got %r" % (graded,))
    return tuple(
        item["property"] for item in graded if item["verdict"] == "outside-limit"
    )


def required_tests(composition, limits=DEFAULT_REUSE_LIMITS):
    """Characterisation the blend owes before it may be loaded."""
    validate_reuse_limits(limits)
    if not isinstance(composition, dict) or "total_mass_kg" not in composition:
        raise ValueError("composition must come from blend_composition")
    needed = set()
    if composition["lot_count"] > 1:
        needed.update(
            {
                "particle-size-distribution",
                "oxygen-and-nitrogen-chemistry",
                "flowability",
            }
        )
    if composition["cycles_since_characterisation"] >= limits[
        "characterisation_interval_cycles"
    ]:
        needed.update(POWDER_TESTS)
    watch = limits["max_oxygen_ppm"] * limits["oxygen_watch_fraction"]
    if _at_least(composition["mass_weighted_oxygen_ppm"], watch):
        needed.add("oxygen-and-nitrogen-chemistry")
    if _at_least(
        composition["mass_weighted_fines_fraction"],
        limits["max_fines_fraction"] * limits["oxygen_watch_fraction"],
    ):
        needed.update({"particle-size-distribution", "flowability"})
    if composition["any_atmosphere_exposure"]:
        needed.add("moisture")
    if composition["worst_case_reuse_cycles"] > 0:
        needed.add("morphology")
    return tuple(sorted(needed))


def manage_powder_reuse(case, limits=DEFAULT_REUSE_LIMITS):
    """Full reuse and blending decision with tests and a disposition."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_reuse_limits(limits)
    composition = blend_composition(case.get("components"))
    graded = grade_blend(composition, limits)
    breached = exceedances(graded)
    tests = required_tests(composition, limits)
    completed = case.get("completed_tests", ())
    if not isinstance(completed, (list, tuple, set, frozenset)):
        raise ValueError("completed_tests must be a sequence, got %r" % (completed,))
    done = set()
    for item in completed:
        name = _require_text("completed test", item)
        if name not in POWDER_TESTS:
            raise ValueError("unknown powder test %r" % name)
        done.add(name)
    outstanding = tuple(sorted(set(tests) - done))
    findings = []
    if breached:
        findings.append(
            "blend properties outside their limit: %s" % ", ".join(breached)
        )
    if outstanding:
        findings.append(
            "characterisation outstanding before loading: %s" % ", ".join(outstanding)
        )
    projected = reuse_cycles_after_next_build(composition)
    if projected > limits["max_reuse_cycles"]:
        findings.append(
            "the blend reaches reuse cycle %d after the next build, past the "
            "limit of %d, so this is its last build"
            % (projected, limits["max_reuse_cycles"])
        )
    if breached:
        disposition = BLEND_REJECTED
    elif outstanding:
        disposition = BLEND_ACCEPTED_AFTER_TEST
    else:
        disposition = BLEND_ACCEPTED
    return {
        "composition": composition,
        "graded": graded,
        "exceedances": breached,
        "required_tests": tests,
        "outstanding_tests": outstanding,
        "reuse_cycles_after_next_build": projected,
        "disposition": disposition,
        "findings": findings,
    }

#!/usr/bin/env python3
"""Design-for-testability of an MMIC die.

Anchor: ECSS-Q-ST-60-12C clause 7.2.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A monolithic microwave integrated circuit is a sealed piece of
semiconductor: once the die is mounted, wire-bonded and lidded, almost
every internal node is gone. Whatever the acceptance flow will have to
measure has to be reachable through access designed into the layout
before tape-out, which is what clause 7.2.7 asks the designer to build
in and then demonstrate.

Access kinds the layout can provide
    rf-probe-pad             a ground-signal-ground landing set for
                             on-wafer scattering-parameter probing
    dc-probe-pad             a bias or rail landing pad
    bias-sense-tap           a separate sense route that reads a node
                             without loading the working path
    process-control-monitor  a drop-in structure in the scribe lane
                             carrying the foundry device parameters
    assembled-fixture-only   reachable only once the die sits in a
                             carrier, so useless to a wafer-level screen

Parameter roles
    screening-critical       every delivered die is graded on it, so it
                             has to be measurable before assembly
    characterisation-only    measured on a sample to describe the
                             design, so assembly-level access will do

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCESS_KINDS = (
    "rf-probe-pad",
    "dc-probe-pad",
    "bias-sense-tap",
    "process-control-monitor",
    "assembled-fixture-only",
)

# Everything but the fixture kind can be reached while the die is still
# on the wafer, which is the only place a pre-assembly screen can run.
ON_WAFER_KINDS = frozenset(
    {"rf-probe-pad", "dc-probe-pad", "bias-sense-tap", "process-control-monitor"}
)

PARAMETER_ROLES = ("screening-critical", "characterisation-only")

ON_WAFER = "on-wafer"
ASSEMBLY_LEVEL = "assembly-level"
UNOBSERVABLE = "unobservable"
OBSERVABILITY_LEVELS = (ON_WAFER, ASSEMBLY_LEVEL, UNOBSERVABLE)

ADEQUATE = "testability-adequate"
CONDITIONAL = "testability-conditional"
INADEQUATE = "testability-inadequate"

DEFAULT_PAD_AREA_BUDGET_FRACTION = 0.08

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


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An area fraction is a ratio of two sums of products, so a layout
    that sits exactly on its budget can land a few units in the last
    place above it. The budget is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_access_point(point):
    """Check one declared access feature and return it normalised."""
    if not isinstance(point, dict):
        raise ValueError("access point must be a mapping, got %r" % (point,))
    identifier = point.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("access point needs a non-empty id, got %r" % (identifier,))
    kind = _require_choice("access kind", point.get("kind"), ACCESS_KINDS)
    normalised = {"id": identifier, "kind": kind}
    if kind in ("rf-probe-pad", "dc-probe-pad"):
        normalised["pitch_um"] = _require_positive("pitch_um", point.get("pitch_um"))
        normalised["width_um"] = _require_positive("width_um", point.get("width_um"))
        normalised["height_um"] = _require_positive("height_um", point.get("height_um"))
        normalised["count"] = _require_positive_int("count", point.get("count", 1))
    return normalised


def minimum_landing_side_um(probe_card):
    """Smallest pad side a probe tip can be landed on with confidence."""
    if not isinstance(probe_card, dict):
        raise ValueError("probe_card must be a mapping, got %r" % (probe_card,))
    tip = _require_positive("tip_diameter_um", probe_card.get("tip_diameter_um"))
    alignment = _require_non_negative(
        "alignment_tolerance_um", probe_card.get("alignment_tolerance_um")
    )
    return tip + 2.0 * alignment


def probe_landing_check(pad, probe_card):
    """Whether one probe pad can actually be landed on by this probe card."""
    pad = validate_access_point(pad)
    if pad["kind"] not in ("rf-probe-pad", "dc-probe-pad"):
        raise ValueError(
            "probe landing only applies to a probe pad, got kind %r" % pad["kind"]
        )
    card_pitch = _require_positive("card pitch_um", probe_card.get("pitch_um"))
    pitch_tolerance = _require_non_negative(
        "pitch_tolerance_um", probe_card.get("pitch_tolerance_um", 0.0)
    )
    minimum_side = minimum_landing_side_um(probe_card)
    findings = []
    pitch_error = abs(pad["pitch_um"] - card_pitch)
    pitch_ok = pitch_error <= pitch_tolerance or math.isclose(
        pitch_error, pitch_tolerance, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if not pitch_ok:
        findings.append(
            "pad %s is on a %.1f um pitch against a %.1f um probe card; the "
            "%.1f um error is outside the %.1f um tolerance"
            % (pad["id"], pad["pitch_um"], card_pitch, pitch_error, pitch_tolerance)
        )
    short_side = min(pad["width_um"], pad["height_um"])
    landing_ok = short_side >= minimum_side or math.isclose(
        short_side, minimum_side, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if not landing_ok:
        findings.append(
            "pad %s has a %.1f um short side against a %.1f um minimum landing "
            "area; the tip will overhang" % (pad["id"], short_side, minimum_side)
        )
    return {
        "id": pad["id"],
        "compatible": bool(pitch_ok and landing_ok),
        "pitch_error_um": pitch_error,
        "minimum_landing_side_um": minimum_side,
        "findings": findings,
    }


def validate_parameter(parameter):
    """Check one parameter the acceptance flow has to measure."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping, got %r" % (parameter,))
    name = parameter.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("parameter needs a non-empty name, got %r" % (name,))
    role = _require_choice("parameter role", parameter.get("role"), PARAMETER_ROLES)
    requires = _require_choice("parameter requires", parameter.get("requires"), ACCESS_KINDS)
    fallback = parameter.get("assembly_fallback", False)
    if not isinstance(fallback, bool):
        raise ValueError(
            "parameter assembly_fallback must be a boolean, got %r" % (fallback,)
        )
    return {
        "name": name,
        "role": role,
        "requires": requires,
        "assembly_fallback": fallback,
    }


def resolve_observability(parameter, available_kinds):
    """Where in the flow this parameter can actually be measured."""
    parameter = validate_parameter(parameter)
    if not isinstance(available_kinds, (set, frozenset, tuple, list)):
        raise ValueError("available_kinds must be a collection, got %r" % (available_kinds,))
    available = set(available_kinds)
    for kind in available:
        _require_choice("available access kind", kind, ACCESS_KINDS)
    required = parameter["requires"]
    if required in available:
        return ON_WAFER if required in ON_WAFER_KINDS else ASSEMBLY_LEVEL
    if parameter["assembly_fallback"] and "assembled-fixture-only" in available:
        return ASSEMBLY_LEVEL
    return UNOBSERVABLE


def coverage_report(parameters, access_points):
    """Group every parameter by where it can be measured, and count.

    Parameters are categorized rather than scored: a screening-critical
    parameter that only comes back at assembly level is a gap even
    though it is measurable somewhere, because a die-level screen cannot
    reach it.
    """
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("parameters must be a non-empty sequence")
    if not isinstance(access_points, (list, tuple)):
        raise ValueError("access_points must be a sequence")
    available = {validate_access_point(p)["kind"] for p in access_points}
    grouped = {level: [] for level in OBSERVABILITY_LEVELS}
    screening_gaps = []
    for raw in parameters:
        parameter = validate_parameter(raw)
        level = resolve_observability(parameter, available)
        grouped[level].append(parameter["name"])
        if parameter["role"] == "screening-critical" and level != ON_WAFER:
            screening_gaps.append({"name": parameter["name"], "observability": level})
    total = len(parameters)
    return {
        "total": total,
        "grouped": grouped,
        "on_wafer_fraction": len(grouped[ON_WAFER]) / float(total),
        "screening_gaps": screening_gaps,
        "available_kinds": sorted(available),
    }


def touchdown_budget(test_steps, retest_allowance, rated_touchdowns):
    """Probe touchdowns the flow will spend against what a pad is rated for."""
    steps = _require_positive_int("test_steps", test_steps)
    allowance = _require_non_negative("retest_allowance", retest_allowance)
    rated = _require_positive_int("rated_touchdowns", rated_touchdowns)
    planned = steps * (1.0 + allowance)
    within = _at_most(planned, float(rated))
    return {
        "planned_touchdowns": planned,
        "rated_touchdowns": rated,
        "headroom": rated - planned,
        "within_budget": within,
    }


def pad_area_overhead(access_points, die_area_um2):
    """Die area the probe pads consume, as an absolute and a fraction."""
    if not isinstance(access_points, (list, tuple)):
        raise ValueError("access_points must be a sequence")
    die_area = _require_positive("die_area_um2", die_area_um2)
    total = 0.0
    for raw in access_points:
        point = validate_access_point(raw)
        if point["kind"] not in ("rf-probe-pad", "dc-probe-pad"):
            continue
        total += point["count"] * point["width_um"] * point["height_um"]
    if total > die_area:
        raise ValueError(
            "probe pads claim %.1f um2 on a %.1f um2 die; the layout is "
            "inconsistent" % (total, die_area)
        )
    return {"pad_area_um2": total, "area_fraction": total / die_area}


def assess_testability(case):
    """Full clause 7.2.7 testability assessment with a verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    parameters = case.get("parameters")
    access_points = case.get("access_points")
    coverage = coverage_report(parameters, access_points)

    findings = []
    probe_results = []
    probe_card_undeclared = False
    probe_card = case.get("probe_card")
    if probe_card is not None:
        for raw in access_points:
            point = validate_access_point(raw)
            if point["kind"] not in ("rf-probe-pad", "dc-probe-pad"):
                continue
            result = probe_landing_check(raw, probe_card)
            probe_results.append(result)
            findings.extend(result["findings"])
    elif any(
        validate_access_point(p)["kind"] in ("rf-probe-pad", "dc-probe-pad")
        for p in access_points
    ):
        probe_card_undeclared = True
        findings.append(
            "probe pads are declared but no probe card is; their landing "
            "compatibility has not been demonstrated"
        )

    area = pad_area_overhead(access_points, case.get("die_area_um2"))
    budget_fraction = _require_positive(
        "pad_area_budget_fraction",
        case.get("pad_area_budget_fraction", DEFAULT_PAD_AREA_BUDGET_FRACTION),
    )
    area_within_budget = _at_most(area["area_fraction"], budget_fraction)
    if not area_within_budget:
        findings.append(
            "probe pads take %.1f%% of the die against a %.1f%% budget"
            % (100.0 * area["area_fraction"], 100.0 * budget_fraction)
        )

    touchdowns = touchdown_budget(
        case.get("test_steps", 1),
        case.get("retest_allowance", 0.0),
        case.get("rated_touchdowns", 1),
    )
    if not touchdowns["within_budget"]:
        findings.append(
            "the flow spends %.1f touchdowns against a pad rated for %d"
            % (touchdowns["planned_touchdowns"], touchdowns["rated_touchdowns"])
        )

    unobservable_critical = [
        gap for gap in coverage["screening_gaps"] if gap["observability"] == UNOBSERVABLE
    ]
    assembly_only_critical = [
        gap for gap in coverage["screening_gaps"] if gap["observability"] == ASSEMBLY_LEVEL
    ]
    for gap in unobservable_critical:
        findings.append(
            "screening-critical parameter %s has no measurement access at all"
            % gap["name"]
        )
    for gap in assembly_only_critical:
        findings.append(
            "screening-critical parameter %s comes back only after assembly, so "
            "no die-level screen can act on it" % gap["name"]
        )
    if coverage["grouped"][UNOBSERVABLE]:
        findings.append(
            "%d parameter(s) are unobservable through the declared access"
            % len(coverage["grouped"][UNOBSERVABLE])
        )

    probes_compatible = all(r["compatible"] for r in probe_results)
    if unobservable_critical or not probes_compatible:
        verdict = INADEQUATE
    elif (
        assembly_only_critical
        or coverage["grouped"][UNOBSERVABLE]
        or not area_within_budget
        or not touchdowns["within_budget"]
        or probe_card_undeclared
    ):
        verdict = CONDITIONAL
    else:
        verdict = ADEQUATE

    return {
        "verdict": verdict,
        "adequate": verdict == ADEQUATE,
        "coverage": coverage,
        "on_wafer_fraction": coverage["on_wafer_fraction"],
        "screening_gaps": coverage["screening_gaps"],
        "probe_results": probe_results,
        "probes_compatible": probes_compatible,
        "probe_card_undeclared": probe_card_undeclared,
        "pad_area_um2": area["pad_area_um2"],
        "pad_area_fraction": area["area_fraction"],
        "pad_area_within_budget": area_within_budget,
        "touchdowns": touchdowns,
        "findings": findings,
    }

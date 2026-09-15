#!/usr/bin/env python3
"""Development, reuse and maintenance routing for a class 1 programmable logic device.

Anchor: ECSS-Q-ST-60C clause 4.6.4 (development, reuse and maintenance rules
for programmable logic devices used in class 1 equipment). Paraphrased into an
implementable procedure; no standard text is reproduced.

A programmable logic device is two things at once. It is a component, bought
against a detail specification like any other, and it is a design the project
authored and loaded into that component. The component half is covered by the
general procurement rules. The design half is not, and clause 4.6.4 is about
the design half: how it is developed, what a reuse claim has to carry, and what
keeps it correct once the unit has shipped.

Procedure implemented here
--------------------------
1. Validate the case: the device technology, the declared design origin, the
   design-assurance evidence, and for a reuse claim both the baseline and the
   candidate build records.
2. Compare candidate against baseline axis by axis and group the differences
   into device, logic and implementation changes.
3. Score the design-assurance evidence against what the declared origin
   demands, and compare the achieved functional coverage with the class 1
   floor.
4. Route the design: a full development flow, a delta verification flow, a
   reviewed reuse flow, or nothing at all while the evidence is short.
5. Attach the programming and in-service maintenance duties that follow from
   the device technology rather than from the route.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "PLD_TECHNOLOGIES",
    "DESIGN_ORIGINS",
    "DEVICE_AXES",
    "LOGIC_AXES",
    "IMPLEMENTATION_AXES",
    "DESIGN_AXES",
    "DESIGN_ASSURANCE_ITEMS",
    "REQUIRED_EVIDENCE_BY_ORIGIN",
    "MAINTENANCE_DUTIES_BY_TECHNOLOGY",
    "FULL_DEVELOPMENT",
    "DELTA_VERIFICATION",
    "REVIEWED_REUSE",
    "EVIDENCE_INCOMPLETE",
    "ACTIVITY_SETS",
    "DEFAULT_PLD_POLICY",
    "validate_pld_policy",
    "validate_build_record",
    "changed_design_axes",
    "group_changed_axes",
    "design_delta_index",
    "design_assurance_gaps",
    "coverage_shortfall_pct",
    "meets_coverage",
    "maintenance_duties",
    "activity_set_for_route",
    "route_pld_design",
    "assess_pld_case",
]

# How the configuration is held in the device. This decides the maintenance
# duties, and it is independent of how the design was developed.
PLD_TECHNOLOGIES = (
    "antifuse-one-time",
    "flash-reprogrammable",
    "volatile-configuration",
)

DESIGN_ORIGINS = ("new-design", "modified-reuse", "unchanged-reuse")

# A device axis moves the silicon the design runs on; a logic axis moves what
# the design does; an implementation axis moves how the same logic was mapped
# into the same device. Grouping them is what turns a difference list into a
# route.
DEVICE_AXES = ("device_part_number", "device_technology", "device_speed_grade")
LOGIC_AXES = ("design_source_revision", "functional_scope", "clock_domain_set")
IMPLEMENTATION_AXES = (
    "synthesis_tool_version",
    "place_and_route_constraints",
    "pin_assignment",
)
DESIGN_AXES = DEVICE_AXES + LOGIC_AXES + IMPLEMENTATION_AXES

DESIGN_ASSURANCE_ITEMS = (
    "requirements_specification",
    "functional_simulation_record",
    "static_timing_analysis",
    "place_and_route_report",
    "post_programming_verification",
)

# An unchanged reuse leans on the baseline records for everything the baseline
# already demonstrated; it still has to show the part in hand was programmed
# and verified.
REQUIRED_EVIDENCE_BY_ORIGIN = {
    "new-design": DESIGN_ASSURANCE_ITEMS,
    "modified-reuse": DESIGN_ASSURANCE_ITEMS,
    "unchanged-reuse": (
        "requirements_specification",
        "post_programming_verification",
    ),
}

MAINTENANCE_DUTIES_BY_TECHNOLOGY = {
    "antifuse-one-time": (
        "approved-programming-facility",
        "programming-yield-record",
        "post-programming-functional-verification",
        "fuse-map-archive-under-configuration-control",
    ),
    "flash-reprogrammable": (
        "configuration-memory-integrity-check",
        "bitstream-archive-under-configuration-control",
        "reprogramming-procedure-approval",
        "configuration-retention-assessment-over-life",
    ),
    "volatile-configuration": (
        "configuration-scrubbing-provision",
        "upset-rate-assessment",
        "power-up-configuration-integrity-check",
        "bitstream-archive-under-configuration-control",
    ),
}

FULL_DEVELOPMENT = "pld-full-development-flow"
DELTA_VERIFICATION = "pld-delta-verification-flow"
REVIEWED_REUSE = "pld-reviewed-reuse-flow"
EVIDENCE_INCOMPLETE = "pld-design-assurance-incomplete"

ACTIVITY_SETS = {
    FULL_DEVELOPMENT: (
        "requirements-capture-review",
        "functional-simulation-campaign",
        "static-timing-analysis",
        "place-and-route-review",
        "post-programming-verification",
    ),
    DELTA_VERIFICATION: (
        "change-impact-review",
        "regression-simulation",
        "static-timing-analysis",
        "post-programming-verification",
    ),
    REVIEWED_REUSE: (
        "baseline-evidence-review",
        "post-programming-verification",
    ),
    EVIDENCE_INCOMPLETE: (),
}

DEFAULT_PLD_POLICY = {
    # Functional coverage the class 1 design campaign has to reach.
    "min_functional_coverage_pct": 95.0,
    # How long a baseline verification record stands before a delta is owed.
    "max_baseline_age_months": 60,
    # Whether a mapping-only change still owes a delta verification.
    "implementation_change_forces_delta": True,
    # Whether the design may be reloaded once the unit has been delivered.
    "reprogramming_after_delivery_allowed": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage figure is a ratio of counts turned into a percentage, so a
    campaign that is exactly on the floor can land a few units in the last
    place below it. The floor itself is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_pld_policy(policy=None):
    """Return a complete routing policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_PLD_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("pld policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_PLD_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_PLD_POLICY:
            raise ValueError("unknown pld policy key %r" % (key,))
        merged[key] = value
    coverage = merged["min_functional_coverage_pct"]
    if not _is_finite_number(coverage):
        raise ValueError("min_functional_coverage_pct must be a finite number")
    if not 0.0 < coverage <= 100.0:
        raise ValueError(
            "min_functional_coverage_pct must lie in (0, 100], got %r" % (coverage,)
        )
    age = merged["max_baseline_age_months"]
    if not _is_int(age) or age <= 0:
        raise ValueError("max_baseline_age_months must be a positive integer")
    for key in (
        "implementation_change_forces_delta",
        "reprogramming_after_delivery_allowed",
    ):
        if not isinstance(merged[key], bool):
            raise ValueError("%s must be a boolean" % key)
    return merged


def validate_build_record(name, record):
    """Check a build record names every design axis with a usable value."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, record))
    missing = [axis for axis in DESIGN_AXES if axis not in record]
    if missing:
        raise ValueError(
            "%s is missing design axes: %s" % (name, ", ".join(sorted(missing)))
        )
    for axis in DESIGN_AXES:
        value = record[axis]
        if value is None:
            raise ValueError("%s axis %s is unset; it cannot be compared" % (name, axis))
        if isinstance(value, str) and not value.strip():
            raise ValueError("%s axis %s is blank; it cannot be compared" % (name, axis))
    _require_choice(
        "%s device_technology" % name, record["device_technology"], PLD_TECHNOLOGIES
    )
    return record


def changed_design_axes(baseline, candidate):
    """Design axes on which the candidate build differs from the baseline."""
    validate_build_record("baseline", baseline)
    validate_build_record("candidate", candidate)
    return tuple(
        axis for axis in DESIGN_AXES if baseline[axis] != candidate[axis]
    )


def group_changed_axes(changed):
    """Sort moved axes into device, logic and implementation groups."""
    if isinstance(changed, str) or not hasattr(changed, "__iter__"):
        raise ValueError("changed must be an iterable of axis names, got %r" % (changed,))
    changed = tuple(changed)
    unknown = [axis for axis in changed if axis not in DESIGN_AXES]
    if unknown:
        raise ValueError("unknown design axes: %s" % ", ".join(sorted(unknown)))
    return {
        "device": [axis for axis in changed if axis in DEVICE_AXES],
        "logic": [axis for axis in changed if axis in LOGIC_AXES],
        "implementation": [axis for axis in changed if axis in IMPLEMENTATION_AXES],
    }


def design_delta_index(changed):
    """Share of the design axis set that moved, as a fraction in [0, 1].

    The argument is materialized before it is counted, so a one-shot iterable
    cannot be consumed by the validation and then counted as empty.
    """
    if not isinstance(changed, str) and hasattr(changed, "__iter__"):
        changed = tuple(changed)
    group_changed_axes(changed)
    return len(changed) / float(len(DESIGN_AXES))


def design_assurance_gaps(origin, evidence_present):
    """Evidence items the declared origin demands and the case does not have."""
    _require_choice("origin", origin, DESIGN_ORIGINS)
    if not isinstance(evidence_present, dict):
        raise ValueError(
            "evidence_present must be a mapping of item to boolean, got %r"
            % (evidence_present,)
        )
    unknown = set(evidence_present) - set(DESIGN_ASSURANCE_ITEMS)
    if unknown:
        raise ValueError(
            "unknown design-assurance items: %s" % ", ".join(sorted(unknown))
        )
    for item, flag in evidence_present.items():
        if not isinstance(flag, bool):
            raise ValueError("evidence_present[%s] must be a boolean" % item)
    required = REQUIRED_EVIDENCE_BY_ORIGIN[origin]
    return tuple(item for item in required if not evidence_present.get(item, False))


def coverage_shortfall_pct(achieved_coverage_pct, required_coverage_pct):
    """How far the achieved functional coverage sits below the floor."""
    for name, value in (
        ("achieved_coverage_pct", achieved_coverage_pct),
        ("required_coverage_pct", required_coverage_pct),
    ):
        if not _is_finite_number(value):
            raise ValueError("%s must be a finite number, got %r" % (name, value))
        if not 0.0 <= value <= 100.0:
            raise ValueError("%s must lie in [0, 100], got %r" % (name, value))
    if _at_least(achieved_coverage_pct, required_coverage_pct):
        return 0.0
    return float(required_coverage_pct) - float(achieved_coverage_pct)


def meets_coverage(achieved_coverage_pct, required_coverage_pct):
    """Whether the campaign reached the class 1 coverage floor."""
    return coverage_shortfall_pct(achieved_coverage_pct, required_coverage_pct) == 0.0


def maintenance_duties(technology, reprogramming_after_delivery=False, policy=None):
    """Programming and in-service duties the device technology carries."""
    _require_choice("technology", technology, PLD_TECHNOLOGIES)
    if not isinstance(reprogramming_after_delivery, bool):
        raise ValueError("reprogramming_after_delivery must be a boolean")
    resolved = validate_pld_policy(policy)
    duties = list(MAINTENANCE_DUTIES_BY_TECHNOLOGY[technology])
    findings = []
    if reprogramming_after_delivery:
        if technology == "antifuse-one-time":
            raise ValueError(
                "an antifuse one-time device cannot be reprogrammed after delivery; "
                "maintenance of that design is by device replacement"
            )
        if resolved["reprogramming_after_delivery_allowed"]:
            duties.append("delivered-reprogramming-control-procedure")
            duties.append("post-reprogramming-functional-verification")
        else:
            findings.append(
                "reprogramming after delivery is declared but the project policy "
                "does not permit it for class 1 equipment"
            )
    return {"duties": duties, "findings": findings}


def activity_set_for_route(route):
    """Activities a route carries once the design is inside it."""
    if route not in ACTIVITY_SETS:
        raise ValueError("unknown route %r" % (route,))
    return ACTIVITY_SETS[route]


def route_pld_design(
    origin,
    changed_groups=None,
    evidence_gaps=(),
    coverage_met=True,
    baseline_age_months=0,
    policy=None,
):
    """Route the design, in precedence order, and say what forced the route."""
    _require_choice("origin", origin, DESIGN_ORIGINS)
    resolved = validate_pld_policy(policy)
    if not isinstance(coverage_met, bool):
        raise ValueError("coverage_met must be a boolean")
    if not _is_int(baseline_age_months) or baseline_age_months < 0:
        raise ValueError("baseline_age_months must be a non-negative integer")
    gaps = tuple(evidence_gaps)
    if gaps:
        return {
            "route": EVIDENCE_INCOMPLETE,
            "driver": "design-assurance evidence missing: %s" % ", ".join(sorted(gaps)),
            "activities": activity_set_for_route(EVIDENCE_INCOMPLETE),
        }
    if origin == "new-design":
        return {
            "route": FULL_DEVELOPMENT,
            "driver": "a new design carries no baseline to lean on",
            "activities": activity_set_for_route(FULL_DEVELOPMENT),
        }
    groups = changed_groups or {"device": [], "logic": [], "implementation": []}
    if not isinstance(groups, dict):
        raise ValueError("changed_groups must be a mapping of group to axis list")
    for key in ("device", "logic", "implementation"):
        if key not in groups:
            raise ValueError("changed_groups is missing the %s group" % key)
    if groups["device"] or groups["logic"]:
        return {
            "route": FULL_DEVELOPMENT,
            "driver": "device or logic axes moved: %s"
            % ", ".join(sorted(groups["device"] + groups["logic"])),
            "activities": activity_set_for_route(FULL_DEVELOPMENT),
        }
    if groups["implementation"] and resolved["implementation_change_forces_delta"]:
        return {
            "route": DELTA_VERIFICATION,
            "driver": "the same logic was remapped: %s"
            % ", ".join(sorted(groups["implementation"])),
            "activities": activity_set_for_route(DELTA_VERIFICATION),
        }
    if not coverage_met:
        return {
            "route": DELTA_VERIFICATION,
            "driver": "the baseline coverage floor was not reached",
            "activities": activity_set_for_route(DELTA_VERIFICATION),
        }
    if baseline_age_months > resolved["max_baseline_age_months"]:
        return {
            "route": DELTA_VERIFICATION,
            "driver": "the baseline verification record is %d months old"
            % baseline_age_months,
            "activities": activity_set_for_route(DELTA_VERIFICATION),
        }
    return {
        "route": REVIEWED_REUSE,
        "driver": "no design axis moved and the baseline evidence stands",
        "activities": activity_set_for_route(REVIEWED_REUSE),
    }


def assess_pld_case(case, policy=None):
    """Full clause 4.6.4 routing with maintenance duties and findings."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    resolved = validate_pld_policy(policy)
    origin = _require_choice("origin", case.get("origin"), DESIGN_ORIGINS)
    technology = _require_choice(
        "technology", case.get("technology"), PLD_TECHNOLOGIES
    )
    evidence_present = case.get("evidence_present", {})
    gaps = design_assurance_gaps(origin, evidence_present)

    findings = []
    if origin == "new-design":
        changed = ()
        groups = {"device": [], "logic": [], "implementation": []}
        delta_index = 0.0
    else:
        baseline = case.get("baseline")
        candidate = case.get("candidate")
        if baseline is None or candidate is None:
            raise ValueError(
                "a %s case needs both a baseline and a candidate build record"
                % origin
            )
        changed = changed_design_axes(baseline, candidate)
        groups = group_changed_axes(changed)
        delta_index = design_delta_index(changed)
        if origin == "unchanged-reuse" and changed:
            findings.append(
                "the case is declared an unchanged reuse but %d design axes moved"
                % len(changed)
            )

    achieved = case.get("achieved_coverage_pct", 100.0)
    shortfall = coverage_shortfall_pct(
        achieved, resolved["min_functional_coverage_pct"]
    )
    coverage_met = shortfall == 0.0
    if not coverage_met:
        findings.append(
            "functional coverage is %.2f points below the class 1 floor" % shortfall
        )

    baseline_age = case.get("baseline_age_months", 0)
    routing = route_pld_design(
        origin,
        changed_groups=groups,
        evidence_gaps=gaps,
        coverage_met=coverage_met,
        baseline_age_months=baseline_age,
        policy=resolved,
    )
    if gaps:
        findings.append(
            "the design-assurance record is short of %s" % ", ".join(sorted(gaps))
        )

    maintenance = maintenance_duties(
        technology,
        bool(case.get("reprogramming_after_delivery", False)),
        resolved,
    )
    findings.extend(maintenance["findings"])

    return {
        "origin": origin,
        "technology": technology,
        "route": routing["route"],
        "route_driver": routing["driver"],
        "activities": routing["activities"],
        "changed_axes": changed,
        "changed_axis_groups": groups,
        "design_delta_index": delta_index,
        "design_assurance_gaps": gaps,
        "coverage_shortfall_pct": shortfall,
        "coverage_met": coverage_met,
        "maintenance_duties": maintenance["duties"],
        "findings": findings,
        "routable": routing["route"] != EVIDENCE_INCOMPLETE,
    }

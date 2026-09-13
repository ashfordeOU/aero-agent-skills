#!/usr/bin/env python3
"""Visual inspection of solar-array wiring after acceptance testing.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.12. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is a post-test examination. The harness is looked at again
once the acceptance tests have been run, and a list of wiring faults is
excluded from the delivered article: a bend pulled tighter than the
cable can take, twist worked into a run, and a crease set into the
jacket. Those three share a property that decides the whole design of
this screen -- they are permanent set. The cable does not recover, so
the inspection stage matters: a sharp bend seen before the tests is a
routing defect to be dressed out, while the same bend seen after them
is an excluded fault on an article that has already been through its
environment.

Fault kinds
    sharp-bend          bend radius tighter than the cable allows
    excess-twist        turns worked into a run beyond the lay limit
    jacket-crease       a flattened permanent set in the jacket
    conductor-kink      a sharp permanent set in the conductor itself
    jacket-chafe        jacket worn away against a structure or tie
    insulation-nick     a cut into the insulation from a tool
    unsupported-span    run length between tie-downs beyond the limit

Cable categories carry their own minimum bend radius, expressed as a
multiple of the cable outer diameter, and their own twist allowance.

    unshielded-power    plain insulated conductor
    shielded-signal     braid under the jacket
    coaxial-rf          a dielectric that takes a set when bent
    flexible-flat       a flat laminate with a preferred bend plane

Dispositions are accept, rework and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WIRING_FAULT_KINDS = (
    "sharp-bend",
    "excess-twist",
    "jacket-crease",
    "conductor-kink",
    "jacket-chafe",
    "insulation-nick",
    "unsupported-span",
)

# The faults the clause excludes once acceptance testing is complete.
POST_TEST_EXCLUDED_KINDS = (
    "sharp-bend",
    "excess-twist",
    "jacket-crease",
    "conductor-kink",
)

CABLE_CATEGORIES = (
    "unshielded-power",
    "shielded-signal",
    "coaxial-rf",
    "flexible-flat",
)

INSPECTION_STAGES = ("before-acceptance-test", "after-acceptance-test")

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_WIRING_CRITERIA = {
    "min_bend_radius_factor": {
        "unshielded-power": 6.0,
        "shielded-signal": 8.0,
        "coaxial-rf": 10.0,
        "flexible-flat": 12.0,
    },
    "max_twist_turns_per_m": {
        "unshielded-power": 2.0,
        "shielded-signal": 1.0,
        "coaxial-rf": 0.5,
        "flexible-flat": 0.25,
    },
    # A crease is read as how flat the jacket has been pressed: the
    # minor axis over the major axis of the deformed section.
    "min_jacket_roundness_ratio": 0.85,
    # Chafe and nick are read as depth into the jacket or insulation.
    "accept_chafe_depth_fraction": 0.10,
    "rework_chafe_depth_fraction": 0.40,
    "accept_nick_depth_fraction": 0.05,
    "rework_nick_depth_fraction": 0.25,
    "max_unsupported_span_mm": 150.0,
    "rework_unsupported_span_mm": 300.0,
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


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A limit is a product of a factor and a measured diameter, so a
    measurement sitting exactly on the limit can evaluate a few units in
    the last place below it. The limit is never relaxed; only the
    comparison tolerates the representation error.
    """
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_wiring_criteria(criteria):
    """Check a criteria set covers every cable category and every limit."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in ("min_bend_radius_factor", "max_twist_turns_per_m"):
        table = criteria.get(key)
        if not isinstance(table, dict):
            raise ValueError("criteria %s must be a mapping" % key)
        missing = set(CABLE_CATEGORIES) - set(table)
        if missing:
            raise ValueError(
                "criteria %s is missing entries: %s"
                % (key, ", ".join(sorted(missing)))
            )
        for category in CABLE_CATEGORIES:
            _require_positive(
                "criteria %s[%s]" % (key, category), table[category]
            )
    roundness = _require_positive(
        "min_jacket_roundness_ratio", criteria.get("min_jacket_roundness_ratio")
    )
    if roundness > 1.0 and not _close(roundness, 1.0):
        raise ValueError(
            "criteria min_jacket_roundness_ratio cannot exceed one, got %r"
            % (roundness,)
        )
    pairs = (
        ("accept_chafe_depth_fraction", "rework_chafe_depth_fraction"),
        ("accept_nick_depth_fraction", "rework_nick_depth_fraction"),
        ("max_unsupported_span_mm", "rework_unsupported_span_mm"),
    )
    for accept_key, rework_key in pairs:
        accept_value = _require_non_negative(accept_key, criteria.get(accept_key))
        rework_value = _require_non_negative(rework_key, criteria.get(rework_key))
        if rework_value < accept_value:
            raise ValueError(
                "criteria %s is below the accept limit %s" % (rework_key, accept_key)
            )
    return criteria


def minimum_bend_radius_mm(
    outer_diameter_mm, cable_category, criteria=DEFAULT_WIRING_CRITERIA
):
    """Smallest bend radius the cable category allows, in millimetres."""
    diameter = _require_positive("outer_diameter_mm", outer_diameter_mm)
    _require_choice("cable_category", cable_category, CABLE_CATEGORIES)
    factor = criteria["min_bend_radius_factor"][cable_category]
    return factor * diameter


def bend_radius_ratio(measured_radius_mm, outer_diameter_mm):
    """Measured bend radius expressed in cable outer diameters."""
    radius = _require_positive("measured_radius_mm", measured_radius_mm)
    diameter = _require_positive("outer_diameter_mm", outer_diameter_mm)
    return radius / diameter


def jacket_roundness_ratio(minor_axis_mm, major_axis_mm):
    """How round the jacket still is; one is undeformed, zero is flat."""
    minor = _require_positive("minor_axis_mm", minor_axis_mm)
    major = _require_positive("major_axis_mm", major_axis_mm)
    if minor > major and not _close(minor, major):
        raise ValueError(
            "minor axis %.3f mm exceeds the major axis %.3f mm; the axes are "
            "swapped" % (minor, major)
        )
    if minor > major:
        minor = major
    return minor / major


def twist_turns_per_m(turns, run_length_mm):
    """Turns worked into a run, normalised to turns per metre."""
    count = _require_non_negative("turns", turns)
    length = _require_positive("run_length_mm", run_length_mm)
    return count * 1000.0 / length


def assess_wiring_fault(
    fault, cable, stage, criteria=DEFAULT_WIRING_CRITERIA
):
    """Disposition one wiring fault for a cable at a given inspection stage."""
    validate_wiring_criteria(criteria)
    if not isinstance(fault, dict):
        raise ValueError("fault must be a mapping, got %r" % (fault,))
    if not isinstance(cable, dict):
        raise ValueError("cable must be a mapping, got %r" % (cable,))
    _require_choice("stage", stage, INSPECTION_STAGES)
    kind = _require_choice("kind", fault.get("kind"), WIRING_FAULT_KINDS)
    category = _require_choice(
        "cable_category", cable.get("cable_category"), CABLE_CATEGORIES
    )
    diameter = _require_positive(
        "outer_diameter_mm", cable.get("outer_diameter_mm")
    )
    after_test = stage == "after-acceptance-test"
    excluded = after_test and kind in POST_TEST_EXCLUDED_KINDS
    reasons = []
    measurements = {}

    if kind == "sharp-bend":
        radius = _require_positive(
            "measured_radius_mm", fault.get("measured_radius_mm")
        )
        limit = minimum_bend_radius_mm(diameter, category, criteria)
        ratio = bend_radius_ratio(radius, diameter)
        measurements["measured_radius_mm"] = radius
        measurements["min_bend_radius_mm"] = limit
        measurements["bend_radius_in_diameters"] = ratio
        if _at_least(radius, limit):
            disposition = ACCEPT
            excluded = False
        else:
            disposition = REJECT if after_test else REWORK
            reasons.append(
                "bend radius %.2f mm is under the %.2f mm minimum for a %s "
                "cable of %.2f mm diameter" % (radius, limit, category, diameter)
            )

    elif kind == "excess-twist":
        turns = fault.get("turns")
        run_length = fault.get("run_length_mm")
        if turns is None or run_length is None:
            raise ValueError(
                "an excess-twist fault needs turns and run_length_mm to give "
                "a rate that a limit can be compared against"
            )
        rate = twist_turns_per_m(turns, run_length)
        limit = criteria["max_twist_turns_per_m"][category]
        measurements["twist_turns_per_m"] = rate
        measurements["max_twist_turns_per_m"] = limit
        if _at_most(rate, limit):
            disposition = ACCEPT
            excluded = False
        else:
            disposition = REJECT if after_test else REWORK
            reasons.append(
                "twist %.3f turns per metre exceeds the %.3f limit for a %s "
                "cable" % (rate, limit, category)
            )

    elif kind == "jacket-crease":
        minor = fault.get("minor_axis_mm")
        major = fault.get("major_axis_mm")
        if minor is None or major is None:
            raise ValueError(
                "a jacket-crease fault needs minor_axis_mm and major_axis_mm "
                "to show how flat the section has been pressed"
            )
        ratio = jacket_roundness_ratio(minor, major)
        limit = criteria["min_jacket_roundness_ratio"]
        measurements["jacket_roundness_ratio"] = ratio
        measurements["min_jacket_roundness_ratio"] = limit
        if _at_least(ratio, limit):
            disposition = ACCEPT
            excluded = False
        else:
            disposition = REJECT if after_test else REWORK
            reasons.append(
                "jacket roundness %.3f is under the %.3f minimum; the section "
                "carries a permanent set" % (ratio, limit)
            )

    elif kind == "conductor-kink":
        disposition = REJECT if after_test else REWORK
        reasons.append(
            "a kink is a permanent set in the conductor itself; straightening "
            "it restores the shape and not the strands"
        )

    elif kind in ("jacket-chafe", "insulation-nick"):
        depth = _require_non_negative("depth_mm", fault.get("depth_mm"))
        wall = _require_positive("wall_thickness_mm", fault.get("wall_thickness_mm"))
        fraction = depth / wall
        if kind == "jacket-chafe":
            accept_limit = criteria["accept_chafe_depth_fraction"]
            rework_limit = criteria["rework_chafe_depth_fraction"]
        else:
            accept_limit = criteria["accept_nick_depth_fraction"]
            rework_limit = criteria["rework_nick_depth_fraction"]
        measurements["depth_fraction"] = fraction
        measurements["accept_depth_fraction"] = accept_limit
        measurements["rework_depth_fraction"] = rework_limit
        if _at_most(fraction, accept_limit):
            disposition = ACCEPT
        elif _at_most(fraction, rework_limit):
            disposition = REWORK
            reasons.append(
                "%s depth %.3f of the wall exceeds the %.3f accept limit"
                % (kind, fraction, accept_limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "%s depth %.3f of the wall exceeds the %.3f rework limit"
                % (kind, fraction, rework_limit)
            )

    else:  # unsupported-span
        span = _require_positive("span_mm", fault.get("span_mm"))
        accept_limit = criteria["max_unsupported_span_mm"]
        rework_limit = criteria["rework_unsupported_span_mm"]
        measurements["span_mm"] = span
        measurements["max_unsupported_span_mm"] = accept_limit
        if _at_most(span, accept_limit):
            disposition = ACCEPT
        elif _at_most(span, rework_limit):
            disposition = REWORK
            reasons.append(
                "unsupported span %.1f mm exceeds the %.1f mm tie-down limit"
                % (span, accept_limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "unsupported span %.1f mm exceeds the %.1f mm rework limit; "
                "the run cannot be brought back by adding one tie"
                % (span, rework_limit)
            )

    if excluded and disposition == ACCEPT:
        excluded = False
    return {
        "id": fault.get("id"),
        "kind": kind,
        "cable_category": category,
        "stage": stage,
        "post_test_excluded": excluded,
        "disposition": disposition,
        "measurements": measurements,
        "reasons": reasons,
    }


def group_faults_by_kind(faults):
    """Group faults by kind and count the post-test exclusion candidates."""
    if not isinstance(faults, (list, tuple)):
        raise ValueError("faults must be a list, got %r" % (faults,))
    counts = dict((kind, 0) for kind in WIRING_FAULT_KINDS)
    for fault in faults:
        if not isinstance(fault, dict):
            raise ValueError("each fault must be a mapping, got %r" % (fault,))
        kind = _require_choice("kind", fault.get("kind"), WIRING_FAULT_KINDS)
        counts[kind] += 1
    candidates = sum(counts[kind] for kind in POST_TEST_EXCLUDED_KINDS)
    return {"counts": counts, "exclusion_candidate_count": candidates}


def inspect_wiring(harness, criteria=DEFAULT_WIRING_CRITERIA):
    """Full clause 5.5.3.2.12 wiring examination with a harness verdict."""
    validate_wiring_criteria(criteria)
    if not isinstance(harness, dict):
        raise ValueError("harness must be a mapping, got %r" % (harness,))
    harness_id = harness.get("harness_id")
    if not isinstance(harness_id, str) or not harness_id.strip():
        raise ValueError("harness needs a non-empty harness_id for traceability")
    stage = _require_choice("stage", harness.get("stage"), INSPECTION_STAGES)
    cable = harness.get("cable")
    if not isinstance(cable, dict):
        raise ValueError("harness needs a cable mapping with its category and size")
    faults = harness.get("faults")
    if not isinstance(faults, (list, tuple)):
        raise ValueError("harness faults must be a list, got %r" % (faults,))

    seen = set()
    assessed = []
    for fault in faults:
        result = assess_wiring_fault(fault, cable, stage, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate fault id %r on harness %s; traceability to the "
                    "rework record would be lost" % (marker, harness_id)
                )
            seen.add(marker)
        assessed.append(result)

    grouping = group_faults_by_kind(list(faults))
    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []
    if not assessed:
        findings.append(
            "no faults recorded; the wiring is examined and clean, and the "
            "record still stands as the inspection evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    excluded_ids = [
        result["id"] for result in assessed if result["post_test_excluded"]
    ]
    if excluded_ids:
        findings.append(
            "post-test excluded faults on %s; the harness cannot be delivered "
            "against this record" % ", ".join(str(m) for m in excluded_ids)
        )
    return {
        "harness_id": harness_id,
        "stage": stage,
        "verdict": verdict,
        "faults": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "post_test_excluded_ids": excluded_ids,
        "kind_counts": grouping["counts"],
        "retest_required": stage == "after-acceptance-test" and verdict == REWORK,
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }

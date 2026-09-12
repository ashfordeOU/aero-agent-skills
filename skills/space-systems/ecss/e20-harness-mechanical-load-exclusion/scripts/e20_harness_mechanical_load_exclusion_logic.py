#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.8.2 harness mechanical load exclusion
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires spacecraft wiring to be
routed and restrained so that the harness itself never becomes part of
a structural or mechanical load path -- the structure carries the
loads, the harness is only carried by it. This module implements the
checkable part of that routing rule: categorization of each attachment
as a restraint or a load-path misuse, the distributed transverse load
a bundle sees under a quasi-static acceleration, the span tension and
sag that follow from the installed slack and the clamp spacing, the
service-loop length a crossing of a moving or thermally displacing
interface needs so the bundle never goes taut, the reaction a
connector would have to take if a bundle were left unsupported behind
it, and the minimum installed bend radius. It does not size the
structure, does not run a random-vibration response, and does not pick
clamp hardware.
"""

import math

STANDARD_GRAVITY_M_S2 = 9.80665

# Boundary comparisons absorb floating-point representation error only;
# the engineering limit itself is never widened.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-12

DEFAULT_SLACK_FACTOR = 1.25
DEFAULT_BEND_RADIUS_RATIO = 6.0

# Attachments that hold the harness to structure without letting the
# harness react a structural load.
RESTRAINT_ATTACHMENT_KINDS = frozenset(
    {
        "p_clamp_on_structure_standoff",
        "cable_tray_tie",
        "lacing_to_dedicated_bracket",
        "saddle_clamp_on_harness_rail",
        "adhesive_tie_base_on_panel",
    }
)

# Attachments that put the harness into a load path; each one is a
# clause 5.8.2 finding on sight.
LOAD_PATH_ATTACHMENT_KINDS = frozenset(
    {
        "harness_as_structural_tie",
        "harness_tensioned_between_hardpoints",
        "connector_as_sole_bundle_support",
        "harness_bridging_moving_joint_without_slack",
        "harness_trapped_in_bolted_joint_faying_surface",
    }
)

_SPAN_REQUIRED_KEYS = (
    "span_id",
    "bundle_mass_per_m_kg",
    "quasi_static_accel_g",
    "span_length_m",
    "installed_sag_m",
    "allowable_tension_n",
    "clearance_to_structure_m",
    "max_clamp_spacing_m",
)

_CROSSING_REQUIRED_KEYS = (
    "crossing_id",
    "attachment_kind",
    "thermal_displacement_m",
    "mechanism_stroke_m",
    "assembly_tolerance_m",
    "installed_slack_m",
    "supported_both_sides",
)

_TERMINATION_REQUIRED_KEYS = (
    "termination_id",
    "unsupported_mass_kg",
    "quasi_static_accel_g",
    "allowable_connector_load_n",
    "first_support_distance_m",
    "max_first_support_distance_m",
    "strain_relief_present",
)


def _within(value, limit):
    """True when value does not exceed limit. An exact-boundary case is
    accepted even when the computed value sits a few units in the last
    place above the limit through the arithmetic that produced it."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def _at_least(value, floor):
    """True when value reaches floor, absorbing representation error at
    an exact-boundary case in the same way as _within."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=COMPARISON_REL_TOL, abs_tol=COMPARISON_ABS_TOL
    )


def _require_keys(record, keys, what):
    missing = [k for k in keys if k not in record]
    if missing:
        raise ValueError(
            "%s record is missing required key(s): %s"
            % (what, ", ".join(sorted(missing)))
        )


def categorize_harness_attachment(attachment_kind):
    """Category of a harness attachment: "restraint" when the fitting
    holds the bundle to structure without reacting structural load, or
    "load_path" when the arrangement makes the harness carry load.
    Raises ValueError for a kind that is not a clause 5.8.2 harness
    attachment."""
    if attachment_kind in RESTRAINT_ATTACHMENT_KINDS:
        return "restraint"
    if attachment_kind in LOAD_PATH_ATTACHMENT_KINDS:
        return "load_path"
    raise ValueError(
        "unrecognized harness attachment kind %r under "
        "E-ST-20C clause 5.8.2" % (attachment_kind,)
    )


def distributed_transverse_load(bundle_mass_per_m_kg, quasi_static_accel_g):
    """Transverse load per metre of bundle, in newtons per metre, under
    a quasi-static acceleration expressed in g. Raises ValueError for a
    non-positive mass per metre or a negative acceleration."""
    if bundle_mass_per_m_kg <= 0:
        raise ValueError("bundle_mass_per_m_kg must be > 0")
    if quasi_static_accel_g < 0:
        raise ValueError("quasi_static_accel_g must be >= 0")
    return bundle_mass_per_m_kg * quasi_static_accel_g * STANDARD_GRAVITY_M_S2


def span_tension(load_per_m_n, span_m, sag_m):
    """Axial tension in a clamped bundle span carrying a uniform
    transverse load, from the shallow-sag relation tension equals load
    per metre times span squared over eight times sag. Raises
    ValueError for a negative load, a non-positive span, or a
    non-positive sag -- a span installed with no slack at all has no
    finite tension solution and is itself the defect clause 5.8.2
    excludes."""
    if load_per_m_n < 0:
        raise ValueError("load_per_m_n must be >= 0")
    if span_m <= 0:
        raise ValueError("span_m must be > 0")
    if sag_m <= 0:
        raise ValueError(
            "sag_m must be > 0; a zero-slack span is routed as a tie, "
            "which clause 5.8.2 excludes"
        )
    return load_per_m_n * span_m * span_m / (8.0 * sag_m)


def span_sag(load_per_m_n, span_m, tension_n):
    """Mid-span sag in metres for a given installed tension, the
    inverse of span_tension. Raises ValueError for a negative load, a
    non-positive span, or a non-positive tension."""
    if load_per_m_n < 0:
        raise ValueError("load_per_m_n must be >= 0")
    if span_m <= 0:
        raise ValueError("span_m must be > 0")
    if tension_n <= 0:
        raise ValueError("tension_n must be > 0")
    return load_per_m_n * span_m * span_m / (8.0 * tension_n)


def max_support_spacing(load_per_m_n, installed_sag_m, allowable_tension_n):
    """Longest span, in metres, that holds the bundle tension at or
    below the allowable for the installed sag. Raises ValueError for a
    non-positive load, sag or allowable tension."""
    if load_per_m_n <= 0:
        raise ValueError("load_per_m_n must be > 0")
    if installed_sag_m <= 0:
        raise ValueError("installed_sag_m must be > 0")
    if allowable_tension_n <= 0:
        raise ValueError("allowable_tension_n must be > 0")
    return math.sqrt(
        8.0 * installed_sag_m * allowable_tension_n / load_per_m_n
    )


def minimum_bend_radius(bundle_diameter_m, radius_ratio=DEFAULT_BEND_RADIUS_RATIO):
    """Smallest permitted installed bend radius in metres, as a
    multiple of the bundle diameter. Raises ValueError for a
    non-positive diameter or a ratio below one."""
    if bundle_diameter_m <= 0:
        raise ValueError("bundle_diameter_m must be > 0")
    if radius_ratio < 1.0:
        raise ValueError("radius_ratio must be >= 1.0")
    return bundle_diameter_m * radius_ratio


def span_findings(span):
    """Findings (empty list when the span is compliant) for one clamped
    bundle span. Required keys: span_id, bundle_mass_per_m_kg,
    quasi_static_accel_g, span_length_m, installed_sag_m,
    allowable_tension_n, clearance_to_structure_m, max_clamp_spacing_m.
    Optional keys bundle_diameter_m, installed_bend_radius_m and
    bend_radius_ratio add the bend check. Raises ValueError for a
    missing required key or an out-of-range value."""
    _require_keys(span, _SPAN_REQUIRED_KEYS, "span")
    span_id = span["span_id"]
    findings = []
    load_per_m = distributed_transverse_load(
        span["bundle_mass_per_m_kg"], span["quasi_static_accel_g"]
    )
    tension = span_tension(
        load_per_m, span["span_length_m"], span["installed_sag_m"]
    )
    allowable = span["allowable_tension_n"]
    if allowable <= 0:
        raise ValueError("allowable_tension_n must be > 0")
    if not _within(tension, allowable):
        findings.append(
            "span %s: bundle tension %.3f N exceeds the allowable %.3f N, "
            "so the span reacts load as a tie" % (span_id, tension, allowable)
        )
    clearance = span["clearance_to_structure_m"]
    if clearance < 0:
        raise ValueError("clearance_to_structure_m must be >= 0")
    if not _within(span["installed_sag_m"], clearance):
        findings.append(
            "span %s: installed sag %.4f m exceeds the clearance %.4f m, so "
            "the bundle would bear on neighbouring hardware"
            % (span_id, span["installed_sag_m"], clearance)
        )
    max_spacing = span["max_clamp_spacing_m"]
    if max_spacing <= 0:
        raise ValueError("max_clamp_spacing_m must be > 0")
    if not _within(span["span_length_m"], max_spacing):
        findings.append(
            "span %s: clamp spacing %.4f m exceeds the routing rule limit "
            "%.4f m" % (span_id, span["span_length_m"], max_spacing)
        )
    if "installed_bend_radius_m" in span:
        if "bundle_diameter_m" not in span:
            raise ValueError(
                "span record with installed_bend_radius_m must also carry "
                "bundle_diameter_m"
            )
        floor = minimum_bend_radius(
            span["bundle_diameter_m"],
            span.get("bend_radius_ratio", DEFAULT_BEND_RADIUS_RATIO),
        )
        if not _at_least(span["installed_bend_radius_m"], floor):
            findings.append(
                "span %s: installed bend radius %.4f m is below the minimum "
                "%.4f m, which puts bending load into the conductors"
                % (span_id, span["installed_bend_radius_m"], floor)
            )
    return findings


def required_service_loop_length(
    thermal_displacement_m,
    mechanism_stroke_m,
    assembly_tolerance_m,
    slack_factor=DEFAULT_SLACK_FACTOR,
):
    """Slack length in metres a harness must carry across an interface
    that moves, in order that the bundle never goes taut: the summed
    relative displacement times a slack factor. Raises ValueError for a
    negative displacement contribution or a slack factor below one."""
    for name, value in (
        ("thermal_displacement_m", thermal_displacement_m),
        ("mechanism_stroke_m", mechanism_stroke_m),
        ("assembly_tolerance_m", assembly_tolerance_m),
    ):
        if value < 0:
            raise ValueError("%s must be >= 0" % name)
    if slack_factor < 1.0:
        raise ValueError("slack_factor must be >= 1.0")
    total = thermal_displacement_m + mechanism_stroke_m + assembly_tolerance_m
    return total * slack_factor


def interface_crossing_findings(crossing):
    """Findings (empty list when compliant) for one harness crossing of
    a structural interface. Required keys: crossing_id,
    attachment_kind, thermal_displacement_m, mechanism_stroke_m,
    assembly_tolerance_m, installed_slack_m, supported_both_sides.
    Optional key slack_factor. Raises ValueError for a missing key, an
    unrecognized attachment kind, or an out-of-range value."""
    _require_keys(crossing, _CROSSING_REQUIRED_KEYS, "crossing")
    crossing_id = crossing["crossing_id"]
    findings = []
    if categorize_harness_attachment(crossing["attachment_kind"]) == "load_path":
        findings.append(
            "crossing %s: attachment %s routes the harness as a load path"
            % (crossing_id, crossing["attachment_kind"])
        )
    required = required_service_loop_length(
        crossing["thermal_displacement_m"],
        crossing["mechanism_stroke_m"],
        crossing["assembly_tolerance_m"],
        crossing.get("slack_factor", DEFAULT_SLACK_FACTOR),
    )
    installed = crossing["installed_slack_m"]
    if installed < 0:
        raise ValueError("installed_slack_m must be >= 0")
    if not _at_least(installed, required):
        findings.append(
            "crossing %s: installed slack %.4f m is short of the %.4f m the "
            "relative displacement needs, so the bundle goes taut"
            % (crossing_id, installed, required)
        )
    if not crossing["supported_both_sides"]:
        findings.append(
            "crossing %s: the bundle is not anchored on both sides of the "
            "interface, so it ties the two structures together" % crossing_id
        )
    return findings


def connector_reaction_force(unsupported_mass_kg, quasi_static_accel_g):
    """Force in newtons that an unsupported bundle mass hanging off a
    connector drives into that connector under a quasi-static
    acceleration. Raises ValueError for a negative mass or
    acceleration."""
    if unsupported_mass_kg < 0:
        raise ValueError("unsupported_mass_kg must be >= 0")
    if quasi_static_accel_g < 0:
        raise ValueError("quasi_static_accel_g must be >= 0")
    return unsupported_mass_kg * quasi_static_accel_g * STANDARD_GRAVITY_M_S2


def connector_termination_findings(termination):
    """Findings (empty list when compliant) for one connector
    termination. Required keys: termination_id, unsupported_mass_kg,
    quasi_static_accel_g, allowable_connector_load_n,
    first_support_distance_m, max_first_support_distance_m,
    strain_relief_present. Raises ValueError for a missing key or an
    out-of-range value."""
    _require_keys(termination, _TERMINATION_REQUIRED_KEYS, "termination")
    term_id = termination["termination_id"]
    findings = []
    force = connector_reaction_force(
        termination["unsupported_mass_kg"], termination["quasi_static_accel_g"]
    )
    allowable = termination["allowable_connector_load_n"]
    if allowable <= 0:
        raise ValueError("allowable_connector_load_n must be > 0")
    if not _within(force, allowable):
        findings.append(
            "termination %s: connector reacts %.3f N against an allowable "
            "%.3f N, so the connector carries the bundle"
            % (term_id, force, allowable)
        )
    distance = termination["first_support_distance_m"]
    limit = termination["max_first_support_distance_m"]
    if distance < 0:
        raise ValueError("first_support_distance_m must be >= 0")
    if limit <= 0:
        raise ValueError("max_first_support_distance_m must be > 0")
    if not _within(distance, limit):
        findings.append(
            "termination %s: first support sits %.4f m from the connector, "
            "beyond the %.4f m limit" % (term_id, distance, limit)
        )
    if not termination["strain_relief_present"]:
        findings.append(
            "termination %s: no strain relief behind the connector" % term_id
        )
    return findings


def aggregate_harness_load_exclusion_review(harness):
    """Clause 5.8.2 review of a routed harness. harness keys:
    harness_id, plus optional lists attachments (mappings with
    attachment_id and attachment_kind), spans, crossings and
    terminations. Returns a mapping of the four finding lists and a
    compliant flag that is true only when every list is empty. Raises
    ValueError for a missing harness_id or through the per-record
    checks."""
    if "harness_id" not in harness:
        raise ValueError("harness record is missing required key: harness_id")
    attachment_findings = []
    for attachment in harness.get("attachments", []):
        _require_keys(
            attachment, ("attachment_id", "attachment_kind"), "attachment"
        )
        if categorize_harness_attachment(attachment["attachment_kind"]) == "load_path":
            attachment_findings.append(
                "attachment %s: %s makes the harness a structural load path"
                % (attachment["attachment_id"], attachment["attachment_kind"])
            )
    span_results = []
    for span in harness.get("spans", []):
        span_results.extend(span_findings(span))
    crossing_results = []
    for crossing in harness.get("crossings", []):
        crossing_results.extend(interface_crossing_findings(crossing))
    termination_results = []
    for termination in harness.get("terminations", []):
        termination_results.extend(connector_termination_findings(termination))
    return {
        "harness_id": harness["harness_id"],
        "attachment_findings": attachment_findings,
        "span_findings": span_results,
        "crossing_findings": crossing_results,
        "termination_findings": termination_results,
        "compliant": not (
            attachment_findings
            or span_results
            or crossing_results
            or termination_results
        ),
    }

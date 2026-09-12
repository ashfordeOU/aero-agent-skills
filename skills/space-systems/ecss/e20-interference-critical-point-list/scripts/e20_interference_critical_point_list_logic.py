#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.1.2 interference critical point list
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the supplier to assemble, and
put to the customer for approval, the list of points at which the
electromagnetic interference margin is to be demonstrated. This module
implements the checkable part of that clause: the coupling-path family
behind each candidate point, the selection rule that says which victim
circuit needs a point on which family, deterministic derivation of the
candidate list, the mandatory record fields a listed point carries,
the demonstrated separation against the margin the point requires, the
merged frequency coverage of the listed points against the project's
spectrum span, and the submission and approval state of the assembled
list. It does not perform the demonstration, does not compute a
coupling model and does not set the project spectrum span.
"""

import datetime
import math

COUPLING_PATH_FAMILY = {
    "conducted_emission": "conducted",
    "conducted_susceptibility": "conducted",
    "radiated_emission": "radiated",
    "radiated_susceptibility": "radiated",
    "common_impedance_coupling": "common_impedance",
    "electrostatic_discharge": "electrostatic_discharge",
}
COUPLING_PATH_FAMILIES = (
    "conducted",
    "radiated",
    "common_impedance",
    "electrostatic_discharge",
)

DEMONSTRATION_METHOD_EVIDENCE = {
    "emc_measurement": "measured",
    "coupling_analysis": "analytical",
    "similarity_to_qualified_unit": "heritage",
    "harness_routing_inspection": "workmanship",
}

CRITICALITY_ORDER = (
    "safety_critical",
    "mission_critical",
    "essential",
    "non_essential",
)

MANDATORY_POINT_FIELDS = (
    "point_id",
    "victim_circuit_id",
    "coupling_path",
    "frequency_band_hz",
    "demonstration_method",
    "required_margin_db",
    "responsible_party",
)

_REL_TOL = 1e-9
_MARGIN_ABS_TOL = 1e-9


def categorize_coupling_path(coupling_path):
    """Coupling-path family behind a named path: "conducted",
    "radiated", "common_impedance" or "electrostatic_discharge". The
    family, not the named path, is what a point is selected against, so
    an emission point and a susceptibility point on the same family do
    not double-count. Raises ValueError for an unrecognized path."""
    if coupling_path in COUPLING_PATH_FAMILY:
        return COUPLING_PATH_FAMILY[coupling_path]
    raise ValueError(
        "unrecognized coupling path %r under E-ST-20C clause 6.3.1.2"
        % (coupling_path,)
    )


def categorize_demonstration_method(demonstration_method):
    """Evidence class a demonstration method produces: "measured",
    "analytical", "heritage" or "workmanship". Raises ValueError for a
    method the point list cannot carry."""
    if demonstration_method in DEMONSTRATION_METHOD_EVIDENCE:
        return DEMONSTRATION_METHOD_EVIDENCE[demonstration_method]
    raise ValueError(
        "unrecognized demonstration method %r" % (demonstration_method,)
    )


def validate_frequency_band(band):
    """Normalized (low, high) frequency band in hertz. Raises
    ValueError when the band is not a pair, carries a non-real or
    non-finite edge, starts below zero, or does not rise."""
    if isinstance(band, str) or not isinstance(band, (list, tuple)):
        raise ValueError("frequency band must be a (low, high) pair, got %r" % (band,))
    if len(band) != 2:
        raise ValueError("frequency band must carry exactly two edges, got %r" % (band,))
    edges = []
    for name, edge in zip(("low", "high"), band):
        if isinstance(edge, bool) or not isinstance(edge, (int, float)):
            raise ValueError("band %s edge must be a real number, got %r" % (name, edge))
        if math.isnan(edge) or math.isinf(edge):
            raise ValueError("band %s edge must be finite, got %r" % (name, edge))
        edges.append(float(edge))
    if edges[0] < 0.0:
        raise ValueError("band low edge must be >= 0 Hz, got %r" % (edges[0],))
    if edges[1] <= edges[0]:
        raise ValueError(
            "band high edge %r must exceed the low edge %r" % (edges[1], edges[0])
        )
    return (edges[0], edges[1])


def point_selection_required(victim_category, path_family, externally_exposed=False):
    """True when clause 6.3.1.2 asks for a demonstration point on this
    victim and this coupling-path family.

    The safety group carries a point on every family. The mission group
    carries one on the conducted, radiated and common-impedance
    families, and one on the discharge family only where the circuit is
    externally exposed. The essential group carries the conducted and
    radiated families. The non essential group carries none. Raises
    ValueError for a category off the ladder, an unrecognized family or
    a non-boolean exposure flag.
    """
    if victim_category not in CRITICALITY_ORDER:
        raise ValueError("unrecognized criticality category %r" % (victim_category,))
    if path_family not in COUPLING_PATH_FAMILIES:
        raise ValueError("unrecognized coupling path family %r" % (path_family,))
    if not isinstance(externally_exposed, bool):
        raise ValueError(
            "externally_exposed must be a boolean, got %r" % (externally_exposed,)
        )
    if victim_category == "safety_critical":
        return True
    if victim_category == "mission_critical":
        if path_family == "electrostatic_discharge":
            return externally_exposed
        return True
    if victim_category == "essential":
        return path_family in ("conducted", "radiated")
    return False


def derive_candidate_points(victims):
    """Deterministic candidate point list for a victim inventory.

    victims: records carrying circuit_id, criticality_category and an
    optional externally_exposed flag. Returns a tuple of records
    ordered by point identifier, each naming the victim, the
    coupling-path family and a derived point identifier. Raises
    ValueError for a malformed victim record or a repeated circuit
    identifier.
    """
    if isinstance(victims, dict) or not isinstance(victims, (list, tuple)):
        raise ValueError("victims must be a list or tuple of victim records")
    seen = set()
    candidates = []
    for victim in victims:
        if not isinstance(victim, dict):
            raise ValueError("victim record must be a mapping, got %r" % (victim,))
        circuit_id = victim.get("circuit_id")
        if not isinstance(circuit_id, str) or not circuit_id.strip():
            raise ValueError(
                "victim circuit_id must be a non-empty string, got %r" % (circuit_id,)
            )
        if circuit_id in seen:
            raise ValueError("duplicate victim circuit_id %r" % (circuit_id,))
        seen.add(circuit_id)
        exposed = victim.get("externally_exposed", False)
        for family in COUPLING_PATH_FAMILIES:
            if point_selection_required(
                victim.get("criticality_category"), family, exposed
            ):
                candidates.append(
                    {
                        "point_id": "ICP-%s-%s" % (circuit_id, family.upper()),
                        "victim_circuit_id": circuit_id,
                        "coupling_path_family": family,
                    }
                )
    return tuple(sorted(candidates, key=lambda record: record["point_id"]))


def point_record_findings(point):
    """Sorted findings against one listed point: a mandatory field
    absent or left empty, an unrecognized coupling path or
    demonstration method, a malformed frequency band, or a required
    margin that is not a finite non-negative number. Raises ValueError
    only when the point is not a mapping at all."""
    if not isinstance(point, dict):
        raise ValueError("point record must be a mapping, got %r" % (point,))
    label = point.get("point_id") if isinstance(point.get("point_id"), str) else "?"
    findings = []
    for field in MANDATORY_POINT_FIELDS:
        value = point.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append("point %s omits the mandatory field %s" % (label, field))
    if point.get("coupling_path") is not None:
        try:
            categorize_coupling_path(point["coupling_path"])
        except ValueError as exc:
            findings.append("point %s: %s" % (label, exc))
    if point.get("demonstration_method") is not None:
        try:
            categorize_demonstration_method(point["demonstration_method"])
        except ValueError as exc:
            findings.append("point %s: %s" % (label, exc))
    if point.get("frequency_band_hz") is not None:
        try:
            validate_frequency_band(point["frequency_band_hz"])
        except ValueError as exc:
            findings.append("point %s: %s" % (label, exc))
    margin = point.get("required_margin_db")
    if margin is not None:
        if isinstance(margin, bool) or not isinstance(margin, (int, float)):
            findings.append("point %s: required_margin_db must be a real number" % label)
        elif math.isnan(margin) or math.isinf(margin) or margin < 0.0:
            findings.append(
                "point %s: required_margin_db must be finite and >= 0" % label
            )
    return sorted(set(findings))


def demonstrated_margin_db(point):
    """Demonstrated separation in decibels at one point: the victim's
    susceptibility threshold less the emission level seen there. Raises
    ValueError when the demonstrated mapping is absent, malformed or
    carries a non-finite level."""
    if not isinstance(point, dict):
        raise ValueError("point record must be a mapping, got %r" % (point,))
    demonstrated = point.get("demonstrated")
    if not isinstance(demonstrated, dict):
        raise ValueError(
            "point %r carries no demonstrated level pair" % (point.get("point_id"),)
        )
    levels = []
    for key in ("susceptibility_threshold_dbuv", "emission_level_dbuv"):
        if key not in demonstrated:
            raise ValueError("demonstrated mapping omits %r" % (key,))
        value = demonstrated[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (key, value))
        if math.isnan(value) or math.isinf(value):
            raise ValueError("%s must be finite, got %r" % (key, value))
        levels.append(float(value))
    return levels[0] - levels[1]


def margin_meets_requirement(demonstrated_db, required_db):
    """True when the demonstrated separation meets or exceeds the
    required one.

    The demonstrated value is a difference of two measured decibel
    levels, so a point that is exactly on its limit can land a few
    units in the last place below it in binary floating point: 33.3
    less 27.3 evaluates to 5.9999999999999964. The comparison absorbs
    that representation error; the required margin is untouched. Raises
    ValueError for a non-real or non-finite input.
    """
    for name, value in (
        ("demonstrated_db", demonstrated_db),
        ("required_db", required_db),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (name, value))
        if math.isnan(value) or math.isinf(value):
            raise ValueError("%s must be finite, got %r" % (name, value))
    if demonstrated_db >= required_db:
        return True
    return math.isclose(
        demonstrated_db, required_db, rel_tol=_REL_TOL, abs_tol=_MARGIN_ABS_TOL
    )


def merge_bands(bands):
    """Frequency bands merged into a minimal ascending cover.

    Two bands are joined when they overlap or meet. Meeting is judged
    with a relative tolerance because the same edge reaches the list by
    different arithmetic paths: 30e6 and 0.03 * 1e9 are the same
    30 MHz edge, yet the second evaluates to 30000000.000000004. A bare
    comparison would leave a four-nanohertz hole between two adjoining
    bands and report it as uncovered spectrum. Raises ValueError
    through validate_frequency_band for a malformed band.
    """
    if isinstance(bands, dict) or not isinstance(bands, (list, tuple)):
        raise ValueError("bands must be a list or tuple of (low, high) pairs")
    normalized = sorted(validate_frequency_band(band) for band in bands)
    merged = []
    for low, high in normalized:
        if merged and (
            low <= merged[-1][1]
            or math.isclose(low, merged[-1][1], rel_tol=_REL_TOL, abs_tol=0.0)
        ):
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return tuple(merged)


def coverage_gaps(bands, spectrum_span_hz):
    """Stretches of the project spectrum span no listed band covers.

    The merged cover is clipped to the span and the holes between the
    clipped pieces are returned as (low, high) pairs. A hole whose
    edges are within tolerance of each other is representation noise
    and is dropped. Raises ValueError through validate_frequency_band
    for a malformed span or band.
    """
    span_low, span_high = validate_frequency_band(spectrum_span_hz)
    merged = merge_bands(bands)
    gaps = []
    cursor = span_low
    for low, high in merged:
        if high <= span_low or low >= span_high:
            continue
        low = max(low, span_low)
        high = min(high, span_high)
        if low > cursor and not math.isclose(
            low, cursor, rel_tol=_REL_TOL, abs_tol=0.0
        ):
            gaps.append((cursor, low))
        cursor = max(cursor, high)
    if cursor < span_high and not math.isclose(
        cursor, span_high, rel_tol=_REL_TOL, abs_tol=0.0
    ):
        gaps.append((cursor, span_high))
    return tuple(gaps)


def approval_state(package):
    """Submission and approval state of the assembled list:
    "not_submitted", "submitted_awaiting_approval" or "approved".
    Dates are ISO calendar dates. Raises ValueError for a malformed
    date, for an approval recorded against a list that was never
    submitted, or for an approval dated before the submission."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    submitted_raw = package.get("submitted_on")
    approved_raw = package.get("approved_on")
    submitted = None
    approved = None
    if submitted_raw is not None:
        if not isinstance(submitted_raw, str):
            raise ValueError("submitted_on must be an ISO date string")
        submitted = datetime.date.fromisoformat(submitted_raw)
    if approved_raw is not None:
        if not isinstance(approved_raw, str):
            raise ValueError("approved_on must be an ISO date string")
        approved = datetime.date.fromisoformat(approved_raw)
    if approved is not None and submitted is None:
        raise ValueError("the list carries an approval date but was never submitted")
    if approved is not None and approved < submitted:
        raise ValueError("approval date precedes the submission date")
    if submitted is None:
        return "not_submitted"
    if approved is None:
        return "submitted_awaiting_approval"
    return "approved"


def review_point_list(package):
    """Aggregate clause 6.3.1.2 review of one interference critical
    point list.

    package: mapping with victims, points, spectrum_span_hz, optional
    submitted_on, approved_on and approving_customer. Returns the
    derived candidate points, the findings for a required point that
    the list does not carry, the record findings, the margin findings,
    the uncovered spectrum stretches, the approval state and its
    findings, and a compliant verdict that is true only when every
    finding list is empty and the customer has approved. Raises
    ValueError for a malformed package or a repeated point identifier.
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    candidates = derive_candidate_points(package.get("victims", ()))
    points = package.get("points", ())
    if isinstance(points, dict) or not isinstance(points, (list, tuple)):
        raise ValueError("points must be a list or tuple of point records")
    record_findings = []
    declared = set()
    seen_ids = set()
    bands = []
    for point in points:
        record_findings.extend(point_record_findings(point))
        point_id = point.get("point_id")
        if isinstance(point_id, str) and point_id.strip():
            if point_id in seen_ids:
                raise ValueError("duplicate point_id %r" % (point_id,))
            seen_ids.add(point_id)
        try:
            family = categorize_coupling_path(point.get("coupling_path"))
        except ValueError:
            family = None
        victim_id = point.get("victim_circuit_id")
        if family is not None and isinstance(victim_id, str):
            declared.add((victim_id, family))
        band = point.get("frequency_band_hz")
        if band is not None:
            try:
                bands.append(validate_frequency_band(band))
            except ValueError:
                pass
    selection_findings = [
        "no demonstration point listed for victim %s on the %s coupling path"
        % (candidate["victim_circuit_id"], candidate["coupling_path_family"])
        for candidate in candidates
        if (candidate["victim_circuit_id"], candidate["coupling_path_family"])
        not in declared
    ]
    margin_findings = []
    for point in points:
        required = point.get("required_margin_db")
        if not isinstance(required, (int, float)) or isinstance(required, bool):
            continue
        label = point.get("point_id", "?")
        if point.get("demonstrated") is None:
            margin_findings.append(
                "point %s carries no demonstrated separation" % (label,)
            )
            continue
        margin = demonstrated_margin_db(point)
        if not margin_meets_requirement(margin, float(required)):
            margin_findings.append(
                "point %s: separation %.3f dB is below the required %.3f dB"
                % (label, margin, float(required))
            )
    gaps = coverage_gaps(bands, package.get("spectrum_span_hz")) if bands else ()
    if not bands:
        gaps = (validate_frequency_band(package.get("spectrum_span_hz")),)
    state = approval_state(package)
    approval_findings = []
    if state != "approved":
        approval_findings.append(
            "the interference critical point list is %s by the customer" % (state,)
        )
    elif not package.get("approving_customer"):
        approval_findings.append(
            "the approval carries no approving customer on record"
        )
    return {
        "candidate_points": candidates,
        "selection_findings": sorted(set(selection_findings)),
        "record_findings": sorted(set(record_findings)),
        "margin_findings": sorted(set(margin_findings)),
        "coverage_gaps_hz": gaps,
        "approval_state": state,
        "approval_findings": sorted(set(approval_findings)),
        "compliant": not selection_findings
        and not record_findings
        and not margin_findings
        and not gaps
        and not approval_findings,
    }

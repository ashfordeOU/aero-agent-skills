"""Part placement and build orientation for powder-bed additive manufacturing.

Anchor: ECSS-Q-ST-70-80 part clauses covering how a part is placed and oriented
on the build platform, taking the resulting material properties and the
residual stress of the build into account. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Rotate the part's surface normals and its critical axis into the machine
   frame for each candidate orientation (in-plane rotation, then tilt).
2. Measure the down-facing area that the candidate leaves below the
   self-supporting angle, separating a surface the design marked critical from
   ordinary down-facing area.
3. Measure the build height the candidate produces and the bonded span it
   presents to the plate, and form a residual-stress index from the two.
4. Measure the angle between the critical loading axis and the build direction,
   because the weakest direction of the material is the build direction.
5. Measure the skew of the part's long in-plane axis against the recoater blade
   line, because a long edge parallel to the blade is what the blade strikes.
6. Reject candidates that break a hard constraint, score the survivors on
   support area, height and residual stress, and return the best one with every
   finding named.
"""

import math

__all__ = [
    "ANGLE_TOLERANCE_DEG",
    "DEFAULT_SELF_SUPPORT_ANGLE_DEG",
    "validate_bbox",
    "validate_orientation",
    "unit_vector",
    "rotate_vector",
    "oriented_extents",
    "build_height_mm",
    "bonded_span_mm",
    "facet_inclination_deg",
    "unsupported_facets",
    "unsupported_area_mm2",
    "critical_axis_angle_deg",
    "residual_stress_index",
    "long_axis_deg",
    "blade_skew_deg",
    "evaluate_candidate",
    "score_candidate",
    "select_orientation",
    "assess_placement",
]

# Angles come out of trigonometry, so a facet sitting exactly on the
# self-supporting angle can read a few units in the last place below it. The
# comparison absorbs that; the angle requirement itself is never relaxed.
ANGLE_TOLERANCE_DEG = 1e-9

# Below this inclination to the plate a down-facing surface is not
# self-supporting in a typical laser powder-bed process.
DEFAULT_SELF_SUPPORT_ANGLE_DEG = 45.0


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(label, value):
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_bbox(bbox_mm):
    """Return the validated part bounding box (dx, dy, dz) in millimetres."""
    if not isinstance(bbox_mm, (list, tuple)) or len(bbox_mm) != 3:
        raise ValueError("bbox_mm must be a (dx, dy, dz) triple in millimetres")
    return tuple(_positive("bbox axis %d" % i, v) for i, v in enumerate(bbox_mm))


def validate_orientation(candidate):
    """Return the validated (id, tilt_deg, rotation_deg) of a candidate."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    identifier = candidate.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("candidate id must be a non-empty string")
    tilt = _finite("candidate %s tilt_deg" % identifier, candidate.get("tilt_deg", 0.0))
    rotation = _finite("candidate %s rotation_deg" % identifier,
                       candidate.get("rotation_deg", 0.0))
    if tilt < 0.0 or tilt > 180.0:
        raise ValueError("candidate %s tilt_deg must sit in [0, 180]" % identifier)
    return (identifier, tilt, rotation)


def unit_vector(vector, label="vector"):
    """Return the normalised form of a three-component vector."""
    if not isinstance(vector, (list, tuple)) or len(vector) != 3:
        raise ValueError("%s must be a three-component vector" % label)
    components = [_finite("%s component %d" % (label, i), v) for i, v in enumerate(vector)]
    norm = math.sqrt(sum(c * c for c in components))
    if norm <= 0.0:
        raise ValueError("%s must have non-zero length" % label)
    return tuple(c / norm for c in components)


def rotate_vector(vector, tilt_deg, rotation_deg):
    """Rotate a vector into the machine frame: in-plane rotation, then tilt."""
    x, y, z = unit_vector(vector)
    r = math.radians(_finite("rotation_deg", rotation_deg))
    t = math.radians(_finite("tilt_deg", tilt_deg))
    xr = x * math.cos(r) - y * math.sin(r)
    yr = x * math.sin(r) + y * math.cos(r)
    zr = z
    yt = yr * math.cos(t) - zr * math.sin(t)
    zt = yr * math.sin(t) + zr * math.cos(t)
    return (xr, yt, zt)


def oriented_extents(bbox_mm, tilt_deg, rotation_deg):
    """Return the axis-aligned extents of the part in the machine frame."""
    dx, dy, dz = validate_bbox(bbox_mm)
    r = math.radians(_finite("rotation_deg", rotation_deg))
    t = math.radians(_finite("tilt_deg", tilt_deg))
    ex = dx * abs(math.cos(r)) + dy * abs(math.sin(r))
    ey_plane = dx * abs(math.sin(r)) + dy * abs(math.cos(r))
    ey = ey_plane * abs(math.cos(t)) + dz * abs(math.sin(t))
    ez = ey_plane * abs(math.sin(t)) + dz * abs(math.cos(t))
    return (ex, ey, ez)


def build_height_mm(bbox_mm, tilt_deg, rotation_deg):
    """Return the height the part occupies in the build direction."""
    return oriented_extents(bbox_mm, tilt_deg, rotation_deg)[2]


def bonded_span_mm(bbox_mm, tilt_deg, rotation_deg):
    """Return the longest in-plane extent the part presents to the plate."""
    ex, ey, _ = oriented_extents(bbox_mm, tilt_deg, rotation_deg)
    return max(ex, ey)


def facet_inclination_deg(normal, tilt_deg, rotation_deg):
    """Return the angle in degrees between a facet and the build plate."""
    _, _, nz = rotate_vector(normal, tilt_deg, rotation_deg)
    return math.degrees(math.acos(min(1.0, abs(nz))))


def unsupported_facets(facets, tilt_deg, rotation_deg,
                       self_support_angle_deg=DEFAULT_SELF_SUPPORT_ANGLE_DEG):
    """Return the down-facing facets that fall below the self-supporting angle."""
    threshold = _finite("self_support_angle_deg", self_support_angle_deg)
    if threshold < 0.0 or threshold > 90.0:
        raise ValueError("self_support_angle_deg must sit in [0, 90]")
    if not isinstance(facets, (list, tuple)) or not facets:
        raise ValueError("facets must be a non-empty sequence")
    found = []
    for index, facet in enumerate(facets):
        if not isinstance(facet, dict) or "normal" not in facet or "area_mm2" not in facet:
            raise ValueError("facet %d needs 'normal' and 'area_mm2'" % index)
        area = _positive("facet %d area_mm2" % index, facet["area_mm2"])
        rotated = rotate_vector(facet["normal"], tilt_deg, rotation_deg)
        if rotated[2] >= 0.0:
            continue
        inclination = math.degrees(math.acos(min(1.0, abs(rotated[2]))))
        if inclination < threshold and not math.isclose(
            inclination, threshold, rel_tol=0.0, abs_tol=ANGLE_TOLERANCE_DEG
        ):
            found.append({
                "facet": facet.get("id", "facet-%d" % index),
                "area_mm2": area,
                "inclination_deg": inclination,
                "critical": bool(facet.get("critical", False)),
            })
    return found


def unsupported_area_mm2(facets, tilt_deg, rotation_deg,
                         self_support_angle_deg=DEFAULT_SELF_SUPPORT_ANGLE_DEG):
    """Return the total down-facing area needing support for an orientation."""
    return sum(record["area_mm2"] for record in
               unsupported_facets(facets, tilt_deg, rotation_deg, self_support_angle_deg))


def critical_axis_angle_deg(axis, tilt_deg, rotation_deg):
    """Return the angle in degrees between a part axis and the build direction."""
    rotated = rotate_vector(axis, tilt_deg, rotation_deg)
    return math.degrees(math.acos(max(-1.0, min(1.0, rotated[2]))))


def residual_stress_index(span_mm, height_mm, reference_span_mm, reference_height_mm):
    """Return a dimensionless residual-stress proxy for a placed part."""
    span = _positive("span_mm", span_mm)
    height = _positive("height_mm", height_mm)
    reference_span = _positive("reference_span_mm", reference_span_mm)
    reference_height = _positive("reference_height_mm", reference_height_mm)
    return (span / reference_span) * (1.0 + height / reference_height)


def long_axis_deg(bbox_mm, rotation_deg):
    """Return the machine-frame direction of the part's long in-plane axis."""
    dx, dy, _ = validate_bbox(bbox_mm)
    rotation = _finite("rotation_deg", rotation_deg)
    return rotation if dx >= dy else rotation + 90.0


def blade_skew_deg(part_axis_deg, blade_axis_deg):
    """Return the acute angle between a part axis and the recoater blade line."""
    delta = abs(_finite("part_axis_deg", part_axis_deg)
                - _finite("blade_axis_deg", blade_axis_deg)) % 180.0
    return min(delta, 180.0 - delta)


def evaluate_candidate(candidate, spec):
    """Evaluate one candidate orientation and return its record."""
    identifier, tilt, rotation = validate_orientation(candidate)
    bbox = validate_bbox(spec["bbox_mm"])
    self_support = spec.get("self_support_angle_deg", DEFAULT_SELF_SUPPORT_ANGLE_DEG)
    unsupported = unsupported_facets(spec["facets"], tilt, rotation, self_support)
    height = build_height_mm(bbox, tilt, rotation)
    span = bonded_span_mm(bbox, tilt, rotation)
    axis_angle = critical_axis_angle_deg(spec["critical_axis"], tilt, rotation)
    blade_axis = _finite("recoater_travel_deg", spec.get("recoater_travel_deg", 0.0)) + 90.0
    skew = blade_skew_deg(long_axis_deg(bbox, rotation), blade_axis)
    return {
        "id": identifier,
        "tilt_deg": tilt,
        "rotation_deg": rotation,
        "build_height_mm": height,
        "bonded_span_mm": span,
        "support_area_mm2": sum(record["area_mm2"] for record in unsupported),
        "critical_support_area_mm2": sum(
            record["area_mm2"] for record in unsupported if record["critical"]
        ),
        "unsupported_facets": unsupported,
        "critical_axis_angle_deg": axis_angle,
        "blade_skew_deg": skew,
        "residual_stress_index": residual_stress_index(
            span, height,
            _positive("reference_span_mm", spec.get("reference_span_mm", 100.0)),
            _positive("reference_height_mm", spec.get("reference_height_mm", 100.0)),
        ),
    }


def score_candidate(record, spec):
    """Return the weighted penalty score of a candidate; lower is better."""
    weights = spec.get("weights", {})
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping")
    w_support = _finite("weights['support']", weights.get("support", 1.0))
    w_height = _finite("weights['height']", weights.get("height", 1.0))
    w_stress = _finite("weights['stress']", weights.get("stress", 1.0))
    for label, value in (("support", w_support), ("height", w_height), ("stress", w_stress)):
        if value < 0.0:
            raise ValueError("weights['%s'] cannot be negative" % label)
    reference_area = _positive("reference_area_mm2", spec.get("reference_area_mm2", 1000.0))
    reference_height = _positive("reference_height_mm", spec.get("reference_height_mm", 100.0))
    return (
        w_support * record["support_area_mm2"] / reference_area
        + w_height * record["build_height_mm"] / reference_height
        + w_stress * record["residual_stress_index"]
    )


def _hard_violations(record, spec):
    """Return the hard-constraint breaks of one candidate record."""
    violations = []
    envelope_height = spec.get("envelope_height_mm")
    if envelope_height is not None:
        limit = _positive("envelope_height_mm", envelope_height)
        if record["build_height_mm"] > limit and not math.isclose(
            record["build_height_mm"], limit, rel_tol=1e-9, abs_tol=0.0
        ):
            violations.append("build height %.2f mm exceeds the %.2f mm envelope"
                              % (record["build_height_mm"], limit))
    minimum_axis = _finite("min_critical_axis_angle_deg",
                           spec.get("min_critical_axis_angle_deg", 0.0))
    if record["critical_axis_angle_deg"] < minimum_axis and not math.isclose(
        record["critical_axis_angle_deg"], minimum_axis,
        rel_tol=0.0, abs_tol=ANGLE_TOLERANCE_DEG
    ):
        violations.append(
            "critical axis sits %.2f deg from the build direction, below the %.2f deg required"
            % (record["critical_axis_angle_deg"], minimum_axis)
        )
    if record["critical_support_area_mm2"] > 0.0:
        violations.append(
            "%.1f mm2 of support lands on a surface the design marked critical"
            % record["critical_support_area_mm2"]
        )
    return violations


def select_orientation(records, spec):
    """Return the best feasible candidate record and the rejected ones."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    feasible = []
    rejected = []
    for record in records:
        violations = _hard_violations(record, spec)
        if violations:
            rejected.append({"id": record["id"], "violations": violations})
        else:
            feasible.append(record)
    if not feasible:
        return (None, rejected)
    best = feasible[0]
    best_score = score_candidate(best, spec)
    for record in feasible[1:]:
        score = score_candidate(record, spec)
        if math.isclose(score, best_score, rel_tol=1e-12, abs_tol=0.0):
            if record["support_area_mm2"] < best["support_area_mm2"]:
                best, best_score = record, score
            elif math.isclose(
                record["support_area_mm2"], best["support_area_mm2"],
                rel_tol=1e-12, abs_tol=0.0
            ) and record["id"] < best["id"]:
                best, best_score = record, score
        elif score < best_score:
            best, best_score = record, score
    return (best, rejected)


def assess_placement(spec):
    """Run the full part placement and orientation assessment.

    spec keys: bbox_mm, facets, candidates, critical_axis, optional
    envelope_height_mm, min_critical_axis_angle_deg, self_support_angle_deg,
    recoater_travel_deg, min_blade_skew_deg, weights and reference values.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("bbox_mm", "facets", "candidates", "critical_axis"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    candidates = spec["candidates"]
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("spec['candidates'] must be a non-empty sequence")
    records = []
    seen = set()
    for candidate in candidates:
        record = evaluate_candidate(candidate, spec)
        if record["id"] in seen:
            raise ValueError("duplicate candidate id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    selected, rejected = select_orientation(records, spec)
    findings = []
    if selected is not None:
        minimum_skew = _finite("min_blade_skew_deg", spec.get("min_blade_skew_deg", 0.0))
        if selected["blade_skew_deg"] < minimum_skew and not math.isclose(
            selected["blade_skew_deg"], minimum_skew, rel_tol=0.0, abs_tol=ANGLE_TOLERANCE_DEG
        ):
            findings.append(
                "long axis sits %.2f deg from the recoater blade line, below the %.2f deg "
                "skew that keeps the blade off a full-length edge"
                % (selected["blade_skew_deg"], minimum_skew)
            )
        if selected["support_area_mm2"] > 0.0:
            findings.append(
                "%.1f mm2 of down-facing area needs support in the selected orientation"
                % selected["support_area_mm2"]
            )
    else:
        findings.append("no candidate orientation satisfies the hard constraints")
    return {
        "records": records,
        "selected": selected,
        "rejected": rejected,
        "findings": findings,
        "placeable": selected is not None,
    }

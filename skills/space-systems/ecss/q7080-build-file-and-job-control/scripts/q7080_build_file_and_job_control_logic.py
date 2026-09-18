"""Build-file and job control for a powder-bed additive-manufacturing build.

Anchor: ECSS-Q-ST-70-80 process clauses covering control of the build file and
the build job: version binding, nesting on the platform and the orientation
each part is built at. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the build-file identity: a version string, a digest of the file
   that was actually sliced, and a parameter set drawn from the approved list.
2. Bind every nested part to the released design index. A part number absent
   from the index, or present at another revision, is a configuration break and
   not a paperwork note.
3. Grade the nest geometrically: each part's in-plane footprint after its
   platform rotation has to sit inside the usable platform with its edge
   margin, no two footprints may come closer than the minimum clearance, and
   the tallest part has to fit the vertical envelope.
4. Grade the orientation of every part against the approved orientation for its
   part number, within the stated angular tolerance, treating an unrecorded
   orientation as a break rather than as nominal.
5. Return a release-or-hold verdict with every finding named against the part
   that produced it.
"""

import math

__all__ = [
    "ANGLE_TOLERANCE",
    "DIGEST_LENGTH",
    "validate_envelope",
    "validate_part",
    "footprint_extent",
    "footprint_box",
    "platform_violation",
    "clearance_mm",
    "nest_clearance_findings",
    "angle_difference_deg",
    "check_build_file_identity",
    "check_revision_binding",
    "check_orientation",
    "assess_build_job",
]

# Footprints come out of a rotation, so two parts placed exactly at the minimum
# clearance can read a few units in the last place below it. The comparison
# absorbs that; the clearance requirement itself is never relaxed.
GEOMETRY_TOLERANCE = 1e-9

# Orientation angles are recorded to a stated tolerance; an angle exactly on
# that tolerance is inside it.
ANGLE_TOLERANCE = 1e-9

# Digest of the sliced build file, hexadecimal.
DIGEST_LENGTH = 64

_HEX = set("0123456789abcdefABCDEF")


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_envelope(envelope):
    """Return the validated usable build envelope (x, y, z) in millimetres."""
    if not isinstance(envelope, (list, tuple)) or len(envelope) != 3:
        raise ValueError("envelope must be an (x, y, z) triple in millimetres")
    return tuple(_positive("envelope axis %d" % i, v) for i, v in enumerate(envelope))


def validate_part(part):
    """Return a validated nested-part record."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("id", "part_number", "design_revision", "bbox_mm", "position_mm"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    identifier = part["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("part id must be a non-empty string")
    number = part["part_number"]
    if not isinstance(number, str) or not number.strip():
        raise ValueError("part %s part_number must be a non-empty string" % identifier)
    revision = part["design_revision"]
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("part %s design_revision must be a non-empty string" % identifier)
    bbox = part["bbox_mm"]
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 3:
        raise ValueError("part %s bbox_mm must be a (dx, dy, dz) triple" % identifier)
    bbox = tuple(_positive("part %s bbox axis %d" % (identifier, i), v)
                 for i, v in enumerate(bbox))
    position = part["position_mm"]
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        raise ValueError("part %s position_mm must be an (x, y) pair" % identifier)
    position = tuple(_finite("part %s position axis %d" % (identifier, i), v)
                     for i, v in enumerate(position))
    rotation = _finite("part %s platform_rotation_deg" % identifier,
                       part.get("platform_rotation_deg", 0.0))
    return {
        "id": identifier,
        "part_number": number,
        "design_revision": revision,
        "bbox_mm": bbox,
        "position_mm": position,
        "platform_rotation_deg": rotation,
        "orientation_deg": part.get("orientation_deg"),
    }


def footprint_extent(bbox_mm, platform_rotation_deg):
    """Return the axis-aligned (width, depth) of a part after platform rotation."""
    if not isinstance(bbox_mm, (list, tuple)) or len(bbox_mm) != 3:
        raise ValueError("bbox_mm must be a (dx, dy, dz) triple")
    dx = _positive("bbox dx", bbox_mm[0])
    dy = _positive("bbox dy", bbox_mm[1])
    _positive("bbox dz", bbox_mm[2])
    angle = math.radians(_finite("platform_rotation_deg", platform_rotation_deg))
    cos_a = abs(math.cos(angle))
    sin_a = abs(math.sin(angle))
    return (dx * cos_a + dy * sin_a, dx * sin_a + dy * cos_a)


def footprint_box(part):
    """Return the (xmin, xmax, ymin, ymax) footprint of a validated part."""
    record = validate_part(part)
    width, depth = footprint_extent(record["bbox_mm"], record["platform_rotation_deg"])
    cx, cy = record["position_mm"]
    return (cx - width / 2.0, cx + width / 2.0, cy - depth / 2.0, cy + depth / 2.0)


def platform_violation(part, envelope, edge_margin_mm=0.0):
    """Return a finding when a part leaves the usable platform, else None."""
    size_x, size_y, size_z = validate_envelope(envelope)
    margin = _finite("edge_margin_mm", edge_margin_mm)
    if margin < 0.0:
        raise ValueError("edge_margin_mm cannot be negative")
    record = validate_part(part)
    xmin, xmax, ymin, ymax = footprint_box(part)
    if (xmin < margin - GEOMETRY_TOLERANCE or ymin < margin - GEOMETRY_TOLERANCE
            or xmax > size_x - margin + GEOMETRY_TOLERANCE
            or ymax > size_y - margin + GEOMETRY_TOLERANCE):
        return {"part": record["id"], "reason": "outside-platform",
                "footprint": (xmin, xmax, ymin, ymax)}
    if record["bbox_mm"][2] > size_z + GEOMETRY_TOLERANCE:
        return {"part": record["id"], "reason": "above-vertical-envelope",
                "height_mm": record["bbox_mm"][2]}
    return None


def clearance_mm(part_a, part_b):
    """Return the in-plane gap between two footprints; negative when they overlap."""
    ax0, ax1, ay0, ay1 = footprint_box(part_a)
    bx0, bx1, by0, by1 = footprint_box(part_b)
    gap_x = max(bx0 - ax1, ax0 - bx1)
    gap_y = max(by0 - ay1, ay0 - by1)
    if gap_x > 0.0 and gap_y > 0.0:
        return math.hypot(gap_x, gap_y)
    if gap_x > 0.0:
        return gap_x
    if gap_y > 0.0:
        return gap_y
    return max(gap_x, gap_y)


def nest_clearance_findings(parts, minimum_clearance_mm):
    """Return a finding for every pair closer than the minimum clearance."""
    minimum = _finite("minimum_clearance_mm", minimum_clearance_mm)
    if minimum < 0.0:
        raise ValueError("minimum_clearance_mm cannot be negative")
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a sequence")
    findings = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            gap = clearance_mm(parts[i], parts[j])
            if gap < minimum and not math.isclose(
                gap, minimum, rel_tol=0.0, abs_tol=GEOMETRY_TOLERANCE
            ):
                findings.append({
                    "parts": (validate_part(parts[i])["id"], validate_part(parts[j])["id"]),
                    "clearance_mm": gap,
                    "minimum_mm": minimum,
                    "reason": "overlap" if gap < 0.0 else "below-minimum-clearance",
                })
    return findings


def angle_difference_deg(recorded, approved):
    """Return the smallest absolute difference between two angles in degrees."""
    a = _finite("recorded angle", recorded)
    b = _finite("approved angle", approved)
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta)


def check_build_file_identity(job, approved_parameter_sets):
    """Return findings on the build-file version, digest and parameter set."""
    if not isinstance(job, dict):
        raise ValueError("job must be a mapping")
    if not isinstance(approved_parameter_sets, (list, tuple, set)) or not approved_parameter_sets:
        raise ValueError("approved_parameter_sets must be a non-empty sequence")
    findings = []
    version = job.get("build_file_version")
    if not isinstance(version, str) or not version.strip():
        findings.append({"reason": "build-file-version-missing"})
    digest = job.get("build_file_digest")
    if not isinstance(digest, str) or len(digest) != DIGEST_LENGTH or any(
        c not in _HEX for c in digest
    ):
        findings.append({"reason": "build-file-digest-missing-or-malformed"})
    parameter_set = job.get("parameter_set_id")
    if parameter_set not in set(approved_parameter_sets):
        findings.append({"reason": "parameter-set-not-approved", "value": parameter_set})
    return findings


def check_revision_binding(parts, released_index):
    """Return findings where a nested part does not match the released index."""
    if not isinstance(released_index, dict) or not released_index:
        raise ValueError("released_index must be a non-empty mapping")
    findings = []
    for part in parts:
        record = validate_part(part)
        number = record["part_number"]
        if number not in released_index:
            findings.append({"part": record["id"], "part_number": number,
                             "reason": "not-in-released-index"})
            continue
        released = released_index[number]
        if record["design_revision"] != released:
            findings.append({"part": record["id"], "part_number": number,
                             "reason": "revision-mismatch",
                             "nested": record["design_revision"], "released": released})
    return findings


def check_orientation(parts, approved_orientations, tolerance_deg=1.0):
    """Return findings where a part's orientation is unrecorded or off-approved."""
    if not isinstance(approved_orientations, dict) or not approved_orientations:
        raise ValueError("approved_orientations must be a non-empty mapping")
    tolerance = _finite("tolerance_deg", tolerance_deg)
    if tolerance < 0.0:
        raise ValueError("tolerance_deg cannot be negative")
    findings = []
    for part in parts:
        record = validate_part(part)
        number = record["part_number"]
        if number not in approved_orientations:
            findings.append({"part": record["id"], "reason": "no-approved-orientation"})
            continue
        recorded = record["orientation_deg"]
        if not isinstance(recorded, (list, tuple)) or len(recorded) != 2:
            findings.append({"part": record["id"], "reason": "orientation-unrecorded"})
            continue
        approved = approved_orientations[number]
        if not isinstance(approved, (list, tuple)) or len(approved) != 2:
            raise ValueError(
                "approved orientation for %s must be a (tilt, rotation) pair" % number
            )
        for axis, index in (("tilt", 0), ("rotation", 1)):
            delta = angle_difference_deg(recorded[index], approved[index])
            if delta > tolerance and not math.isclose(
                delta, tolerance, rel_tol=0.0, abs_tol=ANGLE_TOLERANCE
            ):
                findings.append({"part": record["id"], "reason": "orientation-off-approved",
                                 "axis": axis, "delta_deg": delta, "tolerance_deg": tolerance})
    return findings


def assess_build_job(spec):
    """Run the full build-file and job control assessment.

    spec keys: job, parts, envelope_mm, released_index, approved_orientations,
    approved_parameter_sets, optional minimum_clearance_mm, edge_margin_mm,
    orientation_tolerance_deg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("job", "parts", "envelope_mm", "released_index",
                "approved_orientations", "approved_parameter_sets"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")
    seen = set()
    for part in parts:
        record = validate_part(part)
        if record["id"] in seen:
            raise ValueError("duplicate part id %r in the nest" % record["id"])
        seen.add(record["id"])
    envelope = validate_envelope(spec["envelope_mm"])
    findings = []
    findings.extend(check_build_file_identity(spec["job"], spec["approved_parameter_sets"]))
    findings.extend(check_revision_binding(parts, spec["released_index"]))
    for part in parts:
        violation = platform_violation(part, envelope, spec.get("edge_margin_mm", 0.0))
        if violation is not None:
            findings.append(violation)
    findings.extend(nest_clearance_findings(parts, spec.get("minimum_clearance_mm", 0.0)))
    findings.extend(check_orientation(parts, spec["approved_orientations"],
                                      spec.get("orientation_tolerance_deg", 1.0)))
    return {
        "verdict": "hold" if findings else "release",
        "part_count": len(parts),
        "envelope_mm": envelope,
        "findings": findings,
    }

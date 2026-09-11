#!/usr/bin/env python3
"""ECSS-E-ST-10-09C Annex A CSD DRD generation and validation logic
(paraphrase, not verbatim copy of the standard).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS coordinate-systems standard requires a Coordinate Systems Document
(CSD) as a formal DRD deliverable. The CSD must define every coordinate
frame (inertial, body-fixed, orbital, sensor, etc.) with a unique
identifier, origin, axis directions, and body attachment; record each
frame-to-frame transformation as a rotation sequence and translation
vector; and populate parameter tables listing numeric geometric values
with units and the frame they reference. The document must satisfy an
Annex A completeness checklist: at minimum one inertial frame, one
body-fixed frame, at least one transformation, and a non-empty parameter
table must be present, and the title and issue number must be filled in.
This module implements frame validation, transformation validation,
parameter-table validation, DRD completeness checking, rotation-matrix
computation from Euler angles, orthonormality verification, frame
grouping by type, and a breadth-first transformation-path search.
"""

import math
from collections import deque

# Frame types recognised by ECSS-E-ST-10-09C
VALID_FRAME_TYPES = frozenset({
    "inertial", "body-fixed", "orbital", "sensor",
    "antenna", "solar-array", "instrument", "launch", "topocentric",
})

# Euler rotation sequences (intrinsic, right-to-left product convention)
VALID_ROTATION_SEQUENCES = frozenset({
    "ZYX", "ZXZ", "ZYZ", "XYZ", "XZX", "XZY",
    "YXZ", "YXY", "YZX", "YZY", "ZXY", "XYX",
})


# ---------------------------------------------------------------------------
# Frame validation
# ---------------------------------------------------------------------------

def validate_frame(frame):
    """Check one coordinate frame definition dict.

    Expected keys: frame_id (str), frame_type (str), origin (str),
    x_axis (str), y_axis (str), z_axis (str),
    body_attachment (str | None).
    Returns a list of error strings; an empty list means the frame is valid.
    Does not mutate the input dict.
    """
    errors = []
    if not frame.get("frame_id"):
        errors.append("frame_id is empty or missing")
    if frame.get("frame_type") not in VALID_FRAME_TYPES:
        errors.append(
            "frame_type %r is not a recognised frame type"
            % (frame.get("frame_type"),)
        )
    if not frame.get("origin"):
        errors.append("origin is not specified")
    if not frame.get("x_axis"):
        errors.append("x_axis is not specified")
    if not frame.get("y_axis"):
        errors.append("y_axis is not specified")
    if not frame.get("z_axis"):
        errors.append("z_axis is not specified")
    return errors


# ---------------------------------------------------------------------------
# Transformation validation
# ---------------------------------------------------------------------------

def validate_transformation(transform, frame_ids):
    """Check one frame-to-frame transformation dict.

    Expected keys: source_frame (str), target_frame (str),
    rotation_sequence (str), angles_deg (sequence of 3 floats),
    translation_m (sequence of 3 floats).
    frame_ids: set of already-defined frame identifiers.
    Returns a list of error strings; an empty list means the entry is valid.
    Does not mutate the input dict.
    """
    errors = []
    src = transform.get("source_frame", "")
    tgt = transform.get("target_frame", "")

    if not src:
        errors.append("source_frame is empty or missing")
    elif src not in frame_ids:
        errors.append("source_frame %r is not a defined frame" % (src,))

    if not tgt:
        errors.append("target_frame is empty or missing")
    elif tgt not in frame_ids:
        errors.append("target_frame %r is not a defined frame" % (tgt,))

    if src and tgt and src == tgt:
        errors.append(
            "source_frame and target_frame are identical (%r)" % (src,)
        )

    seq = transform.get("rotation_sequence", "")
    if seq not in VALID_ROTATION_SEQUENCES:
        errors.append("rotation_sequence %r is not recognised" % (seq,))

    angles = transform.get("angles_deg", ())
    if len(angles) != 3:
        errors.append(
            "angles_deg must have exactly 3 components (got %d)" % len(angles)
        )

    tvec = transform.get("translation_m", ())
    if len(tvec) != 3:
        errors.append(
            "translation_m must have exactly 3 components (got %d)" % len(tvec)
        )

    return errors


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

def validate_parameter(param, frame_ids):
    """Check one parameter-table entry dict.

    Expected keys: name (str), value (float), unit (str),
    frame_id (str | None).
    frame_ids: set of already-defined frame identifiers.
    Returns a list of error strings; an empty list means the entry is valid.
    Does not mutate the input dict.
    """
    errors = []
    name = param.get("name", "")
    if not name:
        errors.append("parameter name is empty or missing")
    if not param.get("unit"):
        errors.append("parameter %r has no unit" % (name,))
    fid = param.get("frame_id")
    if fid and fid not in frame_ids:
        errors.append(
            "parameter %r references unknown frame %r" % (name, fid)
        )
    return errors


# ---------------------------------------------------------------------------
# DRD completeness check
# ---------------------------------------------------------------------------

def check_drd_completeness(doc):
    """Verify the CSD document satisfies the Annex A DRD checklist.

    doc: {"title": str, "issue": str, "frames": [...],
          "transformations": [...], "parameters": [...]}
    Returns a list of finding strings; an empty list means the document
    satisfies the completeness checklist.
    Does not mutate doc.
    """
    findings = []
    if not doc.get("title"):
        findings.append("DRD: document title is missing")
    if not doc.get("issue"):
        findings.append("DRD: issue number is missing")

    frame_types = {f.get("frame_type") for f in doc.get("frames", [])}
    if "inertial" not in frame_types:
        findings.append("DRD: no inertial frame is defined")
    if "body-fixed" not in frame_types:
        findings.append("DRD: no body-fixed frame is defined")
    if not doc.get("transformations"):
        findings.append("DRD: no frame-to-frame transformations are defined")
    if not doc.get("parameters"):
        findings.append("DRD: parameter table is empty")

    return findings


# ---------------------------------------------------------------------------
# Full CSD validation
# ---------------------------------------------------------------------------

def validate_csd(doc):
    """Run all validation checks on a CSD document dict.

    Returns a dict with keys "frames", "transformations", "parameters",
    "drd", each containing a list of finding strings. The document is
    compliant when every list is empty.
    Does not mutate doc.
    """
    frame_findings = []
    seen_ids = set()
    frame_ids = set()
    for frame in doc.get("frames", []):
        fid = frame.get("frame_id", "")
        if fid in seen_ids:
            frame_findings.append("DUPLICATE_FRAME_ID: %r" % (fid,))
        seen_ids.add(fid)
        frame_ids.add(fid)
        for err in validate_frame(frame):
            frame_findings.append(
                "FRAME %r: %s" % (fid or "<empty>", err)
            )

    transform_findings = []
    seen_pairs = set()
    for t in doc.get("transformations", []):
        pair = (t.get("source_frame", ""), t.get("target_frame", ""))
        if pair in seen_pairs:
            transform_findings.append(
                "DUPLICATE_TRANSFORM: %s -> %s" % pair
            )
        seen_pairs.add(pair)
        for err in validate_transformation(t, frame_ids):
            transform_findings.append(
                "TRANSFORM %s->%s: %s" % (pair[0], pair[1], err)
            )

    param_findings = []
    seen_param_names = set()
    for p in doc.get("parameters", []):
        pname = p.get("name", "")
        if pname in seen_param_names:
            param_findings.append("DUPLICATE_PARAM: %r" % (pname,))
        seen_param_names.add(pname)
        for err in validate_parameter(p, frame_ids):
            param_findings.append(
                "PARAM %r: %s" % (pname or "<empty>", err)
            )

    return {
        "frames": frame_findings,
        "transformations": transform_findings,
        "parameters": param_findings,
        "drd": check_drd_completeness(doc),
    }


def is_compliant(findings):
    """True when every findings list in the validate_csd result is empty."""
    return all(len(v) == 0 for v in findings.values())


# ---------------------------------------------------------------------------
# Rotation matrix from Euler angles
# ---------------------------------------------------------------------------

def _rx(a):
    """Elementary rotation matrix about X axis (angle in radians)."""
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def _ry(a):
    """Elementary rotation matrix about Y axis (angle in radians)."""
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _rz(a):
    """Elementary rotation matrix about Z axis (angle in radians)."""
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _mat3_mul(a, b):
    """3x3 matrix multiply (row-major lists)."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def build_rotation_matrix(sequence, angles_deg):
    """Build a 3x3 direction cosine matrix from an Euler rotation sequence.

    sequence: one of VALID_ROTATION_SEQUENCES (e.g. 'ZYX').
    angles_deg: iterable of exactly 3 rotation angles in degrees (applied
    left-to-right: the first character of sequence is the first rotation).
    Returns a 3x3 list-of-lists (row-major).
    Raises ValueError for an unrecognised sequence or wrong angle count.
    """
    if sequence not in VALID_ROTATION_SEQUENCES:
        raise ValueError("unrecognised rotation sequence %r" % (sequence,))
    angles = list(angles_deg)
    if len(angles) != 3:
        raise ValueError("angles_deg must have exactly 3 elements")

    _elem = {"X": _rx, "Y": _ry, "Z": _rz}
    mats = [_elem[ax](math.radians(a)) for ax, a in zip(sequence, angles)]
    result = mats[0]
    for m in mats[1:]:
        result = _mat3_mul(m, result)
    return result


def check_orthonormality(matrix, tol=1e-9):
    """Return True if the 3x3 matrix is a proper rotation matrix.

    Checks that R^T R = I (columns orthonormal) and det(R) = +1.
    """
    r = matrix
    for i in range(3):
        for j in range(3):
            dot = sum(r[k][i] * r[k][j] for k in range(3))
            expected = 1.0 if i == j else 0.0
            if abs(dot - expected) > tol:
                return False
    det = (
        r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
        - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
        + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0])
    )
    return abs(det - 1.0) <= tol


# ---------------------------------------------------------------------------
# Frame grouping by type
# ---------------------------------------------------------------------------

def categorize_frames(frames):
    """Group frame definitions by their frame_type.

    frames: iterable of frame dicts (each with "frame_id" and "frame_type").
    Returns a dict mapping frame_type -> list of frame_ids.
    Does not mutate the input.
    """
    groups = {}
    for f in frames:
        ftype = f.get("frame_type", "")
        fid = f.get("frame_id", "")
        groups.setdefault(ftype, []).append(fid)
    return groups


# ---------------------------------------------------------------------------
# Transformation path search
# ---------------------------------------------------------------------------

def find_transformation_path(source, target, transforms, max_hops=10):
    """Search for a chain of defined transformations from source to target.

    Transformations are bidirectional (each defined transform is invertible
    in the reverse direction). Returns a list of (src, tgt) pairs that form
    the path, or an empty list if no path exists or if source == target.
    """
    if source == target:
        return []

    adj = {}
    for t in transforms:
        s = t.get("source_frame", "")
        g = t.get("target_frame", "")
        adj.setdefault(s, []).append(g)
        adj.setdefault(g, []).append(s)

    queue = deque([(source, [source])])
    visited = {source}
    while queue:
        node, path = queue.popleft()
        if len(path) > max_hops + 1:
            break
        for neighbor in adj.get(node, []):
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == target:
                return list(zip(new_path[:-1], new_path[1:]))
            visited.add(neighbor)
            queue.append((neighbor, new_path))
    return []

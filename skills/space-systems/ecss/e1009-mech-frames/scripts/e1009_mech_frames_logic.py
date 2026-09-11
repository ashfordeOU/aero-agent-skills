"""
Mechanical body frame definition and alignment data checker.
Implements ECSS-E-ST-10-09C §5.4.5 procedures (paraphrased).
Stdlib only. Offline, deterministic.
"""

FRAME_TYPES = {"spacecraft", "equipment", "sensor"}
REQUIRED_FRAME_FIELDS = {"name", "type", "parent", "origin", "dcm"}
REQUIRED_ALIGNMENT_FIELDS = {"frame_name", "nominal_dcm", "measurement_status"}
VALID_MEASUREMENT_STATUSES = {"measured", "nominal", "estimated"}
ORTHO_TOL = 1e-6


class FrameDefinitionError(ValueError):
    pass


class AlignmentDataError(ValueError):
    pass


# --- matrix helpers (3x3, no numpy) ---

def _mat_mul(a, b):
    result = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                result[i][j] += a[i][k] * b[k][j]
    return result


def _mat_transpose(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _identity3():
    return [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]


def _mat_max_diff(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


def _det3(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


# --- DCM validation ---

def validate_dcm(dcm, label="DCM"):
    """
    Verify that dcm is a proper 3x3 rotation matrix.
    Returns a list of error strings; empty list means the matrix passes.
    """
    errors = []
    if (
        not isinstance(dcm, (list, tuple))
        or len(dcm) != 3
        or any(not isinstance(row, (list, tuple)) or len(row) != 3 for row in dcm)
    ):
        errors.append(f"{label} must be a 3x3 list of lists")
        return errors
    rrt = _mat_mul(dcm, _mat_transpose(dcm))
    diff = _mat_max_diff(rrt, _identity3())
    if diff > ORTHO_TOL:
        errors.append(f"{label} not orthogonal: max|R·Rᵀ - I| = {diff:.3e}")
    det = _det3(dcm)
    if abs(det - 1.0) > ORTHO_TOL:
        errors.append(f"{label} determinant is {det:.6f}, expected +1.0 (proper rotation)")
    return errors


# --- frame field checks ---

def check_frame_fields(frame):
    """Return list of missing required field names."""
    return [f for f in sorted(REQUIRED_FRAME_FIELDS) if f not in frame]


def check_frame_type(frame):
    ft = frame.get("type")
    if ft not in FRAME_TYPES:
        return [f"Unknown frame type '{ft}'. Must be one of: {sorted(FRAME_TYPES)}"]
    return []


def check_frame_parent(frame, registry):
    """
    Spacecraft frames must have parent=None.
    Equipment/sensor frames must name an existing parent in the registry.
    """
    errors = []
    ft = frame.get("type")
    parent = frame.get("parent")
    name = frame.get("name", "<unnamed>")
    if ft == "spacecraft":
        if parent is not None:
            errors.append(f"Spacecraft body frame '{name}' must have parent=None")
    elif ft in {"equipment", "sensor"}:
        if parent is None:
            errors.append(f"Frame '{name}' of type '{ft}' must specify a parent frame")
        elif parent not in registry:
            errors.append(f"Frame '{name}': parent '{parent}' not found in registry")
    return errors


def check_origin(frame):
    origin = frame.get("origin")
    if origin is None:
        return []
    if not isinstance(origin, (list, tuple)) or len(origin) != 3:
        return [f"Frame '{frame.get('name', '<unnamed>')}': origin must be a 3-element vector [x, y, z]"]
    if not all(isinstance(v, (int, float)) for v in origin):
        return [f"Frame '{frame.get('name', '<unnamed>')}': origin elements must be numeric"]
    return []


def detect_parent_cycle(frame_name, registry):
    """Walk the parent chain and return an error if a cycle is detected."""
    visited = []
    current = frame_name
    while current is not None:
        if current in visited:
            chain = " -> ".join(visited + [current])
            return [f"Cyclic parent reference detected: {chain}"]
        visited.append(current)
        frm = registry.get(current)
        if frm is None:
            break
        current = frm.get("parent")
    return []


# --- frame validation ---

def validate_frame(frame, registry):
    """
    Validate a single frame definition against the full frame registry.

    registry: dict mapping frame name -> frame dict for ALL frames in the set.
    Returns {"name": str, "errors": [str], "warnings": [str]}.
    """
    errors = []
    warnings = []
    name = frame.get("name", "<unnamed>")

    missing = check_frame_fields(frame)
    if missing:
        errors.append(f"Missing required fields: {missing}")

    errors += check_frame_type(frame)
    errors += check_frame_parent(frame, registry)
    errors += check_origin(frame)

    dcm = frame.get("dcm")
    if dcm is not None:
        errors += validate_dcm(dcm, label=f"Frame '{name}' DCM")
    elif "dcm" not in (frame.keys() if isinstance(frame, dict) else []):
        warnings.append("DCM field absent; orthogonality cannot be verified")

    errors += detect_parent_cycle(name, registry)

    return {"name": name, "errors": errors, "warnings": warnings}


# --- alignment field checks ---

def check_alignment_fields(alignment):
    return [f for f in sorted(REQUIRED_ALIGNMENT_FIELDS) if f not in alignment]


def check_measurement_status(alignment):
    status = alignment.get("measurement_status")
    if status not in VALID_MEASUREMENT_STATUSES:
        return [
            f"Invalid measurement_status '{status}'. "
            f"Must be one of: {sorted(VALID_MEASUREMENT_STATUSES)}"
        ]
    return []


def check_alignment_frame_ref(alignment, registry):
    ref = alignment.get("frame_name")
    if ref and ref not in registry:
        return [f"Alignment references unknown frame '{ref}'"]
    return []


# --- alignment validation ---

def validate_alignment(alignment, registry):
    """
    Validate a single alignment data record against the frame registry.
    Returns {"frame_name": str, "errors": [str], "warnings": [str]}.
    """
    errors = []
    warnings = []
    ref = alignment.get("frame_name", "<unknown>")

    missing = check_alignment_fields(alignment)
    if missing:
        errors.append(f"Missing required alignment fields: {missing}")

    errors += check_measurement_status(alignment)
    errors += check_alignment_frame_ref(alignment, registry)

    nominal = alignment.get("nominal_dcm")
    if nominal is not None:
        errors += validate_dcm(nominal, label=f"Alignment '{ref}' nominal_dcm")

    measured = alignment.get("measured_dcm")
    if measured is not None:
        errors += validate_dcm(measured, label=f"Alignment '{ref}' measured_dcm")

    status = alignment.get("measurement_status")
    if status == "measured" and measured is None and not missing:
        warnings.append(
            f"Alignment for '{ref}': measurement_status is 'measured' "
            "but measured_dcm is absent"
        )

    return {"frame_name": ref, "errors": errors, "warnings": warnings}


# --- full set assessment ---

def assess_frame_set(frames, alignments):
    """
    Assess a complete set of frame definitions and alignment records.

    frames:     list of frame dicts
    alignments: list of alignment dicts

    Returns:
        {
            "pass": bool,
            "frame_results":     [{"name": str, "errors": [...], "warnings": [...]}],
            "alignment_results": [{"frame_name": str, "errors": [...], "warnings": [...]}],
            "unaligned_warnings": [str],
        }
    """
    # Build the full registry up-front so parent references can be resolved
    # regardless of list order.
    registry = {f.get("name"): f for f in frames if f.get("name")}

    frame_results = [validate_frame(frm, registry) for frm in frames]

    alignment_results = [validate_alignment(aln, registry) for aln in alignments]

    # Warn about equipment/sensor frames with no alignment record.
    aligned_frame_names = {a.get("frame_name") for a in alignments}
    unaligned_warnings = [
        f"Frame '{f.get('name')}' (type={f.get('type')}) has no alignment data record"
        for f in frames
        if f.get("type") in {"equipment", "sensor"} and f.get("name") not in aligned_frame_names
    ]

    all_errors = (
        [e for r in frame_results for e in r["errors"]]
        + [e for r in alignment_results for e in r["errors"]]
    )

    return {
        "pass": len(all_errors) == 0,
        "frame_results": frame_results,
        "alignment_results": alignment_results,
        "unaligned_warnings": unaligned_warnings,
    }

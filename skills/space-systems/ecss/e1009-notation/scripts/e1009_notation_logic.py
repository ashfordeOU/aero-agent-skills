#!/usr/bin/env python3
"""
e1009_notation_logic.py

Deterministic, offline notation-compliance checks for ECSS-E-ST-10C §5.3.2.
Validates frame labels, rotation matrices, quaternions, Euler-angle
sequences, annotated vectors, exchange records, and transformation chains.

Stdlib only. No network. No external dependencies.
"""

VALID_REPRESENTATIONS = frozenset({"matrix", "quaternion", "euler_angles"})


# ---------------------------------------------------------------------------
# Internal matrix helpers
# ---------------------------------------------------------------------------

def _transpose_3x3(M):
    return [[M[j][i] for j in range(3)] for i in range(3)]


def _mat_mul_3x3(A, B):
    result = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                result[i][j] += A[i][k] * B[k][j]
    return result


def _det_3x3(M):
    a, b, c = M[0]
    d, e, f = M[1]
    g, h, k = M[2]
    return a * (e * k - f * h) - b * (d * k - f * g) + c * (d * h - e * g)


# ---------------------------------------------------------------------------
# Frame label validation
# ---------------------------------------------------------------------------

def validate_frame_label(label):
    """
    Validate a coordinate frame identifier against the ECSS naming convention.

    A conforming label is a non-empty string that:
      - starts with an ASCII letter (A-Z),
      - contains only uppercase letters, decimal digits, and underscores.

    Returns {"ok": True} or {"ok": False, "reason": str}.
    """
    if not isinstance(label, str) or not label:
        return {"ok": False, "reason": "frame label must be a non-empty string"}
    if not label[0].isalpha():
        return {
            "ok": False,
            "reason": f"frame label '{label}' must start with a letter",
        }
    for ch in label:
        if not (ch.isupper() or ch.isdigit() or ch == "_"):
            return {
                "ok": False,
                "reason": (
                    f"frame label '{label}' contains invalid character '{ch}'; "
                    "only uppercase letters, digits, and underscores are allowed"
                ),
            }
    return {"ok": True}


# ---------------------------------------------------------------------------
# Rotation matrix validation
# ---------------------------------------------------------------------------

def validate_rotation_matrix(matrix, tol=1e-6):
    """
    Validate a 3×3 rotation matrix for orthogonality and proper rotation.

    Checks:
      - Exactly 3 rows of 3 numeric elements each.
      - R^T · R ≈ I (all off-diagonal |elements| < tol, diagonal |1 − el| < tol).
      - det(R) ≈ +1.0 within tol.

    Returns {"ok": True} or {"ok": False, "reason": str}.
    """
    if not isinstance(matrix, (list, tuple)) or len(matrix) != 3:
        return {"ok": False, "reason": "rotation matrix must have exactly 3 rows"}
    for i, row in enumerate(matrix):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            return {
                "ok": False,
                "reason": f"row {i} of rotation matrix must have exactly 3 elements",
            }
        for j, el in enumerate(row):
            if not isinstance(el, (int, float)):
                return {
                    "ok": False,
                    "reason": f"element [{i}][{j}] is not numeric (got {type(el).__name__})",
                }

    Rt = _transpose_3x3(matrix)
    RtR = _mat_mul_3x3(Rt, matrix)
    for i in range(3):
        for j in range(3):
            expected = 1.0 if i == j else 0.0
            if abs(RtR[i][j] - expected) > tol:
                return {
                    "ok": False,
                    "reason": (
                        f"rotation matrix is not orthogonal: "
                        f"R^T·R[{i}][{j}] = {RtR[i][j]:.8f}, "
                        f"expected {expected:.1f} (tol={tol})"
                    ),
                }

    det = _det_3x3(matrix)
    if abs(det - 1.0) > tol:
        return {
            "ok": False,
            "reason": (
                f"rotation matrix has determinant {det:.8f}; "
                f"proper rotation requires det ≈ +1.0 (tol={tol})"
            ),
        }

    return {"ok": True}


# ---------------------------------------------------------------------------
# Quaternion validation
# ---------------------------------------------------------------------------

def validate_quaternion(q, tol=1e-6):
    """
    Validate a quaternion for unit norm.

    Accepts any four-element sequence [a, b, c, d]; the check is
    convention-agnostic (scalar-first or scalar-last both accepted).
    The squared norm a²+b²+c²+d² must equal 1.0 within tol.

    Returns {"ok": True} or {"ok": False, "reason": str}.
    """
    if not isinstance(q, (list, tuple)) or len(q) != 4:
        return {
            "ok": False,
            "reason": "quaternion must be a sequence of exactly 4 numeric elements",
        }
    for i, el in enumerate(q):
        if not isinstance(el, (int, float)):
            return {
                "ok": False,
                "reason": f"quaternion element [{i}] is not numeric (got {type(el).__name__})",
            }

    norm_sq = sum(el * el for el in q)
    if abs(norm_sq - 1.0) > tol:
        return {
            "ok": False,
            "reason": (
                f"quaternion squared norm = {norm_sq:.10f}; "
                f"unit quaternion requires norm² ≈ 1.0 (tol={tol})"
            ),
        }
    return {"ok": True}


# ---------------------------------------------------------------------------
# Euler angle sequence validation
# ---------------------------------------------------------------------------

def validate_euler_sequence(sequence):
    """
    Validate an Euler-angle axis-sequence code (e.g., "313", "321").

    Rules:
      - Must be a string of exactly 3 characters.
      - Each character must be '1', '2', or '3' (body-axis indices).
      - No two consecutive characters may be identical.

    Returns {"ok": True} or {"ok": False, "reason": str}.
    """
    if not isinstance(sequence, str):
        return {
            "ok": False,
            "reason": (
                f"Euler sequence must be a string; "
                f"got {type(sequence).__name__}"
            ),
        }
    if len(sequence) != 3:
        return {
            "ok": False,
            "reason": (
                f"Euler sequence must be exactly 3 characters; "
                f"got '{sequence}' (length {len(sequence)})"
            ),
        }
    for i, ch in enumerate(sequence):
        if ch not in ("1", "2", "3"):
            return {
                "ok": False,
                "reason": (
                    f"Euler sequence character [{i}] = '{ch}' is not a valid "
                    "axis index; must be '1', '2', or '3'"
                ),
            }
    if sequence[0] == sequence[1] or sequence[1] == sequence[2]:
        return {
            "ok": False,
            "reason": (
                f"Euler sequence '{sequence}' has consecutive identical axes; "
                "each adjacent pair must differ"
            ),
        }
    return {"ok": True}


# ---------------------------------------------------------------------------
# Annotated vector validation
# ---------------------------------------------------------------------------

def validate_vector_annotation(v_record):
    """
    Validate an annotated vector exchange record.

    A conforming record is a dict with:
      - "frame": a valid frame label (see validate_frame_label).
      - "components": a list of exactly 3 numeric values.

    Returns {"ok": True} or {"ok": False, "reason": str}.
    """
    if not isinstance(v_record, dict):
        return {"ok": False, "reason": "vector record must be a dict"}

    if "frame" not in v_record:
        return {"ok": False, "reason": "vector record missing required key 'frame'"}
    frame_result = validate_frame_label(v_record["frame"])
    if not frame_result["ok"]:
        return {
            "ok": False,
            "reason": f"vector record frame invalid: {frame_result['reason']}",
        }

    if "components" not in v_record:
        return {"ok": False, "reason": "vector record missing required key 'components'"}
    comps = v_record["components"]
    if not isinstance(comps, (list, tuple)) or len(comps) != 3:
        return {
            "ok": False,
            "reason": "vector 'components' must be a list of exactly 3 elements",
        }
    for i, el in enumerate(comps):
        if not isinstance(el, (int, float)):
            return {
                "ok": False,
                "reason": f"vector component [{i}] is not numeric (got {type(el).__name__})",
            }

    return {"ok": True}


# ---------------------------------------------------------------------------
# Exchange record validation
# ---------------------------------------------------------------------------

def validate_exchange_record(record):
    """
    Validate a data exchange record for mandatory ECSS-E-ST-10C §5.3.2 fields.

    A conforming record must contain:
      - "frame": a valid frame label.
      - "representation": one of "matrix", "quaternion", "euler_angles".
      - "payload": a non-None value.
      - If representation is "euler_angles": "euler_sequence" must be present
        and pass validate_euler_sequence.

    Returns a list of finding strings; an empty list means the record is
    compliant. Each finding names the specific field and the violation.
    """
    findings = []

    if not isinstance(record, dict):
        return ["exchange record must be a dict"]

    if "frame" not in record:
        findings.append("missing required field 'frame'")
    else:
        fr = validate_frame_label(record["frame"])
        if not fr["ok"]:
            findings.append(f"invalid frame label: {fr['reason']}")

    if "representation" not in record:
        findings.append("missing required field 'representation'")
    else:
        rep = record["representation"]
        if rep not in VALID_REPRESENTATIONS:
            findings.append(
                f"invalid representation '{rep}'; "
                f"must be one of {sorted(VALID_REPRESENTATIONS)}"
            )
        elif rep == "euler_angles":
            if "euler_sequence" not in record:
                findings.append(
                    "representation 'euler_angles' requires field 'euler_sequence'"
                )
            else:
                es = validate_euler_sequence(record["euler_sequence"])
                if not es["ok"]:
                    findings.append(f"invalid euler_sequence: {es['reason']}")

    if "payload" not in record:
        findings.append("missing required field 'payload'")
    elif record["payload"] is None:
        findings.append("field 'payload' must not be None")

    return findings


# ---------------------------------------------------------------------------
# Transformation chain gap check
# ---------------------------------------------------------------------------

def check_transformation_chain(chain):
    """
    Verify that a sequence of transformation steps forms an unbroken chain.

    Each element must be a dict with "from_frame" and "to_frame" keys
    (both strings). The chain is continuous when the to_frame of step i
    equals the from_frame of step i + 1 for all consecutive pairs.

    Returns a list of gap descriptions; an empty list means the chain is
    gap-free. The chain must contain at least one step.
    """
    findings = []

    if not isinstance(chain, (list, tuple)):
        return ["transformation chain must be a list"]
    if len(chain) == 0:
        return ["transformation chain is empty; at least one step is required"]

    structural_ok = True
    for idx, step in enumerate(chain):
        if not isinstance(step, dict):
            findings.append(f"step [{idx}] is not a dict")
            structural_ok = False
            continue
        for key in ("from_frame", "to_frame"):
            if key not in step:
                findings.append(f"step [{idx}] missing required key '{key}'")
                structural_ok = False

    if structural_ok:
        for i in range(len(chain) - 1):
            to_frame = chain[i]["to_frame"]
            from_frame = chain[i + 1]["from_frame"]
            if to_frame != from_frame:
                findings.append(
                    f"chain break between step [{i}] and [{i + 1}]: "
                    f"step [{i}] to_frame='{to_frame}' != "
                    f"step [{i + 1}] from_frame='{from_frame}'"
                )

    return findings

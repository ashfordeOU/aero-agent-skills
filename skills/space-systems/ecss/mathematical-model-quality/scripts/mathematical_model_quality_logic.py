"""
Structural Mathematical Model (SMM) quality assessment logic.
Anchor: ECSS-E-ST-32C clause 4.6.2.2 (paraphrased procedure, not verbatim text).
stdlib only — offline, deterministic.
"""

VALID_SMM_TYPES = frozenset(
    [
        "linear-static",
        "normal-modes",
        "nonlinear-static",
        "transient",
        "frequency-response",
        "buckling",
    ]
)

RIGID_BODY_MODE_COUNT = 6

DEFAULT_MESH_ASPECT_RATIO_LIMIT = 10.0
DEFAULT_MESH_MAX_ANGLE_DEG = 135.0
DEFAULT_MESH_MIN_ANGLE_DEG = 45.0
DEFAULT_RBM_FREQ_HZ_TOLERANCE = 1.0e-3
DEFAULT_MASS_TOLERANCE_FRACTION = 0.02
DEFAULT_STATIC_TOLERANCE_FRACTION = 0.10
DEFAULT_MODAL_FREQ_TOLERANCE_FRACTION = 0.05


def validate_smm_type(smm_type: str) -> dict:
    """
    Confirm the SMM is assigned one of the recognized analysis categories.
    Returns {'ok': bool, 'smm_type': str, 'finding': str | None}.
    """
    if not isinstance(smm_type, str):
        return {
            "ok": False,
            "smm_type": smm_type,
            "finding": f"SMM type must be a string; received {type(smm_type).__name__}.",
        }
    if smm_type not in VALID_SMM_TYPES:
        return {
            "ok": False,
            "smm_type": smm_type,
            "finding": (
                f"SMM type '{smm_type}' is not a recognized analysis category. "
                f"Accepted values: {sorted(VALID_SMM_TYPES)}."
            ),
        }
    return {"ok": True, "smm_type": smm_type, "finding": None}


def assess_mesh_quality(
    aspect_ratio: float,
    max_angle_deg: float,
    min_angle_deg: float,
    aspect_ratio_limit: float = DEFAULT_MESH_ASPECT_RATIO_LIMIT,
    max_angle_limit: float = DEFAULT_MESH_MAX_ANGLE_DEG,
    min_angle_limit: float = DEFAULT_MESH_MIN_ANGLE_DEG,
) -> dict:
    """
    Evaluate mesh element quality against aspect-ratio and angle bounds.
    Returns {'ok': bool, 'findings': list[str]}.
    """
    findings = []
    if aspect_ratio <= 0:
        findings.append(
            f"Aspect ratio must be positive; received {aspect_ratio}."
        )
    elif aspect_ratio > aspect_ratio_limit:
        findings.append(
            f"Mesh aspect ratio {aspect_ratio:.2f} exceeds limit {aspect_ratio_limit:.1f}."
        )
    if max_angle_deg > max_angle_limit:
        findings.append(
            f"Maximum element angle {max_angle_deg:.1f}° exceeds limit {max_angle_limit:.1f}°."
        )
    if min_angle_deg < min_angle_limit:
        findings.append(
            f"Minimum element angle {min_angle_deg:.1f}° is below limit {min_angle_limit:.1f}°."
        )
    return {"ok": len(findings) == 0, "findings": findings}


def check_rigid_body_modes(
    free_free_frequencies_hz: list,
    tolerance_hz: float = DEFAULT_RBM_FREQ_HZ_TOLERANCE,
) -> dict:
    """
    Verify that at least six rigid-body modes exist and each lies within
    tolerance_hz of zero frequency.
    Returns {'ok': bool, 'findings': list[str]}.
    """
    findings = []
    if len(free_free_frequencies_hz) < RIGID_BODY_MODE_COUNT:
        findings.append(
            f"Expected at least {RIGID_BODY_MODE_COUNT} free-free modes; "
            f"received {len(free_free_frequencies_hz)}."
        )
        return {"ok": False, "findings": findings}

    rbm_freqs = free_free_frequencies_hz[:RIGID_BODY_MODE_COUNT]
    for idx, freq in enumerate(rbm_freqs, start=1):
        if abs(freq) > tolerance_hz:
            findings.append(
                f"Rigid-body mode {idx}: frequency {freq:.4e} Hz exceeds "
                f"zero-frequency tolerance {tolerance_hz:.2e} Hz."
            )
    return {"ok": len(findings) == 0, "findings": findings}


def check_mass_properties(
    smm_mass_kg: float,
    reference_mass_kg: float,
    tolerance_fraction: float = DEFAULT_MASS_TOLERANCE_FRACTION,
) -> dict:
    """
    Compare the SMM total mass against a reference (measured or budgeted) mass.
    Returns {'ok': bool, 'error_fraction': float | None, 'finding': str | None}.
    """
    if reference_mass_kg <= 0:
        return {
            "ok": False,
            "error_fraction": None,
            "finding": (
                f"Reference mass must be positive; received {reference_mass_kg} kg."
            ),
        }
    if smm_mass_kg < 0:
        return {
            "ok": False,
            "error_fraction": None,
            "finding": (
                f"SMM mass must be non-negative; received {smm_mass_kg} kg."
            ),
        }
    error = abs(smm_mass_kg - reference_mass_kg) / reference_mass_kg
    if error > tolerance_fraction:
        return {
            "ok": False,
            "error_fraction": error,
            "finding": (
                f"SMM mass {smm_mass_kg:.4f} kg differs from reference "
                f"{reference_mass_kg:.4f} kg by {error * 100:.2f}% "
                f"(limit {tolerance_fraction * 100:.1f}%)."
            ),
        }
    return {"ok": True, "error_fraction": error, "finding": None}


def check_static_correlation(
    smm_displacement_mm: float,
    test_displacement_mm: float,
    tolerance_fraction: float = DEFAULT_STATIC_TOLERANCE_FRACTION,
) -> dict:
    """
    Correlate an SMM static displacement prediction against a test measurement.
    Returns {'ok': bool, 'error_fraction': float | None, 'finding': str | None}.
    """
    if test_displacement_mm == 0.0:
        return {
            "ok": False,
            "error_fraction": None,
            "finding": "Test displacement is zero; relative error is undefined.",
        }
    error = abs(smm_displacement_mm - test_displacement_mm) / abs(test_displacement_mm)
    if error > tolerance_fraction:
        return {
            "ok": False,
            "error_fraction": error,
            "finding": (
                f"SMM static displacement {smm_displacement_mm:.4f} mm differs from "
                f"test {test_displacement_mm:.4f} mm by {error * 100:.2f}% "
                f"(limit {tolerance_fraction * 100:.1f}%)."
            ),
        }
    return {"ok": True, "error_fraction": error, "finding": None}


def check_modal_frequency_correlation(
    smm_frequency_hz: float,
    test_frequency_hz: float,
    tolerance_fraction: float = DEFAULT_MODAL_FREQ_TOLERANCE_FRACTION,
) -> dict:
    """
    Correlate an SMM natural frequency prediction against a test measurement.
    Returns {'ok': bool, 'error_fraction': float | None, 'finding': str | None}.
    """
    if test_frequency_hz <= 0:
        return {
            "ok": False,
            "error_fraction": None,
            "finding": (
                f"Test modal frequency must be positive; received {test_frequency_hz} Hz."
            ),
        }
    if smm_frequency_hz <= 0:
        return {
            "ok": False,
            "error_fraction": None,
            "finding": (
                f"SMM modal frequency must be positive; received {smm_frequency_hz} Hz."
            ),
        }
    error = abs(smm_frequency_hz - test_frequency_hz) / test_frequency_hz
    if error > tolerance_fraction:
        return {
            "ok": False,
            "error_fraction": error,
            "finding": (
                f"SMM frequency {smm_frequency_hz:.3f} Hz differs from test "
                f"{test_frequency_hz:.3f} Hz by {error * 100:.2f}% "
                f"(limit {tolerance_fraction * 100:.1f}%)."
            ),
        }
    return {"ok": True, "error_fraction": error, "finding": None}


def categorize_finding(severity: str) -> str:
    """
    Map a severity label to its canonical finding category.
    Accepted values: 'critical', 'warning', 'info'.
    Raises ValueError for unrecognized input.
    """
    severity = severity.lower().strip()
    accepted = {"critical", "warning", "info"}
    if severity not in accepted:
        raise ValueError(
            f"Unknown severity '{severity}'. Accepted: {sorted(accepted)}."
        )
    return severity


def aggregate_smm_findings(results: list) -> dict:
    """
    Consolidate a list of check-result dicts into an overall adequacy verdict.
    Each element must have an 'ok' key (bool). Optional keys: 'finding' (str),
    'findings' (list[str]).
    Returns {'adequate': bool, 'all_findings': list[str],
             'pass_count': int, 'fail_count': int}.
    """
    all_findings = []
    pass_count = 0
    fail_count = 0
    for result in results:
        if result.get("ok"):
            pass_count += 1
        else:
            fail_count += 1
            if result.get("finding") is not None:
                all_findings.append(result["finding"])
            for msg in result.get("findings", []):
                all_findings.append(msg)
    return {
        "adequate": fail_count == 0,
        "all_findings": all_findings,
        "pass_count": pass_count,
        "fail_count": fail_count,
    }

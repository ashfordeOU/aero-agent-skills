"""
Element-level mechanical test planning and compliance logic.
Reference: ECSS-E-ST-10C §6.5.2 (paraphrased; standard is the anchor only).
stdlib only — no third-party dependencies.
"""

VALID_TEST_TYPES = frozenset({
    "physical_properties",
    "modal_survey",
    "static_load",
    "spin",
    "transient_sine_burst",
    "acoustic",
    "random_vibration",
    "sinusoidal_vibration",
})

VALID_LEVELS = frozenset({"acceptance", "qualification", "protoflight"})

# Canonical test sequence: physical-properties first, modal-survey before
# vibration/acoustic tests.
CANONICAL_ORDER = [
    "physical_properties",
    "modal_survey",
    "static_load",
    "spin",
    "transient_sine_burst",
    "acoustic",
    "random_vibration",
    "sinusoidal_vibration",
]

_MASS_PROPERTIES = frozenset({"physical_properties"})
_STRUCTURAL = frozenset({"static_load", "spin", "transient_sine_burst"})
_DYNAMIC = frozenset({"modal_survey", "acoustic", "random_vibration", "sinusoidal_vibration"})

_TIMED_TESTS = frozenset({"random_vibration", "sinusoidal_vibration", "acoustic", "transient_sine_burst"})
_VIBRATION_TESTS = frozenset({"random_vibration", "sinusoidal_vibration"})
_MUST_FOLLOW_PHYSICAL = _STRUCTURAL | _DYNAMIC
_MUST_FOLLOW_MODAL = frozenset({"random_vibration", "sinusoidal_vibration", "acoustic", "transient_sine_burst"})


def categorize_test(test_type):
    """Return the mechanical test family for a given test type string."""
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            f"Unknown test type: {test_type!r}. "
            f"Must be one of {sorted(VALID_TEST_TYPES)}"
        )
    if test_type in _MASS_PROPERTIES:
        return "mass_properties"
    if test_type in _STRUCTURAL:
        return "structural"
    return "dynamic"


def check_physical_properties(mass_kg, mass_budget_kg, cm_offset_m, cm_limit_m,
                               moi_kgm2=None, moi_limit_kgm2=None):
    """
    Check element physical-properties measurement against budgets.

    Parameters
    ----------
    mass_kg : float — measured mass
    mass_budget_kg : float — allocated mass budget
    cm_offset_m : float — measured centre-of-mass offset (non-negative)
    cm_limit_m : float — allowable CoM offset limit
    moi_kgm2 : float or None — measured moment of inertia (optional)
    moi_limit_kgm2 : float or None — allowable MoI limit (required if moi_kgm2 given)

    Returns dict: {'compliant': bool, 'findings': list[str]}
    """
    if mass_kg <= 0:
        raise ValueError("mass_kg must be positive")
    if mass_budget_kg <= 0:
        raise ValueError("mass_budget_kg must be positive")
    if cm_offset_m < 0:
        raise ValueError("cm_offset_m must be non-negative")
    if cm_limit_m <= 0:
        raise ValueError("cm_limit_m must be positive")
    if moi_kgm2 is not None and moi_limit_kgm2 is None:
        raise ValueError("moi_limit_kgm2 must be provided when moi_kgm2 is given")
    if moi_limit_kgm2 is not None and moi_limit_kgm2 <= 0:
        raise ValueError("moi_limit_kgm2 must be positive")

    findings = []
    if mass_kg > mass_budget_kg:
        findings.append(
            f"Mass {mass_kg:.3f} kg exceeds budget {mass_budget_kg:.3f} kg "
            f"(delta {mass_kg - mass_budget_kg:.3f} kg)"
        )
    if cm_offset_m > cm_limit_m:
        findings.append(
            f"CoM offset {cm_offset_m:.4f} m exceeds limit {cm_limit_m:.4f} m"
        )
    if moi_kgm2 is not None and moi_kgm2 > moi_limit_kgm2:
        findings.append(
            f"MoI {moi_kgm2:.4f} kg·m² exceeds limit {moi_limit_kgm2:.4f} kg·m²"
        )
    return {"compliant": len(findings) == 0, "findings": findings}


def check_modal_survey(measured_freq_hz, minimum_freq_hz):
    """
    Check that the measured fundamental frequency clears the required minimum.

    Returns dict: {'compliant': bool, 'findings': list[str], 'margin_hz': float}
    """
    if measured_freq_hz <= 0:
        raise ValueError("measured_freq_hz must be positive")
    if minimum_freq_hz <= 0:
        raise ValueError("minimum_freq_hz must be positive")

    margin = measured_freq_hz - minimum_freq_hz
    findings = []
    if measured_freq_hz < minimum_freq_hz:
        findings.append(
            f"Fundamental frequency {measured_freq_hz:.2f} Hz is below "
            f"minimum {minimum_freq_hz:.2f} Hz (margin {margin:.2f} Hz)"
        )
    return {"compliant": len(findings) == 0, "findings": findings, "margin_hz": margin}


def check_static_load(applied_load_n, limit_load_n, safety_factor=1.0):
    """
    Check that the applied test load does not exceed limit_load × safety_factor.

    Returns dict: {'compliant': bool, 'findings': list[str], 'margin_n': float}
    """
    if applied_load_n <= 0:
        raise ValueError("applied_load_n must be positive")
    if limit_load_n <= 0:
        raise ValueError("limit_load_n must be positive")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0")

    allowable = limit_load_n * safety_factor
    margin = allowable - applied_load_n
    findings = []
    if applied_load_n > allowable:
        findings.append(
            f"Applied load {applied_load_n:.2f} N exceeds allowable "
            f"{allowable:.2f} N (limit {limit_load_n:.2f} N × SF {safety_factor:.2f})"
        )
    return {"compliant": len(findings) == 0, "findings": findings, "margin_n": margin}


def check_vibration_level(test_type, measured_grms, specification_grms,
                           tolerance_fraction=0.10):
    """
    Check that a vibration test level lies within the control band
    (specification ± tolerance_fraction).

    test_type must be 'random_vibration' or 'sinusoidal_vibration'.
    Returns dict: {'compliant': bool, 'findings': list[str]}
    """
    if test_type not in _VIBRATION_TESTS:
        raise ValueError(
            f"test_type must be 'random_vibration' or 'sinusoidal_vibration', "
            f"got {test_type!r}"
        )
    if measured_grms <= 0:
        raise ValueError("measured_grms must be positive")
    if specification_grms <= 0:
        raise ValueError("specification_grms must be positive")
    if not (0.0 < tolerance_fraction < 1.0):
        raise ValueError("tolerance_fraction must be between 0 and 1 exclusive")

    lower = specification_grms * (1.0 - tolerance_fraction)
    upper = specification_grms * (1.0 + tolerance_fraction)
    findings = []
    if measured_grms < lower:
        findings.append(
            f"{test_type}: level {measured_grms:.3f} Grms is below lower "
            f"control bound {lower:.3f} Grms"
        )
    elif measured_grms > upper:
        findings.append(
            f"{test_type}: level {measured_grms:.3f} Grms exceeds upper "
            f"control bound {upper:.3f} Grms"
        )
    return {"compliant": len(findings) == 0, "findings": findings}


def check_acoustic_level(measured_oaspl_db, specification_oaspl_db,
                          tolerance_db=3.0):
    """
    Check that the measured acoustic OASPL is within ±tolerance_db of
    specification.

    Returns dict: {'compliant': bool, 'findings': list[str], 'deviation_db': float}
    """
    if specification_oaspl_db <= 0:
        raise ValueError("specification_oaspl_db must be positive")
    if tolerance_db <= 0:
        raise ValueError("tolerance_db must be positive")

    deviation = abs(measured_oaspl_db - specification_oaspl_db)
    findings = []
    if deviation > tolerance_db:
        findings.append(
            f"Acoustic OASPL {measured_oaspl_db:.1f} dB deviates "
            f"{deviation:.1f} dB from specification {specification_oaspl_db:.1f} dB "
            f"(limit ±{tolerance_db:.1f} dB)"
        )
    return {"compliant": len(findings) == 0, "findings": findings, "deviation_db": deviation}


def check_test_sequence(performed_sequence, required_sequence=None):
    """
    Verify test ordering and completeness:
    - physical_properties must precede all structural and dynamic tests.
    - modal_survey must precede all vibration and acoustic tests.
    - All tests in required_sequence must be present.

    performed_sequence: list of test_type strings in execution order.
    required_sequence: list of required test_type strings (defaults to CANONICAL_ORDER).
    Returns dict: {'compliant': bool, 'findings': list[str]}
    """
    if required_sequence is None:
        required_sequence = list(CANONICAL_ORDER)

    for t in performed_sequence:
        if t not in VALID_TEST_TYPES:
            raise ValueError(f"Unknown test type in performed sequence: {t!r}")
    for t in required_sequence:
        if t not in VALID_TEST_TYPES:
            raise ValueError(f"Unknown required test type: {t!r}")

    findings = []

    missing = [t for t in required_sequence if t not in performed_sequence]
    if missing:
        findings.append(f"Missing required test types: {missing}")

    if "physical_properties" in performed_sequence:
        pp_idx = performed_sequence.index("physical_properties")
        for dt in _MUST_FOLLOW_PHYSICAL:
            if dt in performed_sequence:
                dt_idx = performed_sequence.index(dt)
                if dt_idx < pp_idx:
                    findings.append(
                        f"{dt!r} performed before 'physical_properties' "
                        f"(positions {dt_idx} and {pp_idx})"
                    )

    if "modal_survey" in performed_sequence:
        ms_idx = performed_sequence.index("modal_survey")
        for vt in _MUST_FOLLOW_MODAL:
            if vt in performed_sequence:
                vt_idx = performed_sequence.index(vt)
                if vt_idx < ms_idx:
                    findings.append(
                        f"{vt!r} performed before 'modal_survey' "
                        f"(positions {vt_idx} and {ms_idx})"
                    )

    return {"compliant": len(findings) == 0, "findings": findings}


def check_test_level(test_type, level, duration_s=None):
    """
    Validate that:
    - level is one of the three accepted values.
    - timed tests supply a positive duration.

    Returns dict: {'compliant': bool, 'findings': list[str]}
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(f"Unknown test type: {test_type!r}")
    if level not in VALID_LEVELS:
        raise ValueError(
            f"Unknown test level: {level!r}. "
            f"Must be one of {sorted(VALID_LEVELS)}"
        )
    if duration_s is not None and duration_s <= 0:
        raise ValueError("duration_s must be positive")

    findings = []
    if test_type in _TIMED_TESTS and duration_s is None:
        findings.append(
            f"{test_type!r} is a timed test but no duration was supplied"
        )
    return {"compliant": len(findings) == 0, "findings": findings}

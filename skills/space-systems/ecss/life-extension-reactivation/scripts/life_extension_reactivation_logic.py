"""
life_extension_reactivation_logic.py

Engineering logic for service-life extension, reactivation, and re-acceptance
of pressure hardware (PH) per ECSS-E-ST-32C §4.2.4.

Stdlib only — no third-party dependencies.
"""

# Minimum safety margin required to approve a life extension
MIN_EXTENSION_SAFETY_FACTOR = 1.25

# Default maximum dormancy period before mandatory re-qualification
MAX_DORMANCY_MONTHS = 60  # 5 years

# Verdict codes used across all result types
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_CONDITIONAL = "conditional"
STATUS_REQUIRES_REQUALIFICATION = "requires_requalification"


class LifeExtensionResult:
    """Outcome of a service-life extension assessment."""

    def __init__(self, status, reason, remaining_life=None, safety_margin=None):
        self.status = status
        self.reason = reason
        self.remaining_life = remaining_life
        self.safety_margin = safety_margin

    def __repr__(self):
        return (
            f"LifeExtensionResult(status={self.status!r}, "
            f"safety_margin={self.safety_margin})"
        )


class ReactivationResult:
    """Outcome of a reactivation readiness assessment."""

    def __init__(self, status, reason, items_failed=None):
        self.status = status
        self.reason = reason
        self.items_failed = items_failed if items_failed is not None else []

    def __repr__(self):
        return (
            f"ReactivationResult(status={self.status!r}, "
            f"items_failed={self.items_failed})"
        )


class ReAcceptanceResult:
    """Outcome of a re-acceptance assessment."""

    def __init__(self, status, reason, required_actions=None):
        self.status = status
        self.reason = reason
        self.required_actions = required_actions if required_actions is not None else []

    def __repr__(self):
        return (
            f"ReAcceptanceResult(status={self.status!r}, "
            f"required_actions={self.required_actions})"
        )


def assess_life_extension(
    certified_life,
    consumed_life,
    extension_request,
    applied_safety_factor,
    load_increase_fraction=0.0,
):
    """
    Evaluate whether a life extension request is approvable.

    Uses a simplified Miner's-rule analogue: if operating loads have
    increased by a fraction f relative to the original design loads, the
    effective remaining life is reduced to remaining / (1 + f).

    Parameters
    ----------
    certified_life : float
        Original certified life in design cycles or operating hours (> 0).
    consumed_life : float
        Life already consumed; must satisfy 0 <= consumed_life < certified_life.
    extension_request : float
        Additional life being requested (> 0).
    applied_safety_factor : float
        Programme safety factor applied to the remaining-life ratio (>= 1.0).
    load_increase_fraction : float
        Fractional increase in operating load relative to the original design
        (0.0 = no increase, 0.1 = 10% increase). Default 0.0.

    Returns
    -------
    LifeExtensionResult
    """
    if certified_life <= 0:
        raise ValueError("certified_life must be positive")
    if consumed_life < 0 or consumed_life >= certified_life:
        raise ValueError(
            "consumed_life must be in [0, certified_life); "
            f"got consumed_life={consumed_life}, certified_life={certified_life}"
        )
    if extension_request <= 0:
        raise ValueError("extension_request must be positive")
    if applied_safety_factor < 1.0:
        raise ValueError("applied_safety_factor must be >= 1.0")
    if load_increase_fraction < 0.0:
        raise ValueError("load_increase_fraction must be >= 0.0")

    remaining = certified_life - consumed_life

    if load_increase_fraction > 0.0:
        effective_remaining = remaining / (1.0 + load_increase_fraction)
    else:
        effective_remaining = remaining

    safety_margin = (effective_remaining / extension_request) * applied_safety_factor

    if safety_margin < MIN_EXTENSION_SAFETY_FACTOR:
        return LifeExtensionResult(
            status=STATUS_REJECTED,
            reason=(
                f"Safety margin {safety_margin:.4f} is below the minimum "
                f"required {MIN_EXTENSION_SAFETY_FACTOR}. Effective remaining "
                f"life {effective_remaining:.4f} is insufficient for the "
                f"requested extension of {extension_request:.4f}."
            ),
            remaining_life=effective_remaining,
            safety_margin=safety_margin,
        )

    return LifeExtensionResult(
        status=STATUS_APPROVED,
        reason=(
            f"Safety margin {safety_margin:.4f} meets or exceeds the minimum "
            f"required {MIN_EXTENSION_SAFETY_FACTOR}. Life extension approved."
        ),
        remaining_life=effective_remaining,
        safety_margin=safety_margin,
    )


def check_reactivation_readiness(
    dormancy_months,
    seal_inspection_passed,
    structural_inspection_passed,
    functional_test_passed,
    max_dormancy_months=MAX_DORMANCY_MONTHS,
):
    """
    Determine whether a dormant pressure hardware item is ready for reactivation.

    Items that have been dormant longer than max_dormancy_months require
    mandatory re-qualification regardless of inspection outcomes.

    Parameters
    ----------
    dormancy_months : float
        Duration the item has been in storage or dormancy (>= 0).
    seal_inspection_passed : bool
        Whether the seal integrity inspection was satisfactory.
    structural_inspection_passed : bool
        Whether the structural/visual inspection was satisfactory.
    functional_test_passed : bool
        Whether the functional re-qualification test was satisfactory.
    max_dormancy_months : float
        Maximum allowed dormancy before mandatory re-qualification (> 0).

    Returns
    -------
    ReactivationResult
    """
    if dormancy_months < 0:
        raise ValueError("dormancy_months must be >= 0")
    if max_dormancy_months <= 0:
        raise ValueError("max_dormancy_months must be positive")

    if dormancy_months > max_dormancy_months:
        return ReactivationResult(
            status=STATUS_REQUIRES_REQUALIFICATION,
            reason=(
                f"Dormancy duration {dormancy_months:.1f} months exceeds the "
                f"maximum allowed {max_dormancy_months:.1f} months. Mandatory "
                f"re-qualification is required before reactivation."
            ),
            items_failed=[
                f"Dormancy {dormancy_months:.1f} months > limit "
                f"{max_dormancy_months:.1f} months — re-qualification mandatory."
            ],
        )

    items_failed = []
    if not seal_inspection_passed:
        items_failed.append("Seal integrity inspection: FAILED.")
    if not structural_inspection_passed:
        items_failed.append("Structural/visual inspection: FAILED.")
    if not functional_test_passed:
        items_failed.append("Functional re-qualification test: FAILED.")

    if items_failed:
        return ReactivationResult(
            status=STATUS_REJECTED,
            reason="One or more reactivation readiness checks failed.",
            items_failed=items_failed,
        )

    return ReactivationResult(
        status=STATUS_APPROVED,
        reason="All reactivation readiness checks passed. Item may be reactivated.",
    )


def evaluate_re_acceptance(
    design_changed,
    material_traceability_confirmed,
    original_certification_valid,
    updated_test_data_available,
):
    """
    Evaluate re-acceptance suitability after storage, re-use, or design change.

    Decision tree (evaluated in order):
    1. Material traceability not confirmed → reject unconditionally.
    2. Design changed + no test data → reject.
    3. Design changed + test data available → conditional (re-qualification required).
    4. Original certification no longer valid → conditional with mandatory actions.
    5. No current test/inspection data → conditional (inspection/test required).
    6. All satisfied → approved.

    Parameters
    ----------
    design_changed : bool
        Whether the design has been modified since original certification.
    material_traceability_confirmed : bool
        Whether the full material traceability chain is intact.
    original_certification_valid : bool
        Whether the original certification documentation is still applicable.
    updated_test_data_available : bool
        Whether current test data or inspection records are available.

    Returns
    -------
    ReAcceptanceResult
    """
    if not material_traceability_confirmed:
        return ReAcceptanceResult(
            status=STATUS_REJECTED,
            reason=(
                "Material traceability cannot be confirmed. "
                "Re-acceptance is not permitted."
            ),
            required_actions=[
                "Establish or recover the full material traceability chain "
                "before any re-acceptance review."
            ],
        )

    required_actions = []

    if design_changed:
        required_actions.append(
            "Design modification detected: a full re-qualification test campaign "
            "is required before re-acceptance can be granted."
        )
        if not updated_test_data_available:
            required_actions.append(
                "No updated test data is available: re-acceptance cannot proceed "
                "without new test results supporting the design change."
            )
            return ReAcceptanceResult(
                status=STATUS_REJECTED,
                reason=(
                    "Design changed and no supporting test data is available. "
                    "Re-acceptance rejected."
                ),
                required_actions=required_actions,
            )
        return ReAcceptanceResult(
            status=STATUS_CONDITIONAL,
            reason=(
                "Design has changed. Re-acceptance is conditional on completing "
                "the required re-qualification campaign."
            ),
            required_actions=required_actions,
        )

    if not original_certification_valid:
        required_actions.append(
            "Original certification is no longer applicable: an updated "
            "certification approval must be obtained."
        )
        if not updated_test_data_available:
            required_actions.append(
                "No current test or inspection data: an inspection or functional "
                "test must be performed before re-acceptance."
            )
        return ReAcceptanceResult(
            status=STATUS_CONDITIONAL,
            reason=(
                "Original certification is not valid. Conditional re-acceptance "
                "pending updated approval and, if required, new test data."
            ),
            required_actions=required_actions,
        )

    if not updated_test_data_available:
        required_actions.append(
            "No current test or inspection data on record: at minimum an "
            "inspection and functional check must be performed."
        )
        return ReAcceptanceResult(
            status=STATUS_CONDITIONAL,
            reason=(
                "Re-acceptance is conditional: current test or inspection data "
                "must be obtained and reviewed."
            ),
            required_actions=required_actions,
        )

    return ReAcceptanceResult(
        status=STATUS_APPROVED,
        reason="All re-acceptance criteria are satisfied. Component may be re-accepted.",
    )


def summarize_assessment(life_ext_result, reactivation_result, re_acceptance_result):
    """
    Aggregate the three individual assessment results into a single verdict.

    Precedence (highest to lowest): rejected/requires_requalification >
    conditional > approved.

    Parameters
    ----------
    life_ext_result : LifeExtensionResult
    reactivation_result : ReactivationResult
    re_acceptance_result : ReAcceptanceResult

    Returns
    -------
    dict with keys:
        'overall_status' : str  — one of the STATUS_* constants
        'findings'       : dict — per-domain status and reason
    """
    statuses = {
        life_ext_result.status,
        reactivation_result.status,
        re_acceptance_result.status,
    }

    findings = {
        "life_extension": {
            "status": life_ext_result.status,
            "reason": life_ext_result.reason,
            "remaining_life": life_ext_result.remaining_life,
            "safety_margin": life_ext_result.safety_margin,
        },
        "reactivation": {
            "status": reactivation_result.status,
            "reason": reactivation_result.reason,
            "items_failed": reactivation_result.items_failed,
        },
        "re_acceptance": {
            "status": re_acceptance_result.status,
            "reason": re_acceptance_result.reason,
            "required_actions": re_acceptance_result.required_actions,
        },
    }

    if STATUS_REJECTED in statuses or STATUS_REQUIRES_REQUALIFICATION in statuses:
        overall = STATUS_REJECTED
    elif STATUS_CONDITIONAL in statuses:
        overall = STATUS_CONDITIONAL
    else:
        overall = STATUS_APPROVED

    return {"overall_status": overall, "findings": findings}

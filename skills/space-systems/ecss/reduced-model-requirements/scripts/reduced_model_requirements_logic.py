#!/usr/bin/env python3
"""ECSS-E-ST-32 clause 4.4 reduced model requirements (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): structural
reduced models condense a large finite element model to a compact boundary-node
representation using Craig-Bampton component mode synthesis (fixed-interface
normal modes + constraint modes), Guyan static condensation (static slave-to-
master relationship), or a generic superelement wrapper around either technique.
Each technique must satisfy: complete interface-node definition, internal-mode
frequency coverage to 1.5× the target frequency (Craig-Bampton), residual
flexibility correction when modes are truncated below that cutoff, mass
fractional error ≤ 1 %, frequency fractional error ≤ 2 % (Craig-Bampton), and
Guyan applicability only when the target frequency is below the lowest slave-
mode frequency. This module implements those checks deterministically from
floating-point inputs; it does not implement the finite element condensation
arithmetic itself.
"""

# ── Accepted reduction methods ────────────────────────────────────────────────

ACCEPTED_REDUCTION_METHODS = frozenset({"craig_bampton", "guyan", "superelement"})
VALID_DOF_CODES = frozenset({1, 2, 3, 4, 5, 6})

# ── Engineering limits (ECSS-E-ST-32 §4.4 practice, paraphrased) ─────────────

MASS_ACCURACY_LIMIT = 0.01          # max fractional error on total mass
FREQUENCY_ACCURACY_LIMIT = 0.02    # max fractional error on retained mode frequencies
INTERNAL_MODE_FREQ_MARGIN = 1.5    # retained mode set must reach target × this


class ReducedModelError(ValueError):
    """Raised for logically invalid reduced-model specification inputs."""


# ── Primitive checks ──────────────────────────────────────────────────────────

def check_reduction_method(method: str) -> str:
    """Return the normalised method string if accepted; raise ReducedModelError
    for anything outside {'craig_bampton', 'guyan', 'superelement'}."""
    normalised = method.strip().lower()
    if normalised not in ACCEPTED_REDUCTION_METHODS:
        raise ReducedModelError(
            f"Unknown reduction method {method!r}. "
            f"Accepted: {sorted(ACCEPTED_REDUCTION_METHODS)}"
        )
    return normalised


def check_interface_nodes(interface_nodes: list) -> list:
    """Verify interface-node definitions for completeness.

    Each entry must be a dict with:
      'node_id'   — positive int, unique across the list
      'dof_codes' — non-empty list/tuple of ints in 1–6

    Returns a list of finding strings (empty → all nodes pass).
    """
    if not interface_nodes:
        return [
            "interface_nodes list is empty; "
            "at least one boundary interface node is required"
        ]

    findings = []
    seen_ids = set()

    for idx, node in enumerate(interface_nodes):
        tag = f"interface_nodes[{idx}]"
        if not isinstance(node, dict):
            findings.append(
                f"{tag}: entry must be a dict, got {type(node).__name__}"
            )
            continue

        node_id = node.get("node_id")
        dof_codes = node.get("dof_codes")

        if node_id is None:
            findings.append(f"{tag}: missing 'node_id'")
        elif not isinstance(node_id, int) or node_id < 1:
            findings.append(
                f"{tag}: 'node_id' must be a positive integer, got {node_id!r}"
            )
        elif node_id in seen_ids:
            findings.append(f"{tag}: duplicate node_id {node_id}")
        else:
            seen_ids.add(node_id)

        if dof_codes is None:
            findings.append(f"{tag}: missing 'dof_codes'")
        elif not isinstance(dof_codes, (list, tuple)) or len(dof_codes) == 0:
            findings.append(f"{tag}: 'dof_codes' must be a non-empty list")
        else:
            bad = [d for d in dof_codes if d not in VALID_DOF_CODES]
            if bad:
                findings.append(
                    f"{tag}: 'dof_codes' contains invalid code(s) {bad}; "
                    "valid codes are 1–6"
                )

    return findings


def check_craig_bampton(
    boundary_dof_count: int,
    internal_mode_count: int,
    target_frequency_hz: float,
    max_retained_mode_frequency_hz: float,
    mass_fractional_error: float,
    frequency_fractional_error: float,
) -> list:
    """Verify Craig-Bampton parameters against ECSS-E-ST-32 §4.4 practice.

    Returns a list of finding strings (empty → compliant).
    Raises ReducedModelError for logically invalid (negative) inputs.
    """
    if boundary_dof_count < 0:
        raise ReducedModelError("boundary_dof_count must be non-negative")
    if internal_mode_count < 0:
        raise ReducedModelError("internal_mode_count must be non-negative")
    if target_frequency_hz < 0:
        raise ReducedModelError("target_frequency_hz must be non-negative")
    if mass_fractional_error < 0:
        raise ReducedModelError("mass_fractional_error must be non-negative")
    if frequency_fractional_error < 0:
        raise ReducedModelError("frequency_fractional_error must be non-negative")

    findings = []

    if boundary_dof_count == 0:
        findings.append(
            "boundary_dof_count is zero; "
            "at least one boundary degree of freedom is required"
        )

    if target_frequency_hz > 0:
        required_cutoff = target_frequency_hz * INTERNAL_MODE_FREQ_MARGIN
        if max_retained_mode_frequency_hz < required_cutoff:
            findings.append(
                f"retained internal mode set reaches "
                f"{max_retained_mode_frequency_hz:.2f} Hz but must reach "
                f"{required_cutoff:.2f} Hz "
                f"(target {target_frequency_hz:.2f} Hz "
                f"× {INTERNAL_MODE_FREQ_MARGIN})"
            )

    if mass_fractional_error > MASS_ACCURACY_LIMIT:
        findings.append(
            f"mass fractional error {mass_fractional_error:.4f} "
            f"exceeds limit {MASS_ACCURACY_LIMIT:.4f}"
        )

    if frequency_fractional_error > FREQUENCY_ACCURACY_LIMIT:
        findings.append(
            f"frequency fractional error {frequency_fractional_error:.4f} "
            f"exceeds limit {FREQUENCY_ACCURACY_LIMIT:.4f}"
        )

    return findings


def check_guyan(
    total_dof_count: int,
    master_dof_count: int,
    target_frequency_hz: float,
    lowest_slave_mode_frequency_hz: float,
    mass_fractional_error: float,
) -> list:
    """Verify Guyan static condensation parameters.

    Returns a list of finding strings (empty → compliant).
    Raises ReducedModelError for logically invalid inputs.
    """
    if total_dof_count < 0:
        raise ReducedModelError("total_dof_count must be non-negative")
    if master_dof_count < 0:
        raise ReducedModelError("master_dof_count must be non-negative")
    if target_frequency_hz < 0:
        raise ReducedModelError("target_frequency_hz must be non-negative")
    if mass_fractional_error < 0:
        raise ReducedModelError("mass_fractional_error must be non-negative")

    findings = []

    if master_dof_count == 0:
        findings.append(
            "master_dof_count is zero; "
            "at least one master degree of freedom is required"
        )

    if total_dof_count > 0 and master_dof_count > 0:
        if master_dof_count >= total_dof_count:
            findings.append(
                f"master_dof_count {master_dof_count} must be less than "
                f"total_dof_count {total_dof_count}"
            )

    if target_frequency_hz > 0 and lowest_slave_mode_frequency_hz > 0:
        if target_frequency_hz >= lowest_slave_mode_frequency_hz:
            findings.append(
                f"target frequency {target_frequency_hz:.2f} Hz is at or above "
                f"the lowest slave-mode frequency "
                f"{lowest_slave_mode_frequency_hz:.2f} Hz; "
                "Guyan accuracy is inadequate in this range — "
                "consider Craig-Bampton"
            )

    if mass_fractional_error > MASS_ACCURACY_LIMIT:
        findings.append(
            f"mass fractional error {mass_fractional_error:.4f} "
            f"exceeds limit {MASS_ACCURACY_LIMIT:.4f}"
        )

    return findings


def check_residual_flexibility(
    target_frequency_hz: float,
    max_retained_mode_frequency_hz: float,
    residual_flexibility_applied: bool,
) -> list:
    """Determine whether residual flexibility correction is required and applied.

    When the retained mode set does not reach the required frequency cutoff,
    residual flexibility correction is mandatory; its absence is flagged.
    Returns a list of finding strings (empty → compliant).
    """
    if target_frequency_hz <= 0:
        return []

    required_cutoff = target_frequency_hz * INTERNAL_MODE_FREQ_MARGIN
    if (max_retained_mode_frequency_hz < required_cutoff
            and not residual_flexibility_applied):
        return [
            "retained mode set does not reach the required frequency cutoff "
            "and residual flexibility correction is not applied; "
            "truncated modal mass and stiffness are unaccounted for"
        ]
    return []


# ── Categorization helper ─────────────────────────────────────────────────────

def categorize_method_from_properties(
    boundary_fixed: bool,
    dynamic_modes_retained: bool,
) -> str:
    """Derive the reduction method category from model construction properties.

    boundary_fixed=True,  dynamic_modes_retained=True  → 'craig_bampton'
    boundary_fixed=True,  dynamic_modes_retained=False → 'guyan'
    boundary_fixed=False                               → 'free_interface'

    Returns the method string; does not raise.
    """
    if not boundary_fixed:
        return "free_interface"
    if dynamic_modes_retained:
        return "craig_bampton"
    return "guyan"


# ── Top-level assessment ──────────────────────────────────────────────────────

def assess_reduced_model(spec: dict) -> dict:
    """Top-level assessment of a reduced-model specification.

    Required spec keys:
      method (str)                    — 'craig_bampton', 'guyan', 'superelement'
      interface_nodes (list of dicts) — boundary node/DOF definitions
      mass_fractional_error (float)   — |m_red - m_full| / m_full
      target_frequency_hz (float)

    Craig-Bampton additional keys:
      boundary_dof_count (int)
      internal_mode_count (int)
      max_retained_mode_frequency_hz (float)
      frequency_fractional_error (float)
      residual_flexibility_applied (bool)

    Guyan additional keys:
      total_dof_count (int)
      master_dof_count (int)
      lowest_slave_mode_frequency_hz (float)

    Returns:
      {'compliant': bool, 'findings': list[str]}
    """
    findings = []

    method_raw = spec.get("method", "")
    try:
        method = check_reduction_method(method_raw)
    except ReducedModelError as exc:
        return {"compliant": False, "findings": [str(exc)]}

    findings.extend(check_interface_nodes(spec.get("interface_nodes", [])))

    if method == "craig_bampton":
        findings.extend(
            check_craig_bampton(
                boundary_dof_count=spec.get("boundary_dof_count", 0),
                internal_mode_count=spec.get("internal_mode_count", 0),
                target_frequency_hz=spec.get("target_frequency_hz", 0.0),
                max_retained_mode_frequency_hz=spec.get(
                    "max_retained_mode_frequency_hz", 0.0
                ),
                mass_fractional_error=spec.get("mass_fractional_error", 0.0),
                frequency_fractional_error=spec.get(
                    "frequency_fractional_error", 0.0
                ),
            )
        )
        findings.extend(
            check_residual_flexibility(
                target_frequency_hz=spec.get("target_frequency_hz", 0.0),
                max_retained_mode_frequency_hz=spec.get(
                    "max_retained_mode_frequency_hz", 0.0
                ),
                residual_flexibility_applied=spec.get(
                    "residual_flexibility_applied", False
                ),
            )
        )

    elif method == "guyan":
        findings.extend(
            check_guyan(
                total_dof_count=spec.get("total_dof_count", 0),
                master_dof_count=spec.get("master_dof_count", 0),
                target_frequency_hz=spec.get("target_frequency_hz", 0.0),
                lowest_slave_mode_frequency_hz=spec.get(
                    "lowest_slave_mode_frequency_hz", 0.0
                ),
                mass_fractional_error=spec.get("mass_fractional_error", 0.0),
            )
        )

    elif method == "superelement":
        mass_err = spec.get("mass_fractional_error", 0.0)
        if mass_err > MASS_ACCURACY_LIMIT:
            findings.append(
                f"superelement mass fractional error {mass_err:.4f} "
                f"exceeds limit {MASS_ACCURACY_LIMIT:.4f}"
            )

    return {"compliant": len(findings) == 0, "findings": findings}

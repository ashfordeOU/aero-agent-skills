#!/usr/bin/env python3
"""ECSS-E-ST-32C section 5.5 static analysis acceptance checks (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a linear
static finite-element analysis must satisfy three acceptance criteria before
its results are used for structural sizing. (1) Reaction equilibrium: the
vector sum of applied loads and support reaction forces must be near zero in
every degree of freedom, confirming that the model transmits load correctly
to its supports. (2) Energy balance: external work done by the applied loads
must equal the internal strain energy stored in the structure within a
prescribed relative tolerance, confirming that no energy is spuriously created
or lost by the solver or element formulation. (3) Solver convergence: the
dimensionless residual norm ||K u - F|| / ||F|| must fall below a prescribed
threshold, confirming that the linear system was solved to adequate accuracy.
All three criteria are evaluated independently; a run is accepted only when
every criterion returns PASS.
"""

PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"

DEFAULT_REACTION_TOLERANCE_PCT = 1.0
DEFAULT_ENERGY_TOLERANCE_PCT = 1.0
DEFAULT_CONVERGENCE_TOLERANCE = 1e-6


def _make_result(name, status, message, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details if details is not None else {},
    }


def _validate_tolerance_pct(tol_pct, label):
    if not (0.0 < tol_pct < 100.0):
        raise ValueError("%s must be in (0, 100), got %r" % (label, tol_pct))


def check_reactions(applied_forces, reaction_forces,
                    tolerance_pct=DEFAULT_REACTION_TOLERANCE_PCT):
    """Verify reaction equilibrium per ECSS-E-ST-32C §5.5.

    For each component i: residual[i] = applied_forces[i] + reaction_forces[i].
    The check passes when max(|residual[i]|) / scale <= tolerance_pct / 100,
    where scale = max absolute value across both vectors.

    Returns a result dict with keys: name, status, message, details.
    Returns ERROR for empty or mismatched inputs and invalid tolerance.
    """
    if not applied_forces:
        return _make_result("reactions", ERROR, "applied_forces list is empty")

    if len(applied_forces) != len(reaction_forces):
        return _make_result(
            "reactions", ERROR,
            "Length mismatch: applied_forces has %d entries, "
            "reaction_forces has %d" % (len(applied_forces), len(reaction_forces)),
        )

    try:
        _validate_tolerance_pct(tolerance_pct, "tolerance_pct")
    except ValueError as exc:
        return _make_result("reactions", ERROR, str(exc))

    residuals = [a + r for a, r in zip(applied_forces, reaction_forces)]
    all_values = list(applied_forces) + list(reaction_forces)
    scale = max(abs(v) for v in all_values)

    if scale == 0.0:
        return _make_result(
            "reactions", PASS,
            "All applied and reaction forces are zero — trivially balanced.",
            {"residuals": residuals, "scale": scale},
        )

    tol = tolerance_pct / 100.0
    max_rel_residual = max(abs(r) / scale for r in residuals)

    details = {
        "residuals": residuals,
        "max_rel_residual": max_rel_residual,
        "tolerance": tol,
        "scale": scale,
    }

    if max_rel_residual <= tol:
        return _make_result(
            "reactions", PASS,
            "Reaction equilibrium satisfied: max relative residual %.4e <= %.4e"
            % (max_rel_residual, tol),
            details,
        )
    return _make_result(
        "reactions", FAIL,
        "Reaction equilibrium violated: max relative residual %.4e > %.4e"
        % (max_rel_residual, tol),
        details,
    )


def check_energy_balance(external_work, strain_energy,
                         tolerance_pct=DEFAULT_ENERGY_TOLERANCE_PCT):
    """Verify energy balance per ECSS-E-ST-32C §5.5.

    Relative error = |W_ext - U_strain| / |U_strain|.
    The check passes when relative_error <= tolerance_pct / 100.
    Both external_work and strain_energy must be >= 0 for a valid
    linear static solution.

    Returns a result dict with keys: name, status, message, details.
    Returns ERROR for negative inputs or invalid tolerance.
    """
    try:
        _validate_tolerance_pct(tolerance_pct, "tolerance_pct")
    except ValueError as exc:
        return _make_result("energy_balance", ERROR, str(exc))

    if external_work < 0.0:
        return _make_result(
            "energy_balance", ERROR,
            "external_work must be >= 0, got %r" % external_work,
        )
    if strain_energy < 0.0:
        return _make_result(
            "energy_balance", ERROR,
            "strain_energy must be >= 0, got %r" % strain_energy,
        )

    if strain_energy == 0.0:
        if external_work == 0.0:
            return _make_result(
                "energy_balance", PASS,
                "Both external work and strain energy are zero — trivially balanced.",
                {"external_work": external_work, "strain_energy": strain_energy},
            )
        return _make_result(
            "energy_balance", FAIL,
            "Strain energy is zero but external work is %r; "
            "energy balance cannot be satisfied." % external_work,
            {"external_work": external_work, "strain_energy": strain_energy},
        )

    rel_error = abs(external_work - strain_energy) / abs(strain_energy)
    tol = tolerance_pct / 100.0

    details = {
        "external_work": external_work,
        "strain_energy": strain_energy,
        "relative_error": rel_error,
        "tolerance": tol,
    }

    if rel_error <= tol:
        return _make_result(
            "energy_balance", PASS,
            "Energy balance satisfied: relative error %.4e <= %.4e" % (rel_error, tol),
            details,
        )
    return _make_result(
        "energy_balance", FAIL,
        "Energy balance violated: relative error %.4e > %.4e" % (rel_error, tol),
        details,
    )


def check_solver_convergence(residual_norm,
                              tolerance=DEFAULT_CONVERGENCE_TOLERANCE):
    """Verify solver convergence per ECSS-E-ST-32C §5.5.

    residual_norm is the dimensionless ratio ||K u - F|| / ||F||.
    The check passes when residual_norm <= tolerance.

    Returns a result dict with keys: name, status, message, details.
    Returns ERROR for negative residual or non-positive tolerance.
    """
    if residual_norm < 0.0:
        return _make_result(
            "convergence", ERROR,
            "residual_norm must be >= 0, got %r" % residual_norm,
        )
    if tolerance <= 0.0:
        return _make_result(
            "convergence", ERROR,
            "tolerance must be > 0, got %r" % tolerance,
        )

    details = {"residual_norm": residual_norm, "tolerance": tolerance}

    if residual_norm <= tolerance:
        return _make_result(
            "convergence", PASS,
            "Solver converged: residual %.4e <= %.4e" % (residual_norm, tolerance),
            details,
        )
    return _make_result(
        "convergence", FAIL,
        "Solver did not converge: residual %.4e > %.4e" % (residual_norm, tolerance),
        details,
    )


def run_static_analysis_checks(model_data):
    """Run all three ECSS-E-ST-32C §5.5 static analysis checks from model_data.

    Required keys in model_data:
      applied_forces   : list[float]  — applied load components
      reaction_forces  : list[float]  — support reaction components (same length)
      external_work    : float        — external work from solver summary
      strain_energy    : float        — total strain energy from solver summary
      residual_norm    : float        — dimensionless solver residual ||Ku-F||/||F||

    Optional keys:
      reaction_tol_pct  : float  (default 1.0)
      energy_tol_pct    : float  (default 1.0)
      convergence_tol   : float  (default 1e-6)

    Returns a list of result dicts (one per criterion), or a single ERROR
    result if required keys are missing.
    """
    required = ["applied_forces", "reaction_forces",
                "external_work", "strain_energy", "residual_norm"]
    missing = [k for k in required if k not in model_data]
    if missing:
        return [_make_result(
            "run_all", ERROR,
            "Missing required keys: %r" % missing,
        )]

    return [
        check_reactions(
            model_data["applied_forces"],
            model_data["reaction_forces"],
            model_data.get("reaction_tol_pct", DEFAULT_REACTION_TOLERANCE_PCT),
        ),
        check_energy_balance(
            model_data["external_work"],
            model_data["strain_energy"],
            model_data.get("energy_tol_pct", DEFAULT_ENERGY_TOLERANCE_PCT),
        ),
        check_solver_convergence(
            model_data["residual_norm"],
            model_data.get("convergence_tol", DEFAULT_CONVERGENCE_TOLERANCE),
        ),
    ]


def all_checks_pass(results):
    """Return True when every result in a run_static_analysis_checks list is PASS."""
    return all(r["status"] == PASS for r in results)

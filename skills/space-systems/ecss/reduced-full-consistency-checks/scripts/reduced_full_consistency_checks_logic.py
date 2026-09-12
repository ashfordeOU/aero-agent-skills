"""
Reduced vs full FEM consistency checks — ECSS-E-ST-32C clause 5.8.

Implements deterministic, offline checks for four consistency categories:
  1. Mass properties (total mass, CG, inertia tensor)
  2. Natural frequencies (per retained mode)
  3. Modal Assurance Criterion (MAC) for interface modes
  4. Static stiffness at boundary DOFs

All inputs are plain Python numbers/lists/dicts. No third-party dependencies.
"""

import math


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dot(v1, v2):
    """Dot product of two equal-length sequences."""
    if len(v1) != len(v2):
        raise ValueError(
            f"Mode-shape vectors must have equal length: {len(v1)} vs {len(v2)}"
        )
    return sum(a * b for a, b in zip(v1, v2))


def _norm_sq(v):
    """Squared Euclidean norm."""
    return sum(x * x for x in v)


def _pct_diff(reference, value):
    """Signed percentage difference relative to reference (reference != 0)."""
    if reference == 0.0:
        raise ValueError("Reference value must be non-zero for percentage comparison.")
    return (value - reference) / abs(reference) * 100.0


def _euclidean_distance(a, b):
    """Euclidean distance between two equal-length coordinate sequences."""
    if len(a) != len(b):
        raise ValueError(
            f"Coordinate vectors must have equal length: {len(a)} vs {len(b)}"
        )
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ---------------------------------------------------------------------------
# 1. Mass properties
# ---------------------------------------------------------------------------

def compare_mass(full_mass, reduced_mass, tolerance_pct):
    """
    Compare total mass between full FEM and reduced model.

    Returns a dict:
      passed      : bool — True when |delta_pct| <= tolerance_pct
      delta_pct   : float — signed % deviation (reduced - full) / |full|
      full_mass   : float
      reduced_mass: float
      tolerance_pct: float
    """
    if full_mass <= 0:
        raise ValueError("full_mass must be positive.")
    if reduced_mass < 0:
        raise ValueError("reduced_mass must be non-negative.")
    if tolerance_pct < 0:
        raise ValueError("tolerance_pct must be non-negative.")

    delta = _pct_diff(full_mass, reduced_mass)
    return {
        "passed": abs(delta) <= tolerance_pct,
        "delta_pct": delta,
        "full_mass": full_mass,
        "reduced_mass": reduced_mass,
        "tolerance_pct": tolerance_pct,
    }


def compare_cg(full_cg, reduced_cg, tolerance_m):
    """
    Compare centre-of-gravity position vectors (3-element sequences, metres).

    Returns a dict:
      passed     : bool — True when Euclidean distance <= tolerance_m
      distance_m : float
      full_cg    : list
      reduced_cg : list
      tolerance_m: float
    """
    if len(full_cg) != 3 or len(reduced_cg) != 3:
        raise ValueError("CG vectors must each have exactly 3 components (x, y, z).")
    if tolerance_m < 0:
        raise ValueError("tolerance_m must be non-negative.")

    dist = _euclidean_distance(full_cg, reduced_cg)
    return {
        "passed": dist <= tolerance_m,
        "distance_m": dist,
        "full_cg": list(full_cg),
        "reduced_cg": list(reduced_cg),
        "tolerance_m": tolerance_m,
    }


def compare_inertia(full_inertia, reduced_inertia, tolerance_pct):
    """
    Compare inertia tensor components between full FEM and reduced model.

    full_inertia / reduced_inertia : dicts with keys
        "Ixx", "Iyy", "Izz", "Ixy", "Ixz", "Iyz"  (kg·m²)

    Returns a dict:
      passed      : bool — True when ALL |delta_pct| <= tolerance_pct
      components  : dict mapping each key to {"delta_pct": float, "passed": bool}
    """
    required_keys = ("Ixx", "Iyy", "Izz", "Ixy", "Ixz", "Iyz")
    for k in required_keys:
        if k not in full_inertia:
            raise ValueError(f"full_inertia missing key '{k}'.")
        if k not in reduced_inertia:
            raise ValueError(f"reduced_inertia missing key '{k}'.")

    components = {}
    all_pass = True
    for k in required_keys:
        ref = full_inertia[k]
        val = reduced_inertia[k]
        if ref == 0.0:
            delta = 0.0 if val == 0.0 else float("inf")
        else:
            delta = _pct_diff(ref, val)
        ok = abs(delta) <= tolerance_pct
        components[k] = {"delta_pct": delta, "passed": ok}
        if not ok:
            all_pass = False

    return {"passed": all_pass, "components": components, "tolerance_pct": tolerance_pct}


# ---------------------------------------------------------------------------
# 2. Natural frequencies
# ---------------------------------------------------------------------------

def compare_frequencies(full_freqs, reduced_freqs, tolerance_pct):
    """
    Compare paired natural frequencies (Hz).

    full_freqs / reduced_freqs : lists of floats, same length, same ordering.

    Returns a list of dicts, one per mode:
      mode_index   : int (0-based)
      full_freq_hz : float
      reduced_freq_hz : float
      delta_pct    : float
      passed       : bool
    """
    if len(full_freqs) != len(reduced_freqs):
        raise ValueError(
            "full_freqs and reduced_freqs must have the same number of modes."
        )
    if tolerance_pct < 0:
        raise ValueError("tolerance_pct must be non-negative.")

    results = []
    for i, (ff, rf) in enumerate(zip(full_freqs, reduced_freqs)):
        if ff <= 0:
            raise ValueError(f"Mode {i}: full frequency must be positive, got {ff}.")
        delta = _pct_diff(ff, rf)
        results.append(
            {
                "mode_index": i,
                "full_freq_hz": ff,
                "reduced_freq_hz": rf,
                "delta_pct": delta,
                "passed": abs(delta) <= tolerance_pct,
            }
        )
    return results


# ---------------------------------------------------------------------------
# 3. Modal Assurance Criterion (MAC)
# ---------------------------------------------------------------------------

def compute_mac(mode_a, mode_b):
    """
    Compute the MAC scalar between two mode-shape vectors.

    mode_a, mode_b : equal-length sequences of floats (interface-DOF amplitudes).

    Returns a float in [0.0, 1.0].  Returns 0.0 if either vector is a zero vector.
    """
    norm_a = _norm_sq(mode_a)
    norm_b = _norm_sq(mode_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    numerator = _dot(mode_a, mode_b) ** 2
    return numerator / (norm_a * norm_b)


def build_mac_matrix(full_modes, reduced_modes):
    """
    Build the full MAC matrix (n_full × n_reduced).

    full_modes    : list of mode-shape vectors from the full FEM.
    reduced_modes : list of mode-shape vectors from the reduced model.

    Returns a list of lists (row = full mode, column = reduced mode).
    """
    return [
        [compute_mac(fm, rm) for rm in reduced_modes]
        for fm in full_modes
    ]


def check_mac_diagonal(mac_matrix, mac_threshold, n_modes):
    """
    Evaluate diagonal and off-diagonal MAC entries for n_modes paired modes.

    mac_matrix    : list of lists produced by build_mac_matrix.
    mac_threshold : minimum acceptable MAC on the diagonal (e.g. 0.9).
    n_modes       : number of modes to inspect (must be ≤ min(rows, cols)).

    Returns a list of finding dicts:
      mode_index     : int
      mac_value      : float
      check_type     : "diagonal" or "off_diagonal"
      passed         : bool
    """
    findings = []
    for i in range(n_modes):
        diag_val = mac_matrix[i][i]
        findings.append(
            {
                "mode_index": i,
                "mac_value": diag_val,
                "check_type": "diagonal",
                "passed": diag_val >= mac_threshold,
            }
        )
        for j in range(n_modes):
            if j == i:
                continue
            off_val = mac_matrix[i][j]
            if off_val >= mac_threshold:
                findings.append(
                    {
                        "mode_index_row": i,
                        "mode_index_col": j,
                        "mac_value": off_val,
                        "check_type": "off_diagonal",
                        "passed": False,
                    }
                )
    return findings


# ---------------------------------------------------------------------------
# 4. Static stiffness at interface DOFs
# ---------------------------------------------------------------------------

def compare_static_stiffness(full_stiffness, reduced_stiffness, tolerance_pct):
    """
    Compare diagonal static stiffness values at interface DOFs (N/m or N·m/rad).

    full_stiffness / reduced_stiffness : lists of floats, same length.

    Returns a list of dicts, one per DOF:
      dof_index         : int (0-based)
      full_stiffness    : float
      reduced_stiffness : float
      delta_pct         : float
      passed            : bool
    """
    if len(full_stiffness) != len(reduced_stiffness):
        raise ValueError(
            "full_stiffness and reduced_stiffness must have the same number of DOFs."
        )
    if tolerance_pct < 0:
        raise ValueError("tolerance_pct must be non-negative.")

    results = []
    for i, (fk, rk) in enumerate(zip(full_stiffness, reduced_stiffness)):
        if fk <= 0:
            raise ValueError(
                f"DOF {i}: full stiffness must be positive, got {fk}."
            )
        delta = _pct_diff(fk, rk)
        results.append(
            {
                "dof_index": i,
                "full_stiffness": fk,
                "reduced_stiffness": rk,
                "delta_pct": delta,
                "passed": abs(delta) <= tolerance_pct,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_consistency_checks(full_model, reduced_model, criteria):
    """
    Run all four consistency checks and return a consolidated report.

    full_model / reduced_model : dicts with keys:
        "mass"          : float (kg)
        "cg"            : list of 3 floats (m)
        "inertia"       : dict with keys Ixx Iyy Izz Ixy Ixz Iyz (kg·m²)
        "frequencies"   : list of floats (Hz), one per retained mode
        "mode_shapes"   : list of lists (each inner list = interface-DOF amplitudes)
        "static_stiffness" : list of floats (N/m or N·m/rad), one per interface DOF

    criteria : dict with keys:
        "mass_tolerance_pct"       : float  (e.g. 2.0)
        "cg_tolerance_m"           : float  (e.g. 0.005)
        "inertia_tolerance_pct"    : float  (e.g. 2.0)
        "freq_tolerance_pct"       : float  (e.g. 3.0)
        "mac_threshold"            : float  (e.g. 0.9)
        "stiffness_tolerance_pct"  : float  (e.g. 5.0)

    Returns a dict:
        "overall_passed"   : bool — True only if every sub-check passes
        "mass"             : result of compare_mass
        "cg"               : result of compare_cg
        "inertia"          : result of compare_inertia
        "frequencies"      : list from compare_frequencies
        "mac_findings"     : list from check_mac_diagonal
        "static_stiffness" : list from compare_static_stiffness
        "summary"          : dict counting passes and failures per category
    """
    mass_result = compare_mass(
        full_model["mass"],
        reduced_model["mass"],
        criteria["mass_tolerance_pct"],
    )

    cg_result = compare_cg(
        full_model["cg"],
        reduced_model["cg"],
        criteria["cg_tolerance_m"],
    )

    inertia_result = compare_inertia(
        full_model["inertia"],
        reduced_model["inertia"],
        criteria["inertia_tolerance_pct"],
    )

    freq_results = compare_frequencies(
        full_model["frequencies"],
        reduced_model["frequencies"],
        criteria["freq_tolerance_pct"],
    )

    n_modes = len(full_model["mode_shapes"])
    mac_matrix = build_mac_matrix(
        full_model["mode_shapes"],
        reduced_model["mode_shapes"],
    )
    mac_findings = check_mac_diagonal(mac_matrix, criteria["mac_threshold"], n_modes)

    stiffness_results = compare_static_stiffness(
        full_model["static_stiffness"],
        reduced_model["static_stiffness"],
        criteria["stiffness_tolerance_pct"],
    )

    freq_pass = all(r["passed"] for r in freq_results)
    mac_pass = all(r["passed"] for r in mac_findings)
    stiffness_pass = all(r["passed"] for r in stiffness_results)

    overall = (
        mass_result["passed"]
        and cg_result["passed"]
        and inertia_result["passed"]
        and freq_pass
        and mac_pass
        and stiffness_pass
    )

    summary = {
        "mass_passed": mass_result["passed"],
        "cg_passed": cg_result["passed"],
        "inertia_passed": inertia_result["passed"],
        "frequencies_passed": freq_pass,
        "mac_passed": mac_pass,
        "static_stiffness_passed": stiffness_pass,
        "freq_failures": sum(1 for r in freq_results if not r["passed"]),
        "mac_failures": sum(1 for r in mac_findings if not r["passed"]),
        "stiffness_failures": sum(1 for r in stiffness_results if not r["passed"]),
    }

    return {
        "overall_passed": overall,
        "mass": mass_result,
        "cg": cg_result,
        "inertia": inertia_result,
        "frequencies": freq_results,
        "mac_findings": mac_findings,
        "static_stiffness": stiffness_results,
        "summary": summary,
    }

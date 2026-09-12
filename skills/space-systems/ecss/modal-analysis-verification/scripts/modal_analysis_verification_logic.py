#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.2.4 modal analysis verification
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS structural requirements standard's modal analysis clause requires
that natural frequencies computed by the structural dynamic model meet
or exceed project-specified minimum frequency requirements for each
structural axis; that the fundamental frequency per axis is the lowest
natural frequency among modes carrying non-zero effective mass in that
axis; and that cumulative effective mass participation across retained
modes reaches a project-required threshold (commonly 90%) confirming
the modal extraction is sufficiently complete to bound the frequency
result. This module implements fundamental frequency extraction per
axis, frequency margin calculation, cumulative effective mass
participation assessment, and the aggregated compliance verdict; it
does not define the numeric frequency requirements or mass
participation thresholds — those come from the project interface
control document and coupled loads analysis.
"""

STRUCTURAL_AXES = frozenset({"lateral_x", "lateral_y", "axial_z"})

DEFAULT_MASS_PARTICIPATION_THRESHOLD = 0.90


def _validate_axis(axis):
    if axis not in STRUCTURAL_AXES:
        raise ValueError(
            "unrecognized structural axis %r; expected one of %s"
            % (axis, sorted(STRUCTURAL_AXES))
        )


def compute_frequency_margin(mode_frequency_hz, required_min_hz):
    """Fractional frequency margin: (f_mode / f_required) - 1.0.
    Positive means above the requirement; negative means a violation.
    Raises ValueError for non-positive inputs."""
    if mode_frequency_hz <= 0.0:
        raise ValueError("mode_frequency_hz must be > 0; got %r" % (mode_frequency_hz,))
    if required_min_hz <= 0.0:
        raise ValueError("required_min_hz must be > 0; got %r" % (required_min_hz,))
    return (mode_frequency_hz / required_min_hz) - 1.0


def fundamental_frequency(modes, axis):
    """Lowest natural frequency among all modes with non-zero effective mass
    in axis. Returns None if no mode contributes effective mass in that axis.
    Raises ValueError for an unrecognized axis."""
    _validate_axis(axis)
    candidates = [
        m["frequency_hz"]
        for m in modes
        if m.get("effective_mass_fraction", {}).get(axis, 0.0) > 0.0
    ]
    return min(candidates) if candidates else None


def check_frequency_requirement(modes, axis, required_min_hz):
    """Frequency requirement check for one axis.

    Returns a dict with keys 'axis', 'fundamental_hz', 'required_min_hz',
    'margin', 'compliant', and optionally 'issue'. When no mode carries
    effective mass in the axis the result has fundamental_hz=None,
    margin=None, compliant=False, and issue='no_mode_with_effective_mass_in_axis'.
    Raises ValueError for an unrecognized axis or non-positive required_min_hz."""
    _validate_axis(axis)
    if required_min_hz <= 0.0:
        raise ValueError("required_min_hz must be > 0; got %r" % (required_min_hz,))
    f_fund = fundamental_frequency(modes, axis)
    if f_fund is None:
        return {
            "axis": axis,
            "fundamental_hz": None,
            "required_min_hz": required_min_hz,
            "margin": None,
            "compliant": False,
            "issue": "no_mode_with_effective_mass_in_axis",
        }
    margin = compute_frequency_margin(f_fund, required_min_hz)
    result = {
        "axis": axis,
        "fundamental_hz": f_fund,
        "required_min_hz": required_min_hz,
        "margin": margin,
        "compliant": margin >= 0.0,
    }
    if not result["compliant"]:
        result["issue"] = "frequency_requirement_violated"
    return result


def check_mass_participation(modes, axis, threshold=DEFAULT_MASS_PARTICIPATION_THRESHOLD):
    """Cumulative effective mass participation check for one axis.

    Sums effective_mass_fraction across all modes for the axis and checks
    the cumulative total reaches threshold. Returns a dict with keys 'axis',
    'cumulative_fraction', 'threshold', 'compliant'. Raises ValueError for
    an unrecognized axis or a threshold outside (0, 1]."""
    _validate_axis(axis)
    if not (0.0 < threshold <= 1.0):
        raise ValueError(
            "threshold must be in (0, 1]; got %r" % (threshold,)
        )
    total = sum(
        m.get("effective_mass_fraction", {}).get(axis, 0.0) for m in modes
    )
    result = {
        "axis": axis,
        "cumulative_fraction": total,
        "threshold": threshold,
        "compliant": total >= threshold,
    }
    if not result["compliant"]:
        result["issue"] = "insufficient_mass_participation"
    return result


def verify_modal_analysis(
    modes, frequency_requirements, mass_participation_threshold=DEFAULT_MASS_PARTICIPATION_THRESHOLD
):
    """Full modal analysis verification per ECSS-E-ST-32C clause 4.6.2.4.

    modes: list of dicts, each containing:
        "mode_id": str
        "frequency_hz": float (> 0)
        "effective_mass_fraction": dict mapping axis name -> fraction (0..1)
    frequency_requirements: dict mapping axis name -> required_min_hz (> 0)
    mass_participation_threshold: minimum cumulative effective mass fraction
        required in each axis (default 0.90). Must be in (0, 1].

    Returns:
        {
            "frequency_checks": [...],         # one entry per axis
            "mass_participation_checks": [...], # one entry per axis
            "compliant": bool                  # True only when all checks pass
        }

    Raises ValueError for unrecognized axes, non-positive frequencies, or
    an invalid threshold. Does not mutate the input lists or dicts."""
    freq_checks = []
    mass_checks = []
    for axis, req_hz in frequency_requirements.items():
        freq_checks.append(check_frequency_requirement(modes, axis, req_hz))
        mass_checks.append(
            check_mass_participation(modes, axis, mass_participation_threshold)
        )
    all_compliant = all(c["compliant"] for c in freq_checks + mass_checks)
    return {
        "frequency_checks": freq_checks,
        "mass_participation_checks": mass_checks,
        "compliant": all_compliant,
    }

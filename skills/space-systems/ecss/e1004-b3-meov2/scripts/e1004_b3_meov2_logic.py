#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.3 ONERA MEOv2 trapped-electron flux model
logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): MEOv2
is an ONERA trapped-electron model built for the medium-Earth-orbit
(GNSS/navigation-orbit-class) region. It expresses differential
electron flux as a function of energy and McIlwain L-shell: flux falls
off with energy following a smooth spectral form (an exponential
roll-off set by a reference flux level and a characteristic e-folding
energy), and both of those spectral parameters vary with L-shell. The
model data is only defined at a discrete L-shell grid, so applying it
to a real orbit requires interpolating the grid to the L-shell values
the orbit actually visits, then combining the per-L-shell flux across
the orbit's L-shell trace. The reference grid values used here are
illustrative placeholders for exercising this procedure, not a
reproduction of the ECSS Annex B.3 data tables. This module implements
the L-shell validation, grid interpolation, spectral-form evaluation,
and orbit-combination logic only; it does not derive an orbit's
L-shell trace from ephemeris (see the sibling e1004-geomag leaf) or
the higher-level GNSS-orbit model-selection workflow (see the sibling
e1004-meo-meov2 leaf).
"""

import math

MEO_L_SHELL_MIN = 2.0
MEO_L_SHELL_MAX = 7.0

# Illustrative L-shell reference grid: (L_shell, reference differential
# flux in cm^-2 s^-1 sr^-1 MeV^-1 at zero energy, e-folding energy in
# MeV). Nodes must be strictly increasing in L_shell.
L_SHELL_GRID = (
    (2.0, 1.0e5, 0.30),
    (3.0, 5.0e4, 0.50),
    (4.0, 2.0e4, 0.70),
    (5.0, 8.0e3, 0.90),
    (6.0, 3.0e3, 1.10),
    (7.0, 1.0e3, 1.30),
)


def validate_l_shell(l_shell):
    """Raises ValueError when l_shell is outside MEOv2's valid range
    [MEO_L_SHELL_MIN, MEO_L_SHELL_MAX]."""
    if l_shell < MEO_L_SHELL_MIN or l_shell > MEO_L_SHELL_MAX:
        raise ValueError(
            "L-shell %r outside MEOv2 valid range [%r, %r]"
            % (l_shell, MEO_L_SHELL_MIN, MEO_L_SHELL_MAX)
        )


def l_shell_in_range(l_shell):
    """True when l_shell falls within MEOv2's valid range, without
    raising."""
    return MEO_L_SHELL_MIN <= l_shell <= MEO_L_SHELL_MAX


def _interpolate(x, x0, y0, x1, y1):
    """Linear interpolation of y at x between (x0, y0) and (x1, y1)."""
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def interpolate_spectral_params(l_shell):
    """Interpolate the L-shell reference grid to l_shell, returning a
    (reference_flux, e_folding_energy_mev) tuple. Raises ValueError
    when l_shell is outside the grid's valid range."""
    validate_l_shell(l_shell)
    grid = L_SHELL_GRID
    for i in range(len(grid) - 1):
        l0, j0, e0 = grid[i]
        l1, j1, e1 = grid[i + 1]
        if l0 <= l_shell <= l1:
            reference_flux = _interpolate(l_shell, l0, j0, l1, j1)
            e_folding_energy = _interpolate(l_shell, l0, e0, l1, e1)
            return reference_flux, e_folding_energy
    # l_shell equals the last grid node exactly (loop above covers
    # [l0, l1] pairs, so only the final node itself can fall through).
    last_l, last_j0, last_e0 = grid[-1]
    if l_shell == last_l:
        return last_j0, last_e0
    raise ValueError("L-shell %r not covered by the reference grid" % (l_shell,))


def differential_flux(energy_mev, l_shell):
    """Differential electron flux at energy_mev and l_shell, using the
    model's exponential spectral form with L-shell-interpolated
    parameters. Raises ValueError for a negative energy or an
    out-of-range l_shell."""
    if energy_mev < 0:
        raise ValueError("energy must not be negative")
    reference_flux, e_folding_energy = interpolate_spectral_params(l_shell)
    return reference_flux * math.exp(-energy_mev / e_folding_energy)


def integral_flux_above(energy_threshold_mev, l_shell):
    """Integral electron flux above energy_threshold_mev at l_shell,
    obtained analytically from the exponential spectral form. Raises
    ValueError for a negative threshold or an out-of-range l_shell."""
    if energy_threshold_mev < 0:
        raise ValueError("energy threshold must not be negative")
    reference_flux, e_folding_energy = interpolate_spectral_params(l_shell)
    return reference_flux * e_folding_energy * math.exp(
        -energy_threshold_mev / e_folding_energy
    )


def orbit_average_flux(energy_mev, l_shell_samples, dwell_fractions=None):
    """Dwell-time-weighted average differential flux at energy_mev
    across an orbit's l_shell_samples. dwell_fractions, when given,
    must be the same length as l_shell_samples and sum to 1.0; equal
    weighting is used when omitted. Raises ValueError for an empty
    sample list, a length mismatch, or dwell fractions that do not sum
    to 1.0."""
    if not l_shell_samples:
        raise ValueError("l_shell_samples must not be empty")
    if dwell_fractions is None:
        weights = [1.0 / len(l_shell_samples)] * len(l_shell_samples)
    else:
        if len(dwell_fractions) != len(l_shell_samples):
            raise ValueError("dwell_fractions must match l_shell_samples in length")
        if abs(sum(dwell_fractions) - 1.0) > 1e-9:
            raise ValueError("dwell_fractions must sum to 1.0")
        weights = dwell_fractions
    return sum(
        weight * differential_flux(energy_mev, l_shell)
        for weight, l_shell in zip(weights, l_shell_samples)
    )


def worst_case_l_shell(energy_mev, l_shell_samples):
    """The l_shell in l_shell_samples giving the highest differential
    flux at energy_mev. Raises ValueError for an empty sample list."""
    if not l_shell_samples:
        raise ValueError("l_shell_samples must not be empty")
    return max(l_shell_samples, key=lambda l_shell: differential_flux(energy_mev, l_shell))


def assess_meov2_case(case):
    """Full MEOv2 spectral-evaluation and orbit-combination assessment
    for one case dict. Required keys: id, l_shell_samples, energy_mev.
    Optional key: dwell_fractions. Returns a new dict; does not mutate
    the input. Raises ValueError when 'id' is missing or
    l_shell_samples is empty."""
    if "id" not in case:
        raise ValueError("MEOv2 case is missing an id")
    l_shell_samples = case["l_shell_samples"]
    if not l_shell_samples:
        raise ValueError("MEOv2 case has no l_shell_samples")
    energy_mev = case["energy_mev"]
    dwell_fractions = case.get("dwell_fractions")
    in_range = [l_shell_in_range(l_shell) for l_shell in l_shell_samples]
    valid = all(in_range)
    result = {
        "id": case["id"],
        "l_shell_samples": list(l_shell_samples),
        "energy_mev": energy_mev,
        "l_shell_in_range": in_range,
        "valid": valid,
    }
    if valid:
        result["orbit_average_flux"] = orbit_average_flux(
            energy_mev, l_shell_samples, dwell_fractions
        )
        peak_l_shell = worst_case_l_shell(energy_mev, l_shell_samples)
        result["worst_case_l_shell"] = peak_l_shell
        result["worst_case_flux"] = differential_flux(energy_mev, peak_l_shell)
    else:
        result["orbit_average_flux"] = None
        result["worst_case_l_shell"] = None
        result["worst_case_flux"] = None
    return result


def build_meov2_assessment(cases):
    """Assessment record: one assess_meov2_case() result per case, in
    input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_meov2_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate MEOv2 case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def invalid_items(record):
    """Case ids in the record whose L-shell coverage is not entirely
    within MEOv2's valid range, in record order."""
    return [entry["id"] for entry in record if not entry["valid"]]


def all_valid(record):
    """True when every entry in the assessment record is valid."""
    return len(invalid_items(record)) == 0

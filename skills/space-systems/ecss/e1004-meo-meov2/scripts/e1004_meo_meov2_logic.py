"""ECSS-E-ST-10-04C Annex B.3 -- MEO trapped environment via MEOv2.

Representative (non-proprietary) implementation of the MEOv2 modeling
approach: bilinear, log-log spectral interpolation of trapped electron
and proton flux over McIlwain L-shell and kinetic energy, integrated
along an orbit that crosses multiple L-shells to produce an
orbit-averaged differential flux spectrum and mission fluence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


class Species:
    ELECTRON = "electron"
    PROTON = "proton"


# McIlwain L-shell grid spanning representative MEO crossings (Earth radii).
L_GRID: tuple[float, ...] = (1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 6.6, 8.0)

# Kinetic energy grid, MeV.
ENERGY_GRID: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)

# Representative log10(differential flux) tables [#/cm^2/s/MeV], indexed
# [L_index][E_index]. Values are illustrative figures reproducing the
# well-known electron slot/outer-belt double peak and inner-belt proton
# falloff with L; they are NOT digitized ONERA MEOv2 coefficients, which
# are proprietary and distributed only with licensed SPENVIS/OMERE tools.
ELECTRON_LOG_FLUX: tuple[tuple[float, ...], ...] = (
    (5.8, 5.0, 3.9, 2.6, 1.0, -0.6, -2.4),
    (6.2, 5.5, 4.5, 3.3, 1.8, 0.1, -1.6),
    (6.0, 5.4, 4.6, 3.6, 2.3, 0.7, -1.0),
    (5.4, 4.9, 4.2, 3.3, 2.1, 0.6, -1.1),
    (5.2, 4.8, 4.2, 3.4, 2.3, 0.8, -0.9),
    (5.9, 5.6, 5.1, 4.4, 3.4, 2.1, 0.4),
    (6.4, 6.1, 5.7, 5.1, 4.2, 3.0, 1.3),
    (6.1, 5.9, 5.5, 4.9, 4.1, 2.9, 1.2),
    (5.6, 5.4, 5.0, 4.4, 3.6, 2.5, 0.9),
    (4.2, 4.0, 3.6, 3.0, 2.2, 1.1, -0.4),
)

PROTON_LOG_FLUX: tuple[tuple[float, ...], ...] = (
    (5.0, 4.6, 3.8, 2.6, 0.9, -1.0, -3.4),
    (5.6, 5.2, 4.4, 3.2, 1.5, -0.5, -2.9),
    (5.9, 5.5, 4.6, 3.3, 1.5, -0.6, -3.1),
    (5.4, 5.0, 4.0, 2.6, 0.6, -1.6, -4.2),
    (4.6, 4.1, 3.0, 1.4, -0.8, -3.2, -6.0),
    (3.2, 2.6, 1.4, -0.4, -2.8, -5.6, -8.6),
    (2.0, 1.3, 0.0, -1.9, -4.5, -7.5, -10.7),
    (1.0, 0.2, -1.2, -3.3, -6.1, -9.3, -12.6),
    (0.4, -0.5, -2.0, -4.2, -7.1, -10.4, -13.8),
    (-1.2, -2.2, -3.9, -6.4, -9.6, -13.2, -16.8),
)

_TABLES = {
    Species.ELECTRON: ELECTRON_LOG_FLUX,
    Species.PROTON: PROTON_LOG_FLUX,
}

_VALID_SPECIES = frozenset(_TABLES)


@dataclass(frozen=True)
class LShellCrossing:
    """One segment of an MEO orbit ground track through L-shell space."""

    l_shell: float
    dwell_seconds: float


def _clamp(value: float, grid: Sequence[float]) -> float:
    return min(max(value, grid[0]), grid[-1])


def _bracket(value: float, grid: Sequence[float]) -> tuple[int, int, float]:
    """Return (lo_index, hi_index, fraction) for linear interpolation,
    clamping ``value`` to the grid range first."""
    clamped = _clamp(value, grid)
    for i in range(len(grid) - 1):
        if grid[i] <= clamped <= grid[i + 1]:
            span = grid[i + 1] - grid[i]
            frac = 0.0 if span == 0 else (clamped - grid[i]) / span
            return i, i + 1, frac
    last = len(grid) - 1
    return last - 1, last, 1.0


def interpolate_flux(species: str, l_shell: float, energy_mev: float) -> float:
    """Interpolate differential flux over L-shell and energy.

    Interpolation is linear in L against log10(flux), and log-log in
    energy, matching the MEOv2 convention of resolving the trapped
    spectrum smoothly as an orbit crosses L-shells. Out-of-range L or
    energy values are clamped to the nearest tabulated grid edge.
    """
    if species not in _VALID_SPECIES:
        raise ValueError(f"unknown species {species!r}; expected 'electron' or 'proton'")
    if energy_mev <= 0:
        raise ValueError("energy_mev must be positive")

    table = _TABLES[species]
    l_lo, l_hi, l_frac = _bracket(l_shell, L_GRID)

    log_e = math.log10(energy_mev)
    log_e_grid = [math.log10(e) for e in ENERGY_GRID]
    e_lo, e_hi, e_frac = _bracket(log_e, log_e_grid)

    def log_flux_at_l(row_index: int) -> float:
        row = table[row_index]
        return row[e_lo] * (1 - e_frac) + row[e_hi] * e_frac

    log_flux = log_flux_at_l(l_lo) * (1 - l_frac) + log_flux_at_l(l_hi) * l_frac
    return 10.0 ** log_flux


def orbit_averaged_spectrum(
    species: str,
    crossings: Sequence[LShellCrossing],
    energies_mev: Sequence[float] = ENERGY_GRID,
) -> dict[float, float]:
    """Compute the dwell-time-weighted differential flux spectrum for an
    MEO orbit that crosses multiple L-shells over one revolution."""
    if not crossings:
        raise ValueError("crossings must contain at least one L-shell segment")

    total_dwell = sum(c.dwell_seconds for c in crossings)
    if total_dwell <= 0:
        raise ValueError("total dwell time must be positive")

    spectrum: dict[float, float] = {}
    for energy in energies_mev:
        weighted = sum(
            interpolate_flux(species, c.l_shell, energy) * c.dwell_seconds
            for c in crossings
        )
        spectrum[energy] = weighted / total_dwell
    return spectrum


def integrate_fluence(
    species: str,
    crossings: Sequence[LShellCrossing],
    energy_mev: float,
    orbit_period_seconds: float,
    mission_duration_seconds: float,
) -> float:
    """Integrate the orbit-averaged differential flux into a mission fluence.

    fluence [#/cm^2/MeV] = average_flux [#/cm^2/s/MeV] * orbit_period_seconds
    * number_of_orbits, where number_of_orbits = mission_duration_seconds /
    orbit_period_seconds.
    """
    if orbit_period_seconds <= 0:
        raise ValueError("orbit_period_seconds must be positive")
    if mission_duration_seconds < 0:
        raise ValueError("mission_duration_seconds must not be negative")

    average_flux = orbit_averaged_spectrum(species, crossings, (energy_mev,))[energy_mev]
    n_orbits = mission_duration_seconds / orbit_period_seconds
    return average_flux * orbit_period_seconds * n_orbits


_SEVERITY_THRESHOLDS_ELECTRON: tuple[tuple[float, str], ...] = (
    (1.0e9, "benign"),
    (1.0e11, "elevated"),
    (math.inf, "severe"),
)
_SEVERITY_THRESHOLDS_PROTON: tuple[tuple[float, str], ...] = (
    (1.0e7, "benign"),
    (1.0e9, "elevated"),
    (math.inf, "severe"),
)


def categorize_severity(species: str, total_fluence: float) -> str:
    """Categorize total mission fluence into a qualitative severity band.

    Bands are illustrative screening thresholds for engineering triage,
    not an ECSS pass/fail verdict; downstream shielding analysis must
    confirm margins.
    """
    if species not in _VALID_SPECIES:
        raise ValueError(f"unknown species {species!r}; expected 'electron' or 'proton'")
    if total_fluence < 0:
        raise ValueError("total_fluence must not be negative")

    thresholds = (
        _SEVERITY_THRESHOLDS_ELECTRON
        if species == Species.ELECTRON
        else _SEVERITY_THRESHOLDS_PROTON
    )
    for limit, label in thresholds:
        if total_fluence <= limit:
            return label
    return "severe"

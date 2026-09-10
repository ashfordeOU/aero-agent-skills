"""
Worst-case trapped proton model (ECSS-E-ST-10-04C).

Combines AP-8 MIN/MAX (and an optional AP-9 percentile) differential flux
spectra into a single conservative envelope spectrum, and integrates it into
an integral flux spectrum for shielding/dose calculations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence


class TrappedProtonModelError(ValueError):
    """Raised when input spectra fail validation for the worst-case model."""


@dataclass(frozen=True)
class ProtonSpectrum:
    """A validated, immutable differential or integral proton flux spectrum."""

    energies_mev: tuple[float, ...]
    flux: tuple[float, ...]

    def __post_init__(self) -> None:
        _validate_spectrum(self.energies_mev, self.flux)


def _validate_spectrum(energies_mev: Sequence[float], flux: Sequence[float]) -> None:
    if len(energies_mev) == 0:
        raise TrappedProtonModelError("energy grid must contain at least one point")
    if len(energies_mev) != len(flux):
        raise TrappedProtonModelError(
            f"energy grid length ({len(energies_mev)}) must match flux length ({len(flux)})"
        )
    for previous, current in zip(energies_mev, energies_mev[1:]):
        if current <= previous:
            raise TrappedProtonModelError("energy grid must be strictly increasing")
    for energy, value in zip(energies_mev, flux):
        if energy <= 0 or not math.isfinite(energy):
            raise TrappedProtonModelError(f"energy values must be positive and finite, got {energy}")
        if value < 0 or not math.isfinite(value):
            raise TrappedProtonModelError(f"flux values must be non-negative and finite, got {value}")


def make_spectrum(energies_mev: Sequence[float], flux: Sequence[float]) -> ProtonSpectrum:
    """Build a validated ProtonSpectrum from raw energy/flux sequences."""
    return ProtonSpectrum(tuple(energies_mev), tuple(flux))


def _loglog_interpolate(spectrum: ProtonSpectrum, energy_mev: float) -> float:
    """Interpolate flux at energy_mev via log-log linear interpolation, clamped at the grid ends."""
    energies = spectrum.energies_mev
    flux = spectrum.flux

    if energy_mev <= energies[0]:
        return flux[0]
    if energy_mev >= energies[-1]:
        return flux[-1]

    for index in range(len(energies) - 1):
        low_e, high_e = energies[index], energies[index + 1]
        if low_e <= energy_mev <= high_e:
            # Exact node match: return the tabulated flux untouched so
            # grid points reproduce bit-for-bit (the exp/log path below
            # drifts by ~1e-11 even when fraction is exactly 0).
            if energy_mev == low_e:
                return flux[index]
            if energy_mev == high_e:
                return flux[index + 1]
            low_f, high_f = flux[index], flux[index + 1]
            if low_f <= 0 or high_f <= 0:
                fraction = (energy_mev - low_e) / (high_e - low_e)
                return low_f + fraction * (high_f - low_f)
            log_low_e, log_high_e = math.log(low_e), math.log(high_e)
            log_low_f, log_high_f = math.log(low_f), math.log(high_f)
            fraction = (math.log(energy_mev) - log_low_e) / (log_high_e - log_low_e)
            return math.exp(log_low_f + fraction * (log_high_f - log_low_f))

    raise TrappedProtonModelError(f"energy {energy_mev} MeV out of interpolation range")


def resample_spectrum(spectrum: ProtonSpectrum, energy_grid_mev: Sequence[float]) -> ProtonSpectrum:
    """Return a new spectrum with flux resampled onto energy_grid_mev via log-log interpolation."""
    resampled_flux = tuple(_loglog_interpolate(spectrum, energy) for energy in energy_grid_mev)
    return make_spectrum(tuple(energy_grid_mev), resampled_flux)


def _common_energy_grid(*spectra: ProtonSpectrum) -> tuple[float, ...]:
    """Union of energy grid points across spectra, restricted to their overlapping range."""
    if not spectra:
        raise TrappedProtonModelError("at least one spectrum is required to build a common energy grid")

    lower_bound = max(spectrum.energies_mev[0] for spectrum in spectra)
    upper_bound = min(spectrum.energies_mev[-1] for spectrum in spectra)
    if lower_bound >= upper_bound:
        raise TrappedProtonModelError(
            f"spectra energy ranges do not overlap (bounded to [{lower_bound}, {upper_bound}])"
        )

    points = sorted(
        {
            energy
            for spectrum in spectra
            for energy in spectrum.energies_mev
            if lower_bound <= energy <= upper_bound
        }
    )
    return tuple(points)


def build_worst_case_envelope(
    ap8_min: ProtonSpectrum,
    ap8_max: ProtonSpectrum,
    ap9_percentile: Optional[ProtonSpectrum] = None,
) -> tuple[ProtonSpectrum, tuple[str, ...]]:
    """
    Categorize AP-8 MIN/MAX (and an optional AP-9 percentile) spectra by taking
    the point-wise maximum flux at each energy. Returns the worst-case
    envelope spectrum plus, for each energy point, the name of the source
    spectrum that dominated there.
    """
    spectra = [ap8_min, ap8_max] + ([ap9_percentile] if ap9_percentile is not None else [])
    energy_grid = _common_energy_grid(*spectra)

    resampled = {
        "ap8_min": resample_spectrum(ap8_min, energy_grid),
        "ap8_max": resample_spectrum(ap8_max, energy_grid),
    }
    if ap9_percentile is not None:
        resampled["ap9_percentile"] = resample_spectrum(ap9_percentile, energy_grid)

    envelope_flux = []
    dominant_source = []
    for index in range(len(energy_grid)):
        candidates = {name: spectrum.flux[index] for name, spectrum in resampled.items()}
        best_source = max(candidates, key=candidates.get)
        envelope_flux.append(candidates[best_source])
        dominant_source.append(best_source)

    return make_spectrum(energy_grid, tuple(envelope_flux)), tuple(dominant_source)


def integrate_integral_spectrum(spectrum: ProtonSpectrum) -> ProtonSpectrum:
    """
    Integrate a differential flux spectrum (protons/cm^2/s/MeV) into an
    integral flux spectrum (protons/cm^2/s above each energy threshold) using
    trapezoidal integration from the top of the energy grid downward.
    """
    energies = spectrum.energies_mev
    flux = spectrum.flux
    point_count = len(energies)

    integral_flux = [0.0] * point_count
    running_total = 0.0
    for index in range(point_count - 2, -1, -1):
        low_e, high_e = energies[index], energies[index + 1]
        low_f, high_f = flux[index], flux[index + 1]
        segment = 0.5 * (low_f + high_f) * (high_e - low_e)
        running_total += segment
        integral_flux[index] = running_total

    return make_spectrum(energies, tuple(integral_flux))


@dataclass(frozen=True)
class WorstCaseTrappedProtonResult:
    """Full worst-case trapped proton model output."""

    differential_spectrum: ProtonSpectrum
    integral_spectrum: ProtonSpectrum
    dominant_source: tuple[str, ...]


def compute_worst_case_trapped_proton_spectrum(
    ap8_min: ProtonSpectrum,
    ap8_max: ProtonSpectrum,
    ap9_percentile: Optional[ProtonSpectrum] = None,
) -> WorstCaseTrappedProtonResult:
    """
    Compute the full ECSS-E-ST-10-04C worst-case trapped proton result: the
    AP-8/AP-9 envelope differential spectrum, its integral flux spectrum, and
    which source spectrum dominates at each energy point.
    """
    envelope, dominant_source = build_worst_case_envelope(ap8_min, ap8_max, ap9_percentile)
    integral = integrate_integral_spectrum(envelope)
    return WorstCaseTrappedProtonResult(
        differential_spectrum=envelope,
        integral_spectrum=integral,
        dominant_source=dominant_source,
    )

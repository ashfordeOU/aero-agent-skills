"""ECSS-E-ST-10-04C Annex B.2 -- GEO trapped environment via IGE-2006.

Representative (non-proprietary) implementation of the IGE-2006 modeling
approach for the geostationary (GEO) trapped energetic-electron
environment: at GEO the McIlwain L-shell is essentially fixed near
L ~= 6.6 (a geostationary orbit does not sweep across L-shells the way
a LEO or MEO orbit does), so the environment is instead dominated by a
strong magnetic-local-time (MLT) dependence -- substorm-injected
electrons peak in the post-midnight/dawn sector and are suppressed on
the compressed dayside -- and by a percentile axis (mean through
worst-case p99) that captures storm-time variability at a given MLT.

This module implements local-time/energy spectral interpolation at
fixed L ~= 6.6, percentile scaling, local-time-sector categorization,
dwell-weighted mission fluence integration, and a severity screening
band. It does not implement the full digitized ONERA IGE-2006
coefficient set (proprietary, distributed only via licensed
SPENVIS/OMERE tooling).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# A geostationary orbit's McIlwain L-shell is essentially fixed; this
# leaf is only applicable near that value.
GEO_L_SHELL = 6.6
GEO_L_SHELL_TOLERANCE = 0.3

PERCENTILES = ("mean", "p90", "p95", "p99")

# Multiplicative scale applied to the mean flux to approximate storm-time
# statistical percentiles. Illustrative figures reflecting the well-known
# strongly right-skewed (heavy-tailed) statistics of GEO substorm
# electron injections -- NOT digitized IGE-2006 percentile coefficients.
_PERCENTILE_SCALE = {
    "mean": 1.0,
    "p90": 3.0,
    "p95": 6.0,
    "p99": 12.0,
}

# Magnetic-local-time grid, hours (0 = midnight), circular with period 24.
LOCAL_TIME_GRID: tuple[float, ...] = (0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0)
LOCAL_TIME_PERIOD = 24.0

# Kinetic energy grid, MeV.
ENERGY_GRID: tuple[float, ...] = (0.1, 0.3, 1.0, 2.0, 5.0)

# Representative log10(mean differential flux) table [#/cm^2/s/MeV],
# indexed [local_time_index][energy_index]. Values reproduce the
# well-known IGE-2006 qualitative pattern -- a post-midnight/dawn
# (LT ~ 3-6h) peak from substorm injection and a dayside (LT ~ 12h)
# minimum from magnetopause compression -- at illustrative
# order-of-magnitude flux levels. NOT digitized ONERA IGE-2006
# coefficients, which are proprietary and distributed only with
# licensed SPENVIS/OMERE tools.
ELECTRON_LOG_FLUX: tuple[tuple[float, ...], ...] = (
    (5.8, 5.3, 4.3, 3.3, 1.8),  # LT 00h
    (6.0, 5.5, 4.5, 3.5, 2.0),  # LT 03h (peak)
    (5.9, 5.4, 4.4, 3.4, 1.9),  # LT 06h
    (5.6, 5.1, 4.1, 3.1, 1.6),  # LT 09h
    (5.2, 4.7, 3.7, 2.7, 1.2),  # LT 12h (minimum)
    (5.3, 4.8, 3.8, 2.8, 1.3),  # LT 15h
    (5.5, 5.0, 4.0, 3.0, 1.5),  # LT 18h
    (5.7, 5.2, 4.2, 3.2, 1.7),  # LT 21h
)


@dataclass(frozen=True)
class LocalTimeDwell:
    """One segment of mission time spent at a given GEO local time.

    A geostationary satellite is nearly fixed in local time over a
    single day (it only drifts slowly, e.g. across longitude
    relocations or the sidereal/solar-day precession over a year), so
    a mission is described as a set of local-time dwell segments
    rather than a per-orbit L-shell crossing sequence.
    """

    local_time_hours: float
    dwell_seconds: float


def validate_geo_l_shell(l_shell: float) -> None:
    """Raise ValueError if l_shell is not consistent with a
    geostationary orbit (L ~= 6.6). This leaf's local-time spectral
    model is only applicable near that fixed L-shell; use the
    dedicated `e1004-trapped-leo` or `e1004-meo-meov2` leaves for
    orbits that sweep across L-shells."""
    if abs(l_shell - GEO_L_SHELL) > GEO_L_SHELL_TOLERANCE + 1e-9:
        raise ValueError(
            f"l_shell {l_shell!r} is not consistent with a geostationary "
            f"orbit (expected within {GEO_L_SHELL_TOLERANCE} of "
            f"{GEO_L_SHELL}); use a LEO/MEO trapped-environment leaf instead"
        )


def classify_local_time_sector(local_time_hours: float) -> str:
    """Categorize a magnetic local time (hours, 0-24, circular) into
    the qualitative GEO sector it falls in: "midnight", "dawn", "noon",
    or "dusk". This is a category label for engineering triage, not a
    security classification."""
    value = local_time_hours % LOCAL_TIME_PERIOD
    if value >= 21.0 or value < 3.0:
        return "midnight"
    if value < 9.0:
        return "dawn"
    if value < 15.0:
        return "noon"
    return "dusk"


def _percentile_scale(percentile: str) -> float:
    if percentile not in _PERCENTILE_SCALE:
        raise ValueError(
            f"unknown percentile {percentile!r}; expected one of {PERCENTILES}"
        )
    return _PERCENTILE_SCALE[percentile]


def _linear_bracket(value: float, grid: Sequence[float]) -> tuple[int, int, float]:
    """Return (lo_index, hi_index, fraction) for linear interpolation,
    clamping ``value`` to the grid range first."""
    clamped = min(max(value, grid[0]), grid[-1])
    for i in range(len(grid) - 1):
        if grid[i] <= clamped <= grid[i + 1]:
            span = grid[i + 1] - grid[i]
            frac = 0.0 if span == 0 else (clamped - grid[i]) / span
            return i, i + 1, frac
    last = len(grid) - 1
    return last - 1, last, 1.0


def _circular_bracket(
    value_hours: float, grid: Sequence[float], period: float = LOCAL_TIME_PERIOD
) -> tuple[int, int, float]:
    """Return (lo_index, hi_index, fraction) for linear interpolation
    around a circular local-time grid wrapping at ``period``."""
    value = value_hours % period
    n = len(grid)
    for i in range(n):
        lo = grid[i]
        hi = grid[(i + 1) % n]
        hi_eff = hi + period if hi <= lo else hi
        if lo <= value <= hi_eff:
            span = hi_eff - lo
            frac = 0.0 if span == 0 else (value - lo) / span
            return i, (i + 1) % n, frac
    return n - 1, 0, 0.0


def interpolate_flux(
    local_time_hours: float, energy_mev: float, percentile: str = "mean"
) -> float:
    """Interpolate differential electron flux [#/cm^2/s/MeV] at fixed
    GEO L-shell (L ~= 6.6), over magnetic local time (circular,
    linear against log10(flux)) and energy (log-log), then scale by
    the requested percentile.

    Out-of-range energy values are clamped to the nearest tabulated
    grid edge; local time wraps circularly. Raises ValueError for a
    non-positive energy or an unrecognized percentile.
    """
    if energy_mev <= 0:
        raise ValueError("energy_mev must be positive")
    scale = _percentile_scale(percentile)

    lt_lo, lt_hi, lt_frac = _circular_bracket(local_time_hours, LOCAL_TIME_GRID)

    log_e = math.log10(energy_mev)
    log_e_grid = [math.log10(e) for e in ENERGY_GRID]
    e_lo, e_hi, e_frac = _linear_bracket(log_e, log_e_grid)

    def log_flux_at_lt(row_index: int) -> float:
        row = ELECTRON_LOG_FLUX[row_index]
        return row[e_lo] * (1 - e_frac) + row[e_hi] * e_frac

    log_flux = log_flux_at_lt(lt_lo) * (1 - lt_frac) + log_flux_at_lt(lt_hi) * lt_frac
    return (10.0**log_flux) * scale


def local_time_averaged_spectrum(
    dwells: Sequence[LocalTimeDwell],
    percentile: str = "mean",
    energies_mev: Sequence[float] = ENERGY_GRID,
) -> dict[float, float]:
    """Compute the dwell-time-weighted differential flux spectrum
    across a set of GEO local-time dwell segments."""
    if not dwells:
        raise ValueError("dwells must contain at least one local-time segment")

    total_dwell = sum(d.dwell_seconds for d in dwells)
    if total_dwell <= 0:
        raise ValueError("total dwell time must be positive")

    spectrum: dict[float, float] = {}
    for energy in energies_mev:
        weighted = sum(
            interpolate_flux(d.local_time_hours, energy, percentile) * d.dwell_seconds
            for d in dwells
        )
        spectrum[energy] = weighted / total_dwell
    return spectrum


def integrate_fluence(
    dwells: Sequence[LocalTimeDwell],
    energy_mev: float,
    percentile: str = "mean",
) -> float:
    """Integrate mission fluence [#/cm^2/MeV] at a given energy across
    a set of GEO local-time dwell segments: sum over segments of
    (differential flux at that local time) x (dwell duration)."""
    if not dwells:
        raise ValueError("dwells must contain at least one local-time segment")
    total = 0.0
    for d in dwells:
        if d.dwell_seconds < 0:
            raise ValueError("dwell_seconds must be >= 0")
        total += interpolate_flux(d.local_time_hours, energy_mev, percentile) * d.dwell_seconds
    return total


_SEVERITY_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (1.0e10, "benign"),
    (1.0e12, "elevated"),
    (math.inf, "severe"),
)


def categorize_severity(total_fluence: float) -> str:
    """Categorize total mission electron fluence into a qualitative
    severity band ("benign", "elevated", "severe"). Screening
    threshold for engineering triage, not an ECSS pass/fail verdict --
    downstream shielding/surface-charging analysis must confirm
    margins."""
    if total_fluence < 0:
        raise ValueError("total_fluence must not be negative")
    for limit, label in _SEVERITY_THRESHOLDS:
        if total_fluence <= limit:
            return label
    return "severe"

"""
Fracture control — critical crack location and orientation selection.
Reference: ECSS-E-ST-32C clause 7.2.2.

For each structural item under fracture-control assessment, candidate crack
initiation sites are paired with plausible orientations.  The pair whose
stress intensity factor yields the lowest fracture margin is the critical
location-orientation that governs subsequent crack-growth and critical-crack-
size calculations.
"""

import math
from typing import List


class CrackCandidate:
    """One candidate (location, orientation) pair for a structural item."""

    def __init__(
        self,
        location_id: str,
        orientation: str,
        net_stress_mpa: float,
        fracture_toughness_mpa_sqrtm: float,
        crack_half_length_m: float,
        geometry_factor: float = 1.12,
    ) -> None:
        if not location_id or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")
        if not orientation or not orientation.strip():
            raise ValueError("orientation must be a non-empty string")
        if net_stress_mpa <= 0:
            raise ValueError(
                f"net_stress_mpa must be positive; got {net_stress_mpa}"
            )
        if fracture_toughness_mpa_sqrtm <= 0:
            raise ValueError(
                f"fracture_toughness_mpa_sqrtm must be positive; got {fracture_toughness_mpa_sqrtm}"
            )
        if crack_half_length_m <= 0:
            raise ValueError(
                f"crack_half_length_m must be positive; got {crack_half_length_m}"
            )
        if geometry_factor <= 0:
            raise ValueError(
                f"geometry_factor must be positive; got {geometry_factor}"
            )

        self.location_id = location_id
        self.orientation = orientation
        self.net_stress_mpa = net_stress_mpa
        self.fracture_toughness_mpa_sqrtm = fracture_toughness_mpa_sqrtm
        self.crack_half_length_m = crack_half_length_m
        self.geometry_factor = geometry_factor

    def stress_intensity_factor(self) -> float:
        """K = F * sigma * sqrt(pi * a)  [MPa sqrt(m)]"""
        return (
            self.geometry_factor
            * self.net_stress_mpa
            * math.sqrt(math.pi * self.crack_half_length_m)
        )

    def fracture_margin(self) -> float:
        """MoS = Kc / K - 1.  Negative means fracture is predicted."""
        k = self.stress_intensity_factor()
        return self.fracture_toughness_mpa_sqrtm / k - 1.0

    def __repr__(self) -> str:
        return (
            f"CrackCandidate(location={self.location_id!r}, "
            f"orientation={self.orientation!r}, "
            f"K={self.stress_intensity_factor():.3f} MPa√m, "
            f"MoS={self.fracture_margin():.4f})"
        )


def select_critical_candidate(candidates: List[CrackCandidate]) -> CrackCandidate:
    """Return the candidate with the lowest fracture margin (most critical).

    Raises ValueError when the list is empty.
    """
    if not candidates:
        raise ValueError("candidates list must not be empty")
    return min(candidates, key=lambda c: c.fracture_margin())


def rank_candidates(candidates: List[CrackCandidate]) -> List[CrackCandidate]:
    """Return candidates sorted from most critical (lowest MoS) to least critical.

    Raises ValueError when the list is empty.
    """
    if not candidates:
        raise ValueError("candidates list must not be empty")
    return sorted(candidates, key=lambda c: c.fracture_margin())

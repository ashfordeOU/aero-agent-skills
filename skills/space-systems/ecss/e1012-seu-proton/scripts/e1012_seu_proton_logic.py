"""
SEU/MCU rate prediction for proton- and neutron-induced single events.

Implements the two-path (direct ionization + nuclear reaction) model
per ECSS-E-ST-10C §9.4.1.3 procedure.

Stdlib only.  Deterministic.  No network.
"""

import math
from typing import List, Optional


# ── Constants ─────────────────────────────────────────────────────────────────

# Path efficiency for direct proton ionization (unattenuated).
DIRECT_PATH_EFFICIENCY: float = 1.0

# Typical nuclear-spallation path efficiency accounting for reaction geometry
# and energy-dependent cross-section probability relative to direct ionization.
NUCLEAR_PATH_EFFICIENCY: float = 0.87

VALID_PARTICLE_TYPES = frozenset({"proton", "neutron"})


# ── Data containers ───────────────────────────────────────────────────────────

class FluxBin:
    """One bin of a differential particle flux spectrum."""

    def __init__(self, energy_MeV: float, flux: float, dE: float) -> None:
        self.energy_MeV = energy_MeV  # representative bin energy (MeV)
        self.flux = flux              # particles / (cm^2 · s · MeV)
        self.dE = dE                  # bin width (MeV)

    def __repr__(self) -> str:
        return (f"FluxBin(energy_MeV={self.energy_MeV}, "
                f"flux={self.flux}, dE={self.dE})")


class DeviceParams:
    """Four-parameter Weibull SEU cross-section model for a device."""

    def __init__(self, sigma_sat: float, E_th: float, W: float, s: float,
                 mcu_fraction: float = 0.0) -> None:
        self.sigma_sat = sigma_sat      # cm²/bit — saturation cross-section
        self.E_th = E_th                # MeV     — onset (threshold) energy
        self.W = W                      # MeV     — width parameter
        self.s = s                      # dimensionless Weibull shape exponent
        self.mcu_fraction = mcu_fraction  # fraction of upsets that are MCU [0,1]

    def __repr__(self) -> str:
        return (f"DeviceParams(sigma_sat={self.sigma_sat}, E_th={self.E_th}, "
                f"W={self.W}, s={self.s}, mcu_fraction={self.mcu_fraction})")


class SEUBudget:
    """Allowable SEU limits for a device."""

    def __init__(self, max_rate_per_bit_per_s: Optional[float] = None,
                 max_mission_count: Optional[float] = None) -> None:
        self.max_rate_per_bit_per_s = max_rate_per_bit_per_s
        self.max_mission_count = max_mission_count


# ── Weibull cross-section model ───────────────────────────────────────────────

def weibull_sigma(energy_MeV: float, params: DeviceParams) -> float:
    """
    Four-parameter Weibull SEU cross-section (cm²/bit) at *energy_MeV*.

    σ(E) = σ_sat · (1 − exp(−((E − E_th) / W)^s))  for E > E_th
    σ(E) = 0                                         for E ≤ E_th
    """
    if energy_MeV <= params.E_th:
        return 0.0
    return params.sigma_sat * (
        1.0 - math.exp(-((energy_MeV - params.E_th) / params.W) ** params.s)
    )


# ── SEU rate integration ──────────────────────────────────────────────────────

def seu_rate_one_path(flux_spectrum: List[FluxBin],
                      params: DeviceParams,
                      path_efficiency: float) -> float:
    """
    SEU rate (upsets/bit/s) for one transport path via rectangle integration.

    rate = path_efficiency × Σ σ(E_i) × Φ_i × ΔE_i
    """
    if not flux_spectrum:
        raise ValueError("flux_spectrum must not be empty")
    if not 0.0 <= path_efficiency <= 1.0:
        raise ValueError("path_efficiency must be in [0, 1]")

    total = 0.0
    for b in flux_spectrum:
        total += weibull_sigma(b.energy_MeV, params) * b.flux * b.dE
    return path_efficiency * total


def seu_rate_combined(direct_spectrum: List[FluxBin],
                      nuclear_spectrum: List[FluxBin],
                      params: DeviceParams,
                      direct_efficiency: float = DIRECT_PATH_EFFICIENCY,
                      nuclear_efficiency: float = NUCLEAR_PATH_EFFICIENCY
                      ) -> dict:
    """
    Total SEU rate combining direct-ionization and nuclear-reaction paths.

    Returns a dict:
        rate_direct   — upsets/bit/s from the direct-ionization path
        rate_nuclear  — upsets/bit/s from the nuclear-reaction path
        rate_total    — combined rate
    """
    rate_direct = seu_rate_one_path(direct_spectrum, params, direct_efficiency)
    rate_nuclear = seu_rate_one_path(nuclear_spectrum, params, nuclear_efficiency)
    return {
        "rate_direct": rate_direct,
        "rate_nuclear": rate_nuclear,
        "rate_total": rate_direct + rate_nuclear,
    }


# ── MCU and mission count ─────────────────────────────────────────────────────

def mcu_rate(rate_total_per_bit_per_s: float, mcu_fraction: float) -> float:
    """MCU rate (upsets/bit/s) = total SEU rate × MCU fraction."""
    if not 0.0 <= mcu_fraction <= 1.0:
        raise ValueError("mcu_fraction must be in [0, 1]")
    return rate_total_per_bit_per_s * mcu_fraction


def mission_seu_count(rate_per_bit_per_s: float,
                      bit_count: int,
                      mission_duration_s: float) -> float:
    """
    Total expected SEU count over the mission life.

    count = rate × bit_count × mission_duration_s
    """
    if bit_count <= 0:
        raise ValueError("bit_count must be a positive integer")
    if mission_duration_s < 0.0:
        raise ValueError("mission_duration_s must be non-negative")
    return rate_per_bit_per_s * bit_count * mission_duration_s


# ── Compliance check ──────────────────────────────────────────────────────────

def check_seu_compliance(rate_total: float,
                         mission_count: float,
                         budget: SEUBudget) -> dict:
    """
    Compare predicted SEU rate and mission count against the device budget.

    Returns a dict:
        rate_pass     — bool, True if rate is within budget (or no rate limit set)
        count_pass    — bool, True if count is within budget (or no count limit set)
        compliant     — bool, True only if both pass and at least one limit is set
        findings      — list of str describing each violation or missing-budget finding
    """
    findings: List[str] = []
    rate_pass = True
    count_pass = True

    if budget.max_rate_per_bit_per_s is None and budget.max_mission_count is None:
        findings.append(
            "SEU budget not on record — requirement not captured (open finding)"
        )
        return {
            "rate_pass": False,
            "count_pass": False,
            "compliant": False,
            "findings": findings,
        }

    if budget.max_rate_per_bit_per_s is not None:
        if rate_total > budget.max_rate_per_bit_per_s:
            rate_pass = False
            findings.append(
                f"SEU rate {rate_total:.3e} upsets/bit/s exceeds budget "
                f"{budget.max_rate_per_bit_per_s:.3e} upsets/bit/s"
            )

    if budget.max_mission_count is not None:
        if mission_count > budget.max_mission_count:
            count_pass = False
            findings.append(
                f"Mission SEU count {mission_count:.3e} exceeds budget "
                f"{budget.max_mission_count:.3e}"
            )

    compliant = rate_pass and count_pass
    return {
        "rate_pass": rate_pass,
        "count_pass": count_pass,
        "compliant": compliant,
        "findings": findings,
    }


# ── Input validation ──────────────────────────────────────────────────────────

def validate_particle_type(particle_type: str) -> None:
    """Raise ValueError when particle_type is not in the recognized set."""
    if particle_type not in VALID_PARTICLE_TYPES:
        raise ValueError(
            f"Unrecognized particle type '{particle_type}'. "
            f"Expected one of: {sorted(VALID_PARTICLE_TYPES)}"
        )


def validate_flux_bins(bins: List[FluxBin]) -> None:
    """Raise ValueError when any bin carries a physically invalid value."""
    if not bins:
        raise ValueError("Flux spectrum must contain at least one bin")
    for i, b in enumerate(bins):
        if b.energy_MeV <= 0.0:
            raise ValueError(
                f"Bin {i}: energy_MeV must be positive, got {b.energy_MeV}"
            )
        if b.flux < 0.0:
            raise ValueError(
                f"Bin {i}: flux must be non-negative, got {b.flux}"
            )
        if b.dE <= 0.0:
            raise ValueError(
                f"Bin {i}: dE must be positive, got {b.dE}"
            )


def validate_device_params(params: DeviceParams) -> None:
    """Raise ValueError when device parameters are physically invalid."""
    if params.sigma_sat <= 0.0:
        raise ValueError("sigma_sat must be positive")
    if params.E_th < 0.0:
        raise ValueError("E_th must be non-negative")
    if params.W <= 0.0:
        raise ValueError("W (Weibull width) must be positive")
    if params.s <= 0.0:
        raise ValueError("s (Weibull shape exponent) must be positive")
    if not 0.0 <= params.mcu_fraction <= 1.0:
        raise ValueError("mcu_fraction must be in [0, 1]")

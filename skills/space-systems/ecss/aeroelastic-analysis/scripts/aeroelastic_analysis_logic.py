"""
Aeroelastic analysis logic — ECSS E-ST-32C clause 4.6.2.17
Deterministic, offline, stdlib only.
"""

from dataclasses import dataclass, field
from typing import List

# Required margin thresholds (dimensionless fractions)
FLUTTER_SPEED_MARGIN = 0.15       # 15 % above design speed
DIVERGENCE_SPEED_MARGIN = 0.15    # 15 % above design speed
MIN_FREQUENCY_SEPARATION = 0.10   # 10 % separation from aerodynamic forcing

# Regime labels — no banned words
REGIME_STABLE = "stable"
REGIME_FLUTTER_RISK = "flutter-risk"
REGIME_DIVERGENCE_RISK = "divergence-risk"
REGIME_COUPLED_RISK = "coupled-aeroelastic-risk"


class AeroelasticError(ValueError):
    """Raised when input data are invalid or assessment cannot proceed."""


@dataclass
class SurfaceDefinition:
    name: str
    design_speed: float          # m/s — maximum design equivalent airspeed (VD)
    flutter_speed: float         # m/s — predicted onset flutter speed
    divergence_speed: float      # m/s — predicted static divergence speed
    structural_freq_hz: float    # Hz  — lowest structural elastic eigenfrequency
    aerodynamic_freq_hz: float   # Hz  — dominant aerodynamic forcing frequency at max-Q


@dataclass
class AeroelasticFinding:
    surface: str
    regime: str
    flutter_margin: float
    divergence_margin: float
    frequency_separation: float
    flutter_adequate: bool
    divergence_adequate: bool
    frequency_separation_adequate: bool
    findings: List[str] = field(default_factory=list)


def compute_dynamic_pressure(density_kg_m3: float, velocity_m_s: float) -> float:
    """Return q = 0.5 * rho * V^2 in Pascals."""
    if density_kg_m3 < 0:
        raise AeroelasticError("Air density must be non-negative")
    if velocity_m_s < 0:
        raise AeroelasticError("Velocity must be non-negative")
    return 0.5 * density_kg_m3 * velocity_m_s ** 2


def compute_flutter_margin(flutter_speed: float, design_speed: float) -> float:
    """
    Return (V_flutter - V_D) / V_D.
    Positive value means flutter speed exceeds design speed; must be >= FLUTTER_SPEED_MARGIN.
    """
    if design_speed <= 0:
        raise AeroelasticError("Design speed must be positive")
    if flutter_speed <= 0:
        raise AeroelasticError("Flutter speed must be positive")
    return (flutter_speed - design_speed) / design_speed


def compute_divergence_margin(divergence_speed: float, design_speed: float) -> float:
    """
    Return (V_div - V_D) / V_D.
    Positive value means divergence speed exceeds design speed; must be >= DIVERGENCE_SPEED_MARGIN.
    """
    if design_speed <= 0:
        raise AeroelasticError("Design speed must be positive")
    if divergence_speed <= 0:
        raise AeroelasticError("Divergence speed must be positive")
    return (divergence_speed - design_speed) / design_speed


def compute_frequency_separation(structural_freq_hz: float, aerodynamic_freq_hz: float) -> float:
    """
    Return |f_struct - f_aero| / min(f_struct, f_aero).
    Must be >= MIN_FREQUENCY_SEPARATION to prevent resonant coupling.
    """
    if structural_freq_hz <= 0:
        raise AeroelasticError("Structural frequency must be positive")
    if aerodynamic_freq_hz <= 0:
        raise AeroelasticError("Aerodynamic forcing frequency must be positive")
    return abs(structural_freq_hz - aerodynamic_freq_hz) / min(structural_freq_hz, aerodynamic_freq_hz)


def categorize_aeroelastic_regime(
    flutter_margin: float,
    divergence_margin: float,
    freq_separation: float,
) -> str:
    """
    Categorize the aeroelastic regime for a surface based on computed margins.
    Returns one of: stable, flutter-risk, divergence-risk, coupled-aeroelastic-risk.
    """
    flutter_ok = flutter_margin >= FLUTTER_SPEED_MARGIN
    divergence_ok = divergence_margin >= DIVERGENCE_SPEED_MARGIN
    freq_ok = freq_separation >= MIN_FREQUENCY_SEPARATION

    if flutter_ok and divergence_ok and freq_ok:
        return REGIME_STABLE
    if not flutter_ok and not divergence_ok:
        return REGIME_COUPLED_RISK
    if not flutter_ok:
        return REGIME_FLUTTER_RISK
    if not divergence_ok:
        return REGIME_DIVERGENCE_RISK
    # Speed margins adequate but frequency separation insufficient: coupled risk
    return REGIME_COUPLED_RISK


def assess_surface(
    surface: SurfaceDefinition,
    flutter_margin_req: float = FLUTTER_SPEED_MARGIN,
    divergence_margin_req: float = DIVERGENCE_SPEED_MARGIN,
    freq_sep_req: float = MIN_FREQUENCY_SEPARATION,
) -> AeroelasticFinding:
    """Run the full aeroelastic check for one aerodynamic surface."""
    flutter_margin = compute_flutter_margin(surface.flutter_speed, surface.design_speed)
    divergence_margin = compute_divergence_margin(surface.divergence_speed, surface.design_speed)
    freq_separation = compute_frequency_separation(
        surface.structural_freq_hz, surface.aerodynamic_freq_hz
    )

    flutter_ok = flutter_margin >= flutter_margin_req
    divergence_ok = divergence_margin >= divergence_margin_req
    freq_ok = freq_separation >= freq_sep_req

    findings: List[str] = []
    if not flutter_ok:
        findings.append(
            f"Flutter margin {flutter_margin:.4f} below required {flutter_margin_req:.4f} "
            f"(V_flutter={surface.flutter_speed} m/s, V_D={surface.design_speed} m/s)"
        )
    if not divergence_ok:
        findings.append(
            f"Divergence margin {divergence_margin:.4f} below required {divergence_margin_req:.4f} "
            f"(V_div={surface.divergence_speed} m/s, V_D={surface.design_speed} m/s)"
        )
    if not freq_ok:
        findings.append(
            f"Frequency separation {freq_separation:.4f} below required {freq_sep_req:.4f} "
            f"(f_struct={surface.structural_freq_hz} Hz, f_aero={surface.aerodynamic_freq_hz} Hz)"
        )

    regime = categorize_aeroelastic_regime(flutter_margin, divergence_margin, freq_separation)

    return AeroelasticFinding(
        surface=surface.name,
        regime=regime,
        flutter_margin=flutter_margin,
        divergence_margin=divergence_margin,
        frequency_separation=freq_separation,
        flutter_adequate=flutter_ok,
        divergence_adequate=divergence_ok,
        frequency_separation_adequate=freq_ok,
        findings=findings,
    )


def run_aeroelastic_assessment(surfaces: List[SurfaceDefinition]) -> List[AeroelasticFinding]:
    """Assess all aerodynamic surfaces and return one finding per surface."""
    if not surfaces:
        raise AeroelasticError("At least one surface is required for assessment")
    return [assess_surface(s) for s in surfaces]


def is_assessment_compliant(findings: List[AeroelasticFinding]) -> bool:
    """Return True only if every surface is in the stable regime."""
    return all(f.regime == REGIME_STABLE for f in findings)

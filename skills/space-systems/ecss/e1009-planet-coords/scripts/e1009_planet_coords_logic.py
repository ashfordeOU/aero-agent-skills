"""
e1009_planet_coords_logic.py

ECSS-E-ST-10-09C §5.4.6 — Planetary body-fixed frame definition using
WGCCRE (IAU Working Group on Cartographic Coordinates and Rotational
Elements) conventions.

Stdlib only; offline; deterministic.
"""

import math
from typing import NamedTuple, List, Tuple

# ---------------------------------------------------------------------------
# WGCCRE linear rotation elements for selected Solar System bodies.
# Each entry: (alpha0, alpha1, delta0, delta1, W0, W1)
#   alpha0 [deg] — right ascension of North Pole at J2000, ICRF
#   alpha1 [deg/century] — secular rate of alpha0
#   delta0 [deg] — declination of North Pole at J2000, ICRF
#   delta1 [deg/century] — secular rate of delta0
#   W0     [deg] — prime-meridian angle at J2000
#   W1     [deg/day] — prime-meridian rotation rate
#
# Source: IAU WGCCRE 2015 report (Archinal et al. 2018, CeMDA 130:22).
# Periodic terms per body are not included in this linear-only model;
# callers requiring sub-degree accuracy for Jupiter, Saturn, or the Moon
# must add the documented periodic contributions.
# ---------------------------------------------------------------------------
_BODY_PARAMS: dict = {
    "mercury": (281.0103, -0.0328, 61.4155, -0.0049, 329.5988, 6.1385025),
    "venus":   (272.76,    0.0,    67.16,    0.0,    160.20,  -1.4813688),
    "earth":   (  0.00,   -0.641,  90.00,   -0.557,  190.147, 360.9856235),
    "mars":    (317.68143, -0.1061, 52.88650, -0.0609, 176.630, 350.89198226),
    "moon":    (269.9949,   0.0031, 66.5392,   0.0130,  38.3213,  13.17635815),
    "jupiter": (268.056595, -0.006499, 64.495303, 0.002413, 284.95, 870.5360000),
    "saturn":  ( 40.589,   -0.036,  83.537,   -0.004,   38.90, 810.7939024),
}

_KNOWN_BODIES: frozenset = frozenset(_BODY_PARAMS.keys())

# Plausible epoch range: ±200 Julian years (~73 000 days) from J2000.
_EPOCH_MAX_DAYS: float = 73050.0


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class PoleOrientation(NamedTuple):
    alpha_deg: float   # right ascension of North Pole, degrees, ICRF
    delta_deg: float   # declination of North Pole, degrees, ICRF


class PrimeMeridian(NamedTuple):
    W_deg: float       # prime-meridian angle in [0°, 360°)


class BodyFrameResult(NamedTuple):
    body: str
    epoch_d: float           # days from J2000
    T: float                 # Julian centuries from J2000
    pole: PoleOrientation
    prime_meridian: PrimeMeridian
    pole_ra_rad: float
    pole_dec_rad: float
    W_rad: float


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_body(body: str) -> str:
    """Return the canonical (lower-case) body key or raise ValueError."""
    if not isinstance(body, str):
        raise TypeError(f"body must be a string, got {type(body)}")
    key = body.lower().strip()
    if key not in _KNOWN_BODIES:
        raise ValueError(
            f"Unknown body '{body}'. Known bodies: {sorted(_KNOWN_BODIES)}"
        )
    return key


def _validate_epoch_days(epoch_d: float) -> None:
    """Raise TypeError or ValueError if epoch_d is unusable."""
    if not isinstance(epoch_d, (int, float)):
        raise TypeError(f"epoch_d must be numeric, got {type(epoch_d)}")
    if not (-_EPOCH_MAX_DAYS <= epoch_d <= _EPOCH_MAX_DAYS):
        raise ValueError(
            f"epoch_d={epoch_d} is outside the plausible range "
            f"±{_EPOCH_MAX_DAYS} days from J2000 (~±200 years)"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_body_frame(body: str, epoch_d: float) -> BodyFrameResult:
    """
    Compute the WGCCRE body-fixed frame orientation at epoch_d days from J2000.

    Returns pole orientation (α, δ) in ICRF, prime-meridian angle W in [0°, 360°),
    and their radian equivalents.

    Raises ValueError for an unknown body or out-of-range epoch.
    Raises TypeError for non-string body or non-numeric epoch.
    """
    key = _validate_body(body)
    _validate_epoch_days(epoch_d)

    a0, a1, d0, d1, W0, W1 = _BODY_PARAMS[key]

    T = epoch_d / 36525.0          # Julian centuries from J2000

    alpha = a0 + a1 * T            # pole right ascension, degrees
    delta = d0 + d1 * T            # pole declination, degrees
    W_raw = W0 + W1 * epoch_d
    W = W_raw % 360.0              # reduce to [0°, 360°)

    return BodyFrameResult(
        body=key,
        epoch_d=epoch_d,
        T=T,
        pole=PoleOrientation(alpha_deg=alpha, delta_deg=delta),
        prime_meridian=PrimeMeridian(W_deg=W),
        pole_ra_rad=math.radians(alpha),
        pole_dec_rad=math.radians(delta),
        W_rad=math.radians(W),
    )


def pole_unit_vector(result: BodyFrameResult) -> Tuple[float, float, float]:
    """
    Return the body's North Pole as a unit vector in ICRF Cartesian coordinates.

    Definition:
        x = cos(δ) · cos(α)
        y = cos(δ) · sin(α)
        z = sin(δ)
    """
    cos_dec = math.cos(result.pole_dec_rad)
    return (
        cos_dec * math.cos(result.pole_ra_rad),
        cos_dec * math.sin(result.pole_ra_rad),
        math.sin(result.pole_dec_rad),
    )


# ---------------------------------------------------------------------------
# Validation / compliance checks
# ---------------------------------------------------------------------------

def validate_pole_range(result: BodyFrameResult) -> List[str]:
    """
    Check pole orientation and prime-meridian angle against physical bounds.

    Returns a list of finding strings; an empty list means all checks pass.
    """
    findings: List[str] = []
    if not (-180.0 <= result.pole.alpha_deg <= 360.0):
        findings.append(
            f"right ascension {result.pole.alpha_deg:.6f}° is outside [−180°, 360°]"
        )
    if not (-90.0 <= result.pole.delta_deg <= 90.0):
        findings.append(
            f"declination {result.pole.delta_deg:.6f}° is outside [−90°, 90°]"
        )
    if not (0.0 <= result.prime_meridian.W_deg < 360.0):
        findings.append(
            f"prime-meridian W={result.prime_meridian.W_deg:.6f}° is outside [0°, 360°)"
        )
    return findings


def angular_separation_deg(
    v1: Tuple[float, float, float],
    v2: Tuple[float, float, float],
) -> float:
    """
    Great-circle angular separation in degrees between two unit vectors.
    Clamps the dot product to [−1, 1] to guard against floating-point rounding.
    """
    dot = sum(a * b for a, b in zip(v1, v2))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def list_bodies() -> List[str]:
    """Return a sorted list of body names with known WGCCRE entries."""
    return sorted(_KNOWN_BODIES)

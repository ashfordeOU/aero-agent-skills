"""
ECSS E-ST-10C §5.4.4 — time scales and epochs logic.

Implements deterministic, offline checks for time-scale selection,
epoch definition, and frame–time-scale consistency for space mission
reference frames. No third-party dependencies; stdlib only.
"""

from __future__ import annotations
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Time scale registry
# ---------------------------------------------------------------------------

VALID_TIME_SCALES: frozenset[str] = frozenset({
    "TAI",  # International Atomic Time — primary uniform atomic scale
    "UTC",  # Coordinated Universal Time — TAI minus integer leap seconds
    "UT1",  # Universal Time 1 — Earth rotation angle, differs from UTC by DUT1
    "TT",   # Terrestrial Time — TAI + 32.184 s exactly
    "TDB",  # Barycentric Dynamical Time — solar-system ephemeris time
    "TCB",  # Barycentric Coordinate Time — SI-second at solar-system barycentre
    "TCG",  # Geocentric Coordinate Time — SI-second at Earth geocentre
    "GPS",  # GPS Time — TAI − 19 s, constant offset from TAI
})

# Fixed offsets relative to TAI, in seconds (positive = scale is ahead of TAI).
# Only scales with a constant linear relationship to TAI are listed here.
TAI_OFFSET_SECONDS: dict[str, float] = {
    "TAI": 0.0,
    "TT":  32.184,   # TT = TAI + 32.184 s (exact by IAU definition)
    "GPS": -19.0,    # GPS = TAI − 19 s (established at GPS epoch, never changes)
}

# ---------------------------------------------------------------------------
# Frame–time-scale compatibility (ECSS E-ST-10C §5.4.4 paraphrase)
# Each frame maps to the set of time scales appropriate for its description.
# ---------------------------------------------------------------------------

FRAME_RECOMMENDED_SCALES: dict[str, frozenset[str]] = {
    "ECI":   frozenset({"TT", "TAI"}),
    "GCRS":  frozenset({"TT", "TCG"}),
    "ECEF":  frozenset({"UTC", "UT1"}),
    "ITRS":  frozenset({"UTC", "UT1"}),
    "TEME":  frozenset({"UTC", "TAI"}),
    "BCRS":  frozenset({"TDB", "TCB"}),
    "HCI":   frozenset({"TDB", "TCB"}),
    "RTN":   frozenset({"UTC", "TAI", "TT"}),
    "LVLH":  frozenset({"UTC", "TAI", "TT"}),
}

# ---------------------------------------------------------------------------
# Epoch registry
# ---------------------------------------------------------------------------

class Epoch(NamedTuple):
    name: str
    jd: float        # Julian Date of the epoch
    time_scale: str  # Time scale in which the epoch is defined

STANDARD_EPOCHS: dict[str, Epoch] = {
    "J2000.0": Epoch("J2000.0", 2451545.0,    "TT"),   # 2000-01-01 12:00:00 TT
    "J1950.0": Epoch("J1950.0", 2433282.5,    "TT"),   # 1950-01-01 00:00:00 TT
    "B1950.0": Epoch("B1950.0", 2433282.4235, "TT"),   # Besselian 1950.0 (approx)
    "J1900.0": Epoch("J1900.0", 2415020.0,    "TT"),   # 1900-01-01 12:00:00 TT
    "MJD0":    Epoch("MJD0",    2400000.5,    "UTC"),  # MJD zero point
}

MJD_OFFSET: float = 2400000.5  # MJD = JD − MJD_OFFSET

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TimeScaleError(ValueError):
    """Raised when a time scale identifier is not recognized."""


class EpochError(ValueError):
    """Raised when an epoch identifier is not recognized."""


class FrameTimeScaleError(ValueError):
    """Raised when a frame and time scale are procedurally incompatible."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_time_scale(scale: str) -> str:
    """Return scale uppercased and stripped if recognized; raise TimeScaleError otherwise."""
    s = scale.strip().upper()
    if s not in VALID_TIME_SCALES:
        raise TimeScaleError(
            f"Unrecognized time scale '{scale}'. "
            f"Valid scales: {sorted(VALID_TIME_SCALES)}"
        )
    return s


def validate_epoch(epoch_name: str) -> Epoch:
    """Return the Epoch for epoch_name if recognized; raise EpochError otherwise."""
    if epoch_name not in STANDARD_EPOCHS:
        raise EpochError(
            f"Unrecognized epoch '{epoch_name}'. "
            f"Valid epochs: {sorted(STANDARD_EPOCHS)}"
        )
    return STANDARD_EPOCHS[epoch_name]


def validate_frame(frame: str) -> str:
    """Return frame uppercased and stripped if recognized; raise ValueError otherwise."""
    f = frame.strip().upper()
    if f not in FRAME_RECOMMENDED_SCALES:
        raise ValueError(
            f"Unrecognized reference frame '{frame}'. "
            f"Valid frames: {sorted(FRAME_RECOMMENDED_SCALES)}"
        )
    return f


# ---------------------------------------------------------------------------
# Frame–time-scale compatibility check
# ---------------------------------------------------------------------------

def check_frame_time_scale(frame: str, scale: str) -> bool:
    """
    Return True if scale is in the recommended set for frame.
    Raise FrameTimeScaleError if the pairing is procedurally incorrect.
    Raise TimeScaleError or ValueError for unrecognized inputs.
    """
    f = validate_frame(frame)
    s = validate_time_scale(scale)
    recommended = FRAME_RECOMMENDED_SCALES[f]
    if s not in recommended:
        raise FrameTimeScaleError(
            f"Time scale '{s}' is not recommended for frame '{f}'. "
            f"Recommended: {sorted(recommended)}"
        )
    return True


def select_time_scale_for_frame(frame: str) -> list[str]:
    """Return the recommended time scales for frame, sorted alphabetically."""
    f = validate_frame(frame)
    return sorted(FRAME_RECOMMENDED_SCALES[f])


# ---------------------------------------------------------------------------
# Epoch utilities
# ---------------------------------------------------------------------------

def get_epoch_jd(epoch_name: str) -> float:
    """Return the Julian Date of a named standard epoch."""
    return validate_epoch(epoch_name).jd


def get_epoch_time_scale(epoch_name: str) -> str:
    """Return the defining time scale of a named standard epoch."""
    return validate_epoch(epoch_name).time_scale


# ---------------------------------------------------------------------------
# JD / MJD conversions
# ---------------------------------------------------------------------------

def jd_to_mjd(jd: float) -> float:
    """Convert Julian Date to Modified Julian Date (MJD = JD − 2 400 000.5)."""
    return jd - MJD_OFFSET


def mjd_to_jd(mjd: float) -> float:
    """Convert Modified Julian Date to Julian Date."""
    return mjd + MJD_OFFSET


def days_from_j2000(jd: float) -> float:
    """Return Julian days elapsed since J2000.0 (JD 2451545.0 TT)."""
    return jd - STANDARD_EPOCHS["J2000.0"].jd


def centuries_from_j2000(jd: float) -> float:
    """Return Julian centuries (36525 days) elapsed since J2000.0."""
    return days_from_j2000(jd) / 36525.0


# ---------------------------------------------------------------------------
# Fixed-offset time scale conversions
# ---------------------------------------------------------------------------

def tai_to_tt(tai_seconds: float) -> float:
    """Convert TAI seconds to TT seconds (TT = TAI + 32.184 s)."""
    return tai_seconds + TAI_OFFSET_SECONDS["TT"]


def tt_to_tai(tt_seconds: float) -> float:
    """Convert TT seconds to TAI seconds."""
    return tt_seconds - TAI_OFFSET_SECONDS["TT"]


def tai_to_gps(tai_seconds: float) -> float:
    """Convert TAI to GPS time (GPS = TAI − 19 s, constant)."""
    return tai_seconds + TAI_OFFSET_SECONDS["GPS"]


def gps_to_tai(gps_seconds: float) -> float:
    """Convert GPS time to TAI."""
    return gps_seconds - TAI_OFFSET_SECONDS["GPS"]


# ---------------------------------------------------------------------------
# Leap-second conversions (UTC ↔ TAI)
# ---------------------------------------------------------------------------

def _validate_leap_seconds(leap_seconds: object) -> int:
    """Raise ValueError if leap_seconds is not a non-negative integer."""
    if not isinstance(leap_seconds, int) or isinstance(leap_seconds, bool):
        raise ValueError(
            f"leap_seconds must be a non-negative integer, got {leap_seconds!r}"
        )
    if leap_seconds < 0:
        raise ValueError(
            f"leap_seconds must be non-negative, got {leap_seconds}"
        )
    return leap_seconds


def tai_to_utc(tai_seconds: float, leap_seconds: int) -> float:
    """
    Convert TAI seconds to UTC seconds.

    UTC = TAI − leap_seconds, where leap_seconds is the integer count
    of leap seconds applicable at the epoch (caller's responsibility to
    supply the correct IERS value — no table lookup is performed here).
    """
    ls = _validate_leap_seconds(leap_seconds)
    return tai_seconds - ls


def utc_to_tai(utc_seconds: float, leap_seconds: int) -> float:
    """
    Convert UTC seconds to TAI seconds.

    TAI = UTC + leap_seconds.
    """
    ls = _validate_leap_seconds(leap_seconds)
    return utc_seconds + ls


# ---------------------------------------------------------------------------
# Description helper
# ---------------------------------------------------------------------------

_SCALE_DESCRIPTIONS: dict[str, str] = {
    "TAI": "International Atomic Time — uniform atomic seconds, monotonically increasing.",
    "UTC": "Coordinated Universal Time — TAI minus integer leap seconds, Earth broadcast civil time.",
    "UT1": "Universal Time 1 — tracks Earth's rotation angle; differs from UTC by DUT1 (within ±0.9 s).",
    "TT":  "Terrestrial Time — TAI + 32.184 s exactly; used for geocentric ephemerides and J2000.0 epoch.",
    "TDB": "Barycentric Dynamical Time — solar-system ephemeris time; periodic offset from TT within ±2 ms.",
    "TCB": "Barycentric Coordinate Time — SI-second at solar-system barycentre; drifts from TT at ~1.48e-8.",
    "TCG": "Geocentric Coordinate Time — SI-second at Earth geocentre; drifts from TT at ~6.97e-10.",
    "GPS": "GPS Time — TAI − 19 s constant offset; used by GNSS receivers, must be converted for frame work.",
}


def describe_time_scale(scale: str) -> str:
    """Return a short paraphrase description of the given time scale."""
    s = validate_time_scale(scale)
    return _SCALE_DESCRIPTIONS[s]

"""
e1003_test_data_logic.py

Deterministic, offline engineering logic for ECSS-E-ST-10C §4.3.5:
record, reduce, and deliver test data (sampling rates, formats, storage).

All functions are pure (no side-effects). stdlib only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants (paraphrased from ECSS-E-ST-10C §4.3.5 requirements)
# ---------------------------------------------------------------------------

# Minimum sampling rates (Hz) by channel type.
# Floor is set so that the Nyquist criterion is satisfied for the highest
# signal frequency of interest specified in §4.3.5 for each measurement family.
MINIMUM_SAMPLING_RATES_HZ: dict[str, float] = {
    "vibration":    2000.0,
    "acoustic":    10000.0,
    "thermal":         1.0,
    "pressure":       10.0,
    "electrical":    100.0,
    "strain":       1000.0,
    "displacement":   10.0,
}

VALID_DATA_FORMATS: frozenset[str] = frozenset({
    "binary", "ascii", "ieee754_float32", "ieee754_float64", "csv", "hdf5",
})

# Mandatory metadata fields every recorded data channel must carry (§4.3.5
# traceability requirement).
REQUIRED_RECORD_FIELDS: frozenset[str] = frozenset({
    "test_id",
    "channel_id",
    "sampling_rate_hz",
    "unit",
    "calibration_slope",
    "calibration_offset",
    "timestamp_utc",
    "format",
})

# Mandatory fields in a test data delivery package before handover.
REQUIRED_DELIVERY_FIELDS: frozenset[str] = frozenset({
    "test_id",
    "test_title",
    "date_utc",
    "facility",
    "operator",
    "channels",
    "data_file",
    "calibration_file",
    "format",
})

# Minimum retention periods (days) by test phase, per §4.3.5 storage rules.
RETENTION_PERIODS_DAYS: dict[str, int] = {
    "development":   365,
    "qualification": 3650,
    "acceptance":    3650,
    "protoflight":   3650,
    "in-service":    1825,
}

# Channel type groupings used for traceability priority.
_PRIMARY_TYPES    = frozenset({"vibration", "acoustic", "strain"})
_SECONDARY_TYPES  = frozenset({"pressure", "electrical", "displacement"})
_HOUSEKEEPING_TYPES = frozenset({"thermal", "power", "status"})


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def validate_sampling_rate(channel_type: str, rate_hz: float) -> tuple[bool, str]:
    """
    Check whether *rate_hz* meets the §4.3.5 minimum for *channel_type*.

    Returns (True, "") on success or (False, reason) on failure.
    Raises ValueError for an unrecognized channel type.
    """
    if channel_type not in MINIMUM_SAMPLING_RATES_HZ:
        raise ValueError(
            f"Unknown channel type {channel_type!r}. "
            f"Recognized types: {sorted(MINIMUM_SAMPLING_RATES_HZ)}"
        )
    minimum = MINIMUM_SAMPLING_RATES_HZ[channel_type]
    if rate_hz < minimum:
        return (
            False,
            f"Sampling rate {rate_hz} Hz is below the minimum "
            f"{minimum} Hz required for '{channel_type}' channels.",
        )
    return (True, "")


def compute_storage_bytes(
    num_channels: int,
    duration_s: float,
    rate_hz: float,
    bits_per_sample: int,
) -> int:
    """
    Estimate raw storage in bytes for a test run.

    Formula: channels × duration_s × rate_hz × bits_per_sample / 8,
    rounded up to the nearest byte. No compression is assumed (worst case).
    Raises ValueError if any argument is non-positive.
    """
    for name, val in (
        ("num_channels", num_channels),
        ("duration_s", duration_s),
        ("rate_hz", rate_hz),
        ("bits_per_sample", bits_per_sample),
    ):
        if val <= 0:
            raise ValueError(f"{name} must be positive, got {val!r}")
    import math
    raw_bits = num_channels * duration_s * rate_hz * bits_per_sample
    return math.ceil(raw_bits / 8)


def reduce_to_engineering_units(
    raw_value: float,
    slope: float,
    offset: float,
) -> float:
    """
    Apply a linear calibration to convert a raw sensor count to engineering units.

    engineering_value = slope * raw_value + offset

    Raises ValueError if slope is zero (degenerate calibration).
    """
    if slope == 0.0:
        raise ValueError("Calibration slope must not be zero.")
    return slope * raw_value + offset


def check_record_completeness(record: dict) -> list[str]:
    """
    Return a list of missing mandatory fields in a test data record.

    An empty return value means the record is complete.
    Fields absent, None, or holding an empty string are treated as missing.
    Numeric zero (e.g. calibration_offset=0.0) is a valid value and is NOT missing.
    """
    missing: list[str] = []
    for field in sorted(REQUIRED_RECORD_FIELDS):
        value = record.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def validate_delivery_package(package: dict) -> list[str]:
    """
    Return a list of missing mandatory fields in a test data delivery package.

    An empty return value means the package is ready for handover.
    Fields absent, None, empty string, or empty list are treated as missing.
    """
    missing: list[str] = []
    for field in sorted(REQUIRED_DELIVERY_FIELDS):
        value = package.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def categorize_data_channel(channel_type: str) -> str:
    """
    Return 'primary', 'secondary', or 'housekeeping' for a given channel type.

    Raises ValueError for an unrecognized type.
    """
    if channel_type in _PRIMARY_TYPES:
        return "primary"
    if channel_type in _SECONDARY_TYPES:
        return "secondary"
    if channel_type in _HOUSEKEEPING_TYPES:
        return "housekeeping"
    raise ValueError(
        f"Unrecognized channel type {channel_type!r}. "
        "Cannot assign a data category."
    )


def determine_retention_period_days(test_phase: str) -> int:
    """
    Return the minimum data retention period (days) for a given test phase.

    Raises ValueError for an unrecognized phase.
    """
    if test_phase not in RETENTION_PERIODS_DAYS:
        raise ValueError(
            f"Unknown test phase {test_phase!r}. "
            f"Recognized phases: {sorted(RETENTION_PERIODS_DAYS)}"
        )
    return RETENTION_PERIODS_DAYS[test_phase]


def detect_data_gap(
    timestamps_s: list[float],
    max_gap_s: float,
) -> list[tuple[float, float]]:
    """
    Find consecutive timestamp pairs whose gap exceeds *max_gap_s*.

    Returns a list of (t_start, t_end) tuples for each gap found.
    Timestamps must be strictly increasing; raises ValueError otherwise.
    Raises ValueError if max_gap_s is not positive.
    """
    if max_gap_s <= 0:
        raise ValueError(f"max_gap_s must be positive, got {max_gap_s!r}")
    gaps: list[tuple[float, float]] = []
    for i in range(1, len(timestamps_s)):
        if timestamps_s[i] <= timestamps_s[i - 1]:
            raise ValueError(
                f"Timestamps must be strictly increasing: "
                f"index {i - 1}={timestamps_s[i - 1]}, index {i}={timestamps_s[i]}"
            )
        diff = timestamps_s[i] - timestamps_s[i - 1]
        if diff > max_gap_s:
            gaps.append((timestamps_s[i - 1], timestamps_s[i]))
    return gaps


def validate_data_format(fmt: str) -> bool:
    """
    Return True if *fmt* is a §4.3.5-recognised data format, False otherwise.
    """
    return fmt in VALID_DATA_FORMATS


def compute_channel_data_rate_bps(rate_hz: float, bits_per_sample: int) -> float:
    """
    Compute the raw bit-rate for a single channel (bits per second).

    Raises ValueError if either argument is non-positive.
    """
    if rate_hz <= 0:
        raise ValueError(f"rate_hz must be positive, got {rate_hz!r}")
    if bits_per_sample <= 0:
        raise ValueError(f"bits_per_sample must be positive, got {bits_per_sample!r}")
    return rate_hz * bits_per_sample

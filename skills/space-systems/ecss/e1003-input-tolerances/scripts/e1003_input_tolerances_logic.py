"""
Allowable test input tolerances — ECSS-E-ST-10C §4.4.2, Table 4-1 (paraphrased).

Provides a tolerance-band lookup and deviation check for each supported
test input type.  Returns a structured result dict; raises ValueError on
unrecognized input types or invalid numeric inputs.
"""

from __future__ import annotations
import math
from typing import NamedTuple


class ToleranceBand(NamedTuple):
    lo: float       # lower permitted deviation (inclusive)
    hi: float       # upper permitted deviation (inclusive)
    unit: str       # deviation unit label shown in findings
    bound_type: str # "absolute" | "percent" | "db"


# Paraphrased from ECSS-E-ST-10C §4.4.2 Table 4-1.
# "absolute" deviations in the same unit as the input (e.g. °C, %RH).
# "percent"  deviations in % relative to the nominal value.
# "db"       deviations in dB (10 · log10(actual / nominal), power ratio).
_TOLERANCE_TABLE: dict[str, ToleranceBand] = {
    "temperature":          ToleranceBand(-2.0,  2.0, "°C",  "absolute"),
    "pressure":             ToleranceBand(-2.0,  2.0, "%",   "percent"),
    "voltage":              ToleranceBand(-1.0,  1.0, "%",   "percent"),
    "frequency":            ToleranceBand(-0.1,  0.1, "%",   "percent"),
    "random_vibration_psd": ToleranceBand(-1.0,  0.0, "dB",  "db"),
    "sine_vibration":       ToleranceBand(-5.0,  5.0, "%",   "percent"),
    "acoustic_spl":         ToleranceBand(-2.0,  1.0, "dB",  "db"),
    "humidity":             ToleranceBand(-5.0,  5.0, "%RH", "absolute"),
    "duration":             ToleranceBand( 0.0,  2.0, "%",   "percent"),
}

SUPPORTED_INPUT_TYPES: list[str] = sorted(_TOLERANCE_TABLE.keys())


def get_tolerance(input_type: str) -> ToleranceBand:
    """Return the tolerance band for *input_type*; raise ValueError if unknown."""
    key = input_type.strip().lower()
    if key not in _TOLERANCE_TABLE:
        raise ValueError(
            f"Unrecognized test input type: {input_type!r}. "
            f"Supported types: {SUPPORTED_INPUT_TYPES}"
        )
    return _TOLERANCE_TABLE[key]


def compute_deviation(nominal: float, actual: float, bound_type: str) -> float:
    """
    Compute the deviation of *actual* from *nominal* in the units implied by
    *bound_type*.

    - "absolute": actual - nominal  (same physical unit as the input)
    - "percent":  (actual - nominal) / nominal * 100
    - "db":       10 * log10(actual / nominal)  (power-ratio convention)
    """
    if bound_type == "absolute":
        return actual - nominal
    if bound_type == "percent":
        if nominal == 0.0:
            raise ValueError(
                "Nominal value is zero; percent deviation is undefined."
            )
        return (actual - nominal) / nominal * 100.0
    if bound_type == "db":
        if nominal <= 0.0 or actual <= 0.0:
            raise ValueError(
                "dB deviation requires strictly positive nominal and actual values."
            )
        return 10.0 * math.log10(actual / nominal)
    raise ValueError(f"Unknown bound_type: {bound_type!r}")


def check_input_tolerance(
    input_type: str,
    nominal: float,
    actual: float,
) -> dict:
    """
    Check whether *actual* lies within the allowable band for *input_type*
    given a nominal target of *nominal*.

    Returns a result dict with keys:
      input_type       – str  : the queried type
      nominal          – float: the target value
      actual           – float: the applied value
      deviation        – float: computed deviation in band units
      band             – ToleranceBand
      within_tolerance – bool : True when lo <= deviation <= hi
      finding          – str | None: None if compliant; message if out-of-band

    Raises ValueError for unrecognized *input_type* or invalid values.
    """
    band = get_tolerance(input_type)
    deviation = compute_deviation(nominal, actual, band.bound_type)

    within = band.lo <= deviation <= band.hi
    finding = None
    if not within:
        finding = (
            f"{input_type}: deviation {deviation:.4g} {band.unit} "
            f"is outside the allowable band [{band.lo}, {band.hi}] {band.unit}."
        )

    return {
        "input_type": input_type,
        "nominal": nominal,
        "actual": actual,
        "deviation": deviation,
        "band": band,
        "within_tolerance": within,
        "finding": finding,
    }


def check_all_inputs(inputs: list[dict]) -> dict:
    """
    Check a batch of test inputs against their tolerance bands.

    Each element in *inputs* must have keys:
      input_type – str
      nominal    – float
      actual     – float

    Returns:
      results   – list[dict] : per-input check results
      compliant – bool       : True only when every input is within its band
      findings  – list[str]  : exceedance messages; empty list when compliant

    Raises ValueError if any element is missing a required key or has an
    unrecognized input type.
    """
    results: list[dict] = []
    findings: list[str] = []

    for idx, item in enumerate(inputs):
        for key in ("input_type", "nominal", "actual"):
            if key not in item:
                raise ValueError(
                    f"Input item at index {idx} is missing required key {key!r}."
                )
        result = check_input_tolerance(
            item["input_type"], item["nominal"], item["actual"]
        )
        results.append(result)
        if result["finding"]:
            findings.append(result["finding"])

    return {
        "results": results,
        "compliant": len(findings) == 0,
        "findings": findings,
    }

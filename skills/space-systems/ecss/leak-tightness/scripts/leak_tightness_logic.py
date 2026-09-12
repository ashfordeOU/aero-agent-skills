"""
Leak-tightness assessment logic for pressurized spacecraft structures.
Implements the procedure from ECSS-E-ST-32C clause 4.2.1.
Stdlib only; no external dependencies.
"""

import math
from typing import Dict, List, Tuple

# Maximum allowable leak rates by tightness class (mbar·L/s).
# Classes paraphrased from ECSS-E-ST-32C clause 4.2.1 hierarchy;
# LT1 is most stringent, LT4 least stringent.
LEAK_TIGHTNESS_CLASSES: Dict[str, float] = {
    "LT1": 1e-8,   # Most stringent — propellant tanks, safety-critical vessels
    "LT2": 1e-6,   # High — pressurant vessels, sealed instruments
    "LT3": 1e-4,   # Medium — structural pressure cavities
    "LT4": 1e-2,   # Low — non-critical sealed volumes
}

# Recognized physical categories of leak path in a pressurized structure
VALID_PATH_TYPES = frozenset({"seal", "penetration", "weld", "bond_line", "fitting"})


class LeakPathError(ValueError):
    """Raised when a leak path definition or input value is invalid."""


def categorize_leak_path(path_type: str) -> str:
    """
    Categorize a leak path into a recognized interface type.
    Returns the normalized path type string.
    Raises LeakPathError for unrecognized types.
    """
    normalized = path_type.strip().lower()
    if normalized not in VALID_PATH_TYPES:
        raise LeakPathError(
            f"Unrecognized leak path type '{path_type}'. "
            f"Valid types: {sorted(VALID_PATH_TYPES)}"
        )
    return normalized


def validate_leak_rate(rate: float) -> None:
    """Validate that a leak rate value is physically meaningful."""
    if not isinstance(rate, (int, float)):
        raise LeakPathError(
            f"Leak rate must be numeric, got {type(rate).__name__}"
        )
    if math.isnan(rate) or math.isinf(rate):
        raise LeakPathError(f"Leak rate must be finite, got {rate}")
    if rate < 0:
        raise LeakPathError(f"Leak rate must be non-negative, got {rate}")


def scale_leak_rate_to_operating(
    measured_rate: float,
    test_pressure: float,
    operating_pressure: float,
) -> float:
    """
    Scale a leak rate measured at test conditions to the operating pressure.
    Leak rate scales linearly with absolute pressure (viscous-flow regime).
    All pressure values must be in the same unit and strictly positive.
    """
    if test_pressure <= 0:
        raise LeakPathError(
            f"Test pressure must be positive, got {test_pressure}"
        )
    if operating_pressure <= 0:
        raise LeakPathError(
            f"Operating pressure must be positive, got {operating_pressure}"
        )
    validate_leak_rate(measured_rate)
    return measured_rate * (operating_pressure / test_pressure)


def get_allowable_rate(tightness_class: str) -> float:
    """Return the maximum allowable leak rate (mbar·L/s) for a given class."""
    if tightness_class not in LEAK_TIGHTNESS_CLASSES:
        raise LeakPathError(
            f"Unknown tightness class '{tightness_class}'. "
            f"Valid: {sorted(LEAK_TIGHTNESS_CLASSES)}"
        )
    return LEAK_TIGHTNESS_CLASSES[tightness_class]


def check_path_compliance(
    measured_rate: float,
    tightness_class: str,
) -> Tuple[bool, str]:
    """
    Check a single leak path against the class allowable rate.
    Returns (is_compliant, message).
    """
    validate_leak_rate(measured_rate)
    allowable = get_allowable_rate(tightness_class)
    compliant = measured_rate <= allowable
    if compliant:
        msg = (
            f"PASS: measured {measured_rate:.3e} <= allowable "
            f"{allowable:.3e} mbar·L/s"
        )
    else:
        excess = measured_rate / allowable
        msg = (
            f"FAIL: measured {measured_rate:.3e} > allowable "
            f"{allowable:.3e} mbar·L/s (excess factor {excess:.2f}x)"
        )
    return compliant, msg


def compute_system_leak_rate(path_rates: List[float]) -> float:
    """
    Compute the total system leak rate as the sum of all individual path rates.
    All rates in consistent units (mbar·L/s).
    Raises LeakPathError if the list is empty or contains invalid values.
    """
    if not path_rates:
        raise LeakPathError("path_rates must contain at least one entry")
    for rate in path_rates:
        validate_leak_rate(rate)
    return sum(path_rates)


def assess_leak_tightness(
    paths: List[Dict],
    tightness_class: str,
    margin_factor: float = 2.0,
) -> Dict:
    """
    Full leak-tightness assessment per ECSS-E-ST-32C clause 4.2.1.

    Each entry in `paths` requires:
        path_id       str   — unique identifier for the leak path
        path_type     str   — one of VALID_PATH_TYPES
        measured_rate float — measured or predicted leak rate (mbar·L/s)

    margin_factor divides the class allowable to form an effective design
    limit, reserving a compliance margin (must be >= 1.0; default 2.0).

    Returns a dict with:
        compliant       bool  — True only when every path and the system total pass
        system_rate     float — sum of all path rates (mbar·L/s)
        allowable_rate  float — nominal class allowable (mbar·L/s)
        effective_limit float — allowable / margin_factor
        margin_factor   float
        path_results    list  — per-path assessment dicts
        findings        list  — human-readable issue descriptions
    """
    if margin_factor < 1.0:
        raise LeakPathError(
            f"margin_factor must be >= 1.0, got {margin_factor}"
        )

    allowable = get_allowable_rate(tightness_class)
    effective_limit = allowable / margin_factor

    path_results: List[Dict] = []
    findings: List[str] = []
    rates: List[float] = []

    for path in paths:
        path_id = path.get("path_id", "<unknown>")
        path_type_raw = path.get("path_type", "")
        measured_rate = path.get("measured_rate")

        try:
            path_type = categorize_leak_path(path_type_raw)
        except LeakPathError as exc:
            findings.append(f"Path '{path_id}': {exc}")
            path_results.append({"path_id": path_id, "compliant": False, "error": str(exc)})
            rates.append(0.0)
            continue

        try:
            validate_leak_rate(measured_rate)
        except LeakPathError as exc:
            findings.append(f"Path '{path_id}': {exc}")
            path_results.append({"path_id": path_id, "compliant": False, "error": str(exc)})
            rates.append(0.0)
            continue

        path_compliant = measured_rate <= effective_limit
        if not path_compliant:
            findings.append(
                f"Path '{path_id}' ({path_type}): rate {measured_rate:.3e} "
                f"> effective limit {effective_limit:.3e} mbar·L/s"
            )
        path_results.append({
            "path_id": path_id,
            "path_type": path_type,
            "measured_rate": measured_rate,
            "compliant": path_compliant,
        })
        rates.append(measured_rate)

    system_rate = sum(rates)
    system_compliant = system_rate <= effective_limit
    if not system_compliant:
        findings.append(
            f"System total rate {system_rate:.3e} "
            f"> effective limit {effective_limit:.3e} mbar·L/s"
        )

    all_paths_ok = all(r.get("compliant", False) for r in path_results)
    overall_compliant = all_paths_ok and system_compliant

    return {
        "compliant": overall_compliant,
        "system_rate": system_rate,
        "allowable_rate": allowable,
        "effective_limit": effective_limit,
        "margin_factor": margin_factor,
        "path_results": path_results,
        "findings": findings,
    }

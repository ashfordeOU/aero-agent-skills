"""
e1011_offduty_logic.py

Off-duty station HFE compliance checker — ECSS-E-ST-10-11C §4.7.7.
Engineering thresholds are paraphrased from HFE criteria; not verbatim ECSS text.
"""

from __future__ import annotations
from typing import Any

VALID_STATION_TYPES = {"sleep", "hygiene", "recreation"}

# Thresholds paraphrased from ECSS-E-ST-10-11C §4.7.7 off-duty design criteria
SLEEP_REQUIREMENTS: dict[str, dict] = {
    "acoustic_attenuation_dB": {"min": 40},   # minimum noise reduction from ambient
    "lighting_lux_min": {"max": 0},            # must be capable of reaching full dark
    "lighting_lux_max": {"max": 200},          # upper task-lighting limit
    "temperature_c_min": {"min": 18},          # lower thermal comfort bound
    "temperature_c_max": {"max": 27},          # upper thermal comfort bound
    "volume_m3": {"min": 2.0},                 # personal envelope per crew member
    "restraint_system": {"required_true": True},
    "privacy_screen": {"required_true": True},
}

HYGIENE_REQUIREMENTS: dict[str, dict] = {
    "water_flow_ml_per_min": {"min": 50},
    "waste_containment": {"required_true": True},
    "accessibility_rating": {"min": 3, "max": 5},   # 1–5 scale
    "handhold_count": {"min": 2},
}

RECREATION_REQUIREMENTS: dict[str, dict] = {
    "comm_link_available": {"required_true": True},
    "exercise_volume_m3": {"min": 10.0},
    "lighting_lux": {"min": 300},
}

REQUIREMENTS_MAP: dict[str, dict[str, dict]] = {
    "sleep": SLEEP_REQUIREMENTS,
    "hygiene": HYGIENE_REQUIREMENTS,
    "recreation": RECREATION_REQUIREMENTS,
}


def validate_station_type(station_type: str) -> None:
    """Raise ValueError for any unrecognized station type."""
    if station_type not in VALID_STATION_TYPES:
        raise ValueError(
            f"Unrecognized station type '{station_type}'. "
            f"Must be one of {sorted(VALID_STATION_TYPES)}."
        )


def _check_param(name: str, value: Any, rule: dict) -> str | None:
    """Return a finding string when the parameter fails its rule, else None."""
    if "required_true" in rule:
        if value is not True:
            return f"{name}: must be True (got {value!r})"
        return None
    if "min" in rule and value < rule["min"]:
        return f"{name}: {value} is below minimum {rule['min']}"
    if "max" in rule and value > rule["max"]:
        return f"{name}: {value} exceeds maximum {rule['max']}"
    return None


def evaluate_station(station_type: str, params: dict) -> dict:
    """
    Evaluate one off-duty station against its HFE parameter requirements.

    Parameters
    ----------
    station_type : str
        One of 'sleep', 'hygiene', 'recreation'.
    params : dict
        Design-record or measured values keyed by parameter name.

    Returns
    -------
    dict with keys:
        station_type : str
        compliant    : bool
        findings     : list[str]  — parameter failures; empty when compliant
        missing      : list[str]  — required parameters absent from params
    """
    validate_station_type(station_type)
    requirements = REQUIREMENTS_MAP[station_type]
    findings: list[str] = []
    missing: list[str] = []

    for param_name, rule in requirements.items():
        if param_name not in params:
            missing.append(param_name)
            continue
        finding = _check_param(param_name, params[param_name], rule)
        if finding:
            findings.append(finding)

    return {
        "station_type": station_type,
        "compliant": len(findings) == 0 and len(missing) == 0,
        "findings": findings,
        "missing": missing,
    }


def evaluate_station_set(stations: list[dict]) -> dict:
    """
    Evaluate a list of off-duty stations and return aggregated results.

    Each entry must carry 'station_type' (str) and 'params' (dict) keys.

    Returns
    -------
    dict with keys:
        total           : int
        compliant_count : int
        all_compliant   : bool
        results         : list[dict]  — one result dict per station
    """
    if not stations:
        raise ValueError("Station list must not be empty.")

    results = []
    for i, entry in enumerate(stations):
        if "station_type" not in entry:
            raise ValueError(f"Station at index {i} is missing 'station_type'.")
        if "params" not in entry:
            raise ValueError(f"Station at index {i} is missing 'params'.")
        results.append(evaluate_station(entry["station_type"], entry["params"]))

    compliant_count = sum(1 for r in results if r["compliant"])
    return {
        "total": len(results),
        "compliant_count": compliant_count,
        "all_compliant": compliant_count == len(results),
        "results": results,
    }

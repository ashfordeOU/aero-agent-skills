"""
ECSS-E-ST-10-11C §4.7.1-4.7.2 — Habitable Environment Logic
Deterministic, offline, stdlib only.
Paraphrased procedure; ECSS clause cited as anchor only.
"""

# --- Thresholds (paraphrased from ECSS-E-ST-10-11C §4.7) ---

O2_PARTIAL_PRESSURE_MIN_KPA = 19.5
O2_PARTIAL_PRESSURE_MAX_KPA = 23.1
CO2_PARTIAL_PRESSURE_MAX_KPA = 0.5
TOTAL_PRESSURE_MIN_KPA = 70.0
TOTAL_PRESSURE_MAX_KPA = 102.7
TEMPERATURE_MIN_C = 18.0
TEMPERATURE_MAX_C = 27.0
HUMIDITY_MIN_PCT = 25.0
HUMIDITY_MAX_PCT = 75.0

MIN_VOLUME_PER_CREW_M3 = 11.3

REQUIRED_HYGIENE_PROVISIONS = frozenset([
    "waste_management",
    "personal_hygiene",
    "water_dispenser",
])

MIN_EGRESS_PATHS = 1
MIN_WORKSTATIONS_PER_CREW = 1

_ATM_REQUIRED_KEYS = frozenset(
    ["o2_kpa", "co2_kpa", "total_pressure_kpa", "temperature_c", "humidity_pct"]
)


def check_atmospheric_parameters(params: dict) -> list:
    """
    Validate atmospheric parameters for one compartment.
    params keys: o2_kpa, co2_kpa, total_pressure_kpa, temperature_c, humidity_pct.
    Returns list of finding strings; empty list means all parameters are in-band.
    Raises ValueError for missing keys.
    """
    missing = _ATM_REQUIRED_KEYS - set(params.keys())
    if missing:
        raise ValueError(f"Missing atmospheric parameter keys: {sorted(missing)}")

    findings = []

    if not (O2_PARTIAL_PRESSURE_MIN_KPA <= params["o2_kpa"] <= O2_PARTIAL_PRESSURE_MAX_KPA):
        findings.append(
            f"O2 partial pressure {params['o2_kpa']} kPa outside allowable band "
            f"[{O2_PARTIAL_PRESSURE_MIN_KPA}, {O2_PARTIAL_PRESSURE_MAX_KPA}] kPa"
        )

    if params["co2_kpa"] > CO2_PARTIAL_PRESSURE_MAX_KPA:
        findings.append(
            f"CO2 partial pressure {params['co2_kpa']} kPa exceeds limit of "
            f"{CO2_PARTIAL_PRESSURE_MAX_KPA} kPa"
        )

    if not (TOTAL_PRESSURE_MIN_KPA <= params["total_pressure_kpa"] <= TOTAL_PRESSURE_MAX_KPA):
        findings.append(
            f"Total cabin pressure {params['total_pressure_kpa']} kPa outside allowable band "
            f"[{TOTAL_PRESSURE_MIN_KPA}, {TOTAL_PRESSURE_MAX_KPA}] kPa"
        )

    if not (TEMPERATURE_MIN_C <= params["temperature_c"] <= TEMPERATURE_MAX_C):
        findings.append(
            f"Temperature {params['temperature_c']} deg C outside allowable band "
            f"[{TEMPERATURE_MIN_C}, {TEMPERATURE_MAX_C}] deg C"
        )

    if not (HUMIDITY_MIN_PCT <= params["humidity_pct"] <= HUMIDITY_MAX_PCT):
        findings.append(
            f"Relative humidity {params['humidity_pct']} % outside allowable band "
            f"[{HUMIDITY_MIN_PCT}, {HUMIDITY_MAX_PCT}] %"
        )

    return findings


def check_habitable_volume(total_volume_m3: float, crew_count: int) -> list:
    """
    Check that net habitable volume per crew member meets the minimum threshold.
    Returns list of finding strings; empty list means volume is adequate.
    Raises ValueError for invalid inputs.
    """
    if crew_count <= 0:
        raise ValueError("crew_count must be a positive integer")
    if total_volume_m3 < 0:
        raise ValueError("total_volume_m3 must be non-negative")

    per_person = total_volume_m3 / crew_count
    if per_person < MIN_VOLUME_PER_CREW_M3:
        return [
            f"Net habitable volume per crew member {per_person:.2f} m3 is below the "
            f"minimum {MIN_VOLUME_PER_CREW_M3} m3/person "
            f"(total {total_volume_m3} m3, crew {crew_count})"
        ]
    return []


def check_layout(egress_path_count: int, workstation_count: int, crew_count: int) -> list:
    """
    Check emergency egress path count and workstation provisioning.
    Returns list of finding strings; empty list means layout provisions are met.
    Raises ValueError for invalid crew_count.
    """
    if crew_count <= 0:
        raise ValueError("crew_count must be a positive integer")

    findings = []
    if egress_path_count < MIN_EGRESS_PATHS:
        findings.append(
            f"Egress path count {egress_path_count} below minimum {MIN_EGRESS_PATHS} "
            f"for compartment"
        )
    required_ws = MIN_WORKSTATIONS_PER_CREW * crew_count
    if workstation_count < required_ws:
        findings.append(
            f"Workstation count {workstation_count} below minimum {required_ws} "
            f"for crew of {crew_count}"
        )
    return findings


def check_hygiene_provisions(provisions) -> list:
    """
    Verify all required hygiene provisions are allocated for the compartment.
    provisions: iterable of provision identifier strings.
    Returns list of finding strings for each missing provision; empty list means compliant.
    """
    missing = REQUIRED_HYGIENE_PROVISIONS - set(provisions)
    return [f"Hygiene provision not allocated: {item}" for item in sorted(missing)]


def evaluate_habitability(
    compartment_id: str,
    total_volume_m3: float,
    crew_count: int,
    atm_params: dict,
    egress_path_count: int,
    workstation_count: int,
    hygiene_provisions,
) -> dict:
    """
    Aggregate all habitability checks for one compartment.
    Returns dict:
      compartment_id: str
      compliant: bool (True only when findings list is empty)
      findings: list of str
    """
    findings = []
    findings.extend(check_habitable_volume(total_volume_m3, crew_count))
    findings.extend(check_atmospheric_parameters(atm_params))
    findings.extend(check_layout(egress_path_count, workstation_count, crew_count))
    findings.extend(check_hygiene_provisions(hygiene_provisions))
    return {
        "compartment_id": compartment_id,
        "compliant": len(findings) == 0,
        "findings": findings,
    }

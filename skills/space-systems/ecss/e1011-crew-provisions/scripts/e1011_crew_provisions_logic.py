# ECSS-E-ST-10C §4.7.5 — Crew station provisions checker
# Paraphrase of standard requirements; not verbatim ECSS text.
# Reference anchor: ECSS-E-ST-10C clause 4.7.5.

from dataclasses import dataclass
from typing import List

# Recognized station functional types (§4.7.5 categorization).
STATION_TYPES = {"piloting", "mission", "payload", "maintenance"}

# Anthropometric envelope constants — 5th-to-95th percentile combined crew.
SEAT_WIDTH_MIN_MM = 430       # minimum seat pan width
SEAT_DEPTH_MIN_MM = 380       # minimum seat pan depth
REACH_ENVELOPE_MM = 700       # maximum forward reach from torso reference point
CONSOLE_HEIGHT_MAX_MM = 1300  # maximum control/display height above deck reference
CONSOLE_HEIGHT_MIN_MM = 600   # minimum control/display height above deck reference

# Restraint structural load minimums (N) — per §4.7.5 attachment requirements.
RESTRAINT_SHOULDER_MIN_N = 8000
RESTRAINT_LAP_MIN_N = 12000
RESTRAINT_FOOTREST_MIN_N = 4000

# Egress path minimum clear width (mm).
EGRESS_MIN_CLEARANCE_MM = 600


class CrewProvisionError(ValueError):
    """Raised when a station specification is invalid or cannot be assessed."""


@dataclass
class SeatSpec:
    seat_id: str
    width_mm: float
    depth_mm: float
    shoulder_restraint_n: float
    lap_restraint_n: float
    footrest_n: float


@dataclass
class ConsoleSpec:
    console_id: str
    station_type: str
    height_min_mm: float
    height_max_mm: float
    reach_mm: float


@dataclass
class StationProvision:
    station_id: str
    station_type: str
    seat: SeatSpec
    console: ConsoleSpec
    egress_clearance_mm: float


def validate_station_type(station_type: str) -> None:
    if station_type not in STATION_TYPES:
        raise CrewProvisionError(
            f"Unknown station type '{station_type}'. "
            f"Must be one of: {sorted(STATION_TYPES)}"
        )


def check_seat_geometry(seat: SeatSpec) -> List[str]:
    """Return findings for seat pan geometry; empty list means conformant."""
    findings = []
    if seat.width_mm < SEAT_WIDTH_MIN_MM:
        findings.append(
            f"Seat {seat.seat_id}: width {seat.width_mm} mm "
            f"< minimum {SEAT_WIDTH_MIN_MM} mm"
        )
    if seat.depth_mm < SEAT_DEPTH_MIN_MM:
        findings.append(
            f"Seat {seat.seat_id}: depth {seat.depth_mm} mm "
            f"< minimum {SEAT_DEPTH_MIN_MM} mm"
        )
    return findings


def check_restraint_loads(seat: SeatSpec) -> List[str]:
    """Return findings for restraint load capacity; empty list means conformant."""
    findings = []
    if seat.shoulder_restraint_n < RESTRAINT_SHOULDER_MIN_N:
        findings.append(
            f"Seat {seat.seat_id}: shoulder restraint {seat.shoulder_restraint_n} N "
            f"< minimum {RESTRAINT_SHOULDER_MIN_N} N"
        )
    if seat.lap_restraint_n < RESTRAINT_LAP_MIN_N:
        findings.append(
            f"Seat {seat.seat_id}: lap restraint {seat.lap_restraint_n} N "
            f"< minimum {RESTRAINT_LAP_MIN_N} N"
        )
    if seat.footrest_n < RESTRAINT_FOOTREST_MIN_N:
        findings.append(
            f"Seat {seat.seat_id}: footrest load {seat.footrest_n} N "
            f"< minimum {RESTRAINT_FOOTREST_MIN_N} N"
        )
    return findings


def check_console_envelope(console: ConsoleSpec) -> List[str]:
    """Return findings for console geometry; empty list means conformant."""
    validate_station_type(console.station_type)
    findings = []
    if console.height_min_mm < CONSOLE_HEIGHT_MIN_MM:
        findings.append(
            f"Console {console.console_id}: lower edge {console.height_min_mm} mm "
            f"< minimum {CONSOLE_HEIGHT_MIN_MM} mm above deck"
        )
    if console.height_max_mm > CONSOLE_HEIGHT_MAX_MM:
        findings.append(
            f"Console {console.console_id}: upper edge {console.height_max_mm} mm "
            f"> maximum {CONSOLE_HEIGHT_MAX_MM} mm above deck"
        )
    if console.reach_mm > REACH_ENVELOPE_MM:
        findings.append(
            f"Console {console.console_id}: control reach {console.reach_mm} mm "
            f"> maximum reach {REACH_ENVELOPE_MM} mm from torso reference"
        )
    return findings


def check_egress_clearance(station: StationProvision) -> List[str]:
    """Return findings for egress clearance; empty list means conformant."""
    findings = []
    if station.egress_clearance_mm < EGRESS_MIN_CLEARANCE_MM:
        findings.append(
            f"Station {station.station_id}: egress clearance "
            f"{station.egress_clearance_mm} mm "
            f"< minimum {EGRESS_MIN_CLEARANCE_MM} mm"
        )
    return findings


def assess_station(station: StationProvision) -> dict:
    """
    Full crew station provisions assessment per §4.7.5.
    Returns dict with per-check findings and overall compliance flag.
    Raises CrewProvisionError for invalid or internally inconsistent specs.
    """
    validate_station_type(station.station_type)
    if station.station_type != station.console.station_type:
        raise CrewProvisionError(
            f"Station {station.station_id}: station_type '{station.station_type}' "
            f"does not match console station_type '{station.console.station_type}'"
        )

    seat_geo = check_seat_geometry(station.seat)
    restraint = check_restraint_loads(station.seat)
    console_env = check_console_envelope(station.console)
    egress = check_egress_clearance(station)

    all_findings = seat_geo + restraint + console_env + egress
    return {
        "station_id": station.station_id,
        "seat_geometry_findings": seat_geo,
        "restraint_findings": restraint,
        "console_findings": console_env,
        "egress_findings": egress,
        "compliant": len(all_findings) == 0,
        "findings": all_findings,
    }


def assess_all_stations(stations: List[StationProvision]) -> dict:
    """Assess a list of crew stations; returns fleet-level aggregate report."""
    if not stations:
        raise CrewProvisionError("Station list must not be empty")
    results = [assess_station(s) for s in stations]
    non_compliant = [r for r in results if not r["compliant"]]
    return {
        "station_count": len(stations),
        "compliant_count": len(results) - len(non_compliant),
        "non_compliant_count": len(non_compliant),
        "all_compliant": len(non_compliant) == 0,
        "stations": results,
    }


def categorize_stations_by_type(stations: List[StationProvision]) -> dict:
    """
    Group station IDs by their functional type.
    Raises CrewProvisionError for any station with an unrecognized type.
    """
    grouped: dict = {t: [] for t in STATION_TYPES}
    for s in stations:
        validate_station_type(s.station_type)
        grouped[s.station_type].append(s.station_id)
    return grouped

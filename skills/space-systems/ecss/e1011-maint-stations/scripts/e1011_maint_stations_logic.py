# e1011_maint_stations_logic.py
# ECSS-E-ST-10-11C §4.7.8 — Physical maintenance station design logic.
# Paraphrased procedure; cite clause as anchor only. No verbatim standard text.

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class MaintenanceZoneType(Enum):
    IVA = "iva"
    EVA = "eva"
    HYBRID = "hybrid"


class TaskFrequency(Enum):
    ROUTINE = "routine"
    ON_CONDITION = "on_condition"
    CORRECTIVE = "corrective"


# ── Minimum dimensional thresholds (ECSS-E-ST-10-11C §4.7.8 anchor) ─────────

IVA_MIN_REACH_DEPTH_MM = 400.0
IVA_MIN_LATERAL_CLEARANCE_MM = 450.0
IVA_MIN_VERTICAL_CLEARANCE_MM = 500.0

EVA_MIN_REACH_DEPTH_MM = 600.0
EVA_MIN_LATERAL_CLEARANCE_MM = 700.0
EVA_MIN_VERTICAL_CLEARANCE_MM = 750.0

MIN_LIGHTING_IVA_LUX = 150.0
MIN_LIGHTING_EVA_LUX = 100.0

# Tools whose single-hand operating arc exceeds this must be flagged.
MAX_SINGLE_HAND_TOOL_ENVELOPE_MM = 300.0


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class AccessZone:
    reach_depth_mm: float
    lateral_clearance_mm: float
    vertical_clearance_mm: float
    zone_type: MaintenanceZoneType


@dataclass
class Tool:
    tool_id: str
    name: str
    max_envelope_mm: float
    requires_two_hands: bool
    iva_compatible: bool
    eva_compatible: bool


@dataclass
class MaintenanceTask:
    task_id: str
    description: str
    frequency: TaskFrequency
    tools: List[str]
    zone_type: MaintenanceZoneType
    estimated_duration_min: float
    requires_visual_access: bool


@dataclass
class MaintenanceStation:
    station_id: str
    name: str
    access_zone: AccessZone
    tools_on_record: List[Tool] = field(default_factory=list)
    tasks: List[MaintenanceTask] = field(default_factory=list)
    lighting_lux: Optional[float] = None


# ── Finding types ────────────────────────────────────────────────────────────

@dataclass
class AccessFinding:
    station_id: str
    axis: str
    required_mm: float
    actual_mm: float
    compliant: bool

    def as_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "axis": self.axis,
            "required_mm": self.required_mm,
            "actual_mm": self.actual_mm,
            "compliant": self.compliant,
        }


@dataclass
class ToolingFinding:
    station_id: str
    tool_id: str
    issue: str

    def as_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "tool_id": self.tool_id,
            "issue": self.issue,
        }


@dataclass
class LightingFinding:
    station_id: str
    required_lux: float
    actual_lux: Optional[float]
    compliant: bool

    def as_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "required_lux": self.required_lux,
            "actual_lux": self.actual_lux,
            "compliant": self.compliant,
        }


@dataclass
class TaskCategorization:
    task_id: str
    frequency: str
    zone_type: str
    tool_ids: List[str]
    duration_min: float
    unresolved_tools: List[str]

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "frequency": self.frequency,
            "zone_type": self.zone_type,
            "tool_ids": self.tool_ids,
            "duration_min": self.duration_min,
            "unresolved_tools": self.unresolved_tools,
        }


@dataclass
class StationAssessmentResult:
    station_id: str
    access_findings: List[AccessFinding]
    tooling_findings: List[ToolingFinding]
    lighting_findings: List[LightingFinding]
    task_categorizations: List[TaskCategorization]
    compliant: bool

    def as_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "access_findings": [f.as_dict() for f in self.access_findings],
            "tooling_findings": [f.as_dict() for f in self.tooling_findings],
            "lighting_findings": [f.as_dict() for f in self.lighting_findings],
            "task_categorizations": [t.as_dict() for t in self.task_categorizations],
            "compliant": self.compliant,
        }


# ── Assessment functions ─────────────────────────────────────────────────────

def _thresholds_for_zone(zt: MaintenanceZoneType):
    """Return (reach, lateral, vertical) minimum mm for the zone type."""
    if zt in (MaintenanceZoneType.EVA, MaintenanceZoneType.HYBRID):
        return EVA_MIN_REACH_DEPTH_MM, EVA_MIN_LATERAL_CLEARANCE_MM, EVA_MIN_VERTICAL_CLEARANCE_MM
    return IVA_MIN_REACH_DEPTH_MM, IVA_MIN_LATERAL_CLEARANCE_MM, IVA_MIN_VERTICAL_CLEARANCE_MM


def check_access_zone(station: MaintenanceStation) -> List[AccessFinding]:
    """
    Verify the access zone meets minimum dimensional thresholds for its zone
    type. Returns one AccessFinding per axis (reach, lateral, vertical).
    ECSS-E-ST-10-11C §4.7.8 anchor.
    """
    z = station.access_zone
    min_reach, min_lat, min_vert = _thresholds_for_zone(z.zone_type)
    return [
        AccessFinding(station.station_id, "reach", min_reach, z.reach_depth_mm,
                      z.reach_depth_mm >= min_reach),
        AccessFinding(station.station_id, "lateral", min_lat, z.lateral_clearance_mm,
                      z.lateral_clearance_mm >= min_lat),
        AccessFinding(station.station_id, "vertical", min_vert, z.vertical_clearance_mm,
                      z.vertical_clearance_mm >= min_vert),
    ]


def check_tooling(station: MaintenanceStation) -> List[ToolingFinding]:
    """
    Verify each registered tool is compatible with the station zone type.
    Flag large-envelope single-hand tools that may exceed operating arc limits.
    ECSS-E-ST-10-11C §4.7.8 anchor.
    """
    findings: List[ToolingFinding] = []
    zt = station.access_zone.zone_type

    for tool in station.tools_on_record:
        if zt == MaintenanceZoneType.IVA and not tool.iva_compatible:
            findings.append(ToolingFinding(
                station.station_id, tool.tool_id,
                f"Tool '{tool.name}' is not IVA-compatible but station is IVA zone.",
            ))
        elif zt == MaintenanceZoneType.EVA and not tool.eva_compatible:
            findings.append(ToolingFinding(
                station.station_id, tool.tool_id,
                f"Tool '{tool.name}' is not EVA-compatible but station is EVA zone.",
            ))
        elif zt == MaintenanceZoneType.HYBRID and not (tool.iva_compatible and tool.eva_compatible):
            findings.append(ToolingFinding(
                station.station_id, tool.tool_id,
                f"Tool '{tool.name}' must support both IVA and EVA for HYBRID zone.",
            ))

        if (tool.max_envelope_mm > MAX_SINGLE_HAND_TOOL_ENVELOPE_MM
                and not tool.requires_two_hands):
            findings.append(ToolingFinding(
                station.station_id, tool.tool_id,
                (f"Tool '{tool.name}' envelope {tool.max_envelope_mm} mm exceeds "
                 f"{MAX_SINGLE_HAND_TOOL_ENVELOPE_MM} mm single-hand limit; "
                 "verify operating arc clearance or designate as two-hand."),
            ))
    return findings


def check_lighting(station: MaintenanceStation) -> List[LightingFinding]:
    """
    Verify recorded lighting level meets the minimum lux for the zone type.
    A missing value is a non-compliant finding.
    ECSS-E-ST-10-11C §4.7.8 anchor.
    """
    zt = station.access_zone.zone_type
    required = MIN_LIGHTING_EVA_LUX if zt == MaintenanceZoneType.EVA else MIN_LIGHTING_IVA_LUX
    actual = station.lighting_lux
    return [LightingFinding(
        station.station_id,
        required,
        actual,
        actual is not None and actual >= required,
    )]


def categorize_tasks(station: MaintenanceStation) -> List[TaskCategorization]:
    """
    Categorize each maintenance task by frequency and zone type; flag tasks
    that reference tools not on record at the station.
    ECSS-E-ST-10-11C §4.7.8 anchor.
    """
    on_record = {t.tool_id for t in station.tools_on_record}
    result = []
    for task in station.tasks:
        unresolved = [tid for tid in task.tools if tid not in on_record]
        result.append(TaskCategorization(
            task_id=task.task_id,
            frequency=task.frequency.value,
            zone_type=task.zone_type.value,
            tool_ids=list(task.tools),
            duration_min=task.estimated_duration_min,
            unresolved_tools=unresolved,
        ))
    return result


def assess_station(station: MaintenanceStation) -> StationAssessmentResult:
    """
    Run the full §4.7.8 station assessment: access zone dimensions, tooling
    compatibility, lighting, and task categorization.
    Station is compliant only when all sub-checks pass with no findings.
    """
    access = check_access_zone(station)
    tooling = check_tooling(station)
    lighting = check_lighting(station)
    tasks = categorize_tasks(station)

    compliant = (
        all(f.compliant for f in access)
        and len(tooling) == 0
        and all(f.compliant for f in lighting)
        and all(len(t.unresolved_tools) == 0 for t in tasks)
    )
    return StationAssessmentResult(
        station_id=station.station_id,
        access_findings=access,
        tooling_findings=tooling,
        lighting_findings=lighting,
        task_categorizations=tasks,
        compliant=compliant,
    )


def assess_multiple_stations(
    stations: List[MaintenanceStation],
) -> Dict[str, StationAssessmentResult]:
    """Assess a list of stations, returning results keyed by station_id."""
    return {s.station_id: assess_station(s) for s in stations}

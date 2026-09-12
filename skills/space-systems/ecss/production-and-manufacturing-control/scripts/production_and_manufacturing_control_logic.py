"""
Production and manufacturing control logic for ECSS-E-ST-32 section 4.7.

Checks manufacturing process authorization, drawing revision currency,
tooling qualification, assembly procedure completeness, storage condition
compliance, cleanliness level definition, and health-and-safety hazard
mitigation status. All logic is deterministic and offline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class ProcessStatus(Enum):
    AUTHORIZED = "authorized"
    UNAUTHORIZED = "unauthorized"
    PENDING = "pending"


@dataclass
class ManufacturingProcess:
    name: str
    status: ProcessStatus
    process_document_id: Optional[str] = None


@dataclass
class EngineeringDrawing:
    number: str
    revision: str
    latest_revision: str


@dataclass
class Tool:
    tool_id: str
    is_qualified: bool
    traceability_ref: Optional[str] = None


@dataclass
class AssemblyProcedure:
    procedure_id: str
    has_acceptance_criteria: bool
    has_traveler_record: bool


@dataclass
class StorageCondition:
    item_id: str
    temperature_c: float
    temp_min_c: float
    temp_max_c: float
    relative_humidity_pct: float
    humidity_max_pct: float


@dataclass
class CleanlinessRequirement:
    item_id: str
    cleanliness_level: Optional[str]
    monitoring_active: bool


@dataclass
class HazardRecord:
    hazard_id: str
    description: str
    mitigation: Optional[str]
    is_mitigated: bool


Finding = Tuple[bool, str]


def check_process_authorization(process: ManufacturingProcess) -> Finding:
    """
    Returns (True, message) when the process is authorized and documented;
    (False, finding) otherwise.
    """
    if process.status == ProcessStatus.AUTHORIZED:
        if not process.process_document_id:
            return (
                False,
                f"Process '{process.name}' is authorized but lacks a process document "
                "reference; the document must be on record before manufacturing proceeds.",
            )
        return (
            True,
            f"Process '{process.name}' is authorized (doc: {process.process_document_id}).",
        )
    if process.status == ProcessStatus.PENDING:
        return (
            False,
            f"Process '{process.name}' is pending authorization; hardware cannot "
            "advance until authorization is granted.",
        )
    return (
        False,
        f"Process '{process.name}' is not authorized; manufacturing must halt until "
        "authorization is obtained.",
    )


def check_drawing_revision(drawing: EngineeringDrawing) -> Finding:
    """
    Returns (True, message) when the drawing is at its latest approved revision;
    (False, finding) when a superseded revision is in use.
    """
    if drawing.revision == drawing.latest_revision:
        return (
            True,
            f"Drawing {drawing.number} is at current revision {drawing.revision}.",
        )
    return (
        False,
        f"Drawing {drawing.number} revision {drawing.revision} is superseded; "
        f"revision {drawing.latest_revision} must be in use before work proceeds.",
    )


def check_tooling_qualification(tool: Tool) -> Finding:
    """
    Returns (True, message) when the tool is qualified and has a traceability
    reference; (False, finding) for either deficiency.
    """
    if not tool.is_qualified:
        return (
            False,
            f"Tool {tool.tool_id} is not qualified; it must be removed from the "
            "build station until qualification is complete.",
        )
    if not tool.traceability_ref:
        return (
            False,
            f"Tool {tool.tool_id} is qualified but has no traceability reference "
            "on record; a calibration or qualification record must be retrieved.",
        )
    return (
        True,
        f"Tool {tool.tool_id} is qualified and traceable (ref: {tool.traceability_ref}).",
    )


def check_assembly_procedure(procedure: AssemblyProcedure) -> Finding:
    """
    Returns (True, message) when the procedure has both acceptance criteria and a
    traveler record; (False, finding) listing each deficiency.
    """
    deficiencies = []
    if not procedure.has_acceptance_criteria:
        deficiencies.append("missing acceptance criteria")
    if not procedure.has_traveler_record:
        deficiencies.append("missing traveler record")
    if deficiencies:
        return (
            False,
            f"Procedure {procedure.procedure_id} has deficiencies: "
            f"{', '.join(deficiencies)}; the procedure must be updated before use.",
        )
    return (
        True,
        f"Procedure {procedure.procedure_id} has acceptance criteria and traveler record.",
    )


def check_storage_condition(condition: StorageCondition) -> Finding:
    """
    Returns (True, message) when temperature and humidity are within specification;
    (False, finding) listing every parameter violation.

    Each violation states the direction of the excursion explicitly: a parameter
    under its lower limit is reported as "below the minimum", one over its upper
    limit as "above maximum", so the direction can be read off the finding text.
    """
    violations = []
    if condition.temperature_c < condition.temp_min_c:
        violations.append(
            f"temperature {condition.temperature_c}°C is below the minimum "
            f"{condition.temp_min_c}°C"
        )
    if condition.temperature_c > condition.temp_max_c:
        violations.append(
            f"temperature {condition.temperature_c}°C is above maximum permitted "
            f"{condition.temp_max_c}°C"
        )
    if condition.relative_humidity_pct > condition.humidity_max_pct:
        violations.append(
            f"relative humidity {condition.relative_humidity_pct}% is above maximum "
            f"permitted {condition.humidity_max_pct}%"
        )
    if violations:
        return (
            False,
            f"Storage violation for item {condition.item_id}: "
            f"{'; '.join(violations)}; initiate non-conformance process.",
        )
    return (
        True,
        f"Storage conditions for item {condition.item_id} are within specification.",
    )


def check_cleanliness_level(req: CleanlinessRequirement) -> Finding:
    """
    Returns (True, message) when the cleanliness level is defined and active
    monitoring is in place; (False, finding) for either deficiency.
    """
    if req.cleanliness_level is None:
        return (
            False,
            f"Item {req.item_id} has no cleanliness level defined; the requirement "
            "must be established before manufacturing proceeds.",
        )
    if not req.monitoring_active:
        return (
            False,
            f"Item {req.item_id} has cleanliness level {req.cleanliness_level} defined "
            "but no active monitoring is in place; monitoring must be established.",
        )
    return (
        True,
        f"Item {req.item_id} has cleanliness level {req.cleanliness_level} with "
        "active monitoring confirmed.",
    )


def check_hazard_mitigation(hazard: HazardRecord) -> Finding:
    """
    Returns (True, message) when the hazard is confirmed mitigated; (False, finding)
    when the mitigation is absent or not yet confirmed in place.
    """
    if hazard.is_mitigated:
        return (True, f"Hazard {hazard.hazard_id} ('{hazard.description}') is mitigated.")
    if not hazard.mitigation:
        return (
            False,
            f"Hazard {hazard.hazard_id} ('{hazard.description}') has no mitigation "
            "defined; the associated operation must not begin.",
        )
    return (
        False,
        f"Hazard {hazard.hazard_id} ('{hazard.description}') has a mitigation "
        f"plan ('{hazard.mitigation}') but it is not yet confirmed in place; "
        "work must not start until verification is complete.",
    )


@dataclass
class ProductionReviewResult:
    passed: bool
    findings: List[str]
    summary: str


def run_production_control_review(
    processes: List[ManufacturingProcess],
    drawings: List[EngineeringDrawing],
    tools: List[Tool],
    procedures: List[AssemblyProcedure],
    storage_conditions: List[StorageCondition],
    cleanliness_reqs: List[CleanlinessRequirement],
    hazards: List[HazardRecord],
) -> ProductionReviewResult:
    """
    Aggregate all production and manufacturing control checks. Returns a
    ProductionReviewResult with passed=True only when every check passes.
    """
    findings: List[str] = []

    for process in processes:
        ok, msg = check_process_authorization(process)
        if not ok:
            findings.append(msg)

    for drawing in drawings:
        ok, msg = check_drawing_revision(drawing)
        if not ok:
            findings.append(msg)

    for tool in tools:
        ok, msg = check_tooling_qualification(tool)
        if not ok:
            findings.append(msg)

    for procedure in procedures:
        ok, msg = check_assembly_procedure(procedure)
        if not ok:
            findings.append(msg)

    for condition in storage_conditions:
        ok, msg = check_storage_condition(condition)
        if not ok:
            findings.append(msg)

    for req in cleanliness_reqs:
        ok, msg = check_cleanliness_level(req)
        if not ok:
            findings.append(msg)

    for hazard in hazards:
        ok, msg = check_hazard_mitigation(hazard)
        if not ok:
            findings.append(msg)

    passed = len(findings) == 0
    summary = (
        "Production and manufacturing control review PASSED — all checks compliant."
        if passed
        else (
            f"Production and manufacturing control review FAILED — "
            f"{len(findings)} finding(s) require resolution before hardware can advance."
        )
    )
    return ProductionReviewResult(passed=passed, findings=findings, summary=summary)

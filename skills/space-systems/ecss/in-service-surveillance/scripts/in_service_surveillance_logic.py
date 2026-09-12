"""
in_service_surveillance_logic.py

In-service surveillance assessment per ECSS-E-ST-32C section 4.8.
Covers inspection planning, damage evaluation, and maintenance decisions.
stdlib only — no third-party dependencies.
"""

from dataclasses import dataclass, field
from typing import List, Set
from enum import Enum


class Criticality(Enum):
    FRACTURE_CRITICAL = 1
    SIGNIFICANT = 2
    STANDARD = 3


class InspectionType(Enum):
    VISUAL = "visual"
    NDT = "ndt"
    DIMENSIONAL = "dimensional"


class MaintenanceDecision(Enum):
    ACCEPT = "accept"
    ACCEPT_CONTINUE_FLY = "accept_continue_fly"
    FLAG = "flag"
    REPAIR = "repair"
    REPLACE = "replace"


class DamageType(Enum):
    CRACK = "crack"
    DENT = "dent"
    CORROSION = "corrosion"
    DELAMINATION = "delamination"
    IMPACT = "impact"
    SCRATCH = "scratch"


# Criticality multipliers for inspection interval
_CRITICALITY_FACTOR = {
    Criticality.FRACTURE_CRITICAL: 0.5,
    Criticality.SIGNIFICANT: 0.75,
    Criticality.STANDARD: 1.0,
}

# Fatigue fraction above which the interval is further halved
HIGH_FATIGUE_THRESHOLD = 0.8

# Interval reduction factor when fatigue threshold is exceeded
INTERVAL_REDUCTION_FACTOR = 0.5

# Damage beyond allowable * this multiplier triggers REPAIR or REPLACE
EXTENDED_DAMAGE_MULTIPLIER = 2.0


@dataclass
class InspectionItem:
    item_id: str
    criticality: Criticality
    inspection_type: InspectionType
    fatigue_fraction: float       # [0.0, 1.0] — fraction of fatigue life consumed
    base_interval_hours: float    # Base inspection interval in flight hours


@dataclass
class DamageReport:
    item_id: str
    damage_type: DamageType
    damage_size: float            # Measured size in consistent units (e.g. mm)
    allowable_limit: float        # Allowable damage limit for this item
    has_residual_strength_analysis: bool
    can_be_repaired: bool = True


@dataclass
class InspectionSchedule:
    item_id: str
    criticality: Criticality
    inspection_type: InspectionType
    interval_hours: float
    reduced_interval: bool        # True when interval was halved due to high fatigue


@dataclass
class DamageDisposition:
    item_id: str
    damage_size: float
    allowable_limit: float
    decision: MaintenanceDecision
    rationale: str


@dataclass
class SurveillanceResult:
    compliant: bool
    inspection_schedules: List[InspectionSchedule] = field(default_factory=list)
    damage_dispositions: List[DamageDisposition] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)


def assign_inspection_interval(item: InspectionItem) -> InspectionSchedule:
    """
    Compute the inspection schedule for one structural item.
    ECSS-E-ST-32C section 4.8.

    Interval = base_interval * criticality_factor, then halved if
    fatigue_fraction > HIGH_FATIGUE_THRESHOLD.
    """
    if not isinstance(item.criticality, Criticality):
        raise ValueError(f"Unrecognised criticality value: {item.criticality!r}")
    if not (0.0 <= item.fatigue_fraction <= 1.0):
        raise ValueError(
            f"fatigue_fraction must be in [0.0, 1.0]; got {item.fatigue_fraction}"
        )
    if item.base_interval_hours <= 0.0:
        raise ValueError(
            f"base_interval_hours must be positive; got {item.base_interval_hours}"
        )

    interval = item.base_interval_hours * _CRITICALITY_FACTOR[item.criticality]

    reduced = False
    if item.fatigue_fraction > HIGH_FATIGUE_THRESHOLD:
        interval *= INTERVAL_REDUCTION_FACTOR
        reduced = True

    return InspectionSchedule(
        item_id=item.item_id,
        criticality=item.criticality,
        inspection_type=item.inspection_type,
        interval_hours=interval,
        reduced_interval=reduced,
    )


def evaluate_damage(report: DamageReport) -> DamageDisposition:
    """
    Evaluate detected damage against the allowable damage limit.
    ECSS-E-ST-32C section 4.8.

    Returns a disposition with a MaintenanceDecision and rationale string.
    """
    if report.damage_size < 0.0:
        raise ValueError(
            f"damage_size cannot be negative; got {report.damage_size}"
        )
    if report.allowable_limit <= 0.0:
        raise ValueError(
            f"allowable_limit must be positive; got {report.allowable_limit}"
        )

    extended_limit = report.allowable_limit * EXTENDED_DAMAGE_MULTIPLIER

    if report.damage_size <= report.allowable_limit:
        return DamageDisposition(
            item_id=report.item_id,
            damage_size=report.damage_size,
            allowable_limit=report.allowable_limit,
            decision=MaintenanceDecision.ACCEPT,
            rationale=(
                "Damage is within the allowable damage limit. "
                "Document and monitor at the next scheduled inspection."
            ),
        )

    if report.damage_size <= extended_limit:
        if report.has_residual_strength_analysis:
            return DamageDisposition(
                item_id=report.item_id,
                damage_size=report.damage_size,
                allowable_limit=report.allowable_limit,
                decision=MaintenanceDecision.ACCEPT_CONTINUE_FLY,
                rationale=(
                    "Damage exceeds the allowable limit but remains within the extended limit. "
                    "Residual strength analysis confirms continued-flight rationale."
                ),
            )
        return DamageDisposition(
            item_id=report.item_id,
            damage_size=report.damage_size,
            allowable_limit=report.allowable_limit,
            decision=MaintenanceDecision.FLAG,
            rationale=(
                "Damage exceeds the allowable limit and is within the extended limit, "
                "but no residual strength analysis is on record. "
                "Continued operation is not permitted until the analysis is completed."
            ),
        )

    # Damage exceeds the extended limit
    if report.can_be_repaired:
        return DamageDisposition(
            item_id=report.item_id,
            damage_size=report.damage_size,
            allowable_limit=report.allowable_limit,
            decision=MaintenanceDecision.REPAIR,
            rationale=(
                "Damage exceeds the extended allowable limit. "
                "Structural repair is required per an approved repair scheme."
            ),
        )
    return DamageDisposition(
        item_id=report.item_id,
        damage_size=report.damage_size,
        allowable_limit=report.allowable_limit,
        decision=MaintenanceDecision.REPLACE,
        rationale=(
            "Damage exceeds the extended allowable limit and repair is not feasible. "
            "Component replacement is required."
        ),
    )


def surveillance_compliance_check(
    items: List[InspectionItem],
    damage_reports: List[DamageReport],
) -> SurveillanceResult:
    """
    Full in-service surveillance compliance check.

    Builds inspection schedules for all items, evaluates all damage reports,
    and returns a SurveillanceResult. Compliant only when no disposition is
    FLAG, REPAIR, or REPLACE, and no invalid data was encountered.
    """
    findings: List[str] = []
    schedules: List[InspectionSchedule] = []
    dispositions: List[DamageDisposition] = []
    has_invalid = False

    known_ids: Set[str] = {item.item_id for item in items}

    for item in items:
        try:
            schedule = assign_inspection_interval(item)
            schedules.append(schedule)
            if schedule.reduced_interval:
                findings.append(
                    f"Item {item.item_id}: inspection interval reduced to "
                    f"{schedule.interval_hours:.1f} h (fatigue fraction "
                    f"{item.fatigue_fraction:.2f} exceeds {HIGH_FATIGUE_THRESHOLD})."
                )
        except ValueError as exc:
            findings.append(f"Item {item.item_id}: invalid data — {exc}")
            has_invalid = True

    _blocking = {MaintenanceDecision.FLAG, MaintenanceDecision.REPAIR, MaintenanceDecision.REPLACE}

    for report in damage_reports:
        if report.item_id not in known_ids:
            findings.append(
                f"Damage report for item {report.item_id}: "
                "no matching item in the surveillance inventory."
            )
            has_invalid = True
            continue
        try:
            disposition = evaluate_damage(report)
            dispositions.append(disposition)
            if disposition.decision in _blocking:
                findings.append(
                    f"Item {report.item_id}: {disposition.decision.value} — "
                    f"{disposition.rationale}"
                )
        except ValueError as exc:
            findings.append(f"Damage report {report.item_id}: invalid data — {exc}")
            has_invalid = True

    unresolved = [d for d in dispositions if d.decision in _blocking]
    compliant = not has_invalid and len(unresolved) == 0

    return SurveillanceResult(
        compliant=compliant,
        inspection_schedules=schedules,
        damage_dispositions=dispositions,
        findings=findings,
    )

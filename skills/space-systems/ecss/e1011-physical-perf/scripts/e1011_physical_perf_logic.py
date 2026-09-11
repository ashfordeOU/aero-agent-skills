"""
Physical performance and fatigue logic for crew workload assessment.
Anchor: ECSS-E-ST-10-11C §4.5.3.
Stdlib only; no third-party dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class WorkloadCategory(str, Enum):
    REST = "REST"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    VERY_HEAVY = "VERY_HEAVY"


# Metabolic rate upper boundaries (W) for each band below VERY_HEAVY.
# Derived from ISO 8996 categories adapted per ECSS-E-ST-10-11C §4.5.3.
# Interval convention: [lower, upper) — a value equal to the boundary
# belongs to the higher band.
_THRESHOLDS: List[tuple] = [
    (65,  WorkloadCategory.REST),
    (175, WorkloadCategory.LIGHT),
    (295, WorkloadCategory.MODERATE),
    (415, WorkloadCategory.HEAVY),
]

# Maximum continuous uninterrupted work duration (minutes) per band.
_CONTINUOUS_LIMIT_MIN = {
    WorkloadCategory.REST:       1440,
    WorkloadCategory.LIGHT:       480,
    WorkloadCategory.MODERATE:    120,
    WorkloadCategory.HEAVY:        45,
    WorkloadCategory.VERY_HEAVY:   20,
}

# Minimum recovery ratio: required_rest = ratio × work_duration (minutes).
_RECOVERY_RATIO = {
    WorkloadCategory.REST:        0.00,
    WorkloadCategory.LIGHT:       0.25,
    WorkloadCategory.MODERATE:    0.50,
    WorkloadCategory.HEAVY:       1.00,
    WorkloadCategory.VERY_HEAVY:  2.00,
}

# Daily accumulated work-time ceiling (minutes) per band.
_DAILY_LIMIT_MIN = {
    WorkloadCategory.REST:       1440,
    WorkloadCategory.LIGHT:       480,
    WorkloadCategory.MODERATE:    240,
    WorkloadCategory.HEAVY:       120,
    WorkloadCategory.VERY_HEAVY:   60,
}


def categorize_workload(metabolic_rate_w: float) -> WorkloadCategory:
    """Return the workload band for a given metabolic rate (W)."""
    if metabolic_rate_w < 0:
        raise ValueError(
            f"metabolic_rate_w must be non-negative, got {metabolic_rate_w}"
        )
    for threshold, band in _THRESHOLDS:
        if metabolic_rate_w < threshold:
            return band
    return WorkloadCategory.VERY_HEAVY


def continuous_duration_limit(category: WorkloadCategory) -> int:
    """Return the maximum continuous work duration (minutes) for a band."""
    return _CONTINUOUS_LIMIT_MIN[category]


def required_recovery(category: WorkloadCategory, work_duration_min: float) -> float:
    """
    Return the minimum rest time (minutes) required after a work bout.

    REST bouts require no subsequent rest. For all other bands the
    required rest equals the recovery ratio times the work duration.
    """
    if work_duration_min < 0:
        raise ValueError(
            f"work_duration_min must be non-negative, got {work_duration_min}"
        )
    return _RECOVERY_RATIO[category] * work_duration_min


@dataclass
class BoutCheckResult:
    category: WorkloadCategory
    metabolic_rate_w: float
    duration_min: float
    continuous_limit_min: int
    required_recovery_min: float
    violations: List[str] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        return len(self.violations) == 0


def check_work_bout(metabolic_rate_w: float, duration_min: float) -> BoutCheckResult:
    """
    Evaluate a single work bout against the continuous duration limit.

    Raises ValueError for non-positive duration or negative metabolic rate.
    Returns a BoutCheckResult; inspect .compliant and .violations for findings.
    """
    if metabolic_rate_w < 0:
        raise ValueError(
            f"metabolic_rate_w must be non-negative, got {metabolic_rate_w}"
        )
    if duration_min <= 0:
        raise ValueError(
            f"duration_min must be positive, got {duration_min}"
        )
    category = categorize_workload(metabolic_rate_w)
    limit = continuous_duration_limit(category)
    rec = required_recovery(category, duration_min)
    violations: List[str] = []
    if duration_min > limit:
        violations.append(
            f"Continuous duration {duration_min:.1f} min exceeds "
            f"{category.value} limit {limit} min"
        )
    return BoutCheckResult(
        category=category,
        metabolic_rate_w=metabolic_rate_w,
        duration_min=duration_min,
        continuous_limit_min=limit,
        required_recovery_min=rec,
        violations=violations,
    )


@dataclass
class SegmentResult:
    segment_type: str          # 'work' or 'rest'
    metabolic_rate_w: float
    duration_min: float
    category: WorkloadCategory
    violations: List[str] = field(default_factory=list)


@dataclass
class ScheduleResult:
    segments: List[SegmentResult] = field(default_factory=list)
    daily_totals: dict = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        seg_clean = all(len(s.violations) == 0 for s in self.segments)
        return len(self.violations) == 0 and seg_clean


def check_schedule(segments: list) -> ScheduleResult:
    """
    Validate a full crew work-rest schedule.

    Each element of `segments` is a dict with:
      type            – 'work' or 'rest'
      metabolic_rate_w – float, watts
      duration_min    – float, minutes (must be positive)

    Checks applied:
    1. Each work bout against its continuous duration limit.
    2. Recovery between consecutive work bouts (accumulated rest >=
       required_recovery of the preceding bout).
    3. Daily accumulated work time per band against the daily limit.

    Raises ValueError for empty input or malformed segment dicts.
    """
    if not segments:
        raise ValueError("segments list must not be empty")

    result = ScheduleResult()
    daily_totals = {c: 0.0 for c in WorkloadCategory}
    prev_work: SegmentResult = None
    accumulated_rest = 0.0

    for idx, seg in enumerate(segments):
        seg_type = seg.get("type")
        if seg_type not in ("work", "rest"):
            raise ValueError(
                f"Segment {idx}: type must be 'work' or 'rest', got {seg_type!r}"
            )
        rate = float(seg.get("metabolic_rate_w", 0.0))
        duration = seg.get("duration_min")
        if duration is None or float(duration) <= 0:
            raise ValueError(
                f"Segment {idx}: duration_min must be a positive number"
            )
        duration = float(duration)
        if rate < 0:
            raise ValueError(
                f"Segment {idx}: metabolic_rate_w must be non-negative"
            )

        category = categorize_workload(rate)
        seg_result = SegmentResult(
            segment_type=seg_type,
            metabolic_rate_w=rate,
            duration_min=duration,
            category=category,
        )

        if seg_type == "work":
            if prev_work is not None:
                needed = required_recovery(prev_work.category, prev_work.duration_min)
                if needed > 0 and accumulated_rest < needed:
                    seg_result.violations.append(
                        f"Insufficient recovery before segment {idx}: "
                        f"need {needed:.1f} min, had {accumulated_rest:.1f} min"
                    )
            bout = check_work_bout(rate, duration)
            seg_result.violations.extend(bout.violations)
            daily_totals[category] += duration
            prev_work = seg_result
            accumulated_rest = 0.0
        else:
            accumulated_rest += duration
            daily_totals[WorkloadCategory.REST] += duration

        result.segments.append(seg_result)

    for cat, total in daily_totals.items():
        limit = _DAILY_LIMIT_MIN[cat]
        if total > limit:
            result.violations.append(
                f"Daily {cat.value} total {total:.1f} min exceeds limit {limit} min"
            )

    result.daily_totals = {c.value: daily_totals[c] for c in WorkloadCategory}
    return result

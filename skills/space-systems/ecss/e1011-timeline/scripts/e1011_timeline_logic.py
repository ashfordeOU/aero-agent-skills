"""
ECSS-E-ST-10-11C §4.9.3 — Operations Timeline Logic
Deterministic, offline, stdlib-only.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# Workload level identifiers
WORKLOAD_LEVEL_LOW = "low"
WORKLOAD_LEVEL_MEDIUM = "medium"
WORKLOAD_LEVEL_HIGH = "high"

# Numeric value assigned to each workload level (higher = more demanding)
WORKLOAD_VALUES = {
    WORKLOAD_LEVEL_LOW: 1,
    WORKLOAD_LEVEL_MEDIUM: 2,
    WORKLOAD_LEVEL_HIGH: 3,
}

# Assessment constants (paraphrased from ECSS-E-ST-10-11C §4.9.3)
MAX_WORKLOAD_INDEX = 3.0        # max time-averaged workload index per 60-min window
MAX_CONCURRENT_TASKS = 3        # max simultaneous crew tasks (cognitive limit)
MIN_REST_DURATION_MINUTES = 480 # minimum rest gap between high-demand clusters (8 h)
HIGH_DEMAND_CLUSTER_THRESHOLD = 2.5  # workload index above which a window is high-demand


@dataclass
class TimelineEntry:
    task_id: str
    description: str
    start_minute: int       # minutes from mission phase epoch (non-negative)
    duration_minutes: int   # task duration in minutes (positive)
    workload_level: str     # "low", "medium", or "high"
    crew_count: int = 1     # crew members required (>= 1)

    def end_minute(self) -> int:
        return self.start_minute + self.duration_minutes


@dataclass
class ValidationResult:
    passed: bool
    findings: List[str] = field(default_factory=list)


def validate_entry(entry: TimelineEntry) -> ValidationResult:
    """Check a single TimelineEntry for structural correctness."""
    findings = []
    if entry.duration_minutes <= 0:
        findings.append(
            f"Task {entry.task_id}: duration_minutes must be positive, "
            f"got {entry.duration_minutes}"
        )
    if entry.start_minute < 0:
        findings.append(
            f"Task {entry.task_id}: start_minute must be non-negative, "
            f"got {entry.start_minute}"
        )
    if entry.workload_level not in WORKLOAD_VALUES:
        findings.append(
            f"Task {entry.task_id}: unknown workload_level '{entry.workload_level}'; "
            f"must be one of {sorted(WORKLOAD_VALUES.keys())}"
        )
    if entry.crew_count < 1:
        findings.append(
            f"Task {entry.task_id}: crew_count must be at least 1, "
            f"got {entry.crew_count}"
        )
    return ValidationResult(passed=len(findings) == 0, findings=findings)


def compute_workload_index(
    entries: List[TimelineEntry],
    window_start_minute: int,
    window_duration_minutes: int,
) -> float:
    """
    Compute the time-averaged workload index for a window.

    Index = sum(workload_value * overlap_minutes) / window_duration_minutes
    for all entries that overlap the window.  Returns a value in [0, 3*N]
    where N is the number of fully-concurrent tasks.  The unit is workload
    value averaged across the window duration.

    Raises ValueError if window_duration_minutes <= 0.
    """
    if window_duration_minutes <= 0:
        raise ValueError(
            f"window_duration_minutes must be positive, got {window_duration_minutes}"
        )
    window_end = window_start_minute + window_duration_minutes
    total = 0.0
    for entry in entries:
        overlap_start = max(entry.start_minute, window_start_minute)
        overlap_end = min(entry.end_minute(), window_end)
        overlap = max(0, overlap_end - overlap_start)
        if overlap > 0:
            total += WORKLOAD_VALUES[entry.workload_level] * overlap
    return total / window_duration_minutes


def check_workload_constraints(
    entries: List[TimelineEntry],
    window_minutes: int = 60,
) -> ValidationResult:
    """
    Slide a window of window_minutes across the full timeline and flag any
    window whose workload index exceeds MAX_WORKLOAD_INDEX.
    """
    if not entries:
        return ValidationResult(passed=True)
    timeline_end = max(e.end_minute() for e in entries)
    findings = []
    t = 0
    while t < timeline_end:
        win_dur = min(window_minutes, timeline_end - t)
        if win_dur <= 0:
            break
        idx = compute_workload_index(entries, t, win_dur)
        if idx > MAX_WORKLOAD_INDEX:
            findings.append(
                f"Workload index {idx:.2f} exceeds limit {MAX_WORKLOAD_INDEX} "
                f"in window [{t}-{t + win_dur}] min"
            )
        t += window_minutes
    return ValidationResult(passed=len(findings) == 0, findings=findings)


def check_concurrent_tasks(entries: List[TimelineEntry]) -> ValidationResult:
    """
    Event-sweep at every task start/end to count simultaneously active tasks.
    Ends are processed before starts at the same minute so a task replacing
    another at an exact boundary does not produce a spurious violation.
    Flag any instant where the active count exceeds MAX_CONCURRENT_TASKS.
    """
    if not entries:
        return ValidationResult(passed=True)

    # delta: -1 for end (sort before start at same minute), +1 for start
    events: List[Tuple[int, int, str]] = []
    for entry in entries:
        events.append((entry.start_minute, 1, entry.task_id))
        events.append((entry.end_minute(), -1, entry.task_id))
    events.sort(key=lambda x: (x[0], x[1]))  # ends (-1) sort before starts (+1)

    findings = []
    active = 0
    for minute, delta, task_id in events:
        if delta == 1:
            active += 1
            if active > MAX_CONCURRENT_TASKS:
                findings.append(
                    f"Concurrent task count {active} exceeds limit "
                    f"{MAX_CONCURRENT_TASKS} at minute {minute} "
                    f"(task '{task_id}' starting)"
                )
        else:
            active -= 1
    return ValidationResult(passed=len(findings) == 0, findings=findings)


def check_rest_periods(entries: List[TimelineEntry]) -> ValidationResult:
    """
    Identify high-demand 60-min windows (workload index > HIGH_DEMAND_CLUSTER_THRESHOLD),
    group consecutive windows into clusters, and flag any inter-cluster gap
    shorter than MIN_REST_DURATION_MINUTES.
    """
    if not entries:
        return ValidationResult(passed=True)

    timeline_end = max(e.end_minute() for e in entries)
    window_minutes = 60
    high_demand_windows: List[int] = []

    t = 0
    while t < timeline_end:
        win_dur = min(window_minutes, timeline_end - t)
        if win_dur <= 0:
            break
        idx = compute_workload_index(entries, t, win_dur)
        if idx > HIGH_DEMAND_CLUSTER_THRESHOLD:
            high_demand_windows.append(t)
        t += window_minutes

    if not high_demand_windows:
        return ValidationResult(passed=True)

    # Group consecutive high-demand windows into clusters
    clusters: List[Tuple[int, int]] = []
    c_start = high_demand_windows[0]
    c_end = c_start + window_minutes
    for w in high_demand_windows[1:]:
        if w <= c_end:
            c_end = w + window_minutes
        else:
            clusters.append((c_start, c_end))
            c_start = w
            c_end = w + window_minutes
    clusters.append((c_start, c_end))

    if len(clusters) < 2:
        return ValidationResult(passed=True)

    findings = []
    for i in range(len(clusters) - 1):
        gap = clusters[i + 1][0] - clusters[i][1]
        if gap < MIN_REST_DURATION_MINUTES:
            findings.append(
                f"Rest gap of {gap} min between high-demand clusters "
                f"[{clusters[i][0]}-{clusters[i][1]}] and "
                f"[{clusters[i + 1][0]}-{clusters[i + 1][1]}] min "
                f"is below minimum {MIN_REST_DURATION_MINUTES} min"
            )
    return ValidationResult(passed=len(findings) == 0, findings=findings)


def validate_timeline(entries: List[TimelineEntry]) -> ValidationResult:
    """
    Full timeline validation: structural checks, workload constraints,
    concurrent-task limit, and rest-period gaps.  Returns on the first
    structural error batch so downstream checks always receive valid entries.
    """
    # Phase 1: structural entry validation
    structural_findings: List[str] = []
    for entry in entries:
        result = validate_entry(entry)
        structural_findings.extend(result.findings)
    if structural_findings:
        return ValidationResult(passed=False, findings=structural_findings)

    # Phase 2: workload, concurrency, rest
    all_findings: List[str] = []
    for check in (check_workload_constraints, check_concurrent_tasks, check_rest_periods):
        r = check(entries)
        all_findings.extend(r.findings)

    return ValidationResult(passed=len(all_findings) == 0, findings=all_findings)

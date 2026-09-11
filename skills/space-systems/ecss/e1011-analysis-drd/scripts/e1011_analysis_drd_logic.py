"""
HFE Analysis and Simulation Report DRD validation logic.
Ref: ECSS-E-ST-10-11C Annex B — HFE Analysis and Simulation Report DRD.

All logic is deterministic and offline (stdlib only).
"""

REQUIRED_SECTIONS = [
    "scope",
    "applicable_documents",
    "task_analysis",
    "human_performance_requirements",
    "workload_analysis",
    "error_analysis",
    "simulation_activities",
    "verification_evidence",
    "findings_and_recommendations",
]

REQUIRED_TASK_FIELDS = [
    "mission_phase",
    "task_description",
    "crew_size",
    "allocated_time",
]

REQUIRED_SIMULATION_FIELDS = [
    "simulation_id",
    "objective",
    "participants",
    "scenario",
    "findings",
]

VALID_MISSION_PHASES = {
    "launch",
    "ascent",
    "on_orbit",
    "rendezvous",
    "docking",
    "egress",
    "eva",
    "undocking",
    "re_entry",
    "landing",
    "post_landing",
}

VALID_WORKLOAD_LEVELS = {"low", "medium", "high", "critical"}

HIGH_WORKLOAD_THRESHOLD = 0.30


class HFEAnalysisDRDError(ValueError):
    """Raised when input data is structurally invalid."""


def _normalise_phase(raw: str) -> str:
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


def validate_report_structure(report: dict) -> list[str]:
    """Return a list of missing top-level section keys."""
    if not isinstance(report, dict):
        raise HFEAnalysisDRDError("report must be a dict")
    return [s for s in REQUIRED_SECTIONS if s not in report]


def validate_task_entry(entry: dict, index: int) -> list[str]:
    """Return a list of deficiency strings for one task-analysis entry."""
    if not isinstance(entry, dict):
        raise HFEAnalysisDRDError(f"task entry {index} must be a dict")
    issues = []
    for field in REQUIRED_TASK_FIELDS:
        if field not in entry:
            issues.append(f"missing_{field}")
    if "mission_phase" in entry:
        phase = _normalise_phase(str(entry["mission_phase"]))
        if phase not in VALID_MISSION_PHASES:
            issues.append(f"invalid_mission_phase:{entry['mission_phase']!r}")
    if "allocated_time" in entry:
        t = entry["allocated_time"]
        if not isinstance(t, (int, float)) or t <= 0:
            issues.append("allocated_time_must_be_positive")
    if "crew_size" in entry:
        c = entry["crew_size"]
        if not isinstance(c, int) or c < 1:
            issues.append("crew_size_must_be_positive_integer")
    return issues


def validate_simulation_entry(sim: dict, index: int) -> list[str]:
    """Return a list of deficiency strings for one simulation activity entry."""
    if not isinstance(sim, dict):
        raise HFEAnalysisDRDError(f"simulation entry {index} must be a dict")
    issues = []
    for field in REQUIRED_SIMULATION_FIELDS:
        if field not in sim:
            issues.append(f"missing_{field}")
    if "participants" in sim:
        p = sim["participants"]
        if not isinstance(p, int) or p < 1:
            issues.append("participants_must_be_positive_integer")
    if "findings" in sim and not sim["findings"]:
        issues.append("findings_must_not_be_empty")
    return issues


def assess_workload(task_entries: list) -> dict:
    """
    Assess workload distribution across task entries.

    Returns a dict with:
      counts         — tally per recognised workload level
      invalid_levels — list of unrecognised level strings encountered
      high_or_critical_fraction — fraction of entries at high/critical
      flagged        — True when fraction exceeds HIGH_WORKLOAD_THRESHOLD
    """
    counts = {level: 0 for level in VALID_WORKLOAD_LEVELS}
    invalid = []
    for entry in task_entries:
        raw = str(entry.get("workload_level", "")).strip().lower()
        if not raw:
            continue
        if raw in VALID_WORKLOAD_LEVELS:
            counts[raw] += 1
        else:
            invalid.append(raw)

    total = sum(counts.values())
    elevated = counts["high"] + counts["critical"]
    fraction = elevated / total if total > 0 else 0.0
    return {
        "counts": counts,
        "invalid_levels": invalid,
        "high_or_critical_fraction": fraction,
        "flagged": fraction > HIGH_WORKLOAD_THRESHOLD,
    }


def validate_error_analysis(items: list) -> list[str]:
    """Return a list of deficiency strings across all error-analysis items."""
    if not isinstance(items, list):
        raise HFEAnalysisDRDError("error_analysis must be a list")
    issues = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"item_{i}_must_be_dict")
            continue
        if "error_type" not in item:
            issues.append(f"item_{i}_missing_error_type")
        if "mitigation" not in item or not item["mitigation"]:
            issues.append(f"item_{i}_missing_or_empty_mitigation")
        if "probability" not in item:
            issues.append(f"item_{i}_missing_probability")
        else:
            p = item["probability"]
            if not isinstance(p, (int, float)) or not (0.0 <= p <= 1.0):
                issues.append(f"item_{i}_invalid_probability:{p!r}")
    return issues


def validate_report(report: dict) -> dict:
    """
    Run a full DRD compliance check on an HFE analysis and simulation report.

    Returns a dict with keys:
      structure_gaps       — missing section names
      task_analysis_issues — list of {entry, issues} dicts
      simulation_issues    — list of {sim, issues} dicts
      workload_assessment  — output of assess_workload
      error_analysis_issues — flat list of deficiency strings
      compliant            — True only when all finding lists are clear
    """
    if not isinstance(report, dict):
        raise HFEAnalysisDRDError("report must be a dict")

    result = {
        "structure_gaps": [],
        "task_analysis_issues": [],
        "simulation_issues": [],
        "workload_assessment": {},
        "error_analysis_issues": [],
        "compliant": False,
    }

    result["structure_gaps"] = validate_report_structure(report)
    if result["structure_gaps"]:
        return result

    for i, entry in enumerate(report.get("task_analysis", [])):
        issues = validate_task_entry(entry, i)
        if issues:
            result["task_analysis_issues"].append({"entry": i, "issues": issues})

    for i, sim in enumerate(report.get("simulation_activities", [])):
        issues = validate_simulation_entry(sim, i)
        if issues:
            result["simulation_issues"].append({"sim": i, "issues": issues})

    result["workload_assessment"] = assess_workload(
        report.get("task_analysis", [])
    )

    result["error_analysis_issues"] = validate_error_analysis(
        report.get("error_analysis", [])
    )

    wl = result["workload_assessment"]
    all_clear = (
        not result["task_analysis_issues"]
        and not result["simulation_issues"]
        and not result["error_analysis_issues"]
        and not wl.get("flagged", False)
        and not wl.get("invalid_levels", [])
    )
    result["compliant"] = all_clear
    return result

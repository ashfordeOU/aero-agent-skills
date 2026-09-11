"""
ECSS-E-ST-10-11C §4.3.1–4.3.2 — HFE Role in Project Logic
Deterministic, offline, stdlib-only.

Implements checkable engineering logic for:
  - HFE task-category completeness (§4.3.1)
  - Lifecycle phase coverage of HFE tasks
  - HFE interface discipline completeness (§4.3.2)
  - Individual HFE interface record validation
  - Aggregate HFE role completeness scoring
"""

# Required HFE task categories per ECSS-E-ST-10-11C §4.3.1
REQUIRED_HFE_TASK_CATEGORIES = frozenset([
    "requirements_definition",
    "task_analysis",
    "design_support",
    "hmi_definition",
    "verification_and_validation",
    "design_review_participation",
])

# Required interface disciplines per ECSS-E-ST-10-11C §4.3.2
REQUIRED_INTERFACE_DISCIPLINES = frozenset([
    "systems_engineering",
    "safety",
    "operations",
    "training",
    "software_engineering",
])

# Lifecycle phases that must each carry at least one HFE task
REQUIRED_LIFECYCLE_PHASES = frozenset([
    "phase_0",
    "phase_a",
    "phase_b",
    "phase_c",
    "phase_d",
    "phase_e",
])

# Full set of recognised ECSS lifecycle phase identifiers
VALID_LIFECYCLE_PHASES = frozenset([
    "phase_0", "phase_a", "phase_b", "phase_c", "phase_d", "phase_e", "phase_f",
])


def validate_hfe_role_definition(role_def):
    """
    Check that an HFE role definition covers all required task categories.

    Args:
        role_def (dict): {"tasks": [str, ...]}
            Each string is a task category identifier (see REQUIRED_HFE_TASK_CATEGORIES).

    Returns:
        dict: {
            "valid": bool,
            "missing_categories": [str],   # sorted
            "findings": [str],
        }

    Raises:
        TypeError: if role_def is not a dict or "tasks" is not a list.
    """
    if not isinstance(role_def, dict):
        raise TypeError("role_def must be a dict")
    tasks = role_def.get("tasks", [])
    if not isinstance(tasks, list):
        raise TypeError("role_def['tasks'] must be a list")

    present = frozenset(tasks)
    missing = sorted(REQUIRED_HFE_TASK_CATEGORIES - present)
    findings = [f"Missing HFE task category: {c}" for c in missing]

    return {
        "valid": len(missing) == 0,
        "missing_categories": missing,
        "findings": findings,
    }


def validate_hfe_interface(interface):
    """
    Validate a single HFE interface record.

    Args:
        interface (dict): {
            "discipline": str,   # e.g. "systems_engineering"
            "contact": str,      # name or role of the responsible contact
            "outputs": [str],    # list of exchanged deliverables or results
        }

    Returns:
        dict: {
            "valid": bool,
            "findings": [str],
        }

    Raises:
        TypeError: if interface is not a dict.
    """
    if not isinstance(interface, dict):
        raise TypeError("interface must be a dict")

    findings = []

    discipline = interface.get("discipline", "")
    if not discipline:
        findings.append("Interface record is missing the 'discipline' field")

    contact = interface.get("contact", "")
    if not contact:
        findings.append(
            f"Interface record for '{discipline or '<unknown>'}' "
            "is missing the 'contact' field"
        )

    outputs = interface.get("outputs")
    if outputs is None:
        findings.append(
            f"Interface record for '{discipline or '<unknown>'}' "
            "is missing the 'outputs' field"
        )
    elif not isinstance(outputs, list):
        findings.append(
            f"Interface record for '{discipline or '<unknown>'}': "
            "'outputs' must be a list"
        )
    elif len(outputs) == 0:
        findings.append(
            f"Interface '{discipline or '<unknown>'}' has no outputs defined; "
            "at least one exchanged output is required"
        )

    return {
        "valid": len(findings) == 0,
        "findings": findings,
    }


def check_hfe_task_phase_coverage(tasks):
    """
    Check that HFE tasks are assigned to all required lifecycle phases.

    Args:
        tasks (list): [{"phase": str, "category": str}, ...]
            Each dict must contain at least a "phase" key with a valid
            ECSS lifecycle phase identifier.

    Returns:
        dict: {
            "covered_phases": [str],    # sorted, phases that have at least one task
            "uncovered_phases": [str],  # sorted, required phases with no task
            "invalid_entries": [int],   # indices of malformed task entries
            "findings": [str],
        }

    Raises:
        TypeError: if tasks is not a list.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks must be a list")

    covered = set()
    findings = []
    invalid_entries = []

    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            findings.append(f"Task entry at index {i} is not a dict")
            invalid_entries.append(i)
            continue
        phase = task.get("phase", "")
        if not phase:
            findings.append(f"Task entry at index {i} is missing the 'phase' field")
            invalid_entries.append(i)
            continue
        if phase not in VALID_LIFECYCLE_PHASES:
            findings.append(
                f"Task entry at index {i} has unrecognised phase '{phase}'; "
                f"valid values: {sorted(VALID_LIFECYCLE_PHASES)}"
            )
            invalid_entries.append(i)
            continue
        covered.add(phase)

    uncovered = sorted(REQUIRED_LIFECYCLE_PHASES - covered)
    for phase in uncovered:
        findings.append(f"No HFE task is assigned to {phase}")

    return {
        "covered_phases": sorted(covered),
        "uncovered_phases": uncovered,
        "invalid_entries": invalid_entries,
        "findings": findings,
    }


def identify_missing_interfaces(defined_interfaces):
    """
    Return mandatory HFE interface disciplines not present in the project plan.

    Args:
        defined_interfaces (list[str]): discipline identifiers already defined
            in the project's interface matrix.

    Returns:
        list[str]: sorted list of missing mandatory discipline identifiers.

    Raises:
        TypeError: if defined_interfaces is not a list.
    """
    if not isinstance(defined_interfaces, list):
        raise TypeError("defined_interfaces must be a list")

    present = frozenset(defined_interfaces)
    return sorted(REQUIRED_INTERFACE_DISCIPLINES - present)


def score_hfe_role_completeness(role_def, interfaces, tasks):
    """
    Aggregate completeness score for the HFE role definition.

    Checks:
      - Task category coverage (REQUIRED_HFE_TASK_CATEGORIES)
      - Lifecycle phase coverage (REQUIRED_LIFECYCLE_PHASES)
      - Interface discipline coverage (REQUIRED_INTERFACE_DISCIPLINES)

    Args:
        role_def (dict):  {"tasks": [str, ...]}
        interfaces (list[str]): list of defined discipline name strings
        tasks (list[dict]): list of {"phase": str, "category": str} dicts

    Returns:
        dict: {
            "score": float,      # 0.0–1.0 fraction of checks passed
            "findings": [str],
        }
    """
    all_findings = []

    role_result = validate_hfe_role_definition(role_def)
    all_findings.extend(role_result["findings"])

    missing_ifaces = identify_missing_interfaces(interfaces)
    for discipline in missing_ifaces:
        all_findings.append(f"Missing HFE interface with discipline: {discipline}")

    phase_result = check_hfe_task_phase_coverage(tasks)
    all_findings.extend(phase_result["findings"])

    total_checks = (
        len(REQUIRED_HFE_TASK_CATEGORIES)
        + len(REQUIRED_INTERFACE_DISCIPLINES)
        + len(REQUIRED_LIFECYCLE_PHASES)
    )
    failed = (
        len(role_result["missing_categories"])
        + len(missing_ifaces)
        + len(phase_result["uncovered_phases"])
    )
    score = max(0.0, (total_checks - failed) / total_checks)

    return {
        "score": round(score, 4),
        "findings": all_findings,
    }

"""
Composite structure verification logic — ECSS-E-ST-32C clause 4.6.4.

Implements deterministic, offline checks for:
  - allowable statistical basis (A-basis / B-basis)
  - knock-down factor completeness (temperature, moisture, scatter)
  - composite failure mode analysis coverage
  - test-article environment conditioning
  - NDT plan coverage and detectability assessment
  - building-block test pyramid mandatory levels

All functions accept plain dicts/lists and return a result dict with keys:
  pass  : bool
  findings : list of {id?, issue} dicts
"""

VALID_ALLOWABLE_BASIS = frozenset(["A_basis", "B_basis"])

REQUIRED_KNOCK_DOWN_FACTORS = frozenset(["temperature", "moisture", "scatter"])

REQUIRED_FAILURE_MODES = frozenset([
    "fiber_failure",
    "matrix_cracking",
    "delamination",
    "interlaminar_shear",
])

VALID_ENV_CONDITIONS = frozenset([
    "hot_wet",
    "room_temperature_dry",
    "cold_dry",
    "hot_dry",
])

VALID_NDT_METHODS = frozenset([
    "ultrasonic_c_scan",
    "ultrasonic_through_transmission",
    "radiography",
    "thermography",
    "shearography",
])

VALID_STRUCTURE_CATEGORIES = frozenset(["primary", "secondary", "tertiary"])
NDT_REQUIRED_CATEGORIES = frozenset(["primary", "secondary"])

VALID_TEST_LEVELS = frozenset(["coupon", "element", "sub_component", "component"])
MANDATORY_TEST_LEVELS = frozenset(["coupon", "component"])


def _require_list(value, name):
    if not isinstance(value, list):
        raise TypeError(f"'{name}' must be a list, got {type(value).__name__}")


def check_allowable_basis(allowables):
    """
    ECSS-E-ST-32C §4.6.4: every composite design allowable must carry a
    stated statistical basis. Primary (single-load-path) structure requires
    A_basis; redundant structure requires at minimum B_basis.

    Returns {pass: bool, findings: list}.
    """
    _require_list(allowables, "allowables")
    findings = []
    for entry in allowables:
        aid = entry.get("id", "<unnamed>")
        basis = entry.get("basis")
        structure_category = entry.get("structure_category")

        if basis is None:
            findings.append({"id": aid, "issue": "allowable basis not specified"})
            continue

        if basis not in VALID_ALLOWABLE_BASIS:
            findings.append({
                "id": aid,
                "issue": (
                    f"invalid allowable basis '{basis}'; "
                    f"must be one of {sorted(VALID_ALLOWABLE_BASIS)}"
                ),
            })
            continue

        if structure_category == "primary" and basis != "A_basis":
            findings.append({
                "id": aid,
                "issue": (
                    f"single-load-path (primary) structure requires A_basis; "
                    f"got '{basis}'"
                ),
            })

    return {"pass": len(findings) == 0, "findings": findings}


def check_knock_down_factors(allowables):
    """
    ECSS-E-ST-32C §4.6.4: each allowable must have temperature, moisture,
    and scatter knock-down factors applied and traceable.

    Returns {pass: bool, findings: list}.
    """
    _require_list(allowables, "allowables")
    findings = []
    for entry in allowables:
        aid = entry.get("id", "<unnamed>")
        applied = frozenset(entry.get("knock_down_factors") or [])
        missing = REQUIRED_KNOCK_DOWN_FACTORS - applied
        if missing:
            findings.append({
                "id": aid,
                "issue": f"missing knock-down factors: {sorted(missing)}",
            })

    return {"pass": len(findings) == 0, "findings": findings}


def check_failure_mode_coverage(failure_modes_analyzed):
    """
    ECSS-E-ST-32C §4.6.4: analysis must address fiber_failure, matrix_cracking,
    delamination, and interlaminar_shear. Unrecognized mode labels are flagged.

    Returns {pass: bool, findings: list}.
    """
    _require_list(failure_modes_analyzed, "failure_modes_analyzed")
    covered = frozenset(failure_modes_analyzed)
    missing = REQUIRED_FAILURE_MODES - covered
    unknown = covered - REQUIRED_FAILURE_MODES

    findings = []
    if missing:
        findings.append({"issue": f"uncovered failure modes: {sorted(missing)}"})
    if unknown:
        findings.append({"issue": f"unrecognized failure mode labels: {sorted(unknown)}"})

    return {"pass": len(findings) == 0, "findings": findings}


def check_environment_conditioning(test_articles):
    """
    ECSS-E-ST-32C §4.6.4: test articles must be conditioned to the worst-case
    environmental state before structural testing. The recorded conditioning_state
    must match the design_env_condition for each article.

    Returns {pass: bool, findings: list}.
    """
    _require_list(test_articles, "test_articles")
    findings = []
    for article in test_articles:
        tid = article.get("id", "<unnamed>")
        cond = article.get("conditioning_state")
        design_env = article.get("design_env_condition")

        if cond is None:
            findings.append({"id": tid, "issue": "conditioning_state not specified"})
            continue

        if cond not in VALID_ENV_CONDITIONS:
            findings.append({
                "id": tid,
                "issue": (
                    f"conditioning_state '{cond}' not in valid set "
                    f"{sorted(VALID_ENV_CONDITIONS)}"
                ),
            })
            continue

        if design_env is None:
            findings.append({"id": tid, "issue": "design_env_condition not specified"})
            continue

        if design_env not in VALID_ENV_CONDITIONS:
            findings.append({
                "id": tid,
                "issue": f"design_env_condition '{design_env}' not in valid set",
            })
            continue

        if cond != design_env:
            findings.append({
                "id": tid,
                "issue": (
                    f"conditioning mismatch: article conditioned to '{cond}' "
                    f"but design environment is '{design_env}'"
                ),
            })

    return {"pass": len(findings) == 0, "findings": findings}


def check_ndt_coverage(ndt_plan, structure_parts):
    """
    ECSS-E-ST-32C §4.6.4: NDT must cover all primary and secondary composite
    parts. Each covered part must have a valid method and a stated
    critical_defect_size_mm to confirm detectability was assessed.

    Returns {pass: bool, findings: list}.
    """
    _require_list(ndt_plan, "ndt_plan")
    _require_list(structure_parts, "structure_parts")

    covered = {entry["part_id"]: entry for entry in ndt_plan if "part_id" in entry}
    findings = []

    for part in structure_parts:
        pid = part.get("id", "<unnamed>")
        category = part.get("category")

        if category not in VALID_STRUCTURE_CATEGORIES:
            findings.append({
                "id": pid,
                "issue": f"unknown structure category '{category}'",
            })
            continue

        if category not in NDT_REQUIRED_CATEGORIES:
            continue

        ndt_entry = covered.get(pid)
        if ndt_entry is None:
            findings.append({
                "id": pid,
                "issue": f"{category} composite part has no NDT plan entry",
            })
            continue

        method = ndt_entry.get("method")
        if method not in VALID_NDT_METHODS:
            findings.append({
                "id": pid,
                "issue": (
                    f"NDT method '{method}' not in approved set "
                    f"{sorted(VALID_NDT_METHODS)}"
                ),
            })

        if ndt_entry.get("critical_defect_size_mm") is None:
            findings.append({
                "id": pid,
                "issue": "critical_defect_size_mm not recorded; detectability not assessed",
            })

    return {"pass": len(findings) == 0, "findings": findings}


def check_test_pyramid(test_articles):
    """
    ECSS-E-ST-32C §4.6.4: building-block verification requires at minimum
    coupon-level and component-level test evidence. Element and sub_component
    levels are recommended; coupon and component are mandatory.

    Returns {pass: bool, findings: list, levels_present: list}.
    """
    _require_list(test_articles, "test_articles")
    levels_present = frozenset(
        a.get("test_level")
        for a in test_articles
        if a.get("test_level") in VALID_TEST_LEVELS
    )
    missing = MANDATORY_TEST_LEVELS - levels_present

    findings = []
    if missing:
        findings.append({
            "issue": f"mandatory test pyramid levels absent: {sorted(missing)}"
        })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "levels_present": sorted(levels_present),
    }


def run_composite_verification(spec):
    """
    Top-level entry point. Runs all six checks and aggregates results.

    spec keys (all optional — missing keys produce empty-list inputs):
      allowables             : list of allowable dicts
      failure_modes_analyzed : list of failure mode label strings
      test_articles          : list of test article dicts
      ndt_plan               : list of NDT plan entry dicts
      structure_parts        : list of composite part dicts

    Returns {pass: bool, checks: {check_name: result_dict}}.
    """
    if not isinstance(spec, dict):
        raise TypeError(f"spec must be a dict, got {type(spec).__name__}")

    allowables = spec.get("allowables", [])
    failure_modes = spec.get("failure_modes_analyzed", [])
    test_articles = spec.get("test_articles", [])
    ndt_plan = spec.get("ndt_plan", [])
    structure_parts = spec.get("structure_parts", [])

    checks = {
        "allowable_basis": check_allowable_basis(allowables),
        "knock_down_factors": check_knock_down_factors(allowables),
        "failure_mode_coverage": check_failure_mode_coverage(failure_modes),
        "environment_conditioning": check_environment_conditioning(test_articles),
        "ndt_coverage": check_ndt_coverage(ndt_plan, structure_parts),
        "test_pyramid": check_test_pyramid(test_articles),
    }
    overall = all(r["pass"] for r in checks.values())
    return {"pass": overall, "checks": checks}

"""
Structural analysis report and LBB report verification logic.
ECSS-E-ST-32C clause 5.2 (structural analysis report content) and
clause 5.3.5 (Leak-Before-Break report).
Stdlib only; deterministic; offline.
"""

STRUCTURAL_REPORT_REQUIRED_SECTIONS = [
    "objectives",
    "applicable_documents",
    "model_description",
    "load_cases",
    "material_properties",
    "analysis_methodology",
    "results",
    "margin_of_safety",
    "conclusions",
]

LBB_REPORT_REQUIRED_SECTIONS = [
    "fracture_toughness",
    "crack_growth_data",
    "critical_crack_size",
    "inspection_intervals",
    "pressure_cycle_history",
    "leak_detection_rationale",
]

MARGIN_OF_SAFETY_LIMIT = 0.0


def compute_margin_of_safety(allowable: float, applied: float) -> float:
    """
    Compute margin of safety: MS = allowable / applied - 1.
    Raises ValueError when either argument is non-positive.
    """
    if applied <= 0.0:
        raise ValueError(
            f"Applied value must be positive; received {applied}"
        )
    if allowable <= 0.0:
        raise ValueError(
            f"Allowable value must be positive; received {allowable}"
        )
    return allowable / applied - 1.0


def check_report_sections(provided: list, required: list) -> dict:
    """
    Compare a list of provided section keys against a required list.

    Returns a dict with keys:
      present  -- required sections that are present
      missing  -- required sections that are absent
      compliant -- True when missing is empty
    """
    if not isinstance(provided, list):
        raise TypeError(
            f"provided must be a list; received {type(provided).__name__}"
        )
    normalised = {s.lower().strip() for s in provided}
    missing = [r for r in required if r not in normalised]
    present = [r for r in required if r in normalised]
    return {
        "present": present,
        "missing": missing,
        "compliant": len(missing) == 0,
    }


def check_structural_report(sections: list) -> dict:
    """Check structural analysis report section completeness (clause 5.2)."""
    return check_report_sections(sections, STRUCTURAL_REPORT_REQUIRED_SECTIONS)


def check_lbb_report(sections: list) -> dict:
    """Check LBB report section completeness (clause 5.3.5)."""
    return check_report_sections(sections, LBB_REPORT_REQUIRED_SECTIONS)


def evaluate_load_cases(load_cases: list) -> dict:
    """
    Evaluate margin of safety for each load case.

    Each element of load_cases must be a dict with:
      name      -- str label (optional, defaults to "unnamed")
      allowable -- positive float
      applied   -- positive float

    Returns:
      load_cases  -- list of per-case findings
      all_compliant -- True when every case has MS >= 0.0
    """
    findings = []
    for lc in load_cases:
        name = lc.get("name", "unnamed")
        try:
            allowable = float(lc["allowable"])
            applied = float(lc["applied"])
            ms = compute_margin_of_safety(allowable, applied)
            findings.append(
                {
                    "name": name,
                    "margin_of_safety": round(ms, 6),
                    "compliant": ms >= MARGIN_OF_SAFETY_LIMIT,
                    "error": None,
                }
            )
        except (KeyError, ValueError, TypeError) as exc:
            findings.append(
                {
                    "name": name,
                    "margin_of_safety": None,
                    "compliant": False,
                    "error": str(exc),
                }
            )
    return {
        "load_cases": findings,
        "all_compliant": all(f["compliant"] for f in findings),
    }


def evaluate_full_deliverable(report: dict) -> dict:
    """
    Evaluate a complete analysis report deliverable.

    report dict keys:
      report_type -- "structural" or "lbb"
      sections    -- list[str] of section keys present in the document
      load_cases  -- list[dict] (required for structural; ignored for lbb)

    Returns aggregated compliance findings.
    Raises ValueError for an unrecognised report_type.
    """
    report_type = report.get("report_type", "").lower().strip()
    sections = report.get("sections", [])

    if report_type == "structural":
        section_result = check_structural_report(sections)
        lc_result = evaluate_load_cases(report.get("load_cases", []))
        compliant = section_result["compliant"] and lc_result["all_compliant"]
        return {
            "report_type": "structural",
            "section_check": section_result,
            "load_case_check": lc_result,
            "compliant": compliant,
        }

    if report_type == "lbb":
        section_result = check_lbb_report(sections)
        return {
            "report_type": "lbb",
            "section_check": section_result,
            "compliant": section_result["compliant"],
        }

    raise ValueError(
        f"Unknown report_type '{report_type}'; expected 'structural' or 'lbb'"
    )

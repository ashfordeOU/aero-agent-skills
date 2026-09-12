"""
Composite overwrap inspection logic — ECSS-E-ST-32C clause 5.7.

Implements deterministic, offline assessment of composite overwrap integrity:
NDT method selection, defect categorization by size, coverage check, and
final inspection verdict.  No third-party dependencies.
"""

# ---------------------------------------------------------------------------
# Defect size limits (mm).  Each type has two thresholds:
#   <= acceptable_mm  -> "acceptable"
#   <= monitor_mm     -> "monitor"
#   >  monitor_mm     -> "rejectable"
# ---------------------------------------------------------------------------
DEFECT_LIMITS = {
    "void":           {"acceptable_mm": 3.0,  "monitor_mm": 10.0},
    "delamination":   {"acceptable_mm": 5.0,  "monitor_mm": 20.0},
    "surface_scratch":{"acceptable_mm": 1.0,  "monitor_mm": 5.0},
    "fiber_breakage": {"acceptable_mm": 0.0,  "monitor_mm": 2.0},
    "inclusion":      {"acceptable_mm": 2.0,  "monitor_mm": 8.0},
}

KNOWN_DEFECT_TYPES = frozenset(DEFECT_LIMITS.keys())

# ---------------------------------------------------------------------------
# Overwrap material types recognised by this leaf.
# ---------------------------------------------------------------------------
KNOWN_OVERWRAP_TYPES = frozenset({"cfrp", "gfrp", "aramid"})

# ---------------------------------------------------------------------------
# NDT method matrix: (defect_type, overwrap_type) -> [recommended methods].
# Rationale: UT detects volumetric anomalies in all fibre composites;
# radiography is preferred for density-contrast anomalies (inclusions, voids
# in GFRP); thermography surfaces inter-ply disbonds efficiently in CFRP/
# aramid; visual inspection covers surface-only indications.
# ---------------------------------------------------------------------------
_NDT_MATRIX = {
    ("void",            "cfrp"):  ["ultrasonic", "thermography"],
    ("void",            "gfrp"):  ["ultrasonic", "radiography"],
    ("void",            "aramid"):["ultrasonic", "thermography"],
    ("delamination",    "cfrp"):  ["ultrasonic", "thermography"],
    ("delamination",    "gfrp"):  ["ultrasonic", "radiography"],
    ("delamination",    "aramid"):["ultrasonic", "thermography"],
    ("surface_scratch", "cfrp"):  ["visual"],
    ("surface_scratch", "gfrp"):  ["visual"],
    ("surface_scratch", "aramid"):["visual"],
    ("fiber_breakage",  "cfrp"):  ["visual", "ultrasonic"],
    ("fiber_breakage",  "gfrp"):  ["visual", "ultrasonic"],
    ("fiber_breakage",  "aramid"):["visual", "ultrasonic"],
    ("inclusion",       "cfrp"):  ["radiography", "ultrasonic"],
    ("inclusion",       "gfrp"):  ["radiography"],
    ("inclusion",       "aramid"):["radiography", "ultrasonic"],
}

# Minimum inspection coverage required to yield a pass/fail verdict (%).
COVERAGE_THRESHOLD_PCT = 95.0

# Severity ordering used when aggregating multiple defect categories.
_SEVERITY = {"acceptable": 0, "monitor": 1, "rejectable": 2}


class InspectionError(ValueError):
    """Raised for invalid inputs to any inspection function."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def categorize_defect(defect_type: str, size_mm: float) -> str:
    """
    Categorize a single detected defect by type and maximum linear size.

    Returns one of: "acceptable", "monitor", "rejectable".
    Raises InspectionError for an unknown defect type or a negative size.
    """
    if defect_type not in KNOWN_DEFECT_TYPES:
        raise InspectionError(
            f"Unrecognized defect type {defect_type!r}. "
            f"Recognized types: {sorted(KNOWN_DEFECT_TYPES)}"
        )
    if size_mm < 0:
        raise InspectionError(
            f"Defect size must be non-negative; received {size_mm}"
        )

    limits = DEFECT_LIMITS[defect_type]
    if size_mm <= limits["acceptable_mm"]:
        return "acceptable"
    if size_mm <= limits["monitor_mm"]:
        return "monitor"
    return "rejectable"


def select_ndt_method(defect_type: str, overwrap_type: str) -> list:
    """
    Return the list of recommended NDT methods for a defect type and overwrap
    material combination.

    Raises InspectionError for unrecognized defect type or overwrap type.
    """
    if defect_type not in KNOWN_DEFECT_TYPES:
        raise InspectionError(
            f"Unrecognized defect type {defect_type!r}. "
            f"Recognized types: {sorted(KNOWN_DEFECT_TYPES)}"
        )
    if overwrap_type not in KNOWN_OVERWRAP_TYPES:
        raise InspectionError(
            f"Unrecognized overwrap type {overwrap_type!r}. "
            f"Recognized types: {sorted(KNOWN_OVERWRAP_TYPES)}"
        )
    return list(_NDT_MATRIX.get((defect_type, overwrap_type), ["visual"]))


def assess_coverage(inspected_area_cm2: float, total_area_cm2: float) -> dict:
    """
    Compute inspection coverage and determine whether the threshold is met.

    Returns:
        {
            "coverage_pct":      float,
            "coverage_adequate": bool,
        }

    Raises InspectionError for non-positive total area, negative inspected
    area, or inspected area exceeding total area.
    """
    if total_area_cm2 <= 0:
        raise InspectionError(
            f"Total area must be positive; received {total_area_cm2}"
        )
    if inspected_area_cm2 < 0:
        raise InspectionError(
            f"Inspected area must be non-negative; received {inspected_area_cm2}"
        )
    if inspected_area_cm2 > total_area_cm2:
        raise InspectionError(
            f"Inspected area ({inspected_area_cm2}) exceeds total area ({total_area_cm2})"
        )

    coverage_pct = (inspected_area_cm2 / total_area_cm2) * 100.0
    return {
        "coverage_pct": coverage_pct,
        "coverage_adequate": coverage_pct >= COVERAGE_THRESHOLD_PCT,
    }


def evaluate_defect_list(defects: list) -> dict:
    """
    Evaluate a list of defect records and return a per-defect breakdown plus
    the aggregate status.

    Each entry in ``defects`` must be a dict with "type" (str) and "size_mm"
    (float).

    Returns:
        {
            "defects": [{"type": str, "size_mm": float, "category": str}, ...],
            "status":  "accept" | "conditional" | "reject",
        }

    Raises InspectionError if any entry is malformed or contains an
    unrecognized defect type or negative size.
    """
    results = []
    for idx, entry in enumerate(defects):
        if not isinstance(entry, dict) or "type" not in entry or "size_mm" not in entry:
            raise InspectionError(
                f"Defect entry at index {idx} must be a dict with 'type' and 'size_mm' keys"
            )
        category = categorize_defect(entry["type"], entry["size_mm"])
        results.append({
            "type":     entry["type"],
            "size_mm":  entry["size_mm"],
            "category": category,
        })

    worst = max(
        (_SEVERITY[r["category"]] for r in results),
        default=0,
    )
    if worst == _SEVERITY["rejectable"]:
        status = "reject"
    elif worst == _SEVERITY["monitor"]:
        status = "conditional"
    else:
        status = "accept"

    return {"defects": results, "status": status}


def determine_inspection_result(
    defects: list,
    inspected_area_cm2: float,
    total_area_cm2: float,
) -> dict:
    """
    Combine defect evaluation and coverage assessment into a final verdict.

    Returns:
        {
            "coverage":        {coverage_pct, coverage_adequate},
            "defect_summary":  {defects, status},
            "overall_result":  "pass" | "conditional-pass" | "fail" | "incomplete",
        }

    "incomplete" takes precedence over any defect-driven verdict: an
    inspection with insufficient coverage has no valid outcome yet.
    """
    coverage = assess_coverage(inspected_area_cm2, total_area_cm2)
    defect_summary = evaluate_defect_list(defects)

    if not coverage["coverage_adequate"]:
        overall = "incomplete"
    elif defect_summary["status"] == "reject":
        overall = "fail"
    elif defect_summary["status"] == "conditional":
        overall = "conditional-pass"
    else:
        overall = "pass"

    return {
        "coverage":       coverage,
        "defect_summary": defect_summary,
        "overall_result": overall,
    }

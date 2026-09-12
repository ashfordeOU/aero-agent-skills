"""
ECSS-E-ST-32C Annex B — Design Loads Document (DRD-DL) logic.
Paraphrased procedure; ECSS-E-ST-32C cited as anchor only (not reproduced).
stdlib only — no external dependencies.
"""

# Recognized load case types per ECSS-E-ST-32C Annex B taxonomy
LOAD_CASE_TYPES = frozenset({
    "static",
    "quasi-static",
    "dynamic-sine",
    "dynamic-random",
    "dynamic-shock",
    "thermal",
    "acoustic",
    "pressure",
    "inertia",
    "combined",
})

# Default safety factors for metallic structures (ECSS-E-ST-32C Annex B)
DEFAULT_PARTIAL_SAFETY_FACTOR = 1.0   # DLL = LL × 1.0 (nominal, no scatter)
DEFAULT_YIELD_FACTOR = 1.0            # DYL = DLL × 1.0 (metallic yield criterion)
DEFAULT_ULTIMATE_FACTOR = 1.25        # DUL = DLL × 1.25 (metallic ultimate criterion)

# Accepted safety-factor bounds
MIN_SAFETY_FACTOR = 1.0
MAX_SAFETY_FACTOR = 4.0


def categorize_load_type(load_type: str) -> str:
    """
    Return the normalized ECSS load-case type for a given input string.
    Raises ValueError if the type is not in the ECSS-E-ST-32C taxonomy.
    """
    if not isinstance(load_type, str):
        raise ValueError(
            f"Load type must be a string, got {type(load_type).__name__!r}."
        )
    normalized = load_type.strip().lower()
    if normalized not in LOAD_CASE_TYPES:
        raise ValueError(
            f"Load type {load_type!r} is not in the ECSS-E-ST-32C recognized taxonomy. "
            f"Accepted types: {sorted(LOAD_CASE_TYPES)}."
        )
    return normalized


def compute_dll(limit_load: float,
                partial_safety_factor: float = DEFAULT_PARTIAL_SAFETY_FACTOR) -> float:
    """
    Compute the Design Limit Load.
    DLL = LL × partial_safety_factor  (ECSS-E-ST-32C Annex B).
    Raises ValueError for a negative LL or an out-of-range factor.
    """
    if limit_load < 0:
        raise ValueError(
            f"Limit load must be non-negative, got {limit_load}."
        )
    if not (MIN_SAFETY_FACTOR <= partial_safety_factor <= MAX_SAFETY_FACTOR):
        raise ValueError(
            f"Partial safety factor {partial_safety_factor} is outside the accepted "
            f"range [{MIN_SAFETY_FACTOR}, {MAX_SAFETY_FACTOR}]."
        )
    return limit_load * partial_safety_factor


def compute_dyl(dll: float,
                yield_factor: float = DEFAULT_YIELD_FACTOR) -> float:
    """
    Compute the Design Yield Load.
    DYL = DLL × yield_factor  (ECSS-E-ST-32C Annex B).
    Raises ValueError for a negative DLL or an out-of-range factor.
    """
    if dll < 0:
        raise ValueError(
            f"DLL must be non-negative, got {dll}."
        )
    if not (MIN_SAFETY_FACTOR <= yield_factor <= MAX_SAFETY_FACTOR):
        raise ValueError(
            f"Yield factor {yield_factor} is outside the accepted "
            f"range [{MIN_SAFETY_FACTOR}, {MAX_SAFETY_FACTOR}]."
        )
    return dll * yield_factor


def compute_dul(dll: float,
                ultimate_factor: float = DEFAULT_ULTIMATE_FACTOR) -> float:
    """
    Compute the Design Ultimate Load.
    DUL = DLL × ultimate_factor  (ECSS-E-ST-32C Annex B).
    Raises ValueError for a negative DLL or an out-of-range factor.
    """
    if dll < 0:
        raise ValueError(
            f"DLL must be non-negative, got {dll}."
        )
    if not (MIN_SAFETY_FACTOR <= ultimate_factor <= MAX_SAFETY_FACTOR):
        raise ValueError(
            f"Ultimate factor {ultimate_factor} is outside the accepted "
            f"range [{MIN_SAFETY_FACTOR}, {MAX_SAFETY_FACTOR}]."
        )
    return dll * ultimate_factor


def process_load_case(load_case: dict) -> dict:
    """
    Process a single load case and return computed loads with any findings.

    Required keys:
        id           (str)   — unique load case identifier
        type         (str)   — load type from ECSS taxonomy
        limit_load   (float) — Limit Load value (must be >= 0)

    Optional keys:
        partial_safety_factor (float) — default DEFAULT_PARTIAL_SAFETY_FACTOR
        yield_factor          (float) — default DEFAULT_YIELD_FACTOR
        ultimate_factor       (float) — default DEFAULT_ULTIMATE_FACTOR

    Returns:
        {
            "id":           str,
            "type":         str | None,
            "limit_load":   float | None,
            "dll":          float | None,
            "dyl":          float | None,
            "dul":          float | None,
            "findings":     list[str],
        }
    """
    findings = []
    result = {
        "id": load_case.get("id", ""),
        "type": None,
        "limit_load": None,
        "dll": None,
        "dyl": None,
        "dul": None,
        "findings": findings,
    }

    lc_id = load_case.get("id", "")
    if not lc_id:
        findings.append("Load case is missing an 'id' field.")

    raw_type = load_case.get("type", "")
    try:
        result["type"] = categorize_load_type(raw_type)
    except (ValueError, AttributeError) as exc:
        findings.append(str(exc))

    limit_load = load_case.get("limit_load")
    if limit_load is None:
        findings.append(
            f"Load case {lc_id!r}: 'limit_load' is missing — "
            "load case cannot be completed without a Limit Load value."
        )
        return result

    try:
        limit_load = float(limit_load)
        result["limit_load"] = limit_load
    except (TypeError, ValueError):
        findings.append(
            f"Load case {lc_id!r}: 'limit_load' must be a numeric value."
        )
        return result

    psf = load_case.get("partial_safety_factor", DEFAULT_PARTIAL_SAFETY_FACTOR)
    yf  = load_case.get("yield_factor",          DEFAULT_YIELD_FACTOR)
    uf  = load_case.get("ultimate_factor",        DEFAULT_ULTIMATE_FACTOR)

    try:
        dll = compute_dll(limit_load, psf)
        result["dll"] = dll
    except ValueError as exc:
        findings.append(str(exc))
        return result

    try:
        result["dyl"] = compute_dyl(dll, yf)
    except ValueError as exc:
        findings.append(str(exc))

    try:
        result["dul"] = compute_dul(dll, uf)
    except ValueError as exc:
        findings.append(str(exc))

    return result


def process_design_loads_document(load_cases: list) -> dict:
    """
    Process a full list of load cases forming a DRD-DL document.

    Returns:
        {
            "load_case_results": list[dict],  — one entry per input case
            "findings":          list[str],   — all per-case + document-level findings
            "compliant":         bool,        — True only when findings is empty
        }
    """
    if not load_cases:
        return {
            "load_case_results": [],
            "findings": [
                "Design loads document contains no load cases; "
                "at least one load case is required."
            ],
            "compliant": False,
        }

    results = [process_load_case(lc) for lc in load_cases]

    all_findings = []
    for r in results:
        all_findings.extend(r["findings"])

    seen_ids: set = set()
    for r in results:
        lc_id = r["id"]
        if lc_id:
            if lc_id in seen_ids:
                all_findings.append(
                    f"Duplicate load case ID {lc_id!r}: each load case must have "
                    "a unique identifier in the DRD-DL."
                )
            seen_ids.add(lc_id)

    return {
        "load_case_results": results,
        "findings": all_findings,
        "compliant": len(all_findings) == 0,
    }

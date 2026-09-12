"""
Structural engineering load case logic — ECSS-E-ST-32C clause 5.2.

Implements deterministic checks for:
  - Load case categorization (clause 5.2a)
  - Design situation categorization
  - Combined loads via absolute-sum or SRSS (clause 5.2d)
  - Scatter factor application (clause 5.2h)
  - Design load computation
  - Sustained loading / creep identification
  - Creep-rupture margin of safety (clause 5.2, category S)
  - Full load case record validation

No third-party dependencies; stdlib only.
"""

import math
from typing import Dict, List, Optional

VALID_LOAD_CASE_TYPES = {
    "limit",
    "yield",
    "ultimate",
    "proof",
    "fatigue",
    "creep-rupture",
}

VALID_DESIGN_SITUATIONS = {
    "launch",
    "transfer-orbit",
    "on-orbit",
    "re-entry",
    "landing",
    "ground-handling",
    "transportation",
    "storage",
}

VALID_LOAD_SOURCES = {
    "mechanical",
    "thermal",
    "pressure",
    "acoustic",
    "shock",
    "vibration",
}

# Safety factors per load case type (ECSS-E-ST-32C clause 5.2, paraphrased)
SAFETY_FACTORS: Dict[str, float] = {
    "yield": 1.1,
    "ultimate": 1.25,
    "proof": 1.0,
    "fatigue": 4.0,
    "creep-rupture": 1.25,
}

# Sustained duration threshold (hours) that triggers mandatory creep assessment
CREEP_THRESHOLD_HOURS: float = 1.0

# Materials requiring creep and creep-rupture assessment under sustained load
CREEP_SENSITIVE_MATERIALS = {
    "aluminium-alloy",
    "titanium-alloy",
    "composite-cfrp",
    "composite-gfrp",
    "polymer",
    "adhesive",
}


def categorize_load_case(load_case_type: str) -> str:
    """
    Confirm a load case type is in the recognized set from ECSS-E-ST-32C
    clause 5.2a.  Returns the normalized string; raises ValueError otherwise.
    """
    normalized = load_case_type.strip().lower()
    if normalized not in VALID_LOAD_CASE_TYPES:
        raise ValueError(
            f"Unrecognized load case type '{load_case_type}'. "
            f"Expected one of: {sorted(VALID_LOAD_CASE_TYPES)}"
        )
    return normalized


def categorize_design_situation(situation: str) -> str:
    """
    Confirm a design situation is in the recognized set.
    Returns the normalized string; raises ValueError otherwise.
    """
    normalized = situation.strip().lower()
    if normalized not in VALID_DESIGN_SITUATIONS:
        raise ValueError(
            f"Unrecognized design situation '{situation}'. "
            f"Expected one of: {sorted(VALID_DESIGN_SITUATIONS)}"
        )
    return normalized


def combine_loads(loads: Dict[str, float], method: str = "absolute") -> float:
    """
    Combine a mapping of load-source name to value into a scalar resultant.

    method='absolute' — arithmetic sum of absolute values (correlated or
      unknown-phase loads; conservative).
    method='srss' — square root of sum of squares (statistically independent,
      random loads).

    Returns the combined load value (>= 0).
    Raises ValueError for an empty mapping or an unrecognized method.
    """
    if not loads:
        raise ValueError("Load mapping must contain at least one entry.")

    if method not in ("absolute", "srss"):
        raise ValueError(
            f"Unrecognized combination method '{method}'. Use 'absolute' or 'srss'."
        )

    values = [float(v) for v in loads.values()]

    if method == "absolute":
        return sum(abs(v) for v in values)

    return math.sqrt(sum(v ** 2 for v in values))


def apply_scatter_factor(load_value: float, scatter_factor: float) -> float:
    """
    Apply a scatter factor to a limit load per ECSS-E-ST-32C clause 5.2h.

    Scatter factors account for statistical variability in the load
    environment.  scatter_factor must be >= 1.0.
    Returns the factored load.
    """
    if scatter_factor < 1.0:
        raise ValueError(
            f"Scatter factor must be >= 1.0; got {scatter_factor}."
        )
    if load_value < 0:
        raise ValueError(
            f"Load value must be non-negative; got {load_value}."
        )
    return load_value * scatter_factor


def compute_design_load(
    limit_load: float,
    load_case_type: str,
    scatter_factor: float = 1.0,
    safety_factor: Optional[float] = None,
) -> float:
    """
    Compute the design load from a limit load.

    Procedure (ECSS-E-ST-32C clause 5.2, paraphrased):
      1. Apply scatter factor to the limit load.
      2. Multiply the scattered limit load by the safety factor for the
         load case type.

    For the 'limit' type the safety factor is 1.0 (the limit load IS the
    design load after scattering).  For all other types the safety factor
    defaults to the ECSS-derived value in SAFETY_FACTORS unless overridden.

    Returns the design load value (float).
    """
    lc_type = categorize_load_case(load_case_type)

    if lc_type == "limit":
        sf = 1.0
    elif safety_factor is not None:
        sf = float(safety_factor)
    else:
        sf = SAFETY_FACTORS.get(lc_type, 1.0)

    scattered = apply_scatter_factor(limit_load, scatter_factor)
    return scattered * sf


def check_sustained_loading(duration_hours: float, material: str) -> dict:
    """
    Determine whether a sustained load requires creep assessment.

    Returns a dict with keys:
      'creep_required': bool
      'creep_rupture_required': bool
      'reason': str
    """
    if duration_hours < 0:
        raise ValueError(
            f"Duration must be non-negative; got {duration_hours}."
        )

    mat = material.strip().lower()
    is_creep_sensitive = mat in CREEP_SENSITIVE_MATERIALS
    duration_exceeds_threshold = duration_hours >= CREEP_THRESHOLD_HOURS
    creep_required = is_creep_sensitive and duration_exceeds_threshold

    if not is_creep_sensitive:
        reason = (
            f"Material '{material}' is not in the creep-sensitive set; "
            "no creep assessment required."
        )
    elif not duration_exceeds_threshold:
        reason = (
            f"Sustained duration {duration_hours:.2f} h is below the "
            f"{CREEP_THRESHOLD_HOURS:.2f} h threshold; "
            "no creep assessment required."
        )
    else:
        reason = (
            f"Sustained duration {duration_hours:.2f} h on creep-sensitive "
            f"material '{material}' triggers creep deformation and "
            "creep-rupture assessment."
        )

    return {
        "creep_required": creep_required,
        "creep_rupture_required": creep_required,
        "reason": reason,
    }


def check_creep_rupture(
    applied_stress: float,
    allowable_creep_rupture_stress: float,
    duration_hours: float,
) -> dict:
    """
    Assess creep-rupture for a sustained load case (ECSS-E-ST-32C clause 5.2,
    category S).

    Margin of safety: MS = allowable / applied - 1
    MS >= 0.0 passes; MS < 0.0 fails.

    Returns a dict with keys:
      'ms': float — margin of safety
      'passes': bool
      'finding': str — human-readable verdict
    """
    if applied_stress <= 0:
        raise ValueError(
            f"Applied stress must be > 0; got {applied_stress}."
        )
    if allowable_creep_rupture_stress <= 0:
        raise ValueError(
            f"Allowable creep-rupture stress must be > 0; "
            f"got {allowable_creep_rupture_stress}."
        )
    if duration_hours < 0:
        raise ValueError(
            f"Duration must be non-negative; got {duration_hours}."
        )

    ms = allowable_creep_rupture_stress / applied_stress - 1.0
    passes = ms >= 0.0
    verdict = "PASS" if passes else "FAIL (exceedance)"
    finding = (
        f"Creep-rupture MS = {ms:.4f} for {duration_hours:.1f} h "
        f"duration — {verdict}"
    )

    return {"ms": ms, "passes": passes, "finding": finding}


def validate_load_case(load_case: dict) -> List[str]:
    """
    Validate a complete load case record and return a list of findings.
    An empty list means the record is compliant.

    Recognized keys in load_case:
      'type': str           — load case type (required)
      'situation': str      — design situation (required)
      'limit_load': float   — limit load value, >= 0 (required)
      'scatter_factor': float — must be >= 1.0 (optional, default 1.0)
      'duration_hours': float — sustained duration >= 0 (optional)
      'material': str       — material identifier (optional)
    """
    findings: List[str] = []

    # Validate type
    try:
        categorize_load_case(load_case.get("type", ""))
    except ValueError as exc:
        findings.append(str(exc))

    # Validate design situation
    try:
        categorize_design_situation(load_case.get("situation", ""))
    except ValueError as exc:
        findings.append(str(exc))

    # Validate limit_load
    ll = load_case.get("limit_load")
    if ll is None:
        findings.append("'limit_load' is required.")
    elif not isinstance(ll, (int, float)):
        findings.append("'limit_load' must be a number.")
    elif float(ll) < 0:
        findings.append(f"'limit_load' must be non-negative; got {ll}.")

    # Validate scatter_factor
    sf = load_case.get("scatter_factor", 1.0)
    if float(sf) < 1.0:
        findings.append(
            f"'scatter_factor' must be >= 1.0; got {sf}."
        )

    # Validate duration_hours if provided
    dur = load_case.get("duration_hours")
    if dur is not None and float(dur) < 0:
        findings.append(
            f"'duration_hours' must be non-negative; got {dur}."
        )

    return findings

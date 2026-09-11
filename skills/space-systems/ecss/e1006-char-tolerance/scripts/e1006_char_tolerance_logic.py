"""
Tolerance-completeness logic for ECSS-E-ST-10C §8.2.10.

Each quantitative requirement must carry:
  - a nominal value (float)
  - a plus-tolerance (float, >= 0)
  - a minus-tolerance (float, >= 0)

Qualitative requirements are skipped (no tolerance required).
"""

from typing import Any, Dict, List, Optional, Tuple


class Requirement:
    """Single system requirement with optional tolerance record."""

    def __init__(
        self,
        req_id: str,
        is_quantitative: bool,
        nominal: Optional[float] = None,
        plus_tol: Optional[float] = None,
        minus_tol: Optional[float] = None,
    ) -> None:
        if not req_id or not isinstance(req_id, str):
            raise ValueError("req_id must be a non-empty string")
        if is_quantitative and nominal is None:
            raise ValueError(
                f"{req_id}: quantitative requirement must supply a nominal value"
            )
        self.req_id = req_id
        self.is_quantitative = is_quantitative
        self.nominal = nominal
        self.plus_tol = plus_tol
        self.minus_tol = minus_tol


def check_tolerance_stated(req: Requirement) -> Tuple[bool, str]:
    """
    Return (passes, reason) for one requirement.

    Passes when:
      - the requirement is qualitative (no tolerance needed), or
      - the requirement is quantitative and both plus_tol and minus_tol
        are set with non-negative magnitudes.
    """
    if not isinstance(req, Requirement):
        raise TypeError(f"Expected Requirement, got {type(req).__name__}")

    if not req.is_quantitative:
        return True, "qualitative — no tolerance required"

    if req.nominal is None:
        return False, "missing nominal value"

    missing: List[str] = []
    if req.plus_tol is None:
        missing.append("plus-tolerance")
    if req.minus_tol is None:
        missing.append("minus-tolerance")
    if missing:
        return False, "missing: " + ", ".join(missing)

    if req.plus_tol < 0:
        return False, f"plus-tolerance is negative ({req.plus_tol})"
    if req.minus_tol < 0:
        return False, f"minus-tolerance is negative ({req.minus_tol})"

    return True, "tolerance complete"


def audit_requirements(reqs: List[Requirement]) -> Dict[str, Any]:
    """
    Audit a list of requirements for tolerance completeness.

    Returns:
      total     — total requirement count
      passing   — count of requirements that pass
      failing   — count of requirements that fail
      compliant — True only when failing == 0
      findings  — list of {"id": str, "reason": str} for failing requirements
    """
    if not isinstance(reqs, list):
        raise TypeError("reqs must be a list of Requirement objects")

    findings: List[Dict[str, str]] = []
    passing_count = 0

    for req in reqs:
        ok, reason = check_tolerance_stated(req)
        if ok:
            passing_count += 1
        else:
            findings.append({"id": req.req_id, "reason": reason})

    total = len(reqs)
    failing_count = len(findings)

    return {
        "total": total,
        "passing": passing_count,
        "failing": failing_count,
        "compliant": failing_count == 0,
        "findings": findings,
    }


def tolerance_bounds(
    nominal: float, plus_tol: float, minus_tol: float
) -> Tuple[float, float]:
    """
    Compute (lower_bound, upper_bound) from a nominal value and asymmetric tolerances.

    Raises ValueError when either tolerance magnitude is negative.
    """
    if plus_tol < 0 or minus_tol < 0:
        raise ValueError(
            f"Tolerance magnitudes must be non-negative (got +{plus_tol}, -{minus_tol})"
        )
    return nominal - minus_tol, nominal + plus_tol


def requirement_from_bounds(
    req_id: str, lower: float, upper: float
) -> Requirement:
    """
    Build a Requirement from explicit lower and upper bounds.

    Nominal is the midpoint; tolerances are derived symmetrically as half the range.
    Raises ValueError when lower > upper.
    """
    if lower > upper:
        raise ValueError(
            f"lower ({lower}) must be <= upper ({upper})"
        )
    nominal = (lower + upper) / 2.0
    half_range = (upper - lower) / 2.0
    return Requirement(
        req_id=req_id,
        is_quantitative=True,
        nominal=nominal,
        plus_tol=half_range,
        minus_tol=half_range,
    )

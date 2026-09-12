"""
Interface verification logic per ECSS E-ST-32C clause 4.6.3.22.

Deterministic, offline, stdlib-only. No external dependencies.
"""

INTERFACE_TYPES = {"mechanical", "electrical", "thermal", "fluid", "optical"}
VERIFICATION_METHODS = {"inspection", "analysis", "test"}

# Interfaces whose functional nature requires a physical test
_TEST_REQUIRED_TYPES = {"electrical", "optical"}


def categorize_interface(interface_type: str) -> str:
    """
    Return the validated category for an interface type string.

    Raises ValueError for unrecognized types — no silent default assignment.
    """
    if not isinstance(interface_type, str):
        raise TypeError(f"interface_type must be str, got {type(interface_type).__name__}")
    normalized = interface_type.strip().lower()
    if normalized not in INTERFACE_TYPES:
        raise ValueError(
            f"Unrecognized interface type {interface_type!r}. "
            f"Must be one of: {sorted(INTERFACE_TYPES)}"
        )
    return normalized


def select_verification_method(interface_type: str, has_test_facility: bool = False) -> str:
    """
    Select the appropriate verification method for a given interface category.

    - Electrical and optical interfaces require 'test' regardless of facility.
    - Any other category with a dedicated test facility available uses 'test'.
    - Otherwise the baseline method is 'inspection'.
    """
    category = categorize_interface(interface_type)
    if category in _TEST_REQUIRED_TYPES or has_test_facility:
        return "test"
    return "inspection"


def check_dimensional_fit(
    nominal_mm: float,
    tolerance_mm: float,
    actual_mm: float,
) -> dict:
    """
    Check whether actual_mm falls within [nominal_mm - tolerance_mm,
    nominal_mm + tolerance_mm].

    Returns a dict with keys:
      within_tolerance (bool)
      deviation_mm (float)   — signed: positive means oversized
      lower_bound_mm (float)
      upper_bound_mm (float)

    Raises ValueError if tolerance_mm is negative or zero (unset tolerance
    is a traceability error, not a passing condition).
    """
    if not isinstance(tolerance_mm, (int, float)):
        raise TypeError("tolerance_mm must be numeric")
    if tolerance_mm <= 0.0:
        raise ValueError(
            f"tolerance_mm must be positive (got {tolerance_mm}); "
            "an unset or zero tolerance is a traceability finding"
        )
    lower = nominal_mm - tolerance_mm
    upper = nominal_mm + tolerance_mm
    deviation = actual_mm - nominal_mm
    within = lower <= actual_mm <= upper
    return {
        "within_tolerance": within,
        "deviation_mm": round(deviation, 6),
        "lower_bound_mm": round(lower, 6),
        "upper_bound_mm": round(upper, 6),
    }


def validate_icd_reference(icd_reference: str) -> bool:
    """
    Return True when icd_reference is a non-empty, non-whitespace string.
    An empty or blank reference means the ICD traceability link is missing.
    """
    if not isinstance(icd_reference, str):
        raise TypeError(f"icd_reference must be str, got {type(icd_reference).__name__}")
    return bool(icd_reference.strip())


def verify_interface(interface: dict) -> dict:
    """
    Verify a single interface record.

    Required keys in interface:
      interface_id      (str)   — unique identifier
      interface_type    (str)   — one of INTERFACE_TYPES
      nominal_mm        (float) — ICD nominal dimension
      tolerance_mm      (float) — ICD ±tolerance (must be positive)
      actual_mm         (float) — measured dimension
      icd_reference     (str)   — ICD document identifier
      verification_method (str) — one of VERIFICATION_METHODS

    Returns:
      interface_id  (str)
      compliant     (bool)   — True only when all checks pass
      findings      (list)   — list of finding strings; empty means compliant
      fit_check     (dict)   — result from check_dimensional_fit
    """
    required_fields = {
        "interface_id", "interface_type", "nominal_mm",
        "tolerance_mm", "actual_mm", "icd_reference", "verification_method",
    }
    missing = required_fields - set(interface.keys())
    if missing:
        raise ValueError(f"Interface record missing required fields: {sorted(missing)}")

    findings = []

    # Validate category — raises ValueError for unknown types
    categorize_interface(interface["interface_type"])

    # Validate verification method
    vmethod = interface["verification_method"]
    if not isinstance(vmethod, str) or vmethod.strip().lower() not in VERIFICATION_METHODS:
        raise ValueError(
            f"Unrecognized verification_method {vmethod!r}. "
            f"Must be one of: {sorted(VERIFICATION_METHODS)}"
        )

    # ICD reference check
    if not validate_icd_reference(interface["icd_reference"]):
        findings.append("missing_icd_reference: no traceable ICD document identifier")

    # Dimensional fit check
    fit = check_dimensional_fit(
        float(interface["nominal_mm"]),
        float(interface["tolerance_mm"]),
        float(interface["actual_mm"]),
    )
    if not fit["within_tolerance"]:
        findings.append(
            f"dimension_out_of_tolerance: deviation={fit['deviation_mm']:.4f}mm "
            f"(bounds [{fit['lower_bound_mm']:.4f}, {fit['upper_bound_mm']:.4f}]mm)"
        )

    return {
        "interface_id": interface["interface_id"],
        "compliant": len(findings) == 0,
        "findings": findings,
        "fit_check": fit,
    }


def assess_interface_set(interfaces: list) -> dict:
    """
    Assess a list of interface records and return a set-level summary.

    Raises ValueError when the list is empty (an empty set cannot be verified).

    Returns:
      total              (int)
      compliant_count    (int)
      non_compliant_count (int)
      all_compliant      (bool)
      results            (list of per-interface verify_interface dicts)
    """
    if not isinstance(interfaces, list):
        raise TypeError("interfaces must be a list")
    if len(interfaces) == 0:
        raise ValueError("Interface list is empty; nothing to verify")

    results = [verify_interface(iface) for iface in interfaces]

    non_compliant = [r for r in results if not r["compliant"]]

    return {
        "total": len(results),
        "compliant_count": len(results) - len(non_compliant),
        "non_compliant_count": len(non_compliant),
        "all_compliant": len(non_compliant) == 0,
        "results": results,
    }

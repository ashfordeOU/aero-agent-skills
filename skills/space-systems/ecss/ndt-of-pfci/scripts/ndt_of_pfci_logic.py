"""
NDT of PFCI — deterministic engineering logic for ECSS-E-ST-32C fracture control.

Implements:
  - NDT method adequacy check (minimum detectable crack vs assumed initial crack size)
  - Inspection traceability record verification
  - Detected-defect disposition (Q-ST-70-15 interface)
  - Full PFCI assessment combining all three checks

All logic is offline and deterministic. No external dependencies.
"""

from typing import Dict, List, Optional, Any

# Each NDT method entry: minimum detectable crack size (mm), applicable defect
# locations, and compatible material families. Values are representative
# engineering bounds used for procedural adequacy gating, not test-specific data.
NDT_METHOD_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "FPI": {
        "min_detectable_mm": 0.50,
        "applicable_locations": ["surface", "near_surface"],
        "compatible_materials": ["metallic", "polymer"],
    },
    "MPI": {
        "min_detectable_mm": 0.50,
        "applicable_locations": ["surface", "near_surface"],
        "compatible_materials": ["ferromagnetic"],
    },
    "EC": {
        "min_detectable_mm": 0.25,
        "applicable_locations": ["surface", "near_surface"],
        "compatible_materials": ["conductive"],
    },
    "UT": {
        "min_detectable_mm": 1.00,
        "applicable_locations": ["volumetric"],
        "compatible_materials": ["metallic", "composite"],
    },
    "RT": {
        "min_detectable_mm": 1.00,
        "applicable_locations": ["volumetric"],
        "compatible_materials": ["metallic", "polymer"],
    },
    "VT": {
        "min_detectable_mm": 2.00,
        "applicable_locations": ["surface"],
        "compatible_materials": ["metallic", "composite", "polymer"],
    },
}

TRACEABILITY_REQUIRED_FIELDS: List[str] = [
    "item_id",
    "lot_id",
    "inspection_date",
    "ndt_method",
    "procedure_ref",
    "operator_id",
    "operator_qualification",
    "result",
]

VALID_QUALIFICATION_LEVELS = {"L1", "L2", "L3"}
VALID_RESULTS = {"no_defect_detected", "defect_detected", "inconclusive"}


def check_ndt_adequacy(
    ndt_method: str,
    material: str,
    location: str,
    assumed_crack_mm: float,
) -> Dict[str, Any]:
    """
    Determine whether an NDT method is adequate for a PFCI.

    Adequacy requires:
      1. The method is recognised.
      2. The material is compatible with the method.
      3. The defect location is covered by the method.
      4. The method's minimum detectable crack size <= assumed_crack_mm.

    Returns a dict with keys:
      adequate (bool), reason (str), min_detectable_mm (float | None)
    """
    if assumed_crack_mm <= 0.0:
        raise ValueError(
            f"assumed_crack_mm must be a positive number, got {assumed_crack_mm!r}"
        )

    method_key = ndt_method.upper()
    if method_key not in NDT_METHOD_CAPABILITIES:
        raise ValueError(
            f"Unknown NDT method '{ndt_method}'. "
            f"Recognised methods: {sorted(NDT_METHOD_CAPABILITIES)}"
        )

    cap = NDT_METHOD_CAPABILITIES[method_key]

    if material not in cap["compatible_materials"]:
        return {
            "adequate": False,
            "reason": (
                f"Method '{method_key}' is not compatible with material '{material}'. "
                f"Compatible materials: {cap['compatible_materials']}"
            ),
            "min_detectable_mm": cap["min_detectable_mm"],
        }

    if location not in cap["applicable_locations"]:
        return {
            "adequate": False,
            "reason": (
                f"Method '{method_key}' does not cover defect location '{location}'. "
                f"Applicable locations: {cap['applicable_locations']}"
            ),
            "min_detectable_mm": cap["min_detectable_mm"],
        }

    if cap["min_detectable_mm"] > assumed_crack_mm:
        return {
            "adequate": False,
            "reason": (
                f"Method '{method_key}' minimum detectable crack "
                f"({cap['min_detectable_mm']} mm) exceeds assumed initial crack size "
                f"({assumed_crack_mm} mm). Select a more sensitive NDT method."
            ),
            "min_detectable_mm": cap["min_detectable_mm"],
        }

    return {
        "adequate": True,
        "reason": (
            f"Method '{method_key}' minimum detectable crack "
            f"({cap['min_detectable_mm']} mm) is at or below assumed initial crack size "
            f"({assumed_crack_mm} mm). Adequate."
        ),
        "min_detectable_mm": cap["min_detectable_mm"],
    }


def verify_traceability_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify that a PFCI inspection record carries all mandatory traceability fields
    and that enumerated fields hold permitted values.

    Returns a dict with keys:
      complete (bool), missing_fields (list[str]), invalid_fields (list[str])
    """
    missing = [
        f
        for f in TRACEABILITY_REQUIRED_FIELDS
        if f not in record or record[f] is None or record[f] == ""
    ]

    invalid: List[str] = []

    qual = record.get("operator_qualification")
    if qual is not None and qual != "" and qual not in VALID_QUALIFICATION_LEVELS:
        invalid.append(
            f"operator_qualification '{qual}' not in permitted set {sorted(VALID_QUALIFICATION_LEVELS)}"
        )

    result_val = record.get("result")
    if result_val is not None and result_val != "" and result_val not in VALID_RESULTS:
        invalid.append(
            f"result '{result_val}' not in permitted set {sorted(VALID_RESULTS)}"
        )

    return {
        "complete": len(missing) == 0 and len(invalid) == 0,
        "missing_fields": missing,
        "invalid_fields": invalid,
    }


def handle_detected_defect(
    defect_size_mm: float,
    critical_crack_size_mm: float,
) -> Dict[str, Any]:
    """
    Determine defect disposition per the Q-ST-70-15 interface.

    Below critical crack size  → rework_and_reinspect
    At or above critical size  → reject_and_quarantine

    Returns a dict with keys:
      disposition (str), rationale (str), defect_size_mm (float), critical_crack_size_mm (float)
    """
    if defect_size_mm <= 0.0:
        raise ValueError(
            f"defect_size_mm must be a positive number, got {defect_size_mm!r}"
        )
    if critical_crack_size_mm <= 0.0:
        raise ValueError(
            f"critical_crack_size_mm must be a positive number, got {critical_crack_size_mm!r}"
        )

    if defect_size_mm < critical_crack_size_mm:
        return {
            "disposition": "rework_and_reinspect",
            "rationale": (
                f"Detected defect ({defect_size_mm} mm) is below critical crack size "
                f"({critical_crack_size_mm} mm). Quarantine item, perform rework, and "
                "re-inspect before return to service."
            ),
            "defect_size_mm": defect_size_mm,
            "critical_crack_size_mm": critical_crack_size_mm,
        }

    return {
        "disposition": "reject_and_quarantine",
        "rationale": (
            f"Detected defect ({defect_size_mm} mm) meets or exceeds critical crack size "
            f"({critical_crack_size_mm} mm). Reject item, quarantine, and raise "
            "non-conformance report per Q-ST-70-15 interface."
        ),
        "defect_size_mm": defect_size_mm,
        "critical_crack_size_mm": critical_crack_size_mm,
    }


def assess_pfci(
    ndt_method: str,
    material: str,
    location: str,
    assumed_crack_mm: float,
    traceability_record: Dict[str, Any],
    detected_defect_size_mm: Optional[float] = None,
    critical_crack_size_mm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Full PFCI NDT assessment: adequacy check, traceability verification, and
    (when a defect was found) defect disposition.

    A PFCI is compliant only when:
      - NDT adequacy check passes, AND
      - Traceability record is complete, AND
      - No defect was detected (detected_defect_size_mm is None).

    Any detected defect makes the item non-compliant regardless of its size;
    defect_disposition indicates the required corrective action.

    Returns a dict with keys:
      compliant (bool), ndt_adequacy (dict), traceability (dict), defect_disposition (dict | None)
    """
    if detected_defect_size_mm is not None and critical_crack_size_mm is None:
        raise ValueError(
            "critical_crack_size_mm is required when detected_defect_size_mm is provided"
        )

    adequacy = check_ndt_adequacy(ndt_method, material, location, assumed_crack_mm)
    traceability = verify_traceability_record(traceability_record)

    defect_disposition: Optional[Dict[str, Any]] = None
    if detected_defect_size_mm is not None:
        defect_disposition = handle_detected_defect(
            detected_defect_size_mm, critical_crack_size_mm  # type: ignore[arg-type]
        )

    compliant = (
        adequacy["adequate"]
        and traceability["complete"]
        and detected_defect_size_mm is None
    )

    return {
        "compliant": compliant,
        "ndt_adequacy": adequacy,
        "traceability": traceability,
        "defect_disposition": defect_disposition,
    }

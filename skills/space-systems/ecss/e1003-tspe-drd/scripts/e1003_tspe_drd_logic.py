"""
TSPE DRD validation logic — ECSS-E-ST-10C Annex B.

Validates that a Test Specification document contains every section required
by the DRD: identification (ID, name, test-type), objective description,
conditions (environment, configuration, stimuli), ordered procedure steps,
and measurable success criteria (parameter, limit, unit).
"""

from dataclasses import dataclass, field
from typing import List, Dict

# Top-level keys every TSPE document must carry
REQUIRED_TSPE_KEYS = {
    "test_id",
    "test_name",
    "test_type",
    "description",
    "conditions",
    "procedure",
    "success_criteria",
}

# Recognized test-type categories per ECSS-E-ST-10C vocabulary
VALID_TEST_TYPES = {
    "functional",
    "performance",
    "qualification",
    "acceptance",
    "proto-flight",
    "verification",
    "environmental",
}

# Mandatory sub-fields in the conditions block
REQUIRED_CONDITION_KEYS = {"environment", "configuration", "stimuli"}

# Mandatory sub-fields in each success criterion
REQUIRED_CRITERION_KEYS = {"parameter", "limit", "unit"}


@dataclass
class DrdFinding:
    section: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class TspeValidationResult:
    test_id: str
    compliant: bool
    findings: List[DrdFinding] = field(default_factory=list)


def validate_test_identification(doc: dict) -> List[DrdFinding]:
    """Check ID, name, and test-type category in the identification block."""
    findings: List[DrdFinding] = []
    for key in ("test_id", "test_name", "test_type"):
        if not doc.get(key):
            findings.append(DrdFinding(
                section="identification",
                severity="error",
                message=f"Missing or empty required field '{key}' in identification block.",
            ))
    test_type = doc.get("test_type", "")
    if test_type and test_type not in VALID_TEST_TYPES:
        findings.append(DrdFinding(
            section="identification",
            severity="error",
            message=(
                f"test_type '{test_type}' is not a recognized ECSS-E-ST-10C test category. "
                f"Expected one of: {sorted(VALID_TEST_TYPES)}."
            ),
        ))
    return findings


def validate_description(doc: dict) -> List[DrdFinding]:
    """Check the test objective description for presence and minimal substance."""
    findings: List[DrdFinding] = []
    desc = doc.get("description", "")
    if not desc:
        findings.append(DrdFinding(
            section="description",
            severity="error",
            message="Test objective description is absent or empty.",
        ))
    elif len(desc.split()) < 10:
        findings.append(DrdFinding(
            section="description",
            severity="warning",
            message=(
                "Test description has fewer than 10 words; the DRD requires a substantive "
                "objective statement that captures the test purpose and scope."
            ),
        ))
    return findings


def validate_conditions(conditions: object) -> List[DrdFinding]:
    """
    Check the conditions block for all three mandatory sub-fields:
    environment, configuration, and stimuli.
    """
    findings: List[DrdFinding] = []
    if not isinstance(conditions, dict):
        findings.append(DrdFinding(
            section="conditions",
            severity="error",
            message=(
                "The 'conditions' field must be a mapping containing "
                "environment, configuration, and stimuli sub-fields."
            ),
        ))
        return findings
    for key in REQUIRED_CONDITION_KEYS:
        if not conditions.get(key):
            findings.append(DrdFinding(
                section="conditions",
                severity="error",
                message=(
                    f"Conditions block is missing required sub-field '{key}'. "
                    "All three sub-fields are mandatory to reproduce the test."
                ),
            ))
    return findings


def validate_procedure(procedure: object) -> List[DrdFinding]:
    """
    Check the procedure list: must be non-empty, each step must carry
    step_number and action.
    """
    findings: List[DrdFinding] = []
    if not isinstance(procedure, list) or len(procedure) == 0:
        findings.append(DrdFinding(
            section="procedure",
            severity="error",
            message="Procedure must be a non-empty ordered list of step mappings.",
        ))
        return findings
    for i, step in enumerate(procedure):
        if not isinstance(step, dict):
            findings.append(DrdFinding(
                section="procedure",
                severity="error",
                message=f"Procedure entry at index {i} is not a mapping.",
            ))
            continue
        if "step_number" not in step:
            findings.append(DrdFinding(
                section="procedure",
                severity="error",
                message=f"Procedure step at index {i} is missing 'step_number'.",
            ))
        if not step.get("action"):
            findings.append(DrdFinding(
                section="procedure",
                severity="error",
                message=f"Procedure step at index {i} is missing or has an empty 'action'.",
            ))
    return findings


def validate_success_criteria(criteria: object) -> List[DrdFinding]:
    """
    Check the success criteria list: must be non-empty, each criterion must
    carry parameter, limit, and unit.
    """
    findings: List[DrdFinding] = []
    if not isinstance(criteria, list) or len(criteria) == 0:
        findings.append(DrdFinding(
            section="success_criteria",
            severity="error",
            message=(
                "Success criteria must be a non-empty list of measurable "
                "pass/fail thresholds."
            ),
        ))
        return findings
    for i, crit in enumerate(criteria):
        if not isinstance(crit, dict):
            findings.append(DrdFinding(
                section="success_criteria",
                severity="error",
                message=f"Success criterion at index {i} is not a mapping.",
            ))
            continue
        for key in REQUIRED_CRITERION_KEYS:
            if crit.get(key) is None:
                findings.append(DrdFinding(
                    section="success_criteria",
                    severity="error",
                    message=(
                        f"Success criterion at index {i} is missing '{key}'. "
                        "Each criterion must specify parameter, limit, and unit."
                    ),
                ))
    return findings


def validate_tspe_document(doc: dict) -> TspeValidationResult:
    """
    Full DRD compliance check for a TSPE document dict.
    Structural gaps are reported first; sub-field checks run only when
    the top-level structure is intact.
    """
    test_id = doc.get("test_id", "<unknown>")
    findings: List[DrdFinding] = []

    missing_keys = REQUIRED_TSPE_KEYS - set(doc.keys())
    for key in sorted(missing_keys):
        findings.append(DrdFinding(
            section="structure",
            severity="error",
            message=f"TSPE document is missing required top-level key '{key}'.",
        ))

    if not missing_keys:
        findings += validate_test_identification(doc)
        findings += validate_description(doc)
        findings += validate_conditions(doc.get("conditions", {}))
        findings += validate_procedure(doc.get("procedure", []))
        findings += validate_success_criteria(doc.get("success_criteria", []))

    errors = [f for f in findings if f.severity == "error"]
    return TspeValidationResult(
        test_id=test_id,
        compliant=len(errors) == 0,
        findings=findings,
    )


def generate_drd_compliance_report(doc: dict) -> Dict:
    """
    Build a structured compliance report from a TSPE document.
    The report captures the ECSS-E-ST-10C Annex B standard reference,
    the overall compliance verdict, and itemised error and warning lists.
    """
    result = validate_tspe_document(doc)
    errors = [f for f in result.findings if f.severity == "error"]
    warnings = [f for f in result.findings if f.severity == "warning"]
    return {
        "test_id": result.test_id,
        "drd_standard": "ECSS-E-ST-10C Annex B",
        "compliant": result.compliant,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": [{"section": f.section, "message": f.message} for f in errors],
        "warnings": [{"section": f.section, "message": f.message} for f in warnings],
    }

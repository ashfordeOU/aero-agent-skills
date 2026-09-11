"""
Test programme definition logic for ECSS-E-ST-10C §4.1.

Covers: models under test and their test levels, test sequence
validation, functional-test bookend check, programme documentation
completeness, and verification input checks.

All logic is deterministic, offline, stdlib-only.
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MODEL_TYPES: FrozenSet[str] = frozenset({"BB", "EM", "QM", "EQM", "PFM", "FM"})

MODEL_TEST_LEVEL: Dict[str, str] = {
    "BB":  "development",
    "EM":  "development",
    "QM":  "qualification",
    "EQM": "qualification",
    "PFM": "proto-flight",
    "FM":  "acceptance",
}

VALID_TEST_TYPES: FrozenSet[str] = frozenset({
    "functional",
    "vibration-sine",
    "vibration-random",
    "acoustic",
    "shock",
    "thermal-vacuum",
    "thermal-cycling",
    "emc",
    "radiation",
    "inspection",
    "mass-properties",
    "leak",
    "pressure",
    "alignment",
})

REQUIRED_PROGRAMME_DOCUMENTS: FrozenSet[str] = frozenset({
    "test-plan",
    "test-procedures",
    "verification-control-document",
    "test-reports",
})

VERIFICATION_INPUTS_BY_TEST: Dict[str, List[str]] = {
    "functional":       ["functional-baseline", "requirement-list"],
    "vibration-sine":   ["loads-environment", "qualification-levels"],
    "vibration-random": ["loads-environment", "qualification-levels"],
    "acoustic":         ["acoustic-environment", "qualification-levels"],
    "shock":            ["shock-environment", "qualification-levels"],
    "thermal-vacuum":   ["thermal-model", "thermal-environment", "qualification-levels"],
    "thermal-cycling":  ["thermal-model", "thermal-environment"],
    "emc":              ["emc-environment", "emission-limits"],
    "radiation":        ["radiation-environment", "total-dose"],
    "inspection":       ["acceptance-criteria"],
    "mass-properties":  ["mass-budget"],
    "leak":             ["leak-rate-limit", "pressurisation-levels"],
    "pressure":         ["proof-pressure", "burst-pressure"],
    "alignment":        ["alignment-requirement", "coordinate-reference"],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TestItem:
    test_id: str
    test_type: str
    model_id: str
    sequence_position: int

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.test_type not in VALID_TEST_TYPES:
            errors.append(
                f"Unknown test type '{self.test_type}' in item '{self.test_id}'"
            )
        if self.sequence_position < 1:
            errors.append(
                f"Sequence position must be >= 1, got {self.sequence_position} "
                f"in item '{self.test_id}'"
            )
        return errors


@dataclass
class ModelUnderTest:
    model_id: str
    model_type: str
    subsystem: str

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.model_type not in VALID_MODEL_TYPES:
            errors.append(
                f"Invalid model type '{self.model_type}' for model '{self.model_id}'. "
                f"Must be one of {sorted(VALID_MODEL_TYPES)}"
            )
        return errors


@dataclass
class ProgrammeDocumentSet:
    documents: Dict[str, bool]

    def missing(self) -> List[str]:
        return sorted(
            doc for doc in REQUIRED_PROGRAMME_DOCUMENTS
            if not self.documents.get(doc, False)
        )


@dataclass
class VerificationInputSet:
    test_type: str
    provided_inputs: List[str]

    def missing_inputs(self) -> List[str]:
        required = VERIFICATION_INPUTS_BY_TEST.get(self.test_type, [])
        return [inp for inp in required if inp not in self.provided_inputs]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def categorize_model(model: ModelUnderTest) -> Tuple[str, List[str]]:
    """
    Return the test level for a model under test.
    Returns (test_level, errors). errors is empty on success.
    An unrecognised model type is an explicit error.
    """
    errors = model.validate()
    if errors:
        return ("", errors)
    return (MODEL_TEST_LEVEL[model.model_type], [])


def validate_test_sequence(
    model: ModelUnderTest,
    sequence: List[TestItem],
) -> Tuple[bool, List[str]]:
    """
    Validate the test sequence for a model.

    Checks:
    - Sequence is non-empty.
    - All items reference the correct model_id.
    - Each test type is in the recognised set.
    - Sequence positions are unique and consecutive starting from 1.

    Returns (is_valid, findings).
    """
    findings: List[str] = []

    if not sequence:
        return (False, ["Test sequence is empty"])

    wrong_model = [t for t in sequence if t.model_id != model.model_id]
    if wrong_model:
        findings.append(
            f"{len(wrong_model)} item(s) reference model "
            f"'{wrong_model[0].model_id}', expected '{model.model_id}'"
        )

    for item in sequence:
        findings.extend(item.validate())

    positions = [t.sequence_position for t in sequence]
    if len(positions) != len(set(positions)):
        findings.append("Duplicate sequence positions detected")

    sorted_positions = sorted(positions)
    expected = list(range(1, len(sequence) + 1))
    if sorted_positions != expected:
        findings.append(
            f"Positions must be consecutive from 1 to {len(sequence)}, "
            f"got {sorted_positions}"
        )

    return (len(findings) == 0, findings)


def check_functional_bookend(sequence: List[TestItem]) -> Tuple[bool, List[str]]:
    """
    Verify that the sequence opens and closes with a functional test.

    A single-item sequence satisfies both bookend conditions if that
    item is a functional test.

    Returns (bookend_ok, findings).
    """
    if not sequence:
        return (False, ["Cannot check bookend on empty sequence"])

    sorted_seq = sorted(sequence, key=lambda t: t.sequence_position)
    findings: List[str] = []

    if sorted_seq[0].test_type != "functional":
        findings.append(
            f"First item (position {sorted_seq[0].sequence_position}) "
            f"is '{sorted_seq[0].test_type}'; must be 'functional'"
        )

    if len(sorted_seq) > 1 and sorted_seq[-1].test_type != "functional":
        findings.append(
            f"Last item (position {sorted_seq[-1].sequence_position}) "
            f"is '{sorted_seq[-1].test_type}'; must be 'functional'"
        )

    return (len(findings) == 0, findings)


def check_programme_documentation(
    doc_set: ProgrammeDocumentSet,
) -> Tuple[bool, List[str]]:
    """
    Check that all required programme documents are present.
    Returns (all_present, missing_list).
    """
    missing = doc_set.missing()
    return (len(missing) == 0, missing)


def check_verification_inputs(
    input_set: VerificationInputSet,
) -> Tuple[bool, List[str]]:
    """
    Check that all required verification inputs for a test type are supplied.

    An unrecognised test type is itself an error.
    Returns (complete, missing_or_error_list).
    """
    if input_set.test_type not in VALID_TEST_TYPES:
        return (False, [f"Unknown test type '{input_set.test_type}'"])
    missing = input_set.missing_inputs()
    return (len(missing) == 0, missing)


def build_programme_summary(
    models: List[ModelUnderTest],
    sequences: Dict[str, List[TestItem]],
    doc_set: ProgrammeDocumentSet,
) -> Dict:
    """
    Produce a structured summary of the test programme.

    Aggregates model categorization, sequence validation, and document
    completeness into a single result dict. The programme is valid only
    when the findings list is empty.

    Returns:
      {
        "models": {model_id: {type, test_level, subsystem,
                              sequence_count, sequence_valid}},
        "doc_status": {"complete": bool, "missing": [str]},
        "findings": [str],
        "programme_valid": bool,
      }
    """
    findings: List[str] = []
    model_info: Dict = {}

    for model in models:
        level, errors = categorize_model(model)
        if errors:
            findings.extend(errors)
            continue

        seq = sequences.get(model.model_id, [])
        seq_valid, seq_findings = validate_test_sequence(model, seq)

        if not seq_valid:
            findings.extend(seq_findings)

        model_info[model.model_id] = {
            "type": model.model_type,
            "test_level": level,
            "subsystem": model.subsystem,
            "sequence_count": len(seq),
            "sequence_valid": seq_valid,
        }

    doc_ok, missing_docs = check_programme_documentation(doc_set)
    for doc in missing_docs:
        findings.append(f"Missing programme document: {doc}")

    return {
        "models": model_info,
        "doc_status": {
            "complete": doc_ok,
            "missing": missing_docs,
        },
        "findings": findings,
        "programme_valid": len(findings) == 0,
    }

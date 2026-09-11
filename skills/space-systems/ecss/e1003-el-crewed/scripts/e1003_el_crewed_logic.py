#!/usr/bin/env python3
"""ECSS-E-ST-10C §6.5.7 crewed-mission element test acceptance logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
AIT standard's §6.5.7 mandates four test families for hardware installed in
or directly interfacing with a crewed cabin — vibroacoustic emission (the
noise and vibration the equipment radiates into the cabin structure and
atmosphere, checked against an emission limit in dB), HFE test (a human
factors engineering pass/fail verification against the HFE checklist),
toxic offgassing (concentration of any released chemical species at the
crew position checked against the per-substance cabin limit in mg/m³), and
audible noise (total in-cabin acoustic level at the crew position under
representative operating conditions, checked against the habitability limit
in dB(A)). All four families must be completed for every crewed element;
a missing family blocks acceptance. This module implements test-type
categorization, per-family acceptance evaluation, missing-family detection,
and a full crewed-element aggregated review.
"""

CREWED_TEST_FAMILIES = frozenset(
    {"vibroacoustic_emission", "hfe_test", "toxic_offgassing", "audible_noise"}
)


def categorize_test(test_type):
    """Return the test family for test_type (one of CREWED_TEST_FAMILIES).
    Raises ValueError for a test type not in the §6.5.7 family set."""
    if test_type in CREWED_TEST_FAMILIES:
        return test_type
    raise ValueError(
        "unrecognized crewed-mission test type %r; must be one of %s"
        % (test_type, sorted(CREWED_TEST_FAMILIES))
    )


def check_vibroacoustic_emission(equipment_id, measured_db, limit_db):
    """Acceptance check for the vibroacoustic-emission test family.

    measured_db: measured equipment emission level in dB (>= 0).
    limit_db: acceptance emission limit in dB (> 0).
    Returns a list with one violation dict if measured_db > limit_db,
    else an empty list. Raises ValueError for out-of-range inputs."""
    if measured_db < 0:
        raise ValueError("measured_db must be >= 0, got %r" % measured_db)
    if limit_db <= 0:
        raise ValueError("limit_db must be > 0, got %r" % limit_db)
    if measured_db > limit_db:
        return [
            {
                "issue": "vibroacoustic_emission_exceeds_limit",
                "equipment": equipment_id,
                "measured_db": measured_db,
                "limit_db": limit_db,
            }
        ]
    return []


def check_hfe_test(equipment_id, passed):
    """Acceptance check for the HFE test family.

    passed: bool — True when the formal HFE checklist judgment is a pass.
    Returns a list with one violation dict when passed is False, else [].
    Raises ValueError if passed is not a bool."""
    if not isinstance(passed, bool):
        raise ValueError(
            "passed must be a bool, got %r" % type(passed).__name__
        )
    if not passed:
        return [{"issue": "hfe_test_failed", "equipment": equipment_id}]
    return []


def check_toxic_offgassing(equipment_id, substance, measured_mg_m3, limit_mg_m3):
    """Acceptance check for one substance in the toxic-offgassing family.

    substance: identifier string for the offgassing species.
    measured_mg_m3: measured cabin concentration in mg/m³ (>= 0).
    limit_mg_m3: per-substance cabin atmosphere limit in mg/m³ (> 0).
    Returns a list with one violation dict if measured > limit, else [].
    Raises ValueError for out-of-range inputs."""
    if measured_mg_m3 < 0:
        raise ValueError("measured_mg_m3 must be >= 0, got %r" % measured_mg_m3)
    if limit_mg_m3 <= 0:
        raise ValueError("limit_mg_m3 must be > 0, got %r" % limit_mg_m3)
    if measured_mg_m3 > limit_mg_m3:
        return [
            {
                "issue": "toxic_offgassing_exceeds_limit",
                "equipment": equipment_id,
                "substance": substance,
                "measured_mg_m3": measured_mg_m3,
                "limit_mg_m3": limit_mg_m3,
            }
        ]
    return []


def check_audible_noise(equipment_id, measured_dba, limit_dba):
    """Acceptance check for the audible-noise test family.

    measured_dba: measured in-cabin noise level in dB(A) at the crew
    position (>= 0).
    limit_dba: habitability noise limit in dB(A) (> 0).
    Returns a list with one violation dict if measured_dba > limit_dba,
    else []. Raises ValueError for out-of-range inputs."""
    if measured_dba < 0:
        raise ValueError("measured_dba must be >= 0, got %r" % measured_dba)
    if limit_dba <= 0:
        raise ValueError("limit_dba must be > 0, got %r" % limit_dba)
    if measured_dba > limit_dba:
        return [
            {
                "issue": "audible_noise_exceeds_limit",
                "equipment": equipment_id,
                "measured_dba": measured_dba,
                "limit_dba": limit_dba,
            }
        ]
    return []


def _evaluate_record(equipment_id, record):
    """Dispatch a single test record to the appropriate family checker.
    record must contain "test_type" plus the family-specific fields.
    Raises ValueError for an unrecognized test_type or missing fields."""
    test_type = categorize_test(record["test_type"])
    if test_type == "vibroacoustic_emission":
        return check_vibroacoustic_emission(
            equipment_id, record["measured_db"], record["limit_db"]
        )
    if test_type == "hfe_test":
        return check_hfe_test(equipment_id, record["passed"])
    if test_type == "toxic_offgassing":
        findings = []
        for entry in record["substances"]:
            findings.extend(
                check_toxic_offgassing(
                    equipment_id,
                    entry["substance"],
                    entry["measured_mg_m3"],
                    entry["limit_mg_m3"],
                )
            )
        return findings
    if test_type == "audible_noise":
        return check_audible_noise(
            equipment_id, record["measured_dba"], record["limit_dba"]
        )
    return []


def crewed_element_review(equipment_id, test_records):
    """Full §6.5.7 crewed-mission element review for one equipment item.

    equipment_id: identifier string for the equipment item under review.
    test_records: iterable of dicts, each with "test_type" plus the
    family-specific measurement fields (see per-family check functions).
    Returns {"findings": [...], "missing_families": [...]}.
    findings: violation dicts from all records with limit exceedances or
    failed judgments. missing_families: sorted list of the §6.5.7 test
    families for which no record was provided — each is an acceptance
    blocker. Raises ValueError for an unrecognized test_type in any record."""
    findings = []
    covered = set()
    for record in test_records:
        test_type = categorize_test(record["test_type"])
        covered.add(test_type)
        findings.extend(_evaluate_record(equipment_id, record))
    missing = sorted(CREWED_TEST_FAMILIES - covered)
    return {"findings": findings, "missing_families": missing}


def is_crewed_element_compliant(review):
    """True when the crewed_element_review result has no findings and no
    missing test families — the equipment item satisfies §6.5.7."""
    return len(review["findings"]) == 0 and len(review["missing_families"]) == 0

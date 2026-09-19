"""Contract test for the q2007-tf-design leaf (stdlib unittest)."""

import unittest

from q2007_tf_design_logic import (
    CHANGE_MAJOR,
    CHANGE_MINOR,
    CHANGE_NEW,
    CRITICALITY_OPERATIONAL,
    CRITICALITY_SAFETY,
    FINDING_GATE_OPEN,
    FINDING_GATE_OUT_OF_ORDER,
    FINDING_NO_EVIDENCE,
    FINDING_SAFETY_BY_REVIEW_ONLY,
    FINDING_SAFETY_WAIVED,
    FINDING_WAIVER_NO_REFERENCE,
    GATE_CRITICAL_DESIGN_REVIEW,
    GATE_FACILITY_ACCEPTANCE_REVIEW,
    GATE_PRELIMINARY_DESIGN_REVIEW,
    GATE_REQUIREMENTS_REVIEW,
    METHOD_REVIEW_OF_DESIGN,
    METHOD_TEST,
    STATUS_IN_WORK,
    STATUS_NOT_STARTED,
    STATUS_VERIFIED,
    STATUS_WAIVED,
    assess_facility_development,
    assess_requirement,
    gate_findings,
    requirement_findings,
    requirement_is_open,
    required_gates,
    validate_gate_record,
    validate_requirement,
    verification_coverage,
)


def requirement(req_id="FR-1", **kw):
    record = {
        "id": req_id,
        "criticality": CRITICALITY_OPERATIONAL,
        "verification_method": METHOD_TEST,
        "status": STATUS_VERIFIED,
        "evidence_reference": "TR-0042",
    }
    record.update(kw)
    return record


def safety_requirement(req_id="FR-S1", **kw):
    record = {
        "id": req_id,
        "criticality": CRITICALITY_SAFETY,
        "verification_method": METHOD_TEST,
        "status": STATUS_VERIFIED,
        "evidence_reference": "TR-0100",
    }
    record.update(kw)
    return record


def minor_project(**kw):
    project = {
        "change_category": CHANGE_MINOR,
        "requirements": [requirement()],
        "closed_gates": [GATE_REQUIREMENTS_REVIEW, GATE_FACILITY_ACCEPTANCE_REVIEW],
    }
    project.update(kw)
    return project


class TestChangeCategory(unittest.TestCase):
    def test_a_new_facility_owes_four_reviews(self):
        self.assertEqual(len(required_gates(CHANGE_NEW)), 4)

    def test_a_major_modification_drops_the_preliminary_review(self):
        self.assertNotIn(GATE_PRELIMINARY_DESIGN_REVIEW, required_gates(CHANGE_MAJOR))

    def test_a_minor_modification_owes_two_reviews(self):
        self.assertEqual(
            required_gates(CHANGE_MINOR),
            (GATE_REQUIREMENTS_REVIEW, GATE_FACILITY_ACCEPTANCE_REVIEW),
        )

    def test_every_category_starts_with_requirements_and_ends_with_acceptance(self):
        for category in (CHANGE_NEW, CHANGE_MAJOR, CHANGE_MINOR):
            gates = required_gates(category)
            self.assertEqual(gates[0], GATE_REQUIREMENTS_REVIEW)
            self.assertEqual(gates[-1], GATE_FACILITY_ACCEPTANCE_REVIEW)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            required_gates("repaint")


class TestRequirementValidation(unittest.TestCase):
    def test_status_defaults_to_not_started(self):
        norm = validate_requirement(
            {
                "id": "FR-9",
                "criticality": CRITICALITY_OPERATIONAL,
                "verification_method": METHOD_TEST,
            }
        )
        self.assertEqual(norm["status"], STATUS_NOT_STARTED)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(["FR-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(""))

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(criticality="nice-to-have"))

    def test_unknown_verification_method_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(verification_method="demonstration"))

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(status="nearly"))

    def test_blank_evidence_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(evidence_reference="   "))


class TestRequirementRules(unittest.TestCase):
    def test_a_well_formed_requirement_carries_no_finding(self):
        self.assertEqual(requirement_findings(requirement()), [])

    def test_safety_by_review_of_design_alone_is_flagged(self):
        record = safety_requirement(verification_method=METHOD_REVIEW_OF_DESIGN)
        self.assertIn(FINDING_SAFETY_BY_REVIEW_ONLY, requirement_findings(record))

    def test_review_of_design_is_acceptable_for_a_non_safety_requirement(self):
        record = requirement(verification_method=METHOD_REVIEW_OF_DESIGN)
        self.assertEqual(requirement_findings(record), [])

    def test_verified_without_evidence_is_flagged(self):
        record = requirement(evidence_reference=None)
        self.assertIn(FINDING_NO_EVIDENCE, requirement_findings(record))

    def test_waiver_without_a_reference_is_flagged(self):
        record = requirement(status=STATUS_WAIVED, evidence_reference=None)
        self.assertIn(FINDING_WAIVER_NO_REFERENCE, requirement_findings(record))

    def test_a_referenced_waiver_on_a_non_safety_requirement_is_accepted(self):
        record = requirement(
            status=STATUS_WAIVED, evidence_reference=None, waiver_reference="WV-7"
        )
        self.assertEqual(requirement_findings(record), [])

    def test_a_safety_requirement_cannot_be_waived_even_with_a_reference(self):
        record = safety_requirement(
            status=STATUS_WAIVED, evidence_reference=None, waiver_reference="WV-8"
        )
        self.assertIn(FINDING_SAFETY_WAIVED, requirement_findings(record))

    def test_open_statuses_are_recognised(self):
        self.assertTrue(requirement_is_open(requirement(status=STATUS_IN_WORK)))
        self.assertTrue(requirement_is_open(requirement(status=STATUS_NOT_STARTED)))

    def test_verified_and_waived_are_not_open(self):
        self.assertFalse(requirement_is_open(requirement()))
        self.assertFalse(
            requirement_is_open(
                requirement(status=STATUS_WAIVED, waiver_reference="WV-1")
            )
        )

    def test_an_open_requirement_is_not_itself_a_finding(self):
        result = assess_requirement(requirement(status=STATUS_IN_WORK))
        self.assertTrue(result["open"])
        self.assertTrue(result["sound"])


class TestCoverage(unittest.TestCase):
    def test_all_verified_scores_one(self):
        self.assertAlmostEqual(
            verification_coverage([requirement("FR-1"), requirement("FR-2")]),
            1.0,
            places=9,
        )

    def test_one_of_four_open_scores_three_quarters(self):
        records = [
            requirement("FR-1"),
            requirement("FR-2"),
            requirement("FR-3"),
            requirement("FR-4", status=STATUS_IN_WORK),
        ]
        self.assertAlmostEqual(verification_coverage(records), 0.75, places=9)

    def test_a_waived_requirement_does_not_count_as_verified(self):
        records = [
            requirement("FR-1"),
            requirement("FR-2", status=STATUS_WAIVED, waiver_reference="WV-1"),
        ]
        self.assertAlmostEqual(verification_coverage(records), 0.5, places=9)

    def test_empty_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            verification_coverage([])


class TestGates(unittest.TestCase):
    def test_a_complete_gate_record_has_no_finding(self):
        closed = [GATE_REQUIREMENTS_REVIEW, GATE_FACILITY_ACCEPTANCE_REVIEW]
        self.assertEqual(gate_findings(CHANGE_MINOR, closed), [])

    def test_a_missing_review_is_flagged(self):
        findings = gate_findings(CHANGE_MINOR, [GATE_REQUIREMENTS_REVIEW])
        self.assertEqual(findings[0]["finding"], FINDING_GATE_OPEN)
        self.assertEqual(findings[0]["review"], GATE_FACILITY_ACCEPTANCE_REVIEW)

    def test_a_later_review_closed_first_names_the_earlier_one(self):
        findings = gate_findings(CHANGE_MINOR, [GATE_FACILITY_ACCEPTANCE_REVIEW])
        out_of_order = [
            f for f in findings if f["finding"] == FINDING_GATE_OUT_OF_ORDER
        ]
        self.assertEqual(out_of_order[0]["review"], GATE_FACILITY_ACCEPTANCE_REVIEW)
        self.assertEqual(out_of_order[0]["earlier_review"], GATE_REQUIREMENTS_REVIEW)

    def test_a_review_outside_the_category_set_raises(self):
        with self.assertRaises(ValueError):
            gate_findings(CHANGE_MINOR, [GATE_CRITICAL_DESIGN_REVIEW])

    def test_a_review_recorded_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_gate_record(
                CHANGE_MINOR, [GATE_REQUIREMENTS_REVIEW, GATE_REQUIREMENTS_REVIEW]
            )

    def test_a_string_gate_record_raises(self):
        with self.assertRaises(ValueError):
            validate_gate_record(CHANGE_MINOR, GATE_REQUIREMENTS_REVIEW)

    def test_an_empty_gate_record_flags_every_required_review(self):
        findings = gate_findings(CHANGE_NEW, [])
        opens = [f for f in findings if f["finding"] == FINDING_GATE_OPEN]
        self.assertEqual(len(opens), 4)


class TestFacilityDevelopment(unittest.TestCase):
    def test_a_complete_minor_modification_is_ready_for_use(self):
        report = assess_facility_development(minor_project())
        self.assertTrue(report["ready_for_use"])
        self.assertEqual(report["blocking_reasons"], [])
        self.assertAlmostEqual(report["verification_coverage"], 1.0, places=9)

    def test_an_open_requirement_blocks_use(self):
        report = assess_facility_development(
            minor_project(requirements=[requirement(status=STATUS_IN_WORK)])
        )
        self.assertFalse(report["ready_for_use"])
        self.assertIn("requirements-still-open", report["blocking_reasons"])

    def test_an_unclosed_review_blocks_use(self):
        report = assess_facility_development(
            minor_project(closed_gates=[GATE_REQUIREMENTS_REVIEW])
        )
        self.assertFalse(report["ready_for_use"])
        self.assertIn(
            "required-reviews-not-closed-in-order", report["blocking_reasons"]
        )

    def test_a_requirement_finding_blocks_use_even_at_full_coverage(self):
        report = assess_facility_development(
            minor_project(
                requirements=[
                    safety_requirement(verification_method=METHOD_REVIEW_OF_DESIGN)
                ]
            )
        )
        self.assertAlmostEqual(report["verification_coverage"], 1.0, places=9)
        self.assertFalse(report["ready_for_use"])
        self.assertIn("requirements-carrying-findings", report["blocking_reasons"])

    def test_a_new_facility_with_a_minor_gate_record_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_facility_development(
                minor_project(
                    change_category=CHANGE_NEW,
                    closed_gates=[
                        GATE_REQUIREMENTS_REVIEW,
                        GATE_FACILITY_ACCEPTANCE_REVIEW,
                        "repaint-review",
                    ],
                )
            )

    def test_the_required_gate_list_is_reported_back(self):
        report = assess_facility_development(minor_project())
        self.assertEqual(report["required_gates"], list(required_gates(CHANGE_MINOR)))

    def test_duplicate_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            assess_facility_development(
                minor_project(requirements=[requirement("FR-1"), requirement("FR-1")])
            )

    def test_an_empty_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            assess_facility_development(minor_project(requirements=[]))

    def test_a_non_mapping_project_raises(self):
        with self.assertRaises(ValueError):
            assess_facility_development([minor_project()])

    def test_an_unknown_change_category_raises(self):
        with self.assertRaises(ValueError):
            assess_facility_development(minor_project(change_category="refresh"))


if __name__ == "__main__":
    unittest.main()

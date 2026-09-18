"""Contract tests for the Annex A quality assurance plan DRD logic."""

import unittest

from q20_qap_drd_logic import (
    BASE_TASKS,
    CONTRACT_LEVELS,
    DRD_SECTIONS,
    LEVEL_TASKS,
    SECTION_SUBJECTS,
    UNTAILORABLE_SECTIONS,
    assess_qa_plan,
    conformance_fraction,
    normalise_identifier,
    plan_outline,
    reference_findings,
    required_tasks,
    section_findings,
    task_findings,
    validate_plan,
)


def full_plan(contract_level="prime", **changes):
    """Return a plan that answers the whole DRD at the given level."""
    sections = []
    for name in DRD_SECTIONS:
        sections.append({"section": name, "subjects": list(SECTION_SUBJECTS[name])})
    for key, replacement in changes.items():
        name = key.replace("_", "-")
        sections = [item for item in sections if item["section"] != name]
        if replacement is not None:
            sections.append(replacement)
    return {
        "sections": sections,
        "tasks": list(required_tasks(contract_level)),
        "reference_documents": ["qp-001", "qp-002"],
        "cited_documents": ["qp-001"],
    }


class VocabularyTests(unittest.TestCase):
    def test_contract_levels(self):
        self.assertEqual(len(CONTRACT_LEVELS), 3)
        self.assertIn("supplier", CONTRACT_LEVELS)

    def test_every_drd_section_names_its_subjects(self):
        self.assertEqual(set(SECTION_SUBJECTS), set(DRD_SECTIONS))

    def test_untailorable_sections_are_drd_sections(self):
        self.assertTrue(set(UNTAILORABLE_SECTIONS).issubset(set(DRD_SECTIONS)))

    def test_every_level_owes_the_base_tasks(self):
        for level in CONTRACT_LEVELS:
            for task in BASE_TASKS:
                self.assertIn(task, required_tasks(level))

    def test_prime_owes_an_audit_programme(self):
        self.assertIn("internal-audit-programme", required_tasks("prime"))

    def test_supplier_does_not_owe_an_audit_programme(self):
        self.assertNotIn("internal-audit-programme", required_tasks("supplier"))

    def test_level_tasks_cover_every_level(self):
        self.assertEqual(set(LEVEL_TASKS), set(CONTRACT_LEVELS))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            required_tasks("integrator")

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier("  Plan-Maintenance ", "s"), "plan-maintenance")


class OutlineTests(unittest.TestCase):
    def test_outline_follows_the_drd_order(self):
        outline = plan_outline("prime")
        self.assertEqual(tuple(item["section"] for item in outline), DRD_SECTIONS)

    def test_outline_numbers_sections_from_one(self):
        outline = plan_outline("supplier")
        self.assertEqual(outline[0]["number"], "1")
        self.assertEqual(outline[-1]["number"], str(len(DRD_SECTIONS)))

    def test_outline_numbers_subjects_within_their_section(self):
        outline = plan_outline("prime")
        third = outline[2]
        self.assertEqual(third["subjects"][0]["number"], "3.1")

    def test_outline_carries_the_level_task_set(self):
        outline = plan_outline("subcontractor")
        tasks = [item for item in outline if item["section"] == "quality-task-provisions"][0]
        self.assertIn("requirement-flow-down-verification", tasks["tasks"])


class ValidationTests(unittest.TestCase):
    def test_clean_plan_validates(self):
        normalised = validate_plan(full_plan())
        self.assertEqual(len(normalised["sections"]), len(DRD_SECTIONS))

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(["introduction-and-scope"])

    def test_empty_section_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan({"sections": []})

    def test_duplicate_section_rejected(self):
        plan = full_plan()
        plan["sections"].append({"section": "plan-maintenance", "subjects": []})
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_blank_justification_rejected(self):
        plan = full_plan(
            plan_maintenance={
                "section": "plan-maintenance",
                "not_applicable": True,
                "justification": "   ",
            }
        )
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_non_sequence_tasks_rejected(self):
        plan = full_plan()
        plan["tasks"] = "procurement-control"
        with self.assertRaises(ValueError):
            validate_plan(plan)


class SectionGradingTests(unittest.TestCase):
    def test_full_plan_has_no_finding(self):
        result = section_findings(validate_plan(full_plan()))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["satisfied_count"], len(DRD_SECTIONS))

    def test_absent_section_is_reported(self):
        result = section_findings(validate_plan(full_plan(documentation_and_records=None)))
        self.assertEqual(result["missing"], ["documentation-and-records"])

    def test_section_missing_a_subject_is_incomplete(self):
        plan = full_plan(
            organization_and_responsibilities={
                "section": "organization-and-responsibilities",
                "subjects": ["reporting-line", "resource-and-authority"],
            }
        )
        result = section_findings(validate_plan(plan))
        self.assertIn("quality-function-independence", result["incomplete"][0])

    def test_accepted_tailoring_counts_as_satisfied(self):
        plan = full_plan(
            plan_maintenance={
                "section": "plan-maintenance",
                "not_applicable": True,
                "justification": "plan issued once for a single-delivery contract",
                "approved_by": "customer-product-assurance",
            }
        )
        result = section_findings(validate_plan(plan))
        self.assertEqual(result["accepted_not_applicable"], ["plan-maintenance"])
        self.assertEqual(result["findings"], [])

    def test_tailoring_scope_out_is_refused(self):
        plan = full_plan(
            introduction_and_scope={
                "section": "introduction-and-scope",
                "not_applicable": True,
                "justification": "covered by the contract",
                "approved_by": "customer-product-assurance",
            }
        )
        result = section_findings(validate_plan(plan))
        self.assertIn("cannot be declared not applicable", result["findings"][0])

    def test_tailoring_without_approver_is_refused(self):
        plan = full_plan(
            plan_maintenance={
                "section": "plan-maintenance",
                "not_applicable": True,
                "justification": "single issue contract",
            }
        )
        result = section_findings(validate_plan(plan))
        self.assertIn("no customer approver", result["findings"][0])

    def test_undemanded_section_is_listed_as_an_extra(self):
        plan = full_plan()
        plan["sections"].append({"section": "annex-glossary", "subjects": []})
        result = section_findings(validate_plan(plan))
        self.assertEqual(result["extras"], ["annex-glossary"])
        self.assertEqual(result["findings"], [])

    def test_malformed_normalised_input_rejected(self):
        with self.assertRaises(ValueError):
            section_findings({"tasks": ()})


class TaskProvisionTests(unittest.TestCase):
    def test_matching_task_set_is_clean(self):
        result = task_findings("prime", validate_plan(full_plan("prime")))
        self.assertEqual(result["findings"], [])

    def test_prime_plan_graded_as_prime_finds_the_gap(self):
        plan = full_plan("supplier")
        result = task_findings("prime", validate_plan(plan))
        self.assertIn("internal-audit-programme", result["missing_tasks"])

    def test_task_beyond_the_level_is_an_extra_not_a_finding(self):
        plan = full_plan("supplier")
        plan["tasks"].append("internal-audit-programme")
        result = task_findings("supplier", validate_plan(plan))
        self.assertEqual(result["extra_tasks"], ["internal-audit-programme"])
        self.assertEqual(result["findings"], [])


class ReferenceTests(unittest.TestCase):
    def test_resolvable_citation_is_clean(self):
        self.assertEqual(reference_findings(validate_plan(full_plan())), [])

    def test_dangling_citation_is_a_finding(self):
        plan = full_plan()
        plan["cited_documents"].append("qp-999")
        findings = reference_findings(validate_plan(plan))
        self.assertIn("qp-999", findings[0])

    def test_a_dangling_citation_is_named_once(self):
        plan = full_plan()
        plan["cited_documents"] = ["qp-999", "qp-999"]
        findings = reference_findings(validate_plan(plan))
        self.assertEqual(findings[0].count("qp-999"), 1)


class ConformanceTests(unittest.TestCase):
    def test_full_plan_is_one(self):
        result = section_findings(validate_plan(full_plan()))
        self.assertAlmostEqual(conformance_fraction(result), 1.0, places=9)

    def test_one_absent_section_lowers_the_fraction(self):
        result = section_findings(validate_plan(full_plan(plan_maintenance=None)))
        total = len(DRD_SECTIONS)
        self.assertAlmostEqual(
            conformance_fraction(result), (total - 1) / float(total), places=9
        )

    def test_zero_required_count_rejected(self):
        with self.assertRaises(ValueError):
            conformance_fraction({"required_count": 0, "satisfied_count": 0})

    def test_malformed_result_rejected(self):
        with self.assertRaises(ValueError):
            conformance_fraction({"satisfied_count": 3})


class AssessmentTests(unittest.TestCase):
    def test_full_prime_plan_is_conformant(self):
        result = assess_qa_plan("prime", full_plan("prime"))
        self.assertEqual(result["verdict"], "plan-conformant")
        self.assertAlmostEqual(result["conformance_fraction"], 1.0, places=9)

    def test_full_supplier_plan_is_conformant(self):
        result = assess_qa_plan("supplier", full_plan("supplier"))
        self.assertEqual(result["verdict"], "plan-conformant")

    def test_absent_section_makes_the_plan_nonconformant(self):
        result = assess_qa_plan("prime", full_plan("prime", plan_maintenance=None))
        self.assertEqual(result["verdict"], "plan-nonconformant")
        self.assertEqual(result["missing_sections"], ["plan-maintenance"])

    def test_dangling_citation_makes_the_plan_nonconformant(self):
        plan = full_plan("prime")
        plan["cited_documents"].append("qp-404")
        self.assertEqual(assess_qa_plan("prime", plan)["verdict"], "plan-nonconformant")

    def test_counts_are_reported_for_evidence(self):
        result = assess_qa_plan("subcontractor", full_plan("subcontractor"))
        self.assertEqual(result["required_count"], len(DRD_SECTIONS))
        self.assertEqual(result["satisfied_count"], result["required_count"])

    def test_unknown_level_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_qa_plan("integrator", full_plan("prime"))


if __name__ == "__main__":
    unittest.main()

"""Contract test for the q40-02-process-principles leaf (stdlib unittest)."""

import unittest

from q40_02_process_principles_logic import (
    PROCESS_ELEMENTS,
    assess_process_definition,
    documentation_findings,
    element_score,
    missing_elements,
    review_integration_findings,
    technique_findings,
    update_trigger_findings,
    validate_process,
)


def process(pid="HAP-1", **kw):
    record = {
        "id": pid,
        "declared_elements": list(PROCESS_ELEMENTS),
        "analysis_levels": ["functional", "system"],
        "techniques_by_level": {
            "functional": ["functional-hazard-analysis"],
            "system": ["fault-tree-analysis",
                       "failure-modes-effects-and-criticality-analysis"],
        },
        "iteration_reviews": ["pdr", "cdr"],
        "documentation_set": ["hazard-analysis-report", "hazard-log",
                              "traceability-to-requirements"],
        "update_triggers": ["design-change", "anomaly-or-incident"],
    }
    record.update(kw)
    return record


class TestValidateProcess(unittest.TestCase):
    def test_a_complete_definition_normalises(self):
        norm = validate_process(process())
        self.assertEqual(norm["analysis_levels"], ["functional", "system"])
        self.assertEqual(len(norm["declared_elements"]), len(PROCESS_ELEMENTS))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_process("a hazard analysis process")

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(""))

    def test_declaring_no_analysis_level_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(analysis_levels=[]))

    def test_an_unknown_analysis_level_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(analysis_levels=["vibes"]))

    def test_an_unknown_process_element_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(declared_elements=["a-weekly-meeting"]))

    def test_an_unknown_technique_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(techniques_by_level={
                "system": ["having-a-think"]}))

    def test_a_non_mapping_technique_table_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(techniques_by_level=["fault-tree-analysis"]))

    def test_an_unknown_review_milestone_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(iteration_reviews=["kickoff"]))

    def test_a_repeated_documentation_item_raises(self):
        with self.assertRaises(ValueError):
            validate_process(process(documentation_set=["hazard-log", "hazard-log"]))

    def test_tokens_are_case_folded(self):
        norm = validate_process(process(analysis_levels=["FUNCTIONAL", "System"]))
        self.assertEqual(norm["analysis_levels"], ["functional", "system"])


class TestMissingElements(unittest.TestCase):
    def test_a_complete_definition_is_missing_nothing(self):
        self.assertEqual(missing_elements(process()), [])

    def test_an_omitted_element_is_named(self):
        elements = [e for e in PROCESS_ELEMENTS if e != "input-data-set"]
        self.assertEqual(missing_elements(process(declared_elements=elements)),
                         ["input-data-set"])

    def test_the_element_score_of_a_complete_definition_is_one(self):
        self.assertAlmostEqual(element_score(process()), 1.0, places=9)

    def test_the_element_score_falls_with_each_omission(self):
        elements = list(PROCESS_ELEMENTS)[:4]
        self.assertAlmostEqual(element_score(process(declared_elements=elements)),
                               0.5, places=9)


class TestTechniques(unittest.TestCase):
    def test_suited_techniques_produce_no_finding(self):
        self.assertEqual(technique_findings(process()), [])

    def test_a_level_with_no_technique_is_a_finding(self):
        found = technique_findings(process(techniques_by_level={
            "functional": ["functional-hazard-analysis"]}))
        self.assertTrue(any("no technique selected" in f for f in found))

    def test_a_technique_from_another_level_is_a_finding(self):
        found = technique_findings(process(techniques_by_level={
            "functional": ["fault-tree-analysis"],
            "system": ["fault-tree-analysis"]}))
        self.assertTrue(any("different level" in f for f in found))

    def test_a_technique_shared_by_two_levels_suits_both(self):
        found = technique_findings(process(
            analysis_levels=["system", "subsystem"],
            techniques_by_level={
                "system": ["failure-modes-effects-and-criticality-analysis"],
                "subsystem": ["failure-modes-effects-and-criticality-analysis"]}))
        self.assertEqual(found, [])

    def test_techniques_for_an_undeclared_level_are_a_finding(self):
        found = technique_findings(process(techniques_by_level={
            "functional": ["functional-hazard-analysis"],
            "system": ["fault-tree-analysis"],
            "operational": ["task-analysis"]}))
        self.assertTrue(any("does not declare" in f for f in found))

    def test_the_operational_level_carries_its_own_techniques(self):
        found = technique_findings(process(
            analysis_levels=["operational"],
            iteration_reviews=["pdr", "cdr", "ar"],
            techniques_by_level={
                "operational": ["operating-and-support-hazard-analysis"]}))
        self.assertEqual(found, [])


class TestReviewIntegration(unittest.TestCase):
    def test_iterations_at_the_mandatory_reviews_produce_no_finding(self):
        self.assertEqual(review_integration_findings(process()), [])

    def test_a_missing_mandatory_review_is_a_finding(self):
        found = review_integration_findings(process(iteration_reviews=["cdr", "qr"]))
        self.assertTrue(any("pdr" in f for f in found))

    def test_a_single_iteration_is_not_an_iterative_process(self):
        found = review_integration_findings(process(iteration_reviews=["cdr"]))
        self.assertTrue(any("one-off" in f for f in found))

    def test_operational_analysis_wants_an_iteration_at_acceptance(self):
        found = review_integration_findings(process(
            analysis_levels=["functional", "operational"],
            techniques_by_level={"functional": ["functional-hazard-analysis"],
                                 "operational": ["task-analysis"]}))
        self.assertTrue(any("operational baseline" in f for f in found))

    def test_operational_analysis_with_an_acceptance_iteration_is_clean(self):
        found = review_integration_findings(process(
            analysis_levels=["functional", "operational"],
            iteration_reviews=["pdr", "cdr", "ar"],
            techniques_by_level={"functional": ["functional-hazard-analysis"],
                                 "operational": ["task-analysis"]}))
        self.assertEqual(found, [])


class TestDocumentation(unittest.TestCase):
    def test_a_complete_documentation_set_produces_no_finding(self):
        self.assertEqual(documentation_findings(process()), [])

    def test_a_missing_hazard_log_is_a_finding(self):
        found = documentation_findings(process(documentation_set=[
            "hazard-analysis-report", "traceability-to-requirements"]))
        self.assertTrue(any("hazard log" in f for f in found))

    def test_a_hazard_log_without_traceability_is_called_out_twice(self):
        found = documentation_findings(process(documentation_set=[
            "hazard-analysis-report", "hazard-log"]))
        self.assertEqual(len(found), 2)

    def test_an_optional_item_is_not_demanded(self):
        found = documentation_findings(process(documentation_set=[
            "hazard-analysis-report", "hazard-log", "traceability-to-requirements",
            "assumption-register"]))
        self.assertEqual(found, [])


class TestUpdateTriggers(unittest.TestCase):
    def test_the_mandatory_triggers_produce_no_finding(self):
        self.assertEqual(update_trigger_findings(process()), [])

    def test_a_missing_design_change_trigger_is_a_finding(self):
        found = update_trigger_findings(process(update_triggers=["anomaly-or-incident"]))
        self.assertTrue(any("design change" in f for f in found))

    def test_operational_analysis_wants_an_operational_change_trigger(self):
        found = update_trigger_findings(process(
            analysis_levels=["functional", "operational"],
            techniques_by_level={"functional": ["functional-hazard-analysis"],
                                 "operational": ["task-analysis"]}))
        self.assertTrue(any("operational change" in f for f in found))


class TestAssessProcess(unittest.TestCase):
    def test_a_complete_definition_is_conformant(self):
        report = assess_process_definition(process())
        self.assertEqual(report["grade"], "process-conformant")
        self.assertTrue(report["conformant"])
        self.assertEqual(report["findings"], [])

    def test_a_missing_element_is_non_conformant(self):
        elements = [e for e in PROCESS_ELEMENTS if e != "iteration-points"]
        report = assess_process_definition(process(declared_elements=elements))
        self.assertEqual(report["grade"], "process-non-conformant")

    def test_an_unsuited_technique_is_non_conformant(self):
        report = assess_process_definition(process(techniques_by_level={
            "functional": ["fault-tree-analysis"],
            "system": ["fault-tree-analysis"]}))
        self.assertEqual(report["grade"], "process-non-conformant")

    def test_a_review_gap_alone_is_only_a_gap(self):
        report = assess_process_definition(process(iteration_reviews=["cdr", "qr"]))
        self.assertEqual(report["grade"], "process-conformant-with-gaps")
        self.assertFalse(report["conformant"])

    def test_a_trigger_gap_alone_is_only_a_gap(self):
        report = assess_process_definition(process(
            update_triggers=["design-change", "periodic-review"]))
        self.assertEqual(report["grade"], "process-conformant-with-gaps")

    def test_a_documentation_gap_is_non_conformant(self):
        report = assess_process_definition(process(documentation_set=[
            "hazard-analysis-report"]))
        self.assertEqual(report["grade"], "process-non-conformant")

    def test_the_element_score_is_reported_back(self):
        report = assess_process_definition(process())
        self.assertAlmostEqual(report["element_score"], 1.0, places=9)

    def test_findings_from_every_check_reach_the_report(self):
        report = assess_process_definition(process(
            declared_elements=list(PROCESS_ELEMENTS)[:6],
            iteration_reviews=["cdr"],
            documentation_set=["hazard-analysis-report"],
            update_triggers=[]))
        self.assertTrue(report["missing_elements"])
        self.assertTrue(report["review_findings"])
        self.assertTrue(report["documentation_findings"])
        self.assertTrue(report["update_trigger_findings"])
        self.assertGreater(len(report["findings"]), 6)


if __name__ == "__main__":
    unittest.main()

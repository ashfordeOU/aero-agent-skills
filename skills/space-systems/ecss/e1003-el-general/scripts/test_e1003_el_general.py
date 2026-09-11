import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_general_logic import (
    TestRecord,
    validate_test_sequence,
    check_interface_coverage,
    check_functional_coverage,
    categorize_test_by_level,
    check_required_levels_present,
    assess_element_test_compliance,
    TEST_LEVEL_ORDER,
    ELEMENT_REQUIRED_LEVELS,
)


class TestTestRecordCreation(unittest.TestCase):

    def test_valid_record_all_fields(self):
        r = TestRecord(
            "T-001", "unit",
            interfaces=["IF-A"], functions=["F1"],
            status="pass", sequence_position=1,
        )
        self.assertEqual(r.test_id, "T-001")
        self.assertEqual(r.level, "unit")
        self.assertEqual(r.interfaces, ["IF-A"])
        self.assertEqual(r.functions, ["F1"])
        self.assertEqual(r.status, "pass")
        self.assertEqual(r.sequence_position, 1)

    def test_default_fields_are_safe(self):
        r = TestRecord("T-002", "element")
        self.assertEqual(r.interfaces, [])
        self.assertEqual(r.functions, [])
        self.assertEqual(r.status, "pending")
        self.assertIsNone(r.sequence_position)

    def test_empty_test_id_raises(self):
        with self.assertRaises(ValueError):
            TestRecord("", "unit")

    def test_none_test_id_raises(self):
        with self.assertRaises(ValueError):
            TestRecord(None, "unit")

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            TestRecord("T-003", "prototype")

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            TestRecord("T-004", "unit", status="done")

    def test_all_valid_levels_accepted(self):
        for level in TEST_LEVEL_ORDER:
            r = TestRecord("T-X", level)
            self.assertEqual(r.level, level)

    def test_interfaces_list_is_copy(self):
        src = ["IF-A"]
        r = TestRecord("T-005", "unit", interfaces=src)
        src.append("IF-B")
        self.assertEqual(r.interfaces, ["IF-A"])


class TestSequenceValidation(unittest.TestCase):

    def test_valid_ascending_sequence(self):
        records = [
            TestRecord("T-U1", "unit", status="pass", sequence_position=1),
            TestRecord("T-I1", "integration", status="pass", sequence_position=2),
            TestRecord("T-E1", "element", status="pass", sequence_position=3),
        ]
        ok, violations = validate_test_sequence(records)
        self.assertTrue(ok)
        self.assertEqual(violations, [])

    def test_element_before_unit_is_violation(self):
        records = [
            TestRecord("T-E1", "element", status="pass", sequence_position=1),
            TestRecord("T-U1", "unit", status="pass", sequence_position=2),
        ]
        ok, violations = validate_test_sequence(records)
        self.assertFalse(ok)
        self.assertTrue(any("T-U1" in v for v in violations))

    def test_integration_before_unit_is_violation(self):
        records = [
            TestRecord("T-I1", "integration", status="pass", sequence_position=1),
            TestRecord("T-U1", "unit", status="pass", sequence_position=2),
        ]
        ok, violations = validate_test_sequence(records)
        self.assertFalse(ok)
        self.assertEqual(len(violations), 1)

    def test_records_without_position_excluded_from_check(self):
        records = [
            TestRecord("T-E1", "element", status="pass"),
            TestRecord("T-U1", "unit", status="pass"),
        ]
        ok, violations = validate_test_sequence(records)
        self.assertTrue(ok)
        self.assertEqual(violations, [])

    def test_same_level_multiple_tests_no_violation(self):
        records = [
            TestRecord("T-U1", "unit", status="pass", sequence_position=1),
            TestRecord("T-U2", "unit", status="pass", sequence_position=2),
            TestRecord("T-I1", "integration", status="pass", sequence_position=3),
        ]
        ok, violations = validate_test_sequence(records)
        self.assertTrue(ok)


class TestInterfaceCoverage(unittest.TestCase):

    def test_all_interfaces_covered_by_passing_tests(self):
        records = [
            TestRecord("T-1", "element", interfaces=["IF-A", "IF-B"], status="pass"),
            TestRecord("T-2", "element", interfaces=["IF-C"], status="pass"),
        ]
        ok, uncovered = check_interface_coverage(records, ["IF-A", "IF-B", "IF-C"])
        self.assertTrue(ok)
        self.assertEqual(uncovered, [])

    def test_missing_interface_flagged(self):
        records = [
            TestRecord("T-1", "element", interfaces=["IF-A"], status="pass"),
        ]
        ok, uncovered = check_interface_coverage(records, ["IF-A", "IF-B"])
        self.assertFalse(ok)
        self.assertIn("IF-B", uncovered)

    def test_pending_test_does_not_cover_interface(self):
        records = [
            TestRecord("T-1", "element", interfaces=["IF-X"], status="pending"),
        ]
        ok, uncovered = check_interface_coverage(records, ["IF-X"])
        self.assertFalse(ok)
        self.assertIn("IF-X", uncovered)

    def test_failing_test_does_not_cover_interface(self):
        records = [
            TestRecord("T-1", "element", interfaces=["IF-Y"], status="fail"),
        ]
        ok, uncovered = check_interface_coverage(records, ["IF-Y"])
        self.assertFalse(ok)
        self.assertIn("IF-Y", uncovered)

    def test_empty_required_interfaces_is_ok(self):
        records = [TestRecord("T-1", "unit", status="pass")]
        ok, uncovered = check_interface_coverage(records, [])
        self.assertTrue(ok)
        self.assertEqual(uncovered, [])


class TestFunctionalCoverage(unittest.TestCase):

    def test_all_functions_covered(self):
        records = [
            TestRecord("T-1", "unit", functions=["F1", "F2"], status="pass"),
            TestRecord("T-2", "unit", functions=["F3"], status="pass"),
        ]
        ok, uncovered = check_functional_coverage(records, ["F1", "F2", "F3"])
        self.assertTrue(ok)
        self.assertEqual(uncovered, [])

    def test_missing_function_flagged(self):
        records = [
            TestRecord("T-1", "unit", functions=["F1"], status="pass"),
        ]
        ok, uncovered = check_functional_coverage(records, ["F1", "F2"])
        self.assertFalse(ok)
        self.assertIn("F2", uncovered)

    def test_failing_test_does_not_count_as_function_coverage(self):
        records = [
            TestRecord("T-1", "unit", functions=["F4"], status="fail"),
        ]
        ok, uncovered = check_functional_coverage(records, ["F4"])
        self.assertFalse(ok)

    def test_not_run_test_does_not_count(self):
        records = [
            TestRecord("T-1", "unit", functions=["F5"], status="not_run"),
        ]
        ok, uncovered = check_functional_coverage(records, ["F5"])
        self.assertFalse(ok)


class TestCategorizeByLevel(unittest.TestCase):

    def test_unit_is_element_internal(self):
        r = TestRecord("T-1", "unit")
        self.assertEqual(categorize_test_by_level(r), "element-internal")

    def test_integration_is_element_internal(self):
        r = TestRecord("T-1", "integration")
        self.assertEqual(categorize_test_by_level(r), "element-internal")

    def test_element_is_element_boundary(self):
        r = TestRecord("T-1", "element")
        self.assertEqual(categorize_test_by_level(r), "element-boundary")

    def test_system_is_above_element(self):
        r = TestRecord("T-1", "system")
        self.assertEqual(categorize_test_by_level(r), "above-element")


class TestRequiredLevelsPresent(unittest.TestCase):

    def test_all_required_levels_present(self):
        records = [
            TestRecord("T-1", "unit", status="pass"),
            TestRecord("T-2", "integration", status="pass"),
            TestRecord("T-3", "element", status="pass"),
        ]
        ok, missing = check_required_levels_present(records)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_missing_element_level(self):
        records = [
            TestRecord("T-1", "unit", status="pass"),
            TestRecord("T-2", "integration", status="pass"),
        ]
        ok, missing = check_required_levels_present(records)
        self.assertFalse(ok)
        self.assertIn("element", missing)

    def test_missing_unit_level(self):
        records = [
            TestRecord("T-1", "integration", status="pass"),
            TestRecord("T-2", "element", status="pass"),
        ]
        ok, missing = check_required_levels_present(records)
        self.assertFalse(ok)
        self.assertIn("unit", missing)

    def test_failing_tests_do_not_satisfy_level_requirement(self):
        records = [
            TestRecord("T-1", "unit", status="fail"),
            TestRecord("T-2", "integration", status="pass"),
            TestRecord("T-3", "element", status="pass"),
        ]
        ok, missing = check_required_levels_present(records)
        self.assertFalse(ok)
        self.assertIn("unit", missing)

    def test_system_level_alone_does_not_satisfy_required_levels(self):
        records = [
            TestRecord("T-1", "system", status="pass"),
        ]
        ok, missing = check_required_levels_present(records)
        self.assertFalse(ok)
        self.assertEqual(set(missing), ELEMENT_REQUIRED_LEVELS)


class TestFullAssessment(unittest.TestCase):

    def _compliant_records(self):
        return [
            TestRecord(
                "T-U1", "unit",
                interfaces=["IF-A"], functions=["F1"],
                status="pass", sequence_position=1,
            ),
            TestRecord(
                "T-I1", "integration",
                interfaces=["IF-B"], functions=["F2"],
                status="pass", sequence_position=2,
            ),
            TestRecord(
                "T-E1", "element",
                interfaces=["IF-A", "IF-B"], functions=["F1", "F2"],
                status="pass", sequence_position=3,
            ),
        ]

    def test_fully_compliant_campaign(self):
        result = assess_element_test_compliance(
            self._compliant_records(), ["IF-A", "IF-B"], ["F1", "F2"]
        )
        self.assertTrue(result["compliant"])
        self.assertTrue(result["sequence_ok"])
        self.assertTrue(result["interface_ok"])
        self.assertTrue(result["functional_ok"])
        self.assertTrue(result["levels_ok"])
        self.assertEqual(result["sequence_violations"], [])
        self.assertEqual(result["uncovered_interfaces"], [])
        self.assertEqual(result["uncovered_functions"], [])
        self.assertEqual(result["missing_levels"], [])

    def test_non_compliant_missing_interface(self):
        result = assess_element_test_compliance(
            self._compliant_records(), ["IF-A", "IF-B", "IF-C"], ["F1", "F2"]
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["interface_ok"])
        self.assertIn("IF-C", result["uncovered_interfaces"])

    def test_non_compliant_missing_function(self):
        result = assess_element_test_compliance(
            self._compliant_records(), ["IF-A", "IF-B"], ["F1", "F2", "F3"]
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["functional_ok"])
        self.assertIn("F3", result["uncovered_functions"])

    def test_non_compliant_sequence_violation(self):
        records = [
            TestRecord("T-E1", "element", interfaces=["IF-A"], functions=["F1"],
                       status="pass", sequence_position=1),
            TestRecord("T-U1", "unit", interfaces=["IF-A"], functions=["F1"],
                       status="pass", sequence_position=2),
            TestRecord("T-I1", "integration", interfaces=["IF-A"], functions=["F1"],
                       status="pass", sequence_position=3),
        ]
        result = assess_element_test_compliance(records, ["IF-A"], ["F1"])
        self.assertFalse(result["compliant"])
        self.assertFalse(result["sequence_ok"])
        self.assertGreater(len(result["sequence_violations"]), 0)

    def test_non_compliant_missing_required_level(self):
        records = [
            TestRecord("T-U1", "unit", interfaces=["IF-A"], functions=["F1"],
                       status="pass", sequence_position=1),
            TestRecord("T-I1", "integration", interfaces=["IF-A"], functions=["F1"],
                       status="pass", sequence_position=2),
        ]
        result = assess_element_test_compliance(records, ["IF-A"], ["F1"])
        self.assertFalse(result["compliant"])
        self.assertFalse(result["levels_ok"])
        self.assertIn("element", result["missing_levels"])


if __name__ == "__main__":
    unittest.main()

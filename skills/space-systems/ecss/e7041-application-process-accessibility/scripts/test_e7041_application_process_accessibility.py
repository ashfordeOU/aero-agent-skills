"""Contract test for the application-process-accessibility leaf (stdlib unittest)."""

import unittest

from e7041_application_process_accessibility_logic import (
    APID_IDLE,
    APID_MAX,
    accessibility_census,
    assess_application_process_accessibility,
    categorize_identifier,
    is_accessible,
    partition_requests,
    reachable_processes,
    stale_declarations,
    validate_application_process_id,
    validate_declaration,
    validate_defined_processes,
)


def declaration(service_id="TS-1", accessible=(10, 11, 12)):
    return {
        "test_service_id": service_id,
        "accessible_application_process_ids": list(accessible),
    }


DEFINED = [10, 11, 12, 13, 14]


class TestIdentifierValidation(unittest.TestCase):
    def test_top_identifier_is_accepted(self):
        self.assertEqual(validate_application_process_id(APID_MAX), APID_MAX)

    def test_idle_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(APID_IDLE)

    def test_out_of_range_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(5000)

    def test_negative_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(-1)

    def test_boolean_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(True)

    def test_categorize_reports_idle_without_raising(self):
        usable, reason = categorize_identifier(APID_IDLE)
        self.assertFalse(usable)
        self.assertEqual(reason, "reserved-idle-identifier")

    def test_categorize_reports_out_of_range_without_raising(self):
        usable, reason = categorize_identifier(9000)
        self.assertFalse(usable)
        self.assertEqual(reason, "identifier-out-of-range")

    def test_categorize_still_raises_on_a_non_integer(self):
        with self.assertRaises(ValueError):
            categorize_identifier("10")


class TestDeclarationValidation(unittest.TestCase):
    def test_declaration_is_sorted(self):
        norm = validate_declaration(declaration(accessible=(12, 10, 11)))
        self.assertEqual(norm["accessible_application_process_ids"], [10, 11, 12])

    def test_empty_service_id_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(service_id="  "))

    def test_duplicate_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(accessible=(10, 10)))

    def test_idle_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(accessible=(10, APID_IDLE)))

    def test_non_sequence_entries_raise(self):
        with self.assertRaises(ValueError):
            validate_declaration({"test_service_id": "TS-1",
                                  "accessible_application_process_ids": 10})

    def test_empty_declaration_is_allowed(self):
        norm = validate_declaration(declaration(accessible=()))
        self.assertEqual(norm["accessible_application_process_ids"], [])

    def test_duplicate_defined_process_raises(self):
        with self.assertRaises(ValueError):
            validate_defined_processes([10, 10])

    def test_empty_defined_set_raises(self):
        with self.assertRaises(ValueError):
            validate_defined_processes([])


class TestAccessibilityDecisions(unittest.TestCase):
    def test_declared_process_is_accessible(self):
        self.assertTrue(is_accessible(declaration(), 10))

    def test_defined_but_undeclared_process_is_not_accessible(self):
        self.assertFalse(is_accessible(declaration(), 13))

    def test_idle_identifier_is_never_accessible(self):
        self.assertFalse(is_accessible(declaration(), APID_IDLE))

    def test_two_services_can_declare_different_reach(self):
        self.assertTrue(is_accessible(declaration("TS-2", (13,)), 13))
        self.assertFalse(is_accessible(declaration("TS-1", (10,)), 13))


class TestStaleDeclarations(unittest.TestCase):
    def test_declaration_matching_the_defined_set_is_clean(self):
        self.assertEqual(stale_declarations(declaration(), DEFINED), [])

    def test_undefined_entry_is_stale(self):
        self.assertEqual(
            stale_declarations(declaration(accessible=(10, 99)), DEFINED), [99]
        )

    def test_reachable_set_excludes_the_stale_entry(self):
        self.assertEqual(
            reachable_processes(declaration(accessible=(10, 99)), DEFINED), [10]
        )


class TestPartitionAndCensus(unittest.TestCase):
    def test_requests_split_by_reason(self):
        partition = partition_requests(declaration(), [10, 13, APID_IDLE, 9000])
        self.assertEqual(partition["accessible"], [10])
        self.assertEqual(
            [r["reason"] for r in partition["refused"]],
            ["not-declared-accessible", "reserved-idle-identifier",
             "identifier-out-of-range"],
        )

    def test_refusal_names_the_service_it_came_from(self):
        partition = partition_requests(declaration("TS-7"), [13])
        self.assertEqual(partition["refused"][0]["test_service_id"], "TS-7")

    def test_non_sequence_requests_raise(self):
        with self.assertRaises(ValueError):
            partition_requests(declaration(), 10)

    def test_coverage_is_the_reachable_fraction(self):
        census = accessibility_census(declaration(), DEFINED)
        self.assertEqual(census["reachable_count"], 3)
        self.assertEqual(census["defined_count"], 5)
        self.assertAlmostEqual(census["coverage"], 0.6, places=9)
        self.assertEqual(census["unreachable_application_process_ids"], [13, 14])

    def test_full_coverage(self):
        census = accessibility_census(declaration(accessible=DEFINED), DEFINED)
        self.assertAlmostEqual(census["coverage"], 1.0, places=9)
        self.assertEqual(census["unreachable_application_process_ids"], [])

    def test_a_stale_entry_does_not_raise_coverage(self):
        with_stale = accessibility_census(
            declaration(accessible=list(DEFINED) + [99]), DEFINED
        )
        self.assertAlmostEqual(with_stale["coverage"], 1.0, places=9)
        self.assertEqual(with_stale["reachable_count"], 5)


class TestAssessment(unittest.TestCase):
    def test_full_reach_with_no_requests_is_clean(self):
        report = assess_application_process_accessibility(
            {
                "declaration": declaration(accessible=DEFINED),
                "defined_application_process_ids": DEFINED,
            }
        )
        self.assertTrue(report["clean"])
        self.assertEqual(report["findings"], [])

    def test_partial_reach_raises_a_sweep_finding(self):
        report = assess_application_process_accessibility(
            {
                "declaration": declaration(),
                "defined_application_process_ids": DEFINED,
            }
        )
        self.assertFalse(report["clean"])
        self.assertIn("untouched", report["findings"][-1])

    def test_stale_entry_and_refusal_both_reach_the_findings(self):
        report = assess_application_process_accessibility(
            {
                "declaration": declaration(accessible=(10, 99)),
                "defined_application_process_ids": DEFINED,
                "requested": [13],
            }
        )
        self.assertEqual(report["stale_declarations"], [99])
        self.assertTrue(any("stale" in f for f in report["findings"]))
        self.assertTrue(any("refused" in f for f in report["findings"]))

    def test_refusal_finding_says_nothing_was_learned(self):
        report = assess_application_process_accessibility(
            {
                "declaration": declaration(),
                "defined_application_process_ids": DEFINED,
                "requested": [14],
            }
        )
        self.assertTrue(any("nothing was learned" in f for f in report["findings"]))

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_application_process_accessibility({"declaration": declaration()})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_application_process_accessibility([declaration()])


if __name__ == "__main__":
    unittest.main()

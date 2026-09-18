"""Contract tests for the clause 5.2.1.3 communication engineering output logic."""

import unittest

from e50_outputs_logic import (
    COMPLETE,
    INCOMPLETE,
    assess_completeness,
    audit_outputs,
    find_duplicate_output_names,
    find_unidentified_outputs,
    find_untraced_outputs,
    normalize_output,
    validate_output_set,
)

REQUIRED = ["communication architecture", "layer allocation", "link budget"]

ACTIVITIES = [
    "define communication architecture",
    "allocate functions to protocol layers",
    "size the links",
]

DECLARED = [
    {
        "name": "communication architecture",
        "identifier": "COM-ARCH-001",
        "produced_by": "define communication architecture",
    },
    {
        "name": "layer allocation",
        "identifier": "COM-LAY-002",
        "produced_by": "allocate functions to protocol layers",
    },
    {
        "name": "link budget",
        "identifier": "COM-LNK-003",
        "produced_by": "size the links",
    },
]


class NormalizeTests(unittest.TestCase):
    def test_valid_output_normalized(self):
        output = normalize_output(dict(DECLARED[0], name="  link budget  "))
        self.assertEqual(output["name"], "link budget")

    def test_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_output({"identifier": "X"})

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_output({"name": "   "})

    def test_absent_identifier_becomes_none(self):
        self.assertIsNone(normalize_output({"name": "a"})["identifier"])

    def test_blank_identifier_becomes_none(self):
        self.assertIsNone(normalize_output({"name": "a", "identifier": "  "})["identifier"])

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_output({"name": "a", "identifier": 7})

    def test_non_string_producer_rejected(self):
        with self.assertRaises(ValueError):
            normalize_output({"name": "a", "produced_by": ["b"]})

    def test_non_mapping_output_rejected(self):
        with self.assertRaises(ValueError):
            normalize_output("link budget")


class OutputSetTests(unittest.TestCase):
    def test_valid_set_accepted(self):
        self.assertEqual(len(validate_output_set(DECLARED)), 3)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_output_set([])

    def test_mapping_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_output_set({"name": "a"})


class CompletenessTests(unittest.TestCase):
    def test_full_set_is_complete(self):
        result = assess_completeness(REQUIRED, DECLARED)
        self.assertAlmostEqual(result["completion_fraction"], 1.0, places=9)
        self.assertEqual(result["missing"], [])

    def test_missing_output_is_named(self):
        result = assess_completeness(REQUIRED, DECLARED[:2])
        self.assertEqual(result["missing"], ["link budget"])

    def test_partial_completion_is_a_fraction_not_a_yes(self):
        result = assess_completeness(REQUIRED, DECLARED[:1])
        self.assertAlmostEqual(result["completion_fraction"], 1.0 / 3.0, places=9)

    def test_undeclared_output_is_listed_separately(self):
        declared = DECLARED + [{"name": "meeting minutes", "identifier": "M-1", "produced_by": "size the links"}]
        self.assertEqual(assess_completeness(REQUIRED, declared)["undeclared"], ["meeting minutes"])

    def test_undeclared_output_does_not_inflate_completion(self):
        declared = DECLARED[:1] + [{"name": "meeting minutes", "identifier": "M-1"}]
        result = assess_completeness(REQUIRED, declared)
        self.assertAlmostEqual(result["completion_fraction"], 1.0 / 3.0, places=9)

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_completeness([], DECLARED)


class IdentifierTests(unittest.TestCase):
    def test_identified_set_has_no_findings(self):
        self.assertEqual(find_unidentified_outputs(DECLARED), [])

    def test_unidentified_output_is_flagged(self):
        declared = [dict(DECLARED[0], identifier=None)]
        findings = find_unidentified_outputs(declared)
        self.assertTrue(any("no identifier" in f for f in findings))

    def test_each_unidentified_output_gets_its_own_finding(self):
        declared = [dict(item, identifier=None) for item in DECLARED]
        self.assertEqual(len(find_unidentified_outputs(declared)), 3)


class TraceTests(unittest.TestCase):
    def test_traced_set_has_no_findings(self):
        self.assertEqual(find_untraced_outputs(DECLARED, ACTIVITIES), [])

    def test_output_with_no_producer_is_flagged(self):
        declared = [dict(DECLARED[0], produced_by=None)]
        findings = find_untraced_outputs(declared, ACTIVITIES)
        self.assertTrue(any("asserted rather than produced" in f for f in findings))

    def test_output_from_a_foreign_activity_is_flagged(self):
        declared = [dict(DECLARED[0], produced_by="procure the transponder")]
        findings = find_untraced_outputs(declared, ACTIVITIES)
        self.assertTrue(any("not an activity of this step" in f for f in findings))

    def test_activity_list_must_be_a_list(self):
        with self.assertRaises(ValueError):
            find_untraced_outputs(DECLARED, "size the links")


class DuplicateTests(unittest.TestCase):
    def test_unique_set_has_no_duplicates(self):
        self.assertEqual(find_duplicate_output_names(DECLARED), [])

    def test_repeated_name_is_flagged_once_with_its_count(self):
        declared = DECLARED + [dict(DECLARED[0], identifier="COM-ARCH-001-B")]
        findings = find_duplicate_output_names(declared)
        self.assertEqual(len(findings), 1)
        self.assertIn("2 times", findings[0])


class AuditTests(unittest.TestCase):
    def test_clean_step_is_complete(self):
        result = audit_outputs(REQUIRED, DECLARED, ACTIVITIES)
        self.assertEqual(result["verdict"], COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_missing_output_makes_the_step_incomplete(self):
        result = audit_outputs(REQUIRED, DECLARED[:2], ACTIVITIES)
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertIn("link budget", result["findings"][0])

    def test_full_coverage_with_no_identifiers_still_fails(self):
        declared = [dict(item, identifier=None) for item in DECLARED]
        result = audit_outputs(REQUIRED, declared, ACTIVITIES)
        self.assertAlmostEqual(result["completion_fraction"], 1.0, places=9)
        self.assertEqual(result["verdict"], INCOMPLETE)

    def test_full_coverage_with_an_untraced_output_still_fails(self):
        declared = [dict(DECLARED[0], produced_by=None)] + DECLARED[1:]
        result = audit_outputs(REQUIRED, declared, ACTIVITIES)
        self.assertTrue(result["untraced"])
        self.assertEqual(result["verdict"], INCOMPLETE)

    def test_findings_aggregate_every_category(self):
        declared = [{"name": "communication architecture"}, {"name": "communication architecture"}]
        result = audit_outputs(REQUIRED, declared, ACTIVITIES)
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract test for the detail specification review item (offline)."""

import copy
import unittest

from q6012_detail_specification_review_item_logic import (
    REQUIRED_SECTIONS,
    VERDICT_ACCEPTED,
    VERDICT_ACTIONED,
    VERDICT_REJECTED,
    absolute_maximum_findings,
    limit_ordering_findings,
    normalize_section_name,
    parameters_without_a_typical_value,
    review_detail_specification,
    section_report,
    validate_issue_record,
    validate_parameter,
)

SECTIONS = list(REQUIRED_SECTIONS)

RATINGS = {
    "drain-supply-voltage": 12.0,
    "channel-temperature": 175.0,
    "input-drive-power": 24.0,
}

PARAMETERS = [
    {
        "name": "small-signal-gain",
        "unit": "dB",
        "min": 18.0,
        "typ": 20.5,
        "max": 23.0,
        "conditions": {"temperature_c": 25.0, "frequency_ghz": 14.25},
    },
    {
        "name": "saturated-output-power",
        "unit": "dBm",
        "min": 33.0,
        "typ": 34.2,
        "conditions": {"temperature_c": 85.0, "frequency_ghz": 14.25},
    },
    {
        "name": "drain-bias-voltage",
        "unit": "V",
        "min": 9.5,
        "typ": 10.0,
        "max": 10.5,
        "conditions": {"temperature_c": 25.0, "frequency_ghz": 14.25},
        "governing_rating": "drain-supply-voltage",
    },
]

ISSUE = {
    "issue": "C",
    "issue_date": "2026-04-17",
    "approved_by": "product assurance manager",
    "is_first_issue": False,
    "change_record": "gain limit tightened after the qualification lot",
}


def _params(name, **changes):
    params = copy.deepcopy(PARAMETERS)
    for param in params:
        if param["name"] == name:
            param.update(changes)
            for key in [k for k, v in param.items() if v is None]:
                del param[key]
    return params


def _case(**overrides):
    case = {
        "present_sections": list(SECTIONS),
        "parameters": copy.deepcopy(PARAMETERS),
        "absolute_maximum_ratings": dict(RATINGS),
        "issue_record": copy.deepcopy(ISSUE),
    }
    case.update(overrides)
    return case


class SectionTests(unittest.TestCase):
    def test_section_name_is_canonicalised(self):
        self.assertEqual(
            normalize_section_name("  Absolute Maximum Ratings "),
            "absolute-maximum-ratings",
        )

    def test_underscored_section_name_is_canonicalised(self):
        self.assertEqual(
            normalize_section_name("marking_and_traceability"),
            "marking-and-traceability",
        )

    def test_a_complete_document_reports_no_missing_block(self):
        report = section_report(SECTIONS)
        self.assertTrue(report["complete"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["extra"], [])

    def test_a_dropped_block_is_reported(self):
        present = [s for s in SECTIONS if s != "storage-handling-and-esd"]
        report = section_report(present)
        self.assertEqual(report["missing"], ["storage-handling-and-esd"])
        self.assertFalse(report["complete"])

    def test_an_unexpected_block_is_reported_separately(self):
        report = section_report(SECTIONS + ["supplier-price-list"])
        self.assertEqual(report["extra"], ["supplier-price-list"])
        self.assertTrue(report["complete"])

    def test_a_block_listed_twice_rejected(self):
        with self.assertRaises(ValueError):
            section_report(SECTIONS + ["Storage Handling And Esd"])

    def test_a_blank_block_name_rejected(self):
        with self.assertRaises(ValueError):
            section_report(SECTIONS + ["  "])

    def test_a_non_list_of_blocks_rejected(self):
        with self.assertRaises(ValueError):
            section_report("identification-and-scope")


class ParameterValidationTests(unittest.TestCase):
    def test_a_complete_parameter_normalizes(self):
        entry = validate_parameter(PARAMETERS[0])
        self.assertEqual(entry["name"], "small-signal-gain")
        self.assertAlmostEqual(entry["min"], 18.0, places=9)
        self.assertAlmostEqual(entry["conditions"]["frequency_ghz"], 14.25, places=9)

    def test_a_one_sided_parameter_normalizes(self):
        entry = validate_parameter(PARAMETERS[1])
        self.assertIsNone(entry["max"])
        self.assertAlmostEqual(entry["min"], 33.0, places=9)

    def test_a_parameter_with_no_guaranteed_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {
                    "name": "noise-figure",
                    "unit": "dB",
                    "typ": 2.1,
                    "conditions": {"temperature_c": 25.0, "frequency_ghz": 14.25},
                }
            )

    def test_a_parameter_without_conditions_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {"name": "small-signal-gain", "unit": "dB", "min": 18.0}
            )

    def test_a_parameter_missing_a_required_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {
                    "name": "small-signal-gain",
                    "unit": "dB",
                    "min": 18.0,
                    "conditions": {"temperature_c": 25.0},
                }
            )

    def test_a_parameter_without_a_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {
                    "name": "small-signal-gain",
                    "min": 18.0,
                    "conditions": {"temperature_c": 25.0, "frequency_ghz": 14.25},
                }
            )

    def test_a_parameter_with_an_unknown_field_rejected(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["vendor_note"] = "best effort"
        with self.assertRaises(ValueError):
            validate_parameter(param)

    def test_a_non_numeric_condition_rejected(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["conditions"]["temperature_c"] = "ambient"
        with self.assertRaises(ValueError):
            validate_parameter(param)

    def test_an_extra_condition_is_carried_through(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["conditions"]["supply_v"] = 10.0
        entry = validate_parameter(param)
        self.assertAlmostEqual(entry["conditions"]["supply_v"], 10.0, places=9)


class LimitOrderingTests(unittest.TestCase):
    def test_a_well_ordered_parameter_has_no_finding(self):
        self.assertEqual(limit_ordering_findings(PARAMETERS[0]), [])

    def test_a_lower_limit_above_the_upper_limit_is_a_finding(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["min"], param["max"] = 23.0, 18.0
        param["typ"] = 20.5
        findings = limit_ordering_findings(param)
        self.assertTrue(any("above its upper limit" in f for f in findings))

    def test_a_typical_value_below_the_lower_limit_is_a_finding(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["typ"] = 17.0
        findings = limit_ordering_findings(param)
        self.assertTrue(any("below its lower limit" in f for f in findings))

    def test_a_typical_value_above_the_upper_limit_is_a_finding(self):
        param = copy.deepcopy(PARAMETERS[0])
        param["typ"] = 24.0
        findings = limit_ordering_findings(param)
        self.assertTrue(any("above its upper limit" in f for f in findings))

    def test_a_typical_value_sitting_exactly_on_a_limit_is_accepted(self):
        # 0.1 + 0.2 does not evaluate to exactly 0.3, so a strict comparison
        # would report a finding on a parameter that is correctly ordered.
        param = copy.deepcopy(PARAMETERS[0])
        param["min"], param["typ"], param["max"] = 0.1 + 0.2, 0.3, 0.3
        self.assertNotEqual(param["min"], param["max"])
        self.assertEqual(limit_ordering_findings(param), [])


class AbsoluteMaximumTests(unittest.TestCase):
    def test_a_limit_inside_its_rating_has_no_finding(self):
        self.assertEqual(absolute_maximum_findings(PARAMETERS, RATINGS), [])

    def test_a_limit_beyond_its_rating_is_a_finding(self):
        params = _params("drain-bias-voltage", max=12.5)
        findings = absolute_maximum_findings(params, RATINGS)
        self.assertTrue(any("absolute maximum" in f for f in findings))

    def test_a_limit_exactly_on_its_rating_is_accepted(self):
        params = _params("drain-bias-voltage", min=11.9, typ=12.0, max=12.0)
        self.assertEqual(absolute_maximum_findings(params, RATINGS), [])

    def test_a_rating_the_ratings_block_omits_is_a_finding(self):
        ratings = dict(RATINGS)
        del ratings["drain-supply-voltage"]
        findings = absolute_maximum_findings(PARAMETERS, ratings)
        self.assertTrue(any("does not state" in f for f in findings))

    def test_an_ungoverned_parameter_is_skipped(self):
        self.assertEqual(absolute_maximum_findings(PARAMETERS[:2], RATINGS), [])

    def test_a_non_numeric_rating_rejected(self):
        with self.assertRaises(ValueError):
            absolute_maximum_findings(PARAMETERS, {"drain-supply-voltage": "12 V"})

    def test_a_non_mapping_ratings_block_rejected(self):
        with self.assertRaises(ValueError):
            absolute_maximum_findings(PARAMETERS, [12.0])


class TypicalValueTests(unittest.TestCase):
    def test_the_reference_parameters_all_state_a_typical_value(self):
        self.assertEqual(parameters_without_a_typical_value(PARAMETERS), [])

    def test_a_bound_only_parameter_is_reported(self):
        params = _params("small-signal-gain", typ=None)
        self.assertEqual(
            parameters_without_a_typical_value(params), ["small-signal-gain"]
        )


class IssueControlTests(unittest.TestCase):
    def test_a_controlled_issue_record_passes(self):
        record = validate_issue_record(ISSUE)
        self.assertTrue(record["controlled"])
        self.assertEqual(record["issue_date"], "2026-04-17")

    def test_a_first_issue_owes_no_change_record(self):
        record = validate_issue_record(
            {
                "issue": "A",
                "issue_date": "2025-11-03",
                "approved_by": "product assurance manager",
                "is_first_issue": True,
            }
        )
        self.assertTrue(record["controlled"])

    def test_a_later_issue_without_a_change_record_is_uncontrolled(self):
        record = copy.deepcopy(ISSUE)
        del record["change_record"]
        result = validate_issue_record(record)
        self.assertFalse(result["controlled"])
        self.assertTrue(any("what changed" in f for f in result["findings"]))

    def test_an_unapproved_issue_rejected(self):
        record = copy.deepcopy(ISSUE)
        record["approved_by"] = "  "
        with self.assertRaises(ValueError):
            validate_issue_record(record)

    def test_a_malformed_issue_date_rejected(self):
        record = copy.deepcopy(ISSUE)
        record["issue_date"] = "17 April 2026"
        with self.assertRaises(ValueError):
            validate_issue_record(record)

    def test_a_non_mapping_issue_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_issue_record("issue C")


class ReviewTests(unittest.TestCase):
    def test_the_reference_document_is_accepted(self):
        result = review_detail_specification(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["parameter_count"], 3)

    def test_a_missing_block_rejects_the_document(self):
        present = [s for s in SECTIONS if s != "screening-and-qualification"]
        result = review_detail_specification(_case(present_sections=present))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any("screening-and-qualification" in f for f in result["findings"])
        )

    def test_a_limit_beyond_its_rating_rejects_the_document(self):
        result = review_detail_specification(
            _case(parameters=_params("drain-bias-voltage", max=12.5))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(result["absolute_maximum_findings"])

    def test_disordered_limits_reject_the_document(self):
        result = review_detail_specification(
            _case(parameters=_params("small-signal-gain", typ=24.0))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(result["ordering_findings"])

    def test_an_uncontrolled_issue_rejects_the_document(self):
        record = copy.deepcopy(ISSUE)
        del record["change_record"]
        result = review_detail_specification(_case(issue_record=record))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_a_bound_only_parameter_leaves_an_action(self):
        result = review_detail_specification(
            _case(parameters=_params("small-signal-gain", typ=None))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("expected value" in a for a in result["actions"]))

    def test_an_unexpected_block_leaves_an_action(self):
        result = review_detail_specification(
            _case(present_sections=SECTIONS + ["supplier-price-list"])
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("supplier-price-list" in a for a in result["actions"]))

    def test_a_document_with_no_parameter_rejected(self):
        with self.assertRaises(ValueError):
            review_detail_specification(_case(parameters=[]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_detail_specification("detail specification")

    def test_a_case_without_an_issue_record_rejected(self):
        case = _case()
        del case["issue_record"]
        with self.assertRaises(ValueError):
            review_detail_specification(case)


if __name__ == "__main__":
    unittest.main()

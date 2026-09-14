"""Contract tests for the clause 4.3.2 purchase-specification logic."""

import unittest

from q6013_class_1_procurement_specification_logic import (
    LIMIT_TOLERANCE,
    SAMPLING_MODES,
    assess_parameter,
    assess_part_entry,
    assess_purchase_specification,
    limit_tightening_findings,
    validate_header,
    validate_limit_pair,
    validate_parameter,
    validate_sampling_plan,
)

HEADER = {
    "identifier": "PS-6013-014",
    "issue": "issue 3",
    "approved_by": "component engineering authority",
}


def _parameter(**overrides):
    parameter = {
        "name": "supply current",
        "test_condition": "5 V, full temperature range",
        "minimum": 0.4,
        "maximum": 1.8,
        "datasheet_minimum": 0.3,
        "datasheet_maximum": 2.0,
    }
    parameter.update(overrides)
    return parameter


def _entry(part_number="XS-4417-QT", **overrides):
    entry = {
        "part_number": part_number,
        "parameters": [_parameter(), _parameter(name="propagation delay",
                                                minimum=None, maximum=12.0,
                                                datasheet_minimum=None,
                                                datasheet_maximum=15.0)],
        "sampling_plan": {"mode": "100-percent-screening"},
    }
    entry.update(overrides)
    return entry


def _spec(**overrides):
    spec = {
        "document": dict(HEADER),
        "ordered_part_numbers": ["XS-4417-QT"],
        "entries": [_entry()],
    }
    spec.update(overrides)
    return spec


class HeaderTests(unittest.TestCase):
    def test_header_returned_stripped(self):
        header = validate_header({"identifier": "  PS-6013-014 ", "issue": "issue 3",
                                  "approved_by": "component engineering authority"})
        self.assertEqual(header["identifier"], "PS-6013-014")

    def test_missing_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_header({"issue": "issue 3", "approved_by": "authority"})

    def test_blank_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(dict(HEADER, issue="  "))

    def test_missing_approval_rejected(self):
        bad = dict(HEADER)
        del bad["approved_by"]
        with self.assertRaises(ValueError):
            validate_header(bad)

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_header("PS-6013-014")


class LimitPairTests(unittest.TestCase):
    def test_two_sided_pair_returned_as_floats(self):
        self.assertEqual(validate_limit_pair(0.4, 1.8), (0.4, 1.8))

    def test_one_sided_upper_pair_allowed(self):
        self.assertEqual(validate_limit_pair(None, 12.0), (None, 12.0))

    def test_inverted_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair(2.0, 1.0)

    def test_equal_bounds_allowed(self):
        self.assertEqual(validate_limit_pair(5.0, 5.0), (5.0, 5.0))

    def test_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair("0.4", 1.8)

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair(True, 1.8)


class ParameterValidationTests(unittest.TestCase):
    def test_parameter_name_required(self):
        with self.assertRaises(ValueError):
            validate_parameter({"minimum": 0.4})

    def test_non_string_test_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_parameter(test_condition=5))

    def test_missing_test_condition_is_a_finding_not_an_error(self):
        record = assess_parameter(_parameter(test_condition=""))
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("test condition" in f for f in record["findings"]))

    def test_parameter_with_no_limit_is_a_finding(self):
        record = assess_parameter(
            {"name": "leakage", "test_condition": "125 C", "minimum": None,
             "maximum": None}
        )
        self.assertTrue(any("no acceptance limit" in f for f in record["findings"]))

    def test_tightened_parameter_is_acceptable(self):
        self.assertTrue(assess_parameter(_parameter())["acceptable"])


class TighteningTests(unittest.TestCase):
    def test_ordered_limits_equal_to_published_are_admissible(self):
        record = validate_parameter(_parameter(minimum=0.3, maximum=2.0))
        self.assertAlmostEqual(record["minimum"], record["datasheet_minimum"], places=9)
        self.assertAlmostEqual(record["maximum"], record["datasheet_maximum"], places=9)
        self.assertEqual(limit_tightening_findings(record), [])

    def test_loosened_lower_bound_is_a_finding(self):
        record = validate_parameter(_parameter(minimum=0.1))
        self.assertEqual(len(limit_tightening_findings(record)), 1)

    def test_loosened_upper_bound_is_a_finding(self):
        record = validate_parameter(_parameter(maximum=2.4))
        self.assertEqual(len(limit_tightening_findings(record)), 1)

    def test_both_bounds_loosened_gives_two_findings(self):
        record = validate_parameter(_parameter(minimum=0.1, maximum=2.4))
        self.assertEqual(len(limit_tightening_findings(record)), 2)

    def test_dropping_a_published_bound_is_a_finding(self):
        record = validate_parameter(_parameter(maximum=None))
        self.assertTrue(any("orders no upper bound" in f
                            for f in limit_tightening_findings(record)))

    def test_no_published_data_raises_no_tightening_finding(self):
        record = validate_parameter(
            _parameter(datasheet_minimum=None, datasheet_maximum=None)
        )
        self.assertEqual(limit_tightening_findings(record), [])

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


class SamplingPlanTests(unittest.TestCase):
    def test_full_screening_needs_no_sample_size(self):
        plan = validate_sampling_plan({"mode": "100 percent screening"})
        self.assertEqual(plan["mode"], "100-percent-screening")
        self.assertIsNone(plan["sample_size"])

    def test_lot_acceptance_plan_returned(self):
        plan = validate_sampling_plan(
            {"mode": "lot-acceptance-sampling", "sample_size": 22, "accept_on": 0}
        )
        self.assertEqual(plan["sample_size"], 22)
        self.assertEqual(plan["accept_on"], 0)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"mode": "whatever-arrives"})

    def test_lot_plan_without_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan({"mode": "lot-acceptance-sampling", "accept_on": 0})

    def test_accept_number_reaching_the_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(
                {"mode": "lot-acceptance-sampling", "sample_size": 5, "accept_on": 5}
            )

    def test_zero_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling_plan(
                {"mode": "lot-acceptance-sampling", "sample_size": 0, "accept_on": 0}
            )

    def test_both_modes_are_reachable(self):
        for mode in SAMPLING_MODES:
            plan = {"mode": mode}
            if mode == "lot-acceptance-sampling":
                plan.update({"sample_size": 10, "accept_on": 0})
            self.assertEqual(validate_sampling_plan(plan)["mode"], mode)


class PartEntryTests(unittest.TestCase):
    def test_clean_entry_is_acceptable(self):
        self.assertTrue(assess_part_entry(_entry())["acceptable"])

    def test_entry_with_no_parameters_is_a_finding(self):
        record = assess_part_entry(_entry(parameters=[]))
        self.assertFalse(record["acceptable"])

    def test_entry_with_no_acceptance_route_is_a_finding(self):
        record = assess_part_entry(_entry(sampling_plan=None))
        self.assertTrue(any("acceptance route" in f for f in record["findings"]))

    def test_repeated_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_entry(_entry(parameters=[_parameter(), _parameter()]))

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_entry(_entry(part_number="   "))

    def test_non_sequence_parameters_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_entry(_entry(parameters=_parameter()))


class SpecificationAssessmentTests(unittest.TestCase):
    def test_complete_specification_is_fit_to_order_against(self):
        result = assess_purchase_specification(_spec())
        self.assertTrue(result["fit_to_order_against"])
        self.assertEqual(result["findings"], [])

    def test_uncovered_ordered_part_is_a_finding(self):
        result = assess_purchase_specification(
            _spec(ordered_part_numbers=["XS-4417-QT", "XS-4419-QT"])
        )
        self.assertEqual(result["uncovered_part_numbers"], ["XS-4419-QT"])
        self.assertFalse(result["fit_to_order_against"])

    def test_entry_for_an_unordered_part_is_a_finding(self):
        result = assess_purchase_specification(
            _spec(entries=[_entry(), _entry(part_number="XS-9000-ZZ")])
        )
        self.assertEqual(result["unordered_entries"], ["XS-9000-ZZ"])

    def test_loosened_limit_reaches_the_specification_verdict(self):
        entry = _entry(parameters=[_parameter(maximum=2.4)])
        result = assess_purchase_specification(_spec(entries=[entry]))
        self.assertFalse(result["fit_to_order_against"])

    def test_duplicate_part_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(entries=[_entry(), _entry()]))

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(ordered_part_numbers=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_purchase_specification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(["document"])

    def test_uncontrolled_document_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(document=dict(HEADER, identifier="")))

    def test_every_finding_is_named_not_only_the_first(self):
        entry = _entry(parameters=[_parameter(minimum=0.1, maximum=2.4)],
                       sampling_plan=None)
        result = assess_purchase_specification(
            _spec(entries=[entry], ordered_part_numbers=["XS-4417-QT", "XS-4419-QT"])
        )
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()

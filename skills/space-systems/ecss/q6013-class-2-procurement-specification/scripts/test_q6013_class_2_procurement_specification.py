"""Contract tests for the clause 5.3.2 class 2 purchase-specification logic."""

import unittest

from q6013_class_2_procurement_specification_logic import (
    ACCEPTANCE_BASES,
    ACCEPTANCE_ROUTES,
    LIMIT_TOLERANCE,
    assess_parameter,
    assess_part_entry,
    assess_purchase_specification,
    limit_tightening_findings,
    published_basis_findings,
    temperature_range_findings,
    validate_acceptance_route,
    validate_citation,
    validate_header,
    validate_limit_pair,
    validate_parameter,
    validate_temperature_range,
)

HEADER = {
    "identifier": "PS-6013-207",
    "issue": "issue 4",
    "approved_by": "component engineering authority",
}


def _own_limit(**overrides):
    parameter = {
        "name": "quiescent current",
        "basis": "purchase-specification-limit",
        "test_condition": "3.3 V, 85 C",
        "minimum": 0.5,
        "maximum": 1.6,
        "published_minimum": 0.4,
        "published_maximum": 1.8,
    }
    parameter.update(overrides)
    return parameter


def _published(**overrides):
    parameter = {
        "name": "output rise time",
        "basis": "published-data-limit",
        "minimum": None,
        "maximum": 9.0,
        "published_minimum": None,
        "published_maximum": 9.0,
        "citation": {"document": "DS-4417 rev C", "issue": "issue 3"},
    }
    parameter.update(overrides)
    return parameter


def _entry(part_number="XM-8820-KT", **overrides):
    entry = {
        "part_number": part_number,
        "parameters": [_own_limit(), _published()],
        "ordered_temperature_range": {"low_c": -40.0, "high_c": 105.0},
        "published_temperature_range": {"low_c": -40.0, "high_c": 125.0},
        "acceptance_route": {"mode": "100-percent-screening"},
    }
    entry.update(overrides)
    return entry


def _spec(**overrides):
    spec = {
        "document": dict(HEADER),
        "ordered_part_numbers": ["XM-8820-KT"],
        "entries": [_entry()],
    }
    spec.update(overrides)
    return spec


class HeaderTests(unittest.TestCase):
    def test_header_returned_stripped(self):
        header = validate_header(dict(HEADER, identifier="  PS-6013-207 "))
        self.assertEqual(header["identifier"], "PS-6013-207")

    def test_missing_identifier_rejected(self):
        bad = dict(HEADER)
        del bad["identifier"]
        with self.assertRaises(ValueError):
            validate_header(bad)

    def test_blank_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(dict(HEADER, issue="   "))

    def test_missing_approval_rejected(self):
        bad = dict(HEADER)
        del bad["approved_by"]
        with self.assertRaises(ValueError):
            validate_header(bad)

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_header("PS-6013-207")


class CitationTests(unittest.TestCase):
    def test_citation_returned_stripped(self):
        citation = validate_citation({"document": " DS-4417 ", "issue": "issue 3"})
        self.assertEqual(citation["document"], "DS-4417")

    def test_citation_without_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_citation({"document": "DS-4417"})

    def test_citation_with_blank_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_citation({"document": "DS-4417", "issue": " "})


class LimitPairTests(unittest.TestCase):
    def test_two_sided_pair_returned(self):
        self.assertEqual(validate_limit_pair(0.5, 1.6), (0.5, 1.6))

    def test_one_sided_pair_allowed(self):
        self.assertEqual(validate_limit_pair(None, 9.0), (None, 9.0))

    def test_inverted_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair(2.0, 1.0)

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair(True, 1.6)

    def test_non_finite_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_pair(float("inf"), None)


class BasisTests(unittest.TestCase):
    def test_both_bases_are_reachable(self):
        for basis in ACCEPTANCE_BASES:
            parameter = _own_limit(basis=basis)
            if basis == "published-data-limit":
                parameter["citation"] = {"document": "DS-4417", "issue": "issue 3"}
            self.assertEqual(validate_parameter(parameter)["basis"], basis)

    def test_unrecognized_basis_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(_own_limit(basis="whatever the supplier sends"))

    def test_published_basis_without_a_citation_is_a_finding(self):
        record = validate_parameter(_published(citation=None))
        self.assertTrue(any("no citation" in f
                            for f in published_basis_findings(record)))

    def test_published_basis_fixing_no_limit_is_a_finding(self):
        record = validate_parameter(
            _published(minimum=None, maximum=None,
                       published_minimum=None, published_maximum=None)
        )
        self.assertTrue(any("fixes no limit" in f
                            for f in published_basis_findings(record)))

    def test_own_limit_basis_raises_no_published_finding(self):
        self.assertEqual(published_basis_findings(validate_parameter(_own_limit())), [])

    def test_own_limit_without_a_test_condition_is_a_finding(self):
        record = assess_parameter(_own_limit(test_condition=""))
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("test condition" in f for f in record["findings"]))

    def test_own_limit_without_any_limit_is_a_finding(self):
        record = assess_parameter(
            _own_limit(minimum=None, maximum=None,
                       published_minimum=None, published_maximum=None)
        )
        self.assertTrue(any("no acceptance limit" in f for f in record["findings"]))

    def test_published_basis_needs_no_test_condition_of_its_own(self):
        self.assertTrue(assess_parameter(_published())["acceptable"])


class TighteningTests(unittest.TestCase):
    def test_tightened_window_raises_nothing(self):
        self.assertEqual(limit_tightening_findings(validate_parameter(_own_limit())), [])

    def test_ordered_limits_equal_to_published_are_admissible(self):
        record = validate_parameter(_own_limit(minimum=0.4, maximum=1.8))
        self.assertAlmostEqual(record["minimum"], record["published_minimum"], places=9)
        self.assertAlmostEqual(record["maximum"], record["published_maximum"], places=9)
        self.assertEqual(limit_tightening_findings(record), [])

    def test_loosened_lower_bound_is_a_finding(self):
        record = validate_parameter(_own_limit(minimum=0.2))
        self.assertEqual(len(limit_tightening_findings(record)), 1)

    def test_both_bounds_loosened_gives_two_findings(self):
        record = validate_parameter(_own_limit(minimum=0.2, maximum=2.2))
        self.assertEqual(len(limit_tightening_findings(record)), 2)

    def test_dropping_a_published_bound_is_a_finding(self):
        record = validate_parameter(_own_limit(maximum=None))
        self.assertTrue(any("orders no upper bound" in f
                            for f in limit_tightening_findings(record)))

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


class TemperatureRangeTests(unittest.TestCase):
    def test_range_returned_as_a_pair(self):
        self.assertEqual(
            validate_temperature_range({"low_c": -40.0, "high_c": 105.0}),
            (-40.0, 105.0),
        )

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_range({"low_c": 105.0, "high_c": -40.0})

    def test_half_open_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_range({"low_c": -40.0, "high_c": None})

    def test_range_inside_the_published_one_raises_nothing(self):
        self.assertEqual(
            temperature_range_findings((-40.0, 105.0), (-55.0, 125.0)), []
        )

    def test_range_equal_to_the_published_one_is_admissible(self):
        self.assertEqual(
            temperature_range_findings((-55.0, 125.0), (-55.0, 125.0)), []
        )

    def test_range_colder_than_published_is_a_finding(self):
        findings = temperature_range_findings((-65.0, 105.0), (-55.0, 125.0))
        self.assertEqual(len(findings), 1)
        self.assertIn("below the published", findings[0])

    def test_range_hotter_than_published_is_a_finding(self):
        findings = temperature_range_findings((-55.0, 145.0), (-55.0, 125.0))
        self.assertIn("above the published", findings[0])

    def test_range_wider_at_both_ends_gives_two_findings(self):
        self.assertEqual(
            len(temperature_range_findings((-65.0, 145.0), (-55.0, 125.0))), 2
        )

    def test_no_ordered_range_is_a_finding(self):
        self.assertTrue(any("orders no temperature range" in f
                            for f in temperature_range_findings(None, (-55.0, 125.0))))

    def test_no_published_range_raises_nothing(self):
        self.assertEqual(temperature_range_findings((-40.0, 105.0), None), [])


class AcceptanceRouteTests(unittest.TestCase):
    def test_screening_route_needs_no_sample(self):
        route = validate_acceptance_route({"mode": "100 percent screening"})
        self.assertEqual(route["mode"], "100-percent-screening")
        self.assertIsNone(route["sample_size"])

    def test_lot_route_returned(self):
        route = validate_acceptance_route(
            {"mode": "lot-acceptance-sampling", "sample_size": 22, "accept_on": 0}
        )
        self.assertEqual(route["sample_size"], 22)

    def test_accept_number_reaching_the_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_route(
                {"mode": "lot-acceptance-sampling", "sample_size": 8, "accept_on": 8}
            )

    def test_manufacturer_flow_must_be_named(self):
        with self.assertRaises(ValueError):
            validate_acceptance_route({"mode": "manufacturer-standard-flow"})

    def test_named_manufacturer_flow_accepted(self):
        route = validate_acceptance_route(
            {"mode": "manufacturer-standard-flow", "flow": "maker flow QML-P equivalent"}
        )
        self.assertEqual(route["flow"], "maker flow QML-P equivalent")

    def test_blank_manufacturer_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_route(
                {"mode": "manufacturer-standard-flow", "flow": "   "}
            )

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_route({"mode": "whatever arrives"})

    def test_every_route_is_reachable(self):
        for mode in ACCEPTANCE_ROUTES:
            route = {"mode": mode}
            if mode == "lot-acceptance-sampling":
                route.update({"sample_size": 10, "accept_on": 0})
            if mode == "manufacturer-standard-flow":
                route["flow"] = "maker standard production flow"
            self.assertEqual(validate_acceptance_route(route)["mode"], mode)


class PartEntryTests(unittest.TestCase):
    def test_clean_entry_is_acceptable(self):
        self.assertTrue(assess_part_entry(_entry())["acceptable"])

    def test_entry_with_no_parameters_is_a_finding(self):
        record = assess_part_entry(_entry(parameters=[]))
        self.assertFalse(record["acceptable"])

    def test_entry_with_no_acceptance_route_is_a_finding(self):
        record = assess_part_entry(_entry(acceptance_route=None))
        self.assertTrue(any("no acceptance route" in f for f in record["findings"]))

    def test_repeated_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_entry(_entry(parameters=[_own_limit(), _own_limit()]))

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_entry(_entry(part_number="  "))

    def test_published_basis_parameters_are_listed(self):
        record = assess_part_entry(_entry())
        self.assertEqual(record["published_basis_parameters"], ["output rise time"])

    def test_temperature_finding_reaches_the_entry(self):
        record = assess_part_entry(
            _entry(ordered_temperature_range={"low_c": -55.0, "high_c": 135.0})
        )
        self.assertFalse(record["acceptable"])
        self.assertEqual(len(record["findings"]), 2)


class SpecificationTests(unittest.TestCase):
    def test_complete_specification_is_fit_to_order_against(self):
        result = assess_purchase_specification(_spec())
        self.assertTrue(result["fit_to_order_against"])
        self.assertEqual(result["findings"], [])

    def test_published_basis_share_is_reported(self):
        result = assess_purchase_specification(_spec())
        self.assertEqual(result["parameter_count"], 2)
        self.assertAlmostEqual(result["published_basis_share"], 0.5, places=9)

    def test_uncovered_ordered_part_is_a_finding(self):
        result = assess_purchase_specification(
            _spec(ordered_part_numbers=["XM-8820-KT", "XM-8822-KT"])
        )
        self.assertEqual(result["uncovered_part_numbers"], ["XM-8822-KT"])
        self.assertFalse(result["fit_to_order_against"])

    def test_entry_for_an_unordered_part_is_a_finding(self):
        result = assess_purchase_specification(
            _spec(entries=[_entry(), _entry(part_number="XM-9999-ZZ")])
        )
        self.assertEqual(result["unordered_entries"], ["XM-9999-ZZ"])

    def test_duplicate_part_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(entries=[_entry(), _entry()]))

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(ordered_part_numbers=[]))

    def test_uncontrolled_document_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(_spec(document=dict(HEADER, issue="")))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_purchase_specification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase_specification(["document"])

    def test_specification_of_pure_published_basis_is_reported(self):
        entry = _entry(parameters=[_published(), _published(name="input leakage")])
        result = assess_purchase_specification(_spec(entries=[entry]))
        self.assertAlmostEqual(result["published_basis_share"], 1.0, places=9)
        self.assertTrue(result["fit_to_order_against"])

    def test_every_finding_is_named_not_only_the_first(self):
        entry = _entry(
            parameters=[_own_limit(minimum=0.2, maximum=2.2, test_condition=""),
                        _published(citation=None)],
            ordered_temperature_range={"low_c": -65.0, "high_c": 145.0},
            acceptance_route=None,
        )
        result = assess_purchase_specification(
            _spec(entries=[entry], ordered_part_numbers=["XM-8820-KT", "XM-8822-KT"])
        )
        self.assertGreaterEqual(len(result["findings"]), 7)


if __name__ == "__main__":
    unittest.main()

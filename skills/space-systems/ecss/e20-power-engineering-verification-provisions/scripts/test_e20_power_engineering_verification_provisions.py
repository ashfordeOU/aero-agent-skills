#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.11.1 electrical power
engineering verification provisions.

Exercises scripts/e20_power_engineering_verification_provisions_logic.py
(stdlib unittest, offline). Contract: every power verification item maps
to exactly one engineering family and an unrecognized item raises; the
admissible method set follows the item; each method has an earliest
review at which its evidence matures and a provision planned earlier is
reported; the mandatory worst-case condition set is checked against the
conditions the evidence covers; the demonstrated power margin is the
availability surplus over the demand and an exactly-satisfied
requirement is not failed by floating-point subtraction; coverage is
the fraction of required items carrying a provision; and the aggregated
review is compliant only when every finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_engineering_verification_provisions_logic as pv  # noqa: E402


def _clean_budget_provision():
    """A power-budget provision that satisfies every clause 5.11.1 check."""
    return {
        "item_kind": "power_budget",
        "method": "analysis",
        "review_point": "CDR",
        "evidence_artefact": "EPS-AN-014 power budget analysis report",
        "covered_conditions": {
            "end_of_life",
            "worst_case_load_case",
            "maximum_eclipse",
        },
        "available_power_w": 1200.0,
        "demanded_power_w": 1000.0,
        "required_margin": 0.15,
    }


def _clean_stability_provision():
    return {
        "item_kind": "bus_voltage_stability",
        "method": "test",
        "review_point": "QR",
        "evidence_artefact": "EPS-TR-007 bus transient test report",
        "covered_conditions": {
            "worst_case_load_step",
            "maximum_source_impedance_case",
        },
    }


class TestItemCategorization(unittest.TestCase):
    def test_power_budget_is_a_budget_item(self):
        self.assertEqual(pv.categorize_verification_item("power_budget"), "budget")

    def test_battery_capacity_is_a_sizing_item(self):
        self.assertEqual(
            pv.categorize_verification_item("battery_capacity"), "sizing"
        )

    def test_bus_voltage_stability_is_a_dynamic_item(self):
        self.assertEqual(
            pv.categorize_verification_item("bus_voltage_stability"), "dynamic"
        )

    def test_protection_coordination_is_a_protection_item(self):
        self.assertEqual(
            pv.categorize_verification_item("power_protection_coordination"),
            "protection",
        )

    def test_every_item_lands_in_a_known_family(self):
        families = {
            pv.categorize_verification_item(k) for k in pv.POWER_VERIFICATION_ITEMS
        }
        self.assertEqual(
            families, {"budget", "sizing", "dynamic", "protection"}
        )

    def test_uncategorized_item_raises(self):
        with self.assertRaises(ValueError):
            pv.categorize_verification_item("thermal_balance")

    def test_none_item_raises(self):
        with self.assertRaises(ValueError):
            pv.categorize_verification_item(None)


class TestMethodsAndReviews(unittest.TestCase):
    def test_energy_balance_admits_only_analysis(self):
        self.assertEqual(pv.admissible_methods("energy_balance"), frozenset({"analysis"}))

    def test_solar_array_sizing_admits_similarity(self):
        self.assertIn("similarity", pv.admissible_methods("solar_array_sizing"))

    def test_admissible_methods_are_all_recognised_methods(self):
        for item_kind in pv.POWER_VERIFICATION_ITEMS:
            self.assertTrue(
                pv.admissible_methods(item_kind) <= pv.VERIFICATION_METHODS,
                msg=item_kind,
            )

    def test_admissible_methods_unknown_item_raises(self):
        with self.assertRaises(ValueError):
            pv.admissible_methods("attitude_budget")

    def test_review_of_design_matures_at_pdr(self):
        self.assertEqual(pv.earliest_closure_review("review_of_design"), "PDR")

    def test_test_method_matures_at_qr(self):
        self.assertEqual(pv.earliest_closure_review("test"), "QR")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            pv.earliest_closure_review("demonstration_by_opinion")

    def test_review_index_is_chronological(self):
        self.assertLess(pv.review_index("PDR"), pv.review_index("CDR"))
        self.assertLess(pv.review_index("CDR"), pv.review_index("QR"))
        self.assertLess(pv.review_index("QR"), pv.review_index("AR"))

    def test_unknown_review_point_raises(self):
        with self.assertRaises(ValueError):
            pv.review_index("SRR")


class TestMargin(unittest.TestCase):
    def test_margin_fraction_is_surplus_over_demand(self):
        self.assertAlmostEqual(
            pv.power_margin_fraction(1200.0, 1000.0), 0.2, places=12
        )

    def test_zero_margin_when_supply_equals_demand(self):
        self.assertAlmostEqual(pv.power_margin_fraction(900.0, 900.0), 0.0, places=12)

    def test_negative_margin_when_demand_exceeds_supply(self):
        self.assertAlmostEqual(
            pv.power_margin_fraction(800.0, 1000.0), -0.2, places=12
        )

    def test_zero_demand_raises(self):
        with self.assertRaises(ValueError):
            pv.power_margin_fraction(100.0, 0.0)

    def test_negative_demand_raises(self):
        with self.assertRaises(ValueError):
            pv.power_margin_fraction(100.0, -5.0)

    def test_negative_availability_raises(self):
        with self.assertRaises(ValueError):
            pv.power_margin_fraction(-1.0, 100.0)

    def test_non_numeric_availability_raises(self):
        with self.assertRaises(ValueError):
            pv.power_margin_fraction("1200", 1000.0)

    def test_boolean_demand_raises(self):
        with self.assertRaises(ValueError):
            pv.power_margin_fraction(100.0, True)

    def test_exactly_satisfied_margin_survives_float_subtraction(self):
        """3.3 W against 3.0 W is exactly a ten percent margin, but the
        subtraction lands a few units in the last place low."""
        margin = pv.power_margin_fraction(3.3, 3.0)
        self.assertLess(margin, 0.1)
        self.assertTrue(pv.margin_meets_requirement(margin, 0.1))

    def test_real_shortfall_still_fails(self):
        margin = pv.power_margin_fraction(1050.0, 1000.0)
        self.assertFalse(pv.margin_meets_requirement(margin, 0.1))

    def test_comfortable_margin_passes(self):
        self.assertTrue(pv.margin_meets_requirement(0.31, 0.2))

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            pv.margin_meets_requirement(0.2, -0.05)

    def test_non_numeric_required_margin_raises(self):
        with self.assertRaises(ValueError):
            pv.margin_meets_requirement(0.2, "0.1")


class TestConditions(unittest.TestCase):
    def test_full_coverage_reports_no_missing_condition(self):
        self.assertEqual(
            pv.missing_conditions(
                "energy_balance",
                {"end_of_life", "maximum_eclipse", "worst_case_solar_aspect"},
            ),
            [],
        )

    def test_beginning_of_life_only_evidence_misses_end_of_life(self):
        self.assertIn(
            "end_of_life",
            pv.missing_conditions(
                "energy_balance", {"maximum_eclipse", "worst_case_solar_aspect"}
            ),
        )

    def test_missing_conditions_are_sorted(self):
        missing = pv.missing_conditions("energy_balance", set())
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), 3)

    def test_extra_conditions_are_not_findings(self):
        self.assertEqual(
            pv.missing_conditions(
                "harness_voltage_drop",
                {"worst_case_load_case", "hot_case_temperature", "launch_case"},
            ),
            [],
        )

    def test_string_condition_set_raises(self):
        with self.assertRaises(ValueError):
            pv.missing_conditions("power_budget", "end_of_life")

    def test_none_condition_set_raises(self):
        with self.assertRaises(ValueError):
            pv.missing_conditions("power_budget", None)


class TestProvisionCheck(unittest.TestCase):
    def test_clean_budget_provision_has_no_findings(self):
        self.assertEqual(pv.check_verification_provision(_clean_budget_provision()), [])

    def test_clean_stability_provision_has_no_findings(self):
        self.assertEqual(
            pv.check_verification_provision(_clean_stability_provision()), []
        )

    def test_inadmissible_method_is_a_finding(self):
        provision = _clean_budget_provision()
        provision["method"] = "inspection"
        provision["review_point"] = "CDR"
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("cannot produce closure evidence" in f for f in findings))

    def test_review_earlier_than_method_maturity_is_a_finding(self):
        provision = _clean_stability_provision()
        provision["review_point"] = "PDR"
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("earlier than" in f for f in findings))

    def test_review_later_than_maturity_is_accepted(self):
        provision = _clean_stability_provision()
        provision["review_point"] = "AR"
        self.assertEqual(pv.check_verification_provision(provision), [])

    def test_missing_evidence_artefact_is_a_finding(self):
        provision = _clean_budget_provision()
        provision["evidence_artefact"] = "   "
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("no evidence artefact" in f for f in findings))

    def test_absent_worst_case_condition_is_a_finding(self):
        provision = _clean_budget_provision()
        provision["covered_conditions"] = {"end_of_life", "worst_case_load_case"}
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("maximum_eclipse" in f for f in findings))

    def test_margin_item_without_margin_data_is_a_finding(self):
        provision = _clean_budget_provision()
        del provision["available_power_w"]
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("no available/demanded/required" in f for f in findings))

    def test_insufficient_margin_is_a_finding(self):
        provision = _clean_budget_provision()
        provision["available_power_w"] = 1050.0
        findings = pv.check_verification_provision(provision)
        self.assertTrue(any("below the required" in f for f in findings))

    def test_non_margin_item_needs_no_margin_data(self):
        provision = _clean_stability_provision()
        self.assertNotIn("available_power_w", provision)
        self.assertEqual(pv.check_verification_provision(provision), [])

    def test_findings_are_sorted(self):
        provision = _clean_budget_provision()
        provision["covered_conditions"] = set()
        provision["evidence_artefact"] = ""
        findings = pv.check_verification_provision(provision)
        self.assertEqual(findings, sorted(findings))
        self.assertGreaterEqual(len(findings), 4)

    def test_unknown_item_in_provision_raises(self):
        provision = _clean_budget_provision()
        provision["item_kind"] = "propellant_budget"
        with self.assertRaises(ValueError):
            pv.check_verification_provision(provision)

    def test_unknown_method_in_provision_raises(self):
        provision = _clean_budget_provision()
        provision["method"] = "handwave"
        with self.assertRaises(ValueError):
            pv.check_verification_provision(provision)

    def test_unknown_review_point_in_provision_raises(self):
        provision = _clean_budget_provision()
        provision["review_point"] = "MDR"
        with self.assertRaises(ValueError):
            pv.check_verification_provision(provision)


class TestCoverageAndAggregate(unittest.TestCase):
    def test_full_coverage_is_one(self):
        provisions = [_clean_budget_provision(), _clean_stability_provision()]
        self.assertAlmostEqual(
            pv.verification_coverage(
                provisions, {"power_budget", "bus_voltage_stability"}
            ),
            1.0,
            places=9,
        )

    def test_partial_coverage_is_a_fraction(self):
        provisions = [_clean_budget_provision()]
        self.assertAlmostEqual(
            pv.verification_coverage(
                provisions,
                {"power_budget", "bus_voltage_stability", "battery_capacity"},
            ),
            round(1.0 / 3.0, 6),
            places=6,
        )

    def test_empty_required_set_raises(self):
        with self.assertRaises(ValueError):
            pv.verification_coverage([_clean_budget_provision()], set())

    def test_unknown_required_item_raises(self):
        with self.assertRaises(ValueError):
            pv.verification_coverage([_clean_budget_provision()], {"mass_budget"})

    def test_aggregate_clean_set_is_compliant(self):
        result = pv.aggregate_power_verification(
            [_clean_budget_provision(), _clean_stability_provision()],
            {"power_budget", "bus_voltage_stability"},
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["item_findings"], {})
        self.assertEqual(result["uncovered_items"], [])
        self.assertEqual(result["orphan_items"], [])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_aggregate_reports_uncovered_item(self):
        result = pv.aggregate_power_verification(
            [_clean_budget_provision()],
            {"power_budget", "battery_capacity"},
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["uncovered_items"], ["battery_capacity"])

    def test_aggregate_reports_orphan_provision(self):
        result = pv.aggregate_power_verification(
            [_clean_budget_provision(), _clean_stability_provision()],
            {"power_budget"},
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["orphan_items"], ["bus_voltage_stability"])

    def test_aggregate_collects_item_findings(self):
        bad = _clean_budget_provision()
        bad["available_power_w"] = 1000.0
        result = pv.aggregate_power_verification([bad], {"power_budget"})
        self.assertFalse(result["compliant"])
        self.assertIn("power_budget", result["item_findings"])

    def test_aggregate_coverage_is_not_bare_float_equality(self):
        result = pv.aggregate_power_verification(
            [_clean_budget_provision()], {"power_budget"}
        )
        self.assertTrue(math.isclose(result["coverage"], 1.0, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()

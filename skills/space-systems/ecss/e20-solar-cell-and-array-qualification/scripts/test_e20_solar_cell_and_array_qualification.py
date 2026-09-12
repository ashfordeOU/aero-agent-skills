#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.5.1 photovoltaic
assembly qualification.

Exercises scripts/e20_solar_cell_and_array_qualification_logic.py
(stdlib unittest, offline). Contract: a photovoltaic item type maps to
exactly one qualification category and an unrecognized type raises; the
route is full without heritage, similarity only when the design and
process are unchanged and the environment envelope is covered, and
delta otherwise, with a non-boolean heritage flag raising; the owed
test set follows the category and every owed test absent from the
programme is reported; the required thermal-cycle count is the mission
eclipse cycles times the qualification factor rounded up; the required
fluence is the end-of-life dose times the margin factor; end-of-life
power is the beginning-of-life power times every named degradation
factor, with a missing or out-of-range factor raising; and the
aggregated review is complete only when every finding list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_solar_cell_and_array_qualification_logic as sq  # noqa: E402


def _clean_factors():
    return {
        "radiation": 0.90,
        "ultraviolet": 0.98,
        "thermal_cycling": 0.99,
        "contamination": 0.99,
        "mismatch": 0.98,
    }


def _clean_item():
    """A new-design cell assembly that satisfies every clause 5.5.1
    check on the full-qualification route."""
    return {
        "item_id": "CIC-3J-01",
        "item_type": "cell_coverglass_assembly",
        "flight_proven": False,
        "design_or_process_changed": True,
        "environment_envelope_covered": False,
        "planned_tests": [
            "electrical_performance_am0",
            "thermal_cycling",
            "particle_irradiation",
            "humidity_and_temperature",
            "reverse_bias_characterisation",
        ],
        "planned_cycles": 12000,
        "mission_eclipse_cycles": 5500,
        "qualification_fluence": 2.0e15,
        "end_of_life_fluence": 1.0e15,
        "beginning_of_life_power_w": 1200.0,
        "degradation_factors": _clean_factors(),
        "required_eol_power_w": 1000.0,
    }


class CategorizeItemTest(unittest.TestCase):
    def test_bare_cell_is_cell_level(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("bare_solar_cell"), "cell_level"
        )

    def test_cell_coverglass_assembly_is_cell_level(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("cell_coverglass_assembly"),
            "cell_level",
        )

    def test_coverglass_is_optical(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("coverglass"), "optical"
        )

    def test_interconnect_is_its_own_category(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("interconnect"), "interconnect"
        )

    def test_bypass_diode_is_protection_diode(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("bypass_diode"), "protection_diode"
        )

    def test_wing_assembly_is_assembly(self):
        self.assertEqual(
            sq.categorize_photovoltaic_item("wing_assembly"), "assembly"
        )

    def test_unknown_item_raises(self):
        with self.assertRaises(ValueError):
            sq.categorize_photovoltaic_item("reaction_wheel")


class QualificationRouteTest(unittest.TestCase):
    def test_new_design_is_full(self):
        self.assertEqual(
            sq.qualification_route(False, True, False), sq.ROUTE_FULL
        )

    def test_new_design_stays_full_even_if_envelope_covered(self):
        self.assertEqual(
            sq.qualification_route(False, False, True), sq.ROUTE_FULL
        )

    def test_unchanged_and_enveloped_is_similarity(self):
        self.assertEqual(
            sq.qualification_route(True, False, True), sq.ROUTE_SIMILARITY
        )

    def test_modified_flight_proven_is_delta(self):
        self.assertEqual(
            sq.qualification_route(True, True, True), sq.ROUTE_DELTA
        )

    def test_harsher_environment_forces_delta(self):
        self.assertEqual(
            sq.qualification_route(True, False, False), sq.ROUTE_DELTA
        )

    def test_non_boolean_heritage_raises(self):
        with self.assertRaises(ValueError):
            sq.qualification_route("yes", False, True)

    def test_non_boolean_envelope_raises(self):
        with self.assertRaises(ValueError):
            sq.qualification_route(True, False, 1)


class OwedTestsTest(unittest.TestCase):
    def test_cell_level_owes_reverse_bias(self):
        self.assertIn("reverse_bias_characterisation", sq.owed_tests("cell_level"))

    def test_optical_owes_ultraviolet_exposure(self):
        self.assertIn("ultraviolet_exposure", sq.owed_tests("optical"))

    def test_optical_does_not_owe_reverse_bias(self):
        self.assertNotIn(
            "reverse_bias_characterisation", sq.owed_tests("optical")
        )

    def test_protection_diode_owes_reverse_characterisation(self):
        self.assertIn(
            "reverse_characterisation", sq.owed_tests("protection_diode")
        )

    def test_every_category_owes_thermal_cycling(self):
        for category in (
            "cell_level",
            "optical",
            "interconnect",
            "protection_diode",
            "assembly",
        ):
            self.assertIn("thermal_cycling", sq.owed_tests(category))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            sq.owed_tests("structural")

    def test_complete_programme_has_no_missing_test(self):
        self.assertEqual(
            sq.missing_qualification_tests(
                "interconnect",
                ["thermal_cycling", "pull_strength", "metallurgical_section"],
            ),
            [],
        )

    def test_missing_tests_are_sorted(self):
        missing = sq.missing_qualification_tests("assembly", [])
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), 5)

    def test_extra_planned_test_is_not_a_finding(self):
        self.assertEqual(
            sq.missing_qualification_tests(
                "interconnect",
                [
                    "thermal_cycling",
                    "pull_strength",
                    "metallurgical_section",
                    "acoustic_survey",
                ],
            ),
            [],
        )


class ThermalCycleTest(unittest.TestCase):
    def test_required_cycles_apply_the_factor(self):
        self.assertEqual(sq.required_thermal_cycles(5500, 2.0), 11000)

    def test_fractional_requirement_rounds_up(self):
        self.assertEqual(sq.required_thermal_cycles(1001, 1.5), 1502)

    def test_factor_of_one_is_allowed(self):
        self.assertEqual(sq.required_thermal_cycles(300, 1.0), 300)

    def test_non_positive_mission_cycles_raises(self):
        with self.assertRaises(ValueError):
            sq.required_thermal_cycles(0, 2.0)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            sq.required_thermal_cycles(5500, 0.5)

    def test_sufficient_plan_has_no_finding(self):
        self.assertEqual(sq.thermal_cycle_findings("C1", 12000, 5500), [])

    def test_short_plan_is_reported(self):
        findings = sq.thermal_cycle_findings("C1", 9000, 5500)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "insufficient_thermal_cycle_count"
        )
        self.assertEqual(findings[0]["required_cycles"], 11000)

    def test_negative_planned_cycles_raises(self):
        with self.assertRaises(ValueError):
            sq.thermal_cycle_findings("C1", -1, 5500)


class RadiationTest(unittest.TestCase):
    def test_required_fluence_applies_the_margin(self):
        self.assertAlmostEqual(
            sq.required_radiation_fluence(1.0e15, 1.5) / 1.0e15, 1.5
        )

    def test_non_positive_eol_fluence_raises(self):
        with self.assertRaises(ValueError):
            sq.required_radiation_fluence(0.0, 1.5)

    def test_margin_below_one_raises(self):
        with self.assertRaises(ValueError):
            sq.required_radiation_fluence(1.0e15, 0.9)

    def test_sufficient_fluence_has_no_finding(self):
        self.assertEqual(sq.radiation_findings("C1", 2.0e15, 1.0e15), [])

    def test_short_fluence_is_reported(self):
        findings = sq.radiation_findings("C1", 1.0e15, 1.0e15)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "qualification_fluence_below_end_of_life_dose",
        )
        self.assertAlmostEqual(
            findings[0]["required_fluence"] / 1.0e15, 1.5
        )

    def test_negative_qualification_fluence_raises(self):
        with self.assertRaises(ValueError):
            sq.radiation_findings("C1", -1.0, 1.0e15)


class EndOfLifePowerTest(unittest.TestCase):
    def test_power_is_the_product_of_factors(self):
        expected = 1200.0 * 0.90 * 0.98 * 0.99 * 0.99 * 0.98
        self.assertAlmostEqual(
            sq.end_of_life_power(1200.0, _clean_factors()), expected
        )

    def test_all_factors_unity_returns_bol_power(self):
        unity = {name: 1.0 for name in sq.DEGRADATION_FACTOR_NAMES}
        self.assertAlmostEqual(sq.end_of_life_power(1200.0, unity), 1200.0)

    def test_missing_factor_raises(self):
        factors = _clean_factors()
        del factors["mismatch"]
        with self.assertRaises(ValueError):
            sq.end_of_life_power(1200.0, factors)

    def test_factor_above_one_raises(self):
        factors = _clean_factors()
        factors["radiation"] = 1.05
        with self.assertRaises(ValueError):
            sq.end_of_life_power(1200.0, factors)

    def test_zero_factor_raises(self):
        factors = _clean_factors()
        factors["contamination"] = 0.0
        with self.assertRaises(ValueError):
            sq.end_of_life_power(1200.0, factors)

    def test_non_positive_bol_power_raises(self):
        with self.assertRaises(ValueError):
            sq.end_of_life_power(0.0, _clean_factors())

    def test_sufficient_power_has_no_finding(self):
        self.assertEqual(
            sq.power_findings("A1", 1200.0, _clean_factors(), 1000.0), []
        )

    def test_short_power_is_reported(self):
        findings = sq.power_findings("A1", 1200.0, _clean_factors(), 1150.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "end_of_life_power_below_requirement"
        )

    def test_non_positive_requirement_raises(self):
        with self.assertRaises(ValueError):
            sq.power_findings("A1", 1200.0, _clean_factors(), 0.0)


class QualificationReviewTest(unittest.TestCase):
    def test_clean_item_is_complete(self):
        review = sq.qualification_review(_clean_item())
        self.assertTrue(sq.is_qualification_complete(review))
        self.assertEqual(review["route"], sq.ROUTE_FULL)

    def test_missing_test_breaks_completion(self):
        item = _clean_item()
        item["planned_tests"] = ["electrical_performance_am0", "thermal_cycling"]
        review = sq.qualification_review(item)
        self.assertFalse(sq.is_qualification_complete(review))
        self.assertEqual(len(review["test_coverage"]), 3)

    def test_similarity_route_waives_test_coverage(self):
        item = _clean_item()
        item["flight_proven"] = True
        item["design_or_process_changed"] = False
        item["environment_envelope_covered"] = True
        item["planned_tests"] = []
        review = sq.qualification_review(item)
        self.assertEqual(review["route"], sq.ROUTE_SIMILARITY)
        self.assertEqual(review["test_coverage"], [])
        self.assertTrue(sq.is_qualification_complete(review))

    def test_similarity_route_still_owes_the_radiation_check(self):
        item = _clean_item()
        item["flight_proven"] = True
        item["design_or_process_changed"] = False
        item["environment_envelope_covered"] = True
        item["planned_tests"] = []
        item["qualification_fluence"] = 1.0e14
        review = sq.qualification_review(item)
        self.assertEqual(len(review["radiation"]), 1)
        self.assertFalse(sq.is_qualification_complete(review))

    def test_short_cycles_show_in_thermal_cycling_only(self):
        item = _clean_item()
        item["planned_cycles"] = 4000
        review = sq.qualification_review(item)
        self.assertEqual(len(review["thermal_cycling"]), 1)
        self.assertEqual(review["test_coverage"], [])
        self.assertEqual(review["power"], [])

    def test_unknown_item_type_raises_in_review(self):
        item = _clean_item()
        item["item_type"] = "reaction_wheel"
        with self.assertRaises(ValueError):
            sq.qualification_review(item)

    def test_review_does_not_mutate_input(self):
        item = _clean_item()
        snapshot = {
            "planned_tests": list(item["planned_tests"]),
            "degradation_factors": dict(item["degradation_factors"]),
        }
        sq.qualification_review(item)
        self.assertEqual(item["planned_tests"], snapshot["planned_tests"])
        self.assertEqual(
            item["degradation_factors"], snapshot["degradation_factors"]
        )


if __name__ == "__main__":
    unittest.main()

"""Contract test for the device-production-and-testing leaf (stdlib unittest)."""

import unittest

from e2040_device_production_and_testing_logic import (
    FINDING_COVERAGE_BELOW_FLOOR,
    FINDING_NO_LOTS_REPORTED,
    FINDING_PARAMETER_NOT_EXERCISED,
    FINDING_TECHNOLOGY_NOT_REPORTED,
    FINDING_YIELD_BELOW_EXPECTATION,
    assess_device_production_and_testing,
    assess_technology,
    lot_yield_fraction,
    meets_floor,
    test_coverage_fraction,
    unexercised_parameters,
    validate_device,
    validate_lot,
    validate_technology_report,
)


def device(technologies=("tech-a",), did="DEV-1"):
    return {"id": did, "technologies": list(technologies)}


def lot(lid="LOT-1", started=120, completed=100, tested=100, passed=95):
    return {
        "id": lid,
        "units_started": started,
        "units_completed": completed,
        "units_tested": tested,
        "units_passed": passed,
    }


def report(technology="tech-a", lots=None, **kw):
    record = {
        "technology": technology,
        "owed_parameters": ["static-supply-current", "functional-vector-set"],
        "program_parameters": ["static-supply-current", "functional-vector-set"],
        "coverage_floor": 1.0,
        "yield_expectation": 0.9,
        "lots": [lot()] if lots is None else lots,
    }
    record.update(kw)
    return record


class TestValidateDevice(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        self.assertEqual(validate_device(device())["technologies"], ["tech-a"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_device("DEV-1")

    def test_empty_technology_list_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=()))

    def test_duplicate_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(technologies=("tech-a", "tech-a")))


class TestValidateLot(unittest.TestCase):
    def test_normalizes_a_good_lot(self):
        self.assertEqual(validate_lot(lot())["units_passed"], 95)

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(passed=-1))

    def test_non_integer_count_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(tested=10.5))

    def test_completed_above_started_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(started=10, completed=20, tested=10, passed=10))

    def test_tested_above_completed_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(completed=50, tested=60, passed=50))

    def test_passed_above_tested_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(tested=50, passed=60))


class TestFractions(unittest.TestCase):
    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(test_coverage_fraction(lot()), 1.0, places=9)

    def test_partial_coverage(self):
        self.assertAlmostEqual(
            test_coverage_fraction(lot(tested=25, passed=25)), 0.25, places=9
        )

    def test_yield_fraction(self):
        self.assertAlmostEqual(lot_yield_fraction(lot()), 0.95, places=9)

    def test_zero_completed_has_no_coverage(self):
        with self.assertRaises(ValueError):
            test_coverage_fraction(lot(started=5, completed=0, tested=0, passed=0))

    def test_zero_tested_has_no_yield(self):
        with self.assertRaises(ValueError):
            lot_yield_fraction(lot(tested=0, passed=0))

    def test_floor_is_met_exactly_on_the_boundary(self):
        self.assertTrue(meets_floor(0.9, 0.9))

    def test_floor_is_not_met_below_it(self):
        self.assertFalse(meets_floor(0.89, 0.9))

    def test_fraction_outside_zero_to_one_raises(self):
        with self.assertRaises(ValueError):
            meets_floor(1.2, 0.9)


class TestTechnologyReport(unittest.TestCase):
    def test_undeclared_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_report(report(technology="tech-z"), device())

    def test_empty_owed_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_report(report(owed_parameters=[]), device())

    def test_coverage_floor_outside_range_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_report(report(coverage_floor=1.5), device())

    def test_duplicate_lot_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_report(report(lots=[lot(), lot()]), device())

    def test_unexercised_parameter_is_named(self):
        self.assertEqual(
            unexercised_parameters(
                report(program_parameters=["static-supply-current"]), device()
            ),
            ["functional-vector-set"],
        )

    def test_fully_exercised_program_names_nothing(self):
        self.assertEqual(unexercised_parameters(report(), device()), [])


class TestAssessTechnology(unittest.TestCase):
    def test_clean_technology_is_acceptable(self):
        result = assess_technology(report(), device())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["lots"][0]["coverage"], 1.0, places=9)

    def test_coverage_below_floor_is_a_finding(self):
        result = assess_technology(
            report(lots=[lot(tested=80, passed=80)]), device()
        )
        self.assertIn(("LOT-1", FINDING_COVERAGE_BELOW_FLOOR), result["findings"])
        self.assertFalse(result["acceptable"])

    def test_yield_below_expectation_opens_an_investigation(self):
        result = assess_technology(report(lots=[lot(passed=80)]), device())
        self.assertIn(("LOT-1", FINDING_YIELD_BELOW_EXPECTATION), result["findings"])
        self.assertTrue(result["lots"][0]["investigation_owed"])
        self.assertTrue(result["lots"][0]["acceptable"])

    def test_yield_exactly_on_expectation_opens_nothing(self):
        result = assess_technology(report(lots=[lot(passed=90)]), device())
        self.assertFalse(result["lots"][0]["investigation_owed"])
        self.assertAlmostEqual(result["lots"][0]["yield"], 0.9, places=9)

    def test_missing_parameter_makes_the_technology_unacceptable(self):
        result = assess_technology(
            report(program_parameters=["static-supply-current"]), device()
        )
        self.assertIn(
            ("functional-vector-set", FINDING_PARAMETER_NOT_EXERCISED),
            result["findings"],
        )
        self.assertFalse(result["acceptable"])

    def test_technology_with_no_lots_is_a_finding(self):
        result = assess_technology(report(lots=[]), device())
        self.assertIn(("tech-a", FINDING_NO_LOTS_REPORTED), result["findings"])
        self.assertFalse(result["acceptable"])


class TestAssessDevice(unittest.TestCase):
    def test_single_technology_device_is_complete(self):
        result = assess_device_production_and_testing(device(), [report()])
        self.assertTrue(result["complete"])
        self.assertEqual(result["unreported_technologies"], [])

    def test_second_technology_without_a_report_is_a_gap(self):
        dev = device(technologies=("tech-a", "tech-b"))
        result = assess_device_production_and_testing(dev, [report("tech-a")])
        self.assertEqual(result["unreported_technologies"], ["tech-b"])
        self.assertIn(("tech-b", FINDING_TECHNOLOGY_NOT_REPORTED), result["findings"])
        self.assertFalse(result["complete"])

    def test_both_technologies_reported_is_complete(self):
        dev = device(technologies=("tech-a", "tech-b"))
        result = assess_device_production_and_testing(
            dev, [report("tech-a"), report("tech-b")]
        )
        self.assertTrue(result["complete"])

    def test_investigations_are_listed_per_lot(self):
        result = assess_device_production_and_testing(
            device(), [report(lots=[lot(passed=70)])]
        )
        self.assertEqual(result["investigations_owed"], [("tech-a", "LOT-1")])

    def test_duplicate_technology_report_raises(self):
        with self.assertRaises(ValueError):
            assess_device_production_and_testing(device(), [report(), report()])

    def test_non_list_reports_raises(self):
        with self.assertRaises(ValueError):
            assess_device_production_and_testing(device(), report())


if __name__ == "__main__":
    unittest.main()

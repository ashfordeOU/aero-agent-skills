"""Contract tests for the clause 4.4.2 budget allocation and tracking logic."""

import unittest

from e31_budget_allocation_thermal_power_mass_logic import (
    BUDGET_TOLERANCE,
    MATURITY_CONTINGENCY,
    STEFAN_BOLTZMANN_W_PER_M2K4,
    apply_system_margin,
    assess_budget_allocation,
    assess_heater_power_budget,
    assess_mass_budget,
    assess_thermal_rejection_budget,
    budget_status,
    line_with_contingency,
    maturity_contingency,
    radiator_rejection_w,
    roll_up,
    validate_positive,
)


def thermal_budget(**overrides):
    """Return a representative hot-case dissipation budget record."""
    record = {
        "lines": [
            {"name": "transponder", "dissipation_w": 120.0,
             "maturity": "off-the-shelf"},
            {"name": "payload-processor", "dissipation_w": 200.0,
             "maturity": "new-design"},
            {"name": "power-conditioning", "dissipation_w": 90.0,
             "maturity": "modified"},
        ],
        "system_margin_fraction": 0.10,
        "radiator_area_m2": 2.4,
        "radiator_emissivity": 0.86,
        "radiator_temperature_k": 310.0,
        "sink_temperature_k": 120.0,
    }
    record.update(overrides)
    return record


def heater_budget(**overrides):
    """Return a representative cold-case heater power budget record."""
    record = {
        "lines": [
            {"name": "propellant-lines", "heater_power_w": 34.0,
             "maturity": "modified"},
            {"name": "battery", "heater_power_w": 18.0,
             "maturity": "off-the-shelf"},
        ],
        "system_margin_fraction": 0.15,
        "allocation_w": 90.0,
    }
    record.update(overrides)
    return record


def mass_budget(**overrides):
    """Return a representative thermal hardware mass budget record."""
    record = {
        "lines": [
            {"name": "radiator-panels", "mass_kg": 6.4, "maturity": "modified"},
            {"name": "multilayer-insulation", "mass_kg": 3.1,
             "maturity": "off-the-shelf"},
            {"name": "heat-pipes", "mass_kg": 4.2, "maturity": "new-design"},
        ],
        "system_margin_fraction": 0.05,
        "allocation_kg": 20.0,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive("x", 9), 9.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))


class ContingencyTests(unittest.TestCase):
    def test_off_the_shelf_carries_the_least(self):
        self.assertAlmostEqual(maturity_contingency("off-the-shelf"), 0.05, places=12)

    def test_new_design_carries_the_most(self):
        self.assertAlmostEqual(maturity_contingency("new-design"), 0.20, places=12)

    def test_contingency_rises_with_novelty(self):
        self.assertLess(
            MATURITY_CONTINGENCY["off-the-shelf"], MATURITY_CONTINGENCY["modified"]
        )
        self.assertLess(
            MATURITY_CONTINGENCY["modified"], MATURITY_CONTINGENCY["new-design"]
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            maturity_contingency("probably-fine")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            maturity_contingency(0.1)


class BudgetLineTests(unittest.TestCase):
    def test_line_applies_its_contingency(self):
        line = {"name": "heat-pipes", "mass_kg": 4.0, "maturity": "new-design"}
        self.assertAlmostEqual(
            line_with_contingency(line, "mass_kg"), 4.8, places=12
        )

    def test_zero_value_line_allowed(self):
        line = {"name": "spare", "mass_kg": 0.0, "maturity": "modified"}
        self.assertAlmostEqual(line_with_contingency(line, "mass_kg"), 0.0, places=12)

    def test_line_without_maturity_is_unknown_not_zero(self):
        line = {"name": "heat-pipes", "mass_kg": 4.0}
        with self.assertRaises(ValueError):
            line_with_contingency(line, "mass_kg")

    def test_line_missing_the_value_rejected(self):
        line = {"name": "heat-pipes", "maturity": "modified"}
        with self.assertRaises(ValueError):
            line_with_contingency(line, "mass_kg")

    def test_unnamed_line_rejected(self):
        with self.assertRaises(ValueError):
            line_with_contingency({"mass_kg": 4.0, "maturity": "modified"}, "mass_kg")

    def test_negative_value_rejected(self):
        line = {"name": "heat-pipes", "mass_kg": -4.0, "maturity": "modified"}
        with self.assertRaises(ValueError):
            line_with_contingency(line, "mass_kg")


class RollUpTests(unittest.TestCase):
    def test_raw_and_loaded_totals_are_both_reported(self):
        totals = roll_up(mass_budget()["lines"], "mass_kg")
        self.assertAlmostEqual(totals["raw"], 13.7, places=12)
        expected = 6.4 * 1.10 + 3.1 * 1.05 + 4.2 * 1.20
        self.assertAlmostEqual(totals["with_contingency"], expected, places=12)

    def test_contingency_total_never_below_the_raw_total(self):
        totals = roll_up(mass_budget()["lines"], "mass_kg")
        self.assertGreater(totals["with_contingency"], totals["raw"])

    def test_duplicate_line_names_rejected(self):
        lines = [
            {"name": "heat-pipes", "mass_kg": 4.0, "maturity": "modified"},
            {"name": "heat-pipes", "mass_kg": 2.0, "maturity": "modified"},
        ]
        with self.assertRaises(ValueError):
            roll_up(lines, "mass_kg")

    def test_empty_line_set_rejected(self):
        with self.assertRaises(ValueError):
            roll_up([], "mass_kg")


class SystemMarginTests(unittest.TestCase):
    def test_margin_scales_the_total(self):
        self.assertAlmostEqual(apply_system_margin(100.0, 0.10), 110.0, places=12)

    def test_zero_margin_leaves_the_total(self):
        self.assertAlmostEqual(apply_system_margin(100.0, 0.0), 100.0, places=12)

    def test_margin_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            apply_system_margin(100.0, 1.0)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            apply_system_margin(100.0, -0.1)


class BudgetStatusTests(unittest.TestCase):
    def test_margin_fraction_reported(self):
        status = budget_status(80.0, 100.0)
        self.assertAlmostEqual(status["margin_fraction"], 0.20, places=12)
        self.assertTrue(status["compliant"])

    def test_exactly_on_the_allocation_is_compliant(self):
        status = budget_status(100.0, 100.0)
        self.assertAlmostEqual(status["margin_fraction"], 0.0, places=12)
        self.assertTrue(status["compliant"])

    def test_over_the_allocation_is_not_compliant(self):
        status = budget_status(120.0, 100.0)
        self.assertFalse(status["compliant"])
        self.assertAlmostEqual(status["margin_fraction"], -0.20, places=12)

    def test_zero_allocation_rejected(self):
        with self.assertRaises(ValueError):
            budget_status(80.0, 0.0)

    def test_tolerance_is_a_rounding_allowance(self):
        self.assertLess(BUDGET_TOLERANCE, 1e-6)


class RadiatorRejectionTests(unittest.TestCase):
    def test_rejection_matches_the_grey_body_expression(self):
        value = radiator_rejection_w(2.0, 0.9, 300.0, 100.0)
        expected = 0.9 * STEFAN_BOLTZMANN_W_PER_M2K4 * 2.0 * (300.0 ** 4 - 100.0 ** 4)
        self.assertAlmostEqual(value, expected, places=9)

    def test_doubling_the_area_doubles_the_rejection(self):
        single = radiator_rejection_w(2.0, 0.9, 300.0, 100.0)
        double = radiator_rejection_w(4.0, 0.9, 300.0, 100.0)
        self.assertAlmostEqual(double / single, 2.0, places=12)

    def test_colder_sink_rejects_more(self):
        warm_sink = radiator_rejection_w(2.0, 0.9, 300.0, 250.0)
        cold_sink = radiator_rejection_w(2.0, 0.9, 300.0, 100.0)
        self.assertGreater(cold_sink, warm_sink)

    def test_sink_at_the_radiator_temperature_rejected(self):
        with self.assertRaises(ValueError):
            radiator_rejection_w(2.0, 0.9, 300.0, 300.0)

    def test_emissivity_above_one_rejected(self):
        with self.assertRaises(ValueError):
            radiator_rejection_w(2.0, 1.2, 300.0, 100.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            radiator_rejection_w(0.0, 0.9, 300.0, 100.0)


class ThermalBudgetTests(unittest.TestCase):
    def test_nominal_thermal_budget_is_compliant(self):
        result = assess_thermal_rejection_budget(thermal_budget())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tracked_value_carries_both_layers_of_growth(self):
        result = assess_thermal_rejection_budget(thermal_budget())
        expected_loaded = 120.0 * 1.05 + 200.0 * 1.20 + 90.0 * 1.10
        self.assertAlmostEqual(
            result["with_contingency_w"], expected_loaded, places=12
        )
        self.assertAlmostEqual(
            result["tracked_w"], expected_loaded * 1.10, places=12
        )

    def test_small_radiator_raises_a_rejection_finding(self):
        result = assess_thermal_rejection_budget(thermal_budget(radiator_area_m2=0.4))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("radiator rejects" in f for f in result["findings"]))

    def test_uncategorized_line_refused(self):
        budget = thermal_budget()
        del budget["lines"][0]["maturity"]
        with self.assertRaises(ValueError):
            assess_thermal_rejection_budget(budget)

    def test_missing_key_rejected(self):
        budget = thermal_budget()
        del budget["sink_temperature_k"]
        with self.assertRaises(ValueError):
            assess_thermal_rejection_budget(budget)


class HeaterBudgetTests(unittest.TestCase):
    def test_nominal_heater_budget_is_compliant(self):
        result = assess_heater_power_budget(heater_budget())
        self.assertTrue(result["compliant"])

    def test_tracked_value_matches_the_roll_up(self):
        result = assess_heater_power_budget(heater_budget())
        expected = (34.0 * 1.10 + 18.0 * 1.05) * 1.15
        self.assertAlmostEqual(result["tracked_w"], expected, places=12)

    def test_tight_allocation_raises_a_finding(self):
        result = assess_heater_power_budget(heater_budget(allocation_w=40.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("heater demand" in f for f in result["findings"]))

    def test_missing_allocation_rejected(self):
        budget = heater_budget()
        del budget["allocation_w"]
        with self.assertRaises(ValueError):
            assess_heater_power_budget(budget)


class MassBudgetTests(unittest.TestCase):
    def test_nominal_mass_budget_is_compliant(self):
        result = assess_mass_budget(mass_budget())
        self.assertTrue(result["compliant"])

    def test_tracked_mass_matches_the_roll_up(self):
        result = assess_mass_budget(mass_budget())
        expected = (6.4 * 1.10 + 3.1 * 1.05 + 4.2 * 1.20) * 1.05
        self.assertAlmostEqual(result["tracked_kg"], expected, places=12)

    def test_tight_allocation_raises_a_finding(self):
        result = assess_mass_budget(mass_budget(allocation_kg=10.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("hardware mass" in f for f in result["findings"]))

    def test_non_mapping_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess_mass_budget(["lines"])


class AggregateTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "thermal": thermal_budget(),
            "heater_power": heater_budget(),
            "mass": mass_budget(),
        }
        spec.update(overrides)
        return spec

    def test_nominal_assessment_is_compliant(self):
        result = assess_budget_allocation(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tightest_budget_is_named(self):
        result = assess_budget_allocation(
            self._spec(heater_power=heater_budget(allocation_w=62.0))
        )
        self.assertEqual(result["tightest_budget"], "heater_power")

    def test_findings_aggregate_across_the_three_budgets(self):
        result = assess_budget_allocation(self._spec(
            thermal=thermal_budget(radiator_area_m2=0.4),
            heater_power=heater_budget(allocation_w=40.0),
            mass=mass_budget(allocation_kg=10.0),
        ))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 3)

    def test_missing_budget_rejected(self):
        spec = self._spec()
        del spec["mass"]
        with self.assertRaises(ValueError):
            assess_budget_allocation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_budget_allocation("thermal")


if __name__ == "__main__":
    unittest.main()

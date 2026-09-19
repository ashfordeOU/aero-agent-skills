"""Contract tests for the clause 4.7.3.3.1/4.7.3.3.2 fluid-quantity logic."""

import unittest

from e3301_fluid_lubrication_lubricant_quantity_logic import (
    DEFAULT_MAX_FILL_FRACTION,
    DEFAULT_QUANTITY_FACTOR,
    FLUID_CYCLE_FLOOR,
    FLUID_SPEED_FLOOR_M_S,
    MARGIN_TOLERANCE,
    absorption_loss_g,
    arrhenius_factor,
    assess_lubricant_quantity,
    consumption_loss_g,
    creep_loss_g,
    duty_indication,
    evaporation_loss_g,
    fill_fraction,
    loss_budget,
    required_charge_g,
    validate_fraction,
    validate_non_negative,
    validate_positive,
)

LOSSES = {
    "exposed_area_cm2": 10.0,
    "life_years": 15.0,
    "reference_rate_g_per_cm2_year": 0.002,
    "temperature_c": 40.0,
    "reference_temperature_c": 40.0,
    "activation_energy_kj_per_mol": 60.0,
    "wetted_perimeter_mm": 200.0,
    "creep_rate_g_per_mm_year": 0.0002,
    "barrier_effectiveness": 0.9,
    "retainer_mass_g": 8.0,
    "absorption_fraction": 0.15,
    "cycles": 5.0e7,
    "loss_per_million_cycles_g": 0.001,
}

DUTY = {
    "sliding_speed_m_s": 1.5,
    "required_cycles": 5.0e7,
    "temperature_c": (-20.0, 60.0),
    "fluid_temperature_c": (-60.0, 120.0),
}


def _spec(**overrides):
    spec = {
        "duty": dict(DUTY),
        "losses": dict(LOSSES),
        "operating_film_g": 0.5,
        "density_g_per_cm3": 1.9,
        "free_volume_cm3": 50.0,
        "reservoir_capacity_g": 6.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_validator_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 3), 3.0)

    def test_positive_validator_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_non_negative_validator_accepts_zero(self):
        self.assertAlmostEqual(validate_non_negative("x", 0), 0.0)

    def test_fraction_validator_accepts_unity(self):
        self.assertAlmostEqual(validate_fraction("x", 1.0), 1.0)

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction("x", 1.5)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative("x", True)


class ArrheniusTests(unittest.TestCase):
    def test_reference_temperature_gives_unity(self):
        self.assertAlmostEqual(arrhenius_factor(40.0, 40.0, 60.0), 1.0, places=12)

    def test_hotter_operation_raises_the_rate(self):
        self.assertGreater(arrhenius_factor(60.0, 40.0, 60.0), 1.0)

    def test_colder_operation_lowers_the_rate(self):
        self.assertLess(arrhenius_factor(20.0, 40.0, 60.0), 1.0)

    def test_the_factor_is_reciprocal_under_swapped_temperatures(self):
        forward = arrhenius_factor(60.0, 40.0, 60.0)
        reverse = arrhenius_factor(40.0, 60.0, 60.0)
        self.assertAlmostEqual(forward * reverse, 1.0, places=9)

    def test_a_twenty_kelvin_rise_is_a_few_fold(self):
        factor = arrhenius_factor(60.0, 40.0, 60.0)
        self.assertGreater(factor, 3.0)
        self.assertLess(factor, 5.0)

    def test_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_factor(60.0, 40.0, 0.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_factor(-300.0, 40.0, 60.0)


class LossTermTests(unittest.TestCase):
    def test_evaporation_matches_the_closed_form_at_reference(self):
        self.assertAlmostEqual(
            evaporation_loss_g(10.0, 15.0, 0.002, 40.0, 40.0, 60.0), 0.3, places=12
        )

    def test_evaporation_scales_with_exposed_area(self):
        small = evaporation_loss_g(10.0, 15.0, 0.002, 40.0, 40.0, 60.0)
        large = evaporation_loss_g(20.0, 15.0, 0.002, 40.0, 40.0, 60.0)
        self.assertAlmostEqual(large / small, 2.0, places=12)

    def test_zero_exposed_area_gives_no_evaporation(self):
        self.assertAlmostEqual(
            evaporation_loss_g(0.0, 15.0, 0.002, 40.0, 40.0, 60.0), 0.0
        )

    def test_creep_is_reduced_by_the_barrier(self):
        unbarriered = creep_loss_g(200.0, 15.0, 0.0002, 0.0)
        barriered = creep_loss_g(200.0, 15.0, 0.0002, 0.9)
        self.assertAlmostEqual(barriered / unbarriered, 0.1, places=12)

    def test_a_perfect_barrier_removes_the_creep_term(self):
        self.assertAlmostEqual(creep_loss_g(200.0, 15.0, 0.0002, 1.0), 0.0)

    def test_barrier_effectiveness_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            creep_loss_g(200.0, 15.0, 0.0002, 1.2)

    def test_absorption_is_a_fraction_of_the_retainer_mass(self):
        self.assertAlmostEqual(absorption_loss_g(8.0, 0.15), 1.2, places=12)

    def test_negative_retainer_mass_rejected(self):
        with self.assertRaises(ValueError):
            absorption_loss_g(-1.0, 0.15)

    def test_consumption_is_per_million_cycles(self):
        self.assertAlmostEqual(consumption_loss_g(5.0e7, 0.001), 0.05, places=12)

    def test_zero_cycles_consume_nothing(self):
        self.assertAlmostEqual(consumption_loss_g(0.0, 0.001), 0.0)


class LossBudgetTests(unittest.TestCase):
    def test_all_four_terms_are_reported(self):
        budget = loss_budget(LOSSES)
        for key in ("evaporation_g", "creep_g", "absorption_g", "consumption_g"):
            self.assertIn(key, budget)

    def test_total_is_the_sum_of_the_terms(self):
        budget = loss_budget(LOSSES)
        self.assertAlmostEqual(
            budget["total_g"],
            budget["evaporation_g"]
            + budget["creep_g"]
            + budget["absorption_g"]
            + budget["consumption_g"],
            places=12,
        )

    def test_budget_matches_the_hand_calculation(self):
        self.assertAlmostEqual(loss_budget(LOSSES)["total_g"], 1.61, places=9)

    def test_missing_loss_key_rejected(self):
        spec = dict(LOSSES)
        del spec["retainer_mass_g"]
        with self.assertRaises(ValueError):
            loss_budget(spec)

    def test_non_mapping_loss_spec_rejected(self):
        with self.assertRaises(ValueError):
            loss_budget(["exposed_area_cm2"])


class ChargeTests(unittest.TestCase):
    def test_charge_applies_the_quantity_factor(self):
        self.assertAlmostEqual(required_charge_g(0.5, 1.61), 4.22, places=9)

    def test_default_factor_is_a_doubling(self):
        self.assertAlmostEqual(DEFAULT_QUANTITY_FACTOR, 2.0)

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_charge_g(0.5, 1.61, 0.8)

    def test_zero_operating_film_rejected(self):
        with self.assertRaises(ValueError):
            required_charge_g(0.0, 1.61)

    def test_fill_fraction_uses_density_and_free_volume(self):
        self.assertAlmostEqual(fill_fraction(4.22, 1.9, 50.0), 4.22 / 95.0, places=12)

    def test_zero_free_volume_rejected(self):
        with self.assertRaises(ValueError):
            fill_fraction(4.22, 1.9, 0.0)


class DutyIndicationTests(unittest.TestCase):
    def test_fast_high_cycle_duty_is_indicated(self):
        self.assertTrue(duty_indication(DUTY)["indicated"])

    def test_slow_low_cycle_duty_is_counter_indicated(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 0.01
        duty["required_cycles"] = 500.0
        result = duty_indication(duty)
        self.assertFalse(result["indicated"])
        self.assertIn("dry film", result["findings"][0])

    def test_high_cycle_alone_keeps_the_duty_in_the_fluid_domain(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 0.01
        self.assertTrue(duty_indication(duty)["indicated"])

    def test_speed_exactly_on_the_floor_counts_as_fast(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = FLUID_SPEED_FLOOR_M_S
        duty["required_cycles"] = 100.0
        self.assertTrue(duty_indication(duty)["fast_duty"])

    def test_cycles_exactly_on_the_floor_count_as_high(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 0.001
        duty["required_cycles"] = FLUID_CYCLE_FLOOR
        self.assertTrue(duty_indication(duty)["high_cycle_duty"])

    def test_uncovered_temperature_range_is_flagged(self):
        duty = dict(DUTY)
        duty["fluid_temperature_c"] = (-10.0, 80.0)
        result = duty_indication(duty)
        self.assertFalse(result["temperature_covered"])
        self.assertFalse(result["indicated"])

    def test_coincident_temperature_limits_are_covered(self):
        duty = dict(DUTY)
        duty["fluid_temperature_c"] = (-20.0, 60.0)
        self.assertTrue(duty_indication(duty)["temperature_covered"])

    def test_inverted_duty_range_rejected(self):
        duty = dict(DUTY)
        duty["temperature_c"] = (60.0, -20.0)
        with self.assertRaises(ValueError):
            duty_indication(duty)

    def test_missing_duty_key_rejected(self):
        duty = dict(DUTY)
        del duty["fluid_temperature_c"]
        with self.assertRaises(ValueError):
            duty_indication(duty)


class AssessmentTests(unittest.TestCase):
    def test_sound_design_is_compliant(self):
        result = assess_lubricant_quantity(_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_required_charge_is_reported(self):
        result = assess_lubricant_quantity(_spec())
        self.assertAlmostEqual(result["required_charge_g"], 4.22, places=9)

    def test_absorption_dominates_this_loss_budget(self):
        self.assertEqual(assess_lubricant_quantity(_spec())["dominant_loss"], "absorption")

    def test_hot_operation_can_make_evaporation_dominant(self):
        losses = dict(LOSSES)
        losses["temperature_c"] = 100.0
        result = assess_lubricant_quantity(_spec(losses=losses))
        self.assertEqual(result["dominant_loss"], "evaporation")

    def test_small_reservoir_is_flagged(self):
        result = assess_lubricant_quantity(_spec(reservoir_capacity_g=2.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("reservoir capacity" in text for text in result["findings"]))

    def test_capacity_exactly_equal_to_the_charge_is_compliant(self):
        baseline = assess_lubricant_quantity(_spec())
        result = assess_lubricant_quantity(
            _spec(reservoir_capacity_g=baseline["required_charge_g"])
        )
        self.assertTrue(result["compliant"])

    def test_over_filling_the_free_volume_is_flagged(self):
        result = assess_lubricant_quantity(
            _spec(free_volume_cm3=5.0, reservoir_capacity_g=20.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("churn" in text for text in result["findings"]))

    def test_fill_fraction_exactly_on_the_limit_is_compliant(self):
        baseline = assess_lubricant_quantity(_spec())
        result = assess_lubricant_quantity(
            _spec(max_fill_fraction=baseline["fill_fraction"])
        )
        self.assertTrue(result["compliant"])

    def test_removing_the_barrier_raises_the_charge(self):
        losses = dict(LOSSES)
        losses["barrier_effectiveness"] = 0.0
        raised = assess_lubricant_quantity(_spec(losses=losses, reservoir_capacity_g=20.0))
        baseline = assess_lubricant_quantity(_spec(reservoir_capacity_g=20.0))
        self.assertGreater(raised["required_charge_g"], baseline["required_charge_g"])

    def test_counter_indicated_duty_reaches_the_findings(self):
        duty = dict(DUTY)
        duty["sliding_speed_m_s"] = 0.001
        duty["required_cycles"] = 100.0
        result = assess_lubricant_quantity(_spec(duty=duty))
        self.assertFalse(result["compliant"])

    def test_default_max_fill_is_a_minority_of_the_free_volume(self):
        self.assertLess(DEFAULT_MAX_FILL_FRACTION, 0.5)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["free_volume_cm3"]
        with self.assertRaises(ValueError):
            assess_lubricant_quantity(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lubricant_quantity(["duty"])

    def test_margin_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()

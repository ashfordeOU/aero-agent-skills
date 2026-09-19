"""Contract test for the radiation degradation-assessment leaf (stdlib unittest)."""

import unittest

from q7006_degradation_assessment_logic import (
    GROWTH_MODELS,
    MAX_EXTRAPOLATION_FACTOR,
    assess_degradation,
    change_is_measurable,
    degradation_delta,
    extrapolate_degradation,
    extrapolation_factor,
    margin_to_criterion,
    meets_criterion,
    relative_degradation,
    worst_case_degradation,
)


def record(**kw):
    item = {
        "property": "solar-absorptance",
        "direction": "increase-is-degradation",
        "pristine_value": 0.200,
        "exposed_value": 0.260,
        "expanded_uncertainty": 0.010,
        "acceptance_criterion": 0.100,
        "end_of_life_criterion": 0.150,
        "test_exposure": 1000.0,
        "end_of_life_exposure": 2000.0,
        "growth_model": "square-root",
    }
    item.update(kw)
    return item


class TestDelta(unittest.TestCase):
    def test_darkening_is_a_positive_degradation(self):
        self.assertAlmostEqual(
            degradation_delta(0.20, 0.26, "increase-is-degradation"), 0.06, places=9
        )

    def test_a_loss_of_transmittance_is_a_positive_degradation(self):
        self.assertAlmostEqual(
            degradation_delta(0.90, 0.80, "decrease-is-degradation"), 0.10, places=9
        )

    def test_a_property_moving_the_benign_way_degrades_negatively(self):
        self.assertAlmostEqual(
            degradation_delta(0.20, 0.18, "increase-is-degradation"), -0.02, places=9
        )

    def test_an_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            degradation_delta(0.20, 0.26, "bigger-is-worse")

    def test_a_non_numeric_value_raises(self):
        with self.assertRaises(ValueError):
            degradation_delta("0.20", 0.26, "increase-is-degradation")

    def test_relative_degradation_is_a_fraction_of_the_pristine_value(self):
        self.assertAlmostEqual(
            relative_degradation(0.20, 0.26, "increase-is-degradation"), 0.30, places=9
        )

    def test_a_zero_pristine_value_has_no_relative_degradation(self):
        with self.assertRaises(ValueError):
            relative_degradation(0.0, 0.26, "increase-is-degradation")


class TestUncertainty(unittest.TestCase):
    def test_the_worst_case_adds_the_expanded_uncertainty(self):
        self.assertAlmostEqual(worst_case_degradation(0.06, 0.01), 0.07, places=9)

    def test_a_change_larger_than_its_uncertainty_is_measurable(self):
        self.assertTrue(change_is_measurable(0.06, 0.01))

    def test_a_change_exactly_equal_to_its_uncertainty_is_measurable(self):
        self.assertTrue(change_is_measurable(0.01, 0.01))

    def test_a_change_inside_its_uncertainty_is_not_measurable(self):
        self.assertFalse(change_is_measurable(0.002, 0.01))

    def test_a_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            worst_case_degradation(0.06, -0.01)


class TestExtrapolation(unittest.TestCase):
    def test_the_factor_is_the_exposure_ratio(self):
        self.assertAlmostEqual(extrapolation_factor(1000.0, 5000.0), 5.0, places=9)

    def test_a_zero_tested_exposure_raises(self):
        with self.assertRaises(ValueError):
            extrapolation_factor(0.0, 5000.0)

    def test_a_proportional_model_scales_with_the_exposure(self):
        self.assertAlmostEqual(
            extrapolate_degradation(0.06, 1000.0, 4000.0, "linear"), 0.24, places=9
        )

    def test_a_square_root_model_scales_with_the_root_of_the_exposure(self):
        self.assertAlmostEqual(
            extrapolate_degradation(0.06, 1000.0, 4000.0, "square-root"),
            0.12,
            places=9,
        )

    def test_a_saturated_model_does_not_grow(self):
        self.assertAlmostEqual(
            extrapolate_degradation(0.06, 1000.0, 9000.0, "saturated"), 0.06, places=9
        )

    def test_every_declared_model_is_usable(self):
        for model in GROWTH_MODELS:
            self.assertIsInstance(
                extrapolate_degradation(0.06, 1000.0, 2000.0, model), float
            )

    def test_an_unknown_growth_model_raises(self):
        with self.assertRaises(ValueError):
            extrapolate_degradation(0.06, 1000.0, 2000.0, "exponential")


class TestCriteria(unittest.TestCase):
    def test_a_degradation_inside_its_criterion_passes(self):
        self.assertTrue(meets_criterion(0.07, 0.10))

    def test_a_degradation_exactly_on_its_criterion_passes(self):
        self.assertTrue(meets_criterion(0.10, 0.10))

    def test_a_degradation_past_its_criterion_fails(self):
        self.assertFalse(meets_criterion(0.12, 0.10))

    def test_the_margin_is_what_is_left_of_the_criterion(self):
        self.assertAlmostEqual(margin_to_criterion(0.07, 0.10), 0.03, places=9)


class TestAssessment(unittest.TestCase):
    def test_a_compliant_property_is_accepted(self):
        result = assess_degradation(record())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["degradation"], 0.06, places=9)

    def test_the_end_of_life_value_uses_the_declared_model(self):
        result = assess_degradation(record(end_of_life_exposure=4000.0))
        self.assertAlmostEqual(result["end_of_life_degradation"], 0.12, places=9)
        self.assertAlmostEqual(result["worst_case_end_of_life"], 0.13, places=9)

    def test_a_darkening_past_the_acceptance_criterion_is_rejected(self):
        result = assess_degradation(record(exposed_value=0.330))
        self.assertIn(
            "end-of-test-degradation-exceeds-the-acceptance-criterion",
            result["findings"],
        )
        self.assertFalse(result["accepted"])

    def test_a_criterion_met_only_without_the_uncertainty_is_a_finding(self):
        result = assess_degradation(
            record(exposed_value=0.295, acceptance_criterion=0.100)
        )
        self.assertIn(
            "end-of-test-degradation-exceeds-the-acceptance-criterion",
            result["findings"],
        )
        self.assertIn(
            "acceptance-criterion-met-only-without-the-uncertainty",
            result["findings"],
        )
        self.assertFalse(result["accepted"])

    def test_a_breach_wider_than_the_uncertainty_is_not_blamed_on_it(self):
        result = assess_degradation(
            record(exposed_value=0.400, acceptance_criterion=0.100)
        )
        self.assertNotIn(
            "acceptance-criterion-met-only-without-the-uncertainty",
            result["findings"],
        )

    def test_a_worst_case_exactly_on_the_criterion_is_accepted(self):
        result = assess_degradation(
            record(exposed_value=0.290, acceptance_criterion=0.100)
        )
        self.assertNotIn(
            "end-of-test-degradation-exceeds-the-acceptance-criterion",
            result["findings"],
        )

    def test_an_end_of_life_breach_is_reported_separately(self):
        result = assess_degradation(
            record(end_of_life_exposure=6000.0, growth_model="linear")
        )
        self.assertIn(
            "end-of-life-degradation-exceeds-its-criterion", result["findings"]
        )
        self.assertFalse(result["accepted"])

    def test_a_long_extrapolation_is_flagged_as_a_modelling_statement(self):
        result = assess_degradation(
            record(
                end_of_life_exposure=1000.0 * (MAX_EXTRAPOLATION_FACTOR + 5.0),
                growth_model="saturated",
                end_of_life_criterion=0.150,
            )
        )
        self.assertIn(
            "extrapolation-beyond-the-tested-exposure-limit", result["findings"]
        )

    def test_an_extrapolation_exactly_on_the_factor_limit_is_not_flagged(self):
        result = assess_degradation(
            record(
                end_of_life_exposure=1000.0 * MAX_EXTRAPOLATION_FACTOR,
                growth_model="saturated",
            )
        )
        self.assertNotIn(
            "extrapolation-beyond-the-tested-exposure-limit", result["findings"]
        )

    def test_an_unmeasurable_change_is_a_finding(self):
        result = assess_degradation(
            record(exposed_value=0.2005, expanded_uncertainty=0.010)
        )
        self.assertIn("change-inside-the-measurement-uncertainty", result["findings"])

    def test_a_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_degradation(["solar-absorptance"])

    def test_a_missing_exposure_pair_raises(self):
        item = record()
        del item["test_exposure"]
        with self.assertRaises(ValueError):
            assess_degradation(item)


if __name__ == "__main__":
    unittest.main()

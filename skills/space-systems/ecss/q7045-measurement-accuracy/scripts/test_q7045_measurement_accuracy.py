"""Contract tests for the mechanical-test measurement-accuracy budget.

The cases follow an error from the channel it is measured on to the property
it lands in: the limit each channel is graded against, the standard
uncertainty a digital step or a drift band contributes, the quadrature
combination, the doubling a diameter takes on its way into an area, and the
expanded figure the reported property has to come in under.
"""

import math
import unittest

from q7045_measurement_accuracy_logic import (
    DEFAULT_COVERAGE_FACTOR,
    DEFAULT_TEMPERATURE_LIMIT_K,
    area_relative_uncertainty_pct,
    assess_measurement_accuracy,
    channel_findings,
    combine_in_quadrature,
    dominant_contributor,
    expanded_uncertainty,
    modulus_relative_uncertainty_pct,
    relative_percent,
    rectangular_standard_uncertainty,
    resolution_standard_uncertainty,
    stress_relative_uncertainty_pct,
)


def _spec(**overrides):
    spec = {
        "channels": {
            "force": {"relative_pct": 0.5},
            "diameter": {"relative_pct": 0.1},
            "strain": {"relative_pct": 0.5},
            "gauge_length": {"relative_pct": 0.2},
            "temperature": {"absolute_k": 1.0},
        },
        "property": "stress",
        "target_expanded_pct": 2.0,
    }
    spec.update(overrides)
    return spec


class ContributionTests(unittest.TestCase):
    def test_resolution_uses_two_root_three(self):
        self.assertAlmostEqual(
            resolution_standard_uncertainty(0.12), 0.12 / (2.0 * math.sqrt(3.0)), places=12
        )

    def test_resolution_of_zero_contributes_nothing(self):
        self.assertAlmostEqual(resolution_standard_uncertainty(0.0), 0.0, places=12)

    def test_rectangular_band_uses_root_three(self):
        self.assertAlmostEqual(
            rectangular_standard_uncertainty(0.3), 0.3 / math.sqrt(3.0), places=12
        )

    def test_negative_resolution_rejected(self):
        with self.assertRaises(ValueError):
            resolution_standard_uncertainty(-0.1)

    def test_text_half_width_rejected(self):
        with self.assertRaises(ValueError):
            rectangular_standard_uncertainty("0.3")


class QuadratureTests(unittest.TestCase):
    def test_three_four_five_triangle(self):
        self.assertAlmostEqual(combine_in_quadrature([3.0, 4.0]), 5.0, places=12)

    def test_quadrature_is_below_the_arithmetic_sum(self):
        components = [0.4, 0.3, 0.2]
        self.assertLess(combine_in_quadrature(components), sum(components))

    def test_single_component_passes_through(self):
        self.assertAlmostEqual(combine_in_quadrature([0.7]), 0.7, places=12)

    def test_empty_component_set_rejected(self):
        with self.assertRaises(ValueError):
            combine_in_quadrature([])

    def test_negative_component_rejected(self):
        with self.assertRaises(ValueError):
            combine_in_quadrature([0.4, -0.1])

    def test_default_coverage_factor_doubles(self):
        self.assertAlmostEqual(expanded_uncertainty(0.5), 1.0, places=12)
        self.assertAlmostEqual(DEFAULT_COVERAGE_FACTOR, 2.0, places=12)

    def test_coverage_factor_outside_one_to_three_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(0.5, 4.0)


class PropagationTests(unittest.TestCase):
    def test_area_doubles_the_diameter_uncertainty(self):
        self.assertAlmostEqual(area_relative_uncertainty_pct(0.15), 0.30, places=12)

    def test_stress_combines_force_and_area(self):
        value = stress_relative_uncertainty_pct(0.3, 0.2)
        self.assertAlmostEqual(value, math.sqrt(0.3 ** 2 + 0.4 ** 2), places=12)

    def test_modulus_carries_four_terms(self):
        value = modulus_relative_uncertainty_pct(0.3, 0.4, 0.2, 0.1)
        expected = math.sqrt(0.3 ** 2 + 0.4 ** 2 + 0.2 ** 2 + 0.2 ** 2)
        self.assertAlmostEqual(value, expected, places=12)

    def test_modulus_is_never_below_its_largest_term(self):
        value = modulus_relative_uncertainty_pct(0.9, 0.1, 0.1, 0.0)
        self.assertGreater(value, 0.9)

    def test_relative_percent_of_a_reading(self):
        self.assertAlmostEqual(relative_percent(2.0, 400.0), 0.5, places=12)

    def test_relative_percent_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            relative_percent(2.0, 0.0)


class ChannelGradingTests(unittest.TestCase):
    def test_a_channel_inside_its_limit_raises_nothing(self):
        result = channel_findings({"force": {"relative_pct": 0.5}})
        self.assertEqual(result["findings"], [])

    def test_a_channel_outside_its_limit_is_named(self):
        result = channel_findings({"force": {"relative_pct": 1.5}})
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("force", result["findings"][0])

    def test_a_channel_exactly_on_its_limit_is_accepted(self):
        result = channel_findings({"force": {"relative_pct": 1.0}})
        self.assertAlmostEqual(result["graded"]["force"]["error"], 1.0, places=12)
        self.assertTrue(result["graded"]["force"]["within"])

    def test_temperature_is_graded_in_kelvin_not_percent(self):
        result = channel_findings({"soak": {"absolute_k": 1.0}})
        self.assertEqual(result["graded"]["soak"]["unit"], "K")
        self.assertAlmostEqual(
            result["graded"]["soak"]["limit"], DEFAULT_TEMPERATURE_LIMIT_K, places=12
        )

    def test_temperature_outside_its_band_is_a_finding(self):
        result = channel_findings({"soak": {"absolute_k": 3.5}})
        self.assertTrue(result["findings"])

    def test_channel_without_a_declared_limit_rejected(self):
        with self.assertRaises(ValueError):
            channel_findings({"humidity": {"relative_pct": 0.2}})

    def test_channel_without_an_error_rejected(self):
        with self.assertRaises(ValueError):
            channel_findings({"force": {}})

    def test_empty_channel_set_rejected(self):
        with self.assertRaises(ValueError):
            channel_findings({})


class DominantContributorTests(unittest.TestCase):
    def test_largest_term_wins(self):
        self.assertEqual(dominant_contributor({"force": 0.3, "area": 0.7}), "area")

    def test_tie_resolves_on_the_first_name_in_order(self):
        self.assertEqual(dominant_contributor({"b": 0.5, "a": 0.5}), "a")

    def test_empty_budget_rejected(self):
        with self.assertRaises(ValueError):
            dominant_contributor({})


class AssessmentTests(unittest.TestCase):
    def test_a_clean_chain_supports_the_stress(self):
        result = assess_measurement_accuracy(_spec())
        self.assertTrue(result["supported"])
        self.assertEqual(result["findings"], [])

    def test_the_area_term_can_dominate_a_small_force_error(self):
        result = assess_measurement_accuracy(
            _spec(channels=dict(_spec()["channels"], diameter={"relative_pct": 0.4}))
        )
        self.assertEqual(result["dominant"], "area-from-diameter")

    def test_a_modulus_carries_more_terms_than_a_stress(self):
        stress = assess_measurement_accuracy(_spec())
        modulus = assess_measurement_accuracy(_spec(property="modulus"))
        self.assertGreater(
            modulus["combined_standard_pct"], stress["combined_standard_pct"]
        )

    def test_a_tight_target_is_not_supported(self):
        result = assess_measurement_accuracy(_spec(target_expanded_pct=0.5))
        self.assertFalse(result["supported"])

    def test_an_out_of_limit_channel_blocks_the_property(self):
        result = assess_measurement_accuracy(
            _spec(channels=dict(_spec()["channels"], force={"relative_pct": 2.0}))
        )
        self.assertFalse(result["supported"])

    def test_resolution_terms_enlarge_the_budget(self):
        plain = assess_measurement_accuracy(_spec())
        with_res = assess_measurement_accuracy(
            _spec(resolution_contributions={"force-display": 0.2})
        )
        self.assertGreater(
            with_res["combined_standard_pct"], plain["combined_standard_pct"]
        )

    def test_drift_terms_enlarge_the_budget(self):
        plain = assess_measurement_accuracy(_spec())
        with_drift = assess_measurement_accuracy(_spec(drift_half_widths={"amplifier": 0.1}))
        self.assertGreater(
            with_drift["combined_standard_pct"], plain["combined_standard_pct"]
        )

    def test_expanded_is_the_combined_times_the_coverage_factor(self):
        result = assess_measurement_accuracy(_spec(coverage_factor=3.0))
        self.assertAlmostEqual(
            result["expanded_pct"], 3.0 * result["combined_standard_pct"], places=12
        )

    def test_unknown_property_rejected(self):
        with self.assertRaises(ValueError):
            assess_measurement_accuracy(_spec(property="hardness"))

    def test_missing_channel_for_the_property_rejected(self):
        spec = _spec()
        del spec["channels"]["diameter"]
        with self.assertRaises(ValueError):
            assess_measurement_accuracy(spec)

    def test_missing_key_rejected(self):
        spec = _spec()
        del spec["target_expanded_pct"]
        with self.assertRaises(ValueError):
            assess_measurement_accuracy(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_measurement_accuracy("stress")


if __name__ == "__main__":
    unittest.main()

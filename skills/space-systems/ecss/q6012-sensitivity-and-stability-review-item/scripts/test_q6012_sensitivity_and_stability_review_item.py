"""Contract tests for the clause 7.3.5 sensitivity and stability review item."""

import copy
import math
import unittest

from q6012_sensitivity_and_stability_review_item_logic import (
    SPREAD_TOLERANCE,
    STABILITY_TOLERANCE,
    assess_sensitivity,
    assess_stability_sweep,
    mu_factor,
    normalised_sensitivity,
    review_sensitivity_and_stability,
    root_sum_square,
    scattering_determinant,
    rollett_k,
    source_contributions,
    stability_at_frequency,
    to_complex,
)

BAND = (8.0, 12.0)
SPAN_FACTOR = 3.0

# Real-valued scattering set: s11 = 0.5, s22 = 0.4, s12 = 0.05, s21 = 4.0 gives
# a zero determinant and K = 0.59 / 0.4 = 1.475, so the point is unconditionally
# stable. Raising s12 to 0.2 drives K below one.
def sweep_point(frequency_ghz, s12=0.05):
    """Return one swept stability point at the given reverse transmission."""
    return {
        "frequency_ghz": frequency_ghz,
        "s11": (0.5, 0.0),
        "s12": (s12, 0.0),
        "s21": (4.0, 0.0),
        "s22": (0.4, 0.0),
    }


SWEEP = [sweep_point(f) for f in (1.0, 2.0, 8.0, 10.0, 12.0, 20.0, 40.0)]

PARAMETER = {
    "name": "saturated_output_power_mw",
    "nominal": 500.0,
    "allowed_relative_spread": 0.12,
    "sources": [
        {
            "name": "process",
            "relative_input_change": 0.10,
            "perturbed_output": 530.0,
            "tolerance": 0.10,
        },
        {
            "name": "temperature",
            "relative_input_change": 0.20,
            "perturbed_output": 480.0,
            "tolerance": 0.20,
        },
        {
            "name": "supply",
            "relative_input_change": 0.05,
            "perturbed_output": 512.5,
            "tolerance": 0.05,
        },
    ],
}


def package(**overrides):
    """Return a clean sensitivity-and-stability package with overrides applied."""
    base = {
        "parameters": [copy.deepcopy(PARAMETER)],
        "required_variation_sources": ["process", "temperature", "supply"],
        "stability": {
            "band_ghz": BAND,
            "span_factor": SPAN_FACTOR,
            "required_k": 1.0,
            "sweep": copy.deepcopy(SWEEP),
        },
    }
    base.update(copy.deepcopy(overrides))
    return base


class ToComplexTests(unittest.TestCase):
    def test_polar_pair_becomes_a_phasor(self):
        value = to_complex("s11", (1.0, 90.0))
        self.assertAlmostEqual(value.real, 0.0, places=9)
        self.assertAlmostEqual(value.imag, 1.0, places=9)

    def test_zero_angle_is_purely_real(self):
        value = to_complex("s11", (0.5, 0.0))
        self.assertAlmostEqual(value.real, 0.5, places=9)
        self.assertAlmostEqual(value.imag, 0.0, places=9)

    def test_negative_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            to_complex("s11", (-0.5, 0.0))

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            to_complex("s11", (0.5,))

    def test_non_finite_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            to_complex("s11", (float("inf"), 0.0))


class StabilityFactorTests(unittest.TestCase):
    def test_determinant_of_the_stable_set_is_zero(self):
        self.assertAlmostEqual(abs(scattering_determinant(sweep_point(10.0))), 0.0, places=9)

    def test_rollett_k_of_the_stable_set(self):
        self.assertAlmostEqual(rollett_k(sweep_point(10.0)), 0.59 / 0.4, places=9)

    def test_mu_factor_agrees_with_k_on_stability(self):
        point = sweep_point(10.0)
        self.assertGreater(rollett_k(point), 1.0)
        self.assertAlmostEqual(mu_factor(point), 0.75 / 0.6, places=9)

    def test_raising_reverse_transmission_makes_the_point_unstable(self):
        point = sweep_point(10.0, s12=0.2)
        self.assertAlmostEqual(rollett_k(point), 0.95 / 1.6, places=9)
        self.assertAlmostEqual(mu_factor(point), 0.5, places=9)

    def test_k_and_mu_fail_together(self):
        point = sweep_point(10.0, s12=0.2)
        verdict = stability_at_frequency(point)
        self.assertFalse(verdict["unconditionally_stable"])
        self.assertLess(mu_factor(point), 1.0)

    def test_point_landing_exactly_on_k_equals_one_is_not_cleared(self):
        point = {
            "frequency_ghz": 10.0,
            "s11": (0.0, 0.0),
            "s12": (0.5, 0.0),
            "s21": (2.0, 0.0),
            "s22": (0.0, 0.0),
        }
        verdict = stability_at_frequency(point)
        self.assertAlmostEqual(verdict["k"], 1.0, places=9)
        self.assertAlmostEqual(verdict["determinant_magnitude"], 1.0, places=9)
        self.assertFalse(verdict["k_clear"])
        self.assertFalse(verdict["determinant_clear"])

    def test_zero_reverse_transmission_rejected(self):
        with self.assertRaises(ValueError):
            rollett_k(sweep_point(10.0, s12=0.0))

    def test_missing_scattering_entry_rejected(self):
        point = sweep_point(10.0)
        point.pop("s22")
        with self.assertRaises(ValueError):
            rollett_k(point)

    def test_required_k_below_one_rejected(self):
        with self.assertRaises(ValueError):
            stability_at_frequency(sweep_point(10.0), required_k=0.9)

    def test_raised_required_k_can_fail_a_textbook_stable_point(self):
        verdict = stability_at_frequency(sweep_point(10.0), required_k=2.0)
        self.assertFalse(verdict["unconditionally_stable"])
        self.assertTrue(verdict["determinant_clear"])

    def test_stability_tolerance_is_small_and_positive(self):
        self.assertGreater(STABILITY_TOLERANCE, 0.0)
        self.assertLess(STABILITY_TOLERANCE, 1e-6)


class SensitivityCoefficientTests(unittest.TestCase):
    def test_coefficient_is_fractional_move_per_fractional_move(self):
        self.assertAlmostEqual(normalised_sensitivity(500.0, 530.0, 0.10), 0.6, places=9)

    def test_negative_coefficient_for_an_output_that_falls(self):
        self.assertAlmostEqual(normalised_sensitivity(500.0, 480.0, 0.20), -0.2, places=9)

    def test_unmoved_output_gives_a_zero_coefficient(self):
        self.assertAlmostEqual(normalised_sensitivity(500.0, 500.0, 0.10), 0.0, places=9)

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            normalised_sensitivity(0.0, 10.0, 0.1)

    def test_zero_input_change_rejected(self):
        with self.assertRaises(ValueError):
            normalised_sensitivity(500.0, 530.0, 0.0)

    def test_root_sum_square_is_not_an_arithmetic_sum(self):
        self.assertAlmostEqual(root_sum_square([0.03, 0.04]), 0.05, places=9)

    def test_root_sum_square_of_one_value_is_its_magnitude(self):
        self.assertAlmostEqual(root_sum_square([-0.04]), 0.04, places=9)

    def test_root_sum_square_rejects_an_empty_sequence(self):
        with self.assertRaises(ValueError):
            root_sum_square([])

    def test_contributions_weight_each_coefficient_by_its_tolerance(self):
        records = source_contributions(500.0, PARAMETER["sources"])
        by_name = dict((record["name"], record) for record in records)
        self.assertAlmostEqual(by_name["process"]["contribution"], 0.06, places=9)
        self.assertAlmostEqual(by_name["temperature"]["contribution"], -0.04, places=9)
        self.assertAlmostEqual(by_name["supply"]["contribution"], 0.025, places=9)

    def test_duplicate_variation_source_rejected(self):
        sources = copy.deepcopy(PARAMETER["sources"])
        sources.append(copy.deepcopy(sources[0]))
        with self.assertRaises(ValueError):
            source_contributions(500.0, sources)

    def test_non_positive_tolerance_rejected(self):
        sources = copy.deepcopy(PARAMETER["sources"])
        sources[0]["tolerance"] = 0.0
        with self.assertRaises(ValueError):
            source_contributions(500.0, sources)

    def test_spread_tolerance_is_small_and_positive(self):
        self.assertGreater(SPREAD_TOLERANCE, 0.0)
        self.assertLess(SPREAD_TOLERANCE, 1e-6)


class AssessSensitivityTests(unittest.TestCase):
    def test_combined_spread_is_the_root_sum_square(self):
        record = assess_sensitivity(PARAMETER, ["process", "temperature", "supply"])
        expected = math.sqrt(0.06 ** 2 + 0.04 ** 2 + 0.025 ** 2)
        self.assertAlmostEqual(record["relative_spread"], expected, places=9)
        self.assertTrue(record["within_allowance"])

    def test_dominant_source_is_the_largest_contribution_by_magnitude(self):
        record = assess_sensitivity(PARAMETER)
        self.assertEqual(record["dominant_source"], "process")

    def test_spread_above_the_allowance_is_a_finding(self):
        tight = dict(copy.deepcopy(PARAMETER), allowed_relative_spread=0.05)
        record = assess_sensitivity(tight)
        self.assertFalse(record["within_allowance"])
        self.assertTrue(any("exceeds the allowance" in item for item in record["findings"]))

    def test_spread_landing_exactly_on_the_allowance_is_within_it(self):
        parameter = {
            "name": "gain_linear",
            "nominal": 100.0,
            "allowed_relative_spread": 0.05,
            "sources": [
                {
                    "name": "process",
                    "relative_input_change": 0.10,
                    "perturbed_output": 103.0,
                    "tolerance": 0.10,
                },
                {
                    "name": "temperature",
                    "relative_input_change": 0.10,
                    "perturbed_output": 104.0,
                    "tolerance": 0.10,
                },
            ],
        }
        record = assess_sensitivity(parameter)
        self.assertAlmostEqual(record["relative_spread"], 0.05, places=9)
        self.assertTrue(record["within_allowance"])

    def test_unmoved_source_is_flagged_as_never_applied(self):
        parameter = copy.deepcopy(PARAMETER)
        parameter["sources"][2]["perturbed_output"] = 500.0
        record = assess_sensitivity(parameter)
        self.assertTrue(any("moved the output by nothing" in item for item in record["findings"]))

    def test_required_source_never_exercised_is_a_finding(self):
        parameter = copy.deepcopy(PARAMETER)
        parameter["sources"] = parameter["sources"][:2]
        record = assess_sensitivity(parameter, ["process", "temperature", "supply"])
        self.assertTrue(any("never exercised" in item for item in record["findings"]))

    def test_non_positive_allowance_rejected(self):
        parameter = dict(copy.deepcopy(PARAMETER), allowed_relative_spread=0.0)
        with self.assertRaises(ValueError):
            assess_sensitivity(parameter)

    def test_parameter_without_sources_rejected(self):
        parameter = copy.deepcopy(PARAMETER)
        parameter["sources"] = []
        with self.assertRaises(ValueError):
            assess_sensitivity(parameter)


class AssessStabilitySweepTests(unittest.TestCase):
    def test_clean_sweep_has_no_findings(self):
        verdict = assess_stability_sweep(SWEEP, BAND, SPAN_FACTOR)
        self.assertTrue(verdict["sweep_clean"])
        self.assertEqual(verdict["unstable_frequencies_ghz"], [])

    def test_minimum_k_is_reported(self):
        verdict = assess_stability_sweep(SWEEP, BAND, SPAN_FACTOR)
        self.assertAlmostEqual(verdict["minimum_k"], 0.59 / 0.4, places=9)

    def test_one_unstable_point_is_named(self):
        sweep = copy.deepcopy(SWEEP)
        sweep[1] = sweep_point(2.0, s12=0.2)
        verdict = assess_stability_sweep(sweep, BAND, SPAN_FACTOR)
        self.assertEqual(verdict["unstable_frequencies_ghz"], [2.0])
        self.assertFalse(verdict["sweep_clean"])

    def test_sweep_stopping_at_the_band_edges_is_a_coverage_finding(self):
        sweep = [sweep_point(f) for f in (8.0, 10.0, 12.0)]
        verdict = assess_stability_sweep(sweep, BAND, SPAN_FACTOR)
        self.assertFalse(verdict["sweep_clean"])
        self.assertEqual(len(verdict["findings"]), 2)

    def test_low_side_shortfall_is_reported_on_its_own(self):
        sweep = [sweep_point(f) for f in (5.0, 10.0, 40.0)]
        verdict = assess_stability_sweep(sweep, BAND, SPAN_FACTOR)
        self.assertTrue(any("low-frequency" in item for item in verdict["findings"]))
        self.assertFalse(any("out-of-band" in item for item in verdict["findings"]))

    def test_sweep_landing_exactly_on_the_span_bounds_is_clean(self):
        sweep = [sweep_point(f) for f in (BAND[0] / SPAN_FACTOR, 10.0, BAND[1] * SPAN_FACTOR)]
        verdict = assess_stability_sweep(sweep, BAND, SPAN_FACTOR)
        self.assertTrue(verdict["sweep_clean"])

    def test_sweep_that_never_enters_the_band_is_a_finding(self):
        sweep = [sweep_point(f) for f in (1.0, 2.0, 40.0)]
        verdict = assess_stability_sweep(sweep, BAND, SPAN_FACTOR)
        self.assertTrue(any("inside the operating band" in item for item in verdict["findings"]))

    def test_non_increasing_sweep_rejected(self):
        sweep = [sweep_point(f) for f in (1.0, 2.0, 2.0)]
        with self.assertRaises(ValueError):
            assess_stability_sweep(sweep, BAND, SPAN_FACTOR)

    def test_single_point_sweep_rejected(self):
        with self.assertRaises(ValueError):
            assess_stability_sweep([sweep_point(10.0)], BAND, SPAN_FACTOR)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_stability_sweep(SWEEP, (12.0, 8.0), SPAN_FACTOR)

    def test_span_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_stability_sweep(SWEEP, BAND, 0.5)


class ReviewItemTests(unittest.TestCase):
    def test_clean_package_passes_the_item(self):
        result = review_sensitivity_and_stability(package())
        self.assertTrue(result["item_passed"])
        self.assertEqual(result["findings"], [])

    def test_worst_spread_parameter_is_reported(self):
        result = review_sensitivity_and_stability(package())
        self.assertEqual(result["worst_spread_parameter"], "saturated_output_power_mw")

    def test_an_unstable_frequency_fails_the_item(self):
        spec = package()
        spec["stability"]["sweep"][5] = sweep_point(20.0, s12=0.2)
        result = review_sensitivity_and_stability(spec)
        self.assertFalse(result["item_passed"])
        self.assertEqual(result["stability"]["unstable_frequencies_ghz"], [20.0])

    def test_a_sensitivity_breach_fails_an_otherwise_stable_design(self):
        spec = package()
        spec["parameters"][0]["allowed_relative_spread"] = 0.02
        result = review_sensitivity_and_stability(spec)
        self.assertFalse(result["item_passed"])
        self.assertTrue(result["stability"]["sweep_clean"])

    def test_short_sweep_fails_the_item_even_when_every_point_is_stable(self):
        spec = package()
        spec["stability"]["sweep"] = [sweep_point(f) for f in (8.0, 10.0, 12.0)]
        result = review_sensitivity_and_stability(spec)
        self.assertFalse(result["item_passed"])
        self.assertEqual(result["stability"]["unstable_frequencies_ghz"], [])

    def test_duplicate_parameter_rejected(self):
        spec = package()
        spec["parameters"].append(copy.deepcopy(PARAMETER))
        with self.assertRaises(ValueError):
            review_sensitivity_and_stability(spec)

    def test_missing_stability_block_rejected(self):
        spec = package()
        spec.pop("stability")
        with self.assertRaises(ValueError):
            review_sensitivity_and_stability(spec)

    def test_stability_block_without_a_sweep_rejected(self):
        spec = package()
        spec["stability"].pop("sweep")
        with self.assertRaises(ValueError):
            review_sensitivity_and_stability(spec)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            review_sensitivity_and_stability(["parameters"])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            review_sensitivity_and_stability(package(parameters=[]))


if __name__ == "__main__":
    unittest.main()

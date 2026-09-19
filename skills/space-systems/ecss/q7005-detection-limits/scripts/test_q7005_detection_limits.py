"""Contract test for the IR detection limits leaf (stdlib unittest)."""

import unittest

from q7005_detection_limits_logic import (
    DEFAULT_COVERAGE_FACTOR,
    DETECTED_NOT_QUANTIFIED,
    DETECTION_MULTIPLIER,
    MIN_BLANK_REPLICATES,
    NOT_DETECTED,
    QUANTIFICATION_MULTIPLIER,
    QUANTIFIED,
    assess_detection_limits,
    blank_mean,
    blank_standard_deviation,
    combined_relative_uncertainty,
    detection_limit_signal,
    expanded_uncertainty,
    quantification_limit_signal,
    reporting_decision,
    sampling_factor,
    signal_to_areal_mass,
    validate_blank_replicates,
)

# Eight blanks about 0.010 whose deviations are 3, -3, 2, -2, 1, -1, 0, 0 in
# units of 0.001: the sum of squares is 28e-6 and the sample variance 4e-6,
# so the sample standard deviation is exactly 0.002 in signal units.
BLANKS = [0.013, 0.007, 0.012, 0.008, 0.011, 0.009, 0.010, 0.010]
FLAT_BLANKS = [0.010] * 8
COMPONENTS = {"calibration-slope": 0.04, "sampled-area": 0.03}


def spec(**kw):
    base = {
        "blank_replicates": list(BLANKS),
        "calibration_slope": 0.01,
        "dilution_factor": 25.0,
        "recovery_fraction": 0.8,
        "sampled_area_cm2": 100.0,
        "sample_signal": 0.32,
        "uncertainty_components": dict(COMPONENTS),
        "allocation_ug_per_cm2": 20.0,
    }
    base.update(kw)
    return base


class TestValidateBlankReplicates(unittest.TestCase):
    def test_enough_replicates_are_returned(self):
        data = validate_blank_replicates(BLANKS)
        self.assertEqual(len(data), 8)

    def test_too_few_replicates_raise(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates(BLANKS[:3])

    def test_a_lower_floor_can_be_declared(self):
        data = validate_blank_replicates(BLANKS[:3], minimum=3)
        self.assertEqual(len(data), 3)

    def test_a_floor_below_two_raises(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates(BLANKS, minimum=1)

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates("0.010")

    def test_negative_replicate_raises(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates([-0.001] + BLANKS[1:])

    def test_boolean_replicate_is_rejected_not_coerced(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates([True] + BLANKS[1:])

    def test_minimum_constant_is_the_default(self):
        with self.assertRaises(ValueError):
            validate_blank_replicates(BLANKS[:MIN_BLANK_REPLICATES - 1])


class TestBlankStatistics(unittest.TestCase):
    def test_mean_is_the_arithmetic_mean(self):
        self.assertAlmostEqual(blank_mean(BLANKS), 0.010, places=9)

    def test_sample_standard_deviation_uses_n_minus_one(self):
        self.assertAlmostEqual(blank_standard_deviation(BLANKS), 0.002, places=9)

    def test_zero_scatter_raises(self):
        with self.assertRaises(ValueError):
            blank_standard_deviation(FLAT_BLANKS)

    def test_wider_scatter_gives_a_larger_deviation(self):
        wider = [2.0 * v for v in BLANKS]
        self.assertAlmostEqual(blank_standard_deviation(wider), 0.004, places=9)


class TestLimits(unittest.TestCase):
    def test_detection_limit_is_three_standard_deviations(self):
        self.assertAlmostEqual(detection_limit_signal(0.002), 0.006, places=9)

    def test_quantification_limit_is_ten_standard_deviations(self):
        self.assertAlmostEqual(quantification_limit_signal(0.002), 0.020,
                               places=9)

    def test_multipliers_are_the_declared_constants(self):
        self.assertAlmostEqual(
            detection_limit_signal(0.002, DETECTION_MULTIPLIER), 0.006, places=9
        )
        self.assertAlmostEqual(
            quantification_limit_signal(0.002, QUANTIFICATION_MULTIPLIER),
            0.020,
            places=9,
        )

    def test_zero_standard_deviation_raises(self):
        with self.assertRaises(ValueError):
            detection_limit_signal(0.0)

    def test_negative_multiplier_raises(self):
        with self.assertRaises(ValueError):
            quantification_limit_signal(0.002, -10.0)


class TestSamplingFactorAndConversion(unittest.TestCase):
    def test_factor_combines_dilution_recovery_and_area(self):
        self.assertAlmostEqual(sampling_factor(25.0, 0.8, 100.0), 0.3125,
                               places=9)

    def test_unit_chain_gives_the_reciprocal_area(self):
        self.assertAlmostEqual(sampling_factor(1.0, 1.0, 50.0), 0.02, places=9)

    def test_dilution_below_unity_raises(self):
        with self.assertRaises(ValueError):
            sampling_factor(0.5, 0.8, 100.0)

    def test_recovery_above_unity_raises(self):
        with self.assertRaises(ValueError):
            sampling_factor(25.0, 1.5, 100.0)

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            sampling_factor(25.0, 0.8, 0.0)

    def test_signal_converts_to_an_areal_mass(self):
        self.assertAlmostEqual(
            signal_to_areal_mass(0.32, 0.01, 0.3125), 10.0, places=9
        )

    def test_detection_limit_converts_to_an_areal_mass(self):
        self.assertAlmostEqual(
            signal_to_areal_mass(0.006, 0.01, 0.3125), 0.1875, places=9
        )

    def test_zero_slope_raises_in_the_conversion(self):
        with self.assertRaises(ValueError):
            signal_to_areal_mass(0.32, 0.0, 0.3125)


class TestReportingDecision(unittest.TestCase):
    def test_reading_above_the_quantification_limit_is_quantified(self):
        self.assertEqual(reporting_decision(0.32, 0.006, 0.020), QUANTIFIED)

    def test_reading_between_the_limits_is_detected_only(self):
        self.assertEqual(
            reporting_decision(0.010, 0.006, 0.020), DETECTED_NOT_QUANTIFIED
        )

    def test_reading_below_the_detection_limit_is_not_detected(self):
        self.assertEqual(reporting_decision(0.001, 0.006, 0.020), NOT_DETECTED)

    def test_reading_exactly_at_the_detection_limit_is_detected(self):
        sd = blank_standard_deviation(BLANKS)
        lod = detection_limit_signal(sd)
        loq = quantification_limit_signal(sd)
        self.assertEqual(reporting_decision(lod, lod, loq),
                         DETECTED_NOT_QUANTIFIED)

    def test_reading_exactly_at_the_quantification_limit_is_quantified(self):
        sd = blank_standard_deviation(BLANKS)
        lod = detection_limit_signal(sd)
        loq = quantification_limit_signal(sd)
        self.assertEqual(reporting_decision(loq, lod, loq), QUANTIFIED)

    def test_inverted_limits_raise(self):
        with self.assertRaises(ValueError):
            reporting_decision(0.32, 0.020, 0.006)


class TestUncertainty(unittest.TestCase):
    def test_components_combine_in_quadrature(self):
        self.assertAlmostEqual(
            combined_relative_uncertainty(COMPONENTS), 0.05, places=9
        )

    def test_quadrature_is_below_the_arithmetic_sum(self):
        quadrature = combined_relative_uncertainty(COMPONENTS)
        self.assertLess(quadrature, sum(COMPONENTS.values()) - 1e-6)

    def test_empty_components_raise(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({})

    def test_component_of_one_hundred_percent_raises(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({"recovery-fraction": 1.0})

    def test_negative_component_raises(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({"recovery-fraction": -0.1})

    def test_expanded_uncertainty_applies_the_coverage_factor(self):
        out = expanded_uncertainty(10.0, 0.05, DEFAULT_COVERAGE_FACTOR)
        self.assertAlmostEqual(out["standard_uncertainty"], 0.5, places=9)
        self.assertAlmostEqual(out["expanded_uncertainty"], 1.0, places=9)
        self.assertAlmostEqual(out["lower"], 9.0, places=9)
        self.assertAlmostEqual(out["upper"], 11.0, places=9)

    def test_zero_coverage_factor_raises(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(10.0, 0.05, 0.0)


class TestAssessDetectionLimits(unittest.TestCase):
    def test_nominal_quantified_case(self):
        out = assess_detection_limits(spec())
        self.assertAlmostEqual(out["blank_standard_deviation"], 0.002, places=9)
        self.assertAlmostEqual(out["detection_limit_ug_per_cm2"], 0.1875,
                               places=9)
        self.assertAlmostEqual(out["quantification_limit_ug_per_cm2"], 0.625,
                               places=9)
        self.assertAlmostEqual(out["sample_areal_ug_per_cm2"], 10.0, places=9)
        self.assertEqual(out["decision"], QUANTIFIED)
        self.assertAlmostEqual(out["reported_mass_ug_per_cm2"], 10.0, places=9)
        self.assertEqual(out["findings"], [])

    def test_dominant_component_is_named(self):
        out = assess_detection_limits(spec())
        self.assertEqual(out["dominant_component"], "calibration-slope")
        self.assertAlmostEqual(out["relative_standard_uncertainty"], 0.05,
                               places=9)

    def test_reading_between_the_limits_reports_no_mass(self):
        out = assess_detection_limits(spec(sample_signal=0.010))
        self.assertEqual(out["decision"], DETECTED_NOT_QUANTIFIED)
        self.assertIsNone(out["reported_mass_ug_per_cm2"])
        self.assertTrue(any("quantification limit" in f for f in out["findings"]))

    def test_reading_below_the_detection_limit_reports_the_limit(self):
        out = assess_detection_limits(spec(sample_signal=0.001))
        self.assertEqual(out["decision"], NOT_DETECTED)
        self.assertTrue(any("below the detection limit" in f
                            for f in out["findings"]))

    def test_interval_spanning_the_allocation_is_a_finding(self):
        out = assess_detection_limits(spec(allocation_ug_per_cm2=10.5))
        self.assertTrue(any("spans the allocation" in f for f in out["findings"]))

    def test_allocation_clear_of_the_interval_raises_no_finding(self):
        out = assess_detection_limits(spec(allocation_ug_per_cm2=20.0))
        self.assertEqual(out["findings"], [])

    def test_flat_blanks_raise(self):
        with self.assertRaises(ValueError):
            assess_detection_limits(spec(blank_replicates=list(FLAT_BLANKS)))

    def test_too_few_blanks_raise(self):
        with self.assertRaises(ValueError):
            assess_detection_limits(spec(blank_replicates=BLANKS[:4]))

    def test_missing_key_raises(self):
        broken = spec()
        del broken["calibration_slope"]
        with self.assertRaises(ValueError):
            assess_detection_limits(broken)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_limits(list(BLANKS))

    def test_larger_coverage_factor_widens_the_interval(self):
        narrow = assess_detection_limits(spec(coverage_factor=2.0))
        wide = assess_detection_limits(spec(coverage_factor=3.0))
        self.assertGreater(wide["interval"]["expanded_uncertainty"],
                           narrow["interval"]["expanded_uncertainty"])


if __name__ == "__main__":
    unittest.main(verbosity=1)

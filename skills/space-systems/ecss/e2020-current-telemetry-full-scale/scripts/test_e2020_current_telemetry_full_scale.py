"""Contract tests for the clause 5.2.8.3.1 current-telemetry full-scale logic."""

import unittest

from e2020_current_telemetry_full_scale_logic import (
    COVERAGE_TOLERANCE_A,
    SPREAD_CONTRIBUTORS,
    assess_full_scale_coverage,
    headroom_fraction,
    limitation_band,
    telemetry_full_scale_current,
    telemetry_resolution_a,
    worst_case_limitation_current,
)

# A 1.5 A class latching limiter that goes into limiting at 1.3 times its
# class current, with an initial tolerance and a temperature contributor.
CLASS_A = 1.5
RATIO = 1.3
CONTRIBUTORS = {"tolerance": 0.05, "temperature": 0.03}


def _spec(**overrides):
    """Return a coverage spec with a 1 V/A shunt-and-gain chain."""
    spec = {
        "class_current_a": CLASS_A,
        "limitation_ratio": RATIO,
        "contributors": dict(CONTRIBUTORS),
        "shunt_ohm": 0.05,
        "gain": 20.0,
        "converter_span_v": 3.0,
    }
    spec.update(overrides)
    return spec


class LimitationBandTests(unittest.TestCase):
    def test_band_without_contributors_collapses_to_nominal(self):
        low, high = limitation_band(2.0, 1.5)
        self.assertAlmostEqual(low, 3.0, places=9)
        self.assertAlmostEqual(high, 3.0, places=9)

    def test_contributors_sum_arithmetically_not_in_quadrature(self):
        low, high = limitation_band(1.0, 1.0, {"tolerance": 0.05, "ageing": 0.03})
        self.assertAlmostEqual(high, 1.08, places=9)
        self.assertAlmostEqual(low, 0.92, places=9)

    def test_worst_case_is_the_upper_edge(self):
        self.assertAlmostEqual(
            worst_case_limitation_current(2.0, 1.5, {"tolerance": 0.10}),
            3.3,
            places=9,
        )

    def test_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(1.5, 0.9)

    def test_zero_class_current_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(0.0, 1.3)

    def test_boolean_class_current_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(True, 1.3)

    def test_unknown_contributor_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(1.5, 1.3, {"vibration": 0.02})

    def test_negative_contributor_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(1.5, 1.3, {"tolerance": -0.01})

    def test_contributor_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(1.5, 1.3, {"tolerance": 1.0})

    def test_summed_spread_reaching_unity_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(
                1.5, 1.3, {"tolerance": 0.5, "temperature": 0.3, "ageing": 0.2}
            )

    def test_non_mapping_contributors_rejected(self):
        with self.assertRaises(ValueError):
            limitation_band(1.5, 1.3, [("tolerance", 0.05)])

    def test_every_recognised_contributor_is_accepted(self):
        spread = dict((name, 0.01) for name in SPREAD_CONTRIBUTORS)
        high = limitation_band(1.0, 1.0, spread)[1]
        self.assertAlmostEqual(high, 1.0 + 0.01 * len(SPREAD_CONTRIBUTORS), places=9)


class ChainFullScaleTests(unittest.TestCase):
    def test_span_refers_back_through_shunt_and_gain(self):
        chain = telemetry_full_scale_current(0.05, 20.0, 3.0)
        self.assertAlmostEqual(chain["full_scale_current_a"], 3.0, places=9)
        self.assertEqual(chain["limiting_element"], "converter")

    def test_zero_output_voltage_eats_the_top_of_the_span(self):
        chain = telemetry_full_scale_current(0.05, 20.0, 3.0, zero_output_v=0.5)
        self.assertAlmostEqual(chain["full_scale_current_a"], 2.5, places=9)

    def test_amplifier_clip_below_span_becomes_the_limiting_element(self):
        chain = telemetry_full_scale_current(0.05, 20.0, 3.0, amplifier_clip_v=2.2)
        self.assertAlmostEqual(chain["full_scale_current_a"], 2.2, places=9)
        self.assertEqual(chain["limiting_element"], "amplifier")

    def test_amplifier_clip_above_span_leaves_the_converter_in_charge(self):
        chain = telemetry_full_scale_current(0.05, 20.0, 3.0, amplifier_clip_v=4.0)
        self.assertEqual(chain["limiting_element"], "converter")
        self.assertAlmostEqual(chain["ceiling_v"], 3.0, places=9)

    def test_higher_gain_lowers_the_reported_full_scale(self):
        low_gain = telemetry_full_scale_current(0.05, 20.0, 3.0)
        high_gain = telemetry_full_scale_current(0.05, 40.0, 3.0)
        self.assertLess(
            high_gain["full_scale_current_a"], low_gain["full_scale_current_a"]
        )

    def test_zero_output_at_or_above_span_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_full_scale_current(0.05, 20.0, 3.0, zero_output_v=3.0)

    def test_negative_zero_output_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_full_scale_current(0.05, 20.0, 3.0, zero_output_v=-0.1)

    def test_clip_below_zero_output_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_full_scale_current(
                0.05, 20.0, 3.0, zero_output_v=1.0, amplifier_clip_v=0.8
            )

    def test_zero_shunt_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_full_scale_current(0.0, 20.0, 3.0)

    def test_non_numeric_gain_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_full_scale_current(0.05, "20", 3.0)


class ResolutionAndHeadroomTests(unittest.TestCase):
    def test_resolution_uses_the_full_code_span(self):
        self.assertAlmostEqual(telemetry_resolution_a(3.0, 2), 1.0, places=9)

    def test_more_bits_give_a_finer_code(self):
        self.assertLess(telemetry_resolution_a(3.0, 12), telemetry_resolution_a(3.0, 8))

    def test_non_integer_bits_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_resolution_a(3.0, 12.0)

    def test_bits_out_of_span_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_resolution_a(3.0, 0)

    def test_boolean_bits_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_resolution_a(3.0, True)

    def test_headroom_is_zero_at_an_exact_match(self):
        self.assertAlmostEqual(headroom_fraction(3.0, 3.0), 0.0, places=9)

    def test_headroom_is_negative_when_full_scale_falls_short(self):
        self.assertAlmostEqual(headroom_fraction(2.4, 3.0), -0.2, places=9)

    def test_headroom_against_zero_required_rejected(self):
        with self.assertRaises(ValueError):
            headroom_fraction(3.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_generous_span_covers_the_worst_case_limit(self):
        result = assess_full_scale_coverage(_spec())
        self.assertTrue(result["covered"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["required_current_a"], 1.5 * 1.3 * 1.08, places=9)

    def test_short_span_is_reported_as_a_saturating_chain(self):
        result = assess_full_scale_coverage(_spec(converter_span_v=2.0))
        self.assertFalse(result["covered"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("saturates" in f for f in result["findings"]))

    def test_exact_equality_counts_as_covered(self):
        result = assess_full_scale_coverage(
            {
                "class_current_a": 2.0,
                "limitation_ratio": 1.5,
                "shunt_ohm": 0.1,
                "gain": 10.0,
                "converter_span_v": 3.0,
            }
        )
        self.assertAlmostEqual(result["full_scale_current_a"], 3.0, places=9)
        self.assertAlmostEqual(result["required_current_a"], 3.0, places=9)
        self.assertTrue(result["covered"])
        self.assertAlmostEqual(result["headroom_fraction"], 0.0, places=9)

    def test_amplifier_clip_shortfall_names_the_clipping_element(self):
        result = assess_full_scale_coverage(_spec(amplifier_clip_v=1.8))
        self.assertEqual(result["limiting_element"], "amplifier")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("amplifier clips" in f for f in result["findings"]))

    def test_coarse_resolution_is_a_finding_even_when_the_range_reaches(self):
        result = assess_full_scale_coverage(
            _spec(bits=8, required_resolution_a=0.001)
        )
        self.assertTrue(result["covered"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("resolution" in f for f in result["findings"]))

    def test_resolution_inside_the_requirement_leaves_the_leaf_compliant(self):
        result = assess_full_scale_coverage(
            _spec(bits=14, required_resolution_a=0.001)
        )
        self.assertTrue(result["compliant"])
        self.assertIsNotNone(result["resolution_a"])

    def test_resolution_is_absent_when_no_bit_count_is_declared(self):
        self.assertIsNone(assess_full_scale_coverage(_spec())["resolution_a"])

    def test_missing_key_rejected(self):
        spec = _spec()
        del spec["shunt_ohm"]
        with self.assertRaises(ValueError):
            assess_full_scale_coverage(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_full_scale_coverage(["class_current_a"])

    def test_wider_spread_raises_the_current_the_range_has_to_reach(self):
        narrow = assess_full_scale_coverage(_spec(contributors={"tolerance": 0.02}))
        wide = assess_full_scale_coverage(_spec(contributors={"tolerance": 0.20}))
        self.assertLess(narrow["required_current_a"], wide["required_current_a"])

    def test_coverage_tolerance_is_small_enough_to_stay_an_engineering_zero(self):
        self.assertLess(COVERAGE_TOLERANCE_A, 1e-6)


if __name__ == "__main__":
    unittest.main()

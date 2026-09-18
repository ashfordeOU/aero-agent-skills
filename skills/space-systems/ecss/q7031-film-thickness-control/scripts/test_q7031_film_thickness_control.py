"""Contract tests for the per-coat wet and dry film thickness control logic."""

import unittest

from q7031_film_thickness_control_logic import (
    BAND_TOLERANCE,
    DEFAULT_MIN_SINGLE_FRACTION,
    assess_coat_readings,
    assess_film_thickness,
    coat_verdict,
    dry_to_wet_um,
    effective_volume_solids_pct,
    spreading_rate_m2_per_l,
    system_dry_thickness_um,
    validate_fraction,
    validate_positive,
    wet_to_dry_um,
)


def coat(**overrides):
    base = {
        "name": "primer",
        "volume_solids_pct": 50.0,
        "min_dft_um": 20.0,
        "max_dft_um": 40.0,
        "readings": [28.0, 30.0, 32.0, 29.0],
    }
    base.update(overrides)
    return base


class ValidatorTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive(25, "x"), 25.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"), "x")

    def test_fraction_upper_limit_accepted(self):
        self.assertEqual(validate_fraction(1.0, "f"), 1.0)

    def test_fraction_above_upper_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.2, "f")


class VolumeSolidsTests(unittest.TestCase):
    def test_unthinned_returns_tin_value(self):
        self.assertAlmostEqual(effective_volume_solids_pct(55.0), 55.0, places=12)

    def test_ten_percent_thinner_reduces_solids(self):
        self.assertAlmostEqual(effective_volume_solids_pct(55.0, 0.10), 50.0, places=12)

    def test_zero_solids_rejected(self):
        with self.assertRaises(ValueError):
            effective_volume_solids_pct(0.0)

    def test_over_hundred_solids_rejected(self):
        with self.assertRaises(ValueError):
            effective_volume_solids_pct(101.0)

    def test_negative_thinner_rejected(self):
        with self.assertRaises(ValueError):
            effective_volume_solids_pct(50.0, -0.1)


class ConversionTests(unittest.TestCase):
    def test_half_solids_halves_the_film(self):
        self.assertAlmostEqual(wet_to_dry_um(100.0, 50.0), 50.0, places=12)

    def test_wet_target_is_the_inverse(self):
        self.assertAlmostEqual(dry_to_wet_um(50.0, 50.0), 100.0, places=12)

    def test_round_trip_is_identity(self):
        wet = dry_to_wet_um(37.5, 62.0, 0.05)
        self.assertAlmostEqual(wet_to_dry_um(wet, 62.0, 0.05), 37.5, places=9)

    def test_thinner_raises_the_wet_target(self):
        plain = dry_to_wet_um(30.0, 50.0)
        thinned = dry_to_wet_um(30.0, 50.0, 0.20)
        self.assertAlmostEqual(thinned, plain * 1.20, places=9)

    def test_zero_wet_film_rejected(self):
        with self.assertRaises(ValueError):
            wet_to_dry_um(0.0, 50.0)

    def test_spreading_rate_at_full_transfer(self):
        self.assertAlmostEqual(spreading_rate_m2_per_l(50.0, 50.0), 10.0, places=12)

    def test_transfer_efficiency_derates_the_rate(self):
        self.assertAlmostEqual(
            spreading_rate_m2_per_l(50.0, 50.0, 0.0, 0.6), 6.0, places=12
        )

    def test_zero_transfer_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            spreading_rate_m2_per_l(50.0, 50.0, 0.0, 0.0)


class CoatVerdictTests(unittest.TestCase):
    def test_inside_band(self):
        self.assertEqual(coat_verdict(30.0, 20.0, 40.0), "within")

    def test_exactly_on_the_minimum_is_within(self):
        self.assertEqual(coat_verdict(20.0, 20.0, 40.0), "within")

    def test_exactly_on_the_maximum_is_within(self):
        self.assertEqual(coat_verdict(40.0, 20.0, 40.0), "within")

    def test_under_the_band(self):
        self.assertEqual(coat_verdict(12.0, 20.0, 40.0), "below")

    def test_over_the_band(self):
        self.assertEqual(coat_verdict(55.0, 20.0, 40.0), "above")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            coat_verdict(30.0, 40.0, 20.0)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            coat_verdict(30.0, 20.0, 40.0, tolerance=-1.0)


class CoatReadingTests(unittest.TestCase):
    def test_nominal_population_is_acceptable(self):
        result = assess_coat_readings([28.0, 30.0, 32.0], 20.0, 40.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["mean_um"], 30.0, places=12)

    def test_absolute_floor_is_the_fraction_of_the_minimum(self):
        result = assess_coat_readings([28.0, 30.0], 20.0, 40.0)
        self.assertAlmostEqual(result["absolute_floor_um"], 16.0, places=12)

    def test_reading_exactly_on_the_floor_is_kept(self):
        result = assess_coat_readings([16.0, 44.0], 20.0, 40.0)
        self.assertEqual(result["readings_below_floor"], 0)

    def test_thin_spot_under_the_floor_is_caught_even_with_a_good_mean(self):
        result = assess_coat_readings([10.0, 50.0], 20.0, 40.0)
        self.assertEqual(result["mean_verdict"], "within")
        self.assertEqual(result["readings_below_floor"], 1)
        self.assertFalse(result["acceptable"])

    def test_heavy_reading_over_the_maximum_is_counted(self):
        result = assess_coat_readings([30.0, 48.0], 20.0, 40.0)
        self.assertEqual(result["readings_above_maximum"], 1)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_coat_readings([], 20.0, 40.0)

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_coat_readings([-1.0], 20.0, 40.0)

    def test_default_fraction_is_four_fifths(self):
        self.assertAlmostEqual(DEFAULT_MIN_SINGLE_FRACTION, 0.8, places=12)

    def test_minimum_and_maximum_are_reported(self):
        result = assess_coat_readings([25.0, 30.0, 35.0], 20.0, 40.0)
        self.assertAlmostEqual(result["minimum_um"], 25.0, places=12)
        self.assertAlmostEqual(result["maximum_um"], 35.0, places=12)


class SystemThicknessTests(unittest.TestCase):
    def test_sum_of_coats(self):
        self.assertAlmostEqual(system_dry_thickness_um([20.0, 30.0, 25.0]), 75.0, places=12)

    def test_empty_stack_rejected(self):
        with self.assertRaises(ValueError):
            system_dry_thickness_um([])

    def test_non_positive_coat_rejected(self):
        with self.assertRaises(ValueError):
            system_dry_thickness_um([20.0, 0.0])


class AssessFilmThicknessTests(unittest.TestCase):
    def test_single_acceptable_coat(self):
        result = assess_film_thickness({"coats": [coat()]})
        self.assertTrue(result["acceptable"])
        self.assertEqual(len(result["coats"]), 1)

    def test_wet_comb_target_is_issued_per_coat(self):
        result = assess_film_thickness({"coats": [coat()]})
        self.assertAlmostEqual(result["coats"][0]["wet_comb_target_um"], 60.0, places=9)

    def test_target_is_the_band_midpoint(self):
        result = assess_film_thickness({"coats": [coat()]})
        self.assertAlmostEqual(result["coats"][0]["target_dft_um"], 30.0, places=12)

    def test_findings_are_prefixed_with_the_coat_name(self):
        thin = coat(name="topcoat", readings=[8.0, 9.0])
        result = assess_film_thickness({"coats": [thin]})
        self.assertFalse(result["acceptable"])
        self.assertTrue(result["findings"][0].startswith("topcoat:"))

    def test_stack_of_good_coats_can_overshoot_the_system_band(self):
        result = assess_film_thickness(
            {
                "coats": [coat(name="c1"), coat(name="c2"), coat(name="c3")],
                "system_dft_band": (40.0, 80.0),
            }
        )
        self.assertEqual(result["system_verdict"], "above")
        self.assertFalse(result["acceptable"])

    def test_system_band_met(self):
        result = assess_film_thickness(
            {"coats": [coat(name="c1"), coat(name="c2")], "system_dft_band": (40.0, 80.0)}
        )
        self.assertEqual(result["system_verdict"], "within")
        self.assertTrue(result["acceptable"])

    def test_system_verdict_absent_when_no_band_declared(self):
        self.assertIsNone(assess_film_thickness({"coats": [coat()]})["system_verdict"])

    def test_system_total_is_the_sum_of_coat_means(self):
        result = assess_film_thickness({"coats": [coat(name="c1"), coat(name="c2")]})
        expected = sum(c["mean_um"] for c in result["coats"])
        self.assertAlmostEqual(result["system_dft_um"], expected, places=12)

    def test_missing_coat_key_rejected(self):
        broken = coat()
        del broken["readings"]
        with self.assertRaises(ValueError):
            assess_film_thickness({"coats": [broken]})

    def test_empty_coat_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_film_thickness({"coats": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_film_thickness([coat()])

    def test_bad_system_band_shape_rejected(self):
        with self.assertRaises(ValueError):
            assess_film_thickness({"coats": [coat()], "system_dft_band": (40.0,)})

    def test_band_tolerance_is_small(self):
        self.assertAlmostEqual(BAND_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=1)

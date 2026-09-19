"""Contract tests for the sensitive-optics molecular deposition logic."""

import math
import unittest

from q7001_optics_contamination_control_logic import (
    BUDGET_TOLERANCE_NG_CM2,
    LOSS_TOLERANCE,
    accumulate_deposition,
    apportion_budget,
    assess_optics_contamination,
    film_thickness_nm,
    interpolate_table,
    source_deposition_ng_cm2,
    sticking_coefficient_at,
    throughput_loss_fraction,
    transmittance,
    validate_receiver,
    validate_source,
)

# Sticking rises as the receiver gets colder: a cryogenic detector window
# retains almost everything that reaches it, a warm baffle almost nothing.
STICKING_CURVE = [
    (100.0, 1.0),
    (200.0, 0.8),
    (300.0, 0.2),
    (400.0, 0.02),
]

SOURCE_A = {
    "name": "harness-outgassing",
    "outgassing_rate_g_per_s": 1.0e-9,
    "view_factor": 0.5,
    "duration_s": 1.0e4,
    "sticking_coefficient": 1.0,
}

SOURCE_B = {
    "name": "thruster-plume-backflow",
    "outgassing_rate_g_per_s": 1.0e-9,
    "view_factor": 0.25,
    "duration_s": 1.0e4,
    "sticking_coefficient": 1.0,
}


def receiver(**overrides):
    base = {
        "area_cm2": 100.0,
        "budget_ng_cm2": 100.0,
        "allowable_loss_fraction": 0.02,
        "film_density_g_cm3": 1.0,
        "absorption_per_nm": 0.02,
        "surfaces_in_path": 1,
    }
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_source_defaults_weight_to_one(self):
        self.assertAlmostEqual(validate_source(SOURCE_A)["weight"], 1.0)

    def test_source_without_name_rejected(self):
        bad = dict(SOURCE_A)
        del bad["name"]
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_blank_source_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(dict(SOURCE_A, name="   "))

    def test_view_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(dict(SOURCE_A, view_factor=1.4))

    def test_negative_outgassing_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(dict(SOURCE_A, outgassing_rate_g_per_s=-1.0e-9))

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(dict(SOURCE_A, duration_s=0.0))

    def test_boolean_view_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(dict(SOURCE_A, view_factor=True))

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(["harness-outgassing"])

    def test_receiver_defaults_are_filled(self):
        spec = validate_receiver({
            "area_cm2": 10.0,
            "budget_ng_cm2": 50.0,
            "allowable_loss_fraction": 0.01,
        })
        self.assertAlmostEqual(spec["film_density_g_cm3"], 1.0)
        self.assertEqual(spec["surfaces_in_path"], 1)

    def test_receiver_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(area_cm2=0.0))

    def test_receiver_allowable_loss_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(allowable_loss_fraction=1.5))

    def test_receiver_fractional_surface_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(surfaces_in_path=2.5))

    def test_receiver_non_finite_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(budget_ng_cm2=float("inf")))


class StickingCurveTests(unittest.TestCase):
    def test_tabulated_point_is_returned(self):
        self.assertAlmostEqual(sticking_coefficient_at(200.0, STICKING_CURVE), 0.8)

    def test_midpoint_is_linear(self):
        self.assertAlmostEqual(sticking_coefficient_at(250.0, STICKING_CURVE), 0.5)

    def test_colder_receiver_retains_more(self):
        cold = sticking_coefficient_at(150.0, STICKING_CURVE)
        warm = sticking_coefficient_at(350.0, STICKING_CURVE)
        self.assertGreater(cold, warm)

    def test_below_tabulated_span_refused(self):
        with self.assertRaises(ValueError):
            sticking_coefficient_at(50.0, STICKING_CURVE)

    def test_above_tabulated_span_refused(self):
        with self.assertRaises(ValueError):
            sticking_coefficient_at(500.0, STICKING_CURVE)

    def test_single_point_curve_refused(self):
        with self.assertRaises(ValueError):
            interpolate_table([(100.0, 1.0)], 100.0)

    def test_non_monotone_curve_refused(self):
        with self.assertRaises(ValueError):
            interpolate_table([(100.0, 1.0), (100.0, 0.5)], 100.0)

    def test_ordinate_outside_zero_one_refused(self):
        with self.assertRaises(ValueError):
            interpolate_table([(100.0, 1.4), (200.0, 0.5)], 150.0)


class DepositionTests(unittest.TestCase):
    def test_source_deposition_closed_form(self):
        value = source_deposition_ng_cm2(SOURCE_A, 100.0, 1.0)
        self.assertAlmostEqual(value, 50.0, places=9)

    def test_halving_the_view_factor_halves_the_deposition(self):
        full = source_deposition_ng_cm2(SOURCE_A, 100.0, 1.0)
        half = source_deposition_ng_cm2(SOURCE_B, 100.0, 1.0)
        self.assertAlmostEqual(half, full / 2.0, places=9)

    def test_sticking_scales_the_deposition(self):
        full = source_deposition_ng_cm2(SOURCE_A, 100.0, 1.0)
        quarter = source_deposition_ng_cm2(SOURCE_A, 100.0, 0.25)
        self.assertAlmostEqual(quarter, full / 4.0, places=9)

    def test_larger_receiver_area_dilutes_the_areal_deposition(self):
        small = source_deposition_ng_cm2(SOURCE_A, 100.0, 1.0)
        large = source_deposition_ng_cm2(SOURCE_A, 400.0, 1.0)
        self.assertAlmostEqual(large, small / 4.0, places=9)

    def test_zero_receiver_area_rejected(self):
        with self.assertRaises(ValueError):
            source_deposition_ng_cm2(SOURCE_A, 0.0, 1.0)

    def test_sticking_above_one_rejected(self):
        with self.assertRaises(ValueError):
            source_deposition_ng_cm2(SOURCE_A, 100.0, 1.2)

    def test_accumulation_sums_the_sources(self):
        result = accumulate_deposition([SOURCE_A, SOURCE_B], receiver())
        self.assertAlmostEqual(result["total_ng_cm2"], 75.0, places=9)
        self.assertEqual(len(result["sources"]), 2)

    def test_accumulation_uses_the_receiver_temperature_curve(self):
        warm = dict(SOURCE_A)
        del warm["sticking_coefficient"]
        spec = receiver(temperature_k=250.0)
        spec["sticking_curve"] = STICKING_CURVE
        result = accumulate_deposition([warm], spec)
        self.assertAlmostEqual(result["sources"][0]["sticking_coefficient"], 0.5)
        self.assertAlmostEqual(result["total_ng_cm2"], 25.0, places=9)

    def test_missing_sticking_information_is_refused(self):
        warm = dict(SOURCE_A)
        del warm["sticking_coefficient"]
        with self.assertRaises(ValueError):
            accumulate_deposition([warm], receiver())

    def test_empty_source_list_refused(self):
        with self.assertRaises(ValueError):
            accumulate_deposition([], receiver())


class FilmAndThroughputTests(unittest.TestCase):
    def test_unit_density_film_thickness(self):
        self.assertAlmostEqual(film_thickness_nm(100.0, 1.0), 1.0, places=12)

    def test_denser_film_is_thinner(self):
        self.assertAlmostEqual(film_thickness_nm(100.0, 2.0), 0.5, places=12)

    def test_zero_deposition_is_zero_thickness(self):
        self.assertAlmostEqual(film_thickness_nm(0.0), 0.0)

    def test_negative_deposition_rejected(self):
        with self.assertRaises(ValueError):
            film_thickness_nm(-1.0)

    def test_clean_path_transmits_everything(self):
        self.assertAlmostEqual(transmittance(0.0, 0.02), 1.0)

    def test_two_surfaces_square_the_single_surface_transmittance(self):
        one = transmittance(1.0, 0.02, 1)
        two = transmittance(1.0, 0.02, 2)
        self.assertAlmostEqual(two, one * one, places=12)

    def test_throughput_loss_matches_beer_lambert(self):
        loss = throughput_loss_fraction(0.75, 0.02, 1)
        self.assertAlmostEqual(loss, 1.0 - math.exp(-0.015), places=12)

    def test_zero_surface_count_rejected(self):
        with self.assertRaises(ValueError):
            transmittance(1.0, 0.02, 0)


class ApportionmentTests(unittest.TestCase):
    def test_equal_weights_split_evenly(self):
        shares = apportion_budget(100.0, [SOURCE_A, SOURCE_B])
        self.assertAlmostEqual(shares["harness-outgassing"], 50.0, places=9)
        self.assertAlmostEqual(shares["thruster-plume-backflow"], 50.0, places=9)

    def test_weights_shift_the_split(self):
        shares = apportion_budget(
            100.0,
            [dict(SOURCE_A, weight=3.0), dict(SOURCE_B, weight=1.0)],
        )
        self.assertAlmostEqual(shares["harness-outgassing"], 75.0, places=9)

    def test_shares_sum_to_the_budget(self):
        shares = apportion_budget(
            90.0, [dict(SOURCE_A, weight=2.0), dict(SOURCE_B, weight=7.0)]
        )
        self.assertAlmostEqual(math.fsum(shares.values()), 90.0, places=9)

    def test_duplicate_source_names_rejected(self):
        with self.assertRaises(ValueError):
            apportion_budget(100.0, [SOURCE_A, dict(SOURCE_B, name=SOURCE_A["name"])])

    def test_no_sources_rejected(self):
        with self.assertRaises(ValueError):
            apportion_budget(100.0, [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        return {"receiver": receiver(**overrides), "sources": [SOURCE_A, SOURCE_B]}

    def test_compliant_case_has_no_findings(self):
        result = assess_optics_contamination(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_budget_overrun_is_flagged(self):
        result = assess_optics_contamination(self._spec(budget_ng_cm2=40.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("overruns" in f for f in result["findings"]))

    def test_exact_budget_equality_is_accepted(self):
        single = {"receiver": receiver(), "sources": [SOURCE_A]}
        total = assess_optics_contamination(single)["total_deposition_ng_cm2"]
        single["receiver"] = receiver(budget_ng_cm2=total)
        result = assess_optics_contamination(single)
        self.assertAlmostEqual(result["total_deposition_ng_cm2"], total, places=9)
        self.assertEqual(result["overrunning_sources"], [])
        self.assertTrue(result["compliant"])

    def test_exact_loss_equality_is_accepted(self):
        loss = assess_optics_contamination(self._spec())["throughput_loss_fraction"]
        result = assess_optics_contamination(self._spec(allowable_loss_fraction=loss))
        self.assertAlmostEqual(
            result["throughput_loss_fraction"], loss, places=12
        )
        self.assertTrue(result["compliant"])
        self.assertLessEqual(
            abs(result["throughput_loss_fraction"] - loss), LOSS_TOLERANCE
        )

    def test_throughput_shortfall_is_flagged(self):
        result = assess_optics_contamination(self._spec(allowable_loss_fraction=0.001))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("throughput loss" in f for f in result["findings"]))

    def test_source_over_its_own_allocation_is_named(self):
        result = assess_optics_contamination(
            self._spec(budget_ng_cm2=80.0)
        )
        self.assertIn("harness-outgassing", result["overrunning_sources"])

    def test_more_surfaces_in_path_increase_the_loss(self):
        one = assess_optics_contamination(self._spec(surfaces_in_path=1))
        three = assess_optics_contamination(self._spec(surfaces_in_path=3))
        self.assertGreater(
            three["throughput_loss_fraction"], one["throughput_loss_fraction"]
        )

    def test_denser_film_loses_less_throughput(self):
        light = assess_optics_contamination(self._spec(film_density_g_cm3=1.0))
        dense = assess_optics_contamination(self._spec(film_density_g_cm3=2.0))
        self.assertGreater(
            light["throughput_loss_fraction"], dense["throughput_loss_fraction"]
        )

    def test_allocation_is_reported_per_source(self):
        result = assess_optics_contamination(self._spec())
        self.assertEqual(
            sorted(result["allocation_ng_cm2"]),
            ["harness-outgassing", "thruster-plume-backflow"],
        )

    def test_budget_tolerance_is_tight(self):
        self.assertLess(BUDGET_TOLERANCE_NG_CM2, 1e-6)

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_optics_contamination({"receiver": receiver()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_optics_contamination(["receiver"])


if __name__ == "__main__":
    unittest.main()

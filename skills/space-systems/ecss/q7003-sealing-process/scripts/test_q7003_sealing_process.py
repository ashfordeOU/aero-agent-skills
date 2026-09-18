"""Contract test for the black-anodizing sealing leaf (stdlib unittest)."""

import unittest

from q7003_sealing_process_logic import (
    MAX_ABSORPTANCE_LOSS,
    MAX_BLEED_RATING,
    MAX_CONDUCTIVITY_US_CM,
    MAX_DYE_TO_SEAL_MINUTES,
    MAX_NICKEL_ACETATE_G_L,
    MAX_PHOSPHATE_MG_L,
    MAX_SEAL_PH,
    MAX_SILICATE_MG_L,
    METHOD_HOT_WATER,
    METHOD_NICKEL_ACETATE,
    METHOD_WINDOWS,
    MIN_NICKEL_ACETATE_G_L,
    MIN_SEAL_PH,
    absorptance_loss,
    assess_sealing,
    assess_sealing_runs,
    check_bath_chemistry,
    check_dye_to_seal_hold,
    check_seal_result,
    check_seal_time,
    check_temperature,
    check_water,
    required_seal_minutes,
    validate_seal_run,
)


def seal_run(rid="S-1", **kw):
    record = {
        "id": rid,
        "method": METHOD_NICKEL_ACETATE,
        "coating_thickness_um": 10.0,
        "temperature_c": 85.0,
        "declared_minutes": 20.0,
        "conductivity_us_cm": 10.0,
        "silicate_mg_l": 0.0,
        "phosphate_mg_l": 0.0,
        "nickel_acetate_g_l": 6.0,
        "ph": 6.0,
        "hold_minutes": 5.0,
        "absorptance_before": 0.93,
        "absorptance_after": 0.925,
        "bleed_rating": 0,
    }
    record.update(kw)
    return record


class TestRequiredTime(unittest.TestCase):
    def test_hot_water_scales_with_the_coating(self):
        expected = METHOD_WINDOWS[METHOD_HOT_WATER]["minutes_per_um"] * 20.0
        self.assertAlmostEqual(
            required_seal_minutes(METHOD_HOT_WATER, 20.0), expected, places=9
        )

    def test_a_thin_coating_falls_back_to_the_floor(self):
        self.assertAlmostEqual(
            required_seal_minutes(METHOD_HOT_WATER, 1.0),
            METHOD_WINDOWS[METHOD_HOT_WATER]["floor_minutes"],
            places=9,
        )

    def test_nickel_acetate_is_the_faster_route(self):
        self.assertLess(
            required_seal_minutes(METHOD_NICKEL_ACETATE, 20.0),
            required_seal_minutes(METHOD_HOT_WATER, 20.0),
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            required_seal_minutes("steam-blast", 10.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            required_seal_minutes(METHOD_HOT_WATER, -1.0)

    def test_time_exactly_on_the_requirement_is_accepted(self):
        needed = required_seal_minutes(METHOD_NICKEL_ACETATE, 10.0)
        findings, returned = check_seal_time(METHOD_NICKEL_ACETATE, needed, 10.0)
        self.assertEqual(findings, [])
        self.assertAlmostEqual(returned, needed, places=9)

    def test_short_seal_time_is_found(self):
        findings, _ = check_seal_time(METHOD_HOT_WATER, 4.0, 10.0)
        self.assertIn("seal-time-shorter-than-the-coating-depth-needs", findings)


class TestTemperature(unittest.TestCase):
    def test_a_tank_inside_the_window_is_clean(self):
        self.assertEqual(check_temperature(METHOD_HOT_WATER, 98.0), [])

    def test_both_bounds_are_accepted(self):
        low, high = METHOD_WINDOWS[METHOD_NICKEL_ACETATE]["temperature_c"]
        self.assertEqual(check_temperature(METHOD_NICKEL_ACETATE, low), [])
        self.assertEqual(check_temperature(METHOD_NICKEL_ACETATE, high), [])

    def test_a_cold_hot_water_tank_is_found(self):
        self.assertIn(
            "seal-temperature-below-the-hot-water-window",
            check_temperature(METHOD_HOT_WATER, 80.0),
        )

    def test_an_overheated_acetate_tank_is_found(self):
        self.assertIn(
            "seal-temperature-above-the-nickel-acetate-window",
            check_temperature(METHOD_NICKEL_ACETATE, 99.0),
        )


class TestWater(unittest.TestCase):
    def test_clean_water_is_clean(self):
        self.assertEqual(check_water(10.0, 0.0, 0.0), [])

    def test_conductivity_on_the_limit_is_accepted(self):
        self.assertEqual(check_water(MAX_CONDUCTIVITY_US_CM, 0.0, 0.0), [])

    def test_conductive_water_is_found(self):
        self.assertIn(
            "seal-water-conductivity-above-the-limit",
            check_water(MAX_CONDUCTIVITY_US_CM * 2.0, 0.0, 0.0),
        )

    def test_silicate_is_found(self):
        self.assertIn(
            "silicate-in-the-seal-water-poisons-the-seal",
            check_water(10.0, MAX_SILICATE_MG_L + 1.0, 0.0),
        )

    def test_phosphate_is_found(self):
        self.assertIn(
            "phosphate-in-the-seal-water-poisons-the-seal",
            check_water(10.0, 0.0, MAX_PHOSPHATE_MG_L + 1.0),
        )

    def test_negative_conductivity_raises(self):
        with self.assertRaises(ValueError):
            check_water(-1.0, 0.0, 0.0)


class TestBathChemistry(unittest.TestCase):
    def test_an_acetate_bath_inside_its_windows_is_clean(self):
        self.assertEqual(
            check_bath_chemistry(METHOD_NICKEL_ACETATE, 6.0, 6.0), []
        )

    def test_hot_water_ignores_the_acetate_concentration(self):
        self.assertEqual(check_bath_chemistry(METHOD_HOT_WATER, 0.0, 6.0), [])

    def test_weak_acetate_bath_is_found(self):
        self.assertIn(
            "nickel-acetate-concentration-below-window",
            check_bath_chemistry(
                METHOD_NICKEL_ACETATE, MIN_NICKEL_ACETATE_G_L - 2.0, 6.0
            ),
        )

    def test_strong_acetate_bath_is_found(self):
        self.assertIn(
            "nickel-acetate-concentration-above-window",
            check_bath_chemistry(
                METHOD_NICKEL_ACETATE, MAX_NICKEL_ACETATE_G_L + 2.0, 6.0
            ),
        )

    def test_low_ph_is_found(self):
        self.assertIn(
            "seal-bath-ph-below-window",
            check_bath_chemistry(METHOD_HOT_WATER, 0.0, MIN_SEAL_PH - 1.0),
        )

    def test_high_ph_is_found(self):
        self.assertIn(
            "seal-bath-ph-above-window",
            check_bath_chemistry(METHOD_HOT_WATER, 0.0, MAX_SEAL_PH + 1.0),
        )

    def test_ph_outside_the_scale_raises(self):
        with self.assertRaises(ValueError):
            check_bath_chemistry(METHOD_HOT_WATER, 0.0, 20.0)


class TestHold(unittest.TestCase):
    def test_hold_on_the_bound_is_accepted(self):
        self.assertEqual(check_dye_to_seal_hold(MAX_DYE_TO_SEAL_MINUTES), [])

    def test_long_hold_is_found(self):
        self.assertIn(
            "dyed-coating-held-too-long-before-sealing",
            check_dye_to_seal_hold(MAX_DYE_TO_SEAL_MINUTES + 10.0),
        )

    def test_negative_hold_raises(self):
        with self.assertRaises(ValueError):
            check_dye_to_seal_hold(-1.0)


class TestSealResult(unittest.TestCase):
    def test_a_gain_in_absorptance_is_reported_as_no_loss(self):
        self.assertAlmostEqual(absorptance_loss(0.90, 0.93), 0.0, places=9)

    def test_loss_is_the_difference(self):
        self.assertAlmostEqual(absorptance_loss(0.93, 0.90), 0.03, places=9)

    def test_loss_exactly_on_acceptance_is_accepted(self):
        before = 0.95
        findings, loss = check_seal_result(before, before - MAX_ABSORPTANCE_LOSS, 0)
        self.assertEqual(findings, [])
        self.assertAlmostEqual(loss, MAX_ABSORPTANCE_LOSS, places=9)

    def test_a_bleeding_seal_is_found(self):
        findings, _ = check_seal_result(0.95, 0.80, 0)
        self.assertIn("absorptance-lost-across-the-seal-above-acceptance", findings)

    def test_a_high_bleed_rating_is_found(self):
        findings, _ = check_seal_result(0.95, 0.945, MAX_BLEED_RATING + 1)
        self.assertIn("dye-bleed-rating-above-acceptance", findings)

    def test_non_integer_bleed_rating_raises(self):
        with self.assertRaises(ValueError):
            check_seal_result(0.95, 0.94, 1.5)

    def test_negative_bleed_rating_raises(self):
        with self.assertRaises(ValueError):
            check_seal_result(0.95, 0.94, -1)


class TestValidateRun(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_seal_run({"id": "S-9"})
        self.assertEqual(norm["method"], METHOD_HOT_WATER)
        self.assertEqual(norm["bleed_rating"], 0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_run(["S-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_run(seal_run(""))

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_run(seal_run(method="microwave"))

    def test_boolean_bleed_rating_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_run(seal_run(bleed_rating=True))


class TestAssessSealing(unittest.TestCase):
    def test_a_sound_run_is_compliant(self):
        result = assess_sealing(seal_run())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_seal_minutes"], 15.0, places=9)

    def test_a_cold_tank_reaches_the_run_verdict(self):
        result = assess_sealing(seal_run(method=METHOD_HOT_WATER,
                                         temperature_c=70.0,
                                         declared_minutes=60.0))
        self.assertFalse(result["compliant"])
        self.assertIn("seal-temperature-below-the-hot-water-window",
                      result["findings"])

    def test_poisoned_water_reaches_the_run_verdict(self):
        result = assess_sealing(seal_run(silicate_mg_l=5.0))
        self.assertIn("silicate-in-the-seal-water-poisons-the-seal",
                      result["findings"])

    def test_batch_reports_the_failing_runs(self):
        report = assess_sealing_runs([
            seal_run("S-1"),
            seal_run("S-2", declared_minutes=1.0),
        ])
        self.assertEqual(report["non_compliant_ids"], ["S-2"])
        self.assertFalse(report["compliant"])

    def test_duplicate_run_id_raises(self):
        with self.assertRaises(ValueError):
            assess_sealing_runs([seal_run("S-1"), seal_run("S-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_sealing_runs([])


if __name__ == "__main__":
    unittest.main()

"""Contract test for the black-anodizing dyeing leaf (stdlib unittest)."""

import unittest

from q7003_dyeing_process_requirements_logic import (
    DYE_STEP_LOAD,
    DYE_STEP_PRECIPITATE,
    DYE_STEP_RINSE,
    IMMERSION_MINUTES_PER_UM,
    MAX_ABSORPTANCE_SPREAD,
    MAX_HOLD_MINUTES,
    MIN_COLOUR_POINTS,
    MIN_IMMERSION_MINUTES,
    MIN_MEAN_ABSORPTANCE,
    MIN_POINT_ABSORPTANCE,
    absorptance_statistics,
    assess_dyeing,
    assess_dyeing_runs,
    check_bath,
    check_hold,
    check_immersion,
    check_sequence,
    colour_findings,
    required_immersion_minutes,
    validate_dyeing_run,
)

GOOD_BATHS = {
    DYE_STEP_LOAD: {"concentration_g_l": 40.0, "ph": 5.5, "temperature_c": 55.0},
    DYE_STEP_PRECIPITATE: {"concentration_g_l": 25.0, "ph": 6.0,
                           "temperature_c": 50.0},
}


def dye_run(rid="D-1", **kw):
    record = {
        "id": rid,
        "steps": [DYE_STEP_LOAD, DYE_STEP_RINSE, DYE_STEP_PRECIPITATE],
        "baths": {k: dict(v) for k, v in GOOD_BATHS.items()},
        "coating_thickness_um": 10.0,
        "immersion_minutes": 15.0,
        "hold_minutes": 10.0,
        "absorptance_readings": [0.93, 0.94, 0.92, 0.93],
    }
    record.update(kw)
    return record


class TestImmersionTime(unittest.TestCase):
    def test_a_deep_coating_scales_with_thickness(self):
        self.assertAlmostEqual(
            required_immersion_minutes(10.0),
            IMMERSION_MINUTES_PER_UM * 10.0,
            places=9,
        )

    def test_a_shallow_coating_falls_back_to_the_floor(self):
        self.assertAlmostEqual(
            required_immersion_minutes(1.0), MIN_IMMERSION_MINUTES, places=9
        )

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            required_immersion_minutes(-1.0)

    def test_declared_time_on_the_requirement_is_accepted(self):
        needed = required_immersion_minutes(10.0)
        findings, returned = check_immersion(needed, 10.0)
        self.assertEqual(findings, [])
        self.assertAlmostEqual(returned, needed, places=9)

    def test_short_immersion_is_found(self):
        findings, _ = check_immersion(2.0, 10.0)
        self.assertIn("dye-immersion-shorter-than-the-coating-depth-needs",
                      findings)


class TestBathWindows(unittest.TestCase):
    def test_a_bath_inside_its_windows_is_clean(self):
        self.assertEqual(check_bath(DYE_STEP_LOAD, 40.0, 5.5, 55.0), [])

    def test_weak_dye_bath_is_found(self):
        self.assertIn(
            "metal-salt-loading-concentration-g-l-below-window",
            check_bath(DYE_STEP_LOAD, 5.0, 5.5, 55.0),
        )

    def test_acidic_bath_is_found(self):
        self.assertIn(
            "metal-salt-loading-ph-below-window",
            check_bath(DYE_STEP_LOAD, 40.0, 2.0, 55.0),
        )

    def test_hot_bath_is_found(self):
        self.assertIn(
            "pigment-precipitation-temperature-c-above-window",
            check_bath(DYE_STEP_PRECIPITATE, 25.0, 6.0, 90.0),
        )

    def test_unknown_bath_step_raises(self):
        with self.assertRaises(ValueError):
            check_bath("sealing", 25.0, 6.0, 50.0)

    def test_ph_outside_the_scale_raises(self):
        with self.assertRaises(ValueError):
            check_bath(DYE_STEP_LOAD, 40.0, 15.0, 55.0)


class TestSequence(unittest.TestCase):
    def test_the_declared_order_is_clean(self):
        self.assertEqual(
            check_sequence([DYE_STEP_LOAD, DYE_STEP_RINSE, DYE_STEP_PRECIPITATE]),
            [],
        )

    def test_a_reversed_pair_is_found(self):
        self.assertIn(
            "dye-steps-out-of-order",
            check_sequence([DYE_STEP_PRECIPITATE, DYE_STEP_RINSE, DYE_STEP_LOAD]),
        )

    def test_a_missing_intermediate_rinse_is_found(self):
        self.assertIn(
            "dye-step-missing-%s" % DYE_STEP_RINSE,
            check_sequence([DYE_STEP_LOAD, DYE_STEP_PRECIPITATE]),
        )

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            check_sequence([DYE_STEP_LOAD, "electropolish"])

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            check_sequence([])


class TestHold(unittest.TestCase):
    def test_hold_on_the_bound_is_accepted(self):
        self.assertEqual(check_hold(MAX_HOLD_MINUTES), [])

    def test_long_hold_is_found(self):
        self.assertIn(
            "coating-held-too-long-before-dyeing",
            check_hold(MAX_HOLD_MINUTES + 15.0),
        )

    def test_negative_hold_raises(self):
        with self.assertRaises(ValueError):
            check_hold(-1.0)


class TestColour(unittest.TestCase):
    def test_statistics_over_a_set_of_readings(self):
        stats = absorptance_statistics([0.90, 0.94, 0.92])
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["mean"], 0.92, places=9)
        self.assertAlmostEqual(stats["spread"], 0.04, places=9)

    def test_reading_outside_the_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            absorptance_statistics([0.9, 1.4])

    def test_empty_reading_set_raises(self):
        with self.assertRaises(ValueError):
            absorptance_statistics([])

    def test_a_good_black_is_accepted(self):
        findings, stats = colour_findings([0.93, 0.94, 0.92, 0.93])
        self.assertEqual(findings, [])
        self.assertGreater(stats["mean"], MIN_MEAN_ABSORPTANCE)

    def test_a_mean_exactly_on_acceptance_is_accepted(self):
        findings, stats = colour_findings(
            [MIN_MEAN_ABSORPTANCE, MIN_MEAN_ABSORPTANCE, MIN_MEAN_ABSORPTANCE]
        )
        self.assertEqual(findings, [])
        self.assertAlmostEqual(stats["mean"], MIN_MEAN_ABSORPTANCE, places=9)

    def test_a_grey_finish_is_found(self):
        findings, _ = colour_findings([0.70, 0.71, 0.69])
        self.assertIn("mean-absorptance-below-acceptance", findings)

    def test_one_weak_corner_is_found_even_at_a_good_mean(self):
        findings, _ = colour_findings([0.97, 0.97, 0.97, 0.80])
        self.assertIn("single-point-absorptance-below-acceptance", findings)

    def test_a_wide_spread_is_found(self):
        findings, _ = colour_findings([0.99, 0.99, 0.88])
        self.assertIn("absorptance-spread-above-the-uniformity-limit", findings)

    def test_too_few_points_is_found(self):
        findings, _ = colour_findings([0.95] * (MIN_COLOUR_POINTS - 1))
        self.assertIn("too-few-colour-measurement-points", findings)

    def test_a_spread_exactly_on_the_limit_is_accepted(self):
        low = MIN_POINT_ABSORPTANCE + 0.05
        findings, stats = colour_findings([low, low + MAX_ABSORPTANCE_SPREAD, low])
        self.assertNotIn("absorptance-spread-above-the-uniformity-limit", findings)
        self.assertAlmostEqual(stats["spread"], MAX_ABSORPTANCE_SPREAD, places=9)


class TestValidateRun(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_dyeing_run({"id": "D-9"})
        self.assertEqual(norm["baths"], {})
        self.assertEqual(norm["absorptance_readings"], [])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_dyeing_run(["D-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_dyeing_run(dye_run(""))

    def test_unknown_bath_key_raises(self):
        with self.assertRaises(ValueError):
            validate_dyeing_run(dye_run(baths={"sealing": {}}))

    def test_non_sequence_readings_raise(self):
        with self.assertRaises(ValueError):
            validate_dyeing_run(dye_run(absorptance_readings=0.93))


class TestAssessDyeing(unittest.TestCase):
    def test_a_sound_run_is_compliant(self):
        result = assess_dyeing(dye_run())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_immersion_minutes"], 12.0,
                               places=9)

    def test_a_missing_bath_record_is_found(self):
        result = assess_dyeing(
            dye_run(baths={DYE_STEP_LOAD: dict(GOOD_BATHS[DYE_STEP_LOAD])})
        )
        self.assertIn("no-bath-record-for-%s" % DYE_STEP_PRECIPITATE,
                      result["findings"])

    def test_a_run_without_colour_data_is_found(self):
        result = assess_dyeing(dye_run(absorptance_readings=[]))
        self.assertIn("no-colour-measurement-on-record", result["findings"])
        self.assertIsNone(result["colour"])

    def test_a_long_hold_reaches_the_run_verdict(self):
        result = assess_dyeing(dye_run(hold_minutes=MAX_HOLD_MINUTES + 30.0))
        self.assertFalse(result["compliant"])
        self.assertIn("coating-held-too-long-before-dyeing", result["findings"])

    def test_batch_reports_the_failing_runs(self):
        report = assess_dyeing_runs([
            dye_run("D-1"),
            dye_run("D-2", absorptance_readings=[0.60, 0.61, 0.59]),
        ])
        self.assertEqual(report["non_compliant_ids"], ["D-2"])
        self.assertFalse(report["compliant"])

    def test_duplicate_run_id_raises(self):
        with self.assertRaises(ValueError):
            assess_dyeing_runs([dye_run("D-1"), dye_run("D-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_dyeing_runs([])


if __name__ == "__main__":
    unittest.main()

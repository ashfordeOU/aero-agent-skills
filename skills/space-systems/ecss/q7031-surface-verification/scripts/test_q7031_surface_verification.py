"""Contract tests for the ECSS-Q-ST-70-31C prepared-surface verification logic."""

import unittest

from q7031_surface_verification_logic import (
    DEFAULT_MAX_RELATIVE_HUMIDITY_PCT,
    DEFAULT_MIN_DEW_POINT_MARGIN_K,
    DEFAULT_NVR_LIMIT_MG_PER_M2,
    DEFAULT_OBSCURATION_LIMIT_PCT,
    DISPOSITIONS,
    ENVIRONMENT_METRICS,
    MEASUREMENT_TOLERANCE,
    MIN_WATER_BREAK_DWELL_S,
    ROUGHNESS_WINDOWS_UM,
    SURFACE_METRICS,
    assess_readiness,
    dew_point_margin_k,
    dryness_verdict,
    humidity_verdict,
    normalize_key,
    obscuration_verdict,
    residue_verdict,
    roughness_verdict,
    roughness_window_um,
    water_break_verdict,
)


def reading(**overrides):
    base = {
        "paint_system": "epoxy-primer",
        "water_film_continuous": True,
        "water_break_dwell_s": 45.0,
        "nvr_mg_per_m2": 0.9,
        "obscuration_pct": 0.02,
        "ra_um": 1.6,
        "surface_temperature_c": 22.0,
        "dew_point_c": 10.0,
        "relative_humidity_pct": 45.0,
    }
    base.update(overrides)
    return base


class WaterBreakTests(unittest.TestCase):
    def test_continuous_film_passes(self):
        self.assertTrue(water_break_verdict(True, 45.0))

    def test_broken_film_fails(self):
        self.assertFalse(water_break_verdict(False, 45.0))

    def test_dwell_exactly_at_the_minimum_is_evidence(self):
        self.assertTrue(water_break_verdict(True, MIN_WATER_BREAK_DWELL_S))

    def test_short_dwell_is_refused_not_scored(self):
        with self.assertRaises(ValueError):
            water_break_verdict(True, 5.0)

    def test_non_boolean_observation_rejected(self):
        with self.assertRaises(ValueError):
            water_break_verdict("continuous", 45.0)


class CleanlinessTests(unittest.TestCase):
    def test_residue_under_limit_passes(self):
        self.assertTrue(residue_verdict(0.5))

    def test_residue_over_limit_fails(self):
        self.assertFalse(residue_verdict(4.0))

    def test_residue_exactly_at_the_limit_passes(self):
        self.assertTrue(residue_verdict(DEFAULT_NVR_LIMIT_MG_PER_M2))

    def test_residue_representation_error_absorbed(self):
        nudged = DEFAULT_NVR_LIMIT_MG_PER_M2 + MEASUREMENT_TOLERANCE / 2.0
        self.assertTrue(residue_verdict(nudged))

    def test_obscuration_over_limit_fails(self):
        self.assertFalse(obscuration_verdict(0.9))

    def test_obscuration_exactly_at_the_limit_passes(self):
        self.assertTrue(obscuration_verdict(DEFAULT_OBSCURATION_LIMIT_PCT))

    def test_obscuration_above_full_coverage_rejected(self):
        with self.assertRaises(ValueError):
            obscuration_verdict(140.0)

    def test_negative_residue_rejected(self):
        with self.assertRaises(ValueError):
            residue_verdict(-0.1)


class RoughnessTests(unittest.TestCase):
    def test_window_looked_up_per_paint_system(self):
        self.assertEqual(roughness_window_um("epoxy-primer"),
                         ROUGHNESS_WINDOWS_UM["epoxy-primer"])

    def test_unknown_paint_system_rejected(self):
        with self.assertRaises(ValueError):
            roughness_window_um("mystery-coat")

    def test_profile_inside_the_window(self):
        self.assertEqual(roughness_verdict(1.6, (0.8, 3.2)), "in-window")

    def test_profile_below_the_window_is_too_smooth(self):
        self.assertEqual(roughness_verdict(0.2, (0.8, 3.2)), "too-smooth")

    def test_profile_above_the_window_is_too_rough(self):
        self.assertEqual(roughness_verdict(5.0, (0.8, 3.2)), "too-rough")

    def test_profile_exactly_on_the_lower_bound_is_in_window(self):
        self.assertEqual(roughness_verdict(0.8, (0.8, 3.2)), "in-window")

    def test_profile_exactly_on_the_upper_bound_is_in_window(self):
        self.assertEqual(roughness_verdict(3.2, (0.8, 3.2)), "in-window")

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            roughness_verdict(1.0, (3.2, 0.8))

    def test_malformed_window_rejected(self):
        with self.assertRaises(ValueError):
            roughness_verdict(1.0, (0.8,))


class DrynessTests(unittest.TestCase):
    def test_margin_is_surface_minus_dew_point(self):
        self.assertAlmostEqual(dew_point_margin_k(22.0, 10.0), 12.0, places=9)

    def test_margin_can_be_negative(self):
        self.assertAlmostEqual(dew_point_margin_k(4.0, 9.0), -5.0, places=9)

    def test_sufficient_margin_passes(self):
        self.assertTrue(dryness_verdict(12.0))

    def test_margin_exactly_at_the_minimum_passes(self):
        self.assertTrue(dryness_verdict(DEFAULT_MIN_DEW_POINT_MARGIN_K))

    def test_insufficient_margin_fails(self):
        self.assertFalse(dryness_verdict(1.0))

    def test_humidity_under_the_ceiling_passes(self):
        self.assertTrue(humidity_verdict(45.0))

    def test_humidity_exactly_at_the_ceiling_passes(self):
        self.assertTrue(humidity_verdict(DEFAULT_MAX_RELATIVE_HUMIDITY_PCT))

    def test_humidity_over_the_ceiling_fails(self):
        self.assertFalse(humidity_verdict(85.0))

    def test_humidity_above_saturation_rejected(self):
        with self.assertRaises(ValueError):
            humidity_verdict(120.0)


class ReadinessTests(unittest.TestCase):
    def test_clean_dry_in_window_surface_is_ready(self):
        out = assess_readiness(reading())
        self.assertEqual(out["disposition"], "ready-to-coat")
        self.assertEqual(out["surface_findings"], [])
        self.assertEqual(out["environment_findings"], [])

    def test_water_break_sends_the_surface_back(self):
        out = assess_readiness(reading(water_film_continuous=False))
        self.assertEqual(out["disposition"], "re-prepare")
        self.assertIn("water-break-observed", out["surface_findings"])

    def test_residue_sends_the_surface_back(self):
        out = assess_readiness(reading(nvr_mg_per_m2=6.0))
        self.assertIn("non-volatile-residue-over-limit", out["surface_findings"])

    def test_too_rough_profile_sends_the_surface_back(self):
        out = assess_readiness(reading(ra_um=6.0))
        self.assertEqual(out["roughness_verdict"], "too-rough")
        self.assertEqual(out["disposition"], "re-prepare")

    def test_humid_room_holds_rather_than_re_preparing(self):
        out = assess_readiness(reading(relative_humidity_pct=88.0))
        self.assertEqual(out["disposition"], "conditions-hold")
        self.assertIn("relative-humidity-over-ceiling", out["environment_findings"])

    def test_cold_substrate_holds_rather_than_re_preparing(self):
        out = assess_readiness(reading(surface_temperature_c=11.0, dew_point_c=10.0))
        self.assertEqual(out["disposition"], "conditions-hold")
        self.assertIn("dew-point-margin-under-minimum", out["environment_findings"])

    def test_surface_failure_outranks_an_environmental_one(self):
        out = assess_readiness(reading(nvr_mg_per_m2=6.0, relative_humidity_pct=88.0))
        self.assertEqual(out["disposition"], "re-prepare")

    def test_window_may_be_overridden_per_item(self):
        out = assess_readiness(reading(ra_um=5.0, roughness_window=(1.0, 6.0)))
        self.assertEqual(out["roughness_verdict"], "in-window")

    def test_missing_reading_key_rejected(self):
        spec = reading()
        del spec["dew_point_c"]
        with self.assertRaises(ValueError):
            assess_readiness(spec)

    def test_metric_name_lists_are_populated(self):
        self.assertIn("water-break", SURFACE_METRICS)
        self.assertIn("relative-humidity", ENVIRONMENT_METRICS)

    def test_key_helper_folds_case(self):
        self.assertEqual(normalize_key(" Epoxy-Primer ", "paint system"), "epoxy-primer")

    def test_every_disposition_is_a_declared_one(self):
        for spec in (reading(), reading(nvr_mg_per_m2=9.0),
                     reading(relative_humidity_pct=95.0)):
            self.assertIn(assess_readiness(spec)["disposition"], DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()

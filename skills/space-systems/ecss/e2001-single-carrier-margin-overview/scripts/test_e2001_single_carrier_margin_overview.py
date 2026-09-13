#!/usr/bin/env python3
"""Gate 3 contract test -- single-carrier multipactor margin overview.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_single_carrier_margin_overview.py
"""

import math
import unittest

from e2001_single_carrier_margin_overview_logic import (
    ANALYSIS_MARGIN,
    CONTINUOUS_WAVE,
    PULSED_CARRIER,
    TEST_MARGIN,
    achieved_margin_db,
    assess_single_carrier_condition,
    discharge_build_up_time_s,
    governing_carrier_power_w,
    nominal_margin_requirement_db,
    normalize_carrier_mode,
    power_limit_for_margin_w,
    pulse_supports_build_up,
    summarize_margin_overview,
)


class TestCarrierModeCategorization(unittest.TestCase):
    def test_continuous_wave_aliases_resolve(self):
        for spelling in ("cw", "CW", " continuous-wave ", "steady-carrier"):
            self.assertEqual(normalize_carrier_mode(spelling), CONTINUOUS_WAVE)

    def test_pulsed_aliases_resolve(self):
        for spelling in ("pulsed", "PULSED-CARRIER", "duty-cycled"):
            self.assertEqual(normalize_carrier_mode(spelling), PULSED_CARRIER)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_carrier_mode("multi-carrier")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_carrier_mode(3)


class TestGoverningCarrierPower(unittest.TestCase):
    def test_continuous_wave_uses_steady_level(self):
        out = governing_carrier_power_w({"mode": "cw", "carrier_power_w": 120.0})
        self.assertEqual(out["mode"], CONTINUOUS_WAVE)
        self.assertAlmostEqual(out["governing_power_w"], 120.0)
        self.assertEqual(out["basis"], "steady-carrier-power")

    def test_continuous_wave_without_level_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w({"mode": "cw"})

    def test_non_positive_level_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w({"mode": "cw", "carrier_power_w": 0.0})

    def test_stated_peak_envelope_power_used_directly(self):
        out = governing_carrier_power_w({"mode": "pulsed", "peak_power_w": 900.0})
        self.assertAlmostEqual(out["governing_power_w"], 900.0)
        self.assertEqual(out["basis"], "stated-peak-envelope-power")

    def test_peak_recovered_from_duty_cycle(self):
        out = governing_carrier_power_w(
            {"mode": "pulsed", "average_power_w": 10.0, "duty_cycle": 0.1}
        )
        self.assertAlmostEqual(out["governing_power_w"], 100.0)
        self.assertEqual(out["basis"], "peak-recovered-from-duty-cycle")

    def test_full_duty_cycle_is_admissible(self):
        out = governing_carrier_power_w(
            {"mode": "pulsed", "average_power_w": 50.0, "duty_cycle": 1.0}
        )
        self.assertAlmostEqual(out["governing_power_w"], 50.0)

    def test_zero_duty_cycle_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w(
                {"mode": "pulsed", "average_power_w": 10.0, "duty_cycle": 0.0}
            )

    def test_duty_cycle_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w(
                {"mode": "pulsed", "average_power_w": 10.0, "duty_cycle": 1.4}
            )

    def test_missing_duty_cycle_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w({"mode": "pulsed", "average_power_w": 10.0})

    def test_pulsed_without_any_level_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w({"mode": "pulsed"})

    def test_non_mapping_condition_rejected(self):
        with self.assertRaises(ValueError):
            governing_carrier_power_w(["pulsed", 10.0])


class TestDischargeBuildUp(unittest.TestCase):
    def test_build_up_time_from_growth_model(self):
        # 1024 = 2**10, so ten cycles at one gigahertz -> ten nanosecond.
        out = discharge_build_up_time_s(
            1.0e9, growth_per_cycle=2.0, seed_electrons=1.0,
            detectable_electrons=1024.0,
        )
        self.assertAlmostEqual(out, 1.0e-8, places=15)

    def test_slower_growth_takes_longer(self):
        fast = discharge_build_up_time_s(1.0e9, growth_per_cycle=2.0)
        slow = discharge_build_up_time_s(1.0e9, growth_per_cycle=1.2)
        self.assertGreater(slow, fast)

    def test_unity_growth_rejected(self):
        with self.assertRaises(ValueError):
            discharge_build_up_time_s(1.0e9, growth_per_cycle=1.0)

    def test_detectable_population_below_seed_rejected(self):
        with self.assertRaises(ValueError):
            discharge_build_up_time_s(
                1.0e9, growth_per_cycle=2.0, seed_electrons=10.0,
                detectable_electrons=5.0,
            )

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            discharge_build_up_time_s(-1.0e9)

    def test_long_pulse_supports_build_up(self):
        self.assertTrue(pulse_supports_build_up(1.0e-6, 1.0e-8))

    def test_short_pulse_does_not_support_build_up(self):
        self.assertFalse(pulse_supports_build_up(1.0e-9, 1.0e-8))

    def test_pulse_exactly_at_build_up_time_supports_it(self):
        build_up = discharge_build_up_time_s(
            1.0e9, growth_per_cycle=2.0, seed_electrons=1.0,
            detectable_electrons=1024.0,
        )
        self.assertTrue(pulse_supports_build_up(build_up, build_up))

    def test_non_positive_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            pulse_supports_build_up(0.0, 1.0e-8)


class TestMarginArithmetic(unittest.TestCase):
    def test_factor_of_four_is_about_six_decibel(self):
        self.assertAlmostEqual(achieved_margin_db(400.0, 100.0), 6.020599913, places=8)

    def test_equal_levels_give_zero_margin(self):
        self.assertAlmostEqual(achieved_margin_db(250.0, 250.0), 0.0, places=12)

    def test_operating_above_threshold_gives_negative_margin(self):
        self.assertLess(achieved_margin_db(100.0, 400.0), 0.0)

    def test_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            achieved_margin_db(0.0, 100.0)

    def test_non_positive_operating_level_rejected(self):
        with self.assertRaises(ValueError):
            achieved_margin_db(100.0, -5.0)

    def test_power_limit_inverts_the_margin(self):
        self.assertAlmostEqual(
            power_limit_for_margin_w(400.0, 6.020599913279624), 100.0, places=9
        )

    def test_zero_margin_limit_is_the_threshold(self):
        self.assertAlmostEqual(power_limit_for_margin_w(400.0, 0.0), 400.0, places=9)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            power_limit_for_margin_w(400.0, -3.0)


class TestNominalRequirement(unittest.TestCase):
    def test_default_analysis_values(self):
        self.assertAlmostEqual(
            nominal_margin_requirement_db(ANALYSIS_MARGIN, "cw"), 6.0
        )

    def test_default_pulsed_campaign_value_exceeds_continuous_wave(self):
        pulsed = nominal_margin_requirement_db(TEST_MARGIN, "pulsed")
        steady = nominal_margin_requirement_db(TEST_MARGIN, "cw")
        self.assertGreater(pulsed, steady)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            nominal_margin_requirement_db("thermal-margin", "cw")

    def test_policy_without_the_carrier_mode_entry_rejected(self):
        policy = {ANALYSIS_MARGIN: {CONTINUOUS_WAVE: 5.0}}
        with self.assertRaises(ValueError):
            nominal_margin_requirement_db(ANALYSIS_MARGIN, "pulsed", policy)

    def test_policy_without_the_family_entry_rejected(self):
        policy = {ANALYSIS_MARGIN: {CONTINUOUS_WAVE: 5.0}}
        with self.assertRaises(ValueError):
            nominal_margin_requirement_db(TEST_MARGIN, "cw", policy)


class TestConditionAssessment(unittest.TestCase):
    def test_comfortable_continuous_wave_case_is_compliant(self):
        rec = assess_single_carrier_condition(
            {
                "identifier": "output-filter-gap",
                "mode": "cw",
                "carrier_power_w": 50.0,
                "threshold_power_w": 1000.0,
                "margin_family": ANALYSIS_MARGIN,
            }
        )
        self.assertTrue(rec["compliant"])
        self.assertAlmostEqual(rec["shortfall_db"], 0.0)
        self.assertAlmostEqual(rec["achieved_margin_db"], 13.0103, places=4)
        self.assertEqual(rec["findings"], [])

    def test_exactly_met_requirement_is_compliant(self):
        policy = {ANALYSIS_MARGIN: {CONTINUOUS_WAVE: 6.020599913279624}}
        rec = assess_single_carrier_condition(
            {
                "mode": "cw",
                "carrier_power_w": 100.0,
                "threshold_power_w": 400.0,
                "margin_family": ANALYSIS_MARGIN,
            },
            policy,
        )
        self.assertTrue(rec["compliant"])
        self.assertAlmostEqual(rec["shortfall_db"], 0.0)

    def test_shortfall_is_reported_with_a_finding(self):
        rec = assess_single_carrier_condition(
            {
                "identifier": "coaxial-transition",
                "mode": "cw",
                "carrier_power_w": 300.0,
                "threshold_power_w": 600.0,
                "margin_family": ANALYSIS_MARGIN,
            }
        )
        self.assertFalse(rec["compliant"])
        self.assertAlmostEqual(rec["shortfall_db"], 2.9897, places=4)
        self.assertEqual(len(rec["findings"]), 1)

    def test_duty_averaged_level_is_not_taken_as_the_operating_point(self):
        rec = assess_single_carrier_condition(
            {
                "mode": "pulsed",
                "average_power_w": 20.0,
                "duty_cycle": 0.05,
                "threshold_power_w": 500.0,
            }
        )
        self.assertAlmostEqual(rec["governing_power_w"], 400.0)
        self.assertFalse(rec["compliant"])

    def test_short_pulse_raises_a_build_up_finding_without_crediting_it(self):
        rec = assess_single_carrier_condition(
            {
                "mode": "pulsed",
                "peak_power_w": 900.0,
                "threshold_power_w": 1000.0,
                "frequency_hz": 1.0e9,
                "pulse_width_s": 1.0e-9,
                "growth_per_cycle": 2.0,
                "detectable_electrons": 1024.0,
            }
        )
        self.assertEqual(rec["build_up_status"], "build-up-limited")
        self.assertFalse(rec["compliant"])
        self.assertEqual(len(rec["findings"]), 2)

    def test_long_pulse_is_screened_as_build_up_supported(self):
        rec = assess_single_carrier_condition(
            {
                "mode": "pulsed",
                "peak_power_w": 10.0,
                "threshold_power_w": 1000.0,
                "frequency_hz": 1.0e9,
                "pulse_width_s": 1.0e-4,
                "growth_per_cycle": 2.0,
                "detectable_electrons": 1024.0,
            }
        )
        self.assertEqual(rec["build_up_status"], "build-up-supported")
        self.assertTrue(rec["compliant"])

    def test_unscreened_condition_reports_no_build_up_verdict(self):
        rec = assess_single_carrier_condition(
            {"mode": "cw", "carrier_power_w": 10.0, "threshold_power_w": 1000.0}
        )
        self.assertEqual(rec["build_up_status"], "not-screened")

    def test_pulse_width_without_frequency_rejected(self):
        with self.assertRaises(ValueError):
            assess_single_carrier_condition(
                {
                    "mode": "pulsed",
                    "peak_power_w": 10.0,
                    "threshold_power_w": 1000.0,
                    "pulse_width_s": 1.0e-6,
                }
            )

    def test_missing_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_single_carrier_condition({"mode": "cw", "carrier_power_w": 10.0})

    def test_allowed_power_matches_the_required_margin(self):
        rec = assess_single_carrier_condition(
            {
                "mode": "cw",
                "carrier_power_w": 10.0,
                "threshold_power_w": 1000.0,
                "margin_family": TEST_MARGIN,
            }
        )
        self.assertAlmostEqual(rec["required_margin_db"], 3.0)
        self.assertAlmostEqual(rec["allowed_power_w"], 501.187233, places=5)


class TestOverviewRollUp(unittest.TestCase):
    def _conditions(self):
        return [
            {
                "identifier": "waveguide-iris",
                "mode": "cw",
                "carrier_power_w": 20.0,
                "threshold_power_w": 800.0,
            },
            {
                "identifier": "coaxial-connector",
                "mode": "cw",
                "carrier_power_w": 400.0,
                "threshold_power_w": 800.0,
            },
        ]

    def test_roll_up_counts_and_worst_shortfall(self):
        out = summarize_margin_overview(self._conditions())
        self.assertEqual(out["condition_count"], 2)
        self.assertEqual(out["compliant_count"], 1)
        self.assertEqual(out["non_compliant"], ["coaxial-connector"])
        self.assertFalse(out["unit_compliant"])
        self.assertAlmostEqual(out["worst_shortfall_db"], 2.9897, places=4)

    def test_all_compliant_unit_rolls_up_clean(self):
        out = summarize_margin_overview(self._conditions()[:1])
        self.assertTrue(out["unit_compliant"])
        self.assertAlmostEqual(out["worst_shortfall_db"], 0.0)
        self.assertEqual(out["build_up_limited"], [])

    def test_empty_condition_list_rejected(self):
        with self.assertRaises(ValueError):
            summarize_margin_overview([])

    def test_non_list_conditions_rejected(self):
        with self.assertRaises(ValueError):
            summarize_margin_overview({"mode": "cw"})

    def test_records_are_returned_for_every_condition(self):
        out = summarize_margin_overview(self._conditions())
        self.assertEqual(len(out["records"]), 2)
        self.assertTrue(
            all(math.isfinite(r["achieved_margin_db"]) for r in out["records"])
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract test for the acceptance cycling purpose leaf (offline)."""

import copy
import unittest

from e2008_thermal_cycle_acceptance_purpose_logic import (
    ACCEPTANCE_PURPOSES,
    DEFAULT_COFFIN_MANSON_EXPONENT,
    EARLY_LIFE_FRACTION,
    INFANT_MORTALITY_REVEALED,
    MAX_QUALIFICATION_LIFE_FRACTION,
    MIN_ACCEPTANCE_CYCLES,
    MIN_CYCLE_RANGE_K,
    MIN_SOAK_TIME_CONSTANTS,
    ONSET_CATEGORIES,
    PURPOSE_NOT_SERVED,
    WORKMANSHIP_CONFIRMED,
    assess_acceptance_purpose,
    campaign_duration_h,
    categorize_failure_onset,
    cycle_duration_min,
    cycle_temperature_range_k,
    early_life_cycle_count,
    escape_rate,
    fatigue_acceleration,
    group_failures,
    qualification_life_consumed,
    soak_adequacy,
    validate_cycle_profile,
)

ACCEPTANCE_PROFILE = {
    "hot_k": 373.15,
    "cold_k": 173.15,
    "cycles": 8,
    "ramp_rate_k_per_min": 5.0,
    "hot_dwell_min": 30.0,
    "cold_dwell_min": 30.0,
}

QUALIFICATION_PROFILE = {
    "hot_k": 393.15,
    "cold_k": 173.15,
    "cycles": 1000,
    "ramp_rate_k_per_min": 5.0,
    "hot_dwell_min": 30.0,
    "cold_dwell_min": 30.0,
}

CAMPAIGN_CASE = {
    "acceptance_profile": ACCEPTANCE_PROFILE,
    "qualification_profile": QUALIFICATION_PROFILE,
    "thermal_time_constant_min": 8.0,
    "unit_count": 12,
    "failure_cycles": (),
}


def _case(**overrides):
    case = copy.deepcopy(CAMPAIGN_CASE)
    case.update(overrides)
    return case


def _acceptance(**overrides):
    profile = copy.deepcopy(ACCEPTANCE_PROFILE)
    profile.update(overrides)
    return profile


class PurposeDeclarationTests(unittest.TestCase):
    def test_both_acceptance_purposes_are_named(self):
        self.assertIn("reveal-infant-mortality", ACCEPTANCE_PURPOSES)
        self.assertIn("confirm-supplier-workmanship", ACCEPTANCE_PURPOSES)

    def test_the_onset_categories_are_early_and_later(self):
        self.assertEqual(ONSET_CATEGORIES, ("infant-mortality", "later-life"))

    def test_the_early_life_window_is_a_minority_of_the_campaign(self):
        self.assertLess(EARLY_LIFE_FRACTION, 0.5)
        self.assertGreater(EARLY_LIFE_FRACTION, 0.0)


class ProfileValidationTests(unittest.TestCase):
    def test_a_sound_profile_is_normalised(self):
        checked = validate_cycle_profile("acceptance profile", ACCEPTANCE_PROFILE)
        self.assertEqual(checked["cycles"], 8)
        self.assertAlmostEqual(checked["hot_k"], 373.15, places=9)

    def test_a_profile_with_the_extremes_inverted_is_refused(self):
        with self.assertRaises(ValueError):
            validate_cycle_profile(
                "acceptance profile", _acceptance(hot_k=173.15, cold_k=373.15)
            )

    def test_a_profile_missing_a_dwell_is_refused(self):
        profile = _acceptance()
        del profile["cold_dwell_min"]
        with self.assertRaises(ValueError):
            validate_cycle_profile("acceptance profile", profile)

    def test_a_zero_cycle_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_cycle_profile("acceptance profile", _acceptance(cycles=0))

    def test_a_fractional_cycle_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_cycle_profile("acceptance profile", _acceptance(cycles=8.5))

    def test_a_profile_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            validate_cycle_profile("acceptance profile", (373.15, 173.15))


class CampaignArithmeticTests(unittest.TestCase):
    def test_the_cycle_range_is_the_span_of_the_extremes(self):
        self.assertAlmostEqual(
            cycle_temperature_range_k(ACCEPTANCE_PROFILE), 200.0, places=6
        )

    def test_one_cycle_is_two_ramps_and_two_dwells(self):
        self.assertAlmostEqual(
            cycle_duration_min(ACCEPTANCE_PROFILE), 140.0, places=6
        )

    def test_a_faster_ramp_shortens_the_cycle(self):
        self.assertLess(
            cycle_duration_min(_acceptance(ramp_rate_k_per_min=20.0)),
            cycle_duration_min(ACCEPTANCE_PROFILE),
        )

    def test_the_campaign_duration_follows_the_cycle_count(self):
        self.assertAlmostEqual(
            campaign_duration_h(ACCEPTANCE_PROFILE), 140.0 * 8.0 / 60.0, places=6
        )


class SoakTests(unittest.TestCase):
    def test_a_dwell_of_three_time_constants_is_adequate(self):
        soak = soak_adequacy(24.0, 8.0)
        self.assertAlmostEqual(
            soak["soak_time_constants"], MIN_SOAK_TIME_CONSTANTS, places=9
        )
        self.assertTrue(soak["adequate"])

    def test_a_short_dwell_never_reaches_the_extreme(self):
        soak = soak_adequacy(10.0, 8.0)
        self.assertFalse(soak["adequate"])
        self.assertAlmostEqual(soak["soak_time_constants"], 1.25, places=9)

    def test_a_zero_thermal_time_constant_is_refused(self):
        with self.assertRaises(ValueError):
            soak_adequacy(30.0, 0.0)

    def test_a_non_numeric_dwell_is_refused(self):
        with self.assertRaises(ValueError):
            soak_adequacy("30 min", 8.0)


class FatigueTests(unittest.TestCase):
    def test_an_identical_range_carries_no_acceleration(self):
        self.assertAlmostEqual(fatigue_acceleration(200.0, 200.0), 1.0, places=9)

    def test_a_deeper_range_accelerates_the_damage(self):
        self.assertGreater(fatigue_acceleration(250.0, 200.0), 1.2)

    def test_a_shallower_range_slows_the_damage(self):
        self.assertLess(fatigue_acceleration(150.0, 200.0), 0.8)

    def test_a_higher_exponent_sharpens_the_acceleration(self):
        self.assertGreater(
            fatigue_acceleration(250.0, 200.0, 4.0),
            fatigue_acceleration(250.0, 200.0, DEFAULT_COFFIN_MANSON_EXPONENT),
        )

    def test_a_zero_range_cannot_be_scaled(self):
        with self.assertRaises(ValueError):
            fatigue_acceleration(0.0, 200.0)

    def test_a_short_shallow_campaign_spends_almost_no_life(self):
        life = qualification_life_consumed(
            ACCEPTANCE_PROFILE, QUALIFICATION_PROFILE
        )
        self.assertLess(life["consumed_fraction"], 0.01)
        self.assertAlmostEqual(life["acceptance_range_k"], 200.0, places=6)

    def test_a_quarter_life_campaign_sits_exactly_on_the_ceiling(self):
        life = qualification_life_consumed(
            _acceptance(cycles=250),
            _acceptance(cycles=1000),
        )
        self.assertAlmostEqual(
            life["consumed_fraction"], MAX_QUALIFICATION_LIFE_FRACTION, places=9
        )

    def test_a_long_campaign_eats_the_demonstrated_life(self):
        life = qualification_life_consumed(
            _acceptance(cycles=500), QUALIFICATION_PROFILE
        )
        self.assertGreater(life["consumed_fraction"], MAX_QUALIFICATION_LIFE_FRACTION)


class OnsetCategoryTests(unittest.TestCase):
    def test_the_early_window_is_a_quarter_of_the_campaign(self):
        self.assertEqual(early_life_cycle_count(8), 2)
        self.assertEqual(early_life_cycle_count(100), 25)

    def test_a_single_cycle_campaign_still_has_an_early_window(self):
        self.assertEqual(early_life_cycle_count(1), 1)

    def test_an_opening_cycle_failure_is_an_early_life_escape(self):
        self.assertEqual(categorize_failure_onset(1, 8), "infant-mortality")
        self.assertEqual(categorize_failure_onset(2, 8), "infant-mortality")

    def test_a_late_failure_is_grouped_as_later_life(self):
        self.assertEqual(categorize_failure_onset(3, 8), "later-life")
        self.assertEqual(categorize_failure_onset(8, 8), "later-life")

    def test_a_failure_beyond_the_cycles_run_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_failure_onset(9, 8)

    def test_a_failure_before_the_first_cycle_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_failure_onset(0, 8)

    def test_failures_are_grouped_into_both_categories(self):
        grouped = group_failures((1, 7), 8)
        self.assertEqual(grouped["infant-mortality"], (1,))
        self.assertEqual(grouped["later-life"], (7,))

    def test_an_empty_failure_record_groups_to_nothing(self):
        grouped = group_failures((), 8)
        for category in ONSET_CATEGORIES:
            self.assertEqual(grouped[category], ())

    def test_a_failure_record_that_is_not_a_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            group_failures(3, 8)


class EscapeRateTests(unittest.TestCase):
    def test_two_failures_in_twelve_units_is_one_sixth(self):
        self.assertAlmostEqual(escape_rate(2, 12), 2.0 / 12.0, places=12)

    def test_a_clean_lot_has_a_zero_escape_rate(self):
        self.assertAlmostEqual(escape_rate(0, 12), 0.0, places=12)

    def test_more_failures_than_units_is_refused(self):
        with self.assertRaises(ValueError):
            escape_rate(13, 12)

    def test_a_negative_failure_count_is_refused(self):
        with self.assertRaises(ValueError):
            escape_rate(-1, 12)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_capable_campaign_confirms_workmanship(self):
        result = assess_acceptance_purpose(CAMPAIGN_CASE)
        self.assertEqual(result["verdict"], WORKMANSHIP_CONFIRMED)
        self.assertTrue(result["screen_capable"])
        self.assertTrue(result["workmanship_confirmed"])
        self.assertEqual(result["findings"], [])

    def test_an_opening_cycle_failure_is_reported_as_revealed(self):
        result = assess_acceptance_purpose(_case(failure_cycles=(1,)))
        self.assertEqual(result["verdict"], INFANT_MORTALITY_REVEALED)
        self.assertTrue(result["infant_mortality_revealed"])
        self.assertFalse(result["workmanship_confirmed"])
        self.assertTrue(any("early-life escapes" in f for f in result["findings"]))

    def test_a_late_failure_is_escalated_rather_than_charged_to_the_supplier(self):
        result = assess_acceptance_purpose(_case(failure_cycles=(7,)))
        self.assertEqual(result["verdict"], PURPOSE_NOT_SERVED)
        self.assertFalse(result["infant_mortality_revealed"])
        self.assertTrue(any("escalated" in f for f in result["findings"]))

    def test_too_few_cycles_cannot_serve_either_purpose(self):
        result = assess_acceptance_purpose(
            _case(acceptance_profile=_acceptance(cycles=3))
        )
        self.assertEqual(result["verdict"], PURPOSE_NOT_SERVED)
        self.assertFalse(result["screen_capable"])
        self.assertTrue(
            any("early-life escape" in f for f in result["findings"])
        )
        self.assertLess(result["acceptance_cycles"], MIN_ACCEPTANCE_CYCLES)

    def test_a_shallow_range_reveals_nothing(self):
        result = assess_acceptance_purpose(
            _case(acceptance_profile=_acceptance(hot_k=373.15, cold_k=333.15))
        )
        self.assertEqual(result["verdict"], PURPOSE_NOT_SERVED)
        self.assertTrue(any("too shallow" in f for f in result["findings"]))
        self.assertLess(result["acceptance_range_k"], MIN_CYCLE_RANGE_K)

    def test_a_short_hot_dwell_is_a_finding_against_the_campaign(self):
        result = assess_acceptance_purpose(
            _case(acceptance_profile=_acceptance(hot_dwell_min=10.0))
        )
        self.assertEqual(result["verdict"], PURPOSE_NOT_SERVED)
        self.assertTrue(any("hot dwell" in f for f in result["findings"]))
        self.assertFalse(result["hot_soak"]["adequate"])

    def test_a_short_cold_dwell_is_a_finding_against_the_campaign(self):
        result = assess_acceptance_purpose(
            _case(acceptance_profile=_acceptance(cold_dwell_min=10.0))
        )
        self.assertTrue(any("cold dwell" in f for f in result["findings"]))
        self.assertFalse(result["cold_soak"]["adequate"])

    def test_a_campaign_that_eats_the_qualification_life_is_refused(self):
        result = assess_acceptance_purpose(
            _case(acceptance_profile=_acceptance(cycles=500))
        )
        self.assertEqual(result["verdict"], PURPOSE_NOT_SERVED)
        self.assertTrue(
            any("demonstrated fatigue life" in f for f in result["findings"])
        )

    def test_the_escape_rate_is_carried_into_the_result(self):
        result = assess_acceptance_purpose(_case(failure_cycles=(1, 2)))
        self.assertAlmostEqual(result["escape_rate"], 2.0 / 12.0, places=12)
        self.assertEqual(result["grouped_failures"]["infant-mortality"], (1, 2))

    def test_the_early_window_is_reported_with_the_verdict(self):
        result = assess_acceptance_purpose(CAMPAIGN_CASE)
        self.assertEqual(result["early_life_cycle_count"], 2)
        self.assertAlmostEqual(
            result["campaign_duration_h"], 140.0 * 8.0 / 60.0, places=6
        )

    def test_a_case_without_a_qualification_profile_is_refused(self):
        case = _case()
        del case["qualification_profile"]
        with self.assertRaises(ValueError):
            assess_acceptance_purpose(case)

    def test_a_case_without_a_unit_count_is_refused(self):
        case = _case()
        del case["unit_count"]
        with self.assertRaises(ValueError):
            assess_acceptance_purpose(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_purpose("acceptance campaign")


if __name__ == "__main__":
    unittest.main()

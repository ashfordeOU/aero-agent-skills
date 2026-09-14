#!/usr/bin/env python3
"""Contract test for the blocking diode surge test, clause 12.6.17 (offline)."""

import copy
import unittest

from e2008_blocking_diode_surge_test_logic import (
    DEFAULT_DEVICE_RATING,
    DEFAULT_SURGE_CRITERIA,
    DEFAULT_SURGE_PROFILE,
    DEFICIENCY_NO_HEADROOM,
    DEFICIENCY_NO_READOUT,
    DEFICIENCY_NO_RECOVERY,
    DEFICIENCY_OVER_STRESSED,
    DEFICIENCY_PEAK_TOO_LOW,
    DEFICIENCY_PULSE_TOO_LONG,
    DEFICIENCY_UNDER_STRESSED,
    GRADED_PARAMETERS,
    OBSERVABLE_CONDITIONS,
    PROFILE_ADEQUATE,
    PROFILE_INADEQUATE,
    PULSE_WAVEFORMS,
    SPECIMEN_FAILED,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_WITHSTOOD,
    SURGE_TEST_FAILED,
    SURGE_TEST_NOT_EVALUABLE,
    SURGE_TEST_PASSED,
    assess_surge_profile,
    assess_surge_specimen,
    assess_surge_test,
    degradation_sense,
    graded_parameters,
    junction_temperature_rise,
    observable_conditions,
    pulse_action_integral,
    pulse_waveforms,
    surge_ratio,
    train_action_integral,
    validate_device_rating,
    validate_surge_criteria,
    validate_surge_profile,
    waveform_action_factor,
    waveform_mean_factor,
)

PRE = {
    "forward-voltage-drop": 0.90,
    "reverse-leakage-current": 1.0e-6,
}


def _profile(**overrides):
    profile = copy.deepcopy(DEFAULT_SURGE_PROFILE)
    profile.update(overrides)
    return profile


def _rating(**overrides):
    rating = copy.deepcopy(DEFAULT_DEVICE_RATING)
    rating.update(overrides)
    return rating


def _specimen(specimen_id="bd-001", post=None, conditions=None, pre=None):
    return {
        "specimen_id": specimen_id,
        "pre_surge_readings": dict(pre if pre is not None else PRE),
        "post_surge_readings": dict(post if post is not None else PRE),
        "observed_conditions": list(conditions or []),
    }


def _campaign(specimens=None, **overrides):
    campaign = {
        "campaign_id": "bd-surge-12-6-17",
        "profile": _profile(),
        "rating": _rating(),
        "specimens": specimens
        if specimens is not None
        else [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)],
    }
    campaign.update(overrides)
    return campaign


class VocabularyTests(unittest.TestCase):
    def test_waveforms_come_back_as_a_tuple_copy(self):
        waveforms = pulse_waveforms()
        self.assertEqual(waveforms, PULSE_WAVEFORMS)
        self.assertIsInstance(waveforms, tuple)

    def test_graded_parameters_come_back_as_a_tuple_copy(self):
        parameters = graded_parameters()
        self.assertEqual(parameters, GRADED_PARAMETERS)
        self.assertIsInstance(parameters, tuple)

    def test_observable_conditions_include_an_open_circuit(self):
        conditions = observable_conditions()
        self.assertEqual(conditions, OBSERVABLE_CONDITIONS)
        self.assertIn("diode-open-circuit", conditions)

    def test_leakage_degrades_upwards(self):
        self.assertEqual(degradation_sense("reverse-leakage-current"), "increase")

    def test_unknown_parameter_has_no_sense(self):
        with self.assertRaises(ValueError):
            degradation_sense("forward-optimism")

    def test_unknown_waveform_has_no_shape_factor(self):
        with self.assertRaises(ValueError):
            waveform_action_factor("sawtooth-of-theseus")

    def test_unknown_waveform_has_no_mean_factor(self):
        with self.assertRaises(ValueError):
            waveform_mean_factor("sawtooth-of-theseus")


class PulseArithmeticTests(unittest.TestCase):
    def test_a_rectangular_pulse_carries_its_full_action_integral(self):
        self.assertAlmostEqual(
            pulse_action_integral(10.0, 0.01, "rectangular"), 1.0, places=9
        )

    def test_a_half_sine_pulse_carries_half_of_it(self):
        self.assertAlmostEqual(
            pulse_action_integral(10.0, 0.01, "half-sine"), 0.5, places=9
        )

    def test_shape_changes_the_stress_at_equal_peak_and_width(self):
        rectangular = pulse_action_integral(30.0, 0.01, "rectangular")
        triangular = pulse_action_integral(30.0, 0.01, "triangular")
        self.assertAlmostEqual(triangular * 3.0, rectangular, places=9)

    def test_the_train_scales_with_the_pulse_count(self):
        one = pulse_action_integral(30.0, 0.01, "half-sine")
        three = train_action_integral(30.0, 0.01, "half-sine", 3)
        self.assertAlmostEqual(three, one * 3.0, places=9)

    def test_surge_ratio_is_peak_over_rated_average(self):
        self.assertAlmostEqual(surge_ratio(30.0, 2.0), 15.0, places=9)

    def test_a_zero_rated_average_is_rejected(self):
        with self.assertRaises(ValueError):
            surge_ratio(30.0, 0.0)

    def test_a_negative_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            pulse_action_integral(-30.0, 0.01, "half-sine")

    def test_a_boolean_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            pulse_action_integral(True, 0.01, "half-sine")

    def test_a_zero_pulse_count_is_rejected(self):
        with self.assertRaises(ValueError):
            train_action_integral(30.0, 0.01, "half-sine", 0)

    def test_junction_rise_is_energy_over_thermal_capacity(self):
        rise = junction_temperature_rise(10.0, 0.01, "rectangular", 1.0, 0.001)
        self.assertAlmostEqual(rise, 100.0, places=9)

    def test_a_zero_thermal_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_rise(10.0, 0.01, "rectangular", 1.0, 0.0)


class ValidationTests(unittest.TestCase):
    def test_default_rating_validates(self):
        self.assertIs(validate_device_rating(DEFAULT_DEVICE_RATING), DEFAULT_DEVICE_RATING)

    def test_default_profile_validates(self):
        self.assertIs(validate_surge_profile(DEFAULT_SURGE_PROFILE), DEFAULT_SURGE_PROFILE)

    def test_default_criteria_validate(self):
        self.assertIs(
            validate_surge_criteria(DEFAULT_SURGE_CRITERIA), DEFAULT_SURGE_CRITERIA
        )

    def test_non_mapping_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_device_rating("a sturdy little diode")

    def test_rating_without_a_withstand_rejected(self):
        rating = _rating()
        del rating["i2t_withstand_a2s"]
        with self.assertRaises(ValueError):
            validate_device_rating(rating)

    def test_profile_with_a_non_boolean_readout_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_surge_profile(_profile(post_surge_readout_scheduled="yes"))

    def test_profile_with_an_unknown_waveform_rejected(self):
        with self.assertRaises(ValueError):
            validate_surge_profile(_profile(waveform="square-ish"))

    def test_criteria_without_a_specification_reference_rejected(self):
        broken = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        broken["specification_reference"] = "   "
        with self.assertRaises(ValueError):
            validate_surge_criteria(broken)

    def test_criteria_whose_floor_sits_above_its_ceiling_rejected(self):
        broken = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        broken["min_demonstrated_withstand_fraction"] = 0.95
        broken["max_withstand_overstress_fraction"] = 0.50
        with self.assertRaises(ValueError):
            validate_surge_criteria(broken)

    def test_criteria_naming_an_unknown_graded_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        broken["post_surge_limits"]["diode-mood"] = 1.0
        with self.assertRaises(ValueError):
            validate_surge_criteria(broken)

    def test_criteria_naming_an_unknown_condition_rejected(self):
        broken = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        broken["disqualifying_conditions"] = ("diode-looks-tired",)
        with self.assertRaises(ValueError):
            validate_surge_criteria(broken)

    def test_criteria_with_an_empty_condition_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        broken["disqualifying_conditions"] = ()
        with self.assertRaises(ValueError):
            validate_surge_criteria(broken)


class ProfileAdequacyTests(unittest.TestCase):
    def test_the_default_train_is_an_adequate_surge(self):
        report = assess_surge_profile()
        self.assertEqual(report["verdict"], PROFILE_ADEQUATE)
        self.assertEqual(report["deficiencies"], [])
        self.assertEqual(report["findings"], [])

    def test_the_demonstrated_fraction_is_reported(self):
        report = assess_surge_profile()
        self.assertAlmostEqual(report["demonstrated_withstand_fraction"], 0.9, places=9)

    def test_a_peak_near_the_rated_average_is_not_a_surge(self):
        report = assess_surge_profile(_profile(peak_current_a=4.0))
        self.assertEqual(report["verdict"], PROFILE_INADEQUATE)
        self.assertIn(DEFICIENCY_PEAK_TOO_LOW, report["deficiencies"])

    def test_a_peak_landing_on_the_demanded_multiple_is_admissible(self):
        criteria = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        criteria["min_peak_to_rated_multiple"] = 15.0
        report = assess_surge_profile(_profile(), _rating(), criteria)
        self.assertNotIn(DEFICIENCY_PEAK_TOO_LOW, report["deficiencies"])

    def test_a_long_pulse_is_an_overload_not_a_surge(self):
        report = assess_surge_profile(
            _profile(pulse_duration_s=0.5), _rating(i2t_withstand_a2s=300.0)
        )
        self.assertIn(DEFICIENCY_PULSE_TOO_LONG, report["deficiencies"])

    def test_a_pulse_landing_on_the_duration_limit_is_still_a_surge(self):
        report = assess_surge_profile(
            _profile(pulse_duration_s=0.020), _rating(i2t_withstand_a2s=10.0)
        )
        self.assertNotIn(DEFICIENCY_PULSE_TOO_LONG, report["deficiencies"])

    def test_a_feeble_pulse_demonstrates_nothing(self):
        report = assess_surge_profile(_profile(), _rating(i2t_withstand_a2s=400.0))
        self.assertIn(DEFICIENCY_UNDER_STRESSED, report["deficiencies"])

    def test_a_pulse_past_the_withstand_destroys_parts_by_design(self):
        report = assess_surge_profile(_profile(), _rating(i2t_withstand_a2s=1.0))
        self.assertIn(DEFICIENCY_OVER_STRESSED, report["deficiencies"])

    def test_a_pulse_landing_exactly_on_the_withstand_is_admissible(self):
        report = assess_surge_profile(_profile(), _rating(i2t_withstand_a2s=4.5))
        self.assertNotIn(DEFICIENCY_OVER_STRESSED, report["deficiencies"])
        self.assertNotIn(DEFICIENCY_UNDER_STRESSED, report["deficiencies"])
        self.assertAlmostEqual(report["demonstrated_withstand_fraction"], 1.0, places=9)

    def test_a_junction_driven_to_its_ceiling_loses_its_headroom(self):
        report = assess_surge_profile(
            _profile(), _rating(thermal_capacity_j_per_k=0.0008)
        )
        self.assertIn(DEFICIENCY_NO_HEADROOM, report["deficiencies"])

    def test_pulses_too_close_together_do_not_let_the_junction_recover(self):
        report = assess_surge_profile(_profile(inter_pulse_interval_s=2.0))
        self.assertIn(DEFICIENCY_NO_RECOVERY, report["deficiencies"])

    def test_a_single_pulse_needs_no_recovery_interval(self):
        report = assess_surge_profile(
            _profile(pulse_count=1, inter_pulse_interval_s=0.0)
        )
        self.assertNotIn(DEFICIENCY_NO_RECOVERY, report["deficiencies"])

    def test_an_interval_landing_on_the_minimum_is_admissible(self):
        report = assess_surge_profile(_profile(inter_pulse_interval_s=60.0))
        self.assertNotIn(DEFICIENCY_NO_RECOVERY, report["deficiencies"])

    def test_a_train_with_no_closing_readout_cannot_sentence_anything(self):
        report = assess_surge_profile(_profile(post_surge_readout_scheduled=False))
        self.assertIn(DEFICIENCY_NO_READOUT, report["deficiencies"])

    def test_every_deficiency_is_named_not_only_the_first(self):
        report = assess_surge_profile(
            _profile(
                peak_current_a=3.0,
                inter_pulse_interval_s=1.0,
                post_surge_readout_scheduled=False,
            )
        )
        self.assertGreaterEqual(len(report["deficiencies"]), 3)

    def test_the_train_action_integral_counts_every_pulse(self):
        report = assess_surge_profile()
        self.assertAlmostEqual(
            report["train_action_integral"],
            report["pulse_action_integral"] * 3.0,
            places=9,
        )


class SpecimenTests(unittest.TestCase):
    def test_an_unchanged_device_withstood_the_train(self):
        result = assess_surge_specimen(_specimen())
        self.assertEqual(result["verdict"], SPECIMEN_WITHSTOOD)
        self.assertEqual(result["failure_modes"], [])

    def test_a_forward_drop_that_ran_away_fails_the_device(self):
        post = dict(PRE)
        post["forward-voltage-drop"] = 1.40
        result = assess_surge_specimen(_specimen(post=post))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])

    def test_a_small_drift_can_still_break_the_post_surge_limit(self):
        pre = dict(PRE)
        pre["forward-voltage-drop"] = 1.08
        post = dict(pre)
        post["forward-voltage-drop"] = 1.14
        result = assess_surge_specimen(_specimen(pre=pre, post=post))
        self.assertIn(
            "forward-voltage-drop-outside-post-surge-limit", result["failure_modes"]
        )
        self.assertNotIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])

    def test_a_large_drift_can_still_sit_inside_the_post_surge_limit(self):
        pre = dict(PRE)
        pre["forward-voltage-drop"] = 0.50
        post = dict(pre)
        post["forward-voltage-drop"] = 0.90
        result = assess_surge_specimen(_specimen(pre=pre, post=post))
        self.assertIn("forward-voltage-drop-drift-exceeded", result["failure_modes"])
        self.assertNotIn(
            "forward-voltage-drop-outside-post-surge-limit", result["failure_modes"]
        )

    def test_a_device_that_improved_is_inside_its_allowance(self):
        post = dict(PRE)
        post["reverse-leakage-current"] = 4.0e-7
        result = assess_surge_specimen(_specimen(post=post))
        self.assertEqual(result["verdict"], SPECIMEN_WITHSTOOD)

    def test_a_numerically_clean_device_still_fails_on_a_lifted_bond_wire(self):
        result = assess_surge_specimen(_specimen(conditions=["bond-wire-lifted"]))
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)
        self.assertEqual(result["failure_modes"], ["bond-wire-lifted"])

    def test_a_condition_the_specification_omits_does_not_fail_the_device(self):
        criteria = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        criteria["disqualifying_conditions"] = ("die-crack",)
        result = assess_surge_specimen(
            _specimen(conditions=["package-discolouration"]), criteria
        )
        self.assertEqual(result["verdict"], SPECIMEN_WITHSTOOD)
        self.assertEqual(result["observed_conditions"], ["package-discolouration"])

    def test_a_missing_post_reading_is_not_evaluated_rather_than_withstood(self):
        post = dict(PRE)
        del post["reverse-leakage-current"]
        result = assess_surge_specimen(_specimen(post=post))
        self.assertEqual(result["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(result["unread_parameters"], ["reverse-leakage-current"])
        self.assertFalse(result["failed"])

    def test_a_missing_post_reading_does_not_hide_a_real_failure(self):
        post = dict(PRE)
        del post["reverse-leakage-current"]
        result = assess_surge_specimen(
            _specimen(post=post, conditions=["metallisation-melt"])
        )
        self.assertEqual(result["verdict"], SPECIMEN_FAILED)

    def test_every_mode_is_named_not_only_the_first(self):
        post = {"forward-voltage-drop": 1.60, "reverse-leakage-current": 9.0e-5}
        result = assess_surge_specimen(_specimen(post=post, conditions=["die-crack"]))
        self.assertGreaterEqual(len(result["failure_modes"]), 5)

    def test_an_unknown_observed_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_surge_specimen(_specimen(conditions=["diode-haunted"]))

    def test_a_specimen_without_an_identifier_rejected(self):
        specimen = _specimen()
        del specimen["specimen_id"]
        with self.assertRaises(ValueError):
            assess_surge_specimen(specimen)

    def test_non_sequence_observed_conditions_rejected(self):
        specimen = _specimen()
        specimen["observed_conditions"] = "die-crack"
        with self.assertRaises(ValueError):
            assess_surge_specimen(specimen)

    def test_findings_name_the_device(self):
        post = dict(PRE)
        post["reverse-leakage-current"] = 8.0e-5
        result = assess_surge_specimen(_specimen("bd-042", post=post))
        self.assertTrue(any("bd-042" in finding for finding in result["findings"]))


class CampaignTests(unittest.TestCase):
    def test_a_clean_campaign_passes(self):
        result = assess_surge_test(_campaign())
        self.assertEqual(result["verdict"], SURGE_TEST_PASSED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=9)

    def test_one_failed_device_fails_a_zero_allowance_campaign(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_surge_test(_campaign(specimens))
        self.assertEqual(result["verdict"], SURGE_TEST_FAILED)
        self.assertEqual(result["failed_specimen_ids"], ["bd-001"])

    def test_the_failed_share_is_reported(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_surge_test(_campaign(specimens))
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_an_inadequate_profile_leaves_the_campaign_unevaluable(self):
        campaign = _campaign()
        campaign["profile"] = _profile(peak_current_a=3.0)
        result = assess_surge_test(campaign)
        self.assertEqual(result["verdict"], SURGE_TEST_NOT_EVALUABLE)

    def test_a_clean_result_under_an_inadequate_profile_is_not_a_pass(self):
        campaign = _campaign()
        campaign["profile"] = _profile(post_surge_readout_scheduled=False)
        result = assess_surge_test(campaign)
        self.assertEqual(result["failed_specimen_ids"], [])
        self.assertEqual(result["verdict"], SURGE_TEST_NOT_EVALUABLE)

    def test_an_unevaluated_device_blocks_the_campaign_verdict(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        del specimens[2]["post_surge_readings"]["forward-voltage-drop"]
        result = assess_surge_test(_campaign(specimens))
        self.assertEqual(result["verdict"], SURGE_TEST_NOT_EVALUABLE)
        self.assertEqual(result["unevaluated_specimen_ids"], ["bd-003"])

    def test_modes_are_grouped_by_specimen(self):
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[1]["observed_conditions"] = ["diode-short-circuit"]
        specimens[3]["observed_conditions"] = ["diode-short-circuit"]
        result = assess_surge_test(_campaign(specimens))
        self.assertEqual(
            result["modes_by_specimen"]["diode-short-circuit"], ["bd-002", "bd-004"]
        )

    def test_assessments_come_back_in_identifier_order(self):
        specimens = [_specimen("bd-00%d" % n) for n in (4, 1, 3, 2)]
        result = assess_surge_test(_campaign(specimens))
        ids = [entry["specimen_id"] for entry in result["specimen_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_specimen_identifier_rejected(self):
        specimens = [_specimen("bd-001"), _specimen("bd-001")]
        with self.assertRaises(ValueError):
            assess_surge_test(_campaign(specimens))

    def test_an_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_surge_test(_campaign([]))

    def test_a_campaign_without_an_identifier_rejected(self):
        campaign = _campaign()
        del campaign["campaign_id"]
        with self.assertRaises(ValueError):
            assess_surge_test(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_surge_test([_specimen()])

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        criteria = copy.deepcopy(DEFAULT_SURGE_CRITERIA)
        criteria["max_failed_fraction"] = 0.25
        specimens = [_specimen("bd-00%d" % n) for n in (1, 2, 3, 4)]
        specimens[0]["observed_conditions"] = ["die-crack"]
        result = assess_surge_test(_campaign(specimens), criteria)
        self.assertEqual(result["verdict"], SURGE_TEST_PASSED)
        self.assertTrue(result["failed_share_within_allowance"])

    def test_the_campaign_carries_the_profile_report(self):
        result = assess_surge_test(_campaign())
        self.assertEqual(result["profile_report"]["verdict"], PROFILE_ADEQUATE)


if __name__ == "__main__":
    unittest.main()

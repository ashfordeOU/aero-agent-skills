"""Contract tests for the clause 4.3.8 Class 1 radiation verification logic."""

import unittest

from q60_class_1_radiation_verification_testing_logic import (
    DEFAULT_REQUIRED_MARGIN,
    DEFAULT_SAMPLE_CREDIT,
    DESTRUCTIVE_EVENT_TYPES,
    MINIMUM_IRRADIATED_SAMPLE,
    SENSITIVITY_GRADES,
    assess_radiation_verification,
    assess_single_event_response,
    assess_total_dose_adequacy,
    demonstrated_lot_capability,
    low_dose_rate_test_required,
    radiation_design_margin,
    radiation_sensitivity,
    sample_credit_factor,
    verification_test_required,
)

REGISTER = {
    "cmos-bulk": "high",
    "bipolar-linear": "moderate",
    "wirewound-resistor": "low",
}


class SensitivityRegisterTests(unittest.TestCase):
    def test_declared_grade_returned(self):
        self.assertEqual(radiation_sensitivity(REGISTER, "cmos-bulk"), "high")

    def test_family_name_is_case_and_space_insensitive(self):
        self.assertEqual(radiation_sensitivity(REGISTER, "  CMOS-Bulk "), "high")

    def test_unlisted_family_refused(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity(REGISTER, "silicon-carbide-fet")

    def test_empty_register_refused(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity({}, "cmos-bulk")

    def test_unrecognised_grade_refused(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity({"cmos-bulk": "somewhat"}, "cmos-bulk")

    def test_blank_family_refused(self):
        with self.assertRaises(ValueError):
            radiation_sensitivity(REGISTER, "   ")

    def test_grade_vocabulary_is_three_wide(self):
        self.assertEqual(SENSITIVITY_GRADES, ("low", "moderate", "high"))


class TestNecessityTests(unittest.TestCase):
    def test_low_sensitivity_needs_no_test(self):
        self.assertFalse(verification_test_required("low", 10000.0))

    def test_high_sensitivity_without_heritage_needs_a_test(self):
        self.assertTrue(verification_test_required("high", 10000.0))

    def test_heritage_short_of_the_margin_needs_a_test(self):
        self.assertTrue(
            verification_test_required("high", 10000.0, 15000.0, 2.0)
        )

    def test_heritage_exactly_at_the_margin_needs_no_test(self):
        self.assertFalse(
            verification_test_required("high", 10000.0, 20000.0, 2.0)
        )

    def test_heritage_above_the_margin_needs_no_test(self):
        self.assertFalse(
            verification_test_required("moderate", 10000.0, 40000.0, 2.0)
        )

    def test_unknown_grade_refused(self):
        with self.assertRaises(ValueError):
            verification_test_required("severe", 10000.0)

    def test_negative_mission_dose_refused(self):
        with self.assertRaises(ValueError):
            verification_test_required("high", -1.0)

    def test_default_margin_is_two(self):
        self.assertAlmostEqual(DEFAULT_REQUIRED_MARGIN, 2.0, places=9)


class SampleCreditTests(unittest.TestCase):
    def test_wide_sample_earns_full_credit(self):
        self.assertAlmostEqual(sample_credit_factor(11), 1.0, places=9)

    def test_sample_above_the_widest_band_still_earns_full_credit(self):
        self.assertAlmostEqual(sample_credit_factor(40), 1.0, places=9)

    def test_middle_sample_earns_partial_credit(self):
        self.assertAlmostEqual(sample_credit_factor(5), 0.8, places=9)

    def test_smallest_credited_sample(self):
        self.assertAlmostEqual(sample_credit_factor(3), 0.6, places=9)

    def test_uncredited_sample_refused(self):
        with self.assertRaises(ValueError):
            sample_credit_factor(2)

    def test_zero_sample_refused(self):
        with self.assertRaises(ValueError):
            sample_credit_factor(0)

    def test_float_sample_refused(self):
        with self.assertRaises(ValueError):
            sample_credit_factor(5.0)

    def test_credit_above_one_refused(self):
        with self.assertRaises(ValueError):
            sample_credit_factor(5, ((3, 1.4),))

    def test_malformed_credit_entry_refused(self):
        with self.assertRaises(ValueError):
            sample_credit_factor(5, ((3,),))

    def test_default_credit_table_is_ordered_downward(self):
        factors = [factor for _, factor in DEFAULT_SAMPLE_CREDIT]
        self.assertEqual(factors, sorted(factors, reverse=True))


class LotCapabilityTests(unittest.TestCase):
    def test_lowest_dose_drives_the_lot(self):
        out = demonstrated_lot_capability([80000.0, 50000.0, 90000.0])
        self.assertAlmostEqual(out["lowest_failure_free_dose"], 50000.0, places=9)

    def test_credit_is_applied_to_the_lowest_dose(self):
        out = demonstrated_lot_capability([80000.0, 50000.0, 90000.0])
        self.assertAlmostEqual(out["lot_capability"], 30000.0, places=9)

    def test_wide_sample_keeps_the_whole_dose(self):
        out = demonstrated_lot_capability([40000.0] * 12)
        self.assertAlmostEqual(out["lot_capability"], 40000.0, places=9)

    def test_sample_size_reported(self):
        out = demonstrated_lot_capability([40000.0] * 6)
        self.assertEqual(out["sample_size"], 6)

    def test_sample_below_the_minimum_refused(self):
        with self.assertRaises(ValueError):
            demonstrated_lot_capability([40000.0, 41000.0])

    def test_empty_sample_refused(self):
        with self.assertRaises(ValueError):
            demonstrated_lot_capability([])

    def test_non_positive_dose_refused(self):
        with self.assertRaises(ValueError):
            demonstrated_lot_capability([40000.0, 0.0, 42000.0])

    def test_non_numeric_dose_refused(self):
        with self.assertRaises(ValueError):
            demonstrated_lot_capability([40000.0, "40000", 42000.0])

    def test_minimum_sample_default_is_three(self):
        self.assertEqual(MINIMUM_IRRADIATED_SAMPLE, 3)


class TotalDoseTests(unittest.TestCase):
    def test_margin_is_capability_over_mission(self):
        self.assertAlmostEqual(
            radiation_design_margin(30000.0, 10000.0), 3.0, places=9
        )

    def test_adequacy_at_exactly_the_required_margin(self):
        out = assess_total_dose_adequacy(20000.0, 10000.0, 2.0)
        self.assertAlmostEqual(out["radiation_design_margin"], 2.0, places=9)
        self.assertTrue(out["compliant"])

    def test_shortfall_is_zero_when_compliant(self):
        out = assess_total_dose_adequacy(30000.0, 10000.0, 2.0)
        self.assertAlmostEqual(out["dose_shortfall"], 0.0, places=9)

    def test_shortfall_reported_when_short(self):
        out = assess_total_dose_adequacy(15000.0, 10000.0, 2.0)
        self.assertFalse(out["compliant"])
        self.assertAlmostEqual(out["dose_shortfall"], 5000.0, places=9)

    def test_required_capability_reported(self):
        out = assess_total_dose_adequacy(15000.0, 10000.0, 2.0)
        self.assertAlmostEqual(out["required_capability_dose"], 20000.0, places=9)

    def test_zero_mission_dose_refused(self):
        with self.assertRaises(ValueError):
            assess_total_dose_adequacy(15000.0, 0.0)


class LowDoseRateTests(unittest.TestCase):
    def test_listed_family_under_the_threshold_owes_a_test(self):
        self.assertTrue(
            low_dose_rate_test_required(
                "bipolar-linear", 0.002, ["bipolar-linear"], 0.01
            )
        )

    def test_listed_family_at_the_threshold_owes_nothing(self):
        self.assertFalse(
            low_dose_rate_test_required(
                "bipolar-linear", 0.01, ["bipolar-linear"], 0.01
            )
        )

    def test_unlisted_family_owes_nothing(self):
        self.assertFalse(
            low_dose_rate_test_required("cmos-bulk", 0.002, ["bipolar-linear"], 0.01)
        )

    def test_family_list_may_be_a_set(self):
        self.assertTrue(
            low_dose_rate_test_required(
                "bipolar-linear", 0.002, {"bipolar-linear"}, 0.01
            )
        )

    def test_non_sequence_family_list_refused(self):
        with self.assertRaises(ValueError):
            low_dose_rate_test_required("bipolar-linear", 0.002, "bipolar-linear")


class SingleEventTests(unittest.TestCase):
    def test_threshold_above_requirement_is_adequate(self):
        out = assess_single_event_response(60.0, 37.0)
        self.assertTrue(out["compliant"])

    def test_threshold_exactly_at_the_requirement_is_adequate(self):
        out = assess_single_event_response(37.0, 37.0)
        self.assertTrue(out["upset_threshold_adequate"])
        self.assertTrue(out["compliant"])

    def test_threshold_below_the_requirement_fails(self):
        out = assess_single_event_response(20.0, 37.0)
        self.assertFalse(out["compliant"])

    def test_destructive_event_below_requirement_vetoes_a_wide_threshold(self):
        out = assess_single_event_response(
            90.0, 37.0, [{"type": "single-event-latch-up", "onset_let": 20.0}]
        )
        self.assertTrue(out["upset_threshold_adequate"])
        self.assertFalse(out["compliant"])

    def test_destructive_event_above_requirement_does_not_veto(self):
        out = assess_single_event_response(
            90.0, 37.0, [{"type": "single-event-burnout", "onset_let": 60.0}]
        )
        self.assertTrue(out["compliant"])
        self.assertEqual(out["destructive_events_below_requirement"], [])

    def test_unrecognised_event_type_refused(self):
        with self.assertRaises(ValueError):
            assess_single_event_response(
                90.0, 37.0, [{"type": "single-event-upset", "onset_let": 20.0}]
            )

    def test_event_missing_onset_refused(self):
        with self.assertRaises(ValueError):
            assess_single_event_response(
                90.0, 37.0, [{"type": "single-event-latch-up"}]
            )

    def test_destructive_vocabulary_holds_latch_up(self):
        self.assertIn("single-event-latch-up", DESTRUCTIVE_EVENT_TYPES)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "technology": "cmos-bulk",
            "sensitivity_register": REGISTER,
            "mission_dose": 10000.0,
            "required_margin": 2.0,
            "failure_free_doses": [50000.0, 60000.0, 70000.0],
            "threshold_let": 60.0,
            "required_let": 37.0,
        }
        spec.update(overrides)
        return spec

    def test_low_sensitivity_part_needs_no_test(self):
        out = assess_radiation_verification(
            self._spec(technology="wirewound-resistor")
        )
        self.assertEqual(out["disposition"], "no-test-required")

    def test_heritage_margin_waives_the_test(self):
        out = assess_radiation_verification(
            self._spec(heritage_capability_dose=25000.0)
        )
        self.assertEqual(out["disposition"], "no-test-required")

    def test_clean_evidence_passes(self):
        out = assess_radiation_verification(self._spec())
        self.assertEqual(out["disposition"], "verification-passed")

    def test_credited_capability_reported(self):
        out = assess_radiation_verification(self._spec())
        self.assertAlmostEqual(out["lot_capability"]["lot_capability"], 30000.0, places=9)

    def test_short_dose_margin_fails(self):
        out = assess_radiation_verification(
            self._spec(failure_free_doses=[20000.0, 25000.0, 30000.0])
        )
        self.assertEqual(out["disposition"], "failed-total-dose")

    def test_destructive_event_fails_before_the_dose_margin(self):
        out = assess_radiation_verification(
            self._spec(
                observed_events=[
                    {"type": "single-event-latch-up", "onset_let": 12.0}
                ]
            )
        )
        self.assertEqual(out["disposition"], "failed-single-event")

    def test_missing_low_dose_rate_test_is_incomplete_evidence(self):
        out = assess_radiation_verification(
            self._spec(
                technology="bipolar-linear",
                mission_dose_rate=0.001,
                low_dose_rate_families=["bipolar-linear"],
            )
        )
        self.assertEqual(out["disposition"], "evidence-incomplete")

    def test_performed_low_dose_rate_test_lets_the_assessment_run(self):
        out = assess_radiation_verification(
            self._spec(
                technology="bipolar-linear",
                mission_dose_rate=0.001,
                low_dose_rate_families=["bipolar-linear"],
                low_dose_rate_test_performed=True,
            )
        )
        self.assertEqual(out["disposition"], "verification-passed")

    def test_missing_sample_results_refused(self):
        spec = self._spec()
        del spec["failure_free_doses"]
        with self.assertRaises(ValueError):
            assess_radiation_verification(spec)

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["mission_dose"]
        with self.assertRaises(ValueError):
            assess_radiation_verification(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification(["technology"])

    def test_findings_name_the_credited_sample(self):
        out = assess_radiation_verification(self._spec())
        self.assertTrue(any("credited" in f for f in out["findings"]))


if __name__ == "__main__":
    unittest.main()

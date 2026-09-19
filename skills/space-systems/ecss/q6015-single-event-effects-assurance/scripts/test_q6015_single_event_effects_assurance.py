"""Contract test for the single event effects assurance leaf."""

import unittest

from q6015_single_event_effects_assurance_logic import (
    DESTRUCTIVE_LET_MARGIN,
    EVENT_TYPES,
    FINDING_NO_MITIGATION,
    FINDING_RATE_ABOVE_BUDGET,
    FINDING_TRIP_TOO_HIGH,
    FINDING_TRIP_TOO_SLOW,
    FINDING_VOLTAGE_TOO_HIGH,
    FINDING_WRONG_MITIGATION,
    SECONDS_PER_DAY,
    assess_event,
    assess_single_event_effects,
    environment_let_cutoff,
    event_is_destructive,
    event_rate_per_day,
    excluded_by_let_threshold,
    group_events_by_consequence,
    integral_flux_above_let,
    latchup_mitigation_findings,
    validate_event,
    validate_let_spectrum,
    validate_mitigation,
    voltage_derating_findings,
)

SPECTRUM = [
    (1.0, 1.0e-2),
    (10.0, 1.0e-4),
    (30.0, 1.0e-6),
    (60.0, 1.0e-8),
    (80.0, 1.0e-10),
]


def upset(eid="U1", **kw):
    record = {
        "id": eid,
        "event_type": "single-event-upset",
        "let_threshold_mev_cm2_mg": 10.0,
        "saturation_cross_section_cm2": 1.0e-6,
        "device_count": 1,
    }
    record.update(kw)
    return record


def latchup(eid="L1", **kw):
    record = {
        "id": eid,
        "event_type": "single-event-latchup",
        "let_threshold_mev_cm2_mg": 20.0,
        "mitigation": {
            "kind": "latchup-current-limiter",
            "trip_current_a": 0.4,
            "destructive_current_a": 1.0,
            "detection_time_s": 1.0e-4,
            "survivable_duration_s": 1.0e-3,
        },
    }
    record.update(kw)
    return record


def burnout(eid="B1", **kw):
    record = {
        "id": eid,
        "event_type": "single-event-burnout",
        "let_threshold_mev_cm2_mg": 20.0,
        "mitigation": {
            "kind": "voltage-derating",
            "applied_voltage_v": 40.0,
            "demonstrated_safe_voltage_v": 60.0,
        },
    }
    record.update(kw)
    return record


class TestEventGrouping(unittest.TestCase):
    def test_upset_is_recoverable(self):
        self.assertFalse(event_is_destructive("single-event-upset"))

    def test_latchup_is_destructive(self):
        self.assertTrue(event_is_destructive("single-event-latchup"))

    def test_unknown_event_type_raises(self):
        with self.assertRaises(ValueError):
            event_is_destructive("single-event-hiccup")

    def test_grouping_splits_the_two_consequences(self):
        groups = group_events_by_consequence(
            ["single-event-upset", "single-event-burnout"]
        )
        self.assertEqual(groups["recoverable"], ["single-event-upset"])
        self.assertEqual(groups["destructive"], ["single-event-burnout"])

    def test_empty_grouping_raises(self):
        with self.assertRaises(ValueError):
            group_events_by_consequence([])

    def test_every_event_type_has_a_mitigation_route(self):
        self.assertEqual(len(EVENT_TYPES), 6)


class TestSpectrum(unittest.TestCase):
    def test_valid_spectrum_normalizes(self):
        self.assertEqual(len(validate_let_spectrum(SPECTRUM)), 5)

    def test_rising_flux_raises(self):
        with self.assertRaises(ValueError):
            validate_let_spectrum([(1.0, 1.0e-8), (10.0, 1.0e-2)])

    def test_spectrum_that_never_falls_off_raises(self):
        with self.assertRaises(ValueError):
            validate_let_spectrum([(1.0, 1.0e-2), (10.0, 9.0e-3)])

    def test_cutoff_is_the_top_tabulated_let(self):
        self.assertAlmostEqual(environment_let_cutoff(SPECTRUM), 80.0, places=9)

    def test_flux_at_a_tabulated_point_is_its_own_value(self):
        self.assertAlmostEqual(
            integral_flux_above_let(SPECTRUM, 30.0) / 1.0e-6, 1.0, places=9
        )

    def test_flux_above_the_cutoff_is_zero(self):
        self.assertEqual(integral_flux_above_let(SPECTRUM, 120.0), 0.0)

    def test_flux_below_the_span_is_refused(self):
        with self.assertRaises(ValueError):
            integral_flux_above_let(SPECTRUM, 0.1)

    def test_interpolated_flux_sits_between_neighbours(self):
        value = integral_flux_above_let(SPECTRUM, 20.0)
        self.assertLess(value, 1.0e-4)
        self.assertGreater(value, 1.0e-6)


class TestThresholdExclusion(unittest.TestCase):
    def test_threshold_above_the_cutoff_excludes_the_event(self):
        self.assertTrue(excluded_by_let_threshold(SPECTRUM, 120.0))

    def test_threshold_exactly_at_the_cutoff_excludes_the_event(self):
        self.assertTrue(excluded_by_let_threshold(SPECTRUM, 80.0))

    def test_threshold_inside_the_spectrum_does_not_exclude(self):
        self.assertFalse(excluded_by_let_threshold(SPECTRUM, 20.0))

    def test_margin_above_one_makes_exclusion_harder(self):
        self.assertFalse(excluded_by_let_threshold(SPECTRUM, 80.0, margin=1.5))

    def test_default_margin_is_documented(self):
        self.assertAlmostEqual(DESTRUCTIVE_LET_MARGIN, 1.0, places=9)

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            excluded_by_let_threshold(SPECTRUM, 0.0)


class TestEventRate(unittest.TestCase):
    def test_rate_is_flux_times_cross_section_times_seconds(self):
        rate = event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 1)
        self.assertAlmostEqual(rate / (1.0e-6 * 1.0e-6 * SECONDS_PER_DAY), 1.0, places=9)

    def test_device_count_scales_the_rate(self):
        one = event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 1)
        four = event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 4)
        self.assertAlmostEqual(four / one, 4.0, places=9)

    def test_reduction_factor_divides_the_rate(self):
        plain = event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 1)
        corrected = event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 1, 100.0)
        self.assertAlmostEqual(plain / corrected, 100.0, places=9)

    def test_reduction_below_one_raises(self):
        with self.assertRaises(ValueError):
            event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 1, 0.5)

    def test_zero_device_count_raises(self):
        with self.assertRaises(ValueError):
            event_rate_per_day(SPECTRUM, 30.0, 1.0e-6, 0)

    def test_threshold_above_cutoff_gives_no_events(self):
        self.assertEqual(event_rate_per_day(SPECTRUM, 120.0, 1.0e-6, 1), 0.0)


class TestMitigationRecords(unittest.TestCase):
    def test_absent_mitigation_normalizes_to_none(self):
        norm = validate_mitigation(None, "single-event-upset")
        self.assertEqual(norm["kind"], "none")
        self.assertAlmostEqual(norm["reduction_factor"], 1.0, places=9)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_mitigation({"kind": "crossed-fingers"}, "single-event-upset")

    def test_reduction_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_mitigation(
                {"kind": "error-detection-and-correction", "reduction_factor": 0.2},
                "single-event-upset",
            )

    def test_good_latchup_limiter_has_no_findings(self):
        self.assertEqual(latchup_mitigation_findings(latchup()["mitigation"]), [])

    def test_trip_at_the_destructive_current_is_a_finding(self):
        record = dict(latchup()["mitigation"])
        record["trip_current_a"] = 1.0
        self.assertIn(FINDING_TRIP_TOO_HIGH, latchup_mitigation_findings(record))

    def test_detection_slower_than_survival_is_a_finding(self):
        record = dict(latchup()["mitigation"])
        record["detection_time_s"] = 2.0e-3
        self.assertIn(FINDING_TRIP_TOO_SLOW, latchup_mitigation_findings(record))

    def test_negative_limiter_value_raises(self):
        record = dict(latchup()["mitigation"])
        record["trip_current_a"] = -0.1
        with self.assertRaises(ValueError):
            latchup_mitigation_findings(record)

    def test_derating_at_the_safe_voltage_passes(self):
        record = dict(burnout()["mitigation"])
        record["applied_voltage_v"] = 60.0
        self.assertEqual(voltage_derating_findings(record), [])

    def test_derating_above_the_safe_voltage_is_a_finding(self):
        record = dict(burnout()["mitigation"])
        record["applied_voltage_v"] = 70.0
        self.assertIn(FINDING_VOLTAGE_TOO_HIGH, voltage_derating_findings(record))


class TestEventValidation(unittest.TestCase):
    def test_non_mapping_event_raises(self):
        with self.assertRaises(ValueError):
            validate_event("U1")

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_event(upset(""))

    def test_recoverable_event_without_cross_section_raises(self):
        record = upset()
        del record["saturation_cross_section_cm2"]
        with self.assertRaises(ValueError):
            validate_event(record)

    def test_destructive_event_needs_no_cross_section(self):
        norm = validate_event(latchup())
        self.assertNotIn("saturation_cross_section_cm2", norm)

    def test_non_integer_device_count_raises(self):
        with self.assertRaises(ValueError):
            validate_event(upset("U1", device_count=2.5))


class TestAssessEvent(unittest.TestCase):
    def test_upset_inside_budget_is_compliant(self):
        result = assess_event(upset(), SPECTRUM, budget_per_day=1.0)
        self.assertTrue(result["compliant"])
        self.assertIsNotNone(result["rate_per_day"])

    def test_upset_above_budget_is_a_finding(self):
        result = assess_event(upset(), SPECTRUM, budget_per_day=1.0e-9)
        self.assertIn(FINDING_RATE_ABOVE_BUDGET, result["findings"])

    def test_upset_with_correction_can_come_back_inside_budget(self):
        bare = assess_event(upset(), SPECTRUM, budget_per_day=1.0e-6)
        fixed = assess_event(
            upset(
                mitigation={
                    "kind": "error-detection-and-correction",
                    "reduction_factor": 1000.0,
                }
            ),
            SPECTRUM,
            budget_per_day=1.0e-6,
        )
        self.assertFalse(bare["compliant"])
        self.assertTrue(fixed["compliant"])

    def test_latchup_limiter_on_an_upset_is_the_wrong_mitigation(self):
        result = assess_event(
            upset(mitigation={"kind": "latchup-current-limiter"}),
            SPECTRUM,
            budget_per_day=1.0,
        )
        self.assertIn(FINDING_WRONG_MITIGATION, result["findings"])

    def test_destructive_event_above_the_cutoff_needs_no_mitigation(self):
        result = assess_event(
            latchup("L9", let_threshold_mev_cm2_mg=100.0, mitigation=None), SPECTRUM
        )
        self.assertTrue(result["excluded_by_threshold"])
        self.assertTrue(result["compliant"])

    def test_destructive_event_inside_the_spectrum_without_mitigation_fails(self):
        result = assess_event(latchup("L2", mitigation=None), SPECTRUM)
        self.assertIn(FINDING_NO_MITIGATION, result["findings"])

    def test_good_latchup_limiter_clears_the_event(self):
        result = assess_event(latchup(), SPECTRUM)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["rate_per_day"])

    def test_burnout_with_derating_above_safe_voltage_fails(self):
        result = assess_event(
            burnout(
                "B2",
                mitigation={
                    "kind": "voltage-derating",
                    "applied_voltage_v": 80.0,
                    "demonstrated_safe_voltage_v": 60.0,
                },
            ),
            SPECTRUM,
        )
        self.assertIn(FINDING_VOLTAGE_TOO_HIGH, result["findings"])
        self.assertFalse(result["compliant"])

    def test_burnout_with_a_watchdog_is_the_wrong_mitigation(self):
        result = assess_event(
            burnout("B3", mitigation={"kind": "watchdog-reset"}), SPECTRUM
        )
        self.assertIn(FINDING_WRONG_MITIGATION, result["findings"])


class TestAssessment(unittest.TestCase):
    def test_mixed_set_reports_both_groups(self):
        report = assess_single_event_effects(
            [upset(), latchup(), burnout()], SPECTRUM, budget_per_day=1.0
        )
        self.assertEqual(report["destructive_ids"], ["B1", "L1"])
        self.assertTrue(report["compliant"])

    def test_total_rate_sums_the_recoverable_events(self):
        report = assess_single_event_effects(
            [upset("U1"), upset("U2")], SPECTRUM, budget_per_day=1.0
        )
        one = assess_event(upset(), SPECTRUM, budget_per_day=1.0)["rate_per_day"]
        self.assertAlmostEqual(report["total_rate_per_day"] / one, 2.0, places=9)

    def test_excluded_ids_are_listed(self):
        report = assess_single_event_effects(
            [latchup("L9", let_threshold_mev_cm2_mg=100.0, mitigation=None)], SPECTRUM
        )
        self.assertEqual(report["excluded_ids"], ["L9"])

    def test_one_failing_event_fails_the_equipment(self):
        report = assess_single_event_effects(
            [upset(), latchup("L2", mitigation=None)], SPECTRUM, budget_per_day=1.0
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["L2"])

    def test_duplicate_event_for_one_part_raises(self):
        with self.assertRaises(ValueError):
            assess_single_event_effects([upset("U1"), upset("U1")], SPECTRUM)

    def test_empty_event_list_raises(self):
        with self.assertRaises(ValueError):
            assess_single_event_effects([], SPECTRUM)

    def test_non_list_events_raises(self):
        with self.assertRaises(ValueError):
            assess_single_event_effects(upset(), SPECTRUM)


if __name__ == "__main__":
    unittest.main()

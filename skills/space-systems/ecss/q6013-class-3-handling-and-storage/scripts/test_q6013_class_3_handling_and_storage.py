"""Contract tests for the clause 6.4 class 3 handling and storage assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused storage policy,
the sensitivity banding and the minimum measure set each band owes, a
recorded equivalent measure credited and an unrecorded one refused, the band
this class will not relax at all, the duration-weighted excursion dose and
its severity, the humidity indicator states, the shelf-life margin and the
ranked storage verdict.
"""

import datetime
import unittest

from q6013_class_3_handling_and_storage_logic import (
    BASELINE_MEASURES,
    DEFAULT_STORAGE_POLICY,
    DOSE_CRITICAL,
    DOSE_MAJOR,
    DOSE_MINOR,
    DOSE_NONE,
    ESD_BANDS,
    INDICATOR_DRY,
    INDICATOR_MARGINAL,
    INDICATOR_SATURATED,
    NO_SUBSTITUTION_BANDS,
    QUARANTINED,
    RELEASED,
    RELEASED_WITH_ACTIONS,
    SENSITIVE_BANDS,
    SENSITIVE_EXTRA_MEASURES,
    SEVERITY_ORDER,
    assess_class_three_handling_and_storage,
    dose_severity,
    esd_band,
    excursion_dose,
    humidity_indicator_state,
    measure_gaps,
    minimum_measures,
    shelf_life_margin_days,
    storage_verdict,
    validate_storage_policy,
)

TEMPERATURE_LIMITS = (10.0, 30.0)
HUMIDITY_LIMITS = (20.0, 60.0)


def _policy(**overrides):
    policy = dict(DEFAULT_STORAGE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "withstand_volts": 2500.0,
        "measures_operated": list(BASELINE_MEASURES),
        "substitutions": {},
        "temperature_segments": [{"value": 22.0, "hours": 1000.0}],
        "temperature_limits": TEMPERATURE_LIMITS,
        "humidity_segments": [{"value": 45.0, "hours": 1000.0}],
        "humidity_limits": HUMIDITY_LIMITS,
        "moisture_barrier_intact": True,
        "desiccant_present": True,
        "indicator_reading_percent": 10.0,
        "indicator_limit_percent": 10.0,
        "storage_entry": "2025-01-01",
        "shelf_life_days": 365,
        "review_date": "2025-07-01",
    }
    case.update(overrides)
    return case


def _sensitive_case(**overrides):
    case = _case(
        withstand_volts=120.0,
        measures_operated=list(BASELINE_MEASURES) + list(SENSITIVE_EXTRA_MEASURES),
    )
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_storage_policy(DEFAULT_STORAGE_POLICY), DEFAULT_STORAGE_POLICY
        )

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_STORAGE_POLICY)
        del policy["major_dose"]
        with self.assertRaises(ValueError):
            validate_storage_policy(policy)

    def test_dose_thresholds_that_do_not_rise_are_refused(self):
        with self.assertRaises(ValueError):
            validate_storage_policy(_policy(major_dose=400.0))

    def test_a_zero_minor_dose_is_refused(self):
        with self.assertRaises(ValueError):
            validate_storage_policy(_policy(minor_dose=0.0))

    def test_a_fractional_review_horizon_is_refused(self):
        with self.assertRaises(ValueError):
            validate_storage_policy(_policy(review_horizon_days=30.5))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_storage_policy(["minor_dose"])


class BandingTests(unittest.TestCase):
    def test_a_few_hundred_volts_lands_in_the_most_sensitive_band(self):
        self.assertEqual(esd_band(120.0), "0")

    def test_a_band_boundary_belongs_to_the_band_above_it(self):
        self.assertEqual(esd_band(250.0), "1A")

    def test_a_robust_part_lands_in_the_least_sensitive_band(self):
        self.assertEqual(esd_band(20000.0), "3B")

    def test_every_registered_band_covers_its_own_lower_edge(self):
        for band, lower, _upper in ESD_BANDS:
            self.assertEqual(esd_band(lower), band)

    def test_a_negative_withstand_is_refused(self):
        with self.assertRaises(ValueError):
            esd_band(-5.0)

    def test_a_non_numeric_withstand_is_refused(self):
        with self.assertRaises(ValueError):
            esd_band("very sensitive")

    def test_the_baseline_set_is_owed_by_every_band(self):
        for band, _lower, _upper in ESD_BANDS:
            self.assertTrue(set(BASELINE_MEASURES).issubset(minimum_measures(band)))

    def test_a_sensitive_band_owes_more_than_the_baseline(self):
        self.assertEqual(
            len(minimum_measures("0")),
            len(BASELINE_MEASURES) + len(SENSITIVE_EXTRA_MEASURES),
        )

    def test_an_unregistered_band_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_measures("4C")

    def test_the_no_substitution_bands_are_sensitive_bands(self):
        self.assertTrue(set(NO_SUBSTITUTION_BANDS).issubset(set(SENSITIVE_BANDS)))


class MeasureGapTests(unittest.TestCase):
    def test_a_store_operating_the_whole_set_has_no_gap(self):
        gaps = measure_gaps("2", list(BASELINE_MEASURES))
        self.assertEqual(gaps["missing"], [])
        self.assertEqual(gaps["substituted"], [])

    def test_a_measure_the_store_does_not_operate_is_missing(self):
        gaps = measure_gaps("2", list(BASELINE_MEASURES)[:-1])
        self.assertEqual(gaps["missing"], [BASELINE_MEASURES[-1]])

    def test_a_recorded_equivalent_is_credited_at_this_class(self):
        gaps = measure_gaps(
            "2",
            list(BASELINE_MEASURES)[:-1],
            {
                BASELINE_MEASURES[-1]: {
                    "equivalent": "closed-dissipative-transport-tote",
                    "recorded": True,
                }
            },
        )
        self.assertEqual(gaps["missing"], [])
        self.assertEqual(gaps["substituted"], [BASELINE_MEASURES[-1]])

    def test_an_unrecorded_equivalent_is_refused(self):
        gaps = measure_gaps(
            "2",
            list(BASELINE_MEASURES)[:-1],
            {
                BASELINE_MEASURES[-1]: {
                    "equivalent": "closed-dissipative-transport-tote",
                    "recorded": False,
                }
            },
        )
        self.assertEqual(gaps["missing"], [BASELINE_MEASURES[-1]])
        self.assertEqual(gaps["refused_substitutions"], [BASELINE_MEASURES[-1]])

    def test_the_most_sensitive_band_is_not_relaxed_even_on_the_record(self):
        owed = minimum_measures("0")
        gaps = measure_gaps(
            "0",
            owed[:-1],
            {owed[-1]: {"equivalent": "a bench fan", "recorded": True}},
        )
        self.assertEqual(gaps["missing"], [owed[-1]])
        self.assertEqual(gaps["refused_substitutions"], [owed[-1]])

    def test_a_substitution_for_a_measure_the_band_does_not_owe_is_refused(self):
        with self.assertRaises(ValueError):
            measure_gaps(
                "2",
                list(BASELINE_MEASURES),
                {"protected-area-ionizer": {"equivalent": "x", "recorded": True}},
            )

    def test_an_equivalent_that_is_the_measure_itself_is_refused(self):
        with self.assertRaises(ValueError):
            measure_gaps(
                "2",
                list(BASELINE_MEASURES)[:-1],
                {BASELINE_MEASURES[-1]: {"equivalent": BASELINE_MEASURES[-1], "recorded": True}},
            )

    def test_a_substitution_missing_its_record_flag_is_refused(self):
        with self.assertRaises(ValueError):
            measure_gaps(
                "2",
                list(BASELINE_MEASURES)[:-1],
                {BASELINE_MEASURES[-1]: {"equivalent": "a tote"}},
            )

    def test_a_non_sequence_operated_set_is_refused(self):
        with self.assertRaises(ValueError):
            measure_gaps("2", "everything")


class ExcursionDoseTests(unittest.TestCase):
    def test_a_store_inside_its_band_runs_no_dose(self):
        reading = excursion_dose([{"value": 22.0, "hours": 500.0}], 10.0, 30.0)
        self.assertAlmostEqual(reading["dose"], 0.0, places=9)

    def test_a_reading_exactly_on_the_upper_limit_is_inside_the_band(self):
        reading = excursion_dose([{"value": 30.0, "hours": 500.0}], 10.0, 30.0)
        self.assertAlmostEqual(reading["dose"], 0.0, places=9)

    def test_a_reading_exactly_on_the_lower_limit_is_inside_the_band(self):
        reading = excursion_dose([{"value": 10.0, "hours": 500.0}], 10.0, 30.0)
        self.assertAlmostEqual(reading["dose"], 0.0, places=9)

    def test_an_overshoot_is_its_magnitude_multiplied_by_its_duration(self):
        reading = excursion_dose([{"value": 35.0, "hours": 4.0}], 10.0, 30.0)
        self.assertAlmostEqual(reading["over_dose"], 20.0, places=9)
        self.assertAlmostEqual(reading["peak_over"], 5.0, places=9)

    def test_an_undershoot_is_carried_separately_from_an_overshoot(self):
        reading = excursion_dose(
            [{"value": 5.0, "hours": 2.0}, {"value": 35.0, "hours": 4.0}], 10.0, 30.0
        )
        self.assertAlmostEqual(reading["under_dose"], 10.0, places=9)
        self.assertAlmostEqual(reading["over_dose"], 20.0, places=9)
        self.assertAlmostEqual(reading["dose"], 30.0, places=9)

    def test_a_small_excursion_held_long_outweighs_a_large_one_held_briefly(self):
        creeping = excursion_dose([{"value": 32.0, "hours": 100.0}], 10.0, 30.0)
        spike = excursion_dose([{"value": 45.0, "hours": 1.0}], 10.0, 30.0)
        self.assertAlmostEqual(creeping["dose"], 200.0, places=9)
        self.assertAlmostEqual(spike["dose"], 15.0, places=9)
        self.assertGreater(creeping["dose"], spike["dose"])
        self.assertGreater(spike["peak_over"], creeping["peak_over"])

    def test_the_logged_hours_are_carried_through(self):
        reading = excursion_dose(
            [{"value": 22.0, "hours": 10.0}, {"value": 35.0, "hours": 5.0}], 10.0, 30.0
        )
        self.assertAlmostEqual(reading["hours"], 15.0, places=9)

    def test_an_empty_log_is_refused(self):
        with self.assertRaises(ValueError):
            excursion_dose([], 10.0, 30.0)

    def test_a_segment_holding_for_no_time_is_refused(self):
        with self.assertRaises(ValueError):
            excursion_dose([{"value": 35.0, "hours": 0.0}], 10.0, 30.0)

    def test_a_segment_missing_its_duration_is_refused(self):
        with self.assertRaises(ValueError):
            excursion_dose([{"value": 35.0}], 10.0, 30.0)

    def test_an_empty_declared_band_is_refused(self):
        with self.assertRaises(ValueError):
            excursion_dose([{"value": 22.0, "hours": 1.0}], 30.0, 30.0)


class SeverityTests(unittest.TestCase):
    def test_no_dose_grades_as_within_band(self):
        self.assertEqual(dose_severity(0.0), DOSE_NONE)

    def test_a_dose_landing_exactly_on_the_minor_threshold_is_minor(self):
        self.assertEqual(
            dose_severity(DEFAULT_STORAGE_POLICY["minor_dose"]), DOSE_MINOR
        )

    def test_a_dose_landing_exactly_on_the_major_threshold_is_major(self):
        self.assertEqual(
            dose_severity(DEFAULT_STORAGE_POLICY["major_dose"]), DOSE_MAJOR
        )

    def test_a_dose_landing_exactly_on_the_critical_threshold_is_critical(self):
        self.assertEqual(
            dose_severity(DEFAULT_STORAGE_POLICY["critical_dose"]), DOSE_CRITICAL
        )

    def test_a_dose_under_the_minor_threshold_is_within_band(self):
        self.assertEqual(dose_severity(1.0), DOSE_NONE)

    def test_a_negative_dose_is_refused(self):
        with self.assertRaises(ValueError):
            dose_severity(-1.0)


class PackagingAndShelfLifeTests(unittest.TestCase):
    def test_an_indicator_reading_on_its_limit_is_dry(self):
        self.assertEqual(humidity_indicator_state(10.0, 10.0), INDICATOR_DRY)

    def test_an_indicator_inside_the_margin_is_marginal(self):
        self.assertEqual(humidity_indicator_state(14.0, 10.0), INDICATOR_MARGINAL)

    def test_an_indicator_past_the_margin_is_saturated(self):
        self.assertEqual(humidity_indicator_state(20.0, 10.0), INDICATOR_SATURATED)

    def test_a_zero_indicator_limit_is_refused(self):
        with self.assertRaises(ValueError):
            humidity_indicator_state(10.0, 0.0)

    def test_the_shelf_life_margin_is_counted_in_whole_days(self):
        self.assertEqual(
            shelf_life_margin_days("2025-01-01", 365, "2025-07-01"), 184
        )

    def test_an_expired_shelf_life_returns_a_negative_margin(self):
        self.assertEqual(shelf_life_margin_days("2025-01-01", 365, "2026-07-01"), -181)

    def test_a_date_object_is_accepted_as_readily_as_an_iso_string(self):
        self.assertEqual(
            shelf_life_margin_days(
                datetime.date(2025, 1, 1), 365, datetime.date(2025, 7, 1)
            ),
            184,
        )

    def test_a_review_before_the_lot_entered_store_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_margin_days("2025-01-01", 365, "2024-12-01")

    def test_a_fractional_shelf_life_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_margin_days("2025-01-01", 365.5, "2025-07-01")

    def test_a_malformed_date_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_margin_days("the first of January", 365, "2025-07-01")


class VerdictTests(unittest.TestCase):
    def test_no_findings_release_the_lot(self):
        self.assertEqual(storage_verdict([]), RELEASED)

    def test_a_minor_finding_still_releases_the_lot(self):
        self.assertEqual(storage_verdict([("minor", "log it")]), RELEASED)

    def test_a_major_finding_releases_with_actions(self):
        self.assertEqual(
            storage_verdict([("minor", "log it"), ("major", "chase it")]),
            RELEASED_WITH_ACTIONS,
        )

    def test_a_critical_finding_quarantines_the_lot(self):
        self.assertEqual(
            storage_verdict([("major", "chase it"), ("critical", "hold it")]),
            QUARANTINED,
        )

    def test_an_unregistered_severity_is_refused(self):
        with self.assertRaises(ValueError):
            storage_verdict([("catastrophic", "hold it")])

    def test_a_finding_that_is_not_a_pair_is_refused(self):
        with self.assertRaises(ValueError):
            storage_verdict(["hold it"])

    def test_the_severity_register_is_ordered_worst_first(self):
        self.assertEqual(SEVERITY_ORDER[0], "critical")


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_store_releases_the_lot(self):
        result = assess_class_three_handling_and_storage(_case())
        self.assertEqual(result["verdict"], RELEASED)
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_measure_on_a_robust_part_releases_with_actions(self):
        result = assess_class_three_handling_and_storage(
            _case(measures_operated=list(BASELINE_MEASURES)[:-1])
        )
        self.assertEqual(result["verdict"], RELEASED_WITH_ACTIONS)
        self.assertEqual(result["missing_measures"], [BASELINE_MEASURES[-1]])

    def test_the_same_missing_measure_on_a_sensitive_part_quarantines_it(self):
        owed = minimum_measures("0")
        result = assess_class_three_handling_and_storage(
            _sensitive_case(measures_operated=owed[:-1])
        )
        self.assertEqual(result["band"], "0")
        self.assertEqual(result["verdict"], QUARANTINED)

    def test_a_recorded_equivalent_keeps_a_robust_lot_releasable(self):
        result = assess_class_three_handling_and_storage(
            _case(
                measures_operated=list(BASELINE_MEASURES)[:-1],
                substitutions={
                    BASELINE_MEASURES[-1]: {
                        "equivalent": "closed-dissipative-transport-tote",
                        "recorded": True,
                    }
                },
            )
        )
        self.assertEqual(result["verdict"], RELEASED)
        self.assertEqual(result["substituted_measures"], [BASELINE_MEASURES[-1]])

    def test_a_creeping_temperature_excursion_quarantines_the_lot(self):
        result = assess_class_three_handling_and_storage(
            _case(temperature_segments=[{"value": 32.0, "hours": 200.0}])
        )
        self.assertEqual(result["temperature_severity"], DOSE_CRITICAL)
        self.assertEqual(result["verdict"], QUARANTINED)

    def test_a_brief_spike_is_logged_rather_than_quarantined(self):
        result = assess_class_three_handling_and_storage(
            _case(temperature_segments=[{"value": 45.0, "hours": 1.0}])
        )
        self.assertEqual(result["temperature_severity"], DOSE_MINOR)
        self.assertEqual(result["verdict"], RELEASED)

    def test_a_humidity_dose_is_graded_on_its_own_readings(self):
        result = assess_class_three_handling_and_storage(
            _case(humidity_segments=[{"value": 70.0, "hours": 8.0}])
        )
        self.assertEqual(result["humidity_severity"], DOSE_MAJOR)
        self.assertEqual(result["verdict"], RELEASED_WITH_ACTIONS)

    def test_a_breached_bag_with_a_wet_indicator_quarantines_the_lot(self):
        result = assess_class_three_handling_and_storage(
            _case(
                moisture_barrier_intact=False,
                indicator_reading_percent=40.0,
            )
        )
        self.assertEqual(result["indicator_state"], INDICATOR_SATURATED)
        self.assertEqual(result["verdict"], QUARANTINED)

    def test_a_breached_bag_with_a_dry_indicator_releases_with_actions(self):
        result = assess_class_three_handling_and_storage(
            _case(moisture_barrier_intact=False)
        )
        self.assertEqual(result["indicator_state"], INDICATOR_DRY)
        self.assertEqual(result["verdict"], RELEASED_WITH_ACTIONS)

    def test_a_sealed_bag_without_desiccant_is_only_a_minor_finding(self):
        result = assess_class_three_handling_and_storage(
            _case(desiccant_present=False)
        )
        self.assertEqual(result["verdict"], RELEASED)
        self.assertEqual(len(result["findings"]), 1)

    def test_an_expired_shelf_life_quarantines_the_lot(self):
        result = assess_class_three_handling_and_storage(
            _case(review_date="2026-07-01")
        )
        self.assertEqual(result["shelf_life_margin_days"], -181)
        self.assertEqual(result["verdict"], QUARANTINED)

    def test_a_shelf_life_inside_the_review_horizon_releases_with_actions(self):
        result = assess_class_three_handling_and_storage(
            _case(review_date="2025-12-20")
        )
        self.assertEqual(result["verdict"], RELEASED_WITH_ACTIONS)

    def test_a_case_missing_a_required_key_is_refused(self):
        case = _case()
        del case["review_date"]
        with self.assertRaises(ValueError):
            assess_class_three_handling_and_storage(case)

    def test_a_limits_pair_of_the_wrong_shape_is_refused(self):
        with self.assertRaises(ValueError):
            assess_class_three_handling_and_storage(_case(temperature_limits=(30.0,)))

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_class_three_handling_and_storage(["withstand_volts"])

    def test_every_finding_is_a_severity_and_a_sentence(self):
        result = assess_class_three_handling_and_storage(
            _case(
                measures_operated=list(BASELINE_MEASURES)[:-1],
                desiccant_present=False,
                temperature_segments=[{"value": 32.0, "hours": 200.0}],
            )
        )
        self.assertTrue(result["findings"])
        for severity, text in result["findings"]:
            self.assertIn(severity, SEVERITY_ORDER)
            self.assertTrue(text.strip())


if __name__ == "__main__":
    unittest.main()

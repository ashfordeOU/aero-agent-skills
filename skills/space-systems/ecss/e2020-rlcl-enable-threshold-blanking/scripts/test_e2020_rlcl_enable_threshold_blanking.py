"""Contract tests for the clause 5.4.4.3.1 retriggerable enable blanking logic."""

import unittest

from e2020_rlcl_enable_threshold_blanking_logic import (
    BLANKING_ADEQUATE,
    BLANKING_MARGIN_THIN,
    BLANKING_NOT_EVALUATED,
    BLANKING_REQUEST_SUPPRESSED,
    BLANKING_TRANSIENT_ADMITTED,
    DEFAULT_ENABLE_BLANKING_POLICY,
    EVENT_ADMITTED,
    EVENT_BLANKED,
    EVENT_HONOURED,
    EVENT_MARGIN_THIN,
    EVENT_SUPPRESSED,
    EVENT_UNRESOLVED,
    EXCURSION_NUISANCE,
    EXCURSION_REQUEST,
    assess_enable_blanking,
    categorize_excursion_kind,
    excursions_above,
    feasible_confirmation_window,
    grade_event,
    longest_dwell_above,
    measure_event,
    recommended_confirmation_time_s,
    validate_enable_blanking_policy,
    validate_enable_thresholds,
    validate_waveform,
    worst_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_ENABLE_BLANKING_POLICY)
    policy.update(overrides)
    return policy


def _thresholds(**overrides):
    thresholds = {"enable_threshold_v": 24.0, "release_threshold_v": 22.0}
    thresholds.update(overrides)
    return thresholds


def _bands(**overrides):
    return validate_enable_thresholds(_thresholds(**overrides))


def _nuisance(identifier="spike-1", dwell_s=0.010, **overrides):
    event = {"id": identifier, "kind": EXCURSION_NUISANCE, "dwell_s": dwell_s}
    event.update(overrides)
    return event


def _request(identifier="bus-return", dwell_s=0.200, **overrides):
    event = {"id": identifier, "kind": EXCURSION_REQUEST, "dwell_s": dwell_s}
    event.update(overrides)
    return event


def _design(events=None, **overrides):
    design = {
        "thresholds": _thresholds(),
        "confirmation_time_s": 0.050,
        "events": events if events is not None else [_nuisance(), _request()],
    }
    design.update(overrides)
    return design


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_enable_blanking_policy(DEFAULT_ENABLE_BLANKING_POLICY),
            DEFAULT_ENABLE_BLANKING_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_blanking_policy("blank for 50 ms")

    def test_a_nuisance_margin_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_blanking_policy(_policy(nuisance_margin_fraction=1.0))

    def test_a_negative_request_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_blanking_policy(_policy(request_margin_fraction=-0.05))

    def test_a_negative_hysteresis_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_blanking_policy(_policy(min_enable_hysteresis_v=-0.1))

    def test_a_non_boolean_recovery_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_blanking_policy(
                _policy(require_recovery_below_release="yes")
            )


class ThresholdTests(unittest.TestCase):
    def test_a_usable_band_reports_its_hysteresis(self):
        bands = validate_enable_thresholds(_thresholds())
        self.assertAlmostEqual(bands["hysteresis_v"], 2.0, places=9)

    def test_a_release_point_above_the_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_thresholds(_thresholds(release_threshold_v=25.0))

    def test_a_release_point_equal_to_the_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_thresholds(_thresholds(release_threshold_v=24.0))

    def test_hysteresis_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_thresholds(_thresholds(release_threshold_v=23.8))

    def test_hysteresis_exactly_on_the_floor_accepted(self):
        bands = validate_enable_thresholds(_thresholds(release_threshold_v=23.5))
        self.assertAlmostEqual(bands["hysteresis_v"], 0.5, places=9)

    def test_a_negative_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_enable_thresholds(_thresholds(enable_threshold_v=-1.0))


class WaveformTests(unittest.TestCase):
    def test_a_single_sample_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 24.0)])

    def test_a_non_increasing_time_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 20.0), (0.0, 25.0)])

    def test_a_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 20.0), (1.0, 25.0, 3.0)])

    def test_a_non_numeric_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 20.0), (1.0, "25")])

    def test_the_crossing_instant_is_interpolated_not_snapped(self):
        found = excursions_above([(0.0, 20.0), (1.0, 30.0), (2.0, 20.0)], 25.0)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["start_s"], 0.5, places=9)
        self.assertAlmostEqual(found[0]["end_s"], 1.5, places=9)
        self.assertAlmostEqual(found[0]["dwell_s"], 1.0, places=9)

    def test_the_excursion_peak_is_reported(self):
        found = excursions_above(
            [(0.0, 20.0), (1.0, 30.0), (2.0, 34.0), (3.0, 20.0)], 25.0
        )
        self.assertAlmostEqual(found[0]["peak_v"], 34.0, places=9)

    def test_two_separate_excursions_are_kept_apart(self):
        found = excursions_above(
            [(0.0, 20.0), (1.0, 30.0), (2.0, 20.0), (3.0, 30.0), (4.0, 20.0)],
            25.0,
        )
        self.assertEqual(len(found), 2)

    def test_a_trace_ending_above_the_level_is_left_open(self):
        found = excursions_above([(0.0, 20.0), (1.0, 30.0)], 25.0)
        self.assertFalse(found[0]["closed"])

    def test_a_trace_that_never_crosses_has_no_excursion(self):
        self.assertEqual(excursions_above([(0.0, 20.0), (1.0, 21.0)], 25.0), ())

    def test_the_longest_dwell_is_the_one_returned(self):
        dwell = longest_dwell_above(
            [
                (0.0, 20.0),
                (1.0, 30.0),
                (2.0, 20.0),
                (3.0, 30.0),
                (6.0, 30.0),
                (7.0, 20.0),
            ],
            25.0,
        )
        self.assertAlmostEqual(dwell, 4.0, places=9)

    def test_a_trace_with_no_excursion_has_zero_dwell(self):
        self.assertAlmostEqual(
            longest_dwell_above([(0.0, 10.0), (1.0, 11.0)], 25.0), 0.0, places=9
        )


class EventMeasurementTests(unittest.TestCase):
    def test_an_unrecognised_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_excursion_kind("enable-excursion-maybe")

    def test_an_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_excursion_kind("   ")

    def test_a_known_kind_is_trimmed_and_returned(self):
        self.assertEqual(
            categorize_excursion_kind("  enable-request-genuine "), EXCURSION_REQUEST
        )

    def test_an_event_with_neither_dwell_nor_samples_rejected(self):
        with self.assertRaises(ValueError):
            measure_event({"id": "spike-1", "kind": EXCURSION_NUISANCE}, _bands())

    def test_an_event_with_no_id_rejected(self):
        with self.assertRaises(ValueError):
            measure_event(_nuisance(identifier="  "), _bands())

    def test_a_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            measure_event(_nuisance(dwell_s=-0.001), _bands())

    def test_a_sampled_event_takes_its_dwell_from_the_trace(self):
        record = measure_event(
            _nuisance(
                samples=[(0.0, 22.0), (0.1, 26.0), (0.2, 22.0)],
                dwell_s=None,
            ),
            _bands(),
        )
        self.assertAlmostEqual(record["dwell_s"], 0.100, places=9)

    def test_a_sampled_event_that_never_recovers_is_unresolved(self):
        record = measure_event(
            _nuisance(samples=[(0.0, 22.0), (0.1, 26.0)], dwell_s=None), _bands()
        )
        self.assertFalse(record["recovered"])
        self.assertTrue(record["gaps"])

    def test_a_settling_tail_above_the_release_point_is_unresolved(self):
        record = measure_event(
            _nuisance(
                samples=[(0.0, 22.0), (0.1, 26.0), (0.2, 23.0)], dwell_s=None
            ),
            _bands(),
        )
        self.assertFalse(record["recovered"])

    def test_the_recovery_rule_can_be_switched_off_by_policy(self):
        record = measure_event(
            _nuisance(
                samples=[(0.0, 22.0), (0.1, 26.0), (0.2, 23.0)], dwell_s=None
            ),
            _bands(),
            _policy(require_recovery_below_release=False),
        )
        self.assertTrue(record["recovered"])


class EventGradingTests(unittest.TestCase):
    def test_a_short_nuisance_excursion_is_blanked(self):
        record = measure_event(_nuisance(dwell_s=0.010), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_BLANKED)

    def test_a_nuisance_excursion_as_long_as_the_window_is_admitted(self):
        record = measure_event(_nuisance(dwell_s=0.050), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_ADMITTED)

    def test_a_nuisance_excursion_inside_its_margin_is_thin(self):
        record = measure_event(_nuisance(dwell_s=0.045), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_MARGIN_THIN)

    def test_a_nuisance_excursion_exactly_on_its_margin_is_blanked(self):
        record = measure_event(_nuisance(dwell_s=0.040), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_BLANKED)

    def test_a_long_request_is_honoured(self):
        record = measure_event(_request(dwell_s=0.200), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_HONOURED)

    def test_a_request_shorter_than_the_window_is_suppressed(self):
        record = measure_event(_request(dwell_s=0.040), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_SUPPRESSED)

    def test_a_request_inside_its_margin_is_thin(self):
        record = measure_event(_request(dwell_s=0.055), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_MARGIN_THIN)

    def test_a_request_exactly_on_its_margin_is_honoured(self):
        record = measure_event(_request(dwell_s=0.0625), _bands())
        self.assertEqual(grade_event(record, 0.050), EVENT_HONOURED)

    def test_an_unresolved_event_grades_as_unresolved(self):
        record = measure_event(
            _nuisance(samples=[(0.0, 22.0), (0.1, 26.0)], dwell_s=None), _bands()
        )
        self.assertEqual(grade_event(record, 0.050), EVENT_UNRESOLVED)

    def test_a_zero_confirmation_time_rejected(self):
        record = measure_event(_nuisance(), _bands())
        with self.assertRaises(ValueError):
            grade_event(record, 0.0)


class WindowTests(unittest.TestCase):
    def test_the_window_is_bounded_by_the_worst_of_each_kind(self):
        records = [
            measure_event(_nuisance("spike-1", 0.010), _bands()),
            measure_event(_nuisance("spike-2", 0.020), _bands()),
            measure_event(_request("return-1", 0.400), _bands()),
            measure_event(_request("return-2", 0.200), _bands()),
        ]
        window = feasible_confirmation_window(records)
        self.assertAlmostEqual(window["lower_s"], 0.025, places=9)
        self.assertAlmostEqual(window["upper_s"], 0.160, places=9)
        self.assertTrue(window["open"])

    def test_a_window_whose_ends_cross_is_closed(self):
        records = [
            measure_event(_nuisance("spike-1", 0.200), _bands()),
            measure_event(_request("return-1", 0.100), _bands()),
        ]
        self.assertFalse(feasible_confirmation_window(records)["open"])

    def test_a_window_with_no_request_leaves_the_ceiling_unset(self):
        records = [measure_event(_nuisance("spike-1", 0.010), _bands())]
        window = feasible_confirmation_window(records)
        self.assertIsNone(window["upper_s"])

    def test_an_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            feasible_confirmation_window([])

    def test_the_recommendation_sits_between_the_bounds(self):
        records = [
            measure_event(_nuisance("spike-1", 0.020), _bands()),
            measure_event(_request("return-1", 0.200), _bands()),
        ]
        window = feasible_confirmation_window(records)
        recommended = recommended_confirmation_time_s(records)
        self.assertGreater(recommended, window["lower_s"])
        self.assertLess(recommended, window["upper_s"])

    def test_a_closed_window_refuses_a_recommendation(self):
        records = [
            measure_event(_nuisance("spike-1", 0.200), _bands()),
            measure_event(_request("return-1", 0.100), _bands()),
        ]
        with self.assertRaises(ValueError):
            recommended_confirmation_time_s(records)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_design_is_adequate(self):
        result = assess_enable_blanking(_design())
        self.assertEqual(result["verdict"], BLANKING_ADEQUATE)
        self.assertEqual(result["findings"], [])

    def test_an_excursion_that_gets_through_is_reported(self):
        result = assess_enable_blanking(
            _design([_nuisance(dwell_s=0.080), _request()])
        )
        self.assertEqual(result["verdict"], BLANKING_TRANSIENT_ADMITTED)
        self.assertIn("spike-1", result["standings"][EVENT_ADMITTED])

    def test_a_swallowed_request_is_reported(self):
        result = assess_enable_blanking(
            _design([_nuisance(dwell_s=0.005), _request(dwell_s=0.030)])
        )
        self.assertEqual(result["verdict"], BLANKING_REQUEST_SUPPRESSED)

    def test_a_thin_margin_is_reported_without_a_breach(self):
        result = assess_enable_blanking(
            _design([_nuisance(dwell_s=0.045), _request()])
        )
        self.assertEqual(result["verdict"], BLANKING_MARGIN_THIN)

    def test_an_unresolved_event_blocks_the_judgement(self):
        result = assess_enable_blanking(
            _design(
                [
                    _nuisance(samples=[(0.0, 22.0), (0.1, 26.0)], dwell_s=None),
                    _request(),
                ]
            )
        )
        self.assertEqual(result["verdict"], BLANKING_NOT_EVALUATED)

    def test_a_duplicate_event_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_enable_blanking(
                _design([_nuisance("spike-1"), _nuisance("spike-1")])
            )

    def test_a_design_with_no_events_rejected(self):
        with self.assertRaises(ValueError):
            assess_enable_blanking(_design([]))

    def test_a_missing_confirmation_time_rejected(self):
        design = _design()
        del design["confirmation_time_s"]
        with self.assertRaises(ValueError):
            assess_enable_blanking(design)

    def test_findings_name_the_event_that_produced_them(self):
        result = assess_enable_blanking(
            _design([_nuisance("spike-9", 0.080), _request()])
        )
        self.assertTrue(result["findings"][0].startswith("spike-9:"))

    def test_a_closed_window_is_called_out_in_the_findings(self):
        result = assess_enable_blanking(
            _design(
                [_nuisance(dwell_s=0.048), _request(dwell_s=0.052)],
                confirmation_time_s=0.050,
            )
        )
        self.assertFalse(result["window"]["open"])
        self.assertTrue(
            any("serves both duties" in finding for finding in result["findings"])
        )

    def test_the_worst_standing_is_the_one_reported(self):
        result = assess_enable_blanking(
            _design(
                [
                    _nuisance(dwell_s=0.010),
                    _nuisance("spike-2", 0.080),
                    _request(),
                ]
            )
        )
        self.assertEqual(worst_standing(result["events"]), EVENT_ADMITTED)

    def test_worst_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_standing([])


if __name__ == "__main__":
    unittest.main()

"""Contract test for the event-action initiation leaf (stdlib unittest)."""

import unittest

from e7041_action_initiation_logic import (
    APID_MAX,
    DISPOSITION_DEFINITION_DISABLED,
    DISPOSITION_FUNCTION_DISABLED,
    DISPOSITION_NO_DEFINITION,
    DISPOSITION_RELEASED,
    FINDING_OCCURRENCE_OUT_OF_ORDER,
    FINDING_RELEASE_RATE_EXCEEDED,
    FINDING_REPEAT_RELEASE,
    FINDING_UNCOVERED_EVENT_SEEN,
    assess_action_initiation,
    decide_release,
    initiate_actions,
    normalise_bindings,
    normalise_occurrence,
    peak_release_rate,
    releases_per_event,
)

SAFE = (17, 4001)
WARM = (17, 4002)


def action(subtype=1):
    return {"service_type": 8, "message_subtype": subtype, "target_apid": 25}


def bindings(safe_enabled=True, warm_enabled=True):
    return {
        SAFE: {"enabled": safe_enabled, "action": action(1)},
        WARM: {"enabled": warm_enabled, "action": action(2)},
    }


def occurrence(key=SAFE, time_s=0.0):
    return {"apid": key[0], "event_definition_id": key[1], "time_s": time_s}


def findings_of(report):
    return [f["finding"] for f in report["findings"]]


class TestInputValidation(unittest.TestCase):
    def test_an_occurrence_without_an_apid_raises(self):
        with self.assertRaises(ValueError):
            normalise_occurrence({"event_definition_id": 4001}, 0)

    def test_an_apid_past_the_field_raises(self):
        with self.assertRaises(ValueError):
            normalise_occurrence(
                {"apid": APID_MAX + 1, "event_definition_id": 4001}, 0
            )

    def test_a_negative_occurrence_time_raises(self):
        with self.assertRaises(ValueError):
            normalise_occurrence(occurrence(time_s=-1.0), 0)

    def test_a_binding_without_an_action_raises(self):
        with self.assertRaises(ValueError):
            normalise_bindings({SAFE: {"enabled": True}})

    def test_a_binding_key_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            normalise_bindings({4001: {"enabled": True, "action": action()}})

    def test_a_run_with_no_occurrences_raises(self):
        with self.assertRaises(ValueError):
            initiate_actions(True, bindings(), [])


class TestDecisionOrder(unittest.TestCase):
    def test_an_armed_binding_releases(self):
        self.assertEqual(
            decide_release(True, normalise_bindings(bindings()), SAFE),
            DISPOSITION_RELEASED,
        )

    def test_the_function_switch_is_read_before_the_definition(self):
        self.assertEqual(
            decide_release(False, normalise_bindings(bindings()), SAFE),
            DISPOSITION_FUNCTION_DISABLED,
        )

    def test_the_function_switch_hides_even_a_missing_definition(self):
        self.assertEqual(
            decide_release(False, normalise_bindings(bindings()), (18, 1)),
            DISPOSITION_FUNCTION_DISABLED,
        )

    def test_an_event_with_no_definition_is_a_different_answer_from_a_disarmed_one(self):
        table = normalise_bindings(bindings(safe_enabled=False))
        self.assertEqual(decide_release(True, table, SAFE), DISPOSITION_DEFINITION_DISABLED)
        self.assertEqual(decide_release(True, table, (18, 1)), DISPOSITION_NO_DEFINITION)


class TestInitiation(unittest.TestCase):
    def test_the_released_request_is_the_one_the_definition_holds(self):
        outcome = initiate_actions(True, bindings(), [occurrence(WARM)])
        self.assertEqual(outcome["releases"][0]["action"]["message_subtype"], 2)

    def test_every_occurrence_gets_a_disposition_even_when_nothing_is_released(self):
        outcome = initiate_actions(False, bindings(), [occurrence(), occurrence(WARM)])
        self.assertEqual(len(outcome["decisions"]), 2)
        self.assertEqual(outcome["releases"], [])

    def test_two_detections_of_one_event_release_the_action_twice(self):
        outcome = initiate_actions(
            True, bindings(), [occurrence(time_s=1.0), occurrence(time_s=2.0)]
        )
        self.assertEqual(len(outcome["releases"]), 2)

    def test_a_backwards_occurrence_time_is_a_finding(self):
        outcome = initiate_actions(
            True, bindings(), [occurrence(time_s=5.0), occurrence(time_s=2.0)]
        )
        self.assertEqual(
            outcome["findings"][0]["finding"], FINDING_OCCURRENCE_OUT_OF_ORDER
        )

    def test_the_released_action_is_a_copy_the_caller_cannot_alter_in_the_table(self):
        table = bindings()
        outcome = initiate_actions(True, table, [occurrence()])
        outcome["releases"][0]["action"]["message_subtype"] = 99
        self.assertEqual(table[SAFE]["action"]["message_subtype"], 1)


class TestRate(unittest.TestCase):
    def test_no_releases_give_a_zero_rate(self):
        self.assertAlmostEqual(peak_release_rate([], 1.0), 0.0, places=9)

    def test_three_releases_inside_one_second_give_three_per_second(self):
        self.assertAlmostEqual(
            peak_release_rate([0.0, 0.4, 0.9], 1.0), 3.0, places=9
        )

    def test_spreading_the_same_releases_out_lowers_the_peak(self):
        self.assertAlmostEqual(
            peak_release_rate([0.0, 2.0, 4.0], 1.0), 1.0, places=9
        )

    def test_a_wider_window_reports_a_lower_rate_for_the_same_burst(self):
        self.assertAlmostEqual(
            peak_release_rate([0.0, 0.4, 0.9], 2.0), 1.5, places=9
        )

    def test_a_non_positive_window_raises(self):
        with self.assertRaises(ValueError):
            peak_release_rate([0.0], 0.0)

    def test_release_times_must_be_a_list(self):
        with self.assertRaises(ValueError):
            peak_release_rate(0.5, 1.0)


class TestTallies(unittest.TestCase):
    def test_releases_are_counted_per_event(self):
        outcome = initiate_actions(
            True,
            bindings(),
            [occurrence(time_s=0.0), occurrence(time_s=1.0), occurrence(WARM, 2.0)],
        )
        counts = releases_per_event(outcome["releases"])
        self.assertEqual(counts[SAFE], 2)
        self.assertEqual(counts[WARM], 1)

    def test_releases_per_event_needs_a_list(self):
        with self.assertRaises(ValueError):
            releases_per_event({SAFE: 2})


class TestAssessment(unittest.TestCase):
    def test_a_single_armed_detection_is_a_clean_run(self):
        report = assess_action_initiation(True, bindings(), [occurrence()])
        self.assertTrue(report["run_clean"])
        self.assertEqual(report["release_count"], 1)
        self.assertEqual(report["disposition_counts"][DISPOSITION_RELEASED], 1)

    def test_a_disarmed_definition_releases_nothing_and_says_which_switch(self):
        report = assess_action_initiation(
            True, bindings(safe_enabled=False), [occurrence()]
        )
        self.assertEqual(report["release_count"], 0)
        self.assertEqual(
            report["disposition_counts"][DISPOSITION_DEFINITION_DISABLED], 1
        )

    def test_the_function_switch_off_answers_for_every_occurrence(self):
        report = assess_action_initiation(
            False, bindings(), [occurrence(), occurrence(WARM, 1.0)]
        )
        self.assertEqual(report["disposition_counts"][DISPOSITION_FUNCTION_DISABLED], 2)
        self.assertEqual(report["disposition_counts"][DISPOSITION_DEFINITION_DISABLED], 0)

    def test_an_uncovered_event_is_named_once_however_often_it_is_seen(self):
        report = assess_action_initiation(
            True,
            bindings(),
            [occurrence((18, 7), 0.0), occurrence((18, 7), 1.0)],
        )
        self.assertEqual(
            findings_of(report).count(FINDING_UNCOVERED_EVENT_SEEN), 1
        )

    def test_a_repeated_release_is_reported_with_its_count(self):
        report = assess_action_initiation(
            True, bindings(), [occurrence(time_s=0.0), occurrence(time_s=1.0)]
        )
        repeat = [f for f in report["findings"] if f["finding"] == FINDING_REPEAT_RELEASE]
        self.assertEqual(repeat[0]["releases"], 2)

    def test_a_release_storm_breaches_a_stated_rate_limit(self):
        run = [occurrence(time_s=0.1 * i) for i in range(6)]
        report = assess_action_initiation(
            True, bindings(), run, rate_limit_per_s=3.0, window_s=1.0
        )
        self.assertIn(FINDING_RELEASE_RATE_EXCEEDED, findings_of(report))
        self.assertAlmostEqual(report["peak_release_rate_per_s"], 6.0, places=9)

    def test_a_rate_inside_the_limit_raises_no_rate_finding(self):
        run = [occurrence(time_s=float(i)) for i in range(4)]
        report = assess_action_initiation(
            True, bindings(), run, rate_limit_per_s=3.0, window_s=1.0
        )
        self.assertNotIn(FINDING_RELEASE_RATE_EXCEEDED, findings_of(report))

    def test_a_non_positive_rate_limit_raises(self):
        with self.assertRaises(ValueError):
            assess_action_initiation(
                True, bindings(), [occurrence()], rate_limit_per_s=0.0
            )


if __name__ == "__main__":
    unittest.main()

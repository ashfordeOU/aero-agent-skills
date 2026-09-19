"""Contract test for the cleanliness verification history leaf (unittest)."""

import datetime
import unittest

from q7005_record_in_cleanliness_database_logic import (
    DISPOSITION_CONFIRMATION,
    DISPOSITION_CONFLICT,
    DISPOSITION_DUPLICATE,
    DISPOSITION_RECORDED,
    DISPOSITION_REFUSED,
    TREND_DEGRADING,
    TREND_IMPROVING,
    TREND_STABLE,
    TREND_UNKNOWN,
    build_history,
    current_entry,
    effective_level,
    entries_for,
    entry_key,
    parse_date,
    post_entry,
    quantize,
    resolved_policy,
    same_value,
    validate_entry,
    verification_trend,
)

KEY = ("radiator-panel-3", "outboard-face", "solvent-rinse-infrared")


def record(date="2026-03-01", level=1.20, **kw):
    entry = {
        "item": KEY[0],
        "surface_zone": KEY[1],
        "method": KEY[2],
        "verification_date": date,
        "level_mg_m2": level,
        "report_reference": "IR-2026-014",
    }
    entry.update(kw)
    return entry


def posted(records):
    history = []
    for item in records:
        history = post_entry(history, item)["history"]
    return history


class TestQuantize(unittest.TestCase):
    def test_a_value_is_rounded_onto_the_step(self):
        self.assertAlmostEqual(quantize(1.2049, 0.01), 1.20, places=9)

    def test_a_half_step_rounds_upward_deterministically(self):
        self.assertAlmostEqual(quantize(1.205, 0.01), 1.21, places=9)

    def test_two_readings_inside_a_step_become_one_value(self):
        self.assertAlmostEqual(
            quantize(1.2001, 0.01), quantize(1.2049, 0.01), places=12
        )

    def test_a_zero_resolution_raises(self):
        with self.assertRaises(ValueError):
            quantize(1.2, 0.0)

    def test_a_negative_value_raises(self):
        with self.assertRaises(ValueError):
            quantize(-1.2, 0.01)


class TestKeyAndPolicy(unittest.TestCase):
    def test_the_key_is_item_zone_and_method(self):
        self.assertEqual(entry_key(record()), KEY)

    def test_a_missing_surface_zone_raises(self):
        with self.assertRaises(ValueError):
            entry_key(record(surface_zone=""))

    def test_a_description_alone_is_not_a_key(self):
        with self.assertRaises(ValueError):
            entry_key({"description": "the shiny panel"})

    def test_defaults_are_returned_when_nothing_is_passed(self):
        self.assertAlmostEqual(
            resolved_policy()["level_resolution_mg_m2"], 0.01, places=9
        )

    def test_an_unknown_policy_key_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"resolution": 0.01})

    def test_an_iso_date_parses(self):
        self.assertEqual(parse_date("2026-03-01"), datetime.date(2026, 3, 1))

    def test_a_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_date("01.03.2026")


class TestValidateEntry(unittest.TestCase):
    def test_a_valid_entry_is_stored_at_the_history_resolution(self):
        entry = validate_entry(record(level=1.2049))
        self.assertAlmostEqual(entry["level_mg_m2"], 1.20, places=9)

    def test_a_detection_without_a_level_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(record(level=None))

    def test_a_non_detect_is_stored_as_its_bound(self):
        entry = validate_entry(
            record(level=None, detected=False, quantitation_limit_mg_m2=0.30)
        )
        self.assertIsNone(entry["level_mg_m2"])
        self.assertAlmostEqual(entry["quantitation_limit_mg_m2"], 0.30, places=9)

    def test_a_non_detect_carrying_a_level_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(
                record(detected=False, quantitation_limit_mg_m2=0.30)
            )

    def test_a_non_detect_without_a_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(record(level=None, detected=False))

    def test_a_blank_report_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(record(report_reference="   "))

    def test_a_non_boolean_reportable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(record(analysis_reportable="yes"))


class TestEffectiveLevel(unittest.TestCase):
    def test_a_detection_contributes_its_level(self):
        self.assertAlmostEqual(
            effective_level(validate_entry(record(level=1.5))), 1.5, places=9
        )

    def test_a_non_detect_contributes_its_bound(self):
        entry = validate_entry(
            record(level=None, detected=False, quantitation_limit_mg_m2=0.3)
        )
        self.assertAlmostEqual(effective_level(entry), 0.3, places=9)

    def test_two_readings_inside_one_step_are_the_same_value(self):
        left = validate_entry(record(level=1.2001))
        right = validate_entry(record(level=1.2049))
        self.assertTrue(same_value(left, right))

    def test_a_bound_and_a_level_of_equal_size_are_not_the_same_value(self):
        detection = validate_entry(record(level=0.30))
        non_detect = validate_entry(
            record(level=None, detected=False, quantitation_limit_mg_m2=0.30)
        )
        self.assertFalse(same_value(detection, non_detect))


class TestPostEntry(unittest.TestCase):
    def test_a_first_entry_is_recorded_and_becomes_current(self):
        result = post_entry([], record())
        self.assertEqual(result["disposition"], DISPOSITION_RECORDED)
        self.assertTrue(result["becomes_current"])
        self.assertEqual(len(result["history"]), 1)

    def test_an_unreportable_analysis_is_refused(self):
        result = post_entry([], record(analysis_reportable=False))
        self.assertEqual(result["disposition"], DISPOSITION_REFUSED)
        self.assertEqual(result["history"], [])
        self.assertIn("source-analysis-was-never-reportable", result["findings"])

    def test_an_entry_with_no_report_behind_it_is_refused(self):
        result = post_entry([], record(report_reference=None))
        self.assertEqual(result["disposition"], DISPOSITION_REFUSED)
        self.assertIn(
            "entry-does-not-point-at-an-analysis-report", result["findings"]
        )

    def test_the_same_result_on_the_same_day_is_a_duplicate(self):
        history = posted([record()])
        result = post_entry(history, record())
        self.assertEqual(result["disposition"], DISPOSITION_DUPLICATE)
        self.assertEqual(len(result["history"]), 1)

    def test_a_different_result_on_the_same_day_is_a_conflict(self):
        history = posted([record()])
        result = post_entry(history, record(level=3.4))
        self.assertEqual(result["disposition"], DISPOSITION_CONFLICT)
        self.assertEqual(len(result["history"]), 1)
        self.assertIn(
            "same-date-entry-disagrees-with-the-one-held", result["findings"]
        )

    def test_the_same_result_on_a_later_day_is_a_confirmation(self):
        history = posted([record()])
        result = post_entry(history, record(date="2026-06-01"))
        self.assertEqual(result["disposition"], DISPOSITION_CONFIRMATION)
        self.assertTrue(result["becomes_current"])
        self.assertEqual(len(result["history"]), 2)

    def test_a_later_different_result_is_recorded_and_becomes_current(self):
        history = posted([record()])
        result = post_entry(history, record(date="2026-06-01", level=2.5))
        self.assertEqual(result["disposition"], DISPOSITION_RECORDED)
        self.assertTrue(result["becomes_current"])

    def test_a_back_dated_entry_is_kept_but_does_not_become_current(self):
        history = posted([record(date="2026-06-01", level=2.5)])
        result = post_entry(history, record(date="2026-03-01", level=1.2))
        self.assertFalse(result["becomes_current"])
        self.assertTrue(result["back_dated"])
        self.assertIn(
            "entry-is-back-dated-behind-the-current-record", result["findings"]
        )
        self.assertEqual(len(result["history"]), 2)

    def test_a_newer_entry_never_deletes_the_older_one(self):
        history = posted([record(), record(date="2026-06-01", level=2.5)])
        self.assertEqual(len(history), 2)

    def test_another_surface_zone_is_a_separate_record(self):
        history = posted([record(), record(surface_zone="inboard-face")])
        self.assertEqual(len(history), 2)
        self.assertEqual(len(entries_for(history, KEY)), 1)

    def test_another_method_is_a_separate_record(self):
        history = posted([record(), record(method="direct-reflection-infrared")])
        self.assertEqual(len(entries_for(history, KEY)), 1)

    def test_the_current_entry_is_the_newest_one(self):
        history = posted(
            [record(date="2026-06-01", level=2.5), record(date="2026-03-01")]
        )
        self.assertEqual(
            current_entry(history, KEY)["verification_date"],
            datetime.date(2026, 6, 1),
        )

    def test_a_history_with_no_matching_key_has_no_current_entry(self):
        self.assertIsNone(current_entry([], KEY))

    def test_a_non_list_history_raises(self):
        with self.assertRaises(ValueError):
            post_entry("history", record())


class TestVerificationTrend(unittest.TestCase):
    def test_a_single_entry_has_no_trend_yet(self):
        history = posted([record()])
        self.assertEqual(
            verification_trend(history, KEY)["trend"], TREND_UNKNOWN
        )

    def test_a_falling_level_is_improving(self):
        history = posted([record(level=2.0), record(date="2026-06-01", level=1.0)])
        self.assertEqual(
            verification_trend(history, KEY)["trend"], TREND_IMPROVING
        )

    def test_an_unchanged_level_is_stable(self):
        history = posted([record(level=2.0), record(date="2026-06-01", level=2.0)])
        self.assertEqual(verification_trend(history, KEY)["trend"], TREND_STABLE)

    def test_a_rising_level_is_degrading(self):
        history = posted([record(level=2.0), record(date="2026-06-01", level=2.2)])
        self.assertEqual(
            verification_trend(history, KEY)["trend"], TREND_DEGRADING
        )

    def test_a_rise_on_the_permitted_fraction_is_not_flagged(self):
        history = posted([record(level=2.0), record(date="2026-06-01", level=2.4)])
        report = verification_trend(history, KEY)
        self.assertEqual(report["trend"], TREND_DEGRADING)
        self.assertEqual(report["findings"], [])

    def test_a_rise_beyond_the_permitted_fraction_is_flagged(self):
        history = posted([record(level=2.0), record(date="2026-06-01", level=3.0)])
        self.assertIn(
            "rise-beyond-the-permitted-degradation-fraction",
            verification_trend(history, KEY)["findings"],
        )

    def test_a_trend_across_a_bound_is_marked_indicative(self):
        history = posted(
            [
                record(
                    level=None, detected=False, quantitation_limit_mg_m2=0.30
                ),
                record(date="2026-06-01", level=1.0),
            ]
        )
        self.assertIn(
            "trend-taken-across-a-bound-is-indicative-only",
            verification_trend(history, KEY)["findings"],
        )


class TestBuildHistory(unittest.TestCase):
    def test_a_sequence_is_posted_in_order_with_its_dispositions(self):
        summary = build_history(
            [record(), record(), record(date="2026-06-01", level=2.5)]
        )
        self.assertEqual(
            [d["disposition"] for d in summary["dispositions"]],
            [DISPOSITION_RECORDED, DISPOSITION_DUPLICATE, DISPOSITION_RECORDED],
        )
        self.assertEqual(summary["accepted"], 2)

    def test_conflicts_are_collected_for_resolution(self):
        summary = build_history([record(), record(level=3.4)])
        self.assertEqual(len(summary["conflicts"]), 1)
        self.assertEqual(len(summary["history"]), 1)

    def test_refusals_are_collected_apart(self):
        summary = build_history([record(analysis_reportable=False), record()])
        self.assertEqual(len(summary["refused"]), 1)
        self.assertEqual(len(summary["history"]), 1)

    def test_every_distinct_key_is_listed_once(self):
        summary = build_history(
            [record(), record(surface_zone="inboard-face"), record()]
        )
        self.assertEqual(len(summary["keys"]), 2)

    def test_an_empty_record_list_raises(self):
        with self.assertRaises(ValueError):
            build_history([])


if __name__ == "__main__":
    unittest.main()

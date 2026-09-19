"""Contract tests for the clause 5.7.2.6 exception reporting logic."""

import unittest

from e50_on_board_network_exception_reporting_logic import (
    DEFAULT_FIELDS,
    DEFICIENT,
    REPORTED,
    UNDETECTED,
    UNREPORTED,
    assess_exception,
    assess_exception_reporting,
    missing_fields,
    normalise_entry,
    validate_latency,
    validate_name,
    validate_names,
)

REQUIRED = ["link-down", "crc-error", "buffer-overrun"]
GOOD = {
    "name": "link-down",
    "detected": True,
    "reported": True,
    "fields": ["exception-id", "source", "time"],
    "report_latency_s": 0.5,
}
THIN = {
    "name": "crc-error",
    "detected": True,
    "reported": True,
    "fields": ["exception-id", "time"],
    "report_latency_s": 0.2,
}
SILENT = {"name": "buffer-overrun", "detected": True, "reported": False}
BLIND = {"name": "buffer-overrun", "detected": False, "reported": False}


class ValidationTests(unittest.TestCase):
    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name("")

    def test_a_bare_string_is_not_a_name_list(self):
        with self.assertRaises(ValueError):
            validate_names("link-down")

    def test_repeated_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_names(["link-down", "link-down"])

    def test_absent_latency_is_allowed(self):
        self.assertIsNone(validate_latency(None))

    def test_negative_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_latency(-0.1)

    def test_boolean_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_latency(True)

    def test_infinite_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_latency(float("inf"))

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(["link-down"])

    def test_non_boolean_detected_rejected(self):
        with self.assertRaises(ValueError):
            normalise_entry(dict(GOOD, detected="yes"))

    def test_a_report_without_detection_is_an_input_error(self):
        with self.assertRaises(ValueError):
            normalise_entry({"name": "x", "detected": False, "reported": True})

    def test_duplicate_catalogue_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_exception_reporting(REQUIRED, [GOOD, dict(GOOD)])

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_exception_reporting([], [GOOD])

    def test_non_list_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_exception_reporting(REQUIRED, GOOD)


class FieldTests(unittest.TestCase):
    def test_a_complete_report_misses_nothing(self):
        self.assertEqual(missing_fields(GOOD), ())

    def test_a_thin_report_misses_the_source(self):
        self.assertEqual(missing_fields(THIN), ("source",))

    def test_the_default_field_set_has_three_members(self):
        self.assertEqual(len(DEFAULT_FIELDS), 3)

    def test_an_extended_field_set_finds_more_gaps(self):
        self.assertEqual(
            missing_fields(GOOD, ["exception-id", "source", "time", "severity"]),
            ("severity",),
        )

    def test_an_extra_field_is_not_a_gap(self):
        rich = dict(GOOD, fields=["exception-id", "source", "time", "severity"])
        self.assertEqual(missing_fields(rich), ())


class LadderTests(unittest.TestCase):
    def test_an_undetected_exception_sits_on_the_first_rung(self):
        result = assess_exception(BLIND)
        self.assertEqual(result["verdict"], UNDETECTED)

    def test_a_detected_but_silent_exception_sits_on_the_second(self):
        result = assess_exception(SILENT)
        self.assertEqual(result["verdict"], UNREPORTED)

    def test_a_thin_report_sits_on_the_third(self):
        result = assess_exception(THIN)
        self.assertEqual(result["verdict"], DEFICIENT)

    def test_a_complete_timely_report_passes(self):
        result = assess_exception(GOOD, latency_bound_s=1.0)
        self.assertEqual(result["verdict"], REPORTED)
        self.assertEqual(result["reasons"], [])

    def test_an_undetected_exception_misses_every_field(self):
        result = assess_exception(BLIND)
        self.assertEqual(result["missing_fields"], list(DEFAULT_FIELDS))

    def test_a_late_report_is_deficient(self):
        result = assess_exception(GOOD, latency_bound_s=0.1)
        self.assertEqual(result["verdict"], DEFICIENT)
        self.assertTrue(result["late"])

    def test_a_report_exactly_on_its_bound_is_timely(self):
        result = assess_exception(GOOD, latency_bound_s=0.5)
        self.assertFalse(result["late"])
        self.assertEqual(result["verdict"], REPORTED)

    def test_an_unstated_latency_against_a_bound_is_late(self):
        entry = dict(GOOD, report_latency_s=None)
        result = assess_exception(entry, latency_bound_s=1.0)
        self.assertTrue(result["late"])
        self.assertTrue(any("declares no report latency" in r for r in result["reasons"]))

    def test_no_bound_means_latency_is_not_judged(self):
        entry = dict(GOOD, report_latency_s=None)
        self.assertEqual(assess_exception(entry)["verdict"], REPORTED)

    def test_a_thin_late_report_names_both_reasons(self):
        result = assess_exception(THIN, latency_bound_s=0.1)
        self.assertEqual(len(result["reasons"]), 2)


class CatalogueTests(unittest.TestCase):
    def test_a_sound_catalogue_is_compliant(self):
        good_all = [
            GOOD,
            dict(THIN, fields=["exception-id", "source", "time"]),
            dict(SILENT, reported=True, fields=["exception-id", "source", "time"],
                 report_latency_s=0.3),
        ]
        result = assess_exception_reporting(REQUIRED, good_all, latency_bound_s=1.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_an_exception_absent_from_the_catalogue_is_undetected(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN])
        self.assertIn("buffer-overrun", result["undetected"])

    def test_a_silent_exception_fails_the_first_item(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT])
        self.assertFalse(result["reporting_met"])
        self.assertIn("buffer-overrun", result["unreported"])

    def test_a_thin_report_fails_the_second_item(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT])
        self.assertFalse(result["content_met"])
        self.assertIn("crc-error", result["deficient"])

    def test_the_two_items_are_reported_separately(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT])
        self.assertTrue(any("clause item 1" in f for f in result["findings"]))
        self.assertTrue(any("clause item 2" in f for f in result["findings"]))

    def test_detection_ratio_counts_the_required_set(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN])
        self.assertAlmostEqual(result["detection_ratio"], 2.0 / 3.0, places=9)

    def test_full_detection_reads_as_one(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT])
        self.assertAlmostEqual(result["detection_ratio"], 1.0, places=9)

    def test_an_unasked_catalogue_entry_is_reported_as_an_extra(self):
        extra = {"name": "temperature-warning", "detected": True, "reported": True,
                 "fields": ["exception-id", "source", "time"]}
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT, extra])
        self.assertEqual(result["extras"], ["temperature-warning"])

    def test_an_extra_does_not_by_itself_fail_the_clause(self):
        good_all = [
            GOOD,
            dict(THIN, fields=["exception-id", "source", "time"]),
            dict(SILENT, reported=True, fields=["exception-id", "source", "time"]),
            {"name": "temperature-warning", "detected": True, "reported": True,
             "fields": ["exception-id", "source", "time"]},
        ]
        result = assess_exception_reporting(REQUIRED, good_all)
        self.assertTrue(result["compliant"])

    def test_a_late_exception_is_listed(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT], latency_bound_s=0.1)
        self.assertIn("link-down", result["late"])

    def test_every_required_exception_appears_once(self):
        result = assess_exception_reporting(REQUIRED, [GOOD, THIN, SILENT])
        self.assertEqual([r["exception"] for r in result["per_exception"]], REQUIRED)

    def test_an_extended_field_set_can_fail_a_sound_catalogue(self):
        good_all = [
            GOOD,
            dict(THIN, fields=["exception-id", "source", "time"]),
            dict(SILENT, reported=True, fields=["exception-id", "source", "time"]),
        ]
        result = assess_exception_reporting(
            REQUIRED, good_all, ["exception-id", "source", "time", "severity"]
        )
        self.assertFalse(result["content_met"])


if __name__ == "__main__":
    unittest.main()

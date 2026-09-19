"""Contract tests for the threaded-fastener applicability and scope decision."""

import unittest

from q7046_applicability_and_scope_logic import (
    ALL_CLAUSE_GROUPS,
    COARSE_PITCH_MM,
    SMALL_SIZE_THRESHOLD_MM,
    application_verdict,
    assess_scope,
    clause_groups,
    coarse_pitch_for,
    item_kinds,
    kind_verdict,
    parse_thread_designation,
)


class ThreadParsingTests(unittest.TestCase):
    def test_coarse_designation_takes_the_tabulated_pitch(self):
        parsed = parse_thread_designation("M6")
        self.assertAlmostEqual(parsed["nominal_diameter_mm"], 6.0, places=9)
        self.assertAlmostEqual(parsed["pitch_mm"], COARSE_PITCH_MM[6.0], places=9)
        self.assertFalse(parsed["pitch_stated"])

    def test_fine_designation_keeps_the_stated_pitch(self):
        parsed = parse_thread_designation("M8x1")
        self.assertAlmostEqual(parsed["pitch_mm"], 1.0, places=9)
        self.assertTrue(parsed["pitch_stated"])

    def test_star_separator_is_accepted(self):
        self.assertAlmostEqual(
            parse_thread_designation("M8*1")["pitch_mm"], 1.0, places=9
        )

    def test_lowercase_and_spacing_are_tolerated(self):
        self.assertAlmostEqual(
            parse_thread_designation(" m 10 x 1.25 ")["nominal_diameter_mm"], 10.0, places=9
        )

    def test_small_size_flag_follows_the_threshold(self):
        self.assertTrue(parse_thread_designation("M2")["small_size"])
        self.assertFalse(parse_thread_designation("M3")["small_size"])

    def test_threshold_diameter_is_not_small(self):
        parsed = parse_thread_designation("M2.5")
        self.assertAlmostEqual(
            parsed["nominal_diameter_mm"], SMALL_SIZE_THRESHOLD_MM, places=9
        )
        self.assertFalse(parsed["small_size"])

    def test_non_metric_designation_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("1/4-28 UNF")

    def test_untabulated_diameter_without_a_pitch_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("M7")

    def test_pitch_not_smaller_than_diameter_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("M3x3")

    def test_two_pitches_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("M6x1x1")

    def test_non_numeric_diameter_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("Mbig")

    def test_blank_designation_rejected(self):
        with self.assertRaises(ValueError):
            parse_thread_designation("   ")

    def test_coarse_pitch_lookup_rejects_an_untabulated_size(self):
        with self.assertRaises(ValueError):
            coarse_pitch_for(7.0)

    def test_coarse_pitch_lookup_rejects_a_negative_size(self):
        with self.assertRaises(ValueError):
            coarse_pitch_for(-6.0)


class KindTests(unittest.TestCase):
    def test_bolt_is_in_scope(self):
        self.assertEqual(kind_verdict("bolt")[0], "in-scope")

    def test_threaded_insert_is_in_scope(self):
        self.assertEqual(kind_verdict("threaded-insert")[0], "in-scope")

    def test_loose_nut_is_out_of_scope(self):
        self.assertEqual(kind_verdict("nut")[0], "out-of-scope")

    def test_nut_in_a_procured_set_is_in_scope(self):
        self.assertEqual(kind_verdict("nut", True)[0], "in-scope-as-set-member")

    def test_rivet_is_out_of_scope_even_in_a_set(self):
        self.assertEqual(kind_verdict("rivet", True)[0], "out-of-scope")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            kind_verdict("turnbuckle")

    def test_non_boolean_set_flag_rejected(self):
        with self.assertRaises(ValueError):
            kind_verdict("nut", "yes")

    def test_kind_listing_keeps_the_three_groups_apart(self):
        listing = item_kinds()
        self.assertIn("bolt", listing["primary"])
        self.assertIn("nut", listing["set_member"])
        self.assertIn("rivet", listing["excluded"])


class ApplicationTests(unittest.TestCase):
    def test_flight_hardware_is_in_scope(self):
        self.assertEqual(application_verdict("flight")[0], "in-scope")

    def test_plain_ground_support_is_out_of_scope(self):
        self.assertEqual(application_verdict("ground-support")[0], "out-of-scope")

    def test_ground_support_in_a_flight_load_path_is_in_scope(self):
        self.assertEqual(application_verdict("ground-support", True)[0], "in-scope")

    def test_unknown_application_rejected(self):
        with self.assertRaises(ValueError):
            application_verdict("simulator")

    def test_non_boolean_load_flag_rejected(self):
        with self.assertRaises(ValueError):
            application_verdict("test-rig", 1)


class ClauseGroupTests(unittest.TestCase):
    def test_critical_in_scope_item_owes_every_group(self):
        self.assertEqual(clause_groups("in-scope", "critical"), tuple(ALL_CLAUSE_GROUPS))

    def test_minor_item_does_not_owe_the_test_programme(self):
        self.assertNotIn("testing", clause_groups("in-scope", "minor"))

    def test_small_size_drops_the_test_programme(self):
        self.assertNotIn("testing", clause_groups("in-scope", "critical", True))

    def test_records_survive_every_reduction(self):
        self.assertIn("records", clause_groups("in-scope", "minor", True))

    def test_out_of_scope_item_owes_nothing(self):
        self.assertEqual(clause_groups("out-of-scope", "critical"), ())

    def test_set_member_owes_the_same_groups_as_a_primary_item(self):
        self.assertEqual(
            clause_groups("in-scope-as-set-member", "major"),
            clause_groups("in-scope", "major"),
        )

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            clause_groups("in-scope", "catastrophic")

    def test_non_boolean_small_size_rejected(self):
        with self.assertRaises(ValueError):
            clause_groups("in-scope", "major", "small")


class AssessmentTests(unittest.TestCase):
    def _item(self, **overrides):
        item = {
            "kind": "bolt",
            "application": "flight",
            "criticality": "critical",
            "thread_designation": "M6",
        }
        item.update(overrides)
        return item

    def test_flight_bolt_is_in_scope_with_no_findings(self):
        result = assess_scope(self._item())
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["findings"], [])

    def test_ground_support_bolt_falls_out(self):
        result = assess_scope(self._item(application="ground-support"))
        self.assertFalse(result["in_scope"])
        self.assertEqual(result["clause_groups"], [])

    def test_ground_support_bolt_in_a_flight_load_path_stays_in(self):
        result = assess_scope(
            self._item(application="ground-support", carries_flight_load=True)
        )
        self.assertTrue(result["in_scope"])

    def test_loose_nut_falls_out_on_kind(self):
        result = assess_scope(self._item(kind="nut"))
        self.assertFalse(result["in_scope"])
        self.assertEqual(result["kind_verdict"], "out-of-scope")

    def test_nut_in_a_set_is_in_scope_as_a_set_member(self):
        result = assess_scope(self._item(kind="nut", procured_as_set=True))
        self.assertEqual(result["verdict"], "in-scope-as-set-member")

    def test_small_flight_screw_drops_the_test_group_and_says_so(self):
        result = assess_scope(self._item(kind="screw", thread_designation="M2"))
        self.assertNotIn("testing", result["clause_groups"])
        self.assertTrue(any("below" in f for f in result["findings"]))

    def test_out_of_scope_item_does_not_get_a_size_finding(self):
        result = assess_scope(
            self._item(kind="rivet", thread_designation="M2")
        )
        self.assertEqual(len(result["findings"]), 1)

    def test_missing_thread_designation_is_a_finding_not_a_refusal(self):
        item = self._item()
        del item["thread_designation"]
        result = assess_scope(item)
        self.assertTrue(result["in_scope"])
        self.assertTrue(any("thread designation" in f for f in result["findings"]))

    def test_both_reasons_are_reported(self):
        self.assertEqual(len(assess_scope(self._item())["reasons"]), 2)

    def test_parsed_thread_is_returned(self):
        result = assess_scope(self._item(thread_designation="M8x1"))
        self.assertAlmostEqual(result["thread"]["pitch_mm"], 1.0, places=9)

    def test_missing_key_rejected(self):
        item = self._item()
        del item["criticality"]
        with self.assertRaises(ValueError):
            assess_scope(item)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_scope(["bolt"])

    def test_bad_thread_designation_is_refused(self):
        with self.assertRaises(ValueError):
            assess_scope(self._item(thread_designation="M7"))


if __name__ == "__main__":
    unittest.main()

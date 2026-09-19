#!/usr/bin/env python3
"""Contract test for fastener visual and dimensional inspection (offline)."""

import copy
import unittest

from q7046_visual_and_dimensional_logic import (
    ALWAYS_REJECTABLE,
    DISCONTINUITIES,
    FEATURES,
    STRESS_CONCENTRATING_ZONES,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    ZONES,
    allowable_discontinuity_depth,
    assess_dimension,
    assess_discontinuity,
    assess_fastener,
    basic_thread_height,
    summarize_inspection,
)

GOOD_FASTENER = {
    "id": "SN-0001",
    "pitch_mm": 1.5,
    "discontinuities": [
        {"zone": "shank", "discontinuity": "tool-mark", "depth_mm": 0.05},
    ],
    "dimensions": [
        {
            "feature": "major-diameter",
            "measured_mm": 9.98,
            "nominal_mm": 10.0,
            "plus_tol_mm": 0.0,
            "minus_tol_mm": 0.08,
        },
        {
            "feature": "head-height",
            "measured_mm": 6.35,
            "nominal_mm": 6.4,
            "plus_tol_mm": 0.15,
            "minus_tol_mm": 0.15,
        },
    ],
}


def _fastener(**overrides):
    record = copy.deepcopy(GOOD_FASTENER)
    record.update(overrides)
    return record


class ThreadGeometryTests(unittest.TestCase):
    def test_basic_height_scales_with_the_pitch(self):
        self.assertAlmostEqual(
            basic_thread_height(2.0), 2.0 * basic_thread_height(1.0), places=9
        )

    def test_basic_height_is_the_iso_triangle(self):
        self.assertAlmostEqual(basic_thread_height(1.0), 0.8660254037844386, places=9)

    def test_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            basic_thread_height(0.0)

    def test_negative_pitch_rejected(self):
        with self.assertRaises(ValueError):
            basic_thread_height(-1.25)


class DiscontinuityAllowanceTests(unittest.TestCase):
    def test_nothing_is_allowed_in_a_stress_concentrating_zone(self):
        for zone in STRESS_CONCENTRATING_ZONES:
            for kind in DISCONTINUITIES:
                self.assertAlmostEqual(
                    allowable_discontinuity_depth(zone, kind, 1.5), 0.0, places=9
                )

    def test_a_crack_is_allowed_nowhere(self):
        for zone in ZONES:
            for kind in ALWAYS_REJECTABLE:
                self.assertAlmostEqual(
                    allowable_discontinuity_depth(zone, kind, 2.0), 0.0, places=9
                )

    def test_allowance_grows_with_the_pitch(self):
        coarse = allowable_discontinuity_depth("shank", "seam", 3.0)
        fine = allowable_discontinuity_depth("shank", "seam", 1.0)
        self.assertGreater(coarse, fine * 2.5)

    def test_a_tool_mark_is_allowed_less_than_a_burr(self):
        mark = allowable_discontinuity_depth("head-top", "tool-mark", 1.5)
        burr = allowable_discontinuity_depth("head-top", "burr", 1.5)
        self.assertGreater(burr, mark)

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            allowable_discontinuity_depth("washer-face-chamfer", "seam", 1.5)

    def test_unknown_discontinuity_rejected(self):
        with self.assertRaises(ValueError):
            allowable_discontinuity_depth("shank", "scuff", 1.5)


class DiscontinuityVerdictTests(unittest.TestCase):
    def test_a_depth_exactly_on_the_allowance_is_accepted(self):
        allowed = allowable_discontinuity_depth("shank", "seam", 1.5)
        result = assess_discontinuity("shank", "seam", allowed, 1.5)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["allowed_depth_mm"], allowed, places=9)

    def test_a_deeper_seam_is_rejected(self):
        allowed = allowable_discontinuity_depth("shank", "seam", 1.5)
        result = assess_discontinuity("shank", "seam", allowed * 2.0, 1.5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("exceeds", result["reason"])

    def test_a_shallow_lap_in_the_thread_root_is_still_rejected(self):
        result = assess_discontinuity("thread-root", "lap", 0.0005, 1.5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("thread-root", result["reason"])

    def test_a_hairline_crack_on_the_head_top_is_rejected(self):
        result = assess_discontinuity("head-top", "crack", 0.001, 1.5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("any depth", result["reason"])

    def test_negative_depth_rejected(self):
        with self.assertRaises(ValueError):
            assess_discontinuity("shank", "seam", -0.1, 1.5)


class DimensionTests(unittest.TestCase):
    def test_a_measurement_on_nominal_is_accepted(self):
        result = assess_dimension("shank-diameter", 9.0, 9.0, 0.05, 0.05)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["deviation_mm"], 0.0, places=9)

    def test_a_measurement_exactly_on_the_upper_limit_is_accepted(self):
        result = assess_dimension("head-diameter", 16.2, 16.0, 0.2, 0.2)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["margin_mm"], 0.0, places=9)

    def test_a_measurement_past_the_lower_limit_is_rejected(self):
        result = assess_dimension("fillet-radius", 0.3, 0.6, 0.2, 0.1)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertLess(result["margin_mm"], 0.0)

    def test_an_asymmetric_band_is_honoured_on_both_sides(self):
        high = assess_dimension("pitch-diameter", 9.05, 9.0, 0.0, 0.1)
        low = assess_dimension("pitch-diameter", 8.95, 9.0, 0.0, 0.1)
        self.assertEqual(high["verdict"], VERDICT_REJECT)
        self.assertEqual(low["verdict"], VERDICT_ACCEPT)

    def test_a_zero_width_band_is_rejected_as_uninspectable(self):
        with self.assertRaises(ValueError):
            assess_dimension("grip-length", 20.0, 20.0, 0.0, 0.0)

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimension("knurl-depth", 1.0, 1.0, 0.1, 0.1)

    def test_every_feature_name_is_inspectable(self):
        for feature in FEATURES:
            result = assess_dimension(feature, 5.0, 5.0, 0.1, 0.1)
            self.assertEqual(result["verdict"], VERDICT_ACCEPT)


class FastenerRollupTests(unittest.TestCase):
    def test_a_clean_fastener_is_accepted(self):
        result = assess_fastener(GOOD_FASTENER)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_one_bad_dimension_rejects_the_fastener(self):
        record = _fastener()
        record["dimensions"][0]["measured_mm"] = 9.5
        result = assess_fastener(record)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(len(result["findings"]), 1)

    def test_an_empty_inspection_is_not_a_pass(self):
        with self.assertRaises(ValueError):
            assess_fastener({"id": "SN-0002", "pitch_mm": 1.5})

    def test_a_record_without_an_id_is_rejected(self):
        record = _fastener(id="")
        with self.assertRaises(ValueError):
            assess_fastener(record)

    def test_a_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_fastener("one bolt, looked fine")


class SummaryTests(unittest.TestCase):
    def test_summary_counts_and_rate_agree(self):
        good = _fastener(id="SN-A")
        bad = _fastener(id="SN-B")
        bad["discontinuities"] = [
            {"zone": "thread-root", "discontinuity": "seam", "depth_mm": 0.01}
        ]
        summary = summarize_inspection([good, bad, _fastener(id="SN-C")])
        self.assertEqual(summary["inspected"], 3)
        self.assertEqual(summary["rejected"], 1)
        self.assertEqual(summary["accepted"], 2)
        self.assertEqual(summary["rejected_ids"], ["SN-B"])
        self.assertEqual(summary["reject_rate_per_hundred"], 33)

    def test_summary_groups_the_cause_of_each_reject(self):
        bad = _fastener(id="SN-D")
        bad["discontinuities"] = [
            {"zone": "head-to-shank-fillet", "discontinuity": "lap", "depth_mm": 0.02}
        ]
        summary = summarize_inspection([bad])
        self.assertEqual(summary["grouped_causes"]["head-to-shank-fillet/lap"], 1)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            summarize_inspection([_fastener(id="SN-E"), _fastener(id="SN-E")])

    def test_an_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_inspection([])


if __name__ == "__main__":
    unittest.main()

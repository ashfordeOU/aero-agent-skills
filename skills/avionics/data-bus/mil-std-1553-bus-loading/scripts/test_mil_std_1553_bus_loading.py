"""Contract test for the MIL-STD-1553 bus loading model.

Offline, deterministic, stdlib unittest. Run with:
    python3 scripts/test_mil_std_1553_bus_loading.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mil_std_1553_bus_loading_logic import (
    WORD_SLOT_US,
    FRAME_US_DEFAULT,
    LOAD_BUDGET_FRACTION,
    wire_words,
    message_time_us,
    schedule_utilization,
    schedule_headroom,
)

# Reference schedule from the wave-36 spec worked example (5 ms frame).
REF_SCHEDULE = [("BCRT", 16), ("RTBC", 32), ("RTRT", 8), ("BCRT", 4)]


class TestWireWords(unittest.TestCase):
    def test_wire_words_bcrt_16_is_18(self):
        self.assertEqual(wire_words("BCRT", 16), 18)

    def test_wire_words_rtbc_32_is_34(self):
        self.assertEqual(wire_words("RTBC", 32), 34)

    def test_wire_words_rtrt_8_is_11(self):
        self.assertEqual(wire_words("RTRT", 8), 11)

    def test_wire_words_bcrt_4_is_6(self):
        self.assertEqual(wire_words("BCRT", 4), 6)

    def test_wire_words_rtrt_32_is_35_hand_check(self):
        self.assertEqual(wire_words("RTRT", 32), 35)

    def test_wire_words_single_data_word_minimum(self):
        self.assertEqual(wire_words("BCRT", 1), 3)
        self.assertEqual(wire_words("RTBC", 1), 3)
        self.assertEqual(wire_words("RTRT", 1), 4)

    def test_wire_words_rtrt_is_one_more_than_rtbc(self):
        self.assertEqual(wire_words("RTRT", 8), wire_words("RTBC", 8) + 1)

    def test_wire_words_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            wire_words("BC-RT", 16)

    def test_wire_words_zero_data_words_raises(self):
        with self.assertRaises(ValueError):
            wire_words("BCRT", 0)

    def test_wire_words_33_data_words_raises(self):
        with self.assertRaises(ValueError):
            wire_words("RTRT", 33)

    def test_wire_words_negative_data_words_raises(self):
        with self.assertRaises(ValueError):
            wire_words("RTBC", -2)


class TestMessageTime(unittest.TestCase):
    def test_message_time_bcrt_16_is_432_us(self):
        self.assertAlmostEqual(message_time_us("BCRT", 16), 432.0, delta=1e-9)

    def test_message_time_rtbc_32_is_816_us(self):
        self.assertAlmostEqual(message_time_us("RTBC", 32), 816.0, delta=1e-9)

    def test_message_time_rtrt_8_is_264_us(self):
        self.assertAlmostEqual(message_time_us("RTRT", 8), 264.0, delta=1e-9)

    def test_message_time_bcrt_4_is_144_us(self):
        self.assertAlmostEqual(message_time_us("BCRT", 4), 144.0, delta=1e-9)

    def test_message_time_equals_wire_words_times_slot_identity(self):
        for kind, words in (("BCRT", 16), ("RTBC", 32), ("RTRT", 8)):
            self.assertEqual(message_time_us(kind, words),
                             float(wire_words(kind, words)) * WORD_SLOT_US)

    def test_message_time_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            message_time_us("RT2RT", 8)


class TestScheduleUtilization(unittest.TestCase):
    def test_reference_total_is_1656_us(self):
        u = schedule_utilization(REF_SCHEDULE)
        self.assertEqual(u["total_us"], 1656.0)

    def test_reference_utilization_is_33_12_percent(self):
        u = schedule_utilization(REF_SCHEDULE)
        self.assertAlmostEqual(u["utilization_pct"], 33.12, delta=1e-4)
        self.assertAlmostEqual(u["utilization_fraction"], 0.3312, delta=1e-6)

    def test_reference_verdict_is_fits(self):
        self.assertEqual(schedule_utilization(REF_SCHEDULE)["verdict"], "FITS")

    def test_reference_headroom_is_46_88_percent(self):
        u = schedule_utilization(REF_SCHEDULE)
        self.assertAlmostEqual(u["headroom_pct"], 46.88, delta=1e-4)
        self.assertEqual(u["headroom_us"], 2344.0)

    def test_headroom_matches_schedule_headroom_function(self):
        u = schedule_utilization(REF_SCHEDULE)
        self.assertAlmostEqual(u["headroom_pct"],
                               schedule_headroom(REF_SCHEDULE), delta=1e-9)

    def test_four_times_schedule_is_over_132_48(self):
        u = schedule_utilization(REF_SCHEDULE * 4)
        self.assertEqual(u["total_us"], 6624.0)
        self.assertAlmostEqual(u["utilization_pct"], 132.48, delta=1e-4)
        self.assertEqual(u["verdict"], "OVER")
        self.assertLess(u["headroom_pct"], 0.0)

    def test_over_case_negative_headroom_value(self):
        u = schedule_utilization(REF_SCHEDULE * 4)
        self.assertAlmostEqual(u["headroom_pct"], -52.48, delta=1e-4)

    def test_dict_keys_exactly_as_documented(self):
        u = schedule_utilization(REF_SCHEDULE)
        self.assertEqual(list(u.keys()),
                         ["total_us", "utilization_fraction",
                          "utilization_pct", "budget_us", "headroom_us",
                          "headroom_pct", "verdict"])

    def test_custom_frame_length_scales_utilization(self):
        u = schedule_utilization(REF_SCHEDULE, frame_us=10000.0)
        self.assertAlmostEqual(u["utilization_pct"], 16.56, delta=1e-4)
        self.assertEqual(u["budget_us"], 8000.0)
        self.assertEqual(u["verdict"], "FITS")

    def test_exact_budget_boundary_is_fits(self):
        # Ten BCRT 8-data-word messages: 10 words each, 100 wire words at
        # 24 us = 2400 us on a 3 ms frame with an 80 percent budget of
        # exactly 2400 us.
        u = schedule_utilization([("BCRT", 8)] * 10, frame_us=3000.0)
        self.assertEqual(u["total_us"], u["budget_us"])
        self.assertEqual(u["verdict"], "FITS")
        self.assertAlmostEqual(u["headroom_pct"], 0.0, delta=1e-9)

    def test_deterministic_repeat_calls(self):
        self.assertEqual(schedule_utilization(REF_SCHEDULE),
                         schedule_utilization(REF_SCHEDULE))

    def test_budget_is_80_percent_of_frame(self):
        u = schedule_utilization([("BCRT", 1)])
        self.assertEqual(u["budget_us"],
                         LOAD_BUDGET_FRACTION * FRAME_US_DEFAULT)

    def test_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            schedule_utilization([])

    def test_zero_frame_raises(self):
        with self.assertRaises(ValueError):
            schedule_utilization(REF_SCHEDULE, frame_us=0.0)

    def test_negative_frame_raises(self):
        with self.assertRaises(ValueError):
            schedule_utilization(REF_SCHEDULE, frame_us=-1.0)


class TestScheduleHeadroom(unittest.TestCase):
    def test_headroom_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            schedule_headroom([])

    def test_headroom_nonpositive_frame_raises(self):
        with self.assertRaises(ValueError):
            schedule_headroom(REF_SCHEDULE, frame_us=0.0)

    def test_headroom_is_percent_of_frame(self):
        h = schedule_headroom(REF_SCHEDULE)
        self.assertEqual(h, (LOAD_BUDGET_FRACTION * FRAME_US_DEFAULT
                             - 1656.0) / FRAME_US_DEFAULT * 100.0)


if __name__ == "__main__":
    unittest.main()

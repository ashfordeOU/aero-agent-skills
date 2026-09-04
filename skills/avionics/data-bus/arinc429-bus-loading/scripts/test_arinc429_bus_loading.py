"""Contract tests for the ARINC 429 bus loading budget (offline, deterministic).

Run with: python3 scripts/test_arinc429_bus_loading.py
Covers the reference schedule, the worked-example magnitude bounds,
the 12.5 kbps link cases, capacity and headroom boundaries, the
convenience summary dict, determinism, and ValueError rejection of
non-physical inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arinc429_bus_loading_logic as abl

REF_SCHEDULE = [50] * 3 + [20] * 4 + [10] * 2  # 3 at 50 Hz, 4 at 20 Hz, 2 at 10 Hz


class TestTotalWordRate(unittest.TestCase):
    def test_reference_schedule_is_250(self):
        self.assertAlmostEqual(abl.total_word_rate(REF_SCHEDULE), 250.0, places=9)

    def test_single_one_hz_label_is_one(self):
        self.assertAlmostEqual(abl.total_word_rate([1]), 1.0, places=9)

    def test_dict_schedule_sums_values(self):
        rates = {"altitude": 50, "airspeed": 20, "heading": 10}
        self.assertAlmostEqual(abl.total_word_rate(rates), 80.0, places=9)

    def test_empty_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            abl.total_word_rate([])
        with self.assertRaises(ValueError):
            abl.total_word_rate({})

    def test_negative_rate_raises_value_error(self):
        with self.assertRaises(ValueError):
            abl.total_word_rate([50, -20, 10])
        with self.assertRaises(ValueError):
            abl.total_word_rate({"alt": 50, "ias": -1})

    def test_zero_rate_label_is_allowed(self):
        self.assertAlmostEqual(abl.total_word_rate([50, 0]), 50.0, places=9)


class TestBusLoadBps(unittest.TestCase):
    def test_reference_load_is_9000(self):
        self.assertAlmostEqual(abl.bus_load_bps(250), 9000.0, places=9)

    def test_hundred_and_single_word_loads(self):
        self.assertAlmostEqual(abl.bus_load_bps(100), 3600.0, places=9)
        self.assertAlmostEqual(abl.bus_load_bps(1), 36.0, places=9)

    def test_negative_word_rate_raises_value_error(self):
        with self.assertRaises(ValueError):
            abl.bus_load_bps(-1)

    def test_nonpositive_bits_raise_value_error(self):
        with self.assertRaises(ValueError):
            abl.bus_load_bps(100, bits_per_word=0)
        with self.assertRaises(ValueError):
            abl.bus_load_bps(100, bits_per_word=-36)


class TestPercentUtilization(unittest.TestCase):
    def test_worked_case_is_9_percent(self):
        self.assertAlmostEqual(abl.percent_utilization(9000), 9.0, places=9)

    def test_at_capacity_is_100_percent_within_tolerance(self):
        load_at_capacity = abl.bus_load_bps(abl.word_capacity())
        self.assertAlmostEqual(abl.percent_utilization(load_at_capacity), 100.0, places=6)

    def test_3000_words_is_108_percent(self):
        self.assertAlmostEqual(abl.percent_utilization(abl.bus_load_bps(3000)), 108.0, places=9)

    def test_invalid_load_or_link_raises_value_error(self):
        with self.assertRaises(ValueError):
            abl.percent_utilization(-1)
        with self.assertRaises(ValueError):
            abl.percent_utilization(9000, link_rate_bps=0)
        with self.assertRaises(ValueError):
            abl.percent_utilization(9000, link_rate_bps=-100000)


class TestWordCapacity(unittest.TestCase):
    def test_capacity_100kbps_is_2777_78(self):
        self.assertAlmostEqual(abl.word_capacity(), 2777.777777777778, places=3)
        self.assertAlmostEqual(abl.word_capacity(abl.RATE_100_KBPS), 2777.777777777778, places=3)

    def test_capacity_12_5kbps_is_347_22(self):
        self.assertAlmostEqual(abl.word_capacity(abl.RATE_12_5_KBPS), 347.22222222222223, places=3)

    def test_capacity_with_own_bits_per_word(self):
        self.assertAlmostEqual(abl.word_capacity(100000, bits_per_word=40), 2500.0, places=9)

    def test_nonpositive_link_or_bits_raise_value_error(self):
        with self.assertRaises(ValueError):
            abl.word_capacity(link_rate_bps=0)
        with self.assertRaises(ValueError):
            abl.word_capacity(bits_per_word=0)


class TestCapacityVerdict(unittest.TestCase):
    def test_reference_fits_with_headroom_71(self):
        verdict = abl.capacity_verdict(250)
        self.assertEqual(verdict["verdict"], "FITS")
        self.assertAlmostEqual(verdict["utilization_pct"], 9.0, places=9)
        self.assertAlmostEqual(verdict["headroom_pct"], 71.0, places=9)
        self.assertAlmostEqual(verdict["capacity_wps"], 2777.777777777778, places=3)

    def test_3000_words_verdict_over_with_zero_headroom(self):
        verdict = abl.capacity_verdict(3000)
        self.assertEqual(verdict["verdict"], "OVER")
        self.assertAlmostEqual(verdict["utilization_pct"], 108.0, places=9)
        self.assertEqual(verdict["headroom_pct"], 0.0)

    def test_exact_capacity_fits_at_100_percent(self):
        verdict = abl.capacity_verdict(abl.word_capacity())
        self.assertAlmostEqual(verdict["utilization_pct"], 100.0, places=6)
        self.assertEqual(verdict["verdict"], "FITS")
        self.assertEqual(verdict["headroom_pct"], 0.0)

    def test_at_80_percent_design_load_headroom_is_zero(self):
        schedule_at_80 = abl.word_capacity() * 0.8
        verdict = abl.capacity_verdict(schedule_at_80)
        self.assertAlmostEqual(verdict["utilization_pct"], 80.0, places=6)
        self.assertAlmostEqual(verdict["headroom_pct"], 0.0, places=6)

    def test_negative_word_rate_raises_value_error(self):
        with self.assertRaises(ValueError):
            abl.capacity_verdict(-5)

    def test_dict_keys_exact(self):
        self.assertEqual(
            set(abl.capacity_verdict(250).keys()),
            {"capacity_wps", "utilization_pct", "verdict", "headroom_pct"},
        )


class TestTwelveFiveKbpsLink(unittest.TestCase):
    def test_300_words_fits_at_86_4_percent(self):
        verdict = abl.capacity_verdict(300, abl.RATE_12_5_KBPS)
        self.assertAlmostEqual(verdict["utilization_pct"], 86.4, places=9)
        self.assertEqual(verdict["verdict"], "FITS")
        self.assertEqual(verdict["headroom_pct"], 0.0)

    def test_350_words_over_at_100_8_percent(self):
        verdict = abl.capacity_verdict(350, abl.RATE_12_5_KBPS)
        self.assertAlmostEqual(verdict["utilization_pct"], 100.8, places=9)
        self.assertEqual(verdict["verdict"], "OVER")


class TestBusLoadingSummary(unittest.TestCase):
    def test_summary_reference_keys_and_values(self):
        summary = abl.bus_loading_summary(REF_SCHEDULE)
        self.assertEqual(
            set(summary.keys()),
            {"total_words_per_s", "load_bps", "utilization_pct",
             "capacity_wps", "verdict", "headroom_pct"},
        )
        self.assertAlmostEqual(summary["total_words_per_s"], 250.0, places=9)
        self.assertAlmostEqual(summary["load_bps"], 9000.0, places=9)
        self.assertAlmostEqual(summary["utilization_pct"], 9.0, places=9)
        self.assertAlmostEqual(summary["capacity_wps"], 2777.777777777778, places=3)
        self.assertEqual(summary["verdict"], "FITS")
        self.assertAlmostEqual(summary["headroom_pct"], 71.0, places=9)

    def test_summary_adding_one_100hz_label(self):
        summary = abl.bus_loading_summary(REF_SCHEDULE + [100])
        self.assertAlmostEqual(summary["total_words_per_s"], 350.0, places=9)
        self.assertAlmostEqual(summary["load_bps"], 12600.0, places=9)
        self.assertAlmostEqual(summary["utilization_pct"], 12.6, places=9)
        self.assertEqual(summary["verdict"], "FITS")

    def test_summary_thirty_labels_at_100hz_over(self):
        summary = abl.bus_loading_summary([100] * 30)
        self.assertAlmostEqual(summary["total_words_per_s"], 3000.0, places=9)
        self.assertAlmostEqual(summary["utilization_pct"], 108.0, places=9)
        self.assertEqual(summary["verdict"], "OVER")
        self.assertEqual(summary["headroom_pct"], 0.0)

    def test_summary_accepts_dict_input(self):
        summary = abl.bus_loading_summary({"alt": 50, "ias": 20})
        self.assertAlmostEqual(summary["total_words_per_s"], 70.0, places=9)

    def test_summary_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            abl.bus_loading_summary([])
        with self.assertRaises(ValueError):
            abl.bus_loading_summary([50, -5])
        with self.assertRaises(ValueError):
            abl.bus_loading_summary([50], link_rate_bps=0)


class TestIdentities(unittest.TestCase):
    def test_doubling_every_rate_doubles_utilization(self):
        base = [50, 20, 20, 10]
        util_base = abl.percent_utilization(abl.bus_load_bps(abl.total_word_rate(base)))
        util_double = abl.percent_utilization(
            abl.bus_load_bps(abl.total_word_rate([2 * r for r in base]))
        )
        self.assertAlmostEqual(util_double, 2.0 * util_base, places=9)

    def test_determinism_identical_inputs_identical_outputs(self):
        self.assertEqual(
            abl.bus_loading_summary(REF_SCHEDULE), abl.bus_loading_summary(REF_SCHEDULE)
        )
        self.assertEqual(abl.capacity_verdict(250), abl.capacity_verdict(250))


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(abl.BITS_PER_WORD, 36.0)
        self.assertEqual(abl.RATE_100_KBPS, 100000.0)
        self.assertEqual(abl.RATE_12_5_KBPS, 12500.0)
        self.assertEqual(abl.DESIGN_GUIDELINE_PCT, 80.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

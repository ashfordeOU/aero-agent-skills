#!/usr/bin/env python3
"""Deterministic contract test for the noise certification test logic.

Runs offline with stdlib unittest only:

    python3 scripts/test_noise_certification_test.py

Covers the worked example contract: reference geometry for the
flyover, sideline and approach conditions, EPNL integration with the
10 dB down rule and the 10 s normalization (constant series closed
form 90 + 10*log10(20/10) = 93.01), the truncated single peak series
(~89.0 EPNdB with interpolated window bounds), the 100 dB pulse
series staying below 100 EPNdB, margin to limit verdicts, the
cumulative chapter 4 style rule branches, the test matrix helper, the
summary helper, and ValueError rejection of empty, non-finite or
non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noise_certification_test_logic as nct


def raised_cosine_peak92():
    """Symmetric single peak series, 41 samples at 0.5 s (20 s total).

    Peak 92.0 dB at sample 20 (t = 10 s), values falling 10 dB below
    the maximum (82.0 dB) at the series ends: a raised cosine hump of
    half width 6 s over a flat 82.0 dB baseline.
    """
    series = []
    for i in range(41):
        t = i * 0.5
        dist = abs(t - 10.0)
        if dist <= 6.0:
            series.append(82.0 + 10.0 * math.cos(math.pi * dist / 12.0) ** 2)
        else:
            series.append(82.0)
    return series


def pulse100_series():
    """PNLT = 100 dB for t in [8, 12] s, 80 dB elsewhere (no tone)."""
    series = []
    for i in range(41):
        t = i * 0.5
        series.append(100.0 if 8.0 <= t <= 12.0 else 80.0)
    return series


class GeometryTest(unittest.TestCase):
    """Reference geometry for the three measurement conditions."""

    def test_geometry_flyover_distance(self):
        geo = nct.geometry("flyover")
        self.assertEqual(geo["condition"], "flyover")
        self.assertEqual(geo["distance_m"], nct.FLYOVER_DISTANCE_M)
        self.assertEqual(geo["distance_m"], 6500.0)

    def test_geometry_sideline_lateral(self):
        geo = nct.geometry("sideline")
        self.assertEqual(geo["condition"], "sideline")
        self.assertEqual(geo["lateral_m"], nct.SIDELINE_LATERAL_M)
        self.assertEqual(geo["lateral_m"], 450.0)

    def test_geometry_approach_values(self):
        geo = nct.geometry("approach")
        self.assertEqual(geo["condition"], "approach")
        self.assertEqual(geo["distance_m"], nct.APPROACH_DISTANCE_M)
        self.assertEqual(geo["distance_m"], 1200.0)
        self.assertEqual(geo["altitude_m"], nct.APPROACH_ALTITUDE_M)
        self.assertEqual(geo["altitude_m"], 120.0)
        self.assertEqual(geo["glide_deg"], nct.APPROACH_GLIDE_DEG)
        self.assertEqual(geo["glide_deg"], 3.0)

    def test_geometry_unknown_condition_raises(self):
        for bad in ("hover", "takeoff", "flyover-2", "", None):
            with self.assertRaises(ValueError):
                nct.geometry(bad)

    def test_module_constants(self):
        self.assertEqual(nct.T0, 10.0)
        self.assertEqual(nct.DB_DOWN, 10.0)
        self.assertEqual(nct.CUMULATIVE_REQUIRED_DB, 10.0)
        self.assertEqual(nct.FLYOVER_DISTANCE_M, 6500.0)
        self.assertEqual(nct.SIDELINE_LATERAL_M, 450.0)
        self.assertEqual(nct.APPROACH_DISTANCE_M, 1200.0)
        self.assertEqual(nct.APPROACH_ALTITUDE_M, 120.0)
        self.assertEqual(nct.APPROACH_GLIDE_DEG, 3.0)


class EpnlIntegrationTest(unittest.TestCase):
    """EPNL integration with the 10 dB down rule and T0 normalization."""

    def test_constant_series_closed_form(self):
        # 41 samples at 0.5 s = 20 s of constant 90 dB; never drops
        # 10 dB below the maximum, so the full series is integrated and
        # EPNL = 90 + 10*log10(20/10) = 93.0102999566.
        series = [90.0] * 41
        epnl, t_start, t_end, truncated = nct.epnl_from_pnlt(series, 0.5)
        expected = 90.0 + 10.0 * math.log10(20.0 / 10.0)
        self.assertAlmostEqual(epnl, expected, places=6)
        self.assertAlmostEqual(epnl, 93.0102999566, places=6)

    def test_constant_series_full_span_and_not_truncated(self):
        series = [90.0] * 41
        _, t_start, t_end, truncated = nct.epnl_from_pnlt(series, 0.5)
        self.assertAlmostEqual(t_start, 0.0, places=9)
        self.assertAlmostEqual(t_end, 20.0, places=9)
        self.assertFalse(truncated)

    def test_peak92_series_about_89(self):
        # Spec worked example: single peak 92 dB at sample 20 falling
        # 10 dB below the maximum at the ends; module value ~ 89.0.
        series = raised_cosine_peak92()
        epnl, _, _, _ = nct.epnl_from_pnlt(series, 0.5)
        self.assertEqual(max(series), 92.0)
        self.assertEqual(series.index(max(series)), 20)
        self.assertAlmostEqual(epnl, 89.1267284536, places=6)
        self.assertTrue(85.0 < epnl < 92.0)

    def test_peak92_series_window_bounds_and_truncated(self):
        series = raised_cosine_peak92()
        _, t_start, t_end, truncated = nct.epnl_from_pnlt(series, 0.5)
        # 10 dB down crossings at the raised cosine edges, t = 4 s and
        # t = 16 s, with the 82 dB baseline outside the window.
        self.assertAlmostEqual(t_start, 4.0, places=6)
        self.assertAlmostEqual(t_end, 16.0, places=6)
        self.assertTrue(truncated)

    def test_pulse100_series_below_100(self):
        # Peak instantaneous PNLT of 100 dB cannot produce EPNL >= 100
        # because the effective duration is below the 10 s reference.
        series = pulse100_series()
        epnl, _, _, _ = nct.epnl_from_pnlt(series, 0.5)
        self.assertLess(epnl, 100.0)
        self.assertAlmostEqual(epnl, 96.3093611906, places=6)

    def test_pulse_series_interpolated_bounds(self):
        series = pulse100_series()
        _, t_start, t_end, _ = nct.epnl_from_pnlt(series, 0.5)
        # Linear interpolation of the 90 dB crossing between the 80 dB
        # and 100 dB samples at the pulse edges.
        self.assertAlmostEqual(t_start, 7.75, places=6)
        self.assertAlmostEqual(t_end, 12.25, places=6)

    def test_level_shift_identity(self):
        # Adding a constant level shift to every sample shifts EPNL by
        # the same amount: EPNL(x + c) = EPNL(x) + c.
        base = raised_cosine_peak92()
        epnl_base, _, _, _ = nct.epnl_from_pnlt(base, 0.5)
        shifted = [v + 6.0 for v in base]
        epnl_shift, _, _, _ = nct.epnl_from_pnlt(shifted, 0.5)
        self.assertAlmostEqual(epnl_shift - epnl_base, 6.0, places=9)

    def test_default_dt_matches_explicit(self):
        series = [90.0] * 41
        epnl_default, _, _, _ = nct.epnl_from_pnlt(series)
        epnl_explicit, _, _, _ = nct.epnl_from_pnlt(series, 0.5)
        self.assertAlmostEqual(epnl_default, epnl_explicit, places=12)

    def test_single_sample_series_finite(self):
        # A lone sample is integrated over one dt interval at its level.
        epnl, t_start, t_end, truncated = nct.epnl_from_pnlt([90.0], 0.5)
        self.assertTrue(math.isfinite(epnl))
        self.assertAlmostEqual(t_start, 0.0, places=9)
        self.assertAlmostEqual(t_end, 0.0, places=9)
        self.assertFalse(truncated)

    def test_epnl_empty_or_non_finite_series_raises(self):
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([], 0.5)
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0, float("nan"), 90.0], 0.5)
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0, float("inf")], 0.5)
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0, float("-inf")], 0.5)

    def test_epnl_bad_dt_raises(self):
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0] * 10, 0.0)
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0] * 10, -0.5)
        with self.assertRaises(ValueError):
            nct.epnl_from_pnlt([90.0] * 10, float("nan"))


class MarginTest(unittest.TestCase):
    """Per point margin to the stated noise limit."""

    def test_margin_pass_1_99(self):
        margin_db, verdict = nct.margin_to_limit(93.01, 95.0)
        self.assertAlmostEqual(margin_db, 1.99, places=2)
        self.assertGreaterEqual(margin_db, 0.0)
        self.assertEqual(verdict, "pass")

    def test_margin_fail_negative(self):
        margin_db, verdict = nct.margin_to_limit(96.0, 95.0)
        self.assertAlmostEqual(margin_db, -1.0, places=9)
        self.assertEqual(verdict, "fail")

    def test_margin_zero_is_pass(self):
        margin_db, verdict = nct.margin_to_limit(95.0, 95.0)
        self.assertAlmostEqual(margin_db, 0.0, places=9)
        self.assertEqual(verdict, "pass")

    def test_margin_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            nct.margin_to_limit(90.0, -5.0)

    def test_margin_non_finite_epnl_raises(self):
        with self.assertRaises(ValueError):
            nct.margin_to_limit(float("nan"), 95.0)
        with self.assertRaises(ValueError):
            nct.margin_to_limit(float("inf"), 95.0)


class CumulativeMarginTest(unittest.TestCase):
    """Cumulative chapter 4 style rule over the three point set."""

    def test_cumulative_3_4_4_pass(self):
        result = nct.cumulative_margin([3.0, 4.0, 4.0])
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["sum_db"], 11.0, places=9)
        self.assertAlmostEqual(result["required_db"], 10.0, places=9)

    def test_cumulative_3_3_3_fail(self):
        result = nct.cumulative_margin([3.0, 3.0, 3.0])
        self.assertEqual(result["verdict"], "fail")
        self.assertAlmostEqual(result["sum_db"], 9.0, places=9)
        self.assertTrue(any("below" in r for r in result["reasons"]))

    def test_cumulative_negative_individual_fail(self):
        result = nct.cumulative_margin([-1.0, 6.0, 6.0])
        self.assertEqual(result["verdict"], "fail")
        self.assertAlmostEqual(result["sum_db"], 11.0, places=9)
        self.assertLess(result["min_margin_db"], 0.0)
        self.assertTrue(any("individual" in r for r in result["reasons"]))

    def test_cumulative_exact_required_pass(self):
        result = nct.cumulative_margin([2.0, 3.0, 5.0])
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["sum_db"], 10.0, places=9)

    def test_cumulative_empty_or_non_finite_raises(self):
        with self.assertRaises(ValueError):
            nct.cumulative_margin([])
        with self.assertRaises(ValueError):
            nct.cumulative_margin([3.0, float("nan"), 4.0])


class TestMatrixTest(unittest.TestCase):
    """Three condition certification test matrix builder."""

    LIMITS = {"flyover": 92.0, "sideline": 95.0, "approach": 98.0}

    def test_matrix_three_condition_rows(self):
        rows = nct.test_matrix(60000.0, 52000.0, 140.0, 135.0, self.LIMITS)
        self.assertEqual([r["condition"] for r in rows], ["flyover", "sideline", "approach"])

    def test_matrix_weights_speeds_limits(self):
        rows = nct.test_matrix(60000.0, 52000.0, 140.0, 135.0, self.LIMITS)
        by_cond = {r["condition"]: r for r in rows}
        self.assertEqual(by_cond["flyover"]["configuration"], "takeoff")
        self.assertEqual(by_cond["flyover"]["weight_kg"], 60000.0)
        self.assertAlmostEqual(by_cond["flyover"]["reference_speed_kt"], 150.0, places=6)
        self.assertEqual(by_cond["flyover"]["limit"], 92.0)
        self.assertEqual(by_cond["flyover"]["target_epnl"], 92.0)
        self.assertEqual(by_cond["sideline"]["configuration"], "takeoff")
        self.assertEqual(by_cond["sideline"]["weight_kg"], 60000.0)
        self.assertAlmostEqual(by_cond["sideline"]["reference_speed_kt"], 140.0, places=6)
        self.assertEqual(by_cond["sideline"]["limit"], 95.0)
        self.assertEqual(by_cond["approach"]["configuration"], "landing")
        self.assertEqual(by_cond["approach"]["weight_kg"], 52000.0)
        self.assertAlmostEqual(by_cond["approach"]["reference_speed_kt"], 135.0, places=6)
        self.assertEqual(by_cond["approach"]["limit"], 98.0)
        self.assertEqual(by_cond["approach"]["target_epnl"], 98.0)

    def test_matrix_missing_key_raises(self):
        with self.assertRaises(ValueError):
            nct.test_matrix(60000.0, 52000.0, 140.0, 135.0, {"flyover": 92.0, "sideline": 95.0})
        with self.assertRaises(ValueError):
            nct.test_matrix(60000.0, 52000.0, 140.0, 135.0, {})

    def test_matrix_bad_limits_or_weight_raises(self):
        with self.assertRaises(ValueError):
            nct.test_matrix(60000.0, 52000.0, 140.0, 135.0, {"flyover": -1.0, "sideline": 95.0, "approach": 98.0})
        with self.assertRaises(ValueError):
            nct.test_matrix(0.0, 52000.0, 140.0, 135.0, self.LIMITS)


class SummarizeTest(unittest.TestCase):
    """End to end summary across the three point set."""

    def test_summarize_epnl_margin_cumulative(self):
        epnls = {"flyover": 90.0, "sideline": 93.01, "approach": 96.0}
        limits = {"flyover": 92.0, "sideline": 95.0, "approach": 98.0}
        summary = nct.summarize(epnls, limits)
        self.assertEqual(summary["epnl"], epnls)
        self.assertAlmostEqual(summary["margin"]["sideline"], 1.99, places=2)
        self.assertEqual(summary["verdict"]["flyover"], "pass")
        self.assertEqual(summary["verdict"]["sideline"], "pass")
        self.assertEqual(summary["verdict"]["approach"], "pass")
        self.assertEqual(summary["cumulative"]["verdict"], "fail")
        # Cross check: summarize margins must match margin_to_limit.
        margin, verdict = nct.margin_to_limit(96.0, 98.0)
        self.assertAlmostEqual(summary["margin"]["approach"], margin, places=9)
        self.assertEqual(summary["verdict"]["approach"], verdict)

    def test_summarize_missing_epnl_key_raises(self):
        with self.assertRaises(ValueError):
            nct.summarize({"flyover": 90.0, "sideline": 93.01}, {"flyover": 92.0, "sideline": 95.0, "approach": 98.0})

    def test_summarize_missing_limit_key_raises(self):
        with self.assertRaises(ValueError):
            nct.summarize(
                {"flyover": 90.0, "sideline": 93.01, "approach": 96.0},
                {"flyover": 92.0, "sideline": 95.0},
            )


if __name__ == "__main__":
    unittest.main()

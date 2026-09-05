"""Contract test for the in-flight-engine-relight-test leaf (wave-41).

Offline, deterministic, pure stdlib. Exercises the SKILL.md workflow step by
step: step 1 (collect the windmill survey points), step 2 (fit the windmill
N2 regression), step 3 (read the minimum relight airspeed), step 4
(summarize the starter-assisted relight samples), step 5 (score each
altitude band of the demonstration), step 6 (combine the band verdicts into
the overall restart-demonstration verdict) and step 7 (confirm the
reduction with this contract test). The worked-example expectations come
from running the real module: windmill_regression slope 0.1500, intercept
3.0000 and r_squared 1.0000 on the survey TAS [70, 85, 105, 130] m/s with
windmill N2 [13.5, 15.75, 18.75, 22.5] pct, min_relight_airspeed 100.0000
m/s at WINDMILL_N2_MIN_REQUIRED_PCT = 18.0 pct, time_to_idle mean 41.80 s
and worst sample 52.40 s against the type-data limit RELIGHT_IDLE_LIMIT_S =
60.0 s, per-band PASS verdicts at FL200/FL300/FL410, and an overall PASS
restart-demonstration verdict.

Run: python3 scripts/test_in_flight_engine_relight_test.py (exit 0).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import in_flight_engine_relight_test_logic as relight


class TestModuleConstants(unittest.TestCase):
    """Workflow steps 3 and 4 read their thresholds from module constants."""

    def test_module_constants_pin_thresholds(self):
        """Step 3 reads the minimum relight airspeed at the required windmill
        N2 threshold and step 4 checks the starter-assisted relight samples
        against the type-data limit: both thresholds are module constants,
        WINDMILL_N2_MIN_REQUIRED_PCT = 18.0 and RELIGHT_IDLE_LIMIT_S = 60.0."""
        self.assertEqual(relight.WINDMILL_N2_MIN_REQUIRED_PCT, 18.0)
        self.assertEqual(relight.RELIGHT_IDLE_LIMIT_S, 60.0)


class TestWindmillRegression(unittest.TestCase):
    """Workflow step 2: fit the windmill N2 regression to the survey."""

    def test_worked_example_regression_values(self):
        """Step 2 fit on the worked example windmill survey returns slope
        0.1500 pct per m/s, intercept 3.0000 pct and r_squared 1.0000 within
        1e-9, matching the real module outputs."""
        reg = relight.windmill_regression([13.5, 15.75, 18.75, 22.5],
                                          [70.0, 85.0, 105.0, 130.0])
        self.assertAlmostEqual(reg["slope"], 0.1500, places=9)
        self.assertAlmostEqual(reg["intercept"], 3.0000, places=9)
        self.assertAlmostEqual(reg["r_squared"], 1.0000, places=9)

    def test_regression_dict_keys_exact(self):
        """Step 2 fit returns exactly the slope, intercept and r_squared
        keys documented in the windmill N2 regression contract."""
        reg = relight.windmill_regression([13.5, 15.75, 18.75, 22.5],
                                          [70.0, 85.0, 105.0, 130.0])
        self.assertEqual(sorted(reg.keys()),
                         ["intercept", "r_squared", "slope"])

    def test_generating_line_recovered_at_two_points(self):
        """Step 2 identity: the regression on N2 generated as 0.15 * TAS +
        3.0 recovers the generating slope and intercept exactly (within
        1e-12) at the two-point minimum survey."""
        tas = [70.0, 130.0]
        n2 = [0.15 * t + 3.0 for t in tas]
        reg = relight.windmill_regression(n2, tas)
        self.assertAlmostEqual(reg["slope"], 0.15, places=12)
        self.assertAlmostEqual(reg["intercept"], 3.0, places=12)
        self.assertAlmostEqual(reg["r_squared"], 1.0, places=12)

    def test_generating_line_recovered_at_many_points(self):
        """Step 2 identity at nine survey points: perfectly linear windmill
        N2 data over a spread TAS range returns the generating slope 0.15
        and intercept 3.0 exactly with r_squared 1.0 (within 1e-12)."""
        tas = [float(t) for t in range(60, 150, 10)]
        n2 = [0.15 * t + 3.0 for t in tas]
        reg = relight.windmill_regression(n2, tas)
        self.assertAlmostEqual(reg["slope"], 0.15, places=12)
        self.assertAlmostEqual(reg["intercept"], 3.0, places=12)
        self.assertEqual(reg["r_squared"], 1.0)

    def test_constant_n2_line_returns_unit_r_squared(self):
        """Step 2 degenerate constant-line case: windmill N2 that does not
        vary with true airspeed gives a flat line with r_squared 1.0 by
        definition (ss_tot is zero)."""
        reg = relight.windmill_regression([15.0, 15.0, 15.0],
                                          [70.0, 85.0, 105.0])
        self.assertAlmostEqual(reg["slope"], 0.0, places=12)
        self.assertAlmostEqual(reg["intercept"], 15.0, places=12)
        self.assertEqual(reg["r_squared"], 1.0)

    def test_mismatched_list_lengths_valueerror(self):
        """Step 2 rejects a windmill survey whose N2 and true airspeed lists
        differ in length with ValueError, never fitting across mismatched
        samples."""
        with self.assertRaises(ValueError):
            relight.windmill_regression([13.5, 15.75], [70.0])

    def test_single_survey_point_valueerror(self):
        """Step 2 rejects a one-point windmill survey with ValueError: the
        least-squares fit of N2 against true airspeed needs two or more
        survey points."""
        with self.assertRaises(ValueError):
            relight.windmill_regression([13.5], [70.0])

    def test_zero_tas_variance_valueerror(self):
        """Step 2 rejects a survey flown at constant true airspeed with
        ValueError: zero TAS variance leaves the regression denominator
        n * sxx - sx * sx at zero."""
        with self.assertRaises(ValueError):
            relight.windmill_regression([10.0, 20.0], [70.0, 70.0])


class TestMinRelightAirspeed(unittest.TestCase):
    """Workflow step 3: read the minimum relight airspeed where the fitted
    windmill N2 line crosses the required relight threshold."""

    def test_worked_example_min_relight_airspeed(self):
        """Step 3 on the worked example fit returns 100.0000 m/s (194.4 kt
        TAS) where the regression line reaches the 18.0 pct required
        windmill N2, within 1e-9 of the real module output."""
        vmin = relight.min_relight_airspeed(18.0, 0.15, 3.0)
        self.assertAlmostEqual(vmin, 100.0, places=9)
        self.assertAlmostEqual(vmin / 0.514444, 194.4, places=1)

    def test_threshold_shift_identity_positive_delta(self):
        """Step 3 identity: raising the required windmill N2 threshold by
        1.5 pct moves the minimum relight airspeed by 1.5 / 0.15 = 10.0 m/s
        on the worked example line."""
        base = relight.min_relight_airspeed(18.0, 0.15, 3.0)
        raised = relight.min_relight_airspeed(19.5, 0.15, 3.0)
        self.assertAlmostEqual(raised - base, 10.0, places=9)

    def test_threshold_shift_identity_negative_delta(self):
        """Step 3 identity downward: lowering the required windmill N2
        threshold by 3.0 pct moves the relight airspeed by -3.0 / 0.15 =
        -20.0 m/s, so the minimum relight airspeed falls to 80.0 m/s."""
        vmin = relight.min_relight_airspeed(15.0, 0.15, 3.0)
        self.assertAlmostEqual(vmin, 80.0, places=9)

    def test_nonpositive_threshold_valueerror(self):
        """Step 3 rejects a non-positive required windmill N2 threshold with
        ValueError."""
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                relight.min_relight_airspeed(bad, 0.15, 3.0)

    def test_nonpositive_slope_valueerror(self):
        """Step 3 rejects a non-positive windmill N2 regression slope with
        ValueError: windmill N2 must rise with true airspeed for a relight
        airspeed to exist."""
        for bad in (0.0, -0.1):
            with self.assertRaises(ValueError):
                relight.min_relight_airspeed(18.0, bad, 30.0)

    def test_threshold_below_idle_line_valueerror(self):
        """Step 3 rejects a required threshold below the fitted idle line
        with ValueError: the computed relight airspeed is not positive, so
        the relight airspeed is never reached on the survey."""
        with self.assertRaises(ValueError):
            relight.min_relight_airspeed(2.0, 0.15, 3.0)
        with self.assertRaises(ValueError):
            relight.min_relight_airspeed(3.0, 0.15, 3.0)


class TestTimeToIdle(unittest.TestCase):
    """Workflow step 4: summarize the starter-assisted relight samples with
    the mean, the worst sample and the PASS/FAIL verdict against the
    type-data limit."""

    def test_worked_example_time_to_idle_stats(self):
        """Step 4 on the worked example starter-assisted relight samples
        [34.2, 41.7, 38.9, 52.4] returns mean 41.80 s, worst sample 52.40 s,
        limit 60.00 s and verdict PASS within 1e-9 of the real outputs."""
        res = relight.time_to_idle([34.2, 41.7, 38.9, 52.4])
        self.assertAlmostEqual(res["mean_s"], 41.80, places=9)
        self.assertAlmostEqual(res["max_s"], 52.40, places=9)
        self.assertAlmostEqual(res["limit_s"], 60.0, places=9)
        self.assertEqual(res["verdict"], "PASS")

    def test_verdict_tracks_worst_sample_not_mean(self):
        """Step 4 verdict tracks the worst starter-assisted relight sample,
        not the mean: a low mean with one sample over the type-data limit
        still FAILs."""
        res = relight.time_to_idle([10.0, 70.0, 15.0])
        self.assertLess(res["mean_s"], 60.0)
        self.assertEqual(res["verdict"], "FAIL")

    def test_inclusive_limit_boundary_pass_at_60_s(self):
        """Step 4 boundary: a starter-assisted relight sample exactly at the
        60.0 s type-data limit PASSes (the comparison is inclusive)."""
        res = relight.time_to_idle([60.0])
        self.assertAlmostEqual(res["max_s"], 60.0, places=9)
        self.assertEqual(res["verdict"], "PASS")

    def test_fail_above_limit_at_60_1_s(self):
        """Step 4 boundary: a starter-assisted relight sample of 60.1 s,
        just over the 60.0 s type-data limit, FAILs."""
        res = relight.time_to_idle([60.1])
        self.assertEqual(res["verdict"], "FAIL")

    def test_single_sample_mean_equals_worst_sample(self):
        """Step 4 single-sample case: one starter-assisted relight time has
        its mean equal to its worst sample, both below the type-data
        limit."""
        res = relight.time_to_idle([38.5])
        self.assertAlmostEqual(res["mean_s"], 38.5, places=9)
        self.assertAlmostEqual(res["max_s"], 38.5, places=9)
        self.assertEqual(res["verdict"], "PASS")

    def test_empty_sample_list_valueerror(self):
        """Step 4 rejects an empty starter-assisted relight sample list with
        ValueError: no relight was attempted, so no time-to-idle summary
        exists."""
        with self.assertRaises(ValueError):
            relight.time_to_idle([])

    def test_negative_sample_valueerror(self):
        """Step 4 rejects a negative starter-assisted relight time with
        ValueError: a relight time from start to idle cannot be negative."""
        with self.assertRaises(ValueError):
            relight.time_to_idle([-1.0, 40.0])


class TestAltitudeBandVerdict(unittest.TestCase):
    """Workflow step 5: score each altitude band of the demonstration with
    the same time-to-idle check."""

    def test_worked_example_three_bands_pass(self):
        """Step 5 on the worked example demonstration bands scores FL200,
        FL300 and FL410 all PASS with mean 39.83 / 44.83 / 51.57 s and worst
        samples 41.90 / 47.10 / 58.90 s within 1e-9 of the real outputs."""
        bands = {"FL200": [37.4, 40.2, 41.9],
                 "FL300": [42.6, 44.8, 47.1],
                 "FL410": [46.5, 49.3, 58.9]}
        out = relight.altitude_band_verdict(bands)
        self.assertEqual(out["FL200"]["verdict"], "PASS")
        self.assertAlmostEqual(out["FL200"]["mean_s"], 39.8333333333,
                               places=9)
        self.assertAlmostEqual(out["FL200"]["max_s"], 41.90, places=9)
        self.assertEqual(out["FL300"]["verdict"], "PASS")
        self.assertAlmostEqual(out["FL300"]["mean_s"], 44.8333333333,
                               places=9)
        self.assertAlmostEqual(out["FL300"]["max_s"], 47.10, places=9)
        self.assertEqual(out["FL410"]["verdict"], "PASS")
        self.assertAlmostEqual(out["FL410"]["mean_s"], 51.5666666667,
                               places=9)
        self.assertAlmostEqual(out["FL410"]["max_s"], 58.90, places=9)

    def test_band_name_keys_preserved_exactly(self):
        """Step 5 preserves the altitude band name keys exactly: the scored
        result dict carries the same FL200, FL300 and FL410 keys as the
        demonstration input."""
        bands = {"FL200": [37.4], "FL300": [42.6], "FL410": [46.5]}
        out = relight.altitude_band_verdict(bands)
        self.assertEqual(sorted(out.keys()), ["FL200", "FL300", "FL410"])

    def test_failing_band_over_type_data_limit(self):
        """Step 5 flags a band whose worst starter-assisted relight sample
        exceeds the type-data limit: a 62.5 s sample at FL410 gives a FAIL
        band verdict."""
        out = relight.altitude_band_verdict({"FL410": [62.5]})
        self.assertEqual(out["FL410"]["verdict"], "FAIL")

    def test_empty_band_dict_valueerror(self):
        """Step 5 rejects an empty altitude band dict with ValueError: the
        demonstration has no bands to score."""
        with self.assertRaises(ValueError):
            relight.altitude_band_verdict({})

    def test_band_verdicts_replicate_time_to_idle(self):
        """Step 5 identity: the per-band verdict dict replicates the
        time_to_idle summary computed directly on the same starter-assisted
        relight samples of workflow step 4."""
        samples = [34.2, 41.7, 38.9, 52.4]
        band = relight.altitude_band_verdict({"FL200": samples})
        direct = relight.time_to_idle(samples)
        self.assertEqual(band["FL200"], direct)


class TestCombinedVerdict(unittest.TestCase):
    """Workflow step 6: combine the band verdicts with the minimum relight
    airspeed into the overall restart-demonstration verdict."""

    @staticmethod
    def _passing_bands():
        return {"FL200": [37.4, 40.2, 41.9],
                "FL300": [42.6, 44.8, 47.1],
                "FL410": [46.5, 49.3, 58.9]}

    def test_worked_example_combined_pass(self):
        """Step 6 on the worked example bands with the minimum relight
        airspeed of 100.0 m/s returns the overall restart-demonstration
        verdict PASS."""
        bands = relight.altitude_band_verdict(self._passing_bands())
        self.assertEqual(relight.combined_verdict(bands, 100.0), "PASS")

    def test_single_failing_band_fails_combined(self):
        """Step 6 any failing altitude band fails the whole restart
        demonstration regardless of the other bands: PASSing FL200 and
        FL300 bands cannot rescue a FAIL band."""
        verdicts = relight.altitude_band_verdict(self._passing_bands())
        verdicts["FL410"] = relight.time_to_idle([62.5])
        self.assertEqual(relight.combined_verdict(verdicts, 100.0), "FAIL")

    def test_pass_independent_of_airspeed_magnitude(self):
        """Step 6 the combined restart-demonstration verdict is PASS for any
        positive minimum relight airspeed once every band PASSes, at 55.3,
        100.0 and 250.0 m/s alike."""
        bands = relight.altitude_band_verdict(self._passing_bands())
        for airspeed in (55.3, 100.0, 250.0):
            self.assertEqual(relight.combined_verdict(bands, airspeed),
                             "PASS")

    def test_nonpositive_minimum_airspeed_valueerror(self):
        """Step 6 rejects a non-positive minimum relight airspeed with
        ValueError: without a determined relight airspeed the restart
        demonstration cannot be gated."""
        bands = relight.altitude_band_verdict(self._passing_bands())
        for airspeed in (0.0, -100.0):
            with self.assertRaises(ValueError):
                relight.combined_verdict(bands, airspeed)

    def test_empty_band_verdicts_valueerror(self):
        """Step 6 rejects an empty band-verdict dict with ValueError: there
        is nothing to combine into the restart-demonstration verdict."""
        with self.assertRaises(ValueError):
            relight.combined_verdict({}, 100.0)


class TestDeterminism(unittest.TestCase):
    """Workflow step 7: confirm the reduction with the contract test;
    the whole pipeline is deterministic with no randomness anywhere."""

    def test_repeated_calls_deterministic(self):
        """Step 7 repeated calls return byte-identical results: the windmill
        N2 regression dict, the time-to-idle summary and the combined
        restart-demonstration verdict are stable across every run."""
        first = relight.windmill_regression([13.5, 15.75, 18.75, 22.5],
                                            [70.0, 85.0, 105.0, 130.0])
        second = relight.windmill_regression([13.5, 15.75, 18.75, 22.5],
                                             [70.0, 85.0, 105.0, 130.0])
        self.assertEqual(first, second)
        tti1 = relight.time_to_idle([34.2, 41.7, 38.9, 52.4])
        tti2 = relight.time_to_idle([34.2, 41.7, 38.9, 52.4])
        self.assertEqual(tti1, tti2)
        comb1 = relight.combined_verdict(
            relight.altitude_band_verdict(self._passing_bands()), 100.0)
        comb2 = relight.combined_verdict(
            relight.altitude_band_verdict(self._passing_bands()), 100.0)
        self.assertEqual(comb1, comb2)

    @staticmethod
    def _passing_bands():
        return {"FL200": [37.4, 40.2, 41.9],
                "FL300": [42.6, 44.8, 47.1],
                "FL410": [46.5, 49.3, 58.9]}


if __name__ == "__main__":
    unittest.main()

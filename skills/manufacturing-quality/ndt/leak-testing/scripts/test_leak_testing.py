"""Contract test for the leak-testing logic module (stdlib unittest, offline).

Asserts the wave-26 leak-testing spec worked-example anchors:
  - pressure decay 50 L, 0.02 bar, 600 s -> 1.645 scc/s (module 1.644872)
  - gauge resolution time 50 L, 0.001 bar, 0.05 scc/s -> 986.9 s (module 986.923)
  - helium_to_air(1.0) -> 0.3717 scc/s air (module 0.371722, sqrt(4.003/28.97))
  - bubble 3 mm at 1 bubble/s -> 0.01414 scc/s (module 0.014137)
  - method branches: hood at 1e-8, sniffer with localization at 1e-5,
    bubble at 1e-4 with localization and both-side access
  - disposition accept 1.0 vs 2.0 (margin 3.01 dB), reject 3.0 vs 2.0,
    review 2.4 vs 2.0, and the 1.25x review band edges
  - helium mass spectrometer verdict accept for 1e-8 scc/s He vs 1e-8 scc/s air
plus round trips, scaling laws, boundary cases and ValueError rejection of
non-physical inputs. Anchor figures in the spec are quoted to a few decimals;
module values are the exact formula outputs, so tolerances cover the rounding.

Run: cd ~/AeroSkills && python3 skills/manufacturing-quality/ndt/leak-testing/scripts/test_leak_testing.py
"""

import math
import unittest

import leak_testing_logic as lt


class LeakTestingContractTest(unittest.TestCase):
    """Deterministic contract checks for scripts/leak_testing_logic.py."""

    # ------------------------------------------------------------------ #
    # Module constants
    # ------------------------------------------------------------------ #
    def test_module_constants_and_gas_conversion(self):
        self.assertEqual(lt.M_HE, 4.003)
        self.assertEqual(lt.M_AIR, 28.97)
        self.assertEqual(lt.BAR_TO_ATM, 0.986923)
        self.assertEqual(lt.STD_TEMP_K, 293.15)
        self.assertEqual(lt.MS_THRESHOLD, 1e-6)
        self.assertEqual(lt.SNIFFER_THRESHOLD, 1e-5)
        self.assertEqual(lt.BUBBLE_THRESHOLD, 1e-2)
        self.assertEqual(lt.HELIUM_MS_MIN_DETECT_SCCS, 1e-9)
        self.assertEqual(lt.REVIEW_RATIO, 1.25)
        self.assertAlmostEqual(lt.GAS_CONVERSION, math.sqrt(4.003 / 28.97),
                               places=15)

    # ------------------------------------------------------------------ #
    # Pressure and vacuum decay rates
    # ------------------------------------------------------------------ #
    def test_pressure_decay_rate_worked_example(self):
        rate = lt.pressure_decay_rate(50, 0.02, 600)
        # Spec anchor 1.645 scc/s; exact formula 50000 * 0.01973846 / 600.
        self.assertAlmostEqual(rate, 1.645, places=3)
        self.assertAlmostEqual(
            rate, 50 * 1000 * (0.02 * lt.BAR_TO_ATM) / 600, places=12)
        # Standard temperature 293.15 gives no correction.
        self.assertAlmostEqual(rate, lt.pressure_decay_rate(50, 0.02, 600,
                                                            lt.STD_TEMP_K),
                               places=15)

    def test_pressure_decay_rate_temperature_scaling(self):
        rate_hot = lt.pressure_decay_rate(50, 0.02, 600, temp_K=313.15)
        rate_std = lt.pressure_decay_rate(50, 0.02, 600)
        self.assertAlmostEqual(rate_hot, rate_std * (lt.STD_TEMP_K / 313.15),
                               places=12)
        self.assertLess(rate_hot, rate_std)

    def test_pressure_decay_rate_zero_drop(self):
        self.assertEqual(lt.pressure_decay_rate(50, 0.0, 600), 0.0)
        self.assertAlmostEqual(lt.pressure_decay_rate(12.5, 0.05, 300),
                               12.5 * 1000 * (0.05 * lt.BAR_TO_ATM) / 300,
                               places=12)

    def test_vacuum_decay_rate_matches_pressure_decay(self):
        self.assertAlmostEqual(lt.vacuum_decay_rate(50, 0.02, 600),
                               lt.pressure_decay_rate(50, 0.02, 600),
                               places=15)
        self.assertAlmostEqual(lt.vacuum_decay_rate(8.0, 0.01, 120),
                               8.0 * 1000 * (0.01 * lt.BAR_TO_ATM) / 120,
                               places=12)

    # ------------------------------------------------------------------ #
    # Gauge resolution time
    # ------------------------------------------------------------------ #
    def test_gauge_resolution_time_worked_example(self):
        t = lt.gauge_resolution_time(50, 0.001, 0.05)
        # Spec anchor 986.9 s; exact formula 50000 * 0.000986923 / 0.05.
        self.assertAlmostEqual(t, 986.9, places=1)
        self.assertAlmostEqual(
            t, 50 * 1000 * (0.001 * lt.BAR_TO_ATM) / 0.05, places=9)

    def test_gauge_resolution_time_scaling(self):
        t = lt.gauge_resolution_time(50, 0.001, 0.05)
        self.assertAlmostEqual(lt.gauge_resolution_time(50, 0.001, 0.1),
                               t / 2.0, places=9)
        self.assertAlmostEqual(lt.gauge_resolution_time(100, 0.001, 0.05),
                               t * 2.0, places=9)

    def test_gauge_resolution_time_valueerrors(self):
        base = {"volume_L": 50, "gauge_res_bar": 0.001, "target_sccs": 0.05}
        for bad in ({"volume_L": 0}, {"volume_L": -1}, {"gauge_res_bar": 0},
                    {"target_sccs": 0}, {"target_sccs": -0.5},
                    {"temp_K": 0}, {"temp_K": -10}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lt.gauge_resolution_time(**{**base, **bad})

    # ------------------------------------------------------------------ #
    # Helium to air conversion
    # ------------------------------------------------------------------ #
    def test_helium_to_air_worked_example_zero_and_negative(self):
        # Spec anchor 0.3717 scc/s air for 1.0 scc/s He (sqrt(4.003/28.97)).
        self.assertAlmostEqual(lt.helium_to_air(1.0), 0.3717, places=4)
        self.assertAlmostEqual(lt.helium_to_air(1.0), lt.GAS_CONVERSION,
                               places=15)
        self.assertEqual(lt.helium_to_air(0.0), 0.0)
        with self.assertRaises(ValueError):
            lt.helium_to_air(-1.0)

    def test_air_to_helium_inverse(self):
        self.assertAlmostEqual(lt.air_to_helium(1.0), 1.0 / lt.GAS_CONVERSION,
                               places=12)
        self.assertGreater(lt.air_to_helium(1.0), 1.0)
        with self.assertRaises(ValueError):
            lt.air_to_helium(-0.1)

    def test_helium_air_round_trip(self):
        for q_he in (0.05, 1e-7, 3.0, 42.7):
            self.assertAlmostEqual(lt.air_to_helium(lt.helium_to_air(q_he)),
                                   q_he, places=12)

    def test_air_helium_round_trip(self):
        for q_air in (0.02, 5e-8, 1.0, 12.3):
            self.assertAlmostEqual(lt.helium_to_air(lt.air_to_helium(q_air)),
                                   q_air, places=12)

    # ------------------------------------------------------------------ #
    # Bubble leak rate
    # ------------------------------------------------------------------ #
    def test_bubble_leak_rate_worked_example(self):
        rate = lt.bubble_leak_rate(3.0, 1.0)
        # Spec anchor 0.01414 scc/s; per bubble (4/3) pi (0.15 cm)^3.
        self.assertAlmostEqual(rate, 0.01414, places=5)
        self.assertAlmostEqual(rate, (4.0 / 3.0) * math.pi * 0.15 ** 3,
                               places=15)

    def test_bubble_leak_rate_scales_with_count(self):
        self.assertAlmostEqual(lt.bubble_leak_rate(3.0, 2.0),
                               2.0 * lt.bubble_leak_rate(3.0, 1.0), places=15)
        self.assertEqual(lt.bubble_leak_rate(3.0, 0.0), 0.0)
        self.assertEqual(lt.bubble_leak_rate(0.0, 1.0), 0.0)

    def test_bubble_leak_rate_valueerrors(self):
        base = {"bubble_diameter_mm": 2.0, "bubbles_per_s": 1.0}
        for bad in ({"bubble_diameter_mm": -1.0}, {"bubble_diameter_mm": -0.1},
                    {"bubbles_per_s": -1.0}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lt.bubble_leak_rate(**{**base, **bad})

    # ------------------------------------------------------------------ #
    # Method recommendation
    # ------------------------------------------------------------------ #
    def test_method_hood_at_1e_8(self):
        method, _ = lt.method_recommendation(1e-8, True, False, True)
        self.assertEqual(method, "helium-mass-spectrometer-hood")

    def test_method_hood_boundary_ms_threshold(self):
        method, _ = lt.method_recommendation(1e-6, False, False, False)
        self.assertEqual(method, "helium-mass-spectrometer-hood")

    def test_method_sniffer_with_localization(self):
        method, _ = lt.method_recommendation(1e-5, True, True, True)
        self.assertEqual(method, "helium-sniffer")

    def test_method_sniffer_just_above_threshold_falls_to_bubble(self):
        # 2e-5 exceeds the 1e-5 sniffer ceiling, so localization falls to bubble.
        method, _ = lt.method_recommendation(2e-5, True, True, True)
        self.assertEqual(method, "bubble")

    def test_method_bubble_at_1e_4_localized(self):
        method, _ = lt.method_recommendation(1e-4, True, True, True)
        self.assertEqual(method, "bubble")

    def test_method_one_sided_pressure_decay(self):
        method, _ = lt.method_recommendation(1e-3, False, False, True)
        self.assertEqual(method, "pressure-decay")

    def test_method_one_sided_vacuum_decay(self):
        # Documented assumption: one-sided access with a part that cannot take
        # internal pressure selects vacuum decay.
        method, _ = lt.method_recommendation(1e-3, False, False, False)
        self.assertEqual(method, "vacuum-decay")

    def test_method_default_pressure_decay(self):
        method, _ = lt.method_recommendation(1e-1, True, False, True)
        self.assertEqual(method, "pressure-decay")

    def test_method_returns_method_and_rationale(self):
        for args in ((1e-8, True, False, True), (1e-5, True, True, False),
                     (1e-4, True, True, True), (1e-1, False, False, True)):
            with self.subTest(args=args):
                result = lt.method_recommendation(*args)
                self.assertIsInstance(result, tuple)
                self.assertEqual(len(result), 2)
                self.assertIsInstance(result[0], str)
                self.assertIsInstance(result[1], str)
                self.assertIn(result[0], lt.VALID_METHODS)

    def test_method_nonpositive_sensitivity_valueerror(self):
        for bad in (0.0, -1e-8):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lt.method_recommendation(bad, True, False, True)

    # ------------------------------------------------------------------ #
    # Disposition
    # ------------------------------------------------------------------ #
    def test_disposition_accept_worked_example(self):
        outcome = lt.disposition(1.0, 2.0, "pressure-decay")
        self.assertEqual(outcome["verdict"], "accept")
        # Spec anchor margin 3.01 dB = 10 log10(2/1).
        self.assertAlmostEqual(outcome["margin_db"], 3.01, places=2)
        # Measured exactly at the allowable is still accept with zero margin.
        at_limit = lt.disposition(2.0, 2.0, "pressure-decay")
        self.assertEqual(at_limit["verdict"], "accept")
        self.assertAlmostEqual(at_limit["margin_db"], 0.0, places=12)

    def test_disposition_reject_worked_example(self):
        outcome = lt.disposition(3.0, 2.0, "pressure-decay")
        self.assertEqual(outcome["verdict"], "reject")
        self.assertLess(outcome["margin_db"], 0.0)

    def test_disposition_review_band(self):
        # 2.4 vs 2.0 is ratio 1.2, inside the (1, 1.25] review band.
        outcome = lt.disposition(2.4, 2.0, "pressure-decay")
        self.assertEqual(outcome["verdict"], "review")
        self.assertAlmostEqual(outcome["margin_db"], -0.792, places=2)

    def test_disposition_review_upper_boundary_and_reject_above(self):
        # Ratio exactly 1.25 stays review; anything above it rejects.
        self.assertEqual(lt.disposition(2.5, 2.0, "pressure-decay")["verdict"],
                         "review")
        self.assertEqual(lt.disposition(2.5001, 2.0, "pressure-decay")["verdict"],
                         "reject")

    def test_disposition_valueerrors(self):
        base = {"measured_sccs": 1.0, "max_allowable_sccs": 2.0,
                "method": "pressure-decay"}
        for bad in ({"max_allowable_sccs": 0}, {"max_allowable_sccs": -2.0},
                    {"measured_sccs": -1.0}, {"method": "unknown-method"}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    lt.disposition(**{**base, **bad})

    # ------------------------------------------------------------------ #
    # Helium mass spectrometer verdict
    # ------------------------------------------------------------------ #
    def test_helium_ms_verdict_accept(self):
        # 1e-8 scc/s He converts to 3.717e-9 scc/s air, below the 1e-8 limit.
        outcome = lt.helium_ms_verdict(1e-8, 1e-8)
        self.assertEqual(outcome["verdict"], "accept")
        self.assertGreater(outcome["margin_db"], 0.0)

    def test_helium_ms_verdict_reject_and_manual_identity(self):
        outcome = lt.helium_ms_verdict(1e-8, 1e-9)
        self.assertEqual(outcome["verdict"], "reject")
        manual = lt.disposition(lt.helium_to_air(1e-8), 1e-9,
                                "helium-mass-spectrometer-hood")
        self.assertEqual(outcome, manual)

    # ------------------------------------------------------------------ #
    # Summarize and decay ValueError rejection
    # ------------------------------------------------------------------ #
    def test_summarize_worked_example(self):
        summary = lt.summarize(50, 0.02, 600, 2.0)
        self.assertAlmostEqual(summary["leak_rate_sccs"], 1.645, places=3)
        self.assertEqual(summary["method"], "pressure-decay")
        self.assertEqual(summary["verdict"], "accept")
        self.assertAlmostEqual(summary["margin_db"], 0.849, places=2)

    def test_decay_valueerrors_volume_time_temp_dp(self):
        for fn, vol_key in ((lt.pressure_decay_rate, "volume_L"),
                            (lt.vacuum_decay_rate, "chamber_volume_L")):
            base = {vol_key: 50, "dP_bar": 0.02, "time_s": 600,
                    "temp_K": lt.STD_TEMP_K}
            bads = ({vol_key: 0}, {vol_key: -1}, {"time_s": 0},
                    {"time_s": -5}, {"temp_K": 0}, {"temp_K": -10},
                    {"dP_bar": -0.02})
            for bad in bads:
                with self.subTest(fn=fn.__name__, bad=bad):
                    with self.assertRaises(ValueError):
                        fn(**{**base, **bad})


if __name__ == "__main__":
    unittest.main()

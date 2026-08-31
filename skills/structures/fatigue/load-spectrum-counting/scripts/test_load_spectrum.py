#!/usr/bin/env python3
"""Gate 3 contract test: fatigue load spectrum counting.

Exercises scripts/load_spectrum_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - rainflow cycle counting,
exceedance and level-crossing spectra, mission spectrum assembly,
spectrum truncation, Basquin S-N lives, and Miner spectrum damage;
invalid inputs raise ValueError. Rainflow numeric values follow the
ASTM E1049-85 section 5.4.4 counting practice.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import load_spectrum_logic as ls  # noqa: E402


class TurningPointsTest(unittest.TestCase):
    def test_keeps_extrema(self):
        self.assertEqual(ls.turning_points([0, 4, 1, 5, 2, 6, 3]),
                         [0, 4, 1, 5, 2, 6, 3])

    def test_collapses_monotonic_runs(self):
        self.assertEqual(ls.turning_points([0, 5, 5, 5, 1]), [0, 5, 1])
        self.assertEqual(ls.turning_points([2, 1, 0, -1, 3]), [2, -1, 3])

    def test_short_histories(self):
        self.assertEqual(ls.turning_points([]), [])
        self.assertEqual(ls.turning_points([7]), [7])


class RainflowTest(unittest.TestCase):
    def test_repeated_full_cycles(self):
        # [0,10,0,10,0]: two identical excursions, four half cycles.
        cycles = ls.rainflow_cycles([0, 10, 0, 10, 0])
        self.assertEqual(cycles, [(10.0, 5.0, 0.5)] * 4)

    def test_nested_cycles_spectrum(self):
        # [0,10,0,8,0,6,0]: one full cycle each at ranges 6 and 8,
        # the range-10 excursion splits into two half cycles.
        cycles = ls.rainflow_cycles([0, 10, 0, 8, 0, 6, 0])
        self.assertEqual(sorted(cycles), [(6.0, 3.0, 1.0), (8.0, 4.0, 1.0),
                                          (10.0, 5.0, 0.5), (10.0, 5.0, 0.5)])

    def test_open_history_mixed(self):
        # Full cycles: 4->1 and 5->2 (range 3); residual halves at
        # ranges 6 and 3, per the ASTM three-point counting rule.
        cycles = ls.rainflow_cycles([0, 4, 1, 5, 2, 6, 3])
        self.assertEqual(sorted(cycles), [(3.0, 2.5, 1.0), (3.0, 3.5, 1.0),
                                          (3.0, 4.5, 0.5), (6.0, 3.0, 0.5)])

    def test_spectrum_merges_half_cycles(self):
        self.assertEqual(ls.rainflow_spectrum([0, 10, 0, 10, 0]), {10.0: 2.0})
        self.assertEqual(ls.rainflow_spectrum([0, 10, 0, 8, 0, 6, 0]),
                         {10.0: 1.0, 8.0: 1.0, 6.0: 1.0})
        self.assertEqual(ls.rainflow_spectrum([0, 4, 1, 5, 2, 6, 3]),
                         {3.0: 2.5, 6.0: 0.5})

    def test_empty_history(self):
        self.assertEqual(ls.rainflow_cycles([]), [])
        self.assertEqual(ls.rainflow_spectrum([]), {})


class ExceedanceTest(unittest.TestCase):
    PEAKS = [5, 3, 8, 3, 5, 8, 2]

    def test_exceedance_counts(self):
        self.assertEqual(
            ls.exceedance_counts(self.PEAKS, [9, 8, 5, 3, 2]), [0, 2, 4, 6, 7]
        )

    def test_level_equal_counts_as_exceeded(self):
        self.assertEqual(ls.exceedance_counts([5, 3], [5]), [1])


class LevelCrossingTest(unittest.TestCase):
    HISTORY = [0, 4, 1, 5, 2, 6, 3]

    def test_upcrossings(self):
        self.assertEqual(ls.upcrossing_count(self.HISTORY, 2.5), 3)
        self.assertEqual(ls.upcrossing_count(self.HISTORY, 0.5), 1)
        self.assertEqual(ls.upcrossing_count(self.HISTORY, 6.5), 0)

    def test_empty_history(self):
        self.assertEqual(ls.upcrossing_count([], 2.0), 0)


class MissionSpectrumTest(unittest.TestCase):
    def test_aggregation_sums_repeated_levels(self):
        phases = [(3, 5), (5, 2), (4, 10), (5, 3), (8, 1)]
        self.assertEqual(ls.mission_spectrum(phases),
                         {3: 5, 5: 5, 4: 10, 8: 1})

    def test_truncation(self):
        spec = {8: 1, 5: 5, 4: 10, 3: 5}
        self.assertEqual(ls.truncate_spectrum(spec, 4), {8: 1, 5: 5, 4: 10})
        self.assertEqual(ls.truncate_spectrum(spec, 5), {8: 1, 5: 5})
        self.assertEqual(ls.truncate_spectrum(spec, 0), spec)


class DamageTest(unittest.TestCase):
    def test_basquin_life(self):
        # N = 2e10 * S_a**-3: 100 -> 2e4, 200 -> 2500.
        self.assertAlmostEqual(ls.basquin_life(100.0), 2.0e4)
        self.assertAlmostEqual(ls.basquin_life(200.0), 2500.0)

    def test_spectrum_damage_half_life_blocks(self):
        # 1e4 cycles at S_a=100 (N=2e4) plus 1250 at S_a=200 (N=2500):
        # damage 0.5 + 0.5 = 1.0, the Miner life limit.
        self.assertAlmostEqual(
            ls.spectrum_damage([(100.0, 10000), (200.0, 1250)]), 1.0
        )

    def test_spectrum_damage_partial(self):
        self.assertAlmostEqual(ls.spectrum_damage([(100.0, 5000)]), 0.25)

    def test_mission_to_damage_chain(self):
        # Taxi 5 at S_a=20, climb 3 at 100, cruise 10 at 60, descent 2
        # at 100, landing 1 at 200. Truncate below 60, then damage:
        # 5/2e4 + 10/92592.6 + 1/2500 = 0.000758.
        spec = ls.mission_spectrum([(20, 5), (100, 3), (60, 10), (100, 2), (200, 1)])
        spec = ls.truncate_spectrum(spec, 60)
        blocks = [(level, cycles) for level, cycles in sorted(spec.items())]
        self.assertAlmostEqual(ls.spectrum_damage(blocks), 0.000758, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ls.basquin_life(0.0)
        with self.assertRaises(ValueError):
            ls.basquin_life(-5.0)
        with self.assertRaises(ValueError):
            ls.spectrum_damage([(100.0, -1)])


if __name__ == "__main__":
    unittest.main(verbosity=2)

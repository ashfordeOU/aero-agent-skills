#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft mission delta-v budget.

Exercises scripts/mission_delta_v_budget_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (delta-v summation
with margin allocation, Tsiolkovsky delta-v from mass ratio, propellant
and wet mass from delta-v, dry mass, and specific impulse, the
MissionDeltaVBudget class; invalid inputs raise ValueError).

Anchors (hand-computed, g0 = 9.80665 m/s^2):
- tsiolkovsky_delta_v(e, 300) = 2941.995 m/s exactly (Isp * g0 * ln(e))
- propellant_mass(2941.995, 1000, 300) = 1718.2818 kg (mass ratio e,
  so the propellant is m_dry * (e - 1))
- wet_mass(2941.995, 1000, 300) = 2718.2818 kg; propellant fraction
  0.63212 (the classic e/(e-1) limit case)
- sum_delta_v([1500, 2500, 1000, 500]) = 5500 m/s;
  apply_margin(5500, 0.15) = 6325 m/s
- MissionDeltaVBudget([1200, 1800, 600, 400], margin 0.10, dry 800 kg,
  isp 320 s): nominal 4000 m/s, budgeted 4400 m/s, mass ratio
  exp(4400 / 3138.128) = 4.06376, propellant 2451.0117 kg, wet
  3251.0117 kg, propellant fraction 0.75392
- zero delta-v: mass ratio 1, propellant 0, wet mass equals dry mass
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mission_delta_v_budget_logic as mdb  # noqa: E402

G0 = 9.80665
# Tsiolkovsky anchors: mass ratio e with 300 s Isp.
DV_E = 300.0 * G0  # 2941.995 m/s exactly
DRY = 1000.0  # kg


class TsiolkovskyDeltaVTest(unittest.TestCase):
    def test_anchor_mass_ratio_e(self):
        # ln(e) = 1, so dv = Isp * g0 * 1 = 2941.995 exactly.
        self.assertAlmostEqual(mdb.tsiolkovsky_delta_v(math.e, 300.0), 2941.995, places=3)

    def test_scales_with_isp(self):
        dv = mdb.tsiolkovsky_delta_v(math.e, 300.0)
        self.assertAlmostEqual(mdb.tsiolkovsky_delta_v(math.e, 600.0), 2 * dv, places=3)

    def test_zero_delta_v_at_mass_ratio_one(self):
        self.assertEqual(mdb.tsiolkovsky_delta_v(1.0, 300.0), 0.0)

    def test_higher_mass_ratio_more_delta_v(self):
        self.assertGreater(
            mdb.tsiolkovsky_delta_v(math.e**2, 300.0),
            mdb.tsiolkovsky_delta_v(math.e, 300.0),
        )

    def test_anchor_known_mass_ratio(self):
        # Mass ratio 10 at 250 s: 250 * 9.80665 * ln(10).
        self.assertAlmostEqual(
            mdb.tsiolkovsky_delta_v(10.0, 250.0), 250.0 * G0 * math.log(10.0), places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdb.tsiolkovsky_delta_v(0.5, 300.0)
        with self.assertRaises(ValueError):
            mdb.tsiolkovsky_delta_v(math.e, 0.0)
        with self.assertRaises(ValueError):
            mdb.tsiolkovsky_delta_v(math.e, 300.0, g0=0.0)


class PropellantMassTest(unittest.TestCase):
    def test_anchor_mass_ratio_e(self):
        # dv = Isp*g0, so m_prop = m_dry * (e - 1) = 1718.2818 kg.
        self.assertAlmostEqual(
            mdb.propellant_mass(DV_E, DRY, 300.0), 1718.281828, places=3
        )

    def test_wet_mass_anchor(self):
        self.assertAlmostEqual(mdb.wet_mass(DV_E, DRY, 300.0), 2718.281828, places=3)

    def test_wet_is_dry_plus_propellant(self):
        prop = mdb.propellant_mass(DV_E, DRY, 300.0)
        self.assertAlmostEqual(mdb.wet_mass(DV_E, DRY, 300.0), DRY + prop, places=3)

    def test_zero_delta_v_edge(self):
        self.assertEqual(mdb.propellant_mass(0.0, DRY, 300.0), 0.0)
        self.assertEqual(mdb.wet_mass(0.0, DRY, 300.0), DRY)

    def test_dry_mass_scaling(self):
        # Doubling the dry mass doubles the propellant mass.
        prop1 = mdb.propellant_mass(DV_E, DRY, 300.0)
        prop2 = mdb.propellant_mass(DV_E, 2 * DRY, 300.0)
        self.assertAlmostEqual(prop2, 2 * prop1, places=3)

    def test_higher_isp_needs_less_propellant(self):
        self.assertLess(
            mdb.propellant_mass(DV_E, DRY, 450.0), mdb.propellant_mass(DV_E, DRY, 300.0)
        )

    def test_mass_ratio_roundtrip(self):
        # Inverting the propellant mass recovers the budgeted delta-v.
        prop = mdb.propellant_mass(DV_E, DRY, 300.0)
        wet = DRY + prop
        self.assertAlmostEqual(
            mdb.tsiolkovsky_delta_v(wet / DRY, 300.0), DV_E, places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdb.propellant_mass(-1.0, DRY, 300.0)
        with self.assertRaises(ValueError):
            mdb.propellant_mass(DV_E, 0.0, 300.0)
        with self.assertRaises(ValueError):
            mdb.propellant_mass(DV_E, DRY, -300.0)
        with self.assertRaises(ValueError):
            mdb.wet_mass(DV_E, DRY, 0.0)


class DeltaVSumTest(unittest.TestCase):
    def test_anchor_sum(self):
        self.assertAlmostEqual(
            mdb.sum_delta_v([1500.0, 2500.0, 1000.0, 500.0]), 5500.0, places=3
        )

    def test_anchor_margin(self):
        self.assertAlmostEqual(mdb.apply_margin(5500.0, 0.15), 6325.0, places=3)

    def test_zero_margin_unchanged(self):
        self.assertAlmostEqual(mdb.apply_margin(5500.0, 0.0), 5500.0, places=3)

    def test_empty_contributions(self):
        self.assertEqual(mdb.sum_delta_v([]), 0.0)

    def test_single_contribution(self):
        self.assertAlmostEqual(mdb.sum_delta_v([1200.0]), 1200.0, places=3)

    def test_contributions_never_subtract(self):
        # All contributions are positive magnitudes; the total is the sum.
        self.assertAlmostEqual(
            mdb.sum_delta_v([1500.0, 2500.0, 1000.0, 500.0]),
            sum([1500.0, 2500.0, 1000.0, 500.0]),
            places=3,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdb.sum_delta_v([100.0, -50.0])
        with self.assertRaises(ValueError):
            mdb.apply_margin(-1.0, 0.1)
        with self.assertRaises(ValueError):
            mdb.apply_margin(1000.0, -0.1)


class MissionDeltaVBudgetTest(unittest.TestCase):
    def test_anchor_scenario(self):
        # [1200, 1800, 600, 400] = 4000 m/s, margin 0.10 -> 4400 m/s;
        # dry 800 kg, isp 320 s: mass ratio exp(4400/3138.128) = 4.06376.
        b = mdb.MissionDeltaVBudget(
            [1200.0, 1800.0, 600.0, 400.0],
            margin_fraction=0.10,
            dry_mass=800.0,
            isp=320.0,
        )
        self.assertAlmostEqual(b.total_delta_v(), 4000.0, places=3)
        self.assertAlmostEqual(b.budgeted_delta_v(), 4400.0, places=3)
        self.assertAlmostEqual(b.propellant_mass(), 2451.011704, places=3)
        self.assertAlmostEqual(b.wet_mass(), 3251.011704, places=3)
        self.assertAlmostEqual(b.propellant_fraction(), 0.753923, places=3)

    def test_zero_delta_v_budget(self):
        b = mdb.MissionDeltaVBudget([0.0], margin_fraction=0.10, dry_mass=500.0, isp=300.0)
        self.assertEqual(b.total_delta_v(), 0.0)
        self.assertEqual(b.propellant_mass(), 0.0)
        self.assertEqual(b.wet_mass(), 500.0)

    def test_fits_verdict(self):
        b = mdb.MissionDeltaVBudget(
            [1500.0, 2500.0, 1000.0, 500.0],
            margin_fraction=0.10,
            dry_mass=1500.0,
            isp=310.0,
        )
        self.assertFalse(b.fits(5500.0))  # budgeted ~6050 > 5500 available
        self.assertFalse(b.fits(6049.0))  # capability just below the budget
        self.assertTrue(b.fits(6100.0))  # capability above the budget
        self.assertTrue(b.fits(7000.0))  # capability well above the budget

    def test_propellant_sizing_requires_isp_and_dry_mass(self):
        b = mdb.MissionDeltaVBudget([4000.0], margin_fraction=0.10)
        self.assertAlmostEqual(b.budgeted_delta_v(), 4400.0, places=3)
        with self.assertRaises(ValueError):
            b.propellant_mass()
        with self.assertRaises(ValueError):
            b.wet_mass()

    def test_report_fields(self):
        b = mdb.MissionDeltaVBudget(
            [1200.0, 1800.0, 600.0, 400.0],
            margin_fraction=0.10,
            dry_mass=800.0,
            isp=320.0,
        )
        r = b.report()
        self.assertAlmostEqual(r["total_delta_v_m_s"], 4000.0, places=3)
        self.assertAlmostEqual(r["budgeted_delta_v_m_s"], 4400.0, places=3)
        self.assertAlmostEqual(r["propellant_mass_kg"], 2451.011704, places=3)
        self.assertEqual(r["dry_mass_kg"], 800.0)
        self.assertEqual(r["isp_s"], 320.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdb.MissionDeltaVBudget([100.0, -50.0])
        with self.assertRaises(ValueError):
            mdb.MissionDeltaVBudget([1000.0], margin_fraction=-0.1)
        with self.assertRaises(ValueError):
            mdb.MissionDeltaVBudget([1000.0], dry_mass=0.0)
        with self.assertRaises(ValueError):
            mdb.MissionDeltaVBudget([1000.0], dry_mass=500.0, isp=0.0)


class WorkedExampleTest(unittest.TestCase):
    def test_leo_mission_budget_scenario(self):
        # LEO insertion 1600, LEO-GEO transfer 3816, station keeping 50,
        # deorbit 150 m/s: nominal 5616 m/s, 10 percent margin -> 6177.6;
        # dry 1500 kg, isp 310 s (bipropellant class).
        b = mdb.MissionDeltaVBudget(
            [1600.0, 3816.0, 50.0, 150.0],
            margin_fraction=0.10,
            dry_mass=1500.0,
            isp=310.0,
        )
        self.assertAlmostEqual(b.total_delta_v(), 5616.0, places=3)
        self.assertAlmostEqual(b.budgeted_delta_v(), 6177.6, places=3)
        self.assertAlmostEqual(b.propellant_mass(), 9944.728856, places=3)
        self.assertAlmostEqual(b.wet_mass(), 11444.728856, places=3)

    def test_deorbit_only_budget(self):
        # A deorbit-only budget at 150 m/s with margin 0.05.
        b = mdb.MissionDeltaVBudget(
            [150.0], margin_fraction=0.05, dry_mass=300.0, isp=300.0
        )
        self.assertAlmostEqual(b.budgeted_delta_v(), 157.5, places=3)
        self.assertLess(b.propellant_mass(), 20.0)  # small disposal burn


if __name__ == "__main__":
    unittest.main(verbosity=2)

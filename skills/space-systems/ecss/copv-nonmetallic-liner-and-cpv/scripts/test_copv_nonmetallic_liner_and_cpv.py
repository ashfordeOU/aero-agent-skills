#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.3.4 COPV non-metallic liner
and all-composite CPV structural assessment.

Exercises scripts/copv_nonmetallic_liner_and_cpv_logic.py (stdlib unittest,
offline). Contract: a vessel with a homogeneous non-metallic liner is
categorized as COPV, an all-composite vessel as CPV, and an unrecognized
liner type raises; the sustained stress ratio is the ratio of operating fiber
stress to mean fiber strength with non-positive inputs raising; the
power-law stress rupture life grows as SSR decreases, SSR outside (0,1]
raises; damage fractions from each phase sum via the Miner-rule analogue and
the total is checked against the allowable limit; liner hoop stress follows
the thin-wall formula and missing liner parameters or exceeded allowable are
flagged; VDT projects flaw growth linearly and flags when end-of-life flaw
reaches the critical size, with initial flaw below the NDT threshold raising;
and the full vessel review is compliant only when all categories are clear.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import copv_nonmetallic_liner_and_cpv_logic as cv  # noqa: E402


class CategorizeVesselTest(unittest.TestCase):
    def test_nonmetallic_homogeneous_is_copv(self):
        self.assertEqual(cv.categorize_vessel("nonmetallic_homogeneous"), "copv")

    def test_all_composite_is_cpv(self):
        self.assertEqual(cv.categorize_vessel("all_composite"), "cpv")

    def test_unknown_liner_type_raises(self):
        with self.assertRaises(ValueError):
            cv.categorize_vessel("metallic_titanium")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            cv.categorize_vessel("")


class SustainedStressRatioTest(unittest.TestCase):
    def test_half_mean_strength_gives_point_five(self):
        self.assertAlmostEqual(cv.sustained_stress_ratio(100.0, 200.0), 0.5)

    def test_equal_stress_and_strength_gives_one(self):
        self.assertAlmostEqual(cv.sustained_stress_ratio(500.0, 500.0), 1.0)

    def test_zero_operating_stress_raises(self):
        with self.assertRaises(ValueError):
            cv.sustained_stress_ratio(0.0, 500.0)

    def test_zero_mean_strength_raises(self):
        with self.assertRaises(ValueError):
            cv.sustained_stress_ratio(100.0, 0.0)


class StressRuptureLifeTest(unittest.TestCase):
    def test_ssr_at_one_returns_reference_life(self):
        self.assertAlmostEqual(cv.stress_rupture_life(1.0, 3600.0), 3600.0)

    def test_lower_ssr_gives_longer_life(self):
        life_high = cv.stress_rupture_life(0.8, 1.0)
        life_low = cv.stress_rupture_life(0.5, 1.0)
        self.assertGreater(life_low, life_high)

    def test_power_law_formula(self):
        # t = ref * (1/ssr)^exp => 1.0 * (1/0.5)^50 = 2^50
        expected = 2.0 ** 50
        self.assertAlmostEqual(cv.stress_rupture_life(0.5, 1.0, 50.0), expected)

    def test_ssr_above_one_raises(self):
        with self.assertRaises(ValueError):
            cv.stress_rupture_life(1.01, 1000.0)

    def test_ssr_zero_raises(self):
        with self.assertRaises(ValueError):
            cv.stress_rupture_life(0.0, 1000.0)

    def test_negative_reference_life_raises(self):
        with self.assertRaises(ValueError):
            cv.stress_rupture_life(0.5, -1.0)


class StressRuptureDamageTest(unittest.TestCase):
    def _case(self, ssr, duration_s, reference_life_s=1.0, exponent=1.0):
        return {
            "ssr": ssr,
            "duration_s": duration_s,
            "reference_life_s": reference_life_s,
            "exponent": exponent,
        }

    def test_single_phase_at_ssr_one(self):
        # exponent=1: t_rupt = 1.0*(1/1.0)^1 = 1.0; damage = 500/1.0 = 500
        cases = [self._case(1.0, 500.0)]
        self.assertAlmostEqual(cv.stress_rupture_damage(cases), 500.0)

    def test_empty_load_cases_gives_zero_damage(self):
        self.assertAlmostEqual(cv.stress_rupture_damage([]), 0.0)

    def test_multiple_phases_sum_correctly(self):
        # phase 1: ssr=1.0, exponent=1 => t_rupt=1; dmg=100/1=100
        # phase 2: ssr=0.5, exponent=1 => t_rupt=1*(1/0.5)^1=2; dmg=200/2=100
        # total = 200
        cases = [
            self._case(1.0, 100.0),
            self._case(0.5, 200.0),
        ]
        self.assertAlmostEqual(cv.stress_rupture_damage(cases), 200.0)

    def test_zero_duration_contributes_no_damage(self):
        cases = [self._case(0.8, 0.0)]
        self.assertAlmostEqual(cv.stress_rupture_damage(cases), 0.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            cv.stress_rupture_damage([self._case(0.8, -1.0)])


class LinerHoopStressTest(unittest.TestCase):
    def test_thin_wall_formula(self):
        # sigma = p * r / (2*t) = 2.0 * 150.0 / (2 * 3.0) = 50.0
        self.assertAlmostEqual(cv.liner_hoop_stress(2.0, 150.0, 3.0), 50.0)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            cv.liner_hoop_stress(0.0, 100.0, 5.0)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            cv.liner_hoop_stress(2.0, 100.0, 0.0)


class LinerIntegrityViolationsTest(unittest.TestCase):
    def _vessel(self, p=2.0, r=100.0, t=5.0, allowable=50.0):
        return {
            "liner_pressure": p,
            "liner_radius": r,
            "liner_thickness": t,
            "allowable_liner_stress": allowable,
        }

    def test_stress_within_allowable_no_violation(self):
        # sigma = 2.0 * 100.0 / (2 * 5.0) = 20.0; allowable = 50.0
        self.assertEqual(cv.liner_integrity_violations("tank-1", self._vessel()), [])

    def test_stress_exceeds_allowable_flagged(self):
        # sigma = 2.0 * 100.0 / (2 * 5.0) = 20.0; allowable = 10.0
        violations = cv.liner_integrity_violations("tank-1", self._vessel(allowable=10.0))
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "liner_stress_exceeded")
        self.assertAlmostEqual(violations[0]["hoop_stress"], 20.0)

    def test_missing_allowable_flagged(self):
        violations = cv.liner_integrity_violations("tank-1", self._vessel(allowable=None))
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_liner_parameters")

    def test_missing_pressure_flagged(self):
        v = self._vessel()
        v["liner_pressure"] = None
        violations = cv.liner_integrity_violations("tank-1", v)
        self.assertEqual(violations[0]["issue"], "missing_liner_parameters")
        self.assertIn("liner_pressure", violations[0]["missing"])


class VdtComplianceTest(unittest.TestCase):
    def test_compliant_with_positive_margin(self):
        # initial=1.0, ndt=1.0, critical=10.0, growth=0.1/cycle, 20 cycles
        # final = 1.0 + 0.1*20 = 3.0 < 10.0 => compliant
        result = cv.vdt_compliance("tank-1", 1.0, 1.0, 10.0, 0.1, 20)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["final_flaw_mm"], 3.0)
        self.assertAlmostEqual(result["margin"], 0.7)

    def test_flaw_reaches_critical_fails(self):
        # initial=5.0, ndt=1.0, critical=10.0, growth=1.0/cycle, 10 cycles
        # final = 5.0 + 1.0*10 = 15.0 >= 10.0 => non-compliant
        result = cv.vdt_compliance("tank-1", 5.0, 1.0, 10.0, 1.0, 10)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["issue"], "flaw_reaches_critical_size")

    def test_zero_growth_always_compliant(self):
        result = cv.vdt_compliance("tank-1", 2.0, 1.0, 20.0, 0.0, 1000)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["final_flaw_mm"], 2.0)

    def test_initial_below_ndt_threshold_raises(self):
        with self.assertRaises(ValueError):
            cv.vdt_compliance("tank-1", 0.5, 1.0, 10.0, 0.1, 20)

    def test_critical_not_greater_than_initial_raises(self):
        with self.assertRaises(ValueError):
            cv.vdt_compliance("tank-1", 5.0, 1.0, 5.0, 0.0, 10)

    def test_negative_service_cycles_raises(self):
        with self.assertRaises(ValueError):
            cv.vdt_compliance("tank-1", 1.0, 1.0, 10.0, 0.1, -1)


class CopvReviewTest(unittest.TestCase):
    def _compliant_copv(self):
        return {
            "vessel_id": "copv-alpha",
            "liner_type": "nonmetallic_homogeneous",
            "load_cases": [
                {
                    "ssr": 1.0,
                    "duration_s": 0.0,
                    "reference_life_s": 1.0,
                    "exponent": 50.0,
                }
            ],
            "stress_rupture_limit": 1.0,
            "liner_pressure": 2.0,
            "liner_radius": 100.0,
            "liner_thickness": 5.0,
            "allowable_liner_stress": 50.0,
            "vdt": {
                "initial_flaw_mm": 1.0,
                "ndt_threshold_mm": 1.0,
                "critical_flaw_mm": 10.0,
                "growth_per_cycle_mm": 0.05,
                "service_cycles": 100,
            },
        }

    def _compliant_cpv(self):
        return {
            "vessel_id": "cpv-beta",
            "liner_type": "all_composite",
            "load_cases": [],
            "stress_rupture_limit": 1.0,
            "vdt": {
                "initial_flaw_mm": 2.0,
                "ndt_threshold_mm": 1.0,
                "critical_flaw_mm": 20.0,
                "growth_per_cycle_mm": 0.01,
                "service_cycles": 500,
            },
        }

    def test_compliant_copv_no_violations(self):
        review = cv.copv_review(self._compliant_copv())
        self.assertEqual(review["vessel_category"], "copv")
        self.assertEqual(review["stress_rupture"], [])
        self.assertEqual(review["liner_integrity"], [])
        self.assertTrue(review["vdt"]["compliant"])
        self.assertTrue(cv.is_vessel_compliant(review))

    def test_compliant_cpv_no_liner_check(self):
        review = cv.copv_review(self._compliant_cpv())
        self.assertEqual(review["vessel_category"], "cpv")
        self.assertEqual(review["liner_integrity"], [])

    def test_stress_rupture_violation_flagged(self):
        vessel = self._compliant_copv()
        # Large damage: ssr=1.0, duration > reference_life at exponent=1
        vessel["load_cases"] = [
            {"ssr": 1.0, "duration_s": 2.0, "reference_life_s": 1.0, "exponent": 1.0}
        ]
        vessel["stress_rupture_limit"] = 1.0
        review = cv.copv_review(vessel)
        self.assertEqual(len(review["stress_rupture"]), 1)
        self.assertEqual(review["stress_rupture"][0]["issue"], "stress_rupture_limit_exceeded")
        self.assertFalse(cv.is_vessel_compliant(review))

    def test_liner_violation_makes_copv_noncompliant(self):
        vessel = self._compliant_copv()
        vessel["allowable_liner_stress"] = 1.0  # far below hoop stress of 20 MPa
        review = cv.copv_review(vessel)
        self.assertEqual(review["liner_integrity"][0]["issue"], "liner_stress_exceeded")
        self.assertFalse(cv.is_vessel_compliant(review))

    def test_vdt_violation_makes_vessel_noncompliant(self):
        vessel = self._compliant_copv()
        vessel["vdt"]["growth_per_cycle_mm"] = 2.0  # will exceed critical flaw
        vessel["vdt"]["service_cycles"] = 10
        vessel["vdt"]["critical_flaw_mm"] = 10.0
        vessel["vdt"]["initial_flaw_mm"] = 1.0
        review = cv.copv_review(vessel)
        self.assertFalse(review["vdt"]["compliant"])
        self.assertFalse(cv.is_vessel_compliant(review))

    def test_no_vdt_params_leaves_vdt_none(self):
        vessel = self._compliant_copv()
        vessel["vdt"] = None
        review = cv.copv_review(vessel)
        self.assertIsNone(review["vdt"])
        self.assertTrue(cv.is_vessel_compliant(review))

    def test_unknown_liner_type_raises(self):
        vessel = self._compliant_copv()
        vessel["liner_type"] = "ceramic_composite"
        with self.assertRaises(ValueError):
            cv.copv_review(vessel)


if __name__ == "__main__":
    unittest.main(verbosity=2)

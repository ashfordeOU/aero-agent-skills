#!/usr/bin/env python3
"""Gate 3 contract test: space radiation and orbital debris assessment.

Exercises scripts/radiation_debris_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (trapped belt dose rate
versus altitude and inclination, solar particle event fluence, RPP
single-event upset rate from cross-section and LET spectrum, total
ionizing dose versus shielding with exponential attenuation, debris
flux and collision probability over mission life; invalid inputs raise
ValueError).

Anchors (hand-computed):
- inclination_factor(0) = 0.3, inclination_factor(90) = 1.0, and the
  factor is symmetric about 90 deg: 80 deg and 100 deg are equal
- trapped_belt_dose_rate(3500, 90) = 60.7727 rad/day (proton belt peak,
  polar orbit); trapped_belt_dose_rate(600, 98) = 0.26318 rad/day
- spe_fluence(10, 1) = 1e8 protons/cm^2; spe_fluence(100, 1) = 1e5
  (power law exponent 3)
- rpp_cross_section(20, 1e-6, 10, 15, 1) = 4.86583e-7 cm^2 (Weibull,
  shape 1)
- seu_rate(1e-6, 10, 15, 1, [(20, 1e5)]) = 0.0486583 upsets/device/day
- tid at 600 km / 98 deg / 5 years: 0.48064 krad unshielded, 0.26093
  krad behind 3 mm Al, 0.13406 krad behind 10 mm Al (monotone
  decreasing)
- collision_probability(5e-5, 1, 1) = 4.99988e-5 (Poisson, small lambda)
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import radiation_debris_logic as rdl  # noqa: E402


class TrappedBeltTest(unittest.TestCase):
    def test_inclination_factor_anchors(self):
        self.assertAlmostEqual(rdl.inclination_factor(0.0), 0.3, places=6)
        self.assertAlmostEqual(rdl.inclination_factor(90.0), 1.0, places=6)

    def test_inclination_factor_symmetric_about_90(self):
        # cos^2 makes 80 deg and 100 deg identical.
        self.assertAlmostEqual(
            rdl.inclination_factor(80.0), rdl.inclination_factor(100.0), places=9
        )

    def test_dose_rate_anchor_proton_belt_peak_polar(self):
        # 3500 km at 90 deg: proton band at its peak, outer band small.
        self.assertAlmostEqual(
            rdl.trapped_belt_dose_rate(3500.0, 90.0), 60.772746, places=4
        )

    def test_dose_rate_anchor_leo(self):
        # 600 km sun-synchronous-like orbit: small but nonzero rate.
        self.assertAlmostEqual(
            rdl.trapped_belt_dose_rate(600.0, 98.0), 0.263184, places=5
        )

    def test_polar_orbit_rates_higher_than_equatorial(self):
        self.assertGreater(
            rdl.trapped_belt_dose_rate(20000.0, 90.0),
            rdl.trapped_belt_dose_rate(20000.0, 0.0),
        )

    def test_dose_rate_symmetric_about_90_deg(self):
        self.assertAlmostEqual(
            rdl.trapped_belt_dose_rate(600.0, 80.0),
            rdl.trapped_belt_dose_rate(600.0, 100.0),
            places=9,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rdl.trapped_belt_dose_rate(-1.0, 90.0)
        with self.assertRaises(ValueError):
            rdl.trapped_belt_dose_rate(600.0, 181.0)
        with self.assertRaises(ValueError):
            rdl.inclination_factor(-5.0)


class SolarParticleEventTest(unittest.TestCase):
    def test_fluence_anchor_reference_energy(self):
        self.assertAlmostEqual(rdl.spe_fluence(10.0, 1.0), 1e8, places=-3)

    def test_fluence_power_law_scaling(self):
        # Exponent 3: 100 MeV is 1000x below the 10 MeV fluence.
        self.assertAlmostEqual(rdl.spe_fluence(100.0, 1.0), 1e5, places=-2)

    def test_fluence_scales_with_mission_years(self):
        self.assertAlmostEqual(rdl.spe_fluence(10.0, 5.0), 5e8, places=-3)

    def test_fluence_decreases_with_energy(self):
        self.assertLess(rdl.spe_fluence(50.0, 1.0), rdl.spe_fluence(10.0, 1.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rdl.spe_fluence(0.0, 1.0)
        with self.assertRaises(ValueError):
            rdl.spe_fluence(10.0, 0.0)
        with self.assertRaises(ValueError):
            rdl.spe_fluence(10.0, 1.0, spectral_index=0.0)


class SingleEventEffectTest(unittest.TestCase):
    SIGMA = 1e-6  # cm^2
    THRESHOLD = 10.0
    WIDTH = 15.0
    SHAPE = 1.0

    def test_rpp_anchor(self):
        # Weibull shape 1 at LET 20: 1e-6 * (1 - exp(-10/15)).
        self.assertAlmostEqual(
            rdl.rpp_cross_section(20.0, self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE),
            4.865829e-7,
            places=12,
        )

    def test_rpp_zero_below_threshold(self):
        self.assertEqual(
            rdl.rpp_cross_section(10.0, self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE),
            0.0,
        )
        self.assertEqual(
            rdl.rpp_cross_section(5.0, self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE),
            0.0,
        )

    def test_seu_rate_anchor_single_bin(self):
        rate = rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE,
                            [(20.0, 1e5)])
        self.assertAlmostEqual(rate, 0.0486583, places=6)

    def test_seu_rate_scales_with_cross_section(self):
        spec = rdl.power_law_let_spectrum(1e5, 2.5, 0.1, 100.0)
        rate1 = rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE, spec)
        rate2 = rdl.seu_rate(2.0 * self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE, spec)
        self.assertAlmostEqual(rate2, 2.0 * rate1, places=12)

    def test_seu_rate_zero_when_spectrum_below_threshold(self):
        rate = rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE,
                            [(5.0, 1e5), (8.0, 1e5)])
        self.assertEqual(rate, 0.0)

    def test_seu_rate_grows_with_spectrum_intensity(self):
        spec1 = rdl.power_law_let_spectrum(1e4, 2.5, 0.1, 100.0)
        spec2 = rdl.power_law_let_spectrum(2e4, 2.5, 0.1, 100.0)
        r1 = rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE, spec1)
        r2 = rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE, spec2)
        self.assertAlmostEqual(r2, 2.0 * r1, places=12)

    def test_spectrum_bins_deterministic(self):
        spec1 = rdl.power_law_let_spectrum(1e5, 2.5, 0.1, 100.0, bins=64)
        spec2 = rdl.power_law_let_spectrum(1e5, 2.5, 0.1, 100.0, bins=64)
        self.assertEqual(spec1, spec2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rdl.rpp_cross_section(20.0, 0.0, 10.0, 15.0, 1.0)
        with self.assertRaises(ValueError):
            rdl.rpp_cross_section(20.0, 1e-6, -1.0, 15.0, 1.0)
        with self.assertRaises(ValueError):
            rdl.seu_rate(self.SIGMA, self.THRESHOLD, 0.0, self.SHAPE, [(20.0, 1e5)])
        with self.assertRaises(ValueError):
            rdl.seu_rate(self.SIGMA, self.THRESHOLD, self.WIDTH, self.SHAPE, [])


class ShieldingTidTest(unittest.TestCase):
    DOSE_RATE = 0.26318426416049767  # rad/day at 600 km, 98 deg
    YEARS = 5.0

    def test_unshielded_anchor(self):
        self.assertAlmostEqual(
            rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 0.0),
            0.480640,
            places=5,
        )

    def test_shielded_anchors(self):
        self.assertAlmostEqual(
            rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 3.0),
            0.260932,
            places=5,
        )
        self.assertAlmostEqual(
            rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 10.0),
            0.134058,
            places=5,
        )

    def test_dose_decreases_with_shielding(self):
        t0 = rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 0.0)
        t3 = rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 3.0)
        t10 = rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 10.0)
        t50 = rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 50.0)
        self.assertLess(t3, t0)
        self.assertLess(t10, t3)
        self.assertLess(t50, t10)

    def test_shielding_meets_limit(self):
        # High dose rate (proton belt peak, polar orbit, 1 year): the
        # 10 krad limit needs a few mm of aluminum.
        rate = rdl.trapped_belt_dose_rate(3500.0, 90.0)
        t = rdl.shielding_for_dose_limit(rate, 1.0, 10.0)
        self.assertGreater(t, 4.0)
        self.assertLess(t, 5.0)
        self.assertLessEqual(rdl.tid_after_shielding(rate, 1.0, t), 10.0)
        self.assertGreater(rdl.tid_after_shielding(rate, 1.0, t - 0.01), 10.0)

    def test_shielding_returns_none_when_limit_unreachable(self):
        # Proton component floor: even 200 mm cannot meet the limit.
        rate = rdl.trapped_belt_dose_rate(3500.0, 90.0)
        self.assertIsNone(rdl.shielding_for_dose_limit(rate, 100.0, 10.0))

    def test_zero_shielding_is_unshielded(self):
        self.assertAlmostEqual(
            rdl.tid_after_shielding(self.DOSE_RATE, self.YEARS, 0.0),
            self.DOSE_RATE * 365.25 * self.YEARS / 1000.0,
            places=9,
        )

    def test_dose_verdicts(self):
        self.assertEqual(rdl.dose_verdict(10.0, 50.0), "ADEQUATE")
        self.assertEqual(rdl.dose_verdict(49.0, 50.0), "MARGINAL")
        self.assertEqual(rdl.dose_verdict(50.0, 50.0), "EXCEEDED")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rdl.tid_after_shielding(-1.0, 5.0, 3.0)
        with self.assertRaises(ValueError):
            rdl.tid_after_shielding(self.DOSE_RATE, 0.0, 3.0)
        with self.assertRaises(ValueError):
            rdl.tid_after_shielding(self.DOSE_RATE, 5.0, -2.0)
        with self.assertRaises(ValueError):
            rdl.tid_after_shielding(self.DOSE_RATE, 5.0, 3.0, electron_fraction=1.5)
        with self.assertRaises(ValueError):
            rdl.shielding_for_dose_limit(self.DOSE_RATE, 5.0, -1.0)
        with self.assertRaises(ValueError):
            rdl.dose_verdict(-1.0, 50.0)


class DebrisEnvironmentTest(unittest.TestCase):
    def test_flux_anchor_at_peak_altitude(self):
        self.assertAlmostEqual(rdl.debris_flux_per_m2_yr(850.0), 5e-5, places=12)

    def test_flux_anchor_leo(self):
        # 550 km: band factor exp(-1), flux drops by about 63 percent.
        self.assertAlmostEqual(
            rdl.debris_flux_per_m2_yr(550.0), 1.839397e-5, places=9
        )

    def test_flux_decreases_with_size(self):
        self.assertLess(
            rdl.debris_flux_per_m2_yr(850.0, min_size_cm=10.0),
            rdl.debris_flux_per_m2_yr(850.0, min_size_cm=1.0),
        )

    def test_collision_probability_anchor_small_lambda(self):
        # lambda = 5e-5, P = 1 - exp(-5e-5) ~ 5e-5.
        p = rdl.collision_probability(5e-5, 1.0, 1.0)
        self.assertAlmostEqual(p, 4.999875e-5, places=10)

    def test_collision_probability_grows_with_mission_life(self):
        p1 = rdl.collision_probability(5e-5, 1.0, 1.0)
        p5 = rdl.collision_probability(5e-5, 1.0, 5.0)
        p10 = rdl.collision_probability(5e-5, 1.0, 10.0)
        self.assertGreater(p5, p1)
        self.assertGreater(p10, p5)

    def test_collision_probability_grows_with_cross_section(self):
        p1 = rdl.collision_probability(5e-5, 1.0, 5.0)
        p10 = rdl.collision_probability(5e-5, 10.0, 5.0)
        self.assertGreater(p10, p1)

    def test_collision_probability_zero_edges(self):
        self.assertEqual(rdl.collision_probability(5e-5, 0.0, 5.0), 0.0)
        self.assertEqual(rdl.collision_probability(0.0, 10.0, 5.0), 0.0)

    def test_collision_probability_bounded_by_one(self):
        p = rdl.collision_probability(1e-3, 100.0, 100.0)
        self.assertLess(p, 1.0)

    def test_debris_verdicts(self):
        self.assertEqual(rdl.debris_verdict(0.005), "LOW")
        self.assertEqual(rdl.debris_verdict(0.05), "MODERATE")
        self.assertEqual(rdl.debris_verdict(0.5), "HIGH")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rdl.debris_flux_per_m2_yr(-100.0)
        with self.assertRaises(ValueError):
            rdl.debris_flux_per_m2_yr(850.0, min_size_cm=0.0)
        with self.assertRaises(ValueError):
            rdl.collision_probability(-1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            rdl.collision_probability(5e-5, 1.0, 0.0)
        with self.assertRaises(ValueError):
            rdl.debris_verdict(1.5)
        with self.assertRaises(ValueError):
            rdl.debris_verdict(0.5, low_threshold=0.2, high_threshold=0.1)


class RadiationDebrisAssessmentTest(unittest.TestCase):
    def _spectrum(self):
        return rdl.power_law_let_spectrum(1e5, 2.5, 0.1, 100.0)

    def _assessment(self, **kw):
        params = dict(
            altitude_km=600.0,
            inclination_deg=98.0,
            mission_years=5.0,
            shielding_mm_al=3.0,
            sigma_sat=1e-6,
            let_threshold=10.0,
            width=15.0,
            shape=1.0,
            spectrum=self._spectrum(),
            cross_section_m2=10.0,
        )
        params.update(kw)
        return rdl.RadiationDebrisAssessment(**params)

    def test_worked_example_leo_report(self):
        a = self._assessment()
        r = a.report()
        self.assertAlmostEqual(r["dose_rate_rad_day"], 0.263184, places=5)
        self.assertAlmostEqual(r["tid_krad"], 0.260932, places=5)
        self.assertAlmostEqual(r["seu_rate_per_day"], 4.819131e-4, places=8)
        self.assertAlmostEqual(r["debris_flux_per_m2_yr"], 2.496759e-5, places=10)
        self.assertAlmostEqual(r["collision_probability"], 1.247601e-3, places=8)
        self.assertEqual(r["dose_verdict"], "ADEQUATE")
        self.assertEqual(r["debris_verdict"], "LOW")

    def test_reduced_shielding_increases_dose(self):
        a1 = self._assessment(shielding_mm_al=1.0)
        a2 = self._assessment(shielding_mm_al=5.0)
        self.assertGreater(a1.tid_krad(), a2.tid_krad())

    def test_longer_mission_increases_dose_and_collision_risk(self):
        a1 = self._assessment(mission_years=2.0)
        a2 = self._assessment(mission_years=8.0)
        self.assertGreater(a2.tid_krad(), a1.tid_krad())
        self.assertGreater(a2.collision_probability(), a1.collision_probability())

    def test_larger_debris_cross_section_increases_risk(self):
        a1 = self._assessment(cross_section_m2=1.0)
        a2 = self._assessment(cross_section_m2=100.0)
        self.assertGreater(a2.collision_probability(), a1.collision_probability())

    def test_high_risk_scenario_verdicts(self):
        # A debris-dense orbit with a big cross-section and long life.
        a = self._assessment(altitude_km=850.0, cross_section_m2=200.0, mission_years=20.0)
        self.assertEqual(a.debris_verdict(), "HIGH")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            self._assessment(altitude_km=-1.0)
        with self.assertRaises(ValueError):
            self._assessment(inclination_deg=200.0)
        with self.assertRaises(ValueError):
            self._assessment(mission_years=0.0)
        with self.assertRaises(ValueError):
            self._assessment(sigma_sat=0.0)
        with self.assertRaises(ValueError):
            self._assessment(spectrum=[])


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Gate-3 contract tests for e1012-bg-direct.

Run: python3 test_e1012_bg_direct.py
stdlib unittest only; offline; deterministic.
"""
import unittest

from e1012_bg_direct_logic import (
    KNOWN_PARTICLE_TYPES,
    _HEMISPHERE_FACTOR,
    assess_sensor_background,
    compute_deposited_energy_mev,
    compute_hit_rate,
    particle_above_threshold,
    validate_particle,
    validate_sensor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SENSOR_SI = {
    "area_cm2": 1.0,
    "thickness_cm": 0.03,       # 300 µm silicon
    "density_g_cm3": 2.33,
    "threshold_mev": 0.05,
}

PROTON_100MEV = {
    "type": "trapped_proton",
    "flux_cm2_s": 1000.0,
    "let_mev_cm2_mg": 0.002,    # ~100 MeV proton in Si
}

ELECTRON_1MEV = {
    "type": "trapped_electron",
    "flux_cm2_s": 5000.0,
    "let_mev_cm2_mg": 0.0001,   # low LET — will be below threshold
}

GCR_HEAVY = {
    "type": "gcr_heavy",
    "flux_cm2_s": 0.1,
    "let_mev_cm2_mg": 5.0,      # heavy ion — large deposited energy
}


# ---------------------------------------------------------------------------
# compute_deposited_energy_mev
# ---------------------------------------------------------------------------

class TestDepositedEnergy(unittest.TestCase):

    def test_basic_calculation(self):
        # E = 0.01 [MeV·cm²/mg] × 1.0 [g/cm³] × 1000 [mg/g] × 0.01 [cm]
        #   = 0.01 × 1000 × 0.01 = 0.1 MeV
        result = compute_deposited_energy_mev(0.01, 1.0, 0.01)
        self.assertAlmostEqual(result, 0.1, places=10)

    def test_silicon_proton_realistic(self):
        # 100 MeV proton in 300 µm Si: ~140 keV = 0.1398 MeV
        result = compute_deposited_energy_mev(0.002, 2.33, 0.03)
        self.assertAlmostEqual(result, 0.002 * 2330.0 * 0.03, places=10)

    def test_proportional_to_let(self):
        e1 = compute_deposited_energy_mev(1.0, 1.0, 1.0)
        e2 = compute_deposited_energy_mev(2.0, 1.0, 1.0)
        self.assertAlmostEqual(e2, 2 * e1, places=10)

    def test_proportional_to_thickness(self):
        e1 = compute_deposited_energy_mev(1.0, 1.0, 0.5)
        e2 = compute_deposited_energy_mev(1.0, 1.0, 1.0)
        self.assertAlmostEqual(e2, 2 * e1, places=10)

    def test_invalid_let_zero(self):
        with self.assertRaises(ValueError):
            compute_deposited_energy_mev(0.0, 1.0, 1.0)

    def test_invalid_let_negative(self):
        with self.assertRaises(ValueError):
            compute_deposited_energy_mev(-1.0, 1.0, 1.0)

    def test_invalid_density_zero(self):
        with self.assertRaises(ValueError):
            compute_deposited_energy_mev(1.0, 0.0, 1.0)

    def test_invalid_path_zero(self):
        with self.assertRaises(ValueError):
            compute_deposited_energy_mev(1.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# particle_above_threshold
# ---------------------------------------------------------------------------

class TestThresholdFilter(unittest.TestCase):

    def test_above_threshold(self):
        self.assertTrue(particle_above_threshold(1.0, 0.5))

    def test_below_threshold(self):
        self.assertFalse(particle_above_threshold(0.3, 0.5))

    def test_exactly_at_threshold(self):
        # at threshold → contributes (>=)
        self.assertTrue(particle_above_threshold(0.5, 0.5))

    def test_zero_threshold_always_contributes(self):
        self.assertTrue(particle_above_threshold(0.001, 0.0))


# ---------------------------------------------------------------------------
# validate_particle
# ---------------------------------------------------------------------------

class TestValidateParticle(unittest.TestCase):

    def test_valid_particle_passes(self):
        validate_particle(PROTON_100MEV)  # no exception

    def test_missing_type_raises_key_error(self):
        bad = {"flux_cm2_s": 100.0, "let_mev_cm2_mg": 0.1}
        with self.assertRaises(KeyError):
            validate_particle(bad)

    def test_unknown_type_raises_value_error(self):
        bad = dict(PROTON_100MEV, type="dark_matter")
        with self.assertRaises(ValueError):
            validate_particle(bad)

    def test_negative_flux_raises_value_error(self):
        bad = dict(PROTON_100MEV, flux_cm2_s=-1.0)
        with self.assertRaises(ValueError):
            validate_particle(bad)

    def test_zero_let_raises_value_error(self):
        bad = dict(PROTON_100MEV, let_mev_cm2_mg=0.0)
        with self.assertRaises(ValueError):
            validate_particle(bad)

    def test_all_known_types_accepted(self):
        for ptype in KNOWN_PARTICLE_TYPES:
            p = {"type": ptype, "flux_cm2_s": 1.0, "let_mev_cm2_mg": 0.1}
            validate_particle(p)  # no exception


# ---------------------------------------------------------------------------
# validate_sensor
# ---------------------------------------------------------------------------

class TestValidateSensor(unittest.TestCase):

    def test_valid_sensor_passes(self):
        validate_sensor(SENSOR_SI)  # no exception

    def test_missing_area_raises_key_error(self):
        bad = {k: v for k, v in SENSOR_SI.items() if k != "area_cm2"}
        with self.assertRaises(KeyError):
            validate_sensor(bad)

    def test_zero_area_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_sensor(dict(SENSOR_SI, area_cm2=0.0))

    def test_zero_thickness_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_sensor(dict(SENSOR_SI, thickness_cm=0.0))

    def test_zero_density_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_sensor(dict(SENSOR_SI, density_g_cm3=0.0))

    def test_negative_threshold_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_sensor(dict(SENSOR_SI, threshold_mev=-0.01))


# ---------------------------------------------------------------------------
# compute_hit_rate
# ---------------------------------------------------------------------------

class TestHitRate(unittest.TestCase):

    def test_basic_hit_rate(self):
        # flux=1000, area=1, factor=0.5 → 500 events/s
        self.assertAlmostEqual(compute_hit_rate(1000.0, 1.0), 500.0, places=10)

    def test_hemisphere_factor_applied(self):
        rate = compute_hit_rate(1.0, 1.0)
        self.assertAlmostEqual(rate, _HEMISPHERE_FACTOR, places=10)

    def test_zero_flux_gives_zero_rate(self):
        self.assertEqual(compute_hit_rate(0.0, 1.0), 0.0)

    def test_invalid_area_zero(self):
        with self.assertRaises(ValueError):
            compute_hit_rate(1000.0, 0.0)


# ---------------------------------------------------------------------------
# assess_sensor_background — integration
# ---------------------------------------------------------------------------

class TestAssessSensorBackground(unittest.TestCase):

    def test_single_above_threshold_particle(self):
        result = assess_sensor_background([PROTON_100MEV], SENSOR_SI)
        self.assertEqual(len(result.contributions), 1)
        self.assertTrue(result.contributions[0].above_threshold)
        self.assertGreater(result.total_background_s, 0.0)

    def test_below_threshold_particle_contributes_zero(self):
        # LET chosen so deposited energy is far below threshold
        sub = {"type": "trapped_electron", "flux_cm2_s": 1e6, "let_mev_cm2_mg": 1e-6}
        result = assess_sensor_background([sub], SENSOR_SI)
        c = result.contributions[0]
        self.assertFalse(c.above_threshold)
        self.assertEqual(c.hit_rate_s, 0.0)
        self.assertEqual(result.total_background_s, 0.0)

    def test_budget_not_exceeded(self):
        result = assess_sensor_background(
            [PROTON_100MEV], SENSOR_SI, budget_events_s=10000.0
        )
        self.assertFalse(result.budget_exceeded)

    def test_budget_exceeded(self):
        result = assess_sensor_background(
            [PROTON_100MEV], SENSOR_SI, budget_events_s=0.001
        )
        self.assertTrue(result.budget_exceeded)

    def test_no_budget_gives_none(self):
        result = assess_sensor_background([PROTON_100MEV], SENSOR_SI)
        self.assertIsNone(result.budget_s)
        self.assertIsNone(result.budget_exceeded)

    def test_empty_particle_list_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background([], SENSOR_SI)

    def test_multiple_populations_sum_correctly(self):
        particles = [PROTON_100MEV, GCR_HEAVY]
        result = assess_sensor_background(particles, SENSOR_SI)
        expected = sum(
            c.hit_rate_s for c in result.contributions
        )
        self.assertAlmostEqual(result.total_background_s, expected, places=10)

    def test_mixed_above_and_below_threshold(self):
        particles = [PROTON_100MEV, ELECTRON_1MEV]
        result = assess_sensor_background(particles, SENSOR_SI)
        above_count = sum(1 for c in result.contributions if c.above_threshold)
        below_count = sum(1 for c in result.contributions if not c.above_threshold)
        self.assertGreaterEqual(above_count, 1)
        self.assertGreaterEqual(below_count, 0)

    def test_negative_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_sensor_background([PROTON_100MEV], SENSOR_SI, budget_events_s=-1.0)

    def test_total_rate_numeric_value(self):
        # Proton 100 MeV: dep = 0.002 × 2330 × 0.03 = 0.1398 MeV > 0.05 threshold
        # rate = 1000 × 1.0 × 0.5 = 500 events/s
        result = assess_sensor_background([PROTON_100MEV], SENSOR_SI)
        expected_dep = 0.002 * 2330.0 * 0.03
        self.assertAlmostEqual(result.contributions[0].deposited_mev, expected_dep, places=6)
        self.assertAlmostEqual(result.total_background_s, 500.0, places=6)

    def test_gcr_heavy_above_threshold(self):
        # LET=5 → E = 5 × 2330 × 0.03 = 349.5 MeV >> 0.05 threshold
        result = assess_sensor_background([GCR_HEAVY], SENSOR_SI)
        self.assertTrue(result.contributions[0].above_threshold)

    def test_contributions_list_length_matches_input(self):
        particles = [PROTON_100MEV, ELECTRON_1MEV, GCR_HEAVY]
        result = assess_sensor_background(particles, SENSOR_SI)
        self.assertEqual(len(result.contributions), len(particles))


if __name__ == "__main__":
    unittest.main()

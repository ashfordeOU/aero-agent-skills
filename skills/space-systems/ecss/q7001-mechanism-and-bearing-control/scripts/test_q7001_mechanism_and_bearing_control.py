"""Contract tests for the mechanism, bearing and slip-ring contamination logic."""

import math
import unittest

from q7001_mechanism_and_bearing_control_logic import (
    BRIDGING_CATEGORIES,
    CC1246_EXPONENT,
    MARGIN_TOLERANCE,
    REFERENCE_AREA_M2,
    assess_mechanism_cleanliness,
    bridging_category,
    clearance_margin_fraction,
    contamination_drag_torque_nm,
    largest_expected_particle_um,
    lubricant_creep_reach_mm,
    particle_count_over_area,
    particle_count_per_reference_area,
    torque_margin_fraction,
    validate_mechanism,
)


def mechanism(**overrides):
    base = {
        "cleanliness_level": 300.0,
        "wetted_area_m2": 0.01,
        "running_clearance_um": 500.0,
        "available_torque_nm": 0.2,
        "base_drag_nm": 0.05,
        "mission_days": 400.0,
        "slip_ring_gap_um": 1000.0,
        "drag_particle_size_um": 25.0,
        "drag_per_particle_nm": 1.0e-6,
        "required_torque_margin": 1.0,
        "required_clearance_margin": 0.5,
        "creep_rate_mm_per_day": 0.0,
        "creep_barrier_mm": 10.0,
    }
    base.update(overrides)
    return base


class PopulationTests(unittest.TestCase):
    def test_count_at_the_level_is_one_over_the_reference_area(self):
        self.assertAlmostEqual(
            particle_count_per_reference_area(300.0, 300.0), 1.0, places=9
        )

    def test_count_rises_steeply_towards_small_sizes(self):
        big = particle_count_per_reference_area(300.0, 100.0)
        small = particle_count_per_reference_area(300.0, 10.0)
        self.assertGreater(small, big * 10.0)

    def test_a_cleaner_level_has_fewer_particles(self):
        dirty = particle_count_per_reference_area(500.0, 25.0)
        clean = particle_count_per_reference_area(100.0, 25.0)
        self.assertGreater(dirty, clean)

    def test_count_matches_the_squared_logarithm_law(self):
        expected = 10.0 ** (
            CC1246_EXPONENT * (math.log10(300.0) ** 2 - math.log10(25.0) ** 2)
        )
        self.assertAlmostEqual(
            particle_count_per_reference_area(300.0, 25.0), expected, places=9
        )

    def test_area_scaling_is_linear(self):
        one = particle_count_over_area(300.0, 25.0, 0.01)
        two = particle_count_over_area(300.0, 25.0, 0.02)
        self.assertAlmostEqual(two, one * 2.0, places=9)

    def test_reference_area_scaling_is_the_identity(self):
        self.assertAlmostEqual(
            particle_count_over_area(300.0, 25.0, REFERENCE_AREA_M2),
            particle_count_per_reference_area(300.0, 25.0),
            places=9,
        )

    def test_sub_micrometre_size_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_per_reference_area(300.0, 0.5)

    def test_level_below_one_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_per_reference_area(0.5, 25.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_over_area(300.0, 25.0, 0.0)

    def test_boolean_size_rejected(self):
        with self.assertRaises(ValueError):
            particle_count_per_reference_area(300.0, True)


class LargestParticleTests(unittest.TestCase):
    def test_largest_particle_over_a_small_area(self):
        value = largest_expected_particle_um(300.0, 0.01)
        self.assertAlmostEqual(value, 177.25689805, places=6)

    def test_reference_area_returns_the_level(self):
        self.assertAlmostEqual(
            largest_expected_particle_um(300.0, REFERENCE_AREA_M2), 300.0, places=6
        )

    def test_a_larger_area_catches_a_larger_particle(self):
        small = largest_expected_particle_um(300.0, 0.001)
        large = largest_expected_particle_um(300.0, 0.05)
        self.assertGreater(large, small)

    def test_a_clean_level_over_a_tiny_area_expects_none(self):
        self.assertAlmostEqual(largest_expected_particle_um(50.0, 0.0001), 0.0)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            largest_expected_particle_um(300.0, -0.01)


class ClearanceAndGapTests(unittest.TestCase):
    def test_margin_is_the_unoccupied_fraction(self):
        self.assertAlmostEqual(
            clearance_margin_fraction(500.0, 100.0), 0.8, places=12
        )

    def test_a_particle_larger_than_the_clearance_gives_a_negative_margin(self):
        self.assertLess(clearance_margin_fraction(100.0, 250.0), 0.0)

    def test_no_particle_leaves_the_full_clearance(self):
        self.assertAlmostEqual(clearance_margin_fraction(500.0, 0.0), 1.0)

    def test_zero_clearance_rejected(self):
        with self.assertRaises(ValueError):
            clearance_margin_fraction(0.0, 100.0)

    def test_small_particle_is_clear(self):
        self.assertEqual(bridging_category(1000.0, 100.0), "clear")

    def test_half_gap_particle_is_marginal(self):
        self.assertEqual(bridging_category(1000.0, 500.0), "marginal")

    def test_gap_sized_particle_bridges(self):
        self.assertEqual(bridging_category(1000.0, 1000.0), "bridging")

    def test_oversized_particle_bridges(self):
        self.assertEqual(bridging_category(200.0, 400.0), "bridging")

    def test_every_outcome_is_a_known_category(self):
        for particle in (10.0, 600.0, 2000.0):
            self.assertIn(bridging_category(1000.0, particle), BRIDGING_CATEGORIES)

    def test_zero_gap_rejected(self):
        with self.assertRaises(ValueError):
            bridging_category(0.0, 100.0)


class TorqueAndCreepTests(unittest.TestCase):
    def test_clean_mechanism_keeps_its_base_drag(self):
        self.assertAlmostEqual(
            contamination_drag_torque_nm(0.05, 0.0, 1.0e-6), 0.05, places=12
        )

    def test_drag_scales_with_the_particle_count(self):
        self.assertAlmostEqual(
            contamination_drag_torque_nm(0.05, 1000.0, 1.0e-6), 0.051, places=12
        )

    def test_negative_particle_count_rejected(self):
        with self.assertRaises(ValueError):
            contamination_drag_torque_nm(0.05, -5.0, 1.0e-6)

    def test_negative_base_drag_rejected(self):
        with self.assertRaises(ValueError):
            contamination_drag_torque_nm(-0.05, 10.0, 1.0e-6)

    def test_torque_margin_is_relative(self):
        self.assertAlmostEqual(torque_margin_fraction(0.2, 0.05), 3.0, places=12)

    def test_torque_margin_of_zero_when_exactly_balanced(self):
        self.assertAlmostEqual(torque_margin_fraction(0.05, 0.05), 0.0)

    def test_zero_resisting_torque_rejected(self):
        with self.assertRaises(ValueError):
            torque_margin_fraction(0.2, 0.0)

    def test_creep_reach_is_rate_times_duration(self):
        self.assertAlmostEqual(lubricant_creep_reach_mm(0.05, 400.0), 20.0, places=12)

    def test_a_sealed_bearing_creeps_nothing(self):
        self.assertAlmostEqual(lubricant_creep_reach_mm(0.0, 400.0), 0.0)

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            lubricant_creep_reach_mm(0.05, 0.0)


class ValidationTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_mechanism(
            {
                "cleanliness_level": 300.0,
                "wetted_area_m2": 0.01,
                "running_clearance_um": 500.0,
                "available_torque_nm": 0.2,
                "base_drag_nm": 0.05,
                "mission_days": 400.0,
            }
        )
        self.assertIsNone(record["slip_ring_gap_um"])
        self.assertAlmostEqual(record["required_torque_margin"], 1.0)

    def test_missing_key_rejected(self):
        bad = mechanism()
        del bad["base_drag_nm"]
        with self.assertRaises(ValueError):
            validate_mechanism(bad)

    def test_required_clearance_margin_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_mechanism(mechanism(required_clearance_margin=1.4))

    def test_zero_base_drag_rejected(self):
        with self.assertRaises(ValueError):
            validate_mechanism(mechanism(base_drag_nm=0.0))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_mechanism("cleanliness_level")


class AssessmentTests(unittest.TestCase):
    def test_baseline_is_compliant(self):
        result = assess_mechanism_cleanliness(mechanism())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tight_clearance_is_flagged(self):
        result = assess_mechanism_cleanliness(mechanism(running_clearance_um=200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("clearance margin" in f for f in result["findings"]))

    def test_slip_ring_bridging_is_flagged(self):
        result = assess_mechanism_cleanliness(mechanism(slip_ring_gap_um=150.0))
        self.assertEqual(result["slip_ring"]["category"], "bridging")
        self.assertFalse(result["compliant"])

    def test_slip_ring_marginal_is_flagged(self):
        result = assess_mechanism_cleanliness(mechanism(slip_ring_gap_um=200.0))
        self.assertEqual(result["slip_ring"]["category"], "marginal")
        self.assertFalse(result["compliant"])

    def test_mechanism_without_a_slip_ring(self):
        spec = mechanism()
        spec["slip_ring_gap_um"] = None
        self.assertIsNone(assess_mechanism_cleanliness(spec)["slip_ring"])

    def test_contamination_drag_eats_the_torque_margin(self):
        clean = assess_mechanism_cleanliness(mechanism(drag_per_particle_nm=0.0))
        dirty = assess_mechanism_cleanliness(mechanism(drag_per_particle_nm=1.0e-4))
        self.assertGreater(
            clean["torque_margin_fraction"], dirty["torque_margin_fraction"]
        )

    def test_torque_shortfall_is_flagged(self):
        result = assess_mechanism_cleanliness(mechanism(available_torque_nm=0.06))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("torque margin" in f for f in result["findings"]))

    def test_lubricant_creep_past_the_barrier_is_flagged(self):
        result = assess_mechanism_cleanliness(
            mechanism(creep_rate_mm_per_day=0.05, creep_barrier_mm=10.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("creeps" in f for f in result["findings"]))

    def test_exact_clearance_margin_boundary_is_accepted(self):
        probe = assess_mechanism_cleanliness(mechanism())
        limit = probe["clearance_margin_fraction"]
        result = assess_mechanism_cleanliness(
            mechanism(required_clearance_margin=limit)
        )
        self.assertAlmostEqual(
            result["clearance_margin_fraction"], limit, places=9
        )
        self.assertTrue(result["compliant"])

    def test_exact_torque_margin_boundary_is_accepted(self):
        probe = assess_mechanism_cleanliness(mechanism())
        limit = probe["torque_margin_fraction"]
        result = assess_mechanism_cleanliness(mechanism(required_torque_margin=limit))
        self.assertAlmostEqual(result["torque_margin_fraction"], limit, places=9)
        self.assertTrue(result["compliant"])

    def test_a_dirtier_level_finds_a_bigger_particle(self):
        clean = assess_mechanism_cleanliness(mechanism(cleanliness_level=100.0))
        dirty = assess_mechanism_cleanliness(mechanism(cleanliness_level=500.0))
        self.assertGreater(
            dirty["largest_expected_particle_um"],
            clean["largest_expected_particle_um"],
        )

    def test_margin_tolerance_is_tight(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mechanism_cleanliness(["cleanliness_level"])


if __name__ == "__main__":
    unittest.main()

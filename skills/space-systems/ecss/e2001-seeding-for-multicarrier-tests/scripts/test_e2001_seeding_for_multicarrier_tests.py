#!/usr/bin/env python3
"""Gate 3 contract test for e2001-seeding-for-multicarrier-tests.

Offline, deterministic, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_seeding_for_multicarrier_tests_logic as logic  # noqa: E402


def base_spec(**over):
    spec = {
        "carrier_powers_w": [25.0, 25.0, 25.0, 25.0],
        "carrier_spacing_hz": 1.0e6,
        "breakdown_threshold_w": 200.0,
        "gap_volume_cm3": 0.01,
        "background_rate_per_cm3_s": 1.0,
        "seeding_confidence": 0.95,
        "technique": "electron-gun",
        "delivered_rate_per_s": 1.0e8,
        "perturbation_current_a": 1.0e-9,
        "max_perturbation_current_a": 1.0e-6,
    }
    spec.update(over)
    return spec


class CarrierSetValidation(unittest.TestCase):
    def test_valid_set_returns_floats(self):
        out = logic.validate_carrier_powers([4, 9])
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(out[0], 4.0, places=12)

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers("25,25")

    def test_zero_carrier_level_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0, 0.0])

    def test_negative_carrier_level_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0, -1.0])

    def test_non_numeric_carrier_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0, "25"])

    def test_boolean_carrier_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0, True])

    def test_infinite_carrier_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_powers([25.0, float("inf")])


class EnvelopeGeometry(unittest.TestCase):
    def test_coherent_peak_is_square_of_summed_amplitudes(self):
        self.assertAlmostEqual(logic.envelope_peak_w([16.0, 9.0]), 49.0, places=9)

    def test_peak_exceeds_arithmetic_sum_of_levels(self):
        peak = logic.envelope_peak_w([25.0] * 4)
        self.assertAlmostEqual(peak, 400.0, places=9)
        self.assertGreater(peak, 100.0)

    def test_beat_period_is_reciprocal_of_spacing(self):
        self.assertAlmostEqual(logic.beat_period_s(2.0e6), 5.0e-7, places=15)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.beat_period_s(0.0)

    def test_negative_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.beat_period_s(-1.0e6)

    def test_envelope_at_zero_equals_peak(self):
        value = logic.envelope_at_s([25.0, 25.0], 1.0e6, 0.0)
        self.assertAlmostEqual(value, 100.0, places=9)

    def test_envelope_at_half_beat_period_is_null_for_two_carriers(self):
        value = logic.envelope_at_s([25.0, 25.0], 1.0e6, 0.5e-6)
        self.assertAlmostEqual(value, 0.0, places=9)

    def test_envelope_rejects_zero_spacing(self):
        with self.assertRaises(ValueError):
            logic.envelope_at_s([25.0, 25.0], 0.0, 1.0e-7)


class DwellMeasurement(unittest.TestCase):
    def test_two_equal_carriers_spend_half_the_period_above_half_peak(self):
        fraction = logic.above_threshold_fraction([25.0, 25.0], 1.0e6, 50.0)
        self.assertAlmostEqual(fraction, 0.5, places=2)

    def test_fraction_grows_as_threshold_falls(self):
        high = logic.above_threshold_fraction([25.0] * 4, 1.0e6, 350.0)
        low = logic.above_threshold_fraction([25.0] * 4, 1.0e6, 50.0)
        self.assertGreater(low, high)
        self.assertGreater(high, 0.0)

    def test_fraction_is_zero_when_peak_never_reaches_threshold(self):
        fraction = logic.above_threshold_fraction([25.0] * 4, 1.0e6, 1000.0)
        self.assertAlmostEqual(fraction, 0.0, places=12)

    def test_dwell_is_fraction_times_beat_period(self):
        fraction = logic.above_threshold_fraction([25.0] * 4, 1.0e6, 200.0)
        dwell = logic.above_threshold_dwell_s([25.0] * 4, 1.0e6, 200.0)
        self.assertAlmostEqual(dwell, fraction * 1.0e-6, places=15)

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.above_threshold_fraction([25.0, 25.0], 1.0e6, 0.0)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.above_threshold_fraction([25.0, 25.0], 1.0e6, -5.0)

    def test_too_few_samples_rejected(self):
        with self.assertRaises(ValueError):
            logic.above_threshold_fraction([25.0, 25.0], 1.0e6, 50.0, samples=8)

    def test_non_integer_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.above_threshold_fraction([25.0, 25.0], 1.0e6, 50.0, samples=64.0)

    def test_boolean_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.above_threshold_fraction([25.0, 25.0], 1.0e6, 50.0, samples=True)


class ElectronPopulation(unittest.TestCase):
    def test_natural_population_is_rate_times_volume_times_dwell(self):
        lam = logic.natural_electron_population(0.02, 1.5, 2.0e-7)
        self.assertAlmostEqual(lam, 6.0e-9, places=18)

    def test_zero_background_rate_gives_no_electrons(self):
        self.assertAlmostEqual(
            logic.natural_electron_population(0.02, 0.0, 2.0e-7), 0.0, places=18
        )

    def test_zero_gap_volume_rejected(self):
        with self.assertRaises(ValueError):
            logic.natural_electron_population(0.0, 1.0, 1.0e-7)

    def test_negative_background_rate_rejected(self):
        with self.assertRaises(ValueError):
            logic.natural_electron_population(0.02, -1.0, 1.0e-7)

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            logic.natural_electron_population(0.02, 1.0, -1.0e-7)

    def test_required_population_matches_poisson_inverse(self):
        self.assertAlmostEqual(
            logic.required_population(0.95), -math.log(0.05), places=12
        )

    def test_presence_probability_round_trips_the_requirement(self):
        lam = logic.required_population(0.99)
        self.assertAlmostEqual(logic.presence_probability(lam), 0.99, places=12)

    def test_confidence_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_population(0.0)

    def test_confidence_of_one_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_population(1.0)

    def test_confidence_above_one_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_population(1.4)

    def test_negative_population_rejected_by_probability(self):
        with self.assertRaises(ValueError):
            logic.presence_probability(-0.1)


class SeedingDecision(unittest.TestCase):
    def test_sparse_natural_supply_demands_seeding(self):
        self.assertTrue(logic.seeding_is_required(1.0e-9, logic.required_population(0.95)))

    def test_rich_natural_supply_needs_no_seeding(self):
        self.assertFalse(logic.seeding_is_required(12.0, logic.required_population(0.95)))

    def test_exact_match_counts_as_satisfied(self):
        needed = logic.required_population(0.95)
        self.assertFalse(logic.seeding_is_required(needed, needed))

    def test_representation_error_does_not_flip_a_compliant_case(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3; a compliant case must stay compliant.
        self.assertFalse(logic.seeding_is_required(0.3, 0.1 + 0.2))

    def test_negative_natural_population_rejected(self):
        with self.assertRaises(ValueError):
            logic.seeding_is_required(-1.0, 3.0)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            logic.seeding_is_required(1.0, 0.0)

    def test_required_rate_closes_the_deficit(self):
        rate = logic.required_seed_rate_per_s(3.0, 1.0, 2.0e-7)
        self.assertAlmostEqual(rate, 1.0e7, places=1)

    def test_no_rate_needed_when_natural_supply_suffices(self):
        self.assertAlmostEqual(
            logic.required_seed_rate_per_s(3.0, 4.0, 2.0e-7), 0.0, places=12
        )

    def test_ulp_scale_deficit_is_absorbed_not_billed(self):
        self.assertAlmostEqual(
            logic.required_seed_rate_per_s(0.1 + 0.2, 0.3, 1.0e-7), 0.0, places=12
        )

    def test_zero_dwell_cannot_size_a_rate(self):
        with self.assertRaises(ValueError):
            logic.required_seed_rate_per_s(3.0, 0.0, 0.0)

    def test_negative_natural_population_rejected_by_sizing(self):
        with self.assertRaises(ValueError):
            logic.required_seed_rate_per_s(3.0, -1.0, 1.0e-7)


class TechniqueGrading(unittest.TestCase):
    def test_electron_gun_within_limits_is_admissible(self):
        out = logic.grade_technique("electron-gun", 1.0e8, 1.0e-9, 1.0e-6)
        self.assertTrue(out["admissible"])
        self.assertEqual(out["findings"], [])

    def test_rate_at_the_technique_ceiling_is_admissible(self):
        ceiling = logic.SEED_TECHNIQUES["radioactive-source"]["max_rate_per_s"]
        out = logic.grade_technique("radioactive-source", ceiling, 1.0e-13, 1.0e-9)
        self.assertTrue(out["admissible"])

    def test_rate_above_the_ceiling_is_flagged(self):
        out = logic.grade_technique("radioactive-source", 1.0e8, 1.0e-13, 1.0e-9)
        self.assertIn("seed-rate-above-technique-ceiling", out["findings"])

    def test_perturbation_current_at_the_limit_is_admissible(self):
        out = logic.grade_technique("electron-gun", 1.0e8, 1.0e-6, 1.0e-6)
        self.assertTrue(out["admissible"])

    def test_perturbation_current_above_the_limit_is_flagged(self):
        out = logic.grade_technique("electron-gun", 1.0e8, 1.0e-5, 1.0e-6)
        self.assertIn("rf-perturbation-current-exceeded", out["findings"])

    def test_unknown_technique_rejected(self):
        with self.assertRaises(ValueError):
            logic.grade_technique("candle", 1.0e8, 1.0e-9, 1.0e-6)

    def test_zero_delivered_rate_rejected(self):
        with self.assertRaises(ValueError):
            logic.grade_technique("electron-gun", 0.0, 1.0e-9, 1.0e-6)

    def test_negative_perturbation_current_rejected(self):
        with self.assertRaises(ValueError):
            logic.grade_technique("electron-gun", 1.0e8, -1.0e-9, 1.0e-6)

    def test_zero_perturbation_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.grade_technique("electron-gun", 1.0e8, 1.0e-9, 0.0)


class FullAssessment(unittest.TestCase):
    def test_seeded_multicarrier_run_is_compliant(self):
        out = logic.assess_multicarrier_seeding(base_spec())
        self.assertTrue(out["compliant"])
        self.assertTrue(out["seeding_required"])
        self.assertGreater(out["above_threshold_dwell_s"], 0.0)
        self.assertLess(out["natural_presence_probability"], 1.0e-6)
        self.assertGreater(out["seeded_presence_probability"], 0.99)

    def test_missing_seed_source_is_a_finding(self):
        spec = base_spec()
        spec["technique"] = None
        out = logic.assess_multicarrier_seeding(spec)
        self.assertIn("seed-source-absent-for-multicarrier-environment", out["findings"])
        self.assertFalse(out["compliant"])

    def test_weak_seed_rate_is_a_finding(self):
        out = logic.assess_multicarrier_seeding(base_spec(delivered_rate_per_s=1.0))
        self.assertIn("delivered-seed-rate-below-requirement", out["findings"])

    def test_envelope_below_threshold_is_a_finding(self):
        out = logic.assess_multicarrier_seeding(base_spec(breakdown_threshold_w=1000.0))
        self.assertIn("envelope-below-breakdown-threshold", out["findings"])
        self.assertAlmostEqual(out["above_threshold_dwell_s"], 0.0, places=15)
        self.assertAlmostEqual(out["required_seed_rate_per_s"], 0.0, places=12)

    def test_rich_background_removes_the_seeding_obligation(self):
        out = logic.assess_multicarrier_seeding(
            base_spec(
                gap_volume_cm3=1.0e6,
                background_rate_per_cm3_s=1.0e9,
                technique=None,
            )
        )
        self.assertFalse(out["seeding_required"])
        self.assertTrue(out["compliant"])

    def test_required_rate_is_reported_for_the_sparse_case(self):
        out = logic.assess_multicarrier_seeding(base_spec())
        expected = out["required_population"] / out["above_threshold_dwell_s"]
        self.assertAlmostEqual(
            out["required_seed_rate_per_s"] / expected, 1.0, places=6
        )

    def test_technique_report_is_carried_through(self):
        out = logic.assess_multicarrier_seeding(base_spec())
        self.assertEqual(out["technique_report"]["technique"], "electron-gun")
        self.assertTrue(out["technique_report"]["needs_sight_line"])

    def test_non_dict_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier_seeding(["carriers"])

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["gap_volume_cm3"]
        with self.assertRaises(ValueError):
            logic.assess_multicarrier_seeding(spec)

    def test_zero_threshold_in_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier_seeding(base_spec(breakdown_threshold_w=0.0))

    def test_unknown_technique_in_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_multicarrier_seeding(base_spec(technique="torch"))


if __name__ == "__main__":
    unittest.main()

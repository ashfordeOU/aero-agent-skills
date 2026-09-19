"""Contract tests for the vacuum-probe and solvent-rinse sampling logic."""

import unittest

from q7050_vacuum_and_rinse_methods_logic import (
    DEFAULT_BALANCE_FLOOR_MG,
    aliquot_scale_factor,
    area_density_mg_per_m2,
    assess_surface_sampling,
    blank_corrected_residue_mg,
    detection_limit_mg_per_m2,
    evaluate_probe_sample,
    evaluate_rinse_sample,
    particle_density_per_m2,
    probe_swept_area_m2,
    recovery_corrected_mg,
    select_sampling_method,
    validate_area_m2,
)


def rinse(**overrides):
    sample = {
        "id": "r1",
        "method": "solvent-rinse",
        "area_m2": 0.25,
        "rinse_volume_ml": 500.0,
        "aliquot_ml": 100.0,
        "residue_mg": 1.10,
        "blank_mg": 0.10,
        "recovery_fraction": 1.0,
    }
    sample.update(overrides)
    return sample


def probe(**overrides):
    sample = {
        "id": "p1",
        "method": "vacuum-probe",
        "strokes": 10,
        "probe_width_mm": 20.0,
        "stroke_length_mm": 500.0,
        "overlap_fraction": 0.0,
        "count": 400,
    }
    sample.update(overrides)
    return sample


class AreaValidationTests(unittest.TestCase):
    def test_area_returned_as_float(self):
        self.assertAlmostEqual(validate_area_m2(2), 2.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(0.0)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(-0.5)

    def test_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(True)

    def test_non_finite_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(float("nan"))


class ProbeGeometryTests(unittest.TestCase):
    def test_single_stroke_is_width_times_length(self):
        self.assertAlmostEqual(probe_swept_area_m2(1, 20.0, 500.0), 0.01, places=12)

    def test_non_overlapping_strokes_add_up(self):
        self.assertAlmostEqual(probe_swept_area_m2(10, 20.0, 500.0), 0.1, places=12)

    def test_overlap_reduces_the_swept_area(self):
        plain = probe_swept_area_m2(10, 20.0, 500.0, 0.0)
        lapped = probe_swept_area_m2(10, 20.0, 500.0, 0.5)
        self.assertAlmostEqual(lapped, plain * 0.55, places=12)

    def test_overlap_does_not_shrink_a_single_stroke(self):
        self.assertAlmostEqual(
            probe_swept_area_m2(1, 20.0, 500.0, 0.9),
            probe_swept_area_m2(1, 20.0, 500.0, 0.0),
            places=12,
        )

    def test_zero_strokes_rejected(self):
        with self.assertRaises(ValueError):
            probe_swept_area_m2(0, 20.0, 500.0)

    def test_non_integer_strokes_rejected(self):
        with self.assertRaises(ValueError):
            probe_swept_area_m2(3.5, 20.0, 500.0)

    def test_full_overlap_rejected(self):
        with self.assertRaises(ValueError):
            probe_swept_area_m2(4, 20.0, 500.0, 1.0)

    def test_negative_overlap_rejected(self):
        with self.assertRaises(ValueError):
            probe_swept_area_m2(4, 20.0, 500.0, -0.1)


class AliquotTests(unittest.TestCase):
    def test_fifth_aliquot_scales_by_five(self):
        self.assertAlmostEqual(aliquot_scale_factor(100.0, 500.0), 5.0, places=12)

    def test_whole_volume_scales_by_one(self):
        self.assertAlmostEqual(aliquot_scale_factor(500.0, 500.0), 1.0, places=12)

    def test_aliquot_larger_than_rinsate_rejected(self):
        with self.assertRaises(ValueError):
            aliquot_scale_factor(600.0, 500.0)

    def test_zero_aliquot_rejected(self):
        with self.assertRaises(ValueError):
            aliquot_scale_factor(0.0, 500.0)


class BlankAndRecoveryTests(unittest.TestCase):
    def test_net_is_sample_minus_blank(self):
        result = blank_corrected_residue_mg(1.10, 0.10)
        self.assertAlmostEqual(result["net_mg"], 1.0, places=12)
        self.assertEqual(result["status"], "quantified")

    def test_net_at_the_floor_is_sub_floor(self):
        result = blank_corrected_residue_mg(0.11, 0.10, 0.01)
        self.assertAlmostEqual(result["net_mg"], result["balance_floor_mg"], places=9)
        self.assertEqual(result["status"], "sub-floor")

    def test_blank_above_sample_past_the_floor_is_blank_dominated(self):
        result = blank_corrected_residue_mg(0.10, 0.40, 0.01)
        self.assertEqual(result["status"], "blank-dominated")

    def test_blank_slightly_above_sample_is_only_sub_floor(self):
        result = blank_corrected_residue_mg(0.100, 0.105, 0.01)
        self.assertEqual(result["status"], "sub-floor")

    def test_negative_blank_rejected(self):
        with self.assertRaises(ValueError):
            blank_corrected_residue_mg(1.0, -0.1)

    def test_default_floor_is_exposed(self):
        result = blank_corrected_residue_mg(1.0, 0.0)
        self.assertAlmostEqual(result["balance_floor_mg"], DEFAULT_BALANCE_FLOOR_MG,
                               places=12)

    def test_recovery_correction_raises_the_reported_mass(self):
        self.assertAlmostEqual(recovery_corrected_mg(0.8, 0.8), 1.0, places=12)

    def test_unit_recovery_is_a_pass_through(self):
        self.assertAlmostEqual(recovery_corrected_mg(1.25, 1.0), 1.25, places=12)

    def test_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            recovery_corrected_mg(1.0, 1.2)

    def test_zero_recovery_rejected(self):
        with self.assertRaises(ValueError):
            recovery_corrected_mg(1.0, 0.0)


class DensityTests(unittest.TestCase):
    def test_area_density(self):
        self.assertAlmostEqual(area_density_mg_per_m2(5.0, 0.25), 20.0, places=12)

    def test_particle_density(self):
        self.assertAlmostEqual(particle_density_per_m2(400, 0.1), 4000.0, places=9)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            particle_density_per_m2(-1, 0.1)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            particle_density_per_m2(4.5, 0.1)

    def test_detection_limit_scales_with_dilution(self):
        base = detection_limit_mg_per_m2(0.01, 0.25, 1.0, 1.0)
        diluted = detection_limit_mg_per_m2(0.01, 0.25, 1.0, 5.0)
        self.assertAlmostEqual(diluted, base * 5.0, places=12)

    def test_detection_limit_worsens_with_poor_recovery(self):
        base = detection_limit_mg_per_m2(0.01, 0.25, 1.0)
        poor = detection_limit_mg_per_m2(0.01, 0.25, 0.5)
        self.assertAlmostEqual(poor, base * 2.0, places=12)

    def test_dilution_below_one_rejected(self):
        with self.assertRaises(ValueError):
            detection_limit_mg_per_m2(0.01, 0.25, 1.0, 0.5)


class MethodSelectionTests(unittest.TestCase):
    def test_nvr_prefers_the_rinse_when_both_are_possible(self):
        result = select_sampling_method({
            "target": "nvr", "accessible": True, "solvent_compatible": True,
            "rinsate_collectable": True, "probe_tolerant": True,
        })
        self.assertEqual(result["chosen"], "solvent-rinse")

    def test_particulate_prefers_the_probe_when_both_are_possible(self):
        result = select_sampling_method({
            "target": "particulate", "accessible": True, "solvent_compatible": True,
            "rinsate_collectable": True, "probe_tolerant": True,
        })
        self.assertEqual(result["chosen"], "vacuum-probe")

    def test_uncollectable_rinsate_leaves_only_the_probe(self):
        result = select_sampling_method({
            "target": "nvr", "accessible": True, "solvent_compatible": True,
            "rinsate_collectable": False, "probe_tolerant": True,
        })
        self.assertEqual(result["eligible"], ["vacuum-probe"])
        self.assertEqual(result["chosen"], "vacuum-probe")

    def test_inaccessible_surface_has_no_method(self):
        with self.assertRaises(ValueError):
            select_sampling_method({
                "target": "nvr", "accessible": False, "solvent_compatible": True,
                "rinsate_collectable": True, "probe_tolerant": True,
            })

    def test_unknown_target_rejected(self):
        with self.assertRaises(ValueError):
            select_sampling_method({"target": "outgassing", "probe_tolerant": True})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            select_sampling_method({"target": "nvr", "accessible": "yes"})


class SampleEvaluationTests(unittest.TestCase):
    def test_rinse_loading_uses_the_whole_collected_volume(self):
        record = evaluate_rinse_sample(rinse())
        # net 1.00 mg in a 100 mL aliquot of 500 mL -> 5.00 mg over 0.25 m2
        self.assertAlmostEqual(record["loading_mg_per_m2"], 20.0, places=9)

    def test_rinse_sub_floor_reports_no_loading(self):
        record = evaluate_rinse_sample(rinse(residue_mg=0.105, blank_mg=0.100))
        self.assertEqual(record["status"], "sub-floor")
        self.assertIsNone(record["loading_mg_per_m2"])

    def test_rinse_recovery_raises_the_loading(self):
        full = evaluate_rinse_sample(rinse())
        partial = evaluate_rinse_sample(rinse(recovery_fraction=0.5))
        self.assertAlmostEqual(partial["loading_mg_per_m2"],
                               full["loading_mg_per_m2"] * 2.0, places=9)

    def test_rinse_missing_key_rejected(self):
        sample = rinse()
        del sample["aliquot_ml"]
        with self.assertRaises(ValueError):
            evaluate_rinse_sample(sample)

    def test_probe_density_uses_the_swept_area(self):
        record = evaluate_probe_sample(probe())
        self.assertAlmostEqual(record["area_m2"], 0.1, places=12)
        self.assertAlmostEqual(record["particles_per_m2"], 4000.0, places=9)

    def test_probe_missing_key_rejected(self):
        sample = probe()
        del sample["count"]
        with self.assertRaises(ValueError):
            evaluate_probe_sample(sample)

    def test_probe_sample_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_probe_sample(["strokes"])


class AssessmentTests(unittest.TestCase):
    def test_clean_set_reports_no_findings(self):
        result = assess_surface_sampling({
            "samples": [rinse(), probe()],
            "reporting_limit_mg_per_m2": 50.0,
        })
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["quantified_count"], 2)

    def test_loading_above_the_reporting_limit_is_flagged(self):
        result = assess_surface_sampling({
            "samples": [rinse()],
            "reporting_limit_mg_per_m2": 10.0,
        })
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("exceeds the reporting limit" in f for f in result["findings"]))

    def test_loading_exactly_at_the_limit_is_not_flagged(self):
        result = assess_surface_sampling({
            "samples": [rinse()],
            "reporting_limit_mg_per_m2": 20.0,
        })
        self.assertEqual(result["findings"], [])

    def test_blank_dominated_sample_is_flagged(self):
        result = assess_surface_sampling({
            "samples": [rinse(residue_mg=0.10, blank_mg=0.90)],
        })
        self.assertTrue(any("witness blank" in f for f in result["findings"]))

    def test_detection_limit_above_the_reporting_limit_is_flagged(self):
        result = assess_surface_sampling({
            "samples": [rinse(area_m2=0.0001)],
            "reporting_limit_mg_per_m2": 1.0,
        })
        self.assertTrue(any("detection limit" in f for f in result["findings"]))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_sampling({"samples": [{"method": "tape-lift"}]})

    def test_empty_sample_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_sampling({"samples": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_sampling(["samples"])


if __name__ == "__main__":
    unittest.main()

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from e1012_suscept_unc_logic import (
    categorize_data_quality,
    compute_required_threshold,
    check_component_margin,
    assess_component,
    assess_batch,
    EFFECT_TYPES,
    SOURCE_TYPES,
)


class TestCategorizeDataQuality(unittest.TestCase):

    def test_high_level_multi_lot(self):
        r = categorize_data_quality(sample_size=6, source_type="ground_equivalent", lot_count=2)
        self.assertEqual(r["level"], "high")
        self.assertAlmostEqual(r["uncertainty_factor"], 1.0)

    def test_high_level_space_flight(self):
        r = categorize_data_quality(sample_size=5, source_type="space_flight", lot_count=3)
        self.assertEqual(r["level"], "high")

    def test_medium_level_sufficient_samples_vendor(self):
        r = categorize_data_quality(sample_size=4, source_type="vendor_spec")
        self.assertEqual(r["level"], "medium")
        self.assertAlmostEqual(r["uncertainty_factor"], 1.5)

    def test_medium_level_single_sample_qualified_source(self):
        r = categorize_data_quality(sample_size=1, source_type="space_flight")
        self.assertEqual(r["level"], "medium")

    def test_medium_level_three_samples_any_source(self):
        r = categorize_data_quality(sample_size=3, source_type="vendor_spec")
        self.assertEqual(r["level"], "medium")

    def test_low_level_single_vendor(self):
        r = categorize_data_quality(sample_size=1, source_type="vendor_spec")
        self.assertEqual(r["level"], "low")
        self.assertAlmostEqual(r["uncertainty_factor"], 2.0)

    def test_absent_zero_samples(self):
        r = categorize_data_quality(sample_size=0, source_type="vendor_spec")
        self.assertEqual(r["level"], "absent")
        self.assertAlmostEqual(r["uncertainty_factor"], 3.0)

    def test_absent_assumed_source_overrides_large_sample(self):
        r = categorize_data_quality(sample_size=20, source_type="assumed")
        self.assertEqual(r["level"], "absent")

    def test_description_is_string(self):
        r = categorize_data_quality(sample_size=5, source_type="space_flight", lot_count=2)
        self.assertIsInstance(r["description"], str)
        self.assertGreater(len(r["description"]), 0)

    def test_invalid_negative_sample_size(self):
        with self.assertRaises(ValueError):
            categorize_data_quality(sample_size=-1, source_type="vendor_spec")

    def test_invalid_source_type(self):
        with self.assertRaises(ValueError):
            categorize_data_quality(sample_size=3, source_type="mystery_source")

    def test_invalid_lot_count_zero(self):
        with self.assertRaises(ValueError):
            categorize_data_quality(sample_size=5, source_type="ground_equivalent", lot_count=0)

    def test_high_requires_two_lots(self):
        # Five samples from one lot with a good source -> medium, not high
        r = categorize_data_quality(sample_size=5, source_type="ground_equivalent", lot_count=1)
        self.assertEqual(r["level"], "medium")


class TestComputeRequiredThreshold(unittest.TestCase):

    def test_basic_no_uncertainty(self):
        result = compute_required_threshold(1000.0, 2.0, 1.0)
        self.assertAlmostEqual(result, 2000.0)

    def test_with_medium_uncertainty(self):
        result = compute_required_threshold(1000.0, 2.0, 1.5)
        self.assertAlmostEqual(result, 3000.0)

    def test_with_absent_uncertainty(self):
        result = compute_required_threshold(500.0, 2.0, 3.0)
        self.assertAlmostEqual(result, 3000.0)

    def test_invalid_zero_environment_dose(self):
        with self.assertRaises(ValueError):
            compute_required_threshold(0.0, 2.0, 1.0)

    def test_invalid_negative_environment_dose(self):
        with self.assertRaises(ValueError):
            compute_required_threshold(-100.0, 2.0, 1.0)

    def test_invalid_base_rdm_below_one(self):
        with self.assertRaises(ValueError):
            compute_required_threshold(1000.0, 0.9, 1.0)

    def test_invalid_uncertainty_factor_below_one(self):
        with self.assertRaises(ValueError):
            compute_required_threshold(1000.0, 2.0, 0.5)


class TestCheckComponentMargin(unittest.TestCase):

    def test_passes_with_margin_headroom(self):
        r = check_component_margin(8000.0, 1000.0, 2.0, 1.0)
        self.assertTrue(r["passes"])
        self.assertIsNone(r["shortfall"])

    def test_fails_insufficient_threshold(self):
        # required = 1000 * 2.0 * 1.5 = 3000; component = 2500 -> fail
        r = check_component_margin(2500.0, 1000.0, 2.0, 1.5)
        self.assertFalse(r["passes"])
        self.assertAlmostEqual(r["shortfall"], 500.0)

    def test_exact_boundary_passes(self):
        # required = 1000 * 2.0 * 1.0 = 2000; component = 2000 -> pass
        r = check_component_margin(2000.0, 1000.0, 2.0, 1.0)
        self.assertTrue(r["passes"])

    def test_achieved_rdm_value(self):
        r = check_component_margin(4000.0, 1000.0, 2.0, 1.0)
        self.assertAlmostEqual(r["achieved_rdm"], 4.0)

    def test_effective_required_rdm(self):
        r = check_component_margin(5000.0, 1000.0, 2.0, 1.5)
        self.assertAlmostEqual(r["effective_required_rdm"], 3.0)

    def test_invalid_zero_component_threshold(self):
        with self.assertRaises(ValueError):
            check_component_margin(0.0, 1000.0, 2.0, 1.0)

    def test_required_threshold_in_result(self):
        r = check_component_margin(5000.0, 1000.0, 2.0, 2.0)
        self.assertAlmostEqual(r["required_threshold"], 4000.0)


class TestAssessComponent(unittest.TestCase):

    def test_full_pipeline_passes_high_quality(self):
        r = assess_component(
            component_id="R001",
            effect_type="TID",
            component_threshold=10000.0,
            environment_dose=1000.0,
            base_rdm=2.0,
            sample_size=6,
            source_type="ground_equivalent",
            lot_count=2,
        )
        self.assertTrue(r["passes"])
        self.assertEqual(r["data_quality"]["level"], "high")
        self.assertEqual(r["component_id"], "R001")

    def test_full_pipeline_fails_absent_data(self):
        r = assess_component(
            component_id="C002",
            effect_type="TID",
            component_threshold=2500.0,
            environment_dose=1000.0,
            base_rdm=2.0,
            sample_size=0,
            source_type="vendor_spec",
        )
        self.assertFalse(r["passes"])
        self.assertEqual(r["data_quality"]["level"], "absent")
        self.assertAlmostEqual(r["shortfall"], 3500.0)

    def test_see_effect_type_accepted(self):
        r = assess_component(
            component_id="D003",
            effect_type="SEE",
            component_threshold=1e12,
            environment_dose=1e10,
            base_rdm=2.0,
            sample_size=5,
            source_type="space_flight",
            lot_count=2,
        )
        self.assertEqual(r["effect_type"], "SEE")
        self.assertTrue(r["passes"])

    def test_invalid_effect_type_raises(self):
        with self.assertRaises(ValueError):
            assess_component(
                component_id="X",
                effect_type="COSMIC_RAY",
                component_threshold=5000.0,
                environment_dose=1000.0,
                base_rdm=2.0,
                sample_size=3,
                source_type="vendor_spec",
            )

    def test_niel_and_dd_accepted(self):
        for et in ("NIEL", "DD"):
            r = assess_component(
                component_id="T",
                effect_type=et,
                component_threshold=5000.0,
                environment_dose=1000.0,
                base_rdm=2.0,
                sample_size=3,
                source_type="ground_equivalent",
            )
            self.assertEqual(r["effect_type"], et)


class TestAssessBatch(unittest.TestCase):

    def test_batch_mixed_pass_fail(self):
        components = [
            dict(
                component_id="A", effect_type="TID",
                component_threshold=10000.0, environment_dose=1000.0,
                base_rdm=2.0, sample_size=6,
                source_type="ground_equivalent", lot_count=2,
            ),
            dict(
                component_id="B", effect_type="SEE",
                component_threshold=1500.0, environment_dose=1000.0,
                base_rdm=2.0, sample_size=1,
                source_type="vendor_spec", lot_count=1,
            ),
        ]
        results = assess_batch(components)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["passes"])
        self.assertFalse(results[1]["passes"])

    def test_empty_batch(self):
        self.assertEqual(assess_batch([]), [])

    def test_batch_preserves_order(self):
        ids = ["X1", "X2", "X3"]
        components = [
            dict(
                component_id=cid, effect_type="TID",
                component_threshold=5000.0, environment_dose=1000.0,
                base_rdm=2.0, sample_size=5,
                source_type="space_flight", lot_count=2,
            )
            for cid in ids
        ]
        results = assess_batch(components)
        self.assertEqual([r["component_id"] for r in results], ids)


if __name__ == "__main__":
    unittest.main()

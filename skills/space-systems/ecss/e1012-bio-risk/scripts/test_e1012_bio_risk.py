"""
Gate 3 contract tests for e1012-bio-risk.

stdlib unittest only.  Offline, deterministic.
Run: python3 test_e1012_bio_risk.py
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bio_risk_logic import (
    NOMINAL_RISK_COEFFICIENT_PER_MSV,
    TISSUE_WEIGHTS,
    assess_risk,
    categorize_uncertainty_source,
    compute_effective_dose,
    compute_risk_bounds,
    estimate_excess_risk,
)


class TestTissueWeights(unittest.TestCase):

    def test_weights_sum_to_one(self):
        total = sum(TISSUE_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=10)

    def test_expected_tissues_present(self):
        for tissue in ('lung', 'stomach', 'red_bone_marrow', 'thyroid', 'skin'):
            self.assertIn(tissue, TISSUE_WEIGHTS)


class TestEffectiveDose(unittest.TestCase):

    def test_zero_dose_single_organ(self):
        result = compute_effective_dose({'lung': 0.0})
        self.assertEqual(result, 0.0)

    def test_single_organ_lung(self):
        # lung weight = 0.12, dose = 100 mSv → effective = 12.0 mSv
        result = compute_effective_dose({'lung': 100.0})
        self.assertAlmostEqual(result, 12.0)

    def test_two_organs_additive(self):
        # red_bone_marrow (0.12) + stomach (0.12), each 50 mSv → 12.0 mSv
        result = compute_effective_dose({'red_bone_marrow': 50.0, 'stomach': 50.0})
        self.assertAlmostEqual(result, 12.0)

    def test_partial_weight_below_full_body(self):
        # skin weight = 0.01 — result must be less than input dose
        result = compute_effective_dose({'skin': 200.0})
        self.assertAlmostEqual(result, 2.0)

    def test_unrecognised_tissue_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_dose({'phantom_organ': 10.0})

    def test_negative_dose_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_dose({'lung': -1.0})

    def test_empty_dict_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_dose({})

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_dose([('lung', 10.0)])


class TestEstimateExcessRisk(unittest.TestCase):

    def test_zero_effective_dose_gives_zero_risk(self):
        self.assertEqual(estimate_excess_risk(0.0), 0.0)

    def test_nominal_coefficient_100msv(self):
        # 100 mSv × 5e-4 per mSv = 0.05
        result = estimate_excess_risk(100.0)
        self.assertAlmostEqual(result, 0.05)

    def test_custom_coefficient(self):
        result = estimate_excess_risk(200.0, risk_coeff=1.0e-3)
        self.assertAlmostEqual(result, 0.2)

    def test_negative_dose_raises(self):
        with self.assertRaises(ValueError):
            estimate_excess_risk(-10.0)

    def test_linearity(self):
        r1 = estimate_excess_risk(50.0)
        r2 = estimate_excess_risk(100.0)
        self.assertAlmostEqual(r2, 2 * r1)


class TestCategorizeUncertaintySource(unittest.TestCase):

    def test_dosimetry_measurement_maps_to_dosimetry(self):
        self.assertEqual(categorize_uncertainty_source('dosimetry_measurement'), 'DOSIMETRY')

    def test_rbe_factor_maps_to_biology(self):
        self.assertEqual(categorize_uncertainty_source('rbe_factor'), 'BIOLOGY')

    def test_dose_response_model_maps_to_model(self):
        self.assertEqual(categorize_uncertainty_source('dose_response_model'), 'MODEL')

    def test_population_transfer_maps_to_epidemiology(self):
        self.assertEqual(categorize_uncertainty_source('population_transfer'), 'EPIDEMIOLOGY')

    def test_shielding_transport_maps_to_transport(self):
        self.assertEqual(categorize_uncertainty_source('shielding_transport'), 'TRANSPORT')

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            categorize_uncertainty_source('totally_unknown_source')


class TestComputeRiskBounds(unittest.TestCase):

    def test_upper_above_and_lower_below_point(self):
        lo, hi = compute_risk_bounds(0.01, ['DOSIMETRY'])
        self.assertLess(lo, 0.01)
        self.assertGreater(hi, 0.01)

    def test_bounds_ordered_lower_less_than_upper(self):
        lo, hi = compute_risk_bounds(0.01, ['DOSIMETRY'])
        self.assertLess(lo, hi)

    def test_bounds_symmetric_in_log_space(self):
        lo, hi = compute_risk_bounds(0.01, ['DOSIMETRY'])
        self.assertAlmostEqual(math.log(hi / 0.01), math.log(0.01 / lo), places=10)

    def test_multiple_categories_widens_bounds(self):
        lo_single, hi_single = compute_risk_bounds(0.01, ['DOSIMETRY'])
        lo_multi, hi_multi = compute_risk_bounds(0.01, ['DOSIMETRY', 'BIOLOGY'])
        self.assertLess(lo_multi, lo_single)
        self.assertGreater(hi_multi, hi_single)

    def test_source_labels_accepted_as_well_as_category_names(self):
        lo_by_label, hi_by_label = compute_risk_bounds(0.01, ['dosimetry_measurement'])
        lo_by_cat, hi_by_cat = compute_risk_bounds(0.01, ['DOSIMETRY'])
        self.assertAlmostEqual(lo_by_label, lo_by_cat)
        self.assertAlmostEqual(hi_by_label, hi_by_cat)

    def test_zero_point_risk_returns_zero_bounds(self):
        lo, hi = compute_risk_bounds(0.0, ['DOSIMETRY'])
        self.assertEqual(lo, 0.0)
        self.assertEqual(hi, 0.0)

    def test_negative_point_risk_raises(self):
        with self.assertRaises(ValueError):
            compute_risk_bounds(-0.001, ['DOSIMETRY'])

    def test_empty_sources_raises(self):
        with self.assertRaises(ValueError):
            compute_risk_bounds(0.01, [])

    def test_unknown_source_in_list_raises(self):
        with self.assertRaises(ValueError):
            compute_risk_bounds(0.01, ['DOSIMETRY', 'IMAGINARY_CATEGORY'])


class TestAssessRisk(unittest.TestCase):

    def test_compliant_scenario(self):
        # lung (0.12) + stomach (0.12), each 50 mSv → effective = 12.0 mSv
        # point risk = 12.0 × 5e-4 = 0.006; upper = 0.006 × 1.5 = 0.009 ≤ 0.03
        result = assess_risk({'lung': 50.0, 'stomach': 50.0}, ['DOSIMETRY'], risk_limit=0.03)
        self.assertTrue(result['compliant'])
        self.assertAlmostEqual(result['effective_dose_msv'], 12.0)

    def test_non_compliant_high_dose(self):
        # red_bone_marrow (0.12) × 1000 mSv → effective = 120 mSv
        # point risk = 0.06; upper = 0.09 > 0.03
        result = assess_risk({'red_bone_marrow': 1000.0}, ['DOSIMETRY'], risk_limit=0.03)
        self.assertFalse(result['compliant'])

    def test_result_dict_contains_required_keys(self):
        result = assess_risk({'lung': 10.0}, ['DOSIMETRY'], risk_limit=0.03)
        for key in ('effective_dose_msv', 'point_risk', 'lower_bound', 'upper_bound', 'compliant'):
            self.assertIn(key, result)

    def test_compound_factor_in_result(self):
        result = assess_risk({'lung': 10.0}, ['DOSIMETRY'], risk_limit=0.03)
        self.assertIn('compound_factor', result)
        self.assertAlmostEqual(result['compound_factor'], 1.5)

    def test_upper_bound_is_controlling_quantity(self):
        result = assess_risk({'lung': 10.0}, ['DOSIMETRY'], risk_limit=0.03)
        self.assertLessEqual(result['upper_bound'], result['compound_factor'] * result['point_risk'] + 1e-12)

    def test_multi_category_compound_factor(self):
        # DOSIMETRY (1.5) × BIOLOGY (2.0) = 3.0
        result = assess_risk({'lung': 10.0}, ['DOSIMETRY', 'BIOLOGY'], risk_limit=0.03)
        self.assertAlmostEqual(result['compound_factor'], 3.0)

    def test_custom_risk_coefficient(self):
        result = assess_risk({'lung': 100.0}, ['DOSIMETRY'], risk_limit=0.10,
                             risk_coeff=1.0e-3)
        # effective = 12.0 mSv; point = 12.0 × 1e-3 = 0.012
        self.assertAlmostEqual(result['point_risk'], 0.012)


if __name__ == '__main__':
    unittest.main()

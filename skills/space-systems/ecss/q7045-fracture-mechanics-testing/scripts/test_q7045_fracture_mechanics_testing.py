"""Contract tests for the fracture toughness and crack growth test logic.

The cases read a toughness test the way a reviewer does: whether the crack
sat where the geometry factor is defined, what conditional toughness the load
record gives, whether the thickness, the crack depth and the ligament were
each large enough for that toughness to be a plane-strain material property,
and what the cyclic data supports as a growth law.
"""

import unittest

from q7045_fracture_mechanics_testing_logic import (
    CT_ALPHA_BAND,
    PMAX_PQ_LIMIT,
    assess_fracture_test,
    conditional_toughness,
    ct_geometry_factor,
    fit_paris_law,
    growth_rate_at,
    load_record_findings,
    plane_strain_size_requirement_mm,
    size_findings,
)

FACTOR_AT_HALF = 9.659078631008239
TOUGHNESS = 51.83605540548007
REQUIREMENT_AT_900 = 8.293137777777776
HIGH_YIELD = 900.0
LOW_YIELD = 400.0
PQ = 30000.0


def _growth_points():
    return [
        {"delta_k": 10.0, "rate_m_per_cycle": 1.0e-8},
        {"delta_k": 20.0, "rate_m_per_cycle": 8.0e-8},
        {"delta_k": 40.0, "rate_m_per_cycle": 6.4e-7},
    ]


def _spec(**overrides):
    spec = {
        "load_pq_n": PQ,
        "load_pmax_n": 31000.0,
        "thickness_mm": 25.0,
        "width_mm": 50.0,
        "crack_length_mm": 25.0,
        "yield_strength_mpa": HIGH_YIELD,
    }
    spec.update(overrides)
    return spec


class GeometryTests(unittest.TestCase):
    def test_geometry_factor_at_half_depth(self):
        value = ct_geometry_factor(0.5)
        self.assertAlmostEqual(value / FACTOR_AT_HALF, 1.0, places=9)

    def test_geometry_factor_rises_with_crack_depth(self):
        self.assertGreater(ct_geometry_factor(0.65), ct_geometry_factor(0.50))

    def test_factor_at_the_lower_band_edge_is_defined(self):
        self.assertGreater(ct_geometry_factor(CT_ALPHA_BAND[0]), 0.0)

    def test_factor_at_the_upper_band_edge_is_defined(self):
        self.assertGreater(ct_geometry_factor(CT_ALPHA_BAND[1]), 0.0)

    def test_shallow_crack_outside_the_range_rejected(self):
        with self.assertRaises(ValueError):
            ct_geometry_factor(0.30)

    def test_deep_crack_outside_the_range_rejected(self):
        with self.assertRaises(ValueError):
            ct_geometry_factor(0.80)

    def test_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            ct_geometry_factor(0.0)


class ToughnessTests(unittest.TestCase):
    def test_conditional_toughness_from_the_load_record(self):
        value = conditional_toughness(PQ, 25.0, 50.0, 0.5)
        self.assertAlmostEqual(value / TOUGHNESS, 1.0, places=9)

    def test_toughness_scales_linearly_with_load(self):
        single = conditional_toughness(PQ, 25.0, 50.0, 0.5)
        double = conditional_toughness(2.0 * PQ, 25.0, 50.0, 0.5)
        self.assertAlmostEqual(double / single, 2.0, places=9)

    def test_a_thicker_section_lowers_the_toughness_number(self):
        thin = conditional_toughness(PQ, 25.0, 50.0, 0.5)
        thick = conditional_toughness(PQ, 50.0, 50.0, 0.5)
        self.assertAlmostEqual(thin / (2.0 * thick), 1.0, places=9)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            conditional_toughness(PQ, 0.0, 50.0, 0.5)


class SizeCriterionTests(unittest.TestCase):
    def test_size_requirement_at_high_yield(self):
        value = plane_strain_size_requirement_mm(TOUGHNESS, HIGH_YIELD)
        self.assertAlmostEqual(value / REQUIREMENT_AT_900, 1.0, places=9)

    def test_requirement_scales_with_the_square_of_the_ratio(self):
        strong = plane_strain_size_requirement_mm(TOUGHNESS, HIGH_YIELD)
        weak = plane_strain_size_requirement_mm(TOUGHNESS, HIGH_YIELD / 2.0)
        self.assertAlmostEqual(weak / strong, 4.0, places=9)

    def test_generous_specimen_has_no_size_finding(self):
        self.assertEqual(size_findings(8.0, 25.0, 25.0, 25.0), [])

    def test_length_exactly_at_the_requirement_is_silent(self):
        self.assertEqual(size_findings(10.0, 10.0, 10.0, 10.0), [])

    def test_undersized_specimen_reports_every_controlling_length(self):
        notes = size_findings(42.0, 25.0, 25.0, 25.0)
        self.assertEqual(len(notes), 3)

    def test_only_the_short_ligament_is_reported(self):
        notes = size_findings(20.0, 25.0, 25.0, 10.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("ligament", notes[0])

    def test_zero_ligament_rejected(self):
        with self.assertRaises(ValueError):
            size_findings(8.0, 25.0, 25.0, 0.0)


class LoadRecordTests(unittest.TestCase):
    def test_well_behaved_load_record_is_silent(self):
        self.assertEqual(load_record_findings(PQ, 31000.0), [])

    def test_ratio_exactly_at_the_limit_is_silent(self):
        self.assertEqual(load_record_findings(PQ, PQ * PMAX_PQ_LIMIT), [])

    def test_tearing_record_is_reported(self):
        notes = load_record_findings(PQ, 35000.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("tore", notes[0])

    def test_maximum_below_the_conditional_load_is_reported(self):
        notes = load_record_findings(PQ, 25000.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("not a valid", notes[0])

    def test_zero_conditional_load_rejected(self):
        with self.assertRaises(ValueError):
            load_record_findings(0.0, 31000.0)


class GrowthLawTests(unittest.TestCase):
    def test_growth_law_recovers_the_reference_exponent(self):
        fit = fit_paris_law(_growth_points())
        self.assertAlmostEqual(fit["exponent"], 3.0, places=6)

    def test_growth_law_recovers_the_reference_coefficient(self):
        fit = fit_paris_law(_growth_points())
        self.assertAlmostEqual(fit["log10_coefficient"], -11.0, places=5)

    def test_cycled_range_is_carried_with_the_law(self):
        fit = fit_paris_law(_growth_points())
        self.assertAlmostEqual(fit["delta_k_min"] / 10.0, 1.0, places=9)
        self.assertAlmostEqual(fit["delta_k_max"] / 40.0, 1.0, places=9)

    def test_growth_rate_inside_the_cycled_range(self):
        fit = fit_paris_law(_growth_points())
        self.assertAlmostEqual(growth_rate_at(fit, 20.0) / 8.0e-8, 1.0, places=6)

    def test_growth_rate_outside_the_cycled_range_refused(self):
        fit = fit_paris_law(_growth_points())
        with self.assertRaises(ValueError):
            growth_rate_at(fit, 60.0)

    def test_two_growth_points_rejected(self):
        with self.assertRaises(ValueError):
            fit_paris_law(_growth_points()[:2])

    def test_a_single_cyclic_intensity_rejected(self):
        with self.assertRaises(ValueError):
            fit_paris_law([
                {"delta_k": 20.0, "rate_m_per_cycle": 1.0e-8},
                {"delta_k": 20.0, "rate_m_per_cycle": 2.0e-8},
                {"delta_k": 20.0, "rate_m_per_cycle": 3.0e-8},
            ])

    def test_a_falling_growth_curve_rejected(self):
        with self.assertRaises(ValueError):
            fit_paris_law([
                {"delta_k": 10.0, "rate_m_per_cycle": 6.4e-7},
                {"delta_k": 20.0, "rate_m_per_cycle": 8.0e-8},
                {"delta_k": 40.0, "rate_m_per_cycle": 1.0e-8},
            ])

    def test_missing_growth_key_rejected(self):
        points = _growth_points()
        del points[1]["rate_m_per_cycle"]
        with self.assertRaises(ValueError):
            fit_paris_law(points)

    def test_negative_growth_rate_rejected(self):
        points = _growth_points()
        points[1]["rate_m_per_cycle"] = -1.0e-8
        with self.assertRaises(ValueError):
            fit_paris_law(points)


class AssessmentTests(unittest.TestCase):
    def test_valid_plane_strain_test(self):
        result = assess_fracture_test(_spec())
        self.assertTrue(result["plane_strain_valid"])
        self.assertEqual(result["findings"], [])

    def test_reported_toughness_matches_the_computation(self):
        result = assess_fracture_test(_spec())
        self.assertAlmostEqual(
            result["conditional_toughness"] / TOUGHNESS, 1.0, places=9
        )
        self.assertAlmostEqual(
            result["reportable_toughness"] / TOUGHNESS, 1.0, places=9
        )

    def test_crack_depth_ratio_and_ligament_are_reported(self):
        result = assess_fracture_test(_spec())
        self.assertAlmostEqual(result["crack_depth_ratio"], 0.5, places=9)
        self.assertAlmostEqual(result["remaining_ligament_mm"], 25.0, places=9)

    def test_size_requirement_is_reported(self):
        result = assess_fracture_test(_spec())
        self.assertAlmostEqual(
            result["size_requirement_mm"] / REQUIREMENT_AT_900, 1.0, places=9
        )

    def test_low_yield_strength_invalidates_the_size(self):
        result = assess_fracture_test(_spec(yield_strength_mpa=LOW_YIELD))
        self.assertFalse(result["plane_strain_valid"])
        self.assertEqual(len(result["findings"]), 3)
        self.assertIsNone(result["reportable_toughness"])

    def test_tearing_record_invalidates_the_test(self):
        result = assess_fracture_test(_spec(load_pmax_n=40000.0))
        self.assertFalse(result["plane_strain_valid"])

    def test_growth_points_are_fitted_when_present(self):
        result = assess_fracture_test(_spec(growth_points=_growth_points()))
        self.assertAlmostEqual(result["growth_law"]["exponent"], 3.0, places=6)

    def test_no_growth_points_leaves_the_law_absent(self):
        self.assertIsNone(assess_fracture_test(_spec())["growth_law"])

    def test_crack_deeper_than_the_specimen_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_test(_spec(crack_length_mm=60.0))

    def test_crack_outside_the_geometry_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_test(_spec(crack_length_mm=10.0))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["yield_strength_mpa"]
        with self.assertRaises(ValueError):
            assess_fracture_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_fracture_test(["load_pq_n"])


if __name__ == "__main__":
    unittest.main()

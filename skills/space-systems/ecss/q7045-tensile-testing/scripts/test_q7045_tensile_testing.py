"""Contract tests for the tensile property reduction logic.

The cases read a tension record the way a reviewer does: whether the declared
elastic window is actually elastic, where the offset line crosses the curve,
which point of the curve is the peak, what the broken halves say about
ductility, and whether the reduced properties clear the specified minima.
"""

import unittest

from q7045_tensile_testing_logic import (
    DEFAULT_OFFSET_STRAIN,
    MIN_FIT_QUALITY,
    assess_tensile_test,
    elastic_modulus,
    elongation_after_fracture_pct,
    offset_proof_strength,
    reduction_of_area_pct,
    ultimate_tensile_strength,
    validate_curve,
)

MODULUS = 200000.0
YIELD = 400.0
YIELD_STRAIN = YIELD / MODULUS
PLATEAU_END = 0.020
PEAK_STRAIN = 0.120
PEAK_STRESS = 560.0
BREAK_STRAIN = 0.150
BREAK_STRESS = 520.0

# (strain, stress) corners of the piecewise-linear reference record.
_CORNERS = (
    (0.0, 0.0),
    (YIELD_STRAIN, YIELD),
    (PLATEAU_END, YIELD),
    (PEAK_STRAIN, PEAK_STRESS),
    (BREAK_STRAIN, BREAK_STRESS),
)


def _stress_at(strain):
    for i in range(1, len(_CORNERS)):
        x0, y0 = _CORNERS[i - 1]
        x1, y1 = _CORNERS[i]
        if strain <= x1:
            return y0 + (y1 - y0) * (strain - x0) / (x1 - x0)
    return _CORNERS[-1][1]


def _record(steps=(10, 18, 20, 6)):
    """Return the reference tension record sampled segment by segment."""
    points = [{"strain": 0.0, "stress_mpa": 0.0}]
    for i in range(1, len(_CORNERS)):
        x0 = _CORNERS[i - 1][0]
        x1 = _CORNERS[i][0]
        n = steps[i - 1]
        for k in range(1, n + 1):
            strain = x0 + (x1 - x0) * k / n
            points.append({"strain": strain, "stress_mpa": _stress_at(strain)})
    return points


def _elastic_only():
    return [
        {"strain": YIELD_STRAIN * k / 10.0, "stress_mpa": MODULUS * YIELD_STRAIN * k / 10.0}
        for k in range(0, 11)
    ]


def _spec(**overrides):
    spec = {
        "points": _record(),
        "elastic_window": (0.00015, 0.00185),
        "gauge_initial_mm": 50.0,
        "gauge_final_mm": 57.0,
        "area_initial_mm2": 100.0,
        "area_final_mm2": 40.0,
    }
    spec.update(overrides)
    return spec


class RecordValidationTests(unittest.TestCase):
    def test_reference_record_validates(self):
        self.assertEqual(len(validate_curve(_record())), 55)

    def test_two_point_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([{"strain": 0.0, "stress_mpa": 0.0},
                            {"strain": 0.001, "stress_mpa": 200.0}])

    def test_repeated_strain_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([{"strain": 0.0, "stress_mpa": 0.0},
                            {"strain": 0.001, "stress_mpa": 200.0},
                            {"strain": 0.001, "stress_mpa": 210.0}])

    def test_decreasing_strain_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([{"strain": 0.0, "stress_mpa": 0.0},
                            {"strain": 0.002, "stress_mpa": 400.0},
                            {"strain": 0.001, "stress_mpa": 200.0}])

    def test_negative_stress_rejected(self):
        record = _record()
        record[5]["stress_mpa"] = -1.0
        with self.assertRaises(ValueError):
            validate_curve(record)

    def test_missing_stress_key_rejected(self):
        record = _record()
        del record[4]["stress_mpa"]
        with self.assertRaises(ValueError):
            validate_curve(record)

    def test_boolean_strain_rejected(self):
        record = _record()
        record[2]["strain"] = True
        with self.assertRaises(ValueError):
            validate_curve(record)


class ModulusTests(unittest.TestCase):
    def test_elastic_window_recovers_the_modulus(self):
        fit = elastic_modulus(_record(), (0.00015, 0.00185))
        self.assertAlmostEqual(fit["modulus_mpa"] / MODULUS, 1.0, places=9)

    def test_fit_quality_is_unity_on_the_elastic_branch(self):
        fit = elastic_modulus(_record(), (0.00015, 0.00185))
        self.assertAlmostEqual(fit["fit_quality"], 1.0, places=9)

    def test_window_past_the_knee_degrades_the_fit(self):
        fit = elastic_modulus(_record(), (0.00015, 0.010))
        self.assertLess(fit["fit_quality"], MIN_FIT_QUALITY)

    def test_window_holding_two_points_rejected(self):
        with self.assertRaises(ValueError):
            elastic_modulus(_record(), (0.00015, 0.00045))

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            elastic_modulus(_record(), (0.0018, 0.0002))

    def test_points_used_is_reported(self):
        fit = elastic_modulus(_record(), (0.00015, 0.00185))
        self.assertEqual(fit["points_used"], 9)


class ProofStrengthTests(unittest.TestCase):
    def test_offset_line_crosses_on_the_plateau(self):
        value = offset_proof_strength(_record(), MODULUS)
        self.assertAlmostEqual(value, YIELD, places=9)

    def test_default_offset_is_two_tenths_of_a_percent(self):
        self.assertAlmostEqual(DEFAULT_OFFSET_STRAIN, 0.002, places=9)

    def test_a_large_offset_crosses_on_the_hardening_branch(self):
        value = offset_proof_strength(_record(), MODULUS, 0.020)
        self.assertGreater(value, YIELD + 1.0)

    def test_proof_strength_never_exceeds_the_peak(self):
        value = offset_proof_strength(_record(), MODULUS)
        self.assertLess(value, PEAK_STRESS - 1.0)

    def test_an_unyielded_record_has_no_crossing(self):
        with self.assertRaises(ValueError):
            offset_proof_strength(_elastic_only(), MODULUS)

    def test_non_positive_modulus_rejected(self):
        with self.assertRaises(ValueError):
            offset_proof_strength(_record(), 0.0)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            offset_proof_strength(_record(), MODULUS, -0.002)


class PeakAndDuctilityTests(unittest.TestCase):
    def test_peak_is_not_the_last_point(self):
        peak = ultimate_tensile_strength(_record())
        self.assertAlmostEqual(peak["stress_mpa"], PEAK_STRESS, places=9)
        self.assertAlmostEqual(peak["strain"], PEAK_STRAIN, places=9)

    def test_elongation_after_fracture(self):
        self.assertAlmostEqual(elongation_after_fracture_pct(50.0, 57.0), 14.0, places=9)

    def test_unstretched_gauge_gives_zero_elongation(self):
        self.assertAlmostEqual(elongation_after_fracture_pct(50.0, 50.0), 0.0, places=9)

    def test_shrunken_gauge_rejected(self):
        with self.assertRaises(ValueError):
            elongation_after_fracture_pct(50.0, 49.0)

    def test_zero_gauge_length_rejected(self):
        with self.assertRaises(ValueError):
            elongation_after_fracture_pct(0.0, 57.0)

    def test_reduction_of_area(self):
        self.assertAlmostEqual(reduction_of_area_pct(100.0, 40.0), 60.0, places=9)

    def test_grown_fracture_area_rejected(self):
        with self.assertRaises(ValueError):
            reduction_of_area_pct(100.0, 101.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_test_is_accepted(self):
        result = assess_tensile_test(_spec())
        self.assertTrue(result["properties_accepted"])
        self.assertEqual(result["findings"], [])

    def test_reported_properties_match_the_individual_routines(self):
        result = assess_tensile_test(_spec())
        self.assertAlmostEqual(result["proof_strength_mpa"], YIELD, places=9)
        self.assertAlmostEqual(result["tensile_strength_mpa"], PEAK_STRESS, places=9)
        self.assertAlmostEqual(result["elongation_pct"], 14.0, places=9)
        self.assertAlmostEqual(result["reduction_of_area_pct"], 60.0, places=9)

    def test_uniform_strain_at_peak_is_reported(self):
        result = assess_tensile_test(_spec())
        self.assertAlmostEqual(result["uniform_strain_at_peak"], PEAK_STRAIN, places=9)

    def test_property_exactly_at_the_minimum_is_accepted(self):
        result = assess_tensile_test(
            _spec(minima={"proof_strength_mpa": YIELD,
                          "tensile_strength_mpa": PEAK_STRESS})
        )
        self.assertTrue(result["properties_accepted"])

    def test_proof_strength_below_the_minimum_is_reported(self):
        result = assess_tensile_test(_spec(minima={"proof_strength_mpa": 450.0}))
        self.assertFalse(result["properties_accepted"])
        self.assertIn("proof_strength_mpa", result["findings"][0])

    def test_elongation_below_the_minimum_is_reported(self):
        result = assess_tensile_test(_spec(minima={"elongation_pct": 20.0}))
        self.assertFalse(result["properties_accepted"])

    def test_window_past_the_knee_is_reported_as_a_finding(self):
        result = assess_tensile_test(_spec(elastic_window=(0.00015, 0.010)))
        self.assertFalse(result["properties_accepted"])
        self.assertIn("fit quality", result["findings"][0])

    def test_unmeasured_property_with_a_minimum_is_reported(self):
        spec = _spec(minima={"reduction_of_area_pct": 30.0})
        del spec["area_initial_mm2"]
        del spec["area_final_mm2"]
        result = assess_tensile_test(spec)
        self.assertFalse(result["properties_accepted"])
        self.assertIn("not measured", result["findings"][0])

    def test_unknown_minimum_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_tensile_test(_spec(minima={"toughness_j": 10.0}))

    def test_initial_area_without_final_area_rejected(self):
        spec = _spec()
        del spec["area_final_mm2"]
        with self.assertRaises(ValueError):
            assess_tensile_test(spec)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["gauge_final_mm"]
        with self.assertRaises(ValueError):
            assess_tensile_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tensile_test(["points"])


if __name__ == "__main__":
    unittest.main()

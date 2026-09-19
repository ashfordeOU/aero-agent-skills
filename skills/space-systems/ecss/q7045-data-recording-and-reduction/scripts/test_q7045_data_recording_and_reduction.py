"""Contract tests for the mechanical-test data recording and reduction logic.

The cases run a synthetic force-extension record through the reduction: the
unit registry that refuses an unknown unit, the monotonicity the record has to
hold, the least-squares modulus over a declared elastic window, the offset
line the curve is intersected with, the maximum of the curve, and the
elongation measured on the reassembled specimen.
"""

import math
import unittest

from q7045_data_recording_and_reduction_logic import (
    DEFAULT_OFFSET_STRAIN,
    MIN_CURVE_POINTS,
    convert_force_to_n,
    convert_length_to_mm,
    elongation_after_fracture_pct,
    engineering_curve,
    interpolate_stress,
    least_squares_fit,
    modulus_from_window,
    offset_proof_strength,
    rectangular_cross_section_mm2,
    reduce_test_record,
    round_cross_section_mm2,
    tensile_strength,
    validate_curve,
)

MODULUS_MPA = 70000.0
ELASTIC_END_STRAIN = 0.004
ELASTIC_END_STRESS = MODULUS_MPA * ELASTIC_END_STRAIN
PEAK_STRAIN = 0.05
PEAK_STRESS = 400.0
FINAL_STRAIN = 0.08
FINAL_STRESS = 360.0
DIAMETER_MM = 6.0
GAUGE_LENGTH_MM = 50.0
AREA_MM2 = math.pi * DIAMETER_MM * DIAMETER_MM / 4.0


def _stress_at(strain):
    if strain <= ELASTIC_END_STRAIN:
        return MODULUS_MPA * strain
    if strain <= PEAK_STRAIN:
        fraction = (strain - ELASTIC_END_STRAIN) / (PEAK_STRAIN - ELASTIC_END_STRAIN)
        return ELASTIC_END_STRESS + fraction * (PEAK_STRESS - ELASTIC_END_STRESS)
    fraction = (strain - PEAK_STRAIN) / (FINAL_STRAIN - PEAK_STRAIN)
    return PEAK_STRESS + fraction * (FINAL_STRESS - PEAK_STRESS)


def _record(step=0.0002, last=FINAL_STRAIN):
    points = []
    count = int(round(last / step)) + 1
    for index in range(count):
        strain = index * step
        stress = _stress_at(strain)
        points.append((stress * AREA_MM2, strain * GAUGE_LENGTH_MM))
    return points


def _curve(**kwargs):
    return engineering_curve(_record(**kwargs), AREA_MM2, GAUGE_LENGTH_MM)


def _spec(**overrides):
    spec = {
        "points": _record(),
        "force_unit": "N",
        "length_unit": "mm",
        "gauge_length_mm": GAUGE_LENGTH_MM,
        "diameter_mm": DIAMETER_MM,
        "final_gauge_length_mm": 55.0,
    }
    spec.update(overrides)
    return spec


class UnitRegistryTests(unittest.TestCase):
    def test_kilonewtons_become_newtons(self):
        self.assertAlmostEqual(convert_force_to_n(2.5, "kN"), 2500.0, places=9)

    def test_metres_become_millimetres(self):
        self.assertAlmostEqual(convert_length_to_mm(0.05, "m"), 50.0, places=9)

    def test_micrometres_become_millimetres(self):
        self.assertAlmostEqual(convert_length_to_mm(250.0, "um"), 0.25, places=9)

    def test_unknown_force_unit_refused(self):
        with self.assertRaises(ValueError):
            convert_force_to_n(1.0, "kgf")

    def test_unknown_length_unit_refused(self):
        with self.assertRaises(ValueError):
            convert_length_to_mm(1.0, "inch")

    def test_text_force_value_refused(self):
        with self.assertRaises(ValueError):
            convert_force_to_n("2.5", "kN")


class GeometryTests(unittest.TestCase):
    def test_round_area_from_diameter(self):
        self.assertAlmostEqual(round_cross_section_mm2(10.0), math.pi * 25.0, places=9)

    def test_flat_area_from_width_and_thickness(self):
        self.assertAlmostEqual(rectangular_cross_section_mm2(12.5, 2.0), 25.0, places=9)

    def test_zero_diameter_refused(self):
        with self.assertRaises(ValueError):
            round_cross_section_mm2(0.0)

    def test_negative_thickness_refused(self):
        with self.assertRaises(ValueError):
            rectangular_cross_section_mm2(12.5, -2.0)


class RecordValidationTests(unittest.TestCase):
    def test_a_clean_record_validates(self):
        self.assertEqual(len(validate_curve(_record())), len(_record()))

    def test_a_short_record_is_refused(self):
        with self.assertRaises(ValueError):
            validate_curve(_record()[: MIN_CURVE_POINTS - 1])

    def test_a_rewound_record_is_refused(self):
        points = _record()
        points[20], points[21] = points[21], points[20]
        with self.assertRaises(ValueError):
            validate_curve(points)

    def test_a_duplicated_extension_is_refused(self):
        points = _record()
        points[20] = (points[20][0], points[19][1])
        with self.assertRaises(ValueError):
            validate_curve(points)

    def test_a_negative_force_is_refused(self):
        points = _record()
        points[5] = (-1.0, points[5][1])
        with self.assertRaises(ValueError):
            validate_curve(points)

    def test_a_non_finite_reading_is_refused(self):
        points = _record()
        points[5] = (float("nan"), points[5][1])
        with self.assertRaises(ValueError):
            validate_curve(points)


class FitTests(unittest.TestCase):
    def test_a_straight_line_is_recovered_exactly(self):
        fit = least_squares_fit([(1.0, 3.0), (2.0, 5.0), (3.0, 7.0)])
        self.assertAlmostEqual(fit["slope"], 2.0, places=9)
        self.assertAlmostEqual(fit["intercept"], 1.0, places=9)
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=9)

    def test_scatter_lowers_the_coefficient_of_determination(self):
        fit = least_squares_fit([(1.0, 3.0), (2.0, 4.0), (3.0, 7.0)])
        self.assertLess(fit["r_squared"], 1.0)

    def test_a_two_point_fit_is_refused(self):
        with self.assertRaises(ValueError):
            least_squares_fit([(1.0, 2.0), (2.0, 4.0)])

    def test_a_vertical_fit_is_refused(self):
        with self.assertRaises(ValueError):
            least_squares_fit([(1.0, 2.0), (1.0, 4.0), (1.0, 6.0)])

    def test_the_elastic_window_recovers_the_modulus(self):
        result = modulus_from_window(_curve(), 0.0005, 0.0025)
        self.assertAlmostEqual(result["modulus_gpa"], MODULUS_MPA / 1000.0, places=5)
        self.assertTrue(result["window_acceptable"])

    def test_a_window_running_into_the_plastic_range_bends_the_fit(self):
        result = modulus_from_window(_curve(), 0.0005, 0.01, min_r_squared=0.9999)
        self.assertFalse(result["window_acceptable"])

    def test_an_inverted_window_is_refused(self):
        with self.assertRaises(ValueError):
            modulus_from_window(_curve(), 0.003, 0.001)

    def test_a_window_holding_too_few_points_is_refused(self):
        with self.assertRaises(ValueError):
            modulus_from_window(_curve(), 0.00101, 0.00119)


class CurveReadingTests(unittest.TestCase):
    def test_stress_is_interpolated_between_recorded_points(self):
        value = interpolate_stress(_curve(), 0.0003)
        self.assertAlmostEqual(value, MODULUS_MPA * 0.0003, places=6)

    def test_reading_outside_the_record_is_refused(self):
        with self.assertRaises(ValueError):
            interpolate_stress(_curve(), 0.5)

    def test_the_maximum_of_the_curve_is_the_tensile_strength(self):
        result = tensile_strength(_curve())
        self.assertAlmostEqual(result["stress_mpa"], PEAK_STRESS, places=6)
        self.assertAlmostEqual(result["strain_at_max_force"], PEAK_STRAIN, places=9)

    def test_an_empty_curve_has_no_maximum(self):
        with self.assertRaises(ValueError):
            tensile_strength([])


class ProofStrengthTests(unittest.TestCase):
    def test_the_offset_line_crosses_above_the_elastic_end(self):
        proof = offset_proof_strength(_curve(), MODULUS_MPA)
        self.assertIsNotNone(proof)
        self.assertGreater(proof["stress_mpa"], ELASTIC_END_STRESS)
        self.assertLess(proof["stress_mpa"], PEAK_STRESS)

    def test_the_crossing_sits_beyond_the_offset_strain(self):
        proof = offset_proof_strength(_curve(), MODULUS_MPA)
        self.assertGreater(proof["strain"], DEFAULT_OFFSET_STRAIN)

    def test_a_larger_offset_gives_a_higher_proof_strength(self):
        small = offset_proof_strength(_curve(), MODULUS_MPA, 0.001)
        large = offset_proof_strength(_curve(), MODULUS_MPA, 0.005)
        self.assertGreater(large["stress_mpa"], small["stress_mpa"])

    def test_a_record_stopped_inside_the_elastic_range_reaches_no_offset(self):
        short = _curve(step=0.0002, last=0.0030)
        self.assertIsNone(offset_proof_strength(short, MODULUS_MPA))

    def test_a_non_positive_modulus_is_refused(self):
        with self.assertRaises(ValueError):
            offset_proof_strength(_curve(), 0.0)

    def test_a_non_positive_offset_is_refused(self):
        with self.assertRaises(ValueError):
            offset_proof_strength(_curve(), MODULUS_MPA, 0.0)


class ElongationTests(unittest.TestCase):
    def test_elongation_is_the_permanent_extension_over_the_original(self):
        self.assertAlmostEqual(elongation_after_fracture_pct(55.0, 50.0), 10.0, places=9)

    def test_a_shorter_final_length_is_refused(self):
        with self.assertRaises(ValueError):
            elongation_after_fracture_pct(49.0, 50.0)

    def test_a_zero_original_length_is_refused(self):
        with self.assertRaises(ValueError):
            elongation_after_fracture_pct(55.0, 0.0)


class ReductionTests(unittest.TestCase):
    def test_a_clean_record_reduces_and_reports(self):
        result = reduce_test_record(_spec())
        self.assertTrue(result["reportable"])
        self.assertAlmostEqual(result["modulus"]["modulus_gpa"], 70.0, places=5)
        self.assertAlmostEqual(result["tensile_strength"]["stress_mpa"], PEAK_STRESS, places=6)
        self.assertAlmostEqual(result["elongation_after_fracture_pct"], 10.0, places=9)

    def test_the_proof_strength_never_exceeds_the_tensile_strength(self):
        result = reduce_test_record(_spec())
        self.assertLess(
            result["proof_strength"]["stress_mpa"], result["tensile_strength"]["stress_mpa"]
        )

    def test_kilonewton_input_reduces_to_the_same_properties(self):
        newtons = reduce_test_record(_spec())
        kilo = reduce_test_record(
            _spec(points=[(f / 1000.0, e) for f, e in _record()], force_unit="kN")
        )
        self.assertAlmostEqual(
            kilo["tensile_strength"]["stress_mpa"],
            newtons["tensile_strength"]["stress_mpa"],
            places=6,
        )

    def test_a_flat_specimen_uses_width_and_thickness(self):
        spec = _spec()
        del spec["diameter_mm"]
        spec["width_mm"] = 12.5
        spec["thickness_mm"] = 2.0
        result = reduce_test_record(spec)
        self.assertAlmostEqual(result["area_mm2"], 25.0, places=9)

    def test_a_record_with_no_geometry_is_refused(self):
        spec = _spec()
        del spec["diameter_mm"]
        with self.assertRaises(ValueError):
            reduce_test_record(spec)

    def test_a_record_stopped_early_raises_a_finding(self):
        result = reduce_test_record(_spec(points=_record(last=0.0030), final_gauge_length_mm=None))
        self.assertFalse(result["reportable"])
        self.assertTrue(result["findings"])

    def test_elongation_is_absent_when_the_specimen_was_not_remeasured(self):
        result = reduce_test_record(_spec(final_gauge_length_mm=None))
        self.assertIsNone(result["elongation_after_fracture_pct"])

    def test_a_missing_key_is_refused(self):
        spec = _spec()
        del spec["force_unit"]
        with self.assertRaises(ValueError):
            reduce_test_record(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            reduce_test_record(_record())


if __name__ == "__main__":
    unittest.main()

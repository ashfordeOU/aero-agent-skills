"""Contract tests for the clause 5.2.8.5.1 telemetry offset reference logic."""

import unittest

from e2020_current_telemetry_offset_reference_logic import (
    BASES,
    OFFSET_TOLERANCE,
    assess_offset_reference,
    express_offset,
    normalise_basis,
    offset_from_zero_readings,
    offset_ratio_to_class,
    restate_declaration,
    to_absolute_amps,
    within_allowed_offset,
)

# A 1.5 A class device whose telemetry runs to 4.5 A so it still reads where
# the protection ahead of it limits.
CLASS_A = 1.5
FULL_SCALE_A = 4.5


def _spec(**overrides):
    """Return an offset spec declared the way this clause asks for."""
    spec = {
        "declared_offset": 0.02,
        "declared_basis": "class-current",
        "class_current_a": CLASS_A,
        "allowed_offset_ratio": 0.03,
    }
    spec.update(overrides)
    return spec


class BasisTests(unittest.TestCase):
    def test_spelled_out_class_basis_is_recognised(self):
        self.assertEqual(normalise_basis("% of class current"), "class-current")

    def test_underscored_and_capitalised_spellings_are_recognised(self):
        self.assertEqual(normalise_basis("Class_Current"), "class-current")

    def test_full_scale_abbreviation_is_recognised(self):
        self.assertEqual(normalise_basis("FS"), "full-scale")

    def test_absolute_basis_is_recognised(self):
        self.assertEqual(normalise_basis("amps"), "absolute")

    def test_reading_basis_is_refused_outright(self):
        with self.assertRaises(ValueError):
            normalise_basis("% of reading")

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            normalise_basis("of bus voltage")

    def test_empty_basis_rejected(self):
        with self.assertRaises(ValueError):
            normalise_basis("   ")

    def test_non_string_basis_rejected(self):
        with self.assertRaises(ValueError):
            normalise_basis(None)

    def test_canonical_bases_are_the_declared_three(self):
        self.assertEqual(set(BASES), {"absolute", "class-current", "full-scale"})


class ConversionTests(unittest.TestCase):
    def test_class_basis_scales_by_the_class_current(self):
        self.assertAlmostEqual(
            to_absolute_amps(0.02, "class-current", CLASS_A), 0.03, places=9
        )

    def test_full_scale_basis_scales_by_the_telemetry_full_scale(self):
        self.assertAlmostEqual(
            to_absolute_amps(0.02, "full-scale", CLASS_A, FULL_SCALE_A), 0.09, places=9
        )

    def test_absolute_basis_passes_the_value_through(self):
        self.assertAlmostEqual(
            to_absolute_amps(0.03, "absolute", CLASS_A), 0.03, places=9
        )

    def test_a_negative_offset_keeps_its_sign(self):
        self.assertAlmostEqual(
            to_absolute_amps(-0.02, "class-current", CLASS_A), -0.03, places=9
        )

    def test_full_scale_basis_without_a_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            to_absolute_amps(0.02, "full-scale", CLASS_A)

    def test_zero_class_current_rejected(self):
        with self.assertRaises(ValueError):
            to_absolute_amps(0.02, "class-current", 0.0)

    def test_ratio_is_signed_against_the_class_current(self):
        self.assertAlmostEqual(offset_ratio_to_class(-0.03, CLASS_A), -0.02, places=9)

    def test_expression_names_the_basis_it_used(self):
        expressed = express_offset(0.03, CLASS_A)
        self.assertEqual(expressed["basis"], "class-current")
        self.assertAlmostEqual(expressed["class_percent"], 2.0, places=9)


class RestatementTests(unittest.TestCase):
    def test_a_class_declaration_needs_no_restatement(self):
        record = restate_declaration(0.02, "class-current", CLASS_A)
        self.assertFalse(record["restated"])
        self.assertIsNone(record["understatement_factor"])

    def test_a_full_scale_declaration_is_restated_upwards(self):
        record = restate_declaration(0.02, "full-scale", CLASS_A, FULL_SCALE_A)
        self.assertTrue(record["restated"])
        self.assertAlmostEqual(record["class_ratio"], 0.06, places=9)

    def test_the_understatement_factor_is_the_full_scale_over_class_ratio(self):
        record = restate_declaration(0.02, "full-scale", CLASS_A, FULL_SCALE_A)
        self.assertAlmostEqual(record["understatement_factor"], 3.0, places=9)

    def test_an_absolute_declaration_is_restated_without_a_factor(self):
        record = restate_declaration(0.03, "absolute", CLASS_A)
        self.assertTrue(record["restated"])
        self.assertIsNone(record["understatement_factor"])
        self.assertAlmostEqual(record["class_ratio"], 0.02, places=9)

    def test_the_declared_basis_is_returned_canonicalised(self):
        self.assertEqual(
            restate_declaration(0.02, "Class Current", CLASS_A)["declared_basis"],
            "class-current",
        )


class ZeroReadingTests(unittest.TestCase):
    def test_readings_average_to_the_offset(self):
        settled = offset_from_zero_readings([0.030, 0.031, 0.029])
        self.assertAlmostEqual(settled["offset_a"], 0.030, places=9)
        self.assertEqual(settled["count"], 3)

    def test_spread_is_reported(self):
        settled = offset_from_zero_readings([0.030, 0.031, 0.029])
        self.assertAlmostEqual(settled["spread_a"], 0.002, places=9)

    def test_a_scattered_set_is_refused_against_a_spread_limit(self):
        with self.assertRaises(ValueError):
            offset_from_zero_readings([0.030, 0.031, 0.029], max_spread_a=0.001)

    def test_a_settled_set_passes_its_spread_limit(self):
        settled = offset_from_zero_readings([0.030, 0.0301], max_spread_a=0.001)
        self.assertAlmostEqual(settled["spread_a"], 0.0001, places=9)

    def test_an_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            offset_from_zero_readings([])

    def test_a_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            offset_from_zero_readings([0.03, "0.03"])


class AllowanceTests(unittest.TestCase):
    def test_a_small_offset_sits_inside_its_allowance(self):
        self.assertTrue(within_allowed_offset(0.01, 0.03))

    def test_a_negative_offset_is_judged_on_magnitude(self):
        self.assertFalse(within_allowed_offset(-0.05, 0.03))

    def test_an_offset_exactly_on_the_allowance_is_inside_it(self):
        self.assertTrue(within_allowed_offset(0.05, 0.05))

    def test_a_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            within_allowed_offset(0.01, 0.0)

    def test_offset_tolerance_stays_an_engineering_zero(self):
        self.assertLess(OFFSET_TOLERANCE, 1e-9)


class AssessmentTests(unittest.TestCase):
    def test_a_class_referenced_declaration_inside_allowance_is_compliant(self):
        result = assess_offset_reference(_spec())
        self.assertTrue(result["compliant"])
        self.assertTrue(result["expressed_against_class_current"])
        self.assertEqual(result["findings"], [])

    def test_a_full_scale_declaration_is_never_compliant_as_written(self):
        result = assess_offset_reference(
            _spec(declared_basis="full-scale", full_scale_current_a=FULL_SCALE_A)
        )
        self.assertFalse(result["expressed_against_class_current"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("full scale" in f for f in result["findings"]))

    def test_the_full_scale_restatement_reports_the_factor_it_hid(self):
        result = assess_offset_reference(
            _spec(declared_basis="full-scale", full_scale_current_a=FULL_SCALE_A)
        )
        self.assertAlmostEqual(result["governing_class_ratio"], 0.06, places=9)
        self.assertFalse(result["within_allowance"])

    def test_an_offset_exactly_on_the_allowance_stays_inside_it(self):
        result = assess_offset_reference(
            {
                "declared_offset": 0.05,
                "declared_basis": "class-current",
                "class_current_a": 2.0,
                "allowed_offset_ratio": 0.05,
            }
        )
        self.assertAlmostEqual(result["governing_offset_a"], 0.1, places=9)
        self.assertTrue(result["within_allowance"])
        self.assertTrue(result["compliant"])

    def test_a_negative_offset_inside_allowance_is_compliant(self):
        result = assess_offset_reference(_spec(declared_offset=-0.02))
        self.assertAlmostEqual(result["governing_class_ratio"], -0.02, places=9)
        self.assertTrue(result["compliant"])

    def test_measurements_govern_the_verdict_when_they_are_present(self):
        result = assess_offset_reference(
            _spec(zero_readings=[0.060, 0.060, 0.060])
        )
        self.assertAlmostEqual(result["governing_offset_a"], 0.06, places=9)
        self.assertAlmostEqual(result["governing_class_ratio"], 0.04, places=9)
        self.assertFalse(result["compliant"])

    def test_a_measurement_far_from_the_declaration_is_its_own_finding(self):
        result = assess_offset_reference(
            _spec(zero_readings=[0.060], agreement_a=0.005)
        )
        self.assertTrue(any("from the declared" in f for f in result["findings"]))

    def test_a_measurement_inside_the_agreement_band_raises_no_finding(self):
        result = assess_offset_reference(
            _spec(zero_readings=[0.0302], agreement_a=0.005)
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])

    def test_a_scattered_measurement_set_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_offset_reference(
                _spec(zero_readings=[0.03, 0.05], zero_reading_spread_a=0.001)
            )

    def test_a_reading_referenced_declaration_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_offset_reference(_spec(declared_basis="% of reading"))

    def test_missing_key_rejected(self):
        spec = _spec()
        del spec["declared_basis"]
        with self.assertRaises(ValueError):
            assess_offset_reference(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_offset_reference(["declared_offset"])

    def test_an_allowance_of_a_whole_class_current_rejected(self):
        with self.assertRaises(ValueError):
            assess_offset_reference(_spec(allowed_offset_ratio=1.0))

    def test_a_full_scale_declaration_without_a_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            assess_offset_reference(_spec(declared_basis="full-scale"))


if __name__ == "__main__":
    unittest.main()

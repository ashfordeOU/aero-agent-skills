"""Contract tests for the clause 4.7.5.4.8-4.7.5.4.9 clearance logic."""

import math
import unittest

from e3301_mechanical_mli_clearances_logic import (
    ADJACENT_PART_MIN_CLEARANCE_MM,
    CLEARANCE_TOLERANCE_MM,
    INTERFACE_KINDS,
    MLI_BALLOON_FACTOR,
    MLI_STANDOFF_MM,
    MOVING_PART_MIN_CLEARANCE_MM,
    RSS_MIN_CONTRIBUTIONS,
    assess_clearances,
    assess_interface,
    combine_tolerances_mm,
    mli_envelope_mm,
    required_clearance_mm,
    validate_positive,
    worst_case_clearance_mm,
)


def moving_interface(**overrides):
    record = {
        "name": "boom root to bracket",
        "kind": "moving",
        "nominal_gap_mm": 8.0,
        "tolerances": [0.2, 0.3, 0.15],
        "tolerance_method": "rss",
        "thermal_distortion_mm": 0.6,
        "deflection_mm": 0.4,
        "excursion_mm": 3.0,
    }
    record.update(overrides)
    return record


def mli_interface(**overrides):
    record = {
        "name": "hinge to blanket",
        "kind": "mli",
        "nominal_gap_mm": 20.0,
        "tolerances": [0.5],
        "thermal_distortion_mm": 0.8,
        "blanket_thickness_mm": 6.0,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 4), 4.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -0.1, allow_zero=True)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))

    def test_kind_list_is_the_documented_set(self):
        self.assertEqual(INTERFACE_KINDS, ("moving", "adjacent", "mli"))


class ToleranceStackTests(unittest.TestCase):
    def test_worst_case_is_the_arithmetic_sum(self):
        self.assertAlmostEqual(
            combine_tolerances_mm([0.2, 0.3, 0.15]), 0.65, places=9
        )

    def test_rss_is_below_the_worst_case(self):
        rss = combine_tolerances_mm([0.2, 0.3, 0.15], "rss")
        self.assertLess(rss, combine_tolerances_mm([0.2, 0.3, 0.15]))

    def test_rss_matches_the_closed_form(self):
        self.assertAlmostEqual(
            combine_tolerances_mm([0.3, 0.4, 0.0], "rss"), 0.5, places=9
        )

    def test_empty_stack_is_zero(self):
        self.assertAlmostEqual(combine_tolerances_mm([]), 0.0)

    def test_rss_needs_enough_contributions(self):
        with self.assertRaises(ValueError):
            combine_tolerances_mm([0.2, 0.3], "rss")

    def test_rss_minimum_contribution_count(self):
        self.assertEqual(RSS_MIN_CONTRIBUTIONS, 3)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            combine_tolerances_mm([0.2, 0.3, 0.1], "monte-carlo")

    def test_negative_contribution_rejected(self):
        with self.assertRaises(ValueError):
            combine_tolerances_mm([0.2, -0.3, 0.1])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            combine_tolerances_mm(0.4)


class MliEnvelopeTests(unittest.TestCase):
    def test_default_balloon_factor_doubles_the_thickness(self):
        self.assertAlmostEqual(mli_envelope_mm(6.0), 12.0, places=9)

    def test_balloon_factor_value(self):
        self.assertAlmostEqual(MLI_BALLOON_FACTOR, 2.0)

    def test_balloon_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            mli_envelope_mm(6.0, 0.8)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            mli_envelope_mm(0.0)


class RequiredClearanceTests(unittest.TestCase):
    def test_moving_pair_uses_the_moving_floor(self):
        self.assertAlmostEqual(
            required_clearance_mm("moving"), MOVING_PART_MIN_CLEARANCE_MM
        )

    def test_adjacent_pair_uses_the_lower_floor(self):
        self.assertAlmostEqual(
            required_clearance_mm("adjacent"), ADJACENT_PART_MIN_CLEARANCE_MM
        )

    def test_moving_floor_exceeds_the_adjacent_floor(self):
        self.assertGreater(
            MOVING_PART_MIN_CLEARANCE_MM, ADJACENT_PART_MIN_CLEARANCE_MM
        )

    def test_mli_pair_adds_the_standoff_to_the_inflated_envelope(self):
        self.assertAlmostEqual(
            required_clearance_mm("mli", 6.0), 12.0 + MLI_STANDOFF_MM, places=9
        )

    def test_mli_pair_without_a_thickness_rejected(self):
        with self.assertRaises(ValueError):
            required_clearance_mm("mli")

    def test_override_replaces_the_default(self):
        self.assertAlmostEqual(
            required_clearance_mm("moving", override_mm=7.5), 7.5, places=9
        )

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            required_clearance_mm("magnetic")


class WorstCaseClearanceTests(unittest.TestCase):
    def test_every_term_closes_the_gap(self):
        self.assertAlmostEqual(
            worst_case_clearance_mm(10.0, 0.5, 0.4, 0.3, 2.0), 6.8, places=9
        )

    def test_clean_interface_keeps_its_nominal_gap(self):
        self.assertAlmostEqual(
            worst_case_clearance_mm(10.0, 0.0, 0.0, 0.0, 0.0), 10.0, places=9
        )

    def test_over_closed_gap_goes_negative(self):
        self.assertLess(worst_case_clearance_mm(1.0, 0.5, 0.4, 0.3, 2.0), 0.0)

    def test_zero_nominal_gap_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_clearance_mm(0.0, 0.1, 0.1, 0.1, 0.1)


class InterfaceTests(unittest.TestCase):
    def test_sound_moving_interface_is_compliant(self):
        self.assertTrue(assess_interface(moving_interface())["compliant"])

    def test_mli_interface_carries_the_inflated_requirement(self):
        result = assess_interface(mli_interface())
        self.assertAlmostEqual(result["required_clearance_mm"], 17.0, places=9)

    def test_moving_interface_must_declare_its_excursion(self):
        record = moving_interface()
        del record["excursion_mm"]
        with self.assertRaises(ValueError):
            assess_interface(record)

    def test_zero_excursion_is_an_acceptable_declaration(self):
        result = assess_interface(moving_interface(excursion_mm=0.0))
        self.assertTrue(result["compliant"])

    def test_closed_interface_is_reported_as_contact(self):
        result = assess_interface(moving_interface(nominal_gap_mm=3.0))
        self.assertTrue(result["contact"])
        self.assertFalse(result["compliant"])

    def test_margin_exactly_zero_is_compliant(self):
        record = moving_interface()
        probe = assess_interface(record)
        record["nominal_gap_mm"] = record["nominal_gap_mm"] - probe["margin_mm"]
        result = assess_interface(record)
        self.assertAlmostEqual(result["margin_mm"], 0.0, places=9)
        self.assertLessEqual(abs(result["margin_mm"]), CLEARANCE_TOLERANCE_MM)
        self.assertTrue(result["compliant"])

    def test_unnamed_interface_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface(moving_interface(name="   "))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface(moving_interface(kind="sliding"))

    def test_missing_nominal_gap_rejected(self):
        record = moving_interface()
        del record["nominal_gap_mm"]
        with self.assertRaises(ValueError):
            assess_interface(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface(["name", "kind"])


class AssessmentTests(unittest.TestCase):
    def test_sound_set_reports_no_findings(self):
        result = assess_clearances(
            {"interfaces": [moving_interface(), mli_interface()]}
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_interface_count_is_reported(self):
        result = assess_clearances(
            {"interfaces": [moving_interface(), mli_interface()]}
        )
        self.assertEqual(result["interface_count"], 2)

    def test_governing_interface_is_the_smallest_margin(self):
        tight = mli_interface(name="blanket to yoke", nominal_gap_mm=17.6)
        result = assess_clearances({"interfaces": [moving_interface(), tight]})
        self.assertEqual(result["governing_interface"], "blanket to yoke")

    def test_thin_mli_gap_is_flagged(self):
        result = assess_clearances(
            {"interfaces": [mli_interface(nominal_gap_mm=16.0)]}
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("required" in f for f in result["findings"]))

    def test_contact_is_reported_distinctly(self):
        result = assess_clearances(
            {"interfaces": [moving_interface(nominal_gap_mm=2.0)]}
        )
        self.assertTrue(any("closes to contact" in f for f in result["findings"]))

    def test_duplicate_interface_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances(
                {"interfaces": [moving_interface(), moving_interface()]}
            )

    def test_empty_interface_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances({"interfaces": []})

    def test_missing_interfaces_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_clearances(["interfaces"])

    def test_worst_case_stack_is_tighter_than_rss(self):
        rss = assess_clearances({"interfaces": [moving_interface()]})
        worst = assess_clearances(
            {"interfaces": [moving_interface(tolerance_method="worst-case")]}
        )
        self.assertLess(
            worst["governing_margin_mm"], rss["governing_margin_mm"]
        )

    def test_thicker_blanket_raises_the_requirement(self):
        thin = assess_clearances({"interfaces": [mli_interface(blanket_thickness_mm=4.0)]})
        thick = assess_clearances({"interfaces": [mli_interface(blanket_thickness_mm=8.0)]})
        self.assertGreater(
            thick["interfaces"][0]["required_clearance_mm"],
            thin["interfaces"][0]["required_clearance_mm"],
        )


if __name__ == "__main__":
    unittest.main()

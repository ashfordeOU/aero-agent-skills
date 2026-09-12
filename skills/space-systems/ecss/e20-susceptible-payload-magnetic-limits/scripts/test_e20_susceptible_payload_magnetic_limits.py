#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.7.2 static magnetic
field limits at direct-current-sensitive payload units.

Exercises scripts/e20_susceptible_payload_magnetic_limits_logic.py
(stdlib unittest, offline). Contract: a payload unit kind maps to
exactly one susceptibility group and an unrecognized kind raises; the
allowable static field comes from the provider-declared number when
present and from the group default otherwise; a circuit loop's dipole
moment is turns times area times current while a magnet, remanence or
relay carries a measured moment; the static field falls with the cube
of distance and the axial direction is twice the equatorial one;
contributions combine by direct sum or by root-sum-square; the
comparison is against the allowable field divided by the design margin
factor, with a field sitting exactly on that target treated as
compliant; the minimum separation distance is the cube root of the
moment and orientation factor over the target field; a sensitive unit
carrying sources but no declared limit is a record finding; and the
aggregated review is compliant only when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_susceptible_payload_magnetic_limits_logic as ml  # noqa: E402


def _clean_unit():
    """A star tracker head whose magnetic environment passes every
    clause 6.3.7.2 check."""
    return {
        "unit_id": "PLD-STR-01",
        "unit_kind": "star_tracker_head",
        "declared_limit_nt": 200.0,
        "design_margin_factor": 2.0,
        "combination": "worst_case",
        "sources": [
            {
                "source_id": "MAG-01",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 0.05,
                "distance_m": 1.5,
                "orientation": "axial",
            },
            {
                "source_id": "HRN-01",
                "kind": "current_loop",
                "current_a": 2.0,
                "loop_area_m2": 0.01,
                "turns": 1,
                "distance_m": 1.2,
                "orientation": "equatorial",
            },
        ],
    }


class CategorizeUnitSusceptibilityTest(unittest.TestCase):
    def test_science_magnetometer_is_very_high(self):
        self.assertEqual(
            ml.categorize_unit_susceptibility("science_magnetometer"),
            "very_high",
        )

    def test_atomic_frequency_standard_is_high(self):
        self.assertEqual(
            ml.categorize_unit_susceptibility("atomic_frequency_standard"),
            "high",
        )

    def test_star_tracker_head_is_moderate(self):
        self.assertEqual(
            ml.categorize_unit_susceptibility("star_tracker_head"), "moderate"
        )

    def test_imaging_detector_is_low(self):
        self.assertEqual(
            ml.categorize_unit_susceptibility("imaging_detector"), "low"
        )

    def test_digital_processing_unit_is_negligible(self):
        self.assertEqual(
            ml.categorize_unit_susceptibility("digital_processing_unit"),
            "negligible",
        )

    def test_every_unit_kind_is_categorized_into_a_known_group(self):
        for kind in ml.SUSCEPTIBILITY_BY_UNIT_KIND:
            self.assertIn(
                ml.categorize_unit_susceptibility(kind),
                ml.DEFAULT_ALLOWABLE_STATIC_FIELD_NT,
            )

    def test_unknown_unit_kind_raises(self):
        with self.assertRaises(ValueError):
            ml.categorize_unit_susceptibility("coffee_warmer")

    def test_none_unit_kind_raises(self):
        with self.assertRaises(ValueError):
            ml.categorize_unit_susceptibility(None)


class AllowableStaticFieldTest(unittest.TestCase):
    def test_very_high_group_default(self):
        self.assertAlmostEqual(
            ml.allowable_static_field_nt("very_high"), 1.0, places=12
        )

    def test_moderate_group_default(self):
        self.assertAlmostEqual(
            ml.allowable_static_field_nt("moderate"), 100.0, places=9
        )

    def test_declared_limit_supersedes_the_group_default(self):
        self.assertAlmostEqual(
            ml.allowable_static_field_nt("moderate", 35.0), 35.0, places=9
        )

    def test_defaults_are_monotonic_across_the_groups(self):
        ordered = ["very_high", "high", "moderate", "low", "negligible"]
        values = [ml.DEFAULT_ALLOWABLE_STATIC_FIELD_NT[g] for g in ordered]
        for lower, higher in zip(values, values[1:]):
            self.assertLess(lower, higher)

    def test_unknown_group_raises(self):
        with self.assertRaises(ValueError):
            ml.allowable_static_field_nt("extreme")

    def test_zero_declared_limit_raises(self):
        with self.assertRaises(ValueError):
            ml.allowable_static_field_nt("moderate", 0.0)

    def test_negative_declared_limit_raises(self):
        with self.assertRaises(ValueError):
            ml.allowable_static_field_nt("moderate", -5.0)


class LoopDipoleMomentTest(unittest.TestCase):
    def test_single_turn_moment_is_current_times_area(self):
        self.assertAlmostEqual(
            ml.loop_dipole_moment(2.0, 0.01), 0.02, places=12
        )

    def test_turns_scale_the_moment_linearly(self):
        self.assertAlmostEqual(
            ml.loop_dipole_moment(2.0, 0.01, 5), 0.1, places=12
        )

    def test_reverse_current_gives_the_same_moment_magnitude(self):
        self.assertAlmostEqual(
            ml.loop_dipole_moment(-2.0, 0.01), 0.02, places=12
        )

    def test_zero_area_gives_zero_moment(self):
        self.assertAlmostEqual(ml.loop_dipole_moment(2.0, 0.0), 0.0, places=12)

    def test_negative_area_raises(self):
        with self.assertRaises(ValueError):
            ml.loop_dipole_moment(2.0, -0.01)

    def test_zero_turns_raises(self):
        with self.assertRaises(ValueError):
            ml.loop_dipole_moment(2.0, 0.01, 0)

    def test_non_integer_turns_raises(self):
        with self.assertRaises(ValueError):
            ml.loop_dipole_moment(2.0, 0.01, 2.5)

    def test_non_finite_current_raises(self):
        with self.assertRaises(ValueError):
            ml.loop_dipole_moment(float("inf"), 0.01)


class SourceDipoleMomentTest(unittest.TestCase):
    def test_permanent_magnet_uses_the_measured_moment(self):
        source = {"kind": "permanent_magnet", "dipole_moment_am2": 0.4}
        self.assertAlmostEqual(ml.source_dipole_moment(source), 0.4, places=12)

    def test_magnetorquer_remanence_uses_the_measured_moment(self):
        source = {"kind": "magnetorquer_remanence", "dipole_moment_am2": 0.08}
        self.assertAlmostEqual(
            ml.source_dipole_moment(source), 0.08, places=12
        )

    def test_harness_return_loop_uses_the_loop_geometry(self):
        source = {
            "kind": "harness_return_loop",
            "current_a": 3.0,
            "loop_area_m2": 0.02,
            "turns": 2,
        }
        self.assertAlmostEqual(ml.source_dipole_moment(source), 0.12, places=12)

    def test_loop_turns_default_to_one(self):
        source = {"kind": "current_loop", "current_a": 3.0, "loop_area_m2": 0.02}
        self.assertAlmostEqual(ml.source_dipole_moment(source), 0.06, places=12)

    def test_measured_kind_without_moment_key_raises(self):
        with self.assertRaises(ValueError):
            ml.source_dipole_moment({"kind": "latching_relay"})

    def test_measured_kind_with_none_moment_raises(self):
        with self.assertRaises(ValueError):
            ml.source_dipole_moment(
                {"kind": "latching_relay", "dipole_moment_am2": None}
            )

    def test_negative_measured_moment_raises(self):
        with self.assertRaises(ValueError):
            ml.source_dipole_moment(
                {"kind": "soft_magnetic_remanence", "dipole_moment_am2": -0.1}
            )

    def test_unknown_source_kind_raises(self):
        with self.assertRaises(ValueError):
            ml.source_dipole_moment({"kind": "solar_wind"})


class DipoleStaticFieldTest(unittest.TestCase):
    def test_equatorial_field_of_unit_dipole_at_one_metre(self):
        self.assertAlmostEqual(
            ml.dipole_static_field_nt(1.0, 1.0, "equatorial"), 100.0, places=9
        )

    def test_axial_field_is_twice_the_equatorial_field(self):
        axial = ml.dipole_static_field_nt(1.0, 1.0, "axial")
        equatorial = ml.dipole_static_field_nt(1.0, 1.0, "equatorial")
        self.assertAlmostEqual(axial, 2.0 * equatorial, places=9)

    def test_worst_case_orientation_equals_the_axial_case(self):
        self.assertAlmostEqual(
            ml.dipole_static_field_nt(0.3, 2.0, "worst_case"),
            ml.dipole_static_field_nt(0.3, 2.0, "axial"),
            places=12,
        )

    def test_field_falls_with_the_cube_of_distance(self):
        near = ml.dipole_static_field_nt(1.0, 1.0, "axial")
        far = ml.dipole_static_field_nt(1.0, 2.0, "axial")
        self.assertAlmostEqual(far, near / 8.0, places=9)

    def test_zero_moment_gives_zero_field(self):
        self.assertAlmostEqual(
            ml.dipole_static_field_nt(0.0, 1.0, "axial"), 0.0, places=12
        )

    def test_negative_moment_raises(self):
        with self.assertRaises(ValueError):
            ml.dipole_static_field_nt(-1.0, 1.0)

    def test_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            ml.dipole_static_field_nt(1.0, 0.0)

    def test_unknown_orientation_raises(self):
        with self.assertRaises(ValueError):
            ml.dipole_static_field_nt(1.0, 1.0, "sideways")


class CombineFieldContributionsTest(unittest.TestCase):
    def test_worst_case_sums_the_contributions(self):
        self.assertAlmostEqual(
            ml.combine_field_contributions([1.0, 2.0, 3.0], "worst_case"),
            6.0,
            places=12,
        )

    def test_root_sum_square_combines_independent_sources(self):
        self.assertAlmostEqual(
            ml.combine_field_contributions([3.0, 4.0], "root_sum_square"),
            5.0,
            places=12,
        )

    def test_root_sum_square_never_exceeds_the_worst_case_sum(self):
        values = [1.0, 2.5, 0.75, 4.0]
        self.assertLess(
            ml.combine_field_contributions(values, "root_sum_square"),
            ml.combine_field_contributions(values, "worst_case"),
        )

    def test_empty_inventory_gives_zero(self):
        self.assertAlmostEqual(
            ml.combine_field_contributions([], "worst_case"), 0.0, places=12
        )

    def test_single_contribution_is_identical_under_both_rules(self):
        self.assertAlmostEqual(
            ml.combine_field_contributions([7.0], "worst_case"),
            ml.combine_field_contributions([7.0], "root_sum_square"),
            places=12,
        )

    def test_unknown_combination_rule_raises(self):
        with self.assertRaises(ValueError):
            ml.combine_field_contributions([1.0], "average")

    def test_negative_contribution_raises(self):
        with self.assertRaises(ValueError):
            ml.combine_field_contributions([1.0, -1.0], "worst_case")


class MarginedFieldLimitTest(unittest.TestCase):
    def test_margin_factor_divides_the_allowable_field(self):
        self.assertAlmostEqual(
            ml.margined_field_limit_nt(100.0, 2.0), 50.0, places=12
        )

    def test_unity_margin_leaves_the_limit_untouched(self):
        self.assertAlmostEqual(
            ml.margined_field_limit_nt(100.0, 1.0), 100.0, places=12
        )

    def test_default_margin_factor_is_applied(self):
        self.assertAlmostEqual(
            ml.margined_field_limit_nt(100.0),
            100.0 / ml.DEFAULT_DESIGN_MARGIN_FACTOR,
            places=12,
        )

    def test_margin_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            ml.margined_field_limit_nt(100.0, 0.5)

    def test_non_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            ml.margined_field_limit_nt(0.0, 2.0)


class MinimumSeparationDistanceTest(unittest.TestCase):
    def test_unit_dipole_needs_one_metre_for_a_hundred_nanotesla(self):
        self.assertAlmostEqual(
            ml.minimum_separation_distance_m(1.0, 100.0, "equatorial"),
            1.0,
            places=9,
        )

    def test_axial_case_needs_the_cube_root_of_two_more_distance(self):
        axial = ml.minimum_separation_distance_m(1.0, 100.0, "axial")
        self.assertAlmostEqual(axial, 2.0 ** (1.0 / 3.0), places=9)

    def test_distance_and_field_are_mutually_consistent(self):
        distance = ml.minimum_separation_distance_m(0.35, 12.0, "axial")
        self.assertAlmostEqual(
            ml.dipole_static_field_nt(0.35, distance, "axial"), 12.0, places=6
        )

    def test_zero_moment_needs_no_separation(self):
        self.assertAlmostEqual(
            ml.minimum_separation_distance_m(0.0, 5.0), 0.0, places=12
        )

    def test_halving_the_target_field_moves_the_source_by_a_cube_root(self):
        near = ml.minimum_separation_distance_m(1.0, 100.0, "axial")
        far = ml.minimum_separation_distance_m(1.0, 50.0, "axial")
        self.assertAlmostEqual(far / near, 2.0 ** (1.0 / 3.0), places=9)

    def test_negative_moment_raises(self):
        with self.assertRaises(ValueError):
            ml.minimum_separation_distance_m(-1.0, 100.0)

    def test_zero_target_field_raises(self):
        with self.assertRaises(ValueError):
            ml.minimum_separation_distance_m(1.0, 0.0)

    def test_unknown_orientation_raises(self):
        with self.assertRaises(ValueError):
            ml.minimum_separation_distance_m(1.0, 100.0, "diagonal")


class FieldMarginFindingsTest(unittest.TestCase):
    def test_field_well_inside_the_margined_limit_is_clean(self):
        self.assertEqual(
            ml.field_margin_findings("U1", 10.0, 100.0, 2.0), []
        )

    def test_field_exactly_on_the_margined_target_is_compliant(self):
        self.assertEqual(ml.field_margin_findings("U1", 50.0, 100.0, 2.0), [])

    def test_field_between_the_target_and_the_bare_limit_is_a_finding(self):
        findings = ml.field_margin_findings("U1", 80.0, 100.0, 2.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "static_field_exceeds_margined_limit"
        )
        self.assertAlmostEqual(findings[0]["target_nt"], 50.0, places=12)

    def test_representation_error_on_the_target_is_absorbed(self):
        # 0.1 + 0.2 is a few units in the last place above 0.3; the
        # sum sits on the margined target of 0.6 / 2.0 and is
        # physically compliant.
        self.assertEqual(
            ml.field_margin_findings("U1", 0.1 + 0.2, 0.6, 2.0), []
        )

    def test_negative_field_raises(self):
        with self.assertRaises(ValueError):
            ml.field_margin_findings("U1", -1.0, 100.0, 2.0)

    def test_bad_margin_factor_propagates_the_error(self):
        with self.assertRaises(ValueError):
            ml.field_margin_findings("U1", 10.0, 100.0, 0.25)


class SeparationFindingsTest(unittest.TestCase):
    def test_source_beyond_its_required_distance_is_clean(self):
        sources = [
            {
                "source_id": "M1",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 1.0,
                "distance_m": 2.0,
                "orientation": "equatorial",
            }
        ]
        self.assertEqual(ml.separation_findings("U1", sources, 100.0), [])

    def test_source_exactly_at_its_required_distance_is_compliant(self):
        sources = [
            {
                "source_id": "M1",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 1.0,
                "distance_m": 1.0,
                "orientation": "equatorial",
            }
        ]
        self.assertEqual(ml.separation_findings("U1", sources, 100.0), [])

    def test_source_inside_its_required_distance_is_a_finding(self):
        sources = [
            {
                "source_id": "M1",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 1.0,
                "distance_m": 0.4,
                "orientation": "equatorial",
            }
        ]
        findings = ml.separation_findings("U1", sources, 100.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "source_below_minimum_separation_distance"
        )
        self.assertAlmostEqual(
            findings[0]["required_distance_m"], 1.0, places=9
        )

    def test_each_offending_source_yields_its_own_finding(self):
        sources = [
            {
                "source_id": "M1",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 1.0,
                "distance_m": 0.4,
                "orientation": "equatorial",
            },
            {
                "source_id": "M2",
                "kind": "latching_relay",
                "dipole_moment_am2": 0.5,
                "distance_m": 0.2,
                "orientation": "axial",
            },
        ]
        findings = ml.separation_findings("U1", sources, 100.0)
        self.assertEqual(
            [f["source"] for f in findings], ["M1", "M2"]
        )

    def test_non_positive_distance_raises(self):
        sources = [
            {
                "source_id": "M1",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 1.0,
                "distance_m": 0.0,
            }
        ]
        with self.assertRaises(ValueError):
            ml.separation_findings("U1", sources, 100.0)


class UnitFieldReviewTest(unittest.TestCase):
    def test_clean_unit_has_no_findings_anywhere(self):
        review = ml.unit_field_review(_clean_unit())
        self.assertEqual(review["field"], [])
        self.assertEqual(review["separation"], [])
        self.assertEqual(review["record"], [])
        self.assertTrue(ml.is_unit_compliant(review))

    def test_review_returns_the_three_expected_finding_lists(self):
        review = ml.unit_field_review(_clean_unit())
        self.assertEqual(
            sorted(review.keys()), ["field", "record", "separation"]
        )

    def test_dominant_source_breaches_both_field_and_separation(self):
        unit = _clean_unit()
        unit["sources"][0]["dipole_moment_am2"] = 50.0
        unit["sources"][0]["distance_m"] = 0.3
        review = ml.unit_field_review(unit)
        self.assertEqual(len(review["field"]), 1)
        self.assertEqual(len(review["separation"]), 1)
        self.assertFalse(ml.is_unit_compliant(review))

    def test_sensitive_unit_without_a_declared_limit_is_a_record_finding(self):
        unit = _clean_unit()
        unit["declared_limit_nt"] = None
        review = ml.unit_field_review(unit)
        self.assertEqual(len(review["record"]), 1)
        self.assertEqual(
            review["record"][0]["issue"], "unit_allowable_field_not_on_record"
        )
        self.assertFalse(ml.is_unit_compliant(review))

    def test_negligible_unit_without_a_declared_limit_is_accepted(self):
        unit = _clean_unit()
        unit["unit_kind"] = "digital_processing_unit"
        unit["declared_limit_nt"] = None
        review = ml.unit_field_review(unit)
        self.assertEqual(review["record"], [])
        self.assertTrue(ml.is_unit_compliant(review))

    def test_sensitive_unit_with_no_sources_raises_no_record_finding(self):
        unit = _clean_unit()
        unit["declared_limit_nt"] = None
        unit["sources"] = []
        review = ml.unit_field_review(unit)
        self.assertEqual(review["record"], [])
        self.assertTrue(ml.is_unit_compliant(review))

    def test_root_sum_square_can_clear_a_worst_case_breach(self):
        unit = _clean_unit()
        unit["declared_limit_nt"] = 6.0
        unit["design_margin_factor"] = 1.0
        unit["sources"] = [
            {
                "source_id": "A",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 0.03,
                "distance_m": 1.0,
                "orientation": "equatorial",
            },
            {
                "source_id": "B",
                "kind": "permanent_magnet",
                "dipole_moment_am2": 0.04,
                "distance_m": 1.0,
                "orientation": "equatorial",
            },
        ]
        unit["combination"] = "worst_case"
        self.assertEqual(len(ml.unit_field_review(unit)["field"]), 1)
        unit["combination"] = "root_sum_square"
        self.assertEqual(ml.unit_field_review(unit)["field"], [])

    def test_review_does_not_mutate_the_input_unit(self):
        unit = _clean_unit()
        snapshot = repr(unit)
        ml.unit_field_review(unit)
        self.assertEqual(repr(unit), snapshot)

    def test_unrecognized_unit_kind_raises_through_the_review(self):
        unit = _clean_unit()
        unit["unit_kind"] = "thermostat"
        with self.assertRaises(ValueError):
            ml.unit_field_review(unit)

    def test_unrecognized_source_kind_raises_through_the_review(self):
        unit = _clean_unit()
        unit["sources"][1]["kind"] = "cosmic_ray"
        with self.assertRaises(ValueError):
            ml.unit_field_review(unit)

    def test_default_margin_factor_is_used_when_absent(self):
        unit = _clean_unit()
        del unit["design_margin_factor"]
        unit["declared_limit_nt"] = 4.0
        review = ml.unit_field_review(unit)
        self.assertEqual(len(review["field"]), 1)
        self.assertAlmostEqual(
            review["field"][0]["margin_factor"],
            ml.DEFAULT_DESIGN_MARGIN_FACTOR,
            places=12,
        )

    def test_worst_case_total_matches_the_hand_computed_sum(self):
        unit = _clean_unit()
        expected = 100.0 * 2.0 * 0.05 / (1.5 ** 3) + 100.0 * 1.0 * 0.02 / (
            1.2 ** 3
        )
        unit["declared_limit_nt"] = 1.0
        unit["design_margin_factor"] = 1.0
        review = ml.unit_field_review(unit)
        self.assertAlmostEqual(
            review["field"][0]["field_nt"], expected, places=9
        )

    def test_compliance_helper_rejects_any_non_empty_list(self):
        self.assertFalse(
            ml.is_unit_compliant(
                {"field": [], "separation": [{"issue": "x"}], "record": []}
            )
        )

    def test_boundary_tolerance_is_small_and_positive(self):
        self.assertGreater(ml.BOUNDARY_REL_TOL, 0.0)
        self.assertLess(ml.BOUNDARY_REL_TOL, 1e-6)
        self.assertTrue(math.isfinite(ml.BOUNDARY_REL_TOL))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.1.2 interference
critical point list.

Exercises scripts/e20_interference_critical_point_list_logic.py (stdlib
unittest, offline). Contract: a named coupling path maps to exactly one
family and an unrecognized path raises; the selection rule gives the
safety group a point on every family, the mission group a discharge
point only where the circuit is externally exposed, the essential group
the conducted and radiated families and the non essential group none;
candidate derivation is deterministic and rejects a repeated victim; a
listed point reports its absent mandatory fields rather than raising;
a separation exactly on its limit passes even when the decibel
subtraction lands a few units in the last place below it; two bands
that meet at the same edge reached by different arithmetic merge
instead of leaving a nanohertz hole; and the aggregate review is
compliant only when every finding list is empty and the customer has
approved.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_interference_critical_point_list_logic as ip  # noqa: E402

# The same 33 MHz edge reached two ways: the tabulated band limit, and
# the 30 MHz conducted limit carried up by the ten percent band overlap
# the project requires. The second evaluates a few units in the last
# place above the first.
_UPPER_CONDUCTED_HZ = 33e6
_LOWER_RADIATED_HZ = 30e6 * 1.1


def _point(point_id, victim, path, band, margin=6.0, threshold=54.0, emission=40.0):
    return {
        "point_id": point_id,
        "victim_circuit_id": victim,
        "coupling_path": path,
        "frequency_band_hz": band,
        "demonstration_method": "emc_measurement",
        "required_margin_db": margin,
        "responsible_party": "supplier-emc",
        "demonstrated": {
            "susceptibility_threshold_dbuv": threshold,
            "emission_level_dbuv": emission,
        },
    }


def _victims():
    return [
        {
            "circuit_id": "PYRO-ARM-01",
            "criticality_category": "safety_critical",
            "externally_exposed": True,
        },
        {"circuit_id": "TC-DEC-01", "criticality_category": "mission_critical"},
        {"circuit_id": "HTR-SW-01", "criticality_category": "essential"},
        {"circuit_id": "HK-TEMP-07", "criticality_category": "non_essential"},
    ]


def _clean_package():
    """A point list that covers every required point and the whole
    project spectrum span, and that the customer has approved."""
    low_band = (10.0, _UPPER_CONDUCTED_HZ)
    high_band = (_LOWER_RADIATED_HZ, 18e9)
    return {
        "victims": _victims(),
        "points": [
            _point("ICP-01", "PYRO-ARM-01", "conducted_emission", low_band, 20.0, 62.0, 40.0),
            _point("ICP-02", "PYRO-ARM-01", "radiated_susceptibility", high_band, 20.0, 62.0, 40.0),
            _point("ICP-03", "PYRO-ARM-01", "common_impedance_coupling", low_band, 20.0, 62.0, 40.0),
            _point("ICP-04", "PYRO-ARM-01", "electrostatic_discharge", high_band, 20.0, 62.0, 40.0),
            _point("ICP-05", "TC-DEC-01", "conducted_susceptibility", low_band, 12.0, 54.0, 40.0),
            _point("ICP-06", "TC-DEC-01", "radiated_susceptibility", high_band, 12.0, 54.0, 40.0),
            _point("ICP-07", "TC-DEC-01", "common_impedance_coupling", low_band, 12.0, 54.0, 40.0),
            _point("ICP-08", "HTR-SW-01", "conducted_emission", low_band, 6.0, 33.3, 27.3),
            _point("ICP-09", "HTR-SW-01", "radiated_emission", high_band, 6.0, 40.0, 30.0),
        ],
        "spectrum_span_hz": (10.0, 18e9),
        "submitted_on": "2026-03-02",
        "approved_on": "2026-03-20",
        "approving_customer": "prime-contractor-emc-office",
    }


class CouplingPathTest(unittest.TestCase):
    def test_conducted_emission_is_a_conducted_path(self):
        self.assertEqual(ip.categorize_coupling_path("conducted_emission"), "conducted")

    def test_conducted_susceptibility_shares_the_conducted_family(self):
        self.assertEqual(
            ip.categorize_coupling_path("conducted_susceptibility"), "conducted"
        )

    def test_radiated_emission_is_a_radiated_path(self):
        self.assertEqual(ip.categorize_coupling_path("radiated_emission"), "radiated")

    def test_common_impedance_has_its_own_family(self):
        self.assertEqual(
            ip.categorize_coupling_path("common_impedance_coupling"),
            "common_impedance",
        )

    def test_discharge_has_its_own_family(self):
        self.assertEqual(
            ip.categorize_coupling_path("electrostatic_discharge"),
            "electrostatic_discharge",
        )

    def test_every_mapped_path_lands_in_a_known_family(self):
        for family in ip.COUPLING_PATH_FAMILY.values():
            self.assertIn(family, ip.COUPLING_PATH_FAMILIES)

    def test_unknown_path_raises(self):
        with self.assertRaises(ValueError):
            ip.categorize_coupling_path("thermal_gradient")

    def test_none_path_raises(self):
        with self.assertRaises(ValueError):
            ip.categorize_coupling_path(None)


class DemonstrationMethodTest(unittest.TestCase):
    def test_measurement_gives_measured_evidence(self):
        self.assertEqual(
            ip.categorize_demonstration_method("emc_measurement"), "measured"
        )

    def test_coupling_analysis_gives_analytical_evidence(self):
        self.assertEqual(
            ip.categorize_demonstration_method("coupling_analysis"), "analytical"
        )

    def test_similarity_gives_heritage_evidence(self):
        self.assertEqual(
            ip.categorize_demonstration_method("similarity_to_qualified_unit"),
            "heritage",
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            ip.categorize_demonstration_method("engineering_judgement")


class FrequencyBandTest(unittest.TestCase):
    def test_a_rising_band_normalizes_to_floats(self):
        band = ip.validate_frequency_band((10, 1000))
        self.assertAlmostEqual(band[0], 10.0, places=9)
        self.assertAlmostEqual(band[1], 1000.0, places=9)

    def test_a_band_may_start_at_direct_current(self):
        self.assertAlmostEqual(ip.validate_frequency_band((0, 100))[0], 0.0, places=9)

    def test_a_single_value_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band(1000.0)

    def test_a_three_edge_band_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band((10.0, 100.0, 1000.0))

    def test_a_negative_low_edge_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band((-10.0, 100.0))

    def test_a_flat_band_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band((100.0, 100.0))

    def test_a_descending_band_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band((1000.0, 10.0))

    def test_a_non_finite_edge_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band((10.0, float("inf")))

    def test_a_string_edge_raises(self):
        with self.assertRaises(ValueError):
            ip.validate_frequency_band(("10", 100.0))


class PointSelectionTest(unittest.TestCase):
    def test_safety_victim_needs_a_point_on_every_family(self):
        for family in ip.COUPLING_PATH_FAMILIES:
            self.assertTrue(ip.point_selection_required("safety_critical", family))

    def test_mission_victim_needs_the_conducted_family(self):
        self.assertTrue(ip.point_selection_required("mission_critical", "conducted"))

    def test_sheltered_mission_victim_needs_no_discharge_point(self):
        self.assertFalse(
            ip.point_selection_required(
                "mission_critical", "electrostatic_discharge", False
            )
        )

    def test_exposed_mission_victim_needs_a_discharge_point(self):
        self.assertTrue(
            ip.point_selection_required(
                "mission_critical", "electrostatic_discharge", True
            )
        )

    def test_essential_victim_needs_conducted_and_radiated_only(self):
        self.assertTrue(ip.point_selection_required("essential", "radiated"))
        self.assertFalse(ip.point_selection_required("essential", "common_impedance"))

    def test_non_essential_victim_needs_no_point(self):
        for family in ip.COUPLING_PATH_FAMILIES:
            self.assertFalse(ip.point_selection_required("non_essential", family))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            ip.point_selection_required("quite_important", "conducted")

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            ip.point_selection_required("safety_critical", "magnetic_static")

    def test_non_boolean_exposure_raises(self):
        with self.assertRaises(ValueError):
            ip.point_selection_required("mission_critical", "conducted", "yes")


class CandidatePointTest(unittest.TestCase):
    def test_the_victim_inventory_yields_nine_candidates(self):
        self.assertEqual(len(ip.derive_candidate_points(_victims())), 9)

    def test_candidates_are_ordered_by_point_identifier(self):
        ids = [c["point_id"] for c in ip.derive_candidate_points(_victims())]
        self.assertEqual(ids, sorted(ids))

    def test_the_non_essential_victim_contributes_nothing(self):
        victims = ip.derive_candidate_points(_victims())
        self.assertNotIn(
            "HK-TEMP-07", {c["victim_circuit_id"] for c in victims}
        )

    def test_derivation_is_repeatable(self):
        self.assertEqual(
            ip.derive_candidate_points(_victims()),
            ip.derive_candidate_points(_victims()),
        )

    def test_duplicate_victim_raises(self):
        victims = _victims()
        victims.append({"circuit_id": "TC-DEC-01", "criticality_category": "essential"})
        with self.assertRaises(ValueError):
            ip.derive_candidate_points(victims)

    def test_victim_without_a_category_raises(self):
        with self.assertRaises(ValueError):
            ip.derive_candidate_points([{"circuit_id": "C-1"}])

    def test_empty_victim_identifier_raises(self):
        with self.assertRaises(ValueError):
            ip.derive_candidate_points(
                [{"circuit_id": "  ", "criticality_category": "essential"}]
            )

    def test_mapping_instead_of_a_list_raises(self):
        with self.assertRaises(ValueError):
            ip.derive_candidate_points({"circuit_id": "C-1"})


class PointRecordTest(unittest.TestCase):
    def test_a_complete_point_has_no_record_finding(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        self.assertEqual(ip.point_record_findings(point), [])

    def test_a_missing_responsible_party_is_reported(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        del point["responsible_party"]
        findings = ip.point_record_findings(point)
        self.assertEqual(len(findings), 1)
        self.assertIn("responsible_party", findings[0])

    def test_a_field_left_as_none_counts_as_absent(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        point["demonstration_method"] = None
        self.assertTrue(
            any("demonstration_method" in f for f in ip.point_record_findings(point))
        )

    def test_a_blank_string_field_counts_as_absent(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        point["responsible_party"] = "   "
        self.assertEqual(len(ip.point_record_findings(point)), 1)

    def test_an_unrecognized_coupling_path_is_reported_not_raised(self):
        point = _point("ICP-01", "C-1", "thermal_gradient", (10.0, 1e6))
        self.assertTrue(
            any("coupling path" in f for f in ip.point_record_findings(point))
        )

    def test_a_malformed_band_is_reported_not_raised(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (1e6, 10.0))
        self.assertTrue(any("edge" in f for f in ip.point_record_findings(point)))

    def test_a_negative_required_margin_is_reported(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6), -3.0)
        self.assertTrue(
            any("required_margin_db" in f for f in ip.point_record_findings(point))
        )

    def test_a_non_numeric_required_margin_is_reported(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        point["required_margin_db"] = "6 dB"
        self.assertTrue(
            any("real number" in f for f in ip.point_record_findings(point))
        )

    def test_a_non_mapping_point_raises(self):
        with self.assertRaises(ValueError):
            ip.point_record_findings(["ICP-01"])


class DemonstratedMarginTest(unittest.TestCase):
    def test_margin_is_threshold_less_emission(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        self.assertAlmostEqual(ip.demonstrated_margin_db(point), 14.0, places=9)

    def test_a_point_without_demonstrated_levels_raises(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        del point["demonstrated"]
        with self.assertRaises(ValueError):
            ip.demonstrated_margin_db(point)

    def test_a_demonstrated_mapping_missing_a_level_raises(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        del point["demonstrated"]["emission_level_dbuv"]
        with self.assertRaises(ValueError):
            ip.demonstrated_margin_db(point)

    def test_a_non_finite_level_raises(self):
        point = _point("ICP-01", "C-1", "conducted_emission", (10.0, 1e6))
        point["demonstrated"]["emission_level_dbuv"] = float("nan")
        with self.assertRaises(ValueError):
            ip.demonstrated_margin_db(point)

    def test_a_non_mapping_point_raises(self):
        with self.assertRaises(ValueError):
            ip.demonstrated_margin_db("ICP-01")


class MarginRequirementTest(unittest.TestCase):
    def test_a_comfortable_separation_passes(self):
        self.assertTrue(ip.margin_meets_requirement(14.0, 12.0))

    def test_a_clear_shortfall_fails(self):
        self.assertFalse(ip.margin_meets_requirement(4.0, 6.0))

    def test_an_exact_limit_passes(self):
        self.assertTrue(ip.margin_meets_requirement(6.0, 6.0))

    def test_representation_error_below_the_limit_is_absorbed(self):
        separation = 33.3 - 27.3
        self.assertLess(separation, 6.0)
        self.assertTrue(ip.margin_meets_requirement(separation, 6.0))

    def test_the_tolerance_does_not_widen_the_requirement(self):
        self.assertFalse(ip.margin_meets_requirement(6.0 - 1e-3, 6.0))

    def test_a_non_finite_separation_raises(self):
        with self.assertRaises(ValueError):
            ip.margin_meets_requirement(float("inf"), 6.0)

    def test_a_string_requirement_raises(self):
        with self.assertRaises(ValueError):
            ip.margin_meets_requirement(6.0, "6")


class MergeBandsTest(unittest.TestCase):
    def test_disjoint_bands_stay_apart(self):
        merged = ip.merge_bands([(10.0, 100.0), (1000.0, 2000.0)])
        self.assertEqual(len(merged), 2)

    def test_overlapping_bands_merge(self):
        merged = ip.merge_bands([(10.0, 1000.0), (500.0, 2000.0)])
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0][1], 2000.0, places=9)

    def test_bands_are_merged_regardless_of_input_order(self):
        self.assertEqual(
            ip.merge_bands([(500.0, 2000.0), (10.0, 1000.0)]),
            ip.merge_bands([(10.0, 1000.0), (500.0, 2000.0)]),
        )

    def test_a_contained_band_is_absorbed(self):
        merged = ip.merge_bands([(10.0, 1e9), (1e3, 1e6)])
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0][1], 1e9, places=3)

    def test_the_same_edge_reached_by_different_arithmetic_still_joins(self):
        self.assertGreater(_LOWER_RADIATED_HZ, _UPPER_CONDUCTED_HZ)
        merged = ip.merge_bands(
            [(10.0, _UPPER_CONDUCTED_HZ), (_LOWER_RADIATED_HZ, 18e9)]
        )
        self.assertEqual(len(merged), 1)

    def test_a_real_hole_is_not_merged_away(self):
        merged = ip.merge_bands([(10.0, 30e6), (60e6, 18e9)])
        self.assertEqual(len(merged), 2)

    def test_a_malformed_band_raises(self):
        with self.assertRaises(ValueError):
            ip.merge_bands([(10.0, 100.0), (200.0, 150.0)])

    def test_a_mapping_of_bands_raises(self):
        with self.assertRaises(ValueError):
            ip.merge_bands({"low": 10.0, "high": 100.0})


class CoverageGapTest(unittest.TestCase):
    def test_a_full_cover_leaves_no_gap(self):
        self.assertEqual(ip.coverage_gaps([(10.0, 1e9)], (10.0, 1e9)), ())

    def test_a_hole_in_the_middle_is_reported(self):
        gaps = ip.coverage_gaps([(10.0, 30e6), (60e6, 18e9)], (10.0, 18e9))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 30e6, places=3)
        self.assertAlmostEqual(gaps[0][1], 60e6, places=3)

    def test_a_missing_head_of_the_span_is_reported(self):
        gaps = ip.coverage_gaps([(1e6, 18e9)], (10.0, 18e9))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 10.0, places=9)

    def test_a_missing_tail_of_the_span_is_reported(self):
        gaps = ip.coverage_gaps([(10.0, 1e9)], (10.0, 18e9))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1], 18e9, places=3)

    def test_bands_outside_the_span_do_not_count_as_cover(self):
        gaps = ip.coverage_gaps([(20e9, 30e9)], (10.0, 18e9))
        self.assertEqual(len(gaps), 1)

    def test_an_edge_reached_by_different_arithmetic_leaves_no_hair_width_gap(self):
        gaps = ip.coverage_gaps(
            [(10.0, _UPPER_CONDUCTED_HZ), (_LOWER_RADIATED_HZ, 18e9)], (10.0, 18e9)
        )
        self.assertEqual(gaps, ())

    def test_a_malformed_span_raises(self):
        with self.assertRaises(ValueError):
            ip.coverage_gaps([(10.0, 1e9)], (18e9, 10.0))


class ApprovalStateTest(unittest.TestCase):
    def test_an_approved_list_reports_approved(self):
        self.assertEqual(ip.approval_state(_clean_package()), "approved")

    def test_a_submitted_list_awaits_approval(self):
        package = _clean_package()
        package["approved_on"] = None
        self.assertEqual(ip.approval_state(package), "submitted_awaiting_approval")

    def test_an_unsent_list_reports_not_submitted(self):
        package = _clean_package()
        package["submitted_on"] = None
        package["approved_on"] = None
        self.assertEqual(ip.approval_state(package), "not_submitted")

    def test_same_day_approval_is_accepted(self):
        package = _clean_package()
        package["approved_on"] = package["submitted_on"]
        self.assertEqual(ip.approval_state(package), "approved")

    def test_approval_without_submission_raises(self):
        package = _clean_package()
        package["submitted_on"] = None
        with self.assertRaises(ValueError):
            ip.approval_state(package)

    def test_approval_before_submission_raises(self):
        package = _clean_package()
        package["approved_on"] = "2026-02-01"
        with self.assertRaises(ValueError):
            ip.approval_state(package)

    def test_a_malformed_date_raises(self):
        package = _clean_package()
        package["submitted_on"] = "02/03/2026"
        with self.assertRaises(ValueError):
            ip.approval_state(package)

    def test_a_non_string_date_raises(self):
        package = _clean_package()
        package["submitted_on"] = 20260302
        with self.assertRaises(ValueError):
            ip.approval_state(package)

    def test_a_non_mapping_package_raises(self):
        with self.assertRaises(ValueError):
            ip.approval_state(["submitted_on"])


class ReviewPointListTest(unittest.TestCase):
    def test_a_clean_package_is_compliant(self):
        review = ip.review_point_list(_clean_package())
        self.assertTrue(review["compliant"])
        self.assertEqual(review["selection_findings"], [])
        self.assertEqual(review["coverage_gaps_hz"], ())

    def test_the_exact_limit_point_is_not_a_margin_finding(self):
        review = ip.review_point_list(_clean_package())
        self.assertEqual(review["margin_findings"], [])

    def test_dropping_a_required_point_is_reported(self):
        package = _clean_package()
        package["points"] = [p for p in package["points"] if p["point_id"] != "ICP-03"]
        review = ip.review_point_list(package)
        self.assertEqual(len(review["selection_findings"]), 1)
        self.assertFalse(review["compliant"])

    def test_a_margin_shortfall_is_reported(self):
        package = _clean_package()
        package["points"][7]["demonstrated"]["emission_level_dbuv"] = 30.0
        review = ip.review_point_list(package)
        self.assertEqual(len(review["margin_findings"]), 1)
        self.assertIn("ICP-08", review["margin_findings"][0])

    def test_a_point_without_demonstrated_levels_is_reported(self):
        package = _clean_package()
        package["points"][0]["demonstrated"] = None
        review = ip.review_point_list(package)
        self.assertTrue(
            any("no demonstrated separation" in f for f in review["margin_findings"])
        )

    def test_a_record_defect_blocks_compliance(self):
        package = _clean_package()
        del package["points"][4]["responsible_party"]
        review = ip.review_point_list(package)
        self.assertEqual(len(review["record_findings"]), 1)
        self.assertFalse(review["compliant"])

    def test_an_uncovered_stretch_of_the_span_is_reported(self):
        package = _clean_package()
        package["spectrum_span_hz"] = (10.0, 40e9)
        review = ip.review_point_list(package)
        self.assertEqual(len(review["coverage_gaps_hz"]), 1)
        self.assertFalse(review["compliant"])

    def test_an_empty_point_list_leaves_the_whole_span_uncovered(self):
        package = _clean_package()
        package["points"] = []
        review = ip.review_point_list(package)
        self.assertEqual(len(review["coverage_gaps_hz"]), 1)
        self.assertEqual(len(review["selection_findings"]), 9)

    def test_a_list_awaiting_approval_is_not_compliant(self):
        package = _clean_package()
        package["approved_on"] = None
        review = ip.review_point_list(package)
        self.assertEqual(review["approval_state"], "submitted_awaiting_approval")
        self.assertEqual(len(review["approval_findings"]), 1)
        self.assertFalse(review["compliant"])

    def test_an_approval_with_no_customer_on_record_is_reported(self):
        package = _clean_package()
        package["approving_customer"] = ""
        review = ip.review_point_list(package)
        self.assertTrue(
            any("approving customer" in f for f in review["approval_findings"])
        )

    def test_a_duplicate_point_identifier_raises(self):
        package = _clean_package()
        package["points"].append(dict(package["points"][0]))
        with self.assertRaises(ValueError):
            ip.review_point_list(package)

    def test_a_mapping_of_points_raises(self):
        package = _clean_package()
        package["points"] = {"ICP-01": "conducted_emission"}
        with self.assertRaises(ValueError):
            ip.review_point_list(package)

    def test_a_non_mapping_package_raises(self):
        with self.assertRaises(ValueError):
            ip.review_point_list(["points"])

    def test_the_review_is_deterministic_across_repeated_calls(self):
        self.assertEqual(
            ip.review_point_list(_clean_package()),
            ip.review_point_list(_clean_package()),
        )


if __name__ == "__main__":
    unittest.main()

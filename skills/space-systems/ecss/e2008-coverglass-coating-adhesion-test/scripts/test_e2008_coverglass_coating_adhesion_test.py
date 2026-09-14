#!/usr/bin/env python3
"""Contract test for the coverglass coating adhesion leaf (offline)."""

import copy
import math
import unittest

from e2008_coverglass_coating_adhesion_test_logic import (
    ADHESION_ACCEPTED,
    ADHESION_GRADE_BANDS,
    ADHESION_NOT_ACCEPTED,
    ADHESION_RUN_VOID,
    CROSS_CUT_LATTICE,
    MAX_TAPE_PEEL_STRENGTH_N_PER_25MM,
    MAX_TAPE_REMOVAL_FRACTION,
    METHOD_FAMILIES,
    MIN_TAPE_DWELL_TIME_S,
    MIN_TAPE_PEEL_STRENGTH_N_PER_25MM,
    PULL_OFF_STUD,
    TAPE_PEEL,
    THICK_COATING_CUT_SPACING_MM,
    WORST_ADHESION_GRADE,
    adhesion_grade,
    assess_coating_adhesion,
    cut_spacing_is_correct,
    detached_square_fraction,
    failure_mode_is_conclusive,
    lattice_square_count,
    method_family,
    missing_evidence,
    nominate_accepted_standard,
    pull_off_stress_mpa,
    removal_angle_is_accepted,
    removed_area_fraction,
    required_cut_spacing_mm,
    required_evidence,
    tape_is_within_band,
)

ACCEPTED_STANDARDS = {
    "customer-adhesion-spec-tape": TAPE_PEEL,
    "customer-adhesion-spec-lattice": CROSS_CUT_LATTICE,
    "customer-adhesion-spec-stud": PULL_OFF_STUD,
}

TAPE_CASE = {
    "customer_accepted_standards": dict(ACCEPTED_STANDARDS),
    "nominated_standard": "customer-adhesion-spec-tape",
    "evidence": {
        "tape_peel_strength_n_per_25mm": 8.0,
        "dwell_time_s": 90.0,
        "removal_angle_deg": 180.0,
        "tested_area_mm2": 400.0,
        "removed_coating_area_mm2": 0.0,
    },
}

LATTICE_CASE = {
    "customer_accepted_standards": dict(ACCEPTED_STANDARDS),
    "nominated_standard": "customer-adhesion-spec-lattice",
    "max_accepted_grade": 1,
    "evidence": {
        "coating_thickness_um": 0.5,
        "cut_spacing_mm": 1.0,
        "cuts_per_axis": 7,
        "detached_squares": 0,
    },
}

STUD_CASE = {
    "customer_accepted_standards": dict(ACCEPTED_STANDARDS),
    "nominated_standard": "customer-adhesion-spec-stud",
    "evidence": {
        "pull_force_n": 400.0,
        "stud_diameter_mm": 10.0,
        "failure_mode": "adhesive-coating-to-glass",
        "required_pull_off_stress_mpa": 4.0,
    },
}


def _with_evidence(base, **overrides):
    case = copy.deepcopy(base)
    case["evidence"].update(overrides)
    return case


class AcceptedStandardTests(unittest.TestCase):
    def test_a_standard_on_the_accepted_list_is_the_nomination(self):
        self.assertEqual(
            nominate_accepted_standard(
                "customer-adhesion-spec-tape", ACCEPTED_STANDARDS
            ),
            "customer-adhesion-spec-tape",
        )

    def test_a_single_element_sequence_is_also_accepted(self):
        self.assertEqual(
            nominate_accepted_standard(
                ["customer-adhesion-spec-stud"], ACCEPTED_STANDARDS
            ),
            "customer-adhesion-spec-stud",
        )

    def test_a_standard_the_customer_never_accepted_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_accepted_standard("in-house-thumbnail-scrape", ACCEPTED_STANDARDS)

    def test_two_standards_left_open_are_refused(self):
        with self.assertRaises(ValueError):
            nominate_accepted_standard(
                ["customer-adhesion-spec-tape", "customer-adhesion-spec-stud"],
                ACCEPTED_STANDARDS,
            )

    def test_an_empty_nomination_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_accepted_standard([], ACCEPTED_STANDARDS)

    def test_an_empty_accepted_list_cannot_carry_a_nomination(self):
        with self.assertRaises(ValueError):
            nominate_accepted_standard("customer-adhesion-spec-tape", {})

    def test_an_accepted_list_naming_an_unhandled_family_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_accepted_standard(
                "customer-adhesion-spec-scratch",
                {"customer-adhesion-spec-scratch": "fingernail-drag"},
            )

    def test_each_accepted_standard_carries_its_own_family(self):
        self.assertEqual(
            method_family("customer-adhesion-spec-lattice", ACCEPTED_STANDARDS),
            CROSS_CUT_LATTICE,
        )
        self.assertEqual(
            method_family("customer-adhesion-spec-stud", ACCEPTED_STANDARDS),
            PULL_OFF_STUD,
        )


class EvidenceTests(unittest.TestCase):
    def test_every_family_declares_the_evidence_it_needs(self):
        for family in METHOD_FAMILIES:
            self.assertGreaterEqual(len(required_evidence(family)), 4)

    def test_the_families_do_not_ask_for_the_same_evidence(self):
        tape = set(required_evidence(TAPE_PEEL))
        lattice = set(required_evidence(CROSS_CUT_LATTICE))
        stud = set(required_evidence(PULL_OFF_STUD))
        self.assertEqual(tape & lattice, set())
        self.assertEqual(tape & stud, set())
        self.assertEqual(lattice & stud, set())

    def test_an_unhandled_family_declares_no_evidence(self):
        with self.assertRaises(ValueError):
            required_evidence("fingernail-drag")

    def test_absent_evidence_is_named_rather_than_defaulted(self):
        absent = missing_evidence(PULL_OFF_STUD, {"pull_force_n": 400.0})
        self.assertEqual(
            set(absent),
            {"failure_mode", "required_pull_off_stress_mpa", "stud_diameter_mm"},
        )

    def test_evidence_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            missing_evidence(TAPE_PEEL, ["dwell_time_s"])


class TapePeelTests(unittest.TestCase):
    def test_tape_inside_the_band_is_a_valid_instrument(self):
        self.assertTrue(tape_is_within_band(8.0))

    def test_tape_on_the_band_edge_is_inside_it(self):
        self.assertTrue(tape_is_within_band(MIN_TAPE_PEEL_STRENGTH_N_PER_25MM))
        self.assertTrue(tape_is_within_band(MAX_TAPE_PEEL_STRENGTH_N_PER_25MM))

    def test_weak_and_aggressive_tape_are_both_outside_the_band(self):
        self.assertFalse(tape_is_within_band(2.0))
        self.assertFalse(tape_is_within_band(25.0))

    def test_the_two_removal_angles_are_accepted_within_tolerance(self):
        self.assertTrue(removal_angle_is_accepted(180.0))
        self.assertTrue(removal_angle_is_accepted(93.0))
        self.assertFalse(removal_angle_is_accepted(135.0))

    def test_removed_area_reads_as_a_share_of_the_tested_area(self):
        self.assertAlmostEqual(removed_area_fraction(4.0, 400.0), 0.01, places=12)

    def test_more_coating_removed_than_was_tested_is_refused(self):
        with self.assertRaises(ValueError):
            removed_area_fraction(500.0, 400.0)

    def test_a_clean_tape_pull_is_accepted(self):
        result = assess_coating_adhesion(TAPE_CASE)
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)
        self.assertEqual(result["method_family"], TAPE_PEEL)
        self.assertTrue(result["method_detail"]["tape_within_band"])

    def test_wrong_tape_voids_the_pull_rather_than_failing_the_coating(self):
        result = assess_coating_adhesion(
            _with_evidence(TAPE_CASE, tape_peel_strength_n_per_25mm=25.0)
        )
        self.assertEqual(result["verdict"], ADHESION_RUN_VOID)
        self.assertTrue(any("tape peel strength" in r for r in result["void_reasons"]))

    def test_a_short_dwell_voids_the_pull(self):
        result = assess_coating_adhesion(
            _with_evidence(TAPE_CASE, dwell_time_s=MIN_TAPE_DWELL_TIME_S / 6.0)
        )
        self.assertEqual(result["verdict"], ADHESION_RUN_VOID)
        self.assertTrue(any("dwelled" in r for r in result["void_reasons"]))

    def test_an_improvised_removal_angle_voids_the_pull(self):
        result = assess_coating_adhesion(
            _with_evidence(TAPE_CASE, removal_angle_deg=135.0)
        )
        self.assertEqual(result["verdict"], ADHESION_RUN_VOID)

    def test_coating_lifted_by_the_tape_is_a_finding(self):
        result = assess_coating_adhesion(
            _with_evidence(TAPE_CASE, removed_coating_area_mm2=20.0)
        )
        self.assertEqual(result["verdict"], ADHESION_NOT_ACCEPTED)
        self.assertGreater(
            result["method_detail"]["removed_area_fraction"],
            MAX_TAPE_REMOVAL_FRACTION,
        )


class CrossCutLatticeTests(unittest.TestCase):
    def test_a_lattice_of_n_cuts_encloses_n_minus_one_squared(self):
        self.assertEqual(lattice_square_count(7), 36)
        self.assertEqual(lattice_square_count(11), 100)

    def test_a_single_cut_encloses_no_lattice(self):
        with self.assertRaises(ValueError):
            lattice_square_count(1)

    def test_detached_squares_read_as_a_share_of_the_lattice(self):
        self.assertAlmostEqual(detached_square_fraction(9, 7), 0.25, places=12)

    def test_more_detached_squares_than_the_lattice_holds_is_refused(self):
        with self.assertRaises(ValueError):
            detached_square_fraction(40, 7)

    def test_a_spotless_lattice_takes_the_best_grade(self):
        self.assertEqual(adhesion_grade(0.0), 0)

    def test_every_band_edge_falls_in_the_better_grade(self):
        for grade, upper in ADHESION_GRADE_BANDS:
            self.assertEqual(adhesion_grade(upper), grade)

    def test_a_share_past_the_last_band_takes_the_worst_grade(self):
        self.assertEqual(adhesion_grade(0.9), WORST_ADHESION_GRADE)

    def test_a_share_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            adhesion_grade(1.4)

    def test_a_thin_coating_calls_for_the_finest_spacing(self):
        self.assertAlmostEqual(required_cut_spacing_mm(0.5), 1.0, places=9)
        self.assertAlmostEqual(required_cut_spacing_mm(90.0), 2.0, places=9)
        self.assertAlmostEqual(
            required_cut_spacing_mm(300.0), THICK_COATING_CUT_SPACING_MM, places=9
        )

    def test_the_correct_spacing_for_the_thickness_is_recognised(self):
        self.assertTrue(cut_spacing_is_correct(1.0, 0.5))
        self.assertFalse(cut_spacing_is_correct(3.0, 0.5))

    def test_a_spotless_lattice_run_is_accepted(self):
        result = assess_coating_adhesion(LATTICE_CASE)
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)
        self.assertEqual(result["method_detail"]["adhesion_grade"], 0)
        self.assertEqual(result["method_detail"]["lattice_squares"], 36)

    def test_the_wrong_lattice_spacing_voids_the_run(self):
        result = assess_coating_adhesion(
            _with_evidence(LATTICE_CASE, cut_spacing_mm=3.0)
        )
        self.assertEqual(result["verdict"], ADHESION_RUN_VOID)
        self.assertTrue(any("lattice cut at" in r for r in result["void_reasons"]))

    def test_a_grade_worse_than_the_customer_accepts_is_a_finding(self):
        result = assess_coating_adhesion(
            _with_evidence(LATTICE_CASE, detached_squares=9)
        )
        self.assertEqual(result["verdict"], ADHESION_NOT_ACCEPTED)
        self.assertGreater(result["method_detail"]["adhesion_grade"], 1)
        self.assertTrue(any("adhesion grade" in f for f in result["findings"]))

    def test_a_customer_who_accepts_a_worse_grade_gets_that_grade(self):
        case = _with_evidence(LATTICE_CASE, detached_squares=9)
        case["max_accepted_grade"] = 4
        result = assess_coating_adhesion(case)
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)


class PullOffStudTests(unittest.TestCase):
    def test_stress_is_the_force_over_the_stud_face(self):
        stress = pull_off_stress_mpa(400.0, 10.0)
        self.assertAlmostEqual(stress, 400.0 / (math.pi * 25.0), places=9)

    def test_a_wider_stud_lowers_the_stress_for_the_same_force(self):
        self.assertLess(pull_off_stress_mpa(400.0, 20.0), pull_off_stress_mpa(400.0, 10.0))

    def test_a_coating_side_break_says_something_about_the_bond(self):
        self.assertTrue(failure_mode_is_conclusive("adhesive-coating-to-glass"))
        self.assertTrue(failure_mode_is_conclusive("cohesive-within-coating"))

    def test_a_glue_side_break_says_nothing_about_the_bond(self):
        self.assertFalse(failure_mode_is_conclusive("adhesive-glue-to-stud"))

    def test_an_unknown_failure_mode_is_refused(self):
        with self.assertRaises(ValueError):
            failure_mode_is_conclusive("it-just-came-off")

    def test_a_conclusive_pull_over_the_requirement_is_accepted(self):
        result = assess_coating_adhesion(STUD_CASE)
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)
        self.assertTrue(result["method_detail"]["failure_mode_conclusive"])
        self.assertTrue(result["method_detail"]["stress_meets_requirement"])

    def test_a_conclusive_pull_under_the_requirement_is_a_finding(self):
        result = assess_coating_adhesion(
            _with_evidence(STUD_CASE, required_pull_off_stress_mpa=20.0)
        )
        self.assertEqual(result["verdict"], ADHESION_NOT_ACCEPTED)
        self.assertTrue(any("pull-off stress" in f for f in result["findings"]))

    def test_a_glue_failure_under_the_requirement_voids_the_run(self):
        result = assess_coating_adhesion(
            _with_evidence(
                STUD_CASE,
                failure_mode="adhesive-glue-to-stud",
                required_pull_off_stress_mpa=20.0,
            )
        )
        self.assertEqual(result["verdict"], ADHESION_RUN_VOID)
        self.assertTrue(any("weakest link" in r for r in result["void_reasons"]))

    def test_a_glue_failure_over_the_requirement_still_clears_it(self):
        result = assess_coating_adhesion(
            _with_evidence(STUD_CASE, failure_mode="adhesive-glue-to-stud")
        )
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)
        self.assertFalse(result["method_detail"]["failure_mode_conclusive"])

    def test_a_stress_exactly_on_the_requirement_clears_it(self):
        stress = pull_off_stress_mpa(400.0, 10.0)
        result = assess_coating_adhesion(
            _with_evidence(STUD_CASE, required_pull_off_stress_mpa=stress)
        )
        self.assertAlmostEqual(
            result["method_detail"]["pull_off_stress_mpa"], stress, places=9
        )
        self.assertEqual(result["verdict"], ADHESION_ACCEPTED)


class AssessmentGuardTests(unittest.TestCase):
    def test_missing_evidence_stops_the_assessment(self):
        case = copy.deepcopy(LATTICE_CASE)
        del case["evidence"]["cuts_per_axis"]
        with self.assertRaises(ValueError):
            assess_coating_adhesion(case)

    def test_evidence_that_is_not_a_mapping_is_refused(self):
        case = copy.deepcopy(TAPE_CASE)
        case["evidence"] = ["dwell_time_s"]
        with self.assertRaises(ValueError):
            assess_coating_adhesion(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_coating_adhesion(TAPE_PEEL)

    def test_an_unaccepted_standard_stops_the_assessment(self):
        case = copy.deepcopy(TAPE_CASE)
        case["nominated_standard"] = "in-house-thumbnail-scrape"
        with self.assertRaises(ValueError):
            assess_coating_adhesion(case)


if __name__ == "__main__":
    unittest.main()

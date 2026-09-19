"""Contract test for the crimp acceptance criteria leaf (stdlib unittest)."""

import unittest

from q7026_acceptance_rejection_criteria_logic import (
    ACCEPTED,
    ACCEPTED_WITH_RECORD,
    COSMETIC,
    LOT_ACCEPTED,
    LOT_ACCEPTED_WITH_FINDINGS,
    LOT_ESCALATED,
    LOT_REJECTED,
    MAJOR,
    MINOR,
    REJECTED,
    REWORK,
    REWORKABLE,
    assess_lot,
    assess_termination,
    categorize_defect,
    governing_severity,
    grade_pull_off,
    grade_strand_damage,
    minimum_pull_off_force,
    strand_damage_allowance,
    validate_criteria,
    validate_termination,
)


def criteria(**kw):
    c = {
        "defect_severities": {
            "conductor-brush-outside-the-barrel": MAJOR,
            "insulation-trapped-in-the-conductor-barrel": MAJOR,
            "insulation-support-not-formed": REWORKABLE,
            "bellmouth-missing": MINOR,
            "tool-witness-mark-off-centre": COSMETIC,
        },
        "pull_off_minimum_n": [
            {"csa_mm2": 0.14, "minimum_n": 34.0},
            {"csa_mm2": 0.38, "minimum_n": 90.0},
            {"csa_mm2": 0.60, "minimum_n": 140.0},
        ],
        "max_damaged_strand_fraction": 0.10,
        "min_strands_for_any_damage": 19,
        "sample_size": 3,
    }
    c.update(kw)
    return c


def termination(**kw):
    t = {
        "termination_id": "W-0041-A",
        "conductor_csa_mm2": 0.38,
        "strand_count": 19,
        "damaged_strands": 0,
        "defect_codes": [],
        "pull_off_force_n": 120.0,
    }
    t.update(kw)
    return t


class TestCriteriaValidation(unittest.TestCase):
    def test_a_non_mapping_criteria_set_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria("q-st-70-26")

    def test_an_empty_severity_map_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(criteria(defect_severities={}))

    def test_an_undeclared_severity_value_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(
                criteria(defect_severities={"bellmouth-missing": "probably-fine"})
            )

    def test_an_empty_pull_off_table_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(criteria(pull_off_minimum_n=[]))

    def test_a_duplicated_conductor_size_in_the_table_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(
                criteria(
                    pull_off_minimum_n=[
                        {"csa_mm2": 0.38, "minimum_n": 90.0},
                        {"csa_mm2": 0.38, "minimum_n": 95.0},
                    ]
                )
            )

    def test_a_non_positive_minimum_force_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(
                criteria(pull_off_minimum_n=[{"csa_mm2": 0.38, "minimum_n": 0.0}])
            )

    def test_a_strand_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_criteria(criteria(max_damaged_strand_fraction=1.4))

    def test_the_table_is_returned_sorted_by_conductor_size(self):
        checked = validate_criteria(criteria())
        sizes = [row["csa_mm2"] for row in checked["pull_off_minimum_n"]]
        self.assertEqual(sizes, sorted(sizes))


class TestTerminationValidation(unittest.TestCase):
    def test_a_non_mapping_termination_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(["W-0041-A"])

    def test_a_zero_conductor_size_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(conductor_csa_mm2=0.0))

    def test_more_damaged_strands_than_strands_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(strand_count=7, damaged_strands=9))

    def test_a_non_list_defect_code_field_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(defect_codes="bellmouth-missing"))

    def test_a_missing_termination_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(termination_id="   "))

    def test_defect_codes_are_folded_to_lower_case(self):
        checked = validate_termination(
            termination(defect_codes=["Bellmouth-Missing"])
        )
        self.assertEqual(checked["defect_codes"], ["bellmouth-missing"])


class TestPullOffGrading(unittest.TestCase):
    def test_an_untabulated_conductor_size_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_off_force(0.25, criteria())

    def test_a_tabulated_size_returns_its_minimum(self):
        self.assertAlmostEqual(
            minimum_pull_off_force(0.38, criteria()), 90.0, places=9
        )

    def test_a_force_above_the_minimum_passes(self):
        self.assertTrue(grade_pull_off(120.0, 0.38, criteria())["pass"])

    def test_a_force_below_the_minimum_fails(self):
        self.assertFalse(grade_pull_off(71.0, 0.38, criteria())["pass"])

    def test_a_force_exactly_at_the_minimum_passes(self):
        graded = grade_pull_off(90.0, 0.38, criteria())
        self.assertTrue(graded["pass"])
        self.assertAlmostEqual(graded["margin_n"], 0.0, places=9)


class TestStrandDamage(unittest.TestCase):
    def test_a_thin_conductor_is_allowed_no_damage(self):
        self.assertEqual(strand_damage_allowance(7, criteria()), 0)

    def test_the_allowance_scales_with_the_strand_count(self):
        self.assertEqual(strand_damage_allowance(19, criteria()), 1)
        self.assertEqual(strand_damage_allowance(37, criteria()), 3)

    def test_damage_inside_the_allowance_passes(self):
        self.assertTrue(grade_strand_damage(1, 19, criteria())["pass"])

    def test_damage_above_the_allowance_fails(self):
        self.assertFalse(grade_strand_damage(2, 19, criteria())["pass"])


class TestSeverityCategorization(unittest.TestCase):
    def test_an_undeclared_defect_category_raises(self):
        with self.assertRaises(ValueError):
            categorize_defect("barrel-looks-a-bit-odd", criteria())

    def test_a_declared_defect_category_returns_its_severity(self):
        self.assertEqual(
            categorize_defect("bellmouth-missing", criteria()), MINOR
        )

    def test_the_worst_finding_governs_a_mixed_set(self):
        self.assertEqual(governing_severity([COSMETIC, MAJOR, MINOR]), MAJOR)

    def test_an_empty_finding_set_governs_nothing(self):
        self.assertIsNone(governing_severity([]))

    def test_an_unknown_severity_in_the_set_raises(self):
        with self.assertRaises(ValueError):
            governing_severity([COSMETIC, "acceptable-ish"])


class TestTerminationDisposition(unittest.TestCase):
    def test_a_clean_termination_is_accepted(self):
        self.assertEqual(
            assess_termination(termination(), criteria())["disposition"], ACCEPTED
        )

    def test_a_cosmetic_finding_is_still_accepted(self):
        result = assess_termination(
            termination(defect_codes=["tool-witness-mark-off-centre"]), criteria()
        )
        self.assertEqual(result["disposition"], ACCEPTED)

    def test_a_minor_finding_is_accepted_on_the_record(self):
        result = assess_termination(
            termination(defect_codes=["bellmouth-missing"]), criteria()
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_RECORD)
        self.assertTrue(result["conforming"])

    def test_a_reworkable_finding_goes_back_to_the_bench(self):
        result = assess_termination(
            termination(defect_codes=["insulation-support-not-formed"]), criteria()
        )
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["conforming"])

    def test_one_major_finding_governs_a_mostly_clean_termination(self):
        result = assess_termination(
            termination(
                defect_codes=[
                    "tool-witness-mark-off-centre",
                    "conductor-brush-outside-the-barrel",
                ]
            ),
            criteria(),
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertEqual(result["governing_severity"], MAJOR)

    def test_a_failed_pull_test_rejects_on_its_own(self):
        result = assess_termination(
            termination(pull_off_force_n=44.0), criteria()
        )
        self.assertEqual(result["disposition"], REJECTED)

    def test_strand_damage_above_the_allowance_rejects_on_its_own(self):
        result = assess_termination(
            termination(damaged_strands=4), criteria()
        )
        self.assertEqual(result["disposition"], REJECTED)

    def test_a_termination_with_no_pull_test_is_graded_on_the_rest(self):
        result = assess_termination(
            termination(pull_off_force_n=None), criteria()
        )
        self.assertIsNone(result["pull_off"])
        self.assertEqual(result["disposition"], ACCEPTED)


class TestLotDisposition(unittest.TestCase):
    def test_an_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_lot([], criteria())

    def test_a_non_boolean_sampled_flag_raises(self):
        with self.assertRaises(ValueError):
            assess_lot([termination()], criteria(), sampled="yes")

    def test_a_clean_lot_is_accepted(self):
        report = assess_lot([termination(), termination()], criteria())
        self.assertEqual(report["lot_disposition"], LOT_ACCEPTED)

    def test_a_minor_finding_leaves_the_lot_accepted_with_findings(self):
        report = assess_lot(
            [termination(), termination(defect_codes=["bellmouth-missing"])],
            criteria(),
        )
        self.assertEqual(report["lot_disposition"], LOT_ACCEPTED_WITH_FINDINGS)

    def test_a_full_inspection_rejects_the_lot_on_a_rejection(self):
        report = assess_lot(
            [termination(), termination(pull_off_force_n=10.0)], criteria()
        )
        self.assertEqual(report["lot_disposition"], LOT_REJECTED)

    def test_a_sampled_inspection_escalates_rather_than_rejecting(self):
        report = assess_lot(
            [termination(), termination(), termination(pull_off_force_n=10.0)],
            criteria(),
            sampled=True,
        )
        self.assertEqual(report["lot_disposition"], LOT_ESCALATED)

    def test_a_sample_smaller_than_the_declared_size_raises(self):
        with self.assertRaises(ValueError):
            assess_lot([termination()], criteria(), sampled=True)

    def test_the_rework_list_names_the_terminations_going_back(self):
        report = assess_lot(
            [
                termination(termination_id="W-1"),
                termination(
                    termination_id="W-2",
                    defect_codes=["insulation-support-not-formed"],
                ),
            ],
            criteria(),
        )
        self.assertEqual(report["returned_for_rework"], ["W-2"])


if __name__ == "__main__":
    unittest.main()

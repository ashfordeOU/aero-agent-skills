"""Contract tests for the clause 6 pre-tailoring logic."""

import unittest

from q20_pretailoring_logic import (
    APPLIED_DISPOSITIONS,
    DISPOSITIONS,
    PRODUCT_TYPES,
    applicable_fraction,
    apply_pretailoring,
    assess_pretailoring,
    deviation_findings,
    normalize_token,
    validate_matrix,
    validate_product_type,
)


def _row(**overrides):
    row = {p: "applicable" for p in PRODUCT_TYPES}
    row.update(overrides)
    return row


MATRIX = {
    "Q-5-2-1": _row(),
    "Q-5-4-3": _row(
        **{
            "commercial-off-the-shelf-item": "not-applicable",
            "software-product": {"disposition": "modified", "modification": "reduced evidence set"},
        }
    ),
    "Q-5-8-9": _row(**{"software-product": "not-applicable"}),
    "Q-5-7-5": _row(**{"ground-support-equipment": "not-applicable"}),
}

REQUIREMENTS = ["Q-5-2-1", "Q-5-4-3", "Q-5-8-9", "Q-5-7-5"]


def _spec(**overrides):
    spec = {
        "requirements": list(REQUIREMENTS),
        "matrix": {k: dict(v) for k, v in MATRIX.items()},
        "product_type": "first-flight-hardware",
        "proposed": {r: "applicable" for r in REQUIREMENTS},
        "justified": [],
    }
    spec.update(overrides)
    return spec


class NormalizeAndTypeTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Q_5 2 1"), "q-5-2-1")

    def test_known_product_type_accepted(self):
        self.assertEqual(validate_product_type("Ground Support Equipment"), "ground-support-equipment")

    def test_unknown_product_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_product_type("cubesat")

    def test_vocabularies_are_closed(self):
        self.assertEqual(len(PRODUCT_TYPES), 5)
        self.assertEqual(DISPOSITIONS, ("applicable", "modified", "not-applicable"))
        self.assertEqual(set(APPLIED_DISPOSITIONS), {"applicable", "modified"})


class ValidateMatrixTests(unittest.TestCase):
    def test_complete_matrix_is_validated(self):
        rows = validate_matrix(MATRIX)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows["q-5-2-1"]["software-product"]["disposition"], "applicable")

    def test_row_missing_a_product_type_rejected(self):
        row = _row()
        del row["software-product"]
        with self.assertRaises(ValueError):
            validate_matrix({"Q-5-2-1": row})

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix({"Q-5-2-1": _row(**{"software-product": "maybe"})})

    def test_modified_without_a_modification_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix({"Q-5-2-1": _row(**{"software-product": "modified"})})

    def test_modification_note_is_carried_through(self):
        rows = validate_matrix(MATRIX)
        self.assertEqual(
            rows["q-5-4-3"]["software-product"]["modification"], "reduced evidence set"
        )

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix({})

    def test_non_mapping_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix({"Q-5-2-1": ["applicable"]})


class ApplyPretailoringTests(unittest.TestCase):
    def test_first_flight_hardware_keeps_the_whole_set(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "first-flight-hardware")
        self.assertEqual(len(tailored["applied"]), 4)
        self.assertEqual(tailored["dropped"], [])

    def test_ground_support_equipment_drops_its_exempt_requirement(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "ground-support-equipment")
        self.assertEqual(tailored["dropped"], ["q-5-7-5"])
        self.assertEqual(len(tailored["applied"]), 3)

    def test_software_product_keeps_a_modified_requirement_in_the_set(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "software-product")
        applied = {e["id"]: e for e in tailored["applied"]}
        self.assertEqual(applied["q-5-4-3"]["disposition"], "modified")
        self.assertEqual(applied["q-5-4-3"]["modification"], "reduced evidence set")

    def test_requirement_absent_from_the_matrix_is_a_finding(self):
        tailored = apply_pretailoring(
            REQUIREMENTS + ["Q-5-9-9"], MATRIX, "first-flight-hardware"
        )
        self.assertEqual(len(tailored["findings"]), 1)
        self.assertIn("q-5-9-9", tailored["findings"][0])

    def test_duplicate_requirement_rejected(self):
        with self.assertRaises(ValueError):
            apply_pretailoring(["Q-5-2-1", "q 5 2 1"], MATRIX, "first-flight-hardware")

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            apply_pretailoring([], MATRIX, "first-flight-hardware")


class DeviationTests(unittest.TestCase):
    def test_proposal_matching_the_matrix_is_clean(self):
        result = deviation_findings(
            {r: "applicable" for r in REQUIREMENTS}, MATRIX, "first-flight-hardware"
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["tightenings"], [])

    def test_unjustified_relaxation_is_a_finding(self):
        result = deviation_findings(
            {"Q-5-2-1": "not-applicable"}, MATRIX, "first-flight-hardware"
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("relaxed", result["findings"][0])

    def test_justified_relaxation_clears_the_finding(self):
        result = deviation_findings(
            {"Q-5-2-1": "not-applicable"},
            MATRIX,
            "first-flight-hardware",
            justified=["q-5-2-1"],
        )
        self.assertEqual(result["findings"], [])

    def test_relaxation_to_modified_is_still_a_relaxation(self):
        result = deviation_findings(
            {"Q-5-2-1": "modified"}, MATRIX, "first-flight-hardware"
        )
        self.assertEqual(len(result["findings"]), 1)

    def test_tightening_needs_no_justification(self):
        result = deviation_findings(
            {"Q-5-7-5": "applicable"}, MATRIX, "ground-support-equipment"
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["tightenings"]), 1)

    def test_proposal_outside_the_matrix_is_a_finding(self):
        result = deviation_findings(
            {"Q-5-9-9": "applicable"}, MATRIX, "first-flight-hardware"
        )
        self.assertIn("does not cover", result["findings"][0])

    def test_unknown_proposed_disposition_rejected(self):
        with self.assertRaises(ValueError):
            deviation_findings({"Q-5-2-1": "waived"}, MATRIX, "first-flight-hardware")

    def test_empty_proposal_rejected(self):
        with self.assertRaises(ValueError):
            deviation_findings({}, MATRIX, "first-flight-hardware")


class FractionTests(unittest.TestCase):
    def test_untailored_set_is_unity(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "first-flight-hardware")
        self.assertAlmostEqual(applicable_fraction(tailored, len(REQUIREMENTS)), 1.0, places=9)

    def test_one_dropped_requirement_gives_three_quarters(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "ground-support-equipment")
        self.assertAlmostEqual(applicable_fraction(tailored, len(REQUIREMENTS)), 0.75, places=9)

    def test_zero_denominator_rejected(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "first-flight-hardware")
        with self.assertRaises(ValueError):
            applicable_fraction(tailored, 0)

    def test_boolean_denominator_rejected(self):
        tailored = apply_pretailoring(REQUIREMENTS, MATRIX, "first-flight-hardware")
        with self.assertRaises(ValueError):
            applicable_fraction(tailored, True)

    def test_non_tailored_argument_rejected(self):
        with self.assertRaises(ValueError):
            applicable_fraction({"applied_set": []}, 4)


class AssessPretailoringTests(unittest.TestCase):
    def test_clean_proposal_is_adoptable(self):
        result = assess_pretailoring(_spec())
        self.assertTrue(result["tailoring_adoptable"])
        self.assertTrue(result["untailored"])
        self.assertAlmostEqual(result["applicable_fraction"], 1.0, places=9)

    def test_ground_support_equipment_reports_its_tailored_fraction(self):
        spec = _spec(
            product_type="ground-support-equipment",
            proposed={"Q-5-7-5": "not-applicable"},
        )
        result = assess_pretailoring(spec)
        self.assertAlmostEqual(result["applicable_fraction"], 0.75, places=9)
        self.assertFalse(result["untailored"])
        self.assertTrue(result["tailoring_adoptable"])

    def test_unjustified_relaxation_blocks_adoption(self):
        spec = _spec(proposed={"Q-5-8-9": "not-applicable"})
        result = assess_pretailoring(spec)
        self.assertFalse(result["tailoring_adoptable"])

    def test_justified_relaxation_is_adoptable(self):
        spec = _spec(proposed={"Q-5-8-9": "not-applicable"}, justified=["Q-5-8-9"])
        self.assertTrue(assess_pretailoring(spec)["tailoring_adoptable"])

    def test_modified_requirement_stays_in_the_applied_set(self):
        spec = _spec(product_type="software-product", proposed={"Q-5-4-3": "modified"})
        result = assess_pretailoring(spec)
        self.assertTrue(any(e["disposition"] == "modified" for e in result["applied"]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["justified"]
        with self.assertRaises(ValueError):
            assess_pretailoring(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_pretailoring(["requirements"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            requirements=REQUIREMENTS + ["Q-5-9-9", "Q-5-9-8"],
            proposed={"Q-5-2-1": "not-applicable", "Q-5-8-9": "modified"},
        )
        result = assess_pretailoring(spec)
        self.assertFalse(result["tailoring_adoptable"])
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()

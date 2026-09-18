"""Contract test for the outgassing acceptance-criteria leaf (stdlib unittest)."""

import unittest

from q7002_acceptance_criteria_logic import (
    ACCEPTED,
    ACCEPTED_ON_DEVIATION,
    APPLICATION_CLASS_LIMITS,
    BASIS_RECOVERED_MASS_LOSS,
    BASIS_TOTAL_MASS_LOSS,
    REJECTED,
    assess_acceptance,
    class_limits,
    evaluate_material,
    mass_loss_basis,
    recovered_mass_loss_pct,
    validate_result,
    within_limit,
)

GENERAL = "general-screening"
OPTICAL = "optically-sensitive-hardware"
CRYO = "cryogenic-surface-proximity"


def result(material="ADH-1", tml=0.80, cvcm=0.05, **kw):
    record = {
        "material": material,
        "total_mass_loss_pct": tml,
        "cvcm_pct": cvcm,
    }
    record.update(kw)
    return record


class TestClassLimits(unittest.TestCase):
    def test_every_class_carries_both_limits(self):
        for name in APPLICATION_CLASS_LIMITS:
            limits = class_limits(name)
            self.assertIn("mass_loss_limit_pct", limits)
            self.assertIn("cvcm_limit_pct", limits)

    def test_optical_class_is_tighter_on_condensables(self):
        self.assertLess(
            class_limits(OPTICAL)["cvcm_limit_pct"],
            class_limits(GENERAL)["cvcm_limit_pct"],
        )

    def test_cryogenic_class_refuses_the_water_credit(self):
        self.assertFalse(class_limits(CRYO)["water_credit"])

    def test_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            class_limits("wherever-it-fits")

    def test_returned_limits_are_a_copy(self):
        limits = class_limits(GENERAL)
        limits["cvcm_limit_pct"] = 99.0
        self.assertAlmostEqual(
            class_limits(GENERAL)["cvcm_limit_pct"], 0.10, places=9
        )


class TestValidateResult(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        norm = validate_result(result())
        self.assertEqual(norm["material"], "ADH-1")
        self.assertIsNone(norm["water_vapour_regained_pct"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_result(["ADH-1"])

    def test_empty_material_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(""))

    def test_negative_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(tml=-0.1))

    def test_condensing_more_than_was_lost_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(tml=0.05, cvcm=0.20))

    def test_regaining_more_than_was_lost_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(water_vapour_regained_pct=2.0))

    def test_a_result_with_neither_value_nor_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(cvcm=None))

    def test_a_sub_floor_bound_is_accepted_in_place_of_a_value(self):
        norm = validate_result(result(cvcm=None, cvcm_floor_pct=0.005))
        self.assertIsNone(norm["cvcm_pct"])
        self.assertAlmostEqual(norm["cvcm_floor_pct"], 0.005, places=9)

    def test_non_string_deviation_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(deviation_reference=17))


class TestRecoveredMassLoss(unittest.TestCase):
    def test_water_is_subtracted_from_the_total(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(1.20, 0.50), 0.70, places=9)

    def test_all_water_leaves_nothing_behind(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(0.80, 0.80), 0.0, places=12)

    def test_regaining_more_than_lost_raises(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct(0.50, 0.90)

    def test_non_numeric_input_raises(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct("1.2", 0.5)


class TestBasisSelection(unittest.TestCase):
    def test_without_a_water_figure_the_basis_is_the_total(self):
        basis, value = mass_loss_basis(result(), GENERAL)
        self.assertEqual(basis, BASIS_TOTAL_MASS_LOSS)
        self.assertAlmostEqual(value, 0.80, places=9)

    def test_with_a_water_figure_the_basis_is_the_recovered_loss(self):
        basis, value = mass_loss_basis(
            result(tml=1.20, water_vapour_regained_pct=0.40), GENERAL
        )
        self.assertEqual(basis, BASIS_RECOVERED_MASS_LOSS)
        self.assertAlmostEqual(value, 0.80, places=9)

    def test_a_cold_application_keeps_the_total_basis(self):
        basis, value = mass_loss_basis(
            result(tml=0.45, cvcm=0.005, water_vapour_regained_pct=0.20), CRYO
        )
        self.assertEqual(basis, BASIS_TOTAL_MASS_LOSS)
        self.assertAlmostEqual(value, 0.45, places=9)


class TestWithinLimit(unittest.TestCase):
    def test_a_value_on_the_limit_is_within_it(self):
        self.assertTrue(within_limit(1.00, 1.00))

    def test_a_value_under_the_limit_is_within_it(self):
        self.assertTrue(within_limit(0.99, 1.00))

    def test_a_value_clearly_over_the_limit_is_not(self):
        self.assertFalse(within_limit(1.10, 1.00))


class TestEvaluateMaterial(unittest.TestCase):
    def test_a_compliant_material_is_accepted(self):
        row = evaluate_material(result(), GENERAL)
        self.assertEqual(row["verdict"], ACCEPTED)
        self.assertEqual(row["findings"], [])

    def test_a_material_exactly_on_both_limits_is_accepted(self):
        row = evaluate_material(result(tml=1.00, cvcm=0.10), GENERAL)
        self.assertEqual(row["verdict"], ACCEPTED)
        self.assertAlmostEqual(row["mass_loss_value_pct"], 1.00, places=9)

    def test_a_condensable_failure_alone_rejects(self):
        row = evaluate_material(result(tml=0.80, cvcm=0.25), GENERAL)
        self.assertEqual(row["verdict"], REJECTED)
        self.assertIn("cvcm-above-the-class-limit", row["findings"])

    def test_the_same_material_can_pass_one_class_and_fail_another(self):
        record = result(tml=0.80, cvcm=0.05)
        self.assertEqual(evaluate_material(record, GENERAL)["verdict"], ACCEPTED)
        self.assertEqual(evaluate_material(record, OPTICAL)["verdict"], REJECTED)

    def test_water_credit_can_rescue_a_hygroscopic_material(self):
        record = result(tml=1.40, cvcm=0.04, water_vapour_regained_pct=0.60)
        self.assertEqual(evaluate_material(record, GENERAL)["verdict"], ACCEPTED)

    def test_the_same_water_credit_is_refused_at_a_cold_surface(self):
        record = result(tml=0.90, cvcm=0.004, water_vapour_regained_pct=0.60)
        row = evaluate_material(record, CRYO)
        self.assertEqual(row["verdict"], REJECTED)
        self.assertIn("mass-loss-above-the-class-limit", row["findings"])
        self.assertIn(
            "water-credit-not-available-for-this-application", row["findings"]
        )

    def test_a_sub_floor_bound_under_the_limit_demonstrates_compliance(self):
        row = evaluate_material(
            result(cvcm=None, cvcm_floor_pct=0.005), OPTICAL
        )
        self.assertEqual(row["verdict"], ACCEPTED)
        self.assertIsNone(row["cvcm_value_pct"])

    def test_a_sub_floor_bound_over_the_limit_does_not(self):
        row = evaluate_material(
            result(cvcm=None, cvcm_floor_pct=0.05), OPTICAL
        )
        self.assertEqual(row["verdict"], REJECTED)
        self.assertIn(
            "sub-floor-cvcm-bound-above-the-class-limit", row["findings"]
        )

    def test_a_full_deviation_package_carries_a_failing_material(self):
        row = evaluate_material(
            result(
                tml=0.80,
                cvcm=0.25,
                deviation_reference="DEV-0012",
                contamination_assessment_reference="CAR-0044",
            ),
            GENERAL,
        )
        self.assertEqual(row["verdict"], ACCEPTED_ON_DEVIATION)

    def test_a_deviation_without_an_assessment_does_not(self):
        row = evaluate_material(
            result(tml=0.80, cvcm=0.25, deviation_reference="DEV-0012"), GENERAL
        )
        self.assertEqual(row["verdict"], REJECTED)
        self.assertIn(
            "deviation-cited-without-a-contamination-assessment", row["findings"]
        )

    def test_an_assessment_without_a_deviation_does_not_either(self):
        row = evaluate_material(
            result(
                tml=0.80, cvcm=0.25,
                contamination_assessment_reference="CAR-0044",
            ),
            GENERAL,
        )
        self.assertEqual(row["verdict"], REJECTED)
        self.assertIn(
            "contamination-assessment-cited-without-a-deviation", row["findings"]
        )


class TestAssessAcceptance(unittest.TestCase):
    def test_a_clean_list_is_clear(self):
        report = assess_acceptance([result("A"), result("B")], GENERAL)
        self.assertTrue(report["clear"])
        self.assertEqual(report["rejected"], [])

    def test_one_failure_clouds_the_list(self):
        report = assess_acceptance(
            [result("A"), result("B", cvcm=0.40)], GENERAL
        )
        self.assertFalse(report["clear"])
        self.assertEqual(report["rejected"], ["B"])

    def test_deviation_materials_are_listed_separately(self):
        report = assess_acceptance(
            [
                result("A"),
                result(
                    "B", cvcm=0.40,
                    deviation_reference="DEV-1",
                    contamination_assessment_reference="CAR-1",
                ),
            ],
            GENERAL,
        )
        self.assertEqual(report["on_deviation"], ["B"])
        self.assertFalse(report["clear"])

    def test_duplicate_material_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([result("A"), result("A")], GENERAL)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([], GENERAL)

    def test_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([result()], "somewhere-warm")


if __name__ == "__main__":
    unittest.main()

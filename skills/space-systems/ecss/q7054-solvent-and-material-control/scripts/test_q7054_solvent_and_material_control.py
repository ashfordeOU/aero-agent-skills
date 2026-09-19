"""Contract tests for the ultracleaning solvent and agent control logic."""

import unittest

from q7054_solvent_and_material_control_logic import (
    COMPATIBLE,
    PROHIBITED,
    QUALIFIED,
    QUALIFIED_WITH_RESTRICTION,
    REJECTED,
    RESTRICTED,
    compatibility_verdict,
    deposited_nvr_mg_per_01m2,
    grade_residue_limit,
    minimum_purity_grade,
    permissible_residue_mg_per_l,
    qualify_cleaning_agent,
    validate_agent,
    validate_use,
)


def base_agent(**overrides):
    """An electronic-grade alcohol with a batch certificate at 0.8 mg/L."""
    agent = {
        "agent_family": "alcohol",
        "declared_grade": "electronic",
        "certificate_residue_mg_per_l": 0.80,
    }
    agent.update(overrides)
    return agent


def base_use(**overrides):
    """Two litres drained over half a square metre of aluminium."""
    use = {
        "substrate": "aluminium-alloy",
        "wetted_volume_l": 2.0,
        "wetted_area_m2": 0.50,
        "surface_allowance_mg_per_01m2": 0.40,
    }
    use.update(overrides)
    return use


class PurityGradeTests(unittest.TestCase):
    def test_a_known_grade_returns_its_bound(self):
        self.assertAlmostEqual(grade_residue_limit("electronic"), 1.0, places=9)

    def test_the_tightest_grade_has_the_lowest_bound(self):
        self.assertLess(
            grade_residue_limit("ultrapure"), grade_residue_limit("semiconductor")
        )

    def test_an_unknown_grade_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_residue_limit("laboratory")


class DepositionTests(unittest.TestCase):
    def test_deposition_from_concentration_volume_and_area(self):
        self.assertAlmostEqual(
            deposited_nvr_mg_per_01m2(1.0, 2.0, 0.5), 0.40, places=9
        )

    def test_doubling_the_drained_volume_doubles_the_deposit(self):
        single = deposited_nvr_mg_per_01m2(1.0, 2.0, 0.5)
        double = deposited_nvr_mg_per_01m2(1.0, 4.0, 0.5)
        self.assertAlmostEqual(double, 2.0 * single, places=9)

    def test_spreading_over_more_area_lowers_the_deposit(self):
        tight = deposited_nvr_mg_per_01m2(1.0, 2.0, 0.5)
        spread = deposited_nvr_mg_per_01m2(1.0, 2.0, 2.0)
        self.assertAlmostEqual(spread, tight / 4.0, places=9)

    def test_deposition_and_permissible_concentration_round_trip(self):
        self.assertAlmostEqual(
            permissible_residue_mg_per_l(0.40, 2.0, 0.5), 1.0, places=9
        )

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            deposited_nvr_mg_per_01m2(1.0, 2.0, 0.0)

    def test_negative_volume_rejected(self):
        with self.assertRaises(ValueError):
            deposited_nvr_mg_per_01m2(1.0, -2.0, 0.5)

    def test_non_numeric_concentration_rejected(self):
        with self.assertRaises(ValueError):
            deposited_nvr_mg_per_01m2("1.0", 2.0, 0.5)


class MinimumGradeTests(unittest.TestCase):
    def test_a_grade_landing_exactly_on_the_permissible_value_is_taken(self):
        self.assertEqual(minimum_purity_grade(0.40, 2.0, 0.5), "electronic")

    def test_a_tighter_allowance_forces_a_purer_grade(self):
        self.assertEqual(minimum_purity_grade(0.04, 2.0, 0.5), "semiconductor")

    def test_a_loose_allowance_admits_a_cheaper_grade(self):
        self.assertEqual(minimum_purity_grade(20.0, 2.0, 0.5), "technical")

    def test_an_unreachable_allowance_is_refused_with_advice(self):
        with self.assertRaises(ValueError):
            minimum_purity_grade(0.001, 10.0, 0.1)

    def test_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            minimum_purity_grade(0.0, 2.0, 0.5)


class CompatibilityTests(unittest.TestCase):
    def test_an_uncatalogued_pairing_is_compatible(self):
        self.assertEqual(
            compatibility_verdict("alcohol", "aluminium-alloy")["verdict"], COMPATIBLE
        )

    def test_chlorinated_solvent_on_titanium_is_prohibited(self):
        result = compatibility_verdict("chlorinated-solvent", "titanium-alloy")
        self.assertEqual(result["verdict"], PROHIBITED)
        self.assertIn("stress corrosion", result["reason"])

    def test_alkaline_detergent_on_magnesium_is_prohibited(self):
        self.assertEqual(
            compatibility_verdict("aqueous-alkaline-detergent", "magnesium-alloy")[
                "verdict"
            ],
            PROHIBITED,
        )

    def test_alkaline_detergent_on_aluminium_is_restricted(self):
        self.assertEqual(
            compatibility_verdict("aqueous-alkaline-detergent", "aluminium-alloy")[
                "verdict"
            ],
            RESTRICTED,
        )

    def test_alcohol_on_silver_is_restricted(self):
        self.assertEqual(
            compatibility_verdict("alcohol", "silver-coating")["verdict"], RESTRICTED
        )

    def test_an_unknown_agent_family_rejected(self):
        with self.assertRaises(ValueError):
            compatibility_verdict("steam", "aluminium-alloy")

    def test_an_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            compatibility_verdict("alcohol", "beryllium")


class DeclarationValidationTests(unittest.TestCase):
    def test_a_complete_agent_validates(self):
        self.assertEqual(validate_agent(base_agent())["agent_family"], "alcohol")

    def test_an_agent_without_a_certificate_figure_rejected(self):
        agent = base_agent()
        del agent["certificate_residue_mg_per_l"]
        with self.assertRaises(ValueError):
            validate_agent(agent)

    def test_a_non_mapping_agent_rejected(self):
        with self.assertRaises(ValueError):
            validate_agent("electronic grade alcohol")

    def test_a_complete_use_validates(self):
        self.assertAlmostEqual(validate_use(base_use())["wetted_area_m2"], 0.5, places=9)

    def test_a_use_with_no_allowance_rejected(self):
        use = base_use()
        del use["surface_allowance_mg_per_01m2"]
        with self.assertRaises(ValueError):
            validate_use(use)


class QualificationTests(unittest.TestCase):
    def test_a_clean_compatible_agent_qualifies(self):
        result = qualify_cleaning_agent(base_agent(), base_use())
        self.assertEqual(result["verdict"], QUALIFIED)
        self.assertEqual(result["findings"], [])

    def test_the_deposited_residue_is_reported(self):
        result = qualify_cleaning_agent(base_agent(), base_use())
        self.assertAlmostEqual(result["deposited_nvr_mg_per_01m2"], 0.32, places=9)

    def test_a_deposit_landing_exactly_on_the_allowance_still_qualifies(self):
        result = qualify_cleaning_agent(
            base_agent(), base_use(surface_allowance_mg_per_01m2=0.32)
        )
        self.assertEqual(result["verdict"], QUALIFIED)

    def test_a_restricted_pairing_qualifies_with_its_control_attached(self):
        result = qualify_cleaning_agent(base_agent(), base_use(substrate="silver-coating"))
        self.assertEqual(result["verdict"], QUALIFIED_WITH_RESTRICTION)
        self.assertEqual(len(result["restrictions"]), 1)

    def test_a_prohibited_pairing_is_rejected(self):
        result = qualify_cleaning_agent(
            base_agent(agent_family="chlorinated-solvent", declared_grade="electronic"),
            base_use(substrate="titanium-alloy"),
        )
        self.assertEqual(result["verdict"], REJECTED)
        self.assertTrue(any("prohibited" in f for f in result["findings"]))

    def test_a_certificate_above_the_declared_grade_is_rejected(self):
        result = qualify_cleaning_agent(
            base_agent(certificate_residue_mg_per_l=3.0), base_use()
        )
        self.assertEqual(result["verdict"], REJECTED)
        self.assertTrue(any("not evidenced" in f for f in result["findings"]))

    def test_the_same_clean_agent_fails_once_the_drained_volume_grows(self):
        result = qualify_cleaning_agent(base_agent(), base_use(wetted_volume_l=10.0))
        self.assertEqual(result["verdict"], REJECTED)
        self.assertTrue(any("reduce the drained volume" in f for f in result["findings"]))

    def test_spreading_the_same_volume_wider_recovers_the_case(self):
        result = qualify_cleaning_agent(
            base_agent(), base_use(wetted_volume_l=10.0, wetted_area_m2=4.0)
        )
        self.assertEqual(result["verdict"], QUALIFIED)

    def test_the_permissible_concentration_travels_with_the_verdict(self):
        result = qualify_cleaning_agent(base_agent(), base_use())
        self.assertAlmostEqual(result["permissible_residue_mg_per_l"], 1.0, places=9)

    def test_a_non_mapping_use_rejected(self):
        with self.assertRaises(ValueError):
            qualify_cleaning_agent(base_agent(), ["aluminium-alloy"])


if __name__ == "__main__":
    unittest.main()

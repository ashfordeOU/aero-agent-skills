"""Contract test for the e3311 materials leaf (stdlib unittest)."""

import unittest

from e3311_materials_logic import (
    ACCEPTED,
    ACCEPTED_WITH_RESTRICTION,
    DEFAULT_MATERIAL_POLICY,
    REJECTED,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_material,
    compatibility_verdict,
    corrosion_verdict,
    couple_pairs,
    galvanic_couple_difference_v,
    galvanic_verdict,
    outgassing_verdict,
    select_materials,
    service_temperature_verdict,
    validate_material,
    validate_material_policy,
    validate_materials,
)


def material(mid="M-HOUSING", **kw):
    record = {
        "id": mid,
        "total_mass_loss_percent": 0.30,
        "condensable_volatile_percent": 0.02,
        "gas_evolution_cc_per_g": 0.40,
        "onset_depression_k": 0.5,
        "susceptibility": "low",
        "max_service_temperature_k": 420.0,
        "galvanic_potential_v": -0.55,
        "contacts": [],
    }
    record.update(kw)
    return record


def assembly():
    return [
        material("M-HOUSING", galvanic_potential_v=-0.55, contacts=["M-BRACKET"]),
        material("M-BRACKET", galvanic_potential_v=-0.45),
        material("M-SEAL", total_mass_loss_percent=0.60),
    ]


def case(**kw):
    record = {"predicted_hot_k": 350.0, "environment": "uncontrolled-humid"}
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_material_policy(DEFAULT_MATERIAL_POLICY), DEFAULT_MATERIAL_POLICY
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_material_policy("tml 1.0")

    def test_a_zero_mass_loss_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_material_policy(
                dict(DEFAULT_MATERIAL_POLICY, max_total_mass_loss_percent=0.0)
            )

    def test_an_empty_allowed_susceptibility_raises(self):
        with self.assertRaises(ValueError):
            validate_material_policy(
                dict(DEFAULT_MATERIAL_POLICY, allowed_susceptibility=())
            )

    def test_a_missing_environment_allowance_raises(self):
        with self.assertRaises(ValueError):
            validate_material_policy(
                dict(
                    DEFAULT_MATERIAL_POLICY,
                    galvanic_allowance_v={"controlled-benign": 0.5},
                )
            )


class TestMaterialValidation(unittest.TestCase):
    def test_a_valid_material_normalizes(self):
        record = validate_material(material())
        self.assertEqual(record["id"], "M-HOUSING")
        self.assertFalse(record["susceptibility_justified"])

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(""))

    def test_an_unknown_susceptibility_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(susceptibility="probably-fine"))

    def test_a_negative_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(total_mass_loss_percent=-0.1))

    def test_a_zero_service_rating_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(max_service_temperature_k=0.0))

    def test_a_non_boolean_justification_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(susceptibility_justified="signed-off"))

    def test_duplicate_material_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_materials([material("M-A"), material("M-A")])

    def test_a_contact_with_an_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            validate_materials([material("M-A", contacts=["M-GHOST"])])

    def test_a_self_contact_raises(self):
        with self.assertRaises(ValueError):
            validate_materials([material("M-A", contacts=["M-A"])])

    def test_an_empty_material_list_raises(self):
        with self.assertRaises(ValueError):
            validate_materials([])


class TestOutgassingGate(unittest.TestCase):
    def test_a_clean_material_passes(self):
        self.assertTrue(outgassing_verdict(material())["compliant"])

    def test_figures_exactly_on_the_limits_pass(self):
        record = material(
            total_mass_loss_percent=1.0, condensable_volatile_percent=0.10
        )
        self.assertTrue(outgassing_verdict(record)["compliant"])

    def test_excess_mass_loss_fails(self):
        result = outgassing_verdict(material(total_mass_loss_percent=1.4))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_excess_condensables_fail(self):
        result = outgassing_verdict(material(condensable_volatile_percent=0.4))
        self.assertFalse(result["compliant"])

    def test_both_figures_can_fail_together(self):
        result = outgassing_verdict(
            material(total_mass_loss_percent=2.0, condensable_volatile_percent=0.4)
        )
        self.assertEqual(len(result["findings"]), 2)


class TestCompatibilityGate(unittest.TestCase):
    def test_a_compatible_material_passes(self):
        self.assertTrue(compatibility_verdict(material())["compliant"])

    def test_gas_evolution_exactly_on_the_limit_passes(self):
        self.assertTrue(
            compatibility_verdict(material(gas_evolution_cc_per_g=2.0))["compliant"]
        )

    def test_excess_gas_evolution_fails(self):
        result = compatibility_verdict(material(gas_evolution_cc_per_g=5.0))
        self.assertFalse(result["compliant"])

    def test_an_onset_depression_beyond_the_limit_fails(self):
        result = compatibility_verdict(material(onset_depression_k=9.0))
        self.assertFalse(result["compliant"])

    def test_an_onset_depression_exactly_on_the_limit_passes(self):
        self.assertTrue(
            compatibility_verdict(material(onset_depression_k=4.0))["compliant"]
        )


class TestCorrosionGate(unittest.TestCase):
    def test_a_low_susceptibility_alloy_passes_outright(self):
        result = corrosion_verdict(material())
        self.assertTrue(result["compliant"])
        self.assertFalse(result["restricted"])

    def test_a_high_susceptibility_alloy_without_justification_fails(self):
        result = corrosion_verdict(material(susceptibility="high"))
        self.assertFalse(result["compliant"])

    def test_a_justified_alloy_is_retained_under_restriction(self):
        result = corrosion_verdict(
            material(susceptibility="moderate", susceptibility_justified=True)
        )
        self.assertTrue(result["compliant"])
        self.assertTrue(result["restricted"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_widened_policy_accepts_moderate_outright(self):
        policy = dict(DEFAULT_MATERIAL_POLICY, allowed_susceptibility=("low", "moderate"))
        result = corrosion_verdict(material(susceptibility="moderate"), policy)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["restricted"])


class TestServiceTemperatureGate(unittest.TestCase):
    def test_a_generous_rating_passes(self):
        self.assertTrue(service_temperature_verdict(material(), 350.0)["compliant"])

    def test_a_rating_exactly_on_the_requirement_passes(self):
        result = service_temperature_verdict(
            material(max_service_temperature_k=360.0), 350.0
        )
        self.assertAlmostEqual(result["required_rating_k"], 360.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_rating_short_of_the_margin_fails(self):
        result = service_temperature_verdict(
            material(max_service_temperature_k=355.0), 350.0
        )
        self.assertFalse(result["compliant"])

    def test_a_zero_hot_case_raises(self):
        with self.assertRaises(ValueError):
            service_temperature_verdict(material(), 0.0)


class TestGalvanicGate(unittest.TestCase):
    def test_the_difference_is_a_magnitude(self):
        self.assertAlmostEqual(
            galvanic_couple_difference_v(-0.55, -0.45), 0.10, places=9
        )
        self.assertAlmostEqual(
            galvanic_couple_difference_v(-0.45, -0.55), 0.10, places=9
        )

    def test_a_close_couple_passes_in_a_humid_environment(self):
        result = galvanic_verdict(
            material("M-A", galvanic_potential_v=-0.55),
            material("M-B", galvanic_potential_v=-0.45),
            "uncontrolled-humid",
        )
        self.assertTrue(result["compliant"])

    def test_a_couple_exactly_on_the_allowance_passes(self):
        result = galvanic_verdict(
            material("M-A", galvanic_potential_v=-0.50),
            material("M-B", galvanic_potential_v=-0.25),
            "uncontrolled-humid",
        )
        self.assertAlmostEqual(result["difference_v"], 0.25, places=9)
        self.assertTrue(result["compliant"])

    def test_the_same_couple_fails_in_a_coastal_environment(self):
        result = galvanic_verdict(
            material("M-A", galvanic_potential_v=-0.50),
            material("M-B", galvanic_potential_v=-0.25),
            "marine-coastal",
        )
        self.assertFalse(result["compliant"])

    def test_the_pair_is_reported_in_a_stable_order(self):
        result = galvanic_verdict(material("M-Z"), material("M-A"), "controlled-benign")
        self.assertEqual(result["pair"], ("M-A", "M-Z"))

    def test_an_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            galvanic_verdict(material("M-A"), material("M-B"), "deep-space-vacuum")

    def test_declared_contacts_become_one_pair_each(self):
        pairs = couple_pairs(assembly())
        self.assertEqual(len(pairs), 1)
        self.assertEqual(
            tuple(sorted((pairs[0][0]["id"], pairs[0][1]["id"]))),
            ("M-BRACKET", "M-HOUSING"),
        )


class TestPerMaterialOutcome(unittest.TestCase):
    def test_a_clean_material_is_accepted(self):
        result = assess_material(material(), case())
        self.assertEqual(result["outcome"], ACCEPTED)
        self.assertEqual(result["failed_gates"], [])

    def test_a_justified_alloy_is_accepted_with_restriction(self):
        result = assess_material(
            material(susceptibility="high", susceptibility_justified=True), case()
        )
        self.assertEqual(result["outcome"], ACCEPTED_WITH_RESTRICTION)

    def test_a_failing_gate_rejects_the_material(self):
        result = assess_material(material(gas_evolution_cc_per_g=8.0), case())
        self.assertEqual(result["outcome"], REJECTED)
        self.assertEqual(result["failed_gates"], ["compatibility"])

    def test_several_failing_gates_are_all_named(self):
        result = assess_material(
            material(
                total_mass_loss_percent=3.0,
                gas_evolution_cc_per_g=8.0,
                max_service_temperature_k=300.0,
            ),
            case(),
        )
        self.assertEqual(
            result["failed_gates"], ["outgassing", "compatibility", "service"]
        )

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_material(material(), "hot 350 K")


class TestAssemblySelection(unittest.TestCase):
    def test_a_sound_assembly_is_met(self):
        report = select_materials(assembly(), case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["rejected"], [])
        self.assertEqual(sorted(report["accepted"]), ["M-BRACKET", "M-HOUSING", "M-SEAL"])

    def test_a_rejected_material_fails_the_assembly(self):
        parts = assembly()
        parts[2]["total_mass_loss_percent"] = 4.0
        report = select_materials(parts, case())
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["rejected"], ["M-SEAL"])

    def test_a_failing_couple_fails_the_assembly_with_every_material_accepted(self):
        parts = assembly()
        parts[1]["galvanic_potential_v"] = 0.35
        report = select_materials(parts, case())
        self.assertEqual(report["rejected"], [])
        self.assertEqual(report["failed_couples"], [("M-BRACKET", "M-HOUSING")])
        self.assertFalse(report["compliant"])

    def test_the_environment_changes_the_couple_outcome(self):
        parts = assembly()
        parts[1]["galvanic_potential_v"] = -0.35
        humid = select_materials(parts, case(environment="uncontrolled-humid"))
        coastal = select_materials(parts, case(environment="marine-coastal"))
        self.assertTrue(humid["compliant"])
        self.assertFalse(coastal["compliant"])

    def test_a_restricted_material_is_grouped_separately(self):
        parts = assembly()
        parts[0]["susceptibility"] = "moderate"
        parts[0]["susceptibility_justified"] = True
        report = select_materials(parts, case())
        self.assertEqual(report["accepted_with_restriction"], ["M-HOUSING"])
        self.assertTrue(report["compliant"])

    def test_an_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            select_materials(assembly(), case(environment="orbit"))

    def test_a_missing_hot_case_raises(self):
        record = case()
        del record["predicted_hot_k"]
        with self.assertRaises(ValueError):
            select_materials(assembly(), record)


if __name__ == "__main__":
    unittest.main()

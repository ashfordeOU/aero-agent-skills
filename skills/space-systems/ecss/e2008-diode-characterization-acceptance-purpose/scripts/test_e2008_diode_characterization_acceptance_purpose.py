"""Contract tests for the clause 9.4.5.2.1 diode characterisation purpose logic."""

import unittest

from e2008_diode_characterization_acceptance_purpose_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_PURPOSE_POLICY,
    DIODE_CHARACTERISATION_JUSTIFIED,
    DIODE_CHARACTERISATION_NOT_PLANNED,
    DIODE_CHARACTERISATION_NOT_REQUIRED,
    DIODE_CHARACTERISATION_UNDERSAMPLED,
    DIODE_LOSS_BUDGET_EXCEEDED,
    PROTECTION_ROLES,
    RECOGNISED_ROLES,
    assess_diode_characterisation_purpose,
    characterisation_objectives,
    dissipation_within_budget,
    forward_dissipation_w,
    parasitic_loss_fraction,
    parasitic_loss_within_allowance,
    parasitic_reverse_loss_w,
    role_inventory,
    sample_coverage_fraction,
    validate_purpose_policy,
)

ROLES = [
    "cell-string-bypass-on-shadowing",
    "section-blocking-against-bus-drain",
]


def _policy(**overrides):
    policy = dict(DEFAULT_PURPOSE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "protection_roles": list(ROLES),
        "assembly": {
            "diode_population": 200,
            "worst_case_forward_current_a": 1.5,
            "expected_forward_voltage_v": 0.62,
            "string_reverse_voltage_v": 40.0,
            "expected_reverse_leakage_a": 1.0e-6,
            "array_output_w": 1800.0,
        },
        "characterisation": {"characterised_count": 40},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_purpose_policy(DEFAULT_PURPOSE_POLICY),
                      DEFAULT_PURPOSE_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(["min_sample_fraction"])

    def test_zero_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(min_sample_fraction=0.0))

    def test_sample_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(min_sample_fraction=1.4))

    def test_non_positive_dissipation_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(max_forward_dissipation_w=0.0))

    def test_whole_output_loss_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(max_parasitic_loss_fraction=1.0))


class ForwardDissipationTests(unittest.TestCase):
    def test_dissipation_is_drop_times_current(self):
        self.assertAlmostEqual(forward_dissipation_w(0.6, 2.0), 1.2, places=9)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            forward_dissipation_w(0.6, 0.0)

    def test_negative_drop_rejected(self):
        with self.assertRaises(ValueError):
            forward_dissipation_w(-0.6, 2.0)

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            forward_dissipation_w(0.6, True)

    def test_dissipation_exactly_on_budget_is_within_it(self):
        budget = float(DEFAULT_PURPOSE_POLICY["max_forward_dissipation_w"])
        value = forward_dissipation_w(0.5, 4.0)
        self.assertAlmostEqual(value, budget, places=9)
        self.assertTrue(dissipation_within_budget(value))

    def test_dissipation_over_budget_is_refused(self):
        self.assertFalse(dissipation_within_budget(forward_dissipation_w(0.8, 4.0)))


class ParasiticLossTests(unittest.TestCase):
    def test_loss_scales_with_population(self):
        one = parasitic_reverse_loss_w(40.0, 1.0e-6, 1)
        many = parasitic_reverse_loss_w(40.0, 1.0e-6, 200)
        self.assertAlmostEqual(many, one * 200.0, places=12)

    def test_zero_leakage_is_allowed(self):
        self.assertAlmostEqual(parasitic_reverse_loss_w(40.0, 0.0, 10), 0.0, places=12)

    def test_zero_population_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_reverse_loss_w(40.0, 1.0e-6, 0)

    def test_fractional_population_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_reverse_loss_w(40.0, 1.0e-6, 2.5)

    def test_loss_fraction_against_zero_output_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_loss_fraction(0.5, 0.0)

    def test_loss_exactly_on_allowance_is_within_it(self):
        allowance = float(DEFAULT_PURPOSE_POLICY["max_parasitic_loss_fraction"])
        fraction = parasitic_loss_fraction(10.0, 1000.0)
        self.assertAlmostEqual(fraction, allowance, places=9)
        self.assertTrue(parasitic_loss_within_allowance(fraction))

    def test_loss_over_allowance_is_refused(self):
        self.assertFalse(parasitic_loss_within_allowance(
            parasitic_loss_fraction(50.0, 1000.0)))


class SampleCoverageTests(unittest.TestCase):
    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(sample_coverage_fraction(200, 200), 1.0, places=12)

    def test_partial_coverage(self):
        self.assertAlmostEqual(sample_coverage_fraction(40, 200), 0.2, places=12)

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_coverage_fraction(201, 200)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            sample_coverage_fraction(0, 0)

    def test_negative_sample_rejected(self):
        with self.assertRaises(ValueError):
            sample_coverage_fraction(-1, 200)


class RoleInventoryTests(unittest.TestCase):
    def test_every_recognised_role_maps_to_an_objective(self):
        for role in RECOGNISED_ROLES:
            self.assertIn(role, PROTECTION_ROLES)
            self.assertTrue(PROTECTION_ROLES[role])

    def test_duplicates_are_collapsed(self):
        self.assertEqual(role_inventory(ROLES + ROLES), tuple(sorted(ROLES)))

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            role_inventory(["a-role-nobody-declared"])

    def test_non_collection_rejected(self):
        with self.assertRaises(ValueError):
            role_inventory("cell-string-bypass-on-shadowing")

    def test_objectives_append_the_shared_record(self):
        objectives = characterisation_objectives(ROLES)
        self.assertEqual(objectives[-1], COMMON_OBJECTIVE)
        self.assertEqual(len(objectives), len(ROLES) + 1)

    def test_no_roles_gives_no_objectives(self):
        self.assertEqual(characterisation_objectives([]), ())


class PurposeVerdictTests(unittest.TestCase):
    def test_nominal_case_is_justified(self):
        result = assess_diode_characterisation_purpose(_case())
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_JUSTIFIED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_no_declared_role_removes_the_requirement(self):
        result = assess_diode_characterisation_purpose(_case(protection_roles=[]))
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["required"])
        self.assertTrue(result["findings"])

    def test_unplanned_characterisation_is_its_own_verdict(self):
        case = _case()
        case["characterisation"] = None
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_NOT_PLANNED)
        self.assertIsNone(result["sample_coverage_fraction"])

    def test_thin_sample_is_undersampled_not_unplanned(self):
        case = _case(characterisation={"characterised_count": 4})
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_UNDERSAMPLED)
        self.assertFalse(result["sample_coverage_met"])

    def test_coverage_exactly_on_the_floor_earns_the_sample(self):
        case = _case(characterisation={"characterised_count": 20})
        result = assess_diode_characterisation_purpose(case)
        self.assertAlmostEqual(
            result["sample_coverage_fraction"],
            float(DEFAULT_PURPOSE_POLICY["min_sample_fraction"]),
            places=9,
        )
        self.assertTrue(result["sample_coverage_met"])
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_JUSTIFIED)

    def test_hot_diode_reports_the_loss_budget_verdict(self):
        case = _case()
        case["assembly"]["worst_case_forward_current_a"] = 6.0
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_LOSS_BUDGET_EXCEEDED)
        self.assertFalse(result["dissipation_within_budget"])

    def test_leaky_population_reports_the_loss_budget_verdict(self):
        case = _case()
        case["assembly"]["expected_reverse_leakage_a"] = 5.0e-3
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_LOSS_BUDGET_EXCEEDED)
        self.assertFalse(result["parasitic_loss_within_allowance"])

    def test_both_budgets_breached_reports_both_findings(self):
        case = _case()
        case["assembly"]["worst_case_forward_current_a"] = 6.0
        case["assembly"]["expected_reverse_leakage_a"] = 5.0e-3
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_LOSS_BUDGET_EXCEEDED)
        self.assertEqual(len(result["findings"]), 2)

    def test_undersampling_is_reported_before_the_budgets(self):
        case = _case(characterisation={"characterised_count": 1})
        case["assembly"]["worst_case_forward_current_a"] = 6.0
        result = assess_diode_characterisation_purpose(case)
        self.assertEqual(result["verdict"], DIODE_CHARACTERISATION_UNDERSAMPLED)

    def test_objectives_are_reported_whatever_the_verdict(self):
        case = _case(characterisation={"characterised_count": 1})
        result = assess_diode_characterisation_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_missing_roles_key_rejected(self):
        case = _case()
        del case["protection_roles"]
        with self.assertRaises(ValueError):
            assess_diode_characterisation_purpose(case)

    def test_missing_assembly_block_rejected(self):
        case = _case()
        del case["assembly"]
        with self.assertRaises(ValueError):
            assess_diode_characterisation_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_characterisation_purpose(["protection_roles"])

    def test_non_mapping_characterisation_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_characterisation_purpose(_case(characterisation=[40]))

    def test_sample_beyond_population_rejected(self):
        case = _case(characterisation={"characterised_count": 900})
        with self.assertRaises(ValueError):
            assess_diode_characterisation_purpose(case)


if __name__ == "__main__":
    unittest.main()

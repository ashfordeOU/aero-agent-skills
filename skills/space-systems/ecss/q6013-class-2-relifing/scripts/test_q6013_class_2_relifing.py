"""Contract tests for the clause 5.3.10 class 2 relifing of stored parts.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused relifing policy,
an unregistered storage environment or package family, a store that credits
no period, a lot still inside its period, an exhausted cycle ceiling, a test
record missing an owed test, a solderability failure that may be re-tinned,
a failure that may not, and a cycle whose grant is too small to be worth
taking.
"""

import unittest

from q6013_class_2_relifing_logic import (
    BASE_STORAGE_MONTHS,
    DEFAULT_RELIFE_POLICY,
    ELECTRICAL_RE_VERIFICATION,
    EXTERNAL_VISUAL,
    HERMETIC_FAMILIES,
    MOISTURE_PRECONDITIONING,
    PACKAGE_SEAL,
    RELIFE_GRANTED,
    RELIFE_NOT_REQUIRED,
    RELIFE_REFUSED_CYCLE_LIMIT,
    RELIFE_REFUSED_NO_USEFUL_EXTENSION,
    RELIFE_REFUSED_STORAGE_UNCONTROLLED,
    RELIFE_REFUSED_TEST_FAILURE,
    RELIFE_REFUSED_TESTS_INCOMPLETE,
    RETINNING_PERMITTED,
    SOLDERABILITY,
    STORAGE_ENVIRONMENTS,
    assess_relifing,
    base_storage_months,
    effective_storage_months,
    granted_extension_months,
    required_relife_tests,
    storage_environment_factor,
    storage_period_expired,
    test_failures,
    validate_relife_policy,
    validate_test_results,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RELIFE_POLICY)
    policy.update(overrides)
    return policy


def _passing(required):
    return {name: True for name in required}


def _case(**overrides):
    required = required_relife_tests("hermetic-ceramic", False, 0)
    case = {
        "package_family": "hermetic-ceramic",
        "storage_environment": "dry-nitrogen-cabinet",
        "elapsed_storage_months": 72.0,
        "completed_relife_cycles": 0,
        "moisture_sensitive": False,
        "test_results": _passing(required),
        "retinning_already_used": False,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_relife_policy(DEFAULT_RELIFE_POLICY), DEFAULT_RELIFE_POLICY)

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_RELIFE_POLICY)
        del policy["extension_decay"]
        with self.assertRaises(ValueError):
            validate_relife_policy(policy)

    def test_a_decay_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(extension_decay=1.4))

    def test_a_zero_decay_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(extension_decay=0.0))

    def test_a_zero_cycle_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(_policy(max_relife_cycles=0))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_relife_policy(["extension_decay"])


class StoragePeriodTests(unittest.TestCase):
    def test_every_registered_environment_credits_a_known_fraction(self):
        for name, factor in STORAGE_ENVIRONMENTS.items():
            self.assertAlmostEqual(storage_environment_factor(name), factor, places=9)

    def test_an_unregistered_environment_is_refused(self):
        with self.assertRaises(ValueError):
            storage_environment_factor("a shelf in the lab")

    def test_an_unregistered_package_family_is_refused(self):
        with self.assertRaises(ValueError):
            base_storage_months("ceramic-ish")

    def test_the_hermetic_families_are_registered_families(self):
        self.assertTrue(HERMETIC_FAMILIES.issubset(set(BASE_STORAGE_MONTHS)))

    def test_a_graded_store_scales_the_baseline_period(self):
        self.assertAlmostEqual(
            effective_storage_months("hermetic-ceramic", "dry-cabinet-low-humidity"),
            48.0,
            places=9,
        )

    def test_an_uncontrolled_store_credits_nothing(self):
        self.assertAlmostEqual(
            effective_storage_months("plastic-encapsulated", "uncontrolled"), 0.0, places=9
        )

    def test_a_lot_sitting_exactly_on_its_period_is_inside_it(self):
        self.assertFalse(storage_period_expired(60.0, 60.0))

    def test_a_lot_past_its_period_is_expired(self):
        self.assertTrue(storage_period_expired(61.0, 60.0))

    def test_a_negative_elapsed_storage_is_refused(self):
        with self.assertRaises(ValueError):
            storage_period_expired(-1.0, 60.0)


class TestSetTests(unittest.TestCase):
    def test_a_hermetic_family_owes_a_seal_test(self):
        tests = required_relife_tests("hermetic-ceramic", False, 0)
        self.assertIn(PACKAGE_SEAL, tests)
        self.assertNotIn(MOISTURE_PRECONDITIONING, tests)

    def test_a_moisture_sensitive_plastic_family_owes_preconditioning(self):
        tests = required_relife_tests("plastic-encapsulated", True, 0)
        self.assertIn(MOISTURE_PRECONDITIONING, tests)
        self.assertNotIn(PACKAGE_SEAL, tests)

    def test_visual_and_solderability_are_owed_by_every_family(self):
        for family in BASE_STORAGE_MONTHS:
            tests = required_relife_tests(family, False, 0)
            self.assertIn(EXTERNAL_VISUAL, tests)
            self.assertIn(SOLDERABILITY, tests)

    def test_electrical_re_verification_starts_at_the_declared_cycle(self):
        first = required_relife_tests("hermetic-ceramic", False, 0)
        second = required_relife_tests("hermetic-ceramic", False, 1)
        self.assertNotIn(ELECTRICAL_RE_VERIFICATION, first)
        self.assertIn(ELECTRICAL_RE_VERIFICATION, second)

    def test_a_hermetic_family_declared_moisture_sensitive_is_refused(self):
        with self.assertRaises(ValueError):
            required_relife_tests("hermetic-metal", True, 0)

    def test_a_result_record_carrying_an_unowed_test_is_refused(self):
        required = required_relife_tests("plastic-encapsulated", False, 0)
        results = _passing(required)
        results[PACKAGE_SEAL] = True
        with self.assertRaises(ValueError):
            validate_test_results(results, required)

    def test_a_missing_owed_test_is_reported_not_assumed(self):
        required = required_relife_tests("hermetic-ceramic", False, 0)
        results = _passing(required)
        del results[PACKAGE_SEAL]
        record = validate_test_results(results, required)
        self.assertFalse(record["complete"])
        self.assertEqual(record["missing"], [PACKAGE_SEAL])

    def test_a_non_boolean_outcome_is_refused(self):
        required = required_relife_tests("plastic-encapsulated", False, 0)
        results = _passing(required)
        results[SOLDERABILITY] = "pass"
        with self.assertRaises(ValueError):
            validate_test_results(results, required)

    def test_failures_are_reported_in_the_owed_order(self):
        required = required_relife_tests("hermetic-ceramic", False, 0)
        results = _passing(required)
        results[SOLDERABILITY] = False
        results[PACKAGE_SEAL] = False
        self.assertEqual(test_failures(results, required), [SOLDERABILITY, PACKAGE_SEAL])


class ExtensionTests(unittest.TestCase):
    def test_the_first_cycle_grants_a_decayed_share_of_the_period(self):
        self.assertAlmostEqual(
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 0),
            30.0,
            places=9,
        )

    def test_each_further_cycle_grants_less_than_the_one_before(self):
        first = granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 0)
        second = granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", 1)
        self.assertAlmostEqual(second, 15.0, places=9)
        self.assertLess(second, first)

    def test_a_poorer_store_grants_a_smaller_extension(self):
        self.assertAlmostEqual(
            granted_extension_months("plastic-encapsulated", "controlled-ambient", 0),
            6.0,
            places=9,
        )

    def test_a_negative_cycle_count_is_refused(self):
        with self.assertRaises(ValueError):
            granted_extension_months("hermetic-ceramic", "dry-nitrogen-cabinet", -1)


class AssessmentTests(unittest.TestCase):
    def test_an_expired_lot_passing_every_owed_test_is_relifed(self):
        result = assess_relifing(_case())
        self.assertEqual(result["verdict"], RELIFE_GRANTED)
        self.assertTrue(result["relifed"])
        self.assertAlmostEqual(result["granted_extension_months"], 30.0, places=9)
        self.assertAlmostEqual(result["new_permitted_months"], 102.0, places=9)

    def test_a_lot_still_inside_its_period_is_not_relifed(self):
        result = assess_relifing(_case(elapsed_storage_months=48.0))
        self.assertEqual(result["verdict"], RELIFE_NOT_REQUIRED)
        self.assertFalse(result["relifed"])

    def test_a_lot_exactly_on_its_period_is_not_relifed(self):
        result = assess_relifing(_case(elapsed_storage_months=60.0))
        self.assertEqual(result["verdict"], RELIFE_NOT_REQUIRED)

    def test_an_uncontrolled_store_stops_the_assessment_first(self):
        result = assess_relifing(_case(storage_environment="uncontrolled"))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_STORAGE_UNCONTROLLED)

    def test_an_exhausted_cycle_ceiling_sends_the_lot_for_re_screening(self):
        result = assess_relifing(_case(completed_relife_cycles=3))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_CYCLE_LIMIT)

    def test_a_record_missing_an_owed_test_is_not_a_pass(self):
        case = _case()
        del case["test_results"][PACKAGE_SEAL]
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_TESTS_INCOMPLETE)
        self.assertEqual(result["missing_tests"], [PACKAGE_SEAL])

    def test_a_lone_solderability_failure_permits_one_re_tin(self):
        case = _case()
        case["test_results"][SOLDERABILITY] = False
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RETINNING_PERMITTED)

    def test_the_re_tinning_allowance_is_available_only_once(self):
        case = _case(retinning_already_used=True)
        case["test_results"][SOLDERABILITY] = False
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_TEST_FAILURE)

    def test_policy_may_withdraw_the_re_tinning_allowance(self):
        case = _case()
        case["test_results"][SOLDERABILITY] = False
        result = assess_relifing(case, _policy(allow_retinning=False))
        self.assertEqual(result["verdict"], RELIFE_REFUSED_TEST_FAILURE)

    def test_a_seal_failure_is_never_re_tinned(self):
        case = _case()
        case["test_results"][PACKAGE_SEAL] = False
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_TEST_FAILURE)
        self.assertEqual(result["failed_tests"], [PACKAGE_SEAL])

    def test_a_grant_under_the_useful_minimum_sends_the_lot_for_re_screening(self):
        required = required_relife_tests("plastic-encapsulated", False, 2)
        case = _case(
            package_family="plastic-encapsulated",
            storage_environment="controlled-ambient",
            elapsed_storage_months=30.0,
            completed_relife_cycles=2,
            test_results=_passing(required),
        )
        result = assess_relifing(case)
        self.assertEqual(result["verdict"], RELIFE_REFUSED_NO_USEFUL_EXTENSION)
        self.assertAlmostEqual(result["granted_extension_months"], 1.5, places=9)

    def test_a_grant_landing_exactly_on_the_useful_minimum_is_taken(self):
        required = required_relife_tests("bare-die-in-waffle-pack", False, 0)
        case = _case(
            package_family="bare-die-in-waffle-pack",
            storage_environment="controlled-ambient",
            elapsed_storage_months=12.0,
            test_results=_passing(required),
        )
        result = assess_relifing(case)
        self.assertAlmostEqual(result["granted_extension_months"], 3.0, places=9)
        self.assertEqual(result["verdict"], RELIFE_GRANTED)

    def test_a_case_missing_a_required_key_is_refused(self):
        case = _case()
        del case["retinning_already_used"]
        with self.assertRaises(ValueError):
            assess_relifing(case)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_relifing(["package_family"])

    def test_every_verdict_carries_at_least_one_finding(self):
        for case in (
            _case(),
            _case(elapsed_storage_months=48.0),
            _case(storage_environment="uncontrolled"),
            _case(completed_relife_cycles=3),
        ):
            self.assertTrue(assess_relifing(case)["findings"])


if __name__ == "__main__":
    unittest.main()
